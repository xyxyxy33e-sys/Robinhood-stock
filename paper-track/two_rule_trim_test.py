"""EXTENSION_STEP 0.5 with only TWO trim rules (100d > 10%, 200d > 15%).

Owner question (2026-09-20), straight after the 1/3-vs-0.5 study: "for 0.5 how
about just 10% and 15%". The point is structural, not cosmetic. With three
rules the vote count reaches 3, and 1 - 0.5*3 = -0.5 -- negative risky weights,
validate_weights raises, the live trigger ABORTS. With two rules the vote count
tops out at 2 and 1 - 0.5*2 = 0.0 EXACTLY, the same arithmetic that makes the
live step 1/3 safe with three rules. So the owner's variant is the one version
of step 0.5 that needs NO code change at all.

Pre-specified candidate: RULES2 = ((100, 0.10), (200, 0.15)), STEP 0.5.
  A row (SPMO, TQQQ, cash) at 0/1/2 votes: (50,50,0) / (25,25,50) / (0,0,100)

Scored against: LIVE (3 rules, step 1/3) and C3 (3 rules, step 0.5, yesterday's
candidate, which needs the clip). Decomposition arm T2 (2 rules, step 1/3)
separates "which rules" from "which step". Everything else -- the other two
two-rule pairs, the other scalar steps -- is menu, and is counted as menu in
the permutation null.

Baseline is the CURRENT live design, harness borrowed from trim_destination_test
(imported with TDT_STAGE=none), asserted proxy 25.46% / 1.071 / -27.0%
(S 1.399, H 0.825) and real daily 37.30% / 1.475 / -18.6%.

Usage:  python3 paper-track/two_rule_trim_test.py
        TRT_NPERM=1000 TRT_PROCS=4 TRT_STAGE=all|main|boot|perm|sens
"""
import os, sys, io, math, time, random, contextlib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)
sys.path.insert(0, 'paper-track')
os.environ.setdefault('TDT_STAGE', 'none')
STAGE = os.environ.get('TRT_STAGE', 'all')
N_PERM = int(os.environ.get('TRT_NPERM', '1000'))
N_PROCS = int(os.environ.get('TRT_PROCS', '4'))
SEED = 20260920
T0 = time.time()

LOG = 'paper-track/research_notes/two_rule_trim_test_run.log'
_lf = open(LOG, 'a')
def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s); _lf.write(s + '\n'); _lf.flush()

_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    import trim_destination_test as TDT
import state
from state import extension_scale, EXTENSION_RULES, EXTENSION_STEP, TARGET_WEIGHTS
from d_substate_fresh import (rows, run, vt, evaluate_full, real_metrics, RDAYS, SEARCH, HOLDOUT,
                              REGIMES, boot, bstats)
from improvement_search_r2 import scaled

PDATES = TDT.PDATES; RD1 = TDT.RD1
LIVE_SER = TDT.LIVE_SER; RLIVE_SER = TDT.RLIVE_SER
LIVE_EV = TDT.LIVE_EV; RLIVE_EV = TDT.RLIVE_EV
A_IDX = TDT.A_IDX; OTHER_Q = TDT.OTHER_Q; RINFO = TDT.RINFO; RA_DAYS = TDT.RA_DAYS
fmt_ev = TDT.fmt_ev; byyear = TDT.byyear

# ---------------------------------------------------------------- rule sets and votes
RULES3 = ((100, 0.10), (150, 0.12), (200, 0.15))
assert tuple(EXTENSION_RULES) == RULES3
RULES2 = ((100, 0.10), (200, 0.15))                    # the owner's candidate
RULESETS = {'3 rules LIVE': RULES3, '2 rules 10/15': RULES2,
            '2 rules 10/12': ((100, 0.10), (150, 0.12)),
            '2 rules 12/15': ((150, 0.12), (200, 0.15))}

def votes_of(gaps, rules):
    if gaps is None: return 0
    return sum(1 for n, t in rules if gaps.get(n) is not None and gaps[n] > t)

VQ = {lab: {rows[i]['d']: votes_of(rows[i]['gaps'], rl) for i in A_IDX} for lab, rl in RULESETS.items()}
VR = {lab: {d: votes_of(RINFO[d]['gaps'], rl) for d in RA_DAYS} for lab, rl in RULESETS.items()}
assert VQ['3 rules LIVE'] == TDT.VOTES_Q and VR['3 rules LIVE'] == TDT.VOTES_R, 'rule-set 3 must reproduce the harness votes'

