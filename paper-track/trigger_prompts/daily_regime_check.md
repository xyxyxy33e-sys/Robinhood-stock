# PROPOSED replacement prompt — Daily Regime Check (Mon–Thu 15:55 ET)
# Trigger: trig_01GGL83Q7cR8zDB9yPqnKurE   cron: 55 19 * * 1-4
# STATUS: DRAFT FOR REVIEW — not yet applied to the live trigger.

Daily regime check for the Robinhood Agentic account (576391551) — SPMO core +
TQQQ/QLD satellite + XLU defensive + BOXX cash gate, with the micro overlay and
volatility targeting on top. Runs Mon–Thu at 15:55 ET, five minutes before the
close. `STRATEGY.md` in the repo is the single source of truth for what the
strategy is and why; this prompt is only the when-and-how. If the two ever
disagree, STRATEGY.md wins — do not re-derive strategy rationale here.

This is a STATE-CHANGE check, not a daily rebalance. Expected outcome on most
days is "nothing changed, no action, no report" (~8 regime transitions/year).

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

## 3. Decide whether to trade

Compare today's macro state and `micro_agrees` to yesterday's confirmed close.

  - **No regime change** (same macro state AND same micro_agrees): NO TRADE.
    Do not rebalance on volatility drift alone — the vol multiplier moves a
    little every day, and acting on it daily would multiply turnover well past
    what the backtest models. Volatility-driven adjustment is the FRIDAY
    trigger's job, which is what the weekly-rebalance backtest actually
    measures. Still do steps 4 and 5, then stop. No report, no artifact edit.
  - **Regime changed**: rebalance to the new vol-targeted weights now, using
    the order mechanics in step 6.

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
  - Skip any leg whose trade is under **$100 or 0.3%** of account value —
    below that, spread and wash-sale churn cost more than the tracking error.
  - Sell before buy so proceeds are available.
  - Marketable limit orders: at/through the bid for sells, the ask for buys.
    During regular hours (this trigger fires at 15:55 ET, so normally yes)
    fractional/dollar-based orders are fine. If any order must go
    extended-hours, it must be a WHOLE-SHARE limit order with
    `market_hours='extended_hours'` — fractional and dollar-based orders are
    rejected outside regular hours.
  - The cash leg is held as **BOXX**, never as idle buying power.
  - XLU is fractional-tradable in regular hours only.
  - After filling, re-verify holdings against target and report any leg still
    off by more than the threshold.

## 7. Reporting

On a no-change day: no report, no artifact edit — just end. On a rebalance:
append to the weekly report artifact
(https://claude.ai/code/artifact/292cb8f5-b3ad-4a07-a522-91f8d8049c14),
newest week at top, stating the old state, new state, the vol reading and
multiplier, the weights traded to, and the fills.

Any live financial figure that combines two or more numbers (a daily total, a
new cumulative) must be computed in code from raw records
(`get_pnl_trade_history` / `get_realized_pnl`), never hand-added in prose —
`paper-track/consistency_check.py`'s `check_pnl_sum()` exists for this and a
real double-counting incident on 2026-08-31 is why.

If Robinhood MCP tools are unavailable, report that and stop — do not guess
prices or place orders on stale data.
