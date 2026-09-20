"""Maximize Sharpe. BOXX is cash, so Sharpe means EXCESS return over BOXX.

Owner (2026-09-20), after the drawdown work concluded that the only lever on
drawdown is the size of the beta: "then maximize sharpe" / "treat boxx as cash".

BOXX is the risk-free leg, so every Sharpe below is computed on returns in
excess of the cash leg's own return. That makes the objective well posed: it is
SCALE-INVARIANT (verified in section 0), so it cannot be gamed by de-levering
the way a raw Sharpe can. Raising it is the only change that genuinely moves
the frontier -- raise it and you can lever back to any target return carrying
less risk than before.

Method: a one-at-a-time sweep over the PRE-SPECIFIED knob set already wired in
drawdown_study.py -- no new knobs invented to fish with -- scored on full /
search / holdout, then any settings that agree on BOTH harnesses' search era
stacked and put through the usual battery. The whole grid is one menu and is
reported as one.

NOTHING IS APPLIED. Research only.

Usage:  python3 paper-track/sharpe_study.py   [SS_STAGE=all|oat|combo]
"""
import os, sys, io, math, time, contextlib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)
sys.path.insert(0, 'paper-track')
os.environ.setdefault('TDT_STAGE', 'none')
STAGE = os.environ.get('SS_STAGE', 'all')
T0 = time.time()

LOG = 'paper-track/research_notes/sharpe_study_run.log'
_lf = open(LOG, 'a')
def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s); _lf.write(s + '\n'); _lf.flush()

_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    import drawdown_study as DS
from d_substate_fresh import rows, RDAYS, SEARCH, HOLDOUT, REGIMES, boot
from drift_band_test import annual_stats

sim = DS.sim
DATES = {'real': RDAYS[:-1], 'proxy': [r['d'] for r in rows]}
CASHR = {h: [x['lr'][4] for x in DS.dayidx(h)] for h in ('real', 'proxy')}

def _sh(x):
    if len(x) < 3: return float('nan')
    m = sum(x) / len(x)
    v = (sum((a - m) ** 2 for a in x) / (len(x) - 1)) ** 0.5
    return (m * math.sqrt(252)) / v if v else float('nan')

def sharpe(h, ser, lo=None, hi=None):
    """Sharpe of returns in EXCESS of the cash (BOXX) leg, optionally windowed."""
    x = [a - c for a, c, d in zip(ser, CASHR[h], DATES[h])
         if (lo is None or d >= lo) and (hi is None or d <= hi)]
    return _sh(x)

def score(h, **kw):
    ser, expo, reb = sim(h, **kw)
    c, s, m = annual_stats(ser)
    return dict(cagr=c, raw=s, mdd=m, exp=expo, reb=reb, ser=ser,
                F=sharpe(h, ser), S=sharpe(h, ser, lo=SEARCH[0]), H=sharpe(h, ser, hi=HOLDOUT[1]))

BX = {h: score(h) for h in ('real', 'proxy')}

def stage_trap():
    log("\n" + "=" * 134)
    log("RESEARCH LINE sharpe_study (2026-09-20): maximize Sharpe, BOXX treated as cash (excess-return Sharpe)")
    log("=" * 134)
    log("0  SANITY: with BOXX as the risk-free leg, Sharpe is scale-invariant, so 'maximize Sharpe' is well posed.")
    log("   (A RAW Sharpe is not: it drifts up as the book de-levers, purely because the cash leg pays a positive")
    log("    return at ~zero vol. That is why every number below is EXCESS of the cash leg.)")
    log("=" * 134)
    for h in ('real', 'proxy'):
        cs = CASHR[h]; c, _, _ = annual_stats(cs)
        mu = sum(cs) / len(cs); sd = (sum((x - mu) ** 2 for x in cs) / (len(cs) - 1)) ** 0.5
        log(f"\n  {h.upper()}  cash leg (BOXX): CAGR {c*100:.2f}%, annualised sd {sd*math.sqrt(252)*100:.2f}%")
        log(f"  {'k':>6}{'CAGR':>9}{'raw Sharpe':>13}{'SHARPE (ex-cash)':>19}{'MaxDD':>9}")
        for k in (1.00, 0.80, 0.60, 0.50):
            r = score(h, scale=k)
            log(f"  {k:>6.2f}{r['cagr']*100:>8.2f}%{r['raw']:>13.3f}{r['F']:>19.3f}{r['mdd']*100:>8.1f}%")
    log("\n  Flat under scaling, as it must be. Everything below maximises this number.")
    log(f"  LIVE: real Sharpe {BX['real']['F']:.3f} (search {BX['real']['S']:.3f}) | "
        f"proxy {BX['proxy']['F']:.3f} (search {BX['proxy']['S']:.3f}, holdout {BX['proxy']['H']:.3f})")

