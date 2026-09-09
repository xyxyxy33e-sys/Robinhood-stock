# Overlay interactions: the full 2^3 (and 2^4) factorial of the live overlays

Research line `overlay_interactions`, 2026-09-09. Research only; change freeze until 2026-12-07, nothing applied.
Script: `paper-track/overlay_interactions.py` (runs in ~4.5 min; all figures through
`improvement_search.run/evaluate` on the 26y QQQ-core proxy and `return_frontier.eval_real` on the real weekly
SPMO rows; paired circular block bootstrap from `block_bootstrap.boot`, 2000 resamples, blocks 20/60 sessions).

**Question (owner's framing):** with base allocations and execution fixed, does each of fast re-entry (F),
graded extension trim (T) and the max(10d,30d) vol estimator (E) still earn its place alongside the others,
and is there a simpler cell that is statistically indistinguishable from LIVE?

**Answer in one paragraph.** The three overlays are additive, not interacting: every two- and three-way
interaction is below 0.01 Sharpe and below 0.3 pp CAGR, and each overlay's marginal value in the LIVE context
is within 0.02 Sharpe of its value in isolation. The trim T clearly earns its place (+0.141 Sharpe on removal
from LIVE, 95% CI [+0.018, +0.259] / [+0.030, +0.250]; +0.222 real Sharpe; +0.108 beyond an exposure-matched
control). Fast re-entry F earns its place on return (+1.82 pp/yr log-return, CI [+0.30, +3.38] / [+0.20, +3.59],
P<=0 about 0.01) with a Sharpe interval that just touches zero ([-0.006, +0.113]), and its holdout contribution
(+0.084) is the largest of the three. The fast vol estimator E does NOT earn a measurable place: +0.026 Sharpe
(CI [-0.011, +0.068], P<=0 = 0.08-0.10), -0.02 pp/yr log-return, -0.73 pp real CAGR, +13 rebalances per year
(the largest turnover item of the three), and its search-era Sharpe edge is almost entirely COVID 2020 (inside
that window +0.471; with it excluded +0.013). Exactly one simpler cell is inside LIVE's bootstrap noise on the
full proxy, both eras and the real rows: **FT- (LIVE with the plain 30-day estimator)**, at 22.15% / 0.912 /
-33.3%, S 1.100, H 0.769, real 31.40% / 1.248 / -25.0%, 55 vs 68 rebalances/yr. It is the one rule that could be
removed without measurable loss. Its expected cost is about 0.02-0.03 Sharpe concentrated in fast crashes, so
this is "signal, but not large enough to measure", not "no signal".

---

## 0. Setup and reproduction

- Factors, base allocations `TARGET_WEIGHTS` and the 20% vol target (cap 1.0) fixed, 50/200 classifier,
  3% drift band:
  - F: weights keyed by `r['eff']` (on) vs `r['state']` (off)
  - T: `extension_scale` applied (on) vs not (off); the trim uses the same state the weights use
  - E: `r['vol_live']` = max(10d,30d) (on) vs plain 30d (off)
  - V (secondary): vol-target multiplier applied (on) vs multiplier 1.0 (off)
- Cell names are three characters `F T E`, `-` for off, plus ` noVT` for V off. LIVE = `FTE`.
- Rows: proxy 6575 sessions 2000-07-03..2026-08-26; real 564 weeks 2015-11-06..2026-08-21. Same rows for every cell.
- LIVE reproduction: proxy 22.12% / 0.938 / -32.8%, S 1.150, H 0.780; real 30.67% / 1.260 / -25.3%. Exact.
- Candidate count: 16 pre-specified cells (8 primary), no parameter search, no fitted thresholds.
- Rebalances/yr are counted inside `run()` by substituting an object for `ONE_WAY_SPREAD` whose `__mul__`
  records each `cost = ONE_WAY_SPREAD * drift` call; no loop re-implemented.
- Cost sensitivity: `improvement_search.ONE_WAY_SPREAD` and `voltarget_live_backtest.ONE_WAY_SPREAD` set as
  module globals (4, 10, 20 bp).

**Data note (matters for anyone reusing rr).** On the real rows `RF.real_rows()` already stores the LIVE
max(10,30) estimator in `r['vol']` and the plain 30d in `r['vol30']` (`voltarget_live_backtest.build`, changed
2026-09-07). The briefing's "rr ... r['vol'] (30d)" is stale. A first run of this script used `r['vol']` as the
E-off estimator on rr and the E-off real cells silently fell back to the live estimator (E showed exactly zero
real effect). Fixed: E-off uses `r['vol30']` on rr, `r['vol']` on the proxy, and the script asserts
`rr['vol'] == vol_live`. The standing real figure 30.67/1.260 is unaffected (it is the E-on cell).

## 1. The 8-cell table (V on)

At 4 bp (live cost):

| cell | CAGR | Sharpe | MDD | S | H | exp | reb/yr | L1/yr | real CAGR | real Sh | real MDD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| --- | 17.98% | 0.739 | -36.4% | 0.922 | 0.594 | 75.5% | 42.4 | 18.6 | 26.60% | 1.004 | -31.4% |
| --E | 18.02% | 0.760 | -35.5% | 0.959 | 0.604 | 73.7% | 58.1 | 20.1 | 26.05% | 1.014 | -28.2% |
| -T- | 19.84% | 0.856 | -36.0% | 1.077 | 0.684 | 66.0% | 50.2 | 29.8 | 29.98% | 1.227 | -24.7% |
| -TE | 19.92% | 0.885 | -35.5% | 1.133 | 0.697 | 64.6% | 62.9 | 30.3 | 29.33% | 1.242 | -24.7% |
| F-- | 19.77% | 0.779 | -34.8% | 0.937 | 0.655 | 77.4% | 46.7 | 20.2 | 27.99% | 1.030 | -31.4% |
| F-E | 19.71% | 0.797 | -32.8% | 0.971 | 0.664 | 75.6% | 63.1 | 21.6 | 27.36% | 1.038 | -28.2% |
| FT- | 22.15% | 0.912 | -33.3% | 1.100 | 0.769 | 67.7% | 54.8 | 31.8 | 31.40% | 1.248 | -25.0% |
| **FTE (LIVE)** | **22.12%** | **0.938** | **-32.8%** | **1.150** | **0.780** | **66.2%** | **68.0** | **32.2** | **30.67%** | **1.260** | **-25.3%** |

At 10 bp:

| cell | CAGR | Sharpe | MDD | S | H | exp | reb/yr | real CAGR | real Sh | real MDD |
|---|---|---|---|---|---|---|---|---|---|---|
| --- | 16.67% | 0.699 | -37.5% | 0.882 | 0.552 | 75.5% | 42.4 | 25.50% | 0.972 | -31.6% |
| --E | 16.60% | 0.714 | -36.8% | 0.914 | 0.558 | 73.7% | 58.1 | 24.88% | 0.978 | -28.4% |
| -T- | 17.72% | 0.784 | -37.2% | 1.001 | 0.614 | 66.0% | 50.2 | 28.41% | 1.175 | -25.4% |
| -TE | 17.76% | 0.809 | -36.8% | 1.052 | 0.623 | 64.6% | 62.9 | 27.74% | 1.187 | -25.5% |
| F-- | 18.33% | 0.736 | -36.1% | 0.897 | 0.610 | 77.4% | 46.7 | 26.84% | 0.997 | -31.6% |
| F-E | 18.17% | 0.749 | -34.6% | 0.925 | 0.615 | 75.6% | 63.1 | 26.13% | 1.002 | -28.4% |
| FT- | 19.84% | 0.837 | -34.7% | 1.024 | 0.695 | 67.7% | 54.8 | 29.77% | 1.196 | -25.7% |
| **FTE (LIVE)** | **19.78%** | **0.859** | **-34.2%** | **1.069** | **0.703** | **66.2%** | **68.0** | **29.02%** | **1.205** | **-26.0%** |

At 20 bp LIVE is 15.98% / 0.727 / -36.5% (S 0.933, H 0.574), FT- 16.08% / 0.712 / -36.8%; the ordering of the
eight cells by Sharpe is unchanged at every cost. FT- has the highest CAGR at 10 bp and 20 bp.

V-off cells (multiplier 1.0), 4 bp: `FTE noVT` = `FT- noVT` 22.64% / 0.831 / -49.4%, S 1.072, H 0.657, 40
reb/yr, real 34.47% / 1.225 / -29.6%; `--- noVT` 17.44% / 0.675 / -54.6%. With V off, E is by construction
identical to E off (the estimator only enters through the multiplier), so the 16-cell design collapses to 12
distinct cells.

## 2. Main effects and interactions (2^3, V on)

Effect = mean over cells with the factor on minus mean with it off; two-way = half the difference of one
factor's effect across the other's levels; three-way = half the difference of the FxT interaction across E.
CAGR / MDD / exposure in pp, Sharpe in Sharpe units.

4 bp:

| metric | F | T | E | FxT | FxE | TxE | FxTxE |
|---|---|---|---|---|---|---|---|
| Sharpe | +0.046 | +0.129 | +0.024 | +0.008 | -0.001 | +0.004 | -0.000 |
| CAGR (pp) | +2.00 | +2.14 | +0.01 | +0.26 | -0.05 | +0.02 | -0.00 |
| MDD (pp, + = shallower) | +2.46 | +0.47 | +1.00 | +0.26 | +0.27 | -0.47 | -0.26 |
| S-Sharpe | +0.017 | +0.167 | +0.044 | +0.003 | -0.002 | +0.009 | -0.001 |
| H-Sharpe | +0.072 | +0.103 | +0.011 | +0.012 | -0.000 | +0.001 | +0.000 |
| exposure (pp) | +1.80 | -9.43 | -1.65 | -0.13 | -0.03 | +0.15 | +0.00 |
| real Sharpe | +0.022 | +0.223 | +0.011 | -0.003 | -0.001 | +0.002 | -0.000 |
| real CAGR (pp) | +1.36 | +3.34 | -0.64 | +0.02 | -0.04 | -0.05 | -0.00 |

10 bp: Sharpe F +0.044, T +0.098, E +0.019; FxT +0.008, FxE -0.001, TxE +0.004, FxTxE -0.000. CAGR F +1.84,
T +1.33, E -0.06 pp. Cost shrinks T's and E's return contribution (they add turnover) and leaves F's.

Reading: T is the dominant Sharpe effect on every window (full, search, holdout, real); F is the dominant
holdout effect and the only one that adds exposure; E is a small Sharpe-only effect that is largest on the
search era (+0.044) and near zero on holdout (+0.011) and real (+0.011), with no CAGR. The interactions are
an order of magnitude smaller than the smallest main effect. The one interaction with a consistent sign is
FxT (+0.008 Sharpe, +0.26 pp CAGR, +0.012 holdout Sharpe): fast re-entry is slightly MORE valuable when the
trim is on, because the trim cuts the A-row exposure that F's early re-entries carry into extended markets.
No interaction is negative enough to indicate offsetting.

2^4 with V (4 bp): V main effect +0.085 Sharpe, +18.5 pp MDD, +0.10 pp CAGR, -7.8 pp exposure. E x V = +0.012
= E/2 exactly, i.e. E has no existence without V (as it must). T x V +0.010 Sharpe, +0.39 pp exposure (the
trim and the vol target partly overlap in de-levering); F x V -0.38 pp CAGR (with the target on, F's re-entries
are scaled down when vol is high). All other terms below 0.01 Sharpe.

## 3. Marginal contribution: in the LIVE context vs in isolation

| overlay | context | dSharpe | dCAGR | dMDD | dS | dH | dExp | dReb/yr | dReal Sh | dReal CAGR |
|---|---|---|---|---|---|---|---|---|---|---|
| F | in LIVE (LIVE - LIVE-F) | +0.053 | +2.20 | +2.7 | +0.017 | +0.084 | +1.6 | +5.1 | +0.018 | +1.34 |
| F | isolated (F-- - ---) | +0.039 | +1.78 | +1.7 | +0.016 | +0.061 | +2.0 | +4.3 | +0.026 | +1.38 |
| T | in LIVE | +0.141 | +2.41 | +0.0 | +0.179 | +0.116 | -9.4 | +4.9 | +0.222 | +3.31 |
| T | isolated | +0.117 | +1.86 | +0.4 | +0.155 | +0.090 | -9.4 | +7.9 | +0.223 | +3.38 |
| E | in LIVE | +0.026 | -0.03 | +0.5 | +0.050 | +0.012 | -1.5 | +13.2 | +0.012 | -0.73 |
| E | isolated | +0.021 | +0.03 | +0.9 | +0.037 | +0.010 | -1.8 | +15.7 | +0.010 | -0.55 |
| V | in LIVE | +0.108 | -0.52 | +16.6 | +0.078 | +0.123 | -8.8 | +28.0 | +0.035 | -3.81 |
| V | isolated | +0.064 | +0.55 | +18.1 | +0.015 | +0.103 | -6.5 | +17.1 | +0.013 | -2.06 |

Each overlay is worth slightly MORE in the LIVE context than alone (F +0.014, T +0.024, E +0.005 Sharpe), the
signature of small positive complementarity, not duplication. At 10 bp: F +0.051 / +0.037, T +0.110 / +0.085,
E +0.022 / +0.016, V +0.101 / +0.063. With V off, F and T keep essentially the same marginal value
(F +0.056, T +0.118 in the LIVE-V context) and E is identically zero.

### 3b. Paired block bootstrap of each removal from LIVE (full proxy, 4 bp, 2000 resamples)

| removal | point log-ret | point Sharpe | block 20: log-ret CI, P<=0 | Sharpe CI, P<=0 | block 60: log-ret CI, P<=0 | Sharpe CI, P<=0 |
|---|---|---|---|---|---|---|
| LIVE vs LIVE-F (drop fast re-entry) | +1.82 pp | +0.053 | [+0.30, +3.38] 0.008 | [-0.006, +0.113] 0.042 | [+0.20, +3.59] 0.011 | [-0.008, +0.122] 0.048 |
| LIVE vs LIVE-T (drop trim) | +1.99 pp | +0.141 | [-1.33, +5.03] 0.117 | [+0.018, +0.259] 0.015 | [-1.07, +4.80] 0.090 | [+0.030, +0.250] 0.004 |
| LIVE vs LIVE-E (drop max10/30) | -0.02 pp | +0.026 | [-0.95, +1.03] 0.539 | [-0.011, +0.068] 0.100 | [-0.84, +0.95] 0.523 | [-0.009, +0.071] 0.077 |
| LIVE vs LIVE-V (drop vol target) | -0.42 pp | +0.108 | [-3.93, +3.03] 0.602 | [-0.004, +0.226] 0.033 | [-3.89, +3.08] 0.602 | [+0.003, +0.223] 0.022 |
| isolated F (F-- vs ---) | +1.50 pp | +0.039 | [-0.06, +3.00] 0.032 | [-0.016, +0.091] 0.074 | [-0.07, +3.12] 0.036 | [-0.015, +0.094] 0.079 |
| isolated T (-T- vs ---) | +1.56 pp | +0.117 | [-1.97, +4.84] 0.182 | [-0.012, +0.248] 0.038 | [-1.72, +4.49] 0.162 | [-0.000, +0.238] 0.025 |
| isolated E (--E vs ---) | +0.03 pp | +0.021 | [-0.92, +1.10] 0.506 | [-0.013, +0.059] 0.142 | [-0.89, +1.07] 0.500 | [-0.013, +0.058] 0.133 |

Compared with `block_bootstrap.py`'s additions along the single path (000 -> 100 -> 110 -> 111), the removals
from the full design are uniformly a little stronger (F +0.053 vs +0.039, T +0.141 vs +0.117), and the E result
is the same in both framings: Sharpe interval spans zero at both block lengths, log-return centred on zero.

F is a RETURN effect (log-return CI excludes zero, P about 0.01) whose Sharpe interval just touches zero
because it adds exposure and drawdown along with return. T is a SHARPE effect (interval excludes zero at both
block lengths) whose return is inside noise because it removes 9.4 pp of exposure. E is neither.

## 4. Leave-one-regime-out (Sharpe of LIVE minus LIVE-X on the proxy with the window excluded)

| removal | drop dot-com | drop GFC | drop COVID 2020 | drop 2022 | drop SPMO era | inside-window Sharpe (dot-com / GFC / COVID / 2022 / SPMO) |
|---|---|---|---|---|---|---|
| F | +0.055 | +0.039 | +0.054 | +0.063 | +0.084 | +0.213 / +0.164 / +0.034 / +0.017 / +0.017 |
| T | +0.148 | +0.146 | +0.142 | +0.152 | +0.116 | +0.106 / +0.113 / +0.394 / +0.000 / +0.179 |
| E | +0.030 | +0.023 | +0.013 | +0.030 | +0.012 | -0.022 / +0.054 / +0.471 / -0.053 / +0.050 |
| V | +0.056 | +0.112 | +0.097 | +0.106 | +0.123 | -0.093 / +0.077 / +0.573 / -0.159 / +0.078 |

F and T are positive with every regime removed and positive inside every regime (T is exactly zero inside
2022, when the market was never extended). E survives every exclusion in sign but is a COVID-2020 story: it is
negative inside dot-com and 2022 (where fast vol spikes were false alarms relative to 30d), and dropping COVID
cuts its full-period contribution from +0.026 to +0.013. V's Sharpe gain is also dominated by COVID (+0.573
inside), and V is negative inside dot-com and 2022; its full-period gain is a drawdown-control property, not a
return one (log-return -0.42 pp/yr).

