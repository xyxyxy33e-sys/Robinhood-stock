# EXTENSION_STEP: keep 1/3, or move to 0.5? — 2026-09-20

**Verdict: NOT applied. Research result is mixed — six of eight bars pass,
the bootstrap and the honest permutation fail, and the ranking is not stable
to the trim thresholds. Owner decides.**

Script: `paper-track/extension_step_decision.py`
Log: `research_notes/extension_step_decision_run.log`

## Why this line exists

The trim-destination study (2026-09-20, Part III) ended by saying that what
its best cell "DEEP" actually measured was trim **depth**, not the
destination of the trimmed weight — and that the decision it really posed
was whether to revisit `EXTENSION_STEP`. Owner asked for exactly that test,
scoped to two schedules: the live 1/3 and 0.5. One decision, made once, on
the current baseline, with the full battery.

## The two arms

A-row (SPMO, TQQQ, cash) at 0 / 1 / 2 / 3 extension votes. The vol target
multiplies on top, as live. Rung 0 is identical in both arms.

| votes | STEP 1/3 (live) | STEP 0.5 |
|---|---|---|
| 0 | 50 / 50 / 0 | 50 / 50 / 0 |
| 1 | 33.3 / 33.3 / 33.3 | 25 / 25 / 50 |
| 2 | 16.7 / 16.7 / 66.7 | 0 / 0 / 100 |
| 3 | 0 / 0 / 100 | 0 / 0 / 100 |

0.5 is deeper at 1 vote and reaches full cash at 2 votes instead of 3.

## Code fact found while setting this up (applies whatever is decided)

`state.extension_scale()` returns `1.0 - EXTENSION_STEP * votes` with **no
clip at zero**. At STEP 1/3 the expression never goes negative (3 × 1/3 =
1.0 exactly), which is why no clip exists today. At STEP 0.5, 3 votes gives
−0.500, and `target_weights_with_voltarget('A', ...)` then returns
(core −0.250, tqqq −0.250, qld 0, xlu 0, cash +1.500). `validate_weights`
raises `WeightSanityError`, and the live trigger **aborts** — it would not
trade the intended cash row, it would fail to trade at all, on every 3-vote
day. **Adopting 0.5 requires a one-line clip in `state.py` first**
(`max(0.0, 1.0 - EXTENSION_STEP * votes)`). The research harness clips at 0,
so the 0.5 arm measured here is the intended all-cash row.

## Headline

Deltas are 0.5 minus 1/3.

| arm | proxy full | S | H | exp | reb | real daily | exp | reb |
|---|---|---|---|---|---|---|---|---|
| STEP 1/3 (live) | 25.46% / 1.071 / −27.0% | 1.399 | 0.825 | 62.2% | 47.9 | 37.30% / 1.475 / −18.6% | 67.2% | 45.3 |
| STEP 0.5 | 25.78% / 1.094 / −26.6% | 1.424 | 0.846 | 59.9% | 44.8 | 37.60% / 1.501 / −18.4% | 64.9% | 44.8 |
| delta | +0.32 pp / +0.023 / +0.4 pp | +0.026 | +0.021 | −2.3 | −3.2 | +0.29 pp / +0.026 / +0.2 pp | −2.3 | −0.6 |

The real-daily arm was cross-checked against an independent standalone loop
(CAGR, Sharpe, MaxDD, rebalances/yr and all twelve per-year returns agree
within 0.06 pp).

## Verdict card against the project bar

| # | test | result |
|---|---|---|
| 1 | both-era improvement (search AND holdout Sharpe up) | dS +0.026, dH +0.021 → **PASS** |
| 2 | beats the exposure-matched control | proxy S +0.021, H +0.019; real +0.023 → **PASS** |
| 3 | block bootstrap P(≤0) < 0.05, 60d | 0.105 / 0.113 / 0.150 / 0.179 → **FAIL** |
| 4 | permutation p < 0.05 | single pre-specified p 0.000 PASS; honest menu p 0.755–0.932 → **FAIL** |
| 5 | real CAGR not falling | +0.29 pp → **PASS** |
| 6 | one-session execution lag (the DEEP killer) | search +0.003, real +0.000 → **PASS** |
| 7 | 20 bp one-way cost | search +0.009, holdout +0.008, real +0.009 → **PASS** |
| 8 | LORO across five dropped regimes | +0.020 … +0.029, all positive → **PASS** |

### The two failures, stated properly

**Bootstrap.** 2000 circular block draws, paired (same blocks for both
series). No Sharpe CI excludes zero: P(≤0) is 0.105 (proxy vs live, 60d),
0.113 (vs control), 0.150 (real vs live), 0.179 (real vs control). On
**log return** rather than Sharpe, the comparison against the
exposure-matched control does pass: P 0.014 (proxy 60d), 0.032 (real 60d),
0.025/0.047 at 20d. Against live itself, return P is 0.28–0.36. So the
honest reading is: the gain is real enough as return-per-unit-of-capital-held,
and not distinguishable from noise as risk-adjusted return.

