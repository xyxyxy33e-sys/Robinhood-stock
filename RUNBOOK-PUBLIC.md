# RUNBOOK — Public.com taxable account 5OG87042

`public-strategy/public_run.py` computes everything; STRATEGY-PUBLIC.md says what and why. Account `5OG87042` only.
Never trade any ticker outside the script's printed orders. Never touch the autopilot basket (about $50,000 of
individual stocks plus some BOXX, owner 2026-11-20): it trades on its own. The strategy owns only what
`data/public/ledger.json` lists (before the first trade: no shares, cash = `max_capital`).

## 0. Rules
1. `git pull --ff-only` first.
2. Trade only what the script prints, and only when it does NOT print `DRY RUN`.
3. Exit 2 = guard: do not trade, report the line. Exit 3 = market closed: stop, no push.
4. Public tools unavailable: do not guess; say so.

## 1. Fetch and write the input (both runs)
- `get_quotes` (account `5OG87042`) for `SPY SSO IEF VTI EFA EEM TLT GLD DBC VNQ BOXX`.
- VIX for the panic leg: `get_quotes` for `VIX` with `instrument_type` INDEX and pass its last price as
  `"vix": <number>` in the input JSON (Yahoo's live `^VIX` runs about ten minutes behind). Without it the script reads
  Yahoo's value; it prints the VIX it used. If VIX cannot be read at all it says so and runs with the panic leg off.
- `get_portfolio` for `5OG87042` (large: read positions for those tickers and `cash` with jq).
- Write `/tmp/public_<today>.json`:
  `{"date","time","quotes":{SYM:{"last","bid","ask","close":<previousClose>,"last_trade_date":<date of lastTimestamp, ET>}},"positions":{SYM:qty},"cash":<cash>}`

- **Dividends (trade run only; owner 2026-11-23: reinvest at the next run).** `get_history` for the last 10 days
  (large: parse with python, never print). Add `"dividends": [{"id","symbol","amount","date"}]` for rows with
  `subType` DIVIDEND on a strategy ticker. `signal` credits each new one once to the ledger's cash
  (`data/public/dividends.csv`) and, when no other trade is due, prints a buy of the strategy's free cash into the
  most underweight target holding (split across them when it is $100 or more). The brief never credits.

## 2. Morning brief — about 10:00, Mon–Fri (read-only)
`python3 public-strategy/public_run.py brief /tmp/public_<today>.json`, then ONE push with its `PUSH:` line, as printed.

## 3. Trade run — 15:50, Mon–Fri (12:50 on early-close days)
`python3 public-strategy/public_run.py signal /tmp/public_<today>.json`.
- `NO TRADE` or `DRY RUN`: place nothing.
- `TRADE` and enabled: `place_order` (it preflights itself) for each printed line, sells first, LIMIT with the fractional quantity exactly as printed (4 decimals; never an amount-based or MARKET order),
  DAY, `equity_market_session` CORE, done by 15:59 (12:59 on early closes). Never chase more than 0.3% past the printed limit.
- **Sells and tax lots (owner 2026-11-20: highest cost first, any of the account's lots).** If the output says
  `LOTS NEEDED`, call `get_tax_lots_for_symbol` for each ticker it names, add `"tax_lots": {SYM: <the "lots" list>}` to
  the input and run `signal` again. Place each sell with the printed `tax_lot_matching_instructions` and
  `open_close_indicator` CLOSE. If the broker refuses the lot instruction (its lot data is a day old, and it refuses
  after another trade in that ticker the same day), place the same sell without it.
- Keep the order IDs `place_order` returns and read the fills with `get_order` on those IDs only (the autopilot's
  orders are in the same account). Write the fills as `[{"side","symbol","quantity","price"}]` (actual filled quantity
  and average price, filled orders only; add `"lots": "default"` to a sell that went without a lot instruction) and run
  `python3 public-strategy/public_run.py record <fills.json>`. It updates `data/public/ledger.json` and appends each
  sale to `data/public/realized.csv`.
- Commit `data/public/runs/<today>.json`, `data/public/ledger.json` and `data/public/realized.csv`. One push only on a
  trade or a guard.

## 4. Dashboard — after every trade run, traded or not (owner 2026-11-20: update daily; not time-critical)
On a no-trade day use the run's own input (with `"account_value"`); the refresh places no order and sends no push.
`python3 public-strategy/public_run.py dash <input.json> <outdir>` (add `"account_value"` from `get_portfolio` to the
input; run it after `record`, with the positions and cash read again after the fills) writes `status.csv`,
`holdings.csv`, `tax.csv` and `value.csv` (the daily value against SPY; it also adds today's row to
`data/public/daily.csv`, which is committed and pushed after the refresh). For each: Artifact publish with `url` = the dashboard, `asset: true`, `file_path` = the
file; ArtifactData `get` `datasets/<id>` (ids `status`, `holdings`, `tax`, `value`) for its version and old `source.url`; one
ArtifactData `batch` of `update`s pinned with `if_version`: `{source: {kind: "file", url: "<new /_blob url>", name,
format: "csv"}, updated: {at: "<ISO now>", by: "Claude"}}`. Leave the old files in place (deleting them is not
permitted from a run; they are a few hundred bytes each). Never edit `files/index.html` from a run. If a step fails, say so and carry on.
**Every chat message that reports a dashboard refresh or change ends with the link (owner 2026-11-23):**
https://claude.ai/artifact/Ut3LWwtHC9ztXDCviogdZK

## 5. Weekly review — Fridays about 16:25, after the close (read-only, places no orders)
Section 1's fetch (quotes, VIX, `get_portfolio`; add `"account_value"`), then
`python3 public-strategy/public_run.py review <input.json>`. It appends the strategy's value to
`data/public/weekly.csv` and prints the week against SPY, the orders of the week, realized gains, holdings against
targets and the signals. Post the printed review in chat with a two-line plain reading of it (what moved the result,
anything that needs the owner), send ONE push with its `PUSH:` line, refresh the dashboard as in section 4, and commit
`data/public/weekly.csv`. If the market was closed on Friday, run it all the same on the last session's prices.

## 6. Backtest figures on the dashboard — only after a rule change
`PUB_OUT=<dir> python3 public-strategy/backtest.py` (downloads Yahoo data; `PUB_END=<date>` fixes the last session)
writes `stats.csv`, `nav.csv` and `years.csv`; upload them to the dashboard datasets of the same names as in section 4.

## 7. Adding or removing strategy money — only on the owner's instruction in chat
`python3 public-strategy/public_run.py deposit <dollars> "<note>"` (negative takes money out of the strategy's cash).
It changes only the ledger's cash, logs the flow in `data/public/flows.csv` and makes `max_capital` the total put in.
Place no order for it: the next trade run sees the drift and prints the orders. Use the account's cash only
(`cashOnlyBuyingPower`), never margin buying power. Commit ledger, flows and config.
