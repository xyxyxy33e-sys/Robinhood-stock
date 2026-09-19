"""Research line `e_pair_test` (2026-09-19): the D pair test, repeated for STATE E ("do the same test for E").

State E: QQQ below both its 50d and 200d SMAs while the 50d is still ABOVE the 200d -- the first leg down of a correction
whose long trend has not yet rolled over. Live row 50 % XLU / 50 % cash (BOXX), before the 20 % vol target (E's QQQ vol is
~35 %, so the row is typically held at ~0.57x). About 5.8 % of history, ~32 episodes over 26 years, median ~10 sessions.

BASELINE = THE CURRENT LIVE DESIGN, WITH THE STATE-D GATE (applied 2026-09-19 by owner override; state.d_gate_active:
breadth bottom quintile OR QQQ less than 2 % above its 200d -> D row to cash). `d_substate_fresh.py` pins its baseline to
the PRE-gate design (proxy 22.18 % / 0.913 / -33.6 %, real daily 29.66 % / 1.145 / -32.9 %); here the gate is applied on
every macro-D day in both harnesses through `state.d_gate_active(st, breadth_pct, gaps[d0][200])`, and the result MUST
reproduce d_pair_test row #10 `breadth OR gap200<2%`: proxy 25.74 % / 1.077 / -28.5 %, real daily 37.75 % / 1.484 / -19.4 %
(asserted before anything is scored; the real mirror is also asserted day by day against monthly_returns.simulate with
its default d_gate). The E candidates then modify ONLY macro-E days on top of that gated baseline.

PRE-REGISTERED, FIXED BEFORE ANY RESULT
  Rules (the five D families, thresholds adapted to E, where price is below the 200d on every day):
    1 breadth        QQEW/QQQ 60-session log-change in its trailing-252 bottom quintile (pct < 0.20), breadth_tracker verbatim
    2 sma20>=sma60   QQQ 20d SMA >= 60d SMA
    3 px>=sma100     QQQ close >= 100d SMA
    4 gap200<-2%     QQQ MORE than 2 % BELOW its 200d SMA (the E analogue of D's gap200<2%, which is degenerate in E)
    5 volratio>1.5   QQQ 10d realised vol > 1.5x 30d realised vol
  Degeneracy screen (before scoring): each rule's flag rate on E days is printed for the proxy (over E days where the rule's
  inputs exist; breadth exists from 2007-07) and for the real rows; a rule flagging < 5 % or > 95 % of E days on EITHER
  harness is DROPPED and the grid shrinks to the survivors (recorded in the log and the note).
  Action families, each applied ONLY on macro-E days:
    CASH  flagged E day -> 100 % BOXX (drop XLU); unflagged E stays live (50 XLU / 50 cash)
    RISK  UNflagged E day (the "healthy" complement) -> 100 % SPMO (the C row); flagged E stays live
  Grid per family = all singles + all pairs x {AND, OR} + all unions of 3..k of the surviving rules (41 for k = 5); the
  two families together are one grid for the permutation. Controls: constant-E rows, XLU fraction f in 0..100 % step 10
  (rest cash; f = 50 is live) and SPMO fraction g in 0..100 % step 10 (rest cash) -- so an exposure-matched constant
  control exists on both sides. No other rules, no threshold tuning.
  Evaluation as in d_pair_test: proxy full / search (2015-11+) / holdout (2000-07..2015-10) CAGR / Sharpe / MaxDD / exposure
  / rebalances, real daily CAGR / Sharpe / MaxDD, flagged-day and episode counts, deltas vs live, vs the exposure-matched
  constant control (CASH family -> XLU ladder, RISK family -> SPMO ladder), vs the better member single (combinations).
  Whole-grid permutation: 1000 common circular shifts of the E-day flag sequences (all rules together), max statistic over
  the ENTIRE grid (both families) for (a) full-period Sharpe gain vs live, (b) both-era min gain vs live, (c) combination
  minus its best member single, both-era (and full). Deep block for the best single and best combination per family and the
  best overall; drawdown-episode table; statistical-power section.

Harness: imports paper-track/d_substate_fresh.py (DSF_STAGE=none -> bootstrap only) exactly as d_pair_test does; the only
new loop is `simulate_real_e`, a copy of its verified `simulate_real` that (a) applies the D gate and (b) accepts an E-day
override, asserted equal day by day to monthly_returns.simulate(px, qqq, days) with the gate on. Sharpe is the repo's
ZERO-RATE annualised Sharpe (drift_band_test.annual_stats) everywhere.

Prior E research (NOT re-run, cited in the note): STRATEGY.md "D and E substates: searched again on full history, still
nothing" (de_substate_search.py), e1e2_trend_r2_check.py (E1/E2 by 63d trend R^2, rejected), "The XLU update to state E".

Research only. Nothing is applied. No repo data file, no protected file, no commit, no trade.

Run from the repo root:
    python3 paper-track/e_pair_test.py                     # grid + permutation + diagnostics
    EPT_STAGE=boot|grid|perm|diag  EPT_NPERM=1000  EPT_PROCS=4
Intermediates go to the scratchpad (EPT_SCRATCH).
"""
import sys, os, math, json, random, csv, time, itertools

os.environ.setdefault('DSF_STAGE', 'none')          # import d_substate_fresh for its bootstrap only
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)
sys.path.insert(0, 'paper-track')
SCRATCH = os.environ.get('EPT_SCRATCH',
                         '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad')
os.makedirs(SCRATCH, exist_ok=True)
STAGE = os.environ.get('EPT_STAGE', 'all')
N_PERM = int(os.environ.get('EPT_NPERM', '1000'))
N_PROCS = int(os.environ.get('EPT_PROCS', '4'))
SEED = 20260919
T0 = time.time()

import d_substate_fresh as DSF
from d_substate_fresh import (rows, run, evaluate, vt, RF, W, BASE, QIX, RIX, SIG_Q, SIG_R, log,
                              evaluate_full, real_metrics, run_count, sliced_sharpe, tstat,
                              BASE_EV, REAL_EV, REAL_EXP, REAL_REB, LIVE_SER, RPX, RQQQ, RDAYS, RQD,
                              SEARCH, HOLDOUT, REGIMES, boot, bstats, annual_stats, live_fn, sma_series)
import improvement_search as IS
import breadth_tracker as BT
from long_history_backtest import load_px
from state import (d_gate_active, compute_states, compute_micro_agreement, compute_fast_states, compute_extension_gaps,
                   realized_vol_live, target_weights_with_voltarget, effective_state, extension_votes, needs_rebalance,
                   REBALANCE_DRIFT_BAND, D_GATE_ENABLED)
MR = DSF.MR
assert D_GATE_ENABLED, 'state.D_GATE_ENABLED is False: this study is defined on the gated live design'

CASH = (0.0, 0.0, 0.0, 0.0, 1.0)
SPMO = (1.0, 0.0, 0.0, 0.0, 0.0)
E_LIVE = W['E']
assert E_LIVE == (0.0, 0.0, 0.0, 0.5, 0.5), f'live E row is not 50/50 XLU/cash: {E_LIVE}'

# ---------------------------------------------------------------- breadth (breadth_tracker verbatim, as in d_pair_test)
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
assert abs(BP_R['2026-09-04'] - 0.867) < 0.006, 'breadth reading does not reproduce breadth_tracker self-check'

# ---------------------------------------------------------------- GATED LIVE BASELINE (proxy)
GATE_Q = set(r['d'] for r in rows if r['state'] == 'D' and d_gate_active(r['state'], BP_Q.get(r['d']), r['gaps'][200]))
GBASE = {r['d']: (vt(CASH, r['vol']) if r['d'] in GATE_Q else BASE[r['d']]) for r in rows}
def glive_fn(r): return GBASE[r['d']]
GLIVE_EV, GLIVE_SER = evaluate_full(glive_fn)
_, GLIVE_EXP, GLIVE_REB = run_count(rows, glive_fn)

# ---------------------------------------------------------------- GATED LIVE BASELINE (real daily) + E override mirror
def simulate_real_e(px, qqq, days, override_e=None, band=REBALANCE_DRIFT_BAND):
    """Copy of d_substate_fresh.simulate_real (itself the verified mirror of monthly_returns.simulate) with
    (a) the 2026-09-19 state-D gate applied exactly as monthly_returns.simulate applies it (breadth via
    breadth_tracker, gap from compute_extension_gaps), and (b) override_e(d0) -> action row or None on macro-E days,
    applied before the vol target. With override_e=None it is asserted equal to MR.simulate(px, qqq, days) day by day."""
    qd = sorted(qqq)
    states = dict(zip(qd, compute_states(qd, qqq)))
    micro = compute_micro_agreement(qd, qqq)
    fast = compute_fast_states(qd, qqq); gaps = compute_extension_gaps(qd, qqq)
    held = prev = None; out = []; risky = 0.0; nreb = 0
    for i in range(1, len(days)):
        d0, d1 = days[i - 1], days[i]
        st, ag = states[d0], micro[d0]
        gate = d_gate_active(st, BP_R.get(d0), gaps[d0][200])
        vol = realized_vol_live(qd, qqq, as_of=d0)
        row = override_e(d0) if (override_e is not None and st == 'E') else None
        if row is None:
            t = target_weights_with_voltarget(st, ag, vol, fast_state=fast[d0], gaps=gaps[d0], d_gate=gate)
        else:
            t = RF.vt(row, vol)
        eff = effective_state(st, fast[d0])
        stk = (eff, extension_votes(eff, gaps[d0]), gate, row is not None)
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

