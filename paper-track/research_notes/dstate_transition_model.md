# Research line `dstate_transition_model` (2026-09-11): P(breakdown) for a state-D episode

Research only. Nothing here is applied; the discipline in BRIEFING.md (ADDENDUM 2026-09-10) binds. No commits, no edits to any
protected file, no new data files.
Script: `paper-track/dstate_transition_model.py` (run from the repo root; `DSTM_SAMPLES=Q` then `=C`, ~4-5 min each; `DSTM_FAST=1`
runs both samples with 300 bootstrap draws in ~4 min). No numpy / sklearn / statsmodels exist in this environment: the logistic
regression is Newton-Raphson in the standard library. Full logs: `research_notes/dstate_transition_model_Q.log` and `_C.log`.

Question. On any effective-state-D day, what is the probability that the episode ends in a **breakdown** (next effective state E or F:
QQQ breaks its 200d) rather than a **recovery** (A, or B via the 20/100 fast overlay)? The `dgate_anatomy` line's one-feature bucket
table is the baseline: P(E/F) by trailing-252 quintile of the 60d change of log(QQEW/QQQ) = **0.54 / 0.27 / 0.05 / 0.05 / 0.30** on
n = 124/162/187/132/122 D days (727 D days, 71 episodes, 2007-07-27..2026-08-26). Does a multi-feature, calibrated model beat it, and
does a calibrated P add anything to the one-feature gate as a *policy*?

## 0. Summary

- **Reproduction.** Standing figures 22.18% / 0.913 / -33.6%, S 1.103 H 0.768, real 31.40% / 1.248 / -25.0% reproduced through the
  harness (the exec'd `breadth_dgate_2000` section asserts them); the anatomy reference figures (live 26.09/1.006, gate 31.71/1.218,
  S 1.332 H 1.065) and the bucket table (0.54/0.27/0.05/0.05/0.30 on 124/162/187/132/122) reproduced by exec'ing the anatomy code
  verbatim and asserted.
- **Two samples.** Q: 727 D days / 71 episodes / 19 breakdowns on the QQEW rows (2007-07+). C: 934 D days / 88 episodes / 25
  breakdowns on the full 2000-07+ proxy rows with the survivorship-free NASDAQCOM/NASDAQ100 breadth (adds 17 episodes from 2000-2006).
  Every exit on both samples is A or E (never B, C or F).
- **Predicting the label (section 3).** Grouped 10-fold CV (folds = whole episodes), everything chosen inside the training fold.
  On Q the all-feature L2 logistic beats the bucket table on every view: day-weighted log-loss **0.462 vs 0.506** (constant 0.532),
  first-day-of-episode 0.546 vs 0.565, per-episode mean 0.469 vs 0.479, AUC 0.79 vs 0.67. The nested forward-selection model
  (gap200 + breadth-U + composite breadth in 8 of 10 folds) is marginally better still (0.454 / 0.517 / 0.394). On C the bucket table
  is **useless** (log-loss 0.594 vs constant 0.551, AUC 0.48) and the all-feature model recovers 0.518 / 0.518 / 0.459, AUC 0.68.
- **But the gain is gap200.** Forward selection picks gap200 first in 20 of 20 folds; its coefficient (-0.96 per sd on Q, -0.61 on
  C) is the only one whose episode-bootstrap interval is far from zero on both samples. The model **without** gap200/gap50
  (`noGap-L2`) is *no better than the bucket table* (Q day log-loss 0.529 vs 0.506; C 0.596 vs 0.594). On days at least five
  sessions before the exit the all-feature edge over the bucket shrinks to 0.518 vs 0.526 (Q). Distance to the 200d predicts the
  transition label largely because the label *is* "price reaches the 200d": it is a mechanical predictor, and the anatomy line already
  showed that gap200 gates carry no return (placebo gates -0.25 on the holdout).
- **Decision value (section 6): a null result.** Through the harness, with the out-of-fold P (each day's P from the fold in which its
  episode was held out), **no P-driven policy beats the plain breadth gate** (Q: gate 31.71% / 1.218 / -28.5%, S 1.332 H 1.065,
  +0.205/+0.178 vs constant-D). The best all-feature threshold policy is `cash > 0.5`: +0.098/+0.083 vs constant-D, half the gate;
  at p* 0.3-0.4 the search era matches the gate (+0.19..+0.20) but the **holdout goes to zero** (-0.015..+0.004). The continuous
  `w = 1-P` gives +0.101/+0.053. The bucket table's own OOF P reproduces the gate exactly at p* = 0.4 (only the bottom quintile
  exceeds 0.4 in every fold). Adding model days to the gate (`gate | P > 0.8`) changes the gate by +0.018/+0.000 on 3 extra days;
  removing gated days by P (`gate & P > 0.5`) costs -0.16/-0.05. On C every all-feature policy is negative on the holdout.
- **Why:** inside the 124 gated days the model's P does not separate the QLD leg (Q: P below the gated median -100 bp/day, above it
  -41 bp — the wrong direction), and outside the gate the days it flags (P > 0.5, n = 32) return -17 bp/day with t -0.3: the model
  finds no money the gate misses and cannot rank the money the gate has. The breadth gate's value is the breakdown *day*; the model
  predicts the breakdown *episode*.
- **Temporal drift (section 4).** Fitting on episodes ending before 2015-11 and testing after keeps the ordering (fwd-sel 0.437, bucket
  0.502, constant 0.558 on Q). The reverse on C (fit 2015-11+, test 2000-2015) breaks every model *and* the bucket table (0.75-1.01
  vs constant 0.546): the composite-breadth relation of the SPMO era does not describe 2000-2015.
- **Today** (section 7). Last proxy row 2026-08-26 is state A. A hypothetical first D day with today's features (breadth pct 0.90 /
  composite 0.78, gap200 +8.8 %, gap50 -0.1 %, vol30 21.7 %, fast state A, DGS2 +14 bp over 60 sessions): all-feature
  **P(breakdown) = 0.03 [0.004, 0.13]** on Q, 0.06 [0.02, 0.15] on C, against bucket base rates 0.30 / 0.16. With the freshest
  2026-09-04 features (fast state now D, gap200 +9.3 %): 0.026 [0.006, 0.072] / 0.086 [0.037, 0.193]. Far above the 200d: low.
- **Verdict.** The model beats the bucket table as a *probability* (log-loss -0.04 to -0.08, AUC +0.12..+0.20) but not by anything
  that matters, because the improvement is the distance to the 200d, which is nearly tautological for this label and worthless as a
  timing input. As a policy it is strictly dominated by the one-feature gate on both eras. **Null result on decision value; the bucket
  table (or the gate) is the right owner-facing reading of a D day, with gap200 as context, not as a signal.**
- Candidate count: 7 model classes x 2 samples with fold-internal hyper-parameters (no sweep), 47 harness policy cells per sample
  reported in full, nothing selected; cumulative with the earlier lines 240 + 0 rules proposed.

## 1. Standing figures (reproduced through the harness; asserted in the script)

