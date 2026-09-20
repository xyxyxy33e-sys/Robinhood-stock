"""EXTENSION_STEP: keep 1/3, or move to 0.5?  ONE decision, TWO schedules.

Owner question (2026-09-20): `state.EXTENSION_STEP` is 1/3, so the A-row risky
legs are scaled by 1 / .67 / .33 / 0 at 0/1/2/3 extension votes. Is 0.5
(1 / .5 / 0 / 0) better? Exactly two schedules are scored. This is NOT a
search: no third schedule, no threshold tuning, no destination variants (that
question was answered in trim_destination_test.py -- cash is the right
destination; the ladders there are about DEPTH, which is what this file
decides).

CODE FACT, verified at import below: `state.extension_scale()` returns
`1.0 - EXTENSION_STEP * votes` with NO clip at zero. At STEP 0.5 that is -0.5
at three votes, i.e. NEGATIVE risky weights. This harness clips at zero, and
ADOPTING 0.5 would require a one-line clip in state.py first; without it
`validate_weights` raises and the live trigger aborts rather than trades on
3-vote days (fail-safe, but it stops trading on exactly the days the trim is
meant to act).

Baseline is the CURRENT live design: A 50/50, B 75/25, C core, D 100% QLD with
the state-D gate, E 100% cash, F cash, 20/100 fast overlay, graded trim, 20%
vol target on plain 30d vol, 5% band, 4bp. Both harnesses are borrowed from
trim_destination_test.py (imported with TDT_STAGE=none), which builds them by
explicit override on d_substate_fresh exactly as its Part III does, and which
asserts proxy 25.46% / 1.071 / -27.0% (S 1.399, H 0.825) and real daily
37.30% / 1.475 / -18.6%.

Usage:  python3 paper-track/extension_step_decision.py
        ESD_NPERM=1000 ESD_PROCS=4 ESD_STAGE=all|main|perm|deep|sens
"""
import os, sys, io, json, math, time, random, contextlib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)
sys.path.insert(0, 'paper-track')
os.environ.setdefault('TDT_STAGE', 'none')          # import the harness, run none of its stages
SCRATCH = os.environ.get('ESD_SCRATCH',
                         '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad')
os.makedirs(SCRATCH, exist_ok=True)
STAGE = os.environ.get('ESD_STAGE', 'all')
N_PERM = int(os.environ.get('ESD_NPERM', '1000'))
N_PROCS = int(os.environ.get('ESD_PROCS', '4'))
SEED = 20260920
T0 = time.time()

LOG = 'paper-track/research_notes/extension_step_decision_run.log'
_lf = open(LOG, 'a')
def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s); _lf.write(s + '\n'); _lf.flush()

_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    import trim_destination_test as TDT
import state
from state import extension_scale, extension_votes, EXTENSION_RULES, EXTENSION_STEP, TARGET_WEIGHTS
from d_substate_fresh import (rows, run, vt, evaluate_full, real_metrics, RDAYS, SEARCH, HOLDOUT,
                              REGIMES, boot, bstats, sliced_sharpe)
from improvement_search_r2 import scaled

PDATES = TDT.PDATES; RD1 = TDT.RD1
LIVE_SER = TDT.LIVE_SER; RLIVE_SER = TDT.RLIVE_SER
LIVE_EV = TDT.LIVE_EV; RLIVE_EV = TDT.RLIVE_EV
A_IDX = TDT.A_IDX; VOTES_Q = TDT.VOTES_Q; VOTES_R = TDT.VOTES_R; OTHER_Q = TDT.OTHER_Q

# ---------------------------------------------------------------- the two schedules
def scalar_sched(step, a_row=(0.5, 0.5)):
    """A-row (SPMO, TQQQ, cash) at 0..3 votes for a scalar EXTENSION_STEP, CLIPPED at 0."""
    s, t = a_row
    out = []
    for v in range(4):
        f = max(0.0, 1.0 - step * v)
        out.append((s * f, t * f, 1.0 - (s + t) * f))
    return out

