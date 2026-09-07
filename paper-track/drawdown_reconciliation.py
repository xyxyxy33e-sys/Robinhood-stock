"""Reconcile our proxy max drawdown against an outside replay's -39/-40%.

Added 2026-09-07. An outside review reported ~-39% to -40% "depending on the
core proxy" for a longer synthetic replay, against our -34.7%. This varies ONE
construction choice at a time through the repo's OWN engine
(improvement_search.run: 3% drift band, 4bp one-way cost, drift-and-hold), so
the numbers are comparable to every other figure in STRATEGY.md.

A first attempt reimplemented the loop standalone and produced 26.0% / -33.7%
against our standing 23.6% / -34.7% -- the difference was entirely the engine
(daily costless rebalancing vs band + cost + drift), which is exactly the kind
of construction difference this script exists to measure. Use the engine.
"""
import sys
sys.path.insert(0, 'paper-track')
import improvement_search as IS
from improvement_search import build, evaluate, vt
from downturn_review import enrich
from long_history_backtest import (load_px, total_return_index, synth_leveraged,
                                   cash_index, make_rate_lookup, load_tbill_long,
                                   QQQ_DIV_PA, XLU_DIV_PA, FINANCING_SPREAD_PA)
from state import (TARGET_WEIGHTS as W, compute_fast_states, effective_state,
                   sma, extension_scale)

SPY_DIV_PA = 1.8


def make_rows(core_px=None, core_div=QQQ_DIV_PA, spread=FINANCING_SPREAD_PA,
              er3=0.84, er2=0.95):
    """Rebuild improvement_search's cached _DATA with one construction, then
    build enriched rows through the normal path."""
    rate_on = make_rate_lookup(load_tbill_long())
    qqq = load_px('data/qqq_long_history.csv')
    xlu = load_px('data/xlu_long_history.csv')
    core_src = qqq if core_px is None else core_px
    common = set(qqq) & set(xlu) & set(core_src)
    qqq = {d: v for d, v in qqq.items() if d in common}
    xlu = {d: v for d, v in xlu.items() if d in common}
    core_src = {d: v for d, v in core_src.items() if d in common}
    ds = sorted(qqq)
    IS._DATA.clear()
    IS._DATA.update(dict(
        ds=ds, qqq=qqq, rate_on=rate_on,
        core=total_return_index(core_src, core_div),
        lev2=synth_leveraged(qqq, 2, er2, rate_on, spread_pa=spread),
        lev3=synth_leveraged(qqq, 3, er3, rate_on, spread_pa=spread),
        xl=total_return_index(xlu, XLU_DIV_PA),
        cash=cash_index(ds, rate_on),
    ))
    rows = enrich(build())
    fast = compute_fast_states(ds, qqq)
    v = [qqq[d] for d in ds]
    ix = {d: i for i, d in enumerate(ds)}
    for r in rows:
        i = ix[r['d']]
        r['eff'] = effective_state(r['state'], fast[r['d']])
        r['gaps'] = {}
        for n in (100, 150, 200):
            m = sma(v, i, n)
            r['gaps'][n] = (v[i] / m - 1) if m else 0.0
    return rows


def live_fn(r):
    w = W[r['eff']]
    f = extension_scale(r['eff'], r['gaps'])
    if f < 1:
        w = tuple(x * f for x in w[:4]) + (1 - f * sum(w[:4]),)
    return vt(w, r['vol_live'])


def sub(rows, a, b):
    return [r for r in rows if a <= r['d'] <= b]


if __name__ == '__main__':
    qqq = load_px('data/qqq_long_history.csv')
    spy = load_px('data/spy_long_history.csv')
    print(f"{'construction':<46}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>9}")
    base = make_rows()
    for lab, rows in (('OURS: QQQ core, full 2000-2026 (standing)', base),
                      ('  same, restricted to 2000-2015', sub(base, '2000-01-01', '2015-12-31'))):
        ev = evaluate(rows, live_fn) if rows is base else None
        if ev is None:
            from drift_band_test import annual_stats
            from improvement_search import run
            c, s, m = annual_stats(run(rows, live_fn)[0])
            print(f"{lab:<46}{c*100:7.2f}%{s:8.3f}{m*100:8.1f}%")
        else:
            print(f"{lab:<46}{ev['cagr']*100:7.2f}%{ev['sharpe']:8.3f}{ev['mdd']*100:8.1f}%")
    from drift_band_test import annual_stats
    from improvement_search import run
    for lab, kw in (('core swap: SPY core, full', dict(core_px=spy, core_div=SPY_DIV_PA)),
                    ('financing +100bp, QQQ core, full', dict(spread=FINANCING_SPREAD_PA + 1.0)),
                    ('financing +100bp + SPY core, full', dict(core_px=spy, core_div=SPY_DIV_PA, spread=FINANCING_SPREAD_PA + 1.0)),
                    ('heavier fees (ER 1.5/1.2) + fin +100bp, QQQ', dict(spread=FINANCING_SPREAD_PA + 1.0, er3=1.5, er2=1.2))):
        rows = make_rows(**kw)
        c, s, m = annual_stats(run(rows, live_fn)[0])
        print(f"{lab:<46}{c*100:7.2f}%{s:8.3f}{m*100:8.1f}%")
        r15 = sub(rows, '2000-01-01', '2015-12-31')
        c, s, m = annual_stats(run(r15, live_fn)[0])
        print(f"{'  same, 2000-2015 only':<46}{c*100:7.2f}%{s:8.3f}{m*100:8.1f}%")


def lagged(fn, extra=1):
    """Hold weights derived from the signal `extra` rows earlier."""
    state = {'q': []}
    def f(r):
        state['q'].append(fn(r))
        if len(state['q']) > extra + 1:
            state['q'].pop(0)
        return state['q'][0]
    return f


def no_overlays(r):
    """The same weight rows WITHOUT the fast re-entry overlay and WITHOUT the
    extension trim -- i.e. macro state only, vol targeted."""
    return vt(W[r['state']], r['vol_live'])


def no_trim(r):
    return vt(W[r['eff']], r['vol_live'])


def slow_vol(r):
    w = W[r['eff']]
    f = extension_scale(r['eff'], r['gaps'])
    if f < 1:
        w = tuple(x * f for x in w[:4]) + (1 - f * sum(w[:4]),)
    return vt(w, r['vol'])


def extra_probes():
    from drift_band_test import annual_stats
    from improvement_search import run
    rows = make_rows()
    print("\nwhat DOES move the drawdown toward -39/-40%?")
    print(f"{'variant (QQQ core, full window)':<46}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>9}")
    for lab, fn in (('live design (standing)', live_fn),
                    ('  + 1 extra session of execution lag', lagged(live_fn, 1)),
                    ('  + 2 extra sessions of lag', lagged(live_fn, 2)),
                    ('no extension trim (fast overlay kept)', no_trim),
                    ('no overlays at all (macro state + vol target)', no_overlays),
                    ('30d vol estimator instead of max(10,30)', slow_vol)):
        c, s, m = annual_stats(run(rows, fn)[0])
        print(f"{lab:<46}{c*100:7.2f}%{s:8.3f}{m*100:8.1f}%")


if __name__ == '__main__':
    extra_probes()
