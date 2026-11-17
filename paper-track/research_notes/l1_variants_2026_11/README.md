# Is there a better version of L1? (2026-11-17) - research only, nothing adopted

Files: `PLAN.md` (arms, metrics, reading rule; written before any arm ran), `events.py` -> `events.log`, `events_real.csv`, `events_proxy2001.csv`, `spells_*.csv` (Step 1),
`run.py` -> `run.log` (Steps 2-3, 200 placebo draws), `common.py`, `tables.md`, `qqq_event_day_1550_highs.csv` + `qqq_daily_lows_robinhood_2026_09_11.csv` (fetched data, source in the files).
Engine: `harness_live.py` untouched; complete highs (full-day highs to 2026-11-10, live 15:50 highs after). Windows: real 2015-11-03.., proxy 2001-01-03.., proxy 2010-01-05.., real-ex = real ended 2026-10-23 (drops 2026-10-26..11-16). All end 2026-11-16 otherwise.

## Bottom line
**Keep L1 off is the conclusion under the pre-registered rule: no variant passes, and the original L1 fails it on complete data.** The only thing that separates the arms on the real track is whether they open on 2026-10-30 / 11-02 / 11-04; the
real-window Sharpe differences are decided by about three spells and are within bootstrap noise in most cases. This is a statement about the evidence, not that L1 is proven harmful: with the 2026-10-26..11-16 stretch removed, L1 is +0.059 Sharpe over C0 on real.

## Step 1: L1 events (full-day highs; `events.log`)
- Event = macro-D session, breadth gate open, close gap < 2% (gate shut on close) and high gap >= 2% (L1 opens). **Real: 19 sessions in 15 spells. Proxy 2001: 49 sessions in 37 spells** (3 more events in 2000 sit before the window).
  Typical event: close 0.2-2.0% above the 200-day, high 2.0-5.6% above, close 0.2-3.9% under the high, VIX 12-39, D3/D2 rows at gross 1.3-2.1x; spells are 1-2 sessions (books re-align the next session or two).
- **Total effect (L1 minus C0), sum of daily return differences: real -2.75 pp (NAV ratio -3.3%), proxy 2001 +22.3 pp (+23.4%).** Per-spell (non-overlapping) sums: real -2.74 pp, proxy +22.77 pp.
- **Concentration: one spell.** Real spells (15): best 1 / 3 / 5 = +5.67 / +13.25 / +19.29 pp, worst 1 / 3 / 5 = -19.57 / -26.16 / -28.73; 9 up, 6 down; **without the single worst spell (2026-11-04) the total is +16.8 pp, without the best one -8.4 pp.**
  Proxy (37): best 1/3/5 = +5.67 / +14.36 / +22.04, worst 1/3/5 = -19.95 / -26.40 / -31.32; 26 up, 11 down; ex-worst1 +42.7 pp, ex-best1 +17.1 pp. The 2026 events (10-30, 11-02, 11-04, 11-11) are in both lists.
  Per-event mean next-session difference: real -0.14 pp (12/19 positive), proxy +0.45 pp (34/49); 5- and 20-session differences overlap neighbouring events.
- **2026-11-04**: D3, breadth pct 0.38, close +1.67% / high +3.07% over the 200-day, close 1.4% under the high, VIX 16.6, L1 put on gross 2.00x. Next session L1's book -9.17%, C0's +10.39% (C0 sat in cash with the VIXY sleeve, which jumped on the -6.4% QQQ day):
  a **-19.6 pp** one-session difference, the worst spell on both tracks (real -19.57, proxy -19.95). The same spell family (10-30 -1.6, 11-02 +1.2) nets to -20.0 pp across 10-30..11-04.
- The sample is small; positives on the older proxy years (2005 cluster: 13 sessions, mostly D2 at low VIX) are real rows but one regime.

