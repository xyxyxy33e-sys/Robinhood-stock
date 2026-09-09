# Style / exposure attribution of the LIVE design (2026-09-09)

Research line `style_attribution`. Owner's question: *"Does the strategy
outperform after accounting for changing Nasdaq exposure, momentum exposure,
and cash holdings? This separates timing skill from benefiting when a
particular investment style performs well."*

Script `paper-track/style_attribution.py` (202 s), full output in
`research_notes/style_attribution_run.log`. Research only; nothing applied;
no protected file edited; no commit.

## Setup

Everything goes through the project harness (`improvement_search.run` on the
26-year QQQ-core proxy, `return_frontier.eval_real` on the real weekly SPMO
rows). Standing figures reproduced first: **proxy 22.12% / 0.938 / −32.8%,
search 1.150, holdout 0.780; real 30.67% / 1.260 / −25.3%** (asserted). The
only loop-shaped code is `run_w`, a verbatim copy of `run()` that also
records the held weights and the cost charged each day; its returns are
asserted equal to `run()`'s to 1e-15 before use.

**Return sources** (daily on the proxy calendar, d0→d1; weekly on `rr`):

| series | construction |
|---|---|
| MKT_NDX | QQQ total return − cash (`D['core']`, `D['cash']`; exactly `legs[0] − legs[4]`) |
| MKT_SPX | SPY total return (1.8%/yr accrual, `long_history_backtest.total_return_index`) − cash, from `data/spy_long_history.csv` (covers every proxy date) |
| MOM | Fama-French daily momentum factor, compounded over FF dates in (d0, d1] |
| SMB, HML, Mkt-RF | Fama-French daily 3 factors, same treatment |
| LEV | synthetic 3× leg excess − 3× core excess = L3 − 3C + 2·cash: the volatility drag + financing of holding TQQQ (LEV2 likewise for QLD) |
| SPMO−SPY | real momentum-style excess, weekly, `rr` only |

