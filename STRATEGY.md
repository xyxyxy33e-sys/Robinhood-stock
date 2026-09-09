# Live strategy spec — Robinhood Agentic account (576391551)

Single source of truth for the SPMO core + TQQQ/QLD satellite + XLU
defensive + BOXX cash-gate strategy. The live triggers (Mon–Thu daily, Friday
weekly) point here for the "what and why" and keep their own prompts to the
"when and how". **Part I is the live design — what the triggers trade today.
Part II is the research record — dated, kept so nothing is re-run.** Update
Part I when the strategy changes; append to Part II when something is tested.

# Part I — Live design

## Current design at a glance (2026-09-06)

**What the account holds, by effective state** — see the tables under
"Target weights"; effective state = macro 50/200 state, except that macro
B/C hold the A row when the 20/100 fast read is A/B, and macro F holds the
C row when the fast read is A/B/C.

| Effective state | Row | Exposure |
|---|---|---|
| A | 50% SPMO / 50% TQQQ | 2.0x |
| B | 75% SPMO / 25% TQQQ | 1.5x |
| C | 100% SPMO | 1.0x |
| D | 100% QLD | 2.0x |
| E | 50% XLU / 50% BOXX | 0.25x |
| F | 100% BOXX | 0.00x |

**Extension trim (graded):** when the effective state is A, count how many
of {close > 10% above the 100d SMA, > 12% above the 150d, > 15% above the
200d} are true and scale the A row's risky legs by 1 − ⅓ × votes
(×⅔ / ×⅓ / ×0 — three votes is 100% cash). Then the four risky legs are scaled by
`min(1, 20% / max(10d, 30d) realized QQQ vol)` with the remainder in BOXX. Rebalance on any change of effective
state, on L1 drift > 3%, or on a zero-target leg still held above 0.10%.

**Standing figures** (design of 2026-09-07 final: A 50/50, trim step ⅓,
vol estimator max(10d, 30d)). 26-year QQQ-core proxy 2000–2026: **22.1%
CAGR / Sharpe 0.94 / max drawdown −32.8%** (QQQ buy-and-hold 8.7% / 0.45 /
−80%). Real instruments, weekly, Nov 2015–Aug 2026: **30.7% / 1.26 /
−25.3%** (QQQ 18.4% / 0.94 / −35.5%, SPMO 17.4% / 0.94 / −28.3%); real
daily with the drift band **29.7% / 1.20 / −29.5%**, ~69 rebalances/yr.
Search-era Sharpe 1.150, holdout (2000–2015) 0.780 and 17.1%/yr. A
2022-type year is about −19% real / −27% proxy; a COVID-shaped event about
−25% to −33%; a −5% QQQ day is about −10%. **Execution assumption: these
figures assume fills at the signal-session close. One session of lag costs
about 3.1pp of CAGR and 4.8pp of drawdown — see the reconciliation below,
and `fill_quality.py`, which now measures it.**

**Change log (newest first).**

| Date | Change | Evidence |
|---|---|---|
| 2026-09-06 | trim step 0.25 → ⅓ (A ×⅔/⅓/0); A 50/50 → 40/60 | step: both eras, controls, p=0.00; 40/60: owner decision; "Leverage under the trim" |
| 2026-09-06 | graded extension trim: A ×0.75/0.5/0.25 as QQQ clears 10/12/15% above its 100/150/200d | both eras, controls, p=0.00, real +2.7pp; "Extension trim" |
| 2026-09-06 | 20/100 fast re-entry overlay on B/C/F | both eras, controls, p=0.01; "Fast re-entry overlay" |
| 2026-09-06 | A 70/30 → 50/50, D 85% QLD → 100% QLD | owner decision on the frontier; "Return frontier, step 2" |
| 2026-09-04 | zero-target-leg sweep in `needs_rebalance()` | free; "Zero-target-leg sweep" |
| 2026-09-02 | B 25/75 → 75/25, A 80/20 → 70/30, D 70% → 85% QLD, F → 100% cash, micro overlay off | "State F -> 100% cash", "Improvement search", "The return frontier" |
| 2026-09-01 | volatility targeting, 3% drift band, gold removed | "Volatility targeting", "26-year stress test" |
| 2026-08-31 | SPMO core, QLD satellite, XLU in state E | "The XLU update to state E" |

**The two weight tables and the overlay chain above are GENERATED from
`state.py`** by `paper-track/gen_live_tables.py`, and
`consistency_check.py` asserts this file matches the code. They were
hand-maintained until 2026-09-07, when an outside review found the detailed
table still reading A = 50/50 and the overlay chain still reading 0.25 per
vote, two days after the code moved to 40/60 and ⅓. Do not hand-edit them;
regenerate.

## Change freeze (2026-09-07 — READ THIS BEFORE PROPOSING ANY DESIGN CHANGE)

**No design changes until 2026-12-07, or until the strategy actually fails.**
Owner-approved. This binds future sessions, including whichever model reads
this next. If you are about to propose a weight change, a new overlay, a
parameter tweak or a "small free option", the answer is no — record it in the
research log as a candidate and leave the live design alone.

**Why.** Between 2026-09-05 and 2026-09-07 the design changed five times:
A 70/30 → 50/50, D 85% → 100% QLD, trim step 0.25 → ⅓, A 50/50 → 40/60 →
50/50, and vol30 → max(10d, 30d). Live trading began 2026-08-17, so the
design changed five times in the first three weeks of live operation and we
have essentially no live evidence about any of it. When those changes were
finally tested against a persistence-respecting null (circular block
bootstrap, same day), only the extension trim cleared 5%: the fast re-entry
overlay came in at P = 0.080 and the volatility estimator at P = 0.097.
Between this work and an outside report, well over a hundred configurations
have now been scored on the same 26 years of data. **The search itself has
become the dominant risk** — each additional test raises the chance the next
"winner" is noise, and the iteration was fast enough that this was not
noticed until it was pointed out.

**What is allowed during the freeze.**
- Measurement, monitoring and reporting (e.g. `fill_quality.py`).
- Bug fixes, and doc/code consistency fixes.
- Research that is RECORDED but NOT applied.
- Acting on a genuine failure: a guard tripping, a fill failing, a drawdown
  tier breaching, or live behaviour diverging from the backtest.

**What ends the freeze.** Either the date, or a real failure. "The backtest
says something better exists" is NOT a reason — that was true every day this
week and is exactly the condition the freeze exists to interrupt.

**Standing candidates, deliberately NOT applied** (revisit after the freeze,
with live data in hand): the 5% drift band (documented as performance-neutral
at lower turnover, and more attractive now that the faster estimator runs
~69 rebalances/yr); a floor on the extension trim's bottom rung (tested
negative 09-07); extension-threshold hysteresis (tested negative 09-07).

## Execution quality — measured, not assumed (2026-09-07)

`paper-track/fill_quality.py`. The drawdown reconciliation showed one extra
session between signal and fill costs 3.1pp of CAGR and 4.8pp of drawdown,
which is larger than any design change argued over this week — and nothing
measured it. Every rebalance now records, per leg, the realised fill price
against the official close of the signal session, with `slippage_bps`
COST-POSITIVE for both sides (a buy above the reference and a sell below it
are both positive = money lost). `summarize()` reports notional-weighted
slippage, because a bad fill on a $30k leg is not the same event as a bad
fill on a $500 stub. It gates nothing and never blocks a trade.

The number to watch is the notional-weighted figure against the **4bp
one-way cost model the backtests assume**. Persistently worse than that means
the live design is not the backtested one, and it is worth more attention
than any parameter.

Everything below the line "Research record" is history and evidence — what
was tried, what was kept, what was rejected and why. It is there so nothing
gets re-run; it is not what the triggers trade.

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
| A | 50% | 50% | 0% | 0% | 0% | 2.0x |
| B | 75% | 25% | 0% | 0% | 0% | 1.5x |
| C | 100% | 0% | 0% | 0% | 0% | 1.0x |
| D | 0% | 0% | 100% | 0% | 0% | 2.0x |
| E | 0% | 0% | 0% | 50% | 50% | 0.25x |
| F | 0% | 0% | 0% | 0% | 100% | 0.00x |

`target_weights(state)` returns this row — the base table, the right
reference for each state's RELATIVE risk posture. A live trigger never calls
it directly: two overlays apply on top, and the function that applies both is

    target_weights_with_voltarget(state, micro_agrees, vol, fast_state=fast, gaps=gaps)

1. **Fast re-entry overlay** (2026-09-06): `effective_state(state, fast_state)`
   may swap the row — macro B/C with a 20/100 read of A/B holds the **A**
   row; macro F with a 20/100 read of A/B/C holds the **C** row. Nothing
   else changes. Section "Fast re-entry overlay" below.
2. **Extension trim** (2026-09-06, graded): if the effective state is A,
   the four risky legs are scaled by `extension_scale(eff, gaps)` = 1 −
   ⅓ × votes over `EXTENSION_RULES` (×⅔ / ×⅓ / ×0). Section "Extension
   trim" below.
3. **Volatility targeting** (2026-09-01; estimator changed 2026-09-07): the
   four risky legs of that row are scaled by
   `min(1, 0.20 / realized_vol_live)` where `realized_vol_live` is
   **max(10-day, 30-day)** annualized realized QQQ vol, and the freed weight goes to
   cash. Section "Volatility targeting" below.

`micro_agrees` is still passed (the signature needs it) but the 30/150 micro
overlay is DISABLED (2026-09-02) and it moves no weight. `validate_weights(state,
core, tqqq, qld, xlu, cash)` must run on the result before any dollar target
or order; `WeightSanityError` = abort, do not trade, report.

## Fast re-entry overlay, 20/100 (added 2026-09-06)

`FAST_REENTRY_ENABLED`, `FAST_SHORT_N = 20`, `FAST_LONG_N = 100`,
`FAST_REENTRY_MAP`, `compute_fast_states()`, `effective_state()` in
`state.py`; `target_weights_with_voltarget(..., fast_state=)`. Tests:
`paper-track/fast_ma_overlay_test.py`, `fast_ma_overlay_r2.py`.

**Why.** Comparing the live design to a published "100% TQQQ above the
50-day, cash below" switch showed the two use the same line (six 2025 switch
dates all within 0–2 days of our A/B/C ↔ D/E/F transitions) and that the
whole 2025 gap (switch +59%, live +16%) was our re-entry ladder: C (1.0x)
→ B (1.25x) → A (2.0x) took from 1 May to 24 June while the switch was 3x
from day one. Raising B/C weights outright fails on the 26y record (B is a
failed bounce in 17/27 episodes; C at A weights makes 2022 −18%). The
overlay instead reads the SAME six-state machine on a 20/100 pair and uses
it only to skip ladder rungs when the fast reading already confirms:

| macro | fast | weights held |
|---|---|---|
| B or C | A or B | **A** (40/60) |
| F | A, B or C | **C** (100% core) |
| anything else | — | unchanged |

A, D, E are untouched; the overlay never de-risks; it is not a state.
`effective_state()` is what `needs_rebalance()`'s `regime_changed` compares.

**Evidence.** 26y proxy 17.98% / 0.739 / −36.4% → **19.77% / 0.779 /
−34.8%**; Sharpe up in both eras (search 0.922 → 0.937, holdout 0.594 →
**0.655**, the largest out-of-sample gain of anything tested this session);
exposure- and beta-matched controls PASS at k = 1.000 (same average
exposure — the gain is timing, not risk); max-statistic permutation over a
9-window grid p = 0.01; plateau 20/80 – 30/100 all both-era positive; per
year better 15/27, flat 8, worse 4 (2000 −8pp, 2022 −5pp, 2018 −4pp, 2003
−3pp — bear-market rallies). Real SPMO-era weekly 26.60% / 1.004 / −31.4%
→ 27.99% / 1.030 / −31.4%; 2019 +38 → +50, 2023 +52 → +60, 2025 +13 → +18,
2022 −13 → −17. Rebalances/yr 38 → 42. In 2025 it would have held 100%
core from 24 Apr (macro still F) and A weights from 2 May (macro C)
instead of 24 Jun.

**Rejected variants (do not re-run):** fast windows with a 10- or 15-day
short leg (MaxDD −41 to −47%, holdout gain gone — 15/60 holdout 0.586 <
live); 20/60 (+1pp real return, −38% MaxDD — the non-Pareto sibling);
combining 20/60 and 20/100 by AND (= 20/100), OR (= 20/60), or a strict
P>20>60>100 stack (no effect) or a loose one (−43% MaxDD, 2022 −27%);
using the fast reading to EXIT early (A + fast down → D weights: worse both
eras); E + fast up → D weights (no effect); requiring fast confirmation
before any macro transition (worse). The 30/150 micro overlay disabled
09-02 was a different design (changed A/D, fit on 2015+, nothing on
holdout) and stays disabled.

New standing figures: worst case about **−35%** (proxy), 2022-type year
about **−17%** real / −27% proxy.

## Extension trim (added 2026-09-06)

`EXTENSION_TRIM_ENABLED`, `EXTENSION_GAP = 0.15`, `EXTENSION_SCALE = 0.5`,
`compute_gap200()`, `is_extended()` in `state.py`; applied inside
`target_weights_with_voltarget(..., gap200=)` after the fast overlay and
before vol targeting. Tests: `paper-track/research_plan_gaps.py`,
`research_plan_gaps_r2.py`.

**Rule (graded, applied the same evening).** `EXTENSION_RULES = ((100,
0.10), (150, 0.12), (200, 0.15))`, `EXTENSION_STEP = 1/3` (was 0.25 until
later on 2026-09-06 — see "Leverage under the trim" in the research
record), `compute_extension_gaps()`, `extension_votes()`,
`extension_scale()`. When the effective state is A, each window whose gap
exceeds its threshold is one vote; the four risky legs are scaled by 1 −
⅓ × votes (×⅔ / ×⅓ / ×0 — at three votes the A row is 100% BOXX). Each
threshold sits near the 90th–95th percentile of A-day gaps
for its window, so this is one rule measured three ways. No other state is
touched; the trim only ever reduces exposure. A change in the vote count is
a regime change for `needs_rebalance()`.

| | 26y proxy | holdout Sharpe | real weekly 2015–26 |
|---|---|---|---|
| single trim, 200d > 15% → ×0.5 (first version) | 20.75% / 0.844 / −33.3% | 0.680 | 29.49% / 1.149 / −26.4% |
| graded three-window, step 0.25, A 50/50 | 21.73% / 0.890 / −33.3% | 0.748 | 30.72% / 1.211 / −25.3% |
| graded, step ⅓, A 50/50 | 22.15% / 0.912 / −33.3% | 0.769 | 31.40% / 1.248 / −25.0% |
| **graded, step ⅓, A 40/60 (live)** | **23.60% / 0.918 / −35.2%** | **0.771** | **33.34% / 1.233 / −27.0%** |

Step ⅓ vs 0.25 (A 50/50): exposure-matched control 0.747 PASS, max-stat
permutation over 8 schedules (vote labels shuffled among A days) p = 0.00,
real daily with the band 29.27% / 1.122 → 29.62% / 1.146; deeper schedules
test better still (1/.5/0/0: 0.931, holdout 0.788) and ⅓ is the
deliberate non-corner pick. Window count does not matter (4/5-window sets
at step 0.2 land on the 0.25 figures) — depth does. A 40/60 on top is the
owner spending that Sharpe on leverage (beta-matched control equals live
Sharpe at every rung, so leverage itself is a risk dial, not an edge).

Graded vs single: exposure-matched (k = 0.929) 0.744 and beta-matched
0.846 controls PASS; per-year gains spread (2002 +2.8, 2003 +6.4, 2009
+4.9, 2024 +2.6; 2023 −5.9, 2011 −3.0). Other stepped variants (two-step
on 200d, linear ramps, both-windows ×0.25, 2-of-3 vote) all land between
the two. The window check that motivated it: the single trim works at every
window 50–250d (`scratchpad gap_windows`), so the extension, not the 200d,
is the signal. **The reversed rule** (step exposure UP in C/E/F when far
BELOW the averages) was rejected: proxy MaxDD −51% to −68%, holdout Sharpe
0.48–0.61 (2001/2002 falling knives); QQQ's forward 120-day return from
deep-oversold downtrend days is −1.5% with a 45% hit rate over 26 years.

The original single-window evidence follows for the record.

**Evidence.** 26y proxy (live design with the overlay, 19.77% / 0.779 /
−34.8%) → **20.75% / 0.844 / −33.3%**; Sharpe up in both eras (search
0.937 → 1.058, holdout 0.655 → 0.680); exposure-matched control (k = 0.963)
0.742 and beta-matched 0.783 — PASS; max-statistic permutation over a
9-threshold grid **p = 0.00**; threshold plateau 12–20% all both-era, most
Pareto. Real SPMO-era weekly 27.99% / 1.030 / −31.4% → **29.49% / 1.149 /
−26.4%**; real daily with the drift band 27.35% / 0.986 / −33.4% → 29.40% /
1.105 / −32.6% (+2 rebalances/yr). It improves the 80/20, 70/30 and 50/50
A rows alike, so it is not an artifact of the 6 Sep leverage step. It does
not conflict with the 2026-09-01 "state-A confidence" rejection: those
signals (micro agreement, price vs 20d, vol/VIX percentiles) asked whether
to de-lever CONFIRMED trend; this trims OVERHEATED trend.

