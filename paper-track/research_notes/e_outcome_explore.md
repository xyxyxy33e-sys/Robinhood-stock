# State E episodes by how they end — descriptive exploration, 2026-09-19 (NOT a candidate, NOT applied)

Owner question: split the E episodes into the ones that BREAK (exit to F: the
50d crosses below the 200d) and the ones that REVERSE (exit to D/A/B/C: price
recovers above the 50d), and describe whether the other market data looked
different at the time. Script `paper-track/e_outcome_explore.py`; full run log
`e_outcome_explore_run.log` (every number below is copied from it). Pure
Python, seeded (20260919). Research only: no action rows, no backtest of any
rule, no recommendation, nothing in the live code or data changed.

Prior E work, not re-run: `e_pair_test.md` (82-candidate pre-registered grid
inside E, nothing clears permutation), STRATEGY.md "State E pairs and unions"
and "D and E substates". Those asked "is there a good/bad E DAY rule". This
asks a different thing: do BREAK and REVERSAL *episodes* differ at entry.

## 0. Summary

- **32 completed E episodes, 16 BREAK / 16 REVERSAL** (exit counts F 16, D 15,
  A 1). Real-instrument era (2015-11+): 13 episodes, 5 BREAK / 8 REVERSAL.
  No ongoing episode.
- **The groups differ in what happens inside E, not in what was visible at
  entry.** BREAK episodes are longer (median 16.5 vs 6.5 sessions), fall
  further inside E (median QQQ −5.4% vs −0.7%), and are already lower by
  session 3 (QQQ return entry→session 3: BREAK median −0.99%, REVERSAL
  +0.63%; AUC 0.188, p 0.003). The single feature that clears every
  multiplicity check, `below200_pct@avg3` (depth below the 200d averaged over
  E sessions 1–3; AUC 0.148, p_MW 0.001, permutation p 0.032, LOO AUC 0.797),
  is exactly this in-episode path. It is not available at entry and for the
  short REVERSALs it partly *is* the reversal.
- **Nothing measured BEFORE or AT entry separates the groups.** Over the 41
  pre-entry columns (VIX, VXN, rates, QQEW and RSP breadth, price structure,
  realised vol, regime history, QQQ/SPY relative) the largest |AUC−0.5| is
  0.211 (`QQEW_pct@approach10`, AUC 0.711 on 11 vs 11 episodes, p_MW 0.094);
  the permutation null 95th percentile is 0.332 and the permutation p is
  **0.701**. The best full-coverage pre-entry feature (`below200_pct@entry`,
  AUC 0.363) has LOO AUC 0.512; the two-feature pre-entry pair also 0.512.
- **The mechanical 50d–200d spread does not predict the break here.** BREAKs
  enter with a narrower spread on average (mean 2.65% vs 4.07%, median 2.79%
  vs 3.04%) but AUC is only 0.406 (p 0.366) and a median split gives 8/16
  BREAK on each side. The spread is tautologically *sufficient* to explain the
  long-spread REVERSALs (2020-03: spread 10.6–11.1%, 34–35 flat-price sessions
  to cross) but it does not sort the middle, where most episodes live.
- **n is the binding constraint.** With 16/16 the minimum detectable
  |AUC−0.5| for one pre-specified feature is about 0.20 (AUC 0.70), Cohen's d
  about 0.99 for 80% power; with 57 correlated columns the null max
  |AUC−0.5| has median 0.242 and 95th percentile 0.338, and 81% of label
  shuffles produce at least one |AUC−0.5| > 0.20 by chance.

## 1. Episodes and labels

Enumerated from `state.compute_states` on `data/qqq_long_history.csv`
(1999-09-15..2026-09-04, 6784 sessions). Label = first non-E state after the
run: BREAK if F, REVERSAL otherwise. `ret_in` is QQQ from the close before
entry to the exit close; `post20/60` are QQQ from the exit close (for BREAKs
the exit close is the first F day).

```
  # start      end          n  prior exit  label     ret_in  post20  post60   VIX  brPct  spread%  flatX
  0 2000-07-28 2000-08-04   6   A    D   REVERSAL    -1.9    13.9   -14.8  20.8     --     2.51     19
  1 2000-08-10 2000-08-11   2   D    D   REVERSAL    -0.6     1.9    -9.5  19.2     --     2.85     15
  2 2000-09-11 2000-09-21   9   A    F   BREAK       -7.8    -3.1   -27.2  18.4     --     1.16      9
  3 2003-01-24 2003-02-11  13   F    F   BREAK       -5.3     0.3    15.0  31.5     --     0.09    115
  4 2003-02-28 2003-03-12   9   F    A   REVERSAL    -2.2     5.1    24.3  29.6     --     0.02    102
  5 2004-04-30 2004-05-04   3   D    D   REVERSAL    -1.1     3.3    -1.0  17.2     --     2.98     27
  6 2004-05-10 2004-05-24  11   D    D   REVERSAL     1.3     5.3    -4.5  19.8     --     2.12     23
  7 2004-07-13 2004-07-20   6   D    F   BREAK       -0.5    -6.1     0.5  14.5     --     0.20     26
  8 2005-03-22 2005-04-25  24   D    F   BREAK       -3.3     7.0    11.5  14.3     --     1.92     26
  9 2006-05-12 2006-06-13  22   D    F   BREAK       -8.6    -0.9     3.3  14.2     --     2.57     32
 10 2008-01-07 2008-01-31  18   D    F   BREAK       -6.8    -4.8     4.7  23.8   0.14     5.22     30
 11 2008-06-25 2008-07-07   8   F    F   BREAK       -4.1    -1.0   -13.3  21.1   0.36     0.07    137
 12 2010-06-07 2010-06-10   4   D    D   REVERSAL    -0.0    -1.0     2.1  36.6   0.10     6.79     26
 13 2010-06-29 2010-07-20  15   D    F   BREAK        0.3     0.2    11.6  34.1   0.09     3.54     12
 14 2011-06-17 2011-06-27   7   D    D   REVERSAL     2.2     7.9     0.2  21.9   0.92     4.81     23
 15 2011-08-04 2011-08-16   9   D    F   BREAK       -5.1     2.7     5.4  31.7   0.00     1.37     19
 16 2011-12-14 2011-12-30  12   D    D   REVERSAL     0.1     8.4    21.7  26.0   0.43     0.61     14
 17 2012-11-07 2012-12-12  25   D    F   BREAK        0.2     2.2     4.4  19.1   0.99     3.95     24
 18 2015-08-21 2015-09-29  27   D    F   BREAK       -7.1    13.7    13.2  28.0   0.29     3.01     25
 19 2016-01-07 2016-02-03  19   D    F   BREAK       -6.1     3.9     4.0  25.0   0.46     3.52     23
 20 2016-05-09 2016-05-23  11   F    D   REVERSAL     0.7     1.1    10.3  14.6   0.96     0.04     25
 21 2016-06-17 2016-06-22   4   A    D   REVERSAL    -0.7     5.5     9.4  19.4   0.94     0.61      8
 22 2016-06-24 2016-06-27   2   D    F   BREAK       -6.0    11.3    15.6  25.8   0.93     0.27      3
 23 2018-10-11 2018-10-11   1   D    D   REVERSAL    -1.2     2.9    -5.2  25.0   0.28     6.31     38
 24 2018-10-24 2018-11-06  10   D    D   REVERSAL    -1.7    -2.0     0.5  25.2   0.03     5.26     25
 25 2018-11-12 2018-11-30  14   D    F   BREAK       -1.3    -8.6     3.0  20.4   1.00     3.11     15
 26 2019-06-03 2019-06-04   2   D    D   REVERSAL     0.6     8.6     5.8  18.9   0.55     5.43     40
 27 2020-03-09 2020-03-09   1   D    D   REVERSAL    -6.9     1.5    22.3  54.5   0.09    11.08     35
 28 2020-03-11 2020-04-09  22   D    D   REVERSAL    -1.6    11.9    27.8  53.9   0.00    10.59     34
 29 2022-01-20 2022-02-28  27   D    F   BREAK       -5.4     5.2   -17.2  25.6   0.16     7.06     33
 30 2025-03-10 2025-04-11  25   D    F   BREAK       -7.6    11.8    22.2  27.9   0.99     5.34     27
 31 2026-03-20 2026-04-07  12   D    D   REVERSAL    -0.7    15.8    21.1  26.8   0.30     3.11     17
```
(`brPct` = QQEW/QQQ breadth percentile, available from 2007-07; `spread%` =
(SMA50−SMA200)/price; `flatX` = sessions until SMA50 < SMA200 if price stayed
at the entry close.) Prior states: D 25, A 3, F 4.

