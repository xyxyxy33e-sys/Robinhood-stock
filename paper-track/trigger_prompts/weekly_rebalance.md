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

## CHANGE FREEZE until 2026-12-07

The live design is FROZEN by owner decision (2026-09-07). Do not change
weights, overlays or parameters, and do not "apply" a research result,
however good the backtest looks. Between 09-05 and 09-07 the design changed
five times in the first three weeks of live trading, and when finally tested
against a persistence-respecting null only ONE of those changes cleared 5%.
Measurement, bug fixes, doc/code consistency fixes and RECORDED-but-unapplied
research are all still fine. The freeze ends on the date, or on a genuine
failure (a guard tripping, a failed fill, a drawdown tier breaching, or live
behaviour diverging from the backtest) -- NOT on a better backtest.
See "Change freeze" in STRATEGY.md.

## 0. Execution convention — what the signal is computed on

This trigger fires at 15:55 ET and trades immediately, using the SAME
session's prices for both the signal and the fills. The backtest convention
is "decide on the close of session d0, hold the d0 -> d1 return", i.e. the
trade happens at d0's close. The 15:55 snapshot is a five-minute-early PROXY
for that close: the last daily bar returned by `get_equity_historicals` is
not final at 15:55, so the SMA, state, gaps and realized-vol readings are all
computed on a nearly-complete bar. That is the intended alignment, and the
approximation is deliberate -- do NOT "fix" it by switching to the prior
completed close, which would add a full session of lag. Added 2026-09-07
after an outside review flagged the ambiguity; measured on real instruments,
one EXTRA session of lag costs about 1.4pp of CAGR (31.9% -> 30.5%) and
0.04 of Sharpe -- and about 2.2pp under the max(10,30) estimator now live,
which reacts faster and is therefore MORE sensitive to execution delay. The
same lag is also the ENTIRE explanation for an outside replay's -39% to -40%
proxy drawdown against our -34.7% (see the limitations note in section 7).
So the five-minute gap is far smaller than that but is not zero, and
execution discipline is worth more than most design changes. Two
consequences to respect:
  - Report readings as "15:55 snapshot", never as "the close".
  - If a run happens outside 15:50-16:00 ET, say so in the report: the
    further from the close, the worse the proxy.

## 0a. Market-holiday guard

Before doing anything else, confirm the US equity market actually traded
today. The cron fires every Friday regardless of the exchange calendar, and
on 2026-09-07 the daily trigger fired on Labor Day and was only caught
because the run checked. Cheapest reliable check: pull the QQQ quote and
compare `previous_close_date` and the last daily bar's date against today.
If today is a market holiday, report "market closed, no action" and STOP —
do not compute a reading, do not trade, do not edit the artifact.

## 1. Compute this week's reading

