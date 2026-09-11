# Research line `dgate_anatomy` (2026-09-11): what the D-row breadth gate is made of

Research only. Nothing here is applied; the discipline in BRIEFING.md (ADDENDUM 2026-09-10) binds.
Script: `paper-track/dgate_anatomy.py` (run from the repo root, ~60 s; `DGATE_ANAT_FAST=1` cuts the bootstrap/permutation draws to 200).
Full log: `paper-track/research_notes/dgate_anatomy_run.log`. No new data files; no existing file edited.

Rule under study (from `breadth_signal`, extended in `breadth_dgate_2000`; post hoc, 1 of 224 candidates): **effective state D AND the
60-day change of log(QQEW/QQQ) in its trailing-252 bottom quintile (pct < 0.20) -> the D row (100 % QLD) goes to cash.** This line does
not sweep it again. It asks what the rule is made of, where its gain sits, whether the mechanism is coherent, and what a forward test
must look like.

## 0. Summary

- **What it is.** On the 4,800 QQEW rows (2007-07-27..2026-08-26) the gate is on for 124 days in 40 runs inside 23 of the 71 D episodes.
  Its whole gain (+84.5 pp of the +83.1 pp gate-minus-live log difference) comes from the **22 runs whose D episode ended in a breakdown
  to E** (+96.6 pp); the 18 runs whose episode went back to A cost −12.1 pp. In 6 of the 8 largest runs the run ends **one session before
  the E transition** (7 of 8 within two): the gate is worth the single day on which QQQ breaks its 200d. Eight runs carry 68.1 of 84.5 pp (81 %); 14 of 40 runs
  lose money. 2008 / 2020 / 2022 are 10 / 19 / 12 % of the gain (42 % together); 2010 and 2018 are 19 % each; the SPMO era is 62 %.
- **Mechanism (section 2).** On all 727 D days, bottom-quintile breadth is a **breakdown predictor specific to D**: P(next state = E/F)
  0.54 vs 0.05–0.30 in the other buckets, forward-20d QQQ −1.9 % vs +2.0..+4.9 %, forward 20-session vol 29.7 % vs 15.6–18.2 %.
  On A days the same bucket shows nothing actionable (next-day +6 bp, forward-20d +0.6 % vs +1.4–1.5 %); on all days it is a mild general
  negative (forward-20d +0.8 % vs +1.6–1.8 %). Episode-level permutation of the exit outcomes: P = 0.007 (day-weighted) / 0.003 (episode
  level); circular-shift null for the forward returns: P < 0.001. It is **not** distance-to-the-200d in disguise: breadth separates the
  QLD leg within both halves of D by gap200 (−63 vs +45 bp near the 200d, −83 vs +30 bp far from it; t −2.1 / −2.2) and gap200 placebo
  gates fail the holdout (−0.25 at 3 % and 5 %). The top breadth quintile in D also carries an elevated P(E/F) = 0.30 (a U-shape) that the
  rule does not use.
- **Why D and not A (section 3).** Not exposure: the live design's QQQ-beta on bottom-quintile days is 1.59 in A and 1.64 in D. The
  asymmetry is 99 % the return difference (next-day QQQ −35 bp in D vs +6 bp in A). The A gate with D's beta would still lose −88 pp;
  the D gate with A's beta would still gain +69 pp. Narrow leadership while the index is above its 50d is the ordinary state of a
  mega-cap-led bull (28 % of A days are bottom-quintile); the same divergence once the index is already below its 50d is what precedes
  the break of the 200d.
- **Robustness not previously run (section 4).** (a) One session of execution lag keeps most of it (+0.170/+0.148 vs constant-D);
  two sessions keep the search era and lose the holdout (+0.148/+0.041) because the holdout runs are 1–3 days long. (b) At 20 bp one-way
  cost the gate is still +0.175/+0.152 vs constant-D; its extra turnover costs 0.16 pp/yr at 4 bp. (c) Episode-block bootstrap (71 D
  episodes resampled whole, 2,000 draws) vs constant-D: Sharpe CI [+0.080, +0.321], log-return CI [+2.3, +7.8] pp/yr, P(≤0) < 0.001 —
  no wider than the day-block CI. (d) 33 rolling 3-year windows: 2 negative (2012–2015, 2 gated days), 31 positive (+0.05..+0.52).
  (e) The smooth mapping clip((pct−0.2)/0.3, 0, 1) keeps the whole edge (S 1.337 / H 1.073; +0.187/+0.181 vs constant-D; real 1.485);
  every smooth version is positive in both eras and the edge fades monotonically as the ramp flattens — no hard-threshold red flag.
  (f) Four alternate definitions of the same idea (20d+60d average, 120d, ratio vs 200d SMA, cap-minus-equal-weight z-score) all show
  the same sign in both eras vs constant-D and select gated D days with −39..−71 bp next-day QLD vs +26..+36 bp; only the 20d window
  (known) fails.
- **The honest holdout (section 5).** 2007-07..2015-10 has 28 D episodes, 10 with a gated day, 18 runs; 11 positive runs in 7 episodes;
  the top 3 runs (2015-08-20, 2008-01-02, 2011-08-02) carry +25.5 of +32.0 pp, the 4th (2010-06-28) +6.1. **The holdout gain rests on
  four single breakdown days in four D episodes**, offset by one 31-day false alarm (2007-11, −6.5 pp). Strict split, nothing fitted:
  holdout gate vs constant-D +0.178 Sharpe, episode-bootstrap CI [+0.026, +0.362] (P 0.009), log-return CI [+0.81, +8.63] pp/yr; vs live
  the log-return CI touches zero ([−0.60, +8.79], P 0.050). Search era vs constant-D +0.205, CI [+0.037, +0.393].
- **Verdict** (section 7): the mechanism is coherent and specific enough to move the rule from "pre-register" to **candidate**, with
  the explicit reservation that "candidate" means *a rule whose forward test is worth running with a mechanical decision* — not a rule
  to apply. The evidence is 22 D→E breakdowns, 5 of them in the holdout, and the rule's value is a one-day timing of the 200d break.
- Candidate count this line: 16 (5 smooth mappings, 4 alternate definitions, 4 lag variants, 3 gap200 placebo gates); cumulative 240.

## 1. Standing figures and the reference gate (reproduced through the harness)

```
STANDING FIGURES (must match briefing 22.18/0.913/-33.6, S 1.103 H 0.768; real 31.40/1.248/-25.0):
  26y proxy 22.18% / 0.913 / -33.6%  S 1.103 H 0.768  exp 67.7% | real weekly 31.40% / 1.248 / -25.0% | rows 6575 2000-07-03..2026-08-26, real rows 564
REFERENCE on the 4800 QQEW rows 2007-07-27..2026-08-26 (must match the earlier notes):
  live   26.09% / 1.006 / -33.6% S 1.103 H 0.876 exp 72.1%   (note: 26.09/1.006/-33.6 S 1.103 H 0.876)
  gated  31.71% / 1.218 / -28.5% S 1.332 H 1.065 exp 70.0%   (note: 31.71/1.218/-28.5 S 1.332 H 1.065)
  const-D q=0.850 25.32% / 1.024 / -31.2% S 1.127 H 0.886 exp 70.0%
```

