"""RESEARCH LINE `rates_signal` (2026-09-10): does the RATES COMPLEX add anything
to the regime signal?  Research only -- nothing here is applied.

Motivation: an outside discretionary manager downgraded on 2026-09-09 citing
~2/3 odds of a September hike, a rising 10y yield and oil at a May high. No
prediction-market history exists, so CAUSAL market proxies with 2000-2026
coverage are used instead, all from FRED (data/<id>.csv, provenance in
data/README.md and research_notes/rates_signal.md):
  DGS2 (2y yield: cleanest hike-odds proxy), DGS10, T10Y2Y (10y-2y slope),
  DFII10 (10y TIPS real yield, 2003+), DCOILWTICO (WTI), DGS3MO.

Nine signals, each a daily value known at d0's close (FRED dates a value by
its observation day; it is PUBLISHED the next morning, so a one-day-lag
version is shown for anything that looks positive):
  dgs2_20, dgs2_60, dgs10_20, dgs10_60  : 20/60-session change in the yield
  slope_lvl, slope_60                    : 10y-2y level and 60-session change
  dfii10_20, dfii10_60                   : 20/60-session change in real yield
  oil_60                                 : 60-session change in log WTI
Each is turned into a TRAILING-252-session percentile (causal, never a
full-sample constant). "Top quintile" = pct >= 0.8, "bottom" = pct <= 0.2.

Variants (both signs: HI = top-quintile risk-off, i.e. rates rising fast is
bad; LO = bottom-quintile risk-off, i.e. rates falling fast is bad, as in
2001/2008/2020 -- the LO family IS the sign-flip placebo of the HI family):
  delever25 / delever50 : risky legs x0.75 / x0.50 while in the quintile
  vote                  : one extra extension-trim vote (eff A only, like the trim)
  block                 : the 20/100 fast re-entry overlay is not applied while in
                          the quintile (eff falls back to the macro state)
  tilt25 / tilt50       : risky legs x clip(1 - k*2*(pct-0.5), 1-k, 1) [HI] or
                          the mirror [LO], with the vol-target constant T
                          re-calibrated by bisection so average deployed exposure
                          matches LIVE on the same rows (exposure control by
                          construction; the cap 1.0 still never levers up).
6 variants x 2 signs x 9 series = 108 candidates.

Harness discipline (BRIEFING.md + ADDENDUM 2026-09-10): every figure via the
project's own run / evaluate / RF.eval_real; the LIVE weight function is
W[eff] -> extension_scale -> vt(w, r['vol']) with the PLAIN 30d estimator and
band 0.05; standing figures reproduced first; SAME ROWS (DFII10 variants and
their live baseline are restricted to rows where the signal exists); exposure
control (scaled live_fn, k bisected to the candidate's exposure) on EVERY candidate; circular block
bootstrap 20/60d x 2000 draws vs the exposure-matched live series for the best
variant per series; leave-one-regime-out; real weekly SPMO rows via RF.eval_real.
Usage (from the repo root): python3 paper-track/rates_signal.py <series ...>   (sweep + deep
controls for those series, results saved as JSON in the scratchpad), then
python3 paper-track/rates_signal.py summary   (aggregate tables + candidate count).
No arguments = all nine series in one invocation (~25 min).
"""
import sys, math, statistics, time
sys.path.insert(0, 'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from state import extension_scale, extension_votes, EXTENSION_STEP, VOL_TARGET_PA
from improvement_search import SEARCH, HOLDOUT, era
from improvement_search_r2 import scaled
from block_bootstrap import boot, stats, N_BOOT, REGIMES

T0 = time.time()
def log(*a):
    print(*a, flush=True)

# ------------------------------------------------------------------ data
def fred(p):
    """FRED csv -> {date: value}; holiday blanks FORWARD-FILLED, never dropped."""
    out, last = {}, None
    for ln in open(p).read().splitlines()[1:]:
        d, v = ln.split(',')
        if v.strip():
            last = float(v)
        if last is not None:
            out[d] = last
    return out

F = {k: fred(f'data/{k.lower()}.csv') for k in ('DGS2', 'DGS10', 'T10Y2Y', 'DFII10', 'DCOILWTICO')}
for k, v in F.items():
    ks = sorted(v)
    log(f"  {k:<10} {ks[0]} .. {ks[-1]}  ({len(ks)} rows)")

def on_calendar(series, dates):
    """Value known at the close of each QQQ session: last FRED observation dated <= d."""
    sk = sorted(series); out = {}; j = 0; last = None
    for d in dates:
        while j < len(sk) and sk[j] <= d:
            last = series[sk[j]]; j += 1
        out[d] = last
    return out

# Changes and trailing percentiles are computed on each FRED series' OWN business-day
# calendar (forward-filled), then mapped to QQQ sessions as the last value dated <= d0.
# This gives full 2000-07 coverage for every series except DFII10 (starts 2003-01).
def chg(k, n, logv=False):
    v = F[k]; ks = sorted(v); out = {}
    for i, d in enumerate(ks):
        if i < n:
            continue
        a, b = v[ks[i - n]], v[d]
        out[d] = (math.log(max(b, 1.0)) - math.log(max(a, 1.0))) if logv else (b - a)  # WTI printed -37.63 on 2020-04-20: floor at $1
    return out

RAW = {
    'dgs2_20':   chg('DGS2', 20),   'dgs2_60':   chg('DGS2', 60),
    'dgs10_20':  chg('DGS10', 20),  'dgs10_60':  chg('DGS10', 60),
    'slope_lvl': dict(F['T10Y2Y']), 'slope_60': chg('T10Y2Y', 60),
    'dfii10_20': chg('DFII10', 20), 'dfii10_60': chg('DFII10', 60),
    'oil_60':    chg('DCOILWTICO', 60, logv=True),
}
NAMES = list(RAW)
WIN = 252

def trailing_pct(raw):
    """pct[d] = share of the trailing WIN observations (incl. today) <= today's value, on the series' own calendar."""
    out = {}; buf = []
    for d in sorted(raw):
        x = raw[d]; buf.append(x)
        if len(buf) > WIN: buf.pop(0)
        if len(buf) == WIN: out[d] = sum(1 for y in buf if y <= x) / len(buf)
    return out

PCT = {n: on_calendar(trailing_pct(RAW[n]), ds) for n in NAMES}
CAL = {k: on_calendar(v, ds) for k, v in F.items()}   # levels on the QQQ calendar, for the alignment check
dix = {d: i for i, d in enumerate(ds)}
PCT_LAG = {n: {d: (PCT[n][ds[dix[d] - 1]] if dix[d] > 0 else None) for d in ds} for n in NAMES}

for r in rows:
    r['pct'] = {n: PCT[n][r['d']] for n in NAMES}
    r['pctlag'] = {n: PCT_LAG[n][r['d']] for n in NAMES}
def nearest_on_or_before(d):
    # rr d0 are QQQ sessions in practice; fall back to the previous session if not
    if d in dix: return d
    c = [x for x in ds if x <= d]
    return c[-1] if c else None
for r in rr:
    d = nearest_on_or_before(r['d0'])
    r['pct'] = {n: (PCT[n][d] if d else None) for n in NAMES}
    r['pctlag'] = {n: (PCT_LAG[n][d] if d else None) for n in NAMES}

# ------------------------------------------------------------------ live design
def trimmed(r, eff=None):
    eff = eff or r['eff']
    w = W[eff]; f = extension_scale(eff, r['gaps'])
    if f < 1: w = tuple(a * f for a in w[:4]) + (1 - f * sum(w[:4]),)
    return w

def live_fn(r):
    return vt(trimmed(r), r['vol'])
def live_rr(r):
    return RF.vt(trimmed(r), r['vol'])

ev0 = evaluate(rows, live_fn); er0 = RF.eval_real(rr, live_rr)
log('STANDING LIVE FIGURES (must match ADDENDUM: 22.18% / 0.913 / -33.6%, S 1.103, H 0.768; real 31.40% / 1.248 / -25.0%)')
log(f"  26y proxy {ev0['cagr']*100:.2f}% / {ev0['sharpe']:.3f} / {ev0['mdd']*100:.1f}%  S {ev0['s_sharpe']:.3f}  H {ev0['h_sharpe']:.3f}"
    f"  exposure {ev0['risky']:.4f} | real weekly {er0['cagr']*100:.2f}% / {er0['sharpe']:.3f} / {er0['mdd']*100:.1f}%  ({len(rows)} proxy rows, {len(rr)} real rows)")
assert abs(ev0['sharpe'] - 0.913) < 0.002 and abs(er0['sharpe'] - 1.248) < 0.002, 'standing figures not reproduced'

# alignment sanity (contemporaneous d0->d1): QQQ return vs same-window yield / oil change
def corr_contemp(k, logv=False):
    xs, ys = [], []
    v = CAL[k]
    for i in range(1, len(ds)):
        a, b = v[ds[i-1]], v[ds[i]]
        if a and b and a != b:
            xs.append(px[ds[i]] / px[ds[i-1]] - 1); ys.append((math.log(max(b, 1.0)) - math.log(max(a, 1.0))) if logv else (b - a))
    return statistics.correlation(xs, ys), len(xs)
log('  alignment (contemporaneous d0->d1 QQQ return vs change): '
    + '  '.join(f"{k} {corr_contemp(k, k=='DCOILWTICO')[0]:+.3f}" for k in ('DGS2', 'DGS10', 'DCOILWTICO')))
# predictive pairing check: signal at d0 vs QQQ d0->d1 -- should be ~0
log('  predictive (signal pct at d0 vs QQQ d0->d1 return): '
    + '  '.join(f"{n} {statistics.correlation([r['pct'][n] for r in rows if r['pct'][n] is not None], [r['legs'][0] for r in rows if r['pct'][n] is not None]):+.3f}" for n in ('dgs2_20', 'dgs10_60', 'oil_60')))

# ------------------------------------------------------------------ signal descriptives + mechanism
log('\nSIGNAL COVERAGE AND MECHANISM (forward 20-session QQQ log return, annualized, and forward 20d realized vol, by trailing quintile)')
log(f"{'signal':<10} {'first row':<11} {'rows':>5} | {'era':<7} {'bottom<=0.2':>14} {'middle':>12} {'top>=0.8':>12}  (fwd ret %/yr | fwd vol %)  n_top")
fwd = {}; fvol = {}
lp = [math.log(px[d]) for d in ds]
for i, d in enumerate(ds):
    if i + 20 < len(ds):
        fwd[d] = (lp[i+20] - lp[i]) * 252 / 20
        rs = [lp[j+1] - lp[j] for j in range(i, i+20)]
        fvol[d] = statistics.pstdev(rs) * math.sqrt(252)
    else:
        fwd[d] = fvol[d] = None
FIRST = {}
for n in NAMES:
    P = [r for r in rows if r['pct'][n] is not None]; FIRST[n] = P[0]['d']
    for elab, lo, hi in (('HOLDOUT', *HOLDOUT), ('SEARCH', *SEARCH), ('ALL', '0000', '9999')):
        Q = [r for r in P if lo <= r['d'] <= hi and fwd[r['d']] is not None]
        b = {'bottom': [], 'middle': [], 'top': []}
        for r in Q:
            p = r['pct'][n]; k = 'bottom' if p <= 0.2 else ('top' if p >= 0.8 else 'middle')
            b[k].append(r['d'])
        f = lambda k: f"{statistics.mean(fwd[d] for d in b[k])*100:+6.1f} | {statistics.mean(fvol[d] for d in b[k])*100:4.1f}"
        log(f"{n if elab=='HOLDOUT' else '':<10} {FIRST[n] if elab=='HOLDOUT' else '':<11} {len(P) if elab=='HOLDOUT' else '':>5} | {elab:<7} {f('bottom'):>14} {f('middle'):>12} {f('top'):>12}   {len(b['top'])}")

# ------------------------------------------------------------------ candidate weight functions
def make(kind, sign, name, vtf=vt, T=VOL_TARGET_PA, lag=False):
    key = 'pctlag' if lag else 'pct'
    def inq(r):
        p = r[key][name]
        return p is not None and ((p >= 0.8) if sign == 'HI' else (p <= 0.2))
    if kind == 'delever25' or kind == 'delever50':
        s = 0.75 if kind == 'delever25' else 0.50
        def fn(r):
            w = trimmed(r)
            if inq(r): w = tuple(a * s for a in w[:4]) + (1 - s * sum(w[:4]),)
            return vtf(w, r['vol'], T)
    elif kind == 'vote':
        def fn(r):
            eff = r['eff']; v = extension_votes(eff, r['gaps'])
            if inq(r) and eff == 'A': v = min(3, v + 1)
            f = 1.0 - EXTENSION_STEP * v; w = W[eff]
            if f < 1: w = tuple(a * f for a in w[:4]) + (1 - f * sum(w[:4]),)
            return vtf(w, r['vol'], T)
    elif kind == 'block':
        def fn(r):
            eff = r['state'] if inq(r) else r['eff']
            return vtf(trimmed(r, eff), r['vol'], T)
    elif kind in ('tilt25', 'tilt50'):
        k = 0.25 if kind == 'tilt25' else 0.50
        def fn(r):
            w = trimmed(r); p = r[key][name]
            if p is not None:
                x = (p - 0.5) if sign == 'HI' else (0.5 - p)
                s = min(1.0, max(1.0 - k, 1.0 - k * 2 * x))
                w = tuple(a * s for a in w[:4]) + (1 - s * sum(w[:4]),)
            return vtf(w, r['vol'], T)
    else:
        raise ValueError(kind)
    return fn

def calib_T(P, kind, sign, name, target_exp, lag=False, lo=0.02, hi=4.0):
    for _ in range(50):
        mid = (lo + hi) / 2
        if run(P, make(kind, sign, name, T=mid, lag=lag))[1] < target_exp: lo = mid
        else: hi = mid
    return (lo + hi) / 2

def exposure_control(P, target_exp, tol=0.002):
    """Exposure-matched LIVE control: scaled(live_fn, k) with k bisected until average
    deployed capital equals the candidate's. NOT downturn_review.exposure_control -- that
    helper's internal baseline is downturn_review.live() = vt(W[r['state']], vol), the
    MACRO-ONLY design with neither the fast overlay nor the extension trim (checked
    2026-09-10: it reads 0.751 at k=0.845 where the true live design reads ~0.91), so it
    flatters every candidate, placebo included, by ~+0.15 Sharpe."""
    lo, hi = 0.0, 1.0
    while run(P, scaled(live_fn, hi))[1] < target_exp and hi < 8.0:
        lo, hi = hi, hi * 2
    for _ in range(40):
        mid = (lo + hi) / 2
        if run(P, scaled(live_fn, mid))[1] < target_exp: lo = mid
        else: hi = mid
    k = (lo + hi) / 2
    ev = evaluate(P, scaled(live_fn, k)); ev['exp_achieved'] = run(P, scaled(live_fn, k))[1]
    ev['exp_matched'] = abs(ev['exp_achieved'] - target_exp) <= tol; ev['k'] = k
    return k, ev

KINDS = ('delever25', 'delever50', 'vote', 'block', 'tilt25', 'tilt50')
SIGNS = ('HI', 'LO')

# ------------------------------------------------------------------ sweep (per invocation: the series named on the command line)
import json, os
OUT = '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad'
os.makedirs(OUT, exist_ok=True)
ARGS = sys.argv[1:]
MODE = 'summary' if ARGS == ['summary'] else 'sweep'
TODO = NAMES if not ARGS else [a for a in ARGS if a in NAMES]
NCAND = len(NAMES) * len(SIGNS) * len(KINDS)
log(f"\nSWEEP: {len(NAMES)} series x {len(SIGNS)} signs x {len(KINDS)} variants = {NCAND} candidates total; this invocation: {TODO if MODE=='sweep' else 'summary of saved results'}")
log("Columns: candidate Sharpe on full window / search / holdout / real, minus the LIVE baseline on the SAME rows; "
    "'xm' = candidate minus the EXPOSURE-MATCHED live (proxy full-window Sharpe); exp = avg deployed capital; frac = share of rows in the quintile")

def sweep_series(n):
    P = [r for r in rows if r['pct'][n] is not None]; Pr = [r for r in rr if r['pct'][n] is not None]
    evb = evaluate(P, live_fn); erb = RF.eval_real(Pr, live_rr); base_exp = evb['risky']
    log(f"\n--- {n}: {len(P)} proxy rows from {P[0]['d']}, {len(Pr)} real rows | LIVE on these rows: "
        f"{evb['cagr']*100:.2f}% / {evb['sharpe']:.3f} / {evb['mdd']*100:.1f}%  S {evb['s_sharpe']:.3f} H {evb['h_sharpe']:.3f} exp {base_exp:.3f} | real {erb['sharpe']:.3f}")
    log(f"{'variant':<16}{'frac':>6}{'exp':>7}{'CAGR':>8}{'Sharpe':>8}{'MDD':>7}{'dS_full':>9}{'dS_srch':>9}{'dS_hold':>9}{'dS_real':>9}{'xm':>8}{'both':>6}{'T*':>7}")
    RES = {}; SER = {}
    for sign in SIGNS:
        frac = sum(1 for r in P if (r['pct'][n] >= 0.8 if sign == 'HI' else r['pct'][n] <= 0.2)) / len(P)
        for kind in KINDS:
            T = VOL_TARGET_PA
            if kind.startswith('tilt'):
                T = calib_T(P, kind, sign, n, base_exp)
            fn = make(kind, sign, n, T=T); fnr = make(kind, sign, n, vtf=RF.vt, T=T)
            ev = evaluate(P, fn); er = RF.eval_real(Pr, fnr)
            rets, expo = run(P, fn); SER[(sign, kind)] = rets
            k, evx = exposure_control(P, expo)
            both = ev['s_sharpe'] > evb['s_sharpe'] and ev['h_sharpe'] > evb['h_sharpe']
            R = dict(series=n, sign=sign, kind=kind, sharpe=ev['sharpe'], cagr=ev['cagr'], mdd=ev['mdd'], real_sharpe=er['sharpe'], real_mdd=er['mdd'],
                     expo=expo, k=k, xm_sharpe=evx['sharpe'], exp_matched=evx['exp_matched'], exp_achieved=evx['exp_achieved'], both=both, T=T, frac=frac,
                     xm=ev['sharpe'] - evx['sharpe'], dfull=ev['sharpe'] - evb['sharpe'],
                     ds=ev['s_sharpe'] - evb['s_sharpe'], dh=ev['h_sharpe'] - evb['h_sharpe'], dr=er['sharpe'] - erb['sharpe'])
            RES[(sign, kind)] = R
            log(f"{sign+' '+kind:<16}{frac:6.2f}{expo:7.3f}{ev['cagr']*100:8.2f}{ev['sharpe']:8.3f}{ev['mdd']*100:7.1f}"
                f"{R['dfull']:+9.3f}{R['ds']:+9.3f}{R['dh']:+9.3f}{R['dr']:+9.3f}{R['xm']:+8.3f}{'YES' if both else '':>6}"
                f"{T:7.3f}{'' if evx['exp_matched'] else '  (exp ctl unmatched: '+format(evx['exp_achieved'],'.3f')+')'}")
    log(f"  [{time.time()-T0:.0f}s]")

    # ---- deep controls on the best variant (by Sharpe vs exposure-matched live, full window)
    best = max(RES, key=lambda c: RES[c]['xm']); sign, kind = best; R = RES[best]
    flip = ('LO' if sign == 'HI' else 'HI', kind); Rf = RES[flip]
    log(f"\n== {n}: best = {sign} {kind}   Sharpe {R['sharpe']:.3f} vs exposure-matched live {R['xm_sharpe']:.3f} (k={R['k']:.3f}) -> {R['xm']:+.3f};"
        f"  dS search {R['ds']:+.3f} holdout {R['dh']:+.3f} real {R['dr']:+.3f}  both={'YES' if R['both'] else 'no'}")
    log(f"   sign-flip placebo ({flip[0]} {kind}): xm {Rf['xm']:+.3f}  dS search {Rf['ds']:+.3f} holdout {Rf['dh']:+.3f} real {Rf['dr']:+.3f}"
        f"  -> {'placebo LOSES (consistent with a real signal)' if Rf['xm'] < R['xm'] else 'placebo does NOT lose'}")
    a = SER[best]; b = run(P, scaled(live_fn, R['k']))[0]
    la, sa = stats(a); lb, sb = stats(b)
    log(f"   point estimate vs exposure-matched live: {(la-lb)*100:+.2f} pp/yr log-return, {sa-sb:+.3f} Sharpe")
    deep = dict(best=[sign, kind], boot={}, loro={}, placebo=dict(xm=Rf['xm'], ds=Rf['ds'], dh=Rf['dh'], dr=Rf['dr']))
    for blk in (20, 60):
        l1, l2, pl, s1, s2, ps = boot(a, b, blk, seed=(hash((n, sign, kind, blk)) & 0xffff))
        deep['boot'][blk] = [l1, l2, pl, s1, s2, ps]
        log(f"   block {blk:>2}d: log-return 95% CI [{l1*100:+.2f}, {l2*100:+.2f}] pp/yr P(<=0)={pl:.3f}   Sharpe 95% CI [{s1:+.3f}, {s2:+.3f}] P(<=0)={ps:.3f}")
    log('   leave-one-regime-out (Sharpe / log-return delta vs exposure-matched live):')
    for rlab, a0, b0 in REGIMES:
        keep = [i for i, r in enumerate(P) if not (a0 <= r['d'] <= b0)]
        if len(keep) == len(P):
            log(f"      drop {rlab:<24} (regime outside this series' window)"); continue
        ca = [a[i] for i in keep]; cb = [b[i] for i in keep]
        la2, sa2 = stats(ca); lb2, sb2 = stats(cb); deep['loro'][rlab] = [sa2 - sb2, la2 - lb2]
        log(f"      drop {rlab:<24} Sharpe {sa2-sb2:+.3f}   log-return {(la2-lb2)*100:+.2f} pp/yr")
    Pl = [r for r in P if r['pctlag'][n] is not None]; Prl = [r for r in Pr if r['pctlag'][n] is not None]
    T = calib_T(Pl, kind, sign, n, run(Pl, live_fn)[1], lag=True) if kind.startswith('tilt') else VOL_TARGET_PA
    fn = make(kind, sign, n, T=T, lag=True); evl = evaluate(Pl, fn); erl = RF.eval_real(Prl, make(kind, sign, n, vtf=RF.vt, T=T, lag=True))
    evbl = evaluate(Pl, live_fn); erbl = RF.eval_real(Prl, live_rr)
    kl, evxl = exposure_control(Pl, run(Pl, fn)[1])
    deep['lag'] = dict(xm=evl['sharpe'] - evxl['sharpe'], ds=evl['s_sharpe'] - evbl['s_sharpe'], dh=evl['h_sharpe'] - evbl['h_sharpe'], dr=erl['sharpe'] - erbl['sharpe'])
    log(f"   one-day lag: Sharpe {evl['sharpe']:.3f} vs exp-matched live {evxl['sharpe']:.3f} -> {deep['lag']['xm']:+.3f};"
        f"  dS search {deep['lag']['ds']:+.3f} holdout {deep['lag']['dh']:+.3f} real {deep['lag']['dr']:+.3f}")
    log(f"   [{time.time()-T0:.0f}s]")
    json.dump(dict(series=n, first=P[0]['d'], nrows=len(P), nreal=len(Pr), base=dict(sharpe=evb['sharpe'], s=evb['s_sharpe'], h=evb['h_sharpe'], exp=base_exp, real=erb['sharpe']),
                   res=list(RES.values()), deep=deep), open(f'{OUT}/rates_signal_{n}.json', 'w'))

if MODE == 'sweep':
    for n in TODO:
        sweep_series(n)

# ------------------------------------------------------------------ summary over every saved series
if MODE == 'summary':
    ALL = []
    for n in NAMES:
        f = f'{OUT}/rates_signal_{n}.json'
        if os.path.exists(f): ALL.append(json.load(open(f)))
    RES = [R for J in ALL for R in J['res']]
    log(f"\nSWEEP SUMMARY over {len(ALL)} series ({len(RES)} of {NCAND} candidates evaluated)")
    def cnt(f): return sum(1 for R in RES if f(R))
    log(f"  beat live on BOTH eras (raw Sharpe): {cnt(lambda R: R['both'])}")
    log(f"  beat live on both eras AND beat exposure-matched live on full window: {cnt(lambda R: R['both'] and R['xm'] > 0)}")
    log(f"  ... AND beat live on real rows: {cnt(lambda R: R['both'] and R['xm'] > 0 and R['dr'] > 0)}")
    log(f"  full-window Sharpe delta vs exposure-matched live: mean {statistics.mean(R['xm'] for R in RES):+.4f}, "
        f"max {max(R['xm'] for R in RES):+.4f}, min {min(R['xm'] for R in RES):+.4f}; exposure control unmatched on {cnt(lambda R: not R['exp_matched'])} candidates")
    for sg in SIGNS:
        cs = [R for R in RES if R['sign'] == sg]
        log(f"  {sg} sign ({'rates rising fast = risk-off' if sg=='HI' else 'rates falling fast = risk-off'}): "
            f"{sum(1 for R in cs if R['both'] and R['xm'] > 0)} of {len(cs)} pass both-era + exposure control; mean xm {statistics.mean(R['xm'] for R in cs):+.4f}; "
            f"mean dS real {statistics.mean(R['dr'] for R in cs):+.4f}")
    for kd in KINDS:
        cs = [R for R in RES if R['kind'] == kd]
        log(f"  kind {kd:<10}: mean xm {statistics.mean(R['xm'] for R in cs):+.4f}, mean dS search {statistics.mean(R['ds'] for R in cs):+.4f}, holdout {statistics.mean(R['dh'] for R in cs):+.4f}, real {statistics.mean(R['dr'] for R in cs):+.4f}")
    log('\n  every candidate that beats live on both eras (raw), sorted by xm:')
    hdr = f"  {'candidate':<26}{'exp':>7}{'dS_full':>9}{'dS_srch':>9}{'dS_hold':>9}{'dS_real':>9}{'xm':>8}"
    log(hdr)
    for R in sorted(RES, key=lambda R: -R['xm']):
        if R['both']:
            log(f"  {R['series']+' '+R['sign']+' '+R['kind']:<26}{R['expo']:7.3f}{R['dfull']:+9.3f}{R['ds']:+9.3f}{R['dh']:+9.3f}{R['dr']:+9.3f}{R['xm']:+8.3f}")
    log('\n  top 10 by Sharpe vs exposure-matched live (full window):'); log(hdr)
    for R in sorted(RES, key=lambda R: -R['xm'])[:10]:
        log(f"  {R['series']+' '+R['sign']+' '+R['kind']:<26}{R['expo']:7.3f}{R['dfull']:+9.3f}{R['ds']:+9.3f}{R['dh']:+9.3f}{R['dr']:+9.3f}{R['xm']:+8.3f}{'  both' if R['both'] else ''}")
    log('\n  bottom 5 (worst):'); log(hdr)
    for R in sorted(RES, key=lambda R: R['xm'])[:5]:
        log(f"  {R['series']+' '+R['sign']+' '+R['kind']:<26}{R['expo']:7.3f}{R['dfull']:+9.3f}{R['ds']:+9.3f}{R['dh']:+9.3f}{R['dr']:+9.3f}{R['xm']:+8.3f}")
    log('\n  DEEP CONTROLS, best variant per series (vs exposure-matched live; boot = circular block bootstrap Sharpe 95% CI and P(<=0))')
    log(f"  {'series':<10}{'best':<16}{'xm':>7}{'srch':>7}{'hold':>7}{'real':>7}{'both':>5} | {'b20 CI':>17}{'P':>6} | {'b60 CI':>17}{'P':>6} | {'flip xm':>8} | {'lag xm':>7}{'lag S/H/R':>21} | LORO min..max")
    for J in ALL:
        D = J['deep']; bs, bk = D['best']; R = next(R for R in J['res'] if R['sign'] == bs and R['kind'] == bk)
        b20 = D['boot']['20']; b60 = D['boot']['60']; lo = [v[0] for v in D['loro'].values()]
        log(f"  {J['series']:<10}{bs+' '+bk:<16}{R['xm']:+7.3f}{R['ds']:+7.3f}{R['dh']:+7.3f}{R['dr']:+7.3f}{'Y' if R['both'] else 'n':>5} | "
            f"[{b20[3]:+.3f},{b20[4]:+.3f}]{b20[5]:6.3f} | [{b60[3]:+.3f},{b60[4]:+.3f}]{b60[5]:6.3f} | {D['placebo']['xm']:+8.3f} | "
            f"{D['lag']['xm']:+7.3f}  {D['lag']['ds']:+.3f}/{D['lag']['dh']:+.3f}/{D['lag']['dr']:+.3f} | {min(lo):+.3f}..{max(lo):+.3f}")

# ------------------------------------------------------------------ the 2026-09-09 reading
log('\nWHERE THE SIGNALS STAND NOW (trailing-252 percentile at the last proxy row and at the last FRED date)')
last = rows[-1]['d']
log(f"  last proxy row {last}: " + '  '.join(f"{n} {rows[-1]['pct'][n]:.2f}" for n in NAMES))
for k in F:
    ks = sorted(F[k]); log(f"  {k:<10} {ks[-1]} = {F[k][ks[-1]]:.2f}   (60 obs earlier {F[k][ks[-61]]:.2f}, 20 obs earlier {F[k][ks[-21]]:.2f})")
log(f"\nDONE in {time.time()-T0:.0f}s")
