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
| Core | 75% SPMO ETF / 25% IAU (gold), fixed blend | SPMO-as-core changed 2026-08-31 from a 15-stock proportionally-weighted mirror (beats the mirror on every axis: Sharpe 1.065 vs 1.043, -30.4% vs -33.0% max drawdown; removes the weekly Invesco scrape, 15 positions, and core-side wash-sale tracking). Gold blended into the core the same day — see "The GLD core-blend addition (2026-08-31)" below. Live instrument switched GLD → IAU on 2026-09-01 (same-spot-price gold trust, lower 0.25% vs 0.40% expense ratio, and — the deciding factor — GLD is not fractional-tradable on this account, IAU is; see `state.py`'s `CORE_SECONDARY_INSTRUMENT` comment). Every GLD backtest number in this doc still applies: the two ETFs co-move within basis points. |
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

`target_weights(state)` returns this row — the base weights, unchanged since
2026-08-31. Since 2026-09-01, states A and D are further refined by the
**micro overlay** (below) via `target_weights_with_micro(state, micro_agrees)`
— call that instead of plain `target_weights()` in every live trigger now.
Either way, `validate_weights(state, core, tqqq, qld, xlu, cash)` must run
immediately after, before computing any dollar target or placing any order.
`WeightSanityError` = abort, do not trade, report the error.

### Micro overlay for states A and D (added 2026-09-01)

A second, faster classifier — `compute_micro_agreement()` in `state.py`,
the SAME six-state machine as the macro classifier but computed on 30/150-day
SMAs instead of 50/200 — refines two of the six states. `micro_agrees` = the
micro classifier currently reads A or B (a bool, computed the same way and at
the same cadence as the macro state, no lookahead):

| State | micro_agrees | Core | TQQQ | QLD | Cash | vs. base row |
|---|---|---|---|---|---|---|
| A | **True** | 88% | 12% | — | — | de-levered from 80/20 |
| A | False | 80% | 20% | — | — | unchanged |
| D | True | — | — | 70% | 30% | unchanged |
| D | **False** | 56% | — | 14% | 30% | shifted from QLD toward core |

B, C, E, F are never touched by the micro overlay — those splits were tested
and never had enough sample to validate (see below).

**Why this is live and nothing else from an extensive research pass is**:
of the whole session's exploration — MA-window sweeps (10/100, 20/100, other
pairs beat 50/200 alone but at 2-2.5x turnover, no cost model, not adopted on
its own), a from-scratch three-MA classifier (STACK×POSITION, rejected —
search-period Sharpe looked great, holdout got worse than plain 50/200, the
textbook overfitting signature), and an extensive "state-A confidence" line
(four independently-constructed signals — this same micro/macro agreement,
price vs 20-day SMA, QQQ's own realized-vol percentile, VIX percentile — all
mutually corroborating, ~75-80% pairwise overlap, each individually validated
on isolated holdout, then combined into a 4-signal majority-vote composite
that looked cleanest of all) — **only this one survived full-timeline,
cost-adjusted testing.**

