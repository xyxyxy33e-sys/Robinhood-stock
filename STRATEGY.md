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
| Core | 100% SPMO ETF (pure, no blend) | SPMO-as-core changed 2026-08-31 from a 15-stock proportionally-weighted mirror (beats the mirror on every axis: Sharpe 1.065 vs 1.043, -30.4% vs -33.0% max drawdown; removes the weekly Invesco scrape, 15 positions, and core-side wash-sale tracking). Gold was blended INTO the core (75/25 SPMO/gold) the same day, then moved OUT to a standalone leg on 2026-09-01 — see "Gold: from core-blend to standalone top-slice" below. Core is pure SPMO again as of that date. |
| Satellite (3x) | TQQQ | Higher return, higher decay — volatility drag scales with leverage k as k(k-1), so TQQQ's decay coefficient (6) is 3x QLD's (2) |
| Satellite (2x) | QLD | Added 2026-08-31. Lower decay, better Sharpe/drawdown than TQQQ in every combination backtested, at the cost of lower raw CAGR. Confirmed tradable/fractional in the live account. |
| Defensive (state E only) | XLU (Utilities Select Sector SPDR) | Added 2026-08-31. Not a satellite, not blended into core — a standalone leg used only in state E, replacing what used to be E's 50% core allocation. The one candidate from an extensive defensive-instrument search (SPY, SCHD, VYM, USMV, BRK.B all tested and rejected) to survive three independent validation passes, including fully isolated single-state testing. ~0.08% expense ratio, cheaper than SPMO itself. Confirmed tradable/fractional (regular hours) in the live account. |
| Gold — REMOVED | ~~IAU~~ | Standalone top-slice, live 2026-09-01, removed the same day by explicit user decision (not a backtest finding — see "Gold: removed 2026-09-01" below). `STANDALONE_GOLD_FRAC` is set to 0.0; the code path still exists (`target_weights_with_gold()`) but contributes nothing to live weights. |
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
2026-08-31 and still the right reference table for understanding each
state's RELATIVE risk posture. It is no longer what a live trigger should
call directly, though: two overlays apply on top, both added 2026-09-01.

**Live weights, what a trigger actually trades (gold REMOVED 2026-09-01 —
see "Gold: removed 2026-09-01" further below):**

| State | Core (SPMO) | TQQQ | QLD | XLU | Cash (BOXX) |
|---|---|---|---|---|---|
| A, micro agrees | 88.0% | 12.0% | 0% | 0% | 0% |
| A, micro diverges | 80.0% | 20.0% | 0% | 0% | 0% |
| B | 25.0% | 75.0% | 0% | 0% | 0% |
| C | 100.0% | 0% | 0% | 0% | 0% |
| D, micro agrees | 0% | 0% | 70.0% | 0% | 30.0% |
| D, micro diverges | 56.0% | 0% | 14.0% | 0% | 30.0% |
| E | 0% | 0% | 0% | 50.0% | 50.0% |
| F | 30.0% | 0% | 0% | 0% | 70.0% |

**A THIRD OVERLAY IS NOW LIVE ON TOP OF THIS TABLE — volatility targeting,
added 2026-09-01. The table below is no longer what a trigger trades; see
"Volatility targeting" for the function to call.**

Get this by calling `target_weights_with_micro(state, micro_agrees)`
(`state.py`). `target_weights_with_gold(state, micro_agrees)` still exists
and is safe to call — with `STANDALONE_GOLD_FRAC = 0.0` it returns this
exact same table plus an always-zero gold leg, so either function works;
`target_weights_with_micro()` is the simpler, more direct one now that gold
is out. `validate_weights(state, core, tqqq, qld, xlu, cash)` (5-leg) must
run immediately after, before computing any dollar target or placing any
order. `WeightSanityError` = abort, do not trade, report the error.

### Volatility targeting (added 2026-09-01) — the outermost overlay

**`target_weights_with_voltarget(state, micro_agrees, vol)` in `state.py` is
what live triggers must call.** It applies `target_weights_with_micro()` and
then scales the four risky legs (core/TQQQ/QLD/XLU) by

    multiplier = min(1.0, VOL_TARGET_PA / realized_vol)

putting whatever is freed into cash (BOXX). `vol` comes from
`realized_vol(dates, px, as_of=date)` on the **same QQQ series** used for the
state, as of the **same date** — 30 trading days (= 6.0 calendar weeks),
annualized. Pass `None` when history is short: the multiplier degrades to 1.0
and the weights are returned unscaled. Then run `validate_weights()` (5-leg)
before computing any dollar target. Live constants: `VOL_TARGET_PA = 0.20`,
`VOL_LOOKBACK_DAYS = 30`, `VOL_TARGET_CAP = 1.0`.

