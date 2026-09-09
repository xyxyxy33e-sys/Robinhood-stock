# overnight_intraday -- overnight gaps vs intraday: where the losses are and whether the protection arrives before them (2026-09-09)

Research line, RESEARCH ONLY under the change freeze; nothing applied.
Script: `paper-track/overnight_intraday.py` (38 s, prints every table below; reproduces the
standing live figures first: proxy 22.12% / 0.938 / -32.8%, S 1.150, H 0.780, exposure 66.21%,
68 reb/yr; real weekly 30.67% / 1.260 / -25.3%; real daily 29.69% / 1.202 / -29.5%, 70 reb/yr).
New data: `data/tqqq_ohlc.csv`, `data/spmo_ohlc.csv`, `data/qld_ohlc.csv`, `data/xlu_ohlc.csv`.

## Verdict in one paragraph

The protection arrives BEFORE the damaging move, not after it. On the worst 1% of overnight
gaps (66 sessions, mean -3.64%) the live design was holding 22% deployed capital / beta 0.29
going into the gap against 45.5% / 0.60 for the plain macro row -- the vol target had already
taken 0.52pp of the average -1.83% gap loss and the trim another 0.32pp -- and the multiplier was
below 0.9 on 60 of the 66 gaps before they happened (median 14 sessions early on the worst 20).
On the worst intraday sessions it is even clearer: 65 of 66 below 0.9, 63 below 0.7, in place
for a median 73 sessions. The book barely trades after a gap (mean beta change into->after the
worst gaps -0.02 vs an unconditional |change| of 0.08), so "delayed selling" is not the
signature; the vol-target's reaction lag shows up only at the deepest cut (mult < 0.5: 37 of 66
worst gaps in place, 21 after, 8 never). The execution-convention test says the same thing from
the other side: moving every fill from the 15:55 close to the next open costs -0.98pp CAGR /
-0.037 Sharpe / 6.5pp of drawdown on the 26-year proxy, ALL of it overnight (-0.77pp/yr overnight,
+0.02 intraday), but the sign flips by era (holdout -2.2pp/yr, SPMO era +1.2pp/yr; real daily
instruments +0.4pp) and the 26-year bootstrap has P(<=0) = 0.79 -- it is inside noise and is
dominated by a handful of regime flips the session before a big gap (2015-08-24 alone is 16pp
in the close's favour, Brexit 2016-06-24 is 7pp against). A full session of lag is unambiguously
bad (-2.6pp, -0.087, real daily -1.8pp / -0.055), consistent with the trigger prompt's standing
1.4-2.2pp figure. Nothing here argues for changing execution timing: the close-execution
convention is not systematically paying for or being paid by the overnight gap; it is a coin
flip on ~10 sessions per decade, and one extra session of delay is the only thing measurably
worse. The one place the numbers point elsewhere is the vol estimator (section 5): UPweighting
overnight variance hurts monotonically and DOWNweighting it helps by ~+0.01 Sharpe on both eras,
real weekly and real daily -- small, the mirror of what was asked, and recorded, not proposed.

## 1. Data: the OHLC files (provenance)

`data/qqq_ohlc.csv` (range_vol line, 2026-09-08): QQQ d,o,h,l,c 1999-09-15..2026-09-04, 6,784
sessions, closes and opens matching `qqq_long_history.csv` to the cent. Every proxy row's
d0->d1 window is exactly one OHLC session (0 rows span more).

Added by this line (Robinhood `get_equity_historicals`, interval `day`, bounds `regular`,
`adjustment_type=split`, one call per symbol 2015-10-01..2026-09-06, `interpolated` bars dropped):

| file | span | bars | dropped | cross-check vs `/home/user/robinhood/data/kairos/etf/<SYM>.csv` (d,o,c) |
|---|---|---|---|---|
| `data/tqqq_ohlc.csv` | 2015-10-01..2026-09-04 | 2748 | 0 | 2742 common days, 0 open mismatches > 1c, 0 close mismatches > 1c |
| `data/spmo_ohlc.csv` | 2015-10-12..2026-09-04 | 2741 | 7 (pre-inception stubs 10-01..10-09; SPMO listed 2015-10-13) | 2735 common, 0 / 0 |
| `data/qld_ohlc.csv` | 2015-10-01..2026-09-04 | 2748 | 0 | 2742 common, 0 / 0 |
| `data/xlu_ohlc.csv` | 2015-10-01..2026-09-04 | 2748 | 0 | 2742 common, 0 / 0 |

No H < max(O,C) or L > min(O,C) violations in any file. The kairos daily files the real-daily
harness already uses carry opens, so the real-instrument split below is computed from the SAME
files as the standing real-daily figures; the new OHLC files are the independent cross-check and
add high/low. BOXX has no usable open history (flat stub until 2022-12) and is treated as one
piece. `data/README.md` is a protected file and was not edited; this section is the provenance.

Proxy-leg split (stated approximation): a daily-reset k-times fund carries k-times the
underlying's exposure from the prior close, so open/prev-close ~ 1 + k x gap. TQQQ overnight =
3 x QQQ gap, QLD = 2 x; financing, expense ratio and dividend accrual land in the intraday
residual (id = (1+leg)/(1+on) - 1, exact by construction). Checked on the real funds 2015-11+:
corr(3 x QQQ gap, TQQQ gap) = 0.9973, slope 0.990; corr(2 x QQQ gap, QLD gap) = 0.9971, slope
0.999. XLU (close-only long history) and cash are UNSPLIT in the proxy: their whole return sits
in the intraday bucket; they are held in 34% of proxy rows (state E and the cash leg), and their
gap variance is small (real XLU: 22% overnight share).

## 2. Where are the losses (QQQ, then the strategy's own P&L)

Shares are of the close-to-close quantity. var = share of total variance (the 2cov column is the
remainder); semi = share of downside semi-variance; tail1/tail5 = overnight share of the summed
log-return of that window's worst 1% / 5% sessions; cum = summed log return of each half.

### 2a. QQQ, 2000-07..2026-08 by regime

| regime | n | var ON | var ID | 2cov | semi ON | tail1 ON | tail5 ON | cum ON | cum ID | skew ON/ID | kurt ON/ID | ann sd ON/ID |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL 2000-07..2026-08 | 6575 | 29.5% | 71.9% | -1.4% | 28.4% | 28.8% | 29.1% | +255.7% | -53.3% | -0.41 / 0.35 | 12.1 / 12.0 | 13.9% / 21.7% |
| dot-com 2000-07..2002-10 | 569 | 23.2% | 80.3% | -3.5% | 19.9% | 23.1% | 20.9% | +0.7% | -151.5% | 0.40 / 0.64 | 3.0 / 3.9 | 24.5% / 45.6% |
| GFC 2007-10..2009-03 | 356 | 26.1% | 75.5% | -1.6% | 26.1% | 18.1% | 18.5% | -15.6% | -51.3% | -0.65 / -0.06 | 7.4 / 1.6 | 18.9% / 32.2% |
| 2011 Jul-Oct | 85 | 29.6% | 56.4% | 14.0% | 41.1% | 49.5% | 52.1% | -6.3% | +3.8% | -0.40 / 0.14 | 0.2 / -0.5 | 17.4% / 24.0% |
| 2015-16 Aug-Feb | 145 | 60.2% | 63.4% | -23.6% | 52.4% | 116.0% | 65.3% | -2.6% | -2.7% | -2.05 / -0.23 | 14.4 / 1.9 | 18.5% / 19.0% |
| 2018 Q4 | 63 | 28.8% | 74.1% | -2.9% | 23.6% | 2.5% | 10.4% | +1.1% | -19.5% | -0.31 / 0.08 | 0.6 / 0.3 | 17.7% / 28.4% |
| COVID 2020-02-19..03-23 | 24 | 55.3% | 25.4% | 19.3% | 75.0% | 77.9% | 75.5% | -23.6% | -1.9% | -0.28 / -0.31 | -0.7 / -0.9 | 62.1% / 42.1% |
| 2022 bear | 251 | 29.5% | 72.1% | -1.6% | 29.7% | 36.6% | 38.6% | -25.1% | -16.7% | 0.45 / 0.23 | 2.0 / 0.4 | 17.5% / 27.3% |
| calm 2013 | 252 | 35.6% | 66.9% | -2.5% | 33.6% | 41.7% | 29.3% | +13.6% | +12.5% | -0.48 / -0.50 | 0.9 / 1.1 | 7.1% / 9.7% |
| calm 2017 | 251 | 28.0% | 67.6% | 4.4% | 20.9% | 17.2% | 11.9% | +17.6% | +10.6% | 0.08 / -1.33 | 2.0 / 3.9 | 5.5% / 8.6% |
| calm 2019 | 252 | 37.5% | 51.3% | 11.2% | 45.0% | 58.6% | 44.7% | +16.2% | +17.1% | -0.62 / -0.07 | 1.6 / 1.3 | 10.0% / 11.6% |
| calm 2021 | 252 | 31.1% | 65.8% | 3.1% | 29.2% | 28.9% | 26.9% | +15.8% | +10.3% | -0.29 / -0.65 | 1.3 / 0.6 | 10.1% / 14.7% |
| calm 2024 | 252 | 40.8% | 61.1% | -1.9% | 34.8% | 21.1% | 41.2% | +28.6% | -4.9% | -1.61 / -0.78 | 12.9 / 1.4 | 11.4% / 14.0% |
| SEARCH 2015-11+ | 2719 | 37.1% | 61.7% | 1.2% | 38.6% | 48.2% | 38.3% | +118.7% | +65.2% | -1.05 / 0.18 | 13.7 / 7.8 | 13.5% / 17.5% |
| HOLDOUT 2000-07..2015-10 | 3856 | 26.1% | 76.5% | -2.6% | 23.9% | 21.2% | 23.5% | +137.0% | -118.5% | -0.02 / 0.40 | 11.1 / 11.3 | 14.2% / 24.3% |

Real-era extra window: 2025 Mar-Apr tariff (42 sessions) 29.8% var ON, 49.6% semi ON, 60.0%
tail5 ON, cum ON -12.6% vs ID +9.5%.

What this says, beyond range_vol's 29.7%:
- Over 26 years the overnight carries 29.5% of variance, 28.4% of downside semi-variance and
  29% of the worst-tail sum -- the tails are NOT more overnight than the body on the full
  sample. The premium is the famous one: +256% cumulative log return overnight vs -53% intraday.
- The two big bears are INTRADAY bears: dot-com 80% / GFC 76% of variance intraday, tails 18-23%
  overnight, cum ID -152% / -51%. The 2022 bear is body-like (30% / 37%).
- The overnight-dominated episodes are the SHORT shocks: COVID's 24 sessions (55% var, 75% semi,
  78% of the tail), 2015-16 (60% var; tail1 > 100% because the intraday half of those sessions
  was positive: 2015-08-24 gapped -7.98% and closed up from the open), 2011 (41% semi, 50% tails).