| group | n | length (median) | ret_in mean / median | post20 mean / median | post60 mean / median |
|---|---|---|---|---|---|
| BREAK | 16 | 16.5 | −4.65% / −5.35% | +2.12% / +1.25% | +3.54% / +4.53% |
| REVERSAL | 16 | 6.5 | −0.88% / −0.74% | +5.64% / +5.18% | +6.90% / +3.95% |

Real-instrument era (2015-11+): 13 episodes, BREAK 5 (2016-01-07, 2016-06-24,
2018-11-12, 2022-01-20, 2025-03-10), REVERSAL 8.

Note the post-exit returns: after a BREAK, QQQ's next 60 sessions were
positive in 13 of 16 cases (mean +3.5%), i.e. the first F day is on average
not a bad time to own QQQ — consistent with the repo's earlier finding that
F's damage is concentrated in a few long episodes.

## 2. Feature table

57 columns from 27 base quantities × {@entry, @approach10 (entry minus 10
sessions earlier), @avg3 (mean of E sessions 1–3)}. AUC is the probability
that a BREAK episode has the higher value (AUC < 0.5: lower value → BREAK).
Coverage: VIX/rates/price features 16/16; VXN 15/14; RSP breadth 13–14/11–13;
QQEW breadth 11/11 (2007-07+); drawdown-from-252-high 15–16/14.

Power statement (from the log): with 16/16 the SE of an AUC near 0.5 is
0.104, so the 5% two-sided minimum detectable |AUC−0.5| for a *single*
pre-specified feature is about 0.20 (AUC ≈ 0.70); Cohen's d ≈ 0.99 for 80%
power. Bonferroni threshold for 57 columns: p < 0.00088.

Top 15 by |AUC−0.5| (full table in the log):

```
  feature                          fam           nB nR     meanB     medB    meanR     medR     diff  Welch t     p_t    p_MW    AUC
  below200_pct@avg3                price         16 16    -3.546   -3.776   -1.609   -1.198   -1.936    -3.67   0.001   0.001  0.148
  QQEW_pct@approach10              breadth       11 11     0.109    0.119    0.000   -0.032    0.109     1.35   0.192   0.094  0.711
  QQEW_x60@approach10              breadth       11 11     0.007    0.009   -0.002   -0.004    0.010     1.26   0.227   0.140  0.686
  dd_from_252hi@avg3               price         16 14   -13.567  -11.663  -12.427   -9.269   -1.140    -0.42   0.680   0.096  0.321
  below200_pct@entry               price         16 16    -2.614   -2.446   -1.841   -1.631   -0.772    -1.83   0.078   0.187  0.363
  below50_pct@avg3                 price         16 16    -5.818   -6.200   -5.198   -4.307   -0.619    -0.56   0.582   0.243  0.379
  since_last_F@entry               regime        16 16   285.750  242.500  202.750  210.500   83.000     1.07   0.294   0.258  0.617
  spread50_200_pct@approach10      spread        16 16    -0.481   -0.582   -0.211    0.093   -0.270    -0.75   0.458   0.274  0.387
  rvol30@approach10                realised_vol  16 16     0.713    1.348    4.114    1.967   -3.401    -1.64   0.115   0.291  0.391
  spread_chg20@entry               spread        16 16    -0.616   -1.082   -0.062   -0.239   -0.553    -0.73   0.472   0.309  0.395
  slope_10y3m@approach10           rates         16 16    -0.113   -0.090    0.005   -0.055   -0.118    -1.40   0.173   0.327  0.398
  ret20_pre@entry                  price         16 16    -5.004   -4.673   -6.542   -6.148    1.538     1.02   0.317   0.327  0.602
  VIX@approach10                   vol_implied   16 16     4.956    4.535    5.008    2.260   -0.053    -0.02   0.985   0.346  0.598
  spread50_200_pct@avg3            spread        16 16     2.531    2.700    3.997    2.862   -1.466    -1.48   0.151   0.346  0.402
  VIX_minus_m20@avg3               vol_implied   16 16     5.043    3.349    5.128    1.493   -0.085    -0.03   0.976   0.366  0.594
```

Counts: features with p_t < 0.05: **1/57**; p_MW < 0.05: **1/57**; under
Bonferroni: 1 (the same column); expected false positives at 5% if all null
and independent: 2.9. Columns with |AUC−0.5| > 0.20: 2; > 0.25: 1.

What does *not* differ (all AUC within 0.46–0.56, p_MW > 0.6): VIX level at
entry (BREAK mean 23.5 vs REVERSAL 26.8, AUC 0.461, p 0.706), VIX 252-day
percentile (0.73 vs 0.68), VIX 5-day change, VXN level and VXN−VIX spread,
the 2y level, the 10y−2y and 10y−3m slopes, 20-session changes in 2y and 10y,
QQEW and RSP breadth *levels* (x60 and percentile at entry), the 10d/30d vol
ratio, sessions in A over the prior 120, prior state D vs not, QQQ/SPY
20-session relative return, drawdown from the 252-day high at entry, and the
flat-price sessions-to-cross. Depth below the 50d at entry is identical
(−5.0% vs −5.5%, AUC 0.523).

