# Research line 4 (2026-09-08): the volatility term structure as a regime signal

**Verdict: signal-too-small.** The S&P implied-vol slope (VIX/VXV) is a real but marginal
*forward-volatility* forecast, not a forward-return signal. Used as a cash gate it has no
mechanism and does nothing; used as a rebalance trigger it does nothing; used as a modulator
inside the vol target it is directionally right in every control (both eras, sign-flip loses,
leave-one-regime-out all positive, real SPMO rows agree) but worth **+0.011 to +0.017 Sharpe
at matched exposure, block-bootstrap P(<=0) = 0.21 to 0.36, 95% CI straddling zero**. Nothing
here is a candidate. Research only; change freeze until 2026-12-07; nothing applied.

Script: `paper-track/vol_term_structure.py` (runs in ~2 min from the repo root).
New data: `data/vxvcls.csv`.

## Data and provenance

| series | source | span | status |
|---|---|---|---|
| VXVCLS, CBOE S&P 500 3-Month Volatility Index | FRED `https://fred.stlouisfed.org/graph/fredgraph.csv?id=VXVCLS`, fetched 2026-09-08 via the briefing's curl pattern | 2007-12-04 .. 2026-09-04, 4,894 rows, 176 holiday rows carry an empty value (forward-filled, never dropped) | **saved as `data/vxvcls.csv`** (raw FRED file, untouched) |
| VIXCLS | already at `data/vixcls_full.csv` | 1990-01-02 .. 2026-09-07 | used as the front month |
| VXSTCLS / VIX9D / VIX9DCLS / VXST (9-day short end) | FRED | -- | **not on FRED**: every ID returns FRED's HTML error page; FRED search for "VIX9D" returns no series. No short-end slope is obtainable from FRED. |
| VXMTCLS / VIX6M / VIX6MCLS (6-month long end) | FRED | -- | not on FRED |
| VXN3M / VXN3MCLS / any Nasdaq-100 3-month index | FRED | -- | **not on FRED**: FRED search for "Nasdaq 3-Month Volatility" returns only NASDAQ price indices. No Nasdaq term structure is obtainable. |
| VVIXCLS | FRED | -- | not on FRED (probed incidentally) |

So the only obtainable term structure is the S&P one, and this design runs on a QQQ book.
The VIX-vs-VXN work today found the S&P index was the wrong instrument for LEVEL signals
(negative variance risk premium against QQQ realized vol). A ratio divides the level out, so
that failure does not transfer automatically; it was treated as a live risk and tested
directly (Part 0 and Part E below): the S&P slope forecasts QQQ forward vol about as well as
it forecasts SPY forward vol, so the instrument mismatch did not bite for this signal.

Alignment sanity: contemporaneous d0->d1 corr(SPY return, VIX change) = -0.704,
corr(QQQ return, VIX change) = -0.609. Pairing is correct; QQQ is lower because VIX is an
S&P index.

Window discipline: every variant INCLUDING the live baseline is evaluated on the same
4,710 VXV-covered rows, 2007-12-04 .. 2026-08-26 (18.7 yr). The holdout inside this window
is 2007-12-04 .. 2015-10-31 (1,991 rows) and the search era 2015-11-01+ (2,719 rows).
**The dot-com bust is outside the window** and cannot be tested or left out. Figures are
not comparable to 26-year numbers.

Standing figures reproduced first: 26y proxy 22.12% / 0.938 / -32.8%, search 1.150,
holdout 0.780; real weekly 30.67% / 1.260 / -25.3%. All exact.

## The slope: distribution, frequency, persistence

`ratio = VIX/VXV`, `diff = VIX - VXV`, backwardation = ratio > 1 (structural line, not fitted).

| statistic | value |
|---|---|
| ratio mean / median | 0.904 / 0.892 |
| ratio p5 / p25 / p75 / p95 / max | 0.796 / 0.848 / 0.947 / 1.037 / 1.431 |
| diff mean / median / p95 / max | -1.71 / -2.03 / +1.14 / +23.83 vol points |
| days in backwardation | 477 of 4,710 = **10.1%** (holdout 13.8%, search 7.4%) |
| episodes | 131 (7.0 entries/yr) |
| backwardation run length | **median 1 day**, mean 3.6d, max 63d; 50% of runs last one day |
| P(bw tomorrow given bw today) | 0.725 |
| contango run length | median 6d, mean 32.1d |
| overlap with realized 10d/60d > 1 | P(realized bw given implied bw) = 0.73; P(implied bw given realized bw) = 0.18 |
| overlap with high realized vol (vol_live above expanding median) | P(hivol given bw) = 0.80 |

