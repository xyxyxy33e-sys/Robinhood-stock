# Calm VIXY / VIXM hedge study (2026-11-17) - research only, nothing adopted

Files: `PLAN.md` (pre-registered arms and pass bar, written before any run; the owner's VIXM addendum arrived before the first
run and is inside it), `run.py` (everything, ~70 s), `run.log` (all tables, verbatim). Only new files; no existing file touched.

## Setup actually run
- Harness `review_2026_11/harness.py` + 2.0x gross cap (cfg hook) + VIXY 35%-of-cash-leg sleeve (existing sleeve unchanged in every arm).
- Baseline reproduced: real 2015-11-03..2026-11-16: **51.1% CAGR / Sharpe 2.100 / max DD -16.5%**, 46.9 trades/yr (equals `harness.run`
  exactly). Reference quoted was 50.4 / 2.080 / -16.5; the small difference is the extra weeks of data (VIXY closes through 2026-11-16 from
  live_closes). Harness default (VIXM 75% sleeve + cap) is 47.3% / 2.009 / -17.1% for comparison.
- Windows: `real` (2015-11-03..) and `vera` = proxy panel (QQQ core, synthetic TQQQ/QLD) from 2015-09-03 with the sleeve switched on
  (harness has none on proxy): Base 52.1% / 2.031 / -20.1%. **VIXY data in the repo start 2015-09-01. 2011-2015 is not in the repo and there
  is no VIXY proxy, so the requested 2010-onward window cannot be run and everything before 2015-09 is UNTESTED** (22 of the 42 listed
  calm-crack days since 2000 fall there, including 2007-02-27, 2014-04-10, 2015-08-21). `vera` is the same market years as `real`, so it is
  not independent evidence.
- VIXM: data/vixm_daily.csv + live_closes, 2015-09-01..2026-11-13; the last session (11-16) has no VIXM print so its return is 0 (affects VIXM arms for one day). Same windows as VIXY.
- Signal: same-day close of t decides the hedge traded at close t (harness sleeve convention). Lag test: calm input from t-1.
- Matched cash (MC): same rule, funding, sizes, triggers and trade counts; hedge share held in BOXX/cash. Matched vol-target de-lever skipped: the vol target cannot bind in calm markets (rv < 20%), so it cannot remove exposure where the hedge acts.
- Funding `prorata` (main) and `ontop` (cash leg first, else risky) both run; they agree closely (see run.log).

## Results (prorata funding, arm vs its MC; CAGR / Sharpe / max DD; share of days hedge on)
| arm | real arm | real MC | vera arm | vera MC | on |
|---|---|---|---|---|---|
| Base | 51.1 / 2.100 / -16.5 | | 52.1 / 2.031 / -20.1 | | 0 |
| Y C1 T18 h5 | 49.8 / 2.168 / -15.4 | 50.0 / 2.116 / -15.7 | 50.9 / 2.098 / -20.1 | 51.1 / 2.049 / -20.1 | 52% |
| Y C1 T20 h5 | 49.0 / 2.184 / -15.1 | 49.6 / 2.121 / -15.7 | 50.0 / 2.110 / -19.5 | 50.7 / 2.055 / -19.7 | 59% |
| Y C1 T20 h10 | 46.8 / 2.243 / -13.5 | 48.2 / 2.140 / -14.9 | 47.9 / 2.170 / -19.1 | 49.3 / 2.077 / -19.4 | 59% |
| Y C2 h5 | 48.2 / 2.159 / -14.9 | 49.5 / 2.114 / -15.6 | 49.2 / 2.086 / -20.1 | 50.4 / 2.043 / -20.1 | 59% |
| Y C3 h5 | 45.5 / 2.123 / -15.1 | 48.5 / 2.108 / -15.7 | 46.6 / 2.051 / -19.1 | 49.5 / 2.038 / -19.5 | 73% |
| Y C3 h10 | 40.2 / 2.100 / -13.5 | 46.0 / 2.114 / -14.9 | | | 73% |
| Y C4a (ratio<=0.90) h5 | 49.6 / 2.133 / -15.4 | 50.2 / 2.111 / -15.7 | 50.6 / 2.063 / -20.1 | 51.2 / 2.043 / -20.1 | 45% |
| Y C4b (ratio>0.90) h5 | 51.2 / 2.131 / -16.7 | 50.8 / 2.101 / -16.7 | 52.2 / 2.059 / -20.1 | 51.8 / 2.031 / -20.1 | 7% |
| Y C5 h5 | 51.1 / 2.143 / -16.1 | 50.6 / 2.106 / -16.2 | 52.1 / 2.071 / -20.1 | 51.6 / 2.037 / -20.1 | 36% |
| M C1 T18 h10 (=2x5) | 48.8 / 2.169 / -15.2 | 49.0 / 2.130 / -15.4 | 49.8 / 2.100 / -20.1 | 50.1 / 2.065 / -20.1 | 52% |
| M C5 h20 | 50.9 / 2.181 / -15.5 | 49.2 / 2.113 / -15.6 | 52.1 / 2.113 / -20.1 | 50.4 / 2.048 / -20.1 | 36% |
(Y = VIXY hedge, M = VIXM hedge. Full 55 arms x 2 funding x 2 windows in run.log.)