- The SPMO era is more overnight than the holdout (37% vs 26% of variance, 48% vs 21% of the 1%
  tail; overnight skew -1.05 vs -0.02). The gap risk the live design faces is larger than the
  26-year average suggests, and larger than the range_vol figure.

### 2b. The strategy's own daily return (live design, proxy, held weights x leg gaps)

| regime | n | var ON | var ID | 2cov | semi ON | tail1 ON | tail5 ON | cum ON | cum ID | skew ON/ID | kurt ON/ID |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ALL 2000-07..2026-08 | 6575 | 30.2% | 69.9% | -0.0% | 27.1% | 32.1% | 23.8% | +398.0% | +123.4% | -0.27 / -0.53 | 6.6 / 3.4 |
| dot-com | 569 | 18.9% | 70.6% | 10.5% | 20.9% | 21.9% | 25.6% | -10.5% | -12.6% | -0.87 / -1.25 | 8.7 / 11.5 |
| GFC | 356 | 20.2% | 68.9% | 10.8% | 17.0% | 26.7% | 22.1% | +8.4% | -26.4% | 0.64 / -0.44 | 7.7 / 4.8 |
| 2011 Jul-Oct | 85 | 27.8% | 54.8% | 17.4% | 26.2% | 30.4% | 38.7% | -4.1% | -11.4% | 0.03 / -1.63 | 2.7 / 4.6 |
| 2015-16 Aug-Feb | 145 | 30.3% | 52.2% | 17.5% | 35.5% | 45.9% | 41.3% | -8.9% | -11.3% | -0.43 / -1.03 | 11.0 / 4.3 |
| 2018 Q4 | 63 | 9.3% | 75.6% | 15.1% | 8.7% | 13.6% | 13.8% | -6.6% | -28.1% | -0.92 / -2.52 | 4.4 / 9.4 |
| COVID | 24 | 39.6% | 63.4% | -3.0% | 50.9% | 49.1% | 69.1% | -12.9% | -4.9% | -1.15 / -0.17 | 0.5 / 0.9 |
| 2022 bear | 251 | 28.7% | 73.9% | -2.7% | 26.2% | 17.2% | 21.2% | -15.8% | -16.3% | 0.06 / -1.41 | 12.0 / 7.9 |
| calm 2013 / 2017 / 2019 / 2021 / 2024 | | 35 / 29 / 40 / 33 / 38% | | | 33 / 22 / 42 / 33 / 29% | | | | | | |
| SEARCH 2015-11+ | 2719 | 35.2% | 67.5% | -2.7% | 32.3% | 39.0% | 27.4% | +181.8% | +98.5% | -0.64 / -0.67 | 6.2 / 3.8 |
| HOLDOUT | 3856 | 26.1% | 71.8% | 2.1% | 22.5% | 25.6% | 20.9% | +216.2% | +24.9% | 0.21 / -0.43 | 6.2 / 3.1 |

