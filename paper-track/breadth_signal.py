"""RESEARCH LINE `breadth_signal` (2026-09-10): does market BREADTH add anything
to the regime signal?  Research only -- nothing here is applied.

Motivation: an outside discretionary manager downgraded on 2026-09-09 citing
"192 yearly lows vs 35 yearly highs on the NASDAQ composite". We have no
new-highs/new-lows history, so this line builds CAUSAL breadth PROXIES from
daily closes and tests each (a) as a gate/tilt on top of the LIVE design and
(b) as a confirmation / replacement input to the 50/200 classifier.

PROXY SERIES (daily, value known at the close of d0, on the QQQ proxy calendar):
  qqew_20 / qqew_60      20d / 60d change of log(QQEW/QQQ)   (QQEW from 2006-05)
  qqew_s50 / qqew_s200   log-ratio minus its own 50d / 200d SMA
  rsp_*                  the same four for RSP/SPY               (RSP from 2003-05)
  nhnl1 / nhnl10         (252d new highs - new lows) / n over a FIXED basket of
                         30 current top QQQ names; daily and 10d mean.
                         SURVIVORSHIP-BIASED: illustration only, not a holdout test.
  sec200 / sec50         fraction of the NINE 1998-vintage SPDR sector ETFs above
                         their own 200d / 50d SMA (XLRE/XLC excluded to keep the
                         basket fixed through history).
THRESHOLDS: trailing 252-session percentile of each series (inclusive of today,
  ties split). "bottom quintile" = pct < 0.20, "above median" = pct > 0.50.
  Never a full-sample constant.
ROWS: each proxy is scored on the rows where it exists, and the LIVE baseline is
  re-scored on THE SAME rows (same-rows control). Holdout coverage per proxy
  is printed.

VARIANTS (per series; sign-flip placebo = 1 - pct):
  i25 / i50   de-lever the A/D rows by 25% / 50% when breadth is bottom-quintile
  ii          require breadth above its trailing median to hold the untrimmed A
              row; otherwise count one extra extension-trim vote (cap 3)
  iii         block the fast re-entry overlay (20/100) when breadth is bottom-quintile
  iv1         tilt: risky legs x g(pct), g = clip(0.5 + pct, 0.5, 1) (one-sided),
              vol-target T re-calibrated by bisection so average deployed exposure
              on the same rows equals LIVE's (exposure control by construction)
  iv2         tilt: g = clip(0.75 + 0.5 pct, 0.75, 1.25), total risky capped at 1,
              T re-calibrated as above. When T saturates (a de-levering-only tilt cannot reach
              live's capital), T stays 0.20 and a multiplier c on the tilt is bisected instead.
  conf        classifier CONFIRMATION: bottom-quintile breadth downgrades the
              effective row one notch (A->B, B->C)
  repl        classifier REPLACEMENT (one per family): the price-vs-50d and
              price-vs-200d booleans of the six-state machine are replaced by the
              breadth booleans (ratio > own 50d/200d SMA; sector majority above
              50d/200d; NHNL 10d/60d mean > 0), QQQ's own 50>200 cross kept,
              then the live fast overlay + trim + vol target on top.
CONTROLS: same-rows live, both-era, exposure-matched live (LIVE design scaled
  by k to the candidate's deployed capital, plus downturn_review.exposure_control
  for the record), sign-flip placebo, circular block bootstrap (20/60d, 2000
  draws) for the best variant per family, leave-one-regime-out, real weekly
  SPMO rows via RF.eval_real. Candidate count reported.
"""
import sys, os, math, csv, bisect, zlib
QUICK = bool(os.environ.get('BREADTH_QUICK'))   # skip the bootstrap sections (5, 7) for a fast look at 8
sys.path.insert(0, 'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from state import (extension_scale, extension_votes, EXTENSION_STEP, effective_state)
from block_bootstrap import boot, stats, N_BOOT
from downturn_review import exposure_control
from improvement_search import SEARCH, HOLDOUT, era
from long_history_backtest import load_px as _load_px

print("=" * 110)
print("RESEARCH LINE breadth_signal -- market breadth proxies as a gate / tilt / classifier input")
print("=" * 110)

# ------------------------------------------------------------------ 0. live design
def live_w(r, vtf=vt, T=None):
    w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
    if f < 1: w = tuple(a * f for a in w[:4]) + (1 - f * sum(w[:4]),)
    return vtf(w, r['vol']) if T is None else vtf(w, r['vol'], T)
LIVE = lambda r: live_w(r)
LIVE_R = lambda r: live_w(r, RF.vt)
base_all = evaluate(rows, LIVE); real_all = RF.eval_real(rr, LIVE_R)
def fmt(ev): return f"{ev['cagr']*100:5.2f}% / {ev['sharpe']:.3f} / {ev['mdd']*100:5.1f}%"
print(f"\nSTANDING FIGURES (must match briefing): 26y proxy {fmt(base_all)}  S {base_all['s_sharpe']:.3f} "
      f"H {base_all['h_sharpe']:.3f}  exp {base_all['risky']*100:.1f}% | real weekly {fmt(real_all)}")
print(f"  rows {len(rows)} {rows[0]['d']}..{rows[-1]['d']}; real rows {len(rr)} {rr[0]['d0']}..{rr[-1]['d0']}")

# ------------------------------------------------------------------ 1. data
def load_daily(sym):
    return {r['d']: float(r['c']) for r in csv.DictReader(open(f'data/{sym}_daily.csv'))}
spy = _load_px('data/spy_long_history.csv')
qqqpx = px                                   # repo QQQ closes, dict d->c
SECT9 = ['XLK', 'XLF', 'XLE', 'XLV', 'XLI', 'XLY', 'XLP', 'XLU', 'XLB']
BASKET = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'AVGO', 'GOOGL', 'TSLA', 'COST', 'NFLX', 'PLTR', 'CSCO',
          'AMD', 'TMUS', 'LIN', 'PEP', 'INTU', 'ISRG', 'AMAT', 'QCOM', 'BKNG', 'TXN', 'AMGN', 'ADBE', 'MU',
          'HON', 'GILD', 'PANW', 'ADP', 'CMCSA']
Y = {s: load_daily(s) for s in ['QQEW', 'RSP'] + SECT9 + BASKET}

class FF:
    """forward-fill lookup: last close at or before d."""
    def __init__(self, m):
        self.k = sorted(m); self.v = [m[d] for d in self.k]
    def at(self, d):
        i = bisect.bisect_right(self.k, d) - 1
        return self.v[i] if i >= 0 else None
    def idx(self, d):
        i = bisect.bisect_right(self.k, d) - 1
        return i if i >= 0 else None

# full daily calendar for series = repo QQQ dates (ds) extended to 2026-09-09 with Yahoo dates
cal = sorted(set(ds) | set(d for d in Y['XLK'] if d > ds[-1]))
cix = {d: i for i, d in enumerate(cal)}

