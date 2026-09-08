"""range_vol.py -- RESEARCH LINE 3 (2026-09-08, line name `range_vol`).

Range-based realized-volatility estimators as a drop-in replacement for the
vol overlay's estimator. Live divides the book by max(cc10, cc30) of QQQ
close-to-close returns; Parkinson / Garman-Klass / Rogers-Satchell / Yang-
Zhang use the intraday range and are several times more statistically
efficient per day, so a short range window has the precision of a long
close-to-close one. Hypothesis: reaction speed of the 10d leg with the
stability of the 30d leg. This is an ESTIMATOR change, not a timing signal.

RESEARCH ONLY (change freeze until 2026-12-07). Nothing here is applied.

DATA: data/qqq_ohlc.csv (new, this line). Provenance in
research_notes/range_vol.md. Split-adjusted daily OHLC 1999-09-15..2026-09-04,
closes and opens match data/qqq_long_history.csv to the cent on all 6784 days.

CONTROLS (BRIEFING.md): both-era, exposure match (fixed T=0.20 with
exposure_control AND T re-calibrated by bisection to live's exposure -- the
latter is the one that counts because range estimators run BELOW close-to-
close on QQQ, so at a fixed T they simply hold more), causal statistics only,
same rows, block bootstrap (20/60), placebo, leave-one-regime-out, candidate
count, real-instrument confirmation (weekly rr and the real DAILY drift-band
harness of vol_estimator_daily.py), rebalances/yr.
"""
import sys, math, csv, random, time, json
sys.path.insert(0, 'paper-track')
T0 = time.time()
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from downturn_review import exposure_control
from block_bootstrap import boot, stats, N_BOOT, REGIMES
from state import realized_vol, extension_scale, VOL_TARGET_PA
from improvement_search import BAND, ONE_WAY_SPREAD

A = 252
L = math.log
def say(*a):
    print(*a, flush=True)

# ============================================================== 1. OHLC data
O = {}
for r in csv.DictReader(open('data/qqq_ohlc.csv')):
    O[r['d']] = (float(r['o']), float(r['h']), float(r['l']), float(r['c']))
od = sorted(O); oix = {d: i for i, d in enumerate(od)}
assert od == qd, "OHLC dates must equal the long-history dates (same rows)"
cl = {d: O[d][3] for d in od}
mism = sum(1 for d in od if abs(cl[d] - qqq[d]) > 0.01)
say(f"OHLC {len(od)} days {od[0]}..{od[-1]}; closes != long history by >1c on {mism} days")
assert mism == 0

# per-day squared terms (log)
U = []
for i, d in enumerate(od):
    o, h, l, c = O[d]
    hl = L(h / l); co = L(c / o); ho = L(h / o); lo = L(l / o); hc = L(h / c); lc = L(l / c)
    gap = L(o / O[od[i - 1]][3]) if i > 0 else None
    U.append(dict(P=hl * hl / (4 * L(2)), GK=0.5 * hl * hl - (2 * L(2) - 1) * co * co,
                  RS=hc * ho + lc * lo, gap=gap, co=co))

def est(kind, i, n):
    """Annualised vol of `kind` over the n bars ending at index i (causal)."""
    if i - n + 1 < 1:
        return None
    w = U[i - n + 1:i + 1]
    if kind in ('P', 'GK', 'RS'):
        return math.sqrt(max(sum(x[kind] for x in w) / n, 0.0) * A)
    if kind == 'GKJ':   # Garman-Klass plus the squared overnight jump
        return math.sqrt(max(sum(x['GK'] + x['gap'] ** 2 for x in w) / n, 0.0) * A)
    if kind == 'YZ':
        g = [x['gap'] for x in w]; c = [x['co'] for x in w]
        mg = sum(g) / n; mc = sum(c) / n
        vo = sum((x - mg) ** 2 for x in g) / (n - 1)
        vc = sum((x - mc) ** 2 for x in c) / (n - 1)
        vrs = sum(x['RS'] for x in w) / n
        k = 0.34 / (1.34 + (n + 1) / (n - 1))
        return math.sqrt(max(vo + k * vc + (1 - k) * vrs, 0.0) * A)
    if kind == 'cc':    # THE live function, unchanged
        return realized_vol(od, cl, as_of=od[i], lookback=n)
    raise KeyError(kind)

