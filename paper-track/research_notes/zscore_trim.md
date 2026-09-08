# Research line `zscore_trim` — vol-normalised extension-trim thresholds (2026-09-08)

**Verdict: no signal.** Expressing the extension gap as a z-score (gap ÷ horizon-scaled
realized vol) makes the graded trim worse on the proxy in BOTH eras and on real SPMO rows,
at matched vote frequency and at matched exposure. The block bootstrap puts the z-trim
below live (P(Sharpe diff ≤ 0) = 0.88–0.91), every leave-one-regime-out drop keeps the
negative sign, and a placebo with the vol term shuffled by year lands at the same Sharpe
as the real z-trim (2 of 20 placebos beat it). The milder multiplicative vol-scaling is
worse still. 41 variants, 0 both-era winners. Research only — change freeze; nothing applied.

Script: `paper-track/zscore_trim.py` (~1 min; `FAST=1` skips the bootstraps). Harness:
the project's own loop via the `leverage_under_trim.py` bootstrap; live figures reproduce
exactly (proxy 22.12% / 0.938 / −32.8%, S 1.150, H 0.780; real weekly 30.67% / 1.260 / −25.3%).

## Hypothesis and design

Live: votes for {100d gap > 10%, 150d gap > 12%, 200d gap > 15%}, gap = close/SMA − 1,
effective state A only, four risky legs × (1 − votes/3), then max(10,30) vol target.
A 10% stretch over the 100d SMA is ~1 sd at 35% vol and ~3 sd at 12% vol, so the
hypothesis was: `z_n = gap_n / (vol × sqrt(n/252))`, votes = count of `z_n > k_n`,
should fire on a genuinely extended tape and not on a merely volatile one.

- Two vol inputs: 30d (`z30`) and the live max(10d,30d) (`zLIVE`).
- **k calibrated so the search-era A-day vote frequency matches live's** per window
  (changes WHEN it fires, not HOW OFTEN), plus a single common k matched on mean votes
  per A-day, plus a sweep of the common k from 0.6 to 2.8.
- Because the briefing forbids fitting a threshold on the search era and applying it
  backward, the same rule was also run (a) with k fitted on the HOLDOUT A-days and
  applied forward, (b) with an expanding causal quantile (k_n at each A-day = the
  quantile of all PRIOR A-day z_n at the prior live fire rate; 250-A-day warm-up falls
  back to the live vote), and (c) with a common k re-calibrated by bisection until
  average deployed exposure equals live's 66.21%.
- Milder version: keep the price thresholds, multiply by (vol / median vol)^a for
  a ∈ {0.5, 1}, median either expanding-causal (from 1999-09) or full-sample (reference).
- Hybrids: per-window AND / OR of the price test and the z test.
- Everything else live (fast overlay, max(10,30) vol target, A-only, step ⅓, 3% band, 4bp).
- Real rows: z attached by date from the daily series (every weekly d0 is in the daily
  rows with identical gaps and vol); `vol_live` attached per the briefing pattern.

Calibrated thresholds (search-era A-days, 1848 of them; holdout 2061): per-window k on
vol30 = 1.27 / 1.18 / 1.29 for 100/150/200d (vol_live 1.21 / 1.09 / 1.20); common k =
1.248 (vol30), 1.166 (vol_live). Live's search-era per-window fire rates are 15.7% /
20.9% / 18.7%. Holdout-fitted k is lower: 1.06 / 1.09 / 1.19 (vol30).

## Main table (proxy 2000-07..2026-08, 6575 sessions; real SPMO-era weekly, 564 rows)

fireA = share of effective-A days with ≥1 vote (search / holdout); mv = mean votes per
A-day; depth = mean risky-leg trim on A-days; exp = average deployed capital.

