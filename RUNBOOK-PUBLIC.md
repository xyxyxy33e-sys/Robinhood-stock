# RUNBOOK — Public.com taxable account 5OG87042

`public-strategy/public_run.py` computes everything; STRATEGY-PUBLIC.md says what and why. Account `5OG87042` only.
Never trade any ticker outside the script's printed orders. Never sell the account's individual stocks.

## 0. Rules
1. `git pull --ff-only` first.
2. Trade only what the script prints, and only when it does NOT print `DRY RUN`.
3. Exit 2 = guard: do not trade, report the line. Exit 3 = market closed: stop, no push.
4. Public tools unavailable: do not guess; say so.

## 1. Fetch and write the input (both runs)
- `get_quotes` (account `5OG87042`) for `SPY SSO IEF VTI EFA EEM TLT GLD DBC VNQ BOXX`.
- VIX for the panic leg: the script reads Yahoo's `^VIX` itself (2 years of closes plus the live value). If a fresher
  VIX reading is at hand, pass it as `"vix": <number>` in the input JSON; the script prints the VIX it used. If VIX
  cannot be read it says so and runs with the panic leg off.
- `get_portfolio` for `5OG87042` (large: read positions for those tickers and `cash` with jq).
- Write `/tmp/public_<today>.json`:
  `{"date","time","quotes":{SYM:{"last","bid","ask","close":<previousClose>,"last_trade_date":<date of lastTimestamp, ET>}},"positions":{SYM:qty},"cash":<cash>}`

## 2. Morning brief — about 10:00, Mon–Fri (read-only)
`python3 public-strategy/public_run.py brief /tmp/public_<today>.json`, then ONE push with its `PUSH:` line, as printed.

## 3. Trade run — 15:50, Mon–Fri (12:50 on early-close days)
`python3 public-strategy/public_run.py signal /tmp/public_<today>.json`.
- `NO TRADE` or `DRY RUN`: place nothing.
- `TRADE` and enabled: `preflight_order` then `place_order` for each printed line, sells first, limit orders, regular
  hours, done by 15:59 (12:59 on early closes). Never chase more than 0.3% past the printed limit.
- Commit `data/public/runs/<today>.json`. One push only on a trade or a guard.