The only pre-entry columns that lean anywhere are the *approach* of QQEW
breadth (QQEW/QQQ 60-session relative strength *improving* into a BREAK:
median percentile change +0.12 vs −0.03; AUC 0.711/0.686, p 0.094/0.140, on
11 vs 11 episodes only), depth below the 200d at entry (BREAK median −2.4% vs
−1.6%, AUC 0.363, p 0.187) and sessions since the last F (BREAK median 243
vs 211, AUC 0.617, p 0.258). None reaches nominal 5%.

Real-era subset (13 episodes, 5/8) for the top-10 full-history columns: the
ranking mostly holds directionally (`below200_pct@avg3` 0.148 → 0.150,
`QQEW_pct@approach10` 0.711 → 0.775, `QQEW_x60@approach10` 0.686 → 0.875,
`below200_pct@entry` 0.363 → 0.250), but with 5 breaks an AUC moves by 0.2
when one episode changes side.

### 2b. The @avg3 caveat, checked

`@avg3` columns average E sessions 1–3, so they contain the price path
*inside* the episode and are truncated for the 5 episodes shorter than 3
sessions (1 BREAK, 4 REVERSAL). They are not entry information. Checks from
the log:

- `below200_pct@avg3` on episodes with n ≥ 3 only: AUC 0.167, p 0.003
  (15 vs 12) — survives the truncation issue.
- `below200_pct@entry` on the same episodes: AUC 0.367, p 0.242 — the
  entry-day depth alone does not separate.
- QQQ return from entry close to E session 3: BREAK mean −1.48% / median
  −0.99%, REVERSAL +0.58% / +0.63%; AUC 0.188, p 0.003 (all 32); AUC 0.228,
  p 0.017 on n ≥ 3 episodes.
- Depth below the 200d on session 3 alone (n ≥ 3): BREAK median −3.38% vs
  REVERSAL −1.90%, AUC 0.183, p 0.005.

So the separation is real in the data but it is the *continuation of the
decline over the first three E sessions*, i.e. the beginning of the outcome,
not a precondition of it. A 4-session REVERSAL that recovers on session 4 is
already turning by session 3; a 25-session BREAK is still falling.

## 3. Multiple comparisons and permutation

Labels shuffled 2000 times; for each shuffle the max |AUC−0.5| across all
columns (each on its own coverage).

| set | real max \|AUC−0.5\| | null median | 90th | 95th | 99th | perm p |
|---|---|---|---|---|---|---|
| all 57 columns | 0.352 (`below200_pct@avg3`) | 0.242 | 0.316 | 0.338 | 0.383 | **0.032** |
| 41 pre-entry columns (@entry, @approach10) | 0.211 (`QQEW_pct@approach10`) | 0.234 | 0.309 | 0.332 | 0.380 | **0.701** |

81% of shuffles produce at least one column with |AUC−0.5| > 0.20, so a
"0.7 AUC feature" is what noise looks like at this n. The count of columns
with p_MW < 0.05 (real 1) is at the null median (2; 95th 8; p 0.714).

Reading: the whole-set permutation is significant only because of the
in-episode `@avg3` column. Restricted to what was knowable at entry, the
best feature sits *below* the null median for the max statistic.

## 4. Leave-one-episode-out logistic

Ridge 0.5 on standardised slopes, Newton solve, predictions pooled over the
32 held-out episodes. (Pooled LOO-AUC has a known downward bias for null
features — leaving out a positive lowers that fold's intercept — so LOO AUCs
below 0.5 read as "no signal", not inverse signal; the extreme is
`flat_sessions_to_cross@entry` at LOO 0.000 from in-sample 0.486.)

| model | in-sample AUC | LOO AUC | n |
|---|---|---|---|
| `below200_pct@avg3` (in-episode) | 0.852 | **0.797** | 32 |
| `below200_pct@avg3` + `since_last_F@entry` | 0.836 | 0.793 | 32 |
| `spread50_200_pct@entry` + `below200_pct@avg3` | 0.867 | 0.809 | 32 |
| `below200_pct@entry` (best full-coverage pre-entry) | 0.637 | **0.512** | 32 |
| `below200_pct@entry` + `since_last_F@entry` (pre-entry pair, corr −0.15) | 0.660 | **0.512** | 32 |
| `QQEW_pct@approach10` (2007-07+ episodes) | 0.711 | 0.545 | 22 |
| `since_last_F@entry` | 0.617 | 0.418 | 32 |
| `spread50_200_pct@entry` | 0.594 | 0.500 | 32 |
| `spread_chg20@entry` | 0.605 | 0.398 | 32 |

The in-episode path holds up out of fold (0.80), everything pre-entry
collapses to a coin flip (0.51–0.55). Adding the spread to the path feature
adds 0.01. LOO on the real era alone is not run: 13 episodes with 5 breaks
cannot support a fitted model.

## 5. Narrative episode tables

BREAK episodes (16). `flatX` = sessions to cross if price flatlined; `A120`
= sessions in A over the prior 120; `then` = QQQ after the exit close.

