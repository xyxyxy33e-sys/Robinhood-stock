# Pre-committed scale-down / stop rules (2026-11-19) — `stop_rules.py`, `stop_rules_run.log`

Overlay on the full-size current design (MC engine: no VIXY sleeve, no QQQ cash legs), 500 x 10y paths.
- DD40 half (halve at a -40% strategy drawdown, back to full above -20%): fires on 21-51% of 10-year paths;
  costs 0.0-0.8 pp median CAGR; 5th-pct max DD -56 -> -49 (holdout L60), -55 -> -49 (proxy L60),
  -49 -> -45 / -46 (L120), -61 -> -54 with a crash. Never fired in history (worst -21%).
- DD30 half: deeper tail cut (5th pct -46%) but fires on 61-84% of paths and costs 0.4-1.3 pp median CAGR.
- DD30 out (to cash until a new high): costs 2-3 pp median CAGR; 5th-pct CAGR worse.
- DD50 permanent stop: no median benefit, worse 5th-pct CAGR (locks in the loss). Not recommended.
- REL25 (12-month gap to QQQ > 25 pp): fires on 93-98% of paths; useless as a trigger.
None improves the 5th-pct CAGR materially: these rules buy a shallower worst drawdown, not more money.