**New data (provenance):** `data/ff_momentum_daily.csv` and
`data/ff_3factors_daily.csv`, fetched 2026-09-09 through the proxy from
Kenneth French's data library
(`https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Momentum_Factor_daily_CSV.zip`
and `F-F_Research_Data_Factors_daily_CSV.zip`, "created using the 202607 CRSP
database"), parsed to decimal daily returns, 1926-07/11 .. 2026-07-31. The
factors end 2026-07-31, so every regression (all variants, incl. the QQQ/SPY
anchors) uses the 6,556 proxy rows with d1 ≤ 2026-07-31 (same-rows control);
the exposure decomposition needs no French data and uses all 6,575 rows.

Alignment checks: corr(MKT_NDX, FF Mkt-RF) = +0.87, corr(MKT_NDX, MKT_SPX)
= +0.85, corr(MKT_NDX, MOM) = −0.21, weekly corr(MOM, SPMO−SPY) = +0.53.
Factor means over the sample (pp/yr): MKT_NDX +9.6, MKT_SPX +8.0, MOM +3.2,
SMB +0.9, HML +2.9, LEV −1.4. Sanity anchors: QQQ buy-and-hold has alpha
0.00 and beta 1.000 on MKT_NDX in every era; SPY has alpha 0.00 / beta 1.000
on MKT_SPX.

**One modelling note that matters.** LEV has a volatility of 0.1%/yr (it is
a near-constant −1.4 pp/yr drag), so as a *regressor* it is almost collinear
with the intercept: adding it doubles the alpha CI (±7 → ±14 pp) and its
beta is unidentified (−2.4 ± 4.3). The headline static model is therefore
NDX+SPX+MOM, run both on LIVE and on "LIVE net of exact LEV cost" (the
exact w_TQQQ·LEV + w_QLD·LEV2 the book paid each day, added back). The +LEV
models are shown as robustness only.

## 1. Static attribution — daily excess return on the return sources

OLS, Newey-West 10 lags, alpha in pp/yr; `[]` NW 95% CI, `{}` 60-day block
bootstrap 95% CI (400 draws).

| series | era | model | R² | alpha pp/yr | β NDX | β SPX | β MOM |
|---|---|---|---|---|---|---|---|
| **LIVE** | full | NDX only | 0.383 | +15.2 [+8.3, +22.2] | 0.59 | | |
| **LIVE** | full | **NDX+SPX+MOM** | 0.426 | **+13.4 [+6.6, +20.2] {+6.5, +18.7} P=0.000** | 0.47 | 0.25 | 0.29 |
| LIVE | full | NDX+SPX+MOM+LEV | 0.426 | +10.0 [−4.0, +23.9] {−3.5, +23.5} P=0.058 | 0.47 | 0.25 | 0.29 (β LEV −2.4±4.3) |
| LIVE | full | NDX+MOM+SMB+HML+LEV | 0.433 | +7.8 [−6.1, +21.7] | 0.63 | | 0.31 (SMB 0.30, HML 0.14) |
| **LIVE** | search 2015-11+ | NDX+SPX+MOM | 0.525 | **+11.9 [+1.9, +21.9] {+2.0, +20.4} P=0.003** | 1.03 | −0.30 | 0.11 |
| **LIVE** | holdout 2000-07..2015-10 | NDX+SPX+MOM | 0.388 | **+12.9 [+4.2, +21.5] {+3.8, +21.9} P=0.000** | 0.40 | 0.29 | 0.36 |
| LIVE net of exact LEV cost | full | NDX+SPX+MOM | 0.426 | +13.9 [+7.1, +20.7] | 0.47 | 0.25 | 0.29 |
| base allocations only (macro states, no overlays, no VT) | full | NDX only | 0.449 | +11.0 [+2.6, +19.4] | 0.81 | | |
| base allocations only | full | NDX+SPX+MOM | 0.507 | +8.3 [+0.3, +16.3] | 0.64 | 0.36 | 0.43 |
| base allocations only | search | NDX+SPX+MOM | 0.676 | +5.4 [−5.3, +16.1] | 1.39 | −0.26 | 0.25 |
| base allocations only | holdout | NDX+SPX+MOM | 0.416 | +7.7 [−2.8, +18.1] | 0.52 | 0.34 | 0.43 |
| QQQ buy-and-hold | all eras | any | 1.000 | 0.00 | 1.000 | 0 | 0 |

Real weekly SPMO rows (560 weeks with French data, NW 4 lags, ×52):

| series | model | R² | alpha pp/yr | β NDX | β SPX | β MOM / SPMO−SPY |
|---|---|---|---|---|---|---|
| LIVE (real) | NDX only | 0.519 | +12.7 [+3.4, +22.0] | 0.83 | | |
| LIVE (real) | NDX+SPX+MOM+LEV | 0.540 | +13.8 [+3.3, +24.3] | 0.99 | −0.20 | MOM 0.15 |
| LIVE (real) | NDX+SPX+(SPMO−SPY)+LEV | 0.536 | +14.0 [+3.5, +24.4] | 1.01 | −0.24 | SPMOX 0.21 |
| base only (real) | NDX+SPX+MOM+LEV | 0.688 | +6.7 [−4.7, +18.1] | 1.11 | 0.14 | MOM 0.32 |
| SPMO (real core leg) | NDX+SPX+MOM+LEV | 0.816 | +0.5 [−4.0, +4.9] | 0.11 | 0.89 | MOM 0.29 |

Reading. (1) LIVE's *average* Nasdaq beta is only 0.59 (0.47 with SPX
alongside) on the full proxy, 0.82–1.03 in the search era, 0.40–0.49 in the
holdout: the design spends most of the 26 years well under 1× despite an
average leverage of 1.25. (2) The momentum loading is real but modest:
β_MOM 0.29 (0.36 holdout, 0.11 search, 0.15–0.21 real); at MOM's +3.2 pp/yr
mean it explains **~+0.9 pp/yr** of LIVE's return. The base allocations load
on momentum *more* (0.43) — a 50/200 trend rule is a time-series-momentum
strategy and inherits a cross-sectional-momentum correlation; the overlays
reduce it. (3) The static alpha after Nasdaq, S&P and momentum exposure is
**+13.4 pp/yr, CI [+6.6, +20.2]**, positive and clear of zero in *both* eras
(+11.9 search, +12.9 holdout) and on real rows (+13.8). The base design's
alpha on the same model is +8.3 [+0.3, +16.3]: the overlays and vol target
add ~5 pp/yr of static alpha over the plain classifier. (4) R² is only
0.38–0.53: half of LIVE's variance is not explained by *average* factor
exposures, because the exposures are not constant. That is what section 2 is
for.

## 2. Exposure-matched passive — the part that matters

Realized daily exposure from the harness's held weights:
e_t = w·(1, 3, 2, 0.5, 0) (core 1×, TQQQ 3×, QLD 2×, XLU ~0.5× beta proxy,
per `improvement_search_r2.BETA`). Average e̅ = 1.245 (deployed capital
66.2%), range [0.00, 2.03]. Passive series, no information other than the
exposure lagged one session so it is known ex ante:

    P_avg_t  = e̅ · MKT_NDX_t + cash_t            constant average exposure
    P_path_t = e_{t−1} · MKT_NDX_t + cash_t       the strategy's own exposure path, one day late
    (b) timing  = P_path − P_avg
    (c) residual = LIVE − P_path
             ≡ LEV(decay+financing) + XLU selection + one-day lag term − costs   (exact identity, asserted to 1e-12)

