# PROPOSED replacement prompt — Weekly Rebalance (Fri 15:55 ET)
# Trigger: trig_01BasZybRAmmumVcNERAnKX7   cron: 55 19 * * 5
# STATUS: APPLIED to the live trigger 2026-09-01; re-applied 2026-09-02 (weights
# reweighted, micro overlay disabled). This file is the
# source of record — edit here, then push via update_trigger, so the repo and
# the live prompt never drift apart. list_triggers does NOT return prompt text,
# so this file is the only readable copy.

Weekly rebalance for the Robinhood Agentic account (576391551) — SPMO core +
TQQQ/QLD satellite + XLU defensive + BOXX cash gate, with volatility targeting
on top. (The micro overlay was DISABLED 2026-09-02 -- see below.) Runs Friday at 15:55 ET, five minutes before the
close. `STRATEGY.md` in the repo is the single source of truth for what the
strategy is and why; this prompt is only the when-and-how. If the two ever
disagree, STRATEGY.md wins — do not re-derive strategy rationale here.

This is the FULL weekly routine: check the drift band, rebalance if it fires,
then report either way. Note the Mon–Thu trigger uses the SAME drift-band gate,
so by Friday the portfolio is often already within band — in that case trade
nothing and still produce the weekly report. The weekly report is unconditional;
the weekly TRADE is not.

## 1. Compute this week's reading

Pull QQQ daily closes via `get_equity_historicals` (adjustment_type='split',
enough history for a 200-day SMA plus the 30-day vol window — 18 months is
ample). Then, using `paper-track/state.py`'s OWN functions — never a
reimplementation:

  - `compute_states(dates, px)` → macro state (A–F)
  - `compute_micro_agreement(dates, px)` → `micro_agrees` bool. INERT since
    2026-09-02 (`MICRO_OVERLAY_ENABLED = False`): still passed through because
    the signature needs it, but it changes no weight and is not a regime change.
  - `realized_vol(dates, px, as_of=<today>)` → annualized 30-trading-day vol
  - `target_weights_with_voltarget(state, micro_agrees, vol)` → the 5 live
    weights (core, tqqq, qld, xlu, cash)

`target_weights_with_voltarget()` is THE live weight function as of
2026-09-01: it applies the (now inert) micro overlay and then scales the four risky legs
by `min(1.0, VOL_TARGET_PA / realized_vol)`, routing the freed weight to cash.
Do not call `target_weights()`, `target_weights_with_micro()`, or
`target_weights_with_gold()` for live weights — they all omit the volatility
overlay. If `realized_vol` returns None, pass it through: the multiplier
degrades to 1.0, the correct fallback. Report the vol reading and the
resulting multiplier every week, even when nothing trades — it is the main new
moving part and should be visible.

## 2. Safety guards — before any order, every run

  - `validate_weights(state, core, tqqq, qld, xlu, cash)` immediately after
    computing weights. `WeightSanityError` → abort, report, DO NOT TRADE.
  - `circuit_breaker_check(actual_total_value, implied_total_value)` before
    placing any order. `implied` = sum of each position's quantity × live
    quote, rebuilt independently from `get_equity_positions` +
    `get_equity_quotes`; `actual` = `get_portfolio`'s own `total_value`. A gap
    beyond 2% means a data error or bad fill, not market volatility.
    `CircuitBreakerTripped` → abort, report, DO NOT TRADE.

Optionally run `python3 paper-track/consistency_check.py` — it asserts every
`TARGET_WEIGHTS` row, the (disabled) micro overlay, the (inert) gold overlay, and the
volatility overlay are internally consistent. Cheap, and it catches a bad edit
to `state.py` before that edit reaches an order.

## 3. Check the drift band, then rebalance if it fires

Build the account's CURRENT held weights: for each of SPMO / TQQQ / QLD / XLU /
BOXX, quantity × live quote, divided by `get_portfolio`'s `total_value`. Idle
uninvested cash counts toward the cash leg. Then call `state.py`'s own gate:

    do_trade, drift, reason = needs_rebalance(target, held, regime_changed)

  - **regime changed → always rebalance**, whatever the drift.
  - **otherwise rebalance only if L1 drift > `REBALANCE_DRIFT_BAND`** (0.03),
    i.e. roughly "1.5 percentage points of the portfolio is in the wrong leg".
  - **within band → trade nothing**, but still do steps 4-7 and publish the
    weekly report. Report the drift figure so a long quiet stretch is visible
    rather than looking like a trigger that failed to run.

