# Live strategy spec — Robinhood Agentic account (576391551)

Single source of truth for the SPMO core + TQQQ/QLD satellite + BOXX cash-gate
overlay. All three live triggers (Friday weekly, Mon–Thu daily, and any
one-time trigger) should point here for the "what and why" and keep their own
prompts to the "when and how" — mechanics and step order, not re-derived
rationale. This file is what to update when the strategy changes; the
triggers should need only small edits to stay in sync with it.

## Instruments

| Role | Instrument | Notes |
|---|---|---|
| Core | SPMO ETF, held directly | Changed 2026-08-31 from a 15-stock proportionally-weighted mirror. SPMO-as-core beats the mirror on every axis paired with the same satellite/cash overlay (Sharpe 1.065 vs 1.043 with current weights, -30.4% vs -33.0% max drawdown) and removes the weekly Invesco scrape, 15 positions, and core-side wash-sale tracking. |
| Satellite (3x) | TQQQ | Higher return, higher decay — volatility drag scales with leverage k as k(k-1), so TQQQ's decay coefficient (6) is 3x QLD's (2) |
| Satellite (2x) | QLD | Added 2026-08-31. Lower decay, better Sharpe/drawdown than TQQQ in every combination backtested, at the cost of lower raw CAGR. Confirmed tradable/fractional in the live account. |
| Defensive (state E only) | XLU (Utilities Select Sector SPDR) | Added 2026-08-31. Not a satellite, not blended into core — a standalone leg used only in state E, replacing what used to be E's 50% core allocation. The one candidate from an extensive defensive-instrument search (SPY, SCHD, VYM, USMV, BRK.B all tested and rejected) to survive three independent validation passes, including fully isolated single-state testing. ~0.08% expense ratio, cheaper than SPMO itself. Confirmed tradable/fractional (regular hours) in the live account. |
| Cash gate | BOXX (Alpha Architect 1-3 Month Box ETF) | Deliberate allocation, not idle buying power — tax deferral vs. a cash sweep/T-bill, which pay taxable interest every period. Its Section 1256 long-term blended rate does NOT apply here — every gated state runs weeks to months, so a BOXX sale is still short-term. |

Core is NEVER margined. All leverage is expressed through the TQQQ/QLD
satellite positions. XLU carries no leverage.

## Regime engine

Six-state classifier on QQQ (a market signal, not an asset-specific one —
tested and confirmed this beats classifying off SPMO's own moving averages):
50-day and 200-day SMA, price-vs-MA with a 1% hysteresis buffer (flags only
flip when price clears the MA by >1%, otherwise hold their previous value).
State = f(price>50dma, price>200dma, 50dma>200dma). Implementation:
`paper-track/state.py`, `compute_states()`.

| State | Definition | Label | Time in history (2010–2026 QQQ) |
|---|---|---|---|
| A | P>50, P>200, 50>200 | established uptrend | 60.4% |
| B | P>50, P>200, 50<200 | reclaim | 3.5% |
| C | P>50, P<200, 50<200 | bounce in downtrend | 4.2% |
| D | P<50, P>200, 50>200 | pullback in uptrend | 13.5% |
| E | P<50, P<200, 50>200 | breakdown | 4.2% |
| F | P<50, P<200, 50<200 | established downtrend | 14.3% |

## Target weights (core, TQQQ, QLD, XLU, cash) — `TARGET_WEIGHTS` in state.py

| State | Core | TQQQ (3x) | QLD (2x) | XLU | Cash (BOXX) | Effective exposure |
|---|---|---|---|---|---|---|
| A | 80% | 20% | 0% | 0% | 0% | 1.4x |
| B | 25% | 75% | 0% | 0% | 0% | 2.5x |
| C | 100% | 0% | 0% | 0% | 0% | 1.0x |
| D | 0% | 0% | 70% | 0% | 30% | 1.4x |
| E | 0% | 0% | 0% | 50% | 50% | 0.5x |
| F | 30% | 0% | 0% | 0% | 70% | 0.3x |

`target_weights(state)` returns this row. Every live trigger must call it —
never hand-derive weights — and must call `validate_weights(state, core,
tqqq, qld, xlu, cash)` immediately after, before computing any dollar target
or placing any order. `WeightSanityError` = abort, do not trade, report the
error.

### Why each row is what it is (short version — full backtests in the
evaluation artifact: https://claude.ai/code/artifact/e6cb7682-974a-442e-8efc-8de75a41a2d2,
plus `paper-track/four_leg_overlay.py` for the 2026-08-31 QLD update)

QLD joined TQQQ as a second satellite instrument 2026-08-31, after
`four_leg_overlay.py` searched each state's (core, TQQQ, QLD) split
independently against the prior TQQQ-only baseline, one state at a time,
full-timeline Sharpe as the objective, search period pre-2020-01-01 checked
against a 2020+ holdout. Only changes that held up on holdout were adopted:

- **A** (62% of weeks — largest state by far): satellite trimmed 35%→20%
  (still 100% TQQQ, QLD not used here), +0.030 full-timeline Sharpe,
  confirmed on holdout (1.116). Best-evidenced change in this update.
