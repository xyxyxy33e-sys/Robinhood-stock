"""Re-run the per-state single-parameter grid search (same methodology as
four_leg_overlay.py / five_leg_xlu_search.py: vary ONE state's own
(core, tqqq, qld, xlu, cash) weights at a time against the live baseline for
every OTHER state, search period pre-2020-01-01, full-timeline + holdout
Sharpe check) now that "core" means the live 75/25 SPMO/GLD blend
(CORE_SPMO_FRAC/CORE_GLD_FRAC in state.py) instead of pure SPMO -- the
original per-state weights were all chosen against a pure-SPMO core, so this
checks whether any of them shifted now that the core itself changed.

RESULTS SUMMARY: see bottom of file after first execution.
"""
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import STATE_LABEL, compute_states, TARGET_WEIGHTS, CORE_SPMO_FRAC, CORE_GLD_FRAC
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
from four_leg_overlay import last_trading_day_per_week

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
CANDIDATES_DIR = 'data/defensive_candidates'
SEARCH_HOLDOUT_SPLIT = '2020-01-01'
STEP = 0.1

BASELINE = TARGET_WEIGHTS  # live (core, tqqq, qld, xlu, cash) per state


def build_weekly_series():
    qqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    spmo = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPMO.csv')
    tqqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/TQQQ.csv')
    qld = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QLD.csv')
    xlu = load_daily_csv(f'{ROBINHOOD_REPO}/etf/XLU.csv')
    gld = load_daily_csv(f'{CANDIDATES_DIR}/GLD.csv')
    boxx = load_daily_csv(f'{ROBINHOOD_REPO}/etf/BOXX.csv')
    tbill = load_tbill()
    all_dates = sorted(set(qqq) | set(tqqq) | set(spmo) | set(qld) | set(xlu) | set(gld))
    cash_idx = build_cash_index(all_dates, boxx, tbill)

    qqq_dates = sorted(qqq)
    states = compute_states(qqq_dates, qqq)
    state_by_date = dict(zip(qqq_dates, states))

    spmo_wk = last_trading_day_per_week(sorted(set(spmo)))
    tqqq_wk = last_trading_day_per_week(sorted(set(tqqq)))
    qld_wk = last_trading_day_per_week(sorted(set(qld)))
    xlu_wk = last_trading_day_per_week(sorted(set(xlu)))
    gld_wk = last_trading_day_per_week(sorted(set(gld)))
    cash_wk = last_trading_day_per_week(sorted(set(cash_idx)))
    keys = sorted(set(spmo_wk) & set(tqqq_wk) & set(qld_wk) & set(xlu_wk) & set(gld_wk) & set(cash_wk))
    keys = [k for k in keys if spmo_wk[k] >= '2015-11-02']

    rows = []
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        w0, w1 = spmo_wk[k0], spmo_wk[k1]
        t0, t1 = tqqq_wk[k0], tqqq_wk[k1]
        q0, q1 = qld_wk[k0], qld_wk[k1]
        x0, x1 = xlu_wk[k0], xlu_wk[k1]
        g0, g1 = gld_wk[k0], gld_wk[k1]
        c0, c1 = cash_wk[k0], cash_wk[k1]
        sd = w0
        while sd not in state_by_date and sd > qqq_dates[0]:
            sd = (date.fromisoformat(sd) - timedelta(days=1)).isoformat()
        st = state_by_date.get(sd)
        if st is None:
            continue
        r_spmo = spmo[w1] / spmo[w0] - 1
        r_gld = gld[g1] / gld[g0] - 1
        r_core = CORE_SPMO_FRAC * r_spmo + CORE_GLD_FRAC * r_gld
        r_tqqq = tqqq[t1] / tqqq[t0] - 1
        r_qld = qld[q1] / qld[q0] - 1
        r_xlu = xlu[x1] / xlu[x0] - 1
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
    for _, st, rc, rt, rq, rx, rca in rows:
        cw, tw, qw, xw, chw = weights_by_state[st]
        out.append(cw * rc + tw * rt + qw * rq + xw * rx + chw * rca)
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
    baseline_full = sharpe(full_series_rets(rows, BASELINE))
    search_rows = [r for r in rows if r[0] < SEARCH_HOLDOUT_SPLIT]
    holdout_rows = [r for r in rows if r[0] >= SEARCH_HOLDOUT_SPLIT]
    print(f"Live baseline (with 75/25 SPMO/GLD core) full-timeline Sharpe: {baseline_full:.3f}")
    print(f"{'St':<3}{'Label':<22}{'n':>4}  {'Live (c/t/q/x/ch)':<28}{'Search-best (c/t/q/x/ch)':<28}{'full Sh':>8}{'d':>8}{'holdout Sh':>11}  flag")
    by_state = {}
    for r in rows:
        by_state.setdefault(r[1], []).append(r)
    for st in sorted(by_state):
        best = grid_search_one_state(search_rows, st, step=STEP)
        weights_at_best = dict(BASELINE)
        weights_at_best[st] = best[:5]
        full_sh = sharpe(full_series_rets(rows, weights_at_best))
        holdout_sh = sharpe(full_series_rets(holdout_rows, weights_at_best))
        delta = full_sh - baseline_full
        flag = 'MOVED' if best[:5] != BASELINE[st] and delta > 0.005 else 'unchanged/no-gain'
        live_str = "/".join(f"{w:.2f}" for w in BASELINE[st])
        best_str = "/".join(f"{w:.2f}" for w in best[:5])
        print(f"{st:<3}{STATE_LABEL[st]:<22}{len(by_state[st]):>4}  {live_str:<28}{best_str:<28}{full_sh:>8.3f}{delta:>+8.3f}{holdout_sh:>11.3f}  {flag}")


if __name__ == '__main__':
    main()
