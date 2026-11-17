# Surprise-ranked QQQ days (2026-11-17, research only, nothing adopted)

Re-ranks the QQQ sessions in `../days.csv` by move relative to the vol that was normal at the time. Files: `PLAN.md` (pre-registration, with
one dated addendum), `run.py` -> `run.log` (all tables), `top100_surprise_down.csv`, `top100_surprise_up.csv`, `asymmetry_cells.csv`.
Main score z = ret / (max(p_rv10, p_rv30)/100/sqrt(252)); robustness z_vix, z_vxn, z_ewma (lambda 0.94). 6,803 days have z (6,483 for VXN).
Look-ahead checks are in run.log section 0: the denominators equal values rebuilt from returns through t-1 (to 6-decimal rounding), p_ret1[t] = ret[t-1],
and perturbing ret[t] leaves the day-t denominator unchanged in 25 of 25 random days x 2 estimators (day t+1 changes every time).

## Results (numbers are from run.log)
- **Rankings.** Rank correlation of |z|: main vs rv30 0.992, vs EWMA 0.993, vs VXN 0.965, vs VIX 0.945. Top-100 overlap is much lower: main vs EWMA 79, vs rv30 76,
  vs VXN 56, vs VIX 37 (of 100). The VIX-based list is a different list: 56 of its 100 down days are in 1999-2002, as in the raw ranking.
- **Years.** Raw lists: 1999-2002 61 down / 64 up, 2008-09 16 / 13, 2010-19 6 / 6, 2020-26 17 / 14. Main surprise lists: 1999-2002 3 / 12, 2003-07 11 / 22,
  2008-09 8 / 8, 2010-19 46 / 35, 2020-26 32 / 23. The main-score cut-offs are low: down z <= -2.36 (so some "surprise" days are only -1.1% to -2%),
  up z >= +2.17. Several top surprise days have a tiny denominator (2016-09-09 -2.5%, prior rv30 6%, z -6.5).
- **Day before (main score, full history).** Surprise-down days: prior VIX < 20 on 68% (all days 61.8%), prior VIX >= 30 on 6% (9.2%), below the 200-day 16% (26.4%),
  prior-day |move| >= 2% on 4% (16.1%), state A or D 84% (65.1%) with A alone 67.7% (52.4%), state E/F 11% (20.2%). Median prior VIX 16.7 vs 17.8, median rv30 13.6 vs 18.1.
  Surprise-up days look more like stress: below the 200-day 35%, VIX >= 25 31%, state F 20.6%. 2010+ (top 100 within 2010+): down days prior VIX < 20 74% (all 71.3%), state A/D 91% (78.2%).
  So yes, surprise-downs come from calm and from the leveraged states, but part of that is the definition: a calm denominator makes a given drop a bigger z.
  The z_vix list is the opposite (prior VIX < 20 on only 39%; state F 41%).
- **Asymmetry (main z, down/up counts).** All days: beyond +-2 sigma 188/143 (1.31), +-3 42/17 (2.47), +-4 9/3, +-5 5/2. 2010+: 126/83 (1.52), 34/11 (3.09), 8/2, 5/1.
  Only the +-2 cells and a few +-3 cells have >= 20 on both sides; most +-3..5 cells are starred in run.log and carry no conclusion. Where cells are large enough:
  above the 200-day 149/87 (1.71) at 2 sigma, below it 34/51 (0.67); state A 113/63 (1.79); VIX 13-16 53/26 (2.04); VIX 30+ 12/26 (0.46, starred). At 3 sigma, summing the printed
  VIX < 20 cells gives 31 down vs 8 up (full) and 27 vs 7 (2010+), but each individual bucket is starred. Same direction under z_ewma and z_vix (2010+ at 3 sigma: 4.30 and 4.12 overall).
  Down surprises are more common than up surprises in calm, uptrend markets; in stress and below the 200-day the ratio flips to under 1.
