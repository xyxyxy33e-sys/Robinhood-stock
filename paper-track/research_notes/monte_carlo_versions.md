# Monte Carlo of past releases: does an earlier version do better? (2026-10-22)

Script: `paper-track/monte_carlo_versions.py`, built on `monte_carlo.py`.
Full tables: `research_notes/monte_carlo_versions_run.log`. Research only.
Nothing live changed.

## Method

Every release in STRATEGY.md's change log since 2026-09-02 is run on the
**same** 1,000 bootstrapped 10-year paths as the live design. Because the
paths are shared, every comparison is paired: "P(CAGR > live)" is the share
of paths where that release finished ahead of the live design on the same
path. The generator, panels and engine are the ones in `monte_carlo.md`.
Older releases add the XLU leg in state E (+3%/yr yield), the v1 graded
trim, no D gate, the max(10,30) vol estimator and the 3% band where they
had them.

Each release was first checked on the single historical path. Proxy figures
start 2000-07; the real-ETF window is 2015-11..2026-08.

| release | proxy, this engine | proxy, STRATEGY.md | real, this engine | real, STRATEGY.md |
|---|---|---|---|---|
| 2026-09-02 | 15.7% / 0.752 / −32.4% | 15.7% / 0.752 / −32.4% | 22.3% / 0.987 / −28.1% | 23.2% / 1.061 / −26.7% (weekly harness) |
| 2026-09-07 | 22.1% / 0.938 / −32.8% | 22.1% / 0.938 / −32.8% (BRIEFING.md) | 29.8% / 1.206 / −29.4% | n/a |
| 2026-09-09 | 22.2% / 0.914 / −33.6% | 22.2% / 0.913 / −33.6% | 29.8% / 1.150 / −32.8% | 29.7% / 1.145 / −32.9% |
| 2026-09-19 | 25.9% / 1.091 / −27.0% | 25.5% / 1.071 / −27.0% | 37.4% / 1.478 / −18.6% | 37.3% / 1.475 / −18.6% |
| 2026-09-23 A 50/50 | 26.6% / 1.218 / −21.7% | 26.1% / 1.194 / −21.9% | 41.2% / 1.801 / −17.8% | 41.0% / 1.797 / −17.8% |
| 2026-09-23 A 40/60 | 28.3% / 1.221 / −22.5% | 27.8% / 1.199 / −22.6% | 44.4% / 1.810 / −18.7% | 44.2% / 1.804 / −18.7% |
| 2026-10-09 live | 32.3% / 1.269 / −26.6% | 32.7% / 1.275 / −27.7% (from 2001) | 50.9% / 1.879 / −19.2% | 54.7% / 1.977 / −19.4% (with VIXM) |

## Result

The central case is the 26-year proxy with 60–120-day blocks. The paired
columns compare each release with the live design on the same paths.

| release | median CAGR L60 / L120 | median Sharpe L60 / L120 | median MaxDD L60 / L120 | P(CAGR > live) L60 / L120 | P(MaxDD shallower than live) L60 / L120 |
|---|---|---|---|---|---|
| 2026-09-02 | 11.2% / 12.5% | 0.56 / 0.61 | −40.7% / −38.8% | 35% / 15% | 57% / 50% |
| 2026-09-07 | 13.6% / 15.8% | 0.64 / 0.72 | −41.1% / −38.3% | 48% / 31% | 58% / 49% |
| 2026-09-09 | 13.4% / 15.6% | 0.61 / 0.69 | −44.2% / −41.1% | 45% / 32% | 43% / 37% |
| 2026-09-19 | 13.0% / 16.6% | 0.62 / 0.76 | −41.2% / −37.1% | 45% / 32% | 67% / 65% |
| 2026-09-23 A 50/50 | 12.4% / 16.0% | 0.64 / 0.80 | −37.6% / −33.7% | 24% / 9% | 96% / 96% |
| 2026-09-23 A 40/60 | 12.9% / 17.0% | 0.64 / 0.79 | −39.4% / −35.3% | 30% / 13% | 93% / 92% |
| **2026-10-09 live** | **13.8% / 18.5%** | **0.63 / 0.81** | **−43.0% / −37.8%** | — | — |
| live without D ladder | 13.5% / 18.2% | 0.63 / 0.79 | −42.6% / −37.8% | 47% / 36% | 56% / 56% |
| QQQ buy-and-hold | 10.8% / 10.4% | 0.53 / 0.52 | −49.7% / −51.6% | 34% / 11% | 37% / 25% |

## Reading

1. **No earlier release beats the live design in the central case.** At
   L60–L250, live has the highest median CAGR on every panel. Its Sharpe is
   tied for best at L60 and best or within 0.01 at L120+.
2. **The 2026-09-23 A 50/50 release is the same strategy with less risk.** In
   every one of the 12 panel × block cells, its drawdown is shallower than
   live's on 94–97% of paths (median −37.6% vs −43.0% at proxy L60). Its
   Sharpe is within about ±0.05, and its median CAGR is 1.4–7 pp lower. This
   matches STRATEGY.md's finding that the A split is a leverage dial.
   Choosing between them is a risk-appetite question, not an edge question.
3. **When trends are short (L20), the older, simpler releases do better than
   live:** 09-07 beats live on 63–67% of paths. But every release still loses
   to plain QQQ there.
4. **On the 2000–2015 holdout at L60, 09-07 is slightly ahead** (7.6% vs 6.8%
   median CAGR; ahead on 58% of paths). 09-07 came before the D gate, the E
   change and trim v2, all of which were justified mainly on SPMO-era
   evidence. At L120+ live catches up.
5. **The D ladder adds little.** It is +0.3–1 pp median CAGR at long blocks
   and nothing at short ones.

## Follow-up: the reverted max(10,30) vol estimator

09-07 beat 09-09 in nearly every cell. The two differ only in the vol
estimator and the drift band, so both were tested on the live design:

| live + … | cells where drawdown is shallower than live on ≥ 83% of paths | P(Sharpe > live) | median CAGR change | rebalances/yr |
|---|---|---|---|---|
| max(10,30) vol | 9 of 9 (83–93%) | 65–73% | −0.5 to +0.5 pp | ~45 vs ~37 |
| 3% band | 0 of 9 (54–62%) | 30–82%, no consistent direction | ±0.1 pp | — |

(Cells: proxy, holdout and real × L20/60/120.) The estimator, not the band,
is what helped. It wins on the 2000–2015 holdout too (drawdown shallower on
83–93% of paths, Sharpe higher on 69–73%). That answers part of the
2026-09-09 reason for reverting it, "its entire edge is COVID 2020": the
holdout panel contains no 2020.

Still standing:
- the extra ~8 rebalances a year;
- the recovery-window cost the revert study measured;
- its higher sensitivity to execution lag, which is not modelled here.

This is a candidate for the owner, not a change.

## Caveats

As in `monte_carlo.md`: no VIXM, taxes or deposits. Long blocks re-sample
the years the releases were tuned on, and every release after 09-02 was
tuned partly on the same history, so the paired gaps between releases are
small against that tuning.