- **D** (13.5% of history, second-most after A): the single biggest
  structural change in the table — drops core AND TQQQ entirely for 70%
  QLD + 30% cash, +0.025 full-timeline Sharpe, confirmed on holdout (1.088).
  Moderate (not thin, not large) sample; flagged as the row most worth
  re-checking if D's live behavior ever looks off, given the size of the
  jump relative to the evidence base.
- **B, C, F**: four-leg search found "better" search-period weights for all
  three, but each made FULL-timeline Sharpe *worse* (-0.036, -0.069, -0.106
  respectively) — search-only overfitting, not adopted. Confirms rather than
  displaces their existing rationale (below).
- **E**: four-leg search's "best" was 100% cash — a corner solution (cash's
  near-zero variance trivially wins a Sharpe objective regardless of real
  foregone return, a recurring artifact in this project's search work) —
  rejected regardless of its Sharpe number. Superseded by the XLU update
  below, which changes E a different way (not more cash — a defensive
  equity leg instead of half of core).

Original (pre-QLD, TQQQ-only) per-state rationale, still operative for B, C,
F (E's is superseded, see above and below):

- **B**: every axis tested (satellite weight, core/cash split) points toward
  MORE leverage, monotonically, with no plateau found even at 80%
  satellite. Only 4 independent episodes in 16 years (22/16/30/29 trading
  days) — direction trusted, magnitude not. 25/75 is a deliberately
  conservative pick below the raw ~80% peak.
- **C**: monotonic — full deployment, no satellite, no cash, confirmed best
  on every axis tested.
- **F**: satellite strictly hurts, faster than E. Core/cash sweep found F's
  own max drawdown is COMPLETELY UNAFFECTED by F's weight across the full
  0-100% range — reducing exposure here is close to free efficiency, not a
  risk trade-off. 14.3% of history, third-most.

### The XLU update to state E (2026-08-31)

E's 50% core allocation was fully replaced with 50% XLU (utilities sector) —
cash unchanged at 50%. This is the single most-validated speculative change
in this file, having survived three independent passes where every other
candidate tested failed at least one:

1. **Five-leg search** (`paper-track/five_leg_xlu_search.py`): XLU added as a
   standalone leg (not blended into core), one state varied at a time
   against the live baseline, full-timeline Sharpe, search/holdout split.
   E: +0.043 Sharpe, holdout-confirmed (1.092). D also looked promising here
   (+0.020) but did NOT survive step 3 below — see the rejection note.
2. **Finer-grid robustness check**: E's peak is a narrow, single-asset
   corner (100% of the state-E-search grid's top results cluster near 100%
   XLU) — inherently narrow by construction, not necessarily fake, but
   flagged for extra scrutiny given this project's history with corner
   solutions.
3. **Isolated single-state validation**
   (`paper-track/isolated_state_validation.py`): the decisive test. Search
   and holdout computed using ONLY state E's own discontiguous weeks (13
   search weeks, 19 holdout weeks pre/post 2020-01-01), cash fixed at 50% to
   avoid the degenerate-cash-corner trap, NO anchoring to the rest of the
   portfolio's variance. Candidate (0 core / 0 TQQQ / 0 QLD / 50% XLU / 50%
   cash) beat the live weights (50% core / 50% cash) on isolated holdout:
   +7.5% return, Sharpe 0.873 vs live's +4.5%, Sharpe 0.635.

**What was tested alongside XLU and rejected**: SPY blended into core
(monotonically worse on every metric, including the weak years it was meant
to help — diversifying the core dilutes the momentum tilt the strategy
leans into). SCHD, VYM, USMV (all low-fee, 0.06-0.15%, dividend-quality/
low-vol factor tilts) blended into core AND as standalone state-specific
legs — all flat-to-worse, none matched XLU's magnitude even at a loose bar
(`paper-track/defensive_core_blend.py`,
`paper-track/five_leg_search_all_candidates.py`). BRK.B as a standalone leg
showed a real signal in E under method (1) but did NOT survive isolated
validation (3) — live weights beat it in isolation
(`paper-track/isolated_state_validation.py`). **D/XLU is the clearest
cautionary result**: it passed methods (1) and looked non-corner and
holdout-confirmed, but FAILED isolated validation — D's apparent gain was
an artifact of blending with the rest of the portfolio's variance, not a
real property of D's own weeks. D's weights are UNCHANGED from the QLD
update above.

**Full calendar-year effect** (`paper-track/calendar_year_report.py`-style
check, run 2026-08-31): flips 2016 from -4.0% to +4.5%, improves 2022 from
-16.6% to -14.3%, every other year unchanged (states outside E don't
reference this leg). Cumulative return over the full 10.9yr window improves
from +1130.8% to +1305.4%.

**Caveat, carried forward, don't re-litigate**: this rests on state E's own
thin sample (32 weeks total, 19 in the isolated holdout) — the most-validated
speculative change in this file is still built on less independent history
than A or D. Revisit if E's live behavior ever looks off.

### What was tried and rejected

