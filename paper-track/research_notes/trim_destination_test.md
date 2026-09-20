# Research line `trim_destination_test` (2026-09-20): should the extension trim's freed weight go to SPMO instead of cash?

Research only. Nothing here is applied; the discipline in BRIEFING.md (ADDENDUM 2026-09-10) binds. No commits, no edits
to any protected file, no new data files, no trades. Script: `paper-track/trim_destination_test.py` (run from the repo
root; `TDT_STAGE=all|grid|perm|deep`, `TDT_NPERM` default 1000, `TDT_PROCS` default 4; 63 s on 4 cores). Full log:
`paper-track/research_notes/trim_destination_test_run.log`. Standard library only.

**Owner's question.** The graded extension trim in effective state A scales ALL four risky legs toward cash: at 0/1/2/3
votes the A row (50 % SPMO / 50 % TQQQ) is held at x1 / x2/3 / x1/3 / x0 with the freed weight in BOXX. Was moving the
trimmed exposure into SPMO (the unlevered core) instead of cash ever tested?

## 0. Summary and verdict

- **Prior record: no.** Every trim variant in STRATEGY.md sends the freed weight to cash: the single 200d>15% -> x0.5 rule
  and the graded three-window form ("Extension trim"), the step sweep 0.25 / 1/3 / 1/.5/.25/0 / 1/.5/0/0 / 1/0/0/0 and
  the 4- and 5-window sets ("Leverage under the trim; trim step sweep"), the r4 floors (.10/.15/.25), and the z-scored
  trim (Line 2 of the volatility lines). The nearest relatives moved CONFIRMED-trend A weight toward the core rather than
  overheated-trend weight: the 2026-09-01 "state-A confidence" line (de-lever A in its most-confirmed weeks; "Sharpe
  declines MONOTONICALLY as the confident-weeks weight is de-levered away from 80/20 (1.111 at 80/20 -> 1.054 at the fully
  de-levered 100/0)"; REJECTED) and the micro overlay's A-half (88/12 when the 30/150 classifier agrees; "a de-lever of
  state A -- a risk dial, not an edge"; DISABLED 2026-09-02). Neither is this question: they asked whether to hold more
  core on the strongest A days; this asks whether the core is a better parking place than cash on the OVERHEATED A days.
- **Pre-registered grid, fixed before any result: exactly the owner's 7 schedules** (live S0 + 6 candidates S1..S6; rungs
  in section 1), no threshold changes, vol target on top as live. A "no trim" row is printed as a labelled reference
  only. Harness: the CURRENT live design (state-D gate on, E = 100 % cash) built by override on `d_substate_fresh`,
  exactly as `e_outcome_explore.py` part III did, and **asserted to reproduce proxy 25.46 % / 1.071 / -27.0 % (S 1.399,
  H 0.825) and real daily 37.30 % / 1.475 / -18.6 %** before scoring.
- **Result: every schedule that parks the freed weight in SPMO at 2 or 3 votes loses to live in both proxy eras and on the
  real rows** (S1 -0.048 F / -0.063 S / -0.038 H / -0.046 real; S2, S3, S4, S5 between -0.02 and -0.06 everywhere). The
  one schedule that beats live, **S6 "core then cash steps" (100 % SPMO at 1 vote, 50/50 SPMO-cash at 2, cash at 3)**, does
  so by +0.008 full / +0.007 search / +0.009 holdout / +0.002 real -- the size of the E-row study's "inside noise" band
  (0.013) -- with real CAGR -0.31 pp, real MaxDD 0.8 pp deeper, and it beats its exposure-matched control by +0.011 /
  +0.011 / +0.010 (real +0.005).
- **Why:** the vote days are days on which the core does not earn its drift. Mean next-session core return on effective-A
  days: 0 votes +9.1 bp/d (t 4.8); 1 vote -0.8, 2 votes -2.0, 3 votes -3.9 bp/d (t -0.1 / -0.3 / -0.6), against cash at
  +0.7 bp/d. Real SPMO: +9.5 bp/d at 0 votes, +2.0 / -1.7 / -1.0 at 1/2/3. Core-minus-cash is negative or flat at every
  vote level on every harness except the 1-vote rung in the search era (+0.4 t) -- which is exactly the one rung S6
  exploits.
