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

## 2. Morning brief — about 10:00, Mon–Fri (read-only)
`python3 public-strategy/public_run.py brief /tmp/public_<today>.json`, then ONE push with its `PUSH:` line, as printed.

## 3. Trade run — 15:50, Mon–Fri (12:50 on early-close days)
`python3 public-strategy/public_run.py signal /tmp/public_<today>.json`.
- `NO TRADE` or `DRY RUN`: place nothing.
- `TRADE` and enabled: `place_order` (it preflights itself) for each printed line, sells first, whole-share LIMIT,
  DAY, `equity_market_session` CORE, done by 15:59 (12:59 on early closes). Never chase more than 0.3% past the printed limit.
- Keep the order IDs `place_order` returns and read the fills with `get_order` on those IDs only (the autopilot's
  orders are in the same account). Write the fills as `[{"side","symbol","quantity","price"}]` (actual filled quantity and
  average price, filled orders only) and run `python3 public-strategy/public_run.py record <fills.json>`.
- Commit `data/public/runs/<today>.json` and `data/public/ledger.json`. One push only on a trade or a guard.