```
  2000-09-11..2000-09-21 ( 9d, prior A, exit F): VIX  18.4 (pct 0.06) VXN    -- | QQEW pct   -- RSP pct   -- | 10y-2y -0.35 | spread  1.16% chg20 -1.58 flatX   9 | dd252    --% ret20   1.9% rvol30   32 A120  37 | in-E  -7.8% then +20d  -3.1% +60d -27.2%
  2003-01-24..2003-02-11 (13d, prior F, exit F): VIX  31.5 (pct 0.73) VXN  39.8 | QQEW pct   -- RSP pct   -- | 10y-2y  2.28 | spread  0.09% chg20  5.88 flatX 115 | dd252 -36.4% ret20  -2.1% rvol30   32 A120   0 | in-E  -5.3% then +20d   0.3% +60d  15.0%
  2004-07-13..2004-07-20 ( 6d, prior D, exit F): VIX  14.5 (pct 0.03) VXN  21.4 | QQEW pct   -- RSP pct   -- | 10y-2y  1.92 | spread  0.20% chg20 -0.79 flatX  26 | dd252  -7.9% ret20  -2.1% rvol30   16 A120  69 | in-E  -0.5% then +20d  -6.1% +60d   0.5%
  2005-03-22..2005-04-25 (24d, prior D, exit F): VIX  14.3 (pct 0.45) VXN  18.0 | QQEW pct   -- RSP pct 0.03 | 10y-2y  0.77 | spread  1.92% chg20 -3.03 flatX  26 | dd252 -10.7% ret20  -2.1% rvol30   14 A120  39 | in-E  -3.3% then +20d   7.0% +60d  11.5%
  2006-05-12..2006-06-13 (22d, prior D, exit F): VIX  14.2 (pct 0.91) VXN  17.1 | QQEW pct   -- RSP pct 0.20 | 10y-2y  0.18 | spread  2.57% chg20 -0.05 flatX  32 | dd252  -7.0% ret20  -4.5% rvol30   13 A120  82 | in-E  -8.6% then +20d  -0.9% +60d   3.3%
  2008-01-07..2008-01-31 (18d, prior D, exit F): VIX  23.8 (pct 0.83) VXN  29.4 | QQEW pct 0.14 RSP pct 0.12 | 10y-2y  1.10 | spread  5.22% chg20 -2.45 flatX  30 | dd252 -12.5% ret20  -7.9% rvol30   25 A120  68 | in-E  -6.8% then +20d  -4.8% +60d   4.7%
  2008-06-25..2008-07-07 ( 8d, prior F, exit F): VIX  21.1 (pct 0.39) VXN  26.4 | QQEW pct 0.36 RSP pct 0.71 | 10y-2y  1.30 | spread  0.07% chg20  3.10 flatX 137 | dd252 -13.6% ret20  -3.4% rvol30   21 A120   0 | in-E  -4.1% then +20d  -1.0% +60d -13.3%
  2010-06-29..2010-07-20 (15d, prior D, exit F): VIX  34.1 (pct 0.96) VXN  35.0 | QQEW pct 0.09 RSP pct 0.11 | 10y-2y  2.36 | spread  3.54% chg20 -3.84 flatX  12 | dd252 -14.2% ret20  -4.0% rvol30   28 A120  58 | in-E   0.3% then +20d   0.2% +60d  11.6%
  2011-08-04..2011-08-16 ( 9d, prior D, exit F): VIX  31.7 (pct 1.00) VXN  31.7 | QQEW pct 0.00 RSP pct 0.00 | 10y-2y  2.20 | spread  1.37% chg20 -1.56 flatX  19 | dd252  -9.1% ret20  -8.5% rvol30   24 A120  65 | in-E  -5.1% then +20d   2.7% +60d   5.4%
  2012-11-07..2012-12-12 (25d, prior D, exit F): VIX  19.1 (pct 0.62) VXN  20.4 | QQEW pct 0.99 RSP pct 0.98 | 10y-2y  1.41 | spread  3.95% chg20 -1.40 flatX  24 | dd252  -8.8% ret20  -6.1% rvol30   15 A120  66 | in-E   0.2% then +20d   2.2% +60d   4.4%
  2015-08-21..2015-09-29 (27d, prior D, exit F): VIX  28.0 (pct 1.00) VXN  30.2 | QQEW pct 0.29 RSP pct 0.39 | 10y-2y  1.41 | spread  3.01% chg20 -0.76 flatX  25 | dd252 -10.2% ret20  -7.8% rvol30   20 A120 109 | in-E  -7.1% then +20d  13.7% +60d  13.2%
  2016-01-07..2016-02-03 (19d, prior D, exit F): VIX  25.0 (pct 0.94) VXN  26.8 | QQEW pct 0.46 RSP pct 0.09 | 10y-2y  1.20 | spread  3.52% chg20  1.68 flatX  23 | dd252  -8.9% ret20  -8.5% rvol30   20 A120  48 | in-E  -6.1% then +20d   3.9% +60d   4.0%
  2016-06-24..2016-06-27 ( 2d, prior D, exit F): VIX  25.8 (pct 0.91) VXN  24.9 | QQEW pct 0.93 RSP pct 0.70 | 10y-2y  0.93 | spread  0.27% chg20 -0.34 flatX   3 | dd252  -9.4% ret20  -4.8% rvol30   17 A120  16 | in-E  -6.0% then +20d  11.3% +60d  15.6%
  2018-11-12..2018-11-30 (14d, prior D, exit F): VIX  20.4 (pct 0.88) VXN  28.1 | QQEW pct 1.00 RSP pct 0.50 | 10y-2y  0.25 | spread  3.11% chg20 -2.86 flatX  15 | dd252 -10.9% ret20  -3.4% rvol30   33 A120  94 | in-E  -1.3% then +20d  -8.6% +60d   3.0%
  2022-01-20..2022-02-28 (27d, prior D, exit F): VIX  25.6 (pct 0.93) VXN  30.6 | QQEW pct 0.16 RSP pct 0.49 | 10y-2y  0.75 | spread  7.06% chg20 -0.49 flatX  33 | dd252 -10.5% ret20  -7.1% rvol30   22 A120  87 | in-E  -5.4% then +20d   5.2% +60d -17.2%
  2025-03-10..2025-04-11 (25d, prior D, exit F): VIX  27.9 (pct 0.99) VXN  28.8 | QQEW pct 0.99 RSP pct 0.89 | 10y-2y  0.33 | spread  5.34% chg20 -1.37 flatX  27 | dd252 -12.4% ret20  -9.6% rvol30   23 A120 106 | in-E  -7.6% then +20d  11.8% +60d  22.2%
```

Eyeball: BREAKs happen with VIX anywhere from 14 (2004, 2005, 2006) to 34
(2010); with QQEW breadth percentile at 0.00 (2011-08) and at 1.00
(2018-11); with the curve inverted (2000) and at +2.4 (2010); with the spread
at 0.07% (a re-break right after leaving F, 2008-06) and at 7.06% (2022-01).
Only 3 of the 16 were followed by a negative 60-session QQQ return, and those
3 (2000-09, 2008-06, 2022-01) are the ones that turned into the long F
episodes; 2004-07 was flat (+0.5%).

REVERSAL episodes with the largest post-exit 60-session gain (top 8 of 16):