Two facts that decide the outcome: backwardation is rare (10%) and mostly fleeting (half
the episodes are single days), and 80% of it sits inside the high-realized-vol half that
the live vol target already responds to.

## Part 0: mechanism check, forward returns (predictive pairing, signal at d0)

Mean forward return from d0; t uses non-overlapping subsamples of each horizon.

| conditioning | 1d | 5d | 21d |
|---|---|---|---|
| QQQ, implied backwardation (n=477) vs rest | +0.09% vs +0.06% | +0.59% vs +0.29% | **+2.32% vs +1.24%** (t=+0.5) |
| SPY, implied backwardation | +0.05% vs +0.04% | +0.41% vs +0.18% | +1.40% vs +0.80% (t=+0.3) |
| QQQ, realized 10/60 > 1 (n=1,920) | +0.07% vs +0.06% | +0.29% vs +0.34% | +1.15% vs +1.49% (t=-0.4) |
| QQQ, high vol (n=1,931) | +0.09% vs +0.05% | +0.45% vs +0.23% | +1.77% vs +1.07% (t=+0.8) |

Backwardation is NOT followed by lower returns. Forward QQQ returns after backwardation are
higher, not lower, on every horizon (inside noise). That is the textbook result: backwardation
is stress that has already happened, and the price has already moved. **There is no
forward-return mechanism for a de-risking cash gate.**

2x2 against the causal vol state (21d QQQ forward return, hit rate, and forward 21d realized vol):

| cell | n | 21d ret | hit | fwd 21d vol |
|---|---|---|---|---|
| low vol, contango | 2,683 | +1.07% | 67% | 16% |
| low vol, backwardation | 96 | +1.02% | 61% | 24% |
| high vol, contango | 1,550 | +1.55% | 66% | 21% |
| high vol, backwardation | 381 | +2.64% | 66% | 33% |

What the slope does forecast is forward VOLATILITY: inside the high-vol half, backwardation
days are followed by 33% realized vol vs 21% for contango, with no return penalty. That is
exactly the shape that helps a vol target (same return, less variance when scaled down) and
does not help a cash gate.

Implied vs realized slope (21d QQQ): implied-bw with realized calm (n=127) +3.17%, hit 72%;
realized-bw with implied calm (n=1,570) +0.96%, hit 64%. The two partitions are not the same
thing.

By effective state: A 2.0% of days in backwardation, C 14%, D 16%, E 38%, F 44%. The slope
almost never fires in state A, where the leveraged book is held; it fires in the defensive
states, where there is little to de-risk.

## Baseline on the VXV window

LIVE on 4,710 rows: **25.29% / 1.024 / -32.8%, search 1.150, holdout 0.848, exposure 70.15%,
68.2 rebalances/yr.**

Controls used for every variant below: (i) the CURRENT live design scaled by k (bisection)
to the variant's average deployed exposure ("matched"); (ii) `exposure_control()` as
mandated (note it scales `live_base(micro=False)` with vol30, i.e. the pre-overlay, pre-trim
baseline, which is why it prints ~0.856 rather than 1.024; it is reported, not relied on);
(iii) sign-flip (the same rule applied in contango instead); (iv) both-era. Bisections on
rule constants re-calibrate to live's 70.15% exposure exactly.

## Part A: cash gate (scale the four risky legs by g in backwardation)

| variant | CAGR / Sharpe / MDD | S / H | expo | matched live Sharpe | d.Sharpe vs matched |
|---|---|---|---|---|---|
| g=0 on top of vol target | 23.78% / 1.026 / -31.3% | 1.103 / 0.918 | 66.3% | 1.027 | **-0.000** |
| g=0.5 on top of vol target | 24.65% / 1.042 / -30.3% | 1.144 / 0.898 | 68.3% | 1.026 | +0.016 |
| g=0.5, 2-day confirmed | 24.04% / 1.006 / -32.3% | 1.139 / 0.821 | 69.1% | 1.025 | -0.019 |
| g=0.5, hysteresis exit < 0.95 | 23.09% / 1.005 / -31.3% | 1.107 / 0.858 | 66.8% | 1.026 | -0.022 |
| no vol target, no gate (reference) | 26.94% / 0.959 / -40.5% | 1.072 / 0.794 | 77.9% | | |
| g=0 INSTEAD of vol target (raw) | 25.92% / 1.008 / -38.0% | 1.111 / 0.860 | 72.3% | 1.022 | -0.014 |
| g=0.5 INSTEAD of vol target (raw) | 26.72% / 1.010 / -36.9% | 1.123 / 0.846 | 75.1% | 1.020 | -0.011 |
| g=0 instead + global k=0.970 (matched) | 25.22% / 1.010 / -37.0% | 1.114 / 0.860 | 70.15% | 1.024 | -0.015 |
| g=0.5 instead + global k=0.933 (matched) | 25.12% / 1.013 / -34.6% | 1.128 / 0.846 | 70.15% | 1.024 | -0.011 |
| continuous min(1, 0.803/ratio) instead of vt | 24.26% / 0.983 / -34.6% | 1.102 / 0.807 | 70.15% | 1.024 | -0.041 |

