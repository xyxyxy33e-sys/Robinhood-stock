"""Round 2 of the downturn review: stress-test the one survivor of
downturn_review.py, "state D and price within X% above the 200d SMA -> cash".

The X=1%/2% rows were a both-era Pareto win that passed both controls, but
X=3% fell off a cliff (Sharpe 0.80 -> 0.65). A rule that good at 2% and that
bad at 3% is either a real threshold effect or a fit to a handful of
episodes. This script decides which:
  R1  fine sweep X = 0.25%..4% (f=0 and 0.5), with the flagged-day count
  R2  per-year gain vs live, to see whether the edge is spread out or
      concentrated in 1-2 episodes
  R3  max-statistic permutation test (as in de_substate_search.py): shuffle
      which D days are flagged, keeping the count, and compare the best gain
      across the whole X grid per shuffle against the real best
  R4  real-instrument weekly check on the SPMO era (return_frontier harness)
"""
import math
import random
import sys

sys.path.insert(0, 'paper-track')
from improvement_search import build, run, evaluate, era, header, show, vt, live_base, SEARCH, HOLDOUT
from downturn_review import enrich, live
from drift_band_test import annual_stats
from state import TARGET_WEIGHTS, sma, VOL_TARGET_PA
import return_frontier as RF
from long_history_backtest import load_px

GRID = [x / 400 for x in range(1, 17)]   # 0.25% .. 4.0%


def rule(X, f, flag_key='gap200'):
    def fn(r):
        w = live_base(r, micro=False)
        if r['state'] == 'D' and r.get('_flag', r[flag_key] < X):
            w = tuple(x * f for x in w[:4]) + (1 - f * sum(w[:4]),)
        return vt(w, r['vol'])
    return fn


def flagged_rule(f):
    def fn(r):
        w = live_base(r, micro=False)
        if r['state'] == 'D' and r['_flag']:
            w = tuple(x * f for x in w[:4]) + (1 - f * sum(w[:4]),)
        return vt(w, r['vol'])
    return fn


def by_year(rows, fn_a, fn_b):
    ra, _ = run(rows, fn_a)
    rb, _ = run(rows, fn_b)
    out = {}
    for r, a, b in zip(rows, ra, rb):
        y = r['d'][:4]
        o = out.setdefault(y, [0.0, 0.0, 0])
        o[0] += math.log1p(a); o[1] += math.log1p(b)
        o[2] += 1 if (r['state'] == 'D' and r['gap200'] < 0.02) else 0
    return out


def main():
    rows = enrich(build())
    base = evaluate(rows, live())
    print("R1: fine sweep of X (D & gap200 < X -> risky x f)")
    header(); show('LIVE', base)
    for f in (0.0, 0.5):
        for X in GRID:
            n = sum(1 for r in rows if r['state'] == 'D' and r['gap200'] < X)
            ev = evaluate(rows, rule(X, f))
            show(f"X={X*100:.2f}% f={f} ({n} d flagged)", ev, base)

    print("\nR2: per-year log-return, live vs X=2% f=0 (flagged D days per year)")
    yb = by_year(rows, live(), rule(0.02, 0.0))
    print(f"{'year':<6}{'live':>8}{'cand':>8}{'diff':>8}{'flagged':>9}")
    tot = 0
    for y in sorted(yb):
        a, b, n = yb[y]
        tot += b - a
        print(f"{y:<6}{a*100:>7.1f}%{b*100:>7.1f}%{(b-a)*100:>+7.1f}pp{n:>8}")
    print(f"total diff {tot*100:+.1f}pp")

    # what does a flagged day look like -- next-day QQQ return and vol
    fl = [r for r in rows if r['state'] == 'D' and r['gap200'] < 0.02]
    un = [r for r in rows if r['state'] == 'D' and r['gap200'] >= 0.02]
    for lab, s in (('D flagged (<2%)', fl), ('D unflagged', un)):
        m = sum(r['qqq'] for r in s) / len(s)
        print(f"  {lab}: {len(s)} days, mean next-day QQQ {m*1e4:+.1f} bp, "
              f"annualised {(math.exp(m*252)-1)*100:+.1f}%, "
              f"next state E/F share {sum(1 for r in s if r['gap200'] < 0)/len(s):.2f}")

    print("\nR3: max-statistic permutation test over the X grid (f=0), 200 shuffles")
    rng = random.Random(7)
    d_idx = [i for i, r in enumerate(rows) if r['state'] == 'D']
    real_best = max(evaluate(rows, rule(X, 0.0))['sharpe'] for X in GRID) - base['sharpe']
    counts = sorted(set(sum(1 for r in rows if r['state'] == 'D' and r['gap200'] < X) for X in GRID))
    beats = 0
    N = 200
    for k in range(N):
        best = -9
        perm = d_idx[:]
        rng.shuffle(perm)
        for c in counts:
            flags = set(perm[:c])
            for i, r in enumerate(rows):
                r['_flag'] = i in flags
            f, _ = run(rows, flagged_rule(0.0))
            _, s, _ = annual_stats(f)
            best = max(best, s - base['sharpe'])
        beats += best >= real_best
    for r in rows:
        r.pop('_flag', None)
    print(f"  real best Sharpe gain {real_best:+.3f}; shuffled best >= real in {beats}/{N} -> p = {beats/N:.2f}")

    print("\nR4: real-instrument weekly check, SPMO era 2015-11+ (return_frontier harness)")
    rr = RF.real_rows()
    qqq = load_px('data/qqq_long_history.csv')
    qd = sorted(qqq); v = [qqq[d] for d in qd]; idx = {d: i for i, d in enumerate(qd)}
    for r in rr:
        i = idx[r['d0']]
        r['gap200'] = v[i] / sma(v, i, 200) - 1
    def mk(X, f):
        def fn(r):
            w = TARGET_WEIGHTS[r['state']]
            if X is not None and r['state'] == 'D' and r['gap200'] < X:
                w = tuple(x * f for x in w[:4]) + (1 - f * sum(w[:4]),)
            return RF.vt(w, r['vol'])
        return fn
    b = RF.eval_real(rr, mk(None, 0))
    print(f"  {'live':<22} CAGR {b['cagr']*100:.2f}%  Sharpe {b['sharpe']:.3f}  MaxDD {b['mdd']*100:.1f}%")
    for X, f in ((0.01, 0), (0.02, 0), (0.02, 0.5), (0.03, 0)):
        e = RF.eval_real(rr, mk(X, f))
        n = sum(1 for r in rr if r['state'] == 'D' and r['gap200'] < X)
        print(f"  X={X*100:.0f}% f={f:<3} ({n:>3} wk) CAGR {e['cagr']*100:.2f}%  Sharpe {e['sharpe']:.3f}  MaxDD {e['mdd']*100:.1f}%")


if __name__ == '__main__':
    main()
