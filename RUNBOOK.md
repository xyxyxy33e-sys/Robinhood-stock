# RUNBOOK — Robinhood Agentic account (576391551)

The procedure every Routine follows. **STRATEGY.md** says what the strategy is
and why; **`paper-track/live_run.py`** does every calculation; this file says
what to do, in what order. Routine prompts only point here. If this file and a
prompt disagree, this file wins; if this file and STRATEGY.md disagree on the
design, STRATEGY.md wins and the run reports the conflict.

Account `576391551` only. Everything below is US/Eastern.

## 0. Rules for every run

1. `git pull --ff-only` first. If it is not a fast-forward, stop and report.
2. **Trade what the code prints.** Never a number from prose, a past report or
   memory. Never edit `state.py`, `STRATEGY.md`, this file or a Routine from a
   run. Design changes come from the owner.
3. **Guards.** `live_run.py` exits **2** when a guard trips (weight sanity,
   circuit breaker, missing overlay input, positions outside the strategy).
   Do not trade; report the guard line verbatim; it is the day's push.
   Exit **3** = market closed: say so and stop (no push, no data rows).
4. If the Robinhood tools are unavailable: do not guess prices or trade. Say
   so; the post-close run's push carries it.
5. Time matters more than prose. In the trade window do nothing but steps 1.1–1.5.
6. Commit only `data/` files the run wrote, one line per commit.

## 1. Trade run — 15:50, Mon–Fri

1.1 **Fetch** (three calls, nothing else):
- `get_equity_quotes` for `QQQ QQEW SPMO TQQQ QLD XLU BOXX VIXM`
- `get_index_quotes` for VIX, id `3b912aa2-88f9-4682-8ae3-e39520bdf4db`
- `get_equity_positions` and `get_portfolio` for `576391551`

1.2 **Write** `data/runs/in/<today>.json`:
```json
{"date": "<today>", "time": "<HH:MM ET>",
 "quotes": {"<SYM>": {"last": <quote.last_trade_price>, "bid": <bid_price>, "ask": <ask_price>,
                      "close": <close.price>, "close_date": "<close.date>",
                      "last_trade_date": "<date of venue_last_trade_time, ET>"}, "...": "all 8"},
 "vix": <VIX value>,
 "positions": {"<SYM>": <quantity>},
 "idle_cash": <portfolio cash>, "total_value": <portfolio total_value>}
```

1.3 **Run** `python3 paper-track/live_run.py signal data/runs/in/<today>.json`.
It prints the readings, the target, the held weights, the drift, the decision and
the orders. It also writes `data/runs/<today>.json`, which every later step reads.

1.4 **If `DECISION: TRADE`:** place the printed orders, in the printed order (sells first).
- `LIMIT` lines are whole-share marketable limits. Never chase more than 0.3% beyond the printed limit.
- `MARKET dollar-based` and `MARKET` stub lines are regular-hours market orders.
- If a buy exceeds buying power, wait for the sells to fill.
- Target 15:54–15:57; never place after 15:59.
- **VIXM trades in regular hours only.** If it cannot fill now, it waits for the next open; report that.

**If `NO TRADE`** and an idle-cash sweep is printed, place those dollar-based buys. Otherwise do nothing.

1.5 **Stop.** Fills, records, report and push all belong to the post-close run.
Only after the orders are placed: one short line to the session ("traded / no trade, why").

## 2. Post-close run — 16:10, Mon–Fri

2.1 **Holiday check.** Read the QQQ quote. If today did not trade, stop; send no push.

2.2 **Did the trade run finish?** Run `python3 paper-track/live_run.py status`.
- **Run file present:** pull today's agentic orders with
  `get_equity_orders(account_number, created_at_gte=<today 00:00 UTC>, placed_agent='agentic')`.
  Any order rejected, cancelled or partially filled, or a leg still off target, means finishing the rebalance now.
  To see what is left without overwriting the trade-run record, refetch per 1.1 into
  `data/runs/in/<today>-check.json` and run `live_run.py check <that file>`.
- **No run file, or a non-guard failure:** that is the FALLBACK. Refetch per 1.1 and run
  `live_run.py signal` on it; it computes on the close. Then place the orders.
  - After 16:00, extended hours: WHOLE-SHARE limit orders only, `market_hours='extended_hours'`, at most 0.3% through the touch.
  - Fractional stubs and every VIXM line wait for the next regular session. List them in the push.
  - Lose the overnight, never the signal.
- **Guard tripped in the trade run:** do not override it. It leads the push.