**`VOL_TARGET_CAP` must stay at 1.0** — de-lever only. `cap=1.5` was tested
and is worse where it matters: it levers up into the calm before a crash,
taking COVID from -16.2% to -22.3%. `consistency_check.check_voltarget_overlay()`
asserts the cap invariant, that cash never goes negative, and that a `None`/0
vol is a no-op rather than a portfolio wipeout.

**Why this and nothing else.** A 2026-09-01 search for a second defensive
layer went **0-for-6** — VIX level/change, credit spreads, breadth,
cross-asset ETFs, QQQ's own DMA slope/acceleration, and substate splits all
failed out-of-sample. The DMA-slope rule looked strongest until an
exposure-matched control showed ~2/3 of its edge was just holding more, and a
3.2x larger sample moved its p-value the wrong way (0.083 → 0.189). Vol
targeting is the one idea that survived, *because* it keys off realized
volatility rather than price-vs-MA, so it reacts in days rather than in
50/200-crossover time.

Validated on 2000-2026 (`voltarget_and_sp500_test.py`, QQQ-core proxy with
validated synthetic 2x/3x legs, net of 4bps):

| period | live | vol-target 20% |
|---|---|---|
| 2000-07..2015-10 (**OOS**) | 4.51% / 0.311 / -65.1% | **8.03% / 0.512 / -37.9%** |
| 2015-11..2026-08 (fitted) | 23.11% / 1.051 / -26.7% | 20.60% / 1.060 / -20.1% |
| **FULL 2000..2026** | 11.84% / 0.617 / -65.1% | **13.06% / 0.746 / -37.9%** |

Pareto-better on all three metrics over the full window, and it improves the
out-of-sample slice far more than the fitted one — the opposite of an overfit
signature. It passes the exposure-confound control: flat de-levering to the
same average beta returns only 4.45% with -60.4% MaxDD in the OOS slice.
Turnover is slightly *lower* than live. All 18 (lookback × target)
combinations tested beat live on Sharpe and MaxDD, so the decision is robust
to the parameter; 6-8wk is a flat plateau, and shorter is worse on every axis
at once.

On the **real** instruments (`voltarget_live_backtest.py`, SPMO era only —
the bull-dominated window where this overlay is expected to cost return):

| | CAGR | Sharpe | MaxDD |
|---|---|---|---|
| Live | 23.01% | 1.113 | -25.96% |
| **Live + vol target** | 20.46% | **1.133** | **-19.33%** |

Even here it improves Sharpe and cuts max drawdown by 6.6pp for 2.55pp of
CAGR. Nearly all of that cost is **2020 alone** (42.9% → 25.2%): it de-levered
into the COVID crash and was slow to re-lever for the V-shaped recovery.

**What it does NOT fix: COVID-style crashes.** A 5-week crash and 20-week
recovery is faster than any 6-week vol estimate. Its value is in *sustained*
declines — the dot-com goes from -54.7% to -28.6%. Do not expect crash
protection, and do not "fix" 2020 by shortening the lookback: that was tested
across 2-12 weeks and trades away more than it gains.

`VOL_TARGET_PA = 0.15` is the also-defensible drawdown-floor alternative
(full-period 11.71% / 0.757 / -28.3%) — a one-line change.

#### Rebalance drift band (replaces the per-leg trade threshold)

Vol targeting makes the target move a little **every day**, so the old "act
only on a regime change" daily rule no longer covers it, and trading on any
daily difference would rebalance ~250x/year. Live rule
(`needs_rebalance(target, held, regime_changed)` in `state.py`):

- **regime change → always rebalance**, whatever the drift. Never gated.
- **otherwise rebalance only when L1 drift > `REBALANCE_DRIFT_BAND` (0.03)**,
  where drift = Σ|target − held| over the 5 legs. Because the legs sum to 1.0,
  a 3% L1 drift ≈ *1.5 percentage points of the portfolio in the wrong leg*.

**The old per-leg "$100 or 0.3%" trade threshold is REMOVED** (2026-09-01,
user decision). When the band fires, every leg goes to target regardless of
trade size. Gating on how wrong the *whole portfolio* is, is the better
control; a per-leg minimum stacked on top would leave small legs permanently
adrift. Do not reintroduce one.

Band chosen in `paper-track/drift_band_test.py`, which runs a **daily**
simulation where held weights drift with realised returns between rebalances
— more honest than this repo's weekly backtests, which silently reset to
target every week and so assume free rebalancing. Performance is **flat across
the whole 2%–20% band range** (full-period CAGR 11.35–11.43%, Sharpe
0.665–0.669, MaxDD −41.4% to −42.5%), so the band is essentially free in
return terms and was picked on operational grounds:

