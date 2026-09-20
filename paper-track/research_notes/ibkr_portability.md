# Can this strategy run in an IBKR account? — researched 2026-09-20

**Short answer: the strategy ports cleanly; the *automation* does not.**
Every economic and instrument constraint is satisfied — IBKR is cheaper than
the cost model assumes, holds all four legs, and supports fractional trading.
The blocker is execution: IBKR's official Claude connector **cannot place
orders**. It drafts non-binding instructions that the owner must review and
submit by hand inside an IBKR app. Autonomous daily execution at IBKR needs a
self-hosted TWS-API bridge on an always-on machine, which this cloud session
cannot host.

## 1. What actually blocks it

**IBKR's connector is draft-and-sign-off, by design.** The connector appears
in the Claude connector registry as "Interactive Brokers (IBKR)" (not
installed here). Its advertised tools are read-side —
`get_account_balances`, `get_account_positions`, `get_account_summary`,
`get_orders`, `get_portfolio_allocation`, `get_price_history`,
`get_price_snapshot` — plus `get_order_instructions`. An instruction lands in
an **AI Instructions** tab on the Orders and Trades page and stays there until
the owner clicks **Review & Submit**. IBKR's own documentation: *"All such
instructions must be reviewed and explicitly confirmed by the client within an
IBKR application before any action is taken"*, and instructions never become
orders automatically.

The live design is a scheduled Routine that fires at 15:50 ET and places
orders at **15:54–15:57**, unattended, on the same session's close proxy —
"lose the overnight, never the signal". Under the IBKR connector that window
requires a human at a screen. Concretely: ~45 rebalances/yr, each needing
sign-off inside a ~5-minute window, plus a daily no-trade check. A missed
window is not a missed trade — it is a **next-session fill**, which the
fill-quality tracker already flags as `session_lag=1` and whose cost is mostly
the overnight gap, not slippage. The 2026-09-20 lag study measured exactly
this. Running the live design with every decision executed one session late
costs, against the same design executed same-session: **proxy Sharpe −0.050
full period (search −0.033, holdout −0.064), real daily −0.029 Sharpe and
−1.19 pp of CAGR** (37.30% → 36.11%, and proxy 25.46% → 23.83%). That is
larger than any design change tested this month — the whole step-0.5 debate
was over +0.29 pp of real CAGR. Routinely lagged fills would give back several
times what the best available improvement offers.

**Market data.** Real-time US equity quotes at IBKR require a subscription
(US Equity and Options Add-On Streaming Bundle, ~$4.50/month). Without one,
data is delayed 10–20 minutes, or free real-time from Cboe One/IEX only —
non-consolidated, no NBBO. A 15:50 decision on 15-minute-delayed data is a
15:35 decision, which silently breaks the snapshot convention every figure on
record is calibrated to. Cheap to fix, but it must be fixed deliberately, and
the subscription attaches **per username** — it has to sit on whichever login
the automation uses.

## 2. What is not a problem

**Instruments.** SPMO, TQQQ, QLD and BOXX are all US-listed ETFs; IBKR trades
all of them. Fractional trading covers 10,500+ US stocks and ETFs with a
USD 0.01 minimum order, so the dollar-target mechanics survive — but
fractional permissions must be enabled on the account, and each ticker's
eligibility confirmed before go-live rather than assumed.

**Cost — IBKR is cheaper than the model assumes.** The design trades a lot:
490 rebalances over 10.8 years (45.3/yr), average L1 drift 81.7% per
rebalance, i.e. **~3700% of NAV in one-way turnover per year**. At the
modelled 4 bp that is **148 bp/yr of drag, already inside the 37.30% CAGR**.
Adding IBKR commissions on top, at current prices:

| plan | per-leg commission | annual drag | on $207.6k |
|---|---|---|---|
| Pro Tiered ($0.0035/sh, min $0.35) | SPMO 0.23, TQQQ 0.48, QLD 0.38, BOXX 0.30 bp | **+12.9 bp/yr** | ~$268/yr |
| Pro Fixed ($0.005/sh, min $1) | 0.34 / 0.69 / 0.55 / 0.42 bp | +18.5 bp/yr | ~$384/yr |
| Lite | $0 on US exchange-listed stocks/ETFs | +0 | $0 |

