"""Pair-specific MIX search (2026-09-06, owner: "consider the possibility to
create pair specific mix"). For each (macro, fast 20/100) pair with >= 200
days, sweep a coarse grid of weight vectors on that pair's days ONLY,
choose the best by SEARCH-era (2015-11+) Sharpe of the whole strategy, then
report what that choice does on the untouched HOLDOUT (2000-2015) and on
real SPMO-era instruments. The holdout and real numbers are never used to
choose -- that is the protocol that caught every corner solution before.
"""
import itertools, math, sys
sys.path.insert(0, 'paper-track')
from improvement_search import build, data, evaluate, era, run, vt, SEARCH, HOLDOUT, header, show
from downturn_review import enrich
from state import TARGET_WEIGHTS, compute_fast_states, effective_state, compute_states
from drift_band_test import annual_stats
import return_frontier as RF
from long_history_backtest import load_px
W = TARGET_WEIGHTS

GRID = []
for core in (0, .25, .5, .75, 1):
    for tq in (0, .25, .5):
        for qld in (0, .5, 1):
            for xlu in (0, .25, .5):
                cash = 1 - core - tq - qld - xlu
                if cash >= -1e-9: GRID.append((core, tq, qld, xlu, round(cash, 4)))


def main():
    rows = enrich(build()); D = data()
    fast = compute_fast_states(D['ds'], D['qqq'])
    for r in rows: r['fast'] = fast[r['d']]
    live = lambda r: vt(W[effective_state(r['state'], r['fast'])], r['vol'])
    base = evaluate(rows, live)
    S, H = era(rows, *SEARCH), era(rows, *HOLDOUT)
    cells = {}
    for r in rows: cells[(r['state'], r['fast'])] = cells.get((r['state'], r['fast']), 0) + 1
    big = sorted([c for c, n in cells.items() if n >= 200], key=lambda c: -cells[c])
    print(f"{len(GRID)} mixes x {len(big)} cells; choose on SEARCH Sharpe, report HOLDOUT and real\n")
    rr = RF.real_rows(); qqq = load_px('data/qqq_long_history.csv'); qd = sorted(qqq)
    g = dict(zip(qd, compute_states(qd, qqq, short_n=20, long_n=100)))
    for r in rr: r['fast'] = g[r['d0']]
    e0 = RF.eval_real(rr, lambda r: RF.vt(W[effective_state(r['state'], r['fast'])], r['vol']))
    print(f"{'cell':<5}{'days':>5}{'now':>16}   {'best mix (core,tqqq,qld,xlu,cash)':<36}{'S':>7}{'->':>4}{'H':>7}{'->':>4}{'both':>6}   real")
    print(f"{'live':<5}{'':>5}{'':>16}   {'':<36}{base['s_sharpe']:>7.3f}{'':>4}{base['h_sharpe']:>7.3f}{'':>4}{'':>6}   {e0['cagr']*100:.2f}% / {e0['sharpe']:.3f} / {e0['mdd']*100:.1f}%")
    winners = {}
    for c in big:
        cur = W[effective_state(*c)]
        def mk(w, c=c):
            return lambda r: vt(w if (r['state'], r['fast']) == c else W[effective_state(r['state'], r['fast'])], r['vol'])
        best = max(GRID, key=lambda w: annual_stats(run(S, mk(w))[0])[1])
        ss = annual_stats(run(S, mk(best))[0])[1]; hs = annual_stats(run(H, mk(best))[0])[1]
        both = ss > base['s_sharpe'] and hs > base['h_sharpe']
        e = RF.eval_real(rr, lambda r, w=best, c=c: RF.vt(w if (r['state'], r['fast']) == c else W[effective_state(r['state'], r['fast'])], r['vol']))
        print(f"{c[0]}{c[1]:<4}{cells[c]:>5}{str(tuple(cur)):>16}   {str(best):<36}{ss:>7.3f}{'':>4}{hs:>7.3f}{'':>4}{'YES' if both else '':>6}   {e['cagr']*100:.2f}% / {e['sharpe']:.3f} / {e['mdd']*100:.1f}%")
        if both: winners[c] = best
    if winners:
        print("\nall both-era winners applied together:")
        fn = lambda r: vt(winners.get((r['state'], r['fast']), W[effective_state(r['state'], r['fast'])]), r['vol'])
        header(); show('LIVE', base); show('all winners', evaluate(rows, fn), base)
        e = RF.eval_real(rr, lambda r: RF.vt(winners.get((r['state'], r['fast']), W[effective_state(r['state'], r['fast'])]), r['vol']))
        print(f"   real {e['cagr']*100:.2f}% / {e['sharpe']:.3f} / {e['mdd']*100:.1f}%  (live {e0['cagr']*100:.2f}% / {e0['sharpe']:.3f} / {e0['mdd']*100:.1f}%)")


if __name__ == '__main__':
    main()
