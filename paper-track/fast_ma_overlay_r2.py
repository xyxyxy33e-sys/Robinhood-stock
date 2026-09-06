"""Stress test of fast_ma_overlay_test.py's survivors: R2b (macro B/C with
the 20/60 reading in A/B -> hold A weights) and R4 (macro F with 20/60 in
A/B/C -> hold C weights = 100% core), alone and combined.
  S1 exposure- and beta-matched controls
  S2 neighbouring fast windows (does it hold off the 20/60 point?)
  S3 per-year difference vs live, proxy and real; flagged-day counts
  S4 max-statistic permutation: shuffle WHICH B/C (resp. F) days are
     flagged, preserving the count, 200 shuffles, best over the window grid
  S5 rebalances/yr
"""
import math, random, sys
sys.path.insert(0, 'paper-track')
from improvement_search import build, data, evaluate, era, header, show, vt, run, SEARCH, HOLDOUT
from improvement_search_r2 import beta_of, beta_matched_control, scaled
from downturn_review import enrich, live, exposure_control
from fast_ma_overlay_test import add_fast, UP, DOWN
import return_frontier as RF
from state import TARGET_WEIGHTS, compute_states
from long_history_backtest import load_px
from drift_band_test import annual_stats
W = TARGET_WEIGHTS

def mk(kind, key='fast'):
    def f(r):
        m, fs = r['state'], r[key]
        if kind in ('R2b', 'both') and m in 'BC' and fs in 'AB': w = W['A']
        elif kind in ('R4', 'both') and m == 'F' and fs in UP: w = W['C']
        else: w = W[m]
        return vt(w, r['vol'])
    return f

def byyear(rows, fn):
    rets, _ = run(rows, fn); by = {}
    for r, x in zip(rows, rets): by[r['d'][:4]] = by.get(r['d'][:4], 0) + math.log1p(x)
    return by

def rebal_per_year(rows, fn, band=0.03):
    held = None; n = 0
    for r in rows:
        t = fn(r)
        if held is None or sum(abs(t[j] - held[j]) for j in range(5)) > band: n += 1; held = list(t)
        else:
            g = sum(held[j] * r['legs'][j] for j in range(5)); held = [held[j] * (1 + r['legs'][j]) / (1 + g) for j in range(5)]
    return n / (len(rows) / 252)

def main():
    rows = add_fast(enrich(build())); base = evaluate(rows, live())
    print("S1 controls"); header(); show('LIVE', base)
    for kind in ('R2b', 'R4', 'both'):
        fn = mk(kind); ev = evaluate(rows, fn); show(kind, ev, base)
        k1, c1 = exposure_control(rows, ev['risky']); tb = beta_of(rows, fn); k2, c2 = beta_matched_control(rows, live(), tb)
        print(f"   exposure-matched (k={k1:.3f}) Sharpe {c1['sharpe']:.3f} {'PASS' if ev['sharpe']>c1['sharpe'] else 'FAIL'}; "
              f"beta-matched (beta {tb:.2f}, k={k2:.3f}) Sharpe {c2['sharpe']:.3f} {'PASS' if ev['sharpe']>c2['sharpe'] else 'FAIL'}; "
              f"rebal/yr {rebal_per_year(rows, fn):.0f} (live {rebal_per_year(rows, live()):.0f})")

    print("\nS2 neighbouring fast windows, 'both' rule"); header()
    D = data(); ds, px = D['ds'], D['qqq']
    grid = [(10, 30), (10, 50), (15, 45), (20, 60), (20, 100), (25, 75), (30, 90), (30, 150), (40, 120)]
    for s, l in grid:
        fs = dict(zip(ds, compute_states(ds, px, short_n=s, long_n=l)))
        for r in rows: r['f2'] = fs[r['d']]
        show(f"fast {s}/{l}", evaluate(rows, mk('both', 'f2')), base)

    print("\nS3 per-year diff vs live (proxy), 'both'")
    a = byyear(rows, live()); b = byyear(rows, mk('both'))
    for y in sorted(a):
        nb = sum(1 for r in rows if r['d'][:4] == y and r['state'] in 'BC' and r['fast'] in 'AB')
        nf = sum(1 for r in rows if r['d'][:4] == y and r['state'] == 'F' and r['fast'] in UP)
        print(f"  {y} live {math.expm1(a[y])*100:+6.1f}%  both {math.expm1(b[y])*100:+6.1f}%  diff {(b[y]-a[y])*100:+5.1f}pp  B/C-flag {nb:3d}  F-flag {nf:3d}")
    print(f"  years better: {sum(1 for y in a if b[y]>a[y])}/{len(a)}")
    print("\n  real weekly by year, live vs both:")
    rr = RF.real_rows(); qqq = load_px('data/qqq_long_history.csv'); qd = sorted(qqq)
    fast = dict(zip(qd, compute_states(qd, qqq, short_n=20, long_n=60)))
    for r in rr: r['fast'] = fast[r['d0']]
    def real_by(fn):
        prev = None; by = {}
        for r in rr:
            w = fn(r); cost = RF.VL.ONE_WAY_SPREAD * sum(abs(w[i] - (prev[i] if prev else 0)) for i in range(5))
            by[r['d0'][:4]] = by.get(r['d0'][:4], 0) + math.log1p(sum(w[i] * r['legs'][i] for i in range(5)) - cost); prev = w
        return by
    def mkr(kind):
        def f(r):
            m, fs = r['state'], r['fast']
            if kind in ('R2b', 'both') and m in 'BC' and fs in 'AB': w = W['A']
            elif kind in ('R4', 'both') and m == 'F' and fs in UP: w = W['C']
            else: w = W[m]
            return RF.vt(w, r['vol'])
        return f
    ra = real_by(mkr('live')); rb = real_by(mkr('both'))
    for y in sorted(ra): print(f"  {y} live {math.expm1(ra[y])*100:+6.1f}%  both {math.expm1(rb[y])*100:+6.1f}%  diff {(rb[y]-ra[y])*100:+5.1f}pp")

    print("\nS4 max-stat permutation (200 shuffles, best over the 9-window grid)")
    rng = random.Random(11)
    real_best = -9
    for s, l in grid:
        fs = dict(zip(ds, compute_states(ds, px, short_n=s, long_n=l)))
        for r in rows: r['f2'] = fs[r['d']]
        _, sh, _ = annual_stats(run(rows, mk('both', 'f2'))[0]); real_best = max(real_best, sh - base['sharpe'])
    bc = [i for i, r in enumerate(rows) if r['state'] in 'BC']; fi = [i for i, r in enumerate(rows) if r['state'] == 'F']
    counts = []
    for s, l in grid:
        fs = dict(zip(ds, compute_states(ds, px, short_n=s, long_n=l)))
        counts.append((sum(1 for i in bc if fs[rows[i]['d']] in 'AB'), sum(1 for i in fi if fs[rows[i]['d']] in UP)))
    beats = 0; N = 200
    for _ in range(N):
        best = -9; rng.shuffle(bc); rng.shuffle(fi)
        for nb, nf in counts:
            fb, ff = set(bc[:nb]), set(fi[:nf])
            for i, r in enumerate(rows): r['f2'] = 'A' if i in fb or i in ff else 'F'
            _, sh, _ = annual_stats(run(rows, mk('both', 'f2'))[0]); best = max(best, sh - base['sharpe'])
        beats += best >= real_best
    print(f"  real best Sharpe gain {real_best:+.3f}; shuffled >= real in {beats}/{N} -> p = {beats/N:.2f}")

if __name__ == '__main__':
    main()
