# Research line `d_pair_test` (2026-09-19): can two (or more) of the five D-exit rules be combined?

Research only. Nothing here is applied; the discipline in BRIEFING.md (ADDENDUM 2026-09-10) binds. No commits, no edits
to any protected file, no new data files, no trades.
Script: `paper-track/d_pair_test.py` (run from the repo root; `DPT_STAGE=grid|perm|diag`, `DPT_NPERM` (default 1000),
`DPT_PROCS`). Grid 22 s, permutation 3.5 min on 4 cores, diagnostics 2.5 min. Full log:
`paper-track/research_notes/d_pair_test_run.log`. Standard library only (no numpy in this environment).

**Owner's questions.** An outside study on the real-ETF daily window (2015-10..2026-08) reported five single rules that
each improve on live when they send state D (QQQ below its 50d, above its 200d, 50d > 200d; live row 100 % QLD) to cash
on flagged days: (1) the pre-registered **breadth** gate (QQEW/QQQ 60-session change in its trailing-252 bottom quintile),
(2) **sma20>=sma60**, (3) **px>=sma100**, (4) **gap200<2%** (QQQ less than 2 % above its 200d), (5) **volratio>1.5** (10d
realised vol > 1.5x 30d). Reported actual-ETF figures (CAGR / excess Sharpe / MaxDD): live 31.42 / 1.117 / -32.89;
(1) 37.92 / 1.365 / -24.48; (2) 31.77 / 1.277 / -27.90; (3) 31.97 / 1.253 / -26.08; (4) 34.80 / 1.253 / -24.50;
(5) 35.34 / 1.257 / -24.48; constant 85 %-QLD control 30.64 / 1.147 / -29.68.
*"Is it possible to combine two?"* And, pre-registered as a scope extension before any pair result was seen: *"maybe D1,
then D2a, D2b, special cases that are worth going to cash"* -- a tree inside D where D1 = default (live) and each D2x is a
named special case; a tree of k cases is the union of k flags.

## 0. Summary and verdict

- **Pre-registered grid, fixed before any result: 41 candidates** = 5 singles + 10 pairs x {AND, OR} + all unions of 3, 4
  and 5 rules (10 + 5 + 1). Action: D -> 100 % cash on flagged days, unflagged D stays live. Controls: constant-D rows
  (QLD fraction 0..100 % in 5 % steps). No other rules, no threshold tuning. The breadth rule is
  `breadth_tracker.relative_strength_series` + `trailing_pct` verbatim on `data/QQEW_daily_ext.csv` (live reading for
  2026-09-04 reproduced: pct 0.867). QQEW starts 2006-05, so the first breadth value is 2007-07-27; on the 207 holdout D
  days before that, D stays live (AND with breadth is False, OR reduces to the other member). Nothing is backfilled.
- **Harnesses** (all imported from `d_substate_fresh.py`; no backtest loop re-implemented): the 26-year QQQ-core proxy
  through the project harness (standing 22.18 % / 0.913 / -33.6 %, S 1.103, H 0.768, 47.1 rebalances/yr, asserted), and
  the real DAILY mirror of `monthly_returns.simulate` asserted equal day by day (29.66 % / 1.145 / -32.9 %, 72.2 %
  exposure, 45.2 rebalances/yr, 2015-11-02..2026-09-04). Search era 2015-11+ / holdout 2000-07..2015-10. **Sharpe is the
  repo's zero-rate Sharpe throughout**; the outside study's excess-of-cash Sharpe is printed for the real harness as
  `xSh` (live 1.055; breadth 1.299) purely so the two tables can be reconciled -- our real-daily figures for the five
  singles sit within 1-2 pp CAGR and 0.05-0.07 Sharpe of the outside table, same ordering, same MaxDDs.
- **Overlap.** Breadth shares almost no days with the other four: Jaccard 0.10-0.12 on all 934 proxy D days (0.12-0.19 in
  the search era). `sma20>=sma60` and `px>=sma100` are one signal twice (Jaccard 0.47; 71 % of sma20>=sma60 days are also
  px>=sma100 days). `volratio>1.5` (34 days) sits inside the others (82 % of its days are sma20>=sma60 days, 44 % breadth
  days). So in day-set terms most pairs with breadth are two signals, not one -- **but the money is one episode set**: every
  single's top gain episodes are 2018-10 and 2020-02/03 (section 6).