| variant | fireA S/H | mv S/H | depth S/H | exp | proxy CAGR / Sharpe / MDD | S | H | both? | real CAGR / Sharpe / MDD |
|---|---|---|---|---|---|---|---|---|---|
| **LIVE price rule** | 25.8 / 26.0% | .552 / .505 | 18.4 / 16.8% | 66.21% | **22.12% / 0.938 / −32.8%** | **1.150** | **0.780** | — | **30.67% / 1.260 / −25.3%** |
| z30 per-window k (search-cal) | 24.5 / 16.2% | .551 / .334 | 18.4 / 11.1% | 67.02% | 20.76% / 0.862 / −32.8% | 1.069 | 0.708 | no | 28.12% / 1.118 / −25.9% |
| zLIVE per-window k (search-cal) | 24.2 / 16.6% | .551 / .341 | 18.4 / 11.4% | 66.94% | 21.85% / 0.898 / −32.8% | 1.140 | 0.719 | no | 29.58% / 1.178 / −24.3% |
| z30 common k=1.25 | 24.9 / 15.9% | .553 / .325 | 18.4 / 10.8% | 67.10% | 20.89% / 0.866 / −32.8% | 1.063 | 0.719 | no | 27.41% / 1.093 / −25.9% |
| zLIVE common k=1.17 | 24.8 / 16.5% | .553 / .339 | 18.4 / 11.3% | 66.94% | 21.92% / 0.901 / −32.8% | 1.132 | 0.730 | no | 30.11% / 1.191 / −24.3% |
| z30 per-window k (holdout-cal, causal fwd) | 31.3 / 23.3% | .751 / .503 | 25.0 / 16.8% | 63.45% | 20.34% / 0.864 / −32.8% | 1.030 | 0.741 | no | 25.24% / 1.059 / −24.3% |
| zLIVE per-window k (holdout-cal) | 30.5 / 22.8% | .739 / .503 | 24.6 / 16.8% | 63.53% | 21.30% / 0.895 / −32.8% | 1.111 | 0.736 | no | 28.27% / 1.171 / −24.3% |
| z30 expanding causal quantile | 27.7 / 43.4% | .640 / .980 | 21.3 / 32.7% | 59.90% | 22.09% / 0.946 / −32.8% | 1.047 | 0.867 | no | 26.81% / 1.084 / −25.8% |
| zLIVE expanding causal quantile | 26.2 / 40.8% | .624 / .928 | 20.8 / 30.9% | 60.56% | 22.63% / 0.960 / −32.8% | 1.101 | 0.850 | no | 26.42% / 1.068 / −25.9% |
| z30 common k=1.21 (exposure-matched) | 26.7 / 17.5% | .611 / .359 | 20.4 / 12.0% | 66.21% | 21.05% / 0.874 / −32.8% | 1.064 | 0.734 | no | 26.45% / 1.068 / −25.9% |
| zLIVE common k=1.14 (exposure-matched) | 26.3 / 18.3% | .595 / .373 | 19.8 / 12.4% | 66.20% | 21.51% / 0.890 / −32.8% | 1.118 | 0.722 | no | 29.94% / 1.201 / −24.3% |

At matched frequency the z-trim keeps the search-era firing rate (24–25% vs 25.8%) but
fires far less in the holdout (16% vs 26%) — the holdout is a higher-vol era, so the
same z hurdle is a higher price hurdle there. Even so, exposure is within 0.9pp of
live's, and the exposure-matched k (row 10–11) makes no difference: −0.05 to −0.06
Sharpe on the full proxy, worse in both eras, −0.06 to −0.19 Sharpe on real rows.

**Controls at the candidate's exposure** (`exposure_control` = the macro-only vol30
baseline scaled by k, as mandated; "live-scaled" = the actual live design scaled to the
same deployed capital — the sharper control for a trim-only change):

| candidate (exp) | candidate Sharpe (S/H) | exposure_control k / Sharpe (S/H) | live-scaled k / Sharpe (S/H) |
|---|---|---|---|
| z30 common k=1.25 (67.10%) | 0.866 (1.063 / 0.719) | 0.888 / 0.747 (0.932 / 0.600) | 1.014 / 0.937 (1.149 / 0.779) |
| zLIVE common k=1.17 (66.94%) | 0.901 (1.132 / 0.730) | 0.886 / 0.748 (0.932 / 0.600) | 1.011 / 0.937 (1.149 / 0.779) |
| z30 expanding causal (59.90%) | 0.946 (1.047 / 0.867) | 0.793 / 0.757 (0.944 / 0.608) | 0.905 / 0.946 (1.161 / 0.785) |
| zLIVE expanding causal (60.56%) | 0.960 (1.101 / 0.850) | 0.801 / 0.757 (0.943 / 0.608) | 0.915 / 0.945 (1.160 / 0.784) |
| volscaled a=1 exp vol30 (49.95%) | 0.813 (0.938 / 0.714) | 0.660 / 0.776 (0.963 / 0.626) | 0.754 / 0.960 (1.177 / 0.798) |