| rule | rebal/yr | turnover/yr | CAGR | Sharpe | median gap | max gap |
|---|---|---|---|---|---|---|
| every day | 250 | 16.64x | 11.35% | 0.666 | 0 d | 0 d |
| band 2% | 52.4 | 15.92x | 11.35% | 0.665 | 1 d | 51 d |
| **band 3% (live)** | **42.5** | **15.77x** | **11.36%** | **0.665** | **2 d** | **74 d** |
| band 5% | 32.7 | 15.49x | 11.35% | 0.665 | 3 d | 93 d |
| band 8% | 26.9 | 15.28x | 11.42% | 0.667 | 3 d | 118 d |
| band 10% | 24.5 | 15.09x | 11.40% | 0.666 | 4 d | 128 d |
| weekly only | 66.1 | 15.48x | 11.35% | 0.668 | 3 d | 4 d |
| Friday uncond. + band intra-week | 75.9 | 15.87x | 11.37% | 0.667 | 3 d | 4 d |

**3% chosen (user decision, after briefly running 5%)** for tighter tracking:
max gap 74 days vs 5%'s 93, median 2 days vs 3, and it is the only band in the
range that *also* improves MaxDD (−42.1% vs −42.5%), at ~10 more
rebalances/year. **2% was considered and declined** — it adds ~20
rebalances/year over 3% for literally identical CAGR and Sharpe and a slightly
worse drawdown, and at a 1-day median gap it would trade most days.

The whole 2-10% range is one flat plateau on return (CAGR 11.35-11.42%,
Sharpe 0.665-0.667), so this constant is an **operational** choice about trade
frequency, not a return one. Costs the 4bps model does *not* capture — wash
sales, tax-lot fragmentation, and execution risk on every live order — are
what argue against going tighter, and are the real reason 2% was declined.
The eras disagree on the "best" band by margins inside noise (OOS prefers 10%,
the fitted window 5%) — a reason not to fine-tune further.

Long no-trade stretches are not a risk, because they happen where nothing is
happening: seven of the eight longest runs are state A at single-digit-to-low-
teens volatility with the market grinding up (e.g. 128 days Dec 2016-Jun 2017,
vol 8.7%, QQQ +17.9%). The median run is 3 days.

**Responsiveness check**, since a band could in principle make the strategy
sleepy exactly when it matters: traced through the COVID crash, the band
rebalances repeatedly and fast, walking the risky sleeve down
100% → 66% → 47% → 33% → 23% → 13% as realised vol went 14% → 79%. Every band
in the range catches the move — 10% fires 9 times in that window, 5% fires 12,
2% fires 17 — the tighter ones only add refinements, which is further evidence
the choice is operational rather than protective. Regime changes bypass the
band entirely, so state transitions are never delayed by it.

In this drift-aware daily model, vol targeting still beats no vol targeting
clearly — full period 11.43% / 0.669 / −41.6% vs **9.56% / 0.517 / −69.9%** —
though both CAGRs land below the weekly backtests, which is the free-rebalancing
assumption showing up. Treat the daily-model numbers as the more honest ones.

### Micro overlay for states A and D (added 2026-09-01)

A second, faster classifier — `compute_micro_agreement()` in `state.py`,
the SAME six-state machine as the macro classifier but computed on 30/150-day
SMAs instead of 50/200 — refines two of the six states. `micro_agrees` = the
micro classifier currently reads A or B (a bool, computed the same way and at
the same cadence as the macro state, no lookahead):

| State | micro_agrees | Core | TQQQ | QLD | XLU | Cash | vs. base row |
|---|---|---|---|---|---|---|---|
| A | **True** | 88% | 12% | — | — | — | de-levered from 80/20 |
| A | False | 80% | 20% | — | — | — | unchanged |
| D | True | — | — | 70% | — | 30% | unchanged |
| D | **False** | 56% | — | 14% | — | 30% | shifted from QLD toward core |

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
net Sharpe 1.107 vs. live's 1.094 at the FULL micro-adjusted endpoint
(lambda=1.0: 90/10 core/TQQQ for A-agree, 70% core/30% cash for D-diverge
— more extreme than the table above; D's base row is unchanged at 70%
QLD/30% cash, see "State D: QLD/XLU reweight, tried and reverted" below).
Re-run 2026-09-01 after fixing a BOXX data bug (`_strip_boxx_flat_stub()`
in `paper-track/backtest_overlay_etf.py` — BOXX's price feed was a flat
placeholder for all of 2022 before 2022-12-29, so every cash leg read a
fake 0% return that whole year instead of the real T-bill rate); the fix
raised both designs' CAGR (cash-heavy weeks now earn real 2022 yield) but
did not change which design wins or by roughly how much — new still beats
old on net Sharpe both before and after the fix. Cost drag at the
lambda=1.0 endpoint is LOWER than live's despite more transitions
(0.49pp/yr vs 0.74pp/yr), because most of the extra transitions are small
agree/diverge weight tweaks (~0.2 turnover fraction), not full expensive
state changes. Confirmed robust across a 2-15bps transaction-cost
sensitivity range. The lambda=0.8 blend actually used live (the table
above) was the genuine Pareto-sweet-spot at the time this overlay was
validated (better Sharpe AND CAGR than the lambda=1.0 endpoint, for only
slightly worse MaxDD) — that specific comparison predates the BOXX fix and
has not been re-run; the lambda=1.0-vs-old comparison above has been,
and the qualitative conclusion (0.8 is a genuine interior optimum, not an
endpoint) is not expected to flip from a cash-leg data fix that raises
every design's returns roughly in proportion. **Always re-verify any
future refinement
of this kind at the full-timeline, cost-adjusted level before trusting an
isolated-cell result — that discipline is what separated this one live
change from the rejected composite that looked, in isolation, even better.**

