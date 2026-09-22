"""Owner (2026-09-22): "think as vote vs deleverage". Separate the two things a
trim schedule mixes: HOW MUCH leverage each vote removes, and WHICH LEG it comes
from. Nominal leverage L = SPMO + 3 x TQQQ (the project's exposure convention;
SPMO's measured beta is ~0.77, so nominal slightly overstates core-heavy rows).

Part A -- composition at MATCHED leverage (live's path: 2.00 -> 1.33 -> 0.67 -> 0):
  P   proportional (live)          SPMO = TQQQ = L/4, rest cash
  TF  TQQQ first                   SPMO held at 50% while TQQQ absorbs the cut, then SPMO
  SF  SPMO first                   TQQQ held, SPMO cut first (most TQQQ + most cash)
  CH  core-heavy                   least TQQQ and least cash that reach L (no cash while L > 1)
Part B -- was the asymmetric schedule's gain leverage or composition?
  AS  asymmetric (fall_protection_r6), leverage path 2.00 -> 1.17 -> 0.33 -> 0.25
  PA  proportional composition on AS's leverage path
All under the live release and the latch. Research only."""
import os, sys, io, contextlib, math
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
from block_bootstrap import boot
F._lf = open('paper-track/research_notes/fall_protection_r7_run.log', 'w'); log = F.log
H = F.H; D = F.DATES

def comp(kind, L):
    """(spmo, tqqq, cash) with spmo + 3 tqqq = L, weights in [0, 1], sum 1."""
    if L <= 1e-12: return (0.0, 0.0, 1.0)
    if kind == 'P':  s = t = L / 4
    elif kind == 'TF':
        if L >= 0.5: s, t = 0.5, (L - 0.5) / 3
        else: s, t = L, 0.0
    elif kind == 'SF':
        if L >= 1.5: s, t = L - 1.5, 0.5
        else: s, t = 0.0, L / 3
    elif kind == 'CH':
        if L > 1: t = (L - 1) / 2; s = 1 - t
        else: s, t = L, 0.0
    c = 1 - s - t
    assert min(s, t, c) >= -1e-12 and abs(s + 3 * t - L) < 1e-9, (kind, L, s, t, c)
    return (s, t, max(0.0, c))

LIVE_PATH = [2.0, 4 / 3, 2 / 3, 0.0]
AS_ROWS = [(.5, .5, 0), (5 / 12, .25, 1 / 3), (1 / 3, 0, 2 / 3), (.25, 0, .75)]
AS_PATH = [s + 3 * t for s, t, _ in AS_ROWS]
SCH = {k: [comp(k, L) for L in LIVE_PATH] for k in ('P', 'TF', 'SF', 'CH')}
SCH['AS'] = AS_ROWS
SCH['PA'] = [comp('P', L) for L in AS_PATH]
NAME = {'P': 'proportional (live)', 'TF': 'TQQQ first', 'SF': 'SPMO first', 'CH': 'core-heavy',
        'AS': 'asymmetric', 'PA': 'proportional @ AS path'}
for k in SCH: assert all(abs(sum(r) - 1) < 1e-9 for r in SCH[k])
arm_of = lambda m, k: ('X', m, SCH[k])
for h in H:
    x = F.sim(h, arm_of('live', 'P'))[0]
    assert max(abs(p - q) for p, q in zip(x, F.LIVE[h]['ser'])) < 1e-12

log('=' * 150); log('fall_protection_r7: vote vs de-leverage -- composition at matched leverage, and leverage at matched composition'); log('=' * 150)
log('  schedules (SPMO/TQQQ/cash at 1, 2, 3 votes; nominal leverage in brackets):')
for k in SCH:
    log(f"   {NAME[k]:<24} " + '   '.join(f"{s*100:4.1f}/{t*100:4.1f}/{c*100:4.1f} [{s+3*t:.2f}]" for s, t, c in SCH[k][1:]))
S = {}
for part, keys in (('A  composition at LIVE leverage path 2.00 -> 1.33 -> 0.67 -> 0', ('P', 'TF', 'SF', 'CH')),
                   ('B  asymmetric vs proportional on the SAME leverage path 2.00 -> 1.17 -> 0.33 -> 0.25', ('AS', 'PA'))):
    log(f"\n{'-'*150}\n{part}\n{'-'*150}")
    for h in H:
        L = F.LIVE[h]
        log(f"  {h.upper():<6}{'release / schedule':<32}{'CAGR':>8}{'dCAGR':>8}{'MaxDD':>8}{'EDGE':>7}{'exSh F':>8}{'dF':>8}{'dS':>8}{'dH':>8}{'holdCAGR':>10}{'exp':>7}  worst live episodes arm/live")
        for m in ('live', 'latch'):
            for k in keys:
                ser, expo, reb, _ = F.sim(h, arm_of(m, k)); S[(h, m, k)] = ser
                c, _, mdd = annual_stats(ser); edge = (mdd - F.front(h, c)) * 100
                f = F._sh(F.xs(h, ser)); sS = F._sh(F.xs(h, ser, lo=F.SEARCH[0]))
                if h == 'proxy':
                    hh = F._sh(F.xs(h, ser, hi=F.HOLDOUT[1])); dH = f"{hh-L['H']:+8.3f}"
                    hc = annual_stats([r for r, d in zip(ser, D[h]) if d <= F.HOLDOUT[1]])[0]; hcs = f"{hc*100:9.2f}%"
                else: dH = '      - '; hcs = '        - '
                eps = '  '.join(f"{n} {F.mdd_window(ser, D[h], lo, hi)*100:.1f}" for lo, hi, n in F.EPIS[h][:4])
                log(f"  {'':<6}{m+' / '+NAME[k]:<32}{c*100:7.2f}%{(c-L['cagr'])*100:+8.2f}{mdd*100:7.1f}%{edge:+7.2f}{f:8.3f}{f-L['F']:+8.3f}{sS-L['S']:+8.3f}{dH}{hcs}{expo*100:6.1f}%  {eps}")
log('\n  PAIRED BLOCK BOOTSTRAP (60-day blocks): excess-Sharpe 95% CI, P(not better)')
for (a, b, why) in ((('live', 'TF'), ('live', 'P'), 'TQQQ-first vs proportional, live release, same leverage'),
                    (('live', 'CH'), ('live', 'P'), 'core-heavy vs proportional, live release, same leverage'),
                    (('live', 'SF'), ('live', 'P'), 'SPMO-first vs proportional, live release, same leverage'),
                    (('live', 'AS'), ('live', 'PA'), 'asymmetric vs proportional on AS path, live release'),
                    (('live', 'PA'), ('live', 'P'), 'AS leverage path vs live path, proportional, live release'),
                    (('latch', 'TF'), ('latch', 'P'), 'TQQQ-first vs proportional, latch'),
                    (('latch', 'AS'), ('latch', 'PA'), 'asymmetric vs proportional on AS path, latch')):
    parts = []
    for h in H:
        l1, l2, pl, s1, s2, ps = boot(F.xs(h, S[(h,) + a]), F.xs(h, S[(h,) + b]), 60, seed=(sum(map(ord, why)) + len(h)) & 0xffff)
        parts.append(f"{h} [{s1:+.3f}, {s2:+.3f}] P {ps:.2f}")
    log(f"  {why:<62} " + '   '.join(parts))