Every z variant beats the mandated `exposure_control` (as live itself does — that
baseline has no overlay and no trim) and every one LOSES to the live design scaled to
its own exposure. The expanding-causal rows are the instructive case: their headline
proxy Sharpe (0.946 / 0.960) exceeds live's 0.938 only because they hold 6pp less
capital (holdout fireA 41–43% vs 26%); the scaled live book at the same exposure gives
0.945–0.946, and they lose the search era (1.047 / 1.101 vs 1.150) and the real rows
(1.068–1.084 vs 1.260). That is a risk dial, not an edge.

### Common-k sweep — no plateau anywhere

| k (vol30) | fireA S/H | exp | proxy Sharpe | S | H | real Sharpe |
|---|---|---|---|---|---|---|
| 0.6 | 73 / 64% | 42.3% | 0.820 | 0.934 | 0.739 | 1.029 |
| 0.8 | 55 / 49% | 51.6% | 0.862 | 0.936 | 0.809 | 1.156 |
| 1.0 | 40 / 32% | 59.7% | 0.904 | 1.054 | 0.796 | 1.104 |
| 1.2 | 28 / 18% | 65.9% | 0.871 | 1.052 | 0.736 | 1.064 |
| 1.4 | 18 / 11% | 70.1% | 0.864 | 1.068 | 0.711 | 1.165 |
| 1.6 | 10 / 6% | 72.9% | 0.865 | 1.090 | 0.695 | 1.124 |
| 2.0 | 2 / 1% | 75.1% | 0.824 | 1.015 | 0.678 | 1.036 |
| 2.8 (never fires) | 0 / 0% | 75.6% | 0.798 | 0.971 | 0.666 | 1.038 |

Same shape on vol_live (best k=1.0: 0.924, S 1.163, H 0.750, exp 62.2%, real 1.175).
No k beats live 0.938 / 1.150 / 0.780 on the full proxy or both eras; the holdout gains
at k ≤ 1.0 come with 7–15pp less exposure and search-era losses. The "never fires" row
(0.798) confirms the live trim's +0.14 Sharpe is intact in this harness.

### Milder version: price thresholds × (vol / median)^a

| variant | fireA S/H | exp | proxy Sharpe | S | H | real Sharpe |
|---|---|---|---|---|---|---|
| a=0.5, expanding median, vol30 | 38 / 45% | 57.5% | 0.877 | 1.024 | 0.763 | 1.250 |
| a=0.5, expanding median, vol_live | 34 / 42% | 59.1% | 0.910 | 1.107 | 0.757 | 1.250 |
| a=1.0, expanding median, vol30 | 47 / 60% | 50.0% | 0.813 | 0.938 | 0.714 | 1.139 |
| a=1.0, expanding median, vol_live | 41 / 56% | 52.6% | 0.884 | 0.996 | 0.796 | 1.139 |
| a=0.5, full-sample median, vol30 | 37 / 31% | 61.1% | 0.901 | 1.036 | 0.802 | 1.263 |
| a=0.5, full-sample median, vol_live | 34 / 28% | 62.6% | 0.912 | 1.125 | 0.755 | 1.263 |
| a=1.0, full-sample median, vol30 | 46 / 38% | 56.0% | 0.878 | 0.959 | 0.820 | 1.122 |
| a=1.0, full-sample median, vol_live | 40 / 33% | 58.8% | 0.876 | 1.021 | 0.770 | 1.122 |

All worse on the full proxy and the search era. Scaling thresholds up with vol lowers
them below the median (the median vol30 is 17.8%; the expanding median at 2015-11 was
18.8%), so the rule fires on 34–60% of A-days instead of 26% and turns into a blunt
exposure cut (exp 50–63%). The one real-row tie (a=0.5, full median: 1.263 vs 1.260)
is non-causal, holds 5pp less capital, and loses 0.4pp CAGR.

### Hybrids

