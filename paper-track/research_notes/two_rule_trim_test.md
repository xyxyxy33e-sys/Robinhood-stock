# Step 0.5 with only the 10% and 15% rules — 2026-09-20

**Verdict: NOT applied, and it is not a way to get step 0.5 safely. The
arithmetic works — no clip is needed — but the 150d rule is where the
step-0.5 gain actually lives, and dropping it gives essentially all of it
back.**

Script: `paper-track/two_rule_trim_test.py`
Log: `research_notes/two_rule_trim_test_run.log`

## The question, and why it was a good one

The 1/3-vs-0.5 study earlier the same day found that `extension_scale()` is
`1 − STEP × votes` with **no clip at zero**: with three rules and step 0.5,
three votes gives −0.500, `validate_weights` raises, and the live trigger
aborts instead of trading the intended all-cash row. Owner asked whether
using only two rules — 100d > 10% and 200d > 15% — sidesteps that.

**It does, exactly.** Verified against the live code:

| | max votes | scale at max votes | |
|---|---|---|---|
| 3 rules, step 0.5 | 3 | 1 − 0.5×3 = **−0.5000** | negative → trigger aborts |
| **2 rules, step 0.5** | 2 | 1 − 0.5×2 = **+0.0000** | all-cash row, **no clip needed** |
| 3 rules, step 1/3 (live) | 3 | 1 − 0.3333×3 = +0.0000 | all-cash row, no clip needed |

Setting `EXTENSION_RULES = ((100, 0.10), (200, 0.15))` and `EXTENSION_STEP =
0.5` requires **no code change**. That is the same arithmetic that makes the
live step safe today. The question was structurally right.

## The arms

A row (SPMO, TQQQ, cash) by vote count; the vol target multiplies on top.

| arm | rules | rows |
|---|---|---|
| LIVE | 100/10, 150/12, 200/15 | (50,50,0) / (33,33,33) / (17,17,67) / (0,0,100) |
| C3 | same three | (50,50,0) / (25,25,50) / (0,0,100) / (0,0,100) |
| **C2** | **100/10, 200/15** | **(50,50,0) / (25,25,50) / (0,0,100)** |
| T2 | 100/10, 200/15 | (50,50,0) / (33,33,33) / (17,17,67) |

T2 is the decomposition arm: it changes the rules and holds the step at 1/3,
so C2 = LIVE + (rule change) + (step change) can be split.

## Headline

| arm | proxy full | S | H | exp | reb | real daily | exp | reb |
|---|---|---|---|---|---|---|---|---|
| LIVE | 25.46% / 1.071 / −27.0% | 1.399 | 0.825 | 62.2% | 47.9 | 37.30% / 1.475 / −18.6% | 67.2% | 45.3 |
| C3 | 25.78% / 1.094 / −26.6% | 1.424 | 0.846 | 59.9% | 44.8 | 37.60% / 1.501 / −18.4% | 64.9% | 44.8 |
| **C2** | 25.69% / 1.074 / −26.6% | 1.399 | 0.830 | 62.8% | 44.3 | **37.36% / 1.467 / −19.0%** | 68.0% | 40.6 |
| T2 | 24.96% / 1.031 / −27.1% | 1.347 | 0.794 | 65.9% | 45.2 | 36.76% / 1.419 / −19.0% | 71.7% | 41.7 |

Deltas vs LIVE, real daily: C3 **+0.29 pp CAGR, +0.026 Sharpe, 0.2 pp
shallower**; C2 **+0.06 pp CAGR, −0.007 Sharpe, 0.5 pp deeper**; T2 −0.54 pp,
−0.056, 0.5 pp deeper.

**C2 minus C3 is −0.033 real Sharpe, −0.24 pp real CAGR.** Dropping the 150d
rule costs more than moving the step from 1/3 to 0.5 gains.

## Why: the two-rule set trims *less*, not more

This is the part that makes the idea fail. The intuition is that step 0.5
with two rules is "the deeper trim, made safe". It is not — it is a
**shallower design** that happens to use a deeper rung.

| ruleset | A days | 0 votes | 1 | 2 | 3 | ≥1 vote |
|---|---|---|---|---|---|---|
| 3 rules (live), real | 1854 | 1377 | 137 | 136 | 204 | 25.7% |
| 2 rules 10/15, real | 1854 | 1427 | 219 | 208 | — | 23.0% |

Fewer A days get trimmed at all (23.0% vs 25.7%), and the deeper rung does
not make that up. **Average deployed capital rises to 68.0% real, above
live's 67.2%**, where C3 falls to 64.9%. Time with a fully-cash target is
24.6% of real sessions for C2 against live's 24.4% and C3's 29.4% — C2 is,
in exposure terms, live with a slightly different shape, not a more
defensive design.

The mechanism is specific: a day where only the 150d gap fires is 1 vote
under live (half-trim) and **0 votes** under the two-rule set (full risk);
a day where 150d and one other fire is 2 votes under C3 (full cash) and 1
vote under C2 (half). C2 is uniformly less aggressive than C3, and in places
less aggressive than live.

## Battery

