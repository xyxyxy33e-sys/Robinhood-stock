"""Research line `d_substate_fresh` (2026-09-19): a FRESH sub-state search inside
state D (QQQ below its 50d, above its 200d, 50d > 200d; the live row is 100% QLD).

Owner request: "take another look into substate of D, start fresh, ignore the
previous finding, test various dma lines and other concepts." The two earlier
negative studies (de_substate_search.py: 9 QQQ-close signals x 108 candidates;
downturn_review.py P3: gap-to-200d) are NOT inherited here -- only their
evaluation scaffolding is (era split, exposure-matched control, max-statistic
permutation). The candidate set is new in emphasis: additional DMA lines and
their slopes/crossovers, the fast 20/100 reading as a D-splitter, episode
age/depth, EMA variants, and non-DMA concepts (vol regime, drawdown, RSI,
consecutive down days, momentum, range expansion, QQQ/SPY relative strength,
T-bill change, VIX), singly and in pairs (AND / OR), with FIVE actions on the
flagged half of D and the same five on the complement -- including the UPSIDE
action (D -> the A row, 50/50 SPMO/TQQQ), because the owner's objective is to
beat SPY/QQQ, not only to de-risk.

Research only. Nothing is applied. Discipline per BRIEFING.md (ADDENDUM
2026-09-10): project harness only (leverage_under_trim bootstrap -> rows, run,
evaluate; RF.eval_real for real weekly rows; a VERIFIED mirror of
monthly_returns.simulate for the real DAILY rows), standing figures asserted,
both-era hurdle, exposure- and beta-matched controls, max-statistic
permutation over the WHOLE grid, block bootstrap, leave-one-regime-out,
threshold sensitivity, next-day-return profiles, SPY as an independent series.

DATA SHIM (no repo file written): monthly_returns.py / voltarget_live_backtest.py
/ backtest_overlay_etf.py hard-code /home/user/robinhood/data/kairos, which does
not exist here. A temp symlink farm maps SPMO/TQQQ/QLD/XLU -> data/*_ohlc.csv and
DGS3MO -> data/dgs3mo_full.csv (as funding_pct_backtest.py does). BOXX has no
local file: a SYNTHETIC BOXX.csv is written from the 3-month T-bill index
(cash_index * 100, full QQQ calendar) and monthly_returns.TAIL['BOXX'] is
neutralised in-process -- with the TAIL left in, the 118.07 close it injects on
2026-08-31 would register as a fake +11,700% cash-leg day against a 1.0-based
index. The weekly real rows (RF.real_rows) read the same synthetic BOXX, which is
the same T-bill index build_cash_index() would have fallen back to anyway.

Run from the repo root:
    python3 paper-track/d_substate_fresh.py            # grid + permutation + diagnostics (~40 min)
    DSF_STAGE=grid python3 paper-track/d_substate_fresh.py
    DSF_STAGE=perm python3 ...   (needs grid json)      DSF_NPERM=200 (default) DSF_PROCS=4
    DSF_STAGE=diag python3 ...   (needs grid + perm json; DSF_DEEP=335,305 forces deep diagnostics on those ids)
Intermediates go to the scratchpad (DSF_SCRATCH).
"""
import sys, os, math, json, random, csv, bisect, time, tempfile
from datetime import date, timedelta

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)
sys.path.insert(0, 'paper-track')
SCRATCH = os.environ.get('DSF_SCRATCH',
                         '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad')
os.makedirs(SCRATCH, exist_ok=True)
STAGE = os.environ.get('DSF_STAGE', 'all')
N_PERM = int(os.environ.get('DSF_NPERM', '200'))
N_PROCS = int(os.environ.get('DSF_PROCS', '4'))
SEED = 20260919

T0 = time.time()
def log(*a):
    print(*a, flush=True)

# ---------------------------------------------------------------- data shim
from long_history_backtest import (load_px, load_tbill_long, make_rate_lookup, synth_leveraged,
                                   total_return_index, cash_index, START, QQQ_DIV_PA, XLU_DIV_PA,
                                   TQQQ_ER, QLD_ER)
_TMP = os.path.join(SCRATCH, 'kairos_shim')
_ETF = os.path.join(_TMP, 'etf')
os.makedirs(_ETF, exist_ok=True)
for dst, src in {'SPMO.csv': 'spmo_ohlc.csv', 'TQQQ.csv': 'tqqq_ohlc.csv',
                 'QLD.csv': 'qld_ohlc.csv', 'XLU.csv': 'xlu_ohlc.csv'}.items():
    p = os.path.join(_ETF, dst)
    if not os.path.lexists(p):
        os.symlink(os.path.join(REPO_ROOT, 'data', src), p)
p = os.path.join(_TMP, 'DGS3MO.csv')
if not os.path.lexists(p):
    os.symlink(os.path.join(REPO_ROOT, 'data', 'dgs3mo_full.csv'), p)
_QQQ_FULL = load_px('data/qqq_long_history.csv')
_QD_FULL = sorted(_QQQ_FULL)
_RATE_ON = make_rate_lookup(load_tbill_long())
_boxx = os.path.join(_ETF, 'BOXX.csv')
if not os.path.exists(_boxx):
    ci = cash_index(_QD_FULL, _RATE_ON)
    with open(_boxx, 'w') as f:
        f.write('d,c\n')
        for d in _QD_FULL:
            f.write(f'{d},{ci[d]*100:.6f}\n')
import backtest_overlay_etf as BOE
import voltarget_live_backtest as VL
import monthly_returns as MR
# 2026-09-19: this research harness is PINNED to the pre-2026-09-19 live design.
# state.py's E row went to 100% cash later that day; the standing figures below
# were produced with E = 50% XLU / 50% cash, so restore that row IN PLACE (the
# dict object is shared by every module that imported TARGET_WEIGHTS).
import state as _ST
_ST.TARGET_WEIGHTS['E'] = (0.0, 0.0, 0.0, 0.50, 0.50)
BOE.ROBINHOOD_REPO = _TMP
VL.REPO = _TMP
MR.REPO = _ETF
MR.TAIL['BOXX'] = {}          # see module docstring: synthetic BOXX already covers 2026-09-04

# ---------------------------------------------------------------- harness bootstrap
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from state import (extension_scale, compute_states, compute_fast_states, effective_state,
                   compute_extension_gaps, extension_votes, realized_vol_live, realized_vol,
                   target_weights_with_voltarget, needs_rebalance, sma as _sma_at,
                   VOL_TARGET_PA, REBALANCE_DRIFT_BAND, FAST_SHORT_N, FAST_LONG_N)
from improvement_search import SEARCH, HOLDOUT, era, _vol
from improvement_search_r2 import scaled, beta_of, BETA
from block_bootstrap import boot, stats as bstats, N_BOOT, REGIMES
from drift_band_test import annual_stats, ONE_WAY_SPREAD

def trimmed(r):
    w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
    if f < 1: w = tuple(a * f for a in w[:4]) + (1 - f * sum(w[:4]),)
    return w
def live_fn(r):
    return vt(trimmed(r), r['vol'])
def live_rr(r):
    return RF.vt(trimmed(r), r['vol'])

ev0 = evaluate(rows, live_fn); er0 = RF.eval_real(rr, live_rr)
log("=" * 110)
log("RESEARCH LINE d_substate_fresh -- fresh sub-state search inside state D")
log("=" * 110)
log(f"STANDING FIGURES (must match 22.18% / 0.913 / -33.6%, S 1.103, H 0.768; real weekly ~31.40% / 1.248 / -25.0%)")
log(f"  26y proxy {ev0['cagr']*100:.2f}% / {ev0['sharpe']:.3f} / {ev0['mdd']*100:.1f}%  S {ev0['s_sharpe']:.3f}  H {ev0['h_sharpe']:.3f}"
    f"  exposure {ev0['risky']*100:.1f}% | real weekly {er0['cagr']*100:.2f}% / {er0['sharpe']:.3f} / {er0['mdd']*100:.1f}%"
    f"  ({len(rows)} proxy rows {rows[0]['d']}..{rows[-1]['d']}, {len(rr)} real weekly rows)")
assert abs(ev0['sharpe'] - 0.913) < 0.002 and abs(er0['sharpe'] - 1.248) < 0.002, 'standing figures not reproduced'
BASE = {r['d']: live_fn(r) for r in rows}          # live target per proxy row (speed)

# run() with a rebalance counter -- identical arithmetic to improvement_search.run (verified below)
def run_count(rs, wfn, band=REBALANCE_DRIFT_BAND):
    held = prev = None; rets, risky, nreb = [], 0.0, 0
    for r in rs:
        t = wfn(r); key = (r['state'], r['agree']); cost = 0.0
        if held is None:
            held = list(t); nreb += 1
        else:
            drift = sum(abs(t[j] - held[j]) for j in range(5))
            if key != prev or drift > band:
                cost = ONE_WAY_SPREAD * drift; held = list(t); nreb += 1
        risky += sum(held[:4])
        g = sum(held[j] * r['legs'][j] for j in range(5))
        rets.append(g - cost)
        dn = 1 + g
        if dn > 0: held = [held[j] * (1 + r['legs'][j]) / dn for j in range(5)]
        prev = key
    return rets, risky / len(rs), nreb / (len(rs) / 252.0)
_a, _b = run(rows, live_fn), run_count(rows, live_fn)
assert _a[0] == _b[0] and abs(_a[1] - _b[1]) < 1e-12, 'run_count does not reproduce run()'
LIVE_SER, LIVE_EXP, LIVE_REB = _b
log(f"  live rebalances/yr {LIVE_REB:.1f}")