## 2. Episode anatomy

```
40 gated runs, 124 days, inside 23 distinct D episodes (of 71 D episodes on these rows).  Sum of run contributions +84.5pp; total gate-live log difference over all rows +83.1pp (residual -1.4pp is path/rebalance effects outside the runs).  Live return summed over gated days -86.1pp; QLD-leg summed -98.1pp.

    # start      end          n   QQQ%   QLD%  live% contrib  cum% exit to-exit A<=60 EF<=60  parent D episode
    1 2022-01-05 2022-01-19  10   -6.1  -12.3  -10.4   +10.4    12    E       1     -      1  2022-01-05..2022-01-19 (10d)
    2 2015-08-20 2015-08-20   1   -4.5   -9.1   -9.2    +9.2    23    E       1    44      1  2015-08-20..2015-08-20 (1d)
    3 2020-02-25 2020-02-26   2   -4.6   -9.5   -9.1    +9.0    34    E       8    33      8  2020-02-25..2020-03-06 (9d)
    4 2008-01-02 2008-01-04   3   -4.6   -9.5   -8.7    +8.6    44    E       1     -      1  2008-01-02..2008-01-04 (3d)
    5 2018-10-19 2018-10-23   3   -4.5   -9.3   -8.6    +8.6    54    E       1     -      1  2018-10-12..2018-10-23 (8d)
    6 2018-10-08 2018-10-09   2   -4.2   -8.6   -8.6    +8.5    64    E       2     -      2  2018-10-05..2018-10-10 (4d)
    7 2011-08-02 2011-08-03   2   -3.8   -7.9   -7.8    +7.7    73    E       1    48      1  2011-08-02..2011-08-03 (2d)
    8 2010-06-28 2010-06-28   1   -3.9   -8.0   -6.2    +6.1    81    E       1    51      1  2010-06-11..2010-06-28 (12d)
    9 2024-08-02 2024-08-02   1   -3.0   -6.2   -5.4    +5.3    87    A      11    11      -  2024-07-24..2024-08-16 (18d)
   10 2020-02-28 2020-03-06   6   -6.1  -13.5   -5.3    +5.2    93    E       1    26      1  2020-02-25..2020-03-06 (9d)
   11 2026-03-11 2026-03-18   6   -2.4   -5.0   -5.0    +5.0    99    E       2    15      2  2026-02-04..2026-03-19 (31d)
   12 2024-07-31 2024-07-31   1   -2.5   -5.0   -4.7    +4.7   105    A      13    13      -  2024-07-24..2024-08-16 (18d)
   13 2020-03-10 2020-03-10   1   -4.5   -9.1   -4.2    +4.2   109    E       1    24      1  2020-03-10..2020-03-10 (1d)
   14 2010-05-14 2010-05-26   9   -2.3   -4.9   -3.9    +3.9   114    E       7     -      7  2010-05-06..2010-06-04 (21d)
   15 2026-02-11 2026-02-12   2   -1.8   -3.7   -3.7    +3.7   118    E      25    38     25  2026-02-04..2026-03-19 (31d)
   16 2010-06-22 2010-06-24   3   -2.1   -4.3   -3.2    +3.1   122    E       3    53      3  2010-06-11..2010-06-28 (12d)
   17 2015-07-06 2015-07-07   2   -1.5   -3.0   -3.0    +3.0   126    A       5     5     33  2015-06-29..2015-07-13 (10d)
   18 2011-03-14 2011-03-14   1   -1.4   -2.9   -2.9    +2.8   129    A      27    27      -  2011-03-10..2011-04-19 (29d)
   19 2024-07-24 2024-07-29   4   -1.3   -2.7   -2.8    +2.8   132    A      15    15      -  2024-07-24..2024-08-16 (18d)
   20 2018-10-12 2018-10-12   1   -1.2   -2.5   -2.6    +2.5   135    E       8     -      8  2018-10-12..2018-10-23 (8d)
   21 2010-06-01 2010-06-04   4   -2.0   -4.3   -2.4    +2.4   138    E       1     -      1  2010-05-06..2010-06-04 (21d)
   22 2019-05-28 2019-05-28   1   -0.8   -1.7   -1.7    +1.6   140    E       4    15      4  2019-05-13..2019-05-31 (14d)
   23 2021-09-24 2021-09-24   1   -0.8   -1.6   -1.6    +1.5   142    A      17    17      -  2021-09-20..2021-10-18 (21d)
   24 2019-05-15 2019-05-20   4   -0.7   -1.5   -1.5    +1.4   143    E       9    20      9  2019-05-13..2019-05-31 (14d)
   25 2010-06-17 2010-06-17   1   -0.1   -0.2   -0.1    +0.1   144    E       8    58      8  2010-06-11..2010-06-28 (12d)
   26 2010-06-11 2010-06-11   1   -0.0   -0.0   -0.1    +0.0   144    E      12     -     12  2010-06-11..2010-06-28 (12d)
   27 2015-07-01 2015-07-01   1   +0.0   +0.1   +0.1    -0.1   143    A       8     8     36  2015-06-29..2015-07-13 (10d)
   28 2026-04-08 2026-04-08   1   +0.7   +1.3   +1.1    -1.2   142    A       1     1      -  2026-04-08..2026-04-08 (1d)
   29 2011-03-10 2011-03-10   1   +0.6   +1.2   +1.2    -1.2   141    A      29    29      -  2011-03-10..2011-04-19 (29d)
   30 2015-07-13 2015-07-13   1   +0.7   +1.3   +1.3    -1.4   139    A       1     1     29  2015-06-29..2015-07-13 (10d)
   31 2014-05-16 2014-05-16   1   +0.7   +1.4   +1.4    -1.5   137    A       3     3      -  2014-03-26..2014-05-20 (39d)
   32 2014-05-20 2014-05-20   1   +1.0   +1.9   +1.9    -2.0   135    A       1     1      -  2014-03-26..2014-05-20 (39d)
   33 2020-04-13 2020-04-13   1   +4.3   +8.3   +2.1    -2.1   132    A       1     1      -  2020-04-13..2020-04-13 (1d)
   34 2019-05-13 2019-05-13   1   +1.1   +2.2   +2.1    -2.2   130    E      14    25     14  2019-05-13..2019-05-31 (14d)
   35 2007-08-03 2007-08-03   1   +1.2   +2.3   +2.2    -2.2   127    A       3     3      -  2007-08-03..2007-08-07 (3d)
   36 2026-02-20 2026-02-24   3   +1.3   +2.5   +2.5    -2.5   124    E      18    31     18  2026-02-04..2026-03-19 (31d)
   37 2024-08-13 2024-08-15   3   +2.7   +5.2   +3.9    -3.9   120    A       2     2      -  2024-07-24..2024-08-16 (18d)
   38 2018-05-02 2018-05-04   3   +2.7   +5.3   +3.9    -3.9   115    A       1     1      -  2018-04-20..2018-05-04 (11d)
   39 2021-12-20 2021-12-21   2   +3.4   +6.8   +6.1    -6.2   108    A       1     1     20  2021-12-20..2021-12-21 (2d)
   40 2007-11-09 2007-12-24  31   +4.9   +8.6   +6.8    -6.5   100    A       1     1      8  2007-11-09..2007-12-24 (31d)

  top 8 runs carry +68.1 of +84.5pp = 81%: 2022-01-05(10d +10.4), 2015-08-20(1d +9.2), 2020-02-25(2d +9.0), 2008-01-02(3d +8.6), 2018-10-19(3d +8.6), 2018-10-08(2d +8.5), 2011-08-02(2d +7.7), 2010-06-28(1d +6.1)
  runs with NEGATIVE contribution (the gate cost money): 14 of 40, summing -36.8pp; positive runs 26 summing +121.3pp
  exit state of the parent D episode, by run: {'A': 18, 'E': 22}; runs where eff reached E/F within 60 sessions of the run end: 27; reached A within 60: 32; neither within 60: 0
  contribution from runs whose parent D episode exited to E/F: +96.6pp; to A/B/C: -12.1pp

  BY YEAR (year of the run's start): runs, days, contribution pp, share of total, QLD-leg pp
    2007  runs  2  days  32  contrib   -8.7pp  share -10.3%  QLD-leg  +10.9pp
    2008  runs  1  days   3  contrib   +8.6pp  share  10.2%  QLD-leg   -9.5pp
    2010  runs  6  days  19  contrib  +15.6pp  share  18.5%  QLD-leg  -21.8pp
    2011  runs  3  days   4  contrib   +9.3pp  share  11.0%  QLD-leg   -9.5pp
    2014  runs  2  days   2  contrib   -3.4pp  share  -4.1%  QLD-leg   +3.3pp
    2015  runs  4  days   5  contrib  +10.6pp  share  12.5%  QLD-leg  -10.8pp
    2018  runs  4  days   9  contrib  +15.7pp  share  18.6%  QLD-leg  -15.1pp
    2019  runs  3  days   6  contrib   +0.9pp  share   1.0%  QLD-leg   -1.0pp
    2020  runs  4  days  10  contrib  +16.3pp  share  19.2%  QLD-leg  -23.8pp
    2021  runs  2  days   3  contrib   -4.7pp  share  -5.5%  QLD-leg   +5.2pp
    2022  runs  1  days  10  contrib  +10.4pp  share  12.3%  QLD-leg  -12.3pp
    2024  runs  4  days   9  contrib   +8.9pp  share  10.5%  QLD-leg   -8.6pp
    2026  runs  4  days  12  contrib   +5.1pp  share   6.0%  QLD-leg   -5.0pp
  share of the gain from 2008: 10.2%  (+8.6pp of +84.5)
  share of the gain from 2020: 19.2%  (+16.3pp of +84.5)
  share of the gain from 2022: 12.3%  (+10.4pp of +84.5)
  share from 2008+2020+2022 together: 41.7%; from the SPMO era 2015-11+: 62.1%; holdout 2007-07..2015-10: 37.9%
```

