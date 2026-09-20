"""State D row: 60% SPMO / 40% cash instead of 100% QLD.

Owner question (2026-09-20). State D is currently 100% QLD (2x QQQ), gated to
100% BOXX when breadth pct < 0.20 OR gap200 < 0.02. The candidate replaces the
UNGATED D row with 60% core / 40% cash. The gate is unchanged: gated D days
stay 100% cash under both arms, so this measures only what is held on the D
days the design still takes risk on.

PRE-SPECIFIED CANDIDATE: D = (0.60 core, 0, 0, 0, 0.40 cash).
Everything else is context or control and is labelled as such.

Note on the proxy: its core leg is QQQ, not SPMO (SPMO has no pre-2015 history),
so proxy figures are 60/40 QQQ/cash. The real daily harness uses actual SPMO.

Baseline = the current live design, harness borrowed from trim_destination_test
(TDT_STAGE=none), which asserts proxy 25.46% / 1.071 / -27.0% (S 1.399,
H 0.825) and real daily 37.30% / 1.475 / -18.6%.

Usage:  python3 paper-track/d_row_test.py        [DRT_STAGE=all|main|boot]
"""
import os, sys, io, math, time, contextlib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)
sys.path.insert(0, 'paper-track')
os.environ.setdefault('TDT_STAGE', 'none')
STAGE = os.environ.get('DRT_STAGE', 'all')
T0 = time.time()

LOG = 'paper-track/research_notes/d_row_test_run.log'
_lf = open(LOG, 'a')
def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s); _lf.write(s + '\n'); _lf.flush()

_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    import trim_destination_test as TDT
from d_substate_fresh import (rows, run, vt, RF, W, evaluate_full, real_metrics, RDAYS,
                              SEARCH, HOLDOUT, REGIMES, boot, bstats)
from improvement_search_r2 import scaled
import state
from state import needs_rebalance, TARGET_WEIGHTS
import monthly_returns as MR

PDATES = TDT.PDATES; RD1 = TDT.RD1
LIVE_EV, LIVE_SER = TDT.LIVE_EV, TDT.LIVE_SER
RLIVE_EV, RLIVE_SER = TDT.RLIVE_EV, TDT.RLIVE_SER
GATE_Q, E_Q = TDT.GATE_Q, TDT.E_Q
VOTES_Q, VOTES_R, OTHER_Q = TDT.VOTES_Q, TDT.VOTES_R, TDT.OTHER_Q
RINFO, RA_DAYS, RLEG_RET = TDT.RINFO, TDT.RA_DAYS, TDT.RLEG_RET
CASH = TDT.CASH; SCHED = TDT.SCHED; srow = TDT.srow
fmt_ev = TDT.fmt_ev; byyear = TDT.byyear

# ---------------------------------------------------------------- the D rows
LIVE_D = TARGET_WEIGHTS['D']
assert LIVE_D == (0.0, 0.0, 1.0, 0.0, 0.0), f"live D row is not 100% QLD: {LIVE_D}"

CAND = ('60/40 core/cash', (0.60, 0.0, 0.0, 0.0, 0.40))          # <- the owner's candidate
CONTEXT = [
    ('LIVE 100% QLD',      LIVE_D),
    CAND,
    ('100% core',          (1.00, 0.0, 0.0, 0.0, 0.00)),
    ('50/50 core/cash',    (0.50, 0.0, 0.0, 0.0, 0.50)),
    ('70/30 core/cash',    (0.70, 0.0, 0.0, 0.0, 0.30)),
    ('60/40 QLD/cash',     (0.0, 0.0, 0.60, 0.0, 0.40)),
    ('100% cash',          CASH),
]
for _, w in CONTEXT:
    assert abs(sum(w) - 1) < 1e-12 and min(w) >= 0

