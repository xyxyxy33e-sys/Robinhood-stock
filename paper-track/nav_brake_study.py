"""Owner (2026-10-08): "Should there be an exit rule on when dip is how far off from the
all time high" -> "re-run it on the current design".

The 2026-09-20 drawdown_study scored five NAV brakes on the 19 Sep design; every one lost
to flat de-levering on at least one harness. This re-runs the question on the CURRENT design
(extension trim v2 + 3-session whipsaw carry, D gate, E cash, 30d vol target, 5% band),
with more depths and two re-entry rules the first study did not have.

PRE-REGISTERED before any run (2026-10-08, not edited after):
  Brake: when the strategy's own NAV closes more than DEPTH below its peak, the risky legs
  are scaled by MULT on that same close (0 = all BOXX). Arms = DEPTH {5,10,15,20}% x
  MULT {0.5, 0} x RELEASE:
    nav     - off as soon as NAV closes back above the line (the 20 Sep study's rule)
    high20  - once on, stays on until QQQ makes a new 20-session closing high
    roll252 - as nav, but the peak is the ROLLING 252-session high (the funding-tier peak),
              so a brake cannot stay on forever after a deep loss
  = 24 arms. Primary base 40/60 (the next A spell); 50/50 reported for information.
  Null: flat de-levering of the same design (LEV_SCALE 0.5..1.2) -> MaxDD at equal CAGR.
  An arm PASSES only if, at 40/60, ALL hold:
    P1 EDGE (MaxDD minus the null's MaxDD at the arm's CAGR) >= +1.0 pp on BOTH harnesses;
    P2 full-period excess Sharpe >= live on both harnesses;
    P3 proxy 2000-2015 holdout excess Sharpe >= live.
  Block bootstrap reported, not gated. The VIXM sleeve is not in this harness (VIXM data
  start 2011; the proxy runs from 2000); it only touches the BOXX leg and is held ~9% of days.
  Research only -- nothing is applied by this script; the owner decides.
"""
import sys, io, contextlib, time
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
from block_bootstrap import boot
F._lf = open('paper-track/research_notes/nav_brake_study_run.log', 'w'); log = F.log
T0 = time.time()

def sched(s0, t0, ks, kt):
    return [(s0 * max(0, 1 - ks * v), t0 * max(0, 1 - kt * v), 1 - s0 * max(0, 1 - ks * v) - t0 * max(0, 1 - kt * v)) for v in range(4)]
F.CARRY_G = 3
BASES = {'40/60': sched(.4, .6, 1/6, 1.0), '50/50': sched(.5, .5, 1/6, 1.0)}
ARMS = [(dp, mu, rl) for rl in ('nav', 'high20', 'roll252') for dp in (0.05, 0.10, 0.15, 0.20) for mu in (0.5, 0.0)]
lab = lambda a: f"{int(a[0]*100)}% -> {'cash' if a[1] == 0 else 'x0.5'}, {a[2]}"

def run(h, sc, brake=None, scale=1.0):
    F.NAV_BRAKE, F.LEV_SCALE = brake, scale
    try:
        ser, expo, reb, _ = F.sim(h, ('X', 'stephigh:15', sc))
    finally:
        F.NAV_BRAKE, F.LEV_SCALE = None, 1.0
    c, _, m = annual_stats(ser)
    return dict(ser=ser, c=c, m=m, expo=expo, reb=reb, F=F._sh(F.xs(h, ser)),
                H=F._sh(F.xs(h, ser, hi=F.HOLDOUT[1])) if h == 'proxy' else float('nan'))

# hooks off must reproduce the hook-less design exactly
for h in F.H:
    a = F.sim(h, ('X', 'stephigh:15', BASES['40/60']))[0]; b = run(h, BASES['40/60'])['ser']
    assert max(abs(x - y) for x, y in zip(a, b)) < 1e-12, h

R, FR = {}, {}
for b, sc in BASES.items():
    for h in F.H:
        pts = []
        for k in (0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2):
            r = run(h, sc, scale=k); pts.append((r['c'], r['m']))
        FR[(b, h)] = sorted(pts)
        R[(b, None, h)] = run(h, sc)
        for a in ARMS:
            R[(b, a, h)] = run(h, sc, brake=a)

