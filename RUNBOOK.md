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
7. Margin loan (`data/margin_loan.json`, STRATEGY.md "Margin-funded deposits"): `live_run.py` sizes draws,
   flags the repay and holds the repay cash out of the strategy. Never edit the ledger from a run except
   by running `live_run.py`; never sweep or reinvest held repay cash.
   **Netting (2026-10-16):** while a loan is drawn the strategy holds no BOXX up to the loan amount;
   `live_run.py signal` keeps that cash back (orders already reflect it, the `netted:` line shows the
   weights) and, after 2 sessions, prints `MARGIN REPAY: transfer $X …` or `MARGIN DRAW (re-borrow): …`.
   Trade the printed orders as usual; never buy BOXX with cash the run is keeping back.
   **Draws are OFF (owner 2026-10-16, 6826 bonus hold):** no `MARGIN DRAW` lines are printed; funding
   triggers are still reported. The existing loan still repays (`MARGIN REPAY`, `MARGIN REPAY DUE`).
8. **Pre-committed rules (owner 2026-11-19; STRATEGY.md "Pre-committed rules").**
   - **Risk brake (automatic).** `live_run.py` halves every non-BOXX leg once the strategy NAV is 40% below its
     peak, and goes back to full size once the full-size strategy is within 20% of the peak (state in
     `data/risk_brake.json`). It prints `RISK BRAKE ON/OFF` and a push; trade the printed orders as usual.
     Never edit the brake file by hand.
   - **Pause.** While `data/trading_paused.json` exists, `live_run.py` exits 2 with `TRADING PAUSED`: trade
     nothing, lead the push with it. `live_run.py` writes the file itself when the same guard trips on 3 runs in
     a row; the monthly check writes it on a tracking breach (section 3). Only the owner deletes it.

## 1. Trade run — 15:50, Mon–Fri

1.1 **Fetch** (four calls, nothing else):
- `get_equity_quotes` for `QQQ QQEW SPY TQQQ QLD XLU BOXX VIXY` (the core trades SPY from 2026-11-20, SPMO before; the volatility sleeve trades VIXY from 2026-11-11, VIXM before)
- `get_index_quotes` for VIX, id `3b912aa2-88f9-4682-8ae3-e39520bdf4db`
- `get_equity_positions` and `get_portfolio` for `576391551`
- `get_equity_historicals` for `["QQQ"]`, interval `30minute`, start_time `<today>T14:30:00Z` (regular session):
  `qqq_high` = the largest `high_price` across today's bars. Since 2026-11-17 the D gate reads the
  15:50 price only (L1 switched off, owner); the high is still logged so `l1_tracker.py` can follow L1 on
  paper. If the call fails, omit `qqq_high`; the run is unaffected.

1.2 **Write** `data/runs/in/<today>.json`:
```json
{"date": "<today>", "time": "<HH:MM ET>",
 "quotes": {"<SYM>": {"last": <quote.last_trade_price>, "bid": <bid_price>, "ask": <ask_price>,
                      "close": <close.price>, "close_date": "<close.date>",
                      "last_trade_date": "<date of venue_last_trade_time, ET>"}, "...": "all 8"},
 "vix": <VIX value>,
 "qqq_high": <QQQ intraday high so far, from the historicals call>,
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
- Target 15:54–15:57; never place after 15:59. **Early-close days** (13:00 close, `live_run.EARLY_CLOSES`):
  the trade run fires at 12:50 instead; target 12:54–12:57, never after 12:59. The 15:50 run then exits 3.
- **VIXY trades in regular hours only on Robinhood (like VIXM before it).** It must fill in this window; if it cannot, it waits for the next open; report that.
- **Gross cap 2.0x (2026-11-11):** `live_run.py` already applies it; trade the printed orders as they are.

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
  - Fractional stubs and every VIXY (or legacy VIXM) line wait for the next regular session. List them in the push.
  - Lose the overnight, never the signal.
- **Guard tripped in the trade run:** do not override it. It leads the push.

2.3 **Record.** Write `data/runs/in/<today>-record.json`:
```json
{"date": "<today>", "closes": {"<SYM>": <last_trade_price now, for all 8: QQQ QQEW SPY TQQQ QLD XLU BOXX VIXY, plus SPMO for the shadow tracks>},
 "fills": [{"symbol": "...", "side": "buy|sell", "quantity": <cumulative_quantity>, "price": <average_price>}],
 "session_lag": 0, "total_value": <get_portfolio total_value>}