OAT = [
    ('vol target',      [(f'{v:.2f}', dict(vol_target=v)) for v in (0.12, 0.14, 0.16, 0.18, 0.20, 0.25, 0.30, 1.00)]),
    ('A row core/TQQQ', [(f'{a}/{100-a}', dict(a_row=(a / 100, 1 - a / 100, 0, 0, 0))) for a in (30, 40, 50, 60, 70)]),
    ('B row core/TQQQ', [(f'{a}/{100-a}', dict(b_row=(a / 100, 1 - a / 100, 0, 0, 0))) for a in (55, 65, 75, 85, 100)]),
    ('D row',           [('100% QLD', {}), ('TQQQ 70/30 cash', dict(d_row=(0, .70, 0, 0, .30))),
                         ('QLD 85/15 cash', dict(d_row=(0, 0, .85, 0, .15))), ('100% core', dict(d_row=(1, 0, 0, 0, 0)))]),
    ('TQQQ cap',        [('none', {}), ('0.40', dict(lev_cap=0.40)), ('0.25', dict(lev_cap=0.25)), ('0.00', dict(lev_cap=0.00))]),
    ('D gate breadth',  [(f'{b:.2f}', dict(gate_breadth=b)) for b in (0.00, 0.15, 0.20, 0.25, 0.30)]),
    ('D gate gap200',   [(f'{g:.2f}', dict(gate_gap200=g)) for g in (0.00, 0.02, 0.03, 0.05)]),
    ('macro pair',      [(f'{a}/{b}', dict(macro=(a, b))) for a, b in
                         ((50, 200), (50, 150), (60, 200), (40, 200), (40, 150), (30, 200))]),
    ('drift band',      [(f'{b:.2f}', dict(band=b)) for b in (0.02, 0.03, 0.05, 0.08, 0.12)]),
]
LIVE_TAG = {'vol target': '0.20', 'A row core/TQQQ': '50/50', 'B row core/TQQQ': '75/25', 'D row': '100% QLD',
            'TQQQ cap': 'none', 'D gate breadth': '0.20', 'D gate gap200': '0.02', 'macro pair': '50/200',
            'drift band': '0.05'}
ALL = {}

def stage_oat():
    for h in ('real', 'proxy'):
        log("\n" + "=" * 134)
        log(f"1  ONE-AT-A-TIME SWEEP, {h.upper()}. Sharpe = excess over BOXX. Deltas vs LIVE.")
        log("=" * 134)
        b = BX[h]
        log(f"  LIVE  Sharpe full {b['F']:.3f}  search {b['S']:.3f}  holdout {b['H']:.3f}   "
            f"CAGR {b['cagr']*100:.2f}%  MaxDD {b['mdd']*100:.1f}%  exp {b['exp']*100:.1f}%")
        log(f"  {'knob':<18}{'setting':<18}{'full':>8}{'search':>9}{'hold':>8}  |{'dFull':>8}{'dSearch':>9}{'dHold':>8}"
            f"{'CAGR':>9}{'MaxDD':>9}  better?")
        for knob, opts in OAT:
            for tag, kw in opts:
                r = score(h, **kw)
                ALL.setdefault(h, {})[(knob, tag)] = r
                up = (r['S'] > b['S'] + 1e-9) if h == 'real' else (r['S'] > b['S'] + 1e-9 and r['H'] > b['H'] + 1e-9)
                mark = '  <- LIVE' if tag == LIVE_TAG.get(knob) else ''
                log(f"  {knob:<18}{tag:<18}{r['F']:>8.3f}{r['S']:>9.3f}{r['H']:>8.3f}  |"
                    f"{r['F']-b['F']:>+8.3f}{r['S']-b['S']:>+9.3f}{r['H']-b['H']:>+8.3f}"
                    f"{r['cagr']*100:>8.2f}%{r['mdd']*100:>8.1f}%  {'YES' if up else ''}{mark}")
            log("")

