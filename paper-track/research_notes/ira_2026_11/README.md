# A separate strategy for an IRA (2026-11-19) — `ira.py`

Goal (owner): a different concept for a future IRA, using no ETF the live strategy holds (no wash-sale overlap).
Pre-registered published rules, 2007-01 -> 2026-11, adjusted closes (Yahoo), 5bp/side, monthly at month-end.

| | CAGR | Sharpe | MaxDD | worst yr | 2007-15 | 2016-26 | corr to live |
|---|---|---|---|---|---|---|---|
| C1 trend, 6 assets (SPY EFA IEF VNQ DBC GLD, 10-month avg) | 5.6% | 0.76 | -13.8% | -4.5% | 4.5% / 0.56 | 6.5% / 0.98 | 0.42 |
| **C2 momentum top-2 of 7 (SPY EFA EEM TLT GLD DBC VNQ, 6-month, beat T-bills)** | **10.3%** | 0.70 | **-22.7%** | -12.2% | 11.1% / 0.69 | 9.5% / 0.72 | **0.31** |
| C3 live rules on the S&P (2x/3x S&P) | 12.9% | 0.68 | -44.8% | -24.2% | 5.7% / 0.37 | 19.3% / 0.94 | 0.70 |
| C3b bare rules on the S&P | 14.5% | 0.72 | -40.6% | -29.8% | 13.7% / 0.70 | 15.1% / 0.74 | 0.66 |
| SPY buy & hold | 10.7% | 0.62 | -55.2% | -36.8% | 6.3% / 0.39 | 14.4% / 0.85 | 0.62 |
| live strategy (QQQ proxy, in-sample) | 36.9% | 1.54 | -22.1% | -14.0% | | | 1.00 |

50/50 household blend with the live strategy: + C2 23.7% / 1.46 / -15.4%; + C1 20.8% / 1.52 / -14.5%;
+ S&P bare 25.7% / 1.24 / -24.3%; + SPY 23.6% / 1.23 / -35.9%.
C2 is the candidate: SPY-like return at less than half SPY's drawdown, steady in both halves, the lowest
correlation to the live strategy, and monthly turnover that is costly in a taxable account but free in an IRA.
C3 is a near-duplicate of the live bet. Not implemented; no account changes.