Pull QQQ daily closes via `get_equity_historicals` (adjustment_type='split',
enough history for a 200-day SMA plus the 30-day vol window — 18 months is
ample). Then, using `paper-track/state.py`'s OWN functions — never a
reimplementation:

  - `compute_states(dates, px)` → macro state (A–F). NOTE this returns a LIST
    aligned to `dates`, not a dict — zip it with `dates` or index by position.
    `compute_fast_states` and `compute_extension_gaps` DO return dicts keyed
    by date.
  - `compute_micro_agreement(dates, px)` → `micro_agrees` bool. INERT since
    2026-09-02 (`MICRO_OVERLAY_ENABLED = False`): still passed through because
    the signature needs it, but it changes no weight and is not a regime change.
  - `realized_vol_live(dates, px, as_of=<today>)` → **the live volatility
    estimate: max(10-day, 30-day) annualized realized vol** (changed
    2026-09-07; was the plain 30-day figure). Taking the max means the fast
    window can only RAISE the estimate, so it can only ever de-lever faster,
    never lever up faster. Returns None on the same insufficient-history
    condition the 30-day estimator did, so the "None → multiplier 1.0"
    fallback is unchanged. Report BOTH legs and which one binds. Do not call
    `realized_vol()` directly for live weights.
  - `compute_fast_states(dates, px)[<today>]` → today's FAST (20/100) reading
    of the same six-state machine. Added 2026-09-06: the fast re-entry
    overlay. It is NOT a state of its own -- it only decides whether a macro
    B/C day holds A weights (fast in A/B) or a macro F day holds C weights
    (fast in A/B/C). See `effective_state()`.
  - `live_target_weights(state, micro_agrees, vol, fast_state, gaps)`
    -> the 5 live weights (core, tqqq, qld, xlu, cash). **Call THIS, not
    `target_weights_with_voltarget`.** Added 2026-09-07: `fast_state` and
    `gaps` are REQUIRED positional arguments and are validated, raising
    `MissingOverlayInputs`. The older function accepts them as None so
    pre-overlay backtests still run, which meant a live call that forgot one
    silently traded the PRE-OVERLAY design and looked fine doing it. `vol=None`
    is still accepted and still degrades the multiplier to 1.0.
  - `effective_state(state, fast_state)` → the state whose weight row is
    actually held. Report BOTH the macro state and the effective state
    whenever they differ.
  - `compute_extension_gaps(dates, px)[<today>]` → today's {100: gap, 150:
    gap, 200: gap} (close / SMA − 1). Added 2026-09-06: the GRADED EXTENSION
    TRIM. Votes = how many of {100d > 10%, 150d > 12%, 200d > 15%} are true;
    when the effective state is A the four risky legs are scaled by
    1 − ⅓ × votes (×⅔ / ×⅓ / ×0 — three votes puts the A row 100%
    in BOXX) before vol targeting. Step 0.25 → ⅓ on 2026-09-06 (later).
    `extension_votes(effective_state, gaps)` gives the count. Pass the dict
    as `gaps=<gaps>` to the live weight function (do NOT use the legacy
    `gap200=` argument). Report the three gaps and the vote count every run.
    NOTE the three windows are ~0.9 correlated — they are ONE signal read
    three ways, not three independent confirmations.

`live_target_weights()` is THE live weight function as of 2026-09-07
(it wraps `target_weights_with_voltarget()`, live since 2026-09-01): it applies the (now inert) micro overlay and then scales the four risky legs
by `min(1.0, VOL_TARGET_PA / realized_vol)`, routing the freed weight to cash.
Do not call `target_weights()`, `target_weights_with_micro()`, or
`target_weights_with_gold()` for live weights — they all omit the volatility
overlay. If `realized_vol_live` returns None, pass it through: the multiplier
degrades to 1.0, the correct fallback. Report both vol legs, which binds, and the
resulting multiplier every week, even when nothing trades — it is the main new
moving part and should be visible.

**Trade what the code returns, never a number written in prose** — here, in
STRATEGY.md, or in any past report. `state.py`'s `TARGET_WEIGHTS` is
authoritative.

## 2. Safety guards — before any order, every run

  - `validate_weights(state, core, tqqq, qld, xlu, cash)` immediately after
    computing weights. `WeightSanityError` → abort, report, DO NOT TRADE.
  - `circuit_breaker_check(actual_total_value, implied_total_value)` before
    placing any order. `implied` = sum of each position's quantity × live
    quote, rebuilt independently from `get_equity_positions` +
    `get_equity_quotes`, PLUS the account's cash; `actual` =
    `get_portfolio`'s own `total_value`. A gap beyond 2% means a data error
    or bad fill, not market volatility. `CircuitBreakerTripped` → abort,
    report, DO NOT TRADE. Note this guard reconciles two views of the SAME
    balance — it does NOT detect a deposit, and a deposit is not a failure.
  - `MissingOverlayInputs` from `live_target_weights` → abort, report, DO NOT
    TRADE. It means an overlay input was not computed; never fall back to
    `target_weights_with_voltarget` to get past it.

Optionally run `python3 paper-track/consistency_check.py` — it asserts every
`TARGET_WEIGHTS` row, the (disabled) micro overlay, the (inert) gold overlay, and the
volatility overlay are internally consistent. Cheap, and it catches a bad edit
to `state.py` before that edit reaches an order.