```
- `fills` lists every agentic order filled today. Use `session_lag` 0 when the fill was on today's signal, even after the close.
- Run `python3 paper-track/live_run.py record data/runs/in/<today>-record.json`.
- It logs the fills and their slippage, the NAV row and drawdown, the shadow tracks with the trim-v2 revert rule,
  and the breadth log on D days. It prints any funding push.

2.3a **Core is SPY (owner 2026-11-19, from the 2026-11-20 run).** The core leg (`state.CORE_INSTRUMENT`) is SPY.
Any SPMO left in this account is outside the strategy: `live_run.py` raises the positions guard. Never buy SPMO here:
the owner's IRA holds SPMO, and the switch removes the wash-sale overlap.

2.3b **Simple-rule yardstick (owner 2026-11-19).** Run `python3 paper-track/simple_sp_track.py`. It rebuilds
`data/simple_sp_paper.csv` (2x S&P above SPY's 200-day, T-bills below; paper only, nothing traded) and prints two
lines: the yardstick's holding and NAV since 19 Nov 2026, and the IRA SPMO buy window. Commit the CSV with the
day's data. Put both lines in the Friday weekly report; add nothing to the daily push. If Yahoo fails, say so and
carry on.

2.4 **Fridays only.** Do these before the dashboard:
- **Weekly report.** Append one entry, newest at top, to `https://claude.ai/artifact/65u1kZeRoYha2Amps9mESw` from the week's
  `data/runs/*.json` files. It covers:
  - state, trim, D gate, D ladder zone (D1/D2/D3, on D days; note a day the ±0.5% buffer held the zone —
    `live_run.py` prints "held by the +/-0.5% buffer; plain reading …") and VIXM readings
  - each day's decision and trades, with slippage
  - realized P&L split usable / wash-sale-deferred, via `wash_sale.flag_wash_sales(trades, require_buys=True)`.
    The trade list comes from `get_pnl_trade_history` plus the BUYS from `get_equity_orders`, filled, from 30 days before the earliest loss sale.
  - drawdown
  - **tax-year capital gains** (owner 2026-11-11: this account is taxable and the owner offsets it with
    tax-loss harvesting elsewhere, so the aim is to keep its net gain low and visible). One small table for the
    calendar tax year to date: realized gain/loss from `get_realized_pnl` span `ytd`; the wash-sale-deferred part
    (from the `wash_sale.flag_wash_sales` line above) and so the estimated reportable net; short- vs long-term
    where `get_equity_tax_lots` / the trade history shows the term; unrealized gain/loss on open lots
    (`get_equity_tax_lots` per held symbol against Friday's close), noting any deferred loss sitting in a lot's
    basis that the next sale will release. Add the change since last Friday, and the 2027 projection range from
    `paper-track/research_notes/tax_2026_11/` until January, then the projection for the year in progress.
    Robinhood's numbers are before its own wash-sale adjustments; say so. Not tax advice.
    **K-1 split** (owner 2026-11-17): VIXY and VIXM (and VIXM before them) are ProShares Trust II commodity
    pools that issue a Schedule K-1, not a 1099-DIV; their futures gains pass through as roughly 60% long-term /
    40% short-term whatever the holding period. In the table, show the VIXY+VIXM realized gain/loss on its own
    row with that 60/40 estimate beside it, every other symbol as short-term, and the netted total under both
    views (all short-term as Robinhood reports it, and the K-1 estimate). Say that the true split comes on the
    K-1s in mid-March and that the 1099-B for these funds needs the K-1 basis adjustment. The owner is in New
    York City: state and city tax treat all capital gains as ordinary income, so the 60/40 saving is federal
    only.
  - **December year-end wash check** (owner 2026-11-11; every Friday report from the first Friday of December
    through the last Friday of January). List each loss sale in the prior 30 days that is still open to a wash
    (symbol, date, shares, realized loss, the date its 30-day window closes) and say, for each, whether the
    current target holds or would buy that symbol, so a re-buy would push the loss across the year boundary
    (a December loss washed by a January buy lands in the next tax year). Flag any such loss above $5k at the
    top of the entry. Report only: the run still trades exactly the printed orders; the owner decides whether
    to ask for a substitute (research: `research_notes/tax_2026_11/`, December-only substitute rules rejected).
  - the shadow-track summary line and verdict
  - the standing limitations (STRATEGY.md "Known limitations")

  Read the artifact first (action `read`), then edit surgically.
- **Top-N paper mark.** Run the paper-only top-5/10/15 momentum mark per the docstring of
  `paper-track/topn_momentum_track.py`. Commit `data/topn_momentum_*`. It never touches the live book.

2.5 **Dashboard.** Update `https://claude.ai/artifact/HoxQpURsWcALzFG7hGr5ck`.
- Read it first, then edit the saved `index.html` surgically. Use figures from today's run file and the record output only.
- Derived figures (moving averages, state lines, positions table): `python3 paper-track/dashboard_figures.py <today> SYM=qty@avg_cost ...`.
  Copy the saved page into the scratchpad and change it with the Edit tool (pre-approved), then publish with the Artifact tool.
  No inline `python3 -` scripts: they are not pre-approved and stop an unattended run at a permission prompt.
- Account value is NET of the margin loan (the `NET` line `live_run.py record` prints: value minus loan + interest), with the gross value beside it.
- Update: the as-of line; the four top cards; target vs held; the QQQ/SMA card and its threshold lines; the positions table; the NAV/footer.
- **Realized column in the positions table** (added 2026-10-22, owner): on a day with any sell, refresh it from
  `get_pnl_trade_history(account_number='576391551', span='all')`: per-symbol sums of `realized_gain` for SPMO, QLD,
  TQQQ, VIXM (sleeve until 2026-11-10), VIXY (sleeve from 2026-11-11), QQQ (deep-E leg, from 2026-11-11), BOXX; the "closed earlier" row is everything else (gold, the 31 Aug stock mirror, pre-strategy trades);
  the total must equal `get_realized_pnl(span='all', asset_classes=['equity'])['total_returns']`. Sum in code, never
  by hand. Robinhood's figures are before wash-sale deferral; keep the note saying so.
- **Cumulative return section** (added 2026-10-22, owner): `dashboard_figures.py` prints a `cumulative since ...` block.
  Replace the whole `const CUM = [...];` line in the page script with the printed one; set the three figures
  (`id="cum-s"`, `cum-q`, `cum-m`, sign class `pos`/`neg`), their sub-lines (NAV and distance from its high;
  strategy vs QQQ and vs SPMO in points) and the month line (`id="cum-months"`) from the same block.
- Leave the backtest charts alone.

2.6 **One push** per trading day: `PushNotification`, proactive, one line, at most about 250 characters, figures only.
- **Lead with whatever needs the owner:**
  - a guard trip, or a missed or fallback run, naming any legs that wait for the open
  - ~~a funding trigger~~ — removed 2026-10-19 (owner); `live_run.py` no longer prints one
  - a `MARGIN DRAW`, `MARGIN DRAW (re-borrow)`, `MARGIN REPAY` or `MARGIN REPAY DUE` line, quoted exactly
    (the owner moves the money; the run never does). `live_run.py record` repeats the trade run's margin
    lines as `PUSH:` so the post-close push carries them.
    When the owner says a draw's transfer has landed, run `live_run.py draw-orders` and place the printed
    whole-share limits (extended hours after 16:00, regular hours otherwise).
  - a regime shift
  - a REVERT or AFFIRM verdict
  - missing records
  - a long-term buy level (below)
- **Then the shape:** `Agentic $X (±$Y / ±Z% strategy) · <eff> <split>, drift d% · <traded …|no trade> · VIXM <in/out/latch> · DD -x% · recorded`.
- **Long-term line: RETIRED 2026-10-19** (VTI/VXUS sold; `longterm_watch.json` has `retired`). Skip the two bullets below while `retired` is set.
- **Long-term line.** `data/longterm_watch.json` holds VTI and VXUS entries in the owner's account ending 6826, which is READ-ONLY.
  - Add `LT: VTI ±a%, VXUS ±b% vs entry`.
  - When a level not yet in `reached` closes at or below, lead with `BUY-MORE LEVEL …`, append it to `reached`, and commit.
- While a margin loan is open, `$X` is the NET value (gross minus loan + interest) and the line adds `· margin $L`.
- If a re-fire finds today's push already sent, send nothing.

2.7 **Commit** the run's `data/` files: `<today>: <eff state>, <traded|no trade>, NAV ±x%`.

## 3. Monthly check — 1st of the month, 10:00

This is not a strategy review and changes nothing.
- **Compare.** The account's time-weighted return since the last check (deposits removed) against `data/live_nav_index.csv`.
- **Holdings.** Every `data/runs/*.json` against its record:
  - a regime change not traded in the same session is MATERIAL
  - drift above 5% not traded by the next session is MATERIAL
- **Fills.** `fill_quality.summarize()` against the 4bp cost model.
- **D gate on the day's high (L1, off since 2026-11-17, followed on paper).** Run `python3 paper-track/l1_tracker.py` and copy its table into the report: the sessions where the gate would have opened on the day high while the 15:50 price kept it shut, and what QQQ did after 1, 5 and 20 sessions. Report it; change nothing.
- **Report.**
  - Gap within about 1.5pp per month or 3pp cumulative, and nothing material: one paragraph.
  - Otherwise: find the dates, check the Routines' `last_run`, and report the cause. Change nothing.
- **Pause on a tracking breach (owner 2026-11-19).** If live trails the model (what the rules say the account
  should have earned on the same prices) by **3 pp or more cumulative**, write
  `data/trading_paused.json` = `{"since": "<today>", "reason": "tracking breach: live <x>% vs model <y>% since <date>"}`,
  commit it, and push "TRADING PAUSED: tracking breach …". The owner investigates and deletes the file to resume.
- **Strategy review flag (owner 2026-11-19).** Once 3 years of live NAV exist (from 2029-09), report the rolling
  3-year return of `data/live_nav_index.csv` against the T-bill return over the same window. Below cash: say
  "STRATEGY REVIEW DUE" at the top of the report and in the push. This is a decision for the owner, not an action.

## 5. Morning brief — about 10:00, Mon–Fri (owner 2026-11-19)

Read-only. Never place, modify or cancel an order, and write nothing under `data/`.
5.1 **Fetch** the first three calls of 1.1 (quotes for all 8, SPY among them, VIX, positions/portfolio for `576391551`),
    and `get_index_quotes` with symbols `["SPX"]` for the S&P 500 level. The S&P 500 is reported only, not used by the rules.
    If QQQ's last trade is not today: market closed, stop, no push.
5.2 **Write** the 1.2 JSON (with `"time"`, SPY in `quotes`, `"spx": <SPX value>`, no `qqq_high` needed) to `/tmp/morning_<today>.json`, not `data/`.
5.3 **Run** `python3 paper-track/morning_brief.py /tmp/morning_<today>.json`. It runs `live_run.py check` on
    the morning price (what 15:50 would do if QQQ closed here), then the same live rules with QQQ moved
    −8%..+8% and VIX from 12 to 40, and prints where the target would change.
5.4 **Push** exactly one notification: the script's `PUSH:` line exactly as printed (it is kept under 200
    characters, because longer pushes are truncated or dropped on phones). Add nothing to it. If a guard trips or the tools are
    unavailable, push that instead. This push is separate from the post-close run's one push.