## Step 2: highs up to 15:50
AlphaVantage intraday is a premium endpoint (refused). Robinhood `get_equity_historicals` (5- and 30-minute bars) returns data for 2026 but only flat interpolated bars for 2025 and earlier (probed 2025-02-27, 2025-03-05, 2025-06-02). So **only 5 of the 19 real event days could be checked** (2026-03-06, 10-30, 11-02, 11-04; 11-11 is the live 15:50 value already); 14 real events and all 30 proxy-only events remain full-day highs.
| day | gap on full-day high | gap on 15:50 high | close gap | opens at 15:50? |
|---|---|---|---|---|
| 2026-03-06 | 2.918% | 2.916% | 1.856% | yes (full-day 606.00 vs 605.99 through 15:50) |
| 2026-10-30 | 2.812% | 2.711% | 1.614% | yes (698.63 daily vs 697.94 in regular bars; peak in the first half hour) |
| 2026-11-02 | 2.885% | 2.885% | 0.187% | yes (peak 699.43 at ~10:00) |
| 2026-11-04 | 3.070% | 3.070% | 1.674% | yes (701.45 at 10:15 ET, hours before 15:50) |
| 2026-11-11 | 2.007% | 2.007% | 1.271% | yes (live; clears by 0.007 pp) |
In every checkable case the day's high printed in the morning, so full-day = 15:50 high to within 0.1 pp; the grid with these substitutions (second block of `run.log`) is numerically identical to the full-day grid at the printed precision. This is five days only: it says nothing about whether the 14 older events would survive a 15:50 cut. Note 2026-11-04 would have opened live at 15:50 with the high long since printed, so the -19.6 pp spell is not a full-day-high artefact.

## Step 3: arm table (full-day highs). Cell = CAGR % / Sharpe / max DD % / worst-20-session %
(`HC0.0` is identical to L1: macro D already implies the close is above the 200-day. Second table: worst day / worst 5 / sessions with a gate opening C0 does not have / average target gross.)

| arm | real: CAGR / Sharpe / DD / worst-20 | proxy 2001 | proxy 2010 | real ex 10-26..11-16 |
|---|---|---|---|---|
| C0 | 51.1 / 2.100 / -16.5 / -16.5 | 34.0 / 1.480 / -22.1 / -18.3 | 43.9 / 1.739 / -20.1 / -16.3 | 49.8 / 2.090 / -15.9 / -14.8 |
| L1 | 50.6 / 2.064 / -25.4 / -23.6 | 35.1 / 1.505 / -24.9 / -23.2 | 45.2 / 1.762 / -24.9 / -23.2 | 52.4 / 2.149 / -16.6 / -15.5 |
| H2.5 | 50.7 / 2.077 / -25.4 / -23.6 | 34.7 / 1.495 / -24.9 / -23.2 | 44.7 / 1.755 / -24.9 / -23.2 | 52.3 / 2.159 / -14.8 / -13.0 |
| H3.0 | 50.0 / 2.058 / -24.2 / -22.3 | 33.5 / 1.459 / -23.7 / -21.9 | 43.5 / 1.721 / -23.7 / -21.9 | 51.4 / 2.131 / -14.8 / -13.0 |
| H4.0 | 52.6 / 2.136 / -16.5 / -16.5 | 34.6 / 1.497 / -22.1 / -18.3 | 44.9 / 1.764 / -20.1 / -16.3 | 51.3 / 2.127 / -14.8 / -13.0 |
| HC0.0 | 50.6 / 2.064 / -25.4 / -23.6 | 35.1 / 1.505 / -24.9 / -23.2 | 45.2 / 1.762 / -24.9 / -23.2 | 52.4 / 2.149 / -16.6 / -15.5 |
| HC0.5 | 50.8 / 2.073 / -26.3 / -24.5 | 35.3 / 1.512 / -25.8 / -24.1 | 45.3 / 1.767 / -25.8 / -24.1 | 52.8 / 2.163 / -16.6 / -15.5 |
| HC1.0 | 49.6 / 2.043 / -26.3 / -24.5 | 34.7 / 1.495 / -25.8 / -24.1 | 44.2 / 1.739 / -25.8 / -24.1 | 51.5 / 2.134 / -18.8 / -17.7 |
| HC1.5 | 49.6 / 2.041 / -26.3 / -24.5 | 34.0 / 1.473 / -25.8 / -24.1 | 43.2 / 1.712 / -25.8 / -24.1 | 51.3 / 2.128 / -18.2 / -17.1 |
| R0.5 | 50.7 / 2.081 / -20.6 / -19.6 | 34.0 / 1.478 / -22.1 / -20.6 | 43.8 / 1.733 / -21.6 / -20.6 | 49.5 / 2.070 / -20.6 / -19.6 |
| R1.0 | 50.6 / 2.077 / -20.6 / -19.6 | 34.5 / 1.491 / -22.1 / -20.6 | 44.0 / 1.737 / -21.6 / -20.6 | 49.5 / 2.070 / -20.6 / -19.6 |
| R1.5 | 48.2 / 1.999 / -26.3 / -24.5 | 33.7 / 1.461 / -25.8 / -24.1 | 42.7 / 1.696 / -25.8 / -24.1 | 50.1 / 2.089 / -20.6 / -19.6 |
| TP3 | 53.7 / 2.172 / -16.5 / -16.5 | 34.9 / 1.506 / -22.1 / -19.8 | 45.7 / 1.789 / -20.1 / -16.3 | 52.4 / 2.164 / -14.8 / -13.0 |
| TP2 | 50.1 / 2.050 / -26.3 / -24.5 | 34.4 / 1.485 / -25.8 / -24.1 | 44.1 / 1.731 / -25.8 / -24.1 | 51.9 / 2.136 / -18.8 / -17.7 |
| P2 | 53.0 / 2.137 / -18.8 / -18.3 | 35.8 / 1.531 / -22.1 / -19.8 | 46.1 / 1.792 / -20.1 / -17.2 | 51.9 / 2.137 / -16.6 / -15.5 |
| HALF | 51.1 / 2.114 / -17.8 / -17.2 | 34.8 / 1.507 / -22.1 / -19.1 | 44.8 / 1.771 / -20.1 / -16.3 | 51.4 / 2.135 / -15.7 / -14.6 |
| VIXF | 48.0 / 1.995 / -24.2 / -22.3 | 33.6 / 1.460 / -23.7 / -21.9 | 42.6 / 1.691 / -23.7 / -21.9 | 49.5 / 2.070 / -20.6 / -19.6 |
| VIXFa | 48.7 / 2.026 / -24.2 / -22.3 | 33.7 / 1.468 / -23.7 / -21.9 | 42.8 / 1.702 / -23.7 / -21.9 | 50.2 / 2.103 / -15.9 / -14.8 |
| VIXopp | 53.8 / 2.168 / -18.8 / -18.3 | 35.5 / 1.524 / -22.1 / -19.8 | 46.5 / 1.810 / -20.1 / -17.2 | 52.7 / 2.169 / -14.8 / -13.0 |
| OPEN-ONLY | 49.5 / 2.045 / -23.3 / -21.4 | 33.9 / 1.472 / -22.8 / -21.0 | 43.7 / 1.726 / -22.8 / -21.0 | 50.8 / 2.117 / -15.9 / -13.0 |
| CLOSE-ONLY | 53.0 / 2.141 / -18.8 / -18.3 | 35.4 / 1.522 / -22.1 / -19.8 | 45.4 / 1.775 / -20.1 / -17.2 | 52.0 / 2.141 / -16.6 / -15.5 |