def scalar_sched(step, a_row=(0.5, 0.5)):
    """A-row (SPMO, TQQQ, cash) at 0..3 votes for a scalar EXTENSION_STEP, clipped at 0."""
    s, t = a_row
    return [(s * max(0.0, 1 - step * v), t * max(0.0, 1 - step * v),
             1 - (s + t) * max(0.0, 1 - step * v)) for v in range(4)]

STEPS = {'0.25': 0.25, '1/3': 1.0 / 3.0, '0.5': 0.5, '1.0': 1.0}
LIVE_STEP, CAND_STEP = 1.0 / 3.0, 0.5

# ARMS: (label, ruleset label, step, max votes that actually occur)
ARMS = [('LIVE   3 rules, 1/3', '3 rules LIVE', LIVE_STEP),
        ('C3     3 rules, 0.5', '3 rules LIVE', CAND_STEP),
        ('C2     2 rules, 0.5', '2 rules 10/15', CAND_STEP),
        ('T2     2 rules, 1/3', '2 rules 10/15', LIVE_STEP)]

_AT = {}
def at(step):
    if step not in _AT:
        sch = scalar_sched(step)
        _AT[step] = {rows[i]['d']: [vt(TDT.srow(sch, v), rows[i]['vol']) for v in range(4)] for i in A_IDX}
    return _AT[step]

def pfn(step, votes):
    AT = at(step)
    def fn(r):
        d = r['d']
        return AT[d][votes[d]] if d in votes else OTHER_Q[d]
    return fn
def peval(step, votes):
    return evaluate_full(pfn(step, votes))
def reval(step, votes, **kw):
    return TDT.real_eval(scalar_sched(step), votes=votes, **kw)

def fmt_sched(step, mx):
    s = scalar_sched(step)
    return ' / '.join(f"({a*100:.0f},{b*100:.0f},{c*100:.0f})" for a, b, c in s[:mx + 1])

RES = {}

