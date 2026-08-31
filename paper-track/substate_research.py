"""Substate research: can any of the six A-F regime states be usefully split
into "high"/"low" halves by an external factor (VIX, credit spread, S&P 500
breadth, or utilities-relative-strength), such that a different (core,
satellite, cash) weight would be warranted for each half?

METHODOLOGY (mirrors optimize_top1_states.py / four_leg_overlay.py, the
project's established single-parameter isolated-search pattern):
  1. Weekly-rebalanced SPMO core + TQQQ satellite + BOXX/T-bill cash series,
     state assigned by compute_states() at the START of each week (the same
     day the factor snapshot is taken -- no lookahead).
  2. For each of the 4 factors x 6 states, split that state's weeks into
     "high"/"low" halves by the factor's value at week-start (median split,
     plus a fixed VIX>25 stress threshold tried separately). Flag any split
     with fewer than MIN_N=15 weeks in either half as untestable BEFORE
     computing anything -- this project has already documented (STRATEGY.md)
     that states B/C/E have only 28-32 weeks total, so a half-split leaves
     ~14-16 weeks per side, right at or below the noise floor.
  3. For splits with enough weeks in both halves, grid-search that
     state-half's own (core, sat, cash) weight ONLY on the search period
     (pre-2020-01-01), holding every other state AND the other half of the
     same state at the live TARGET_WEIGHTS baseline, maximizing FULL
     continuous-timeline Sharpe (not the isolated state-weeks alone, which
     degenerates to 100% cash -- confirmed in optimize_top1_states.py).
  4. Check full-timeline Sharpe and HOLDOUT-ONLY (post-2020) Sharpe at the
     found weight. A split is only reported as a real finding if it holds up
     on holdout -- this project has already been burned twice this session by
     search-only overfitting (four_leg_overlay.py's B/C/F results, and the
     joint 6-state grid search in STRATEGY.md, search Sharpe 1.446 ->
     holdout 0.579). A search-only win that reverses or craters on holdout is
     reported as "not real," not as tentative support.
  5. Confound check: for each split, compare the distribution of the state
     that follows each half's weeks (a proxy for "is this factor secretly
     just a repackaged version of the already-documented transition
     structure in STRATEGY.md, not new information").

============================== RESULTS SUMMARY ==============================
(from the actual run of this script, 2026-08-31 -- re-run to reproduce
exactly; numbers below are what came out, not projections)

Data: SPMO/QQQ/TQQQ/BOXX daily closes (paper-track's usual sources) +
VIXCLS.csv, BAA10Y.csv, and factors.csv's breadth_pct / xlu_spy_rel60
(/home/user/robinhood/data/kairos/). 564 weekly rows, 2015-11-06 to
2026-08-27, factor value taken at each week's start date (nearest prior
trading day if the factor series doesn't have that exact date -- no
lookahead). Live-weights baseline: full Sharpe 1.013, search-only 0.906,
holdout-only 1.078.

TESTABLE (n_state >= 2*MIN_N=30, so a 50/50 split can clear 15/side): A
(n=351), D (n=79), E (n=32, barely), F (n=46). NOT testable: B (n=28) and C
(n=28) -- both below the 30-week floor before any split is even attempted,
consistent with STRATEGY.md already flagging B's 4-episode/28-week sample as
"direction trusted, magnitude not." Even among the testable states, several
individual factor splits came out too thin to grid-search (e.g. D's
VIX>25 fixed threshold: 9 high-VIX weeks, below MIN_N; E and F's "high" half
under several factors had too few SEARCH-PERIOD weeks, even though the
full-history half cleared MIN_N) -- these are reported as untestable, not
run through the grid search.

RESULT: after correcting for two systematic false positives (see below),
ZERO factor/state combinations produced a substate weight that is both (a)
economically meaningful (>0.02 full-timeline Sharpe gain) and (b) not a
corner-solution artifact of the full-timeline-Sharpe objective.

False-positive pattern #1 -- CORNER SOLUTIONS. The full-timeline Sharpe
objective can improve markedly just by routing a substate's weeks toward
100% cash (or another 0/1 corner of the core/sat/cash simplex), because
BOXX/T-bill's near-zero variance mechanically lowers portfolio-wide vol
regardless of whether the underlying weeks are genuinely different. This
happened repeatedly and in BOTH directions within the same split (e.g. state
A split by credit_baa10y: the high-spread half's grid-search optimum moved
to 30/70/0 -- more satellite -- while the low-spread half's optimum moved to
0/0/100 cash; state A split by VIX: high-VIX optimum went to 100% cash while
low-VIX optimum went to more satellite). Opposite-corner "wins" on both
sides of the same split, for a state whose baseline (65/35/0) STRATEGY.md
already documents as "inside the noise floor of a shallow alternative
optimum," reads as the search finding slack in A's OVERALL weight, not two
distinct substates -- and A's credit-spread median split (thr~1.93) also
roughly bisects the timeline by calendar era (spread was structurally higher
pre-2019 than after), so "search vs. holdout" and "high-credit vs.
low-credit" are not cleanly separable for this factor -- an extra reason not
to trust it. These cases are reported below as corner solutions, not as
findings.

False-positive pattern #2 -- CONTRADICTS ALREADY-ESTABLISHED EVIDENCE. State
F split by credit_baa10y (n_high=23, n_low too thin for search-period grid
search) is the one combo whose numbers alone pass every check: search
Sharpe 1.024, full-timeline 1.101 (+0.088 vs baseline), holdout 1.150 (vs
baseline holdout 1.078), and it's not a 0/1 corner (best weight ~0/80/20).
It is NOT reported as a real finding, because the optimal weight it finds --
80% satellite during high-credit-spread F-weeks -- directly contradicts
F's independently, extensively tested result in STRATEGY.md ("satellite
strictly hurts, faster than E," confirmed across the full 0-100% sweep with
NO conditioning at all). F->C is 79% of F's transitions (STRATEGY.md); a
plausible mechanism is that high-BAA10Y-spread F-weeks are disproportionately
late in F's episodes, closer to the eventual bounce into C, so loading up on
satellite there captures a few large reversal weeks rather than a real,
tradeable-in-advance substate. With only 23 weeks and no economic prior
pointing this direction, this reads as overfitting wearing the holdout
check's clothing, not a confirmed result -- exactly the kind of "looked good
on search, don't actually trust it" case this file exists to name explicitly.

Every other combo across A, D, E, F fell into the third bucket:
"search-only / not confirmed" -- either the grid search found no
improvement worth acting on, the delta reversed sign or shrank to
sub-0.02 noise on holdout, or the "high" side had too few search-period
weeks to search at all (chiefly a problem for E and F, whose ~16-23-week
halves leave under a dozen pre-2020 weeks once split by date too).

CONFOUND CHECK -- for every combo, the distribution of the state that
follows a run of "high" vs "low" weeks was compared against STRATEGY.md's
documented transition structure (A->D 96%, D->A 73%/D->E 27%, F->C 79%,
etc). No combo showed the two halves funneling into meaningfully different
destination states -- e.g. D's VIX halves both transition ~75/25 to A/E,
matching the whole-state ratio; F's halves both go ~100% to C. So none of
these splits is secretly a repackaged transition-structure signal by THIS
particular check -- but with 15-40 weeks per half this check has limited
power, and it doesn't rule out the WITHIN-episode timing confound described
for F/credit_baa10y above (position inside an episode, not which state comes
next).

VERDICT: substating is NOT worth pursuing further. Only two states (A, D)
have enough weeks to split with any real per-cell sample size, and even
there every factor split that "won" did so via a mechanical cash-corner
effect, a calendar-collinear factor, or (F/credit_baa10y) a result that
contradicts already-established, independently-tested evidence for that
state. B, C, and (in practice) E and F don't have enough weeks to split at
all without falling below sample sizes STRATEGY.md already treats as too
thin at the WHOLE-STATE level. This is the same conclusion the B/C/F
fixed-weight search already reached this session, one level down: this
dataset does not have enough independent history below the six-state level
to support finer partitioning without reintroducing the overfitting this
project has explicitly disciplined itself against. Breadth's survivorship
bias (SOURCES.md: today's S&P 500 membership, not point-in-time) is a
further reason not to lean on any breadth_pct split even where the raw
numbers looked suggestive.

Caveats carried over from the rest of this project's work: one bear market
(2022) in the whole evaluation window, search/holdout split at 2020-01-01 is
the only validation used (no walk-forward), and breadth_pct is
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

def load_fred_csv(path, col):
    out = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            try:
                out[r['observation_date']] = float(r[col])
            except (ValueError, KeyError):
                pass
    return out


def load_factors_csv_column(path, col):
    out = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            try:
                out[r['date']] = float(r[col])
            except (ValueError, KeyError):
                pass
    return out


def value_on_or_before(series_sorted_dates, series, d):
    """Nearest available factor value on date d, or the most recent prior
    date if d itself isn't in the series (weekends/holidays/coverage gaps)."""
    import bisect
    i = bisect.bisect_right(series_sorted_dates, d) - 1
    if i < 0:
        return None
    return series[series_sorted_dates[i]]


