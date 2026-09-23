"""Owner (2026-09-23): "What about rebalancing times". Follow-up 22. Re-tests the L1 drift band
(last tested 2026-09-09 on the pre-v2 design) under the live rule (v2 + carry 3) at A bases 50/50
and 40/60: bands 2 / 3 / 5 (live) / 7.5 / 10 / 15% and 'regime changes only' (no drift trigger).
Reports rebalances/yr and the yearly cost drag at the 4 bp model. Research only."""
import sys, io, contextlib, math
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
from block_bootstrap import boot
F._lf = open('paper-track/research_notes/fall_protection_r24_run.log', 'w'); log = F.log
def sched(s0, t0, ks, kt):
    return [(s0 * max(0, 1 - ks * v), t0 * max(0, 1 - kt * v), 1 - s0 * max(0, 1 - ks * v) - t0 * max(0, 1 - kt * v)) for v in range(4)]
F.CARRY_G = 3
BASES = [('50/50', (.5, .5)), ('40/60', (.4, .6))]
BANDS = [('2%', .02), ('3%', .03), ('5% (live)', .05), ('7.5%', .075), ('10%', .10), ('15%', .15), ('regime only', 9.9)]
R = {}; S = {}; B0 = F.REBALANCE_DRIFT_BAND
for h in F.H:
    D = F.DATES[h]; yrs = len(D) / 252
    for b, (c0, t0) in BASES:
        for lab, band in BANDS:
            F.REBALANCE_DRIFT_BAND = band
            det, ex, reb, _ = F.sim(h, ('X', 'stephigh:15', sched(c0, t0, 1/6, 1.0)), detail=True)
            ser = [x['net'] for x in det]; S[(h, b, lab)] = ser
            cost = sum(sum(w * r for w, r in zip(x['held'], x['lr'])) - x['net'] for x in det) / yrs
            c, sh, m = annual_stats(ser)[:3]
            r = dict(c=c, sh=sh, m=m, reb=reb, cost=cost)
            if h == 'proxy':
                hs = [x for x, d in zip(ser, D) if d <= F.HOLDOUT[1]]; r['hc'], r['hsh'] = annual_stats(hs)[:2]
            R[(h, b, lab)] = r
F.REBALANCE_DRIFT_BAND = B0
log('=' * 120); log('fall_protection_r24: drift band sweep under the live rule (v2 + carry 3), 4 bp one-way cost'); log('=' * 120)
for h in F.H:
    for b, _ in BASES:
        log(f"\n  {h.upper()}  base {b}")
        log(f"  {'band':<13}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>8}{'reb/yr':>8}{'cost/yr':>9}" + (f"{'holdCAGR':>10}{'holdSh':>8}" if h == 'proxy' else ''))
        for lab, _ in BANDS:
            r = R[(h, b, lab)]
            log(f"  {lab:<13}{r['c']*100:7.2f}%{r['sh']:8.3f}{r['m']*100:7.1f}%{r['reb']:8.1f}{r['cost']*100:8.2f}%"
                + (f"{r['hc']*100:9.2f}%{r['hsh']:8.3f}" if h == 'proxy' else ''))
log('')
for b, _ in BASES:
    for lab in ('3%', '10%', 'regime only'):
        ps = [boot(F.xs(h, S[(h, b, lab)]), F.xs(h, S[(h, b, '5% (live)')]), 60, seed=(sum(map(ord, b + lab)) + len(h)) & 0xffff)[5] for h in F.H]
        log(f"  {b} bootstrap band {lab:<12} vs 5% (live)  P(Sharpe not better) real {ps[0]:.2f}  proxy {ps[1]:.2f}")
F._lf.close()