On top of the vol target: g=0 is exactly zero against the matched control; g=0.5 is +0.016
but fails both-era (search 1.144 < 1.150; the whole gain is holdout). Confirmation and
hysteresis variants are negative. Instead of the vol target: the term-structure gate cannot
even reach live's exposure on its own (g=0 still deploys 72.3% because backwardation is only
10% of days) and every matched version is worse than live by 0.01 to 0.04 Sharpe, with 2 to 5
points more drawdown. **The slope cannot replace the vol target.** Sign-flips (gate in
contango) put the book in cash 90% of the time and lose 0.13 to 1.8 Sharpe against their own
matched controls, as they should.

## Part B: modulator, m = min(1, T / (vol_live x h)), h > 1 in backwardation, T re-calibrated

Calibration check: h=1 recovers T* = 0.2000 exactly (live T = 0.20).

| variant | CAGR / Sharpe / MDD | S / H | d.Sharpe vs matched | sign-flip d.Sharpe |
|---|---|---|---|---|
| h=1.25, T*=0.206 | 25.45% / 1.035 / -32.3% | 1.159 / 0.860 | **+0.011** BOTH | -0.019 |
| h=1.5, T*=0.211 | 25.52% / 1.040 / -31.4% | 1.160 / 0.872 | **+0.016** BOTH | -0.035 |
| h=2.0, T*=0.219 | 25.49% / 1.041 / -32.3% | 1.159 / 0.875 | **+0.017** BOTH | -0.055 |
| h=max(ratio,1)^1, T*=0.201 | 25.33% / 1.028 / -32.5% | 1.157 / 0.848 | +0.004 BOTH (holdout tie) | |
| h=max(ratio,1)^2, T*=0.203 | 25.37% / 1.031 / -32.3% | 1.163 / 0.848 | +0.007 (holdout tie) | |
| threshold 0.95 (24% of days), h=1.5 | 24.40% / 1.004 / -32.4% | 1.135 / 0.814 | -0.021 | |
| threshold 1.05 (4% of days), h=1.5 | 25.50% / 1.036 / -32.2% | 1.169 / 0.851 | +0.012 BOTH | |

This is the only family that passes the screen, and it is consistent in every direction a
real effect should be: sign-flips lose and lose more as h grows; the gain is a PLATEAU in h
(1.035 / 1.040 / 1.041) with drawdown not worsening, so it is not a leverage artifact; and the
structural threshold 1.0 beats 0.95 (which dilutes the signal) while 1.05 is about the same.
But the magnitude is +0.19pp/yr and +0.016 Sharpe.

Where the edge lives (h=1.5, Part E): year-by-year deltas vs live in pp of log return:
07 -0.2, 08 +0.1, 09 +0.3, 10 -2.8, 11 +3.1, 12 +0.3, 13 -1.3, 14 +1.6, 15 +1.7, 16 -0.3,
17 0.0, 18 +1.2, 19 -2.7, 20 +2.9, 21 +0.8, 22 -2.4, 23 +1.6, 24 -2.9, 25 +2.6, 26 0.0.
Sum +3.5pp over 20 years, 12 better / 7 worse, no single year carries it, and the 2022 bear
is a LOSS (-2.4pp). Rebalances 70.1/yr vs 68.2. On backwardation days the modulator holds
0.70x of live's risky exposure (median; p90 0.83), and 87% of those days live is already
capped by the vol target, so the modulator is a second, smaller cut on days the overlay is
already cutting. The recalibrated T* = 0.211 gives that exposure back on the other 90% of days.

## Part C: regime-change trigger only

