# State E pairs and unions — pre-registered test, 2026-09-19 (NOT applied)

Owner request: "do the same test for E" as `d_pair_test.md`. Script
`paper-track/e_pair_test.py`; full run log `e_pair_test_run.log` (every
number below is copied from it; nothing is hand-derived). Research only;
live code unchanged. Sharpe is the repo's zero-rate Sharpe throughout.

## 0. Summary and verdict

- **Baseline = the CURRENT live design, with the state-D gate.** Both
  harnesses reproduce it before anything is scored: 26-year QQQ-core proxy
  25.74% / 1.077 / −28.5% (S 1.410, H 0.828, 64.5% exposure, 49.4 reb/yr)
  and real daily 37.75% / 1.484 / −19.4% (69.2%, 47.3 reb/yr) — `d_pair_test`
  row #10, asserted day by day against `monthly_returns.simulate`.
- **State E is small.** 380 proxy days (5.8%) in 32 episodes (search 13,
  holdout 19), median 10 sessions; 150 real E days in 13 episodes. The
  effective sample for any E-only rule is the episodes, not the days.
- **Grid: 82 pre-registered candidates** = the five rules (breadth, SMA20≥SMA60,
  px≥SMA100, gap200 < −2%, vol ratio > 1.5) as singles, 10 AND pairs, 10 OR
  pairs and 16 unions, × two action families: CASH (flagged E day → 100% BOXX)
  and RISK (unflagged E day → 100% SPMO). 22 constant-E controls (XLU 0–100%
  and SPMO 0–100% on every E day, 10% steps). No rule was degenerate on the
  screen (flag rates 6.8%–61.6% of E days), so the full grid ran.
- **Nothing moves the book.** The ENTIRE constant-E ladder, from 100% cash to
  100% XLU to 100% SPMO on every E day, spans 0.013 of full-period Sharpe
  (S 0.018, H 0.026, real 0.012). That is the ceiling on what any E-row rule
  can do. The best candidate on the grid, CASH: SMA20≥SMA60 OR volratio>1.5,
  is +0.011 full-period Sharpe vs live (S +0.009, H +0.012; real +0.011).
- **Whole-grid permutation (1000 common shifts of the E-day flags, max over
  82):** full-period gain null 95th +0.027 vs best real +0.011, **p = 0.495**;
  both-era min null 95th +0.018 vs +0.009, **p = 0.259**; combination over
  its best member null 95th +0.021 vs +0.010, **p = 0.383**; both-era version
  p = 0.712. Within the CASH family alone (41 candidates) the both-era
  statistic reaches p = 0.087 — closest thing to a signal, still not 5%.
- **The RISK family is negative where it matters.** Holding 100% SPMO on
  "healthy" E days raises real CAGR by up to ~0.8 pp but deepens the proxy
  max drawdown from −28.5% to −33/−34% and the real one from −19.4% to −23.9%,
  loses the holdout for every breadth/gap200 variant (down to −0.066), and is
  worse than or equal to its own constant-SPMO control on real rows.