## 2a. Unexpected cash — deposits and withdrawals

If the account's cash differs materially from what the last run left behind
(a deposit or withdrawal you did not place), the target weights still apply
to the FULL `total_value` — new money is deployed to target, not held aside.
But a large unannounced balance change is worth one question before acting:
if the change exceeds 20% of the prior account value, report the reading and
the trades it implies and ASK the owner before placing them, rather than
deploying silently. Below that threshold, deploy to target and note the
change in the report. A deposit is not a circuit-breaker event.

## 3. Check the drift band, then rebalance if it fires

Build the account's CURRENT held weights: for each of SPMO / TQQQ / QLD / XLU /
BOXX, quantity × live quote, divided by `get_portfolio`'s `total_value`. Idle
uninvested cash counts toward the cash leg. Then call `state.py`'s own gate:

    do_trade, drift, reason = needs_rebalance(target, held, regime_changed)

  - **regime changed → always rebalance**, whatever the drift. Regime =
    the EFFECTIVE state (`effective_state(macro, fast)`) plus the extension
    trim vote count (`extension_votes(...)`), so the fast re-entry overlay
    switching or the trim changing by a step counts (2026-09-06).
  - **otherwise rebalance only if L1 drift > `REBALANCE_DRIFT_BAND`** (0.03),
    i.e. roughly "1.5 percentage points of the portfolio is in the wrong leg".
  - **a leg whose target is EXACTLY 0% but is still held above 0.10%
    (`ZERO_LEG_EPS`) → rebalance**, whatever the total drift. Added
    2026-09-04 — when vol drops below target the cash target becomes exactly
    zero, and a leftover BOXX stub would otherwise sit inside the band
    indefinitely. `needs_rebalance()` applies this itself.
  - **within band → trade nothing**, but still do steps 4-7 and publish the
    weekly report. Report the drift figure so a long quiet stretch is visible
    rather than looking like a trigger that failed to run.

Known behaviour, not a bug: the extension vote count changes about 18x/year
and roughly 44% of those changes reverse within three sessions, so some
rebalances are round trips. A hysteresis band was tested 2026-09-07 and
REJECTED (it helps the SPMO era and costs holdout Sharpe). Do not add one.
Likewise the max(10,30) estimator trades more often than the 30-day one did
(~69 vs ~55 rebalances/yr, turnover essentially unchanged); that is the
applied design, not drift to be damped.

When it does fire:

  - Dollar target per leg = weight × `get_portfolio`'s `total_value`.
  - **No per-leg minimum** — every leg goes to target, however small its
    trade. The old "$100 or 0.3%" per-leg skip was REMOVED 2026-09-01: the
    band gates on whether the portfolio as a whole is meaningfully wrong,
    which is the better control, and a per-leg gate on top of it would leave
    small legs permanently adrift. Do not reintroduce one.
  - Sell before buy so proceeds are available. Check this explicitly when the
    buy side exceeds available buying power — a leg being liquidated to zero
    is what funds the buys.
  - Marketable limit orders: at/through the bid for sells, the ask for buys.
    Do not chase more than 0.3% through the touch. At 15:55 ET regular-hours
    rules apply, so fractional/dollar-based orders are fine. If anything slips
    to extended hours it must be a WHOLE-SHARE limit order with
    `market_hours='extended_hours'` — fractional and dollar-based orders are
    rejected outside regular hours. Note a LIMIT order cannot be fractional in
    any session; to liquidate a fractional stub completely, use a market order
    in regular hours.
  - The cash leg is held as **BOXX**, never as idle buying power. If the
    account is holding uninvested cash that the target says should be in BOXX,
    buy BOXX with it.
  - XLU is fractional-tradable in regular hours only.
  - If any residual **IAU** is found, sell it — gold was removed from the
    design 2026-09-01 and any remaining position is dust to be cleared.
  - After filling, re-verify holdings against target and report the resulting
    L1 drift; it should be near zero. Anything above the band after a
    completed rebalance means a fill failed — investigate, do not ignore.
  - **Record execution quality for EVERY filled leg** (added 2026-09-07).
    After fills, call `paper-track/fill_quality.py`'s
    `record_fill(date, symbol, side, quantity, fill_price, ref_price)` once
    per leg, where `ref_price` is the OFFICIAL CLOSE of the signal session
    (pass `ref_kind` if you had to use anything else). Then report
    `summarize()`'s notional-weighted slippage in bps against the **4bp
    one-way cost model the backtests assume**. This gates nothing and must
    never block or delay a trade -- it is measurement only. It exists because
    one session of execution lag costs 3.1pp of CAGR and 4.8pp of drawdown,
    larger than any design change made this week, and until now nothing
    checked it. Flag any single leg worse than 25bp; persistent
    notional-weighted slippage worse than 4bp means the live design is not
    the backtested one and is worth more attention than any parameter.
    IMPORTANT when interpreting a flag: on a same-session 15:55 run the
    reference IS effectively the fill session, so a large number is genuine
    execution slippage. On any run where the signal session and the fill
    session differ, most of the number is the overnight GAP, not broker
    execution — say which it is rather than reporting a gap as bad execution.

