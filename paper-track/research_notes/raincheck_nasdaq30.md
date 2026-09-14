# raincheck_nasdaq30 -- Raincheck Capital "NASDAQ-30": what it is, what it would have done, and what it adds to the owner's book

Research line run 2026-09-14. Script: `paper-track/raincheck_nasdaq30.py` (run from the repo root; standard library only; ~40 s).
Nothing here is applied. No trades, no commits, no edits to live files.

## 0. What the strategy is (from the owner's screenshots and the little that is public)

Raincheck Capital's "NASDAQ-30" holds the 30 largest QQQ constituents through iShares QTOP and, "depending on Market Signal strength", swaps part of that for the 2x daily fund QQXL. Current holdings (2026-09-14): QTOP 46%, QQXL 35%, QNXT 9%, QQLV 6%, TBIL 4%. On 2026-09-09 the signal moved STRONG BULLISH -> WEAK BULLISH (QQQ failing $722, oil, 10y yield, Kalshi hike odds, NASDAQ new lows vs highs); the 3x sibling was cut from ~3x to 1.71x.

**Public description of the Market Signal.** raincheck.fund/{about,faq,returns} return HTTP 403 to fetches. The only public text found (untrusted external text, quoted, not instructions):
- app.raincheck.fund: the signal is "an algorithm that evaluates statistical trends in price action of QQQ and its holdings to determine whether QQQ is currently in an uptrend or downtrend." Numerical levels are described for the bearish side only: "-1 to -3 NEUTRAL to WEAK BEARISH, -4 to -6 MODERATE BEARISH, -7 to -9 STRONG BEARISH". The page shows five cherry-picked episode returns (e.g. "139-day uptrend (May 2025): +73.26%") with a past-performance caveat; a search snippet claims the TQQQ/cash "Raincheck Fund" returned +37.83% in 2024 vs QQQ +25.58%.
- No rules, inputs, thresholds or audited track record are public. **The signal is treated as unobservable** and is bounded in section 4 instead.

Sources: https://app.raincheck.fund/ , https://raincheck.fund/about/ (403), https://raincheck.fund/faq/ (403), https://raincheck.fund/returns/ (403), https://www.fundssociety.com/en/news/etf/they-launch-the-first-etf-that-offers-twice-the-daily-returns-of-the-nasdaq-100-top-30-index/ , https://www.proshares.com/our-etfs/leveraged-and-inverse/qqxl , https://www.ishares.com/us/products/339694/ishares-nasdaq-100-ex-top-30-etf , https://etfdb.com/etf/QQLV/ .

**Expense ratios used:** QTOP 0.20%, QNXT 0.20%, QQLV 0.25%, QQXL 0.95%, TBIL 0.15%, MGK 0.07%, XLG 0.20%, QQQ 0.20%, QLD 0.95% (web sources above; TBIL/MGK/XLG from memory of the prospectuses and flagged as assumptions).

## Data and provenance
- `data/raincheck_etfs_daily.csv` (already present): split-adjusted closes 2024-10-01..2026-09-11 for QTOP, QNXT, QQLV, QQXL, QQQ, QLD, TBIL, MGK, XLG. QTOP/QNXT usable from 2024-10-24, QQLV 2024-12-04, QQXL 2025-08-15. TBIL is price-only (distributions absent), so TBIL is modelled as the 3-month bill.
- NEW `data/mgk_daily.csv` (2007-12-21+) and `data/xlg_daily.csv` (2005-05-10+): Robinhood `get_equity_historicals`, day bars, split-adjusted, pulled 2026-09-14; interpolated bars dropped. Provenance appended to `data/README.md`.
- Harness rows: `exec(open('paper-track/leverage_under_trim.py').read().split('rr=RF.real_rows()')[0])` -- the daily QQQ-core proxy rows 2000-07-03..2026-08-26 (n=6575) with legs (QQQ TR, 3x synthetic, 2x synthetic with 0.95% ER + financing, XLU TR, bill). The real weekly SPMO rows need `/home/user/robinhood/data/kairos`, which is not on this machine; they are not needed for this line.
- Live reproduction check passed: 22.18% / 0.913 / -33.6%, search 1.103, holdout 0.768 (standing figures per the ADDENDUM).