### State D: QLD/XLU reweight, tried and reverted (2026-09-01, user decision)

**Net outcome: state D stays at 70% QLD / 30% cash (unchanged from the
original table above).** The XLU tilt below was implemented, backtested at
the full-portfolio level, and reverted the same day once that backtest came
back — kept here as documented research, not as the live design.

State D's original 70% QLD / 30% cash split (above) was re-examined at the
user's request after the gold-removal research closed out, using a new
shared harness (`paper-track/state_isolated_test.py`) and a dedicated
deep-dive script covering a full 2D grid over QLD% x XLU% (cash as the
remainder).

The grid-wide "optimum" — QLD=0%, XLU=0%, cash=100% — is a **corner-solution
artifact**, not a real finding: search-period Sharpe 15.695, but holdout
CAGR only 2.98% and MaxDD -0.17%. Cash's near-zero variance trivially wins
a Sharpe objective regardless of real foregone return — the same failure
mode caught repeatedly elsewhere in this file (state E's four-leg search,
several rejected gold-search corners). Rejected outright.

Excluding that corner, the legitimate interior region is **QLD 10-30% / XLU
20-50% / cash ~30%**, consistent with the original per-state XLU-for-D
subagent finding from the broader parallel research pass.

An episode-by-episode check (28 distinct state-D episodes, 2015-2026,
grouped by >14-day gaps) comparing live (70/30 QLD/cash) against a
representative interior point (40% QLD/30% XLU/30% cash) found XLU only
helps in **9 of 28 episodes** — concentrated in the sharp drawdowns (Dec
2015, Oct 2018, Mar 2020 COVID, Jan 2022, Mar 2025, Feb-Mar 2026) — and
**hurts in the other 19**, mostly rally/recovery episodes where QLD's
leverage would have captured more upside. This is a genuine trade
(upside participation in the common case, for tail protection in the
uncommon one), not a free improvement — flagged to the user as such rather
than presented as a strict win.

User initially took the XLU-tilted side of that trade — 30% QLD / 40% XLU /
30% cash, the midpoint of the interior region — and it was briefly live in
`TARGET_WEIGHTS['D']` and the micro overlay's `_LIVE_D`/`_NEW_D`. A
full-portfolio backtest comparison (net of a 4bps turnover cost model,
2015-11 to 2026-08, 564 weeks) then showed the tilt costs CAGR and Sharpe
at the WHOLE-PORTFOLIO level, even though it improves state D's own
isolated performance:

| | Full-portfolio net Sharpe | Full-portfolio net CAGR | State D-only Sharpe | State D-only MaxDD |
|---|---|---|---|---|
| 70% QLD / 30% cash (original) | 1.113 | 23.01% | 1.611 | -12.04% |
| 30% QLD / 40% XLU / 30% cash (tilt) | 1.102 | 22.23% | **1.730** | **-8.59%** |

State D is only 13.5% of history (79 of 564 weeks), so an isolated
improvement there doesn't outweigh giving up upside capture in the 19-of-28
episodes (mostly rallies) where the tilt hurts, at the full-portfolio level.
**User reverted to 70% QLD / 30% cash** given this comparison. The interior
region and the isolated-state numbers above remain documented as a real,
evidenced option — not adopted, but not rejected as an artifact either;
revisit if state D's live behavior (or its share of history) changes enough
to shift this full-portfolio tradeoff. No live rebalancing trades were
placed for either the tilt or the revert — the account has been on 70%
QLD/30% cash for D throughout; per the user's standing instruction, trading
is deferred until the full portfolio design is finalized.

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
  structural change in the table — drops core AND TQQQ entirely for
  leverage + cash, +0.025 full-timeline Sharpe, confirmed on holdout (1.088)
  at the original 70% QLD / 30% cash split. Moderate (not thin, not large)
  sample; flagged as the row most worth re-checking if D's live behavior
  ever looks off, given the size of the jump relative to the evidence base.
  **Re-examined 2026-09-01** (an XLU tilt was tried and reverted the same
  day) — see "State D: QLD/XLU reweight, tried and reverted" below.
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

### The GLD core-blend addition (2026-08-31) — SUPERSEDED 2026-09-01

**Superseded the next day** by moving gold out of the core into a standalone
top-slice — see "Gold: from core-blend to standalone top-slice" further
below for why and the comparison data. Kept below as history: the
core-blend numbers are still real backtest results and the reasoning for
holding *some* gold at all still applies: only the *mechanism* (in-core
blend vs. standalone leg) changed, not the underlying case for gold
exposure. Core is pure SPMO again as of 2026-09-01.

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