## 5. Exposure accounting (each cell vs `exposure_control`, the macro-only/vol30 baseline scaled to the same average deployed capital)

4 bp; all controls matched within tolerance:

| cell | exp | k | Sharpe | ctl Sharpe | dSh vs ctl | CAGR | ctl CAGR | MDD | ctl MDD | dS | dH |
|---|---|---|---|---|---|---|---|---|---|---|---|
| --- | 75.5% | 1.000 | 0.739 | 0.739 | 0.000 | 17.98% | 17.98% | -36.4% | -36.4% | 0.000 | 0.000 |
| --E | 73.7% | 0.977 | 0.760 | 0.741 | +0.019 | 18.02% | 17.69% | -35.5% | -35.6% | +0.036 | +0.008 |
| -T- | 66.0% | 0.874 | 0.856 | 0.749 | +0.108 | 19.84% | 16.31% | -36.0% | -32.2% | +0.143 | +0.083 |
| -TE | 64.6% | 0.855 | 0.885 | 0.750 | +0.135 | 19.92% | 16.03% | -35.5% | -31.4% | +0.197 | +0.095 |
| F-- | 77.4% | 1.026 | 0.779 | 0.738 | +0.040 | 19.77% | 18.33% | -34.8% | -37.3% | +0.017 | +0.061 |
| F-E | 75.6% | 1.002 | 0.797 | 0.739 | +0.058 | 19.71% | 18.01% | -32.8% | -36.5% | +0.049 | +0.070 |
| FT- | 67.7% | 0.897 | 0.912 | 0.747 | +0.166 | 22.15% | 16.60% | -33.3% | -32.9% | +0.169 | +0.170 |
| FTE | 66.2% | 0.877 | 0.938 | 0.749 | +0.190 | 22.12% | 16.34% | -32.8% | -32.2% | +0.216 | +0.179 |
| --- noVT | 82.0% | 1.087 | 0.675 | 0.735 | -0.060 | 17.44% | 19.09% | -54.6% | -39.1% | -0.010 | -0.099 |
| -T- noVT | 72.0% | 0.954 | 0.775 | 0.743 | +0.032 | 19.48% | 17.39% | -54.0% | -34.8% | +0.131 | -0.039 |
| F-- noVT | 85.4% | 1.132 | 0.713 | 0.732 | -0.019 | 19.80% | 19.62% | -54.8% | -40.5% | +0.003 | -0.025 |
| FT- noVT | 75.0% | 0.994 | 0.831 | 0.740 | +0.091 | 22.64% | 17.90% | -49.4% | -36.2% | +0.150 | +0.062 |