```
STANDING FIGURES (must match briefing 22.18/0.913/-33.6, S 1.103 H 0.768; real 31.40/1.248/-25.0):
  26y proxy 22.18% / 0.913 / -33.6%  S 1.103 H 0.768  exp 67.7% | real weekly 31.40% / 1.248 / -25.0% | rows 6575 2000-07-03..2026-08-26, real rows 564
REFERENCE on the 4800 QQEW rows 2007-07-27..2026-08-26 (must match the earlier notes):
  live   26.09% / 1.006 / -33.6% S 1.103 H 0.876 exp 72.1%   (note: 26.09/1.006/-33.6 S 1.103 H 0.876)
  gated  31.71% / 1.218 / -28.5% S 1.332 H 1.065 exp 70.0%   (note: 31.71/1.218/-28.5 S 1.332 H 1.065)
  const-D q=0.850 25.32% / 1.024 / -31.2% S 1.127 H 0.886 exp 70.0%
ANATOMY BUCKET TABLE (reused grid(); must match P(E/F) 0.54/0.27/0.05/0.05/0.30 on n=124/162/187/132/122):
  bucket      n  eps  P(E/F)  P(A/B) P(to D) P(down) to-chg  d1 bp   fwd5  fwd10  fwd20  med20  vol20
  0.0-0.2   124   23    0.54    0.46    0.00    0.54    9.4  -34.8  -1.32  -2.05  -1.91  -0.97   29.7
  0.2-0.4   162   35    0.27    0.73    0.00    0.27   11.2   11.1   0.74   1.12   2.25   3.62   18.2
  0.4-0.6   187   36    0.05    0.95    0.00    0.05    8.9   21.8   1.09   2.02   3.50   4.18   17.1
  0.6-0.8   132   26    0.05    0.95    0.00    0.05    9.8   27.6   1.69   2.97   4.92   5.60   15.6
  0.8-1.0   122   20    0.30    0.70    0.00    0.30    9.4   15.4   0.30   0.83   2.01   2.74   17.9
  reproduced.
```

Reuse: `breadth_dgate_2000.py` sections 0-3 (192 lines: standing-figure assert, data, `ratio_series`/`diffs`/`trailing_pct`, row
attachment, `trimmed`/`scale_risky`/`gate_fn`/`const_D`/`calib_q`) and, from `dgate_anatomy.py`, the reference-row block
(`RQ`, `episodes()`, `EP_D`, `exit_state()`, `ep_of()`, `gated()`), the `grid()` bucket table and `ep_boot()` are exec'd verbatim.

## 2. Samples, labels, features

Label per day = the eventual exit of the day's episode (E/F = 1, A/B = 0; every day of an episode shares it). Episodes come from
`episodes('D')` on the full rows (so an episode that straddles the QQEW start keeps its true start). Features, all at the d0 close:

| name | definition |
|---|---|
| `bp` | breadth percentile: trailing-252 pct of the 60-session change of log(QQEW/QQQ) (sample Q) / log(NASDAQCOM/NASDAQ100) (sample C) |
| `bp_sq` | (bp - 0.5)^2, the U-shape term (the top quintile also carries P(E/F) 0.30) |
| `bp_comp` | the composite/NDX percentile, as a second breadth feature on sample Q |
| `gap200`, `gap50` | close / SMA - 1 |
| `vol30`, `vol_pct` | 30d realized vol (`r['vol']`) and its trailing-252 percentile (`trailing_pct` on the daily series; the first 191 sessions of 2000 use an expanding, still causal, percentile) |
| `ldse` | log1p(sessions since the episode began) |
| `ret20` | QQQ 20-session return |
| `fast_def` | 1 if the fast 20/100 state is already D/E/F |
| `volratio` | 10d / 30d realized vol |
| `dgs2_60` | DGS2 (FRED, forward-filled on holidays) minus its value 60 sessions earlier, pp |

Standardization uses the training fold's mean and sd only. The fit is day-weighted (every D day one observation), the evaluation is
reported day-weighted, on the first day of each episode, on the per-episode mean of the daily P, and on days at least 5 sessions before
the exit (`>=5d to exit`), which removes the last sessions where gap200 is trivially near zero.

```
  [Q: QQEW rows 2007-07+] D days 727, episodes 71, breakdown episodes 19 (0.27), breakdown days 163 (0.22); exits {'A': 52, 'E': 19}
  [C: full proxy rows 2000-07+ (composite/NDX breadth)] D days 934, episodes 88, breakdown episodes 25 (0.28), breakdown days 224 (0.24); exits {'E': 25, 'A': 63}

  feature means on D days by label (raw units), sample Q:
  feature      recover  breakdown  diff t  |  sample C:    recover  breakdown  diff t
  bp            0.5251     0.3783   -5.31  |      0.5464     0.4414   -3.91
  bp_sq         0.0638     0.1207    8.69  |      0.0872     0.1376    7.76
  bp_comp       0.5478     0.2965   -9.82  |
  gap200        0.0641     0.0285  -15.75  |      0.0612     0.0273  -17.57
  gap50        -0.0187    -0.0304   -7.11  |     -0.0180    -0.0289   -7.95
  vol30         0.1961     0.2068    1.93  |      0.1904     0.1952    0.99
  vol_pct       0.6378     0.6864    2.20  |      0.5957     0.5612   -1.50
  ldse          1.9144     1.7487   -1.95  |      1.9623     1.9865    0.29
  ret20        -0.0261    -0.0371   -4.04  |     -0.0247    -0.0341   -4.13
  fast_def      0.7766     0.9080    4.58  |      0.7775     0.8839    4.01
  volratio      1.0860     1.1443    2.55  |      1.0780     1.1129    1.92
  dgs2_60      -0.0479    -0.0854   -1.16  |     -0.0142     0.0838    3.00
  (t is day-weighted and overstated: the ~70-90 episodes are the independent units, not the days)
```

## 3. Grouped cross-validation (the main result)

Models: `bucket` = training-fold quintile frequency of the breakdown label (Jeffreys-smoothed (k+0.5)/(n+1) so a fold with an empty
bucket has finite log-loss); `breadth` = logistic on `bp` alone; `breadth+U` = logistic on `bp`, `bp_sq`; `all-L2` = L2 logistic on
every feature, lambda from an inner grouped 5-fold CV over {0.03..100}; `noGap-L2` = the same without `gap200`/`gap50`; `fwd-sel` =
1-3 features by nested forward selection on the inner CV log-loss (lambda 3); `stump` = one feature, one threshold, chosen by training
log-loss. Folds are whole episodes, stratified on the episode label.

```
  [Q] grouped 10-fold, out-of-fold metrics   (lambda chosen per fold: all-L2 30 x8, 100 x2, 10 x1; breadth 100 x8)
  model      | day: logloss  Brier    AUC | first-day: logloss  Brier    AUC | ep-mean: logloss  Brier    AUC | >=5d to exit: ll  Brier    AUC
  bucket             0.5057 0.1672  0.673               0.5645 0.1842  0.645             0.4790 0.1619  0.802             0.5255 0.1745  0.628
  breadth            0.5562 0.1801  0.569               0.5862 0.1951  0.609             0.5859 0.1948  0.615             0.5503 0.1773  0.555
  breadth+U          0.5556 0.1844  0.671               0.5624 0.1872  0.699             0.5461 0.1826  0.757             0.5763 0.1919  0.635
  all-L2             0.4615 0.1497  0.790               0.5461 0.1654  0.796             0.4693 0.1346  0.887             0.5176 0.1710  0.703
  noGap-L2           0.5294 0.1731  0.652               0.5478 0.1811  0.670             0.5259 0.1729  0.700             0.5573 0.1836  0.595
  fwd-sel            0.4536 0.1449  0.813               0.5173 0.1609  0.802             0.3941 0.1215  0.897             0.5229 0.1686  0.747
  stump              0.5392 0.1748  0.608               0.5828 0.1899  0.601             0.4914 0.1581  0.744             0.5874 0.1926  0.535
  (constant P = sample base rate 0.224: day log-loss 0.5322, Brier 0.1739; n days 727, episodes 71; days >=5 to exit 485)
  forward selection per fold: gap200 first in 10/10; then bp_sq / bp_comp (8 folds), gap200 alone (1), gap200+bp_sq (1)
  stump per fold: gap200 < 0.036..0.044 -> P 0.44..0.54 else 0.08..0.11 (8 folds); bp_comp < 0.30 -> 0.48..0.51 else 0.09 (2)

  [Q] second fold assignment (fold noise)
  bucket             0.4906 0.1616  0.673               0.5497 0.1801  0.649             0.4702 0.1572  0.799             0.5044 0.1656  0.637
  breadth+U          0.5196 0.1715  0.686               0.5415 0.1794  0.673             0.5191 0.1718  0.752             0.5237 0.1732  0.654
  all-L2             0.4266 0.1405  0.808               0.5027 0.1735  0.771             0.4106 0.1351  0.878             0.4775 0.1585  0.730
  noGap-L2           0.4951 0.1602  0.675               0.5440 0.1790  0.678             0.5194 0.1689  0.718             0.5072 0.1645  0.621

  [Q] leave-one-episode-out (71 folds; lambda fixed at the median 10-fold choice: all-L2 30, breadth 100 -- a mild leak)
  bucket             0.5097 0.1688  0.636               0.5565 0.1825  0.604             0.4800 0.1616  0.790             0.5288 0.1748  0.603
  breadth            0.5471 0.1777  0.540               0.5796 0.1937  0.599             0.5822 0.1943  0.622             0.5374 0.1735  0.516
  breadth+U          0.5196 0.1709  0.649               0.5435 0.1806  0.668             0.5289 0.1763  0.751             0.5231 0.1721  0.601
  all-L2             0.4387 0.1445  0.792               0.4985 0.1706  0.783             0.4100 0.1339  0.881             0.4905 0.1625  0.710
  noGap-L2           0.5197 0.1698  0.636               0.5500 0.1825  0.666             0.5287 0.1740  0.694             0.5363 0.1759  0.580
  stump              0.4977 0.1592  0.525               0.5567 0.1815  0.555             0.4633 0.1519  0.800             0.5294 0.1696  0.434
```