**Costs and sample.** Sits half-out through post-crash melt-ups: proxy 2009
−18pp, 2020 −4.5pp; real 2023 −3pp, 2024 −4pp; gets it back in 2007,
2010–11, 2018, 2020 (real +10), 2024–26. 65 episodes / 669 days in about
eight extension regimes (2003, 2009–10, 2011, 2020–21, 2023, 2024, 2025,
2026). Trim size is monotone — ×0.75 through ×0.0 all improve — so 0.5 was
a deliberately non-corner pick and step ⅓ is the graded equivalent; do not
push it toward full cash at one vote on the strength of that monotonicity.

## Volatility targeting (added 2026-09-01) — the outermost overlay

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

## Zero-target-leg sweep (added 2026-09-04)

`needs_rebalance()` now fires when any leg's target is **exactly 0%** but it is
still held above **`ZERO_LEG_EPS` = 0.10%**, regardless of total L1 drift.

**Why.** On 2026-09-04 realised vol fell to 19.78%, below the 20% target, so
the multiplier hit 1.0 and the cash target became exactly 0.00% — while the
account still held 0.50% BOXX. Total drift was 0.99%, inside the 3% band, so
nothing traded and nothing would have until an unrelated move pushed drift
past 3%. The return drag is trivial (~5bp/yr while it lasts); the real cost is
that the stub contributed 0.5pp of the 0.99% reading and never decays, so a
permanent floor on the drift metric makes a 3% band behave like a ~2.5% band
for genuine drift.

**This is not the per-leg threshold removed on 2026-09-01.** That one decided
which legs to SKIP once a rebalance had fired, and left small legs adrift.
This only ever ADDS a reason to fire; when it fires, every leg still goes to
target. The two rules are not in tension.

**The evidence says free, not profitable** (`paper-track/zero_leg_sweep_test.py`,
daily 2000-2026 proxy). CAGR, Sharpe and MaxDD are identical to three decimal
places in all three eras — full 15.69% / 0.752 / −32.4%, OOS 11.25% / 0.603,
fitted 22.29% / 0.941 — for +0.2 rebalances/yr and +0.01x turnover. It is
adopted for coherence ("target 0% means hold 0%"), not for return. Anyone
re-deriving this should know the numbers neither argue for it nor against
removing it.

The stub is rarer than it looks: a zero leg set to exactly 0 stays at 0 under
drift, so it only reappears when the target *changes* to zero while something
is still held. Stub days are 0.7% of history without the rule and 0.0% with
it. It cannot oscillate. 0.25% and 0.50% epsilons test identically but leave
~0.16% stubs standing; 0.10% (~$100 on this account, above fractional-fill
dust) was taken because it clears the case completely.

**Standing lesson: before trusting any state-level statistic, check whether
the sample window contains the market conditions that state is meant to
handle.** Use `data/qqq_long_history.csv` for anything that only needs QQQ
prices (state classification, regime statistics, signal research); the
2015-11 floor is only binding where SPMO/QLD/XLU/BOXX leg returns are needed.

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

- **Monday–Friday, 15:55 ET** — every session computes the macro state, the
  20/100 fast read, realized vol and the live weights, then calls
  `needs_rebalance(target, held, regime_changed)`: rebalance on a change of
  EFFECTIVE state, on L1 drift > 3%, or on a zero-target leg still held
  above 0.10%; otherwise no trade. ~42 rebalances/year expected.
- **Friday** additionally produces the weekly report (state, fast read, vol
  and multiplier, weights, fills, realized P&L with the wash-sale split,
  drawdown from high) whether or not it traded.
