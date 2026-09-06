"""Stress test of research_plan_gaps.py's two survivors:
  X1  A & gap200 > X -> risky x f  (extension trim)
  X2  two-window vol control (10d to cut, 30d to restore)
Controls, real SPMO-era weekly (+ by year), threshold sweep, per-year proxy
diff, max-stat permutation (shuffle which A days are flagged, count kept)."""
import math, random, sys
sys.path.insert(0, 'paper-track')
from improvement_search import build, data, evaluate, era, header, show, vt, run, SEARCH, HOLDOUT
from improvement_search_r2 import beta_of, beta_matched_control, scaled
from downturn_review import enrich, exposure_control
from state import TARGET_WEIGHTS, compute_fast_states, compute_states, effective_state, sma, VOL_TARGET_PA
from drift_band_test import annual_stats
import return_frontier as RF
from long_history_backtest import load_px
W = TARGET_WEIGHTS


def main():
    rows = enrich(build()); D = data(); fast = compute_fast_states(D['ds'], D['qqq'])
    v = [D['qqq'][d] for d in D['ds']]; ix = {d: i for i, d in enumerate(D['ds'])}
    for r in rows:
        r['fast'] = fast[r['d']]; r['gap200'] = v[ix[r['d']]] / sma(v, ix[r['d']], 200) - 1
        r['eff'] = effective_state(r['state'], r['fast'])
    live = lambda r: vt(W[r['eff']], r['vol']); base = evaluate(rows, live)

    def trim(X, f, key='gap200'):
        def fn(r):
            w = W[r['eff']]
            if r['eff'] == 'A' and r[key] > X: w = tuple(x * f for x in w[:4]) + (1 - f * sum(w[:4]),)
            return vt(w, r['vol'])
        return fn

    print("X1 controls"); header(); show('LIVE', base)
    for X, f in ((0.15, 0.5), (0.15, 0.75), (0.20, 0.5), (0.10, 0.5)):
        fn = trim(X, f); ev = evaluate(rows, fn); show(f"A & gap>{X*100:.0f}% x{f}", ev, base)
        k1, c1 = exposure_control(rows, ev['risky']); tb = beta_of(rows, fn); k2, c2 = beta_matched_control(rows, live, tb)
        print(f"   exposure-matched (k={k1:.3f}) Sharpe {c1['sharpe']:.3f} {'PASS' if ev['sharpe']>c1['sharpe'] else 'FAIL'}; beta {tb:.2f} (k={k2:.3f}) Sharpe {c2['sharpe']:.3f} {'PASS' if ev['sharpe']>c2['sharpe'] else 'FAIL'}")

    print("\nX1 threshold sweep, f=0.5"); header()
    for X in (0.08, 0.10, 0.12, 0.14, 0.15, 0.16, 0.18, 0.20, 0.22):
        n = sum(1 for r in rows if r['eff'] == 'A' and r['gap200'] > X)
        show(f"X={X*100:.0f}% ({n} d)", evaluate(rows, trim(X, 0.5)), base)

    print("\nX1 per-year proxy diff, X=15% f=0.5")
    def byyear(fn):
        rets, _ = run(rows, fn); by = {}
        for r, x in zip(rows, rets): by[r['d'][:4]] = by.get(r['d'][:4], 0) + math.log1p(x)
        return by
    a = byyear(live); b = byyear(trim(0.15, 0.5))
    print('  ' + '  '.join(f"{y}:{(b[y]-a[y])*100:+.1f}" for y in sorted(a)))
    print(f"  better {sum(1 for y in a if b[y]>a[y])}/{len(a)}")

    print("\nX1 real SPMO-era weekly")
    rr = RF.real_rows(); qqq = load_px('data/qqq_long_history.csv'); qd = sorted(qqq); qv = [qqq[d] for d in qd]; qix = {d: i for i, d in enumerate(qd)}
    g = dict(zip(qd, compute_states(qd, qqq, short_n=20, long_n=100)))
    for r in rr:
        r['fast'] = g[r['d0']]; r['eff'] = effective_state(r['state'], r['fast']); r['gap200'] = qv[qix[r['d0']]] / sma(qv, qix[r['d0']], 200) - 1
    def rtrim(X, f):
        def fn(r):
            w = W[r['eff']]
            if X is not None and r['eff'] == 'A' and r['gap200'] > X: w = tuple(x * f for x in w[:4]) + (1 - f * sum(w[:4]),)
            return RF.vt(w, r['vol'])
        return fn
    def real_by(fn):
        prev = None; by = {}
        for r in rr:
            w = fn(r); c = RF.VL.ONE_WAY_SPREAD * sum(abs(w[i] - (prev[i] if prev else 0)) for i in range(5)); by[r['d0'][:4]] = by.get(r['d0'][:4], 0) + math.log1p(sum(w[i] * r['legs'][i] for i in range(5)) - c); prev = w
        return by
    for lab, X, f in (('live', None, 1), ('gap>10% x0.5', 0.10, 0.5), ('gap>15% x0.5', 0.15, 0.5), ('gap>15% x0.75', 0.15, 0.75), ('gap>20% x0.5', 0.20, 0.5)):
        e = RF.eval_real(rr, rtrim(X, f)); by = real_by(rtrim(X, f)); n = sum(1 for r in rr if X is not None and r['eff'] == 'A' and r['gap200'] > X)
        print(f"  {lab:<16} {e['cagr']*100:.2f}% / {e['sharpe']:.3f} / {e['mdd']*100:.1f}%  ({n:>3} wk)  " + ' '.join(f"{y[2:]}:{math.expm1(by[y])*100:+.0f}" for y in sorted(by)))

    print("\nX1 max-stat permutation (shuffle which A days are flagged; 9-threshold grid; 100 shuffles)")
    rng = random.Random(21); A = [i for i, r in enumerate(rows) if r['eff'] == 'A']
    grid = (0.08, 0.10, 0.12, 0.14, 0.15, 0.16, 0.18, 0.20, 0.22)
    real_best = max(evaluate(rows, trim(X, 0.5))['sharpe'] for X in grid) - base['sharpe']
    counts = [sum(1 for i in A if rows[i]['gap200'] > X) for X in grid]
    beats = 0; N = 100
    for _ in range(N):
        rng.shuffle(A); best = -9
        for c in counts:
            flag = set(A[:c])
            for i, r in enumerate(rows): r['pf'] = 1.0 if i in flag else -1.0
            best = max(best, annual_stats(run(rows, trim(0.0, 0.5, 'pf'))[0])[1] - base['sharpe'])
        beats += best >= real_best
    print(f"  real best gain {real_best:+.3f}; p = {beats/N:.2f}")

    print("\nX2 two-window vol control on real weekly rows (10d cut / 30d restore needs daily vol; weekly rows only carry 30d) -- proxy only:")
    print("  proxy: 19.71% / 0.797 / -32.8% (S 0.971, H 0.663) vs live 19.77 / 0.779 / -34.8. Earlier rejection of max(10d,30d): see STRATEGY.md.")


if __name__ == '__main__':
    main()
