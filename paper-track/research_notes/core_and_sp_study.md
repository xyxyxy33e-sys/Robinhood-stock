# VGT as the core; an S&P version on VOO / SPXL / SSO / SPXS (2026-10-30)

**Question and method.**
- Owner: "test if vgt is a better core"; "the sp version with voo spxl spxs". This was prompted by alphaAI's VGT-based Leveraged Nasdaq and its Leveraged S&P. Research only.
- Script `core_and_sp_study.py` (pre-registered); output `core_and_sp_study_run.log`.
- Data: Yahoo split-adjusted closes `data/*_yahoo_daily.csv`. The 29 Oct closes match Robinhood. TQQQ/QLD match the repo files to 5e-6 a day on average.
- Returns: price returns plus a flat dividend accrual per core (SPMO 0.8%, VGT/QQQ 0.6%, VOO 1.3%).
- Live design incl. the 0.5% zone buffer; VIXM out.

**Main results, 4 bp per side** (20 bp in the log, same ordering):

| arm | real 2015-11..2026-10 | real 2010-06..2026-10 | synthetic 2005..2026 |
|---|---|---|---|
| Nasdaq, SPMO core (live) | **44.3% / 1.860 / −18.4%** | — | — |
| Nasdaq, VGT core | 45.8% / 1.786 / −21.2% | 39.4% / 1.531 / −22.4% | 33.6% / 1.374 / −22.1% |
| Nasdaq, QQQ core | 44.3% / 1.768 / −21.8% | 39.0% / 1.533 / −22.4% | 33.1% / 1.366 / −22.2% |
| S&P: SPY signals, VOO/SPXL/SSO | 18.3% / 0.902 / −34.6% | 17.2% / 0.841 / −36.6% | 12.3% / 0.654 / −37.3% |
| S&P + 100% SPXS in F | 15.8% / 0.708 / −46.5% | 11.2% / 0.545 / −54.4% | 9.3% / 0.466 / −54.3% |
| S&P legs, QQQ signals | 29.1% / 1.641 / −14.8% | 25.5% / 1.327 / −24.6% | 21.1% / 1.137 / −28.1% |

**Buy-and-hold reference, real 2015-11..2026-10** (CAGR / Sharpe / max DD):

| hold | |
|---|---|
| QQQ | 18.9% / 0.892 / −35.2% |
| VGT | 22.6% / 0.958 / −35.1% |
| VOO | 14.1% / 0.833 / −34.2% |
| TQQQ | 35.0% / 0.790 / −81.8% |
| SPXL | 26.0% / 0.707 / −76.9% |

**Findings.** Nothing passes.
- **VGT core: fail.** It earns 1.4 pp a year more than SPMO but has lower Sharpe (−0.074 at 4 bp, −0.060 at 20 bp) and a 2.8 pp deeper max drawdown.
- **VGT behaves like QQQ.** Over the longer windows it ties the QQQ core (−0.002 / +0.008). VGT and QQQ are concentrated in the same names as TQQQ, so in a tech selloff the core falls with the leveraged sleeve. SPMO is S&P momentum, less correlated with the TQQQ sleeve, and that is where its Sharpe edge comes from.
- **S&P version: fail by a wide margin.** On its own signals it barely beats holding VOO on Sharpe. The S&P trends less cleanly than the Nasdaq-100, so the 50/200 classifier whipsaws. Its lower volatility also means the 20% vol target rarely cuts the 3x leg.
  - Fair caveat: every parameter here was fit on QQQ. A real S&P design would need its own tuning, and this test does not search for one.
- **SPXS in F is worse again,** as in `sqqq_hedge_study.py`.
- **S&P legs on QQQ signals** have the shallowest 2015–2026 drawdown (−14.8%) but give up 15 pp of CAGR, and their drawdown is deeper than the Nasdaq design's in the longer windows.
- **Conclusion:** keep SPMO / TQQQ / QLD on QQQ signals.