- **Permutation** (vote labels shuffled among the 3909 effective-A days, counts kept, 1000 draws, paired: live and the six
  candidates both re-scored on the same shuffled labels): best-of-6 full-period gain vs live, null median +0.083, 95th
  +0.122; real best +0.008 (S6) **p = 1.000**. Both-era min gain: null median +0.069, 95th +0.108; real +0.006, p = 0.998.
  The real gain sits BELOW the null's minimum (+0.027; 0 of 1000 draws at or below it) -- under random labels an SPMO
  destination beats cash by ~0.08 because random A days carry the core's drift; the actual vote days do not. The label is
  strongly informative, in the direction that favours cash.
- **Bootstrap (S6):** proxy vs live Sharpe 95 % CI [-0.011, +0.029] P(<=0) 0.21; vs matched control [-0.012, +0.031]
  P(<=0) 0.15; real vs live [-0.083, +0.082] P(<=0) 0.48. Log-return vs control P(<=0) 0.99 (S6 earns LESS than live
  levered to its exposure). LORO: +0.004 to +0.011 in every drop (keeps sign, never leaves noise). One-session lag: S6 vs
  live-lagged F -0.002 / S -0.017 / H +0.009 / real -0.023. 20 bp cost: -0.021 / -0.025 / -0.017 vs live, real -0.031.
- **Verdict against the project bar:** S1-S5 fail every rung. S6 passes both-era and the matched control on point estimates
  only; it fails the bootstrap (P 0.15-0.48), fails the permutation (p ~ 1.0), loses under a one-session lag and at 20 bp,
  and lowers real CAGR (-0.31 pp); its one unambiguous plus is a shallower MaxDD (proxy -26.6 % vs -27.0 %, real -17.8 %
  vs -18.6 %), bought by holding 50 % cash instead of 33 % at 2 votes. Nothing here argues for a destination other than
  cash. The owner decides.
- Candidate count this line: 6 pre-registered + live + 1 labelled reference (no-trim) + 6 exposure-matched controls.
  Cumulative with earlier lines: 240 + 890 + 41 (+ E lines) + 6.

## 1. Setup and prior evidence

**Prior evidence, cited.** STRATEGY.md "Extension trim (added 2026-09-06)": "each window whose gap exceeds its threshold is
one vote; the four risky legs are scaled by 1 - 1/3 x votes (x2/3 / x1/3 / x0 -- at three votes the A row is 100 % BOXX)
... the trim only ever reduces exposure"; "Trim size is monotone -- x0.75 through x0.0 all improve -- so 0.5 was a
deliberately non-corner pick"; costs "post-crash melt-ups: proxy 2009 -18pp, 2020 -4.5pp; real 2023 -3pp, 2024 -4pp;
gets it back in 2007, 2010-11, 2018, 2020 (real +10), 2024-26". "Leverage under the trim; trim step sweep (2026-09-06)":
the multiplier schedules 1/.75/.5/.25, 1/.67/.33/0, 1/.5/.25/0, 1/.5/0/0, 1/0/0/0 -- every one a multiplier on all four
risky legs with the remainder in cash; "Response is monotone in trim depth ... permutation over the 8 schedules (vote
labels shuffled among effective-A days, counts kept, 200 shuffles) gives p = 0.00"; the r4 floors "pay in melt-ups (2009
+1.6, 2023 +2.1 proxy) and give it back at tops (2003 -2.1, 2007 -1.3, 2024 -1.9, 2026 -1.8)". "Block bootstrap and
leave-one-regime-out (2026-09-07)": the trim's Sharpe edge +0.143, CI [+0.025, +0.266], P(<=0) 0.007, survives every LORO
drop (+0.121 without the SPMO era). The z-scored trim (volatility Line 2) changed WHEN the trim fires, not where the
weight goes. The "state-A confidence" line (four signals; composite; `composite_turnover_cost.py`) and the micro
overlay's A-half (88/12) both moved CONFIRMED-trend A weight toward the core and were rejected / disabled: "trimming its
return specifically in its most-confirmed weeks removes some of the portfolio's best Sharpe contribution". The "Extension
trim" section itself draws the line: "those signals ... asked whether to de-lever CONFIRMED trend; this trims OVERHEATED
trend." So: destination = cash was never varied; destination = core was only ever tested on the wrong days.

**Schedules** (A-row weights (SPMO, TQQQ, cash) at 0 / 1 / 2 / 3 votes; exact fractions; S4 verbatim from the
pre-registration, 7/12 / 1/3 / 1/12 and 7/12 / 1/6 / 1/4):

