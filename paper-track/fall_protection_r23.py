"""Owner (2026-09-23): "With 75 tqqq try vote step down". Follow-up 21. At the 25/75 base, TQQQ is
cut in STEPS per held vote instead of all out at the first vote: kt = 1/3 (75 -> 50 -> 25 -> 0),
1/2 (75 -> 37.5 -> 0), 2/3 (75 -> 25 -> 0), 1 (live: 75 -> 0). SPMO cut 1/6 per vote, cut weight to
BOXX, held votes step down one per new 15-session high, whipsaw carry 3. Research only."""
import sys, io, contextlib, math, statistics as stt
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
from block_bootstrap import boot
F._lf = open('paper-track/research_notes/fall_protection_r23_run.log', 'w'); log = F.log
def sched(s0, t0, ks, kt):
    return [(s0 * max(0, 1 - ks * v), t0 * max(0, 1 - kt * v), 1 - s0 * max(0, 1 - ks * v) - t0 * max(0, 1 - kt * v)) for v in range(4)]
F.CARRY_G = 3
ARMS = [('50/50 all-out (live)', sched(.5, .5, 1/6, 1.0)), ('30/70 all-out', sched(.3, .7, 1/6, 1.0)),
        ('25/75 all-out', sched(.25, .75, 1/6, 1.0)), ('25/75 step 2/3', sched(.25, .75, 1/6, 2/3)),
        ('25/75 step 1/2', sched(.25, .75, 1/6, 1/2)), ('25/75 step 1/3', sched(.25, .75, 1/6, 1/3))]
YS = ('2018', '2020', '2021', '2022', '2024', '2025', '2026')
R = {}; S = {}
for h in F.H:
    D = F.DATES[h]
    for lab, sc in ARMS:
        ser, ex, reb, _ = F.sim(h, ('X', 'stephigh:15', sc)); S[(h, lab)] = ser
        c, sh, m = annual_stats(ser)[:3]
        r = dict(c=c, sh=sh, m=m, reb=reb, ex=ex, ys={y: (math.prod(1 + x for x, d in zip(ser, D) if d[:4] == y) - 1) * 100 for y in YS})
        if h == 'proxy':
            hs = [x for x, d in zip(ser, D) if d <= F.HOLDOUT[1]]; r['hc'], r['hsh'], r['hm'] = annual_stats(hs)[:3]
            r['eps'] = [F.mdd_window(ser, D, lo, hi) * 100 for lo, hi, _ in F.EPIS[h][:3]]
        R[(h, lab)] = r
log('=' * 140); log('fall_protection_r23: stepped TQQQ cut per held vote at the 25/75 base (v2 hold, carry 3)'); log('=' * 140)
for h in F.H:
    log(f"\n  {h.upper()}")
    log(f"  {'arm':<22}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>8}{'reb':>6}{'exp':>6}" +
        (f"{'holdCAGR':>10}{'holdSh':>8}  worst episodes ({', '.join(n for _, _, n in F.EPIS[h][:3])})" if h == 'proxy' else ''.join(f'{y:>7}' for y in YS)))
    for lab, _ in ARMS:
        r = R[(h, lab)]
        s = f"  {lab:<22}{r['c']*100:7.2f}%{r['sh']:8.3f}{r['m']*100:7.1f}%{r['reb']:6.1f}{r['ex']:6.2f}"
        s += (f"{r['hc']*100:9.2f}%{r['hsh']:8.3f}  " + ' / '.join(f'{e:.1f}%' for e in r['eps'])) if h == 'proxy' else ''.join(f"{r['ys'][y]:7.1f}" for y in YS)
        log(s)
log('')
for lab in ('25/75 step 2/3', '25/75 step 1/2', '25/75 step 1/3'):
    ps = [boot(F.xs(h, S[(h, lab)]), F.xs(h, S[(h, '25/75 all-out')]), 60, seed=(sum(map(ord, lab)) + len(h)) & 0xffff)[5] for h in F.H]
    log(f"  bootstrap {lab:<15} vs 25/75 all-out  P(Sharpe not better) real {ps[0]:.2f}  proxy {ps[1]:.2f}")
F._lf.close()