# ---------------------------------------------------------------- 1. header + the arithmetic fact
def stage_main():
    log("\n" + "=" * 124)
    log("RESEARCH LINE two_rule_trim_test (2026-09-20): EXTENSION_STEP 0.5 with only the 10% and 15% rules")
    log("=" * 124)
    log("  THE ARITHMETIC, which is the whole point of the owner's question:")
    for lab, rl in (('3 rules, step 0.5', RULES3), ('2 rules, step 0.5', RULES2), ('3 rules, step 1/3 (live)', RULES3)):
        st = 0.5 if 'ep 0.5' in lab else LIVE_STEP
        mx = len(rl)
        raw = 1.0 - st * mx
        log(f"    {lab:<26} max votes {mx}, scale at max votes = 1 - {st:.4f}*{mx} = {raw:+.4f}"
            f"   {'NEGATIVE -> validate_weights raises, trigger ABORTS' if raw < -1e-12 else 'exactly zero -> all-cash row, NO clip needed'}")
    state.EXTENSION_STEP = 0.5
    hot = {100: 0.20, 150: 0.20, 200: 0.20}
    log(f"    verified against the live code: state.extension_scale('A', all-three-hot) at STEP 0.5 = {extension_scale('A', hot):+.4f}")
    state.EXTENSION_RULES = RULES2
    log(f"    with EXTENSION_RULES = {RULES2} the same call gives {extension_scale('A', hot):+.4f}  -> no code change required")
    state.EXTENSION_RULES = RULES3; state.EXTENSION_STEP = LIVE_STEP

    log("\n  ARMS (A row SPMO/TQQQ/cash by vote count; the vol target multiplies on top, as live):")
    for lab, rs, st in ARMS:
        mx = len(RULESETS[rs])
        log(f"    {lab:<22} rules {str(RULESETS[rs]):<34} rows {fmt_sched(st, mx)}")

    log("\n  VOTE-DAY CENSUS on effective-A days (proxy full / search / holdout / real daily):")
    log(f"  {'ruleset':<16}{'harness':<14}{'A days':>8}{'0':>8}{'1':>8}{'2':>8}{'3':>8}   {'>=1':>7}  {'max rung':>9}")
    for rs in RULESETS:
        for hl, vd, ds_ in (('proxy full', VQ[rs], list(VQ[rs])),
                            ('proxy search', VQ[rs], [d for d in VQ[rs] if d >= SEARCH[0]]),
                            ('proxy holdout', VQ[rs], [d for d in VQ[rs] if d <= HOLDOUT[1]]),
                            ('real daily', VR[rs], list(VR[rs]))):
            c = [sum(1 for d in ds_ if vd[d] == k) for k in range(4)]
            log(f"  {rs:<16}{hl:<14}{len(ds_):>8}{c[0]:>8}{c[1]:>8}{c[2]:>8}{c[3]:>8}   {sum(c[1:])/len(ds_)*100:6.1f}%{max(k for k in range(4) if c[k]):>9}")

    log("\n" + "=" * 124)
    log("2  HEADLINE. proxy full / search(2015-11+) / holdout(2000-07..2015-10) and real daily. deltas vs LIVE.")
    log("=" * 124)
    log(f"  {'arm':<22}| {'proxy full':>24} {'S':>7}{'H':>7}{'exp':>7}{'reb':>6} | {'real daily':>24} {'exp':>7}{'reb':>6}")
    for lab, rs, st in ARMS:
        ev, ser = peval(st, VQ[rs]); rev, rser = reval(st, VR[rs])
        RES[lab] = dict(ev=ev, ser=ser, rev=rev, rser=rser, rs=rs, st=st)
        log(f"  {lab:<22}| {fmt_ev(ev):>24} {ev['s_sharpe']:7.3f}{ev['h_sharpe']:7.3f}{ev['risky']*100:6.1f}%{ev['reb']:6.1f} | "
            f"{fmt_ev(rev):>24} {rev['exp']*100:6.1f}%{rev['reb']:6.1f}")
    L = RES['LIVE   3 rules, 1/3']
    log("")
    log(f"  {'delta vs LIVE':<22}| {'CAGR pp':>9}{'Sharpe':>9}{'S':>8}{'H':>8}{'MaxDD pp':>10}{'exp pp':>8} | {'real CAGR':>10}{'Sharpe':>9}{'MaxDD':>8}{'exp pp':>8}{'reb':>7}")
    for lab, rs, st in ARMS[1:]:
        r = RES[lab]
        log(f"  {lab:<22}| {(r['ev']['cagr']-L['ev']['cagr'])*100:+9.2f}{r['ev']['sharpe']-L['ev']['sharpe']:+9.3f}"
            f"{r['ev']['s_sharpe']-L['ev']['s_sharpe']:+8.3f}{r['ev']['h_sharpe']-L['ev']['h_sharpe']:+8.3f}"
            f"{(r['ev']['mdd']-L['ev']['mdd'])*100:+10.1f}{(r['ev']['risky']-L['ev']['risky'])*100:+8.1f} | "
            f"{(r['rev']['cagr']-L['rev']['cagr'])*100:+10.2f}{r['rev']['sharpe']-L['rev']['sharpe']:+9.3f}"
            f"{(r['rev']['mdd']-L['rev']['mdd'])*100:+8.1f}{(r['rev']['exp']-L['rev']['exp'])*100:+8.1f}{r['rev']['reb']-L['rev']['reb']:+7.1f}")
    c2 = RES['C2     2 rules, 0.5']; c3 = RES['C3     3 rules, 0.5']
    log(f"\n  C2 minus C3 (does dropping the 150d rule cost or help at step 0.5?): proxy Sharpe {c2['ev']['sharpe']-c3['ev']['sharpe']:+.3f} "
        f"(S {c2['ev']['s_sharpe']-c3['ev']['s_sharpe']:+.3f}, H {c2['ev']['h_sharpe']-c3['ev']['h_sharpe']:+.3f}), "
        f"CAGR {(c2['ev']['cagr']-c3['ev']['cagr'])*100:+.2f} pp, real Sharpe {c2['rev']['sharpe']-c3['rev']['sharpe']:+.3f}, "
        f"real CAGR {(c2['rev']['cagr']-c3['rev']['cagr'])*100:+.2f} pp")
    log(f"  both-era improvement over LIVE: C2 dS {c2['ev']['s_sharpe']-L['ev']['s_sharpe']:+.3f} dH {c2['ev']['h_sharpe']-L['ev']['h_sharpe']:+.3f} -> "
        f"{'PASS' if c2['ev']['s_sharpe']>L['ev']['s_sharpe'] and c2['ev']['h_sharpe']>L['ev']['h_sharpe'] else 'FAIL'}")

    # ------------------------------------------------ exposure-matched controls
    log("\n" + "=" * 124)
    log("3  EXPOSURE-MATCHED CONTROL: LIVE flat de-levered (all four risky legs x k every day) to each arm's exposure")
    log("=" * 124)
    for lab in ('C3     3 rules, 0.5', 'C2     2 rules, 0.5', 'T2     2 rules, 1/3'):
        r = RES[lab]
        k, cev, cser = TDT.proxy_control(r['ev']['risky'])
        rk, rcev, rcser = TDT.real_control(r['rev']['exp'])
        r['ctrl_ser'] = cser; r['rctrl_ser'] = rcser
        log(f"  {lab:<22} proxy k {k:.4f} control {fmt_ev(cev)} S {cev['s_sharpe']:.3f} H {cev['h_sharpe']:.3f} | "
            f"arm - control: F {r['ev']['sharpe']-cev['sharpe']:+.3f} S {r['ev']['s_sharpe']-cev['s_sharpe']:+.3f} "
            f"H {r['ev']['h_sharpe']-cev['h_sharpe']:+.3f} CAGR {(r['ev']['cagr']-cev['cagr'])*100:+.2f} pp")
        log(f"  {'':<22} real  k {rk:.4f} control {fmt_ev(rcev)} | arm - control: {r['rev']['sharpe']-rcev['sharpe']:+.3f} "
            f"CAGR {(r['rev']['cagr']-rcev['cagr'])*100:+.2f} pp, MaxDD {(r['rev']['mdd']-rcev['mdd'])*100:+.1f} pp")

    # ------------------------------------------------ per year
    log("\n" + "=" * 124)
    log("4  PER YEAR. Return %, and deltas vs LIVE in pp.")
    log("=" * 124)
    for hl, key, serkey, dates in (('PROXY (QQQ core, 2000-07..2026-08)', 'ev', 'ser', PDATES),
                                   ('REAL DAILY (SPMO era, 2015-11+)', 'rev', 'rser', RD1)):
        log(f"\n  {hl}")
        bys = {lab: byyear(RES[lab][serkey], dates) for lab, _, _ in ARMS}
        log(f"  {'year':<6}{'LIVE':>9}{'C3':>9}{'C2':>9}{'T2':>9} |{'C3-L':>8}{'C2-L':>8}{'T2-L':>8}{'C2-C3':>8}")
        yrs = sorted(bys['LIVE   3 rules, 1/3'])
        for y in yrs:
            v = [bys[lab][y] * 100 for lab, _, _ in ARMS]
            log(f"  {y:<6}{v[0]:>9.1f}{v[1]:>9.1f}{v[2]:>9.1f}{v[3]:>9.1f} |{v[1]-v[0]:>+8.1f}{v[2]-v[0]:>+8.1f}{v[3]-v[0]:>+8.1f}{v[2]-v[1]:>+8.1f}")
        for j, lab in ((2, 'C2'), (1, 'C3')):
            d = [bys[ARMS[j][0]][y] * 100 - bys[ARMS[0][0]][y] * 100 for y in yrs]
            w = sum(1 for x in d if x > 0.05); ident = sum(1 for x in d if abs(x) <= 0.05)
            log(f"  {lab}: beats LIVE in {w}/{len(yrs)} years (identical in {ident}); worst {min(d):+.1f} pp ({yrs[d.index(min(d))]}), "
                f"best {max(d):+.1f} pp ({yrs[d.index(max(d))]}); sum {sum(d):+.1f} pp")

    # ------------------------------------------------ behaviour
    log("\n" + "=" * 124)
    log("5  BEHAVIOUR: how much of the time is the TARGET row fully in cash, and the longest continuous stretch")
    log("=" * 124)
    for hl, dsall, vkey, dates in (('proxy full', PDATES, VQ, PDATES), ('real daily', [d for d in RDAYS[:-1]], VR, None)):
        log(f"  {hl}:")
        for lab, rs, st in ARMS:
            sch = scalar_sched(st); vd = vkey[rs]
            if hl == 'proxy full':
                cashd = [r['d'] for r in rows
                         if (r['d'] in vd and sch[vd[r['d']]][2] > 1 - 1e-9) or
                            (r['d'] not in vd and (r['d'] in TDT.GATE_Q or r['d'] in TDT.E_Q or r['state'] == 'F'))]
                tot = len(rows); order = PDATES
            else:
                cashd = [d for d in RDAYS[:-1]
                         if (d in vd and sch[vd[d]][2] > 1 - 1e-9) or
                            (d not in vd and (RINFO[d]['gate'] or RINFO[d]['st'] in ('E', 'F')))]
                tot = len(RDAYS) - 1; order = RDAYS[:-1]
            cs = set(cashd); best = cur = 0; bend = None
            for d in order:
                if d in cs:
                    cur += 1
                    if cur > best: best, bend = cur, d
                else: cur = 0
            log(f"    {lab:<22} fully-cash target on {len(cashd):>5} / {tot} sessions = {len(cashd)/tot*100:5.1f}%   "
                f"longest stretch {best:>3} sessions, ending {bend}")
    log(f"  average deployed capital: " + "; ".join(
        f"{lab.split()[0]} {RES[lab]['ev']['risky']*100:.1f}% proxy / {RES[lab]['rev']['exp']*100:.1f}% real" for lab, _, _ in ARMS))
    log(f"  rebalances/yr: " + "; ".join(
        f"{lab.split()[0]} {RES[lab]['ev']['reb']:.1f} proxy / {RES[lab]['rev']['reb']:.1f} real" for lab, _, _ in ARMS))

