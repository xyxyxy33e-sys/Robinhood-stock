# Research line `qqew_vol_supplement` (2026-09-11): equal-weight Nasdaq vol / dispersion as a SECOND INPUT to the live vol-target estimator

Research only. Nothing here is applied; the discipline in BRIEFING.md (ADDENDUM 2026-09-10) binds. No commit, no trade, no
artifact, no existing data file edited. Script: `paper-track/qqew_vol_supplement.py` (run from the repo root, ~145 s at 2000
bootstrap draws; `QVS_NB=<draws>`, `QVS_STAGE=boot|rest` to split). Full log: `paper-track/research_notes/qqew_vol_supplement_run.log`.

Owner's brief: *"not as a replacement, think as a supplement."* The live vol target scales the four risky legs by
min(1, 20% / 30-day realized QQQ vol). Volatility has worked as a SCALING input everywhere and failed as a TIMING input
everywhere. Does the equal-weight Nasdaq-100's realized volatility, or the DISPERSION between equal-weight and cap-weight
vol, add anything as a second input to the estimator, with the target (20%), cap (1.0) and lookback (30d) unchanged?

## 0. Summary

- **Answer: no.** Nine estimator variants (one of them the v_e-only replacement, reference only) were fed into the live
  design as the ONLY change. None earns a place under the standing bar (both eras + real rows + exposure-matched control +
  block bootstrap, and not COVID-only). The equal-weight vol is a 0.975-correlated echo of the QQQ vol with a slightly
  lower mean (19.32% vs 19.84%); it carries no information the live input lacks, and the dispersion component v_r is a
  monotone de-lever dial with a heavy recovery cost. The clean statement is "no signal": every variant either loses to live
  on both eras with a bootstrap CI excluding zero, or "wins" by holding less risk and loses to the exposure-matched control,
  or reproduces the COVID-only / +10 rebalances/yr signature of the estimator the owner reverted on 09-09.
- **The one both-era + exposure-control pass, (6) max(10d QQEW, 30d QQQ), is the reverted max(10,30) wearing a QQEW hat.**
  Full Sharpe +0.019 (1.025 vs 1.006), S +0.028, H +0.006; real rows +0.005 (1.253 vs 1.248); bootstrap Sharpe CI
  [−0.022, +0.061] / [−0.022, +0.065] with P(≤0) 0.21 and log-return −0.22 pp/yr; COVID 2020 alone +0.357, with COVID
  dropped +0.004; +10.2 rebalances/yr (58.6 vs 48.4); recovery-window cost −2.71 pp/yr, CI [−4.4, −1.2], P 1.000. Its
  multiplier is within 0.05 of the reverted QQQ max(10,30)'s on 85.9% of days and the two daily return series correlate
  0.998. Same signature, slightly weaker (the QQQ version on the same rows: +0.039 Sharpe, COVID +0.436, 59.4 reb/yr).
- **v_q + k·v_r (4) is a leverage dial, not a signal.** k = 0.5 scrapes a both-era pass vs live (+0.004 / +0.003) with
  3.2 pp less exposure, and fails vs the exposure-matched control (−0.002 / +0.003); k = 1 has H −0.003. Both variants and
  both sign-flipped placebos (v_q − k·v_r) sit on a straight line in k: CAGR 27.02 / 26.76 / 26.09 / 24.79 / 23.23 as k goes
  +1 → −1, exposure 76.1 / 74.4 / 72.1 / 68.9 / 64.8%, Sharpe flat (0.980 / 0.995 / 1.006 / 1.009 / 1.013). Recovery cost
  −4.7 and −9.4 pp/yr (P 1.000): v_r stays elevated for months after a trough (the longest run of a >0.05 lower
  multiplier is 548 sessions, 2007-07 to 2009-09). The real rows "improve" (1.256 / 1.280) for the same reason the MDD
  improves: less risk.
- **The v_e family (1)–(3) and the spread-percentile boost (5) lose cleanly.** max(v_q, v_e): −0.014 / −0.016, bootstrap
  Sharpe CI [−0.027, −0.002], P(≤0) 0.99, real −0.012. Blends: −0.013 / −0.001 and −0.019 / −0.009, CIs touch zero from
  below. v_e alone (the replacement): −0.036 / −0.018, real −0.032, MDD −35.4 vs −33.6. Spread boost c = 0.5 / 1:
  −0.008 / −0.003 and −0.017 / −0.005 with CIs excluding zero on log-return; and the SIGN-FLIPPED placebo (boost when the
  spread percentile is unusually LOW) does better than the real rule (+0.029 / −0.000, real +0.026), which kills the
  idea that unusually high dispersion is the time to hold less.
