"""Owner (2026-09-23): "consider remove the vote in steps, idea of reentry during
the A state". The latch caps profit because it holds every vote until the book
leaves A. Stepped re-entry: votes rise at once; held votes come off ONE at a
time (never below the raw count). Fixed before running, base 30/70, TQQQ fully
out at the first vote (the current candidate schedule):
  step:5 / step:10 / step:20   one vote off per 5 / 10 / 20 sessions without a change
  stephigh                     one vote off on each new 20-session closing high
Decomposition controls: the same schedule with the LIVE release (no latch) and
with the latch; 30/70 with the live trim; live 50/50. Research only."""
import os, sys, io, contextlib, math
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
from block_bootstrap import boot
F._lf = open('paper-track/research_notes/fall_protection_r11_run.log', 'w'); log = F.log
H = F.H; D = F.DATES
def sched(s0, t0, ks, kt):
    return [(s0 * max(0, 1 - ks * v), t0 * max(0, 1 - kt * v), 1 - s0 * max(0, 1 - ks * v) - t0 * max(0, 1 - kt * v)) for v in range(4)]
FULL = sched(.3, .7, 1/6, 1.0)
ARMS = [('live 50/50 (today)',            ('X', 'live', sched(.5, .5, 1/3, 1/3))),
        ('30/70 live trim',               ('X', 'live', sched(.3, .7, 1/3, 1/3))),
        ('30/70 full cut, live release',  ('X', 'live', FULL)),
        ('30/70 full cut, latch',         ('X', 'latch', FULL)),
        ('30/70 full cut, step 5d',       ('X', 'step:5', FULL)),
        ('30/70 full cut, step 10d',      ('X', 'step:10', FULL)),
        ('30/70 full cut, step 20d',      ('X', 'step:20', FULL)),
        ('30/70 full cut, step on 20d high', ('X', 'stephigh', FULL))]
for h in H:
    assert max(abs(p - q) for p, q in zip(F.sim(h, ARMS[0][1])[0], F.LIVE[h]['ser'])) < 1e-12
def isA(x): return x['eff'] == 'A' and not x['gate'] and x['st'] not in 'EF'
log('=' * 170); log('fall_protection_r11: stepped re-entry inside A (base 30/70, TQQQ fully out at the first vote)'); log('=' * 170)
S = {}
for h in H:
    L = F.LIVE[h]
    QR = {d: F.PX[h][F.PXD[h][F.PXI[h][d] + 1]] / F.PX[h][d] - 1 for d in D[h]}
    up = [d for d in D[h] if QR[d] > 0]; dn = [d for d in D[h] if QR[d] < 0]
    log(f"\n  {h.upper()}")
    hdr = f"  {'arm':<34}{'CAGR':>8}{'dCAGR':>8}{'MaxDD':>8}{'EDGE':>7}{'exSh':>7}{'dSh':>8}"
    hdr += (f"{'holdCAGR':>10}{'holdSh':>8}" if h == 'proxy' else '') + f"{'upCap':>7}{'dnCap':>7}{'exp':>7}"
    hdr += ''.join(f"{y:>8}" for y in ('2020', '2021', '2024', '2025', '2026'))
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
        ys = ''.join(f"{(math.prod(1 + r for r, d in zip(ser, D[h]) if d[:4] == y) - 1)*100:8.1f}" for y in ('2020', '2021', '2024', '2025', '2026'))
        log(f"  {lab:<34}{c*100:7.2f}%{(c-L['cagr'])*100:+8.2f}{m*100:7.1f}%{edge:+7.2f}{sh:7.3f}{sh-L['F']:+8.3f}{ex}{uc:7.2f}{dc:7.2f}{expo*100:6.1f}%{ys}")
    log(f"  worst episodes:")
    for lo, hi, n in F.EPIS[h][:4]:
        log(f"    {n:<16}" + ''.join(f"{F.mdd_window(S[(h, lab)], D[h], lo, hi)*100:8.1f}%" for lab, _ in ARMS))
log('\n  CAP vs SAVE over the latched spells (first vote -> last A session), each arm vs 30/70 live trim, pp/yr')
for h in H:
    lat = F.sim(h, ARMS[3][1], detail=True)[0]; yrs = len(lat) / 252
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
        log(f"  {h:<6}{lab:<34} caps {cap/yrs:+6.2f}   saves {sav/yrs:+6.2f}   net {(cap+sav)/yrs:+6.2f}")
log('\n  PAIRED BLOCK BOOTSTRAP vs live 50/50 and vs 30/70 live trim (60-day blocks): excess-Sharpe 95% CI, P(not better)')
for lab, _ in ARMS[2:]:
    parts = []
    for h in H:
        for ref in ('live 50/50 (today)', '30/70 live trim'):
            l1, l2, pl, s1, s2, ps = boot(F.xs(h, S[(h, lab)]), F.xs(h, S[(h, ref)]), 60, seed=(sum(map(ord, lab + ref)) + len(h)) & 0xffff)
            parts.append(f"{h} vs {ref.split(' ')[0]+' '+ref.split(' ')[1]}: [{s1:+.3f}, {s2:+.3f}] P {ps:.2f}")
    log(f"  {lab:<34} " + '  '.join(parts))