| id | rungs | idea |
|---|---|---|
| S0 LIVE | (50,50,0) / (33.3,33.3,33.3) / (16.7,16.7,66.7) / (0,0,100) | x2/3, x1/3, x0 to cash |
| S1 | (50,50,0) / (75,25,0) / (100,0,0) / (100,0,0) | TQQQ-first, never cash |
| S2 | (50,50,0) / (75,25,0) / (100,0,0) / (50,0,50) | TQQQ-first then cash |
| S3 | (50,50,0) / (75,25,0) / (100,0,0) / (0,0,100) | TQQQ-first then all cash |
| S4 | (50,50,0) / (58.3,33.3,8.3) / (58.3,16.7,25) / (50,0,50) | half-and-half |
| S5 | (50,50,0) / (100,0,0) / (100,0,0) / (100,0,0) | core-only at any vote |
| S6 | (50,50,0) / (100,0,0) / (50,0,50) / (0,0,100) | core then cash steps |
| REF | (50,50,0) at every vote | no trim -- reference only, not a candidate |

**Harness.** `d_substate_fresh` imported with `DSF_STAGE=none` (proxy `rows`, `vt`, `run`/`run_count`, `evaluate_full`,
the real daily mirror's data `RPX/RQQQ/RDAYS`, `block_bootstrap.boot` (2000 draws), `REGIMES`). Because that module pins
`state.TARGET_WEIGHTS['E']` back to 50 % XLU and neither its proxy `BASE` nor `simulate_real` applies the D gate, the
current live design is built by override: proxy rows with `state == 'D'` and `state.d_gate_active(st, breadth_pct,
gaps[200])` -> `vt(cash)`, rows with `state == 'E'` -> `vt(cash)`, every other row the harness's own live target; on
effective-A rows the schedule's rung for `state.extension_votes(eff, gaps)` under `vt`. Breadth is
`breadth_tracker.relative_strength_series` + `trailing_pct` on `data/QQEW_daily_ext.csv` (first value 2006-05-02, as
d_pair_test). The real daily mirror precomputes `compute_states / compute_fast_states / compute_extension_gaps /
realized_vol_live / d_gate_active` per session and runs `needs_rebalance` with the regime key (eff, votes, gate) and 4 bp
one-way cost, i.e. `monthly_returns.simulate` mechanics; the S0 path is asserted equal, day by day, to
`target_weights_with_voltarget(..., d_gate=)` with the E override. The live schedule is asserted equal to the harness's
own trimmed A row on every A day. Sharpe: zero-rate (`drift_band_test.annual_stats`), everywhere.

| harness | live CAGR / Sharpe / MaxDD | S Sharpe | H Sharpe | exposure | reb/yr | rows |
|---|---|---|---|---|---|---|
| proxy 2000-07-03..2026-08-26 | 25.46 % / 1.071 / -27.0 % | 1.399 | 0.825 | 62.2 % | 47.9 | 6575 (gated D 240, E 380) |
| real daily 2015-11-02..2026-09-04 | 37.30 % / 1.475 / -18.6 % | -- | -- | 67.2 % | 45.3 | 2725 sessions |

**Effective-A days by vote count** (the only days any schedule touches; rung 0 is identical in all seven):

| | A days | 0 votes | 1 vote | 2 votes | 3 votes | share at 1/2/3 | of all days |
|---|---|---|---|---|---|---|---|
| proxy full | 3909 | 2897 | 322 | 331 | 359 | 8.2 / 8.5 / 9.2 % | 15.4 % |
| proxy search 2015-11+ | 1848 | 1371 | 137 | 136 | 204 | 7.4 / 7.4 / 11.0 % | 17.5 % |
| proxy holdout ..2015-10 | 2061 | 1526 | 185 | 195 | 155 | 9.0 / 9.5 / 7.5 % | 13.9 % |
| real daily 2015-11+ | 1854 | 1377 | 137 | 136 | 204 | 7.4 / 7.3 / 11.0 % | 17.5 % |

So the schedules differ from live on 1012 proxy days (477 search, 535 holdout) and 477 real days. The 3-vote rung is the
largest in the search era (204 days, 11 % of A days), the smallest in the holdout (155).

## 2. The table

Proxy full / search / holdout (CAGR / Sharpe / MaxDD), exposure, rebalances/yr; deltas vs live; real daily.

| id | CAGR | Sharpe | MaxDD | exp | reb | S Sharpe | H Sharpe | dS_F | dS_S | dS_H | real CAGR | real Sharpe | real MaxDD | real exp | real reb | real dSh |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **S0 live** | 25.46 % | 1.071 | -27.0 % | 62.2 % | 47.9 | 1.399 | 0.825 | -- | -- | -- | 37.30 % | 1.475 | -18.6 % | 67.2 % | 45.3 | -- |
| S1 | 24.70 % | 1.023 | -27.5 % | 71.9 % | 47.3 | 1.336 | 0.787 | -0.048 | -0.063 | -0.038 | 37.04 % | 1.428 | -18.3 % | 78.9 % | 47.6 | -0.046 |
| S2 | 24.95 % | 1.041 | -27.5 % | 69.4 % | 49.3 | 1.364 | 0.798 | -0.030 | -0.034 | -0.027 | 37.12 % | 1.450 | -18.3 % | 75.4 % | 46.9 | -0.024 |
| S3 | 25.09 % | 1.049 | -27.5 % | 66.8 % | 48.7 | 1.375 | 0.804 | -0.022 | -0.023 | -0.021 | 37.04 % | 1.455 | -18.3 % | 71.8 % | 46.0 | -0.020 |
| S4 | 25.04 % | 1.040 | -27.9 % | 67.8 % | 49.1 | 1.363 | 0.797 | -0.031 | -0.036 | -0.028 | 37.19 % | 1.447 | -18.5 % | 73.9 % | 46.5 | -0.028 |
| S5 | 24.76 % | 1.036 | -26.6 % | 71.9 % | 43.5 | 1.342 | 0.804 | -0.035 | -0.056 | -0.021 | 36.72 % | 1.431 | -17.8 % | 78.9 % | 47.6 | -0.044 |
| **S6** | 25.41 % | **1.079** | -26.6 % | 64.4 % | 48.2 | **1.405** | **0.834** | **+0.008** | **+0.007** | **+0.009** | 36.99 % | **1.477** | -17.8 % | 69.6 % | 45.5 | **+0.002** |
| REF no trim | 23.06 % | 0.907 | -30.7 % | 71.9 % | 37.7 | 1.176 | 0.699 | -0.164 | -0.223 | -0.127 | 34.89 % | 1.250 | -20.4 % | 78.9 % | 48.0 | -0.225 |

Search-era CAGR / MaxDD: live 37.14 % / -25.3 %, S6 36.96 % / -25.0 %, S1 36.27 % / -25.4 %; holdout: live 17.84 % /
-27.0 %, S6 17.88 % / -26.6 %, S1 17.15 % / -27.5 %. Reading: the trim itself is worth +0.164 Sharpe over no trim on this
harness (+0.225 real); the six destinations span 1.023..1.079 around live's 1.071. Ordering by how much SPMO is held at
2-3 votes: S1 = S5 (100 % core at 3 votes) worst; S2 / S4 (50 % core at 3 votes) next; S3 (core at 1-2 votes, cash at 3)
-0.022; S6 (core at 1 vote only) +0.008. **The more core is held at the deeper rungs, the worse; the only rung on which core
is not clearly worse than cash is the 1-vote rung** (section 3, attribution). No candidate raises real CAGR (S6 -0.31 pp,
S4 -0.11 pp, S5 -0.58 pp). MaxDD: S5 and S6 (the two schedules that hold NO TQQQ at any vote) are shallower than live on both
harnesses (proxy -26.6 % vs -27.0 %, real -17.8 % vs -18.6 %); S1-S4 (which still hold TQQQ at 1-2 votes) are 0.5-1.0 pp deeper on the
proxy (-27.5 / -27.9 %) and 0.1-0.3 pp shallower on real. (In the log the "DD" delta column is candidate minus live, so a positive number is a shallower
drawdown.)

## 3. Controls, attribution, permutation

**Exposure-matched controls** (live flat de-levered / levered, all four risky legs x k every day, to the candidate's
average exposure; k > 1 because every SPMO destination holds MORE capital than live):

| id | proxy exp | k | control F / S / H | candidate - control F / S / H | real exp | k | control real Sh / MaxDD | cand - control real |
|---|---|---|---|---|---|---|---|---|
| S1 | 71.9 % | 1.157 | 1.060 / 1.384 / 0.816 | -0.037 / -0.048 / -0.030 | 78.9 % | 1.176 | 1.458 / -21.9 % | -0.030 |
| S2 | 69.4 % | 1.116 | 1.063 / 1.387 / 0.820 | -0.022 / -0.022 / -0.022 | 75.4 % | 1.123 | 1.465 / -20.9 % | -0.014 |
| S3 | 66.8 % | 1.074 | 1.066 / 1.390 / 0.822 | -0.017 / -0.015 / -0.018 | 71.8 % | 1.069 | 1.469 / -19.9 % | -0.014 |
| S4 | 67.8 % | 1.091 | 1.065 / 1.388 / 0.822 | -0.025 / -0.026 / -0.024 | 73.9 % | 1.100 | 1.467 / -20.4 % | -0.020 |
| S5 | 71.9 % | 1.157 | 1.060 / 1.384 / 0.816 | -0.024 / -0.042 / -0.013 | 78.9 % | 1.176 | 1.458 / -21.9 % | -0.028 |
| S6 | 64.4 % | 1.036 | 1.069 / 1.394 / 0.824 | +0.011 / +0.011 / +0.010 | 69.6 % | 1.036 | 1.472 / -19.1 % | +0.005 |

Only S6 beats its control, and by about one hundredth of Sharpe on every slice. S1-S5 are worse than simply levering live
up by 7-18 % -- the extra capital they hold is held on the wrong days.

**Per-rung attribution** (mean next-session return on effective-A days by vote count; t = mean / s.e.):

| harness | votes | n | core bp/d (t) | TQQQ bp/d (t) | cash bp/d | core - cash t |
|---|---|---|---|---|---|---|
| proxy full | 0 | 2897 | +9.1 (4.78) | +25.1 (4.42) | 0.7 | +4.39 |
| proxy full | 1 | 322 | -0.8 (-0.11) | -4.7 (-0.22) | 0.9 | -0.24 |
| proxy full | 2 | 331 | -2.0 (-0.31) | -7.3 (-0.38) | 0.4 | -0.37 |
| proxy full | 3 | 359 | -3.9 (-0.58) | -13.5 (-0.68) | 0.7 | -0.69 |
| proxy search | 1 / 2 / 3 | 137 / 136 / 204 | +4.7 / -2.9 / -3.0 | +10.8 / -10.9 / -11.8 | 1.4 / 0.8 / 1.1 | +0.38 / -0.34 / -0.44 |
| proxy holdout | 1 / 2 / 3 | 185 / 195 / 155 | -4.9 / -1.3 / -5.0 | -16.2 / -4.8 / -15.9 | 0.5 / 0.2 / 0.2 | -0.52 / -0.19 / -0.55 |
| real daily (SPMO) | 0 | 1377 | +9.5 (3.85) | +27.7 (3.67) | 0.9 | +3.49 |
| real daily (SPMO) | 1 / 2 / 3 | 137 / 136 / 204 | +2.0 / -1.7 / -1.0 | +9.8 / -10.7 / -10.9 | 1.4 / 0.8 / 1.1 | +0.07 / -0.25 / -0.24 |

The core's whole A-day edge (+9 bp/d, t 4-5) is earned at 0 votes. On vote days the core's mean return is at or below cash
on every harness and every rung except the 1-vote rung in the search era (+4.7 bp/d proxy, +2.0 bp/d SPMO, both t < 0.5).
That single rung is the entirety of S6's edge, and it is the rung the holdout contradicts (-4.9 bp/d, t -0.52). There is no
rung on which the unlevered core is a statistically better parking place than cash; TQQQ's mean on vote days is 3x worse,
which is what the existing trim already removes.

**Max-statistic permutation** (proxy; vote labels shuffled among the 3909 effective-A days, counts kept, 1000 draws, seed
20260920, 4 workers). Per draw: live and all six candidates re-scored on the SAME shuffled labels (paired), statistic =
max over S1..S6 of candidate Sharpe minus live Sharpe; full-period, and both-era min(dS_search, dS_holdout) with sliced
Sharpes as in d_pair_test.

| statistic | null median | null 95th | null 99th | real best | p (null >= real) | null min / 1st pct | draws <= real |
|---|---|---|---|---|---|---|---|
| full-period gain vs live | +0.083 | +0.122 | +0.142 | +0.008 (S6) | **1.000** | +0.027 / +0.039 | 0.000 |
| both-era min gain vs live | +0.069 | +0.108 | +0.125 | +0.006 (S6) | **0.998** | -0.002 / +0.017 | 0.002 |

Under the null the best SPMO destination beats trim-to-cash by ~0.08 Sharpe, because on RANDOM A days the core carries
its +9 bp/d drift and cash forgoes it. The real gain (+0.008) is below the null's minimum: **the actual vote days are days
on which the core does not earn its drift, so the vote label is informative -- and informative in the direction that
favours cash as the destination.** The r2-style unpaired form (candidates under shuffled labels vs the FIXED real live
Sharpe: null 95th -0.158, p = 0.000) only re-confirms that the trim itself works, which was already established; it says
nothing about the destination and is printed for reference only.

## 4. Deep block: S6 (best on every criterion -- proxy full, real, both-era)

S6 = 100 % SPMO at 1 vote, 50 % SPMO / 50 % cash at 2, cash at 3. Proxy 25.41 % / 1.079 / -26.6 % (S 1.405, H 0.834, exp
64.4 %), real 36.99 % / 1.477 / -17.8 % (exp 69.6 %); matched control k 1.036 on both harnesses.

**(a) Circular block bootstrap, 2000 draws** (Sharpe difference; log-return difference in pp/yr):

| comparison | block | Sharpe 95 % CI | P(<=0) | log-return CI | P(<=0) |
|---|---|---|---|---|---|
| proxy vs live | 20d | [-0.012, +0.028] | 0.205 | [-0.52, +0.43] | 0.568 |
| proxy vs live | 60d | [-0.011, +0.029] | 0.209 | [-0.53, +0.45] | 0.548 |
| proxy vs matched control | 20d | [-0.009, +0.032] | 0.154 | [-1.33, -0.06] | 0.986 |
| proxy vs matched control | 60d | [-0.012, +0.031] | 0.151 | [-1.37, -0.07] | 0.986 |
| real vs live | 20d | [-0.081, +0.078] | 0.467 | [-2.15, +1.52] | 0.585 |
| real vs live | 60d | [-0.083, +0.082] | 0.484 | [-2.20, +1.66] | 0.611 |
| real vs matched control | 20d | [-0.072, +0.078] | 0.426 | [-3.13, +0.68] | 0.889 |
| real vs matched control | 60d | [-0.081, +0.090] | 0.459 | [-3.29, +0.91] | 0.871 |

No interval excludes zero for Sharpe; the real-daily comparison is a coin flip (P 0.47-0.48). The one interval that does
exclude zero is the log-return vs the matched control (proxy, P(<=0) 0.986): S6 EARNS LESS than live levered to the same
average exposure, i.e. its tiny Sharpe gain comes from lower variance on the 2-vote days (50 % cash instead of 33 %), not
from the core earning anything at 1 vote.

**(b) Leave-one-major-regime-out** (Sharpe difference with the window removed):

| drop | proxy vs live | proxy vs control | real vs live | real vs control |
|---|---|---|---|---|
| dot-com 2000-2002 | +0.004 | +0.006 | -- | -- |
| GFC 2007-2009 | +0.010 | +0.012 | -- | -- |
| COVID 2020 | +0.011 | +0.014 | +0.012 | +0.015 |
| 2022 bear | +0.009 | +0.011 | +0.003 | +0.006 |
| whole SPMO era 2015-11+ | +0.009 | +0.010 | -- | -- |

Sign kept in every drop, magnitude never above +0.015: not one episode, and never out of noise. Dropping the dot-com years
(the largest holdout vote cluster, 2003) halves it.

**(c) One-extra-session lag** (vote count from the previous close, applied to candidate AND live so the comparison stays
paired): live lagged 23.83 % / 1.021 / -28.1 % (S 1.366, H 0.761; real 36.11 % / 1.446 / -18.9 %); S6 lagged 23.52 % /
1.019 / -27.3 % (S 1.350, H 0.770; real 35.03 % / 1.423 / -18.5 %). **S6 lagged vs live lagged: F -0.002, S -0.017, H
+0.009, real -0.023.** Against unlagged live (d_pair_test convention): -0.052 / -0.049 / -0.055 / real -0.052, almost all
of it the lag's cost to the trim itself (live loses 0.050 to its own lag; the trim is a same-close rule and this confirms
it must stay one). The destination edge does not survive a one-day lag.