_ref = MR.simulate(RPX, RQQQ, RDAYS)                 # default d_gate = state.D_GATE_ENABLED (True): the live design
_mine, GREAL_EXP, GREAL_REB = simulate_real_e(RPX, RQQQ, RDAYS)
assert len(_ref) == len(_mine) and all(a[0] == b[0] and abs(a[2] - b[2]) < 1e-12 for a, b in zip(_ref, _mine)), \
    'simulate_real_e does not reproduce monthly_returns.simulate with the D gate'
GREAL_EV, GREAL_SER = real_metrics(_mine)

log(f"\n{'='*118}\nRESEARCH LINE e_pair_test -- baselines\n{'='*118}")
log(f"PRE-GATE standing figures (d_substate_fresh, for reference only): proxy {BASE_EV['cagr']*100:.2f}% / {BASE_EV['sharpe']:.3f} / "
    f"{BASE_EV['mdd']*100:.1f}% (S {BASE_EV['s_sharpe']:.3f} H {BASE_EV['h_sharpe']:.3f}) | real daily {REAL_EV['cagr']*100:.2f}% / "
    f"{REAL_EV['sharpe']:.3f} / {REAL_EV['mdd']*100:.1f}%")
log(f"GATED LIVE (this study's baseline; D -> cash on {len(GATE_Q)} proxy D days via state.d_gate_active):")
log(f"  proxy {GLIVE_EV['cagr']*100:.2f}% / {GLIVE_EV['sharpe']:.3f} / {GLIVE_EV['mdd']*100:.1f}%  S {GLIVE_EV['s_sharpe']:.3f} "
    f"H {GLIVE_EV['h_sharpe']:.3f}  exposure {GLIVE_EXP*100:.1f}%  {GLIVE_REB:.1f} reb/yr   (must be 25.74% / 1.077 / -28.5%, d_pair_test #10)")
log(f"  real daily {GREAL_EV['cagr']*100:.2f}% / {GREAL_EV['sharpe']:.3f} / {GREAL_EV['mdd']*100:.1f}%  exposure {GREAL_EXP*100:.1f}%  "
    f"{GREAL_REB:.1f} reb/yr   (must be 37.75% / 1.484 / -19.4%; mirror asserted day by day vs monthly_returns.simulate)")
assert abs(GLIVE_EV['cagr'] * 100 - 25.74) < 0.006 and abs(GLIVE_EV['sharpe'] - 1.077) < 0.0006 and abs(GLIVE_EV['mdd'] * 100 + 28.5) < 0.06, \
    'proxy gated baseline does not reproduce d_pair_test #10'
assert abs(GREAL_EV['cagr'] * 100 - 37.75) < 0.006 and abs(GREAL_EV['sharpe'] - 1.484) < 0.0006 and abs(GREAL_EV['mdd'] * 100 + 19.4) < 0.06, \
    'real gated baseline does not reproduce d_pair_test #10'
log("  both baselines reproduced.")

# ---------------------------------------------------------------- E days
E_ROWS = [i for i, r in enumerate(rows) if r['state'] == 'E']
assert all(rows[i]['eff'] == 'E' for i in E_ROWS), 'fast overlay re-maps some macro-E day (unexpected: FAST_REENTRY_MAP has no E entry)'
nE = len(E_ROWS)
E_DATES = [rows[i]['d'] for i in E_ROWS]
RE_IDX = [k for k, d in enumerate(RDAYS[:-1]) if SIG_R['state'][RIX[d]] == 'E']
RE_DATES = [RDAYS[k] for k in RE_IDX]
S_MASK = [d >= SEARCH[0] for d in E_DATES]; H_MASK = [not m for m in S_MASK]

def episodes(flags, idx):
    """runs of consecutive flagged rows (consecutive in the harness row index)."""
    eps = []; cur = None
    for f, i in zip(flags, idx):
        if f:
            if cur is not None and i == cur[1] + 1: cur[1] = i; cur[2] += 1
            else:
                if cur: eps.append(tuple(cur))
                cur = [i, i, 1]
    if cur: eps.append(tuple(cur))
    return eps
E_EPS = episodes([True] * nE, E_ROWS)
RE_EPS = episodes([True] * len(RE_IDX), RE_IDX)
def med(v):
    s = sorted(v); n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])
E_VOL = [rows[i]['vol'] for i in E_ROWS]
log(f"\nstate E: {nE} proxy days ({nE/len(rows)*100:.1f}% of {len(rows)} rows), search {sum(S_MASK)}, holdout {sum(H_MASK)}; "
    f"{len(E_EPS)} episodes (search {sum(1 for e in E_EPS if rows[e[0]]['d'] >= SEARCH[0])}, holdout "
    f"{sum(1 for e in E_EPS if rows[e[0]]['d'] < SEARCH[0])}), median length {med([e[2] for e in E_EPS]):.0f} sessions, "
    f"median 30d QQQ vol on E days {med(E_VOL)*100:.1f}%")
log(f"real daily: {len(RE_DATES)} E days in {len(RE_EPS)} episodes, median length {med([e[2] for e in RE_EPS]):.0f} sessions")

# ---------------------------------------------------------------- rules and flags
RULES_ALL = [
    ('breadth',      'QQEW/QQQ 60-session log-change in trailing-252 bottom quintile (pct < 0.20) [breadth_tracker verbatim]'),
    ('sma20>=sma60', 'QQQ 20d SMA >= 60d SMA'),
    ('px>=sma100',   'QQQ close >= 100d SMA'),
    ('gap200<-2%',   'QQQ more than 2 % BELOW its 200d SMA'),
    ('volratio>1.5', 'QQQ 10d realised vol > 1.5x 30d realised vol'),
]
SHORT = {'breadth': 'BR', 'sma20>=sma60': 'S20', 'px>=sma100': 'P100', 'gap200<-2%': 'G200', 'volratio>1.5': 'VR'}
def build_flags(dates, close, SIG, bp):
    sm20, sm60 = sma_series(close, 20), sma_series(close, 60)
    F = {}
    F['breadth'] = [bp.get(d) is not None and bp[d] < BT.GATE_PCT for d in dates]
    F['sma20>=sma60'] = [a is not None and b is not None and a >= b for a, b in zip(sm20, sm60)]
    F['px>=sma100'] = [g is not None and g >= 0.0 for g in SIG['gap100']]
    F['gap200<-2%'] = [g is not None and g < -0.02 for g in SIG['gap200']]
    F['volratio>1.5'] = [v is not None and v > 1.5 for v in SIG['volratio']]
    F['_avail'] = {'breadth': [bp.get(d) is not None for d in dates],
                   'sma20>=sma60': [a is not None and b is not None for a, b in zip(sm20, sm60)],
                   'px>=sma100': [g is not None for g in SIG['gap100']],
                   'gap200<-2%': [g is not None for g in SIG['gap200']],
                   'volratio>1.5': [v is not None for v in SIG['volratio']]}
    return F
def lagged(F, k=1):
    out = {n: [False] * k + v[:-k] for n, v in F.items() if n != '_avail'}
    out['_avail'] = F['_avail']
    return out
def dseq(F, dates, ix):
    out = {n: [F[n][ix[d]] for d in dates] for n in F if n != '_avail'}
    out['_avail'] = {n: [F['_avail'][n][ix[d]] for d in dates] for n in F['_avail']}
    return out

FQ = build_flags(DSF._QD_EXT, DSF._QC_EXT, SIG_Q, BP_Q)
_, RC, _, _ = DSF.extend_back(RQQQ)
FR = build_flags(RQD, RC, SIG_R, BP_R)
FLQ = dseq(FQ, E_DATES, QIX); FLR = dseq(FR, RE_DATES, RIX)
EIDX = {d: j for j, d in enumerate(E_DATES)}; REIDX = {d: j for j, d in enumerate(RE_DATES)}