# ---------------------------------------------------------------- bootstrap, LORO, lag, cost
def stage_boot():
    L = RES['LIVE   3 rules, 1/3']
    log("\n" + "=" * 124)
    log("6a  CIRCULAR BLOCK BOOTSTRAP (2000 draws, 20d and 60d blocks; paired -- same blocks for both series)")
    log("=" * 124)
    log(f"  {'comparison':<34}{'blk':>4} | {'Sharpe 95% CI':>26}{'P(<=0)':>9} | {'log-return CI (pp/yr)':>28}{'P(<=0)':>9}")
    for lab in ('C2     2 rules, 0.5', 'C3     3 rules, 0.5'):
        r = RES[lab]; tag = lab.split()[0]
        for cl, a, b in ((f'{tag} vs LIVE, proxy', r['ser'], L['ser']),
                         (f'{tag} vs control, proxy', r['ser'], r['ctrl_ser']),
                         (f'{tag} vs LIVE, real', r['rser'], L['rser']),
                         (f'{tag} vs control, real', r['rser'], r['rctrl_ser'])):
            for blk in (20, 60):
                l1, l2, pl, s1, s2, ps = boot(a, b, blk, seed=(hash(cl) + blk) & 0xffff)
                log(f"  {cl:<34}{blk:>3}d | [{s1:+9.3f},{s2:+9.3f}]  {ps:8.3f} | [{l1*100:+10.2f},{l2*100:+10.2f}]  {pl:8.3f}")
    log("  (P(<=0) is the share of resamples in which the arm does NOT beat the comparison. The project bar is P < 0.05.)")

    log("\n" + "=" * 124)
    log("6b  LEAVE-ONE-MAJOR-REGIME-OUT (proxy full-period Sharpe with that window removed)")
    log("=" * 124)
    log(f"  {'drop':<28}{'LIVE':>9}{'C3':>9}{'C2':>9} | {'C3-L':>8}{'C2-L':>8}{'C2-ctl':>9}")
    for rlab, a0, b0 in REGIMES:
        keep = [i for i, r in enumerate(rows) if not (a0 <= r['d'] <= b0)]
        sh = {}
        for lab in ('LIVE   3 rules, 1/3', 'C3     3 rules, 0.5', 'C2     2 rules, 0.5'):
            sh[lab] = bstats([RES[lab]['ser'][i] for i in keep])[1]
        sc = bstats([RES['C2     2 rules, 0.5']['ctrl_ser'][i] for i in keep])[1]
        log(f"  {rlab:<28}{sh['LIVE   3 rules, 1/3']:>9.3f}{sh['C3     3 rules, 0.5']:>9.3f}{sh['C2     2 rules, 0.5']:>9.3f} | "
            f"{sh['C3     3 rules, 0.5']-sh['LIVE   3 rules, 1/3']:>+8.3f}{sh['C2     2 rules, 0.5']-sh['LIVE   3 rules, 1/3']:>+8.3f}"
            f"{sh['C2     2 rules, 0.5']-sc:>+9.3f}")

    log("\n" + "=" * 124)
    log("6c  ONE-SESSION EXECUTION LAG (vote count read from the PREVIOUS close, all arms) -- the test that killed DEEP")
    log("=" * 124)
    prevQ = {d: (PDATES[i - 1] if i else None) for i, d in enumerate(PDATES)}
    prevR = {d: (RDAYS[i - 1] if i else None) for i, d in enumerate(RDAYS)}
    lagQ = {rs: {d: (VQ[rs].get(prevQ[d], 0) if prevQ[d] else 0) for d in VQ[rs]} for rs in RULESETS}
    lagR = {rs: {d: (VR[rs].get(prevR[d], 0) if prevR[d] else 0) for d in VR[rs]} for rs in RULESETS}
    lv = {}
    for lab, rs, st in ARMS:
        ev, _ = peval(st, lagQ[rs]); rev, _ = reval(st, lagR[rs])
        lv[lab] = (ev, rev)
        log(f"  lagged {lab:<22} proxy {fmt_ev(ev)} S {ev['s_sharpe']:.3f} H {ev['h_sharpe']:.3f} | real {fmt_ev(rev)}")
    b = lv['LIVE   3 rules, 1/3']
    for lab in ('C3     3 rules, 0.5', 'C2     2 rules, 0.5', 'T2     2 rules, 1/3'):
        a = lv[lab]
        log(f"  {lab.split()[0]} - LIVE, both lagged: full {a[0]['sharpe']-b[0]['sharpe']:+.3f}  search {a[0]['s_sharpe']-b[0]['s_sharpe']:+.3f}  "
            f"holdout {a[0]['h_sharpe']-b[0]['h_sharpe']:+.3f}  real {a[1]['sharpe']-b[1]['sharpe']:+.3f}   "
            f"(unlagged: full {RES[lab]['ev']['sharpe']-RES['LIVE   3 rules, 1/3']['ev']['sharpe']:+.3f} "
            f"search {RES[lab]['ev']['s_sharpe']-RES['LIVE   3 rules, 1/3']['ev']['s_sharpe']:+.3f} "
            f"real {RES[lab]['rev']['sharpe']-RES['LIVE   3 rules, 1/3']['rev']['sharpe']:+.3f})")
    log("  BENCHMARK: the DEEP schedule failed this at search -0.031 / real -0.040; 3-rule step 0.5 survived at +0.003 / +0.000.")

    log("\n" + "=" * 124)
    log("6d  20 bp ONE-WAY COST (live cost is 4 bp)")
    log("=" * 124)
    import monthly_returns as MR
    ow0 = MR.ONE_WAY
    ev20 = {}
    for lab, rs, st in ARMS:
        rev, _ = reval(st, VR[rs], one_way=0.0020)
        ev20[lab] = rev
        log(f"  20bp {lab:<22} real {fmt_ev(rev)}")
    b = ev20['LIVE   3 rules, 1/3']
    for lab in ('C3     3 rules, 0.5', 'C2     2 rules, 0.5', 'T2     2 rules, 1/3'):
        log(f"    {lab.split()[0]} - LIVE at 20bp: real Sharpe {ev20[lab]['sharpe']-b['sharpe']:+.3f}, CAGR {(ev20[lab]['cagr']-b['cagr'])*100:+.2f} pp")

