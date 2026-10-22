# Re-baseline of the live design — 2026-10-22

Owner: "run the re-baseline". Script `paper-track/rebaseline_2026_10_22.py`, log
`rebaseline_2026_10_22_run.log`. One run of exactly what trades after the day's changes,
so live results are judged against one reference.

**Design:** A 40/60 SPMO/TQQQ + trim v2 (carry 3), B 75/25, C 100% SPMO, E/F cash, fast
20/100 re-entry, D gate, D ladder D1 50/50 SPMO/QLD · D2 50/50 TQQQ/QLD · D3 100% TQQQ,
20% vol target on max(10d, 30d), 5% band, 4 bp; VIXM 75% of the cash leg on the real panel
(state.vixm_series, CBOE VIX/VIX3M, Robinhood VIXM closes `data/vixm_daily.csv`).
Engine: `monte_carlo.py`, verified day by day against `state.py`; the "before today"
proxy line reproduces its verified 33.7% / 1.310 / −26.6%.

## Standing figures

| | CAGR | Sharpe | Max DD | Avg DD | 95th-pct DD | Worst 12m | −15% episodes | Longest underwater |
|---|---|---|---|---|---|---|---|---|
| **Real ETFs 2015-11..2026-08, with VIXM** (off in D2, 2026-10-22) | **47.9%** | **2.01** | **−18.4%** | −3.4% | −12.4% | −11.0% | 3 | 221 d |
| real, no VIXM | 44.5% | 1.89 | −18.4% | −3.7% | −13.7% | −12.7% | 4 | 326 d |
| real, before today (A 25/75, D3 25/75, 30d vol) | 53.9% | 1.97 | −19.3% | −4.2% | −15.0% | −13.3% | 6 | 297 d |
| QQQ / SPMO / SPY held | 18.6 / 17.5 / 12.8% | 0.88 / 0.89 / 0.77 | −35.6 / −31.3 / −34.1% | | | | | |
| **Proxy 2001–2026 (no VIXM)** | **30.4%** | **1.32** | **−24.6%** | −5.7% | −18.2% | −20.1% | 14 | 329 d |
| proxy, before today | 33.7% | 1.31 | −26.6% | −6.3% | −19.5% | −21.5% | 16 | 370 d |
| QQQ / SPY held (TR) | 11.4 / 9.2% | 0.56 / 0.56 | −70.1 / −55.3% | | | | | |
| **Holdout 2001–2015-10** | **20.8%** | **0.97** | −24.6% | −6.4% | −18.2% | −14.8% | 7 | 320 d |
| holdout, before today | 22.2% | 0.95 | −26.6% | −7.1% | −19.7% | −17.0% | 10 | 322 d |

Real panel: ~46 trades/yr, average QQQ-equivalent exposure 1.18×, time in A 68% / B 1% /
C 6% / D 14% / E 6% / F 6%, VIXM held on 9.2% of sessions. Calendar years (real, 2015 is
Nov–Dec only): 2015 −10, 2016 +15, 2017 +89, 2018 +64, 2019 +69, 2020 +36, 2021 +97,
2022 −8, 2023 +81, 2024 +77, 2025 +28, 2026 YTD +23 (%).

Updated later on 2026-10-22 for VIXM off in ungated D2 (owner): 47.7% / 2.005 → 47.9% / 2.006.

## Reading

- Today's changes trade ~6 pp real / ~3 pp proxy of CAGR for a shallower book on every
  drawdown measure, with Sharpe up on both panels and in the holdout.
- VIXM adds ~3 pp real CAGR and +0.11 Sharpe, and shortens the longest underwater stretch,
  but does not move the max drawdown. It rests on one ~10-year window and is untestable on
  the proxy (see `vixm_cash_sleeve.md`).
- These are backtests on one historical path each: the real panel is a strong-drift decade
  with one bear market; the proxy uses synthetic 2×/3× legs. Price-only on the real panel.