On REAL instruments 2015-11..2026-08 (SPMO/TQQQ/QLD/XLU opens, BOXX unsplit, 2719 sessions):
strategy 37.3% var ON, 33.5% semi ON, 35.2% / 28.8% tail1/tail5 ON, cum ON +225.7% vs ID
+54.8%; 2018 Q4 10.4% var ON; COVID 40.2% / semi 54.5%; 2022 33.1%; 2025 tariff 24.8% var
(49% semi). Per instrument: SPMO 49.1% var ON (cum ON +265% / ID -91%), TQQQ 37.6%, QLD 37.4%,
XLU 22.0%.

Reading: the strategy's overnight share is essentially QQQ's (30% vs 29.5% full sample, 35% vs
37% SPMO era). The overlays do NOT tilt the book away from gap risk toward intraday risk; they
scale both. Where the strategy's tail share is LOWER than QQQ's (2015-16 46% vs 116%, 2018 Q4
14% vs 2.5% is the exception, COVID 49% vs 78%, SPMO era 39% vs 48%) it is because the design
was already de-levered into those gaps -- section 3 measures exactly that. Kurtosis of the
strategy's overnight half is 6.6 vs QQQ's 12.1: the vol target halves the gap tail.

## 3. What does each overlay protect

### 3a. Forward damage after the overlay cut exposure (QQQ, next 1/5/21 sessions)

"ON share of loss" is aggregated over the windows whose total was negative.

| overlay reduced exposure | sessions | horizon | mean ON | mean ID | ON share of loss | P(ON < ID) | unconditional ON / ID (ON share of loss) |
|---|---|---|---|---|---|---|---|
| vol target (mult < 1) | 2190 (33.3%) | 1 | +0.03% | +0.03% | 27.5% | 49.7% | +0.04% / -0.01% (24.7%) |
| | | 5 | +0.15% | +0.10% | 29.2% | 48.6% | +0.20% / -0.04% (22.7%) |
| | | 21 | +0.70% | +0.10% | 25.3% | 47.5% | +0.82% / -0.17% (13.5%) |
| vol target mult in [0.5,0.7) | 843 | 21 | +1.10% | -1.35% | 4.0% | 40.6% | |
| vol target mult < 0.5 | 778 | 5 | -0.16% | -0.25% | 26.7% | 50.8% | |
| | | 21 | -0.38% | -1.18% | 20.3% | 53.9% | |
| extension trim (votes > 0 in eff A) | 1012 (15.4%) | 1 | +0.04% | -0.07% | 25.8% | 46.6% | |
| | | 5 | +0.26% | -0.23% | 18.3% | 41.0% | |
| | | 21 | +1.33% | -0.88% | 6.4% | 34.4% | |
| fast overlay RAISED exposure (eff != state) | 692 (10.5%) | 21 | -0.01% | +0.81% | 30.4% | 59.2% | |

The fast overlay only ever UPGRADES the row (B/C -> A, F -> C); it reduced exposure on 0
sessions by construction (the 38 rows flagged are effective-A rows where the trim then applied),
so its line is the mirror question: the exposure it adds earns its keep intraday (+0.81% over
21 sessions vs +0.82%/-0.17% unconditionally).

What the overlays are protecting against, by horizon:
- The vol target's subsequent damage is intraday-shaped: after a cut, the next-21-session
  overnight is still POSITIVE on average (+0.70%, +1.10% in the 0.5-0.7 bucket) and the loss is
  intraday (-1.35% in that bucket; ON share of the loss 4%). Only the deepest cuts (mult < 0.5)
  see negative forward gaps (-0.38% over 21), and even there the loss is 80% intraday.
- The trim is the same, more so: over 21 sessions after a trim vote, overnight +1.33%, intraday
  -0.88%, overnight share of the loss 6.4%. The extension trim gives up overnight premium to
  avoid intraday give-back in extended tape.
