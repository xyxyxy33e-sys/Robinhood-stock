# `<SYMBOL>_daily.csv` files (added 2026-09-10, research line `breadth_signal`)

45 files, columns `d,c` (date, split-adjusted close, 6 decimals), one row per
session, through 2026-09-09 (the 2026-09-10 bar was fetched intraday and
removed as unsettled). Source: Yahoo Finance chart API
`https://query1.finance.yahoo.com/v8/finance/chart/<SYMBOL>?period1=0&period2=<now>&interval=1d`
(field `indicators.quote[0].close`, split-adjusted, NOT dividend-adjusted),
fetched through the session proxy with curl. Chosen over the Robinhood
`get_equity_historicals` MCP tool because that tool returns ~60 tokens per bar
into the model context (a full 10-symbol/5000-bar call would be ~3M tokens);
Yahoo delivers the same split-adjusted daily closes as a file.

Cross-check against the repo's own series (Yahoo SPY/QQQ pulled and then
deleted, not stored): QQQ 6,784/6,784 repo dates present, 42 days differ by
more than 0.2%, all in 1999-2000 (Yahoo's early bad ticks, e.g. 1999-12-21
89.44 vs 88.69); SPY 6,778/6,778 present, 126 days >0.2%, all 1999-2002.
2003+ closes agree to the cent. XLU vs `xlu_long_history.csv`: identical from
2002-07; before that the REPO file is exactly 2x Yahoo -- the repo file has an
unadjusted seam at the 2025-12-05 2:1 split; Yahoo is internally consistent.
Conclusion: usable from 2003 with confidence; the 1999-2002 sector-ETF closes
carry Yahoo-era tick noise that a 50/200d SMA comparison is insensitive to.

Symbols and first date:
- Equal-weight vs cap-weight: QQEW 2006-05-02, RSP 2003-05-01 (4:1 split
  2006-04-27, adjusted). Cap-weight legs use the repo's
  `qqq_long_history.csv` / `spy_long_history.csv`.
- SPDR sectors: XLK XLF XLE XLV XLI XLY XLP XLU XLB all 1998-12-22; XLRE
  2015-10-08; XLC 2018-06-19. XLF's 2016-09-19 1.231:1 (the REIT spin-off)
  is applied by Yahoo as a split; XLK/XLE/XLY/XLU/XLB 2025-12-05 2:1 adjusted.
- QQQ top-30 basket (weights as of 2026-09, SURVIVORSHIP-BIASED by
  construction): AAPL MSFT NVDA AMZN META AVGO GOOGL TSLA COST NFLX PLTR CSCO
  AMD TMUS LIN PEP INTU ISRG AMAT QCOM BKNG TXN AMGN ADBE MU HON GILD PANW ADP
  CMCSA. Histories start 1970-2020 (META 2012-05, PANW 2012-07, PLTR
  2020-09, AVGO 2009-08, TSLA 2010-06, TMUS 2007-04, GOOGL 2004-08).
  Yahoo split events were checked for each (listed in the research note).

# Files added 2026-09-10 by research line `breadth_dgate_2000`

Purpose: survivorship-free breadth proxies with full 1999+ coverage, to extend
the D-row breadth gate test to 2000-07. All columns `d,c`.

- `nasdaqcom_fred.csv`, `nasdaq100_fred.csv`: FRED series NASDAQCOM
  (1971-02-05..2026-09-09) and NASDAQ100 (1986-01-02..2026-09-09) via
  `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES>`. Holiday rows
  carry an EMPTY value (FRED's "."): consumers must forward-fill, never drop.
- `RUT_index_daily.csv` (^RUT Russell 2000, 1987-09-10..2026-09-10),
  `RUA_index_daily.csv` (^RUA Russell 3000, 1987-09-10..), `NYA_index_daily.csv`
  (^NYA NYSE Composite, 1970-01-02..), `W5000_index_daily.csv` (^W5000 Wilshire
  5000, 1989-01-03..2026-09-09), `XAX_index_daily.csv` (^XAX NYSE American
  Composite, 1995-12-27..; fetched, NOT used), `NDX_index_daily.csv` (^NDX,
  1985-10-01..): Yahoo Finance chart API, same URL pattern as above, browser
  User-Agent required (the bare request is rate-limited "Too Many Requests"),
  timestamps converted to New York dates. Index closes, unadjusted (indices
  carry no splits). Cross-check: Yahoo ^NDX vs FRED NASDAQ100 on 6,962 common
  dates 1999+ agree except early Yahoo tick noise (max 2.4%, 1999); FRED is the
  NDX leg used everywhere. Value Line Geometric (^VLG): not on Yahoo ("symbol
  may be delisted"); stooq.com is behind a JavaScript challenge through the
  proxy; NOT obtained. FRED Wilshire series (WILL5000PR etc.) and Russell
  (RU2000PR) return 404 (discontinued).
- `ndx_survivor_ew_daily.csv` (`d,c,n`; 1999-01-05..2006-12-29): equal-weight,
  daily-rebalanced chain of the point-in-time Nasdaq-100 members WITH price
  data, roster by Nasdaq-100 Trust (QQQ) annual prospectus Schedule of
  Investments as of each Sept-30 1999..2006 (SEC EDGAR CIK 1067839, 485BPOS
  filings; issuer names mapped to era tickers by hand, 226 names), members
  fetched from Yahoo (198 tickers probed). `n` = names contributing that day
  (27-51). Coverage of the point-in-time roster with full-year data: 1999 30%,
  2000 28%, 2001 30%, 2002 33%, 2003 45%, 2004 47%, 2005 48%, 2006 52% -- the
  delisted/acquired names (WCOM, SUNW, YHOO, PSFT, JDSU, ...) are gone from
  Yahoo and reused tickers (ADPT, DELL, MNST, ATHM, ...) were excluded by date.
  SURVIVORSHIP-BIASED, ILLUSTRATIVE ONLY; never a holdout test.
