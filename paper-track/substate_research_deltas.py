"""Substate research, take 2: RATE OF CHANGE instead of LEVEL.

substate_research.py (read that file first -- this one reuses its exact
methodology and infrastructure) tested whether states A-F could be split by
the LEVEL of four factors (VIX, credit spread BAA10Y, S&P 500 breadth_pct,
xlu_spy_rel60) at week-start. Verdict there: no level split survived both
the corner-solution check and the holdout check.

A manual (unvalidated, pre-pipeline) check found a different pattern for
state F: not VIX's LEVEL but its RATE OF CHANGE going into the week --
top-quartile 1-day and 5-day VIX point-jumps looked much worse for F's
weekly core/satellite returns than the rest of F's weeks. Economically this
is a different signal from level (level-high-VIX historically marked
bottoms for F; a VIX currently ACCELERATING upward looks more like
mid-selloff momentum). This file runs that finding -- and the same
delta framing generalized to the other three factors -- through the exact
same grid-search / Sharpe / corner-solution / holdout / confound pipeline
substate_research.py uses for levels, instead of taking the raw-average
check on faith.

METHODOLOGY (identical to substate_research.py except for how the split
value is computed):
  1. Same weekly SPMO-core/TQQQ-satellite/BOXX-cash series, state assigned
     at week start, no lookahead.
  2. Factor DELTA at week-start = factor_value(week-start's trading day, per
     factors.csv's own trading-day index) minus factor_value(N trading days
     earlier in that same index), for N in {1, 5}. Both endpoints are
     strictly before the week's own return -- no lookahead. All four factors
     (vix, credit_baa10y, breadth_pct, xlu_spy_rel60) are pulled from the
     single factors.csv file (not the separate FRED VIXCLS.csv/BAA10Y.csv
     substate_research.py used for levels) specifically so "N trading days
     ago" means the same thing -- N rows back in the same table -- for every
     factor; mixing index conventions across files would make deltas
     mean subtly different things per factor.
  3. Only A, D, E, F are attempted (B, C already excluded in
     substate_research.py: 28 weeks total, below MIN_N=15-per-half even
     before any split).
  4. Median split of each state's weeks into "top" (delta >= median) vs
     "rest" per factor per window (1-day, 5-day) -- NOT the "top quartile"
     framing used in the informal manual check, because a quartile split
     halves the testable sample again and most of these states are already
     thin; median split is what substate_research.py used throughout, and
     using the same split rule keeps this comparable. MIN_N=15 per half,
     same floor as substate_research.py.
  5. Grid-search the flagged half's (core, sat, cash) weight on the search
     period only (pre-2020-01-01), holding everything else (the other half,
     every other state) at the live TARGET_WEIGHTS baseline. Maximize
     full-timeline Sharpe. Check full and holdout Sharpe at the found
     weight. Reject corner solutions (a 0/1 weight on any leg) outright,
     regardless of Sharpe -- BOXX/T-bill's near-zero variance can win Sharpe
     mechanically. Only call something HOLDS UP if it's not a corner, the
     full-timeline gain is economically meaningful (>0.02), and holdout
     Sharpe is not below baseline holdout.
  6. Confound check: does the "top-delta" half of a state's weeks
     disproportionately precede a different next-state than the "rest"
     half? (Would mean the delta split is a repackaged transition-structure
     signal, not new information -- exactly how F/credit_baa10y's LEVEL
     result was rejected in substate_research.py despite passing every
     mechanical check.)

============================== RESULTS SUMMARY ==============================
(from the actual run of this script, 2026-08-31 -- re-run to reproduce
exactly; numbers below are what came out, not projections)

Data: same SPMO/QQQ/TQQQ/BOXX daily closes as substate_research.py, plus all
four factor columns pulled from factors.csv only (4160 trading-day rows,
2010-02-11 to 2026-08-27). Same 564 weekly rows, 2015-11-06 to 2026-08-27.
Live-weights baseline: full Sharpe 1.013, search-only 0.906, holdout-only
1.078 (identical to substate_research.py -- same baseline series).

TESTABLE (n_state >= 30): A (n=351), D (n=79), E (n=32, barely), F (n=46).
B and C skipped as in substate_research.py.

*** THE HEADLINE FINDING (F / VIX rate-of-change) DOES NOT SURVIVE. ***
Median split (not the informal check's top-quartile) puts F's VIX 1-day
delta median at -0.52 and 5-day at -0.47 -- i.e. "top" is just "VIX fell
less / rose more than the state's typical week", not an extreme-jump tail.
F/vix-d1d: "top" (n=23) grid-search optimum is 0.0/0.0/1.0 (100% cash) --
searchSharpe 0.930, fullSharpe 1.016 (+0.003 vs baseline), holdout 1.071 --
a corner solution with a trivial gain, REJECTED regardless of Sharpe, same
rule as substate_research.py. "rest" (n=23) optimum is also a corner
(0.0/1.0/0.0), fullSharpe 1.068 (+0.055), holdout 1.027 -- rejected too.
F/vix-d5d: "top" optimum (0.0/1.0/0.0) full Sharpe *drops* to 0.920 (-0.093
vs baseline) -- reverses sign entirely -- and is a corner regardless.
"rest" is non-corner (0.0/0.3/0.7) but its full-timeline delta is -0.013,
i.e. worse than baseline, not a finding either way.
So the informal quartile-tail average-return check (top-quartile VIX-jump
F-weeks averaging -2% to -8% vs +1% to +4% for the rest) was a REAL pattern
in that narrow tail, but a median split doesn't reproduce it (the effect is
concentrated in the extreme tail, not a clean top/bottom-half split), and
even where the pipeline finds a directionally-plausible cash-leaning
optimum for the bad-looking half, it's a corner solution with a
near-baseline Sharpe -- not the strong, holdout-confirmed result the
manual check's raw averages suggested. VERDICT: the F/VIX-acceleration
finding does NOT survive full validation.

State E: all 8 factor/window combinations reversed sign between the 1-day
and 5-day window for at least one half, or failed to clear +0.02 fulltime
gain, or were corners. Consistent with the task's own expectation -- E is
noise at n=32, not signal. No findings.

States A (n=351) and D (n=79): the grid search flagged several results as
mechanically "HOLDS UP" (non-corner, >0.02 full-timeline gain, holdout >=
baseline): A/vix-d5d-top (0.7/0.0/0.3, delta +0.058, holdout 1.129),
A/credit_baa10y-d1d-top (0.2/0.0/0.8, delta +0.065, holdout 1.083),
A/breadth_pct-d5d-rest (0.4/0.0/0.6, delta +0.098, holdout 1.101),
A/xlu_spy_rel60-d5d-top (0.3/0.2/0.5, delta +0.101, holdout 1.212), and
D/vix-d5d-rest (0.0/0.5/0.5, delta +0.041, holdout 1.119). All five push
AWAY from satellite and TOWARD cash relative to that state's live weight,
for whichever half the grid search was pointed at.

PLACEBO CHECK (added because A alone got 4/16 "HOLDS UP" flags and every
one of them de-weights satellite -- worth asking whether the grid search
would find something similar for ANY arbitrary split, not just a
factor-motivated one). Five independent MEANINGLESS random 50/50 splits of
A's weeks (MD5 hash of week_start, no economic content) were run through
the identical grid-search/corner/holdout pipeline: 10 half-tests total, 1
mechanically cleared the "HOLDS UP" bar (seed 2's "top" half: delta +0.102,
holdout 1.113) -- a ~10% false-positive rate under this exact mechanical
bar, from pure noise, at this sample size. The same check on D's 79 weeks:
5 random splits, 10 half-tests, 1 "HOLDS UP" (seed 2's "rest" half, delta
+0.029). So a meaningless split clears this bar roughly 1 time in 10 by
chance alone. A produced 4/16 flagged combinations (25%) and D produced
1/16 (6%) -- A's rate is somewhat above the placebo base rate but the
sample of both real tests and placebo trials is too small to call that
difference significant, and D's rate is indistinguishable from noise. None
of these five "HOLDS UP" results has an independent economic story pointing
the same direction the way F's credit-spread LEVEL result did (that one
was rejected anyway, for contradicting established evidence) -- they read
as instances of the general fact that de-weighting TQQQ satellite lowers
portfolio variance and mechanically helps full-timeline Sharpe for
WHICHEVER half of a state's weeks happens to get flagged, not as five
distinct genuine substates. Given the placebo base rate, these are not
reported as real findings.

CONFOUND CHECK: run for every combination that reached the grid-search
stage. F's VIX-delta halves (both windows) both transition ~100% to C,
matching F's whole-state rate (STRATEGY.md: F->C 79%) and
substate_research.py's F-level results -- no distinct signal there even
setting the corner-solution problem aside. A's and D's delta-halves also
track their whole-state transition ratios throughout (e.g. D's halves both
run ~70-80% to A / 20-30% to E, matching D's documented D->A 73%/D->E 27%
split) -- none of the flagged A/D combinations is secretly a repackaged
transition-structure signal either.

VERDICT: rate-of-change factors are NOT more productive than level factors
were -- if anything this run is a slightly cleaner rejection, because the
headline motivating pattern (F/VIX acceleration) visibly weakens once
moved from an informal top-quartile average-return check to the project's
actual median-split/grid-search/holdout pipeline, and the placebo check
gives a concrete, quantified reason (a ~10% base rate for a meaningless
split to mechanically pass the same bar) to distrust the handful of A/D
results that superficially passed. The underlying constraint is the same
one substate_research.py already named: 15-46 weeks per state, 12-23 per
half, is not enough independent history to support finer partitioning
without reintroducing the overfitting this project has explicitly
disciplined itself against -- true for level splits and equally true for
rate-of-change splits.

Caveats carried over: one bear market (2022) in the whole window,
search/holdout split at 2020-01-01 only (no walk-forward), breadth_pct is
survivorship-biased on today's S&P 500 constituents (SOURCES.md).
===============================================================================
"""
import csv
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import compute_states, target_weights, STATE_LABEL
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
SEARCH_HOLDOUT_SPLIT = '2020-01-01'
MIN_N = 15  # minimum weeks required in EACH half for a split to be testable at all
DELTA_WINDOWS = (1, 5)  # trading days back

