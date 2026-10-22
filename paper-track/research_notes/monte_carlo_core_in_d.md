# Keep the core through state D: re-run on the 2026-10-22 design (2026-10-22)

Script: `paper-track/monte_carlo_core_in_d.py`. Full tables: `monte_carlo_core_in_d_run.log`.
Research only. Nothing live changed.

## Question

The 2026-09-06 whole-strategy review found that keeping the core through D
was worth about +3.6 pp/yr after tax at a top bracket, because D then sold
100% of the core and bought it back weeks later. The D rows have changed
since (the ladder). This tests two candidates, fixed before running, each at
the same leverage per zone:

- **(a)** D2 0/50/50 TQQQ/QLD (2.5x) → **25/75 SPMO/TQQQ** (2.5x)
- **(b)** as (a), and D1 50/50 SPMO/QLD (1.5x) → **75/25 SPMO/TQQQ** (1.5x)

## Results

| | live | (a) | (b) |
|---|---|---|---|
| core sell-outs per year (median over cells) | 6.0–7.0 | 3.8–6.0 | 3.8–6.0 |
| pre-tax: cells Sharpe-better / DD-shallower | — | 5/12 / 12/12 | 12/12 / 12/12 |
| pre-tax ΔCAGR | — | −0.3 … +0.0 pp | −0.2 … +0.1 pp |
| pre-tax ΔMaxDD | — | +0.0 … +0.1 pp | +0.0 … +0.2 pp |
| real-ETF cells only: P(Sharpe better) | — | 29–50% | 57–64% |
| historical real 2015-11..2026-08 | 48.8% / 1.864 / −19.0% | 48.4% / 1.856 / −19.1% | 48.5% / 1.862 / −18.7% |
| after tax, top bracket, ΔCAGR vs live | — | −0.2 … +0.1 pp | +0.1 … +0.2 pp |
| after tax, middle bracket, ΔCAGR vs live | — | −0.2 … +0.0 pp | 0.0 … +0.2 pp |

## Reading

1. **The 09-06 tax edge is gone, because the design that caused it is gone.**
   - In September, D held 85–100% QLD with no core, and A held 50% core.
   - Today A holds only 25% core and the D ladder already keeps some core
     in D1 and D3.
   - Most realised gains now come from the TQQQ leg and the exits to cash
     (D gate, E, F, the extension trim), which no D row can change.
   - Holding the core through D cuts core sell-outs from about 6 to 4–6 a
     year, but is worth only ≤ 0.2 pp a year after tax.
2. **(b) is a harmless micro-refinement, not an improvement worth trading.**
   - On the proxy it wins every cell, but by a mechanical fee effect: 25%
     TQQQ costs less in expense ratio than 50% QLD for the same 1.5x. The
     proxy's core is QQQ, so it cannot see the SPMO difference.
   - On real ETFs it is a near-tie: Sharpe better on 57–64% of paths,
     slightly shallower drawdown, −0.2 to 0.0 pp of return.
3. **(a) alone is slightly worse on real ETFs.** It puts more TQQQ, rather
   than QLD, into the deepest-volatility D zone.

**Verdict:** no change. Neither candidate moves the design by more than
model noise, before or after tax.