| arm | real: worst day / worst 5 / L1-only sessions / avg gross | proxy 2001 | proxy 2010 | real ex |
|---|---|---|---|---|
| C0 | -7.0 / -13.1 / 0 / 1.130 | -8.3 / -13.7 / 0 / 1.054 | -7.0 / -13.7 / 0 / 1.214 | -6.7 / -13.1 / 0 / 1.133 |
| L1 | -9.2 / -16.8 / 19 / 1.143 | -9.6 / -17.2 / 49 / 1.068 | -9.6 / -17.2 / 30 / 1.227 | -6.7 / -13.1 / 15 / 1.143 |
| H2.5 | -9.2 / -16.8 / 15 / 1.140 | -9.6 / -17.2 / 33 / 1.064 | -9.6 / -17.2 / 21 / 1.224 | -6.7 / -13.1 / 12 / 1.141 |
| H3.0 | -9.2 / -15.5 / 8 / 1.135 | -9.6 / -15.8 / 15 / 1.058 | -9.6 / -15.8 / 11 / 1.219 | -6.7 / -13.1 / 7 / 1.138 |
| H4.0 | -7.0 / -13.1 / 6 / 1.134 | -8.3 / -13.7 / 6 / 1.056 | -7.0 / -13.7 / 6 / 1.217 | -6.7 / -13.1 / 6 / 1.137 |
| HC0.0 | -9.2 / -16.8 / 19 / 1.143 | -9.6 / -17.2 / 49 / 1.068 | -9.6 / -17.2 / 30 / 1.227 | -6.7 / -13.1 / 15 / 1.143 |
| HC0.5 | -9.2 / -17.8 / 17 / 1.141 | -9.6 / -18.2 / 45 / 1.067 | -9.6 / -18.2 / 28 / 1.227 | -6.7 / -13.1 / 14 / 1.142 |
| HC1.0 | -9.2 / -17.8 / 13 / 1.139 | -9.6 / -18.2 / 37 / 1.065 | -9.6 / -18.2 / 23 / 1.224 | -6.7 / -13.1 / 10 / 1.140 |
| HC1.5 | -9.2 / -17.8 / 9 / 1.136 | -9.6 / -18.2 / 22 / 1.060 | -9.6 / -18.2 / 11 / 1.219 | -6.7 / -13.1 / 7 / 1.138 |
| R0.5 | -7.0 / -13.1 / 2 / 1.131 | -8.3 / -13.7 / 6 / 1.056 | -7.0 / -13.7 / 3 / 1.216 | -6.7 / -13.1 / 2 / 1.134 |
| R1.0 | -7.0 / -13.1 / 3 / 1.132 | -8.3 / -13.7 / 11 / 1.057 | -7.0 / -13.7 / 5 / 1.216 | -6.7 / -13.1 / 2 / 1.134 |
| R1.5 | -9.2 / -17.8 / 7 / 1.135 | -9.6 / -18.2 / 24 / 1.061 | -9.6 / -18.2 / 13 / 1.220 | -6.7 / -13.1 / 4 / 1.136 |
| TP3 | -7.0 / -13.1 / 6 / 1.134 | -8.3 / -13.7 / 11 / 1.057 | -7.0 / -13.7 / 7 / 1.217 | -6.7 / -13.1 / 6 / 1.137 |
| TP2 | -9.2 / -17.8 / 14 / 1.140 | -9.6 / -18.2 / 32 / 1.063 | -9.6 / -18.2 / 19 / 1.223 | -6.7 / -13.1 / 12 / 1.141 |
| P2 | -7.0 / -13.1 / 16 / 1.141 | -8.3 / -13.7 / 42 / 1.066 | -7.0 / -13.7 / 25 / 1.225 | -6.7 / -13.1 / 14 / 1.142 |
| HALF | -7.0 / -13.1 / 19 / 1.137 | -8.3 / -13.7 / 49 / 1.063 | -7.0 / -13.7 / 30 / 1.222 | -6.7 / -13.1 / 15 / 1.139 |
| VIXF | -9.2 / -15.5 / 4 / 1.132 | -9.6 / -15.8 / 15 / 1.058 | -9.6 / -15.8 / 8 / 1.218 | -6.7 / -13.1 / 2 / 1.134 |
| VIXFa | -9.2 / -15.5 / 3 / 1.132 | -9.6 / -15.8 / 10 / 1.057 | -9.6 / -15.8 / 4 / 1.216 | -6.7 / -13.1 / 1 / 1.134 |
| VIXopp | -7.0 / -13.1 / 15 / 1.140 | -8.3 / -13.7 / 34 / 1.064 | -7.0 / -13.7 / 22 / 1.224 | -6.7 / -13.1 / 13 / 1.142 |
| OPEN-ONLY | -9.2 / -14.5 / 9 / 1.136 | -9.6 / -14.8 / 21 / 1.060 | -9.6 / -14.8 / 14 / 1.220 | -6.7 / -13.1 / 6 / 1.137 |
| CLOSE-ONLY | -7.0 / -13.1 / 13 / 1.139 | -8.3 / -13.7 / 32 / 1.063 | -7.0 / -13.7 / 18 / 1.222 | -6.7 / -13.1 / 11 / 1.141 |