RANGE = ('P', 'GK', 'RS', 'YZ')
LBS = (5, 10, 20, 30)
SER = {}
def series(key):
    if key not in SER:
        kind = key.rstrip('0123456789'); n = int(key[len(kind):])
        SER[key] = {d: est(kind, i, n) for i, d in enumerate(od)}
    return SER[key]
for k in RANGE + ('GKJ',):
    for n in LBS: series(f'{k}{n}')
for n in (5, 10, 20, 30): series(f'cc{n}')
# causal bias-corrected GK10: scale by trailing-252d cc/GK level ratio
# window = min(252, bars available), floor 60, so it is defined on every proxy
# row (OHLC starts ~200 sessions before the first row) and stays causal.
SER['bcGK10'] = {}
for i, d in enumerate(od):
    m = min(252, i)
    c_, g_ = (est('cc', i, m), est('GK', i, m)) if m >= 60 else (None, None)
    SER['bcGK10'][d] = SER['GK10'][d] * c_ / g_ if (SER['GK10'][d] and c_ and g_) else None
say(f"series built ({len(SER)}) in {time.time()-T0:.0f}s")

# sanity: rows' vol fields equal our cc series (same function, same data)
dv30 = max(abs(r['vol'] - SER['cc30'][r['d']]) for r in rows)
dv10 = max(abs(r['vol10'] - SER['cc10'][r['d']]) for r in rows)
say(f"rows vol30/vol10 vs cc30/cc10 max abs diff {dv30:.2e} / {dv10:.2e}")

# =============================================== 2. synthetic GBM verification
say("\n== 2. SYNTHETIC GBM: bias and efficiency of each estimator (true sigma = 20%)")
def gbm_check(days=12000, steps=390, f_over=0.0, sig=0.20, n=10, seed=7):
    """Pure-python GBM with `steps` intraday increments per day and an optional
    overnight jump carrying `f_over` of the daily variance. Returns, per
    estimator, (E[sigma_hat]/sigma, Var(cc variance estimate)/Var(estimator))
    over non-overlapping n-day windows."""
    rng = random.Random(seed); dv = sig ** 2 / A
    so = math.sqrt(f_over * dv); si = math.sqrt((1 - f_over) * dv / steps)
    bars = []; prev = 0.0
    for _ in range(days):
        o = prev + rng.gauss(0, so); x = 0.0; hi = 0.0; lo = 0.0
        for _ in range(steps):
            x += rng.gauss(0, si)
            if x > hi: hi = x
            elif x < lo: lo = x
        c = o + x; bars.append((o, o + hi, o + lo, c, o - prev)); prev = c
    terms = []
    for i in range(1, days):
        o, h, l, c, gap = bars[i]
        hl = h - l; co = c - o; ho = h - o; lo_ = l - o; hc = h - c; lc = l - c
        terms.append(dict(P=hl * hl / (4 * L(2)), GK=0.5 * hl * hl - (2 * L(2) - 1) * co * co,
                          RS=hc * ho + lc * lo_, gap=gap, co=co, cc=c - bars[i - 1][3]))
    k = 0.34 / (1.34 + (n + 1) / (n - 1))
    out = {kk: [] for kk in ('P', 'GK', 'RS', 'GKJ', 'YZ', 'cc')}
    def svar(v):
        m = sum(v) / len(v); return sum((x - m) ** 2 for x in v) / (len(v) - 1)
    for s in range(0, len(terms) - n + 1, n):
        w = terms[s:s + n]
        out['P'].append(sum(x['P'] for x in w) / n); out['GK'].append(sum(x['GK'] for x in w) / n)
        out['RS'].append(sum(x['RS'] for x in w) / n)
        out['GKJ'].append(sum(x['GK'] + x['gap'] ** 2 for x in w) / n)
        out['YZ'].append(svar([x['gap'] for x in w]) + k * svar([x['co'] for x in w]) + (1 - k) * sum(x['RS'] for x in w) / n)
        out['cc'].append(svar([x['cc'] for x in w]))
    vcc = svar(out['cc'])
    return {kk: (math.sqrt(sum(v) / len(v) * A) / sig, vcc / svar(v)) for kk, v in out.items()}