- So at the 1-5-21 horizon neither overlay is "protecting the gap": what follows a cut is a
  positive-drift overnight and a negative intraday, i.e. the overlays reduce exposure to the
  half of the session where the subsequent loss actually occurs. This is the opposite of the
  delayed-selling picture, in which the gap would already have been taken and the forward window
  would be flat.

### 3b. Exposure held INTO the worst gaps, per overlay (the direct test)

"expo" = deployed capital (sum of risky weights), beta = 1.0/3.0/2.0/0.5/0 per leg, "port ret"
= that allocation's mean overnight return on those sessions using the leg gaps, "avoided" =
LIVE's overnight return minus that allocation's (positive = LIVE lost less). Last column = the
same allocation one session LATER (does the design sell after the gap?).

Worst 1% overnight gaps (66 sessions, mean QQQ gap -3.64%, worst -9.46% 2020-03-16):

| allocation | expo into | beta into | port ret | avoided vs LIVE | expo / beta 1 session later |
|---|---|---|---|---|---|
| macro only W[state] | 45.5% | 0.60 | -1.83% | +0.95pp | 39.4% / 0.50 |
| +fast (W[eff]) | 45.5% | 0.60 | -1.83% | +0.95pp | 39.4% / 0.50 |
| +trim (no vt) | 38.9% | 0.47 | -1.40% | +0.52pp | 36.9% / 0.45 |
| LIVE target (fast+trim+vt) | 22.4% | 0.30 | -0.89% | 0 | 20.1% / 0.28 |
| LIVE with vt OFF | 38.9% | 0.47 | -1.40% | +0.52pp | 36.9% / 0.45 |
| LIVE with trim OFF | 27.2% | 0.39 | -1.21% | +0.32pp | 21.6% / 0.30 |
| LIVE with fast OFF | 22.4% | 0.30 | -0.89% | +0.00pp | 20.1% / 0.28 |
| LIVE with plain vol30 | 25.6% | 0.34 | -1.03% | +0.15pp | 24.0% / 0.33 |
| LIVE HELD (drift band) | 22.3% | 0.29 | -0.88% | -- | 20.0% / 0.27 |

Worst 5% overnight gaps (329 sessions, mean -2.08%):

| allocation | expo into | beta into | port ret | avoided vs LIVE | 1 session later |
|---|---|---|---|---|---|
| macro only | 56.4% | 0.89 | -1.63% | +0.55pp | 53.0% / 0.82 |
| +fast | 63.7% | 1.02 | -1.86% | +0.78pp | 59.7% / 0.94 |
| +trim (no vt) | 56.4% | 0.88 | -1.57% | +0.49pp | 55.7% / 0.86 |
| LIVE target | 36.7% | 0.61 | -1.08% | 0 | 35.9% / 0.59 |
| LIVE with vt OFF | 56.4% | 0.88 | -1.57% | +0.49pp | 55.7% / 0.86 |
| LIVE with trim OFF | 42.7% | 0.73 | -1.31% | +0.23pp | 38.9% / 0.65 |
| LIVE with fast OFF | 34.4% | 0.56 | -0.99% | -0.09pp | 33.6% / 0.54 |
| LIVE with plain vol30 | 39.4% | 0.65 | -1.17% | +0.09pp | 39.2% / 0.64 |
| LIVE HELD | 36.7% | 0.61 | -1.08% | -- | 35.9% / 0.59 |

Worst 1% intraday sessions (66, mean -5.21%, worst -9.51% 2001-10-17) and worst 5% (329,
mean -3.33%):

| allocation | 1%: expo / beta into | port ret | avoided | 5%: expo / beta into | port ret | avoided |
|---|---|---|---|---|---|---|
| macro only | 18.2% / 0.23 | -1.06% | +0.36pp | 48.9% / 0.80 | -2.30% | +0.79pp |
| +fast | 28.8% / 0.33 | -1.69% | +0.99pp | 55.9% / 0.91 | -2.66% | +1.15pp |
| +trim (no vt) | 28.8% / 0.33 | -1.69% | +0.99pp | 48.5% / 0.76 | -2.24% | +0.73pp |
| LIVE target | 11.5% / 0.15 | -0.71% | 0 | 31.9% / 0.53 | -1.51% | 0 |
| LIVE with trim OFF | 11.5% / 0.15 | -0.71% | +0.01pp | 38.2% / 0.66 | -1.86% | +0.35pp |
| LIVE with fast OFF | 8.5% / 0.12 | -0.52% | -0.18pp | 29.6% / 0.50 | -1.38% | -0.13pp |
| LIVE with plain vol30 | 13.0% / 0.17 | -0.82% | +0.11pp | 34.0% / 0.57 | -1.61% | +0.11pp |
| LIVE HELD | 11.4% / 0.15 | -0.70% | -- | 31.9% / 0.53 | -1.51% | -- |

Mean LIVE beta change from "into the event" to the next session: -0.021 (worst 1% gaps), -0.021
(5%), -0.052 (worst 1% intraday), -0.030 (5% intraday); unconditional mean |change| 0.083.

Reading:
- The vol target is the gap protector: it alone takes LIVE's beta into the worst 1% gaps from
  0.47 to 0.30 and avoids 0.52pp of a -1.83% average macro-row loss (0.49pp of -1.63% on the 5%
  set). The trim adds 0.32pp on the 1% set (0.23pp on 5%). Together the overlays hold LESS THAN
  HALF the macro row's beta into the worst gaps (0.29 vs 0.60; 0.61 vs 0.89 on the 5% set) and
  cut the gap loss by roughly half (-0.88% vs -1.83%).
- max(10,30) vs plain 30d: 0.15pp better on the 1% gaps, 0.09pp on the 5% -- the faster leg
  IS earlier into gaps, by a little.