# ---------------------------------------------------------------- permutation
_DS = [rows[i]['d'] for i in A_IDX]
MENU = [(f"{rs} x {sl}", rs, sv) for rs in RULESETS for sl, sv in STEPS.items()]

def _pw(seed):
    rnd = random.Random(seed)
    sv = {}
    for rs in RULESETS:                       # each rule set's labels shuffled independently
        vals = [VQ[rs][d] for d in _DS]
        rnd.shuffle(vals)
        sv[rs] = dict(zip(_DS, vals))
    base = evaluate_full(pfn(LIVE_STEP, sv['3 rules LIVE']))[0]
    out = {}
    for lab, rs, st in MENU:
        ev = evaluate_full(pfn(st, sv[rs]))[0]
        out[lab] = (ev['sharpe'] - base['sharpe'],
                    min(ev['s_sharpe'] - base['s_sharpe'], ev['h_sharpe'] - base['h_sharpe']))
    return out

def stage_perm():
    import multiprocessing as mp
    L = RES['LIVE   3 rules, 1/3']
    log("\n" + "=" * 124)
    log(f"7  PERMUTATION, {N_PERM} draws: vote labels shuffled among effective-A days (counts kept per rule set), proxy.")
    log("=" * 124)
    log("  Null: 'the vote label carries no information about whether this trim shape helps'.")
    log("    (a) SINGLE pre-specified candidate = C2 (2 rules 10/15, step 0.5), the shape the owner named.")
    log(f"    (b) HONEST MENU = max over all {len(MENU)} cells (4 rule sets x 4 scalar steps) -- what you are entitled to,")
    log("        because the step has already been moved once and the rule set is now being moved too.")
    real = {}
    for lab, rs, st in MENU:
        ev, _ = peval(st, VQ[rs])
        real[lab] = (ev['sharpe'] - L['ev']['sharpe'],
                     min(ev['s_sharpe'] - L['ev']['s_sharpe'], ev['h_sharpe'] - L['ev']['h_sharpe']))
    log(f"\n  the {len(MENU)} menu cells on the REAL labels (full-period dSharpe / both-era-min):")
    log(f"  {'ruleset':<16}" + "".join(f"{sl:>18}" for sl in STEPS))
    for rs in RULESETS:
        log(f"  {rs:<16}" + "".join(f"{real[f'{rs} x {sl}'][0]:>+9.3f}{real[f'{rs} x {sl}'][1]:>+9.3f}" for sl in STEPS))
    best = max(real, key=lambda k: real[k][0])
    log(f"  best cell full-period: {best} at {real[best][0]:+.3f}; best both-era-min: "
        f"{max(real, key=lambda k: real[k][1])} at {max(real[k][1] for k in real):+.3f}")
    t = time.time()
    with mp.Pool(N_PROCS) as pool:
        res = pool.map(_pw, [SEED + i for i in range(N_PERM)])
    log(f"\n  {N_PERM} draws in {time.time()-t:.0f}s")
    def pct(v, q):
        s = sorted(v); return s[min(len(s) - 1, int(q * len(s)))]
    C2 = '2 rules 10/15 x 0.5'
    tests = [('(a) SINGLE pre-specified C2, full-period', [r[C2][0] for r in res], real[C2][0]),
             ('(a) SINGLE pre-specified C2, both-era min', [r[C2][1] for r in res], real[C2][1]),
             (f'(b) MENU of {len(MENU)} cells, full-period', [max(r[k][0] for k in r) for r in res], real[C2][0]),
             (f'(b) MENU of {len(MENU)} cells, both-era min', [max(r[k][1] for k in r) for r in res], real[C2][1])]
    log("")
    for nm, null, rl in tests:
        p = sum(1 for x in null if x >= rl) / len(null)
        log(f"  {nm:<46} null median {pct(null,0.5):+.3f}  95th {pct(null,0.95):+.3f}  max {max(null):+.3f} | "
            f"real {rl:+.3f} -> p = {p:.3f}")


