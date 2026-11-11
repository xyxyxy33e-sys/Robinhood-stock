# Soften-the-cliffs test (review 2026-11-11)

Script: `soften_cliffs_test.py`. Its docstring holds the pre-registration and was not edited after the run. Verbatim output: `soften_cliffs_test_run.log`. This is research only. No state or live file was changed.

**Checks before scoring.** The (1%, MA50, 2%) signal variant matches `MC.signals` exactly. The live arm matches `harness.run` on all three periods. S1 equals live on every session that is not D.

## Arms
- **S1, soft gate.** On a D day where the breadth half of the gate does not fire, the row is `(1-f)·ungated D row + f·cash`, with `f = clip((0.04-gap200)/0.04, 0, 1)`. When breadth pct < 0.20, the row still goes 100% to cash.
- **S2, ensemble.** The row is the mean of the 5-leg targets over buffer {0.5, 1, 1.5}% x macro short MA {40, 50, 60}. The buffer applies to both the macro and the fast classifier.
- **S3.** S1 applied inside S2.
- **Rebalance key.** All arms use the live variant's key. Any other movement trades only through the 5% band and the stub rule.

## Sharpe (mean/sd) at 2 bp. Ex-cash Sharpe, CAGR and max DD are in the log.

| arm | real L0 | real L1 | proxy L0 | proxy L1 | hold L0 | hold L1 | min | median | trades/yr |
|---|---|---|---|---|---|---|---|---|---|
| live | 2.068 | 1.835 | 1.425 | 1.254 | 1.096 | 0.951 | 0.951 | 1.340 | 45-50 |
| S1 | 2.031 | 1.797 | 1.390 | 1.249 | 1.059 | **0.973** | **0.973** | 1.319 | 51-55 |
| S2 | 2.023 | 1.770 | 1.344 | 1.167 | 0.985 | 0.855 | 0.855 | 1.255 | 62-64 |
| S3 | 1.983 | 1.729 | 1.305 | 1.162 | 0.944 | 0.880 | 0.880 | 1.234 | 67-71 |

The results at 10 bp follow the same pattern. Live's min/median is 0.851/1.238. S1 scores 0.874/1.217. S2 and S3 fail.

## Verdict (pre-registered rule, 2 bp)
- **S1: MORE ROBUST, but only just.** Its min is +0.022 above live's and its median is -0.020 below it. The higher minimum comes from one cell, holdout with lag 1. S1 is lower than live in the other 5 of 6 cells, and it trades about 5 more times a year. Real CAGR is about 2 points lower.
- **S2 and S3: not more robust.** They are lower in every cell, and their medians are 0.08 to 0.11 below live's.

## Sensitivity map (2 bp, lag 0)
Values are Sharpe for real / proxy / holdout. The centre is T=2%, b=1%, MA50. The spread is the max minus the min over the 3x3 grid of gate threshold T and buffer b. The last column is how far the centre sits above the mean of its 8 neighbours.

| | real spread | proxy spread | holdout spread | centre minus neighbours |
|---|---|---|---|---|
| live | 0.237 | 0.252 | 0.338 | +0.13 to +0.14 |
| S3 | 0.080 | 0.120 | 0.171 | +0.02 |

- **Live has a sharp peak.** It sits on all three parameters: T, b and macro MA (40/60 give about -0.10 on every period). This confirms the reviewer's finding.
- **S3's surface is 2 to 3 times flatter,** and its centre is no longer a lone peak. Its worst grid point on holdout is 0.850, against 0.800 for live.
- **S3's level roughly equals the mean of live's neighbourhood.** On proxy, S3 scores 1.305 and the mean of live's neighbours is about 1.30. S3 gives up the peak premium in exchange for flatness.

## Reading
- **On these data, smoothing does not raise the worst case** beyond S1's marginal pass.
- **The cost of smoothing is the size of live's peak premium,** about 0.1 Sharpe. If that premium is overfit, S3 is about what live should be expected to deliver out of sample, and live's backtest figures are overstated by about 0.1 Sharpe.
- **S1 is the only arm that passes.** Its edge rests on a single cell, so it is weak evidence and not a case to switch.