- **Descriptive: dispersion is not a leading vol input.** Around the 42 (of 66) worst-1% overnight gaps inside the QQEW
  window, the spread percentile sits BELOW its unconditional 0.50 the whole way in (0.41 at d0−20, 0.39 at d0−1, 0.37 at
  d0) and v_e < v_q on 30 of 42 at d0; the raw levels of v_q, v_e and v_r all rise together into the gap (v_q 22 → 33%,
  v_e 21 → 32%, v_r 7.9 → 9.6% from d0−20 to d0−1) and keep rising after it. The lead/lag correlation of daily CHANGES is
  symmetric (k = −1: +0.139, k = +1: +0.129, contemporaneous +0.911). The equal-weight vol moves WITH the cap-weight vol,
  not before it.
- Candidate count 9 (plus 5 placebos, not counted). Standing figures reproduced first: 26y 22.18 / 0.913 / −33.6, S 1.103,
  H 0.768; real 31.40 / 1.248 / −25.0; same-rows live on the 4,800 QQEW rows 26.09 / 1.006 / −33.6, S 1.103, H 0.876,
  48.4 rebalances/yr, L1 turnover 33.0×/yr.

## 1. Method

- Harness: `leverage_under_trim.py` bootstrap, then sections 0–3 of `breadth_dgate_2000.py` exec'd verbatim (the block
  `qqew_dma_overlay.py` reuses), so the reference rows are the same 4,800 rows 2007-07-27..2026-08-26 (`sub_rows('qqew_60')`)
  and `live_w`/`LIVE`/`LIVE_R`, `exposure_control_live` (bisection of k·LIVE over the true live function), `trailing_pct`,
  `both`, `seed` are the standing definitions. `run`/`evaluate` of `improvement_search` for every figure (costs and the 0.05
  drift band inside); a counted copy of `run()` (pattern of `vol_term_structure.py`) adds a rebalance counter and an L1
  turnover accumulator and is asserted bit-identical on every call. Real rows via `RF.eval_real(rr, fn)` with `RF.vt`.
- Series, all from `state.realized_vol` on their own price series, all causal at d0's close, built ONCE on the daily QQEW
  calendar and attached by date (bisect at-or-before; 0 stale prints on the reference rows): v_q = 30d QQQ (asserted equal to
  `r['vol']` on both the daily and the real rows, max diff 0.0); v_e = 30d QQEW (`data/QQEW_daily_ext.csv`, 2006-05-02..
  2026-09-10, 5,122 sessions); v_e10 = 10d QQEW; v_r = 30d realized vol of the QQEW/QQQ ratio series (the dispersion /
  idiosyncratic component); spread = v_e − v_q and ratio = v_e / v_q with trailing-252 percentiles (`trailing_pct`).
- Weight function: `w = W[eff]; extension_scale; vt(w, EST(r))` — the live function with ONLY the estimator argument
  replaced (asserted identical to `LIVE` when EST = v_q). Multiplier = `state.vol_target_multiplier` (min(1, 0.20/v)).
- Controls: both-era Sharpe vs live; exposure-matched live control; real weekly rows; circular paired block bootstrap 20/60d,
  2000 draws (`block_bootstrap.boot`); leave-one-regime-out over `block_bootstrap.REGIMES` (no dot-com rows on this window);
  recovery windows from `recovery_study.py`'s own episode block (exec'd verbatim: trailing-252 running high, primary set
  depth ≤ −15%, recovery half = [trough, window end)), scored as annualised log-return / Sharpe variant minus live inside
  those sessions with a 20/60d bootstrap; the days on which the variant multiplier differs from live's by > 0.05; sign-flip
  placebos of each family; the 66 worst-1% overnight gaps of `overnight_intraday` (open_{d1}/close_{d0} − 1 from
  `data/qqq_ohlc.csv` on the full proxy rows; 42 fall inside the QQEW window).

## 2. Descriptive

| | v_q | v_e | v_r |
|---|---|---|---|
| mean | 19.84% | 19.32% | 6.88% |
| median | 17.12% | 16.33% | |

corr(v_e, v_q) = +0.975 (log-log +0.964); corr(v_r, v_q) = +0.690; corr(spread, v_q) = −0.143. v_e > v_q on 42.2% of days,
v_e > 1.05·v_q on 25.8%, > 1.10·v_q on 14.1%. Spread v_e − v_q: mean −0.52 pp, p5 −4.59, p25 −1.93, p50 −0.40, p75 +0.84,
p95 +3.00; ratio v_e/v_q p5 0.808, p50 0.978, p95 1.174. v_r / v_q mean 0.372. Live multiplier < 1 on 35.9% of days; v_e > 20%
on 35.8%; the two disagree about the 20% line on 157 + 163 days (3.3% and 3.4% of the sample, symmetric).

