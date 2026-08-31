"""Four-instrument overlay: SPMO core + {TQQQ, QLD} satellite (searched split,
not fixed) + BOXX/T-bill cash, weekly rebalanced, six-state regime timing.

Per-state weight search: vary ONE state's (core, tqqq, qld) weights at a time
-- cash implied as the remainder -- while holding every other state at a
baseline (TARGET_WEIGHTS from state.py, satellite weight placed 100% in
TQQQ, matching the currently-live design), and measure Sharpe over the FULL
continuous timeline. This is the same methodology validated in
optimize_top1_states.py: isolating a single state's own (discontiguous)
weeks degenerates the search to 100% cash because cash's near-zero variance
trivially wins Sharpe regardless of foregone return.

Search/holdout split at 2020-01-01, consistent with the rest of this
project's sensitivity work.
"""
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import compute_states, target_weights, STATE_LABEL
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
    qqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    spmo = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPMO.csv')
    tqqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/TQQQ.csv')
    qld = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QLD.csv')
    boxx = load_daily_csv(f'{ROBINHOOD_REPO}/etf/BOXX.csv')
    tbill = load_tbill()
    all_dates = sorted(set(qqq) | set(tqqq) | set(spmo) | set(qld))
    cash_idx = build_cash_index(all_dates, boxx, tbill)

    qqq_dates = sorted(qqq)
    states = compute_states(qqq_dates, qqq)
    state_by_date = dict(zip(qqq_dates, states))

    spmo_by_week = last_trading_day_per_week(sorted(set(spmo)))
    tqqq_by_week = last_trading_day_per_week(sorted(set(tqqq)))
    qld_by_week = last_trading_day_per_week(sorted(set(qld)))
    cash_by_week = last_trading_day_per_week(sorted(set(cash_idx)))

    common_keys = sorted(set(spmo_by_week) & set(tqqq_by_week) & set(qld_by_week) & set(cash_by_week))
    common_keys = [k for k in common_keys if spmo_by_week[k] >= '2015-11-02']

    rows = []  # (week_end_date, state, r_core, r_tqqq, r_qld, r_cash)
    for i in range(len(common_keys) - 1):
        k0, k1 = common_keys[i], common_keys[i + 1]
        d0c, d1c = spmo_by_week[k0], spmo_by_week[k1]
        d0t, d1t = tqqq_by_week[k0], tqqq_by_week[k1]
        d0q, d1q = qld_by_week[k0], qld_by_week[k1]
        c0, c1 = cash_by_week[k0], cash_by_week[k1]

        state_day = d0c
        while state_day not in state_by_date and state_day > qqq_dates[0]:
            state_day = (date.fromisoformat(state_day) - timedelta(days=1)).isoformat()
        st = state_by_date.get(state_day)
        if st is None:
            continue

        r_core = spmo[d1c] / spmo[d0c] - 1
        r_tqqq = tqqq[d1t] / tqqq[d0t] - 1
        r_qld = qld[d1q] / qld[d0q] - 1
        r_cash = cash_idx[c1] / cash_idx[c0] - 1
        rows.append((d1c, st, r_core, r_tqqq, r_qld, r_cash))
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


def cagr_of(rets):
    nav = 1.0
    for r in rets:
        nav *= (1 + r)
    years = len(rets) / 52.1775
    return nav ** (1 / years) - 1 if years > 0 else float('nan')


BASELINE = {s: (target_weights(s)[0], target_weights(s)[1], 0.0, target_weights(s)[2])
            for s in STATE_LABEL}  # (core, tqqq, qld, cash) -- satellite 100% TQQQ, matches live design


def full_series_rets(rows, weights_by_state):
    out = []
    for _, st, rc, rt, rq, rca in rows:
        cw, tw, qw, chw = weights_by_state[st]
        out.append(cw * rc + tw * rt + qw * rq + chw * rca)
    return out


def grid_search_one_state(rows, target_state, step=0.1):
    best = (None, None, None, None, -1e9)
    n = round(1 / step)
    for i in range(n + 1):
        core_w = round(i * step, 2)
        for j in range(n + 1 - i):
            tqqq_w = round(j * step, 2)
            for k in range(n + 1 - i - j):
                qld_w = round(k * step, 2)
                cash_w = round(1 - core_w - tqqq_w - qld_w, 6)
                if cash_w < -1e-9:
                    continue
                weights = dict(BASELINE)
                weights[target_state] = (core_w, tqqq_w, qld_w, cash_w)
                rets = full_series_rets(rows, weights)
                sh = sharpe(rets)
                if sh is not None and sh > best[4]:
                    best = (core_w, tqqq_w, qld_w, round(cash_w, 2), sh)
    return best


def main():
    rows = build_weekly_series()
    print(f"Total weeks: {len(rows)}")
    by_state = {}
    for r in rows:
        by_state.setdefault(r[1], []).append(r)

    baseline_full = full_series_rets(rows, BASELINE)
    baseline_sharpe = sharpe(baseline_full)
    baseline_cagr = cagr_of(baseline_full)
    print(f"Baseline (live weights, satellite=100% TQQQ, SPMO core): "
          f"Sharpe {baseline_sharpe:.3f}, CAGR {baseline_cagr*100:.2f}%\n")

    search_rows = [r for r in rows if r[0] < SEARCH_HOLDOUT_SPLIT]
    holdout_rows = [r for r in rows if r[0] >= SEARCH_HOLDOUT_SPLIT]

    print(f"{'St':<3}{'label':<22}{'n':>5}  {'Baseline(c/t/q/$)':<20}  "
          f"{'SearchBest(c/t/q/$)':<24}{'FullSharpe@best':>16}  {'vs baseline':>12}")
    for st in sorted(by_state):
        n_state = len(by_state[st])
        base_c, base_t, base_q, base_ch = BASELINE[st]
        state_search_rows = [r for r in search_rows if True]  # full search set (all states), varying only `st`

        best = grid_search_one_state(search_rows, st, step=0.1)
        weights_at_best = dict(BASELINE)
        weights_at_best[st] = (best[0], best[1], best[2], best[3])
        full_sh_at_best = sharpe(full_series_rets(rows, weights_at_best))
        holdout_sh = sharpe(full_series_rets(holdout_rows, weights_at_best))

        base_str = f"{base_c:.2f}/{base_t:.2f}/{base_q:.2f}/{base_ch:.2f}"
        best_str = f"{best[0]}/{best[1]}/{best[2]}/{best[3]}"
        delta = full_sh_at_best - baseline_sharpe
        print(f"{st:<3}{STATE_LABEL[st]:<22}{n_state:>5}  {base_str:<20}  "
              f"{best_str:<24}{full_sh_at_best:>16.3f}  {delta:>+12.3f}")
        if holdout_sh is not None:
            print(f"     (holdout-period-only Sharpe at this weight: {holdout_sh:.3f})")


if __name__ == '__main__':
    main()
