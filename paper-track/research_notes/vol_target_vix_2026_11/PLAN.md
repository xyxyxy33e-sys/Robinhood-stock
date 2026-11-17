# PLAN (pre-registered 2026-11-17, written before any arm was run; research only, nothing adopted)

Question: does adding VIX / VXN to the vol-target estimator improve the live strategy?

## Setup
- Engine: `paper-track/review_2026_11/harness.py` (CUR design: 40/60 A + trim v2, D ladder + gate + buffer, VIXM sleeve,
  deep-E and VIX-panic QQQ legs, 5% band, 2 bp/side). The harness default has NO 2.0x gross cap; the live design has it,
  so the **main baseline is CUR + gross_cap=2.0** (harness `cfg` hook). The plain harness default is reported too, and the
  full arm set is re-run on it as a robustness pass (verdict table only). The L1 gate is not in the harness.
- Tracks: real instruments 2015-11-02..2026-11-16; proxy 2001-01-02..2026-11-16.
- Only the vol estimator feeding `min(1, 20%/vol)` changes. Regime keys, VIXM sleeve (harness VIX), panic latch unchanged.
- VIX/VXN input: FRED `vol_predict_2026_11/VIXCLS.csv` / `VXNCLS.csv`, forward-filled over missing dates, /100.
  **Convention:** the harness realized vol at session t uses returns through the close of t, and its VIX sleeve/panic logic
  uses the same-day VIX close, trade at close t. New input uses the same: VIX close of day t sets the multiplier traded at
  close t. Robustness: VIX/VXN lagged one extra day (value of t-1).
- k_med = median over 2001-2026 proxy sessions of rv30/VIX (reported; one value used for both tracks; mild in-sample).

## Arms (estimator = what replaces max(rv10, rv30) in the vol target)
- Base: max(rv10, rv30).
- V1: max(rv10, rv30, k*VIX), k in {0.8, 0.9, 1.0, 1.1, 1.2}.
- V2: max(rv10, rv30, k*VXN), k in {0.7, 0.8, 0.9, 1.0}; before VXN exists (pre 2001-02) falls back to Base.
- V3: w*(k*VIX) + (1-w)*max(rv10, rv30), w in {0.25, 0.5}, k in {1.0, k_med}.
- V4: k*VIX alone, k in {1.0, 1.2, k_med}.
- V5: V1 estimator only on days whose effective state is A or ungated D, else Base; same k grid as V1.
- Matched de-lever (MD) for every arm and track: Base with vol_target lowered (bisection, 0.05..0.60) so that average target
  gross exposure (sum of leg weight x GROSS_EXPOSURE, after cap, over the track's evaluation days) equals the arm's.
  An arm is compared with its own MD, not just Base.

## Metrics
CAGR, Sharpe (mean/sd, no rf, as harness), max DD, annual vol, avg gross, share of days the new term changes the multiplier
vs Base, trades/yr, worst day, worst 5-day compounded. Year-by-year diff vs Base and vs MD (real), ex-2020, first/second half
of each track (split at the midpoint session), extra-day lag of the new input (MD re-matched), paired block bootstrap
(20-session circular blocks, 2,000 paths, same blocks for arm and MD) of Sharpe(arm)-Sharpe(MD), P = share of paths with
difference <= 0 (one-sided). Calm-crack days (QQQ <= -3% with prior-day VIX < 20, analyze.log section 7) inside each track.

## PASS BAR (versus the arm's own matched de-lever)
An arm passes only if ALL hold:
1. Sharpe higher than MD on BOTH tracks;
2. max DD not worse than MD's by more than 0.5 pp on either track;
3. Sharpe beats MD in both halves of both tracks AND with 2020 removed (on both tracks);
4. at least two other k values (V3: other cells of its 2x2 grid; V4: other members) pass criteria 1-3, so 3+ cells pass in all;
   for V1/V2/V5 these must be neighbours in the k grid (contiguous run of 3);
5. bootstrap P < 0.10 on at least one track.
Otherwise: rejected. Lag-1 results are reported as a robustness check, not part of the bar. Results within noise will be called so.

## ADDENDUM (owner request, same day, before any run; pass bar unchanged)
Extra view: proxy track with evaluation starting 2010-01-01 (indicators warmed on earlier data), labelled `p2010`, with the same
columns for Base, every arm and its matched de-lever (MD re-matched to average gross over that window), plus whether each arm
beats its MD there (Sharpe, max DD, halves, ex-2020, bootstrap P). The pass bar still uses the real track and the full 2001-2026
proxy only; p2010 is informational.
