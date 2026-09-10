"""Research line breadth_dgate_2000 (2026-09-10): does the post-hoc D-row breadth gate survive 2000-2002?

The breadth_signal line found, post hoc, that "effective state D AND the 60-day change of log(QQEW/QQQ) in its
trailing-252 bottom quintile -> hold the D row (100% QLD) in cash" passes every control on 2007-07+ rows.  QQEW starts
2006-04, so the dot-com bear was never tested.  This line
  1. tries to build a point-in-time equal-weight Nasdaq-100 from 1999 (result: ~30% price coverage in 2000-2002 on
     Yahoo, because delisted names are gone -> survivorship-biased, ILLUSTRATIVE ONLY, series 'ndxsurv');
  2. builds survivorship-free breadth fallbacks with full coverage (composite/NDX, Russell 2000/NDX, Russell 3000/NDX,
     NYSE Composite/NDX, Wilshire 5000/NDX), validates each against the real QQEW/QQQ series on the 2007-07+ rows
     (correlation, flag agreement, and -- the test that matters -- whether the D-gate reproduces the QQEW result);
  3. runs the full control set on the 2000-07+ rows for every fallback that validates;
  4. gives the verdict.

Research only.  Nothing is applied.  Harness: the project harness only (leverage_under_trim bootstrap -> rows, rr,
run, evaluate, RF.eval_real; block_bootstrap.boot/stats).  Run from the repo root:
    python3 paper-track/breadth_dgate_2000.py            (full, ~10 min)
    DGATE_STAGE=1 python3 ...                            (data + validation only)
Code paths for row attachment / trailing percentile / D-gate / constant-D control are copied verbatim from
paper-track/breadth_signal.py (which cannot be imported without re-running its whole search).
"""
import sys, os, math, csv, bisect, zlib
sys.path.insert(0, 'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from state import extension_scale, extension_votes, EXTENSION_STEP
from block_bootstrap import boot, stats, N_BOOT
from improvement_search import SEARCH, HOLDOUT, era
from long_history_backtest import load_px as _load_px
STAGE = int(os.environ.get('DGATE_STAGE', '9'))

print("=" * 112)
print("RESEARCH LINE breadth_dgate_2000 -- the D-row breadth gate extended to 2000-07 with survivorship-free proxies")
print("=" * 112)

# ------------------------------------------------------------------ 0. live design and standing figures
def live_w(r, vtf=vt):
    w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
    if f < 1: w = tuple(a * f for a in w[:4]) + (1 - f * sum(w[:4]),)
    return vtf(w, r['vol'])
LIVE = lambda r: live_w(r)
LIVE_R = lambda r: live_w(r, RF.vt)
def fmt(ev): return f"{ev['cagr']*100:5.2f}% / {ev['sharpe']:.3f} / {ev['mdd']*100:5.1f}%"
base_all = evaluate(rows, LIVE); real_all = RF.eval_real(rr, LIVE_R)
print(f"\nSTANDING FIGURES (must match briefing 22.18/0.913/-33.6, S 1.103 H 0.768; real 31.40/1.248/-25.0):")
print(f"  26y proxy {fmt(base_all)}  S {base_all['s_sharpe']:.3f} H {base_all['h_sharpe']:.3f}  exp {base_all['risky']*100:.1f}%"
      f" | real weekly {fmt(real_all)} | rows {len(rows)} {rows[0]['d']}..{rows[-1]['d']}, real rows {len(rr)}")
assert abs(base_all['sharpe'] - 0.913) < 0.002 and abs(real_all['sharpe'] - 1.248) < 0.002, "standing figures not reproduced"

# ------------------------------------------------------------------ 1. data
def load_dc(path):
    out = {}
    for r in csv.DictReader(open(path)):
        if r['c'] not in ('', '.'): out[r['d']] = float(r['c'])   # FRED holidays are empty: skipped here, forward-filled at lookup
    return out
qqqpx = px; spy = _load_px('data/spy_long_history.csv')
QQEW = load_dc('data/QQEW_daily.csv'); RSP = load_dc('data/RSP_daily.csv')
COMP = load_dc('data/nasdaqcom_fred.csv'); NDX = load_dc('data/nasdaq100_fred.csv')
YNDX = load_dc('data/NDX_index_daily.csv')
IDX = {s: load_dc(f'data/{s}_index_daily.csv') for s in ('RUT', 'RUA', 'NYA', 'W5000')}
SURV = load_dc('data/ndx_survivor_ew_daily.csv')
# spot-check Yahoo ^NDX against FRED NASDAQ100 (same index, two sources)
common = [d for d in YNDX if d in NDX and d >= '1999-01-01']
mx = max(abs(YNDX[d] / NDX[d] - 1) for d in common)
print(f"  Yahoo ^NDX vs FRED NASDAQ100: {len(common)} common dates, max abs rel diff {mx*100:.3f}% (FRED used as the NDX leg)")

class FF:
    """forward-fill lookup: last close at or before d."""
    def __init__(self, m):
        self.k = sorted(m); self.v = [m[d] for d in self.k]
    def at(self, d):
        i = bisect.bisect_right(self.k, d) - 1
        return self.v[i] if i >= 0 else None

# calendar: repo QQQ dates, extended BACK with NDX (FRED) sessions so the 60d change + 252d percentile exist by 2000-07,
# and FORWARD with Yahoo sessions for today's reading
cal = sorted(set(ds) | set(d for d in NDX if '1998-01-01' <= d < ds[0]) | set(d for d in YNDX if d > ds[-1]))
cix = {d: i for i, d in enumerate(cal)}

def ratio_series(num, den_map):
    """log(num/den) on cal, forward-filled; None before num exists."""
    f = FF(num); fd = FF(den_map); out = []
    for d in cal:
        a = f.at(d) if d >= f.k[0] else None; b = fd.at(d) if d >= fd.k[0] else None
        out.append(math.log(a / b) if (a and b) else None)
    return out
def diffs(lr, n):
    return [None if (i < n or lr[i] is None or lr[i - n] is None) else lr[i] - lr[i - n] for i in range(len(lr))]
def trailing_pct(v, n=252):
    out = [None] * len(v); win = []; hist = []
    for i, x in enumerate(v):
        if x is None: win = []; hist = []; continue
        bisect.insort(win, x); hist.append(x)
        if len(hist) > n: win.pop(bisect.bisect_left(win, hist.pop(0)))
        if len(win) == n:
            lo = bisect.bisect_left(win, x); hi = bisect.bisect_right(win, x)
            out[i] = (lo + 0.5 * (hi - lo)) / n
    return out

# survivor equal-weight NDX (illustrative) spliced onto QQEW from 2006-07-03 (levels matched on that date)
splice = '2006-07-03'
fq, fs = FF(QQEW), FF(SURV); kk = fq.at(splice) / fs.at(splice)
NDXSURV = {d: v for d, v in SURV.items() if d < splice}
NDXSURV.update({d: v / kk for d, v in QQEW.items() if d >= splice})

PROXIES = {   # name: (numerator, denominator, description)
    'qqew': (QQEW, qqqpx, 'QQEW/QQQ (the original; 2006-05+)'),
    'ndxsurv': (NDXSURV, qqqpx, 'survivor equal-weight NDX 1999-2006 spliced to QQEW (ILLUSTRATIVE, ~30% coverage)'),
    'comp': (COMP, NDX, 'NASDAQCOM/NASDAQ100 (FRED, composite vs mega-cap)'),
    'rut': (IDX['RUT'], NDX, 'Russell 2000 / NDX'),
    'rua': (IDX['RUA'], NDX, 'Russell 3000 / NDX'),
    'nya': (IDX['NYA'], NDX, 'NYSE Composite / NDX'),
    'w5k': (IDX['W5000'], NDX, 'Wilshire 5000 / NDX'),
    'rsp': (RSP, spy, 'RSP/SPY (S&P equal-weight; 2003-05+)'),
}
FALLBACKS = ['comp', 'rut', 'rua', 'nya', 'w5k']
WINDOWS = (10, 20, 40, 60, 90, 120, 250)
LR = {n: ratio_series(a, b) for n, (a, b, _) in PROXIES.items()}
series, pct = {}, {}
for n in PROXIES:
    for w in WINDOWS:
        series[f'{n}_{w}'] = diffs(LR[n], w); pct[f'{n}_{w}'] = trailing_pct(series[f'{n}_{w}'])
NAMES = list(series)

print("\nSERIES COVERAGE (60d window; first date with a trailing-252 percentile) and readings on 2026-09-09")
i9 = cix['2026-09-09']
for n in PROXIES:
    k = f'{n}_60'; first = next(d for d, p in zip(cal, pct[k]) if p is not None)
    print(f"  {k:<12}{first:>12}  n {sum(1 for p in pct[k] if p is not None):>5}  | 09-09 value {series[k][i9]:+.4f} pct {pct[k][i9]:.2f}  | {PROXIES[n][2]}")

# ------------------------------------------------------------------ 2. attach to rows (causal: value at d0 close)
def attach(r, d):
    i = cix[d]
    r['bp'] = {n: pct[n][i] for n in NAMES}; r['bv'] = {n: series[n][i] for n in NAMES}
for r in rows: attach(r, r['d'])
for r in rr:
    d = r['d0']
    if d not in cix: d = cal[bisect.bisect_right(cal, d) - 1]
    attach(r, d)

def mean(a): return sum(a) / len(a)
def corr(a, b):
    ma, mb = mean(a), mean(b); va = sum((x - ma) ** 2 for x in a); vb = sum((y - mb) ** 2 for y in b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)
def tstat(a):
    m = mean(a); sd_ = (sum((x - m) ** 2 for x in a) / (len(a) - 1)) ** 0.5
    return m / (sd_ / math.sqrt(len(a)))

# alignment sanity check: contemporaneous corr(QQQ d0->d1, change of the raw log-ratio d0->d1) should be negative for
# any "broad vs mega-cap Nasdaq" ratio (equal-weight/breadth lags on QQQ up-days), the predictive pairing near zero
print("\nALIGNMENT CHECK (60d series): contemp = corr(QQQ d0->d1, raw log-ratio change d0->d1); pred = corr(pct at d0, QQQ d0->d1)")
for n in PROXIES:
    k = f'{n}_60'; pr = [(r, rows[i + 1]) for i, r in enumerate(rows[:-1]) if r['bp'][k] is not None and rows[i + 1]['bp'][k] is not None]
    lr_ = LR[n]
    c1 = corr([r['qqq'] for r, _ in pr], [lr_[cix[r2['d']]] - lr_[cix[r['d']]] for r, r2 in pr])
    c2 = corr([r['bp'][k] for r, _ in pr], [r['qqq'] for r, _ in pr])
    print(f"  {k:<12} n {len(pr):>5}  contemp {c1:+.3f}  pred d1 {c2:+.3f}")

# ------------------------------------------------------------------ 3. gate, controls (verbatim from breadth_signal.py)
def trimmed(eff, gaps, extra=0):
    w = W[eff]
    votes = min(3, extension_votes(eff, gaps) + (extra if eff == 'A' else 0))
    f = 1.0 - EXTENSION_STEP * votes
    return w if f >= 1 else tuple(x * f for x in w[:4]) + (1 - f * sum(w[:4]),)
def scale_risky(w, k): return tuple(x * k for x in w[:4]) + (1 - k * sum(w[:4]),)
def gate_fn(name, k, thr=0.2, scope=('D',), vtf=vt, flip=False):
    def fn(r):
        w = trimmed(r['eff'], r['gaps']); p = r['bp'][name]
        on = (p > 1 - thr) if flip else (p < thr)
        if r['eff'] in scope and on: w = scale_risky(w, 1 - k)
        return vtf(w, r['vol'])
    return fn
def const_D(q, vtf=vt):
    """live design with the D row held at q x QLD (rest cash) ALWAYS -- no breadth."""
    def fn(r):
        w = trimmed(r['eff'], r['gaps'])
        if r['eff'] == 'D': w = scale_risky(w, q)
        return vtf(w, r['vol'])
    return fn
def expo(rs, fn): return run(rs, fn)[1]
def calib_q(rs, target):
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if expo(rs, const_D(mid)) < target: lo = mid
        else: hi = mid
    return (lo + hi) / 2
def live_scaled(k): return lambda r: scale_risky(live_w(r), k)
def exposure_control_live(rs, target, lo=0.0, hi=1.0):
    while expo(rs, live_scaled(hi)) < target and hi < 8: lo, hi = hi, hi * 2
    for _ in range(40):
        mid = (lo + hi) / 2
        if expo(rs, live_scaled(mid)) < target: lo = mid
        else: hi = mid
    k = (lo + hi) / 2
    return k, evaluate(rs, live_scaled(k))
def sub_rows(name): return [r for r in rows if r['bp'][name] is not None]
def both(ev, b): return ev['s_sharpe'] > b['s_sharpe'] and ev['h_sharpe'] > b['h_sharpe']
def seed(*a): return zlib.crc32('|'.join(map(str, a)).encode())
NCAND = 0

def dgate_block(rs, name, depth, label, thr=0.2, do_boot=True, flip=False, real=True):
    """the D-gate at one depth on rows rs, with the constant-D and k-live capital controls, bootstrap and real rows."""
    global NCAND; NCAND += 0 if flip else 1
    fn = gate_fn(name, depth, thr, flip=flip); ev = evaluate(rs, fn); b = evaluate(rs, LIVE)
    q = calib_q(rs, ev['risky']); ce = evaluate(rs, const_D(q)); kk, ke = exposure_control_live(rs, ev['risky'])
    re = RF.eval_real(rr, gate_fn(name, depth, thr, vtf=RF.vt, flip=flip)) if real else None
    on = sum(1 for r in rs if r['eff'] == 'D' and ((r['bp'][name] > 1 - thr) if flip else (r['bp'][name] < thr)))
    out = dict(ev=ev, b=b, q=q, ce=ce, k=kk, ke=ke, re=re, on=on, fn=fn)
    line = (f"  {label:<26}{fmt(ev):>22}  S {ev['s_sharpe']:.3f} H {ev['h_sharpe']:.3f} exp {ev['risky']*100:4.1f}% on {on:>4}"
            f" | vs live {ev['s_sharpe']-b['s_sharpe']:+.3f}/{ev['h_sharpe']-b['h_sharpe']:+.3f}"
            f" | const-D q={q:.3f} {ev['s_sharpe']-ce['s_sharpe']:+.3f}/{ev['h_sharpe']-ce['h_sharpe']:+.3f}"
            f" | k-live k={kk:.3f} {ev['s_sharpe']-ke['s_sharpe']:+.3f}/{ev['h_sharpe']-ke['h_sharpe']:+.3f}")
    if real: line += f" | real {re['sharpe']:.3f} ({re['sharpe']-real_all['sharpe']:+.3f})"
    if do_boot:
        a = run(rs, fn)[0]; bl = run(rs, LIVE)[0]; bc = run(rs, const_D(q))[0]; out['a'] = a; out['bl'] = bl; out['bc'] = bc
        bs = {}
        for lab, ref in (('live', bl), ('constD', bc)):
            for blk in (20, 60):
                l1, l2, pl, s1, s2, ps = boot(a, ref, blk, seed=seed(name, depth, thr, label, lab, blk))
                bs[(lab, blk)] = (l1, l2, pl, s1, s2, ps)
        out['boot'] = bs
        line += "\n" + " " * 28 + "  ".join(f"boot vs {lab} {blk}d: Sh CI [{v[3]:+.3f},{v[4]:+.3f}] P<=0 {v[5]:.3f} logret P<=0 {v[2]:.3f}"
                                            for (lab, blk), v in bs.items())
    print(line, flush=True)
    return out

# ------------------------------------------------------------------ 4. VALIDATION on the QQEW rows (2007-07-27+)
print("\n" + "=" * 112)
print("STEP 2 -- VALIDATE EACH FALLBACK AGAINST THE REAL QQEW/QQQ SERIES ON THE SAME 2007-07+ ROWS")
print("=" * 112)
RQ = sub_rows('qqew_60')
print(f"rows with qqew_60 percentile: {len(RQ)} {RQ[0]['d']}..{RQ[-1]['d']}; state-D rows among them {sum(1 for r in RQ if r['eff']=='D')}")
print("\n(a) series agreement with qqew_60 on those rows: corr of the 60d log-ratio changes, corr of the percentiles, bottom-quintile")
print("    flag agreement (all rows / state-D rows), Jaccard of the flag sets on state-D rows")
print(f"  {'series':<12}{'corr chg':>9}{'corr pct':>9}{'agree all':>10}{'agree D':>9}{'Jaccard D':>10}{'flags D (qqew/this/both)':>26}")
AGREE = {}
for n in ['ndxsurv'] + FALLBACKS + ['rsp']:
    k = f'{n}_60'; pr = [r for r in RQ if r['bp'][k] is not None]
    c1 = corr([r['bv'][k] for r in pr], [r['bv']['qqew_60'] for r in pr]); c2 = corr([r['bp'][k] for r in pr], [r['bp']['qqew_60'] for r in pr])
    fa = mean([1.0 if (r['bp'][k] < 0.2) == (r['bp']['qqew_60'] < 0.2) else 0.0 for r in pr])
    dd = [r for r in pr if r['eff'] == 'D']
    fd = mean([1.0 if (r['bp'][k] < 0.2) == (r['bp']['qqew_60'] < 0.2) else 0.0 for r in dd])
    nq = sum(1 for r in dd if r['bp']['qqew_60'] < 0.2); nt = sum(1 for r in dd if r['bp'][k] < 0.2)
    nb = sum(1 for r in dd if r['bp'][k] < 0.2 and r['bp']['qqew_60'] < 0.2); jac = nb / max(1, nq + nt - nb)
    AGREE[n] = (c1, c2, fa, fd, jac, nq, nt, nb)
    print(f"  {k:<12}{c1:>9.3f}{c2:>9.3f}{fa:>10.3f}{fd:>9.3f}{jac:>10.3f}{f'{nq}/{nt}/{nb}':>26}")

print("\n(b) the D-gate re-run on the SAME rows with each proxy (this is the validation that matters). Reference: qqew_60.")
print("    Columns: CAGR/Sh/MDD, S/H Sharpe, deployed capital, days gate on; Sharpe deltas S/H vs same-rows live, vs the")
print("    constant-D control at matched capital (q), vs the live design scaled to matched capital (k); real weekly Sharpe.")
VAL = {}
for depth in (1.0, 0.5):
    print(f"\n  depth {depth*100:.0f}%:   same-rows live {fmt(evaluate(RQ, LIVE))} S {evaluate(RQ, LIVE)['s_sharpe']:.3f} H {evaluate(RQ, LIVE)['h_sharpe']:.3f}")
    ref = dgate_block(RQ, 'qqew_60', depth, f'qqew_60 (reference)', do_boot=(depth == 1.0))
    for n in ['ndxsurv'] + FALLBACKS + ['rsp']:
        k = f'{n}_60'; rs = [r for r in RQ if r['bp'][k] is not None]
        o = dgate_block(rs, k, depth, k, do_boot=(depth == 1.0))
        if depth == 1.0:
            # is the fallback-gated series distinguishable from the QQEW-gated series?  block bootstrap of the difference
            l1, l2, pl, s1, s2, ps = boot(o['a'], ref['a'], 20, seed=seed(k, 'vsqqew', 20)); l3, l4, pl2, s3, s4, ps2 = boot(o['a'], ref['a'], 60, seed=seed(k, 'vsqqew', 60))
            pass_ = (o['ev']['s_sharpe'] > o['ce']['s_sharpe'] and o['ev']['h_sharpe'] > o['ce']['h_sharpe'] and
                     o['ev']['s_sharpe'] > o['b']['s_sharpe'] and o['ev']['h_sharpe'] > o['b']['h_sharpe'] and
                     o['boot'][('constD', 20)][5] < 0.05 and o['boot'][('constD', 60)][5] < 0.05)
            VAL[n] = dict(pass_=pass_, o=o, vsq=(s1, s2, ps, s3, s4, ps2))
            print(f"{'':28}vs qqew-gated: Sh diff CI 20d [{s1:+.3f},{s2:+.3f}] P<=0 {ps:.3f}; 60d [{s3:+.3f},{s4:+.3f}] P<=0 {ps2:.3f}"
                  f"  -> {'VALIDATES (both-era > live and > const-D, boot vs const-D P<0.05 at 20d and 60d)' if pass_ else 'DOES NOT VALIDATE'}")
VALID = [n for n in FALLBACKS if VAL[n]['pass_']]
print(f"\nVALIDATED FALLBACKS: {VALID}   (not validated: {[n for n in FALLBACKS if not VAL[n]['pass_']]}; ndxsurv {'passes' if VAL['ndxsurv']['pass_'] else 'fails'} but is illustrative only; rsp {'passes' if VAL['rsp']['pass_'] else 'fails'})")
if STAGE == 1: sys.exit(0)

# ------------------------------------------------------------------ 5. STEP 3: full 2000-07+ rows
print("\n" + "=" * 112)
print("STEP 3 -- THE D-GATE ON THE FULL 2000-07+ PROXY ROWS, EVERY FALLBACK THAT VALIDATES (non-validating ones shown for the record, marked)")
print("=" * 112)
REGIMES = [('dot-com 2000-07..2003-03', '2000-07-01', '2003-03-31'), ('2000-2006 (pre-QQEW)', '2000-01-01', '2006-12-31'),
           ('GFC 2007-09', '2007-01-01', '2009-12-31'), ('COVID 2020', '2020-01-01', '2020-12-31'),
           ('2022 bear', '2022-01-01', '2022-12-31'), ('SPMO era 2015-11+', '2015-11-01', '2099-01-01')]
FULL = {}
ONLY = os.environ.get('DGATE_ONLY', '').split(',') if os.environ.get('DGATE_ONLY') else None
for n in [x for x in VALID + ['ndxsurv'] if (ONLY is None or x in ONLY)]:
    k = f'{n}_60'; rs = sub_rows(k); tag = '' if (n in VALID) else ('  [ILLUSTRATIVE, survivorship-biased]' if n == 'ndxsurv' else '  [NOT VALIDATED on 2007+]')
    b = evaluate(rs, LIVE)
    print(f"\n[{k}] {PROXIES[n][2]}{tag}\n  rows {len(rs)} {rs[0]['d']}..{rs[-1]['d']}; live {fmt(b)} S {b['s_sharpe']:.3f} H {b['h_sharpe']:.3f} exp {b['risky']*100:.1f}%")
    o100 = dgate_block(rs, k, 1.0, 'D-gate 100% cash'); o50 = dgate_block(rs, k, 0.5, 'D-gate 50% cash')
    FULL[n] = (o100, o50)
    for depth, o in ((1.0, o100), (0.5, o50)):
        a, bl, bc = o['a'], o['bl'], o['bc']
        print(f"  leave-one-regime-out, depth {depth*100:.0f}% (Sharpe diff vs const-D / vs live; then the DROPPED slice on its own: gate / const-D / live Sharpe):")
        for rlab, a0, b0 in REGIMES:
            keep = [i for i, r in enumerate(rs) if not (a0 <= r['d'] <= b0)]; drop = [i for i, r in enumerate(rs) if a0 <= r['d'] <= b0]
            _, s1 = stats([a[i] for i in keep]); _, s2 = stats([bc[i] for i in keep]); _, s3 = stats([bl[i] for i in keep])
            _, d1 = stats([a[i] for i in drop]); _, d2 = stats([bc[i] for i in drop]); _, d3 = stats([bl[i] for i in drop])
            print(f"      drop {rlab:<26} {s1-s2:+.3f} / {s1-s3:+.3f}   | slice alone ({len(drop)} d): {d1:.3f} / {d2:.3f} / {d3:.3f}  gate-live {d1-d3:+.3f}")
    # sign-flip placebo (top quintile gates), own q
    print("  sign-flip placebo (gate when pct > 0.80 instead):")
    dgate_block(rs, k, 1.0, 'flip 100%', flip=True, do_boot=False); dgate_block(rs, k, 0.5, 'flip 50%', flip=True, do_boot=False)
    # threshold sweep
    print("  threshold sweep (100% depth; each is a candidate):")
    for t in (0.10, 0.20, 0.30, 0.40, 0.50): dgate_block(rs, k, 1.0, f'thr {t:.2f}', thr=t, do_boot=False)
    # window sweep
    print("  window sweep (100% depth, thr 0.20; each is a candidate; rows restricted to where that window has a percentile):")
    for w in WINDOWS:
        kw = f'{n}_{w}'; rw = sub_rows(kw); dgate_block(rw, kw, 1.0, f'window {w:>3}d (n={len(rw)})', do_boot=False)

# ------------------------------------------------------------------ 6. dot-com D episodes
print("\n" + "=" * 112)
print("DOT-COM D EPISODES (2000-07-01..2003-03-31): every contiguous run of effective state D, with the QLD-leg log-return over")
print("the run, and for each validated fallback (and the illustrative survivor series) how many of its days the gate is on and the")
print("QLD-leg return on gated vs ungated days.  A gate that 'works' in dot-com should be on during the negative runs.")
print("=" * 112)
DOT = [r for r in rows if '2000-07-01' <= r['d'] <= '2003-03-31']
eps = []; cur = None
for r in DOT:
    if r['eff'] == 'D':
        if cur is None: cur = []
        cur.append(r)
    elif cur: eps.append(cur); cur = None
if cur: eps.append(cur)
SHOW = [x for x in VALID + ['ndxsurv'] if x in FULL]
print(f"  {len(eps)} D episodes, {sum(len(e) for e in eps)} D days in the slice. QLD-leg return = sum of log(1+legs[2]).")
hdr = f"  {'start':<11}{'end':<11}{'days':>5}{'QLD ret':>9} |" + "".join(f" {n+'_60':>10} on/ret-on/ret-off" for n in SHOW)
print(hdr)
tot = {n: [0, 0.0, 0.0, 0, 0] for n in SHOW}
for e in eps:
    line = f"  {e[0]['d']:<11}{e[-1]['d']:<11}{len(e):>5}{sum(math.log1p(r['legs'][2]) for r in e)*100:>+8.1f}% |"
    for n in SHOW:
        k = f'{n}_60'; on = [r for r in e if r['bp'][k] is not None and r['bp'][k] < 0.2]; off = [r for r in e if not (r['bp'][k] is not None and r['bp'][k] < 0.2)]
        ron = sum(math.log1p(r['legs'][2]) for r in on) * 100; roff = sum(math.log1p(r['legs'][2]) for r in off) * 100
        tot[n][0] += len(on); tot[n][1] += ron; tot[n][2] += roff; tot[n][3] += len(off); tot[n][4] += 1 if on else 0
        line += f" {len(on):>4}/{len(e):<3}{ron:>+7.1f}%{roff:>+7.1f}%"
    print(line)
for n in SHOW:
    t = tot[n]; k = f'{n}_60'
    on = [r['legs'][2] for r in DOT if r['eff'] == 'D' and r['bp'][k] is not None and r['bp'][k] < 0.2]
    off = [r['legs'][2] for r in DOT if r['eff'] == 'D' and not (r['bp'][k] is not None and r['bp'][k] < 0.2)]
    print(f"  {k:<12} gate on in {t[4]}/{len(eps)} episodes, {t[0]} of {t[0]+t[3]} D days; QLD-leg summed on gated days {t[1]:+.1f}pp, ungated {t[2]:+.1f}pp;"
          f" per-day mean gated {mean(on)*1e4 if on else float('nan'):+.0f}bp (t {tstat(on) if len(on) > 2 else float('nan'):+.2f}, hit {mean([1.0 if x > 0 else 0.0 for x in on]) if on else float('nan'):.2f})"
          f" vs ungated {mean(off)*1e4:+.0f}bp (hit {mean([1.0 if x > 0 else 0.0 for x in off]):.2f})")
# per-day stats over the whole 2000-07+ sample and the 2000-2006 slice
print("\nPER-DAY QLD-LEG STATISTICS on gated vs other state-D days (whole 2000-07+ sample and the 2000-2006 slice):")
print(f"  {'series':<12}{'slice':<12}{'gated n':>8}{'mean bp':>9}{'t':>7}{'hit':>6} |{'other n':>8}{'mean bp':>9}{'hit':>6} | diff t")
for n in SHOW:
    k = f'{n}_60'
    for lab, lo, hi in (('full', '2000-07-01', '2099'), ('2000-2006', '2000-07-01', '2006-12-31'), ('2007+', '2007-01-01', '2099')):
        dd = [r for r in rows if r['eff'] == 'D' and lo <= r['d'] <= hi and r['bp'][k] is not None]
        g = [r['legs'][2] for r in dd if r['bp'][k] < 0.2]; o = [r['legs'][2] for r in dd if r['bp'][k] >= 0.2]
        if len(g) < 3 or len(o) < 3: continue
        mg, mo = mean(g), mean(o); vg = sum((x - mg) ** 2 for x in g) / (len(g) - 1); vo = sum((x - mo) ** 2 for x in o) / (len(o) - 1)
        dt = (mg - mo) / math.sqrt(vg / len(g) + vo / len(o))
        print(f"  {k:<12}{lab:<12}{len(g):>8}{mg*1e4:>9.1f}{tstat(g):>7.2f}{mean([1.0 if x>0 else 0 for x in g]):>6.2f} |{len(o):>8}{mo*1e4:>9.1f}{mean([1.0 if x>0 else 0 for x in o]):>6.2f} | {dt:+.2f}")

# ------------------------------------------------------------------ 7. side by side: RSP/SPY vs NASDAQCOM/NASDAQ100 vs QQEW on the common window
print("\n" + "=" * 112)
print("SIDE BY SIDE on the COMMON rows: the S&P analogue (rsp_60) vs the composite fallback (comp_60) vs the original (qqew_60).")
print("(i) rows where rsp_60 exists (2004-07+): rsp vs comp;  (ii) rows where qqew_60 exists (2007-07+): all three.")
print("=" * 112)
for lab, base_k, ks in (('rsp rows 2004-07+', 'rsp_60', ['rsp_60', 'comp_60']), ('qqew rows 2007-07+', 'qqew_60', ['qqew_60', 'rsp_60', 'comp_60'])):
    rs = sub_rows(base_k); b = evaluate(rs, LIVE)
    print(f"\n  ({lab}) n={len(rs)}: live {fmt(b)} S {b['s_sharpe']:.3f} H {b['h_sharpe']:.3f}")
    for k in ks:
        for depth in (1.0, 0.5): dgate_block(rs, k, depth, f'{k} {depth*100:.0f}%', do_boot=False)

# ------------------------------------------------------------------ 8. summary for the verdict
print("\n" + "=" * 112)
print("SUMMARY -- 26y (2000-07..2026-08) figures, live vs gated-100 vs gated-50, per validated fallback (and the illustrative survivor series)")
print("=" * 112)
print(f"  {'series':<12}{'rule':<10}{'CAGR/Sh/MDD':>22}{'S':>7}{'H':>7}{'exp':>7}{'| vs live S/H':>14}{'| vs constD S/H':>16}{'| vs k-live S/H':>16}{'| boot constD P20/P60':>22}{'| real Sh':>9}")
b = evaluate(rows, LIVE)
print(f"  {'live':<12}{'':<10}{fmt(b):>22}{b['s_sharpe']:>7.3f}{b['h_sharpe']:>7.3f}{b['risky']*100:>6.1f}%")
for n in [x for x in VALID + ['ndxsurv'] if x in FULL]:
    for depth, o in zip((1.0, 0.5), FULL[n]):
        ev, ce, ke, bb = o['ev'], o['ce'], o['ke'], o['b']
        print(f"  {n+'_60':<12}{f'gate {depth*100:.0f}%':<10}{fmt(ev):>22}{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f}{ev['risky']*100:>6.1f}%"
              f"{ev['s_sharpe']-bb['s_sharpe']:>+7.3f}{ev['h_sharpe']-bb['h_sharpe']:>+7.3f}"
              f"{ev['s_sharpe']-ce['s_sharpe']:>+9.3f}{ev['h_sharpe']-ce['h_sharpe']:>+7.3f}"
              f"{ev['s_sharpe']-ke['s_sharpe']:>+9.3f}{ev['h_sharpe']-ke['h_sharpe']:>+7.3f}"
              f"{o['boot'][('constD',20)][5]:>12.3f}{o['boot'][('constD',60)][5]:>8.3f}{o['re']['sharpe']:>10.3f}")
print(f"\nTOTAL CANDIDATE CELLS EVALUATED THIS LINE (gate variants incl. depth/threshold/window cells, excluding placebos): {NCAND}")
print("Today's readings printed in the SERIES COVERAGE table above; last proxy row " + rows[-1]['d'] + " eff " + rows[-1]['eff'])