**(d) 20 bp one-way cost** (both sides): live proxy 18.56 % / 0.833 / -33.7 % (S 1.157, H 0.590); S6 17.80 % / 0.813 /
-33.3 % (S 1.131, H 0.573): vs live F -0.021, S -0.025, H -0.017; vs the matched control at 20 bp F -0.018, S -0.021,
H -0.016. Real: live 29.40 % / 1.219 / -21.9 %, S6 28.18 % / 1.187 / -21.0 % (-0.031). S6's rungs are bigger moves (50/50
-> 100/0 is L1 drift 1.0 where live's x2/3 is 0.33; 48.2 vs 47.9 rebalances/yr), so the edge reverses as costs rise.

## 5. Per-year returns

Live vs the best two by proxy full Sharpe (S6, S3) and the no-trim reference; deltas in pp vs live. C = a year STRATEGY.md
lists as one the trim costs (2003, 2009, 2020, 2023, 2024, 2026); P = a year it says the trim pays (2007, 2010-11, 2018,
2020, 2024-26).

**Proxy (QQQ core), years on which the schedules differ** (2005, 2013-16, 2022 have no vote days and are identical):

| year | live | S6 | S3 | ref | dS6 | dS3 | dref | tag |
|---|---|---|---|---|---|---|---|---|
| 2000 | -18.9 | -18.6 | -19.1 | -19.6 | +0.4 | -0.2 | -0.7 | |
| 2001 | +6.6 | +7.3 | +6.3 | +5.6 | +0.7 | -0.3 | -0.9 | |
| 2002 | -1.7 | -0.1 | -2.7 | -5.1 | +1.6 | -1.0 | -3.4 | |
| 2003 | +75.3 | +73.7 | +75.0 | +55.4 | -1.6 | -0.3 | -19.9 | C |
| 2004 | +12.3 | +12.5 | +11.5 | +7.9 | +0.1 | -0.8 | -4.5 | |
| 2006 | +17.9 | +17.9 | +17.2 | +15.0 | -0.0 | -0.7 | -2.9 | |
| 2007 | +25.8 | +27.2 | +24.3 | +11.1 | +1.4 | -1.5 | -14.7 | P |
| 2008 | -1.6 | -0.6 | -2.1 | -3.8 | +1.0 | -0.5 | -2.2 | |
| 2009 | +54.2 | +48.4 | +57.0 | +85.0 | -5.8 | +2.8 | +30.9 | C |
| 2010 | +46.9 | +46.8 | +44.7 | +37.4 | -0.1 | -2.2 | -9.4 | P |
| 2011 | -6.4 | -5.8 | -7.2 | -8.2 | +0.7 | -0.7 | -1.7 | P |
| 2012 | +19.4 | +19.1 | +19.9 | +21.4 | -0.3 | +0.5 | +2.0 | |
| 2017 | +75.9 | +77.3 | +75.2 | +73.0 | +1.5 | -0.7 | -2.9 | |
| 2018 | +6.7 | +6.2 | +6.4 | +3.2 | -0.6 | -0.3 | -3.5 | P |
| 2019 | +53.9 | +54.7 | +53.5 | +52.1 | +0.9 | -0.4 | -1.8 | |
| 2020 | +57.0 | +53.2 | +59.6 | +68.4 | -3.8 | +2.7 | +11.5 | CP |
| 2021 | +53.2 | +53.4 | +51.5 | +47.1 | +0.1 | -1.8 | -6.2 | |
| 2023 | +74.1 | +78.0 | +70.7 | +82.3 | +3.9 | -3.3 | +8.3 | C |
| 2024 | +62.7 | +60.9 | +61.9 | +44.6 | -1.8 | -0.7 | -18.1 | CP |
| 2025 | +36.5 | +35.3 | +35.4 | +29.1 | -1.2 | -1.1 | -7.4 | P |
| 2026 | +39.2 | +38.9 | +40.2 | +29.3 | -0.3 | +1.1 | -9.8 | CP |