def stage_combo():
    log("\n" + "=" * 134)
    log("2  COMBINATION: settings that raise SEARCH-era Sharpe on BOTH harnesses, stacked, then tested honestly.")
    log("=" * 134)
    agree = {}
    for (knob, tag), r in ALL['real'].items():
        rp = ALL['proxy'].get((knob, tag))
        if rp is None or tag == LIVE_TAG.get(knob): continue
        g = min(r['S'] - BX['real']['S'], rp['S'] - BX['proxy']['S'])
        if g > 1e-9:
            kw = dict(next(kk for kn, opts in OAT if kn == knob for tt, kk in opts if tt == tag))
            if knob not in agree or g > agree[knob][0]:
                agree[knob] = (g, tag, kw)
    if not agree:
        log("  NO setting raises search-era Sharpe on both harnesses. There is no stack to build.")
        log("  That IS the result: the live configuration is already the Sharpe maximum over this menu.")
        return
    log("  settings that raise search-era Sharpe on BOTH harnesses:")
    stack = {}
    for knob, (g, tag, kw) in sorted(agree.items(), key=lambda kv: -kv[1][0]):
        log(f"    {knob:<20}{tag:<18} min search gain {g:+.3f}")
        stack.update(kw)
    log(f"\n  stacked configuration: {stack}")
    log(f"\n  {'arm':<24}{'full':>8}{'search':>9}{'hold':>8}{'CAGR':>9}{'MaxDD':>9}{'exp':>8}{'reb':>7}")
    for h in ('real', 'proxy'):
        b = BX[h]; r = score(h, **stack)
        log(f"  {h.upper()+' LIVE':<24}{b['F']:>8.3f}{b['S']:>9.3f}{b['H']:>8.3f}{b['cagr']*100:>8.2f}%"
            f"{b['mdd']*100:>8.1f}%{b['exp']*100:>7.1f}%{b['reb']:>7.1f}")
        log(f"  {h.upper()+' STACK':<24}{r['F']:>8.3f}{r['S']:>9.3f}{r['H']:>8.3f}{r['cagr']*100:>8.2f}%"
            f"{r['mdd']*100:>8.1f}%{r['exp']*100:>7.1f}%{r['reb']:>7.1f}")
        log(f"  {'':24}delta full {r['F']-b['F']:+.3f}  search {r['S']-b['S']:+.3f}  holdout {r['H']-b['H']:+.3f}"
            f"  -> holdout {'HOLDS' if r['H'] > b['H'] else 'FAILS'}")
        lo, hi = 0.2, 3.0
        for _ in range(40):
            mid = (lo + hi) / 2
            if score(h, scale=mid, **stack)['cagr'] < b['cagr']: lo = mid
            else: hi = mid
        k = (lo + hi) / 2; rr = score(h, scale=k, **stack)
        log(f"  {'':24}RE-LEVERED to LIVE's CAGR: k {k:.3f} -> CAGR {rr['cagr']*100:.2f}%, MaxDD {rr['mdd']*100:.1f}% "
            f"vs LIVE {b['mdd']*100:.1f}% ({'BETTER' if rr['mdd'] > b['mdd'] else 'WORSE'} by {abs(rr['mdd']-b['mdd'])*100:.2f} pp), "
            f"exposure {rr['exp']*100:.1f}% vs {b['exp']*100:.1f}%")
        if k > 1.0:
            log(f"  {'':24}NOTE k>1 needs MORE than 100% risky -- not implementable without extra TQQQ; upper bound only.")
    log("\n  block bootstrap of the excess-return Sharpe difference, stack vs LIVE (2000 draws, paired):")
    for h in ('real', 'proxy'):
        r = score(h, **stack); b = BX[h]
        a = [x - c for x, c in zip(r['ser'], CASHR[h])]
        z = [x - c for x, c in zip(b['ser'], CASHR[h])]
        for blk in (20, 60):
            l1, l2, pl, s1, s2, ps = boot(a, z, blk, seed=(hash(h) + blk) & 0xffff)
            log(f"    {h:<6} block {blk:>2}d: Sharpe 95% CI [{s1:+.3f}, {s2:+.3f}] P(<=0)={ps:.3f}   "
                f"log-return [{l1*100:+.2f}, {l2*100:+.2f}] pp/yr P(<=0)={pl:.3f}")
    n = sum(len(o) for _, o in OAT)
    log(f"\n  MENU SIZE: {n} settings over {len(OAT)} knobs on two harnesses. Any maximum over a menu this size is")
    log("  inflated; the stack is the best cell of that menu, not an independent finding.")

if __name__ == '__main__':
    stage_trap()
    if STAGE in ('all', 'oat', 'combo'): stage_oat()
    if STAGE in ('all', 'combo'): stage_combo()
    log(f"\n[done] elapsed {time.time()-T0:.0f}s")