for f_over in (0.0, 0.30):
    for n in (5, 10, 30):
        res = gbm_check(f_over=f_over, n=n)
        say(f"  overnight share {f_over:.0%}  n={n:>2}  " + "  ".join(
            f"{k}: bias {b:.3f} eff {e:4.1f}x" for k, (b, e) in res.items()))
say("  (bias = E[sigma_hat]/sigma; eff = Var(cc var-estimate)/Var(estimator) -- >1 means fewer days")
say("   for the same precision. 390 steps/day: the discrete-sampling bias of the range terms is a few %.)")

# ============================================= 3. QQQ empirical bias / overnight
say("\n== 3. QQQ EMPIRICAL: level vs close-to-close, overnight share, forecast quality")
P_rows = rows  # proxy rows 2000-07..2026-08
gsq = [U[oix[r['d']]]['gap'] ** 2 for r in P_rows]
ccsq = [(L(O[r['d']][3] / O[od[oix[r['d']] - 1]][3])) ** 2 for r in P_rows]
say(f"  overnight (close->open) share of daily close-to-close variance on proxy rows: "
    f"{sum(gsq)/sum(ccsq):.1%}")
def mean(x): return sum(x) / len(x)
say(f"  {'series':<8}{'mean vol':>10}{'/cc30':>8}{'corr w/ cc30':>14}{'RMSE log fwd20':>16}{'corr fwd20':>12}")
# forward 20d realized cc vol (target for forecast-quality diagnostic)
FWD = {}
for i, d in enumerate(od):
    FWD[d] = realized_vol(od, cl, as_of=od[i + 20], lookback=20) if i + 20 < len(od) else None
def corr(a, b):
    ma, mb = mean(a), mean(b)
    sa = math.sqrt(sum((x - ma) ** 2 for x in a)); sb = math.sqrt(sum((x - mb) ** 2 for x in b))
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb)
mcc30 = mean([SER['cc30'][r['d']] for r in P_rows])
DIAG = {}
for key in ['cc10', 'cc20', 'cc30', 'cc5'] + [f'{k}{n}' for k in RANGE + ('GKJ',) for n in LBS] + ['bcGK10']:
    xs = [SER[key][r['d']] for r in P_rows if SER[key][r['d']]]; ys = [SER['cc30'][r['d']] for r in P_rows if SER[key][r['d']]]
    ok = [(x, SER['cc30'][r['d']], FWD[r['d']]) for x, r in zip(xs, P_rows) if x and FWD[r['d']]]
    rmse = math.sqrt(mean([(L(x) - L(f)) ** 2 for x, _, f in ok]))
    cf = corr([L(x) for x, _, f in ok], [L(f) for x, _, f in ok])
    DIAG[key] = dict(mean=mean(xs), ratio=mean(xs) / mcc30, rmse=rmse, corr_fwd=cf)
    say(f"  {key:<8}{mean(xs)*100:9.2f}%{mean(xs)/mcc30:8.3f}{corr(xs, ys):14.3f}{rmse:16.3f}{cf:12.3f}")
# live max(10,30) forecast quality
ok = [(r['vol_live'], FWD[r['d']]) for r in P_rows if FWD[r['d']]]
say(f"  {'live':<8}{mean([x for x,_ in ok])*100:9.2f}%{'':8}{'':14}"
    f"{math.sqrt(mean([(L(x)-L(f))**2 for x,f in ok])):16.3f}{corr([L(x) for x,_ in ok],[L(f) for _,f in ok]):12.3f}")

# ============================================================ 4. the family
FAM = {}
FAM['LIVE max(cc10,cc30)'] = ('cc10', 'cc30')
for n in (10, 20, 30): FAM[f'cc{n}'] = (f'cc{n}',)
for k in RANGE:
    for n in LBS: FAM[f'{k}{n}'] = (f'{k}{n}',)