```
  [C] grouped 10-fold, out-of-fold metrics   (lambda: all-L2 100 in 10/10 folds; noGap 100 in 10/10)
  model      | day: logloss  Brier    AUC | first-day: logloss  Brier    AUC | ep-mean: logloss  Brier    AUC | >=5d to exit: ll  Brier    AUC
  bucket             0.5938 0.1954  0.484               0.6068 0.2022  0.560             0.5813 0.1957  0.628             0.6297 0.2077  0.402
  breadth            0.5921 0.1927  0.471               0.5843 0.1983  0.632             0.5877 0.1989  0.646             0.6133 0.1983  0.385
  breadth+U          0.5662 0.1872  0.494               0.5826 0.1955  0.590             0.5731 0.1934  0.641             0.5858 0.1940  0.412
  all-L2             0.5176 0.1715  0.684               0.5184 0.1731  0.745             0.4586 0.1509  0.872             0.5810 0.1951  0.553
  noGap-L2           0.5956 0.1951  0.460               0.6079 0.2017  0.544             0.5892 0.1963  0.606             0.6285 0.2070  0.359
  fwd-sel            0.4903 0.1636  0.737               0.5208 0.1777  0.763             0.4147 0.1375  0.856             0.5530 0.1877  0.646
  stump              0.5186 0.1707  0.642               0.5721 0.1884  0.642             0.4716 0.1567  0.820             0.5666 0.1890  0.569
  (constant P = sample base rate 0.240: day log-loss 0.5509, Brier 0.1823; n days 934, episodes 88; days >=5 to exit 641)
  forward selection per fold: gap200 alone in 7/10; + ldse / + dgs2_60,vol30 / + bp_sq,fast_def once each
  stump per fold: gap200 < 0.025..0.042 in 10/10 -> P 0.39..0.65 else 0.08..0.16

  [C] leave-one-episode-out (88 folds; lambda 100 / 100)
  bucket             0.6124 0.1991  0.427               0.6196 0.2070  0.499             0.5948 0.2001  0.580             0.6520 0.2117  0.335
  breadth            0.5946 0.1944  0.441               0.5948 0.2023  0.583             0.5980 0.2029  0.601             0.6120 0.1991  0.352
  breadth+U          0.5765 0.1899  0.444               0.5916 0.1990  0.558             0.5809 0.1961  0.615             0.5975 0.1969  0.352
  all-L2             0.5367 0.1774  0.642               0.5319 0.1788  0.734             0.4715 0.1566  0.856             0.6028 0.2012  0.497
  noGap-L2           0.6158 0.2006  0.423               0.6216 0.2072  0.527             0.6028 0.2011  0.575             0.6521 0.2130  0.315
  stump              0.5136 0.1691  0.573               0.5629 0.1853  0.572             0.4700 0.1569  0.827             0.5564 0.1844  0.510
```

Calibration (fixed-width bins of the out-of-fold P; day-weighted and first-day-of-episode):

```
  [Q] bucket                                          [Q] all-L2
  bin        n days  mean P realized | n eps  mean P realized      bin        n days  mean P realized | n eps  mean P realized
  0.0-0.1       319   0.055    0.053      27   0.052    0.111      0.0-0.1       234   0.050    0.021      19   0.054    0.000
  0.1-0.2        29   0.198    0.586       2   0.198    0.500      0.1-0.2       169   0.142    0.189      13   0.147    0.231
  0.2-0.3       130   0.251    0.423      15   0.255    0.400      0.2-0.3        99   0.241    0.222      14   0.251    0.357
  0.3-0.4       125   0.336    0.056      11   0.333    0.000      0.3-0.4        74   0.348    0.405       8   0.334    0.125
  0.4-0.5        24   0.491    1.000       0     nan      nan      0.4-0.5        53   0.449    0.472       3   0.479    0.667
  0.5-0.6        65   0.534    0.615      13   0.536    0.615      0.5-0.6        29   0.540    0.379       2   0.513    0.500
  0.7-0.8        35   0.717    0.086       3   0.717    0.333      0.6-0.7        20   0.638    0.450       4   0.642    0.500
                                                                   0.7-0.8        17   0.741    0.706       0     nan      nan
                                                                   0.8-0.9        17   0.844    0.588       6   0.857    0.667
                                                                   0.9-1.0        15   0.932    0.467       2   0.961    0.500
  [C] bucket                                          [C] all-L2
  0.0-0.1        48   0.092    0.312       5   0.092    0.600      0.0-0.1       165   0.071    0.042      12   0.075    0.000
  0.1-0.2       415   0.135    0.234      35   0.138    0.143      0.1-0.2       312   0.147    0.212      29   0.147    0.207
  0.2-0.3       240   0.251    0.121      26   0.255    0.269      0.2-0.3       215   0.246    0.251      18   0.240    0.222
  0.3-0.4        65   0.337    0.292       4   0.368    0.500      0.3-0.4       114   0.344    0.342      12   0.328    0.500
  0.4-0.5        87   0.430    0.655      15   0.430    0.467      0.4-0.5        66   0.442    0.409      11   0.434    0.364
  0.5-0.6        79   0.546    0.089       3   0.562    0.333      0.5-0.6        31   0.546    0.645       3   0.557    1.000
                                                                   0.6-0.7        20   0.655    0.300       2   0.638    0.500
                                                                   0.7-0.8        11   0.736    0.455       1   0.715    1.000
```

