"""Tests blending a defensive/low-fee candidate into the SPMO core (core =
spmo_frac*SPMO + (1-spmo_frac)*candidate), same overlay methodology as
everywhere else (TQQQ/QLD satellite, BOXX/T-bill cash, current TARGET_WEIGHTS,
weekly rebalance). Reports CAGR/Sharpe/MaxDD plus the two weak calendar years
in this window (2016, 2022) at each blend fraction.

Candidates tested and verdict (2026-08-31):
  - SPY: monotonically worse on every metric, including 2016/2022 -- rejected
    outright, diversifying the core into a broader index dilutes exactly the
    momentum-tilt effect the strategy leans into.
  - XLU (utilities, ~0.08% expense ratio): the standout. Only candidate that
    makes 2016 BETTER (not worse) while giving the largest 2022 cushion of
    anything tested (-16.6% -> -13.2% at a 75/25 blend), for a modest Sharpe
    cost. A rate-sensitive, regulated-earnings sector decouples from
    tech/momentum-driven drawdowns for real structural reasons.
  - SCHD, VYM, USMV (all low-fee, 0.06-0.15%, dividend-quality/low-vol factor
    tilts): all WORSE than XLU at every blend level tested, and all make 2016
    slightly WORSE (not better) despite being "defensive"-branded products --
    they're correlated cousins of momentum within the same broad equity
    universe, not a genuinely different macro driver, so they don't decouple
    the way XLU does.

Net: XLU remains the best defensive-tilt candidate found. Not adopted live --
this is a real Sharpe-for-smoothness trade-off (a preference call), not a
free backtest win, and MaxDD does not improve even as the calendar-year
numbers do (the strategy's worst drawdown isn't driven by the core leg).
"""
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from four_leg_overlay import last_trading_day_per_week
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
from state import compute_states

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
CANDIDATES_DIR = 'data/defensive_candidates'

NEW_WEIGHTS = {
    'A': (0.80, 0.20, 0.00, 0.00), 'B': (0.25, 0.75, 0.00, 0.00), 'C': (1.00, 0.00, 0.00, 0.00),
    'D': (0.00, 0.00, 0.70, 0.30), 'E': (0.50, 0.00, 0.00, 0.50), 'F': (0.30, 0.00, 0.00, 0.70),
}

FRACTIONS = (1.0, 0.9, 0.75, 0.5, 0.25, 0.0)


def sharpe(rets):
    mean_r = sum(rets) / len(rets)
    var = sum((r - mean_r) ** 2 for r in rets) / (len(rets) - 1)
    vol = math.sqrt(var) * math.sqrt(52.1775)
    return (mean_r * 52.1775) / vol


def cagr(rets):
    nav = 1.0
    for r in rets:
        nav *= (1 + r)
    return nav ** (1 / (len(rets) / 52.1775)) - 1


def mdd(rets):
    nav = 1.0
    peak = 1.0
    m = 0.0
    for r in rets:
        nav *= (1 + r)
        peak = max(peak, nav)
        m = min(m, nav / peak - 1)
    return m


def run_blend(spmo, candidate_px, qqq, tqqq, qld, cash_idx, state_by_date, qqq_dates, spmo_frac,
              flag_years=('2016', '2022')):
    spmo_wk = last_trading_day_per_week(sorted(set(spmo)))
    cand_wk = last_trading_day_per_week(sorted(set(candidate_px)))
    tqqq_wk = last_trading_day_per_week(sorted(set(tqqq)))
    qld_wk = last_trading_day_per_week(sorted(set(qld)))
    cash_wk = last_trading_day_per_week(sorted(set(cash_idx)))
    keys = sorted(set(spmo_wk) & set(cand_wk) & set(tqqq_wk) & set(qld_wk) & set(cash_wk))
    keys = [k for k in keys if spmo_wk[k] >= '2015-11-02']

    rets = []
    year_rets = {y: [] for y in flag_years}
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        w0, w1 = spmo_wk[k0], spmo_wk[k1]
        u0, u1 = cand_wk[k0], cand_wk[k1]
        t0, t1 = tqqq_wk[k0], tqqq_wk[k1]
        q0, q1 = qld_wk[k0], qld_wk[k1]
        c0, c1 = cash_wk[k0], cash_wk[k1]
        sd = w0
        while sd not in state_by_date and sd > qqq_dates[0]:
            sd = (date.fromisoformat(sd) - timedelta(days=1)).isoformat()
        st = state_by_date.get(sd)
        if st is None:
            continue
        cw, tw, qw, chw = NEW_WEIGHTS[st]
        r_spmo = spmo[w1] / spmo[w0] - 1
        r_cand = candidate_px[u1] / candidate_px[u0] - 1
        r_core = spmo_frac * r_spmo + (1 - spmo_frac) * r_cand
        r_t = tqqq[t1] / tqqq[t0] - 1
        r_q = qld[q1] / qld[q0] - 1
        r_c = cash_idx[c1] / cash_idx[c0] - 1
        wk = cw * r_core + tw * r_t + qw * r_q + chw * r_c
        rets.append(wk)
        if w1[:4] in year_rets:
            year_rets[w1[:4]].append(wk)

    year_returns = {}
    for y, yr in year_rets.items():
        nav = 1.0
        for r in yr:
            nav *= (1 + r)
        year_returns[y] = nav - 1

    return dict(cagr=cagr(rets), sharpe=sharpe(rets), mdd=mdd(rets), year_returns=year_returns, n=len(rets))


def main():
    qqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    spmo = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPMO.csv')
    tqqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/TQQQ.csv')
    qld = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QLD.csv')
    boxx = load_daily_csv(f'{ROBINHOOD_REPO}/etf/BOXX.csv')
    tbill = load_tbill()
    xlu = load_daily_csv(f'{ROBINHOOD_REPO}/etf/XLU.csv')
    spy = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPY.csv')

    candidates = {'SPY': spy, 'XLU': xlu}
    for sym in ('SCHD', 'VYM', 'USMV'):
        candidates[sym] = load_daily_csv(f'{CANDIDATES_DIR}/{sym}.csv')

    all_dates = sorted(set(qqq) | set(tqqq) | set(spmo) | set(qld) | set().union(*[set(c) for c in candidates.values()]))
    cash_idx = build_cash_index(all_dates, boxx, tbill)
    qqq_dates = sorted(qqq)
    states = compute_states(qqq_dates, qqq)
    state_by_date = dict(zip(qqq_dates, states))

    for sym, px in candidates.items():
        print(f"--- {sym} ---")
        for frac in FRACTIONS:
            r = run_blend(spmo, px, qqq, tqqq, qld, cash_idx, state_by_date, qqq_dates, frac)
            yr = r['year_returns']
            print(f"  SPMO={frac:.2f}/{sym}={1-frac:.2f}: CAGR={r['cagr']*100:.2f}% "
                  f"Sharpe={r['sharpe']:.3f} MaxDD={r['mdd']*100:.2f}% "
                  f"2016={yr.get('2016',0)*100:.1f}% 2022={yr.get('2022',0)*100:.1f}%")
        print()


if __name__ == '__main__':
    main()