Reading. The earlier note's "8 of 40 carry 68 of 86 pp" is confirmed with the realized contribution: the eight are 2022-01-05 (10 d),
2015-08-20 (1 d), 2020-02-25 (2 d), 2008-01-02 (3 d), 2018-10-19 (3 d), 2018-10-08 (2 d), 2011-08-02 (2 d), 2010-06-28 (1 d) = +68.1 of
+84.5 pp; the −86.1 pp in the earlier note is the live return summed over gated days, the +84.5 is what the gate actually captured after
the vol target (which had already cut D exposure to 0.82 on those days). Three structural facts: (i) every run's parent D episode exited
to either A (18 runs) or E (22 runs) — never B, C or F — so the gate is a bet on the D→E transition; (ii) the runs in episodes that broke
down gained +96.6 pp, the runs in episodes that recovered lost −12.1 pp; (iii) seven of the eight largest runs end one or two sessions before the
E transition (to-exit = 1, 1, 8, 1, 1, 2, 1, 1): the money is the breakdown day itself, not a slow bleed. The false alarms are the long
runs (2007-11, 31 d, −6.5; 2024-08-13, 2018-05, 2021-12) where the gate stayed in cash through a recovery.

## 3. Transition mechanism

```
  [state D days]  n=727
  bucket      n  eps  P(E/F)  P(A/B) P(to D) P(down) to-chg  d1 bp   fwd5  fwd10  fwd20  med20  vol20
  0.0-0.2   124   23    0.54    0.46    0.00    0.54    9.4  -34.8  -1.32  -2.05  -1.91  -0.97   29.7
  0.2-0.4   162   35    0.27    0.73    0.00    0.27   11.2   11.1   0.74   1.12   2.25   3.62   18.2
  0.4-0.6   187   36    0.05    0.95    0.00    0.05    8.9   21.8   1.09   2.02   3.50   4.18   17.1
  0.6-0.8   132   26    0.05    0.95    0.00    0.05    9.8   27.6   1.69   2.97   4.92   5.60   15.6
  0.8-1.0   122   20    0.30    0.70    0.00    0.30    9.4   15.4   0.30   0.83   2.01   2.74   17.9

  [state A days]  n=3092
  bucket      n  eps  P(E/F)  P(A/B) P(to D) P(down) to-chg  d1 bp   fwd5  fwd10  fwd20  med20  vol20
  0.0-0.2   879   34    0.00    0.05    0.95    1.00   41.7    6.1   0.28   0.42   0.56   1.36   18.2
  0.2-0.4   674   47    0.00    0.06    0.93    1.00   39.9    4.6   0.21   0.47   0.58   1.29   16.0
  0.4-0.6   645   54    0.00    0.02    0.96    1.00   43.3    6.4   0.21   0.56   1.48   1.70   15.2
  0.6-0.8   459   44    0.02    0.03    0.91    1.00   38.7   15.3   0.48   0.76   1.54   1.84   16.4
  0.8-1.0   435   34    0.01    0.03    0.90    1.00   40.0    3.1   0.32   0.62   1.42   1.92   16.6

  [all days]  n=4800
  bucket      n  P(E/F)  P(A/B) P(down) to-chg  d1 bp   fwd5  fwd10  fwd20  med20  vol20
  0.0-0.2  1163    0.12    0.10    0.87   33.7    3.4   0.27   0.45   0.84   1.40   21.2
  0.2-0.4   951    0.09    0.19    0.81   31.2    5.2   0.31   0.53   0.78   1.41   17.7
  0.4-0.6   948    0.04    0.22    0.73   32.2    6.6   0.26   0.67   1.62   2.11   17.5
  0.6-0.8   730    0.08    0.22    0.69   28.0   16.2   0.63   1.00   1.75   2.59   19.4
  0.8-1.0  1008    0.16    0.22    0.57   22.8    4.8   0.24   0.69   1.71   2.34   21.9

  D days, bottom quintile vs the other four, by era:
  era      scope       n  eps  P(E/F)  P(A/B)  d1 bp  fwd20  vol20 QLD d1 bp
  full     pct<0.2   124   23    0.54    0.46  -34.8  -1.91   29.7     -70.5
  full     pct>=0.2  603   62    0.16    0.84   18.9   3.18   17.2      37.2
  holdout  pct<0.2    65   10    0.38    0.62  -25.0  -1.80   24.8     -50.8
  holdout  pct>=0.2  280   24    0.16    0.84   15.0   3.30   15.9      29.9
  search   pct<0.2    59   13    0.71    0.29  -45.7  -2.04   35.1     -92.2
  search   pct>=0.2  323   38    0.16    0.84   22.2   3.07   18.4      43.5
```

