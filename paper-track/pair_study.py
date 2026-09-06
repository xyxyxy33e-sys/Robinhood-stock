"""Study of the (macro, fast) state PAIR -- 2026-09-06, owner's question after
the 20/100 fast re-entry overlay went live: "every day is a letter pair, can
we study the pair?"

P1  census of all 36 (macro 50/200, fast 20/100) pairs: days, share, mean
    next-day QQQ return, t-stat, annualised, split by era
P2  one-change tests: for every pair with >= 60 days, hold a DIFFERENT
    TARGET_WEIGHTS row (A..F) on that pair's days; both-era filter
P3  max-statistic permutation: within each macro state shuffle the fast
    labels across days (counts preserved), recompute the best full-period
    Sharpe gain over ALL (pair, row) candidates -- prices the ~150 tries
The live overlay (B/C+fastAB->A, F+fastABC->C) is the baseline here.
"""
import math, random, sys
sys.path.insert(0, 'paper-track')
from improvement_search import build, data, evaluate, era, header, show, vt, run, SEARCH, HOLDOUT
from downturn_review import enrich
from state import TARGET_WEIGHTS, compute_fast_states, effective_state
from drift_band_test import annual_stats
W = TARGET_WEIGHTS


def live_fn(r):
    return vt(W[effective_state(r['state'], r['fast'])], r['vol'])


def main():
    rows = enrich(build()); D = data()
    fast = compute_fast_states(D['ds'], D['qqq'])
    for r in rows: r['fast'] = fast[r['d']]
    base = evaluate(rows, live_fn)
    header(); show('LIVE (with 20/100 overlay)', base)

    print("\nP1 pair census: macro x fast, next-day QQQ (signal-to-next-close)")
    print(f"{'pair':<6}{'days':>6}{'share':>7}{'held':>6}{'mean bp':>9}{'t':>7}{'ann':>8}   {'H days':>6}{'H bp':>7}{'S days':>6}{'S bp':>7}")
    cells = {}
    for m in 'ABCDEF':
        for f in 'ABCDEF':
            s = [r for r in rows if r['state'] == m and r['fast'] == f]
            if not s: continue
            x = [r['qqq'] for r in s]; mu = sum(x) / len(x); sd = (sum((v - mu) ** 2 for v in x) / max(1, len(x) - 1)) ** .5
            t = mu / (sd / len(x) ** .5) if len(x) > 2 else 0
            h = [r['qqq'] for r in s if r['d'] < '2015-11']; sh = [r['qqq'] for r in s if r['d'] >= '2015-11']
            hb = sum(h) / len(h) * 1e4 if h else float('nan'); sb = sum(sh) / len(sh) * 1e4 if sh else float('nan')
            cells[(m, f)] = len(s)
            print(f"{m}{f:<5}{len(s):>6}{len(s)/len(rows)*100:>6.1f}%{effective_state(m, f):>6}{mu*1e4:>+9.1f}{t:>7.2f}{(math.exp(mu*252)-1)*100:>+7.1f}%   {len(h):>6}{hb:>+7.1f}{len(sh):>6}{sb:>+7.1f}")

    print("\nP2 one-change tests (pairs with >= 60 days; hold row X on that pair's days)")
    header(); show('LIVE', base)
    cands = []
    for (m, f), n in sorted(cells.items()):
        if n < 60: continue
        cur = effective_state(m, f)
        for row in 'ABCDEF':
            if row == cur: continue
            def fn(r, m=m, f=f, row=row):
                st = row if (r['state'] == m and r['fast'] == f) else effective_state(r['state'], r['fast'])
                return vt(W[st], r['vol'])
            ev = evaluate(rows, fn)
            both = ev['s_sharpe'] > base['s_sharpe'] and ev['h_sharpe'] > base['h_sharpe']
            cands.append(((m, f), row, ev, both, fn))
            if both:
                show(f"{m}{f} ({n}d, holds {cur}) -> {row}", ev, base)
    print(f"  tried {len(cands)}; both-era survivors {sum(1 for c in cands if c[3])}")
    real_best = max(c[2]['sharpe'] for c in cands) - base['sharpe']
    print(f"  best full-period Sharpe gain among all tries: {real_best:+.3f}")

    print("\nP3 max-stat permutation (shuffle fast labels within each macro state), 60 shuffles")
    rng = random.Random(3)
    by_macro = {m: [i for i, r in enumerate(rows) if r['state'] == m] for m in 'ABCDEF'}
    tried = [(c[0], c[1]) for c in cands]
    beats = 0; N = 60
    for _ in range(N):
        for m, idx in by_macro.items():
            labs = [rows[i]['fast'] for i in idx]; rng.shuffle(labs)
            for i, l in zip(idx, labs): rows[i]['f2'] = l
        # baseline under shuffled labels
        b0 = annual_stats(run(rows, lambda r: vt(W[effective_state(r['state'], r['f2'])], r['vol']))[0])[1]
        best = -9
        for (m, f), row in tried:
            def fn(r, m=m, f=f, row=row):
                st = row if (r['state'] == m and r['f2'] == f) else effective_state(r['state'], r['f2'])
                return vt(W[st], r['vol'])
            best = max(best, annual_stats(run(rows, fn)[0])[1] - b0)
        beats += best >= real_best
    print(f"  shuffled best >= real best in {beats}/{N} -> p = {beats/N:.2f}")


if __name__ == '__main__':
    main()