## Reading rule per arm (dSharpe vs C0 on real / proxy01 / proxy10 / real-ex; dDD in pp, negative = deeper; flags r1..r5, `run.log` has the table)
- **L1**: -0.036 / +0.025 / +0.023 / +0.059; DD -8.9 / -2.8 / -4.9 / -0.7 pp. **Fails r1 (real), r2, r3, r4 (second half of proxy 2001: -0.004); r6 true (placebo percentile 72 / 87 / 92).** Fails the rule on complete data.
- H2.5 -0.023 / +0.015 / +0.016 / +0.069, H3.0 -0.042 / -0.021 / -0.018 / +0.041: fail. H4.0 +0.036 / +0.017 / +0.025 / +0.037 (DD identical to C0, i.e. never opens on the days that hurt): fails r1 on proxy01 (+0.017 < 0.02), r4 (first half +0.000), r5 (neighbour H3.0 negative).
- HC-y (HC0.0 = L1; 0.5 -0.028 / +0.032 / +0.027; 1.0 -0.057 / +0.015 / -0.000; 1.5 -0.059 / -0.007 / -0.027): fail; DD 9.8 pp deeper on real. R-z (0.5 / 1.0 / 1.5: real -0.019 / -0.023 / -0.101): fail. The reversal filter keeps 11-04 (close 1.4% under the high) out only for z <= 1.0%, but then still opens days that closed near the high, e.g. 2025-03-05 (close 0.3% under, -5.5 pp next day), so real DD is -20.6% vs C0 -16.5%; at z=1.5% it opens 11-04 (DD -26.3%).
- **TP3** +0.072 / +0.026 / +0.050 / +0.074, DD equal to C0 on all windows: **closest to passing**: passes r1, r2, r3, placebo 100 / 99 / 100; fails r4 (first half of proxy 2001 -0.018) and r5 (its neighbour TP2 is -0.050 / +0.005 / -0.008 and DD 9.8 pp deeper). Its real gain comes from 6 openings (vs 19), none of them the 11-04 day; the typical-price line is a post-hoc discriminator on 2026-10-30..11-04, not an independent finding. lag-1 gain only +0.006 on real.
- TP2 fail. P2 +0.037 / +0.051 / +0.053 / +0.046: fails r2 (real DD -2.3 pp deeper, -18.8% vs -16.5%); placebo 76 / 98 / 98 (a persistence rule gains a lot on random highs too, placebo mean +0.014..0.019). HALF +0.014 / +0.027 / +0.032: fails r1 on real (+0.014) and r2 (-1.2 pp real); placebo 83 / 96 / 98; its bootstrap on proxy excludes 0 (5-95% [+0.008, +0.066]).
- VIXF (my calm-market version) -0.105 / -0.020 / -0.048: **worse**; VIXFa also worse; VIXopp (the opposite: high counts only when VIX is not calming) +0.068 / +0.045 / +0.071 but real DD 2.3 pp deeper (fails r2) and it is the reverse of the pre-stated hypothesis (selected by the data; not meaningful). OPEN-ONLY -0.055 / -0.007 / -0.013 fail; CLOSE-ONLY +0.041 / +0.042 / +0.035 but real DD -2.3 pp (fail r2); placebo 80 / 97 / 90.
- **No arm passes**; none meets r1..r6 together. Arms beating C0 on all three windows: H4.0, TP3, P2, HALF, VIXopp, CLOSE-ONLY (robustness below).