Reading. (i) On Q the all-feature model beats the bucket table on every view and under both fold assignments and LOEO: day log-loss
0.44-0.46 vs 0.49-0.51, first-day 0.50-0.55 vs 0.55-0.56, AUC 0.79-0.81 vs 0.64-0.67. It is also better calibrated: the bucket
table's out-of-fold P is lumpy (its 0.3-0.4 bin realizes 0.06, its 0.7-0.8 bin 0.09 — the top-quintile rate swings 0.20-0.36
between folds), the model's bins track realized frequency to within ~0.1 up to P 0.5 and are over-confident above (0.9+ realizes
0.47 on 15 days). (ii) The gain is the distance to the 200d. `noGap-L2` — the same model without gap200/gap50 — is *worse* than the
bucket table on Q (0.529 vs 0.506 day-weighted; 0.548 vs 0.565 first-day is the one view where it edges ahead) and identical to it on
C (0.596 vs 0.594). The stump chooses gap200 in 18 of 20 folds. (iii) The linear breadth-only logistic is worse than the bucket table
(0.556 vs 0.506) because the relation is U-shaped; adding the U term recovers part of it (0.520-0.556) but the two-parameter curve
never matches the five-cell table on Q, i.e. the bucket table's shape is not an artefact of a smooth relation. (iv) On C the
composite-breadth bucket table has no information (AUC 0.43-0.48, log-loss above the constant); this is consistent with
`breadth_dgate_2000`, where the composite gate validated only weakly. (v) On days at least 5 sessions before the exit the
all-feature edge over the bucket table shrinks to 0.518 vs 0.526 (Q, first assignment; 0.478 vs 0.504 second; 0.491 vs 0.529
LOEO) and the AUC to 0.70 vs 0.63: a real but modest early-warning content.

## 4. Time-ordered evaluation

```
  [Q] fit <2015-11 (28 eps) -> test 2015-11+ (43 eps): all-L2 lambda 100; fwd-sel [gap200, bp_sq, ldse]; stump gap200 < 0.011 -> 0.79 else 0.14
  model      | day: logloss  Brier    AUC | first-day: logloss  Brier    AUC | ep-mean: logloss  Brier    AUC | >=5d to exit: ll  Brier    AUC
  bucket             0.5018 0.1631  0.779               0.5632 0.1760  0.710             0.4711 0.1622  0.760             0.5113 0.1656  0.783
  breadth            0.5584 0.1858  0.782               0.5733 0.1920  0.690             0.5743 0.1924  0.663             0.5538 0.1839  0.849
  breadth+U          0.5341 0.1777  0.744               0.5427 0.1812  0.693             0.5383 0.1803  0.746             0.5335 0.1772  0.763
  all-L2             0.4876 0.1614  0.776               0.5259 0.1743  0.702             0.4720 0.1552  0.855             0.5337 0.1780  0.662
  noGap-L2           0.5409 0.1795  0.641               0.5653 0.1896  0.619             0.5414 0.1813  0.699             0.5587 0.1855  0.568
  fwd-sel            0.4370 0.1470  0.844               0.5303 0.1819  0.770             0.4144 0.1417  0.861             0.5006 0.1692  0.795
  stump              0.5110 0.1620  0.612               0.6430 0.2162  0.514             0.4481 0.1446  0.857             0.5783 0.1889  0.529
  (constant P = 0.246: day log-loss 0.5580; n days 382, episodes 43; days >=5 to exit 234)

  [Q] fit 2015-11+ -> test <2015-11: all-L2 lambda 10; fwd-sel [bp_comp, gap200, bp_sq]; stump bp_comp < 0.296 -> 0.63 else 0.07
  bucket             0.5036 0.1712  0.698               0.5708 0.1915  0.691             0.4577 0.1465  0.800             0.5233 0.1792  0.653
  breadth            0.5651 0.1731  0.540               0.6159 0.1955  0.634             0.5744 0.1773  0.684             0.5630 0.1735  0.497
  breadth+U          0.5414 0.1788  0.689               0.5670 0.1882  0.697             0.4820 0.1536  0.759             0.5713 0.1903  0.653
  all-L2             0.5071 0.1738  0.720               0.5821 0.1995  0.750             0.4471 0.1496  0.838             0.5511 0.1882  0.648
  noGap-L2           0.5522 0.1790  0.607               0.6509 0.2111  0.637             0.5984 0.1881  0.656             0.5618 0.1823  0.555
  fwd-sel            0.5097 0.1725  0.749               0.5352 0.1803  0.781             0.4019 0.1385  0.856             0.5666 0.1899  0.680
  stump              0.5869 0.1929  0.580               0.7021 0.2282  0.588             0.6190 0.1966  0.641             0.5922 0.1962  0.550
  (constant P = 0.200: day log-loss 0.5004; n days 345, episodes 28; days >=5 to exit 251)

  [C] fit <2015-11 (45 eps) -> test 2015-11+ (43 eps): all-L2 lambda 100; fwd-sel [gap200]; stump dgs2_60 < 0.55 -> 0.18 else 0.94
  bucket             0.5990 0.2010  0.426               0.6218 0.2093  0.412             0.6046 0.2030  0.432             0.6042 0.2024  0.408
  breadth            0.6017 0.2006  0.102               0.6061 0.2032  0.219             0.6063 0.2032  0.185             0.5993 0.1995  0.091
  breadth+U          0.5723 0.1913  0.536               0.5813 0.1954  0.523             0.5741 0.1924  0.514             0.5734 0.1915  0.514
  all-L2             0.5185 0.1724  0.690               0.5472 0.1830  0.653             0.4769 0.1570  0.830             0.5827 0.1960  0.522
  noGap-L2           0.5857 0.1984  0.484               0.5970 0.2022  0.503             0.5667 0.1911  0.551             0.6134 0.2091  0.396
  fwd-sel            0.4363 0.1422  0.829               0.5314 0.1778  0.733             0.4001 0.1336  0.889             0.5023 0.1677  0.753
  stump              0.6784 0.2232  0.490               0.7091 0.2360  0.469             0.6059 0.2058  0.497             0.7407 0.2439  0.464
  (constant P = 0.246: day log-loss 0.5580; n days 382, episodes 43)

  [C] fit 2015-11+ -> test <2015-11: all-L2 lambda 10; fwd-sel [bp, gap200]; stump bp < 0.296 -> 0.63 else 0.07
  bucket             0.9556 0.2609  0.427               0.8608 0.2519  0.574             0.8665 0.2520  0.556             1.0150 0.2770  0.372
  breadth            1.0107 0.2597  0.392               0.8603 0.2572  0.567             0.8772 0.2554  0.555             1.0857 0.2748  0.327
  breadth+U          0.8877 0.2629  0.392               0.8366 0.2623  0.567             0.8410 0.2619  0.553             0.9407 0.2779  0.327
  all-L2             0.7495 0.2524  0.608               0.7123 0.2290  0.698             0.6331 0.2160  0.728             0.8222 0.2763  0.530
  noGap-L2           0.7292 0.2414  0.398               0.7625 0.2441  0.551             0.7543 0.2470  0.537             0.7592 0.2524  0.309
  fwd-sel            0.8623 0.2582  0.578               0.6971 0.2195  0.737             0.6171 0.2026  0.763             0.9818 0.2873  0.489
  stump              0.7126 0.2349  0.508               0.7219 0.2359  0.601             0.6685 0.2161  0.644             0.7542 0.2502  0.463
  (constant P = 0.236: day log-loss 0.5458; n days 552, episodes 45)
```

Reading. Forward in time on Q (fit on the 28 pre-SPMO episodes, test on the 43 since) the ordering holds: fwd-sel 0.437 < all-L2 0.488
< bucket 0.502 < constant 0.558. Backward on Q the all-feature model and the bucket table are level (0.507 vs 0.504 day-weighted; the
model wins on the episode views, the bucket on the first-day view). On C the backward test is a wipe-out for everything: fitted on the
SPMO era, every model *and* the bucket table are far worse than the constant on 2000-2015 (0.71-1.01 vs 0.546) — the composite-breadth
sign flips (the 2015+ stump "bp < 0.30 -> 0.63" applied to 2000-2015 is the wrong way round; AUC 0.33-0.39). Whatever relation exists
between composite breadth and D-breakdowns in the SPMO era did not exist in the dot-com and GFC episodes. gap200 is the only feature
that transfers in all four directions.

## 5. Coefficients (all-L2 on the whole sample, standardized units, 400 episode-bootstrap refits)