```
  PERMUTATION TESTS (the unit of independence is the D EPISODE, not the day):
  (a) day-weighted: P(E/F | D day, pct<0.2) - P(E/F | D day, pct>=0.2) = +0.381; null = exit outcomes permuted across the 71 D episodes (2000 perms): P(T_null >= T) = 0.007
  (b) episode level: P(E/F | episode had >=1 gated day, n=23) - P(E/F | never gated, n=48) = +0.376; same null: P = 0.003
  (c) forward 20d QQQ return, gated D days minus other D days = -5.09pp; null = the gate's on/off pattern circularly shifted within D days (2000 shifts): P(null <= actual) = 0.000
  (d) next-day QLD leg, gated minus other D days = -107.7bp; same null: P = 0.000
```

```
  2b. CONFOUND CHECK: within D, does the gate just pick the days when price is already close to the 200d (gap200 small),
      which would predict the E transition mechanically?  gap200/gap50 = close/SMA-1 (%); pos = sessions since the D episode began.
  scope                   n  gap200%  gap50%  vol30%   pos  P(E/F) QLD d1 bp
  gated                 124     4.44   -2.66    24.4   9.6    0.54     -70.5
  other D               603     5.85   -2.03    18.9   8.6    0.16      37.2
  2x2 split at the D-day median gap200 = 5.14%:
  gap200<med gated       79     2.74   -3.33    24.1   9.7    0.67     -63.4
  gap200<med other      284     3.10   -2.75    18.8   9.3    0.30      45.1
  gap200>=med gated      45     7.43   -1.47    25.0   9.5    0.31     -83.0
  gap200>=med other     319     8.30   -1.39    19.0   7.9    0.03      30.1
  placebo gates on the same D rows using the distance to the 200d instead of breadth (D row to cash when gap200 < g; each a candidate):
  rule                    on gated bp other bp           | CAGR/Sh/MDD      S      H  | vs live S/H | vs constD S/H
  gap200 < 2%             94    -29.4     26.0 28.46% / 1.104 / -29.5%  1.228  0.939  +0.125/+0.063   +0.104/+0.054
  gap200 < 3%            150     43.3     12.4 22.55% / 0.936 / -38.3%  1.153  0.639  +0.050/-0.238   +0.018/-0.251
  gap200 < 5%            345     25.7     12.6 21.00% / 0.922 / -37.0%  1.138  0.629  +0.035/-0.247   -0.023/-0.261
  breadth gate within the far half of D days by gap200: gated n=45 QLD d1 -83.0bp vs other n=319 +30.1bp, diff t -2.17
  breadth gate within the near half of D days by gap200: gated n=79 QLD d1 -63.4bp vs other n=284 +45.1bp, diff t -2.08
```

Reading. In D the bottom quintile is different in kind, not degree: 54 % of those days sit in an episode that ends below the 200d
(vs 5 % in the middle three buckets and 16 % for all other D days), the forward 20-day QQQ return is negative (−1.9 %, median −1.0 %)
against +2.0..+4.9 % elsewhere, and forward vol nearly doubles. In A the bottom quintile has a slightly lower forward return (+0.6 % vs
+1.4–1.5 %) but a positive next-day return and no transition signal (P(to D) is 0.90–0.96 in every bucket: leaving A is always a downgrade
and breadth does not time it). On all days the bottom two buckets are a mild general negative (+0.8 % vs +1.6–1.8 % over 20 d) that no
gate can monetise. So the answer to the question posed is: **a breakdown predictor specific to D**, with a weak general-negative component
underneath. Two qualifications. The top quintile in D also has P(E/F) = 0.30 and a below-average forward return — extreme readings in
either direction are bad in D, the rule only uses one tail. And the confound check shows the gated days are somewhat closer to the 200d
(4.4 % vs 5.9 %) and higher-vol (30d 24 % vs 19 %), but breadth separates the QLD leg inside both gap200 halves and the vol target already
acts on the vol; the distance-to-200d placebo gates do not reproduce the result (the 2 % gate is +0.104/+0.054 vs constant-D, the 3 % and
5 % gates fail the holdout by −0.25).

## 4. Why D and not A

```
  state bucket      n  risky  beta  d1 bp  fwd20  vol20 live d1 beta*d1
  A     0.0-0.2   879   0.79  1.59    6.1   0.56   18.2    12.9    13.4
  A     0.2-0.4   674   0.82  1.63    4.6   0.58   16.0    11.4    11.9
  A     0.4-0.6   645   0.85  1.69    6.4   1.48   15.2    10.6    11.2
  A     0.6-0.8   459   0.79  1.58   15.3   1.54   16.4    25.3    26.2
  A     0.8-1.0   435   0.66  1.33    3.1   1.42   16.6     1.5     2.2
  D     0.0-0.2   124   0.82  1.64  -34.8  -1.91   29.7   -64.1   -62.7
  D     0.2-0.4   162   0.95  1.90   11.1   2.25   18.2    20.3    21.5
  D     0.4-0.6   187   0.97  1.94   21.8   3.50   17.1    39.7    41.4
  D     0.6-0.8   132   0.93  1.86   27.6   4.92   15.6    51.2    52.2
  D     0.8-1.0   122   0.93  1.86   15.4   2.01   17.9    25.2    26.1

  BOTTOM-QUINTILE DAYS: A n=879 beta 1.59 next-day QQQ +6.1bp;  D n=124 beta 1.64 next-day QQQ -34.8bp
  per-day P&L at stake (beta x d1): D -57.1bp vs A +9.7bp, difference -66.7bp/day, of which
    return difference   (mean beta x dr): -66.0bp  (99%)
    exposure difference (mean r x dbeta): -0.7bp  (1%)

  COUNTERFACTUAL 'cash-instead' gains (sum of -beta x next-day QQQ over bottom-quintile days, pp, before costs/vol-target path):
    D gate as designed (own beta):            +77.8pp over 124 days
    D days but with A's mean beta 1.59:      +68.6pp   (return effect alone)
    A gate as designed (own beta):            -117.6pp over 879 days
    A days but with D's mean beta 1.64:      -87.7pp   (exposure effect alone)
  harness: A-only cash gate 19.07% / 0.845 / -28.1% S 0.855 H 0.833 exp 57.5% vs k-live k=0.797 S 1.122 H 0.876 -> -0.267/-0.044; gated A days 879
```

