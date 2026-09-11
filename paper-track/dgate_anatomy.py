"""Research line dgate_anatomy (2026-09-11): anatomy of the post-hoc D-row breadth gate.

Rule under study (from breadth_signal / breadth_dgate_2000, NOT applied): effective state D AND the 60-day change of
log(QQEW/QQQ) in its trailing-252 bottom quintile (pct < 0.20) -> the D row (100% QLD) goes to cash.

This line does not sweep the rule again.  It asks what the rule is made of:
  1. episode anatomy (every gated run, its contribution, what the state did next, concentration by episode / year)
  2. transition mechanism: on ALL D days, is bottom-quintile breadth a breakdown predictor (next state E/F) or a
     general negative-return signal?  Same grid for A days and all days; episode-level permutation test.
  3. why D and not A: forward returns AND the live design's own exposure by breadth bucket, and how much of the
     D-vs-A asymmetry each explains
  4. robustness not yet run: execution lag, cost, EPISODE-block bootstrap, rolling 3y windows, a continuous
     (smooth) version, and alternate breadth definitions with the same mechanism (consistency check, not a search)
  5. the honest holdout: the D episodes of 2007-07..2015-10, which were gated, what each contributed; a strict
     two-way split with the episode-bootstrap CI
  6. today's reading for the live-tracking spec (the spec itself is in the note)

Research only.  Nothing is applied.  Harness: the project harness only (leverage_under_trim bootstrap -> rows, rr,
run, evaluate, RF.eval_real; block_bootstrap.boot/stats).  The data loading, row attachment, 60-day log-ratio change,
trailing-252 percentile, D-gate weight function and constant-D control are NOT re-implemented: the corresponding
sections of paper-track/breadth_dgate_2000.py (sections 0-3) are exec'd from that file verbatim, so the objects used
here are the same code the earlier lines used.  Run from the repo root:
    python3 paper-track/dgate_anatomy.py        (~4-6 min; DGATE_ANAT_FAST=1 cuts bootstrap draws to 200)
"""
import sys, os, math, csv, bisect, zlib, random
sys.path.insert(0, 'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from state import extension_scale, extension_votes, EXTENSION_STEP
from block_bootstrap import boot, stats, N_BOOT
from improvement_search import SEARCH, HOLDOUT, era
import improvement_search as IS
from long_history_backtest import load_px as _load_px
NB = 200 if os.environ.get('DGATE_ANAT_FAST') else 2000

print("=" * 112)
print("RESEARCH LINE dgate_anatomy -- what the D-row breadth gate is made of (no re-sweep)")
print("=" * 112)

# ---- reuse: sections 0..3 of breadth_dgate_2000.py, exec'd verbatim (standing-figure assert, data, ratio series,
#      diffs, trailing_pct, attach, trimmed/scale_risky/gate_fn/const_D/calib_q/exposure_control_live/sub_rows, dgate_block)
_SRC = open('paper-track/breadth_dgate_2000.py').read()
_A = _SRC.index('# ------------------------------------------------------------------ 0. live design')
_B = _SRC.index('# ------------------------------------------------------------------ 4. VALIDATION')
exec(_SRC[_A:_B])
print(f"\n(reused breadth_dgate_2000.py sections 0-3 verbatim: {_SRC[_A:_B].count(chr(10))} lines)")

# ---- extra series built with the SAME primitives (minus_sma copied verbatim from breadth_signal.py)
def minus_sma(lr, n):
    out = [None] * len(lr); win = []
    for i, x in enumerate(lr):
        if x is None: win = []; continue
        win.append(x)
        if len(win) > n: win.pop(0)
        if len(win) == n: out[i] = x - sum(win) / n
    return out
def trailing_z(v, n=252):
    """trailing-n z-score of v (inclusive of today): (x - mean)/sd; None until n values."""
    out = [None] * len(v); hist = []
    for i, x in enumerate(v):
        if x is None: hist = []; continue
        hist.append(x)
        if len(hist) > n: hist.pop(0)
        if len(hist) == n:
            m = sum(hist) / n; sd_ = (sum((y - m) ** 2 for y in hist) / (n - 1)) ** 0.5
            out[i] = (x - m) / sd_ if sd_ > 0 else 0.0
    return out
series['qqew_s200'] = minus_sma(LR['qqew'], 200); pct['qqew_s200'] = trailing_pct(series['qqew_s200'])
series['qqew_avg2060'] = [None if (a is None or b is None) else 0.5 * (a + b) for a, b in zip(series['qqew_20'], series['qqew_60'])]
pct['qqew_avg2060'] = trailing_pct(series['qqew_avg2060'])
# cap-weight minus equal-weight 60d return = -(qqew_60); z-scored on the trailing 252; 'weak breadth' = z > +0.8416
# (the normal-quantile analogue of a bottom quintile).  Stored as a pseudo-percentile 1 - Phi(z) so that '< 0.20' fires it.
def _phi(z): return 0.5 * (1 + math.erf(z / math.sqrt(2)))
_z = trailing_z([None if x is None else -x for x in series['qqew_60']])
series['cwz60'] = _z; pct['cwz60'] = [None if z is None else 1 - _phi(z) for z in _z]
for nm in ('qqew_s200', 'qqew_avg2060', 'cwz60'):
    NAMES.append(nm)
    for r in rows: r['bp'][nm] = pct[nm][cix[r['d']]]; r['bv'][nm] = series[nm][cix[r['d']]]
    for r in rr:
        d = r['d0'] if r['d0'] in cix else cal[bisect.bisect_right(cal, r['d0']) - 1]
        r['bp'][nm] = pct[nm][cix[d]]; r['bv'][nm] = series[nm][cix[d]]

# ---- the reference rows and the reference figures
K = 'qqew_60'
_IDX = {id(r_): i for i, r_ in enumerate(rows)}
RQ = sub_rows(K); RQ_I0 = _IDX[id(RQ[0])]
GATE = gate_fn(K, 1.0); EVG = evaluate(RQ, GATE); BL_EV = evaluate(RQ, LIVE)
Q = calib_q(RQ, EVG['risky']); CD = const_D(Q); EVC = evaluate(RQ, CD)
A_G = run(RQ, GATE)[0]; A_L = run(RQ, LIVE)[0]; A_C = run(RQ, CD)[0]
print(f"\nREFERENCE on the {len(RQ)} QQEW rows {RQ[0]['d']}..{RQ[-1]['d']} (must match the earlier notes):")
print(f"  live   {fmt(BL_EV)} S {BL_EV['s_sharpe']:.3f} H {BL_EV['h_sharpe']:.3f} exp {BL_EV['risky']*100:.1f}%   (note: 26.09/1.006/-33.6 S 1.103 H 0.876)")
print(f"  gated  {fmt(EVG)} S {EVG['s_sharpe']:.3f} H {EVG['h_sharpe']:.3f} exp {EVG['risky']*100:.1f}%   (note: 31.71/1.218/-28.5 S 1.332 H 1.065)")
print(f"  const-D q={Q:.3f} {fmt(EVC)} S {EVC['s_sharpe']:.3f} H {EVC['h_sharpe']:.3f} exp {EVC['risky']*100:.1f}%")
assert abs(EVG['sharpe'] - 1.218) < 0.002 and abs(EVG['s_sharpe'] - 1.332) < 0.002 and abs(EVG['h_sharpe'] - 1.065) < 0.002, "reference D-gate figures not reproduced"
assert abs(BL_EV['sharpe'] - 1.006) < 0.002 and abs(BL_EV['h_sharpe'] - 0.876) < 0.002, "same-rows live figures not reproduced"

# ---- helpers: forward QQQ outcomes on the repo QQQ calendar (px/ds from the harness), episodes, transitions
pv = [px[d] for d in ds]; pix = {d: i for i, d in enumerate(ds)}
def fwd(r, n):
    j = pix[r['d']]
    return pv[j + n] / pv[j] - 1 if j + n < len(pv) else None
def fvol(r, n=20):
    j = pix[r['d']]
    if j + n >= len(pv): return None
    lr_ = [math.log(pv[j + k + 1] / pv[j + k]) for k in range(n)]; m = mean(lr_)
    return (sum((x - m) ** 2 for x in lr_) / (n - 1)) ** 0.5 * math.sqrt(252)
def median(a):
    s = sorted(a); n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])