```
  [Q] lambda 30, n 727                                 [C] lambda 100, n 934
  feature       coef  boot lo  boot hi  P(sign flips)    feature       coef  boot lo  boot hi  P(sign flips)
  intercept   -1.754   -2.871   -1.021                   intercept   -1.344   -2.506   -0.689
  bp          -0.294   -0.820    0.177           0.12    bp          -0.179   -0.565    0.171           0.16
  bp_sq        0.608    0.174    0.962           0.00    bp_sq        0.306   -0.002    0.565           0.03
  bp_comp     -0.590   -1.024   -0.225           0.00
  gap200      -0.961   -1.272   -0.557           0.00    gap200      -0.612   -0.809   -0.389           0.00
  gap50       -0.144   -0.426    0.167           0.15    gap50       -0.198   -0.362   -0.026           0.01
  vol30        0.045   -0.322    0.464           0.41    vol30        0.148   -0.116    0.387           0.16
  vol_pct     -0.258   -0.630    0.287           0.17    vol_pct     -0.165   -0.493    0.214           0.27
  ldse        -0.136   -0.488    0.133           0.17    ldse        -0.037   -0.351    0.180           0.34
  ret20        0.025   -0.280    0.268           0.45    ret20       -0.035   -0.221    0.108           0.31
  fast_def     0.116   -0.182    0.416           0.22    fast_def     0.107   -0.050    0.266           0.07
  volratio     0.184   -0.175    0.491           0.21    volratio     0.052   -0.164    0.244           0.33
  dgs2_60      0.186   -0.316    0.545           0.29    dgs2_60      0.175   -0.198    0.477           0.23
  breadth-only Q: P at pct 0.1 / 0.5 / 0.9 = 0.30 / 0.22 / 0.15;  C: 0.29 / 0.24 / 0.19
  (raw sd per coefficient unit: gap200 3.3pp, gap50 1.9pp, bp 0.28-0.31, vol30 5.7pp, dgs2_60 0.39pp)
```

Signs. Closer to the 200d -> more likely to break (gap200, the dominant term: -0.96 per 3.3 pp on Q); extreme breadth in *either*
direction -> more likely (bp_sq positive, interval clear of zero on Q; the linear breadth term is negative but its interval spans zero
once the U term is in); weak composite breadth -> more likely (bp_comp -0.59, clear of zero, on Q); further below the 50d (gap50)
weakly more likely. Everything else — level and percentile of vol, the vol ratio, the 20d return, the fast state, days into the
episode — has a sign-flip probability of 0.15-0.45 under episode resampling. **DGS2**: the 60-session change enters positive on both
samples (rising 2y yield -> more breakdowns, +0.19 / +0.18 per 0.39 pp) but with intervals [-0.32, +0.55] / [-0.20, +0.48]; it is
chosen by forward selection in one fold of twenty. It carries no reliable transition information either.

## 6. Decision value through the harness (the test that matters)

Policies driven by the strictly out-of-fold P of section 3 (10-fold grouped; each day's P comes from the fold in which its episode was
held out). `cash > p*`: the D row's QLD leg to cash when P > p*. `w = 1-P`: QLD weight scaled by 1-P. `gate & P>p`: the breadth gate
fires only if also P > p. `gate | P>p`: the gate or P > p. Controls: same-rows live, the plain breadth gate, constant-D at the policy's
deployed capital (`calib_q`); `ep_boot` (D episodes resampled whole, 1000 draws) of the Sharpe difference vs constant-D and vs live.
Real rows: rr's D rows (79) get the daily OOF P at the same d0; reported, not selected on.

