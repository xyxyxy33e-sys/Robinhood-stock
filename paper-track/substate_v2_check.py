"""Verification test for a substate proposal surfaced in a separate,
unrelated conversation (screenshot, not this project's own research):

  A1: QQQ 20-day realized vol < its own rolling 75th-percentile threshold
      -> 55% core / 45% TQQQ (more aggressive)
  A2: QQQ 20-day realized vol >= that threshold
      -> 85% core / 15% TQQQ (more conservative)
  D1: RSP has outperformed QQQ over the trailing 63 trading days
      -> 70% core / 30% TQQQ (no cash)
  D2: RSP has lagged QQQ over the trailing 63 trading days
      -> 45% core / 10% TQQQ / 45% cash

This project already ran a broader substate study (substate_research.py)
across VIX, credit spread, breadth_pct, and xlu_spy_rel60 for states A/D/E/F
and found NOTHING held up (corner solutions, calendar confounds, or direct
contradiction of already-tested evidence). Neither factor proposed here
(QQQ's own realized-vol percentile; RSP-vs-QQQ relative strength) is exactly
one of those four, so this checks the SPECIFIC proposed rule and weights
against real data, using the same methodology: sample-size floor (MIN_N=15
weeks per half), full-timeline + search/holdout(2020-01-01) Sharpe, and a
corner-solution / calendar-collinearity check.
"""
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import compute_states, STATE_LABEL
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
from four_leg_overlay import last_trading_day_per_week

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
CANDIDATES_DIR = 'data/defensive_candidates'
SEARCH_HOLDOUT_SPLIT = '2020-01-01'
MIN_N = 15

# Current live TARGET_WEIGHTS baseline for A and D (5-leg collapsed to
# core/tqqq/cash since this proposal doesn't use QLD or XLU)
BASE_A = (0.80, 0.20, 0.00)
BASE_D_QLD = (0.00, 0.00, 0.70, 0.00, 0.30)  # core, tqqq, qld, xlu, cash -- live D uses QLD not TQQQ


def sharpe(rets):
    if len(rets) < 4:
        return None
    mean_r = sum(rets) / len(rets)
    var = sum((r - mean_r) ** 2 for r in rets) / (len(rets) - 1)
    if var <= 0:
        return None
    vol = math.sqrt(var) * math.sqrt(52.1775)
    return (mean_r * 52.1775) / vol


def cagr(rets):
    nav = 1.0
    for r in rets:
        nav *= (1 + r)
    return nav ** (1 / (len(rets) / 52.1775)) - 1 if rets else None


def rolling_percentile(values, dates, lookback=252):
    """values: dict date->float. Returns dict date-> percentile rank (0-1)
    of that date's value within the trailing `lookback` prior daily values
    (excluding the current day's own future, no lookahead)."""
    out = {}
    vals_sorted_window = []
    ordered = [(d, values[d]) for d in dates if d in values]
    for i, (d, v) in enumerate(ordered):
        window = [x for _, x in ordered[max(0, i - lookback):i]]
        if len(window) < 60:
            continue
        rank = sum(1 for w in window if w <= v) / len(window)
        out[d] = rank
    return out


def qqq_realized_vol_20d(qqq_px, qqq_dates):
    """Annualized 20-trading-day realized vol of QQQ daily log returns."""
    rets = {}
    for i in range(1, len(qqq_dates)):
        d0, d1 = qqq_dates[i - 1], qqq_dates[i]
        rets[d1] = math.log(qqq_px[d1] / qqq_px[d0])
    vol = {}
    ordered = [(d, rets[d]) for d in qqq_dates if d in rets]
    for i in range(19, len(ordered)):
        window = [r for _, r in ordered[i - 19:i + 1]]
        mean_r = sum(window) / len(window)
        var = sum((r - mean_r) ** 2 for r in window) / (len(window) - 1)
        vol[ordered[i][0]] = math.sqrt(var) * math.sqrt(252)
    return vol


def rsp_vs_qqq_63d(rsp_px, qqq_px, dates):
    out = {}
    for i in range(63, len(dates)):
        d0, d1 = dates[i - 63], dates[i]
        if d0 not in rsp_px or d1 not in rsp_px or d0 not in qqq_px or d1 not in qqq_px:
            continue
        r_rsp = rsp_px[d1] / rsp_px[d0] - 1
        r_qqq = qqq_px[d1] / qqq_px[d0] - 1
        out[d1] = r_rsp - r_qqq
    return out