Against a design that was re-tested at **20 bp one-way (741 bp/yr) and still
beat live**, 13–19 bp/yr is immaterial. The $0.35/$1 order minimums almost
never bind — average legs are far above the ~$10k where they stop mattering.

The real cost question is not commission but **fill quality**. Robinhood and
IBKR Lite both route with payment for order flow; IBKR Pro with SMART routing
plausibly fills better. The 4 bp assumption is spread and slippage, not
commission, and `fill_quality.py` already measures it against the official
close — so this is answerable with data after a switch, not before.

**Day-trading rules.** Positions are held overnight and there are ~45
rebalances a year, so PDT never engages.

**Account type.** Rebalances sell one leg to fund another the same session.
Under T+1 a *cash* account risks good-faith violations doing that; a **margin
account** is required, even though the strategy never borrows.

**Code coupling is small.** `state.py`, `monthly_returns.py` and every
backtest are broker-agnostic. The Robinhood dependency lives entirely in the
two trigger prompts — tool names (`get_portfolio`, `get_equity_quotes`,
`place_equity_order`) and Robinhood-specific order semantics (dollar-based
fractional orders in regular hours, whole-share limit orders extended-hours).
Porting is a rewrite of two prompt files, not of the strategy.

## 3. The one thing IBKR would do better

IBKR supports **market-on-close** orders, which Robinhood does not. The
backtest convention is "decide on close t, hold t→t+1", with the 15:5x
snapshot standing in for the close and `fill_quality` measuring the gap. MOC
would fill at the *actual official close*, collapsing that gap to zero and
removing a known source of tracking error.

It is not free: MOC cutoffs are **15:45 ET (NYSE) and 15:50 ET (Nasdaq)** —
*before* the current 15:50 trigger. The signal would have to be computed
around 15:40, and MOC orders cannot be cancelled after the cutoff. That is a
different snapshot convention and would need its own study before adoption,
not a switch to flip. Worth noting it is a genuine upgrade available only at
IBKR.

## 4. The routes, ranked

**(a) Official IBKR connector, owner signs off.** Works today, costs nothing,
loses unattended execution. Viable only if the owner is reliably at a screen
at 15:50 ET on rebalance days. Given the measured cost of lagged fills, this
is a real degradation, not a formality.

**(b) Self-hosted TWS-API bridge.** Community MCP servers exist
(`jinyiabc/ibkr-mcp`, `code-rabi/interactive-brokers-mcp`) that place orders
through the TWS API. **This is the only route that preserves autonomous
execution.** The catch: TWS or IB Gateway must run as a persistent process,
and IBKR does not support a headless session — it needs a virtual display
(Xvfb) plus login automation (IBC), on an always-on machine or VPS.
**This session's container cannot host it**: it is ephemeral and reclaimed
after inactivity. This route means the owner running and maintaining
infrastructure, and it puts order placement behind software IBKR does not
support for unattended use.

**(c) Stay at Robinhood.** The current path. Unattended execution works, fills
are measured, commissions are zero.

## 5. Recommendation

**Do not move the live account.** Nothing about IBKR improves the strategy's
economics — the cost advantage is ~13 bp/yr on a design that tolerates 741 —
and the move would either surrender unattended execution (route a) or take on
unsupported infrastructure (route b). The measured cost of a one-session
execution lag is larger than any edge tested this month.

If IBKR is wanted for reasons outside this strategy — a second venue,
international access, MOC execution, securities lending — the defensible
sequence is: open the account, install the connector read-side, and run it as
a **shadow book** for a quarter, with `fill_quality.py` recording IBKR's fills
against the official close alongside Robinhood's. That answers the only open
question (does IBKR Pro fill better than Robinhood?) with data, at no risk to
the live account.

Nothing applied; no account action taken. This is research only.

Sources: IBKR AI integrations and AI Instructions documentation
(interactivebrokers.com/en/trading/ai-integrations.php,
ibkrguides.com/clientportal/gen-ai-instructions.htm), IBKR stock commissions
and market-data pricing pages, IBKR Campus TWS API setup notes, and the
Claude connector registry entry for Interactive Brokers.
