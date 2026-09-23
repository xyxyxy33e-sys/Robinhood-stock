"""Owner (2026-09-23): "i feel the 15 day high might also work well in other places" / "yes run it".
Follow-up 23.

PRE-REGISTERED before any run (2026-09-23, not edited after):
  Four arms, each the live design (v2 + whipsaw carry 3) plus ONE new-15-session-closing-high gate:
    gate    -- after the state-D gate clears, D stays in BOXX until a new 15-day high
               (cleared early if the effective state returns to A/B/C)
    spell   -- at the start of a new A spell (after a non-A gap > 3 sessions) TQQQ waits for a
               new 15-day high (SPMO at its base; the TQQQ weight sits in BOXX meanwhile)
    overlay -- when the 20/100 fast re-entry overlay switches on (B/C -> A row, F -> C row), the
               upgrade waits for a new 15-day high (the macro row is held meanwhile)
    vol     -- the vol-target multiplier may fall at once but may only RISE on a new-15-day-high day
  Primary base 40/60 (the base for the next A spell); 50/50 reported for information.
  An arm PASSES only if, at 40/60, ALL hold against the live design:
    P1 real Sharpe > live;  P2 proxy Sharpe > live;  P3 proxy 2000-2015 holdout Sharpe >= live;
    P4 proxy MaxDD no more than 1.0 pp deeper than live.
  Each passing arm is a candidate on its own; combinations are NOT tested today. The block
  bootstrap is reported, not gated. Research only -- nothing is applied by this script.
"""
import sys, io, contextlib, math
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
from block_bootstrap import boot
F._lf = open('paper-track/research_notes/fall_protection_r25_run.log', 'w'); log = F.log
def sched(s0, t0, ks, kt):
    return [(s0 * max(0, 1 - ks * v), t0 * max(0, 1 - kt * v), 1 - s0 * max(0, 1 - ks * v) - t0 * max(0, 1 - kt * v)) for v in range(4)]
F.CARRY_G = 3
BASES = {'40/60': sched(.4, .6, 1/6, 1.0), '50/50': sched(.5, .5, 1/6, 1.0)}
ARMS = [('live', frozenset()), ('gate', frozenset({'gate'})), ('spell', frozenset({'spell'})),
        ('overlay', frozenset({'overlay'})), ('vol', frozenset({'vol'}))]
YS = ('2018', '2020', '2022', '2023', '2025', '2026')
R = {}; S = {}
for b, sc in BASES.items():
    for lab, hr in ARMS:
        F.HIGHREL = hr
        for h in F.H:
            D = F.DATES[h]
            ser, ex, reb, _ = F.sim(h, ('X', 'stephigh:15', sc)); S[(b, lab, h)] = ser
            c, sh, m = annual_stats(ser)[:3]
            r = dict(c=c, sh=sh, m=m, reb=reb, ex=ex, ys={y: (math.prod(1 + x for x, d in zip(ser, D) if d[:4] == y) - 1) * 100 for y in YS})
            if h == 'proxy':
                hs = [x for x, d in zip(ser, D) if d <= F.HOLDOUT[1]]; r['hc'], r['hsh'], r['hm'] = annual_stats(hs)[:3]
                r['eps'] = [F.mdd_window(ser, D, lo, hi) * 100 for lo, hi, _ in F.EPIS[h][:3]]
            R[(b, lab, h)] = r
F.HIGHREL = frozenset()
# the live arm must still be the live design
for h in F.H:
    F.CARRY_G = 3
    ref = F.sim(h, ('X', 'stephigh:15', BASES['40/60']))[0]
    assert max(abs(p - q) for p, q in zip(ref, S[('40/60', 'live', h)])) < 1e-12
log('=' * 150); log('fall_protection_r25: a new 15-day high as a re-lever gate in four other places (pre-registered)'); log('=' * 150)
for b in BASES:
    for h in F.H:
        log(f"\n  {h.upper()}  base {b}")
        log(f"  {'arm':<9}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>8}{'reb':>6}{'exp':>6}" +
            (f"{'holdCAGR':>10}{'holdSh':>8}  worst episodes ({', '.join(n for _, _, n in F.EPIS[h][:3])})" if h == 'proxy' else ''.join(f'{y:>7}' for y in YS)))
        for lab, _ in ARMS:
            r = R[(b, lab, h)]
            s = f"  {lab:<9}{r['c']*100:7.2f}%{r['sh']:8.3f}{r['m']*100:7.1f}%{r['reb']:6.1f}{r['ex']:6.2f}"
            s += (f"{r['hc']*100:9.2f}%{r['hsh']:8.3f}  " + ' / '.join(f'{e:.1f}%' for e in r['eps'])) if h == 'proxy' else ''.join(f"{r['ys'][y]:7.1f}" for y in YS)
            log(s)
L = lambda lab, h, k: R[('40/60', lab, h)][k]
log('\n  PRE-REGISTERED TEST at 40/60 (P1 real Sh > live, P2 proxy Sh > live, P3 holdout Sh >= live, P4 proxy MaxDD >= live - 1pp)')
passed = []
for lab, _ in ARMS[1:]:
    ok = (L(lab, 'real', 'sh') > L('live', 'real', 'sh'), L(lab, 'proxy', 'sh') > L('live', 'proxy', 'sh'),
          L(lab, 'proxy', 'hsh') >= L('live', 'proxy', 'hsh'), L(lab, 'proxy', 'm') >= L('live', 'proxy', 'm') - 0.01)
    ps = [boot(F.xs(h, S[('40/60', lab, h)]), F.xs(h, S[('40/60', 'live', h)]), 60, seed=(sum(map(ord, lab)) + len(h)) & 0xffff)[5] for h in F.H]
    log(f"  {lab:<9} P1 {'Y' if ok[0] else '-'}  P2 {'Y' if ok[1] else '-'}  P3 {'Y' if ok[2] else '-'}  P4 {'Y' if ok[3] else '-'}"
        f"   bootstrap P(not better) real {ps[0]:.2f} proxy {ps[1]:.2f}" + ('   PASS' if all(ok) else ''))
    if all(ok): passed.append(lab)
log(f"\n  RESULT: {'candidates: ' + ', '.join(passed) if passed else 'no arm passes -- nothing to apply'}")
F._lf.close()
