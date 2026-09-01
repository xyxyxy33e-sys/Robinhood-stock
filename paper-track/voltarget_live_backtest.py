"""Backtest the LIVE design with volatility targeting on the REAL instruments
(SPMO / TQQQ / QLD / XLU / BOXX), 2015-11 onward -- i.e. the actual thing that
will trade, not the QQQ-core long-history proxy used to validate the overlay.

Calls state.py's own target_weights_with_voltarget() and realized_vol(), so
this backtest and the live triggers cannot drift apart.

READ THIS BEFORE INTERPRETING THE NUMBERS. This window (2015-11..2026-08) is
the bull-dominated era in which every live parameter was fitted, and it
contains exactly one real bear market (2022). It is the era where volatility
targeting is EXPECTED to cost return -- its value showed up in 2000-2015,
which SPMO cannot reach. Judge the overlay on paper-track/long_history_backtest.py
and voltarget_and_sp500_test.py (2000-2026, QQQ core); use THIS file to see
what it does to the real portfolio in the recent regime, and to confirm the
live code path produces sane weights on real prices.
"""
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import (compute_states, compute_micro_agreement, realized_vol,
                   target_weights_with_micro, target_weights_with_voltarget,
                   validate_weights, VOL_TARGET_PA, VOL_LOOKBACK_DAYS)
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
from four_leg_overlay import last_trading_day_per_week
from long_history_backtest import load_px, stats

REPO = '/home/user/robinhood/data/kairos'
ONE_WAY_SPREAD = 0.0004
SPLIT = '2020-01-01'


def build():
    qqq = load_px('data/qqq_long_history.csv')      # signal + vol source
    qd = sorted(qqq)
    spmo = load_daily_csv(f'{REPO}/etf/SPMO.csv')
    tqqq = load_daily_csv(f'{REPO}/etf/TQQQ.csv')
    qld = load_daily_csv(f'{REPO}/etf/QLD.csv')
    xlu = load_daily_csv(f'{REPO}/etf/XLU.csv')
    boxx = load_daily_csv(f'{REPO}/etf/BOXX.csv')
    cash = build_cash_index(sorted(set(qd) | set(spmo) | set(tqqq) | set(qld) | set(xlu)),
                            boxx, load_tbill())
    states = dict(zip(qd, compute_states(qd, qqq)))
    micro = compute_micro_agreement(qd, qqq)

    wk = {n: last_trading_day_per_week(sorted(s)) for n, s in
          (('spmo', spmo), ('tqqq', tqqq), ('qld', qld), ('xlu', xlu),
           ('cash', cash), ('qqq', qqq))}
    keys = [k for k in sorted(set.intersection(*[set(v) for v in wk.values()]))
            if wk['spmo'][k] >= '2015-11-02']

    rows = []
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        d0 = wk['qqq'][k0]
        st, ag = states.get(d0), micro.get(d0)
        if st is None or ag is None:
            continue
        rows.append(dict(
            d0=d0, state=st, agree=ag,
            vol=realized_vol(qd, qqq, as_of=d0),
            legs=(spmo[wk['spmo'][k1]] / spmo[wk['spmo'][k0]] - 1,
                  tqqq[wk['tqqq'][k1]] / tqqq[wk['tqqq'][k0]] - 1,
                  qld[wk['qld'][k1]] / qld[wk['qld'][k0]] - 1,
                  xlu[wk['xlu'][k1]] / xlu[wk['xlu'][k0]] - 1,
                  cash[wk['cash'][k1]] / cash[wk['cash'][k0]] - 1),
            bench_spmo=spmo[wk['spmo'][k1]] / spmo[wk['spmo'][k0]] - 1,
            bench_qqq=qqq[wk['qqq'][k1]] / qqq[wk['qqq'][k0]] - 1,
        ))
    return rows


def run(rows, voltarget=True):
    out, prev, exposures, turnover = [], None, [], 0.0
    for r in rows:
        if voltarget:
            w = target_weights_with_voltarget(r['state'], r['agree'], r['vol'])
        else:
            w = target_weights_with_micro(r['state'], r['agree'])
        validate_weights(r['state'], *w)          # same guard the triggers use
        g = sum(w[j] * r['legs'][j] for j in range(5))
        t = 0.0 if prev is None else sum(abs(w[j] - prev[j]) for j in range(5))
        turnover += t
        exposures.append(w[0] + 3 * w[1] + 2 * w[2] + w[3])
        out.append(g - ONE_WAY_SPREAD * t)
        prev = w
    return out, sum(exposures) / len(exposures), turnover / (len(rows) / 52.1775)


