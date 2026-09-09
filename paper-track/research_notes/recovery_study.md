# Line `recovery_study` — does protection pay for its recovery cost, episode by episode? (2026-09-09)

**Verdict: YES in aggregate, NO in medium corrections, and the rule that costs recovery
participation is the VOL TARGET — but it is also the rule that earns the most in the
decline, and the two halves net to a positive figure in dollars at 4, 10 and 20 bp.
Nothing here supports removing or simplifying a rule.** The fast re-entry overlay is the
one rule that unambiguously HELPS recovery (+8.7 pp/yr of recovery-window log-return,
95% CI [+4.7, +13.1]); the extension trim costs recovery only in 2009 and 2023 and is
repaid by the 18 shallow pullbacks; the max(10,30) vol estimator's recovery drag
(−2.1 pp/yr, CI [−3.3, −1.1]) is real but small and repaid in the declines (whole-window
+0.9 pp/yr, P(≤0) 0.16 — noise). Research only; the change freeze holds.

Script: `paper-track/recovery_study.py`. Full output: `recovery_study_run.log`;
session-by-session deep-dive paths: `recovery_study_paths.log` (both in this folder).
No new data files. No parameters were searched (candidate count: 0 — all 9 portfolios
and the episode definition were fixed before the first run).

## Setup

- Harness: the 26-year QQQ-core proxy (6,575 sessions 2000-07-03..2026-08-26) through
  `run()` with the 3% drift band and one-way cost set as a module global
  (`improvement_search.ONE_WAY_SPREAD`) at 4 / 10 / 20 bp; real weekly SPMO/TQQQ rows
  (564, 2015-11-06..2026-08-21) through a per-row copy of `return_frontier.eval_real`'s
  loop, asserted equal to `eval_real`. The per-session exposure path needs the held
  weights that `run()` does not return, so `run_path` is a verbatim copy of `run()` with
  one extra output; every call asserts its return series is bit-identical to `run()`.
- Standing figures reproduced first: proxy 22.12% / 0.938 / −32.8%, S 1.150 H 0.780;
  real 30.67% / 1.260 / −25.3%.
- Portfolios (all pre-specified): LIVE; LIVE−fast (macro state drives weights and trim);
  LIVE−trim; LIVE vol30 (plain 30d estimator); LIVE−VT (no vol target); BASE+VT (macro
  states + live vol target, no overlays); BASE (macro states only, no VT); QQQ buy-and-hold
  (100% core leg, total return); A5050 (50/50 core/TQQQ held constant inside the drift band).
- Episodes are defined mechanically on the QQQ close series: running high = trailing
  252-session max; a segment runs between consecutive running-high dates; peak = first high,
  trough = min close, R = next running high (price above every close of the past year),
  F = first close ≥ the true peak. The recovery window ends at F if the peak is regained
  before the next qualifying episode starts, else at that next episode's peak. Primary set:
  depth ≤ −15%; secondary: −8% > depth > −15%. The dot-com peak (2000-03-27) predates the
  first strategy row; that episode's strategy measures start 2000-07-03 (QQQ already −20%).
- Measures per episode and portfolio: peak→trough return; trough→window-end, →T+63,
  →T+126; average held risky weight in each window; sessions after the trough until held
  exposure is back to ≥90% of the portfolio's own pre-episode exposure (mean of the 21
  sessions before the peak); sessions to regain the portfolio's own prior NAV high (max
  over [peak−252, trough]); net = (P→T advantage) + (T→R shortfall) in pp; and the
  compounded peak→window-end difference in dollars on a $200k book.
- **Read the dollar column, not the additive pp column, for deep episodes.** The additive
  net rewards volatility: A5050 scores +376 pp vs QQQ across the 11 episodes and LOSES
  $241k, because −98% in 2000-02 followed by +234% is a wipeout. The pp column is reported
  because it was asked for; conclusions below are drawn from the compounded figures.

## 1. Episode list

Primary (≥15%), 11 episodes:

