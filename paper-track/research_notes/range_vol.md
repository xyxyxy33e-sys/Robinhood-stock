# range_vol -- range-based realized-vol estimators for the vol overlay (2026-09-08)

Research line 3. RESEARCH ONLY under the change freeze; nothing applied.
Script: `paper-track/range_vol.py` (176 s, prints every table below).
New data: `data/qqq_ohlc.csv`.

## Verdict: NO SIGNAL (0 of 41 candidates beat live on both eras, exposure-matched)

The estimators are correct and more precise, and the extra precision is real
in the data -- but it lives in the CALM region where a cap-1.0 vol target does
nothing, and disappears in the high-vol region where the overlay actually
bites. Once exposure is matched, every range variant is inside +/-0.05 Sharpe
of live on the proxy, and every one loses on the real weekly and real daily
instruments.

## 1. Data: data/qqq_ohlc.csv (provenance)

- Source: Robinhood `get_equity_historicals`, symbol QQQ, interval `day`,
  bounds `regular`, `adjustment_type=split` (the project's convention), pulled
  in two chunks (1999-09-01..2013-12-31 and 2014-01-01..2026-09-05, the tool
  caps at 5000 bars per call) plus a 3-day call to recover 2013-12-31, which
  fell between the chunks. Interpolated gap-fill bars (`interpolated=true`)
  were dropped.
- Alpha Vantage `TIME_SERIES_DAILY outputsize=full` was tried first and is a
  premium-only feature on this key (error returned); not used.
- EODHD (free, 1-year cap) used as an independent cross-check only.
- Span: 1999-09-15 .. 2026-09-04, 6784 sessions, columns `d,o,h,l,c`.
  Identical date set to `data/qqq_long_history.csv`.
- Cross-checks: closes AND opens match `qqq_long_history.csv` to the cent on
  6784/6784 days (0 mismatches > $0.01). Against EODHD on the 251 overlapping
  days, o/h/l/c all agree within $0.005 (max diff 0.005, 0 above 1 cent).
  The QQQ 2:1 split of 2000-03-20 is consistently adjusted (103-116 around
  the split, same as the long history). No H<max(O,C) or L>min(O,C)
  violations; no zero-range bars.

## 2. Estimators (paper-track/range_vol.py, drop-in for state.realized_vol)

Parkinson (H/L), Garman-Klass (OHLC), Rogers-Satchell (OHLC, drift-robust),
Yang-Zhang (overnight + open-close + RS, the gap-aware one), plus GKJ
(GK + squared overnight jump) and a causal bias-corrected `bcGK10`
(GK10 x trailing cc/GK level ratio, window min(252, available) >= 60).
All annualised x252, lookbacks 5/10/20/30, causal (bars <= as_of only). The
close-to-close legs use `state.realized_vol` unchanged (verified identical to
r['vol'] / r['vol10'] on every row, max diff 0.0).

Synthetic GBM verification (390 steps/day, 12,000 days, true sigma 20%),
bias = E[sigma_hat]/sigma, eff = Var(cc variance est.)/Var(estimator):

| overnight share | n | P | GK | RS | GKJ | YZ | cc |
|---|---|---|---|---|---|---|---|
| 0% | 10 | 0.964 / 5.7x | 0.952 / 9.2x | 0.952 / 7.4x | 0.952 / 9.2x | 0.957 / 8.5x | 0.995 / 1.0x |
| 0% | 30 | 0.964 / 5.2x | 0.952 / 8.5x | 0.952 / 6.7x | 0.952 / 8.5x | 0.958 / 7.7x | 0.993 / 1.0x |
| 30% | 10 | 0.806 / 11.4x | 0.796 / 18.4x | 0.796 / 14.9x | 0.968 / 6.7x | 0.971 / 6.1x | 1.003 / 1.0x |
| 30% | 30 | 0.806 / 9.5x | 0.796 / 15.8x | 0.796 / 12.5x | 0.968 / 5.8x | 0.971 / 5.4x | 1.002 / 1.0x |

All recover sigma to within the known few-percent discrete-sampling bias when
there is no overnight gap; P/GK/RS drop to ~0.80 of sigma when 30% of the
variance is overnight (they cannot see it); YZ and GKJ stay unbiased. The
efficiency ratios of 5-10x match the textbook figures.

## 3. QQQ empirical

- Overnight (close->open) share of daily close-to-close variance, proxy rows:
  **29.7%**. So P/GK/RS run at 0.82-0.86 of cc30 on QQQ (GK10 18.4% vs
  cc30 22.1%); YZ/GKJ run at 0.99-1.02.
- Forecast quality against forward-20d cc vol (RMSE of log ratio / corr):

| series | mean | /cc30 | RMSE fwd20 | corr fwd20 |
|---|---|---|---|---|
| live max(cc10,cc30) | 24.14% | -- | 0.404 | 0.715 |
| cc30 | 22.13% | 1.000 | 0.389 | 0.710 |
| cc10 | 21.51% | 0.972 | 0.431 | 0.697 |
| GK10 | 18.43% | 0.833 | 0.403 | 0.753 |
| YZ10 | 22.12% | 1.000 | 0.371 | 0.743 |
| GKJ10 | 21.98% | 0.993 | **0.365** | 0.748 |
| bcGK10 | 21.59% | 0.976 | 0.363 | 0.752 |

The range estimators ARE better forecasters overall (RMSE 0.36-0.37 vs
0.39-0.40, corr 0.75 vs 0.71). This is the part of the hypothesis that is
true. Section 7 shows why it does not reach the P&L.

## 4. Family and results (41 candidates + live; same rows: 6575 proxy, 564 real weekly)

Family: singles cc10/20/30, {P,GK,RS,YZ} x {5,10,20,30}, GKJ10/30, bcGK10;
max(fast range 5/10, cc30) for P/GK/RS/YZ/GKJ; max(range5|10, range30) for
P/GK/RS/YZ; max(bcGK10, cc30). Live = max(cc10, cc30), T = 0.20.

Live reproduced exactly: 26y proxy 22.12% / 0.938 / -32.8%, S 1.150,
H 0.780, exposure 66.21%, 68 rebalances/yr; real weekly 30.67% / 1.260 /
-25.3%.

### 4a. Fixed T = 0.20 (naive swap) -- the trap
Every pure range estimator holds MORE capital (P/GK/RS 70-71% vs 66.2%) and
still scores WORSE on full Sharpe (0.88-0.93 vs 0.938) with deeper drawdowns
(-36% to -41% vs -32.8%). `exposure_control` at each variant's exposure
confirms the direction: all beat the scaled-down live control, i.e. the
naive swap is a leverage dial, not an estimator improvement. YZ/GKJ (gap-
aware) hold roughly live's exposure and score 0.89-0.93. No variant beats
live on both eras at fixed T except none -- 0/41.

### 4b. Exposure-matched (T re-calibrated by bisection to 66.21%) -- THE comparison

| variant | T* | CAGR | Sharpe | MDD | S | H | reb/yr | real weekly CAGR/Sh/MDD | real expo |
|---|---|---|---|---|---|---|---|---|---|
| **LIVE max(cc10,cc30)** | 0.200 | 22.12% | 0.938 | -32.8% | 1.150 | 0.780 | 68 | 30.67 / 1.260 / -25.3 | 70.1% |
| cc30 (old live) | 0.184 | 21.69% | 0.917 | -33.8% | 1.104 | 0.775 | 58 | 30.48 / 1.249 / -23.4 | 70.3% |
| GK10 | 0.147 | 21.48% | 0.926 | -33.2% | 1.123 | 0.773 | 77 | 30.41 / 1.226 / -28.5 | 72.2% |
| YZ10 | 0.179 | 21.07% | 0.910 | -33.5% | 1.117 | 0.753 | 77 | 29.52 / 1.206 / -27.7 | 71.0% |
| GKJ10 | 0.178 | 21.20% | 0.915 | -33.6% | 1.125 | 0.756 | 76 | 29.75 / 1.215 / -27.7 | 70.9% |
| bcGK10 | 0.174 | 21.25% | 0.921 | -31.7% | 1.120 | 0.773 | 77 | 28.87 / 1.215 / -27.0 | 70.0% |
| max(GK10,cc30) | 0.189 | 21.67% | 0.920 | -33.3% | 1.102 | 0.780 | 59 | 30.37 / 1.243 / -24.2 | 70.6% |
| max(YZ5,cc30) | 0.202 | 21.46% | 0.922 | -32.1% | 1.154 | 0.748 | 71 | 29.78 / 1.234 / -26.6 | 70.2% |
| max(GKJ5,cc30) | 0.201 | 21.69% | 0.930 | -32.2% | 1.160 | 0.758 | 69 | 29.84 / 1.236 / -26.9 | 70.2% |
| max(GKJ10,cc30) | 0.198 | 21.50% | 0.919 | -33.2% | 1.120 | 0.768 | 64 | 30.37 / 1.250 / -24.9 | 70.2% |
| max(bcGK10,cc30) | 0.197 | 21.71% | 0.928 | -33.0% | 1.127 | 0.780 | 64 | 30.12 / 1.252 / -24.7 | 70.0% |
| max(P10,P30) | 0.164 | 21.72% | 0.929 | -33.0% | 1.132 | 0.770 | 64 | 31.48 / 1.265 / -25.7 | 71.7% |
| max(GK10,GK30) | 0.163 | 21.83% | 0.933 | -33.2% | 1.121 | 0.786 | 63 | 31.35 / 1.255 / -26.4 | 71.9% |
| **max(GK5,GK30)** (best) | 0.166 | 21.83% | 0.940 | -32.9% | 1.134 | 0.790 | 68 | 30.55 / 1.238 / -28.0 | 71.9% |
| max(RS5,RS30) | 0.168 | 21.77% | 0.937 | -33.4% | 1.129 | 0.787 | 68 | 30.45 / 1.226 / -28.3 | 72.2% |
| max(RS10,RS30) | 0.165 | 21.86% | 0.933 | -33.2% | 1.112 | 0.793 | 62 | 31.30 / 1.248 / -27.0 | 72.2% |

(Full 41-row tables are in the script output.) Range of full Sharpe across
all 41: 0.894 .. 0.940 against live 0.938. Only max(GK5,GK30) ties live on
full Sharpe (+0.002) and it does so by winning the holdout (+0.010) while
losing the search era (-0.016): **BOTH-era survivors: 0 / 41.** Real-weekly
survivors: 1 / 41 (max(P10,P30), 1.265 vs 1.260, while holding 71.7% vs
70.1% on the real rows -- inside noise and not exposure-matched there).

Note the real-rows exposure column: T* was calibrated on the proxy; on the
real rows every range variant holds 0.5-2pp MORE than live and still has a
lower Sharpe, so the real-instrument comparison is tilted in their favour and
they lose anyway. Rebalances/yr: 55-93 vs live 68; 5-day range legs churn at
90+/yr as single estimators, ~68-71 when maxed with a 30d leg.

## 5. Controls on the top 3 (max(GK5,GK30), max(RS5,RS30), max(RS10,RS30))

Block bootstrap vs live, exposure-matched, 2000 resamples, 6575 sessions:

| candidate | point | block 20d Sharpe CI (P<=0) | block 60d Sharpe CI (P<=0) |
|---|---|---|---|
| max(GK5,GK30) | -0.24pp/yr, +0.002 Sh | [-0.043, +0.049] (0.483) | [-0.049, +0.048] (0.462) |
| max(RS5,RS30) | -0.28pp/yr, -0.001 Sh | [-0.055, +0.053] (0.522) | [-0.058, +0.052] (0.534) |
| max(RS10,RS30) | -0.22pp/yr, -0.005 Sh | [-0.057, +0.045] (0.597) | [-0.068, +0.048] (0.533) |

P(<=0) ~ 0.5 in every case: a coin flip. Leave-one-regime-out Sharpe
differences all sit in -0.011 .. +0.012 (dot-com out: -0.005/-0.009/-0.011;
GFC out: +0.007/+0.006/+0.012; COVID out: +0.003/-0.001/+0.001; 2022 out:
+0.010/+0.009/+0.002; SPMO era out: +0.010/+0.007/+0.012). No regime carries
or kills anything because there is nothing to carry.

Placebo (fast leg = cc30 x block-permuted fast/cc30 ratio, 60d blocks, 5
seeds, T re-calibrated): max(GK5,GK30) 0.940 real vs 0.891 placebo
(0.876..0.925). The range information is genuine -- destroying its timing
costs ~0.05 Sharpe. But the level-only control (live's own cc10 leg shifted
to the range estimator's level, x0.845, T re-calibrated) scores 0.930 with
S 1.135 / H 0.771: close-to-close carries the same information. The range
estimator is real information that is not INCREMENTAL to live.

Real DAILY harness (vol_estimator_daily.py loop with the estimator injected,
SPMO/TQQQ/QLD/XLU/BOXX, 3% drift band, needs_rebalance, 2720 sessions
2015-11-02..2026-08-27), candidates at their proxy T*:

| variant | T | CAGR | Sharpe | MDD | reb/yr | turnover | Sharpe @10bp | @20bp |
|---|---|---|---|---|---|---|---|---|
| LIVE | 0.200 | 29.69% | 1.202 | -29.5% | 69 | 17.1x | 1.116 | 0.972 |
| max(GK5,GK30) | 0.166 | 29.49% | 1.185 | -30.9% | 70 | 17.8x | 1.097 | 0.949 |
| max(RS5,RS30) | 0.168 | 29.50% | 1.181 | -31.2% | 69 | 18.0x | 1.092 | 0.944 |
| max(RS10,RS30) | 0.165 | 29.45% | 1.162 | -31.7% | 64 | 17.4x | 1.078 | 0.937 |

All three lose on the real daily book (-0.017 to -0.040 Sharpe, bootstrap
P(Sharpe diff <= 0) 0.70-0.87), with a worse drawdown and slightly more
turnover. By year the divergences are 2018 (-6/-9 vs -3), 2022 (-21/-22 vs
-19) and 2024 (+57..+61 vs +64): the lowered T* bites in mild-vol years.

## 6. Why a better forecaster does not help (the finding worth keeping)

Forecast quality split by whether the overlay bites (forward-20d cc vol >
0.20, n = 2690 of 6555 rows) or not:

| series | RMSE bite | corr bite | RMSE calm | corr calm |
|---|---|---|---|---|
| live max(cc10,cc30) | **0.394** | 0.603 | 0.410 | 0.285 |
| cc30 | 0.408 | 0.591 | 0.376 | 0.285 |
| GK10 | 0.477 | 0.626 | **0.342** | 0.377 |
| YZ10 | 0.401 | 0.617 | 0.348 | 0.363 |
| GKJ10 | 0.397 | 0.623 | 0.341 | 0.368 |
| max(GK5,GK30) | 0.421 | 0.627 | 0.329 | 0.359 |

1. The 5-10x efficiency gain shows up where vol is LOW (calm RMSE 0.33-0.35
   vs 0.41). With cap = 1.0 the multiplier is 1.0 whenever vol < T, so
   precision there is worth exactly nothing to the book.
2. Where vol is HIGH, the range estimators are no better (YZ/GKJ 0.40 vs live
   0.39) or worse (GK10 0.48): crash variance on QQQ is 30% overnight gaps,
   which the intraday range never sees, and the gap-aware YZ/GKJ recover it
   only by re-including the same close-to-close information live already
   uses. Live's max(cc10,cc30) is in fact the best forecaster in the bite
   region of everything tested.
3. Exposure matching lowers T* to 0.147-0.166 for the range variants. That
   does not add crash protection -- the multiplier on the 5% worst QQQ days
   is 0.535 (max(GK5,GK30)) vs live's 0.556, and 0.519 vs 0.522 the day after
   -- it removes exposure in mild-vol up-years instead: yearly exposure 2004
   71% vs 78%, 2007 82% vs 90%, 2010 68% vs 70% (2007 P&L +30% vs +43%).
   The capital freed on those years is what pays for the tiny holdout gain.

What would have to be true for this to work: either the overlay would have
to act BELOW T (cap > 1.0, i.e. lever up in calm markets -- rejected in
state.py: cap=1.5 took COVID from -16.2% to -22.3%), or QQQ's overnight
share would have to be much smaller than 30% so that the range carried the
crash variance. Neither is a change this project would make.

## 7. Classification

- NOT a signal: 0/41 both-era, bootstrap P ~ 0.5, real weekly and real daily
  both lose, LORO flat.
- NOT a risk-preference dial either: at fixed T the naive swap is a leverage
  dial (holds 4-5pp more, worse MDD), and once matched there is nothing left.
- The estimators themselves are validated and `data/qqq_ohlc.csv` is clean;
  both are reusable if a future line needs intraday range (e.g. gap vs
  intraday decomposition as a feature, which is a different, TIMING-shaped
  question and not the one tested here).

Candidate count: 41. Survivors: 0.