for k in RANGE + ('GKJ',):
    for n in (5, 10): FAM[f'max({k}{n},cc30)'] = (f'{k}{n}', 'cc30')
for k in RANGE:
    FAM[f'max({k}10,{k}30)'] = (f'{k}10', f'{k}30')
    FAM[f'max({k}5,{k}30)'] = (f'{k}5', f'{k}30')
FAM['GKJ10'] = ('GKJ10',); FAM['GKJ30'] = ('GKJ30',)
FAM['bcGK10'] = ('bcGK10',); FAM['max(bcGK10,cc30)'] = ('bcGK10', 'cc30')
NCAND = len(FAM) - 1
say(f"\n== 4. FAMILY: {NCAND} candidates + live")

for r in rows:
    for key in SER: r[key] = SER[key][r['d']]
for r in rr:
    for key in SER: r[key] = SER[key][r['d0']]
allkeys = sorted({k for v in FAM.values() for k in v})
P = [r for r in rows if all(r[k] is not None for k in allkeys)]
Pr = [r for r in rr if all(r[k] is not None for k in allkeys)]
say(f"  same rows: proxy {len(P)}/{len(rows)}  real weekly {len(Pr)}/{len(rr)}")

def trim_of(r):
    w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
    return w if f >= 1 else tuple(a * f for a in w[:4]) + (1 - f * sum(w[:4]),)

def mk(keys, T=VOL_TARGET_PA, vtf=vt):
    def fn(r):
        return vtf(trim_of(r), max(r[k] for k in keys), T)
    return fn

def run_count(rows_, wfn, band=BAND):
    """improvement_search.run() verbatim plus a rebalance counter. Verified
    below to return the identical return series -- it is NOT a new loop."""
    held = prev = None; rets = []; risky = 0.0; nreb = 0
    for r in rows_:
        t = wfn(r); key = (r['state'], r['agree']); cost = 0.0
        if held is None:
            held = list(t)
        else:
            drift = sum(abs(t[j] - held[j]) for j in range(5))
            if key != prev or drift > band:
                cost = ONE_WAY_SPREAD * drift; held = list(t); nreb += 1
        risky += sum(held[:4]); g = sum(held[j] * r['legs'][j] for j in range(5))
        rets.append(g - cost); dn = 1 + g
        if dn > 0: held = [held[j] * (1 + r['legs'][j]) / dn for j in range(5)]
        prev = key
    return rets, risky / len(rows_), nreb

live_fn = mk(FAM['LIVE max(cc10,cc30)'])
a1, e1 = run(P, live_fn); a2, e2, nreb_live = run_count(P, live_fn)
assert a1 == a2 and e1 == e2, "run_count diverged from run()"
YRS = len(P) / A
base = evaluate(P, live_fn); base_exp = base['risky']
baser = RF.eval_real(Pr, mk(FAM['LIVE max(cc10,cc30)'], vtf=RF.vt))
say(f"  LIVE: {base['cagr']*100:.2f}% / {base['sharpe']:.3f} / {base['mdd']*100:.1f}%  "
    f"S {base['s_sharpe']:.3f} H {base['h_sharpe']:.3f}  expo {base_exp*100:.2f}%  "
    f"reb/yr {nreb_live/YRS:.0f}  real {baser['cagr']*100:.2f}% / {baser['sharpe']:.3f} / {baser['mdd']*100:.1f}%")

def calib(keys, target, lo=0.02, hi=3.0):
    for _ in range(45):
        mid = (lo + hi) / 2
        if run(P, mk(keys, mid))[1] < target: lo = mid
        else: hi = mid
    return (lo + hi) / 2