# ---- degeneracy screen (pre-registered: drop < 5 % or > 95 % on either harness, rate over E days with an available reading)
log(f"\n{'='*118}\nFLAG RATES on E days (pre-registered degeneracy screen: drop a rule flagging < 5 % or > 95 % of E days on either harness)\n{'='*118}")
log(f"{'rule':<14}{'proxy avail':>12}{'flagged':>9}{'rate':>7}{'| S rate':>9}{'H rate':>8} | {'real avail':>11}{'flagged':>9}{'rate':>7}  verdict")
RNAMES = []; DROPPED = []; RATES = {}
for n, desc in RULES_ALL:
    aq = [j for j in range(nE) if FLQ['_avail'][n][j]]; fq = sum(1 for j in aq if FLQ[n][j])
    ar = [j for j in range(len(RE_DATES)) if FLR['_avail'][n][j]]; fr = sum(1 for j in ar if FLR[n][j])
    rq = fq / len(aq) if aq else float('nan'); rr_ = fr / len(ar) if ar else float('nan')
    sq = [j for j in aq if S_MASK[j]]; hq = [j for j in aq if H_MASK[j]]
    rs = sum(1 for j in sq if FLQ[n][j]) / len(sq) if sq else float('nan'); rh = sum(1 for j in hq if FLQ[n][j]) / len(hq) if hq else float('nan')
    degenerate = not (0.05 <= rq <= 0.95) or not (0.05 <= rr_ <= 0.95)
    RATES[n] = dict(proxy_avail=len(aq), proxy_flag=fq, proxy_rate=rq, s_rate=rs, h_rate=rh, real_avail=len(ar), real_flag=fr, real_rate=rr_, dropped=degenerate)
    log(f"{n:<14}{len(aq):>12}{fq:>9}{rq*100:>6.1f}%{rs*100:>8.1f}%{rh*100:>7.1f}% | {len(ar):>11}{fr:>9}{rr_*100:>6.1f}%  {'DROPPED (degenerate)' if degenerate else 'kept'}")
    (DROPPED if degenerate else RNAMES).append(n)
n_bmiss = sum(1 for a in FLQ['_avail']['breadth'] if not a)
log(f"  breadth unavailable on {n_bmiss} proxy E days (all before {min(d for d, a in zip(E_DATES, FLQ['_avail']['breadth']) if a)}); "
    f"E stays live there (AND with breadth is False, OR reduces to the other member). Nothing backfilled.")
if DROPPED:
    log(f"  DROPPED: {', '.join(DROPPED)} -> grid built on the {len(RNAMES)} surviving rules: {', '.join(RNAMES)}")
else:
    log(f"  no rule dropped; grid built on all {len(RNAMES)} rules")
K = len(RNAMES)
RULES = [(n, d) for n, d in RULES_ALL if n in RNAMES]

# ---------------------------------------------------------------- candidates (pre-registered structure)
FAMILIES = ('CASH', 'RISK')
FAM_ROW = {'CASH': CASH, 'RISK': SPMO}
FAM_DESC = {'CASH': 'flagged E day -> 100 % BOXX, unflagged E live', 'RISK': 'UNflagged E day -> 100 % SPMO, flagged E live'}
CANDS = []
for fam in FAMILIES:
    for n in RNAMES: CANDS.append((fam, 'single', (n,)))
    for a, b in itertools.combinations(RNAMES, 2):
        CANDS.append((fam, 'and', (a, b))); CANDS.append((fam, 'or', (a, b)))
    for k in range(3, K + 1):
        for c in itertools.combinations(RNAMES, k):
            CANDS.append((fam, 'or', c))
N_CAND = len(CANDS)
PER_FAM = N_CAND // 2
assert N_CAND == 2 * (K + K * (K - 1) + sum(math.comb(K, k) for k in range(3, K + 1)))
def label(spec):
    fam, op, names = spec
    if op == 'single': core = names[0]
    elif len(names) == 2: core = f"{names[0]} {op.upper()} {names[1]}"
    else: core = 'UNION(' + '|'.join(SHORT[n] for n in names) + ')'
    return f"{fam}: {core}"
def combine(spec, FL):
    _, op, names = spec
    seqs = [FL[n] for n in names]
    if op == 'single': return list(seqs[0])
    if op == 'and': return [all(t) for t in zip(*seqs)]
    return [any(t) for t in zip(*seqs)]
def on_days(spec, fl, dates):
    """days that receive the family's action row: CASH -> flagged days; RISK -> unflagged days."""
    fam = spec[0]
    return set(d for d, f in zip(dates, fl) if (f if fam == 'CASH' else not f))

# ---------------------------------------------------------------- evaluation helpers
def proxy_eval(on, row, row_fn=None):
    def fn(r):
        if r['d'] in on: return vt(row if row_fn is None else row_fn(r['d']), r['vol'])
        return GBASE[r['d']]
    return evaluate_full(fn)
def real_eval(on, row, row_fn=None):
    ov = lambda d0: (row if row_fn is None else row_fn(d0)) if d0 in on else None
    out, exp, reb = simulate_real_e(RPX, RQQQ, RDAYS, ov)
    m, ser = real_metrics(out)
    return dict(m, exp=exp, reb=reb), ser
_r0, _ = real_eval(set(), CASH)
assert abs(_r0['sharpe'] - GREAL_EV['sharpe']) < 1e-12
_p0, _ = proxy_eval(set(), CASH)
assert abs(_p0['sharpe'] - GLIVE_EV['sharpe']) < 1e-12

def dd_window(ser, dates):
    nav = 1.0; peak = 1.0; pk_i = 0; best = (0.0, 0, 0); navs = []
    for i, r in enumerate(ser):
        nav *= 1 + r; navs.append(nav)
        if nav > peak: peak = nav; pk_i = i
        dd = nav / peak - 1
        if dd < best[0]: best = (dd, pk_i, i)
    mdd, p, t = best
    rec = None
    for i in range(t, len(navs)):
        if navs[i] >= navs[p]: rec = dates[i]; break
    return dates[p], dates[t], mdd, rec
def fmt_ev(ev):
    return f"{ev['cagr']*100:6.2f}% /{ev['sharpe']:6.3f} /{ev['mdd']*100:6.1f}%"

JS_GRID = os.path.join(SCRATCH, 'ept_grid.json')
JS_PERM = os.path.join(SCRATCH, 'ept_perm.json')

def eval_candidate(spec, FLq=FLQ, FLr=FLR):
    fq = combine(spec, FLq); fr = combine(spec, FLr)
    onq = on_days(spec, fq, E_DATES); onr = on_days(spec, fr, RE_DATES)
    row = FAM_ROW[spec[0]]
    ev, ser = proxy_eval(onq, row); rev, rser = real_eval(onr, row)
    epq = episodes(fq, E_ROWS); epr = episodes(fr, RE_IDX)
    # episodes of the ACTION (days actually moved): flagged runs for CASH, unflagged runs for RISK
    aq = episodes([d in onq for d in E_DATES], E_ROWS); ar = episodes([d in onr for d in RE_DATES], RE_IDX)
    return dict(ev=ev, real=rev, n_flag=sum(fq), n_flag_s=sum(1 for j, f in enumerate(fq) if f and S_MASK[j]),
                n_flag_h=sum(1 for j, f in enumerate(fq) if f and H_MASK[j]), n_flag_ep=len(epq), n_flag_r=sum(fr), n_flag_ep_r=len(epr),
                n_on=len(onq), n_on_ep=len(aq), n_on_r=len(onr), n_on_ep_r=len(ar)), ser, rser, fq, fr

def overlap_table(FL, mask, names, title):
    idx = [j for j, m in enumerate(mask) if m]
    log(f"\n--- {title} (n = {len(idx)} E days): |a|, then Jaccard |a&b|/|a|b| (upper) and conditional P(col | row) = |a&b|/|row| (lower) ---")
    log(f"{'':<14}{'|a|':>5} " + "".join(f"{SHORT[n]:>8}" for n in names))
    for a in names:
        A = set(j for j in idx if FL[a][j]); cells = []
        for b in names:
            B = set(j for j in idx if FL[b][j])
            if a == b: cells.append(f"{'--':>8}")
            elif names.index(b) > names.index(a):
                u = len(A | B); cells.append(f"{(len(A & B) / u if u else float('nan')):>8.2f}")
            else:
                cells.append(f"{(len(A & B) / len(A) if A else float('nan')):>8.2f}")
        log(f"{a:<14}{len(A):>5} " + "".join(cells))