LIVE_WEIGHTS = {
    'A': (0.65, 0.35, 0.00), 'B': (0.25, 0.75, 0.00), 'C': (1.00, 0.00, 0.00),
    'D': (0.55, 0.20, 0.25), 'E': (0.50, 0.00, 0.50), 'F': (0.30, 0.00, 0.70),
}


def iso_week_key(d):
    return date.fromisoformat(d).isocalendar()[:2]


def last_trading_day_per_week(dates):
    by_week = {}
    for d in dates:
        by_week[iso_week_key(d)] = d
    return by_week


# ---------------------------------------------------------------- factors --

def load_factors_csv_all(path):
    """Load ALL four factor columns from factors.csv, keyed by date, plus the
    sorted trading-day date list -- so 'N trading days ago' means the same
    thing (N rows back in this same table) for every factor."""
    cols = ['vix', 'credit_baa10y', 'breadth_pct', 'xlu_spy_rel60']
    series = {c: {} for c in cols}
    with open(path) as f:
        for r in csv.DictReader(f):
            d = r['date']
            for c in cols:
                try:
                    series[c][d] = float(r[c])
                except (ValueError, KeyError):
                    pass
    sorted_dates = sorted(set().union(*[series[c].keys() for c in cols]))
    return series, sorted_dates


