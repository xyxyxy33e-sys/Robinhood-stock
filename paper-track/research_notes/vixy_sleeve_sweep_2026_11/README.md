# VIXY sleeve sweep: is 35% / the current trigger sensible? (2026-11-17) - research only, nothing adopted

Files: `PLAN.md` (grid, definitions, reading rule: written before any cell was run), `run.py` (one run, ~40 s), `run.log` (every table). No existing file
touched; nothing committed.

## Live constants (paper-track/state.py)
VIXM_INSTRUMENT 'VIXY'; entry VIX < 18.0 and VIX/VIX3M <= 1.0 (VIXM_EXIT_RATIO, used for both entry and exit); exit when VIX/VIX3M > 1.0;
fade VIXM_FADE 0.25 (VIX <= 0.75 x its high since entry); stress floor VIXM_MIN_VOL 0.20 on plain 30d QQQ realized vol (>=); VIXM_CASH_SHARE 0.35;
off in ungated D2 (VIXM_OFF_D_ZONES ('D2',)).

## Baselines reproduced (cap 2.0, VIXY 35%, live trigger): all match the references
real 51.1% / 2.100 / -16.5% (equals harness.run exactly); late 52.0 / 2.029 / -20.1; oos 22.6 / 0.963 / -16.4; joined 42.7 / 1.690 / -20.1.
Sleeve held (share of sessions / spells): real 8.5% / 30; late 8.6% / 31; oos **1.4% / 4**; joined 6.5% / 35. The oos window therefore says almost
nothing about the sleeve (a no-sleeve book is +0.014 Sharpe there). No-sleeve book: real 45.2 / 1.932 / -19.3; joined 39.0 / 1.582 / -20.4.

## Part 1: weight (live trigger). Sharpe (CAGR %) [max DD %]; full metrics in run.log
| w | real | late | oos | joined | worst sleeve day (% NAV) |
|---|---|---|---|---|---|
| 0 | 1.932 (45.2) [-19.3] | 1.868 (46.2) [-20.4] | 0.977 (23.0) [-16.4] | 1.582 (39.0) [-20.4] | 0 |
| 25 | 2.065 (49.4) [-16.6] | 1.995 (50.4) [-20.1] | 0.966 (22.7) [-16.4] | 1.665 (41.6) [-20.1] | -1.55 |
| 30 | 2.083 (50.2) [-16.5] | 2.013 (51.2) [-20.1] | 0.965 (22.7) [-16.4] | 1.678 (42.2) [-20.1] | -1.86 |
| **35 live** | 2.100 (51.1) [-16.5] | 2.029 (52.0) [-20.1] | 0.963 (22.6) [-16.4] | 1.690 (42.7) [-20.1] | -2.17 (2024-09-09) |
| 40 | 2.113 (51.9) [-16.5] | 2.044 (52.9) [-20.1] | 0.962 (22.6) [-16.4] | 1.701 (43.3) [-20.1] | -2.48 |
| 50 | 2.131 (53.5) [-16.5] | 2.065 (54.5) [-20.1] | 0.960 (22.5) [-16.4] | 1.718 (44.3) [-20.1] | -3.10 |
| 60 | 2.140 (55.1) [-16.5] | 2.076 (56.1) [-20.1] | 0.957 (22.4) [-16.4] | 1.731 (45.3) [-20.1] | -3.73 |
| 75 | 2.136 (57.5) [-16.5] | 2.079 (58.5) [-20.1] | 0.954 (22.3) [-16.4] | 1.740 (46.9) [-20.1] | -4.66 |
| 100 | 2.098 (61.4) [-19.4] | 2.054 (62.4) [-20.1] | 0.948 (22.2) [-16.4] | 1.736 (49.3) [-20.1] | -6.21 |
| VIXM 75 | 2.086 (50.0) | 2.017 (51.0) | 0.961 (22.6) | 1.678 (42.0) | -1.59 |
Sharpe rises monotonically with weight up to about 60-75% on real/late/joined, is flat-to-slightly-down on oos (sleeve was a small net loser there), max DD does not
change from 30% to 75% (the worst drawdown is not a sleeve episode), and w=100 is worse on real (DD -19.4). Live 35% sits on the rising slope, not at a peak. Because the
sleeve's in-sample contribution is positive (+4.1 %NAV/yr on real) more of it mechanically adds return; the Sharpe gain per step is small (+0.013 at 40%, +0.031 at 50%).