None of the three overlays' Sharpe gains is a de-levering artifact: a constant scaling of the baseline to the
same capital changes Sharpe by at most +0.011 (the baseline is nearly scale-invariant), so essentially the whole
of T's +0.117 (control +0.010), F's +0.040 (control -0.001) and E's +0.021 (control +0.002) is timing. This
also serves as the constant-magnitude placebo for each overlay (briefing control 6): an untimed exposure
change of the same size does nothing. T's edge is in WHEN it de-levers (its control gives up 3.5 pp CAGR for
+0.010 Sharpe; the trim gives up 0 pp for +0.108). The vol target's own gain beyond exposure is +0.060 at the
same capital (`--- noVT` 0.675 vs its k=1.087 control 0.735), with an 18 pp MDD reduction, and it is the
only factor whose holdout Sharpe is HURT by removal in every V-off cell.

## 6. Redundancy: do two overlays make the same trades?

Daily return-difference series (overlay on minus off) and per-session target-exposure changes, 4 bp:

| context | corr F~T | corr F~E | corr T~E | sessions F / T / E active | F&T joint (same/opp) | F&E joint (same/opp) | T&E joint (same/opp) |
|---|---|---|---|---|---|---|---|
| in LIVE (LIVE minus LIVE-X) | +0.011 | -0.047 | +0.026 | 295 (4.5%) / 1012 (15.4%) / 1098 (16.7%) | 70 (70/0) | 102 (30/72) | 133 (133/0) |
| isolated (X00 minus 000) | -0.000 | -0.024 | +0.189 | 225 / 942 / 1127 | 0 | 0 | 204 (204/0) |

