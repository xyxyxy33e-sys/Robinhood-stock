# Public.com taxable account (5OG87042) — trend + rotation strategy

Status: **LIVE since 2026-11-20** with $15,000 (`data/public/config.json` `enabled=true`, `max_capital` 15000). Owner request 2026-11-19. Separate from the
Robinhood Agentic strategy (STRATEGY.md) and the IRA (buy-and-hold SPMO).

## Rules
- **Trend sleeve, 50%.** SSO (2x S&P 500) while SPY's dividend-adjusted price is above its 200-day average, with 1%
  hysteresis (in above +1%, out below -1%); otherwise IEF (7-10 year Treasuries). Read daily at 15:50.
  **Fallback filter (owner 2026-11-19):** IEF is held only if its 6-month total return at the last completed
  month-end beats T-bills, the same test the rotation uses; otherwise the trend half sits in BOXX.
  **VIX-panic leg (owner 2026-11-20):** while the trend is off and the VIX latch is on (a close at or above 30 turns it
  on, a close below 25 off), 25% of the trend half is 1x S&P: SSO 6.25% of the strategy, fallback 37.5%, BOXX 6.25%.
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
| Combined 50/50 | 12.3% | 0.77 | -22.8% | -16.9% (2022) |
| Trend sleeve alone | 12.8% | 0.63 | -37.9% | -26.3% |
| Rotation sleeve alone | 10.6% | 0.72 | -19.9% | -8.3% |
| SPY buy & hold | 10.5% | 0.61 | -55.2% | -36.8% |
2007-2015: 9.7% / 0.61 vs SPY 5.7% / 0.36. 2016-2026: 14.4% / 0.91 vs 14.4% / 0.85.
These figures include the fallback filter and the VIX-panic leg (filter alone: 12.0% / 0.75 / -22.9%, 2008 +17%). Before it (always IEF): 12.0% / 0.75 / -26.7%, worst year -23.5%, 2008 +22%;
the research sections below that say "current" were run before the filter.
After federal tax (38.8% short-term, 18.8% long-term, paid yearly): **9.3%** vs SPY buy & hold **9.2%**: in a
taxable account the return ties the index; what it buys is the drawdown (-23% vs -55%; +15% in 2008) and a
0.58 daily correlation to the Robinhood strategy. Behind SPY in 2010, 2015 (-16% vs +1%), 2019, 2022, 2023, 2026.
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

## Rotation scoring system: not adopted, close call (tested 2026-11-19)

Owner's idea: score each fund on several lookbacks with 6 months weighted most. Seven weightings, each as a weighted
return over T-bills and as a weighted rank (`public-strategy/research_notes/score.py`, `score.txt`). All 14 land at
11.4% to 12.4% a year and Sharpe 0.71 to 0.76 against 12.0% / 0.75 for 6 months alone. The return-weighted scores that
include 12 months are 0.3 to 0.7pp better after tax (9.3% to 9.7% against 9.0%) and 2pp better on maximum drawdown,
but all are worse in 2007-2015 (9.0% to 9.4% against 9.8%) and the rank versions show no gain, so the both-halves bar
is not met. Kept 6 months. If revisited, the candidate is 3/6/12 = 25/50/25 (12.3% / 0.76 / -24.8%, 9.7% after tax).

## Structure tests (2026-11-19): fallback filter is the one candidate; band, middle step, top-N, split unchanged

Scripts and outputs in `public-strategy/research_notes/` (`trend12`, `ideas34`, `band_long`). Current = 12.0% / 0.75 / -26.7%.
- **Bond fallback filter (ADOPTED by the owner 2026-11-19).** Trend half holds IEF below the 200-day line only if IEF's
  6-month return beats T-bills, else the cash slot: 12.3% / 0.77 / -22.8%, both halves no worse (9.9% and 14.2% against
  9.8% and 13.8%), 2022 -18.4% against -23.5%, 2023 +7.5% against +9.5%. Passes the bars, but the gain is one episode (2022).
  That test used a 126-trading-day lookback. As built (month-end to month-end, the rotation's own dates) the return is
  unchanged at 12.0% / 0.75, 2008 is +17% instead of +22%, and the maximum drawdown is -22.9%: it is drawdown
  insurance, not extra return.
- **Middle 1x step: rejected.** Eleven versions: 11.1% to 12.3%, more than twice the trend trades, after tax lower in all but one.
- **Wider band: not adopted.** 1.5% to 4% bands show 13.1% to 13.7% in 2007-2026, but on 2x S&P / T-bills for
  1951-2007, untouched by this design, 1% gives 16.8% and 2.5% to 3% give 16.3% to 16.6%. The gain is a 2010/2015/2023
  artifact. A 3% band does switch 1.0 times a year against 2.5 for the same 75-year return, so it is a fair choice on
  trading and tax grounds only.
- **Top 3 (or 1, 4) instead of top 2: rejected.** 10.3% to 11.6% against 12.0%; combined maximum drawdown no better.
- **Split: stays 50/50.** 30/70 to 70/30 trade return for drawdown in a straight line (11.6% / -19.5% to 12.3% / -35.1%).

## 50-day line in the trend half: rejected (tested 2026-11-19)

Seven rules using the S&P's 50-day line, as the Robinhood strategy does on QQQ (`research_notes/fifty.py`,
`fifty_long.py`). Rules that cut 2x to 1x or to bonds below the 50-day line: 9.9% to 11.2% against 12.0% in 2007-2026,
and 11.3% to 14.4% against 16.8% on 2x S&P for 1951-2007, with two to three times the trades. The one rule ahead in
2007-2026 (1x when below the 200-day but above the 50-day: 13.0%) is level on 1951-2007 (16.8% against 16.8%) with a
deeper drawdown (-47.5% against -37.1%). Golden cross: fewer trades but -59% drawdown. No change.