STEPS = {'0.25': 0.25, '1/3 LIVE': 1.0 / 3.0, '0.5': 0.5, '1.0': 1.0}
LIVE_STEP, CAND_STEP = 1.0 / 3.0, 0.5
S_LIVE = scalar_sched(LIVE_STEP)
S_CAND = scalar_sched(CAND_STEP)
for s in (S_LIVE, S_CAND):
    for a, b, c in s:
        assert abs(a + b + c - 1) < 1e-12 and min(a, b, c) >= -1e-12

def fmt_sched(s):
    return ' / '.join(f"({a*100:.0f},{b*100:.0f},{c*100:.0f})" for a, b, c in s)

# ---------------------------------------------------------------- evaluation on either harness
def proxy_eval_sched(sched, votes=None, a_scale=1.0):
    votes = VOTES_Q if votes is None else votes
    AT = {rows[i]['d']: [vt(TDT.srow(sched, v), rows[i]['vol']) for v in range(4)] for i in A_IDX}
    def fn(r):
        d = r['d']
        if d in votes: return AT[d][votes[d]]
        return OTHER_Q[d]
    return evaluate_full(fn)

def real_eval_sched(sched, **kw):
    return TDT.real_eval(sched, **kw)

def fmt_ev(ev): return TDT.fmt_ev(ev)

# ---------------------------------------------------------------- 0. header, code fact, baselines
def header():
    log("\n" + "=" * 118)
    log("RESEARCH LINE extension_step_decision -- EXTENSION_STEP 1/3 vs 0.5 (one decision, two schedules)")
    log("=" * 118)
    state.EXTENSION_STEP = 0.5
    hot = {100: 0.20, 150: 0.20, 200: 0.20}
    raw3 = extension_scale('A', hot)
    state.EXTENSION_STEP = LIVE_STEP
    log(f"  CODE FACT: state.extension_scale() = 1 - STEP*votes with NO clip. At STEP 0.5, 3 votes -> {raw3:+.3f} "
        f"(negative risky weights).")
    log(f"             This harness clips at 0. Adopting 0.5 REQUIRES a one-line clip in state.py; without it "
        f"validate_weights raises and the trigger aborts on 3-vote days.")
    log(f"  live EXTENSION_STEP = {EXTENSION_STEP:.4f}; A row {TARGET_WEIGHTS['A'][:2]}; rules {EXTENSION_RULES}")
    log(f"  schedule 1/3  (SPMO,TQQQ,cash) at 0/1/2/3 votes: {fmt_sched(S_LIVE)}")
    log(f"  schedule 0.5                                   : {fmt_sched(S_CAND)}")
    log(f"\n  BASELINE (asserted by trim_destination_test at import):")
    log(f"    proxy {fmt_ev(LIVE_EV)} S {LIVE_EV['s_sharpe']:.3f} H {LIVE_EV['h_sharpe']:.3f} exp {LIVE_EV['risky']*100:.1f}%")
    log(f"    real  {fmt_ev(RLIVE_EV)} exp {RLIVE_EV['exp']*100:.1f}% reb {RLIVE_EV['reb']:.1f}/yr")
    ev, _ = proxy_eval_sched(S_LIVE)
    assert abs(ev['sharpe'] - LIVE_EV['sharpe']) < 1e-9, 'scalar 1/3 schedule != harness live'
    log("    scalar-1/3 schedule reproduces the harness live arm exactly (asserted).")

JS = os.path.join(SCRATCH, 'esd.json')

