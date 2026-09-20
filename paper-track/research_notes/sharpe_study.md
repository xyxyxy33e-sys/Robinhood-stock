# Maximize Sharpe (BOXX treated as cash) — 2026-09-20

**Headline: naively maximizing over the knob menu overfits and the holdout
catches it. One single change survives every era on both harnesses with
bootstrap support: state D held as 70% TQQQ / 30% BOXX instead of 100% QLD —
the same ~2.1× beta through a different vehicle. Not applied.**

Script: `paper-track/sharpe_study.py`
Log: `research_notes/sharpe_study_run.log`

## The metric

BOXX is the risk-free leg, so **Sharpe means excess return over the cash leg**.
That matters: a raw Sharpe drifts upward as the book de-levers (real 1.475 →
1.576 at k = 0.50) purely because BOXX pays ~2.3%/yr at 0.17% annualised vol.
Excess Sharpe is flat under scaling (1.376 → 1.378 real, 0.990 → 0.985 proxy),
verified in section 0 of the log. That makes "maximize Sharpe" a well-posed
question and the only quantity whose improvement genuinely moves the frontier —
raise it and you can lever back to any target return carrying less risk.

**LIVE:** real **1.376**; proxy **0.990** (search 1.305, holdout 0.754).

## What a naive maximum does

A one-at-a-time sweep over 46 settings across 9 pre-specified knobs, then every
setting that raises **search-era** Sharpe on **both** harnesses stacked:

| arm | full | search | holdout | CAGR | MaxDD |
|---|---|---|---|---|---|
| proxy LIVE | 0.990 | 1.305 | 0.754 | 25.46% | −27.0% |
| proxy STACK | 0.958 | **1.360** | **0.683** | 26.70% | **−48.5%** |
| real LIVE | 1.376 | 1.376 | — | 37.29% | −18.6% |
| real STACK | 1.441 | 1.441 | — | 40.85% | −19.6% |

The stack wins the search era on both harnesses and **fails the proxy holdout
by −0.071**, with MaxDD blowing out from −27.0% to −48.5%. Re-levered to live's
CAGR its proxy drawdown is −46.3% against live's −27.0% — **19.3 pp worse**.

**Why, and it is worth naming.** The stack switches off the volatility target
(`vol_target = 1.00`) and the gap200 half of the D gate. Turning the vol target
off raises search-era Sharpe on both harnesses (+0.004 proxy, +0.016 real) and
costs **−0.111 on the proxy holdout**, taking proxy MaxDD from −27.0% to
−51.3%. The 2015-11+ search era simply does not contain the event the vol
target exists for. **This is the strongest argument on record for keeping the
vol target**, and it only appears because the holdout exists.

## The survivors

Three single settings are positive in **every** era on **both** harnesses.
Scored individually, with bootstrap and leave-one-regime-out:

### 1. D row = 70% TQQQ / 30% BOXX (instead of 100% QLD) — the real candidate

| harness | Sharpe | Δfull | Δsearch | Δhold | CAGR | ΔCAGR | MaxDD | bootstrap 60d |
|---|---|---|---|---|---|---|---|---|
| real | 1.390 | **+0.014** | +0.014 | — | 38.31% | +1.01 pp | −18.6% | Sharpe **P 0.018**, return **P 0.000** |
| proxy | 1.005 | **+0.015** | +0.021 | +0.010 | 26.22% | +0.76 pp | −27.5% | Sharpe **P 0.000**, return **P 0.000** |

LORO all five windows positive (+0.010 … +0.015). Re-levered to live's CAGR,
MaxDD is better by 0.47 pp real / 0.37 pp proxy at ~5 pp less exposure.

**This clears more bars than anything tested this month**: both proxy eras,
both harnesses, bootstrap under 0.05 on both (0.000 on returns), and every LORO
window. For comparison, the EXTENSION_STEP 0.5 candidate failed the bootstrap
outright at P 0.105–0.179.

**The caution:** there is no clean mechanism. 0.7 × 3× and 1.0 × 2× carry the
same static beta, and volatility drag should actually be *worse* for the TQQQ
version (drag scales with leverage², so 0.7 × 9σ² > 1.0 × 4σ²). The gain is
therefore coming from path and interaction effects — the 30% cash changes how
the drift band fires and how the vol target scales the row — not from something
I can state in one sentence. An edge without a mechanism, found in a 46-cell
menu, is exactly the shape of thing this project has rejected before.

Note also it is **Sharpe-positive but not drawdown-positive**: the same variant
scored +0.00 against the drawdown frontier in `drawdown_study2`. Both are true.

### 2. B row = 100/0 (no TQQQ in state B)

real +0.004 (bootstrap **P 0.320** — nothing); proxy +0.013 full, +0.005 search,
+0.019 holdout, bootstrap P 0.024; LORO all positive. **State B is 0.7% of real
sessions (18 days)**, so the real-harness result is essentially a non-event.
Proxy-only evidence.

### 3. D gate: gap200 half OFF

real +0.004 (bootstrap **P 0.454**); proxy +0.026 full, +0.010 search, +0.037
holdout, bootstrap P 0.245; LORO all positive; re-levered proxy MaxDD better by
2.40 pp. **This proposes undoing half of the state-D gate the owner applied on
2026-09-19.** It fails the bootstrap on both harnesses, so on this evidence it
is a suggestion, not a finding — but it is on the record that the gap200 half
of the gate is Sharpe-negative in both proxy eras.

### All three together

real +0.021 (bootstrap P 0.329); proxy +0.054 full, +0.036 search, +0.067
holdout (bootstrap Sharpe P 0.075, return P 0.019); re-levered MaxDD better by
0.63 pp real and 3.99 pp proxy. LORO all positive.

## The honest caveat

**Menu size: 46 settings across 9 knobs, scored on two harnesses.** Anything
selected as a maximum over a menu that size is inflated, and with 46 draws one
expects a couple of settings to look positive in all eras by chance. No
permutation test over the menu was run here — that is the missing piece before
any of this could be applied, and on past form (the EXTENSION_STEP study) the
honest menu permutation is where candidates die.

## Recommendation

**Apply nothing now.** The design is frozen to 7 December, and three changes
already went in this week that have not been observed live for a single
session.

The D-row candidate is the strongest thing this line has produced and should
be re-run **pre-registered and alone** after the freeze: one hypothesis, the
full battery including a menu permutation, decided once. If it survives that,
it is worth ~+1 pp of real CAGR at unchanged drawdown.

The most valuable output of this study is not a candidate at all. It is the
holdout's rejection of the naive Sharpe maximum, and specifically the
demonstration that **switching off the volatility target looks good in every
part of the data we searched on and is catastrophic in the part we did not.**

Nothing applied. Candidate count this line: 46 settings + 4 combinations.