### Gold: removed 2026-09-01 (user decision)

Gold is out of the live design entirely, by explicit user instruction —
not because the backtest evidence turned against it. `STANDALONE_GOLD_FRAC`
is set to `0.0` in `paper-track/state.py`; the code path
(`target_weights_with_gold()`, `validate_weights_6leg()`,
`TARGET_WEIGHT_LEGS_WITH_GOLD`) is kept intact, not deleted, in case gold
is reconsidered later — flip the constant back to reactivate it.

For the record, the same-day research trail below (kept as history, not
current design) never found a reason in the numbers to drop it: candidate
replacements were tested (BTAL, TLT, DBC, PDBC, KMLM — see
`paper-track/tlt_standalone_test.py`, `multi_candidate_test.py`,
`btal_downturn_test.py`), downturn-only variants of both gold and BTAL
were tested and rejected (concentrating a diversifier only in D/E/F
underperforms holding it flat everywhere, for every candidate tried),
alternate uses of the freed-up 20% were tested (extra cash, extra
leverage, extra core, both uniform and bucketed by offense/defense
regime — see `gold_removed_realloc.py`, `gold_removed_bucketed.py`,
`sensitivity_full.py`), and a full continuous-fraction sensitivity sweep
confirmed gold's chosen 20% sits on a genuine, non-overfit part of the
Sharpe surface. None of that changes the outcome here: this section
documents the design that was in place from 2026-09-01 (the standalone
top-slice) through its removal the same day, kept for continuity in case
the decision is revisited.

### Gold: from core-blend to standalone top-slice (2026-09-01, historical)

The in-core 75/25 SPMO/gold blend above had a structural flaw not visible
until checked directly: because `core_weight` is **0% in states D and E**
(`TARGET_WEIGHTS`), blending gold into the core meant gold exposure
silently dropped to **zero exactly in pullback and breakdown** — the states
where a safe-haven asset would matter most. Prompted by the user asking to
double-check the 25% weight (gold had just had a historically strong
decade, including +62.3% in 2025 alone — worth checking the case wasn't an
artifact of one outlier year), then to explicitly move gold outside the
core and re-evaluate.

**Standalone gold beat the in-core design on every metric, in every period
tested**, including the honest checks (excl-2025, pre-2020 search, 2020-24
holdout — not just the full-timeline number 2025 can inflate):

| Period | Best in-core Sharpe (25-30% of core) | Standalone Sharpe (20%, every state) |
|---|---|---|
| Full timeline | 1.183 | 1.244 |
| Excl. 2025 | 1.117 | 1.164 |
| Pre-2020 search | 1.151 | 1.247 |
| 2020-24 holdout | 1.128 | 1.154 |

**Isolation check** (is this gold-specific, or just generic de-risking?): a
standalone slice of plain **cash** at the same weight underperforms the
gold slice on both Sharpe and CAGR in every period — cash's MaxDD is
marginally better in isolation (zero volatility, expected), but gold's
extra return more than compensates on a risk-adjusted basis. Confirms real
diversification value, not a dilution artifact.

