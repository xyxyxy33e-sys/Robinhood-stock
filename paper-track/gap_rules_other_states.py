"""Owner question 2026-09-06: the extension trim works in A -- does the same
idea (act on QQQ's distance from its 200d) help in any OTHER effective
state? Baseline = live design incl. the A trim. For each state:
  - far ABOVE the 200d  -> scale risky by f (trim, like A)
  - far BELOW the 200d  -> either scale risky by f (cut) or hold the row one
    step MORE aggressive (add: 'oversold' bounce)
Both eras on the 26y proxy, real SPMO-era weekly for anything that passes."""
import sys
sys.path.insert(0, 'paper-track')
from improvement_search import build, data, evaluate, header, show, vt
from downturn_review import enrich
from state import (TARGET_WEIGHTS, compute_fast_states, compute_gap200, compute_states,
                   effective_state, is_extended, EXTENSION_SCALE, sma)
import return_frontier as RF
from long_history_backtest import load_px
W = TARGET_WEIGHTS
UP_ROW = dict(B='A', C='A', D='A', E='D', F='C')     # one step more aggressive


def base_w(r):
    w = W[r['eff']]
    if is_extended(r['eff'], r['gap']): w = tuple(x * EXTENSION_SCALE for x in w[:4]) + (1 - EXTENSION_SCALE * sum(w[:4]),)
    return w


def main():
    rows = enrich(build()); D = data(); fast = compute_fast_states(D['ds'], D['qqq']); gap = compute_gap200(D['ds'], D['qqq'])
    for r in rows: r['eff'] = effective_state(r['state'], fast[r['d']]); r['gap'] = gap[r['d']]
    live = lambda r: vt(base_w(r), r['vol']); base = evaluate(rows, live)
    rr = RF.real_rows(); qqq = load_px('data/qqq_long_history.csv'); qd = sorted(qqq); g = dict(zip(qd, compute_states(qd, qqq, short_n=20, long_n=100))); gq = compute_gap200(qd, qqq)
    for r in rr: r['eff'] = effective_state(r['state'], g[r['d0']]); r['gap'] = gq[r['d0']]
    e0 = RF.eval_real(rr, lambda r: RF.vt(base_w(r), r['vol']))
    print(f"baseline (live incl. A trim): proxy {base['cagr']*100:.2f}/{base['sharpe']:.3f}/{base['mdd']*100:.1f} S {base['s_sharpe']:.3f} H {base['h_sharpe']:.3f}; real {e0['cagr']*100:.2f}/{e0['sharpe']:.3f}/{e0['mdd']*100:.1f}")
    # gap distribution per state
    print("\ngap200 by effective state (pct of days): p10 / median / p90")
    for st in 'ABCDEF':
        gs = sorted(r['gap'] for r in rows if r['eff'] == st)
        if gs: print(f"  {st}: n={len(gs):4d}  {gs[len(gs)//10]*100:+6.1f}% / {gs[len(gs)//2]*100:+6.1f}% / {gs[9*len(gs)//10]*100:+6.1f}%")
    survivors = []
    def test(label, fn, n):
        ev = evaluate(rows, fn); both = ev['s_sharpe'] > base['s_sharpe'] and ev['h_sharpe'] > base['h_sharpe']
        show(f"{label} ({n} d)", ev, base)
        if both: survivors.append((label, fn))
    print("\n1. trim when far ABOVE the 200d (like A)"); header()
    for st, Xs in (('B', (0.05, 0.10)), ('C', (0.0, 0.05)), ('D', (0.05, 0.10, 0.15)), ('E', (0.0,))):
        for X in Xs:
            for f in (0.5, 0.0):
                n = sum(1 for r in rows if r['eff'] == st and r['gap'] > X)
                if n < 30: continue
                def fn(r, st=st, X=X, f=f):
                    w = base_w(r)
                    if r['eff'] == st and r['gap'] > X: w = tuple(x * f for x in w[:4]) + (1 - f * sum(w[:4]),)
                    return vt(w, r['vol'])
                test(f"{st} & gap>{X*100:+.0f}% -> x{f}", fn, n)
    print("\n2. cut when far BELOW the 200d"); header()
    for st, Xs in (('B', (-0.05,)), ('C', (-0.10, -0.20)), ('D', (0.0,)), ('E', (-0.05, -0.10)), ('F', (-0.20, -0.30))):
        for X in Xs:
            n = sum(1 for r in rows if r['eff'] == st and r['gap'] < X)
            if n < 30: continue
            def fn(r, st=st, X=X):
                w = base_w(r)
                if r['eff'] == st and r['gap'] < X: w = (0, 0, 0, 0, 1)
                return vt(w, r['vol'])
            test(f"{st} & gap<{X*100:+.0f}% -> cash", fn, n)
    print("\n3. ADD when far BELOW the 200d (oversold bounce: hold the next-more-aggressive row)"); header()
    for st, Xs in (('C', (-0.10, -0.20)), ('E', (-0.05, -0.10)), ('F', (-0.15, -0.20, -0.30)), ('B', (-0.05,)), ('D', (0.0,))):
        for X in Xs:
            n = sum(1 for r in rows if r['eff'] == st and r['gap'] < X)
            if n < 30: continue
            def fn(r, st=st, X=X):
                w = base_w(r)
                if r['eff'] == st and r['gap'] < X: w = W[UP_ROW[st]]
                return vt(w, r['vol'])
            test(f"{st} & gap<{X*100:+.0f}% -> {UP_ROW[st]} row", fn, n)
    print(f"\nboth-era survivors: {len(survivors)}")
    for label, fn in survivors:
        # real check needs the same rule on rr rows: rebuild from label is messy; re-evaluate via closure defaults
        e = RF.eval_real(rr, lambda r, fn=fn: RF.vt(fn.__wrapped__(r) if hasattr(fn, '__wrapped__') else _rowweights(fn, r), r['vol']))
        print(f"  {label:<34} real {e['cagr']*100:.2f}% / {e['sharpe']:.3f} / {e['mdd']*100:.1f}%  (live {e0['cagr']*100:.2f} / {e0['sharpe']:.3f} / {e0['mdd']*100:.1f})")


def _rowweights(fn, r):
    """Recover the pre-vol weights the proxy rule would hold for a real row by
    calling it with vol=None (vt with None is identity)."""
    return fn(dict(r, vol=None))


if __name__ == '__main__':
    main()
