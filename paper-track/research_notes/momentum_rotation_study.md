# alphaAI-style momentum rotation: top 6 of 9 ETFs (2026-10-30)

**Rules as published:**
- Universe: SPY, QQQ, VGT, MGK, VUG, IWF, MTUM, QUAL, SOXX.
- Holdings: the top 6 by 12-month momentum, weighted by relative trend strength.
- Rebalanced monthly. An unpublished "m7 AI" overlay sets cash across 4 states.

Research only. Script `momentum_rotation_study.py` (pre-registered); output `momentum_rotation_study_run.log`. Yahoo total-return data. The overlay is stood in for by this repo's QQQ state: 50% cash in gated D / E, 100% in F.

| 4 bp | 2015-11..2026-10 | 2005-03..2026-10 |
|---|---|---|
| top 6, equal weight | 18.9% / 0.893 / −35.0% | 13.8% / 0.718 / −52.6% |
| top 6, momentum-weighted | 20.6% / 0.918 / −34.8% | 14.1% / 0.712 / −54.0% |
| + state overlay | 21.0% / 1.093 / −23.9% | 15.2% / 0.909 / −28.0% |
| hold QQQ | 19.0% / 0.898 / −35.1% | 15.5% / 0.773 / −53.4% |
| hold SPMO | 18.1% / 0.915 / −30.9% | — |
| **live design (for scale)** | **44.4% / 1.865 / −18.4%** | — |

**Findings.**
- **The rotation on its own is QQQ with extra trading.** It adds about 1.5 pp a year since 2015, trails QQQ since 2005 (14.1% vs 15.5%), and has the same −54% drawdown in 2008. The SOXX / growth tilt does the work in 2019–2026.
- **The cash overlay is what helps.** It cuts the long-run drawdown to −28% and lifts Sharpe to 0.91 — the same lesson as this repo's own state machine.
- **Core swap: fail.** As the core of the live design in place of SPMO, it gives −0.095 Sharpe at 4 bp (−0.091 at 20 bp) and a 2.5 pp deeper drawdown. SPMO's lower correlation with the TQQQ sleeve again beats a more tech-heavy core.
- **2026 does not reconcile.** The replica makes +35.0% (+30.0% with the overlay). alphaAI's page shows +69.8% YTD, which equals SOXX alone (+70.9%), and its Aug/Sep/Oct (−4.0 / +9.8 / +2.5) match neither SOXX (+1.2 / +11.3 / −9.6) nor the replica (+2.3 / +6.9 / −6.0). The page's figures cannot come from an unleveraged top-6 portfolio of this universe in 2026. They are another year, use leverage, or follow different rules than published.