Hedge-leg P&L (real, % of NAV per year; calm-crack days = QQQ <= -3% with prior VIX < 20, 20 of them in the window):
| arm | crack days | other days | total | net of cash carry |
|---|---|---|---|---|
| Y C1 T18 h5 | +0.72 | -0.94 | -0.23 | -0.30 |
| Y C1 T20 h5 | +0.75 | -1.32 | -0.57 | -0.65 |
| Y C1 T20 h10 | +1.48 | -2.59 | -1.11 | -1.27 |
| Y C2 h5 | +0.70 | -1.69 | -0.99 | -1.07 |
| Y C3 h5 | +0.75 | -2.94 | -2.19 | -2.27 |
| Y C3 h10 | +1.48 | -5.80 | -4.32 | -4.49 |
| Y C5 h5 | +0.53 | -0.19 | +0.34 | +0.30 |
| M C1 T18 h10 | +0.43 | -0.51 | -0.08 | -0.21 |
| M C5 h20 | +0.61 | +0.69 | +1.30 | +1.12 |
Instrument itself, real: VIXY mean +14.8% on the 10 crack days the C1 T18 hedge was on (VIXM +4.6%); on the other hedge-on days VIXY
returns -36% / yr (C1 T18), -56% (C2), -80% (C3, arithmetic); VIXM -10% / -18% / -24%. The exception is C5 (state A, stretched): VIXY -8% / yr
arithmetic (-21% geometric), VIXM +9.8% / yr on 986 hedge-on days.

Average book return on the 20 real-window crack days (QQQ -3.72%): Base -1.04%; Y C1 T18 h5 -0.54% (MC -0.93%); Y C1 T20 h5 -0.50% (MC -0.92%);
Y C2 h5 -0.55% (-0.94%); Y C3 h5 -0.50% (-0.92%); Y C5 h5 -0.68% (-0.98%); M C5 h20 -0.46% (-0.79%). The hedge was on for 10-11 of the 20 days
(the rest were in B/E/F/gated D or the sleeve was already on).

Named episodes (real; day / day+5 sessions, Base vs best VIXY arm Y C1 T20 h10 vs its MC): 2018-02-05 -0.94/+4.66 vs +3.73/+9.60 (MC -0.47/+5.17);
2020-02-24 -0.53/+1.08 vs +1.64/+3.28 (MC -0.26/+1.36); 2024-07-24 -0.68/+3.02 vs +1.10/+4.12 (MC -0.33/+2.92), span to 08-05 +6.67 vs +7.82;
2025-10-10 -0.72/-0.22 vs +0.80/+1.77; 2026-06-05 -1.16/-1.67 vs +0.02/-0.49; 2026-10-30 -6.97/+2.72 vs -5.05/+4.84; 2018-10-10 and 2026-11-05: no
change (not leveraged-and-calm; on 11-05 the book was in the gated-D cash leg and +10.39% from the existing sleeve).

## Verdicts against the pre-registered bar (run.log "FINAL VERDICTS")
Prorata funding. PASS by the letter of the bar: VIXY C1 T18 and T20 at h 2%/5% and T20 at 10%; VIXM C1 T18 and T20 at 2/4/5/10%, VIXM C5 h 5/10/20%.
Every other cell is rejected: C1 T14/T16 (hedge on only 0-3 of the 20 crack days; Sharpe change about 0), C1 T18 h10 and VIXM h20 (bootstrap P >= 0.10),
VIXY C2 and C3 (second half Sharpe negative vs MC), VIXY C4a / C4b / C5 (cannot satisfy the two-neighbour rule; they otherwise hold),
VIXM C2 / C3 (second half negative). Ontop funding: same pattern, 18 passes (adds VIXY C1 T18 h10, VIXM T20 h20). Insurance flag: only VIXY C3 h10
(Sharpe -0.013 vs MC, max DD 1.34 pp shallower, worst-5 2.35 pp better, cost -5.75 pp CAGR/yr and -4.3% NAV/yr hedge P&L).