def main():
    rows = build()
    live, live_beta, live_turn = run(rows, voltarget=False)
    vt, vt_beta, vt_turn = run(rows, voltarget=True)
    bs = [r['bench_spmo'] for r in rows]
    bq = [r['bench_qqq'] for r in rows]

    print(f"REAL instruments (SPMO core / TQQQ / QLD / XLU / BOXX), "
          f"{rows[0]['d0']}..{rows[-1]['d0']}, {len(rows)} weeks")
    print(f"vol target {VOL_TARGET_PA*100:.0f}% annualized, {VOL_LOOKBACK_DAYS}-trading-day "
          f"(~{VOL_LOOKBACK_DAYS/5:.0f} week) lookback, cap 1.0, net of 4bps turnover cost\n")

    print(f"{'':<30}{'CAGR':>9}{'Sharpe':>9}{'MaxDD':>10}{'TotalRet':>11}")
    for nm, s in (('LIVE (no vol target)', live), ('LIVE + vol target', vt),
                  ('SPMO buy & hold', bs), ('QQQ buy & hold', bq)):
        t, c, sh, m = stats(s)
        print(f"{nm:<30}{c*100:>8.2f}%{sh:>9.3f}{m*100:>9.2f}%{t*100:>10.1f}%")

    print(f"\naverage beta   live {live_beta:.2f}  ->  vol-targeted {vt_beta:.2f}")
    print(f"turnover/yr    live {live_turn:.2f}x ->  vol-targeted {vt_turn:.2f}x")

    pre = [i for i, r in enumerate(rows) if r['d0'] < SPLIT]
    post = [i for i, r in enumerate(rows) if r['d0'] >= SPLIT]
    print(f"\nsearch/holdout Sharpe (split {SPLIT}):")
    for nm, s in (('LIVE', live), ('LIVE + vol target', vt)):
        _, _, ss, _ = stats([s[i] for i in pre])
        _, _, hs, _ = stats([s[i] for i in post])
        print(f"  {nm:<20} search {ss:.3f}   holdout {hs:.3f}")

    print("\ncalendar years:")
    yrs = sorted({r['d0'][:4] for r in rows})
    print(f"{'year':<6}{'LIVE':>10}{'+voltarget':>13}{'SPMO':>10}{'QQQ':>10}")
    for y in yrs:
        idx = [i for i, r in enumerate(rows) if r['d0'][:4] == y]
        def cum(s):
            n = 1.0
            for i in idx:
                n *= (1 + s[i])
            return n - 1
        print(f"{y:<6}{cum(live)*100:>9.1f}%{cum(vt)*100:>12.1f}%"
              f"{cum(bs)*100:>9.1f}%{cum(bq)*100:>9.1f}%")

    print("\ndrawdown events:")
    for nm, a, b in (('COVID 2020-02..04', '2020-02-01', '2020-04-30'),
                     ('2022 bear', '2022-01-01', '2022-12-31'),
                     ('2025 Apr', '2025-03-01', '2025-05-31')):
        idx = [i for i, r in enumerate(rows) if a <= r['d0'] <= b]
        if not idx:
            continue
        tl, _, _, ml = stats([live[i] for i in idx])
        tv, _, _, mv = stats([vt[i] for i in idx])
        print(f"  {nm:<20} live {tl*100:>+6.1f}% (DD {ml*100:>5.1f}%)   "
              f"+voltarget {tv*100:>+6.1f}% (DD {mv*100:>5.1f}%)")

    cur = rows[-1]
    print(f"\ncurrent reading as of {cur['d0']}: state {cur['state']}, "
          f"micro_agrees={cur['agree']}, realized vol {cur['vol']*100:.1f}%")
    w_live = target_weights_with_micro(cur['state'], cur['agree'])
    w_vt = target_weights_with_voltarget(cur['state'], cur['agree'], cur['vol'])
    print(f"  weights without vol target: " + ", ".join(f"{n}={v*100:.1f}%" for n, v in
          zip(('core', 'tqqq', 'qld', 'xlu', 'cash'), w_live)))
    print(f"  weights WITH vol target   : " + ", ".join(f"{n}={v*100:.1f}%" for n, v in
          zip(('core', 'tqqq', 'qld', 'xlu', 'cash'), w_vt)))


if __name__ == '__main__':
    main()
