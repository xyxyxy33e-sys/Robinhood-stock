# Research line `d_substate_fresh` (2026-09-19): a fresh sub-state search inside state D

Research only. Nothing here is applied; the discipline in BRIEFING.md (ADDENDUM 2026-09-10) binds. No commits, no edits
to any protected file, no new data files, no trades.
Script: `paper-track/d_substate_fresh.py` (run from the repo root; `DSF_STAGE=grid|perm|diag`, `DSF_NPERM`, `DSF_PROCS`,
`DSF_DEEP=<ids>`; grid ~5 min, permutation ~15 min on 4 cores, diagnostics ~3 min). Full log:
`paper-track/research_notes/d_substate_fresh_run.log`. No numpy exists in this environment; everything is standard library.

**Owner's question.** "Take another look into substate of D, start fresh, ignore the previous finding, test various dma
lines and other concepts." State D = QQQ below its 50d SMA, above its 200d, 50d > 200d; the live row is 100 % QLD (2x).
Should D be split into a "healthy pullback -> stay levered" half and a "deteriorating pullback -> de-risk" half, and
symmetrically, is there a "good D" half that should be MORE levered (the A row)?

The two earlier negative studies (`de_substate_search.py`, 108 candidates on nine QQQ-close signals; `downturn_review.py`
P3, gap-to-200d) were ignored as verdicts; only their evaluation scaffolding was reused. Two rules in this grid
(`gap200<2%`, `gap200<5%` -> cash/half) overlap P3 and are marked as such; everything else is new in emphasis.

## 0. Summary and verdict

- **N = 890 candidates**: 61 a-priori binary rules x 2 sides (rule true / rule false) x 5 actions (D -> 100 % cash,
  100 % SPMO, 50 % QLD / 50 % cash, 50 % QLD / 50 % XLU, the A row 50/50 SPMO/TQQQ) = 610 singles, plus 8 pre-named rules
  in 28 pairs x AND/OR x 5 actions = 280 pairs. Rule families: price vs 10/20/30/100/150d SMA, gap buckets, SMA slopes
  (20/50/100/200d over 5/10/20 sessions), SMA crossovers (20/50, 20/100, 50/100), the live fast 20/100 six-state read,
  EMA variants, episode age, depth vs 50d/200d, realised-vol regime, drawdown from the 252d high, RSI(14), consecutive
  down days, 20/60d momentum, true-range expansion, QQQ/SPY relative strength, 3m T-bill change, VIX level/percentile/change.
