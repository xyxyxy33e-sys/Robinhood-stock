# Where can max drawdown be cut? — 2026-09-20

**Answer: nowhere cheaply. Of nineteen levers tested, exactly one beats
"just hold less" on both harnesses, and it beats it by 0.1 pp — noise. If you
want a shallower drawdown, de-lever; that is the efficient frontier, and the
exchange rate is ~0.53 pp of MaxDD per 1 pp of CAGR.**

Script: `paper-track/drawdown_study.py`
Log: `research_notes/drawdown_study_run.log`

## The frame

Every risk reduction reduces drawdown, so "no change" is the wrong null. The
right null is **flat de-levering**: take the live design and multiply all four
risky legs by a constant k every day. That traces a (CAGR, MaxDD) frontier —
the drawdown you can have for free, by doing nothing clever. A lever is only
interesting if it lands **above** that frontier. Every candidate is scored as
`arm MaxDD − frontier MaxDD at the same CAGR`, where **positive = shallower
than the null = the lever is doing real work**.

The simulator reproduces both asserted baselines exactly before anything is
moved (proxy 25.46% / 1.071 / −27.0%, real daily 37.30% / 1.475 / −18.6%).

## 1. Where the drawdown actually comes from

### The deepest episodes

| harness | peak → trough | depth | sessions to trough | to recover | regime mix |
|---|---|---|---|---|---|
| proxy | 2004-12-13 → 2005-10-31 | **−27.0%** | 223 | 267 | A 65%, D 14%, D-gated 12% |
| proxy | 2000-07-14 → 2002-08-28 | −26.7% | 531 | 239 | F 76%, A 14%, C 9% |
| proxy | 2007-11-05 → 2009-03-13 | −25.4% | 340 | 108 | F 77%, C 15%, A 6% |
| proxy | 2021-11-18 → 2023-01-18 | −25.3% | 291 | 77 | F 60%, C 32%, A 9% |
| real | 2021-11-18 → 2023-01-17 | **−18.6%** | 290 | 70 | F 60%, C 31%, A 9% |
| real | 2025-02-18 → 2025-03-03 | −17.8% | **9** | 84 | D 60%, D-gated 40% |
| real | 2023-09-13 → 2023-10-26 | −17.0% | 31 | 12 | D 56%, A 38% |
| real | 2018-03-09 → 2018-04-05 | −16.3% | 18 | 67 | D 90%, D-gated 10% |

### Attribution inside the three worst, by regime and by leg

| episode | by regime | by leg | avg exposure |
|---|---|---|---|
| proxy 2004-12 → 2005-10, −27.0% | **D −30.0 pp (48 days)**, A −5.6 (92d), C +4.0 (9d) | **QLD −28.3 pp**, TQQQ −4.4, core +5.1 | 70.2% (design 62.2%) |
| proxy 2000-07 → 2002-08, −26.7% | **A −27.4 pp (64 days)**, C −1.1 (69d), F +1.4 (374d) | **TQQQ −21.1 pp**, core −10.9, BOXX +6.4 | **15.6%** |
| proxy 2007-11 → 2009-03, −25.4% | (see log) | | |
| real 2021-11 → 2023-01, −18.6% | **A −16.5 pp (43 days)**, C −6.5 (59d), F +3.2 (150d) | **TQQQ −13.4 pp**, core −5.5 | **31.9%** |
| real 2025-02 → 2025-03, −17.8% | D −9.7 (3 days), A −9.7 (5 days) | **QLD −9.3, TQQQ −7.5** | 80.0% |
| real 2023-09 → 2023-10, −17.0% | A −10.3 (11d), D −6.7 (20d) | TQQQ −7.7, QLD −5.9 | 95.8% |

**Three facts fall out, and they are the whole story:**

1. **It is always the leveraged legs.** TQQQ or QLD accounts for the entire
   loss in every episode; the unlevered core and BOXX are near zero or
   positive. There is no "the strategy was in the wrong asset" problem to fix
   — it is in a 2x or 3x asset, and that asset falls.

2. **In the long bears, the design is already mostly in cash — and the damage
   is done on the few days it isn't.** Through the 2000–2002 episode average
   exposure was **15.6%** (374 of 531 sessions in state F), and through the
   2021–2023 episode **31.9%** (150 sessions in F). The classifier worked.
   The drawdown is the residual risk-on days, not a failure to de-risk.

3. **The fastest episodes are the ones no slow lever can catch.** The second
   worst real drawdown is **−17.8% in nine sessions** at 80% exposure. A
   30-day vol target cannot move in nine sessions, and a NAV brake triggers
   after most of the fall. Anything that reacts to realised loss arrives late
   by construction.

## 2. The null: what de-levering buys

Real daily, all four risky legs × k every day:

| k | CAGR | Sharpe | MaxDD | exposure | pp DD per pp CAGR |
|---|---|---|---|---|---|
| 1.00 (live) | 37.29% | 1.475 | −18.6% | 67.2% | — |
| 0.95 | 35.47% | 1.480 | −17.7% | 63.9% | 0.48 |
| 0.90 | 33.65% | 1.485 | −16.5% | 60.5% | 0.57 |
| 0.85 | 31.83% | 1.491 | −15.5% | 57.2% | 0.55 |
| 0.80 | 30.02% | 1.498 | −14.6% | 53.9% | 0.54 |
| 0.75 | 28.28% | 1.508 | −13.6% | 50.5% | 0.55 |
| 0.70 | 26.45% | 1.517 | −12.8% | 47.2% | 0.53 |
| 0.60 | 22.96% | 1.543 | −11.0% | 40.5% | 0.53 |

The exchange rate is **strikingly stable at ~0.53 pp of drawdown per 1 pp of
CAGR** across the whole range, and **Sharpe rises slightly as k falls**
(1.475 → 1.543). De-levering is not merely the null — it is Sharpe-neutral to
Sharpe-positive. That is a high bar for anything cleverer to clear.

## 3. Nineteen levers, scored against the frontier

Positive = shallower than de-levering to the same CAGR.

| lever | real vs frontier | proxy vs frontier | beats null on both? |
|---|---|---|---|
| drift band 3% | +0.11 | +0.07 | **YES** |
| drift band 2% | +0.13 | +0.04 | (proxy inside noise) |
| B row 100/0 | +0.00 | +0.21 | |
| B row 85/15 | −0.00 | +0.12 | |
| vol target 18% | +0.61 | −1.07 | |
| TQQQ capped at 40% | +0.47 | −1.44 | |
| vol target 14% | +0.43 | −4.64 | |
| vol target 16% | −0.00 | −2.78 | |
| D gate breadth 0.30 | −0.25 | −0.85 | |
| TQQQ capped at 25% | −0.23 | −3.15 | |
| D-row vol target 15% | −1.25 | −1.96 | |
| TQQQ capped at 0% (no 3x) | −1.14 | −4.94 | |
| vol target 12% | −1.86 | −4.47 | |
| D-row vol target 12% | −2.61 | −3.06 | |
| NAV brake −5% → ×0.5 | −2.65 | +0.51 | |
| NAV brake −15% → ×0.5 | −2.42 | −3.93 | |
| NAV brake −10% → cash | −3.34 | +0.56 | |
| NAV brake −10% → ×0.5 | −7.35 | −2.63 | |
| NAV brake −15% → cash | −9.06 | −4.64 | |
| D gate 0.30 AND gap 5% | −12.02 | −9.58 | |
| D gate gap200 5% | **−15.74** | **−12.05** | |

**Only `drift band 3%` is positive on both, at +0.11 / +0.07 pp — noise.**

Three families are worth naming because they fail in instructive ways:

- **Widening the D gate is the worst thing tested.** Gating D on gap200 < 5%
  takes real CAGR from 37.29% to 30.10% and makes MaxDD **deeper**, −18.6% →
  −30.4%. A wider gate sells *after* the fall and sits out the recovery; it
  converts a drawdown into a permanent one. (Consistent with the 2026-09-20
  D-row test, where 60/40 core/cash scored −7.4 pp against this same frontier.)

- **NAV brakes are structurally late.** Every variant loses to the null on at
  least one harness, most on both. `−10% → cash` takes real CAGR to **3.55%**
  for a 6 pp shallower drawdown. They sell into the hole and miss the bounce —
  the same mechanism that made the extension trim's recovery windows expensive.

- **Vol-target and leverage-cap changes essentially *are* the frontier.** They
  sit within ±0.6 pp of it on real and below it on the proxy. That is the
  expected result: turning the vol target down is de-levering, just
  state-contingent, and the state-contingency adds nothing.

## 4. What this means

There is no free drawdown reduction in this design. The classifier is already
doing the work — in the long bears it is 60–77% in cash — and what is left is
irreducible: leveraged exposure on the risk-on days, including fast ones no
reactive rule can catch.

**If less drawdown is wanted, de-lever, and price it honestly.** The menu is
the table in section 2. Representative points on the real harness:

| target | k | CAGR | MaxDD | Sharpe |
|---|---|---|---|---|
| live | 1.00 | 37.29% | −18.6% | 1.475 |
| ~15% DD | 0.85 | 31.83% | −15.5% | 1.491 |
| ~13% DD | 0.75 | 28.28% | −13.6% | 1.508 |
| ~11% DD | 0.60 | 22.96% | −11.0% | 1.543 |

**The tension to state plainly:** the standing objective is to outperform SPY
and QQQ. De-levering cuts drawdown at a fair price in Sharpe terms but
directly reduces expected outperformance, which is the thing the account
exists to produce. That is an owner call about risk appetite, not a research
finding — research says only that the price is fair and no cheaper route
exists.

Nothing applied. Candidate count this line: 19 levers + 9 frontier points
(controls, not candidates).
