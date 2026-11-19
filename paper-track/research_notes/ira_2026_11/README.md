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

## Against "buy & hold SPMO + $7,500/yr" (owner's IRA plan) — `ira2.py`

Nov 2015 -> Nov 2026, $48,241 start + $7,500 each year:
| | CAGR | Sharpe | MaxDD | ending $ |
|---|---|---|---|---|
| SPMO buy & hold | 16.8% | 0.86 | -30.9% | 521k |
| SPY / MTUM buy & hold | 13.9% / 13.6% | 0.83 / 0.70 | -33.7 / -34.1% | 405k / 383k |
| I1 rotation | 9.5% | 0.72 | -17.8% | 276k |
| I3 SSO/IEF on SPY's 200-day | 13.2% | 0.63 | -46.0% | 396k |
| I4 50/50 I1 + I3 | 12.0% | 0.77 | -27.0% | 349k |
| I5 MTUM with a 10-month filter | 7.0% | 0.46 | -37.5% | 216k |
| live rules on the S&P (SPY/SSO/UPRO, no overlap with the live ETFs) | 18.1% | 0.89 | -36.4% | 568k |
2007-2026: I4 12.0% / 0.75 / -27% and I1 10.3% / 0.70 / -22.7% vs SPY 10.7% / 0.62 / -55%; S&P live rules
12.9% / 0.68 / -44.8% (only 5.7% in 2007-15).
No diversified design beats SPMO's exceptional decade on money; they beat it on drawdown. Only the leveraged
regime rules (live strategy, or its S&P twin) out-earned it, the twin by a thin, era-dependent margin.

## Simple S&P trend rules vs S&P 500 total return, 1951-2026 — `spx.py` (owner: "simpler S&P version, beat SPY")

CAGR / excess Sharpe / max DD (same-session execution):
| | 1951-2026 | 1951-89 | 1990-2026 | 2007-26 |
|---|---|---|---|---|
| S&P 500 total return | 11.4 / 0.50 / -55% | 12.0 / 0.52 / -45% | 10.8 / 0.50 / -55% | 10.5 / 0.53 / -55% |
| S1 200-day, 1x | 11.1 / 0.67 / -20% | 13.1 / 0.80 | 9.1 / 0.57 | 8.3 / 0.61 |
| **S2 200-day, 2x** | **15.5 / 0.60 / -39%** | **18.6 / 0.73** | **12.3 / 0.50** | **12.1 / 0.54** |
| S3 200-day + vol target (max 2x) | 12.3 / 0.56 / -27% | 16.0 / 0.72 | 8.6 / 0.42 | 8.7 / 0.50 |
| S4 simple live (2x / 1x by 50/200, vol target) | 13.4 / 0.58 / -38% | 17.5 / 0.77 | 9.3 / 0.42 | 9.7 / 0.51 |
S2 beats S&P total return on CAGR in every era with equal or better Sharpe and a shallower max DD; beats it in
45 of 76 years; ~2.5 switches a year; one session late: 14.5% / -61.5% over 1951-2026 (1987), 12.4% / -40.5% since
1990. Its edge since 1990 is leverage plus drawdown control (Sharpe ties), larger before 1990. It does not beat
SPMO's 2015-26 decade (SSO/IEF variant 13.2% vs 16.8%).
