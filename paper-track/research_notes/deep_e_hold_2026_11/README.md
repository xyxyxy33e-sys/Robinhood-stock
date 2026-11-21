# Deep-E exit variants (2026-11-21)

Owner question: deep-E sells when the state turns E -> F; what if it is held through F?
All runs: `harness_live.run_live(track, vixy_source='old')`, the live design (2.0x cap, VIXY 35%, A 40/60, D ladder,
VIX-panic), data to 2026-11-20 (VIX/VIX3M for 11-20 from the live 15:50 reading, as `dashboard_years.py` does).
Variants are swapped into `harness_live.build` in memory; nothing live was touched by the scripts.
NOTE: since the adoption, harness_live's default IS "hold through F", so re-running these scripts reproduces the
figures only for the variants they set explicitly (on_off.py now compares hold-through-F on/off deep-E).

| Variant | real 2015-11..2026-11 | proxy 2001..2026 |
|---|---|---|
| deep-E off | 47.6% / 2.04 / -16.5% | 32.3% / 1.44 / -22.1% |
| live until 2026-11-20: sell at F or at the -5% recovery line | 50.9% / 2.09 / -16.5% | 34.1% / 1.48 / -22.1% |
| **hold through F, keep the -5% exit (ADOPTED, live 2026-11-23)** | **51.3% / 2.09 / -16.5%** | **34.3% / 1.48 / -22.1%** |
| also enter in F | 50.9% / 2.03 / -17.7% | 32.2% / 1.32 / -38.5% |
| hold until the state leaves E/F (no -5% exit) | 49.8% / 2.02 / -18.3% | 33.8% / 1.46 / -22.1% |

Hold through F vs live, pts by year: real 2016 +0.7, 2022 +0.7, 2025 +1.4; proxy 2003 +2.0, 2006 +1.7, 2008 -0.1,
2016 +0.6, 2022 +0.6, 2025 +1.3. It binds on a handful of spells: too few to call evidence; adopted as an owner decision
("basically 0 cost") with that stated.
Enter in F: 2001 -24.5, 2002 -16.3, 2008 -11.3 pts (proxy). Hold until D: real 2020 -14.7, 2022 -2.2, 2025 -3.1, 2018 +6.9.
The -5% line over the next months: the 200-day sheds Feb-May 2026 closes (~$613 average), so the line stays ~$645-650 for
~40-60 sessions even with QQQ flat at $580-610; it drops under the 2026-11-20 average cost ($634.47) only after ~54-87 sessions.