def sma_list(v, n):
    out = [None] * len(v); s = 0.0
    for i, x in enumerate(v):
        s += x
        if i >= n: s -= v[i - n]
        if i >= n - 1: out[i] = s / n
    return out

def ratio_series(num, den_map):
    """log(num/den) on cal, forward-filled; None before num exists."""
    f = FF(num); fd = FF(den_map); out = []
    for d in cal:
        a = f.at(d) if d >= f.k[0] else None; b = fd.at(d)
        out.append(math.log(a / b) if (a and b) else None)
    return out

def diffs(lr, n):
    return [None if (i < n or lr[i] is None or lr[i - n] is None) else lr[i] - lr[i - n] for i in range(len(lr))]

def minus_sma(lr, n):
    out = [None] * len(lr); win = []
    for i, x in enumerate(lr):
        if x is None: win = []; continue
        win.append(x)
        if len(win) > n: win.pop(0)
        if len(win) == n: out[i] = x - sum(win) / n
    return out

series, aux = {}, {}
for tag, num, den in (('qqew', Y['QQEW'], qqqpx), ('rsp', Y['RSP'], spy)):
    lr = ratio_series(num, den)
    series[f'{tag}_20'] = diffs(lr, 20); series[f'{tag}_60'] = diffs(lr, 60)
    series[f'{tag}_s50'] = minus_sma(lr, 50); series[f'{tag}_s200'] = minus_sma(lr, 200)
    aux[tag] = lr

# sector participation: fraction of the nine above own 200d / 50d SMA
def above_sma_flags(sym, n):
    m = Y[sym]; k = sorted(m); v = [m[d] for d in k]; s = sma_list(v, n)
    return {d: (v[i] > s[i]) for i, d in enumerate(k) if s[i] is not None}
for n, name in ((200, 'sec200'), (50, 'sec50')):
    flags = {s: above_sma_flags(s, n) for s in SECT9}
    ffs = {s: FF(flags[s]) for s in SECT9}
    out = []
    for d in cal:
        vals = [ffs[s].at(d) for s in SECT9 if d >= ffs[s].k[0]]
        out.append(sum(vals) / len(vals) if len(vals) == 9 else None)
    series[name] = out

# NH-NL over the fixed basket: 252d closing high / low, per symbol on its own calendar
def nhnl_flags(sym, n=252):
    m = Y[sym]; k = sorted(m); v = [m[d] for d in k]; out = {}
    for i in range(n - 1, len(v)):
        w = v[i - n + 1:i + 1]; out[k[i]] = (1 if v[i] >= max(w) else 0) - (1 if v[i] <= min(w) else 0)
    return out
bf = {s: FF(nhnl_flags(s)) for s in BASKET}
raw, navail = [], []
for d in cal:
    vals = [bf[s].at(d) for s in BASKET if d >= bf[s].k[0]]
    navail.append(len(vals)); raw.append(sum(vals) / len(vals) if len(vals) >= 15 else None)
series['nhnl1'] = raw
def roll_mean(v, n):
    out = [None] * len(v); win = []
    for i, x in enumerate(v):
        if x is None: win = []; continue
        win.append(x)
        if len(win) > n: win.pop(0)
        if len(win) == n: out[i] = sum(win) / n
    return out
series['nhnl10'] = roll_mean(raw, 10)
aux['nhnl60'] = roll_mean(raw, 60)

# trailing 252-session percentile (inclusive of today, ties split)
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
pct = {k: trailing_pct(v) for k, v in series.items()}
NAMES = ['qqew_20', 'qqew_60', 'qqew_s50', 'qqew_s200', 'rsp_20', 'rsp_60', 'rsp_s50', 'rsp_s200',
         'nhnl1', 'nhnl10', 'sec200', 'sec50']
FAMILY = {n: n.split('_')[0] if '_' in n else ('nhnl' if n.startswith('nhnl') else 'sec') for n in NAMES}

print("\nSERIES COVERAGE (first date with a trailing-252 percentile) and LAST readings (what breadth said on 2026-09-08/09)")
print(f"  {'series':<10}{'first pct':>12}{'n days':>8} | {'value 09-08':>12}{'pct':>6} | {'value 09-09':>12}{'pct':>6}")
for n in NAMES:
    first = next(d for d, p in zip(cal, pct[n]) if p is not None)
    i8, i9 = cix['2026-09-08'], cix['2026-09-09']
    print(f"  {n:<10}{first:>12}{sum(1 for p in pct[n] if p is not None):>8} | {series[n][i8]:>12.4f}{pct[n][i8]:>6.2f} | "
          f"{series[n][i9]:>12.4f}{pct[n][i9]:>6.2f}")
print(f"  basket names available for NH-NL: {navail[cix['2003-01-02']]} on 2003-01-02, {navail[cix['2010-01-04']]} on 2010-01-04, "
      f"{navail[-1]} on {cal[-1]}; the basket is the 2026-09 top 30, so early counts are on survivors only.")

# ------------------------------------------------------------------ 2. attach to rows (causal: value at d0 close)
def bool_inputs(n_fam, i):
    """(b_short, b_long) breadth booleans for the replacement classifier, per family."""
    if n_fam in ('qqew', 'rsp'):
        a, b = series[f'{n_fam}_s50'][i], series[f'{n_fam}_s200'][i]
        return None if a is None or b is None else (a > 0, b > 0)
    if n_fam == 'sec':
        a, b = series['sec50'][i], series['sec200'][i]
        return None if a is None or b is None else (a >= 0.5, b >= 0.5)
    a, b = series['nhnl10'][i], aux['nhnl60'][i]
    return None if a is None or b is None else (a > 0, b > 0)

fast = compute_fast_states(ds, px); pv = [px[d] for d in ds]; pix = {d: i for i, d in enumerate(ds)}
def attach(r, d):
    i = cix[d]
    r['bp'] = {n: pct[n][i] for n in NAMES}; r['bv'] = {n: series[n][i] for n in NAMES}
    r['bb'] = {f: bool_inputs(f, i) for f in ('qqew', 'rsp', 'nhnl', 'sec')}
for r in rows:
    attach(r, r['d']); j = pix[r['d']]; r['fast'] = fast[r['d']]; r['cross'] = sma(pv, j, 50) > sma(pv, j, 200)
for r in rr:
    d = r['d0']
    if d not in cix: d = cal[bisect.bisect_right(cal, d) - 1]
    attach(r, d); j = qix[r['d0']]; r['fast'] = g[r['d0']]; r['cross'] = sma(qv, j, 50) > sma(qv, j, 200)

# ------------------------------------------------------------------ 3. alignment + descriptive
def mean(a): return sum(a) / len(a)
def corr(a, b):
    ma, mb = mean(a), mean(b); va = sum((x - ma) ** 2 for x in a); vb = sum((y - mb) ** 2 for y in b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)
