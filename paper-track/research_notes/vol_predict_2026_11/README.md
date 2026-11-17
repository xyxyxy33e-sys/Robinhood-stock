# Can big QQQ days be seen coming? (2026-11-17, research only, nothing adopted)

Owner question: VIX seems to capture the dip days; rank the top 100 up and down days and check
whether the prior day's VIX and other signals predict them.

Sample: 6,833 QQQ sessions, 1999-09-16..2026-11-16, close to close. All signals are read at the
prior close. Top-100 cut-offs: up >= +4.17%, down <= -4.30%.

## Result

- **Size is predictable.** Prior-day VIX ranks big days (|r| >= 2%) with AUC 0.79; VXN 0.82; 10- and
  30-day realized vol 0.80. Walk-forward logistic (refit each January, 2005-2026): VIX only 0.775,
  rv10 only 0.759, VIX + rv10 + rv30 0.786, twelve features 0.800. The top forecast decile holds
  about a third of all big days (hit rate 36-39% vs an 11% base).
- **Direction is not.** AUC for a down day: 0.50-0.52 for every signal, 0.50 walk-forward. The
  walk-forward forecasts for "big down" and "big up" correlate 0.954.
- **VIX is coincident.** Same-day corr(QQQ return, VIX change) = -0.61; prior-day VIX change vs
  return = +0.03. VIX rose the same day on 91 of the top-100 down days, and the day before on 47
  (all days: 46%).
- **Asymmetry.** Prior VIX < 20: 42 days of -3% or worse vs 14 of +3% or better. Prior VIX >= 30:
  66 vs 91. Mean next-day return with VIX >= 30 is +0.28%.
- **Where the top 200 sit:** 1999-2002 125, 2003-07 3, 2008-09 29, 2010-19 12, 2020-26 31.
  Prior state F before 65% of both lists; state A before 6% (down) and 1% (up).
- The level of volatility carries the information; yesterday's change in VIX carries none (AUC 0.50).

## For the strategy

The vol target already uses the predictable part (realized vol). A rule that exits before big down
days also exits before big up days. The gap is the drop out of calm (2026-11-05: -6.5% after VIX
16.6), which nothing here flags. Untested follow-up: add VIX/VXN to the vol-target estimator.

## Limits

Raw-percent ranking favours 2000-02 and 2008. VIX3M from Dec 2007, VXN from Feb 2001. VVIX, SKEW
and VIX9D were not available (CBOE download blocked) and are untested. Price returns only.
Single-signal AUCs are in-sample rankings; only section 6 of analyze.log is out of sample.

## Files

`build.py` -> `days.csv`, `top100_up.csv`, `top100_down.csv`; `analyze.py` -> `analyze.log`;
`page_gen.py` + `page_template.html` -> the published page; `VIXCLS/VXVCLS/VXNCLS/NASDAQ100.csv`
are the FRED downloads of 2026-11-17.

## Since 2010 only (owner follow-up, same day)

`python3 analyze.py 2010 > analyze_2010.log`. 4,243 sessions; top-100 cut-offs +2.61% / -2.85%;
2022 holds 44 of the 200 and 2020 holds 35. The walk-forward there tests 2014-2026.

- Size still predictable, direction still not: VIX AUC 0.785 for |r| >= 2% (walk-forward 0.787);
  down-day AUC 0.49-0.52 for every signal, 0.47-0.50 walk-forward.
- **VIX now beats realized vol**: 0.785 vs 0.756 (rv10) and 0.744 (rv30); walk-forward VIX 0.787,
  rv10 0.760, VIX + rv 0.787. Over the full history they were level.
- **More of the worst days come out of calm**: prior VIX < 20 before 28% of the top-100 down days
  (8% full history) and 16% of the up days; state A or D before 53% of the down days. Moves of 3%+
  with prior VIX < 20: 22 down, 7 up.
- VIX rose the same day on 98 of the top-100 down days, the day before on 42 (all days 45%).
- Among |r| >= 2% days: 58% down above the 200-day, 44% below it; after a -2% day the next big day
  was up 62% (n = 47). A lean in which way a big day goes, not a predictor of up vs down overall.
- The big-down and big-up forecasts correlate 0.655 here (0.954 full history).

Follow-up backtest of VIX in the vol target: `../vol_target_vix_2026_11/`.
