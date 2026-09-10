# Research line `breadth_signal` (2026-09-10): does market breadth add anything to the regime signal?

Research only. Nothing here is applied; the freeze discipline in BRIEFING.md (ADDENDUM 2026-09-10) binds.
Script: `paper-track/breadth_signal.py` (run from the repo root; `BREADTH_QUICK=1` skips the bootstrap sections).
Full log: `paper-track/research_notes/breadth_signal_run.log`.

## 0. Summary

**Question.** An outside discretionary manager downgraded on 2026-09-09 citing "192 yearly lows vs 35 yearly highs on
the NASDAQ composite". We have no new-highs/new-lows history, so this line built three families of *causal* breadth
proxies from daily closes and tested them (a) as gates / tilts on top of the LIVE design and (b) as a confirmation /
replacement input to the 50/200 classifier.

**Answer, in two parts.**

1. **The breadth rules as specified (variants i–iv, confirmation, replacement) are a clean negative.** 88 candidates,
   15 raw both-era passes, one sign-flip placebo also passes. The best per family survive the exposure-matched live
   control on paper but every one of them has a *negative* log-return point estimate (−0.4 to −0.5 pp/yr) and a block-
   bootstrap Sharpe interval that spans zero (P(≤0) 0.12–0.19 at 20d and 60d blocks). The A-row-only versions of the
   surviving gates *lose* to live in every family (e.g. qqew_60 A-only S 1.014 vs 1.111 control). The sector-
   participation and new-highs/new-lows proxies — the ones closest to what the manager quoted — fail everything.
   Nothing in the requested design beats the LIVE design on search, holdout and real rows at matched capital.

2. **One post-hoc finding that survived every control I could build, reported as a hypothesis, not evidence for a
   change.** The de-lever ladder showed the entire gain of the surviving gates came from the **D row** (price below
   50d but above 200d; live holds 100 % QLD). Restricting the gate to state D only — *"when the 60-day change of
   log(QQEW/QQQ) is in its trailing-252d bottom quintile, hold the D row in cash"* — gives, on the same 4,800 rows
   (2007-07..2026-08): 31.71 % / 1.218 / −28.5 % vs live 26.09 % / 1.006 / −33.6 %; search Sharpe 1.332 vs 1.103,
   holdout 1.065 vs 0.876; against a constant-D de-lever at *matched deployed capital* +0.205 / +0.178; block bootstrap
   vs live and vs the constant-D control P(≤0) ≤ 0.003 at 20d and 60d; leave-one-regime-out +0.16..+0.23 everywhere;
   thresholds 0.10–0.50 all work; sign-flip fails; QQQ's own 60d momentum and the vol percentile on the same D rows
   fail; a stale (lagged) signal decays monotonically; 300 random re-placements of the same episode pattern within
   state-D days give P = 0.003; real weekly rows 37.67 % / 1.490 / −22.0 % vs 31.40 % / 1.248 / −25.0 %, with the 13
   gated weeks averaging −4.3 %/wk on the QLD leg vs +2.35 %/wk on the other 66 state-D weeks.
   **Why it is only a hypothesis:** it is 1 of 170 candidates and the D-only scope was chosen *after* seeing the
   ladder; it is on for 124 of 4,800 days in 40 episodes and eight episodes carry 68 of the 86 pp it avoids; the window
   sensitivity is not monotone (10d and 20d fail, 40/60/120/250 pass, 90 is marginal); the S&P analogue (RSP/SPY) is
   much weaker in the holdout (+0.03..+0.06 vs constant-D) and the ratio-vs-200d-SMA version fails there; the proxy
   only covers 55 % of the holdout (2007-07+, no dot-com test); and it is a *timing* rule, the class that ~300 prior
   variants say does not work here. The right next step is a pre-registered confirmation (rule frozen as stated,
   tracked forward on the paper track, plus a longer equal-weight history for the dot-com era), not a change.

Today's reading (2026-09-09): qqew_60 percentile 0.82, qqew_s200 0.86 — the Nasdaq-100 equal-weight has been
*outperforming* cap-weight over 60 days, so the one rule with any support would be OFF; the last proxy row
(2026-08-26) is state A anyway, where none of the D-row logic applies. Sector participation is bottom-decile
(sec200 0.07, sec50 0.14) and RSP/SPY 20d is 0.11 — those are the readings that agree with the manager's downgrade, and
they are the proxies that failed every test here.

## 1. Data and provenance

