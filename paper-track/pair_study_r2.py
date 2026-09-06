"""Stress test of pair_study.py's two strong cells:
  DD  macro D + fast D (376 d, next-day QQQ ~0): hold E/F/C weights instead of 2x QLD
  EF  macro E + fast F (234 d, +29 bp/d, t 2.1):  hold C/D/A weights instead of XLU/cash
S1 controls (exposure/beta matched) for each candidate and the pair
S2 fast-window neighbours (20/80, 20/100, 25/100, 30/100, 20/60)
S3 per-year proxy diff vs live
S4 real SPMO-era weekly eval + by year
S5 DD drill: next-day return by episode age and by depth below the 50d
"""
import math, sys
sys.path.insert(0, 'paper-track')
from improvement_search import build, data, evaluate, header, show, vt, run
from improvement_search_r2 import beta_of, beta_matched_control
from downturn_review import enrich, exposure_control
from state import TARGET_WEIGHTS, compute_states, effective_state, sma
from long_history_backtest import load_px
import return_frontier as RF
W = TARGET_WEIGHTS
CANDS = {'DD->E': {('D', 'D'): 'E'}, 'DD->F': {('D', 'D'): 'F'}, 'DD->C': {('D', 'D'): 'C'},
         'EF->C': {('E', 'F'): 'C'}, 'EF->D': {('E', 'F'): 'D'}, 'EF->A': {('E', 'F'): 'A'},
         'DD->E + EF->C': {('D', 'D'): 'E', ('E', 'F'): 'C'}, 'DD->E + EF->D': {('D', 'D'): 'E', ('E', 'F'): 'D'}}


def mk(over, key='fast', vtf=vt):
    def f(r):
        st = over.get((r['state'], r[key]), effective_state(r['state'], r[key]))
        return vtf(W[st], r['vol'])
    return f


def main():
    rows = enrich(build()); D = data(); ds, px = D['ds'], D['qqq']
    fasts = {(s, l): dict(zip(ds, compute_states(ds, px, short_n=s, long_n=l))) for s, l in ((20, 60), (20, 80), (20, 100), (25, 100), (30, 100))}
    for r in rows: r['fast'] = fasts[(20, 100)][r['d']]
    live = mk({}); base = evaluate(rows, live)
    print("S1 controls"); header(); show('LIVE', base)
    for lab, over in CANDS.items():
        fn = mk(over); ev = evaluate(rows, fn); show(lab, ev, base)
        k1, c1 = exposure_control(rows, ev['risky']); tb = beta_of(rows, fn); k2, c2 = beta_matched_control(rows, live, tb)
        print(f"   exposure (k={k1:.3f}) {c1['sharpe']:.3f} {'PASS' if ev['sharpe']>c1['sharpe'] else 'FAIL'}; beta {tb:.2f} (k={k2:.3f}) {c2['sharpe']:.3f} {'PASS' if ev['sharpe']>c2['sharpe'] else 'FAIL'}")
    print("\nS2 fast-window neighbours"); header()
    for lab in ('DD->E', 'EF->C', 'DD->E + EF->C'):
        for (s, l), fs in fasts.items():
            for r in rows: r['f2'] = fs[r['d']]
            show(f"{lab} @ {s}/{l}", evaluate(rows, mk(CANDS[lab], 'f2')), evaluate(rows, mk({}, 'f2')))
    print("\nS3 per-year proxy diff vs live (pp)")
    def byyear(fn):
        rets, _ = run(rows, fn); by = {}
        for r, x in zip(rows, rets): by[r['d'][:4]] = by.get(r['d'][:4], 0) + math.log1p(x)
        return by
    a = byyear(live); out = {lab: byyear(mk(CANDS[lab])) for lab in ('DD->E', 'EF->C', 'EF->D')}
    print(f"{'year':<6}{'live':>8}" + ''.join(f"{lab:>10}" for lab in out))
    for y in sorted(a): print(f"{y:<6}{math.expm1(a[y])*100:>+7.1f}%" + ''.join(f"{(out[lab][y]-a[y])*100:>+10.1f}" for lab in out))
    print("\nS4 real SPMO-era weekly")
    rr = RF.real_rows(); qqq = load_px('data/qqq_long_history.csv'); qd = sorted(qqq)
    g = dict(zip(qd, compute_states(qd, qqq, short_n=20, long_n=100)))
    for r in rr: r['fast'] = g[r['d0']]
    def real_by(fn):
        prev = None; by = {}
        for r in rr:
            w = fn(r); c = RF.VL.ONE_WAY_SPREAD * sum(abs(w[i] - (prev[i] if prev else 0)) for i in range(5)); by[r['d0'][:4]] = by.get(r['d0'][:4], 0) + math.log1p(sum(w[i] * r['legs'][i] for i in range(5)) - c); prev = w
        return by
    for lab, over in [('live', {})] + list(CANDS.items()):
        fn = mk(over, vtf=RF.vt); e = RF.eval_real(rr, fn); by = real_by(fn)
        print(f"  {lab:<16} {e['cagr']*100:.2f}% / {e['sharpe']:.3f} / {e['mdd']*100:.1f}%  " + ' '.join(f"{y[2:]}:{math.expm1(by[y])*100:+.0f}" for y in sorted(by)))
    print("\nS5 DD drill (macro D & fast D): next-day QQQ by depth below the 50d, and XLU")
    v = [px[d] for d in ds]; ix = {d: i for i, d in enumerate(ds)}
    dd = [r for r in rows if r['state'] == 'D' and r['fast'] == 'D']
    for r in dd: r['g50'] = v[ix[r['d']]] / sma(v, ix[r['d']], 50) - 1
    for lo, hi in ((-0.2, -0.04), (-0.04, -0.02), (-0.02, -0.01), (-0.01, 0.0), (0.0, 0.01)):
        s = [r for r in dd if lo <= r['g50'] < hi]
        if s: print(f"  gap50 [{lo*100:+.0f}%,{hi*100:+.0f}%) n={len(s):3d} QQQ {sum(r['qqq'] for r in s)/len(s)*1e4:+6.1f}bp  XLU {sum(r['legs'][3] for r in s)/len(s)*1e4:+6.1f}bp  cash {sum(r['legs'][4] for r in s)/len(s)*1e4:+5.1f}bp")
    de = [r for r in rows if r['state'] == 'D' and r['fast'] != 'D']
    print(f"  all DD: QQQ {sum(r['qqq'] for r in dd)/len(dd)*1e4:+.1f}bp XLU {sum(r['legs'][3] for r in dd)/len(dd)*1e4:+.1f}bp | D & fast!=D: QQQ {sum(r['qqq'] for r in de)/len(de)*1e4:+.1f}bp XLU {sum(r['legs'][3] for r in de)/len(de)*1e4:+.1f}bp")


if __name__ == '__main__':
    main()