print("\nALIGNMENT CHECK: corr(QQQ d0->d1 return, CHANGE of the raw series over d0->d1) should be clearly non-zero for the")
print("  ratio/NHNL series (contemporaneous), and corr(pct at d0, QQQ d0->d1) is the PREDICTIVE pairing.")
print(f"  {'series':<10}{'n':>6}{'contemp':>10}{'pred d1':>10}{'pred 21d':>10}{'pred 63d':>10}")
for n in NAMES:
    a, b, c1, c21, c63 = [], [], [], [], []
    for k, r in enumerate(rows):
        i = cix[r['d']]; p = r['bp'][n]
        if p is None or series[n][i + 1] is None or series[n][i] is None: continue
        a.append(r['qqq']); b.append(series[n][i + 1] - series[n][i]); c1.append(p)
        j = pix[r['d']]
        c21.append(pv[j + 21] / pv[j] - 1 if j + 21 < len(pv) else None); c63.append(pv[j + 63] / pv[j] - 1 if j + 63 < len(pv) else None)
    ok21 = [k for k in range(len(a)) if c21[k] is not None]; ok63 = [k for k in range(len(a)) if c63[k] is not None]
    print(f"  {n:<10}{len(a):>6}{corr(a, b):>10.3f}{corr(c1, a):>10.3f}"
          f"{corr([c1[k] for k in ok21], [c21[k] for k in ok21]):>10.3f}{corr([c1[k] for k in ok63], [c63[k] for k in ok63]):>10.3f}")

print("\nFORWARD 21-DAY QQQ RETURN BY TRAILING-252 PERCENTILE QUINTILE OF EACH SERIES (causal buckets; mean %, n)")
print(f"  {'series':<10}" + "".join(f"{'Q'+str(q+1):>14}" for q in range(5)) + f"{'Q5-Q1':>10}   | search-era Q5-Q1 | holdout-era Q5-Q1")
for n in NAMES:
    def qtab(sub):
        b = [[] for _ in range(5)]
        for r in sub:
            p = r['bp'][n]; j = pix[r['d']]
            if p is None or j + 21 >= len(pv): continue
            b[min(4, int(p * 5))].append(pv[j + 21] / pv[j] - 1)
        return b
    b = qtab(rows); bs = qtab(era(rows, *SEARCH)); bh = qtab(era(rows, *HOLDOUT))
    line = f"  {n:<10}" + "".join(f"{mean(x)*100:>8.2f} ({len(x):>4})" if x else f"{'--':>14}" for x in b)
    line += f"{(mean(b[4])-mean(b[0]))*100:>10.2f}"
    line += f"   | {(mean(bs[4])-mean(bs[0]))*100:>+8.2f}        | {(mean(bh[4])-mean(bh[0]))*100:>+8.2f}" if bh[0] and bh[4] and bs[0] and bs[4] else ""
    print(line)

# ------------------------------------------------------------------ 4. variants
def trimmed(eff, gaps, extra=0):
    w = W[eff]
    votes = min(3, extension_votes(eff, gaps) + (extra if eff == 'A' else 0))
    f = 1.0 - EXTENSION_STEP * votes
    return w if f >= 1 else tuple(x * f for x in w[:4]) + (1 - f * sum(w[:4]),)
def scale_risky(w, k): return tuple(x * k for x in w[:4]) + (1 - k * sum(w[:4]),)
def cap1(w):
    s = sum(w[:4])
    return w if s <= 1.0 else tuple(x / s for x in w[:4]) + (0.0,)
DOWN = {'A': 'B', 'B': 'C'}
STATE_TABLE = lambda s50, s200, cross: ('A' if (s50 and s200 and cross) else 'B' if (s50 and s200) else 'C' if s50
                                        else 'D' if s200 else 'E' if cross else 'F')

def variant(name, kind, sign=1, T=None, vtf=vt, c=1.0):
    """c: multiplier on the tilt g (iv1/iv2) used ONLY when T saturates -- then T stays at live 0.20
    and c is bisected instead so deployed capital still matches live; risky legs capped at 1."""
    fam = FAMILY[name]
    def fn(r):
        p = r['bp'][name]
        if sign < 0: p = 1 - p
        eff, gaps, v = r['eff'], r['gaps'], r['vol']
        if kind in ('i25', 'i50'):
            w = trimmed(eff, gaps)
            if eff in ('A', 'D') and p < 0.2: w = scale_risky(w, 0.75 if kind == 'i25' else 0.5)
        elif kind == 'ii':
            w = trimmed(eff, gaps, extra=1 if p <= 0.5 else 0)
        elif kind == 'iii':
            e2 = r['state'] if (p < 0.2 and eff != r['state']) else eff
            w = trimmed(e2, gaps)
        elif kind == 'iv1':
            w = cap1(scale_risky(trimmed(eff, gaps), c * min(1.0, max(0.5, 0.5 + p))))
        elif kind == 'iv2':
            w = cap1(scale_risky(trimmed(eff, gaps), c * min(1.25, max(0.75, 0.75 + 0.5 * p))))
        elif kind == 'conf':
            e2 = DOWN.get(eff, eff) if p < 0.2 else eff
            w = trimmed(e2, gaps)
        elif kind == 'repl':
            bs, bl = r['bb'][fam]
            if sign < 0: bs, bl = (not bs), (not bl)
            e2 = effective_state(STATE_TABLE(bs, bl, r['cross']), r['fast'])
            w = trimmed(e2, gaps)
        out = vtf(w, v) if T is None else vtf(w, v, T)
        return cap1(out) if kind in ('iv1', 'iv2') else out
    return fn

KINDS = ['i25', 'i50', 'ii', 'iii', 'iv1', 'iv2', 'conf']
def sub_rows(name):
    return [r for r in rows if r['bp'][name] is not None and r['bb'][FAMILY[name]] is not None]
def expo(rs, fn): return run(rs, fn)[1]
def calib_T(rs, name, kind, sign, target, lo=0.05, hi=3.0):
    """Bisect T so average deployed capital == target. If T saturates (the tilt only de-levers, so even
    an unbounded T cannot restore live's capital), fall back to T=0.20 and bisect a multiplier c on the
    tilt instead (risky capped at 1). Returns (T, c)."""
    for _ in range(45):
        mid = (lo + hi) / 2
        if expo(rs, variant(name, kind, sign, T=mid)) < target: lo = mid
        else: hi = mid
    T = (lo + hi) / 2
    if T < 2.9: return (T, 1.0)
    lo, hi = 1.0, 4.0
    for _ in range(45):
        mid = (lo + hi) / 2
        if expo(rs, variant(name, kind, sign, T=0.20, c=mid)) < target: lo = mid
        else: hi = mid
    return (0.20, (lo + hi) / 2)
def both(ev, b): return ev['s_sharpe'] > b['s_sharpe'] and ev['h_sharpe'] > b['h_sharpe']

