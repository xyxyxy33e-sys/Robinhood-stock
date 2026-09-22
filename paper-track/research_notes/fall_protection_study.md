# Protection during the fall, inside state A — 2026-09-22. **One real finding; NOT applied (fails the holdout).**

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
