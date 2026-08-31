"""Per-state weight optimization for core=top-1 SPMO name + TQQQ satellite +
BOXX/T-bill cash, weekly rebalanced. Same isolated-single-state methodology
used earlier in this project (each state's weeks analyzed independently,
search/holdout split at 2020-01-01, no joint optimization across states --
joint search was shown elsewhere in this project to overfit badly).
"""
import csv
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import compute_states, STATE_LABEL
from backtest_topn_weekly import load_holdings, load_prices as load_mirror_prices, holdings_for_date, top_n_weights
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
SEARCH_HOLDOUT_SPLIT = '2020-01-01'


def iso_week_key(d):
    return date.fromisoformat(d).isocalendar()[:2]


def last_trading_day_per_week(dates):
    by_week = {}
    for d in dates:
        by_week[iso_week_key(d)] = d
    return by_week


def build_weekly_series():
    periods = load_holdings()
    mirror_px = load_mirror_prices()
    qqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    tqqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/TQQQ.csv')
    spmo = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPMO.csv')
    boxx = load_daily_csv(f'{ROBINHOOD_REPO}/etf/BOXX.csv')
    tbill = load_tbill()
    all_dates = sorted(set(qqq) | set(tqqq) | set(spmo))
    cash_idx = build_cash_index(all_dates, boxx, tbill)

    qqq_dates = sorted(qqq)
    states = compute_states(qqq_dates, qqq)
    state_by_date = dict(zip(qqq_dates, states))

    core_by_week = {iso_week_key(w): w for sym in mirror_px for w in mirror_px[sym]}
    # rebuild core_by_week properly: any week present in the mirror price file
    mirror_weeks = sorted({w for sym in mirror_px for w in mirror_px[sym]})
    core_by_week = {iso_week_key(w): w for w in mirror_weeks}
    tqqq_by_week = last_trading_day_per_week(sorted(set(tqqq)))
    cash_by_week = last_trading_day_per_week(sorted(set(cash_idx)))

    common_keys = sorted(set(core_by_week) & set(tqqq_by_week) & set(cash_by_week))
    common_keys = [k for k in common_keys if core_by_week[k] >= '2015-11-02']

    rows = []  # (week_start_date_str, state, r_core, r_sat, r_cash)
    for i in range(len(common_keys) - 1):
        k0, k1 = common_keys[i], common_keys[i + 1]
        w0, w1 = core_by_week[k0], core_by_week[k1]
        d0, d1 = tqqq_by_week[k0], tqqq_by_week[k1]
        c0, c1 = cash_by_week[k0], cash_by_week[k1]

        state_day = d0
        while state_day not in state_by_date and state_day > qqq_dates[0]:
            state_day = (date.fromisoformat(state_day) - timedelta(days=1)).isoformat()
        st = state_by_date.get(state_day)
        if st is None:
            continue

        d0h = holdings_for_date(periods, date.fromisoformat(w0))
        top1 = top_n_weights(d0h, 1, 'proportional')
        (ticker,) = top1.keys()
        if w0 not in mirror_px.get(ticker, {}) or w1 not in mirror_px.get(ticker, {}):
            continue
        r_core = mirror_px[ticker][w1] / mirror_px[ticker][w0] - 1
        r_sat = tqqq[d1] / tqqq[d0] - 1
        r_cash = cash_idx[c1] / cash_idx[c0] - 1

        rows.append((w1, st, r_core, r_sat, r_cash))
    return rows


def sharpe(rets):
    if len(rets) < 4:
        return None
    mean_r = sum(rets) / len(rets)
    var = sum((r - mean_r) ** 2 for r in rets) / (len(rets) - 1)
    if var <= 0:
        return None
    vol = math.sqrt(var) * math.sqrt(52.1775)
    return (mean_r * 52.1775) / vol


