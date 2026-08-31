"""Verification of an E1/E2 substate proposal surfaced outside this project:
  E1: QQQ 63-day trailing trend R^2 >= 0.20 -> 70% core / 30% cash
  E2: QQQ 63-day trailing trend R^2 <  0.20 -> 30% core / 70% cash
Core = the live 75/25 SPMO/GLD blend. This replaces state E's live XLU
allocation entirely with direct (trend-gated) core exposure -- a
fundamentally different mechanism from the validated E/XLU design, tested
here on its own terms against the live baseline.

Trend R^2 = coefficient of determination of an OLS fit of log(QQQ close)
vs. trading-day index over the trailing 63 trading days (no lookahead,
value as of week-start). High R^2 means a clean, low-noise trend (up OR
down); low R^2 means choppy/directionless price action.

Same discipline as every other substate check this session: MIN_N=15/half,
search period pre-2020-01-01, full-timeline + holdout Sharpe, corner-solution
flag, then isolated single-state validation (E's own weeks only) as the
decisive test given this project's history of E/D false positives.

RESULTS SUMMARY (run 2026-08-31): REJECTED, decisively. State E only has 32
weeks total; splitting further leaves E1 with 8 search-period weeks (below
this project's MIN_N=15 floor) and E2 with just 7 weeks total (5 search, 2
holdout) -- not remotely testable. The full-timeline check with the exact
proposed weights shows NO improvement over live E/XLU (Sharpe 1.132 vs
1.138, i.e. slightly worse), with the post-2020 number (1.229) offset by a
worse pre-2020 number (0.955) -- itself a search/holdout inconsistency.
E1's isolated test reproduces the exact corner-solution trap seen elsewhere
in this project: a blind search on E1's 8 search weeks collapses to 0%
core/100% cash (search-Sharpe 8.7, the same absurd-Sharpe-tiny-sample
signature as every prior false positive), applying THAT to holdout gives a
real return of +0.6% despite the inflated Sharpe -- the proposed 70% core
weight only looks good if you already know the holdout outcome, exactly
the cherry-picking this project's search->holdout discipline exists to
catch. No live weights changed.
"""
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import compute_states, STATE_LABEL, TARGET_WEIGHTS, CORE_SPMO_FRAC, CORE_GLD_FRAC
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
from four_leg_overlay import last_trading_day_per_week
from a1a2_deepdive import nearest_prior

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
CANDIDATES_DIR = 'data/defensive_candidates'
SEARCH_HOLDOUT_SPLIT = '2020-01-01'
MIN_N = 15
WINDOW = 63


def trend_r2(qqq_px, qqq_dates):
    """Trailing 63-day OLS R^2 of log(close) vs day index, no lookahead."""
    out = {}
    log_px = [(d, math.log(qqq_px[d])) for d in qqq_dates]
    for i in range(WINDOW - 1, len(log_px)):
        window = log_px[i - WINDOW + 1:i + 1]
        xs = list(range(WINDOW))
        ys = [y for _, y in window]
        mx = sum(xs) / WINDOW
        my = sum(ys) / WINDOW
        sxy = sum((xs[j] - mx) * (ys[j] - my) for j in range(WINDOW))
        sxx = sum((x - mx) ** 2 for x in xs)
        syy = sum((y - my) ** 2 for y in ys)
        if sxx <= 0 or syy <= 0:
            continue
        r = sxy / math.sqrt(sxx * syy)
        out[window[-1][0]] = r * r  # R^2
    return out


def sharpe(rets):
    if len(rets) < 4:
        return None
    mean_r = sum(rets) / len(rets)
    var = sum((r - mean_r) ** 2 for r in rets) / (len(rets) - 1)
    if var <= 0:
        return None
    vol = math.sqrt(var) * math.sqrt(52.1775)
    return (mean_r * 52.1775) / vol


def build_rows():
    qqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    spmo = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPMO.csv')
    tqqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/TQQQ.csv')
    qld = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QLD.csv')
    xlu = load_daily_csv(f'{ROBINHOOD_REPO}/etf/XLU.csv')
    gld = load_daily_csv(f'{CANDIDATES_DIR}/GLD.csv')
    boxx = load_daily_csv(f'{ROBINHOOD_REPO}/etf/BOXX.csv')
    tbill = load_tbill()

    qqq_dates = sorted(qqq)
    states = compute_states(qqq_dates, qqq)
    state_by_date = dict(zip(qqq_dates, states))
    r2 = trend_r2(qqq, qqq_dates)

    all_dates = sorted(set(qqq) | set(tqqq) | set(spmo) | set(qld) | set(xlu) | set(gld))
    cash_idx = build_cash_index(all_dates, boxx, tbill)

    spmo_wk = last_trading_day_per_week(sorted(set(spmo)))
    tqqq_wk = last_trading_day_per_week(sorted(set(tqqq)))
    qld_wk = last_trading_day_per_week(sorted(set(qld)))
    xlu_wk = last_trading_day_per_week(sorted(set(xlu)))
    gld_wk = last_trading_day_per_week(sorted(set(gld)))
    cash_wk = last_trading_day_per_week(sorted(set(cash_idx)))
    keys = sorted(set(spmo_wk) & set(tqqq_wk) & set(qld_wk) & set(xlu_wk) & set(gld_wk) & set(cash_wk))
    keys = [k for k in keys if spmo_wk[k] >= '2015-11-02']

    rows = []
    floor = qqq_dates[0]
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        w0, w1 = spmo_wk[k0], spmo_wk[k1]
        t0, t1 = tqqq_wk[k0], tqqq_wk[k1]
        q0, q1 = qld_wk[k0], qld_wk[k1]
        x0, x1 = xlu_wk[k0], xlu_wk[k1]
        g0, g1 = gld_wk[k0], gld_wk[k1]
        c0, c1 = cash_wk[k0], cash_wk[k1]
        sd = w0
        while sd not in state_by_date and sd > floor:
            sd = (date.fromisoformat(sd) - timedelta(days=1)).isoformat()
        st = state_by_date.get(sd)
        if st is None:
            continue
        r_core = CORE_SPMO_FRAC * (spmo[w1] / spmo[w0] - 1) + CORE_GLD_FRAC * (gld[g1] / gld[g0] - 1)
        r_tqqq = tqqq[t1] / tqqq[t0] - 1
        r_qld = qld[q1] / qld[q0] - 1
        r_xlu = xlu[x1] / xlu[x0] - 1
        r_cash = cash_idx[c1] / cash_idx[c0] - 1
        r2_val = nearest_prior(r2, sd, floor)
        rows.append((w1, st, r_core, r_tqqq, r_qld, r_xlu, r_cash, r2_val))
    return rows


