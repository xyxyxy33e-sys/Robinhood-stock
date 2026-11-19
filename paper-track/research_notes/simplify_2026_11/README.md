# Simplification / overfitting test (2026-11-19)

`simple.py` (run from a scratch copy of review_2026_11/harness.py + untouched_test.py, today's partial row skipped).
Current design with the 2.0x cap, vol sleeve off everywhere. Each piece removed in turn, then BARE (six rows + vol
target + cap) and two simple designs (above-200d via the six states: 40/60 or 100% core, else cash).

In-sample (CAGR / Sharpe / MaxDD): full 45.2/1.93/-19.3 real, 31.8/1.41/-22.1 proxy, 22.4/1.07 holdout.
Every removal costs in-sample; biggest: trim (38.6/1.35 real, 0.90 holdout, DD -28.7 proxy), D gate (36.5/1.49,
DD -30.9), fast re-entry (-3.4pp real, -4.2pp holdout), QQQ cash legs (-5.1pp real). Ladder and zone buffer: small.
BARE 23.0/0.89 real. SIMPLE 40/60 23.0/0.88. SIMPLE unlevered 11.4/0.87.

Untouched sets (excess Sharpe, lag 0; buy & hold NDX87-00 0.634, Nikkei 0.180, DAX 0.320, FTSE 0.191):
full 0.517 / 0.050 / 0.290 / -0.108. Without trim 0.703 / 0.200 / 0.341 / -0.125 (beats full on 3 of 4, beats
buy & hold on NDX, Nikkei, DAX). BARE 0.526 / 0.174 / 0.397 / -0.082 and SIMPLE 0.557 / 0.197 / 0.370 / -0.001 beat
full on all four. SIMPLE unlevered 0.544 / 0.203 / 0.381 / 0.013 with the shallowest drawdowns (-23 to -45%).
Removing the gate, ladder, fast overlay, cash legs or buffer moves the untouched sets little either way.

Reading: the in-sample edge of the full design over the simple ones lives mostly in trim v2 (fit on 2015-26 after
~90 variants) and the D gate; trim v2 is the one piece that is clearly worse out of sample. The trend + vol-target
core is roughly as good as buy-and-hold on untouched data, with shallower drawdowns; the extras do not travel.
No live change made (owner decision).