def sliced_sharpe(ser, lo, hi):
    x = [v for r, v in zip(rows, ser) if lo <= r['d'] <= hi]
    return bstats(x)[1]
D_ROWS = [i for i, r in enumerate(rows) if r['state'] == 'D']
assert all(rows[i]['eff'] == 'D' for i in D_ROWS)
nD = len(D_ROWS)
log(f"  state D: {nD} proxy days ({nD/len(rows)*100:.1f}%), search {sum(1 for i in D_ROWS if rows[i]['d'] >= SEARCH[0])}, "
    f"holdout {sum(1 for i in D_ROWS if rows[i]['d'] < SEARCH[0])}")

# ---------------------------------------------------------------- signals (point-in-time, on a price calendar)
def fred(path, col):
    out, last = {}, None
    for r in csv.DictReader(open(path)):
        v = r[col].strip()
        if v and v != '.':
            last = float(v)
        if last is not None:
            out[r['observation_date']] = last
    return out
VIX = fred('data/vixcls_full.csv', 'VIXCLS')
TB = fred('data/dgs3mo_full.csv', 'DGS3MO')
SPY = load_px('data/spy_long_history.csv')
QQQ_OHLC = {}
for r in csv.DictReader(open('data/qqq_ohlc.csv')):
    try: QQQ_OHLC[r['d']] = (float(r['h']), float(r['l']), float(r['c']))
    except ValueError: pass

def on_cal(series, dates, lag=0):
    """value known at the close of each session: last observation dated <= dates[i-lag]."""
    sk = sorted(series); out = [None] * len(dates); j = 0; last = None
    vals = []
    for d in dates:
        while j < len(sk) and sk[j] <= d:
            last = series[sk[j]]; j += 1
        vals.append(last)
    for i in range(len(dates)):
        out[i] = vals[i - lag] if i - lag >= 0 else None
    return out

def sma_series(v, n):
    out = [None] * len(v); s = 0.0
    for i, x in enumerate(v):
        s += x
        if i >= n: s -= v[i - n]
        if i >= n - 1: out[i] = s / n
    return out
def ema_series(v, n):
    out = [None] * len(v); a = 2.0 / (n + 1); e = None
    for i, x in enumerate(v):
        if i == n - 1: e = sum(v[:n]) / n
        elif i >= n: e = a * x + (1 - a) * e
        out[i] = e
    return out
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
def rsi_series(v, n=14):
    out = [None] * len(v); ag = al = None
    for i in range(1, len(v)):
        ch = v[i] - v[i - 1]; g = max(ch, 0.0); l = max(-ch, 0.0)
        if i < n: continue
        if i == n:
            gs = [max(v[k] - v[k - 1], 0.0) for k in range(1, n + 1)]
            ls = [max(v[k - 1] - v[k], 0.0) for k in range(1, n + 1)]
            ag, al = sum(gs) / n, sum(ls) / n
        else:
            ag = (ag * (n - 1) + g) / n; al = (al * (n - 1) + l) / n
        out[i] = 100.0 if al == 0 else 100.0 - 100.0 / (1 + ag / al)
    return out
def rvol(rets, i, n):
    r = [x for x in rets[max(0, i - n + 1):i + 1] if x is not None]
    return _vol(r) if len(r) == n else None

def build_signals(dates, close, hl=None, spy=None, vix=None, tb=None, states=None, fast=None):
    """dict name -> list aligned to dates. Every value uses only data at or before that session's close
    (T-bill lagged one session: FRED publishes the next morning)."""
    v = close; n = len(v)
    rets = [None] + [v[i] / v[i - 1] - 1 for i in range(1, n)]
    S = {}
    SM = {k: sma_series(v, k) for k in (10, 20, 30, 50, 100, 150, 200)}
    EM = {k: ema_series(v, k) for k in (20, 50)}
    for k in SM: S[f'gap{k}'] = [None if m is None else v[i] / m - 1 for i, m in enumerate(SM[k])]
    for k in EM: S[f'egap{k}'] = [None if m is None else v[i] / m - 1 for i, m in enumerate(EM[k])]
    for k in (20, 50, 100, 200):
        for h in (5, 10, 20):
            S[f'slope{k}_{h}'] = [None if (i < h or SM[k][i] is None or SM[k][i - h] is None) else SM[k][i] / SM[k][i - h] - 1
                                  for i in range(n)]
    for a, b in ((20, 50), (20, 100), (50, 100)):
        S[f'x{a}_{b}'] = [None if (SM[a][i] is None or SM[b][i] is None) else SM[a][i] / SM[b][i] - 1 for i in range(n)]
    S['ex20_50'] = [None if (EM[20][i] is None or EM[50][i] is None) else EM[20][i] / EM[50][i] - 1 for i in range(n)]
    px = dict(zip(dates, v))
    if fast is None: fast = compute_states(dates, px, short_n=FAST_SHORT_N, long_n=FAST_LONG_N)
    S['fastCDEF'] = [1.0 if f in 'CDEF' else 0.0 for f in fast]
    S['fastEF'] = [1.0 if f in 'EF' else 0.0 for f in fast]
    S['fast'] = fast
    st = states if states is not None else compute_states(dates, px)
    age = [0] * n
    for i in range(1, n):
        age[i] = age[i - 1] + 1 if st[i] == st[i - 1] else 0
    S['age'] = [float(a) for a in age]
    S['state'] = st
    v10 = [rvol(rets, i, 10) for i in range(n)]; v30 = [rvol(rets, i, 30) for i in range(n)]
    S['vol10'] = v10; S['vol30'] = v30
    S['volratio'] = [None if (a is None or not b) else a / b for a, b in zip(v10, v30)]
    S['vol30pct'] = trailing_pct(v30); S['vol10pct'] = trailing_pct(v10)
    S['dd252'] = [None if i < 251 else v[i] / max(v[i - 251:i + 1]) - 1 for i in range(n)]
    S['rsi14'] = rsi_series(v, 14)
    cd = [0] * n
    for i in range(1, n): cd[i] = cd[i - 1] + 1 if v[i] < v[i - 1] else 0
    S['consec_down'] = [float(x) for x in cd]
    S['mom20'] = [None if i < 20 else v[i] / v[i - 20] - 1 for i in range(n)]
    S['mom60'] = [None if i < 60 else v[i] / v[i - 60] - 1 for i in range(n)]
    if hl is not None:
        tr = [None] * n
        for i in range(1, n):
            if dates[i] not in hl: continue
            h, l = hl[dates[i]][0], hl[dates[i]][1]
            pc = v[i - 1]; tr[i] = max(h - l, abs(h - pc), abs(l - pc)) / pc
        def mean_tr(i, k):
            x = [t for t in tr[max(0, i - k + 1):i + 1] if t is not None]
            return sum(x) / len(x) if len(x) >= k * 0.8 else None
        S['range_exp'] = [None if (i < 60) else ((mean_tr(i, 5) / mean_tr(i, 60)) if (mean_tr(i, 5) and mean_tr(i, 60)) else None)
                          for i in range(n)]
    if spy is not None:
        sp = on_cal(spy, dates)
        lr = [None if (sp[i] is None) else math.log(v[i] / sp[i]) for i in range(n)]
        S['rs_spy20'] = [None if (i < 20 or lr[i] is None or lr[i - 20] is None) else lr[i] - lr[i - 20] for i in range(n)]
    if vix is not None:
        vx = on_cal(vix, dates)
        S['vix'] = vx; S['vixpct'] = trailing_pct(vx)
        S['vix_chg5'] = [None if (i < 5 or vx[i] is None or vx[i - 5] is None) else vx[i] - vx[i - 5] for i in range(n)]
    if tb is not None:
        t = on_cal(tb, dates, lag=1)
        S['tb_chg20'] = [None if (i < 20 or t[i] is None or t[i - 20] is None) else t[i] - t[i - 20] for i in range(n)]
        S['tb_chg60'] = [None if (i < 60 or t[i] is None or t[i - 60] is None) else t[i] - t[i - 60] for i in range(n)]
    return S

