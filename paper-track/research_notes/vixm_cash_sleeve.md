# VIXM sleeve in the cash leg — research record (2026-10-08)

Owner question: "during cash positions in different states, can we hold some
positions?" Applied 2026-10-08 as an owner decision after the review below.
Code: `paper-track/state.py` (VIXM section), `paper-track/vol_curve.py`.
Research scripts (full history, all variants): repo `xyxyxy33e-sys/Robinhood`,
branch `research/vol-backtest`, `research/regime_tape_*.py` and
`research/vix_curve.py`.

## Harness

The Regime Tape artifact's daily weights (2016-08-29 .. 2026-08-27; the
2026-09-23 design with A = 50/50, every overlay applied) replayed on real
instruments, price-only like the page, BOXX at the 13-week T-bill, 4 bp
one-way, weights set at a close earn the next session. Replay reproduces the
page (44.8% vs 44.9% CAGR, daily corr 1.0000). Only the contents of the BOXX
slot change. The slot averages 38% of the book (A 30%, D 29%, E 100%, F 86%).

## What was tried, in order

| idea | verdict |
|---|---|
| gold (IAU) 50% of the slot | +3.6pp CAGR, Sharpe up both halves; **declined by owner**: gold 2026 vol 31%, -24% from its Jan peak, corr to SPY rising |
| static 20% VIXM in the slot | Sharpe 1.88 but recent half 1.37 < live 1.40 — the 2018 effect |
| VIXM per state (static) | bleeds in C/E/F: bought after the spike. No per-state static mix survives both halves |
| VIX 4-7 month switch (vix_improve) in the slot | 2020-only; recent half 0.84 |
| **VIXM while cheap: on at VIX < 18, off at VIX > VIX3M** | 26 of 36 entry/exit/size variants beat BOXX on both halves; exit at ratio 1.0 best for every entry |
| per-state VIX gates | no state's alternative gate beats 18 on both halves (B/C/E/F have 3-9 episodes) |
| VXN instead of VIX | interchangeable as the gate (VXN<22 ~ VIX<18); worse as stress filter and exit |
| caps on VIXM (% of book) | shrink wins and losses alike; worse on both halves |
| **stress filter: QQQ 30d vol >= 20%** | removes the trim-driven calm-market bleed (Jun 2023: VIXM 37.5% of book, -18% month, -7.4pp) |
| size 25..100% of the slot (with filter) | monotone, flat max DD; 75% chosen: ~all of the gain, 25% BOXX kept, VIXM trade ~12% of ADV at $540k |
| extra exits (take-profit, trailing, stop, time) | inside noise; **VIX fade -25% from high** fixes Jun 2026 (-2.5pp -> +0.3pp) at no cost |

## Final rule and evidence

latch ON at VIX < 18 (and VIX <= VIX3M), OFF at VIX > VIX3M; VIXM only while
QQQ 30d realized vol >= 20%; VIXM = 75% of the cash leg; sell early when VIX
is 25% below its high since entry (blocked until stress resets).

| | CAGR | MaxDD | Sharpe | worst 12m | 2016-21 | 2021-26 |
|---|---|---|---|---|---|---|
| live (all BOXX) | 44.8% | -17.7% | 1.79 | -11.7% | 2.20 | 1.40 |
| final, signal from prior close | 50.4% | -17.7% | 1.93 | -8.8% | 2.29 | 1.61 |
| **final, same-session signal (as run live)** | **47.9%** | **-17.7%** | **1.90** | **-9.7%** | **2.26** | **1.56** |
| final, +1 session late | 47.4% | -17.7% | 1.80 | -10.9% | 2.28 | 1.40 |

Robustness: VIXM cost 4/10/20/30 bp -> Sharpe 1.93/1.92/1.91/1.90; 86 of 108
neighbouring parameter sets (gate 16/18/20 x share 50/75/100 x vol 18/20/22 x
fade none/15/25/35) beat live on both halves, 36 deepen max DD by > 1pt;
from 2019: 42.1% / 1.69 -> 47.6% / 1.81; from 2023: 48.8% / 1.70 -> 60.2% /
1.92. Live code (`state.vixm_series` on CBOE history) agrees with the
backtest gate on 99.92% of days (2 edge days at the 20% vol line) and
reproduces its result exactly.

Monthly (final vs live): 26 of 121 months differ, 14 better / 12 worse;
best Aug 2024 +18.2pp, Nov 2018 +5.0, Mar 2025 +4.5; worst May 2018 -1.5,
Jun 2026 -1.4. Year differences: 2018 +13.1, 2019 -4.3, 2021 +3.2, 2022
+3.1, 2023 +6.7, 2024 +30.1, 2025 +9.3, 2026 -1.4.

## Limitations — carry these

1. One ~10-year window. VIXM begins 2011, the CBOE futures files 2013: the
   26-year proxy cannot test it. Same evidence class as the D gate.
2. Concentrated: Aug 2024 is about a third of the gain; without it ~+3-4pp/yr.
3. Execution-sensitive: one extra session of lag erases most of it. The VIXM
   leg trades in the 15:5x window like everything else; VIXM has NO
   extended-hours tradability, so a missed run's VIXM leg waits for the next
   regular session.
4. VIXM decays ~15-19%/yr while held (53% of held days lose to BOXX); the
   stress filter and the fade keep holding stretches short (median 11 sessions).
5. The parameters (18 / 1.0 / 20% / 75% / 25%) were chosen on the full window;
   the neighbourhood check is the only defence against that.
6. VIX3M is ~15 min delayed at 15:5x (CBOE); VIX is real time (Robinhood).
