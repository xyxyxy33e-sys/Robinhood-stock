# Holding SPMO longer through state shifts (2026-10-29)

Owner question: "hold SPMO longer during a state shift, considering drift costs and others". Research only;
nothing live changed. Script `spmo_hold_study.py` (pre-registered in its docstring), output `spmo_hold_study_run.log`.
Live design, VIXM left out of every arm, each arm at 4 bp and 20 bp per side.

| arm | real Sharpe 4bp / 20bp | proxy Sharpe 4bp / 20bp | holdout Sharpe | real max DD | SPMO sell days/yr | verdict |
|---|---|---|---|---|---|---|
| live design | 1.831 / 1.623 | 1.306 / 1.111 | 0.973 | −18.4% | 15.8 | — |
| delay SPMO cut 5 days | 1.732 / 1.547 | 1.197 / 1.030 | 0.862 | −19.1% | 18.0 | fail |
| delay SPMO cut 10 days | 1.657 / 1.489 | 1.148 / 0.999 | 0.813 | −23.2% | 16.6 | fail |
| delay SPMO cut 20 days | 1.679 / 1.528 | 1.145 / 1.015 | 0.798 | −24.0% | 15.8 | fail |
| cut SPMO only if >15 pp | 1.820 / 1.618 | 1.299 / 1.110 | 0.975 | −17.9% | 7.2 | fail (near tie) |

Delaying the SPMO cut after a state shift is clearly worse (−0.10 to −0.18 Sharpe, bootstrap P 0.96–1.00, drawdowns
up to 8 pp deeper). The state shift is the risk signal, and staying in SPMO after it is exactly the exposure the
strategy is built to drop. Higher costs do not rescue it: the gap narrows at 20 bp but stays large.
Hysteresis (only cut SPMO when the cut is over 15 pp) is a statistical tie with live: Sharpe −0.011 / −0.006, holdout
+0.002, shallower max DD, and it halves SPMO sell days (15.8 → 7.2 a year). It misses the pre-registered bar by a
hair, so no change; it is the one variant worth revisiting if wash sales or short-term-gain tax lots become a
concern, since SPMO dollar turnover only falls about 8%.