# ---------------------------------------------------------------- rule inventory (a priori; each is a binary flag)
# (name, family, series, op, thr, step-for-sensitivity, description). op in '<', '>', '<=', '>='.
RULES = [
    # --- DMA: price vs additional lines
    ('px<sma10',   'DMA-line', 'gap10',  '<', 0.0,  None, 'close below 10d SMA'),
    ('px<sma20',   'DMA-line', 'gap20',  '<', 0.0,  None, 'close below 20d SMA'),
    ('px<sma30',   'DMA-line', 'gap30',  '<', 0.0,  None, 'close below 30d SMA'),
    ('px<sma100',  'DMA-line', 'gap100', '<', 0.0,  None, 'close below 100d SMA'),
    ('px<sma150',  'DMA-line', 'gap150', '<', 0.0,  None, 'close below 150d SMA'),
    ('gap20<-2%',  'DMA-gap',  'gap20',  '<', -0.02, 0.01, 'close more than 2% below 20d'),
    ('gap20<-4%',  'DMA-gap',  'gap20',  '<', -0.04, 0.01, 'close more than 4% below 20d'),
    ('gap100<2%',  'DMA-gap',  'gap100', '<', 0.02,  0.01, 'close within 2% of (or below) 100d'),
    ('gap50<-2%',  'DMA-depth', 'gap50', '<', -0.02, 0.01, 'depth: >2% below 50d'),
    ('gap50<-4%',  'DMA-depth', 'gap50', '<', -0.04, 0.01, 'depth: >4% below 50d'),
    ('gap50<-6%',  'DMA-depth', 'gap50', '<', -0.06, 0.01, 'depth: >6% below 50d'),
    ('gap200<2%',  'DMA-depth', 'gap200', '<', 0.02, 0.01, 'within 2% above 200d (overlaps P3)'),
    ('gap200<5%',  'DMA-depth', 'gap200', '<', 0.05, 0.01, 'within 5% above 200d (overlaps P3)'),
    ('gap200>10%', 'DMA-depth', 'gap200', '>', 0.10, 0.02, 'more than 10% above 200d'),
    # --- DMA: slopes (falling = flag)
    *[(f'slope{k}_{h}<0', 'DMA-slope', f'slope{k}_{h}', '<', 0.0, None, f'{k}d SMA lower than {h} sessions ago')
      for k in (20, 50, 100, 200) for h in (5, 10, 20)],
    # --- DMA: crossovers inside D
    ('sma20<sma50',  'DMA-cross', 'x20_50',  '<', 0.0, None, '20d SMA below 50d'),
    ('sma20<sma100', 'DMA-cross', 'x20_100', '<', 0.0, None, '20d SMA below 100d'),
    ('sma50<sma100', 'DMA-cross', 'x50_100', '<', 0.0, None, '50d SMA below 100d'),
    # --- fast 20/100 six-state read
    ('fast_CDEF', 'DMA-fast', 'fastCDEF', '>', 0.5, None, 'fast 20/100 reads C/D/E/F (not A/B)'),
    ('fast_EF',   'DMA-fast', 'fastEF',   '>', 0.5, None, 'fast 20/100 reads E/F (below its 100d)'),
    # --- EMA variants
    ('px<ema20',    'DMA-ema', 'egap20',  '<', 0.0, None, 'close below 20d EMA'),
    ('px<ema50',    'DMA-ema', 'egap50',  '<', 0.0, None, 'close below 50d EMA'),
    ('ema20<ema50', 'DMA-ema', 'ex20_50', '<', 0.0, None, '20d EMA below 50d EMA'),
    # --- episode age
    ('age>5',  'DMA-age', 'age', '>', 5,  5, 'more than 5 sessions into the D episode'),
    ('age>10', 'DMA-age', 'age', '>', 10, 5, 'more than 10 sessions into the D episode'),
    ('age>20', 'DMA-age', 'age', '>', 20, 5, 'more than 20 sessions into the D episode'),
    # --- non-DMA: realised vol regime
    ('volratio>1.0', 'vol', 'volratio', '>', 1.0, 0.15, '10d vol above 30d vol'),
    ('volratio>1.3', 'vol', 'volratio', '>', 1.3, 0.15, '10d vol 30% above 30d vol'),
    ('vol30pct>0.8', 'vol', 'vol30pct', '>', 0.8, 0.1,  '30d vol in trailing-252 top quintile'),
    ('vol30>25%',    'vol', 'vol30',    '>', 0.25, 0.05, '30d realised vol above 25%'),
    # --- drawdown from 252d high
    ('dd252<-5%',  'drawdown', 'dd252', '<', -0.05, 0.025, 'more than 5% off the 252d high'),
    ('dd252<-10%', 'drawdown', 'dd252', '<', -0.10, 0.025, 'more than 10% off the 252d high'),
    # --- RSI
    ('rsi<30', 'rsi', 'rsi14', '<', 30, 5, 'RSI(14) below 30'),
    ('rsi<40', 'rsi', 'rsi14', '<', 40, 5, 'RSI(14) below 40'),
    ('rsi<50', 'rsi', 'rsi14', '<', 50, 5, 'RSI(14) below 50'),
    # --- consecutive down days
    ('down>=3', 'streak', 'consec_down', '>=', 3, 1, '3+ consecutive down closes'),
    ('down>=5', 'streak', 'consec_down', '>=', 5, 1, '5+ consecutive down closes'),
    # --- momentum
    ('mom20<0',   'momentum', 'mom20', '<', 0.0,   0.025, '20d return negative'),
    ('mom20<-5%', 'momentum', 'mom20', '<', -0.05, 0.025, '20d return below -5%'),
    ('mom60<0',   'momentum', 'mom60', '<', 0.0,   0.025, '60d return negative'),
    # --- range expansion (true range 5d / 60d)
    ('range>1.3', 'range', 'range_exp', '>', 1.3, 0.15, '5d true range 30% above its 60d mean'),
    ('range>1.6', 'range', 'range_exp', '>', 1.6, 0.15, '5d true range 60% above its 60d mean'),
    # --- QQQ vs SPY relative strength
    ('rs_spy20<0',   'relstr', 'rs_spy20', '<', 0.0,   0.01, 'QQQ lagged SPY over 20 sessions'),
    ('rs_spy20<-2%', 'relstr', 'rs_spy20', '<', -0.02, 0.01, 'QQQ lagged SPY by >2% over 20 sessions'),
    # --- rates (3m T-bill, one-session lag)
    ('tb60>0',     'rates', 'tb_chg60', '>', 0.0,   0.125, '3m T-bill higher than 60 sessions ago'),
    ('tb60<-25bp', 'rates', 'tb_chg60', '<', -0.25, 0.125, '3m T-bill down >25bp over 60 sessions'),
    # --- VIX
    ('vix>20',     'vix', 'vix',      '>', 20,  5,   'VIX above 20'),
    ('vix>30',     'vix', 'vix',      '>', 30,  5,   'VIX above 30'),
    ('vixpct>0.8', 'vix', 'vixpct',   '>', 0.8, 0.1, 'VIX in trailing-252 top quintile'),
    ('vix5>0',     'vix', 'vix_chg5', '>', 0.0, 2.0, 'VIX up over 5 sessions'),
]
RULE = {r[0]: r for r in RULES}
PAIR_SET = ['px<sma20', 'slope50_10<0', 'sma20<sma50', 'fast_CDEF', 'age>10', 'volratio>1.0', 'dd252<-5%', 'vixpct>0.8']
ACTIONS = {'cash': (0.0, 0.0, 0.0, 0.0, 1.0), 'spmo': (1.0, 0.0, 0.0, 0.0, 0.0),
           'half': (0.0, 0.0, 0.5, 0.0, 0.5), 'xlu': (0.0, 0.0, 0.5, 0.5, 0.0), 'arow': W['A']}
ACTION_DESC = {'cash': 'D -> 100% cash', 'spmo': 'D -> 100% SPMO core', 'half': 'D -> 50% QLD / 50% cash',
               'xlu': 'D -> 50% QLD / 50% XLU', 'arow': 'D -> A row (50/50 SPMO/TQQQ)'}

def flag_of(val, op, thr):
    if val is None: return False
    return {'<': val < thr, '>': val > thr, '<=': val <= thr, '>=': val >= thr}[op]

def rule_flags(S, dates, name, series=None, op=None, thr=None):
    _, _, s, o, t, _, _ = RULE[name]
    s = series or s; o = op or o; t = thr if thr is not None else t
    if s not in S: return None
    return [flag_of(x, o, t) for x in S[s]]

# ---- signal calendar: the QQQ series extended BACKWARD (1998-01 .. 1999-09-14) with the FRED NASDAQ-100 index,
# rescaled to QQQ at the splice, purely so the 252-session lookbacks (dd252, vol/VIX percentiles) exist by 2000-07.
# Macro states and episode age are taken from the QQQ-only classifier (the one the proxy rows use), never from the
# spliced series, so the rows' state sequence is untouched (asserted below).
NDX_FRED = {}
for r_ in csv.DictReader(open('data/nasdaq100_fred.csv')):
    try: NDX_FRED[r_['d']] = float(r_['c'])
    except ValueError: pass
def extend_back(px, first_from='1998-01-01'):
    ds_ = sorted(px); d0 = ds_[0]
    k = px[d0] / NDX_FRED[d0] if d0 in NDX_FRED else None
    pre = [d for d in sorted(NDX_FRED) if first_from <= d < d0] if k else []
    dates = pre + ds_
    close = [NDX_FRED[d] * k for d in pre] + [px[d] for d in ds_]
    st_q = dict(zip(ds_, compute_states(ds_, px)))
    fs_q = dict(zip(ds_, compute_states(ds_, px, short_n=FAST_SHORT_N, long_n=FAST_LONG_N)))
    states = [st_q.get(d, 'F') for d in dates]; fast = [fs_q.get(d, 'F') for d in dates]
    return dates, close, states, fast
_QD_EXT, _QC_EXT, _QS_EXT, _QF_EXT = extend_back(_QQQ_FULL)
SIG_Q = build_signals(_QD_EXT, _QC_EXT, hl=QQQ_OHLC, spy=SPY, vix=VIX, tb=TB, states=_QS_EXT, fast=_QF_EXT)
QIX = {d: i for i, d in enumerate(_QD_EXT)}
# sanity: the proxy rows' macro state equals the one computed on the full calendar
assert all(SIG_Q['state'][QIX[r['d']]] == r['state'] for r in rows), 'state mismatch between proxy rows and signal calendar'
FLAGS = {}     # rule name -> list over D_ROWS of bool
for name in RULE:
    fl = rule_flags(SIG_Q, _QD_FULL, name)
    FLAGS[name] = [fl[QIX[rows[i]['d']]] for i in D_ROWS]
missing = [n for n in RULE if sum(1 for i in D_ROWS if SIG_Q[RULE[n][2]][QIX[rows[i]['d']]] is None)]
assert not missing, f'rules with missing values on D days: {missing}'

# ---------------------------------------------------------------- candidates
# singles: rule x side (flag / complement) x action ; pairs: (a AND b), (a OR b) x action on the flagged side
def combo_flags(spec):
    """spec: ('single', name) | ('and', a, b) | ('or', a, b) -> list over D_ROWS."""
    if spec[0] == 'single': return FLAGS[spec[1]]
    a, b = FLAGS[spec[1]], FLAGS[spec[2]]
    return [x and y for x, y in zip(a, b)] if spec[0] == 'and' else [x or y for x, y in zip(a, b)]