pp/yr, simple means; bootstrap = `block_bootstrap.boot` (2000 draws) on the
paired daily series, P = P(≤0):

| era | N | LIVE xs | P_avg xs | P_path xs | **(b) timing** | (c) resid | = LEV | +XLU | +lag | −cost | resid Sharpe | LIVE−P_path CI 20d / 60d |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 6575 | +21.1 | +12.1 | +20.1 | **+8.0** | +0.95 | −0.49 | +0.21 | +2.53 | −1.29 | +0.16 | [−1.1, +3.1] P 0.18 / [−1.4, +3.1] P 0.20 |
| search 2015-11+ | 2719 | +26.9 | +23.9 | +27.3 | **+3.5** | −0.40 | −0.53 | +0.14 | +1.35 | −1.37 | −0.06 | [−4.1, +3.0] P 0.57 / [−4.0, +2.9] P 0.58 |
| holdout 2000-07..2015-10 | 3856 | +17.0 | +4.7 | +15.1 | **+10.3** | +1.91 | −0.47 | +0.26 | +3.35 | −1.23 | +0.36 | [−0.6, +4.4] P 0.07 / [−0.8, +4.9] P 0.09 |
| 2000-07..2009 | 2389 | +13.1 | −4.0 | +11.1 | +15.1 | +2.01 | −0.36 | +0.23 | +3.39 | −1.25 | +0.35 | P 0.15 / 0.16 |
| 2010..2019 | 2515 | +22.1 | +27.5 | +22.9 | −4.6 | −0.78 | −0.65 | +0.20 | +0.82 | −1.14 | −0.14 | P 0.67 / 0.67 |
| 2020..2026 | 1671 | +31.0 | +21.7 | +28.9 | +7.3 | +2.04 | −0.46 | +0.20 | +3.87 | −1.57 | +0.31 | P 0.17 / 0.14 |
| **real weekly** (lag = 1 week) | 563 | +27.3 | +23.1 | +23.4 | +0.3 | +3.81 | −0.85 | +0.76 | +5.17 (−0.42 SPMO-vs-QQQ) | −0.85 | +0.35 | [−10.7, +51.3] P 0.11 / [−9.0, +49.0] P 0.10 |

Sharpe: LIVE 0.938 vs P_path 0.902 vs P_avg 0.439 (full); search 1.150 /
1.169 / 0.885; holdout 0.780 / 0.703 / 0.192. LIVE−P_path Sharpe difference
CI (60d) full [−0.06, +0.13] P 0.22, search [−0.16, +0.11] P 0.60, holdout
[−0.04, +0.20] P 0.10.

**The timing term (b) — the exposure path against the same average exposure
held constantly:**

| era | e̅ | (b) pp/yr | log-return CI 20d | P | CI 60d | P | ΔSharpe CI 60d | P |
|---|---|---|---|---|---|---|---|---|
| full | 1.245 | **+8.0** | [+1.9, +19.2] | **0.007** | [+2.6, +18.4] | **0.004** | [+0.16, +0.76] | **0.001** |
| search 2015-11+ | 1.341 | +3.5 | [−5.5, +15.3] | 0.19 | [−3.8, +13.1] | 0.14 | [−0.04, +0.63] | 0.046 |
| holdout 2000-07..2015-10 | 1.178 | **+10.3** | [+0.8, +25.4] | **0.017** | [+1.5, +25.7] | **0.013** | [+0.09, +0.91] | **0.006** |
| real weekly (lag 1 wk) | 1.336 | +0.3 | [−46.9, +55.1] | 0.42 | [−45.3, +48.4] | 0.43 | | |

So: **once the strategy's own exposure path is handed to a passive holder one
day late, that passive holder captures 20.1 of LIVE's 21.1 pp/yr excess
return and 0.90 of its 0.94 Sharpe.** The remaining residual (c) is +0.95
pp/yr, Sharpe 0.16, inside noise in every era (P 0.18–0.58), and it is not
"selection" at all: it is +2.5 pp/yr of *same-day execution value* (the lag
term — acting at the signal close instead of the next close) minus 1.3 pp of
costs and 0.5 pp of leverage decay, plus 0.2 pp from the XLU leg. There is no
residual beyond execution timing and known costs. Everything the design earns
over a constant-exposure Nasdaq holder is the *timing of exposure* (b): +8.0
pp/yr on the full proxy, +10.3 in the holdout, both with bootstrap CIs
excluding zero; +3.5 in the search era, not distinguishable from zero on
log-return (P 0.14) but marginal on Sharpe (P 0.046).

**Timing value vs execution delay** ((b) at lag k sessions, 60d-block P in brackets):

