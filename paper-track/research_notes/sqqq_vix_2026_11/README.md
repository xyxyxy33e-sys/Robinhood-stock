# SQQQ by VIX level (2026-11-20) - research only, nothing adopted, no existing file touched

Owner question: should the strategy hold SQQQ (-3x daily QQQ) during certain VIX levels? Files: `PLAN.md` (arms, windows and pass bar, written before any run),
`run.py` (everything, about 25 s), `run.log` (every table, verbatim), `sqqq_yahoo_full.csv` (Yahoo chart API, 2010-02-11..2026-11-20, close_split_adj + adjclose + dividends; fetched by `fetch_sqqq.py`),
`arm_table.md` (all 39 arms x 4 windows), `years_all_arms.csv` (arm minus matched cash by calendar year).

## Answer
**No. 0 of 39 arms pass the pre-registered bar; no VIX level is a good time to hold SQQQ.** Holding it at high VIX (>= 25, >= 30, >= 35, E/F with VIX >= 25) loses to (or ties) the same size held in cash on every window; VIX 20-25, 25-30 and the VIX-rising triggers are
mixed to negative and never close to passing. The two groups that look good on the 2015+ real track (VIX 15-20, and calm-and-stretched) fail only on the
out-of-sample 2010-2015 window, which is the same pattern as the calm VIXY hedge. Details below.

## What was run
- Engine `harness_live.build(..., vixy_source='old')` = live design (L1 off, 2.0x cap, VIXY 35% sleeve, deep-E, VIX-panic leg); baseline reproduced: real 2015-11-03..2026-11-19 **51.3% / 2.109 / -16.5%**, proxy 2001 34.2% / 1.487 / -22.1%.
  An SQQQ column is added to the harness weights and run through `monte_carlo.run_strategy` (same rebalance rule, 2 bp). The regime key includes the trigger, so trade counts match the control.
- 39 arms = 13 triggers x h in {5, 10, 20}% of NAV; each has a matched-cash twin (same trigger, funding, key, trades; the h share in T-bill instead of SQQQ).
- Funding: from the cash column (BOXX) first, then pro-rata from every other leg. **The cash leg is often too small**: held days partly funded pro-rata at h = 10% (real window): VIX<15 72%, VIX 15-20 41%, calm-stretched 51%,
  VIX-up 32%, VIX 20-25 10%, VIX>=25 about 1-2%, E/F 0%. State A holds almost no cash, so a calm-market SQQQ position is mostly funded by selling TQQQ/SPMO. At h = 20% the share of the SQQQ weight so funded is 28-41% (run.log section 2, `sf`).
- Timing: the trigger reads the VIX close of session t and trades at close t (harness convention, same as the VIX-panic leg); robustness lags it one more session.
- Windows: W1 real 2015-11-02..2026-11-19 (2,778 sessions, 180 days QQQ -2% or worse); W2 proxy 2001-01-02.. (6,508; synthetic SQQQ before 2010-02-12, real after); W3 proxy 2010-02-11.. (4,218; real SQQQ; 230 crash days);
  W4 proxy 2010-02-11..2015-10-30 (1,439; 50 crash days; exact prefix of W3).
