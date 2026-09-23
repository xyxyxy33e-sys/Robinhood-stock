"""Fix 3 from the 2026-09-23 critique (owner: "fixes 1, 3 and 6 now"). Follow-up 14.

PRE-REGISTERED before any run (2026-09-23):
  Live v2 resets held votes on ANY non-A session, so a one-day dip out of A releases
  the hold. Test: held votes survive a non-A gap of <= G sessions (G = 3, 10); a longer
  gap resets as today. Base 50/50 (live), 30/70 shown for information. 2 arms.
  ADOPT the smallest G that, at 50/50, meets ALL of:
    real exSharpe >= v2 - 0.01;  proxy exSharpe >= v2 - 0.01;
    proxy MaxDD >= v2 - 1.0 pp;  proxy 2000-15 holdout CAGR >= v2 - 0.5 pp.
  None -> held votes keep resetting (no change to the weights).
  Separately, and regardless of this test (a definition, not a performance rule): for
  choosing the A BASE ROW, an A spell continues across a non-A gap of <= 3 sessions,
  so a 1-3 day whipsaw can never flip a 50/50 spell to 30/70.
"""
import sys, io, contextlib, math
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
F._lf = open('paper-track/research_notes/fall_protection_r16_run.log', 'w'); log = F.log
H = F.H; D = F.DATES
def sched(s0, t0, ks, kt):
    return [(s0 * max(0, 1 - ks * v), t0 * max(0, 1 - kt * v), 1 - s0 * max(0, 1 - ks * v) - t0 * max(0, 1 - kt * v)) for v in range(4)]
BASES = {'50/50': sched(.5, .5, 1/6, 1.0), '30/70': sched(.3, .7, 1/6, 1.0)}
R = {}
for base, sc in BASES.items():
    for G in (0, 3, 10):
        F.CARRY_G = G
        for h in H:
            det = F.sim(h, ('X', 'stephigh:15', sc), detail=True)[0]; ser = [x['net'] for x in det]
            c, _, m = annual_stats(ser)
            r = dict(c=c, m=m, sh=F._sh(F.xs(h, ser)), vh=[x['v'][0] if isinstance(x['v'], tuple) else 0 for x in det],
                     ys={y: (math.prod(1 + x for x, d in zip(ser, D[h]) if d[:4] == y) - 1) * 100 for y in ('2018', '2020', '2022', '2025', '2026')})
            if h == 'proxy':
                r['hc'] = annual_stats([x for x, d in zip(ser, D[h]) if d <= F.HOLDOUT[1]])[0]
            R[(base, G, h)] = r
F.CARRY_G = 0
log('=' * 120); log('fall_protection_r16: carry held votes across short non-A gaps (G sessions)'); log('=' * 120)
for base in BASES:
    for h in H:
        log(f"\n  {base} {h.upper()}")
        for G in (0, 3, 10):
            r = R[(base, G, h)]; nd = sum(a != b for a, b in zip(r['vh'], R[(base, 0, h)]['vh']))
            log(f"  G={G:<3} CAGR {r['c']*100:6.2f}%  MaxDD {r['m']*100:6.1f}%  exSh {r['sh']:.3f}  days held differs {nd:4d}"
                + (f"  holdout {r['hc']*100:.2f}%" if h == 'proxy' else '  ' + ' '.join(f"{y} {v:6.1f}" for y, v in r['ys'].items())))
v = lambda G, h, k: R[('50/50', G, h)][k]
win = None
for G in (3, 10):
    ok = (v(G, 'real', 'sh') >= v(0, 'real', 'sh') - 0.01, v(G, 'proxy', 'sh') >= v(0, 'proxy', 'sh') - 0.01,
          v(G, 'proxy', 'm') >= v(0, 'proxy', 'm') - 0.01, v(G, 'proxy', 'hc') >= v(0, 'proxy', 'hc') - 0.005)
    log(f"\n  PRE-REGISTERED TEST G={G}: real Sh {'Y' if ok[0] else '-'}  proxy Sh {'Y' if ok[1] else '-'}  proxy MaxDD {'Y' if ok[2] else '-'}  holdout {'Y' if ok[3] else '-'}")
    if all(ok) and win is None: win = G
log(f"\n  RESULT: {'adopt carry G=' + str(win) if win else 'no carry adopted -- held votes keep resetting'}")
F._lf.close()