- The fast overlay is the one overlay that ADDS beta into gaps (+0.13 on the 5% set, 0.78pp of
  extra loss vs the macro row on those sessions), which is the price of its re-entry job; on
  the 1% set it is neutral because those gaps mostly happen in E/F/D where it is inactive.
- "1 session later" columns: LIVE's held beta after the worst gaps is 0.27-0.28 vs 0.29-0.30
  into them, and after the worst intraday sessions 0.10 vs 0.15. The design does not sell into
  the hole after a gap; the reduction was in place before it. Delayed selling would show as
  high beta into the event and a large drop after it; the observed pattern is low beta into it
  and a change one quarter the size of a normal day's.

## 4. Reaction lag, measured (worst 20 overnight gaps / worst 20 intraday sessions)

lag = sessions between the decision whose holding window contains the event (0 = the close
before the gap / before the session) and the first decision with the signal below the
threshold. <= 0: in place going in (-k = had been in place k sessions); > 0: arrived k sessions
after; '-' = never within 60 sessions. Columns: live max(10,30) multiplier < 0.9 / 0.7 / 0.5,
plain 30d the same, trim votes >= 1/2/3, fast upgrade active, macro state left A.

Worst 20 overnight gaps:

| gap d1 | QQQ gap | state/eff | live .9 | .7 | .5 | v30 .9 | .7 | .5 | tr1 | tr2 | tr3 | fast | notA | mult into/after |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2020-03-16 | -9.46% | E/E | -14 | -11 | -9 | -11 | -9 | -3 | +55 | +56 | +56 | +32 | -13 | 0.21 / 0.19 |
| 2015-08-24 | -7.98% | E/E | +0 | +1 | +3 | +3 | +8 | - | - | - | - | +30 | -1 | 0.74 / 0.69 |
| 2008-10-24 | -7.74% | F/F | -30 | -26 | -24 | -30 | -24 | -15 | - | - | - | +5 | -205 | 0.21 / 0.21 |
| 2001-09-17 | -7.62% | F/F | -299 | -299 | +1 | -299 | -299 | +1 | +56 | - | - | +15 | -251 | 0.52 / 0.45 |
| 2020-03-09 | -6.99% | D/D | -9 | -6 | -4 | -6 | -4 | +2 | +60 | - | - | +37 | -8 | 0.37 / 0.33 |
| 2020-03-12 | -6.73% | E/E | -12 | -9 | -7 | -9 | -7 | -1 | +57 | +58 | +58 | +34 | -11 | 0.28 / 0.25 |
| 2020-03-18 | -5.78% | E/E | -16 | -13 | -11 | -13 | -11 | -5 | +53 | +54 | +54 | +30 | -15 | 0.17 / 0.18 |
| 2008-01-22 | -5.58% | E/E | -10 | +35 | +43 | -10 | +46 | - | - | - | - | - | -12 | 0.75 / 0.71 |
| 2001-09-21 | -5.38% | F/F | -303 | -303 | -3 | -303 | -303 | -3 | +52 | - | - | +11 | -255 | 0.46 / 0.47 |
| 2024-08-05 | -5.36% | D/D | -7 | -1 | - | +0 | - | - | - | - | - | - | -7 | 0.62 / 0.63 |
| 2002-06-07 | -4.33% | F/F | -481 | -481 | -20 | -481 | -481 | -20 | - | - | - | +48 | -433 | 0.40 / 0.40 |
| 2001-02-16 | -4.18% | F/F | -157 | -157 | -101 | -157 | -157 | -100 | - | - | - | +38 | -109 | 0.42 / 0.40 |
| 2025-04-03 | -4.14% | E/E | -20 | +1 | +2 | -13 | +1 | +5 | +60 | - | - | +15 | -26 | 0.79 / 0.59 |
| 2002-06-26 | -4.01% | F/F | -494 | -494 | +2 | -494 | -494 | +7 | - | - | - | +35 | -446 | 0.52 / 0.54 |
| 2020-09-08 | -3.99% | A/A | -1 | -1 | +1 | -1 | +3 | - | -58 | -48 | -48 | - | +9 | 0.61 / 0.49 |
| 2001-03-14 | -3.94% | F/F | -174 | -174 | -118 | -174 | -174 | -117 | - | - | - | +21 | -126 | 0.29 / 0.30 |
| 2008-01-23 | -3.73% | E/E | -11 | +34 | +42 | -11 | +45 | - | - | - | - | - | -13 | 0.71 / 0.75 |
| 2016-06-24 | -3.67% | D/D | +1 | +3 | - | - | - | - | - | - | - | +9 | -4 | 1.00 / 0.83 |
| 2020-02-24 | -3.66% | A/A | +1 | +4 | +6 | +4 | +6 | +12 | -12 | -12 | -12 | +47 | +2 | 1.00 / 0.81 |
| 2002-10-16 | -3.57% | C/C | -572 | -572 | -10 | -572 | -572 | -2 | +15 | - | - | +6 | -524 | 0.39 / 0.39 |

| threshold | live max(10,30): in place / after / never, median lag | plain 30d |
|---|---|---|
| mult < 0.9 | 18 / 2 / 0, median -14 | 17 / 2 / 1, median -13 |
| mult < 0.7 | 14 / 6 / 0, median -9 | 12 / 6 / 2, median -9 |
| mult < 0.5 | 10 / 8 / 2, median -3 | 9 / 5 / 6, median -2 |

Worst 20 intraday sessions (17 of the 20 are dot-com or GFC sessions in state F):

| threshold | live: in place / after / never, median lag | plain 30d |
|---|---|---|
| mult < 0.9 | 20 / 0 / 0, median -73 | 20 / 0 / 0, -73 |
| mult < 0.7 | 20 / 0 / 0, median -73 | 20 / 0 / 0, -73 |
| mult < 0.5 | 18 / 2 / 0, median -29 | 17 / 3 / 0, -29 |

Broadened to the worst 1% (66 events each):

