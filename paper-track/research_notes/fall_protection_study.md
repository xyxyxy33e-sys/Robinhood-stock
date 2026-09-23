# Protection during the fall, inside state A — 2026-09-22/23.

> **APPLIED 2026-09-23 by owner decision** (freeze removed): extension trim v2 —
> TQQQ out at the first held vote, core ⅙ per vote, held votes step down one per
> new 15-session closing high and never below the raw count, reset outside A;
> A base 30/70 for A spells starting on/after 2026-09-23 (the spell in progress
> keeps 50/50). `state.py` "EXTENSION TRIM v2"; STRATEGY.md Part I. Standing
> figures: 50/50 real 39.32% / 1.717 / −17.8%, proxy 25.41% / 1.161 / −21.9%
> (S 1.619, H 0.829); 30/70 real 45.05% / 1.711 / −19.6%, proxy 28.50% / 1.162 /
> −24.7% (S 1.631, H 0.824). The sections below are the research as written,
> including their "not applied" verdicts at the time.

Owner: *"consider how we can add protection during the fall"*, after
`a_ratio_study.md` §6 showed the extension trim is off on 19 of the 20 worst A
days. Scripts `paper-track/fall_protection_study.py` (12 pre-registered arms),
`paper-track/fall_protection_r2.py` (robustness). Logs alongside. The hook
reproduces `drawdown_study.sim` exactly (asserted). Null = flat de-levering of
live; **edge** = MaxDD minus the null's MaxDD at the same CAGR (+ = shallower
than just holding less). Scope: effective state A only.

Not re-run (already negative on this record): NAV brakes, a faster macro
classifier, wider D gates, a faster vol estimator, VIX/VXN/VRP, fast-state pair
cells, bond sleeves, gap-band trim hysteresis.

## The flaw, in one week — February 2018 (real)

| date | live votes | live book | QQQ-driven day, live | memory-20 book |
|---|---|---|---|---|
| 25–29 Jan | 1→3 | trimmed toward cash | — | 100% cash |
| 1 Feb | **0** | **back to 50/50** | −3.77% | cash, 0.00% |
| 2 Feb | 0 | 50/50 | **−8.10%** | cash |
| 6 Feb | 0 | 50/50 | −1.62% | cash |
| 7 Feb | 0 | 50/50 | **−8.22%** | cash |

The trim votes on *distance above the averages*. When an extended market
breaks, the distance shrinks, the votes fall away and **the live design
re-levers into the fall** — from cash to full 50/50 within a week. Month:
live −6.1%, memory arm +14.3% (both caught the same D-state rebound days).

## Results (12 arms)

| arm | real CAGR / MaxDD | real edge | real ΔSharpe | proxy CAGR / MaxDD | proxy edge | proxy ΔSharpe F / S / **H** |
|---|---|---|---|---|---|---|
| live | 37.29% / −18.6% | — | — | 25.46% / −27.0% | — | — |
| **trim memory 20d** | 38.70% / −17.8% | **+1.53** | **+0.195** | 24.66% / −23.9% | **+2.07** | +0.043 / +0.186 / **−0.052** |
| **trim memory 40d** | 38.70% / −17.7% | **+1.63** | **+0.251** | 24.57% / −23.9% | **+1.96** | +0.057 / +0.226 / **−0.047** |
| trim memory 10d | 38.45% / −17.8% | +1.40 | +0.146 | 24.32% / −27.0% | −1.39 | +0.015 / +0.143 / −0.075 |
| trim memory 5d | 34.59% / −18.3% | −1.20 | −0.020 | 23.27% / −26.6% | −2.13 | −0.040 |
| QQQ 4% off 20d high → TQQQ to core | 38.46% / −21.4% | −2.21 | +0.075 | 25.31% / −27.6% | −0.77 | +0.016 |
| QQQ 6% off 20d high → TQQQ to core | 37.79% / −18.6% | +0.26 | +0.025 | 25.42% / −27.0% | −0.05 | +0.004 |
| QQQ 8% off 20d high (either) | ≈ live | ≈0 | ≈0 | ≈ live | ≈0 | ≈0 |
| QQQ < 10d SMA → TQQQ to core | 32.96% / −17.8% | −1.64 | +0.003 | 20.98% / −25.2% | −3.25 | −0.066 |

(HALF variants of the short-drawdown and 10d-SMA arms sit between; full table
in the log.)

- **Short-drawdown triggers and the 10d SMA are the null or worse.** 4% off the
  high whipsaws in the 2021–23 bear (−21.4% vs −18.6%); 10d SMA is plain
  de-levering bought at a bad price (edge −1.6 real, −3.3 proxy). Rejected.
- **Trim memory is the first lever in the project to beat flat de-levering by a
  material amount on BOTH harnesses** (previous best: +0.1 pp). It is smooth in
  N: edge +1.4 to +1.7 real and +1.3 to +2.3 proxy for every N from 15 to 40.
  It rebalances *less* (29–34/yr vs 45).
- Worst live episodes, memory-20 vs live: real 2021–23 bear −15.5 vs −18.6,
  Sep–Oct 2023 −14.7 vs −17.0, COVID −0.1 vs −5.5; proxy 2005 −23.2 vs −27.0,
  dot-com −23.9 vs −26.7, GFC −21.2 vs −25.4, 2021–23 −22.7 vs −25.3.
  Feb–Mar 2025 (−17.8) and Q4 2018 (−15.0) unchanged — those falls did not
  start from an extended market.

## Why it is not applied

1. **It fails the 2000–2015 holdout on return and Sharpe.** Proxy holdout:
   live 17.84% / −27.0% / 0.754, memory-20 15.52% / −23.9% / 0.702 (−2.3 pp CAGR,
   −0.052 Sharpe). Both halves of the holdout are worse (2000–07 and 2008–15).
   The drawdown gain survives out of sample; the return does not.
2. **It is a handful of events.** Real calendar-year differences (memory-20
   minus live): 2018 **+29.6**, 2021 **+33.3**, 2020 **−18.4**, 2024 **−14.9**,
   2025 −7.3, **2026 −12.0**; everything else within ±2.3. Better in 5 years,
   worse in 4. Its cost is sitting in cash through extended melt-ups that keep
   going, and **the three most recent years are all losers** — directly
   against the objective of outperforming SPY and QQQ.
3. **Bootstrap is short of significance**: real P(not better) 0.10 (20d) /
   0.06 (40d); proxy 0.28 / 0.22.
4. Design frozen to 7 December.

## What it tells us

The drawdown is not only "the fall is uncatchable". Part of it is
**self-inflicted re-levering**: the trim's own release rule puts leverage back
on as an extended market breaks. That mechanism is real, visible day by day,
and fixable in principle. The fixed-N memory fixes it and pays for it in
melt-ups. A release rule that only lets the trim come off when the market is
**not falling** (e.g. release votes only on a close above the 10-day SMA or at
a new 20-day high) targets the flaw directly without a fixed calendar hold. It
is **not tested here** — it would be a thirteenth arm chosen after seeing these
results, and must be pre-registered and judged on the holdout like everything
else.

Candidates this line: 12 (+ 7 N-values for smoothness), none adopted.

## Follow-up: "what if we keep the trim til exit A" (owner, same day)

`paper-track/fall_protection_r3.py`, log `fall_protection_r3_run.log`. **Latch:**
inside effective A the vote count can only rise; it resets when the book leaves
A (or goes to cash via the D gate / E). No parameter to choose.