# D days that the candidate actually touches: state D, not gated (gated -> cash both arms)
D_ALL_Q = [r['d'] for r in rows if r['state'] == 'D']
D_OPEN_Q = [d for d in D_ALL_Q if d not in GATE_Q]
D_ALL_R = [d for d in RDAYS[:-1] if RINFO[d]['st'] == 'D']
D_OPEN_R = [d for d in D_ALL_R if not RINFO[d]['gate']]
DSET_Q, DSET_R = set(D_OPEN_Q), set(D_OPEN_R)

# ---------------------------------------------------------------- evaluation
VOLQ = {r['d']: r['vol'] for r in rows}
def proxy_eval(drow):
    AT = {d: vt(drow, VOLQ[d]) for d in D_OPEN_Q}
    def fn(r):
        d = r['d']
        if d in DSET_Q: return AT[d]
        if d in VOTES_Q: return TDT.A_T[d][0][VOTES_Q[d]]
        return OTHER_Q[d]
    return evaluate_full(fn)

def real_sim(drow, scale=1.0, one_way=None, lag_state=None):
    """Real daily mirror, live design, with the UNGATED state-D row replaced."""
    ow = MR.ONE_WAY if one_way is None else one_way
    sched = SCHED[0][2]
    held = prev = None; out = []; risky = 0.0; nreb = 0
    for i in range(1, len(RDAYS)):
        d0, d1 = RDAYS[i - 1], RDAYS[i]
        I = RINFO[d0]; st, eff, gate = I['st'], I['eff'], I['gate']
        if lag_state is not None:
            st, eff, gate = lag_state[d0]
        if gate or st == 'E':
            v = 0; t = CASH
        elif st == 'D':
            v = 0; t = RF.vt(drow, I['vol'])
        elif d0 in VOTES_R and eff == 'A':
            v = VOTES_R[d0]; t = RF.vt(srow(sched, v), I['vol'])
        else:
            v = 0; t = RF.vt(W[eff], I['vol'])
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

def real_eval(drow, **kw):
    out, exp, reb = real_sim(drow, **kw)
    m, ser = real_metrics(out)
    return dict(m, exp=exp, reb=reb), ser

RES = {}

