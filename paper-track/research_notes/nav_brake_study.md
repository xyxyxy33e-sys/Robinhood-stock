# Drawdown-from-high exit rule on the current design — 2026-10-08

Owner: "Should there be an exit rule on when dip is how far off from the all time
high" → "re-run it on the current design". Script `paper-track/nav_brake_study.py`,
log `nav_brake_study_run.log`. Hooks: `fall_protection_study.NAV_BRAKE` / `LEV_SCALE`
(default off; asserted to reproduce the current design exactly).

## Pre-registered (before the run, not edited after)

Current design: trim v2 + 3-session whipsaw carry, D gate, E cash, 30d vol target,
5% band. Brake: when the strategy NAV closes more than DEPTH below its peak, risky
legs × MULT on that close. 24 arms = DEPTH 5/10/15/20% × MULT 0.5 / cash × release
(`nav` back above the line; `high20` new 20-session QQQ closing high; `roll252` rolling
252-session peak, the funding-tier definition). Primary base 40/60. Null: flat
de-levering of the same design. PASS needs P1 drawdown edge vs the null ≥ +1.0 pp on
both harnesses, P2 excess Sharpe ≥ live on both, P3 proxy 2000–2015 holdout ≥ live.
The VIXM sleeve is not in the harness (its data start 2011).

## Result — no arm passes; no exit rule

| (40/60) | real CAGR / MaxDD | proxy CAGR / MaxDD | edge real / proxy | ΔSharpe real / proxy |
|---|---|---|---|---|
| live | 44.2% / −18.7% | 27.8% / −22.6% | — | — |
| −5% → ×0.5, nav | 30.9 / −15.0 | 18.2 / −15.5 | −1.5 / −0.7 | −0.17 / −0.10 |
| −10% → ×0.5, roll252 (best real) | 38.8 / −16.0 | 20.5 / −25.0 | +0.6 / −8.2 | −0.08 / −0.13 |
| −10% → cash, nav | 9.7 / −14.0 | 1.8 / −13.2 | −6.3 / −3.7 | −1.02 / −1.10 |
| −5% → cash, high20 (best proxy) | 8.4 / −9.1 | 3.9 / −7.4 | −1.4 / +2.1 | −0.98 / −0.78 |
| −20% (any) | unchanged (never fires: real MaxDD −18.7%) | 26.1 / −23.1 | 0 / −1.8 | 0 / −0.05 |

- **Every arm lowers Sharpe on both harnesses**, and none beats simply holding less
  leverage on both. The best real-instrument edge is +0.6 pp; the same arm is −8.2 pp
  on the proxy.
- **Cash brakes are ruinous**: they sell near the bottom and, released on NAV recovery,
  sit in BOXX through the rebound (real CAGR 44% → 5–30%).
- **The rolling-252 peak makes it worse, not better**: the brake releases after a year
  and re-fires on the next leg down, so proxy drawdowns get *deeper* (−25% to −33%).
- **A −20% line never fires on real instruments** — the design's own worst drawdown is
  −18.7% — and on the proxy it fires late enough to only add cost.
- Same conclusion as the 2026-09-20 study on the 19 Sep design: a rule that reacts to
  realized loss is late by construction. The state machine, the vol target and trim v2
  already do the de-risking; the drawdown tiers stay funding (buy) signals.

Nothing applied. The only lever that buys drawdown cleanly is less leverage throughout
(on the frontier above, about 0.4 pp of MaxDD per pp of CAGR real and 0.8 pp proxy).