| # | peak | trough | depth | P→T sess | R (52w high) | F (peak regained) | window end | T→end sess | era |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2000-03-27* | 2002-10-09 | −83.0% | 636 | 2003-06-03 | 2016-09-06 | 2004-01-26 (next peak) | 325 | holdout |
| 2 | 2004-01-26 | 2004-08-12 | −15.9% | 138 | 2004-11-12 | 2004-11-12 | 2004-11-12 | 65 | holdout |
| 3 | 2006-01-11 | 2006-07-21 | −17.4% | 132 | 2006-11-13 | 2006-11-13 | 2006-11-13 | 80 | holdout |
| 4 | 2007-10-31 | 2008-11-20 | −53.6% | 267 | 2009-09-21 | 2011-01-04 | 2010-04-23 (next peak) | 356 | holdout |
| 5 | 2010-04-23 | 2010-07-02 | −15.9% | 49 | 2010-10-13 | 2010-10-13 | 2010-10-13 | 71 | holdout |
| 6 | 2011-07-26 | 2011-08-19 | −16.1% | 18 | 2012-01-19 | 2012-01-19 | 2012-01-19 | 104 | holdout |
| 7 | 2015-12-01 | 2016-02-09 | −16.4% | 47 | 2016-07-29 | 2016-07-29 | 2016-07-29 | 119 | search |
| 8 | 2018-08-29 | 2018-12-24 | −23.2% | 80 | 2019-04-17 | 2019-04-17 | 2019-04-17 | 78 | search |
| 9 | 2020-02-19 | 2020-03-16 | −28.6% | 18 | 2020-06-05 | 2020-06-05 | 2020-06-05 | 57 | search |
| 10 | 2021-11-19 | 2022-12-28 | −35.6% | 277 | 2023-05-18 | 2023-12-15 | 2023-12-15 | 243 | search |
| 11 | 2025-02-19 | 2025-04-08 | −22.9% | 34 | 2025-06-24 | 2025-06-24 | 2025-06-24 | 52 | search |

\* strategy measured from 2000-07-03. Note the 2008 trough is 2008-11-20, not 2009-03-09:
QQQ's November close (25.56) was below March's (25.65). Depth buckets: 15–25% = 7 episodes
(2004, 2006, 2010, 2011, 2015, 2018, 2025), >25% = 4 (2000, 2008, 2020, 2022).

Secondary (8–15%), 18 episodes: 2004-12 (−14.3), 2007-07 (−9.7), 2010-01 (−8.5), 2011-02
(−8.0), 2011-04 (−9.2), 2012-04 (−11.5), 2012-09 (−11.9), 2014-09 (−8.5), 2015-07 (−13.9),
2018-01 (−10.2), 2018-03 (−10.7), 2019-05 (−10.9), 2020-09 (−12.7), 2021-02 (−10.9),
2023-07 (−10.9), 2024-07 (−13.6), 2025-10 (−12.2), 2026-06 (−11.3, still open at 2026-08-27).
Full table with dates in the run log.

## 2. Per-episode results, LIVE at 4 bp (returns in %)

