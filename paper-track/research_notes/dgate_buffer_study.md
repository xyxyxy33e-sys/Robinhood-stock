# D-gate buffer zone (hysteresis) — 2026-09-30

Owner: "run the gate buffer test", after the February 2026 D-gate flip-flop
(gate QLD <-> BOXX four times in three weeks). Script
`paper-track/dgate_buffer_study.py`, log `dgate_buffer_study_run.log`.
Hook: `fall_protection_study.GATE_G_EXIT` / `GATE_B_EXIT` (None = live gate,
asserted to reproduce the live design exactly).

## Pre-registered (before the run, not edited after)

Live design (trim v2 + whipsaw carry 3) with one change: the gate's ON
threshold is unchanged, its OFF threshold moves.
Arms: gap200 off at >= 2.5% / 3% / 4% (on below 2%); breadth off at >= 0.25
(on below 0.20). Primary base 40/60. PASS needs, vs live: P1 real Sharpe >=,
P2 proxy Sharpe >=, P3 proxy holdout Sharpe >=, P4 MaxDD <= 0.5 pp deeper on
both harnesses, P5 gate switches inside D down >= 25% (proxy).

## Result — no arm passes; the live gate stays

| arm (40/60) | real Sharpe | proxy Sharpe | holdout Sh | proxy MaxDD | flips (proxy) | verdict |
|---|---|---|---|---|---|---|
| live | 1.804 | 1.199 | 0.834 | −22.6% | 97 | — |
| gap200 off 2.5% | +0.009 | −0.034 | −0.067 | **−29.0%** | 93 | fail |
| gap200 off 3% | −0.014 | −0.064 | −0.102 | −28.3% | 83 | fail |
| gap200 off 4% | −0.016 | −0.048 | −0.074 | −27.4% | 65 | fail |
| breadth off 0.25 | **+0.019** | **+0.015** | **+0.014** | −22.6% | 84 | fail (P5 only) |

- **A buffer on the 200-day half is harmful**: it holds cash after QQQ has
  moved back above its 200-day, which is the rebound — proxy drawdown 5–6 pp
  deeper and every Sharpe lower. Same lesson as "wider D gates sell after the
  fall": the gap200 line should switch off promptly.
- **The breadth buffer is no-harm and slightly better on every Sharpe**
  (bootstrap P(not better) 0.10 real / 0.03 proxy; February 2026 −3.4% vs
  −5.7% at 40/60), but it cut flips by only 13%, short of the pre-registered
  25%, so it FAILS as registered. It is also one of four arms tested, so its
  edge is discounted for multiple testing.
- **Correction to the February explanation**: February's flips were driven by
  the BREADTH half (pct crossing 0.20: 11–12 Feb, 20–24 Feb), not the 200-day
  half — QQQ was 3–6% above its 200-day all month.

Nothing applied. Owner decides whether the breadth buffer merits a paper
shadow track.