# ---------------------------------------------------------------- 1-2. headline + controls
def stage_main():
    header()
    log("\n" + "=" * 118)
    log("HEADLINE. proxy full / search(2015-11+) / holdout(2000-07..2015-10); real daily. delta = 0.5 minus 1/3")
    log("=" * 118)
    out = {}
    for lab, step, sched in (('1/3 LIVE', LIVE_STEP, S_LIVE), ('0.5', CAND_STEP, S_CAND)):
        ev, ser = proxy_eval_sched(sched)
        rev, rser = real_eval_sched(sched)
        out[lab] = dict(ev=ev, ser=ser, real=rev, rser=rser, sched=sched)
        log(f"  {lab:<10} proxy {fmt_ev(ev)} S {ev['s_sharpe']:.3f} H {ev['h_sharpe']:.3f} exp {ev['risky']*100:.1f}% "
            f"reb {ev['reb']:.1f}/yr | real {fmt_ev(rev)} exp {rev['exp']*100:.1f}% reb {rev['reb']:.1f}/yr")
    a, b = out['1/3 LIVE'], out['0.5']
    log(f"  {'DELTA':<10} proxy CAGR {(b['ev']['cagr']-a['ev']['cagr'])*100:+.2f}pp  Sharpe {b['ev']['sharpe']-a['ev']['sharpe']:+.3f} "
        f"(S {b['ev']['s_sharpe']-a['ev']['s_sharpe']:+.3f}, H {b['ev']['h_sharpe']-a['ev']['h_sharpe']:+.3f})  "
        f"MaxDD {(b['ev']['mdd']-a['ev']['mdd'])*100:+.1f}pp | real CAGR {(b['real']['cagr']-a['real']['cagr'])*100:+.2f}pp "
        f"Sharpe {b['real']['sharpe']-a['real']['sharpe']:+.3f} MaxDD {(b['real']['mdd']-a['real']['mdd'])*100:+.1f}pp")
    log("\n  CROSS-CHECK vs the standalone loop (real daily): expected 0.5 -> 37.60% / 1.501 / -18.4% at 44.8 reb/yr")
    rv = b['real']
    ok = abs(rv['cagr'] * 100 - 37.60) < 0.05 and abs(rv['sharpe'] - 1.501) < 0.005 and abs(rv['mdd'] * 100 + 18.4) < 0.1
    log(f"    got {rv['cagr']*100:.2f}% / {rv['sharpe']:.3f} / {rv['mdd']*100:.1f}% at {rv['reb']:.1f} -> {'AGREES' if ok else 'DISAGREES'}")

    log("\n" + "=" * 118)
    log("EXPOSURE-MATCHED CONTROL (flat de-lever of LIVE to the 0.5 arm's average exposure)")
    log("=" * 118)
    ck, cev, cser = TDT.proxy_control(b['ev']['risky'])
    rck, rcev, rcser = TDT.real_control(b['real']['exp'])
    out['ctl'] = dict(k=ck, ev=cev, ser=cser); out['rctl'] = dict(k=rck, ev=rcev, ser=rcser)
    log(f"  proxy control k {ck:.4f}: {fmt_ev(cev)} S {cev['s_sharpe']:.3f} H {cev['h_sharpe']:.3f} exp {cev['risky']*100:.1f}%")
    log(f"    0.5 minus control: F {b['ev']['sharpe']-cev['sharpe']:+.3f}  S {b['ev']['s_sharpe']-cev['s_sharpe']:+.3f}  "
        f"H {b['ev']['h_sharpe']-cev['h_sharpe']:+.3f}")
    log(f"  real  control k {rck:.4f}: {fmt_ev(rcev)} exp {rcev['exp']*100:.1f}%")
    log(f"    0.5 minus control: {b['real']['sharpe']-rcev['sharpe']:+.3f}")

    log("\n" + "=" * 118)
    log("PER YEAR (0.5 minus 1/3), with extension-vote day counts")
    log("=" * 118)
    pby_a = TDT.byyear(a['ser'], PDATES); pby_b = TDT.byyear(b['ser'], PDATES)
    rby_a = TDT.byyear(a['rser'], RD1); rby_b = TDT.byyear(b['rser'], RD1)
    vq = {}
    for i in A_IDX:
        y = rows[i]['d'][:4]; vq.setdefault(y, [0, 0, 0, 0])[VOTES_Q[rows[i]['d']]] += 1
    vr = {}
    for d, v in VOTES_R.items():
        vr.setdefault(d[:4], [0, 0, 0, 0])[v] += 1
    log(f"  {'year':<6}{'proxy 1/3':>11}{'proxy 0.5':>11}{'diff':>8}   {'votes 0/1/2/3':<18}"
        f"{'real 1/3':>10}{'real 0.5':>10}{'diff':>8}   votes 0/1/2/3")
    for y in sorted(pby_a):
        c = vq.get(y, [0, 0, 0, 0]); rc = vr.get(y, [0, 0, 0, 0])
        rt = (f"{rby_a[y]*100:>9.1f}%{rby_b[y]*100:>9.1f}%{(rby_b[y]-rby_a[y])*100:>+8.1f}   "
              f"{rc[0]}/{rc[1]}/{rc[2]}/{rc[3]}") if y in rby_a else ''
        log(f"  {y:<6}{pby_a[y]*100:>10.1f}%{pby_b[y]*100:>10.1f}%{(pby_b[y]-pby_a[y])*100:>+8.1f}   "
            f"{c[0]}/{c[1]}/{c[2]}/{c[3]:<12}{rt}")

    log("\n" + "=" * 118)
    log("BEHAVIOUR")
    log("=" * 118)
    for lab, sched in (('1/3 LIVE', S_LIVE), ('0.5', S_CAND)):
        cnt = [0, 0, 0, 0]
        for i in A_IDX: cnt[VOTES_Q[rows[i]['d']]] += 1
        tot = sum(cnt)
        ev = a['ev'] if lab.startswith('1/3') else b['ev']
        rev = a['real'] if lab.startswith('1/3') else b['real']
        # fully-cash share over ALL proxy sessions
        fc = 0
        for r in rows:
            d = r['d']
            if d in VOTES_Q:
                w = TDT.srow(sched, VOTES_Q[d])
                if w[0] + w[1] < 1e-12: fc += 1
            else:
                w = OTHER_Q[d]
                if sum(w[:4]) < 1e-9: fc += 1
        run_best = run_cur = 0; bs = be = cs = None
        for r in rows:
            d = r['d']
            w = TDT.srow(sched, VOTES_Q[d]) if d in VOTES_Q else None
            isc = (w[0] + w[1] < 1e-12) if w is not None else (sum(OTHER_Q[d][:4]) < 1e-9)
            if isc:
                if run_cur == 0: cs = d
                run_cur += 1
                if run_cur > run_best: run_best, bs, be = run_cur, cs, d
            else: run_cur = 0
        log(f"  {lab:<10} longest continuous fully-cash stretch (proxy): {run_best} sessions {bs}..{be}")
        log(f"  {lab:<10} A-days 0/1/2/3 = {cnt[0]}/{cnt[1]}/{cnt[2]}/{cnt[3]} of {tot}; "
            f"proxy fully-cash {fc}/{len(rows)} = {fc/len(rows)*100:.1f}% of ALL sessions; "
            f"exposure {ev['risky']*100:.1f}% proxy / {rev['exp']*100:.1f}% real; reb {ev['reb']:.1f} proxy / {rev['reb']:.1f} real")
    json.dump({k: {kk: vv for kk, vv in v.items() if kk in ('ev', 'real', 'k')} for k, v in out.items()},
              open(JS + '.meta', 'w'), default=float)
    json.dump({k: {kk: vv for kk, vv in v.items() if kk in ('ser', 'rser')} for k, v in out.items()}, open(JS, 'w'))
    return out