| era | lag 0 | lag 1 | lag 2 | lag 3 | lag 5 | lag 10 |
|---|---|---|---|---|---|---|
| full | +10.6 [0.000] | +8.0 [0.009] | +6.6 [0.017] | +6.5 [0.013] | +6.0 [0.036] | +4.0 [0.096] |
| search | +4.8 [0.088] | +3.5 [0.138] | +2.2 [0.202] | +2.1 [0.226] | +0.3 [0.366] | +1.2 [0.343] |
| holdout | +13.7 [0.001] | +10.3 [0.013] | +8.8 [0.037] | +8.7 [0.024] | +9.0 [0.023] | +5.0 [0.114] |

The first day of delay costs 2.5 pp/yr, the next four together another 2
pp; at 10 sessions' delay the timing is still +4 pp/yr but no longer
significant. This is consistent with the 09-07 drawdown reconciliation
("it is execution lag") and quantifies it: the live book, trading the next
morning, is on the lag-1 line, not the lag-0 line the proxy figures assume.
On the weekly real rows a one-*week* lag removes almost all of (b) (+0.3)
and moves it into the lag term (+5.2) — the weekly rows cannot separate
timing from execution and should not be read as evidence against (b).

**Which rule produces the timing** (lag 1, pp/yr, 60d-block P(b≤0)):

| design | full (b) | P | search (b) | P | holdout (b) | P | full Sharpe |
|---|---|---|---|---|---|---|---|
| base allocations only (no VT) | +4.8 | 0.078 | −0.3 | 0.43 | +6.7 | 0.096 | 0.675 |
| base + vol target | +5.1 | 0.051 | −0.6 | 0.41 | +7.6 | 0.063 | 0.760 |
| base + fast overlay + VT | +6.1 | 0.022 | −0.9 | 0.41 | +9.7 | 0.018 | 0.797 |
| base + trim + VT | +6.6 | 0.025 | +3.6 | 0.14 | +7.7 | 0.054 | 0.885 |
| **LIVE** | **+8.0** | **0.005** | **+3.5** | 0.13 | **+10.3** | **0.007** | 0.938 |

The 50/200 classifier alone times exposure worth +4.8 pp/yr but not
significantly (P 0.08), and *nothing* in the search era (−0.3). The vol
target adds little to (b) directly (it is a risk dial, +0.09 Sharpe through
lower P_avg variance). The fast re-entry overlay adds +1.3 pp (all holdout);
the extension trim adds +1.8 pp and is the *only* rule that gives the design
positive timing in the search era (+3.6 vs −0.9 without it). Together they
take (b) from "suggestive" to P 0.005. This is the same ordering the
09-09 overlay-interaction test found on Sharpe (T > F > E), seen from the
attribution side.

## 3. Style-regime buckets — where does the timing live?

Daily rows bucketed by calendar-quarter statistics (contemporaneous
quintiles/terciles over 105 quarters). "share" = the bucket's share of the
full-sample sum of that term. pp/yr within bucket.

**(i) Fama-French momentum factor, quarterly quintile** (Q5 = momentum works best)

| bucket | N | e̅ | MKT_NDX | LIVE xs | P_avg xs | P_path xs | (b) | (c) | share (b) | share (c) |
|---|---|---|---|---|---|---|---|---|---|---|
| Q1 lowest | 1297 | 0.97 | +48.0 | +48.7 | +59.7 | +47.4 | −12.4 | +1.4 | −30% | +28% |
| Q2 | 1321 | 1.39 | +8.0 | +3.6 | +10.0 | +6.7 | −3.3 | −3.1 | −8% | −65% |
| Q3 | 1322 | 1.60 | +22.6 | +38.3 | +28.1 | +35.5 | +7.4 | +2.8 | +18% | +58% |
| Q4 | 1321 | 1.32 | +1.2 | +9.4 | +1.5 | +9.5 | +8.0 | −0.1 | +20% | −2% |
| **Q5 highest** | 1314 | 0.93 | **−30.7** | +5.8 | −38.2 | +2.0 | **+40.2** | +3.9 | **+100%** | +81% |

**(ii) Nasdaq vs S&P relative performance (MKT_NDX − MKT_SPX), quarterly quintile** (Q5 = Nasdaq beats S&P most)

| bucket | N | e̅ | MKT_NDX | LIVE xs | P_avg xs | P_path xs | (b) | (c) | share (b) | share (c) |
|---|---|---|---|---|---|---|---|---|---|---|
| **Q1 Nasdaq lags most** | 1282 | 0.77 | −47.5 | −26.5 | −59.1 | −29.2 | **+29.9** | +2.7 | **+73%** | +55% |
| Q2 | 1312 | 1.40 | +3.2 | +3.0 | +4.0 | +5.0 | +1.0 | −2.0 | +2% | −42% |
| Q3 | 1334 | 1.46 | +14.7 | +37.8 | +18.4 | +37.8 | +19.5 | −0.0 | +49% | −1% |
| Q4 | 1326 | 1.50 | +30.7 | +43.3 | +38.3 | +40.8 | +2.6 | +2.5 | +7% | +52% |
| **Q5 Nasdaq beats most** | 1321 | 1.08 | +45.5 | +46.0 | +56.7 | +44.4 | **−12.3** | +1.7 | **−31%** | +36% |

