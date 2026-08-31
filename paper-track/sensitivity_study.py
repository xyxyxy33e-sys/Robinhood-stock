"""Sensitivity study on the live TARGET_WEIGHTS (core=SPMO ETF, TQQQ, QLD, cash),
per state, finer grid (0.05 step) than four_leg_overlay.py's 0.1. Reports not just
the argmax but the shape of the Sharpe surface around it -- how many grid points
land within a small tolerance of the peak (a broad plateau means the current
weight is robust to being slightly off; a narrow peak means it's fragile) -- and
the Sharpe cost of moving 10 percentage points off the live weight in each
direction, to see how much the live choice actually matters vs. how much is
inside the noise floor.

One state varied at a time against the (now-live, post-QLD, post-SPMO-swap)
baseline, full-timeline Sharpe, search period pre-2020-01-01 for the argmax,
holdout (2020+) to confirm. Same methodology as four_leg_overlay.py and
optimize_top1_states.py -- see those files for why (avoids the degenerate
100%-cash corner solution from isolating a single state's own weeks).
"""
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import STATE_LABEL, compute_states
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
SEARCH_HOLDOUT_SPLIT = '2020-01-01'
STEP = 0.05
PLATEAU_TOL = 0.01  # Sharpe units

LIVE_WEIGHTS = {
    'A': (0.80, 0.20, 0.00, 0.00),
    'B': (0.25, 0.75, 0.00, 0.00),
    'C': (1.00, 0.00, 0.00, 0.00),
    'D': (0.00, 0.00, 0.70, 0.30),
    'E': (0.50, 0.00, 0.00, 0.50),
    'F': (0.30, 0.00, 0.00, 0.70),
}


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

    spmo_wk = last_trading_day_per_week(sorted(set(spmo)))
    tqqq_wk = last_trading_day_per_week(sorted(set(tqqq)))
    qld_wk = last_trading_day_per_week(sorted(set(qld)))
    cash_wk = last_trading_day_per_week(sorted(set(cash_idx)))

    keys = sorted(set(spmo_wk) & set(tqqq_wk) & set(qld_wk) & set(cash_wk))
    keys = [k for k in keys if spmo_wk[k] >= '2015-11-02']

    rows = []
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        w0, w1 = spmo_wk[k0], spmo_wk[k1]
        t0, t1 = tqqq_wk[k0], tqqq_wk[k1]
        q0, q1 = qld_wk[k0], qld_wk[k1]
        c0, c1 = cash_wk[k0], cash_wk[k1]
        sd = w0
        while sd not in state_by_date and sd > qqq_dates[0]:
            sd = (date.fromisoformat(sd) - timedelta(days=1)).isoformat()
        st = state_by_date.get(sd)
        if st is None:
            continue
        r_core = spmo[w1] / spmo[w0] - 1
        r_tqqq = tqqq[t1] / tqqq[t0] - 1
        r_qld = qld[q1] / qld[q0] - 1
        r_cash = cash_idx[c1] / cash_idx[c0] - 1
        rows.append((w1, st, r_core, r_tqqq, r_qld, r_cash))
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


def full_series_rets(rows, weights_by_state):
    out = []
    for _, st, rc, rt, rq, rca in rows:
        cw, tw, qw, chw = weights_by_state[st]
        out.append(cw * rc + tw * rt + qw * rq + chw * rca)
    return out


def grid_for_state(rows, target_state, step=STEP):
    """Returns list of (core, tqqq, qld, cash, sharpe) for every valid grid
    point, computed on the SEARCH period only (pre-2020), full weights_by_state
    holding every other state at LIVE_WEIGHTS."""
    search_rows = [r for r in rows if r[0] < SEARCH_HOLDOUT_SPLIT]
    n = round(1 / step)
    results = []
    for i in range(n + 1):
        core_w = round(i * step, 4)
        for j in range(n + 1 - i):
            tqqq_w = round(j * step, 4)
            for k in range(n + 1 - i - j):
                qld_w = round(k * step, 4)
                cash_w = round(1 - core_w - tqqq_w - qld_w, 4)
                if cash_w < -1e-9:
                    continue
                weights = dict(LIVE_WEIGHTS)
                weights[target_state] = (core_w, tqqq_w, qld_w, cash_w)
                rets = full_series_rets(search_rows, weights)
                sh = sharpe(rets)
                if sh is not None:
                    results.append((core_w, tqqq_w, qld_w, cash_w, sh))
    return results


