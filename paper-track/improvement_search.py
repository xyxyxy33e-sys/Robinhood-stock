"""Systematic improvement search on the full 2000-2026 history, prompted by the
by-year tables of 2026-09-02: the strategy's losses to QQQ cluster in sharp
recovery years (2003/2009/2020/2023 -- slow re-entry after a bottom) and in
one whipsaw year (2011), and EVERY per-state weight was fit on the 2015+
window that just proved misleading for state F.

Each test changes ONE thing against the current live design and reports
full-period CAGR / Sharpe / MaxDD plus Sharpe in both eras (searched 2015-11+,
clean holdout 2000-2015). A candidate is only worth a second look if it
improves BOTH eras; a Pareto win on CAGR+Sharpe+MaxDD is the bar the F change
cleared. Exposure-matched controls are run on anything that survives.

Tests:
  T1  per-state weights re-swept on full history, one state at a time
  T2  hysteresis buffer (2011 whipsaw)
  T3  micro overlay on/off (fit on 2015+, never checked on 2000-2015)
  T4  vol-targeting variants: downside semi-vol, EWMA, blended lookbacks
      (2020: vol stayed high while the market ripped, so we sat in cash)
  T5  state C with leverage (re-entry: C is the first state after a bottom)
"""
import math
import sys

sys.path.insert(0, 'paper-track')
import state as ST
from state import (compute_states, sma, realized_vol, TARGET_WEIGHTS,
                   MICRO_OVERLAY_WEIGHTS, VOL_TARGET_PA, VOL_LOOKBACK_DAYS,
                   MICRO_SHORT_N, MICRO_LONG_N)
from long_history_backtest import (load_px, load_tbill_long, make_rate_lookup,
                                   synth_leveraged, total_return_index, cash_index,
                                   START, QQQ_DIV_PA, XLU_DIV_PA)
from drift_band_test import annual_stats, ONE_WAY_SPREAD

BAND = 0.03
SEARCH = ('2015-11-01', '2099')
HOLDOUT = (START, '2015-10-31')

_DATA = {}


def data():
    if not _DATA:
        rate_on = make_rate_lookup(load_tbill_long())
        qqq = load_px('data/qqq_long_history.csv')
        xlu = load_px('data/xlu_long_history.csv')
        common = set(qqq) & set(xlu)
        qqq = {d: v for d, v in qqq.items() if d in common}
        xlu = {d: v for d, v in xlu.items() if d in common}
        ds = sorted(qqq)
        _DATA.update(dict(
            ds=ds, qqq=qqq, rate_on=rate_on,
            core=total_return_index(qqq, QQQ_DIV_PA),
            lev2=synth_leveraged(qqq, 2, 0.95, rate_on),
            lev3=synth_leveraged(qqq, 3, 0.84, rate_on),
            xl=total_return_index(xlu, XLU_DIV_PA),
            cash=cash_index(ds, rate_on),
        ))
    return _DATA


def build(buf=0.01, micro_buf=0.01):
    D = data()
    ds, px = D['ds'], D['qqq']
    states = compute_states(ds, px, buf=buf)
    micro_states = compute_states(ds, px, buf=micro_buf, short_n=MICRO_SHORT_N, long_n=MICRO_LONG_N)
    v = [px[d] for d in ds]
    rets = [None] + [v[i] / v[i - 1] - 1 for i in range(1, len(v))]
    rows = []
    for i in range(1, len(ds)):
        d0, d1 = ds[i - 1], ds[i]
        if d0 < START or sma(v, i - 1, 200) is None:
            continue
        j = i - 1
        r30 = [x for x in rets[j - 29:j + 1] if x is not None]
        r10 = [x for x in rets[j - 9:j + 1] if x is not None]
        r60 = [x for x in rets[j - 59:j + 1] if x is not None]
        rows.append(dict(
            d=d0, state=states[j], agree=micro_states[j] in ('A', 'B'),
            vol=_vol(r30), vol10=_vol(r10), vol60=_vol(r60),
            semivol=_semivol(r30), ewma=None,
            legs=(D['core'][d1] / D['core'][d0] - 1, D['lev3'][d1] / D['lev3'][d0] - 1,
                  D['lev2'][d1] / D['lev2'][d0] - 1, D['xl'][d1] / D['xl'][d0] - 1,
                  D['cash'][d1] / D['cash'][d0] - 1),
        ))
    # EWMA vol (RiskMetrics-style, lambda 0.94 ~ 16-day half-life... use 0.97 ~ 23d)
    lam = 0.97
    var = None
    ret_by_d = dict(zip(ds, rets))
    for r in rows:
        x = ret_by_d[r['d']] or 0.0
        var = x * x if var is None else lam * var + (1 - lam) * x * x
        r['ewma'] = math.sqrt(var * 252)
    return rows


