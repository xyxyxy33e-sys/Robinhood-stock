# PROPOSED replacement prompt — Daily Regime Check (Mon–Thu 15:50 ET)
# Trigger: trig_01GGL83Q7cR8zDB9yPqnKurE   cron: 50 19 * * 1-4  (15:50 ET since 2026-09-09)
# STATUS: APPLIED to the live trigger 2026-09-01; re-applied 2026-09-02 (weights
# reweighted, micro overlay disabled). This file is the
# source of record — edit here, then push via update_trigger, so the repo and
# the live prompt never drift apart. list_triggers does NOT return prompt text,
# so this file is the only readable copy.

Daily regime check for the Robinhood Agentic account (576391551) — SPMO core +
TQQQ/QLD satellite + XLU defensive + BOXX cash gate, with volatility targeting
on top. (The micro overlay was DISABLED 2026-09-02 -- see below.) Runs Mon–Thu at 15:50 ET, ten minutes before the
close (moved from 15:55 on 2026-09-09 -- see section 0b). `STRATEGY.md` in the repo is the single source of truth for what the
strategy is and why; this prompt is only the when-and-how. If the two ever
disagree, STRATEGY.md wins — do not re-derive strategy rationale here.

This is a DRIFT-GATED check, not an unconditional daily rebalance. Most days
the answer is "within band, no action, no report" — expect roughly 47
rebalances/year total across all causes at the 5% band (~55 at the old 3%
band; the max(10,30) estimator briefly raised this to ~69 between 09-07 and
09-09 and was reverted).

## CHANGE DISCIPLINE (freeze of 2026-09-07 LIFTED 2026-09-09 by owner decision)

The 09-07 freeze was lifted by the owner on 2026-09-09 for ONE change, after
nine independent research lines on 09-08/09: the max(10,30) vol estimator was
REVERTED to the plain 30-day reading (see "Volatility estimator reverted" in
STRATEGY.md). Nothing else changed. The discipline the freeze encoded still
binds: do not change weights, overlays or parameters on the strength of a
better backtest. A change needs both-era improvement, exposure/beta-matched
controls, a block bootstrap, and an owner decision -- the nine studies of
09-08/09 are the standard. Measurement, bug fixes, doc/code consistency
fixes and RECORDED-but-unapplied research are always fine.

## 0. Execution convention — what the signal is computed on

This trigger fires at 15:50 ET (15:55 until 2026-09-09) and trades immediately, using the SAME
session's prices for both the signal and the fills. The backtest convention
is "decide on the close of session d0, hold the d0 -> d1 return", i.e. the
trade happens at d0's close. The 15:5x snapshot is a few-minutes-early PROXY
for that close: the last daily bar returned by `get_equity_historicals` is
not final at 15:5x, so the SMA, state, gaps and realized-vol readings are all
computed on a nearly-complete bar. That is the intended alignment, and the
approximation is deliberate -- do NOT "fix" it by switching to the prior
completed close, which would add a full session of lag. Added 2026-09-07
after an outside review flagged the ambiguity; measured on real instruments,
one EXTRA session of lag costs about 1.4pp of CAGR (31.9% -> 30.5%) and
0.04 of Sharpe (about 2.2pp under the max(10,30) estimator that was live
09-07..09-09, which reacted faster and was more lag-sensitive). The
same lag is also the ENTIRE explanation for an outside replay's -39% to -40%
proxy drawdown against our -34.7% (reconciled 2026-09-07: core proxy,
financing and fees move it by <=0.5pp; one extra session takes it to -39.5%,
two to -40.3%). So the five-minute gap is far smaller than that but is not
zero, and execution discipline is worth more than most design changes. Two
consequences to respect:
  - Report readings as "15:5x snapshot", never as "the close".
  - If a run happens outside 15:45-16:00 ET, say so in the report: the
    further from the close, the worse the proxy.

## 0a. Market-holiday guard

Before doing anything else, confirm the US equity market actually traded
today. The cron fires Mon–Thu regardless of the exchange calendar, and on
2026-09-07 (Labor Day) it fired on a closed market and was only caught
because the run checked. Cheapest reliable check: pull the QQQ quote and
compare `previous_close_date` and the last daily bar's date against today.
If today is a holiday or an early close that has already passed, report
"market closed, no action" and STOP — do not compute a reading, do not
trade, do not append to the artifact.