def sd(a):
    m = mean(a); return (sum((x - m) ** 2 for x in a) / (len(a) - 1)) ** 0.5
def sharpe_of(rets):
    return stats(rets)[1]
def bucket(p): return min(4, int(p * 5))
BUCK = ['0.0-0.2', '0.2-0.4', '0.4-0.6', '0.6-0.8', '0.8-1.0']
ORDER = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5}

# episodes of a given effective state over the FULL rows (so exits at the RQ start are known), indexed into rows
def episodes(state, rs=rows):
    eps = []; cur = None
    for i, r in enumerate(rs):
        if r['eff'] == state:
            if cur is None: cur = [i, i]
            cur[1] = i
        elif cur: eps.append(tuple(cur)); cur = None
    if cur: eps.append(tuple(cur))
    return eps
EP_D = [e for e in episodes('D') if e[1] >= RQ_I0]          # D episodes touching the QQEW rows
EP_A = [e for e in episodes('A') if e[1] >= RQ_I0]
def exit_state(ep):
    j = ep[1] + 1
    return rows[j]['eff'] if j < len(rows) else None
def ep_of(i, eps):
    for e in eps:
        if e[0] <= i <= e[1]: return e
    return None
def gated(r): return r['eff'] == 'D' and r['bp'][K] is not None and r['bp'][K] < 0.2
def first_reach(i, states, horizon=60):
    """sessions after row i until eff is in `states` (None if not within horizon)."""
    for k in range(1, horizon + 1):
        if i + k >= len(rows): return None
        if rows[i + k]['eff'] in states: return k
    return None
def ann_log(a): return sum(math.log1p(x) for x in a)

# gated runs (contiguous gated days) on the QQEW rows
RUNS = []; cur = None
for i in range(RQ_I0, len(rows)):
    if gated(rows[i]):
        if cur is None: cur = [i, i]
        cur[1] = i
    elif cur: RUNS.append(tuple(cur)); cur = None
if cur: RUNS.append(tuple(cur))
def ri(i): return i - RQ_I0    # index into RQ / A_G / A_L / A_C

# =====================================================================================================================
print("\n" + "=" * 112)
print("1. EPISODE ANATOMY -- every gated run on the QQEW rows")
print("=" * 112)
print("contrib = sum over the run's days of log(1+gate) - log(1+live) in pp (the realized gain incl. vol-target scaling);")
print("QLD-leg = sum of log(1+QLD leg) over the run (what a 100% QLD holder would have made); QQQ = same for QQQ.")
print("exit = the effective state the parent D episode went to; to-exit = sessions from the run's END to that change;")
print("A<=60 / EF<=60 = sessions from the run's end until eff first reaches A / E-or-F (within 60), '-' = not reached.")
rows_out = []
for (s, e) in RUNS:
    days = list(range(s, e + 1)); pe = ep_of(s, EP_D)
    contrib = sum(math.log1p(A_G[ri(i)]) - math.log1p(A_L[ri(i)]) for i in days) * 100
    qld = sum(math.log1p(rows[i]['legs'][2]) for i in days) * 100
    qqq_ret = sum(math.log1p(rows[i]['qqq']) for i in days) * 100
    ex = exit_state(pe); to_exit = (pe[1] + 1 - e) if ex else None
    rows_out.append(dict(s=rows[s]['d'], e=rows[e]['d'], n=len(days), qqq=qqq_ret, qld=qld, c=contrib, ex=ex, tx=to_exit,
                         a60=first_reach(e, ('A',)), ef60=first_reach(e, ('E', 'F')), pe=pe, live=sum(math.log1p(A_L[ri(i)]) for i in days) * 100,
                         pep=f"{rows[pe[0]]['d']}..{rows[pe[1]]['d']} ({pe[1]-pe[0]+1}d)"))
TOT = sum(x['c'] for x in rows_out); TOTQ = sum(x['qld'] for x in rows_out); TOTL = sum(x['live'] for x in rows_out)
full_diff = (ann_log(A_G) - ann_log(A_L)) * 100
print(f"\n{len(RUNS)} gated runs, {sum(x['n'] for x in rows_out)} days, inside {len(set(x['pe'] for x in rows_out))} distinct D episodes "
      f"(of {len(EP_D)} D episodes on these rows).  Sum of run contributions {TOT:+.1f}pp; total gate-live log difference over all rows "
      f"{full_diff:+.1f}pp (residual {full_diff-TOT:+.1f}pp is path/rebalance effects outside the runs).  Live return summed over gated days {TOTL:+.1f}pp; QLD-leg summed {TOTQ:+.1f}pp.")
print(f"\n  {'#':>3} {'start':<11}{'end':<11}{'n':>3}{'QQQ%':>7}{'QLD%':>7}{'live%':>7}{'contrib':>8}{'cum%':>6} {'exit':>4}{'to-exit':>8}{'A<=60':>6}{'EF<=60':>7}  parent D episode")
ranked = sorted(rows_out, key=lambda x: -x['c']); cum = 0.0
for k, x in enumerate(ranked, 1):
    cum += x['c']
    print(f"  {k:>3} {x['s']:<11}{x['e']:<11}{x['n']:>3}{x['qqq']:>+7.1f}{x['qld']:>+7.1f}{x['live']:>+7.1f}{x['c']:>+8.1f}{cum/TOT*100:>6.0f} {x['ex'] or '-':>4}"
          f"{x['tx'] if x['tx'] is not None else '-':>8}{x['a60'] if x['a60'] else '-':>6}{x['ef60'] if x['ef60'] else '-':>7}  {x['pep']}")
top8 = ranked[:8]; c8 = sum(x['c'] for x in top8)
print(f"\n  top 8 runs carry {c8:+.1f} of {TOT:+.1f}pp = {c8/TOT*100:.0f}%: " + ", ".join(f"{x['s']}({x['n']}d {x['c']:+.1f})" for x in top8))
neg = [x for x in ranked if x['c'] < 0]
print(f"  runs with NEGATIVE contribution (the gate cost money): {len(neg)} of {len(ranked)}, summing {sum(x['c'] for x in neg):+.1f}pp; "
      f"positive runs {len(ranked)-len(neg)} summing {sum(x['c'] for x in ranked if x['c']>=0):+.1f}pp")
# what happened next, aggregated
ex_ct = {}
for x in rows_out: ex_ct[x['ex'] or 'none'] = ex_ct.get(x['ex'] or 'none', 0) + 1
print(f"  exit state of the parent D episode, by run: {ex_ct}; runs where eff reached E/F within 60 sessions of the run end: "
      f"{sum(1 for x in rows_out if x['ef60'])}; reached A within 60: {sum(1 for x in rows_out if x['a60'])}; "
      f"neither within 60: {sum(1 for x in rows_out if not x['a60'] and not x['ef60'])}")