```
  2020-03-11..2020-04-09 (22d, prior D, exit D): VIX  53.9 (pct 0.99) VXN  50.7 | QQEW pct 0.00 RSP pct 0.00 | 10y-2y  0.32 | spread 10.59% chg20  2.07 flatX  34 | dd252 -17.6% ret20 -15.9% rvol30   44 A120  99 | in-E  -1.6% then +20d  11.9% +60d  27.8%
  2003-02-28..2003-03-12 ( 9d, prior F, exit A): VIX  29.6 (pct 0.57) VXN  40.3 | QQEW pct   -- RSP pct   -- | 10y-2y  2.18 | spread  0.02% chg20 -0.52 flatX 102 | dd252 -34.9% ret20   2.5% rvol30   26 A120   0 | in-E  -2.2% then +20d   5.1% +60d  24.3%
  2020-03-09..2020-03-09 ( 1d, prior D, exit D): VIX  54.5 (pct 1.00) VXN  53.7 | QQEW pct 0.09 RSP pct 0.00 | 10y-2y  0.16 | spread 11.08% chg20  2.74 flatX  35 | dd252 -18.3% ret20 -15.5% rvol30   40 A120 101 | in-E  -6.9% then +20d   1.5% +60d  22.3%
  2011-12-14..2011-12-30 (12d, prior D, exit D): VIX  26.0 (pct 0.64) VXN  26.1 | QQEW pct 0.43 RSP pct 0.26 | 10y-2y  1.67 | spread  0.61% chg20  1.24 flatX  14 | dd252  -7.9% ret20  -5.6% rvol30   26 A120  24 | in-E   0.1% then +20d   8.4% +60d  21.7%
  2026-03-20..2026-04-07 (12d, prior D, exit D): VIX  26.8 (pct 0.93) VXN  29.2 | QQEW pct 0.30 RSP pct 0.88 | 10y-2y  0.51 | spread  3.11% chg20 -2.36 flatX  17 | dd252  -8.4% ret20  -4.4% rvol30   17 A120  75 | in-E  -0.7% then +20d  15.8% +60d  21.1%
  2016-05-09..2016-05-23 (11d, prior F, exit D): VIX  14.6 (pct 0.33) VXN  17.4 | QQEW pct 0.96 RSP pct 0.96 | 10y-2y  1.05 | spread  0.04% chg20  2.87 flatX  25 | dd252  -8.1% ret20  -2.5% rvol30   13 A120  24 | in-E   0.7% then +20d   1.1% +60d  10.3%
  2016-06-17..2016-06-22 ( 4d, prior A, exit D): VIX  19.4 (pct 0.69) VXN  20.2 | QQEW pct 0.94 RSP pct 0.77 | 10y-2y  0.92 | spread  0.61% chg20  0.19 flatX   8 | dd252  -7.5% ret20   1.1% rvol30   12 A120  18 | in-E  -0.7% then +20d   5.5% +60d   9.4%
  2019-06-03..2019-06-04 ( 2d, prior D, exit D): VIX  18.9 (pct 0.74) VXN  24.2 | QQEW pct 0.55 RSP pct 0.42 | 10y-2y  0.25 | spread  5.43% chg20  1.66 flatX  40 | dd252 -10.9% ret20 -10.9% rvol30   18 A120  28 | in-E   0.6% then +20d   8.6% +60d   5.8%
```

The two 2020 episodes are the visible outliers: VIX 54, breadth percentile
0.00, spread 10.6–11.1% (the widest of the 32), 20-session return −16%. They
look like nothing else in the set and are exactly the case where the wide
spread mechanically bought time. The other big reversals (2003-02, 2011-12,
2026-03, 2016-05/06) happened with VIX 15–30, breadth anywhere from 0.30 to
0.96 and spreads from 0.02% to 3.11%: no common signature.

## 6. The mechanical spread point

F is *defined* by SMA50 < SMA200, so the spread at E entry and its closing
rate are near-tautological predictors: a narrow, shrinking spread needs fewer
down sessions to cross. What the data say:

| group | spread% at entry mean / median (min–max) | 20-session spread change mean / median | flat-price sessions to cross (median, min–max) | episode length median |
|---|---|---|---|---|
| BREAK | 2.65 / 2.79 (0.07–7.06) | −0.62 / −1.08 | 26 (3–137) | 16 |
| REVERSAL | 4.07 / 3.04 (0.02–11.08) | −0.06 / −0.24 | 25 (8–102) | 6 |

- `spread@entry` AUC for BREAK 0.406 (p_MW 0.366); flat-cross sessions AUC
  0.486 (p 0.895). Median split (2.99%): 8/16 BREAK on each side.
  Thresholds: spread ≤ 2% → 7/11 BREAK, > 2% → 9/21; ≤ 4% → 13/22, > 4% →
  3/10; ≤ 5% → 13/23, > 5% → 3/9.
- So the spread explains the tails, not the middle: of the 9 entries with
  spread > 5%, 6 reversed (2010-06-07 6.79%, 2018-10-11 6.31%, 2018-10-24
  5.26%, 2019-06-03 5.43%, 2020-03-09 11.08%, 2020-03-11 10.59%) and 3 broke
  anyway (2008-01 5.22%, 2022-01 7.06%, 2025-03 5.34%) because the decline
  ran 18–27 sessions.
- The "sessions to close at the approach rate" column (spread ÷ 20-session
  closing rate) is uninformative: it ranges from 5 to 1012 sessions across
  the BREAKs and is undefined for 3 of them whose spread was still widening
  at entry (2003-01, 2008-06, 2016-01). The BREAKs were not, in general,
  entered with the spread already collapsing; the collapse happened inside E.
- The flat-price sessions-to-cross for BREAKs (median 26) is longer than the
  actual E length (median 16): BREAKs did not merely wait for the cross, they
  kept falling. That is the same fact as section 2b.
- The top non-spread features are not proxies for the spread
  (`below200_pct@avg3` corr −0.11, `QQEW_pct@approach10` −0.11,
  `since_last_F` +0.52, `rvol30@approach10` +0.70).

## 7. What this does and does not imply

- **No rule is proposed.** This was descriptive; nothing here was tested as
  an action row, and nothing here should be written into a trigger prompt or
  STRATEGY.md as guidance.
- **At E entry, the two futures look the same.** On 41 pre-entry columns
  spanning implied vol, rates, two breadth measures, price structure,
  realised vol, regime history and QQQ/SPY relative strength, the best
  |AUC−0.5| (0.211) is below the permutation null median (0.234), p 0.701,
  and every pre-entry LOO AUC is 0.51–0.55. This is consistent with the two
  prior E studies: E is a state where the information is not yet in.
- **What differs is the path inside E**, which is the outcome beginning to
  unfold: BREAKs keep falling through session 3 (median −1.0% vs +0.6%),
  end up ~5% lower, and last ~16 sessions rather than ~6. Whether "still
  falling on E session 3" carries any *tradable* information is a different
  question that this study did not ask and cannot answer; the repo's E row
  is already held at ~0.57x by the 20% vol target and e_pair_test found the
  entire constant-E ladder spans 0.013 Sharpe, which caps what any E-row
  change can do.
- **Post-exit returns are not a reason to fear the break.** QQQ's 60
  sessions after the first F day averaged +3.5% (13/16 positive); the three
  negative ones were the long F episodes (2000, 2008, 2022) that the
  classifier is there to catch anyway.
- **n = 32 (16/16; real era 13, 5/8) is the binding constraint.** A single
  pre-specified feature needs AUC ≈ 0.70 to reach 5%, and 81% of label
  shuffles produce a ≥ 0.70 AUC somewhere among 57 columns. Anything that
  looked interesting here — the QQEW breadth *approach* on 22 episodes, the
  entry depth below the 200d — would need the full pre-registered battery
  (proxy full / search / holdout, real daily, exposure-matched controls,
  whole-grid permutation) on both eras before it is even a candidate, and at
  this n the battery is not powered to pass it.

---

# Part II — inside the episodes: survivors at E sessions 3, 5 and 10 (owner follow-up, same day)

