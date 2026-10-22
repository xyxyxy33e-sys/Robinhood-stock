# Monte Carlo improvement candidates, round 2 (2026-10-22)

Script: `paper-track/monte_carlo_improve_r2.py`. Full tables: `monte_carlo_improve_r2_run.log`.
Research only. Nothing live changed.

## Method

Three candidates were fixed before running. Each is paired against the
2026-10-22 live design (max(10d, 30d) vol) on 1,000 bootstrapped 10-year
paths. There are 12 cells: proxy, holdout and real panels, each with mean
blocks of 20, 60, 120 and 250 sessions. The pass rule is the same as in
round 1.

## Results

| candidate | cells Sharpe-better | cells DD-shallower | ΔCAGR | ΔMaxDD | Δ rebalances/yr | verdict |
|---|---|---|---|---|---|---|
| book-vol target (scales each row by its own leverage), leverage-matched | 0/12 | 8/12 | −2.2 … −0.3 pp | −1.0 … +0.8 pp | −1 | **worse**: reject |
| D2 at the D1 row (100–150d zone at 1.5x, not 2.5x) | 5/12 | 12/12 | −3.5 … +0.1 pp | +0.3 … +1.3 pp | 0 | a risk dial: less drawdown for less return |
| drift band 10% (from 5%) | 9/12 (by ≤ 0.007) | 10/12 | −0.1 … +0.3 pp | −0.0 … +0.1 pp | **−7.6** | **performance-neutral, ~17% fewer trades** |

## Reading

1. **The book-vol target loses even at matched leverage.** The design gains
   from holding its leverage in calm, confirmed trends (A, D3). Scaling 2.5x
   rows harder moves that leverage into the 1–1.5x rows, where it earns
   less. Treating the vol target as "QQQ vol" rather than "book vol" is
   correct as it stands.
2. **D2 at 1.5x is a dial, not an edge.** It gives a shallower drawdown in
   every cell, but costs up to 3.5 pp a year in long-trend worlds. It
   belongs with the A split and the vol target as a risk choice.
3. **A 10% band is the one free improvement, and it is operational, not
   performance.** About 7–8 fewer rebalances a year (~44 → ~37) for
   statistically nothing in return, Sharpe or drawdown. Regime changes,
   trim-vote changes, the D gate and the ladder zone still always trade.
   Only drift trades go. The value is fewer taxable lots, fewer wash-sale
   collisions and fewer fills to get wrong. The cost is that weights can
   drift up to 10% L1 from target between regime trades.
