# harness_live: the live design as the default (research only)

**Update 2026-11-17: L1 is switched off live, so the default is now L1 OFF (it follows `state.DGATE_HIGH_ENABLED`). Default results: real 51.1% / 2.100 / -16.5%, proxy 2001 (sleeve on from 2011) 34.0% / 1.480 / -22.1%. Pass `l1=True` for the old rule. Data audit: `research_notes/data_audit_2026_11/AUDIT.md`.**

`paper-track/harness_live.py` imports `review_2026_11/harness.py` (untouched, so old studies still reproduce) and builds the design that trades since
2026-11-11: **2.0x gross cap**, **VIXY sleeve at 35% of the cash leg** (full VIXY history, so it also runs on the proxy panel from 2011-01-04), and the
**D gate read on the day's high ("L1")**. Everything else is harness.CUR (A 40/60 + trim v2, B 50/50, D ladder + 0.5% buffer, max(10d,30d) vol target 20%,
5% band, 2 bp, deep-E and VIX-panic QQQ legs). `LIVE_CFG` documents every setting and its source in state.py.

## Call
```python
import sys; sys.path.insert(0, 'paper-track'); import harness_live as HL
r, ds, tpy = HL.run_live('real')            # or 'proxy'; same outputs as harness.run (daily returns, dates, trades/yr)
d = HL.run_live_detail('proxy', d0='2010-01-04', a_split=(0.5, 0.5), gross_cap=1.75)   # dict with r, ds, tpy, W, names, eff, gross, a_mask, gate
```
Overrides: `l1, gross_cap (None = no cap), a_cap (cap for state A only), a_split, a_instr ('QLD' moves A's TQQQ weight to QLD), sleeve_share,
sleeve_proxy, vol_target, risky_scale (flat de-lever), vixy_source ('full'|'old'), use_live_highs`, plus `d0, d1, lag, cost`.
`HL.build()` returns the weight matrix and leg returns for custom engines (the leverage study uses it); `HL.stats/fmt/cash_for` are harness's.

## Validation (`research_notes/leverage_a_2026_11/check_harness.py`, log `check_harness.log`)
CAGR / Sharpe / max DD; all windows end 2026-11-16 unless stated.

| Window | Run | Result | Recorded reference |
|---|---|---|---|
| Real 2015-11 | no L1, cap + VIXY 35% | 51.1% / 2.100 / -16.5% | 51.1% / 2.100 / -16.5% (vixy_sleeve_sweep), and identical to `harness.run(cap, VIXY 35%)` to 1e-16 |
| Real | L1 with highs as the recorded studies had them, to 2026-11-10 | 53.0% / 2.139 / -16.6% | 53.0% / 2.139 (STRATEGY.md); tax study 52.9% / 2.136 / -16.6% |
| Real | same, to 2026-11-16 | 53.7% / 2.158 / -16.6% | none (longer sample) |
| Real | L1 with complete highs (default until 2026-11-17), to 2026-11-16 | **50.6% / 2.064 / -25.4%** | none (see below) |
| Proxy 2001 | L1 (recorded highs), sleeve off | 34.0% / 1.474 / -22.1% | 34.0% / 1.474 |
| Proxy | no L1, sleeve off | 31.8% / 1.409 / -22.1% | 31.8% / 1.409 / -22.1% |
| Proxy | no L1, sleeve ON from 2011 | 34.0% / 1.480 / -22.1% | none |
| Proxy | L1 (recorded highs), sleeve ON | 36.3% / 1.546 / -22.1% | none |
| Proxy | **DEFAULT** (L1 complete highs, sleeve ON) | **35.1% / 1.505 / -24.9%** | none |
| Proxy | L1 complete highs, sleeve OFF | 33.2% / 1.435 / -28.1% | none |

Every reference is reproduced to the printed digit (the tax study's 52.9% / 2.136 is the same run on a slightly different end date and its own engine; mine gives
53.0% / 2.138 to 2026-11-11, inside 0.3 pp / 0.01).

**The one real difference, and why the default differs from the references.** `data/qqq_ohlc.csv` stops on 2026-09-04, so the recorded L1 studies read the CLOSE on the
~46-50 sessions after it (the research log says "all after 2026-09-04"). Those sessions include 2026-10-30..11-05. With real daily highs (QQQ full-day highs for
2026-09-08..11-10 from AlphaVantage `TIME_SERIES_DAILY`, saved in `research_notes/leverage_a_2026_11/qqq_highs_av_2026_09_11.csv`; live 15:50 highs from `data/qqq_highs.csv`
for 11-11 on) L1 re-opens the gate at the 2026-11-04 close (high 701.45 vs close 691.95) and the book is long 2.0x into the -6.5% QQQ day of 2026-11-05: -9.2% book day, max DD
-16.6% -> -25.4%, CAGR 53.7% -> 50.6%, Sharpe 2.158 -> 2.064; proxy max DD -22.1% -> -24.9% (sleeve on). The default therefore uses complete highs;
`use_live_highs=False` gives the recorded-reference behaviour. The 11-04 high is a full-day high: whether it printed before 15:50 is unknown, so this is an upper bound
on what live L1 would have done on that day (the live rule has only run since 2026-11-11).

## Known differences from live
- L1: the live gate reads the intraday high up to 15:50 (`data/qqq_highs.csv`); the backtest uses the full-day high (includes 15:50-16:00), which flatters entries (the dgate_high
  study measured ~80% of the gain surviving a crude cut). Daily highs for 2026-11-11 on are the live 15:50 values.
- Sleeve on the proxy panel is a research choice (VIXY exists from 2011-01-04; before that the sleeve is simply absent); `sleeve_proxy=False` restores the old harness behaviour.
- VIXY: split-adjusted Yahoo closes (full history); price-only; the real-panel run equals the harness-era series (max daily difference 0.27%, mean 0.002%).
- Gross exposure reported by `run_live_detail` is the TARGET weights' equity-like exposure (SPMO 1x, TQQQ 3x, QLD 2x, XLU 1x, QQQ legs 1x), not drifted holdings.
- 2 bp per side, no taxes, no financing/borrowing beyond the proxy's synthetic leveraged legs; VIXM data ends one session before the last date (only matters for old-VIXM runs).
- The signals are the engine's (classifier on the normalised QQQ path); the live system's data (15:50 prices) differ slightly from closes (live_closes.csv).