```
[Q: QQEW rows 2007-07+] rows 4800; live 26.09% / 1.006 / -33.6% S 1.103 H 0.876 exp 72.1%
  policy                             CAGR/Sh/MDD      S      H    exp   on  | vs live S/H | vs constD S/H | ep-boot Sh CI vs constD  P<=0  | vs live Sh CI  P<=0| real Sh
  breadth gate pct<0.2    31.71% / 1.218 / -28.5%  1.332  1.065  70.0%  124  +0.229/+0.189   +0.205/+0.178        [+0.065,+0.322] 0.000  [+0.088,+0.344] 0.000    1.490
  bucket cash > 0.3       29.53% / 1.177 / -28.8%  1.302  1.007  67.5%  249  +0.200/+0.131   +0.151/+0.115        [+0.004,+0.283] 0.021  [+0.013,+0.341] 0.018    1.430
  bucket cash > 0.4       31.71% / 1.218 / -28.5%  1.332  1.065  70.0%  124  +0.229/+0.189   +0.205/+0.178        [+0.068,+0.316] 0.000  [+0.085,+0.359] 0.000    1.490
  bucket cash > 0.5       30.87% / 1.186 / -28.5%  1.305  1.026  70.4%  100  +0.203/+0.150   +0.183/+0.141        [+0.047,+0.299] 0.000  [+0.053,+0.323] 0.001    1.469
  bucket cash > 0.6       26.09% / 1.012 / -33.6%  1.095  0.900  71.6%   35  -0.007/+0.024   -0.015/+0.021        [-0.033,+0.050] 0.509  [-0.029,+0.053] 0.399    1.248
  bucket w = 1-P          27.63% / 1.121 / -28.8%  1.222  0.986  69.0%  727  +0.120/+0.110   +0.085/+0.094        [+0.037,+0.145] 0.003  [+0.036,+0.196] 0.003    1.349
  breadth cash > 0.3      28.02% / 1.088 / -33.3%  1.160  0.991  70.8%   75  +0.058/+0.115   +0.043/+0.108        [-0.012,+0.167] 0.047  [-0.003,+0.187] 0.032    1.306
  breadth cash > 0.4      26.28% / 1.018 / -33.6%  1.095  0.913  71.6%   34  -0.007/+0.036   -0.014/+0.034        [-0.020,+0.059] 0.392  [-0.014,+0.058] 0.310    1.248
  breadth cash > 0.5/0.6  = live (no day above 0.5)
  breadth w = 1-P         25.53% / 1.054 / -29.8%  1.160  0.912  68.9%  727  +0.057/+0.035   +0.022/+0.019        [+0.002,+0.040] 0.011  [-0.002,+0.094] 0.029    1.291
  breadth+U cash > 0.3    30.21% / 1.173 / -28.5%  1.273  1.041  69.8%  134  +0.171/+0.165   +0.144/+0.154        [+0.029,+0.284] 0.007  [+0.036,+0.329] 0.007    1.442
  breadth+U cash > 0.4    27.32% / 1.060 / -32.4%  1.116  0.984  71.2%   56  +0.014/+0.108   +0.003/+0.102        [-0.028,+0.140] 0.142  [-0.022,+0.144] 0.110    1.240
  breadth+U cash > 0.5    26.52% / 1.028 / -33.6%  1.091  0.942  71.5%   38  -0.011/+0.066   -0.019/+0.063        [-0.029,+0.077] 0.292  [-0.026,+0.086] 0.225    1.233
  breadth+U w = 1-P       26.52% / 1.089 / -28.6%  1.189  0.956  68.8%  727  +0.086/+0.080   +0.050/+0.065        [+0.020,+0.097] 0.000  [+0.018,+0.144] 0.002    1.309
  all-L2 cash > 0.3       28.41% / 1.146 / -29.3%  1.332  0.895  67.9%  225  +0.230/+0.019   +0.185/+0.004        [-0.059,+0.273] 0.115  [-0.026,+0.329] 0.070    1.370
  all-L2 cash > 0.4       28.83% / 1.137 / -26.6%  1.334  0.873  69.4%  151  +0.232/-0.003   +0.202/-0.015        [-0.026,+0.248] 0.049  [-0.007,+0.280] 0.035    1.439
  all-L2 cash > 0.5       28.65% / 1.113 / -26.3%  1.220  0.968  70.4%   98  +0.118/+0.092   +0.098/+0.083        [-0.009,+0.196] 0.040  [+0.005,+0.218] 0.017    1.404
  all-L2 cash > 0.6       28.01% / 1.088 / -27.3%  1.158  0.993  70.9%   69  +0.056/+0.117   +0.041/+0.110        [-0.016,+0.171] 0.052  [-0.015,+0.182] 0.047    1.404
  all-L2 w = 1-P          27.17% / 1.115 / -28.8%  1.241  0.946  68.7%  727  +0.139/+0.069   +0.101/+0.053        [+0.008,+0.167] 0.013  [+0.013,+0.214] 0.013    1.407
  all-L2 gate & P>0.3     29.00% / 1.125 / -29.3%  1.204  1.019  70.4%   97  +0.101/+0.143   +0.082/+0.134        [+0.007,+0.214] 0.017  [+0.020,+0.238] 0.012    1.425
  all-L2 gate & P>0.5     28.52% / 1.099 / -27.2%  1.164  1.010  71.0%   66  +0.062/+0.134   +0.048/+0.128        [-0.009,+0.191] 0.048  [-0.009,+0.207] 0.038    1.369
  all-L2 gate | P>0.6     31.30% / 1.214 / -28.5%  1.336  1.053  69.6%  142  +0.233/+0.177   +0.206/+0.165        [+0.075,+0.322] 0.001  [+0.067,+0.351] 0.002    1.526
  all-L2 gate | P>0.8     31.97% / 1.228 / -28.5%  1.350  1.065  69.9%  127  +0.248/+0.189   +0.223/+0.178        [+0.092,+0.332] 0.001  [+0.096,+0.375] 0.000    1.514
  noGap-L2 cash > 0.3     29.26% / 1.155 / -27.2%  1.297  0.967  69.2%  159  +0.195/+0.090   +0.163/+0.077        [+0.012,+0.251] 0.014  [+0.013,+0.274] 0.011    1.522
  noGap-L2 cash > 0.4     30.31% / 1.171 / -27.7%  1.304  0.995  70.6%   92  +0.202/+0.119   +0.184/+0.110        [+0.025,+0.283] 0.004  [+0.039,+0.312] 0.001    1.427
  noGap-L2 cash > 0.5     28.54% / 1.099 / -28.0%  1.174  0.998  71.2%   56  +0.071/+0.122   +0.060/+0.116        [-0.007,+0.184] 0.041  [+0.003,+0.197] 0.023    1.340
  noGap-L2 cash > 0.6     27.49% / 1.059 / -33.6%  1.143  0.945  71.6%   30  +0.041/+0.068   +0.034/+0.066        [-0.020,+0.129] 0.091  [-0.014,+0.141] 0.081    1.255
  noGap-L2 w = 1-P        27.07% / 1.113 / -28.5%  1.231  0.955  68.8%  727  +0.128/+0.079   +0.092/+0.064        [+0.033,+0.134] 0.000  [+0.036,+0.188] 0.003    1.359
  noGap-L2 gate & P>0.3   29.88% / 1.154 / -27.2%  1.278  0.986  70.5%   93  +0.176/+0.110   +0.158/+0.102        [+0.025,+0.252] 0.008  [+0.036,+0.286] 0.002    1.472
  noGap-L2 gate | P>0.6   = the gate (no un-gated day above 0.6)
  fwd-sel cash > 0.3      26.58% / 1.079 / -34.5%  1.238  0.864  67.7%  239  +0.136/-0.013   +0.089/-0.028        [-0.167,+0.240] 0.309  [-0.139,+0.279] 0.234    1.341
  fwd-sel cash > 0.4      28.40% / 1.126 / -35.6%  1.336  0.840  68.7%  184  +0.234/-0.037   +0.197/-0.053        [-0.092,+0.266] 0.134  [-0.070,+0.316] 0.099    1.378
  fwd-sel cash > 0.5      28.60% / 1.120 / -30.5%  1.265  0.922  69.5%  142  +0.163/+0.046   +0.134/+0.034        [-0.036,+0.237] 0.086  [-0.036,+0.251] 0.069    1.415
  fwd-sel cash > 0.6      28.86% / 1.118 / -30.1%  1.214  0.988  70.3%  102  +0.112/+0.112   +0.091/+0.103        [-0.010,+0.203] 0.036  [+0.002,+0.232] 0.024    1.377
  fwd-sel w = 1-P         27.54% / 1.119 / -28.9%  1.243  0.950  68.7%  727  +0.141/+0.074   +0.103/+0.058        [-0.021,+0.194] 0.057  [-0.004,+0.238] 0.034    1.394
  fwd-sel gate & P>0.3    29.02% / 1.123 / -28.5%  1.195  1.025  70.4%   99  +0.092/+0.149   +0.073/+0.141        [+0.006,+0.217] 0.017  [+0.015,+0.243] 0.010    1.379
  fwd-sel gate | P>0.6    32.27% / 1.247 / -28.5%  1.384  1.067  69.4%  156  +0.281/+0.190   +0.251/+0.178        [+0.098,+0.351] 0.000  [+0.097,+0.382] 0.000    1.500
  fwd-sel gate | P>0.8    32.43% / 1.245 / -28.5%  1.374  1.074  69.8%  133  +0.272/+0.198   +0.245/+0.187        [+0.099,+0.341] 0.000  [+0.105,+0.387] 0.000    1.528
  stump cash > 0.3/0.4    22.39% / 0.937 / -39.1%  1.130  0.673  68.5%  189  +0.027/-0.203   -0.013/-0.218        [-0.312,+0.084] 0.838  [-0.290,+0.135] 0.735    1.267
  stump cash > 0.5        24.06% / 0.962 / -35.3%  1.077  0.804  70.9%   64  -0.025/-0.072   -0.040/-0.079        [-0.205,+0.076] 0.776  [-0.212,+0.101] 0.712    1.211
  stump w = 1-P           24.26% / 1.006 / -31.5%  1.151  0.809  69.2%  727  +0.049/-0.067   +0.016/-0.081        [-0.116,+0.051] 0.716  [-0.092,+0.101] 0.495    1.285
```

