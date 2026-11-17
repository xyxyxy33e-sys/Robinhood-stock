# PLAN (pre-registered 2026-11-17, written before any arm was run; research only, nothing adopted)

Question: does an extra "calm hedge" (VIXY, and as an owner addendum VIXM) held while the book is leveraged and the market
is calm earn its roll decay? Prior: no. Tested against a matched cash control, not just the baseline.

## Engine and baseline
- `paper-track/review_2026_11/harness.py` (CUR design, 2 bp/side), plus the 2.0x gross cap through the cfg hook (`gross_cap=2.0`,
  as vol_target_vix_2026_11/run.py). No L1 gate (harness has none).
- Baseline sleeve: VIXY at 35% of the cash leg (`vixm_share=0.35`, VIXY returns from
  research_notes/vixm_followups_2026_11/vixy_daily.csv, extended with the VIXY column of data/live_closes.csv after 2026-11-10).
  Reproduced and reported as is; no forcing to the quoted 50.4% / 2.080 / -16.5%.
- Existing sleeve stays as is in every arm (VIXY 35% of cash leg).
- Windows. VIXY data in the repo start 2015-09-01 (VIXY listed 2011; 2011-2015 is NOT in the repo; there is no VIXY synthetic in
  the repo; the CFE mid-term proxy is a VIXM-like series, not VIXY, and is not used). I build none. So:
  * `real`: real ETFs, 2015-11-02 .. last date (2026-11-16).
  * `vera` (proxy panel, VIXY era): proxy panel (QQQ core, synthetic TQQQ/QLD) from 2015-09-02 to the same last date, with the
    sleeve (VIXY 35%, same latch) switched on, which the harness does not do on its proxy track. Not independent of `real`
    (same market years); it tests the instrument substitution only.
  * The requested 2010-onward window cannot be run: no VIXY before 2015-09. Pre-2015-09 is UNTESTED. Calm-crack days before
    2015-09 are counted but not evaluated.
- Signal convention = harness sleeve convention: the close of session t (VIX, VIX3M, QQQ 30d vol, SMA gap) decides the position
  traded at close t, earned from t+1. Same-day VIX close, no look-ahead. VIX / VIX3M from FRED files in
  vol_predict_2026_11 (VIXCLS.csv, VXVCLS.csv), forward-filled; QQQ 30d vol is the harness plain 30d (`sig['vol']`), the same
  number the live sleeve's stress floor uses.
- "Lagged" arm = the calm-condition inputs (VIX, VIX3M ratio, rv30, SMA gap) taken from t-1; state and sleeve conditions unchanged.
  C3 has no calm input so its lagged run equals its unlagged run.

## Calm hedge definition
Hedge share h of the BOOK (NAV). Active on day t only when ALL: effective state leveraged (eff == A, or eff == D and gate open),
the existing sleeve is not holding (sleeve weight == 0), and the arm's condition holds. Hedge weight = min(h, funding available).
- Funding F1 (main, "prorata"): all of h comes out of the risky legs (core, TQQQ, QLD, XLU) pro rata to their NAV weights; cash leg
  untouched. If risky NAV weight < h, hedge = risky weight.
- Funding F2 ("ontop"): first from the residual cash leg (BOXX) that is not used by the sleeve/QQQ cash legs, the rest from risky legs pro rata.
- Matched cash arm (MC): identical rule, funding, sizes and rebalance triggers; the hedge-leg return is replaced by the BOXX/cash return.
  Trade count and cost are therefore identical; only the instrument return differs. This is the main control.
- Matched de-lever by vol target: NOT done. In calm markets the vol-target multiplier is 1 (vol below 20%), so lowering the target
  cannot remove exposure where the hedge operates (same reason the VIX floor in the vol target could not bind). MC is the control.
- Hedge regime key: a hedge on/off change triggers a rebalance (counted in trades/yr).

## Arms (instrument VIXY unless stated)
- C1 calm by VIX: VIX close < T, T in {14,16,18,20}; h in {2,5,10}%.
- C2 calm by realized vol: QQQ rv30 < 20%; h in {2,5,10}%.
- C3 always on in leveraged states when the sleeve is off; h in {2,5,10}%.
- C4 C1 with T=18, h=5%, split by VIX/VIX3M: C4a ratio <= 0.90 (steep contango) vs C4b ratio > 0.90.
- C5 state A only and QQQ > 10% above its 200-day SMA; h in {5,10}%.
- Owner addendum (received before any run): VIXM as the hedge instrument for C1, C2, C3, C5 at book share h and at 2h, 2h capped at 20%
  of the book (h grid {2,5,10} -> VIXM shares {2,4,5,10,20}; C5: {5,10,20}); same MC control, same funding variants. VIXM
  data: data/vixm_daily.csv extended with the live_closes VIXM column (harness loader); its start date and last real print are
  printed in run.log. Window for VIXM = the same `real` / `vera` windows as VIXY (both start 2015-09). The instrument comparison
  uses identical windows. Only the extra hedge changes instrument; the sleeve stays VIXY 35%.
- Not a pass-bar change.

