# Trigger chop study (2026-11-24): which regime-key triggers chop, does a buffer help?

Research only. Nothing outside this folder was touched. Run: `python3 paper-track/research_notes/trigger_chop_2026_11/run.py > run.log` from the repo root.
Files: `common.py` (monkeypatch header, helpers, rebalance-cause replica), `run.py` (Part 1 + Part 2), `run.log`, `results.json`.
Engine `harness_live.run_live_detail(track, vixy_source='old')`; buffers patched in memory (HL.signals wrapper for the D gate, H.CUR['d_buffer'] for the zone).

Baseline reproduces: real CAGR 51.48% / Sharpe 2.097 / maxDD -16.80% / 46.1 trades/yr; proxy 34.40% / 1.485 / -22.12% / 42.3 trades/yr.
The replica of `MC.run_strategy`'s rebalance decision gives the same trade counts as the engine (509 real, 1094 proxy).

## Part 1: chop per trigger (per-session key components, sample = backtest window)
"Spells" = runs of a constant value (binary triggers: on-spells). "Short" = interior spell <= 3 sessions. "Re-flip" = a spell of <= 5 sessions that returns to the value it came from.

| trigger | real flips/yr | real spells | real short<=3 | real re-flips | proxy flips/yr | proxy spells | proxy short<=3 | proxy re-flips |
|---|---|---|---|---|---|---|---|---|
| macro state (1% hysteresis lines) | 11.2 | 125 | 22 (18%) | 21 | 11.7 | 304 | 64 (21%) | 51 |
| eff state (macro + fast 20/100) | 13.9 | 154 | 31 (20%) | 29 | 15.1 | 390 | 94 (24%) | 76 |
| fast overlay active (eff != macro) | 5.7 | 32 | 7 (23%) | 13 | 7.8 | 101 | 31 (31%) | 64 |
| **D gate (effective)** | 9.6 | 54 | 30 (56%) | 53 | 8.9 | 118 | 64 (54%) | 116 |
|   gate_b breadth half | 4.0 | 22 | 17 (77%) | 28 | 3.8 | 49 | 39 (80%) | 64 |
|   gate_g gap200<2% half | 4.3 | 24 | 19 (79%) | 30 | 4.6 | 60 | 47 (78%) | 73 |
| **D ladder zone (0.5% buffer already live)** | 14.8 | 164 | 82 (51%) | 62 | 12.7 | 329 | 164 (50%) | 114 |
| VIXY sleeve allowed | 7.8 | 43 | 17 (40%) | 34 | 5.3 | 69 | 27 (39%) | 54 |
| VIX-panic | 5.2 | 29 | 6 (21%) | 13 | 5.4 | 71 | 18 (26%) | 36 |
| deep-E (already fixed live; shown for reference) | 4.3 | 24 | 9 (39%) | 16 | 4.4 | 57 | 21 (38%) | 39 |
| A trim votes (held) | 5.3 | 60 | 17 (29%) | 10 | 5.5 | 142 | 40 (29%) | 32 |

Trade-day attribution (rebalance days whose key component changed; a day can carry several; "sole" = only that component changed):

| cause | real days (/yr) | real sole | proxy days (/yr) | proxy sole |
|---|---|---|---|---|
| eff state | 153 (13.9) | 36 | 389 (15.1) | 131 |
| A trim votes | 59 (5.3) | 19 | 141 (5.5) | 35 |
| D gate | 106 (9.6) | 0* | 231 (8.9) | 0* |
| D zone | 163 (14.8) | 42 | 328 (12.7) | 75 |
| VIXY sleeve | 86 (7.8) | 35 | 138 (5.3) | 37 |
| deep-E | 47 (4.3) | 17 | 113 (4.4) | 30 |
| VIX-panic | 57 (5.2) | 25 | 139 (5.4) | 47 |
| pure drift (>5%, no key change) | 164 (14.9) | | 369 (14.3) | |
| all rebalance days | 509 (46.1) | | 1094 (42.3) | |

*A gate flip always also moves the zone term of the key (only D has a gate), so it is never the sole cause; the gate and zone are one coupled D-state trigger. Of eff-change trade days, 109 (real) / 252 (proxy) coincide with a macro-state change and 44 / 137 are fast-overlay-only.