## Robustness of arms that beat C0 on all three windows (Sharpe difference vs C0; `run.log`)
| arm | real full / half1 / half2 / ex-2020 / lag1 / boot median, P(<=0) | proxy01 | proxy10 |
|---|---|---|---|
| L1 | -0.036 / +0.018 / -0.081 / -0.039 / +0.041 / +0.032, 0.34 | +0.025 / +0.057 / -0.004 / +0.027 / +0.085 / +0.054, 0.09 | +0.023 / +0.097 / -0.055 / +0.025 / +0.060 / +0.064, 0.11 |
| H4.0 | +0.036 / -0.014 / +0.083 / +0.040 / +0.030 / +0.034, 0.09 | +0.017 / +0.000 / +0.032 / +0.018 / +0.014 / +0.017, 0.08 | +0.025 / +0.010 / +0.039 / +0.027 / +0.020 / +0.023, 0.09 |
| TP3 | +0.072 / +0.016 / +0.125 / +0.079 / +0.006 / +0.071, 0.001 | +0.026 / -0.018 / +0.065 / +0.027 / +0.017 / +0.025, 0.04 | +0.050 / +0.018 / +0.081 / +0.053 / +0.006 / +0.048, 0.000 |
| P2 | +0.037 / -0.008 / +0.081 / +0.041 / +0.030 / +0.040, 0.15 | +0.051 / +0.054 / +0.047 / +0.053 / +0.071 / +0.053, 0.01 | +0.053 / +0.064 / +0.038 / +0.056 / +0.039 / +0.054, 0.02 |
| HALF | +0.014 / +0.009 / +0.014 / +0.014 / +0.027 / +0.032, 0.15 | +0.027 / +0.035 / +0.023 / +0.028 / +0.055 / +0.038, 0.03 | +0.032 / +0.058 / +0.008 / +0.034 / +0.039 / +0.046, 0.03 |
| VIXopp | +0.068 / -0.008 / +0.139 / +0.075 / +0.024 / +0.072, 0.03 | +0.045 / +0.010 / +0.075 / +0.047 / +0.053 / +0.046, 0.02 | +0.071 / +0.064 / +0.076 / +0.075 / +0.035 / +0.072, 0.00 |
| CLOSE-ONLY | +0.041 / +0.014 / +0.070 / +0.046 / +0.017 / +0.044, 0.09 | +0.042 / +0.045 / +0.038 / +0.044 / +0.043 / +0.043, 0.01 | +0.035 / +0.022 / +0.046 / +0.038 / +0.006 / +0.036, 0.04 |
Placebo (200 draws; percentile of the real Sharpe gain among placebo gains, real / proxy01 / proxy10): L1 72 / 87 / 92; H4.0 100 / 100 / 100; TP3 100 / 99 / 100; P2 76 / 98 / 98; HALF 83 / 96 / 98; VIXopp 98 / 100 / 100; CLOSE-ONLY 80 / 97 / 90.
Reading: the placebo rule (>= 90th on one track) is met by all of them, but it is a weak test here: random highs at random sessions make an arm that opens often (L1) lose Sharpe (placebo mean -0.058 on real), so anything that opens on fewer days looks "above placebo" (H4 placebo mean -0.007). Lag-1 gains are small for TP3/H4 and the 5-95% bootstraps include 0 for H4, P2 (real), HALF (real), CLOSE-ONLY (real); TP3 and VIXopp exclude 0 but are the arms whose real result is decided by the 10-30..11-04 spells.
Lag 1 flips L1 on real to +0.041 (the day-shifted book dodges the 11-05 loss), another sign that the real-window sign of L1 is one-day-timing luck.