def load_factors():
    vix = load_fred_csv(f'{ROBINHOOD_REPO}/VIXCLS.csv', 'VIXCLS')
    credit = load_fred_csv(f'{ROBINHOOD_REPO}/BAA10Y.csv', 'BAA10Y')
    breadth = load_factors_csv_column(f'{ROBINHOOD_REPO}/factors.csv', 'breadth_pct')
    xlu_rel = load_factors_csv_column(f'{ROBINHOOD_REPO}/factors.csv', 'xlu_spy_rel60')
    factors = {
        'vix': vix,
        'credit_baa10y': credit,
        'breadth_pct': breadth,
        'xlu_spy_rel60': xlu_rel,
    }
    sorted_dates = {name: sorted(series) for name, series in factors.items()}
    return factors, sorted_dates


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

    factors, factor_sorted_dates = load_factors()

    rows = []  # dict: week_start, week_end, state, r_core, r_sat, r_cash, factor values
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

        fvals = {}
        for name, series in factors.items():
            fvals[name] = value_on_or_before(factor_sorted_dates[name], series, d0c)

        rows.append(dict(week_start=d0c, week_end=d1c, state=st,
                          r_core=r_core, r_sat=r_sat, r_cash=r_cash, factors=fvals))
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
    """weight_fn(row) -> (core_w, sat_w, cash_w) for that row."""
    out = []
    for row in rows:
        cw, sw, chw = weight_fn(row)
        out.append(cw * row['r_core'] + sw * row['r_sat'] + chw * row['r_cash'])
    return out