RES = {}
say(f"\n-- 4a. FIXED T=0.20 (what a naive swap does) --")
say(f"  {'variant':<20}{'CAGR':>7}{'Sharpe':>8}{'MDD':>7}{'S':>7}{'H':>7}{'expo':>7}{'ctl Sh':>8}{'ctl S/H':>13}{'reb/yr':>7}{'real Sh':>8}")
for lab, keys in FAM.items():
    fn = mk(keys); ev = evaluate(P, fn); _, _, nreb = run_count(P, fn)
    k, c = exposure_control(P, ev['risky'])
    er = RF.eval_real(Pr, mk(keys, vtf=RF.vt))
    both = ev['s_sharpe'] > base['s_sharpe'] and ev['h_sharpe'] > base['h_sharpe']
    beats_ctl = ev['s_sharpe'] > c['s_sharpe'] and ev['h_sharpe'] > c['h_sharpe']
    RES[lab] = dict(keys=keys, fixed=dict(ev=ev, ctl=c, nreb=nreb / YRS, real=er, both=both, beats_ctl=beats_ctl))
    say(f"  {lab:<20}{ev['cagr']*100:6.2f}%{ev['sharpe']:8.3f}{ev['mdd']*100:6.1f}%{ev['s_sharpe']:7.3f}{ev['h_sharpe']:7.3f}"
        f"{ev['risky']*100:6.1f}%{c['sharpe']:8.3f}{c['s_sharpe']:7.3f}/{c['h_sharpe']:.3f}{nreb/YRS:7.0f}{er['sharpe']:8.3f}"
        f"{'  BOTH' if both else ''}{'+ctl' if beats_ctl else ''}{'' if c['exp_matched'] else ' (ctl unmatched)'}")

say(f"\n-- 4b. EXPOSURE-MATCHED: T re-calibrated so proxy exposure = live's {base_exp*100:.2f}% (THE comparison) --")
say(f"  {'variant':<20}{'T*':>6}{'CAGR':>7}{'Sharpe':>8}{'MDD':>7}{'S':>7}{'H':>7}{'reb/yr':>7}{'real CAGR/Sh/MDD':>20}{'real expo':>10}")
SERIES = {'LIVE': run(P, live_fn)[0]}
def real_expo(fn):
    return mean([sum(fn(r)[:4]) for r in Pr])
live_real_expo = real_expo(mk(FAM['LIVE max(cc10,cc30)'], vtf=RF.vt))
for lab, keys in FAM.items():
    T = VOL_TARGET_PA if lab.startswith('LIVE') else calib(keys, base_exp)
    fn = mk(keys, T); ev = evaluate(P, fn); rets, _, nreb = run_count(P, fn)
    er = RF.eval_real(Pr, mk(keys, T, RF.vt)); rex = real_expo(mk(keys, T, RF.vt))
    both = ev['s_sharpe'] > base['s_sharpe'] and ev['h_sharpe'] > base['h_sharpe']
    RES[lab]['matched'] = dict(T=T, ev=ev, nreb=nreb / YRS, real=er, real_expo=rex, both=both)
    SERIES[lab] = rets
    say(f"  {lab:<20}{T:6.3f}{ev['cagr']*100:6.2f}%{ev['sharpe']:8.3f}{ev['mdd']*100:6.1f}%{ev['s_sharpe']:7.3f}{ev['h_sharpe']:7.3f}"
        f"{nreb/YRS:7.0f}   {er['cagr']*100:5.2f}/{er['sharpe']:.3f}/{er['mdd']*100:5.1f}{rex*100:9.1f}%"
        f"{'  BOTH' if both else ''}{'  +real' if er['sharpe'] > baser['sharpe'] else ''}")

# ============================================================ 5. survivors
surv = [lab for lab in FAM if not lab.startswith('LIVE') and RES[lab]['matched']['both']]
surv_real = [lab for lab in surv if RES[lab]['matched']['real']['sharpe'] > baser['sharpe']]
say(f"\n== 5. SCREEN: {len(surv)}/{NCAND} beat live on BOTH eras exposure-matched; "
    f"{len(surv_real)} of those also beat live on real weekly: {surv_real}")
# deep-dive set: survivors that also win on real, else the top-3 by full Sharpe
if surv_real:
    DEEP = sorted(surv_real, key=lambda l: -RES[l]['matched']['ev']['sharpe'])[:4]
else:
    DEEP = sorted([l for l in FAM if not l.startswith('LIVE')], key=lambda l: -RES[l]['matched']['ev']['sharpe'])[:3]
say(f"  deep-dive set: {DEEP}")

