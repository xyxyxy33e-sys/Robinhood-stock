"""Research line qqew_vol_supplement (2026-09-11): does the equal-weight Nasdaq-100's realized volatility, or the
DISPERSION between equal-weight and cap-weight vol, add anything as a SECOND INPUT to the live vol-target estimator?

Owner: "not as a replacement, think as a supplement".  The live vol target scales the four risky legs by
min(1, 20% / 30-day realized QQQ vol).  Target (20%), cap (1.0) and lookback (30d) are unchanged in every variant;
ONLY the estimator argument of vt() changes.  No other rule is touched.

Series (all causal at d0's close, on the QQEW rows 2007-07-27+; data/QQEW_daily_ext.csv):
  v_q  = 30d realized QQQ vol (the live input; r['vol'] on the harness rows, asserted == state.realized_vol)
  v_e  = 30d realized QQEW vol                      (state.realized_vol on the QQEW close series)
  v_e10= 10d realized QQEW vol
  v_r  = 30d realized vol of the QQEW/QQQ ratio     (= dispersion / idiosyncratic component; realized_vol on the ratio)
  spread = v_e - v_q, ratio = v_e / v_q, each with a trailing-252-session percentile (breadth_dgate_2000.trailing_pct)

Variants (estimator argument only):
  (1) max(v_q, v_e)               (2) 0.75/0.25 and 0.5/0.5 blends of v_q, v_e     (3) v_e alone  [REPLACEMENT, reference only]
  (4) v_q + k*v_r, k in {0.5, 1}  (5) v_q*(1 + c*max(0, spread_pct - 0.8)), c in {0.5, 1}   (6) max(v_e10, v_q)
  + sign-flip placebos of the three families (min(v_q,v_e); v_q - k*v_r; boost when spread_pct < 0.2).

For every variant: full/SEARCH/HOLDOUT through the harness (evaluate/run of improvement_search, costs and the 5% drift
band inside), rebalances/yr and L1 turnover (a counted copy of run(), asserted bit-identical), average exposure, the
exposure-matched live control (bisection of k*LIVE over the TRUE live function), real weekly rows via RF.eval_real,
circular block bootstrap 20/60d vs live, leave-one-regime-out (block_bootstrap.REGIMES), the recovery-window cost
(recovery_study episode definition, recovery halves [trough, window end)), and the days on which the variant's
multiplier differs from live's by more than 0.05.  Descriptive: corr(v_e, v_q), how often v_e > v_q, and the
dispersion series around the 66 worst-1% overnight gaps of overnight_intraday.

Research only.  Nothing is applied.  Standard library only.  Run from the repo root:
    python3 paper-track/qqew_vol_supplement.py            (~4-6 min with 2000 bootstrap draws)
    QVS_NB=200 python3 paper-track/qqew_vol_supplement.py (quick)
    QVS_STAGE=boot / QVS_STAGE=rest  split the two long halves (each < 10 min at 2000 draws)
"""
import sys, os, math, csv, bisect, zlib, random, inspect, time, statistics
sys.path.insert(0, 'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from state import extension_scale, realized_vol, VOL_TARGET_PA, VOL_TARGET_CAP, vol_target_multiplier
import block_bootstrap as BB
from block_bootstrap import boot, stats, REGIMES
from improvement_search import SEARCH, HOLDOUT, era
import improvement_search as IS
from long_history_backtest import load_px as _load_px
NB = int(os.environ.get('QVS_NB', '2000')); BB.N_BOOT = NB
STAGE = os.environ.get('QVS_STAGE', 'all')   # all | boot (sections 1-3 + full-sample bootstrap) | rest (sections 1-3 + LORO/recovery/signature/summary)
T0 = time.time()
def el(): return f"[{time.time()-T0:4.0f}s]"

print("=" * 118)
print("RESEARCH LINE qqew_vol_supplement -- equal-weight Nasdaq vol / dispersion as a SECOND INPUT to the live vol-target estimator")
print("=" * 118)

# ---- reuse: sections 0..3 of breadth_dgate_2000.py verbatim (standing-figure assert, QQEW/QQQ data, trailing_pct, attach,
#      live_w/LIVE/LIVE_R/fmt, exposure_control_live, sub_rows, both, seed, mean/corr/tstat, FF, load_dc) -- the same
#      block qqew_dma_overlay.py reuses, so the 4,800 reference rows are the same rows.
_SRC = open('paper-track/breadth_dgate_2000.py').read()
_A = _SRC.index('# ------------------------------------------------------------------ 0. live design')
_B = _SRC.index('# ------------------------------------------------------------------ 4. VALIDATION')
exec(_SRC[_A:_B])
print(f"\n(reused breadth_dgate_2000.py sections 0-3 verbatim: {_SRC[_A:_B].count(chr(10))} lines)  {el()}")

# ---- counted run: verbatim copy of improvement_search.run plus a rebalance counter and an L1 turnover accumulator
_src = inspect.getsource(IS.run).replace('def run(', 'def run_counted(') \
    .replace('cost = ONE_WAY_SPREAD * drift', 'cost = ONE_WAY_SPREAD * drift; NREB[0] += 1; TURN[0] += drift') \
    .replace('return rets, risky / len(rows)', 'return rets, risky / len(rows), NREB[0], TURN[0]') \
    .replace('    held = prev = None', '    NREB[0] = 0; TURN[0] = 0.0\n    held = prev = None')
_ns = dict(ONE_WAY_SPREAD=IS.ONE_WAY_SPREAD, BAND=IS.BAND, NREB=[0], TURN=[0.0]); exec(_src, _ns); run_counted = _ns['run_counted']
_a, _e = run(rows, LIVE); _b, _e2, _n, _t = run_counted(rows, LIVE)
assert _a == _b and _e == _e2, 'counted run diverges from harness run'
print(f"  live on the full 26y proxy: {_n/(len(rows)/252):.1f} rebalances/yr, L1 turnover {_t/(len(rows)/252):.2f}x/yr, drift band {IS.BAND}")

# ================================================================== 1. the reference rows and the vol series
QPATH = 'data/QQEW_daily_ext.csv' if os.path.exists('data/QQEW_daily_ext.csv') else 'data/QQEW_daily.csv'
QQEW_X = load_dc(QPATH); dq = sorted(QQEW_X)
dr = [d for d in dq if d in qqq]; RATIO = {d: QQEW_X[d] / qqq[d] for d in dr}
K = 'qqew_60'; RQ = sub_rows(K)
BL_EV = evaluate(RQ, LIVE); A_LIVE, EXP_LIVE, NREB_LIVE, TURN_LIVE = run_counted(RQ, LIVE)
YRS = len(RQ) / 252
print(f"\nREFERENCE on the {len(RQ)} QQEW rows {RQ[0]['d']}..{RQ[-1]['d']}: live {fmt(BL_EV)} S {BL_EV['s_sharpe']:.3f} H {BL_EV['h_sharpe']:.3f}"
      f" exp {BL_EV['risky']*100:.2f}%  reb/yr {NREB_LIVE/YRS:.1f}  L1 turnover {TURN_LIVE/YRS:.2f}x/yr   (note: 26.09/1.006/-33.6 S 1.103 H 0.876)")
assert abs(BL_EV['sharpe'] - 1.006) < 0.002 and abs(BL_EV['s_sharpe'] - 1.103) < 0.002 and abs(BL_EV['h_sharpe'] - 0.876) < 0.002
RR = [r for r in rr if r['d0'] >= RQ[0]['d']]; assert len(RR) == len(rr)
REAL_LIVE = RF.eval_real(rr, LIVE_R)

# the vol series, each via state.realized_vol on its own price series (30d and 10d), keyed by session
print(f"\nVOL SERIES  QQEW {QPATH} {dq[0]}..{dq[-1]} ({len(dq)} sessions); ratio sessions {len(dr)}  {el()}")
VE = {d: realized_vol(dq, QQEW_X, as_of=d, lookback=30) for d in dq}
VE10 = {d: realized_vol(dq, QQEW_X, as_of=d, lookback=10) for d in dq}
VR = {d: realized_vol(dr, RATIO, as_of=d, lookback=30) for d in dr}
VQ = {d: realized_vol(qd, qqq, as_of=d, lookback=30) for d in dr}
print(f"  computed v_e, v_e10, v_r, v_q  {el()}")
# spread / ratio and their trailing-252 percentiles, built ONCE on the daily (dr) calendar
SPR = [None if (VE.get(d) is None or VQ.get(d) is None) else VE[d] - VQ[d] for d in dr]
RAT = [None if (VE.get(d) is None or VQ.get(d) is None) else VE[d] / VQ[d] for d in dr]
VRL = [VR.get(d) for d in dr]
SPR_P = trailing_pct(SPR); RAT_P = trailing_pct(RAT); VR_P = trailing_pct(VRL)
rix_dr = {d: i for i, d in enumerate(dr)}

def attach_v(r, d):
    j = bisect.bisect_right(dr, d) - 1; dd = dr[j]; i = rix_dr[dd]
    r['ve'] = VE[dd]; r['ve10'] = VE10[dd]; r['vr'] = VR[dd]; r['vq_chk'] = VQ[dd]
    r['spr'] = SPR[i]; r['rat'] = RAT[i]; r['spr_p'] = SPR_P[i]; r['rat_p'] = RAT_P[i]; r['vr_p'] = VR_P[i]; r['v_stale'] = dd != d
for r in RQ: attach_v(r, r['d'])
for r in rr: attach_v(r, r['d0'])
# the live input is r['vol'] (plain 30d after the 09-09 revert); assert it IS state.realized_vol(30) on both row kinds
mx_d = max(abs(r['vol'] - realized_vol(ds, px, as_of=r['d'], lookback=30)) for r in RQ[::7])
mx_r = max(abs(r['vol'] - realized_vol(qd, qqq, as_of=r['d0'], lookback=30)) for r in rr)
assert mx_d < 1e-9 and mx_r < 1e-9, (mx_d, mx_r)
miss = [r['d'] for r in RQ if any(r[k] is None for k in ('ve', 've10', 'vr', 'spr_p', 'rat_p', 'vr_p'))]
assert not miss, miss[:5]
assert all(r[k] is not None for r in rr for k in ('ve', 'vr', 'spr_p'))
print(f"  r['vol'] == realized_vol(30d) on daily rows (max diff {mx_d:.1e}) and real rows ({mx_r:.1e}); all series present on all {len(RQ)} rows;"
      f" stale QQEW prints {sum(1 for r in RQ if r['v_stale'])}")

# ================================================================== 2. descriptive
def pc(n, d): return f"{100*n/d:5.1f}%" if d else "    -"
def sub(rs, lo, hi): return [r for r in rs if lo <= r['d'] <= hi]
def q(a, p):
    s = sorted(a); k = (len(s) - 1) * p; f = int(k); return s[f] + (s[min(f + 1, len(s) - 1)] - s[f]) * (k - f)
ve_ = [r['ve'] for r in RQ]; vq_ = [r['vol'] for r in RQ]; vr_ = [r['vr'] for r in RQ]; spr_ = [r['spr'] for r in RQ]; rat_ = [r['rat'] for r in RQ]
print(f"\nDESCRIPTIVE on the {len(RQ)} rows")
print(f"  mean v_q {mean(vq_)*100:.2f}%  v_e {mean(ve_)*100:.2f}%  v_r {mean(vr_)*100:.2f}%  | median v_q {q(vq_,.5)*100:.2f}% v_e {q(ve_,.5)*100:.2f}%")
print(f"  corr(v_e, v_q) {corr(ve_, vq_):+.4f}   corr(log v_e, log v_q) {corr([math.log(x) for x in ve_], [math.log(x) for x in vq_]):+.4f}"
      f"   corr(v_r, v_q) {corr(vr_, vq_):+.3f}   corr(spread, v_q) {corr(spr_, vq_):+.3f}")
print(f"  v_e > v_q on {pc(sum(1 for r in RQ if r['ve'] > r['vol']), len(RQ))} of days; v_e > 1.05 v_q on {pc(sum(1 for r in RQ if r['ve'] > 1.05*r['vol']), len(RQ))};"
      f" v_e > 1.10 v_q on {pc(sum(1 for r in RQ if r['ve'] > 1.10*r['vol']), len(RQ))}")
print(f"  spread v_e-v_q: mean {mean(spr_)*100:+.2f}pp  p5 {q(spr_,.05)*100:+.2f}  p25 {q(spr_,.25)*100:+.2f}  p50 {q(spr_,.5)*100:+.2f}  p75 {q(spr_,.75)*100:+.2f}  p95 {q(spr_,.95)*100:+.2f}"
      f" | ratio v_e/v_q: p5 {q(rat_,.05):.3f} p50 {q(rat_,.5):.3f} p95 {q(rat_,.95):.3f}")
print(f"  v_r / v_q: mean {mean([a/b for a,b in zip(vr_, vq_)]):.3f}   (v_r is the vol of the equal-weight-minus-cap-weight daily return)")
print(f"  {'regime':<26}{'n':>6}{'v_q':>8}{'v_e':>8}{'v_r':>8}{'spread':>9}{'v_e>v_q':>9}{'spr_p>.8':>10}")
for lab, lo, hi in REGIMES + [('calm 2013-2014', '2013-01-01', '2014-12-31'), ('2018 Q4', '2018-10-01', '2018-12-31')]:
    s = sub(RQ, lo, hi)
    if not s: continue
    print(f"  {lab:<26}{len(s):>6}{mean([r['vol'] for r in s])*100:7.1f}%{mean([r['ve'] for r in s])*100:7.1f}%{mean([r['vr'] for r in s])*100:7.1f}%"
          f"{mean([r['spr'] for r in s])*100:+8.2f}p{pc(sum(1 for r in s if r['ve']>r['vol']), len(s)):>9}{pc(sum(1 for r in s if r['spr_p']>0.8), len(s)):>10}")
# where the live multiplier bites vs where v_e would bite more
print(f"  live multiplier < 1 on {pc(sum(1 for r in RQ if r['vol'] > VOL_TARGET_PA), len(RQ))} of days; v_e > 20% on {pc(sum(1 for r in RQ if r['ve'] > VOL_TARGET_PA), len(RQ))};"
      f" v_e > 20% while v_q <= 20% on {sum(1 for r in RQ if r['ve'] > VOL_TARGET_PA >= r['vol'])} days; v_q > 20% while v_e <= 20% on {sum(1 for r in RQ if r['vol'] > VOL_TARGET_PA >= r['ve'])} days")

# ---- the 66 worst-1% overnight gaps (overnight_intraday definition: worst 1% of open_{d1}/close_{d0}-1 on the full proxy rows)
O = {}; C = {}
for x in csv.DictReader(open('data/qqq_ohlc.csv')): O[x['d']] = float(x['o']); C[x['d']] = float(x['c'])
d1_of = {rows[i]['d']: rows[i + 1]['d'] for i in range(len(rows) - 1)}; d1_of[rows[-1]['d']] = ds[ds.index(rows[-1]['d']) + 1] if rows[-1]['d'] != ds[-1] else None
GAP = {r['d']: O[d1_of[r['d']]] / C[r['d']] - 1 for r in rows if d1_of[r['d']] and d1_of[r['d']] in O}
kk = int(math.ceil(len(rows) * 0.01)); worst = sorted(GAP, key=lambda d: GAP[d])[:kk]
worstQ = sorted(d for d in worst if d >= RQ[0]['d'] and d in rix_dr)
print(f"\nWORST-1% OVERNIGHT GAPS: {kk} on the full proxy (mean {mean([GAP[d] for d in worst])*100:+.2f}%), {len(worstQ)} inside the QQEW window"
      f" (mean {mean([GAP[d] for d in worstQ])*100:+.2f}%)")
print("  event-time profile (session offsets relative to d0 = the close before the gap; unconditional mean of a percentile = 0.50):")
OFFS = (-20, -10, -5, -3, -1, 0, 1, 3, 5, 10, 20)
def prof(series_p, lab):
    out = []
    for k in OFFS:
        vals = [series_p[rix_dr[d] + k] for d in worstQ if 0 <= rix_dr[d] + k < len(dr) and series_p[rix_dr[d] + k] is not None]
        out.append(mean(vals))
    print(f"  {lab:<24}" + ''.join(f"{v:7.2f}" for v in out))
print(f"  {'offset':<24}" + ''.join(f"{k:7d}" for k in OFFS))
prof(SPR_P, 'spread pct'); prof(RAT_P, 'ratio pct'); prof(VR_P, 'v_r pct')
# raw levels relative to their own value at d0-20 (does dispersion rise BEFORE the gap?)
def lvl(series, lab):
    out = []
    for k in OFFS:
        vals = [series[rix_dr[d] + k] for d in worstQ if 0 <= rix_dr[d] + k < len(dr)]
        out.append(mean(vals) * 100)
    print(f"  {lab:<24}" + ''.join(f"{v:7.2f}" for v in out))
lvl([VQ.get(d) for d in dr], 'v_q level %'); lvl([VE.get(d) for d in dr], 'v_e level %'); lvl(VRL, 'v_r level %'); lvl(SPR, 'spread level pp')
# count: on how many of the gaps was spread pct > 0.8 (the variant-5 trigger) already at d0-1 / d0; and v_e > v_q at d0
n_pre = sum(1 for d in worstQ if SPR_P[rix_dr[d] - 1] is not None and SPR_P[rix_dr[d] - 1] > 0.8)
n_at = sum(1 for d in worstQ if SPR_P[rix_dr[d]] > 0.8); n_after = sum(1 for d in worstQ if rix_dr[d] + 5 < len(dr) and SPR_P[rix_dr[d] + 5] > 0.8)
n_ve = sum(1 for d in worstQ if VE[d] > VQ[d])
print(f"  spread pct > 0.8 at d0-1: {n_pre}/{len(worstQ)}, at d0: {n_at}, at d0+5: {n_after}  | v_e > v_q at d0: {n_ve}/{len(worstQ)}"
      f" | unconditional P(spread pct > 0.8) = {pc(sum(1 for r in RQ if r['spr_p']>0.8), len(RQ))}")
# lead/lag: cross-correlation of daily changes of v_e vs v_q (does v_e move first?)
dv_e = [VE[dr[i]] - VE[dr[i-1]] for i in range(1, len(dr)) if VE.get(dr[i]) and VE.get(dr[i-1])]
dv_q = [VQ[dr[i]] - VQ[dr[i-1]] for i in range(1, len(dr)) if VE.get(dr[i]) and VE.get(dr[i-1])]
print("  lead/lag corr of daily CHANGES, corr(dv_e[t], dv_q[t+k]) for k = -3..+3 (positive k = v_e leads):")
print("    " + '  '.join(f"k={k:+d} {corr(dv_e[max(0,-k):len(dv_e)-max(0,k)], dv_q[max(0,k):len(dv_q)-max(0,-k)]):+.3f}" for k in (-3, -2, -1, 0, 1, 2, 3)))

# ================================================================== 3. variants (estimator argument only)
def E_live(r): return r['vol']
def E_max(r): return max(r['vol'], r['ve'])
def E_min(r): return min(r['vol'], r['ve'])
def E_blend(a): return lambda r: a * r['vol'] + (1 - a) * r['ve']
def E_ve(r): return r['ve']
def E_vr(k): return lambda r: r['vol'] + k * r['vr']
def E_vr_neg(k): return lambda r: max(1e-6, r['vol'] - k * r['vr'])
def E_spr(c, thr=0.8): return lambda r: r['vol'] * (1 + c * max(0.0, r['spr_p'] - thr))
def E_spr_flip(c, thr=0.2): return lambda r: r['vol'] * (1 + c * max(0.0, thr - r['spr_p']))
def E_fast(r): return max(r['vol'], r['ve10'])
def E_rat(c, thr=0.8): return lambda r: r['vol'] * (1 + c * max(0.0, r['rat_p'] - thr))

VARIANTS = [   # (label, estimator, is_candidate, is_replacement)
    ('LIVE v_q (30d QQQ)', E_live, False, False),
    ('(1) max(v_q, v_e)', E_max, True, False),
    ('(2) 0.75 v_q + 0.25 v_e', E_blend(0.75), True, False),
    ('(2) 0.50 v_q + 0.50 v_e', E_blend(0.5), True, False),
    ('(3) v_e alone [REPLACEMENT]', E_ve, True, True),
    ('(4) v_q + 0.5 v_r', E_vr(0.5), True, False),
    ('(4) v_q + 1.0 v_r', E_vr(1.0), True, False),
    ('(5) v_q(1+0.5 max(0,sp-.8))', E_spr(0.5), True, False),
    ('(5) v_q(1+1.0 max(0,sp-.8))', E_spr(1.0), True, False),
    ('(6) max(v_e10, v_q)', E_fast, True, False),
]
PLACEBOS = [
    ('placebo min(v_q, v_e)', E_min),
    ('placebo v_q - 0.5 v_r', E_vr_neg(0.5)),
    ('placebo v_q - 1.0 v_r', E_vr_neg(1.0)),
    ('placebo v_q(1+1.0 max(0,.2-sp))', E_spr_flip(1.0)),
    ('extra v_q(1+max(0,ratio_p-.8))', E_rat(1.0)),
]
NCAND = sum(1 for v in VARIANTS if v[2])

def wfn(est, vtf=vt):
    def fn(r):
        w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
        if f < 1: w = tuple(a * f for a in w[:4]) + (1 - f * sum(w[:4]),)
        return vtf(w, est(r))
    return fn
assert all(wfn(E_live)(r) == LIVE(r) for r in RQ) and all(wfn(E_live, RF.vt)(r) == LIVE_R(r) for r in rr)

def mult(v): return vol_target_multiplier(v)   # min(cap, target/vol) -- state.py's own
RES = {}
print(f"\nVARIANTS on the {len(RQ)} QQEW rows (estimator argument only; target 20%, cap 1.0, lookback 30d, drift band {IS.BAND} unchanged)  {el()}")
hdr = (f"  {'variant':<32}{'CAGR/Sharpe/MDD':>22}{'S':>7}{'H':>7}{'dS':>8}{'dH':>8}{'exp':>7}{'reb/yr':>8}{'L1/yr':>7}{'real CAGR/Sh/MDD':>24}{'dReal':>7}"
       f"{'|d|>.05':>8}{'lower':>7}{'higher':>7}{'k-live':>8}{'dS_k':>7}{'dH_k':>7}")
print(hdr)
for lab, est, cand, repl in VARIANTS + [(l, e, False, False) for l, e in PLACEBOS]:
    fn = wfn(est); a, ex, nreb, turn = run_counted(RQ, fn); ev = evaluate(RQ, fn); assert a == run(RQ, fn)[0]
    re = RF.eval_real(rr, wfn(est, RF.vt))
    diffs = [mult(est(r)) - mult(r['vol']) for r in RQ]
    nlo = sum(1 for x in diffs if x < -0.05); nhi = sum(1 for x in diffs if x > 0.05)
    kk_, ke = exposure_control_live(RQ, ev['risky']) if abs(ev['risky'] - BL_EV['risky']) > 1e-6 else (1.0, BL_EV)
    RES[lab] = dict(ev=ev, re=re, a=a, nreb=nreb, turn=turn, diffs=diffs, k=kk_, ke=ke, cand=cand, repl=repl, est=est, fn=fn)
    print(f"  {lab:<32}{fmt(ev):>22}{ev['s_sharpe']:7.3f}{ev['h_sharpe']:7.3f}{ev['s_sharpe']-BL_EV['s_sharpe']:+8.3f}{ev['h_sharpe']-BL_EV['h_sharpe']:+8.3f}"
          f"{ev['risky']*100:6.1f}%{nreb/YRS:8.1f}{turn/YRS:7.2f}{fmt(re):>24}{re['sharpe']-REAL_LIVE['sharpe']:+7.3f}"
          f"{nlo+nhi:8d}{nlo:7d}{nhi:7d}{kk_:8.3f}{ev['s_sharpe']-ke['s_sharpe']:+7.3f}{ev['h_sharpe']-ke['h_sharpe']:+7.3f}", flush=True)
print(f"  (dS/dH = vs live; |d|>.05 = days the variant multiplier differs from live by > 0.05, lower = variant holds LESS; k-live = exposure-matched live"
      f" control k*LIVE with dS_k/dH_k the variant minus that control.  Live: {NREB_LIVE/YRS:.1f} reb/yr, L1 {TURN_LIVE/YRS:.2f}x/yr, real {fmt(REAL_LIVE)})")
print(f"  CANDIDATE COUNT: {NCAND} (of which 1 is a replacement, reference only); placebos {len(PLACEBOS)} not counted.")
print(f"  both-era passes vs live: {[l for l, v in RES.items() if v['cand'] and both(v['ev'], BL_EV)]}")
print(f"  both-era passes vs the exposure-matched control: {[l for l, v in RES.items() if v['cand'] and both(v['ev'], v['ke'])]}")

# ---- the multiplier-difference days: when, and in which direction
print(f"\nMULTIPLIER DIFFERENCE DAYS (|variant mult - live mult| > 0.05): count by year and the longest runs")
labs = [l for l, v in RES.items() if v['cand']]
years = sorted({r['d'][:4] for r in RQ})
print(f"  {'year':<6}" + ''.join(f"{l[:14]:>15}" for l in labs))
for y in years:
    idx = [i for i, r in enumerate(RQ) if r['d'][:4] == y]
    print(f"  {y:<6}" + ''.join(f"{sum(1 for i in idx if RES[l]['diffs'][i] < -0.05):>7}/{sum(1 for i in idx if RES[l]['diffs'][i] > 0.05):<7}" for l in labs))
print("  (lower/higher: days the variant holds less / more than live)")
for l in labs:
    d_ = RES[l]['diffs']; runs = []; i = 0
    while i < len(d_):
        if abs(d_[i]) > 0.05:
            j = i
            while j + 1 < len(d_) and abs(d_[j + 1]) > 0.05: j += 1
            runs.append((RQ[i]['d'], RQ[j]['d'], j - i + 1, mean(d_[i:j + 1]))); i = j + 1
        else: i += 1
    runs.sort(key=lambda t: -t[2])
    print(f"  {l:<32} {len(runs):>3} runs, mean |diff| on those days {mean([abs(x) for x in d_ if abs(x) > 0.05]) if any(abs(x) > 0.05 for x in d_) else 0:.3f}; "
          f"longest: " + '; '.join(f"{a}..{b} ({n}d, {m:+.2f})" for a, b, n, m in runs[:5]))

# ================================================================== 4. bootstrap, leave-one-regime-out, recovery windows
if STAGE in ("all", "boot"):
  print(f"\nBLOCK BOOTSTRAP vs live ({NB} draws, circular paired blocks 20/60d) -- every candidate and the placebos  {el()}")
  for lab, v in RES.items():
    if lab.startswith('LIVE'): continue
    out = []
    for blk in (20, 60):
        l1, l2, pl, s1, s2, ps = boot(v['a'], A_LIVE, blk, seed=seed('qvs', lab, blk))
        out.append(f"{blk}d: logret {(stats(v['a'])[0]-stats(A_LIVE)[0])*100:+.2f}pp/yr CI [{l1*100:+.2f},{l2*100:+.2f}] P<=0 {pl:.3f}; Sharpe CI [{s1:+.3f},{s2:+.3f}] P<=0 {ps:.3f}")
    print(f"  {lab:<32} " + ' | '.join(out), flush=True)
if STAGE == 'boot': print(f"  stage boot done {el()}"); sys.exit(0)

print(f"\nLEAVE-ONE-REGIME-OUT (Sharpe, variant minus live): regime ALONE / sample with the regime DROPPED  {el()}")
print(f"  {'variant':<32}" + ''.join(f"{lab[:20]:>24}" for lab, _, _ in REGIMES))
print(f"  {'':<32}" + ''.join(f"{'alone':>12}{'dropped':>12}" for _ in REGIMES))
def sharpe_of(a): return stats(a)[1]
for lab, v in RES.items():
    if lab.startswith('LIVE') or not (v['cand'] or lab.startswith('placebo min') or lab.startswith('extra')): continue
    cells = []
    for rl, lo, hi in REGIMES:
        ins = [i for i, r in enumerate(RQ) if lo <= r['d'] <= hi]; outs = [i for i, r in enumerate(RQ) if not (lo <= r['d'] <= hi)]
        if not ins: cells.append(f"{'-':>12}{'-':>12}"); continue
        d_in = sharpe_of([v['a'][i] for i in ins]) - sharpe_of([A_LIVE[i] for i in ins])
        d_out = sharpe_of([v['a'][i] for i in outs]) - sharpe_of([A_LIVE[i] for i in outs])
        cells.append(f"{d_in:+12.3f}{d_out:+12.3f}")
    print(f"  {lab:<32}" + ''.join(cells))
print("  (no rows in dot-com on the QQEW window; GFC = 2007-07-27..2009-12-31 here)")

# ---- recovery windows: recovery_study.py's own episode definition (exec of its episodes block), recovery halves [trough, window end)
RUN_N = 252; MIN_DD = 0.15; SEC_LO = 0.08
_RS = open('paper-track/recovery_study.py').read()
exec(_RS[_RS.index('# ---------------------------------------------------------------- episodes'):_RS.index('def ep_table')])
rixQ = {r['d']: k for k, r in enumerate(RQ)}
EPQ = [e for e in PRIMARY if ds[e['T']] in rixQ and ds[e['Rw']] in rixQ or (ds[e['T']] in rixQ and ds[e['Rw']] > RQ[-1]['d'])]
print(f"\nRECOVERY WINDOWS (recovery_study episode definition; primary set depth <= -15%; recovery half = [trough, window end)): "
      f"{len(EPQ)} episodes inside the QQEW rows  {el()}")
print("  " + ', '.join(f"{e['name']} T {ds[e['T']]} -> {ds[e['Rw']] if ds[e['Rw']] in rixQ else RQ[-1]['d']} ({e['Rw_kind']}, depth {e['depth']*100:.0f}%)" for e in EPQ))
winr = []
for e in EPQ: winr.extend(range(rixQ[ds[e['T']]], rixQ.get(ds[e['Rw']], len(RQ))))
print(f"  {len(winr)} sessions in recovery halves ({len(winr)/len(RQ)*100:.0f}% of rows). Annualised log-return and Sharpe, variant minus live, with 20/60d block bootstrap:")
print(f"  {'variant':<32}{'dlogret/yr':>12}{'dSharpe':>9}{'exp var':>9}{'exp live':>9}   20d CI / P<=0            60d CI / P<=0        per-episode dlogret (pp, trough->end)")
for lab, v in RES.items():
    if lab.startswith('LIVE'): continue
    a = [v['a'][k] for k in winr]; b = [A_LIVE[k] for k in winr]
    la, sa = stats(a); lb, sb = stats(b)
    # held exposure inside the windows: the variant's and live's (average of target exposure is a fair proxy of the difference)
    ea = mean([sum(v['fn'](RQ[k])[:4]) for k in winr]); eb = mean([sum(LIVE(RQ[k])[:4]) for k in winr])
    per = []
    for e in EPQ:
        ks = range(rixQ[ds[e['T']]], rixQ.get(ds[e['Rw']], len(RQ)))
        per.append(sum(math.log1p(v['a'][k]) for k in ks) - sum(math.log1p(A_LIVE[k]) for k in ks))
    cells = []
    for blk in (20, 60):
        l1, l2, pl, s1, s2, ps = boot(a, b, blk, seed=seed('qvs-rec', lab, blk))
        cells.append(f"[{l1*100:+.1f},{l2*100:+.1f}] {pl:.3f}")
    print(f"  {lab:<32}{(la-lb)*100:+12.2f}{sa-sb:+9.3f}{ea*100:8.1f}%{eb*100:8.1f}%   {cells[0]:<24} {cells[1]:<24} " + ' '.join(f"{x*100:+.1f}" for x in per), flush=True)
print("  (recovery_study measured the reverted max(10,30) QQQ estimator at -2.1pp/yr [-3.3,-1.1] on the same construction over the full proxy)")

# ---- the signature of variant (6) vs the reverted max(10,30) on QQQ: same COVID-only + rebalances profile?
def E_q1030(r): return max(r['vol'], realized_vol(ds, px, as_of=r['d'], lookback=10))
fn_q = wfn(E_q1030); a_q, e_q, n_q, t_q = run_counted(RQ, fn_q); ev_q = evaluate(RQ, fn_q)
print(f"\nSIGNATURE CHECK: the reverted max(10d QQQ, 30d QQQ) on the same rows: {fmt(ev_q)} S {ev_q['s_sharpe']:.3f} H {ev_q['h_sharpe']:.3f}"
      f" exp {e_q*100:.1f}% reb/yr {n_q/YRS:.1f} L1 {t_q/YRS:.2f}  (live {NREB_LIVE/YRS:.1f} / {TURN_LIVE/YRS:.2f})")
v6 = RES['(6) max(v_e10, v_q)']
for rl, lo, hi in REGIMES:
    ins = [i for i, r in enumerate(RQ) if lo <= r['d'] <= hi]
    if not ins: continue
    dq_ = sharpe_of([a_q[i] for i in ins]) - sharpe_of([A_LIVE[i] for i in ins]); d6 = sharpe_of([v6['a'][i] for i in ins]) - sharpe_of([A_LIVE[i] for i in ins])
    print(f"  {rl:<26} dSharpe vs live: max(10,30) QQQ {dq_:+.3f}   max(10d QQEW, 30d QQQ) {d6:+.3f}")
agree = sum(1 for r, x, y in zip(RQ, a_q, v6['a']) if abs(mult(E_q1030(r)) - mult(E_fast(r))) <= 0.05)
print(f"  multipliers of the two fast variants within 0.05 of each other on {pc(agree, len(RQ))} of days; corr of daily returns {corr(a_q, v6['a']):.5f}")

# ================================================================== 5. summary
print(f"\nSUMMARY  {el()}")
print(f"  live on the QQEW rows: {fmt(BL_EV)} S {BL_EV['s_sharpe']:.3f} H {BL_EV['h_sharpe']:.3f} exp {BL_EV['risky']*100:.1f}% reb/yr {NREB_LIVE/YRS:.1f} L1 {TURN_LIVE/YRS:.2f} real {fmt(REAL_LIVE)}")
print(f"  {'variant':<32}{'both-era vs live':>17}{'vs k-live':>11}{'real':>7}{'dCAGR':>8}{'dSharpe':>9}{'dMDD':>7}{'dReb/yr':>9}{'dL1/yr':>8}{'dExp':>7}")
for lab, v in RES.items():
    if lab.startswith('LIVE'): continue
    ev, re = v['ev'], v['re']
    print(f"  {lab:<32}{('PASS' if both(ev, BL_EV) else 'fail'):>17}{('PASS' if both(ev, v['ke']) else 'fail'):>11}{('+' if re['sharpe'] > REAL_LIVE['sharpe'] else '-'):>7}"
          f"{(ev['cagr']-BL_EV['cagr'])*100:+8.2f}{ev['sharpe']-BL_EV['sharpe']:+9.3f}{(ev['mdd']-BL_EV['mdd'])*100:+7.1f}{(v['nreb']-NREB_LIVE)/YRS:+9.1f}{(v['turn']-TURN_LIVE)/YRS:+8.2f}{(ev['risky']-BL_EV['risky'])*100:+7.2f}")
print(f"  candidates {NCAND}; done {el()}")