def main():
    rows = build_weekly_series()
    holdout_rows = [r for r in rows if r[0] >= SEARCH_HOLDOUT_SPLIT]
    baseline_full = sharpe(full_series_rets(rows, LIVE_WEIGHTS))
    print(f"Live baseline (all states at current weights), full-timeline Sharpe: {baseline_full:.3f}")
    print(f"Grid step: {STEP}, plateau tolerance: {PLATEAU_TOL} Sharpe units\n")

    for st in sorted(STATE_LABEL):
        live = LIVE_WEIGHTS[st]
        grid = grid_for_state(rows, st, step=STEP)
        if not grid:
            print(f"=== {st} ({STATE_LABEL[st]}) === no valid grid points, skipped\n")
            continue
        grid.sort(key=lambda x: -x[4])
        best = grid[0]
        peak_sh = best[4]
        plateau = [g for g in grid if peak_sh - g[4] <= PLATEAU_TOL]
        plateau_frac = len(plateau) / len(grid)

        # full-timeline + holdout at the argmax weight
        weights_at_best = dict(LIVE_WEIGHTS)
        weights_at_best[st] = (best[0], best[1], best[2], best[3])
        full_at_best = sharpe(full_series_rets(rows, weights_at_best))
        holdout_at_best = sharpe(full_series_rets(holdout_rows, weights_at_best))

        # sensitivity: full-timeline Sharpe if core is nudged +/-0.10 from live
        # (satellite/cash absorbing the difference proportionally), holding
        # search-optimal composition direction fixed -- crude but illustrative
        def nudged(delta_core):
            c, t, q, ch = live
            new_c = max(0.0, min(1.0, c + delta_core))
            remainder = 1 - new_c
            old_remainder = t + q + ch
            if old_remainder <= 0:
                nt, nq, nch = 0, 0, remainder
            else:
                nt = t / old_remainder * remainder
                nq = q / old_remainder * remainder
                nch = ch / old_remainder * remainder
            w = dict(LIVE_WEIGHTS)
            w[st] = (new_c, nt, nq, nch)
            return sharpe(full_series_rets(rows, w))

        sh_minus10 = nudged(-0.10)
        sh_plus10 = nudged(0.10)

        print(f"=== {st} ({STATE_LABEL[st]}), n_weeks={sum(1 for r in rows if r[1]==st)} ===")
        print(f"  live weight (core/tqqq/qld/cash): {live}")
        print(f"  grid peak (search-period): {best[:4]}  search-Sharpe={peak_sh:.3f}")
        print(f"  at peak: full-timeline Sharpe={full_at_best:.3f} (vs baseline {baseline_full:.3f}, "
              f"delta {full_at_best-baseline_full:+.3f})  holdout-only Sharpe={holdout_at_best:.3f}")
        print(f"  plateau: {len(plateau)}/{len(grid)} grid points ({plateau_frac*100:.1f}%) within "
              f"{PLATEAU_TOL} of peak search-Sharpe -- {'BROAD (robust)' if plateau_frac>0.15 else 'NARROW (fragile)'}")
        print(f"  core weight nudged -10pp: full-timeline Sharpe={sh_minus10:.3f} "
              f"(vs live {baseline_full:.3f}, delta {sh_minus10-baseline_full:+.3f})")
        print(f"  core weight nudged +10pp: full-timeline Sharpe={sh_plus10:.3f} "
              f"(vs live {baseline_full:.3f}, delta {sh_plus10-baseline_full:+.3f})")
        print()


if __name__ == '__main__':
    main()
