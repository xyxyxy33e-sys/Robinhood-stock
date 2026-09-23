"""Owner (2026-09-23): "seems this becomes a profit cap". Measure it. For the
30/70 + latch + all-TQQQ-out-at-first-vote arm against 30/70 with the live trim
(same base, so only the latch + cut differs): every A spell in which the latch
engaged -- what QQQ did from the first vote to the end of the spell, what the
arm made vs the comparison, and how the gains and losses split. Plus
up/down capture vs QQQ. Research only."""
import os, sys, io, contextlib, math
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
F._lf = open('paper-track/research_notes/fall_protection_r10_run.log', 'w'); log = F.log
H = F.H; D = F.DATES
def sched(s0, t0, ks, kt):
    return [(s0 * max(0, 1 - ks * v), t0 * max(0, 1 - kt * v), 1 - s0 * max(0, 1 - ks * v) - t0 * max(0, 1 - kt * v)) for v in range(4)]
ARM = ('X', 'latch', sched(.3, .7, 1/6, 1.0))
CMP = ('X', 'live', sched(.3, .7, 1/3, 1/3))           # 30/70 with the live trim
LIVE = ('X', 'live', sched(.5, .5, 1/3, 1/3))
def isA(x): return x['eff'] == 'A' and not x['gate'] and x['st'] not in 'EF'
log('=' * 140); log('fall_protection_r10: is the latch + full cut a profit cap?'); log('=' * 140)
for h in H:
    QR = {d: F.PX[h][F.PXD[h][F.PXI[h][d] + 1]] / F.PX[h][d] - 1 for d in D[h] if F.PXI[h][d] + 1 < len(F.PXD[h])}
    a = F.sim(h, ARM, detail=True)[0]; c = F.sim(h, CMP, detail=True)[0]; l = F.sim(h, LIVE, detail=True)[0]
    yrs = len(a) / 252
    # spells where the latch engaged
    spells = []; i = 0
    while i < len(a):
        if isA(a[i]) and isinstance(a[i]['v'], tuple) and a[i]['v'][0] > 0:
            j = i
            while j + 1 < len(a) and isA(a[j + 1]): j += 1
            spells.append((i, j)); i = j + 1
        else: i += 1
    log(f"\n  {h.upper()}: {len(spells)} A spells in which the latch engaged ({len(spells)/yrs:.1f}/yr); window = first vote -> last A session")
    log(f"  {'first vote':<12}{'spell end':<12}{'days':>5}{'QQQ':>8}{'arm':>8}{'30/70 live-trim':>17}{'arm - cmp':>11}   type")
    rows = []
    for i, j in spells:
        q = math.prod(1 + QR.get(a[k]['d'], 0) for k in range(i, j + 1)) - 1
        ra = math.prod(1 + a[k]['net'] for k in range(i, j + 1)) - 1
        rc = math.prod(1 + c[k]['net'] for k in range(i, j + 1)) - 1
        typ = 'CAP (market kept rising)' if q > 0.02 else ('SAVE (market broke)' if q < -0.02 else 'flat')
        rows.append((a[i]['d'], a[j]['d'], j - i + 1, q, ra, rc, typ))
        log(f"  {a[i]['d']:<12}{a[j]['d']:<12}{j-i+1:5d}{q*100:+7.1f}%{ra*100:+7.1f}%{rc*100:+16.1f}%{(ra-rc)*100:+10.1f}pp   {typ}")
    caps = [r for r in rows if r[6].startswith('CAP')]; saves = [r for r in rows if r[6].startswith('SAVE')]
    lg = lambda rs: sum(math.log1p(r[4]) - math.log1p(r[5]) for r in rs) * 100
    log(f"  summary: CAP spells {len(caps)} ({sum(r[2] for r in caps)} days) cost {lg(caps):+.1f} log-pp total ({lg(caps)/yrs:+.2f}/yr); "
        f"SAVE spells {len(saves)} ({sum(r[2] for r in saves)} days) earned {lg(saves):+.1f} ({lg(saves)/yrs:+.2f}/yr); "
        f"all latched spells net {lg(rows):+.1f} ({lg(rows)/yrs:+.2f}/yr)")
    if caps: log(f"  biggest cap: {max(caps, key=lambda r: r[5]-r[4])[:2]} forgone {max((r[5]-r[4]) for r in caps)*100:.1f}pp; median cap {sorted(r[5]-r[4] for r in caps)[len(caps)//2]*100:.1f}pp")
    if saves: log(f"  biggest save: {max(saves, key=lambda r: r[4]-r[5])[:2]} saved {max((r[4]-r[5]) for r in saves)*100:.1f}pp; median save {sorted(r[4]-r[5] for r in saves)[len(saves)//2]*100:.1f}pp")
    # capture ratios vs QQQ, whole history
    log(f"  UP/DOWN CAPTURE vs QQQ (mean daily return on QQQ up days / down days, relative to QQQ's):")
    up = [d for d in D[h] if QR.get(d, 0) > 0]; dn = [d for d in D[h] if QR.get(d, 0) < 0]
    for lab, det in (('live 50/50', l), ('30/70 live trim', c), ('30/70 latch + full cut', a)):
        m = {x['d']: x['net'] for x in det}
        uc = sum(m[d] for d in up) / sum(QR[d] for d in up); dc = sum(m[d] for d in dn) / sum(QR[d] for d in dn)
        # best QQQ decile days and worst decile
        qs = sorted(D[h], key=lambda d: QR.get(d, 0)); n = len(qs) // 10
        top = sum(m[d] for d in qs[-n:]) / sum(QR[d] for d in qs[-n:]); bot = sum(m[d] for d in qs[:n]) / sum(QR[d] for d in qs[:n])
        log(f"    {lab:<24} up {uc:5.2f}x  down {dc:5.2f}x  ratio {uc/dc:4.2f}   best-10% QQQ days {top:5.2f}x  worst-10% {bot:5.2f}x")