**Permutation.** Vote labels shuffled among effective-A days, counts kept,
both arms re-evaluated on the same shuffle. 1000 draws (this supersedes the
8-draw section 4b in the log):

| null | median | 95th | max | real | p |
|---|---|---|---|---|---|
| single pre-specified, full period | −0.042 | −0.012 | +0.017 | +0.023 | **0.000** |
| single pre-specified, both-era min | −0.056 | −0.023 | +0.005 | +0.021 | **0.000** |
| menu of 4 scalar steps, full period | +0.048 | +0.074 | +0.105 | +0.023 | 0.932 |
| menu of 4 scalar steps, both-era min | +0.035 | +0.063 | +0.094 | +0.021 | 0.755 |

Pre-specified, STEP 0.5 clearly beats its own null — the null median is
**negative**, i.e. on random vote days a deeper trim *hurts*, so the vote
label does carry the information. Chosen from the menu of four steps
{0.25, 1/3, 0.5, 1}, it does not: a shuffle typically hands some step in the
menu a bigger gain than 0.5 earns on the real labels. The menu null is the
honest one here, because the step has already been moved once (0.25 → 1/3
on 2026-09-06).

## What does not hold up: threshold sensitivity

Shifting the three trim thresholds (10/12/15%) together:

| shift | thresholds | A days ≥1 vote | proxy dF | dS | dH | d real | ranking |
|---|---|---|---|---|---|---|---|
| −2 pp | 8/10/13 | 1569 | −0.031 | −0.067 | −0.004 | −0.064 | **1/3 ahead** |
| −1 pp | 9/11/14 | 1255 | +0.010 | +0.024 | −0.001 | +0.023 | mixed |
| 0 | 10/12/15 | 1012 | +0.023 | +0.026 | +0.021 | +0.026 | 0.5 ahead |
| +1 pp | 11/13/16 | 800 | +0.008 | +0.015 | +0.002 | +0.011 | 0.5 ahead |
| +2 pp | 12/14/17 | 636 | +0.004 | +0.011 | −0.002 | +0.014 | mixed |

The ranking **flips** two points to the loose side. The A-row sensitivity is
by contrast stable: 0.5 is ahead at 40/60, 50/50 and 60/40 (dF +0.022 to
+0.025, real +0.024 to +0.028).

## What it costs, and where

- **Time fully in cash rises 26.6% → 31.6% of all sessions** (+5.0 pp on
  every slice). Longest continuous all-cash stretch on the proxy goes from
  55 sessions (2008-01→03) to 74 (2009-07→10). Average deployed capital
  62.2% → 59.9% proxy, 67.2% → 64.9% real.
- **Recovery windows.** 120 sessions after each drawdown trough, 0.5 minus
  1/3: −5.9 pp (real, after the 2020 trough), −5.8 pp (proxy 2020), −0.7,
  −0.6, +0.7, +1.3, +1.4. Mean −1.4 pp. This is the known cost of a deeper
  trim: the melt-up off the low pushes the 100/150/200-day gaps through the
  thresholds while the market is still rising.
- **Per year, real daily:** 0.5 wins 7 of 12 (identical in 3). Worst 2020
  −8.2 pp, best 2023 +4.6 pp; then 2021 +4.4, 2025 +2.8, 2017 +0.9, 2019
  +0.8, 2024 +0.6, 2018 +0.2, 2026 −2.6. Sum +3.5 pp. On the proxy: 16 of 27,
  worst 2009 −9.5 pp, best 2023 +6.5 pp, sum +6.9 pp.

## Standing recommendation

Do not apply, and keep the design frozen to 7 December. The reasoning is not
that 0.5 looks bad — it clears the one-session lag test that killed DEEP,
clears the exposure-matched control on both harnesses, keeps every LORO sign
and trades *less*, and its pre-specified permutation is as clean as this
project has produced. The reasoning is that (i) the honest menu permutation
says a gain this size is what searching over four steps produces by chance,
(ii) no bootstrap CI on Sharpe excludes zero, (iii) the ranking is not stable
to a two-point move in the thresholds that feed it, and (iv) it would be the
third design change in one week, on top of the state-D gate and the E row,
neither of which has yet been observed live for a single session. The
+0.29 pp of real CAGR is not worth spending the freeze on.

Candidate count this line: 2 schedules (live 1/3 and the pre-specified 0.5)
+ 2 menu-only steps inside the permutation null; controls, threshold shifts
and alternative A rows are sensitivity, not candidates.
