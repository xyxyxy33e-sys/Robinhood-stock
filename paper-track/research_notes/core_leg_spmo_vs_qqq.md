# Is SPMO the right core leg? — tested 2026-09-21

**The core-leg choice had never been tested.** No entry existed in the research
record, yet the core is 50% of state A, 75% of B, 100% of C — right now ~48%
of the live book. Testing it: **SPMO dominates QQQ inside the design, and the
advantage is risk, not return.** Confirmed, not applied (nothing changes).

Separately, the standing post-reconstitution holdings check is now done and it
raises a live concern — section 3.

## 1. Standalone (2015-11 → 2026-09, 2726 sessions)

| | CAGR | Sharpe | MaxDD | vol |
|---|---|---|---|---|
| SPMO | +17.50% | 0.887 | −31.3% | 20.59% |
| QQQ | **+18.51%** | 0.876 | −35.6% | 22.20% |

SPMO vs QQQ: **beta 0.773, correlation 0.833, annualised alpha +3.22%.** Lower
return, lower risk, marginally better Sharpe — and materially less than fully
correlated with the Nasdaq sleeve the strategy levers.

Year by year the two diverge violently: SPMO trails QQQ by 38.4 pp in 2023 and
21.3 pp in 2020, and beats it by 21.1 pp in 2022 and 20.2 pp in 2024. As a
standalone bet it is a coin flip with a factor attached.

## 2. Inside the design — SPMO wins, on risk

Swapping the core leg from SPMO to QQQ, everything else identical, at the same
dollar exposure (67.2%):

| core | CAGR | Sharpe (ex-cash) | MaxDD | exposure |
|---|---|---|---|---|
| **SPMO (live)** | **37.29%** | **1.376** | **−18.6%** | 67.2% |
| QQQ | 36.74% | 1.300 | −25.5% | 67.2% |
| QQQ − SPMO | −0.55 pp | **−0.076** | **−6.9 pp** | 0 |

**SPMO dominates outright**: higher CAGR, higher Sharpe, a 6.9 pp shallower
drawdown — *and lower beta* (0.773), so it does this carrying less risk. No
exposure-matched control is needed, because any control would de-lever the QQQ
arm and make it worse still. This is the opposite shape from the state-D
TQQQ/QLD result, where the apparent winner was a hidden leverage increase.

### Is it just the recent momentum run? Partly — and the split matters

| slice | SPMO CAGR | QQQ CAGR | ΔCAGR | ΔSharpe | SPMO DD | QQQ DD |
|---|---|---|---|---|---|---|
| full era | 37.29% | 36.74% | +0.55 | **+0.076** | −18.6% | −25.5% |
| first half (to 2021-04) | 35.50% | 35.30% | +0.20 | **+0.086** | −16.5% | −17.5% |
| second half (2021-05+) | 39.17% | 38.24% | +0.93 | **+0.070** | −18.6% | −25.5% |
| before the SPMO run (→2023) | 32.12% | 32.44% | **−0.32** | **+0.069** | −18.6% | −25.5% |
| the SPMO run (2024→) | 54.43% | 50.80% | **+3.63** | **+0.091** | −17.8% | −19.2% |

**The return edge is not stable** — it is *negative* (−0.32 pp) over the eight
years to 2023 and worth +3.63 pp only in 2024-2026. **The Sharpe edge is
stable**: +0.069 to +0.091 in every slice, including the era where SPMO lost
on return. So SPMO earns its place by lowering risk consistently, not by
adding return; the recent outperformance is a bonus that should not be
extrapolated.

Design-level per-year diffs are still noisy (2023 −17.6 pp, 2022 +8.2, 2016
+6.2, 2024 +6.2), which is what a 0.77-beta, 0.83-correlation substitute
should look like.

**Hard limitation:** SPMO's fund inception is 2015-10-09, so this comparison
lives entirely inside the search era and **can never be holdout-tested**. That
is the same constraint that makes the whole real harness search-only, and it
is why the stable-Sharpe result matters more than the CAGR number.

## 3. The post-reconstitution concern (holdings as of 2026-09-18)

$22.1B AUM, 0.13% expense ratio, 44% annual turnover — liquid and cheap. But
the September reconstitution has left it extremely concentrated:

- **Top 3 = 26.3%** (MU **10.84%**, NVDA 9.05%, AVGO 6.43%); top 10 = 51.7%
- **Semiconductors ≈ 39.1%** of the top 25, **+5.7% memory/storage = ~44.8%**
- Information Technology sector weight **52.5%**
- **50.6% of the top-25 weight is also in the Nasdaq-100** — i.e. doubled up
  with the TQQQ/QLD sleeve the strategy already levers

The whole case for SPMO in section 2 rests on beta 0.773 and correlation
0.833 — it works because it is *not* the Nasdaq. A book that is ~45%
semiconductors in the core leg **and** holding 2×/3× Nasdaq in the satellite
is far more concentrated than those historical numbers imply, and a single
memory-cycle turn would hit both legs at once.

This is a forward-looking observation from current holdings, not a backtested
finding — the historical beta and correlation already include past
reconstitutions. But it is the exact risk the standing reconstitution check
exists to catch, and it argues for **re-measuring SPMO's beta and correlation
to QQQ on a trailing 6-month window each quarter**, rather than relying on the
11-year figures. If the rolling beta drifts toward 1.0, the diversification
that justifies the core leg is gone and this test should be re-run.

## Conclusion

**SPMO is the right core and stays.** The choice was never tested before and
now has been; it dominates QQQ on every axis at lower beta, with a Sharpe
advantage stable across every sub-period. Nothing to change.

**But watch the concentration.** Add a quarterly rolling beta/correlation check
on SPMO vs QQQ. The justification is a diversification property that the
current portfolio is actively eroding.

Nothing applied; `state.py` unchanged.