**(iii) realised QQQ vol, quarterly tercile**

| bucket | N | e̅ | MKT_NDX | LIVE xs | P_avg xs | P_path xs | (b) | (c) | share (b) | share (c) |
|---|---|---|---|---|---|---|---|---|---|---|
| T1 low vol | 2204 | 1.85 | +24.5 | +46.2 | +30.5 | +45.9 | +15.4 | +0.3 | +64% | +10% |
| T2 | 2177 | 1.34 | +16.5 | +18.4 | +20.6 | +18.3 | −2.3 | +0.2 | −10% | +6% |
| T3 high vol | 2194 | 0.54 | −11.9 | −1.5 | −14.8 | −3.9 | +10.9 | +2.4 | +45% | +83% |

**(iv) market direction (MKT_NDX quarterly quintile) and macro state**

| bucket | N | e̅ | MKT_NDX | LIVE xs | P_avg xs | P_path xs | (b) | (c) | share (b) |
|---|---|---|---|---|---|---|---|---|---|
| M1 worst quarters | 1308 | 0.65 | −66.6 | −38.5 | −83.0 | −37.8 | **+45.2** | −0.7 | **+112%** |
| M2 | 1299 | 1.22 | −3.7 | −11.3 | −4.6 | −14.6 | −10.0 | +3.2 | −25% |
| M3 | 1312 | 1.71 | +14.7 | +24.3 | +18.3 | +27.7 | +9.5 | −3.4 | +24% |
| M4 | 1330 | 1.68 | +34.4 | +63.0 | +42.8 | +58.4 | +15.6 | +4.5 | +39% |
| M5 best quarters | 1326 | 0.96 | +68.5 | +66.4 | +85.3 | +65.3 | **−20.0** | +1.1 | **−50%** |
| state A | 3442 | 1.56 | +12.2 | +23.6 | +15.2 | +22.5 | +7.4 | +1.1 | +48% |
| state B | 381 | 1.58 | −11.7 | +1.7 | −14.6 | +0.5 | +15.1 | +1.2 | +11% |
| state C | 445 | 0.83 | +27.3 | +36.8 | +34.0 | +40.7 | +6.6 | −3.9 | +6% |
| state D | 934 | 1.78 | +22.1 | +38.7 | +27.5 | +40.1 | +12.6 | −1.4 | +22% |
| state E | 380 | 0.18 | +22.9 | +4.4 | +28.5 | −2.0 | −30.5 | +6.4 | −22% |
| state F | 993 | 0.13 | −15.1 | +2.5 | −18.8 | −0.1 | +18.7 | +2.6 | +35% |
| effective F (after fast overlay) | 768 | 0.00 | −28.1 | −0.6 | −34.9 | −1.7 | +33.2 | +1.1 | +48% |

Regression alpha (NDX+SPX+MOM+LEV) inside halves: high-MOM half +9.7
[−11.5, +30.9], low-MOM half +1.2 [−15.9, +18.3]; high NDX−SPX half +6.5,
low half +3.6 — differences well inside the CIs.

Reading. The timing term does **not** live in "Nasdaq beats S&P" regimes:
the top Nasdaq-outperformance quintile is where (b) is most *negative* (−12
pp/yr, −31% share), and the bottom quintile — Nasdaq lagging the S&P by the
most, i.e. tech bears — carries 73% of it. Likewise the momentum-factor Q5
bucket carries 100% of (b), but that bucket's Nasdaq return is −31 pp/yr: the
cross-sectional momentum factor does best in crashes (losers keep losing),
so "momentum works" and "market falls" are the same quarters here. Sorting
by market direction makes it explicit: the worst quintile of quarters
supplies 112% of the timing (+45 pp/yr inside it, e̅ 0.65 vs 1.25), the best
quintile costs 50% of it (−20 pp/yr, e̅ 0.96). Effective state F (0.00
exposure, Nasdaq −28 pp/yr while it is on) is 48% of the term by itself.
**The outperformance is the crash-avoidance payoff of a trend rule** — earned
by being out or light when the Nasdaq falls hard, paid for by being under-
levered in the strongest rallies and by the recovery miss the 09-09 recovery
study measured. That is a *style* in the time-series-momentum sense, but it
is not "riding a factor that happened to pay": the cross-sectional MOM
loading explains under 1 pp/yr, and the strategy is *short* the
Nasdaq-beats-S&P style in its best years. The residual (c) is small and
sign-alternating across every bucketing (−3.9 to +6.4, sum +0.95).

