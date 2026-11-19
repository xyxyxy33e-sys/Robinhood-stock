# Credit spreads and rates as strategy inputs (2026-11-19)

`ctest.py` (pre-registration in its docstring; data: FRED BAA10Y, DGS10; Yahoo HYG, IEF; all lagged one session).
Bar: better Sharpe on real 2015-26, proxy 2001-26, holdout 2001-Oct15 AND untouched NDX 1987-2000, no worse max DD.

| Variant | Real | Proxy | Holdout | NDX 87-00 (exSh) |
|---|---|---|---|---|
| current (cap, sleeve off) | 45.2% 1.93 -19.3% | 31.8% 1.41 -22.1% | 22.4% 1.07 | 15.9% 0.52 -31.0% |
| A halved when Baa spread > its 100d avg (42% of days) | 41.4% 1.94 -17.5% | 29.1% 1.45 -19.1% | 20.0% 1.10 | 12.2% 0.39 -31.0% |
| D to cash when spread widening | 40.5% 1.85 | 28.0% 1.33 | 19.1% 0.98 | 18.6% 0.66 |
| A halved when 10y up >= 0.5pp in 60 sessions (12%) | 44.9% 1.96 -19.3% | 31.5% 1.42 -22.1% | 22.0% 1.08 | 16.1% 0.53 -27.0% |
| others (HYG/IEF, deep-E skips, D cash on rates, inverse credit) | all lower or equal on Sharpe in-sample |

Credit widening: helps A in all three QQQ eras (Sharpe +0.01..+0.04, DD -2..-3pp) but fails the untouched NDX
(0.52 -> 0.39); not adopted. Rates shock in A: the only variant of 13 to clear the bar, by +0.01..+0.03 Sharpe
for -0.3pp real CAGR; one pass in 13 tries (and ~60 variants tested today) is what chance produces, so it is
recorded, not adopted. 16 Nov: 10y 5.15% vs 4.69% 60 sessions earlier (+0.46pp, just under the line); spread 1.47
vs 100d 1.54 (not widening).