## 0b. Timing, pre-staging and the missed-run fallback (2026-09-09)

**Fire time is now 15:50 ET (was 15:55).** The extra five minutes are for
computing, not waiting: the style-attribution study measured the design's
timing value at 10.6 / 8.0 / 6.6 pp/yr for 0 / 1 / 2 sessions of execution
delay, so the single most valuable thing this run can do is FINISH before the
close. Sequence, and do not reorder it:
  1. 15:50-15:54: holiday guard, pull data, compute the reading, run BOTH
     guards, build the held weights, call `needs_rebalance`. Nothing else.
  2. If it fires: place the orders IMMEDIATELY -- target 15:54-15:57, never
     after 15:59. Report readings as the "15:5x snapshot"; the bar is not
     final and that is the intended proxy (section 0).
  3. Only after fills are confirmed (or no trade): fill-quality recording,
     NAV row, drawdown watch, notifications, artifact, commit. All of that
     can run after 16:00 without cost; an order cannot.
Do not spend the window on commentary, research, or reading STRATEGY.md.

**Fill-quality recording now takes `session_lag`.** A same-session fill is
`session_lag=0` (the normal case). If the fill happened the session AFTER the
signal (the fallback below, or any delayed run), pass `session_lag=1`.
`summarize()` counts only lag-0 fills toward the 25bp alarm and the 4bp cost
comparison -- on a lagged fill the number is mostly the overnight gap, not
execution (overnight_intraday.md) -- and reports lagged fills separately.

**If THIS run cannot complete by 16:00** (tools down, data missing, guard
tripped for a data reason, anything): do NOT wait for the next scheduled run.
Say so plainly and stop; the 16:10 ET watchdog Routine will pick it up. The
fallback it applies, measured in overnight_intraday.md: execute the CLOSE's
signal at the next opportunity -- extended-hours whole-share limit orders if
the reading is available by 16:10, otherwise the next open. That costs about
-0.8 pp/yr and is not statistically distinguishable from zero; letting the
SIGNAL slip a whole session instead costs -2.6 pp/yr proxy / -1.8 real at
every cost level. Lose the overnight, never the signal.

## 1. Compute today's reading

Pull QQQ daily closes via `get_equity_historicals` (adjustment_type='split',
enough history for a 200-day SMA plus the 30-day vol window — 18 months is
ample). Then, using `paper-track/state.py`'s OWN functions — never a
reimplementation:

  - `compute_states(dates, px)` → today's macro state (A–F). NOTE this returns
    a LIST aligned to `dates`, not a dict — zip it with `dates` or index by
    position. `compute_fast_states` and `compute_extension_gaps` DO return
    dicts keyed by date.
  - `compute_micro_agreement(dates, px)` → today's `micro_agrees` bool. INERT
    since 2026-09-02 (`MICRO_OVERLAY_ENABLED = False`): still computed and
    passed through because the function signature needs it, but it changes
    no weight and is NOT a regime change.
  - `realized_vol_live(dates, px, as_of=<today>)` → **the live volatility
    estimate: the plain 30-day annualized realized vol** (REVERTED to this
    2026-09-09 by owner decision; between 09-07 and 09-09 it was
    max(10-day, 30-day), which three studies then found inside noise,
    COVID-dependent and +13 rebalances/yr -- `VOL_ESTIMATOR_MAX_ENABLED` is
    now False and the function returns the 30-day figure). Still call THIS
    function, never `realized_vol()` directly, so a future flag change flows
    through. Returns None on insufficient history → multiplier 1.0. Report
    the 30-day reading; you may also report the 10-day for information, but
    it moves no weight.
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

**Trade what the code returns, never a number written in prose** — here,
in STRATEGY.md, or in any past report. `state.py`'s `TARGET_WEIGHTS` is
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

