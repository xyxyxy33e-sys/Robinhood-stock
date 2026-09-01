"""Two tests requested 2026-09-01, both run over the full 2000-2026 history
via paper-track/long_history_backtest.py's validated synthetic-leverage machinery:

TEST 1 -- VOLATILITY TARGETING. The one structurally-different defensive idea
left after this session's filter search went 0-for-6 (VIX, credit spreads,
breadth, cross-asset ETFs, DMA slope/acceleration, substate splits all failed
out-of-sample). Vol targeting scales total exposure by TRAILING REALIZED
VOLATILITY rather than by regime state, so it reacts in days rather than in
50/200-day-crossover time. That is the specific reason a 50/200 classifier
cannot see a COVID: the crash and recovery both complete before the signal
moves. Multiplier = min(cap, target_vol / realised_vol), applied to the risky
legs with the remainder going to cash. cap=1.0 means "only ever de-risk";
cap>1.0 lets it lever UP in calm markets, which is the aggressive variant.

TEST 2 -- S&P 500 CORE. The account's goal is to beat SPY and QQQ, and the
26-year run showed the edge over SPY is thin (4.51% vs 4.16% in the
out-of-sample slice). S&P 500 has liquid 2x/3x funds (SSO 2006, UPRO 2009),
so the whole design can be run on SPY instead of QQQ. S&P is less volatile
than the Nasdaq-100, and leverage decay scales with variance, so the
leveraged legs should bleed less -- the question is whether that outweighs
the Nasdaq's higher raw return.

The REGIME SIGNAL stays QQQ in the headline SPY-core variant: state.py
documents QQQ-as-signal as a validated research finding, independent of what
is being traded. An SPY-signal variant is also reported for completeness.

SYNTHETIC LEVERAGE VALIDATION (see long_history_backtest.py for the model):
  QQQ legs: TQQQ real 42.22% vs synth 42.14% (-0.08pp/yr), TE 3.3%
            QLD  real 35.01% vs synth 34.63% (-0.39pp/yr), TE 3.1%
  SPY legs: SSO  real 23.30% vs synth 24.25% (+0.96pp/yr), TE 2.5% (2016+)
            UPRO real 32.37% vs synth 31.95% (-0.42pp/yr), TE 5.6%
  NOTE the SPY-side calibration is looser than the QQQ side: SSO implies a
  ~1.4%/yr underlying-income term and UPRO ~1.8%, where the QQQ funds agreed
  on 0.6% exactly. 1.6% is used as the compromise, so treat SPY-core
  leveraged-leg returns as +/-1pp/yr uncertain. That is small relative to the
  differences being tested but is NOT zero -- do not read a sub-1pp CAGR
  difference between QQQ-core and SPY-core as real.
  Pre-2016 SSO/UPRO prices are deeply split-back-adjusted (SSO $4.65 in 2006,
  UPRO $1.20 in 2009), so one cent of rounding is 0.2-1%/day and daily
  tracking error on those eras is quantization noise, not model error --
  which is why SSO validates at TE 13.3% pre-2016 but 2.5% post-2016.
"""
import csv
import math
import sys
from datetime import date

sys.path.insert(0, 'paper-track')
from state import compute_states, compute_micro_agreement, target_weights_with_micro
from four_leg_overlay import last_trading_day_per_week
from long_history_backtest import (load_px, load_tbill_long, make_rate_lookup,
                                   synth_leveraged, total_return_index, cash_index,
                                   stats, ONE_WAY_SPREAD, START, QQQ_DIV_PA, XLU_DIV_PA)

SPY_DIV_PA = 1.8
SPY_LEV_INCOME = 1.6      # compromise between SSO's ~1.4 and UPRO's ~1.8
SSO_ER, UPRO_ER = 0.89, 0.91


def realised_vol(px, dates, idx, lookback):
    if idx < lookback:
        return None
    rets = [px[dates[i]] / px[dates[i - 1]] - 1 for i in range(idx - lookback + 1, idx + 1)]
    m = sum(rets) / len(rets)
    return (sum((r - m) ** 2 for r in rets) / (len(rets) - 1)) ** 0.5 * math.sqrt(252)