Same script (`part2()` in `paper-track/e_outcome_explore.py`), same log
(appended). Same rules: descriptive, no rule proposed, nothing applied. At
each checkpoint k the sample is the episodes still in E at session k; every
feature is measured at session k as (a) its level and (b) its change since
the E entry session, plus the explicit price path (QQQ return entry→k, up
sessions in the first k). Labels are permuted among the survivors only.

## II.1 Survivorship and the conditional base rate

| k | still in E: BREAK / REVERSAL | already ended: BREAK / REVERSAL | P(BREAK \| in E at k) | real era survivors (BREAK) | MDE \|AUC−0.5\| |
|---|---|---|---|---|---|
| 3 | 15 / 12 (27) | 1 / 4 | **0.56** | 9 (4) → 0.44 | 0.22 |
| 5 | 15 / 9 (24) | 1 / 7 | **0.62** | 8 (4) → 0.50 | 0.24 |
| 10 | 11 / 6 (17) | 5 / 10 | **0.65** | 8 (4) → 0.50 | 0.30 |

Conditioning on survival changes the base rate mechanically: REVERSALs are
short (median 6.5 sessions vs 16.5), so by session 10 ten of the sixteen
REVERSALs are already gone and the unconditional 0.50 has become 0.65. Any
"signal" at k has to be read against that conditional rate, and the MDE
column says what one pre-specified feature could even detect at 5%: an AUC
of about 0.72 at k=3, 0.74 at k=5, 0.80 at k=10.

## II.2 Feature tables at each checkpoint

36 columns per k (18 base quantities as level @k and, where sensible, change
@chg0-k, plus the path columns). Bonferroni threshold p < 0.00139 at every k;
**no column clears it at any k.** Top rows by |AUC−0.5| (full tables in the
log):

**k = 3 (15 B / 12 R).** p_MW < 0.05: 3/36; |AUC−0.5| > 0.20: 4.

| feature | nB/nR | BREAK mean / median | REVERSAL mean / median | p_MW | AUC |
|---|---|---|---|---|---|
| `below200_pct@k3` | 15/12 | −3.99 / −3.38 | −1.42 / −1.90 | 0.005 | 0.183 |
| `QQQ_ret_entry_to_k3` | 15/12 | −1.45 / −0.82 | +0.43 / +0.63 | 0.017 | 0.228 |
| `up_sessions_first_3` | 15/12 | 0.73 / 1 | 1.33 / 1 | 0.023 | 0.267 |
| `dd_from_252hi@k3` | 15/11 | −14.2 / −12.5 | −12.2 / −8.6 | 0.058 | 0.279 |
| `below50_pct@k3` | 15/12 | −6.27 / −6.33 | −4.23 / −3.19 | 0.079 | 0.300 |
| `VXN@chg0-3` | 14/11 | +1.81 / +0.25 | −0.84 / −0.46 | 0.106 | 0.692 |
| `VIX@chg0-3` | 15/12 | +1.66 / +0.25 | −0.48 / −0.79 | 0.097 | 0.689 |

Everything else (VIX/VXN *levels*, VIX percentile, all rates levels and
changes, QQEW and RSP breadth levels and changes, realised vol, vol ratio,
spread and its change, QQQ/SPY relative) is at AUC 0.41–0.59 with p > 0.12.
The only non-price columns that lean are the VIX and VXN *changes since
entry* (implied vol rising over the first three E sessions in the eventual
BREAKs, median +0.25 vs −0.5 to −0.8 points) at p 0.10.

**k = 5 (15 B / 9 R).** p_MW < 0.05: 3/36; |AUC−0.5| > 0.20: 5.

| feature | nB/nR | BREAK mean / median | REVERSAL mean / median | p_MW | AUC |
|---|---|---|---|---|---|
| `below200_pct@k5` | 15/9 | −4.31 / −3.88 | −2.28 / −1.88 | 0.022 | 0.215 |
| `RSP_pct@chg0-5` | 12/6 | −0.007 / −0.012 | +0.108 / +0.083 | 0.075 | 0.236 |
| `below50_pct@k5` | 15/9 | −6.30 / −6.00 | −4.83 / −2.80 | 0.040 | 0.244 |
| `QQQ_ret_pre_entry_to_k5` | 15/9 | −3.96 / −3.80 | −2.06 / −1.13 | 0.053 | 0.259 |
| `up_sessions_first_5` | 15/9 | 1.53 / 2 | 2.11 / 2 | 0.032 | 0.270 |
| `QQQ_ret_entry_to_k5` | 15/9 | −1.77 / −1.85 | −0.19 / +0.23 | 0.114 | 0.304 |
| `DGS3MO@chg0-5` | 15/9 | −0.002 / +0.01 | −0.034 / −0.01 | 0.151 | 0.678 |

The VIX/VXN-change lean from k=3 is gone by k=5 (`VIX@chg0-5` AUC 0.519,
p 0.88; `VXN@chg0-5` 0.491). The RSP/SPY breadth change (equal-weight S&P
improving relative to SPY in the REVERSALs) is on 12 vs 6 episodes.

**k = 10 (11 B / 6 R).** p_MW < 0.05: 1/36; |AUC−0.5| > 0.20: 3.

| feature | nB/nR | BREAK mean / median | REVERSAL mean / median | p_MW | AUC |
|---|---|---|---|---|---|
| `dd_from_252hi@k10` | 11/6 | −13.4 / −10.3 | −10.5 / −8.4 | 0.044 | 0.197 |
| `QQEW_x60@chg0-10` | 8/5 | +0.017 / +0.016 | +0.001 / −0.017 | 0.188 | 0.725 |
| `VXN_minus_VIX@chg0-10` | 11/6 | +0.72 / +0.32 | −0.48 / −0.77 | 0.159 | 0.712 |
| `QQQ_ret_pre_entry_to_k10` | 11/6 | −3.12 / −3.39 | −2.00 / −0.83 | 0.191 | 0.303 |
| `below200_pct@k10` | 11/6 | −3.38 / −3.08 | −2.25 / −1.09 | 0.482 | 0.394 |

By session 10 even the depth below the 200d has stopped separating (AUC
0.394, p 0.48), and `QQQ_ret_entry_to_k10` is AUC 0.439 (p 0.69): the
survivors that will reverse have fallen about as much as the ones that will
break. VIX level at k=10 is AUC 0.500, p 1.000.

## II.3 Permutation and LOO at each checkpoint

2000 shuffles of the survivor labels, max |AUC−0.5| over the columns.

| k | set | real max | feature | null median | null 95th | perm p |
|---|---|---|---|---|---|---|
| 3 | all 36 | 0.317 | `below200_pct@k3` | 0.261 | 0.372 | **0.182** |
| 3 | 28 non-price (implied vol, rates, breadth, realised vol, relative) | 0.192 | `VXN@chg0-3` | 0.256 | 0.363 | **0.909** |
| 5 | all 36 | 0.285 | `below200_pct@k5` | 0.282 | 0.396 | **0.493** |
| 5 | 28 non-price | 0.264 | `RSP_pct@chg0-5` | 0.278 | 0.393 | **0.590** |
| 10 | all 36 | 0.303 | `dd_from_252hi@k10` | 0.333 | 0.444 | **0.693** |
| 10 | 28 non-price | 0.225 | `QQEW_x60@chg0-10` | 0.326 | 0.439 | **0.961** |