## VIX pieces from the Robinhood strategy (tested 2026-11-19): sleeve rejected, panic leg is a candidate

`public-strategy/research_notes/vix.py`, `panic_long.py`. Both act only while the trend half is off.
- **VIX sleeve (VIXY 20-50% or VIXM 75% of the fallback, live latch, S&P vol threshold 10-20%): rejected.** 2011-2026:
  11.1% to 11.7% against 11.7%, Sharpe 0.73 to 0.76 against 0.77; on 0.5% to 1.5% of days; cost up to 6.5 points in 2015.
  It would also need a VIX fund the Robinhood account does not trade.
- **VIX-panic leg (VIX closes >= 30 on, < 25 off; that share of the fallback in 1x S&P, held as SSO at half weight):
  ADOPTED at 25% by the owner 2026-11-20.** 2007-2026 at 25% / 50%: 12.3% / 0.77 / -22.8% and 12.6% / 0.78 / -23.0% against 12.0% /
  0.75 / -22.9%; both halves better; after tax 9.3% / 9.4% against 9.0%. On 2x S&P / T-bills for 1990-2007, untouched:
  13.4% and 14.0% against 12.8%, Sharpe 0.48 and 0.50 against 0.46, drawdown no worse; thresholds 25/20, 35/28 and 40/30
  also ahead. Cost: it buys into falling markets, so 2008 is +14.8% / +12.2% against +17.1%, and at 100% the drawdown
  grows to -28%.

## VIX as a factor in the rotation score: rejected (tested 2026-11-20)

Thirteen versions on the month-end VIX (`research_notes/vixscore.py`): barring the four stock funds when VIX is high or
above VIX3M (10.9% to 11.9% against 12.0%), tilting scores toward bonds and gold or toward stocks with VIX (10.7% to
12.0%), and switching the lookback on VIX. Only "3-month lookback when VIX is 20/25 or more" is ahead (12.4% to 12.7%,
Sharpe 0.76 to 0.78), and it gets there by giving up the 2008 gain (+6% to +8% against +17%) and taking the rotation
half's drawdown from -20% to -34%. No change.

## Deep-drawdown study (2026-11-20): no free fix; two dials offered to the owner

`research_notes/dd.py`, `dd_long.py`. Current: 12.3% / 0.77 / -22.8%, 11% of days 15% or more below the high.
- **Anatomy.** The five deepest drops (-19.5% to -22.8%: 2018 Q4, 2010, 2022, 2015, 2020) all began with SSO at 50%;
  the trend half lost 16 to 24 points in each, the rotation half 1 to 8. The 200-day rule cannot react to a fast fall
  from above the line.
- **Rejected.** Account-level brake (half size at -10/-12/-15%): 9.5% to 10.8%, drawdown no better (it sells after the
  fall and misses the rebound). Rotation stop-loss (-8/-12% from the pick): return and drawdown both worse.
- **Dials (cost return for depth, Sharpe unchanged).** SSO volatility target 30% (SSO share cut in quarter steps when
  S&P vol x2 is above 30%): 12.2% / 0.80 / -20.0%, 4% of days below -15%, after tax 8.7% against 9.3%; on the 75-year
  2x S&P rule it costs about 1 point a year on the trend half (14.5% against 15.5%) for -31.9% against -39.3%, Sharpe
  0.60 both. Split 40/60: 12.1% / 0.78 / -21.4%, after tax 8.8%. Both together: 12.0% / 0.81 / -18.8%, after tax 8.3%.
  1.5x instead of 2x: 11.0% / -19.3%.
- **October 1987.** The 200-day rule had already left the S&P before the 19 October crash (0% that day); the month
  still cost the 2x rule -23% on the way out.

## The daily 15:50 check stays (tested 2026-11-20)