# ================================================================= STAGE grid
if STAGE in ('all', 'grid'):
    log(f"\n{'='*118}\nRESEARCH LINE e_pair_test -- pre-registered grid of {N_CAND} candidates ({PER_FAM} per family: {K} singles, "
        f"{K*(K-1)//2} x AND, {K*(K-1)//2} x OR, {PER_FAM - K - K*(K-1)} unions of 3-{K}) + 22 constant-E controls\n{'='*118}")
    log("Sharpe = zero-rate (repo convention) everywhere. Baseline = gated live (above). Candidates act on macro-E days only.")
    for n, desc in RULES: log(f"  {n:<14} {desc}")
    for fam in FAMILIES: log(f"  family {fam}: {FAM_DESC[fam]}")

    # ---- overlap
    log(f"\n{'='*118}\nOVERLAP of the singles' flag sets, counted on E days\n{'='*118}")
    overlap_table(FLQ, [True] * nE, RNAMES, 'proxy, full 2000-07..2026-08')
    overlap_table(FLQ, S_MASK, RNAMES, 'proxy, search era 2015-11+')
    overlap_table(FLQ, [h and a for h, a in zip(H_MASK, FLQ['_avail']['breadth'])], RNAMES, 'proxy, holdout 2007-07..2015-10 (breadth available)')
    overlap_table(FLR, [True] * len(RE_DATES), RNAMES, 'real daily 2015-11..2026-09')
    log("\n--- pair detail on proxy E days (full): |a|, |b|, |a&b|, |a|b|, Jaccard, P(b|a), P(a|b); search-era Jaccard; real-daily Jaccard ---")
    PAIRS = {}
    for a, b in itertools.combinations(RNAMES, 2):
        A = set(j for j in range(nE) if FLQ[a][j]); B = set(j for j in range(nE) if FLQ[b][j])
        As = set(j for j in A if S_MASK[j]); Bs = set(j for j in B if S_MASK[j])
        Ar = set(j for j in range(len(RE_DATES)) if FLR[a][j]); Br = set(j for j in range(len(RE_DATES)) if FLR[b][j])
        jf = len(A & B) / max(1, len(A | B)); js = len(As & Bs) / max(1, len(As | Bs)); jr = len(Ar & Br) / max(1, len(Ar | Br))
        PAIRS[(a, b)] = dict(a=len(A), b=len(B), ab=len(A & B), aub=len(A | B), j=jf, pba=len(A & B) / max(1, len(A)), pab=len(A & B) / max(1, len(B)), js=js, jr=jr)
        log(f"  {a:<14}{b:<14} {len(A):>4}{len(B):>5}{len(A & B):>6}{len(A | B):>6}{jf:>7.2f}{len(A & B)/max(1,len(A)):>7.2f}{len(A & B)/max(1,len(B)):>7.2f} | {js:>6.2f} | {jr:>6.2f}")

    # ---- E-day return profile: next-day XLU-leg and core-leg return on flagged vs unflagged E days per rule (bp/day)
    log(f"\n{'='*118}\nNEXT-DAY LEG RETURNS on E days, flagged vs unflagged (bp/day, t of the difference): core (QQQ TR proxy) and XLU legs\n{'='*118}")
    log(f"{'rule':<14}{'era':<8}{'nF':>5}{'core F':>8}{'core U':>8}{'t':>6}{'xlu F':>8}{'xlu U':>8}{'t':>6}")
    for n in RNAMES:
        for era_lab, mask in (('full', [True] * nE), ('search', S_MASK), ('holdout', H_MASK)):
            F_ = [j for j in range(nE) if mask[j] and FLQ[n][j]]; U_ = [j for j in range(nE) if mask[j] and not FLQ[n][j]]
            c1 = [rows[E_ROWS[j]]['legs'][0] for j in F_]; c0 = [rows[E_ROWS[j]]['legs'][0] for j in U_]
            x1 = [rows[E_ROWS[j]]['legs'][3] for j in F_]; x0 = [rows[E_ROWS[j]]['legs'][3] for j in U_]
            m = lambda v: sum(v) / len(v) * 1e4 if v else float('nan')
            log(f"{n:<14}{era_lab:<8}{len(F_):>5}{m(c1):>8.0f}{m(c0):>8.0f}{tstat(c1, c0):>6.1f}{m(x1):>8.0f}{m(x0):>8.0f}{tstat(x1, x0):>6.1f}")

    # ---- constant-E controls
    log(f"\n{'='*118}\nCONSTANT-E CONTROLS: E -> f x XLU + (1-f) cash (f = 50 % is live) and E -> g x SPMO + (1-g) cash, every E day, 10 % steps\n{'='*118}")
    log(f"{'row':<14} | proxy {'CAGR':>7}{'Sharpe':>7}{'MaxDD':>7}{'exp':>6}{'reb':>6}{'S Sh':>7}{'H Sh':>7}{'dS_S':>7}{'dS_H':>7}{'dS_F':>7} | real {'CAGR':>7}{'Sharpe':>7}{'MaxDD':>7}{'exp':>6}{'reb':>6}{'rdSh':>7}")
    CTRL = {'XLU': [], 'SPMO': []}
    allq = set(E_DATES); allr = set(RE_DATES)
    for inst in ('XLU', 'SPMO'):
        for f in range(0, 101, 10):
            row = (0.0, 0.0, 0.0, f / 100.0, 1 - f / 100.0) if inst == 'XLU' else (f / 100.0, 0.0, 0.0, 0.0, 1 - f / 100.0)
            ev, _ = proxy_eval(allq, row); rev, _ = real_eval(allr, row)
            CTRL[inst].append(dict(inst=inst, f=f, ev=ev, real=rev))
            log(f"{inst + ' ' + str(f) + '%':<14} | {ev['cagr']*100:>6.2f}%{ev['sharpe']:>7.3f}{ev['mdd']*100:>6.1f}%{ev['risky']*100:>5.1f}%{ev['reb']:>6.1f}{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f}"
                f"{ev['s_sharpe']-GLIVE_EV['s_sharpe']:>+7.3f}{ev['h_sharpe']-GLIVE_EV['h_sharpe']:>+7.3f}{ev['sharpe']-GLIVE_EV['sharpe']:>+7.3f} | "
                f"{rev['cagr']*100:>6.2f}%{rev['sharpe']:>7.3f}{rev['mdd']*100:>6.1f}%{rev['exp']*100:>5.1f}%{rev['reb']:>6.1f}{rev['sharpe']-GREAL_EV['sharpe']:>+7.3f}")
    live_ctl = CTRL['XLU'][5]
    assert live_ctl['f'] == 50 and abs(live_ctl['ev']['sharpe'] - GLIVE_EV['sharpe']) < 1e-9 and abs(live_ctl['real']['sharpe'] - GREAL_EV['sharpe']) < 1e-9, \
        'XLU 50 % control does not reproduce gated live'
    allc = CTRL['XLU'] + CTRL['SPMO']
    rng_f = max(c['ev']['sharpe'] for c in allc) - min(c['ev']['sharpe'] for c in allc)
    rng_s = max(c['ev']['s_sharpe'] for c in allc) - min(c['ev']['s_sharpe'] for c in allc)
    rng_h = max(c['ev']['h_sharpe'] for c in allc) - min(c['ev']['h_sharpe'] for c in allc)
    rng_r = max(c['real']['sharpe'] for c in allc) - min(c['real']['sharpe'] for c in allc)
    log(f"  the whole constant-E ladder (22 rows, cash..100 % XLU..100 % SPMO) spans a Sharpe range of {rng_f:.3f} (full), {rng_s:.3f} (S), "
        f"{rng_h:.3f} (H), {rng_r:.3f} (real): the most ANY E-row change can move the portfolio.")
    def match_ctrl(fam, exp, key):
        lad = CTRL['XLU' if fam == 'CASH' else 'SPMO']
        return min(lad, key=lambda c: abs((c['ev']['risky'] if key == 'ev' else c['real']['exp']) - exp))

    # ---- grid
    log(f"\n{'='*118}\nGRID: every candidate (proxy full / search / holdout; real daily). nFl/fEp = flagged proxy E days / flagged episodes; "
        f"nOn/oEp = days actually moved to the action row / their episodes\n{'='*118}")
    log(f"GATED LIVE proxy {fmt_ev(GLIVE_EV)} exp {GLIVE_EV['risky']*100:.1f}% reb {GLIVE_EV['reb']:.1f}/yr  S {GLIVE_EV['s_sharpe']:.3f} H {GLIVE_EV['h_sharpe']:.3f} | "
        f"real {fmt_ev(GREAL_EV)} exp {GREAL_EXP*100:.1f}% reb {GREAL_REB:.1f}/yr")
    log(f"{'#':>3} {'candidate':<44}{'nFl':>5}{'fEp':>4}{'nOn':>5}{'oEp':>4}{'CAGR':>7}{'Sharpe':>7}{'MaxDD':>7}{'exp':>6}{'reb':>5}"
        f"{'S Sh':>7}{'H Sh':>7}{'dS_S':>7}{'dS_H':>7}{'dS_F':>7} | {'rCAGR':>7}{'rSh':>6}{'rDD':>7}{'rexp':>5}{'rreb':>5}{'rnFl':>5}{'rnOn':>5}{'rdSh':>7}")
    RES = []; SER = {}; RSER = {}; FLAG = {}
    for k, spec in enumerate(CANDS):
        rec, ser, rser, fq, fr = eval_candidate(spec)
        ev, rev = rec['ev'], rec['real']
        rec.update(idx=k, label=label(spec), fam=spec[0], spec=[spec[1], list(spec[2])],
                   dS_S=ev['s_sharpe'] - GLIVE_EV['s_sharpe'], dS_H=ev['h_sharpe'] - GLIVE_EV['h_sharpe'], dS_F=ev['sharpe'] - GLIVE_EV['sharpe'],
                   rvL=rev['sharpe'] - GREAL_EV['sharpe'])
        RES.append(rec); SER[k] = ser; RSER[k] = rser; FLAG[k] = (fq, fr)
        log(f"{k:>3} {rec['label']:<44}{rec['n_flag']:>5}{rec['n_flag_ep']:>4}{rec['n_on']:>5}{rec['n_on_ep']:>4}{ev['cagr']*100:>6.2f}%{ev['sharpe']:>7.3f}{ev['mdd']*100:>6.1f}%{ev['risky']*100:>5.1f}%"
            f"{ev['reb']:>5.1f}{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f}{rec['dS_S']:>+7.3f}{rec['dS_H']:>+7.3f}{rec['dS_F']:>+7.3f} | "
            f"{rev['cagr']*100:>6.2f}%{rev['sharpe']:>6.3f}{rev['mdd']*100:>6.1f}%{rev['exp']*100:>4.0f}%{rev['reb']:>5.1f}{rec['n_flag_r']:>5}{rec['n_on_r']:>5}{rec['rvL']:>+7.3f}")

    # ---- deltas
    log(f"\n{'='*118}\nDELTAS: Sharpe vs (i) gated live, (ii) the constant-E control of the family's instrument matched to the nearest 10 % by "
        f"average exposure (CASH -> XLU ladder, RISK -> SPMO ladder), (iii) the BETTER of the member singles of the SAME family (per era)\n{'='*118}")
    log(f"{'#':>3} {'candidate':<44}{'ctrl':>9}{'vLive S':>8}{'vLive H':>8}{'vLive F':>8}{'vCtl S':>8}{'vCtl H':>8}{'vCtl F':>8}{'vBest S':>8}{'vBest H':>8}{'vBest F':>8}"
        f" | {'rctl':>9}{'rvLive':>7}{'rvCtl':>7}{'rvBest':>7}  adds?  both-era?")
    SINGLE = {(r['fam'], r['spec'][1][0]): r for r in RES if r['spec'][0] == 'single'}
    for rec in RES:
        ev, rev = rec['ev'], rec['real']; fam = rec['fam']
        c = match_ctrl(fam, ev['risky'], 'ev'); cr = match_ctrl(fam, rev['exp'], 'real')
        rec['ctrl'] = f"{c['inst']} {c['f']}%"; rec['rctrl'] = f"{cr['inst']} {cr['f']}%"
        rec['vC_S'] = ev['s_sharpe'] - c['ev']['s_sharpe']; rec['vC_H'] = ev['h_sharpe'] - c['ev']['h_sharpe']; rec['vC_F'] = ev['sharpe'] - c['ev']['sharpe']
        rec['rvC'] = rev['sharpe'] - cr['real']['sharpe']
        rec['both'] = rec['dS_S'] > 0 and rec['dS_H'] > 0
        rec['both_ctl'] = rec['vC_S'] > 0 and rec['vC_H'] > 0
        mem = rec['spec'][1]
        if len(mem) > 1:
            bs = max(SINGLE[(fam, n)]['ev']['s_sharpe'] for n in mem); bh = max(SINGLE[(fam, n)]['ev']['h_sharpe'] for n in mem)
            bf = max(SINGLE[(fam, n)]['ev']['sharpe'] for n in mem); br = max(SINGLE[(fam, n)]['real']['sharpe'] for n in mem)
            rec['vB_S'] = ev['s_sharpe'] - bs; rec['vB_H'] = ev['h_sharpe'] - bh; rec['vB_F'] = ev['sharpe'] - bf; rec['rvB'] = rev['sharpe'] - br
            rec['best_single'] = max(mem, key=lambda n: SINGLE[(fam, n)]['ev']['sharpe'])
            rec['best_single_real'] = max(mem, key=lambda n: SINGLE[(fam, n)]['real']['sharpe'])
            rec['adds'] = rec['vB_S'] > 0 and rec['vB_H'] > 0
            vb = f"{rec['vB_S']:>+8.3f}{rec['vB_H']:>+8.3f}{rec['vB_F']:>+8.3f} | {rec['rctrl']:>9}{rec['rvL']:>+7.3f}{rec['rvC']:>+7.3f}{rec['rvB']:>+7.3f}  {'ADDS' if rec['adds'] else 'no  '}"
        else:
            rec['adds'] = None
            vb = f"{'':>24} | {rec['rctrl']:>9}{rec['rvL']:>+7.3f}{rec['rvC']:>+7.3f}{'':>7}  --  "
        log(f"{rec['idx']:>3} {rec['label']:<44}{rec['ctrl']:>9}{rec['dS_S']:>+8.3f}{rec['dS_H']:>+8.3f}{rec['dS_F']:>+8.3f}{rec['vC_S']:>+8.3f}{rec['vC_H']:>+8.3f}{rec['vC_F']:>+8.3f}" + vb
            + f"   {'BOTH' if rec['both'] else 'no'}{'+ctl' if rec['both'] and rec['both_ctl'] else ''}")
    both = [r for r in RES if r['both']]
    log(f"\n  candidates with Sharpe above gated live in BOTH proxy eras: {len(both)} of {N_CAND}: "
        + (", ".join(f"#{r['idx']} {r['label']} (S {r['dS_S']:+.3f}, H {r['dS_H']:+.3f}, real {r['rvL']:+.3f}, vs ctl S {r['vC_S']:+.3f} H {r['vC_H']:+.3f})" for r in both) if both else "(none)"))
    bc = [r for r in both if r['both_ctl'] and r['rvL'] > 0 and r['real']['cagr'] >= GREAL_EV['cagr']]
    log(f"  ... of which also above the matched control in both eras, above live on the real rows AND real CAGR not lower: {len(bc)}: "
        + (", ".join(f"#{r['idx']} {r['label']}" for r in bc) if bc else "(none)"))
    adders = [r for r in RES if r['adds']]
    log(f"  combinations that beat the better of their own family singles in BOTH proxy eras: {len(adders)} of {N_CAND - 2*K}: "
        + (", ".join(f"#{r['idx']} {r['label']} (S {r['vB_S']:+.3f}, H {r['vB_H']:+.3f}, real {r['rvB']:+.3f})" for r in adders) if adders else "(none)"))
    picks = {}
    for fam in FAMILIES:
        picks[f'{fam}_single'] = max((r for r in RES if r['fam'] == fam and len(r['spec'][1]) == 1), key=lambda r: r['ev']['sharpe'])['idx']
        picks[f'{fam}_combo'] = max((r for r in RES if r['fam'] == fam and len(r['spec'][1]) > 1), key=lambda r: r['ev']['sharpe'])['idx']
        picks[f'{fam}_single_real'] = max((r for r in RES if r['fam'] == fam and len(r['spec'][1]) == 1), key=lambda r: r['real']['sharpe'])['idx']
        picks[f'{fam}_combo_real'] = max((r for r in RES if r['fam'] == fam and len(r['spec'][1]) > 1), key=lambda r: r['real']['sharpe'])['idx']
    picks['overall'] = max(RES, key=lambda r: r['ev']['sharpe'])['idx']
    picks['overall_both'] = max(RES, key=lambda r: min(r['dS_S'], r['dS_H']))['idx']
    picks['overall_real'] = max(RES, key=lambda r: r['real']['sharpe'])['idx']
    log("\n  picks (by full-period proxy Sharpe unless noted): " + "; ".join(f"{k} #{v} {RES[v]['label']} ({RES[v]['ev']['sharpe']:.3f} / real {RES[v]['real']['sharpe']:.3f})" for k, v in picks.items()))
    json.dump(dict(res=RES, ctrl=CTRL, pairs={f"{a}|{b}": v for (a, b), v in PAIRS.items()}, picks=picks, rates=RATES, dropped=DROPPED,
                   glive=dict(GLIVE_EV, exp=GLIVE_EXP, reb=GLIVE_REB), greal=dict(GREAL_EV, exp=GREAL_EXP, reb=GREAL_REB),
                   ladder_range=dict(full=rng_f, s=rng_s, h=rng_h, real=rng_r)), open(JS_GRID, 'w'))
    log(f"\n[grid saved: {JS_GRID}]  elapsed {time.time()-T0:.0f}s")