## Method in one paragraph
Every portfolio figure is produced by the harness `run()` (4bp one-way on L1 turnover, `state.REBALANCE_DRIFT_BAND` = 5% drift band, so the "static" mix is drift-band rebalanced, not free). The NASDAQ-30 book is mapped onto harness legs as QTOP -> QQQ total-return core, QQXL -> the daily-reset 2x leg (its 0.95% ER equals QQXL's), QNXT -> core (the QNXT-vs-QQQ residual is reported separately in section 1), QQLV -> 0.18 x core + 0.82 x bill (its measured beta, which happens to equal Raincheck's quoted 0.18), TBIL -> bill; the residual ER not already inside the legs (0.014%/yr) is deducted daily. That gives harness weights (core 0.561, QLD 0.35, cash 0.089), proxy beta 1.26 (Raincheck's own beta arithmetic gives 1.32 because QTOP/QQXL carry 1.05/2.15 betas to QQQ). A second row set swaps in MGK for the mega-cap sleeve (MGK TR with 0.5%/yr dividend, daily-reset 2x MGK synthetic, extra 13bp ER for QTOP vs MGK) on identical dates from 2007-12-21. Sharpe is the harness convention (mean/vol, no risk-free deduction). Controls: exposure-matched constant-beta QQQ line found by bisection for every rule in section 4, sign-flipped placebo, search/holdout split, circular block bootstrap (20/60d) for the mix-vs-live comparison.

## 1. Proxy validation (daily returns, overlap window)

| pair | window | n | beta | corr | TE (ann) | ann ret A | ann ret B | A-B ann |
|---|---|---|---|---|---|---|---|---|
| QTOP vs QQQ | 2024-10-24..2026-09-11 | 470 | 1.053 | 0.992 | 3.26% | +24.9% | +22.1% | +2.7% |
| QTOP vs MGK | 2024-10-24..2026-09-11 | 470 | 1.032 | 0.963 | 6.33% | +24.9% | +18.6% | +6.3% |
| QTOP vs XLG | 2024-10-24..2026-09-11 | 470 | 1.217 | 0.952 | 8.21% | +24.9% | +15.4% | +9.5% |
| QNXT vs QQQ | 2024-10-24..2026-09-11 | 470 | 0.777 | 0.888 | 10.16% | +11.7% | +22.1% | -10.4% |
| QQLV vs QQQ | 2024-12-04..2026-09-11 | 442 | 0.177 | 0.308 | 22.14% | -0.3% | +19.5% | -19.7% |
| QQXL vs QTOP x2.00 | 2025-08-15..2026-09-11 | 269 | 0.986 | 0.996 | 3.65% | +35.2% | +45.3% | -10.1% |
| QQXL vs QQQ | 2025-08-15..2026-09-11 | 269 | 2.155 | 0.988 | 23.15% | +35.2% | +22.2% | +13.1% |
| QLD vs QQQ x2.00 | 2024-10-01..2026-09-11 | 487 | 0.993 | 1.000 | 1.05% | +36.7% | +43.7% | -7.0% |
| MGK vs QQQ | 2024-10-01..2026-09-11 | 487 | 0.961 | 0.969 | 5.44% | +19.8% | +22.7% | -2.9% |
| XLG vs QQQ | 2024-10-01..2026-09-11 | 487 | 0.796 | 0.957 | 6.89% | +16.4% | +22.7% | -6.4% |
| QTOP vs QNXT | 2024-10-24..2026-09-11 | 470 | 1.010 | 0.831 | 13.05% | +24.9% | +11.7% | +13.2% |
| TBIL price-only vs DGS3MO accrual | 2024-10-01..2026-09-11 | 487 | - | - | 1.17% | +0.07% | +4.21% | price series excludes ~monthly distributions; TBIL modelled as the bill |

Reading: QTOP is QQQ with a 1.05 beta, 0.99 correlation and 3.3% tracking error; the long-history proxy that best represents it is **QQQ itself** (MGK 0.96 corr / 6.3% TE; XLG 0.95 / 8.2% TE and only 0.80 beta to QQQ because it is S&P-weighted and holds financials/health care). QNXT (holdings 31-100) is a 0.78-beta, 0.89-correlation slice that lagged QQQ by 10%/yr over the window, so mapping QNXT -> QQQ overstates that 9% sleeve by roughly 0.9%/yr of book return in a year like the last two. QQLV is essentially not a QQQ instrument (beta 0.18, corr 0.31, -0.3%/yr). QQXL tracks 2 x QTOP daily with beta 0.99 and corr 0.996; over its 13 months it returned +35.2% vs +45.3% for 2 x QTOP's daily return compounded -- the -10%/yr gap is the daily-reset path cost plus 0.95% ER plus financing, exactly what the harness 2x leg models (QLD vs 2 x QQQ: -7.0%/yr over the same window).

Concentration residual by month:

| month | QTOP | QQQ | QNXT | QTOP-QQQ | QTOP-QNXT |
|---|---|---|---|---|---|
| 2024-11 | +5.2% | +5.4% | +5.8% | -0.2% | -0.6% |
| 2024-12 | +2.4% | +0.3% | -6.8% | +2.1% | +9.2% |
| 2025-01 | +0.9% | +2.2% | +5.7% | -1.2% | -4.8% |
| 2025-02 | -2.7% | -2.7% | -1.6% | +0.0% | -1.0% |
| 2025-03 | -8.0% | -7.7% | -6.5% | -0.3% | -1.5% |
| 2025-04 | +1.4% | +1.4% | +1.5% | +0.0% | -0.1% |
| 2025-05 | +10.2% | +9.2% | +5.5% | +1.0% | +4.7% |
| 2025-06 | +6.5% | +6.3% | +5.2% | +0.3% | +1.4% |
| 2025-07 | +3.3% | +2.4% | -0.4% | +0.8% | +3.7% |
| 2025-08 | +1.4% | +1.0% | -0.8% | +0.5% | +2.3% |
| 2025-09 | +5.1% | +5.3% | +6.8% | -0.2% | -1.7% |
| 2025-10 | +5.6% | +4.8% | +0.9% | +0.8% | +4.6% |
| 2025-11 | -2.3% | -1.6% | -1.9% | -0.8% | -0.5% |
| 2025-12 | -0.3% | -0.8% | -0.1% | +0.5% | -0.1% |
| 2026-01 | +1.3% | +1.2% | +1.0% | +0.1% | +0.3% |
| 2026-02 | -3.4% | -2.3% | +0.3% | -1.0% | -3.7% |
| 2026-03 | -4.3% | -5.0% | -6.1% | +0.6% | +1.8% |
| 2026-04 | +17.5% | +15.7% | +9.7% | +1.8% | +7.8% |
| 2026-05 | +11.0% | +10.6% | +8.0% | +0.4% | +3.0% |
| 2026-06 | -1.1% | -0.3% | +1.4% | -0.8% | -2.5% |
| 2026-07 | -7.2% | -6.6% | -2.7% | -0.7% | -4.5% |
| 2026-08 | +4.1% | +4.2% | +3.7% | -0.0% | +0.4% |
| 2026-09 | +0.8% | -0.3% | -4.1% | +1.1% | +4.9% |

QTOP beat QQQ in 14/23 months, beat QNXT in 12/23 months; cumulative QTOP +51.3% vs QQQ +45.2% vs QNXT +22.9% (2024-10-24..2026-09-11).

## 2. The top-30 concentration premium

| year | XLG | QQQ | SPY | XLG-QQQ | XLG-SPY | MGK | MGK-QQQ | MGK-SPY |
|---|---|---|---|---|---|---|---|---|
| 2005 | +2.8% | +13.0% | +6.8% | -10.2% | -4.0% | - | - | - |
| 2006 | +15.9% | +6.8% | +13.7% | +9.1% | +2.1% | - | - | - |
| 2007 | +2.4% | +18.7% | +3.2% | -16.2% | -0.8% | -1.0% | +0.2% | +0.2% |
| 2008 | -35.4% | -41.9% | -38.3% | +6.5% | +2.9% | -36.9% | +5.0% | +1.3% |
| 2009 | +17.1% | +53.8% | +23.5% | -36.7% | -6.4% | +32.9% | -21.0% | +9.4% |
| 2010 | +7.1% | +19.0% | +12.8% | -12.0% | -5.8% | +13.1% | -6.0% | +0.2% |
| 2011 | +2.0% | +2.5% | -0.2% | -0.5% | +2.2% | +1.6% | -0.9% | +1.8% |
| 2012 | +12.8% | +16.7% | +13.5% | -3.9% | -0.7% | +15.3% | -1.4% | +1.8% |
| 2013 | +26.1% | +35.1% | +29.7% | -9.0% | -3.6% | +30.7% | -4.4% | +1.0% |
| 2014 | +9.1% | +17.4% | +11.3% | -8.3% | -2.2% | +12.1% | -5.3% | +0.8% |
| 2015 | +2.0% | +8.3% | -0.8% | -6.3% | +2.8% | +2.2% | -6.2% | +3.0% |
| 2016 | +9.0% | +5.9% | +9.6% | +3.0% | -0.7% | +4.9% | -1.0% | -4.7% |
| 2017 | +20.6% | +31.5% | +19.4% | -10.8% | +1.2% | +27.8% | -3.7% | +8.4% |
| 2018 | -5.4% | -1.0% | -6.3% | -4.4% | +1.0% | -3.9% | -2.9% | +2.5% |
| 2019 | +29.5% | +37.6% | +28.5% | -8.1% | +1.0% | +35.9% | -1.7% | +7.4% |
| 2020 | +22.5% | +47.8% | +16.4% | -25.3% | +6.1% | +40.1% | -7.7% | +23.7% |
| 2021 | +29.4% | +26.8% | +27.0% | +2.6% | +2.3% | +28.0% | +1.2% | +0.9% |
| 2022 | -25.2% | -33.1% | -19.5% | +7.8% | -5.7% | -34.0% | -0.9% | -14.5% |
| 2023 | +36.7% | +53.8% | +24.3% | -17.1% | +12.4% | +50.8% | -3.0% | +26.5% |
| 2024 | +32.4% | +24.8% | +23.3% | +7.6% | +9.1% | +32.3% | +7.5% | +9.0% |
| 2025 | +18.7% | +20.2% | +16.4% | -1.5% | +2.3% | +20.2% | +0.0% | +3.8% |
| 2026 | +5.7% | +17.4% | +13.1% | -11.7% | -7.4% | +9.6% | -7.8% | -3.5% |

| series | window | CAGR | vol | Sharpe | MaxDD | notes |
|---|---|---|---|---|---|---|
| MGK | 2007-12-21..2026-08-27 | +13.05% | 21.1% | 0.686 | -48.6% | div 0.5%/yr assumed |
| QQQ | 2007-12-21..2026-08-27 | +15.87% | 22.3% | 0.771 | -51.0% | div 0.6%/yr assumed |
| SPY | 2007-12-21..2026-08-27 | +10.91% | 19.9% | 0.620 | -53.6% | div 1.5%/yr assumed |
| XLG | 2005-05-10..2026-08-27 | +10.63% | 18.7% | 0.633 | -53.1% | div 1.0%/yr assumed |
| QQQ | 2005-05-10..2026-08-27 | +15.88% | 21.7% | 0.789 | -53.3% | div 0.6%/yr assumed |
| SPY | 2005-05-10..2026-08-27 | +10.95% | 19.1% | 0.639 | -55.5% | div 1.5%/yr assumed |

MGK beat QQQ in 4 of 19 full calendar years 2008-2025.
  2007-12-21..2022-12-31: MGK +8.52%  QQQ +11.53%  SPY +6.53%  (price CAGR)
  2023-01-01..2026-09-11: MGK +30.74%  QQQ +31.82%  SPY +21.45%  (price CAGR)
  2005-05-10..2022-12-31: XLG +6.52%  QQQ +12.07%  SPY +6.97%  (price CAGR)
  2023-01-01..2026-09-11: XLG +25.54%  QQQ +31.82%  SPY +21.45%  (price CAGR)

Reading: over the long window mega-cap concentration is **not** a premium over QQQ. MGK lost to QQQ in 15 of 19 calendar years 2008-2025 and compounds 2.8%/yr slower with the same drawdown; XLG lost to QQQ by 5.3%/yr over 21 years. Both beat SPY, but that is the growth/tech tilt, not the "top 30". The only stretch in which "the largest 30" beat QQQ is 2024 (+7.5%) and the QTOP window 2024-10..2026-09 (+2.7%/yr, driven by 2024-12 and 2026-04); in 2026 YTD MGK and XLG are 8-12% behind QQQ. Against the NEXT 70 (QNXT) the top-30 premium is very large in the same window (+13%/yr, 12/23 months), which is the breadth collapse the repo has documented elsewhere -- a 2023-2026 phenomenon of the AI-capex leaders, not a persistent factor. Conclusion: QTOP is a QQQ beta sleeve; expect its excess over QQQ to be zero-mean with 3% tracking error, with a fat-tailed 2020-style reversal risk (XLG -25% vs QQQ in 2020) when leadership broadens.

## 3. Static-mix backtest of the current holdings (46/35/9/6/4)

QQLV stand-in: measured daily beta to QQQ 0.18 (corr 0.31) on 2024-12-04..2026-09-11; Raincheck quotes 0.18. Modelled as 0.18 x QQQ-core + 0.82 x bill. 6% of the book, so any stand-in moves book beta by < 0.05.
Residual expense drag not already inside the harness legs: 0.014%/yr (applied daily).
Harness weights (core, TQQQ, QLD, XLU, cash) = (0.561, 0.0, 0.35, 0.0, 0.089); proxy beta 1.26 (Raincheck's own beta-weighted figure with QTOP 1.05 / QQXL 2.15 / QNXT 0.78 / QQLV 0.18: 1.32).

Harness rows 2000-07..2026-08 (n=6575); costs: 4bp one-way, 5% L1 drift band, lev2 leg = daily-reset 2x QQQ with 0.95% ER + financing at bill+spread.

| strategy | CAGR | vol | Sharpe | MaxDD | worst yr | 2008 | 2020 | 2022 | avg deployed | avg nominal beta (w x leg beta) |
|---|---|---|---|---|---|---|---|---|---|---|
| NASDAQ-30 static mix (46/35/9/6/4) | +8.68% | 32.3% | 0.419 | -88.6% | 2000 -53.5% | -47.3% | +52.8% | -42.3% | 0.91 | 1.26 |
| QQQ buy-and-hold | +8.72% | 25.6% | 0.454 | -80.2% | 2000 -43.7% | -38.1% | +44.0% | -33.8% | 1.00 | 1.00 |
| constant 1.26x QQQ (core+lev2, same rows) | +8.98% | 32.3% | 0.427 | -88.4% | 2000 -53.5% | -47.1% | +54.3% | -42.1% | 1.00 | 1.26 |
| constant 1.30x QQQ (core+lev2) | +8.91% | 33.3% | 0.423 | -89.4% | 2000 -54.9% | -48.6% | +55.6% | -43.4% | 1.00 | 1.30 |
| LIVE design (harness run) | +22.18% | 25.5% | 0.913 | -33.6% | 2022 -27.2% | -13.5% | +33.3% | -27.2% | 0.68 | 1.27 |

LIVE reproduction check: 22.18% / 0.913 / -33.6%  search 1.103 holdout 0.768 (standing: 22.18% / 0.913 / -33.6%, 1.103, 0.768).

MGK window 2007-12-21..2026-08-25 (n=4694, rows dropped where MGK has no bar: 2). QTOP->MGK total return (0.5%/yr div assumed), QQXL->daily-reset 2x MGK (0.95% ER), QNXT->MGK (residual noted in section 1), QQLV->0.18x MGK + bill, TBIL->bill. Extra ER drag 0.074%/yr.

| strategy | CAGR | vol | Sharpe | MaxDD | worst yr | 2008 | 2020 | 2022 | avg deployed | avg nominal beta (w x leg beta) |
|---|---|---|---|---|---|---|---|---|---|---|
| NASDAQ-30 mix on MGK legs | +14.37% | 26.6% | 0.638 | -58.6% | 2022 -43.6% | -42.9% | +43.1% | -43.6% | 0.91 | 1.26 |
| NASDAQ-30 mix on QQQ legs (same dates) | +17.98% | 28.2% | 0.728 | -60.5% | 2008 -47.3% | -47.3% | +52.9% | -42.3% | 0.91 | 1.26 |
| MGK buy-and-hold | +12.85% | 21.1% | 0.678 | -48.6% | 2022 -34.8% | -33.9% | +36.6% | -34.8% | 1.00 | 1.00 |
| QQQ buy-and-hold | +15.68% | 22.3% | 0.764 | -51.0% | 2008 -38.1% | -38.1% | +44.0% | -33.8% | 1.00 | 1.00 |
| constant 1.26x MGK | +14.79% | 26.6% | 0.652 | -58.2% | 2022 -43.3% | -42.4% | +44.3% | -43.3% | 1.00 | 1.26 |
| LIVE design (QQQ legs, same dates) | +24.81% | 26.3% | 0.977 | -33.6% | 2022 -27.2% | -13.5% | +33.3% | -27.2% | 0.72 | 1.36 |

Reading: held statically the book is a 1.26x QQQ line and behaves like one: on the 26-year rows it adds nothing over QQQ buy-and-hold (8.68% vs 8.72% CAGR, Sharpe 0.42 vs 0.45) while widening the worst drawdown from -80% to -89% and the worst year from -44% to -54%. The "constant 1.26x" row is 0.3%/yr better than the mix only because the mix keeps 8.9% in bills (drag in a bull market). On the 2007-12+ window the QQQ-legged mix earns 18.0% vs 15.7% for QQQ, i.e. the classic leverage-in-a-bull-market pickup, with Sharpe LOWER (0.73 vs 0.76) and MDD -60% vs -51%. On MGK legs the mix is worse still (14.4%, -59%) because MGK itself trailed QQQ. The live design on identical rows: 22.2% / 0.913 / -33.6% (26y) and 24.8% / 0.977 / -33.6% (2007-12+), i.e. +6.8 to +10.4 points of CAGR at a third of the drawdown, deploying 68-72% on average.

## 4. The managed-leverage question

The Market Signal is discretionary and unobservable, so it is bracketed. Rungs are constant-beta QQQ lines {STRONG 2.15, WEAK 1.30, NEUTRAL 1.05, OFF 0.18} built from the harness legs; each rule is switched by a causal feature known at the close of d0; each is compared to a constant-beta QQQ line with the same average nominal beta (bisection) and to its sign-flipped version.

Ladder rungs (proxy beta): STRONG 2.15 (0.15 lev3 + 0.85 lev2), WEAK 1.30 (0.30 lev2 + 0.70 core), NEUTRAL 1.05, OFF 0.18 (0.18 core + 0.82 bill).
Each rule is a constant-beta line switched by a causal QQQ feature known at the close of d0; costs/drift band inside harness run().

| rule | CAGR | vol | Sharpe | MaxDD | worst yr | 2008 | 2020 | 2022 | avg beta | switches/yr | matched const beta: CAGR / Sharpe / MDD | Sharpe edge vs matched | flipped Sharpe |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| (a) PERFECT FORESIGHT next-month sign | +95.19% | 34.8% | 2.098 | -33.5% | 2000 +23.6% | +61.0% | +276.1% | +42.6% | 1.36 | 5.6 | +8.85% / 0.418 / -90.7% | +1.680 | nan |
| (b1) price vs 50d/200d (4 rungs) | +13.22% | 30.5% | 0.561 | -69.6% | 2022 -33.4% | -24.2% | +65.4% | -33.4% | 1.55 | 21.4 | +8.66% / 0.407 / -93.9% | +0.153 | 0.131 |
| (b2) live 50/200 classifier A..F | +17.25% | 31.6% | 0.663 | -63.1% | 2000 -44.1% | -13.4% | +72.1% | -32.7% | 1.56 | 12.3 | +8.64% / 0.407 / -94.0% | +0.256 | 0.068 |
| (b3) 20d & 60d momentum sign | +9.85% | 30.3% | 0.463 | -87.1% | 2001 -49.1% | -13.5% | +68.6% | -22.8% | 1.45 | 32.6 | +8.82% / 0.413 / -92.4% | +0.050 | 0.162 |
| (b4) 20d momentum sign (2 rungs) | +9.86% | 32.6% | 0.453 | -93.4% | 2001 -59.1% | -9.9% | +98.3% | -17.1% | 1.40 | 22.1 | +8.84% / 0.415 / -91.6% | +0.038 | 0.152 |
| (b5) key level: 20d breakout/breakdown | +10.83% | 30.7% | 0.490 | -73.0% | 2022 -31.3% | -7.4% | +65.1% | -31.3% | 1.35 | 12.8 | +8.85% / 0.418 / -90.6% | +0.071 | 0.183 |
| static 46/35/9/6/4 mix | +8.68% | 32.3% | 0.419 | -88.6% | 2000 -53.5% | -47.3% | +52.8% | -42.3% | 1.26 | 0 | +8.98% / 0.427 / -88.4% | -0.008 | - |
| LIVE design (reference) | +22.18% | 25.5% | 0.913 | -33.6% | 2022 -27.2% | -13.5% | +33.3% | -27.2% | 1.27 | - | +8.98% / 0.427 / -88.6% | +0.486 | - |

Both-era check (Sharpe): search 2015-11+ / holdout 2000-07..2015-10, rule vs its matched constant-beta line

| rule | search rule | search matched | holdout rule | holdout matched |
|---|---|---|---|---|
| (b1) price vs 50d/200d (4 rungs) | 0.913 | 0.839 | 0.296 | 0.170 |
| (b2) live 50/200 classifier A..F | 0.914 | 0.839 | 0.487 | 0.169 |
| (b3) 20d & 60d momentum sign | 0.899 | 0.845 | 0.173 | 0.171 |
| (b4) 20d momentum sign (2 rungs) | 0.974 | 0.849 | 0.135 | 0.173 |
| (b5) key level: 20d breakout/breakdown | 0.891 | 0.851 | 0.239 | 0.180 |

Candidate count in (b): 5 mechanical rules, no parameter sweeps; 1 perfect-foresight bound.

(c) The one observed Market Signal action: 2026-09-09 STRONG BULLISH -> WEAK BULLISH (3x sibling cut to 1.71x).
NASDAQ-30 book 2026-09-09 close -> 2026-09-11 close using the actual ETF closes (holdings frozen at 46/35/9/6/4, no rebalance):

| leg | weight | 09-09 | 09-10 | 09-11 | 09-09->09-11 | contribution |
|---|---|---|---|---|---|---|
| QTOP | 46% | 37.620 | 37.225 | 37.614 | -0.02% | -0.01% |
| QQXL | 35% | 54.981 | 53.835 | 54.912 | -0.13% | -0.04% |
| QNXT | 9% | 30.667 | 30.352 | 30.515 | -0.50% | -0.04% |
| QQLV | 6% | 24.742 | 24.675 | 24.808 | +0.27% | +0.02% |
| TBIL | 4% | 49.910 | 49.910 | 49.920 | +0.02% | +0.00% |
| **book** | 100% | | | | **-0.08%** | vs QQQ -0.20%; QQQ 09-10 -1.06%, 09-11 +0.87% |
Two sessions after the downgrade the book did +0.12% relative to QQQ: a 1.3x book on a flat two days; the signal change itself had no measurable consequence in this window.

Reading:
- **(a) Perfect foresight** of next month's QQQ sign turns the ladder into a 95% CAGR / Sharpe 2.1 machine with -33% MDD, +61% in 2008 and +43% in 2022. That is the ceiling on what "managed leverage" can be worth: the whole value of the strategy lives in the signal, none of it in the holdings.
- **(b) Mechanical proxies** a discretionary manager plausibly tracks add a Sharpe of +0.04 to +0.26 over their matched constant-beta line on the 26-year rows, and every one of them LOSES when flipped (0.07-0.18 vs 0.45-0.66), so trend-following the QQQ 50/200 is a real, small signal -- which is precisely what the owner's live design already is. The best mechanical ladder (b2, the live classifier states mapped to leverage rungs) reaches 17.3% / 0.663 / -63%; the live design on the same rows is 22.2% / 0.913 / -33.6% because it holds 68% deployed on average rather than a 1.56 nominal beta and scales by vol. The both-era table shows the ladders' edge over the matched line survives in search (0.05-0.13) and, for the 50/200 family, in holdout (+0.13, +0.32); the 20d-momentum and 20d-breakout variants have no holdout edge (0.135-0.239 vs 0.17-0.18). None of the five is worth pursuing as an idea: they are all worse than the live design and the count is 5 rules / 0 sweeps.
- **The static 46/35/9/6/4 mix carries none of this**: it is a 1.26x line, Sharpe edge -0.008 vs its matched line, and worst drawdown -89%. Whatever the manager's timing is worth, it has to be earned entirely by moving QQXL up and down; the owner cannot verify that from public information and the one observed action (below) is uninformative.
- **(c) The known switch** (STRONG -> WEAK BULLISH on 2026-09-09): the NASDAQ-30 book's actual closes give -0.08% for 09-09 -> 09-11 vs QQQ -0.20% (QQQ -1.06% then +0.87%). Nothing to learn from two flat sessions; note that the NASDAQ-30 mix is still 35% QQXL, i.e. ~1.3x, AFTER the downgrade.

## 5. Leveraged-ETF mechanics

| year | QQQ TR | 2x daily-reset (harness lev2, 0.95% ER) | 2x monthly-rebalanced | daily-reset minus monthly | real QLD (price) | 35% sleeve contribution (daily reset) |
|---|---|---|---|---|---|---|
| 2008 | -38.1% | -68.1% | -68.2% | +0.1% | - | -23.8% |
| 2009 | +50.5% | +109.6% | +110.2% | -0.6% | - | +38.3% |
| 2011 | +3.6% | +0.1% | +4.1% | -4.1% | - | +0.0% |
| 2015 | +7.0% | +9.4% | +9.5% | -0.1% | +19.4% | +3.3% |
| 2018 | -1.7% | -11.2% | -9.3% | -1.9% | -11.4% | -3.9% |
| 2020 | +44.0% | +78.7% | +84.2% | -5.5% | +82.9% | +27.5% |
| 2021 | +30.6% | +63.0% | +65.8% | -2.9% | +59.1% | +22.0% |
| 2022 | -33.8% | -61.8% | -60.9% | -0.8% | -61.4% | -21.6% |
| 2023 | +53.1% | +112.8% | +111.0% | +1.8% | +120.0% | +39.5% |
| 2024 | +27.5% | +47.6% | +49.3% | -1.7% | +47.4% | +16.7% |
| 2025 | +20.9% | +31.2% | +36.1% | -4.9% | +30.7% | +10.9% |

Reading: in a trending year the daily reset HELPS (2x compounding of a one-way move beats monthly 2x); in a choppy or V-shaped year (2020, 2022) it costs. Holding 35% of the book in a 2x fund through a -33% QQQ year (2022) costs roughly 0.35 x the 2x fund's loss, i.e. the sleeve alone knocks about a fifth off the book, plus ~0.33%/yr of ER (0.35 x 0.95%) and financing at bill+spread on the borrowed half.

| year | book (mix) | QTOP-sleeve (core, 55%*) | 2x sleeve (35%) | cash-ish (10%) |
|---|---|---|---|---|
| 2008 | -47.3% | -21.4% | -23.8% | +0.1% |
| 2020 | +52.8% | +24.7% | +27.5% | +0.0% |
| 2022 | -42.3% | -18.9% | -21.6% | +0.2% |
*core sleeve = QTOP 46 + QNXT 9 + QQLV beta share; harness core is QQQ total return.

Reading: the daily-reset cost is small and sign-indefinite year to year (+1.8% in trending 2023, -5.5% in V-shaped 2020, -4.9% in choppy 2025) and the real QLD matches the harness 2x leg within 1-3%/yr, so the harness proxy is trustworthy for QQXL. The 35% sleeve is not a "decay" problem, it is a size problem: in a -34% QQQ year the 2x sleeve loses ~62% and takes 21.6 points off the book, and the book as a whole loses 42-47% in 2008/2022 because 55% of the rest is 1x QQQ too. Recurring drag is ~0.33%/yr of ER on the sleeve plus financing on the borrowed half (bill + spread on 35% of NAV, ~1.5-2%/yr at current rates).

## 6. Side by side with the live design, and the combined book

### 2000-07+ harness rows (QQQ legs for both): 2000-07-03..2026-08-26 (n=6575)

| book | CAGR | vol | Sharpe | MaxDD | worst yr | 2008 | 2020 | 2022 | avg deployed | realised regression beta to QQQ |
|---|---|---|---|---|---|---|---|---|---|---|
| NASDAQ-30 static mix | +8.68% | 32.3% | 0.419 | -88.6% | 2000 -53.5% | -47.3% | +52.8% | -42.3% | 0.91 | 1.26 |
| LIVE design | +22.18% | 25.5% | 0.913 | -33.6% | 2022 -27.2% | -13.5% | +33.3% | -27.2% | 0.68 | 0.62 |
| QQQ B&H | +8.72% | 25.6% | 0.454 | -80.2% | 2000 -43.7% | -38.1% | +44.0% | -33.8% | 1.00 | 1.00 |
| combined 200k/20k (91%/9%) | +21.22% | 25.2% | 0.891 | -35.1% | 2022 -28.3% | -16.6% | +35.6% | -28.3% | - | 0.68 |

Daily-return correlation mix vs live: 0.627 (beta of mix on live 0.79). Live avg beta 1.27, mix 1.26; combined avg beta 1.27.
Block bootstrap (mix minus live): block 20 log-ret CI [-0.201,-0.039] P(<=0) 1.00, Sharpe CI [-0.802,-0.203] P(<=0) 1.00; block 60 log-ret CI [-0.210,-0.041] P(<=0) 1.00, Sharpe CI [-0.814,-0.203] P(<=0) 1.00.

### 2007-12+ MGK window (mix on MGK legs, live on QQQ legs, identical dates): 2007-12-21..2026-08-25 (n=4694)

| book | CAGR | vol | Sharpe | MaxDD | worst yr | 2008 | 2020 | 2022 | avg deployed | realised regression beta to QQQ |
|---|---|---|---|---|---|---|---|---|---|---|
| NASDAQ-30 static mix | +14.37% | 26.6% | 0.638 | -58.6% | 2022 -43.6% | -42.9% | +43.1% | -43.6% | 0.91 | 1.16 |
| LIVE design | +24.81% | 26.3% | 0.977 | -33.6% | 2022 -27.2% | -13.5% | +33.3% | -27.2% | 0.72 | 0.82 |
| QQQ B&H | +15.68% | 22.3% | 0.764 | -51.0% | 2008 -38.1% | -38.1% | +44.0% | -33.8% | 1.00 | 1.00 |
| combined 200k/20k (91%/9%) | +24.07% | 25.5% | 0.973 | -32.6% | 2022 -28.5% | -16.0% | +34.8% | -28.5% | - | 0.85 |

Daily-return correlation mix vs live: 0.664 (beta of mix on live 0.67). Live avg beta 1.36, mix 1.26; combined avg beta 1.35.
Block bootstrap (mix minus live): block 20 log-ret CI [-0.170,-0.002] P(<=0) 0.98, Sharpe CI [-0.676,-0.004] P(<=0) 0.98; block 60 log-ret CI [-0.167,-0.013] P(<=0) 0.99, Sharpe CI [-0.666,-0.023] P(<=0) 0.98.

Reading: the two books are 0.63-0.66 correlated daily; the NASDAQ-30 mix has a 0.67-0.79 beta ON the live book. At $200k live + $20k NASDAQ-30 (91/9) the combination is 96% "live design": CAGR 21.2% vs 22.2% (26y) and 24.1% vs 24.8% (2007+), Sharpe -0.02 to -0.004, worst drawdown -35.1% vs -33.6% (26y) and -32.6% vs -33.6% (2007+, marginally better thanks to the MGK path), 2008 -16.6% vs -13.5%, 2022 -28.3/-28.5% vs -27.2%. The block bootstrap says the mix's shortfall vs live is not noise: P(mix log-return <= live) 0.98-1.00, Sharpe CI [-0.80,-0.20] (26y) and [-0.68,-0.004] (2007+). At 9% of capital the second account adds ~1.5 points of drawdown and ~1 point of CAGR drag as a static line; whatever the manager's leverage timing adds or subtracts sits on top of that and is unmeasurable.

## Verdict

Raincheck NASDAQ-30 is a mega-cap QQQ beta sleeve (QTOP = QQQ with beta 1.05 and 0.99 correlation; "the 30 largest" has been a premium only in 2024-2026 and lost to QQQ in 15 of the previous 19 years) run at ~1.3x through a 35% position in a 2x daily fund, with the leverage dial turned by a discretionary, undisclosed "Market Signal" whose public description is one sentence about "statistical trends in price action of QQQ." Held as currently constituted it is a constant 1.26x QQQ line: no Sharpe over QQQ, -89% worst drawdown on the 26-year rows, -42 to -47% in 2008 and 2022, and it would have to move QQXL to near zero in downturns to avoid that. Every mechanical stand-in for the signal that a manager could plausibly be following is a smaller, worse-drawdown version of the owner's live 50/200 + vol-target design (best ladder 17.3% / 0.66 / -63% vs live 22.2% / 0.91 / -34% on identical rows), and the perfect-foresight ceiling (95% CAGR) shows the product's entire value proposition is the timing, which cannot be audited from outside. At $20k against $200k live it is a 9% side bet with 0.65 correlation to the main book; it costs ~1 point of CAGR and adds ~1.5 points of drawdown as a static line. Nothing in the holdings or the mechanics is worth importing into the live design; the one thing worth the owner's attention is that after the 09-09 "WEAK BULLISH" downgrade the account is still ~1.3x QQQ, so in a 2022-style year the $20k should be expected to lose 40%+ unless the manager de-levers faster than a 50/200 rule would.