When it does fire:

  - Dollar target per leg = weight × `get_portfolio`'s `total_value`.
  - **No per-leg minimum** — every leg goes to target, however small its
    trade. The old "$100 or 0.3%" per-leg skip was REMOVED 2026-09-01: the
    band gates on whether the portfolio as a whole is meaningfully wrong,
    which is the better control, and a per-leg gate on top of it would leave
    small legs permanently adrift. Do not reintroduce one.
  - Sell before buy so proceeds are available.
  - Marketable limit orders: at/through the bid for sells, the ask for buys.
    At 15:55 ET regular-hours rules apply, so fractional/dollar-based orders
    are fine. If anything slips to extended hours it must be a WHOLE-SHARE
    limit order with `market_hours='extended_hours'` — fractional and
    dollar-based orders are rejected outside regular hours.
  - The cash leg is held as **BOXX**, never as idle buying power. If the
    account is holding uninvested cash that the target says should be in BOXX,
    buy BOXX with it.
  - XLU is fractional-tradable in regular hours only.
  - If any residual **IAU** is found, sell it — gold was removed from the
    design 2026-09-01 and any remaining position is dust to be cleared.
  - After filling, re-verify holdings against target and report the resulting
    L1 drift; it should be near zero. Anything above the band after a
    completed rebalance means a fill failed — investigate, do not ignore.

## 4. Drawdown-from-high watch (informational only — never gates a trade)

Same as the daily trigger: compute the strategy's own daily return from
yesterday's confirmed state's weights — from **`target_weights_with_voltarget`**,
i.e. the weights actually held, WITH the volatility overlay (changed
2026-09-01; the un-vol-targeted series would alert on drawdowns the real
account never had) — dotted with today's official-close-to-close leg returns
for SPMO/TQQQ/QLD/XLU/BOXX, append via
`paper-track/drawdown_tracker.py`'s `record_return()`, then
`current_drawdown()` and `newly_crossed()` for the -5/-10/-15/-20% tiers.

## 5. Push notifications — exactly three events, nothing else

`PushNotification` ONLY for: (1) a regime shift — a macro state change (micro
flips no longer count, 2026-09-02); (2) a newly crossed drawdown tier;
(3) any single day at -2% or worse in the strategy's own daily return. Event
(3) is NOT deduplicated and is frequent (~10x/year) — frame as low-conviction
FYI. A routine weekly rebalance with no regime change is NOT a push event.

## 6. Realized P&L and wash sales

Pull the strategy-era trade list (`get_pnl_trade_history`, span 'all',
paginate) and run `paper-track/wash_sale.py`'s `flag_wash_sales()` +
`summarize()` whenever there was a loss-sale. Split realized losses into
usable vs. wash-sale-deferred and NEVER report a deferred loss as reducing
this year's tax liability.

**`get_pnl_trade_history` IS NOT ENOUGH ON ITS OWN.** It returns only CLOSING
trades, so a list built from it alone has no buy records, and `flag_wash_sales`
then reports every loss as usable — a confidently wrong tax figure that looks
like a clean result. Also pull BUYS from `get_equity_orders` (state='filled',
`created_at_gte` at least 30 days before the earliest loss-sale), append them
as `{date, symbol, side:'buy', realized_gain:0}` rows, and call
`flag_wash_sales(trades, require_buys=True)` so the mistake raises
`MissingBuyRecords` instead of returning a silent $0 deferred. This is not
hypothetical: the 2026-09-04 run reported $0 deferred on the first pass and
$1,532.59 deferred of $1,610.66 in losses once the buys were added.

One more caveat to carry when reporting: a buy on the SAME DATE as the
loss-sale is not matched (`SAME_DAY_MATCHES = False`), so a same-day round
trip reads as "usable". Call that out rather than presenting it as settled —
if a week's entire usable total comes from same-day round trips, say so.

TQQQ resizes and BOXX buy/sell cycles make wash sales closer to the norm than
the exception, and volatility targeting adds more BOXX cycling, so expect this
to matter more than it used to.

Any figure combining two or more numbers (a weekly total, a new cumulative)
must be computed in code from the raw records, never hand-added in prose. Use
`paper-track/consistency_check.py`'s `check_pnl_sum(trade_pnls,
expected_total)` to assert the raw sum matches the account's own reported
aggregate BEFORE reporting either figure — a real double-counting incident on
2026-08-31 is why this rule exists.

## 7. Report

Update the weekly report artifact
(https://claude.ai/code/artifact/292cb8f5-b3ad-4a07-a522-91f8d8049c14),
newest week at top: state and label, `micro_agrees`, the realized-vol reading
and resulting multiplier, target vs. actual weights per leg, trades placed and
fills, realized P&L with the wash-sale split, and current drawdown-from-high.

Carry the standing limitations into any commentary, without re-litigating
them: every parameter is fit on the ~11-year SPMO window with one real bear
market in it; the strategy's true max drawdown is about **-32%** on the
2000-2026 stress test (`paper-track/drift_band_test.py`, design of 2026-09-02:
B=75/25, A=70/30, D=85% QLD, micro off; it was -42% before that reweight and
-65 to -70% before vol targeting; QQQ buy-and-hold is -80%), NOT the -19% to
-27% figures the SPMO-era window shows — never quote those as the worst case.
Also carry: the 2026-09-02 reweight is a deliberate step UP the return
frontier, so live-era stress events are larger than before (COVID-shaped
drawdowns about -27% instead of -19%) — that is by design, not a fault.

If Robinhood MCP tools are unavailable, report that and stop — do not guess
prices or place orders on stale data.