| event set | threshold | live in place / after / never | plain 30d |
|---|---|---|---|
| worst 1% gaps | < 0.9 | 60 / 5 / 1 | 59 / 3 / 4 |
| | < 0.7 | 53 / 10 / 3 | 47 / 14 / 5 |
| | < 0.5 | 37 / 21 / 8 | 31 / 17 / 18 |
| worst 1% intraday | < 0.9 | 65 / 1 / 0 | 63 / 2 / 1 |
| | < 0.7 | 63 / 2 / 1 | 61 / 3 / 2 |
| | < 0.5 | 54 / 11 / 1 | 50 / 11 / 5 |

Reading:
- The vol target is in place before the event in 90% of the worst gaps at the 0.9 level, 80% at
  0.7 and 56% at 0.5; before the worst intraday sessions 98% / 95% / 82%. The lag that exists
  is at the DEEPEST cut, and it is the first gap of a new episode that catches it: 2015-08-24
  (mult 0.74 going in, 0.5 reached 3 sessions later), 2016-06-24 Brexit (1.00 going in),
  2020-02-24 (1.00 going in, 0.5 reached 6 sessions later), 2024-08-05 (0.62, never below 0.5).
  Once an episode is under way (COVID March, GFC October, 2001-09) the multiplier is already
  0.2-0.5 before every subsequent worst-20 gap.
- max(10,30) vs 30d: the 10-day leg buys 1-3 sessions at 0.7 and turns 6 "never" outcomes at
  0.5 into 2 on the worst-20 gaps (18 "never" into 8 on the worst 1%). That is what the
  estimator change of 09-07 bought: not earlier first reaction (median -14 vs -13 at 0.9),
  but a deeper cut inside an episode.
- The trim is irrelevant to the worst gaps (they happen in D/E/F where it does not apply; tr1
  is "-" or +50s on 17 of 20). Where the macro classifier matters it is early by a lot (notA
  median in the hundreds of sessions in the bears, -7..-26 on the SPMO-era shocks) except the
  two A-state gaps (2020-02-24, 2020-09-08) where it flipped 2 and 9 sessions AFTER. The fast
  overlay's "upgrade on" column is always positive: it re-enters 5-48 sessions after the worst
  gap, which is its job and is the source of the beta it adds into the NEXT gap (section 3b).

## 5. Execution-convention counterfactuals (harness half-rows)

Each proxy row is split into an overnight half-row (legs = 1x/3x/2x gap, XLU/cash 0) and an
intraday half-row (the exact residual), run through `run_x` (the harness loop with a per-row
trade flag), and the two halves are recombined into a daily return. V0 rebuilt this way equals
the daily harness on every row to 5.5e-5 (the cost x intraday cross-term; residual after
removing it 3.6e-16), CAGR 22.120% / Sharpe 0.9384 / MDD -32.79% on both.

- V0 live: decide close d0, fill close d0 -> new weights earn overnight(d0->d1) + intraday(d1).
- V1 next open: decide close d0, fill open d1 -> OLD weights earn the gap, new weights earn
  intraday(d1); the drift-band check and cost are taken at the open. The "morning routine with
  prior-close signals" is this same row set (the signal is d0's close either way; what moves is
  which weights sit through the gap).
- V1b: SAME trade decisions as V0 (band judged at the close) but the fill is deferred to the
  open -- the pure timing test, path effects excluded.
- V2 lag 1: decide close d0, fill close d1 -- one full session of lag, the standing reference.

26-year proxy (S/H = search / holdout Sharpe):

| variant | cost | CAGR | Sharpe | MDD | S | H | reb/yr | vs V0 |
|---|---|---|---|---|---|---|---|---|
| V0 live (close) | 4bp | 22.12% | 0.938 | -32.8% | 1.150 | 0.780 | 68 | -- |
| V1 next open | 4bp | 21.17% | 0.902 | -39.3% | 1.201 | 0.682 | 69 | -0.95pp / -0.036 / -6.5pp |
| V1b close-decide, open-fill | 4bp | 21.14% | 0.901 | -39.3% | 1.199 | 0.682 | 68 | -0.98pp / -0.037 / -6.5pp |
| V2 lag 1 session | 4bp | 19.52% | 0.851 | -36.5% | 1.116 | 0.654 | 71 | -2.60pp / -0.087 / -3.8pp |
| V0 | 10bp | 19.78% | 0.859 | -34.2% | 1.069 | 0.703 | 68 | -- |
| V1 | 10bp | 18.85% | 0.824 | -40.6% | 1.119 | 0.606 | 69 | -0.93pp / -0.036 / -6.4pp |
| V1b | 10bp | 18.82% | 0.823 | -40.6% | 1.118 | 0.606 | 68 | -0.96pp / -0.037 / -6.4pp |
| V2 | 10bp | 17.22% | 0.772 | -37.9% | 1.035 | 0.576 | 71 | -2.56pp / -0.087 / -3.7pp |
| V0 | 20bp | 15.98% | 0.728 | -36.5% | 0.933 | 0.574 | 68 | -- |
| V1 | 20bp | 15.07% | 0.693 | -42.7% | 0.983 | 0.478 | 69 | -0.90pp / -0.035 / -6.3pp |
| V1b | 20bp | 15.05% | 0.692 | -42.7% | 0.982 | 0.478 | 68 | -0.93pp / -0.036 / -6.3pp |
| V2 | 20bp | 13.50% | 0.640 | -40.2% | 0.899 | 0.446 | 71 | -2.48pp / -0.088 / -3.7pp |

Real DAILY instruments (SPMO/TQQQ/QLD/XLU/BOXX, `needs_rebalance` policy, 2015-11-02..2026-08-27):

