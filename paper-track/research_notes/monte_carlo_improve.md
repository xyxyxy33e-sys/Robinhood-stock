# Monte Carlo: room to improve the live design? (2026-10-22)

Script: `paper-track/monte_carlo_improve.py`. Full tables: `monte_carlo_improve_run.log`.
Research only. Nothing live changed.

## Method

Seven candidates were fixed before running, each motivated by
`monte_carlo.md` / `monte_carlo_versions.md`. Each is paired against the live
design on the same 1,000 bootstrapped 10-year paths, in 12 cells: proxy,
holdout and real panels, each with mean block lengths of 20, 60, 120 and 250
sessions.

A candidate counts only if, in most of the 12 cells, it has:
- higher Sharpe than live on more than half of the paths; and
- no more than 0.5 pp lower median CAGR.

## Results

"Cells Sharpe-better" is the number of cells where the candidate's Sharpe beats
live on more than half the paths; "cells DD-shallower" is the same for
drawdown. All Δ columns are medians, paired against live on the same paths.

| candidate | cells Sharpe-better | cells DD-shallower | ΔCAGR | ΔMaxDD | Δ rebal/yr | verdict |
|---|---|---|---|---|---|---|
| vol max(10,30) | 12/12 | 12/12 | −1.3 … +0.6 pp | +0.8 … +3.7 pp | +7 | **passes** (see the matched test below) |
| vol target 18% | 12/12 | 12/12 | −1.6 … +0.3 pp | +1.3 … +2.4 pp | +3 | a risk dial |
| vol target 22% | 0/12 | 0/12 | −0.3 … +1.1 pp | −2.0 … −1.1 pp | −2 | a risk dial, worse Sharpe |
| D gate breadth only | 10/12 (by ≤ 0.04) | 0/12 | +0.0 … +1.7 pp | −2.6 … −0.9 pp | 0 | more return for more drawdown; a dial |
| no D gate | 2/12 | 0/12 | −3.5 … +1.6 pp | −6.1 … −1.6 pp | +1 | worse: keep the gate |
| no extension trim | 1/12 | 0/12 | −3.7 … +7.2 pp | −11.1 … −7.2 pp | +2 | much worse: keep the trim |
| vol max + breadth gate | 11/12 | 8/12 | −0.9 … +1.5 pp | −1.3 … +2.5 pp | +8 | the two effects cancel |

## Is max(10,30) just less exposure?

Partly. At 20%, the max(10,30) estimator holds about as much exposure as the
plain 30d estimator at an 18.2–18.6% target. Against that exposure-matched
control it still wins in all 12 cells, but by less:

- Sharpe higher on 54–68% of paths (ΔSharpe +0.002 … +0.016)
- MaxDD shallower on 50–78% of paths (Δ +0.0 … +1.5 pp; p5 MaxDD +0.3 … +2.1 pp)
- CAGR change −0.2 … +0.4 pp

The residual edge is largest when trends are short (L20), where the design
is weakest. So roughly two-thirds of the headline benefit is the lower risk
level and one-third is timing: it de-levers faster in the first days of a
volatility spike.

## Execution lag

One session of lag (decide at close t, trade at close t+1) costs the live
design 0.2–3.1 pp of median CAGR and lowers Sharpe in every cell. The
max(10,30) candidate keeps its advantage under the same lag: it beats
lagged live in 12/12 cells on both Sharpe and drawdown. That answers the
2026-09-09 worry that the estimator is the more lag-sensitive of the two.

## Recommendations (for the owner)

1. **Re-enabling max(10,30) is the one change the Monte Carlo supports.**
   - It is a flag flip: `VOL_ESTIMATOR_MAX_ENABLED`.
   - The gain is modest but consistent across all 12 cells, and it holds
     out of sample and under lag.
   - Costs: ~7–8 more rebalances a year, and up to −1.3 pp median CAGR in
     long-trend worlds. The recovery-window cost from the 09-09 study still
     applies.
2. **Execution timing matters more than any indicator.** Same-session
   fills are worth up to 3 pp a year, so the 15:50 run and its
   missed-run fallback are worth protecting.
3. **Keep the D gate and the extension trim.** Removing either is clearly
   worse off the tuned path.
4. **Leverage is a separate choice.** The vol target, the A split and the
   breadth-only gate move along the risk/return line rather than improving
   it. Choose them for the drawdown you can live with.
5. **No candidate fixes the short-trend weakness.** When trends last about a
   month, every variant still trails buy-and-hold QQQ.