## 4. Rolling 3-year alpha and beta

756-session windows ending each year-end; a1 = single-factor alpha, a4 =
NDX+SPX+MOM+LEV alpha (pp/yr); e = average realised exposure; median 3y beta
1.04. Flag: alpha<0 & beta>median = style-riding signature; alpha>0 &
beta<median = timing.

| year | 3y β | 3y a1 | 3y a4 | 3y e | 1y β | 1y a4 | LIVE | QQQ | MOM | flag |
|---|---|---|---|---|---|---|---|---|---|---|
| 2002 | 0.15 | −1.4 | +5.7 | 0.24 | 0.15 | +14.7 | −2.5 | −45.1 | +23.0 | timing |
| 2003 | 0.22 | +19.0 | +7.6 | 0.38 | 0.71 | +26.2 | +49.2 | +36.5 | −12.6 | timing |
| 2004 | 0.42 | +18.6 | +14.1 | 0.78 | 1.35 | +14.3 | +9.7 | +8.9 | −0.9 | timing |
| 2005 | 1.04 | +4.2 | +10.9 | 1.28 | 1.59 | +0.3 | +2.5 | +5.1 | +17.6 | |
| 2006 | 1.36 | +3.1 | −2.7 | 1.53 | 1.19 | −14.4 | +15.6 | +5.2 | −7.3 | **style-riding** |
| 2007 | 1.50 | +8.3 | −3.0 | 1.65 | 1.68 | +12.8 | +36.0 | +16.1 | +24.9 | **style-riding** |
| 2008 | 0.53 | +18.2 | +11.0 | 1.25 | 0.18 | −16.0 | −12.9 | −47.8 | +8.2 | timing |
| 2009 | 0.46 | +19.7 | +10.0 | 0.94 | 0.50 | −30.6 | +41.1 | +40.9 | −65.8 | timing |
| 2010 | 0.42 | +18.5 | −18.0 | 0.78 | 1.26 | −27.7 | +31.8 | +18.0 | +4.8 | |
| 2011 | 0.78 | +1.4 | −16.9 | 1.01 | 0.78 | +6.5 | −21.0 | +3.5 | +8.8 | |
| 2012 | 1.08 | −3.4 | +9.1 | 1.32 | 1.51 | +40.6 | +17.1 | +17.4 | +2.0 | |
| 2013 | 1.15 | −1.1 | +29.2 | 1.55 | 1.99 | −1.6 | +49.8 | +26.7 | +6.3 | |
| 2014 | 1.76 | −3.7 | +25.8 | 1.81 | 1.95 | −0.4 | +28.6 | +17.1 | +2.6 | |
| 2015 | 1.67 | −0.8 | −3.0 | 1.89 | 1.37 | −26.5 | −1.4 | +6.8 | +14.9 | **style-riding** |
| 2016 | 1.39 | −5.4 | −13.5 | 1.71 | 0.99 | −45.8 | −2.1 | +9.4 | −20.7 | **style-riding** |
| 2017 | 1.32 | −0.8 | −14.6 | 1.72 | 1.96 | +3.7 | +56.5 | +28.9 | +7.8 | **style-riding** |
| 2018 | 1.13 | +2.4 | −12.1 | 1.62 | 1.01 | −18.9 | −7.2 | −1.7 | +10.3 | **style-riding** |
| 2019 | 1.25 | +6.3 | −0.7 | 1.71 | 1.43 | −6.3 | +40.9 | +33.9 | −0.7 | **style-riding** |
| 2020 | 0.67 | +7.9 | +16.8 | 1.21 | 0.37 | +3.8 | +34.3 | +36.3 | −12.5 | timing |
| 2021 | 0.73 | +16.8 | +19.6 | 1.28 | 1.50 | +0.7 | +45.4 | +26.7 | −9.1 | timing |
| 2022 | 0.48 | +12.5 | +5.8 | 0.83 | 0.27 | −2.1 | −32.2 | −41.4 | +16.1 | timing |
| 2023 | 0.72 | +16.7 | +23.5 | 1.11 | 1.33 | +12.6 | +56.3 | +43.0 | −16.9 | timing |
| 2024 | 0.73 | +18.5 | +28.3 | 1.09 | 1.58 | +11.4 | +50.2 | +24.3 | +21.4 | timing |
| 2025 | 1.11 | +13.5 | +18.4 | 1.41 | 0.72 | +2.8 | +23.5 | +19.1 | +4.4 | |
| 2026 | 1.09 | +16.3 | +28.9 | 1.48 | 0.95 | +52.1 | +33.8 | +20.8 | +21.5 | |

Corr across windows: 3y a4 vs 3y beta −0.10; 1y a4 vs 1y MOM return +0.38;
1y a4 vs 1y QQQ return +0.12.