Checking the trend rule and the VIX latch less often (`research_notes/freq.py`, `freq_long.py`). On 2007-2026 a weekly
or monthly check looks better (13.0% to 14.0% against 12.3%), the same whipsaw artifact as the wider band. On the
2x S&P rule for 1951-2007 it is worse (15.1% to 16.2% against 16.8%) and the worst drawdown goes from -37% to about
-60%: in October 1987 the daily rule left the S&P before the 19th and lost -23% for the month; checking even every
second day could still hold 2x through the crash and lose -55%. With a 2x fund the daily check is the protection.

## Rebalancing only when the trend half trades: no gain (tested 2026-11-20)

`research_notes/rebal_sso.py`, before tax. Resetting the two halves to 50/50 only when the trend half trades (4.7 times
a year against 10.9): 12.4% / 0.75 / -23.7% against 12.3% / 0.77 / -22.8%; the trend half drifts up to 64% of the
strategy. Reset only when SSO is bought: 12.4% / 0.75 / -24.0%. Once a year: 12.4% / 0.77 / -23.0%. Never: 11.8% / 0.74.
Changing the rotation picks only on days the trend half trades: 9.5% / 0.62 / -41.4% (picks go stale for a year or more).
No change.

## Every signal once a week: rejected (tested 2026-11-20)

`research_notes/weekly_all.py`. Trend, VIX latch, IEF test and rotation all read on one weekday: 11.7% to 13.2% a year
(average 12.4% against 12.3%), Sharpe 0.72 to 0.80, maximum drawdown -23.2% to -35.4% depending on the weekday, 16 to 17
trading days a year against 11. The result is a draw on return with a drawdown set by which weekday is chosen, and it
keeps the 1987 exposure found in the check-frequency test. No change.

## Owner decision 2026-11-20: rotation stays monthly, full reset on every trade

After the weekly and two-weekly tests the owner confirmed: rotation is read at month-end only, and whenever anything
trades the whole strategy is brought back to its targets (50% trend / 50% rotation). This is what `public_run.py`
already does: on a trade day it sizes every holding to target, not only the one that changed.

## Cash in the rotation half while the S&P is below its 200-day line: rejected (tested 2026-11-20)

`research_notes/downcash.py`. Current 12.3% / 0.77 / -22.8%. Rotation half all to cash: 10.4% / 0.69 / -25.1% (2008
+2.7% against +14.8%: it sells the Treasuries and gold that carried that year). Half to cash: 11.4% / 0.73. Stock funds
only to cash or swapped for bonds/gold/commodities: 11.1% to 11.2% / -25%. Only when the S&P is more than 5% or 10%
below the line: 12.0% to 12.5%, Sharpe 0.75 to 0.78, drawdown -22% to -23%, 2008 +6% to +13%: no better than noise.
The deep drawdowns start with SSO above the line, where none of these rules act. No change.

## Account state 2026-11-20: all cash

The owner sold most of the individual stocks during the morning and then instructed the agent to sell the rest: 46
positions (about $19,190) sold with market orders at about 11:15 ET, all filled. The account holds no positions and
$65,362.52 cash. `enabled` is still false: with no `max_capital` set, enabling it would deploy the whole cash balance.

## Account state 2026-11-20, 11:33 ET: autopilot basket plus $15,000 for this strategy

Minutes after the liquidation, 93 dollar-amount market buys (11:17-11:23 ET, $49,999.89) put 77 individual stocks and
14.97 BOXX in the account. Owner 2026-11-20: that $50,000 is managed by Public's autopilot and trades on its own.
Account: $15,362.60 cash, $49,730.85 in 78 positions. The owner set this strategy's capital at $15,000
(`max_capital`) and told the agent to go live: `enabled=true`, first trade at the 15:50 run on 2026-11-20, with two
weekday scheduled tasks in the Public strategy chat (about 10:00 brief, 15:50 trade run).

Because the autopilot also holds BOXX, the account's positions cannot tell the two apart. `public_run.py` now counts
only its own ledger (`data/public/ledger.json`: shares it bought and its cash, starting at `max_capital`), updated
with `public_run.py record` after every fill. It refuses to run if the account holds fewer shares of a ticker than the
ledger says. Dividends on strategy holdings land in account cash and are not added to the ledger. The Scope rule above
("ten tickers plus positive cash") is replaced by the ledger.

## VIX latch keeps the 15:50 reading (owner 2026-11-20)

The 15:50 run treats the live VIX as that day's close. Later runs now replay that same reading for the day (from
`data/public/runs/<date>.json`) instead of the official close, so a 30.1 at 15:50 followed by a 29.8 close no longer
buys the panic leg one day and sells it the next. Thresholds are unchanged (on at 30, off below 25). The run files are
therefore part of the strategy's state: always commit them.
