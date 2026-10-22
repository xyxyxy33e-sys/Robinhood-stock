# `tlt_daily_tr.csv` (added 2026-10-22, research line `monte_carlo_new`)

iShares 20+ Year Treasury Bond ETF (TLT), daily, 2002-07-30 .. 2026-10-21.
Columns `d,c,close_raw`: `c` is Yahoo `adjclose` (split- AND dividend-adjusted,
i.e. a total-return series); `close_raw` is Yahoo's split-adjusted price.

Source: Yahoo Finance chart API (`query2.finance.yahoo.com/v8/finance/chart/TLT`),
pulled 2026-10-22. Check: `close_raw` matches `defensive_candidates/TLT.csv`
(2015-01..2026-08, 2,931 common days) within 0.08% relative.