def stage_main():
    log("\n" + "=" * 126)
    log("RESEARCH LINE d_row_test (2026-09-20): state D = 60% SPMO / 40% cash instead of 100% QLD")
    log("=" * 126)
    log(f"  live D row {LIVE_D} (100% QLD); candidate {CAND[1]} (60% core / 40% cash)")
    log(f"  the state-D GATE is unchanged and ON: breadth pct < 0.20 OR gap200 < 0.02 -> 100% cash under BOTH arms,")
    log(f"  so this measures only the D days the design still takes risk on.")
    log(f"  proxy : state D {len(D_ALL_Q)} days ({len(D_ALL_Q)/len(rows)*100:.1f}% of {len(rows)}), "
        f"gated {len(D_ALL_Q)-len(D_OPEN_Q)}, UNGATED {len(D_OPEN_Q)} ({len(D_OPEN_Q)/len(rows)*100:.1f}% of all sessions)")
    log(f"          ungated-D search {sum(1 for d in D_OPEN_Q if d >= SEARCH[0])}, holdout {sum(1 for d in D_OPEN_Q if d <= HOLDOUT[1])}")
    log(f"  real  : state D {len(D_ALL_R)} days, gated {len(D_ALL_R)-len(D_OPEN_R)}, UNGATED {len(D_OPEN_R)} "
        f"({len(D_OPEN_R)/(len(RDAYS)-1)*100:.1f}% of {len(RDAYS)-1} sessions)")
    log("  NOTE: the proxy's core leg is QQQ (SPMO has no pre-2015 history), so proxy rows are 60/40 QQQ/cash;")
    log("        the real daily harness uses actual SPMO.")

    # what each leg actually earned on the ungated D days -- the direct diagnostic
    log("\n" + "=" * 126)
    log("1  WHAT THE LEGS ACTUALLY EARNED on the ungated D days (next-session return, bp/day, of the SIGNAL day)")
    log("=" * 126)
    LEGN = ('core', 'TQQQ', 'QLD', 'XLU', 'BOXX')
    log(f"  {'slice':<26}{'n':>6}" + "".join(f"{x:>10}" for x in LEGN) + f"{'60/40 mix':>12}")
    for lab, ds_, getleg in (('proxy full', D_OPEN_Q, lambda d: TDT.PLEG[d] if hasattr(TDT, 'PLEG') else None),):
        pass
    PL = {r['d']: r['legs'] for r in rows}
    for lab, ds_, PLX in (('proxy full', D_OPEN_Q, PL),
                          (f'proxy search {SEARCH[0]}+', [d for d in D_OPEN_Q if d >= SEARCH[0]], PL),
                          ('proxy holdout', [d for d in D_OPEN_Q if d <= HOLDOUT[1]], PL),
                          ('real daily', D_OPEN_R, RLEG_RET)):
        if not ds_: continue
        m = [sum(PLX[d][j] for d in ds_) / len(ds_) * 1e4 for j in range(5)]
        mix = 0.60 * m[0] + 0.40 * m[4]
        log(f"  {lab:<26}{len(ds_):>6}" + "".join(f"{x:>10.1f}" for x in m) + f"{mix:>12.1f}")
    log("  (QLD is the live D holding; '60/40 mix' is 0.6 x core + 0.4 x BOXX, before the vol target and costs.)")

    log("\n" + "=" * 126)
    log("2  HEADLINE. proxy full / search(2015-11+) / holdout(2000-07..2015-10) and real daily.")
    log("=" * 126)
    log(f"  {'D row':<20}| {'proxy full':>24} {'S':>7}{'H':>7}{'exp':>7}{'reb':>6} | {'real daily':>24} {'exp':>7}{'reb':>6}")
    for lab, drow in CONTEXT:
        ev, ser = proxy_eval(drow); rev, rser = real_eval(drow)
        RES[lab] = dict(ev=ev, ser=ser, rev=rev, rser=rser, drow=drow)
        mark = '  <- CANDIDATE' if lab == CAND[0] else ('  <- LIVE' if lab.startswith('LIVE') else '')
        log(f"  {lab:<20}| {fmt_ev(ev):>24} {ev['s_sharpe']:7.3f}{ev['h_sharpe']:7.3f}{ev['risky']*100:6.1f}%{ev['reb']:6.1f} | "
            f"{fmt_ev(rev):>24} {rev['exp']*100:6.1f}%{rev['reb']:6.1f}{mark}")
    L = RES['LIVE 100% QLD']
    assert abs(L['ev']['sharpe'] - LIVE_EV['sharpe']) < 1e-9 and abs(L['rev']['sharpe'] - RLIVE_EV['sharpe']) < 1e-9, \
        'the LIVE D row must reproduce the harness baseline exactly'
    log("  (the LIVE row reproduces the asserted harness baseline exactly -- asserted)")
    log("")
    log(f"  {'delta vs LIVE':<20}| {'CAGR pp':>9}{'Sharpe':>9}{'S':>8}{'H':>8}{'MaxDD pp':>10}{'exp pp':>8} | "
        f"{'real CAGR':>10}{'Sharpe':>9}{'MaxDD':>8}{'exp pp':>8}{'reb':>7}")
    for lab, _ in CONTEXT:
        if lab.startswith('LIVE'): continue
        r = RES[lab]
        log(f"  {lab:<20}| {(r['ev']['cagr']-L['ev']['cagr'])*100:+9.2f}{r['ev']['sharpe']-L['ev']['sharpe']:+9.3f}"
            f"{r['ev']['s_sharpe']-L['ev']['s_sharpe']:+8.3f}{r['ev']['h_sharpe']-L['ev']['h_sharpe']:+8.3f}"
            f"{(r['ev']['mdd']-L['ev']['mdd'])*100:+10.1f}{(r['ev']['risky']-L['ev']['risky'])*100:+8.1f} | "
            f"{(r['rev']['cagr']-L['rev']['cagr'])*100:+10.2f}{r['rev']['sharpe']-L['rev']['sharpe']:+9.3f}"
            f"{(r['rev']['mdd']-L['rev']['mdd'])*100:+8.1f}{(r['rev']['exp']-L['rev']['exp'])*100:+8.1f}{r['rev']['reb']-L['rev']['reb']:+7.1f}")
    c = RES[CAND[0]]
    log(f"\n  CANDIDATE both-era improvement: dS {c['ev']['s_sharpe']-L['ev']['s_sharpe']:+.3f}  "
        f"dH {c['ev']['h_sharpe']-L['ev']['h_sharpe']:+.3f}  -> "
        f"{'PASS' if c['ev']['s_sharpe']>L['ev']['s_sharpe'] and c['ev']['h_sharpe']>L['ev']['h_sharpe'] else 'FAIL'}")

    log("\n" + "=" * 126)
    log("3  EXPOSURE-MATCHED CONTROL: the LIVE design flat de-levered (all four risky legs x k, every day) to the arm's exposure")
    log("=" * 126)
    for lab, _ in CONTEXT:
        if lab.startswith('LIVE'): continue
        r = RES[lab]
        k, cev, cser = TDT.proxy_control(r['ev']['risky'])
        rk, rcev, rcser = TDT.real_control(r['rev']['exp'])
        r['ctrl_ser'] = cser; r['rctrl_ser'] = rcser
        log(f"  {lab:<20} proxy k {k:.4f} ctl {fmt_ev(cev)} S {cev['s_sharpe']:.3f} H {cev['h_sharpe']:.3f} | "
            f"arm-ctl F {r['ev']['sharpe']-cev['sharpe']:+.3f} S {r['ev']['s_sharpe']-cev['s_sharpe']:+.3f} "
            f"H {r['ev']['h_sharpe']-cev['h_sharpe']:+.3f} || real k {rk:.4f} ctl {fmt_ev(rcev)} "
            f"arm-ctl {r['rev']['sharpe']-rcev['sharpe']:+.3f} CAGR {(r['rev']['cagr']-rcev['cagr'])*100:+.2f} pp")

    log("\n" + "=" * 126)
    log("4  PER YEAR (return %, and the candidate minus LIVE in pp). Years with no ungated D day are identical.")
    log("=" * 126)
    for hl, evk, serk, dates, dopen in (('PROXY (QQQ core, 2000-07..2026-08)', 'ev', 'ser', PDATES, D_OPEN_Q),
                                        ('REAL DAILY (SPMO era, 2015-11+)', 'rev', 'rser', RD1, D_OPEN_R)):
        log(f"\n  {hl}")
        bl = byyear(L[serk], dates); bc = byyear(c[serk], dates)
        bq = byyear(RES['100% cash'][serk], dates)
        cnt = {}
        for d in dopen: cnt[d[:4]] = cnt.get(d[:4], 0) + 1
        log(f"  {'year':<6}{'LIVE':>9}{'60/40':>9}{'cash':>9} |{'cand-LIVE':>11}{'ungated D days':>16}")
        tot = 0.0; wins = 0; nz = 0
        for y in sorted(bl):
            d_ = (bc[y] - bl[y]) * 100
            n_ = cnt.get(y, 0)
            log(f"  {y:<6}{bl[y]*100:>9.1f}{bc[y]*100:>9.1f}{bq[y]*100:>9.1f} |{d_:>+11.1f}{n_:>16}")
            if n_:
                tot += d_; nz += 1
                if d_ > 0.05: wins += 1
        log(f"  candidate beats LIVE in {wins}/{nz} years that HAVE an ungated D day; sum of those deltas {tot:+.1f} pp")

