# Pre-registration: surprise-ranked QQQ days (written before run.py was run; research only)

Data: ../days.csv (6,833 sessions 1999-09-16..2026-11-16). Right-hand sides use only p_ columns (prior close) or
quantities rebuilt from returns up to the prior close. Nothing is adopted; no strategy harness is run.

## Scores (denominator uses information through the prior close only)
- z_rv_main = ret / (max(p_rv10, p_rv30)/100/sqrt(252))   <- MAIN score (needs both rv10, rv30; first 30 sessions dropped)
- z_rv30    = ret / (p_rv30/100/sqrt(252))
- z_vix     = ret / (p_vix/100/sqrt(252));  z_vxn = ret / (p_vxn/100/sqrt(252)) (2001+)
- z_ewma    = ret / sigma_t, sigma_t^2 = 0.94*sigma_{t-1}^2 + 0.06*r_{t-1}^2 (zero-mean RiskMetrics), seeded with the mean
  squared return of the first 30 sessions, so sigma for day t contains returns up to t-1 only.
Similarity: Pearson correlation of the ranks of |z| (= Spearman) on the common sample, and overlap of the top-100 lists
(|z|, down lists, up lists).

## Look-ahead checks (printed in run.log)
1. p_rv10/p_rv30 in days.csv equal values rebuilt from returns through t-1 only.
2. p_ret1[t] == ret[t-1].
3. Perturbation test: multiply ret[t] by 5 for a set of days and rebuild the denominators; the denominators of day t
   (rv, EWMA) must not change, while day t+1 must change.

## Analyses (all on the main score unless stated; z_vix and z_ewma as robustness)
1. Top-100 surprise-down (lowest z) and surprise-up (highest z); CSVs; era counts 1999-2002, 2003-07, 2008-09, 2010-19, 2020-26 vs raw-percent lists.
2. Day-before table as analyze.py section 2 (medians, shares, state shares) for surprise-down, surprise-up, all days. Also repeated with
   the top 100 taken within 2010+ only.
3. Asymmetry: counts beyond -2,-3,-4,-5 vs +2,+3,+4,+5 sigma, all days and by prior VIX bucket (<13,13-16,16-20,20-25,25-30,30+),
   state A-F, above/below 200d; full history and 2010+. Cells where either side has <20 events are starred and carry no conclusion.
4. Predictability. Events: z<=-3, z>=+3, |z|>=3 (and 2.5 variants; counts reported). Single-signal AUC for all p_ signals
   (excluding p_state, p_vix3m level) plus built extras. Walk-forward logistic (numpy, L2=1, standardised, expanding window,
   refit each January, test the next calendar year, test years 2005-2026) for the down event. PRIMARY event z<=-3, PRIMARY model = the wide feature set
   (VIX-only and the vol-only sets are shown as references). The bar to call it "predictable":
   out-of-sample pooled AUC >= 0.60 AND >= 0.55 in each of the three eras (test years 2005-09 / 2010-19 / 2020-26; the first era is only five test years).
   If z<=-3 has fewer than 15 events in an era the 2.5 event is also reported and the verdict is stated on both. Nothing is tuned after seeing results;
   with several models and events shown, a single value just above the bar is weak evidence (multiple comparisons), and I will say so.
   Single-signal AUCs are in-sample rankings (no fitting, but signal choice is looked at after the fact).
5. Damage share for a 2x holder (daily 2*ret, no financing/fees), on days with ret <= -2%: share of loss on days with prior VIX < 20 and on days with
   z_main <= -3 (also z_vix, z_ewma), for states A or D (p_state in A/D, stand-in for "levered") and for all states; loss measured as sum of -2*ret
   and as sum of -ln(1+2*ret). Full sample and 2010+.
6. After the surprise: forward 1/5/20-session return from the close of the surprise day (mean, median, share positive) for the top-100 down and top-100 up lists
   vs all days, split by above/below 200d at the prior close. Descriptive; overlapping windows and clustering flagged; n<20 flagged.