| variant | Sharpe | S / H | rebal/yr | d.Sharpe vs live |
|---|---|---|---|---|
| live, no extra trigger | 1.024 | 1.150 / 0.848 | 68.2 | |
| trigger on entry INTO backwardation | 1.025 | 1.150 / 0.849 | 72.3 | +0.0003 |
| trigger on entry AND exit | 1.024 | 1.149 / 0.849 | 76.5 | +0.0002 |
| trigger on entry into realized-vol bw (10/60) | 1.024 | 1.149 / 0.849 | 74.4 | -0.0001 |
| placebo: 131 random forced rebalances, 10 seeds | mean 1.0248, min 1.0235, max 1.0261 | | | |

Forcing a rebalance to the live target on entry into backwardation adds 4 rebalances a year
and +0.0003 Sharpe, inside the range of 131 RANDOM forced rebalances (1.0235 to 1.0261). The
slope has no timing information about WHEN to act. (Mechanically this is expected: the live
target is already re-checked daily against a 3% band, so an extra forced rebalance only
matters when drift is between 0 and 3%.)

## Part D: discriminator, the same rules on the causal realized-vol proxy (vol10/vol60 > 1)

| variant | Sharpe | S / H | expo | matched live | d.Sharpe vs matched |
|---|---|---|---|---|---|
| [realized] gate g=0 on top | 0.923 | 0.897 / 0.963 | 44.2% | 1.055 | -0.132 |
| [realized] gate g=0.5 on top | 1.057 | 1.118 / 0.971 | 57.2% | 1.037 | +0.021 (search fails) |
| [realized] modulator h=1.5, T*=0.256 | 1.003 | 1.144 / 0.805 | 70.15% | 1.024 | **-0.021** |
| [realized] modulator h=2.0, T*=0.321 | 1.002 | 1.144 / 0.802 | 70.15% | 1.024 | -0.023 |
| gate g=0.5, implied AND realized bw | 1.067 | 1.166 / 0.928 | 68.7% | 1.025 | **+0.042** BOTH |
| gate g=0.5, implied bw, realized calm | 0.998 | 1.127 / 0.817 | 69.7% | 1.025 | -0.027 |
| gate g=0.5, realized bw, implied calm | 0.979 | 1.076 / 0.841 | 58.7% | 1.035 | -0.056 |

The realized 10/60 ratio as a modulator LOSES at matched exposure (-0.021) where the implied
slope wins (+0.016). So the implied term structure does carry something the realized slope
does not, and the forward-vol table in Part E shows what: the realized-proxy cells add
nothing beyond the vol level (fwd/current vol 0.75 vs 0.80 in the high-vol half, the same
ordering as the implied slope but on a partition covering 41% of days instead of 10%).

The strongest single line in the whole study is the implied-AND-realized gate, +0.042 Sharpe
vs matched, both eras. It is also the best of a post-hoc three-cell split.

## Survivors, candidate count, bootstrap, leave-one-regime-out, real rows

**24 candidates evaluated** (excluding placebos, sign-flips and controls). 5 beat live on both
eras and beat the exposure-matched live on both eras; 4 of the 5 are the same modulator at
different h, so effectively two ideas survived the screen. The threshold-1.05 modulator also
passes (6 of 24 including sensitivity), same family.

Paired circular block bootstrap vs exposure-matched live, 2,000 resamples, 4,710 sessions:

| candidate | point | block 20: Sharpe 95% CI, P(<=0) | block 60: Sharpe 95% CI, P(<=0) |
|---|---|---|---|
| modulator h=1.25 | +0.13pp/yr, +0.011 | [-0.013, +0.039] 0.210 | [-0.014, +0.038] 0.209 |
| modulator h=1.5 | +0.19pp/yr, +0.016 | [-0.027, +0.064] 0.248 | [-0.026, +0.063] 0.236 |
| modulator h=2.0 | +0.16pp/yr, +0.017 | [-0.056, +0.090] 0.357 | [-0.049, +0.088] 0.322 |
| modulator h=max(ratio,1) | +0.03pp/yr, +0.004 | [-0.004, +0.014] 0.222 | [-0.004, +0.015] 0.233 |
| gate g=0.5, implied AND realized | +0.65pp/yr, +0.042 | [-0.031, +0.116] 0.141 | [-0.028, +0.117] 0.133 |

Leave-one-regime-out (Sharpe difference vs matched live with that window removed; dot-com is
outside the VXV window and cannot be left out):