## Verdict under the reading rule
- **L1 (original): does not pass on complete data** (r1 real -0.036, r2 DD -8.9 / -2.8 / -4.9 pp, r3, r4). Excluding the 2026-10-26..11-16 stretch it is +0.059 and DD -0.7 pp (still outside the 0.5 pp), and its sign over 2001-2026 is positive (+0.025 / +0.023); the gain is 26 up / 11 down spells on the proxy with a total decided by a handful of days.
- **H2.5/H3.0/H4.0, HC0.0-1.5, R0.5-1.5, TP2, VIXF, VIXFa, OPEN-ONLY: fail** (see above). **TP3, P2, HALF, VIXopp, CLOSE-ONLY: fail** (TP3: r4, r5; P2, VIXopp, CLOSE-ONLY: r2; HALF: r1 and r2).
- **Conclusion: keep L1 off (C0) as the rule-compliant answer; no better L1 is proposed.** If the owner nevertheless wants an L1-type rule, the least-bad shapes by this data are a stricter high threshold (H4%: never opens on 10-30..11-04, DD equal to C0, +0.036/+0.017/+0.025) or the typical-price read (TP3), but both are shaped by the same three sessions, were run after seeing the 11-04 result, and fail the plateau/halves tests; that is a post-hoc fit, not a recommendation.

## Wrong, skipped or approximate
- Full-day highs include 15:50-16:00; checked on 5 of 19 real event days only (older bars unavailable, AlphaVantage intraday premium). Proxy events 2000-2025 are all full-day.
- Lows after 2026-09-04 come from Robinhood daily bars (needed only by TP3); 10-30 high differs 698.63 (daily) vs 697.94 (regular-session 30-min bars), 0.1 pp of gap.
- VIX is the daily close (not 15:50). The "VIXF" arm is my reading of "calming market" (below the 10-day mean incl. today, OR down on the day).
- HALF, OPEN-ONLY, CLOSE-ONLY need a stored previous-session flag; the live `gate_gap200` is stateless, so these are research constructs (not in the current code path). HALF halves the risky legs before the 2.0x cap; its trade cost and the key change are in the engine.
- Spell definition: until the two books' target weights re-align plus one session. Event-day windows (5/20) overlap neighbouring events; use the spell column for sums.
- Real-ex is the real window ended 2026-10-23; I did not remove the stretch from the proxy windows (they include 2026-10-26..11-16).
- Placebo draws random same-year (H/C-1, L/C-1) pairs; it breaks the high's link to the actual path but also changes how many events there are, so it favours sparse arms. It was run on real, proxy01 and a slice of the proxy01 run for proxy10.
- Rule item "neighbouring parameter values point the same way" is n/a for P2, HALF, VIXopp, OPEN-ONLY, CLOSE-ONLY (no parameter) and is counted as not failing; those arms fail anyway on other items.
- 21 arms on overlapping data; any Sharpe difference of about +/-0.03 on the real window is within noise (bootstrap 5-95% widths about 0.1 on real, 0.04-0.06 on the proxy).
- 2026-11-04 in the engine is a daily-bar simulation: fill at the close, 2 bp per side, no taxes.