| regime | n | v_q | v_e | v_r | spread | v_e > v_q | spread pct > 0.8 |
|---|---|---|---|---|---|---|---|
| GFC 2007-07..2009 | 614 | 28.4% | 29.5% | 11.9% | +1.08 pp | 63.7% | 28.0% |
| COVID 2020 | 253 | 30.6% | 28.6% | 8.8% | −2.00 pp | 32.8% | 19.0% |
| 2022 bear | 251 | 31.8% | 29.8% | 6.7% | −1.95 pp | 3.2% | 21.1% |
| SPMO era 2015-11+ | 2719 | 19.8% | 18.5% | 6.6% | −1.37 pp | 26.6% | 23.1% |
| calm 2013-2014 | 504 | 12.8% | 13.0% | 4.5% | +0.15 pp | 62.3% | 11.9% |
| 2018 Q4 | 63 | 27.4% | 22.9% | 7.7% | −4.56 pp | 0.0% | 0.0% |

Reading: the equal-weight index is MORE volatile than QQQ only in the GFC (the one financials/small-cap-led crash in the
window) and in calm markets; in every mega-cap-led stress (COVID, 2022, 2018 Q4) it is LESS volatile, so max(v_q, v_e)
mostly bites in 2009–2012 and a v_e-based estimator would have de-levered LESS into 2018 Q4, 2020 and 2022 than live did.

### The 66 worst-1% overnight gaps (42 inside the window, mean −3.80%) — event-time profile, d0 = the close before the gap

| offset (sessions) | −20 | −10 | −5 | −3 | −1 | 0 | +1 | +3 | +5 | +10 | +20 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| spread pct (uncond. 0.50) | 0.41 | 0.40 | 0.33 | 0.34 | 0.39 | 0.37 | 0.36 | 0.32 | 0.33 | 0.39 | 0.50 |
| ratio pct | 0.43 | 0.46 | 0.42 | 0.43 | 0.48 | 0.47 | 0.47 | 0.45 | 0.47 | 0.51 | 0.57 |
| v_r pct | 0.67 | 0.68 | 0.75 | 0.75 | 0.75 | 0.76 | 0.78 | 0.79 | 0.79 | 0.80 | 0.73 |
| v_q level | 22.3% | 26.5% | 30.1% | 31.6% | 33.2% | 34.4% | 36.1% | 38.7% | 40.9% | 43.3% | 45.3% |
| v_e level | 21.1% | 25.1% | 28.3% | 29.8% | 31.6% | 32.6% | 34.4% | 36.6% | 39.0% | 41.8% | 44.1% |
| v_r level | 7.9% | 8.3% | 9.0% | 9.2% | 9.6% | 9.8% | 10.1% | 10.3% | 10.7% | 11.5% | 12.3% |
| spread level (pp) | −1.23 | −1.41 | −1.83 | −1.87 | −1.68 | −1.80 | −1.72 | −2.07 | −1.86 | −1.53 | −1.21 |

Spread pct > 0.8 (the variant-5 trigger) at d0−1 on 9 of 42, at d0 on 8, at d0+5 on 7 — against an unconditional 20.9%,
i.e. the trigger is LESS likely than usual to be on going into a bad gap. v_e > v_q at d0 on 12 of 42. Dispersion (v_r) is
elevated in level terms into the gaps (percentile 0.67–0.76), but it rises in step with v_q, which the live estimator already
sees; the spread, which is what a "second input" would have to add, is negative and falling into the events. Lead/lag
correlation of daily changes corr(Δv_e[t], Δv_q[t+k]): k = −3..+3 = +0.126, +0.154, +0.139, **+0.911**, +0.129, +0.156,
+0.134 — symmetric; v_e does not lead v_q. Dispersion rises WITH the gap, not before it.

## 3. Variants on the 4,800 QQEW rows (estimator argument only; target 20%, cap 1.0, lookback 30d, band 0.05 unchanged)

Live: 26.09% / 1.006 / −33.6%, S 1.103, H 0.876, exposure 72.1%, 48.4 rebalances/yr, L1 turnover 33.04×/yr; real weekly
31.40% / 1.248 / −25.0%. dS/dH = search/holdout Sharpe minus live; |d|>.05 = days the variant's multiplier differs from
live's by more than 0.05 (lower = variant holds LESS); k-live = exposure-matched control k·LIVE with dS_k/dH_k the variant
minus that control.

