# Stock Analyzer

A stock analysis dashboard fed by MCP data pulls:

- **Robinhood MCP** — real-time quotes, daily OHLCV history (1 year), fundamentals
- **Liquid (Co-Invest MCP)** — perp positioning (long share, bias, funding, open interest), curated market news, unusual-activity screen
- **Public.com MCP** — option chains with Greeks: 30-day ATM implied volatility, expected move (ATM straddle), put/call volume & OI ratios, 25Δ skew, highest-OI strikes

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
| Options market | 30d ATM IV vs realized vol, expected move by expiry, put/call ratios, 25Δ skew, highest-OI strikes |
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

Two paths:

**Live, in the published artifact** — the claude.ai artifact version declares the
`mcp` runtime capability, so a **Refresh data** button appears when viewed on
claude.ai with the Robinhood, Co-Invest, and Public connectors available. It
re-pulls everything through the viewer's own connectors (quotes, bars,
fundamentals, news, positioning, option chains), recomputes in the page, and
persists to `localStorage`. Adding a new symbol tab auto-pulls that symbol the
same way.

**Via Claude** — data is otherwise a snapshot (stamped in the header). Ask Claude
(in a session with the Robinhood + Co-Invest + Public MCP servers connected) to:

1. Pull for each symbol: `get_equity_quotes`, `get_equity_fundamentals`,
   `get_equity_historicals` (1 year, `interval: day`), Liquid
   `analyze_markets_batch` + `get_news`, and Public `get_option_chain` for the
   expiration nearest 30 days.
2. Regenerate `data/analysis.json` in the documented shape (see the existing file:
   `bars` are `[date, open, high, low, close, volume]`).
3. Run `python3 scripts/build_dashboard.py`.

> Informational tool only — not investment advice.
