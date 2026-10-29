# D1/D2 flip-flops: zone buffer study (2026-10-29)

Trigger: 16–29 Oct 2026 the live account moved A→D2, then D2→D1→D2→D1→D2 as QQQ sat on its 100-day average.
Each flip swaps ~40% of the account between SPMO and TQQQ. Owner: hold SPMO longer through a shift (not E/F).
Research only; nothing live changed. Script `d_zone_buffer_study.py` (pre-registered), output `d_zone_buffer_study_run.log`.
VIXM left out of every arm. The engine reproduces the live zone path of those two weeks exactly.

| arm | real Sharpe 4/20bp | proxy Sharpe 4/20bp | holdout | max DD real / proxy | zone changes/yr (real) | 15–29 Oct | verdict |
|---|---|---|---|---|---|---|---|
| live | 1.831 / 1.623 | 1.306 / 1.111 | 0.973 | −18.4 / −24.6 | 6.2 | −0.90% | — |
| buffer ±0.5% | 1.849 / 1.653 | 1.321 / 1.138 | 0.988 | −18.4 / −22.2 | 4.3 | −0.81% | PASS (not significant) |
| buffer ±1% | 1.813 / 1.630 | 1.305 / 1.131 | 0.986 | −17.7 / −22.6 | 2.4 | −4.65% | fail |
| buffer ±2% | 1.740 / 1.566 | 1.272 / 1.105 | 0.973 | −17.7 / −22.6 | 0.6 | −4.65% | fail |
| stay D1 to −1% (SPMO-favouring) | 1.806 / 1.610 | 1.302 / 1.117 | 0.985 | −18.4 / −24.6 | 3.9 | −0.90% | fail |
| stay D1 to −2% (SPMO-favouring) | 1.758 / 1.567 | 1.270 / 1.091 | 0.961 | −18.4 / −24.6 | 2.5 | −0.90% | fail |
| 3-close confirmation | 1.749 / 1.571 | 1.278 / 1.105 | 0.979 | −17.5 / −21.9 | 1.0 | −4.65% | fail |

- Holding SPMO longer (stay in D1 until QQQ is 1–2% under its 100d) does not pay: it loses Sharpe on real ETFs at
  both costs. Below the 100d line, D2's TQQQ/QLD has done better than D1's SPMO/QLD.
- Wider buffers and confirmation delays cut churn but keep D2 too long on the way back up; over 15–29 Oct they would
  have lost −4.65% vs −0.90%, because they would have stayed in TQQQ the whole time.
- A ±0.5% buffer on both lines passes every pre-registered rule (Sharpe +0.016 to +0.030, proxy max DD 2.5 pp shallower,
  a third fewer zone changes) but the gain is small and the bootstrap does not separate it from live (P 0.23 / 0.12),
  and it is the best of six arms. Adopting it needs the live code to remember yesterday's zone.
- The flips of these two weeks cost little in the model (−0.90% at 4 bp, −1.57% at 20 bp over the window); most of it
  was market move, not churn.