Nothing clears permutation at any k, not even the price path once the
sample is restricted to survivors (the part-I result for `below200_pct@avg3`
owed part of its strength to the 5 short episodes, 4 of them REVERSALs).
Among non-price columns the real max sits *below* the null median at every k.

LOO logistic (ridge 0.5):

| k | model | in-sample AUC | LOO AUC |
|---|---|---|---|
| 3 | `below200_pct@k3` | 0.817 | 0.756 |
| 3 | + `DGS10@chg0-3` (corr 0.14) | 0.839 | 0.761 |
| 3 | best non-price `VIX@chg0-3` | 0.689 | 0.500 |
| 5 | `below200_pct@k5` | 0.785 | 0.696 |
| 5 | + `up_sessions_first_5` (corr 0.44) | 0.800 | 0.704 |
| 5 | best non-price `DGS3MO@chg0-5` | 0.678 | 0.407 |
| 10 | `dd_from_252hi@k10` | 0.803 | **0.152** |
| 10 | + `VXN_minus_VIX@chg0-10` (corr −0.12) | 0.712 | 0.485 |
| 10 | best non-price `VXN_minus_VIX@chg0-10` | 0.712 | 0.621 |

The depth-below-200d feature holds up out of fold at k=3 and k=5 (0.76,
0.70) and collapses at k=10 (0.15, the pooled-LOO pathology on 17 episodes).
Every non-price feature is at or below coin-flip out of fold except
`VXN_minus_VIX@chg0-10` at 0.62 on 11/6 — which is inside its own MDE of 0.30.

## II.4 The economically relevant quantity: forward QQQ return from session k

| k | group | n | to episode exit: mean / median (positive) | next 20 sessions regardless of exit: mean / median (positive) |
|---|---|---|---|---|
| 3 | BREAK | 15 | −0.87% / −1.84% (6/15) | −2.94% / −2.69% (4/15) |
| 3 | REVERSAL | 12 | +1.06% / +0.41% (7/12) | +5.28% / +4.76% (11/12) |
| 3 | ALL | 27 | −0.01% / 0.00% (13/27) | +0.71% / +2.66% (15/27) |
| 5 | BREAK | 15 | −0.56% / −1.59% (6/15) | −1.60% / −2.57% (4/15) |
| 5 | REVERSAL | 9 | +1.77% / +0.79% (5/9) | +8.41% / +7.70% (9/9) |
| 5 | ALL | 24 | +0.31% / −0.18% (11/24) | +2.15% / +2.04% (13/24) |
| 10 | BREAK | 11 | −1.52% / −0.49% (3/11) | −2.18% / −3.07% (5/11) |
| 10 | REVERSAL | 6 | +1.83% / +0.52% (4/6) | +7.03% / +6.70% (5/6) |
| 10 | ALL | 17 | −0.34% / −0.13% (7/17) | +1.07% / +0.65% (10/17) |

The *label* is worth a lot in hindsight (next-20 spread of 8–10 pp between
groups at every k). The question is whether the best feature at k predicts
that forward return, not just the label:

| k | feature | Spearman with return to exit (p) | Spearman with next-20 return (p) |
|---|---|---|---|
| 3 | `below200_pct@k3` | −0.330 (0.093) | **+0.021 (0.918)** |
| 3 | `VIX@chg0-3` | +0.055 (0.784) | −0.102 (0.613) |
| 3 | `QQQ_ret_entry_to_k3` | −0.268 (0.176) | +0.081 (0.689) |
| 5 | `below200_pct@k5` | −0.324 (0.122) | **+0.049 (0.821)** |
| 5 | `DGS3MO@chg0-5` | −0.165 (0.442) | −0.136 (0.526) |
| 5 | `QQQ_ret_entry_to_k5` | −0.250 (0.238) | −0.002 (0.994) |
| 10 | `dd_from_252hi@k10` | −0.164 (0.529) | +0.162 (0.535) |
| 10 | `VXN_minus_VIX@chg0-10` | −0.498 (0.042) | −0.294 (0.252) |
| 10 | `QQQ_ret_entry_to_k10` | −0.424 (0.090) | −0.174 (0.504) |

Reading: the depth-below-200d features correlate *negatively* with the
return to exit (deeper → the episode ends lower, i.e. in F) but have **zero**
correlation with the next 20 sessions' return (rho +0.02, +0.05). They
predict the label because the label is partly determined by how far price
has already fallen; they do not predict what QQQ does next. The one
nominally significant forward correlation, `VXN_minus_VIX@chg0-10` with the
return to exit (rho −0.50, p 0.042, n=17), is one of ~40 correlations
reported here and does not carry to the next-20 return (p 0.25).

## II.5 Compact table across k

```
   k  nB  nR  P(B)  best feature                     AUC   p_MW perm p   LOO rho_exit     p  rho_20     p  | best non-price                AUC perm p   LOO
   3  15  12  0.56  below200_pct@k3                0.183  0.005  0.182 0.756   -0.330 0.093  +0.021 0.918  | VXN@chg0-3                  0.692  0.909 0.500
   5  15   9  0.62  below200_pct@k5                0.215  0.022  0.493 0.696   -0.324 0.122  +0.049 0.821  | RSP_pct@chg0-5              0.236  0.590 0.407
  10  11   6  0.65  dd_from_252hi@k10              0.197  0.044  0.693 0.152   -0.164 0.529  +0.162 0.535  | QQEW_x60@chg0-10            0.725  0.961 0.621
```

## II.6 Paths, for eyeballing

QQQ return from the entry close, VIX change (points), QQEW breadth-percentile
change (B) and RSP breadth-percentile change (R) since entry, at sessions
3 / 5 / 10.