print(f"  contribution from runs whose parent D episode exited to E/F: {sum(x['c'] for x in rows_out if x['ex'] in ('E','F')):+.1f}pp; "
      f"to A/B/C: {sum(x['c'] for x in rows_out if x['ex'] in ('A','B','C')):+.1f}pp")
print("\n  BY YEAR (year of the run's start): runs, days, contribution pp, share of total, QLD-leg pp")
by = {}
for x in rows_out:
    y = x['s'][:4]; b = by.setdefault(y, [0, 0, 0.0, 0.0]); b[0] += 1; b[1] += x['n']; b[2] += x['c']; b[3] += x['qld']
for y in sorted(by):
    b = by[y]; print(f"    {y}  runs {b[0]:>2}  days {b[1]:>3}  contrib {b[2]:>+6.1f}pp  share {b[2]/TOT*100:>5.1f}%  QLD-leg {b[3]:>+6.1f}pp")
for y in ('2008', '2020', '2022'):
    b = by.get(y, [0, 0, 0.0, 0.0]); print(f"  share of the gain from {y}: {b[2]/TOT*100:.1f}%  ({b[2]:+.1f}pp of {TOT:+.1f})")
print(f"  share from 2008+2020+2022 together: {sum(by.get(y,[0,0,0.0])[2] for y in ('2008','2020','2022'))/TOT*100:.1f}%;"
      f" from the SPMO era 2015-11+: {sum(x['c'] for x in rows_out if x['s'] >= '2015-11-01')/TOT*100:.1f}%; holdout 2007-07..2015-10: {sum(x['c'] for x in rows_out if x['s'] < '2015-11-01')/TOT*100:.1f}%")

# =====================================================================================================================
print("\n" + "=" * 112)
print("2. TRANSITION MECHANISM -- forward outcome by breadth bucket on ALL state-D days, on A days, on all days")
print("=" * 112)
print("P(E/F) = share of days whose parent episode's NEXT effective state is E or F (breakdown below the 200d);")
print("P(A/B) = next state A or B (recovery above the 50d); to-chg = mean sessions until the state changes;")
print("fwd5/10/20 = mean forward QQQ return (%), med20 = median 20d, vol20 = mean forward 20-session realized vol (ann. %),")
print("d1 = mean next-day QQQ return (bp).  'all days': next state relative to the current one, down = higher letter.")
def grid(scope_rows, eps, label, extra_down=None):
    print(f"\n  [{label}]  n={len(scope_rows)}")
    hdr = f"  {'bucket':<8}{'n':>5}{'eps':>5}{'P(E/F)':>8}{'P(A/B)':>8}{'P(to D)':>8}{'P(down)':>8}{'to-chg':>7}{'d1 bp':>7}{'fwd5':>7}{'fwd10':>7}{'fwd20':>7}{'med20':>7}{'vol20':>7}"
    print(hdr); out = {}
    for b in range(5):
        sub = [r for r in scope_rows if bucket(r['bp'][K]) == b]
        if not sub: print(f"  {BUCK[b]:<8}{0:>5}"); continue
        idx = [_IDX[id(r)] for r in sub]; pes = [ep_of(i, eps) for i in idx]
        exs = [exit_state(p) for p in pes]; ok = [(x, p, i) for x, p, i in zip(exs, pes, idx) if x is not None]
        pef = mean([1.0 if x in ('E', 'F') else 0.0 for x, _, _ in ok]) if ok else float('nan')
        pab = mean([1.0 if x in ('A', 'B') else 0.0 for x, _, _ in ok]) if ok else float('nan')
        pdn = mean([1.0 if ORDER[x] > ORDER[rows[i]['eff']] else 0.0 for x, _, i in ok]) if ok else float('nan')
        ptd = mean([1.0 if x == 'D' else 0.0 for x, _, _ in ok]) if ok else float('nan')
        tch = mean([p[1] + 1 - i for _, p, i in ok]) if ok else float('nan')
        f5 = [fwd(r, 5) for r in sub]; f10 = [fwd(r, 10) for r in sub]; f20 = [fwd(r, 20) for r in sub]; v20 = [fvol(r) for r in sub]
        f5 = [x for x in f5 if x is not None]; f10 = [x for x in f10 if x is not None]; f20 = [x for x in f20 if x is not None]; v20 = [x for x in v20 if x is not None]
        out[b] = dict(n=len(sub), pef=pef, pab=pab, f20=f20, v20=v20, d1=[r['qqq'] for r in sub], eps=len(set(pes)))
        print(f"  {BUCK[b]:<8}{len(sub):>5}{len(set(pes)):>5}{pef:>8.2f}{pab:>8.2f}{ptd:>8.2f}{pdn:>8.2f}{tch:>7.1f}{mean([r['qqq'] for r in sub])*1e4:>7.1f}"
              f"{mean(f5)*100:>7.2f}{mean(f10)*100:>7.2f}{mean(f20)*100:>7.2f}{median(f20)*100:>7.2f}{mean(v20)*100:>7.1f}")
    return out
D_ROWS = [r for r in RQ if r['eff'] == 'D']; A_ROWS = [r for r in RQ if r['eff'] == 'A']
EP_ALL = {}
for st in 'ABCDEF': EP_ALL[st] = episodes(st)
def eps_any(i):
    return ep_of(i, EP_ALL[rows[i]['eff']])
GD = grid(D_ROWS, EP_D, 'state D days')
GA = grid(A_ROWS, EP_A, 'state A days')
# all days: need the parent episode of whatever state the day is in
print(f"\n  [all days]  n={len(RQ)}")
print(f"  {'bucket':<8}{'n':>5}{'P(E/F)':>8}{'P(A/B)':>8}{'P(down)':>8}{'to-chg':>7}{'d1 bp':>7}{'fwd5':>7}{'fwd10':>7}{'fwd20':>7}{'med20':>7}{'vol20':>7}")
GALL = {}
for b in range(5):
    sub = [r for r in RQ if bucket(r['bp'][K]) == b]; idx = [_IDX[id(r)] for r in sub]
    pes = [eps_any(i) for i in idx]; exs = [exit_state(p) for p in pes]; ok = [(x, p, i) for x, p, i in zip(exs, pes, idx) if x is not None]
    pef = mean([1.0 if x in ('E', 'F') else 0.0 for x, _, _ in ok]); pab = mean([1.0 if x in ('A', 'B') else 0.0 for x, _, _ in ok])
    pdn = mean([1.0 if ORDER[x] > ORDER[rows[i]['eff']] else 0.0 for x, _, i in ok]); tch = mean([p[1] + 1 - i for _, p, i in ok])
    f5 = [x for x in (fwd(r, 5) for r in sub) if x is not None]; f10 = [x for x in (fwd(r, 10) for r in sub) if x is not None]
    f20 = [x for x in (fwd(r, 20) for r in sub) if x is not None]; v20 = [x for x in (fvol(r) for r in sub) if x is not None]
    GALL[b] = dict(f20=f20, v20=v20, d1=[r['qqq'] for r in sub], pdn=pdn)
    print(f"  {BUCK[b]:<8}{len(sub):>5}{pef:>8.2f}{pab:>8.2f}{pdn:>8.2f}{tch:>7.1f}{mean([r['qqq'] for r in sub])*1e4:>7.1f}"
          f"{mean(f5)*100:>7.2f}{mean(f10)*100:>7.2f}{mean(f20)*100:>7.2f}{median(f20)*100:>7.2f}{mean(v20)*100:>7.1f}")

