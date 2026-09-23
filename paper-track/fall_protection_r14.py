"""Owner (2026-09-23): "under this setup I feel the change in days of n will make a
difference, let's test it". Graded TQQQ re-entry with the floor (r13 F1), N-day
high N = 5, 10, 15, 20, 30, 40, 60, read as a curve; the one-step version at the
same N alongside. Base 30/70, TQQQ fully out on a fresh vote. Research only."""
import os, sys, io, contextlib, math
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
from block_bootstrap import boot
F._lf = open('paper-track/research_notes/fall_protection_r14_run.log', 'w'); log = F.log
H = F.H; D = F.DATES
def sched(s0, t0, ks, kt):
    return [(s0 * max(0, 1 - ks * v), t0 * max(0, 1 - kt * v), 1 - s0 * max(0, 1 - ks * v) - t0 * max(0, 1 - kt * v)) for v in range(4)]
FULL = sched(.3, .7, 1/6, 1.0)
NS = (5, 10, 15, 20, 30, 40, 60)
ARMS = [('live 50/50 (today)', ('X', 'live', sched(.5, .5, 1/3, 1/3)))]
ARMS += [(f'graded   N={n}', ('X', f'grade:{n}:F1', (.3, .7))) for n in NS]
ARMS += [(f'one-step N={n}', ('X', f'stephigh:{n}', FULL)) for n in NS]
for h in H:
    assert max(abs(p - q) for p, q in zip(F.sim(h, ARMS[0][1])[0], F.LIVE[h]['ser'])) < 1e-12
log('=' * 160); log('fall_protection_r14: N-day high sweep for graded re-entry (floor) and one-step re-entry, base 30/70'); log('=' * 160)
S = {}; R = {}
for h in H:
    QR = {d: F.PX[h][F.PXD[h][F.PXI[h][d] + 1]] / F.PX[h][d] - 1 for d in D[h]}
    up = [d for d in D[h] if QR[d] > 0]
    for lab, a in ARMS:
        ser, expo, reb, _ = F.sim(h, a); S[(h, lab)] = ser
        c, _, m = annual_stats(ser); mm = dict(zip(D[h], ser))
        R[(h, lab)] = dict(c=c, m=m, sh=F._sh(F.xs(h, ser)), edge=(m - F.front(h, c)) * 100,
                           uc=sum(mm[d] for d in up) / sum(QR[d] for d in up), reb=reb,
                           ys={y: (math.prod(1 + r for r, d in zip(ser, D[h]) if d[:4] == y) - 1) * 100 for y in ('2021', '2024', '2025', '2026')},
                           eps=[F.mdd_window(ser, D[h], lo, hi) * 100 for lo, hi, _ in F.EPIS[h][:3]])
        if h == 'proxy':
            R[(h, lab)]['hc'] = annual_stats([r for r, d in zip(ser, D[h]) if d <= F.HOLDOUT[1]])[0]
            R[(h, lab)]['hs'] = F._sh(F.xs(h, ser, hi=F.HOLDOUT[1]))
for h in H:
    en = [n for _, _, n in F.EPIS[h][:3]]
    log(f"\n  {h.upper()}")
    log(f"  {'arm':<20}{'CAGR':>8}{'MaxDD':>8}{'EDGE':>7}{'exSh':>7}{'upCap':>7}{'reb':>6}" + (f"{'holdCAGR':>10}{'holdSh':>8}" if h == 'proxy' else '')
        + ''.join(f"{y:>8}" for y in ('2021', '2024', '2025', '2026')) + ''.join(f"{n[:12]:>13}" for n in en))
    for lab, _ in ARMS:
        r = R[(h, lab)]
        ex = f"{r['hc']*100:9.2f}%{r['hs']:8.3f}" if h == 'proxy' else ''
        log(f"  {lab:<20}{r['c']*100:7.2f}%{r['m']*100:7.1f}%{r['edge']:+7.2f}{r['sh']:7.3f}{r['uc']:7.2f}{r['reb']:6.1f}{ex}"
            + ''.join(f"{r['ys'][y]:8.1f}" for y in ('2021', '2024', '2025', '2026')) + ''.join(f"{e:12.1f}%" for e in r['eps']))
log('\n  PAIRED BLOCK BOOTSTRAP, graded vs one-step at the same N (60-day blocks): excess-Sharpe 95% CI, P(graded not better)')
for n in NS:
    parts = []
    for h in H:
        l1, l2, pl, s1, s2, ps = boot(F.xs(h, S[(h, f'graded   N={n}')]), F.xs(h, S[(h, f'one-step N={n}')]), 60, seed=(n * 97 + len(h)) & 0xffff)
        parts.append(f"{h} [{s1:+.3f}, {s2:+.3f}] P {ps:.2f}")
    log(f"  N={n:<3} " + '   '.join(parts))
