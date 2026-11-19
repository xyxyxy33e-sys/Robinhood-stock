# Public.com taxable account (5OG87042) — trend + rotation strategy

Status: **built, dry run** (`data/public/config.json` `enabled=false`). Owner request 2026-11-19. Separate from the
Robinhood Agentic strategy (STRATEGY.md) and the IRA (buy-and-hold SPMO).

## Rules
- **Trend sleeve, 50%.** SSO (2x S&P 500) while SPY's dividend-adjusted price is above its 200-day average, with 1%
  hysteresis (in above +1%, out below -1%); otherwise IEF (7-10 year Treasuries). Read daily at 15:50.
- **Rotation sleeve, 50%.** The 2 strongest of VTI, EFA, EEM, TLT, GLD, DBC, VNQ by 6-month total return at the
  last completed month-end close, 25% each. A pick that does not beat T-bills (BOXX) over those 6 months is held in
  BOXX. Changes trade at the first 15:50 run of the new month.
- **Trading.** Trade only when a target holding is missing, a non-target holding is still held, or L1 drift is
  above 20%. No calendar rebalancing (fewer taxable sales). Whole-share limit orders, at most 0.3% through the touch.
- **Scope.** The strategy manages only its ten tickers plus positive cash. Every other position in the account
  (the existing individual stocks) is ignored. `max_capital` in the config caps what it deploys.

## No wash-sale overlap
Its tickers (SSO IEF VTI EFA EEM TLT GLD DBC VNQ BOXX) share none with the Robinhood strategy (SPY TQQQ QLD QQQ
VIXY XLU; SPMO until 2026-11-19) or the IRA (SPMO), except **BOXX, the cash fund, shared on purpose** (owner
2026-11-19): BOXX almost never sells at a loss, a washed loss between two taxable accounts is only deferred, and
its return is a capital gain that the owner's capital losses can offset (T-bill interest cannot be, beyond $3,000 a
year). In the backtest the cash slot was used in 14 of 232 months, 6 months at most, about 2% of the account on
average. The 8.5 BOXX shares already in the account (~$1,013) now count as strategy capital. SPY is read as a signal and never traded here; the code
refuses to run if the account holds a reserved ticker. SSO and VTI track the S&P 500 x2 and
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

Dashboard: https://claude.ai/artifact/Ut3LWwtHC9ztXDCviogdZK (five attached CSV files: status, holdings, stats, years, nav; regenerate from `public_run.py` and `backtest.py`).

## Rotation check day: stays on the last session of the month (tested 2026-11-19)

The rotation check was moved 0 to 20 trading days after month-end (`public-strategy/research_notes/rebalance_day.py`,
results in `rebalance_day.txt`). Across the 21 days the combined strategy returned 9.9% to 12.3% a year (mean 11.2%,
Sharpe 0.63 to 0.76). Month-end (12.0%, 0.75) is near the top; mid-month (days 8 to 12) averaged 10.9% and 0.68 and was
not better in either half. The spread between neighbouring days is noise, so the honest expectation is the mean, about
11%, not the month-end 12.0%. No change.

## Rotation check frequency: stays monthly (tested 2026-11-19)

Weekly, two-weekly and daily rotation checks, all with a 126-trading-day lookback
(`public-strategy/research_notes/rebalance_weekly.py`, results in `rebalance_weekly.txt`): 10.9% to 11.4% a year and
Sharpe 0.69 to 0.71 against 11.1% and 0.70 monthly on the same lookback; after tax 8.2% to 8.6% against 8.6%. Weekly
makes 14 to 15 rotation changes a year against about 6. No gain for more than twice the trading. No change.

## Rotation cash rule: unchanged (tested 2026-11-19)

The rotation already goes to the cash slot when a pick fails to beat T-bills over 6 months. Removing the rule, and five
stricter versions (above own 200-day average; beat T-bills by 2 or 5 points; at least 3 or 4 of 7 funds beating
T-bills), are in `public-strategy/research_notes/cash_rule.py` and `cash_rule.txt`. The current rule has the best
return, Sharpe and maximum drawdown of the seven (12.0% / 0.75 / -26.7%); stricter rules hold 6% to 36% cash and return
10.4% to 11.6%. No change.

## Rotation lookback: stays 6 months (tested 2026-11-19)

Lookbacks of 1, 3, 6, 9 and 12 months and six blends (`public-strategy/research_notes/lookback.py`, `lookback.txt`).
Combined strategy: 10.1% to 12.0% a year, Sharpe 0.66 to 0.75; 6 months is joint best (12.0% / 0.75) and no blend beats
it before tax (the 3/6/12 blend is 0.4pp better after tax, within noise). Caution recorded: the rotation half alone
shows a -19.9% maximum drawdown at 6 months but -23% to -38% at every other setting, so the 6-month figure is partly
luck; plan on the rotation half being able to fall 30% or more. No change.
