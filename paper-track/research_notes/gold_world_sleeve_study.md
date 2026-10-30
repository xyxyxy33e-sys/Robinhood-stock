# alphaAI "Gold Rush" and "World Tour" replicas, and as 20% sleeves (2026-10-30)

**Setup.** Research only. Script `gold_world_sleeve_study.py` (pre-registered); output `gold_world_sleeve_study_run.log`.
- **alphaAI's figures:** both monthly tables stop at Feb 2026, and the year tabs start in 2021. Gold Rush shows max DD −33.8% and Sharpe 0.86.
- **Replicas** are built from the published rules. The World Tour overlay is unpublished; the stand-in moves a top-5 market's weight to cash when it is below its 200-day EMA.

| 4 bp | CAGR / Sharpe / max DD | benchmark |
|---|---|---|
| Gold Rush replica 2010-12..2026-10 | 6.0% / 0.40 / −39.3% | hold GLD 6.5% / 0.46 / −45.6% |
| World Tour replica 2013-01..2026-10 | 4.5% / 0.32 / −37.2% (1.4% / 0.17 at 20 bp) | hold EEM 4.6% / 0.32 / −39.8% |
| SPY 2013-01..2026-10 | 14.7% / 0.91 / −33.7% | |

**Replica years.**
- Gold Rush: 2025 +86%, 2024 +15%, 2020 +27%, but 2014 −13% and 2022 −12%.
- World Tour: 2022 −30%, 2015 −15%, 2018 −14%; 2026 +33% so far.

Both match their underlying asset class and add nothing over buy-and-hold. alphaAI's Gold Rush Sharpe of 0.86 comes from a window that starts in 2021 and ends in Feb 2026, which covers gold's 2024–2025 run.

**20% sleeve next to the live design, 2015-11..2026-10** (monthly back to 80/20):

| | 4 bp | 20 bp | daily corr with live |
|---|---|---|---|
| 100% live | 44.0% / 1.849 / −18.4% | 38.2% / 1.653 / −19.1% | |
| 80/20 with gold | 37.3% / 1.880 / −16.9% | 32.8% / 1.690 / −18.8% | +0.11 |
| 80/20 with world | 36.0% / 1.729 / −17.6% | 30.8% / 1.520 / −20.3% | +0.42 |

**Verdict.**
- **Gold sleeve passes the rule.** Sharpe +0.03 / +0.04 and a 1.5 pp shallower max DD, because gold barely correlates with the design. It costs 6.7 pp of CAGR a year, so it is a risk dial, not an improvement.
  - This repeats the 2026-08/09 finding: gold was blended in on 31 Aug and removed by the owner on 1 Sep, a preference decision rather than a backtest finding.
  - Plain GLD would do the same job as the RSI rotation; the replica does not beat holding GLD.
- **World sleeve fails.**