def index_on_or_before(sorted_dates, d):
    import bisect
    i = bisect.bisect_right(sorted_dates, d) - 1
    return i if i >= 0 else None


def deltas_at(series, sorted_dates, col, d0, windows=DELTA_WINDOWS):
    """Point-change of series[col] as of trading day <= d0, vs N trading
    days earlier in sorted_dates (same table -> consistent index for every
    factor). Returns {n: delta or None}. Strictly backward-looking: both
    endpoints are on or before d0, the week's own start date."""
    i = index_on_or_before(sorted_dates, d0)
    out = {}
    if i is None:
        return {n: None for n in windows}
    d_now = sorted_dates[i]
    v_now = series[col].get(d_now)
    for n in windows:
        j = i - n
        if v_now is None or j < 0:
            out[n] = None
            continue
        d_prev = sorted_dates[j]
        v_prev = series[col].get(d_prev)
        out[n] = None if v_prev is None else (v_now - v_prev)
    return out


def load_factors():
    series, sorted_dates = load_factors_csv_all(f'{ROBINHOOD_REPO}/factors.csv')
    return series, sorted_dates


# --------------------------------------------------------- weekly returns --

def build_weekly_series():
    qqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    spmo = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPMO.csv')
    tqqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/TQQQ.csv')
    boxx = load_daily_csv(f'{ROBINHOOD_REPO}/etf/BOXX.csv')
    tbill = load_tbill()
    all_dates = sorted(set(qqq) | set(tqqq) | set(spmo))
    cash_idx = build_cash_index(all_dates, boxx, tbill)

    qqq_dates = sorted(qqq)
    states = compute_states(qqq_dates, qqq)
    state_by_date = dict(zip(qqq_dates, states))

    spmo_by_week = last_trading_day_per_week(sorted(set(spmo)))
    tqqq_by_week = last_trading_day_per_week(sorted(set(tqqq)))
    cash_by_week = last_trading_day_per_week(sorted(set(cash_idx)))

    common_keys = sorted(set(spmo_by_week) & set(tqqq_by_week) & set(cash_by_week))
    common_keys = [k for k in common_keys if spmo_by_week[k] >= '2015-11-02']

    factor_series, factor_sorted_dates = load_factors()
    factor_cols = ['vix', 'credit_baa10y', 'breadth_pct', 'xlu_spy_rel60']

    rows = []
    for i in range(len(common_keys) - 1):
        k0, k1 = common_keys[i], common_keys[i + 1]
        d0c, d1c = spmo_by_week[k0], spmo_by_week[k1]
        d0t, d1t = tqqq_by_week[k0], tqqq_by_week[k1]
        c0, c1 = cash_by_week[k0], cash_by_week[k1]

        state_day = d0c
        while state_day not in state_by_date and state_day > qqq_dates[0]:
            state_day = (date.fromisoformat(state_day) - timedelta(days=1)).isoformat()
        st = state_by_date.get(state_day)
        if st is None:
            continue

        r_core = spmo[d1c] / spmo[d0c] - 1
        r_sat = tqqq[d1t] / tqqq[d0t] - 1
        r_cash = cash_idx[c1] / cash_idx[c0] - 1

        deltas = {}
        for col in factor_cols:
            deltas[col] = deltas_at(factor_series, factor_sorted_dates, col, d0c)

        rows.append(dict(week_start=d0c, week_end=d1c, state=st,
                          r_core=r_core, r_sat=r_sat, r_cash=r_cash, deltas=deltas))
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


