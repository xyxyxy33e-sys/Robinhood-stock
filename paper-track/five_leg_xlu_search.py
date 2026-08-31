"""Five-leg search: core=SPMO, TQQQ, QLD, XLU (as a standalone state-specific
leg, not blended into core), cash=BOXX/T-bill. Same methodology as
four_leg_overlay.py -- vary ONE state's (core, tqqq, qld, xlu) weights at a
time (cash implied as the remainder) against the live 4-leg baseline, search
period pre-2020-01-01, full-timeline + holdout Sharpe check, corner-solution
rejection (100% cash trivially wins Sharpe regardless of real opportunity
cost -- confirmed recurring artifact in this project, reject regardless of
the Sharpe number).
"""
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import STATE_LABEL, compute_states
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
from four_leg_overlay import last_trading_day_per_week

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
SEARCH_HOLDOUT_SPLIT = '2020-01-01'
STEP = 0.1

# (core, tqqq, qld, xlu, cash) -- live baseline, xlu=0 everywhere
BASELINE = {
    'A': (0.80, 0.20, 0.00, 0.00, 0.00),
    'B': (0.25, 0.75, 0.00, 0.00, 0.00),
    'C': (1.00, 0.00, 0.00, 0.00, 0.00),
    'D': (0.00, 0.00, 0.70, 0.00, 0.30),
    'E': (0.50, 0.00, 0.00, 0.00, 0.50),
    'F': (0.30, 0.00, 0.00, 0.00, 0.70),
}


def build_weekly_series():
    qqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    spmo = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPMO.csv')
    tqqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/TQQQ.csv')
    qld = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QLD.csv')
    xlu = load_daily_csv(f'{ROBINHOOD_REPO}/etf/XLU.csv')
    boxx = load_daily_csv(f'{ROBINHOOD_REPO}/etf/BOXX.csv')
    tbill = load_tbill()
    all_dates = sorted(set(qqq) | set(tqqq) | set(spmo) | set(qld) | set(xlu))
    cash_idx = build_cash_index(all_dates, boxx, tbill)

    qqq_dates = sorted(qqq)
    states = compute_states(qqq_dates, qqq)
    state_by_date = dict(zip(qqq_dates, states))

    spmo_wk = last_trading_day_per_week(sorted(set(spmo)))
    tqqq_wk = last_trading_day_per_week(sorted(set(tqqq)))
    qld_wk = last_trading_day_per_week(sorted(set(qld)))
    xlu_wk = last_trading_day_per_week(sorted(set(xlu)))
    cash_wk = last_trading_day_per_week(sorted(set(cash_idx)))

    keys = sorted(set(spmo_wk) & set(tqqq_wk) & set(qld_wk) & set(xlu_wk) & set(cash_wk))
    keys = [k for k in keys if spmo_wk[k] >= '2015-11-02']

    rows = []
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        w0, w1 = spmo_wk[k0], spmo_wk[k1]
        t0, t1 = tqqq_wk[k0], tqqq_wk[k1]
        q0, q1 = qld_wk[k0], qld_wk[k1]
        u0, u1 = xlu_wk[k0], xlu_wk[k1]
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
        r_xlu = xlu[u1] / xlu[u0] - 1
        r_cash = cash_idx[c1] / cash_idx[c0] - 1
        rows.append((w1, st, r_core, r_tqqq, r_qld, r_xlu, r_cash))
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
    for _, st, rc, rt, rq, ru, rca in rows:
        cw, tw, qw, uw, chw = weights_by_state[st]
        out.append(cw * rc + tw * rt + qw * rq + uw * ru + chw * rca)
    return out


def grid_search_one_state(rows, target_state, step=STEP):
    best = (None,) * 5 + (-1e9,)
    n = round(1 / step)
    for i in range(n + 1):
        core_w = round(i * step, 2)
        for j in range(n + 1 - i):
            tqqq_w = round(j * step, 2)
            for k in range(n + 1 - i - j):
                qld_w = round(k * step, 2)
                for l in range(n + 1 - i - j - k):
                    xlu_w = round(l * step, 2)
                    cash_w = round(1 - core_w - tqqq_w - qld_w - xlu_w, 6)
                    if cash_w < -1e-9:
                        continue
                    weights = dict(BASELINE)
                    weights[target_state] = (core_w, tqqq_w, qld_w, xlu_w, cash_w)
                    rets = full_series_rets(rows, weights)
                    sh = sharpe(rets)
                    if sh is not None and sh > best[5]:
                        best = (core_w, tqqq_w, qld_w, xlu_w, round(cash_w, 2), sh)
    return best


def main():
    rows = build_weekly_series()
    print(f"Total weeks: {len(rows)}")
    by_state = {}
    for r in rows:
        by_state.setdefault(r[1], []).append(r)

    baseline_full = sharpe(full_series_rets(rows, BASELINE))
    print(f"Baseline (live weights, XLU unused): full-timeline Sharpe {baseline_full:.3f}\n")

    search_rows = [r for r in rows if r[0] < SEARCH_HOLDOUT_SPLIT]
    holdout_rows = [r for r in rows if r[0] >= SEARCH_HOLDOUT_SPLIT]

    print(f"{'St':<3}{'label':<22}{'n':>5}  {'Baseline(c/t/q/u/$)':<24}  "
          f"{'SearchBest(c/t/q/u/$)':<28}{'FullSharpe@best':>16}  {'vs baseline':>12}  {'Holdout@best':>13}")
    for st in sorted(by_state):
        n_state = len(by_state[st])
        base = BASELINE[st]
        best = grid_search_one_state(search_rows, st, step=STEP)
        weights_at_best = dict(BASELINE)
        weights_at_best[st] = best[:5]
        full_sh_at_best = sharpe(full_series_rets(rows, weights_at_best))
        holdout_sh = sharpe(full_series_rets(holdout_rows, weights_at_best))

        base_str = f"{base[0]:.2f}/{base[1]:.2f}/{base[2]:.2f}/{base[3]:.2f}/{base[4]:.2f}"
        best_str = f"{best[0]}/{best[1]}/{best[2]}/{best[3]}/{best[4]}"
        delta = full_sh_at_best - baseline_full
        print(f"{st:<3}{STATE_LABEL[st]:<22}{n_state:>5}  {base_str:<24}  "
              f"{best_str:<28}{full_sh_at_best:>16.3f}  {delta:>+12.3f}  {holdout_sh:>13.3f}")


if __name__ == '__main__':
    main()