| ep | P→T LIVE / BASE / QQQ | T→end LIVE / BASE / QQQ | T+63 LIVE / QQQ | T+126 LIVE / QQQ | expo P→T | expo T→R | pre | re-part sess | own-high regain LIVE / QQQ | net vs QQQ | net vs BASE | $ vs QQQ | $ vs BASE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2000-03 | −20.6 / −43.3 / −78.6 | 93.1 / 102.0 / 93.9 | 10.0 / 33.3 | −2.1 / 28.9 | 0.16 | 0.38 | 0.42 | 4 | 215 / 2950 | +57.2 | +13.8 | +223,731 | +77,502 |
| 2004-01 | −19.9 / −25.0 / −15.6 | 17.6 / 12.7 / 19.2 | 12.4 / 16.6 | 10.9 / 14.8 | 0.77 | 0.88 | 0.50 | 7 | 77 / 65 | −6.0 | +10.0 | −12,947 | +19,316 |
| 2006-01 | −16.8 / −14.1 / −17.1 | 28.6 / 18.1 / 22.0 | 18.9 / 17.5 | 29.9 / 22.4 | 0.75 | 0.88 | 1.00 | 9 | 58 / 77 | +7.0 | +7.8 | +11,851 | +11,098 |
| 2007-10 | −21.8 / −30.8 / −53.3 | 86.5 / 97.3 / 99.3 | −4.0 / 12.8 | 15.6 / 36.5 | 0.41 | 0.41 | 0.72 | 118 | 219 / 515 | +18.7 | −1.7 | +105,551 | +18,981 |
| 2010-04 | −21.1 / −30.8 / −15.8 | 20.2 / 15.1 / 19.2 | 13.3 / 15.6 | 38.8 / 28.6 | 0.60 | 0.65 | 0.89 | 12 | 85 / 71 | −4.2 | +14.8 | −10,764 | +30,438 |
| 2011-07 | −17.6 / −16.2 / −16.1 | 0.8 / −3.4 / 19.9 | −3.1 / 11.8 | 14.5 / 27.5 | 0.50 | 0.47 | 0.94 | 95 | 264 / 103 | −20.7 | +2.7 | −35,321 | +4,103 |
| 2015-12 | −15.5 / −14.6 / −16.3 | −2.3 / −5.1 / 20.0 | 0.6 / 11.6 | 0.6 / 21.8 | 0.66 | 0.74 | 1.00 | 23 | 303 / 118 | −21.5 | +1.9 | −35,879 | +2,956 |
| 2018-08 | −30.0 / −33.8 / −23.0 | 24.9 / 19.8 / 30.7 | 13.5 / 24.2 | 15.7 / 29.9 | 0.57 | 0.74 | 1.00 | 36 | 249 / 77 | −12.8 | +8.9 | −26,431 | +16,249 |
| 2020-02 | −16.4 / −45.0 / −28.5 | 20.5 / 46.3 / 41.8 | 23.6 / 41.2 | 27.5 / 63.0 | 0.36 | 0.35 | 0.25 | 19 | 57 / 55 | −9.1 | +2.8 | −1,184 | +40,558 |
| 2021-11 | −28.8 / −30.2 / −35.2 | 76.2 / 86.4 / 56.7 | 25.0 / 21.6 | 45.6 / 42.5 | 0.37 | 0.67 | 1.00 | 58 | 102 / 241 | +25.8 | −8.8 | +47,755 | −9,228 |
| 2025-02 | −23.2 / −26.2 / −22.8 | 15.6 / 19.0 / 29.9 | 22.1 / 33.7 | 44.5 / 47.4 | 0.57 | 0.55 | 0.95 | 36 | 98 / 52 | −14.7 | −0.4 | −22,982 | +1,816 |

Reading it:
- **Loss avoided.** LIVE's peak→trough is better than QQQ's in the 4 deep episodes (by 58,
  32, 12 and 6 pp) and WORSE than QQQ's in 6 of the 7 medium ones (2004 −19.9 vs −15.6;
  2010 −21.1 vs −15.8; 2018 −30.0 vs −23.0; 2025 −23.2 vs −22.8). The medium corrections
  are too fast for the 50/200 state machine; the book is still holding TQQQ into the
  first leg down, and the vol target only bites after the vol has printed.
- **Recovery missed.** LIVE's trough→window-end lags QQQ in 9 of 11 (mean 34.7 vs 41.1;
  T+126 mean 22.0 vs 33.0). Average held exposure in the recovery windows is 0.35–0.88,
  lowest exactly in the biggest recoveries (2020 0.35, 2000 0.38, 2008 0.41). Time back to
  90% of pre-episode exposure: median 23 sessions, but 118 in 2008-09, 95 in 2011, 58 in
  2022.
- **Own-high regain.** In the deep episodes LIVE regains its own NAV high far sooner than
  QQQ regains its own (2000: 215 vs 2950 sessions; 2008: 219 vs 515; 2022: 102 vs 241);
  in the medium ones it is slower (2011: 264 vs 103; 2015: 303 vs 118; 2018: 249 vs 77;
  2025: 98 vs 52).
