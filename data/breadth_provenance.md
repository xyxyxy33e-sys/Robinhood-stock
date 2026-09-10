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