nH = len(era(rows, *HOLDOUT)); nS = len(era(rows, *SEARCH))
print(f"\nSAME-ROWS BASELINES (live re-scored on each proxy's rows). Holdout has {nH} rows, search {nS}.")
print(f"  {'series':<10}{'rows':>6}{'first':>12}{'holdout cov':>13}{'live CAGR/Sh/MDD':>26}{'S':>8}{'H':>8}{'exp':>7}")
BASE = {}
for n in NAMES:
    rs = sub_rows(n); b = evaluate(rs, LIVE); BASE[n] = (rs, b)
    hc = len(era(rs, *HOLDOUT))
    print(f"  {n:<10}{len(rs):>6}{rs[0]['d']:>12}{hc:>6}/{nH} {hc/nH*100:3.0f}%{fmt(b):>26}{b['s_sharpe']:>8.3f}{b['h_sharpe']:>8.3f}{b['risky']*100:>6.1f}%")
live_rexp = mean([sum(LIVE_R(r)[:4]) for r in rr])

RESULTS = []   # (name, kind, ev, real, flip_ev, flip_real, T, Tflip)
print("\nVARIANT SCREEN.  Each line: candidate on its proxy rows vs same-rows live (dS, dH = Sharpe minus live in search / holdout),")
print("  exposure (deployed capital, %), real weekly rows Sharpe vs live real, and the sign-flip placebo's dS/dH. 'both' = beats")
print("  live on search AND holdout. iv1/iv2: T* bisected so exposure matches live on the same rows (flip re-calibrated).")
hdr = f"  {'series':<10}{'var':<5}{'CAGR/Sh/MDD':>22}{'dS':>8}{'dH':>8}{'exp':>7}{'both':>6}{'| real Sh':>10}{'dReal':>8}{'| flip dS':>10}{'dH':>8}{'T*/c*':>9}"
print(hdr)
ncand = 0
for n in NAMES:
    rs, b = BASE[n]
    kinds = KINDS + (['repl'] if n in ('qqew_s200', 'rsp_s200', 'nhnl10', 'sec200') else [])
    for kind in kinds:
        ncand += 1
        T = Tf = (None, 1.0)
        if kind in ('iv1', 'iv2'):
            T = calib_T(rs, n, kind, 1, b['risky']); Tf = calib_T(rs, n, kind, -1, b['risky'])
        fn = variant(n, kind, 1, T[0], c=T[1]); ev = evaluate(rs, fn)
        fl = evaluate(rs, variant(n, kind, -1, Tf[0], c=Tf[1]))
        re = RF.eval_real(rr, variant(n, kind, 1, T[0], RF.vt, c=T[1])); rf = RF.eval_real(rr, variant(n, kind, -1, Tf[0], RF.vt, c=Tf[1]))
        RESULTS.append((n, kind, ev, re, fl, rf, T, Tf, b))
        cal_s = '' if T[0] is None else (f'T={T[0]:.3f}' if T[1] == 1.0 else f'c={T[1]:.3f}')
        print(f"  {n:<10}{kind:<5}{fmt(ev):>22}{ev['s_sharpe']-b['s_sharpe']:>+8.3f}{ev['h_sharpe']-b['h_sharpe']:>+8.3f}{ev['risky']*100:>6.1f}%"
              f"{'YES' if both(ev, b) else '-':>6}{re['sharpe']:>10.3f}{re['sharpe']-real_all['sharpe']:>+8.3f}"
              f"{fl['s_sharpe']-b['s_sharpe']:>+10.3f}{fl['h_sharpe']-b['h_sharpe']:>+8.3f}{cal_s:>9}")
npass = sum(1 for x in RESULTS if both(x[2], x[8]))
npass_real = sum(1 for x in RESULTS if both(x[2], x[8]) and x[3]['sharpe'] > real_all['sharpe'])
nflip_pass = sum(1 for x in RESULTS if both(x[4], x[8]))
print(f"\nCANDIDATE COUNT: {ncand} breadth candidates ({len(NAMES)} series x 7 gate/tilt variants + 4 replacement classifiers)."
      f"  both-era passes: {npass};  both-era AND real-rows Sharpe above live: {npass_real}.  Sign-flip placebos passing both-era: {nflip_pass}.")

# ------------------------------------------------------------------ 5. deep controls on the best per family
def live_scaled(k): return lambda r: scale_risky(live_w(r), k)
def exposure_control_live(rs, target, lo=0.0, hi=1.0):
    while expo(rs, live_scaled(hi)) < target and hi < 8: lo, hi = hi, hi * 2
    for _ in range(40):
        mid = (lo + hi) / 2
        if expo(rs, live_scaled(mid)) < target: lo = mid
        else: hi = mid
    k = (lo + hi) / 2
    return k, evaluate(rs, live_scaled(k))
REGIMES = [('dot-com 2000-02', '2000-01-01', '2002-12-31'), ('GFC 2007-09', '2007-01-01', '2009-12-31'),
           ('COVID 2020', '2020-01-01', '2020-12-31'), ('2022 bear', '2022-01-01', '2022-12-31'),
           ('SPMO era 2015-11+', '2015-11-01', '2099-01-01')]

print("\nDEEP CONTROLS on the best variant per proxy FAMILY (selection: largest min(dS, dH) vs same-rows live; a family whose")
print("  best is negative in an era is reported anyway -- that IS the result).")
for fam in (() if QUICK else ('qqew', 'rsp', 'nhnl', 'sec')):
    cands = [x for x in RESULTS if FAMILY[x[0]] == fam]
    best = max(cands, key=lambda x: min(x[2]['s_sharpe'] - x[8]['s_sharpe'], x[2]['h_sharpe'] - x[8]['h_sharpe']))
    n, kind, ev, re, fl, rf, T, Tf, b = best; rs = BASE[n][0]
    fn = variant(n, kind, 1, T[0], c=T[1]); fnf = variant(n, kind, -1, Tf[0], c=Tf[1])
    print(f"\n[{fam}] best = {n} {kind}: {fmt(ev)}  S {ev['s_sharpe']:.3f} (live {b['s_sharpe']:.3f})  H {ev['h_sharpe']:.3f} (live {b['h_sharpe']:.3f})"
          f"  exp {ev['risky']*100:.1f}% (live {b['risky']*100:.1f}%)  both-era {'PASS' if both(ev, b) else 'FAIL'}")
    k1, c1 = exposure_control_live(rs, ev['risky'])
    k2, c2 = exposure_control(rs, ev['risky'])
    print(f"   exposure control, LIVE design scaled k={k1:.3f} to {c1['risky']*100:.1f}%: {fmt(c1)}  S {c1['s_sharpe']:.3f} H {c1['h_sharpe']:.3f}"
          f"  -> candidate beats it both eras: {both(ev, c1)}")
    print(f"   downturn_review.exposure_control (macro-only/vol30 baseline) k={k2:.3f} matched={c2['exp_matched']}: {fmt(c2)}  S {c2['s_sharpe']:.3f} H {c2['h_sharpe']:.3f}")
    print(f"   sign-flip placebo: {fmt(fl)}  S {fl['s_sharpe']:.3f} H {fl['h_sharpe']:.3f}  both-era {'PASS' if both(fl, b) else 'FAIL'}"
          f"   (a real signal must LOSE when flipped: flip full Sharpe {fl['sharpe']-ev['sharpe']:+.3f} vs candidate)")
    print(f"   real weekly rows: candidate {fmt(re)} vs live {fmt(real_all)}  (dSharpe {re['sharpe']-real_all['sharpe']:+.3f}); flip {fmt(rf)}")
    a = run(rs, fn)[0]; bl = run(rs, LIVE)[0]; af = run(rs, fnf)[0]
    la, sa = stats(a); lb, sb = stats(bl)
    print(f"   BLOCK BOOTSTRAP vs same-rows live ({N_BOOT} draws, {len(rs)} sessions): point {(la-lb)*100:+.2f}pp/yr log-return, {sa-sb:+.3f} Sharpe")
    for blk in (20, 60):
        l1, l2, pl, s1, s2, ps = boot(a, bl, blk, seed=zlib.crc32(f'{n}|{kind}|{blk}'.encode()))
        print(f"      block {blk:>2}d: log-return 95% CI [{l1*100:+.2f}, {l2*100:+.2f}] pp/yr P(<=0)={pl:.3f}   Sharpe CI [{s1:+.3f}, {s2:+.3f}] P(<=0)={ps:.3f}")
    lf, sf = stats(af)
    l1, l2, pl, s1, s2, ps = boot(af, bl, 20, seed=zlib.crc32(f'{n}|{kind}|flip'.encode()))
    print(f"      flip, block 20d: point {(lf-lb)*100:+.2f}pp/yr, {sf-sb:+.3f} Sharpe; Sharpe CI [{s1:+.3f}, {s2:+.3f}] P(<=0)={ps:.3f}")
    print("   leave-one-regime-out (Sharpe diff vs same-rows live, window removed):")
    for rlab, a0, b0 in REGIMES:
        keep = [i for i, r in enumerate(rs) if not (a0 <= r['d'] <= b0)]
        if len(keep) == len(rs): print(f"      drop {rlab:<20} (window not covered by this proxy)"); continue
        _, s1 = stats([a[i] for i in keep]); _, s2 = stats([bl[i] for i in keep])
        print(f"      drop {rlab:<20} {s1-s2:+.3f}")