New files (45) under `data/<SYMBOL>_daily.csv` (`d,c`, split-adjusted close, through 2026-09-09), provenance note in
`data/breadth_provenance.md`. Source: Yahoo Finance chart API via curl through the session proxy. Reason for not
using the Robinhood `get_equity_historicals` MCP tool: it returns ~60 tokens per bar into the model context — a
10-symbol × 5,000-bar call is ~3 M tokens — which made ~45 symbols × 27 years impossible; a one-symbol probe (QQEW
2006-01..06) confirmed the two sources carry the same split-adjusted closes (QQEW first real bar 2006-04-25,
19.63, matches). Cross-checks (Yahoo SPY/QQQ pulled, compared, then deleted): QQQ 6,784/6,784 repo dates present,
42 days differ by >0.2 %, all 1999-2000; SPY 6,778/6,778 present, 126 days >0.2 %, all 1999-2002; 2003+ agrees to
the cent. XLU vs the repo's `xlu_long_history.csv`: identical from 2002-07; before that the *repo* file is exactly 2×
Yahoo (an unadjusted seam at the 2025-12-05 2:1 split in the repo file; not edited, not my line). The cap-weight legs
use the repo's `qqq_long_history.csv` / `spy_long_history.csv`; the QQEW/RSP legs are forward-filled onto that
calendar.

Symbols and first dates: QQEW 2006-05-02, RSP 2003-05-01 (4:1 2006-04-27 adjusted); XLK XLF XLE XLV XLI XLY XLP
XLU XLB 1998-12-22 (XLF 2016-09-19 1.231:1 REIT spin-off applied as a split; five 2025-12-05 2:1 splits adjusted);
XLRE 2015-10-08 and XLC 2018-06-19 fetched but **not used** so the sector basket stays fixed at nine; the QQQ top-30
basket (AAPL MSFT NVDA AMZN META AVGO GOOGL TSLA COST NFLX PLTR CSCO AMD TMUS LIN PEP INTU ISRG AMAT QCOM BKNG
TXN AMGN ADBE MU HON GILD PANW ADP CMCSA) with histories from 1970 to 2020 (22 names available in 2003, 25 in 2010,
30 today).

**Survivorship statement for the NH-NL proxy.** The basket is the *2026-09* top 30. Every name in it survived and
grew into the top 30; in 2003-2015 the proxy counts new highs/lows among tomorrow's winners only. It is valid as an
illustration of what a highs-minus-lows count looks like on this calendar and nothing more; it must not be read as
a holdout test. (It failed anyway, which is the safe direction for this bias.)

## 2. Method

Harness: the project harness only (`leverage_under_trim.py` bootstrap → `rows`, `rr`, `run`, `evaluate`, `RF.eval_real`;
`downturn_review.exposure_control`; `block_bootstrap.boot/stats`). Standing figures reproduced first:
26y proxy 22.18 % / 0.913 / −33.6 %, search 1.103, holdout 0.768, exposure 67.7 %; real weekly 31.40 % / 1.248 /
−25.0 %.

Series (daily, value at the close of d0, attached to rows by date; on `rr` by d0 exact-match):
- `qqew_20`, `qqew_60`: 20d / 60d change of log(QQEW/QQQ); `qqew_s50`, `qqew_s200`: log-ratio minus its own 50d / 200d
  SMA. `rsp_*`: the same four for RSP/SPY.
- `nhnl1`: (252d new highs − 252d new lows) / names available over the fixed basket (≥15 names required); `nhnl10`:
  its 10d mean.
- `sec200`, `sec50`: fraction of the nine sector ETFs above their own 200d / 50d SMA.
- Thresholds: trailing 252-session percentile (inclusive of today, ties split). Bottom quintile = pct < 0.20; above
  median = pct > 0.50. No full-sample constant anywhere.

Same-rows rule: every proxy is scored on the rows where it has a percentile, and the live baseline is re-scored on
those rows. Holdout (3,856 rows) coverage: QQEW family 50–55 % (2007-05/2008-02 .. 2015-10), RSP family 70–75 %
(2004-05/2005-02 ..), NH-NL and sector 98–99 % (2000-09 ..). The dot-com bear is therefore untested for the
equal-weight proxies.

Variants per series (sign-flip placebo = 1 − pct, re-calibrated where a calibration exists):
i25/i50 de-lever the A/D rows by 25 %/50 % in the bottom quintile; ii extra extension-trim vote when breadth is at or
below its trailing median; iii block the 20/100 fast re-entry when bottom-quintile; iv1 one-sided tilt g =
clip(0.5+pct, 0.5, 1); iv2 two-sided tilt g = clip(0.75+0.5·pct, 0.75, 1.25) with total risky capped at 1; both iv's
have T bisected so deployed capital equals live's on the same rows — when T saturates (a de-levering-only tilt cannot
reach live's capital even with no vol target), T stays 0.20 and a multiplier c on the tilt is bisected instead (the log
prints which); conf downgrades the effective row one notch (A→B, B→C) in the bottom quintile; repl (one per family)
replaces the classifier's price-vs-50d / price-vs-200d booleans with the breadth booleans, keeps QQQ's 50>200 cross,
and applies the live overlay, trim and vol target on top.