- **Predictability (bar: pooled OOS AUC >= 0.60 and >= 0.55 in each of three eras).** Event counts at z <= -3: 42 total (8 in 1999-2009, 21 in 2010-19, 13 in 2020-26); z >= +3: 17; |z| >= 3: 59.
  Walk-forward, down z <= -3: WIDE (20 features) 0.714 pooled (eras 0.960 [1 event] / 0.660 / 0.769); VIX only 0.549; rv10+rv30 only 0.676; VIX+rv 0.708. WIDE top decile: hit 3.1% vs 0.78% base,
  14 of 35 events (40%). **Literally, WIDE passes the bar, but the first era is not informative** (it is 2009 only: the guard skipped test years with < 5 training events). At 2.5 sigma
  (81 events) WIDE gives 0.714, eras 0.594 / 0.719 / 0.767. **Mostly a denominator effect:** the vol-only model (rv10+rv30, the denominator itself) gets 0.676; the extra features add about 0.04.
  VIX alone does not beat 0.55 (0.549). In single-signal terms the best are rv30 (AUC 0.283, i.e. 0.717 inverted: low realized vol), VRP 0.709, 5-day VIX change 0.698, days since a 2% move 0.670;
  day of week, prior quiet day, VIX/VIX3M, VXN/VIX are near 0.5 to 0.55. Section 4d (post-hoc, flagged): the same pattern holds for z<=-3 AND ret<=-2% (WIDE 0.700, rv-only 0.654), while raw ret <= -3% is
  predicted at 0.83 (it is a size effect, VIX alone 0.776). Single-signal AUCs for events with 17-42 events have standard errors near 0.05-0.07.
  Plain reading: a surprise-down is more likely when realized vol is already low and the market is up and quiet, but that is what "surprise" means; the useful content is a ~3-4x lift of a 0.7% event, with few events.
- **Share of damage (2x holder, 2*ret, no financing; days with ret <= -2%).** All states, full history: 578 days; prior VIX < 20 on 26.6% of them and 22.0% of the loss; z <= -3 on 6.9% of them and 8.0% of the loss.
  State A or D (full): 195 days; prior VIX < 20 = 59.5% of days / 57.1% of loss; z <= -3 = 16.9% / 20.1%. 2010+: all states 232 days, VIX < 20 35.9% of loss, z <= -3 16.2%;
  state A/D 139 days, VIX < 20 57.4%, z <= -3 23.7%. State E/F for contrast: z <= -3 2.9% (full). So for the levered states, calm-origin drops are the majority of the -2% damage, but
  most of those are ordinary 2-3% down days after VIX under 20, not extreme surprises; the extreme (z <= -3) part is about a fifth of the loss. State A/D is a stand-in; D's gate is not modelled.
- **After the surprise (descriptive, main z, from the event-day close).** Top-100 down: next 1 / 5 / 20 days mean +0.14% / +0.39% / +0.40%, median +0.21 / +0.57 / +1.81, positive 57% / 54% / 59%
  (all days +0.04 / +0.21 / +0.81, median 0.10 / 0.46 / 1.51, positive 54 / 57 / 62). Above the 200-day (n 83): 20-day mean +1.06%, 63% positive (all-days above: +1.06%, 64%). Below the 200-day (n 16, <20):
  20-day mean -2.98%, 38% positive: small, no conclusion. Top-100 up: 1 / 5 / 20 mean -0.01 / +0.41 / +0.71, positive 61 / 64 / 64; below the 200-day n 35. Nothing stands out against all days at these sample sizes;
  5- and 20-day windows overlap (events form 71 down and 78 up clusters separated by > 20 sessions).

## Limits
Price returns only; the event counts at 3 sigma are small (42 down, 17 up). The z lists lean on a small denominator, so low-vol periods (2016-17, 2019) are over-represented in the main list.
Single-signal AUCs are in-sample rankings and several signals were scanned. The first-era AUC of the walk-forward is not informative.