- Both triggers use the SAME `state.py` functions and safety guards. If the
  daily check already moved the book to target mid-week, Friday finds it
  there and trades nothing extra.

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
- **The real max drawdown is about -35% (proxy, 2000-2026) under the
  2026-09-06 design (A=40/60, D=100% QLD, 20/100 fast re-entry overlay,
  graded extension trim at step ⅓).**
  History of the figure, same proxy (`paper-track/long_history_backtest.py`,
  `drift_band_test.py`, `improvement_search.py`): live weights WITHOUT the
  vol overlay -69.6% (dot-com alone -67.2%); vol target 20% + 3% band
  (2026-09-01) -42.1%; the 2026-09-02 design (B=75/25, A=70/30, D=85% QLD,
  micro off) -32.4%; A=50/50 + D=100% QLD -36.5%; with the overlay -34.8%;
  with the extension trim -33.3% (single and graded alike); step ⅓ and
  A=40/60 (third revision the same day) -35.2%.
  QQQ buy-and-hold over the same
  span is -80.2%. Quote the SPMO-era figure only as "max drawdown in the
  SPMO-era window", never as the worst case. Cutting the tail from ~-70% to
  ~-42% is the main reason the vol overlay earned its place; the B fix took
  it the rest of the way. The same run also shows two whipsaw failures
  the recent window hides -- 2011 (strategy -22.2% while QQQ was +4.1%) and
  COVID-2020 (-15.9% vs QQQ's -7.1%) -- which are the standing cost of
  trend-following through sharp round trips, not fixable by reweighting.
- B's weights were 25/75 until 2026-09-02, resting on 4 episodes; the full-history
  re-sweep (27 episodes) reversed the direction to 75/25. The old note, for the record:
  B's weights (25/75/0) rest on 4 independent episodes. Trust the direction,
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

# Part II — Research record

Dated evidence for every row and overlay, and every idea that was tried and
rejected. Read the relevant section before proposing a change; if it is
listed under a rejection, do not re-run it without a genuinely new reason.

| Date | Section | Outcome |
|---|---|---|
| — | Why each row is what it is | rationale per state |
| — | What was tried and rejected | standing rejections |
| — | Transition structure | context only |
| 2026-08-31 | The XLU update to state E | applied |
| 2026-08-31 | The GLD core-blend addition | superseded, then removed |
| 2026-09-01 | Gold: standalone top-slice / removed | removed (owner) |
| 2026-09-01 | Micro overlay for states A and D | disabled 09-02 |
| 2026-09-01 | State D: QLD/XLU reweight, reverted | reverted (owner) |
| 2026-09-01 | 26-year stress test | led to vol targeting |
| 2026-09-02 | State F -> 100% cash; F episode census | applied |
| 2026-09-02 | D and E substates on full history | negative |
| 2026-09-02 | Improvement search on full history | B edge applied; rest rejected |
| 2026-09-02 | The return frontier | A/D step applied |
| 2026-09-06 | Downturn review D/E/F | negative |
| 2026-09-06 | Whole-strategy review | collapses/after-tax: no change |
| 2026-09-06 | Return frontier, step 2 | applied |
| 2026-09-06 | Fast re-entry overlay (Part I) | applied |
| 2026-09-06 | Extension trim (Part I); research-plan gap tests | applied |
| 2026-09-06 | Gap-to-200d rules in other states | negative |
| 2026-09-06 | Pair study | negative |
| 2026-09-06 | Post-change re-checks | confirmed |
| 2026-09-06 | Leverage under the trim; trim step sweep | step ⅓ + A 40/60 APPLIED (owner) |
| 2026-09-07 | Outside report review; max(vol10, vol30) estimator | candidate, not applied |
| 2026-09-07 | Outside review round 2: spec/control/churn audit | 3 defects FIXED; hysteresis negative |
| 2026-09-07 | vol estimator vol30 → max(vol10, vol30) | owner decision; real daily +0.05 Sharpe / +3pp MaxDD, both proxy eras up, real WEEKLY CAGR −0.85pp; block bootstrap NOT significant |
| 2026-09-07 | Block bootstrap + leave-one-regime-out; drawdown reconciliation | trim survives, overlay/estimator do not; −39/−40% gap = execution lag |
| 2026-09-07 | A 40/60 → **50/50** (reverted); CHANGE FREEZE; fill-quality tracking | owner decision after the bootstrap; see "Change freeze" |

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
sample; F's defensive posture is validated much more strongly than the
2015+ numbers suggest (and this finding is what drove F to 100% cash on
2026-09-02 — see below), and the risk/return frontier computed for F on the
short sample understates the case for staying defensive. The slope signal
itself also died here: permutation p went the WRONG way with 3.2x the data
(0.083 -> 0.189) and episode breadth flipped from 11-helped/2-hurt to
11-helped/15-hurt. A real effect strengthens with more data.

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

### Micro overlay for states A and D (added 2026-09-01, DISABLED 2026-09-02)

**Status: OFF** (`MICRO_OVERLAY_ENABLED = False` in `state.py`). The
full-history improvement search showed the overlay's A-half is a de-lever of
state A — a risk dial, not an edge (see "Improvement search on full history"
and "The return frontier" below) — and it was switched off as part of the
2026-09-02 move up the return frontier. `micro_agrees` is still computed and
still passed to `target_weights_with_voltarget()`, but it no longer changes
any weight and a micro flip is no longer a regime change. The section below
is the original rationale, kept for the record and for re-enabling.


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

### 26-year stress test: the design had a -65% drawdown in it (2026-09-01)

**Read this together with "Volatility targeting" above: everything in this
section describes the design BEFORE the vol overlay went live the same day.
The overlay cut the worst case from ~-65/-70% to about -42%; the 2026-09-02
reweight (B fix + return-frontier step) then moved it to about -32%. The section is
kept as-is because it is what motivated adding the overlay.**

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

**The bad one: max drawdown is -65%, not -26%** (pre-vol-targeting; ~-42%
with the overlay, ~-32% after the 2026-09-02 reweight). Every drawdown figure
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

### State F -> 100% cash (changed 2026-09-02)

State F's weights moved from **30% core / 70% cash to 100% cash**. This is the
direct consequence of the finding immediately above: on the full 1999-2026
history QQQ compounds **-39.4%** across F weeks, so the 30% core leg was
holding equity through the only regime the classifier explicitly labels
"established downtrend, going down."

Measured on the 2000-2026 QQQ-core stress test with volatility targeting and
the 3% drift band live (`paper-track/long_history_backtest.py`,
`paper-track/drift_band_test.py`):

| Design | CAGR | Sharpe | MaxDD | Rebalances/yr |
|---|---|---|---|---|
| LIVE (F = 30% core / 70% cash) | 11.36% | 0.665 | -42.1% | 42.5 |
| **F -> 100% cash (adopted)** | **11.61%** | **0.682** | **-38.8%** | **38.6** |
| E+F -> cash (not adopted) | 11.33% | 0.671 | -36.2% | 36.5 |
| D+E+F -> cash (not adopted) | 8.64% | 0.566 | -34.8% | 33.5 |

Better on all three axes, and it trades less.

**Why this isn't the usual cash-corner artifact.** This project has repeatedly
rejected "100% cash" search results as corner solutions — cash's near-zero
variance trivially wins a Sharpe objective regardless of foregone return, and
state E's own search hit exactly that trap. The distinguishing test is the
**exposure-matched control**: flatly de-levering the live design until its
average equity exposure matches the F-cash version gives 11.12% / 0.667 /
-41.4%, i.e. *worse* than routing that same reduction specifically into state
F. The gain comes from *when* the cash is held, not from holding less risk.

**Caveats, all of which are real:**

- The benefit is concentrated in **2000-2015** (7.37% / 0.479 vs 6.88% /
  0.451); **2015-2026 is a dead heat**. That the win lands in the era that was
  never searched is the good direction, but the recent era does not confirm it.
- It helps in **only 8 of 27 F episodes**; the old design wins the other 19.
  The aggregate gain is a positively-skewed insurance payoff — a few large
  avoided losses paying for many small foregone gains. *Expect it to feel
  wrong most of the time it fires.*
- It protects against sustained declines, not chop: dot-com improves
  **-32.1% -> -21.7%**, but the 2011 whipsaw **worsens -14.0% -> -16.0%**.

### State F episode census (2000-2026)

`paper-track/f_episodes.py` lists every F episode on daily data. **39
episodes, 993 trading days, 15.1% of history.** Duration: min 1 day, median
15 days (~3 weeks), mean 25.5, max 110.

| Duration bucket | Episodes | Days | Share of all F time |
|---|---:|---:|---:|
| <=1 week | 7 | 20 | 2.0% |
| 1-4 weeks | 17 | 202 | 20.3% |
| 1-3 months | 10 | 350 | 35.2% |
| >3 months | 5 | 421 | 42.4% |

The distribution is the whole argument for holding cash in F: **25 of 39
episodes end with QQQ flat or higher, but 42% of all F *time* sits in just
five episodes longer than three months.** The six worst run 52-110 days and
lose 15-35% each, with intra-episode drawdowns of 22-45%:

| Episode | Days | QQQ | Worst DD inside |
|---|---:|---:|---:|
| 2008-09-03 -> 2008-12-15 | 73 | -35.4% | -43.4% |
| 2002-03-13 -> 2002-08-16 | 110 | -33.4% | -42.7% |
| 2000-09-22 -> 2001-01-19 | 82 | -28.6% | -42.5% |
| 2001-02-02 -> 2001-04-18 | 52 | -26.0% | -44.7% |
| 2001-06-13 -> 2001-10-23 | 89 | -22.3% | -38.3% |
| 2022-04-11 -> 2022-07-18 | 67 | -15.1% | -21.6% |

This is the same positively-skewed payoff recorded in the F weights change
above, seen episode by episode. The live era (2015-11+) is episodes 29-39 --
eleven episodes, only three negative, worst -15.1% -- which is exactly why the
truncated window made F look excessively defensive.

**Two measurement notes, so the numbers in this file reconcile:**

- QQQ compounded across all F episodes is **-83.1% daily-sampled** here vs
  **-39.4% weekly-sampled** in the section above. The weekly figure uses the
  last trading day of each ISO week (197 weeks / 28 episodes), the cadence the
  weekly backtests run on; daily sampling resolves entries and exits the
  weekly grid blurs and does not merge episodes a few days apart. Both are
  correct for what they measure. Neither is the strategy's return -- F holds
  100% cash, so these are losses AVOIDED, not taken.
- `compute_states()` emits `'F'` as a placeholder while the 200-day SMA is
  still warming up (`if m200 is None: out.append('F')`). On data starting
  1999-09-15 that fabricates a 199-day "episode" ending 2000-06-27 in which
  QQQ rose 51% -- the longest and most positive entry, entirely artifact. The
  backtests never saw it (`long_history_backtest.START = '2000-07-01'` exists
  to skip it), but **any ad-hoc state tally on this data must drop the warm-up
  explicitly.**

### D and E substates: searched again on full history, still nothing (2026-09-02)

The user asked whether states D and E have a substate justifying a bigger cash
position, the way state F turned out to. `paper-track/de_substate_search.py`
answers no, and this is the second independent time the substate question has
come back negative.

The earlier study (`substate_research.py`, `substate_research_deltas.py`) ran
on the 2015-11+ window where D is ~370 trading days and E ~115 -- too thin to
split. The full QQQ history roughly triples both and adds the dot-com crash
and the GFC, which is precisely what flipped the F conclusion, so the retry
was justified.

**Flat cash increases first, as the baseline** (2000-2026 QQQ core, vol
targeting + 3% band, F already at 100% cash):

| Design | CAGR | Sharpe | MaxDD | avg risky |
|---|---:|---:|---:|---:|
| **Live** | **11.61%** | **0.682** | **-38.8%** | 71.5% |
| D risky x0.70 | 10.86% | 0.662 | -38.3% | 68.7% |
| D risky x0.00 | 8.86% | 0.575 | -37.4% | 62.2% |
| E risky x0.70 | 11.53% | 0.680 | -38.0% | 70.8% |
| E risky x0.00 | 11.33% | 0.671 | -36.2% | 69.2% |

D is strictly worse with more cash -- 2.75pp of CAGR for 1.4pp of drawdown.
E's whole cash axis is nearly flat. Neither resembles F, where the move was
Pareto-improving.

**Then the conditional search.** Nine point-in-time signals computable from
QQQ closes alone (drawdown from the 252d high, 200-SMA slope, 50-SMA gap,
50/200 gap, 20d and 12-1 momentum, 63d trend R^2, 30d/252d vol ratio, episode
age) x 3 split points x 2 cash depths, per state = 108 candidates, thresholds
fit on the search era and applied unchanged to the holdout.

- **6 of 108** improved Sharpe in both eras. Best gain **+0.007** Sharpe
  (state E, 252-day drawdown, worst third to cash), against **+0.017** for the
  F change.
- All six survived the exposure-matched control -- but by 0.001-0.007 Sharpe,
  well inside noise, and all six sit in state E whose cash axis the flat sweep
  had already shown to be featureless.
- **All six fail the max-statistic permutation test**, decisively: best
  p = **0.580**. The null distribution of the best-of-108 gain has median
  **+0.009** and 95th percentile **+0.022** -- i.e. *a random split of E's days
  typically beats the best real signal we found.* That is the textbook
  signature of nothing being there.

**Conclusion: no substate adopted for D or E.** The six states remain the
right granularity. Two negative results on independent data sets is enough --
do not re-run this search a third time without a genuinely new signal source
(the nine tested here exhaust what QQQ closes can say), and note that F's
success came from a *sample-window* fix, not from finer conditioning.

**The lever that does raise cash in D and E is the vol target itself**, which
needs no new signal (full period, band 3%):

| Vol target | CAGR | Sharpe | MaxDD | avg risky |
|---:|---:|---:|---:|---:|
| 22% | 11.62% | 0.665 | -40.6% | 73.0% |
| **20% (live)** | **11.61%** | **0.682** | **-38.8%** | 71.5% |
| 18% | 11.40% | 0.694 | -35.9% | 69.5% |
| 16% | 10.90% | 0.698 | -32.2% | 66.5% |
| 14% | 10.18% | 0.702 | -28.5% | 62.3% |
| 12% | 9.22% | 0.703 | -24.6% | 56.4% |

Sharpe sits on a flat plateau from 18% down to 12% while CAGR falls steadily:
a clean risk dial, not an edge. 20% is at the CAGR peak and is kept, since
this account's stated objective is to outperform SPY and QQQ. Lowering it is
the honest way to buy drawdown protection if that objective ever changes --
a deliberate return-for-risk trade, not a free improvement.

### Improvement search on full history (2026-09-02) — B edge APPLIED 09-02, rest rejected

Prompted by the by-year tables: the strategy's losses to QQQ cluster in sharp
recovery years and one whipsaw year, and every per-state weight was fit on the
2015+ window that had just proved misleading for F. `paper-track/
improvement_search.py` (round 1: per-state re-sweeps, hysteresis, micro
overlay on/off, five vol-measure variants, vol-target exemptions) and
`improvement_search_r2.py` (round 2: fine sweeps, episode census, beta-matched
control, combinations) test each change against the current design on
2000-2026, requiring improvement in BOTH eras, then re-check survivors on the
real SPMO-era instruments.

**One change is recommended: state B, 25% core / 75% TQQQ -> 75% core / 25%
TQQQ.** Everything else tested is either a risk dial or fails a check.

| Design (26y proxy) | CAGR | Sharpe | MaxDD | Sharpe 2015+ | Sharpe 2000-15 |
|---|---:|---:|---:|---:|---:|
| Live (B=25/75) | 11.61% | 0.682 | -38.8% | 0.959 | 0.479 |
| B=50/50 | 11.97% | 0.724 | -33.3% | 0.977 | 0.535 |
| **B=75/25** | **12.30%** | **0.765** | **-29.8%** | **0.989** | **0.593** |
| B=100/0 | 12.58% | 0.799 | -26.4% | 0.995 | 0.646 |

Monotonic: less leverage in B is better at every step, in both eras, on all
three metrics. Beta-matched control (live design flatly de-levered to the same
average beta 0.887): Sharpe 0.686 vs candidate 0.765 — **PASS**, decisively.

*Why.* B ("reclaim": price above both SMAs while the 50 is still below the
200) is structurally a state that ends either by FAILING (price drops back:
14 of 27 episodes exit to C or F) or by GRADUATING to A (13 of 27), and the
gains from graduation accrue in A, not B. Inside B itself QQQ finished
negative in 17 of 27 episodes (median 13 days). Leverage in a state that
mostly ends in failure is a bad bet; 2008 alone cost 12.8pp vs QQQ via three
bear-market rallies classified as B. The live 25/75 came from four episodes on
2015-11+, all of which happened to be real reclaims (QQQ +19.9% compounded
over that window's 28 B-weeks). Same failure mode as F: the recent window
didn't contain the case the state exists to handle.

*The cost, stated plainly.* On the real SPMO-era instruments B=75/25 gives
18.28% / 1.138 / -19.3% vs live 20.02% / 1.116 / -19.3%: **-1.74pp CAGR,
+0.022 Sharpe.** In that window it slips just below QQQ's 18.39% CAGR. Over 26
years it is +0.69pp CAGR and -9pp MaxDD. This is a bet that B episodes keep
behaving as they did in 27 episodes rather than as they did in the last 6.
B=60/40 (real: 18.83% / 1.142 — the live-era Sharpe peak; proxy: 12.11% /
0.741 / -31.9%, both-era Pareto) is the hedge if the live-era return matters
more.

**Tested and NOT recommended:**

- **C=80/20 TQQQ.** Proxy full-period Pareto (+0.6pp CAGR) but 2015+ Sharpe
  worse, and on real instruments it costs **4.9pp in 2022** (C is bear-market
  bounces; 14 of 2022's weeks were C). It also contradicts the B mechanism —
  both are counter-trend states with 50 < 200, and the evidence says no
  leverage there. C exits to F 19 of 43 times.
- **max(10d,30d) realised vol** (faster de-lever). Proxy +0.016 Sharpe /
  -1.8pp MaxDD in both eras, but real instruments -0.73pp CAGR and Sharpe
  1.116 -> 1.105. Mixed; not enough to justify a change.
- **Micro overlay OFF.** +1.85pp CAGR on the proxy, better 2000-15, worse
  2015+; real instruments 22.66% / 1.095 / -23.8% vs 20.02% / 1.116 / -19.3%.
  Splitting it: the A-half (88/12 instead of 80/20 when the fast classifier
  agrees) is simply a de-lever of state A — the A sweep shows Sharpe flat at
  0.693-0.699 from 10% to 40% TQQQ while CAGR and MaxDD climb together. **A
  risk dial, not an edge**, same family as the vol target. Left on.
- **Hysteresis.** 1% is the best of 0.5/1/2/3/5%; 2-3% are much worse (2011
  is not fixable this way).
- **Downside semi-vol, EWMA vol, mean(10d,30d), min(30d,60d):** all worse.
- **Exempting B or C from vol targeting:** MaxDD -52% to -54%. Very bad.
- **A: more TQQQ** raises CAGR (14.3% at 70/30) with flat Sharpe and worse
  MaxDD — a dial. **D, E:** nothing (see the substate section above).

### The return frontier (2026-09-02) — how to raise CAGR, and what it costs

**APPLIED 2026-09-02 (user decision): the bolded row — B=75/25, A=70/30,
D=85% QLD / 15% cash, micro overlay off.** Confirmed from `state.py` itself
after the edit: real instruments 23.35% / 1.063 / −26.7%
(`voltarget_live_backtest.py`); 26-year proxy **15.69% / 0.752 / −32.4%** at
the 3% band, 41 rebalances/yr (`drift_band_test.py`). Every "−42%" worst-case
figure elsewhere in this file describes the design before this change; the
current worst case on the proxy is about **−32%**, and the live-era stress
events are larger than before (COVID −27% vs −19%). To reduce drawdown
later, walk the path in reverse: A first, then D, then re-enable micro.

The user asked how to bring the return up. The improvement search found one
edge (B) and otherwise only DIALS — leverage in the trend states A and D, and
the micro overlay (an A de-lever). `paper-track/return_frontier.py` draws the
dial, starting from B=75/25. Vol target is NOT on it: 20% is already the CAGR
peak (22% -> 11.62%, 25% -> 11.45%), so raising it buys drawdown for nothing.

| Design | Proxy CAGR | Sharpe | MaxDD | Real CAGR | Sharpe | MaxDD |
|---|---:|---:|---:|---:|---:|---:|
| LIVE (B=25/75, micro on) | 11.61% | 0.682 | -38.8% | 20.02% | 1.116 | -19.3% |
| B=75/25, micro on | 12.30% | 0.765 | -29.8% | 18.28% | 1.138 | -19.3% |
| B=75/25, micro off | 14.16% | 0.763 | -30.2% | 20.88% | 1.094 | -23.8% |
| + A=70/30 | 15.04% | 0.755 | -32.1% | 22.15% | 1.062 | -25.7% |
| + D=85% QLD | 14.81% | 0.756 | -30.6% | 21.98% | 1.085 | -24.8% |
| **+ A=70/30, D=85% QLD (APPLIED)** | **15.69%** | **0.752** | **-32.4%** | **23.25%** | **1.061** | **-26.7%** |
| + A=60/40, D=100% QLD | 17.19% | 0.744 | -34.7% | 25.50% | 1.030 | -29.6% |
| + A=50/50, D=100% QLD | 17.98% | 0.739 | -36.4% | 26.60% | 1.004 | -31.4% |

Real-era stress events per point (COVID 2020-02..04 / 2022 / Apr 2025 max
drawdown): live -19.3 / -6.6 / -11.4; micro off -23.8 / -10.0 / -15.3;
A=70/30+D=85% -26.7 / -11.8 / -18.1; A=60/40+D=100% -29.6 / -13.7 / -20.8;
QQQ -27.3 / -31.4 / -21.5.

Reading it:

- **Sharpe declines slowly and without a knee** (proxy 0.765 -> 0.739 across
  the whole span). No point on the frontier is "wrong"; it is a preference.
- **On 26 years, every point up to A=60/40 + D=100% still has a SMALLER max
  drawdown than today's live design** (-34.7% vs -38.8%), because the B fix
  buys ~9pp of drawdown that leverage then spends back. On the real 2015+
  era the B fix bought nothing (MaxDD unchanged at -19.3%), so there every
  step up costs drawdown directly — COVID goes -19% -> -30% at the top.
- **D leverage is nearly free in the live era** (D=85% QLD: real Sharpe
  1.062 -> 1.061 on top of A=70/30) while **A leverage and micro-off are what
  cost Sharpe** there. Order of preference if climbing: micro off, then D,
  then A.
- Proxy leverage in 2000-02 runs through SYNTHETIC TQQQ/QLD; real funds did
  not exist. The regime behaviour is the finding, not the decimals.

### Downturn review: states D/E/F (2026-09-06) — NEGATIVE, no change

Prompted by the Jan-2024..Sep-2026 monthly table (down-capture vs QQQ 1.44x,
worst relative months all D/E/F months). `paper-track/downturn_review.py`
and `downturn_review_r2.py`; outputs in the session scratchpad.

**Attribution first.** Decomposing strategy-minus-QQQ by the state in force
on the signal day (26y proxy, live design): A +62.5pp, B +6.8pp, C -1.0pp,
**D +29.9pp**, **E -18.6pp**, **F +98.3pp**. D is a net *positive*
contributor over 26 years (33.6%/yr vs QQQ 23.2%/yr on D days) and F is the
largest single source of edge. E is the only downturn state that loses, and
it loses almost entirely in the search era (-16.6pp of the -18.6pp): E days
there are V-bottom rebound days (Dec 2018, Mar 2020, Mar 2025) where QQQ
compounded +43.7%/yr while E held 39% exposure. On the holdout, E is a wash
(-2.0pp). On the real-instrument 2024-2026 daily window: A +20.0pp,
D +1.4pp, E +1.4pp, **F -5.0pp** (the 12-day April 2025 F whipsaw),
C -2.7pp. So the 1.44x down-capture in the monthly table is **not** a
D/E/F problem: it is 1.3-1.4x leverage in A/B on down days, which is the
price of the 2026-09-02 return-frontier step.

**Seven new tests, one survivor, and that survivor was rejected on
robustness:**

- P2 D composition beyond the T1 grid (core/QLD blends, XLU inside D,
  TQQQ-half). Four rows improve Sharpe in both eras and pass both controls,
  best `D=(0,0,0.70,0.15,0.15)`: 15.49% / 0.768 / -31.8% vs live 15.69% /
  0.752 / -32.4%. That is -0.2pp CAGR for +0.016 Sharpe — a Sharpe-for-
  return trade, the wrong direction for this account's objective. Not
  applied; on file as the option if the objective ever shifts.
- P3 D substate on price proximity to the 200d SMA (the one QQQ signal the
  2026-09-02 substate search did not include). `D & gap200<2% -> cash`
  looked like a clean Pareto win (16.58% / 0.803 / -32.0%, both eras,
  both controls, max-stat permutation p=0.03). **Rejected anyway:** (i)
  cliff — at X=2.5% it collapses to 14.97/0.744/-37.3 and holdout Sharpe
  0.61 -> 0.49; (ii) the next-day return profile by gap bin is
  non-monotonic (negative below 1.5%, then +45bp and +74bp t=3.7 in the
  2-3% bins — the rule's edge is an accident of where a rebound bin sits);
  (iii) SPY as an independent series shows no such profile at all (every
  bin flat to slightly positive); (iv) the real-instrument weekly check is
  mixed (X=2% slightly worse). Consistent with the earlier 108-candidate
  negative: there is no D/E substate.
- P4 lower vol target (10%/15%) inside D, E, DE, DEF, CDE: worse on every
  metric, both eras.
- P5 synthetic inverse exposure (-1x, ER 0.95%, short proceeds at T-bill)
  in F and/or E: 0.25 short in F is a hair better full-period
  (15.86/0.756/-31.9) but worse in the search era; every larger size
  raises MaxDD. Fails both-era. (No PSQ/SQQQ data on disk; not worth
  acquiring.)
- P6 asymmetric hysteresis (fast exit / slow re-entry and the reverse, 8
  pairs): nothing beats symmetric 1%/1% on both eras.
- P7 strategy-NAV drawdown kill switch (cut risk after -10/-15/-20% from
  the 252d high, restore when recovered): all far worse (CAGR 4.6-13.5%),
  because every deep drawdown in the record was followed by a recovery
  the switch sat out.

**Verdict:** no change to D/E/F. The honest levers on downturn pain are the
ones already on the frontier table — A/B leverage and the vol target — and
those are return-for-drawdown trades the owner has already priced.

### Whole-strategy review (2026-09-06) — no change (after-tax proposal declined)

`paper-track/strategy_review.py` and `strategy_review_r2.py`. Four questions
the project had not asked before; results:

- **Portfolio-level (leverage-aware) vol target** — scale by
  `min(1, T / (beta_eff * vol_qqq))` so a 1.6x state A and a 1.0x state C
  carry the same risk. At matched CAGR it is no better than the live
  QQQ-vol target (T=0.30: 15.50% / 0.746 / -34.7% vs live 15.69% / 0.752 /
  -32.4%) and the search-era Sharpe is worse at every T. Rejected.
- **Classifier ensemble** (average the weights of 2-3 MA pairs): worse on
  every metric for every combination. Rejected.
- **Simplification / state collapses on the 26y proxy.** Every collapse
  that keeps the CORE through C and D beats the 6-state machine on the
  proxy (2-state ABCD->70/30, EF->cash: 16.54% / 0.779 / -30.2%, both eras,
  Pareto, beta-control PASS; 4-state C->A, D->A: 16.90% / 0.793). **But on
  real instruments they lose** (2-state 22.13% vs live 23.25%, worst years
  2016 -8.9pp and 2022 -6.7pp — the two momentum-crash years). The proxy's
  core is QQQ; the live core is SPMO, and rotating OUT of a momentum core
  in a pullback (state D) is worth about +0.7pp/yr pre-tax that the proxy
  cannot see. **Standing lesson: any test that changes which states hold
  the core leg must be confirmed on real SPMO rows — the proxy is blind to
  the SPMO/QQQ difference.** Each piece separately on real SPMO-era rows:
  E->cash only 22.32% / 1.029 (-0.9pp; loses 2016/2026, E is the V-bottom
  state); C->A + D->A 22.86% / 1.062 (-0.4pp; 2022 -17.4% vs -11.3%);
  C->A alone 23.56% / 1.063 (+0.3pp, but 2022 -18.1% -- leverage in a
  bear-market rally, same reason C leverage was rejected 09-02); the
  2-state 22.13% / 1.034 (-1.1pp). The six states earn their keep on the
  instruments actually held. Do not re-run.
- **After-tax (the one that matters if the account is taxable).** Lot-level
  FIFO/HIFO simulation, annual settlement, top bracket (ST 40.8% / LT
  23.8%), on real weekly SPMO-era rows 2015-11..2026-08:

  | design | pre-tax | after annual tax | full liquidations/yr |
  |---|---|---|---|
  | QQQ buy-and-hold (liquidated at LT) | 18.39% | 15.98% | — |
  | SPMO buy-and-hold (liquidated at LT) | 17.39% | 15.05% | — |
  | **LIVE** (D = 85% QLD) | 23.25% | **15.10%** | 6.8 |
  | D = 70/30 core/TQQQ | 22.55% | 18.43% | 2.1 |
  | **D = 60/40 core/TQQQ** | **23.28%** | **18.70%** | 2.1 |

  The live design gives back 8pp/yr to tax and, after tax, roughly TIES
  buy-and-hold QQQ in a top-bracket taxable account. The cause is
  structural: state D (about four episodes a year) sells 100% of the core
  into QLD and buys it back weeks later, so core lots never reach one year
  and every gain is realised short-term. Keeping the core through D and
  expressing D's leverage with TQQQ instead — `D = (0.60, 0.40, 0, 0, 0)`,
  1.8x vs the live 1.7x — matches live pre-tax on real instruments
  (23.28% vs 23.25%), is a both-era Sharpe improvement on the 26y proxy
  (16.39% / 0.768 / -32.5% vs 15.69% / 0.752 / -32.4%, beta-control PASS),
  cuts full liquidations from 6.8 to 2.1 a year, and is worth about
  **+3.6pp/yr after tax**. At a 24% bracket the after-tax gap is about
  +2.5pp/yr. HIFO vs FIFO lot selection, a wider drift band and turning
  the vol target off each move after-tax return by <1.5pp and are not
  worth their costs. Caveats: wash-sale disallowance is ignored (it makes
  live look BETTER than it is), dividend tax is ignored, and the bracket
  is assumed. If the account is tax-advantaged none of this applies and
  the live D row stays.

  **Proposed `D = (0.60, 0.40, 0.00, 0.00, 0.00)` on after-tax grounds — DECLINED
  by the owner 2026-09-06 (gains are offset by a separate tax-loss-harvesting
  account, so after-tax is not the objective). On pre-tax merits alone it is a
  tie on real instruments and was not applied. D later moved to 100% QLD
  ("Return frontier, step 2").**

### Return frontier, step 2 (2026-09-06) — APPLIED

Owner decision after the whole-strategy review ("what if I want more"). The
frontier ladder (ad-hoc run, figures reproduced by `improvement_search.py`'s
harness and `return_frontier.py`'s real-instrument rows):

| rung | 26y CAGR | Sharpe | MaxDD | 2022 | real CAGR | real Sharpe | real MaxDD |
|---|---|---|---|---|---|---|---|
| 2026-09-02 design (A70/30, D85% QLD) | 15.69% | 0.752 | -32.4% | -21.0% | 23.25% | 1.061 | -26.7% |
| A60/40 | 16.55% | 0.747 | -34.2% | -21.6% | 24.44% | 1.031 | -28.6% |
| A60/40 + D100% QLD | 17.19% | 0.744 | -34.7% | -22.9% | 25.50% | 1.030 | -29.6% |
| **A50/50 + D100% QLD (APPLIED)** | **17.98%** | **0.740** | **-36.5%** | **-23.5%** | **26.60%** | **1.004** | **-31.4%** |
| A50/50 + VT 25% | 17.57% | 0.721 | -37.8% | -26.5% | 26.63% | 0.992 | -32.3% |
| A40/60 + VT 25% | 18.34% | 0.716 | -39.5% | -27.2% | 27.60% | 0.964 | -34.1% |
| A50/50, vol target OFF | 16.84% | 0.674 | -54.6% | -27.4% | 27.47% | 0.989 | -38.3% |

What was learned mapping it: **A leverage is the cheap rung** (~+0.85pp CAGR
per 10pp of TQQQ for ~-1.8pp MaxDD, Sharpe nearly flat); **D leverage is
nearly free**; **raising the vol target is the expensive rung** (+0.2pp CAGR
for a 2022-type year going from -22% to -26%); **B leverage has negative
expected return on the 26y record** (QQQ negative in 17/27 B episodes, 4
exits straight to F) and only looks good on the 2015+ window where every
bounce succeeded — B stays 75/25; **vol target off is a trap** (less return
than A50/50 with it on, -55% MaxDD, 6 years underwater). Beyond A50/50 the
real-window Sharpe drops below 1.0.

New standing figures: worst case about **-36%** (proxy), COVID-shaped event
about **-34%**, 2022-type year about **-24%**, 2025 tariff-shaped event about
**-25%**. Search/holdout Sharpe 0.922 / 0.594 (was 0.941 / 0.603). This is a
return-for-drawdown trade the owner priced, not an edge. Effective exposure
in A is now 2.0x; a -5% QQQ day is about a -10% strategy day. Real-instrument
2020 under this design: +43.8% vs QQQ +47.6% (Feb-Mar -21%, April lag -10pp);
2024: +48.1% vs +24.8%; 2026 YTD to Aug: +24.8% vs +17.4%.

### Pair study: macro × fast state pairs (2026-09-06) — NEGATIVE, no change

`paper-track/pair_study.py`, `pair_study_r2.py`, `pair_mix_search.py`.
Every day is one of 36 (macro 50/200, fast 20/100) pairs. Census, then
one-change tests (hold a different row on a pair's days), pair-specific
weight mixes, and cash-in-pair, on both fast windows (20/100 and 20/60):

- The three cells the overlay acts on (CA, CB, FC) are the cleanest positive
  reads. EC (45 d) is the only small cell consistent in both halves (−44
  bp/day) and already holds the defensive row. Cells under ~100 days have
  halves that disagree in sign — anecdotes, not signals.
- **DD → E/F/C** and **EF → C/D/A** pass the both-era filter on the proxy
  (DD→E: 21.24% / 0.856, controls pass, max-stat p = 0.03) but **fail on
  real instruments** (DD→E 23.85% / 0.940 vs live 27.99% / 1.030, with
  ±15–20pp year swings; EF→C flat-to-worse). DD's "zero return" has no
  internal structure (returns by depth below the 50d are +5/+3/+7 bp in the
  middle bins).
- 20/60 pairs: best gain +0.047 Sharpe, permutation p = 0.20. Nothing.
- Pair-specific mixes (38 vectors × 9 big cells, chosen on search-era
  Sharpe): proxy 24.4% / 0.933 both eras, **real 22.47% / 0.873** — the
  clearest overfit signature in the project.
- Fitting on the SPMO era alone, split-half both ways: each half picks a
  different set of pairs, looks superb on its own years (Sharpe 1.3) and
  loses 10–15pp/yr on the other half.
- Cash in any further pair: no single pair improves real instruments;
  combinations cost 0.6–5.4pp/yr real.

**Standing lesson:** a pair cell is a signal only above ~200 days AND only if
it survives on real instruments; the proxy alone has enough freedom to fit
any cell.

### Gap-to-200d rules in the other states (2026-09-06) — NEGATIVE, no change

`paper-track/gap_rules_other_states.py`. Asked after the A extension trim:
does distance from the 200d help anywhere else? Three families on the 26y
proxy (baseline = live incl. the A trim, 20.75% / 0.844 / −33.3%):

- **Trim when far above** (D at +5/+10%): no both-era gain. D's median gap
  is only +4.8%; the deep-extension days that make the A trim work do not
  exist in D.
- **Cut to cash when far below** (B/C/E/F): F is already cash. `C & gap <
  −10% → cash` passes both eras on the proxy (21.11% / 0.859) but is worse
  on real instruments (29.12% / 1.139 / −27.9% vs 29.49% / 1.149 / −26.4%).
- **Add when far below** (oversold bounce, hold the next-more-aggressive
  row): `E & gap < −5% → D row` (100% QLD) is the best-looking proxy result
  of the day — 24.50% / 0.940 / −31.0%, both eras, Pareto, positive in 12 of
  13 affected years — **but rests on 105 proxy days / 12 real weeks, and on
  real instruments it is flat on Sharpe with MaxDD −26.4% → −32.8%** (2022
  −17 → −22, 2025 +20 → +8). Buying a breakdown at 2x fails the
  real-instrument hurdle on drawdown. Rejected; the one gap rule worth
  revisiting when the real window contains more E episodes.

**Standing conclusion:** the 200d gap is informative in A (overheating) and
nowhere else that survives on real instruments.

### Post-change re-checks (2026-09-06) — all confirmed

Under the 2.0x design, re-swept: vol target 15–25% × 10/30/60-day lookback
(20% / 30d still the point — 17.5% is +0.001 Sharpe for −0.8pp proxy /
−1.3pp real; 10-day lookbacks push MaxDD to −40..−48%); drift band 2–8%
(flat, 19.8% / 0.78 / −34.7% throughout; only trades/yr change: 53 / 42 /
31 / 24 — 5% is a free option if fewer trades are wanted); A row at 2.0x
with less TQQQ (25/25/50 or 100% QLD: identical proxy, −0.2 to −0.5pp real —
SPMO's momentum is worth more than the decay saved).

### Leverage under the trim; trim step sweep (2026-09-06) — leverage NO EDGE; step ⅓ + A 40/60 APPLIED (owner decision)

Question: does the graded extension trim make more A/B leverage
sensible? Scripts: `paper-track/leverage_under_trim.py` (ladders) and
`leverage_under_trim_r2.py` (schedule variants, permutation, real daily).
Everything below runs the FULL live design (fast 20/100 + graded trim +
VT 20%).

A ladder (core/TQQQ), proxy 26y CAGR / Sharpe / MaxDD, search S, holdout H,
real weekly:

| A row | proxy | S / H | real weekly |
|---|---|---|---|
| 50/50 (live) | 21.7 / 0.890 / −33.3 | 1.075 / 0.748 | 30.7 / 1.211 / −25.3 |
| 40/60 | 23.1 / 0.894 / −35.2 | 1.084 / 0.748 | 32.5 / 1.193 / −27.4 |
| 30/70 | 24.4 / 0.895 / −37.2 | 1.090 / 0.746 | 34.2 / 1.173 / −29.5 |
| 0/100 | 28.1 / 0.894 / −42.5 | 1.095 / 0.740 | 39.0 / 1.115 / −37.6 |

Sharpe is flat on the proxy, flat-to-down on the holdout, and DOWN on
real instruments at every step; MaxDD grows ~2pp per 10pp of TQQQ. The
beta-matched control Sharpe equals the live Sharpe at every rung, i.e.
leverage remains a pure risk dial — the trim does not turn it into an
edge. B ladder (60/40, 50/50) is negative on the proxy and holdout and
only +0.5–0.8pp real. VT 22/25/30% with the trim on: proxy Sharpe
0.879/0.867/0.843, holdout 0.732/0.717/0.687 — still expensive. Verdict:
same as the 09-06 frontier note — more leverage is a preference, not an
improvement; the trim does not change that.

What the sweep DID find: the trim STEP (0.25, chosen without a sweep) is
too shallow. Multiplier at 0/1/2/3 votes, A 50/50:

| schedule | proxy | S / H | expo-ctl | real weekly | real daily (band) |
|---|---|---|---|---|---|
| 1/.75/.5/.25 (live) | 21.7 / 0.890 / −33.3 | 1.075 / 0.748 | 0.744 | 30.7 / 1.211 / −25.3 | 29.3 / 1.122 / −32.6 |
| 1/.67/.33/0 (step ⅓) | 22.2 / 0.912 / −33.3 | 1.100 / 0.769 | 0.747 | 31.4 / 1.248 / −25.0 | 29.6 / 1.146 / −32.6 |
| 1/.5/.25/0 | 22.3 / 0.922 / −33.3 | 1.105 / 0.782 | 0.748 | 31.3 / 1.254 / −24.4 | 29.6 / 1.153 / −32.6 |
| 1/.5/0/0 | 22.5 / 0.931 / −33.3 | 1.118 / 0.788 | 0.750 | 31.8 / 1.274 / −24.4 | — |
| 1/0/0/0 | 22.4 / 0.937 / −33.3 | 1.108 / 0.805 | 0.752 | 30.7 / 1.249 / −24.4 | — |

Response is monotone in trim depth (a surface, not a spike), improves
both eras, beats the exposure-matched control, and the max-statistic
permutation over the 8 schedules (vote labels shuffled among effective-A
days, counts kept, 200 shuffles) gives p = 0.00. Real daily with band
mechanics: +0.02–0.03 Sharpe, CAGR +0.3pp, trades/yr unchanged. Cost is
behavioural: at 3 votes the A row goes to 100% cash (9.2% of A days on
the proxy; 17.7% at ≥2 votes for the 1/.5/0/0 form). Per-year real
daily: 2020 gives back 5–8pp (+39 → +31..34), 2021/2024/2025/2026 gain
2–4pp each. NOT applied — owner's call; the minimal change is
`EXTENSION_STEP = 1/3`. If more return is wanted, spending the Sharpe on
A 40/60 under step ⅓ gives proxy 23.6 / 0.918 / −35.2 (H 0.771), real
daily 31.9 / 1.154 / −33.2 — i.e. higher CAGR than live at a better
Sharpe than live, for ~2pp more proxy MaxDD.

Follow-up (same day, `leverage_under_trim_r3.py`): 4 and 5 windows. Adding
a 50d (>6% or >8%) or 250d (>15% or >17%) window at step 0.2
(1/.8/.6/.4/.2) lands on the live figures (proxy Sharpe 0.884–0.890,
real 1.17–1.25) — the multiplier never reaches zero, so it is the live
trim with the same depth spread thinner. The same window sets at step
0.25 or ⅓ (bottom at 0) recover the gain (proxy 0.904–0.919, H
0.75–0.80, real 1.20–1.31). Depth, not window count, is what matters;
4w +50d>6% step ⅓ has the best holdout (0.801) and real MaxDD (−22.8%)
but a weaker search-era Sharpe (1.069 vs 1.100 for 3w step ⅓), so the
3-window step-⅓ form remains the cleaner candidate.

**Applied (same day, owner: "apply step 1/3 and 40/60").** `EXTENSION_STEP
= 1/3`, `TARGET_WEIGHTS['A'] = (0.40, 0.60, 0, 0, 0)`. Standing figures
move to proxy 23.60% / 0.918 / −35.2% (search 1.112, holdout 0.771,
holdout CAGR 18.1%, worst holdout year −19.1%), real weekly 33.34% /
1.233 / −27.0%, real daily 31.86% / 1.154 / −33.2%. Proxy by year: 2000
−18.9, 2008 −13.2, 2011 −19.1, 2020 +37.5, 2022 −28.0; COVID drawdown
−25.2%, 2022 drawdown −30.6%. Real daily by year: 2020 +40.3, 2022 −20.3,
2023 +73.4, 2024 +64.5, 2025 +28.9, 2026 YTD +35.9. Worst-case figure to
carry: **about −35%**.

**Floor on the bottom rung (same day, `leverage_under_trim_r4.py`) —
NEGATIVE.** Owner asked for 1/.67/.33/.15 after seeing Jul–Aug 2020 sit at
0% under step ⅓. A 40/60 throughout: proxy 23.60 / 0.918 / −35.2 (S 1.112,
H 0.771) → 23.42 / 0.912 / −35.2 (S 1.104, H 0.766); real weekly 33.34 /
1.233 → 33.03 / 1.222; real daily 31.86 / 1.154 → 31.70 / 1.147. Floors of
.10 and .25 sit on the same line. 2020 real daily: +40.3% → +41.0% (Jul
+2.4, Aug +3.3 instead of 0/0) with max drawdown −25.2% → −26.8%. The
floor pays in melt-ups (2009 +1.6, 2023 +2.1 proxy) and gives it back at
tops (2003 −2.1, 2007 −1.3, 2024 −1.9, 2026 −1.8). Not applied.

### Outside report review; faster volatility estimator (2026-09-07) — CANDIDATE, not applied

The owner shared an outside research report (data cutoff 31 Aug 2026)
benchmarked against a PINNED OLD COMMIT of this repo (3b7f5a08), i.e. before
the 6 Sep design. Its "original six-state" line is 24.70% / 0.975 / −27.7%
on 2016+; our current design is 33.3% / 1.23 / −27.0% real weekly, so its
baseline is not what we run and its head-to-head numbers cannot be read
across. Three of its conclusions were checked against our own record:

- **Its headline recommendation is a full TQQQ/cash sleeve** (200 DMA
  regime, no SPMO), 38.45%/yr since 2016. This is the raincheckfund-shaped
  strategy already reviewed and rejected on 2026-09-06. Its OWN 2000–2015
  stress table agrees with that rejection: 8.34% CAGR / −61.4% MaxDD /
  −24.0% worst rolling 3y for the TQQQ/cash family, against 9.52% /
  −35.7% / −12.1% for our six-state design. Its own bootstrap puts the
  return advantage at −2.03 to +2.67pp, spanning zero. No change.
- **Its negative finding on "extension trimming" does not test our rule.**
  It caps exposure at 2x above 110%/115% of the 50 DMA on the TQQQ/cash
  sleeve; ours is a graded three-window vote (100/150/200d) on the A row of
  the six-state design, validated both-era with p=0.00. Its 115% variant
  never bound in-sample. Not evidence against ours.
- **Its "D uses A allocation" suggestion** is against the old D row. Our D
  became 100% QLD on 2026-09-06 on the frontier analysis. Not revisited.

**The one genuinely new idea is the volatility ESTIMATOR: use
max(vol10, vol30) instead of vol30.** We have swept the vol TARGET and the
LOOKBACK but never a two-window max. Tested on the live design
(`vol_estimator_family.py`, `vol_estimator_daily.py`):

| estimator | 26y proxy | search / holdout | expo-ctl | real weekly | real daily (band) |
|---|---|---|---|---|---|
| **vol30 (live)** | 23.60 / 0.918 / −35.2 | 1.112 / 0.771 | 0.741 | 33.34 / 1.233 / −27.0 | 31.86 / 1.154 / −33.2 |
| max(10,30) | 23.55 / 0.942 / −34.7 | 1.158 / 0.781 | 0.744 | 32.49 / 1.240 / −27.4 | 31.94 / 1.206 / −30.1 |
| max(5,30) | 23.32 / 0.945 / −34.0 | 1.163 / 0.783 | 0.744 | 31.65 / 1.240 / −27.9 | — |
| vol10 alone | 23.71 / 0.922 / −37.7 | 1.160 / 0.745 | 0.741 | 33.29 / 1.224 / −29.2 | — |
| max(10,60) | 23.00 / 0.932 / −35.8 | 1.099 / 0.807 | 0.744 | 29.85 / 1.162 / −27.5 | — |

It is a surface, not a spike: every max(fast, slow) pair beats its own
single-window counterpart on Sharpe, and the good region is max(5–15, 30).
Exposure- and beta-matched controls pass (0.744 and 0.920 vs 0.942). Real
daily with the band is the strongest result — Sharpe 1.154 → 1.206, MaxDD
−33.2% → −30.1%, CAGR flat — and it survives 10bp and 20bp costs
(0.951 → 0.991 at 20bp). Turnover is essentially unchanged (17.1 → 17.2x
of portfolio value per year) even though rebalances rise 55 → 69/yr: more
frequent, smaller trims.

**Why it is NOT applied.** It fails our standing bar, which requires
improvement on the proxy AND on real instruments on every metric: real
WEEKLY CAGR drops 33.34% → 32.49% and MaxDD widens −27.0% → −27.4%. The
weekly harness only re-decides weekly, so a 10-day reading is largely
stale in it, which is a principled reason to weight the daily test higher
— but that is an argument, not evidence, and the two real harnesses
disagree. Proxy per-year diffs are two-sided (2020 +5.8, 2018 +4.0, 2010
+3.7 against 2003 −4.2, 2026 −3.3, 2023 −2.5). Owner's call.

### Outside review round 2 (2026-09-07) — three real defects FIXED, one correction to the record

A second outside critique. Four of its six points were verified true against
the code; all are now fixed or measured.

**(a) FIXED — the live spec contradicted the code.** Part I's DETAILED
weight table still read A = 50/50 and the overlay chain still read 0.25 per
vote, two days after the code moved to 40/60 and ⅓. My 09-06 edit had caught
the at-a-glance table and missed these. Both weight tables and the overlay
chain are now GENERATED from `state.py` by `paper-track/gen_live_tables.py`,
and `consistency_check.py::check_strategy_md_matches_code()` fails the build
if this file disagrees with the code. (The same pass corrected state E's
effective exposure from 0.5x to 0.25x — 50% XLU at the documented 0.5x
weighting is 0.25x, and the table had been wrong since it was written.)

**(b) FIXED — the live weight function permitted silent fallback.**
`target_weights_with_voltarget()` accepts `fast_state=None`/`gaps=None` so
pre-overlay backtests still run; a live caller that omitted either silently
traded the PRE-OVERLAY design. New `live_target_weights(state, micro_agrees,
vol, fast_state, gaps)` takes both as REQUIRED positional arguments and
raises `MissingOverlayInputs`; both trigger prompts now call it.

**(c) FIXED — the exposure/beta-matched controls could not match upward, and
one of them measures the wrong thing.** Both helpers bisected on [0, 1], so
they could only scale the baseline DOWN. A candidate with HIGHER beta —
every rung of a leverage ladder — saturated at k = 1.0 and the "control"
was the UNSCALED baseline, reported as PASS. Both now expand the bracket and
return `beta_achieved`/`exp_achieved` and a `matched` flag; `controls()`
reports UNMATCHED instead of PASS. Separately, `exposure_control()` measures
DEPLOYED CAPITAL (the sum of the four risky weights), not leverage: A 50/50
and A 40/60 both deploy 100% and score identically, so that control is
uninformative for any change that shifts weight between a 1x and a 3x
instrument. Both limitations are now documented in the docstrings.

**CORRECTION to the 09-06 leverage note.** It said the beta-matched control
Sharpe "equals live at every rung, so leverage is a pure risk dial". That
equality was the saturation artifact, not a result. Corrected (baseline =
live A 40/60, beta 1.363):

| A row | candidate beta | matched control k | control Sharpe | candidate Sharpe |
|---|---|---|---|---|
| 50/50 | 1.270 | 0.932 | 0.924 | 0.912 |
| 40/60 (live) | 1.363 | 1.000 | 0.918 | 0.918 |
| 30/70 | 1.456 | 1.068 | 0.914 | 0.922 |
| 0/100 | 1.735 | 1.273 | 0.903 | 0.894 |

The control DOES move, and the comparison is mixed (the scaled baseline wins
at 50/50, the candidate wins slightly at 30/70), all within ±0.01 Sharpe.
The CONCLUSION — extra leverage buys no Sharpe — still stands, and rests on
the direct figures (proxy Sharpe flat, real Sharpe falling as leverage
rises), not on the control. The stated evidence was wrong; the decision was
not.

**(d) MEASURED — extension-threshold churn is real and large; hysteresis
FAILS the both-era bar.** The vote count changes 18.0x/yr, and **44% of
those changes reverse to the prior count within 3 sessions** (49% within 5,
51% within 10); 12.1% of effective-A days sit within 0.5pp of a threshold.
Per-window hysteresis (a window turns on above t+band, off below t−band):

| band | real daily CAGR / Sharpe / MaxDD | reb/yr | vote changes/yr | proxy Sharpe | holdout |
|---|---|---|---|---|---|
| 0 (live) | 31.86 / 1.154 / −33.2 | 55 | 18.0 | 0.918 | 0.771 |
| 1.0pp | 32.57 / 1.167 / −33.2 | 47 | 8.2 | 0.903 | 0.733 |
| 2.0pp | 28.95 / 1.072 / −33.2 | 44 | 4.1 | 0.847 | 0.709 |

A 1pp band more than halves the churn and improves the SPMO era, but costs
proxy Sharpe (0.918 → 0.903) and holdout Sharpe (0.771 → 0.733). Not
applied. Caveat: the proxy run carries hysteresis state across `evaluate()`'s
internal passes, which contaminates the first rows of a pass; the holdout gap
is far larger than that effect but the figure is indicative, not exact.
The reviewer's related point stands and is now recorded: the 100/150/200-day
gaps are ~0.9 correlated, so three votes are ONE signal read three ways, not
three independent confirmations — as the original note said, but the
"p = 0.00" phrasing oversold it. That p is "0 of 200 shuffles", i.e. p < 0.005,
and day-level shuffling breaks episode persistence, so it overstates
significance for a persistent signal. Block-bootstrap versions are the right
test and have not been run.

**(e) NOT FIXED, documented — execution alignment.** The trigger fires at
15:55 ET and uses that snapshot as a proxy for the session close, then trades
immediately; the backtest decides on d0's close and earns d0→d1. So live is
the backtest convention approximated five minutes early, NOT a day of
misalignment. Measured: one extra full session of lag costs 1.4pp CAGR
(31.9% → 30.5%) and 0.04 Sharpe, and costs the max(10,30) candidate more
(31.9% → 29.8%), so a faster estimator would raise our execution sensitivity.
Both prompts now state the convention explicitly and require readings to be
reported as a "15:55 snapshot", never as "the close".

**(f) OPEN — drawdown reconciliation.** The reviewer's longer synthetic
replay reaches −39% to −40% depending on the core proxy, against our −35.2%.
Different proxy construction (their SPMO substitute, financing model and
leveraged-ETF synthesis differ from ours) is the likely cause and has NOT
been reconciled. Until it is, treat −35% as OUR proxy's figure and roughly
−40% as a plausible alternative construction; neither is a loss ceiling.

**Answering "why not max(5–15, 30)"** (real daily, the decisive harness):
max(5,30) 31.45 / 1.208 / −32.5 at 81 rebalances/yr; **max(10,30) 31.94 /
1.206 / −30.1 at 69**; max(15,30) 31.78 / 1.185 / −30.9 at 66; max(20,30)
31.64 / 1.168 / −31.9 at 61. 10 is an interior optimum on drawdown and
CAGR, not a corner; 5 buys 12 more rebalances a year for a worse drawdown.
Still unapplied.

### Volatility estimator max(10d, 30d) — APPLIED 2026-09-07 (owner decision)

`VOL_FAST_LOOKBACK_DAYS = 10`, `VOL_ESTIMATOR_MAX_ENABLED = True`,
`realized_vol_live()` in `state.py`; live triggers call it instead of
`realized_vol()`. Taking the MAX means the fast window can only ever RAISE
the estimate, so it can only de-lever faster and never lever up faster.

| | proxy 26y | search / holdout | real weekly | real daily (band) |
|---|---|---|---|---|
| vol30 (was) | 23.60 / 0.918 / −35.2 | 1.112 / 0.771 | 33.34 / 1.233 / −27.0 | 31.86 / 1.154 / −33.2 |
| **max(10,30) (live)** | **23.55 / 0.942 / −34.7** | **1.158 / 0.781** | **32.49 / 1.240 / −27.4** | **31.94 / 1.206 / −30.1** |

Holds at 10bp and 20bp costs; turnover essentially unchanged (17.1 →
17.2x/yr) though rebalances rise 55 → 69/yr. A surface, not a spike: every
max(fast, slow) pair beats its own single-window counterpart, and 10 is an
INTERIOR optimum on the real daily harness — max(5,30) 1.208 Sharpe but 81
rebalances/yr and −32.5% MaxDD; max(15,30) 1.185; max(20,30) 1.168.

**Accepted costs, stated plainly.** This did NOT clear the usual bar
("better on the proxy AND on real instruments on every metric"): real
WEEKLY CAGR falls 33.34% → 32.49% and weekly MaxDD widens −27.0% → −27.4%.
The weekly harness re-decides only weekly, which largely wastes a 10-day
reading, so the daily harness is the more faithful test — but that is an
argument, not evidence, and the two real harnesses disagree. It also raises
execution sensitivity: an extra session of lag costs this estimator 2.2pp
of CAGR against 1.4pp for vol30.

**CORRECTION — this was NOT a new idea.** I told the owner we had never
tested a two-window max. Wrong: `improvement_search.py` T4 tested
`max(10d,30d)` on 2026-09-02 and the record REJECTED it ("proxy +0.016
Sharpe / −1.8pp MaxDD in both eras, but real instruments −0.73pp CAGR and
Sharpe 1.116 → 1.105. Mixed; not enough to justify a change"). The real
weekly CAGR cost is the SAME objection then and now. What is genuinely new
is the real DAILY result, which was not run in September, and the current
design (A 40/60, fast overlay, trim step ⅓) it now sits on top of.

**Harness consistency (bugs fixed the same day).** Changing the live
estimator silently makes any harness still on 30-day vol report a
DIFFERENT strategy than the one being traded. Fixed:
`monthly_returns.simulate()` and `voltarget_live_backtest.build()` now call
`realized_vol_live()`, which also flows to `return_frontier.real_rows()`
and `strategy_summary_data.py`. `improvement_search.build()` rows keep
`vol` as the plain 30-day reading so every figure recorded here before
2026-09-07 stays reproducible, and add `vol_live` for anything meant to
represent the live design. One bug was introduced and caught in the same
pass: `strategy_summary_data.py`'s OLD (2026-09-02 design) comparison
series began reading the new estimator too, flattering-then-misstating it
at 22.76% instead of 23.25%; the weekly row now carries both `vol` (live)
and `vol30`, and any pre-09-07 design is compared on its own spec.

**Unrelated pre-existing bug fixed.** `voltarget_and_sp500_test.py` crashed
with `KeyError: '2026-08-28'`: it derived its weekly calendar from the CORE
series alone and guarded only the core and signal series, so any other leg
(here XLU) ending earlier raised on `d1`. It now derives the calendar from
the intersection of every series a leg reads from and skips rows missing an
endpoint.

### Block bootstrap and leave-one-regime-out (2026-09-07) — the trim survives, the overlay and the estimator do NOT

`paper-track/block_bootstrap.py`. The outside review was right that day-level
shuffling destroys episode persistence and that "p = 0.00" (0 of 200 shuffles)
means p < 0.005, not zero. Replacing that null with a CIRCULAR BLOCK bootstrap
(2000 resamples, blocks of 20 and 60 sessions, paired on the same blocks, proxy
2000–2026 daily, 6575 sessions) materially weakens two of the three claims.

| change | point estimate | Sharpe 95% CI (60d blocks) | P(Sharpe diff ≤ 0) | verdict |
|---|---|---|---|---|
| fast re-entry overlay | +1.70pp/yr, +0.041 Sharpe | [−0.015, +0.096] | 0.080 | **NOT significant** |
| graded extension trim (step ⅓) | +2.30pp/yr, +0.143 Sharpe | [+0.025, +0.266] | 0.007 | **survives** |
| max(10,30) vol estimator | −0.04pp/yr, +0.024 Sharpe | [−0.012, +0.065] | 0.097 | **NOT significant** |
| all three together | +3.96pp/yr, +0.208 Sharpe | [+0.070, +0.348] | 0.002 | survives |

Log-return intervals are wider still: only the fast overlay and the composite
exclude zero (P ≈ 0.03), and the TRIM's return advantage does not
(P ≈ 0.10) even though its Sharpe advantage does. Block length barely matters
(20d and 60d agree), which is reassuring about the resampling itself.

**What this changes.** The earlier "p = 0.01" for the overlay and "p = 0.00"
for the trim were against an i.i.d. day-shuffled null and overstated both. The
honest position now: the extension trim has a Sharpe edge that survives a
persistence-respecting test; the fast overlay and the volatility estimator do
NOT clear 5% on their own, and are held on the strength of the point estimate,
the both-era behaviour and the controls, not on significance. The composite
design is significant, but that is partly the trim carrying it. Nothing is
being un-applied on this basis — it is a downgrade of confidence, not of the
design — but no future note should quote "p = 0.00" for these.

**Leave-one-major-regime-out** (drop the window, recompute the Sharpe
difference): every comparison keeps its sign in every drop, so none of it is
one episode. Fast overlay +0.033 to +0.062 (weakest without the GFC); trim
+0.121 to +0.153 (weakest without the SPMO era); estimator +0.010 to +0.028;
composite +0.193 to +0.229. Dropping the whole SPMO era — the window every
parameter was fit in — leaves the trim at +0.121 and the composite at +0.193,
which is the single most reassuring number here.

### Drawdown reconciliation (2026-09-07) — RESOLVED: it is execution lag

`paper-track/drawdown_reconciliation.py`. The outside replay reported ~−39% to
−40% against our −34.7%. Varying one construction choice at a time through the
repo's OWN engine (3% band, 4bp one-way cost, drift-and-hold):

| construction | CAGR | Sharpe | MaxDD |
|---|---|---|---|
| ours: QQQ core, 2000–2026 (standing) | 23.55% | 0.942 | −34.7% |
| restricted to 2000–2015 | 16.89% | 0.740 | −32.8% |
| SPY core instead of QQQ | 22.48% | 0.940 | −33.9% |
| financing +100bp | 22.70% | 0.916 | −35.1% |
| financing +100bp + SPY core | 21.65% | 0.913 | −34.1% |
| heavier fees (ER 1.5/1.2) + financing +100bp | 22.44% | 0.907 | −35.2% |
| **+ 1 extra session of execution lag** | **20.46%** | **0.846** | **−39.5%** |
| **+ 2 extra sessions of lag** | **18.53%** | **0.782** | **−40.3%** |

Core proxy, financing spread and expense ratios move the drawdown by at most
0.5pp and CANNOT account for the gap. **Execution lag accounts for all of
it**: one extra session gives −39.5%, two give −40.3%, bracketing the reported
−39% to −40% exactly. That is consistent with the reviewer's own stated
method — "completed-close signals and next-session-close fills" — which is
precisely one session later than our convention (decide on d0's close, hold
the d0 → d1 return). So the two figures are not in conflict: they measure the
same strategy under different execution assumptions, and the reviewer's own
point (1) about execution alignment is the explanation for their point (6).

**Operational consequence, and it is a real one.** Our −35% assumes we trade
at (or within five minutes of) the close on the signal date. A single session
of slippage costs 3.1pp of CAGR AND 4.8pp of drawdown. Execution discipline is
therefore not a bookkeeping detail — it is worth more than most of the design
changes argued over this week. The triggers now say so.

A note found while doing this: a first attempt reimplemented the simulation
loop standalone and produced 26.04% / −33.7% against the standing 23.55% /
−34.7%. The difference was entirely the engine — costless daily rebalancing
versus the band, the cost model and drift-and-hold. Always reconcile through
`improvement_search.run()`, never a fresh loop.

### A 40/60 → 50/50, reverted (2026-09-07, owner decision)

The 09-06 step to A 40/60 spent the step-⅓ trim's Sharpe gain on leverage.
After the block bootstrap the owner stepped back. The revert improves BOTH
Sharpe and drawdown on every harness and costs CAGR, which is exactly what
the leverage ladder predicted (real-instrument Sharpe falls monotonically as
A leverage rises):

| | 26y proxy | search / holdout | real weekly | real daily (band) |
|---|---|---|---|---|
| A 40/60 | 23.55 / 0.942 / −34.7 | 1.158 / 0.781 | 32.49 / 1.240 / −27.4 | 31.94 / 1.206 / −30.1 |
| **A 50/50 (live)** | **22.12 / 0.938 / −32.8** | **1.150 / 0.780** | **30.67 / 1.260 / −25.3** | **29.69 / 1.202 / −29.5** |

Real weekly Sharpe 1.260 is the highest recorded for any design in this file,
and −25.3% is the smallest real drawdown since the overlays went in. Cost:
1.8pp of real weekly CAGR. Proxy holdout is unchanged within noise
(0.781 → 0.780).

### VIX as the volatility-target input (2026-09-08) — NEGATIVE, not applied

> **Superseded on the instrument question by the VXN section below (2026-09-08).**
> VXN is the matched (Nasdaq-100) index and starts 2001, not 2008. Every
> conclusion here was re-run on it. The conclusions held; the reasoning did
> not need the wrong index to reach them.
>
> **CORRECTION, same day:** the "VIX starts 2008 / 51% holdout coverage"
> constraint stated in this section is WRONG. It was a property of the local
> file `/home/user/robinhood/data/kairos/VIXCLS.csv`, which is a truncated
> download, not of the series: FRED's VIXCLS runs from **1990-01-02**. The
> full series is now at `data/vixcls_full.csv`. The conclusions here are
> unaffected — they were re-derived on VXN, which is the right index
> regardless — but the coverage figure should not be quoted.

Asked by the owner: "have we tested VIX correlation?" VIX had been tested four
times before, always as a FILTER or SUBSTATE SPLITTER, and rejected every
time: level/change in the 0-for-6 defensive-layer search (09-01), median and
VIX>25 substate splits (`substate_research.py`, zero surviving combinations),
VIX rate-of-change for state F (`substate_research_deltas.py`, the headline
finding evaporated once the split was taken at the median — the "top quartile"
of VIX jumps had a *negative* median, i.e. it meant "VIX fell less"), and VIX
percentile as one of four signals in the state-A confidence composite
(validated on isolated holdout, then fully reversed by
`composite_turnover_cost.py`).

None of those asked the obvious remaining question. The vol overlay — the part
that actually sizes the book daily — runs entirely on REALIZED vol, and all
eleven candidates in `vol_estimator_family.py` are realized-vol windows.
Implied vol had never been in that family. Tested now in
`paper-track/vix_estimator_test.py`.

**Two constraints decided the design of the test.**

1. *Coverage.* VIXCLS starts 2008-01-02. The standing holdout is 2000–2015,
   so only 51% of holdout days (1,972 of 3,856) have VIX at all, and the
   2000–02 bear — the regime the holdout exists to test — is invisible to any
   VIX variant. Letting a VIX variant fall back to realized vol pre-2008 would
   silently blend two designs, so EVERY variant (realized included) is
   evaluated on the same 2008+ rows. These figures are therefore NOT
   comparable to the full-window numbers elsewhere in this file.
2. *Level vs timing.* Raw implied vol fed into min(1, 0.20/vol) changes how
   much risk is held, so any Sharpe difference would confound forecasting
   skill with de-levering — the trap the DMA-slope rule fell into. VIX is
   therefore tested both raw and rescaled by a single constant fitted on the
   SEARCH era only (k = mean(v30)/mean(VIX)), which removes the level
   difference and leaves only timing.

**Result: every VIX variant loses, in both eras, on proxy AND real
instruments, and with deeper drawdowns.** All rows 2008+, S = 2015-11+,
H = 2008–2015:

| estimator | proxy CAGR/Sharpe/MDD | S / H | real weekly |
|---|---|---|---|
| vol30 (ref) | 25.57 / 1.000 / −33.3 | 1.100 / 0.855 | 31.40 / 1.248 / −25.0 |
| **max(10,30) — LIVE** | **25.57 / 1.034 / −32.8** | **1.150 / 0.869** | **30.67 / 1.260 / −25.3** |
| VIX raw | 24.11 / 0.953 / −37.6 | 1.049 / 0.809 | 30.60 / 1.190 / −31.2 |
| VIX scaled | 23.31 / 0.946 / −37.0 | 1.036 / 0.809 | 29.42 / 1.173 / −30.9 |
| max(v30, VIX raw) | 23.41 / 0.960 / −33.1 | 1.061 / 0.811 | 29.72 / 1.224 / −25.8 |
| max(v30, VIX sc) | 22.88 / 0.956 / −33.1 | 1.054 / 0.811 | 28.98 / 1.212 / −26.2 |
| max(v10, v30, VIX sc) | 23.09 / 0.982 / −32.3 | 1.097 / 0.814 | 28.84 / 1.232 / −25.8 |
| 50/50 blend v30+VIX sc | 24.57 / 0.976 / −35.3 | 1.073 / 0.832 | 30.56 / 1.211 / −27.7 |

Not one variant beats the live estimator on either era. Scaling makes VIX
WORSE, not better, which kills the "it only looked bad because it de-levers"
defence — the level was not the problem, the timing was. ADDING VIX to the
live max(10,30) degrades it (1.034 → 0.982). Every VIX-driven variant carries
a deeper real drawdown than live (−25.8 to −31.2 vs −25.3).

**Why, mechanically.** VIX is a 30-day forward-looking estimate that
correlates +0.808 with trailing realized vol30 — it is mostly the same signal
with a lead. The overlay does not need a lead: it re-reads every session and
the drift band re-trades within days. What the overlay needs is a fast local
reading of how violent *this week* is, which max(10,30) supplies and a
30-day-horizon implied number smooths away. That is the same reason vol60
loses to vol30 and vol30 loses to max(10,30).

**Correlation, measured separately** (`paper-track/vix_corr.py`, 4,690
sessions 2008+, live design). Contemporaneous and predictive are reported
apart because conflating them is easy — an alignment bug in the first pass of
this very analysis did exactly that. `build()` sets `row['d'] = d0` and
`row['legs']` = the d0→d1 return, so pairing a return with VIX at `row['d']`
is a PREDICTIVE pairing, not a contemporaneous one:

| | |
|---|---|
| corr(strategy return, same-session VIX change) | **−0.535** |
| corr(QQQ return, same-session VIX change) | −0.753 *(sanity check)* |
| corr(strategy return, VIX level) | +0.003 |
| corr(VIX level at d0, next-session return) | +0.003 |
| corr(VIX change to d0, next-session return) | +0.032 |

Two things worth keeping. The strategy's sensitivity to VIX moves is about
**30% lower than QQQ's** (−0.535 vs −0.753) — that is the vol overlay and the
cash gate doing their job. And VIX has **no predictive content** for this
strategy's next-session return (+0.003 / +0.032), which is consistent with
four prior failures and with this one. High-VIX days are not bad days for the
book: top-decile VIX sessions average **+15.9 bp/day against +10.4 bp
overall**, because the strategy is already de-levered into BOXX by then.

**One caveat, stated rather than buried: VIX is S&P 500 implied vol, and this
design is entirely on QQQ.** The evidence is in the test's own output — the
variance risk premium came out NEGATIVE (mean VIX − mean QQQ vol30 = −1.34 vol
points, k = 1.0726), the opposite of the textbook, precisely because QQQ
realizes more vol than the S&P implies. The matched instrument is VXN
(Nasdaq-100). VXN was fetched and is real, but the available data plan caps it
at ONE YEAR (2025-09-08 → 2026-09-04), which cannot support the search/holdout
discipline. So the honest scope of this result is: *S&P 500 implied vol is not
a better input than QQQ realized vol for a QQQ vol target, clearly and in
every variant.* A VXN test remains open and would need a longer history than
this session can obtain.

Not applied, and nothing here argues for applying anything — the change freeze
is not the binding constraint, the result is.

### VIX % change, VIX cutoff, and DMA-on-VIX as overlays (2026-09-08) — NEGATIVE, not applied

> **Superseded on the instrument question by the VXN section below (2026-09-08).**
> VXN is the matched (Nasdaq-100) index and starts 2001, not 2008. Every
> conclusion here was re-run on it. The conclusions held; the reasoning did
> not need the wrong index to reach them.
>
> **CORRECTION, same day:** the "VIX starts 2008 / 51% holdout coverage"
> constraint stated in this section is WRONG. It was a property of the local
> file `/home/user/robinhood/data/kairos/VIXCLS.csv`, which is a truncated
> download, not of the series: FRED's VIXCLS runs from **1990-01-02**. The
> full series is now at `data/vixcls_full.csv`. The conclusions here are
> unaffected — they were re-derived on VXN, which is the right index
> regardless — but the coverage figure should not be quoted.

Owner follow-up to the estimator test: "also consider vix daily percentage
change and vix cutoff line — and what about the dma idea on vix". All three
were genuinely open. `substate_research_deltas.py` had tested VIX POINT deltas
and `substate_research.py` a VIX>25 cutoff, but both as SUBSTATE SPLITTERS on
weekly rows under sample floors that left several cells untestable — never as
global overlays. And the 0-for-6 search's DMA slope rule was on QQQ's own
moving average, never on VIX's. Tested in `paper-track/vix_overlay_test.py`
(40 candidates) and `paper-track/vix_dma_validate.py`.

Each overlay multiplies the four risky legs by g ≤ 1 AFTER the live trim and
vol target, so every one is a cash gate and `exposure_control()` is the right
control. All variants including the baseline run on the same 2008+ rows.

**Families A and B fail outright.** Daily-%-change triggers and level cutoffs
were swept across 5 thresholds × 2 de-lever depths and 7 × 2 respectively.
NOT ONE beat live in both eras. The best % -change variant (>25% → ×0.5,
Sharpe 1.100 vs live 1.095) is a near-no-op — daily VIX jumps above 25% are
rare enough that it barely fires. Cutoffs are worse the tighter they get:
VIX>18 → cash gives Sharpe 0.663 against live's 1.095, because a static line
sits the strategy out of most of the sample. Both ideas are answered.

**Family C — DMA on VIX — is the one that survives the screen, and by a lot.**
5 of 40 candidates beat live in both eras, all at a HALF de-lever (×0.5), all
with drawdowns 3–9pp shallower, all beating their exposure-matched control:

| rule | CAGR/Sharpe/MDD | S / H | expo | ctl Sharpe | reb/yr | real weekly Sharpe |
|---|---|---|---|---|---|---|
| **LIVE** | 26.55 / 1.064 / −32.8 | 1.150 / 0.938 | 70.7% | 0.890 | 68 | **1.260** |
| VIX>SMA20 ×0.5 | 21.32 / 1.119 / −23.2 | 1.238 / 0.951 | 56.4% | 0.907 | 86 | 1.261 |
| VIX>SMA50 ×0.5 | 22.60 / 1.154 / −25.6 | 1.261 / 1.006 | 57.9% | 0.905 | 79 | 1.195 |
| VIXsma20 rising ×0.5 | 22.29 / 1.158 / −26.2 | 1.306 / 0.949 | 55.7% | 0.907 | 83 | 1.287 |
| VIXsma50 rising ×0.5 | 21.00 / 1.091 / −25.8 | 1.173 / 0.975 | 56.1% | 0.907 | 77 | **1.361** |

**THE DISCRIMINATOR, and the one genuinely new finding here.** "VIX above its
own moving average" is a vol-is-accelerating detector, and QQQ's own REALIZED
vol has a moving average too. If realized-vol-DMA did the same job, VIX would
add nothing we cannot compute from price alone — no external feed, no
S&P-vs-Nasdaq mismatch, history back to 2000 instead of 2008. So the identical
four rules were run on realized vol30:

| rule | Sharpe | S / H | real weekly |
|---|---|---|---|
| RV>SMA20 ×0.5 | 0.996 | 1.016 / 0.967 | 1.249 |
| RV>SMA50 ×0.5 | 1.031 | 1.144 / 0.865 | 1.308 |
| RVsma20 rising ×0.5 | 1.019 | 1.110 / 0.884 | 1.270 |
| RVsma50 rising ×0.5 | 1.075 | 1.192 / 0.909 | 1.341 |

Every realized-vol version is WORSE than live (1.064) on full-period Sharpe,
and their bootstrap Sharpe differences are NEGATIVE (P(≤0) = 0.67–0.72).
So the VIX result is **not** just "vol accelerating" — implied vol carries
something trailing realized vol does not. That is the first time VIX has
added anything in this repo, and it is worth remembering.

**But it does not clear the bar, for two independent reasons.**

*The Sharpe gain is not distinguishable from noise.* Circular block bootstrap,
2000 resamples, paired, vs live: Sharpe P(≤0) = **0.124–0.266** across all VIX
variants at both block lengths; every 95% CI spans zero (e.g. VIX>SMA50
[−0.062, +0.243]). Nothing reaches 10%, let alone 5%.

*The return cost IS close to significant, in the wrong direction.* Point
estimates are **−3.2 to −4.2pp/yr** of log return with P(≤0) = 0.94–0.98, and
VIX>SMA20's 60-day-block CI is [−8.45, −0.03]pp — excluding zero on the losing
side. So this buys an unprovable Sharpe gain with a well-evidenced 3–4pp/yr
CAGR loss. That is the same trade the leverage ladder offered in the other
direction, which the owner declined on 09-07.

Three more marks against, none fatal alone: turnover rises 68 → 77–86
rebalances/yr; **no variant is best on both harnesses** (VIX>SMA50 has the top
proxy Sharpe and a WORSE real weekly figure, 1.195 vs 1.260; VIXsma50-rising
has the top real figure and a middling proxy) which is the signature of noise
being fitted across 40 candidates; and VIXsma20-rising's edge collapses to
+0.011 Sharpe when the SPMO era is dropped, i.e. nearly all of it is 2015+.
Leave-one-regime-out is otherwise favourable in sign for the VIX rules
(+0.067 to +0.127 across GFC / COVID / 2022 drops).

**Verdict: not applied.** The screen is real, the discriminator is real, the
significance is not. Recorded because the discriminator result is the one
thread worth pulling if VXN with a pre-2008 history ever becomes available —
the same open item left by the estimator test. 40 candidates were swept to
find 5 survivors; that is stated here rather than buried.

### Everything re-run on VXN, the matched index (2026-09-08) — NEGATIVE, not applied

Owner: "try everything with vxn instead — VXN has been available since January
2001." Correct on both counts, and it fixed the two defects the VIX work had
flagged against itself. Source: FRED `VXNCLS`, saved to `data/vxncls.csv`,
2001-02-02 .. 2026-09-04, cross-checked against an independent EODHD
`VXN.INDX` pull on the overlap (21.07 / 20.16 / 20.04, exact match).
Scripts: `paper-track/vxn_full_test.py`, `paper-track/vxn_validate.py`.

**The instrument mismatch is confirmed and repaired.** The VIX test measured a
NEGATIVE variance risk premium (mean VIX − mean QQQ realized vol30 = −1.34 vol
points), which is backwards and was itself the evidence of using S&P implied
vol against a Nasdaq strategy. On VXN it is **+2.66 vol points (k = 0.8815)** —
the textbook positive sign. And holdout coverage goes from **51% to 96%**: the
dot-com bust, invisible to every VIX variant, is now in the window.

**PART 1 — VXN as the vol-target input: still loses.** All on VXN-covered rows:

| estimator | CAGR/Sharpe/MDD | S / H | real weekly |
|---|---|---|---|
| **max(10,30) — LIVE** | 23.55 / **0.983** / −32.8 | 1.150 / 0.853 | 30.67 / **1.260** / −25.3 |
| VXN raw | 21.32 / 0.925 / −34.4 | 1.075 / 0.806 | 29.26 / 1.217 / −25.3 |
| VXN scaled | 22.34 / 0.917 / −37.1 | 1.059 / 0.804 | 31.14 / 1.220 / −28.3 |
| max(v30, VXN) | 21.22 / 0.931 / −32.4 | 1.077 / 0.817 | 29.12 / 1.243 / −24.6 |
| max(v10, v30, VXNsc) | 22.56 / 0.963 / −32.7 | 1.124 / 0.838 | 29.84 / 1.254 / −25.9 |

Nothing beats live in either era. The estimator conclusion therefore survives
the instrument correction and is no longer confounded by it.

**PART 2 — the overlay families collapse from 5 survivors to 1.** Same 40
candidates (% change × 5 thresholds, cutoff × 7, DMA × 8, all × 2 depths),
now on 6,237 rows from 2001-11. Exactly **one** beats live in both eras:

| | CAGR/Sharpe/MDD | S / H | expo | ctl | reb/yr | real wkly |
|---|---|---|---|---|---|---|
| **LIVE** | 23.66 / 0.984 / −32.8 | 1.150 / 0.854 | 67.8% | 0.780 | 68 | **1.260** |
| VXN SMA20 rising ×0.5 | 19.58 / 1.039 / −27.5 | 1.240 / 0.889 | 53.2% | 0.801 | 81 | 1.271 |

**That collapse is the headline.** On the WRONG index over a SHORTER window,
five of forty survived. Moving to the RIGHT index with 25 years instead of 18
should strengthen a real signal; instead it eliminated four of the five,
including both of the VIX front-runners. One survivor in forty is roughly what
chance delivers at a nominal 5% threshold. The VIX "survivors" were noise.

**The discriminator REPLICATES, and it is the one durable finding.** The same
rules on QQQ's own realized vol30: RVsma20-rising 0.924, RV>SMA50 0.929 —
both below live's 0.984, with bootstrap Sharpe differences NEGATIVE
(P(≤0) = 0.80, 0.81). So implied vol really does carry something trailing
realized vol does not, and that now holds on both indices independently. It is
a genuine asymmetry. It is simply not big enough to matter.

**The survivor still fails significance, and fails it the same way.** Block
bootstrap vs live, 2000 resamples, paired, 6,379 sessions:

- Sharpe: point +0.055, **P(≤0) = 0.181–0.208**, 95% CI [−0.074, +0.183] —
  spans zero, nowhere near 5%. (VIX's best was 0.124; VXN's is *worse*.)
- Log return: point **−3.35pp/yr**, P(≤0) = 0.973–0.977, 20-day-block CI
  [−6.67, −0.06]pp — **excludes zero on the losing side.**

Leave-one-regime-out is genuinely favourable this time and now includes the
dot-com bust: +0.066 (dot-com), +0.087 (GFC), +0.048 (COVID), +0.068 (2022),
+0.035 (SPMO era) — all positive, which the VIX version could not demonstrate.
Turnover rises 68 → 81 rebalances/yr. Real weekly is a wash: 1.271 vs 1.260.

**What this family actually is.** Every variant that "works" cuts deployed
capital from ~68% to ~53%, buys 5–7pp of drawdown (−32.8% → −26 to −29%), and
costs 3–5pp/yr of CAGR, with a Sharpe change inside noise. That is a RISK
PREFERENCE DIAL, structurally identical to the leverage ladder — the same
trade the owner declined on 09-07, pointing the other way. It is not an edge.
Against the standing objective (outperform SPY and QQQ) a 3–4pp/yr CAGR give-up
is the wrong direction, so this would need to be wanted for its drawdown, not
adopted for its Sharpe.

**Verdict: not applied.** Three VIX/VXN research lines are now closed —
implied vol as the estimator input, as a % -change trigger, as a level cutoff,
and as a DMA overlay. The volatility-index question is answered on the correct
instrument with 25 years of history; it does not need revisiting.

### The VXN−VIX vol gap as a core/satellite tilt (2026-09-08) — STRONGEST CANDIDATE, still not applied

Owner's idea: "SPMO is based on S&P 500 / VIX; TQQQ and QLD are based on QQQ /
VXN. So if we look at both volatilities and track the gap in between, should
help with our weights?" This is the best-posed question put to the design so
far, and it exposes a real inconsistency worth stating on its own: **the vol
overlay scales the WHOLE book — the SPMO leg included — by min(1, 0.20 / QQQ's
realized vol). The S&P sleeve is being sized by the Nasdaq's volatility.**

It is also structurally different from every VIX/VXN candidate before it.
Those were all CASH GATES, which "work" by holding less risk and died to
`exposure_control`. This is a TILT BETWEEN TWO RISKY LEGS at constant deployed
capital: when the gap is wide (Nasdaq priced to be relatively more violent),
shift weight from TQQQ to SPMO; when narrow, the reverse. So the de-levering
confound does not apply and `beta_matched_control` / a constant-tilt control
are the right tests.

**Two harness problems had to be fixed first, both caught in this session's
own output.**

1. *The 26-year proxy is structurally blind to this.* `improvement_search.data()`
   models `core` as QQQ total return, so in the proxy BOTH legs are QQQ and
   there is no S&P/Nasdaq divergence to exploit. STRATEGY.md already said the
   proxy is blind to core-leg questions. Fixed by building an **SPY-core
   proxy** — the same machinery with `core` swapped to SPY total return.
   Validated: with core left as QQQ it reproduces the standing figures exactly
   (22.12 / 0.938 / −32.8, S 1.150 H 0.780).
2. *The first threshold was contaminated.* Using the SEARCH-era median of the
   gap put only 31% of all rows and **5% of holdout rows** above it — the rule
   spent 2001–2015 permanently tilted to the satellite, i.e. adding leverage
   with a threshold fitted on later data. That is why all 8 first-pass
   variants "won" and won monotonically in delta. Replaced with a **causal
   trailing median** (500 sessions), built once from the DAILY series and
   attached by date — an earlier attempt built it per-row-list and burned 500
   *weeks* on the weekly rows, cutting real confirmation from 564 rows to 64.

**Result on the corrected harness** (SPY-core proxy 2003–2026, 5,927 rows;
real SPMO weekly 564 rows; tilt δ = 0.20 between core and TQQQ in states A/B):

| | CAGR/Sharpe/MDD | S / H | beta | real weekly |
|---|---|---|---|---|
| **LIVE** | 23.98 / 1.016 / −32.0 | 1.151 / **0.901** | 1.352 | 1.260 |
| const tilt δ=0.05 (no signal) | 24.94 / 1.019 / −33.1 | 1.157 / 0.903 | 1.403 | 1.254 |
| **gap tilt δ=0.20** | 26.57 / **1.063** / −36.5 | 1.271 / 0.890 | 1.384 | **1.372** |
| gap tilt δ=0.20, SIGN-FLIPPED | 20.27 / 0.896 / −33.9 | 0.953 / 0.847 | 1.320 | 1.075 |

**The signal is real.** Both controls pass decisively. Against a constant tilt
carrying the same beta it adds **+0.044 proxy / +0.118 real** Sharpe — so it is
not disguised leverage. Sign-flipped it collapses (1.063 → 0.896 proxy,
1.372 → 1.075 real), which a noise signal cannot do. Real-instrument
confirmation is large and consistent across both gap definitions (1.372 with
the implied gap, 1.377 with the realized one, vs live's 1.260).

**But it fails this project's own bar, and it fails it on the evidence that
matters most.** Extending the window to include the GFC — possible only after
the data correction below — flipped the holdout: **H 0.890 vs live's 0.901**,
so it no longer improves in both eras. Block bootstrap Sharpe P(≤0) =
**0.115 / 0.120**, well short of 5%. On the shorter 2010+ window it had looked
like P = 0.029; the entire Sharpe result was concentrated in a stretch with no
bear market in it. Max drawdown worsens 32.0% → 36.5%.

What *is* significant is the RETURN: **+2.07pp/yr, P(≤0) = 0.019**, 95% CI
[+0.12, +4.09]pp at both block lengths. So this is a genuine
return-frontier step with a real timing signal inside it — more CAGR, deeper
drawdown, Sharpe up but not provably so. That is a risk-preference decision,
not an edge, and it belongs to the owner rather than to a backtest.

**Verdict: not applied, and the change freeze is not the only reason.** It is
recorded as the strongest candidate this line of research has produced and the
one worth re-examining when the freeze lifts on 2026-12-07 — with fresh
attention to the holdout, since that is where it breaks.

**DATA CORRECTION, and it invalidates a constraint asserted earlier today.**
`/home/user/robinhood/data/kairos/VIXCLS.csv` starts 2008-01-02, and both VIX
sections above cite that as the limit of the data. It is not — it is a
truncated download. FRED's VIXCLS runs from **1990-01-02**, now saved as
`data/vixcls_full.csv`. With it, the implied gap runs from 2003 instead of
2010, which is what made the holdout test above possible and what changed the
answer. The earlier VIX conclusions stand (they were re-derived on VXN, the
correct index), but any "VIX only starts 2008" claim in this file is wrong.
Correlation between the implied and realized gaps also rises from +0.739 to
**+0.914** on the full series — they are very nearly the same signal.

Scripts: `paper-track/volgap_test.py` (SPY-core proxy, first pass and its
controls), `paper-track/volgap_causal2.py` (causal threshold, final result).

### Per-leg and blended vol targeting (2026-09-08) — NEGATIVE, and it RESOLVES the "inconsistency"

Owner: "test blended vol, or SP vol for SPMO, QQQ vol for TQQQ/QLD." This is
the direct fix to the thing the vol-gap work flagged — the overlay sizes the
whole book, SPMO included, by min(1, 0.20 / QQQ's realized vol), so an S&P
sleeve is sized by Nasdaq vol. Tested in `paper-track/perleg_vol_test.py`.

**Test design is the whole ballgame here.** Mean QQQ vol over the window is
**24.14%** against SPY's **17.94%**, a ratio of 1.346. So ANY variant feeding
SPY vol into min(1, T/v) yields a higher multiplier, de-levers less, and holds
more risk — and would score better for that reason alone. Comparing at a fixed
T = 0.20 would have been meaningless and would have "confirmed" the idea. Every
variant therefore has its target constant **T re-calibrated by bisection until
its average deployed exposure matches live's exactly (66.21% for all)**. Risk
is constant by construction; only the SHAPE of the signal differs.

| variant | T* | expo | CAGR/Sharpe/MDD | S / H | real weekly |
|---|---|---|---|---|---|
| **LIVE — QQQ vol for everything** | 0.200 | 66.21% | 20.82 / **0.934** / −32.0 | **1.151 / 0.770** | **1.260** |
| per-leg SPY for SPMO, QQQ for TQQQ/QLD | 0.175 | 66.21% | 19.31 / 0.910 / −30.3 | 1.122 / 0.751 | 1.253 |
| blended vol (weight-weighted) | 0.174 | 66.21% | 19.33 / 0.899 / −30.5 | 1.120 / 0.733 | 1.243 |
| blend, leverage-aware (3× / 2×) | 0.320 | 66.21% | 18.48 / 0.891 / −31.0 | 1.112 / 0.726 | 1.279 |
| SPY vol only (control) | 0.152 | 66.21% | 19.40 / 0.880 / −35.9 | 1.107 / 0.709 | 1.225 |

**Every variant is worse than live, in both eras, and the ordering is
monotone in how much the design leans on S&P vol:** 0.934 (QQQ only) → 0.910
(per-leg) → 0.899 (blend) → 0.891 (leverage-aware) → 0.880 (SPY only). Block
bootstrap on the per-leg variant: Sharpe **−0.024, P(≤0) = 0.944–0.955**, and
return **−1.26pp/yr with P(≤0) = 0.999–1.000**, CI [−2.01, −0.54]pp excluding
zero on the losing side. It is not a wash — it is reliably worse.

**Why, and this is the useful part: the "inconsistency" is not a defect, it is
the correct choice.** The book's risk is Nasdaq-dominated. Even in state A at
50/50, TQQQ is 3× QQQ, so roughly three quarters of portfolio variance comes
off the QQQ side. QQQ vol is therefore a BETTER proxy for the portfolio's own
risk than any leg-weighted blend of the two indices. Sizing the SPMO leg by
the calmer S&P reading keeps that leg fully deployed exactly when the Nasdaq
side is blowing up — which is when the whole book should be smaller. The
single-index rule is not sloppiness carried over from an earlier design; it
happens to be the right risk proxy for this specific mix.

One honest point in the idea's favour, not enough to change the verdict:
per-leg and blended both give a SHALLOWER max drawdown (−30.3%, −30.5% vs
−32.0%). If drawdown were the only objective they would be worth another look.
They cost Sharpe, return and both eras to get it.

Note this does NOT contradict the vol-gap tilt section above. That asks whether
the RELATIVE WEIGHTS between legs should respond to the vol gap, and finds a
real signal. This asks whether each leg should be SIZED by its own index's vol,
and finds that it should not. Different questions; the answers are independent.

Caveat: SPY vol proxies SPMO's vol on both harnesses — SPMO is an S&P momentum
sleeve and daily SPMO history is not in the repo. A true SPMO vol series would
sit between SPY's and QQQ's, which if anything weakens the tested variants
further, since the ordering above is monotone toward QQQ vol.

### Five volatility research lines (2026-09-08, owner-directed, run independently)

After a day in which every vol-based TIMING overlay failed and vol as a
SCALING input kept working, the owner asked for five remaining ideas to be
tested independently and deeply. Each ran under the shared contract in
`paper-track/research_notes/BRIEFING.md` (reuse the harness, causal
thresholds, same rows for every variant, exposure/beta match, placebo,
block bootstrap, leave-one-regime-out, report the candidate count). Full
writeups in `paper-track/research_notes/<line>.md`. Verdicts on one scale:
*no signal / signal too small / risk-preference dial / candidate*.

#### Line 5 — vol-modulated hysteresis buffer — NO SIGNAL

The 50/200 classifier uses a fixed 1% hysteresis. Hypothesis: scale the
buffer with realized vol so noise does not flip the state in turbulent tapes.
`paper-track/vol_hysteresis.py`, 21 variants (clamp range × estimator ×
macro/fast/both), buffer path pinned so its SEARCH-era mean equals 1%
(shape changes, mean does not). Sanity: a constant-1% variant reproduces
`compute_states()` element-for-element and the rebuilt rows reproduce live
exactly.

| variant | Sharpe | S / H | real | whipsaws (10d) |
|---|---|---|---|---|
| **LIVE** | **0.938** | **1.150 / 0.780** | **1.260** | 91 |
| macro, live-vol, clamp 0.2–4% | 0.915 | 1.123 / 0.760 | 1.250 | 97 |
| fast only, live-vol, 0.5–2% (best) | 0.936 | 1.141 / 0.783 | 1.260 | — |
| both, vol30 | 0.899 | 1.113 / 0.739 | 1.246 | 103 |
| **sign-flipped placebo** (narrower in turbulence) | 0.947 | 1.162 / 0.787 | 1.268 | 123 |

0 of 21 beat live in both eras. The placebo — the *opposite* of the
hypothesis — beats it in all six pairings, and is itself inside noise
(bootstrap P(≤0) = 0.31). Year-block-shuffled vol: P(placebo ≥ real) = 0.73.

*Why, measured:* the premise is true — whipsaws per 1,000 days run 5.9 / 14.1
/ 21.4 across vol terciles. But the vol-scaled buffer cuts high-vol whipsaws
47 → 29 while raising low-vol 13 → 31 and mid 31 → 37: net **91 → 97**. It
relocates whipsaws from turbulent to calm tapes and adds more than it
removes, while delaying genuine breaks where delay costs most (2009: −2.2 to
−4.2pp). Whipsaw count is not the objective; T2's rejection of a wider fixed
buffer stands.

#### Line 2 — vol-normalized (z-scored) extension trim — NO SIGNAL

The trim is the one overlay that survived the block bootstrap, so this tried
to refine it: express each gap as a z-score (gap ÷ vol·√(n/252)) so a 10%
stretch means the same thing at 12% vol and 35% vol. `paper-track/zscore_trim.py`,
41 variants + 20 placebo draws; k calibrated so the A-day vote frequency
matches live's, so it changes WHEN the trim fires, not how often.

| variant | fire rate S/H | expo | Sharpe | S / H | real |
|---|---|---|---|---|---|
| **LIVE price rule** | 25.8 / 26.0% | 66.2% | **0.938** | **1.150 / 0.780** | **1.260** |
| z-live, per-window k | 24.2 / 16.6% | 66.9% | 0.898 | 1.140 / 0.719 | 1.178 |
| z-live, k re-calibrated to live exposure | 26.3 / 18.3% | 66.2% | 0.890 | 1.118 / 0.722 | 1.201 |
| z-live, expanding causal quantile | 26.2 / 40.8% | 60.6% | 0.960 | 1.101 / 0.850 | 1.068 |

0 of 41 beat live in both eras; the one headline above live (0.960) holds
6pp less capital and live scaled to that exposure gives 0.946 — a dial that
also loses search and real. Bootstrap z vs live: −0.072 Sharpe, P(≤0) = 0.895.
Leave-one-regime-out negative in every drop.

*Why, and this is the finding worth keeping.* Where the two rules disagree,
QQQ's forward 21-session return tells the story:

| A-days | n | mean vol | 21d fwd return | harness P&L, z − live |
|---|---|---|---|---|
| both trim | 470 | 14.0% | **−0.31%** | +2.2pp |
| live trims, z holds | 542 | 23.0% | +1.38% | +7.7pp |
| z trims, live holds | 318 | **8.9%** | +0.96% | **−28.1pp** |

A z-score fires when vol is *low* by construction — it trims the 9%-vol
calm grind-ups (2013/2014/2017) where trimming forgoes drift and removes
almost no variance, and holds through the 23%-vol post-crash melt-ups where
the vol target has already sized the book at ~0.87 anyway. The only bucket
with negative forward returns is where both rules agree. The price-gap trim
works precisely because it is NOT vol-normalized: "extended" in price terms
is the overheated signal; "extended in sigma terms" is a low-vol signal in
disguise. Same lesson as the rest of the day — vol scales, vol does not time.

#### Line 4 — volatility term structure (VIX vs 3-month VXV) — SIGNAL TOO SMALL

Front-month against 3-month implied vol; backwardation (near > far) is stress
that is here rather than forecast. `paper-track/vol_term_structure.py`, data
`data/vxvcls.csv` (FRED, 2007-12+). FRED has no short-end, no 6-month and no
Nasdaq term-structure series — all probed — so this is an S&P slope applied
to a QQQ book; checked directly, it forecasts QQQ forward vol (36.2%) as well
as SPY's (35.6%) in the stress cell, so the instrument mismatch that killed
VIX-level signals did not bite here. Baseline on the 4,710 VXV rows: 25.29% /
1.024 / −32.8%, S 1.150 H 0.848. Dot-com is outside the window.

*Mechanism first.* Backwardation covers 10.1% of days in 131 episodes with a
**median run of one day**; 80% overlaps high realized vol; it fires on 2% of
state-A days vs 38–44% of E/F days. Forward 21-day QQQ return in
backwardation is **+2.32%** vs +1.24% in contango (t = 0.5) — no return
penalty, because the stress has already happened. What it does forecast is
*vol*: forward/current vol 0.81 vs 0.77 after conditioning on level. That ~5%
relative difference is the entire incremental content.

| use | ΔSharpe vs exposure-matched live |
|---|---|
| cash gate on top of the vol target (g = 0 / 0.5) | −0.000 / +0.016, fails search era |
| gate INSTEAD of the vol target, matched | −0.011 to −0.041, MDD 2–5pt worse |
| **modulator** of the vol target, h = 1.25 / 1.5 / 2.0, T re-calibrated | **+0.011 / +0.016 / +0.017, both eras**; sign-flip loses; MDD flat |
| rebalance trigger on entry into backwardation | +0.0003, inside a random-rebalance placebo band |
| realized 10d/60d ratio (discriminator) | −0.021 — the implied slope knows something realized does not |

24 candidates, 5 both-era (4 are the same modulator family). Every bootstrap
Sharpe CI straddles zero (h = 1.5: [−0.027, +0.064], P(≤0) = 0.25); dropping
COVID cuts the modulator to +0.002–0.006; real rows agree in sign and size;
2022 is a −2.4pp loss year. Directionally right in every control and too
small to matter: the vol target already captures most of what the slope
knows. It cannot replace the vol target, and as a cash gate or a trigger it
is a null.

#### Line 3 — range-based volatility estimators — NO SIGNAL (and a useful reason)

Parkinson / Garman–Klass / Rogers–Satchell / Yang–Zhang estimators as
drop-in replacements for the live max(cc10, cc30). `paper-track/range_vol.py`.
First job was data: a full-history QQQ OHLC series now exists at
`data/qqq_ohlc.csv` (1999–2026, opens and closes matching the long history
**to the cent on 6,784 of 6,784 days**, independently cross-checked). The
estimators were verified on synthetic GBM: 5.7–9.2× the efficiency of
close-to-close at n = 10, exactly as the literature says.

41 candidates, exposure-matched by re-calibrating T to live's 66.21%:

| variant | T* | Sharpe | S / H | reb/yr | real weekly |
|---|---|---|---|---|---|
| **LIVE max(cc10, cc30)** | 0.200 | **0.938** | **1.150 / 0.780** | 68 | **1.260** |
| GK10 | 0.147 | 0.926 | 1.123 / 0.773 | 77 | 1.226 |
| YZ10 | 0.179 | 0.910 | 1.117 / 0.753 | 77 | 1.206 |
| max(GK10, cc30) | 0.189 | 0.920 | 1.102 / 0.780 | 59 | 1.243 |
| max(GK5, GK30) (best) | 0.166 | 0.940 | 1.134 / 0.790 | 68 | 1.238 |

0 of 41 both-era at matched exposure; the top three sit at bootstrap P(≤0)
≈ 0.5 and lose on both real harnesses (real daily 1.185 vs 1.202). At a
fixed T = 0.20 the naive swap is a leverage dial: range estimators read low on
QQQ, so the book holds 70–71% instead of 66% and drawdown goes to −36…−41%.

*Why — the finding worth keeping.* The extra precision is real (placebo:
0.940 vs 0.891 block-permuted) but it lands in the wrong place. Range
estimators are sharper in the **calm** region (forecast RMSE 0.34 vs 0.41),
where a cap-1.0 overlay does nothing anyway. In the **bite** region
(forward vol > 20%) live's max(cc10, cc30) is the *best* forecaster tested
(RMSE 0.394 vs GK10's 0.477), because **~30% of QQQ's crash variance is
overnight gaps** — which intraday ranges never see. Yang–Zhang, which models
the overnight component, is unbiased on synthetic data but still loses live,
because its gap term is just close-to-close by another name. The live
estimator is close-to-close precisely where it matters.

#### Line 1 — variance risk premium as a time-varying signal — SIGNAL TOO SMALL

VXN minus QQQ realized vol, used as a causal daily series rather than the
single constant it had been. `paper-track/vrp_signal.py`, full output in
`research_notes/vrp_signal_run.log`. 63 variants (28 tilts, 35 vol-target
modulators), every one with sign-flip, QQQ-core and real-row runs, plus 18
decomposition controls. Same rows for all: 6,176 proxy rows from 2002-02
(live on those rows 22.76 / 0.986 / −32.0, S 1.151 H 0.852) and all 564 real
rows. The research agent finished the science and was cut off by a session
limit before writing the note; the note was written from its final run.

*The effect exists at a fraction of the textbook size.* Causal trailing
quintiles: top-VRP days see QQQ +1.98% over the next 21 sessions vs +0.70% for
bottom-VRP, but the spread is t = 1.2 with overlap respected, the middle
quintiles are not monotone, and next-day predictive correlation is +0.027
(t 2.2) and gone by 21 days.

*As a modulator of the vol target, exposure-matched* (m = min(1, T/(vol·e^(−k·vrp))),
T re-bisected to live's 69.28%): 17 of 35 both-era, every sign-flip loses,
drawdown flat-to-better.

| variant | Sharpe | S / H | vs live | real | bootstrap Sharpe P(≤0) |
|---|---|---|---|---|---|
| **live** | 0.986 | 1.151 / 0.852 | — | 1.260 | — |
| q10 exp k=4 (best) | 1.014 | 1.213 / 0.857 | +0.028 | 1.276 | — |
| q21 exp k=2 | 0.999 | 1.170 / 0.861 | +0.013 | 1.271 | **0.10** |
| q30 exp k=2 | 0.995 | 1.160 / 0.862 | +0.009 | 1.274 | 0.18 |

The RETURN gain clears 5% for several (q21 k=2: +0.6pp/yr, CI [+0.08, +1.12],
P = 0.01); the SHARPE gain never does (P 0.10–0.34). Decomposition is the
useful result: implied-level-only gives −0.001…−0.042, realized-only gives
−0.021…+0.003, the premium gives +0.009…+0.028 — **it needs both halves, so
it is the premium, not a convex vol response**. Leave-one-regime-out positive
in every drop for every survivor; survives 10bp costs, dies at 20bp; survives
5-session smoothing (which also cuts churn). As a core/satellite tilt it is
weaker (2 of 28 both-era, P ≈ 0.21).

Best-of-63, +0.01–0.03 Sharpe, +0.5–0.9pp/yr — inside the execution-lag cost
the project already measured (3.1pp/yr per session). Real, consistent, and too
small to act on.

### Recovery participation, event by event (2026-09-09) — protection pays, and the vol target is the rule that delays re-entry

Owner's reframing after two days of indicator research: "whether protection
pays for its subsequent recovery cost across many episodes, rather than just
improving maximum drawdown." `paper-track/recovery_study.py`; full writeup and
session-by-session 2008–09 / 2020 paths in `research_notes/recovery_study.*`.
Episodes defined systematically: every QQQ close ≥15% off its trailing-252
high, 11 primary (2000–02 −83%, 2004, 2006, 2007–08 −54%, 2010, 2011, 2015–16,
2018 −23%, 2020 −29%, 2021–22 −36%, 2025 −23%), 18 secondary at 8–15%. Each
scored peak→trough, trough→QQQ's regain, and compounded end to end on a $200k
book, at 4/10/20bp. Standing figures reproduced first.

**Did protection pay?** LIVE over the 11 episodes, compounded:

| cost | vs QQQ buy-and-hold | episodes paid | vs base allocations (no overlays) | paid |
|---|---|---|---|---|
| 4bp | +$243k | 4/11 | +$214k | 8/11 |
| 10bp | +$182k | 4/11 | +$191k | 8/11 |
| 20bp | +$86k | 3/11 | +$157k | 7/11 |

The split by depth is the finding. In the seven **15–25% corrections** the
design loses to buy-and-hold in 6 of 7 (−$132k summed, ~−10pp each) while
still beating base allocations in 6 of 7. In the four **>25% bears** it earns
+$376k vs QQQ and +$128k vs base. Real SPMO/TQQQ rows (5 episodes, 2015+)
show the same shape: +20.9pp vs base (3/5), −19.3pp vs QQQ (1/5). Block
bootstrap on episode windows only: LIVE vs base +8.2pp/yr, P(≤0) = 0.03 at
4bp and 0.06 at 20bp. **The recovery miss is real** — recovery halves alone,
LIVE vs QQQ −9.9pp/yr, P = 0.94, and at 20bp the CI [−29, −4] excludes zero —
**and the decline halves pay for it.** So the design is what the leverage
ladder already implied: a risk-preference dial that gives up ~10pp per
ordinary correction to earn $60–220k per real bear, not a free lunch.

**Which rule delays re-participation** (leave-one-out, 4bp, variant minus LIVE):

| rule removed | Σ peak→trough | Σ trough→recovery | median re-entry delay | Σ $ vs QQQ | recovery-half bootstrap |
|---|---|---|---|---|---|
| fast re-entry | +9.6pp | **−74.8pp, worse in 11/11** | 0 | −$89k | LIVE better **+8.7pp/yr [+4.7, +13.1], P = 0.000** |
| extension trim | −26.4 | +15.7 (2009 +22, 2023 +10, 2003 −16) | 0 | −$56k | −1.3pp/yr, P = 0.58 |
| max(10,30) → vol30 | −18.5 | +21.6 | 0 | −$16k | −2.1pp/yr [−3.3, −1.1] |
| **vol target** | **−72.5** | **+130.9** | **+19 sessions (108 in 2008–09)** | −$53k | **−12.4pp/yr [−20.1, −5.1], P = 1.000** |

*The vol target is the rule costing recovery.* It delays re-entry by a median
19 sessions — 108 in 2008–09, where it held the multiplier at 0.47–0.58
through March–April 2009 — and costs 12.4pp/yr of recovery-window return with
a CI excluding zero at every cost level. In 2020 it alone did all the work
and all the damage: multiplier 0.19 at the trough, still 0.25 on 04-14 when
the state returned to A, 0.78 by 05-29. The max(10,30) estimator adds a small,
certain second-order drag (−2.1pp/yr) in the same phase.

*The fast re-entry overlay is the one rule that unambiguously buys recovery*:
+8.7pp/yr, better in 11 of 11 proxy and 4 of 5 real episodes — the strongest
single-rule result in this file, and stronger than its whole-sample bootstrap
(P = 0.080) suggested, because its entire contribution is concentrated in the
turns. *The trim* is a wash on recovery: its 2009/2023 cost is repaid by 2003
and by the 18 shallow pullbacks.

**Why this does not argue for simplifying.** The VT's decline-phase
protection (−72.5pp summed) exceeds its recovery cost in compounded dollars at
4, 10 and 20bp (+$53k / +$66k / +$83k over the 11 episodes); the whole-window
bootstrap is a wash (+2.1pp/yr, P = 0.29); and dropping it on the full sample
takes the book to 22.64% / 0.831 / −49.4% with both era Sharpes lower. Any
attempt to release the VT faster after a trough is a vol-*timing* change —
the class that failed every test this week. Candidate count 0; nothing added.

At both the 2007-10-31 and 2020-02-19 peaks the trim had 3 votes and LIVE held
zero risky weight — transient, gone within two weeks, and the right call both
times. Worth knowing when it happens live.

### Full overlay interaction test, 2³ + vol-target extension (2026-09-09) — overlays are additive; one simpler cell is inside LIVE's noise

Owner-directed: all eight on/off combinations of fast re-entry (F), extension
trim (T) and the max(10,30) estimator (E), base allocations and execution
fixed, plus vol target on/off as a 16-cell extension. `paper-track/overlay_interactions.py`;
writeup in `research_notes/overlay_interactions.md`. 16 pre-specified cells,
no search. LIVE cell reproduced exactly. (Harness note it surfaced and the
briefing now carries: on real rows `r['vol']` is already max(10,30) and
`r['vol30']` is the plain 30d — the first run lost E's real effect to that.)

| cell | CAGR / Sharpe / MDD | S / H | expo | reb/yr | real CAGR / Sharpe / MDD |
|---|---|---|---|---|---|
| — — — (base + VT only) | 17.98 / 0.739 / −36.4 | 0.922 / 0.594 | 75.5% | 42 | 26.60 / 1.004 / −31.4 |
| — T — | 19.84 / 0.856 / −36.0 | 1.077 / 0.684 | 66.0% | 50 | 29.98 / 1.227 / −24.7 |
| F — — | 19.77 / 0.779 / −34.8 | 0.937 / 0.655 | 77.4% | 47 | 27.99 / 1.030 / −31.4 |
| **F T —** (plain 30d vol) | **22.15 / 0.912 / −33.3** | **1.100 / 0.769** | 67.7% | **55** | **31.40 / 1.248 / −25.0** |
| **F T E = LIVE** | **22.12 / 0.938 / −32.8** | **1.150 / 0.780** | 66.2% | **68** | **30.67 / 1.260 / −25.3** |
| no vol target (F T, V off) | 22.64 / 0.831 / −49.4 | — / 0.657 | | | |

Ordering is unchanged at 10bp and 20bp. Main effects on Sharpe: **T +0.129,
F +0.046, E +0.024**; every two- and three-way interaction is ≤ 0.008 — an
order of magnitude below the smallest main effect. **The overlays are
additive**, each worth slightly *more* in the live context than alone (mild
complementarity, no duplication): return-difference correlations ≤ 0.05, T
and E overlap on 133 of 6,575 sessions.

**Marginal removals from LIVE**, paired block bootstrap:

| remove | Δ log-return | Δ Sharpe | Sharpe CI (20d / 60d blocks) | verdict |
|---|---|---|---|---|
| **trim (T)** | +1.99pp | **+0.141** | [+0.018, +0.259] / [+0.030, +0.250], P ≤ 0.015 | earns its place, unambiguously; +0.222 real |
| **fast re-entry (F)** | **+1.82pp** | +0.053 | [−0.006, +0.113] / [−0.008, +0.122], P ≈ 0.045; log-return CI [+0.30, +3.38] P = 0.008 | earns its place as a *return* overlay; largest holdout contributor |
| **estimator (E)** | −0.02pp | +0.026 | [−0.011, +0.068] / [−0.009, +0.071], P ≈ 0.09 | **does not earn a measurable place** |
| vol target (V) | −0.42pp | +0.108 | [−0.004, +0.226] / [+0.003, +0.223], P ≈ 0.03 | earns its place; without it MDD −49.4% |

Exposure-matched controls: every overlay's Sharpe gain is timing, not
de-levering (rescaling the baseline moves Sharpe ≤ +0.011).
Leave-one-regime-out: F and T positive with every regime dropped and inside
every regime. **E's entire edge is COVID 2020** (+0.471 inside it, +0.013
with it dropped) and it is *negative* inside dot-com and 2022. E also adds
**+13 rebalances/yr** (68 vs 55) — the largest single turnover item — for
zero CAGR.

**Exactly one cell is statistically indistinguishable from LIVE on the full
proxy, both eras and real rows: `F T —`, LIVE with the plain 30-day vol
estimator.** 22.15% / 0.912 / −33.3%, real 31.40% / 1.248 / −25.0%, **19%
fewer rebalances**, *higher* real CAGR. Its expected cost is ~0.02–0.03 Sharpe
concentrated in fast crashes — "signal, but not large enough to measure", not
"no signal".

**Three independent lines now point at the same rule.** The 09-07 block
bootstrap put the max(10,30) estimator at P = 0.097 on its own; the recovery
study found it adds a certain −2.1pp/yr drag in recovery windows; this test
finds it inside noise, COVID-dependent, and the design's biggest churn item.
It was applied on 09-07 for an argument about de-levering *speed* that the
overnight/intraday line is now testing directly. This is the one
simplification candidate with real evidence behind it, for the 2026-12-07
freeze review. Nothing applied.

## Funding policy (owner, 2026-09-07) — reporting duty only

The owner funds the account EPISODICALLY, not monthly: **$5,000 per event**
on exactly two triggers.

  1. **Each newly crossed 5% drawdown tier** (−5 / −10 / −15 / −20 / −25%
     from the rolling 252-day high). ~5.2x/yr; historically 28 / 15 / 8 / 4 /
     1 crossings by tier, worst quarter 5 (2018Q4).
  2. **Each shift of the EFFECTIVE state from D/E/F into A/B/C** — the turn.
     ~4.1x/yr, worst quarter 2.

Together ~9 events/yr, ~$45k/yr, worst historical quarter $30k. Both are now
push events in the triggers, and the single-day "−2% or worse" alert was
REMOVED to make room (it fired ~10x/yr and was explicitly low-conviction).
The triggers only REPORT these; they never move money.

**Why these two and not the alternatives** (all measured 2026-09-07,
`scratchpad dipfund.py` / `statefund.py`, $5k/event, 2015-11 → 2026-08):

| trigger set | /yr | total | final | IRR | per $ |
|---|---|---|---|---|---|
| shift into A/B/C only | 4.1 | $220k | $3.21M | 31.3% | 10.05x |
| drawdown tiers only | 5.2 | $280k | $3.05M | 30.6% | 8.03x |
| **both (adopted)** | **9.0** | **$485k** | **$4.58M** | **31.5%** | 7.84x |
| every strategy day < −3% | 9.3 | $500k | $4.52M | 31.3% | 7.53x |
| annual lump each January | 1.1 | $60k | $2.17M | 30.2% | 13.56x |

REJECTED and not to be reinvented: **entering F** (1.1x/yr) — the deployed
sleeve on that day is **0.0%**, because F is 100% BOXX, so new money lands in
cash; with a $2k/mo budget it left $235k of $260k uninvested and returned
26.1%. **Any state change** (11.5x/yr) — no edge, up to $50k a quarter.
**A −3% day** — most frequent, worst per-dollar efficiency, worst clustering
($35k in a quarter).

**Two honest caveats.** (a) Per-dollar efficiency FALLS as triggers are added
— the annual lump is 13.56x — but that reflects less money working for
longer, not better timing; the adopted pair ends at $4.58M against $2.17M.
(b) Against a monthly schedule with the SAME budget, every trigger tested lost
(deploy-immediately 31.2% vs 31.1% for the shift, 30.4% for tiers), because
cash waiting out of a ~30% strategy is expensive. The owner does not want
monthly contributions, so the schedule is not the live alternative — but if
that ever changes, the schedule wins on the arithmetic.