# ------------------------------------------------------------------ 6. where does breadth fire? exposure accounting
print("\nWHERE THE GATES FIRE: share of A/D rows with bottom-quintile breadth, by era, and live-design mean next-day return on those rows")
print(f"  {'series':<10}{'A/D rows':>9}{'bottom-Q':>9}{'S share':>9}{'H share':>9}{'live r(d1) botQ':>17}{'live r(d1) rest':>17}")
for n in NAMES:
    rs, b = BASE[n]; lr = run(rs, LIVE)[0]
    ad = [(r, x) for r, x in zip(rs, lr) if r['eff'] in ('A', 'D')]
    bq = [(r, x) for r, x in ad if r['bp'][n] < 0.2]; rest = [(r, x) for r, x in ad if r['bp'][n] >= 0.2]
    sS = sum(1 for r, _ in bq if r['d'] >= SEARCH[0]) / max(1, sum(1 for r, _ in ad if r['d'] >= SEARCH[0]))
    sH = sum(1 for r, _ in bq if r['d'] < SEARCH[0]) / max(1, sum(1 for r, _ in ad if r['d'] < SEARCH[0]))
    print(f"  {n:<10}{len(ad):>9}{len(bq):>9}{sS*100:>8.1f}%{sH*100:>8.1f}%{mean([x for _, x in bq])*1e4:>14.1f}bp{mean([x for _, x in rest])*1e4:>14.1f}bp")
# ------------------------------------------------------------------ 7. robustness of the survivors: de-lever ladder, threshold, scope
def gate_fn(name, k, thr=0.2, scope=('A', 'D'), vtf=vt):
    def fn(r):
        w = trimmed(r['eff'], r['gaps'])
        if r['eff'] in scope and r['bp'][name] < thr: w = scale_risky(w, 1 - k)
        return vtf(w, r['vol'])
    return fn
SURV = [x for x in RESULTS if both(x[2], x[8]) and x[1] in ('i25', 'i50')]
SURV_NAMES = sorted(set(x[0] for x in SURV))
print("\nSURVIVOR ROBUSTNESS (the de-lever gate on every series that passed both eras with i25/i50). Briefing lesson: a win that")
print("  grows MONOTONICALLY with the de-lever depth while CAGR falls is a risk-preference dial, not a signal. Each cell is the gate")
print("  vs the LIVE design scaled to the same deployed capital (k-control); bootstrap is 20d blocks, Sharpe CI vs same-rows live.")
print(f"  {'series':<10}{'depth':>6}{'thr':>5}{'scope':>6}{'CAGR/Sh/MDD':>22}{'S':>7}{'H':>7}{'exp':>7}{'| k-ctrl Sh':>12}{'S':>7}{'H':>7}{'both>ctrl':>10}{'| boot Sh CI 20d':>18}{'P<=0':>6}")
for n in ([] if QUICK else SURV_NAMES):
    rs, b = BASE[n]; bl = run(rs, LIVE)[0]
    grid = [(k, 0.2, ('A', 'D')) for k in (0.25, 0.5, 0.75, 1.0)] + [(0.5, t, ('A', 'D')) for t in (0.1, 0.3)] + \
           [(0.5, 0.2, ('A',)), (0.5, 0.2, ('A', 'B', 'C', 'D'))]
    for k, t, sc in grid:
        fn = gate_fn(n, k, t, sc); ev = evaluate(rs, fn); kk, c = exposure_control_live(rs, ev['risky'])
        a = run(rs, fn)[0]; _, _, _, s1, s2, ps = boot(a, bl, 20, seed=zlib.crc32(f'{n}|lad|{k}|{t}|{len(sc)}'.encode()))
        print(f"  {n:<10}{k*100:>5.0f}%{t:>5.1f}{''.join(sc):>6}{fmt(ev):>22}{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f}{ev['risky']*100:>6.1f}%"
              f"{c['sharpe']:>12.3f}{c['s_sharpe']:>7.3f}{c['h_sharpe']:>7.3f}{'YES' if both(ev, c) else '-':>10}"
              f"   [{s1:+.3f}, {s2:+.3f}]{ps:>6.3f}")
# ------------------------------------------------------------------ 8. is it the D row? D-only gate vs a CONSTANT D de-lever at the same capital
def const_D(q, vtf=vt):
    """live design with the D row held at q x QLD (rest cash) ALWAYS -- no breadth."""
    def fn(r):
        w = trimmed(r['eff'], r['gaps'])
        if r['eff'] == 'D': w = scale_risky(w, q)
        return vtf(w, r['vol'])
    return fn
def calib_q(rs, target):
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if expo(rs, const_D(mid)) < target: lo = mid
        else: hi = mid
    return (lo + hi) / 2