# D days by era, bottom quintile vs rest
print("\n  D days, bottom quintile vs the other four, by era:")
print(f"  {'era':<9}{'scope':<8}{'n':>5}{'eps':>5}{'P(E/F)':>8}{'P(A/B)':>8}{'d1 bp':>7}{'fwd20':>7}{'vol20':>7}{'QLD d1 bp':>10}")
for lab, lo, hi in (('full', '0000', '9999'), ('holdout', '0000', SEARCH[0]), ('search', SEARCH[0], '9999')):
    for sc, cond in (('pct<0.2', lambda r: r['bp'][K] < 0.2), ('pct>=0.2', lambda r: r['bp'][K] >= 0.2)):
        sub = [r for r in D_ROWS if lo <= r['d'] < hi and cond(r)]; idx = [_IDX[id(r)] for r in sub]; pes = [ep_of(i, EP_D) for i in idx]
        ok = [exit_state(p) for p in pes if exit_state(p)]
        f20 = [x for x in (fwd(r, 20) for r in sub) if x is not None]; v20 = [x for x in (fvol(r) for r in sub) if x is not None]
        print(f"  {lab:<9}{sc:<8}{len(sub):>5}{len(set(pes)):>5}{mean([1.0 if x in ('E','F') else 0.0 for x in ok]):>8.2f}{mean([1.0 if x in ('A','B') else 0.0 for x in ok]):>8.2f}"
              f"{mean([r['qqq'] for r in sub])*1e4:>7.1f}{mean(f20)*100:>7.2f}{mean(v20)*100:>7.1f}{mean([r['legs'][2] for r in sub])*1e4:>10.1f}")

# ---- permutation tests
print("\n  PERMUTATION TESTS (the unit of independence is the D EPISODE, not the day):")
d_idx = [_IDX[id(r)] for r in D_ROWS]; d_pe = [ep_of(i, EP_D) for i in d_idx]
eps_list = sorted(set(d_pe)); eps_with_exit = [e for e in eps_list if exit_state(e)]
ex_map = {e: exit_state(e) for e in eps_with_exit}
def T_day(exmap):
    g = [1.0 if exmap[p] in ('E', 'F') else 0.0 for r, p in zip(D_ROWS, d_pe) if p in exmap and r['bp'][K] < 0.2]
    o = [1.0 if exmap[p] in ('E', 'F') else 0.0 for r, p in zip(D_ROWS, d_pe) if p in exmap and r['bp'][K] >= 0.2]
    return mean(g) - mean(o)
ep_gated = {e: any(gated(rows[i]) for i in range(e[0], e[1] + 1)) for e in eps_with_exit}
ep_minpct = {e: min(rows[i]['bp'][K] for i in range(e[0], e[1] + 1)) for e in eps_with_exit}
def T_ep(exmap):
    g = [1.0 if exmap[e] in ('E', 'F') else 0.0 for e in eps_with_exit if ep_gated[e]]
    o = [1.0 if exmap[e] in ('E', 'F') else 0.0 for e in eps_with_exit if not ep_gated[e]]
    return mean(g) - mean(o)
rng = random.Random(11); vals = list(ex_map.values()); Td, Te = T_day(ex_map), T_ep(ex_map); cd = ce = 0
for _ in range(NB):
    rng.shuffle(vals); pm = dict(zip(eps_with_exit, vals))
    if T_day(pm) >= Td: cd += 1
    if T_ep(pm) >= Te: ce += 1
ng = sum(1 for e in eps_with_exit if ep_gated[e])
print(f"  (a) day-weighted: P(E/F | D day, pct<0.2) - P(E/F | D day, pct>=0.2) = {Td:+.3f}; null = exit outcomes permuted across the "
      f"{len(eps_with_exit)} D episodes ({NB} perms): P(T_null >= T) = {cd/NB:.3f}")
print(f"  (b) episode level: P(E/F | episode had >=1 gated day, n={ng}) - P(E/F | never gated, n={len(eps_with_exit)-ng}) = {Te:+.3f}; same null: P = {ce/NB:.3f}")
# forward-return version: circular shift of the gate pattern within D days (preserves run lengths), fwd20 and next-day QLD
pat = [r['bp'][K] < 0.2 for r in D_ROWS]; f20d = [fwd(r, 20) for r in D_ROWS]; q1 = [r['legs'][2] for r in D_ROWS]
def T_ret(flags, vals_):
    g = [v for f, v in zip(flags, vals_) if f and v is not None]; o = [v for f, v in zip(flags, vals_) if not f and v is not None]
    return mean(g) - mean(o)
rng = random.Random(12); T20 = T_ret(pat, f20d); T1 = T_ret(pat, q1); c20 = c1 = 0
for _ in range(NB):
    off = rng.randrange(1, len(pat)); sh = pat[-off:] + pat[:-off]
    if T_ret(sh, f20d) <= T20: c20 += 1
    if T_ret(sh, q1) <= T1: c1 += 1
print(f"  (c) forward 20d QQQ return, gated D days minus other D days = {T20*100:+.2f}pp; null = the gate's on/off pattern circularly shifted"
      f" within D days ({NB} shifts): P(null <= actual) = {c20/NB:.3f}")
print(f"  (d) next-day QLD leg, gated minus other D days = {T1*1e4:+.1f}bp; same null: P = {c1/NB:.3f}")

# ---- 2b. the obvious confound: within D, is bottom-quintile breadth just "price already near the 200d"?
print("\n  2b. CONFOUND CHECK: within D, does the gate just pick the days when price is already close to the 200d (gap200 small),")
print("      which would predict the E transition mechanically?  gap200/gap50 = close/SMA-1 (%); pos = sessions since the D episode began.")
print(f"  {'scope':<20}{'n':>5}{'gap200%':>9}{'gap50%':>8}{'vol30%':>8}{'pos':>6}{'P(E/F)':>8}{'QLD d1 bp':>10}")
def dstat(sub, lab):
    idx = [_IDX[id(r)] for r in sub]; pes = [ep_of(i, EP_D) for i in idx]; ok = [exit_state(p) for p in pes if exit_state(p)]
    print(f"  {lab:<20}{len(sub):>5}{mean([r['gaps'][200] for r in sub])*100:>9.2f}{mean([r['gap50'] for r in sub])*100:>8.2f}{mean([r['vol'] for r in sub])*100:>8.1f}"
          f"{mean([i - p[0] for i, p in zip(idx, pes)]):>6.1f}{mean([1.0 if x in ('E','F') else 0.0 for x in ok]):>8.2f}{mean([r['legs'][2] for r in sub])*1e4:>10.1f}")