**Per-state weight optimization was tried and rejected** — classic
overfitting on thin per-state samples. States C and E "optimized" to a
nonsensical 0% with search-period Sharpe above 4.8 (corner-solution
artifacts from 10-13-week samples); states B, D, F all pushed to the grid
edge (40-50%); state F's holdout Sharpe **collapsed from 3.81 (search) to
0.058 (holdout)** — the same search-only-overfit pattern documented
elsewhere in this file. The full-timeline composite built from each state's
"optimal" weight looked best of everything tested (Sharpe 1.276) but
**lost to the simple uniform 20% weight on the one honest test** (2020-24
holdout: per-state 1.073 vs. uniform 20%'s 1.154) — reject per-state
weighting for the same reason every other search-only-overfit result in
this file was rejected.

**A defensive tilt (more gold in D/E/F than A/B/C) was also tried and
rejected** — the user's own hypothesis, tested directly and refuted by the
data. A 2D grid over (offense weight, defense weight) found the Sharpe
surface ridges along **offense ≈ defense**, not toward extra defense
weight — at every offense level tested, the best-performing defense weight
was statistically indistinguishable from just using the same weight as
offense. Every deliberately defense-tilted combination underperformed the
flat/uniform version at the same total gold budget on the honest 2020-24
holdout (0% offense / 35% defense, the most extreme tilt tested, scored
worst of everything: holdout Sharpe 1.099 vs. uniform 20/20's 1.154).
Reason: offense states (A/B/C) are 407 of 564 weeks — most of the
timeline — so starving them of gold to concentrate it in the 157
defense-state weeks removes diversification value during the majority of
history to fund a bigger position during the minority.

**Weight chosen: 20%** (`STANDALONE_GOLD_FRAC` in `paper-track/state.py`).
15% was also defensible (same flat-plateau shape held up in every check),
but 20% strictly dominated it — better Sharpe, CAGR, AND MaxDD in every
single period tested, no tradeoff either way.

**Mechanism**: `target_weights_with_gold(state, micro_agrees)` composes the
micro overlay with this — every leg from `target_weights_with_micro()` is
scaled by 0.80, and gold added at a flat 0.20, in every state, every time.
This is the function live triggers call now; `validate_weights_6leg()` is
its matching guard (6 legs: core, tqqq, qld, xlu, gold, cash).

**One caution carried forward, same as the in-core version's**: this
backtest window is an unusually strong decade for gold. Even the honest
2020-24 holdout keeps showing "more gold is better" as weight rises past
40% — treat that climb skeptically rather than chasing it; it likely
reflects gold's trailing tailwind more than a structural edge that will
persist at arbitrarily high weights. 20% was chosen from the flat,
well-evidenced part of the curve, not the extrapolated tail.

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

State F substate on 50dma SLOPE (2026-09-01) — rejected, and the
investigation produced a MORE IMPORTANT correction, below. A search for
factors predicting the direction of individual state-F weeks (bucketed as
big-up >=+3%, big-down <=-3%, mild) tested, in order: 14 cross-asset ETFs,
VIX, credit spreads, breadth, rates, and finally ~20 moving-average
relationships (distances, MA-vs-MA spreads, slopes, acceleration,
vol-normalised distances, death-cross age). Only the 50dma's SLOPE (its
20-day rate of change) looked promising: steeper decline preceding bigger
bounces, a capitulation/mean-reversion story. It appeared to survive
search/holdout, episode breadth (11 of 14), exclusion of 2022, and
parameter-insensitivity. **It was still wrong**, for two reasons worth
remembering:
  1. EXPOSURE CONFOUND. Ranking the 50dma slope against its own trailing
     2-year distribution splits state-F weeks 55/7, not ~50/50 -- inside an
     established downtrend the 50dma is almost always falling relative to a
     window dominated by uptrend weeks. So the "rule" was really "hold 60%
     core in 89% of F weeks", averaging 54% exposure vs the live 30%. Most
     of its apparent edge was simply holding more, not signal. ALWAYS
     exposure-match before crediting a conditional weight rule -- and note
     that an "inverted rule performs badly" sanity check proves NOTHING
     under this confound (inverting also halves average exposure).
  2. IT DIED ON MORE DATA. See below.

**The 2015+ backtest window was hiding both bear markets (found 2026-09-01).**
Every state-F number in this file and in the evaluation artifact was computed
on data starting 2015-11 (SPMO's inception, which caps the *strategy*
backtest). But a factor/state study needs only QQQ daily closes, so it can run
much further back. `data/qqq_long_history.csv` now holds a merged QQQ daily
series from **1999-09-15** (fetched via get_equity_historicals, splice
verified against the existing 2009+ kairos series across 102 overlapping days
at a price ratio of exactly 1.000000). Re-running state F on it:

| | 2009-2026 (what everything above used) | Full 1999-2026 |
|---|---|---|
| F weeks / episodes | 62 / 14 | **197 / 28** |
| QQQ compounded over F weeks | **+17.5%** | **-39.4%** |
| big_up / big_down / mild | 20 / 14 / 28 | 50 / 58 / 89 |

The post-2015 window contains no sustained bear market except 2022 -- it
excludes the 2000-02 dot-com crash and the 2008-09 GFC, i.e. exactly the
episodes state F exists for. On the real history QQQ *loses* ~39% cumulatively
across F weeks and big-down weeks outnumber big-up ones. Any framing of
"state F underperforms QQQ, why so defensive" is an artifact of the truncated
sample; F's 30% core / 70% cash is validated much more strongly than the
2015+ numbers suggest, and the risk/return frontier computed for F on the
short sample understates the case for staying defensive. The slope signal
itself also died here: permutation p went the WRONG way with 3.2x the data
(0.083 -> 0.189) and episode breadth flipped from 11-helped/2-hurt to
11-helped/15-hurt. A real effect strengthens with more data.

**Standing lesson: before trusting any state-level statistic, check whether
the sample window contains the market conditions that state is meant to
handle.** Use `data/qqq_long_history.csv` for anything that only needs QQQ
prices (state classification, regime statistics, signal research); the
2015-11 floor is only binding where SPMO/QLD/XLU/BOXX leg returns are needed.

### 26-year stress test: the design has a -65% drawdown in it (2026-09-01)

`paper-track/long_history_backtest.py` runs the LIVE weights (same
`target_weights_with_micro`, same 4bps cost model, weekly rebalance) from
2000-07 to 2026-08 by substituting instruments that have long history:
QQQ total return as the core, SYNTHETIC 2x/3x for QLD/TQQQ, real XLU, and
3-month T-bill as cash. The synthetic leverage is validated against the real
funds over their full overlap -- TQQQ real CAGR 42.22% vs synthetic 42.14%
(gap -0.08pp/yr), QLD 35.01% vs 34.63% (-0.39pp/yr) -- using a single
0.6%/yr underlying-income term that is approximately QQQ's real dividend
yield and fits BOTH the 2x and 3x fund, which a fitted fudge factor would
not. Run with `--validate` to re-check. **Caveat: core is QQQ, not SPMO, so
read this as a test of the REGIME MACHINERY, not of the live design's
absolute returns.**

| period | strat CAGR | QQQ CAGR | strat Sharpe | strat MaxDD |
|---|---|---|---|---|
| 2000-07..2015-10 (**100% out-of-sample**) | 4.51% | 1.79% | 0.311 | **-65.11%** |
| 2015-11..2026-08 (the fitted window) | 23.11% | 19.24% | 1.051 | -26.75% |
| Full 2000..2026 | 11.84% | 8.67% | 0.617 | **-65.11%** |

Two findings, pulling in opposite directions.

**The good one: the regime machinery survives genuine out-of-sample data.**
Every per-state weight in `state.py` was fit inside the 2015-11+ window, so
2000-2015 is data no parameter has ever seen. Over it the strategy still beat
QQQ on CAGR (4.51% vs 1.79%) and Sharpe (0.311 vs 0.196), and it cushioned
every real bear: dot-com -54.7% vs QQQ's -72.8%, GFC -28.1% vs -38.3%, 2022
-17.6% vs -28.8%. That is meaningful validation -- the design is not merely
an artifact of the window it was fit in.

**The bad one: max drawdown is -65%, not -26%.** Every drawdown figure
elsewhere in this file comes from the 2015-11+ window and is roughly
2.5x too optimistic about the worst case. The dot-com decline alone takes
this design down -61.9% peak-to-trough. Anyone reading "-25.96% MaxDD" as
the risk of this strategy is reading a number produced by a sample with both
century-defining bear markets removed.

Two specific failure modes the recent window also hides, both WHIPSAW rather
than trend:
  - **2011: strategy -22.2% while QQQ was +4.1%** -- a 26pp underperformance
    in an UP year. The classifier churned all six states (A:20 B:5 C:2 D:9
    E:7 F:9 weeks) through the Aug-2011 crash/recovery, repeatedly
    de-risking into lows and re-levering into highs.
  - **COVID 2020: strategy -15.9% vs QQQ -7.1%** -- same mechanism, a crash
    too fast for a 50/200 classifier to help, then a recovery it was too
    slow to rejoin.
Both are the known cost of trend-following: it pays for protection against
sustained declines with losses in sharp round trips. The 2015-11+ window
contains one clean trend-bear (2022) and so shows mostly the benefit.

The state mix also differs materially, which is why the recent window
flatters the design: state F was 8.2% of the fitted window but 15.2% of the
full history, and state A 62.2% vs 52.2%. The recent era simply had more
established uptrend and less established downtrend than the long run.

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
   same for `CORE_SPMO_FRAC`/`CORE_GLD_FRAC` (now 1.0/0.0 — core is pure
   SPMO since gold moved to a standalone leg 2026-09-01) — run it after any
   edit to the core blend. `check_gold_overlay()` asserts every
   (state, micro_agrees) combination from `target_weights_with_gold()` sums
   to 1.0 — run it after any edit to `STANDALONE_GOLD_FRAC` or the micro
   overlay weights. See `paper-track/README.md` for which scripts in that
   directory are load-bearing vs. historical record.

   **BOXX data bug, found and fixed 2026-09-01**: BOXX's price feed
   (`/home/user/robinhood/data/kairos/etf/BOXX.csv`, pulled via
   `get_equity_historicals`) was a flat placeholder (100.0301) for every
   date from 2022-01-03 through 2022-12-28 -- not real price data; BOXX's
   actual listing predates the reliable part of that feed and the vendor
   backfilled a constant stub before it. `build_cash_index()` only falls
   back to the T-bill rate when a date is genuinely MISSING from BOXX's
   history, so this stub silently made every cash leg read a fake 0%
   return for all of 2022 instead of the real ~1.6-2%+ T-bill yield that
   year (rates were rising fast). Backtest-only -- live trading pulls
   real-time quotes, not this historical file, so no live trade was ever
   affected. Fixed in `paper-track/backtest_overlay_etf.py`'s
   `load_daily_csv()` via `_strip_boxx_flat_stub()`, which every script in
   this directory that loads BOXX.csv picks up automatically (all of them
   import `load_daily_csv` from that one module). Effect on results: small
   and mostly confined to 2022 and to cash-heavy states (F's isolated
   annualized return moved from 8.2% to 9.2%, Sharpe 1.081 to 1.211;
   full-strategy net Sharpe moved from 1.098 to 1.113) -- it did NOT
   reverse any design conclusion in this file (the state D revert, the
   micro overlay's edge over the old design, gold's removal) when
   re-checked against the fix.

## Drawdown-from-high watch (added 2026-09-01)

Informational only — never gates or triggers a trade. The user funds this
account with occasional manual deposits (transferred by hand, not
automated) and wanted an objective signal for "is this a real dip worth
adding extra money to," rather than reacting to any single red day. A
single day's move is too frequent to be useful: QQQ alone has closed down
≥2% ~14x/year historically (1.3% daily stdev, so a -2% day is only ~1.5σ).
Cumulative drawdown from a rolling high is far rarer and a more meaningful
signal — the strategy's own 2015-2026 backtested daily series (state-
weighted, not raw QQQ) crossed -5% off its 52-week high ~2.5x/year, -10%
~1.4x/year, -15% only 3 times in 10.9 years (Dec 2018, Mar 2020, Mar
2023), -20% exactly once (the Mar 2020 COVID crash).