# ================================================================= STAGE perm
LIVE_F_SH = bstats(GLIVE_SER)[1]
LIVE_S_SL = sliced_sharpe(GLIVE_SER, *SEARCH); LIVE_H_SL = sliced_sharpe(GLIVE_SER, *HOLDOUT)
SINGLE_IDX = {(spec[0], spec[2][0]): k for k, spec in enumerate(CANDS) if spec[1] == 'single'}
def _stats_for(FL):
    """(dF, dS, dH) vs gated live for every candidate under E-day flag sequences FL."""
    out = []
    for spec in CANDS:
        fl = combine(spec, FL); on = on_days(spec, fl, E_DATES); row = FAM_ROW[spec[0]]
        ser, _ = run(rows, lambda r: vt(row, r['vol']) if r['d'] in on else GBASE[r['d']])
        out.append((bstats(ser)[1] - LIVE_F_SH, sliced_sharpe(ser, *SEARCH) - LIVE_S_SL, sliced_sharpe(ser, *HOLDOUT) - LIVE_H_SL))
    return out
def _summ(st):
    """max over the grid of: dF; min(dS,dH); combo-minus-best-member dF; combo-minus-best-member both-era."""
    bF = max(s[0] for s in st); bB = max(min(s[1], s[2]) for s in st)
    gF = -9.0; gB = -9.0
    for k, spec in enumerate(CANDS):
        fam, _, mem = spec
        if len(mem) < 2: continue
        mF = max(st[SINGLE_IDX[(fam, n)]][0] for n in mem); mS = max(st[SINGLE_IDX[(fam, n)]][1] for n in mem); mH = max(st[SINGLE_IDX[(fam, n)]][2] for n in mem)
        gF = max(gF, st[k][0] - mF); gB = max(gB, min(st[k][1] - mS, st[k][2] - mH))
    return bF, bB, gF, gB