| variant | CAGR / Sharpe / MDD | S | H | dS | dH | exp | reb/yr | L1/yr | real CAGR / Sh / MDD | dReal | \|d\|>.05 | lower | higher | k | dS_k | dH_k |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| (1) max(v_q, v_e) | 25.43 / 0.991 / −33.8 | 1.089 | 0.860 | −0.014 | −0.016 | 71.5% | 49.2 | 32.66 | 30.89 / 1.236 / −25.0 | −0.012 | 395 | 395 | 0 | 0.992 | −0.015 | −0.015 |
| (2) 0.75 v_q + 0.25 v_e | 25.94 / 0.998 / −33.9 | 1.089 | 0.875 | −0.013 | −0.001 | 72.3% | 47.8 | 33.02 | 31.40 / 1.240 / −25.5 | −0.008 | 56 | 26 | 30 | 1.002 | −0.013 | −0.001 |
| (2) 0.50 v_q + 0.50 v_e | 25.84 / 0.992 / −34.7 | 1.083 | 0.867 | −0.019 | −0.009 | 72.4% | 47.1 | 33.03 | 31.44 / 1.232 / −26.0 | −0.016 | 409 | 108 | 301 | 1.005 | −0.019 | −0.009 |
| (3) v_e alone [REPLACEMENT] | 25.57 / 0.979 / −35.4 | 1.067 | 0.858 | −0.036 | −0.018 | 72.7% | 46.3 | 33.07 | 31.51 / 1.216 / −27.5 | −0.032 | 1059 | 395 | 664 | 1.009 | −0.035 | −0.018 |
| (4) v_q + 0.5 v_r | 24.79 / 1.009 / −33.9 | 1.106 | 0.879 | +0.004 | +0.003 | 68.9% | 52.7 | 31.45 | 29.73 / 1.256 / −22.3 | +0.008 | 2032 | 2032 | 0 | 0.955 | −0.002 | +0.003 |
| (4) v_q + 1.0 v_r | 23.23 / 1.013 / −33.5 | 1.118 | 0.873 | +0.016 | −0.003 | 64.8% | 58.1 | 29.52 | 28.03 / 1.280 / −20.7 | +0.032 | 2926 | 2926 | 0 | 0.898 | +0.007 | −0.003 |
| (5) v_q(1+0.5·max(0, sp−.8)) | 25.83 / 1.000 / −33.8 | 1.095 | 0.873 | −0.008 | −0.003 | 71.9% | 48.6 | 32.93 | 31.03 / 1.239 / −25.1 | −0.009 | 139 | 139 | 0 | 0.997 | −0.009 | −0.003 |
| (5) v_q(1+1.0·max(0, sp−.8)) | 25.57 / 0.994 / −34.0 | 1.086 | 0.871 | −0.017 | −0.005 | 71.6% | 50.1 | 32.94 | 30.60 / 1.227 / −25.2 | −0.021 | 353 | 353 | 0 | 0.993 | −0.018 | −0.004 |
| (6) max(v_e10, v_q) | 25.81 / 1.025 / −33.1 | 1.131 | 0.882 | +0.028 | +0.006 | 70.6% | 58.6 | 33.30 | 30.84 / 1.253 / −24.3 | +0.005 | 742 | 742 | 0 | 0.980 | +0.025 | +0.007 |
| placebo min(v_q, v_e) | 26.25 / 0.993 / −35.4 | 1.081 | 0.873 | −0.021 | −0.003 | 73.2% | 45.6 | 33.45 | 32.02 / 1.228 / −27.5 | −0.020 | 664 | 0 | 664 | 1.016 | −0.019 | −0.003 |
| placebo v_q − 0.5 v_r | 26.76 / 0.995 / −35.1 | 1.097 | 0.858 | −0.005 | −0.019 | 74.4% | 45.7 | 34.27 | 32.78 / 1.245 / −28.2 | −0.003 | 1463 | 0 | 1463 | 1.032 | −0.002 | −0.019 |
| placebo v_q − 1.0 v_r | 27.02 / 0.980 / −36.7 | 1.085 | 0.840 | −0.018 | −0.036 | 76.1% | 43.2 | 35.19 | 33.48 / 1.235 / −29.5 | −0.013 | 1581 | 0 | 1581 | 1.056 | −0.012 | −0.038 |
| placebo v_q(1+1.0·max(0, .2−sp)) | 26.26 / 1.022 / −33.4 | 1.132 | 0.876 | +0.029 | −0.000 | 71.4% | 51.3 | 33.12 | 31.65 / 1.274 / −23.2 | +0.026 | 456 | 456 | 0 | 0.990 | +0.028 | +0.001 |
| extra v_q(1+1.0·max(0, ratio pct−.8)) | 25.62 / 0.994 / −34.0 | 1.092 | 0.864 | −0.011 | −0.012 | 71.7% | 50.1 | 32.96 | 30.80 / 1.232 / −25.3 | −0.016 | 284 | 284 | 0 | 0.995 | −0.012 | −0.012 |