Controls: both-era; exposure control two ways (the LIVE design scaled by k to the candidate's deployed capital — the
right control for a rule that moves capital in and out of the live design — and `downturn_review.exposure_control`,
whose baseline is the macro-only/vol30 design, printed for the record); sign flip; circular block bootstrap 20d/60d,
2,000 draws; leave-one-regime-out; real weekly rows. For the D-row finding additionally: constant-D de-lever at matched
capital, A-only / all-states scopes, threshold and window sweeps, two non-breadth gates on the same rows, lag
placebos, random-episode placebo, per-day distribution, real-row week list.

## 3. Descriptive: coverage, today's readings, alignment, forward returns by quintile

{{SEC:SERIES COVERAGE}}

Alignment: the contemporaneous pairing (QQQ d0→d1 return vs the change of the raw series over d0→d1) is clearly
non-zero for the QQEW ratios (−0.18..−0.23: equal-weight lags on up days, cap-weight leadership), NH-NL (+0.44) and
sector participation (+0.37..+0.41); the RSP ratios are ~0 contemporaneously (S&P equal-weight vs cap-weight is not
a QQQ beta). The predictive pairing (pct at d0 vs the next-day / 21d / 63d QQQ return) is ≤ |0.10| everywhere.

{{SEC:ALIGNMENT CHECK}}

{{SEC:FORWARD 21-DAY}}

Reading: no proxy has a monotone quintile pattern that holds in both eras. `qqew_60` and `qqew_s200` show Q5 > Q1 in
both eras (+0.9 / +0.5..0.9 pp per 21d); the sector and NH-NL proxies are *inverted* (weak breadth → better 21d
returns, the mean-reversion direction), and the RSP series flip sign between eras.

## 4. The requested variants: screen on the live design

{{SEC:SAME-ROWS BASELINES}}

{{SEC:VARIANT SCREEN}}

Reading. 15 of 88 pass both eras raw; 13 of those also have a real-row Sharpe above live; one sign-flip placebo
passes both eras (`sec50 iii`, +0.004 / +0.010 — a no-op-level pass; every raw pass in the ratio families has a
flip that is worse in at least one era, which is the correct direction). But every pass either (a) deploys less capital than live (i25/i50: 62–71 % vs 68–74 %) so the
exposure control decides it, or (b) is a tilt whose gain is ≤ +0.04 Sharpe in an era. `ii` (breadth as an extra
trim vote), `iii` (block fast re-entry), `conf` (classifier confirmation) and all four `repl` classifiers fail; the
replacement classifiers are much worse (full Sharpe 0.62–1.01 vs 0.94–1.03 live), i.e. breadth cannot *replace* the
price-based state machine. `iii` is essentially a no-op: it fires on so few days that the numbers equal live to the
third decimal (nhnl1 iii "passes" by +0.001/+0.002).

## 5. Deep controls on the best variant per family

{{SEC:DEEP CONTROLS on the best}}

Reading. The two ratio families pass the LIVE-scaled exposure control and their flips fail, which is the pattern a
real signal shows — but the *size* is not there: log-return point estimates are −0.42 and −0.47 pp/yr (the Sharpe
gain is all drawdown reduction: −25.7 % vs −30.0 % for the k-control), and the Sharpe intervals span zero at both
block lengths (P(≤0) 0.12–0.19). The NH-NL "best" is a no-op (+0.002). The sector best fails the k-control. By the
briefing's own bar this section is a negative.

## 6. Where the gates fire, and the de-lever ladder that exposed the D row

{{SEC:WHERE THE GATES FIRE}}

{{SEC:SURVIVOR ROBUSTNESS}}

Reading. Two things. (1) The Sharpe gain does grow with de-lever depth for qqew_60/qqew_s200 (25→75 %) with CAGR
falling in step — the leverage-dial pattern the briefing warns about — and the bootstrap intervals widen faster than
the point moves. (2) The **scope** row is the informative one: restricting the same gate to the A row *loses* to the
k-control in every family (qqew_60 A-only S 1.014 / H 0.870 vs 1.111 / 0.876), while A/D and all-states pass. The
gate's entire contribution comes from the D row.

## 7. Is it the D row? Constant-D control, every series, and non-breadth placebos

{{SEC:IS IT THE D ROW}}

{{SEC:THE D-ONLY GATE ON EVERY}}