Mechanism (`paper-track/drawdown_tracker.py`): the daily trigger computes
the STRATEGY's own daily return every day it runs (yesterday's confirmed
state's weights, from `target_weights_with_voltarget` (CHANGED 2026-09-01
from `target_weights_with_micro` — the tracker must describe the portfolio
actually held, or it alerts on drawdowns the account never had; vol targeting
cuts full-period MaxDD from -69.9% to -41.6%, so an un-vol-targeted series
fires the -5%/-10% tiers earlier and more often than reality), dotted with
that day's official-close-to-close leg returns — SPMO/TQQQ/QLD/XLU/BOXX; gold/IAU
removed 2026-09-01, no longer part of this), and
appends it to a small local log (`data/live_nav_index.csv`) via
`record_return(date, daily_return)`. This builds an independent,
cash-flow-blind return index — deliberately NOT the account's raw
`total_value`, so that a manual deposit never itself looks like a new high
or distorts the reading. `current_drawdown()` compares the latest index
value to its rolling 252-trading-day high (or all-time high, until the log
has a year of history — it started empty 2026-09-01, so this runs as an
all-time-high tracker through roughly September 2027). Thresholds checked:
**-5%** (low-conviction "worth a look," included at the user's request
despite being the noisiest tier — ~2.5x/year in backtest), **-10%** (worth
a modest add), **-15%** and **-20%** (rare, genuinely major dislocations).
`newly_crossed()` fires only the FIRST day a threshold is breached, not
every day the account stays below it, so this alerts once per episode, not
daily during a drawdown.