Reading. The live design's exposure on bottom-quintile days is the same in A and D (risky 0.79 vs 0.82, beta 1.59 vs 1.64: in A the
trim and vol target take 20 % off the raw 2.0 beta of 50/50 SPMO/TQQQ, in D the vol target takes 18 % off the raw 2.0 of 100 % QLD).
The D-vs-A asymmetry in P&L at stake (−63 vs +13 bp/day) is 99 % return difference and 1 % exposure difference. The A-only gate failed
in the earlier line not because the A row was already protected but because bottom-quintile A days are not negative: with D's beta the
A gate would still have lost −88 pp; with A's beta the D gate would still have gained +69 pp. (Harness check, same rows: A-only cash gate
S 0.855 / H 0.833 vs the k-live control 1.122 / 0.876.)

## 5. Robustness not previously run

```
(a) EXECUTION LAG.  The gate flag (state D AND pct<0.2) is computed at d0 and acted on at d0+k.  Two readings:
    'if still D': at d0+k the row goes to cash only if eff is still D (the state machine has not moved on);
    'unconditional': the cash instruction is executed at d0+k whatever the state then is.
  lag  variant                   CAGR/Sh/MDD      S      H    exp  | vs live S/H | vs const-D S/H | on
  0    if still D     31.71% / 1.218 / -28.5%  1.332  1.065  70.0%  +0.229/+0.189    +0.205/+0.178  124
  1    if still D     30.77% / 1.182 / -33.6%  1.294  1.034  70.3%  +0.191/+0.158    +0.170/+0.148  108
  1    unconditional  31.02% / 1.190 / -32.4%  1.301  1.043  70.1%  +0.198/+0.167    +0.175/+0.157  124
  2    if still D     29.17% / 1.121 / -33.6%  1.269  0.925  70.5%  +0.167/+0.049    +0.148/+0.041   97
  2    unconditional  28.61% / 1.106 / -33.8%  1.241  0.927  70.1%  +0.139/+0.051    +0.116/+0.041  124
```

```
(b) COST SENSITIVITY (one-way spread patched in the harness; q of the constant-D control kept at the base calibration):
  cost        gate CAGR/Sh/MDD      S      H | live Sh      S      H | constD Sh | gate-live S/H | gate-constD S/H | cost drag gate/live pp/yr
    4bp31.71% / 1.218 / -28.5%  1.332  1.065     1.006  1.103  0.876       1.024   +0.229/+0.189     +0.205/+0.178          1.48 / 1.32
   10bp28.82% / 1.130 / -30.0%  1.242  0.979     0.931  1.027  0.803       0.946   +0.216/+0.176     +0.194/+0.168          3.69 / 3.30
   20bp24.15% / 0.982 / -32.5%  1.093  0.835     0.806  0.900  0.680       0.817   +0.193/+0.154     +0.175/+0.152          7.38 / 6.61
```

```
(c) EPISODE-BLOCK BOOTSTRAP (2000 draws).  Unit = a whole D episode (all its days, paired across the two series); the
    non-D days are kept fixed, the D episodes are resampled with replacement (same count), then the Sharpe / log-return
    difference is recomputed.  This is the bootstrap that treats the ~40 episodes as the sample size, not the 4,800 days.
  gate vs const-D  point +4.97pp/yr, +0.194 Sharpe | episode boot (71 episodes): log-return CI [+2.33, +7.78] P(<=0)=0.000   Sharpe CI [+0.080, +0.321] P(<=0)=0.000
  gate vs live     point +4.36pp/yr, +0.212 Sharpe | episode boot (71 episodes): log-return CI [+1.34, +7.80] P(<=0)=0.001   Sharpe CI [+0.084, +0.358] P(<=0)=0.000
  (for comparison, circular day-block bootstrap vs const-D, block 20d: Sharpe CI [+0.073, +0.336] P(<=0)=0.000)
  (for comparison, circular day-block bootstrap vs const-D, block 60d: Sharpe CI [+0.068, +0.329] P(<=0)=0.001)
```

```
(d) ROLLING 3-YEAR WINDOWS (start every 6 months): Sharpe of gate / const-D / live in the window, deltas, gated days & runs
  window                      n   gate constD   live   g-cD g-live gated d runs D days
  2007-07-01..2010-07-01    738  0.900  0.639  0.632 +0.261 +0.268      54    9    119
  2008-01-01..2011-01-01    757  1.378  1.001  0.946 +0.377 +0.433      22    7     70
  2008-07-01..2011-07-01    756  1.364  1.095  1.064 +0.269 +0.300      21    8    113
  2009-01-01..2012-01-01    755  1.200  0.849  0.814 +0.351 +0.386      23    9    116
  2009-07-01..2012-07-01    756  1.197  0.875  0.836 +0.322 +0.361      23    9    157
  2010-01-01..2013-01-01    753  0.772  0.491  0.450 +0.281 +0.322      23    9    171
  2010-07-01..2013-07-01    753  0.848  0.729  0.715 +0.119 +0.134       4    3    123
  2011-01-01..2014-01-01    753  0.882  0.755  0.749 +0.127 +0.133       4    3    129
  2011-07-01..2014-07-01    753  0.991  0.937  0.920 +0.053 +0.071       4    3    129
  2012-01-01..2015-01-01    754  1.344  1.399  1.387 -0.055 -0.044       2    2    141
  2012-07-01..2015-07-01    753  1.189  1.215  1.234 -0.025 -0.044       2    2    127
  2013-01-01..2016-01-01    756  1.205  1.072  1.099 +0.133 +0.107       7    6    120
  2013-07-01..2016-07-01    757  0.840  0.750  0.739 +0.090 +0.101       7    6    115
  2014-01-01..2017-01-01    756  0.575  0.467  0.480 +0.108 +0.094       7    6    129
  2014-07-01..2017-07-01    757  0.794  0.650  0.643 +0.144 +0.151       5    4     83
  2015-01-01..2018-01-01    755  1.015  0.864  0.851 +0.151 +0.164       5    4     75
  2015-07-01..2018-07-01    756  0.992  0.887  0.889 +0.106 +0.103       8    5     81
  2016-01-01..2019-01-01    754  0.952  0.771  0.718 +0.181 +0.234       9    4     80
  2016-07-01..2019-07-01    753  1.444  1.218  1.178 +0.226 +0.266      15    7     98
  2017-01-01..2020-01-01    754  1.452  1.242  1.200 +0.210 +0.252      15    7    110
  2017-07-01..2020-07-01    754  1.436  1.010  0.942 +0.426 +0.494      25   11    121
  2018-01-01..2021-01-01    756  1.331  0.894  0.837 +0.436 +0.494      25   11    125
  2018-07-01..2021-07-01    755  1.560  1.036  0.970 +0.524 +0.589      22   10    123
  2019-01-01..2022-01-01    757  1.815  1.562  1.545 +0.252 +0.270      19    9    131
  2019-07-01..2022-07-01    757  1.478  1.097  1.091 +0.381 +0.387      23    7    118
  2020-01-01..2023-01-01    756  1.106  0.719  0.719 +0.387 +0.388      23    7     86
  2020-07-01..2023-07-01    755  1.235  1.103  1.135 +0.132 +0.100      13    3     75
  2021-01-01..2024-01-01    753  1.180  1.058  1.089 +0.122 +0.091      13    3    100
  2021-07-01..2024-07-01    753  1.463  1.370  1.362 +0.093 +0.101      13    3     88
  2022-01-01..2025-01-01    753  1.377  1.104  1.095 +0.273 +0.281      19    5     91
  2022-07-01..2025-07-01    751  1.420  1.321  1.297 +0.100 +0.123       9    4     95
  2023-01-01..2026-01-01    752  1.793  1.686  1.667 +0.108 +0.126       9    4    106
  2023-07-01..2026-07-01    751  1.726  1.556  1.524 +0.169 +0.201      21    8    141
  windows 33; negative vs const-D: 2; negative vs live: 2
```