CANDS = []
for name in RULE:
    for side in ('flag', 'comp'):
        for act in ACTIONS:
            CANDS.append(dict(spec=('single', name), side=side, act=act))
for i in range(len(PAIR_SET)):
    for j in range(i + 1, len(PAIR_SET)):
        for kind in ('and', 'or'):
            for act in ACTIONS:
                CANDS.append(dict(spec=(kind, PAIR_SET[i], PAIR_SET[j]), side='flag', act=act))
if os.environ.get('DSF_SMOKE'):
    CANDS = CANDS[:int(os.environ['DSF_SMOKE'])]
N_CAND = len(CANDS)
def cand_label(c):
    s = c['spec']
    core = s[1] if s[0] == 'single' else f"({s[1]} {s[0].upper()} {s[2]})"
    return f"{'NOT ' if c['side'] == 'comp' else ''}{core} -> {c['act']}"

def cand_fn(flags_over_D, side, act):
    """weight function: live everywhere; on D days where the (possibly complemented) flag is on, the action row."""
    on = set()
    for j, i in enumerate(D_ROWS):
        f = flags_over_D[j]
        if (f if side == 'flag' else not f): on.add(rows[i]['d'])
    row = ACTIONS[act]
    def fn(r):
        if r['d'] in on:
            return vt(row, r['vol'])
        return BASE[r['d']]
    return fn, on

def evaluate_full(fn):
    ser, exp, reb = run_count(rows, fn)
    c, s, m = annual_stats(ser)
    cs, ss, ms = annual_stats(run(ERA_S, fn)[0])
    ch, hs, mh = annual_stats(run(ERA_H, fn)[0])
    return dict(cagr=c, sharpe=s, mdd=m, risky=exp, reb=reb, s_sharpe=ss, h_sharpe=hs,
                s_cagr=cs, s_mdd=ms, h_cagr=ch, h_mdd=mh), ser
ERA_S, ERA_H = era(rows, *SEARCH), era(rows, *HOLDOUT)
BASE_EV, _ = evaluate_full(live_fn)
assert abs(BASE_EV['s_sharpe'] - ev0['s_sharpe']) < 1e-9 and abs(BASE_EV['h_sharpe'] - ev0['h_sharpe']) < 1e-9
S_LIVE_EV = dict(cagr=BASE_EV['s_cagr'], sharpe=BASE_EV['s_sharpe'], mdd=BASE_EV['s_mdd'])
H_LIVE_EV = dict(cagr=BASE_EV['h_cagr'], sharpe=BASE_EV['h_sharpe'], mdd=BASE_EV['h_mdd'])

# ---------------------------------------------------------------- exposure / beta controls
def exposure_control(target_exp):
    """live design scaled so its average deployed capital equals target_exp (bisection; bracket expands)."""
    lo, hi = 0.0, 1.0
    while run(rows, scaled(live_fn, hi))[1] < target_exp and hi < 8: lo, hi = hi, hi * 2
    for _ in range(40):
        mid = (lo + hi) / 2
        if run(rows, scaled(live_fn, mid))[1] < target_exp: lo = mid
        else: hi = mid
    k = (lo + hi) / 2
    ev, ser = evaluate_full(scaled(live_fn, k))
    return k, ev, ser
def beta_control(target_beta):
    lo, hi = 0.0, 1.0
    while beta_of(rows, scaled(live_fn, hi)) < target_beta and hi < 8: lo, hi = hi, hi * 2
    for _ in range(40):
        mid = (lo + hi) / 2
        if beta_of(rows, scaled(live_fn, mid)) < target_beta: lo = mid
        else: hi = mid
    k = (lo + hi) / 2
    ev, ser = evaluate_full(scaled(live_fn, k))
    return k, ev, ser

# ---------------------------------------------------------------- real DAILY harness (mirror of monthly_returns.simulate)
def real_build():
    px, qqq, common = MR.build()
    days = [d for d in common if d >= '2015-11-02']
    qd, qc, qs, qf = extend_back(qqq)
    S = build_signals(qd, qc, hl=QQQ_OHLC, spy=SPY, vix=VIX, tb=TB, states=qs, fast=qf)
    return px, qqq, days, qd, S
def simulate_real(px, qqq, days, override=None, band=REBALANCE_DRIFT_BAND):
    """EXACT mirror of monthly_returns.simulate (plain 30d estimator, needs_rebalance band, 4bp), plus
    (a) override(d0) -> action row or None, applied before the vol target on D days, (b) exposure and
    rebalance counting. Verified against MR.simulate(px, qqq, days) with override=None at import."""
    qd = sorted(qqq)
    states = dict(zip(qd, compute_states(qd, qqq)))
    from state import compute_micro_agreement
    micro = compute_micro_agreement(qd, qqq)
    fast = compute_fast_states(qd, qqq); gaps = compute_extension_gaps(qd, qqq)
    held = prev = None; out = []; risky = 0.0; nreb = 0
    for i in range(1, len(days)):
        d0, d1 = days[i - 1], days[i]
        st, ag = states[d0], micro[d0]
        vol = realized_vol_live(qd, qqq, as_of=d0)
        row = override(d0) if (override is not None and st == 'D') else None
        if row is None:
            t = target_weights_with_voltarget(st, ag, vol, fast_state=fast[d0], gaps=gaps[d0])
        else:
            t = RF.vt(row, vol)
        eff = effective_state(st, fast[d0])
        stk = (eff, extension_votes(eff, gaps[d0]), row is not None)
        cost = 0.0
        if held is None:
            held = list(t); nreb += 1
        else:
            do, drift, _ = needs_rebalance(t, held, stk != prev)
            if do:
                cost = MR.ONE_WAY * drift; held = list(t); nreb += 1
        r = [px[s][d1] / px[s][d0] - 1 for s in MR.LEGS]
        g = sum(held[j] * r[j] for j in range(5))
        risky += sum(held[:4])
        out.append((d1, stk[0], g - cost))
        dn = 1 + g
        if dn > 0: held = [held[j] * (1 + r[j]) / dn for j in range(5)]
        prev = stk
    n = len(out)
    return out, risky / n, nreb / (n / 252.0)
def real_metrics(out):
    ser = [x[2] for x in out]
    c, s, m = annual_stats(ser)
    return dict(cagr=c, sharpe=s, mdd=m), ser

RPX, RQQQ, RDAYS, RQD, SIG_R = real_build()
_ref = MR.simulate(RPX, RQQQ, RDAYS, d_gate=False)   # baseline pinned to the pre-2026-09-19 design (no D gate)
_mine, REAL_EXP, REAL_REB = simulate_real(RPX, RQQQ, RDAYS)
assert len(_ref) == len(_mine) and all(a[0] == b[0] and abs(a[2] - b[2]) < 1e-12 for a, b in zip(_ref, _mine)), \
    'simulate_real does not reproduce monthly_returns.simulate'
REAL_EV, REAL_SER = real_metrics(_mine)
RIX = {d: i for i, d in enumerate(RQD)}
log(f"  real DAILY harness (SPMO/TQQQ/QLD/XLU/BOXX-synthetic, {RDAYS[0]}..{RDAYS[-1]}, {len(RDAYS)-1} sessions): "
    f"{REAL_EV['cagr']*100:.2f}% / {REAL_EV['sharpe']:.3f} / {REAL_EV['mdd']*100:.1f}%  exposure {REAL_EXP*100:.1f}%  "
    f"{REAL_REB:.1f} rebalances/yr  (mirror verified against monthly_returns.simulate)")
n_rd = sum(1 for d in RDAYS[:-1] if SIG_R['state'][RIX[d]] == 'D')
log(f"  real daily D days: {n_rd}")

def real_override(spec, side, act):
    row = ACTIONS[act]
    def fl(name, d):
        _, _, s, o, t, _, _ = RULE[name]
        return flag_of(SIG_R[s][RIX[d]], o, t)
    def ov(d0):
        if spec[0] == 'single': f = fl(spec[1], d0)
        elif spec[0] == 'and': f = fl(spec[1], d0) and fl(spec[2], d0)
        else: f = fl(spec[1], d0) or fl(spec[2], d0)
        on = f if side == 'flag' else not f
        return row if on else None
    return ov

def real_weekly_fn(spec, side, act):
    """the same rule on the real WEEKLY rows (RF.eval_real): signal at the week's decision date d0."""
    row = ACTIONS[act]
    def fl(name, d):
        _, _, s, o, t, _, _ = RULE[name]
        return flag_of(SIG_Q[s][QIX[d]], o, t)
    def fn(r):
        if r['state'] != 'D': return live_rr(r)
        d0 = r['d0']
        if spec[0] == 'single': f = fl(spec[1], d0)
        elif spec[0] == 'and': f = fl(spec[1], d0) and fl(spec[2], d0)
        else: f = fl(spec[1], d0) or fl(spec[2], d0)
        return RF.vt(row, r['vol']) if (f if side == 'flag' else not f) else live_rr(r)
    return fn

# ---------------------------------------------------------------- next-day-return profile helpers
def tstat(a, b):
    if len(a) < 2 or len(b) < 2: return float('nan')
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    va = sum((x - ma) ** 2 for x in a) / (len(a) - 1); vb = sum((x - mb) ** 2 for x in b) / (len(b) - 1)
    se = math.sqrt(va / len(a) + vb / len(b))
    return (ma - mb) / se if se > 0 else float('nan')
