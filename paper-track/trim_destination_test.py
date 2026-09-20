#!/usr/bin/env python3
"""
trim_destination_test.py -- RESEARCH ONLY (2026-09-20). Where should the extension trim send the freed A-row weight?

Owner's question: the graded extension trim in effective state A holds the A row (50 % SPMO / 50 % TQQQ) at x1 /
x2/3 / x1/3 / x0 at 0/1/2/3 votes and puts the freed weight in BOXX. Every trim variant recorded in STRATEGY.md
("Extension trim", "Leverage under the trim", the z-score line, the r4 floors) sends the trimmed weight to CASH. Was
moving it into SPMO (the unlevered core) instead ever tested? This script tests exactly the pre-registered 7 schedules
(6 candidates + live), nothing else. No thresholds change. The vol target multiplies on top, as live.

Pre-registered A-row weights (SPMO, TQQQ, cash) at 0 / 1 / 2 / 3 votes:
  S0 LIVE                  (50,50,0) / (33.3,33.3,33.3) / (16.7,16.7,66.7) / (0,0,100)
  S1 TQQQ-first, never cash (50,50,0) / (75,25,0)        / (100,0,0)        / (100,0,0)
  S2 TQQQ-first then cash  (50,50,0) / (75,25,0)        / (100,0,0)        / (50,0,50)
  S3 TQQQ-first, all cash  (50,50,0) / (75,25,0)        / (100,0,0)        / (0,0,100)
  S4 half-and-half         (50,50,0) / (58.3,33.3,8.3)  / (58.3,16.7,25)   / (50,0,50)     [verbatim from the pre-registration]
  S5 core-only at any vote (50,50,0) / (100,0,0)        / (100,0,0)        / (100,0,0)
  S6 core then cash steps  (50,50,0) / (100,0,0)        / (50,0,50)        / (0,0,100)
A "no trim" row ((50,50,0) at every vote) is printed as a labelled REFERENCE only; it is not a candidate and is not in
the permutation.

Harness: the CURRENT live design (state-D gate, E = 100 % cash) built exactly as e_outcome_explore.py part III did:
`d_substate_fresh` imported with DSF_STAGE=none for its bootstrap (proxy rows, vt, run/run_count, evaluate_full, the
real DAILY mirror's data, block_bootstrap.boot, REGIMES). d_substate_fresh pins state.TARGET_WEIGHTS['E'] back to 50 %
XLU at import and its simulate_real / proxy BASE do not apply the D gate, so the baseline is built by override: D days ->
cash when state.d_gate_active(st, breadth_pct, gap200) (breadth = breadth_tracker on data/QQEW_daily_ext.csv, as
d_pair_test), E days -> (0,0,0,0,1). Both baselines are ASSERTED to reproduce proxy 25.46 % / 1.071 / -27.0 % (S 1.399,
H 0.825) and real daily 37.30 % / 1.475 / -18.6 % before anything is scored. Sharpe is the repo's zero-rate Sharpe.

Stages: TDT_STAGE=all|grid|perm|deep (default all; Part I) and TDT_STAGE=part2 (Part II, S6 anatomy, appends to the log),
TDT_NPERM (1000), TDT_PROCS (4). Run from the repo root:
    python3 paper-track/trim_destination_test.py
Log: paper-track/research_notes/trim_destination_test_run.log (written by the script). Standard library only.
"""
import sys, os, math, json, random, csv, time, statistics, io, contextlib

os.environ.setdefault('DSF_STAGE', 'none')          # import d_substate_fresh for its bootstrap only
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)
sys.path.insert(0, 'paper-track')
SCRATCH = os.environ.get('TDT_SCRATCH',
                         '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad')
os.makedirs(SCRATCH, exist_ok=True)
STAGE = os.environ.get('TDT_STAGE', 'all')
N_PERM = int(os.environ.get('TDT_NPERM', '1000'))
N_PROCS = int(os.environ.get('TDT_PROCS', '4'))
SEED = 20260920
T0 = time.time()
LOG_PATH = os.path.join(REPO_ROOT, 'paper-track', 'research_notes', 'trim_destination_test_run.log')
_LOG_MODE = 'w' if STAGE in ('all', 'grid') else 'a'
_logf = open(LOG_PATH, _LOG_MODE)

def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True); _logf.write(s + '\n'); _logf.flush()

_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):                # the harness prints its standing figures at import
    import d_substate_fresh as DSF
    import monthly_returns as MR
    import improvement_search as IS
    import block_bootstrap as BB
from d_substate_fresh import (rows, run, run_count, vt, RF, W, evaluate_full, real_metrics, RPX, RQQQ, RDAYS,
                              SEARCH, HOLDOUT, REGIMES, boot, bstats, annual_stats, sliced_sharpe)
from improvement_search_r2 import scaled
import state
from state import (d_gate_active, compute_micro_agreement, compute_fast_states, compute_extension_gaps,
                   compute_states, realized_vol_live, target_weights_with_voltarget, effective_state,
                   extension_votes, needs_rebalance, D_GATE_ENABLED, EXTENSION_STEP, TARGET_WEIGHTS)
import breadth_tracker as BT

assert D_GATE_ENABLED and BB.N_BOOT == 2000 and abs(EXTENSION_STEP - 1 / 3) < 1e-12
assert TARGET_WEIGHTS['A'] == (0.5, 0.5, 0.0, 0.0, 0.0), 'A row is not 50/50; the schedules below assume it'

CASH = (0.0, 0.0, 0.0, 0.0, 1.0)
F3 = 1.0 / 3.0

# ---------------------------------------------------------------- the 7 pre-registered schedules (+ 1 reference)
# (SPMO, TQQQ, cash) at 0 / 1 / 2 / 3 votes; exact fractions of the figures in the pre-registration.
SCHED = [
    ('S0', 'LIVE: x2/3, x1/3, x0 to cash',   [(.5, .5, 0), (F3, F3, F3), (1 / 6, 1 / 6, 2 / 3), (0, 0, 1)]),
    ('S1', 'TQQQ-first, never cash',         [(.5, .5, 0), (.75, .25, 0), (1, 0, 0), (1, 0, 0)]),
    ('S2', 'TQQQ-first then cash',           [(.5, .5, 0), (.75, .25, 0), (1, 0, 0), (.5, 0, .5)]),
    ('S3', 'TQQQ-first then all cash',       [(.5, .5, 0), (.75, .25, 0), (1, 0, 0), (0, 0, 1)]),
    ('S4', 'half-and-half (verbatim)',       [(.5, .5, 0), (7 / 12, F3, 1 / 12), (7 / 12, 1 / 6, .25), (.5, 0, .5)]),
    ('S5', 'core-only at any vote',          [(.5, .5, 0), (1, 0, 0), (1, 0, 0), (1, 0, 0)]),
    ('S6', 'core then cash steps',           [(.5, .5, 0), (1, 0, 0), (.5, 0, .5), (0, 0, 1)]),
]
REF_NOTRIM = ('REF', 'no trim (reference only)', [(.5, .5, 0)] * 4)
for _, _, s in SCHED + [REF_NOTRIM]:
    for a, b, c in s: assert abs(a + b + c - 1) < 1e-12
def srow(sched, v):
    a, b, c = sched[v]
    return (a, b, 0.0, 0.0, c)
def fmt_row(sched):
    return ' / '.join(f"({a*100:.0f},{b*100:.0f},{c*100:.0f})" if abs(a*100-round(a*100))<1e-9 and abs(b*100-round(b*100))<1e-9
                      else f"({a*100:.1f},{b*100:.1f},{c*100:.1f})" for a, b, c in sched)

# ---------------------------------------------------------------- breadth (breadth_tracker verbatim, as d_pair_test)
def load_dc(path):
    out = {}
    for r in csv.DictReader(open(path)):
        try: out[r['d']] = float(r['c'])
        except ValueError: pass
    return out
QQEW = load_dc('data/QQEW_daily_ext.csv')
def breadth_pct(qqq, other=QQEW):
    common, x = BT.relative_strength_series(sorted(qqq), other, qqq)
    return dict(zip(common, BT.trailing_pct(x)))
BP_Q = breadth_pct(DSF._QQQ_FULL)
BP_R = breadth_pct(RQQQ)

# ---------------------------------------------------------------- PROXY: gated baseline with E -> cash, A by schedule
GATE_Q = set(r['d'] for r in rows if r['state'] == 'D' and d_gate_active(r['state'], BP_Q.get(r['d']), r['gaps'][200]))
E_Q = set(r['d'] for r in rows if r['state'] == 'E')
A_IDX = [i for i, r in enumerate(rows) if r['eff'] == 'A' and r['d'] not in GATE_Q and r['d'] not in E_Q]
assert all(rows[i]['state'] != 'D' for i in A_IDX)
VOTES_Q = {rows[i]['d']: extension_votes(rows[i]['eff'], rows[i]['gaps']) for i in A_IDX}
# A-day override targets, precomputed for speed: A_T[d][sched_idx][votes] = vt(row, vol)
ALL_S = [s for _, _, s in SCHED] + [REF_NOTRIM[2]]
A_T = {rows[i]['d']: [[vt(srow(s, v), rows[i]['vol']) for v in range(4)] for s in ALL_S] for i in A_IDX}
OTHER_Q = {}
for r in rows:
    if r['d'] in GATE_Q or r['d'] in E_Q: OTHER_Q[r['d']] = vt(CASH, r['vol'])
    elif r['d'] not in VOTES_Q: OTHER_Q[r['d']] = DSF.BASE[r['d']]
def proxy_fn(si, votes=VOTES_Q):
    """weight function on the proxy rows for schedule index si (0..6, 7 = no-trim reference)."""
    def fn(r):
        d = r['d']
        if d in votes: return A_T[d][si][votes[d]]
        return OTHER_Q[d]
    return fn
def proxy_eval(si, votes=VOTES_Q):
    return evaluate_full(proxy_fn(si, votes))
# the live schedule must equal the harness's own trimmed A row day by day
for i in A_IDX:
    r = rows[i]
    assert max(abs(a - b) for a, b in zip(A_T[r['d']][0][VOTES_Q[r['d']]], DSF.BASE[r['d']])) < 1e-12

# ---------------------------------------------------------------- REAL DAILY mirror (monthly_returns.simulate mechanics)
def real_precompute():
    qd = sorted(RQQQ)
    states = dict(zip(qd, compute_states(qd, RQQQ)))
    micro = compute_micro_agreement(qd, RQQQ)
    fast = compute_fast_states(qd, RQQQ); gaps = compute_extension_gaps(qd, RQQQ)
    info = {}
    for d0 in RDAYS[:-1]:
        st = states[d0]; eff = effective_state(st, fast[d0])
        info[d0] = dict(st=st, ag=micro[d0], fast=fast[d0], gaps=gaps[d0], eff=eff,
                        vol=realized_vol_live(qd, RQQQ, as_of=d0),
                        gate=d_gate_active(st, BP_R.get(d0), gaps[d0][200]),
                        votes=extension_votes(eff, gaps[d0]))
    return info