Sum over the trim-cost years (2003, 2009, 2020, 2023, 2024, 2026): S6 -9.3 pp, S3 +2.2 pp, no-trim +2.8 pp. Sum over the
trim-pay years (2007, 2010, 2011, 2018, 2020, 2024, 2025, 2026): S6 -5.6 pp, S3 -2.8 pp, no-trim -53.1 pp. **Holding the
core on vote days does not buy back the melt-ups.** S6 gives up 5.8 pp of 2009 and 3.8 pp of 2020 (its 2-vote rung holds
50 % cash where live holds 33 %) and takes 3.9 pp of 2023 (a 1-vote year); S3 recovers 2.8 / 2.7 pp of 2009 / 2020 (core
at 2 votes) and gives back 3.3 pp of 2023 and 2.2 pp of 2010. The no-trim reference shows what the trim's cost years
actually cost (2009 -31 pp, 2020 -11.5, 2023 -8.3) and what it saves (2003 +19.9, 2007 +14.7, 2024 +18.1, 2026 +9.8): the
destination choice moves single-digit pp inside years where the trim itself moves tens.

**Real daily (SPMO era):**

| year | live | S6 | S3 | ref | dS6 | dS3 | dref | tag |
|---|---|---|---|---|---|---|---|---|
| 2015 | -6.8 | -6.8 | -6.8 | -6.8 | 0.0 | 0.0 | 0.0 | |
| 2016 | +14.8 | +14.8 | +14.8 | +14.8 | 0.0 | 0.0 | 0.0 | |
| 2017 | +70.6 | +75.6 | +72.2 | +68.8 | +5.0 | +1.6 | -1.8 | |
| 2018 | +11.2 | +10.9 | +12.3 | +8.3 | -0.3 | +1.0 | -2.9 | P |
| 2019 | +44.2 | +44.5 | +43.5 | +42.5 | +0.3 | -0.7 | -1.7 | |
| 2020 | +60.9 | +56.1 | +63.2 | +74.6 | -4.7 | +2.3 | +13.7 | CP |
| 2021 | +45.9 | +47.0 | +43.6 | +37.0 | +1.1 | -2.3 | -8.9 | |
| 2022 | -9.2 | -9.2 | -9.2 | -9.2 | 0.0 | 0.0 | 0.0 | |
| 2023 | +60.0 | +68.8 | +63.8 | +69.4 | +8.8 | +3.7 | +9.4 | C |
| 2024 | +61.9 | +57.8 | +58.9 | +48.4 | -4.1 | -3.0 | -13.5 | CP |
| 2025 | +37.6 | +31.5 | +32.9 | +28.8 | -6.1 | -4.6 | -8.8 | P |
| 2026 | +38.6 | +36.8 | +38.2 | +29.8 | -1.8 | -0.4 | -8.8 | CP |

