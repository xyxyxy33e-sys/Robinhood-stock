# Stock Analyzer — instructions for Claude sessions

The dashboard (`dashboard.html`) is built from `dashboard.template.html` +
`data/analysis.json` by `scripts/build_dashboard.py`.

## To refresh data or add a symbol

1. Pull per symbol (Robinhood MCP): `get_equity_quotes`, `get_equity_fundamentals`,
   and `get_equity_historicals` with `interval: "day"` and `start_time` one year back.
2. Pull once (Co-Invest / Liquid MCP): `analyze_markets_batch` for all symbols
   (skip failures — not every equity is tradable on Liquid) and `get_news`.
3. Update `data/analysis.json`, keeping the existing shape:
   - top level: `generatedAt`, `sources`, `news[] {title, source, url}`,
     `unusualActivity[] {symbol, ratio, lastHour}`, `symbols{}`
   - per symbol: `quote {last, prevClose, bid, ask}`, `fundamentals` (see existing
     keys; use `null` where not applicable), `liquid` (or `null` if not on Liquid),
     `bars` as arrays `[YYYY-MM-DD, open, high, low, close, volume]`.
4. Run `python3 scripts/build_dashboard.py` and verify `dashboard.html` renders
   without console errors.

All analytics (quality score, entry range, confidence, indicators) are computed in
the template's JavaScript — do not precompute them into the JSON.