Running `python3 paper-track/consistency_check.py` is cheap and now also
asserts that STRATEGY.md's weight tables match `state.py`, that the live
weight function rejects missing overlay inputs, and that the max(10,30)
`realized_vol_live` returns the plain 30-day reading (the max(10,30) leg is
disabled by flag and its code path still tested).

## 2a. Unexpected cash — deposits and withdrawals

If the account's cash differs materially from what the last run left behind
(a deposit or withdrawal you did not place), the target weights still apply
to the FULL `total_value` — new money is deployed to target, not held aside.
But a large unannounced balance change is worth one question before acting:
if the change exceeds 20% of the prior account value, report the reading and
the trades it implies and ASK the owner before placing them, rather than
deploying silently. Below that threshold, deploy to target and note the
change in the report. A deposit is not a circuit-breaker event.

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
  - **otherwise rebalance only if L1 drift > `REBALANCE_DRIFT_BAND`** (0.05; raised from 0.03 on 2026-09-09 -- performance-neutral, ~14% fewer trades: ~47/yr vs ~55),
    where drift = sum over the 5 legs of |target − held|. Since the legs each
    sum to 1.0, a 5% L1 drift is roughly "2.5 percentage points of the
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
(The max(10,30) estimator live 09-07..09-09 traded ~69x/yr against ~55 for
the 30-day one; that extra churn was part of why it was reverted.)

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
a tier is breached, not every day underwater. `current_drawdown()` returns a
TUPLE (drawdown, peak_date, peak_value, current_date, current_value) — take
element 0 for the drawdown itself.

Record the return only ONCE per session, and only for a completed session.
An intraday or off-schedule run must NOT append a row.

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

## 6. Order mechanics, when trading

  - Compute dollar targets = weight × `get_portfolio`'s `total_value`.
  - **No per-leg minimum.** Once the band has fired, every leg goes to target,
    however small its trade. (The old $100/0.3% skip was removed 2026-09-01.)
  - Sell before buy so proceeds are available. Check this explicitly when the
    buy side exceeds available buying power — a leg being liquidated to zero
    is what funds the buys.
  - Marketable limit orders: at/through the bid for sells, the ask for buys.
    Do not chase more than 0.3% through the touch. During regular hours (this
    trigger fires at 15:50 ET, so normally yes) fractional/dollar-based orders
    are fine. If any order must go extended-hours, it must be a WHOLE-SHARE
    limit order with `market_hours='extended_hours'` — fractional and
    dollar-based orders are rejected outside regular hours. Note a LIMIT order
    cannot be fractional in any session; to liquidate a fractional stub
    completely, use a market order in regular hours.
  - The cash leg is held as **BOXX**, never as idle buying power.
  - XLU is fractional-tradable in regular hours only.
  - After filling, re-verify holdings against target and report the resulting
    L1 drift; it should be near zero. Anything above the band after a
    completed rebalance means a fill failed — investigate, do not ignore.
  - **Record execution quality for EVERY filled leg** (added 2026-09-07).
    After fills, call `paper-track/fill_quality.py`'s
    `record_fill(date, symbol, side, quantity, fill_price, ref_price,
    session_lag=0)` once per leg (session_lag=1 for a next-session fill), where `ref_price` is the OFFICIAL CLOSE of the signal session
    (pass `ref_kind` if you had to use anything else). Then report
    `summarize()`'s notional-weighted slippage in bps against the **4bp
    one-way cost model the backtests assume**. This gates nothing and must
    never block or delay a trade -- it is measurement only. It exists because
    one session of execution lag costs 3.1pp of CAGR and 4.8pp of drawdown,
    larger than any design change made this week, and until now nothing
    checked it. Flag any single leg worse than 25bp; persistent
    notional-weighted slippage worse than 4bp means the live design is not
    the backtested one and is worth more attention than any parameter.
    IMPORTANT when interpreting a flag: on a same-session 15:5x run the
    reference IS effectively the fill session, so a large number is genuine
    execution slippage. On any run where the signal session and the fill
    session differ, most of the number is the overnight GAP, not broker
    execution — say which it is rather than reporting a gap as bad execution.

## 7. Reporting

On a within-band day with NO funding trigger: no report, no artifact edit —
just end.