A full joint grid search across all six states simultaneously (12 free
dimensions) found a config with better full-window Sharpe (0.988 vs 0.978)
but WORSE holdout Sharpe (0.949 vs 0.961) than what's live. Re-fitting the
same search using ONLY 2015-2019 data and checking 2020+ collapsed from
search Sharpe 1.446 to holdout Sharpe 0.579 — the worst result anywhere in
this evaluation. Free-form joint optimization overfits fast; every live
parameter here was set by single-state analysis with an economic story, not
blind search. Don't re-introduce unconstrained joint tuning.

Substate research (VIX/credit-spread/breadth/utilities-relative-strength,
both level and rate-of-change versions — `paper-track/substate_research.py`,
`substate_research_deltas.py`) tested whether any of the six states should be
split further by external market data. Nothing survived a corner-solution
check, a holdout check, AND a placebo check (random meaningless splits
cleared the same "looks like a finding" bar ~10% of the time by chance).
Below-state partitioning isn't supported by the available history — six
states is treated as the right granularity, not a stepping stone to a finer
one.

### Transition structure (context, not a trading rule)

States move through a loop, not randomly: A→D is 96% of A's transitions; D
forks to A (73%) or E (27%); E forks to D (55%) or F (45%); F→C is 79% of
F's transitions; C forks to B (56%) or F (44%); B→A is 69% of B's
transitions. No state jumps directly to its opposite (A never → F, F never →
A) — always transits through the middle. C is the highest-stakes junction:
near coin-flip odds (56/44) deciding between the two most opposite postures
in the whole table (B's 75% satellite vs F's 70% cash), a bigger weight swing
than any other transition. Tested whether a leading indicator (distance to
200dma at C's entry, or the state prior to C) could predict C's outcome in
advance — real-looking signal, but only 18 total C-episodes with overlapping
distributions; not enough to build a rule on. React to the confirmed
destination state, nothing more.

## Safety guards

1. **`validate_weights(state, core, tqqq, qld, xlu, cash)`** — every trigger,
   every run, right after `target_weights()`. Weights must sum to 1.0
   (±0.5%) and the state must be a valid letter. `WeightSanityError` →
   abort, report, do not trade.
2. **`circuit_breaker_check(actual_total_value, implied_total_value)`** —
   every trigger, before placing any order. `implied_total_value` = sum of
   each held position's quantity × live quote, reconstructed independently
   from `get_equity_positions` + `get_equity_quotes`. `actual_total_value` =
   `get_portfolio`'s own `total_value`. These are two views of the same
   number, not two predictions — a gap beyond 2% tolerance means a data
   error, bad fill, unaccounted position, or bug, not market volatility.
   `CircuitBreakerTripped` → abort, report, do not trade. This is
   deliberately NOT a "the market moved a lot" breaker — large moves are
   expected at up to 2.5x effective exposure and are the design working as
   intended, not a fault condition.
3. **Wash-sale flagging** — `paper-track/wash_sale.py`,
   `flag_wash_sales()` + `summarize()`, run on the strategy-era trade list
   whenever there's a loss-sale. Splits realized losses into usable vs.
   wash-sale-deferred; never report a deferred loss as reducing this year's
   tax liability. TQQQ resizes and BOXX buy/sell cycles are now frequent
   enough that wash sales are closer to the normal case than the exception.

## Cadence

- **Friday, 15:55 ET** — full weekly routine: compute state, rebalance
  everything (SPMO core + TQQQ/QLD satellite + BOXX), realized P&L +
  wash-sale report, update the weekly report artifact.
- **Monday–Thursday, 15:55 ET** — state-change check only. If the regime
  hasn't changed since yesterday's confirmed close: no action, no report, no
  artifact touch (expected outcome most days, ~8 transitions/year). If it
  has: rebalance immediately to the new state's target weights.
- Both use the SAME `target_weights()` / `compute_states()` / safety guards.
  Overlap is intentional and harmless: if the daily check already moved a
  position to target mid-week, Friday's diff just finds it there and trades
  nothing extra.

## Reports

- **Weekly report artifact**: https://claude.ai/code/artifact/292cb8f5-b3ad-4a07-a522-91f8d8049c14
  — running log, newest week at top, updated by every trigger that trades.
- **Evaluation artifact**: https://claude.ai/code/artifact/e6cb7682-974a-442e-8efc-8de75a41a2d2
  — full backtests, per-state sensitivity, search/holdout checks, the joint
  grid search failure, calendar-year tables.

## Known limitations (carry these into every report, don't re-litigate them)

- Every parameter here is fit on the same ~11-year SPMO window (16+ years
  for the QQQ-only regime signal). One real bear market (2022) in the
  strategy's own live-comparable history — n≈1 for the thing the whole
  design is supposed to protect against.
- B's weights (25/75/0) rest on 4 independent episodes. Trust the direction,
  not the magnitude.
- Complexity has grown faster than the account: six states × three legs ×
  wash-sale tracking × a tax-deferral instrument × three independently
  firing triggers × a monthly reconciliation check. Every added piece is
  something that can silently break. When extending this further, prefer
  editing this file and `state.py` over adding new standalone mechanisms.