def _perm_worker(args):
    s, = args
    FL = {n: [FLQ[n][(j + s) % nE] for j in range(nE)] for n in RNAMES}
    st = _stats_for(FL)
    return _summ(st), [x[0] for x in st], [min(x[1], x[2]) for x in st]

if STAGE in ('all', 'perm'):
    G = json.load(open(JS_GRID)); RES = G['res']
    log(f"\n{'='*118}\nPERMUTATION: whole-grid max statistic over all {N_CAND} candidates (both families), {N_PERM} common circular shifts of the "
        f"{nE}-day E flag sequences (all {K} rules shifted together, so overlap between rules is preserved)\n{'='*118}")
    rng = random.Random(SEED); shifts = [rng.randrange(1, nE) for _ in range(N_PERM)]
    from multiprocessing import Pool
    t1 = time.time()
    with Pool(N_PROCS) as pool:
        outs = pool.map(_perm_worker, [(s,) for s in shifts], chunksize=2)
    log(f"  {N_PERM} permutations in {time.time()-t1:.0f}s")
    real = _stats_for(FLQ)
    for k, (dF, dS, dH) in enumerate(real):
        assert abs(dF - RES[k]['dS_F']) < 1e-9
    rF, rB, rgF, rgB = _summ(real)
    q = lambda v, p: v[min(len(v) - 1, int(len(v) * p))]
    names = [f'best-of-{N_CAND} full-period Sharpe gain vs live', f'best-of-{N_CAND} both-era gain min(dS_S, dS_H) vs live',
             f'best-of-{N_CAND - 2*K} combo gain over its best member single (full)', f'best-of-{N_CAND - 2*K} combo gain over its best member (both-era min)']
    reals = [rF, rB, rgF, rgB]
    def _gain(k, both_):
        fam, _, mem = CANDS[k]
        if len(mem) < 2: return -9.0
        if not both_: return real[k][0] - max(real[SINGLE_IDX[(fam, n)]][0] for n in mem)
        return min(real[k][1] - max(real[SINGLE_IDX[(fam, n)]][1] for n in mem), real[k][2] - max(real[SINGLE_IDX[(fam, n)]][2] for n in mem))
    bests = [max(range(N_CAND), key=lambda k: real[k][0]), max(range(N_CAND), key=lambda k: min(real[k][1], real[k][2])),
             max(range(N_CAND), key=lambda k: _gain(k, False)), max(range(N_CAND), key=lambda k: _gain(k, True))]
    P = dict(shifts=shifts)
    for i, nm in enumerate(names):
        null = sorted(o[0][i] for o in outs); p = sum(1 for x in null if x >= reals[i]) / N_PERM
        P[f'null{i}'] = null; P[f'real{i}'] = reals[i]; P[f'p{i}'] = p
        log(f"  {nm}: null median {q(null,0.5):+.3f}  95th {q(null,0.95):+.3f}  max {null[-1]:+.3f} | best real {reals[i]:+.3f} -> p = {p:.3f}")
    log("  best real candidate per statistic: " + "; ".join(f"stat {i+1} #{b} {RES[b]['label']}" for i, b in enumerate(bests)))
    # per-family maxima (the same null draws, restricted to one family) for the record
    for fam in FAMILIES:
        ks = [k for k, spec in enumerate(CANDS) if spec[0] == fam]
        nullF = sorted(max(o[1][k] for k in ks) for o in outs); nullB = sorted(max(o[2][k] for k in ks) for o in outs)
        bF_ = max(real[k][0] for k in ks); bB_ = max(min(real[k][1], real[k][2]) for k in ks)
        log(f"  family {fam} only ({len(ks)} candidates): full gain null median {q(nullF,0.5):+.3f} 95th {q(nullF,0.95):+.3f}, best real {bF_:+.3f} "
            f"p {sum(1 for x in nullF if x >= bF_)/N_PERM:.3f}; both-era null 95th {q(nullB,0.95):+.3f}, best real {bB_:+.3f} p {sum(1 for x in nullB if x >= bB_)/N_PERM:.3f}")
        P[f'fam_{fam}'] = dict(nullF=nullF, nullB=nullB, bF=bF_, bB=bB_)
    per_p = [sum(1 for o in outs if o[0][0] >= real[k][0]) / N_PERM for k in range(N_CAND)]
    P['per_cand_p'] = per_p
    # single-candidate null spread (no max-over-grid): sd and 95th of each candidate's own null dF and both-era stat
    P['cand_null_sd'] = []; P['cand_null_95'] = []; P['cand_null_both_95'] = []
    for k in range(N_CAND):
        v = [o[1][k] for o in outs]; m = sum(v) / len(v); sd = (sum((x - m) ** 2 for x in v) / (len(v) - 1)) ** 0.5
        vb = sorted(o[2][k] for o in outs)
        P['cand_null_sd'].append(sd); P['cand_null_95'].append(q(sorted(v), 0.95)); P['cand_null_both_95'].append(q(vb, 0.95))
    log("  per-candidate p on the best-of-grid full-period null: " + ", ".join(f"#{k} {per_p[k]:.2f}" for k in range(N_CAND)))
    log("  per-candidate OWN null (no max over grid) sd of dF: median over candidates "
        f"{sorted(P['cand_null_sd'])[N_CAND//2]:.3f}, range {min(P['cand_null_sd']):.3f}..{max(P['cand_null_sd']):.3f}; "
        f"own-null 95th of dF: median {sorted(P['cand_null_95'])[N_CAND//2]:+.3f}")
    json.dump(P, open(JS_PERM, 'w'))
    log(f"[perm saved: {JS_PERM}]  elapsed {time.time()-T0:.0f}s")

# ================================================================= STAGE diag
def spy_setup():
    SP_ROWS, SP_D, SIG_S = DSF.build_spy_rows()
    SPY = DSF.SPY; RSP = load_dc('data/RSP_daily.csv')
    v = [SPY[d] for d in SP_D]; sp_px = {d: SPY[d] for d in SP_D}
    bp = breadth_pct(sp_px, other=RSP)          # SPY analogue of breadth: RSP/SPY 60-session change, bottom quintile
    F = build_flags(SP_D, v, SIG_S, bp)
    SPIX = {d: i for i, d in enumerate(SP_D)}
    # the D gate analogue on SPY (RSP/SPY breadth OR gap200 < 2 %), so the SPY baseline is the same design
    gate = set(r['d'] for r in SP_ROWS if r['state'] == 'D' and d_gate_active('D', bp.get(r['d']), r['gaps'][200]))
    SPB0 = {r['d']: live_fn(r) for r in SP_ROWS}
    SPB = {r['d']: (vt(CASH, r['vol']) if r['d'] in gate else SPB0[r['d']]) for r in SP_ROWS}
    E_IDX = [i for i, r in enumerate(SP_ROWS) if r['state'] == 'E']
    ed = [SP_ROWS[i]['d'] for i in E_IDX]
    FL = {n: [F[n][SPIX[d]] for d in ed] for n in RNAMES}
    base0 = evaluate(SP_ROWS, lambda r: SPB0[r['d']]); base = evaluate(SP_ROWS, lambda r: SPB[r['d']])
    def ev_of(spec):
        fl = combine(spec, FL); on = on_days(spec, fl, ed); row = FAM_ROW[spec[0]]
        e = evaluate(SP_ROWS, lambda r: vt(row, r['vol']) if r['d'] in on else SPB[r['d']])
        return e, len(on), sum(fl)
    rates = {n: sum(1 for j in range(len(ed)) if FL[n][j] and F['_avail'][n][SPIX[ed[j]]]) / max(1, sum(1 for d in ed if F['_avail'][n][SPIX[d]])) for n in RNAMES}
    return base0, base, ev_of, len(SP_ROWS), len(E_IDX), len(gate), rates