Candidate count 9 (one a replacement); placebos 5 and the ratio-percentile extra are not counted. Both-era passes vs live:
(4) k = 0.5 and (6). Both-era passes vs the exposure-matched control: (6) only — and the sign-flipped (5) placebo, which
passes the control (+0.028 / +0.001) where the real rule fails.

### Block bootstrap vs live (2000 draws, circular paired 20/60d blocks)

| variant | Δlogret pp/yr | 20d logret CI, P(≤0) | 20d Sharpe CI, P(≤0) | 60d logret CI, P(≤0) | 60d Sharpe CI, P(≤0) |
|---|---|---|---|---|---|
| (1) max(v_q, v_e) | −0.52 | [−0.93, −0.18] 0.999 | [−0.027, −0.002] 0.990 | [−0.97, −0.15] 0.999 | [−0.028, −0.002] 0.988 |
| (2) 0.75/0.25 | −0.12 | [−0.30, +0.07] 0.889 | [−0.015, −0.000] 0.980 | [−0.32, +0.08] 0.888 | [−0.015, −0.000] 0.981 |
| (2) 0.50/0.50 | −0.19 | [−0.55, +0.18] 0.841 | [−0.027, −0.000] 0.980 | [−0.62, +0.17] 0.837 | [−0.028, −0.001] 0.982 |
| (3) v_e alone | −0.41 | [−1.15, +0.28] 0.860 | [−0.053, −0.002] 0.985 | [−1.17, +0.36] 0.845 | [−0.052, −0.000] 0.977 |
| (4) k = 0.5 | −1.03 | [−2.18, +0.12] 0.964 | [−0.031, +0.039] 0.423 | [−2.26, +0.13] 0.958 | [−0.033, +0.040] 0.435 |
| (4) k = 1.0 | −2.29 | [−4.22, −0.15] 0.980 | [−0.051, +0.070] 0.396 | [−4.48, −0.19] 0.982 | [−0.057, +0.073] 0.405 |
| (5) c = 0.5 | −0.21 | [−0.39, −0.05] 0.995 | [−0.012, −0.000] 0.979 | [−0.42, −0.04] 0.993 | [−0.013, +0.000] 0.971 |
| (5) c = 1.0 | −0.41 | [−0.78, −0.10] 0.995 | [−0.024, +0.000] 0.974 | [−0.84, −0.05] 0.989 | [−0.026, +0.001] 0.956 |
| (6) max(v_e10, v_q) | −0.22 | [−1.29, +0.89] 0.674 | [−0.022, +0.061] 0.206 | [−1.25, +0.97] 0.663 | [−0.022, +0.065] 0.211 |
| placebo min(v_q, v_e) | +0.13 | [−0.47, +0.72] 0.336 | [−0.034, +0.009] 0.856 | [−0.50, +0.74] 0.345 | [−0.033, +0.008] 0.891 |
| placebo v_q − 0.5 v_r | +0.53 | [−0.35, +1.40] 0.133 | [−0.038, +0.016] 0.763 | [−0.37, +1.44] 0.134 | [−0.037, +0.017] 0.769 |
| placebo v_q − 1.0 v_r | +0.74 | [−0.91, +2.34] 0.193 | [−0.079, +0.024] 0.848 | [−0.89, +2.63] 0.215 | [−0.076, +0.027] 0.828 |
| placebo v_q(1+max(0, .2−sp)) | +0.14 | [−0.32, +0.70] 0.298 | [−0.003, +0.038] 0.053 | [−0.30, +0.63] 0.276 | [−0.002, +0.037] 0.045 |
| extra ratio-pct boost | −0.37 | [−0.65, −0.12] 1.000 | [−0.021, −0.002] 0.992 | [−0.69, −0.09] 0.999 | [−0.022, −0.001] 0.986 |

### Leave-one-regime-out (Sharpe, variant minus live; regime ALONE / sample with the regime DROPPED)