- **Verdict: E stays 50% XLU / 50% BOXX.** No candidate clears any part of the
  bar (both-era, matched control, bootstrap P<0.05, grid permutation p<0.05).
  This is the third negative on E substates (after `substate_research.py`
  and `de_substate_search.py`, STRATEGY.md "D and E substates: searched again
  on full history, still nothing", 2026-09-02) and the first with an explicit
  power statement: the sample cannot resolve an E-row effect smaller than
  about ±0.02 Sharpe, and the whole feasible range of E rows is 0.013 wide.
  Nothing here is a candidate for application or for a forward test.
  Candidate count this line: 82 + 22 controls. Cumulative D/E lines:
  267 + 890 + 41 + 82.

## 1. Setup

Harness imported from `d_substate_fresh.py` (DSF_STAGE=none) and
`d_pair_test.py`; the D gate is applied as an override on macro-D days via
`state.d_gate_active`, then E candidates modify only macro-E days on top.
Search era 2015-11+, holdout 2000-07..2015-10. Breadth is unavailable before
2008-01-07 (105 proxy E days): E stays live there, AND-with-breadth is False,
OR reduces to the other member; nothing backfilled.

Rules and flag rates on E days (proxy / real):

| rule | proxy flagged | rate | S rate | H rate | real flagged | rate |
|---|---:|---:|---:|---:|---:|---:|
| breadth (QQEW/QQQ 60d pct < 0.20) | 78 of 275 avail | 28.4% | 21.3% | 36.8% | 32 | 21.3% |
| SMA20 ≥ SMA60 | 56 | 14.7% | 9.3% | 18.3% | 14 | 9.3% |
| px ≥ SMA100 | 28 | 7.4% | 6.7% | 7.8% | 10 | 6.7% |
| gap200 < −2% (E analogue of the D rule; price is below the 200d on every E day) | 234 | 61.6% | 71.3% | 55.2% | 107 | 71.3% |
| volratio > 1.5 | 26 | 6.8% | 9.3% | 5.2% | 14 | 9.3% |

Degeneracy screen (drop if < 5% or > 95%): none dropped.

Next-day leg returns on E days, flagged vs unflagged (bp/day, core leg): no
rule separates E days at |t| > 1.9 in any era. The largest: px≥SMA100 flags
28 days whose next-day core return is −54 bp vs +15 unflagged (t −1.8, all
of it holdout); gap200<−2% flags days at +21 vs −8 (t 1.4). Nothing on the
XLU leg reaches |t| 1.2.

## 2. Overlap

Jaccard on proxy E days: breadth–volratio 0.28 (88% of vol-ratio days are
breadth days), gap200–volratio 0.10 (92% of vol-ratio days are gap200 days),
SMA20≥SMA60–px≥SMA100 0.18 (46% conditional). Breadth and px≥SMA100 never
coincide (0 days). In the search era volratio sits entirely inside gap200
(P = 1.00). So the grid has three roughly independent signals (breadth,
trend-intact, deep-below-200d) plus one duplicate (vol ratio).

## 3. Constant-E controls

Every E day, f × XLU + (1−f) cash and g × SPMO + (1−g) cash, 10% steps.
Full-period proxy Sharpe runs 1.071 (all cash) … 1.077 (live 50% XLU) …
1.074 (100% XLU) … 1.064 (100% SPMO); real 1.475 … 1.484 … 1.479 … 1.474.
Live (50% XLU) is at or within 0.003 of the best point on both ladders.
Holdout Sharpe falls monotonically as SPMO rises (0.825 → 0.802). The ladder
spans 0.013 full-period Sharpe end to end.

## 4. The grid (82 candidates)

Best by full-period proxy Sharpe, both families (Δ vs gated live):

| # | candidate | proxy CAGR / Sharpe / MaxDD | S Sh | H Sh | ΔS | ΔH | ΔF | real CAGR / Sharpe / MaxDD | real Δ |
|---|---|---|---|---|---|---|---|---|---|
| 18 | CASH: SMA20≥SMA60 OR volratio>1.5 | 26.03% / 1.088 / −28.5% | 1.419 | 0.840 | +0.009 | +0.012 | +0.011 | 38.02% / 1.494 / −19.4% | +0.011 |
| 70 | RISK: UNION(BR\|P100\|VR) | 26.45% / 1.087 / −33.4% | 1.411 | 0.843 | +0.001 | +0.015 | +0.010 | 38.54% / 1.486 / −23.9% | +0.002 |
| 22 | CASH: px≥SMA100 OR volratio>1.5 | 25.97% / 1.086 / −27.5% | 1.417 | 0.837 | +0.007 | +0.009 | +0.008 | 37.95% / 1.492 / −19.4% | +0.008 |
| 1 | CASH: SMA20≥SMA60 | 25.93% / 1.084 / −28.5% | 1.411 | 0.839 | +0.001 | +0.011 | +0.007 | 37.78% / 1.485 / −19.4% | +0.001 |
| 11 | CASH: breadth AND volratio>1.5 | 25.89% / 1.083 / −28.5% | 1.420 | 0.831 | +0.010 | +0.003 | +0.006 | 38.02% / 1.494 / −19.4% | +0.011 |
| 4 | CASH: volratio>1.5 | 25.87% / 1.082 / −28.5% | 1.418 | 0.831 | +0.008 | +0.003 | +0.005 | 37.97% / 1.492 / −19.4% | +0.009 |
| 43 | RISK: px≥SMA100 | 26.28% / 1.077 / −33.4% | 1.407 | 0.828 | −0.003 | +0.000 | +0.000 | 38.43% / 1.472 / −23.9% | −0.012 |
| 51 | RISK: breadth OR gap200<−2% | 25.26% / 1.057 / −34.0% | 1.430 | 0.778 | +0.020 | **−0.049** | −0.020 | 38.59% / 1.507 / −20.1% | +0.024 |
| 0 | CASH: breadth | 25.68% / 1.076 / −28.1% | 1.413 | 0.824 | +0.003 | −0.004 | −0.001 | 37.80% / 1.488 / −19.3% | +0.004 |
| 3 | CASH: gap200<−2% | 25.51% / 1.072 / −26.9% | 1.399 | 0.827 | −0.011 | −0.001 | −0.005 | 37.31% / 1.474 / −19.6% | −0.010 |

Worst: RISK: SMA20≥SMA60 (−0.022 search, real −0.028), RISK: SMA20≥SMA60 OR
px≥SMA100 (−0.025 search). Every RISK candidate has proxy MaxDD −31% to
−34% and real MaxDD −20% to −24% against the live −28.5% / −19.4%.

The best real-row candidate, #51 RISK: breadth OR gap200<−2% (real 38.59% /
1.507 / −20.1%, +0.024), is the D-gate pattern inverted: it holds 100% SPMO
on the 118 E days that are neither breadth-weak nor deep below the 200d. It
loses the holdout by −0.049, deepens the proxy drawdown to −34.0%, and
leave-one-regime-out is negative in every drop (−0.012 … −0.049).

## 5. Deltas and permutation