# ---------------------------------------------------------------- 3. bootstrap
def _bw(args):
    lab, a, b, blk, seed = args
    return lab, blk, boot(a, b, blk, seed)

def stage_deep(out):
    import multiprocessing as mp
    a, b = out['1/3 LIVE'], out['0.5']
    log("\n" + "=" * 118)
    log("BLOCK BOOTSTRAP (2000 draws) -- 0.5 vs 1/3 and 0.5 vs matched control")
    log("=" * 118)
    jobs = []
    for lab, x, y in (('proxy 0.5 vs 1/3', b['ser'], a['ser']),
                      ('proxy 0.5 vs control', b['ser'], out['ctl']['ser']),
                      ('real  0.5 vs 1/3', b['rser'], a['rser']),
                      ('real  0.5 vs control', b['rser'], out['rctl']['ser'])):
        for blk in (20, 60):
            jobs.append((lab, x, y, blk, (hash(lab) + blk) & 0xffff))
    with mp.Pool(min(N_PROCS, len(jobs))) as pool:
        res = pool.map(_bw, jobs)
    for lab, blk, (l1, l2, pl, s1, s2, ps) in res:
        log(f"  {lab:<26} block {blk:>2}d: Sharpe 95% CI [{s1:+.3f}, {s2:+.3f}] P(<=0)={ps:.3f}   "
            f"log-return [{l1*100:+.2f}, {l2*100:+.2f}] pp/yr P(<=0)={pl:.3f}")

    log("\n" + "=" * 118)
    log("LEAVE-ONE-MAJOR-REGIME-OUT (Sharpe difference 0.5 minus 1/3, that window removed)")
    log("=" * 118)
    for rlab, a0, b0 in REGIMES:
        keep = [i for i, d in enumerate(PDATES) if not (a0 <= d <= b0)]
        sa = bstats([b['ser'][i] for i in keep])[1]; sl = bstats([a['ser'][i] for i in keep])[1]
        sc = bstats([out['ctl']['ser'][i] for i in keep])[1]
        rk = [i for i, d in enumerate(RD1) if not (a0 <= d <= b0)]
        rtxt = ''
        if 252 < len(rk) < len(RD1):
            ra = bstats([b['rser'][i] for i in rk])[1]; rl = bstats([a['rser'][i] for i in rk])[1]
            rtxt = f"   | real {ra-rl:+.3f}"
        log(f"  drop {rlab:<26} proxy vs live {sa-sl:+.3f}, vs control {sa-sc:+.3f}{rtxt}")

    log("\n" + "=" * 118)
    log("ONE-SESSION EXECUTION LAG (vote count read from the previous close, BOTH arms) -- the key discriminator")
    log("=" * 118)
    lagQ = {}
    for i in A_IDX:
        d = rows[i]['d']; dp = rows[i - 1]['d'] if i > 0 else None
        lagQ[d] = VOTES_Q.get(dp, 0) if dp is not None else 0
    lagR = {}
    rd = RDAYS[:-1]
    for j, d in enumerate(rd):
        if d in VOTES_R:
            dp = rd[j - 1] if j > 0 else None
            lagR[d] = VOTES_R.get(dp, 0) if dp is not None else 0
    la, _ = proxy_eval_sched(S_LIVE, votes=lagQ); lb, _ = proxy_eval_sched(S_CAND, votes=lagQ)
    rla, _ = real_eval_sched(S_LIVE, votes=lagR); rlb, _ = real_eval_sched(S_CAND, votes=lagR)
    log(f"  lagged 1/3 : proxy {fmt_ev(la)} S {la['s_sharpe']:.3f} H {la['h_sharpe']:.3f} | real {fmt_ev(rla)}")
    log(f"  lagged 0.5 : proxy {fmt_ev(lb)} S {lb['s_sharpe']:.3f} H {lb['h_sharpe']:.3f} | real {fmt_ev(rlb)}")
    log(f"  LAGGED DELTA (0.5 minus 1/3): proxy F {lb['sharpe']-la['sharpe']:+.3f} S {lb['s_sharpe']-la['s_sharpe']:+.3f} "
        f"H {lb['h_sharpe']-la['h_sharpe']:+.3f} | real {rlb['sharpe']-rla['sharpe']:+.3f}")
    log(f"  (unlagged delta was proxy F {b['ev']['sharpe']-a['ev']['sharpe']:+.3f} S {b['ev']['s_sharpe']-a['ev']['s_sharpe']:+.3f} "
        f"H {b['ev']['h_sharpe']-a['ev']['h_sharpe']:+.3f} | real {b['real']['sharpe']-a['real']['sharpe']:+.3f})")

    log("\n" + "=" * 118)
    log("20 bp ONE-WAY COST (both arms)")
    log("=" * 118)
    for lab, sched in (('1/3 LIVE', S_LIVE), ('0.5', S_CAND)):
        rev20, _ = real_eval_sched(sched, one_way=0.0020)
        log(f"  real @20bp {lab:<10} {fmt_ev(rev20)}")
    r20a, _ = real_eval_sched(S_LIVE, one_way=0.0020); r20b, _ = real_eval_sched(S_CAND, one_way=0.0020)
    log(f"  real @20bp DELTA (0.5 minus 1/3): {r20b['sharpe']-r20a['sharpe']:+.3f} Sharpe, "
        f"{(r20b['cagr']-r20a['cagr'])*100:+.2f}pp CAGR")

    log("\n" + "=" * 118)
    log("RECOVERY WINDOWS: return over the 60 / 120 sessions after each major trough")
    log("=" * 118)
    troughs_p = [('dot-com 2002-10-09', '2002-10-09'), ('GFC 2009-03-09', '2009-03-09'),
                 ('COVID 2020-03-23', '2020-03-23'), ('2022 2022-12-28', '2022-12-28')]
    idx = {d: i for i, d in enumerate(PDATES)}
    for lab, d0 in troughs_p:
        if d0 not in idx: continue
        i0 = idx[d0]
        for n in (60, 120):
            ra_ = sum(math.log1p(x) for x in a['ser'][i0:i0 + n]); rb_ = sum(math.log1p(x) for x in b['ser'][i0:i0 + n])
            log(f"  proxy {lab:<22} +{n:>3}d: 1/3 {math.expm1(ra_)*100:+7.1f}%   0.5 {math.expm1(rb_)*100:+7.1f}%   "
                f"diff {(math.expm1(rb_)-math.expm1(ra_))*100:+6.1f}pp")
    ridx = {d: i for i, d in enumerate(RD1)}
    for lab, d0 in (('COVID 2020-03-23', '2020-03-23'), ('2022 2022-12-28', '2022-12-28'), ('2025 2025-04-08', '2025-04-08')):
        if d0 not in ridx: continue
        i0 = ridx[d0]
        for n in (60, 120):
            ra_ = sum(math.log1p(x) for x in a['rser'][i0:i0 + n]); rb_ = sum(math.log1p(x) for x in b['rser'][i0:i0 + n])
            log(f"  real  {lab:<22} +{n:>3}d: 1/3 {math.expm1(ra_)*100:+7.1f}%   0.5 {math.expm1(rb_)*100:+7.1f}%   "
                f"diff {(math.expm1(rb_)-math.expm1(ra_))*100:+6.1f}pp")