- **Net.** Vs QQQ, protection paid in 4 of 11 (2000, 2006, 2008, 2022), all but one deep.
  Vs BASE it paid in 8 of 11; the exceptions are 2008 (−1.7 pp, but +$19k compounded),
  2022 (−8.8 pp, −$9k) and 2025 (−0.4 pp). In dollars on $200k the 11 episodes sum to
  **+$243k vs QQQ and +$214k vs BASE** — almost all of it from 2000, 2008 and 2022.

## 3. Aggregate "did protection pay", primary set, at 4 / 10 / 20 bp

Sum of net (pp) and count paid/lost; $ = compounded peak→window-end difference summed over
the 11 episodes on $200k.

| cost | portfolio | net vs QQQ sum | paid/lost | net vs BASE sum | paid/lost | $ vs QQQ | $ vs BASE |
|---|---|---|---|---|---|---|---|
| 4bp | **LIVE** | +19.7 | 4/7 | +51.7 | 8/3 | **+243,379** | **+213,789** |
| 4bp | LIVE−fast | −45.5 | 3/8 | −13.5 | 7/4 | +154,376 | +124,787 |
| 4bp | LIVE−trim | +9.0 | 4/7 | +41.1 | 8/3 | +186,943 | +157,353 |
| 4bp | LIVE vol30 | +22.7 | 4/7 | +54.8 | 7/4 | +227,877 | +198,287 |
| 4bp | LIVE−VT | +78.1 | 4/7 | +110.2 | 10/1 | +190,459 | +160,870 |
| 4bp | BASE+VT | −45.3 | 3/8 | −13.3 | 4/7 | +125,923 | +96,333 |
| 4bp | BASE | −32.1 | 3/8 | 0 | — | +29,589 | 0 |
| 4bp | A5050 | +375.7 | 11/0 | +407.8 | 11/0 | −240,853 | −270,442 |
| 10bp | **LIVE** | −11.7 | 4/7 | +40.0 | 8/3 | **+182,117** | **+191,313** |
| 10bp | LIVE−fast | −72.4 | 2/9 | −20.7 | 7/4 | +103,476 | +112,673 |
| 10bp | LIVE−trim | −12.3 | 4/7 | +39.4 | 8/3 | +143,135 | +152,331 |
| 10bp | LIVE vol30 | −9.1 | 4/7 | +42.6 | 7/4 | +165,926 | +175,123 |
| 10bp | LIVE−VT | +37.9 | 4/7 | +89.6 | 10/1 | +116,464 | +125,660 |
| 10bp | BASE | −51.7 | 3/8 | 0 | — | −9,196 | 0 |
| 20bp | **LIVE** | −62.3 | 3/8 | +21.7 | 7/4 | **+85,692** | **+157,467** |
| 20bp | LIVE−fast | −115.9 | 2/9 | −31.9 | 7/4 | +22,526 | +94,301 |
| 20bp | LIVE−trim | −47.2 | 4/7 | +36.8 | 7/4 | +72,689 | +144,464 |
| 20bp | LIVE vol30 | −60.3 | 4/7 | +23.6 | 7/4 | +68,513 | +140,288 |
| 20bp | LIVE−VT | −26.2 | 4/7 | +57.7 | 10/1 | +2,560 | +74,335 |
| 20bp | BASE | −84.0 | 3/8 | 0 | — | −71,775 | 0 |

The additive-pp column flips sign vs QQQ between 4 and 10 bp; the compounded column does
not, at any cost. LIVE is the best compounded outcome of the 9 portfolios at every cost
(vol30 is within $15k of it at 4 bp). Removing the vol target scores best on additive pp
(+110 vs BASE, 10/11 paid) and worse in dollars (−$53k vs LIVE at 4 bp, −$83k at 20 bp)
because it loses more in the declines and trades bigger weight swings.

Splits (LIVE, compounded $ vs QQQ / vs BASE, and net-vs-QQQ paid count):