```
  episode                  n label              session 3           |          session 5           |          session 10
  BREAK episodes:
  2000-09-11..2000-09-21   9 BREAK      +1.1% V -0.1 B   -- R   -- |  -1.6% V  0.1 B   -- R   -- |                        ended
  2003-01-24..2003-02-11  13 BREAK      -0.2% V  0.4 B   -- R   -- |  -1.1% V -0.2 B   -- R   -- |  -2.5% V  1.8 B   -- R   --
  2004-07-13..2004-07-20   6 BREAK      -1.4% V  0.2 B   -- R   -- |  -2.7% V  0.7 B   -- R   -- |                        ended
  2005-03-22..2005-04-25  24 BREAK      +0.4% V -0.8 B   -- R 0.41 |  -0.2% V  0.2 B   -- R 0.04 |  +1.2% V -0.6 B   -- R 0.60
  2006-05-12..2006-06-13  22 BREAK      -0.8% V -0.8 B   -- R-0.04 |  -2.8% V  2.8 B   -- R 0.02 |  -2.1% V  1.3 B   -- R-0.10
  2008-01-07..2008-01-31  18 BREAK      -0.5% V  0.3 B-0.06 R-0.07 |  -2.3% V -0.1 B-0.05 R-0.04 |  -5.9% V  3.4 B 0.14 R 0.08
  2008-06-25..2008-07-07   8 BREAK      -4.0% V  2.3 B-0.04 R 0.00 |  -3.7% V  2.5 B-0.06 R-0.13 |                        ended
  2010-06-29..2010-07-20  15 BREAK      -1.8% V -1.3 B 0.31 R 0.02 |  -1.8% V -4.5 B 0.15 R-0.01 |  +4.5% V -9.6 B 0.35 R 0.05
  2011-08-04..2011-08-16   9 BREAK      -6.6% V 16.3 B 0.00 R 0.00 |  -6.1% V 11.3 B 0.00 R 0.01 |                        ended
  2012-11-07..2012-12-12  25 BREAK      -1.2% V -0.5 B 0.00 R 0.01 |  -1.9% V -2.4 B-0.01 R-0.03 |  -0.6% V -4.0 B-0.01 R-0.02
  2015-08-21..2015-09-29  27 BREAK      -4.2% V  8.0 B-0.06 R-0.07 |  +3.2% V -1.9 B-0.25 R-0.14 |  +1.0% V -2.4 B-0.13 R-0.02
  2016-01-07..2016-02-03  19 BREAK      -0.5% V -0.7 B-0.16 R-0.06 |  -2.8% V  0.2 B-0.10 R-0.03 |  -3.8% V  1.7 B 0.15 R 0.20
  2016-06-24..2016-06-27   2 BREAK                            ended |                        ended |                        ended
  2018-11-12..2018-11-30  14 BREAK      -0.7% V  0.8 B-0.00 R-0.03 |  +0.7% V -2.3 B 0.00 R 0.04 |  -2.1% V -1.6 B 0.00 R 0.49
  2022-01-20..2022-02-28  27 BREAK      -2.3% V  4.3 B 0.49 R 0.21 |  -4.7% V  6.4 B 0.36 R 0.21 |  +1.9% V -3.5 B 0.33 R 0.07
  2025-03-10..2025-04-11  25 BREAK      +0.9% V -3.6 B 0.00 R-0.02 |  +1.5% V -6.1 B 0.01 R-0.01 |  +1.7% V -8.6 B-0.00 R 0.02
  REVERSAL episodes that survived to session 10:
  2004-05-10..2004-05-24  11 REVERSAL   +1.7% V -1.6 B   -- R   -- |  +0.2% V -1.3 B   -- R   -- |  +1.0% V -1.3 B   -- R   --
  2011-12-14..2011-12-30  12 REVERSAL   -0.1% V -1.8 B 0.21 R 0.11 |  +1.9% V -2.8 B 0.15 R 0.10 |  +1.3% V -2.5 B 0.23 R 0.59
  2016-05-09..2016-05-23  11 REVERSAL   +0.5% V  0.1 B-0.16 R-0.06 |  -0.4% V  0.5 B-0.21 R-0.11 |  +0.6% V  0.6 B-0.24 R-0.12
  2018-10-24..2018-11-06  10 REVERSAL   +0.8% V -1.1 B 0.23 R 0.04 |  +0.4% V -1.9 B 0.85 R 0.35 |  +3.0% V -5.3 B 0.96 R 0.79
  2020-03-11..2020-04-09  22 REVERSAL   -1.5% V  3.9 B 0.00 R 0.00 |  -6.7% V 22.0 B 0.00 R 0.00 |  -5.9% V  7.8 B 0.02 R 0.01
  2026-03-20..2026-04-07  12 REVERSAL   +0.3% V  0.2 B-0.10 R 0.03 |  -1.4% V  0.7 B-0.00 R 0.06 |  +0.5% V -2.9 B-0.28 R-0.05
```

Eyeball: at session 10 five of the eleven surviving BREAKs are *up* from the
entry close (2005, 2010, 2015, 2022, 2025, by +1.0 to +4.5%) with VIX down
0.6–9.6 points — indistinguishable from the surviving REVERSALs (2004, 2011-12,
2016-05, 2018-10, 2026-03, up +0.5 to +3.0%, VIX −5.3 to +0.6). The BREAKs that
were clearly down at session 10 (2008-01 −5.9%, 2016-01 −3.8%, 2003 −2.5%)
sit next to the 2020-03 REVERSAL at −5.9% with VIX +7.8. Breadth changes
run both ways in both groups (2010 and 2022 BREAKs with QQEW pct +0.33/+0.35;
2016-05 and 2026-03 REVERSALs with −0.24/−0.28). There is no visible common
shape.

## II.7 What this does and does not imply

- **No rule is proposed**, and nothing here is a candidate. This is a
  description of 27, 24 and 17 episodes.
- **The two paths do not diverge in anything other than price itself, and
  price stops diverging by session 10.** At sessions 3 and 5 the eventual
  BREAKs are 2 pp deeper below the 200d and had fewer up sessions; that is
  the outcome accumulating (Spearman with the return to exit −0.33/−0.32),
  and it has zero correlation with the next 20 sessions' QQQ return
  (+0.02/+0.05). At session 10 the surviving REVERSALs have fallen as far as
  the surviving BREAKs (AUC 0.39–0.44 for depth and path, p > 0.48).
- **Implied vol, rates, breadth, realised vol and QQQ/SPY relative strength
  show nothing at any checkpoint.** Non-price permutation p = 0.91 / 0.59 /
  0.96; every non-price LOO AUC is 0.41–0.62 against MDEs of 0.22–0.30. The
  early lean in VIX/VXN change (k=3, p 0.10) is gone by k=5.
- **The base rate does the work.** P(BREAK | still in E) rises from 0.50 to
  0.56, 0.62 and 0.65 purely because REVERSALs are short. Any future look at
  "E has lasted k sessions" has to start from that conditional rate, and
  from the fact that the forward 20-session QQQ return for *all* survivors
  is still positive on average at every k (+0.7%, +2.2%, +1.1%).
- **Power.** With 15/12, 15/9 and 11/6 survivors the minimum detectable
  |AUC−0.5| for a single pre-specified feature is 0.22, 0.24 and 0.30, and
  the null max over 36 columns has a 95th percentile of 0.37, 0.40 and 0.44.
  Nothing short of a near-deterministic separation could have shown up here,
  and nothing did. Anything anyone still wanted to test from this would need
  the full pre-registered battery (proxy full / search / holdout, real daily,
  exposure-matched controls, whole-grid permutation) on both eras, and at
  these n the battery is not powered to pass it.