| | real CAGR / MaxDD / edge / ΔSharpe | proxy CAGR / MaxDD / edge | proxy ΔSharpe F / S / **H** |
|---|---|---|---|
| live | 37.29% / −18.6% / — / — | 25.46% / −27.0% / — | — |
| **latch until exit A** | 37.64% / −17.8% / **+0.98** / **+0.139** | 24.80% / −23.9% / **+2.23** | +0.043 / +0.129 / **−0.014** |
| memory 20d | 38.70% / −17.8% / +1.53 / +0.195 | 24.66% / −23.9% / +2.07 | +0.043 / +0.186 / −0.052 |
| memory 40d | 38.70% / −17.7% / +1.63 / +0.251 | 24.57% / −23.9% / +1.96 | +0.057 / +0.226 / −0.047 |

- **Same protection, better out of sample.** Every worst episode improves exactly
  as with memory (real 2021–23 −15.5 vs −18.6, COVID −0.1 vs −5.5; proxy 2005
  −23.2 vs −27.0, dot-com −23.9 vs −26.7, GFC −21.2 vs −25.4). Best proxy edge
  of the family (+2.23). Holdout Sharpe −0.014 (memory: −0.05); 2008–15 half is
  slightly **better** than live (1.068 vs 1.059); 2000–07 half worse (0.361 vs
  0.416). Holdout CAGR still −1.4 pp (16.46% vs 17.84%).
- **It costs in persistent melt-ups, and recently.** Real years latch minus
  live: 2018 +19.6, 2021 +19.4, 2020 −14.4, **2024 −10.4, 2025 −6.5, 2026
  −12.2**; better 5, worse 4. Proxy better 14, worse 8.
- Trim-on A days rise 477 → 708 (real); exposure 67.2% → 60.7%; rebalances
  45 → 30/yr.
- Bootstrap: real P(not better) 0.12, proxy 0.23. Not significant.
- **Today it would change nothing**: the current A spell began after the last
  vote (10 Jul), so the latch is at 0.

**Verdict: the cleanest version of the fix — parameter-free, near-neutral
holdout Sharpe, the largest both-harness drawdown edge on record — but it does
not meet the both-era bar (holdout CAGR −1.4 pp, Sharpe −0.014), the bootstrap
is not significant, and it would have cost 29 pp across 2024–26.** An owner
call on risk appetite, not a research pass. Frozen to 7 December regardless.

## Follow-up 2: release rules (owner: "also try this, why not")

`paper-track/fall_protection_r4.py`, log `fall_protection_r4_run.log`. Votes rise
at once but may only **fall** on a close that passes a release test; reset on
exit from A. Specified in the owner's words before running (post-hoc relative to
the first study — stated).

| arm | real CAGR / MaxDD / edge / ΔSh | proxy CAGR / MaxDD / edge | proxy holdout CAGR / Sharpe |
|---|---|---|---|
| live | 37.29% / −18.6% / — / — | 25.46% / −27.0% / — | 17.84% / 0.754 |
| release on close > 10d SMA | 35.48% / −18.6% / **−0.88** / −0.005 | 23.70% / −27.5% / **−2.61** | 15.87% / 0.696 |
| release on new 20d high | 37.90% / −17.8% / +1.11 / +0.137 | 24.54% / −23.9% / +1.93 | 15.83% / 0.710 |
| **latch until exit A** | 37.64% / −17.8% / +0.98 / +0.139 | 24.80% / −23.9% / **+2.23** | **16.46% / 0.740** |
| memory 20d | 38.70% / −17.8% / +1.53 / +0.195 | 24.66% / −23.9% / +2.07 | 15.52% / 0.702 |

- **Release above the 10d SMA is wrong in both directions.** In a real fall
  the first bounce above the 10-day releases the votes and re-levers into the
  bear rally (2021–23 bear unchanged at −18.6%); in a bull run a shallow dip
  below the 10-day holds the trim and misses the rebound (2024 −15.4, 2026
  −16.1 pp). Worst of the family on every axis. Rejected.
- **Release at a new 20-day high ≈ the latch.** A falling market rarely makes a
  new 20-day high before it leaves A, so it holds the trim through the same
  episodes (identical worst-episode depths). It releases a little earlier in
  melt-ups (+0.26 pp real CAGR vs the latch) but gives back more in the holdout
  (Sharpe −0.044 vs −0.014). Bootstrap P 0.13 / 0.33.
- **The latch remains the best of the family out of sample.** Nothing in this
  round changes the verdict above: not applied, owner call after the freeze.

## Follow-up 3: release vs volatility (owner: "what about release vs volatility")

`paper-track/fall_protection_r5.py`, log `fall_protection_r5_run.log`. Votes rise
at once; they may only fall when volatility is calm. Two arms, no new numbers:
10-day QQQ vol below the live 30-day estimate (vol not expanding), and 10-day
vol below the 20% vol target.

| arm | real CAGR / MaxDD / edge / ΔSh | proxy CAGR / MaxDD / edge | proxy holdout CAGR / Sharpe |
|---|---|---|---|
| live | 37.29% / −18.6% / — / — | 25.46% / −27.0% / — | 17.84% / 0.754 |
| release: 10d vol < 30d vol | 34.95% / −18.5% / **−1.20** / −0.026 | 24.00% / −27.2% / **−1.92** | 16.72% / 0.731 |
| release: 10d vol < 20% | 35.78% / −18.6% / **−0.73** / −0.018 | 24.01% / −27.0% / **−1.69** | 16.44% / 0.713 |
| latch until exit A | 37.64% / −17.8% / +0.98 / +0.139 | 24.80% / −23.9% / +2.23 | 16.46% / 0.740 |

- **Both are worse than simply holding less, on both harnesses.** They cost
  1.5–2.3 pp CAGR and do not touch the 2021–23 bear (−18.5 / −18.6 vs −18.6).
- **Why: volatility lags the break.** The falls that matter here start from
  a calm, extended market — the Nov 2021 top and the Jan 2022 roll-over began
  with 10-day vol still low, so the votes released and the book re-levered
  exactly as live does. Volatility only catches the fast, violent breaks
  (Feb 2018: +14.1 pp for the 10d<30d arm), which the 30-day vol target and the
  classifier partly handle already. Meanwhile brief vol pops inside melt-ups
  hold the trim and miss the rebound (2026 −15.6 / −10.8 pp).
- Rejected. **Price-based holding (latch, new 20d high) beats vol-based release
  because the dangerous falls begin quietly.** The latch remains the best of
  the family.

## Follow-up 4: trim shape — cut TQQQ only, or at different rates (owner)

`paper-track/fall_protection_r6.py`, log `fall_protection_r6_run.log`. Five
schedules (SPMO / TQQQ / cash at 0/1/2/3 votes), each under the live release and
the latch; proportional + live release asserted identical to live.

| shape | 1 vote | 2 votes | 3 votes |
|---|---|---|---|
| proportional (live) | 33/33/33 | 17/17/67 | 0/0/100 |
| TQQQ only → cash | 50/33/17 | 50/17/33 | 50/0/50 |
| TQQQ only → SPMO | 67/33/0 | 83/17/0 | 100/0/0 |
| TQQQ first, then SPMO | 50/25/25 | 50/0/50 | 0/0/100 |
| asymmetric (TQQQ ½, SPMO ⅙ per vote) | 42/25/33 | 33/0/67 | 25/0/75 |