def front(b, h, c):
    p = FR[(b, h)]
    if c <= p[0][0]: return p[0][1]
    if c >= p[-1][0]: return p[-1][1]
    for i in range(1, len(p)):
        if c <= p[i][0]:
            f = (c - p[i-1][0]) / (p[i][0] - p[i-1][0]); return p[i-1][1] + f * (p[i][1] - p[i-1][1])

EP = {'real': [('2020-02-19', '2020-03-23', 'COVID'), ('2021-11-18', '2023-01-17', '2022 bear'), ('2025-02-18', '2025-04-30', 'spring 2025')],
      'proxy': [('2000-03-24', '2002-10-09', 'dot-com'), ('2007-10-31', '2009-03-09', 'GFC'), ('2020-02-19', '2020-03-23', 'COVID')]}
log('=' * 150); log('nav_brake_study (2026-10-08): drawdown-from-high exit rule on the current design (pre-registered)'); log('=' * 150)
for b in BASES:
    for h in F.H:
        L = R[(b, None, h)]
        log(f"\n  {h.upper()}  base {b}   null frontier (CAGR, MaxDD): " + ', '.join(f"{c*100:.1f}/{m*100:.1f}" for c, m in FR[(b, h)]))
        log(f"  {'arm':<26}{'CAGR':>8}{'MaxDD':>8}{'EDGE':>7}{'exSh':>7}{'dSh':>7}{'dHold':>7}{'expo':>6}{'reb':>6}   worst live episodes (arm / live)")
        for a in [None] + ARMS:
            e = R[(b, a, h)]
            edge = (e['m'] - front(b, h, e['c'])) * 100
            eps = '  '.join(f"{nm} {F.mdd_window(e['ser'], F.DATES[h], lo, hi)*100:.1f}/{F.mdd_window(L['ser'], F.DATES[h], lo, hi)*100:.1f}" for lo, hi, nm in EP[h])
            dH = f"{e['H']-L['H']:+7.3f}" if h == 'proxy' else '      -'
            log(f"  {('LIVE' if a is None else lab(a)):<26}{e['c']*100:7.2f}%{e['m']*100:7.1f}%{edge:+7.2f}{e['F']:7.3f}{e['F']-L['F']:+7.3f}{dH}{e['expo']*100:5.0f}%{e['reb']:6.1f}   {eps}")

log("\n  PRE-REGISTERED VERDICT (base 40/60)")
passing = []
for a in ARMS:
    E = {h: R[('40/60', a, h)] for h in F.H}; L = {h: R[('40/60', None, h)] for h in F.H}
    ed = {h: (E[h]['m'] - front('40/60', h, E[h]['c'])) * 100 for h in F.H}
    P = [all(ed[h] >= 1.0 for h in F.H), all(E[h]['F'] >= L[h]['F'] for h in F.H), E['proxy']['H'] >= L['proxy']['H']]
    ok = all(P); passing += [a] if ok else []
    log(f"  {lab(a):<26} P1 {'Y' if P[0] else 'n'} (edge real {ed['real']:+.2f} / proxy {ed['proxy']:+.2f})  "
        f"P2 {'Y' if P[1] else 'n'} (dSh {E['real']['F']-L['real']['F']:+.3f} / {E['proxy']['F']-L['proxy']['F']:+.3f})  "
        f"P3 {'Y' if P[2] else 'n'} ({E['proxy']['H']-L['proxy']['H']:+.3f})  => {'PASS' if ok else 'fail'}")
log(f"  passing: {', '.join(lab(a) for a in passing) if passing else 'none -- no drawdown exit rule'}")

log("\n  PAIRED BLOCK BOOTSTRAP vs live, 40/60 (60-day blocks, 2000 draws): excess-Sharpe 95% CI, P(not better) -- best 6 arms by proxy edge")
best = sorted(ARMS, key=lambda a: -(R[('40/60', a, 'proxy')]['m'] - front('40/60', 'proxy', R[('40/60', a, 'proxy')]['c'])))[:6]
for a in best:
    parts = []
    for h in F.H:
        l1, l2, pl, s1, s2, ps = boot(F.xs(h, R[('40/60', a, h)]['ser']), F.xs(h, R[('40/60', None, h)]['ser']), 60,
                                      seed=(sum(map(ord, lab(a))) * 31 + len(h)) & 0xffff)
        parts.append(f"{h} [{s1:+.3f}, {s2:+.3f}] P {ps:.2f}")
    log(f"  {lab(a):<26} " + '   '.join(parts))
log(f"\n  done in {time.time()-T0:.0f}s")