## Part 2: one knob at a time (w 35%). dSharpe vs live on real / late / oos / joined; days-on real
- entry VIX: 15 -0.099/-0.096/0.000/-0.066 (3.1%); 16 -0.086; 17 -0.057/-0.055/0/-0.037 (5.5%); **18 live** (8.5%); 19 -0.046/-0.043/0/-0.029 (10.3%); 20 -0.073/-0.067/0/-0.044 (11.2%); 22 -0.189/-0.171/-0.011/-0.116; none -0.404/-0.391/-0.030/-0.271. Live 18 is a sharp local peak (both neighbours -0.05), i.e. consistent with a threshold tuned on the same years; no neighbour is better.
- entry curve (<=): 0.90 -0.064/-0.060/0/-0.041; 0.95 +0.003/+0.003/0/+0.002 (identical in practice); none = live exactly (exit 1.00 already blocks it; see PLAN). EXTRA, no curve test at all (entry and exit none): -0.186/-0.165/+0.022/-0.092, max DD -4.3pp: the curve filter matters.
- exit ratio (>): 0.95 -0.052/-0.050/0/-0.034; 1.05 -0.054/-0.046/0/-0.023 (CAGR +0.4pp but DD -0.33pp late); 1.10 -0.135/-0.123/0/-0.077 (DD -4.3pp real). Live 1.00 is the best.
- fade: 15% -0.031/-0.030/+0.010/-0.018; 20% +0.011/+0.010/0.000/+0.007; 25% live; 30% -0.016/-0.015/0/-0.010; 40% and off -0.014/-0.014/0/-0.009. Flat: all within about +/-0.03.
- stress floor: none +0.019/+0.016/-0.021/+0.004 (sleeve on 18.7% real, 30.9% oos; oos DD -1.29pp); 15% -0.004/-0.003/-0.092/-0.029 (oos DD -6.0pp); 18% -0.063/-0.060/-0.018/-0.045; 22% -0.037/-0.038/+0.009/-0.026; 25% -0.126/-0.123/+0.014/-0.082. Live 20% is a local peak; removing the floor is the only knob move that helps real, but it hurts oos (the only window where the sleeve is allowed on calm-but-up markets).
- off in D2: on vs off identical Sharpe (real 0.000, joined -0.003), CAGR -0.13pp: noise.

## Part 3 (joint): entry VIX {16..20} x stress floor {15,18,20,22} x weight {25,35,50}: 60 cells
Knob spread ranking: entry VIX 0.337, floor 0.116, exit ratio 0.106, entry ratio 0.055, fade 0.033. No joint cell beats live on real/late/joined with oos not lower,
except the pure-weight column (floor 20, VIX 18). Best plateau (min over cell and its axis neighbours of mean dSharpe real/late/joined) is **w50 with the live trigger** (+0.013); every cell
that moves the trigger off live values is below live on Sharpe on all four windows except some oos cells with the sleeve nearly off (0.1% days-on, meaningless). Best-of-grid by own mean dSh: w50 +0.032, then
w50 floor22 -0.002, i.e. nothing in the trigger direction.

## Part 4: NAV cap (sleeve = min(35% of cash leg, c x NAV)), live trigger
| c | real Sharpe / CAGR / DD | worst sleeve day (real/joined) | dSh real/joined | dCAGR pp real/joined |
|---|---|---|---|---|
| none | 2.100 / 51.1 / -16.5 | -2.17 | | |
| 30 | 2.093 / 50.5 / -16.5 | -1.98 | -0.007/-0.007 | -0.54/-0.35 |
| 25 | 2.084 / 49.9 / -16.6 | -1.64 / -1.65 | -0.017/-0.014 | -1.13/-0.75 |
| 20 | 2.070 / 49.2 / -17.2 | -1.31 | -0.030/-0.025 | -1.82/-1.21 |
| 15 | 2.050 / 48.4 / -17.7 | -0.98 | -0.050/-0.039 | -2.68/-1.76 |
| 10 | 2.023 / 47.4 / -18.2 | -0.65 | -0.077/-0.057 | -3.62/-2.40 |
Max held sleeve weight in the history is 37.0% of NAV; in the 11-year real sample the worst sleeve day was only -2.17% of NAV (2024-09-09, VIXY about -6%).
Only 1 of the 21 VIXY days of -10% or worse in the real window (2025-05-27, -10.0%) fell on a day the sleeve was held, at 5.8% of NAV (-0.58%). The latch is off after spikes (VIX > VIX3M),
so the "10-15% unwind while a third of the account is in VIXY" case has not occurred in this history; at 37% of NAV a -15% day would be -5.6% NAV (hypothetical arithmetic, not a backtest result).
Max DD is deeper with a tight cap only on the real window (c=10: -1.68pp, c=20: -0.61pp); late and joined max DD (the 2020-type drawdown) is unchanged by any cap.

## Live cell, real window: spells
30 spells, 2015-11-03..2026-11-16 (the last, entered 2026-11-11, is still open: +5.36 %NAV in 3 days). Total sleeve contribution +44.8 %NAV (+4.07/yr) before cost; 17 wins / 13 losses (57%);
mean spell +1.49 %NAV, median +0.25; mean length 7.9 days. Exits: curve 10, stress floor 11, fade 5, D2 gate 3, still open 1 (full list in run.log). Concentration: best 1 spell (2026-11-04..05, VIXY +29.7% in one day, +10.4 %NAV) = 23% of the net total;
best 3 (adds 2021-12-23 +7.6, 2024-07-31 +6.0) = 54%; best 5 = 77%. With the best 3 removed the sleeve still adds +20.8 %NAV over 11 years (+1.9/yr); approximate book with those spells' P&L stripped: 47.9% / 2.022 / -16.5 vs no-sleeve 45.2 / 1.932 / -19.3 and live 51.1 / 2.100 / -16.5.