LIVE_WEIGHTS = {
    'A': (0.65, 0.35, 0.00), 'B': (0.25, 0.75, 0.00), 'C': (1.00, 0.00, 0.00),
    'D': (0.55, 0.20, 0.25), 'E': (0.50, 0.00, 0.50), 'F': (0.30, 0.00, 0.70),
}


def full_series_rets(rows, weights_by_state):
    """rows must be the FULL, time-ordered series (not filtered to one state) --
    every week uses weights_by_state[that week's state], so changing one
    state's weight only affects that state's weeks but Sharpe is measured over
    the WHOLE continuous timeline, properly weighing a low-vol choice (more
    cash) against the return opportunity cost across the entire portfolio,
    not just the isolated discontiguous weeks of a single state (which
    degenerates to 100% cash trivially -- confirmed and rejected, see below)."""
    out = []
    for _, st, rc, rs, rca in rows:
        cw, sw, chw = weights_by_state[st]
        out.append(cw * rc + sw * rs + chw * rca)
    return out


def grid_search_one_state(rows, target_state, step=0.1):
    """Vary target_state's weight only, holding every other state at
    LIVE_WEIGHTS, and maximize FULL-timeline Sharpe. Returns
    (core_w, sat_w, cash_w, sharpe)."""
    best = (None, None, None, -1e9)
    n = round(1 / step)
    for i in range(n + 1):
        core_w = i * step
        for j in range(n + 1 - i):
            sat_w = j * step
            cash_w = round(1 - core_w - sat_w, 6)
            if cash_w < -1e-9:
                continue
            weights = dict(LIVE_WEIGHTS)
            weights[target_state] = (core_w, sat_w, cash_w)
            rets = full_series_rets(rows, weights)
            sh = sharpe(rets)
            if sh is not None and sh > best[3]:
                best = (round(core_w, 2), round(sat_w, 2), round(cash_w, 2), sh)
    return best


def main():
    rows = build_weekly_series()
    print(f"Total weeks: {len(rows)}")
    by_state = {}
    for r in rows:
        by_state.setdefault(r[1], []).append(r)

    search_rows_all = [r for r in rows if r[0] < SEARCH_HOLDOUT_SPLIT]
    holdout_rows_all = [r for r in rows if r[0] >= SEARCH_HOLDOUT_SPLIT]

    live_full_sharpe = sharpe(full_series_rets(rows, LIVE_WEIGHTS))
    print(f"Live weights, full-timeline Sharpe (top-1 core): {live_full_sharpe:.3f}\n")

    print(f"{'St':<3}{'label':<22}{'n':>5}  {'LiveW(c/s/$)':<16}  "
          f"{'SearchBest(c/s/$)':<20}{'SearchFullSharpe':>17}  {'HoldoutFullSharpe@best':>23}")
    for st in sorted(by_state):
        n_state = len(by_state[st])
        live_c, live_s, live_cash = LIVE_WEIGHTS[st]

        best = grid_search_one_state(search_rows_all, st, step=0.1)

        weights_at_best = dict(LIVE_WEIGHTS)
        weights_at_best[st] = (best[0], best[1], best[2])
        holdout_sh = sharpe(full_series_rets(holdout_rows_all, weights_at_best))
        full_sh_at_best = sharpe(full_series_rets(rows, weights_at_best))

        live_str = f"{live_c:.2f}/{live_s:.2f}/{live_cash:.2f}"
        best_str = f"{best[0]}/{best[1]}/{best[2]}" if best[0] is not None else "n/a"
        print(f"{st:<3}{STATE_LABEL[st]:<22}{n_state:>5}  {live_str:<16}  "
              f"{best_str:<20}{'%.3f'%best[3] if best[3] not in (None,-1e9) else 'n/a':>17}  "
              f"{'%.3f'%holdout_sh if holdout_sh is not None else 'n/a':>23}  "
              f"{'%.3f'%full_sh_at_best if full_sh_at_best is not None else 'n/a':>10} (vs live {live_full_sharpe:.3f})")


if __name__ == '__main__':
    main()
