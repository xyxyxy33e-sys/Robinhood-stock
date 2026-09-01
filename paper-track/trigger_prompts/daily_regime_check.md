# PROPOSED replacement prompt — Daily Regime Check (Mon–Thu 15:55 ET)
# Trigger: trig_01GGL83Q7cR8zDB9yPqnKurE   cron: 55 19 * * 1-4
# STATUS: DRAFT FOR REVIEW — not yet applied to the live trigger.

Daily regime check for the Robinhood Agentic account (576391551) — SPMO core +
TQQQ/QLD satellite + XLU defensive + BOXX cash gate, with the micro overlay and
volatility targeting on top. Runs Mon–Thu at 15:55 ET, five minutes before the
close. `STRATEGY.md` in the repo is the single source of truth for what the
strategy is and why; this prompt is only the when-and-how. If the two ever
disagree, STRATEGY.md wins — do not re-derive strategy rationale here.

This is a DRIFT-GATED check, not an unconditional daily rebalance. Most days
the answer is "within band, no action, no report" — expect roughly 33
rebalances/year total across all causes.

## 1. Compute today's reading

Pull QQQ daily closes via `get_equity_historicals` (adjustment_type='split',
enough history for a 200-day SMA plus the 30-day vol window — 18 months is
ample). Then, using `paper-track/state.py`'s OWN functions — never a
reimplementation:

  - `compute_states(dates, px)` → today's macro state (A–F)
  - `compute_micro_agreement(dates, px)` → today's `micro_agrees` bool
  - `realized_vol(dates, px, as_of=<today>)` → annualized 30-trading-day vol
  - `target_weights_with_voltarget(state, micro_agrees, vol)` → the 5 live
    weights (core, tqqq, qld, xlu, cash)

`target_weights_with_voltarget()` is THE live weight function as of
2026-09-01. Do not call `target_weights()`, `target_weights_with_micro()`, or
`target_weights_with_gold()` for live weights — they all omit the volatility
overlay. If `realized_vol` returns None (insufficient history), pass it
through anyway: the multiplier degrades to 1.0, which is the correct fallback.

## 2. Safety guards — before any order, every run

  - `validate_weights(state, core, tqqq, qld, xlu, cash)` immediately after
    computing weights. `WeightSanityError` → abort, report, DO NOT TRADE.
  - `circuit_breaker_check(actual_total_value, implied_total_value)` before
    placing any order. `implied` = sum of each position's quantity × live
    quote, rebuilt independently from `get_equity_positions` +
    `get_equity_quotes`; `actual` = `get_portfolio`'s own `total_value`.
    A gap beyond 2% means a data error or bad fill, not market volatility.
    `CircuitBreakerTripped` → abort, report, DO NOT TRADE.

## 3. Decide whether to trade — the drift band

Build the account's CURRENT held weights: for each of SPMO / TQQQ / QLD / XLU /
BOXX, quantity × live quote, divided by `get_portfolio`'s `total_value`. Idle
uninvested cash counts toward the cash leg. Then call `state.py`'s own gate:

    do_trade, drift, reason = needs_rebalance(target, held, regime_changed)

where `regime_changed` = today's (macro state, micro_agrees) differs from
yesterday's confirmed close. The rule it implements:

  - **regime changed → always rebalance**, no matter how small the drift. A
    state transition is never gated by the band.
  - **otherwise rebalance only if L1 drift > `REBALANCE_DRIFT_BAND`** (0.05),
    where drift = sum over the 5 legs of |target − held|. Since the legs each
    sum to 1.0, a 5% L1 drift is roughly "2.5 percentage points of the
    portfolio is in the wrong leg".
  - **within band → NO TRADE.** Still do steps 4 and 5, then stop. No report,
    no artifact edit.

This replaces the old "state-change only" daily rule AND the old per-leg
"$100 or 0.3%" trade threshold, both removed 2026-09-01. Do not reintroduce a
per-leg minimum: when a rebalance fires, take EVERY leg to target. The band
already gates on whether the portfolio as a whole is meaningfully wrong, which
is the better control; adding a second per-leg gate on top would leave small
legs permanently drifting.

The band is deliberately responsive, not sleepy: traced through the COVID
crash it fired TWELVE rebalances in five weeks, cutting the risky sleeve from
100% to 13% as realised vol went 14% → 79%. Long quiet stretches only happen
where nothing is happening — the median no-trade run is 3 days, and the
longest runs are all calm state-A uptrends.

## 4. Drawdown-from-high watch (informational only — never gates a trade)

Compute the STRATEGY's own daily return: yesterday's confirmed state's
weights (from `target_weights_with_micro` — the tracker's series is
deliberately the un-vol-targeted design return) dotted with today's
official-close-to-close leg returns for SPMO/TQQQ/QLD/XLU/BOXX. Append it via
`paper-track/drawdown_tracker.py`'s `record_return(date, daily_return)` to
`data/live_nav_index.csv`. This is a cash-flow-blind index on purpose, so a
manual deposit never registers as a new high.

Then `current_drawdown()` vs the rolling 252-day high (all-time high until the
log has a year — it started empty 2026-09-01) and `newly_crossed()` for the
-5% / -10% / -15% / -20% tiers. `newly_crossed()` fires only on the FIRST day
a tier is breached, not every day underwater.

## 5. Push notifications — exactly three events, nothing else

Call the `PushNotification` tool (a real interrupt to the user's phone) ONLY
for: (1) a regime shift — macro state change, or a micro-agreement flip within
states A/D; (2) a newly crossed drawdown tier; (3) any single day at -2% or
worse in the strategy's own daily return. Event (3) is NOT deduplicated —
each such day is its own event — and is frequent (~10x/year), so frame it as
low-conviction FYI, not an escalation. Everything else stays in-session.

## 6. Order mechanics, when trading

  - Compute dollar targets = weight × `get_portfolio`'s `total_value`.
  - **No per-leg minimum.** Once the band has fired, every leg goes to target,
    however small its trade. (The old $100/0.3% skip was removed 2026-09-01.)
  - Sell before buy so proceeds are available.
  - Marketable limit orders: at/through the bid for sells, the ask for buys.
    During regular hours (this trigger fires at 15:55 ET, so normally yes)
    fractional/dollar-based orders are fine. If any order must go
    extended-hours, it must be a WHOLE-SHARE limit order with
    `market_hours='extended_hours'` — fractional and dollar-based orders are
    rejected outside regular hours.
  - The cash leg is held as **BOXX**, never as idle buying power.
  - XLU is fractional-tradable in regular hours only.
  - After filling, re-verify holdings against target and report the resulting
    L1 drift; it should be near zero. Anything above the band after a
    completed rebalance means a fill failed — investigate, do not ignore.

## 7. Reporting

On a within-band day: no report, no artifact edit — just end. On a rebalance:
append to the weekly report artifact
(https://claude.ai/code/artifact/292cb8f5-b3ad-4a07-a522-91f8d8049c14),
newest week at top, stating the old state, new state, the vol reading and
multiplier, the drift and which condition fired (regime change vs drift band),
the weights traded to, and the fills.

Any live financial figure that combines two or more numbers (a daily total, a
new cumulative) must be computed in code from raw records
(`get_pnl_trade_history` / `get_realized_pnl`), never hand-added in prose —
`paper-track/consistency_check.py`'s `check_pnl_sum()` exists for this and a
real double-counting incident on 2026-08-31 is why.

If Robinhood MCP tools are unavailable, report that and stop — do not guess
prices or place orders on stale data.