## Robustness (shortlist: live, 25, 50, 75, 60, 100, 40, cap20)
- Halves / ex-2020 dSharpe vs live: w40, 50, 60 are positive in both halves of real and joined and ex-2020 (w50: real +0.019/+0.052/+0.036, joined +0.019/+0.029/+0.031); w75 too; w100 is negative in joined second half (-0.021); w25 and cap20 negative everywhere.
- Lag +1 session on the sleeve signal: live loses little (real 2.091, joined 1.688). dSharpe vs live-with-lag: w50 +0.017 real / +0.023 joined; w60 +0.014/+0.029; w40 +0.009/+0.010; w75 -0.010 real.
- 5 bp one-way on sleeve trades: live 2.098 real; the weight differences barely change (w50 +0.031, w60 +0.039).
- Block bootstrap (2,000 paths, 20-session blocks, paired vs live), P(dSharpe<=0) real / joined: w40 0.04/0.01; w50 0.07/0.02; w60 0.12/0.04; w75 0.23/0.09; w100 0.46/0.21; w25 0.99/0.99; cap20 0.92/0.96. Median dMaxDD for w40-75 is 0 (same worst drawdown); w100 -0.68pp real.
- Concentration: dropping the live cell's best 1 / best 3 spells from both books, w50's advantage stays (+0.037 / +0.020), w60 (+0.053 / +0.028), w40 (+0.014 / +0.008): it does not hinge on one event, but shrinks.

## Reading rule outcomes (PLAN.md, pre-registered)
- **Weight.** "35% is fine" is NOT met: live is 0.040 below the best weight on real (60%) and 0.050 on joined (75%), above the 0.03 tolerance (the second clause is met: no neighbour beats live by >0.02 on both oos and late). Weights 40, 50 and 60 pass every clause of "worth proposing"
  (Sharpe up on real/late/joined, oos within -0.006, no deeper DD on any window, plateau, both halves and ex-2020, bootstrap P<0.10 on joined; 75 fails only the plateau test because 100 is below live on real; 100 fails). Magnitude is small: +0.013 / +0.031 / +0.040 Sharpe on real, CAGR +0.8 / +2.5 / +4.1 pp, and the worst sleeve day grows from -2.17% to -2.48 / -3.10 / -3.73% of NAV.
  A best cell picked from an 11-point grid is biased upward and the gains come from a sleeve whose in-sample mean is positive on a few big spells; the oos window (1.4% days-on) cannot confirm it. Reading: 35% is not optimal; a modestly larger weight (about 40-50%) looks like a plateau, not a spike, but the evidence is weak-to-moderate, and w50 would raise the worst sleeve day by 43%.
- **Triggers.** No trigger value passes (the neighbours of live are below live or inside noise; fade 20% and entry-ratio 0.95 are inside noise and fail the plateau test). Entry VIX 18, the exit ratio 1.00 and the 20% stress floor are each local peaks with both neighbours worse, which is the signature of in-sample tuning, but there is no better value to move to. No change.
- **Pure risk trade-offs (flag only, not proposals).** w=25: worst sleeve day -1.55% (29% smaller), max DD unchanged, CAGR -1.67pp real / -1.08 joined, Sharpe -0.035/-0.025. NAV cap 25%: worst sleeve day -1.64%, DD -0.07pp, CAGR -1.13/-0.75pp. NAV cap 20%: -1.31% (40% smaller), real DD 0.61pp deeper, CAGR -1.82/-1.21pp, Sharpe -0.030/-0.025. Caps 15% and 10% cost -2.7 / -3.6pp CAGR and deepen real DD by 1.1 / 1.7pp. No cell cuts the sleeve loss without a Sharpe cost, and in this history the loss avoided is theoretical (max historical sleeve day -2.17% NAV).

## Caveats / things not done
- ~110 cells tested; picks from the grid are biased upward; Sharpe differences under about 0.03 are within bootstrap noise (live vs w25/w40 median differences are well inside the Sharpe sampling error of a 11-year track).
- real and late are the same market years (not independent); oos has 4 sleeve spells, so it cannot support or contradict any weight (its tiny negative slope with weight is noise-level, -0.004 at 50%).
- Entry curve "none" is identical to live by construction (PLAN); the EXTRA cell shows the no-curve case.
- The sleeve contribution excludes trading cost; the 5 bp test includes it. The best-3-spells-removed book subtracts daily sleeve P&L only (approximation).
- The latest session 2026-11-16 uses VIXY close from the yahoo file (19.56); the live sleeve entered 2026-11-11 and its 3 days are part of the real window.