## What this means - read before acting on "PASS"
- The prior was half right. On net hedge-leg P&L the VIXY hedge loses money in C1/C2/C3 (-0.2 to -4.3% of NAV per year): the decay on the
  hedge-on days (-36% to -80%/yr for VIXY) beats the crack-day payoff (+0.7 to +1.5%/yr). It still raises Sharpe vs matched cash by +0.02 to +0.10
  because the payoff lands on the worst days and cuts vol 0.6-1.9 pp, worst 5-day loss by 1.5-2.4 pp, and max DD by 0.3-1.4 pp. But it **costs CAGR vs matched cash**
  in every VIXY C1/C2/C3 cell (-0.1 to -5.8 pp/yr; T18 h5 -0.27, T20 h5 -0.69, T20 h10 -1.38) and vs Base too (49.8% vs 51.1% for T18 h5).
  The pass bar is Sharpe/max-DD based, so it does not penalise that.
- C4: costly-carry split behaves as expected the wrong way round: the flat-curve hedge (ratio > 0.90, on 7% of days) is the only C1-family cell with a gain
  in CAGR (+0.45 pp vs MC) but fires on only 5 crack days; steep-contango (<= 0.90) loses 0.6 pp CAGR. Small samples.
- C5 (state A, QQQ > 10% over 200d) and VIXM-in-C5 are the only cells with a positive hedge-leg P&L and a CAGR gain vs MC (+0.5 pp VIXY h5, +1.7 pp VIXM h20);
  dSharpe +0.04 / +0.07. VIXM's positive "other days" return there (+9.8%/yr) is likely a few episodes (2018, 2020-21); not a persistent carry.
- Evidence strength: the effect is carried by about ten events (2018-02-05 largest, then 2020-02-24, 2019-08, 2021-11-26, 2024-12-18). Dropping the five best days
  keeps dSharpe positive for C1 T18/T20 (e.g. T18 h5 +0.052 -> +0.025) but removes it for VIXY C3 and mostly for C2 h10 / C5 h10 (concentration table in run.log).
  Bootstrap P is 0.02-0.09 on the passing cells; with 55 arms x 2 funding variants tested and highly correlated cells (same events), treat that as suggestive, not
  significant. Year by year (real) the T18 h5 diff vs MC is -9.8 pp in 2017, -3.3 pp in 2023, +2.9 in 2018: a strong calm-bull-year drag. Sharpe gain is concentrated in
  the first half (+0.085 vs +0.032 in the second half for T18 h5; C2/C3 negative in the second half). Lagging the calm signal a day leaves C1 T18 about unchanged
  (+0.050 vs +0.052), T20 h5 +0.050 vs +0.062; 5 bp cost on VIXY trades moves dSharpe by <= 0.003 and CAGR by 0.03-0.07 pp.
- VIXM vs VIXY at like-for-like size (VIXM 2h): VIXM C1 T18 h10 vs VIXY h5: dSharpe +0.039 vs +0.052, dCAGR -0.19 vs -0.27, max DD +0.26 vs +0.26 shallower:
  VIXM delivers about the same insurance for ~30% less CAGR cost in the C1 cells; at C2/C3 VIXM h10 vs VIXY h5 is similar. VIXM passes more cells because its drag is smaller, not
  because it hedges better.

## Limits
- No VIXY before 2015-09 in the repo; no synthetic built (the CFE mid-term proxy is VIXM-like, not VIXY). 2011-2015 (Aug 2011, calm 2013-14, Aug 2015) untested.
  The `vera` window is the same years as `real`. Roughly 11 years and 20 crack days: small sample.
- Harness has no L1 gate; proxy `vera` sleeve is my addition (harness leaves the sleeve off on proxy). VIXM 2026-11-16 return forward-filled to 0.
- Matched cash arm is a de-risking control; it reduces equity exposure equally. The vol-target matched de-lever was not run (cannot bind in calm).
- Pass-bar neighbour rule makes C4 (two cells) unpassable by construction; reported as "would pass otherwise".
- The concentration table was added after the first run (not part of the pass bar).