def build(core_px, core_div, lev2, lev3, signal_px, xlu_px, rate_on):
    """Weekly rows for one instrument set. signal_px drives the classifier."""
    ds = sorted(core_px)
    core = total_return_index(core_px, core_div)
    xl = total_return_index(xlu_px, XLU_DIV_PA)
    cash = cash_index(ds, rate_on)
    sdates = sorted(signal_px)
    states = dict(zip(sdates, compute_states(sdates, signal_px)))
    micro = compute_micro_agreement(sdates, signal_px)
    didx = {d: i for i, d in enumerate(ds)}

    wk = last_trading_day_per_week(ds)
    keys = sorted(wk)
    rows = []
    for i in range(len(keys) - 1):
        d0, d1 = wk[keys[i]], wk[keys[i + 1]]
        st, ag = states.get(d0), micro.get(d0)
        if st is None or ag is None or d0 < START or d0 not in didx:
            continue
        rows.append(dict(
            d0=d0, d1=d1, state=st, w=target_weights_with_micro(st, ag),
            legs=(core[d1] / core[d0] - 1, lev3[d1] / lev3[d0] - 1,
                  lev2[d1] / lev2[d0] - 1, xl[d1] / xl[d0] - 1,
                  cash[d1] / cash[d0] - 1),
            bench=core[d1] / core[d0] - 1,
            vol20=realised_vol(signal_px, sdates, sdates.index(d0), 20)
                  if d0 in signal_px else None,
            vol60=realised_vol(signal_px, sdates, sdates.index(d0), 60)
                  if d0 in signal_px else None,
        ))
    return rows


def run(rows, target_vol=None, lookback='vol60', cap=1.0):
    """target_vol=None -> plain live weights. Otherwise scale risky legs."""
    out = []
    prev = None
    for r in rows:
        w = list(r['w'])
        if target_vol is not None:
            rv = r[lookback]
            if rv and rv > 0:
                mult = min(cap, target_vol / rv)
                risky = sum(w[:4])
                w = [x * mult for x in w[:4]] + [1 - risky * mult]
        g = sum(w[j] * r['legs'][j] for j in range(5))
        t = 0.0 if prev is None else sum(abs(w[j] - prev[j]) for j in range(5))
        out.append(g - ONE_WAY_SPREAD * t)
        prev = w
    return out


def slice_rows(rows, a, b):
    return [r for r in rows if a <= r['d0'] <= b]


PERIODS = (('2000-07..2015-10 OOS', START, '2015-10-31'),
           ('2015-11..2026-08 fit', '2015-11-01', '2026-12-31'),
           ('FULL 2000..2026', START, '2026-12-31'))


def report(rows, label, configs):
    print(f"\n=== {label} ===")
    print(f"{'variant':<34}{'period':<24}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>9}")
    for nm, kw in configs:
        for pn, a, b in PERIODS:
            sub = slice_rows(rows, a, b)
            _, c, s, m = stats(run(sub, **kw))
            print(f"{nm if pn.startswith('2000') else '':<34}{pn:<24}{c*100:>7.2f}%{s:>8.3f}{m*100:>8.1f}%")
        print()


def event_table(rows, configs, events):
    print(f"{'variant':<34}" + "".join(f"{e[0]:>22}" for e in events))
    for nm, kw in configs:
        cells = []
        for _, a, b in events:
            sub = slice_rows(rows, a, b)
            if not sub:
                cells.append("n/a"); continue
            t, _, _, m = stats(run(sub, **kw))
            cells.append(f"{t*100:+.1f}% (DD {m*100:.0f}%)")
        print(f"{nm:<34}" + "".join(f"{c:>22}" for c in cells))