| variant | 4bp | 10bp | 20bp |
|---|---|---|---|
| V0 live (close) | 29.69% / 1.202 / -29.5% | 27.05% / 1.116 / -30.0% | 22.76% / 0.973 / -30.8% |
| V1 next open | 30.17% / 1.223 / -24.9% (+0.48pp / +0.021 / +4.6pp) | 27.51% / 1.136 / -26.2% | 23.20% / 0.992 / -28.5% |
| V1b close-decide, open-fill | 30.08% / 1.220 / -24.9% (+0.39pp / +0.018) | 27.43% / 1.134 / -26.2% | 23.13% / 0.990 / -28.5% |
| V2 lag 1 session | 27.91% / 1.147 / -28.3% (-1.77pp / -0.055) | 25.31% / 1.061 / -29.8% | 21.08% / 0.917 / -32.3% |

Real WEEKLY rr (564 weeks; V1 = last week's weights through the first gap after d0 only): V0
30.67% / 1.260 / -25.3% vs V1 29.13% / 1.198 / -29.0% at 4bp (-1.54pp / -0.062), the same
-1.5pp at 10 and 20bp. Caveat: the weekly harness resets fully every week, so "old weights" there
are a WEEK-old target, a much larger perturbation than the daily V1; it is reported for
completeness, not weighed.

Where the proxy difference sits (pre-cost, per session): overnight V0 +6.41bp vs V1 +6.11bp
(-0.76pp/yr), intraday +3.23 vs +3.24bp (+0.03pp/yr), cost 0.51bp in both. The convention
moves ONLY the overnight P&L; V1's open fill does not buy into intraday continuation (intraday
P&L after gap-down sessions +9.43pp V1 vs +8.86pp V0 over 503 sessions).

V1 - V0 by regime (log-return pp/yr, Sharpe): dot-com +0.78 / +0.059; GFC -2.50 / -0.117; 2011
+4.80 / +0.174; 2015-16 -30.17 / -0.537; 2018 Q4 +31.17 / +1.442; 2022 +1.36 / +0.039; calm
years -2.0..+2.1; SEARCH +1.21 / +0.051; HOLDOUT -2.18 / -0.098. Block bootstrap of V1 - V0
(4bp, 2000 resamples): 20d blocks log-return CI [-2.88, +0.91] pp/yr P(<=0) 0.794, Sharpe CI
[-0.129, +0.038] P(<=0) 0.801; 60d blocks [-2.69, +1.05], 0.782 / [-0.124, +0.044], 0.789.

By what happened at the d0 close in V0 (sum of V1 - V0 overnight differences, positive = the
OLD weights were the better ones to hold through that gap): regime flip at d0 (442 sessions)
+9.65pp, of which the worst-5% gaps -8.57pp; drift-band trade at d0 (4684) -29.35pp, worst-5%
gaps +1.94pp; no trade (1449) 0. So the drift-band (mostly vol-target) trades are worth
~1.1pp/yr executed at the close rather than the open, spread thinly over thousands of sessions
and NOT concentrated in the worst gaps; the regime flips are a net loss for the close
convention on average (whipsaw) but a large gain on the gaps that matter.

The 12 sessions that decide it (beta held through the gap, V0 new / V1 old):

| gap date | QQQ gap | state d-1 -> d0 | beta V0 | beta V1 | V1 - V0 | trigger at d0 |
|---|---|---|---|---|---|---|
| 2015-08-24 | -7.98% | D -> E | 0.19 | 2.00 | -15.96pp | regime flip (mult 1.00 -> 0.74) |
| 2016-06-20 | +1.18% | A -> E | 0.25 | 1.97 | +2.33pp | regime flip |
| 2016-06-24 (Brexit) | -3.67% | E -> D | 2.00 | 0.25 | +7.34pp | regime flip |
| 2018-10-12 | +2.69% | D -> E | 0.22 | 1.64 | +4.43pp | regime flip |
| 2020-02-05 | +1.21% | A -> A | 0.00 | 2.03 | +2.46pp | drift-band (mult 1.00 -> 0.91) |
| 2020-03-10 | +3.90% | D -> E | 0.08 | 0.74 | +2.88pp | regime flip |
| 2020-03-12 | -6.73% | D -> E | 0.07 | 0.57 | -3.81pp | regime flip |
| 2020-06-12 | +2.17% | A -> A | 1.30 | 0.00 | -2.81pp | drift-band (0.99 -> 0.65) |
| 2020-11-05 | +2.27% | D -> A | 0.35 | 1.40 | +2.37pp | regime flip |
| 2021-02-23 | -1.69% | A -> A | 2.00 | 0.62 | +2.32pp | drift-band |
| 2022-09-13 | -2.88% | F -> C | 0.81 | 0.00 | +2.33pp | regime flip |
| 2026-03-23 | +1.45% | D -> E | 0.25 | 2.00 | +2.91pp | regime flip |

Max drawdown: V0 -32.8% (2015-07-20 -> 2016-06-24), V1 -39.3% (same peak, trough 2016-06-27),
V2 -36.5%. The 6.5pp of extra drawdown under V1 is the single 2015-08-24 session -- the D -> E
flip at the Friday 08-21 close (the day after a -3% session) had the book in XLU/cash before
the -7.98% Monday gap, and V1 would have held 100% QLD through it. V0 was NOT protected by the
vol target there (mult 0.74 going in; the estimator crossed 0.5 three sessions later): it was
protected by the classifier flipping at the close, which the close-execution convention turns
into being out of the gap. Brexit is the mirror (E -> D flip at Thursday's close put beta 2.0
into a -3.67% gap; V1 held 0.25). Rows like 2020-02-05 / 2020-06-12 / 2021-02-23 (A -> A, beta
0 <-> 2) are the drift-band re-entries/exits at the 3% band that happen to land before a
>1% gap; those are symmetric.