Reading. Against the correct control for this rule — the D row held at a constant fraction q of QLD with q bisected to
the gate's deployed capital — the equal-weight gates win by a margin the earlier screen never showed: qqew_60 100 %
+0.205 / +0.178, qqew_s200 +0.091 / +0.202, and the 50 % depth wins by about half of that with CAGR *rising* rather
than falling (so this is not the leverage dial). The two non-breadth placebos on the same D rows — QQQ's own 60d
momentum percentile and the 30d-vol percentile — fail (−0.09/−0.07 and −0.03/−0.02 vs constant-D). Sector
participation and NH-NL fail here too. The RSP/SPY gates win in the search era only. The gate is ON for 89–160 of
~4,700 days (state D itself is 14 % of rows).

## 8. Deep controls on the D-only gate

{{SEC:DEEP CONTROLS ON THE D-ONLY}}

## 9. Trying to break it: per-day distribution, windows, era vs instrument, placebos, real weeks

{{SEC:PER-DAY STATISTICS}}

{{SEC:WINDOW SENSITIVITY}}

{{SEC:ERA vs INSTRUMENT}}

{{SEC:LAG AND RANDOM}}

{{SEC:REAL WEEKLY ROWS}}

{{SEC:TODAY}}

Reading, honestly in both directions.
- *For:* the gated D days have a mean QLD-leg return of −70 bp with median −4.5 bp and hit rate 0.48, vs +37 bp /
  +56 bp / 0.59 on the other 603 state-D days; the difference-in-means t is −3.7 (−3.0 search, −2.2 holdout), so the
  distribution is shifted, not just eight crash days. Thresholds 0.10–0.50 all beat live. The stale-signal placebo decays
  monotonically (lag 5: 1.163, 21: 1.068, 63: 1.019, 252: 0.852 vs actual 1.243, live 1.030) — the information is in
  the *recent* relative strength. Random re-placement of the same episode pattern among state-D days: 300 shifts,
  95th percentile 1.094, max 1.246, P = 0.003. On the same 4,661 rows the S&P version (rsp_60) also beats constant-D
  in both eras (+0.156 / +0.060), so it is not only a Nasdaq artefact, though it is much weaker. Real rows: 13 gated
  weeks, QLD leg −56 % summed, −4.3 %/wk vs +2.35 %/wk on the other 66 state-D weeks.
- *Against:* eight of 40 episodes (2022-01, 2015-08-20, 2020-02, 2008-01, 2018-10 ×2, 2011-08, 2010-06) carry 68 of
  the 86 pp; the rule is a crash-avoidance rule for "narrow-leadership pullbacks" and its value depends on those
  episodes recurring. The window sweep is not monotone: 10d and 20d fail (−0.10/−0.07 vs constant-D in search),
  40/60/120/250 pass, 90d is −0.024 in search — 60 is the best of seven, i.e. selected. RSP/SPY at 40/90/120/250 fail
  the holdout. The holdout for QQEW is 2007-07..2015-10 (55 %); the dot-com bear, where state D preceded the biggest
  losses, is untested. It is a timing rule; the briefing's meta-finding is that timing rules here have failed ~300
  times, and this one was found post hoc after 128 candidates.

## 10. Candidate count

170 candidates: 88 in the specified screen (12 series × 7 variants + 4 replacement classifiers), 40 in the survivor
ladder (5 series × 8 cells), 28 D-only cells (14 series incl. 2 non-breadth placebo series × 2 depths), 14 window-sweep
cells. Sign-flip placebos and lag/random placebos are not counted as candidates. The D-only scope was chosen after
seeing the ladder.

## 11. Verdict

The breadth proxies **do not add anything to the regime signal as a gate, tilt, confirmation or replacement on the
live design**: every requested variant is either inside noise at matched capital or worse than live, the sector and
highs/lows proxies (the ones that match the manager's argument) fail every control, and the proxies say the
Nasdaq-100 equal-weight is currently *leading*, not lagging, so even the one rule with support would be off today.
The one thing this line found — cash the 100 % QLD D row when 60-day equal-weight relative strength is bottom-quintile
— passes every control I could construct, including the ones the briefing does not require, but it is a single
post-hoc timing rule out of 170, concentrated in ~40 episodes, with a holdout that starts in 2007 and a non-monotone
window sensitivity. Classification: "signal, plausibly real, not yet large enough in *evidence* (as opposed to size)
to act on". Recommendation: no change; freeze the rule exactly as stated (qqew_60 trailing-252 pct < 0.20, effective
state D only, D row to cash, nothing else), track it forward on the paper track as a pre-registered hypothesis, and
try to extend the equal-weight history back through 2000-2002 (a Nasdaq-100 equal-weight index series, if one can be
sourced with provenance) before anyone re-tests it.