| candidate | drop GFC 2007-12..09 | drop COVID 2020 | drop 2022 | drop SPMO era 2015-11+ |
|---|---|---|---|---|
| modulator h=1.5 | +0.018 | +0.006 | +0.024 | +0.024 |
| modulator h=2.0 | +0.021 | +0.002 | +0.030 | +0.027 |
| gate implied AND realized | +0.045 | +0.030 | +0.049 | +0.080 |

All positive, none large. Dropping COVID nearly removes the modulator's edge (+0.002 to
+0.006), so the 2020 crash is the biggest single contributor even though no calendar year
dominates.

Real SPMO weekly rows (564 weeks, slope at d0, 6.2% of weeks in backwardation, 28 weeks in the
implied-AND-realized cell):

| variant | CAGR / Sharpe / MDD | expo | matched live | d.Sharpe |
|---|---|---|---|---|
| live | 30.67% / 1.260 / -25.3% | 70.1% | | |
| gate g=0 on top | 29.24% / 1.260 / -25.3% | 67.2% | 1.264 | -0.004 |
| gate g=0.5 on top | 30.05% / 1.276 / -25.3% | 68.6% | 1.262 | +0.014 |
| [realized] gate g=0.5 on top | 25.28% / 1.278 / -21.8% | 57.8% | 1.280 | -0.002 |
| modulator h=1.25, T*=0.204 | 30.70% / 1.265 / -25.7% | 70.1% | 1.260 | +0.005 |
| modulator h=1.5, T*=0.207 | 30.83% / 1.273 / -26.0% | 70.1% | 1.260 | +0.013 |
| modulator h=2.0, T*=0.212 | 30.97% / 1.281 / -26.4% | 70.1% | 1.260 | +0.021 |
| gate g=0.5, implied AND realized | 31.17% / 1.300 / -25.3% | 69.0% | 1.261 | +0.038 |

The real rows agree in sign and size with the proxy (modulator +0.01 to +0.02, the joint gate
+0.04), which is worth noting because they are independent instruments. They do not change
the magnitude.

## Part E: what the slope actually knows

Forward 21-day realized vol by cell (current vol_live vs forward vol):

| cell | n | current vol_live | fwd 21d QQQ vol | fwd 21d SPY vol | fwd/current QQQ |
|---|---|---|---|---|---|
| low vol, contango | 2,683 | 15.0% | 15.3% | 12.5% | 1.02 |
| low vol, backwardation | 96 | 19.5% | 22.1% | 19.8% | 1.14 |
| high vol, contango | 1,550 | 27.9% | 21.4% | 16.8% | 0.77 |
| high vol, backwardation | 381 | 45.0% | 36.2% | 35.6% | 0.81 |
| realized proxy: high vol, rv calm | 855 | 29.5% | 22.2% | | 0.75 |
| realized proxy: high vol, rv bw | 1,076 | 32.7% | 26.1% | | 0.80 |

Read the last column: after conditioning on the level, backwardation says forward vol will be
about 5% higher relative to current than contango does (0.81 vs 0.77). That is the entire
incremental content of the slope for a vol-targeting book, and it is the size of the effect
observed. The S&P slope forecasts QQQ forward vol (36.2%) as well as SPY forward vol (35.6%) in
the stress cell, so applying an S&P term structure to a Nasdaq book is not what limits this
line; the information is simply small once the vol level is known.

## What would have to be true for this to work

- A forward-RETURN effect. There is none: forward returns after backwardation are higher, not
  lower. Any cash gate on this signal is fighting the mean reversion the literature also
  reports.
- Backwardation would need to fire in state A, where the leveraged legs are held. It fires on
  2% of A days and 38 to 44% of E/F days.
- The incremental vol forecast would need to be several times larger than the observed 0.81 vs
  0.77 for the modulator to clear a bootstrap at 4,710 sessions.
- A Nasdaq term structure (VXN 3-month) might sharpen the vol forecast for QQQ; it is not on
  FRED and was not testable. Given that the S&P slope already forecasts QQQ vol as well as it
  forecasts SPY vol, the expected gain from that is small.

## One-line verdict

**signal-too-small**: the term structure is a marginal forward-vol forecast, directionally
consistent across every control but worth +0.01 to +0.02 Sharpe at matched exposure with
bootstrap P(<=0) of 0.21 to 0.36; the cash-gate and trigger uses are nulls, and the slope
cannot replace the vol target. Not a candidate. Nothing applied (change freeze).
