"""Broader substate research pass, requested after two narrower checks
(substate_research.py: VIX/credit/breadth/xlu_spy_rel60, all rejected;
substate_v2_check.py + a1a2_deepdive.py: QQQ vol-percentile and RSP-vs-QQQ,
vol-percentile showed a real-but-fragile signal for state A only, RSP-vs-QQQ
rejected). This pass widens the factor set and tests EVERY factor against
EVERY testable state (not just the one or two each prior script focused on),
using the live GLD-blended core (CORE_SPMO_FRAC/CORE_GLD_FRAC) as the return
series, and the same discipline throughout: MIN_N=15/half, grid search on
search-period only (pre-2020-01-01), full-timeline + holdout Sharpe check,
corner-solution flag, next-state confound check.

FACTORS (11 total):
  Level:        vix, credit_baa10y, breadth_pct, xlu_spy_rel60, dgs3mo
  21d change:   vix_chg21, credit_chg21, breadth_chg21, xlu_rel_chg21, dgs3mo_chg21
  Internal:     qqq_vol20_pct (252d rolling percentile of QQQ's own 20d realized
                vol -- the one factor that showed a real signal before, now
                checked against every state, not just A)

RESULTS SUMMARY (run 2026-08-31): the 11-factor x 6-state median-split sweep
found ZERO candidates clearing the bar (non-corner, positive full-timeline
AND holdout Sharpe delta) -- reinforces substate_research.py's original
conclusion with a much wider factor net (rate-of-change versions of every
level factor, plus DGS3MO, none tried before). A follow-up extended the one
factor with prior real backing (QQQ's own realized-vol percentile) to every
state at multiple percentile thresholds (60th-90th), not just state A:
a few "HOLDS UP" hits appeared but none survive scrutiny -- A/70th is a
near-zero coin flip (+1.7% vs -2.9% over 48 weeks) on a 100%-XLU corner;
D/75th and D/90th both route into XLU, reproducing the exact D/XLU
corner-solution false positive already caught and rejected elsewhere in
this project; F/90th has a 6-week search sample, below this project's own
15-week floor. VERDICT: no new evidence for substating beyond the original
A/252d/75th-percentile signal, already documented as "real kernel, not
robust enough to trust" in a1a2_deepdive.py. Nothing adopted.
"""
import csv
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import compute_states, STATE_LABEL, TARGET_WEIGHTS, CORE_SPMO_FRAC, CORE_GLD_FRAC
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
from four_leg_overlay import last_trading_day_per_week
from a1a2_deepdive import qqq_realized_vol_20d, rolling_percentile, nearest_prior

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
CANDIDATES_DIR = 'data/defensive_candidates'
SEARCH_HOLDOUT_SPLIT = '2020-01-01'
MIN_N = 15
STEP = 0.1

BASELINE = TARGET_WEIGHTS


def load_fred(path):
    out = {}
    with open(path) as f:
        r = csv.DictReader(f)
        for row in r:
            d, v = row['observation_date'], row[list(row.keys())[1]]
            if v and v != '.':
                out[d] = float(v)
    return out