- Baselines (no SQQQ): W1 51.3 / 2.109 / -16.5; W2 34.2 / 1.487 / -22.1; W3 44.8 / 1.768 / -20.1; W4 32.0 / 1.314 / -16.4 (CAGR % / Sharpe / max DD %).
- Not a repeat of 2026-11-10 `hv_test` (#3, SQQQ 10-25% of the CASH LEG in state F only, any VIX, no matched-cash control, synthetic SQQQ, compared with base) nor the 2026-10-30 `sqqq_hedge_study` (F/E+F rows). Here: share of the book, VIX-triggered, real SQQQ,
  matched cash, four windows. The state-based arm S4 overlaps those and agrees with them (below).

## 0. Data check (run.log section 0)
Real SQQQ total return (adjclose) 2010-02-12..2026-11-19, 4,218 sessions, no panel date missing. Against synthetic (-3 x QQQ total return + 4 x T-bill - 0.95%/yr, daily reset): mean daily difference **-0.87 bp = -2.20%/yr**
(real is worse; sd of the daily difference 0.217%, correlation 0.9985); CAGR real -51.6% vs synthetic -50.7%. Against a bare -3 x QQQ total return: +1.24 bp/day = +3.14%/yr (the T-bill credit on 4x NAV and the fee roughly cancel: the pure
-3x is -53.3% CAGR). Price-only SQQQ (no distributions) is a further -1.7%/yr below adjclose. By year the real-minus-synthetic gap is -0.04 to -6.7%/yr; the large ones are 2020 (-6.7), 2022 (-4.8; real +82.4% vs synthetic +89.7%), 2012 (-3.8).
So **the pre-2010 synthetic is about 2%/yr generous to SQQQ** (no swap/borrow spread, no tracking noise): FLAGGED approximation, used only in W2 for 2001-2010-02. Early split-adjusted Yahoo prices are quantised
(32 panel days show exactly 0.00% real return, e.g. 2013-10-02, 2024-04-08, on days QQQ moved <0.05%), so single early daily returns are noisy by about 0.01-0.03%; unbiased. The 2011-01-03 session is not in the QQQ file; the panel's 2011-01-04 return spans both days for QQQ and SQQQ. 2026-11-20 (partial bar) is dropped.

## 1. Arms vs matched cash, four windows (CAGR % / Sharpe / max DD %, arm vs matched cash; dSh = arm minus control)
Full table with all 39 arms: `arm_table.md`; per-window detail with worst day, worst 20, average weights: run.log section 1. Selected (h = 10%; dSh W1 / W2 / W3 / W4; dCAGR W1 pp; max-DD difference W1, W4 pp, + = arm shallower):

| trigger (h 10%) | days on W1 | dSh W1 | W2 | W3 | W4 | dCAGR W1 | dDD W1 / W4 |
|---|---|---|---|---|---|---|---|
| S1 VIX<15 | 34% | -0.010 | +0.025 | -0.000 | +0.002 | -2.39 | +0.2 / +0.0 |
| S1 VIX 15-20 | 36% | **+0.121** | +0.037 | +0.059 | **-0.048** | +0.37 | +2.6 / +1.2 |
| S1 VIX 20-25 | 16% | -0.028 | +0.024 | -0.024 | -0.031 | -1.99 | -0.4 / +0.0 |
| S1 VIX 25-30 | 8% | -0.027 | +0.003 | -0.003 | +0.032 | -1.26 | 0.0 / +0.1 |
| S1 / S2 VIX >= 30 | 5.5% | -0.010 | -0.043 | -0.028 | -0.045 | -2.24 | 0.0 / -3.9 |
| S2 VIX >= 25 | 14% | -0.040 | -0.045 | -0.033 | -0.012 | -3.57 | 0.0 / -1.3 |
| S2 VIX >= 35 | 2% | -0.022 | -0.028 | -0.041 | -0.062 | -2.11 | 0.0 / -5.2 |
| S3 VIX<18 and QQQ >10% over 200d | 28% | +0.057 | +0.034 | +0.031 | -0.009 | +0.33 | +0.9 / +0.4 |
| S4 state E/F | 12% | -0.016 | +0.020 | -0.043 | -0.079 | -1.70 | 0.0 / -4.4 |
| S4 E/F and VIX>=25 | 6.5% | -0.011 | -0.007 | -0.029 | -0.047 | -1.73 | 0.0 / -2.5 |
| S5 VIX up >=10% on the day | 9% | -0.028 | -0.030 | -0.017 | +0.007 | -2.32 | -0.3 / -0.4 |
| S5 VIX > VIX3M | 7% | -0.007 | -0.010 | -0.005 | +0.011 | -2.23 | 0.0 / +0.4 |

(S1 VIX>=30 and S2 VIX>=30 are the same trigger. VIX3M starts 2007-12, so S5 VIX>VIX3M is off before then in W2.) Max DD in the high-VIX arms gets WORSE, not better: W4 S2 VIX>=30 h20 -23.8% vs -16.4% (control), S2 VIX>=35 h20 -26.9%; W3 S4 E/F h20 -24.9% vs -20.1%:
a held -3x position meets the +10% rebounds that follow VIX 30+ closes (the vol_predict finding: mean next day +0.28%, +3% days outnumber -3% days 91 to 66).
Differences below about 0.02 Sharpe are within noise (bootstrap 90% intervals are +-0.02 to +-0.04 for h5 on W3/W2, wider on W1/W4).

## 2. The SQQQ leg itself (% of NAV per year; crash = QQQ -2% or worse; net = after the T-bill carry the cash would have earned; own = SQQQ return while held, annualised arithmetic / compounded over held days)
Real window W1 (h = 10%; the P&L scales linearly with h):

| trigger | crash days | other days | net of carry | crash days held / all | own return while held |
|---|---|---|---|---|---|
| VIX<15 | +1.00 | -2.61 | -1.69 | 15/180 | -47% / -42% |
| VIX 15-20 | +4.41 | -4.23 | +0.08 | 58/180 | +5% / -11% |
| VIX 20-25 | +3.91 | -5.18 | -1.31 | 50/180 | -78% / -65% |
| VIX 25-30 | +2.53 | -3.32 | -0.80 | 28/180 | -97% / -76% |
| VIX >= 30 | +3.06 | -4.54 | -1.48 | 29/180 | -266% / -98% |
| VIX >= 25 | +5.59 | -7.86 | -2.28 | 57/180 | -166% / -91% |
| VIX >= 35 | +1.38 | -2.86 | -1.49 | 10/180 | -678% / -100% |
| calm and stretched | +1.74 | -1.49 | +0.15 | 23/180 | +9% / -1% |
| E/F | +5.04 | -6.04 | -1.02 | 55/180 | -86% / -79% |
| E/F and VIX>=25 | +3.35 | -4.41 | -1.08 | 33/180 | -163% / -93% |
| VIX up >=10% | +1.41 | -2.89 | -1.51 | 15/180 | -168% / -88% |
| VIX > VIX3M | +3.94 | -5.43 | -1.51 | 38/180 | -201% / -95% |

The leg is a loser everywhere except VIX 15-20 and calm-and-stretched (about zero net). It pays on the crash days it is held for but loses more on the days around them; at VIX >= 30 it loses 98% of its value compounded over the held days.
W3 and W4 (SQQQ own return while held, compounded): VIX 15-20 -30% (W3) and -55% (W4); calm-stretched -10% and -29%; the leg is clearly negative before 2015-11. W4 net of carry: VIX 15-20 h10 -2.66 %/yr, calm-stretched h10 -0.64 %/yr.

## 3. Verdicts (pre-registered bar, run.log section 4)
Criteria: c1 Sharpe > control on all four windows; c2 max DD not >0.5 pp deeper on any window; c3 both halves of every window and ex-2020 (W1-W3) positive; c4 a neighbouring setting also meets c1; c5 bootstrap P < 0.10 on at least one window.
**All 39 REJECTED.** Only one arm meets c1 (S1 VIX<15 h5, dSh +0.001 / +0.014 / +0.004 / +0.006: noise; costs -1.07, -0.44, -0.92, -0.64 pp CAGR vs control; fails c3 and c4).

| family | verdict | why |
|---|---|---|
| S1 VIX<15 (h5/10/20) | rejected | Sharpe equal to control within noise (-0.05 to +0.03), CAGR -0.4 to -4.7 pp vs control; SQQQ loses 47%/yr while held |
| S1 VIX 15-20 | rejected, closest of the VIX bands | strongly positive W1 (+0.067 / +0.121 / +0.179), W3 (+0.034 / +0.059 / +0.073), mildly W2; **negative on W4** (-0.020 / -0.048 / -0.135, CAGR -1.5 / -3.2 / -6.2 pp vs control; bootstrap P(diff<=0) 0.78 / 0.82 / 0.89); also fails first half of W2 and both halves of W4. h5 fails c1 and c3 only. h20 formally trips the insurance flag, see below |
| S1 VIX 20-25 | rejected | negative on W1, W3, W4; 2020 -4.1 / -7.9 / -15.8 pp (h5/10/20) vs control, 2022 +2.9 / +5.8 / +11.9 |
| S1 VIX 25-30 | rejected | zero to slightly negative on W1-W3, positive only on W4 (+0.017 / +0.032 / +0.058, a 5%-of-days sample with 0.36 pp worst day), h20 negative on W1 and W2 |
| S1 VIX>=30, S2 VIX>=25 / >=30 / >=35 | rejected, clearly | Sharpe below control on every window at every size (except a +0.000 tie on W1 at h5); max DD deeper by up to 10.5 pp; beat the control in 0 of 17 calendar years; 2020 -6.1 to -25.4 pp |
| S3 calm and stretched | rejected on W4 only | W1 +0.032 / +0.057 / +0.077, W2 +0.018 / +0.034 / +0.052, W3 +0.018 / +0.031 / +0.039, W4 -0.002 / -0.009 / -0.026. h5 on W4 is -0.002 (noise) but both halves of W4 are below zero by tiny amounts, so the strict bar fails; c4 fails because no neighbour clears all four windows |
| S4 E/F; E/F and VIX>=25 | rejected | W1 about 0 to -0.1, W3 -0.011 to -0.121, W4 -0.022 to -0.170; 2020 -2.6 to -12.0 pp (beat the control in 0-2 of 17 years). Agrees with the 2026-11-10 `hv_test` (SQQQ 10% of cash in F: real 46.2% vs 46.6%, Sharpe 1.904 vs 1.928) |
| S5 VIX up >=10%; VIX > VIX3M | rejected | dSh -0.094 to +0.011 (all within about 0.01 at h5 and negative at h20), no benefit anywhere; the VIX-up trigger holds 1 session and costs 1.1-4.6 pp CAGR |

Bootstrap (20-session blocks, 2,000 paths, P = share of paths with Sharpe difference <= 0): 16 of 156 arm-window cells have P < 0.10 in the arm's favour and 35 have P > 0.90 against it. The significant cells are almost all VIX 15-20 and calm-stretched on W1 (P 0.003-0.048 and 0.016-0.106),
and the same two families on W2/W3; all arms share the same crash events, so these are not independent tests and there is no multiple-testing correction.

## 4. Robustness of the best arms (run.log sections 3, 8, 9)
dSh vs matched cash: window, half 1 / half 2, ex-2020, one session of lag, 5 bp cost, price-only SQQQ:
- **S1 VIX 15-20 h5**: W1 +0.067 (halves +0.071 / +0.061, ex-2020 +0.073, lag +0.063, 5 bp +0.062, price-only +0.064); W2 +0.022 (halves -0.001 / +0.046); W3 +0.034 (+0.007 / +0.063; lag +0.030); W4 -0.020 (+0.002 / -0.038). h10: W1 +0.121 (+0.130 / +0.107), W2 +0.037 (-0.009 / +0.084), W3 +0.059 (+0.006 / +0.116), W4 -0.048 (-0.008 / -0.084).
  The gain is in the second half of each window and in 2015-11 on; lagging the trigger a session or adding 5 bp barely changes it.
- **S3 h5 / h10 / h20**: W1 +0.032 / +0.057 / +0.077 (halves h10 +0.045 / +0.065; ex-2020 +0.062; lag **+0.080**, 5 bp +0.052); W2 +0.018 / +0.034 / +0.052; W3 +0.018 / +0.031 / +0.039 (lag +0.058 for h10); W4 -0.002 / -0.009 / -0.026 (lag +0.014 / +0.027 / +0.042). One session of lag helps S3 (the VIX-below-18 test is cleaner on the prior close); the lagged version was not pre-registered as an arm.
- Post-hoc split (not part of the bar), dSh / dCAGR pp for S1 15-20 h10 and S3 h10: 2001-2009 (synthetic SQQQ) +0.003 / -0.36 and +0.046 / +0.91; 2010-02..2015-10 -0.048 / -3.17 and -0.009 / -0.78; 2015-11..2020 +0.128 / +1.36 and +0.040 / +0.23; 2021-2026 +0.107 / -0.38 and +0.068 / +0.53.
  VIX 15-20 helps only after 2015-11 (the years the owner's rules were mostly tuned on); in 2001-2009 it is flat and in 2010-2015 it is negative. S3 is positive in 2001-2009, flat-to-slightly-negative 2010-2015, positive after.
- **Year by year (W3, arm minus matched cash, pp)**: VIX 15-20 h5 / h10 / h20 beat the control in only 3 of 17 years (2018 +4.56 / +8.92 / +17.63, 2022 +2.14 / +4.32 / +8.84, 2026 +3.29 / +6.40 / +12.58) and lose small amounts in the rest: 2020 -0.37 / -0.77 / -1.63, 2023 -5.55 / -10.73 / -20.26, 2013 -3.59 / -7.10 / -13.94, 2010 -2.14 / -4.59 / -8.98, 2021 -2.46 / -4.13 / -7.97.
  S3 h5 / h10 / h20 beat it in 9 / 8 / 8 of 17 years; 2020 -0.25 / -0.51 / -1.00, 2022 +0.02 / +0.05 / +0.10 (it is not on in 2022: QQQ below its 200-day), best 2025 +2.25 / +4.52 / +9.16, worst 2023 -2.35 / -3.80 (2013) / -9.39. High-VIX arms: 2020 is the worst year for most of them (-6 to -25 pp), 2022 -0.4 to -4.8 pp.
- Funding caveat for S1 VIX 15-20 and S3: part of each position is pro-rata funded from risky legs, so the "SQQQ in place of cash" matched control also de-risks the same amount; the comparison is like-for-like but the real-world position is a partial short-QQQ overlay on a TQQQ book.

## 5. Insurance trade-off flag (separate from the bar)
Rule: Sharpe below control on at least one window, but max DD and worst-20 each at least 1.0 pp shallower on at least three of four windows. **Only S1 VIX 15-20 h20 trips it** (the h5 and h10 versions have no Sharpe shortfall except W4 and do not reach 1 pp on worst-20 in enough windows):
W1 max DD -12.2% vs -14.4% (control), worst 20 +3.08 pp; W2 -20.5% vs -21.9%, worst 20 +1.23 pp; W3 -17.2% vs -19.9%, +1.61 pp; but W4 -15.2% vs -14.8% and Sharpe -0.135. Cost vs control: -1.5 pp CAGR W2, -2.0 pp W3, -6.2 pp W4, but +0.7 pp W1; vs Base (no SQQQ): W1 +0.2 pp, W2 -2.5, W3 -3.3. About 28% of its SQQQ weight (W1) is funded by selling risky legs on half of its held days. Not recommended on this evidence: the benefit is real only on 2015-11+.

## What this means
- High VIX is the wrong time for SQQQ in this design: volatility is highest right before rebounds, and the design already de-risks there (states E/F, the D ladder) so the extra -3x short adds rebound risk on top of a book that is mostly cash.
- The two apparent winners are calm-market overlays (VIX 15-20; calm-stretched) and behave like the VIXY calm hedge: positive on 2015-11+ and in 2001-2009 (S3 only), negative or flat out of sample on 2010-2015, small yearly bleed in calm bull years (2013, 2021, 2023), large payoffs in a few episodes (2018, 2022, 2026). Under the owner's bar they are rejected.
- S3 h5 is the nearest thing to a candidate (positive Sharpe on three windows, within noise on W4, no deeper drawdown, positive CAGR vs control on W1/W2, 9 of 17 years better than control), but its Sharpe gain is +0.018 to +0.032 and W4 is the only window that does not agree; a follow-up would need a pre-registered one-session-lag rule and a larger out-of-sample (the 2001-2009 synthetic period is not independent evidence as the SQQQ there is synthetic).

## Anything wrong, skipped or approximate
- Pre-2010 SQQQ is synthetic (about 2%/yr generous vs real SQQQ); W2 mixes it with real SQQQ from 2010-02-12.
- SQQQ returns use adjclose (distributions included); price-only is a sensitivity (results move by up to 0.015 Sharpe for the best arms, e.g. S1 15-20 h20 W1 +0.168 vs +0.179, S3 h20 W1 +0.063 vs +0.077).
- Proxy windows use the harness proxy panel (QQQ core, synthetic TQQQ/QLD), VIXY sleeve from 2011-01-04 (`vixy_source='old'`: vixy_daily.csv + live_closes through 2026-11-19, the harness_live default 'full' file ends earlier). W3 and W4 start at SQQQ's first session, not 2010-01.
- SQQQ P&L and weights are TARGET weights (the engine lets holdings drift inside the 5% band; reconciliation of arm-minus-control daily return vs weight x (SQQQ - cash) has correlation 0.998).
- Matched cash only removes the same dollar exposure; it is not vol-target matched. The 5 bp test applies 5 bp to every trade in arm and control, so it barely separates them; an SQQQ-leg-only 5 bp cost was not run in the engine; from the trigger flip counts (run.log section 7: VIX 15-20 32 flips/yr, calm-stretched 17, VIX-up 40, high-VIX 3-10, E/F 4) it would cost 0.02-0.20% of NAV per year at h = 10%, which does not change any verdict.
- Pass-bar choices that matter: halves tested in all four windows (8 checks), neighbours must meet c1; a looser reading of c3 would not rescue any arm except possibly S3 h5/S1 VIX 15-20 h5, which still fail c1 (W4).
- Triggers use same-day close VIX with a same-close fill (the harness convention); in practice a 15:50 fill carries the usual few-bp slippage and the VIX close is not final at 15:50. Lag-1 results are in run.log.
- S1 VIX>=30 and S2 VIX>=30 are identical rows; the 5%-VIX-up trigger is a one-session hold.
- No taxes, no borrow/margin, no intraday path (SQQQ daily reset only); leveraged-ETF distributions are in adjclose only.

## Arm table, all 39 arms (CAGR % / Sharpe / max DD %; arm vs matched cash; share of days on)
| arm | W1 real 2015-11.. | W2 proxy 2001.. | W3 proxy 2010-02.. | W4 proxy 2010-02..2015-10 |
|---|---|---|---|---|
| Base (no SQQQ) | 51.3 / 2.109 / -16.5 | 34.2 / 1.487 / -22.1 | 44.8 / 1.768 / -20.1 | 32.0 / 1.314 / -16.4 |
| S1 VIX<15 h5 | 50.2 / 2.110 / -16.5 vs 51.3 / 2.109 / -16.6; on 34% | 33.8 / 1.503 / -22.1 vs 34.2 / 1.488 / -22.1; on 32% | 43.8 / 1.773 / -20.1 vs 44.7 / 1.769 / -20.1; on 34% | 31.4 / 1.324 / -16.3 vs 32.0 / 1.318 / -16.3; on 35% |
| S1 VIX<15 h10 | 48.8 / 2.101 / -16.4 vs 51.2 / 2.111 / -16.6; on 34% | 33.2 / 1.516 / -22.1 vs 34.1 / 1.491 / -22.1; on 32% | 42.6 / 1.771 / -20.1 vs 44.7 / 1.771 / -20.1; on 34% | 30.6 / 1.325 / -16.2 vs 32.1 / 1.323 / -16.3; on 35% |
| S1 VIX<15 h20 | 44.7 / 2.047 / -16.1 vs 49.4 / 2.098 / -16.4; on 34% | 31.5 / 1.532 / -22.1 vs 33.4 / 1.503 / -22.1; on 32% | 39.4 / 1.753 / -20.1 vs 43.4 / 1.778 / -20.1; on 34% | 29.0 / 1.351 / -16.2 vs 31.8 / 1.352 / -16.2; on 35% |
| S1 15-20 h5 | 51.6 / 2.181 / -15.1 vs 51.4 / 2.114 / -16.4; on 36% | 33.9 / 1.511 / -21.8 vs 34.2 / 1.489 / -22.2; on 31% | 44.3 / 1.806 / -19.3 vs 44.8 / 1.773 / -20.0; on 37% | 30.5 / 1.302 / -15.4 vs 32.1 / 1.321 / -16.1; on 39% |
| S1 15-20 h10 | 51.7 / 2.242 / -13.5 vs 51.3 / 2.121 / -16.1; on 36% | 33.4 / 1.526 / -21.4 vs 34.1 / 1.489 / -22.2; on 31% | 43.7 / 1.835 / -18.6 vs 44.6 / 1.775 / -20.0; on 37% | 28.6 / 1.270 / -14.7 vs 31.8 / 1.318 / -15.9; on 39% |
| S1 15-20 h20 | 51.5 / 2.339 / -12.2 vs 50.8 / 2.160 / -14.4; on 36% | 31.7 / 1.523 / -20.5 vs 33.2 / 1.490 / -21.9; on 31% | 41.5 / 1.860 / -17.2 vs 43.5 / 1.787 / -19.9; on 37% | 23.6 / 1.152 / -15.2 vs 29.9 / 1.287 / -14.8; on 39% |
| S1 20-25 h5 | 50.3 / 2.100 / -16.7 vs 51.3 / 2.109 / -16.5; on 16% | 34.1 / 1.502 / -21.2 vs 34.2 / 1.486 / -22.2; on 18% | 43.8 / 1.759 / -19.3 vs 44.7 / 1.768 / -20.0; on 15% | 31.2 / 1.300 / -16.2 vs 32.0 / 1.314 / -16.3; on 14% |
| S1 20-25 h10 | 49.3 / 2.081 / -16.9 vs 51.3 / 2.109 / -16.5; on 16% | 34.1 / 1.512 / -20.2 vs 34.2 / 1.487 / -22.1; on 18% | 42.9 / 1.745 / -18.7 vs 44.7 / 1.768 / -20.0; on 15% | 30.4 / 1.285 / -16.2 vs 32.0 / 1.315 / -16.3; on 14% |
| S1 20-25 h20 | 46.7 / 1.997 / -17.3 vs 50.8 / 2.102 / -16.5; on 16% | 33.9 / 1.500 / -19.1 vs 34.0 / 1.489 / -21.8; on 18% | 40.6 / 1.687 / -18.2 vs 44.3 / 1.764 / -19.9; on 15% | 28.5 / 1.237 / -16.6 vs 31.7 / 1.314 / -15.9; on 14% |
| S1 25-30 h5 | 50.7 / 2.101 / -16.5 vs 51.4 / 2.110 / -16.5; on 8% | 33.9 / 1.489 / -21.9 vs 34.2 / 1.486 / -22.1; on 9% | 44.5 / 1.769 / -19.4 vs 44.8 / 1.768 / -20.1; on 7% | 32.3 / 1.331 / -16.3 vs 32.0 / 1.314 / -16.4; on 5% |
| S1 25-30 h10 | 50.1 / 2.083 / -16.5 vs 51.4 / 2.109 / -16.5; on 8% | 33.7 / 1.488 / -21.6 vs 34.2 / 1.485 / -22.1; on 9% | 44.2 / 1.765 / -18.7 vs 44.8 / 1.768 / -20.1; on 7% | 32.7 / 1.347 / -16.3 vs 32.0 / 1.315 / -16.4; on 5% |
| S1 25-30 h20 | 48.6 / 2.019 / -16.5 vs 51.1 / 2.105 / -16.5; on 8% | 32.8 / 1.449 / -21.1 vs 34.0 / 1.481 / -22.1; on 9% | 43.6 / 1.740 / -19.6 vs 44.6 / 1.765 / -20.1; on 7% | 33.4 / 1.373 / -16.1 vs 32.0 / 1.316 / -16.3; on 5% |
| S1 VIX>=30 h5 | 50.2 / 2.110 / -16.5 vs 51.4 / 2.110 / -16.5; on 6% | 33.0 / 1.471 / -20.0 vs 34.2 / 1.487 / -22.1; on 9% | 43.7 / 1.758 / -20.0 vs 44.8 / 1.769 / -20.0; on 6% | 31.0 / 1.294 / -18.3 vs 32.0 / 1.315 / -16.4; on 7% |
| S1 VIX>=30 h10 | 49.1 / 2.100 / -16.5 vs 51.4 / 2.110 / -16.5; on 6% | 31.8 / 1.443 / -20.2 vs 34.2 / 1.487 / -22.1; on 9% | 42.6 / 1.740 / -20.2 vs 44.8 / 1.769 / -20.0; on 6% | 30.1 / 1.270 / -20.2 vs 32.0 / 1.315 / -16.4; on 7% |
| S1 VIX>=30 h20 | 47.0 / 2.037 / -16.5 vs 51.3 / 2.109 / -16.5; on 6% | 29.4 / 1.348 / -23.8 vs 34.2 / 1.486 / -22.1; on 9% | 40.6 / 1.683 / -23.8 vs 44.7 / 1.768 / -20.0; on 6% | 28.3 / 1.215 / -23.8 vs 32.0 / 1.315 / -16.4; on 7% |
| S2 VIX>=25 h5 | 49.5 / 2.098 / -16.5 vs 51.3 / 2.109 / -16.5; on 14% | 32.6 / 1.472 / -19.4 vs 34.2 / 1.486 / -22.1; on 18% | 43.4 / 1.757 / -19.4 vs 44.7 / 1.768 / -20.1; on 13% | 31.4 / 1.311 / -17.0 vs 32.0 / 1.314 / -16.4; on 12% |
| S2 VIX>=25 h10 | 47.7 / 2.068 / -16.5 vs 51.3 / 2.108 / -16.5; on 14% | 31.2 / 1.441 / -18.8 vs 34.2 / 1.486 / -22.1; on 18% | 42.0 / 1.734 / -18.8 vs 44.7 / 1.768 / -20.1; on 13% | 30.7 / 1.302 / -17.7 vs 32.0 / 1.315 / -16.4; on 12% |
| S2 VIX>=25 h20 | 44.3 / 1.943 / -16.5 vs 51.1 / 2.103 / -16.5; on 14% | 28.1 / 1.310 / -20.3 vs 34.0 / 1.481 / -22.1; on 18% | 39.4 / 1.653 / -19.6 vs 44.6 / 1.764 / -20.1; on 13% | 29.5 / 1.271 / -19.4 vs 32.0 / 1.316 / -16.3; on 12% |
| S2 VIX>=30 h5 | 50.2 / 2.110 / -16.5 vs 51.4 / 2.110 / -16.5; on 6% | 33.0 / 1.471 / -20.0 vs 34.2 / 1.487 / -22.1; on 9% | 43.7 / 1.758 / -20.0 vs 44.8 / 1.769 / -20.0; on 6% | 31.0 / 1.294 / -18.3 vs 32.0 / 1.315 / -16.4; on 7% |
| S2 VIX>=30 h10 | 49.1 / 2.100 / -16.5 vs 51.4 / 2.110 / -16.5; on 6% | 31.8 / 1.443 / -20.2 vs 34.2 / 1.487 / -22.1; on 9% | 42.6 / 1.740 / -20.2 vs 44.8 / 1.769 / -20.0; on 6% | 30.1 / 1.270 / -20.2 vs 32.0 / 1.315 / -16.4; on 7% |
| S2 VIX>=30 h20 | 47.0 / 2.037 / -16.5 vs 51.3 / 2.109 / -16.5; on 6% | 29.4 / 1.348 / -23.8 vs 34.2 / 1.486 / -22.1; on 9% | 40.6 / 1.683 / -23.8 vs 44.7 / 1.768 / -20.0; on 6% | 28.3 / 1.215 / -23.8 vs 32.0 / 1.315 / -16.4; on 7% |
| S2 VIX>=35 h5 | 50.4 / 2.104 / -16.5 vs 51.4 / 2.110 / -16.5; on 2% | 33.5 / 1.478 / -20.1 vs 34.2 / 1.487 / -22.2; on 5% | 43.7 / 1.752 / -20.1 vs 44.8 / 1.769 / -20.1; on 2% | 30.9 / 1.285 / -19.0 vs 32.0 / 1.315 / -16.4; on 3% |
| S2 VIX>=35 h10 | 49.3 / 2.088 / -16.5 vs 51.4 / 2.110 / -16.5; on 2% | 32.7 / 1.459 / -21.6 vs 34.2 / 1.487 / -22.2; on 5% | 42.6 / 1.728 / -21.6 vs 44.8 / 1.769 / -20.1; on 2% | 29.8 / 1.253 / -21.6 vs 32.0 / 1.315 / -16.4; on 3% |
| S2 VIX>=35 h20 | 47.1 / 2.023 / -16.9 vs 51.4 / 2.109 / -16.5; on 2% | 31.0 / 1.396 / -26.9 vs 34.2 / 1.487 / -22.2; on 5% | 40.4 / 1.662 / -26.9 vs 44.8 / 1.769 / -20.1; on 2% | 27.5 / 1.179 / -26.9 vs 32.0 / 1.315 / -16.4; on 3% |
| S3 calm&stretched h5 | 51.4 / 2.138 / -16.1 vs 51.2 / 2.107 / -16.6; on 29% | 34.3 / 1.504 / -22.1 vs 34.1 / 1.486 / -22.1; on 20% | 44.6 / 1.783 / -20.1 vs 44.6 / 1.766 / -20.1; on 26% | 31.5 / 1.310 / -16.1 vs 31.9 / 1.312 / -16.3; on 22% |
| S3 calm&stretched h10 | 51.5 / 2.167 / -15.7 vs 51.2 / 2.109 / -16.6; on 29% | 34.4 / 1.520 / -22.1 vs 34.1 / 1.486 / -22.1; on 20% | 44.5 / 1.798 / -20.1 vs 44.6 / 1.767 / -20.1; on 26% | 31.1 / 1.303 / -15.9 vs 31.8 / 1.313 / -16.3; on 22% |
| S3 calm&stretched h20 | 50.9 / 2.194 / -15.5 vs 50.5 / 2.117 / -15.7; on 29% | 34.4 / 1.542 / -22.1 vs 33.8 / 1.490 / -22.1; on 20% | 43.7 / 1.808 / -20.1 vs 43.9 / 1.769 / -20.1; on 26% | 29.8 / 1.283 / -15.4 vs 31.3 / 1.309 / -16.0; on 22% |
| S4 E/F h5 | 50.5 / 2.109 / -16.5 vs 51.3 / 2.109 / -16.5; on 12% | 34.3 / 1.506 / -20.8 vs 34.2 / 1.487 / -22.1; on 17% | 43.7 / 1.751 / -20.8 vs 44.8 / 1.768 / -20.1; on 11% | 30.7 / 1.277 / -18.6 vs 32.0 / 1.314 / -16.4; on 10% |
| S4 E/F h10 | 49.6 / 2.093 / -16.5 vs 51.3 / 2.109 / -16.5; on 12% | 34.4 / 1.507 / -21.6 vs 34.2 / 1.487 / -22.1; on 17% | 42.7 / 1.725 / -21.6 vs 44.8 / 1.768 / -20.1; on 11% | 29.4 / 1.235 / -20.8 vs 32.0 / 1.314 / -16.4; on 10% |
| S4 E/F h20 | 48.1 / 2.013 / -17.3 vs 51.3 / 2.109 / -16.5; on 12% | 34.6 / 1.461 / -24.9 vs 34.2 / 1.487 / -22.1; on 17% | 40.8 / 1.647 / -24.9 vs 44.7 / 1.768 / -20.1; on 11% | 27.0 / 1.144 / -24.9 vs 32.0 / 1.314 / -16.4; on 10% |
| S4 E/F & VIX>=25 h5 | 50.4 / 2.110 / -16.5 vs 51.3 / 2.109 / -16.5; on 7% | 33.7 / 1.488 / -20.0 vs 34.2 / 1.487 / -22.1; on 9% | 43.9 / 1.757 / -20.0 vs 44.8 / 1.768 / -20.1; on 6% | 31.2 / 1.293 / -17.6 vs 32.0 / 1.314 / -16.4; on 5% |
| S4 E/F & VIX>=25 h10 | 49.6 / 2.098 / -16.5 vs 51.3 / 2.109 / -16.5; on 7% | 33.4 / 1.481 / -19.9 vs 34.2 / 1.487 / -22.1; on 9% | 43.0 / 1.739 / -19.9 vs 44.8 / 1.768 / -20.1; on 6% | 30.3 / 1.268 / -18.9 vs 32.0 / 1.314 / -16.4; on 5% |
| S4 E/F & VIX>=25 h20 | 48.1 / 2.036 / -16.5 vs 51.3 / 2.109 / -16.5; on 7% | 32.6 / 1.422 / -21.1 vs 34.2 / 1.487 / -22.1; on 9% | 41.5 / 1.682 / -21.1 vs 44.7 / 1.768 / -20.1; on 6% | 28.8 / 1.212 / -21.1 vs 32.0 / 1.314 / -16.4; on 5% |
| S5 VIX up>=10% h5 | 50.1 / 2.096 / -16.7 vs 51.3 / 2.106 / -16.6; on 9% | 33.4 / 1.474 / -22.7 vs 34.2 / 1.486 / -22.5; on 8% | 44.0 / 1.763 / -20.1 vs 44.8 / 1.768 / -20.1; on 9% | 31.9 / 1.324 / -16.4 vs 32.1 / 1.320 / -16.3; on 9% |
| S5 VIX up>=10% h10 | 48.9 / 2.077 / -16.9 vs 51.2 / 2.105 / -16.6; on 9% | 32.7 / 1.456 / -22.9 vs 34.2 / 1.486 / -22.5; on 8% | 43.1 / 1.752 / -20.0 vs 44.8 / 1.769 / -20.1; on 9% | 31.6 / 1.329 / -16.7 vs 32.2 / 1.322 / -16.3; on 9% |
| S5 VIX up>=10% h20 | 46.2 / 2.008 / -17.1 vs 50.8 / 2.102 / -16.6; on 9% | 30.9 / 1.402 / -23.4 vs 33.9 / 1.483 / -22.5; on 8% | 41.1 / 1.712 / -20.0 vs 44.5 / 1.769 / -20.1; on 9% | 31.1 / 1.333 / -17.1 vs 32.2 / 1.330 / -16.0; on 9% |
| S5 VIX>VIX3M h5 | 50.2 / 2.112 / -16.5 vs 51.3 / 2.109 / -16.5; on 7% | 33.7 / 1.485 / -22.1 vs 34.2 / 1.488 / -22.1; on 5% | 44.0 / 1.770 / -20.0 vs 44.8 / 1.769 / -20.0; on 8% | 31.9 / 1.326 / -16.1 vs 32.1 / 1.318 / -16.4; on 8% |
| S5 VIX>VIX3M h10 | 49.1 / 2.102 / -16.5 vs 51.3 / 2.108 / -16.5; on 7% | 33.2 / 1.479 / -22.1 vs 34.2 / 1.489 / -22.1; on 5% | 43.2 / 1.765 / -19.9 vs 44.8 / 1.771 / -20.0; on 8% | 31.8 / 1.334 / -15.9 vs 32.2 / 1.323 / -16.3; on 8% |
| S5 VIX>VIX3M h20 | 46.7 / 2.029 / -16.5 vs 51.1 / 2.104 / -16.5; on 7% | 32.2 / 1.449 / -22.1 vs 34.2 / 1.489 / -22.1; on 5% | 41.7 / 1.726 / -19.8 vs 44.7 / 1.773 / -20.0; on 8% | 31.7 / 1.344 / -16.1 vs 32.4 / 1.336 / -15.7; on 8% |


SQQQ-leg P&L, % of NAV per year (crash days / other days / net of cash carry), SQQQ own return while held (arithmetic / compounded %/yr)

| arm | W1 | W2 | W3 | W4 |
|---|---|---|---|---|
| S1 VIX<15 h5 | +0.50 / -1.30 / -0.85; own -47 / -42 | +0.51 / -0.88 / -0.41; own -23 / -26 | +0.48 / -1.20 / -0.75; own -42 / -39 | +0.43 / -1.01 / -0.58; own -33 / -32 |
| S1 VIX<15 h10 | +1.00 / -2.61 / -1.69; own -47 / -42 | +1.02 / -1.76 / -0.82; own -23 / -26 | +0.95 / -2.41 / -1.51; own -42 / -39 | +0.87 / -2.02 / -1.15; own -33 / -32 |
| S1 VIX<15 h20 | +2.00 / -5.22 / -3.39; own -47 / -42 | +2.03 / -3.52 / -1.64; own -23 / -26 | +1.91 / -4.82 / -3.02; own -42 / -39 | +1.74 / -4.04 / -2.30; own -33 / -32 |
| S1 15-20 h5 | +2.20 / -2.11 / +0.04; own 5 / -11 | +1.67 / -1.98 / -0.34; own -20 / -30 | +1.78 / -2.18 / -0.44; own -22 / -30 | +0.95 / -2.28 / -1.33; own -68 / -54 |
| S1 15-20 h10 | +4.41 / -4.23 / +0.08; own 5 / -11 | +3.34 / -3.95 / -0.67; own -20 / -30 | +3.55 / -4.36 / -0.88; own -22 / -30 | +1.91 / -4.57 / -2.66; own -68 / -54 |
| S1 15-20 h20 | +8.82 / -8.46 / +0.16; own 5 / -11 | +6.68 / -7.91 / -1.34; own -20 / -30 | +7.11 / -8.73 / -1.75; own -22 / -30 | +3.81 / -9.14 / -5.33; own -68 / -54 |
| S1 20-25 h5 | +1.95 / -2.59 / -0.66; own -78 / -65 | +2.62 / -2.60 / +0.00; own 2 / -27 | +1.55 / -2.19 / -0.65; own -83 / -65 | +0.76 / -1.40 / -0.64; own -93 / -66 |
| S1 20-25 h10 | +3.91 / -5.18 / -1.31; own -78 / -65 | +5.24 / -5.20 / +0.01; own 2 / -27 | +3.09 / -4.37 / -1.30; own -83 / -65 | +1.52 / -2.80 / -1.29; own -93 / -66 |
| S1 20-25 h20 | +7.81 / -10.37 / -2.63; own -78 / -65 | +10.48 / -10.40 / +0.02; own 2 / -27 | +6.18 / -8.74 / -2.61; own -83 / -65 | +3.04 / -5.60 / -2.57; own -93 / -66 |
| S1 25-30 h5 | +1.27 / -1.66 / -0.40; own -97 / -76 | +1.81 / -2.00 / -0.20; own -43 / -65 | +1.04 / -1.21 / -0.18; own -49 / -59 | +0.60 / -0.34 / +0.26; own 106 / 114 |
| S1 25-30 h10 | +2.53 / -3.32 / -0.80; own -97 / -76 | +3.62 / -4.00 / -0.39; own -43 / -65 | +2.08 / -2.42 / -0.35; own -49 / -59 | +1.20 / -0.68 / +0.52; own 106 / 114 |
| S1 25-30 h20 | +5.06 / -6.64 / -1.60; own -97 / -76 | +7.23 / -7.99 / -0.79; own -43 / -65 | +4.15 / -4.84 / -0.70; own -49 / -59 | +2.40 / -1.36 / +1.04; own 106 / 114 |
| S1 VIX>=30 h5 | +1.53 / -2.27 / -0.74; own -266 / -98 | +2.48 / -3.37 / -0.90; own -188 / -94 | +1.34 / -2.07 / -0.73; own -240 / -96 | +0.98 / -1.69 / -0.71; own -200 / -92 |
| S1 VIX>=30 h10 | +3.06 / -4.54 / -1.48; own -266 / -98 | +4.96 / -6.75 / -1.79; own -188 / -94 | +2.69 / -4.14 / -1.46; own -240 / -96 | +1.97 / -3.39 / -1.42; own -200 / -92 |
| S1 VIX>=30 h20 | +6.12 / -9.07 / -2.96; own -266 / -98 | +9.93 / -13.49 / -3.58; own -188 / -94 | +5.38 / -8.29 / -2.92; own -240 / -96 | +3.94 / -6.77 / -2.84; own -200 / -92 |
| S2 VIX>=25 h5 | +2.80 / -3.93 / -1.14; own -166 / -91 | +4.29 / -5.37 / -1.09; own -118 / -86 | +2.38 / -3.28 / -0.91; own -137 / -86 | +1.58 / -2.03 / -0.45; own -75 / -69 |
| S2 VIX>=25 h10 | +5.59 / -7.86 / -2.28; own -166 / -91 | +8.58 / -10.74 / -2.18; own -118 / -86 | +4.76 / -6.56 / -1.81; own -137 / -86 | +3.17 / -4.07 / -0.90; own -75 / -69 |
| S2 VIX>=25 h20 | +11.19 / -15.72 / -4.57; own -166 / -91 | +17.16 / -21.48 / -4.37; own -118 / -86 | +9.53 / -13.13 / -3.62; own -137 / -86 | +6.34 / -8.13 / -1.79; own -75 / -69 |
| S2 VIX>=30 h5 | +1.53 / -2.27 / -0.74; own -266 / -98 | +2.48 / -3.37 / -0.90; own -188 / -94 | +1.34 / -2.07 / -0.73; own -240 / -96 | +0.98 / -1.69 / -0.71; own -200 / -92 |
| S2 VIX>=30 h10 | +3.06 / -4.54 / -1.48; own -266 / -98 | +4.96 / -6.75 / -1.79; own -188 / -94 | +2.69 / -4.14 / -1.46; own -240 / -96 | +1.97 / -3.39 / -1.42; own -200 / -92 |
| S2 VIX>=30 h20 | +6.12 / -9.07 / -2.96; own -266 / -98 | +9.93 / -13.49 / -3.58; own -188 / -94 | +5.38 / -8.29 / -2.92; own -240 / -96 | +3.94 / -6.77 / -2.84; own -200 / -92 |
| S2 VIX>=35 h5 | +0.69 / -1.43 / -0.74; own -678 / -100 | +1.47 / -2.07 / -0.60; own -251 / -98 | +0.59 / -1.38 / -0.79; own -650 / -100 | +0.41 / -1.27 / -0.87; own -608 / -100 |
| S2 VIX>=35 h10 | +1.38 / -2.86 / -1.49; own -678 / -100 | +2.93 / -4.14 / -1.21; own -251 / -98 | +1.18 / -2.75 / -1.57; own -650 / -100 | +0.81 / -2.54 / -1.73; own -608 / -100 |
| S2 VIX>=35 h20 | +2.75 / -5.73 / -2.98; own -678 / -100 | +5.87 / -8.28 / -2.42; own -251 / -98 | +2.37 / -5.51 / -3.14; own -650 / -100 | +1.62 / -5.09 / -3.46; own -608 / -100 |
| S3 calm&stretched h5 | +0.87 / -0.75 / +0.08; own 8 / -1 | +0.52 / -0.40 / +0.09; own 12 / 3 | +0.66 / -0.69 / -0.06; own -2 / -10 | +0.26 / -0.58 / -0.32; own -29 / -29 |
| S3 calm&stretched h10 | +1.74 / -1.49 / +0.15; own 8 / -1 | +1.04 / -0.80 / +0.19; own 12 / 3 | +1.32 / -1.38 / -0.12; own -2 / -10 | +0.53 / -1.17 / -0.64; own -29 / -29 |
| S3 calm&stretched h20 | +3.47 / -2.99 / +0.30; own 8 / -1 | +2.07 / -1.61 / +0.37; own 12 / 3 | +2.64 / -2.76 / -0.24; own -2 / -10 | +1.05 / -2.33 / -1.28; own -29 / -29 |
| S4 E/F h5 | +2.52 / -3.02 / -0.51; own -86 / -79 | +4.11 / -3.93 / +0.16; own 21 / -43 | +1.97 / -2.62 / -0.65; own -116 / -83 | +0.91 / -1.85 / -0.93; own -180 / -89 |
| S4 E/F h10 | +5.04 / -6.04 / -1.02; own -86 / -79 | +8.22 / -7.87 / +0.32; own 21 / -43 | +3.94 / -5.23 / -1.31; own -116 / -83 | +1.82 / -3.69 / -1.87; own -180 / -89 |
| S4 E/F h20 | +10.09 / -12.07 / -2.03; own -86 / -79 | +16.44 / -15.73 / +0.65; own 21 / -43 | +7.89 / -10.47 / -2.61; own -116 / -83 | +3.65 / -7.38 / -3.73; own -180 / -89 |
| S4 E/F & VIX>=25 h5 | +1.67 / -2.21 / -0.54; own -163 / -93 | +2.70 / -2.94 / -0.25; own -56 / -82 | +1.39 / -1.93 / -0.55; own -178 / -93 | +0.84 / -1.41 / -0.57; own -214 / -93 |
| S4 E/F & VIX>=25 h10 | +3.35 / -4.41 / -1.08; own -163 / -93 | +5.40 / -5.89 / -0.50; own -56 / -82 | +2.78 / -3.87 / -1.10; own -178 / -93 | +1.67 / -2.82 / -1.14; own -214 / -93 |
| S4 E/F & VIX>=25 h20 | +6.70 / -8.83 / -2.15; own -163 / -93 | +10.81 / -11.78 / -1.00; own -56 / -82 | +5.55 / -7.73 / -2.20; own -178 / -93 | +3.34 / -5.63 / -2.29; own -214 / -93 |
| S5 VIX up>=10% h5 | +0.70 / -1.45 / -0.75; own -168 / -88 | +0.67 / -1.22 / -0.55; own -143 / -85 | +0.70 / -1.26 / -0.56; own -127 / -80 | +0.70 / -0.89 / -0.19; own -45 / -50 |
| S5 VIX up>=10% h10 | +1.41 / -2.89 / -1.51; own -168 / -88 | +1.35 / -2.43 / -1.10; own -143 / -85 | +1.40 / -2.52 / -1.13; own -127 / -80 | +1.40 / -1.79 / -0.39; own -45 / -50 |
| S5 VIX up>=10% h20 | +2.81 / -5.79 / -3.02; own -168 / -88 | +2.69 / -4.86 / -2.20; own -143 / -85 | +2.81 / -5.03 / -2.25; own -127 / -80 | +2.80 / -3.57 / -0.78; own -45 / -50 |
| S5 VIX>VIX3M h5 | +1.97 / -2.72 / -0.75; own -201 / -95 | +1.17 / -1.54 / -0.37; own -147 / -89 | +1.80 / -2.34 / -0.54; own -141 / -88 | +1.48 / -1.60 / -0.12; own -31 / -54 |
| S5 VIX>VIX3M h10 | +3.94 / -5.43 / -1.51; own -201 / -95 | +2.34 / -3.07 / -0.74; own -147 / -89 | +3.60 / -4.67 / -1.08; own -141 / -88 | +2.95 / -3.20 / -0.25; own -31 / -54 |
| S5 VIX>VIX3M h20 | +7.88 / -10.87 / -3.01; own -201 / -95 | +4.67 / -6.15 / -1.49; own -147 / -89 | +7.21 / -9.34 / -2.15; own -141 / -88 | +5.90 / -6.40 / -0.50; own -31 / -54 |
