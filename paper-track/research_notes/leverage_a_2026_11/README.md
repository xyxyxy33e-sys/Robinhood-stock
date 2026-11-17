# How much leverage should state A carry? (2026-11-17) - research only, nothing adopted

Files: `PLAN.md` (arms, metrics and the reading rule, written before any arm ran), `run.py` -> `run.log` (default highs) and `run_refs.log` (`HIGHS=refs python3 run.py`),
`tables.md` / `tables_refs.md` (all README tables), `check_harness.py/.log`, `qqq_highs_av_2026_09_11.csv`. Engine: `paper-track/harness_live.py` (see `harness_live_README.md`).
Windows end 2026-11-16: real ETFs from 2015-11-03 (2,775 sessions), proxy from 2001-01-03 (6,505) and from 2010-01-05 (4,242). Sleeve on the proxy from 2011.

## Read this first: two things that shape every number
1. **State A's split is the wrong lever for the calm-crack losses.** On the 20 calm-crack days in the real window (prior VIX < 20, QQQ <= -3%) the live book lost 40.4% in total (sum of daily returns):
   only 3 days (2019-08-05, 2022-01-05, 2024-09-03: -15.2%, 38%) were in state A with no extension trim, i.e. where the SPMO/TQQQ split matters; 8 more were in A with the extension trim already on
   (TQQQ out, gross 0.12-0.33x: -6.1%, 15%); **4 were in ungated D (2019-08-23, 2021-03-18, 2026-10-30, 2026-11-05: -21.3%, 53%)** where the A split does nothing and only the cap (or D's rows) acts; 5 were gated/E/other (+2.1%).
   Consequence: mean book return on those days is -2.02% live, -2.01% with A 100/0 (!), -1.93% with A 20/80; only the cap moves it (cap 1.5 -1.47%, 1.75 -1.76%, none -2.16%). (`run.log`, "CRACK-DAY ANATOMY".)
2. **Highs.** The default harness_live reads QQQ's full-day highs for 2026-09-08..11-10, which the recorded L1 studies did not have (their file ends 2026-09-04). With them L1 re-opens the gate on the 11-04 close and the book takes the -9.2%
   day of 2026-11-05 at 2.0x (a D-state loss, identical for every A split). That one day sets the real-window max DD (-25.4% instead of -16.6%) and the worst-20 for every arm. I therefore give two passes: **default highs** (this README's first tables;
   `run.log`) and **recorded-reference highs** (file highs only; `run_refs.log`, `tables_refs.md`; live 53.7% / 2.158 / -16.6%), and say where they differ. The A-split conclusions do not depend on the pass.
   I could not verify that the 11-04 high printed before 15:50; treat the default-pass DD as an upper bound.

## Verdict under the reading rule (PLAN.md)
- **Rule 1 (proposal bar): no arm qualifies, in either pass.** No arm beats live on Sharpe by more than 0.03 on all three windows, and none has a plateau. Closest: A-only cap 1.5 / 1.75, dSharpe real / proxy01 / proxy10 =
  +0.004/+0.024/+0.007 and +0.005/+0.013/+0.007 (default highs); +0.016/+0.029/+0.016 and +0.011/+0.016/+0.011 (recorded highs); "cap none" +0.004/+0.016/+0.019 (recorded highs; -0.006/+0.013/+0.014 default);
  A SPMO/QLD 50/50 +0.030 on proxy01 only (recorded highs; -0.016/+0.023/+0.003 default). Bootstrap P(dSharpe <= 0) for A-only cap: 0.45/0.17/0.42 (1.5) and 0.39/0.13/0.35 (1.75), default highs: not distinguishable from zero in the real window.
- **Rule 2 (risk-appetite map): cutting A is a poor way to buy drawdown protection; a plain de-lever of the whole book is cheaper per point on almost every cell.** CAGR given up per 1 pp of max DD avoided (default highs, real): A 100/0 4.3 vs 1.3 for the
  matched flat de-lever, A 80/20 4.4 vs 1.3, A 60/40 5.6 vs 1.3, A SPMO/QLD 50/50 3.6 vs 1.3, A-only cap 1.5 / 1.75 2.5 / 2.1 vs 1.3, cap 1.5 / 1.75 1.40 / 1.28 vs 1.26 / 1.28 (the all-state cap is the only lever that ties the de-lever). Worst-20 per pp: similar.
  Recorded-highs pass: de-lever 2.6-3.0 on real; arms 3.2-6.9 on max DD (1.9-7.6 on worst-20), except A-only cap on the worst-20 metric (2.28 / 1.92 vs 2.69 / 2.65, cheaper) in real and proxy01 - but not on max DD, and not on proxy10 (4.8 / 13.4 vs 2.5). Mixed, not a finding.
  No arm is cheaper than the matched de-lever in all three windows. A 0/100 QLD shows a ~0 cost in the default real window only because it gives up almost no CAGR while lowering avg gross by 0.07 (n/a on the proxy windows: no DD avoided).
- **Previously chosen on overlapping data:** the A 40/60 split came from STRATEGY.md's "A-row ratio study" (and A 25/75, 20/80 were live for days) on these same real/proxy windows; a split that looks best or worst here is not an out-of-sample finding, and no arm here is proposed.

## What the map says
- Splits: more TQQQ pays more and costs little Sharpe: real CAGR 32.7 / 39.3 / 45.9 / 49.2 / **50.6** / 51.3 / 51.8 for 100/0 ... 20/80, Sharpe 1.790 / 1.980 / 2.049 / 2.054 / **2.064** / 2.056 / 2.048 (default highs); 30/70 and 20/80 are the same gross after the 2.0x cap (avg gross 1.14 / 1.13); the cap is what limits leverage in A, not the split.
  The split only matters in 2022-type years: 2022 return +12.3% (100/0), +5.6% (60/40), +2.2% (live), +0.3% (20/80) real; proxy01 0.0 / -4.2 / -6.3 / -7.0.
- Cap: every 0.25x of cap is worth ~3-5 pp CAGR and ~2-3.5 pp of max DD (default real: 1.5 41.0% / -18.6%, 1.75 46.1% / -21.9%, 2.0 50.6% / -25.4%, 2.25 53.6% / -27.6%, none 54.9% / -27.2%; recorded highs -13.9 / -15.1 / -16.6 / -17.8 / -18.3). Sharpe is flat (2.046-2.073 default real).
  The 11-05 day: -4.3% (cap 1.5), -6.7% (1.75), -9.2% (2.0), -11.1% (2.25 / none): the cap is the only tested lever on that day.
- Matched de-levers beat every arm on Sharpe at equal gross (e.g. real: A 60/40 2.049 vs matched 2.086; cap 1.75 2.073 vs 2.099; A 100/0 1.790 vs 2.177): probably because the freed gross sits in BOXX and the vol-targeted days keep their scale (not tested), so holding less everywhere looks a better use of the same gross than concentrating the cut in A. Bootstrap P(arm Sharpe <= matched de-lever) 0.6-0.99, mostly above 0.8 (robustness table below).
- Turnover: trades/yr 44-51 on real (live 47.1; low-TQQQ splits and the 2.25 / none caps trade more, the lower caps less), one-way turnover 26-33 books/yr; taxes are out of scope.

## Tables (default highs)
### Leverage table: CAGR % / Sharpe / maxDD % / worst-20-session % / avg gross, per window; matched = plain flat de-lever to the arm's avg gross

| arm | real | proxy 2001 | proxy 2010 |
|---|---|---|---|
| A 100/0 | 32.7 / 1.790 / -21.3 / -19.7 / 0.80 | 25.3 / 1.456 / -19.7 / -18.8 / 0.76 | 31.0 / 1.653 / -19.7 / -18.8 / 0.84 |
| &nbsp;&nbsp;matched flat de-lever | 37.7 / 2.177 / -15.2 / -13.8 / 0.80 | 26.3 / 1.572 / -18.6 / -14.1 / 0.76 | 32.5 / 1.848 / -14.4 / -13.1 / 0.84 |
| A 80/20 | 39.3 / 1.980 / -22.8 / -21.5 / 0.94 | 29.1 / 1.503 / -21.9 / -20.7 / 0.88 | 36.4 / 1.730 / -21.9 / -20.7 / 1.00 |
| &nbsp;&nbsp;matched flat de-lever | 42.8 / 2.134 / -19.3 / -17.7 / 0.94 | 29.9 / 1.546 / -20.0 / -17.5 / 0.88 | 37.6 / 1.816 / -18.6 / -17.1 / 1.00 |
| A 60/40 | 45.9 / 2.049 / -24.6 / -22.9 / 1.08 | 32.7 / 1.507 / -24.2 / -22.5 / 1.01 | 41.8 / 1.753 / -24.2 / -22.5 / 1.15 |
| &nbsp;&nbsp;matched flat de-lever | 48.0 / 2.086 / -23.4 / -21.6 / 1.08 | 33.4 / 1.519 / -23.2 / -21.5 / 1.01 | 42.7 / 1.779 / -23.0 / -21.4 / 1.15 |
| A 50/50 | 49.2 / 2.054 / -25.5 / -23.7 / 1.14 | 34.6 / 1.501 / -25.2 / -23.5 / 1.07 | 44.5 / 1.754 / -25.2 / -23.5 / 1.23 |
| LIVE A 40/60 | 50.6 / 2.064 / -25.4 / -23.6 / 1.14 | 35.1 / 1.505 / -24.9 / -23.2 / 1.07 | 45.2 / 1.762 / -24.9 / -23.2 / 1.23 |
| A 30/70 | 51.3 / 2.056 / -25.1 / -23.3 / 1.14 | 35.4 / 1.505 / -25.2 / -23.4 / 1.06 | 45.5 / 1.764 / -25.2 / -23.4 / 1.22 |
| A 20/80 | 51.8 / 2.048 / -25.1 / -23.3 / 1.13 | 35.6 / 1.503 / -25.2 / -23.4 / 1.06 | 45.7 / 1.762 / -25.2 / -23.4 / 1.21 |
| A SPMO/QLD 50/50 | 41.9 / 2.047 / -23.0 / -21.6 / 0.94 | 30.1 / 1.528 / -22.4 / -21.1 / 0.88 | 38.0 / 1.765 / -22.4 / -21.1 / 1.01 |
| &nbsp;&nbsp;matched flat de-lever | 42.8 / 2.134 / -19.2 / -17.7 / 0.94 | 29.9 / 1.545 / -20.0 / -17.6 / 0.88 | 37.9 / 1.814 / -18.9 / -17.4 / 1.01 |
| A 0/100 QLD | 50.6 / 2.022 / -25.0 / -23.2 / 1.07 | 34.6 / 1.512 / -25.1 / -23.4 / 1.01 | 44.8 / 1.770 / -25.1 / -23.4 / 1.17 |
| &nbsp;&nbsp;matched flat de-lever | 48.0 / 2.087 / -23.3 / -21.6 / 1.07 | 33.5 / 1.518 / -23.3 / -21.6 / 1.01 | 43.3 / 1.776 / -23.5 / -21.8 / 1.17 |
| cap 1.5 | 41.0 / 2.071 / -18.6 / -17.1 / 0.93 | 28.8 / 1.498 / -21.0 / -16.9 / 0.87 | 35.9 / 1.744 / -19.0 / -16.9 / 0.99 |
| &nbsp;&nbsp;matched flat de-lever | 42.4 / 2.139 / -18.9 / -17.3 / 0.93 | 29.5 / 1.548 / -19.8 / -17.1 / 0.87 | 37.3 / 1.818 / -18.4 / -16.9 / 0.99 |
| cap 1.75 | 46.1 / 2.073 / -21.9 / -20.2 / 1.04 | 32.1 / 1.506 / -21.8 / -20.2 / 0.97 | 40.8 / 1.759 / -21.8 / -20.2 / 1.11 |
| &nbsp;&nbsp;matched flat de-lever | 46.6 / 2.099 / -22.3 / -20.6 / 1.04 | 32.4 / 1.527 / -22.0 / -20.4 / 0.97 | 41.3 / 1.789 / -21.9 / -20.3 / 1.11 |
| cap 2.25 | 53.6 / 2.046 / -27.6 / -25.7 / 1.22 | 37.4 / 1.502 / -27.4 / -25.6 / 1.14 | 48.4 / 1.756 / -27.4 / -25.6 / 1.32 |
| cap none | 54.9 / 2.058 / -27.2 / -25.3 / 1.23 | 38.5 / 1.519 / -27.1 / -25.2 / 1.15 | 50.0 / 1.776 / -27.1 / -25.2 / 1.33 |
| A-only cap 1.5 | 43.7 / 2.068 / -22.6 / -21.2 / 0.95 | 31.1 / 1.529 / -22.5 / -21.1 / 0.89 | 38.9 / 1.770 / -22.5 / -21.1 / 1.01 |
| &nbsp;&nbsp;matched flat de-lever | 43.1 / 2.131 / -19.5 / -17.9 / 0.95 | 30.1 / 1.544 / -20.1 / -17.8 / 0.89 | 38.1 / 1.812 / -19.1 / -17.5 / 1.01 |
| A-only cap 1.75 | 47.3 / 2.069 / -23.9 / -22.3 / 1.05 | 33.2 / 1.519 / -23.9 / -22.3 / 0.98 | 42.2 / 1.769 / -23.9 / -22.3 / 1.12 |
| &nbsp;&nbsp;matched flat de-lever | 47.0 / 2.096 / -22.5 / -20.8 / 1.05 | 32.7 / 1.524 / -22.3 / -20.7 / 0.98 | 41.7 / 1.787 / -22.2 / -20.6 / 1.12 |
| grid 60/40 cap 1.75 | 44.2 / 2.057 / -22.4 / -20.7 / 1.05 | 31.4 / 1.499 / -21.7 / -20.1 / 0.98 | 40.0 / 1.749 / -21.7 / -20.1 / 1.12 |
| &nbsp;&nbsp;matched flat de-lever | 47.0 / 2.095 / -22.6 / -20.9 / 1.05 | 32.7 / 1.524 / -22.3 / -20.7 / 0.98 | 41.7 / 1.788 / -22.2 / -20.5 / 1.12 |
| grid 50/50 cap 1.75 | 45.3 / 2.068 / -22.2 / -20.5 / 1.05 | 31.8 / 1.503 / -21.6 / -20.1 / 0.98 | 40.5 / 1.756 / -21.6 / -20.1 / 1.12 |
| &nbsp;&nbsp;matched flat de-lever | 46.9 / 2.097 / -22.5 / -20.8 / 1.05 | 32.6 / 1.525 / -22.2 / -20.6 / 0.98 | 41.6 / 1.788 / -22.1 / -20.4 / 1.12 |

### Cost per point (CAGR pp given up per 1 pp avoided): arm vs matched flat de-lever; DD = max drawdown, W20 = worst 20 sessions; * = arm cheaper than matched; n/a = nothing avoided

| arm | real DD | real W20 | proxy01 DD | proxy01 W20 | proxy10 DD | proxy10 W20 |
|---|---|---|---|---|---|---|
| A 100/0 | 4.32 vs 1.27 | 4.66 vs 1.32 | 1.87 vs 1.40 | 2.22 vs 0.97 | 2.69 vs 1.20 | 3.19 vs 1.25 |
| A 80/20 | 4.37 vs 1.26 | 5.36 vs 1.32 | 2.03 vs 1.06 | 2.40 vs 0.92 | 2.94 vs 1.20 | 3.48 vs 1.24 |
| A 60/40 | 5.62 vs 1.27 | 7.08 vs 1.32 | 3.05 vs 0.96 | 3.63 vs 1.00 | 4.39 vs 1.30 | 5.22 vs 1.35 |
| A SPMO/QLD 50/50 | 3.57 vs 1.26 | 4.30 vs 1.31 | 2.01 vs 1.05 | 2.39 vs 0.92 | 2.88 vs 1.20 | 3.43 vs 1.24 |
| A 0/100 QLD | -0.04* vs 1.27 | -0.04* vs 1.32 | n/a vs 0.96 | n/a vs 0.99 | n/a vs 1.31 | n/a vs 1.37 |
| cap 1.5 | 1.40 vs 1.26 | 1.47 vs 1.31 | 1.60 vs 1.10 | 1.00 vs 0.92 | 1.56 vs 1.20 | 1.46 vs 1.24 |
| cap 1.75 | 1.28 vs 1.28 | 1.34 vs 1.33 | 0.97 vs 0.93 | 1.01 vs 0.97 | 1.41 vs 1.26 | 1.46 vs 1.31 |
| A-only cap 1.5 | 2.47 vs 1.26 | 2.88 vs 1.31 | 1.65 vs 1.03 | 1.92 vs 0.92 | 2.55 vs 1.20 | 2.98 vs 1.25 |
| A-only cap 1.75 | 2.11 vs 1.27 | 2.46 vs 1.32 | 1.84 vs 0.94 | 2.14 vs 0.98 | 2.85 vs 1.26 | 3.31 vs 1.31 |
| grid 60/40 cap 1.75 | 2.13 vs 1.27 | 2.25 vs 1.32 | 1.15 vs 0.94 | 1.20 vs 0.98 | 1.61 vs 1.26 | 1.68 vs 1.31 |
| grid 50/50 cap 1.75 | 1.66 vs 1.27 | 1.75 vs 1.32 | 1.01 vs 0.93 | 1.05 vs 0.97 | 1.43 vs 1.26 | 1.49 vs 1.31 |

### Calm-crack days (prior VIX < 20, QQQ <= -3%): mean book return %, total % (sum), share of the arm's summed return on all QQQ <= -2% days / on leveraged-state -2% days

| arm | real (20 days) | proxy 2001 (33) | proxy 2010 (22) |
|---|---|---|---|
| A 100/0 | -2.01 / -40.2 / 18.7% / 23.3% | -1.96 / -64.8 / 10.3% / 14.6% | -2.19 / -48.2 / 13.0% / 16.4% |
| A 80/20 | -2.03 / -40.7 / 17.9% / 22.1% | -1.98 / -65.2 / 10.0% / 14.0% | -2.19 / -48.3 / 12.4% / 15.6% |
| A 60/40 | -2.05 / -40.9 / 17.1% / 20.9% | -1.98 / -65.4 / 9.7% / 13.3% | -2.19 / -48.1 / 11.9% / 14.8% |
| A 50/50 | -2.04 / -40.8 / 16.7% / 20.3% | -1.97 / -65.1 / 9.5% / 12.9% | -2.17 / -47.7 / 11.6% / 14.4% |
| LIVE A 40/60 | -2.02 / -40.4 / 16.5% / 20.2% | -1.94 / -64.0 / 9.4% / 12.8% | -2.15 / -47.3 / 11.6% / 14.4% |
| A 30/70 | -1.99 / -39.8 / 16.4% / 20.0% | -1.89 / -62.3 / 9.2% / 12.7% | -2.10 / -46.2 / 11.5% / 14.3% |
| A 20/80 | -1.93 / -38.6 / 16.1% / 19.7% | -1.83 / -60.3 / 9.1% / 12.4% | -2.03 / -44.8 / 11.3% / 14.1% |
| A SPMO/QLD 50/50 | -1.86 / -37.2 / 16.8% / 21.0% | -1.79 / -59.2 / 9.5% / 13.4% | -1.99 / -43.9 / 11.8% / 15.0% |
| A 0/100 QLD | -1.71 / -34.2 / 15.1% / 18.8% | -1.62 / -53.5 / 8.6% / 12.1% | -1.79 / -39.4 / 10.6% / 13.5% |
| cap 1.5 | -1.47 / -29.3 / 13.9% / 17.7% | -1.52 / -50.3 / 8.2% / 11.5% | -1.62 / -35.6 / 10.0% / 13.0% |
| cap 1.75 | -1.76 / -35.3 / 15.4% / 19.1% | -1.75 / -57.7 / 8.9% / 12.3% | -1.91 / -42.0 / 11.0% / 13.9% |
| cap 2.25 | -2.16 / -43.1 / 16.9% / 20.5% | -2.05 / -67.8 / 9.6% / 13.0% | -2.28 / -50.2 / 11.8% / 14.5% |
| cap none | -2.16 / -43.1 / 16.8% / 20.4% | -2.05 / -67.8 / 9.6% / 13.0% | -2.28 / -50.2 / 11.8% / 14.4% |
| A-only cap 1.5 | -1.80 / -36.0 / 16.1% / 20.2% | -1.73 / -57.0 / 9.0% / 12.7% | -1.92 / -42.3 / 11.4% / 14.5% |
| A-only cap 1.75 | -1.93 / -38.6 / 16.5% / 20.3% | -1.85 / -61.1 / 9.3% / 12.9% | -2.06 / -45.4 / 11.6% / 14.6% |
| grid 60/40 cap 1.75 | -1.87 / -37.4 / 16.1% / 19.9% | -1.86 / -61.5 / 9.3% / 12.8% | -2.02 / -44.4 / 11.3% / 14.2% |
| grid 50/50 cap 1.75 | -1.83 / -36.6 / 15.8% / 19.6% | -1.81 / -59.8 / 9.1% / 12.6% | -1.97 / -43.4 / 11.2% / 14.1% |
| matched flat(A 100/0) | -0.92 / -18.4 / 11.4% / 16.5% | -1.05 / -34.7 / 7.0% / 10.8% | -0.98 / -21.6 / 7.9% / 11.6% |
| matched flat(A 80/20) | -1.36 / -27.1 / 13.9% / 18.3% | -1.41 / -46.4 / 8.1% / 11.8% | -1.45 / -31.8 / 9.8% / 13.0% |
| matched flat(A 60/40) | -1.80 / -36.1 / 15.8% / 19.7% | -1.76 / -58.1 / 9.0% / 12.5% | -1.91 / -42.1 / 11.1% / 14.0% |
| matched flat(A SPMO/QLD 50/50) | -1.35 / -27.1 / 13.9% / 18.3% | -1.41 / -46.6 / 8.1% / 11.8% | -1.47 / -32.4 / 9.8% / 13.1% |
| matched flat(A 0/100 QLD) | -1.80 / -36.0 / 15.8% / 19.7% | -1.77 / -58.5 / 9.0% / 12.5% | -1.97 / -43.2 / 11.2% / 14.1% |
| matched flat(cap 1.5) | -1.32 / -26.4 / 13.7% / 18.2% | -1.37 / -45.3 / 8.0% / 11.7% | -1.42 / -31.2 / 9.7% / 12.9% |
| matched flat(cap 1.75) | -1.68 / -33.6 / 15.3% / 19.4% | -1.66 / -54.8 / 8.8% / 12.3% | -1.79 / -39.3 / 10.8% / 13.8% |
| matched flat(A-only cap 1.5) | -1.38 / -27.6 / 14.0% / 18.4% | -1.43 / -47.3 / 8.2% / 11.9% | -1.49 / -32.8 / 9.9% / 13.1% |
| matched flat(A-only cap 1.75) | -1.71 / -34.2 / 15.5% / 19.4% | -1.69 / -55.7 / 8.9% / 12.4% | -1.82 / -40.1 / 10.8% / 13.8% |
| matched flat(grid 60/40 cap 1.75) | -1.72 / -34.4 / 15.5% / 19.5% | -1.69 / -55.7 / 8.9% / 12.4% | -1.82 / -40.0 / 10.8% / 13.8% |
| matched flat(grid 50/50 cap 1.75) | -1.71 / -34.1 / 15.4% / 19.4% | -1.68 / -55.4 / 8.8% / 12.4% | -1.81 / -39.8 / 10.8% / 13.8% |

### Stress, % return (real panel; proxy 2001 for 2022 and Feb-Mar 2020 in brackets)

| arm | 2022 | Feb-Mar 2020 | 2026-11-05 | 2026-10-30..11-05 |
|---|---|---|---|---|
| A 100/0 | +12.3 [+0.0] | +11.2 [+10.6] | -9.17 | -16.83 |
| A 80/20 | +8.9 [-2.1] | +11.4 [+10.8] | -9.17 | -16.83 |
| A 60/40 | +5.6 [-4.2] | +11.6 [+11.0] | -9.17 | -16.83 |
| A 50/50 | +3.9 [-5.3] | +11.7 [+11.1] | -9.17 | -16.83 |
| LIVE A 40/60 | +2.2 [-6.3] | +11.8 [+11.2] | -9.17 | -16.83 |
| A 30/70 | +1.0 [-7.0] | +11.9 [+11.2] | -9.17 | -16.83 |
| A 20/80 | +0.3 [-7.0] | +11.9 [+11.2] | -9.17 | -16.83 |
| A SPMO/QLD 50/50 | +6.7 [-2.7] | +11.7 [+11.1] | -9.17 | -16.83 |
| A 0/100 QLD | +1.1 [-5.3] | +12.2 [+11.4] | -9.17 | -16.83 |
| cap 1.5 | +4.2 [-4.1] | +11.8 [+11.2] | -4.28 | -10.34 |
| cap 1.75 | +3.1 [-5.4] | +11.8 [+11.2] | -6.73 | -13.61 |
| cap 2.25 | +2.2 [-6.3] | +11.8 [+11.2] | -11.13 | -18.76 |
| cap none | +2.2 [-6.3] | +11.8 [+11.2] | -11.13 | -18.76 |
| A-only cap 1.5 | +4.2 [-4.1] | +11.8 [+11.2] | -9.17 | -16.83 |
| A-only cap 1.75 | +3.1 [-5.4] | +11.8 [+11.2] | -9.17 | -16.83 |
| grid 60/40 cap 1.75 | +5.6 [-4.2] | +11.6 [+11.0] | -6.73 | -13.61 |
| grid 50/50 cap 1.75 | +3.9 [-5.2] | +11.7 [+11.1] | -6.73 | -13.61 |
| matched flat(A 100/0) | +7.1 [+0.9] | +11.7 [+11.2] | -3.14 | -8.79 |
| matched flat(A 80/20) | +5.0 [-2.0] | +11.7 [+11.2] | -5.57 | -12.07 |
| matched flat(A 60/40) | +3.1 [-5.0] | +11.8 [+11.1] | -8.00 | -15.29 |
| matched flat(A SPMO/QLD 50/50) | +5.0 [-2.1] | +11.7 [+11.2] | -5.56 | -12.05 |
| matched flat(A 0/100 QLD) | +3.2 [-5.1] | +11.8 [+11.1] | -7.97 | -15.25 |
| matched flat(cap 1.5) | +5.2 [-1.7] | +11.7 [+11.2] | -5.36 | -11.78 |
| matched flat(cap 1.75) | +3.7 [-4.0] | +11.8 [+11.1] | -7.33 | -14.41 |
| matched flat(A-only cap 1.5) | +4.9 [-2.2] | +11.7 [+11.2] | -5.70 | -12.24 |
| matched flat(A-only cap 1.75) | +3.5 [-4.2] | +11.8 [+11.1] | -7.49 | -14.62 |
| matched flat(grid 60/40 cap 1.75) | +3.5 [-4.2] | +11.8 [+11.1] | -7.53 | -14.68 |
| matched flat(grid 50/50 cap 1.75) | +3.6 [-4.1] | +11.8 [+11.1] | -7.47 | -14.59 |

### Robustness, lower-leverage arms: dSharpe vs live (full / half1 / half2 / ex-2020), bootstrap median and P(dSh<=0); and full dSharpe vs matched de-lever with P

| arm | window | vs live | bootstrap | vs matched (dSh, P) |
|---|---|---|---|---|
| A 100/0 | real | -0.274 / -0.266 / -0.273 / -0.285 | -0.268, P 0.95 | -0.387, P 0.98 |
| A 100/0 | p01 | -0.050 / +0.014 / -0.111 / -0.057 | -0.048, P 0.74 | -0.116, P 0.94 |
| A 100/0 | p10 | -0.109 / -0.079 / -0.152 / -0.122 | -0.113, P 0.87 | -0.195, P 0.97 |
| A 80/20 | real | -0.084 / -0.041 / -0.111 / -0.087 | -0.081, P 0.81 | -0.154, P 0.93 |
| A 80/20 | p01 | -0.002 / +0.033 / -0.036 / -0.007 | -0.001, P 0.51 | -0.042, P 0.83 |
| A 80/20 | p10 | -0.033 / -0.015 / -0.058 / -0.040 | -0.035, P 0.74 | -0.086, P 0.93 |
| A 60/40 | real | -0.015 / +0.012 / -0.032 / -0.015 | -0.014, P 0.63 | -0.037, P 0.81 |
| A 60/40 | p01 | +0.002 / +0.019 / -0.014 / +0.000 | +0.002, P 0.44 | -0.011, P 0.75 |
| A 60/40 | p10 | -0.009 / +0.002 / -0.022 / -0.012 | -0.010, P 0.69 | -0.026, P 0.89 |
| A SPMO/QLD 50/50 | real | -0.016 / +0.014 / -0.037 / -0.013 | -0.014, P 0.60 | -0.087, P 0.90 |
| A SPMO/QLD 50/50 | p01 | +0.023 / +0.039 / +0.005 / +0.023 | +0.023, P 0.22 | -0.017, P 0.70 |
| A SPMO/QLD 50/50 | p10 | +0.003 / +0.019 / -0.020 / +0.002 | +0.001, P 0.48 | -0.049, P 0.88 |
| A 0/100 QLD | real | -0.042 / -0.092 / -0.008 / -0.033 | -0.041, P 0.84 | -0.065, P 0.94 |
| A 0/100 QLD | p01 | +0.006 / +0.002 / +0.008 / +0.014 | +0.006, P 0.36 | -0.006, P 0.62 |
| A 0/100 QLD | p10 | +0.008 / +0.031 / -0.014 / +0.020 | +0.008, P 0.34 | -0.006, P 0.59 |
| cap 1.5 | real | +0.007 / -0.032 / +0.030 / +0.004 | +0.007, P 0.46 | -0.068, P 0.94 |
| cap 1.5 | p01 | -0.008 / -0.007 / -0.001 / -0.014 | -0.007, P 0.61 | -0.051, P 0.99 |
| cap 1.5 | p10 | -0.018 / -0.040 / -0.003 / -0.028 | -0.020, P 0.72 | -0.074, P 0.99 |
| cap 1.75 | real | +0.009 / -0.011 / +0.021 / +0.006 | +0.008, P 0.38 | -0.027, P 0.89 |
| cap 1.75 | p01 | +0.000 / -0.002 / +0.006 / -0.003 | +0.001, P 0.49 | -0.021, P 0.96 |
| cap 1.75 | p10 | -0.003 / -0.014 / +0.006 / -0.008 | -0.004, P 0.58 | -0.030, P 0.98 |
| A-only cap 1.5 | real | +0.004 / +0.033 / -0.021 / +0.002 | +0.006, P 0.45 | -0.064, P 0.88 |
| A-only cap 1.5 | p01 | +0.024 / +0.026 / +0.027 / +0.021 | +0.024, P 0.17 | -0.015, P 0.69 |
| A-only cap 1.5 | p10 | +0.007 / +0.016 / -0.008 / +0.003 | +0.006, P 0.42 | -0.043, P 0.88 |
| A-only cap 1.75 | real | +0.005 / +0.016 / -0.003 / +0.004 | +0.006, P 0.39 | -0.027, P 0.86 |
| A-only cap 1.75 | p01 | +0.013 / +0.012 / +0.017 / +0.012 | +0.014, P 0.13 | -0.005, P 0.64 |
| A-only cap 1.75 | p10 | +0.007 / +0.010 / +0.001 / +0.005 | +0.007, P 0.35 | -0.018, P 0.84 |
| grid 60/40 cap 1.75 | real | -0.007 / -0.011 / -0.005 / -0.008 | -0.006, P 0.57 | -0.038, P 0.84 |
| grid 60/40 cap 1.75 | p01 | -0.006 / +0.006 / -0.017 / -0.010 | -0.006, P 0.64 | -0.025, P 0.94 |
| grid 60/40 cap 1.75 | p10 | -0.014 / -0.021 / -0.009 / -0.019 | -0.015, P 0.76 | -0.039, P 0.97 |
| grid 50/50 cap 1.75 | real | +0.005 / -0.006 / +0.011 / +0.003 | +0.004, P 0.43 | -0.028, P 0.88 |
| grid 50/50 cap 1.75 | p01 | -0.002 / +0.001 / -0.004 / -0.005 | -0.002, P 0.57 | -0.022, P 0.97 |
| grid 50/50 cap 1.75 | p10 | -0.007 / -0.020 / +0.004 / -0.011 | -0.007, P 0.68 | -0.033, P 0.99 |

### Trades per year / one-way annual turnover (sum |target - held| at rebalances; 1.0 = whole book once)

| arm | real | proxy 2001 | proxy 2010 |
|---|---|---|---|
| A 100/0 | 50.9 / 28.8 | 47.0 / 26.7 | 46.3 / 28.6 |
| A 80/20 | 50.5 / 29.1 | 46.2 / 26.8 | 46.0 / 28.7 |
| A 60/40 | 49.8 / 29.6 | 45.5 / 27.1 | 45.7 / 28.9 |
| A 50/50 | 49.4 / 30.0 | 45.2 / 27.5 | 45.7 / 29.2 |
| LIVE A 40/60 | 47.1 / 30.4 | 43.1 / 27.7 | 43.8 / 29.5 |
| A 30/70 | 45.6 / 30.9 | 41.8 / 28.1 | 42.7 / 29.9 |
| A 20/80 | 44.4 / 31.6 | 40.4 / 28.5 | 41.5 / 30.5 |
| A SPMO/QLD 50/50 | 48.5 / 27.6 | 44.1 / 25.7 | 44.3 / 26.8 |
| A 0/100 QLD | 45.3 / 32.6 | 41.5 / 29.8 | 42.4 / 31.3 |
| cap 1.5 | 44.0 / 29.3 | 40.6 / 26.5 | 41.0 / 28.3 |
| cap 1.75 | 45.2 / 29.7 | 41.7 / 27.0 | 42.2 / 28.8 |
| cap 2.25 | 49.5 / 31.2 | 45.6 / 28.5 | 46.2 / 30.3 |
| cap none | 50.4 / 31.3 | 46.4 / 28.8 | 47.3 / 30.6 |
| A-only cap 1.5 | 44.6 / 29.5 | 41.0 / 26.9 | 41.6 / 28.7 |
| A-only cap 1.75 | 45.7 / 29.8 | 42.0 / 27.2 | 42.7 / 29.0 |
| grid 60/40 cap 1.75 | 48.7 / 29.3 | 44.4 / 26.7 | 44.7 / 28.5 |
| grid 50/50 cap 1.75 | 46.5 / 29.1 | 42.6 / 26.6 | 43.0 / 28.3 |

## Tables (recorded-reference highs: file highs only; live = 53.7% / 2.158 / -16.6% real)

### Leverage table: CAGR % / Sharpe / maxDD % / worst-20-session % / avg gross, per window; matched = plain flat de-lever to the arm's avg gross

| arm | real | proxy 2001 | proxy 2010 |
|---|---|---|---|
| A 100/0 | 35.4 / 1.908 / -12.5 / -11.6 / 0.80 | 26.4 / 1.508 / -19.0 / -13.2 / 0.76 | 32.8 / 1.730 / -15.4 / -13.2 / 0.84 |
| &nbsp;&nbsp;matched flat de-lever | 39.5 / 2.229 / -11.7 / -11.5 / 0.80 | 27.0 / 1.600 / -18.6 / -14.1 / 0.76 | 33.7 / 1.885 / -13.6 / -11.0 / 0.84 |
| A 80/20 | 42.2 / 2.091 / -13.7 / -13.6 / 0.94 | 30.2 / 1.551 / -20.0 / -14.8 / 0.88 | 38.3 / 1.800 / -17.0 / -13.8 / 0.99 |
| &nbsp;&nbsp;matched flat de-lever | 45.2 / 2.206 / -13.7 / -13.4 / 0.94 | 30.8 / 1.580 / -20.0 / -16.5 / 0.88 | 39.1 / 1.864 / -16.4 / -13.3 / 0.99 |
| A 60/40 | 48.9 / 2.151 / -15.6 / -15.6 / 1.07 | 33.9 / 1.551 / -21.1 / -18.0 / 1.01 | 43.7 / 1.816 / -18.5 / -15.6 / 1.15 |
| &nbsp;&nbsp;matched flat de-lever | 50.8 / 2.174 / -15.7 / -15.4 / 1.07 | 34.5 / 1.557 / -21.4 / -18.7 / 1.01 | 44.5 / 1.835 / -18.8 / -15.5 / 1.15 |
| A 50/50 | 52.2 / 2.150 / -16.7 / -16.7 / 1.14 | 35.8 / 1.542 / -21.6 / -19.5 / 1.07 | 46.4 / 1.813 / -19.3 / -16.5 / 1.23 |
| LIVE A 40/60 | 53.7 / 2.158 / -16.6 / -16.5 / 1.14 | 36.3 / 1.546 / -22.1 / -19.8 / 1.07 | 47.1 / 1.821 / -20.1 / -16.5 / 1.23 |
| A 30/70 | 54.4 / 2.149 / -16.7 / -16.2 / 1.13 | 36.6 / 1.545 / -22.4 / -20.1 / 1.06 | 47.5 / 1.823 / -20.8 / -17.1 / 1.22 |
| A 20/80 | 54.9 / 2.139 / -16.8 / -16.2 / 1.12 | 36.8 / 1.543 / -22.5 / -20.1 / 1.05 | 47.7 / 1.821 / -21.2 / -17.4 / 1.21 |
| A SPMO/QLD 50/50 | 44.8 / 2.157 / -14.4 / -13.8 / 0.94 | 31.3 / 1.576 / -20.3 / -15.5 / 0.88 | 39.9 / 1.834 / -17.4 / -14.3 / 1.00 |
| &nbsp;&nbsp;matched flat de-lever | 45.1 / 2.206 / -13.7 / -13.4 / 0.94 | 30.8 / 1.579 / -20.0 / -16.5 / 0.88 | 39.4 / 1.862 / -16.5 / -13.4 / 1.00 |
| A 0/100 QLD | 53.7 / 2.114 / -16.9 / -16.1 / 1.07 | 35.8 / 1.553 / -21.6 / -19.4 / 1.01 | 46.7 / 1.830 / -19.3 / -16.5 / 1.17 |
| &nbsp;&nbsp;matched flat de-lever | 50.8 / 2.175 / -15.7 / -15.4 / 1.07 | 34.6 / 1.557 / -21.4 / -18.8 / 1.01 | 45.1 / 1.833 / -19.1 / -15.7 / 1.17 |
| cap 1.5 | 43.2 / 2.134 / -13.9 / -13.9 / 0.92 | 29.6 / 1.528 / -21.0 / -15.8 / 0.87 | 37.3 / 1.787 / -19.0 / -15.2 / 0.99 |
| &nbsp;&nbsp;matched flat de-lever | 44.7 / 2.209 / -13.6 / -13.2 / 0.92 | 30.4 / 1.582 / -19.8 / -16.2 / 0.87 | 38.8 / 1.865 / -16.2 / -13.1 / 0.99 |
| cap 1.75 | 48.7 / 2.152 / -15.1 / -15.0 / 1.04 | 33.1 / 1.541 / -21.6 / -18.0 / 0.97 | 42.5 / 1.811 / -20.1 / -16.3 / 1.11 |
| &nbsp;&nbsp;matched flat de-lever | 49.3 / 2.183 / -15.2 / -14.9 / 1.04 | 33.4 / 1.564 / -21.0 / -18.1 / 0.97 | 43.0 / 1.844 / -18.2 / -14.9 / 1.11 |
| cap 2.25 | 57.1 / 2.151 / -17.8 / -17.1 / 1.22 | 38.7 / 1.546 / -22.1 / -21.1 / 1.14 | 50.6 / 1.820 / -20.1 / -17.7 / 1.32 |
| cap none | 58.4 / 2.162 / -18.3 / -16.7 / 1.23 | 39.8 / 1.562 / -22.1 / -21.1 / 1.15 | 52.2 / 1.840 / -20.1 / -17.2 / 1.33 |
| A-only cap 1.5 | 46.6 / 2.175 / -14.6 / -13.4 / 0.94 | 32.2 / 1.575 / -21.0 / -16.1 / 0.89 | 40.8 / 1.837 / -19.0 / -15.2 / 1.01 |
| &nbsp;&nbsp;matched flat de-lever | 45.5 / 2.205 / -13.8 / -13.5 / 0.94 | 31.0 / 1.578 / -20.1 / -16.6 / 0.89 | 39.6 / 1.861 / -16.6 / -13.5 / 1.01 |
| A-only cap 1.75 | 50.3 / 2.169 / -15.6 / -14.8 / 1.04 | 34.3 / 1.562 / -21.6 / -18.2 / 0.98 | 44.1 / 1.833 / -20.1 / -16.3 / 1.12 |
| &nbsp;&nbsp;matched flat de-lever | 49.6 / 2.182 / -15.3 / -15.0 / 1.04 | 33.7 / 1.562 / -21.1 / -18.3 / 0.98 | 43.5 / 1.842 / -18.4 / -15.0 / 1.12 |
| grid 60/40 cap 1.75 | 46.7 / 2.138 / -15.6 / -15.6 / 1.05 | 32.4 / 1.535 / -21.1 / -17.6 / 0.98 | 41.6 / 1.800 / -18.5 / -14.8 / 1.12 |
| &nbsp;&nbsp;matched flat de-lever | 49.8 / 2.181 / -15.3 / -15.0 / 1.05 | 33.7 / 1.562 / -21.1 / -18.3 / 0.98 | 43.4 / 1.842 / -18.3 / -15.0 / 1.12 |
| grid 50/50 cap 1.75 | 47.9 / 2.148 / -15.4 / -15.4 / 1.04 | 32.8 / 1.539 / -21.5 / -17.8 / 0.98 | 42.1 / 1.807 / -19.3 / -15.5 / 1.12 |
| &nbsp;&nbsp;matched flat de-lever | 49.6 / 2.182 / -15.3 / -15.0 / 1.04 | 33.6 / 1.563 / -21.1 / -18.2 / 0.98 | 43.3 / 1.843 / -18.3 / -15.0 / 1.12 |

### Cost per point (CAGR pp given up per 1 pp avoided): arm vs matched flat de-lever; DD = max drawdown, W20 = worst 20 sessions; * = arm cheaper than matched; n/a = nothing avoided

| arm | real DD | real W20 | proxy01 DD | proxy01 W20 | proxy10 DD | proxy10 W20 |
|---|---|---|---|---|---|---|
| A 100/0 | 4.43 vs 2.87 | 3.68 vs 2.80 | 3.14 vs 2.65 | 1.52* vs 1.64 | 3.09 vs 2.08 | 4.41 vs 2.46 |
| A 80/20 | 3.90 vs 2.92 | 3.99 vs 2.70 | 2.89 vs 2.58 | 1.22* vs 1.66 | 2.88 vs 2.19 | 3.33 vs 2.49 |
| A 60/40 | 4.67 vs 2.98 | 5.13 vs 2.60 | 2.27* vs 2.52 | 1.35* vs 1.71 | 2.25 vs 2.18 | 3.82 vs 2.52 |
| A SPMO/QLD 50/50 | 3.93 vs 2.92 | 3.26 vs 2.70 | 2.74 vs 2.58 | 1.18* vs 1.66 | 2.70 vs 2.19 | 3.24 vs 2.48 |
| A 0/100 QLD | n/a vs 2.98 | -0.04* vs 2.60 | 0.91* vs 2.49 | 1.14* vs 1.71 | 0.53* vs 2.15 | 9.66 vs 2.50 |
| cap 1.5 | 3.88 vs 2.91 | 4.01 vs 2.69 | 5.92 vs 2.59 | 1.65 vs 1.65 | 9.40 vs 2.19 | 7.43 vs 2.50 |
| cap 1.75 | 3.16 vs 2.97 | 3.34 vs 2.66 | 6.73 vs 2.57 | 1.75 vs 1.68 | n/a vs 2.17 | 20.55 vs 2.49 |
| A-only cap 1.5 | 3.38 vs 2.92 | 2.28* vs 2.69 | 3.64 vs 2.58 | 1.12* vs 1.66 | 6.09 vs 2.20 | 4.81 vs 2.48 |
| A-only cap 1.75 | 3.23 vs 2.97 | 1.92* vs 2.65 | 4.15 vs 2.57 | 1.20* vs 1.69 | n/a vs 2.16 | 13.36 vs 2.49 |
| grid 60/40 cap 1.75 | 6.93 vs 2.97 | 7.60 vs 2.64 | 3.70 vs 2.57 | 1.76 vs 1.69 | 3.60 vs 2.16 | 3.27 vs 2.49 |
| grid 50/50 cap 1.75 | 4.83 vs 2.97 | 5.21 vs 2.65 | 5.98 vs 2.56 | 1.78 vs 1.68 | 6.55 vs 2.16 | 4.87 vs 2.49 |

### Stress, % return (real panel; proxy 2001 for 2022 and Feb-Mar 2020 in brackets)

| arm | 2022 | Feb-Mar 2020 | 2026-11-05 | 2026-10-30..11-05 |
|---|---|---|---|---|
| A 100/0 | +12.3 [+0.0] | +11.2 [+10.6] | +10.39 | +2.73 |
| A 80/20 | +8.9 [-2.1] | +11.4 [+10.8] | +10.39 | +2.73 |
| A 60/40 | +5.6 [-4.2] | +11.6 [+11.0] | +10.39 | +2.73 |
| A 50/50 | +3.9 [-5.3] | +11.7 [+11.1] | +10.39 | +2.73 |
| LIVE A 40/60 | +2.2 [-6.3] | +11.8 [+11.2] | +10.39 | +2.73 |
| A 30/70 | +1.0 [-7.0] | +11.9 [+11.2] | +10.39 | +2.73 |
| A 20/80 | +0.3 [-7.0] | +11.9 [+11.2] | +10.39 | +2.73 |
| A SPMO/QLD 50/50 | +6.7 [-2.7] | +11.7 [+11.1] | +10.39 | +2.73 |
| A 0/100 QLD | +1.1 [-5.3] | +12.2 [+11.4] | +10.39 | +2.73 |
| cap 1.5 | +4.2 [-4.1] | +11.8 [+11.2] | +10.39 | +4.65 |
| cap 1.75 | +3.1 [-5.4] | +11.8 [+11.2] | +10.39 | +3.69 |
| cap 2.25 | +2.2 [-6.3] | +11.8 [+11.2] | +10.39 | +2.66 |
| cap none | +2.2 [-6.3] | +11.8 [+11.2] | +10.39 | +2.66 |
| A-only cap 1.5 | +4.2 [-4.1] | +11.8 [+11.2] | +10.39 | +2.73 |
| A-only cap 1.75 | +3.1 [-5.4] | +11.8 [+11.2] | +10.39 | +2.73 |
| grid 60/40 cap 1.75 | +5.6 [-4.2] | +11.6 [+11.0] | +10.39 | +3.69 |
| grid 50/50 cap 1.75 | +3.9 [-5.2] | +11.7 [+11.1] | +10.39 | +3.69 |
| matched flat(A 100/0) | +7.1 [+0.9] | +11.7 [+11.2] | +10.39 | +5.12 |
| matched flat(A 80/20) | +5.0 [-2.0] | +11.7 [+11.2] | +10.39 | +4.16 |
| matched flat(A 60/40) | +3.1 [-5.0] | +11.8 [+11.1] | +10.39 | +3.19 |
| matched flat(A SPMO/QLD 50/50) | +5.0 [-2.1] | +11.7 [+11.2] | +10.39 | +4.16 |
| matched flat(A 0/100 QLD) | +3.2 [-5.0] | +11.8 [+11.1] | +10.39 | +3.20 |
| matched flat(cap 1.5) | +5.2 [-1.7] | +11.7 [+11.2] | +10.39 | +4.24 |
| matched flat(cap 1.75) | +3.7 [-4.0] | +11.8 [+11.1] | +10.39 | +3.46 |
| matched flat(A-only cap 1.5) | +4.9 [-2.2] | +11.7 [+11.2] | +10.39 | +4.11 |
| matched flat(A-only cap 1.75) | +3.6 [-4.2] | +11.8 [+11.1] | +10.39 | +3.40 |
| matched flat(grid 60/40 cap 1.75) | +3.5 [-4.2] | +11.8 [+11.1] | +10.39 | +3.38 |
| matched flat(grid 50/50 cap 1.75) | +3.6 [-4.1] | +11.8 [+11.1] | +10.39 | +3.40 |

## Approximations, skipped, caveats
- Crack-day share: "share of the arm's total loss on all -2% days" is sum of daily book returns on crack days / on all QQQ <= -2% days; live real 16.5% (20.2% among leveraged-state -2% days), proxy01 9.4% / 12.8%.
  The earlier study's "57% of the loss on -2% days while leveraged" is not reproduced by this book-return definition; it must have been on a different basis (position/QQQ exposure) which I could not reconstruct from the files. Shares are of the summed daily returns (additive approximation).
- "Matched" de-lever: flat multiplier on the four risky legs after vol target and cap, bisected so that the average target equity-like gross over the window equals the arm's (QQQ legs included, VIXY and cash excluded); computed per window. The vol-target-lowered variant is in `run.log` (matched vt rows, "matched-vt" cost): same conclusion.
  Arms with avg gross within 0.02 of live (A 50/50, 30/70, 20/80, 2.25 cap, none) get no matched control. The flat scale also raises the cash leg and hence the VIXY/QQQ sleeves proportionally.
- Max DD and worst-20 are single-event statistics (real: one cluster, 2026-10-30..11-05 under default highs): cost-per-point ratios are unstable when little is avoided (n/a, or 13-20 on proxy10). 20 real crack days; 3 of them in unextended A.
- Gross/turnover from target weights; turnover = sum |target - held| at rebalances. Full-day highs (not 15:50) for 2026-09-08..11-10; VIXY absent before 2011; proxy leveraged legs synthetic (3x/2x - T-bill+0.3% financing - ER). A SPMO/QLD arms put the TQQQ weight on QLD at the same dollar weight (so 50/50 is 1.5x before vol target, 0/100 QLD 2.0x).
- Not done: tax lots, the 15:50-high version of L1, intraday execution, any adoption. Sensitivity blocks (L1 off, recorded highs, proxy sleeve off) are at the end of `run.log`.
