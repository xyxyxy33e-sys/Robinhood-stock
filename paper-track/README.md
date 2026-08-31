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
  per state, and a helper to cross-check any hand-composed P&L figure against
  raw trade records before it goes in a report.

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

## Historical record only -- rejected paths, not referenced by current STRATEGY.md

- **`defensive_core_blend.py`** -- tested blending a defensive instrument
  (XLU, SPY, SCHD, VYM, USMV) into the core weight rather than as a separate
  state-specific leg. Superseded by the standalone-leg approach in
  `five_leg_xlu_search.py` / `isolated_state_validation.py`.
- **`five_leg_search_all_candidates.py`** -- broad sweep across SPY, XLU,
  SCHD, VYM, USMV, BRK.B, GLD as candidate defensive/state-specific legs.
  Only XLU (state E) survived isolated validation; kept for the record of
  what was tried and why the others were rejected.
- **`gld_validation.py`** -- head-to-head isolated test of gold (GLD) vs.
  the currently-live XLU in state E (XLU included as a free option in the
  same search grid, not just compared to the pre-XLU cash baseline). The
  search step itself picked XLU over GLD; GLD only "wins" on a holdout
  look-back, which the search→holdout discipline treats as a reject, not a
  finding. See STRATEGY.md's "What was tested alongside XLU and rejected"
  for the full writeup.
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
  fetched to test the rejected defensive candidates above. Kept alongside
  the scripts that consume them for reproducibility.