def baseline_weight_fn(row):
    return LIVE_WEIGHTS[row['state']]


# ------------------------------------------------------- substate search --

def assign_halves(rows, factor_name, target_state, threshold=None):
    """Returns dict: id(row) -> 'high'/'low'/None (None = not target_state or
    missing factor value). threshold=None means median split within
    target_state's weeks; otherwise a fixed threshold."""
    state_rows = [r for r in rows if r['state'] == target_state and r['factors'][factor_name] is not None]
    vals = sorted(r['factors'][factor_name] for r in state_rows)
    if threshold is None:
        if not vals:
            return {}, None
        mid = len(vals) // 2
        med = vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2
        thr = med
    else:
        thr = threshold
    halves = {}
    for r in state_rows:
        halves[id(r)] = 'high' if r['factors'][factor_name] >= thr else 'low'
    return halves, thr


def grid_search_substate(rows, halves, target_state, target_half, step=0.1):
    """Vary ONLY target_state's target_half weeks; the OTHER half of
    target_state and every other state stay at LIVE_WEIGHTS. Maximizes
    full-timeline Sharpe over `rows` (the search-period rows passed in)."""
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
    """For each half, tabulate the STATE OF THE NEXT WEEK WHOSE STATE DIFFERS
    from target_state (i.e. the transition destination), as a coarse check
    for whether the factor split is really just a repackaged leading
    indicator of the already-documented transition structure."""
    by_row = {id(r): r for r in rows if r['state'] == target_state}
    idx_by_id = {id(r): i for i, r in enumerate(rows)}
    dest_counts = {'high': {}, 'low': {}}
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

    factors = ['vix', 'credit_baa10y', 'breadth_pct', 'xlu_spy_rel60']
    thresholds_to_try = {'vix': [None, 25.0]}  # None = median split; also try VIX>25 fixed stress threshold

    for st in sorted(by_state):
        n_state = len(by_state[st])
        if n_state < 2 * MIN_N:
            print(f"=== State {st} ({STATE_LABEL[st]}): n={n_state}, cannot clear "
                  f"MIN_N={MIN_N} per half even at exact 50/50 -- SKIPPED, not run. ===\n")
            continue

        print(f"=== State {st} ({STATE_LABEL[st]}), n={n_state}, live weight "
              f"{LIVE_WEIGHTS[st]} ===")

        for factor in factors:
            for thr in thresholds_to_try.get(factor, [None]):
                halves, thr_used = assign_halves(rows, factor, st, threshold=thr)
                if thr_used is None:
                    continue
                n_high = sum(1 for h in halves.values() if h == 'high')
                n_low = sum(1 for h in halves.values() if h == 'low')
                label = f"{factor}{'' if thr is None else f'>{thr}'}"
                if n_high < MIN_N or n_low < MIN_N:
                    print(f"  {label:<18} split n_high={n_high:<4} n_low={n_low:<4} "
                          f"(thr={thr_used:.2f})  -- TOO THIN (<{MIN_N} in a half), skipped")
                    continue

                # search-period halves only, for the grid search
                search_halves = {id(r): halves[id(r)] for r in search_rows
                                  if id(r) in halves}

                results = {}
                for half in ('high', 'low'):
                    n_search_half = sum(1 for v in search_halves.values() if v == half)
                    if n_search_half < 5:
                        results[half] = None
                        continue
                    best = grid_search_substate(search_rows, search_halves, st, half, step=0.1)
                    full_sh = eval_weight_fn(rows, st, half, halves, best[:3])
                    holdout_sh = eval_weight_fn(holdout_rows, st, half, halves, best[:3])
                    results[half] = (best, full_sh, holdout_sh)

                print(f"  {label:<18} split n_high={n_high:<4} n_low={n_low:<4} (thr={thr_used:.2f})")
                for half in ('high', 'low'):
                    res = results[half]
                    if res is None:
                        print(f"      {half:<5}: too few search-period weeks to grid search")
                        continue
                    best, full_sh, holdout_sh = res
                    delta_full = full_sh - baseline_full_sh
                    is_corner = best[0] in (0.0, 1.0) and best[1] in (0.0, 1.0) or best[2] in (0.0, 1.0)
                    # Deliberately conservative "held up" bar -- see docstring for why the
                    # weaker version of this check (any holdout >= baseline - noise) was
                    # dropped after manual review found it mislabeling corner solutions and
                    # counterintuitive-direction splits as confirmed. A split is only called
                    # HOLDS UP if the full-timeline gain is economically meaningful (>0.02,
                    # not just inside the noise floor other per-state sweeps in this project
                    # already documented as flat) AND holdout is not below baseline AND the
                    # weight isn't a 0/1 corner (which a low-variance full-timeline Sharpe
                    # objective can hand out mechanically regardless of real substate content).
                    if is_corner:
                        verdict = "corner solution -- not trusted regardless of Sharpe"
                    elif holdout_sh is not None and holdout_sh >= baseline_holdout_sh and delta_full > 0.02:
                        verdict = "HOLDS UP"
                    else:
                        verdict = "search-only / not confirmed"
                    print(f"      {half:<5}: best(c/s/$)={best[0]}/{best[1]}/{best[2]}  "
                          f"searchSharpe={best[3]:.3f}  fullSharpe={full_sh:.3f} ({delta_full:+.3f} vs baseline)  "
                          f"holdoutSharpe={holdout_sh if holdout_sh is None else round(holdout_sh,3)}  [{verdict}]")

                dest = transition_confound(rows, halves, st)
                print(f"      confound check -- next-state after 'high' weeks: {dest['high']}  "
                      f"after 'low' weeks: {dest['low']}")
        print()


if __name__ == '__main__':
    main()