| variant | fireA S/H | exp | proxy Sharpe | S | H | real | live-scaled control |
|---|---|---|---|---|---|---|---|
| AND price & z30 | 14 / 10% | 71.4% | 0.877 | 1.081 | 0.723 | 1.125 | 0.933 |
| AND price & zLIVE | 14 / 11% | 71.4% | 0.901 | 1.127 | 0.731 | 1.184 | 0.933 |
| OR price & z30 | 37 / 32% | 61.9% | 0.929 | 1.134 | 0.778 | 1.231 | 0.943 |
| OR price & zLIVE | 37 / 32% | 61.8% | 0.940 | 1.158 | 0.780 | 1.272 | 0.943 |

OR-with-zLIVE is the closest anything came: proxy 0.940 vs 0.938, search 1.158 vs
1.150, holdout 0.780 = 0.780 (0.7800 vs 0.7803, fails the strict both-era test), real
1.272 vs 1.260 with CAGR 30.26% vs 30.67%. It deploys 4.4pp less capital and the live
book scaled to that exposure gives 0.943 — the improvement is the exposure cut, not the
signal. Risk-preference dial at most; inside noise on every metric.

## Mechanism check: where the two rules disagree

A-days, z30 common k=1.25 vs live; QQQ forward return from the decision close.

| bucket | n | mean vol | mean 200d gap | z200 | 5d mean / hit | 21d mean / hit | 21d ann. Sharpe |
|---|---|---|---|---|---|---|---|
| both trim | 470 | 14.0% | 17.7% | 1.44 | −0.13% / 53% | **−0.31% / 57%** | −0.21 |
| LIVE only (live trims, z holds) | 542 | 23.0% | 14.6% | 0.79 | +0.22% / 56% | +1.38% / 67% | 0.93 |
| CAND only (z trims, live holds) | 318 | 8.9% | 11.8% | 1.51 | +0.26% / 63% | +0.96% / 67% | 1.00 |
| neither | 2579 | 17.2% | 7.3% | 0.57 | +0.33% / 61% | +1.04% / 64% | 0.76 |

By vote difference (z − live): −3: n 149, 21d +1.84% (hit 71%); −2: n 232, +2.24% (72%);
−1: n 305, +0.63%; 0: n 2796, +0.80%; +1: n 160, +0.85%; +2: n 115, +0.54%; +3: n 152, +1.03%.

By era: holdout — CAND only n 116 −0.03% (hit 55%), LIVE only n 323 +1.30% (68%), both
n 212 +0.06% (58%), neither n 1410 +0.57%; search — CAND only n 202 +1.53% (74%), LIVE
only n 219 +1.48% (66%), both n 258 −0.62% (55%), neither n 1152 +1.61%.

Reading: the only bucket with NEGATIVE forward returns is where the two rules AGREE —
gap ~18% over the 200d at ~14% vol, z ~1.4. Both disagreement buckets have positive
forward returns, so neither rule's private trims are catching anything; the trim's edge
lives in the intersection, and the z-rule does not sharpen it. Vote-days per year (live /
z): 2003 305/19, 2009 362/140, 2020 401/162 (post-crash melt-ups, high vol: z holds) vs
2013 0/68, 2014 0/88, 2017 5/231, 2019 18/70 (calm grind-ups, ~9% vol: z trims).

**P&L attribution through the harness** (sum of daily return differences, z30 − live, pp):

| bucket | n | holdout | search | total | mean/day |
|---|---|---|---|---|---|
| both trim | 470 | −6.61 | +8.80 | +2.19 | +0.5 bp |
| LIVE only | 542 | +4.07 | +3.64 | +7.71 | +1.4 bp |
| CAND only | 318 | −5.81 | −22.26 | **−28.07** | **−8.8 bp** |
| neither / not A | 5245 | ~0 | ~0 | +0.10 | 0 |

Per-year: 2009 +20.2, 2014 +10.3, 2023 +8.3, 2020 +5.2 vs 2017 −11.3, 2007 −10.2,
2024 −8.3, 2012 −7.5, 2010 −6.0, 2019 −5.8. (zLIVE: LIVE-only +27.6, CAND-only −21.4,
both −2.9; same shape.)