RINFO = real_precompute()
RA_DAYS = [d for d in RDAYS[:-1] if RINFO[d]['eff'] == 'A' and not RINFO[d]['gate'] and RINFO[d]['st'] != 'E']
VOTES_R = {d: RINFO[d]['votes'] for d in RA_DAYS}
RLEG_RET = {}
for i in range(1, len(RDAYS)):
    d0, d1 = RDAYS[i - 1], RDAYS[i]
    RLEG_RET[d0] = [RPX[s][d1] / RPX[s][d0] - 1 for s in MR.LEGS]

def simulate_real_sched(sched, votes=VOTES_R, scale=1.0, one_way=None, use_live_fn_check=False):
    """Real daily mirror with the CURRENT live design: D gate -> cash, E -> cash, effective-A days by `sched`
    (rungs by vote count), everything else the live row. Then the vol target, then an optional flat de-lever k
    (exposure control). Rebalance: needs_rebalance() with the regime key (eff, votes, gate), cost MR.ONE_WAY."""
    ow = MR.ONE_WAY if one_way is None else one_way
    held = prev = None; out = []; risky = 0.0; nreb = 0
    for i in range(1, len(RDAYS)):
        d0, d1 = RDAYS[i - 1], RDAYS[i]
        I = RINFO[d0]; st, eff, gate = I['st'], I['eff'], I['gate']
        if gate or st == 'E':
            v = 0; t = CASH
        elif d0 in votes:
            v = votes[d0]; t = RF.vt(srow(sched, v), I['vol'])
        else:
            v = 0
            if use_live_fn_check:
                t = target_weights_with_voltarget(st, I['ag'], I['vol'], fast_state=I['fast'], gaps=I['gaps'], d_gate=gate)
            else:
                t = RF.vt(W[eff], I['vol'])
        if scale != 1.0:
            rk = sum(t[:4]); t = tuple(x * scale for x in t[:4]) + (1.0 - rk * scale,)
        stk = (eff, v, gate)
        cost = 0.0
        if held is None:
            held = list(t); nreb += 1
        else:
            do, drift, _ = needs_rebalance(t, held, stk != prev)
            if do:
                cost = ow * drift; held = list(t); nreb += 1
        r = RLEG_RET[d0]
        g = sum(held[j] * r[j] for j in range(5))
        risky += sum(held[:4])
        out.append((d1, eff, g - cost))
        dn = 1 + g
        if dn > 0: held = [held[j] * (1 + r[j]) / dn for j in range(5)]
        prev = stk
    n = len(out)
    return out, risky / n, nreb / (n / 252.0)
def real_eval(sched, **kw):
    out, exp, reb = simulate_real_sched(sched, **kw)
    m, ser = real_metrics(out)
    return dict(m, exp=exp, reb=reb), ser
def fmt_ev(ev): return f"{ev['cagr']*100:6.2f}% /{ev['sharpe']:6.3f} /{ev['mdd']*100:6.1f}%"
def byyear(ser, dates):
    by = {}
    for d, x in zip(dates, ser): by[d[:4]] = by.get(d[:4], 0.0) + math.log1p(x)
    return {y: math.expm1(v) for y, v in by.items()}
PDATES = [r['d'] for r in rows]
RD1 = RDAYS[1:]

# ---------------------------------------------------------------- baselines (asserted)
LIVE_EV, LIVE_SER = proxy_eval(0)
RLIVE_EV, RLIVE_SER = real_eval(SCHED[0][2])
_chk, _, _ = simulate_real_sched(SCHED[0][2], use_live_fn_check=True)
assert all(abs(a[2] - b[2]) < 1e-12 for a, b in zip(_chk, simulate_real_sched(SCHED[0][2])[0])), \
    'real mirror: W[eff]+vt path differs from target_weights_with_voltarget path'

def header():
    log("=" * 118)
    log("RESEARCH LINE trim_destination_test (2026-09-20): does the extension trim's freed weight belong in SPMO instead of cash?")
    log("=" * 118)
    for line in _buf.getvalue().splitlines():
        if 'proxy' in line or 'harness' in line or 'STANDING' in line: log('  [d_substate_fresh] ' + line.strip())
    log(f"  breadth for the D gate: breadth_tracker on data/QQEW_daily_ext.csv (first value proxy {min(BP_Q)}, real {min(BP_R)}); gate pct < {BT.GATE_PCT}, gap200 < {state.D_GATE_GAP200}")
    log(f"\n  BASELINE = CURRENT live design (A 50/50, trim step 1/3 to cash, vol target 20 %, 5 % band, D gate, E = cash):")
    log(f"    proxy {fmt_ev(LIVE_EV)}  S {LIVE_EV['s_sharpe']:.3f} H {LIVE_EV['h_sharpe']:.3f} exp {LIVE_EV['risky']*100:.1f}% reb {LIVE_EV['reb']:.1f}/yr "
        f"({len(rows)} rows {rows[0]['d']}..{rows[-1]['d']}; gated D days {len(GATE_Q)}, E days {len(E_Q)})")
    log(f"    real daily {fmt_ev(RLIVE_EV)} exp {RLIVE_EV['exp']*100:.1f}% reb {RLIVE_EV['reb']:.1f}/yr ({len(RDAYS)-1} sessions {RDAYS[0]}..{RDAYS[-1]})")
    assert abs(LIVE_EV['cagr'] * 100 - 25.46) < 0.006 and abs(LIVE_EV['sharpe'] - 1.071) < 0.0006 and abs(LIVE_EV['mdd'] * 100 + 27.0) < 0.06, 'proxy baseline != 25.46/1.071/-27.0'
    assert abs(LIVE_EV['s_sharpe'] - 1.399) < 0.0006 and abs(LIVE_EV['h_sharpe'] - 0.825) < 0.0006, 'proxy S/H != 1.399/0.825'
    assert abs(RLIVE_EV['cagr'] * 100 - 37.30) < 0.006 and abs(RLIVE_EV['sharpe'] - 1.475) < 0.0006 and abs(RLIVE_EV['mdd'] * 100 + 18.6) < 0.06, 'real baseline != 37.30/1.475/-18.6'
    log("    BOTH BASELINES REPRODUCED (asserted: proxy 25.46 / 1.071 / -27.0, S 1.399, H 0.825; real 37.30 / 1.475 / -18.6).")
    # vote-count census
    def census(votes, dates_in):
        c = [0, 0, 0, 0]
        for d in dates_in: c[votes[d]] += 1
        return c
    aq = list(VOTES_Q); aS = [d for d in aq if d >= SEARCH[0]]; aH = [d for d in aq if d <= HOLDOUT[1]]
    log(f"\n  EFFECTIVE-A DAYS BY VOTE COUNT (these are the only days any schedule touches; rung 0 is identical in all 7):")
    log(f"  {'':<22}{'A days':>8}{'0 votes':>9}{'1 vote':>9}{'2 votes':>9}{'3 votes':>9}   {'share of A days at 1/2/3':<28} {'of all days':>11}")
    for lab, ds_, tot in (('proxy full', aq, len(rows)), (f'proxy search {SEARCH[0]}+', aS, len(DSF.ERA_S)), ('proxy holdout ..2015-10', aH, len(DSF.ERA_H)),
                          ('real daily 2015-11+', RA_DAYS, len(RDAYS) - 1)):
        c = census(VOTES_Q if lab.startswith('proxy') else VOTES_R, ds_)
        log(f"  {lab:<22}{len(ds_):>8}{c[0]:>9}{c[1]:>9}{c[2]:>9}{c[3]:>9}   {c[1]/len(ds_)*100:5.1f}% / {c[2]/len(ds_)*100:5.1f}% / {c[3]/len(ds_)*100:5.1f}%       {sum(c[1:])/tot*100:5.1f}%")
    log("  (A days here = effective state A after the 20/100 fast overlay, excluding gated-D and E days, which are cash under every schedule.)")

# ---------------------------------------------------------------- exposure-matched controls (flat de-lever of LIVE)
def proxy_control(target_exp):
    base = proxy_fn(0)
    lo, hi = 0.0, 1.0
    while run(rows, scaled(base, hi))[1] < target_exp and hi < 8: lo, hi = hi, hi * 2
    for _ in range(36):
        mid = (lo + hi) / 2
        if run(rows, scaled(base, mid))[1] < target_exp: lo = mid
        else: hi = mid
    k = (lo + hi) / 2
    ev, ser = evaluate_full(scaled(base, k))
    return k, ev, ser
def real_control(target_exp):
    lo, hi = 0.0, 1.0
    while simulate_real_sched(SCHED[0][2], scale=hi)[1] < target_exp and hi < 8: lo, hi = hi, hi * 2
    for _ in range(30):
        mid = (lo + hi) / 2
        if simulate_real_sched(SCHED[0][2], scale=mid)[1] < target_exp: lo = mid
        else: hi = mid
    k = (lo + hi) / 2
    ev, ser = real_eval(SCHED[0][2], scale=k)
    return k, ev, ser

JS_GRID = os.path.join(SCRATCH, 'tdt_grid.json')
JS_PERM = os.path.join(SCRATCH, 'tdt_perm.json')