print("\nIS IT THE D ROW?  The A-only gate fails everywhere above, so the surviving gates earn their Sharpe by cutting the D row")
print("  (100% QLD; price below 50d, above 200d). Control: the D row held at a CONSTANT fraction q of QLD, q bisected so deployed")
print("  capital equals the D-only gate's. If the constant cut does as well, breadth is only re-discovering that D is a leverage dial.")
print(f"  {'series':<10}{'rule':<22}{'CAGR/Sh/MDD':>22}{'S':>7}{'H':>7}{'exp':>7}{'| real Sh':>10}{'| vs const-D: dS':>17}{'dH':>7}{'dSh full':>9}{'boot Sh CI 20d':>18}{'P<=0':>6}")
for n in SURV_NAMES:
    rs, b = BASE[n]
    for depth in (0.5, 1.0):
        fn = gate_fn(n, depth, 0.2, ('D',)); ev = evaluate(rs, fn); re = RF.eval_real(rr, gate_fn(n, depth, 0.2, ('D',), RF.vt))
        q = calib_q(rs, ev['risky']); cf = const_D(q); ce = evaluate(rs, cf); cre = RF.eval_real(rr, const_D(q, RF.vt))
        a = run(rs, fn)[0]; bl = run(rs, cf)[0]
        _, _, _, s1, s2, ps = boot(a, bl, 20, seed=zlib.crc32(f'{n}|D|{depth}'.encode()))
        print(f"  {n:<10}{f'D-only gate {depth*100:.0f}%':<22}{fmt(ev):>22}{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f}{ev['risky']*100:>6.1f}%{re['sharpe']:>10.3f}"
              f"{ev['s_sharpe']-ce['s_sharpe']:>+17.3f}{ev['h_sharpe']-ce['h_sharpe']:>+7.3f}{ev['sharpe']-ce['sharpe']:>+9.3f}   [{s1:+.3f}, {s2:+.3f}]{ps:>6.3f}")
        print(f"  {'':<10}{f'  const D q={q:.3f}':<22}{fmt(ce):>22}{ce['s_sharpe']:>7.3f}{ce['h_sharpe']:>7.3f}{ce['risky']*100:>6.1f}%{cre['sharpe']:>10.3f}")
# ------------------------------------------------------------------ 9. the D-only gate, taken seriously: every series, non-breadth placebos, episodes
# non-breadth gates on the same D rows: QQQ's own 60d log change (price momentum) and 30d realized vol (sign: HIGH vol = weak)
qlr = [math.log(px[d]) for d in ds]
series['qqq_60'] = [None] * len(cal)
for i, d in enumerate(ds):
    if i >= 60: series['qqq_60'][cix[d]] = qlr[i] - qlr[i - 60]
series['negvol30'] = [None] * len(cal)
for r in rows: series['negvol30'][cix[r['d']]] = -r['vol']
for k in ('qqq_60', 'negvol30'):
    pct[k] = trailing_pct(series[k]); FAMILY[k] = 'ctrl'
    for r in rows: r['bp'][k] = pct[k][cix[r['d']]]
    for r in rr:
        d = r['d0'] if r['d0'] in cix else cal[bisect.bisect_right(cal, r['d0']) - 1]
        r['bp'][k] = pct[k][cix[d]]
ALL9 = NAMES + ['qqq_60', 'negvol30']
print("\nTHE D-ONLY GATE ON EVERY SERIES (plus two NON-BREADTH placebos on the same rows: QQQ's own 60d momentum percentile and")
print("  the 30d-vol percentile, sign so that 'bottom quintile' = weak). Rule: effective state D and pct < 0.2 -> D row x(1-depth).")
print("  Controls per line: same-rows live, constant-D at matched capital (q), LIVE scaled to matched capital (k), sign-flip.")
print(f"  {'series':<10}{'depth':>6}{'CAGR/Sh/MDD':>22}{'S':>7}{'H':>7}{'exp':>7}{'| dS/dH vs live':>16}{'| vs constD':>12}{'| vs k-live':>12}{'| flip vs constD':>17}{'| real':>8}{'dReal':>7}{'rows on':>8}")
D9 = {}
for n in ALL9:
    rs = [r for r in rows if r['bp'][n] is not None]; b = evaluate(rs, LIVE)
    for depth in (0.5, 1.0):
        fn = gate_fn(n, depth, 0.2, ('D',)); ev = evaluate(rs, fn)
        q = calib_q(rs, ev['risky']); ce = evaluate(rs, const_D(q)); k, ke = exposure_control_live(rs, ev['risky'])
        ff = lambda r, n=n, depth=depth: (lambda w: vt(w, r['vol']))(scale_risky(trimmed(r['eff'], r['gaps']), 1 - depth) if (r['eff'] == 'D' and r['bp'][n] >= 0.8) else trimmed(r['eff'], r['gaps']))
        fe = evaluate(rs, ff); qf = calib_q(rs, fe['risky']); cfe = evaluate(rs, const_D(qf))
        re = RF.eval_real(rr, gate_fn(n, depth, 0.2, ('D',), RF.vt))
        on = sum(1 for r in rs if r['eff'] == 'D' and r['bp'][n] < 0.2)
        D9[(n, depth)] = (rs, b, ev, ce, q, re)
        print(f"  {n:<10}{depth*100:>5.0f}%{fmt(ev):>22}{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f}{ev['risky']*100:>6.1f}%"
              f"{ev['s_sharpe']-b['s_sharpe']:>+8.3f}{ev['h_sharpe']-b['h_sharpe']:>+8.3f}"
              f"{ev['s_sharpe']-ce['s_sharpe']:>+6.3f}{ev['h_sharpe']-ce['h_sharpe']:>+6.3f}"
              f"{ev['s_sharpe']-ke['s_sharpe']:>+6.3f}{ev['h_sharpe']-ke['h_sharpe']:>+6.3f}"
              f"{fe['s_sharpe']-cfe['s_sharpe']:>+9.3f}{fe['h_sharpe']-cfe['h_sharpe']:>+8.3f}"
              f"{re['sharpe']:>8.3f}{re['sharpe']-real_all['sharpe']:>+7.3f}{on:>8}")
nD = sum(1 for r in rows if r['eff'] == 'D')
print(f"  (effective-state-D rows in the full proxy: {nD} of {len(rows)} = {nD/len(rows)*100:.1f}%; the gate is OFF everywhere else)")