| split | n | 4bp $ vs QQQ | 4bp $ vs BASE | paid vs QQQ | paid vs BASE | 20bp $ vs QQQ | 20bp $ vs BASE |
|---|---|---|---|---|---|---|---|
| depth 15–25% | 7 | −132,474 | +85,977 | 1/7 | 6/7 | −174,388 | +79,998 |
| depth >25% | 4 | +375,852 | +127,812 | 3/4 | 2/4 | +260,080 | +77,470 |
| era holdout | 6 | +282,100 | +161,438 | 3/6 | 5/6 | +166,450 | +113,567 |
| era search | 5 | −38,722 | +52,351 | 1/5 | 3/5 | −80,758 | +43,901 |
| secondary 8–15% | 18 | +24,185 | +188,687 | 10/18 | 14/18 | −48,903 | +165,406 |

This is the shape of the answer. **Protection is a risk-preference dial, not a free lunch:
it costs about 10 pp (−$19k on $200k) per medium correction relative to buy-and-hold and
earns +$60k to +$220k per deep bear.** Against the base allocations it pays in both
buckets. The search era, which has no >25% episode besides 2020 and 2022 and where the
dot-com and GFC gains are absent, is where it looks worst vs QQQ (1 of 5 paid).

## 4. Per-overlay attribution (leave-one-out, variant minus LIVE)