say(f"\n-- 5a. BLOCK BOOTSTRAP vs LIVE ({N_BOOT} resamples, {len(P)} sessions, exposure-matched) --")
for lab in DEEP:
    a, b = SERIES[lab], SERIES['LIVE']
    la, sa = stats(a); lb, sb = stats(b)
    say(f"  {lab} (point {(la-lb)*100:+.2f}pp/yr, {sa-sb:+.3f} Sharpe)")
    RES[lab]['boot'] = {}
    for blk in (20, 60):
        l1, l2, pl, s1, s2, ps = boot(a, b, blk, seed=hash((lab, blk)) & 0xffff)
        RES[lab]['boot'][blk] = (l1, l2, pl, s1, s2, ps)
        say(f"     block {blk:>2}d: logret [{l1*100:+.2f},{l2*100:+.2f}]pp P(<=0)={pl:.3f} | "
            f"Sharpe [{s1:+.3f},{s2:+.3f}] P(<=0)={ps:.3f}")

say(f"\n-- 5b. LEAVE-ONE-REGIME-OUT (Sharpe diff vs live, exposure-matched) --")
for lab in DEEP:
    out = []
    for rlab, a0, b0 in REGIMES:
        keep = [i for i, r in enumerate(P) if not (a0 <= r['d'] <= b0)]
        _, sa = stats([SERIES[lab][i] for i in keep]); _, sb = stats([SERIES['LIVE'][i] for i in keep])
        out.append((rlab, sa - sb))
    RES[lab]['loro'] = out
    say(f"  {lab:<20} " + "  ".join(f"drop {rl.split()[0]:<8}{d:+.3f}" for rl, d in out))

say(f"\n-- 5c. PLACEBO / LEVEL-ONLY CONTROL (T re-calibrated each time) --")
say("  placebo: fast leg replaced by cc30 x (fast/cc30 ratio block-permuted, 60d blocks) -- keeps the")
say("  level and distribution of the fast leg but destroys its timing. level-only: fast leg = cc10 x")
say("  mean(fast/cc10), i.e. live's own fast leg shifted to the range estimator's level.")
for lab in DEEP:
    keys = RES[lab]['keys']
    if len(keys) != 2:
        say(f"  {lab}: single estimator -- placebo = block-permuted ratio to cc30, level-only = cc30 x mean ratio")
        fast, slow = keys[0], 'cc30'; single = True
    else:
        fast, slow = keys; single = False
    ratio = [r[fast] / r[slow] for r in P]
    plac = []
    for seed in range(5):
        rng = random.Random(seed); n = len(P); blk = 60
        perm = []
        while len(perm) < n:
            s = rng.randrange(n); perm.extend(ratio[(s + k) % n] for k in range(blk))
        pk = f'_pl_{fast}'
        for r, x in zip(P, perm[:n]): r[pk] = r[slow] * x
        for r in Pr: r[pk] = r[slow]   # real rows not used here
        kk = (pk,) if single else (pk, slow)
        T = calib(kk, base_exp); ev = evaluate(P, mk(kk, T))
        plac.append((ev['sharpe'], ev['s_sharpe'], ev['h_sharpe']))
    # level-only
    ref = 'cc10'
    c = mean([r[fast] for r in P]) / mean([r[ref] for r in P])
    lk = f'_lv_{fast}'
    for r in P: r[lk] = r[ref] * c
    for r in Pr: r[lk] = r[ref] * c
    kk = (lk,) if single else (lk, slow)
    T = calib(kk, base_exp); evl = evaluate(P, mk(kk, T))
    m = RES[lab]['matched']['ev']
    RES[lab]['placebo'] = dict(plac=plac, level=(evl['sharpe'], evl['s_sharpe'], evl['h_sharpe']), level_c=c)
    say(f"  {lab:<20} real: {m['sharpe']:.3f} S {m['s_sharpe']:.3f} H {m['h_sharpe']:.3f} | "
        f"placebo mean of 5: {mean([p[0] for p in plac]):.3f} S {mean([p[1] for p in plac]):.3f} H {mean([p[2] for p in plac]):.3f} "
        f"(range {min(p[0] for p in plac):.3f}..{max(p[0] for p in plac):.3f}) | "
        f"level-only (x{c:.3f}): {evl['sharpe']:.3f} S {evl['s_sharpe']:.3f} H {evl['h_sharpe']:.3f} | live {base['sharpe']:.3f}")