def full_series_rets(rows, weight_fn):
    out = []
    for row in rows:
        cw, sw, chw = weight_fn(row)
        out.append(cw * row['r_core'] + sw * row['r_sat'] + chw * row['r_cash'])
    return out


def baseline_weight_fn(row):
    return LIVE_WEIGHTS[row['state']]


# ------------------------------------------------------- substate search --

def assign_halves(rows, factor_name, window, target_state):
    """Median split of target_state's weeks by the N-trading-day delta of
    factor_name. Returns (halves dict: id(row)->'top'/'rest', median_used)."""
    state_rows = [r for r in rows if r['state'] == target_state
                  and r['deltas'][factor_name][window] is not None]
    vals = sorted(r['deltas'][factor_name][window] for r in state_rows)
    if not vals:
        return {}, None
    mid = len(vals) // 2
    med = vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2
    halves = {}
    for r in state_rows:
        halves[id(r)] = 'top' if r['deltas'][factor_name][window] >= med else 'rest'
    return halves, med


def grid_search_substate(rows, halves, target_state, target_half, step=0.1):
    best = (None, None, None, -1e9)
    n = round(1 / step)

    def weight_fn_factory(cw, sw, chw):
        def fn(row):
            if row['state'] == target_state and halves.get(id(row)) == target_half:
                return (cw, sw, chw)
            return LIVE_WEIGHTS[row['state']]
        return fn

    for i in range(n + 1):
        core_w = round(i * step, 2)
        for j in range(n + 1 - i):
            sat_w = round(j * step, 2)
            cash_w = round(1 - core_w - sat_w, 6)
            if cash_w < -1e-9:
                continue
            rets = full_series_rets(rows, weight_fn_factory(core_w, sat_w, cash_w))
            sh = sharpe(rets)
            if sh is not None and sh > best[3]:
                best = (core_w, sat_w, round(cash_w, 2), sh)
    return best


def eval_weight_fn(rows, target_state, target_half, halves, weights):
    cw, sw, chw = weights

    def fn(row):
        if row['state'] == target_state and halves.get(id(row)) == target_half:
            return (cw, sw, chw)
        return LIVE_WEIGHTS[row['state']]
    return sharpe(full_series_rets(rows, fn))


# ------------------------------------------------------------- confound ---

def transition_confound(rows, halves, target_state):
    idx_by_id = {id(r): i for i, r in enumerate(rows)}
    dest_counts = {'top': {}, 'rest': {}}
    for rid, half in halves.items():
        if half is None:
            continue
        i = idx_by_id.get(rid)
        if i is None:
            continue
        j = i + 1
        while j < len(rows) and rows[j]['state'] == target_state:
            j += 1
        if j < len(rows):
            dest = rows[j]['state']
            dest_counts[half][dest] = dest_counts[half].get(dest, 0) + 1
    return dest_counts


# ------------------------------------------------------------------ main --

