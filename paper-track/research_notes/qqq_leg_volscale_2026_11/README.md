# Vol-scaling the QQQ legs (deep-E, VIX-panic) - research only, 2026-11

Script: run.py (in-memory patch of HL.build; freed weight stays in the cash leg). Log: run.log.
Multiplier = min(1, 0.20/vol), vol = sg['vol'][0] (max of 10d/30d), NaN -> 1. Deep-E hold-through-F as live.
Variant 7 (QQQ legs alone target 20%) is identical to 2 in practice and skipped. Variant 8 = 30% target.
Baseline reproduces: real 51.3 / 2.09 / -16.5; proxy 34.3 / 1.48 / -22.1.

## Results (CAGR % / Sharpe / maxDD % / vol % / trades per yr | ex-2020 CAGR / Sharpe)
REAL (2015-26)
| variant | CAGR | Sh | maxDD | vol | tr/yr | ex20 CAGR | ex20 Sh |
|---|---|---|---|---|---|---|---|
| 1 baseline | 51.3 | 2.093 | -16.5 | 20.8 | 47.2 | 49.9 | 2.039 |
| 2 both full | 48.7 | 2.082 | -16.5 | 20.0 | 48.3 | 49.2 | 2.047 |
| 3 deep-E only | 49.5 | 2.080 | -16.5 | 20.3 | 47.8 | 49.6 | 2.050 |
| 4 panic only | 50.6 | 2.106 | -16.5 | 20.4 | 48.0 | 49.5 | 2.040 |
| 5 both sqrt | 49.7 | 2.092 | -16.5 | 20.3 | 47.8 | 49.5 | 2.046 |
| 6 both floor .5 | 49.3 | 2.094 | -16.5 | 20.1 | 48.2 | 49.2 | 2.047 |
| 8 both 30% tgt | 49.6 | 2.083 | -16.5 | 20.4 | 48.3 | 49.7 | 2.042 |

PROXY (2001-26)
| variant | CAGR | Sh | maxDD | vol | tr/yr | ex20 CAGR | ex20 Sh |
|---|---|---|---|---|---|---|---|
| 1 baseline | 34.3 | 1.484 | -22.1 | 21.4 | 43.4 | 33.1 | 1.438 |
| 2 both full | 32.9 | 1.469 | -19.9 | 20.8 | 44.2 | 32.3 | 1.436 |
| 3 deep-E only | 33.5 | 1.469 | -22.1 | 21.2 | 43.9 | 32.8 | 1.436 |
| 4 panic only | 33.7 | 1.488 | -19.9 | 21.0 | 43.8 | 32.6 | 1.439 |
| 5 both sqrt | 33.4 | 1.476 | -20.3 | 21.0 | 43.7 | 32.6 | 1.437 |
| 6 both floor .5 | 33.1 | 1.477 | -19.9 | 20.9 | 44.0 | 32.4 | 1.438 |
| 8 both 30% tgt | 33.4 | 1.475 | -20.4 | 21.1 | 44.1 | 32.7 | 1.438 |

## Per-year difference vs baseline, key years (pts; real has no 2008)
| variant | real 2020 | real 2022 | real 2026 | proxy 2008 | proxy 2020 | proxy 2022 | proxy 2026 |
|---|---|---|---|---|---|---|---|
| 2 both full | -21.0 | -2.1 | +1.3 | +2.9 | -21.6 | -1.9 | +1.3 |
| 3 deep-E | -17.1 | -0.7 | +1.3 | -0.4 | -17.5 | -0.6 | +1.3 |
| 4 panic | -4.3 | -1.4 | 0.0 | +3.3 | -4.5 | -1.3 | 0.0 |
| 5 sqrt | -13.9 | -1.1 | +0.7 | +1.0 | -13.9 | -1.0 | +0.7 |
| 6 floor | -14.9 | -2.0 | +1.3 | +2.6 | -15.3 | -1.8 | +1.3 |
| 8 30% | -16.5 | -0.6 | +0.1 | +1.8 | -16.8 | -0.6 | +0.1 |
(Baseline years: real 2020 +65.7, 2022 +2.9, 2026 +28.2; proxy 2008 0.0, 2020 +69.0, 2022 -5.7, 2026 +32.3.)
Other years differing >0.5 pt (mostly -0.7 to -2.5, e.g. 2018, 2025, 2016; proxy 2001 -7.4 for variants 2/4) are in run.log.

## Bar
Sharpe >= baseline on BOTH panels, maxDD not worse on either, and ex-2020 Sharpe >= baseline ex-2020.

## Verdict
Only variant 4 (scale VIX-panic leg only) technically passes: Sharpe 2.106 vs 2.093 (real), 1.488 vs 1.484 (proxy), maxDD equal on real and better on proxy (-19.9 vs -22.1, from 2008 +3.3 and a 2001 effect), ex-2020 Sharpe 2.040/1.439 vs 2.039/1.438. But the margins are within noise (+0.004 proxy Sharpe, +0.001 ex-2020) and it costs about 0.6-0.7 pt CAGR; the drawdown gain on proxy comes from a handful of episodes, and the real-panel max DD is unchanged. Scaling the deep-E leg (3, 2, 5, 6, 8) fails: Sharpe falls on at least one panel and CAGR drops 1.4-2.6 pts, almost all from 2020 (-14 to -21 pts), exactly the rebound-capture edge; deep-E scaling also never improves maxDD on the real panel. Vol is brought to ~20% in-sample only by giving up return, so Sharpe does not improve. Conclusion: no variant is a clear win; the full-scaling idea is rejected; panic-only is a marginal, low-confidence pass that I would not change live on this evidence alone.