**A FUNDING TRIGGER ALWAYS PRODUCES A REPORT, even on a no-trade day.** A new
drawdown tier can cross while the portfolio is comfortably within the drift
band, and the shift into A/B/C is a regime change that will normally trade
anyway — but do not rely on that. If either funding trigger fired, append an
entry even if nothing was bought or sold, and put the trigger at the TOP of
it: which trigger, the tier or the prior/new state, the account value, and the
standing $5,000-per-event policy. (Added 2026-09-07 — before this, a tier
crossing on a quiet day would have been silently dropped.)

On a rebalance: append to the weekly report artifact
(https://claude.ai/code/artifact/292cb8f5-b3ad-4a07-a522-91f8d8049c14),
newest week at top, stating the old state, new state (macro AND effective,
if the fast overlay is active), the extension-trim vote count, both vol legs
with the binding one and the resulting multiplier, the drift and which condition fired (regime change vs drift band),
the weights traded to, the fills, and the notional-weighted slippage.

To edit that artifact you must FIRST call the Artifact tool with
`action: "read"` and its URL, then build your edit on the version that comes
back and diff local against live before republishing — a publish to an
artifact this session has not read is refused.

Any live financial figure that combines two or more numbers (a daily total, a
new cumulative) must be computed in code from raw records
(`get_pnl_trade_history` / `get_realized_pnl`), never hand-added in prose —
`paper-track/consistency_check.py`'s `check_pnl_sum()` exists for this and a
real double-counting incident on 2026-08-31 is why.

Evidence discipline when commenting on the overlays: a circular BLOCK
bootstrap (2026-09-07) downgraded two claims that earlier day-shuffled tests
overstated. The graded extension trim survives (Sharpe 95% CI [+0.025,
+0.266], P(<=0) = 0.007); the fast re-entry overlay (P = 0.080) and the
max(10,30) volatility estimator (P = 0.097; reverted 09-09) do NOT clear 5% on their own.
Do not quote "p = 0.00" for any of them. Leave-one-major-regime-out keeps
every sign in every drop, including dropping the whole SPMO fitting window.

Never reproduce a standing performance figure by reimplementing the backtest
loop — call `improvement_search.run()` (or the harness that owns the figure).
A hand-rolled loop silently rebalances costlessly every day and produces
numbers that look right and are not.

## 8. Breadth forward test — MEASUREMENT ONLY, after step 3 (added 2026-09-11)

A pre-registered candidate rule is under forward test: "effective state D AND
the 60-day QQEW/QQQ relative-strength reading in its trailing-252 bottom
quintile (pct < 0.20) -> D row to cash". It is NOT applied and changes no
weight; the owner decides after 8 gated runs or 48 months by the rule in
`research_notes/dgate_anatomy.md` section 6. Your only job is to LOG it,
after every trading and reporting step and never inside 15:50-16:00:
  - Pull QQEW and QQQ daily closes (`get_equity_historicals`, 18 months,
    split-adjusted; QQEW is the equal-weight Nasdaq-100 ETF) and call
    `paper-track/breadth_tracker.py`'s
    `breadth_reading(dates, qqew, qqq, as_of=<today>)` -> x60, pct, gate.
    Use the OFFICIAL closes if the run is after 16:00, else the 15:5x
    snapshot and say so. pct None = insufficient history; report it, no row.
  - EVERY session, one line: "breadth pct 0.84, gate off".
  - On a session whose EFFECTIVE state is D: `record_d_day(date, 'D', x60,
    pct, gate)`; on the NEXT session `fill_next_returns(<that date>,
    qld_next, qqq_next)` with official close-to-close returns. In any report
    entry for a D day add ONE informational line: the breadth bucket, its
    historical breakdown rate `bucket_base_rate(pct)` (P(next state E/F);
    unconditional D-episode base rate 0.16) and the distance to the 200d.
    No commentary, no weight change, no notification.
  - `summarize()` is the running tally. Do not change GATE_PCT, LOOKBACK or
    WINDOW; do not act on the gate. Commit the log row with the NAV row.

If Robinhood MCP tools are unavailable, report that and stop — do not guess
prices or place orders on stale data.