def profile(flags_over_D, leg=2, lo='0000', hi='9999'):
    """next-day return of leg (2 = QLD proxy) on D days, flagged vs unflagged, restricted to d in [lo, hi]."""
    a = [rows[i]['legs'][leg] for j, i in enumerate(D_ROWS) if flags_over_D[j] and lo <= rows[i]['d'] <= hi]
    b = [rows[i]['legs'][leg] for j, i in enumerate(D_ROWS) if not flags_over_D[j] and lo <= rows[i]['d'] <= hi]
    ma = sum(a) / len(a) if a else float('nan'); mb = sum(b) / len(b) if b else float('nan')
    return len(a), ma, len(b), mb, tstat(a, b)

JS_GRID = os.path.join(SCRATCH, 'dsf_grid.json')
JS_PERM = os.path.join(SCRATCH, 'dsf_perm.json')

# ================================================================= STAGE: grid
if STAGE in ('all', 'grid'):
    log(f"\n{'='*110}\nSTAGE grid: {N_CAND} candidates = {len(RULE)} rules x 2 sides x {len(ACTIONS)} actions "
        f"+ {len(PAIR_SET)}C2 pairs x AND/OR x {len(ACTIONS)} actions\n{'='*110}")
    log("\n--- screening table: next-day QLD-leg return on D days, flagged vs unflagged (bp/day, t of difference) ---")
    log(f"{'rule':<16}{'family':<11}{'nF':>5}{'flag':>8}{'unfl':>8}{'t':>6} | {'S nF':>5}{'flag':>8}{'unfl':>8}{'t':>6} | {'H nF':>5}{'flag':>8}{'unfl':>8}{'t':>6}")
    PROF = {}
    for name in RULE:
        fa = profile(FLAGS[name]); fs = profile(FLAGS[name], lo=SEARCH[0]); fh = profile(FLAGS[name], hi=HOLDOUT[1])
        PROF[name] = dict(full=fa, search=fs, holdout=fh)
        log(f"{name:<16}{RULE[name][1]:<11}{fa[0]:>5}{fa[1]*1e4:>8.0f}{fa[3]*1e4:>8.0f}{fa[4]:>6.1f} | "
            f"{fs[0]:>5}{fs[1]*1e4:>8.0f}{fs[3]*1e4:>8.0f}{fs[4]:>6.1f} | {fh[0]:>5}{fh[1]*1e4:>8.0f}{fh[3]*1e4:>8.0f}{fh[4]:>6.1f}")

    log(f"\n--- grid: every candidate through the harness (proxy full / search / holdout; real daily; real weekly) ---")
    log(f"LIVE: proxy {BASE_EV['cagr']*100:.2f}% / {BASE_EV['sharpe']:.3f} / {BASE_EV['mdd']*100:.1f}%  exp {BASE_EV['risky']*100:.1f}%  "
        f"reb {BASE_EV['reb']:.1f}/yr  S {BASE_EV['s_sharpe']:.3f} H {BASE_EV['h_sharpe']:.3f} | real daily {REAL_EV['cagr']*100:.2f}% / "
        f"{REAL_EV['sharpe']:.3f} / {REAL_EV['mdd']*100:.1f}% | real weekly {er0['cagr']*100:.2f}% / {er0['sharpe']:.3f} / {er0['mdd']*100:.1f}%")
    hdr = (f"{'#':>4} {'candidate':<44}{'nOn':>5}{'CAGR':>7}{'Sharpe':>7}{'MaxDD':>7}{'exp':>6}{'reb':>6}"
           f"{'dS_S':>8}{'dS_H':>8}{'dS_F':>8} | {'rdCAGR':>7}{'rdSh':>7}{'rdDD':>7}{'rdExp':>6} | {'rwSh':>6}")
    log(hdr)
    RES = []
    for n_, c in enumerate(CANDS):
        fl = combo_flags(c['spec'])
        fn, on = cand_fn(fl, c['side'], c['act'])
        ev, ser = evaluate_full(fn)
        # real daily
        rout, rexp, rreb = simulate_real(RPX, RQQQ, RDAYS, real_override(c['spec'], c['side'], c['act']))
        rev, _ = real_metrics(rout)
        rw = RF.eval_real(rr, real_weekly_fn(c['spec'], c['side'], c['act']))
        rec = dict(idx=n_, label=cand_label(c), spec=list(c['spec']), side=c['side'], act=c['act'], n_on=len(on),
                   n_on_search=sum(1 for d in on if d >= SEARCH[0]), n_on_holdout=sum(1 for d in on if d < SEARCH[0]),
                   ev=ev, dS_S=ev['s_sharpe'] - BASE_EV['s_sharpe'], dS_H=ev['h_sharpe'] - BASE_EV['h_sharpe'],
                   dS_F=ev['sharpe'] - BASE_EV['sharpe'],
                   real=dict(cagr=rev['cagr'], sharpe=rev['sharpe'], mdd=rev['mdd'], exp=rexp, reb=rreb),
                   realw=rw)
        RES.append(rec)
        log(f"{n_:>4} {rec['label']:<44}{len(on):>5}{ev['cagr']*100:>6.2f}%{ev['sharpe']:>7.3f}{ev['mdd']*100:>6.1f}%{ev['risky']*100:>5.1f}%"
            f"{ev['reb']:>6.1f}{rec['dS_S']:>+8.3f}{rec['dS_H']:>+8.3f}{rec['dS_F']:>+8.3f} | {rev['cagr']*100:>6.2f}%{rev['sharpe']:>7.3f}"
            f"{rev['mdd']*100:>6.1f}%{rexp*100:>5.0f}% | {rw['sharpe']:>6.3f}")
    json.dump(dict(base=BASE_EV, real_base=dict(REAL_EV, exp=REAL_EXP, reb=REAL_REB), realw_base=er0, res=RES, prof=PROF,
                   n_cand=N_CAND, n_rules=len(RULE)), open(JS_GRID, 'w'))
    log(f"\n[grid saved: {JS_GRID}]  elapsed {time.time()-T0:.0f}s")

# ================================================================= STAGE: permutation
def _perm_worker(args):
    """one permutation: common circular shift s of every rule's flag sequence within the D-day sequence;
    returns (max over candidates of dS_full, max of min(dS_S, dS_H) [sliced], per-action maxima)."""
    s, = args
    shifted = {name: [FLAGS[name][(j + s) % nD] for j in range(nD)] for name in RULE}
    best_full = -9.0; best_both = -9.0; best_act = {a: -9.0 for a in ACTIONS}
    for c in CANDS:
        sp = c['spec']
        if sp[0] == 'single': fl = shifted[sp[1]]
        else:
            a, b = shifted[sp[1]], shifted[sp[2]]
            fl = [x and y for x, y in zip(a, b)] if sp[0] == 'and' else [x or y for x, y in zip(a, b)]
        fn, _ = cand_fn(fl, c['side'], c['act'])
        ser, _ = run(rows, fn)
        dF = bstats(ser)[1] - LIVE_F_SH
        dS = sliced_sharpe(ser, *SEARCH) - LIVE_S_SL; dH = sliced_sharpe(ser, *HOLDOUT) - LIVE_H_SL
        best_full = max(best_full, dF); best_both = max(best_both, min(dS, dH))
        best_act[c['act']] = max(best_act[c['act']], dF)
    return best_full, best_both, best_act
LIVE_F_SH = bstats(LIVE_SER)[1]
LIVE_S_SL = sliced_sharpe(LIVE_SER, *SEARCH); LIVE_H_SL = sliced_sharpe(LIVE_SER, *HOLDOUT)

if STAGE in ('all', 'perm'):
    G = json.load(open(JS_GRID))
    RES = G['res']
    log(f"\n{'='*110}\nSTAGE perm: max-statistic permutation over the whole grid ({N_CAND} candidates), {N_PERM} circular shifts "
        f"of the D-day flag sequences (common shift per draw, so the dependence between candidates is preserved)\n{'='*110}")
    rng = random.Random(SEED)
    shifts = [rng.randrange(1, nD) for _ in range(N_PERM)]
    from multiprocessing import Pool
    t1 = time.time()
    with Pool(N_PROCS) as pool:
        outs = pool.map(_perm_worker, [(s,) for s in shifts], chunksize=1)
    log(f"  {N_PERM} permutations in {time.time()-t1:.0f}s")
    mf = sorted(o[0] for o in outs); mb = sorted(o[1] for o in outs)
    ma = {a: sorted(o[2][a] for o in outs) for a in ACTIONS}
    # real candidates on the SAME statistics (sliced eras for the both-era stat)
    real_stats = []
    for rec in RES:
        c = dict(spec=tuple(rec['spec']), side=rec['side'], act=rec['act'])
        fn, _ = cand_fn(combo_flags(c['spec']), c['side'], c['act'])
        ser, _ = run(rows, fn)
        dF = bstats(ser)[1] - LIVE_F_SH
        both = min(sliced_sharpe(ser, *SEARCH) - LIVE_S_SL, sliced_sharpe(ser, *HOLDOUT) - LIVE_H_SL)
        real_stats.append((dF, both))
    bestF = max(range(N_CAND), key=lambda k: real_stats[k][0]); bestB = max(range(N_CAND), key=lambda k: real_stats[k][1])
    pF = sum(1 for x in mf if x >= real_stats[bestF][0]) / N_PERM
    pB = sum(1 for x in mb if x >= real_stats[bestB][1]) / N_PERM
    q = lambda v, p: v[min(len(v) - 1, int(len(v) * p))]
    log(f"\n  null best-of-{N_CAND} FULL-period Sharpe gain: median {q(mf, 0.5):+.3f}  95th {q(mf, 0.95):+.3f}  max {mf[-1]:+.3f}")
    log(f"  best REAL candidate on that statistic: #{bestF} {RES[bestF]['label']}  dS_full {real_stats[bestF][0]:+.3f}  -> p = {pF:.3f}")
    log(f"  null best-of-{N_CAND} BOTH-ERA gain min(dS_S, dS_H): median {q(mb, 0.5):+.3f}  95th {q(mb, 0.95):+.3f}  max {mb[-1]:+.3f}")
    log(f"  best REAL candidate on that statistic: #{bestB} {RES[bestB]['label']}  min(dS_S,dS_H) {real_stats[bestB][1]:+.3f}  -> p = {pB:.3f}")
    log(f"  per-action null 95th pct of the full-period gain: " + ", ".join(f"{a} {q(ma[a], 0.95):+.3f}" for a in ACTIONS))
    per_cand_p = [sum(1 for x in mf if x >= rs[0]) / N_PERM for rs in real_stats]
    json.dump(dict(shifts=shifts, null_full=mf, null_both=mb, null_act=ma, real_stats=real_stats, per_cand_p=per_cand_p,
                   bestF=bestF, bestB=bestB, pF=pF, pB=pB), open(JS_PERM, 'w'))
    log(f"[perm saved: {JS_PERM}]  elapsed {time.time()-T0:.0f}s")