Separately, at the user's explicit request, a single-day move of **-2% or
worse** in the strategy's own daily return (the same number computed for
the log above) is ALSO flagged every time it happens — this one is NOT
deduplicated like the cumulative-drawdown tiers, since each such day is its
own event, not a sustained episode. Per this session's own check, this is
a genuinely frequent occurrence (~10x/year for the strategy's own
state-weighted series, ~14x/year for raw QQQ) — the user was told this
explicitly and asked for it anyway, so treat every occurrence as
low-conviction "FYI" framing, not an escalation.

**Push notifications** (added 2026-09-01, at the user's explicit request):
both live triggers call the `PushNotification` tool — a real interrupt to
the user's phone/desktop, not just text in the session transcript — for
three specific events, and only these three: (1) any regime shift (macro
state change, or a micro-agreement flip within states A/D), (2) a newly
crossed drawdown-from-high tier (-5/-10/-15/-20%), (3) any single day at
-2% or worse. Every other routine event (no-change days, ordinary weekly
reports) stays as in-session/artifact reporting only — pushing for those
would defeat the purpose by making the signal-to-noise ratio worse.

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
  design is supposed to protect against. **This is not a footnote — it
  actively distorts state-level statistics.** Demonstrated 2026-09-01: on
  the 2015+ window QQQ *gains* +17.5% across state-F weeks, but on the full
  1999-2026 history (`data/qqq_long_history.csv`) it *loses* -39.4%, because
  the short window excludes the 2000-02 and 2008-09 bears. Anything that only
  needs QQQ prices should be re-checked on the long series before it is
  believed — see "What was tried and rejected" for the full write-up.
- **The real max drawdown is about -65%, not the -26% quoted from the
  2015-11+ backtest.** `paper-track/long_history_backtest.py` runs the live
  weights over 2000-2026 (QQQ core, validated synthetic 2x/3x legs): MaxDD
  -65.11%, driven by the dot-com decline (-61.9% peak-to-trough). Quote
  -26% as "max drawdown in the SPMO-era window", never as the strategy's
  worst case. The same run also shows two whipsaw failures the recent window
  hides — 2011 (strategy -22.2% while QQQ was +4.1%) and COVID-2020
  (-15.9% vs QQQ's -7.1%) — which are the standing cost of trend-following
  through sharp round trips, not fixable by reweighting.
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