| variant | GFC alone | GFC dropped | COVID alone | COVID dropped | 2022 alone | 2022 dropped | SPMO era alone | SPMO era dropped |
|---|---|---|---|---|---|---|---|---|
| (1) max(v_q, v_e) | −0.058 | −0.009 | −0.060 | −0.012 | +0.000 | −0.014 | −0.014 | −0.016 |
| (2) 0.75/0.25 | −0.019 | −0.006 | −0.013 | −0.008 | −0.011 | −0.006 | −0.013 | −0.001 |
| (2) 0.50/0.50 | −0.044 | −0.010 | −0.021 | −0.014 | −0.007 | −0.011 | −0.019 | −0.009 |
| (3) v_e alone | −0.074 | −0.021 | −0.067 | −0.026 | −0.021 | −0.021 | −0.036 | −0.018 |
| (4) k = 0.5 | +0.055 | −0.002 | −0.028 | +0.006 | +0.069 | −0.003 | +0.005 | +0.003 |
| (4) k = 1.0 | +0.075 | +0.002 | −0.030 | +0.010 | +0.101 | −0.003 | +0.016 | −0.003 |
| (5) c = 0.5 | −0.011 | −0.005 | −0.054 | −0.003 | −0.004 | −0.007 | −0.008 | −0.003 |
| (5) c = 1.0 | −0.012 | −0.011 | −0.099 | −0.007 | +0.024 | −0.014 | −0.017 | −0.005 |
| (6) max(v_e10, v_q) | −0.038 | +0.026 | **+0.357** | **+0.004** | −0.016 | +0.023 | +0.028 | +0.006 |

(No dot-com rows on the QQEW window; "GFC" here is 2007-07-27..2009-12-31.) Variant (4)'s in-regime gains are the de-lever
paying in the two bear years and costing in COVID's V; variant (6)'s edge is COVID: with 2020 dropped it is +0.004.

### Recovery windows (recovery_study episodes, recovery half = [trough, window end); 8 episodes, 1,080 sessions, 22% of rows)

Episodes: 2007-10 (T 2008-11-20 → 2010-04-23, −54%), 2010-04 (→ 2010-10-13, −16%), 2011-07 (→ 2012-01-19, −16%), 2015-12
(→ 2016-07-29, −16%), 2018-08 (→ 2019-04-17, −23%), 2020-02 (→ 2020-06-05, −29%), 2021-11 (T 2022-12-28 → 2023-12-15, −36%),
2025-02 (→ 2025-06-24, −23%). Annualised log-return and Sharpe inside those sessions, variant minus live; exposure = mean
target exposure inside the windows (live 56.4%).

| variant | Δlogret pp/yr | ΔSharpe | exp | 20d CI, P(≤0) | 60d CI, P(≤0) | per-episode Δ (pp, trough→end) |
|---|---|---|---|---|---|---|
| (1) max(v_q, v_e) | −1.62 | −0.016 | 54.8% | [−3.0, −0.4] 0.998 | [−3.0, −0.5] 0.999 | −4.4 −0.5 +0.2 −1.5 +0.0 −0.9 +0.0 +0.0 |
| (2) 0.75/0.25 | −0.17 | +0.002 | 56.2% | [−0.6, +0.2] 0.794 | [−0.6, +0.2] 0.777 | −1.1 −0.1 +0.2 −0.1 +0.2 −0.2 +0.1 +0.2 |
| (2) 0.50/0.50 | −0.36 | +0.001 | 56.0% | [−1.2, +0.4] 0.821 | [−1.3, +0.4] 0.790 | −2.3 −0.2 +0.3 −0.5 +0.4 −0.3 +0.6 +0.5 |
| (3) v_e alone | −1.04 | −0.016 | 55.5% | [−2.5, +0.3] 0.925 | [−2.7, +0.5] 0.919 | −4.1 −0.5 +0.2 −1.5 +0.8 −1.5 +1.1 +1.0 |
| (4) k = 0.5 | **−4.74** | −0.077 | 52.3% | [−6.7, −2.7] 1.000 | [−6.8, −2.8] 1.000 | −8.3 −1.0 +0.3 −1.6 −0.6 −2.9 −5.3 −1.0 |
| (4) k = 1.0 | **−9.38** | −0.119 | 47.5% | [−13.1, −5.9] 1.000 | [−13.2, −5.9] 1.000 | −14.8 −2.1 −0.1 −3.9 −1.3 −4.6 −11.3 −2.2 |
| (5) c = 0.5 | −0.74 | −0.008 | 55.7% | [−1.3, −0.3] 1.000 | [−1.4, −0.2] 1.000 | −1.0 −0.1 −0.0 −0.6 +0.0 −1.0 −0.3 −0.1 |
| (5) c = 1.0 | −1.54 | −0.019 | 54.8% | [−2.7, −0.6] 0.999 | [−2.7, −0.5] 0.998 | −1.5 −0.1 −0.1 −1.9 +0.0 −1.9 −0.9 −0.1 |
| (6) max(v_e10, v_q) | **−2.71** | −0.071 | 55.0% | [−4.4, −1.2] 1.000 | [−4.4, −1.3] 1.000 | −5.8 −0.5 −0.2 −2.3 −0.1 −1.0 −1.5 −0.3 |
| placebo min(v_q, v_e) | +0.62 | +0.003 | 57.1% | [+0.0, +1.3] 0.018 | [−0.0, +1.3] 0.029 | +0.3 +0.0 +0.0 +0.0 +0.8 −0.5 +1.1 +1.0 |
| placebo v_q − 0.5 v_r | +2.51 | −0.022 | 59.7% | [+0.5, +4.7] 0.007 | [+0.5, +5.2] 0.004 | +3.7 +0.5 −0.6 +0.6 +0.8 +2.4 +2.3 +1.1 |
| placebo v_q − 1.0 v_r | +3.98 | −0.096 | 62.7% | [−0.3, +8.8] 0.035 | [−0.9, +9.8] 0.058 | +8.0 +0.9 −2.3 +0.9 +1.0 +4.5 +2.7 +1.3 |