def main():
    rate_on = make_rate_lookup(load_tbill_long())
    qqq = load_px('data/qqq_long_history.csv')
    spy = load_px('data/spy_long_history.csv')
    xlu = load_px('data/xlu_long_history.csv')

    qqq_rows = build(qqq, QQQ_DIV_PA,
                     synth_leveraged(qqq, 2, 0.95, rate_on),
                     synth_leveraged(qqq, 3, 0.84, rate_on),
                     qqq, xlu, rate_on)
    spy_rows = build(spy, SPY_DIV_PA,
                     synth_leveraged(spy, 2, SSO_ER, rate_on, div_pa=SPY_LEV_INCOME),
                     synth_leveraged(spy, 3, UPRO_ER, rate_on, div_pa=SPY_LEV_INCOME),
                     qqq, xlu, rate_on)          # QQQ still the signal
    spy_sig_rows = build(spy, SPY_DIV_PA,
                         synth_leveraged(spy, 2, SSO_ER, rate_on, div_pa=SPY_LEV_INCOME),
                         synth_leveraged(spy, 3, UPRO_ER, rate_on, div_pa=SPY_LEV_INCOME),
                         spy, xlu, rate_on)      # SPY as signal too

    vt = [('live weights (no vol target)', {}),
          ('vol-target 15%, 60d, cap 1.0', dict(target_vol=0.15, lookback='vol60', cap=1.0)),
          ('vol-target 20%, 60d, cap 1.0', dict(target_vol=0.20, lookback='vol60', cap=1.0)),
          ('vol-target 25%, 60d, cap 1.0', dict(target_vol=0.25, lookback='vol60', cap=1.0)),
          ('vol-target 20%, 20d, cap 1.0', dict(target_vol=0.20, lookback='vol20', cap=1.0)),
          ('vol-target 20%, 60d, cap 1.5', dict(target_vol=0.20, lookback='vol60', cap=1.5))]

    print("TEST 1 -- VOLATILITY TARGETING (QQQ core, the live design)")
    report(qqq_rows, "vol targeting", vt)
    print("--- the two whipsaw failures vol targeting is meant to address ---")
    event_table(qqq_rows, vt, (('COVID 2020', '2020-02-01', '2020-04-30'),
                               ('2011 whipsaw', '2011-01-01', '2011-12-31'),
                               ('dot-com 00-02', START, '2002-12-31')))

    print("\n\nTEST 2 -- S&P 500 CORE vs NASDAQ CORE (no vol targeting)")
    print(f"{'variant':<34}{'period':<24}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>9}")
    for nm, rws in (('QQQ core (current)', qqq_rows),
                    ('SPY core, QQQ signal', spy_rows),
                    ('SPY core, SPY signal', spy_sig_rows)):
        for pn, a, b in PERIODS:
            sub = slice_rows(rws, a, b)
            _, c, s, m = stats(run(sub))
            print(f"{nm if pn.startswith('2000') else '':<34}{pn:<24}{c*100:>7.2f}%{s:>8.3f}{m*100:>8.1f}%")
        print()

    print("--- benchmarks over the same window ---")
    for nm, rws in (('QQQ buy&hold (TR)', qqq_rows), ('SPY buy&hold (TR)', spy_rows)):
        for pn, a, b in PERIODS:
            sub = slice_rows(rws, a, b)
            _, c, s, m = stats([r['bench'] for r in sub])
            print(f"{nm if pn.startswith('2000') else '':<34}{pn:<24}{c*100:>7.2f}%{s:>8.3f}{m*100:>8.1f}%")
        print()

    print("\nTEST 3 -- BOTH COMBINED (best vol target applied to each core)")
    print(f"{'variant':<34}{'period':<24}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>9}")
    for nm, rws in (('QQQ core + vol-target 20%', qqq_rows), ('SPY core + vol-target 20%', spy_rows)):
        for pn, a, b in PERIODS:
            sub = slice_rows(rws, a, b)
            _, c, s, m = stats(run(sub, target_vol=0.20, lookback='vol60', cap=1.0))
            print(f"{nm if pn.startswith('2000') else '':<34}{pn:<24}{c*100:>7.2f}%{s:>8.3f}{m*100:>8.1f}%")
        print()


if __name__ == '__main__':
    main()
