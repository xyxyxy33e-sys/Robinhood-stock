# Where to cut max drawdown — Part II, the general question (2026-09-20)

**Answer: there is no structural slack left. The drawdown is leveraged beta on
the days the design is legitimately long. The classifier already converts a
−45% (real) / −87% (proxy) constant-beta drawdown into −18.6% / −27.0% *while
raising* CAGR. Nothing tested — redistributing leverage between states, a
faster classifier, or a bond sleeve — beats flat de-levering.**

Script: `paper-track/drawdown_study2.py`
Log: `research_notes/drawdown_study2_run.log`
Part I (19 knobs): `drawdown_study.md`

Same null throughout: flat de-levering traces a (CAGR, MaxDD) frontier; a lever
must land **above** it. MaxDD is negative, so positive edge = shallower than
the null.

## A. Is it just beta? Mostly yes.

Each episode split into `average effective beta × QQQ move` versus a timing
residual. Leg betas core 1.0 / TQQQ 3.0 / QLD 2.0 / XLU 0.2 / BOXX 0.

| harness | episode | depth | avg beta | QQQ move | beta-implied | residual share |
|---|---|---|---|---|---|---|
| real | 2021-11 → 2023-01 | −18.6% | 0.45 | −30.8% | −13.9% | 25% |
| real | 2025-02 → 2025-03 | −17.8% | 1.61 | −8.1% | −13.1% | 26% |
| real | 2023-09 → 2023-10 | −17.0% | 1.92 | −7.7% | −14.8% | **13%** |
| real | 2018-01 → 2018-02 | −16.5% | 1.71 | −9.0% | −15.4% | **6%** |
| real | 2018-03 → 2018-04 | −16.3% | 1.45 | −9.5% | −13.8% | 15% |
| proxy | 2007-11 → 2009-03 | −25.4% | 0.43 | −47.7% | −20.6% | 19% |
| proxy | 2012-04 → 2012-06 | −19.7% | 1.92 | −8.9% | −17.2% | **13%** |

**Six to 32% of each real drawdown is timing residual; the rest is beta × the
index falling.** There is no hidden execution or selection error to remove.

### And the timing machinery is already doing enormous work

Hold a constant beta to QQQ equal to the design's own average effective beta,
over the same window (first-order, no financing or rebalancing drag — a floor
on what constant leverage costs):

| harness | design avg beta | constant-beta MaxDD | constant-beta CAGR | **the design** |
|---|---|---|---|---|
| proxy | 1.20 | **−86.7%** | 8.89% | **−27.0%, 25.46%** |
| real | 1.31 | **−45.0%** | 23.65% | **−18.6%, 37.29%** |

The classifier turns −86.7% into −27.0% while nearly tripling CAGR. Whatever
slack existed has already been taken.

## B. Which state carries the risk? A, by volume; D, by intensity.

Across **all** sessions, not just the worst episodes:

| regime | % time | avg exposure | % of drawdown loss | % of downside semi-var | loss/day while in DD |
|---|---|---|---|---|---|
| **A** (real) | 68.0% | 78.2% | **72.9%** | 70.3% | −39.6 bp |
| **D** (real) | 10.7% | 91.8% | 22.7% | 27.8% | **−78.4 bp** |
| C | 3.7% | 66.1% | 2.2% | 1.0% | −21.8 bp |
| F | 8.1% | 14.7% | 1.2% | 0.5% | −5.4 bp |
| B | 0.7% | 85.3% | 0.9% | 0.4% | −51.8 bp |
| D-gated / E | 8.8% | 0.0% | 0.2% | 0.0% | −1.9 / −0.1 bp |

Proxy is the same shape (A 70.7% of drawdown loss, D 20.1%). **State A is where
the drawdown is, because it is where the time is. State D is twice as damaging
per day but only a tenth of the calendar.** The cash states (E, F, D-gated)
contribute essentially nothing — they are working.

### Moving leverage between states buys nothing

