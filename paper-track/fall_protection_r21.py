"""Owner (2026-09-23): "What about 40/60". Follow-up 19. The live rule (v2: TQQQ out at the first
held vote, core 1/6 per vote, one vote off per new 15-session high, whipsaw carry 3) at A bases
50/50, 40/60 and 30/70. Research only."""
import sys, io, contextlib, math
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
from block_bootstrap import boot
F._lf = open('paper-track/research_notes/fall_protection_r21_run.log', 'w'); log = F.log
def sched(s0, t0, ks, kt):
    return [(s0 * max(0, 1 - ks * v), t0 * max(0, 1 - kt * v), 1 - s0 * max(0, 1 - ks * v) - t0 * max(0, 1 - kt * v)) for v in range(4)]
F.CARRY_G = 3
BASES = [('50/50 (live)', (.5, .5)), ('40/60', (.4, .6)), ('30/70 (next spell)', (.3, .7))]
YS = ('2018', '2020', '2021', '2022', '2024', '2025', '2026')
R = {}; S = {}
for h in F.H:
    D = F.DATES[h]
    for lab, (c0, t0) in BASES:
        ser, ex, reb, _ = F.sim(h, ('X', 'stephigh:15', sched(c0, t0, 1/6, 1.0))); S[(h, lab)] = ser
        c, sh, m = annual_stats(ser)[:3]
        r = dict(c=c, sh=sh, m=m, reb=reb, ex=ex, ys={y: (math.prod(1 + x for x, d in zip(ser, D) if d[:4] == y) - 1) * 100 for y in YS})
        if h == 'proxy':
            hs = [x for x, d in zip(ser, D) if d <= F.HOLDOUT[1]]; r['hc'], r['hsh'], r['hm'] = annual_stats(hs)[:3]
        R[(h, lab)] = r
log('=' * 130); log('fall_protection_r21: live rule (v2 + carry) at A bases 50/50, 40/60, 30/70'); log('=' * 130)
for h in F.H:
    log(f"\n  {h.upper()}")
    log(f"  {'base':<20}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>8}{'reb':>6}{'exp':>6}" +
        (f"{'holdCAGR':>10}{'holdSh':>8}{'holdDD':>8}" if h == 'proxy' else ''.join(f'{y:>7}' for y in YS)))
    for lab, _ in BASES:
        r = R[(h, lab)]
        s = f"  {lab:<20}{r['c']*100:7.2f}%{r['sh']:8.3f}{r['m']*100:7.1f}%{r['reb']:6.1f}{r['ex']:6.2f}"
        s += f"{r['hc']*100:9.2f}%{r['hsh']:8.3f}{r['hm']*100:7.1f}%" if h == 'proxy' else ''.join(f"{r['ys'][y]:7.1f}" for y in YS)
        log(s)
log('')
for ref in ('50/50 (live)', '30/70 (next spell)'):
    ps = [boot(F.xs(h, S[(h, '40/60')]), F.xs(h, S[(h, ref)]), 60, seed=(sum(map(ord, '4060' + ref)) + len(h)) & 0xffff)[5] for h in F.H]
    log(f"  bootstrap 40/60 vs {ref:<19} P(Sharpe not better) real {ps[0]:.2f}  proxy {ps[1]:.2f}")
F._lf.close()
