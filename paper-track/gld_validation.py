"""Isolated single-state validation for GLD (SPDR Gold Shares, ~0.40% expense
ratio) as a candidate defensive leg, following the same methodology as
isolated_state_validation.py: fit and evaluate using ONLY a target state's
own discontiguous weeks, cash weight FIXED at the live value (not searched,
to avoid the degenerate 100%-cash corner solution), search period pre-2020,
holdout post-2020.

Motivation: five_leg_search_all_candidates.py's looser full-timeline search
found GLD's state-E result (100% GLD, full-timeline Sharpe delta +0.142) far
larger than XLU's (+0.043, the currently-live E-state defensive leg) --
large enough relative to prior false positives in this project (D/XLU,
E/BRK.B) that it needs the strict isolated test before being trusted, not
just the looser search.

This script does two things XLU's own validation didn't need to: (1) run
GLD through the same isolated test XLU passed, and (2) since GLD's looser
signal is bigger than XLU's, directly compare GLD against XLU (not just
against the pre-XLU cash baseline) on E's isolated holdout weeks, and check
a GLD/XLU blend in case they hedge different things.

RESULTS SUMMARY (run 2026-08-31): see bottom of file after first execution.
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

LIVE_CASH_E = 0.50
LIVE_E_XLU = (0.0, 0.0, 0.0, 1.0, 0.0, 0.50)  # core/tqqq/qld/xlu/gld/cash -- current live E


def build_rows():
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
        r_core = spmo[w1] / spmo[w0] - 1
        r_tqqq = tqqq[t1] / tqqq[t0] - 1
        r_qld = qld[q1] / qld[q0] - 1
        r_xlu = xlu[x1] / xlu[x0] - 1
        r_gld = gld[g1] / gld[g0] - 1
        r_cash = cash_idx[c1] / cash_idx[c0] - 1
        rows.append((w1, st, r_core, r_tqqq, r_qld, r_xlu, r_gld, r_cash))
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


def isolated_rets(state_rows, core_w, tqqq_w, qld_w, xlu_w, gld_w, cash_w):
    out = []
    for _, st, rc, rt, rq, rx, rg, rca in state_rows:
        out.append(core_w * rc + tqqq_w * rt + qld_w * rq + xlu_w * rx + gld_w * rg + cash_w * rca)
    return out


def isolated_return(rows, weights):
    rets = isolated_rets(rows, *weights)
    nav = 1.0
    for r in rets:
        nav *= (1 + r)
    return nav - 1, rets


def grid_search_isolated(rows, cash_w, step=STEP):
    """Search core/tqqq/qld/xlu/gld (summing to 1-cash_w) to maximize
    isolated Sharpe -- includes XLU so the search can find a blend, not
    just crown whichever single asset happens to win in this sample."""
    budget = round(1 - cash_w, 6)
    best = (None,) * 5 + (-1e9,)
    n = round(budget / step + 1e-9)
    for i in range(n + 1):
        core_w = round(i * step, 4)
        for j in range(n + 1 - i):
            tqqq_w = round(j * step, 4)
            for k in range(n + 1 - i - j):
                qld_w = round(k * step, 4)
                for l in range(n + 1 - i - j - k):
                    xlu_w = round(l * step, 4)
                    gld_w = round(budget - core_w - tqqq_w - qld_w - xlu_w, 4)
                    if gld_w < -1e-9:
                        continue
                    rets = isolated_rets(rows, core_w, tqqq_w, qld_w, xlu_w, gld_w, cash_w)
                    sh = sharpe(rets)
                    if sh is not None and sh > best[5]:
                        best = (core_w, tqqq_w, qld_w, xlu_w, gld_w, sh)
    return best


def main():
    rows = build_rows()
    state_rows = [r for r in rows if r[1] == 'E']
    search_rows = [r for r in state_rows if r[0] < SEARCH_HOLDOUT_SPLIT]
    holdout_rows = [r for r in state_rows if r[0] >= SEARCH_HOLDOUT_SPLIT]

    print(f"=== State E ({STATE_LABEL['E']}) -- GLD vs live XLU, isolated ===")
    print(f"  total weeks in state E: {len(state_rows)} (search={len(search_rows)}, holdout={len(holdout_rows)})")
    if len(search_rows) < 8 or len(holdout_rows) < 4:
        print("  INSUFFICIENT DATA -- skipping")
        return

    best = grid_search_isolated(search_rows, LIVE_CASH_E, step=STEP)
    print(f"  isolated search-period best (core/tqqq/qld/xlu/gld): {best[:5]} "
          f"(cash fixed at {LIVE_CASH_E})  search-Sharpe={best[5]:.3f}")

    best_weights = (*best[:5], LIVE_CASH_E)
    best_holdout_ret, best_holdout_rets = isolated_return(holdout_rows, best_weights)
    best_holdout_sh = sharpe(best_holdout_rets)

    # 100% GLD, isolated, for direct single-asset comparison to XLU's own result
    gld_only = (0.0, 0.0, 0.0, 0.0, 0.50, 0.50)
    gld_holdout_ret, gld_holdout_rets = isolated_return(holdout_rows, gld_only)
    gld_holdout_sh = sharpe(gld_holdout_rets)

    xlu_holdout_ret, xlu_holdout_rets = isolated_return(holdout_rows, LIVE_E_XLU)
    xlu_holdout_sh = sharpe(xlu_holdout_rets)

    print(f"  HOLDOUT (isolated, state E's own weeks post-2020):")
    print(f"    search-optimal blend : total return {best_holdout_ret*100:+.1f}%, Sharpe {best_holdout_sh}")
    print(f"    100% GLD / 50% cash  : total return {gld_holdout_ret*100:+.1f}%, Sharpe {gld_holdout_sh}")
    print(f"    100% XLU / 50% cash (current live): total return {xlu_holdout_ret*100:+.1f}%, Sharpe {xlu_holdout_sh}")

    verdict = "GLD HOLDS UP over live XLU on isolated holdout" if gld_holdout_ret > xlu_holdout_ret else \
              "GLD DOES NOT beat live XLU on isolated holdout"
    print(f"  VERDICT: {verdict}")

    # sample composition check -- how many distinct weeks/years actually drive state E,
    # and were GLD's biggest weeks clustered (a repeat of the corner-solution / small-sample trap)?
    print(f"\n  state E holdout weeks (n={len(holdout_rows)}) individual GLD returns:")
    for wk, st, rc, rt, rq, rx, rg, rca in holdout_rows:
        print(f"    {wk}: GLD {rg*100:+.2f}%  XLU {rx*100:+.2f}%")


if __name__ == '__main__':
    main()