# ======================= 6. real DAILY drift-band harness (vol_estimator_daily)
say(f"\n== 6. REAL DAILY (SPMO/TQQQ/QLD/XLU/BOXX, drift band, needs_rebalance) -- vol_estimator_daily.py loop, estimator injected")
ns = {}
code = open('paper-track/vol_estimator_daily.py').read().split('print("real DAILY')[0]
exec(code, ns)
days = ns['days']; dyrs = len(days) / A
def daily(keys, T, cost=0.0004):
    ns['V30'] = {d: max(SER[k][d] for k in keys) for d in days}
    ns['V10'] = {d: None for d in days}
    ns['VOL_TARGET_PA'] = T
    out, nreb, turn = ns['simulate']('live', cost)
    c, sh, m, by = ns['stats'](out)
    return dict(cagr=c, sharpe=sh, mdd=m, reb=nreb / dyrs, turn=turn / dyrs,
                expo=None, by=by, rets=[x for _, x in out])
say(f"  {len(days)} sessions {days[0]}..{days[-1]}")
say(f"  {'variant':<20}{'T':>6}{'CAGR':>7}{'Sharpe':>8}{'MDD':>7}{'reb/yr':>7}{'turn/yr':>8}   at 10bp Sharpe   20bp Sharpe")
DL = daily(FAM['LIVE max(cc10,cc30)'], VOL_TARGET_PA)
d10 = daily(FAM['LIVE max(cc10,cc30)'], VOL_TARGET_PA, 0.0010); d20 = daily(FAM['LIVE max(cc10,cc30)'], VOL_TARGET_PA, 0.0020)
say(f"  {'LIVE':<20}{VOL_TARGET_PA:6.3f}{DL['cagr']*100:6.2f}%{DL['sharpe']:8.3f}{DL['mdd']*100:6.1f}%{DL['reb']:7.0f}{DL['turn']:8.1f}x   {d10['sharpe']:.3f}          {d20['sharpe']:.3f}")
RES['LIVE max(cc10,cc30)']['daily'] = DL
for lab in DEEP:
    T = RES[lab]['matched']['T']; keys = RES[lab]['keys']
    D = daily(keys, T); D10 = daily(keys, T, 0.0010); D20 = daily(keys, T, 0.0020)
    # also at its own exposure-matched T on the daily rows? report the proxy T* -- same rule end to end
    RES[lab]['daily'] = D
    say(f"  {lab:<20}{T:6.3f}{D['cagr']*100:6.2f}%{D['sharpe']:8.3f}{D['mdd']*100:6.1f}%{D['reb']:7.0f}{D['turn']:8.1f}x   {D10['sharpe']:.3f}          {D20['sharpe']:.3f}")
    a, b = D['rets'], DL['rets']
    la, sa = stats(a); lb, sb = stats(b)
    for blk in (20, 60):
        l1, l2, pl, s1, s2, ps = boot(a, b, blk, seed=hash((lab, 'daily', blk)) & 0xffff)
        say(f"     vs live: point {(la-lb)*100:+.2f}pp/yr {sa-sb:+.3f} Sh | block {blk}d logret [{l1*100:+.2f},{l2*100:+.2f}] P(<=0)={pl:.3f} Sharpe [{s1:+.3f},{s2:+.3f}] P(<=0)={ps:.3f}")
    say("     by year: " + " ".join(f"{y[2:]}:{math.expm1(D['by'][y])*100:+.0f}/{math.expm1(DL['by'][y])*100:+.0f}" for y in sorted(D['by'])))

# ============================================================ 7. by-year table
say(f"\n== 7. PROXY BY-YEAR (candidate / live), exposure-matched")
def byyear(rets):
    by = {}
    for r, x in zip(P, rets): by[r['d'][:4]] = by.get(r['d'][:4], 0) + math.log1p(x)
    return {y: math.expm1(v) for y, v in by.items()}