Against the exposure-matched constant control, only two singles are positive
in both eras: CASH: SMA20≥SMA60 (+0.003 S / +0.012 H vs XLU 40%) and CASH:
volratio>1.5 (+0.008 / +0.003 vs XLU 50%). Both are inside the constant-E
ladder's own 0.013 range. No combination beats its better member single in
both eras by more than +0.006.

Whole-grid permutation, 1000 common circular shifts of the 380-day E flag
sequences, max statistic over all 82 candidates:

| statistic | null median | null 95th | null max | best real | p |
|---|---:|---:|---:|---:|---:|
| full-period Sharpe gain vs live | +0.011 | +0.027 | +0.073 | +0.011 (#18) | 0.495 |
| both-era min gain vs live | +0.005 | +0.018 | +0.068 | +0.009 (#18) | 0.259 |
| combination over best member, full | +0.008 | +0.021 | +0.033 | +0.010 (#70) | 0.383 |
| combination over best member, both-era | +0.003 | +0.014 | +0.028 | +0.001 (#18) | 0.712 |

Family-only nulls: CASH (41) full p 0.172, both-era p 0.087; RISK (41) full
p 0.450, both-era p 0.396. Per-candidate own-null sd of the full-period gain:
median 0.008.

## 6. Deep diagnostics

**#18 CASH: SMA20≥SMA60 OR volratio>1.5** (best overall). Block bootstrap vs
live: proxy Sharpe 95% CI [−0.005, +0.032] P(≤0) 0.11; real [−0.006, +0.039]
P 0.20. Vs matched XLU-40% control: proxy P 0.06–0.07, real P 0.13–0.14. Vs
its better member: P 0.23–0.33. LORO +0.007 … +0.013 in every drop, one-session
lag +0.011, 20 bp +0.014, SPY analogue S −0.006 / H +0.008. It touches 16 of
32 proxy episodes for +5.8 pp total, of which 2015-08-21..09-29 is +4.8 pp
and 2020-03-11..04-09 is +2.3 pp; real total +1.9 pp over 7 episodes. A rule
whose lifetime contribution is two episodes and whose CI includes zero on
every comparison.

**#1 CASH: SMA20≥SMA60** (best single): P(≤0) vs live 0.14–0.15 proxy, 0.41
real; vs control 0.07–0.10; lag +0.010; 20 bp +0.010; SPY S −0.026 / H +0.010.
Total +3.6 pp over 26 years, +3.3 of it in Aug–Sep 2015.

**#43 RISK: px≥SMA100** and **#70 RISK: UNION(BR|P100|VR)**: bootstrap vs
live P ≈ 0.4–0.6, real vs matched SPMO control P 0.88–0.95 (i.e. worse than
just holding more SPMO on every E day), lag −0.010 / −0.028, 20 bp negative,
proxy MaxDD −33.4%.

**#51 RISK: breadth OR gap200<−2%**: real vs live P 0.05–0.07 (the one
near-miss) but proxy vs live P 0.83–0.86, LORO negative in all five drops
including −0.049 with the SPMO era removed, 20 bp holdout −0.069, SPY
−0.044 / −0.012. A search-era artefact of the 2018-10 and 2026-03 episodes.

**Drawdown episodes.** No candidate changes the live max-drawdown window
(proxy 2007-11-05 → 2009-03-13 at −28.5%; real 2021-11-18 → 2023-01-17 at
−19.4%). CASH rules touch it by 0.0–2.6 pp; RISK rules deepen it to −31/−34%
proxy and −20/−24% real. Per-episode gains for the best CASH rules come
from 2015-08, 2020-03 and 2000-09; the worst are 2016-06 and 2010-06/07.

## 7. Statistical power

32 proxy episodes (13 search / 19 holdout), 13 real. At the grid level a true
full-period Sharpe gain must exceed +0.027 to clear p < 0.05, a both-era gain
+0.018; for one pre-registered candidate on its own null the 95th percentile
is about +0.008. The best candidate's bootstrap CI is 0.036 wide on the proxy
and 0.043 on real rows, so an effect smaller than roughly ±0.02 cannot be
told from zero. The entire feasible range of E rows (all cash → all XLU → all
SPMO) is 0.013 wide. **The sample cannot support a conclusion about any E
sub-rule beyond "inside noise", and the space of E rows is too narrow for a
rule to matter even if one existed.**

## 8. Verdict

State E stays 50% XLU / 50% BOXX. No single, pair or union in either action
family clears both eras against its matched control with a bootstrap P<0.05,
and the whole-grid permutation is p 0.26–0.71 on every statistic. The RISK
family (hold SPMO on "healthy" E days) is the only thing with a visible real
CAGR effect and it buys it with a deeper drawdown, a holdout loss and a
negative leave-one-regime-out. Prior verdicts stand: `substate_research.py`
(2015+ window, too thin), `de_substate_search.py` (full history, flat cash
increases and 108 candidates, best +0.007, permutation p 0.58), and the XLU
choice for E (`The XLU update to state E`, 2026-08-31) is unchanged. Not a
forward-test candidate: with ~1.2 E episodes a year it would take decades to
log eight, and the effect ceiling is 0.013 Sharpe.