dstat([r for r in D_ROWS if r['bp'][K] < 0.2], 'gated'); dstat([r for r in D_ROWS if r['bp'][K] >= 0.2], 'other D')
g200 = sorted(r['gaps'][200] for r in D_ROWS); med200 = g200[len(g200) // 2]
print(f"  2x2 split at the D-day median gap200 = {med200*100:.2f}%:")
for glab, gc in (('gap200<med', lambda r: r['gaps'][200] < med200), ('gap200>=med', lambda r: r['gaps'][200] >= med200)):
    for blab, bc_ in (('gated', lambda r: r['bp'][K] < 0.2), ('other', lambda r: r['bp'][K] >= 0.2)):
        sub = [r for r in D_ROWS if gc(r) and bc_(r)]
        if sub: dstat(sub, f'{glab} {blab}')
print("  placebo gates on the same D rows using the distance to the 200d instead of breadth (D row to cash when gap200 < g; each a candidate):")
print(f"  {'rule':<22}{'on':>4}{'gated bp':>9}{'other bp':>9}{'| CAGR/Sh/MDD':>24}{'S':>7}{'H':>7}{'| vs live S/H':>15}{'| vs constD S/H':>16}")
NC_GAP = 0
for g in (0.02, 0.03, 0.05):
    NC_GAP += 1
    def gfn(r, g=g, vtf=vt):
        w = trimmed(r['eff'], r['gaps'])
        if r['eff'] == 'D' and r['gaps'][200] < g: w = scale_risky(w, 0.0)
        return vtf(w, r['vol'])
    ev = evaluate(RQ, gfn); q_ = calib_q(RQ, ev['risky']); ce_ = evaluate(RQ, const_D(q_))
    on = [r for r in D_ROWS if r['gaps'][200] < g]; off = [r for r in D_ROWS if r['gaps'][200] >= g]
    print(f"  {'gap200 < ' + f'{g*100:.0f}%':<22}{len(on):>4}{mean([r['legs'][2] for r in on])*1e4:>9.1f}{mean([r['legs'][2] for r in off])*1e4:>9.1f}{fmt(ev):>24}{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f}"
          f"{ev['s_sharpe']-BL_EV['s_sharpe']:>+8.3f}/{ev['h_sharpe']-BL_EV['h_sharpe']:+.3f}{ev['s_sharpe']-ce_['s_sharpe']:>+9.3f}/{ev['h_sharpe']-ce_['h_sharpe']:+.3f}")
# breadth gate restricted to the far-from-200d half: if breadth still separates there, it is not the distance
far = [r for r in D_ROWS if r['gaps'][200] >= med200]; near = [r for r in D_ROWS if r['gaps'][200] < med200]
for lab, sub in (('far half', far), ('near half', near)):
    g_ = [r['legs'][2] for r in sub if r['bp'][K] < 0.2]; o_ = [r['legs'][2] for r in sub if r['bp'][K] >= 0.2]
    dt = (mean(g_) - mean(o_)) / math.sqrt(sd(g_) ** 2 / len(g_) + sd(o_) ** 2 / len(o_))
    print(f"  breadth gate within the {lab} of D days by gap200: gated n={len(g_)} QLD d1 {mean(g_)*1e4:+.1f}bp vs other n={len(o_)} {mean(o_)*1e4:+.1f}bp, diff t {dt:+.2f}")

# =====================================================================================================================
print("\n" + "=" * 112)
print("3. WHY D AND NOT A -- forward return, forward vol and the LIVE design's OWN exposure by breadth bucket")
print("=" * 112)
print("risky = mean live target risky weight (sum of the four risky legs after trim and vol target); beta = mean QQQ-beta of the")
print("live target (core x1 + TQQQ x3 + QLD x2); live d1 = mean realized live-design next-day return (bp) on those days;")
print("beta*d1 = mean of (beta x next-day QQQ return) (bp) = the P&L the design has at stake on such a day.")
def expo_stats(sub):
    ws = [LIVE(r) for r in sub]
    risky = mean([sum(w[:4]) for w in ws]); beta = mean([w[0] + 3 * w[1] + 2 * w[2] for w in ws])
    bd1 = mean([(w[0] + 3 * w[1] + 2 * w[2]) * r['qqq'] for w, r in zip(ws, sub)])
    return risky, beta, bd1
print(f"\n  {'state':<6}{'bucket':<8}{'n':>5}{'risky':>7}{'beta':>6}{'d1 bp':>7}{'fwd20':>7}{'vol20':>7}{'live d1':>8}{'beta*d1':>8}")
XS = {}
for st, sub_all in (('A', A_ROWS), ('D', D_ROWS)):
    for b in range(5):
        sub = [r for r in sub_all if bucket(r['bp'][K]) == b]
        if not sub: continue
        risky, beta, bd1 = expo_stats(sub); f20 = [x for x in (fwd(r, 20) for r in sub) if x is not None]; v20 = [x for x in (fvol(r) for r in sub) if x is not None]
        ld1 = mean([A_L[ri(_IDX[id(r)])] for r in sub])
        XS[(st, b)] = dict(n=len(sub), risky=risky, beta=beta, d1=mean([r['qqq'] for r in sub]), f20=mean(f20), v20=mean(v20), bd1=bd1)
        print(f"  {st:<6}{BUCK[b]:<8}{len(sub):>5}{risky:>7.2f}{beta:>6.2f}{mean([r['qqq'] for r in sub])*1e4:>7.1f}{mean(f20)*100:>7.2f}{mean(v20)*100:>7.1f}{ld1*1e4:>8.1f}{bd1*1e4:>8.1f}")
# decomposition of the bottom-quintile asymmetry
a0, d0 = XS[('A', 0)], XS[('D', 0)]
print(f"\n  BOTTOM-QUINTILE DAYS: A n={a0['n']} beta {a0['beta']:.2f} next-day QQQ {a0['d1']*1e4:+.1f}bp;  D n={d0['n']} beta {d0['beta']:.2f} next-day QQQ {d0['d1']*1e4:+.1f}bp")
bb = 0.5 * (a0['beta'] + d0['beta']); rb = 0.5 * (a0['d1'] + d0['d1'])
tot = d0['beta'] * d0['d1'] - a0['beta'] * a0['d1']
print(f"  per-day P&L at stake (beta x d1): D {d0['beta']*d0['d1']*1e4:+.1f}bp vs A {a0['beta']*a0['d1']*1e4:+.1f}bp, difference {tot*1e4:+.1f}bp/day, of which")
print(f"    return difference   (mean beta x dr): {bb*(d0['d1']-a0['d1'])*1e4:+.1f}bp  ({bb*(d0['d1']-a0['d1'])/tot*100:.0f}%)")
print(f"    exposure difference (mean r x dbeta): {rb*(d0['beta']-a0['beta'])*1e4:+.1f}bp  ({rb*(d0['beta']-a0['beta'])/tot*100:.0f}%)")
# counterfactual gate gains: gain of a cash gate = -sum(beta_i * qqq_i) over gated days
def gate_gain(sub, beta_override=None):
    tot_ = 0.0
    for r in sub:
        w = LIVE(r); beta = (w[0] + 3 * w[1] + 2 * w[2]) if beta_override is None else beta_override
        tot_ += -beta * r['qqq']
    return tot_ * 100
Ab = [r for r in A_ROWS if r['bp'][K] < 0.2]; Db = [r for r in D_ROWS if r['bp'][K] < 0.2]
print(f"\n  COUNTERFACTUAL 'cash-instead' gains (sum of -beta x next-day QQQ over bottom-quintile days, pp, before costs/vol-target path):")
print(f"    D gate as designed (own beta):            {gate_gain(Db):+.1f}pp over {len(Db)} days")
print(f"    D days but with A's mean beta {a0['beta']:.2f}:      {gate_gain(Db, a0['beta']):+.1f}pp   (return effect alone)")
print(f"    A gate as designed (own beta):            {gate_gain(Ab):+.1f}pp over {len(Ab)} days")
print(f"    A days but with D's mean beta {d0['beta']:.2f}:      {gate_gain(Ab, d0['beta']):+.1f}pp   (exposure effect alone)")
# the actual harness numbers for the A-only gate on these rows, for the record
GA_fn = gate_fn(K, 1.0, scope=('A',)); EVA = evaluate(RQ, GA_fn); kA, keA = exposure_control_live(RQ, EVA['risky'])
print(f"  harness: A-only cash gate {fmt(EVA)} S {EVA['s_sharpe']:.3f} H {EVA['h_sharpe']:.3f} exp {EVA['risky']*100:.1f}% vs k-live k={kA:.3f} "
      f"S {keA['s_sharpe']:.3f} H {keA['h_sharpe']:.3f} -> {EVA['s_sharpe']-keA['s_sharpe']:+.3f}/{EVA['h_sharpe']-keA['h_sharpe']:+.3f}; gated A days {len(Ab)}")

# =====================================================================================================================
print("\n" + "=" * 112)
print("4. ROBUSTNESS NOT YET RUN")
print("=" * 112)
# ---- (a) execution lag
print("\n(a) EXECUTION LAG.  The gate flag (state D AND pct<0.2) is computed at d0 and acted on at d0+k.  Two readings:")
print("    'if still D': at d0+k the row goes to cash only if eff is still D (the state machine has not moved on);")
print("    'unconditional': the cash instruction is executed at d0+k whatever the state then is.")
print(f"  {'lag':<5}{'variant':<15}{'CAGR/Sh/MDD':>22}{'S':>7}{'H':>7}{'exp':>7}{'| vs live S/H':>15}{'| vs const-D S/H':>17}{'| on':>5}")
def lag_fn(k, cond):
    def fn(r):
        i = _IDX[id(r)]; w = trimmed(r['eff'], r['gaps'])
        j = i - k; on = j >= 0 and gated(rows[j]) and (r['eff'] == 'D' if cond else True)
        if on: w = scale_risky(w, 0.0)
        return vt(w, r['vol'])
    return fn
for k in (0, 1, 2):
    for cond, lab in ((True, 'if still D'), (False, 'unconditional')):
        if k == 0 and not cond: continue
        fn = lag_fn(k, cond); ev = evaluate(RQ, fn); q_ = calib_q(RQ, ev['risky']); ce_ = evaluate(RQ, const_D(q_))
        on = sum(1 for r in RQ if (_IDX[id(r)] - k >= 0 and gated(rows[_IDX[id(r)] - k]) and (r['eff'] == 'D' if cond else True)))
        print(f"  {k:<5}{lab:<15}{fmt(ev):>22}{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f}{ev['risky']*100:>6.1f}%"
              f"{ev['s_sharpe']-BL_EV['s_sharpe']:>+8.3f}/{ev['h_sharpe']-BL_EV['h_sharpe']:+.3f}{ev['s_sharpe']-ce_['s_sharpe']:>+10.3f}/{ev['h_sharpe']-ce_['h_sharpe']:+.3f}{on:>5}")

# ---- (b) cost sensitivity
print("\n(b) COST SENSITIVITY (one-way spread patched in the harness; q of the constant-D control kept at the base calibration):")
print(f"  {'cost':<6}{'gate CAGR/Sh/MDD':>22}{'S':>7}{'H':>7}{'| live Sh':>10}{'S':>7}{'H':>7}{'| constD Sh':>12}{'| gate-live S/H':>16}{'| gate-constD S/H':>18}{'| cost drag gate/live pp/yr':>28}")
base_cost = IS.ONE_WAY_SPREAD
IS.ONE_WAY_SPREAD = 0.0; g0 = stats(run(RQ, GATE)[0])[0]; l0 = stats(run(RQ, LIVE)[0])[0]
for c in (0.0004, 0.0010, 0.0020):
    IS.ONE_WAY_SPREAD = c
    ev = evaluate(RQ, GATE); bl_ = evaluate(RQ, LIVE); ce_ = evaluate(RQ, CD)
    gd = (g0 - stats(run(RQ, GATE)[0])[0]) * 100; ld = (l0 - stats(run(RQ, LIVE)[0])[0]) * 100
    print(f"  {c*1e4:>3.0f}bp{fmt(ev):>22}{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f}{bl_['sharpe']:>10.3f}{bl_['s_sharpe']:>7.3f}{bl_['h_sharpe']:>7.3f}{ce_['sharpe']:>12.3f}"
          f"{ev['s_sharpe']-bl_['s_sharpe']:>+9.3f}/{ev['h_sharpe']-bl_['h_sharpe']:+.3f}{ev['s_sharpe']-ce_['s_sharpe']:>+11.3f}/{ev['h_sharpe']-ce_['h_sharpe']:+.3f}{gd:>14.2f} / {ld:.2f}")
IS.ONE_WAY_SPREAD = base_cost

# ---- (c) episode-block bootstrap
print(f"\n(c) EPISODE-BLOCK BOOTSTRAP ({NB} draws).  Unit = a whole D episode (all its days, paired across the two series); the")
print("    non-D days are kept fixed, the D episodes are resampled with replacement (same count), then the Sharpe / log-return")
print("    difference is recomputed.  This is the bootstrap that treats the ~40 episodes as the sample size, not the 4,800 days.")
def ep_boot(a, b, rs, i0, nb=NB, seed_=1):
    """a, b: daily return lists aligned with rs (rows[i0:]); D episodes from rows indices."""
    i1 = i0 + len(rs) - 1
    eps = [(max(s, i0) - i0, min(e, i1) - i0) for s, e in EP_D if e >= i0 and s <= i1]
    dset = set(); [dset.update(range(s, e + 1)) for s, e in eps]
    fixed = [i for i in range(len(rs)) if i not in dset]
    fa = [a[i] for i in fixed]; fb = [b[i] for i in fixed]
    ea = [[a[i] for i in range(s, e + 1)] for s, e in eps]; eb = [[b[i] for i in range(s, e + 1)] for s, e in eps]
    rng = random.Random(seed_); dl, dsh = [], []
    for _ in range(nb):
        pick = [rng.randrange(len(eps)) for _ in eps]
        xa = fa + [x for p in pick for x in ea[p]]; xb = fb + [x for p in pick for x in eb[p]]
        la, sa = stats(xa); lb, sb = stats(xb); dl.append(la - lb); dsh.append(sa - sb)
    dl.sort(); dsh.sort(); lo, hi = int(0.025 * nb), int(0.975 * nb) - 1
    return (dl[lo], dl[hi], sum(1 for x in dl if x <= 0) / nb, dsh[lo], dsh[hi], sum(1 for x in dsh if x <= 0) / nb, len(eps))
for lab, ref in (('const-D', A_C), ('live', A_L)):
    l1, l2, pl, s1, s2, ps, ne = ep_boot(A_G, ref, RQ, RQ_I0, seed_=zlib.crc32(lab.encode()))
    la, sa = stats(A_G); lb, sb = stats(ref)
    print(f"  gate vs {lab:<8} point {(la-lb)*100:+.2f}pp/yr, {sa-sb:+.3f} Sharpe | episode boot ({ne} episodes): log-return CI [{l1*100:+.2f}, {l2*100:+.2f}] P(<=0)={pl:.3f}"
          f"   Sharpe CI [{s1:+.3f}, {s2:+.3f}] P(<=0)={ps:.3f}")
for blk in (20, 60):
    l1, l2, pl, s1, s2, ps = boot(A_G, A_C, blk, seed=zlib.crc32(f'anat|constD|{blk}'.encode()))
    print(f"  (for comparison, circular day-block bootstrap vs const-D, block {blk}d: Sharpe CI [{s1:+.3f}, {s2:+.3f}] P(<=0)={ps:.3f})")

# ---- (d) rolling 3-year windows
print("\n(d) ROLLING 3-YEAR WINDOWS (start every 6 months): Sharpe of gate / const-D / live in the window, deltas, gated days & runs")
print(f"  {'window':<24}{'n':>5}{'gate':>7}{'constD':>7}{'live':>7}{'g-cD':>7}{'g-live':>7}{'gated d':>8}{'runs':>5}{'D days':>7}")
starts = []; y, m = 2007, 7
while True:
    s = f"{y:04d}-{m:02d}-01"; e = f"{y+3:04d}-{m:02d}-01"
    if e > RQ[-1]['d']: break
    starts.append((s, e)); m += 6
    if m > 12: m -= 12; y += 1
negs = 0; negl = 0; nwin = 0
for s, e in starts:
    idx = [i for i, r in enumerate(RQ) if s <= r['d'] < e]
    if len(idx) < 500: continue
    nwin += 1
    sg = sharpe_of([A_G[i] for i in idx]); sc = sharpe_of([A_C[i] for i in idx]); sl = sharpe_of([A_L[i] for i in idx])
    gd = sum(1 for i in idx if gated(RQ[i])); nr = sum(1 for (a_, b_) in RUNS if s <= rows[a_]['d'] < e); dd = sum(1 for i in idx if RQ[i]['eff'] == 'D')
    negs += sg - sc < 0; negl += sg - sl < 0
    print(f"  {s}..{e:<12}{len(idx):>5}{sg:>7.3f}{sc:>7.3f}{sl:>7.3f}{sg-sc:>+7.3f}{sg-sl:>+7.3f}{gd:>8}{nr:>5}{dd:>7}")
print(f"  windows {nwin}; negative vs const-D: {negs}; negative vs live: {negl}")

# ---- (e) continuous version
print("\n(e) CONTINUOUS VERSION: QLD weight in D = f(pct) instead of the hard 0/1 at 0.20 (each mapping is one candidate; the")
print("    hard threshold is the reference).  Controls: same-rows live and constant-D at matched capital; episode bootstrap vs const-D.")
print(f"  {'mapping':<28}{'CAGR/Sh/MDD':>22}{'S':>7}{'H':>7}{'exp':>7}{'| vs live S/H':>15}{'| vs constD S/H':>16}{'| ep-boot Sh CI vs constD':>27}{'P<=0':>6}{'| real Sh':>9}")
MAPS = [('hard: 1[pct>=0.2] (reference)', lambda p: 1.0 if p >= 0.2 else 0.0),
        ('clip((pct-0.2)/0.3, 0, 1)', lambda p: min(1.0, max(0.0, (p - 0.2) / 0.3))),
        ('clip((pct-0.1)/0.3, 0, 1)', lambda p: min(1.0, max(0.0, (p - 0.1) / 0.3))),
        ('clip(pct/0.4, 0, 1)', lambda p: min(1.0, max(0.0, p / 0.4))),
        ('pct (linear 0..1)', lambda p: p),
        ('clip((pct-0.2)/0.6, 0, 1)', lambda p: min(1.0, max(0.0, (p - 0.2) / 0.6)))]
def smooth_fn(f, vtf=vt):
    def fn(r):
        w = trimmed(r['eff'], r['gaps'])
        if r['eff'] == 'D': w = scale_risky(w, f(r['bp'][K]))
        return vtf(w, r['vol'])
    return fn
NC_SMOOTH = 0
for lab, f in MAPS:
    fn = smooth_fn(f); ev = evaluate(RQ, fn); q_ = calib_q(RQ, ev['risky']); ce_ = evaluate(RQ, const_D(q_))
    a_ = run(RQ, fn)[0]; c_ = run(RQ, const_D(q_))[0]; _, _, _, s1, s2, ps, _ = ep_boot(a_, c_, RQ, RQ_I0, seed_=zlib.crc32(lab.encode()))
    re_ = RF.eval_real(rr, smooth_fn(f, RF.vt)); NC_SMOOTH += 0 if 'reference' in lab else 1
    print(f"  {lab:<28}{fmt(ev):>22}{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f}{ev['risky']*100:>6.1f}%"
          f"{ev['s_sharpe']-BL_EV['s_sharpe']:>+8.3f}/{ev['h_sharpe']-BL_EV['h_sharpe']:+.3f}{ev['s_sharpe']-ce_['s_sharpe']:>+9.3f}/{ev['h_sharpe']-ce_['h_sharpe']:+.3f}"
          f"{'':>8}[{s1:+.3f}, {s2:+.3f}]{ps:>6.3f}{re_['sharpe']:>9.3f}")

# ---- (f) alternate breadth definitions, same mechanism, same D rows
print("\n(f) ALTERNATE BREADTH DEFINITIONS with the SAME mechanism (D row to cash when the definition is 'weak'), on the SAME rows")
print("    (rows where every definition has a value).  Mechanism-consistency check, not a search: a coherent mechanism should show")
print("    the same sign on every definition; per-day stats are the QLD leg on gated vs other D days.")
ALT = [('qqew_60', 'QQEW/QQQ 60d change (reference)'), ('qqew_avg2060', 'avg of 20d and 60d changes'), ('qqew_120', '120d change'),
       ('qqew_s200', 'log-ratio minus its 200d SMA'), ('cwz60', 'cap-wt minus eq-wt 60d, z>0.84'), ('qqew_20', '20d change (known to fail)')]
RALT = [r for r in RQ if all(r['bp'][n] is not None for n in [a for a, _ in ALT])]; RALT_I0 = _IDX[id(RALT[0])]
bA = evaluate(RALT, LIVE); dA = [r for r in RALT if r['eff'] == 'D']
print(f"  rows {len(RALT)} {RALT[0]['d']}..{RALT[-1]['d']}, D days {len(dA)}; live {fmt(bA)} S {bA['s_sharpe']:.3f} H {bA['h_sharpe']:.3f}")
print(f"  {'definition':<32}{'on':>4}{'Jacc':>6}{'gated bp':>9}{'other bp':>9}{'diff t':>7}{'| CAGR/Sh/MDD':>24}{'S':>7}{'H':>7}{'| vs live S/H':>15}{'| vs constD S/H':>16}{'| real':>7}")
ref_on = set(_IDX[id(r)] for r in dA if r['bp']['qqew_60'] < 0.2)
for n, lab in ALT:
    on = [r for r in dA if r['bp'][n] < 0.2]; off = [r for r in dA if r['bp'][n] >= 0.2]
    ons = set(_IDX[id(r)] for r in on); jac = len(ons & ref_on) / max(1, len(ons | ref_on))
    g = [r['legs'][2] for r in on]; o = [r['legs'][2] for r in off]
    dt = (mean(g) - mean(o)) / math.sqrt(sd(g) ** 2 / len(g) + sd(o) ** 2 / len(o)) if len(g) > 2 else float('nan')
    fn = gate_fn(n, 1.0); ev = evaluate(RALT, fn); q_ = calib_q(RALT, ev['risky']); ce_ = evaluate(RALT, const_D(q_)); re_ = RF.eval_real(rr, gate_fn(n, 1.0, vtf=RF.vt))
    print(f"  {lab:<32}{len(on):>4}{jac:>6.2f}{mean(g)*1e4:>9.1f}{mean(o)*1e4:>9.1f}{dt:>7.2f}{fmt(ev):>24}{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f}"
          f"{ev['s_sharpe']-bA['s_sharpe']:>+8.3f}/{ev['h_sharpe']-bA['h_sharpe']:+.3f}{ev['s_sharpe']-ce_['s_sharpe']:>+9.3f}/{ev['h_sharpe']-ce_['h_sharpe']:+.3f}{re_['sharpe']:>7.3f}")

# =====================================================================================================================
print("\n" + "=" * 112)
print("5. THE HONEST HOLDOUT -- D episodes in 2007-07-27..2015-10-31")
print("=" * 112)
HO = [r for r in RQ if r['d'] <= HOLDOUT[1]]; SE = [r for r in RQ if r['d'] >= SEARCH[0]]
print(f"  {'start':<11}{'end':<11}{'days':>5}{'QLD%':>7}{'QQQ%':>7}{'exit':>5}{'gated':>6}{'g-days':>7}{'contrib':>8}  gated runs")
hc = 0.0; hn = 0; hne = 0
for (s, e) in EP_D:
    if rows[s]['d'] > HOLDOUT[1] or rows[e]['d'] < RQ[0]['d']: continue
    days = [i for i in range(max(s, RQ_I0), e + 1)]
    qld = sum(math.log1p(rows[i]['legs'][2]) for i in days) * 100; qqq_ret = sum(math.log1p(rows[i]['qqq']) for i in days) * 100
    gdays = [i for i in days if gated(rows[i])]; contrib = sum(math.log1p(A_G[ri(i)]) - math.log1p(A_L[ri(i)]) for i in days) * 100
    runs_ = [x for x in rows_out if x['pe'] == (s, e)]
    if gdays: hn += 1; hne += len(runs_)
    hc += contrib
    print(f"  {rows[max(s,RQ_I0)]['d']:<11}{rows[e]['d']:<11}{len(days):>5}{qld:>+7.1f}{qqq_ret:>+7.1f}{exit_state((s,e)) or '-':>5}{'YES' if gdays else '-':>6}{len(gdays):>7}{contrib:>+8.1f}  "
          + ", ".join(f"{x['s']}({x['n']}d {x['c']:+.1f})" for x in runs_))
print(f"  holdout: {sum(1 for (s,e) in EP_D if rows[s]['d'] <= HOLDOUT[1])} D episodes, {hn} with a gated day, {hne} gated runs, contribution over D-episode days {hc:+.1f}pp")
ho_ranked = sorted([x for x in rows_out if x['s'] <= HOLDOUT[1]], key=lambda x: -x['c'])
print(f"  holdout gated runs ranked: " + ", ".join(f"{x['s']}({x['n']}d {x['c']:+.1f})" for x in ho_ranked))
print(f"  -> the holdout gain rests on {sum(1 for x in ho_ranked if x['c'] > 0)} positive runs in {len(set(x['pe'] for x in ho_ranked if x['c'] > 0))} D episodes; "
      f"the top 3 runs carry {sum(x['c'] for x in ho_ranked[:3]):+.1f}pp of the holdout total {sum(x['c'] for x in ho_ranked):+.1f}pp; negative runs sum {sum(x['c'] for x in ho_ranked if x['c']<0):+.1f}pp")

print("\n  STRICT SPLIT (fit nothing; the rule is fixed; q of the constant-D control is (i) the full-sample 0.850 and (ii) re-matched")
print("  to the gate's capital inside each half -- a control setting, not a fit).  Episode bootstrap CI per half.")
from drift_band_test import annual_stats
def ev_half(rs_, fn):
    f, e = run(rs_, fn); c, s_, m = annual_stats(f); return dict(cagr=c, sharpe=s_, mdd=m, risky=e)
for lab, rs_ in (('holdout 2007-07..2015-10', HO), ('search 2015-11..2026-08', SE)):
    i0 = _IDX[id(rs_[0])]; ag = run(rs_, GATE)[0]; al = run(rs_, LIVE)[0]
    evg = ev_half(rs_, GATE); evl = ev_half(rs_, LIVE)
    q2 = calib_q(rs_, evg['risky']); ac1 = run(rs_, CD)[0]; ac2 = run(rs_, const_D(q2))[0]
    ev1 = ev_half(rs_, CD); ev2 = ev_half(rs_, const_D(q2))
    print(f"\n  [{lab}] n={len(rs_)}  gate {fmt(evg)} exp {evg['risky']*100:.1f}% | live {fmt(evl)} | const-D q=0.850 {fmt(ev1)} exp {ev1['risky']*100:.1f}% | const-D q={q2:.3f} {fmt(ev2)} exp {ev2['risky']*100:.1f}%")
    for cl, ref in (('live', al), ('const-D q=0.850', ac1), (f'const-D q={q2:.3f}', ac2)):
        l1, l2, pl, s1, s2, ps, ne = ep_boot(ag, ref, rs_, i0, seed_=zlib.crc32((lab + cl).encode()))
        la, sa = stats(ag); lb, sb = stats(ref)
        bl20 = boot(ag, ref, 20, seed=zlib.crc32((lab + cl + '20').encode())); bl60 = boot(ag, ref, 60, seed=zlib.crc32((lab + cl + '60').encode()))
        print(f"    vs {cl:<18} point {(la-lb)*100:+.2f}pp/yr {sa-sb:+.3f} Sh | episode boot ({ne} eps) Sh CI [{s1:+.3f},{s2:+.3f}] P<=0 {ps:.3f}, logret CI [{l1*100:+.2f},{l2*100:+.2f}] P<=0 {pl:.3f}"
              f" | day-block 20d Sh P<=0 {bl20[5]:.3f}, 60d {bl60[5]:.3f}")

# =====================================================================================================================
print("\n" + "=" * 112)
print("6. TODAY'S READING for the live-tracking spec")
print("=" * 112)
last_q = max(QQEW); last_row = rows[-1]
print(f"  QQEW_daily.csv last date {last_q}; data/qqq_long_history.csv last date {max(qqq)}; harness QQQ (QQQ+XLU common) last date {ds[-1]};")
print(f"  last proxy row {last_row['d']} state {last_row['state']} eff {last_row['eff']}.  The table below recomputes the series with the FULL QQQ file")
print(f"  (the exec'd code uses the harness QQQ, which is stale after {ds[-1]}); a leg marked stale is forward-filled and the reading is provisional.")
_lr = ratio_series(QQEW, qqq); _s60 = diffs(_lr, 60); _p60 = trailing_pct(_s60)
print(f"  {'date':<12}{'log(QQEW/QQQ)':>15}{'60d chg':>9}{'pct252':>8}{'fires?':>8}  legs")
for d in cal[-10:]:
    i = cix[d]; v = _s60[i]; p = _p60[i]
    if v is None: continue
    st = ('QQEW stale ' if d not in QQEW else '') + ('QQQ stale' if d not in qqq else '')
    print(f"  {d:<12}{_lr[i]:>15.5f}{v:>+9.4f}{p:>8.3f}{'yes' if p < 0.2 else 'no':>8}  {st or 'both fresh'}")
print(f"\nCANDIDATE COUNT this line: {NC_SMOOTH} smooth mappings + {len(ALT)-2} alternate definitions (qqew_60 and qqew_20 were already counted) "
      f"+ 4 lag variants + {NC_GAP} gap200 placebo gates = {NC_SMOOTH + len(ALT) - 2 + 4 + NC_GAP}; cumulative with the earlier lines: {224 + NC_SMOOTH + len(ALT) - 2 + 4 + NC_GAP}.")
print("Done.")
