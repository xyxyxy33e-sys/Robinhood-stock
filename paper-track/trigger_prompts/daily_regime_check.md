# PROPOSED replacement prompt — Daily Regime Check (Mon–Thu 15:55 ET)
# Trigger: trig_01GGL83Q7cR8zDB9yPqnKurE   cron: 55 19 * * 1-4
# STATUS: APPLIED to the live trigger 2026-09-01; re-applied 2026-09-02 (weights
# reweighted, micro overlay disabled). This file is the
# source of record — edit here, then push via update_trigger, so the repo and
# the live prompt never drift apart. list_triggers does NOT return prompt text,
# so this file is the only readable copy.

Daily regime check for the Robinhood Agentic account (576391551) — SPMO core +
TQQQ/QLD satellite + XLU defensive + BOXX cash gate, with volatility targeting
on top. (The micro overlay was DISABLED 2026-09-02 -- see below.) Runs Mon–Thu at 15:55 ET, five minutes before the
close. `STRATEGY.md` in the repo is the single source of truth for what the
strategy is and why; this prompt is only the when-and-how. If the two ever
disagree, STRATEGY.md wins — do not re-derive strategy rationale here.

This is a DRIFT-GATED check, not an unconditional daily rebalance. Most days
the answer is "within band, no action, no report" — expect roughly 69
rebalances/year total across all causes (up from ~55 since the volatility
estimator changed 2026-09-07: more frequent, smaller trims; turnover is
essentially unchanged).

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
proxy drawdown against our -34.7% (reconciled 2026-09-07: core proxy,
financing and fees move it by <=0.5pp; one extra session takes it to -39.5%,
two to -40.3%). So the five-minute gap is far smaller than that but is not
zero, and execution discipline is worth more than most design changes. Two
consequences to respect:
  - Report readings as "15:55 snapshot", never as "the close".
  - If a run happens outside 15:50-16:00 ET, say so in the report: the
    further from the close, the worse the proxy.

## 1. Compute today's reading

Pull QQQ daily closes via `get_equity_historicals` (adjustment_type='split',
enough history for a 200-day SMA plus the 30-day vol window — 18 months is
ample). Then, using `paper-track/state.py`'s OWN functions — never a
reimplementation:

  - `compute_states(dates, px)` → today's macro state (A–F)
  - `compute_micro_agreement(dates, px)` → today's `micro_agrees` bool. INERT
    since 2026-09-02 (`MICRO_OVERLAY_ENABLED = False`): still computed and
    passed through because the function signature needs it, but it changes
    no weight and is NOT a regime change.
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
(it wraps `target_weights_with_voltarget()`, live since 2026-09-01). Do not call `target_weights()`, `target_weights_with_micro()`, or
`target_weights_with_gold()` for live weights — they all omit the volatility
overlay. If `realized_vol_live` returns None (insufficient history), pass it
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
  - `MissingOverlayInputs` from `live_target_weights` → abort, report, DO NOT
    TRADE. It means an overlay input was not computed; never fall back to
    `target_weights_with_voltarget` to get past it.

Running `python3 paper-track/consistency_check.py` is cheap and now also
asserts that STRATEGY.md's weight tables match `state.py`, that the live
weight function rejects missing overlay inputs, and that the max(10,30)
estimator can only raise the vol reading, never lower it.

## 3. Decide whether to trade — the drift band

Build the account's CURRENT held weights: for each of SPMO / TQQQ / QLD / XLU /
BOXX, quantity × live quote, divided by `get_portfolio`'s `total_value`. Idle
uninvested cash counts toward the cash leg. Then call `state.py`'s own gate:

    do_trade, drift, reason = needs_rebalance(target, held, regime_changed)

