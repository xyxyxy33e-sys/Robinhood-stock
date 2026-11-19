# Public.com taxable account (5OG87042) — trend + rotation strategy

Status: **built, dry run** (`data/public/config.json` `enabled=false`). Owner request 2026-11-19. Separate from the
Robinhood Agentic strategy (STRATEGY.md) and the IRA (buy-and-hold SPMO).

## Rules
- **Trend sleeve, 50%.** SSO (2x S&P 500) while SPY's dividend-adjusted price is above its 200-day average, with 1%
  hysteresis (in above +1%, out below -1%); otherwise IEF (7-10 year Treasuries). Read daily at 15:50.
- **Rotation sleeve, 50%.** The 2 strongest of VTI, EFA, EEM, TLT, GLD, DBC, VNQ by 6-month total return at the
  last completed month-end close, 25% each. A pick that does not beat T-bills (SGOV) over those 6 months is held in
  SGOV. Changes trade at the first 15:50 run of the new month.
- **Trading.** Trade only when a target holding is missing, a non-target holding is still held, or L1 drift is
  above 20%. No calendar rebalancing (fewer taxable sales). Whole-share limit orders, at most 0.3% through the touch.
- **Scope.** The strategy manages only its ten tickers plus positive cash. Every other position in the account
  (the existing individual stocks) is ignored. `max_capital` in the config caps what it deploys.

## No wash-sale overlap
Its tickers (SSO IEF VTI EFA EEM TLT GLD DBC VNQ SGOV) share none with the Robinhood strategy (SPY TQQQ QLD QQQ
VIXY BOXX XLU; SPMO until 2026-11-19) or the IRA (SPMO). SPY is read as a signal and never traded here; the code
refuses to run if the account holds a reserved ticker (BOXX dust excepted). SSO and VTI track the S&P 500 x2 and
the total US market: different securities from SPY, generally not "substantially identical", but the IRS has not
ruled on it; a cautious reading avoids harvesting an SSO/VTI loss in a week the Robinhood account buys SPY.

## Evidence (`public-strategy/backtest.py`, pre-registered, Jul 2007 - Nov 2026, adjusted closes, 5bp/side)
| | CAGR | Sharpe | Max DD | Worst year |
|---|---|---|---|---|
| Combined 50/50 | 12.0% | 0.75 | -26.7% | -23.5% (2022) |
| Trend sleeve alone | 12.3% | 0.60 | -46.0% | -37.5% |
| Rotation sleeve alone | 10.6% | 0.72 | -19.9% | -8.3% |
| SPY buy & hold | 10.5% | 0.61 | -55.2% | -36.8% |
2007-2015: 9.8% / 0.61 vs SPY 5.7% / 0.36. 2016-2026: 13.8% / 0.87 vs 14.4% / 0.85.
After federal tax (38.8% short-term, 18.8% long-term, paid yearly): **9.0%** vs SPY buy & hold **9.2%**: in a
taxable account the return ties the index; what it buys is the drawdown (-27% vs -55%; +22% in 2008) and a
0.56 daily correlation to the Robinhood strategy. Behind SPY in 2010, 2015 (-16% vs +1%), 2019, 2022, 2023, 2026.
Differences from the backtest when live: rotation changes trade one session after month-end; whole shares leave a
little cash idle.

## Running it
`public-strategy/public_run.py` does every calculation; RUNBOOK-PUBLIC.md has the steps (10:00 brief, 15:50 trade
run). Go-live needs: capital in the account (it is currently all individual stocks with negative cash), the owner
setting `enabled=true`, and two scheduled tasks in a session that has the Public connector.