def _vol(r):
    if len(r) < 2:
        return None
    m = sum(r) / len(r)
    return (sum((x - m) ** 2 for x in r) / (len(r) - 1)) ** 0.5 * math.sqrt(252)


def _semivol(r):
    """Downside semi-deviation, annualised, scaled so a symmetric series gives
    the same number as _vol (multiply by sqrt(2))."""
    if len(r) < 2:
        return None
    neg = [min(x, 0.0) ** 2 for x in r]
    return (sum(neg) / (len(r) - 1)) ** 0.5 * math.sqrt(252) * math.sqrt(2)


def vt(weights, vol, target=VOL_TARGET_PA):
    m = 1.0 if not vol else min(1.0, target / vol)
    risky = sum(weights[:4])
    return tuple(w * m for w in weights[:4]) + (1.0 - risky * m,)


def live_base(r, weights=None, micro=True):
    W = weights or TARGET_WEIGHTS
    if micro:
        return MICRO_OVERLAY_WEIGHTS.get((r['state'], r['agree']), W[r['state']])
    return W[r['state']]


def run(rows, wfn, band=BAND):
    held = prev = None
    rets, risky = [], 0.0
    for r in rows:
        t = wfn(r)
        key = (r['state'], r['agree'])
        cost = 0.0
        if held is None:
            held = list(t)
        else:
            drift = sum(abs(t[j] - held[j]) for j in range(5))
            if key != prev or drift > band:
                cost = ONE_WAY_SPREAD * drift
                held = list(t)
        risky += sum(held[:4])
        g = sum(held[j] * r['legs'][j] for j in range(5))
        rets.append(g - cost)
        dn = 1 + g
        if dn > 0:
            held = [held[j] * (1 + r['legs'][j]) / dn for j in range(5)]
        prev = key
    return rets, risky / len(rows)


def era(rows, lo, hi):
    return [r for r in rows if lo <= r['d'] <= hi]


def evaluate(rows, wfn):
    f, e = run(rows, wfn)
    c, s, m = annual_stats(f)
    _, ss, _ = annual_stats(run(era(rows, *SEARCH), wfn)[0])
    _, hs, _ = annual_stats(run(era(rows, *HOLDOUT), wfn)[0])
    return dict(cagr=c, sharpe=s, mdd=m, risky=e, s_sharpe=ss, h_sharpe=hs)


def header():
    print(f"{'candidate':<38}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>8}{'risky':>7}{'  S':>8}{'H':>7}{'  both?':>8}")


def show(label, ev, base=None):
    both = ''
    if base:
        both = 'YES' if ev['s_sharpe'] > base['s_sharpe'] and ev['h_sharpe'] > base['h_sharpe'] else ''
        pareto = (ev['cagr'] > base['cagr'] and ev['sharpe'] > base['sharpe'] and ev['mdd'] > base['mdd'])
        both = both + (' PARETO' if pareto else '')
    print(f"{label:<38}{ev['cagr']*100:>7.2f}%{ev['sharpe']:>8.3f}{ev['mdd']*100:>7.1f}%"
          f"{ev['risky']*100:>6.1f}%{ev['s_sharpe']:>8.3f}{ev['h_sharpe']:>7.3f}{both:>8}")


