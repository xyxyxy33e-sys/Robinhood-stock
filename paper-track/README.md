# paper-track script index

This directory has accumulated a lot of one-off research scripts across the
strategy's development. Not all of them are load-bearing. This README says
which ones STRATEGY.md's rationale actually depends on, versus which are
historical record of paths that were tested and rejected. If you're trying
to understand *why* the live weights are what they are, start with
STRATEGY.md, then the canonical scripts below -- don't assume every script
in this directory reflects current strategy.

## Live / canonical (imported by triggers or referenced by STRATEGY.md)

- **`state.py`** -- the strategy itself. `compute_states()`, `target_weights()`,
  `validate_weights()`, `circuit_breaker_check()`. Every live trigger calls
  into this file directly; nothing here is a reimplementation. `TARGET_WEIGHTS`
  is the single source of truth for per-state weights.
- **`wash_sale.py`** -- `flag_wash_sales()` / `summarize()`, used live every
  week to separate usable vs. wash-sale-deferred realized losses.
- **`consistency_check.py`** -- automated guard: `TARGET_WEIGHTS` sums to 1.0
  per state, `CORE_SPMO_FRAC`/`CORE_GLD_FRAC` sum to 1.0, and a helper to
  cross-check any hand-composed P&L figure against raw trade records before
  it goes in a report.

## Research that shaped the current design (results summarized in STRATEGY.md)

- **`four_leg_overlay.py`** -- the original QLD-as-second-satellite search
  (core/TQQQ/QLD/cash, 4 legs) that produced the per-state weights adopted
  2026-08-29.
- **`five_leg_xlu_search.py`** -- extended the search to 5 legs
  (core/TQQQ/QLD/xlu/cash) and found the E-state XLU allocation.
- **`sensitivity_study.py`** -- finer-grid robustness check on the 4/5-leg
  search results, run after the initial coarse search to make sure the
  chosen weights weren't a narrow local optimum.
- **`isolated_state_validation.py`** -- the strictest test in this project:
  validates a candidate state-specific leg using ONLY that state's own
  discontiguous weeks (cash weight fixed, not searched, to avoid the
  degenerate 100%-cash corner solution). This is what caught and rejected
  D/XLU after it had passed the two looser checks above, and confirmed
  E/XLU. Any new candidate leg should go through this before being adopted.
- **`calendar_year_report.py`** -- calendar-year backtest table vs.
  SPMO/QQQ/SPY, used to sanity-check the strategy's behavior year by year
  (not just aggregate Sharpe) before and after each design change.
- **`defensive_core_blend.py`** -- tests blending a candidate into the core
  weight (SPMO_frac/candidate_frac) rather than as a separate state-specific
  leg. SPY/SCHD/VYM/USMV/XLU all tested and rejected here in this role
  (superseded for XLU by the standalone-leg approach in
  `five_leg_xlu_search.py`), but this is the script (extended inline,
  2026-08-31) that found and confirmed the GLD 75/25 core blend actually
  live today -- load-bearing for that result, not just historical record.

## Research that shaped, then rejected, a candidate (kept for the record)

- **`gld_validation.py`** -- head-to-head isolated test of gold (GLD) vs.
  XLU as a STATE-E-SPECIFIC leg (XLU included as a free option in the same
  search grid, not just compared to the pre-XLU cash baseline). The search
  step itself picked XLU over GLD; GLD only "wins" on a holdout look-back,
  which the search→holdout discipline treats as a reject, not a finding.
  Do not confuse this with GLD's core-blend role above, which IS live --
  this script only tested and rejected GLD as a replacement/standalone leg
  in E. See STRATEGY.md's "What was tested alongside XLU and rejected".
- **`five_leg_search_all_candidates.py`** -- broad sweep across SPY, XLU,
  SCHD, VYM, USMV, BRK.B, GLD as candidate defensive/state-specific legs.
  Only XLU (state E) survived isolated validation as a standalone leg; kept
  for the record of what was tried and why the others were rejected in that
  role (GLD's core-blend role is separate, see above).
- **`substate_v2_check.py`**, **`a1a2_deepdive.py`**, **`a1a2_magnitude.py`**
  -- verification of an A1/A2 (QQQ realized-vol) and D1/D2 (RSP-vs-QQQ)
  substate proposal surfaced outside this project. A1/A2 showed a real but
  parameter-fragile signal that mostly reduced to "more average TQQQ
  leverage" once isolated from timing skill; D1/D2 failed on sample size and
  a search/holdout sign flip. Neither adopted.

## Historical record only -- rejected paths, not referenced by current STRATEGY.md

- **`backtest_overlay_etf.py`**, **`backtest_overlay_etf_totalreturn.py`**,
  **`backtest_overlay_mirror.py`**, **`backtest_topn_weekly.py`**,
  **`backtest_topn_weekly_totalreturn.py`** -- earlier backtests from when
  core was the 15-stock SPMO mirror rather than the SPMO ETF directly
  (mirror retired 2026-08-31). Kept for historical comparison
  (mirror-vs-ETF evaluation), not part of the live design.
- **`basket_turnover_corr.py`**, **`optimize_top1_states.py`**,
  **`substate_research.py`**, **`substate_research_deltas.py`** -- earlier
  exploratory work on the mirror basket's turnover/correlation and
  sub-state regime research, predating the current 6-state design's
  finalization. Not referenced by current STRATEGY.md.

## Data

- `../data/defensive_candidates/{SCHD,VYM,USMV,BRKB,GLD}.csv` -- price data
  fetched to test the defensive/core-blend candidates above (GLD is the one
  that's live, in its core-blend role; the rest were rejected). Kept
  alongside the scripts that consume them for reproducibility.
- `../data/defensive_candidates/RSP.csv` -- price data for the rejected
  D1/D2 substate check (`substate_v2_check.py`).