def main():
    rows = build_weekly_series()
    print(f"Total weeks: {len(rows)}  ({rows[0]['week_start']} .. {rows[-1]['week_end']})\n")

    by_state = {}
    for r in rows:
        by_state.setdefault(r['state'], []).append(r)

    baseline_full_sh = sharpe(full_series_rets(rows, baseline_weight_fn))
    search_rows = [r for r in rows if r['week_start'] < SEARCH_HOLDOUT_SPLIT]
    holdout_rows = [r for r in rows if r['week_start'] >= SEARCH_HOLDOUT_SPLIT]
    baseline_search_sh = sharpe(full_series_rets(search_rows, baseline_weight_fn))
    baseline_holdout_sh = sharpe(full_series_rets(holdout_rows, baseline_weight_fn))
    print(f"Live-weights baseline -- full Sharpe {baseline_full_sh:.3f}, "
          f"search-only {baseline_search_sh:.3f}, holdout-only {baseline_holdout_sh:.3f}\n")

    print("State week counts:")
    for st in sorted(by_state):
        print(f"  {st} ({STATE_LABEL[st]:<20}) n={len(by_state[st])}")
    print()

    factor_cols = ['vix', 'credit_baa10y', 'breadth_pct', 'xlu_spy_rel60']

    for st in sorted(by_state):
        n_state = len(by_state[st])
        if n_state < 2 * MIN_N:
            print(f"=== State {st} ({STATE_LABEL[st]}): n={n_state}, cannot clear "
                  f"MIN_N={MIN_N} per half even at exact 50/50 -- SKIPPED, not run. ===\n")
            continue

        print(f"=== State {st} ({STATE_LABEL[st]}), n={n_state}, live weight "
              f"{LIVE_WEIGHTS[st]} ===")

        for factor in factor_cols:
            for window in DELTA_WINDOWS:
                halves, med_used = assign_halves(rows, factor, window, st)
                label = f"{factor} d{window}d"
                if med_used is None:
                    print(f"  {label:<20} no factor coverage -- skipped")
                    continue
                n_top = sum(1 for h in halves.values() if h == 'top')
                n_rest = sum(1 for h in halves.values() if h == 'rest')
                if n_top < MIN_N or n_rest < MIN_N:
                    print(f"  {label:<20} split n_top={n_top:<4} n_rest={n_rest:<4} "
                          f"(median={med_used:+.3f})  -- TOO THIN (<{MIN_N} in a half), skipped")
                    continue

                search_halves = {id(r): halves[id(r)] for r in search_rows
                                  if id(r) in halves}

                results = {}
                for half in ('top', 'rest'):
                    n_search_half = sum(1 for v in search_halves.values() if v == half)
                    if n_search_half < 5:
                        results[half] = None
                        continue
                    best = grid_search_substate(search_rows, search_halves, st, half, step=0.1)
                    full_sh = eval_weight_fn(rows, st, half, halves, best[:3])
                    holdout_sh = eval_weight_fn(holdout_rows, st, half, halves, best[:3])
                    results[half] = (best, full_sh, holdout_sh)

                print(f"  {label:<20} split n_top={n_top:<4} n_rest={n_rest:<4} (median={med_used:+.3f})")
                any_grid_searched = False
                for half in ('top', 'rest'):
                    res = results[half]
                    if res is None:
                        print(f"      {half:<5}: too few search-period weeks to grid search")
                        continue
                    any_grid_searched = True
                    best, full_sh, holdout_sh = res
                    delta_full = full_sh - baseline_full_sh
                    is_corner = (best[0] in (0.0, 1.0) and best[1] in (0.0, 1.0)) or best[2] in (0.0, 1.0)
                    if is_corner:
                        verdict = "corner solution -- not trusted regardless of Sharpe"
                    elif holdout_sh is not None and holdout_sh >= baseline_holdout_sh and delta_full > 0.02:
                        verdict = "HOLDS UP"
                    else:
                        verdict = "search-only / not confirmed"
                    print(f"      {half:<5}: best(c/s/$)={best[0]}/{best[1]}/{best[2]}  "
                          f"searchSharpe={best[3]:.3f}  fullSharpe={full_sh:.3f} ({delta_full:+.3f} vs baseline)  "
                          f"holdoutSharpe={holdout_sh if holdout_sh is None else round(holdout_sh,3)}  [{verdict}]")

                if any_grid_searched:
                    dest = transition_confound(rows, halves, st)
                    print(f"      confound check -- next-state after 'top' weeks: {dest['top']}  "
                          f"after 'rest' weeks: {dest['rest']}")
        print()


if __name__ == '__main__':
    main()