# ================================================================= STAGE: diagnostics
def build_spy_rows():
    """SPY-core proxy rows: classifier, fast overlay, gaps, vol AND signals all on SPY; legs = SPY TR core,
    synthetic 3x/2x on SPY, XLU TR, T-bill cash. Same row schema as the QQQ proxy, so run()/evaluate apply."""
    D_ = data(); xlu = load_px('data/xlu_long_history.csv')
    sp = {d: SPY[d] for d in SPY if d in xlu and d >= '1999-09-15'}
    sd = sorted(sp)
    core = total_return_index(sp, 1.8); lev3 = synth_leveraged(sp, 3, TQQQ_ER, D_['rate_on'], div_pa=1.8)
    lev2 = synth_leveraged(sp, 2, QLD_ER, D_['rate_on'], div_pa=1.8)
    xl = total_return_index({d: xlu[d] for d in sd}, XLU_DIV_PA); cash = cash_index(sd, D_['rate_on'])
    st = compute_states(sd, sp); fast = compute_fast_states(sd, sp); gaps = compute_extension_gaps(sd, sp)
    v = [sp[d] for d in sd]; rets = [None] + [v[i] / v[i - 1] - 1 for i in range(1, len(v))]
    out = []
    for i in range(1, len(sd)):
        d0, d1 = sd[i - 1], sd[i]; j = i - 1
        if d0 < START or _sma_at(v, j, 200) is None: continue
        r30 = [x for x in rets[j - 29:j + 1] if x is not None]
        eff = effective_state(st[j], fast[d0])
        out.append(dict(d=d0, state=st[j], agree=False, vol=_vol(r30), eff=eff,
                        gaps={n: (gaps[d0][n] if gaps[d0][n] is not None else 0.0) for n in (100, 150, 200)},
                        legs=(core[d1] / core[d0] - 1, lev3[d1] / lev3[d0] - 1, lev2[d1] / lev2[d0] - 1,
                              xl[d1] / xl[d0] - 1, cash[d1] / cash[d0] - 1)))
    S = build_signals(sd, v, vix=VIX, tb=TB)
    return out, sd, S