## Out-of-sample 2011-2015 (follow-up, `run_oos.py` / `run_oos.log`; PLAN.md Addendum 2 written before the run)
Data: `vixy_yahoo_full.csv`, `vixm_yahoo_full.csv` (split-adjusted closes, 2011-01-04..2026-11-16). They match the earlier series on the overlap (VIXM max daily-return
difference 0.04%; VIXY 0.27% on one day, mean 0.002%). Proxy panel only (no SPMO before 2015): core = QQQ + 0.6%/yr dividend, TQQQ/QLD synthetic 3x/2x with T-bill + 0.3% financing
and 0.84%/0.95% expense ratios, XLU long history + 3% yield, cash = 3-month T-bill accrual. Same rules, sizes and pro-rata funding as before; nothing re-tuned.
Baseline (cap 2.0, VIXY 35% sleeve; the sleeve was allowed on only 1.4% of 2011-15 sessions): OOS 2011-01-05..2015-09-02 **22.6% / 0.963 / -16.4%**;
2015-09-03..2026-11-16 52.0% / 2.029 / -20.1% (original vera 52.1 / 2.031, difference is the new VIXY return file); joined 42.7% / 1.690 / -20.1%.

**The OOS window contains only 2 calm-crack days** (2014-04-10, state D ungated, hedge on for the VIX cells, off for C5; 2015-08-21, state D gated = cash, hedge off for every arm). It therefore
mostly measures the decay cost, not the payoff. VIX was under 18 on 72% of OOS sessions and the book was leveraged on 84% (state A 69%), so the C1 hedge was on 66-74% of days.

OOS, arm vs matched cash (dCAGR pp / dSharpe / dmaxDD pp; hedge on %): VIXY C1 T18 h5 -1.19 / -0.009 / +0.47 (66%); VIXY C1 T20 h5 -2.08 / -0.037 / +0.04 (74%); VIXM C1 T18 h10 -1.90 / -0.041 / +0.19 (66%);
VIXY C5 h5 -0.53 / -0.013 / +0.02 (26%); VIXM C5 h10 -0.66 / -0.019 / +0.04 (26%); VIXM C5 h20 -1.35 / -0.042 / +0.08 (26%); VIXY C3 h5 -3.02 / -0.058 / +0.19 (83%).
Late window (2015-09+, same code): C1/C5 cells again +0.03 to +0.07 Sharpe as in the main study; joined window dSharpe +0.016 to +0.035 (C1), +0.018 to +0.031 (C5), C3 -0.005.
Hedge-leg P&L OOS, % NAV/yr (crack / other): VIXY C1 T18 h5 +0.07 / -1.20; T20 h5 +0.07 / -1.97; VIXM C1 T18 h10 +0.05 / -1.72; VIXY C5 h5 0 / -0.46; VIXM C5 h10 0 / -0.58; VIXM C5 h20 0 / -1.13;
VIXY C3 h5 +0.07 / -2.76. Instrument return on hedge-on non-crack days OOS: VIXY -34% (C1 T18), -50% (T20), -29% (C5), -63% (C3); VIXM -26% (C1), -21% (C5). In 2011-15 even VIXM C5 lost 21%/yr
on hedge-on days, versus +9.8%/yr in 2015-2026.
Year by year (OOS, arm minus matched cash, pp): the C1 cells lose 1-3 pp in each of 2012 and 2013 (calm bull years: 2012 Base +27.7%, hedged T18 h5 +25.7% vs matched cash +27.4%); C5 cells are about -1 to -3 pp in 2011-13
and positive in 2014 (+1.4, +1.2, +2.2). Episodes: Aug 2011 and Aug 2015 show no hedge effect (VIX above 20 / book in cash); 2013-06 hedged arms -3.9 to -4.5% vs Base -5.7%
(matched cash -4.9 to -5.3); 2014-04-10 day -3.8% vs Base -4.4% (matched cash -4.1%); 2014-10-09..15 T20 h5 -7.9% vs Base -9.1% (matched cash -8.8%).

Verdicts under the pre-registered reading rule (OOS alone): VIXY C1 T18 h5 INCONCLUSIVE; VIXY C1 T20 h5 CONTRADICTED; VIXM C1 T18 h10 CONTRADICTED; VIXY C5 h5 INCONCLUSIVE; VIXM C5 h10 INCONCLUSIVE;
VIXM C5 h20 CONTRADICTED; VIXY C3 h5 CONTRADICTED (expected). None is confirmed. Caveat: with 2 crack days the window cannot test the payoff; it shows the drag (-0.5 to -3 pp CAGR/yr and
-0.01 to -0.06 Sharpe vs matched cash) in 2011-15, when the hedge was on far more often. Both worst-day and worst-5-day were unchanged in the OOS window except C3, and max DD gains were at most 0.5 pp.