Two style-riding stretches, both the same shape: **2006–07** and
**2015–19**, when the book sat fully levered (e 1.5–1.9, beta 1.3–1.8) and
the 3-year multi-factor alpha was −3 to −15 pp/yr — in those windows the
design earned *less* than its leverage on the Nasdaq should have paid, and
its 2015–18 calendar-year excess was negative (−1.4, −2.1, −7.2) while QQQ
was positive. The timing windows are the ones that contain a bear and its
first recovery year: 2002–04, 2008–09, 2020–24. Alpha comes in the turns and
is given back in the long grinding bull. Note the *single-factor* a1 is
never materially negative (min −5.4) because the low average beta flatters
it; the 4-factor a4 is the honest column.

## 5. The gap vs SPY and vs QQQ — three-way decomposition

Annualised log return, pp/yr, terms add exactly:
gap = [index choice: QQQ − SPY] + **(a)** average leverage [P_avg − QQQ] +
**(b)** time-varying exposure [P_path − P_avg] + **(c)** residual [LIVE −
P_path]. (c) = LEV + XLU + one-day lag − costs.

| cost / era | e̅ | CAGR LIVE / QQQ / SPY | gap vs QQQ | (a) avg lev | (b) exposure timing | (c) residual | gap vs SPY | index choice |
|---|---|---|---|---|---|---|---|---|
| **4bp full** | 1.25 | 22.12 / 8.72 / 8.49 | **+11.6** | +0.6 (5%) | **+10.1 (87%)** | +0.9 (8%) | **+11.8** | +0.2 (2%) |
| 4bp search | 1.34 | 29.67 / 19.30 / 14.85 | +8.3 | +4.1 (49%) | +4.7 (56%) | −0.4 (−5%) | +12.1 | +3.8 (31%) |
| 4bp holdout | 1.18 | 17.06 / 1.83 / 4.22 | +13.9 | −0.8 (−6%) | +12.8 (92%) | +1.9 (14%) | +11.6 | −2.3 (−20%) |
| 4bp real weekly | 1.34 | 30.57 / 19.09 / 14.73 (SPMO 17.43) | +9.2 | +4.2 | +1.0 (lag-1-week) | +4.1 (of which lag +5.2) | +12.9 | +3.7 |
| **10bp full** | 1.25 | 19.78 / 8.72 / 8.49 | +9.7 | +0.6 (6%) | +10.1 (104%) | −1.0 (−10%) | +9.9 | +0.2 |
| 10bp search | 1.34 | 27.03 / 19.30 / 14.85 | +6.3 | +4.1 (65%) | +4.7 (74%) | −2.5 (−39%) | +10.1 | +3.8 |
| 10bp holdout | 1.18 | 14.92 / 1.83 / 4.22 | +12.1 | −0.8 (−6%) | +12.8 (106%) | +0.0 (0%) | +9.8 | −2.3 |
| 10bp real weekly | 1.34 | 28.92 / 19.09 / 14.73 | +7.9 | +4.2 | +1.0 | +2.8 | +11.7 | +3.7 |

(c) at 4bp full: LEV −0.49, XLU +0.21, lag +2.53, cost −1.29.

Reading. Over 26 years, **average leverage explains almost nothing** of the
gap (+0.6 pp of 11.6): 1.25× the Nasdaq held constantly through 2000–02 and
2008 would have returned 9.35% against QQQ's 8.72%. **87% of the gap over
QQQ, and 85% over SPY, is the timing of exposure**; the residual is 8% at
4bp and slightly negative at 10bp. The picture is era-dependent in the way
the earlier studies predicted: in the search era (one bear, 2022, and a long
levered bull) the gap splits ~50/50 between average leverage and timing,
and on the real rows — where the one-week lag folds most of the timing into
the residual — average leverage is the largest named term. Against SPY, the
Nasdaq index choice is worth +3.8 pp/yr since 2015 and −2.3 before it, net
+0.2 over the full sample: **the design's edge over the S&P is not "chose
the Nasdaq"**.

## 6. Placebo — the exposure path with its timing destroyed

Same exposure values, same average, random placement: (i) calendar-year
blocks permuted; (ii) 60-session circular blocks resampled; 1000 draws.
Statistic: P_path's annualised log return and Sharpe. P = fraction of
placebo paths at least as good as the actual path.

| era | actual P_path | year-shuffle median [95%] | P (log-ret) | P (Sharpe) | 60d-block median | P (log-ret) | P (Sharpe) |
|---|---|---|---|---|---|---|---|
| full | +19.1 pp / 0.902 | +7.0 [−1.6, +15.4] / 0.373 | **0.004** | **0.000** | +6.5 / 0.362 | **0.003** | **0.000** |
| search | +26.4 / 1.169 | +20.8 [+12.8, +29.9] / 0.776 | 0.116 | **0.010** | +20.0 / 0.756 | 0.086 | **0.004** |
| holdout | +13.9 / 0.703 | −1.1 [−14.5, +12.6] / 0.175 | **0.016** | **0.005** | −1.5 / 0.160 | **0.005** | **0.002** |