BYL = byyear(SERIES['LIVE'])
for lab in DEEP:
    BY = byyear(SERIES[lab])
    say(f"  {lab:<20} " + " ".join(f"{y[2:]}:{BY[y]*100:+.0f}/{BYL[y]*100:+.0f}" for y in sorted(BY)))

# ============================================================ 8. save
def clean(x):
    if isinstance(x, dict): return {str(k): clean(v) for k, v in x.items() if k != 'rets'}
    if isinstance(x, (list, tuple)): return [clean(v) for v in x]
    return x
json.dump(dict(ncand=NCAND, base=base, baser=baser, base_exp=base_exp, diag=DIAG, res=clean(RES), deep=DEEP,
               surv=surv, surv_real=surv_real),
          open('/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/range_vol_results.json', 'w'), indent=1, default=str)
say(f"\ndone in {time.time()-T0:.0f}s; candidates tested: {NCAND}")

# ============ 8. WHY a better forecaster does not help: bite-region diagnostics
say(f"\n== 8. WHERE THE OVERLAY BITES: forecast quality when vol > T, and yearly exposure on the divergent years")
def rmse_corr(pairs):
    return (math.sqrt(mean([(L(x) - L(f)) ** 2 for x, f in pairs])),
            corr([L(x) for x, _ in pairs], [L(f) for _, f in pairs]))
say(f"  {'series':<16}{'n bite':>7}{'RMSE bite':>10}{'corr bite':>10}{'RMSE calm':>10}{'corr calm':>10}   (bite = forward-20d cc vol > 0.20)")
for lab, keys in [('live', ('cc10', 'cc30')), ('cc30', ('cc30',)), ('cc10', ('cc10',)), ('GK10', ('GK10',)), ('YZ10', ('YZ10',)),
                  ('GKJ10', ('GKJ10',)), ('max(GK5,GK30)', ('GK5', 'GK30')), ('max(GK10,cc30)', ('GK10', 'cc30')), ('bcGK10', ('bcGK10',))]:
    pr = [(max(r[k] for k in keys), FWD[r['d']]) for r in P if FWD[r['d']]]
    bite = [p for p in pr if p[1] > 0.20]; calm = [p for p in pr if p[1] <= 0.20]
    rb, cb = rmse_corr(bite); rc, cc_ = rmse_corr(calm)
    say(f"  {lab:<16}{len(bite):7d}{rb:10.3f}{cb:10.3f}{rc:10.3f}{cc_:10.3f}")
# under-reaction on gap days: mean multiplier on the 5% worst QQQ days, day-of and next day
say("\n  average vol-target multiplier min(1,T/v) on the 5% WORST QQQ close-to-close days (d0), and the day after:")
worst = sorted(P, key=lambda r: r['qqq'])[:int(0.05 * len(P))]
ixP = {r['d']: i for i, r in enumerate(P)}
for lab in ['LIVE max(cc10,cc30)', 'max(GK5,GK30)', 'GK10', 'max(GK10,cc30)', 'max(GKJ5,cc30)']:
    keys = RES[lab]['keys']; T = RES[lab]['matched']['T']
    m0 = mean([min(1.0, T / max(r[k] for k in keys)) for r in worst])
    m1 = mean([min(1.0, T / max(P[ixP[r['d']] + 1][k] for k in keys)) for r in worst if ixP[r['d']] + 1 < len(P)])
    say(f"    {lab:<20} T*={T:.3f}  multiplier day-of {m0:.3f}  next day {m1:.3f}")
say("\n  yearly average exposure, candidate / live (exposure-matched over the whole proxy):")
def yexp(fn):
    by = {}; cnt = {}
    for r in P:
        y = r['d'][:4]; by[y] = by.get(y, 0) + sum(fn(r)[:4]); cnt[y] = cnt.get(y, 0) + 1
    return {y: by[y] / cnt[y] for y in by}
EL = yexp(live_fn)
for lab in DEEP[:1] + ['GK10', 'max(GK10,cc30)']:
    E = yexp(mk(RES[lab]['keys'], RES[lab]['matched']['T']))
    say(f"    {lab:<16} " + " ".join(f"{y[2:]}:{E[y]*100:.0f}/{EL[y]*100:.0f}" for y in sorted(E)))