2.3 **Record.** Write `data/runs/in/<today>-record.json`:
```json
{"date": "<today>", "closes": {"<SYM>": <last_trade_price now, for all 8>},
 "fills": [{"symbol": "...", "side": "buy|sell", "quantity": <cumulative_quantity>, "price": <average_price>}],
 "session_lag": 0, "total_value": <get_portfolio total_value>}
```
- `fills` lists every agentic order filled today. Use `session_lag` 0 when the fill was on today's signal, even after the close.
- Run `python3 paper-track/live_run.py record data/runs/in/<today>-record.json`.
- It logs the fills and their slippage, the NAV row and drawdown, the shadow tracks with the trim-v2 revert rule,
  and the breadth log on D days. It prints any funding push.

2.4 **Fridays only.** Do these before the dashboard:
- **Weekly report.** Append one entry, newest at top, to `https://claude.ai/artifact/65u1kZeRoYha2Amps9mESw` from the week's
  `data/runs/*.json` files. It covers:
  - state, trim, D gate, D ladder zone (D1/D2/D3, on D days) and VIXM readings
  - each day's decision and trades, with slippage
  - realized P&L split usable / wash-sale-deferred, via `wash_sale.flag_wash_sales(trades, require_buys=True)`.
    The trade list comes from `get_pnl_trade_history` plus the BUYS from `get_equity_orders`, filled, from 30 days before the earliest loss sale.
  - drawdown
  - the shadow-track summary line and verdict
  - the standing limitations (STRATEGY.md "Known limitations")

  Read the artifact first (action `read`), then edit surgically.
- **Top-N paper mark.** Run the paper-only top-5/10/15 momentum mark per the docstring of
  `paper-track/topn_momentum_track.py`. Commit `data/topn_momentum_*`. It never touches the live book.

2.5 **Dashboard.** Update `https://claude.ai/artifact/HoxQpURsWcALzFG7hGr5ck`.
- Read it first, then edit the saved `index.html` surgically. Use figures from today's run file and the record output only.
- Update: the as-of line; the four top cards; target vs held; the QQQ/SMA card and its threshold lines; the positions table; the NAV/footer.
- Leave the backtest charts alone.

2.6 **One push** per trading day: `PushNotification`, proactive, one line, at most about 250 characters, figures only.
- **Lead with whatever needs the owner:**
  - a guard trip, or a missed or fallback run, naming any legs that wait for the open
  - a funding trigger, quoted exactly as `live_run.py` printed it
  - a regime shift
  - a REVERT or AFFIRM verdict
  - missing records
  - a long-term buy level (below)
- **Then the shape:** `Agentic $X (±$Y / ±Z% strategy) · <eff> <split>, drift d% · <traded …|no trade> · VIXM <in/out/latch> · DD -x% · recorded`.
- **Long-term line.** `data/longterm_watch.json` holds VTI and VXUS entries in the owner's account ending 6826, which is READ-ONLY.
  - Add `LT: VTI ±a%, VXUS ±b% vs entry`.
  - When a level not yet in `reached` closes at or below, lead with `BUY-MORE LEVEL …`, append it to `reached`, and commit.
- If a re-fire finds today's push already sent, send nothing.

2.7 **Commit** the run's `data/` files: `<today>: <eff state>, <traded|no trade>, NAV ±x%`.

## 3. Monthly check — 1st of the month, 10:00

This is not a strategy review and changes nothing.
- **Compare.** The account's time-weighted return since the last check (deposits removed) against `data/live_nav_index.csv`.
- **Holdings.** Every `data/runs/*.json` against its record:
  - a regime change not traded in the same session is MATERIAL
  - drift above 5% not traded by the next session is MATERIAL
- **Fills.** `fill_quality.summarize()` against the 4bp cost model.
- **Report.**
  - Gap within about 1.5pp per month or 3pp cumulative, and nothing material: one paragraph.
  - Otherwise: find the dates, check the Routines' `last_run`, and report the cause. Change nothing.

## 4. Schedule, sessions, recovery

- **Routines.** Trade run `50 15 * * 1-5`, post-close `10 16 * * 1-5`, monthly `0 10 1 * *`, all `CRON_TZ=America/New_York`.
  US daylight-saving changes need no edit.
- **Session.** They fire into the lean runner session, not the owner's long conversation session.
- **Missed trade run.** The post-close run's fallback (2.2) catches it. A missed post-close run is caught by the next trade run:
  `live_run.py` fills price gaps from Yahoo and recomputes a missing prior-day target.
  Run `record` for a missed date by hand if its NAV row matters.
- **Rollback.** The pre-2026-10-08 prompts are saved in `paper-track/trigger_prompts/archive-2026-10-08/`.
  Re-creating the old Routines from them restores the old workflow exactly. `state.VIXM_OVERLAY_ENABLED = False` removes VIXM alone.
- **Same account, other Routines.** The 0DTE/7DTE options Routines also name this account. They are dry-run.
  If they ever go live, their buying power must be fenced from this strategy first.