Choppiest by short-spell round trips: (1) D gate, both halves (about 55% of spells <= 3 sessions, nearly every spell re-flips within 5; the gap200 half is 78-79% short), (2) D ladder zone (50% short, most flips in absolute terms despite the live 0.5% buffer), (3) VIXY sleeve latch (40% short). The macro 1% hysteresis lines and the fast overlay are comparatively clean (18-24% short; the overlay's 20-31% of spells being short is its main cost).
About a third of all trades (14-15/yr) are pure drift, not triggers.

## Part 2: buffers (pre-declared, 4 + 3 variants; no others were run)
Gate variants act on the gap200 half of the D gate (gate on when gap200 < line; macro D only). Hysteresis: enter below X, stay until above Y. Min-hold n: a state may flip only after n sessions in it. Zone variants: `d_zone_buffer` 0.5% (live) raised. "RT" = spells <= 3 sessions of the trigger the variant targets (effective D gate; zone runs).

| variant | panel | CAGR | Sharpe | Sh ex-2020 | maxDD | trades/yr | gate short spells (of) | zone short runs |
|---|---|---|---|---|---|---|---|---|
| BASE live | real | 51.48 | 2.097 | 2.044 | -16.80 | 46.1 | 30 (54) | 82 |
| | proxy | 34.40 | 1.485 | 1.439 | -22.12 | 42.3 | 64 (118) | 164 |
| gate_g in<1.5% out>2.5% | real | 52.86 | 2.137 | 2.087 | -18.84 | 45.8 | 25 (49) | 78 |
| | proxy | 34.91 | 1.502 | 1.457 | -22.12 | 41.7 | 51 (106) | 145 |
| gate_g in<1.0% out>3.0% | real | 52.65 | 2.120 | 2.069 | -18.84 | 45.9 | 23 (46) | 83 |
| | proxy | 34.70 | 1.491 | 1.445 | -22.29 | 41.5 | 47 (100) | 148 |
| gate_g min-hold 2 | real | 51.94 | 2.104 | 2.051 | -16.54 | 45.9 | 23 (48) | 81 |
| | proxy | 34.90 | 1.497 | 1.451 | -22.12 | 42.1 | 51 (106) | 164 |
| gate_g min-hold 3 | real | 48.88 | 2.001 | 1.940 | -16.54 | 45.9 | 20 (45) | 80 |
| | proxy | 33.08 | 1.435 | 1.387 | -22.12 | 41.8 | 46 (101) | 156 |
| zone buffer 0.75% | real | 50.90 | 2.083 | 2.028 | -16.80 | 45.3 | 30 (54) | 68 |
| | proxy | 34.21 | 1.478 | 1.432 | -22.12 | 41.5 | 64 (118) | 137 |
| zone buffer 1.0% | real | 50.74 | 2.070 | 2.014 | -18.54 | 44.6 | 30 (54) | 59 |
| | proxy | 34.12 | 1.473 | 1.426 | -22.12 | 41.3 | 64 (118) | 131 |
| zone buffer 1.5% | real | 49.87 | 2.031 | 1.972 | -18.54 | 44.2 | 30 (54) | 49 |
| | proxy | 33.58 | 1.452 | 1.404 | -22.12 | 40.8 | 64 (118) | 107 |

Bar (pre-registered), required on BOTH panels: Sharpe >= baseline - 0.01; maxDD no worse than 0.5 pt; AND (trades/yr cut >= 3 OR targeted round trips cut >= 30%). Result per variant (real / proxy; S = Sharpe ok, D = drawdown ok, C = cut ok):

| variant | dSharpe | dMaxDD (pt) | trades/yr cut | RT cut | S D C | verdict |
|---|---|---|---|---|---|---|
| gate_g in1.5/out2.5 | +0.040 / +0.017 | -2.05 / 0 | 0.4 / 0.7 | 17% / 20% | real fails D, C | FAIL |
| gate_g in1.0/out3.0 | +0.023 / +0.005 | -2.05 / -0.17 | 0.3 / 0.8 | 23% / 27% | real fails D, C | FAIL |
| gate_g min-hold 2 | +0.006 / +0.011 | +0.25 / 0 | 0.2 / 0.2 | 23% / 20% | S, D ok; C fails | FAIL (cut too small) |
| gate_g min-hold 3 | -0.096 / -0.051 | +0.25 / 0 | 0.3 / 0.5 | 33% / 28% | S fails | FAIL |
| zone 0.75% | -0.014 / -0.007 | 0 / 0 | 0.8 / 0.8 | 17% / 16% | real S fails, C fails | FAIL |
| zone 1.0% | -0.027 / -0.013 | -1.74 / 0 | 1.5 / 1.0 | 28% / 20% | fails S, D, C | FAIL |
| zone 1.5% | -0.066 / -0.034 | -1.74 / 0 | 1.9 / 1.5 | 40% / 35% | fails S, D | FAIL |

## Verdict
Nothing passes. D gate and D zone are the choppiest triggers (about half of their spells last <= 3 sessions), but they are cheap to chop: the 2 bp/side cost on the small weight changes they cause means that cutting 20-30% of their short spells removes only about 0.2-1.9 trades/yr, far below the 3/yr bar, because most trades are drift-driven (about 15/yr) or come from the eff state, trim votes, VIXY and panic triggers. The only variants that cut round trips by >= 30% (gate min-hold 3 on real, zone 1.5% on both) lose 0.05-0.10 Sharpe. The gate hysteresis lines raise Sharpe (+0.02 to +0.04 real, +0.005 to +0.017 proxy, partly an in-sample effect of one line shifting) but deepen the real maxDD by 2.05 pt and cut trades by under 1/yr, so they are a return/risk tradeoff, not a chop fix. Gate min-hold 2 is harmless (Sharpe +0.006/+0.011, DD unchanged) but also nearly useless (0.2 trades/yr). No change is recommended. Caveats: one fixed set of variants, single sample per panel, the real panel has only 54 gate spells; the VIXY latch (third choppiest) and the breadth half of the gate were not buffer-tested.