```
(e) CONTINUOUS VERSION: QLD weight in D = f(pct) instead of the hard 0/1 at 0.20 (each mapping is one candidate; the
    hard threshold is the reference).  Controls: same-rows live and constant-D at matched capital; episode bootstrap vs const-D.
  mapping                                CAGR/Sh/MDD      S      H    exp  | vs live S/H | vs constD S/H  | ep-boot Sh CI vs constD  P<=0| real Sh
  hard: 1[pct>=0.2] (reference)31.71% / 1.218 / -28.5%  1.332  1.065  70.0%  +0.229/+0.189   +0.205/+0.178        [+0.079, +0.324] 0.000    1.490
  clip((pct-0.2)/0.3, 0, 1)   30.48% / 1.224 / -28.5%  1.337  1.073  67.5%  +0.235/+0.197   +0.187/+0.181        [+0.062, +0.306] 0.002    1.485
  clip((pct-0.1)/0.3, 0, 1)   31.00% / 1.217 / -28.1%  1.335  1.058  69.2%  +0.232/+0.182   +0.200/+0.167        [+0.075, +0.311] 0.000    1.458
  clip(pct/0.4, 0, 1)         30.23% / 1.186 / -28.0%  1.297  1.036  69.8%  +0.194/+0.160   +0.168/+0.149        [+0.068, +0.262] 0.001    1.413
  pct (linear 0..1)           26.47% / 1.148 / -28.3%  1.277  0.975  65.1%  +0.174/+0.099   +0.116/+0.087        [+0.010, +0.193] 0.019    1.400
  clip((pct-0.2)/0.6, 0, 1)   27.24% / 1.166 / -28.5%  1.290  0.999  64.9%  +0.188/+0.123   +0.129/+0.111        [+0.012, +0.235] 0.016    1.432
```

```
(f) ALTERNATE BREADTH DEFINITIONS with the SAME mechanism (D row to cash when the definition is 'weak'), on the SAME rows
    (rows where every definition has a value).  Mechanism-consistency check, not a search: a coherent mechanism should show
    the same sign on every definition; per-day stats are the QLD leg on gated vs other D days.
  rows 4661 2008-02-14..2026-08-26, D days 675; live 26.57% / 1.030 / -33.6% S 1.103 H 0.923
  definition                        on  Jacc gated bp other bp diff t           | CAGR/Sh/MDD      S      H  | vs live S/H | vs constD S/H | real
  QQEW/QQQ 60d change (reference)   89  1.00   -101.9     36.5  -2.98 32.39% / 1.243 / -27.2%  1.332  1.116  +0.229/+0.193   +0.209/+0.181  1.490
  avg of 20d and 60d changes        66  0.42    -56.4     26.3  -1.62 29.07% / 1.129 / -29.1%  1.159  1.086  +0.056/+0.163   +0.041/+0.153  1.285
  120d change                       93  0.24    -51.0     29.3  -1.78 29.51% / 1.159 / -33.3%  1.222  1.068  +0.120/+0.145   +0.098/+0.132  1.302
  log-ratio minus its 200d SMA     144  0.36    -38.9     33.7  -2.14 30.13% / 1.191 / -27.7%  1.225  1.142  +0.122/+0.220   +0.091/+0.202  1.411
  cap-wt minus eq-wt 60d, z>0.84   111  0.75    -70.7     35.7  -2.75 31.53% / 1.219 / -28.3%  1.296  1.106  +0.194/+0.183   +0.169/+0.169  1.496
  20d change (known to fail)        65  0.17     49.1     15.0   0.91 24.82% / 0.988 / -33.6%  1.048  0.899  -0.054/-0.024   -0.070/-0.034  1.255
```

Reading. (a) The base case is the project's standing convention (signal from the d0 close, trade at the d0 close, return d0→d1 — the
same convention the live design is scored on). One session of lag keeps about 85 % of the edge in both eras; two sessions keep the search
era and lose the holdout, which is the arithmetic of section 2: the holdout runs are one to three days long. Any live implementation that
cannot act on the signal day (or at worst the next) does not have the holdout evidence. (b) Costs are not the issue: the gate's extra turnover
costs 0.16 pp/yr at 4 bp and 0.77 pp/yr at 20 bp and at 20 bp still beats constant-D by +0.175/+0.152. (c) Resampling whole D
episodes gives essentially the same interval as the day-block bootstrap (episodes are short, so day blocks of 20–60 already contain them);
the 95 % interval excludes zero in Sharpe and in log-return. (d) 31 of 33 rolling windows are positive; the two negatives are the
2012–2015 windows where the gate fired on two days. (e) A smooth ramp from pct 0.2 to 0.5 is as good as the hard threshold (marginally
better on Sharpe, at 2.5 pp less capital); flatter ramps keep less, monotonically. A hard threshold that beat every smooth version would
have been a red flag; it does not. (f) Every definition with a horizon of 60 sessions or more agrees in sign in both eras and selects
gated D days that lose 40–100 bp the next day against +26..+36 bp on the other D days; the 20-day change picks different days (Jaccard
0.17) that do not lose money. The mechanism needs a multi-month leadership divergence.

## 6. The honest holdout