| release / shape | real CAGR / MaxDD / edge / ΔSh | proxy CAGR / MaxDD / edge | proxy ΔSh F / S / H | holdout CAGR |
|---|---|---|---|---|
| live / proportional | 37.29% / −18.6% / — / — | 25.46% / −27.0% / — | — | 17.84% |
| live / TQQQ only → cash | 37.26% / −18.5% / +0.03 / −0.019 | 25.14% / −27.4% / −0.80 | −0.023 / −0.027 / −0.020 | 17.50% |
| live / TQQQ only → SPMO | 36.78% / −18.5% / −0.19 / −0.065 | 24.45% / −28.6% / −2.89 | −0.063 / −0.080 / −0.053 | 16.90% |
| live / TQQQ first | 37.53% / −18.3% / +0.39 / +0.013 | 25.62% / −26.8% / +0.39 | +0.009 / +0.011 / +0.008 | 17.97% |
| **live / asymmetric** | **37.65% / −18.3% / +0.43 / +0.020** | **25.63% / −26.6% / +0.57** | **+0.012 / +0.013 / +0.010** | **17.98%** |
| latch / proportional | 37.64% / −17.8% / +0.98 / +0.139 | 24.80% / −23.9% / +2.23 | +0.043 / +0.129 / −0.014 | 16.46% |
| latch / TQQQ only → cash | 37.81% / −17.8% / +1.07 / +0.108 | 24.66% / −24.7% / +1.34 | +0.018 / +0.079 / −0.023 | 16.52% |
| latch / TQQQ only → SPMO | 37.71% / −17.8% / +1.02 / +0.037 | 24.30% / −26.1% / −0.53 | −0.029 / −0.003 / −0.048 | 16.38% |
| latch / TQQQ first | 37.20% / −17.8% / +0.76 / +0.137 | 24.82% / −23.6% / +2.59 | +0.049 / +0.136 / −0.008 | 16.55% |
| **latch / asymmetric** | 37.21% / −17.8% / +0.76 / +0.139 | 24.80% / **−23.3% / +2.74** | +0.045 / +0.118 / **−0.002** | 16.68% |

- **Cutting only TQQQ is worse than cutting both.** Keeping SPMO whole leaves
  the book holding its most market-sensitive non-levered leg through exactly the
  days the trim fires, when the core does not earn (see
  `trim_destination_test.md`). To SPMO is clearly worse (proxy edge −2.89,
  holdout −0.053), confirming the 20 Sep result. To cash is roughly neutral on
  real and worse on proxy.
- **Cutting TQQQ faster but still ending mostly in cash is the best shape.**
  Under the *live* release the asymmetric schedule improves **every** point
  estimate in **both** eras: real CAGR +0.35 pp, MaxDD −18.3%, Sharpe +0.020;
  proxy CAGR +0.17 pp, MaxDD −26.6%, Sharpe +0.012 full / +0.013 search /
  +0.010 holdout; holdout CAGR +0.14 pp. It does not change recent years
  materially (2024 +0.8, 2025 +0.1, 2026 −2.6 pp). But it is small — the size
  of the 0.013 "inside noise" band — and the bootstrap is P 0.17 real / 0.15
  proxy. TQQQ-first is the same story, a little smaller (proxy P 0.03, real 0.23).
- **Latch + asymmetric is the best drawdown result on record**: proxy −23.3%
  (edge +2.74), dot-com −23.3, GFC −20.8, 2005 −21.9; holdout Sharpe
  −0.002 (neutral). It still gives up 1.2 pp of holdout CAGR and the recent
  years (2025 −13.5, 2026 −12.9 pp).

**Verdict.** Two separable ideas, neither applied (frozen to 7 December):
(1) **shape** — trim TQQQ faster than SPMO, to cash — is a small, consistent,
both-era improvement that costs nothing measurable, but is not statistically
distinguishable from live; (2) **release** — the latch — buys the largest
drawdown reduction on record, near-neutral holdout Sharpe, at ~1.2 pp of
holdout CAGR and painful recent years. Nine arms this round.

## Follow-up 5: vote vs de-leverage (owner: "think as vote vs deleverage")

`paper-track/fall_protection_r7.py`, log `fall_protection_r7_run.log`. A trim
schedule mixes two things: **how much leverage** each vote removes (nominal
L = SPMO + 3·TQQQ) and **which leg** supplies it. Separated here.

**A. Which leg, at the live leverage path (2.00 → 1.33 → 0.67 → 0):**

| composition (1 vote / 2 votes) | live release real CAGR / MaxDD / ΔSh | proxy ΔSh F / H | latch real ΔSh | latch proxy edge |
|---|---|---|---|---|
| proportional (live) 33/33/33 · 17/17/67 | 37.29% / −18.6% / — | — | +0.139 | +2.23 |
| TQQQ first 50/28/22 · 50/6/44 | 37.42% / −18.4% / +0.005 | +0.002 / +0.001 | +0.135 | +2.29 |
| SPMO first 0/44/56 · 0/22/78 | 37.27% / −19.0% / −0.004 | −0.002 / −0.003 | +0.116 | +2.14 |
| core-heavy 83/17/0 · 67/0/33 | 37.19% / −18.0% / −0.002 | −0.003 / −0.004 | +0.144 | +2.21 |

**At matched leverage, which leg you cut barely matters** — every composition
is within ±0.005 Sharpe and ±0.15 pp CAGR of live under either release. Two
small effects pull against each other: less TQQQ saves decay and financing,
but on vote days the core earns less than cash (`trim_destination_test.md`),
so replacing cash with core costs. TQQQ-first sits at the small sweet spot
(proxy P 0.05 live release; P 0.00 under the latch, +0.002 Sharpe — real but
negligible).

**B. The asymmetric schedule, decomposed.** In leverage terms it is
2.00 → **1.17 → 0.33 → 0.25**: deeper at 1–2 votes, shallower at 3.

| live release | real ΔSh / ΔCAGR | proxy ΔSh F / H |
|---|---|---|
| proportional on AS's leverage path (the *depth* effect) | +0.007 / −0.03 pp | +0.006 / +0.005 |
| asymmetric (depth + *composition*) | +0.020 / +0.35 pp | +0.012 / +0.010 |

About half of the asymmetric gain is the leverage path, half the composition
(less TQQQ, less cash, more core at the same leverage). The composition half is
statistically clean on the proxy (CI [+0.004, +0.009], P 0.00) because it is
nearly mechanical — at equal leverage, less 3× means less decay — but it is a
0.006 Sharpe effect. Real P 0.16.

**Ranking of what matters, from all rounds:**
1. **The release rule** (when a vote is allowed to come off) — the latch moves
   real Sharpe +0.13 to +0.14 and proxy MaxDD by 3 pp, whatever the composition.
2. **The leverage path** per vote — ~0.007 Sharpe between reasonable paths
   (and trim depth, per `extension_step_decision.md`).
3. **Which leg** — ≤0.006 Sharpe at matched leverage.

So: think of a vote as a **de-leverage instruction**; the question worth an
owner decision is how long the de-leverage is held, not which ETF is sold.
Nothing applied.

## Follow-up 6: latch + asymmetric trim, with the A row at 30/70 (owner)

`paper-track/fall_protection_r8.py`, log `fall_protection_r8_run.log`. Asymmetric
at any base: TQQQ loses ½ of its base weight per vote, SPMO ⅙, freed weight to
cash. 30/70 rows: 30/70/0 → 25/35/40 → 20/0/80 → 15/0/85 (leverage 2.40 → 1.30
→ 0.20 → 0.15).

| arm | real CAGR / MaxDD / exSh | proxy CAGR / MaxDD / edge / exSh | holdout 2000–15 CAGR / MaxDD / Sh |
|---|---|---|---|
| live 50/50 | 37.29% / −18.6% / 1.376 | 25.46% / −27.0% / — / 0.990 | 17.84% / −27.0% / 0.754 |
| 30/70 alone | 41.94% / −23.0% / 1.342 | 28.35% / −31.3% / −0.60 / 0.983 | 19.77% / −31.3% / 0.753 |
| 50/50 + latch + asym | 37.21% / −17.8% / 1.515 | 24.66% / −23.3% / +2.74 / 1.035 | 16.68% / −23.3% / 0.752 |
| 40/60 + latch + asym | 39.57% / −18.7% / 1.511 | 26.06% / −24.3% / +3.46 / 1.038 | 17.58% / −24.3% / 0.756 |
| **30/70 + latch + asym** | **41.88% / −19.6% / 1.500** | **27.41% / −25.5% / +3.95 / 1.038** | **18.41% / −25.5% / 0.755** |

