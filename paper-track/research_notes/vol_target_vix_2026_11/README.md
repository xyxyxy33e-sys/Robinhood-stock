# Does VIX / VXN in the vol-target estimator help? (2026-11-17, research only, nothing adopted)

Files: `PLAN.md` (pre-registered arms and pass bar, with the owner's 2010+ addendum), `run.py`, `run.log` (all tables).
Engine: `review_2026_11/harness.py`; main baseline = CUR + 2.0x gross cap (live design, cap via cfg). No L1 gate in the harness.

## Baseline reproduced (harness as it stands; CAGR / Sharpe / max DD)
| | real 2015-11..2026-11 | proxy 2001..2026-11 | proxy 2010+ |
|---|---|---|---|
| harness default (no cap, VIXM) | 51.3% / 2.010 / -18.7% | 34.8% / 1.425 / -22.1% | 44.6% / 1.656 / -21.9% |
| CUR + 2.0x cap (main baseline) | 47.3% / 2.009 / -17.1% | 31.8% / 1.409 / -22.1% | 40.4% / 1.637 / -20.4% |
These differ from the quoted numbers (VIXY sleeve, L1 gate) as expected; the proxy cap run is close to the quoted no-L1 31.9% / 1.410.

## Convention
VIX/VXN close of day t sets the multiplier traded at close t, exactly like the harness realized vol and harness VIX sleeve/panic
logic. Lag-1 arms use t-1. FRED files, forward-filled. Median rv30/VIX = 1.03 (2001-26; 0.975 since 2010; quartiles 0.84-1.25), so
k_med = 1.03. Median VXN/VIX 1.21, rv30/VXN 0.82.

## Result: every arm is rejected
Each arm's Sharpe is BELOW its matched de-lever (same average gross) on all three windows, for every arm and k, with and
without the cap. Sharpe differences vs matched de-lever (real / proxy / proxy 2010+):
- V1 VIX floor k=0.8..1.2: -0.003..-0.044 / -0.004..-0.031 / -0.003..-0.024 (worse as k grows). k=1.0: -0.014 / -0.018 / -0.014.
- V2 VXN floor: -0.003..-0.023 / -0.001..-0.029 / -0.001..-0.020.
- V3 blends: -0.018..-0.035 / -0.010..-0.023 / -0.008..-0.018.
- V4 VIX only: -0.037..-0.082 / -0.053..-0.080 / -0.021..-0.054; also max DD up to 2.3 pp deeper on proxy (k=1.0).
- V5 calm-only floor: essentially identical to V1 (-0.003..-0.043 / -0.003..-0.034 / -0.003..-0.029).
Bootstrap P (one-sided P that the gain is <= 0) is 0.79-1.00 everywhere; no arm is near 0.10. Maximum-DD gains vs matched
de-lever exist only for k>=1.1 (real up to +0.42 pp) and never offset the Sharpe loss. Core criteria (both tracks, halves, ex-2020)
fail for all arms, so neighbour and bootstrap tests are moot. Lag-1 inputs: same sign (slightly less negative), none positive beyond
+0.001. Versus Base (not the fair test) all arms are within -0.001..-0.12 Sharpe and lower CAGR, since they simply hold less risk.

Matched de-lever is the right yardstick: a higher vol estimate cuts exposure (avg gross 1.099 -> 1.083 at V1 1.2 on real), and simply
lowering the target to match does at least as well. 2010+ window (extra view): V1 k=1.0 39.6% / 1.625 / -20.4% vs matched
40.2% / 1.639 / -20.3%; V4 k=1.0 40.0% / 1.579 / -23.7% vs 41.0% / 1.599 / -23.7%. No arm beats its matched de-lever there either,
including the VIX floor and VIX-only arms. (Full per-arm columns for all three windows are in run.log.)

## Calm-crack days (QQQ <= -3%, prior VIX < 20; 42 listed, 20 in real track, 33 in proxy, 22 in 2010+)
Strategy mean return on those days: real Base -1.67% (QQQ -3.72%), best V1 (0.8) -1.67%; proxy Base -1.88%, V1/V5 -1.87..-1.88%;
2010+ Base -2.06%. Reason: with a 20% target the floor k*VIX can only bind when VIX > 20/k, i.e. never on a day with prior VIX < 20 for
k<=1.0, and only for VIX 16.7-20 at k=1.2; so V1/V5 do nothing on these days by construction (only the matched de-lever, which holds
less risk everywhere, trims the loss slightly, e.g. -1.56% at the k=1.2 match). The 2026-11-05 day (-6.5% QQQ) is +2.37% for Base and
all arms in the real track (the book was not exposed to it); VIX could not have changed that.

## Limits
- Gross exposure matched on target weights (not realized after drift). One k_med from the full proxy sample (mild in-sample).
- Neighbour-k rule interpreted as in PLAN.md. V2 real/p2010 windows include VXN (exists from 2001-02); pre-2001-02 falls back to Base.
- The "bind" column on matched de-lever rows compares its multiplier with the 20% Base and is not meaningful.
- Harness has no L1 gate and uses VIXM, not VIXY; price returns only; bootstrap uses 20-session circular blocks, 2,000 paths.
- Differences of 0.001-0.005 Sharpe (k<=0.9, V2 0.7) are within noise; the conclusion rests on the consistent sign across 3 windows, 2 cap settings and all k.