## 4. Schedule, sessions, recovery

- **Routines.** Trade run `50 15 * * 1-5`, post-close `10 16 * * 1-5`, morning brief `57 9 * * 1-5`, monthly `0 10 1 * *`, all `CRON_TZ=America/New_York`.
  US daylight-saving changes need no edit.
- **Session.** They fire into the lean runner session, not the owner's long conversation session.
- **Missed trade run.** The post-close run's fallback (2.2) catches it. A missed post-close run is caught by the next trade run:
  `live_run.py` fills price gaps from Yahoo and recomputes a missing prior-day target.
  Run `record` for a missed date by hand if its NAV row matters.
- **Rollback.** The pre-2026-10-08 prompts are saved in `paper-track/trigger_prompts/archive-2026-10-08/`.
  Re-creating the old Routines from them restores the old workflow exactly. `state.VIXM_OVERLAY_ENABLED = False` removes VIXM alone;
  `state.DEEP_E_ENABLED = False` removes the deep-E QQQ leg alone (2026-11-11).
- **Early closes (added 2026-11-19).** NYSE closes at 13:00 on the day after Thanksgiving and some Christmas
  Eves (2026-11-27, 2026-12-24, 2027-11-26). One-shot Routines fire the trade run at 12:50 ET on those dates, into
  the same runner session; the regular 15:50 run exits 3 (`EARLY_CLOSES` in `live_run.py`); the 16:10 post-close
  run is unchanged and is the fallback if the 12:50 run was missed. Each December, add the next year's early
  closes to `EARLY_CLOSES` and create their 12:50 one-shot Routines.
- **Same account, other Routines.** The 0DTE/7DTE options Routines also name this account. They are dry-run.
  If they ever go live, their buying power must be fenced from this strategy first.