For reference recovery_study measured the reverted max(10,30) QQQ estimator at −2.1 pp/yr [−3.3, −1.1] on the same
construction over the full proxy. Every variant that de-levers more than live pays in the recoveries, and the amount paid is
proportional to how much longer it holds the multiplier down: the v_r variants, whose input stays high for months after a
trough (v_r 12.3% twenty sessions after the worst gaps and still climbing), pay the most.

### Multiplier-difference days (|variant − live| > 0.05): by year (lower / higher) and the longest runs

| year | (1) max | (2) .75 | (2) .50 | (3) v_e | (4) k.5 | (4) k1 | (5) c.5 | (5) c1 | (6) fast |
|---|---|---|---|---|---|---|---|---|---|
| 2007 | 0/0 | 0/0 | 0/29 | 0/43 | 86/0 | 109/0 | 0/0 | 0/0 | 21/0 |
| 2008 | 18/0 | 0/0 | 1/1 | 18/46 | 247/0 | 253/0 | 18/0 | 42/0 | 77/0 |
| 2009 | 139/0 | 26/0 | 70/0 | 139/0 | 191/0 | 229/0 | 19/0 | 79/0 | 107/0 |
| 2010 | 35/0 | 0/0 | 0/0 | 35/0 | 121/0 | 144/0 | 3/0 | 7/0 | 47/0 |
| 2011 | 69/0 | 0/0 | 6/0 | 69/0 | 93/0 | 160/0 | 30/0 | 51/0 | 62/0 |
| 2012 | 37/0 | 0/0 | 8/0 | 37/0 | 65/0 | 139/0 | 1/0 | 2/0 | 36/0 |
| 2013 | 0/0 | 0/0 | 0/0 | 0/0 | 1/0 | 30/0 | 0/0 | 0/0 | 15/0 |
| 2014 | 0/0 | 0/0 | 0/0 | 0/0 | 23/0 | 53/0 | 3/0 | 14/0 | 25/0 |
| 2015 | 0/0 | 0/0 | 0/1 | 0/32 | 62/0 | 123/0 | 0/0 | 0/0 | 13/0 |
| 2016 | 37/0 | 0/0 | 6/0 | 37/13 | 82/0 | 98/0 | 17/0 | 54/0 | 33/0 |
| 2017 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 1/0 | 0/0 | 0/0 | 0/0 |
| 2018 | 0/0 | 0/0 | 0/67 | 0/117 | 124/0 | 142/0 | 0/0 | 0/0 | 41/0 |
| 2019 | 0/0 | 0/0 | 0/2 | 0/38 | 71/0 | 116/0 | 0/0 | 0/0 | 30/0 |
| 2020 | 26/0 | 0/6 | 15/87 | 26/95 | 166/0 | 181/0 | 31/0 | 39/0 | 54/0 |
| 2021 | 0/0 | 0/0 | 0/3 | 0/11 | 87/0 | 145/0 | 0/0 | 0/0 | 41/0 |
| 2022 | 0/0 | 0/0 | 0/10 | 0/101 | 173/0 | 251/0 | 15/0 | 35/0 | 56/0 |
| 2023 | 0/0 | 0/0 | 0/1 | 0/53 | 121/0 | 236/0 | 2/0 | 27/0 | 11/0 |
| 2024 | 0/0 | 0/6 | 0/39 | 0/39 | 83/0 | 178/0 | 0/0 | 0/0 | 9/0 |
| 2025 | 0/0 | 0/5 | 0/30 | 0/38 | 113/0 | 185/0 | 0/0 | 1/0 | 24/0 |
| 2026 | 34/0 | 0/13 | 2/31 | 34/38 | 123/0 | 153/0 | 0/0 | 2/0 | 40/0 |

