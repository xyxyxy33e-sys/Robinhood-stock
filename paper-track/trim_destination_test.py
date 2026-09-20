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

Stages: TDT_STAGE=all|grid|perm|deep (default all), TDT_NPERM (1000), TDT_PROCS (4). Run from the repo root:
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

if __name__ == '__main__':
    if STAGE in ('all', 'grid'): stage_grid()
    if STAGE in ('all', 'perm'):
        if STAGE == 'perm': header()
        stage_perm()
    if STAGE in ('all', 'deep'):
        if STAGE == 'deep': header()
        stage_deep()
    log(f"\n[total {time.time()-T0:.0f} s]")