# ---------------------------------------------------------------- paired permutation (common day map)
def _pw2(seed):
    """PAIRED null: ONE random bijection on A-days, applied to EVERY rule set's label vector.
    This keeps the joint structure across rule sets (a day that is 3-vote under RULES3 keeps whatever
    the 2-rule sets said about the SAME donor day), so the arm and the base see the same draw --
    the way the 2026-09-20 step study's permutation was paired within one rule set."""
    rnd = random.Random(seed)
    donors = list(_DS); rnd.shuffle(donors)
    m = dict(zip(_DS, donors))
    sv = {rs: {d: VQ[rs][m[d]] for d in _DS} for rs in RULESETS}
    base = evaluate_full(pfn(LIVE_STEP, sv['3 rules LIVE']))[0]
    out = {}
    for lab, rs, st in MENU:
        ev = evaluate_full(pfn(st, sv[rs]))[0]
        out[lab] = (ev['sharpe'] - base['sharpe'],
                    min(ev['s_sharpe'] - base['s_sharpe'], ev['h_sharpe'] - base['h_sharpe']))
    return out

def stage_perm2():
    import multiprocessing as mp
    L = RES['LIVE   3 rules, 1/3']
    log("\n" + "=" * 124)
    log(f"7b  PERMUTATION, PAIRED VARIANT, {N_PERM} draws: ONE day-map applied to every rule set (see _pw2 docstring).")
    log("=" * 124)
    log("  Stage 7 shuffled each rule set's labels INDEPENDENTLY, which decorrelates the arm from its base and")
    log("  widens the null (95th +0.155 vs the +0.074 the 3-rule-only study saw). This variant restores the pairing.")
    real = {}
    for lab, rs, st in MENU:
        ev, _ = peval(st, VQ[rs])
        real[lab] = (ev['sharpe'] - L['ev']['sharpe'],
                     min(ev['s_sharpe'] - L['ev']['s_sharpe'], ev['h_sharpe'] - L['ev']['h_sharpe']))
    t = time.time()
    with mp.Pool(N_PROCS) as pool:
        res = pool.map(_pw2, [SEED + 5000 + i for i in range(N_PERM)])
    log(f"  {N_PERM} draws in {time.time()-t:.0f}s")
    def pct(v, q):
        s = sorted(v); return s[min(len(s) - 1, int(q * len(s)))]
    C2 = '2 rules 10/15 x 0.5'; C3 = '3 rules LIVE x 0.5'
    tests = [('(a) SINGLE pre-specified C2, full-period', [r[C2][0] for r in res], real[C2][0]),
             ('(a) SINGLE pre-specified C2, both-era min', [r[C2][1] for r in res], real[C2][1]),
             ('    (reference) SINGLE C3, full-period', [r[C3][0] for r in res], real[C3][0]),
             ('    (reference) SINGLE C3, both-era min', [r[C3][1] for r in res], real[C3][1]),
             (f'(b) MENU of {len(MENU)} cells, full-period', [max(r[k][0] for k in r) for r in res], real[C2][0]),
             (f'(b) MENU of {len(MENU)} cells, both-era min', [max(r[k][1] for k in r) for r in res], real[C2][1])]
    log("")
    for nm, null, rl in tests:
        p = sum(1 for x in null if x >= rl) / len(null)
        log(f"  {nm:<46} null median {pct(null,0.5):+.3f}  95th {pct(null,0.95):+.3f}  max {max(null):+.3f} | "
            f"real {rl:+.3f} -> p = {p:.3f}")