Primary set. dP→T summed (negative = the rule was protecting), dT→R summed (positive =
the rule was costing recovery), re-entry delay attributable to the rule (LIVE sessions to
90% pre-exposure minus the variant's), and compounded $ change vs QQQ summed.

| cost | rule removed | Σ dP→T | Σ dT→R | Σ dNet | mean / median delay (sess) | Σ d$ |
|---|---|---|---|---|---|---|
| 4bp | fast re-entry | +9.6 | **−74.8** | −65.2 | −1.5 / 0 | −89,002 |
| 4bp | extension trim | −26.4 | +15.7 | −10.7 | −5.4 / 0 | −56,436 |
| 4bp | max(10,30) → vol30 | −18.5 | +21.6 | +3.0 | +0.5 / 0 | −15,502 |
| 4bp | vol target | **−72.5** | **+130.9** | +58.4 | **+30.7 / +19** | −52,919 |
| 10bp | vol target | −73.7 | +123.3 | +49.6 | +30.7 / +19 | −65,654 |
| 20bp | vol target | −75.6 | +111.7 | +36.1 | +30.7 / +19 | −83,132 |
| 20bp | extension trim | −24.0 | +39.2 | +15.1 | −5.4 / 0 | −13,003 |
| 20bp | fast re-entry | +13.0 | −66.6 | −53.6 | −1.5 / 0 | −63,166 |

Per episode (4 bp, dT→R in pp / delay in sessions), the rule that delayed re-participation:
- 2000-02: VT (+48 pp / 2 sess); removing the trim would have HURT (−16 pp: 2003 was
  extended and the trim dodged the Sep-03 and Jan-04 dips).
- 2008-09: **VT +28 pp / 108 sessions**; trim +22 pp (it held the A row at ZERO from
  2009-07-17 to 2009-10-12 while QQQ rose 35.6→42.6, see deep dive).
- 2011: VT +89 sessions but −1.8 pp (no return cost).
- 2015-16: VT 18 sessions, +2.4 pp.
- 2018 Q4: VT 28 sessions, +3.4 pp.
- 2020: VT +28.5 pp / 19 sessions; trim 0 pp (the 3 votes at the 2020-02-19 peak were
  gone by 02-26); fast overlay −1.5 pp.
- 2022: VT +10.2 pp / 49 sessions; trim +9.9 pp.
- 2025: VT +10.2 pp / 25 sessions.
- Removing the fast re-entry overlay worsened the recovery in all 11 episodes (−1.0 to
  −20.4 pp; 2008 −20.4, 2022 −11.2, 2006 −9.3, 2018 −7.1).

Paired block bootstrap (2000 resamples, blocks 20/60) on the concatenated episode
windows (3,178 sessions, 48% of the sample), LIVE vs each variant, annualised log-return
difference with 95% CI and P(≤0):

| comparison | whole window [peak, end) 4bp | recovery half only [trough, end) 4bp | recovery half 20bp |
|---|---|---|---|
| LIVE vs BASE | +8.2 pp/yr [−0.5, +17.8] P .03 / .015 | −1.6 [−13.4, +9.7] P .59; Sharpe +0.53 [+0.16, +0.92] P .004 | −4.1 P .76; Sharpe +0.37 P .02 |
| LIVE vs QQQ | +9.9 [−3.1, +23.9] P .07 / .06 | **−9.9 [−23.0, +3.3] P .94** | **−16.0 [−29.1, −3.7] P .99** |
| LIVE vs LIVE−fast | +3.3 [+0.4, +6.2] P .015 / .036 | **+8.7 [+4.7, +13.1] P .000** | +8.2 [+4.2, +12.6] P .000 |
| LIVE vs LIVE−trim | +2.1 [−2.9, +6.8] P .18 | −1.3 [−10.3, +7.1] P .58; Sharpe +0.36 [+0.04, +0.71] P .017 | −3.6 P .79 |
| LIVE vs LIVE vol30 | +0.9 [−0.7, +2.8] P .16 | **−2.1 [−3.3, −1.1] P 1.000** | −2.2 [−3.3, −1.2] P 1.000 |
| LIVE vs LIVE−VT | +2.1 [−5.0, +9.5] P .29 | **−12.4 [−20.1, −5.1] P 1.000**; Sharpe +0.11 [−0.09, +0.32] | −11.5 [−19.3, −4.4] P 1.000 |

At 10 bp LIVE vs BASE is +7.7 pp/yr (P .04 / .03); at 20 bp +6.8 (P .06 / .045). LIVE vs
QQQ over whole windows is not significant at 10 bp (P .13 / .11) or 20 bp (P .26 / .25).

## 5. Real weekly rows (actual SPMO / TQQQ), episodes with peak ≥ 2015-11

At 4 bp (10 and 20 bp in the log; totals +20.3 / +19.3 pp vs BASE):

| ep | P→T LIVE / BASE / QQQ | T→R LIVE / BASE / QQQ | T+13w LIVE / QQQ | T+26w LIVE / QQQ | expo T→R | net vs BASE | net vs QQQ | $ vs BASE |
|---|---|---|---|---|---|---|---|---|
| 2015-12 | −15.3 / −14.2 / −14.9 | 3.3 / 4.4 / 17.6 | −0.5 / 7.6 | 6.0 / 19.6 | 0.69 | −2.1 | −14.6 | −4,042 |
| 2018-08 | −17.9 / −21.7 / −18.0 | 21.4 / 13.3 / 22.5 | 15.4 / 17.5 | 23.6 / 22.1 | 0.73 | +11.9 | −0.9 | +21,911 |
| 2020-02 | −7.1 / −37.9 / −25.9 | 16.5 / 31.7 / 40.4 | 21.3 / 43.1 | 27.5 / 56.3 | 0.36 | +15.6 | −5.2 | +52,811 |
| 2021-11 | −23.9 / −24.5 / −34.1 | 48.6 / 55.4 / 52.2 | 11.5 / 20.5 | 21.1 / 38.7 | 0.66 | −6.2 | +6.6 | −8,443 |
| 2025-02 | −16.3 / −17.5 / −13.6 | 18.1 / 17.7 / 20.6 | 20.3 / 22.0 | 35.4 / 29.7 | 0.59 | +1.7 | −5.1 | +3,774 |
| sum | | | | | | **+20.9** | **−19.3** | **+66,011** |

Same shape as the proxy's search era (vs BASE +4.3 pp / +$52k, vs QQQ −32 pp): protection
pays vs the base allocations (3/5, +$66k) and loses vs QQQ (1/5). Real-row leave-one-out
on the trough→R leg agrees with the proxy: removing the fast overlay costs recovery in 4/5
(−9.1, −2.3, −7.6, −4.5 pp), removing the VT gains +20.8 (2020), +6.3 (2025), +2.6 (2018),
+2.1 (2015), removing the trim +14.8 in 2022 and ~0 elsewhere, vol30 vs max(10,30) is 0.0
everywhere on weekly rows.

## 6. Deep dives (4 bp, NAVs rebased to the peak; full paths in `recovery_study_paths.log`)

**2007-10 → 2008-11 → 2010-04.** At the 2007-10-31 peak the extension trim had all three
votes on and LIVE held ZERO risky weight (BASE 1.00). That advantage was transient: by
11-14 the state was D, votes 0, held 0.54. The decline was handled by the state machine
(E/F from 2008-01-14; 2008-06-20 to 2008-12-04 in F with one two-week C excursion) and the
VT (vol_live 61–89% from 09-30, multiplier 0.23–0.33). At the trough (2008-11-20, QQQ
−53.6%) LIVE was at 0.782 of peak, BASE 0.692, QQQ 0.467; both LIVE and BASE held 0. The
turn: fast state C on 12-05 gives eff C → LIVE re-enters at 0.30 (VT multiplier 0.30 on
66% vol) while BASE stays at 0 until the macro state flips on 12-16; both whipsaw back to F
on 2009-01-14 and 02-24. From 03-24 eff A: LIVE 0.47 → 0.58 (04-22) → 0.25 (05-06, 2
trim votes) → 0 from 07-17 to 10-12 (3 votes, QQQ 15%+ above its 200d) → 0.33 → 0.67 →
1.00 on 2010-03-08. BASE was at 1.00 from 2009-03-24 onward. LIVE NAV went 0.75 (03-10)
→ 0.985 (07-17) → flat at 0.985 for two months while QQQ rose 8% → 1.24 (2010-03-08);
BASE 0.59 → 0.77 → 1.16. So in 2008-09 the VT cost the first 4 months of the recovery
(multiplier 0.47–0.58 in Mar–Apr 2009) and the trim cost Jul–Oct 2009; the episode still
nets +$106k vs QQQ and +$19k vs BASE because the 2008 decline was −21.8% instead of
−30.8% / −53.3%.

**2020-02 → 2020-03-16 → 2020-06-05.** At the 2020-02-19 peak the trim again had 3 votes
and LIVE held 0 (pre-episode exposure 0.25, the lowest of any episode); by 02-26 state D,
0.76. The VT did the rest: vol_live 45% on 03-02 (mult 0.44), 104% at the trough (0.19),
115% on 03-17 (0.17); state E from 03-09, so LIVE held 0.09–0.14 through 03-09..04-09
while BASE held 0.50. Trough: LIVE 0.836, BASE 0.550, QQQ 0.715. The turn: fast state C on
03-30 does nothing (E,C is not in the re-entry map); state D on 04-13 and A on 04-14 with
fast B give eff A but the VT multiplier is still 0.25 (vol 80%); the multiplier reaches
0.42 on 04-30, 0.57 on 05-14, 0.78 on 05-29. Recovery window: LIVE +20.5%, BASE +46.3%,
QQQ +41.8%, average held exposure 0.35. Net: +2.8 pp / +$41k vs BASE, −9.1 pp / −$1.2k vs
QQQ (compounded, LIVE finished the window at 1.007 of peak vs QQQ 1.013). What each overlay
was doing at the turn: fast overlay idle (no mapped pair until 04-14), trim idle (votes 0
from 02-26 to 06-04, then 3 again on 06-05), VT doing all of the work and all of the
damage: it alone accounts for the +28.5 pp of recovery a no-VT book would have caught
(and the −20.5 pp it would have lost more on the way down).

## 7. What this says about each rule

- **Fast re-entry 20/100** — the rule that catches recoveries. Removing it worsens the
  recovery in 11/11 proxy episodes and 4/5 real ones; recovery-window log-return +8.7
  pp/yr with a CI that excludes zero at both block lengths and both costs. Keep.
- **Extension trim** — costs recovery only where the rebound is extended above the 200d
  (2009: 22 pp, 2023: 10 pp), helps in 2003, and earns its keep in the 18 shallow pullbacks
  (LIVE−trim: −$182k vs LIVE's +$24k against QQQ on the secondary set) and in Sharpe
  inside recoveries (+0.36, P .017). Whole-window +2.1 pp/yr, P .18. Not the culprit.
- **max(10,30) estimator** — the fast leg holds the multiplier down after a shock by
  construction ("fast down, slow up"). Its recovery cost is the most certain number in
  this study (−2.1 pp/yr, CI [−3.3, −1.1]) and also the smallest; it is repaid in the
  declines (Σ dP→T −18.5 pp) so the whole-window figure is +0.9 pp/yr, P .16, and the
  compounded $ favours keeping it by $15k. Proxy only: on weekly real rows the two
  estimators are identical. A wash; no case to simplify.
- **Vol target** — the rule that delays re-participation: mean +31 sessions, median +19,
  108 in 2008-09; recovery-window log-return −12.4 pp/yr [−20.1, −5.1] vs a no-VT book.
  It is also the biggest protector (Σ dP→T −72.5 pp) and, compounded, removing it costs
  $53k / $66k / $83k at 4 / 10 / 20 bp across the 11 episodes; on the full 26-year proxy
  the no-VT book is 22.64% / 0.831 / −49.4%, S 1.072 H 0.657 (measured through
  `evaluate`) against LIVE's 22.12% / 0.938 / −32.8%, S 1.150 H 0.780 — half a point of
  CAGR for 17 points of drawdown and a loss on both era Sharpes. Inside episode windows
  the two halves net to +2.1 pp/yr, P .29: statistically a wash, economically positive.

Distinguishing the three cases the briefing asks for: this is **"signal, but it is a
risk-preference dial"** for the vol target and the design as a whole (pays in >25%
declines, costs ~10 pp per 15–25% correction, positive compounded at every cost), **"real
signal"** for the fast re-entry overlay, and **"signal too small to matter either way"**
for the estimator choice.

## 8. What would have to be true for a simplification to be supported

- Dropping the VT: would need the deep episodes to stop happening. Every one of the 4
  >25% episodes is where the compounded edge comes from; the no-VT book is +$60k worse
  on those four at 4 bp and its full-sample drawdown is the reason the VT exists.
- Plain 30d estimator: would need the whole-window CI [−0.7, +2.8] pp/yr to resolve
  negative. It does not, and the real rows cannot see the difference at weekly cadence.
- Making the VT release faster after the trough (a shorter or asymmetric window on the
  way up) is a vol-TIMING change, the class the briefing records as failing every time
  this week; it was not tested here and this line adds no candidate to that count.

## Controls and caveats
- Same rows for every portfolio; costs applied inside `run()`; no threshold fitted.
- Both-era: LIVE beats BASE compounded in both eras (holdout +$161k, search +$52k) and
  on real rows (+$66k). It beats QQQ in holdout (+$282k) and loses in search (−$39k):
  the search era simply contains fewer and shallower bears.
- The bootstrap restricted to episode windows is the significance statement asked for;
  note the recovery-half result vs QQQ is significant NEGATIVE at 20 bp — LIVE does miss
  recoveries relative to buy-and-hold, and it is the peak→trough half that pays for it.
- Re-participation is measured against each portfolio's OWN pre-episode exposure, so a
  portfolio whose exposure was already cut at the peak (LIVE at 2007-10 and 2020-02, trim
  3 votes) has a lower bar; the absolute exposure paths in the deep dives are the honest
  comparison there.
- Additive net in pp overstates high-beta portfolios (A5050); the compounded $ column is
  the one to rank on and is what the verdict uses.
- The QQQ reference is the harness's 100% core leg (QQQ total return with dividends);
  episode dates use price closes. On real rows the QQQ reference is the `bench_qqq` column.