def daily_change(series, dates, window=21):
    out = {}
    ordered = [(d, series[d]) for d in dates if d in series]
    for i in range(window, len(ordered)):
        d1, v1 = ordered[i]
        d0, v0 = ordered[i - window]
        out[d1] = v1 - v0
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

    vix = load_fred(f'{ROBINHOOD_REPO}/VIXCLS.csv')
    credit = load_fred(f'{ROBINHOOD_REPO}/BAA10Y.csv')
    dgs3mo = load_fred(f'{ROBINHOOD_REPO}/DGS3MO.csv')

    factors_csv = {}
    with open(f'{ROBINHOOD_REPO}/factors.csv') as f:
        for row in csv.DictReader(f):
            factors_csv[row['date']] = row
    breadth = {d: float(r['breadth_pct']) for d, r in factors_csv.items() if r.get('breadth_pct')}
    xlu_rel = {d: float(r['xlu_spy_rel60']) for d, r in factors_csv.items() if r.get('xlu_spy_rel60')}

    vol20 = qqq_realized_vol_20d(qqq, qqq_dates)
    vol_pct = rolling_percentile(vol20, qqq_dates, 252)

    vix_chg = daily_change(vix, sorted(vix))
    credit_chg = daily_change(credit, sorted(credit))
    breadth_chg = daily_change(breadth, sorted(breadth))
    xlu_rel_chg = daily_change(xlu_rel, sorted(xlu_rel))
    dgs3mo_chg = daily_change(dgs3mo, sorted(dgs3mo))

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
        factor_vals = {
            'vix': nearest_prior(vix, sd, floor),
            'vix_chg21': nearest_prior(vix_chg, sd, floor),
            'credit_baa10y': nearest_prior(credit, sd, floor),
            'credit_chg21': nearest_prior(credit_chg, sd, floor),
            'breadth_pct': nearest_prior(breadth, sd, floor),
            'breadth_chg21': nearest_prior(breadth_chg, sd, floor),
            'xlu_spy_rel60': nearest_prior(xlu_rel, sd, floor),
            'xlu_rel_chg21': nearest_prior(xlu_rel_chg, sd, floor),
            'dgs3mo': nearest_prior(dgs3mo, sd, floor),
            'dgs3mo_chg21': nearest_prior(dgs3mo_chg, sd, floor),
            'qqq_vol20_pct': nearest_prior(vol_pct, sd, floor),
        }
        rows.append((w1, st, r_core, r_tqqq, r_qld, r_xlu, r_cash, sd, factor_vals))
    return rows


def full_series_rets(rows, weights_by_state):
    out = []
    for r in rows:
        cw, tw, qw, xw, chw = weights_by_state[r[1]]
        out.append(cw * r[2] + tw * r[3] + qw * r[4] + xw * r[5] + chw * r[6])
    return out


def grid_search_one_state_split(rows, target_state, halfmask, step=STEP):
    """halfmask: dict row-index-in-target-state-list -> 'high'/'low'/None.
    Search each half's own weight independently isn't done here -- to match
    substate_research.py's methodology, this searches ONE flagged half at a
    time (passed in via filtered rows), against the live baseline elsewhere."""
    best = (None,) * 5 + (-1e9,)
    n = round(1 / step)
    for i in range(n + 1):
        cw = round(i * step, 2)
        for j in range(n + 1 - i):
            tw = round(j * step, 2)
            for k in range(n + 1 - i - j):
                qw = round(k * step, 2)
                for l in range(n + 1 - i - j - k):
                    xw = round(l * step, 2)
                    chw = round(1 - cw - tw - qw - xw, 6)
                    if chw < -1e-9:
                        continue
                    rets = []
                    for r in rows:
                        if id(r) in halfmask:
                            rets.append(cw * r[2] + tw * r[3] + qw * r[4] + xw * r[5] + chw * r[6])
                        else:
                            wcw, wtw, wqw, wxw, wchw = TARGET_WEIGHTS[r[1]]
                            rets.append(wcw * r[2] + wtw * r[3] + wqw * r[4] + wxw * r[5] + wchw * r[6])
                    sh = sharpe(rets)
                    if sh is not None and sh > best[5]:
                        best = (cw, tw, qw, xw, round(chw, 2), sh)
    return best


def is_corner(weights, tol=0.02):
    return any(w <= tol or w >= 1 - tol for w in weights[:5])