def stage_grid():
    header()
    log(f"\n{'='*118}\nGRID: the 7 pre-registered schedules (+ no-trim reference). Proxy full / search / holdout, real daily; deltas vs live\n{'='*118}")
    log(f"  {'id':<3} {'rungs (SPMO,TQQQ,cash) at 0/1/2/3 votes':<58} | {'CAGR':>7}{'Sharpe':>7}{'MaxDD':>7}{'exp':>6}{'reb':>6} | S {'CAGR':>7}{'Sh':>6}{'DD':>7} | H {'CAGR':>7}{'Sh':>6}{'DD':>7} | "
        f"{'dS_F':>7}{'dS_S':>7}{'dS_H':>7} | real {'CAGR':>7}{'Sh':>6}{'DD':>7}{'exp':>6}{'reb':>5}{'rdSh':>7}")
    REC = []
    for si, (sid, desc, s) in enumerate(SCHED + [REF_NOTRIM]):
        ev, ser = proxy_eval(si); rev, rser = real_eval(s)
        rec = dict(si=si, id=sid, desc=desc, sched=s, ev=ev, real=rev, ser=ser, rser=rser,
                   dF=ev['sharpe'] - LIVE_EV['sharpe'], dS=ev['s_sharpe'] - LIVE_EV['s_sharpe'], dH=ev['h_sharpe'] - LIVE_EV['h_sharpe'],
                   rd=rev['sharpe'] - RLIVE_EV['sharpe'])
        REC.append(rec)
        log(f"  {sid:<3} {fmt_row(s):<58} | {ev['cagr']*100:>6.2f}%{ev['sharpe']:>7.3f}{ev['mdd']*100:>6.1f}%{ev['risky']*100:>5.1f}%{ev['reb']:>6.1f} | "
            f"{ev['s_cagr']*100:>8.2f}%{ev['s_sharpe']:>6.3f}{ev['s_mdd']*100:>6.1f}% | {ev['h_cagr']*100:>8.2f}%{ev['h_sharpe']:>6.3f}{ev['h_mdd']*100:>6.1f}% | "
            f"{rec['dF']:>+7.3f}{rec['dS']:>+7.3f}{rec['dH']:>+7.3f} | {rev['cagr']*100:>11.2f}%{rev['sharpe']:>6.3f}{rev['mdd']*100:>6.1f}%{rev['exp']*100:>5.1f}%{rev['reb']:>5.1f}{rec['rd']:>+7.3f}")
    log("  descriptions: " + "; ".join(f"{r['id']} = {r['desc']}" for r in REC))
    log("  (REF is not a candidate: it is the same design with the trim switched off, printed so the reader can see where each destination sits between 'no trim' and 'trim to cash'.)")
    assert abs(REC[0]['dF']) < 1e-12 and abs(REC[0]['rd']) < 1e-12
    log(f"  live CAGR deltas (pp) and MaxDD deltas (pp): " + "; ".join(
        f"{r['id']}: proxy {(r['ev']['cagr']-LIVE_EV['cagr'])*100:+.2f} / DD {(r['ev']['mdd']-LIVE_EV['mdd'])*100:+.1f}, real {(r['real']['cagr']-RLIVE_EV['cagr'])*100:+.2f} / DD {(r['real']['mdd']-RLIVE_EV['mdd'])*100:+.1f}" for r in REC[1:7]))
    both = [r for r in REC[1:7] if r['dS'] > 0 and r['dH'] > 0]
    log(f"  both-era (S and H Sharpe both above live): {', '.join(r['id'] for r in both) if both else 'NONE'}; "
        f"real Sharpe above live: {', '.join(r['id'] for r in REC[1:7] if r['rd'] > 0) or 'NONE'}; real CAGR above live: {', '.join(r['id'] for r in REC[1:7] if r['real']['cagr'] > RLIVE_EV['cagr']) or 'NONE'}")

    # ---- exposure-matched controls
    log(f"\n{'='*118}\nEXPOSURE-MATCHED CONTROLS: LIVE flat de-levered (all four risky legs x k every day) to each candidate's average exposure\n{'='*118}")
    log(f"  {'id':<3} | proxy {'exp':>6}{'k':>7}{'ctl Sh':>8}{'ctl S':>7}{'ctl H':>7} | cand-ctl {'F':>7}{'S':>7}{'H':>7} | real {'exp':>6}{'k':>7}{'ctl Sh':>8}{'ctl DD':>7} | cand-ctl {'rSh':>7}")
    for r in REC[1:7]:
        k, cev, cser = proxy_control(r['ev']['risky']); rk, rcev, rcser = real_control(r['real']['exp'])
        r.update(ctl_k=k, ctl=cev, ctl_ser=cser, rctl_k=rk, rctl=rcev, rctl_ser=rcser,
                 vCF=r['ev']['sharpe'] - cev['sharpe'], vCS=r['ev']['s_sharpe'] - cev['s_sharpe'], vCH=r['ev']['h_sharpe'] - cev['h_sharpe'],
                 rvC=r['real']['sharpe'] - rcev['sharpe'])
        log(f"  {r['id']:<3} | {r['ev']['risky']*100:>11.1f}%{k:>7.3f}{cev['sharpe']:>8.3f}{cev['s_sharpe']:>7.3f}{cev['h_sharpe']:>7.3f} | {r['vCF']:>+16.3f}{r['vCS']:>+7.3f}{r['vCH']:>+7.3f} | "
            f"{r['real']['exp']*100:>10.1f}%{rk:>7.3f}{rcev['sharpe']:>8.3f}{rcev['mdd']*100:>6.1f}% | {r['rvC']:>+15.3f}")
    log("  (k > 1 means the candidate holds MORE capital than live; the control then levers live up to match, cash negative on those days is allowed in the harness as in exposure_control().)")
    log("  beats control in both proxy eras: " + (', '.join(r['id'] for r in REC[1:7] if r['vCS'] > 0 and r['vCH'] > 0) or 'NONE') +
        "; beats control on real: " + (', '.join(r['id'] for r in REC[1:7] if r['rvC'] > 0) or 'NONE'))

    # ---- per-rung attribution: what does each destination earn on the days of each vote level? (descriptive)
    log(f"\n{'='*118}\nPER-RUNG ATTRIBUTION (descriptive): mean next-session return of the SPMO/core leg and of TQQQ on A days by vote count; cash for reference\n{'='*118}")
    log(f"  {'harness':<26}{'votes':>6}{'n':>6}{'core bp/d':>11}{'t':>6}{'TQQQ bp/d':>11}{'t':>6}{'cash bp/d':>10}{'core-cash t':>12}")
    def tst(x):
        n = len(x)
        if n < 3: return float('nan')
        m = statistics.mean(x); sd = statistics.stdev(x)
        return m / (sd / math.sqrt(n)) if sd > 0 else float('nan')
    for hname, ds_, votes, getret in (('proxy full', list(VOTES_Q), VOTES_Q, lambda d: PLEG[d]), (f'proxy search {SEARCH[0]}+', [d for d in VOTES_Q if d >= SEARCH[0]], VOTES_Q, lambda d: PLEG[d]),
                                       ('proxy holdout', [d for d in VOTES_Q if d <= HOLDOUT[1]], VOTES_Q, lambda d: PLEG[d]), ('real daily', RA_DAYS, VOTES_R, lambda d: RLEG_RET[d])):
        for v in range(4):
            dd = [d for d in ds_ if votes[d] == v]
            if not dd: continue
            core = [getret(d)[0] for d in dd]; tq = [getret(d)[1] for d in dd]; ca = [getret(d)[4] for d in dd]
            log(f"  {hname:<26}{v:>6}{len(dd):>6}{statistics.mean(core)*1e4:>11.1f}{tst(core):>6.2f}{statistics.mean(tq)*1e4:>11.1f}{tst(tq):>6.2f}{statistics.mean(ca)*1e4:>10.1f}{tst([c-x for c,x in zip(core,ca)]):>12.2f}")
    log("  (proxy core = QQQ total-return leg, TQQQ = synthetic 3x; real core = SPMO. Positive core-minus-cash at 1-3 votes is what any SPMO destination needs.)")

    json.dump([dict((k, v) for k, v in r.items() if k not in ('ser', 'rser', 'ctl_ser', 'rctl_ser')) for r in REC], open(JS_GRID, 'w'))
    # series for the deep stage
    json.dump({r['id']: dict(ser=r['ser'], rser=r['rser'], ctl_ser=r.get('ctl_ser'), rctl_ser=r.get('rctl_ser')) for r in REC}, open(os.path.join(SCRATCH, 'tdt_series.json'), 'w'))
    log(f"\n  [grid done in {time.time()-T0:.0f} s]")
    return REC
PLEG = {r['d']: r['legs'] for r in rows}

# ---------------------------------------------------------------- permutation (proxy; vote labels shuffled among effective-A days, counts kept)
def _perm_worker(args):
    seed, n = args
    rng = random.Random(seed)
    a_dates = [rows[i]['d'] for i in A_IDX]
    labels = [VOTES_Q[d] for d in a_dates]
    out = []
    for _ in range(n):
        rng.shuffle(labels)
        pv = dict(zip(a_dates, labels))
        lser = run(rows, proxy_fn(0, pv))[0]
        lF = bstats(lser)[1]; lS = sliced_sharpe(lser, *SEARCH); lH = sliced_sharpe(lser, *HOLDOUT)
        bestF = bestB = bestF_unp = -9.0
        for si in range(1, 7):
            ser = run(rows, proxy_fn(si, pv))[0]
            F = bstats(ser)[1]; S = sliced_sharpe(ser, *SEARCH); H = sliced_sharpe(ser, *HOLDOUT)
            bestF = max(bestF, F - lF); bestB = max(bestB, min(S - lS, H - lH)); bestF_unp = max(bestF_unp, F - LIVE_F)
        out.append((bestF, bestB, bestF_unp))
    return out
LIVE_F = bstats(LIVE_SER)[1]; LIVE_S_SL = sliced_sharpe(LIVE_SER, *SEARCH); LIVE_H_SL = sliced_sharpe(LIVE_SER, *HOLDOUT)