TOP = [('qqew_60', 1.0), ('qqew_s200', 1.0), ('rsp_20', 1.0), ('qqew_60', 0.5)]
print("\nDEEP CONTROLS ON THE D-ONLY GATE (bootstrap vs same-rows live AND vs the constant-D control; LORO; thresholds; by-year)")
for n, depth in TOP:
    rs, b, ev, ce, q, re = D9[(n, depth)]
    fn = gate_fn(n, depth, 0.2, ('D',)); a = run(rs, fn)[0]; bl = run(rs, LIVE)[0]; bc = run(rs, const_D(q))[0]
    la, sa = stats(a); lb, sb = stats(bl); lc, sc = stats(bc)
    print(f"\n[{n} D-only {depth*100:.0f}%] {fmt(ev)} S {ev['s_sharpe']:.3f} H {ev['h_sharpe']:.3f} | live {fmt(b)} | const-D q={q:.3f} {fmt(ce)} | real {fmt(re)}")
    print(f"   point vs live {(la-lb)*100:+.2f}pp/yr {sa-sb:+.3f} Sh; vs const-D {(la-lc)*100:+.2f}pp/yr {sa-sc:+.3f} Sh")
    for lab, ref in (('live', bl), ('const-D', bc)):
        for blk in (20, 60):
            l1, l2, pl, s1, s2, ps = boot(a, ref, blk, seed=zlib.crc32(f'{n}|D9|{depth}|{lab}|{blk}'.encode()))
            print(f"      vs {lab:<8} block {blk:>2}d: log-return CI [{l1*100:+.2f}, {l2*100:+.2f}] P(<=0)={pl:.3f}   Sharpe CI [{s1:+.3f}, {s2:+.3f}] P(<=0)={ps:.3f}")
    print("   leave-one-regime-out (Sharpe diff vs const-D / vs live):")
    for rlab, a0, b0 in REGIMES:
        keep = [i for i, r in enumerate(rs) if not (a0 <= r['d'] <= b0)]
        if len(keep) == len(rs): print(f"      drop {rlab:<20} (not covered)"); continue
        _, s1 = stats([a[i] for i in keep]); _, s2 = stats([bc[i] for i in keep]); _, s3 = stats([bl[i] for i in keep])
        print(f"      drop {rlab:<20} {s1-s2:+.3f} / {s1-s3:+.3f}")
    print("   threshold sensitivity (pct <): " + "  ".join(
        f"{t:.2f}: Sh {evaluate(rs, gate_fn(n, depth, t, ('D',)))['sharpe']:.3f} S {evaluate(rs, gate_fn(n, depth, t, ('D',)))['s_sharpe']:.3f} H {evaluate(rs, gate_fn(n, depth, t, ('D',)))['h_sharpe']:.3f}"
        for t in (0.1, 0.2, 0.3, 0.5)))
    by = {}
    for r, x, y in zip(rs, a, bl):
        yv = by.setdefault(r['d'][:4], [0.0, 0.0, 0]); yv[0] += math.log1p(x); yv[1] += math.log1p(y); yv[2] += 1 if (r['eff'] == 'D' and r['bp'][n] < 0.2) else 0
    print("   by year (gate minus live, pp; days gate on): " + "  ".join(f"{y}:{(v[0]-v[1])*100:+.1f}({v[2]})" for y, v in sorted(by.items()) if v[2] > 0 or abs(v[0]-v[1]) > 1e-9))
    # episodes: contiguous runs of gate-on days; live D-row return over the run
    eps = []; cur = None
    for r, y in zip(rs, bl):
        on = r['eff'] == 'D' and r['bp'][n] < 0.2
        if on:
            if cur is None: cur = [r['d'], r['d'], 0.0, 0]
            cur[1] = r['d']; cur[2] += math.log1p(y); cur[3] += 1
        elif cur is not None: eps.append(cur); cur = None
    if cur: eps.append(cur)
    eps.sort(key=lambda e: e[2])
    print(f"   {len(eps)} gate episodes, {sum(e[3] for e in eps)} days; live return over gated days summed {sum(e[2] for e in eps)*100:+.1f}pp;"
          f" worst 8: " + "  ".join(f"{e[0]}..{e[1]}({e[3]}d {e[2]*100:+.1f})" for e in eps[:8]))
    print(f"   best 5: " + "  ".join(f"{e[0]}..{e[1]}({e[3]}d {e[2]*100:+.1f})" for e in eps[-5:]))
# ------------------------------------------------------------------ 10. breaking the D-gate: per-day stats, windows, era vs instrument, lag/random placebos
import random
def tstat(a):
    m = mean(a); sd_ = (sum((x - m) ** 2 for x in a) / (len(a) - 1)) ** 0.5
    return m / (sd_ / math.sqrt(len(a)))
print("\nPER-DAY STATISTICS OF THE D ROW (QLD leg, d0->d1) ON GATED vs OTHER STATE-D DAYS.  The Sharpe could be eight crash days;")
print("  this is the distribution. t = t-stat of the mean; hit = share of positive days.")
print(f"  {'series':<10}{'era':<8}{'gated n':>8}{'mean bp':>9}{'median':>8}{'t':>7}{'hit':>6}{'| other n':>10}{'mean bp':>9}{'median':>8}{'hit':>6}{'| diff t':>9}")
for n in ('qqew_60', 'qqew_s200', 'rsp_20', 'rsp_60', 'sec200', 'qqq_60'):
    rs = [r for r in rows if r['bp'][n] is not None]
    for lab, lo, hi in (('full', '0000', '9999'), ('search', SEARCH[0], '9999'), ('holdout', '0000', SEARCH[0])):
        gd = [r['legs'][2] for r in rs if r['eff'] == 'D' and r['bp'][n] < 0.2 and lo <= r['d'] < hi]
        od = [r['legs'][2] for r in rs if r['eff'] == 'D' and r['bp'][n] >= 0.2 and lo <= r['d'] < hi]
        if len(gd) < 5 or len(od) < 5: continue
        sg = sorted(gd); so = sorted(od)
        pooled = ((sum((x - mean(gd)) ** 2 for x in gd) + sum((x - mean(od)) ** 2 for x in od)) / (len(gd) + len(od) - 2)) ** 0.5
        dt = (mean(gd) - mean(od)) / (pooled * math.sqrt(1 / len(gd) + 1 / len(od)))
        print(f"  {n:<10}{lab:<8}{len(gd):>8}{mean(gd)*1e4:>9.1f}{sg[len(sg)//2]*1e4:>8.1f}{tstat(gd):>7.2f}{sum(1 for x in gd if x > 0)/len(gd):>6.2f}"
              f"{len(od):>10}{mean(od)*1e4:>9.1f}{so[len(so)//2]*1e4:>8.1f}{sum(1 for x in od if x > 0)/len(od):>6.2f}{dt:>9.2f}")