This is the whole story. Un-trimming the high-vol "LIVE only" days recovers only
+7.7pp over 26 years because on a 23%-vol tape the vol target already sizes the book at
~0.87 and the trim there is mostly a variance cut, which is what Sharpe rewards.
Trimming the "CAND only" days costs −28pp because on a 9%-vol tape the trim gives up
drift (+1.0% per 21 sessions, 67% hit rate) while removing almost no variance. A
z-score deliberately fires MORE when vol is LOW — it is built to trim the quiet grind-up,
and the quiet grind-up is exactly where trimming is pure cost. The price rule's
"defect" (10% is 3 sd at 12% vol) is a feature: an extension that has built up on a
low-vol tape is a big move relative to the noise, but it is not the overheated,
high-participation tape the trim earns its keep on.

Churn: vote changes/yr live 15.7, z30 12.2, zLIVE 12.6 (the z-rule churns LESS on the
proxy, so turnover is not what kills it); volscaled a=1: 20.6.

## Bootstrap, leave-one-regime-out, placebo

Circular block bootstrap, 2000 resamples, paired blocks, candidate minus live:

| candidate | point | block | log-return 95% CI (pp/yr) | P(≤0) | Sharpe 95% CI | P(≤0) |
|---|---|---|---|---|---|---|
| z30 common k=1.25 | −1.01pp, −0.072 | 20d | [−3.95, +2.19] | 0.736 | [−0.192, +0.052] | 0.875 |
| | | 60d | [−3.90, +2.03] | 0.757 | [−0.186, +0.043] | 0.895 |
| z30 per-window search-cal | −1.12pp, −0.076 | 20d | [−4.15, +2.01] | 0.778 | [−0.198, +0.044] | 0.894 |
| | | 60d | [−4.17, +1.95] | 0.773 | [−0.195, +0.039] | 0.905 |
| volscaled a=1 exp vol30 | −4.53pp, −0.126 | 20d | [−8.44, −0.57] | 0.988 | [−0.291, +0.039] | 0.929 |
| | | 60d | [−8.69, −0.46] | 0.986 | [−0.294, +0.044] | 0.927 |

Leave-one-regime-out (Sharpe diff, z30 common k): drop dot-com −0.070, GFC −0.081,
COVID −0.067, 2022 −0.078, whole SPMO era −0.061. Per-window: −0.072 to −0.082.
Volscaled: −0.066 to −0.141. Every drop keeps the negative sign; the loss is not one
episode (it is the sum of 2007, 2010–12, 2017–19, 2024).

Placebo — z30 common k=1.25 with the vol series block-shuffled by calendar year (each
year's vol path replaced by another year's, level and persistence preserved, 20 seeds):
placebo Sharpe min 0.790 / median 0.843 / max 0.908 (search median 1.031, holdout
0.693; exposure 69.9%). The real z-trim scores 0.866 — inside the placebo range, 2 of 20
placebos beat it, 0 of 20 beat live 0.938. Normalising by the RIGHT year's vol is
indistinguishable from normalising by a random year's. With vol replaced by its constant
median (a re-scaled price rule at ~9% fire rate): 0.841.

## Candidate count

41 variants evaluated on the proxy (2 vol inputs × {per-window search-cal, common
search-cal, per-window holdout-cal, expanding causal, exposure-matched} = 10; common-k
sweep 18; volscaled 8; hybrids 4; constant-vol 1), plus 20 placebo draws. **0 beat live
on both eras**; 0 beat live on the full proxy at matched exposure; 1 (OR-zLIVE) ties
live within noise at 4.4pp lower exposure and equals its own scaled-live control.

## Verdict and what would have to be true

**No signal.** The z-score normalisation is not a refinement of the trim; it is a
different trim that fires on low-vol grind-ups, and those are the days where trimming
costs the most. This is consistent with the briefing's standing lesson: vol works as a
SCALING input (the vol target, which already handles the high-vol side of these days),
and fails as a TIMING input. Here it was a timing input.

For a vol-normalised threshold to work, low-vol extensions would have to mean-revert
harder than high-vol ones. The data say the opposite: 21-session forward return after a
z-only trim day is +0.96% (hit 67%), and the "both trim" bucket's −0.31% comes from
high-gap days at ordinary (14%) vol, which the price rule already catches. No variant
of k, vol window, calibration era, exponent, or hybrid changed that ordering.

Nothing to apply, and nothing here weakens the live trim: the never-fires row (0.798)
and the "both trim" bucket reconfirm that the price-gap trim's +0.14 Sharpe is where it
was.