# ---------------------------------------------------------------- sensitivity
def stage_sens():
    L = RES['LIVE   3 rules, 1/3']
    log("\n" + "=" * 124)
    log("8a  THRESHOLD SENSITIVITY: the surviving thresholds shifted together by -2..+2 pp")
    log("=" * 124)
    log(f"  {'shift':<8}{'C2 rules':<20}{'A days >=1':>11}{'LIVE Sh':>9}{'C2 Sh':>8}{'dF':>8}{'dS':>8}{'dH':>8}{'real d':>9}  ranking")
    for sh in (-0.02, -0.01, 0.0, 0.01, 0.02):
        r3 = tuple((n, t + sh) for n, t in RULES3); r2 = tuple((n, t + sh) for n, t in RULES2)
        v3 = {rows[i]['d']: votes_of(rows[i]['gaps'], r3) for i in A_IDX}
        v2 = {rows[i]['d']: votes_of(rows[i]['gaps'], r2) for i in A_IDX}
        w3 = {d: votes_of(RINFO[d]['gaps'], r3) for d in RA_DAYS}
        w2 = {d: votes_of(RINFO[d]['gaps'], r2) for d in RA_DAYS}
        ea, _ = peval(LIVE_STEP, v3); eb, _ = peval(CAND_STEP, v2)
        ra, _ = reval(LIVE_STEP, w3); rb, _ = reval(CAND_STEP, w2)
        dF, dS, dH, dR = eb['sharpe']-ea['sharpe'], eb['s_sharpe']-ea['s_sharpe'], eb['h_sharpe']-ea['h_sharpe'], rb['sharpe']-ra['sharpe']
        rank = 'C2 ahead' if min(dS, dH, dR) > 0 else ('LIVE ahead' if max(dF, dR) < 0 else 'mixed')
        log(f"  {sh*100:+.0f} pp  {f'{r2[0][1]*100:.0f}%/{r2[1][1]*100:.0f}%':<20}{sum(1 for v in v2.values() if v>=1):>11}"
            f"{ea['sharpe']:>9.3f}{eb['sharpe']:>8.3f}{dF:>+8.3f}{dS:>+8.3f}{dH:>+8.3f}{dR:>+9.3f}  {rank}")

    log("\n" + "=" * 124)
    log("8b  A-ROW SENSITIVITY: 40/60 and 60/40 (core/TQQQ) instead of 50/50")
    log("=" * 124)
    for arow in ((0.4, 0.6), (0.5, 0.5), (0.6, 0.4)):
        out = {}
        for lab, rs, st in ARMS:
            sch = scalar_sched(st, arow)
            AT = {rows[i]['d']: [vt(TDT.srow(sch, v), rows[i]['vol']) for v in range(4)] for i in A_IDX}
            def fn(r, AT=AT, vd=VQ[rs]):
                d = r['d']
                return AT[d][vd[d]] if d in vd else OTHER_Q[d]
            ev, _ = evaluate_full(fn)
            rev, _ = TDT.real_eval(sch, votes=VR[rs])
            out[lab] = (ev, rev)
        b = out['LIVE   3 rules, 1/3']
        log(f"  A {arow[0]*100:.0f}/{arow[1]*100:.0f}: " + "; ".join(
            f"{lab.split()[0]} dF {out[lab][0]['sharpe']-b[0]['sharpe']:+.3f} dS {out[lab][0]['s_sharpe']-b[0]['s_sharpe']:+.3f} "
            f"dH {out[lab][0]['h_sharpe']-b[0]['h_sharpe']:+.3f} real {out[lab][1]['sharpe']-b[1]['sharpe']:+.3f}"
            for lab in ('C3     3 rules, 0.5', 'C2     2 rules, 0.5')))

if __name__ == '__main__':
    stage_main()
    if STAGE in ('all', 'boot'): stage_boot()
    if STAGE in ('all', 'perm'): stage_perm()
    if STAGE in ('all', 'perm2'): stage_perm2()
    if STAGE in ('all', 'sens'): stage_sens()
    log(f"\n[done] elapsed {time.time()-T0:.0f}s")
