# Holding SPMO more consistently (2026-10-29)

Owner question: "test if holding spmo more consistently is beneficial". Research only; nothing live changed.
Script `paper-track/spmo_consistency_study.py` (pre-registered in its docstring before the run); full output in
`spmo_consistency_study_run.log`. Engine `monte_carlo.py` on the live design, VIXM left out of every arm.

| arm | real CAGR / Sharpe / max DD | proxy Sharpe / max DD | holdout Sharpe | verdict |
|---|---|---|---|---|
| live design | 43.5% / 1.831 / −18.4% | 1.306 / −24.6% | 0.973 | — |
| E/F 50% SPMO | 43.7% / 1.822 / −20.7% | 1.275 / −24.3% | 0.915 | fail |
| E/F 100% SPMO | 44.0% / 1.781 / −23.9% | 1.205 / −37.4% | 0.824 | fail |
| E/F + gated D 50% SPMO | 42.5% / 1.775 / −21.8% | 1.246 / −25.3% | 0.904 | fail |
| SPMO floor 30% everywhere | 39.9% / 1.761 / −19.3% | 1.245 / −24.1% | 0.914 | fail |
| trim keeps SPMO at base | 43.3% / 1.812 / −18.4% | 1.295 / −24.6% | 0.974 | fail |

No arm passes. Every arm lowers Sharpe on both panels. Holding SPMO in E/F adds a little CAGR on real ETFs
(at most +0.5 pp) but deepens max drawdown by 2–5 pp and costs 0.06–0.15 holdout Sharpe. The 30% floor is
the only arm the bootstrap separates from live, and it is worse (P 0.98 real, 1.00 proxy). Keeping SPMO through
trim votes is a near-tie (−0.02 / −0.01 Sharpe), so there is no case to change it.
Conclusion: keep the live design. The cash and leverage legs that replace SPMO in E/F and D2/D3 earn their place.