Exposure-intent correlations: F~T +0.084, F~E +0.006, T~E -0.098 in LIVE; +0.065 / +0.060 / +0.072 isolated.
Mean target-exposure change per session: F +1.64 pp, T -9.42 pp, E -1.51 pp.

- T and E both de-lever, and are the only pair with a non-trivial return-diff correlation (+0.19 in isolation,
  +0.03 in the LIVE context). But they overlap on only 133 of 6575 sessions (2.0%): T acts alone on 879, E
  alone on 965. On the joint sessions T removes 49.0 session-fractions of exposure vs E's 6.7, i.e. where they
  coincide the trim does the work and E adds 14% on top. Not duplicates: T fires on extension above the SMAs
  (calm melt-ups), E fires on 10-day vol spikes (shocks), and those are different days.
- F and E are the one mildly OFFSETTING pair: on 72 of their 102 joint sessions F is adding exposure (early
  re-entry) while E is cutting it (the re-entry happens into a still-elevated 10d vol). Realized return-diff
  sign agreement is 72/261 same vs 189 opposite. The net is small (corr -0.047, FxE interaction -0.001 Sharpe)
  because E's multiplier only shaves the re-entry, it does not cancel it.
- F and T never conflict (70/70 same direction in LIVE; F's downgrade days coincide with trim days).

So no overlay duplicates another, and the only offset (F vs E) is worth -0.001 Sharpe.

## 7. Simplification candidates

Rankings (4 bp holdout Sharpe, 4 bp real Sharpe, 10 bp CAGR):

- Holdout: FTE 0.780 > FT- 0.769 > -TE 0.697 > -T- 0.684 > F-E 0.664 > F-- 0.655 > --E 0.604 > --- 0.594
- Real: FTE 1.260 > FT- 1.248 > -TE 1.242 > -T- 1.227 > F-E 1.038 > F-- 1.030 > --E 1.014 > --- 1.004
- CAGR 10 bp: FT- 19.84% > FTE 19.78% > F-- 18.33% > F-E 18.17% > -TE 17.76% > -T- 17.72% > --- 16.67% > --E 16.60%
- 16 cells: `FT- noVT` / `FTE noVT` lead CAGR at 10 bp (20.03%) but sit 6th on holdout (0.657) and 5th on
  real (1.225), with MDD -49%/-52%: the vol target is a risk-preference dial that is Sharpe- and
  holdout-positive, and turning it off is not a simplification candidate under the "beat on both eras" rule.

Screen: paired bootstrap of LIVE minus cell on the search era, the holdout era and the real weekly rows
(blocks 4/12 weeks, Sharpe rescaled to weekly), plus the full proxy. Sharpe 95% CIs, 4 bp:

| cell | point dS / dH / dReal | full 20 / 60 | S 20 / 60 | H 20 / 60 | real 4 / 12 |
|---|---|---|---|---|---|
| FT- (drop E) | -0.050 / -0.012 / -0.012 | [-0.01,+0.07] / [-0.01,+0.07] | [-0.02,+0.14] / [-0.02,+0.14] | [-0.02,+0.04] / [-0.02,+0.04] | [-0.04,+0.08] / [-0.04,+0.08] |
| -TE (drop F) | -0.017 / -0.084 / -0.018 | [-0.01,+0.12] / [-0.01,+0.12] | [-0.06,+0.09] / [-0.06,+0.10] | [-0.01,+0.18] / [-0.01,+0.19] | [-0.09,+0.12] / [-0.08,+0.11] |
| -T- (drop F, E) | -0.073 / -0.096 / -0.033 | [+0.01,+0.15] / [+0.01,+0.16] | [-0.04,+0.19] / [-0.04,+0.18] | [-0.00,+0.19] / [-0.01,+0.20] | [-0.08,+0.15] / [-0.08,+0.15] |
| F-E (drop T) | -0.179 / -0.116 / -0.222 | [+0.02,+0.27] / [+0.03,+0.25] | [-0.03,+0.40] / [-0.01,+0.38] | [-0.02,+0.25] / [-0.01,+0.24] | [-0.03,+0.52] / [-0.01,+0.49] |
| F-- | -0.212 / -0.125 / -0.230 | [+0.03,+0.30] / [+0.04,+0.29] | [-0.02,+0.44] / [-0.01,+0.43] | [-0.02,+0.28] / [-0.01,+0.26] | [-0.04,+0.53] / [-0.01,+0.52] |
| --E | -0.191 / -0.176 / -0.246 | [+0.04,+0.31] / [+0.05,+0.30] | [-0.03,+0.42] / [-0.00,+0.40] | [+0.00,+0.35] / [+0.02,+0.34] | [-0.03,+0.56] / [-0.02,+0.54] |
| --- | -0.228 / -0.186 / -0.256 | [+0.06,+0.35] / [+0.06,+0.33] | [-0.02,+0.48] / [+0.00,+0.46] | [+0.01,+0.36] / [+0.02,+0.36] | [-0.04,+0.58] / [-0.01,+0.56] |
| FT- noVT | -0.078 / -0.123 / -0.035 | [-0.00,+0.23] / [-0.00,+0.22] | [-0.10,+0.30] / [-0.09,+0.27] | [-0.01,+0.27] / [-0.03,+0.26] | [-0.10,+0.20] / [-0.09,+0.19] |

**Power caveat, stated plainly.** The per-era and real-row intervals are wide (10.8 y, 15.3 y and 564 weeks
respectively), so the literal criterion "CI spans zero on S, H and real" is necessary but not sufficient: it
lets through `F--` (real Sharpe 0.230 below LIVE) and even `F-E` (drop the trim). The full 26-year proxy is the
only window with enough power to separate cells, and there only two removals keep a zero-spanning Sharpe
interval: `FT-` (drop E) and `-TE` (drop F). Of these, dropping F costs +1.82 pp/yr of log-return with a CI
that excludes zero at both block lengths and costs 0.084 of holdout Sharpe, so `-TE` is not a free removal.
Dropping E costs nothing measurable on any window at any block length: -0.02 pp/yr log-return, Sharpe CI
[-0.011, +0.068], holdout -0.012, real -0.012, and it saves 13 rebalances a year (68 -> 55, -19%) and 0.4 L1
turnover.

**Verdict.** T earns its place unambiguously; F earns its place as a return overlay (and is the biggest
holdout contributor); E does not earn a MEASURABLE place beside the other two. The simpler cell `FT-` (LIVE with
the plain 30-day estimator) is statistically indistinguishable from LIVE on the full proxy, both eras and the
real rows, and is the one rule in the design that could be removed without measurable loss. What would have
to be true for E to be worth keeping: another COVID-type crash in which 10-day vol spikes days before 30-day
vol; inside 2020 alone E was worth +0.471 Sharpe, and outside it +0.013. That is a real but rare
insurance-like property ("signal, but not large enough to measure"), not "no signal". Nothing changes under
the freeze; this is the evidence for the 2026-12-07 review.

## Controls checklist

1. Both-era: no cell beats LIVE on both eras; the closest is FT- (S -0.050, H -0.012). Reported as a
   simplification, not an improvement.
2. Exposure match: section 5; every overlay's Sharpe gain survives an exposure-matched control by more than
   the control's own change.
3. Causal thresholds: none fitted; all overlays use the live constants.
4. Same rows: all 16 cells on the same 6575 proxy sessions and 564 real weeks; E-off on the real rows uses
   `vol30`, never falls back to the live estimator (assertion in the script).
5. Block bootstrap: sections 3b and 7, blocks 20/60 (proxy) and 4/12 weeks (real), 2000 resamples.
6. Placebo: the exposure-matched control is the constant-magnitude placebo for each overlay (section 5).
7. Leave-one-regime-out: section 4.
8. Candidate count: 16 pre-specified cells, no search.
9. Real-instrument confirmation: real Sharpe FTE 1.260 vs FT- 1.248 (CI spans zero); T's real contribution
   +0.222 and F's +0.018 are consistent with the proxy ordering.