# ---------------------------------------------------------------- 4. permutation
# precomputed A-day target rows per step (independent of the vote LABELS, so safe to reuse across shuffles)
_AT = {}
def _at(step):
    if step not in _AT:
        sch = scalar_sched(step)
        _AT[step] = {rows[i]['d']: [vt(TDT.srow(sch, v), rows[i]['vol']) for v in range(4)] for i in A_IDX}
    return _AT[step]
def _eval_votes(step, votes):
    AT = _at(step)
    def fn(r):
        d = r['d']
        if d in votes: return AT[d][votes[d]]
        return OTHER_Q[d]
    return evaluate_full(fn)[0]
_DS = [rows[i]['d'] for i in A_IDX]

def _pw(args):
    seed, steps = args
    rnd = random.Random(seed)
    vals = [VOTES_Q[d] for d in _DS]
    rnd.shuffle(vals)
    sv = dict(zip(_DS, vals))
    base = _eval_votes(LIVE_STEP, sv)
    out = {}
    for lab, st in steps:
        ev = _eval_votes(st, sv)
        out[lab] = (ev['sharpe'] - base['sharpe'],
                    min(ev['s_sharpe'] - base['s_sharpe'], ev['h_sharpe'] - base['h_sharpe']))
    return out

def stage_perm(out):
    import multiprocessing as mp
    a, b = out['1/3 LIVE'], out['0.5']
    real_F = b['ev']['sharpe'] - a['ev']['sharpe']
    real_B = min(b['ev']['s_sharpe'] - a['ev']['s_sharpe'], b['ev']['h_sharpe'] - a['ev']['h_sharpe'])
    menu = [(k, v) for k, v in STEPS.items() if k != '1/3 LIVE']
    log("\n" + "=" * 118)
    log(f"PERMUTATION RERUN, {N_PERM} draws (the 2026-09-20 study above ran only 8; this supersedes section 4b) ( vote labels shuffled among effective-A days, counts kept; proxy)")
    log("=" * 118)
    t = time.time()
    with mp.Pool(N_PROCS) as pool:
        res = pool.map(_pw, [(SEED + i, menu) for i in range(N_PERM)])
    log(f"  {N_PERM} draws in {time.time()-t:.0f}s")
    def pct(v, q):
        s = sorted(v); return s[min(len(s) - 1, int(q * len(s)))]
    single_F = [r['0.5'][0] for r in res]; single_B = [r['0.5'][1] for r in res]
    menu_F = [max(r[k][0] for k, _ in menu) for r in res]; menu_B = [max(r[k][1] for k, _ in menu) for r in res]
    for nm, null, real in (('(a) SINGLE pre-specified candidate, full-period', single_F, real_F),
                           ('(a) SINGLE pre-specified candidate, both-era min', single_B, real_B),
                           ('(b) MENU of 4 scalar steps, full-period', menu_F, real_F),
                           ('(b) MENU of 4 scalar steps, both-era min', menu_B, real_B)):
        p = sum(1 for x in null if x >= real) / len(null)
        log(f"  {nm:<52} null median {pct(null,0.5):+.3f}  95th {pct(null,0.95):+.3f}  max {max(null):+.3f} | "
            f"real {real:+.3f} -> p = {p:.3f}")