print("\nWINDOW SENSITIVITY of the equal-weight ratio change, D-only gate 100% (each is one more candidate):")
print(f"  {'series':<10}{'rows':>6}{'CAGR/Sh/MDD':>22}{'S':>7}{'H':>7}{'| live Sh':>10}{'S':>7}{'H':>7}{'| vs constD S':>14}{'H':>7}{'| real Sh':>10}{'on':>5}")
NW = 0
for tag in ('qqew', 'rsp'):
    for w in (10, 20, 40, 60, 90, 120, 250):
        key = f'{tag}_{w}'
        if key not in series:
            series[key] = diffs(aux[tag], w); pct[key] = trailing_pct(series[key]); FAMILY[key] = tag
            for r in rows: r['bp'][key] = pct[key][cix[r['d']]]
            for r in rr:
                d = r['d0'] if r['d0'] in cix else cal[bisect.bisect_right(cal, r['d0']) - 1]
                r['bp'][key] = pct[key][cix[d]]
        NW += 1
        rs = [r for r in rows if r['bp'][key] is not None]; b = evaluate(rs, LIVE)
        fn = gate_fn(key, 1.0, 0.2, ('D',)); ev = evaluate(rs, fn); q = calib_q(rs, ev['risky']); ce = evaluate(rs, const_D(q))
        re = RF.eval_real(rr, gate_fn(key, 1.0, 0.2, ('D',), RF.vt)); on = sum(1 for r in rs if r['eff'] == 'D' and r['bp'][key] < 0.2)
        print(f"  {key:<10}{len(rs):>6}{fmt(ev):>22}{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f}{b['sharpe']:>10.3f}{b['s_sharpe']:>7.3f}{b['h_sharpe']:>7.3f}"
              f"{ev['s_sharpe']-ce['s_sharpe']:>+14.3f}{ev['h_sharpe']-ce['h_sharpe']:>+7.3f}{re['sharpe']:>10.3f}{on:>5}")

print("\nERA vs INSTRUMENT: the RSP/SPY gates scored on the QQEW rows (2007-07+), so the two equal-weight proxies face the same history.")
ERA_KEYS = ('qqew_60', 'rsp_60', 'rsp_20', 'rsp_s200', 'qqew_s200')
rsq = [r for r in rows if all(r['bp'][k] is not None for k in ERA_KEYS)]; bq = evaluate(rsq, LIVE)
print(f"  same rows n={len(rsq)}: live {fmt(bq)} S {bq['s_sharpe']:.3f} H {bq['h_sharpe']:.3f}")
for key in ERA_KEYS:
    fn = gate_fn(key, 1.0, 0.2, ('D',)); ev = evaluate(rsq, fn); q = calib_q(rsq, ev['risky']); ce = evaluate(rsq, const_D(q))
    print(f"  {key:<10} D-gate 100%: {fmt(ev)} S {ev['s_sharpe']:.3f} H {ev['h_sharpe']:.3f}  vs const-D S {ev['s_sharpe']-ce['s_sharpe']:+.3f} H {ev['h_sharpe']-ce['h_sharpe']:+.3f}")
# overlap of the two gates
both_on = sum(1 for r in rsq if r['eff'] == 'D' and r['bp']['qqew_60'] < 0.2 and r['bp']['rsp_60'] < 0.2)
q_on = sum(1 for r in rsq if r['eff'] == 'D' and r['bp']['qqew_60'] < 0.2); r_on = sum(1 for r in rsq if r['eff'] == 'D' and r['bp']['rsp_60'] < 0.2)
print(f"  gated D-days: qqew_60 {q_on}, rsp_60 {r_on}, both {both_on}")

print("\nLAG AND RANDOM-EPISODE PLACEBOS for qqew_60 D-only 100% (same rows). Lag k: use the percentile from k sessions EARLIER")
print("  (still causal, just stale). Random: the gate's on/off pattern within state-D days is circularly shifted by a random offset,")
print("  preserving episode lengths; 300 shifts; P = share of shifts whose Sharpe >= the actual gate's.")
rs = rsq; base_ev = evaluate(rs, gate_fn('qqew_60', 1.0, 0.2, ('D',)))
pq = pct['qqew_60']
for lag in (5, 21, 63, 252):
    def lagfn(r, lag=lag):
        i = cix[r['d']] - lag; p = pq[i] if i >= 0 else None
        w = trimmed(r['eff'], r['gaps'])
        if r['eff'] == 'D' and p is not None and p < 0.2: w = scale_risky(w, 0.0)
        return vt(w, r['vol'])
    ev = evaluate(rs, lagfn)
    print(f"  lag {lag:>3}: {fmt(ev)} S {ev['s_sharpe']:.3f} H {ev['h_sharpe']:.3f}   (actual gate {base_ev['sharpe']:.3f}, live {bq['sharpe']:.3f})")
didx = [i for i, r in enumerate(rs) if r['eff'] == 'D']; pattern = [rs[i]['bp']['qqew_60'] < 0.2 for i in didx]
rng = random.Random(7); shs = []
for _ in range(300):
    off = rng.randrange(1, len(didx)); shifted = pattern[-off:] + pattern[:-off]
    shs.append({didx[j] for j, f in enumerate(shifted) if f})
for i, r in enumerate(rs): r['_i'] = i
vals = []
for onset in shs:
    fn = (lambda onset: lambda r: vt(scale_risky(trimmed(r['eff'], r['gaps']), 0.0) if r['_i'] in onset else trimmed(r['eff'], r['gaps']), r['vol']))(onset)
    vals.append(evaluate(rs, fn)['sharpe'])
vals.sort()
print(f"  random-episode Sharpe: median {vals[len(vals)//2]:.3f}, 95th pct {vals[int(0.95*len(vals))]:.3f}, max {vals[-1]:.3f}; actual {base_ev['sharpe']:.3f};"
      f" P(random >= actual) = {sum(1 for v in vals if v >= base_ev['sharpe'])/len(vals):.3f}")

print("\nREAL WEEKLY ROWS, qqew_60 D-only gate: which weeks are gated and what they cost/saved")
gw = [(r['d0'], r['legs'][2]) for r in rr if r['eff'] == 'D' and r['bp']['qqew_60'] < 0.2]
print(f"  {len(gw)} of {len(rr)} weeks gated; QLD leg over those weeks: " + "  ".join(f"{d}:{x*100:+.1f}%" for d, x in gw))
print(f"  sum {sum(x for _, x in gw)*100:+.1f}%, mean {mean([x for _, x in gw])*100:+.2f}%/wk; other state-D weeks mean "
      f"{mean([r['legs'][2] for r in rr if r['eff'] == 'D' and r['bp']['qqew_60'] >= 0.2])*100:+.2f}%/wk (n={sum(1 for r in rr if r['eff'] == 'D' and r['bp']['qqew_60'] >= 0.2)})")

last = rows[-1]
print(f"\nTODAY: last proxy row {last['d']} state {last['state']} eff {last['eff']}; qqew_60 pct {last['bp']['qqew_60']:.2f}, rsp_20 pct {last['bp']['rsp_20']:.2f}."
      f" On 2026-09-09: qqew_60 pct {pct['qqew_60'][cix['2026-09-09']]:.2f}, qqew_s200 {pct['qqew_s200'][cix['2026-09-09']]:.2f}, rsp_20 {pct['rsp_20'][cix['2026-09-09']]:.2f}, sec200 {pct['sec200'][cix['2026-09-09']]:.2f}.")
print(f"TOTAL CANDIDATES EXAMINED: {ncand} screen + {8*len(SURV_NAMES)} survivor ladder + {2*len(ALL9)} D-only (incl. 4 non-breadth placebo cells) + {NW} window sweep = "
      f"{ncand + 8*len(SURV_NAMES) + 2*len(ALL9) + NW}. The D-only scope was chosen AFTER seeing the ladder (post hoc).")
print("\nDone.")
