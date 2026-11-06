# VIXM sleeve follow-ups, 2026-11-04 .. 11-05 (owner questions) — research record, no design change

All runs: live design, real ETFs 2015-11..2026-10 (VIXM 75% of the cash leg while `allowed`), 2bp one way,
engine `monte_carlo.py`. Scripts here were run from the session scratchpad with `MC.DATA` pointed at a copy of
`data/` extended with `data/live_closes.csv` (`ext_data2.py`); paths inside them are that scratchpad's.
Every log is the verbatim output.

| Question | Script / log | Answer |
|---|---|---|
| Scale the VIXM share (vol, VIX level, VIX/VIX3M, spell age) instead of a fixed 75%? | `vixm_scale` | No. Best edge vs a fixed share at the same average +0.35 CAGR pts / +0.01 Sharpe; more VIXM is simply better in-sample (25% → 100% monotone) |
| VIXY instead of VIXM? | `vixy_test` | VIXY moves 2.0x VIXM. VIXY 35% of cash ≈ VIXM 75%: 54.5% / 1.932 vs 54.3% / 1.931. Same result, ~20x the volume, higher decay (-47%/yr held vs -12%) |
| VXX? (common window 2018-01..) | `vxx_test` | Same index as VIXY (daily corr 0.987, -0.06bp/day); ETN = Barclays credit risk + issuance-halt risk (Mar 2022). Prefer VIXY |
| VIXM + VIXY blends, hedge size, step rules | `blend_test` | Mix at equal hedge: tie. Bigger hedge adds ~+1.3 CAGR pts / +0.03 Sharpe per 0.25 VIXM-units, bootstrap P(not better) 0.06-0.26. Step rules flip with small changes: noise |
| Buffer on the 20% stress floor | `stress_band` | No. Flips 58 → 52-54 over 11y, results within ±0.15 pts; 2-3 close confirmation -0.1..-0.5; floor 18-19% -0.7..-1.0 |
| Exit rules (ratio 0.95..1.10, 2 closes, partial, fade 15..35%, VIXM trail, time stop) | `exit_test` | No change. Later exits ride Aug-2024 / Mar-2025 and lose in the first half; 5-session half-sell the only both-halves positive (+1.39, P 0.22) — watch only |
| Out of sample 2008-01..2015-10 (real VIXM 2011+, CFE-built mid-term proxy before) | `hist_build`, `hist_test` | Sleeve on 2.3% of sessions, 7 spells, -0.05 pts/yr: the latch (VIX < 18 and contango) kept it out of 2008/2010/2011. Cannot confirm or refute the edge |
| Holding period / win rate | `hold`, `winrate` | 29 spells, mean 7.9 sessions, median 4; 55% of spells win, avg win +2.26 vs loss -0.77 pts of the book (2.9x); top 3 spells ≈ 60% of the gain |
| 2026 YTD through 2026-11-05 | `ytd1105` | A 40/60 +19.4% (2026 max DD -16.8%) vs A 20/80 +19.5% (-19.1%); QQQ +5.4%. Led to the owner's A 40/60 from 2026-11-06 |

Decision record: STRATEGY.md "Known limitations" — VIXM liquidity watch; switch to VIXY 35% of the cash leg if a
VIXM exit fill slips >~15bp vs the model or leaves shares unfilled, or once the account passes ~$1M.
First exit test (2026-11-05): 33,996 VIXM sold in one fill at the bid on a one-cent spread; the tracker's +51bp is
vs the close (post-order drift), not liquidity.