# ---------------------------------------------------------------- 5. sensitivity
def stage_sens(out):
    log("\n" + "=" * 118)
    log("SENSITIVITY: does 0.5 still beat 1/3 when the thresholds or the A row move?")
    log("=" * 118)
    base_rules = tuple(EXTENSION_RULES)
    log("  (i) all three trim thresholds shifted together (proxy F/S/H, real) -- delta = 0.5 minus 1/3")
    for sh in (-0.02, -0.01, 0.0, 0.01, 0.02):
        state.EXTENSION_RULES = tuple((n, t + sh) for n, t in base_rules)
        vq = {rows[i]['d']: extension_votes(rows[i]['eff'], rows[i]['gaps']) for i in A_IDX}
        ea, _ = proxy_eval_sched(S_LIVE, votes=vq); eb, _ = proxy_eval_sched(S_CAND, votes=vq)
        log(f"    shift {sh*100:+.0f}pp: proxy F {eb['sharpe']-ea['sharpe']:+.3f}  S {eb['s_sharpe']-ea['s_sharpe']:+.3f}  "
            f"H {eb['h_sharpe']-ea['h_sharpe']:+.3f}   (vote days 1/2/3 = "
            f"{sum(1 for v in vq.values() if v==1)}/{sum(1 for v in vq.values() if v==2)}/{sum(1 for v in vq.values() if v==3)})")
    state.EXTENSION_RULES = base_rules
    log("  (ii) A row moved (proxy F/S/H, real) -- delta = 0.5 minus 1/3 at each A row")
    for arow in ((0.4, 0.6), (0.5, 0.5), (0.6, 0.4)):
        sa = scalar_sched(LIVE_STEP, arow); sb = scalar_sched(CAND_STEP, arow)
        ea, _ = proxy_eval_sched(sa); eb, _ = proxy_eval_sched(sb)
        ra, _ = real_eval_sched(sa); rb, _ = real_eval_sched(sb)
        log(f"    A {arow[0]*100:.0f}/{arow[1]*100:.0f}: proxy F {eb['sharpe']-ea['sharpe']:+.3f}  "
            f"S {eb['s_sharpe']-ea['s_sharpe']:+.3f}  H {eb['h_sharpe']-ea['h_sharpe']:+.3f} | "
            f"real {rb['sharpe']-ra['sharpe']:+.3f}  (0.5 arm: proxy {fmt_ev(eb)} | real {fmt_ev(rb)})")

# ---------------------------------------------------------------- main
if __name__ == '__main__':
    out = stage_main()
    if STAGE in ('all', 'deep'): stage_deep(out)
    if STAGE in ('all', 'perm'): stage_perm(out)
    if STAGE in ('all', 'sens'): stage_sens(out)
    log(f"\n[done] elapsed {time.time()-T0:.0f}s")