## Metrics (arm and its MC, each window)
CAGR, Sharpe (mean/sd, no rf, as harness), max DD, annual vol, share of days hedge held, average hedge weight (all days; and when on),
trades/yr, worst day, worst 5-day (compounded). Hedge-leg standalone P&L: sum of (hedge weight x instrument return) in % of NAV, total
and per year, split into calm-crack days (QQQ <= -3% with prior-day VIX < 20, list from vol_predict_2026_11/analyze.log) and other
days; also net of the cash carry the money would have earned. Mean book return on calm-crack days (n per window): Base / arm / MC.
Named episodes (day and following 5 sessions; 2024-07-24..08-05 as one span). Year by year arm minus MC (real), ex-2020, halves
(split at the window midpoint), block bootstrap (20-session circular blocks, 2,000 paths, paired with MC) of Sharpe difference
(one-sided P(diff <= 0)) and of max-DD difference. 5 bp one-way sensitivity on VIXY / VIXM hedge-and-sleeve trades (other legs 2 bp).
Per instrument: own mean return on calm-crack days, and annualized return on all other hedge-on days.

## PASS BAR (versus the arm's own matched cash arm; each funding variant and instrument judged separately)
An arm passes only if ALL hold:
1. EITHER (a) Sharpe(arm) >= Sharpe(MC) on both windows AND max DD at least 1.0 pp shallower than MC on `real` and not deeper on `vera`,
   OR (b) Sharpe(arm) > Sharpe(MC) on both windows;
2. the Sharpe criterion of the branch holds (>= for (a), > for (b)) in both halves and with 2020 removed, on both windows;
3. neighbours: for the 2-D C1 grid at least two 4-connected neighbour cells (adjacent T or adjacent h) also pass; for 1-D grids
   (h only) the cell must lie in a run of 3 consecutive passing cells; C4 (two cells) cannot satisfy this by construction and is
   reported "would pass except neighbours" if the rest holds;
4. bootstrap P(Sharpe diff <= 0) < 0.10 on at least one window.
Otherwise rejected. Results within bootstrap noise are called so.
Flag (not a pass): "insurance trade-off" = Sharpe lower than MC but, on `real`, max DD >= 1.0 pp shallower AND worst-5-day >= 0.5 pp better
than MC; reported with the annual cost (CAGR diff in pp, and hedge-leg net P&L in % NAV/yr).

## Addendum 2 (2026-11-17, written before run_oos.py was run): out-of-sample 2011-01-04..2015-09-02
Owner follow-up. New data in this folder: `vixy_yahoo_full.csv`, `vixm_yahoo_full.csv` (d, close_split_adj, adjclose; 2011-01-04..2026-11-16);
returns use close_split_adj. Nothing is re-tuned: thresholds, sizes, funding (pro-rata only) and rules are exactly those of the original run.
Same code path as run.py (copied into run_oos.py; run.py/run.log untouched). Output: run_oos.log.
- Arms (each against its matched cash arm): VIXY C1 T18 h5; VIXY C1 T20 h5; VIXM C1 T18 h10 (VIX-based cells); VIXY C5 h5; VIXM C5 h10; VIXM C5 h20
  (stretched-uptrend cells); context: VIXY C3 h5 (always on).
- Track: proxy panel only (the real track cannot start before 2015-11: SPMO). Legs on the proxy panel: core = QQQ price return + 0.6%/yr dividend accrual,
  TQQQ/QLD = synthetic 3x/2x of that with financing (T-bill + 0.3%) and expense ratios 0.84% / 0.95%, XLU = long-history XLU + 3% yield, cash/BOXX = 3-month T-bill
  accrual (DGS3MO), QQQ cash legs = QQQ. Hedge/sleeve instruments VIXY / VIXM are the real ETFs (split-adjusted closes).
- Baseline sleeve: VIXY 35% of the cash leg, same latch as "vera", now run with VIXY returns for the whole history (so it also operates in 2011-2015).
- Windows: (1) OOS 2011-01-04..2015-09-02 (indicators warmed up on earlier data; first return day 2011-01-05); (2) 2015-09-03..2026-11-16 (the original
  "vera" window, same code path, with the new return files; compared with the original vera numbers as a data check); (3) joined 2011-01-05..2026-11-16.
- Reported per arm and window: CAGR / Sharpe / max DD for arm and matched cash and the differences, share of days hedge on, hedge-leg P&L in % NAV/yr (total,
  calm-crack days, other days), instrument annualised return on hedge-on non-crack days, worst day and worst 5-day. Calm-crack days in the OOS window are listed with
  whether each hedge was on. Year-by-year arm minus matched cash 2011-2015 and the named OOS episodes (2011-08-04..08-10, 2012 full year, 2013-06, 2014-04-10,
  2014-10-09..10-15, 2015-08-21..08-26).
- READING RULE (OOS window alone, arm vs its matched cash; d = arm minus matched cash):
  * CONTRADICTED if dSharpe < -0.02, OR (dCAGR < -1.0 pp AND no drawdown benefit, i.e. max DD not shallower than matched cash by at least 0.1 pp). Checked first.
  * else CONFIRMED if dSharpe > 0 AND max DD not deeper than matched cash by more than 0.5 pp.
  * else INCONCLUSIVE.
  The number of calm-crack days inside the OOS window is stated with the verdict; if it is only a handful the window mostly measures the decay cost and the
  verdict is read that way. No bootstrap is part of this reading rule.
