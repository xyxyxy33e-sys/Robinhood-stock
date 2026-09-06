"""Owner's six-test research plan (2026-09-06 evening). Four were already
answered this session; this script runs the parts that were not:
  T2  asymmetric vol control -- cut fast, restore slowly (ratchet: the
      multiplier may fall to its new value at once but rise by at most
      `step` per day; and a two-window variant: use 10d vol to cut, 60d to
      restore)
  T3  staged re-entry -- on any move to a HIGHER-exposure row, ramp the
      weights in over N trading days instead of all at once
  T4  trim when QQQ is extended above its 200d -- A & gap200 > X -> risky x f
  T6  execution -- one extra day of signal lag; 2x the cost model
Everything on the 26y proxy with both eras, real SPMO-era weekly where the
harness allows. Baseline = the live design (with the 20/100 overlay).
"""
import sys
sys.path.insert(0, 'paper-track')
from improvement_search import build, data, evaluate, era, header, show, vt, run, SEARCH, HOLDOUT
from downturn_review import enrich
from state import TARGET_WEIGHTS, compute_fast_states, effective_state, VOL_TARGET_PA, sma
from drift_band_test import annual_stats, ONE_WAY_SPREAD
import return_frontier as RF
W = TARGET_WEIGHTS


def live_w(r):
    return W[effective_state(r['state'], r['fast'])]


def live(r):
    return vt(live_w(r), r['vol'])


def run_path(rows, wfn, band=0.03, cost=ONE_WAY_SPREAD, lag=0, ramp=None, ratchet=None, volkeys=None):
    """Generic runner: optional extra lag (use weights from `lag` rows earlier),
    ramp (days to phase in an exposure INCREASE), ratchet (max daily rise of
    the vol multiplier), volkeys=(cut_key, restore_key) two-window control."""
    held = None; rets = []; targets = []
    mult_prev = 1.0
    ramp_from = None; ramp_left = 0
    for i, r in enumerate(rows):
        src = rows[max(0, i - lag)]
        w = live_w(src)
        # vol multiplier
        if volkeys:
            vc, vr = src[volkeys[0]], src[volkeys[1]]
            m_cut = 1.0 if not vc else min(1.0, VOL_TARGET_PA / vc)
            m_res = 1.0 if not vr else min(1.0, VOL_TARGET_PA / vr)
            m = min(m_cut, mult_prev) if m_cut < mult_prev else min(m_res, 1.0)
            if m_cut < m: m = m_cut
        else:
            v = src['vol']; m = 1.0 if not v else min(1.0, VOL_TARGET_PA / v)
        if ratchet is not None and m > mult_prev:
            m = min(m, mult_prev + ratchet)
        mult_prev = m
        risky = sum(w[:4]); t = [x * m for x in w[:4]] + [1 - risky * m]
        # staged re-entry
        if ramp:
            if held is not None and sum(t[:4]) > sum(held[:4]) + 0.05 and ramp_left == 0:
                ramp_from = list(held); ramp_left = ramp
            if ramp_left > 0:
                f = 1 - (ramp_left - 1) / ramp
                t = [ramp_from[j] + (t[j] - ramp_from[j]) * f for j in range(5)]
                ramp_left -= 1
        c = 0.0
        if held is None:
            held = list(t)
        else:
            drift = sum(abs(t[j] - held[j]) for j in range(5))
            if drift > band or ramp_left > 0:
                c = cost * drift; held = list(t)
        g = sum(held[j] * r['legs'][j] for j in range(5))
        rets.append(g - c)
        dn = 1 + g
        if dn > 0: held = [held[j] * (1 + r['legs'][j]) / dn for j in range(5)]
    return rets


def ev(rows, **kw):
    f = run_path(rows, live, **kw); c, s, m = annual_stats(f)
    _, ss, _ = annual_stats(run_path(era(rows, *SEARCH), live, **kw))
    _, hs, _ = annual_stats(run_path(era(rows, *HOLDOUT), live, **kw))
    return dict(cagr=c, sharpe=s, mdd=m, risky=0, s_sharpe=ss, h_sharpe=hs)


def main():
    rows = enrich(build()); D = data(); fast = compute_fast_states(D['ds'], D['qqq'])
    for r in rows: r['fast'] = fast[r['d']]
    base = ev(rows)
    header(); show('LIVE (6 Sep design)', base)

    print("\nT2 asymmetric vol control: cut at once, restore slowly")
    for step in (0.02, 0.05, 0.10):
        show(f"ratchet: multiplier rises <= {step:.2f}/day", ev(rows, ratchet=step), base)
    show("two-window: 10d vol to cut, 60d to restore", ev(rows, volkeys=('vol10', 'vol60')), base)
    show("two-window: 10d vol to cut, 30d to restore", ev(rows, volkeys=('vol10', 'vol')), base)

    print("\nT3 staged re-entry: phase an exposure increase in over N days")
    for n in (3, 5, 10, 20):
        show(f"ramp exposure increases over {n}d", ev(rows, ramp=n), base)

    print("\nT4 trim when extended: A & price > X above 200d -> risky x f")
    v = [D['qqq'][d] for d in D['ds']]; ix = {d: i for i, d in enumerate(D['ds'])}
    for r in rows: r['gap200'] = v[ix[r['d']]] / sma(v, ix[r['d']], 200) - 1
    for X in (0.10, 0.15, 0.20, 0.25):
        for f in (0.5, 0.75):
            n = sum(1 for r in rows if effective_state(r['state'], r['fast']) == 'A' and r['gap200'] > X)
            def fn(r, X=X, f=f):
                w = live_w(r)
                if effective_state(r['state'], r['fast']) == 'A' and r['gap200'] > X:
                    w = tuple(x * f for x in w[:4]) + (1 - f * sum(w[:4]),)
                return vt(w, r['vol'])
            show(f"A & gap200>{X*100:.0f}% -> x{f} ({n} d)", evaluate(rows, fn), base)

    print("\nT6 execution: extra signal lag, higher cost")
    show("lag +1 day (act on yesterday's reading)", ev(rows, lag=1), base)
    show("lag +2 days", ev(rows, lag=2), base)
    show("cost 8 bps one-way (2x)", ev(rows, cost=2 * ONE_WAY_SPREAD), base)
    show("cost 20 bps one-way (5x)", ev(rows, cost=5 * ONE_WAY_SPREAD), base)


if __name__ == '__main__':
    main()