def full_series_rets(rows, weights_by_state):
    out = []
    for r in rows:
        cw, tw, qw, xw, chw = weights_by_state[r[1]]
        out.append(cw * r[2] + tw * r[3] + qw * r[4] + xw * r[5] + chw * r[6])
    return out


def main():
    rows = build_rows()
    baseline_full = sharpe(full_series_rets(rows, TARGET_WEIGHTS))
    print(f"Live baseline full-timeline Sharpe: {baseline_full:.3f}\n")

    e_rows = [r for r in rows if r[1] == 'E' and r[7] is not None]
    e1 = [r for r in e_rows if r[7] >= 0.20]
    e2 = [r for r in e_rows if r[7] < 0.20]
    print(f"State E: n={len(e_rows)}  E1(R2>=0.20)={len(e1)}  E2(R2<0.20)={len(e2)}")
    for label, subset in (('E1', e1), ('E2', e2)):
        search = [r for r in subset if r[0] < SEARCH_HOLDOUT_SPLIT]
        holdout = [r for r in subset if r[0] >= SEARCH_HOLDOUT_SPLIT]
        print(f"  {label}: search={len(search)}  holdout={len(holdout)}")
        if search:
            avg_ret = sum(r[2] for r in search) / len(search)  # avg weekly core return
    print()

    # Apply the EXACT proposed weights (70/30 and 30/70, core/cash) full-timeline
    def weekly_ret(row):
        w1, st, rc, rt, rq, rx, rca, r2v = row
        if st == 'E' and r2v is not None:
            if r2v >= 0.20:
                return 0.70 * rc + 0.30 * rca
            else:
                return 0.30 * rc + 0.70 * rca
        cw, tw, qw, xw, chw = TARGET_WEIGHTS[st]
        return cw * rc + tw * rt + qw * rq + xw * rx + chw * rca

    proposed_rets = [weekly_ret(r) for r in rows]
    proposed_full = sharpe(proposed_rets)
    weeks = [r[0] for r in rows]
    pre_idx = [i for i, w in enumerate(weeks) if w < SEARCH_HOLDOUT_SPLIT]
    post_idx = [i for i, w in enumerate(weeks) if w >= SEARCH_HOLDOUT_SPLIT]
    proposed_pre = sharpe([proposed_rets[i] for i in pre_idx])
    proposed_post = sharpe([proposed_rets[i] for i in post_idx])
    print(f"Proposed E1/E2 (exact weights) full Sharpe: {proposed_full:.3f} (d={proposed_full-baseline_full:+.3f})")
    print(f"  pre-2020 (search): {proposed_pre:.3f}")
    print(f"  post-2020 (holdout): {proposed_post:.3f}")
    print()

    # Isolated validation: E's own weeks only, cash NOT searched (fixed per-half at the
    # proposed cash weight), core weight searched to see what the data itself would pick
    print("=== Isolated validation (state E's own weeks only) ===")
    for label, subset, live_cash in (('E1 (R2>=0.20)', e1, 0.30), ('E2 (R2<0.20)', e2, 0.70)):
        search = [r for r in subset if r[0] < SEARCH_HOLDOUT_SPLIT]
        holdout = [r for r in subset if r[0] >= SEARCH_HOLDOUT_SPLIT]
        if len(search) < 6 or len(holdout) < 4:
            print(f"  {label}: n_search={len(search)} n_holdout={len(holdout)} -- INSUFFICIENT DATA")
            continue
        best = None
        for i in range(21):
            core_w = round(i * 0.05, 2)
            cash_w = round(1 - core_w, 2)
            rets = [core_w * r[2] + cash_w * r[6] for r in search]
            sh = sharpe(rets)
            if sh is not None and (best is None or sh > best[1]):
                best = (core_w, sh)
        proposed_core_w = 0.70 if label.startswith('E1') else 0.30
        holdout_proposed = [proposed_core_w * r[2] + (1 - proposed_core_w) * r[6] for r in holdout]
        holdout_search_best = [best[0] * r[2] + (1 - best[0]) * r[6] for r in holdout]
        nav_p = 1.0
        for r in holdout_proposed: nav_p *= (1 + r)
        nav_b = 1.0
        for r in holdout_search_best: nav_b *= (1 + r)
        print(f"  {label}: n_search={len(search)} n_holdout={len(holdout)}  "
              f"search-optimal core_w={best[0]:.2f} (search-Sharpe={best[1]})")
        print(f"    proposed weight ({proposed_core_w}) on holdout: total return {(nav_p-1)*100:+.1f}%  Sharpe={sharpe(holdout_proposed)}")
        print(f"    search-optimal weight on holdout: total return {(nav_b-1)*100:+.1f}%  Sharpe={sharpe(holdout_search_best)}")


if __name__ == '__main__':
    main()
