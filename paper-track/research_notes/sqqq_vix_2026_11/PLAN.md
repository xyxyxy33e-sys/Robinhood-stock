# SQQQ by VIX level: pre-registered plan (2026-11-20, written before any arm was run)

Research only; nothing adopted; no existing file touched. Owner question: should the strategy hold SQQQ (-3x daily QQQ) during certain VIX levels?

## What is different from earlier SQQQ tests (so this is not a repeat)
- `deep_e_2026_11/hv_test.py` (2026-11-10, "#3 inverse QQQ in F"): PSQ/SQQQ as 10-25% of the CASH LEG, ONLY in state F (5.9% of real sessions), any VIX, no matched-cash control, synthetic -3x (QQQ price return, no real SQQQ).
- `sqqq_hedge_study.py` (2026-10-30): SQQQ in state F / E+F rows, synthetic.
- Here: SQQQ as a fixed share h of the BOOK, switched by VIX level (and a few other triggers), REAL SQQQ prices from 2010-02-11, a matched-cash control for every arm, four windows, a pre-registered pass bar. S4 (E/F states) overlaps the old tests by construction; it is run with the new controls and sized on the book.

## Engine
`harness_live.build('real'|'proxy', vixy_source='old')` = live design (L1 off, 2.0x cap, VIXY 35% sleeve, deep-E, VIX-panic leg), unchanged. Its weight matrix W (columns core, tqqq, qld, xlu, vixy, qqq, qqq, cash) is the base. An SQQQ column is added and run through `monte_carlo.run_strategy` (same rebalance rule: regime-key change, 5% drift band, zero-leg stub; cost 2 bp per side unless stated). The regime key gets +10^8 x (trigger on) so the book rebalances when the trigger flips; the matched-cash arm uses the same key, so trade counts are identical.

## Signal timing
Trigger at the close of session t uses VIX of session t (harness convention: weights set at close t, filled at close t, earned from t+1; same as the existing VIX-panic leg). Robustness: trigger lagged one more session (uses VIX of t-1, i.e. the strict "prior-day" reading).

## Funding
SQQQ weight x = h x on. Taken from the cash column of W (BOXX proper, i.e. the cash leg after the VIXY / deep-E / panic sleeves) first; if x exceeds it, the remainder is taken pro-rata from all other columns. Frequency and size of that shortfall are reported per arm (state A/B hold little cash, so it will be common there). Matched cash: identical funding, but x is added to the cash column instead of the SQQQ column (so equally de-risked, earns T-bill instead of -3x QQQ).

## SQQQ returns
Real SQQQ from Yahoo (`sqqq_yahoo_full.csv`, fetched 2026-11-20): primary = adjusted close (total return: SQQQ pays distributions), sensitivity = split-adjusted price only. Before 2010-02-12 (proxy panel only): synthetic = max(-3 x QQQ total return + 4 x T-bill - 0.95%/252, -99%), daily reset; no swap/borrow spread, no tracking noise, so it is a FLAGGED approximation (checked against real SQQQ over 2010-2026 in run.log). Total-return QQQ = panel price return + 0.6%/yr dividend accrual.

## Arms (h in {5%, 10%, 20%} of NAV for each; 39 arms, each with a matched-cash twin)
- S1 VIX bands (each separately): VIX<15, 15<=VIX<20, 20<=VIX<25, 25<=VIX<30, VIX>=30.
- S2 high VIX: VIX>=25, >=30, >=35.
- S3 calm and stretched: VIX<18 and QQQ more than 10% above its 200-day SMA (gap200 of the harness signal).
- S4 cash states: effective state E or F (any VIX); E or F with VIX>=25.
- S5 VIX rising: VIX up >=10% on the day (on that one close, held one session); VIX > VIX3M (VIX3M exists from 2007-12; the trigger is off before).
Reference rows: Base (no SQQQ).

## Windows
W1 real 2015-11-02..2026-11-19 (harness real track); W2 proxy 2001-01-02.. (synthetic SQQQ before 2010-02-12); W3 proxy 2010-02-11.. (real SQQQ throughout); W4 proxy 2010-02-11..2015-10-30 (prefix of W3, out of the window most rules were tuned on).

## Metrics
Per arm and window, arm vs matched cash: CAGR, Sharpe (mean/sd x sqrt252, no rf, project convention), max DD, worst day, worst 20 sessions (compounded), share of days on, average SQQQ weight (all days / while on), SQQQ leg P&L in % of NAV per year (target weight at t-1 x SQQQ return at t; gross and net of the T-bill the cash would have earned), split into days QQQ fell 2%+ (price return <= -2%) and all other days, SQQQ's own annualized return while held (arithmetic and compounded over held days). Year-by-year vs matched cash 2010-2026 (W3), 2020 and 2022 called out. Robustness: halves (midpoint of each window), one session of lag, 5 bp cost (all legs, arm and control), 20-session moving-block bootstrap, 2,000 paths (paired indices arm/control, seed fixed) of the Sharpe difference vs matched cash, P = share of paths with difference <= 0.

## Pass bar (an arm passes only if ALL hold, h/threshold exactly as defined above; otherwise REJECTED)
1. Sharpe higher than its matched cash on all four windows.
2. Max DD not deeper than matched cash by more than 0.5 pp on any window.
3. Sharpe difference > 0 in both halves of every window, and > 0 with calendar 2020 removed (days dropped from both series) in W1, W2, W3.
4. A neighbouring setting also has Sharpe > matched cash on all four windows. Neighbours: adjacent h in {5,10,20}; S1 adjacent band at the same h; S2 adjacent threshold at the same h; S4 and S5 their sibling trigger at the same h (S3 has h neighbours only).
5. Bootstrap P < 0.10 on at least one window.
Reading rule: a difference below about 0.02 Sharpe, or a bootstrap P above 0.10, is within noise. With 39 arms x 4 windows, a few P<0.10 cells are expected by chance; this is stated with the count.
Insurance flag (separate, not a pass): Sharpe lower than matched cash on at least one window, but on at least three of four windows max DD >= 1.0 pp shallower AND worst-20 >= 1.0 pp shallower than matched cash; reported with its CAGR cost per year vs matched cash and vs Base.
