# Line `vrp_signal` — the variance risk premium as a time-varying signal (2026-09-08)

**Verdict: SIGNAL TOO SMALL.** Real, consistent, in the right direction under every
control, and worth about +0.01 to +0.03 Sharpe. Not a candidate. Nothing applied.

Script: `paper-track/vrp_signal.py`. Full output: `vrp_signal_run.log` (the research
agent completed three full runs and was cut off by a session limit before writing
this note; the note is written from run 3, which is the script's final form).

## Setup
- vrp_t = implied − realized, both annualised fractions, causal: q30/q21/q10 = VXN −
  rv(QQQ, 30/21/10); s30 = VIX − rv(SPY, 30) for the S&P core leg. FRED holidays
  forward-filled.
- Thresholds: trailing 252-session quantiles (causal) and an expanding-window variant.
  Never fitted on an era.
- Same-rows: VXN starts 2001-02 and the trailing window needs 252 sessions, so every
  variant INCLUDING live is scored on 6,176 proxy rows 2002-02-07..2026-08-26
  (holdout 3,457 / search 2,719) and all 564 real weekly rows. Live on those rows:
  SPY-core 22.76 / 0.986 / −32.0, S 1.151 H 0.852, expo 69.28%; QQQ-core S 1.150
  H 0.887; real 30.67 / 1.260 / −25.3 (standing figure reproduced).
- 63 variants: 28 tilts + 35 modulators (incl. 3 smoothed), each with sign-flip,
  QQQ-core and real-row runs, plus 18 decomposition controls.

## (c) Does the effect exist in this data?
Distribution (q30): mean +3.25 vol pts, sd 5.66, negative 20% of days; holdout mean
+3.69, search +2.66. Autocorrelation lag1 0.943, lag5 0.766, lag21 0.153 — a slow
signal. Alignment sanity: corr(QQQ d0→d1, VXN change d0→d1) = −0.652.

Predictive correlation with next-day QQQ return: +0.027 (t 2.2) at h=1, gone by
h=21 (+0.026, t 0.45). Causal trailing-252 quintiles, QQQ forward returns:

| quintile | n | fwd 5d | fwd 21d | 21d Sharpe |
|---|---|---|---|---|
| Q1 (low VRP) | 1394 | +0.14% | +0.70% | 0.39 |
| Q5 (high VRP) | 1281 | +0.62% | +1.98% | 1.17 |
| Q5−Q1 | | +0.48% (t 1.8) | +1.28% (t 1.2) | |

Holdout-only Q5−Q1 21d +1.77% (t 1.15); search-only +0.61% (t 0.40). The literature's
sign is there — high premium → better forward returns — but the middle quintiles are
not monotone and the t-stats do not clear 2 once overlap is respected.

## (a) Tilt core↔TQQQ on VRP, constant capital
Best: q21 d=0.10 median — Sharpe 1.001 vs live 0.986, S 1.158 / H 0.872 (BOTH),
beats beta-matched live and constant-tilt (+0.015), flip loses, real 1.284 vs 1.260.
Bootstrap vs live: Sharpe 95% [−0.022, +0.053], P(≤0) = 0.21–0.22; vs const-tilt
P = 0.22–0.23. LORO all positive (+0.007..+0.020). Only 2 of 28 tilts are both-era;
the 30-day and S&P-side versions mostly fail search.

## (b) Modulator of the vol target, T re-calibrated to live's 69.28% exposure
m = min(1, T / (vol_live · g(vrp))), g = exp(−k·vrp) (also piecewise, power).
17 of 35 both-era; every one's sign-flip loses; MDD flat to slightly better.

| variant | T* | Sharpe | S / H | vs live | real |
|---|---|---|---|---|---|
| live | 0.200 | 0.986 | 1.151 / 0.852 | — | 1.260 |
| q10 exp k=4 (best) | 0.190 | 1.014 | 1.213 / 0.857 | +0.028 | 1.276 |
| q21 exp k=4 | 0.193 | 1.002 | 1.168 / 0.869 | +0.016 | 1.269 |
| q21 exp k=2 | 0.195 | 0.999 | 1.170 / 0.861 | +0.013 | 1.271 |
| q30 exp k=2 | 0.195 | 0.995 | 1.160 / 0.862 | +0.009 | 1.274 |

Bootstrap vs live (20d / 60d blocks): q21 exp k=2 log-return [+0.08, +1.12]pp
P(≤0) = 0.012 / 0.009, Sharpe [−0.007, +0.034] P = 0.100 / 0.107; q30 exp k=2
log-return P = 0.018 / 0.015, Sharpe P = 0.19 / 0.18; q30 exp k=4 Sharpe P = 0.34.
The RETURN gain (+0.5..+0.9pp/yr) clears 5% for several; the SHARPE gain never does.

## (d) Decomposition — is it the premium, or just convex realized vol?
g = exp(−k·IV)·exp(+k·rv). Controls at matched exposure: IV-level only gives
−0.001..−0.042 Sharpe; rv-only gives −0.021..+0.003. The full VRP gives +0.009..+0.028.
So neither half reproduces it: the gain needs implied AND realized together — it is
the premium, not a steeper vol response. VRP vs rv-only bootstrap: q21 k=4 Sharpe
[−0.024, +0.067] P = 0.17–0.18; log-return P = 0.08.

Robustness: LORO positive in every drop for every survivor (+0.010..+0.032 Sharpe);
holds at 10bp cost (0.912 vs live 0.901) and vanishes at 20bp (0.762 vs 0.760);
one-session signal lag keeps q10 k=2 (+0.013) and kills q21 k=4 (−0.004);
5-session smoothing keeps it (q21 k=4 sm5: +0.017, real 1.278) and reduces churn
36.5× → 34.6× vs live 33.2×. Where the exposure moves: −6.5pp in state A when
VRP < 0 (437 days), +1.0pp when VRP ≥ 0; −13pp in C when VRP < 0. Year-by-year
q21 k=4: 18 up / 7 down, biggest +6.2pp (2020), worst −1.9pp (2016, 2025).

## Why it is not a candidate
- Best-of-63 selection; 17 both-era modulators are one family with one knob.
- Sharpe 95% CIs straddle zero for every variant against live, against the
  constant tilt, and against the rv-only control.
- The economic size is +0.5..+0.9pp/yr and +0.01..+0.03 Sharpe — inside the
  execution-lag cost the project already measured (3.1pp/yr per session).
- Predictive t-stats on the underlying effect are 1–2, not 2+.

## What would have to be true
A VRP effect of the literature's size would show Q5−Q1 21d spreads of 3–5% with
t > 3. This data shows 1.3% at t 1.2. The mechanism is present at a fraction of
the textbook magnitude on QQQ over 2002–2026, and the vol target already captures
most of the realized half of it.
