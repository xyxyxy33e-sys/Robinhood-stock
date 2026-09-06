"""Round 2 of the whole-strategy review (2026-09-06). Two leads from
strategy_review.py:

  A. The 2-state collapse (A/B/C/D -> state-A weights 70/30, E/F -> cash)
     beat the live 6-state machine on both eras, Pareto. Verify: E->cash
     alone under the CURRENT design (the old E=cash rejection was under the
     pre-09-02 design), A-weight variants of the 2-state, beta-matched
     control, and a real-instrument weekly check by calendar year.
  B. After-tax: the live design realises nearly all gains short-term. Test
     the levers that change that -- lot selection (FIFO vs HIFO), drift
     band width, vol-target on/off, keeping the core through D, and the
     2-state machine (fewer full liquidations) -- all after tax, on the
     SPMO era and the 26y proxy.
"""
import math
import sys
from datetime import date

sys.path.insert(0, 'paper-track')
from improvement_search import build, evaluate, era, header, show, vt, live_base, SEARCH, BAND
from improvement_search_r2 import beta_of, beta_matched_control
from downturn_review import enrich, live
from state import TARGET_WEIGHTS, sma
from drift_band_test import ONE_WAY_SPREAD
import return_frontier as RF

ST_RATE, LT_RATE = 0.408, 0.238


def collapsed(mapping, W=None):
    W = W or TARGET_WEIGHTS
    def fn(r):
        return vt(W[mapping[r['state']]], r['vol'])
    return fn


def run_taxed(rows, wfn, band=BAND, policy='fifo', st_rate=ST_RATE, lt_rate=LT_RATE, vol=True):
    lots = {j: [] for j in range(5)}
    held = prev = None
    nav = 1.0
    st_g = lt_g = carry = tax_paid = 0.0
    year = rows[0]['d'][:4]
    n_liq = 0

    def value(j):
        return sum(l[1] for l in lots[j])

    def sell(j, amt, d):
        nonlocal st_g, lt_g
        rem = amt
        if policy == 'hifo':
            lots[j].sort(key=lambda l: -(l[0] / l[1]))       # highest basis ratio first
        elif policy == 'lifo':
            lots[j].sort(key=lambda l: l[2], reverse=True)
        while rem > 1e-12 and lots[j]:
            l = lots[j][0]
            take = min(rem, l[1]); frac = take / l[1]
            gain = take - l[0] * frac
            age = (date.fromisoformat(d) - date.fromisoformat(l[2])).days
            if age > 365: lt_g += gain
            else: st_g += gain
            l[0] -= l[0] * frac; l[1] -= take
            if l[1] <= 1e-12: lots[j].pop(0)
            rem -= take
        if policy != 'fifo':
            lots[j].sort(key=lambda l: l[2])

    for r in rows:
        d = r['d']
        if d[:4] != year:
            net = st_g + lt_g + carry
            if net <= 0:
                carry = net; tax = 0.0
            else:
                carry = 0.0
                st_t = max(0.0, st_g + min(0.0, lt_g) + min(0.0, carry))
                tax = min(net, st_t) * st_rate + max(0.0, net - st_t) * lt_rate
            if tax > 0:
                c = min(tax, value(4)); sell(4, c, d)
                if tax - c > 1e-12: sell(0, min(tax - c, value(0)), d)
                nav -= tax; tax_paid += tax
            st_g = lt_g = 0.0
            year = d[:4]
        rr = dict(r)
        if not vol: rr['vol'] = None
        t = wfn(rr)
        key = (r['state'], r['agree'])
        cost = 0.0
        if held is None:
            for j in range(5):
                if t[j] > 0: lots[j].append([t[j], t[j], d])
            held = list(t)
        else:
            cur = [value(j) for j in range(5)]; tot = sum(cur)
            drift = sum(abs(t[j] - cur[j] / tot) for j in range(5))
            if key != prev or drift > band:
                cost = ONE_WAY_SPREAD * drift
                for j in range(5):
                    if cur[j] > t[j] * tot + 1e-12: sell(j, cur[j] - t[j] * tot, d)
                for j in range(5):
                    if t[j] * tot > cur[j] + 1e-12: lots[j].append([t[j] * tot - cur[j], t[j] * tot - cur[j], d])
                held = list(t)
                if drift > 1.0: n_liq += 1
        tot = sum(value(j) for j in range(5))
        for j in range(5):
            for l in lots[j]: l[1] *= (1 + r['legs'][j]) * (1 - cost)
        nav = sum(value(j) for j in range(5))
        prev = key
    unreal = sum(l[1] - l[0] for j in range(5) for l in lots[j])
    return nav, unreal, tax_paid, carry, n_liq


def after_tax(rows, wfn, **kw):
    nav, unreal, paid, carry, nliq = run_taxed(rows, wfn, **kw)
    yrs = len(rows) / 252
    liq = nav - max(0.0, unreal + carry) * LT_RATE
    return (nav ** (1 / yrs) - 1) * 100, (liq ** (1 / yrs) - 1) * 100, nliq / yrs


def bench(rows):
    yrs = len(rows) / 252
    core = 1.0
    for r in rows: core *= 1 + r['legs'][0]
    return (core ** (1 / yrs) - 1) * 100, ((core - (core - 1) * LT_RATE) ** (1 / yrs) - 1) * 100


