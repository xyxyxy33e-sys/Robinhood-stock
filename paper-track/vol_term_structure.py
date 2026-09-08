"""RESEARCH LINE 4 (2026-09-08): the S&P implied-vol TERM STRUCTURE as a regime
signal. Research only -- change freeze until 2026-12-07, nothing here is applied.

slope_t = VIX_t / VXV_t (ratio) and VIX_t - VXV_t (difference), VXV = CBOE S&P
500 3-Month Volatility Index (FRED VXVCLS, from 2007-12-04, data/vxvcls.csv).
Contango (ratio < 1) is the calm state; backwardation (ratio > 1) is stress
that is HERE rather than forecast. The literature treats the slope as a
cleaner regime signal than the level, and nothing in this project has looked
at it.

DATA. FRED carries VXVCLS. It does NOT carry VXSTCLS / VIX9D (short end),
VXMT / VIX6M (long end), nor ANY Nasdaq-100 3-month index (VXN3M is not on
FRED) -- all probed 2026-09-08 and every one returned FRED's error page. So
the only obtainable term structure is the S&P one, and this design is on
QQQ. The VIX-vs-VXN work today found the S&P index was the WRONG instrument
for LEVEL signals (negative variance risk premium against QQQ realized vol).
A ratio divides the level out, so that specific failure does not carry over
automatically -- but it is a live risk and is tested directly: the forward-
return mechanism check is run on both QQQ and SPY, and the strategy tests all
run on the QQQ book.

DISCIPLINE (BRIEFING.md): every figure through the project's own harness
(run / evaluate / eval_real), never a hand-rolled loop. SAME ROWS: every
variant INCLUDING the live baseline is restricted to the VXV span (2007-12-04
onward), so figures are NOT comparable to 26-year numbers, and the "holdout"
is 2007-12..2015-10 -- the dot-com bust is OUTSIDE this window. Exposure is
matched by bisection on the rule's own constant, plus exposure_control().
Causal thresholds only (the backwardation line is the structural ratio > 1;
the only other statistic used is an EXPANDING median). Sign-flip placebos,
both-era test, block bootstrap, leave-one-regime-out, candidate count.

Test (c) needs an extra "regime changed" event. run() rebalances when
(r['state'], r['agree']) changes, so the switch is injected by shallow-
copying rows with agree=(agree, backwardation_episode_id): the loop is
untouched and the key changes exactly on entry INTO backwardation. The
rebalance COUNT comes from a verbatim copy of run() with a counter, asserted
to return the identical return series.
"""
import sys, math, random, statistics, inspect
sys.path.insert(0, 'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from state import extension_scale, realized_vol
from improvement_search import SEARCH, HOLDOUT, era
import improvement_search as IS
from improvement_search_r2 import scaled
from downturn_review import exposure_control
from block_bootstrap import boot, stats, N_BOOT

# ------------------------------------------------------------------ helpers
def fred(p):
    """FRED csv -> {date: value}, holidays FORWARD-FILLED (never dropped)."""
    out, last = {}, None
    for ln in open(p).read().splitlines()[1:]:
        d, v = ln.split(',')
        if v.strip():
            last = float(v)
        if last is not None:
            out[d] = last
    return out

vix = fred('data/vixcls_full.csv'); vxv = fred('data/vxvcls.csv')
spy = {}
for ln in open('data/spy_long_history.csv').read().splitlines()[1:]:
    d, c = ln.split(',')[:2]; spy[d] = float(c)
sd = sorted(spy); six = {d: i for i, d in enumerate(sd)}

def trimmed(r):
    w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
    if f < 1: w = tuple(a*f for a in w[:4]) + (1 - f*sum(w[:4]),)
    return w

def live_fn(r):
    return vt(trimmed(r), r.get('vol_live') or r['vol'])

def sharpe_of(rets):
    return stats(rets)[1]

# counted run: verbatim copy of improvement_search.run plus a rebalance counter
_src = inspect.getsource(IS.run)
_src = _src.replace('def run(', 'def run_counted(') \
           .replace('cost = ONE_WAY_SPREAD * drift', 'cost = ONE_WAY_SPREAD * drift; NREB[0] += 1') \
           .replace('return rets, risky / len(rows)', 'return rets, risky / len(rows), NREB[0]') \
           .replace('    held = prev = None', '    NREB[0] = 0\n    held = prev = None')
_ns = dict(ONE_WAY_SPREAD=IS.ONE_WAY_SPREAD, BAND=IS.BAND, NREB=[0]); exec(_src, _ns)
run_counted = _ns['run_counted']
_a, _e = run(rows, live_fn); _b, _e2, _n = run_counted(rows, live_fn)
assert _a == _b and _e == _e2, 'counted run diverges from harness run'

# standing figures, full window (must reproduce before anything else)
ev0 = evaluate(rows, live_fn)
for r in rr:
    a = realized_vol(qd, qqq, as_of=r['d0'], lookback=10); b = realized_vol(qd, qqq, as_of=r['d0'], lookback=30)
    r['vol_live'] = b if (a is None or b is None) else max(a, b)
def live_rr(r):
    return RF.vt(trimmed(r), r['vol_live'])
er0 = RF.eval_real(rr, live_rr)
print('STANDING LIVE FIGURES (full window, must match STRATEGY.md)')
print(f"  26y proxy {ev0['cagr']*100:.2f}% / {ev0['sharpe']:.3f} / {ev0['mdd']*100:.1f}%  S {ev0['s_sharpe']:.3f}  H {ev0['h_sharpe']:.3f}"
      f"  | real weekly {er0['cagr']*100:.2f}% / {er0['sharpe']:.3f} / {er0['mdd']*100:.1f}%  | live rebalances/yr {_n/(len(rows)/252):.1f}")

# alignment sanity: contemporaneous index return vs VIX change
def corr_chg(dates, pxm):
    xs, ys = [], []
    for i in range(1, len(dates)):
        d0, d1 = dates[i-1], dates[i]
        if d0 in vix and d1 in vix: xs.append(pxm[d1]/pxm[d0]-1); ys.append(vix[d1]/vix[d0]-1)
    return statistics.correlation(xs, ys), len(xs)
print(f"  alignment: corr(SPY ret, VIX chg) = {corr_chg(sd, spy)[0]:+.3f}   corr(QQQ ret, VIX chg) = {corr_chg(ds, px)[0]:+.3f}  (contemporaneous, d0->d1)")

# ------------------------------------------------------------------ attach slope
START_VXV = '2007-12-04'
P = [r for r in rows if r['d'] >= START_VXV]
for r in P:
    r['ratio'] = vix[r['d']] / vxv[r['d']]; r['diff'] = vix[r['d']] - vxv[r['d']]
    r['bw'] = r['ratio'] > 1.0
    r['rv_ratio'] = (r['vol10'] / r['vol60']) if (r['vol10'] and r['vol60']) else 1.0
    r['rv_bw'] = r['rv_ratio'] > 1.0
# episode ids: increment on entry INTO backwardation (and separately on exit)
ep = 0; prev = False; ep_any = 0
for r in P:
    if r['bw'] and not prev: ep += 1
    if r['bw'] != prev: ep_any += 1
    r['ep'] = ep; r['ep_any'] = ep_any; prev = r['bw']
ep = 0; prev = False
for r in P:
    if r['rv_bw'] and not prev: ep += 1
    r['rv_ep'] = ep; prev = r['rv_bw']
# expanding (causal) median of vol_live -> "high vol" flag
hv = []; acc = []
for r in P:
    acc.append(r['vol_live']); s = sorted(acc); r['hivol'] = r['vol_live'] > s[len(s)//2]
n_yr = len(P) / 252
print(f"\nROWS: {len(P)} sessions {P[0]['d']}..{P[-1]['d']} ({n_yr:.1f} yr). Holdout in this window = {P[0]['d']}..2015-10-31 "
      f"({len(era(P,*HOLDOUT))} rows) -- dot-com is OUTSIDE it. Search = 2015-11-01+ ({len(era(P,*SEARCH))} rows).")

# ================================================================== PART 0: mechanism
print('\n' + '='*100 + '\nPART 0 -- SLOPE DISTRIBUTION AND FORWARD-RETURN MECHANISM CHECK\n' + '='*100)
ratios = sorted(r['ratio'] for r in P); diffs = sorted(r['diff'] for r in P)
pct = lambda a, q: a[min(len(a)-1, int(q*len(a)))]
print(f"ratio VIX/VXV: mean {statistics.mean(ratios):.3f}  p5 {pct(ratios,.05):.3f}  p25 {pct(ratios,.25):.3f}  median {pct(ratios,.5):.3f}  "
      f"p75 {pct(ratios,.75):.3f}  p95 {pct(ratios,.95):.3f}  max {ratios[-1]:.3f}")
print(f"diff VIX-VXV : mean {statistics.mean(diffs):+.2f}  p5 {pct(diffs,.05):+.2f}  median {pct(diffs,.5):+.2f}  p95 {pct(diffs,.95):+.2f}  max {diffs[-1]:+.2f}")
nb = sum(r['bw'] for r in P)
print(f"backwardation (ratio>1): {nb} of {len(P)} days = {nb/len(P)*100:.1f}%   episodes {P[-1]['ep']}  ({P[-1]['ep']/n_yr:.1f} entries/yr)")
for lab, lo, hi in (('holdout 2007-12..2015-10',)+HOLDOUT, ('search 2015-11+',)+SEARCH):
    E = era(P, lo, hi); print(f"   {lab}: {sum(r['bw'] for r in E)/len(E)*100:.1f}% of days")
def runs(flag):
    out, cur = [], 0
    for r in P:
        if r[flag]: cur += 1
        elif cur: out.append(cur); cur = 0
    if cur: out.append(cur)
    return out
rb = runs('bw'); rc = [len(list(g)) for g in []]
cont, cur = [], 0
for r in P:
    if not r['bw']: cur += 1
    elif cur: cont.append(cur); cur = 0
if cur: cont.append(cur)
print(f"persistence: backwardation runs median {statistics.median(rb):.0f}d mean {statistics.mean(rb):.1f}d max {max(rb)}d  (n={len(rb)}); "
      f"contango runs median {statistics.median(cont):.0f}d mean {statistics.mean(cont):.1f}d")
print(f"   1-day backwardation runs: {sum(1 for x in rb if x==1)} of {len(rb)} ({sum(1 for x in rb if x==1)/len(rb)*100:.0f}%);"
      f"  P(bw tomorrow | bw today) = {sum(1 for i in range(1,len(P)) if P[i]['bw'] and P[i-1]['bw'])/max(1,sum(r['bw'] for r in P[:-1])):.3f}")
# realized-proxy overlap
both = sum(1 for r in P if r['bw'] and r['rv_bw']); print(f"overlap with realized 10d/60d>1: {sum(r['rv_bw'] for r in P)/len(P)*100:.1f}% of days realized-bw; "
      f"P(rv_bw | bw)={both/nb:.2f}  P(bw | rv_bw)={both/sum(r['rv_bw'] for r in P):.2f}; P(hivol | bw)={sum(1 for r in P if r['bw'] and r['hivol'])/nb:.2f}")

def fwd(dates, pxm, ixm, d, k):
    i = ixm.get(d)
    if i is None or i + k >= len(dates): return None
    return pxm[dates[i+k]] / pxm[dates[i]] - 1
def fwd_table(label, cond, dates, pxm, ixm, key='d'):
    out = []
    for k in (1, 5, 21):
        a = [fwd(dates, pxm, ixm, r['d'], k) for r in P if cond(r)]; b = [fwd(dates, pxm, ixm, r['d'], k) for r in P if not cond(r)]
        a = [x for x in a if x is not None]; b = [x for x in b if x is not None]
        ma, mb = statistics.mean(a), statistics.mean(b)
        # SE of the difference using non-overlapping sub-sampling of horizon k (conservative)
        sa = statistics.pstdev(a[::k]) / math.sqrt(len(a[::k])); sb = statistics.pstdev(b[::k]) / math.sqrt(len(b[::k]))
        t = (ma - mb) / math.sqrt(sa*sa + sb*sb)
        out.append(f"{k:>2}d: cond {ma*100:+.2f}% (n={len(a)}) vs rest {mb*100:+.2f}%  diff {(ma-mb)*100:+.2f}pp t={t:+.1f}")
    print(f"  {label}\n     " + '\n     '.join(out))
print('\nFORWARD RETURNS from d0 (predictive pairing: signal at d0, return d0->d0+k; t uses non-overlapping subsamples)')
fwd_table('QQQ | implied backwardation (VIX/VXV>1)', lambda r: r['bw'], ds, px, ix)
fwd_table('SPY | implied backwardation (VIX/VXV>1)', lambda r: r['bw'], sd, spy, six)
fwd_table('QQQ | realized proxy vol10/vol60>1', lambda r: r['rv_bw'], ds, px, ix)
fwd_table('QQQ | high vol (vol_live > expanding median)', lambda r: r['hivol'], ds, px, ix)
print('\n2x2: does the implied slope add to what the vol target already sees?  mean 21d QQQ forward return, mean 5d, hit-rate(21d>0)')
for hv_ in (False, True):
    for bw_ in (False, True):
        sel = [r for r in P if r['hivol'] == hv_ and r['bw'] == bw_]
        a21 = [x for x in (fwd(ds, px, ix, r['d'], 21) for r in sel) if x is not None]
        a5 = [x for x in (fwd(ds, px, ix, r['d'], 5) for r in sel) if x is not None]
        if a21:
            print(f"   hivol={hv_!s:<5} bw={bw_!s:<5} n={len(sel):>4}  21d {statistics.mean(a21)*100:+.2f}%  5d {statistics.mean(a5)*100:+.2f}%  "
                  f"hit {sum(x>0 for x in a21)/len(a21)*100:.0f}%  realized fwd-21d vol {statistics.pstdev(a21)*math.sqrt(252/21)*100:.0f}%")
print('2x2: implied vs realized slope (21d QQQ fwd)')
for rv_ in (False, True):
    for bw_ in (False, True):
        sel = [r for r in P if r['rv_bw'] == rv_ and r['bw'] == bw_]
        a21 = [x for x in (fwd(ds, px, ix, r['d'], 21) for r in sel) if x is not None]
        if a21: print(f"   rv_bw={rv_!s:<5} bw={bw_!s:<5} n={len(sel):>4}  21d {statistics.mean(a21)*100:+.2f}%  hit {sum(x>0 for x in a21)/len(a21)*100:.0f}%")
# by state
print('by effective state: % of days in backwardation, 21d fwd QQQ in bw vs contango')
for s in 'ABCDEF':
    sel = [r for r in P if r['eff'] == s]
    if not sel: continue
    a = [x for x in (fwd(ds, px, ix, r['d'], 21) for r in sel if r['bw']) if x is not None]
    b = [x for x in (fwd(ds, px, ix, r['d'], 21) for r in sel if not r['bw']) if x is not None]
    print(f"   {s}: n={len(sel):>4} bw {len(a)/len(sel)*100:4.1f}%  21d fwd bw {statistics.mean(a)*100 if a else float('nan'):+.2f}%  contango {statistics.mean(b)*100 if b else float('nan'):+.2f}%")

# ================================================================== baseline on P
print('\n' + '='*100 + '\nBASELINE ON THE VXV WINDOW (same rows for everything below)\n' + '='*100)
base = evaluate(P, live_fn); base_exp = run(P, live_fn)[1]; base_ser = run(P, live_fn)[0]; base_nreb = run_counted(P, live_fn)[2]
def fmt(ev): return f"{ev['cagr']*100:5.2f}% / {ev['sharpe']:.3f} / {ev['mdd']*100:5.1f}%  S {ev['s_sharpe']:.3f}  H {ev['h_sharpe']:.3f}"
print(f"LIVE on {len(P)} rows: {fmt(base)}  expo {base_exp*100:.2f}%  rebal/yr {base_nreb/n_yr:.1f}")

def match_k(wfn, target, lo=0.0, hi=1.0):
    """scale wfn's risky legs by k (bisection) until average deployed exposure == target."""
    while run(P, scaled(wfn, hi))[1] < target and hi < 8: lo, hi = hi, hi*2
    for _ in range(50):
        mid = (lo+hi)/2
        if run(P, scaled(wfn, mid))[1] < target: lo = mid
        else: hi = mid
    return (lo+hi)/2
def bisect_param(make, target, lo, hi, increasing=True, n=50):
    """find x with expo(make(x)) == target; increasing: expo rises with x."""
    for _ in range(n):
        mid = (lo+hi)/2; e = run(P, make(mid))[1]
        if (e < target) == increasing: lo = mid
        else: hi = mid
    return (lo+hi)/2

CANDS = []   # (label, ev, expo, matched-live ev, beats_both, series)
def report(label, fn, flip_fn=None, note=''):
    ev = evaluate(P, fn); e = run(P, fn)[1]; ser = run(P, fn)[0]
    k = match_k(live_fn, e); evm = evaluate(P, scaled(live_fn, k))          # current-live scaled to same exposure
    kc, evc = exposure_control(P, e)                                        # mandated control (scales the pre-overlay base)
    both = ev['s_sharpe'] > base['s_sharpe'] and ev['h_sharpe'] > base['h_sharpe']
    bothm = ev['s_sharpe'] > evm['s_sharpe'] and ev['h_sharpe'] > evm['h_sharpe']
    line = (f"{label:<44} {fmt(ev)}  expo {e*100:5.2f}%  | live@k={k:.3f}: {evm['sharpe']:.3f} S {evm['s_sharpe']:.3f} H {evm['h_sharpe']:.3f}"
            f" | exp_ctl {evc['sharpe']:.3f}{'' if evc['exp_matched'] else '(unmatched)'} | d.Sharpe vs matched {ev['sharpe']-evm['sharpe']:+.3f}"
            f"{'  BOTH-vs-live' if both else ''}{'  BOTH-vs-matched' if bothm else ''}{note}")
    print(line)
    if flip_fn is not None:
        evf = evaluate(P, flip_fn); ef = run(P, flip_fn)[1]; kf = match_k(live_fn, ef); evfm = evaluate(P, scaled(live_fn, kf))
        print(f"{'   sign-flip (same rule in contango)':<44} {fmt(evf)}  expo {ef*100:5.2f}%  | live@k={kf:.3f}: {evfm['sharpe']:.3f} | d.Sharpe vs matched {evf['sharpe']-evfm['sharpe']:+.3f}")
    CANDS.append((label, ev, e, evm, both, bothm, ser))
    return ev

# ================================================================== PART A: cash gate
print('\n' + '='*100 + '\nPART A -- CASH GATE: scale the four risky legs by g when VIX/VXV > 1\n' + '='*100)
def gate_on_top(g, flag='bw'):
    def fn(r):
        w = live_fn(r)
        if r[flag]: w = tuple(a*g for a in w[:4]) + (1 - g*sum(w[:4]),)
        return w
    return fn
def gate_on_top_flip(g):
    def fn(r):
        w = live_fn(r)
        if not r['bw']: w = tuple(a*g for a in w[:4]) + (1 - g*sum(w[:4]),)
        return w
    return fn
def gate_instead(g, flag='bw', k=1.0):
    def fn(r):
        w = trimmed(r); m = (g if r[flag] else 1.0) * k
        return tuple(a*m for a in w[:4]) + (1 - m*sum(w[:4]),)
    return fn
def gate_instead_flip(g, k=1.0):
    def fn(r):
        w = trimmed(r); m = (1.0 if r['bw'] else g) * k
        return tuple(a*m for a in w[:4]) + (1 - m*sum(w[:4]),)
    return fn
print('A1. ON TOP of the live vol target')
for g in (0.0, 0.5):
    report(f'gate g={g} on top of vol target', gate_on_top(g), gate_on_top_flip(g))
# confirmation / hysteresis variants (still causal, structural thresholds)
for r in P: pass
prev2 = [False, False]; state_h = False
for i, r in enumerate(P):
    r['bw2'] = r['bw'] and (i > 0 and P[i-1]['bw'])                    # 2-day confirmation
    if r['ratio'] > 1.0: state_h = True
    elif r['ratio'] < 0.95: state_h = False
    r['bwh'] = state_h                                                 # hysteresis exit at 0.95
for flag, lab in (('bw2', '2-day confirmed'), ('bwh', 'hysteresis exit<0.95')):
    report(f'gate g=0.5 on top, {lab}', gate_on_top(0.5, flag))
print('A2. INSTEAD of the vol target (trim only + term-structure gate)')
ev_notarget = evaluate(P, gate_instead(1.0)); e_nt = run(P, gate_instead(1.0))[1]
print(f"{'no vol target, no gate (reference)':<44} {fmt(ev_notarget)}  expo {e_nt*100:5.2f}%")
for g in (0.0, 0.5):
    report(f'gate g={g} instead of vol target (raw)', gate_instead(g), gate_instead_flip(g))
# matched exposure: bisect g in [0,1]; if g=0 still deploys more than live, add global k
e_g0 = run(P, gate_instead(0.0))[1]
if e_g0 > base_exp:
    kk = bisect_param(lambda k: gate_instead(0.0, k=k), base_exp, 0.0, 1.0)
    print(f"   g=0 alone deploys {e_g0*100:.2f}% > live {base_exp*100:.2f}%: gate cannot reach live exposure; global k={kk:.3f} added on top of g=0")
    report('gate g=0 instead, + global k (matched)', gate_instead(0.0, k=kk), gate_instead_flip(0.0, k=bisect_param(lambda k: gate_instead_flip(0.0, k=k), base_exp, 0.0, 1.0)))
    for g in (0.5,):
        kk = bisect_param(lambda k: gate_instead(g, k=k), base_exp, 0.0, 1.0)
        report(f'gate g={g} instead, + global k={kk:.3f} (matched)', gate_instead(g, k=kk))
else:
    gg = bisect_param(lambda g: gate_instead(g), base_exp, 0.0, 1.0)
    report(f'gate g={gg:.3f} instead of vol target (matched)', gate_instead(gg), gate_instead_flip(gg))
# --- instead-of: vol target replaced by a CONTINUOUS slope function at matched exposure
def slope_scaler(T):
    def fn(r):
        w = trimmed(r); m = min(1.0, T / r['ratio'])
        return tuple(a*m for a in w[:4]) + (1 - m*sum(w[:4]),)
    return fn
TT = bisect_param(slope_scaler, base_exp, 0.3, 1.5)
report(f'continuous min(1, {TT:.3f}/ratio) instead of vt', slope_scaler(TT))

# ================================================================== PART B: modulator
print('\n' + '='*100 + '\nPART B -- MODULATOR: m = min(1, T / (vol_live * h)), h>1 in backwardation, T re-calibrated to live exposure\n' + '='*100)
def modulator(h, T, flag='bw', flip=False):
    def fn(r):
        w = trimmed(r); v = r['vol_live'] or r['vol']
        on = (not r[flag]) if flip else r[flag]
        m = min(1.0, T / (v * (h if on else 1.0)))
        return tuple(a*m for a in w[:4]) + (1 - m*sum(w[:4]),)
    return fn
Tchk = bisect_param(lambda T: modulator(1.0, T), base_exp, 0.05, 1.0)
print(f"   calibration check: h=1 recovers T*={Tchk:.4f} (live T=0.20)")
for h in (1.25, 1.5, 2.0):
    T = bisect_param(lambda T: modulator(h, T), base_exp, 0.05, 1.0)
    Tf = bisect_param(lambda T: modulator(h, T, flip=True), base_exp, 0.05, 1.0)
    report(f'modulator h={h} T*={T:.3f}', modulator(h, T), modulator(h, Tf, flip=True))
# continuous modulator: h = ratio itself (vol * ratio), and h = ratio^2
def modulator_cont(T, powr):
    def fn(r):
        w = trimmed(r); v = r['vol_live'] or r['vol']; m = min(1.0, T / (v * max(r['ratio'], 1.0) ** powr))
        return tuple(a*m for a in w[:4]) + (1 - m*sum(w[:4]),)
    return fn
for powr in (1.0, 2.0):
    T = bisect_param(lambda T: modulator_cont(T, powr), base_exp, 0.05, 1.0)
    report(f'modulator h=max(ratio,1)^{powr:.0f} T*={T:.3f}', modulator_cont(T, powr))

# ================================================================== PART C: trigger only
print('\n' + '='*100 + '\nPART C -- REGIME-CHANGE TRIGGER ONLY: entry into backwardation forces a rebalance to the live target\n' + '='*100)
def with_key(keyname):
    return [dict(r, agree=(r['agree'], r[keyname])) for r in P]
def trig_report(label, rows2):
    ev = evaluate(rows2, live_fn); ser, e, nreb = run_counted(rows2, live_fn)
    d = ev['sharpe'] - base['sharpe']
    print(f"{label:<44} {fmt(ev)}  expo {e*100:5.2f}%  rebal/yr {nreb/n_yr:5.1f} (live {base_nreb/n_yr:.1f})  d.Sharpe {d:+.4f}"
          f"{'  BOTH' if ev['s_sharpe']>base['s_sharpe'] and ev['h_sharpe']>base['h_sharpe'] else ''}")
    return ev, ser
print(f"{'live (no extra trigger)':<44} {fmt(base)}  expo {base_exp*100:5.2f}%  rebal/yr {base_nreb/n_yr:5.1f}")
evC, serC = trig_report('trigger: entry INTO backwardation', with_key('ep'))
trig_report('trigger: entry AND exit', with_key('ep_any'))
trig_report('trigger: entry into realized-vol bw (10/60)', with_key('rv_ep'))
# placebo: random events at the same rate, 10 seeds
n_ev = P[-1]['ep']; pl = []
for seed in range(10):
    rng = random.Random(1000 + seed); starts = set(rng.sample(range(len(P)), n_ev)); c = 0; rows2 = []
    for i, r in enumerate(P):
        if i in starts: c += 1
        rows2.append(dict(r, agree=(r['agree'], c)))
    ev = evaluate(rows2, live_fn); pl.append(ev['sharpe'])
print(f"   placebo: {n_ev} random forced rebalances, 10 seeds: Sharpe mean {statistics.mean(pl):.4f} min {min(pl):.4f} max {max(pl):.4f} (live {base['sharpe']:.4f}, slope trigger {evC['sharpe']:.4f})")
CANDS.append(('trigger: entry into backwardation', evC, base_exp, base, evC['s_sharpe']>base['s_sharpe'] and evC['h_sharpe']>base['h_sharpe'],
              evC['s_sharpe']>base['s_sharpe'] and evC['h_sharpe']>base['h_sharpe'], serC))

# ================================================================== PART D: discriminator
print('\n' + '='*100 + '\nPART D -- DISCRIMINATOR: the same rules on the causal realized-vol proxy (vol10/vol60 > 1)\n' + '='*100)
for g in (0.0, 0.5):
    report(f'[realized] gate g={g} on top', gate_on_top(g, 'rv_bw'))
for h in (1.5, 2.0):
    T = bisect_param(lambda T: modulator(h, T, 'rv_bw'), base_exp, 0.05, 1.0)
    report(f'[realized] modulator h={h} T*={T:.3f}', modulator(h, T, 'rv_bw'))
# implied on top of realized: does adding the implied slope to a realized-slope rule change anything?
for r in P: r['both_bw'] = r['bw'] and r['rv_bw']; r['impl_only'] = r['bw'] and not r['rv_bw']; r['real_only'] = r['rv_bw'] and not r['bw']
for flag, lab in (('both_bw', 'implied AND realized bw'), ('impl_only', 'implied bw, realized calm'), ('real_only', 'realized bw, implied calm')):
    report(f'gate g=0.5 on top | {lab}', gate_on_top(0.5, flag))

# ================================================================== survivors
print('\n' + '='*100 + '\nSURVIVOR SCREEN, CANDIDATE COUNT, BOOTSTRAP, LEAVE-ONE-REGIME-OUT, REAL ROWS\n' + '='*100)
print(f"candidates evaluated (excluding placebos/sign-flips/controls): {len(CANDS)}")
surv_live = [c for c in CANDS if c[4]]; surv_m = [c for c in CANDS if c[5]]
print(f"  beat live on BOTH eras (raw, unmatched): {len(surv_live)} -> {[c[0] for c in surv_live]}")
print(f"  beat exposure-MATCHED live on BOTH eras: {len(surv_m)} -> {[c[0] for c in surv_m]}")
REGIMES = [('GFC 2007-12..2009 (window starts 2007-12-04)', '2007-01-01', '2009-12-31'), ('COVID 2020', '2020-01-01', '2020-12-31'),
           ('2022 bear', '2022-01-01', '2022-12-31'), ('whole SPMO era 2015-11+', '2015-11-01', '2099-01-01')]
print("  (dot-com 2000-02 is outside the VXV window and cannot be left out)")
for lab, ev, e, evm, both, bothm, ser in (surv_m or surv_live):
    k = match_k(live_fn, e); bser = run(P, scaled(live_fn, k))[0]
    la, sa = stats(ser); lb, sb = stats(bser)
    print(f"\n  {lab}: vs exposure-matched live (k={k:.3f}), point {(la-lb)*100:+.2f}pp/yr, {sa-sb:+.3f} Sharpe")
    for blk in (20, 60):
        l1, l2, pl_, s1, s2, ps = boot(ser, bser, blk, seed=hash((lab, blk)) & 0xffff)
        print(f"     block {blk:>2}d: logret 95% [{l1*100:+.2f},{l2*100:+.2f}]pp P(<=0)={pl_:.3f} | Sharpe 95% [{s1:+.3f},{s2:+.3f}] P(<=0)={ps:.3f}")
    for rlab, a0, b0 in REGIMES:
        keep = [i for i, r in enumerate(P) if not (a0 <= r['d'] <= b0)]
        sa_ = sharpe_of([ser[i] for i in keep]); sb_ = sharpe_of([bser[i] for i in keep])
        print(f"     leave out {rlab:<44}: cand {sa_:.3f} vs matched live {sb_:.3f}  d {sa_-sb_:+.3f}")

# real weekly rows: attach slope at d0 and confirm the main families
print('\nREAL SPMO WEEKLY ROWS (rr), slope at d0, all variants at matched T where applicable')
for r in rr:
    r['ratio'] = vix[r['d0']] / vxv[r['d0']]; r['bw'] = r['ratio'] > 1
    a = realized_vol(qd, qqq, as_of=r['d0'], lookback=10); b = realized_vol(qd, qqq, as_of=r['d0'], lookback=60)
    r['rv_bw'] = (a / b > 1) if (a and b) else False
print(f"   rr backwardation share {sum(r['bw'] for r in rr)/len(rr)*100:.1f}% of weeks")
def rr_gate(g, flag='bw'):
    def fn(r):
        w = live_rr(r)
        if r[flag]: w = tuple(a*g for a in w[:4]) + (1 - g*sum(w[:4]),)
        return w
    return fn
def rr_mod(h, T, flag='bw'):
    def fn(r):
        w = trimmed(r); m = min(1.0, T / (r['vol_live'] * (h if r[flag] else 1.0)))
        return tuple(a*m for a in w[:4]) + (1 - m*sum(w[:4]),)
    return fn
def rr_exp(fn): return statistics.mean(sum(fn(r)[:4]) for r in rr)
print(f"   {'live':<40} {er0['cagr']*100:5.2f}% / {er0['sharpe']:.3f} / {er0['mdd']*100:5.1f}%  expo {rr_exp(live_rr)*100:.1f}%")
for lab, fn in (('gate g=0 on top', rr_gate(0.0)), ('gate g=0.5 on top', rr_gate(0.5)), ('[realized] gate g=0.5 on top', rr_gate(0.5, 'rv_bw'))):
    e = RF.eval_real(rr, fn); ex = rr_exp(fn)
    # exposure-matched live on rr: scale risky legs by k
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo+hi)/2
        if rr_exp(scaled(live_rr, mid)) < ex: lo = mid
        else: hi = mid
    em = RF.eval_real(rr, scaled(live_rr, (lo+hi)/2))
    print(f"   {lab:<40} {e['cagr']*100:5.2f}% / {e['sharpe']:.3f} / {e['mdd']*100:5.1f}%  expo {ex*100:.1f}%  | matched live {em['sharpe']:.3f}  d {e['sharpe']-em['sharpe']:+.3f}")
for h in (1.5, 2.0):
    lo, hi = 0.05, 1.0; target = rr_exp(live_rr)
    for _ in range(40):
        mid = (lo+hi)/2
        if rr_exp(rr_mod(h, mid)) < target: lo = mid
        else: hi = mid
    T = (lo+hi)/2; e = RF.eval_real(rr, rr_mod(h, T))
    print(f"   {'modulator h=%.2f T*=%.3f' % (h, T):<40} {e['cagr']*100:5.2f}% / {e['sharpe']:.3f} / {e['mdd']*100:5.1f}%  expo {rr_exp(rr_mod(h,T))*100:.1f}%  | live {er0['sharpe']:.3f}  d {e['sharpe']-er0['sharpe']:+.3f}")

# ================================================================== PART E: where does the modulator's edge live?
print('\n' + '='*100 + '\nPART E -- DIAGNOSTICS ON THE ONLY FAMILY THAT PASSED: forward VOL (not return) is what the slope forecasts\n' + '='*100)
def fwd_vol(dates, pxm, ixm, d, k=21):
    i = ixm.get(d)
    if i is None or i + k >= len(dates): return None
    rs = [pxm[dates[j+1]]/pxm[dates[j]]-1 for j in range(i, i+k)]
    return statistics.pstdev(rs) * math.sqrt(252)
print('forward 21d REALIZED vol by cell (mean of per-day forward vols), QQQ and SPY -- the S&P slope applied to a Nasdaq book:')
for hv_ in (False, True):
    for bw_ in (False, True):
        sel = [r for r in P if r['hivol'] == hv_ and r['bw'] == bw_]
        q = [x for x in (fwd_vol(ds, px, ix, r['d']) for r in sel) if x is not None]
        sp = [x for x in (fwd_vol(sd, spy, six, r['d']) for r in sel) if x is not None]
        cur = statistics.mean(r['vol_live'] for r in sel)
        print(f"   hivol={hv_!s:<5} bw={bw_!s:<5} n={len(sel):>4}  current vol_live {cur*100:4.1f}%  fwd21 QQQ {statistics.mean(q)*100:4.1f}%  fwd21 SPY {statistics.mean(sp)*100:4.1f}%"
              f"  ratio fwd/current QQQ {statistics.mean(q)/cur:.2f}")
# same, realized proxy cells: does the realized 10/60 slope forecast forward vol beyond level?
print('   realized-proxy cells:')
for hv_ in (False, True):
    for rv_ in (False, True):
        sel = [r for r in P if r['hivol'] == hv_ and r['rv_bw'] == rv_]
        q = [x for x in (fwd_vol(ds, px, ix, r['d']) for r in sel) if x is not None]; cur = statistics.mean(r['vol_live'] for r in sel)
        print(f"   hivol={hv_!s:<5} rv_bw={rv_!s:<5} n={len(sel):>4}  current vol_live {cur*100:4.1f}%  fwd21 QQQ {statistics.mean(q)*100:4.1f}%  ratio fwd/current {statistics.mean(q)/cur:.2f}")
# year-by-year and turnover for the h=1.5 modulator vs live
T15 = bisect_param(lambda T: modulator(1.5, T), base_exp, 0.05, 1.0); fn15 = modulator(1.5, T15)
def by_year(fn):
    rets, _ = run(P, fn); by = {}
    for r, x in zip(P, rets): by[r['d'][:4]] = by.get(r['d'][:4], 0) + math.log1p(x)
    return by
b1, b0 = by_year(fn15), by_year(live_fn)
print(f"\nmodulator h=1.5 T*={T15:.3f} minus live, log-return by year (pp):")
print('   ' + '  '.join(f"{y[2:]}:{(b1[y]-b0[y])*100:+.1f}" for y in sorted(b1)))
print(f"   sum {(sum(b1.values())-sum(b0.values()))*100:+.2f}pp over {len(b1)} yrs; years better {sum(b1[y]>b0[y] for y in b1)} / worse {sum(b1[y]<b0[y] for y in b1)}")
_, _, n15 = run_counted(P, fn15); print(f"   rebalances/yr: modulator {n15/n_yr:.1f} vs live {base_nreb/n_yr:.1f}")
# how much does the modulator actually move the book? distribution of (m_mod / m_live) on backwardation days
ratio_m = []
for r in P:
    if r['bw']:
        a = sum(fn15(r)[:4]); b = sum(live_fn(r)[:4]); 
        if b > 0: ratio_m.append(a/b)
ratio_m.sort(); print(f"   on backwardation days, risky exposure mod/live: median {ratio_m[len(ratio_m)//2]:.2f} p10 {ratio_m[len(ratio_m)//10]:.2f} p90 {ratio_m[9*len(ratio_m)//10]:.2f};"
      f" share of bw days where live is already capped by vt (m<1): {sum(1 for r in P if r['bw'] and (r['vol_live'] or 0) > 0.20)/nb:.2f}")
# threshold sensitivity (counted as candidates): ratio > 0.95 / 1.05 in place of 1.0, h=1.5
print('\nthreshold sensitivity, modulator h=1.5 (structural line is 1.0; these are counted as candidates):')
for thr in (0.95, 1.05):
    for r in P: r['bw_t'] = r['ratio'] > thr
    T = bisect_param(lambda T: modulator(1.5, T, 'bw_t'), base_exp, 0.05, 1.0)
    report(f'modulator h=1.5 thr={thr} T*={T:.3f} ({sum(r["bw_t"] for r in P)/len(P)*100:.0f}% days)', modulator(1.5, T, 'bw_t'))
print(f"candidate count including sensitivity: {len(CANDS)}")

# rr confirmation for the remaining survivors
print('\nREAL ROWS, remaining survivors:')
for r in rr: r['both_bw'] = r['bw'] and r['rv_bw']
for lab, fn in (('gate g=0.5 on top | implied AND realized', rr_gate(0.5, 'both_bw')),):
    e = RF.eval_real(rr, fn); ex = rr_exp(fn); lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo+hi)/2
        if rr_exp(scaled(live_rr, mid)) < ex: lo = mid
        else: hi = mid
    em = RF.eval_real(rr, scaled(live_rr, (lo+hi)/2))
    print(f"   {lab:<40} {e['cagr']*100:5.2f}% / {e['sharpe']:.3f} / {e['mdd']*100:5.1f}%  expo {ex*100:.1f}%  | matched live {em['sharpe']:.3f}  d {e['sharpe']-em['sharpe']:+.3f}"
          f"   (weeks in cell: {sum(r['both_bw'] for r in rr)})")
lo, hi = 0.05, 1.0; target = rr_exp(live_rr)
for _ in range(40):
    mid = (lo+hi)/2
    if rr_exp(rr_mod(1.25, mid)) < target: lo = mid
    else: hi = mid
T = (lo+hi)/2; e = RF.eval_real(rr, rr_mod(1.25, T))
print(f"   {'modulator h=1.25 T*=%.3f' % T:<40} {e['cagr']*100:5.2f}% / {e['sharpe']:.3f} / {e['mdd']*100:5.1f}%  expo {rr_exp(rr_mod(1.25,T))*100:.1f}%  | live {er0['sharpe']:.3f}  d {e['sharpe']-er0['sharpe']:+.3f}")

print('\nDone.')