def nearest_prior(d_map, d, floor):
    dd = d
    while dd not in d_map and dd > floor:
        dd = (date.fromisoformat(dd) - timedelta(days=1)).isoformat()
    return d_map.get(dd)


def main():
    qqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    spmo = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPMO.csv')
    tqqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/TQQQ.csv')
    boxx = load_daily_csv(f'{ROBINHOOD_REPO}/etf/BOXX.csv')
    tbill = load_tbill()
    rsp = load_daily_csv(f'{CANDIDATES_DIR}/RSP.csv')

    qqq_dates = sorted(qqq)
    states = compute_states(qqq_dates, qqq)
    state_by_date = dict(zip(qqq_dates, states))

    vol20 = qqq_realized_vol_20d(qqq, qqq_dates)
    vol_pct = rolling_percentile(vol20, qqq_dates, lookback=252)
    rsp_rel = rsp_vs_qqq_63d(rsp, qqq, qqq_dates)

    all_dates = sorted(set(qqq) | set(tqqq) | set(spmo) | set(rsp))
    cash_idx = build_cash_index(all_dates, boxx, tbill)

    spmo_wk = last_trading_day_per_week(sorted(set(spmo)))
    tqqq_wk = last_trading_day_per_week(sorted(set(tqqq)))
    cash_wk = last_trading_day_per_week(sorted(set(cash_idx)))
    keys = sorted(set(spmo_wk) & set(tqqq_wk) & set(cash_wk))
    keys = [k for k in keys if spmo_wk[k] >= '2015-11-02']

    rows = []
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        w0, w1 = spmo_wk[k0], spmo_wk[k1]
        t0, t1 = tqqq_wk[k0], tqqq_wk[k1]
        c0, c1 = cash_wk[k0], cash_wk[k1]
        sd = w0
        while sd not in state_by_date and sd > qqq_dates[0]:
            sd = (date.fromisoformat(sd) - timedelta(days=1)).isoformat()
        st = state_by_date.get(sd)
        if st is None:
            continue
        vp = nearest_prior(vol_pct, sd, qqq_dates[0])
        rr = nearest_prior(rsp_rel, sd, qqq_dates[0])
        r_core = spmo[w1] / spmo[w0] - 1
        r_tqqq = tqqq[t1] / tqqq[t0] - 1
        r_cash = cash_idx[c1] / cash_idx[c0] - 1
        rows.append((w1, st, r_core, r_tqqq, r_cash, vp, rr))

    # ---- A1/A2 sample-size + head-to-head check ----
    a_rows = [r for r in rows if r[1] == 'A' and r[5] is not None]
    a1 = [r for r in a_rows if r[5] < 0.75]   # low vol
    a2 = [r for r in a_rows if r[5] >= 0.75]  # high vol
    print(f"=== A1/A2 (QQQ 20d realized vol vs its own rolling-252d 75th pct) ===")
    print(f"  A total testable weeks: {len(a_rows)}  A1(low vol,n={len(a1)})  A2(high vol,n={len(a2)})")
    for label, subset in (('A1', a1), ('A2', a2)):
        search = [r for r in subset if r[0] < SEARCH_HOLDOUT_SPLIT]
        holdout = [r for r in subset if r[0] >= SEARCH_HOLDOUT_SPLIT]
        print(f"    {label}: search n={len(search)}  holdout n={len(holdout)}")

    def apply_scheme(rows_subset, weight_fn):
        rets = []
        for w1, st, rc, rt, rca, vp, rr in rows_subset:
            cw, tw, chw = weight_fn(st, vp, rr)
            rets.append(cw * rc + tw * rt + chw * rca)
        return rets

    def flat_weight(st, vp, rr):
        if st == 'A':
            return BASE_A
        return (1.0, 0.0, 0.0) if st not in ('B',) else (0.25, 0.75, 0.0)

    def a_substate_weight(st, vp, rr):
        if st == 'A':
            return (0.55, 0.45, 0.0) if vp < 0.75 else (0.85, 0.15, 0.0)
        return flat_weight(st, vp, rr)

    # Only compare A-relevant weeks in isolation to avoid B/C/D/E/F noise;
    # then also do a full-timeline check restricted to rows where state in ('A',)
    # union everything else held at flat_weight (so only A differs).
    all_rows_for_a_test = [r for r in rows if r[5] is not None or r[1] != 'A']
    flat_rets = apply_scheme(all_rows_for_a_test, flat_weight)
    sub_rets = apply_scheme(all_rows_for_a_test, a_substate_weight)
    wks = [r[0] for r in all_rows_for_a_test]
    flat_sh_full = sharpe(flat_rets)
    sub_sh_full = sharpe(sub_rets)
    pre = [i for i, w in enumerate(wks) if w < SEARCH_HOLDOUT_SPLIT]
    post = [i for i, w in enumerate(wks) if w >= SEARCH_HOLDOUT_SPLIT]
    flat_sh_pre = sharpe([flat_rets[i] for i in pre])
    sub_sh_pre = sharpe([sub_rets[i] for i in pre])
    flat_sh_post = sharpe([flat_rets[i] for i in post])
    sub_sh_post = sharpe([sub_rets[i] for i in post])
    print(f"  full-timeline Sharpe: flat A(80/20)={flat_sh_full:.3f}  A1/A2-substate={sub_sh_full:.3f}  "
          f"delta={sub_sh_full-flat_sh_full:+.3f}")
    print(f"  pre-2020 (search)   : flat={flat_sh_pre:.3f}  substate={sub_sh_pre:.3f}  delta={sub_sh_pre-flat_sh_pre:+.3f}")
    print(f"  post-2020 (holdout) : flat={flat_sh_post:.3f}  substate={sub_sh_post:.3f}  delta={sub_sh_post-flat_sh_post:+.3f}")
    print()

    # ---- D1/D2 sample-size + head-to-head check ----
    d_rows = [r for r in rows if r[1] == 'D' and r[6] is not None]
    d1 = [r for r in d_rows if r[6] > 0]   # RSP outperformed QQQ
    d2 = [r for r in d_rows if r[6] <= 0]  # RSP lagged QQQ
    print(f"=== D1/D2 (RSP vs QQQ, trailing 63 trading days) ===")
    print(f"  D total testable weeks: {len(d_rows)}  D1(RSP>QQQ,n={len(d1)})  D2(RSP<=QQQ,n={len(d2)})")
    for label, subset in (('D1', d1), ('D2', d2)):
        search = [r for r in subset if r[0] < SEARCH_HOLDOUT_SPLIT]
        holdout = [r for r in subset if r[0] >= SEARCH_HOLDOUT_SPLIT]
        print(f"    {label}: search n={len(search)}  holdout n={len(holdout)}")

    def flat_weight_tqqq_only(st, vp, rr):
        # Same idea but D's live baseline uses QLD not TQQQ; this proposal
        # is TQQQ-only, so compare against a TQQQ-equivalent flat D weight
        # (55/20/25, this project's ORIGINAL pre-QLD D baseline) for apples-to-apples.
        if st == 'D':
            return (0.55, 0.20, 0.25)
        return flat_weight(st, vp, rr)

    def d_substate_weight(st, vp, rr):
        if st == 'D':
            return (0.70, 0.30, 0.0) if rr is not None and rr > 0 else (0.45, 0.10, 0.45)
        return flat_weight(st, vp, rr)

    all_rows_for_d_test = [r for r in rows if r[6] is not None or r[1] != 'D']
    flat_rets_d = apply_scheme(all_rows_for_d_test, flat_weight_tqqq_only)
    sub_rets_d = apply_scheme(all_rows_for_d_test, d_substate_weight)
    wks_d = [r[0] for r in all_rows_for_d_test]
    pre_d = [i for i, w in enumerate(wks_d) if w < SEARCH_HOLDOUT_SPLIT]
    post_d = [i for i, w in enumerate(wks_d) if w >= SEARCH_HOLDOUT_SPLIT]
    print(f"  full-timeline Sharpe: flat D(55/20/25)={sharpe(flat_rets_d):.3f}  D1/D2-substate={sharpe(sub_rets_d):.3f}  "
          f"delta={sharpe(sub_rets_d)-sharpe(flat_rets_d):+.3f}")
    print(f"  pre-2020 (search)   : flat={sharpe([flat_rets_d[i] for i in pre_d]):.3f}  "
          f"substate={sharpe([sub_rets_d[i] for i in pre_d]):.3f}  "
          f"delta={sharpe([sub_rets_d[i] for i in pre_d])-sharpe([flat_rets_d[i] for i in pre_d]):+.3f}")
    print(f"  post-2020 (holdout) : flat={sharpe([flat_rets_d[i] for i in post_d]):.3f}  "
          f"substate={sharpe([sub_rets_d[i] for i in post_d]):.3f}  "
          f"delta={sharpe([sub_rets_d[i] for i in post_d])-sharpe([flat_rets_d[i] for i in post_d]):+.3f}")


if __name__ == '__main__':
    main()
