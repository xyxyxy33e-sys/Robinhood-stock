# Review items 2, 5, 6, 8 (2026-11-11)

Research only. Script `review_tests_2568.py` (pre-registered); output `review_tests_2568_run.log`.
Base: the 11 Nov live design incl. VIXM, deep-E, VIX-panic and the zone buffer, 2 bp per side (`harness.py`).

## 2. Restated expectations (report only)

| | Sharpe (mean/sd) | Sharpe net of cash | CAGR | max DD | with 1 session lag |
|---|---|---|---|---|---|
| real 2015-11..2026-11 | 2.07 | 1.96 | 53.6% | −18.3% | 46.2% / 1.84 (net 1.73) / −20.8% |
| proxy 2001-2026 | 1.43 | 1.34 | 34.8% | −22.1% | 29.7% / 1.25 / −28.6% |
| holdout 2001-2015 | 1.10 | 1.03 | 24.7% | −22.1% | 20.7% / 0.95 / −27.2% |

**Bootstrap, 10-year paths** (2,000 paths, 20-session blocks):

| | median max DD | 5th-percentile max DD | Sharpe 5th / 95th pct |
|---|---|---|---|
| real | −22% | −32% | 1.57 / 2.58 |
| proxy | −26% | −39% | 0.93 / 1.90 |

**Live vs the replayed design.** Live NAV since 31 Aug is −4.2% (to 10 Nov). The 11 Nov design replayed over the same days gives −1.9%. That replay is not the design that was live each day.

## 5. VIXM sleeve size — no cap passes

| arm (real) | CAGR / Sharpe / max DD | dSh |
|---|---|---|
| live, VIXM 75% of cash | 53.6% / 2.068 / −18.3% | — |
| VIXM capped at 25% of NAV | 51.2% / 2.015 / −19.4% | −0.053 |
| VIXM 25% of cash | 50.6% / 1.989 / −19.4% | −0.079 |
| VIXY 35% of cash | 53.1% / 2.055 / −18.3% | −0.012 |
| no sleeve | 49.2% / 1.940 / −20.9% | −0.128 |

- The account's worst day (−7.4%) and worst 5 days (−14.4%) are equity days with no VIXM held. A cap cannot improve them, so every arm fails the "cuts the tail" condition.
- VIXM sat above 25% of NAV on only 3.8% of days.
- The reviewer's concern (a −15% VIXM day while VIXM is 75% of NAV) is a forward risk the 2015–2026 record never produced. The data can neither confirm nor refute it.
- VIXY at 35% of cash is the near-free alternative: −0.012 Sharpe, and VIXY trades at about 100× VIXM's volume.

## 6. Gross exposure cap 2.0x — no arm passes the pre-registered bar

| arm | real | proxy | bootstrap median 10y max DD real / proxy |
|---|---|---|---|
| live | 53.6% / 2.068 / −18.3% | 34.8% / 1.425 / −22.1% | −21.4% / −25.2% |
| G-scale (any row above 2.0x scaled to 2.0x) | 49.5% / 2.070 / −16.5% | 31.9% / 1.410 / −22.1% | −19.9% / −23.7% |
| G-ladder (D2, D3 → 50/50 SPMO/TQQQ) | 49.5% / 2.021 / −17.4% | 32.4% / 1.385 / −22.1% | −21.2% / −25.0% |
| both | 47.6% / 2.043 / −16.2% | 31.1% / 1.397 / −22.1% | −19.8% / −23.7% |

- **G-scale is nearly free on Sharpe** (+0.003 real, −0.015 proxy). It costs 3–4 pp of CAGR and cuts the real max DD by 1.8 pp. Its bootstrap median drawdown improves by only 1.4–1.5 pp, short of the 3 pp bar.
- G-scale is a risk dial, like the A split, not an improvement.
- **Instantaneous loss on a −12% / −20% QQQ day:**

| row | exposure | −12% day | −20% day |
|---|---|---|---|
| A 40/60 | 2.2x | −26% | −44% |
| D2 | 2.5x | −30% | −50% |
| D3 | 3.0x | −36% | −60% |
| any row under the 2.0x cap | 2.0x | −24% | −40% |

## 8. Execution

| | real | proxy |
|---|---|---|
| close (backtest; the 15:50 run approximates it) | 53.6% / 2.068 / −18.3% | 34.8% / 1.425 / −22.1% |
| half at the close, half the next session | 50.4% / 2.004 / −18.5% | 32.5% / 1.363 / −23.3% |
| one session late | 46.2% / 1.835 / −20.8% | 29.7% / 1.254 / −28.6% |

- **Timing is the most sensitive input found.** A full session of delay costs 0.23 / 0.17 Sharpe and adds 6.5 pp to the proxy drawdown.
- Market-on-close orders match what the backtest assumes. Anything that pushes execution to the next day (a missed run, a failed fill) is costly.
- **Circuit breaker** (cash for 5 sessions after a QQQ day of −4/−5/−6%): rejected. It does not help, because the damage is done on the crash day itself and the sessions after a −5% day tend to rebound.
