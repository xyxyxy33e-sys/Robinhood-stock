# Public.com taxable account (5OG87042) — trend + rotation strategy

Status: **LIVE since 2026-11-20** with $15,000, 2% trend band, SSO volatility target 30% (`data/public/config.json` `enabled=true`, `max_capital` 15000). Owner request 2026-11-19. Separate from the
Robinhood Agentic strategy (STRATEGY.md) and the IRA (buy-and-hold SPMO).

## Rules
- **Trend sleeve, 50%.** SSO (2x S&P 500) while SPY's dividend-adjusted price is above its 200-day average, with 2%
  hysteresis (in above +2%, out below -2%; 1% until 2026-11-20); otherwise IEF (7-10 year Treasuries). Read daily at 15:50.
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

## Tax lots and realized gains (owner 2026-11-20)

Sells name their tax lots, highest cost first, from all the account's lots of that ticker, the autopilot's included
(owner: "you can sell autopilot's lot, its fine"); the number of shares sold still comes from the strategy's ledger.
Public's lot data is as of the previous night and allows at most 8 lots per order; when the lots do not cover a sale or
the broker refuses the instruction, the sell goes without one. `record` appends every sale to
`data/public/realized.csv` (proceeds, cost of the lots named, gain, short or long term; a sale without a lot
instruction is costed at the strategy's average price and marked `average`). The dashboard has a tax section fed by
`tax.csv` (`public_run.py dash`): realized gain or loss per ETF for the tax year.

## Weekly review (owner 2026-11-20)

Every Friday after the close a scheduled task runs `public_run.py review`: the strategy's value against SPY for the
week and since the $15,000 start, the week's orders, realized gains, holdings against targets and the signals, with one
push and a dashboard refresh. Values are kept in `data/public/weekly.csv`. The first review (2026-11-20) is the baseline.

## Owner decisions 2026-11-20: rotation score stays 6 months; SSO volatility target 30% ADOPTED

- **Rotation score:** 6 months alone. The 3/6/12 blend is not adopted.
- **SSO volatility target 30%:** while the trend is on, the SSO share of the trend half is min(1, 30% / (2 x S&P vol)),
  rounded to the nearest quarter and never below a quarter; S&P vol is the larger of the 10- and 30-session annualized
  volatility; the rest of the trend half sits in BOXX. A change of step trades and resets everything to target. The
  panic-leg SSO (trend off) is not scaled. `public_run.py` (`VOL_TARGET`, `sso_scale`) and `backtest.py` both apply it.
- **Backtest rebuilt.** `backtest.py` no longer needs the private price harness: it downloads Yahoo adjusted closes and
  uses the 13-week T-bill yield for cash. On this data every return is about 0.3 points a year lower than the figures in
  "Evidence" above (SPY 10.3% against 10.5%), so compare like with like, Jul 2007 - 19 Nov 2026:

| | CAGR | Sharpe | Max DD | Worst year | After tax | 2007-2015 | 2016-2026 |
|---|---|---|---|---|---|---|---|
| Without the vol target | 12.0% | 0.75 | -22.8% | -16.9% | 8.9% | 9.7% / 0.61 | 13.9% / 0.88 |
| With the 30% vol target (live) | 12.0% | 0.79 | -20.0% | -14.5% | 8.5% | 10.3% / 0.67 | 13.3% / 0.90 |
| SPY buy & hold | 10.3% | 0.60 | -55.2% | -36.8% | 9.0% | 5.7% / 0.36 | 14.1% / 0.83 |

  Same return before tax, higher Sharpe in both halves, 2.8 points less drawdown; it costs about 0.4 points a year after
  tax (more short-term trades), which leaves the strategy about half a point behind SPY after tax. This matches the
  earlier study (12.2% / 0.80 / -20.0%, 8.7% after tax against 9.3%). The dashboard's backtest figures are these.

## Search for something better (2026-11-20): nothing structural; a 2% band is the one candidate

Owner: "find something better than this". `research_notes/better.py` (results `better.txt`) runs eleven designs, named
before any was run, through one engine with the same costs and taxes; `better_long.py` (`better_long.txt`) checks the
band on 1960-2007. The engine also taxes fund distributions (18.8% stock-fund dividends, 38.8% bond and REIT income),
which the earlier after-tax figures left out: **the live strategy is 8.0% a year after tax, not 8.5%, against 9.0% for
SPY bought and held.** Jul 2007 - 19 Nov 2026:

| | CAGR | Sharpe | Max DD | After tax | 2007-15 pre / after | 2016-26 pre / after |
|---|---|---|---|---|---|---|
| Live | 11.9% | 0.79 | -20.0% | 8.0% | 10.1 / 6.3 | 13.5 / 9.2 |
| Live, 2% band | 12.8% | 0.83 | -19.0% | 8.8% | 12.4 / 8.5 | 13.3 / 9.0 |
| Live, 3% band | 12.9% | 0.83 | -20.0% | 9.0% | 12.5 / 8.5 | 13.4 / 9.5 |
| 50% VTI held + 50% live | 11.1% | 0.76 | -28.4% | 8.5% | 8.2 / 5.5 | 13.6 / 10.7 |
| Live trend half + 7-fund trend | 9.4% | 0.73 | -18.9% | 7.0% | 6.7 / 4.6 | 11.7 / 8.8 |
| Trend rule unlevered (VTI) | 7.8% | 0.66 | -22.5% | 5.7% | | |
| Dual momentum (VTI/EFA/IEF) | 6.0% | 0.44 | -35.0% | 3.9% | | |
| 7 funds, each above its 10-month average | 5.7% | 0.72 | -12.3% | 4.2% | | |
| Static VTI 45 / EFA 15 / IEF 25 / GLD 15 | 8.1% | 0.73 | -27.7% | 6.8% | | |
| SPY bought and held | 10.3% | 0.60 | -55.2% | 9.0% | 5.7 / 4.4 | 14.2 / 12.3 |

- **No different design is better.** Every structural alternative returns less, and none beats SPY after tax.
- **2% band (candidate, not adopted).** Trend half alone on 1960-2007, with the vol target: 14.3% / 0.79 / -34.6%, 11.2%
  after tax, against 13.6% / 0.77 / -37.9%, 10.8% for 1%; better in 1960-1983 and 1984-2007, before and after tax, with
  1.2 switches a year against 2.2. On 2007-2026 it is ahead in the first half and 0.2 points behind in the second. The
  bands are not monotonic (3% is worse than 2% and 4% on 1960-2007; 4% is best), so the return gain is within noise;
  what is solid is about half the switching. The earlier "wider band" entry tested 2.5-3%, not 2%.
- **In a taxable account the strategy costs about 1 point a year against SPY** for a worst drop of -20% instead of -55%.

## Nasdaq-100 tilt (tested 2026-11-20, owner: "lean more towards qqq strategy"): era-dependent; owner decision pending

`research_notes/nasdaq.py`, `nasdaq.txt`; same engine and taxes as `better.py`. QQQ/QLD prices stand in for the fund.
Jul 2007 - 19 Nov 2026, whole strategy:

| | CAGR | Sharpe | Max DD | After tax | 2007-15 pre / after | 2016-26 pre / after |
|---|---|---|---|---|---|---|
| Live (SSO on SPY's signal) | 11.9% | 0.79 | -19.8% | 8.0% | 10.1 / 6.3 | 13.5 / 9.2 |
| Trend half = QLD on QQQ's signal and vol | 14.9% | 0.90 | -19.0% | 10.3% | 12.7 / 8.8 | 16.7 / 11.6 |
| Trend half = 25% SSO + 25% QLD, own signals | 13.5% | 0.86 | -19.2% | 9.2% | 11.6 / 7.7 | 15.1 / 10.5 |
| QLD switched by SPY's signal | 15.8% | 0.89 | -24.7% | 11.0% | | |
| QQQ (1x) added to the rotation funds | 11.4% | 0.73 | -22.0% | 7.8% | | |
| Trend half = QQQ unlevered on its own signal | 11.7% | 0.89 | -16.7% | 8.1% | | |
| QQQ held / SPY held | 15.3% / 10.3% | 0.75 / 0.60 | -53.4% / -55.2% | 14.0% / 9.0% | | |

Trend half alone on Dec 1999 - Jun 2007 (2x funds built from the index funds; the Nasdaq-100 fell 83%): SSO/SPY 6.4% a
year, -22.2%; QLD/QQQ 1.8%, -35.1%; half each 4.5%, -25.0%; QLD on SPY's signal 2.8%, -53.3%. In the bust itself the
two were alike (-7.0% and -5.9% a year to 2002); the Nasdaq version fell behind in 2003-2007 (7.0% against 16.2%).

Reading: the Nasdaq version wins in both halves of 2007-2026 and loses on the one earlier period available, so it is a
bet that the Nasdaq keeps leading, not a rule improvement. It also needs QLD (no other 2x Nasdaq-100 fund is known to
the agent), which the Robinhood strategy trades: that ends the no-shared-ticker rule for this account (wash sales
between the two taxable accounts defer losses and must be tracked by hand), and both accounts would then hold levered
Nasdaq at the same times. Not applied; the live rules are unchanged.

## Structural port of the Robinhood (QQQ) strategy onto non-overlapping funds (tested 2026-11-20): owner decision pending

Owner: lean towards the QQQ strategy "structurally, no overlapping etf". `research_notes/regime_port.py`,
`regime_port.txt`. Ported from `paper-track/state.py` (read only): the six-state 50/200 classifier, the 20/100 fast
re-entry, rows A 40% core / 60% 3x, B 50% core / 50% cash, C core, D 2x (cash under 2% above the 200-day), E and F cash,
extension trim v2, the 20% vol target, trade on a regime change or 5% drift. Not ported: VIXM sleeve, breadth gate,
D ladder, deep-E, VIX-panic. Funds: VTI for SPMO, UPRO for TQQQ, SSO for QLD, BOXX. **The port is faithful:** run on
the original's own funds for Nov 2015 - Nov 2026 it gives 35.4% / 1.58 / -19.2% (A 50/50) against about 37% / 1.48 /
-18.6% documented for that strategy.

| Jul 2007 - 19 Nov 2026 | CAGR | Sharpe | Max DD | After tax | 2007-15 pre / after | 2016-26 pre / after | Turnover a year |
|---|---|---|---|---|---|---|---|
| Live | 11.9% | 0.79 | -20.0% | 8.0% | 10.1 / 6.3 | 13.5 / 9.2 | 7x |
| Port, signals on SPY | 15.9% | 0.79 | -48.8% | 10.6% | 8.4 / 4.6 | 22.0 / 14.9 | 18x |
| Port, signals on QQQ (read only), S&P funds | 18.1% | 0.98 | -36.1% | 11.4% | 8.5 / 5.0 | 26.7 / 16.7 | 16x |
| Half live + half port (QQQ signals) | 15.8% | 1.01 | -21.8% | 9.9% | 9.3 / 5.6 | 21.8 / 13.6 | 11x |
| SPY held | 10.3% | 0.60 | -55.2% | 9.0% | 5.7 / 4.4 | 14.2 / 12.3 | 0 |

Earlier history, S&P 500 funds built from the index (no rotation funds exist, so the comparison is the live trend half):
- 1960 - Jun 2007, signals on the S&P: port 13.2% / 0.78 / -59.9%, 8.5% after tax; live trend half 13.6% / 0.77 /
  -38.0%, 10.8% after tax; S&P held 10.3%, 9.8% after tax. 2000-2002: port -42%, trend half -22%.
- 1972 - Jun 2007, signals on the Nasdaq Composite: port 15.4% / 0.94 / -43.3%, 9.8% after tax; trend half 14.0% /
  0.74 / -37.8%, 11.2% after tax; S&P held 11.1%, 10.4% after tax. 2000-2002: port -8%, trend half -22%.
- Dec 1999 - Jun 2007, real QQQ as signal: port 10.0% / 0.78 / -14.6%, 6.4% after tax; trend half 5.7%, 4.0% after tax.

Reading: on S&P signals the structure is worse than what is live (deeper falls, lower after-tax return on 1960-2007).
On Nasdaq signals it has the better Sharpe before tax in every period tested, but it turns the account over 13 to 16
times a year, so after tax it is ahead of the live strategy only since 2016 and behind on 1972-2007, and its worst fall
is -36% to -43% against -20%. Both accounts would then act on the same QQQ signals. Not applied; live rules unchanged.

## Berkshire and a defensive fund (tested 2026-11-20): only a held Berkshire slice helps, a little; owner decision pending

Owner: "add Berkshire as a position, and something defensive like XLU". `research_notes/defensive.py`,
`defensive.txt`. XLU is reserved for the Robinhood strategy; its prices stand in for a utilities fund (VPU would be the
one traded) and XLP for staples. Three roles, Jul 2007 - 19 Nov 2026 (live: 11.9% / 0.79 / -20.0%, 8.0% after tax, 2008 +15%):
- **Added to the rotation list** (top 2 of 8-10): 11.1% to 11.8%, Sharpe 0.74 to 0.78, drawdown -21% to -24%, after
  tax 7.6% to 8.1%. No gain from any of the five combinations.
- **Held by the trend half while the S&P trend is off**, in place of IEF/BOXX: 11.9% to 12.5%, drawdown -23%, and 2008
  goes from +15% to -1% (utilities), +11% (staples), +8% (Berkshire): defensive stocks still fall in a bear market.
  On 2000 - Jun 2007 utilities helped (10.4% against 7.6% for T-bills) and Berkshire deepened the drawdown. Rejected.
- **A slice bought once and held**, the rest on the live rules: 20% Berkshire 11.8% / 0.82 / -18.9%, 8.6% after tax
  (both halves no worse after tax; 2008 +3%); 30% Berkshire 11.7% / 0.82 / -20.2%, 8.8% after tax (2008 -2%); 20% plain
  VTI, as a reference, 11.6% / 0.79 / -19.7%, 8.2% after tax, so a third of the Berkshire gain is only the holding;
  20% utilities 11.3% / 0.79 / -17.7%, 7.7% after tax. Berkshire pays no dividend and a held slice is never sold, so
  the gain is mostly tax; Berkshire itself returned 11.3% a year with a -54% fall, about the S&P's.
Not applied; live rules unchanged.

## Owner decisions 2026-11-20 (afternoon): 2% band ADOPTED; no Nasdaq tilt, no structural port, no Berkshire or utilities

After the four studies above the owner said: "leave it as is, add the 2% band". `HYST` in `public_run.py` and `BAND` in
`backtest.py` are 0.02. The trend was off at the change (SPY 3.8% below its 200-day), so nothing traded on it; it turns
back on above +2%. Live rules now, Jul 2007 - 19 Nov 2026 (`backtest.py`): **12.9% / 0.84 / -19.0%**, worst year
-13.5%; 2007-2015 12.4%, 2016-2026 13.1%; after tax with distributions taxed 8.8% against 9.0% for SPY held
(`backtest.py`'s own after-tax line, 9.2%, leaves distributions out). The Nasdaq tilt, the regime port and the
Berkshire / defensive ideas are not adopted. The agent's advice, accepted: no further rule changes for three to six
months unless something breaks.

## VIX-leg thresholds 25/20 and 30/20 against 30/25 (tested 2026-11-20): no change

`research_notes/vix_levels.py`, `vix_levels.txt`; live rules otherwise. A VIX close of 30 or more is 8% of days since
1990; the 30/25 latch starts about once a year and the leg is active on about 10% of days.
- Jul 2007 - 19 Nov 2026, whole strategy: 30/25 12.8% / 0.83 / -19.0%, 8.8% after tax; 25/20 12.7% / 0.83 / -19.2%,
  9.0%; 30/20 12.9% / 0.84 / -19.0%, 9.1%; 35/28 12.8% / 0.83 / -18.6%, 8.6%; no leg 12.5% / 0.81 / -18.6%, 8.3%.
- 1990 - Jun 2007, trend half alone: 30/25 13.1% / 0.70 / -33.3%, 10.8% after tax; 25/20 12.7% / 0.68 / -36.0%, 10.6%;
  30/20 12.6% / 0.68 / -36.8%, 10.5%; 35/28 13.2% / 0.70 / -34.3%, 10.9%; no leg 12.7% / 0.68 / -33.8%, 10.4%.
The lower exits are 0.1 to 0.3 points ahead after tax on the recent period and 0.2 to 0.3 behind, with a deeper
drawdown, on the earlier one: no difference beyond noise. 30/25 kept.

## Buffer on the SSO volatility-target steps (tested 2026-11-20): less trading, same result; owner decision pending

The step flickers when volatility sits on a rounding boundary (January 2015: eight flips between full and three-quarter
size in a month). `research_notes/vt_buffer.py`, `vt_buffer.txt`: keep the current step until 30% / (2 x vol) is more
than a buffer past the boundary. Whole strategy, Jul 2007 - 19 Nov 2026: live 12.8% / 0.83 / -19.0%, 8.8% after tax,
10.8 size changes and 19.9 trade days a year; buffer 0.025 12.8% / 0.83 / -19.3%, 8.8%, 7.7 and 16.9; buffer 0.05
12.7% / 0.83 / -20.6%, 8.8%, 6.5 and 15.8; buffering only the step back up (0.05, 0.10) 12.5% to 12.7%, 8.6% to 8.7%.
Trend half alone, 1960 - Jun 2007: live 14.3% / 0.79 / -34.6%, 11.2% after tax, 5.8 size changes a year; buffer 0.025
14.1% / 0.78 / -34.5%, 11.2%, 3.8; buffer 0.05 14.0%, 11.2%, 2.9. No effect on return or drawdown beyond noise; a
0.025 buffer removes about a third of the size changes. Not applied.

## Owner decision 2026-11-20: 0.025 buffer on the vol-target steps ADOPTED

"add the small buffer". `VT_BUFFER = 0.025` in `public_run.py` and `backtest.py`: a step of the SSO volatility target
moves down only when 30% / (2 x vol) is more than 0.025 below the boundary under the current step, and up only when
it is more than 0.025 above the boundary of the higher step. The live script replays the step from the price history
and takes yesterday's step from yesterday's run file when there is one; it matches the backtest's step on all of the
last 250 sessions. Live rules now, Jul 2007 - 19 Nov 2026: 12.9% / 0.84 / -19.3%, worst year -13.8%, 8.8% after tax
with distributions taxed (SPY 9.0%). The trend was off at the change, so nothing traded on it.

## Holding 1x in place of SSO at certain times (tested 2026-11-20): rejected

Owner: "consider times hold 1x?". `research_notes/one_x.py`, `one_x.txt`; live rules otherwise. (A middle 1x step by
distance from the 200-day and a 1.5x fund were already logged as rejected.) Whole strategy Jul 2007 - 19 Nov 2026,
live 12.8% / 0.83 / -19.3%, 8.8% after tax; trend half alone 1960 - Jun 2007, live 14.1% / 0.78 / -34.5%, 11.2%:
- Same exposure with less borrowing (VTI where the vol target has SSO at half size, half and half at three-quarters):
  12.7%, 8.2% after tax; 14.0%, 10.4%. The swaps between the two funds cost more in tax than the borrowing saved.
- VTI while T-bills yield more than 3 / 4 / 5%: 12.3% to 12.5%, 8.4% to 8.7% after tax; 11.9% to 13.1%, 9.4% to 9.9%
  on 1960-2007, where rates were above 4% on 62% of days. Sharpe a little higher, return lower in both periods.
- VTI while S&P volatility is above 18 / 22%: 12.2% to 12.5%, 7.5% to 8.1%; 12.9% to 13.8%, 9.3% to 10.6%.
- VTI always (no leverage): 10.2% / 0.86 / -16.3%, 6.7% after tax; 11.2% / 1.06 / -19.1%, 9.0%.
Every version is less return for less risk; none is ahead after tax in either period. No change.

## 1x during a dip and while recovering from one (tested 2026-11-20): rejected

Owner: "what about during a dip and when recovering from a dip". `research_notes/dip_1x.py`, `dip_1x.txt`; 1x tried
as VTI and as SSO at half weight. Live: 12.8% / 0.83 / -19.3%, 8.8% after tax (2007-2026); trend half 14.1% / 0.78 /
-34.5%, 11.2% (1960-2007).
- **During a dip** (trend on, SPY more than 5% or 8% below its 252-session high): 12.1% to 12.4%, 7.5% to 8.4% after
  tax, drawdown -20% to -21%; 1960-2007 12.6% to 14.0%, 8.8% to 11.0%.
- **While recovering** (first 20 or 60 sessions after the trend turns back on, or until a new 252-session high):
  11.8% to 12.4%, 7.8% to 8.5% after tax, drawdown -18%; 1960-2007 13.1% to 13.7%, 10.1% to 10.9%; 60 sessions cut the
  1960-2007 drawdown to -26.6% (the 1987 re-entry) for 0.4 points of return.
- Both together: 11.5% to 11.7%, 7.1% to 7.9%; 11.9% to 12.4%, 8.3% to 9.6%.
All twelve versions return less before and after tax in both periods. No change.
