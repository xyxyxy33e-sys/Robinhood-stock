# Monte Carlo study, current design vs simpler versions, with crashes (2026-11-19)

`mc_study.py` (pre-registration in the docstring), `mc_study_run.log`, `mc_study.json`. 500 paths x 10 years per
cell. VIXY sleeve and the QQQ cash legs not modelled (understates current by roughly 2-5 pp on real ETFs).

Findings
1. Planning range (median 10-year CAGR / median max DD, current design): holdout bootstrap block 60-120
   7.7-10.6% / -33..-37% (with a crash 6.5-8.4%); proxy 11.5-15.7%; real ETFs 19.3-26.9%. 5th pct CAGR
   -2.2..+1.1% on the holdout. QQQ on the same paths: 4.2-4.9% holdout, 9.1-9.5% proxy, ~18% real.
2. On reshuffled QQQ history (all three panels, block >= 60) the current design has the best Sharpe and the
   shallowest drawdowns of the four, ~8-12 pp shallower than no-trim; it beats QQQ on 57-99% of paths. A crash
   widens its lead.
3. Random walk (no trends): no design beats QQQ (Sharpe 0.55-0.57 vs 0.67): no look-ahead; the cost of the
   machinery in a trendless world is ~0.1 Sharpe and ~3 pp CAGR.
4. Bull/bear regime worlds (no blow-off tops): current trails no-trim / bare / simple by 5-12 pp CAGR and
   0.02-0.17 Sharpe at every trend length, with 7-9 pp shallower drawdowns. Short blocks (20) on real history
   show the same.
5. Reading: trim v2 is a bet that stretched markets fall back hard. It pays in QQQ's own history (2000, 2018,
   2020, 2022, and in bootstraps of 1999-2015 that never fit it) and costs in steady trends (synthetic bulls,
   NDX 1987-2000, Nikkei, DAX). Simple and bare are about equal to each other everywhere.
No live change.
