"""Isolated single-state validation for the D/E candidate legs (XLU in D,
XLU and BRK.B in E) found by five_leg_xlu_search.py / BRK.B test. Unlike
those scripts (which vary one state's weight against the live baseline and
measure Sharpe over the FULL continuous timeline), this fits and evaluates
using ONLY that state's own (discontiguous) weeks -- no other-state weeks
enter the objective at all. This is a strictly independent check: a finding
that only looks good when blended into the full timeline's variance could be
riding on the other states' behavior, not a real property of the state being
tested.

To avoid the degenerate 100%-cash corner solution (near-zero variance
trivially wins an isolated-Sharpe objective regardless of foregone return --
confirmed and rejected repeatedly elsewhere in this project), cash weight is
FIXED at the state's current live value and only the equity legs (core,
tqqq, qld, candidate) are searched, splitting the remaining budget.

Search = state's own weeks before 2020-01-01. Holdout = state's own weeks
from 2020-01-01 on. Both computed in isolation from every other state.
"""
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import STATE_LABEL, compute_states
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
from four_leg_overlay import last_trading_day_per_week

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
CANDIDATES_DIR = 'data/defensive_candidates'
SEARCH_HOLDOUT_SPLIT = '2020-01-01'
STEP = 0.05

LIVE_CASH = {'D': 0.30, 'E': 0.50}  # fixed, not searched


def build_rows(cand_px):
    qqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    spmo = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPMO.csv')
    tqqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/TQQQ.csv')
    qld = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QLD.csv')
    boxx = load_daily_csv(f'{ROBINHOOD_REPO}/etf/BOXX.csv')
    tbill = load_tbill()
    all_dates = sorted(set(qqq) | set(tqqq) | set(spmo) | set(qld) | set(cand_px))
    cash_idx = build_cash_index(all_dates, boxx, tbill)
    qqq_dates = sorted(qqq)
    states = compute_states(qqq_dates, qqq)
    state_by_date = dict(zip(qqq_dates, states))

    spmo_wk = last_trading_day_per_week(sorted(set(spmo)))
    tqqq_wk = last_trading_day_per_week(sorted(set(tqqq)))
    qld_wk = last_trading_day_per_week(sorted(set(qld)))
    cand_wk = last_trading_day_per_week(sorted(set(cand_px)))
    cash_wk = last_trading_day_per_week(sorted(set(cash_idx)))
    keys = sorted(set(spmo_wk) & set(tqqq_wk) & set(qld_wk) & set(cand_wk) & set(cash_wk))
    keys = [k for k in keys if spmo_wk[k] >= '2015-11-02']

    rows = []
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        w0, w1 = spmo_wk[k0], spmo_wk[k1]
        t0, t1 = tqqq_wk[k0], tqqq_wk[k1]
        q0, q1 = qld_wk[k0], qld_wk[k1]
        u0, u1 = cand_wk[k0], cand_wk[k1]
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
        r_u = cand_px[u1] / cand_px[u0] - 1
        r_cash = cash_idx[c1] / cash_idx[c0] - 1
        rows.append((w1, st, r_core, r_tqqq, r_qld, r_u, r_cash))
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


def isolated_rets(state_rows, core_w, tqqq_w, qld_w, cand_w, cash_w):
    out = []
    for _, st, rc, rt, rq, ru, rca in state_rows:
        out.append(core_w * rc + tqqq_w * rt + qld_w * rq + cand_w * ru + cash_w * rca)
    return out


def grid_search_isolated(rows, cash_w, step=STEP):
    """Search core/tqqq/qld/candidate (summing to 1-cash_w) to maximize
    isolated Sharpe on `rows` (already filtered to ONE state's own weeks,
    typically the search-period subset)."""
    budget = round(1 - cash_w, 6)
    best = (None,) * 4 + (-1e9,)
    n = round(budget / step + 1e-9)
    for i in range(n + 1):
        core_w = round(i * step, 4)
        for j in range(n + 1 - i):
            tqqq_w = round(j * step, 4)
            for k in range(n + 1 - i - j):
                qld_w = round(k * step, 4)
                cand_w = round(budget - core_w - tqqq_w - qld_w, 4)
                if cand_w < -1e-9:
                    continue
                rets = isolated_rets(rows, core_w, tqqq_w, qld_w, cand_w, cash_w)
                sh = sharpe(rets)
                if sh is not None and sh > best[4]:
                    best = (core_w, tqqq_w, qld_w, cand_w, sh)
    return best


def isolated_return(rows, weights):
    core_w, tqqq_w, qld_w, cand_w, cash_w = weights
    rets = isolated_rets(rows, core_w, tqqq_w, qld_w, cand_w, cash_w)
    nav = 1.0
    for r in rets:
        nav *= (1 + r)
    return nav - 1, rets


LIVE_D = (0.0, 0.0, 0.7, 0.0, 0.3)   # core/tqqq/qld/cand/cash, cand unused
LIVE_E = (0.5, 0.0, 0.0, 0.0, 0.5)


def validate(target_state, cand_name, cand_px, live_weights):
    rows = build_rows(cand_px)
    state_rows = [r for r in rows if r[1] == target_state]
    search_rows = [r for r in state_rows if r[0] < SEARCH_HOLDOUT_SPLIT]
    holdout_rows = [r for r in state_rows if r[0] >= SEARCH_HOLDOUT_SPLIT]

    print(f"=== State {target_state} ({STATE_LABEL[target_state]}), candidate={cand_name} ===")
    print(f"  total weeks in state: {len(state_rows)}  (search={len(search_rows)}, holdout={len(holdout_rows)})")

    if len(search_rows) < 8 or len(holdout_rows) < 4:
        print("  INSUFFICIENT DATA for an isolated search/holdout split -- skipping, not enough independent weeks")
        print()
        return

    cash_w = LIVE_CASH[target_state]
    best = grid_search_isolated(search_rows, cash_w, step=STEP)
    print(f"  isolated search-period best (core/tqqq/qld/{cand_name}): {best[:4]}  "
          f"(cash fixed at {cash_w})  search-Sharpe={best[4]:.3f}")

    search_ret, _ = isolated_return(search_rows, (*best[:4], cash_w))
    holdout_ret, holdout_rets = isolated_return(holdout_rows, (*best[:4], cash_w))
    holdout_sh = sharpe(holdout_rets)

    live_ret, live_rets_holdout = isolated_return(holdout_rows, live_weights)
    live_holdout_sh = sharpe(live_rets_holdout)

    print(f"  applied to HOLDOUT weeks only (isolated, this state's own weeks post-2020):")
    print(f"    candidate weights: total return {holdout_ret*100:+.1f}%, Sharpe {holdout_sh}")
    print(f"    live weights ({live_weights[:4]}, cash={live_weights[4]}): "
          f"total return {live_ret*100:+.1f}%, Sharpe {live_holdout_sh}")
    verdict = "HOLDS UP -- candidate beats live weights on isolated holdout" if (
        holdout_ret > live_ret) else "DOES NOT HOLD UP -- live weights beat the candidate on isolated holdout"
    print(f"  VERDICT: {verdict}")
    print()


def main():
    xlu = load_daily_csv(f'{CANDIDATES_DIR}/../XLU.csv') if False else load_daily_csv(f'{ROBINHOOD_REPO}/etf/XLU.csv')
    brkb = load_daily_csv(f'{CANDIDATES_DIR}/BRKB.csv')

    validate('D', 'XLU', xlu, LIVE_D)
    validate('E', 'XLU', xlu, LIVE_E)
    validate('E', 'BRKB', brkb, LIVE_E)


if __name__ == '__main__':
    main()