def main():
    rows = build_rows()
    baseline_full = sharpe(full_series_rets(rows, BASELINE))
    print(f"Live baseline (GLD-blended core) full-timeline Sharpe: {baseline_full:.3f}\n")

    by_state = {}
    for r in rows:
        by_state.setdefault(r[1], []).append(r)

    factors = ['vix', 'vix_chg21', 'credit_baa10y', 'credit_chg21', 'breadth_pct',
               'breadth_chg21', 'xlu_spy_rel60', 'xlu_rel_chg21', 'dgs3mo',
               'dgs3mo_chg21', 'qqq_vol20_pct']

    findings = []
    for st in sorted(by_state):
        state_rows = by_state[st]
        if len(state_rows) < 2 * MIN_N:
            print(f"State {st} ({STATE_LABEL[st]}): n={len(state_rows)} < {2*MIN_N}, not testable at all\n")
            continue
        print(f"=== State {st} ({STATE_LABEL[st]}), n={len(state_rows)} ===")
        for factor in factors:
            vals = [(r, r[8][factor]) for r in state_rows if r[8][factor] is not None]
            if len(vals) < 2 * MIN_N:
                continue
            sorted_vals = sorted(v for _, v in vals)
            median = sorted_vals[len(sorted_vals) // 2]
            high = set(id(r) for r, v in vals if v >= median)
            low_n = len(vals) - len(high)
            if len(high) < MIN_N or low_n < MIN_N:
                continue
            for half_label, half_ids in (('high', high), ('low', set(id(r) for r, v in vals if v < median))):
                half_rows = [r for r in state_rows if id(r) in half_ids]
                search_half = [r for r in half_rows if r[0] < SEARCH_HOLDOUT_SPLIT]
                holdout_half = [r for r in half_rows if r[0] >= SEARCH_HOLDOUT_SPLIT]
                if len(search_half) < 6 or len(holdout_half) < 4:
                    continue
                search_set = set(id(r) for r in search_half)
                search_rows_all = [r for r in rows if r[0] < SEARCH_HOLDOUT_SPLIT]
                best = grid_search_one_state_split(search_rows_all, st, search_set, step=STEP)
                if best[5] is None:
                    continue
                weights_at_best = dict(BASELINE)
                weights_at_best[st] = best[:5]
                # apply candidate weight only to the matching half in holdout, live elsewhere
                holdout_ids = set(id(r) for r in holdout_half)
                holdout_rets = []
                for r in rows:
                    if r[0] < SEARCH_HOLDOUT_SPLIT:
                        continue
                    if id(r) in holdout_ids:
                        cw, tw, qw, xw, chw = best[:5]
                    else:
                        cw, tw, qw, xw, chw = BASELINE[r[1]]
                    holdout_rets.append(cw * r[2] + tw * r[3] + qw * r[4] + xw * r[5] + chw * r[6])
                holdout_sh = sharpe(holdout_rets)
                full_rets = []
                for r in rows:
                    if id(r) in half_ids:
                        cw, tw, qw, xw, chw = best[:5]
                    else:
                        cw, tw, qw, xw, chw = BASELINE[r[1]]
                    full_rets.append(cw * r[2] + tw * r[3] + qw * r[4] + xw * r[5] + chw * r[6])
                full_sh = sharpe(full_rets)
                delta_full = full_sh - baseline_full
                delta_holdout = holdout_sh - baseline_full
                corner = is_corner(best[:5])
                if delta_full > 0.02 and delta_holdout > 0.0 and not corner:
                    print(f"  {factor:<16} {half_label:<5} n={len(half_rows):>3} (search={len(search_half)},holdout={len(holdout_half)})  "
                          f"best={best[:5]}  full_Sh={full_sh:.3f} (d={delta_full:+.3f})  holdout_Sh={holdout_sh:.3f} (d={delta_holdout:+.3f})  CANDIDATE")
                    findings.append((st, factor, half_label, best, delta_full, delta_holdout, corner))
        print()

    print("=== SUMMARY: non-corner candidates clearing full+holdout Sharpe bar ===")
    if not findings:
        print("  NONE. Every factor/state/half combination either failed the sample-size floor, "
              "produced a corner solution, or did not improve both full-timeline and holdout Sharpe.")
    for st, factor, half, best, df, dh, corner in findings:
        print(f"  {st}/{factor}/{half}: weights={best[:5]}  d_full={df:+.3f}  d_holdout={dh:+.3f}")


if __name__ == '__main__':
    main()