## After-tax view (`run_tax.py` / `run_tax.log`; PLAN.md Addendum 3 written before the run)
Method and rates are those of `review_2026_11/after_tax_test.py`: FIFO lots, ST if held <= 365 days, wash sales +/-30 days same ticker, price-only, tax for year Y paid 15 April Y+1 by pro-rata
sale, ST and LT netted separately with carryforwards (a net-loss year pays nothing and the loss is carried forward), no $3k offset, BOXX deferred, liquidation-basis after-tax CAGR. S1 federal
38.8% ST / 18.8% LT; S2 top + California 50.1% / 33.1%. VIXY and VIXM are modelled as ordinary ETFs (their real pool/ETN tax treatment is not). The lot simulation reproduces the engine's daily returns
to 1e-9. After-tax Sharpe / max DD are on the taxed account's daily value changes including the April payments; an accrual alternative (tax or credit at the rate on each day's realized gain) is in the log.
Baseline after tax (S1 / S2 CAGR / Sharpe / DD): real 34.2% / 1.364 / -26.3% and 28.8% / 1.127 / -31.4%; OOS 15.1% / 0.739 and 12.6% / 0.663; late 34.8% / 1.341 and 29.3% / 1.117.

Result: **the hedge does not shrink the net realized gain in the cells that looked best pre-tax, so tax does not rescue any cell.** Net realized gain per full year (mean, $ per $600k): real Base $340k; VIXY C1 T18 h5
$334k vs matched cash $331k (hedge arm +$2.3k MORE); VIXM C5 h10 $346k vs $337k (+$9.4k more); VIXM C5 h20 +$18k more; VIXY C3 h5 is the only real-window cell that removes gain ($11.5k/yr, at a cost of $23.1k/yr
of pre-tax P&L: 2.0 pre-tax dollars per dollar of gain removed). In the OOS window gains are removed by 6 of 7 cells ($2-10k/yr) at 1.3-5.2 pre-tax dollars given up per dollar removed. The crack-day payoffs are
realized short-term gains, and the decay losses are partly deferred by wash sales, so the stream of "losses to offset elsewhere" is small: hedge-leg net realized P&L (real, % NAV/yr, no wash adjustment) is +0.2 (C1 T18),
+0.1 (C1 T20), +0.3 (VIXM C1), +0.7 (VIXY C5), +0.9 (VIXM C5 h10), -1.0 (C3).
Wash sales on the hedge leg (real window): the loss that crosses a year-end (December loss re-bought within 30 days into January) is on average 0.3-1.5% of NAV per year (worst year 1.8-7.2%, e.g. 2018, 2023 for
the VIXY cells), i.e. a loss realized in December that lands in the next tax year.
Pre-tax vs after-tax differences (arm minus matched cash, dCAGR pp / dSharpe), late window: VIXY C1 T18 h5 -0.22 / +0.049 pre, -0.36 / +0.013 S1, -0.36 / +0.005 S2; VIXM C5 h10 +0.86 / +0.040 pre, +0.61 / +0.019, +0.53 / +0.013.
OOS: VIXY C1 T18 h5 -1.19 / -0.009 pre, -0.98 / -0.024 S1, -0.83 / -0.028 S2; VIXM C5 h10 -0.66 / -0.019 pre, -0.43 / -0.013, -0.35 / -0.012. Taxes shrink the CAGR gap where the hedge removes gains (OOS) and widen it where the hedge adds
gains (real/late C1, C5), and cut the late-window Sharpe edge by roughly 50-90%. No cell flips from negative pre-tax to positive after tax in the OOS window. Verdicts under the reading rule: all seven cells NO CHANGE.
Arithmetic check: where gain is removed, tax saved / gain removed equals the ST rate (0.36-0.40 S1, 0.48-0.50 S2) as it must; four OOS/late cells show 0.390-0.397 vs 0.388 (ST/LT mix in the net-gain denominator), so tax cannot turn a hedge loss
into a gain, and after-tax differences stay on the same side of zero as pre-tax. Limits: commodity-pool / ETN tax treatment of VIXY/VIXM not modelled (K-1 / Section 1256 could change this); proxy-panel OOS is synthetic for the leveraged legs;
wash-sale cross-year estimate is an approximation (with-vs-without-rule difference on hedge-tagged lots); the owner's loss harvesting elsewhere is not modelled.
