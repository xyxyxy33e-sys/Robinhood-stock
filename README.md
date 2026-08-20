# Stock Analyzer

A stock analysis dashboard fed by MCP data pulls:

- **Robinhood MCP** — real-time quotes, daily OHLCV history (1 year), fundamentals
- **Liquid (Co-Invest MCP)** — perp positioning (long share, bias, funding, open interest), curated market news, unusual-activity screen

Open **`dashboard.html`** in any browser (no server needed). Everything is computed
client-side from the embedded dataset.

## What it shows

| Section | Details |
|---|---|
| Quality score (0–100) | Composite of trend health, momentum, volume & liquidity, volatility regime, risk geometry, valuation — with a per-component breakdown |
| Trend | Uptrend / pullback / recovering / downtrend from SMA 20/50/200 structure |
| Volatility | ATR-14 as % of price, 30-day annualized realized vol, calm/normal/elevated regime |
| Suggested entry range | ATR- and support-anchored pullback zone below the current price |
| Confidence | High/Medium/Low from a 7-signal checklist (MAs, RSI, MACD, OBV) |
| Charts | Price with SMA 50/200 + Bollinger band + entry band overlay; volume vs 30-day average — with crosshair tooltips and 1M/3M/6M/1Y ranges |
| Liquid positioning | Mark price, 24h change, long share %, bias, funding, open interest |
| Fundamentals | Market cap, P/E, P/B, dividend yield, 52-week range, volumes |
| Market news | Recent headlines + Liquid unusual-activity movers |
| Tabs | Saved symbols persist in `localStorage`; add/remove freely |

## Architecture

```
data/analysis.json        <- dataset assembled from MCP pulls (bars, quotes, fundamentals, liquid, news)
dashboard.template.html   <- UI + all analytics (indicators, scoring) in plain JS/SVG
scripts/build_dashboard.py<- injects the JSON into the template -> dashboard.html
dashboard.html            <- built, self-contained output (the thing you open)
```

Indicators (SMA/EMA, RSI-14, MACD 12/26/9, ATR-14, Bollinger 20×2, OBV, realized
vol) are computed in the browser from raw daily bars, so the scoring is transparent
and re-derivable.

## Refreshing data / adding symbols

Data is a snapshot (stamped in the header). To refresh or add symbols, ask Claude
(in a session with the Robinhood + Co-Invest MCP servers connected) to:

1. Pull for each symbol: `get_equity_quotes`, `get_equity_fundamentals`,
   `get_equity_historicals` (1 year, `interval: day`), and Liquid
   `analyze_markets_batch` + `get_news`.
2. Regenerate `data/analysis.json` in the documented shape (see the existing file:
   `bars` are `[date, open, high, low, close, volume]`).
3. Run `python3 scripts/build_dashboard.py`.

A symbol tab added in the UI without embedded data shows a prompt explaining
exactly that.

> Informational tool only — not investment advice.
