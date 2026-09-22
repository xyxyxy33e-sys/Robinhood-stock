"""Owner (2026-09-22): "then also consider only cutting tqqq, or different
percentage for the two". Trim SHAPE (where the freed weight comes from and goes),
under both the live release and the latch. Five schedules fixed before running,
(SPMO, TQQQ, cash) at 0/1/2/3 votes:
  P   proportional (live)        50/50/0  33/33/33   17/17/67   0/0/100
  TC  TQQQ only, to cash         50/50/0  50/33/17   50/17/33   50/0/50
  TS  TQQQ only, to SPMO         50/50/0  67/33/0    83/17/0    100/0/0
  TF  TQQQ first, then SPMO      50/50/0  50/25/25   50/0/50    0/0/100
  AS  asymmetric (TQQQ 1/2 per vote, SPMO 1/6 per vote)
                                 50/50/0  42/25/33   33/0/67    25/0/75
Same battery as the other fall_protection rounds. Research only."""
import os, sys, io, contextlib, math
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
from block_bootstrap import boot
F._lf = open('paper-track/research_notes/fall_protection_r6_run.log', 'w'); log = F.log
H = F.H; D = F.DATES
t3 = 1 / 3
SCH = {
  'P':  [(.5, .5, 0), (t3, t3, t3), (t3 / 2, t3 / 2, 2 * t3), (0, 0, 1)],
  'TC': [(.5, .5, 0), (.5, t3, 1 / 6), (.5, 1 / 6, t3), (.5, 0, .5)],
  'TS': [(.5, .5, 0), (2 * t3, t3, 0), (5 / 6, 1 / 6, 0), (1, 0, 0)],
  'TF': [(.5, .5, 0), (.5, .25, .25), (.5, 0, .5), (0, 0, 1)],
  'AS': [(.5, .5, 0), (5 / 12, .25, t3), (t3, 0, 2 * t3), (.25, 0, .75)],
}
NAME = {'P': 'proportional', 'TC': 'TQQQ only -> cash', 'TS': 'TQQQ only -> SPMO', 'TF': 'TQQQ first, then SPMO', 'AS': 'asymmetric 1/2 : 1/6'}
for k, rs in SCH.items():
    for r in rs: assert abs(sum(r) - 1) < 1e-9, (k, r)
ARMS = [('X', m, k) for m in ('live', 'latch') for k in SCH]
nm = lambda a: f"{a[1]:<5} {NAME[a[2]]}"
arm_of = lambda a: ('X', a[1], SCH[a[2]])
# identity: proportional under the live release must reproduce live exactly
for h in H:
    x = F.sim(h, arm_of(('X', 'live', 'P')))[0]; y = F.LIVE[h]['ser']
    assert max(abs(p - q) for p, q in zip(x, y)) < 1e-12, h
log('=' * 150); log('fall_protection_r6: trim SHAPE (cut TQQQ only / asymmetric) under the live release and the latch'); log('=' * 150)
log('  identity check passed: proportional + live release reproduces live exactly on both harnesses')
S = {}
for h in H:
    L = F.LIVE[h]
    log(f"\n  {h.upper()}")
    log(f"  {'release / shape':<30}{'CAGR':>8}{'dCAGR':>8}{'MaxDD':>8}{'EDGE':>7}{'exSh F':>8}{'dF':>8}{'dS':>8}{'dH':>8}{'reb':>6}{'exp':>7}  worst live episodes arm/live")
    for a in ARMS:
        ser, expo, reb, _ = F.sim(h, arm_of(a)); S[(h, a)] = ser
        c, _, m = annual_stats(ser); edge = (m - F.front(h, c)) * 100
        f = F._sh(F.xs(h, ser)); sS = F._sh(F.xs(h, ser, lo=F.SEARCH[0]))
        hh = F._sh(F.xs(h, ser, hi=F.HOLDOUT[1])) if h == 'proxy' else float('nan')
        eps = '  '.join(f"{n} {F.mdd_window(ser, D[h], lo, hi)*100:.1f}/{F.mdd_window(L['ser'], D[h], lo, hi)*100:.1f}" for lo, hi, n in F.EPIS[h][:4])
        dH = f"{hh-L['H']:+8.3f}" if h == 'proxy' else '      - '
        log(f"  {nm(a):<30}{c*100:7.2f}%{(c-L['cagr'])*100:+8.2f}{m*100:7.1f}%{edge:+7.2f}{f:8.3f}{f-L['F']:+8.3f}{sS-L['S']:+8.3f}{dH}{reb:6.1f}{expo*100:6.1f}%  {eps}")
log('\n  PROXY holdout 2000-2015 (CAGR / MaxDD / exSharpe)')
for a in ARMS:
    ss = [r for r, d in zip(S[('proxy', a)], D['proxy']) if d <= F.HOLDOUT[1]]
    c, _, m = annual_stats(ss)
    log(f"  {nm(a):<30} {c*100:6.2f}% / {m*100:6.1f}% / {F._sh(F.xs('proxy', S[('proxy', a)], hi=F.HOLDOUT[1])):.3f}")
log('\n  REAL calendar years 2018 / 2020 / 2021 / 2024 / 2025 / 2026, arm minus live (pp)')
for a in ARMS:
    parts = []
    for y in ('2018', '2020', '2021', '2024', '2025', '2026'):
        p = math.prod(1 + r for r, d in zip(S[('real', a)], D['real']) if d[:4] == y)
        q = math.prod(1 + r for r, d in zip(F.LIVE['real']['ser'], D['real']) if d[:4] == y)
        parts.append(f"{y} {(p-q)*100:+6.1f}")
    log(f"  {nm(a):<30} " + '  '.join(parts))
log('\n  PAIRED BLOCK BOOTSTRAP vs live (60-day blocks): excess-Sharpe 95% CI, P(not better)')
for a in ARMS:
    if a == ('X', 'live', 'P'): continue
    parts = []
    for h in H:
        l1, l2, pl, s1, s2, ps = boot(F.xs(h, S[(h, a)]), F.xs(h, F.LIVE[h]['ser']), 60, seed=(sum(map(ord, nm(a))) * 13 + len(h)) & 0xffff)
        parts.append(f"{h} [{s1:+.3f}, {s2:+.3f}] P {ps:.2f}")
    log(f"  {nm(a):<30} " + '   '.join(parts))