def main():
    rows = build()
    live = lambda r: vt(live_base(r), r['vol'])
    base = evaluate(rows, live)
    print(f"{len(rows)} days {rows[0]['d']}..{rows[-1]['d']}; S = Sharpe 2015-11+, H = Sharpe 2000-2015\n")
    header()
    show('LIVE (current design)', base)

    # ---------------- T1: per-state weight re-sweep on full history
    print("\n=== T1: per-state weights, one state at a time (full history) ===")
    sweeps = {
        'A': [(c, 1 - c, 0, 0, 0) for c in (1.0, 0.9, 0.8, 0.7, 0.6)],
        'B': [(1 - t, t, 0, 0, 0) for t in (0.25, 0.5, 0.75, 1.0)] + [(0, 0, 1, 0, 0)],
        'C': [(1, 0, 0, 0, 0), (0.8, 0, 0.2, 0, 0), (0.6, 0, 0.4, 0, 0), (0.8, 0.2, 0, 0, 0), (0.7, 0, 0, 0, 0.3)],
        'D': [(0, 0, q, 0, 1 - q) for q in (0.7, 0.85, 1.0)] + [(0.7, 0, 0, 0, 0.3), (1, 0, 0, 0, 0)],
        'E': [(0, 0, 0, x, 1 - x) for x in (0.5, 0.25, 0.0)] + [(0.5, 0, 0, 0, 0.5), (0.3, 0, 0, 0.3, 0.4)],
    }
    for st, opts in sweeps.items():
        header()
        for w in opts:
            W = dict(TARGET_WEIGHTS)
            W[st] = w
            micro = (st not in ('A', 'D'))   # overlay rows hard-code A/D; drop them when resweeping those
            ev = evaluate(rows, lambda r, W=W, micro=micro: vt(live_base(r, W, micro), r['vol']))
            tag = ' (live)' if w == TARGET_WEIGHTS[st] else ''
            show(f"{st}={tuple(round(x, 2) for x in w)}{tag}{'' if micro else ' [no micro]'}", ev, base)

    # ---------------- T2: hysteresis
    print("\n=== T2: hysteresis buffer (live 1%) ===")
    header()
    for buf in (0.005, 0.01, 0.02, 0.03, 0.05):
        rb = build(buf=buf)
        ev = evaluate(rb, live)
        show(f"buf={buf*100:.1f}%", ev, base)

    # ---------------- T3: micro overlay
    print("\n=== T3: micro overlay ===")
    header()
    show('micro ON (live)', base)
    show('micro OFF', evaluate(rows, lambda r: vt(live_base(r, micro=False), r['vol'])), base)

    # ---------------- T4: vol measure variants
    print("\n=== T4: vol-targeting variants (target 20%) ===")
    header()
    show('30d realised (live)', base)
    show('downside semi-vol 30d', evaluate(rows, lambda r: vt(live_base(r), r['semivol'])), base)
    show('EWMA lam=0.97', evaluate(rows, lambda r: vt(live_base(r), r['ewma'])), base)
    show('max(10d,30d) fast down/slow up', evaluate(rows, lambda r: vt(live_base(r), max(r['vol10'] or 0, r['vol'] or 0))), base)
    show('min(30d,60d) slow down/fast up', evaluate(rows, lambda r: vt(live_base(r), min(r['vol'] or 9, r['vol60'] or 9))), base)
    show('mean(10d,30d)', evaluate(rows, lambda r: vt(live_base(r), ((r['vol10'] or 0) + (r['vol'] or 0)) / 2)), base)
    # semivol at other targets, since its scale differs
    for tg in (0.16, 0.18, 0.22):
        show(f'semi-vol 30d, target {tg*100:.0f}%', evaluate(rows, lambda r, tg=tg: vt(live_base(r), r['semivol'], tg)), base)

    # ---------------- T5: vol-target exemption by state (re-entry)
    print("\n=== T5: vol targeting exempt in re-entry states ===")
    header()
    for ex in (('B',), ('C',), ('B', 'C')):
        def wf(r, ex=ex):
            w = live_base(r)
            return w if r['state'] in ex else vt(w, r['vol'])
        show(f"no vol-target in {'+'.join(ex)}", evaluate(rows, wf), base)


if __name__ == '__main__':
    main()