def stage_boot():
    L = RES['LIVE 100% QLD']; c = RES[CAND[0]]
    log("\n" + "=" * 126)
    log("5a  CIRCULAR BLOCK BOOTSTRAP (2000 draws, 20d and 60d blocks; paired)")
    log("=" * 126)
    log(f"  {'comparison':<32}{'blk':>4} | {'Sharpe 95% CI':>24}{'P(<=0)':>9} | {'log-return CI pp/yr':>26}{'P(<=0)':>9}")
    for cl, a, b in (('60/40 vs LIVE, proxy', c['ser'], L['ser']),
                     ('60/40 vs control, proxy', c['ser'], c['ctrl_ser']),
                     ('60/40 vs LIVE, real', c['rser'], L['rser']),
                     ('60/40 vs control, real', c['rser'], c['rctrl_ser'])):
        for blk in (20, 60):
            l1, l2, pl, s1, s2, ps = boot(a, b, blk, seed=(hash(cl) + blk) & 0xffff)
            log(f"  {cl:<32}{blk:>3}d | [{s1:+8.3f},{s2:+8.3f}]  {ps:8.3f} | [{l1*100:+9.2f},{l2*100:+9.2f}]  {pl:8.3f}")

    log("\n" + "=" * 126)
    log("5b  LEAVE-ONE-MAJOR-REGIME-OUT (proxy full-period Sharpe with that window removed)")
    log("=" * 126)
    log(f"  {'drop':<28}{'LIVE':>9}{'60/40':>9}{'control':>9} | {'cand-LIVE':>11}{'cand-ctl':>10}")
    for rlab, a0, b0 in REGIMES:
        keep = [i for i, r in enumerate(rows) if not (a0 <= r['d'] <= b0)]
        sl = bstats([L['ser'][i] for i in keep])[1]
        sc = bstats([c['ser'][i] for i in keep])[1]
        sk = bstats([c['ctrl_ser'][i] for i in keep])[1]
        log(f"  {rlab:<28}{sl:>9.3f}{sc:>9.3f}{sk:>9.3f} | {sc-sl:>+11.3f}{sc-sk:>+10.3f}")

    log("\n" + "=" * 126)
    log("5c  ONE-SESSION STATE LAG (the whole regime read -- state, effective state and gate -- taken from the PREVIOUS close)")
    log("=" * 126)
    prevR = {d: (RDAYS[i - 1] if i else None) for i, d in enumerate(RDAYS)}
    lag = {}
    for d in RDAYS[:-1]:
        p = prevR[d]
        I = RINFO[p] if p in RINFO else RINFO[d]
        lag[d] = (I['st'], I['eff'], I['gate'])
    for lab in ('LIVE 100% QLD', CAND[0], '100% cash'):
        rev, _ = real_eval(RES[lab]['drow'], lag_state=lag)
        RES[lab]['lag'] = rev
        log(f"  lagged {lab:<20} real {fmt_ev(rev)} exp {rev['exp']*100:.1f}%")
    log(f"  60/40 - LIVE, both lagged: real Sharpe {RES[CAND[0]]['lag']['sharpe']-RES['LIVE 100% QLD']['lag']['sharpe']:+.3f}  "
        f"CAGR {(RES[CAND[0]]['lag']['cagr']-RES['LIVE 100% QLD']['lag']['cagr'])*100:+.2f} pp   "
        f"(unlagged: {c['rev']['sharpe']-L['rev']['sharpe']:+.3f} / {(c['rev']['cagr']-L['rev']['cagr'])*100:+.2f} pp)")

    log("\n" + "=" * 126)
    log("5d  20 bp ONE-WAY COST (live cost is 4 bp)")
    log("=" * 126)
    base20 = None
    for lab, _ in CONTEXT:
        rev, _ = real_eval(RES[lab]['drow'], one_way=0.0020)
        if lab.startswith('LIVE'): base20 = rev
        log(f"  20bp {lab:<20} real {fmt_ev(rev)}" +
            ('' if lab.startswith('LIVE') else
             f"   vs LIVE: Sharpe {rev['sharpe']-base20['sharpe']:+.3f}, CAGR {(rev['cagr']-base20['cagr'])*100:+.2f} pp"))

if __name__ == '__main__':
    stage_main()
    if STAGE in ('all', 'boot'): stage_boot()
    log(f"\n[done] elapsed {time.time()-T0:.0f}s")
