# `vixm_daily.csv` (added 2026-10-22, research line `monte_carlo_vixm`)

ProShares VIX Mid-Term Futures ETF (VIXM), daily, 2011-01-04 .. 2026-10-20.
Columns `d,c,close_raw`: date, split-adjusted close (`c`, Yahoo `adjclose`),
and Yahoo's split-adjusted `close` (identical: VIXM pays no distributions).

Source: Yahoo Finance chart API
(`query2.finance.yahoo.com/v8/finance/chart/VIXM?interval=1d`), pulled
2026-10-22 — the same source the 2026-10-08 VIXM research used (via yfinance).
One reverse split (1:4, 2014-11-06) is already in the adjusted series.

Check: matches the `VIXM` column of `live_closes.csv` on all 1,204 common days
(2022-01-03 .. 2026-10-20) to within 6e-8 relative. No gaps over 5 calendar days;
the only one-day moves over 15% are 2020-03-16/18/25 and 2024-08-05.
