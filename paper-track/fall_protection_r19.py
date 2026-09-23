"""Owner (2026-09-23): "what about the 5, 10, 15 dma". Follow-up 17. Fast-cut (SPMO cut 1/6 per
RAW vote, restored as the votes fall; TQQQ out while raw >= 1) with TQQQ returning, once raw
is back to 0, on a close ABOVE the 5 / 10 / 15-day SMA of QQQ ('fcsma:N') -- against the
new-15-day-high re-entry ('fchigh:15'), plain fast-cut and v2. Bases 50/50 and 30/70,
whipsaw carry 3. Research only."""
import sys, io, contextlib, math, statistics as stt
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
from block_bootstrap import boot
F._lf = open('paper-track/research_notes/fall_protection_r19_run.log', 'w'); log = F.log
def sched(s0, t0, ks, kt):
    return [(s0 * max(0, 1 - ks * v), t0 * max(0, 1 - kt * v), 1 - s0 * max(0, 1 - ks * v) - t0 * max(0, 1 - kt * v)) for v in range(4)]
F.CARRY_G = 3
BASES = {'50/50': sched(.5, .5, 1/6, 1.0), '30/70': sched(.3, .7, 1/6, 1.0)}
KINDS = [('fast-cut', 'live'), ('fc + 5d SMA', 'fcsma:5'), ('fc + 10d SMA', 'fcsma:10'), ('fc + 15d SMA', 'fcsma:15'),
         ('fc + 15d high', 'fchigh:15'), ('v2', 'stephigh:15')]
R = {}; S = {}
for h in F.H:
    D = F.DATES[h]; PX = F.PX[h]; PD = F.PXD[h]; PI = F.PXI[h]
    fwd = lambda d, n: PX[PD[min(PI[d] + n, len(PD) - 1)]] / PX[d] - 1
    for b, sc in BASES.items():
        for lab, k in KINDS:
            det, ex, reb, _ = F.sim(h, ('X', k, sc), detail=True); ser = [x['net'] for x in det]; S[(h, b, lab)] = ser
            c, sh, m = annual_stats(ser)[:3]
            r = dict(c=c, sh=sh, m=m, reb=reb, ys={y: (math.prod(1 + x for x, d in zip(ser, D) if d[:4] == y) - 1) * 100 for y in ('2018', '2021', '2022', '2025', '2026')})
            if h == 'proxy':
                hs = [x for x, d in zip(ser, D) if d <= F.HOLDOUT[1]]; r['hc'], r['hsh'] = annual_stats(hs)[:2]
            ents = [det[i]['d'] for i in range(1, len(det)) if det[i]['eff'] == 'A' and det[i - 1]['eff'] == 'A'
                    and det[i]['t'][1] > 1e-9 and det[i - 1]['t'][1] <= 1e-9]
            r['nent'] = len(ents); r['f20'] = stt.mean(fwd(d, 20) for d in ents) if ents else float('nan')
            r['bad'] = sum(fwd(d, 20) < 0 for d in ents) / len(ents) if ents else float('nan')
            R[(h, b, lab)] = r
log('=' * 150); log('fall_protection_r19: fast-cut with TQQQ re-entry on a close above the 5/10/15-day SMA vs the 15-day high, whipsaw carry 3'); log('=' * 150)
for h in F.H:
    for b in BASES:
        log(f"\n  {h.upper()}  base {b}")
        log(f"  {'arm':<15}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>8}{'reb':>6}{'re-entries':>11}{'QQQ+20d':>9}{'bad%':>6}" +
            (f"{'holdCAGR':>10}{'holdSh':>8}" if h == 'proxy' else ''.join(f'{y:>7}' for y in ('2018', '2021', '2022', '2025', '2026'))))
        for lab, _ in KINDS:
            r = R[(h, b, lab)]
            s = (f"  {lab:<15}{r['c']*100:7.2f}%{r['sh']:8.3f}{r['m']*100:7.1f}%{r['reb']:6.1f}{r['nent']:11d}"
                 f"{r['f20']*100:+8.2f}%{r['bad']*100:5.0f}%")
            s += f"{r['hc']*100:9.2f}%{r['hsh']:8.3f}" if h == 'proxy' else ''.join(f"{r['ys'][y]:7.1f}" for y in ('2018', '2021', '2022', '2025', '2026'))
            log(s)
log('')
for b in BASES:
    for lab in ('fc + 5d SMA', 'fc + 10d SMA', 'fc + 15d SMA'):
        for ref in ('fc + 15d high', 'fast-cut'):
            ps = [boot(F.xs(h, S[(h, b, lab)]), F.xs(h, S[(h, b, ref)]), 60, seed=(sum(map(ord, b + lab + ref)) + len(h)) & 0xffff)[5] for h in F.H]
            log(f"  {b} bootstrap {lab:<13} vs {ref:<13} P(Sharpe not better) real {ps[0]:.2f}  proxy {ps[1]:.2f}")
F._lf.close()