if STAGE in ('all', 'diag'):
    G = json.load(open(JS_GRID)); P = json.load(open(JS_PERM))
    RES = G['res']
    log(f"\n{'='*110}\nSTAGE diag: hurdles, controls and survivor diagnostics\n{'='*110}")
    mf = P['null_full']; N_PERM_ = len(mf)
    # hurdle 1+2: both eras and full
    h12 = [k for k, rec in enumerate(RES) if rec['dS_F'] > 0 and rec['dS_S'] > 0 and rec['dS_H'] > 0]
    log(f"\nHURDLE 1-2 (Sharpe up in full period AND both eras): {len(h12)} of {N_CAND} candidates")
    h12.sort(key=lambda k: -RES[k]['dS_F'])
    log(f"{'#':>4} {'candidate':<44}{'nOn':>5}{'dS_S':>8}{'dS_H':>8}{'dS_F':>8}{'CAGR':>7}{'MaxDD':>7}{'exp':>6}{'rdSh':>7}{'rwSh':>7}{'perm p':>8}")
    for k in h12[:25]:
        rec = RES[k]
        log(f"{k:>4} {rec['label']:<44}{rec['n_on']:>5}{rec['dS_S']:>+8.3f}{rec['dS_H']:>+8.3f}{rec['dS_F']:>+8.3f}{rec['ev']['cagr']*100:>6.2f}%"
            f"{rec['ev']['mdd']*100:>6.1f}%{rec['ev']['risky']*100:>5.1f}%{rec['real']['sharpe']:>7.3f}{rec['realw']['sharpe']:>7.3f}{P['per_cand_p'][k]:>8.3f}")
    # top by upside (CAGR) among both-era passers, and top by real daily Sharpe overall -- reported for completeness
    by_cagr = sorted(range(N_CAND), key=lambda k: -RES[k]['ev']['cagr'])[:8]
    log(f"\nTOP 8 by FULL-period CAGR (any hurdle status) -- the upside view:")
    for k in by_cagr:
        rec = RES[k]
        log(f"{k:>4} {rec['label']:<44}{rec['ev']['cagr']*100:>6.2f}%{rec['ev']['sharpe']:>7.3f}{rec['ev']['mdd']*100:>6.1f}%  "
            f"dS_S {rec['dS_S']:+.3f} dS_H {rec['dS_H']:+.3f}  real daily {rec['real']['cagr']*100:.2f}% / {rec['real']['sharpe']:.3f} / {rec['real']['mdd']*100:.1f}%")
    by_real = sorted(range(N_CAND), key=lambda k: -RES[k]['real']['sharpe'])[:8]
    log(f"\nTOP 8 by REAL DAILY Sharpe (2015-11..2026-09, search era only, no holdout exists for real instruments):")
    for k in by_real:
        rec = RES[k]
        log(f"{k:>4} {rec['label']:<44} real {rec['real']['cagr']*100:.2f}% / {rec['real']['sharpe']:.3f} / {rec['real']['mdd']*100:.1f}%  "
            f"proxy dS_S {rec['dS_S']:+.3f} dS_H {rec['dS_H']:+.3f}")

    # CONSTANT-D controls: the same action on EVERY D day (a flat row change, no split). A split is only credited with
    # what it adds over the better of live and its own flat row.
    log(f"\nCONSTANT-D CONTROLS (action on all {nD} D days -- a row change, not a sub-state):")
    log(f"{'flat row':<30}{'CAGR':>7}{'Sharpe':>7}{'MaxDD':>7}{'exp':>6}{'dS_S':>8}{'dS_H':>8}{'dS_F':>8} | {'rdCAGR':>7}{'rdSh':>7}{'rdDD':>7} | {'rwSh':>6}")
    FLAT = {}
    for act in ACTIONS:
        fnf, _ = cand_fn([True] * nD, 'flag', act); evf, serf = evaluate_full(fnf)
        ro, rexp, rreb = simulate_real(RPX, RQQQ, RDAYS, lambda d0, row=ACTIONS[act]: row); revf, _ = real_metrics(ro)
        rwf = RF.eval_real(rr, lambda r, row=ACTIONS[act]: (RF.vt(row, r['vol']) if r['state'] == 'D' else live_rr(r)))
        FLAT[act] = dict(ev=evf, ser=serf, real=revf, realw=rwf)
        log(f"{ACTION_DESC[act]:<30}{evf['cagr']*100:>6.2f}%{evf['sharpe']:>7.3f}{evf['mdd']*100:>6.1f}%{evf['risky']*100:>5.1f}%"
            f"{evf['s_sharpe']-BASE_EV['s_sharpe']:>+8.3f}{evf['h_sharpe']-BASE_EV['h_sharpe']:>+8.3f}{evf['sharpe']-BASE_EV['sharpe']:>+8.3f} | "
            f"{revf['cagr']*100:>6.2f}%{revf['sharpe']:>7.3f}{revf['mdd']*100:>6.1f}% | {rwf['sharpe']:>6.3f}")
    log("  -> a candidate's SPLIT value below is quoted against max(live, its flat row) in each era ('vs flat')")
    for k in h12[:25]:
        rec = RES[k]; f = FLAT[rec['act']]['ev']
        log(f"    #{k:<4}{rec['label']:<44} vs flat: S {rec['ev']['s_sharpe']-f['s_sharpe']:+.3f}  H {rec['ev']['h_sharpe']-f['h_sharpe']:+.3f}  "
            f"F {rec['ev']['sharpe']-f['sharpe']:+.3f}   real daily Sh {rec['real']['sharpe']-FLAT[rec['act']]['real']['sharpe']:+.3f}")

    # hurdle 3: exposure / beta controls on the hurdle-1-2 passers (top 12 by dS_F) plus the top-3 near-misses by dS_F overall
    near = [k for k in sorted(range(N_CAND), key=lambda k: -RES[k]['dS_F']) if k not in h12][:3]
    cand_ids = h12[:12] + near
    log(f"\nHURDLE 3: exposure-matched and beta-matched controls (full proxy), on {len(h12[:12])} passers + {len(near)} near-misses")
    log(f"{'#':>4} {'candidate':<44}{'cand Sh':>8}{'exp':>6}{'k_exp':>6}{'ctrl Sh':>8}{'beta':>6}{'k_b':>6}{'bctrl':>7}  verdict")
    CTRL = {}
    for k in cand_ids:
        rec = RES[k]; c = dict(spec=tuple(rec['spec']), side=rec['side'], act=rec['act'])
        fn, _ = cand_fn(combo_flags(c['spec']), c['side'], c['act'])
        ke, eve, sere = exposure_control(rec['ev']['risky'])
        cb = beta_of(rows, fn); kb, evb, serb = beta_control(cb)
        okE = rec['ev']['sharpe'] > eve['sharpe']; okB = rec['ev']['sharpe'] > evb['sharpe']
        both_ctrl = (rec['ev']['s_sharpe'] > eve['s_sharpe'] and rec['ev']['h_sharpe'] > eve['h_sharpe'])
        CTRL[k] = dict(k_exp=ke, ctrl=eve, ctrl_ser=sere, k_beta=kb, bctrl=evb, okE=okE, okB=okB, both_ctrl=both_ctrl)
        log(f"{k:>4} {rec['label']:<44}{rec['ev']['sharpe']:>8.3f}{rec['ev']['risky']*100:>5.1f}%{ke:>6.3f}{eve['sharpe']:>8.3f}{cb:>6.2f}{kb:>6.3f}{evb['sharpe']:>7.3f}  "
            f"{'PASS' if okE else 'FAIL'}-exp {'PASS' if okB else 'FAIL'}-beta  vs ctrl S {rec['ev']['s_sharpe']-eve['s_sharpe']:+.3f} H {rec['ev']['h_sharpe']-eve['h_sharpe']:+.3f}"
            f"{'' if k in h12 else '  (near-miss)'}")
    # hurdle 4: permutation
    log(f"\nHURDLE 4: max-statistic permutation (null = best of {N_CAND} under a common circular shift within D days, {N_PERM_} draws)")
    q = lambda v, p: v[min(len(v) - 1, int(len(v) * p))]
    log(f"  null best full-period gain: median {q(mf,0.5):+.3f}, 95th {q(mf,0.95):+.3f}; best real #{P['bestF']} {RES[P['bestF']]['label']} "
        f"{P['real_stats'][P['bestF']][0]:+.3f} p = {P['pF']:.3f}")
    mb = P['null_both']
    log(f"  null best both-era gain: median {q(mb,0.5):+.3f}, 95th {q(mb,0.95):+.3f}; best real #{P['bestB']} {RES[P['bestB']]['label']} "
        f"{P['real_stats'][P['bestB']][1]:+.3f} p = {P['pB']:.3f}")
    survivors = [k for k in h12[:12] if CTRL[k]['okE'] and CTRL[k]['okB'] and P['per_cand_p'][k] < 0.05]
    log(f"\nSURVIVORS of hurdles 1-4: {len(survivors)}  " + (", ".join(f"#{k} {RES[k]['label']}" for k in survivors) if survivors else "(none)"))

    # ---- deep diagnostics on survivors, else on the three most interesting near-misses (best dS_F both-era passer,
    #      best both-era passer that clears the exposure control, best real-daily Sharpe among both-era passers)
    deep = list(survivors)
    if os.environ.get('DSF_DEEP'):                      # force deep diagnostics on named candidate ids
        deep = [int(x) for x in os.environ['DSF_DEEP'].split(',')]
        log(f"\nDSF_DEEP override: deep diagnostics on " + ", ".join(f"#{k} {RES[k]['label']}" for k in deep))
    elif not deep:
        pool_ = h12[:12] or list(range(N_CAND))
        picks = [pool_[0]]
        ce = [k for k in pool_ if CTRL.get(k, {}).get('okE')]
        if ce and ce[0] not in picks: picks.append(ce[0])
        br = max(pool_, key=lambda k: RES[k]['real']['sharpe'])
        if br not in picks: picks.append(br)
        deep = picks
        log(f"\nNo survivor. Deep diagnostics on {len(deep)} near-misses: " + ", ".join(f"#{k} {RES[k]['label']}" for k in deep))
    SP_ROWS, SP_D, SIG_S = build_spy_rows()
    SP_BASE = evaluate(SP_ROWS, live_fn)
    SP_D_IDX = [i for i, r in enumerate(SP_ROWS) if r['state'] == 'D']
    SPIX = {d: i for i, d in enumerate(SP_D)}
    log(f"\nSPY-core proxy (independent series; classifier + signals on SPY): live {SP_BASE['cagr']*100:.2f}% / {SP_BASE['sharpe']:.3f} / "
        f"{SP_BASE['mdd']*100:.1f}%  S {SP_BASE['s_sharpe']:.3f} H {SP_BASE['h_sharpe']:.3f}  ({len(SP_ROWS)} rows, {len(SP_D_IDX)} D days)")
    for k in deep:
        rec = RES[k]; spec = tuple(rec['spec']); side, act = rec['side'], rec['act']
        log(f"\n{'-'*110}\nDEEP #{k}: {rec['label']}   [{ACTION_DESC[act]}]   nOn {rec['n_on']} (S {rec['n_on_search']}, H {rec['n_on_holdout']})")
        log(f"  proxy {rec['ev']['cagr']*100:.2f}% / {rec['ev']['sharpe']:.3f} / {rec['ev']['mdd']*100:.1f}%  exp {rec['ev']['risky']*100:.1f}%  reb {rec['ev']['reb']:.1f}/yr"
            f"  S {rec['ev']['s_sharpe']:.3f} ({rec['dS_S']:+.3f})  H {rec['ev']['h_sharpe']:.3f} ({rec['dS_H']:+.3f}) | "
            f"real daily {rec['real']['cagr']*100:.2f}% / {rec['real']['sharpe']:.3f} / {rec['real']['mdd']*100:.1f}% exp {rec['real']['exp']*100:.0f}% reb {rec['real']['reb']:.0f}/yr"
            f" | real weekly {rec['realw']['cagr']*100:.2f}% / {rec['realw']['sharpe']:.3f} / {rec['realw']['mdd']*100:.1f}% | perm p {P['per_cand_p'][k]:.3f}")
        fn, on = cand_fn(combo_flags(spec), side, act)
        ser, _ = run(rows, fn)
        f_ = FLAT[act]['ev']
        log(f"  vs its FLAT row ({ACTION_DESC[act]} on all D days: {f_['cagr']*100:.2f}% / {f_['sharpe']:.3f} / {f_['mdd']*100:.1f}%, S {f_['s_sharpe']:.3f} H {f_['h_sharpe']:.3f}): "
            f"split adds S {rec['ev']['s_sharpe']-f_['s_sharpe']:+.3f}  H {rec['ev']['h_sharpe']-f_['h_sharpe']:+.3f}  F {rec['ev']['sharpe']-f_['sharpe']:+.3f}; "
            f"real daily {rec['real']['sharpe']-FLAT[act]['real']['sharpe']:+.3f}")
        # (a) threshold sensitivity
        if spec[0] == 'single':
            name = spec[1]; _, fam, s, op, thr, step, _ = RULE[name]
            log("  (a) threshold sensitivity:")
            variants = []
            if step is not None:
                variants = [(f"{s} {op} {thr + m*step:g}", s, op, thr + m * step) for m in (-2, -1, 0, 1, 2)]
            elif s.startswith('gap') or s.startswith('egap'):
                wins = (5, 10, 15, 20, 30, 50, 75, 100, 150, 200); cur = int(''.join(ch for ch in s if ch.isdigit()))
                pre = 'egap' if s.startswith('egap') else 'gap'
                variants = [(f"close vs {pre[1:] if pre=='egap' else 'sma'}{w}", f"{pre}{w}", op, thr) for w in wins if abs(wins.index(w) - wins.index(cur)) <= 2] if cur in wins else []
            elif s.startswith('slope'):
                kk, hh = s[5:].split('_'); kk, hh = int(kk), int(hh)
                variants = [(f"slope{kk}_{h2}<0", f"slope{kk}_{h2}", op, thr) for h2 in (3, 5, 10, 20, 40)] + \
                           [(f"slope{k2}_{hh}<0", f"slope{k2}_{hh}", op, thr) for k2 in (20, 50, 100, 200) if k2 != kk]
            elif s.startswith('x') or s.startswith('ex'):
                variants = [(f"{s} {op} {t2:+.3f}", s, op, t2) for t2 in (-0.02, -0.01, 0.0, 0.01, 0.02)]
                for pre in ('ex', 'x'):
                    for a_, b_ in ((10, 30), (10, 50), (15, 50), (20, 40), (20, 50), (25, 50), (30, 50), (20, 60), (20, 100), (50, 100)):
                        nm = f"{pre}{a_}_{b_}"
                        if nm != s: variants.append((f"{'EMA' if pre=='ex' else 'SMA'}{a_} < {'EMA' if pre=='ex' else 'SMA'}{b_}", nm, op, 0.0))
            for lab, s2, o2, t2 in variants:
                if s2 not in SIG_Q:
                    # extra windows/horizons not pre-built: build on demand
                    v_ = _QC_EXT
                    if s2.startswith('gap'): SIG_Q[s2] = [None if m is None else v_[i] / m - 1 for i, m in enumerate(sma_series(v_, int(s2[3:])))]
                    elif s2.startswith('egap'): SIG_Q[s2] = [None if m is None else v_[i] / m - 1 for i, m in enumerate(ema_series(v_, int(s2[4:])))]
                    elif s2.startswith('ex') or (s2.startswith('x') and '_' in s2):
                        pre = 'ex' if s2.startswith('ex') else 'x'; a_, b_ = map(int, s2[len(pre):].split('_'))
                        mk_ = ema_series if pre == 'ex' else sma_series; A_, B_ = mk_(v_, a_), mk_(v_, b_)
                        SIG_Q[s2] = [None if (A_[i] is None or B_[i] is None) else A_[i] / B_[i] - 1 for i in range(len(v_))]
                    elif s2.startswith('slope'):
                        kk2, hh2 = map(int, s2[5:].split('_')); sm = sma_series(v_, kk2)
                        SIG_Q[s2] = [None if (i < hh2 or sm[i] is None or sm[i - hh2] is None) else sm[i] / sm[i - hh2] - 1 for i in range(len(v_))]
                fl2 = [flag_of(SIG_Q[s2][QIX[rows[i]['d']]], o2, t2) for i in D_ROWS]
                fn2, on2 = cand_fn(fl2, side, act); ev2, _ = evaluate_full(fn2)
                log(f"      {lab:<28} nOn {len(on2):>4}  {ev2['cagr']*100:.2f}% / {ev2['sharpe']:.3f} / {ev2['mdd']*100:.1f}%  "
                    f"dS_S {ev2['s_sharpe']-BASE_EV['s_sharpe']:+.3f} dS_H {ev2['h_sharpe']-BASE_EV['h_sharpe']:+.3f} dS_F {ev2['sharpe']-BASE_EV['sharpe']:+.3f}")
            # (b) bucket profile of the underlying series on D days (quintiles cut on the SEARCH era)
            vals_s = sorted(SIG_Q[s][QIX[rows[i]['d']]] for i in D_ROWS if rows[i]['d'] >= SEARCH[0])
            cuts = [vals_s[int(len(vals_s) * p)] for p in (0.2, 0.4, 0.6, 0.8)]
            log(f"  (b) next-day QLD-leg return by search-era quintile of {s} (cuts {', '.join(f'{c:.4g}' for c in cuts)}); bp/day, t vs the rest:")
            for era_lab, lo, hi in (('full', '0000', '9999'), ('search', SEARCH[0], '9999'), ('holdout', '0000', HOLDOUT[1])):
                parts = []
                for b in range(5):
                    inb = [bisect.bisect_right(cuts, SIG_Q[s][QIX[rows[i]['d']]]) == b for i in D_ROWS]
                    n1, m1, n0, m0, t = profile(inb, lo=lo, hi=hi)
                    parts.append(f"Q{b+1} n{n1:>3} {m1*1e4:>+5.0f}bp t{t:>+4.1f}")
                log(f"      {era_lab:<8} " + " | ".join(parts))
        else:
            log("  (a) pair: sensitivity shown through its components in the grid; (b) profile flagged vs unflagged:")
        for era_lab, lo, hi in (('full', '0000', '9999'), ('search', SEARCH[0], '9999'), ('holdout', '0000', HOLDOUT[1])):
            n1, m1, n0, m0, t = profile(combo_flags(spec), lo=lo, hi=hi)
            log(f"      {era_lab:<8} flagged n{n1:>4} {m1*1e4:>+6.0f} bp/day   unflagged n{n0:>4} {m0*1e4:>+6.0f} bp/day   t {t:+.1f}   "
                f"(QQQ leg: flagged {profile(combo_flags(spec), leg=0, lo=lo, hi=hi)[1]*1e4:+.0f} bp, unflagged {profile(combo_flags(spec), leg=0, lo=lo, hi=hi)[3]*1e4:+.0f} bp)")
        # (c) SPY as an independent series with the same rule
        def sp_flags():
            def fl(name):
                _, _, s_, o_, t_, _, _ = RULE[name]
                if s_ not in SIG_S: return None
                return [flag_of(SIG_S[s_][SPIX[SP_ROWS[i]['d']]], o_, t_) for i in SP_D_IDX]
            if spec[0] == 'single': return fl(spec[1])
            a, b = fl(spec[1]), fl(spec[2])
            if a is None or b is None: return None
            return [x and y for x, y in zip(a, b)] if spec[0] == 'and' else [x or y for x, y in zip(a, b)]
        sfl = sp_flags()
        if sfl is None:
            log("  (c) SPY: signal not computable on SPY (needs QQQ-specific input)")
        else:
            on_s = set(SP_ROWS[i]['d'] for j, i in enumerate(SP_D_IDX) if (sfl[j] if side == 'flag' else not sfl[j]))
            SPB = {r['d']: live_fn(r) for r in SP_ROWS}
            def sfn(r, row=ACTIONS[act]):
                return vt(row, r['vol']) if r['d'] in on_s else SPB[r['d']]
            spe = evaluate(SP_ROWS, sfn)
            a_ = [SP_ROWS[i]['legs'][2] for j, i in enumerate(SP_D_IDX) if sfl[j]]; b_ = [SP_ROWS[i]['legs'][2] for j, i in enumerate(SP_D_IDX) if not sfl[j]]
            log(f"  (c) SPY-core proxy, same rule on SPY: {spe['cagr']*100:.2f}% / {spe['sharpe']:.3f} / {spe['mdd']*100:.1f}%  "
                f"dS_S {spe['s_sharpe']-SP_BASE['s_sharpe']:+.3f} dS_H {spe['h_sharpe']-SP_BASE['h_sharpe']:+.3f} dS_F {spe['sharpe']-SP_BASE['sharpe']:+.3f}  "
                f"nOn {len(on_s)} | SPY D days: 2x-leg flagged n{len(a_)} {sum(a_)/max(1,len(a_))*1e4:+.0f} bp, unflagged n{len(b_)} "
                f"{sum(b_)/max(1,len(b_))*1e4:+.0f} bp, t {tstat(a_, b_):+.1f}")
        # (d) block bootstrap vs live and vs the exposure-matched control
        log("  (d) circular block bootstrap of the Sharpe / log-return difference (2000 draws):")
        for lab, base_ser in (('vs LIVE', LIVE_SER), ('vs exposure-matched live', CTRL[k]['ctrl_ser'] if k in CTRL else exposure_control(rec['ev']['risky'])[2]),
                              ('vs its flat row', FLAT[act]['ser'])):
            for blk in (20, 60):
                l1, l2, pl, s1, s2, ps = boot(ser, base_ser, blk, seed=(k * 7919 + blk) & 0xffff)
                log(f"      {lab:<26} block {blk:>2}d: Sharpe 95% CI [{s1:+.3f}, {s2:+.3f}] P(<=0)={ps:.3f}   log-return [{l1*100:+.2f}, {l2*100:+.2f}] pp/yr P(<=0)={pl:.3f}")
        # (e) leave-one-major-regime-out
        log("  (e) leave-one-major-regime-out (Sharpe / log-return difference vs live, that window removed):")
        for rlab, a0, b0 in REGIMES:
            keep = [i for i, r in enumerate(rows) if not (a0 <= r['d'] <= b0)]
            ca = [ser[i] for i in keep]; cb = [LIVE_SER[i] for i in keep]
            la, sa = bstats(ca); lb, sb = bstats(cb)
            log(f"      drop {rlab:<26} Sharpe {sa-sb:+.3f}   log-return {(la-lb)*100:+.2f} pp/yr")
        # (f) per-year contribution of the override days (where does the money come from)
        by = {}
        for r, x, y in zip(rows, ser, LIVE_SER):
            if r['d'] in on: by[r['d'][:4]] = by.get(r['d'][:4], 0.0) + math.log1p(x) - math.log1p(y)
        top = sorted(by.items(), key=lambda kv: -abs(kv[1]))[:8]
        log("  (f) log-return difference vs live accumulated on override days, by year (top 8 by size): " +
            ", ".join(f"{y} {v*100:+.1f}pp" for y, v in top) + f"; years positive {sum(1 for v in by.values() if v > 0)}/{len(by)}")

    # ---- reference: the previously-studied QQEW/QQQ breadth gate on the SAME rows (2007-07+), for scale only
    try:
        QQEW = {}
        for r_ in csv.DictReader(open('data/QQEW_daily_ext.csv')):
            try: QQEW[r_['d']] = float(r_['c'])
            except ValueError: pass
        lr = [None if (d not in QQEW or d not in _QQQ_FULL) else math.log(QQEW[d] / _QQQ_FULL[d]) for d in _QD_EXT]
        ch = [None if (i < 60 or lr[i] is None or lr[i - 60] is None) else lr[i] - lr[i - 60] for i in range(len(lr))]
        pc = trailing_pct(ch)
        sub = [r for r in rows if pc[QIX[r['d']]] is not None]
        onb = set(r['d'] for r in sub if r['state'] == 'D' and pc[QIX[r['d']]] < 0.2)
        def bfn(r): return vt(ACTIONS['cash'], r['vol']) if r['d'] in onb else BASE[r['d']]
        e_l = evaluate(sub, live_fn); e_b = evaluate(sub, bfn)
        log(f"\nREFERENCE (already studied, breadth_signal/dgate_anatomy; not part of this grid): QQEW/QQQ 60d-change bottom-quintile D gate -> cash, "
            f"same {len(sub)} rows {sub[0]['d']}..{sub[-1]['d']}: live {e_l['cagr']*100:.2f}% / {e_l['sharpe']:.3f} (S {e_l['s_sharpe']:.3f} H {e_l['h_sharpe']:.3f}) "
            f"-> gate {e_b['cagr']*100:.2f}% / {e_b['sharpe']:.3f} (S {e_b['s_sharpe']:.3f} H {e_b['h_sharpe']:.3f}), nOn {len(onb)}")
    except Exception as e_:
        log(f"\nREFERENCE breadth gate skipped: {e_}")
    log(f"\n[diag done]  elapsed {time.time()-T0:.0f}s")
