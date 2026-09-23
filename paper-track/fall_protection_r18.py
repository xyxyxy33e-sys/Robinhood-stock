"""Owner (2026-09-23): "try 30/70 with fast-cut plus new high". Follow-up 16. SPMO cut 1/6 per
RAW vote and restored as the votes fall; TQQQ out while raw >= 1 and back only on a new N-session
closing high once raw is 0 (fchigh). Base 30/70 (the base scheduled for the next A spell), with
50/50 live references. Whipsaw carry 3. Research only."""
import sys, io, contextlib, math, statistics as stt
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
from block_bootstrap import boot
F._lf = open('paper-track/research_notes/fall_protection_r18_run.log', 'w'); log = F.log
def sched(s0, t0, ks, kt):
    return [(s0 * max(0, 1 - ks * v), t0 * max(0, 1 - kt * v), 1 - s0 * max(0, 1 - ks * v) - t0 * max(0, 1 - kt * v)) for v in range(4)]
V2 = sched(.5, .5, 1/6, 1.0); V3 = sched(.3, .7, 1/6, 1.0); F.CARRY_G = 3
ARMS = [('v2 50/50 (live)', ('X', 'stephigh:15', V2)), ('fc+high15 50/50', ('X', 'fchigh:15', V2)), ('fast-cut 30/70', ('X', 'live', V3)), ('v2 30/70', ('X', 'stephigh:15', V3))] + [(f'fc+high{n} 30/70', ('X', f'fchigh:{n}', V3)) for n in (15, 10, 20)]
R = {}; S = {}
for h in F.H:
    D = F.DATES[h]; PX = F.PX[h]; PD = F.PXD[h]; PI = F.PXI[h]
    fwd = lambda d, n: PX[PD[min(PI[d] + n, len(PD) - 1)]] / PX[d] - 1
    for lab, a in ARMS:
        det, ex, reb, _ = F.sim(h, a, detail=True); ser = [x['net'] for x in det]; S[(h, lab)] = ser
        c, sh, m = annual_stats(ser)[:3]
        r = dict(c=c, sh=sh, m=m, reb=reb, ex=ex,
                 ys={y: (math.prod(1 + x for x, d in zip(ser, D) if d[:4] == y) - 1) * 100 for y in ('2018', '2020', '2021', '2024', '2025', '2026')})
        if h == 'proxy':
            hs = [x for x, d in zip(ser, D) if d <= F.HOLDOUT[1]]; r['hc'], r['hsh'], r['hm'] = annual_stats(hs)[:3]
        ents = [det[i]['d'] for i in range(1, len(det)) if det[i]['eff'] == 'A' and det[i - 1]['eff'] == 'A'
                and det[i]['t'][1] > 1e-9 and det[i - 1]['t'][1] <= 1e-9]
        r['nent'] = len(ents); r['f20'] = stt.mean(fwd(d, 20) for d in ents) if ents else float('nan')
        r['bad'] = sum(fwd(d, 20) < 0 for d in ents) / len(ents) if ents else float('nan')
        R[(h, lab)] = r
    allA = [x['d'] for x in det if x['eff'] == 'A']
    R[(h, 'base20')] = stt.mean(fwd(d, 20) for d in allA)
log('=' * 150); log('fall_protection_r18: fast-cut + new-high TQQQ re-entry at the 30/70 base, whipsaw carry 3'); log('=' * 150)
for h in F.H:
    log(f"\n  {h.upper()}   (QQQ next-20d mean on any A day {R[(h, 'base20')]*100:+.2f}%)")
    log(f"  {'arm':<18}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>8}{'reb':>6}{'exp':>6}{'re-entries':>11}{'QQQ+20d':>9}{'bad%':>6}" +
        (f"{'holdCAGR':>10}{'holdSh':>8}{'holdDD':>8}" if h == 'proxy' else ''.join(f'{y:>7}' for y in ('2018', '2020', '2021', '2024', '2025', '2026'))))
    for lab, _ in ARMS:
        r = R[(h, lab)]
        s = (f"  {lab:<18}{r['c']*100:7.2f}%{r['sh']:8.3f}{r['m']*100:7.1f}%{r['reb']:6.1f}{r['ex']:6.2f}{r['nent']:11d}"
             f"{r['f20']*100:+8.2f}%{r['bad']*100:5.0f}%")
        s += f"{r['hc']*100:9.2f}%{r['hsh']:8.3f}{r['hm']*100:7.1f}%" if h == 'proxy' else ''.join(f"{r['ys'][y]:7.1f}" for y in ('2018', '2020', '2021', '2024', '2025', '2026'))
        log(s)
log('')
for ref in ('v2 30/70', 'fast-cut 30/70', 'v2 50/50 (live)'):
    for h in F.H:
        _, _, _, _, _, ps = boot(F.xs(h, S[(h, 'fc+high15 30/70')]), F.xs(h, S[(h, ref)]), 60, seed=(sum(map(ord, 'fch15' + ref)) + len(h)) & 0xffff)
        log(f"  bootstrap fast-cut+high 15 vs {ref:<16} {h:<5} P(Sharpe not better) {ps:.2f}")
F._lf.close()