def deep(rec, ref_label, ref_ser, ref_rser, extra_refs=()):
    k = rec['idx']; spec = (rec['fam'], rec['spec'][0], tuple(rec['spec'][1]))
    ser, rser = SER[k], RSER[k]
    log(f"\n{'-'*118}\nDEEP #{k}: {rec['label']}   proxy {fmt_ev(rec['ev'])} S {rec['ev']['s_sharpe']:.3f} H {rec['ev']['h_sharpe']:.3f} exp {rec['ev']['risky']*100:.1f}% "
        f"reb {rec['ev']['reb']:.1f}/yr | real {fmt_ev(rec['real'])} exp {rec['real']['exp']*100:.0f}% reb {rec['real']['reb']:.0f}/yr | flagged {rec['n_flag']} E days, moved {rec['n_on']} (real {rec['n_flag_r']} / {rec['n_on_r']})")
    log(f"  (a) circular block bootstrap (2000 draws) of the Sharpe / log-return difference:")
    for lab, a, b in ((f'proxy vs {ref_label}', ser, ref_ser), (f'real daily vs {ref_label}', rser, ref_rser)) + tuple(extra_refs):
        for blk in (20, 60):
            l1, l2, pl, s1, s2, ps = boot(a, b, blk, seed=(k * 7919 + blk + len(lab)) & 0xffff)
            log(f"      {lab:<44} block {blk:>2}d: Sharpe 95% CI [{s1:+.3f}, {s2:+.3f}] P(<=0)={ps:.3f}   log-return [{l1*100:+.2f}, {l2*100:+.2f}] pp/yr P(<=0)={pl:.3f}")
    log(f"  (b) leave-one-major-regime-out, proxy (Sharpe difference vs {ref_label}, that window removed):")
    for rlab, a0, b0 in REGIMES:
        keep = [i for i, r in enumerate(rows) if not (a0 <= r['d'] <= b0)]
        sa = bstats([ser[i] for i in keep])[1]; sb = bstats([ref_ser[i] for i in keep])[1]; sl = bstats([GLIVE_SER[i] for i in keep])[1]
        log(f"      drop {rlab:<26} vs {ref_label}: {sa-sb:+.3f}" + (f"   vs live: {sa-sl:+.3f}" if ref_label != 'live' else ""))
    recL, _, _, _, _ = eval_candidate(spec, FLQ_LAG, FLR_LAG)
    log(f"  (c) one-extra-session lag (flag from the previous close): proxy {fmt_ev(recL['ev'])} S {recL['ev']['s_sharpe']:.3f} H {recL['ev']['h_sharpe']:.3f} "
        f"(dS vs live S {recL['ev']['s_sharpe']-GLIVE_EV['s_sharpe']:+.3f} H {recL['ev']['h_sharpe']-GLIVE_EV['h_sharpe']:+.3f} F {recL['ev']['sharpe']-GLIVE_EV['sharpe']:+.3f}) | "
        f"real {fmt_ev(recL['real'])} ({recL['real']['sharpe']-GREAL_EV['sharpe']:+.3f} vs live)")
    DSF.ONE_WAY_SPREAD = IS.ONE_WAY_SPREAD = 0.002; MR.ONE_WAY = 0.002
    try:
        live20, _ = proxy_eval(set(), CASH); rlive20, _ = real_eval(set(), CASH)
        rec20, _, _, _, _ = eval_candidate(spec)
    finally:
        DSF.ONE_WAY_SPREAD = IS.ONE_WAY_SPREAD = 0.0004; MR.ONE_WAY = 0.0004
    log(f"  (d) 20 bp one-way cost: live proxy {fmt_ev(live20)} S {live20['s_sharpe']:.3f} H {live20['h_sharpe']:.3f}; candidate {fmt_ev(rec20['ev'])} "
        f"S {rec20['ev']['s_sharpe']:.3f} H {rec20['ev']['h_sharpe']:.3f} (vs live S {rec20['ev']['s_sharpe']-live20['s_sharpe']:+.3f} H {rec20['ev']['h_sharpe']-live20['h_sharpe']:+.3f} "
        f"F {rec20['ev']['sharpe']-live20['sharpe']:+.3f}) | real live {fmt_ev(rlive20)} candidate {fmt_ev(rec20['real'])} ({rec20['real']['sharpe']-rlive20['sharpe']:+.3f})")
    e, n_on, n_fl = SPY_EV(spec)
    log(f"  (e) SPY-core proxy (gated), same rule(s) on SPY (breadth analogue = RSP/SPY): {fmt_ev(e)} S {e['s_sharpe']:.3f} H {e['h_sharpe']:.3f}  "
        f"dS vs SPY-live S {e['s_sharpe']-SPY_BASE['s_sharpe']:+.3f} H {e['h_sharpe']-SPY_BASE['h_sharpe']:+.3f} F {e['sharpe']-SPY_BASE['sharpe']:+.3f}  flagged {n_fl}, moved {n_on}")

def episode_gains(k, harness):
    """per E EPISODE: log-return difference candidate minus gated live accumulated over the episode's days, and how many
    of its days were moved to the action row."""
    fq, fr = FLAG[k]
    if harness == 'proxy':
        eps, ser, base, dates, on = E_EPS, SER[k], GLIVE_SER, [r['d'] for r in rows], set(d for d, f in zip(E_DATES, fq) if (f if RES[k]['fam'] == 'CASH' else not f))
    else:
        eps, ser, base, dates, on = RE_EPS, RSER[k], GREAL_SER, RDAYS[:-1], set(d for d, f in zip(RE_DATES, fr) if (f if RES[k]['fam'] == 'CASH' else not f))
    out = []
    for a, b, n in eps:
        g = sum(math.log1p(ser[i]) - math.log1p(base[i]) for i in range(a, b + 1))
        nm = sum(1 for i in range(a, b + 1) if dates[i] in on)
        out.append((dates[a], dates[b], n, nm, g))
    return out