where `regime_changed` = today's EFFECTIVE state (`effective_state(macro,
fast)`, A–F) differs from yesterday's confirmed close, OR the extension
trim vote count (`extension_votes(effective_state, gaps)`) differs from
yesterday's.
That covers a macro transition, the fast re-entry overlay switching on or
off, and the extension trim switching on or off (both added 2026-09-06) —
each one moves the weight row, so each one fires. A
`micro_agrees` flip alone is NOT a regime change as of 2026-09-02 — that
overlay is disabled, so a flip moves no weight. The rule it implements:

  - **regime changed → always rebalance**, no matter how small the drift. A
    state transition is never gated by the band.
  - **otherwise rebalance only if L1 drift > `REBALANCE_DRIFT_BAND`** (0.03),
    where drift = sum over the 5 legs of |target − held|. Since the legs each
    sum to 1.0, a 3% L1 drift is roughly "1.5 percentage points of the
    portfolio is in the wrong leg".
  - **a leg whose target is EXACTLY 0% but is still held above 0.10%
    (`ZERO_LEG_EPS`) → rebalance**, whatever the total drift. Added
    2026-09-04. When realised vol drops below the 20% target the multiplier
    hits 1.0 and the cash target becomes exactly zero; a leftover BOXX stub
    would otherwise sit inside the band indefinitely, permanently consuming
    part of the band's budget for real drift. `needs_rebalance()` handles
    this itself — you do not need to check it separately. This is NOT the
    per-leg trade threshold removed 2026-09-01: it only ever ADDS a reason to
    fire, and when it fires every leg still goes to target.
  - **within band → NO TRADE.** Still do steps 4 and 5, then stop. No report,
    no artifact edit.

Known behaviour, not a bug: the extension vote count changes about 18x/year
and roughly 44% of those changes reverse within three sessions, so some
rebalances are round trips. A hysteresis band was tested 2026-09-07 and
REJECTED (it helps the SPMO era and costs holdout Sharpe). Do not add one.
Likewise the max(10,30) estimator trades more often than the 30-day one did
(~69 vs ~55 rebalances/yr, turnover essentially unchanged); that is the
applied design, not drift to be damped.

This replaces the old "state-change only" daily rule AND the old per-leg
"$100 or 0.3%" trade threshold, both removed 2026-09-01. Do not reintroduce a
per-leg minimum: when a rebalance fires, take EVERY leg to target. The band
already gates on whether the portfolio as a whole is meaningfully wrong, which
is the better control; adding a second per-leg gate on top would leave small
legs permanently drifting.

The band is deliberately responsive, not sleepy: traced through the COVID
crash it rebalances repeatedly, walking the risky sleeve from 100% down to
~13% as realised vol goes 14% → 79%. Long quiet stretches only happen where
nothing is happening — the median no-trade run is 2 days, and the longest
runs are all calm state-A uptrends.

## 4. Drawdown-from-high watch (informational only — never gates a trade)

Compute the STRATEGY's own daily return: yesterday's confirmed state's
weights — from the live weight function, i.e. the weights actually
held, WITH the volatility overlay — dotted with today's
official-close-to-close leg returns for SPMO/TQQQ/QLD/XLU/BOXX. Append it via
`paper-track/drawdown_tracker.py`'s `record_return(date, daily_return)` to
`data/live_nav_index.csv`. This is a cash-flow-blind index on purpose, so a
manual deposit never registers as a new high. It must track the VOL-TARGETED
portfolio (changed 2026-09-01): the un-vol-targeted series would fire the
-5%/-10% tiers earlier and more often than the real account experiences,
alerting on a drawdown that isn't happening.

Then `current_drawdown()` vs the rolling 252-day high (all-time high until the
log has a year — it started empty 2026-09-01) and `newly_crossed()` for the
-5% / -10% / -15% / -20% tiers. `newly_crossed()` fires only on the FIRST day
a tier is breached, not every day underwater.

## 5. Push notifications — exactly three events, nothing else

Call the `PushNotification` tool (a real interrupt to the user's phone) ONLY
for: (1) a regime shift — a MACRO state change (micro flips no longer count,
2026-09-02; the fast re-entry overlay switching on/off is reported in-session
but is NOT a push event); (2) a newly crossed drawdown tier; (3) any single day at -2% or
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

## 7. Reporting

On a within-band day: no report, no artifact edit — just end. On a rebalance:
append to the weekly report artifact
(https://claude.ai/code/artifact/292cb8f5-b3ad-4a07-a522-91f8d8049c14),
newest week at top, stating the old state, new state (macro AND effective,
if the fast overlay is active), the extension-trim vote count, both vol legs
with the binding one and the resulting multiplier, the drift and which condition fired (regime change vs drift band),
the weights traded to, and the fills.

Any live financial figure that combines two or more numbers (a daily total, a
new cumulative) must be computed in code from raw records
(`get_pnl_trade_history` / `get_realized_pnl`), never hand-added in prose —
`paper-track/consistency_check.py`'s `check_pnl_sum()` exists for this and a
real double-counting incident on 2026-08-31 is why.

Evidence discipline when commenting on the overlays: a circular BLOCK
bootstrap (2026-09-07) downgraded two claims that earlier day-shuffled tests
overstated. The graded extension trim survives (Sharpe 95% CI [+0.025,
+0.266], P(<=0) = 0.007); the fast re-entry overlay (P = 0.080) and the
max(10,30) volatility estimator (P = 0.097) do NOT clear 5% on their own.
Do not quote "p = 0.00" for any of them. Leave-one-major-regime-out keeps
every sign in every drop, including dropping the whole SPMO fitting window.

If Robinhood MCP tools are unavailable, report that and stop — do not guess
prices or place orders on stale data.