```
[C: full proxy rows 2000-07+] rows 6575; live 22.18% / 0.913 / -33.6% S 1.103 H 0.768 exp 67.7%
  policy                             CAGR/Sh/MDD      S      H    exp   on  | vs live S/H | vs constD S/H | ep-boot Sh CI vs constD  P<=0  | vs live Sh CI  P<=0| real Sh
  breadth gate pct<0.2    24.59% / 1.024 / -35.1%  1.345  0.785  65.1%  187  +0.243/+0.017   +0.212/+0.012        [-0.004,+0.199] 0.031  [+0.006,+0.237] 0.019    1.502
  bucket cash > 0.3       23.98% / 1.008 / -35.1%  1.313  0.780  64.5%  231  +0.210/+0.012   +0.172/+0.006        [-0.015,+0.186] 0.066  [-0.013,+0.225] 0.048    1.470
  bucket cash > 0.4       23.58% / 0.985 / -35.1%  1.229  0.801  65.4%  166  +0.127/+0.034   +0.099/+0.029        [-0.026,+0.148] 0.078  [-0.020,+0.173] 0.075    1.377
  bucket cash > 0.5       22.16% / 0.922 / -33.6%  1.163  0.737  66.5%   79  +0.061/-0.031   +0.045/-0.034        [-0.046,+0.045] 0.466  [-0.029,+0.059] 0.335    1.286
  bucket w = 1-P          21.96% / 0.960 / -29.9%  1.204  0.777  64.6%  934  +0.102/+0.009   +0.065/+0.003        [-0.001,+0.061] 0.028  [-0.004,+0.099] 0.035    1.333
  breadth+U cash > 0.3    23.72% / 0.998 / -33.6%  1.308  0.767  64.8%  211  +0.205/-0.001   +0.170/-0.008        [-0.031,+0.180] 0.093  [-0.022,+0.207] 0.072    1.449
  breadth+U w = 1-P       21.84% / 0.956 / -29.8%  1.195  0.777  64.6%  934  +0.093/+0.009   +0.056/+0.002        [+0.004,+0.046] 0.011  [-0.003,+0.091] 0.035    1.321
  all-L2 cash > 0.3       20.35% / 0.894 / -37.5%  1.212  0.655  64.3%  242  +0.110/-0.113   +0.070/-0.119        [-0.181,+0.096] 0.687  [-0.170,+0.136] 0.609    1.371
  all-L2 cash > 0.4       21.98% / 0.931 / -30.0%  1.178  0.746  65.9%  128  +0.076/-0.022   +0.054/-0.026        [-0.079,+0.102] 0.415  [-0.077,+0.117] 0.338    1.375
  all-L2 cash > 0.5       22.59% / 0.938 / -30.1%  1.208  0.734  66.9%   62  +0.106/-0.034   +0.095/-0.037        [-0.032,+0.076] 0.225  [-0.031,+0.078] 0.178    1.351
  all-L2 cash > 0.6       22.76% / 0.936 / -33.6%  1.184  0.749  67.3%   31  +0.081/-0.019   +0.075/-0.020        [-0.014,+0.060] 0.131  [-0.012,+0.065] 0.106    1.309
  all-L2 w = 1-P          21.17% / 0.934 / -31.5%  1.191  0.741  64.6%  934  +0.089/-0.026   +0.052/-0.033        [-0.036,+0.045] 0.433  [-0.035,+0.079] 0.236    1.340
  all-L2 gate & P>0.5     23.09% / 0.952 / -33.6%  1.174  0.784  67.0%   53  +0.072/+0.016   +0.061/+0.014        [+0.002,+0.071] 0.020  [+0.005,+0.078] 0.012    1.351
  all-L2 gate | P>0.6     24.47% / 1.021 / -35.1%  1.345  0.778  65.1%  188  +0.243/+0.010   +0.212/+0.006        [-0.001,+0.199] 0.026  [-0.002,+0.223] 0.026    1.502
  noGap-L2 cash > 0.3     21.03% / 0.906 / -34.1%  1.278  0.634  64.9%  201  +0.176/-0.134   +0.143/-0.139        [-0.143,+0.094] 0.677  [-0.136,+0.131] 0.572    1.412
  noGap-L2 cash > 0.4     23.21% / 0.964 / -33.6%  1.217  0.776  66.5%   90  +0.115/+0.008   +0.099/+0.005        [-0.037,+0.122] 0.154  [-0.035,+0.141] 0.118    1.373
  noGap-L2 w = 1-P        21.32% / 0.939 / -30.9%  1.195  0.749  64.6%  934  +0.092/-0.019   +0.056/-0.025        [-0.022,+0.042] 0.334  [-0.028,+0.081] 0.147    1.320
  fwd-sel cash > 0.3      17.91% / 0.808 / -35.5%  1.133  0.553  63.7%  283  +0.030/-0.215   -0.015/-0.219        [-0.271,+0.014] 0.956  [-0.262,+0.050] 0.901    1.211
  fwd-sel cash > 0.5      22.67% / 0.948 / -29.5%  1.206  0.750  66.1%  118  +0.103/-0.017   +0.083/-0.021        [-0.067,+0.116] 0.284  [-0.057,+0.133] 0.226    1.289
  fwd-sel cash > 0.6      22.81% / 0.947 / -29.8%  1.221  0.737  66.9%   63  +0.119/-0.031   +0.107/-0.034        [-0.037,+0.092] 0.215  [-0.025,+0.106] 0.163    1.298
  fwd-sel w = 1-P         20.60% / 0.910 / -31.7%  1.155  0.722  64.7%  934  +0.052/-0.046   +0.017/-0.053        [-0.087,+0.046] 0.732  [-0.070,+0.077] 0.530    1.295
  fwd-sel gate | P>0.6    24.56% / 1.033 / -30.6%  1.425  0.739  64.7%  221  +0.322/-0.029   +0.286/-0.035        [-0.010,+0.221] 0.046  [-0.008,+0.254] 0.036    1.516
  stump cash > 0.3        16.82% / 0.773 / -39.7%  1.015  0.584  63.2%  320  -0.087/-0.183   -0.138/-0.187        [-0.313,-0.010] 0.988  [-0.298,+0.015] 0.967    1.305
  stump cash > 0.5        21.24% / 0.892 / -29.5%  1.133  0.708  66.8%   64  +0.031/-0.060   +0.019/-0.063        [-0.095,+0.037] 0.795  [-0.088,+0.050] 0.704    1.279
  (the remaining C cells -- breadth cash > 0.4+, breadth+U > 0.4+, and the other combinations -- are in the log; none is better than the rows shown)
```

Per-day diagnostics: does the out-of-fold P separate the QLD leg *within* the gated days and *within* the un-gated days?

```
  [Q]  model     scope     P range         n QLD d1 bp     t  label| fwd20 QQQ %        [C]  model     scope     P range         n QLD d1 bp     t  label| fwd20 QQQ %
       bucket    gated     < med 0.55     60    -116.6 -1.98   0.90        -2.63             bucket    gated     < med 0.45     76     -65.8 -1.38   0.83        -2.23
       bucket    gated     >= med         64     -27.3 -0.63   0.20        -1.24             bucket    gated     >= med        111      -6.0 -0.24   0.18         3.07
       bucket    un-gated  < med 0.07    290      48.5  3.02   0.06         3.94             bucket    un-gated  < med 0.16    371      26.4  1.95   0.28         1.55
       bucket    un-gated  >= med        313      26.7  1.80   0.25         2.47             bucket    un-gated  >= med        376      33.2  2.39   0.10         3.40
       all-L2    gated     < med 0.53     62     -99.7 -1.97   0.50        -2.80             all-L2    gated     < med 0.37     93     -53.5 -1.73   0.41         1.21
       all-L2    gated     >= med         62     -41.3 -0.79   0.58        -1.03             all-L2    gated     >= med         94      -7.3 -0.19   0.48         0.62
       all-L2    gated     > 0.5          66     -47.1 -0.95   0.58        -0.89             all-L2    gated     > 0.5          53     -55.0 -1.06   0.49        -0.04
       all-L2    un-gated  < med 0.13    301      43.1  2.89   0.05         3.68             all-L2    un-gated  < med 0.16    373      21.8  1.65   0.14         2.16
       all-L2    un-gated  >= med        302      31.2  1.97   0.27         2.68             all-L2    un-gated  >= med        374      37.9  2.66   0.24         2.81
       all-L2    un-gated  > 0.5          32     -16.8 -0.28   0.34         1.45             all-L2    un-gated  > 0.5           9     150.4  1.06   0.56         3.24
       noGap-L2  gated     < med 0.44     62     -13.9 -0.33   0.55        -0.18             noGap-L2  gated     < med 0.37     93     -28.3 -0.89   0.49         1.97
       noGap-L2  gated     >= med         62    -127.1 -2.16   0.53        -3.65             noGap-L2  gated     >= med         94     -32.2 -0.86   0.39        -0.13
       noGap-L2  un-gated  > 0.5           9     -12.8 -0.11   0.22         1.08             noGap-L2  un-gated  > 0.5           0
       fwd-sel   gated     < med 0.68     62     -92.0 -1.71   0.52        -2.91             fwd-sel   gated     < med 0.31     93     -51.4 -1.43   0.42        -0.22
       fwd-sel   gated     >= med         62     -49.1 -1.00   0.56        -0.92             fwd-sel   gated     >= med         94      -9.4 -0.28   0.47         2.03
       fwd-sel   un-gated  > 0.5          66      -4.9 -0.13   0.52         2.38             fwd-sel   un-gated  > 0.5          69      21.5  0.60   0.49         2.56
```

