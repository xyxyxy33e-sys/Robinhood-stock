# Drift band width on the 2026-11-23 design (2026-11-21, owner question; not adopted)
`run.py`: harness_live live design (deep-E -6/-4 band held through F, VIX-panic, VIXY 35%, 2.0x cap), data to 2026-11-20,
MC.run_strategy band 2/3/4/5/7%, cost 2bp and 5bp.
Real 2bp: 2% 50.9% / 2.084 (70 trades/yr), 3% 50.8 / 2.082 (57), 4% 50.9 / 2.083 (50), **5% 51.0 / 2.088 (46)**, 7% 50.9 / 2.082 (43);
max DD -16.8% for all. Proxy 2bp: Sharpe 1.475-1.481, 5% best (42 trades/yr vs 64 at 2%). 5bp and ex-2020: same ranking.
Flat; a tighter band adds ~25 trades a year (and wash-sale chances) for nothing. Keep 5%.