Reading: at 26 years the close convention is worth -0.98pp/yr (i.e. the LIVE convention is
better) with a bootstrap P(V1 <= V0) of 0.79 -- a point estimate that is 3/4 of one session
(2015-08-24) and reverses on the SPMO era (+1.2pp/yr proxy, +0.4-0.5pp real daily, MDD 4.6pp
better). It is not a structural edge or cost of the convention; it is the sum of which side of
~10 large gaps per decade a regime flip happened to land on. The decision that IS structural:
one full session of lag costs 2.5-2.6pp / 0.087 Sharpe on the proxy and 1.7-1.8pp / 0.055 on
real instruments, at every cost level -- because the SIGNAL is late, not because of which half
of the session the fill lands in. Execution discipline at the 15:55 snapshot remains the thing
that matters; where in the next 17 hours the fill lands does not, measurably.

## 6. Overnight-aware variants (brief; 5 candidates + 4 sign-flips, all exposure-matched to 66.21%)

Two families, both causal, T re-calibrated by bisection to live's deployed exposure:
(a) estimator sqrt(var_cc + (a - 1) x var_on) on the max(10,30) structure, a = 1.5 / 2 / 3
(Yang-Zhang's overnight term with a weight; a = 1 is live); (b) gap gate: if |gap into d0| >
trailing-252-session p95 (341 rows) or p99 (57 rows), risky x 0.5 for that decision. Sign-flips:
a = 0.5 / 0.25 / 0 (downweight or remove overnight variance) and a gate on the SMALLEST 5% of
gaps (347 rows).

| candidate | T* | CAGR | Sharpe | MDD | S | H | both-era | real weekly | real daily (4bp) |
|---|---|---|---|---|---|---|---|---|---|
| live (a = 1) | 0.200 | 22.12% | 0.938 | -32.8% | 1.150 | 0.780 | -- | 30.67 / 1.260 / -25.3 | 29.69 / 1.202 / -29.5 |
| ON x1.5 var | 0.214 | 21.80% | 0.927 | -33.1% | 1.134 | 0.774 | | 30.08 / 1.246 / -25.7 | 29.02 / 1.185 / -29.5 |
| ON x2 var | 0.229 | 21.58% | 0.919 | -33.4% | 1.125 | 0.767 | | 29.77 / 1.239 / -26.0 | 28.62 / 1.175 / -29.5 |
| ON x3 var | 0.255 | 21.35% | 0.910 | -33.2% | 1.118 | 0.759 | | 29.35 / 1.229 / -26.4 | 28.25 / 1.167 / -29.6 |
| gap gate p95, x0.5 | 0.216 | 22.37% | 0.941 | -33.4% | 1.190 | 0.757 | | 29.93 / 1.219 / -26.7 | -- |
| gap gate p99, x0.5 | 0.202 | 22.43% | 0.949 | -32.6% | 1.167 | 0.787 | YES | 30.94 / 1.267 / -25.5 | -- |
| SIGN-FLIP ON x0.5 | 0.184 | 22.47% | 0.950 | -32.4% | 1.169 | 0.784 | YES | 31.52 / 1.279 / -24.8 | 30.54 / 1.220 / -29.3 |
| SIGN-FLIP ON x0.25 | 0.176 | 22.45% | 0.949 | -32.3% | 1.168 | 0.782 | YES | 31.84 / 1.284 / -24.6 | 30.72 / 1.220 / -29.3 |
| SIGN-FLIP ON x0 (intraday-only var) | 0.169 | 22.44% | 0.948 | -32.0% | 1.166 | 0.780 | YES | 31.84 / 1.282 / -24.4 | 30.78 / 1.215 / -29.4 |
| SIGN-FLIP gate on smallest 5% gaps | 0.221 | 20.53% | 0.873 | -33.1% | 1.082 | 0.715 | | 33.23 / 1.313 / -27.1 | -- |

Controls on the best of each side:
- gap gate p99 (best non-placebo, +0.011 Sharpe): bootstrap vs live 20d [-0.006, +0.029] P(<=0)
  0.116, 60d [-0.006, +0.029] 0.110; LORO +0.007..+0.013. 57 events; not distinguishable from
  noise.
- ON x0.5 (best sign-flip, +0.012 Sharpe, +0.3pp/yr): bootstrap 20d Sharpe CI [-0.002, +0.026]
  P(<=0) 0.046, 60d [-0.001, +0.026] 0.032; LORO +0.004..+0.014; real weekly +0.019, real daily
  +0.018 with 2 more rebalances/yr.

Result: the hypothesis as posed -- that a gap-aware, overnight-UPweighted estimator would protect
better -- is rejected, and monotonically so (a = 1.5 / 2 / 3: 0.927 / 0.919 / 0.910 proxy, 1.185 /
1.175 / 1.167 real daily). The gap gate is noise. The sign-flip WINS: removing overnight variance
from the sizing signal is the direction that helps, by ~+0.01 Sharpe on the proxy (both eras),
real weekly and real daily, P ~ 0.03-0.05 at 60-day blocks. This is range_vol's finding restated
from the other side (the intraday-range estimators forecast better at level; here the
close-to-open piece of the close-to-close variance is what carries the useful information) and
it is not the question this line was asked. It is recorded as: signal, small (+0.3pp/yr,
+0.01 Sharpe), consistent across four books, one parameter, a mirror of the tested hypothesis
-- and under the change freeze. Candidate count 5 (+4 sign-flips); both-era survivors among the
5: 1 (gap gate p99, bootstrap P 0.11).

## 7. Classification

- Descriptive result (the deliverable): the losses are ~30% overnight on the full sample and in
  the long bears, 55-60% overnight in the short shocks (COVID, 2015-16), 37% in the SPMO era;
  the strategy's own split mirrors QQQ's. The design's protection is IN PLACE before 90% of the
  worst gaps and 98% of the worst intraday sessions at the 0.9 level; the residual lag is at the
  0.5 level on the first gap of a new episode. The book does not sell after gaps.
- Execution timing: not a signal either way at 26 years (P 0.79), era-dependent, decided by a
  dozen sessions; one session of lag is the only measurable harm. No change argued.
- Overnight-aware sizing: no signal in the tested direction; a small consistent signal in the
  opposite direction (downweight overnight variance), inside what range_vol already found and
  not proposed.
