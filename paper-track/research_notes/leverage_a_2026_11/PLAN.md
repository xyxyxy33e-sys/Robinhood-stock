# How much leverage should state A carry? Plan (2026-11-17, written before any arm was run)

Research only; nothing adopted, no live file touched. Engine: `paper-track/harness_live.py` (live design: 2.0x cap, VIXY 35% sleeve
incl. the proxy panel from 2011, D gate on the day's high "L1"), numpy/pandas only. Run: `run.py` -> `run.log`; write-up `README.md`.

## Question
A study today found drops out of calm (prior-day VIX < 20, QQQ down >= 3%) are ~57% of the loss on -2% days while the book is leveraged
(A / ungated D), and nothing predicts them. The only levers on that exposure: how much leverage state A carries (SPMO/TQQQ split, live 40/60 =
2.2x before vol target and cap) and the 2.0x gross cap. Map the trade-off on the CURRENT live design. Known history (STRATEGY.md "A-row ratio
study", 40/60 chosen; A 25/75 and 20/80 live briefly) is NOT re-litigated: the A split was chosen on data that overlaps these windows
(real ETFs 2015-, proxy 2001-), so a split that "wins" here is not an out-of-sample finding.

## Windows (all end at the latest session, 2026-11-16)
real = real ETFs, returns from 2015-11-03; proxy01 = proxy panel from 2001-01-03; proxy10 = proxy panel from 2010-01-05.
Sleeve on the proxy runs from 2011-01-04 (first VIXY print), off before (so proxy10 has one year without it). Default highs: complete
(file + AlphaVantage full-day QQQ highs 2026-09-08..11-10 + live 15:50 highs 11-11..); sensitivity block reruns with the recorded-reference
highs (file only, 50 late sessions read the close) and with L1 off.

## Arms (everything else at live values)
1. A split SPMO/TQQQ: 100/0, 80/20, 60/40, 50/50, 40/60 (LIVE), 30/70, 20/80. Also A as SPMO/QLD 50/50 and 0/100 QLD (same $ weights, TQQQ weight moved to QLD).
2. Gross cap (all states): 1.5, 1.75, 2.0 (LIVE), 2.25, none.
3. A-only cap: A capped at 1.5 / 1.75, D keeps 2.0.
4. Joint grid: A split {60/40, 50/50, 40/60} x cap {1.75, 2.0}.
5. Fairness control: a plain de-lever of the whole live book matched to each lower-leverage arm's average gross exposure on each window
   (average over sessions of the target equity-like gross: SPMO 1x + TQQQ 3x + QLD 2x + XLU 1x + QQQ legs 1x, VIXY and cash excluded).
   Primary = flat scale on the four risky legs after vol target and cap (bisection on avg gross); secondary = lowered vol target.
   Arms with MORE average gross than live get no matched control.

## Metrics per arm per window
CAGR, Sharpe (mean*252/vol, as harness.stats), max DD, annual vol, avg gross, worst day, worst 5 sessions and worst 20 sessions (rolling compounded
return), share of time in A, avg gross while in A, trades/yr and one-way annual turnover (sum of |target-held| at rebalances / years).
Calm-crack days = days.csv rows with p_vix < 20 and QQQ ret <= -3% (42 days since 1999; 20 in real, 22 since 2010): mean and total (sum of daily
book returns) loss per arm, and the share of the arm's summed return on all QQQ <= -2% days that falls on the crack days.
Cost per point: (CAGR_live - CAGR_arm) / (DD points avoided), same for worst-20-day; same ratio for the matched de-lever; "arm beats matched"
= lower CAGR cost per point (or higher CAGR / shallower DD at equal gross).
Stress: calendar 2022, Feb-Mar 2020, 2026-11-05 day, 2026-10-30..11-05 five sessions.
Robustness (frontier points = lower-leverage arms): Sharpe difference vs live on halves, ex-2020, and a 20-session block bootstrap (2,000 paths,
paired) giving median difference and P(diff <= 0); the same vs the matched flat de-lever.
Taxes out of scope; one line of trades/yr and turnover per arm.

## Reading rule (fixed now)
This is a risk-appetite map, not a search for a better Sharpe.
1. Proposal only if an arm beats live on Sharpe on ALL THREE windows by more than 0.03 and sits on a plateau (at least two neighbouring arms in
   its family also clear 0.03 on all three). Otherwise no proposal.
2. Otherwise, for each lower-leverage arm report the CAGR cost per 1 pp of max-DD and per 1 pp of worst-20-day reduction, and whether cutting A
   (the arm) beats the matched plain de-lever on that ratio.
State plainly that the A split was previously chosen on overlapping data. Report anything approximate (turnover/gross from target weights,
full-day highs vs live 15:50 highs, VIXY pre-2011 absent).
