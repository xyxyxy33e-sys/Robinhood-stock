# Sharpe search over every knob (2026-10-30)

Owner: "try to maximize sharpe, allow to tweak anything". Research only. Script `sharpe_search.py` (pre-registered); output `sharpe_search_run.log`.

**Method.**
- Coordinate descent, two passes, over 13 knobs and 65 configs.
- Objective: proxy 2001–2015 Sharpe, the era no live parameter was fit in.
- Validation, judged once on the winner: real ETFs 2015–2026 with VIXM.

**Winner, changes from live:**
- A 40/60 → 75/25
- B 75/25 → 100% SPMO
- C 100% SPMO → 75/25
- D1 50 SPMO/50 QLD → 100% SPMO
- D2 50 TQQQ/50 QLD → 100% TQQQ
- vol estimator max(10,30) → 30d
- band 5% → 3%

| | real 4 bp | real 20 bp | proxy 2001–2026 | search window 2001–2015 |
|---|---|---|---|---|
| live | 47.2% / 1.959 / −18.4% | 40.7% / 1.743 / −19.1% | 30.7% / 1.321 / −22.2% | 21.2% / 0.988 / −22.2% |
| winner | 39.8% / 1.933 / −17.7% | 33.6% / 1.688 / −18.4% | 28.4% / 1.376 / −23.4% | 21.2% / 1.086 / −22.1% |

**Verdict: keep live.**
- The +0.10 Sharpe found in the search window does not carry over. On real ETFs the winner loses Sharpe (−0.026 at 4 bp, −0.055 at 20 bp) and 7 pp of CAGR. Bootstrap P(not better) is 0.60.
- The search found the pre-2015, QQQ-core era rewarding lower leverage in A/B/D1. The SPMO era rewards the opposite. The live design sits between the two optima.
- **Structural knobs that won in both passes, by a wide margin:** D gate (on: 1.08 vs 0.87), trim v2 (1.08 vs 0.97), fast re-entry (1.08 vs 0.98), zone buffer 0.5% (1.08 vs 1.04–1.07), vol target 20% (the peak of 15–30%). These are the parts of the design that are robust across eras.