if STAGE in ('all', 'diag'):
    G = json.load(open(JS_GRID)); P = json.load(open(JS_PERM)); RES = G['res']; CTRL = G['ctrl']; PK = G['picks']
    log(f"\n{'='*118}\nDIAGNOSTICS\n{'='*118}")
    SER = {}; RSER = {}; FLAG = {}
    for k, spec in enumerate(CANDS):
        rec, ser, rser, fq, fr = eval_candidate(spec); SER[k] = ser; RSER[k] = rser; FLAG[k] = (fq, fr)
        assert abs(rec['ev']['sharpe'] - RES[k]['ev']['sharpe']) < 1e-9
    FLQ_LAG = dseq(lagged(FQ), E_DATES, QIX); FLR_LAG = dseq(lagged(FR), RE_DATES, RIX)
    SPY_BASE0, SPY_BASE, SPY_EV, n_sp, n_spe, n_spg, sp_rates = spy_setup()
    log(f"SPY-core proxy: ungated live {fmt_ev(SPY_BASE0)} S {SPY_BASE0['s_sharpe']:.3f} H {SPY_BASE0['h_sharpe']:.3f}; GATED live (RSP/SPY breadth OR gap200<2% on "
        f"{n_spg} D days) {fmt_ev(SPY_BASE)} S {SPY_BASE['s_sharpe']:.3f} H {SPY_BASE['h_sharpe']:.3f} ({n_sp} rows, {n_spe} E days)")
    log("  SPY E-day flag rates: " + ", ".join(f"{n} {sp_rates[n]*100:.0f}%" for n in RNAMES))
    log("  the singles on SPY (both families):")
    for fam in FAMILIES:
        for n in RNAMES:
            e, n_on, n_fl = SPY_EV((fam, 'single', (n,)))
            log(f"    {fam}: {n:<14} {fmt_ev(e)}  dS S {e['s_sharpe']-SPY_BASE['s_sharpe']:+.3f} H {e['h_sharpe']-SPY_BASE['h_sharpe']:+.3f} F {e['sharpe']-SPY_BASE['sharpe']:+.3f}  flagged {n_fl} moved {n_on}")
    CTRL_SER = {}
    def ctrl_series(inst, f):
        if (inst, f) not in CTRL_SER:
            row = (0.0, 0.0, 0.0, f / 100.0, 1 - f / 100.0) if inst == 'XLU' else (f / 100.0, 0.0, 0.0, 0.0, 1 - f / 100.0)
            _, s = proxy_eval(set(E_DATES), row); _, rs = real_eval(set(RE_DATES), row); CTRL_SER[(inst, f)] = (s, rs)
        return CTRL_SER[(inst, f)]
    def parse_ctrl(s):
        inst, f = s.split(); return inst, int(f.rstrip('%'))

    q = lambda v, p: v[min(len(v) - 1, int(len(v) * p))]
    log(f"\nPERMUTATION recap ({len(P['shifts'])} shifts): best-of-{N_CAND} full gain null median {q(P['null0'],0.5):+.3f} 95th {q(P['null0'],0.95):+.3f}, "
        f"best real {P['real0']:+.3f} p {P['p0']:.3f}; both-era null 95th {q(P['null1'],0.95):+.3f}, best real {P['real1']:+.3f} p {P['p1']:.3f}; "
        f"combo-over-best-member null 95th {q(P['null2'],0.95):+.3f}, best real {P['real2']:+.3f} p {P['p2']:.3f}; both-era {q(P['null3'],0.95):+.3f} / {P['real3']:+.3f} p {P['p3']:.3f}")

    # ---- E episode census
    log(f"\n{'='*118}\nE EPISODES (proxy): dates, sessions, QQQ-core-leg compounded return, gated-live compounded return over the episode, and which rules flag it\n{'='*118}")
    log(f"{'#':>3} {'start':<11}{'end':<11}{'n':>4}{'QQQ':>8}{'XLU':>8}{'live':>8}  " + "".join(f"{SHORT[n]:>6}" for n in RNAMES) + "   (fraction of the episode's days each rule flags)")
    for e_i, (a, b, n) in enumerate(E_EPS):
        qq = math.exp(sum(math.log1p(rows[i]['legs'][0]) for i in range(a, b + 1))) - 1
        xl = math.exp(sum(math.log1p(rows[i]['legs'][3]) for i in range(a, b + 1))) - 1
        lv = math.exp(sum(math.log1p(GLIVE_SER[i]) for i in range(a, b + 1))) - 1
        fr_ = [sum(1 for i in range(a, b + 1) if FLQ[nm][EIDX[rows[i]['d']]]) / n for nm in RNAMES]
        log(f"{e_i:>3} {rows[a]['d']:<11}{rows[b]['d']:<11}{n:>4}{qq*100:>+7.1f}%{xl*100:>+7.1f}%{lv*100:>+7.1f}%  " + "".join(f"{x:>6.2f}" for x in fr_))
    log(f"\nE EPISODES (real daily): {len(RE_EPS)}")
    log(f"{'#':>3} {'start':<11}{'end':<11}{'n':>4}{'live':>8}  " + "".join(f"{SHORT[n]:>6}" for n in RNAMES))
    for e_i, (a, b, n) in enumerate(RE_EPS):
        lv = math.exp(sum(math.log1p(GREAL_SER[i]) for i in range(a, b + 1))) - 1
        fr_ = [sum(1 for i in range(a, b + 1) if FLR[nm][REIDX[RDAYS[i]]]) / n for nm in RNAMES]
        log(f"{e_i:>3} {RDAYS[a]:<11}{RDAYS[b]:<11}{n:>4}{lv*100:>+7.1f}%  " + "".join(f"{x:>6.2f}" for x in fr_))

    # ---- drawdown episodes / MaxDD windows for the singles of both families
    log(f"\n{'='*118}\nDRAWDOWN EPISODES: live MaxDD window, each single's MaxDD window, its drawdown inside the live window, per-episode gain vs live\n{'='*118}")
    for hn, ser0, dates0 in (('proxy', GLIVE_SER, [r['d'] for r in rows]), ('real daily', GREAL_SER, RDAYS[:-1])):
        p0, t0, m0, r0 = dd_window(ser0, dates0)
        log(f"  {hn} GATED LIVE max drawdown {m0*100:.1f}%: peak {p0} -> trough {t0}, recovered {r0}")
        for fam in FAMILIES:
            for n in RNAMES:
                k = SINGLE_IDX[(fam, n)]; rec = RES[k]
                ser = SER[k] if hn == 'proxy' else RSER[k]
                p1, t1, m1, r1 = dd_window(ser, dates0)
                nav = 1.0; pk = 1.0; dd_live_win = 0.0
                for d, x in zip(dates0, ser):
                    if p0 <= d <= t0:
                        nav *= 1 + x; pk = max(pk, nav); dd_live_win = min(dd_live_win, nav / pk - 1)
                eps = episode_gains(k, 'proxy' if hn == 'proxy' else 'real')
                moved = [e for e in eps if e[3] > 0]
                inwin = [e for e in moved if not (e[1] < p0 or e[0] > t0)]
                srt = sorted(moved, key=lambda e: -e[4])
                log(f"    {rec['label']:<28} MaxDD {m1*100:.1f}% ({p1} -> {t1}); DD inside live window {dd_live_win*100:.1f}%; touches {len(moved)}/{len(eps)} E episodes, "
                    f"{len(inwin)} inside the live window ({sum(e[3] for e in inwin)} moved days, {sum(e[4] for e in inwin)*100:+.1f} pp vs live); total vs live {sum(e[4] for e in eps)*100:+.1f} pp; "
                    f"episodes positive {sum(1 for e in moved if e[4] > 0)}/{len(moved)}")
                log(f"        best: " + "; ".join(f"{a}..{b} ({n_}d, {nm} moved, {g*100:+.1f}pp)" for a, b, n_, nm, g in srt[:4])
                    + "  | worst: " + "; ".join(f"{a}..{b} ({nm} moved, {g*100:+.1f}pp)" for a, b, n_, nm, g in srt[-2:]))

    # ---- deep block: best single per family, best combination per family, best overall
    log(f"\n{'='*118}\nDEEP DIAGNOSTICS: best single per family, best combination per family (by full-period proxy Sharpe), best overall\n{'='*118}")
    done = set()
    order = [PK['CASH_single'], PK['CASH_combo'], PK['RISK_single'], PK['RISK_combo'], PK['overall']]
    for k in order:
        if k in done:
            log(f"\n  (#{k} {RES[k]['label']} already covered above)"); continue
        done.add(k); rec = RES[k]
        ci, cf = parse_ctrl(rec['ctrl']); rci, rcf = parse_ctrl(rec['rctrl'])
        refs = ((f"proxy vs constant-E {ci} {cf}% (matched)", SER[k], ctrl_series(ci, cf)[0]),
                (f"real vs constant-E {rci} {rcf}% (matched)", RSER[k], ctrl_series(rci, rcf)[1]))
        if len(rec['spec'][1]) > 1:
            b1 = rec['best_single']; kb = SINGLE_IDX[(rec['fam'], b1)]
            refs += ((f"proxy vs better member single ({rec['fam']}: {b1})", SER[k], SER[kb]), (f"real vs better member single ({rec['fam']}: {b1})", RSER[k], RSER[kb]))
        deep(rec, 'live', GLIVE_SER, GREAL_SER, extra_refs=refs)
        # per-episode gains for the deep candidates (proxy and real), all E episodes it touches
        for hn in ('proxy', 'real'):
            eps = episode_gains(k, hn); moved = [e for e in eps if e[3] > 0]
            srt = sorted(moved, key=lambda e: -e[4])
            log(f"  (f) {hn} per-episode gain vs live ({len(moved)} of {len(eps)} E episodes touched; total {sum(e[4] for e in eps)*100:+.1f} pp; "
                f"positive {sum(1 for e in moved if e[4] > 0)}): " + "; ".join(f"{a}..{b} ({nm}/{n_}d {g*100:+.1f}pp)" for a, b, n_, nm, g in srt))
    extra = [PK['overall_both'], PK['overall_real']]
    for k in extra:
        if k not in done:
            log(f"\n  (best by both-era min / by real Sharpe differs: #{k} {RES[k]['label']})")
            done.add(k); rec = RES[k]
            ci, cf = parse_ctrl(rec['ctrl']); rci, rcf = parse_ctrl(rec['rctrl'])
            deep(rec, 'live', GLIVE_SER, GREAL_SER, extra_refs=((f"proxy vs constant-E {ci} {cf}% (matched)", SER[k], ctrl_series(ci, cf)[0]),
                                                                 (f"real vs constant-E {rci} {rcf}% (matched)", RSER[k], ctrl_series(rci, rcf)[1])))

    # ---- statistical power
    log(f"\n{'='*118}\nSTATISTICAL POWER\n{'='*118}")
    nS_ep = sum(1 for e in E_EPS if rows[e[0]]['d'] >= SEARCH[0]); nH_ep = len(E_EPS) - nS_ep
    log(f"  sample: {nE} proxy E days in {len(E_EPS)} episodes (search {nS_ep}, holdout {nH_ep}); {len(RE_DATES)} real E days in {len(RE_EPS)} episodes; "
        f"median episode {med([e[2] for e in E_EPS]):.0f} sessions. Effective independent observations for an E-only rule are the EPISODES, not the days.")
    log(f"  detectable effect at the grid level (null = best of {N_CAND} random E-day splits, 1000 draws): a true full-period Sharpe gain must exceed "
        f"{q(P['null0'],0.95):+.3f} (95th) to clear p < 0.05; both-era min gain must exceed {q(P['null1'],0.95):+.3f}; a combination must add "
        f"{q(P['null3'],0.95):+.3f} over its best member in both eras.")
    log(f"  detectable effect for ONE pre-registered candidate (its own null, no max over the grid): median own-null 95th of dF {sorted(P['cand_null_95'])[N_CAND//2]:+.3f}, "
        f"own-null sd {sorted(P['cand_null_sd'])[N_CAND//2]:.3f}; both-era own-null 95th median {sorted(P['cand_null_both_95'])[N_CAND//2]:+.3f}.")
    LR = G['ladder_range']
    log(f"  the ENTIRE constant-E ladder (cash .. 100 % XLU .. 100 % SPMO on every E day) spans full-period Sharpe {LR['full']:.3f}, S {LR['s']:.3f}, H {LR['h']:.3f}, "
        f"real {LR['real']:.3f}: that is the ceiling on what any E-row rule can move. Grid-level 95th null {q(P['null0'],0.95):+.3f} full / {q(P['null1'],0.95):+.3f} both-era.")
    best = RES[PK['overall']]
    l1, l2, pl, s1, s2, ps = boot(SER[best['idx']], GLIVE_SER, 60, seed=1234)
    rl1, rl2, rpl, rs1, rs2, rps = boot(RSER[best['idx']], GREAL_SER, 60, seed=1234)
    log(f"  bootstrap resolution for the best overall (#{best['idx']}): proxy Sharpe-difference 95% CI width {s2-s1:.3f} (60d blocks), real {rs2-rs1:.3f}: "
        f"an E-row effect smaller than roughly half those widths cannot be told from zero on this sample.")
    log(f"\n[diag done]  elapsed {time.time()-T0:.0f}s")