def stage_perm():
    import multiprocessing as mp
    log(f"\n{'='*118}\nMAX-STATISTIC PERMUTATION over the 6 candidates: vote labels shuffled among effective-A days (counts kept), {N_PERM} draws, proxy\n{'='*118}")
    log("  Statistic per draw: max over S1..S6 of (candidate Sharpe - live Sharpe), BOTH evaluated on the same shuffled labels (paired null:")
    log("  'the vote label carries no information about whether the freed weight does better in SPMO or in cash'). Full-period gain, and")
    log("  both-era gain = min(dS_search, dS_holdout) with sliced Sharpes (as d_pair_test). Also the r2-precedent unpaired form (candidate")
    log("  under shuffled labels minus the FIXED real live Sharpe), for reference only.")
    real = []
    for si in range(1, 7):
        ser = run(rows, proxy_fn(si))[0]
        real.append((bstats(ser)[1] - LIVE_F, min(sliced_sharpe(ser, *SEARCH) - LIVE_S_SL, sliced_sharpe(ser, *HOLDOUT) - LIVE_H_SL), SCHED[si][0]))
    realF = max(real, key=lambda x: x[0]); realB = max(real, key=lambda x: x[1])
    per = max(1, N_PERM // (N_PROCS * 4))
    chunks = []; left = N_PERM; k = 0
    while left > 0:
        n = min(per, left); chunks.append((SEED + k, n)); left -= n; k += 1
    with mp.Pool(N_PROCS) as pool:
        res = [x for part in pool.map(_perm_worker, chunks) for x in part]
    nullF = sorted(x[0] for x in res); nullB = sorted(x[1] for x in res); nullU = sorted(x[2] for x in res)
    def q(v, p): return v[min(len(v) - 1, int(p * len(v)))]
    pF = sum(1 for x in nullF if x >= realF[0]) / len(nullF); pB = sum(1 for x in nullB if x >= realB[1]) / len(nullB)
    pU = sum(1 for x in nullU if x >= realF[0]) / len(nullU)
    log(f"  real best full-period gain vs live: {realF[0]:+.3f} ({realF[2]}); null median {q(nullF,.5):+.3f}, 95th {q(nullF,.95):+.3f}, 99th {q(nullF,.99):+.3f} -> p = {pF:.3f}")
    log(f"  real best both-era min gain vs live: {realB[1]:+.3f} ({realB[2]}); null median {q(nullB,.5):+.3f}, 95th {q(nullB,.95):+.3f}, 99th {q(nullB,.99):+.3f} -> p = {pB:.3f}")
    log(f"  (unpaired r2-style, full period: null 95th {q(nullU,.95):+.3f} -> p = {pU:.3f})")
    # lower tail: if the real best sits BELOW the null, the vote days are days on which SPMO does WORSE relative to cash
    # than random A days do, i.e. the label is informative in the direction that favours cash as the destination.
    loF = sum(1 for x in nullF if x <= realF[0]) / len(nullF); loB = sum(1 for x in nullB if x <= realB[1]) / len(nullB)
    log(f"  lower tail: null full-period min {nullF[0]:+.3f}, 1st pct {q(nullF,.01):+.3f}, 5th {q(nullF,.05):+.3f}; draws <= real best {loF:.3f}. "
        f"both-era: min {nullB[0]:+.3f}, 1st {q(nullB,.01):+.3f}, 5th {q(nullB,.05):+.3f}; draws <= real best {loB:.3f}.")
    log("  (Reading: under the null the best SPMO destination beats trim-to-cash by the null median simply because random A days earn the core's drift;")
    log("   the real gain being far below that says the actual vote days are days on which the core does NOT earn it -- the label is informative,")
    log("   and in the direction that favours cash.)")
    log("  per-candidate real gains (F, both-era min): " + "; ".join(f"{c}: {f:+.3f} / {b:+.3f}" for f, b, c in real))
    json.dump(dict(realF=realF, realB=realB, pF=pF, pB=pB, pU=pU, nullF95=q(nullF, .95), nullB95=q(nullB, .95), n=len(res)), open(JS_PERM, 'w'))
    log(f"  [perm done in {time.time()-T0:.0f} s]")

# ---------------------------------------------------------------- deep block for the best candidate(s)
def _boot_worker(args):
    lab, a, b, blk, seed = args
    return lab, blk, boot(a, b, blk, seed)

def stage_deep():
    import multiprocessing as mp
    REC = json.load(open(JS_GRID)); SERS = json.load(open(os.path.join(SCRATCH, 'tdt_series.json')))
    for r in REC:
        r.update(SERS[r['id']])
    cands = REC[1:7]
    best = max(cands, key=lambda r: r['ev']['sharpe'])
    best_real = max(cands, key=lambda r: r['real']['sharpe'])
    best_both = max(cands, key=lambda r: min(r['dS'], r['dH']))
    log(f"\n{'='*118}\nDEEP BLOCK. best by proxy full Sharpe: {best['id']}; best by real Sharpe: {best_real['id']}; best by both-era min gain: {best_both['id']}\n{'='*118}")
    todo = [best] + ([best_real] if best_real['id'] != best['id'] else []) + ([best_both] if best_both['id'] not in (best['id'], best_real['id']) else [])
    for rec in todo:
        si = rec['si']; s = SCHED[si][2]
        log(f"\n{'-'*118}\nDEEP {rec['id']} ({rec['desc']}): proxy {fmt_ev(rec['ev'])} S {rec['ev']['s_sharpe']:.3f} H {rec['ev']['h_sharpe']:.3f} exp {rec['ev']['risky']*100:.1f}% | "
            f"real {fmt_ev(rec['real'])} exp {rec['real']['exp']*100:.1f}% | control k {rec['ctl_k']:.3f} (proxy) {rec['rctl_k']:.3f} (real)")
        log(f"  (a) circular block bootstrap (2000 draws) of the Sharpe / log-return difference:")
        jobs = []
        for lab, a, b in (('proxy vs live', rec['ser'], LIVE_SER), ('proxy vs matched control', rec['ser'], rec['ctl_ser']),
                          ('real daily vs live', rec['rser'], RLIVE_SER), ('real daily vs matched control', rec['rser'], rec['rctl_ser'])):
            for blk in (20, 60):
                jobs.append((lab, a, b, blk, (si * 7919 + blk + len(lab)) & 0xffff))
        with mp.Pool(min(N_PROCS, len(jobs))) as pool:
            res = pool.map(_boot_worker, jobs)
        for lab, blk, (l1, l2, pl, s1, s2, ps) in res:
            log(f"      {lab:<32} block {blk:>2}d: Sharpe 95% CI [{s1:+.3f}, {s2:+.3f}] P(<=0)={ps:.3f}   log-return [{l1*100:+.2f}, {l2*100:+.2f}] pp/yr P(<=0)={pl:.3f}")
        log(f"  (b) leave-one-major-regime-out (Sharpe difference vs live / vs matched control with that window removed; proxy, and real where the window overlaps):")
        for rlab, a0, b0 in REGIMES:
            keep = [i for i, d in enumerate(PDATES) if not (a0 <= d <= b0)]
            sa = bstats([rec['ser'][i] for i in keep])[1]; sl = bstats([LIVE_SER[i] for i in keep])[1]; sc = bstats([rec['ctl_ser'][i] for i in keep])[1]
            rk = [i for i, d in enumerate(RD1) if not (a0 <= d <= b0)]
            rtxt = ''
            if len(rk) > 252 and len(rk) < len(RD1):
                ra = bstats([rec['rser'][i] for i in rk])[1]; rl = bstats([RLIVE_SER[i] for i in rk])[1]; rc = bstats([rec['rctl_ser'][i] for i in rk])[1]
                rtxt = f"   | real: vs live {ra-rl:+.3f}, vs control {ra-rc:+.3f}"
            log(f"      drop {rlab:<26} proxy: vs live {sa-sl:+.3f}, vs control {sa-sc:+.3f}{rtxt}")
        # (c) one-session lag of the vote count (destination AND depth read from the previous close), applied to candidate and to live
        lagQ = {}
        for j, i in enumerate(A_IDX):
            d = rows[i]['d']; dp = rows[i - 1]['d'] if i > 0 else None
            lagQ[d] = VOTES_Q.get(dp, 0) if dp is not None else 0
        lagR = {}
        for j, d in enumerate(RDAYS[:-1]):
            if d in VOTES_R:
                dp = RDAYS[j - 1] if j > 0 else None
                lagR[d] = VOTES_R.get(dp, 0) if dp is not None else 0
        evL, _ = proxy_eval(si, lagQ); lvL, _ = proxy_eval(0, lagQ); revL, _ = real_eval(s, votes=lagR); rlvL, _ = real_eval(SCHED[0][2], votes=lagR)
        log(f"  (c) one-extra-session lag (vote count from the previous close, for candidate AND live):")
        log(f"      live lagged  proxy {fmt_ev(lvL)} S {lvL['s_sharpe']:.3f} H {lvL['h_sharpe']:.3f} | real {fmt_ev(rlvL)}")
        log(f"      {rec['id']} lagged   proxy {fmt_ev(evL)} S {evL['s_sharpe']:.3f} H {evL['h_sharpe']:.3f} | real {fmt_ev(revL)}")
        log(f"      {rec['id']} lagged vs live lagged: F {evL['sharpe']-lvL['sharpe']:+.3f} S {evL['s_sharpe']-lvL['s_sharpe']:+.3f} H {evL['h_sharpe']-lvL['h_sharpe']:+.3f} real {revL['sharpe']-rlvL['sharpe']:+.3f}; "
            f"vs UNLAGGED live (d_pair_test convention): F {evL['sharpe']-LIVE_EV['sharpe']:+.3f} S {evL['s_sharpe']-LIVE_EV['s_sharpe']:+.3f} H {evL['h_sharpe']-LIVE_EV['h_sharpe']:+.3f} real {revL['sharpe']-RLIVE_EV['sharpe']:+.3f}")
        # (d) 20 bp one-way cost
        DSF.ONE_WAY_SPREAD = IS.ONE_WAY_SPREAD = 0.002
        try:
            l20, _ = proxy_eval(0); c20, _ = proxy_eval(si)
            k20, ctl20, _ = proxy_control(c20['risky'])
        finally:
            DSF.ONE_WAY_SPREAD = IS.ONE_WAY_SPREAD = 0.0004
        rl20, _ = real_eval(SCHED[0][2], one_way=0.002); rc20, _ = real_eval(s, one_way=0.002)
        log(f"  (d) 20 bp one-way cost (both sides): live proxy {fmt_ev(l20)} S {l20['s_sharpe']:.3f} H {l20['h_sharpe']:.3f}; {rec['id']} {fmt_ev(c20)} S {c20['s_sharpe']:.3f} H {c20['h_sharpe']:.3f} "
            f"(vs live F {c20['sharpe']-l20['sharpe']:+.3f} S {c20['s_sharpe']-l20['s_sharpe']:+.3f} H {c20['h_sharpe']-l20['h_sharpe']:+.3f}; vs matched control at 20 bp F {c20['sharpe']-ctl20['sharpe']:+.3f} S {c20['s_sharpe']-ctl20['s_sharpe']:+.3f} H {c20['h_sharpe']-ctl20['h_sharpe']:+.3f})")
        log(f"      real: live {fmt_ev(rl20)} {rec['id']} {fmt_ev(rc20)} ({rc20['sharpe']-rl20['sharpe']:+.3f})")
    # ---- per-year
    top2 = sorted(cands, key=lambda r: -r['ev']['sharpe'])[:2]
    log(f"\n{'='*118}\nPER-YEAR RETURNS: live vs the best two by proxy full Sharpe ({top2[0]['id']}, {top2[1]['id']}); no-trim reference alongside\n{'='*118}")
    ref = REC[7]
    COST_Y = {'2003', '2009', '2020', '2023', '2024', '2026'}; PAY_Y = {'2007', '2010', '2011', '2018', '2020', '2024', '2025', '2026'}
    for hname, dates, lser, rser0 in (('PROXY (QQQ core)', PDATES, LIVE_SER, 'ser'), ('REAL DAILY (SPMO era)', RD1, RLIVE_SER, 'rser')):
        yl = byyear(lser, dates); ys = [byyear(r[rser0], dates) for r in top2]; yr = byyear(ref[rser0], dates)
        log(f"  {hname}: year, live, {top2[0]['id']}, {top2[1]['id']}, no-trim ref; deltas vs live in pp; tag = STRATEGY.md 'trim costs' (C) / 'trim pays' (P) year")
        log(f"  {'year':<6}{'live':>8}{top2[0]['id']:>8}{top2[1]['id']:>8}{'ref':>8} | {'d'+top2[0]['id']:>8}{'d'+top2[1]['id']:>8}{'dref':>8}  tag")
        for y in sorted(yl):
            tag = ('C' if y in COST_Y else '') + ('P' if y in PAY_Y else '')
            log(f"  {y:<6}{yl[y]*100:>+8.1f}{ys[0][y]*100:>+8.1f}{ys[1][y]*100:>+8.1f}{yr[y]*100:>+8.1f} | {(ys[0][y]-yl[y])*100:>+8.1f}{(ys[1][y]-yl[y])*100:>+8.1f}{(yr[y]-yl[y])*100:>+8.1f}  {tag}")
        for lab, yy in (('trim-cost years', COST_Y), ('trim-pay years', PAY_Y)):
            ks = [y for y in sorted(yl) if y in yy]
            log(f"    sum over {lab} present ({', '.join(ks)}): " + "; ".join(f"{r['id']} {sum((ys[j][y]-yl[y]) for y in ks)*100:+.1f} pp" for j, r in enumerate(top2)) + f"; ref {sum((yr[y]-yl[y]) for y in ks)*100:+.1f} pp")
    # ---- verdict card against the project bar
    log(f"\n{'='*118}\nPROJECT BAR, per candidate: both-era improvement | beats matched control (S and H) | real Sharpe up | real CAGR not down\n{'='*118}")
    for r in cands:
        log(f"  {r['id']}: both-era {'PASS' if r['dS']>0 and r['dH']>0 else 'fail'} (dS {r['dS']:+.3f}, dH {r['dH']:+.3f}) | control {'PASS' if r['vCS']>0 and r['vCH']>0 else 'fail'} (vC S {r['vCS']:+.3f}, H {r['vCH']:+.3f}, F {r['vCF']:+.3f}; real vC {r['rvC']:+.3f}) | "
            f"real Sharpe {r['rd']:+.3f} | real CAGR {(r['real']['cagr']-RLIVE_EV['cagr'])*100:+.2f} pp | proxy MaxDD {(r['ev']['mdd']-LIVE_EV['mdd'])*100:+.1f} pp, real MaxDD {(r['real']['mdd']-RLIVE_EV['mdd'])*100:+.1f} pp")
    if os.path.exists(JS_PERM):
        P = json.load(open(JS_PERM))
        log(f"  permutation (proxy, {P['n']} draws): full-period best {P['realF'][0]:+.3f} ({P['realF'][2]}) p = {P['pF']:.3f} (null 95th {P['nullF95']:+.3f}); both-era best {P['realB'][1]:+.3f} ({P['realB'][2]}) p = {P['pB']:.3f} (null 95th {P['nullB95']:+.3f})")
    log(f"\n  candidate count this line: 6 pre-registered + live + 1 labelled reference (no-trim) + 6 exposure-matched controls. Nothing applied; owner decides.")
    log(f"  [deep done in {time.time()-T0:.0f} s]")

# ================================================================================================================
# PART II (owner follow-up, pre-registered 2026-09-20 before any Part II number was seen): S6 ANATOMY.
#   S6 = A row 100/0/0 at 1 vote, 50/0/50 at 2, cash at 3. Grid fixed in advance and reported in full:
#   1. decomposition S6a (only the 1-vote rung changed) / S6b (only the 2-vote rung changed);
#   2. 5 x 5 neighbour grid (1-vote row x 2-vote row, 3-vote row = cash; one cell is live, one is S6), each with its
#      exposure-matched control; paired max-stat permutation over the 24 non-live cells, both-era-min gain vs live and
#      vs matched control (control under the shuffle = live-shuffled scaled by the cell's real-label k);
#   3. threshold shifts -2..+2 pp on all three windows, S6 minus live;
#   4. attribution by extension episode / year / drawdown window;  5. per-vote-level leg returns by era with t;
#   6. trading (rebalances, turnover, regime changes; lag and 20 bp for S6a, S6b);  7. bootstrap S6a / S6b / S6;
#   8. verdict.  Run: TDT_STAGE=part2 (appends to the log).
# ================================================================================================================
S6 = SCHED[6][2]
S6A = [(.5, .5, 0), (1, 0, 0), (1 / 6, 1 / 6, 2 / 3), (0, 0, 1)]
S6B = [(.5, .5, 0), (F3, F3, F3), (.5, 0, .5), (0, 0, 1)]
ROW1 = [('100/0/0', (1, 0, 0)), ('75/0/25', (.75, 0, .25)), ('50/0/50', (.5, 0, .5)), ('75/25/0', (.75, .25, 0)), ('live 33/33/33', (F3, F3, F3))]
ROW2 = [('50/0/50', (.5, 0, .5)), ('75/0/25', (.75, 0, .25)), ('25/0/75', (.25, 0, .75)), ('0/0/100', (0, 0, 1)), ('live 17/17/67', (1 / 6, 1 / 6, 2 / 3))]
NB = [(f"{l1} x {l2}", [(.5, .5, 0), r1, r2, (0, 0, 1)]) for l1, r1 in ROW1 for l2, r2 in ROW2]
RULES3 = ((100, 0.10), (150, 0.12), (200, 0.15))
assert state.EXTENSION_RULES == RULES3

def make_AT(s):
    return {rows[i]['d']: [vt(srow(s, v), rows[i]['vol']) for v in range(4)] for i in A_IDX}
def pfn(AT, votes=VOTES_Q):
    def fn(r):
        d = r['d']
        if d in votes: return AT[d][votes[d]]
        return OTHER_Q[d]
    return fn
def peval(s, votes=VOTES_Q):
    return evaluate_full(pfn(make_AT(s), votes))
def pctl(s_ev_risky):
    return proxy_control(s_ev_risky)

def run_held(rs, wfn, band=state.REBALANCE_DRIFT_BAND):
    """run_count() with per-row held weights, traded L1 turnover and regime-change count (diagnostics; asserted equal)."""
    held = prev = None; rets, helds, turn, nreg = [], [], 0.0, 0
    for r in rs:
        t = wfn(r); key = (r['state'], r['agree']); cost = 0.0
        if held is None: held = list(t); turn += 1.0
        else:
            drift = sum(abs(t[j] - held[j]) for j in range(5))
            if key != prev: nreg += 1
            if key != prev or drift > band:
                cost = DSF.ONE_WAY_SPREAD * drift; held = list(t); turn += drift
        helds.append(tuple(held))
        g = sum(held[j] * r['legs'][j] for j in range(5)); rets.append(g - cost)
        dn = 1 + g
        if dn > 0: held = [held[j] * (1 + r['legs'][j]) / dn for j in range(5)]
        prev = key
    return rets, helds, turn / len(rs), nreg / (len(rs) / 252.0)

def simulate_real_detail(sched, votes=VOTES_R, one_way=None):
    """simulate_real_sched with per-session held weights, traded turnover/session and regime changes/yr."""
    ow = MR.ONE_WAY if one_way is None else one_way
    held = prev = None; out = []; helds = []; turn = 0.0; nreg = 0; nreb = 0
    for i in range(1, len(RDAYS)):
        d0 = RDAYS[i - 1]; I = RINFO[d0]; st, eff, gate = I['st'], I['eff'], I['gate']
        if gate or st == 'E': v = 0; t = CASH
        elif d0 in votes: v = votes[d0]; t = RF.vt(srow(sched, v), I['vol'])
        else: v = 0; t = RF.vt(W[eff], I['vol'])
        stk = (eff, v, gate); cost = 0.0
        if held is None: held = list(t); nreb += 1; turn += 1.0
        else:
            if stk != prev: nreg += 1
            do, drift, _ = needs_rebalance(t, held, stk != prev)
            if do: cost = ow * drift; held = list(t); nreb += 1; turn += drift
        helds.append(tuple(held))
        r = RLEG_RET[d0]; g = sum(held[j] * r[j] for j in range(5)); out.append(g - cost)
        dn = 1 + g
        if dn > 0: held = [held[j] * (1 + r[j]) / dn for j in range(5)]
        prev = stk
    n = len(out)
    return out, helds, turn / n, nreg / (n / 252.0), nreb / (n / 252.0)

def dd_window(ser, dates):
    """(peak date, trough date, recovery date or None, maxdd) of the NAV path."""
    nav = 1.0; peak = 1.0; pk_i = 0; best = (0.0, 0, 0)
    navs = []
    for i, x in enumerate(ser):
        nav *= 1 + x; navs.append(nav)
        if nav > peak: peak = nav; pk_i = i
        dd = nav / peak - 1
        if dd < best[0]: best = (dd, pk_i, i)
    dd, a, b = best
    rec = next((dates[j] for j in range(b, len(navs)) if navs[j] >= navs[a]), None)
    return dates[a], dates[b], rec, dd, a, b

def tst(x):
    n = len(x)
    if n < 3: return float('nan')
    m = statistics.mean(x); sd = statistics.stdev(x)
    return m / (sd / math.sqrt(n)) if sd > 0 else float('nan')

def votes_shift(gaps, shift_pp):
    return sum(1 for n, t in RULES3 if gaps.get(n) is not None and gaps[n] > t + shift_pp / 100.0)

def episodes_of(idx_list, votes_by_pos):
    """runs of consecutive positions with >= 1 vote: list of (start_pos, end_pos)."""
    out = []; cur = None
    for p, v in zip(idx_list, votes_by_pos):
        if v >= 1:
            if cur is not None and p == cur[1] + 1: cur[1] = p
            else:
                if cur: out.append(tuple(cur))
                cur = [p, p]
        else:
            if cur: out.append(tuple(cur)); cur = None
    if cur: out.append(tuple(cur))
    return out

NB_AT = {}; NB_K = {}
def _perm2_worker(args):
    seed, n = args
    rng = random.Random(seed)
    a_dates = [rows[i]['d'] for i in A_IDX]; labels = [VOTES_Q[d] for d in a_dates]
    out = []
    for _ in range(n):
        rng.shuffle(labels); pv = dict(zip(a_dates, labels))
        lfn = pfn(NB_AT['live'], pv); lser = run(rows, lfn)[0]
        lS = sliced_sharpe(lser, *SEARCH); lH = sliced_sharpe(lser, *HOLDOUT)
        bL = bC = -9.0
        for lab, _ in NB:
            if lab in NB_K and NB_K[lab] is None: continue      # live cell
            ser = run(rows, pfn(NB_AT[lab], pv))[0]
            S = sliced_sharpe(ser, *SEARCH); H = sliced_sharpe(ser, *HOLDOUT)
            bL = max(bL, min(S - lS, H - lH))
            cser = run(rows, scaled(lfn, NB_K[lab]))[0]
            bC = max(bC, min(S - sliced_sharpe(cser, *SEARCH), H - sliced_sharpe(cser, *HOLDOUT)))
        out.append((bL, bC))
    return out

def lag_votes():
    lagQ = {}
    for i in A_IDX:
        dp = rows[i - 1]['d'] if i > 0 else None
        lagQ[rows[i]['d']] = VOTES_Q.get(dp, 0) if dp is not None else 0
    lagR = {}
    for j, d in enumerate(RDAYS[:-1]):
        if d in VOTES_R:
            dp = RDAYS[j - 1] if j > 0 else None
            lagR[d] = VOTES_R.get(dp, 0) if dp is not None else 0
    return lagQ, lagR

def stage_part2():
    import multiprocessing as mp
    log(f"\n\n{'#'*118}\nPART II: S6 ANATOMY (owner follow-up, pre-registered; everything reported, not the best rows). S6 = 100/0/0 at 1 vote, 50/0/50 at 2, cash at 3.\n{'#'*118}")
    live_ev, live_ser = LIVE_EV, LIVE_SER; rlive_ev, rlive_ser = RLIVE_EV, RLIVE_SER
    # ---------------------------------------------------------------- II.1 decomposition
    log(f"\n{'='*118}\nII.1  DECOMPOSITION: S6a (only the 1-vote rung -> 100/0/0), S6b (only the 2-vote rung -> 50/0/50), S6 (both)\n{'='*118}")
    log(f"  {'id':<4}{'rungs 1/2/3':<40} | {'CAGR':>7}{'Sharpe':>7}{'MaxDD':>7}{'exp':>6} | {'S Sh':>6}{'S DD':>7}{'H Sh':>6}{'H DD':>7} | {'dF':>7}{'dS':>7}{'dH':>7} | ctl {'k':>6}{'vC F':>7}{'vC S':>7}{'vC H':>7} | real {'CAGR':>7}{'Sh':>6}{'DD':>7}{'exp':>6}{'rdSh':>7}{'rk':>6}{'rvC':>7}")
    DEC = {}
    for lab, s in (('S6a', S6A), ('S6b', S6B), ('S6', S6)):
        ev, ser = peval(s); rev, rser = real_eval(s)
        k, cev, cser = proxy_control(ev['risky']); rk, rcev, rcser = real_control(rev['exp'])
        DEC[lab] = dict(s=s, ev=ev, ser=ser, rev=rev, rser=rser, k=k, cev=cev, cser=cser, rk=rk, rcev=rcev, rcser=rcser)
        log(f"  {lab:<4}{fmt_row(s)[10:]:<40} | {ev['cagr']*100:>6.2f}%{ev['sharpe']:>7.3f}{ev['mdd']*100:>6.1f}%{ev['risky']*100:>5.1f}% | {ev['s_sharpe']:>6.3f}{ev['s_mdd']*100:>6.1f}%{ev['h_sharpe']:>6.3f}{ev['h_mdd']*100:>6.1f}% | "
            f"{ev['sharpe']-live_ev['sharpe']:>+7.3f}{ev['s_sharpe']-live_ev['s_sharpe']:>+7.3f}{ev['h_sharpe']-live_ev['h_sharpe']:>+7.3f} | {k:>10.3f}{ev['sharpe']-cev['sharpe']:>+7.3f}{ev['s_sharpe']-cev['s_sharpe']:>+7.3f}{ev['h_sharpe']-cev['h_sharpe']:>+7.3f} | "
            f"{rev['cagr']*100:>11.2f}%{rev['sharpe']:>6.3f}{rev['mdd']*100:>6.1f}%{rev['exp']*100:>5.1f}%{rev['sharpe']-rlive_ev['sharpe']:>+7.3f}{rk:>6.3f}{rev['sharpe']-rcev['sharpe']:>+7.3f}")
    log(f"  live: proxy {fmt_ev(live_ev)} S {live_ev['s_sharpe']:.3f} H {live_ev['h_sharpe']:.3f} exp {live_ev['risky']*100:.1f}% | real {fmt_ev(rlive_ev)} exp {rlive_ev['exp']*100:.1f}%")
    a, b, c = DEC['S6a']['ev']['sharpe'] - live_ev['sharpe'], DEC['S6b']['ev']['sharpe'] - live_ev['sharpe'], DEC['S6']['ev']['sharpe'] - live_ev['sharpe']
    log(f"  additivity (proxy full): S6a {a:+.4f} + S6b {b:+.4f} = {a+b:+.4f} vs S6 {c:+.4f}; real: {DEC['S6a']['rev']['sharpe']-rlive_ev['sharpe']:+.4f} + {DEC['S6b']['rev']['sharpe']-rlive_ev['sharpe']:+.4f} vs {DEC['S6']['rev']['sharpe']-rlive_ev['sharpe']:+.4f}")

    # ---------------------------------------------------------------- II.2 neighbour grid
    log(f"\n{'='*118}\nII.2  NEIGHBOUR GRID: 1-vote row x 2-vote row (3-vote row = cash), 25 cells; each with its exposure-matched control (proxy F/S/H; real)\n{'='*118}")
    log(f"  {'#':>2} {'1-vote x 2-vote':<30} | {'Sharpe':>7}{'S':>7}{'H':>7}{'MaxDD':>7}{'exp':>6} | {'dF':>7}{'dS':>7}{'dH':>7} | ctl {'k':>6}{'F':>7}{'S':>7}{'H':>7} | {'vC S':>7}{'vC H':>7} | real {'Sh':>6}{'DD':>7}{'exp':>6}{'rdSh':>7}{'rvC':>7} | both-era? ctl?")
    GRID = []
    for j, (lab, s) in enumerate(NB):
        is_live = (s[1] == (F3, F3, F3) and s[2] == (1 / 6, 1 / 6, 2 / 3))
        AT = make_AT(s); NB_AT[lab] = AT
        ev, ser = evaluate_full(pfn(AT)); rev, rser = real_eval(s)
        if is_live:
            NB_AT['live'] = AT; NB_K[lab] = None; k, cev = 1.0, ev; rk, rcev = 1.0, rev
        else:
            k, cev, _ = proxy_control(ev['risky']); rk, rcev, _ = real_control(rev['exp']); NB_K[lab] = k
        g = dict(j=j, lab=lab, s=s, ev=ev, rev=rev, k=k, cev=cev, rk=rk, rcev=rcev, live=is_live,
                 dF=ev['sharpe'] - live_ev['sharpe'], dS=ev['s_sharpe'] - live_ev['s_sharpe'], dH=ev['h_sharpe'] - live_ev['h_sharpe'],
                 vCS=ev['s_sharpe'] - cev['s_sharpe'], vCH=ev['h_sharpe'] - cev['h_sharpe'], rd=rev['sharpe'] - rlive_ev['sharpe'], rvC=rev['sharpe'] - rcev['sharpe'])
        GRID.append(g)
        tag = ('LIVE' if is_live else ('S6' if s == S6 else ''))
        log(f"  {j:>2} {lab:<30} | {ev['sharpe']:>7.3f}{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f}{ev['mdd']*100:>6.1f}%{ev['risky']*100:>5.1f}% | {g['dF']:>+7.3f}{g['dS']:>+7.3f}{g['dH']:>+7.3f} | "
            f"{k:>10.3f}{cev['sharpe']:>7.3f}{cev['s_sharpe']:>7.3f}{cev['h_sharpe']:>7.3f} | {g['vCS']:>+7.3f}{g['vCH']:>+7.3f} | {rev['sharpe']:>11.3f}{rev['mdd']*100:>6.1f}%{rev['exp']*100:>5.1f}%{g['rd']:>+7.3f}{g['rvC']:>+7.3f} | "
            f"{'Y' if g['dS']>0 and g['dH']>0 else '-':>5} {'Y' if g['vCS']>0 and g['vCH']>0 else '-':>4}  {tag}")
    nb_ok = [g for g in GRID if not g['live'] and g['dS'] > 0 and g['dH'] > 0]
    nb_ok_c = [g for g in nb_ok if g['vCS'] > 0 and g['vCH'] > 0]
    nb_real = [g for g in GRID if not g['live'] and g['rd'] > 0]
    log(f"  cells above live in both eras: {len(nb_ok)}/24 ({', '.join(g['lab'] for g in nb_ok) or 'none'}); of those also above their control in both eras: {len(nb_ok_c)} "
        f"({', '.join(g['lab'] for g in nb_ok_c) or 'none'}); above live on real: {len(nb_real)} ({', '.join(g['lab'] for g in nb_real) or 'none'})")
    # marginal means by row
    log("  marginal mean dF by 1-vote row: " + "; ".join(f"{l1}: {statistics.mean([g['dF'] for g in GRID if g['lab'].startswith(l1 + ' x')]):+.3f}" for l1, _ in ROW1))
    log("  marginal mean dF by 2-vote row: " + "; ".join(f"{l2}: {statistics.mean([g['dF'] for g in GRID if g['lab'].endswith('x ' + l2)]):+.3f}" for l2, _ in ROW2))
    # permutation over the 24
    log(f"\n  MAX-STAT PERMUTATION over the 24 non-live cells ({N_PERM} paired draws; vote labels shuffled among effective-A days, counts kept; live and every cell")
    log(f"  re-scored on the same labels; control under the shuffle = live-shuffled x the cell's real-label k). Statistic: max over cells of min(dS_search, dS_holdout).")
    realL = max(((min(g['dS'], g['dH']), g['lab']) for g in GRID if not g['live']))
    realC = max(((min(g['vCS'], g['vCH']), g['lab']) for g in GRID if not g['live']))
    per = max(1, N_PERM // (N_PROCS * 4)); chunks = []; left = N_PERM; kk = 0
    while left > 0:
        n = min(per, left); chunks.append((SEED + 1000 + kk, n)); left -= n; kk += 1
    with mp.Pool(N_PROCS) as pool:
        res = [x for part in pool.map(_perm2_worker, chunks) for x in part]
    nL = sorted(x[0] for x in res); nC = sorted(x[1] for x in res)
    def q(v, p): return v[min(len(v) - 1, int(p * len(v)))]
    pL = sum(1 for x in nL if x >= realL[0]) / len(nL); pC = sum(1 for x in nC if x >= realC[0]) / len(nC)
    log(f"  vs live:    null median {q(nL,.5):+.3f}, 95th {q(nL,.95):+.3f}, min {nL[0]:+.3f}; real best {realL[0]:+.3f} ({realL[1]}) -> p = {pL:.3f}; draws <= real {sum(1 for x in nL if x <= realL[0])/len(nL):.3f}")
    log(f"  vs control: null median {q(nC,.5):+.3f}, 95th {q(nC,.95):+.3f}, min {nC[0]:+.3f}; real best {realC[0]:+.3f} ({realC[1]}) -> p = {pC:.3f}; draws <= real {sum(1 for x in nC if x <= realC[0])/len(nC):.3f}")
    PERM2 = dict(realL=realL, realC=realC, pL=pL, pC=pC, n95L=q(nL, .95), n95C=q(nC, .95))

    # ---------------------------------------------------------------- II.3 threshold shifts
    log(f"\n{'='*118}\nII.3  THRESHOLD SENSITIVITY: all three trim thresholds shifted together (100d>10%, 150d>12%, 200d>15% + shift); live and S6 both re-run\n{'='*118}")
    log(f"  {'shift':>6} {'A days 1/2/3 (proxy)':<24} | live {'F':>7}{'S':>7}{'H':>7}{'real':>7} | S6 {'F':>7}{'S':>7}{'H':>7}{'real':>7} | S6-live {'F':>7}{'S':>7}{'H':>7}{'real':>7}")
    SH = []
    for sh in (-2, -1, 0, 1, 2):
        vq = {rows[i]['d']: votes_shift(rows[i]['gaps'], sh) for i in A_IDX}
        vr = {d: votes_shift(RINFO[d]['gaps'], sh) for d in RA_DAYS}
        if sh == 0: assert vq == VOTES_Q and vr == VOTES_R
        le, _ = peval(SCHED[0][2], vq); se, _ = peval(S6, vq); rle, _ = real_eval(SCHED[0][2], votes=vr); rse, _ = real_eval(S6, votes=vr)
        c = [0, 0, 0, 0]
        for v in vq.values(): c[v] += 1
        SH.append((sh, se['sharpe'] - le['sharpe'], se['s_sharpe'] - le['s_sharpe'], se['h_sharpe'] - le['h_sharpe'], rse['sharpe'] - rle['sharpe']))
        log(f"  {sh:>+5}pp {f'{c[1]}/{c[2]}/{c[3]}':<24} | {le['sharpe']:>12.3f}{le['s_sharpe']:>7.3f}{le['h_sharpe']:>7.3f}{rle['sharpe']:>7.3f} | {se['sharpe']:>10.3f}{se['s_sharpe']:>7.3f}{se['h_sharpe']:>7.3f}{rse['sharpe']:>7.3f} | "
            f"{SH[-1][1]:>+15.3f}{SH[-1][2]:>+7.3f}{SH[-1][3]:>+7.3f}{SH[-1][4]:>+7.3f}")
    log(f"  both-era positive at shifts: {', '.join(f'{s:+d}' for s, f, S_, H_, r in SH if S_ > 0 and H_ > 0) or 'none'}; real positive at: {', '.join(f'{s:+d}' for s, f, S_, H_, r in SH if r > 0) or 'none'}")

    # ---------------------------------------------------------------- II.4 attribution
    log(f"\n{'='*118}\nII.4  ATTRIBUTION of S6 minus live: extension episodes (runs of consecutive effective-A days with >= 1 vote), years, drawdown windows\n{'='*118}")
    s6ser = DEC['S6']['ser']; s6rser = DEC['S6']['rser']
    ATT = {}
    for hname, cand, base, dates, apos, votes in (('proxy', s6ser, live_ser, PDATES, A_IDX, VOTES_Q),
                                                  ('real', s6rser, rlive_ser, RD1, [RDAYS.index(d) for d in RA_DAYS], VOTES_R)):
        # positions: proxy rows index i; real: RDAYS index of d0 == position in the return series (out[i-1] is d0=RDAYS[i-1])
        if hname == 'proxy':
            pos = apos; vpos = [votes[rows[p]['d']] for p in pos]
        else:
            pos = apos; vpos = [votes[RDAYS[p]] for p in pos]
        eps = episodes_of(pos, vpos)
        diff = [math.log1p(c) - math.log1p(b) for c, b in zip(cand, base)]
        tot = sum(diff) * 100
        in_ep = set()
        rec = []
        for a0, b0 in eps:
            days = range(a0, b0 + 1); in_ep.update(days)
            g = sum(diff[i] for i in days) * 100
            if hname == 'proxy': vl = [votes[rows[i]['d']] for i in days]; d_a, d_b = rows[a0]['d'], rows[b0]['d']
            else: vl = [votes[RDAYS[i]] for i in days]; d_a, d_b = RDAYS[a0], RDAYS[b0]
            rec.append((g, d_a, d_b, len(vl), vl.count(1), vl.count(2), vl.count(3)))
        # spill-over: differences on days outside episodes (band/cost carry after a rung change)
        spill = sum(diff[i] for i in range(len(diff)) if i not in in_ep) * 100
        rec.sort(reverse=True)
        pos_sum = sum(g for g, *_ in rec if g > 0); neg_sum = sum(g for g, *_ in rec if g < 0)
        top3 = sum(g for g, *_ in rec[:3])
        log(f"  {hname.upper()}: {len(rec)} episodes, {sum(r[3] for r in rec)} vote days; total S6-live log-return {tot:+.2f} pp (in episodes {tot-spill:+.2f}, spill-over outside {spill:+.2f}); "
            f"positive episodes {sum(1 for r in rec if r[0]>0)}/{len(rec)} summing {pos_sum:+.2f} pp, negative {neg_sum:+.2f} pp; top-3 {top3:+.2f} pp = {top3/pos_sum*100 if pos_sum else 0:.0f}% of gross positive")
        log(f"  {'gain pp':>8} {'start':<11}{'end':<11}{'days':>5} {'n1':>4}{'n2':>4}{'n3':>4}")
        for g, d_a, d_b, n, n1, n2, n3 in rec:
            log(f"  {g:>+8.2f} {d_a:<11}{d_b:<11}{n:>5} {n1:>4}{n2:>4}{n3:>4}")
        ATT[hname] = rec
        # Sharpe decomposition: mean and sd of the two series
        mc, sc = statistics.mean(cand), statistics.stdev(cand); mb, sb = statistics.mean(base), statistics.stdev(base)
        log(f"  Sharpe anatomy ({hname}): live mean {mb*1e4:.2f} bp/d sd {sb*1e4:.1f} bp -> {mb/sb*math.sqrt(252):.3f}; S6 mean {mc*1e4:.2f} bp/d sd {sc*1e4:.1f} bp -> {mc/sc*math.sqrt(252):.3f} "
            f"(mean {'-' if mc<mb else '+'}{abs(mc-mb)*1e4:.2f} bp/d, sd {'-' if sc<sb else '+'}{abs(sc-sb)*1e4:.1f} bp: the gain is {'a variance effect' if mc <= mb else 'a return effect'})")
    # per-year, both harnesses, S6a/S6b/S6
    log(f"\n  PER-YEAR (return %, deltas vs live in pp): proxy then real")
    for hname, dates, base, key in (('proxy', PDATES, live_ser, 'ser'), ('real', RD1, rlive_ser, 'rser')):
        yl = byyear(base, dates); ys = {lab: byyear(DEC[lab][key], dates) for lab in ('S6a', 'S6b', 'S6')}
        log(f"  {hname}: {'year':<6}{'live':>8}{'S6a':>8}{'S6b':>8}{'S6':>8} | {'dS6a':>7}{'dS6b':>7}{'dS6':>7}")
        for y in sorted(yl):
            if all(abs(ys[l][y] - yl[y]) < 1e-9 for l in ys): continue
            log(f"  {'':<7}{y:<6}{yl[y]*100:>+8.1f}{ys['S6a'][y]*100:>+8.1f}{ys['S6b'][y]*100:>+8.1f}{ys['S6'][y]*100:>+8.1f} | {(ys['S6a'][y]-yl[y])*100:>+7.1f}{(ys['S6b'][y]-yl[y])*100:>+7.1f}{(ys['S6'][y]-yl[y])*100:>+7.1f}")
        log(f"  {'':<7}(years with no vote day omitted: identical)")
    # drawdown windows
    log(f"\n  DRAWDOWN WINDOWS (peak -> trough, recovery) and the sessions inside the live window where S6 held less beta-equivalent exposure (core + 3 TQQQ + 2 QLD) than live:")
    lr, lh, _, _ = run_held(rows, proxy_fn(0)); sr, shh, _, _ = run_held(rows, pfn(make_AT(S6)))
    assert all(abs(a - b) < 1e-12 for a, b in zip(lr, live_ser)) and all(abs(a - b) < 1e-12 for a, b in zip(sr, s6ser))
    rl_out, rl_h, rl_turn, rl_reg, rl_reb = simulate_real_detail(SCHED[0][2]); rs_out, rs_h, rs_turn, rs_reg, rs_reb = simulate_real_detail(S6)
    assert all(abs(a - b) < 1e-12 for a, b in zip(rl_out, rlive_ser)) and all(abs(a - b) < 1e-12 for a, b in zip(rs_out, s6rser))
    def beta(h): return h[0] + 3 * h[1] + 2 * h[2]
    for hname, base, cand, hb, hc, dates, ddates in (('proxy', live_ser, s6ser, lh, shh, PDATES, PDATES), ('real', rlive_ser, s6rser, rl_h, rs_h, RD1, RDAYS[:-1])):
        pa, pb, prc, pdd, ia, ib = dd_window(base, dates); ca, cb, crc, cdd, ja, jb = dd_window(cand, dates)
        log(f"  {hname}: live MaxDD {pdd*100:.1f}% {pa} -> {pb} (recovered {prc}); S6 MaxDD {cdd*100:.1f}% {ca} -> {cb} (recovered {crc})")
        # within the live window, sessions with different holdings
        rows_diff = [(ddates[i], beta(hb[i]), beta(hc[i]), hb[i], hc[i], base[i], cand[i]) for i in range(ia, ib + 1) if abs(beta(hb[i]) - beta(hc[i])) > 1e-9]
        less = [x for x in rows_diff if x[2] < x[1]]; more = [x for x in rows_diff if x[2] > x[1]]
        cum = sum(math.log1p(c) - math.log1p(b) for _, _, _, _, _, b, c in rows_diff) * 100
        log(f"    inside the live window: {ib-ia+1} sessions, {len(rows_diff)} with different holdings ({len(less)} S6 less beta, {len(more)} S6 more); S6-live log-return over them {cum:+.2f} pp; "
            f"S6 NAV at live's trough date vs live: {(math.exp(sum(math.log1p(x) for x in cand[:ib+1]) - sum(math.log1p(x) for x in base[:ib+1]))-1)*100:+.2f}%")
        # S6 drawdown at the live window and vice versa
        def dd_over(ser, a, b):
            nav = 1.0; pk = 1.0; worst = 0.0
            for x in ser[a:b + 1]:
                nav *= 1 + x; pk = max(pk, nav); worst = min(worst, nav / pk - 1)
            return worst
        log(f"    S6 drawdown over live's window {dd_over(cand, ia, ib)*100:.1f}%; live drawdown over S6's window {dd_over(base, ja, jb)*100:.1f}%")
        for d, bl, bc, hl_, hc_, rb, rc in (less + more)[:40]:
            log(f"      {d}  live beta {bl:.2f} (core {hl_[0]:.2f} tqqq {hl_[1]:.2f} cash {hl_[4]:.2f})  S6 beta {bc:.2f} (core {hc_[0]:.2f} tqqq {hc_[1]:.2f} cash {hc_[4]:.2f})  ret live {rb*100:+.2f}% S6 {rc*100:+.2f}%")
        if len(rows_diff) > 40: log(f"      ... {len(rows_diff)-40} more sessions")

    # ---------------------------------------------------------------- II.5 per-vote-level leg returns by era
    log(f"\n{'='*118}\nII.5  PER-VOTE-LEVEL NEXT-SESSION RETURNS by era: core, TQQQ leg, cash (bp/d, t, n) and the S6 row minus the live row (both after the vol target)\n{'='*118}")
    log(f"  {'harness / era':<28}{'v':>2}{'n':>6} | core {'bp/d':>7}{'t':>6} | TQQQ {'bp/d':>7}{'t':>6} | cash {'bp/d':>6} | core-cash {'t':>6} | S6row-liverow {'bp/d':>7}{'t':>6}{'pos%':>6}")
    ATS6 = make_AT(S6); ATL = make_AT(SCHED[0][2])
    for hname, ds_, votes, getret, rowfn in ((f'proxy search {SEARCH[0][:7]}+', [d for d in VOTES_Q if d >= SEARCH[0]], VOTES_Q, lambda d: PLEG[d], lambda d, v: (ATS6[d][v], ATL[d][v])),
                                             ('proxy holdout ..2015-10', [d for d in VOTES_Q if d <= HOLDOUT[1]], VOTES_Q, lambda d: PLEG[d], lambda d, v: (ATS6[d][v], ATL[d][v])),
                                             ('proxy full', list(VOTES_Q), VOTES_Q, lambda d: PLEG[d], lambda d, v: (ATS6[d][v], ATL[d][v])),
                                             ('real daily (SPMO) 2015-11+', RA_DAYS, VOTES_R, lambda d: RLEG_RET[d], lambda d, v: (RF.vt(srow(S6, v), RINFO[d]['vol']), RF.vt(srow(SCHED[0][2], v), RINFO[d]['vol'])))):
        for v in range(4):
            dd = [d for d in ds_ if votes[d] == v]
            if not dd: continue
            core = [getret(d)[0] for d in dd]; tq = [getret(d)[1] for d in dd]; ca = [getret(d)[4] for d in dd]
            diffs = []
            for d in dd:
                r = getret(d); a_, b_ = rowfn(d, v)
                diffs.append(sum(a_[j] * r[j] for j in range(5)) - sum(b_[j] * r[j] for j in range(5)))
            log(f"  {hname:<28}{v:>2}{len(dd):>6} | {statistics.mean(core)*1e4:>12.1f}{tst(core):>6.2f} | {statistics.mean(tq)*1e4:>12.1f}{tst(tq):>6.2f} | {statistics.mean(ca)*1e4:>11.1f} | {tst([c-x for c,x in zip(core,ca)]):>16.2f} | "
                f"{statistics.mean(diffs)*1e4:>21.1f}{tst(diffs):>6.2f}{sum(1 for x in diffs if x>0)/len(diffs)*100:>6.0f}")
    log("  (rung 0 and rung 3 rows are identical in S6 and live, so S6row-liverow is 0 there by construction. The 1-vote line is the direct test of 'SPMO is worth holding at 1 vote'.)")

    # ---------------------------------------------------------------- II.6 trading
    log(f"\n{'='*118}\nII.6  TRADING on the real daily harness: rebalances/yr, traded L1 turnover per session, regime changes/yr (vote-count changes included); lag and 20 bp for S6a, S6b, S6\n{'='*118}")
    log(f"  {'design':<6}{'reb/yr':>8}{'turnover/session':>18}{'turnover/yr':>13}{'regime chg/yr':>15}")
    for lab, s in (('live', SCHED[0][2]), ('S6a', S6A), ('S6b', S6B), ('S6', S6)):
        _, _, tu, rg, rb = simulate_real_detail(s)
        log(f"  {lab:<6}{rb:>8.1f}{tu*100:>17.2f}%{tu*252*100:>12.0f}%{rg:>15.1f}")
    lagQ, lagR = lag_votes()
    lvL, _ = proxy_eval(0, lagQ); rlvL, _ = real_eval(SCHED[0][2], votes=lagR)
    DSF.ONE_WAY_SPREAD = IS.ONE_WAY_SPREAD = 0.002
    try: l20, _ = proxy_eval(0)
    finally: DSF.ONE_WAY_SPREAD = IS.ONE_WAY_SPREAD = 0.0004
    rl20, _ = real_eval(SCHED[0][2], one_way=0.002)
    log(f"\n  {'design':<6} lag (both lagged) vs live-lagged {'F':>7}{'S':>7}{'H':>7}{'real':>7} | 20 bp vs live-20bp {'F':>7}{'S':>7}{'H':>7}{'real':>7} | vs ctl@20bp {'F':>7}{'S':>7}{'H':>7}")
    for lab, s in (('S6a', S6A), ('S6b', S6B), ('S6', S6)):
        evL, _ = peval(s, lagQ); revL, _ = real_eval(s, votes=lagR)
        DSF.ONE_WAY_SPREAD = IS.ONE_WAY_SPREAD = 0.002
        try:
            c20, _ = peval(s); _, ctl20, _ = proxy_control(c20['risky'])
        finally: DSF.ONE_WAY_SPREAD = IS.ONE_WAY_SPREAD = 0.0004
        rc20, _ = real_eval(s, one_way=0.002)
        log(f"  {lab:<6}{'':<32}{evL['sharpe']-lvL['sharpe']:>+7.3f}{evL['s_sharpe']-lvL['s_sharpe']:>+7.3f}{evL['h_sharpe']-lvL['h_sharpe']:>+7.3f}{revL['sharpe']-rlvL['sharpe']:>+7.3f} | {'':<19}"
            f"{c20['sharpe']-l20['sharpe']:>+7.3f}{c20['s_sharpe']-l20['s_sharpe']:>+7.3f}{c20['h_sharpe']-l20['h_sharpe']:>+7.3f}{rc20['sharpe']-rl20['sharpe']:>+7.3f} | {'':<11}{c20['sharpe']-ctl20['sharpe']:>+7.3f}{c20['s_sharpe']-ctl20['s_sharpe']:>+7.3f}{c20['h_sharpe']-ctl20['h_sharpe']:>+7.3f}")
    log(f"  (live lagged: proxy {fmt_ev(lvL)} S {lvL['s_sharpe']:.3f} H {lvL['h_sharpe']:.3f}, real {fmt_ev(rlvL)}; live at 20 bp: proxy {fmt_ev(l20)}, real {fmt_ev(rl20)})")

    # ---------------------------------------------------------------- II.7 bootstrap
    log(f"\n{'='*118}\nII.7  BLOCK BOOTSTRAP (2000 draws, 20d / 60d) S6a, S6b, S6 vs live and vs matched control; proxy and real; Sharpe and log-return\n{'='*118}")
    jobs = []
    for lab in ('S6a', 'S6b', 'S6'):
        D_ = DEC[lab]
        for cmp_, a, b in ((f'{lab} proxy vs live', D_['ser'], live_ser), (f'{lab} proxy vs control', D_['ser'], D_['cser']),
                           (f'{lab} real vs live', D_['rser'], rlive_ser), (f'{lab} real vs control', D_['rser'], D_['rcser'])):
            for blk in (20, 60): jobs.append((cmp_, a, b, blk, (sum(ord(ch) * (k + 1) for k, ch in enumerate(cmp_)) + blk) & 0xffff))
    with mp.Pool(N_PROCS) as pool:
        res = pool.map(_boot_worker, jobs)
    BOOT = {}
    for lab, blk, (l1, l2, pl, s1, s2, ps) in res:
        BOOT[(lab, blk)] = (ps, pl)
        log(f"  {lab:<24} block {blk:>2}d: Sharpe 95% CI [{s1:+.3f}, {s2:+.3f}] P(<=0)={ps:.3f}   log-return [{l1*100:+.2f}, {l2*100:+.2f}] pp/yr P(<=0)={pl:.3f}")

    # ---------------------------------------------------------------- II.8 verdict card
    log(f"\n{'='*118}\nII.8  VERDICT CARD (project bar: both-era improvement | beats matched control S and H | bootstrap P(<=0) < 0.05 | permutation p < 0.05 | real CAGR not falling)\n{'='*118}")
    for lab in ('S6a', 'S6b', 'S6'):
        D_ = DEC[lab]; ev, rev, cev = D_['ev'], D_['rev'], D_['cev']
        log(f"  {lab}: both-era {'PASS' if ev['s_sharpe']>live_ev['s_sharpe'] and ev['h_sharpe']>live_ev['h_sharpe'] else 'fail'} (dS {ev['s_sharpe']-live_ev['s_sharpe']:+.3f}, dH {ev['h_sharpe']-live_ev['h_sharpe']:+.3f}) | "
            f"control {'PASS' if ev['s_sharpe']>cev['s_sharpe'] and ev['h_sharpe']>cev['h_sharpe'] else 'fail'} (S {ev['s_sharpe']-cev['s_sharpe']:+.3f}, H {ev['h_sharpe']-cev['h_sharpe']:+.3f}) | "
            f"bootstrap P(<=0) proxy vs live {BOOT[(f'{lab} proxy vs live',60)][0]:.3f}, vs control {BOOT[(f'{lab} proxy vs control',60)][0]:.3f}, real vs live {BOOT[(f'{lab} real vs live',60)][0]:.3f} | "
            f"real Sharpe {rev['sharpe']-rlive_ev['sharpe']:+.3f}, real CAGR {(rev['cagr']-rlive_ev['cagr'])*100:+.2f} pp")
    log(f"  neighbourhood permutation (24 cells, both-era-min): vs live real best {PERM2['realL'][0]:+.3f} ({PERM2['realL'][1]}) null 95th {PERM2['n95L']:+.3f} p = {PERM2['pL']:.3f}; "
        f"vs matched control real best {PERM2['realC'][0]:+.3f} ({PERM2['realC'][1]}) null 95th {PERM2['n95C']:+.3f} p = {PERM2['pC']:.3f}")
    log(f"  cells clearing both-era AND control on points: {len(nb_ok_c)}/24; threshold shifts with S6-live positive in both eras: {sum(1 for s, f, S_, H_, r in SH if S_ > 0 and H_ > 0)}/5, real positive {sum(1 for s, f, S_, H_, r in SH if r > 0)}/5")
    log(f"  Part II candidate count: 2 (S6a, S6b) + 23 new neighbour cells + 5 threshold shifts x 2 designs (sensitivity, not candidates) + 27 exposure-matched controls. Nothing applied; owner decides.")
    log(f"  [part2 done in {time.time()-T0:.0f} s]")

if __name__ == '__main__':
    if STAGE == 'part2':
        header(); stage_part2(); log(f"\n[total {time.time()-T0:.0f} s]"); sys.exit(0)
    if STAGE in ('all', 'grid'): stage_grid()
    if STAGE in ('all', 'perm'):
        if STAGE == 'perm': header()
        stage_perm()
    if STAGE in ('all', 'deep'):
        if STAGE == 'deep': header()
        stage_deep()
    log(f"\n[total {time.time()-T0:.0f} s]")