def main():
    rows = enrich(build())
    base = evaluate(rows, live())
    two = dict(A='A', B='A', C='A', D='A', E='F', F='F')

    print("=== A1: state collapses under the CURRENT design ===")
    header(); show('LIVE (6 states)', base)
    for lab, m in {'5-state: E->F (E = cash)': dict(A='A', B='B', C='C', D='D', E='F', F='F'),
                   '5-state: D->A (keep core in D)': dict(A='A', B='B', C='C', D='A', E='E', F='F'),
                   '5-state: C->A': dict(A='A', B='B', C='A', D='D', E='E', F='F'),
                   '4-state: C->A, D->A': dict(A='A', B='B', C='A', D='A', E='E', F='F'),
                   '3-state: BCD->A, E, F': dict(A='A', B='A', C='A', D='A', E='E', F='F'),
                   '2-state: ABCD->A, EF->cash': two}.items():
        show(lab, evaluate(rows, collapsed(m)), base)

    print("\n=== A2: 2-state with different 'on' weights ===")
    header()
    for w in ((0.8, 0.2, 0, 0, 0), (0.7, 0.3, 0, 0, 0), (0.6, 0.4, 0, 0, 0), (0.5, 0.5, 0, 0, 0),
              (0, 0, 0.85, 0, 0.15), (0, 0, 1.0, 0, 0), (0.5, 0, 0.5, 0, 0), (1, 0, 0, 0, 0)):
        W = dict(TARGET_WEIGHTS); W['A'] = w
        ev = evaluate(rows, collapsed(two, W))
        show(f"on={w}", ev, base)

    print("\n=== A3: beta-matched control for the 2-state (70/30) ===")
    fn = collapsed(two)
    ev = evaluate(rows, fn)
    tb = beta_of(rows, fn)
    k, c = beta_matched_control(rows, live(), tb)
    print(f"  2-state Sharpe {ev['sharpe']:.3f} vs live scaled to beta {tb:.2f} (k={k:.3f}) Sharpe {c['sharpe']:.3f} "
          f"-> {'PASS' if ev['sharpe'] > c['sharpe'] else 'FAIL'}")

    print("\n=== A4: real instruments, weekly, SPMO era: live vs 2-state, by calendar year ===")
    rr = RF.real_rows()
    def mk(mapping):
        def f(r):
            return RF.vt(TARGET_WEIGHTS[mapping[r['state']]], r['vol'])
        return f
    ident = dict(A='A', B='B', C='C', D='D', E='E', F='F')
    for lab, m in (('live', ident), ('2-state', two), ('5-state D->A', dict(ident, D='A')),
                   ('5-state E->F', dict(ident, E='F'))):
        e = RF.eval_real(rr, mk(m))
        print(f"  {lab:<14} CAGR {e['cagr']*100:.2f}%  Sharpe {e['sharpe']:.3f}  MaxDD {e['mdd']*100:.1f}%")
    by = {}
    for lab, m in (('live', ident), ('2-state', two)):
        f = mk(m); prev = None
        for r in rr:
            w = f(r)
            cost = RF.VL.ONE_WAY_SPREAD * sum(abs(w[i] - (prev[i] if prev else 0)) for i in range(5))
            x = sum(w[i] * r['legs'][i] for i in range(5)) - cost; prev = w
            y = r['d0'][:4]
            by.setdefault(y, {}).setdefault(lab, []).append(x)
    print(f"  {'year':<6}{'live':>9}{'2-state':>9}{'diff':>8}")
    for y in sorted(by):
        a = math.prod(1 + x for x in by[y]['live']) - 1
        b = math.prod(1 + x for x in by[y]['2-state']) - 1
        print(f"  {y:<6}{a*100:>8.1f}%{b*100:>8.1f}%{(b-a)*100:>+7.1f}")

    print("\n=== B: after-tax CAGR (annual settlement; 'liq' = then liquidate at LT) ===")
    for lab, sub in (('SPMO era 2015-11+', era(rows, *SEARCH)), ('26y proxy', rows)):
        q, ql = bench(sub)
        print(f"\n{lab}: QQQ B&H {q:.2f}% (liquidated {ql:.2f}%)")
        print(f"  {'design':<44}{'pre-tax':>8}{'after':>8}{'liq':>8}{'liq/yr':>8}")
        cands = [
            ('live, FIFO', live(), {}),
            ('live, HIFO lots', live(), dict(policy='hifo')),
            ('live, band 6%', live(), dict(band=0.06)),
            ('live, band 10%', live(), dict(band=0.10)),
            ('live, no vol target', live(), dict(vol=False)),
            ('live, no vol target, HIFO', live(), dict(vol=False, policy='hifo')),
            ('D->A (keep core in D), FIFO', collapsed(dict(A='A', B='B', C='C', D='A', E='E', F='F')), {}),
            ('2-state, FIFO', collapsed(two), {}),
            ('2-state, HIFO', collapsed(two), dict(policy='hifo')),
            ('2-state, no vol target', collapsed(two), dict(vol=False)),
            ('2-state, no vol target, HIFO', collapsed(two), dict(vol=False, policy='hifo')),
            ('2-state on=100% core, no VT, HIFO', collapsed(two, dict(TARGET_WEIGHTS, A=(1, 0, 0, 0, 0))), dict(vol=False, policy='hifo')),
        ]
        for lab2, fn, kw in cands:
            sub2 = sub
            from improvement_search import run as _run
            from drift_band_test import annual_stats as _as
            pf = (lambda r, fn=fn: fn(dict(r, vol=None))) if not kw.get('vol', True) else fn
            pre = _as(_run(sub2, pf, band=kw.get('band', BAND))[0])[0] * 100
            a, l, nl = after_tax(sub2, fn, **kw)
            print(f"  {lab2:<44}{pre:>7.2f}%{a:>7.2f}%{l:>7.2f}%{nl:>8.1f}")


if __name__ == '__main__':
    main()
