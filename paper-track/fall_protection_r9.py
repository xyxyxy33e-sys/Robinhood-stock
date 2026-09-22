"""Owner (2026-09-22): "check to see under 30/70, should the deleverage be quicker
since it's at a higher leverage". Base A row 30/70, latch on, freed weight to
cash. Fixed before running:
  GRID   TQQQ cut per vote kt in {1/3, 1/2 (current), 2/3, 1} x SPMO cut per vote
         ks in {1/6 (current), 1/3}  -- 8 arms, deeper = quicker de-leverage
  LM     leverage-matched: after each vote the book holds the SAME absolute
         leverage as 50/50 + both (1.17 / 0.33 / 0.25) -- i.e. cut back to where
         the 50/50 book would be
  EARLY  current schedule, votes fire earlier: thresholds 8/10/13% instead of
         10/12/15% above the 100/150/200-day
Reference: live 50/50 and the current 30/70 + latch + asymmetric. Research only."""
import os, sys, io, contextlib, math
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
from block_bootstrap import boot
F._lf = open('paper-track/research_notes/fall_protection_r9_run.log', 'w'); log = F.log
H = F.H; D = F.DATES
def sched(s0, t0, ks, kt):
    out = []
    for v in range(4):
        s = s0 * max(0.0, 1 - ks * v); t = t0 * max(0.0, 1 - kt * v); out.append((s, t, 1 - s - t))
    return out
def lm_sched():
    out = [(.3, .7, 0)]
    for L, s in ((7 / 6, .25), (1 / 3, .2), (.25, .15)):
        t = (L - s) / 3; out.append((s, t, 1 - s - t))
    return out
fr = lambda x: {1/6: '1/6', 1/3: '1/3', 1/2: '1/2', 2/3: '2/3', 1.0: '1'}[x]
ARMS = [('live 50/50 (today)', ('X', 'live', sched(.5, .5, 1/3, 1/3)))]
for ks in (1/6, 1/3):
    for kt in (1/3, 1/2, 2/3, 1.0):
        tag = '  <- current 30/70+both' if (ks, kt) == (1/6, 1/2) else ''
        ARMS.append((f"30/70 latch TQQQ {fr(kt)} SPMO {fr(ks)}{tag}", ('X', 'latch', sched(.3, .7, ks, kt))))
ARMS.append(('30/70 latch leverage-matched', ('X', 'latch', lm_sched())))
ARMS.append(('30/70 latch current, EARLY votes', ('X', 'latch', sched(.3, .7, 1/6, 1/2), (0.08, 0.10, 0.13))))
ARMS.append(('50/50 latch asym (reference)', ('X', 'latch', sched(.5, .5, 1/6, 1/2))))
for h in H:
    assert max(abs(p - q) for p, q in zip(F.sim(h, ARMS[0][1])[0], F.LIVE[h]['ser'])) < 1e-12
CUR = [l for l, _ in ARMS if 'current 30/70+both' in l][0]
log('=' * 160); log('fall_protection_r9: at 30/70, should the de-leverage be quicker?'); log('=' * 160)
for lab, a in ARMS:
    log(f"  {lab:<48} " + '  '.join(f"{s*100:4.1f}/{t*100:4.1f}/{c*100:4.1f}" for s, t, c in a[2]) + '   lev ' + '->'.join(f"{s+3*t:.2f}" for s, t, c in a[2]))
S = {}
for h in H:
    L = F.LIVE[h]
    log(f"\n  {h.upper()}")
    log(f"  {'arm':<48}{'CAGR':>8}{'dCAGR':>8}{'MaxDD':>8}{'EDGE':>7}{'exSh':>7}{'dSh':>8}" + (f"{'hold CAGR':>11}{'hold MDD':>10}{'hold Sh':>9}" if h == 'proxy' else '') + f"{'exp':>7}{'reb':>6}")
    for lab, a in ARMS:
        ser, expo, reb, _ = F.sim(h, a); S[(h, lab)] = ser
        c, _, m = annual_stats(ser); edge = (m - F.front(h, c)) * 100; sh = F._sh(F.xs(h, ser))
        extra = ''
        if h == 'proxy':
            hs = [r for r, d in zip(ser, D[h]) if d <= F.HOLDOUT[1]]; hc, _, hm = annual_stats(hs)
            extra = f"{hc*100:10.2f}%{hm*100:9.1f}%{F._sh(F.xs(h, ser, hi=F.HOLDOUT[1])):9.3f}"
        log(f"  {lab:<48}{c*100:7.2f}%{(c-L['cagr'])*100:+8.2f}{m*100:7.1f}%{edge:+7.2f}{sh:7.3f}{sh-L['F']:+8.3f}{extra}{expo*100:6.1f}%{reb:6.1f}")
log('\n  REAL: worst episodes (MaxDD inside window) and recent calendar years (%)')
EP = F.EPIS['real'][:4] + [('2022-01-01', '2022-12-31', '2022')]
log(f"  {'arm':<48}" + ''.join(f"{n[:12]:>13}" for _, _, n in EP) + ''.join(f"{y:>8}" for y in ('2020', '2024', '2025', '2026')))
for lab, _ in ARMS:
    ser = S[('real', lab)]
    eps = ''.join(f"{F.mdd_window(ser, D['real'], lo, hi)*100:12.1f}%" for lo, hi, _ in EP)
    ys = ''.join(f"{(math.prod(1 + r for r, d in zip(ser, D['real']) if d[:4] == y) - 1)*100:8.1f}" for y in ('2020', '2024', '2025', '2026'))
    log(f"  {lab:<48}{eps}{ys}")
log(f"\n  PAIRED BLOCK BOOTSTRAP vs the CURRENT 30/70+both (60-day blocks): excess-Sharpe and log-return 95% CI, P(not better)")
for lab, a in ARMS[1:]:
    if lab == CUR or 'reference' in lab: continue
    parts = []
    for h in H:
        l1, l2, pl, s1, s2, ps = boot(F.xs(h, S[(h, lab)]), F.xs(h, S[(h, CUR)]), 60, seed=(sum(map(ord, lab)) + len(h)) & 0xffff)
        parts.append(f"{h} Sh [{s1:+.3f}, {s2:+.3f}] P {ps:.2f} ret [{l1*100:+.2f}, {l2*100:+.2f}] P {pl:.2f}")
    log(f"  {lab:<48} " + '   '.join(parts))

log('\n  CONTROL: is "quicker" specific to the higher base leverage? Same TQQQ cut rates at 50/50 (latch, SPMO 1/6)')
log(f"  {'base / TQQQ cut per vote':<34}{'real CAGR':>10}{'MaxDD':>8}{'exSh':>7}{'proxy CAGR':>12}{'MaxDD':>8}{'exSh':>7}{'hold Sh':>9}")
for base in ((.5, .5), (.3, .7)):
    for kt in (1/3, 1/2, 2/3, 1.0):
        a = ('X', 'latch', sched(base[0], base[1], 1/6, kt)); row = []
        for h in H:
            ser = F.sim(h, a)[0]; c, _, m = annual_stats(ser)
            row.append((c, m, F._sh(F.xs(h, ser)), F._sh(F.xs(h, ser, hi=F.HOLDOUT[1])) if h == 'proxy' else None))
        (rc, rm, rs, _), (pc, pm, ps, ph) = row
        log(f"  {int(base[0]*100)}/{int(base[1]*100)} TQQQ {fr(kt):<22}{rc*100:9.2f}%{rm*100:7.1f}%{rs:7.3f}{pc*100:11.2f}%{pm*100:7.1f}%{ps:7.3f}{ph:9.3f}")