| variant | real vs frontier | proxy vs frontier |
|---|---|---|
| leverage INTO B (A 65/35, B 55/45) | +0.10 | −2.24 |
| D as TQQQ 70/30 cash (same ~2.1×) | +0.00 | −0.55 |
| all leverage as QLD | −2.45 | −0.37 |
| D as QLD 85/15 cash, A 45/55 | −1.60 | −1.42 |
| leverage INTO A (A 40/60, B 90/10) | −2.22 | −1.49 |
| **leverage OUT of D (D core, A 35/65)** | **−7.03** | **−5.34** |

Nothing clears the frontier on both. "D as TQQQ 70/30 cash" scores exactly
+0.00 / −0.55 — the *same* beta through a different vehicle changes nothing,
which is the cleanest possible confirmation that only the size of the beta
matters. And taking leverage out of D is the worst variant, consistent with the
same-day D-row test (60/40 core/cash scored −7.4 against this frontier).

## C. Is the exit too slow? No — every faster classifier is worse.

The design is often still at beta ~2.0 twenty sessions after a peak (C1 in the
log), which *looks* like the problem. It isn't:

| macro pair | real CAGR | real MaxDD | vs frontier | proxy vs frontier |
|---|---|---|---|---|
| **50/200 (live)** | 37.29% | −18.6% | +0.00 | +0.00 |
| 50/150 | 35.80% | −18.6% | −0.72 | −1.27 |
| 30/200 | 36.30% | −20.7% | −2.66 | −7.80 |
| 40/150 | 33.81% | −20.5% | −3.94 | −9.53 |
| 30/120 | 30.88% | −23.6% | −8.51 | −10.53 |
| 20/100 | 21.03% | −28.7% | −18.67 | −13.11 |

**Every faster pair is worse on both axes at once** — lower CAGR *and* deeper
drawdown. Faster exits whipsaw, and the whipsaw costs more than the early exit
saves. The 50/200 pair is not slow; it is right. (The 50/200 row here is the
classifier recomputed end to end and reproduces LIVE exactly — asserted.)

## D. Does diversification help? Not with bonds.

Carve x% out of the risky legs into a 10-year note proxy (DGS10 carry −
8.5 × Δy, covering the full history):

| sleeve | real CAGR | real MaxDD | vs frontier | proxy vs frontier |
|---|---|---|---|---|
| 10% of risky | 33.38% | −16.8% | −0.43 | −0.54 |
| 20% of risky | 29.54% | −15.5% | −1.19 | −0.91 |
| 30% of risky | 25.68% | −14.2% | −1.74 | −1.33 |

All below the frontier. The reason is visible in the sleeve itself: **the bond
proxy's own MaxDD over the real era is −26.8%, deeper than the strategy's
−18.6%**, at a 0.52% CAGR. Bonds were not a diversifier in the period that
matters — they fell in the same episodes. This is one asset on one proxy, so it
does not close the diversification question in general (gold, managed futures
and explicit convexity are untested, and options cannot be backtested over this
history), but it does close the cheap version of it.

## Conclusion

Four independent angles, one answer. The drawdown is **leveraged beta taken on
days the design is correctly long**; the residual is 6–32%; the classifier has
already removed two-thirds of a constant-beta drawdown while raising return;
the risk is spread across state A in proportion to the time spent there;
moving it around, speeding it up, or diluting it with bonds all lose to simply
holding less.

**The only lever that works is the size of the beta.** From Part I, the price
is ~0.53 pp of MaxDD per 1 pp of CAGR, and de-levering is Sharpe-positive
(1.475 → 1.543 at k = 0.60). If a shallower drawdown is wanted, that is the
route, and it is an owner call on risk appetite against the standing objective
of outperforming SPY and QQQ.

**What remains genuinely untested:** convexity (protective puts / collars),
which buys drawdown reduction by paying premium rather than by cutting
exposure, and non-bond diversifiers. Options cannot be evaluated on this
history with the data available here.

Nothing applied. Candidate count this line: 7 leverage redistributions +
6 classifier pairs + 3 bond sleeves = 16.

*Note on the record: two earlier passes of this script were wrong and were
discarded before any result was reported — `rows['qqq']` is a next-session
return, not a price, which corrupted first the episode beta decomposition and
then the proxy classifier recomputation. The fix is asserted: recomputing the
classifier at 50/200 now reproduces LIVE exactly on both harnesses.*