# ---------------------------------------------------------------- 3. the survivors, one at a time
def stage_solo():
    """The stack overfits. These are the single settings that are positive in EVERY
    era on BOTH harnesses -- the only ones entitled to a second look."""
    SOLO = [
        ('D row = TQQQ 70/30 cash', dict(d_row=(0, .70, 0, 0, .30))),
        ('B row = 100/0 (no TQQQ in B)', dict(b_row=(1.0, 0.0, 0, 0, 0))),
        ('D gate: gap200 half OFF', dict(gate_gap200=0.00)),
        ('  (all three together)', dict(d_row=(0, .70, 0, 0, .30), b_row=(1.0, 0.0, 0, 0, 0), gate_gap200=0.00)),
    ]
    log("\n" + "=" * 134)
    log("3  THE SURVIVORS. The stack in section 2 FAILED the proxy holdout (-0.071) and blew MaxDD to -48.5%:")
    log("   it switched the vol target and the gap200 gate off, both of which only look good in the search era.")
    log("   These are the settings positive in EVERY era on BOTH harnesses -- the only ones entitled to a second look.")
    log("=" * 134)
    for lab, kw in SOLO:
        log(f"\n  {lab}   {kw}")
        log(f"  {'':8}{'full':>8}{'search':>9}{'hold':>8}{'dFull':>8}{'dSearch':>9}{'dHold':>8}{'CAGR':>9}{'dCAGR':>8}{'MaxDD':>9}{'exp':>7}{'reb':>7}")
        for h in ('real', 'proxy'):
            b = BX[h]; r = score(h, **kw)
            log(f"  {h:<8}{r['F']:>8.3f}{r['S']:>9.3f}{r['H']:>8.3f}{r['F']-b['F']:>+8.3f}{r['S']-b['S']:>+9.3f}"
                f"{r['H']-b['H']:>+8.3f}{r['cagr']*100:>8.2f}%{(r['cagr']-b['cagr'])*100:>+8.2f}"
                f"{r['mdd']*100:>8.1f}%{r['exp']*100:>6.1f}%{r['reb']:>7.1f}")
            lo, hi = 0.2, 3.0
            for _ in range(40):
                mid = (lo + hi) / 2
                if score(h, scale=mid, **kw)['cagr'] < b['cagr']: lo = mid
                else: hi = mid
            k = (lo + hi) / 2; rr = score(h, scale=k, **kw)
            log(f"  {'':8}re-levered to LIVE CAGR: k {k:.3f} -> MaxDD {rr['mdd']*100:.1f}% vs LIVE {b['mdd']*100:.1f}% "
                f"({'BETTER' if rr['mdd'] > b['mdd'] else 'WORSE'} {abs(rr['mdd']-b['mdd'])*100:.2f} pp), "
                f"exposure {rr['exp']*100:.1f}% vs {b['exp']*100:.1f}%")
            a = [x - c for x, c in zip(r['ser'], CASHR[h])]
            z = [x - c for x, c in zip(b['ser'], CASHR[h])]
            for blk in (60,):
                l1, l2, pl, s1, s2, ps = boot(a, z, blk, seed=(hash(lab + h) + blk) & 0xffff)
                log(f"  {'':8}bootstrap {blk}d: Sharpe CI [{s1:+.3f}, {s2:+.3f}] P(<=0)={ps:.3f}  "
                    f"log-return [{l1*100:+.2f}, {l2*100:+.2f}] pp/yr P(<=0)={pl:.3f}")
        # leave-one-regime-out on the proxy
        r = score('proxy', **kw); b = BX['proxy']
        ds = DATES['proxy']
        outs = []
        for rlab, a0, b0 in REGIMES:
            keep = [i for i, d in enumerate(ds) if not (a0 <= d <= b0)]
            xa = [r['ser'][i] - CASHR['proxy'][i] for i in keep]
            xb = [b['ser'][i] - CASHR['proxy'][i] for i in keep]
            outs.append((rlab, _sh(xa) - _sh(xb)))
        log(f"  {'':8}LORO (proxy, Sharpe delta with each window dropped): "
            + ", ".join(f"{l.split()[0]} {v:+.3f}" for l, v in outs)
            + f"   all positive: {'YES' if all(v > 0 for _, v in outs) else 'NO'}")

if __name__ == '__main__' and STAGE in ('all', 'solo'):
    stage_solo()
    log(f"\n[done stage 3] elapsed {time.time()-T0:.0f}s")