## 4. Drawdown-from-high watch (informational only — never gates a trade)

Same as the daily trigger: compute the strategy's own daily return from
yesterday's confirmed state's weights — from **`target_weights_with_voltarget`**,
i.e. the weights actually held, WITH the volatility overlay (changed
2026-09-01; the un-vol-targeted series would alert on drawdowns the real
account never had) — dotted with today's official-close-to-close leg returns
for SPMO/TQQQ/QLD/XLU/BOXX, append via
`paper-track/drawdown_tracker.py`'s `record_return()`, then
`current_drawdown()` and `newly_crossed()` for the -5/-10/-15/-20% tiers.
`current_drawdown()` returns a TUPLE (drawdown, peak_date, peak_value,
current_date, current_value) — take element 0 for the drawdown itself.

Record the return only ONCE per session, and only for a completed session.
If the daily trigger already recorded today's row, do not append a second.

## 5. Push notifications — exactly three events, nothing else

Call the `PushNotification` tool (a real interrupt to the user's phone) ONLY
for these three, and nothing else:

  1. **A regime shift** — a MACRO state change. (Micro flips have not counted
     since 2026-09-02.)
  2. **A newly crossed drawdown tier** (-5 / -10 / -15 / -20% from the
     rolling 252-day high, via `newly_crossed()`). **This is also a FUNDING
     TRIGGER** — see below.
  3. **The EFFECTIVE state shifting from D/E/F into A/B/C** — the turn.
     **This is a FUNDING TRIGGER.** Added 2026-09-07. Note this one DOES fire
     when the shift is driven by the fast re-entry overlay alone, which is a
     deliberate exception to the rule that overlay switches are not push
     events: the owner funds on this signal, so they need to see it.

REMOVED 2026-09-07: the old event (3), "any single day at -2% or worse in the
strategy's own daily return". It fired ~10x/year as an explicit low-conviction
FYI and was never actionable. The owner's funding policy uses drawdown TIERS
and the turn instead, both of which are above. Do not reinstate a single-day
return alert.

If a macro shift into A/B/C happens, events 1 and 3 are the same event — send
ONE notification, and say it is a funding trigger.

## 5a. Funding triggers — what to tell the owner

The owner funds the account episodically, not monthly, on **$5,000 per event**
at exactly two signals (2026-09-07):

  - **each newly crossed 5% drawdown tier** (~5.2x/yr historically), and
  - **each shift of the effective state from D/E/F into A/B/C** (~4.1x/yr).

Together about 9 events/year, roughly $45k/year, worst historical quarter
$30k. When either fires, say so explicitly and name which one, the tier or
the prior/new state, and the account value. Do NOT compute or suggest a
different amount, do not net the two against each other, and do not invent
additional funding signals — funding on a -3% day, on any state change, or on
entry into F were all tested 2026-09-07 and rejected (entering F is the worst
of them: the strategy is 100% BOXX there, so new money would land in cash).
This is a REPORTING duty only. Never move money, and never treat a funding
trigger as a reason to deviate from the computed target weights.

The $5,000 figure is the standing policy, not a cap on what the owner may
choose to send. If a deposit larger than the policy amount arrives, deploy it
to target under section 2a — do not hold the excess back to match the policy.

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

Never reproduce a standing performance figure by reimplementing the backtest
loop — call `improvement_search.run()` (or the harness that owns the figure).
A hand-rolled loop silently rebalances costlessly every day and produces
numbers that look right and are not.

## 7. Report

To edit the artifact you must FIRST call the Artifact tool with
`action: "read"` and its URL, then build your edit on the version that comes
back and diff local against live before republishing — a publish to an
artifact this session has not read is refused.

Update the weekly report artifact
(https://claude.ai/code/artifact/292cb8f5-b3ad-4a07-a522-91f8d8049c14),
newest week at top: macro state and label, fast (20/100) reading and the
effective state if it differs, the three extension gaps and the vote count,
`micro_agrees`, both realized-vol legs with the binding one
and resulting multiplier, target vs. actual weights per leg, trades placed and
fills, realized P&L with the wash-sale split, current drawdown-from-high, and
the notional-weighted slippage from the fill-quality tracker.

If a FUNDING TRIGGER fired this week — a newly crossed 5% drawdown tier, or
the effective state shifting from D/E/F into A/B/C — put it at the TOP of the
entry: which trigger, the tier or the prior/new state, the account value, and
the standing $5,000-per-event policy. Also list any funding triggers that fired
earlier in the week on a Mon-Thu run, so the weekly entry is a complete record
of the week's funding events even when the Friday run itself trades nothing.

Carry the standing limitations into any commentary, without re-litigating
them: every parameter is fit on the ~11-year SPMO window with one real bear
market in it; the strategy's true max drawdown is about **-33%** on the
2000-2026 stress test (design of 2026-09-07 final: A=50/50 core/TQQQ, B=75/25,
D=100% QLD, F=cash, 20/100 fast re-entry overlay on B/C/F, graded extension
trim (A scaled x2/3 / x1/3 / x0 as QQQ clears 10%/12%/15% above its
100/150/200-day SMAs), micro off, vol target 20% on max(10d,30d) realized vol;
it was -34.7% during the one day the A row sat at 40/60 on 09-06, -32% under the
2026-09-02 design, -42% before that reweight and -65 to -70% before vol
targeting; QQQ buy-and-hold is -80%), NOT the -25% to -31% figures the
SPMO-era window shows -- never quote those as the worst case. An outside
replay reaching -39% to -40% was RECONCILED 2026-09-07: it is not a data,
fee or proxy difference (core proxy, financing spread and expense ratios move
it by <=0.5pp), it is EXECUTION LAG. One extra session between signal and fill
took the A=40/60 design from -34.7% to -39.5%, two sessions to -40.3%, and one
session also costs 3.1pp of CAGR. So -33% is the figure for trading AT the
signal close, which is what this trigger does; -40% is the figure if execution
routinely slips a day (measured at A=40/60; A=50/50 is ~2pp better throughout). Neither is a loss ceiling. This is why the 15:55
convention in section 0 matters operationally, not just pedantically.
Also carry:
the 2026-09-06 reweight is the SECOND deliberate step up the return frontier,
so live-era stress events are larger than before (COVID-shaped drawdowns about
-25% to -33%, a 2022-type year about -19% real / -27% proxy) -- that is by design, not a fault.

Evidence discipline when commenting on the overlays: a circular BLOCK
bootstrap (2026-09-07) downgraded two claims that earlier day-shuffled tests
overstated. The graded extension trim survives (Sharpe 95% CI [+0.025,
+0.266], P(<=0) = 0.007); the fast re-entry overlay (P = 0.080) and the
max(10,30) volatility estimator (P = 0.097) do NOT clear 5% on their own.
Do not quote "p = 0.00" for any of them. Leave-one-major-regime-out keeps
every sign in every drop, including dropping the whole SPMO fitting window.

If Robinhood MCP tools are unavailable, report that and stop — do not guess
prices or place orders on stale data.
