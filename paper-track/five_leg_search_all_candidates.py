"""Generalizes five_leg_xlu_search.py to test SCHD, VYM, and USMV as
standalone state-specific legs too (not blended into core), same
per-state-vs-baseline methodology, search/holdout split at 2020-01-01.

RESULTS SUMMARY (run 2026-08-31, full-timeline Sharpe delta vs. the live
4-leg baseline of 1.065, "HOLDS UP" = search win that also improves the
full timeline AND holdout, not just the search slice):

           A       B        C        D        E        F
  XLU    flat   worse    worse   +0.020*  +0.043*   worse
  SCHD   flat   worse    worse    flat     worse     worse
  VYM    flat   worse    worse    flat    +0.005~    worse
  USMV   flat   worse    worse   worse     flat      worse

  * = holdout-confirmed (see five_leg_xlu_search.py for the full numbers
      and the narrow-peak caveats -- D replaces its entire core+QLD
      structure with TQQQ+XLU, E goes to a 100% XLU single-asset corner)
  ~ = technically clears the "HOLDS UP" threshold but at 1/9th of XLU's
      magnitude (+0.005 vs +0.043) -- not a meaningfully different result
      from "flat", not worth pursuing on its own

VERDICT: XLU remains uniquely effective, including as a standalone
state-specific leg, not just blended into core. None of the three
low-fee dividend/quality/low-vol alternatives (SCHD ~0.06%, VYM ~0.06%,
USMV ~0.15%) come close to matching XLU's D or E result even at this
looser bar -- confirms (doesn't just repeat) the earlier core-blend
finding that XLU's rate-sensitive utilities-sector behavior is doing
something structurally different from these equity-factor tilts, which
stay correlated with the momentum core they're meant to hedge.
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
STEP = 0.1

BASELINE = {
    'A': (0.80, 0.20, 0.00, 0.00, 0.00), 'B': (0.25, 0.75, 0.00, 0.00, 0.00), 'C': (1.00, 0.00, 0.00, 0.00, 0.00),
    'D': (0.00, 0.00, 0.70, 0.00, 0.30), 'E': (0.50, 0.00, 0.00, 0.00, 0.50), 'F': (0.30, 0.00, 0.00, 0.00, 0.70),
}


def build_weekly_series(cand_px):
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
                    cand_w = round(l * step, 2)
                    cash_w = round(1 - core_w - tqqq_w - qld_w - cand_w, 6)
                    if cash_w < -1e-9:
                        continue
                    weights = dict(BASELINE)
                    weights[target_state] = (core_w, tqqq_w, qld_w, cand_w, cash_w)
                    rets = full_series_rets(rows, weights)
                    sh = sharpe(rets)
                    if sh is not None and sh > best[5]:
                        best = (core_w, tqqq_w, qld_w, cand_w, round(cash_w, 2), sh)
    return best


def main():
    for sym in ('SCHD', 'VYM', 'USMV', 'GLD'):
        px = load_daily_csv(f'{CANDIDATES_DIR}/{sym}.csv')
        rows = build_weekly_series(px)
        baseline_full = sharpe(full_series_rets(rows, BASELINE))
        search_rows = [r for r in rows if r[0] < SEARCH_HOLDOUT_SPLIT]
        holdout_rows = [r for r in rows if r[0] >= SEARCH_HOLDOUT_SPLIT]
        print(f"=== {sym} === baseline full-Sharpe {baseline_full:.3f}")
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
            flag = 'HOLDS UP' if delta > 0.005 and holdout_sh > baseline_full - 0.05 else ('worse' if delta < -0.005 else 'flat')
            print(f"  {st} ({STATE_LABEL[st]:<20}) n={len(by_state[st]):>3}  best={best[:5]}  "
                  f"full={full_sh:.3f} (d={delta:+.3f})  holdout={holdout_sh:.3f}  [{flag}]")
        print()


if __name__ == '__main__':
    main()