LIVE itself (residual included) sits +13.0 pp/yr above the placebo median
on the full proxy, +16.9 in the holdout, +5.2 in the search era (inside the
placebo 95% band there on log-return, outside it on Sharpe).

Sign-flip (exposure mirrored around e̅, 2e̅ − e_t): full actual +19.1 / 0.90
→ flipped **−7.6 / 0.12**; holdout +13.9 / 0.70 → **−19.1 / −0.07**; search
+26.4 / 1.17 → +12.6 / 0.51. The constant-e̅ holder sits between (+8.9 /
0.44). A real timing signal must lose when flipped; this one does, hard.

## Controls, honestly stated

- Both-era: (b) positive in both eras; significant on log-return in full
  and holdout, marginal (P 0.05 Sharpe / 0.14 log-return) in the search era.
- Exposure match: the passive series *is* the exposure match — same
  exposure, same average, by construction. No exposure_control needed.
- Causal: exposure lagged one session; factors contemporaneous with the
  return they explain; regime buckets are conditioning only, not signals.
- Same rows: every regression variant on the same 6,556 rows; every
  decomposition on the same 6,575; real rows 563 for all designs.
- Block bootstrap 20/60d (project `boot`), 400-draw block bootstrap for
  regression alphas, 1000-draw placebos.
- Placebo: year-shuffle, 60d-block shuffle, sign-flip — all pass.
- Leave-one-regime-out is not re-run here: the by-decade and bucket tables
  make the dependence explicit instead — the timing term is *negative* in
  2010–19 (−4.6 pp/yr) and positive in every decade with a bear.
- Candidate count: 0. Nothing was searched; this line measures, it does
  not propose.
- Caveats: (1) XLU's 0.5 beta is an assumption; XLU is 0.2 pp/yr of the
  book and cannot move the conclusion. (2) The proxy's TQQQ/QLD are
  synthetic; on the real rows LEV uses the real ETFs and is −0.85 pp/yr vs
  −0.49 synthetic — the proxy slightly understates leverage cost. (3) The
  lag-0 vs lag-1 gap (2.5 pp/yr) is the harness's same-close execution
  assumption; the live book is on the lag-1 line. (4) French factors stop
  2026-07-31; the last 19 rows are excluded from regressions only.

## Verdict

After accounting for exposure to the Nasdaq, the S&P, cross-sectional
momentum, leverage decay and cash, the LIVE design has a static alpha of
**+13.4 pp/yr [+6.6, +20.2]** on the 26-year proxy, +11.9 in the search era,
+12.9 in the holdout, +13.8 on real rows — but that alpha is *not* a
selection residual, and the momentum loading (β 0.29, worth under 1 pp/yr)
does not explain it. Handing the strategy's own exposure path, one day late,
to a passive Nasdaq holder reproduces **20.1 of its 21.1 pp/yr** excess
return and 0.90 of its 0.94 Sharpe; the remainder is +0.95 pp/yr (Sharpe
0.16, P 0.2), which is +2.5 pp of same-day execution value minus known costs
and leverage decay — nothing left over. **The timing residual therefore
lives entirely in the exposure path: +8.0 pp/yr over a constant
average-exposure holder on the full proxy [+2.6, +18.4], +10.3 in the
holdout [+1.5, +25.7], +3.5 in the search era (P 0.14 log-return, 0.046
Sharpe), P ≤ 0.004 against year-shuffled placebo paths, and −7.6 pp/yr when
sign-flipped.** It is 87% of the gap over QQQ and 85% over SPY; average
leverage is 5% and the Nasdaq-vs-S&P index choice 2%. Where it lives: 112%
of it in the worst quintile of market quarters (effective state F alone is
48%), −50% in the best quintile, −31% in the quarters when the Nasdaq beats
the S&P by the most, and it is negative through the whole of 2010–19, with
multi-factor alpha of −3 to −15 pp/yr in the 2006–07 and 2015–19 windows
when the book sat fully levered. So: **this is timing, not riding a style
that happened to pay — but the timing is one specific thing, the
crash-avoidance payoff of a trend rule (a time-series-momentum style), paid
for in every long bull.** The extension trim is the one rule that keeps the
timing term positive in the search era (+3.6 vs −0.9 without it), the fast
re-entry adds ~1.3 pp all in the holdout, and the vol target contributes
through variance, not timing — consistent with the 09-09 interaction test.
Nothing here argues for a change; it tells the owner what he is paid for
and when to expect to be paying.