Longest runs (start..end, sessions, mean difference): (1) 2011-09-23..2012-01-12 (77d, −0.07), 2009-04-21..2009-08-03
(73d, −0.14); (3) v_e alone 2018-10-16..2019-02-14 (83d, +0.11), 2020-09-03..2020-12-15 (72d, +0.16) — the replacement
would have held MORE than live through 2018 Q4 and the 2020 autumn; (4) k = 0.5 2007-10-31..2008-10-14 (241d, −0.12),
2008-10-29..2009-08-27 (209d, −0.12), 2020-05-11..2020-12-16 (154d, −0.12), 2026-03-26..2026-08-26 (106d, −0.16); (4) k = 1
2007-07-27..2009-09-28 (548d, −0.20), 2021-11-30..2023-08-31 (441d, −0.14); (5) c = 1 2011-09-21..2011-11-14 (39d, −0.10),
2020-05-12..2020-07-02 (37d, −0.12); (6) 122 short runs, mean |diff| 0.137, longest 2008-09-15..2008-10-24 (30d, −0.10),
2020-02-24..2020-03-27 (25d, −0.11), 2019-08-05..2019-08-27 (17d, −0.21). Where the v_e-side variants bite (2009, 2011–12,
2016) is where the equal-weight index was the more volatile one: post-GFC and the 2011/2016 small-cap-led drawdowns — none
of which the live estimator handled badly.

### Signature check: variant (6) against the reverted max(10d, 30d) QQQ estimator on the same rows

| | CAGR / Sharpe / MDD | S | H | exp | reb/yr | L1/yr | GFC | COVID | 2022 | SPMO era |
|---|---|---|---|---|---|---|---|---|---|---|
| live | 26.09 / 1.006 / −33.6 | 1.103 | 0.876 | 72.1% | 48.4 | 33.04 | | | | |
| reverted max(10,30) QQQ | 26.21 / 1.045 / −33.0 | 1.152 | 0.904 | 70.3% | 59.4 | 33.43 | +0.053 | +0.436 | −0.036 | +0.050 |
| (6) max(10d QQEW, 30d QQQ) | 25.81 / 1.025 / −33.1 | 1.131 | 0.882 | 70.6% | 58.6 | 33.30 | −0.038 | +0.357 | −0.016 | +0.028 |

Multipliers within 0.05 of each other on 85.9% of days; daily return correlation 0.998. Variant (6) IS the reverted estimator
with a noisier fast leg: the same +10 rebalances/yr, the same COVID-only edge (+0.357 alone, +0.004 dropped), the same
recovery cost (−2.7 vs −2.1 pp/yr), and a smaller total. Nothing about the equal-weight input changes the trade the owner
already resolved on 09-09.

## 4. Verdict

No variant earns a place. The equal-weight vol is a 0.975-correlated copy of the QQQ vol: as a max, blend or replacement
it loses to live on both eras and on the real rows with bootstrap CIs at or below zero (max: Sharpe CI [−0.027, −0.002],
P(≤0) 0.99; the blends' CIs touch zero from below; v_e alone −0.036 / −0.018 and real −0.032), because it is LOWER than
QQQ vol in every mega-cap-led stress (2018 Q4, 2020, 2022) and higher only post-GFC and in calm tape. The dispersion
component v_r is a leverage dial: CAGR and exposure move monotonically in k in both directions (27.0 → 23.2% CAGR, 76 → 65%
exposure from k = −1 to +1) with Sharpe flat inside ±0.02, the k = 0.5 both-era "pass" (+0.004 / +0.003) fails the
exposure-matched control (−0.002 / +0.003), and the recovery cost is −4.7 and −9.4 pp/yr with P 1.000 because v_r stays
elevated for months after a trough. The spread-percentile boost is beaten by its own sign-flipped placebo (+0.029 vs −0.017
on search), so high dispersion is not the time to hold less; and dispersion does not lead the worst gaps (spread percentile
0.41 → 0.37 into the 42 events, v_r rising in lockstep with v_q). The only both-era + exposure-control pass, max(10d QQEW,
30d QQQ), is the reverted max(10,30) with a QQEW fast leg (85.9% same multiplier, 0.998 return correlation): +0.019 Sharpe
with CI [−0.022, +0.065], real +0.005, COVID-only (+0.357 alone, +0.004 dropped), +10.2 rebalances/yr and −2.7 pp/yr in
recoveries — the same trade the owner already declined. Distinguishing the three: v_e-family = no signal (worse, reliably);
v_r-family = risk-preference dial, not a signal; fast-QQEW = the known max(10,30) trade in different clothing. Nine
candidates, one COVID-only pass, zero survivors. The single-index 30d QQQ estimator stands.
