"""Owner (2026-09-23): "Test a middle version, where the hold ends after a set number of
sessions or once the votes have been clear for M days." Follow-up 13. Research only.

PRE-REGISTERED before any run (written 2026-09-23, not edited after):
  Base 50/50 (the live base). Mechanism 'stepx:15:K:M' = live v2 (TQQQ out at the first
  held vote, core 1/6 per vote, one held vote off per new 15-session closing high, never
  below raw) PLUS a release of the hold to the raw count
    - K: after K sessions since the last vote rise      K in {20, 40, 60, 90}, M off
    - M: once raw votes have been 0 for M sessions      M in {3, 5, 10, 20},   K off
  8 arms, no others. References: 19 Sep design, fast-cut-only (no hold), live v2.
  An arm PASSES only if all three hold:
    P1  proxy MaxDD >= 3 pp shallower than fast-cut-only        (>= -23.6%, i.e. shallower)
    P2  real 2025+2026 compounded shortfall vs fast-cut-only is <= half of v2's shortfall
    P3  proxy 2000-2015 holdout CAGR >= the 19 Sep design's       (>= 17.84%)
  Several pass -> the best holdout excess Sharpe. None pass -> no change (v2 stays).
"""
import sys, io, contextlib, math
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
from block_bootstrap import boot
F._lf = open('paper-track/research_notes/fall_protection_r15_run.log', 'w'); log = F.log
H = F.H; D = F.DATES
def sched(s0, t0, ks, kt):
    return [(s0 * max(0, 1 - ks * v), t0 * max(0, 1 - kt * v), 1 - s0 * max(0, 1 - ks * v) - t0 * max(0, 1 - kt * v)) for v in range(4)]
V2 = sched(.5, .5, 1/6, 1.0)
REF = [('19 Sep design', ('X', 'live', sched(.5, .5, 1/3, 1/3))),
       ('fast-cut only', ('X', 'live', V2)),
       ('live v2', ('X', 'stephigh:15', V2))]
MID = [(f'hold cap K={k}', ('X', f'stepx:15:{k}:0', V2)) for k in (20, 40, 60, 90)]
MID += [(f'clear M={m}', ('X', f'stepx:15:0:{m}', V2)) for m in (3, 5, 10, 20)]
for h in H:   # K=M=0 must reproduce live v2 exactly; the untouched hook must reproduce live
    assert max(abs(p - q) for p, q in zip(F.sim(h, ('X', 'stepx:15:0:0', V2))[0], F.sim(h, REF[2][1])[0])) < 1e-12
    assert max(abs(p - q) for p, q in zip(F.sim(h, REF[0][1])[0], F.LIVE[h]['ser'])) < 1e-12
log('=' * 150); log('fall_protection_r15: middle version -- v2 hold with a session cap (K) or a clear-days release (M), base 50/50'); log('=' * 150)
S = {}; R = {}
yp = lambda ser, dd, ys: math.prod(1 + r for r, d in zip(ser, dd) if d[:4] in ys) - 1
for h in H:
    for lab, a in REF + MID:
        ser, expo, reb, _ = F.sim(h, a); S[(h, lab)] = ser
        c, _, m = annual_stats(ser)
        r = dict(c=c, m=m, sh=F._sh(F.xs(h, ser)), reb=reb, expo=expo,
                 ys={y: yp(ser, D[h], (y,)) * 100 for y in ('2018', '2021', '2022', '2024', '2025', '2026')},
                 y2526=yp(ser, D[h], ('2025', '2026')))
        if h == 'proxy':
            r['hc'] = annual_stats([x for x, d in zip(ser, D[h]) if d <= F.HOLDOUT[1]])[0]
            r['hs'] = F._sh(F.xs(h, ser, hi=F.HOLDOUT[1]))
        R[(h, lab)] = r
for h in H:
    log(f"\n  {h.upper()}")
    log(f"  {'arm':<16}{'CAGR':>8}{'MaxDD':>8}{'exSh':>7}{'expo':>6}{'reb':>6}" + (f"{'holdCAGR':>10}{'holdSh':>8}" if h == 'proxy' else ''.join(f'{y:>7}' for y in ('2018', '2021', '2022', '2024', '2025', '2026'))))
    for lab, _ in REF + MID:
        r = R[(h, lab)]
        s = f"  {lab:<16}{r['c']*100:7.2f}%{r['m']*100:7.1f}%{r['sh']:7.3f}{r['expo']:6.2f}{r['reb']:6.1f}"
        s += f"{r['hc']*100:9.2f}%{r['hs']:8.3f}" if h == 'proxy' else ''.join(f"{r['ys'][y]:7.1f}" for y in ('2018', '2021', '2022', '2024', '2025', '2026'))
        log(s)
fc, v2 = R[('real', 'fast-cut only')]['y2526'], R[('real', 'live v2')]['y2526']
p1 = R[('proxy', 'fast-cut only')]['m'] + 0.03; p3 = R[('proxy', '19 Sep design')]['hc']
log(f"\n  PRE-REGISTERED TEST  P1 proxy MaxDD >= {p1*100:.1f}%   P2 2025-26 shortfall vs fast-cut <= {(fc - v2)/2*100:.1f} pp (v2's is {(fc - v2)*100:.1f})   P3 holdout CAGR >= {p3*100:.2f}%")
passed = []
for lab, _ in MID:
    rp, rr = R[('proxy', lab)], R[('real', lab)]
    ok = (rp['m'] >= p1,   # MaxDD is negative: shallower = larger (code fixed to match the docstring rule)
           (fc - rr['y2526']) <= (fc - v2) / 2, rp['hc'] >= p3)
    log(f"  {lab:<16} P1 {'Y' if ok[0] else '-'} ({rp['m']*100:.1f})  P2 {'Y' if ok[1] else '-'} ({(fc - rr['y2526'])*100:.1f})  P3 {'Y' if ok[2] else '-'} ({rp['hc']*100:.2f})" + ('   PASS' if all(ok) else ''))
    if all(ok): passed.append(lab)
win = max(passed, key=lambda l: R[('proxy', l)]['hs']) if passed else None
log(f"\n  RESULT: {'winner ' + win if win else 'no arm passes -- no change, v2 stays'}")
cands = [win] if win else [max((l for l, _ in MID), key=lambda l: R[('proxy', l)]['hs'])]
for lab in cands:
    for ref in ('live v2', 'fast-cut only'):
        for h in H:
            l1, l2, pl, s1, s2, ps = boot(F.xs(h, S[(h, lab)]), F.xs(h, S[(h, ref)]), 60, seed=(sum(map(ord, lab + ref)) + len(h)) & 0xffff)
            log(f"  bootstrap {lab} vs {ref:<14} {h:<5} P(Sharpe not better) {ps:.2f}")
F._lf.close()