| # | test | C3 (3 rules, 0.5) | **C2 (2 rules, 0.5)** |
|---|---|---|---|
| 1 | both-era Sharpe up | +0.026 / +0.021 **PASS** | +0.000 / +0.005 **PASS (on a rounding edge)** |
| 2 | beats exposure-matched control | proxy +0.020, real +0.023 **PASS** | proxy +0.004, **real −0.007 FAIL** |
| 3 | block bootstrap P(≤0) < 0.05 | 0.086–0.165 FAIL | **0.41–0.66 FAIL badly** |
| 4 | permutation | pre-specified p 0.000, menu 0.93 | see below |
| 5 | real CAGR not falling | +0.29 pp PASS | +0.06 pp PASS |
| 6 | **one-session execution lag** | search +0.003, real +0.000 **PASS** | **search −0.031, real −0.032 FAIL** |
| 7 | 20 bp one-way cost | +0.009 real Sharpe PASS | +0.002 Sharpe, **+0.28 pp CAGR PASS** |
| 8 | LORO across five regimes | +0.020 … +0.029 PASS | −0.003 … +0.007, **sign flips** |

Two of these deserve naming.

**The execution lag is decisive.** This is the test that killed the DEEP
schedule (search −0.031, real −0.040) and that C3 survived. C2 fails it at
**search −0.031, real −0.032** — DEEP's failure level exactly. A shape whose
advantage evaporates when the vote is read one session late is reading the
same close it trades on.

**LORO flips sign.** C3 kept a positive sign in all five dropped windows.
C2 is −0.003 with the dot-com years removed and +0.007 at best. There is no
regime-robust edge to keep.

## Per year, real daily

| year | LIVE | C3 | **C2** | C3−L | **C2−L** |
|---|---|---|---|---|---|
| 2017 | 70.6 | 71.4 | 68.8 | +0.9 | −1.7 |
| 2018 | 11.2 | 11.4 | 12.3 | +0.2 | +1.1 |
| 2019 | 44.2 | 45.1 | 45.1 | +0.8 | +0.8 |
| 2020 | 60.9 | 52.7 | 59.2 | −8.2 | −1.6 |
| 2021 | 45.9 | 50.3 | 41.4 | +4.4 | **−4.5** |
| 2023 | 60.0 | 64.6 | 65.6 | +4.6 | **+5.6** |
| 2024 | 61.9 | 62.5 | 61.9 | +0.6 | −0.0 |
| 2025 | 37.6 | 40.3 | 39.3 | +2.8 | +1.8 |
| 2026 | 38.6 | 36.0 | 37.7 | −2.6 | −0.8 |

2015 / 2016 / 2022 are identical under all arms (no vote days). C2 beats live
in **4 of 12 years**, sum **+0.6 pp** over eleven years — against C3's 7 of 12
and +3.5 pp. C2's one real win is 2023 (+5.6 pp, better than C3's +4.6) and
it is paid for by 2021 (−4.5). It does cushion 2020 relative to C3 (−1.6 vs
−8.2), which is the honest point in its favour.

## Sensitivity

**Thresholds** shifted together: C2 never gets a clean win. Real delta is
negative at every one of the five shifts (−0.007 at the live setting, −0.026
at +2 pp), and the proxy search and holdout disagree in sign at four of five.
C3, by comparison, was at least ahead at 0 and +1 pp.

**A row** (40/60, 50/50, 60/40): C2 is −0.006 / −0.007 / −0.008 real at the
three rows — stably, mildly negative. C3 is +0.024 to +0.028 at all three.

## The permutation, and a caveat about it

Stage 7's null shuffles each rule set's labels **independently**, which
decorrelates an arm from its base and widens the null (95th +0.155, against
the +0.074 the three-rule-only study saw). Stage 7b repeats it **paired** —
one random day map applied to every rule set — which is the construction the
earlier study used. Both are in the log; the paired one is the one to read.

The sixteen-cell grid on the real labels (full-period dSharpe / both-era min):

| ruleset | 0.25 | 1/3 | 0.5 | 1.0 |
|---|---|---|---|---|
| 3 rules (live) | −0.030 / −0.037 | 0 / 0 | **+0.023 / +0.021** | +0.032 / +0.019 |
| 2 rules 10/15 | −0.067 / −0.089 | −0.039 / −0.052 | **+0.003 / +0.000** | +0.049 / +0.046 |
| 2 rules 10/12 | −0.064 / −0.104 | −0.036 / −0.073 | +0.004 / −0.036 | +0.055 / +0.021 |
| 2 rules 12/15 | −0.078 / −0.080 | −0.055 / −0.069 | −0.025 / −0.055 | −0.051 / −0.069 |

Every two-rule cell at step 1/3 or below is **worse** than live. The only
two-rule cells that beat live are at step 1.0 — all-cash at a single vote —
which is the corner the 2026-09-06 note explicitly warned against taking on
the strength of trim-depth monotonicity.

## Recommendation

Do not adopt. The arithmetic insight is worth keeping on the record — if
step 0.5 is ever wanted, a two-rule set is one of exactly two ways to get it
without touching `state.py`, the other being the one-line clip — but the
version that earns the step-0.5 gain is the three-rule one, and that one
needs the clip. The two-rule version trades away the gain to avoid a one-line
change, fails the execution-lag test at DEEP's level, does not beat its own
exposure-matched control on real instruments, and flips sign under LORO.

The standing recommendation from the step study is unchanged: keep the design
frozen to 7 December.

Candidate count this line: 3 arms (C2 pre-specified, C3 already counted, T2
decomposition) + 12 menu-only cells inside the permutation null; controls,
threshold shifts and alternative A rows are sensitivity, not candidates.