Reading, in order of importance.

1. **Nothing beats the plain gate.** On Q the gate is +0.205/+0.178 vs constant-D (S/H). The best threshold policy from the
   all-feature model is `cash > 0.5` at +0.098/+0.083 — half the gate on both eras, with the episode-bootstrap interval touching
   zero ([-0.009, +0.196]); `cash > 0.3/0.4` match the gate on the search era (+0.185/+0.202) and *lose the holdout entirely*
   (+0.004/-0.015): the low thresholds put 151-225 D days in cash, and in 2007-2015 those days were mostly recoveries. The continuous
   `w = 1-P` is +0.101/+0.053. On C every all-feature policy has a negative holdout (-0.02..-0.12) and the bootstrap P(<=0) is
   0.13-0.69. The stump (gap200 < ~4 %) loses -0.2 on the holdout on both samples — the anatomy line's gap200 placebo result again.
2. **The bucket table's OOF P reproduces the gate.** `bucket cash > 0.4` is the gate to the fourth decimal (only the bottom quintile
   exceeds 0.4 in every training fold; the top quintile's 0.20-0.36 never does), and `bucket cash > 0.5` is the gate minus the 24 days
   in folds where the bottom-quintile rate fell below 0.5 (+0.183/+0.141). So the baseline, used as a policy, *is* the candidate rule.
3. **A calibrated P adds nothing on top of the gate.** `all-L2 gate | P > 0.8` adds three days to the gate and +0.018/+0.000 Sharpe;
   `fwd-sel gate | P > 0.6/0.8` adds 9-32 days and +0.05/+0.00 to +0.04/+0.01 (S/H), all inside the gate's own bootstrap interval;
   the same combinations on C add -0.00/-0.01 to +0.08/-0.05. Subtracting gated days by P (`gate & P > 0.3/0.5`) costs -0.10 to
   -0.16 on the search era for +0.00 to -0.04 on the holdout — the model cannot tell the profitable gated days from the unprofitable.
   The per-day table says why: inside the gate the all-feature P is *inversely* related to the money (Q: -100 bp/day below the gated
   median P, -41 above; C: -54 vs -7), because the high-P gated days are the ones already at the 200d, where the break is imminent
   but the next-day loss is smaller than on the days a few percent above it; and outside the gate the days it flags (P > 0.5: 32 on
   Q, 9 on C) return -17 bp/day (t -0.3) and +150 bp/day (t +1.1) respectively — no money the gate misses. `noGap-L2` finds no
   un-gated day above 0.6 at all; its whole policy value (+0.184/+0.110 at 0.4) is a noisier copy of the gate (92 days, 47 gated).
4. **The label is not the money.** The models predict "this episode will end in E" well; the gate's value is the one or two sessions
   before the 200d gives way (anatomy section 1). Knowing an episode will break does not say *when*, and every day spent in cash
   before the break in a D episode that is drifting sideways above the 200d costs the QLD carry. gap200 knows *when* — but only in
   the mechanical sense that the break is close when the price is close, at which point the day's loss is small.

## 7. Today's reading

```
  last proxy row 2026-08-26: state A eff A fast A; QQQ file last 2026-09-04; DGS2 last 2026-09-08 = 4.39
  features at 2026-08-26 (as a hypothetical FIRST D day tomorrow: ldse=0): bp=0.9028, bp_sq=0.1622, bp_comp=0.7758, gap200=0.0875, gap50=-0.0014,
     vol30=0.2166, vol_pct=0.7520, ldse=0, ret20=0.0750, fast_def=0, volratio=0.6003, dgs2_60=0.1400
  [Q] all-L2 P(breakdown) = 0.032  episode-bootstrap 95% [0.004, 0.128] | bucket base rate 0.30 | logit: gap200 -0.91, bp_comp -0.56, ldse +0.26, bp_sq +0.66
  [C] all-L2 P(breakdown) = 0.060  episode-bootstrap 95% [0.021, 0.147] | bucket base rate 0.16 | logit: gap200 -0.63, fast_def -0.22, vol30 +0.06, ldse +0.07

  freshest date with both QQQ and QQEW closes: 2026-09-04: macro state A, fast D, breadth pct 0.867 (comp 0.899)
  features: bp=0.8671, bp_sq=0.1347, bp_comp=0.8988, gap200=0.0931, gap50=0.0111, vol30=0.1978, vol_pct=0.6012, ldse=0, ret20=-0.0056, fast_def=1, volratio=0.6946, dgs2_60=0.2400
  [Q] all-L2 P(breakdown) = 0.026  [0.006, 0.072] | bucket base rate 0.30 | logit: gap200 -1.08, bp_comp -0.80, ldse +0.26, bp_sq +0.45
  [C] all-L2 P(breakdown) = 0.086  [0.037, 0.193] | bucket base rate 0.26 | logit: gap200 -0.73, gap50 -0.34, dgs2_60 +0.10, bp_sq +0.12
```

Today is state A (fast state D since early September, so a D transition tomorrow would be through the macro 50d, not the overlay).
Were tomorrow a first D day with today's features, the model's P(breakdown) is 0.03 (Q) / 0.06-0.09 (C), against 0.30 / 0.16-0.26
from the bucket table (the top-quintile cell). The gap between the two is the U-shaped breadth term (top quintile) pulling up and the
+9 % distance to the 200d pulling down, and the previous section says the bucket's reading is the one with return content. The
interval is an episode bootstrap of the *fit* (parameter uncertainty), not of the outcome.

## 8. Verdict

Does a calibrated multi-feature P(breakdown) beat the one-feature bucket table by enough to matter? **As a probability, yes but
narrowly and for the wrong reason; as a decision input, no.** Grouped-by-episode and time-ordered, the all-feature logistic lowers the
out-of-fold log-loss from 0.51 to 0.44-0.46 on the QQEW rows (AUC 0.67 -> 0.79) and from a useless 0.59 to 0.52 on the 2000-07+
composite rows, and its calibration bins track realized frequency up to P ~ 0.5. But the improvement is the distance to the 200d
(-0.96 per sd, chosen first in 20 of 20 folds); remove gap200/gap50 and the model is no better than the bucket table on either sample.
Vol level, vol percentile, the vol ratio, the 20d return, the fast state, days into the episode and the 60-session change in DGS2 all
have coefficients whose sign flips in 15-45 % of episode-bootstrap refits; DGS2 is positive on both samples (rising 2y -> more breaks)
but inside its interval. Through the harness, no policy built on the out-of-fold P — hard thresholds 0.3-0.6, the continuous 1-P
weight, or the model added to / intersected with the gate — beats the plain `pct < 0.2` gate on both eras; the model's best is half
the gate's Sharpe gain, and its low thresholds lose the whole holdout. The bucket table's own out-of-fold P reproduces the gate exactly
at p* = 0.4. This is a clean null on decision value, and it is the expected one: the label is "the episode ends below the 200d", the
money is "the day it happens", and the features that predict the first (price already near the 200d) do not time the second — the
anatomy line's gap200 placebo gates (-0.25 holdout) said the same. Nothing here changes the earlier recommendation: the breadth gate
stays a *candidate* under its pre-registered forward test, the bucket table (with gap200 as context) is the right owner-facing reading
of a D day, and no model is proposed for application.

Candidate count this line: 7 model classes on 2 samples, hyper-parameters chosen inside training folds (not a sweep); 47 harness
policy cells per sample reported in full, none selected. Cumulative rule count with the earlier lines: 240 (no new rule).