The state-A confidence line is the cautionary tale worth remembering: every
piece of it validated on ISOLATED holdout (checking a candidate weight
against only that cell's own return variance), but a full-timeline,
cost-adjusted composite test (`paper-track/composite_turnover_cost.py`)
reversed all of it — live's unchanged 80/20 turned out to be the actual
full-portfolio optimum, because trimming state A's return in its most
confirmed weeks removes some of the portfolio's best Sharpe contribution,
invisible to an isolated-cell check. This micro overlay is the one exception
that was different in degree, not method — a much MILDER de-lever (88/12,
not the composite line's full 100/0) — and it was walked back to specifically
where a `paper-track/micro_macro_sweep.py`+lambda-interpolation frontier
found it still net-beneficial: `paper-track/turnover_cost_model.py` showed
net Sharpe 1.149 vs. live's 1.111 at the FULL micro-adjusted endpoint
(lambda=1.0: 90/10 core/TQQQ for A-agree, 70% core/30% cash for D-diverge —
more extreme than the table above). The lambda=0.8 blend actually used live
(the table above) is Pareto-BETTER than that lambda=1.0 endpoint on both
Sharpe (1.154 vs 1.149) and CAGR (21.86% vs 21.07%), for only slightly worse
MaxDD (-23.59% vs -21.98%) — the interpolation frontier's genuine sweet
spot, not either raw endpoint. Cost drag at the lambda=1.0 endpoint was LOWER than live's
despite more transitions (0.49pp/yr vs 0.74pp/yr), because most of the extra
transitions are small agree/diverge weight tweaks (~0.2 turnover fraction),
not full expensive state changes. Confirmed robust across a 2-15bps
transaction-cost sensitivity range. **Always re-verify any future refinement
of this kind at the full-timeline, cost-adjusted level before trusting an
isolated-cell result — that discipline is what separated this one live
change from the rejected composite that looked, in isolation, even better.**

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

**GLD (gold, tested 2026-08-31, after XLU was already live)**: the loose
full-timeline search (`paper-track/five_leg_search_all_candidates.py`) found
a state-E signal even larger than XLU's original one (+0.142 vs +0.043,
100% GLD corner) — big enough, given this project's history of oversized
loose-search signals turning out fake (D/XLU, E/BRK.B), to demand the
decisive test before touching anything live. Two isolated checks
(`paper-track/gld_validation.py`, `paper-track/isolated_state_validation.py`
extended to GLD): (a) against the pre-XLU baseline (50% core/50% cash), GLD
alone "holds up" (+17.3% holdout return, Sharpe 3.70, vs live's +4.5%/0.635)
— but that's the wrong comparison now that XLU is actually live; (b) run
head-to-head against XLU directly, with XLU included as a free option in the
same isolated search grid, the search step itself — using only state E's 13
pre-2020 search weeks, blind to the holdout — picked 100% XLU over GLD every
time. GLD only "wins" if you look at the 19 holdout weeks in hindsight and
pick the asset that did better there (+18.9% GLD vs +12.4% XLU, driven
mostly by one COVID week, 2020-03-20: XLU -17.1% vs GLD -2.2%) — exactly the
holdout-cherry-pick this project's search→holdout discipline exists to
reject. States A, B, D were also checked and GLD did not hold up in any of
them (live weights beat it on isolated holdout in each). **Verdict: GLD
rejected as a state-specific replacement/standalone leg** (it does not
belong in state E in place of or alongside XLU). It was tested again the
same day in a completely different role — blended into the core across
every state, not competing with XLU at all — and adopted there; see "The
GLD core-blend addition (2026-08-31)" below. Data cached at
`data/defensive_candidates/GLD.csv` for the record.

**Full calendar-year effect** (`paper-track/calendar_year_report.py`-style
check, run 2026-08-31): flips 2016 from -4.0% to +4.5%, improves 2022 from
-16.6% to -14.3%, every other year unchanged (states outside E don't
reference this leg). Cumulative return over the full 10.9yr window improves
from +1130.8% to +1305.4%.

**Caveat, carried forward, don't re-litigate**: this rests on state E's own
thin sample (32 weeks total, 19 in the isolated holdout) — the most-validated
speculative change in this file is still built on less independent history
than A or D. Revisit if E's live behavior ever looks off.

### The GLD core-blend addition (2026-08-31)

The core changed from 100% SPMO to a fixed 75% SPMO / 25% GLD blend, applied
identically in every state that has a nonzero core weight (`CORE_SPMO_FRAC`,
`CORE_GLD_FRAC` in `paper-track/state.py`). This is unrelated to GLD's
rejection as a state-E leg above — that test asked "can GLD replace or
compete with XLU as a state-specific defensive position" (no); this one
asks "does a small permanent gold sleeve inside the core improve the whole
portfolio's risk profile" (yes, modestly).

Unlike every other core-blend candidate tested before it (SPY, SCHD, VYM,
USMV — see "What was tried and rejected" below, all monotonically worse or
flat-to-worse on every metric including the two weak years), GLD improves
max drawdown **consistently in both halves of the data**, not just in
hindsight on holdout:

| Metric | 100% SPMO (prior) | 75/25 SPMO/GLD (live) |
|---|---|---|
| CAGR | 24.91% | 24.46% (-0.45pp) |
| Sharpe, full timeline | 1.065 | 1.110 (+0.045) |
| Sharpe, pre-2020 (search) | 0.967 | 0.966 (-0.001, noise-level) |
| Sharpe, post-2020 (holdout) | 1.123 | 1.191 (+0.068) |
| Max drawdown | -30.36% | -27.35% (+3.0pp better) |
| 2016 (weak year) | -4.0% | -3.8% |
| 2022 (weak year) | -16.6% | -15.4% |

The pre-2020 search-period Sharpe cost is negligible — the same
both-sides-hold-up pattern that validated E/XLU, not the holdout-only
pattern behind every rejected candidate (D/XLU, E/BRK.B, GLD-as-E-leg
above, the A1/D1 substate ideas below). Two honest caveats, not
disqualifying but worth carrying forward: (1) a meaningful share of the
full/holdout-period benefit comes from GLD's own large 2020 and 2025
rallies landing in years the core was already strong (added beta from a
second bull run, not pure downside cushioning) rather than repeatable
diversification value — don't expect the full effect to recur if gold goes
flat for a few years; (2) 90/10 and 50/50 blends were also tested (see the
weekly-report conversation record) — 90/10 costs almost nothing but buys
less protection, 50/50 buys more protection but the pre-2020 Sharpe cost
turns clearly negative (-0.023); 75/25 was chosen as the middle of that
dial, not because it's a local optimum the data singled out.

Rejected in the same core-blend role: SPY, SCHD, VYM, USMV (see below) —
none matched XLU's original core-blend result, let alone GLD's. Confirmed
tradable, fractional, in the live account (576391551).

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
4. **Compute in code, never hand-add** (added 2026-08-31, after a real
   incident) — any live financial figure derived by combining two or more
   other numbers (a "today's total," a "new cumulative," a period subtotal)
   must be computed programmatically from the raw records
   (`get_pnl_trade_history`, `get_realized_pnl`, etc.), never composed by
   hand in prose. On 2026-08-31 a weekly report's headline realized-P&L
   figures were hand-added and ended up double-counting a pre-existing
   loss, reporting both "today's total" and "new cumulative" wrong until an
   independent code-based recomputation caught it (see the weekly report
   artifact's correction note for that date). `paper-track/consistency_check.py`
   has a `check_pnl_sum(trade_pnls, expected_total)` helper for exactly this:
   sum the raw per-trade records and assert the result matches the account's
   own independently-reported aggregate before reporting either figure. The
   same file's `check_target_weights()` asserts every row of `TARGET_WEIGHTS`
   sums to 1.0, independent of `validate_weights()`'s per-run check — run it
   after any edit to `TARGET_WEIGHTS`. `check_core_blend_fracs()` does the
   same for `CORE_SPMO_FRAC`/`CORE_GLD_FRAC` — run it after any edit to the
   core blend. See `paper-track/README.md` for which scripts in that
   directory are load-bearing vs. historical record.

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
- **Dollar-based/fractional market orders placed outside regular hours get
  CANCELLED by the broker, not queued** (discovered 2026-08-31, the hard
  way — a real ~$15.2k after-hours SPMO sell sat as `state='cancelled'`,
  not `'queued'`, silently stalling the GLD migration until caught and
  fixed manually that evening). The earlier assumption in this file and
  the trigger prompts ("market closed → orders queue") was simply wrong for
  this order type. Both live triggers now handle this: use dollar-based
  market orders in regular hours as normal; outside regular hours, use
  whole-share LIMIT orders with `market_hours` set to `extended_hours` or
  `all_day_hours` at a marketable price, and always re-check order state
  after placing rather than assuming it filled or queued.
- **The 50/200-day SMA windows themselves have never been validated** --
  every other parameter here (per-state weights, QLD, XLU, GLD, the
  substate ideas) went through this project's search/holdout discipline;
  the classifier's own windows were just inherited from
  `research/leverage_ma.md`. A sweep (`paper-track/ma_window_sweep.py`,
  2026-08-31) found shorter pairs (10/100, 20/100) beat 50/200 on both
  search and holdout Sharpe simultaneously -- a real effect -- but at
  2-2.5x the state-transition rate, with no transaction-cost or
  wash-sale-drag modeling to check whether that edge survives real
  friction. Not adopted; would require re-optimizing every per-state
  weight against the new classifier's states, not just swapping the
  windows. See also `paper-track/three_ma_split_check.py` -- a third
  (20-day) MA usefully splits state A in one direction (de-lever once
  price is already confirmed above it) but not the other; partial,
  unconfirmed on its own. A genuine three-MA classifier (STACK x POSITION
  regime, `paper-track/three_ma_classifier.py`) was tried for 10/50/100
  and 50/100/200 and REJECTED for both -- search-period Sharpe looks much
  better (1.09 -> 1.8-2.1) but holdout Sharpe gets WORSE than the plain
  50/200 baseline (1.17 -> 0.95-1.00), the textbook overfitting signature
  from fitting many small independently-weighted cells. CAGR also drops
  hard (25.5% -> ~18%) and 10/50/100 more than triples the transition
  rate. Cleaner rejection than the two-MA sweep above -- this one fails
  the search/holdout check outright, not just a turnover-cost caveat.
  A gentler variant -- running a fast "micro" classifier (10/100) alongside
  the live "macro" one (50/200) in parallel, splitting each macro state by
  whether the two agree, rather than merging into one bigger state machine
  (`paper-track/micro_macro_agreement.py`) -- avoids the overfitting blowup
  (only 2 cells per state, not a cross-product) but nets out to a wash: two
  individually-real, holdout-confirmed signals (A when micro confirms;
  D when micro diverges) don't compose into a net full-timeline
  improvement once blended at micro=10/100 (Sharpe 1.124 vs live 1.138,
  CAGR down ~4pp, MaxDD better by ~6pp).

  A broader sweep of the micro pair itself (`paper-track/micro_macro_sweep.py`,
  2026-09-01) found the SAME two cells (A/agree, D/diverge) validate across
  every micro pair tried (9 windows) -- consistent, not fragile to exact
  parameterization -- and several pairs (30/100, 30/150) beat live 50/200 on
  full-timeline, search, AND holdout Sharpe SIMULTANEOUSLY, not the
  search-up/holdout-down pattern that sank the merged 3-MA classifier. Best
  (30/150): Sharpe 1.171 vs 1.138, search 1.140 vs 1.090, holdout 1.203 vs
  1.174, MaxDD -21.9% vs -29.7%, CAGR 21.6% vs 25.5% (real cost). Turnover
  ~50% higher than macro-only (16.7/yr vs 11.2/yr), much milder than
  10/100's ~25/yr. This is the strongest, best-behaved finding from the
  whole MA-window research line -- flagged as a serious candidate, not
  filed away, but NOT YET IMPLEMENTED: no transaction-cost/wash-sale-drag
  modeling at the higher turnover, only A and D are touched (B/C/E/F stay
  at live weights), and it would add a second classifier plus a doubled
  per-state weight table to state.py -- a real complexity increase.
  Revisit before adopting.

  Turnover-cost modeling done (`paper-track/turnover_cost_model.py`,
  2026-09-01): the objection does NOT hold up. At a calibrated 4bps
  one-way spread/slippage rate, the micro-30/150 design's annualized cost
  drag is LOWER than live 50/200-only (0.49pp/yr vs 0.74pp/yr) despite
  more total transitions, because most of the extra ones are small
  agree/diverge weight tweaks (~0.2 turnover fraction) rather than the
  old design's fewer-but-all-expensive full state changes (up to ~2.0
  turnover fraction). Net Sharpe: old 1.111, new 1.149 -- edge holds
  across a 2-15bps cost sensitivity range. The remaining open items before
  implementation: wash-sale drag isn't NAV-modeled (it's a tax-timing
  effect, reported only directionally), and it still needs the second
  classifier + doubled per-state weight table built into `state.py` and
  the live triggers.

  A follow-up (`paper-track/confident_a_leverage.py`, 2026-09-01) tested
  whether GATING extra leverage to only the confident (agree) weeks could
  push CAGR higher without the Sharpe cost -- the naive "lever up when
  confident" hypothesis. The data says the opposite: Sharpe improves
  monotonically as the agree-side TQQQ weight falls TOWARD ZERO (5 of 7
  micro pairs tested peak at 0% TQQQ / 100% core during agree weeks), not
  as it rises. Likely mechanism: leverage's edge comes from catching
  acceleration/inflection early in a trend, before both a fast and slow
  signal confirm it -- once both already agree the trend is mature, and
  TQQQ's decay increasingly outweighs its beta. Same trade-off shape as
  everything else here (CAGR falls right alongside Sharpe's improvement,
  21.15% -> 19.99% at the Sharpe optimum) -- does not unlock higher
  return without cost. Confirms this whole micro/macro family is a
  smoothing trade, not a return-boosting one.

  Three more independently-constructed signals converged on the SAME
  de-lever-when-confirmed direction for state A: price vs its own 20-day
  SMA (`paper-track/three_ma_split_check.py`), QQQ's own realized-vol
  percentile (a corrected re-read of `paper-track/a1a2_deepdive.py`'s
  actual blind-search result, not its originally-proposed weights), and
  VIX percentile. All four signals overlap substantially with each other
  (~75-80% pairwise agreement) and each validated a near-zero-TQQQ weight
  on ISOLATED holdout for its own "confident" majority. A 4-signal
  majority-vote composite (`paper-track/combined_confidence_signal.py`)
  made this even cleaner in isolation -- large samples (250-332 weeks),
  strong isolated-holdout confirmation at every vote threshold.

  **But the full-timeline, cost-adjusted test reverses all of it**
  (`paper-track/composite_turnover_cost.py`, 2026-09-01): live's unchanged
  80/20 core/TQQQ is the actual full-portfolio OPTIMUM. Sharpe declines
  MONOTONICALLY as the confident-weeks weight is de-levered away from
  80/20 (1.111 at 80/20 -> 1.054 at the fully de-levered 100/0), across
  every cost assumption tested. Mechanism: isolated-holdout validation
  checks a candidate weight against ONLY that cell's own return variance,
  which is blind to how those weeks interact with the rest of the
  multi-state portfolio. State A is the majority state and already
  contributes the strategy's steadiest return stream (mostly free of the
  worse drawdowns concentrated in D/E/F); trimming its return specifically
  in its most-confirmed weeks removes some of the portfolio's best Sharpe
  contribution -- a real full-timeline cost invisible to the isolated test.
  **Net verdict on the entire state-A confidence line of research
  (four converging signals, all corroborating in isolation): REJECTED.**
  This was the most thoroughly-investigated idea of the whole research
  effort and it is a clean rejection at the level that actually matters,
  not an ambiguous one. No live weights changed. The broader lesson,
  carried forward: isolated-cell validation is necessary (it catches
  corner solutions) but not sufficient -- always re-check any candidate
  change at the full-timeline, cost-adjusted level before trusting it.