```
  start      end         days   QLD%   QQQ% exit gated g-days contrib  gated runs
  2007-08-03 2007-08-07     3   +5.8   +3.0    A   YES      1    -2.3  2007-08-03(1d -2.2)
  2007-08-10 2007-08-30    15   +6.0   +3.3    A     -      0    +0.0  
  2007-11-09 2007-12-24    31   +8.6   +4.9    A   YES     31    -6.5  2007-11-09(31d -6.5)
  2008-01-02 2008-01-04     3   -9.5   -4.6    E   YES      3    +8.6  2008-01-02(3d +8.6)
  2009-07-07 2009-07-13     5   +6.7   +3.4    A     -      0    +0.0  
  2009-10-30 2009-11-04     4   +6.6   +3.3    A     -      0    +0.0  
  2010-01-22 2010-02-26    25   +5.2   +2.8    A     -      0    +0.0  
  2010-05-06 2010-06-04    21  -11.1   -5.1    E   YES     13    +6.2  2010-05-14(9d +3.9), 2010-06-01(4d +2.4)
  2010-06-11 2010-06-28    12   -9.9   -4.8    E   YES      6    +9.2  2010-06-11(1d +0.0), 2010-06-17(1d +0.1), 2010-06-22(3d +3.1), 2010-06-28(1d +6.1)
  2011-03-10 2011-04-19    29   +5.8   +3.0    A   YES      2    +1.4  2011-03-10(1d -1.2), 2011-03-14(1d +2.8)
  2011-05-24 2011-05-27     4   +6.2   +3.1    A     -      0    +0.0  
  2011-06-03 2011-06-16    10   -9.4   -4.6    E     -      0    +0.0  
  2011-06-28 2011-06-30     3   +6.4   +3.2    A     -      0    +0.0  
  2011-08-02 2011-08-03     2   -7.9   -3.8    E   YES      2    +7.7  2011-08-02(2d +7.7)
  2011-12-13 2011-12-13     1   -3.2   -1.6    E     -      0    +0.0  
  2012-01-03 2012-01-03     1   +0.8   +0.4    A     -      0    +0.0  
  2012-04-24 2012-04-24     1   +5.2   +2.6    A     -      0    +0.0  
  2012-05-04 2012-06-28    39   -2.3   -0.8    A     -      0    +0.0  
  2012-07-12 2012-07-17     4   +6.1   +3.1    A     -      0    +0.0  
  2012-10-09 2012-11-06    19   -9.6   -4.7    E     -      0    +0.0  
  2013-04-18 2013-04-22     3   +6.6   +3.3    A     -      0    +0.0  
  2013-06-20 2013-07-09    13   +6.8   +3.4    A     -      0    +0.0  
  2014-01-29 2014-02-06     7   +5.4   +2.8    A     -      0    +0.0  
  2014-03-26 2014-05-20    39   +2.9   +1.7    A   YES      2    -3.5  2014-05-16(1d -1.5), 2014-05-20(1d -2.0)
  2014-10-07 2014-10-27    15   +7.0   +3.7    A     -      0    +0.0  
  2015-01-05 2015-02-09    25   +5.5   +2.9    A     -      0    +0.0  
  2015-06-29 2015-07-13    10   +6.5   +3.3    A   YES      4    +1.3  2015-07-01(1d -0.1), 2015-07-06(2d +3.0), 2015-07-13(1d -1.4)
  2015-08-20 2015-08-20     1   -9.1   -4.5    E   YES      1    +9.2  2015-08-20(1d +9.2)
  holdout: 28 D episodes, 10 with a gated day, 18 gated runs, contribution over D-episode days +31.3pp
  holdout gated runs ranked: 2015-08-20(1d +9.2), 2008-01-02(3d +8.6), 2011-08-02(2d +7.7), 2010-06-28(1d +6.1), 2010-05-14(9d +3.9), 2010-06-22(3d +3.1), 2015-07-06(2d +3.0), 2011-03-14(1d +2.8), 2010-06-01(4d +2.4), 2010-06-17(1d +0.1), 2010-06-11(1d +0.0), 2015-07-01(1d -0.1), 2011-03-10(1d -1.2), 2015-07-13(1d -1.4), 2014-05-16(1d -1.5), 2014-05-20(1d -2.0), 2007-08-03(1d -2.2), 2007-11-09(31d -6.5)
  -> the holdout gain rests on 11 positive runs in 7 D episodes; the top 3 runs carry +25.5pp of the holdout total +32.0pp; negative runs sum -14.9pp
```

```
  STRICT SPLIT (fit nothing; the rule is fixed; q of the constant-D control is (i) the full-sample 0.850 and (ii) re-matched
  to the gate's capital inside each half -- a control setting, not a fit).  Episode bootstrap CI per half.

  [holdout 2007-07..2015-10] n=2081  gate 26.23% / 1.065 / -28.5% exp 69.6% | live 21.51% / 0.876 / -30.0% | const-D q=0.850 20.75% / 0.886 / -29.7% exp 69.7% | const-D q=0.848 20.73% / 0.886 / -29.7% exp 69.6%
    vs live               point +3.81pp/yr +0.189 Sh | episode boot (28 eps) Sh CI [+0.012,+0.396] P<=0 0.017, logret CI [-0.60,+8.79] P<=0 0.050 | day-block 20d Sh P<=0 0.013, 60d 0.013
    vs const-D q=0.850    point +4.45pp/yr +0.178 Sh | episode boot (28 eps) Sh CI [+0.026,+0.362] P<=0 0.009, logret CI [+0.81,+8.63] P<=0 0.006 | day-block 20d Sh P<=0 0.015, 60d 0.013
    vs const-D q=0.848    point +4.46pp/yr +0.178 Sh | episode boot (28 eps) Sh CI [+0.026,+0.362] P<=0 0.011, logret CI [+0.81,+8.58] P<=0 0.005 | day-block 20d Sh P<=0 0.011, 60d 0.015

  [search 2015-11..2026-08] n=2719  gate 36.08% / 1.332 / -26.2% exp 70.3% | live 29.73% / 1.103 / -33.3% | const-D q=0.850 28.96% / 1.127 / -30.1% exp 70.2% | const-D q=0.853 28.97% / 1.127 / -30.1% exp 70.3%
    vs live               point +4.78pp/yr +0.229 Sh | episode boot (43 eps) Sh CI [+0.038,+0.437] P<=0 0.007, logret CI [+0.43,+9.58] P<=0 0.015 | day-block 20d Sh P<=0 0.008, 60d 0.004
    vs const-D q=0.850    point +5.38pp/yr +0.205 Sh | episode boot (43 eps) Sh CI [+0.037,+0.393] P<=0 0.006, logret CI [+1.73,+9.50] P<=0 0.002 | day-block 20d Sh P<=0 0.015, 60d 0.008
    vs const-D q=0.853    point +5.37pp/yr +0.205 Sh | episode boot (43 eps) Sh CI [+0.041,+0.384] P<=0 0.006, logret CI [+1.63,+9.27] P<=0 0.002 | day-block 20d Sh P<=0 0.009, 60d 0.005
```

Reading. The holdout is 28 D episodes over eight years; the gate fired in 10 of them, was right (episode broke down) in 5 and wrong in 5.
The five right calls are 2008-01, 2010-05, 2010-06, 2011-08 and 2015-08; four of them are one to three sessions long and each avoids a
single −3.8..−4.6 % QQQ day. The five wrong calls cost −14.9 pp in total, most of it the 31-day 2007-11 run. Net +32 pp on the gated runs.
Strictly split, with the constant-D control's capital matched inside the half, the holdout advantage is +0.178 Sharpe with an
episode-bootstrap interval [+0.026, +0.362] and a log-return interval [+0.81, +8.63] pp/yr; against live the log-return interval touches
zero (P 0.050). The search era is stronger (+0.205, [+0.037, +0.393]). Both halves clear zero on Sharpe without anything fitted; the
count of independent events behind the holdout number is five.

## 7. Plain-language reading and verdict