Real sums: trim-cost years (2020, 2023, 2024, 2026) S6 -1.8 pp, S3 +2.7 pp, no-trim +0.9 pp; trim-pay years (2018, 2020,
2024, 2025, 2026) S6 -17.0 pp, S3 -4.6 pp, no-trim -20.3 pp. S6's real-daily record is two years (2017 +5.0, 2023 +8.8)
against four (2020 -4.7, 2024 -4.1, 2025 -6.1, 2026 -1.8): the 1-vote rung paid in the two grind-up years and the deeper
cash at 2 votes cost in every other year with votes. Real CAGR ends 0.31 pp below live.

## 6. Verdict against the project bar

| candidate | both-era improvement | beats matched control (S, H) | bootstrap P(<=0) < 0.05 | permutation p < 0.05 | real CAGR not falling |
|---|---|---|---|---|---|
| S1 | fail (-0.063 / -0.038) | fail (-0.048 / -0.030) | -- | -- | fail (-0.26 pp) |
| S2 | fail (-0.034 / -0.027) | fail (-0.022 / -0.022) | -- | -- | fail (-0.18 pp) |
| S3 | fail (-0.023 / -0.021) | fail (-0.015 / -0.018) | -- | -- | fail (-0.26 pp) |
| S4 | fail (-0.036 / -0.028) | fail (-0.026 / -0.024) | -- | -- | fail (-0.11 pp) |
| S5 | fail (-0.056 / -0.021) | fail (-0.042 / -0.013) | -- | -- | fail (-0.58 pp) |
| S6 | pass on points (+0.007 / +0.009) | pass on points (+0.011 / +0.010; real +0.005) | **fail** (0.15-0.21 proxy, 0.43-0.48 real) | **fail** (1.000 / 0.998) | **fail** (-0.31 pp) |

The answer to the owner's question is now on the record: the destination of the trimmed weight has been varied across
six pre-registered schedules on both harnesses. Five are worse than live on every slice and worse than simply levering
live up to their exposure. The sixth (S6) is live's Sharpe within a hundredth on both eras and the real rows, does not
clear the bootstrap or the permutation, loses under a one-session lag and at 20 bp, and lowers real CAGR. The attribution
explains why nothing here can work: the graded trim fires on days when the core's own next-session return is at or below
the cash rate on every harness and every rung (the one exception, 1 vote in the search era, is t 0.4 and reverses in the
holdout), so there is no unlevered drift to capture by staying in SPMO -- the cash destination is not a missed opportunity,
it is the point. This is consistent with, and distinct from, the "state-A confidence" rejection: there the core was held
on the BEST A days and it cost Sharpe because those days carry the drift; here the core would be held on the WORST A days,
and it earns nothing because they do not. The owner decides; nothing is applied.