- **The latch pays for the extra leverage.** 30/70 alone buys +4.65 pp real CAGR
  with 4.4 pp more drawdown; with the latch and the asymmetric trim it keeps
  +4.59 pp of that CAGR for **1.0 pp** more real drawdown, and on the proxy it
  is both higher-return (+1.96 pp) and **shallower** (−25.5% vs −27.0%) than live.
- **First combination today that improves both proxy eras on point estimates**:
  holdout CAGR +0.57 pp, MaxDD +1.5 pp, Sharpe +0.001; search CAGR +4.25 pp,
  Sharpe +0.121. Largest drawdown edge on record (+3.95).
- Dollars (real history): $222k grows ×43.9 vs ×30.8 live; worst drawdown on
  today's balance $43.5k vs $41.3k.
- **Costs:** 2020 +36.4% vs +54.9%, **2025 +22.9% vs +37.3%, 2026 +27.7% vs
  +38.8%** (still above QQQ's 20.2% / 17.3%). 2022 −13.6% vs −10.3%. Worst
  real episodes: 2021–23 bear −18.1 (live −18.6), Feb–Mar 2025 −19.6 (−17.8),
  Q4 2018 −16.6 (−15.0) — falls that do not start from an extended market get
  the full 2.4× hit.
- **Evidence strength:** bootstrap vs live — Sharpe P(not better) 0.19 real /
  0.24 proxy, return P 0.17 / 0.18. Not significant. And this combination was
  **assembled after ~50 arms today**, each piece chosen after seeing results:
  the both-era pass is a point estimate on a selected configuration, not a
  pre-registered test.

**Status: the strongest candidate on the record, not applied.** Design frozen to
7 December. Honest path: pre-register exactly this configuration now, run it as a
paper shadow beside live until the freeze lifts, and decide then on the combined
backtest and forward evidence.

## Follow-up 7: at 30/70, should the de-leverage be quicker? (owner)

`paper-track/fall_protection_r9.py`, log `fall_protection_r9_run.log`. Base 30/70,
latch on. TQQQ cut per vote kt ∈ {⅓, ½ (current), ⅔, 1} × SPMO cut ks ∈ {⅙, ⅓};
plus a leverage-matched path (same absolute leverage per vote as 50/50 + both)
and earlier votes (8/10/13% instead of 10/12/15%).

| 30/70 + latch, TQQQ cut per vote | leverage path | real CAGR / MaxDD / exSh | proxy CAGR / MaxDD / exSh | holdout Sh | 2025 / 2026 real |
|---|---|---|---|---|---|
| ⅓ | 2.40→1.60→0.80→0 (≈) | 42.72% / −19.8% / 1.492 | 27.55% / −27.5% / 1.026 | 0.738 | 31.2 / 30.5 |
| ½ (current) | 2.40→1.30→0.20→0.15 | 41.88% / −19.6% / 1.500 | 27.41% / −25.5% / 1.038 | 0.755 | 22.9 / 27.7 |
| ⅔ | 2.40→0.95→0.20→0.15 | 42.41% / −19.6% / 1.532 | 27.61% / −24.7% / 1.052 | 0.760 | 21.3 / 26.8 |
| **1 (all TQQQ out at the first vote)** | 2.40→0.25→0.20→0.15 | **43.21% / −19.6% / 1.573** | **27.91% / −24.7% / 1.070** | **0.764** | 18.3 / 25.0 |
| live 50/50 | 2.00→1.33→0.67→0 | 37.29% / −18.6% / 1.376 | 25.46% / −27.0% / 0.990 | 0.754 | 37.3 / 38.8 |

- **Yes, quicker is better — monotonically in Sharpe, drawdown and holdout.**
  Cutting all TQQQ at the first vote is best on every summary metric, both eras,
  and even adds CAGR (+1.3 pp real vs current). Real 2021–23 bear −15.8% (current
  −18.1%, live −18.6%).
- **SPMO's cut rate is irrelevant** (⅙ vs ⅓: within ±0.003 Sharpe) — consistent
  with "which leg ≤0.006". Leverage-matched path sits between ½ and ⅔.
- **Earlier votes (8/10/13%) are rejected**: real CAGR −6.1 pp vs current (2024
  +47.4% vs +65.0%), even though the proxy holdout loves it (0.847) — the eras
  disagree.
- **Not specific to the higher leverage.** The same rates at 50/50: Sharpe
  1.507 → 1.515 → 1.537 → 1.574, proxy MaxDD −24.3 → −21.9. The gain from
  quicker cuts is about the same at either base (+0.06 to +0.07 real Sharpe from
  ½ to 1). **Vote days are bad days to hold TQQQ at any leverage**; the quicker
  cut simply removes it sooner.
- **Costs:** quicker = more cash in melt-ups. 2025 real +18.3% (current +22.9%,
  live +37.3%); 2026 +25.0% (+27.7%, +38.8%). Bootstrap vs current: ⅔ P 0.06 real
  / 0.11 proxy; 1 P 0.12 / 0.16. Not significant.
- **What "TQQQ out at the first vote" means with the latch:** any single vote
  inside an A spell moves the book to 25% SPMO / 75% cash until the book leaves
  A. The trim becomes a switch. Exposure 58.9% vs live 67.2%.

Still post hoc (now ~70 arms today), still frozen to 7 December. If a
configuration is pre-registered for a shadow track, the evidence favours
**30/70 + latch + TQQQ fully out at the first vote**, with the recent-years cost
stated alongside it.

## Follow-up 8: "seems this becomes a profit cap" (owner) — measured: yes

`paper-track/fall_protection_r10.py`, log `fall_protection_r10_run.log`. Arm:
30/70 + latch + all TQQQ out at the first vote. Comparison: 30/70 with the live
trim (same base, so only the latch + cut differs). Every A spell in which the
latch engaged, first vote → last A session, split by what QQQ did.

| | real | proxy |
|---|---|---|
| latched spells | 17 (1.6/yr) | 41 (1.6/yr) |
| **CAP** spells (QQQ kept rising >2%) | 6 spells, **473 days**, **−7.2 pp/yr** | 14 spells, 979 days, −5.9 pp/yr |
| **SAVE** spells (QQQ fell >2%) | 11 spells, 199 days, **+8.7 pp/yr** | 21 spells, 284 days, +5.7 pp/yr |
| **net over latched spells** | **+0.9 pp/yr** | **−0.4 pp/yr** |
| median forgone in a cap / saved in a save | 15.6 pp / 8.8 pp | 10.3 pp / 6.4 pp |

Largest caps (real): 19 Dec 2023 – 12 Apr 2024 **−22.0 pp**, 30 Jun – 17 Nov 2025
**−20.9 pp**, 5 May – 15 Jul 2026 **−15.6 pp**. Largest saves: Apr–May 2021
+12.6, Dec 2024 – Jan 2025 +12.4, Nov–Dec 2021 +11.4. **Three of the last four
latched spells were caps.**

Up / down capture vs QQQ (mean daily return on QQQ up / down days):

| | real up / down | best-10% QQQ days | proxy up / down |
|---|---|---|---|
| live 50/50 | 1.00× / 0.87× | 0.71× | 0.93× / 0.81× |
| 30/70 live trim | 1.18× / 1.04× | 0.82× | 1.06× / 0.93× |
| 30/70 latch + full cut | **0.95× / 0.77×** | **0.61×** | 0.88× / 0.74× |

**Reading.** It is a profit cap, by construction: a vote means "the market is
extended", the latch means "stay out until the trend resets", and in a
persistent melt-up the trend does not reset for months. It wins more often
(saves outnumber caps ~2:1) but each save is short and each cap is long.
Summed over its own spells it is roughly **break-even** (+0.9 real / −0.4 proxy
pp/yr); what it really buys is **shape** — lower down-capture, lower drawdown,
higher Sharpe — paid for with up-capture falling below 1.0× QQQ and a third less
of the best days. The overall CAGR gain of 30/70 + latch over live comes from the
30/70 base leverage, not from the latch.

Against the standing objective ("outperform SPY and QQQ") this is a mismatch:
the cost lands in exactly the strong persistent rallies (2024, 2025, 2026) that
have dominated recently. The asymmetric / TQQQ-first *shape* under the live
release has no cap (it releases normally) and remains the only free piece.

## Follow-up 9: stepped re-entry inside A (owner: "remove the vote in steps")

`paper-track/fall_protection_r11.py`, log `fall_protection_r11_run.log`. Base
30/70, TQQQ fully out at the first vote. Votes rise at once; held votes come off
**one at a time**, never below the raw count: one step per 5 / 10 / 20 sessions
without a change, or one step per new 20-session closing high. Controls: same
schedule with the live release (no latch) and with the full latch.

| 30/70, TQQQ out at first vote | real CAGR / MaxDD / exSh | up / down capture | proxy CAGR / MaxDD / edge / exSh | holdout CAGR / Sh | real 2024 / 2025 / 2026 |
|---|---|---|---|---|---|
| live 50/50 | 37.29% / −18.6% / 1.376 | 1.00 / 0.87 | 25.46% / −27.0% / — / 0.990 | 17.84% / 0.754 | 66.8 / 37.3 / 38.8 |
| 30/70 live trim | 41.94% / −23.0% / 1.342 | 1.18 / 1.04 | 28.35% / −31.3% / −0.60 / 0.983 | 19.77% / 0.753 | 73.9 / 40.0 / 44.2 |
| live release (no latch) | 41.87% / −21.7% / 1.368 | 1.11 / 0.96 | 28.73% / −28.0% / +3.21 / 1.015 | 20.49% / 0.792 | 69.3 / 34.3 / 43.8 |
| latch | 43.21% / −19.6% / 1.573 | 0.95 / 0.77 | 27.91% / −24.7% / +5.37 / 1.070 | 18.43% / 0.764 | 65.9 / 18.3 / 25.0 |
| step 5d | 39.47% / −21.7% / 1.376 | 1.02 / 0.88 | 27.32% / −27.8% / +1.48 / 1.016 | 19.74% / 0.798 | 66.8 / 26.0 / 25.2 |
| step 10d | 43.62% / −21.2% / 1.527 | 1.00 / 0.82 | 28.35% / −26.9% / +3.75 / 1.064 | 18.88% / 0.775 | 79.5 / 23.0 / 25.3 |
| step 20d | 42.77% / −19.6% / 1.545 | 0.96 / 0.78 | 27.63% / −24.7% / +4.99 / 1.056 | 18.26% / 0.757 | 65.6 / 22.8 / 25.1 |
| **step on each new 20d high** | **44.83% / −19.6% / 1.606** | 0.97 / 0.78 | **28.31% / −24.7% / +5.90 / 1.077** | 18.08% / 0.749 | **80.6** / 20.7 / 25.0 |

Cap vs save over the latched spells (vs 30/70 live trim, pp/yr): latch −7.24 /
+8.67 (net +1.42 real; −0.17 proxy); **step on 20d high −6.28 / +8.68 (net
+2.40 real; +0.09 proxy)**; step 10d −5.33 / +7.05 (+1.72; +0.24).

- **Stepping on new highs is the best of the latch family.** Same crash
  protection as the full latch (identical worst episodes: real 2021–23 −15.8%,
  proxy GFC −18.8%, dot-com −21.3%), with part of the cap given back: the
  Dec 2023 – Apr 2024 rally is recovered (2024 +80.6% vs latch +65.9%, live
  +66.8%). Highest real Sharpe (1.606) and largest proxy edge (+5.90) on record.
- **It does not remove the cap.** 2025 +20.7% and 2026 +25.0% (live +37.3% /
  +38.8%); up-capture 0.97× vs 30/70-live-trim 1.18×. Those rallies stayed
  extended — raw votes stayed on — so stepping down to the raw count still left
  TQQQ out. Holdout Sharpe 0.749 vs live 0.754 (not confirmed out of sample).
- **Time-based steps are unstable in N**: 5d is poor, 10d good, 20d ≈ latch.
  Step 10d is the only arm beating live in both proxy eras on CAGR *and* Sharpe
  (holdout 18.88% / 0.775) but leaves the real 2021–23 bear at −21.2%.
- **Decomposition surprise:** the full cut *with the live release* (no latch)
  has the best holdout of all (20.49% / 0.792) at up-capture 1.11× — the cut
  speed carries out of sample better than any hold rule.
- Bootstrap vs live: step-on-high P 0.08 real / 0.15 proxy. ~80 arms today, all
  post hoc. Nothing applied; frozen to 7 December.

## Follow-up 10: step on a 5 / 10 / 15 / 20 / 30-day high (owner: "5 day and 15 day high")

`paper-track/fall_protection_r12.py`, log `fall_protection_r12_run.log`
(`stephigh:20` asserted identical to follow-up 9's `stephigh`). Base 30/70, TQQQ
out at the first vote; one held vote comes off per new N-session closing high.

| N | real CAGR / MaxDD / exSh | real 2024 / 2025 / 2026 | proxy CAGR / MaxDD / edge / exSh | holdout CAGR / Sh | cap/save net real / proxy |
|---|---|---|---|---|---|
| live 50/50 | 37.29% / −18.6% / 1.376 | 66.8 / 37.3 / 38.8 | 25.46% / −27.0% / — / 0.990 | 17.84% / 0.754 | — |
| 5 | 38.57% / −21.7% / 1.362 | 53.9 / 21.5 / 24.7 | 25.63% / −29.6% / −2.46 / 0.970 | 17.52% / 0.725 | −2.02 / −1.53 |
| 10 | 43.03% / −19.6% / 1.544 | 67.8 / 20.9 / 25.0 | 27.87% / −24.7% / +5.30 / 1.059 | 18.46% / 0.761 | +1.15 / −0.25 |
| **15** | **45.05% / −19.6% / 1.612** | **80.6** / 20.9 / 25.0 | **28.50% / −24.7% / +6.16 / 1.083** | **18.27% / 0.755** | **+2.55 / +0.24** |
| 20 | 44.83% / −19.6% / 1.606 | 80.6 / 20.7 / 25.0 | 28.31% / −24.7% / +5.90 / 1.077 | 18.08% / 0.749 | +2.40 / +0.09 |
| 30 | 44.83% / −19.6% / 1.606 | 80.6 / 20.7 / 25.0 | 28.31% / −24.7% / +5.90 / 1.077 | 18.08% / 0.749 | +2.40 / +0.09 |

- **5-day is bad on every axis**: in a fall, any short bounce makes a 5-day
  high, so the votes step off into the decline (real 2021–23 bear −21.7% vs
  −15.8%; proxy edge −2.46; holdout 0.725). Rejected.
- **10-day** keeps the crash protection but does not recover the 2024 rally.
- **15 / 20 / 30 form a plateau** — 20 and 30 are identical and 15 is a hair
  better (real 45.05% / 1.612; proxy edge +6.16; holdout 18.27% / 0.755 vs live
  17.84% / 0.754). A plateau rather than a spike is the good sign here: the rule
  is not balanced on one number.
- Unchanged by N ≥ 10: the same worst-episode protection and the same 2025 /
  2026 cap (+20.9% / +25.0% vs live +37.3% / +38.8%).
- Bootstrap vs live: 15d P 0.06 real / 0.14 proxy. Post hoc (~85 arms today).
  Nothing applied; frozen to 7 December.

## Follow-up 11: graded TQQQ re-entry (owner: "try it")

`paper-track/fall_protection_r13.py`, log `fall_protection_r13_run.log`. Exit fast
(a fresh vote takes all TQQQ out), come back in thirds: each new N-day high puts
one third of the base TQQQ back (0 → 23 → 47 → 70%). F1 keeps the floor (rung ≤
3 − raw votes); F0 has none (only a fresh vote takes TQQQ out again).

| arm (30/70) | real CAGR / MaxDD / exSh | up-cap | real 2021 / 2024 / 2025 / 2026 | proxy CAGR / MaxDD / exSh | holdout CAGR / Sh | proxy dot-com |
|---|---|---|---|---|---|---|
| live 50/50 | 37.29% / −18.6% / 1.376 | 1.00 | 49.2 / 66.8 / 37.3 / 38.8 | 25.46% / −27.0% / 0.990 | 17.84% / 0.754 | −26.7% |
| one-step, 15d high | 45.05% / −19.6% / 1.612 | 0.97 | 94.5 / 80.6 / 20.9 / 25.0 | 28.50% / −24.7% / 1.083 | 18.27% / 0.755 | −21.3% |
| **graded, 15d, floor** | **45.54% / −19.6% / 1.616** | **1.01** | 83.0 / 79.6 / **28.8** / 25.3 | 28.13% / −24.7% / 1.061 | **17.51% / 0.721** | −24.5% |
| graded, 20d, floor | 45.34% / −19.6% / 1.612 | 1.01 | 83.0 / 79.6 / 28.5 / 25.3 | 27.91% / −24.7% / 1.055 | 17.27% / 0.713 | −24.5% |
| graded, 15d, no floor | 41.26% / −23.5% / 1.337 | 1.15 | 68.6 / **48.7** / 28.5 / **15.6** | 27.10% / −24.7% / 0.962 | 18.33% / 0.722 | −24.5% |

- **With the floor, graded re-entry is the best real result on record** (45.54% /
  1.616) and eases the cap a little: up-capture back to 1.01×, 2025 +28.8% vs
  +20.9% one-step (live +37.3%). 2026 unchanged (+25.3%). Crash protection on
  the real episodes identical.
- **But it fails the holdout**, which the one-step version passed: 2000–15
  17.51% / 0.721 vs live 17.84% / 0.754 and one-step 18.27% / 0.755. The
  mechanism: in 2000–02 bear rallies set new 15-day highs, and partial re-entry
  put TQQQ back into them (dot-com −24.5% vs −21.3% one-step). Graded vs one-step:
  real P(not better) 0.46, proxy 0.78 — no evidence it is better.
- **Without the floor it is bad everywhere** (real 41.26% / −23.5% / 1.337;
  2024 +48.7%, 2026 +15.6%): re-entering while the market is still extended
  puts TQQQ back just before the next vote fires and takes it out again —
  whipsaw. Rejected. The floor is doing real work.

**Verdict:** graded re-entry trades out-of-sample robustness for a slightly
better recent record. The one-step version remains the pick for a pre-registered
shadow (it is the one that holds up in 2000–15). Nothing applied; frozen to
7 December.

## Follow-up 12: N sweep under graded re-entry (owner: "the change in days of n will make a difference")

`paper-track/fall_protection_r14.py`, log `fall_protection_r14_run.log`. Graded
(floor) and one-step re-entry at N = 5 / 10 / 15 / 20 / 30 / 40 / 60.

| N | graded real CAGR / exSh | graded holdout CAGR / Sh | one-step real CAGR / exSh | one-step holdout CAGR / Sh |
|---|---|---|---|---|
| live 50/50 | 37.29% / 1.376 | 17.84% / 0.754 | — | — |
| 5 | 40.80% / 1.438 | 17.30% / 0.710 | 38.57% / 1.362 | 17.52% / 0.725 |
| 10 | 45.02% / 1.597 | 17.40% / 0.717 | 43.03% / 1.544 | **18.46% / 0.761** |
| 15 | **45.54% / 1.616** | 17.51% / 0.721 | 45.05% / 1.612 | 18.27% / 0.755 |
| 20 | 45.34% / 1.612 | 17.27% / 0.713 | 44.83% / 1.606 | 18.08% / 0.749 |
| 30 | 45.21% / 1.608 | 17.27% / 0.713 | 44.83% / 1.606 | 18.08% / 0.749 |
| 40 | 45.21% / 1.608 | 17.43% / 0.720 | 44.83% / 1.606 | 18.00% / 0.746 |
| 60 | 45.25% / 1.610 | 17.43% / 0.720 | 44.83% / 1.606 | 18.00% / 0.746 |

- **N matters only below ~10.** N = 5 fails both versions (a 5-day high comes on
  any bounce, so TQQQ goes back into falls). From 10 to 60 the graded version is
  flat: real 45.0–45.5%, Sharpe 1.597–1.616; proxy MaxDD −24.7% at every N;
  2025 +28.5–28.8%, 2026 +25.3% at every N.
- **Why flat:** in state A the market sits near its highs, so a new 10-, 20- or
  even 60-day high arrives within days of the rally resuming, and the floor
  (raw votes) is what actually sets the pace of re-entry, not N.
- **The graded holdout failure is structural**: 2000–15 Sharpe 0.710–0.721 at
  every N, all below live (0.754) and below one-step at the same N. No choice of
  N rescues it; the dot-com bear rallies are the cause (−24.5% vs −21.3%).
- Graded vs one-step at the same N: real P(not better) 0.43–0.46 for N ≥ 15,
  proxy 0.72–0.81. Only at N = 5 is graded clearly better, and both fail there.
- One-step N = 10 has the best holdout of the sweep (18.46% / 0.761) but misses
  the 2024 rally (real +67.8%); N = 15 is the balance point.

**Verdict unchanged:** one-step re-entry on a 15-day high remains the shadow
pick. N is not a sensitive parameter above 10, which is reassuring. Nothing
applied; frozen to 7 December.

## Follow-up 13: middle version — cap the hold (owner: "test a middle version")

`paper-track/fall_protection_r15.py`, log `fall_protection_r15_run.log`. Base 50/50
(live). v2 plus a release of the hold to the raw count, either after **K** sessions
since the last vote rise (K = 20/40/60/90) or once raw votes have been zero for **M**
sessions (M = 3/5/10/20). 8 arms, grid and pass rule **pre-registered in the script
docstring before the first run**. Asserted: K = M = 0 reproduces live v2 exactly.

Pass rule (all three): P1 proxy MaxDD ≥ 3 pp shallower than fast-cut-only (≥ −23.6%);
P2 real 2025+2026 shortfall vs fast-cut-only ≤ half of v2's (≤ 15.5 pp; v2's is
31.0); P3 proxy 2000–15 CAGR ≥ the 19 Sep design's (≥ 17.84%).
*Correction logged:* the first run's P1 code compared in the wrong direction
(`<=` on a negative MaxDD); the code was fixed to match the written rule and re-run.
The verdict was the same both times.

| arm (50/50) | real CAGR / exSh | 2025 / 2026 | proxy MaxDD | holdout CAGR / Sh | P1 P2 P3 |
|---|---|---|---|---|---|
| 19 Sep design | 37.29% / 1.376 | 37.3 / 38.8 | −27.0% | 17.84% / 0.754 | ref |
| fast-cut only | 37.27% / 1.397 | 32.4 / 38.3 | −26.6% | 18.25% / 0.783 | ref |
| live v2 | 39.32% / 1.605 | 22.7 / 24.1 | −21.9% | 16.56% / 0.752 | ref |
| cap K=20 | 38.38% / 1.543 | 26.0 / 26.6 | −21.9% | 17.03% / 0.767 | Y – – |
| cap K=40 | 39.64% / 1.615 | 22.7 / 26.1 | −21.9% | 16.56% / 0.751 | Y – – |
| cap K=60, 90 | ≈ v2 | ≈ v2 | −21.9% | ≈ v2 | Y – – |
| clear M=3 | 34.45% / 1.353 | 22.4 / 21.4 | −26.6% | 15.64% / 0.701 | – – – |
| clear M=5 | 34.75% / 1.384 | 24.3 / 24.1 | −26.6% | 15.72% / 0.708 | – – – |
| clear M=10 | 36.67% / 1.474 | 26.3 / 24.1 | −26.5% | 16.01% / 0.726 | – – – |
| clear M=20 | ≈ v2 | ≈ v2 | −21.9% | 16.76% / 0.759 | Y – – |

**Result: no arm passes. No change; v2 stays.**

- **The session cap does little.** Holds rarely outlast 40 sessions without a
  step-off, so K ≥ 60 is v2. K = 20 buys back ~3 pp in 2025 and 2026 and +0.5 pp
  holdout CAGR, at −0.06 real Sharpe, keeping v2's full drawdown protection.
  Not distinguishable from v2 (bootstrap P 0.88 real / 0.69 proxy).
- **The clear-days release is worse than both ends.** It re-levers inside
  pullbacks: raw votes clear when price falls back toward the averages, not when
  the rally resumes. On the 85 real days where M = 5 held TQQQ and v2 did not, QQQ
  ran at **−58% annualised**, 2.4% below its 20-day high on average (all A days:
  +17.7%, −1.0%). This is the v1 flaw the new-high step was built to remove.
- **The trade-off is structural.** Every arm that keeps v2's drawdown (−21.9%)
  also keeps most of its 2025–26 cost and its lower holdout CAGR; every arm that
  drops the cost also drops the protection. There is no free middle on this
  mechanism. 8 more arms (~93 today), all post hoc.

## Follow-up 14: whipsaw carry (fix 3 of the critique) — APPLIED

`paper-track/fall_protection_r16.py`, log `fall_protection_r16_run.log`. v2 reset
the held votes on ANY non-A session, so a one-day dip out of A put TQQQ straight
back in. Test: held votes survive a non-A gap of ≤ G sessions (G = 3, 10).
Pre-registered no-harm rule at 50/50: real and proxy exSharpe ≥ v2 − 0.01, proxy
MaxDD ≥ v2 − 1 pp, holdout CAGR ≥ v2 − 0.5 pp; adopt the smallest G that passes.

| 50/50 | real CAGR / Sharpe / MaxDD | proxy CAGR / Sharpe / MaxDD | holdout CAGR |
|---|---|---|---|
| v2 (G = 0) | 39.32% / 1.717 / −17.8% | 25.41% / 1.161 / −21.9% | 16.56% |
| **G = 3** | **41.03% / 1.797 / −17.8%** | **26.11% / 1.194 / −21.9%** | **16.64%** |
| G = 10 | 39.29% / — / −17.8% | 25.33% / — / −21.9% | 16.48% |

Both pass; **G = 3 adopted** (smallest). The gain is a few events, all the same
mechanism: a 1–2 day D reading, votes reset, TQQQ back in at full weight right
before the next leg down — real 6–7 Feb 2018 (−1.6% and **−8.2%** vs +0.1% and
−1.1%), 1–2 Mar 2021 (−3.0%, −4.9% vs −0.5%, −0.6%), Dec 2021; proxy adds Nov
2002 and Apr–May 2012 (where the carry cost a little). Adopted on the mechanism
under a no-harm rule; the size of the gain is not the argument. `state.py`
`A_SPELL_GAP_CARRY = 3` reproduces the harness on all 1,854 real A days;
`check_extension_trim_v2` asserts the Feb 2018 carry and every gap in the history
(13 short gaps carried, 82 new spells). The same rule defines the A spell for the
30/70 base row, so a 1–3 day whipsaw cannot flip the live 50/50 spell to 30/70.

## Follow-up 15: fast-cut with a new-high re-entry for TQQQ only (owner: "test fast cut with a new-high re-entry for TQQQ only")

`paper-track/fall_protection_r17.py`, log `fall_protection_r17_run.log`; harness arm
`fchigh:N`. SPMO is cut ⅙ per RAW vote and restored as soon as the votes fall;
TQQQ is out while raw ≥ 1 and, once raw is back to 0, returns only on a new
N-session closing high (one high brings all of it back). Base 50/50, whipsaw carry 3.

| arm | real CAGR / Sharpe / MaxDD | reb/yr | 2025 / 2026 | proxy CAGR / Sharpe / MaxDD | holdout CAGR / Sharpe | TQQQ re-entries (real): QQQ next 20d |
|---|---|---|---|---|---|---|
| fast-cut | 37.27% / 1.498 / −17.8% | 45 | 32.4 / 38.3 | 25.64% / 1.096 / −26.6% | 18.25% / 0.855 | 50: −0.54% |
| live v2 | 41.03% / 1.797 / −17.8% | 32 | 22.7 / 24.1 | 26.11% / 1.194 / −21.9% | 16.64% / 0.834 | 5: +1.10% |
| **fast-cut + high 15** | **40.93% / 1.783 / −17.8%** | 45 | 23.3 / 25.9 | **25.81% / 1.176 / −22.4%** | **16.36% / 0.818** | 5: +1.27% |
| fast-cut + high 5 / 10 / 20 | 37.12 / 39.55 / 40.74% | 45–46 | ~23 / ~26 | MaxDD −26.6 / −22.4 / −22.4% | 16.49 / 16.18 / 16.81% | 11 / 7 / 5 |

**Result: it is v2 in all but name.** Every number sits within noise of v2
(bootstrap vs v2 P 0.72 real / 0.86 proxy): the same protection (proxy −22.4% vs
−21.9%), the same profit cap (2025–26 +23 / +26 vs +23 / +24), the same weaker
holdout return (16.4% vs 16.6%), and ~13 more rebalances a year because SPMO still
moves with the raw votes. Against plain fast-cut it is a real Sharpe gain (P 0.03
real / 0.14 proxy) bought with the same 2025–26 cost.

What it settles: **the new-high test on TQQQ is the whole of v2's effect** — both
its protection and its cost. Holding SPMO down (⅙ per held vote) adds almost
nothing. So the trade-off from follow-ups 12–14 is really one question: does
TQQQ wait for a new high after the votes clear, or not? N = 15 sits on a plateau
(10–20 alike; 5 re-enters too early: 11 re-entries, 45% followed by a 20-day fall).

Probation consequence: the shadow comparator stays **plain fast-cut**. Fast-cut +
high is so close to v2 that comparing against it could not tell the two apart.
Nothing applied. ~98 arms today.

## Follow-up 16: fast-cut + new-high TQQQ re-entry at 30/70 (owner: "try 30/70 with fast-cut plus new high")

`paper-track/fall_protection_r18.py`, log `fall_protection_r18_run.log`. Same rule as
follow-up 15 at the 30/70 base scheduled for the next A spell; whipsaw carry 3.

| arm | real CAGR / Sharpe / MaxDD | reb/yr | 2025 / 2026 | proxy CAGR / Sharpe / MaxDD | holdout CAGR / Sharpe |
|---|---|---|---|---|---|
| v2 50/50 (live) | 41.03% / 1.797 / −17.8% | 32 | 22.7 / 24.1 | 26.11% / 1.194 / −21.9% | 16.64% / 0.834 |
| fast-cut 30/70 | 41.87% / 1.455 / −21.7% | 45 | 34.3 / 43.8 | 28.73% / 1.087 / −28.0% | **20.49%** / 0.857 |
| v2 30/70 | 47.36% / 1.802 / −19.6% | 32 | 20.9 / 25.0 | 29.42% / 1.200 / −24.7% | 18.36% / 0.830 |
| **fast-cut + high 15, 30/70** | **47.33% / 1.798 / −19.6%** | 44 | 21.7 / 26.0 | **29.03% / 1.183 / −24.7%** | **17.86% / 0.808** |
| fast-cut + high 10 / 20, 30/70 | 45.31 / 47.06% | 45 / 44 | ~22 / 26 | 28.13 / 29.34%, −24.7% | 17.60 / 18.50% |

Result: the same as at 50/50 — **fast-cut + high is v2 again** (bootstrap vs v2
30/70 P 0.62 real / 0.84 proxy), with ~12 more rebalances a year and a slightly
weaker holdout (17.9% vs 18.4%). Moving the base from 50/50 to 30/70 under either
rule adds ~6.3 pp real / ~3 pp proxy CAGR at the same Sharpe, for ~1.8 pp (real)
and ~2.8 pp (proxy) more drawdown — the leverage dial found in `a_ratio_study.md`,
unchanged. Plain fast-cut at 30/70 has the best holdout return of any arm today
(20.5%) and the worst drawdown (proxy −28.0%, real −21.7%). Nothing applied.

## Follow-up 17: TQQQ re-entry on a close above the 5 / 10 / 15-day SMA (owner: "what about the 5, 10, 15 dma")

`paper-track/fall_protection_r19.py`, log `fall_protection_r19_run.log`; harness arm
`fcsma:N`. Fast-cut, but once the raw votes are back to 0 TQQQ returns on a close
above QQQ's N-day SMA instead of a new 15-day high. Bases 50/50 and 30/70, carry 3.

| 50/50 | real CAGR / Sharpe | 2025 / 2026 | proxy CAGR / MaxDD | holdout CAGR | real re-entries: QQQ next 20d, % followed by a fall |
|---|---|---|---|---|---|
| fast-cut | 37.27% / 1.498 | 32.4 / 38.3 | 25.64% / −26.6% | 18.25% | 50: −0.54%, 54% |
| fc + 5d SMA | 35.30% / 1.496 | 18.2 / 23.8 | 23.31% / −26.6% | 15.72% | 23: −0.41%, 61% |
| fc + 10d SMA | 37.77% / 1.588 | 24.3 / 26.2 | 24.58% / −26.7% | 16.24% | 19: −1.22%, 68% |
| fc + 15d SMA | 36.47% / 1.515 | 24.7 / 23.8 | 24.50% / −26.7% | 16.91% | 30: −0.14%, 57% |
| fc + 15d high | 40.93% / 1.783 | 23.3 / 25.9 | 25.81% / −22.4% | 16.36% | 5: +1.27%, 20% |
| v2 | 41.03% / 1.797 | 22.7 / 24.1 | 26.11% / −21.9% | 16.64% | 5: +1.10%, 20% |

30/70 is the same picture (SMA arms 39.0–42.7% real, Sharpe 1.45–1.56, proxy MaxDD
−28.0 to −28.6%, holdout 16.9–18.6%; fc + 15d high 47.3% / 1.80 / −24.7%).

**Result: worst of both.** A close above a short SMA happens routinely inside a
pullback (a bounce day), so the SMA arms put TQQQ back into falls — QQQ is lower
20 days later on average after every one of them, and 57–68% of re-entries are
followed by a fall — and they lose the proxy protection (−26.6 to −28.6%, same as
plain fast-cut). Yet they still pay most of the rally cost (2025 +15 to +25%),
because the extra round trips trim, re-enter and trim again. Bootstrap: none beats
plain fast-cut (P 0.23–0.85) and all lose to the 15-day high (P 0.93–1.00). The
new-high test works because a new high is a much stricter "the fall is over" read
than a close above an average. Nothing applied; ~110 arms today.

## Follow-up 18: new 10-day high for re-entry (owner: "try a new 10 day high for re-entry")

`paper-track/fall_protection_r20.py`, log `fall_protection_r20_run.log`. v2 and
fast-cut + high with N = 10 vs the live N = 15, both bases, whipsaw carry 3.

| | real CAGR / Sharpe / MaxDD | 2024 / 2025 / 2026 | proxy CAGR / MaxDD | holdout CAGR / Sharpe |
|---|---|---|---|---|
| v2 15d, 50/50 (live) | 41.03% / 1.797 / −17.8% | 69.6 / 22.7 / 24.1 | 26.11% / −21.9% | 16.64% / 0.834 |
| v2 10d, 50/50 | 39.61% / 1.739 / −17.8% | 60.7 / 22.7 / 24.1 | 25.64% / −21.9% | 16.75% / 0.838 |
| v2 15d, 30/70 | 47.36% / 1.802 / −19.6% | 80.6 / 20.9 / 25.0 | 29.42% / −24.7% | 18.36% / 0.830 |
| v2 10d, 30/70 | 45.31% / 1.731 / −19.6% | 67.8 / 20.9 / 25.0 | 28.77% / −24.7% | 18.54% / 0.835 |

**Result: slightly worse; keep 15.** N = 10 re-enters a little earlier (7 real
re-entries vs 5; 29% followed by a 20-day fall vs 20%). It costs 1.4–2.1 pp real
CAGR, almost all in 2024 (one early re-entry into the July–August 2024 fall), leaves
the drawdowns unchanged, and does NOT reduce the 2025–26 rally cost at all (identical
years). The holdout is a hair better (+0.1–0.2 pp, noise). Bootstrap vs 15: P(not
better) 1.00 real / 0.90 proxy. Fast-cut + high behaves the same way. Nothing applied.

## Follow-up 19: A base 40/60 under the live rule (owner: "What about 40/60")

`paper-track/fall_protection_r21.py`, log `fall_protection_r21_run.log`. v2 + whipsaw carry.

| A base | real CAGR / Sharpe / MaxDD | 2021 / 2022 / 2025 / 2026 | proxy CAGR / Sharpe / MaxDD | holdout CAGR / Sharpe |
|---|---|---|---|---|
| 50/50 (live) | 41.03% / 1.797 / −17.8% | 83.6 / −10.1 / 22.7 / 24.1 | 26.11% / 1.194 / −21.9% | 16.64% / 0.834 |
| **40/60** | **44.18% / 1.804 / −18.7%** | 93.3 / −11.8 / 21.8 / 24.5 | **27.78% / 1.199 / −22.6%** | **17.54% / 0.834** |
| 30/70 (next spell) | 47.36% / 1.802 / −19.6% | 103.3 / −13.4 / 20.9 / 25.0 | 29.42% / 1.200 / −24.7% | 18.36% / 0.830 |

Sharpe is flat across all three (bootstrap 40/60 vs 50/50 P 0.27 / 0.16, vs 30/70
P 0.59 / 0.73): the base is a leverage dial, as in `a_ratio_study.md`. Return is
linear in the base (+3.2 pp real, +1.7 pp proxy per 10 pp of TQQQ) but the proxy
drawdown is NOT: 50→40 costs 0.7 pp (−21.9 → −22.6%), 40→30 costs 2.1 pp more
(→ −24.7%). So **40/60 buys about half of 30/70's extra return for about a quarter
of its extra long-run drawdown** — the best return-per-drawdown step on the dial.
The real-era drawdown moves evenly (−17.8 / −18.7 / −19.6%), so the kink rests on
the proxy's two big bears. The rally cost in 2025–26 is the same at every base.
An owner choice on the dial; nothing applied (30/70 remains scheduled).