- **Does any pair add to the breadth rule?** No. Of the 20 pairs and 16 unions, exactly two containing breadth beat breadth
  in both proxy eras, and both by noise: #8 `breadth OR px>=sma100` (+0.005 / +0.005) and #12 `breadth OR volratio>1.5`
  (+0.007 / +0.006). The best pair by full Sharpe, **#10 `breadth OR gap200<2%`** (25.74 % / 1.077 / -28.5 %; real
  37.75 % / 1.484 / -19.4 %), beats breadth in the search era (+0.078) and on the real rows (+0.089) but **loses the
  holdout (-0.045)**; block bootstrap vs breadth P(<=0) 0.43 (proxy) / 0.11 (real); leave-out-the-SPMO-era -0.045; at
  20 bp cost -0.016 full; SPY analogue +0.070 / -0.003. The three combinations that do beat the better of their OWN members
  in both eras (#20 `px>=sma100 OR gap200<2%`, #24 `gap200<2% OR volratio>1.5`, #34 `UNION(P100|G200|VR)`) do not contain
  breadth and all sit below breadth in the holdout (0.822 / 0.802 / 0.822 vs 0.872) and in the full period.
- **Permutation** (1000 common circular shifts of all five D-day flag sequences, max statistic over the whole grid of 41):
  best-of-41 full-period gain vs live, null median +0.037 / 95th +0.117, best real +0.178 (#30) p = 0.004; both-era
  min(dS_S, dS_H), null 95th +0.083, best real +0.110 (#12) p = 0.023 -- both driven by breadth itself, which is already
  pre-registered (#0 alone: p 0.01). **The statistic that answers the owner's question -- best combination gain over its
  best member single, both-era -- has null 95th +0.043, best real +0.024 (#20), p = 0.186.** Full-period version:
  null 95th +0.068, best real +0.079 (#34, over gap200<2%), p = 0.007 -- a real but breadth-free effect that never reaches
  the breadth rule's level.
- **Drawdown episodes** (section 6). The real-daily live MaxDD -32.9 % is 2018-08-28 -> 2018-12-07. All five singles flag
  days inside it (Oct-2018 sell-off: +9.9 to +19.7 pp vs live inside the window), so all five remove the same episode and
  land on the same next-worst floor: breadth and volratio both -24.7 % on **2025-02-18 -> 2025-04-07** (the -24.48 / -24.48
  pair in the outside table), gap200<2% -24.6 % on 2020-02-21 -> 2020-03-20 (the -24.50), px>=sma100 -26.2 % and
  sma20>=sma60 -28.1 % on 2025-11-07 -> 2026-03-19 (the -26.08 / -27.90). **Confirmed with dates: the near-identical
  MaxDDs are the same dodged episode (Oct 2018) and the same untouched one (Feb-Apr 2025), not five independent risk
  controls.**
- **Tree of special cases** (section 7). Best union #30 `UNION(breadth | gap200<2% | volratio>1.5)`: proxy 26.02 % / 1.091 /
  -28.5 % (S 1.418, H 0.846), real 37.77 % / 1.495 / -19.4 %; vs breadth alone S +0.086, **H -0.026**, F +0.021, real
  +0.100. Only breadth earns its place (its 85 unique days lose -32 bp/day for QLD in the search era and -28 bp in the
  holdout); gap200<2% has 113 unique days that lose -40 bp in search but **make +21 bp in the holdout** (dropping it raises
  holdout Sharpe +0.031); volratio>1.5 has 16 unique days (+13 bp search) and moves nothing (+/-0.02). In the full 5-union,
  `sma20>=sma60` and `px>=sma100` are actively harmful as cases: their unique days are the healthy-pullback days, **+177 bp
  and +63 bp/day for QLD in the search era** (t 3.8 / 2.4), and dropping each raises search Sharpe +0.190 / +0.134. No
  union beats breadth in both eras. Post-hoc per-case actions (cash vs half) change nothing (best 1.091 -> 1.090).
- **Verdict: the pre-registered breadth rule stands alone.** Nothing on this grid adds to it on its own terms (both eras,
  bootstrap, permutation over the grid). The pairs that look best on the real rows (#10, #30) are the breadth rule plus a
  second look at Oct-2018 / Mar-2020 from the 200d line, paid for with a holdout loss; the "healthy-looking" rules
  (sma20>=sma60, px>=sma100) are one signal twice and, as tree cases, exit the days that make QLD's money.
- Candidate count this line: 41 pre-registered + 21 constant-D controls + 8 post-hoc per-case action variants (reported,
  not part of the permutation). Cumulative with earlier lines: 240 + 890 + 41.

## 1. Setup

Reproduction is entirely through `d_substate_fresh.py`, imported with `DSF_STAGE=none` so only its bootstrap runs: the
`leverage_under_trim` harness bootstrap (`rows`, `run`, `evaluate`, `vt`, `RF`), its `run_count` (asserted equal to
`improvement_search.run`), `evaluate_full` (full / search / holdout), `simulate_real` (asserted equal to
`monthly_returns.simulate` day by day), the kairos symlink shim and the synthetic BOXX with `MR.TAIL['BOXX']`
neutralised, the signal calendar extended back to 1998 with the FRED NASDAQ-100 index (so SMA/vol lookbacks exist by
2000-07), `build_spy_rows` for the SPY-core proxy, `block_bootstrap.boot` (2000 draws) and `REGIMES`.

Signals on that calendar: `gap100`, `gap200`, `volratio` (10d / 30d realised vol, `_vol` on daily returns) are the
harness's own series; SMA20 / SMA60 are `sma_series` on the same close; breadth is `breadth_tracker` on
`QQEW_daily_ext.csv` against each harness's own QQQ series (proxy `qqq_long_history`, real `monthly_returns.build()`),
first value 2007-07-27 in both. Flags read at the decision close d0 and act on d0 -> d1, as the live design does.

Constant-D controls: D -> f x QLD + (1 - f) cash before the vol target, f in 5 % steps (f = 100 % reproduces live to
1e-9 on both harnesses). A candidate is matched to the control whose average deployed capital is nearest its own.

Sharpe: zero-rate, `drift_band_test.annual_stats`, everywhere. Real-daily `xSh` = excess of the synthetic BOXX leg.

| harness | live CAGR / Sharpe / MaxDD | S Sharpe | H Sharpe | exposure | rebalances/yr | D days |
|---|---|---|---|---|---|---|
| proxy 2000-07-03..2026-08-26 (6575 rows) | 22.18 % / 0.913 / -33.6 % | 1.103 | 0.768 | 67.7 % | 47.1 | 934 (S 382, H 552; 207 without breadth) |
| real daily 2015-11-02..2026-09-04 (2725 rows) | 29.66 % / 1.145 (xSh 1.055) / -32.9 % | -- | -- | 72.2 % | 45.2 | 382 |

## 2. Overlap of the five flag sets on D days

Upper triangle Jaccard |a&b| / |a|b|, lower triangle conditional P(column | row) = |a&b| / |row|.

Proxy, full (934 D days):

| | n | BR | S20 | P100 | G200 | VR |
|---|---|---|---|---|---|---|
| breadth (BR) | 124 | -- | 0.12 | 0.10 | 0.12 | 0.10 |
| sma20>=sma60 (S20) | 415 | 0.14 | -- | 0.47 | 0.07 | 0.07 |
| px>=sma100 (P100) | 496 | 0.12 | 0.59 | -- | 0.02 | 0.04 |
| gap200<2% (G200) | 144 | 0.19 | 0.25 | 0.09 | -- | 0.04 |
| volratio>1.5 (VR) | 34 | 0.44 | 0.82 | 0.59 | 0.21 | -- |

Search era 2015-11+ (382 D days; identical to the real-daily D days):

| | n | BR | S20 | P100 | G200 | VR |
|---|---|---|---|---|---|---|
| breadth | 59 | -- | 0.16 | 0.12 | 0.15 | 0.19 |
| sma20>=sma60 | 200 | 0.17 | -- | 0.52 | 0.07 | 0.09 |
| px>=sma100 | 220 | 0.13 | 0.65 | -- | 0.04 | 0.05 |
| gap200<2% | 46 | 0.30 | 0.35 | 0.20 | -- | 0.08 |
| volratio>1.5 | 24 | 0.54 | 0.75 | 0.46 | 0.21 | -- |

Holdout with breadth available, 2007-07..2015-10 (345 D days):

| | n | BR | S20 | P100 | G200 | VR |
|---|---|---|---|---|---|---|
| breadth | 65 | -- | 0.13 | 0.13 | 0.14 | 0.03 |
| sma20>=sma60 | 133 | 0.17 | -- | 0.37 | 0.06 | 0.08 |
| px>=sma100 | 179 | 0.16 | 0.47 | -- | 0.01 | 0.05 |
| gap200<2% | 48 | 0.29 | 0.21 | 0.06 | -- | 0.04 |
| volratio>1.5 | 10 | 0.20 | 1.00 | 0.90 | 0.20 | -- |

Pair detail (proxy full): |a|, |b|, |a&b|, |a|b|, Jaccard, P(b|a), P(a|b); then search-era and real-daily Jaccard.

| a | b | a | b | a&b | a\|b | J | P(b\|a) | P(a\|b) | J search | J real |
|---|---|---|---|---|---|---|---|---|---|---|
| breadth | sma20>=sma60 | 124 | 415 | 58 | 481 | 0.12 | 0.47 | 0.14 | 0.16 | 0.16 |
| breadth | px>=sma100 | 124 | 496 | 58 | 562 | 0.10 | 0.47 | 0.12 | 0.12 | 0.12 |
| breadth | gap200<2% | 124 | 144 | 28 | 240 | 0.12 | 0.23 | 0.19 | 0.15 | 0.15 |
| breadth | volratio>1.5 | 124 | 34 | 15 | 143 | 0.10 | 0.12 | 0.44 | 0.19 | 0.19 |
| sma20>=sma60 | px>=sma100 | 415 | 496 | 293 | 618 | 0.47 | 0.71 | 0.59 | 0.52 | 0.52 |
| sma20>=sma60 | gap200<2% | 415 | 144 | 36 | 523 | 0.07 | 0.09 | 0.25 | 0.07 | 0.07 |
| sma20>=sma60 | volratio>1.5 | 415 | 34 | 28 | 421 | 0.07 | 0.07 | 0.82 | 0.09 | 0.09 |
| px>=sma100 | gap200<2% | 496 | 144 | 13 | 627 | 0.02 | 0.03 | 0.09 | 0.04 | 0.04 |
| px>=sma100 | volratio>1.5 | 496 | 34 | 20 | 510 | 0.04 | 0.04 | 0.59 | 0.05 | 0.05 |
| gap200<2% | volratio>1.5 | 144 | 34 | 7 | 171 | 0.04 | 0.05 | 0.21 | 0.08 | 0.08 |

Reading: `sma20>=sma60` / `px>=sma100` is one signal twice (the pullback that has not yet broken the intermediate
trend). `volratio>1.5` is a small subset of both of those and half-inside breadth. Breadth vs the 200d-gap rule share 28
of 240 days. Day-set overlap is therefore LOW for most breadth pairs -- the case for "two signals" has to be made on
where the money comes from, which section 6 does.

## 3. Constant-D controls

| f (QLD in D) | proxy CAGR / Sharpe / MaxDD | exp | reb/yr | S Sh | H Sh | real CAGR / Sharpe / xSh / MaxDD | exp |
|---|---|---|---|---|---|---|---|
| 0 % | 16.71 % / 0.854 / -28.5 % | 54.4 % | 44.5 | 1.084 | 0.684 | 23.11 % / 1.164 / 1.045 / -23.0 % | 59.4 % |
| 20 % | 17.97 % / 0.899 / -28.7 % | 57.1 % | 45.1 | 1.134 | 0.725 | 24.67 % / 1.214 / 1.097 / -20.6 % | 62.0 % |
| 40 % | 19.22 % / 0.928 / -29.0 % | 59.7 % | 45.8 | 1.160 | 0.755 | 26.20 % / 1.234 / 1.122 / -20.5 % | 64.5 % |
| 50 % | 19.79 % / 0.934 / -29.2 % | 61.1 % | 46.1 | 1.161 | 0.764 | 26.88 % / 1.231 / 1.122 / -21.8 % | 65.8 % |
| 60 % | 20.31 % / 0.935 / -29.0 % | 62.4 % | 46.3 | 1.156 | 0.770 | 27.50 % / 1.221 / 1.116 / -24.1 % | 67.1 % |
| 75 % | 21.06 % / 0.932 / -29.6 % | 64.4 % | 46.6 | 1.142 | 0.773 | 28.36 % / 1.198 / 1.097 / -27.5 % | 69.0 % |
| 85 % | 21.51 % / 0.925 / -31.2 % | 65.7 % | 46.9 | 1.127 | 0.772 | 28.90 % / 1.178 / 1.081 / -29.7 % | 70.3 % |
| 90 % | 21.75 % / 0.922 / -32.0 % | 66.4 % | 47.0 | 1.120 | 0.772 | 29.16 % / 1.168 / 1.073 / -30.7 % | 70.9 % |
| 100 % (live) | 22.18 % / 0.913 / -33.6 % | 67.7 % | 47.1 | 1.103 | 0.768 | 29.66 % / 1.145 / 1.055 / -32.9 % | 72.2 % |

(All 21 steps are in the log.) The constant-D Sharpe is flat: 0.913..0.935 on the proxy, 1.145..1.234 real. Any
candidate's value is what it adds over the control at its own exposure, not over live.

## 4. The grid: all 41 candidates

Proxy full / search / holdout, then real daily. nOn / ep = flagged D days / flagged episodes (full proxy); rnOn / rep =
same on the real rows. dS = Sharpe minus live.

| # | candidate | nOn | ep | CAGR | Sharpe | MaxDD | exp | reb | S Sh | H Sh | dS_S | dS_H | dS_F | real CAGR | rSh | xSh | rDD | rexp | rreb | rnOn | rep |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | breadth | 124 | 40 | 26.13 % | 1.070 | -28.5 % | 66.2 % | 47.9 | 1.332 | 0.872 | +0.229 | +0.104 | +0.157 | 36.09 % | 1.395 | 1.299 | -24.7 % | 70 % | 46.7 | 59 | 22 |
| 1 | sma20>=sma60 | 415 | 71 | 22.35 % | 0.994 | -31.3 % | 61.8 % | 47.1 | 1.238 | 0.817 | +0.135 | +0.049 | +0.082 | 30.00 % | 1.311 | 1.205 | -28.1 % | 65 % | 44.5 | 200 | 34 |
| 2 | px>=sma100 | 496 | 130 | 22.19 % | 0.977 | -32.6 % | 60.7 % | 50.4 | 1.219 | 0.798 | +0.116 | +0.030 | +0.064 | 30.23 % | 1.286 | 1.183 | -26.2 % | 65 % | 49.1 | 220 | 68 |
| 3 | gap200<2% | 144 | 61 | 23.34 % | 0.974 | -29.5 % | 65.7 % | 49.2 | 1.228 | 0.779 | +0.125 | +0.011 | +0.061 | 33.04 % | 1.284 | 1.190 | -24.6 % | 71 % | 46.8 | 46 | 22 |
| 4 | volratio>1.5 | 34 | 11 | 23.79 % | 0.973 | -33.6 % | 67.3 % | 47.4 | 1.233 | 0.777 | +0.130 | +0.009 | +0.060 | 33.54 % | 1.287 | 1.194 | -24.7 % | 71 % | 45.7 | 24 | 8 |
| 5 | breadth AND sma20>=sma60 | 58 | 23 | 25.37 % | 1.034 | -31.3 % | 67.0 % | 47.7 | 1.293 | 0.839 | +0.190 | +0.071 | +0.121 | 35.15 % | 1.351 | 1.257 | -25.2 % | 71 % | 46.2 | 35 | 15 |
| 6 | breadth OR sma20>=sma60 | 481 | 87 | 23.10 % | 1.034 | -28.5 % | 61.0 % | 47.2 | 1.282 | 0.853 | +0.180 | +0.086 | +0.121 | 30.91 % | 1.362 | 1.254 | -26.3 % | 65 % | 44.9 | 224 | 41 |
| 7 | breadth AND px>=sma100 | 58 | 28 | 24.13 % | 0.985 | -33.6 % | 67.0 % | 47.9 | 1.229 | 0.800 | +0.126 | +0.032 | +0.072 | 33.39 % | 1.281 | 1.188 | -27.0 % | 71 % | 46.5 | 29 | 15 |
| 8 | breadth OR px>=sma100 | 562 | 138 | 24.19 % | 1.073 | -28.5 % | 59.8 % | 50.1 | 1.337 | 0.877 | +0.234 | +0.110 | +0.160 | 32.92 % | 1.420 | 1.313 | -24.3 % | 64 % | 48.8 | 250 | 72 |
| 9 | breadth AND gap200<2% | 28 | 16 | 23.74 % | 0.970 | -29.5 % | 67.4 % | 47.5 | 1.160 | 0.825 | +0.057 | +0.057 | +0.057 | 31.47 % | 1.208 | 1.116 | -24.9 % | 72 % | 45.9 | 14 | 7 |
| 10 | breadth OR gap200<2% | 240 | 82 | 25.74 % | 1.077 | -28.5 % | 64.5 % | 49.4 | 1.410 | 0.828 | +0.308 | +0.060 | +0.164 | 37.75 % | 1.484 | 1.385 | -19.4 % | 69 % | 47.3 | 91 | 35 |
| 11 | breadth AND volratio>1.5 | 15 | 6 | 23.75 % | 0.968 | -33.6 % | 67.5 % | 47.3 | 1.228 | 0.772 | +0.125 | +0.004 | +0.055 | 33.52 % | 1.279 | 1.186 | -24.9 % | 72 % | 45.5 | 13 | 5 |
| 12 | breadth OR volratio>1.5 | 143 | 44 | 26.18 % | 1.076 | -28.5 % | 65.9 % | 47.9 | 1.339 | 0.878 | +0.236 | +0.110 | +0.163 | 36.14 % | 1.405 | 1.309 | -24.7 % | 70 % | 46.7 | 70 | 24 |
| 13 | sma20>=sma60 AND px>=sma100 | 293 | 82 | 24.62 % | 1.040 | -32.2 % | 63.5 % | 49.2 | 1.383 | 0.787 | +0.280 | +0.019 | +0.127 | 36.31 % | 1.457 | 1.357 | -27.8 % | 67 % | 48.0 | 144 | 47 |
| 14 | sma20>=sma60 OR px>=sma100 | 618 | 115 | 19.99 % | 0.930 | -31.3 % | 59.0 % | 47.9 | 1.064 | 0.832 | -0.038 | +0.064 | +0.017 | 24.22 % | 1.129 | 1.020 | -26.5 % | 63 % | 45.3 | 276 | 54 |
| 15 | sma20>=sma60 AND gap200<2% | 36 | 25 | 23.62 % | 0.967 | -30.0 % | 67.2 % | 48.0 | 1.156 | 0.823 | +0.053 | +0.055 | +0.055 | 31.30 % | 1.205 | 1.114 | -29.4 % | 72 % | 46.3 | 16 | 10 |
| 16 | sma20>=sma60 OR gap200<2% | 523 | 105 | 22.08 % | 1.005 | -29.4 % | 60.3 % | 48.1 | 1.327 | 0.772 | +0.225 | +0.004 | +0.092 | 31.73 % | 1.412 | 1.302 | -26.2 % | 64 % | 44.8 | 230 | 45 |
| 17 | sma20>=sma60 AND volratio>1.5 | 28 | 10 | 23.17 % | 0.951 | -33.6 % | 67.4 % | 47.4 | 1.181 | 0.777 | +0.078 | +0.009 | +0.038 | 31.93 % | 1.231 | 1.139 | -31.1 % | 72 % | 45.7 | 18 | 7 |
| 18 | sma20>=sma60 OR volratio>1.5 | 421 | 72 | 22.97 % | 1.019 | -31.3 % | 61.7 % | 47.1 | 1.299 | 0.817 | +0.196 | +0.049 | +0.106 | 31.59 % | 1.377 | 1.270 | -28.1 % | 65 % | 44.5 | 206 | 35 |
| 19 | px>=sma100 AND gap200<2% | 13 | 11 | 22.42 % | 0.923 | -33.3 % | 67.5 % | 47.5 | 1.131 | 0.765 | +0.029 | -0.003 | +0.010 | 30.49 % | 1.177 | 1.086 | -32.9 % | 72 % | 46.0 | 9 | 7 |
| 20 | px>=sma100 OR gap200<2% | 627 | 166 | 23.18 % | 1.041 | -27.5 % | 58.8 % | 51.3 | 1.335 | 0.822 | +0.232 | +0.054 | +0.128 | 32.81 % | 1.418 | 1.311 | -24.3 % | 64 % | 49.6 | 257 | 81 |
| 21 | px>=sma100 AND volratio>1.5 | 20 | 9 | 23.10 % | 0.946 | -33.6 % | 67.5 % | 47.5 | 1.159 | 0.784 | +0.056 | +0.016 | +0.033 | 31.43 % | 1.207 | 1.115 | -32.9 % | 72 % | 46.0 | 11 | 6 |
| 22 | px>=sma100 OR volratio>1.5 | 510 | 131 | 22.88 % | 1.008 | -32.6 % | 60.5 % | 50.2 | 1.305 | 0.791 | +0.203 | +0.023 | +0.095 | 32.34 % | 1.382 | 1.277 | -26.2 % | 64 % | 48.7 | 233 | 69 |
| 23 | gap200<2% AND volratio>1.5 | 7 | 3 | 22.48 % | 0.924 | -33.6 % | 67.6 % | 47.2 | 1.146 | 0.755 | +0.043 | -0.013 | +0.011 | 31.05 % | 1.193 | 1.102 | -24.7 % | 72 % | 45.4 | 5 | 2 |
| 24 | gap200<2% OR volratio>1.5 | 171 | 68 | 24.66 % | 1.025 | -29.5 % | 65.3 % | 49.3 | 1.320 | 0.802 | +0.217 | +0.034 | +0.112 | 35.58 % | 1.384 | 1.288 | -20.7 % | 70 % | 47.0 | 65 | 27 |
| 25 | UNION(BR\|S20\|P100) | 660 | 120 | 20.90 % | 0.974 | -28.5 % | 58.4 % | 47.8 | 1.129 | 0.862 | +0.026 | +0.094 | +0.062 | 25.71 % | 1.201 | 1.090 | -24.5 % | 62 % | 45.3 | 296 | 57 |
| 26 | UNION(BR\|S20\|G200) | 567 | 109 | 22.18 % | 1.017 | -28.5 % | 59.7 % | 47.9 | 1.320 | 0.797 | +0.217 | +0.029 | +0.104 | 31.31 % | 1.405 | 1.295 | -25.5 % | 64 % | 44.9 | 242 | 47 |
| 27 | UNION(BR\|S20\|VR) | 484 | 87 | 23.31 % | 1.042 | -28.5 % | 61.0 % | 47.2 | 1.302 | 0.853 | +0.200 | +0.086 | +0.130 | 31.45 % | 1.383 | 1.276 | -26.3 % | 65 % | 44.9 | 227 | 41 |
| 28 | UNION(BR\|P100\|G200) | 666 | 158 | 23.70 % | 1.076 | -28.5 % | 58.3 % | 50.6 | 1.397 | 0.839 | +0.294 | +0.071 | +0.163 | 33.90 % | 1.489 | 1.380 | -23.9 % | 63 % | 48.7 | 274 | 78 |
| 29 | UNION(BR\|P100\|VR) | 569 | 137 | 24.01 % | 1.067 | -28.5 % | 59.7 % | 50.0 | 1.335 | 0.870 | +0.233 | +0.102 | +0.155 | 32.77 % | 1.419 | 1.312 | -24.3 % | 64 % | 48.6 | 256 | 71 |
| 30 | UNION(BR\|G200\|VR) | 256 | 84 | 26.02 % | 1.091 | -28.5 % | 64.3 % | 49.4 | 1.418 | 0.846 | +0.315 | +0.079 | +0.178 | 37.77 % | 1.495 | 1.395 | -19.4 % | 69 % | 47.3 | 101 | 36 |
| 31 | UNION(S20\|P100\|G200) | 722 | 137 | 19.94 % | 0.947 | -28.9 % | 57.5 % | 48.6 | 1.172 | 0.784 | +0.069 | +0.016 | +0.035 | 26.49 % | 1.249 | 1.137 | -24.6 % | 62 % | 45.5 | 304 | 63 |
| 32 | UNION(S20\|P100\|VR) | 624 | 116 | 20.59 % | 0.955 | -31.3 % | 58.9 % | 47.9 | 1.125 | 0.832 | +0.023 | +0.064 | +0.042 | 25.74 % | 1.195 | 1.085 | -26.5 % | 63 % | 45.3 | 282 | 55 |
| 33 | UNION(S20\|G200\|VR) | 525 | 104 | 22.29 % | 1.013 | -29.4 % | 60.2 % | 48.0 | 1.347 | 0.772 | +0.245 | +0.004 | +0.100 | 32.25 % | 1.433 | 1.323 | -26.2 % | 64 % | 44.6 | 232 | 44 |
| 34 | UNION(P100\|G200\|VR) | 635 | 164 | 23.48 % | 1.056 | -27.5 % | 58.7 % | 51.0 | 1.374 | 0.822 | +0.272 | +0.054 | +0.143 | 33.55 % | 1.461 | 1.353 | -24.3 % | 63 % | 48.9 | 265 | 79 |
| 35 | UNION(BR\|S20\|P100\|G200) | 742 | 131 | 20.22 % | 0.963 | -28.5 % | 57.2 % | 48.2 | 1.185 | 0.802 | +0.083 | +0.034 | +0.051 | 26.71 % | 1.264 | 1.151 | -24.0 % | 62 % | 45.1 | 312 | 61 |
| 36 | UNION(BR\|S20\|P100\|VR) | 663 | 120 | 21.11 % | 0.983 | -28.5 % | 58.4 % | 47.8 | 1.149 | 0.862 | +0.046 | +0.094 | +0.070 | 26.23 % | 1.223 | 1.112 | -24.5 % | 62 % | 45.2 | 299 | 57 |
| 37 | UNION(BR\|S20\|G200\|VR) | 569 | 108 | 22.40 % | 1.025 | -28.5 % | 59.7 % | 47.8 | 1.340 | 0.797 | +0.238 | +0.029 | +0.112 | 31.83 % | 1.426 | 1.316 | -25.5 % | 64 % | 44.7 | 244 | 46 |
| 38 | UNION(BR\|P100\|G200\|VR) | 671 | 156 | 23.64 % | 1.075 | -28.5 % | 58.3 % | 50.4 | 1.396 | 0.839 | +0.293 | +0.071 | +0.162 | 33.71 % | 1.488 | 1.378 | -23.9 % | 63 % | 48.4 | 279 | 76 |
| 39 | UNION(S20\|P100\|G200\|VR) | 724 | 136 | 20.15 % | 0.956 | -28.9 % | 57.5 % | 48.5 | 1.193 | 0.784 | +0.090 | +0.016 | +0.043 | 26.99 % | 1.271 | 1.158 | -24.6 % | 62 % | 45.3 | 306 | 62 |
| 40 | UNION(BR\|S20\|P100\|G200\|VR) | 744 | 130 | 20.43 % | 0.972 | -28.5 % | 57.2 % | 48.1 | 1.206 | 0.802 | +0.103 | +0.034 | +0.059 | 27.21 % | 1.286 | 1.172 | -24.0 % | 62 % | 44.9 | 314 | 60 |

Reconciliation with the outside table (real daily, their CAGR / excess Sharpe / MaxDD -> ours CAGR / xSh / MaxDD): live
31.42 / 1.117 / -32.89 -> 29.66 / 1.055 / -32.9; breadth 37.92 / 1.365 / -24.48 -> 36.09 / 1.299 / -24.7; sma20>=sma60
31.77 / 1.277 / -27.90 -> 30.00 / 1.205 / -28.1; px>=sma100 31.97 / 1.253 / -26.08 -> 30.23 / 1.183 / -26.2; gap200<2%
34.80 / 1.253 / -24.50 -> 33.04 / 1.190 / -24.6; volratio>1.5 35.34 / 1.257 / -24.48 -> 33.54 / 1.194 / -24.7; 85 %
control 30.64 / 1.147 / -29.68 -> 28.90 / 1.081 / -29.7. Same ordering, same drawdowns; the level gap is the window
(2015-10 vs 2015-11-02 start) and the cash leg.

## 5. Deltas: vs live, vs the exposure-matched constant-D control, vs the better member single

Sharpe differences. "vBest" per era = candidate minus the higher of its members' Sharpes in that era. A combination
"adds" only if vBest > 0 in BOTH proxy eras.

| # | candidate | ctrl f | vLive S / H / F | vCtl S / H / F | vBest S / H / F | real: ctrl f | vLive | vCtl | vBest | adds? |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | breadth | 90 % | +0.229 / +0.104 / +0.157 | +0.212 / +0.101 / +0.148 | -- | 85 % | +0.250 | +0.217 | -- | -- |
| 1 | sma20>=sma60 | 55 % | +0.135 / +0.049 / +0.082 | +0.079 / +0.050 / +0.059 | -- | 45 % | +0.165 | +0.077 | -- | -- |
| 2 | px>=sma100 | 45 % | +0.116 / +0.030 / +0.064 | +0.059 / +0.038 / +0.046 | -- | 40 % | +0.141 | +0.052 | -- | -- |
| 3 | gap200<2% | 85 % | +0.125 / +0.011 / +0.061 | +0.101 / +0.007 / +0.048 | -- | 90 % | +0.138 | +0.116 | -- | -- |
| 4 | volratio>1.5 | 95 % | +0.130 / +0.009 / +0.060 | +0.121 / +0.008 / +0.055 | -- | 95 % | +0.141 | +0.129 | -- | -- |
| 5 | breadth AND sma20>=sma60 | 95 % | +0.190 / +0.071 / +0.121 | +0.181 / +0.070 / +0.116 | -0.039 / -0.033 / -0.036 | 90 % | +0.206 | +0.183 | -0.044 | no |
| 6 | breadth OR sma20>=sma60 | 50 % | +0.180 / +0.086 / +0.121 | +0.121 / +0.089 / +0.100 | -0.050 / -0.019 / -0.036 | 40 % | +0.217 | +0.128 | -0.033 | no |
| 7 | breadth AND px>=sma100 | 95 % | +0.126 / +0.032 / +0.072 | +0.117 / +0.031 / +0.067 | -0.103 / -0.072 / -0.085 | 95 % | +0.136 | +0.124 | -0.114 | no |
| 8 | breadth OR px>=sma100 | 40 % | +0.234 / +0.110 / +0.160 | +0.177 / +0.123 / +0.145 | **+0.005 / +0.005** / +0.003 | 35 % | +0.274 | +0.187 | +0.025 | ADDS (noise) |
| 9 | breadth AND gap200<2% | 95 % | +0.057 / +0.057 / +0.057 | +0.048 / +0.055 / +0.052 | -0.172 / -0.047 / -0.100 | 95 % | +0.062 | +0.050 | -0.187 | no |
| 10 | breadth OR gap200<2% | 75 % | +0.308 / +0.060 / +0.164 | +0.268 / +0.054 / +0.145 | **+0.078 / -0.045** / +0.008 | 75 % | +0.338 | +0.286 | +0.089 | no |
| 11 | breadth AND volratio>1.5 | 100 % | +0.125 / +0.004 / +0.055 | +0.125 / +0.004 / +0.055 | -0.104 / -0.100 / -0.102 | 95 % | +0.133 | +0.121 | -0.116 | no |
| 12 | breadth OR volratio>1.5 | 85 % | +0.236 / +0.110 / +0.163 | +0.212 / +0.106 / +0.150 | **+0.007 / +0.006** / +0.006 | 80 % | +0.260 | +0.218 | +0.010 | ADDS (noise) |
| 13 | sma20>=sma60 AND px>=sma100 | 70 % | +0.280 / +0.019 / +0.127 | +0.235 / +0.015 / +0.106 | +0.145 / -0.030 / +0.045 | 60 % | +0.312 | +0.236 | +0.146 | no |
| 14 | sma20>=sma60 OR px>=sma100 | 35 % | -0.038 / +0.064 / +0.017 | -0.093 / +0.083 / +0.007 | -0.174 / +0.014 / -0.065 | 30 % | -0.017 | -0.101 | -0.182 | no |
| 15 | sma20>=sma60 AND gap200<2% | 95 % | +0.053 / +0.055 / +0.055 | +0.044 / +0.053 / +0.050 | -0.082 / +0.006 / -0.027 | 95 % | +0.060 | +0.048 | -0.105 | no |
| 16 | sma20>=sma60 OR gap200<2% | 45 % | +0.225 / +0.004 / +0.092 | +0.167 / +0.012 / +0.074 | +0.089 / -0.045 / +0.010 | 40 % | +0.266 | +0.177 | +0.101 | no |
| 17 | sma20>=sma60 AND volratio>1.5 | 95 % | +0.078 / +0.009 / +0.038 | +0.068 / +0.008 / +0.033 | -0.057 / -0.040 / -0.043 | 95 % | +0.086 | +0.074 | -0.079 | no |
| 18 | sma20>=sma60 OR volratio>1.5 | 55 % | +0.196 / +0.049 / +0.106 | +0.140 / +0.050 / +0.084 | +0.061 / +0.000 / +0.025 | 45 % | +0.231 | +0.144 | +0.066 | no |
| 19 | px>=sma100 AND gap200<2% | 100 % | +0.029 / -0.003 / +0.010 | +0.029 / -0.003 / +0.010 | -0.096 / -0.033 / -0.054 | 95 % | +0.032 | +0.020 | -0.109 | no |
| 20 | px>=sma100 OR gap200<2% | 35 % | +0.232 / +0.054 / +0.128 | +0.178 / +0.073 / +0.118 | **+0.107 / +0.024** / +0.064 | 35 % | +0.272 | +0.185 | +0.132 | ADDS |
| 21 | px>=sma100 AND volratio>1.5 | 100 % | +0.056 / +0.016 / +0.033 | +0.056 / +0.016 / +0.033 | -0.074 / -0.014 / -0.031 | 95 % | +0.061 | +0.049 | -0.080 | no |
| 22 | px>=sma100 OR volratio>1.5 | 45 % | +0.203 / +0.023 / +0.095 | +0.145 / +0.030 / +0.077 | +0.073 / -0.007 / +0.031 | 40 % | +0.237 | +0.148 | +0.095 | no |
| 23 | gap200<2% AND volratio>1.5 | 100 % | +0.043 / -0.013 / +0.011 | +0.043 / -0.013 / +0.011 | -0.087 / -0.024 / -0.049 | 100 % | +0.047 | +0.047 | -0.094 | no |
| 24 | gap200<2% OR volratio>1.5 | 80 % | +0.217 / +0.034 / +0.112 | +0.186 / +0.030 / +0.097 | **+0.087 / +0.023** / +0.051 | 85 % | +0.239 | +0.206 | +0.097 | ADDS |
| 25 | UNION(BR\|S20\|P100) | 30 % | +0.026 / +0.094 / +0.062 | -0.023 / +0.120 / +0.058 | -0.203 / -0.010 / -0.095 | 20 % | +0.056 | -0.013 | -0.194 | no |
| 26 | UNION(BR\|S20\|G200) | 40 % | +0.217 / +0.029 / +0.104 | +0.160 / +0.042 / +0.089 | -0.012 / -0.075 / -0.053 | 35 % | +0.260 | +0.172 | +0.010 | no |
| 27 | UNION(BR\|S20\|VR) | 50 % | +0.200 / +0.086 / +0.130 | +0.141 / +0.089 / +0.108 | -0.030 / -0.019 / -0.027 | 40 % | +0.238 | +0.149 | -0.011 | no |
| 28 | UNION(BR\|P100\|G200) | 30 % | +0.294 / +0.071 / +0.163 | +0.245 / +0.097 / +0.159 | +0.065 / -0.033 / +0.006 | 30 % | +0.344 | +0.260 | +0.094 | no |
| 29 | UNION(BR\|P100\|VR) | 40 % | +0.233 / +0.102 / +0.155 | +0.175 / +0.115 / +0.140 | +0.004 / -0.002 / -0.002 | 35 % | +0.273 | +0.186 | +0.024 | no |
| 30 | UNION(BR\|G200\|VR) | 75 % | +0.315 / +0.079 / +0.178 | +0.276 / +0.073 / +0.159 | **+0.086 / -0.026** / +0.021 | 75 % | +0.349 | +0.297 | +0.100 | no |
| 31 | UNION(S20\|P100\|G200) | 25 % | +0.069 / +0.016 / +0.035 | +0.029 / +0.049 / +0.039 | -0.066 / -0.033 / -0.047 | 20 % | +0.104 | +0.035 | -0.061 | no |
| 32 | UNION(S20\|P100\|VR) | 35 % | +0.023 / +0.064 / +0.042 | -0.032 / +0.083 / +0.032 | -0.113 / +0.014 / -0.039 | 25 % | +0.050 | -0.027 | -0.115 | no |
| 33 | UNION(S20\|G200\|VR) | 45 % | +0.245 / +0.004 / +0.100 | +0.187 / +0.012 / +0.082 | +0.110 / -0.045 / +0.019 | 40 % | +0.287 | +0.198 | +0.122 | no |
| 34 | UNION(P100\|G200\|VR) | 30 % | +0.272 / +0.054 / +0.143 | +0.223 / +0.080 / +0.140 | **+0.141 / +0.024** / +0.079 | 30 % | +0.316 | +0.232 | +0.175 | ADDS |
| 35 | UNION(BR\|S20\|P100\|G200) | 20 % | +0.083 / +0.034 / +0.051 | +0.051 / +0.077 / +0.065 | -0.147 / -0.070 / -0.106 | 20 % | +0.119 | +0.050 | -0.130 | no |
| 36 | UNION(BR\|S20\|P100\|VR) | 30 % | +0.046 / +0.094 / +0.070 | -0.002 / +0.120 / +0.067 | -0.183 / -0.010 / -0.087 | 20 % | +0.078 | +0.009 | -0.172 | no |
| 37 | UNION(BR\|S20\|G200\|VR) | 40 % | +0.238 / +0.029 / +0.112 | +0.180 / +0.042 / +0.097 | +0.008 / -0.075 / -0.045 | 35 % | +0.281 | +0.193 | +0.032 | no |
| 38 | UNION(BR\|P100\|G200\|VR) | 30 % | +0.293 / +0.071 / +0.162 | +0.244 / +0.097 / +0.158 | +0.064 / -0.033 / +0.005 | 25 % | +0.342 | +0.266 | +0.093 | no |
| 39 | UNION(S20\|P100\|G200\|VR) | 25 % | +0.090 / +0.016 / +0.043 | +0.050 / +0.049 / +0.048 | -0.045 / -0.033 / -0.038 | 20 % | +0.126 | +0.057 | -0.040 | no |
| 40 | UNION(BR\|S20\|P100\|G200\|VR) | 20 % | +0.103 / +0.034 / +0.059 | +0.072 / +0.077 / +0.073 | -0.126 / -0.070 / -0.098 | 20 % | +0.141 | +0.072 | -0.109 | no |

Five of 36 combinations beat the better of their own members in both eras: #8 and #12 (with breadth, by +0.005..+0.007
-- below the resolution of anything else in this note), and #20, #24, #34 (without breadth, by +0.02 in the holdout).
**None of the 32 combinations without breadth reaches the breadth single in the holdout (best 0.832, #14/#32, vs 0.872) or
in the full period (best 1.056, #34, vs 1.070).** Every AND pair is worse than its better member in the full period: the
intersection just removes days from the stronger rule.

### Permutation (whole grid of 41, 1000 common circular shifts of the D-day flag sequences)

All five rule sequences are shifted by the same offset within the 934-day D sequence, so the overlap structure between
rules -- and hence between candidates -- is preserved under the null.

| statistic (max over the grid) | null median | null 95th | null max | best real | candidate | p |
|---|---|---|---|---|---|---|
| full-period Sharpe gain vs live (41) | +0.037 | +0.117 | +0.352 | +0.178 | #30 UNION(BR\|G200\|VR) | 0.004 |
| both-era min(dS_S, dS_H) vs live (41) | +0.016 | +0.083 | +0.332 | +0.110 | #12 breadth OR volratio>1.5 | 0.023 |
| combination minus its best member, full (36) | +0.032 | +0.068 | +0.098 | +0.079 | #34 UNION(P100\|G200\|VR) over gap200<2% | 0.007 |
| **combination minus its best member, both-era min (36)** | +0.007 | +0.043 | +0.074 | **+0.024** | #20 px>=sma100 OR gap200<2% | **0.186** |

Per-candidate p on the best-of-41 full-period null (in the log): breadth #0 0.01; #8 0.01; #10 0.01; #12 0.01; #28 0.01;
#29 0.01; #30 0.00; #38 0.01; #34 0.03; every combination without breadth other than #34 is >= 0.04. The grid "finds"
something at p 0.004 -- but the something is the breadth rule, which was pre-registered before this line, plus a full-period
gain over the 200d-gap rule that never reaches the breadth rule's level. On the question actually asked -- does a combination
add to its best member in both eras -- the best real gain (+0.024) is a median-to-95th null draw.

## 6. Deep diagnostics: best single, best pair, best union, full 5-union

Picks by full-period proxy Sharpe: single #0 breadth; pair #10 `breadth OR gap200<2%` (also the best pair by real daily
Sharpe, 1.484); union #30 `UNION(BR|G200|VR)`; full 5-union #40. The best pair on the both-era statistic is #12 (+0.007 /
+0.006 over breadth) -- not worth a deep block; it is breadth plus 19 days.

### #0 breadth (reference, the pre-registered rule)

- Proxy 26.13 % / 1.070 / -28.5 %, S 1.332, H 0.872, exposure 66.2 %, 47.9 reb/yr; real 36.09 % / 1.395 (xSh 1.299) / -24.7 %.
- Bootstrap vs live: proxy Sharpe 95 % CI [+0.052, +0.274] P(<=0) 0.001 (20d and 60d); real [+0.036, +0.512] P 0.010 / 0.003.
  Vs matched constant-D (proxy f 90 %, real f 85 %): proxy [+0.046, +0.251] P 0.000; real [+0.021, +0.436] P 0.011.
- LORO vs live: drop dot-com +0.171, GFC +0.170, COVID +0.128, 2022 +0.146, whole SPMO era +0.104.
- One-session lag: proxy 25.95 % / 1.063 / -28.5 % (S +0.190, H +0.122 vs live); real 34.65 % / 1.351 (+0.206).
- 20 bp: proxy live 16.14 % / 0.714 -> candidate 19.36 % / 0.844 (S +0.193, H +0.084); real 22.84 % / 0.933 -> 28.09 % / 1.143.
- SPY-core proxy (breadth analogue RSP/SPY): live 12.94 % / 0.660 (S 0.926, H 0.456) -> 14.72 % / 0.750, dS S +0.075, H +0.102.
  The other four singles on SPY: sma20>=sma60 -0.069 / -0.153, px>=sma100 -0.116 / -0.134, gap200<2% +0.060 / -0.090,
  volratio>1.5 +0.062 / -0.005 (S / H). Only breadth transfers to the independent series with the right sign in both eras.

### #10 breadth OR gap200<2% (best pair)

- Proxy 25.74 % / 1.077 / -28.5 %, S 1.410, H 0.828, exposure 64.5 %, 49.4 reb/yr; real 37.75 % / 1.484 (xSh 1.385) / -19.4 %,
  69 % exposure, 47 reb/yr; 240 flagged proxy D days in 82 episodes (real 91 / 35).
- vs breadth: S +0.078, **H -0.045**, F +0.008; real +0.089. vs matched constant-D f 75 %: S +0.268, H +0.054.
- Bootstrap vs breadth: proxy Sharpe CI [-0.076, +0.096] P(<=0) 0.437 (20d) / 0.433 (60d), log-return [-2.30, +1.73] pp/yr
  P 0.63; real [-0.050, +0.242] P 0.130 / 0.113, log-return [-1.84, +4.45] P 0.25. Vs live: proxy P 0.006, real P 0.002.
- LORO vs breadth: drop dot-com +0.011, GFC +0.011, COVID +0.006, 2022 +0.009, **drop the SPMO era -0.045** -- the whole
  pair-over-single gain is the search era.
- One-session lag: proxy 25.55 % / 1.070 / -28.9 % (S +0.323, H +0.033 vs live); real 38.32 % / 1.495 (+0.350).
- 20 bp: proxy 18.48 % / 0.828 (S +0.256, H +0.010 vs live at 20 bp); vs breadth at 20 bp S +0.064, **H -0.075, F -0.016**;
  real 29.42 % / 1.215 (+0.283 vs live, +0.073 vs breadth).
- SPY analogue: 12.82 % / 0.689, dS vs SPY-live S +0.070, H -0.003 (breadth alone on SPY: +0.075 / +0.102 -- adding the
  200d rule removes the holdout gain on SPY too).

### #30 UNION(breadth | gap200<2% | volratio>1.5) (best union)

- Proxy 26.02 % / 1.091 / -28.5 %, S 1.418, H 0.846; real 37.77 % / 1.495 / -19.4 %; 256 flagged D days in 84 episodes.
- vs breadth: S +0.086, **H -0.026**, F +0.021; real +0.100. Bootstrap vs breadth: proxy [-0.067, +0.121] P 0.339 / 0.318;
  real [-0.058, +0.281] P 0.104 / 0.107. LORO vs breadth: +0.020..+0.026 everywhere except **drop SPMO era -0.026**.
- Lag: 25.04 % / 1.059 (S +0.309, H +0.024 vs live). 20 bp: vs breadth S +0.068, H -0.056, F -0.004. SPY: S +0.069, H -0.002.

### #40 full 5-union (the whole tree)

- Proxy 20.43 % / 0.972 / -28.5 %, S 1.206, H 0.802, exposure 57.2 %; real 27.21 % / 1.286 / -24.0 %; 744 of 934 D days
  flagged (80 %) -- this is "D -> 20 % QLD" wearing five hats (matched control f 20 %: vs control +0.072 / +0.077 / +0.073).
- vs breadth: S -0.126, H -0.070, F -0.098; real -0.109. Bootstrap vs breadth: proxy log-return CI [-8.47, -0.68] pp/yr
  P(<=0) 0.87-0.89; real [-13.41, +0.34] P 0.74-0.75. LORO vs breadth -0.07..-0.10 everywhere.
- 20 bp: 13.59 % / 0.700, below live (F -0.014). SPY: 7.34 % / 0.467, dS S -0.113, H -0.250.

### Drawdown episodes: which days does each single actually dodge?

Real daily. Live MaxDD -32.9 %: peak 2018-08-28 -> trough 2018-12-07 (recovered 2020-01-08).

| single | MaxDD (window) | its DD inside the live window | flagged episodes inside the live window (days, gain vs live) | top-3 gain episodes (dates, pp vs live) | total vs live |
|---|---|---|---|---|---|
| breadth | -24.7 % (2025-02-18 -> 2025-04-07) | -18.3 % | 3 (6 d, +19.7 pp) | 2022-01-05..01-19 +10.4; 2020-02-25..02-26 +9.1; 2018-10-19..10-23 +8.6 | +53.2 pp |
| sma20>=sma60 | -28.1 % (2025-11-07 -> 2026-03-19) | -22.0 % | 2 (5 d, +15.1 pp) | 2020-02-25..03-06 +14.3; 2018-10-05..10-10 +12.4; 2024-07-24..08-06 +11.9 | +3.8 pp |
| px>=sma100 | -26.2 % (2025-11-07 -> 2026-03-19) | -26.0 % | 1 (3 d, +9.9 pp) | 2026-07-16..07-28 +9.9; 2018-10-05..10-09 +9.9; 2020-02-25..02-26 +9.1 | +7.2 pp |
| gap200<2% | -24.6 % (2020-02-21 -> 2020-03-20) | -21.9 % | 4 (10 d, +15.1 pp) | 2025-03-03..03-07 +10.1; 2018-10-18..10-23 +8.9; 2016-01-04..01-06 +8.7 | +28.1 pp |
| volratio>1.5 | -24.7 % (2025-02-18 -> 2025-04-07) | -21.5 % | 2 (7 d, +15.7 pp) | 2018-10-16..10-23 +13.1; 2020-03-02..03-06 +13.0; 2020-03-10 +4.2 | +31.9 pp |

Worst episodes per single (real): breadth 2021-12-20..21 -6.2 pp; sma20>=sma60 2018-02-08..13 -9.8 and 2021-05-12..21
-9.4; px>=sma100 2025-11-21..26 -9.4 and 2019-06-06..17 -9.2; gap200<2% 2019-06-05..06 -5.2; volratio>1.5 2018-02-12..13
-3.9.

Reading. All five flag the October 2018 sell-off inside the live drawdown window (2018-10-05..10-23) and four of five flag
late February / early March 2020; those two episodes are the bulk of each rule's lifetime gain (breadth +34.6 of +53.2 pp, volratio>1.5 +30.3 of +31.9 pp), and for sma20>=sma60 and px>=sma100 they EXCEED the lifetime total (+3.8 / +7.2 pp): everything else those two rules do nets out negative. Once Oct-2018 is out of the
path, the next-worst drawdown sets the MaxDD: breadth and volratio>1.5 both leave 2025-02-18 -> 2025-04-07 untouched and
land on -24.7 % (the outside table's -24.48 / -24.48); gap200<2% flags 2025-03-03..07 and so lands on 2020-02-21 ->
2020-03-20 at -24.6 % (the -24.50); px>=sma100 and sma20>=sma60 flag neither and land on 2025-11 -> 2026-03 at -26.2 /
-28.1 % (the -26.08 / -27.90). **Confirmed: the near-identical MaxDDs are one dodged episode and one shared floor, not
five independent risk reductions.** The proxy tells the same story with a different live MaxDD (2015-07-17 -> 2016-06-23,
-33.6 %): breadth's proxy MaxDD is -28.5 % (2007-11 -> 2009-03), and its 26-year gain is +84.5 pp of which the top five
episodes (2022-01, 2015-08-20, 2020-02, 2008-01, 2018-10) are +45.8 pp.

## 7. A tree of special cases: what each case uniquely contributes

D1 = default (live 100 % QLD); D2x = one case each; any flagged day -> cash. "uniq" = D days flagged by this case and no
other case of the union; "J rest" = Jaccard of the case against the union of the other cases; "drop-case" = union with the
case minus union without it (positive = the case helps); "QLD next-day" = mean next-session QLD-leg return on the case's
unique days vs the days it shares with another case (t = unique minus shared). A case earns its place only if its unique
days are money-losing for QLD in both proxy eras.

**Best union #30 `UNION(breadth | gap200<2% | volratio>1.5)`** -- proxy 26.02 % / 1.091 / -28.5 %, S 1.418, H 0.846; real 37.77 % / 1.495 / -19.4 %.

| case | flag | uniq (episodes) | J rest | drop-case dS S / H / F | drop dCAGR / dMDD | real drop dSh / dCAGR / dMDD | QLD next-day, uniq vs shared: S (t) | H (t) | real (t) | earns? |
|---|---|---|---|---|---|---|---|---|---|---|
| breadth | 124 | 85 (30) | 0.15 | +0.098 / +0.044 / +0.066 | +1.36 pp / +1.0 pp | +0.111 / +2.19 / +1.3 | -32 vs -186 bp (1.2), n 36 | -28 vs -121 bp (0.7), n 49 | -35 vs -186 bp (1.2), n 36 | **EARNS** |
| gap200<2% | 144 | 113 (50) | 0.12 | +0.079 / **-0.031** / +0.015 | -0.16 / +0.0 | +0.089 / +1.63 / +5.2 | -40 vs -63 (0.2), n 31 | **+21** vs -78 (0.8), n 82 | -41 vs -66 (0.2), n 31 | no |
| volratio>1.5 | 34 | 16 (8) | 0.07 | +0.008 / +0.019 / +0.014 | +0.28 / +0.0 | +0.011 / +0.02 / -0.0 | **+13** vs -322 (1.8), n 10 | -109 vs +67 (-0.9), n 6 | +11 vs -323 (1.8), n 10 | no |

**Full 5-union #40** -- proxy 20.43 % / 0.972 / -28.5 %, S 1.206, H 0.802; real 27.21 % / 1.286 / -24.0 %.

| case | flag | uniq (episodes) | J rest | drop-case dS S / H / F | drop dCAGR | real drop dSh / dCAGR | QLD next-day, uniq vs shared: S (t) | H (t) | real (t) | earns? |
|---|---|---|---|---|---|---|---|---|---|---|
| breadth | 124 | 20 (11) | 0.14 | +0.013 / +0.018 / +0.016 | +0.28 pp | +0.015 / +0.22 | -11 vs -105 bp (0.7), n 8 | -7 vs -61 (0.4), n 12 | -11 vs -107 (0.8), n 8 | **EARNS** |
| sma20>=sma60 | 415 | 73 (40) | 0.46 | **-0.190 / -0.037 / -0.103** | -3.21 | -0.202 / -6.51 | **+177** vs -36 (3.8), n 35 | +50 vs -9 (1.3), n 38 | +180 vs -37 (3.9), n 35 | no (harmful) |
| px>=sma100 | 496 | 175 (50) | 0.43 | **-0.134** / +0.005 / -0.053 | -1.97 | -0.140 / -4.62 | **+63** vs -28 (2.4), n 70 | +8 vs -4 (0.4), n 105 | +64 vs -29 (2.5), n 70 | no (harmful) |
| gap200<2% | 144 | 81 (33) | 0.08 | +0.057 / **-0.060** / -0.011 | -0.69 | +0.063 / +0.98 | -64 vs -39 (-0.2), n 15 | **+41** vs -69 (1.5), n 66 | -61 vs -43 (-0.1), n 15 | no |
| volratio>1.5 | 34 | 2 (1) | 0.04 | +0.021 / +0.000 / +0.009 | +0.21 | +0.022 / +0.50 | -229 vs -178, n 2 | (no unique holdout days) | -217 vs -181, n 2 | no (duplicate) |

Reading.
- **Breadth is the only case that earns its place**: its unique days are money-losing for QLD in both eras (and on the
  real rows), and removing it costs Sharpe in both eras of both unions. It is also the case with the LEAST overlap with the
  rest (J 0.14-0.15) -- it is genuinely a different signal, and it is the one that works.
- **gap200<2% is a search-era case**: its 113 unique days lose -40 bp/day in 2015+ but MAKE +21 bp/day (+41 in the 5-union)
  in 2007-2015; dropping it from the best union raises holdout Sharpe +0.031. Its search-era value is Oct-2018 and Mar-2025
  (section 6). It fails the "both eras" bar.
- **volratio>1.5 is a duplicate**: 34 days, of which 2 are unique in the 5-union and 16 in the 3-union; 82 % of its days
  are sma20>=sma60 days and 44 % are breadth days; its unique search-era days are +13 bp/day; its marginal effect is
  +0.01..+0.02 everywhere, i.e. nothing.
- **sma20>=sma60 and px>=sma100 are one signal twice (J 0.47) and harmful as tree cases.** Their unique days -- D days where
  the intermediate trend is intact but neither breadth, the 200d line nor vol is flagging -- are the healthy-pullback days:
  +177 and +63 bp/day for QLD in the search era (t 3.8 / 2.4), +50 / +8 in the holdout. As singles they beat live only
  through the days they share with breadth / gap200 / volratio (Oct-2018, Feb-2020). Adding them to the tree exits the days
  that pay for the D row.
- **Does the tree beat the single pre-registered breadth rule in both eras?** No union does. The closest, #30, is +0.086 in
  the search era and -0.026 in the holdout (-0.045 / -0.075 for #10 / #37 with the 200d rule; #29 BR|P100|VR is +0.004 /
  -0.002, i.e. breadth). The full tree #40 is -0.126 / -0.070.

### Post-hoc, not pre-registered, not in the permutation: per-case actions on #30

Each case independently cash or 50 % QLD / 50 % cash; a day flagged by any cash case is cash, otherwise half.

| BR / G200 / VR | proxy CAGR / Sharpe / MaxDD | exp | S Sh | H Sh | real CAGR / Sharpe / MaxDD |
|---|---|---|---|---|---|
| cash / cash / cash (= #30) | 26.02 % / 1.091 / -28.5 % | 64.3 % | 1.418 | 0.846 | 37.77 % / 1.495 / -19.4 % |
| cash / cash / half | 25.89 % / 1.085 / -28.5 % | 64.4 % | 1.417 | 0.837 | 37.78 % / 1.492 / -19.4 % |
| cash / half / cash | 26.16 % / 1.090 / -28.5 % | 65.1 % | 1.389 | 0.867 | 37.05 % / 1.462 / -22.0 % |
| cash / half / half | 26.15 % / 1.089 / -28.5 % | 65.2 % | 1.387 | 0.865 | 37.05 % / 1.459 / -22.0 % |
| half / cash / cash | 25.38 % / 1.064 / -28.9 % | 64.8 % | 1.380 | 0.828 | 36.75 % / 1.451 / -19.3 % |
| half / cash / half | 24.73 % / 1.040 / -28.9 % | 65.0 % | 1.338 | 0.816 | 35.52 % / 1.406 / -19.3 % |
| half / half / cash | 25.04 % / 1.046 / -29.2 % | 65.8 % | 1.345 | 0.822 | 35.85 % / 1.413 / -22.0 % |
| half / half / half | 24.26 % / 1.017 / -29.2 % | 66.0 % | 1.283 | 0.817 | 33.95 % / 1.345 / -22.4 % |

Halving the 200d case moves the holdout from 0.846 to 0.867 (still below breadth alone, 0.872) and costs -0.029 in the
search era; every variant that halves breadth loses. There is no per-case sizing that rescues the tree.

## 8. Verdict

**Does any pair add to the pre-registered breadth rule on its own terms?** No. The two pairs that beat breadth in both eras
do so by +0.005..+0.007 Sharpe -- 19 and 438 extra days for nothing measurable. The pairs and unions that look strong on
the real daily rows (#10 `breadth OR gap200<2%` 37.75 % / 1.484 / -19.4 %; #30 adding volratio, 37.77 % / 1.495 / -19.4 %)
are the breadth rule plus a second look at October 2018 and March 2020 from the 200d line, and the second look costs
-0.045 / -0.026 in the 2007-2015 holdout, fails the bootstrap against breadth (P(<=0) 0.43 proxy, 0.11 real), reverses when
the SPMO era is removed, goes negative at 20 bp, and does not transfer to SPY in the holdout. On the whole-grid permutation
the "combination beats its best member in both eras" statistic is p = 0.186.

**Is the extra a second look at the same days?** In day-set terms, mostly not (breadth's Jaccard with the others is 0.10-0.12);
in money terms, yes: every rule's gain is Oct-2018 + Feb/Mar-2020, all five leave the same Feb-Apr 2025 drawdown, and the
two rules that flag genuinely different days (sma20>=sma60, px>=sma100) flag days on which QLD makes +63..+177 bp/day.

**The tree.** Breadth earns its place; gap200<2% is a search-era case that reverses in the holdout; volratio>1.5 is a
duplicate; sma20>=sma60 and px>=sma100 are one signal twice and actively harmful as exit cases. No tree beats the single
pre-registered breadth rule in both eras. **D stays 100 % QLD; the breadth gate stays under its pre-registered forward test
unchanged; nothing from this line is a candidate for application.**
