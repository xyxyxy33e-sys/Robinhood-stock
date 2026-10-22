# `tyx_daily.csv` (added 2026-10-22, research line `monte_carlo_new`, simulated rates)

CBOE 30-Year Treasury Yield Index (^TYX), daily close in percent,
2000-01-03 .. 2026-10-21. Source: Yahoo Finance chart API
(`query2.finance.yahoo.com/v8/finance/chart/%5ETYX`), pulled 2026-10-22.
FRED's DGS20/DGS30 download was blocked by a bot check from this environment.

Use: prices TLT from simulated yield paths in `monte_carlo_new.py`. Calibrated
on 2002-07..2026-10 against `tlt_daily_tr.csv`: daily TLT return =
(y30 - 0.25%) x year-fraction - 15.81 x dy + 0.5 x 261 x dy^2; R^2 0.88,
tracking error 5.0%/yr, mean error 0.00%/yr; CAGR 2002-07..2015-10 TLT 7.31% vs
model 7.13%, 2015-11..2026-10 -1.04% vs -0.57%.
