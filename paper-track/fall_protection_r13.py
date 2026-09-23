"""Owner (2026-09-23): "try it" -- graded re-entry for TQQQ. Exit fast (a fresh
vote takes ALL TQQQ out), come back in thirds: each new N-session closing high
puts one third of the base TQQQ back (0 -> 23 -> 47 -> 70% at 30/70). SPMO sits at
25% while TQQQ is out or partly back, 30% when fully in. Fixed before running:
  F1  floor kept: the rung may not exceed 3 - raw votes (as before)
  F0  no floor: re-entry on new highs even while the market is still extended;
      only a FRESH vote (raw count rising) takes TQQQ out again
N = 15 (the plateau pick) and 20 (neighbour). Reference: live 50/50, 30/70 live
trim, the one-step version (step on 15d high), and the full cut with the live
release. Research only."""
import os, sys, io, contextlib, math
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
from block_bootstrap import boot
F._lf = open('paper-track/research_notes/fall_protection_r13_run.log', 'w'); log = F.log
H = F.H; D = F.DATES
def sched(s0, t0, ks, kt):
    return [(s0 * max(0, 1 - ks * v), t0 * max(0, 1 - kt * v), 1 - s0 * max(0, 1 - ks * v) - t0 * max(0, 1 - kt * v)) for v in range(4)]
FULL = sched(.3, .7, 1/6, 1.0)
ARMS = [('live 50/50 (today)',             ('X', 'live', sched(.5, .5, 1/3, 1/3))),
        ('30/70 live trim',                ('X', 'live', sched(.3, .7, 1/3, 1/3))),
        ('full cut, live release',         ('X', 'live', FULL)),
        ('one-step re-entry, 15d high',    ('X', 'stephigh:15', FULL)),
        ('GRADED, 15d high, floor',        ('X', 'grade:15:F1', (.3, .7))),
        ('GRADED, 15d high, no floor',     ('X', 'grade:15:F0', (.3, .7))),
        ('GRADED, 20d high, floor',        ('X', 'grade:20:F1', (.3, .7))),
        ('GRADED, 20d high, no floor',     ('X', 'grade:20:F0', (.3, .7)))]
for h in H:
    assert max(abs(p - q) for p, q in zip(F.sim(h, ARMS[0][1])[0], F.LIVE[h]['ser'])) < 1e-12
def isA(x): return x['eff'] == 'A' and not x['gate'] and x['st'] not in 'EF'
log('=' * 170); log('fall_protection_r13: exit fast, re-enter TQQQ in thirds on new highs (base 30/70)'); log('=' * 170)
S = {}
for h in H:
    L = F.LIVE[h]
    QR = {d: F.PX[h][F.PXD[h][F.PXI[h][d] + 1]] / F.PX[h][d] - 1 for d in D[h]}
    up = [d for d in D[h] if QR[d] > 0]; dn = [d for d in D[h] if QR[d] < 0]
    log(f"\n  {h.upper()}")
    hdr = f"  {'arm':<32}{'CAGR':>8}{'dCAGR':>8}{'MaxDD':>8}{'EDGE':>7}{'exSh':>7}{'dSh':>8}"
    hdr += (f"{'holdCAGR':>10}{'holdSh':>8}" if h == 'proxy' else '') + f"{'upCap':>7}{'dnCap':>7}{'exp':>7}{'reb':>6}"
    hdr += ''.join(f"{y:>8}" for y in ('2018', '2020', '2021', '2024', '2025', '2026'))
    log(hdr)
    for lab, a in ARMS:
        ser, expo, reb, _ = F.sim(h, a); S[(h, lab)] = ser
        c, _, m = annual_stats(ser); edge = (m - F.front(h, c)) * 100; sh = F._sh(F.xs(h, ser))
        mm = dict(zip(D[h], ser))
        uc = sum(mm[d] for d in up) / sum(QR[d] for d in up); dc = sum(mm[d] for d in dn) / sum(QR[d] for d in dn)
        ex = ''
        if h == 'proxy':
            hc = annual_stats([r for r, d in zip(ser, D[h]) if d <= F.HOLDOUT[1]])[0]
            ex = f"{hc*100:9.2f}%{F._sh(F.xs(h, ser, hi=F.HOLDOUT[1])):8.3f}"
        ys = ''.join(f"{(math.prod(1 + r for r, d in zip(ser, D[h]) if d[:4] == y) - 1)*100:8.1f}" for y in ('2018', '2020', '2021', '2024', '2025', '2026'))
        log(f"  {lab:<32}{c*100:7.2f}%{(c-L['cagr'])*100:+8.2f}{m*100:7.1f}%{edge:+7.2f}{sh:7.3f}{sh-L['F']:+8.3f}{ex}{uc:7.2f}{dc:7.2f}{expo*100:6.1f}%{reb:6.1f}{ys}")
    log(f"  worst episodes:  " + ''.join(f"{lab[:14]:>15}" for lab, _ in ARMS))
    for lo, hi, n in F.EPIS[h][:4]:
        log(f"    {n:<14}" + ''.join(f"{F.mdd_window(S[(h, lab)], D[h], lo, hi)*100:14.1f}%" for lab, _ in ARMS))
log('\n  CAP vs SAVE over the latched spells (as in r10/r11; each arm vs 30/70 live trim, pp/yr)')
for h in H:
    lat = F.sim(h, ('X', 'latch', FULL), detail=True)[0]; yrs = len(lat) / 252
    QR = {d: F.PX[h][F.PXD[h][F.PXI[h][d] + 1]] / F.PX[h][d] - 1 for d in D[h]}
    spells = []; i = 0
    while i < len(lat):
        if isA(lat[i]) and isinstance(lat[i]['v'], tuple) and lat[i]['v'][0] > 0:
            j = i
            while j + 1 < len(lat) and isA(lat[j + 1]): j += 1
            spells.append((i, j)); i = j + 1
        else: i += 1
    cmp = S[(h, '30/70 live trim')]
    for lab, _ in ARMS[2:]:
        ser = S[(h, lab)]; cap = sav = 0.0
        for i, j in spells:
            q = math.prod(1 + QR[D[h][k]] for k in range(i, j + 1)) - 1
            dlt = sum(math.log1p(ser[k]) - math.log1p(cmp[k]) for k in range(i, j + 1)) * 100
            if q > 0.02: cap += dlt
            elif q < -0.02: sav += dlt
        log(f"  {h:<6}{lab:<32} caps {cap/yrs:+6.2f}   saves {sav/yrs:+6.2f}   net {(cap+sav)/yrs:+6.2f}")
log('\n  PAIRED BLOCK BOOTSTRAP (60-day blocks): excess-Sharpe 95% CI, P(not better)')
for lab, _ in ARMS[2:]:
    parts = []
    for h in H:
        for ref in ('live 50/50 (today)', 'one-step re-entry, 15d high'):
            if ref == lab: continue
            l1, l2, pl, s1, s2, ps = boot(F.xs(h, S[(h, lab)]), F.xs(h, S[(h, ref)]), 60, seed=(sum(map(ord, lab + ref)) + len(h)) & 0xffff)
            parts.append(f"{h} vs {'live' if ref.startswith('live') else 'one-step'}: [{s1:+.3f}, {s2:+.3f}] P {ps:.2f}")
    log(f"  {lab:<32} " + '  '.join(parts))