- **Harnesses.** (a) 26-year QQQ-core daily proxy through the project harness (standing figures reproduced and asserted:
  22.18 % / 0.913 / -33.6 %, S 1.103, H 0.768, 47.1 rebalances/yr). (b) Real DAILY instruments SPMO/TQQQ/QLD/XLU/BOXX
  2015-11-02..2026-09-04 through a mirror of `monthly_returns.simulate` that is asserted equal to the original day by day
  (baseline 29.66 % / 1.145 / -32.9 %, 72.2 % exposure, 45.2 rebalances/yr -- matches the standing "real daily 29.62 % /
  1.146"). (c) Real WEEKLY rows via `RF.eval_real` (31.35 % / 1.247 / -25.0 %). Era split as in every existing script:
  search 2015-11+ / holdout 2000-07..2015-10. The real instruments only exist in the search era; stated, not glossed.
- **Hurdles 1-2 (Sharpe up in full period and both eras): 278 of 890 pass.** That number is not evidence of anything: the
  `xlu` action passes on almost any split because the FLAT row "D -> 50 % QLD / 50 % XLU on every D day" is itself
  +0.111 / +0.029 Sharpe vs live (a row change, not a sub-state; it failed isolated validation in the 2026-08-31 XLU work
  and is not re-litigated here), and the A-row action passes with ~+0.016 in both eras on splits covering ~890 of 934 D
  days, i.e. "D -> A row everywhere", a leverage-mix dial with no timing content.
- **Hurdle 3 (exposure- and beta-matched controls): all 12 top passers pass.** Hurdle 3b (constant-D control, the same
  action on every D day): the genuine cash-side splits add +0.13..+0.22 Sharpe over their own flat row in both eras.
- **Hurdle 4 (max-statistic permutation over the whole grid, 200 common circular shifts of the D-day flag sequences):
  the null best-of-890 full-period Sharpe gain has median +0.101, 95th percentile +0.165. The best real candidate,
  #335 `D and EMA20 still above EMA50 -> cash` (+0.157), has p = 0.070; on the both-era statistic min(dS_S, dS_H) it is
  +0.127 against a null 95th of +0.132, p = 0.050. Zero of 890 candidates clear p < 0.05.** No candidate survives.
- **Survivor-style diagnostics were run anyway on the four members of the one coherent cluster** ("the fresh break below
  the 50d is the bad part of D": #335 EMA20 > EMA50, #305 fast 20/100 read not E/F, #535 QQQ not lagging SPY over 20d,
  #355 episode age <= 10). For #335: both controls pass; leave-one-regime-out +0.13..+0.18 everywhere; block bootstrap vs
  live Sharpe CI [-0.013, +0.330] P(<=0) 0.039 at 20d, 0.030 at 60d, but the log-return CI spans zero (P 0.19); **the
  threshold is a cliff** (moving the EMA20/EMA50 cross by +/-1 % turns +0.157 into -0.05..-0.08; the SMA20/SMA50 version
  is -0.008); the next-day profile across quintiles of the EMA gap is **U-shaped, not monotonic** (Q1 +39, Q2 +52, Q3
  -30, Q4 -6, Q5 +31 bp/day); and **on SPY the same rule reverses sign** (SPY-core proxy dS_S -0.100, dS_H -0.188; the SPY
  2x leg is +8 bp/day on flagged D days vs +26 bp unflagged). #305 fails the bootstrap (P 0.13-0.16) and SPY (-0.17);
  #535 fails the bootstrap (P 0.09) and its threshold sweep (-0.01 -> holdout -0.200); #355 fails the bootstrap
  (P 0.21-0.24, log-return CI [-5.1, +3.7]) and the SPY holdout (-0.146).
- **Upside test (D -> A row on a "good" half): nothing.** Best A-row candidate +0.019 / +0.016 (search / holdout) at
  22.71 % / 0.930 / -33.2 %, real daily 29.80 % / 1.169 / -33.1 % vs live 29.66 % / 1.145 / -32.9 %, and the whole A-row
  column's null 95th percentile is +0.017. There is no D half that wants more leverage than QLD.
- **Verdict: negative, on a grid that was designed to find something.** State D does not contain a sub-state that this
  project's own bar (both eras, controls, whole-grid permutation, bootstrap, threshold plateau, independent series) can
  distinguish from the best of 890 random splits. The one candidate that comes closest (#335) is a thin, cliff-shaped,
  QQQ-specific effect whose money comes from 25 D -> E breakdown episodes (+110.6 pp) against 63 D -> A episodes
  (-65.5 pp), with 2003 alone costing -22.2 pp; it helps in 41 episodes, hurts in 30, and is inert in 17. The owner
  should read this as: **D stays 100 % QLD; the previous negative conclusion is reproduced from a different direction,
  not inherited.**
- Candidate count this line: 890 (plus 5 constant-D controls, 3 exposure/beta control pairs per deep candidate, and 33
  sensitivity variants on #335 reported in full). Cumulative with earlier lines: 240 + 890.

## 1. Setup and data shim

Reproduction is through the project harness only (`exec(leverage_under_trim ... split('base=evaluate')[0])` -> `rows`,
`rr`, `run`, `evaluate`, `vt`, `RF`). The LIVE weight function is `W[eff] -> extension_scale -> vt(w, r['vol'])` with the
plain 30d estimator and the 0.05 band (read from `state.REBALANCE_DRIFT_BAND`). A `run_count` copy of
`improvement_search.run` adds a rebalance counter and is asserted to return identical daily returns.

Data shim, stated precisely (no repo file written):
- `voltarget_live_backtest.REPO` / `backtest_overlay_etf.ROBINHOOD_REPO` / `monthly_returns.REPO` are pointed at a temp
  symlink farm in the scratchpad mapping `SPMO/TQQQ/QLD/XLU.csv -> data/*_ohlc.csv` and `DGS3MO.csv -> data/dgs3mo_full.csv`,
  the same shim `funding_pct_backtest.py` documents.
- BOXX has no local file. A **synthetic `BOXX.csv`** is written from the 3-month T-bill index (`cash_index` x 100 on the
  full QQQ calendar through 2026-09-04). `monthly_returns.TAIL['BOXX']` is set to `{}` in-process: left in, the 118.07
  close it injects on 2026-08-31 lands on a ~100-based synthetic index as a fake +18 % cash-leg day (and on a 1.0-based
  index, +11,700 %). The weekly real rows read the same file, which is the T-bill index `build_cash_index()` would have
  fallen back to anyway; the weekly Sharpe reads 1.247 against the standing 1.248 for that reason.
- The real daily harness: `simulate_real()` mirrors `monthly_returns.simulate` (plain 30d `realized_vol_live`,
  `needs_rebalance` with the live band and zero-leg sweep, 4 bp), adds an override hook applied before the vol target on
  D days, and counts exposure and rebalances. With the hook off it is asserted equal to `MR.simulate` on every session.
- Signals are computed on the QQQ calendar extended BACKWARD to 1998-01 with the FRED NASDAQ-100 index rescaled at the
  1999-09-15 splice, purely so the 252-session lookbacks (dd252, vol/VIX percentiles) exist by 2000-07. Macro states,
  fast states and episode age are taken from the QQQ-only classifier (asserted equal to the rows' state sequence).
  T-bill values are lagged one session (FRED publishes next morning). VIX is the same-day close (known at the close).

State D: 934 proxy days (14.2 %), 382 in the search era, 552 in the holdout; 88 episodes; 382 D days on the real daily
rows. `eff == state` on every D day (the fast overlay never touches D).

## 2. Screening table: next-day QLD-leg return on D days, rule true vs rule false (bp/day, t of difference)

The one table in this line that needs no harness. Every rule, both eras. `nF` = D days where the rule is true.

| rule | family | nF | true | false | t | S: nF | true | false | t | H: nF | true | false | t |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| px<sma10 | DMA-line | 606 | 20 | 14 | 0.3 | 265 | 21 | 27 | -0.2 | 341 | 19 | 7 | 0.6 |
| px<sma20 | DMA-line | 693 | 20 | 11 | 0.5 | 306 | 20 | 32 | -0.4 | 387 | 20 | 1 | 0.9 |
| px<sma30 | DMA-line | 765 | 18 | 16 | 0.1 | 338 | 16 | 69 | -1.3 | 427 | 19 | -2 | 1.0 |
| px<sma100 | DMA-line | 438 | 37 | 1 | 1.9 | 162 | 52 | 1 | 1.5 | 276 | 28 | 1 | 1.3 |
| px<sma150 | DMA-line | 129 | 17 | 18 | -0.0 | 41 | 10 | 24 | -0.2 | 88 | 20 | 14 | 0.2 |
| gap50<-2% | depth | 425 | 32 | 6 | 1.4 | 190 | 49 | -4 | 1.6 | 235 | 18 | 12 | 0.3 |
| gap50<-6% | depth | 29 | 189 | 12 | 2.4 | 11 | 210 | 17 | 1.2 | 18 | 175 | 9 | 2.4 |
| gap200<2% | depth (P3) | 144 | -12 | 23 | -1.3 | 46 | -47 | 32 | -1.4 | 98 | 5 | 17 | -0.4 |
| gap200>10% | depth | 94 | 63 | 13 | 1.8 | 47 | 56 | 18 | 0.8 | 47 | 70 | 9 | 1.8 |
| slope50_10<0 | slope | 430 | 31 | 6 | 1.4 | 159 | 32 | 16 | 0.5 | 271 | 31 | -1 | 1.5 |
| slope200_20<0 | slope | 46 | 45 | 16 | 1.0 | 10 | 127 | 20 | 2.1 | 36 | 22 | 14 | 0.2 |
| sma20<sma50 | cross | 613 | 18 | 18 | 0.0 | 220 | 23 | 22 | 0.0 | 393 | 15 | 13 | 0.1 |
| sma50<sma100 | cross | 73 | 2 | 19 | -0.5 | 24 | -13 | 25 | -0.5 | 49 | 9 | 15 | -0.1 |
| fast_CDEF | fast 20/100 | 814 | 21 | -5 | 1.2 | 349 | 21 | 38 | -0.4 | 465 | 21 | -21 | 1.7 |
| fast_EF | fast 20/100 | 374 | 44 | 0 | 2.3 | 149 | 51 | 4 | 1.4 | 225 | 39 | -2 | 1.8 |
| ema20<ema50 | EMA | 481 | 44 | -10 | 2.9 | 173 | 60 | -8 | 2.1 | 308 | 34 | -11 | 2.1 |
| age>10 | age | 345 | 37 | 6 | 1.7 | 85 | 71 | 8 | 1.9 | 260 | 26 | 4 | 1.0 |
| age>20 | age | 137 | 36 | 15 | 1.0 | 11 | -21 | 24 | -0.6 | 126 | 41 | 7 | 1.5 |
| volratio>1.3 | vol | 177 | -6 | 23 | -1.1 | 101 | -14 | 36 | -1.2 | 76 | 5 | 16 | -0.3 |
| vol30pct>0.8 | vol | 288 | 12 | 20 | -0.4 | 122 | 17 | 25 | -0.2 | 166 | 9 | 17 | -0.3 |
| dd252<-5% | drawdown | 575 | 28 | 1 | 1.5 | 246 | 41 | -11 | 1.7 | 329 | 19 | 9 | 0.5 |
| dd252<-10% | drawdown | 64 | 155 | 8 | 2.6 | 31 | 162 | 10 | 1.6 | 33 | 148 | 6 | 2.1 |
| rsi<30 | RSI | 13 | 276 | 14 | 2.3 | 7 | 288 | 18 | 1.8 | 6 | 262 | 12 | 1.3 |
| rsi<50 | RSI | 717 | 21 | 6 | 0.8 | 307 | 18 | 41 | -0.7 | 410 | 24 | -12 | 1.7 |
| mom20<-5% | momentum | 212 | 64 | 4 | 2.4 | 88 | 74 | 7 | 1.4 | 124 | 57 | 2 | 2.0 |
| range>1.6 | range | 137 | 39 | 14 | 0.7 | 85 | 15 | 25 | -0.2 | 52 | 78 | 8 | 1.6 |
| rs_spy20<0 | rel. strength | 683 | 30 | -17 | 2.1 | 286 | 37 | -21 | 1.4 | 397 | 26 | -14 | 1.6 |
| tb60>0 | rates | 455 | 9 | 26 | -0.9 | 170 | 9 | 33 | -0.7 | 285 | 9 | 20 | -0.5 |
| vix>20 | VIX | 326 | 32 | 10 | 1.0 | 145 | 61 | -1 | 1.7 | 181 | 9 | 17 | -0.3 |
| vix5>0 | VIX | 489 | 1 | 36 | -1.9 | 204 | 1 | 47 | -1.4 | 285 | 2 | 28 | -1.3 |

(All 61 rows are in the run log.) The striking regularity is that **every "deteriorating" flag has the WRONG sign for
a de-risk rule**: deeper below the 50d (+189 bp/day at gap50 < -6 %), deeper drawdown (+155 bp at dd252 < -10 %),
oversold RSI (+276 bp), a 5 %+ 20-day loss (+64 bp), a fast read already in E/F (+44 bp), an EMA20 already under EMA50
(+44 bp) -- those D days are the mean-reversion days, and the QLD leg earns its keep there. The days that lose money in
D are the **fresh** ones: the first sessions after the close drops through the 50d, before the faster lines have
confirmed anything (EMA20 still above EMA50: -10 bp/day; fast read still A/B: -5 bp; QQQ still ahead of SPY: -17 bp;
VIX up on the week: +1 bp). No single flag separates D days at more than t = 2.9 on 934 observations, and nothing
in the vol / VIX / rates families separates them at all.

## 3. Grid results

Baselines: proxy 22.18 % / 0.913 / -33.6 %, exposure 67.7 %, 47.1 rebalances/yr, S 1.103, H 0.768; real daily 29.66 % /
1.145 / -32.9 %, exposure 72.2 %, 45.2 reb/yr; real weekly 31.35 % / 1.247 / -25.0 %.

### 3a. Constant-D controls (the action on every D day: a row change, not a sub-state)

| flat row | CAGR / Sharpe / MaxDD | exp | dS_S | dS_H | dS_F | real daily | real weekly Sh |
|---|---|---|---|---|---|---|---|
| D -> 100 % cash | 16.71 % / 0.854 / -28.5 % | 54.4 % | -0.018 | -0.084 | -0.059 | 23.11 % / 1.164 / -23.0 % | 1.150 |
| D -> 100 % SPMO | 20.04 % / 0.943 / -28.9 % | 67.7 % | +0.066 | +0.007 | +0.030 | 26.19 % / 1.221 / -23.2 % | 1.244 |
| D -> 50 % QLD / 50 % cash | 19.79 % / 0.934 / -29.2 % | 61.1 % | +0.059 | -0.004 | +0.021 | 26.88 % / 1.231 / -21.8 % | 1.266 |
| D -> 50 % QLD / 50 % XLU | 21.41 % / 0.974 / -28.6 % | 67.7 % | +0.111 | +0.029 | +0.062 | 28.85 % / 1.275 / -21.7 % | 1.317 |
| D -> A row 50/50 SPMO/TQQQ | 22.71 % / 0.930 / -33.2 % | 67.7 % | +0.019 | +0.016 | +0.017 | 29.80 % / 1.169 / -33.1 % | 1.247 |

The XLU row is the one to know about: it is a 26-year Pareto-ish improvement on the proxy (Sharpe and MaxDD better, CAGR
0.8 pp lower) and better on both real harnesses. It is NOT a sub-state finding and it is NOT new: STRATEGY.md records that
XLU in D "looked promising ... but FAILED isolated validation" on 2026-08-31, and the 2026-09-01 episode-by-episode
check found XLU helps in 9 of 28 episodes. Every `-> xlu` split in the grid inherits this row's gain; the split's own
contribution is what section 3c prices.

### 3b. Hurdle 1-2 passers (Sharpe up in full period and both eras): 278 of 890, top 25 by full-period gain

| # | candidate | nOn | dS_S | dS_H | dS_F | CAGR | MaxDD | exp | real daily Sh | real weekly Sh | perm p |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 335 | NOT ema20<ema50 -> cash | 453 | +0.206 | +0.127 | +0.157 | 24.34 % | -32.0 % | 61.2 % | 1.385 | 1.282 | 0.070 |
| 338 | NOT ema20<ema50 -> xlu | 453 | +0.147 | +0.095 | +0.115 | 24.20 % | -30.9 % | 67.7 % | 1.308 | 1.306 | 0.230 |
| 336 | NOT ema20<ema50 -> spmo | 453 | +0.143 | +0.082 | +0.105 | 23.57 % | -30.4 % | 67.7 % | 1.335 | 1.287 | 0.370 |
| 337 | NOT ema20<ema50 -> half | 453 | +0.140 | +0.077 | +0.101 | 23.46 % | -30.5 % | 64.5 % | 1.306 | 1.298 | 0.500 |
| 428 | NOT dd252<-10% -> xlu | 870 | +0.151 | +0.068 | +0.101 | 22.85 % | -28.0 % | 67.7 % | 1.315 | 1.350 | 0.500 |
| 358 | NOT age>10 -> xlu | 589 | +0.140 | +0.077 | +0.100 | 23.21 % | -28.6 % | 67.7 % | 1.304 | 1.361 | 0.500 |
| 188 | NOT slope50_10<0 -> xlu | 504 | +0.113 | +0.088 | +0.097 | 23.56 % | -29.7 % | 67.7 % | 1.271 | 1.374 | 0.550 |
| 305 | NOT fast_EF -> cash | 560 | +0.136 | +0.070 | +0.096 | 22.83 % | -32.7 % | 59.8 % | 1.310 | 1.110 | 0.565 |
| 535 | NOT rs_spy20<0 -> cash | 251 | +0.126 | +0.068 | +0.093 | 23.73 % | -39.5 % | 64.2 % | 1.287 | 1.188 | 0.630 |
| 368 | NOT age>20 -> xlu | 797 | +0.112 | +0.082 | +0.091 | 22.49 % | -28.6 % | 67.7 % | 1.276 | 1.313 | 0.655 |
| 178 | NOT slope50_5<0 -> xlu | 437 | +0.117 | +0.070 | +0.089 | 23.59 % | -30.3 % | 67.7 % | 1.273 | 1.349 | 0.735 |
| 108 | NOT gap50<-6% -> xlu | 905 | +0.134 | +0.055 | +0.087 | 22.26 % | -28.9 % | 67.7 % | 1.298 | 1.305 | 0.780 |
| 498 | NOT mom20<-5% -> xlu | 722 | +0.122 | +0.059 | +0.085 | 22.91 % | -29.0 % | 67.7 % | 1.281 | 1.312 | 0.855 |
| 355 | NOT age>10 -> cash | 589 | +0.137 | +0.050 | +0.080 | 21.38 % | -29.8 % | 59.4 % | 1.323 | 1.322 | 0.950 |
| 258 | NOT slope200_20<0 -> xlu | 888 | +0.132 | +0.043 | +0.079 | 21.94 % | -28.6 % | 67.7 % | 1.297 | 1.327 | 0.955 |
| 438 | NOT rsi<30 -> xlu | 921 | +0.133 | +0.041 | +0.078 | 21.97 % | -28.6 % | 67.7 % | 1.299 | 1.330 | 0.960 |
| 138 | NOT gap200>10% -> xlu | 840 | +0.116 | +0.053 | +0.078 | 22.11 % | -28.6 % | 67.7 % | 1.280 | 1.321 | 0.960 |
| 356 | NOT age>10 -> spmo | 589 | +0.125 | +0.050 | +0.077 | 22.21 % | -27.4 % | 67.7 % | 1.277 | 1.314 | 0.970 |
| 308 | NOT fast_EF -> xlu | 560 | +0.117 | +0.050 | +0.077 | 23.15 % | -30.7 % | 67.7 % | 1.276 | 1.247 | 0.970 |
| 768 | (sma20<sma50 OR volratio>1.0) -> xlu | 853 | +0.106 | +0.056 | +0.076 | 22.04 % | -28.6 % | 67.7 % | 1.269 | 1.320 | 0.980 |
| 426 | NOT dd252<-10% -> spmo | 870 | +0.107 | +0.055 | +0.076 | 21.70 % | -27.4 % | 67.7 % | 1.260 | 1.268 | 0.980 |
| 306 | NOT fast_EF -> spmo | 560 | +0.104 | +0.053 | +0.073 | 22.79 % | -31.3 % | 67.7 % | 1.298 | 1.206 | 1.000 |
| 357 | NOT age>10 -> half | 589 | +0.121 | +0.045 | +0.073 | 22.07 % | -27.4 % | 63.6 % | 1.293 | 1.337 | 1.000 |
| 248 | NOT slope200_10<0 -> xlu | 888 | +0.119 | +0.040 | +0.071 | 21.74 % | -28.6 % | 67.7 % | 1.284 | 1.333 | 1.000 |
| 495 | NOT mom20<-5% -> cash | 722 | +0.094 | +0.056 | +0.071 | 21.34 % | -28.3 % | 57.3 % | 1.269 | 1.192 | 1.000 |

Composition of the 278: 94 `xlu` (median 722 of 934 D days flagged, i.e. mostly the flat XLU row), 75 `arow` (all
~+0.016, mostly "A row everywhere"), 49 `spmo`, 47 `half`, 13 `cash`. Pairs: 67 of 280 pass; the best pair
(`sma20<sma50 OR volratio>1.0 -> xlu`, +0.106 / +0.056) is below the best single of its action, so pairing adds nothing.
Rebalances: every candidate stays within 46-52/yr against live's 47.1.

Note the convention: rules were named in the "deteriorating" direction, so the passers are almost all `NOT <rule>`:
the money is on the *un-deteriorated* side of D. That is the reverse of the "deteriorating -> de-risk" hypothesis.

### 3c. Split value over the flat row (what the sub-state itself adds, both eras)

| # | candidate | vs flat row: S | H | F | real daily Sh |
|---|---|---|---|---|---|
| 335 | NOT ema20<ema50 -> cash | +0.225 | +0.211 | +0.215 | +0.221 |
| 305 | NOT fast_EF -> cash | +0.155 | +0.154 | +0.155 | +0.146 |
| 355 | NOT age>10 -> cash | +0.155 | +0.133 | +0.138 | +0.159 |
| 535 | NOT rs_spy20<0 -> cash | +0.144 | +0.152 | +0.152 | +0.123 |
| 495 | NOT mom20<-5% -> cash | +0.112 | +0.140 | +0.130 | +0.105 |
| 337 | NOT ema20<ema50 -> half | +0.081 | +0.081 | +0.080 | +0.075 |
| 336 | NOT ema20<ema50 -> spmo | +0.077 | +0.075 | +0.075 | +0.114 |
| 338 | NOT ema20<ema50 -> xlu | +0.036 | +0.066 | +0.053 | +0.033 |
| 428 | NOT dd252<-10% -> xlu | +0.040 | +0.039 | +0.039 | +0.040 |
| 358 | NOT age>10 -> xlu | +0.029 | +0.048 | +0.038 | +0.029 |
| 188 | NOT slope50_10<0 -> xlu | +0.002 | +0.059 | +0.035 | -0.004 |
| 768 | (sma20<sma50 OR volratio>1.0) -> xlu | -0.005 | +0.027 | +0.014 | -0.006 |

Only the cash-action members of the "fresh break" cluster carry a split value that is not the XLU row in disguise.

### 3d. Hurdle 3: exposure- and beta-matched controls (full proxy)

| # | candidate | cand Sh | exp | k_exp | ctrl Sh | beta | k_beta | beta-ctrl Sh | vs ctrl S / H |
|---|---|---|---|---|---|---|---|---|---|
| 335 | NOT ema20<ema50 -> cash | 1.069 | 61.2 % | 0.903 | 0.920 | 1.14 | 0.897 | 0.920 | +0.198 / +0.121 |
| 305 | NOT fast_EF -> cash | 1.009 | 59.8 % | 0.882 | 0.922 | 1.11 | 0.875 | 0.922 | +0.127 / +0.063 |
| 535 | NOT rs_spy20<0 -> cash | 1.005 | 64.2 % | 0.947 | 0.917 | 1.20 | 0.944 | 0.918 | +0.119 / +0.065 |
| 338 | NOT ema20<ema50 -> xlu | 1.027 | 67.7 % | 1.000 | 0.913 | 1.22 | 0.961 | 0.916 | +0.147 / +0.095 |

All 12 top passers and the 3 near-misses pass both controls (the controls barely move: de-levering live to 88-95 % of
its capital costs it ~0.01 Sharpe, so these are cheap hurdles for a rule that only touches 14 % of days).

### 3e. Hurdle 4: max-statistic permutation over the whole grid

Null: each draw applies ONE random circular shift to every rule's true/false sequence along the 934 D days (episode
structure and the dependence between the 890 candidates preserved), re-runs all 890 through the harness, and records
the best gain. 200 draws, 911 s on 4 cores.

| statistic | null median | null 95th | null max | best real candidate | value | p |
|---|---|---|---|---|---|---|
| best full-period Sharpe gain | +0.101 | +0.165 | +0.217 | #335 NOT ema20<ema50 -> cash | +0.157 | **0.070** |
| best both-era gain min(dS_S, dS_H) | +0.074 | +0.132 | +0.197 | #335 | +0.127 | **0.050** |
| per-action null 95th (full gain) | cash +0.165, spmo +0.096, half +0.100, xlu +0.113, arow +0.017 | | | | | |

Per-candidate p against the whole-grid null: 0 of 890 below 0.05, 1 below 0.10 (#335). A random re-placement of the
same flag pattern inside D typically produces a "both-era +0.07" candidate and one time in twenty a "+0.13".
The best real candidate sits exactly at that boundary.

## 4. Deep diagnostics on the near-misses

Run on the four cash-side members of the cluster (`DSF_DEEP=335,305,535,355`). Bootstrap = paired circular block
bootstrap, 2,000 draws, blocks 20 and 60 sessions. LORO windows as in `block_bootstrap.REGIMES`.

### 4a. #335 `D and EMA20 still above EMA50 -> 100 % cash` (on 453 of 934 D days; S 209, H 244)

- proxy 24.34 % / 1.069 / -32.0 %, exposure 61.2 %, 47.5 reb/yr, S 1.309 (+0.206), H 0.895 (+0.127); real daily 31.97 % /
  1.385 / -27.9 % (exp 65 %, 45 reb/yr); real weekly 29.10 % / 1.282 / -25.0 % (CAGR *below* live's 31.35 %).
- **Threshold sensitivity (cliff).** The rule is "EMA20/EMA50 - 1 < 0 -> hold QLD, else cash":

  | variant | nOn | CAGR / Sharpe / MaxDD | dS_S | dS_H | dS_F |
  |---|---|---|---|---|---|
  | gap < -2 % | 933 | 16.80 % / 0.858 / -28.5 % | -0.009 | -0.084 | -0.055 |
  | gap < -1 % | 857 | 17.74 % / 0.881 / -28.5 % | -0.018 | -0.035 | -0.032 |
  | **gap < 0 (the candidate)** | 453 | 24.34 % / 1.069 / -32.0 % | +0.206 | +0.127 | +0.157 |
  | gap < +1 % | 103 | 20.13 % / 0.864 / -33.6 % | -0.005 | -0.080 | -0.049 |
  | gap < +2 % | 12 | 22.40 % / 0.923 / -33.6 % | +0.015 | +0.007 | +0.010 |
  | EMA25 < EMA50 | 526 | 23.07 % / 1.036 / -29.0 % | +0.127 | +0.127 | +0.123 |
  | EMA30 < EMA50 | 601 | 22.45 % / 1.025 / -28.3 % | +0.064 | +0.155 | +0.112 |
  | EMA20 < EMA60 | 562 | 22.22 % / 1.009 / -29.0 % | +0.054 | +0.134 | +0.097 |
  | EMA15 < EMA50 | 377 | 21.73 % / 0.960 / -31.3 % | +0.042 | +0.055 | +0.048 |
  | EMA10 < EMA50 | 294 | 21.95 % / 0.948 / -32.0 % | +0.049 | +0.025 | +0.035 |
  | EMA20 < EMA40 | 356 | 21.16 % / 0.938 / -31.3 % | +0.044 | +0.016 | +0.026 |
  | EMA20 < EMA100 | 820 | 17.00 % / 0.847 / -28.5 % | -0.045 | -0.073 | -0.066 |
  | SMA20 < SMA50 | 321 | 20.16 % / 0.905 / -32.1 % | +0.007 | -0.013 | -0.008 |
  | SMA20 < SMA60 | 415 | 22.35 % / 0.994 / -31.3 % | +0.135 | +0.049 | +0.082 |
  | SMA25 < SMA50 | 390 | 20.84 % / 0.939 / -33.3 % | +0.010 | +0.045 | +0.026 |
  | SMA30 < SMA50 | 443 | 21.26 % / 0.961 / -33.3 % | +0.091 | +0.024 | +0.048 |

  The exact crossover (gap 0) is a plateau across neighbouring EMA window pairs (25/50, 30/50, 20/60 all both-era
  positive, +0.10..+0.12 full) but a cliff in the gap dimension (+/-1 % kills it), and the SMA analogue of the very same
  pair is -0.008. That is the signature of a rule whose value is the exact day the fast line crosses, not a regime.
- **Profile is U-shaped, not monotonic** (next-day QLD-leg return by search-era quintile of the EMA20/EMA50 gap, bp/day, t
  vs the rest): full Q1 +39 (t +1.4), Q2 +52 (+2.0), Q3 -30 (-2.5), Q4 -6 (-1.3), Q5 +31 (+0.6); holdout Q1 +38, Q2 +37, Q3
  -34, Q4 -12, Q5 +39. The top quintile (EMA20 well above EMA50, the freshest breaks) is *positive*; the loss sits in the
  middle two quintiles. A monotone "deteriorating -> worse" relation would show the opposite.
- Flagged-vs-unflagged: full +44 vs -10 bp/day (t +2.9), search +60 vs -8 (t +2.1), holdout +34 vs -11 (t +2.1);
  QQQ leg +22 vs -4 bp.
- **SPY, same rule on an SPY-classified, SPY-signalled, SPY-core proxy** (live on SPY 12.94 % / 0.660 / -41.6 %, S 0.926,
  H 0.456; 896 SPY D days): **8.62 % / 0.508 / -45.1 %, dS_S -0.100, dS_H -0.188, dS_F -0.152.** On SPY's D days the 2x leg
  is +8 bp on flagged days vs +26 bp unflagged (t -1.3): the sign reverses.
- Block bootstrap: vs live Sharpe CI [-0.013, +0.330] P(<=0) 0.039 (20d) / [-0.004, +0.318] 0.030 (60d), log-return
  [-2.19, +5.80] pp/yr P(<=0) 0.196 / 0.185; vs exposure-matched live Sharpe [-0.021, +0.325] 0.046 / 0.035, log-return
  [-0.47, +7.12] 0.050 / 0.038; vs its flat row Sharpe [+0.044, +0.399] 0.009 / 0.007. A Sharpe edge that is barely
  distinguishable from zero and a return edge that is not.
- LORO (Sharpe / log-return vs live): drop dot-com +0.176 / +1.94 pp; GFC +0.171 / +1.99; COVID +0.147 / +1.75; 2022 +0.165
  / +1.74; whole SPMO era +0.127 / +1.77. Robust to any one regime -- because the money is not in the crashes.
- Where the money is (log-return difference on override days): 2003 -22.2 pp, 2024 +18.5, 2010 +13.9, 2007 +13.7, 2013
  -13.5, 2009 -13.1, 2016 +12.6, 2025 -12.2; 16 of 24 years positive. Episode level (88 D episodes): helps 41, hurts 30,
  inert 17; exits to E (25 episodes) +110.6 pp, exits to A (63 episodes) -65.5 pp; the top 8 episodes are 197 % of the
  net (+45.1 pp). The worst six are all short episodes the rule sat out entirely (2018-02, 2021-05, 2003-08, 2015-12,
  2020-10, 2025-11: -7 to -10 pp each).
- Mechanism check: EMA20 > EMA50 days are early-episode (median age 3 vs 13 sessions), but the separation persists inside
  age buckets (age 6-10: -86 bp unflagged vs +41 flagged; age 11-20: -62 vs +57), so it is not purely age. The same
  separation does not exist on SPY.

### 4b. #305 `D and fast 20/100 read not E/F -> cash` (560 days) -- the owner's fast-read splitter

proxy 22.83 % / 1.009 / -32.7 %, S +0.136, H +0.070; real daily 30.49 % / 1.310 / -29.2 %; real weekly 24.73 % / 1.110 /
-25.0 % (*worse* than live on both weekly figures); perm p 0.565. Split over flat row +0.155 / +0.154. Profile: fast
E/F days +44 bp vs +0 bp (t +2.3), holdout +39 vs -2 (t +1.8). SPY: 8.18 % / 0.489, dS_S -0.071, dS_H -0.248 (reverses).
Bootstrap vs live Sharpe CI [-0.070, +0.256] P 0.128 / 0.138, log-return P 0.40. LORO +0.07..+0.11. Years positive 11 of
25; 2005 +24.8 pp, 2003 -22.2, 2010 +21.6, 2021 -14.4, 2025 -14.3. The reading that the fast overlay uses to ADD exposure
in B/C/F does not carry a D split; using `fast_CDEF` instead (fast reads anything but A/B) is +0.108 / +0.025 with XLU and
nothing with cash.

### 4c. #535 `D and QQQ not lagging SPY over 20 sessions -> cash` (251 days)

proxy 23.73 % / 1.005 / **-39.5 %** (MaxDD 6 pp worse than live), S +0.126, H +0.068; real daily 32.05 % / 1.287 /
-33.6 %; perm p 0.630. Threshold sweep is a cliff: at -1 % the holdout is -0.200, at -2 % -0.136. Quintile profile
non-monotonic in both eras (holdout Q4 +75 bp t +2.9 next to Q5 -17 bp). Bootstrap vs live Sharpe P 0.086 / 0.087,
log-return P 0.21. Not computable on SPY. Money: 2020 +17.2 pp, 2018 -16.1, 2010 +14.7.

### 4d. #355 `D and episode age <= 10 -> cash` (589 days)

proxy 21.38 % / 0.992 / -29.8 %, S +0.137, H +0.050; real daily 28.29 % / 1.323 / -29.6 % (CAGR 1.4 pp below live);
perm p 0.950. Age sweep: >0 +0.026/+0.005, >5 -0.014/+0.016, **>10 +0.137/+0.050**, >15 +0.048/-0.002, >20 -0.039/+0.040 --
a spike at one value. Bootstrap vs live Sharpe CI [-0.108, +0.267] P 0.21-0.24, log-return [-5.07, +3.71] P 0.61-0.63.
SPY dS_S +0.078, dS_H -0.146. LORO log-return negative in every window (-0.1 to -1.1 pp/yr). Years positive 13 of 25.

### 4e. Reference (not part of the grid)

The previously studied QQEW/QQQ 60d-change bottom-quintile D gate (`breadth_signal`, `dgate_anatomy`), on the same
4,800 rows 2007-07-27..2026-08-26: live 26.09 % / 1.006 (S 1.103, H 0.876) -> gate 31.71 % / 1.218 (S 1.332, H 1.065) on
124 gated days. Reproduced here for scale only. It remains the only D-conditional rule this project has seen with a
holdout gain of that size, and its own note explains why it is a "candidate for a forward test", not a change.

## 5. What was learned, and what would have to be true

1. **D's losing days are the fresh break, not the deep one.** Across 61 rules the sign is consistent: every measure of
   "the pullback has deepened / confirmed" (price far below the 50d, 10 %+ drawdown, RSI < 30, EMA20 under EMA50, fast
   read in E/F, 5 %+ 20-day loss) marks D days on which the QLD leg does *well* (+44 to +276 bp/day); the negative
   next-day returns sit on the first sessions after the 50d break, before anything has confirmed. A "deteriorating
   pullback -> de-risk" split therefore has the sign backwards; the only splits that gain are "un-confirmed pullback ->
   cash", which means selling into the first days of every D episode and buying back once the faster lines have crossed
   -- exactly the behaviour the 2026-09-06 fast re-entry overlay was built to avoid in B/C/F.
2. **No D half wants more leverage.** The A-row action is a flat +0.016 both eras on almost any split and its whole
   column's permutation null 95th is +0.017. The "healthy pullback -> lever up" hypothesis is empty on 26 years.
3. **The XLU row in D is the strongest flat effect in the grid** (+0.111 / +0.029 Sharpe, MaxDD -28.6 % vs -33.6 %,
   real daily 1.275 vs 1.145) and was already rejected on isolated validation in August. It is a row-composition question
   for the owner, not a sub-state, and it is not re-opened by this line.
4. **The best split (#335) is a near-miss that fails four independent ways**: whole-grid permutation p 0.070 / 0.050;
   a +/-1 % threshold cliff with the SMA analogue at -0.008; a U-shaped rather than monotonic profile; and a sign
   reversal on SPY. Its log-return advantage is not distinguishable from zero (bootstrap P 0.19), it costs 1.4 pp of
   real weekly CAGR, and 2003 alone costs it -22 pp.

For any of these to be adopted, all of the following would have to be true, and it is the owner's decision, not this
line's: (i) a pre-registered rule (e.g. #335 exactly as written, or the EMA25/50 variant) held fixed and then confirmed
on live D episodes that did not exist when it was found; (ii) a plateau, not a cliff, in the gap dimension; (iii) the
same sign on SPY or a stated reason the effect is Nasdaq-specific; (iv) a whole-grid permutation p below 0.05 and a
bootstrap log-return interval that excludes zero; (v) a real-instrument CAGR that does not fall (the weekly harness says
it does). None of (ii)-(v) holds today.

**Verdict: D stays 100 % QLD. The fresh grid of 890 candidates, built to find a split and including the upside
direction, finds nothing that beats the best of 890 random splits of the same shape.**

## 6. Candidate inventory

- 61 rules (families and counts): DMA-line 5, DMA-gap 3, DMA-depth 6 (two overlap P3), DMA-slope 12, DMA-cross 3,
  DMA-fast 2, DMA-ema 3, DMA-age 3, vol 4, drawdown 2, RSI 3, streak 2, momentum 3, range 2, relative strength 2, rates 2,
  VIX 4.
- 2 sides x 5 actions -> 610 singles; 8 pre-named rules (`px<sma20`, `slope50_10<0`, `sma20<sma50`, `fast_CDEF`,
  `age>10`, `volratio>1.0`, `dd252<-5%`, `vixpct>0.8`) in 28 pairs x AND/OR x 5 actions -> 280 pairs. **N = 890.**
- Controls: 5 constant-D rows; exposure and beta controls on 15 candidates; 33 threshold/window variants of #335;
  5 of #535; 5 of #355; 4 deep candidates through the SPY-core proxy, bootstrap and LORO.
- Thresholds: fixed a priori (round numbers, zero crossings, the live 20/100 windows) or trailing-252 percentiles;
  the only search-era-fitted cut-offs are the quintile boundaries in the profile tables, which are diagnostic, not
  part of any candidate.