What the rule does, in words: state D means QQQ has slipped below its 50-day average but is still above its 200-day — a pullback inside
an uptrend, where the design holds 2× QQQ on the expectation that most pullbacks resolve upward (they do: 52 of the 71 D episodes on these
rows went back to A, 19 broke down to E). The breadth series asks whether, over the last three months, the average Nasdaq-100 stock has been falling behind
the cap-weighted index — whether the index has been held up by a few mega-caps while the typical stock is already weak. When that is
true *and* the index itself has cracked its 50d, the pullback tends to become the break of the 200d: 54 % of such days sit in an episode
that ends in E, versus 5 % when leadership is broad. The gate steps aside for exactly those days, and its value is concentrated in the
one or two sessions before the 200d gives way. The same divergence with the index still above its 50d is just what a mega-cap-led bull
looks like, and gating it loses money; that is why the D-only scope, chosen post hoc, is also the scope the mechanism predicts.

Verdict. The mechanism is coherent: it is state-specific in the way the story requires, it is not explained by exposure, by distance to
the 200d, or by vol, it survives being made continuous and being re-defined four ways, and the episode-level bootstrap and permutation
tests treat the ~70 episodes, not the 4,800 days, as the sample. On that basis the rule should be raised from "pre-register" to
**candidate** — meaning a rule with a mechanism worth a forward test whose decision is mechanical (section 8), not a rule to apply now
and not at half depth. The reservations are unchanged and quantified here: the evidence is 22 breakdown episodes, five of them in the
holdout; the holdout log-return advantage over live touches zero; the value depends on acting on the signal day (a two-session lag removes
the holdout); it was selected post hoc from 224 candidates (240 with this line); and it is a timing rule in a project where some 300
timing variants have failed. Nothing in this line changes the recommendation of the two earlier ones on *application*: no change.

## 8. Live tracking specification (pre-registration; frozen as written)

1. **Rule.** On each session d0 on which the live state machine's *effective* state (`state.effective_state`, after the 20/100 fast
   overlay — the same field the paper track logs) is D, compute `pct(d0)` as below. The rule **fires** on d0 iff `pct(d0) < 0.20`
   (strict). Hypothetical action when it fires: the D row's QLD leg (after the vol target) is held in cash for the session d0→d1; the
   trim and vol target are untouched; nothing else in the design changes. The rule is evaluated on paper only.
2. **Data.** Split-adjusted daily closes of QQEW and QQQ, both for the same session; source as in `data/breadth_provenance.md` (Yahoo
   chart API via curl through the session proxy; Robinhood `get_equity_historicals` as the cross-check source, closes agree). The
   series is built on the QQQ session calendar; QQEW is forward-filled onto it only for sessions QQEW did not print (none in practice).
   If either close for d0 is not available by the time of the daily run, the reading is logged as `no reading` and the rule is treated as
   **not fired** — a stale leg never counts (section 6 of the log shows what a stale QQQ leg does to the value).
3. **Percentile.** `x(d) = log(QQEW_d / QQQ_d) − log(QQEW_{d−60} / QQQ_{d−60})` over 60 *sessions*. `pct(d0)` = trailing-252
   percentile of `x(d0)` among `x(d0−251)..x(d0)` (inclusive of today, exactly 252 values, ties split: `(lo + 0.5·(hi−lo))/252` where
   `lo`/`hi` are the bisect positions of `x(d0)` in the sorted window) — the `trailing_pct` function in `paper-track/breadth_dgate_2000.py`,
   which this line exec's verbatim. No full-sample constants anywhere.
4. **Logged each D day** (append-only, one row per session with effective state D): date; effective state; `x(d0)`; `pct(d0)`;
   fires (Y/N); the live design's QLD weight that day; the QLD leg's d0→d1 return; QQQ's d0→d1 return; the effective state on d1;
   gap200 on d0. Plus, once per calendar month, a row with the current `pct` regardless of state (drift check on the percentile itself).
5. **Episode bookkeeping.** A *gated run* is a maximal set of consecutive D sessions on which the rule fired. A run's outcome is the
   sum of log(1 + QLD leg) over its sessions, and the exit state of its D episode.
6. **Pre-declared decision** — evaluated when **8 gated runs** have completed or **48 months** have elapsed, whichever comes first
   (historical rate: ~2 runs and ~6.5 gated days per year; 8 runs ≈ 4 years):
   - *Primary (per day):* mean QLD-leg d0→d1 return on gated D days minus the mean on un-gated D days over the tracking window is
     negative with P < 0.05 under the circular-shift null of section 3(d) (the on/off pattern shifted within the tracked D days,
     2,000 shifts). Historical value of the statistic: −108 bp/day.
   - *Secondary (per run):* at least 5 of the 8 runs have a negative QLD-leg sum (historical: 26 of 40).
   - *Transition check:* the share of gated-run episodes that exit to E/F is at least 0.40 (historical 0.54; base rate for D episodes
     0.16). Reported, not decisive.
   - **Pass** = primary and secondary both met → the rule is eligible for the normal change process (both-era harness re-run on the
     extended rows, exposure control, block and episode bootstrap, owner decision). **Fail** = primary not met, or the gated mean is not
     below the un-gated mean → the rule is retired and not re-tuned. **Early stop (fail)** at any point if the rule fires on more than
     40 % of tracked D days over any trailing 12 months (the percentile has drifted from the regime it was found in) or if 4 consecutive
     runs end with a positive QLD-leg sum.
   - No parameter (window, threshold, depth, scope, series) may be changed during tracking; a change restarts the clock.
7. **Today's reading** (for the record; the log's section 6): with both legs fresh, 2026-09-04 `x` = +0.0465, `pct` = 0.867; the
   provisional 2026-09-09 reading with a stale QQQ leg is 0.819. Far from 0.20, and the last proxy row (2026-08-26) is state A: the rule
   is off and would have been off.

```
  QQEW_daily.csv last date 2026-09-09; data/qqq_long_history.csv last date 2026-09-04; harness QQQ (QQQ+XLU common) last date 2026-08-27;
  last proxy row 2026-08-26 state A eff A.  The table below recomputes the series with the FULL QQQ file
  (the exec'd code uses the harness QQQ, which is stale after 2026-08-27); a leg marked stale is forward-filled and the reading is provisional.
  date          log(QQEW/QQQ)  60d chg  pct252  fires?  legs
  2026-08-27         -1.46550  +0.0703   0.911      no  both fresh
  2026-08-28         -1.46507  +0.0760   0.911      no  both fresh
  2026-08-31         -1.46807  +0.0738   0.907      no  both fresh
  2026-09-01         -1.47422  +0.0606   0.895      no  both fresh
  2026-09-02         -1.47851  +0.0642   0.899      no  both fresh
  2026-09-03         -1.48539  +0.0571   0.879      no  both fresh
  2026-09-04         -1.49417  +0.0465   0.867      no  both fresh
  2026-09-08         -1.50821  +0.0381   0.831      no  QQQ stale
  2026-09-09         -1.51338  +0.0320   0.819      no  QQQ stale
  2026-09-10         -1.51338  +0.0353   0.819      no  QQEW stale QQQ stale
```
