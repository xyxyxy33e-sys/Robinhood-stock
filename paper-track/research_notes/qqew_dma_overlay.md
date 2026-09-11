# Research line `qqew_dma_overlay` (2026-09-11): the live DMA classifier computed on QQEW, overlaid on the harness

Research only. Nothing here is applied; the discipline in BRIEFING.md (ADDENDUM 2026-09-10) binds. No commit, no trade, no artifact,
no existing data file edited. Script: `paper-track/qqew_dma_overlay.py` (run from the repo root, ~90 s; `QDMA_STAGE=desc|overlay|boot`,
`QDMA_NB=<draws>`). Full log: `paper-track/research_notes/qqew_dma_overlay_run.log`.

Owner's brief: *"gather all QQEW data, compute the same multiple DMA lines and overlay to the backtest data, see if you can find anything,
relative to QQQ and such."*

## 0. Summary

- **What was done.** state.py's own classifier (`compute_states` 50/200 with 1 % hysteresis, `compute_fast_states` 20/100,
  `compute_extension_gaps` 100/150/200, `effective_state`, `extension_scale`) was run unchanged on the QQEW close series and on the
  QQEW/QQQ ratio, exactly as the harness runs it on QQQ, and attached by date to the same 4,800 harness rows (2007-07-27..2026-08-26) the
  breadth lines used. Same-rows live reproduced: 26.09 % / 1.006 / −33.6 %, S 1.103, H 0.876 (standing 26y and real figures reproduced first).
- **Descriptive answer (the core deliverable): the average stock's trend read is an echo of the index's, with a small lead on breakdowns
  and a small lag on recoveries.** Effective states agree on 83.1 % of days (kappa 0.70); QQEW reads *worse* than QQQ on 11.9 % of days and
  *better* on 5.0 %. For QQQ downgrades the matching QQEW change came earlier on 38 %, the same day on 42 %, later on 20 % of the events
  (median lag 0, Q1 −3 sessions, mean −2.2); for upgrades earlier 26 %, same day 40 %, later 34 % (median 0, Q3 +2). The lead is
  real but short and concentrated in the break of the 200d (D→E: QQEW earlier 65 %, median −2 sessions; E→F median −4..−11) while the
  recovery (D→A) is where QQEW lags (later 49–53 %, mean +4..+5). The cross-correlation of daily rank changes is 0.42 contemporaneous
  and ≤ 0.08 at any other lag. Both eras agree on all of this.
- **Event study: the divergences carry no forward information.** After "QQEW downgrades while QQQ holds" (80 events) forward QQQ and
  live-design returns are *positive* and indistinguishable from the circular-shift null (20d +1.6 % / +2.5 %, P 0.65 / 0.61); the same
  for "QQEW upgrades while QQQ holds". The persistent "narrow" flag (QQEW rank > QQQ rank, 570 days) has lower but not significant forward
  returns (P 0.09–0.36) and on D days it is *not* negative at all (20d +0.4 %, P 0.27; holdout +1.5 %). The pre-registered pct<0.20
  flag on the same D days is −1.9 % (P 0.036) — a different set of days: Jaccard 0.15.
- **Overlays: a clean negative.** 18 candidates (a: confirmation ×2; b: QQEW-only classifier ×2; c: divergence as vote / D-gate ×2 /
  fast-block / de-lever ×2; d: QQEW gaps replace / sum / max; e: ratio state gate ×2 + vote; two combinations with the pre-registered
  gate). **None of the 16 stand-alone variants beats live in both eras**, before or after the corrected exposure control; every
  confirmation / replacement variant loses the holdout by −0.05..−0.14 Sharpe; the divergence D-gate is +0.066 / −0.069 (its 124 gated
  days are as many as the pct gate's but only 33 overlap) and its bootstrap interval is centred on zero. The two combinations pass both
  eras only because they contain the pct gate, and both are *worse* than the pct gate alone (AND: −0.137 Sharpe, 20d CI [−0.264, −0.029];
  OR: −0.060, and its sign-flip also passes, i.e. the pct component carries it). Real rows: 14 of 18 below live's 1.248; the two that
  are above are the combinations, both below the pct gate's 1.490.
- **Verdict.** The QQEW DMA lines add nothing beyond what the pct<0.20 D-gate already captures, and the divergence gate is **not** the same
  rule under another name: it selects mostly different D days (Jaccard 0.15), and the days it selects that the pct gate does not (91) have a
  *positive* next-day QLD leg (+48 bp). What the pct gate measures — a three-month *drift* of equal-weight relative strength — is not what a
  state comparison measures — whether equal-weight is *currently* on the other side of a moving average. The descriptive picture is the
  useful output: the equal-weight read is coincident with the index's, leads its 200d breaks by a couple of sessions and lags its recoveries
  by a few, so a confirmation rule built on it can only cost recovery days, which is what the harness shows. Candidate count this line: 18;
  cumulative 258.
- **Today's reading (provisional after 2026-09-04).** On 2026-09-10 QQEW's macro state flipped to D (below its 50d with the buffer;
  fast D since 09-01) and the ratio has been D since 09-08, while QQQ is still A (−0.3 % vs its 50d, inside the 1 % band; fast D since
  09-01). That is a live "QQEW down, QQQ holds" event — the type the event study finds uninformative — and the pre-registered gate is off
  (pct 0.82, QQQ effective A).

## 1. Data and provenance

- QQEW: `data/QQEW_daily.csv` (Yahoo, 2006-05-02..2026-09-09, split-adjusted, provenance in `data/breadth_provenance.md`). Extension:
  the Yahoo chart API returned "Too Many Requests" on every attempt this session (query1/query2, browser User-Agent, through the proxy), so
  ONE row (2026-09-10, 156.6521) was added from the Robinhood MCP `get_equity_historicals` (day bars, split-adjusted) cross-checked with
  `get_equity_quotes` (official settled close, `sip-list-exchange-close`, not interpolated) and saved as a NEW file
  `data/QQEW_daily_ext.csv` (5,122 rows); provenance appended to `data/breadth_provenance.md`. Cross-check of the overlap: Robinhood
  QQEW closes match the file to the cent on all 12 common sessions 2026-08-24..09-09; Robinhood QQQ matches `qqq_long_history.csv` on
  09-03/04. QQQ closes for 09-08/09/10 (718.36, 716.31, 708.69) are used only for the provisional today's reading (a literal in the
  script, not a data file).
- QQQ: the harness's `qqq_long_history.csv` (the `qqq`/`px` objects of the bootstrap). Calendar: QQEW printed on every harness session
  from 2006-05-02 (0 forward-fills); QQEW has one session the harness lacks (2011-01-03). The classifier is computed on QQEW's own
  session calendar (5,122 sessions) and read at the harness row's d0; the 200d warm-up ends 2007-02-15, before the first row used.
- Rows: the 4,800 rows on which the pre-registered percentile exists (`sub_rows('qqew_60')` from the verbatim exec of
  `breadth_dgate_2000.py` sections 0–3, as `dgate_anatomy.py` does), so every table here is on the same rows as the earlier notes. Real
  rows: the 564 weekly SPMO-era rows (`rr`), QQEW/ratio states attached at d0.

## 2. Method

Harness only: `leverage_under_trim.py` bootstrap → `rows`, `rr`, `run`, `evaluate`, `RF.eval_real`; `downturn_review.exposure_control`
(the 2026-09-11-corrected version that bisects k over the TRUE live function and requires `eff`/`gaps`); `block_bootstrap.boot` (2,000
draws, 20d/60d circular blocks); rebalances/yr through a verbatim source copy of `improvement_search.run` with a counter, asserted equal
to the harness run (the `vol_term_structure.py` pattern). Row attachment, trailing percentile, `trimmed`, `scale_risky`, `gate_fn`,
`const_D`, `calib_q` are the exec'd sections of `breadth_dgate_2000.py`. The classifier is never re-implemented: the QQEW and ratio
states are `state.compute_states` / `compute_fast_states` / `compute_extension_gaps` / `effective_state` called on the other series
(a check in the log: the same calls on the QQQ file reproduce all 6,575 harness `state`/`eff` values with 0 mismatches).

Definitions. Rank A<B<C<D<E<F. `div` = rank(QQEW eff) − rank(QQQ eff); "narrow" = div ≥ 1, "broad" = div ≤ −1. Lead/lag: for every
QQQ state change at row i (from a to b), the nearest QQEW change within ±60 sessions in the same direction (down = rank rises) —
"strict" requires the same destination state b, "loose" any destination; lag = j − i (negative = QQEW earlier); ties prefer the lead.
Event study: forward h-session return from the d0 close (QQQ from the harness closes; live design from `run(RQ, LIVE)` daily returns),
h = 5/10/20/60; placebo = 2,000 circular shifts of the flag vector, P<= = share of shifts with a mean ≤ the actual (P>= the reverse).
Overlays: each candidate is a weight function on `trimmed(eff, gaps)` + the live vol target; sign-flip placebo = the opposite condition
(better-of instead of worse-of, div ≤ −1 instead of div ≥ 1, ratio in A/B/C instead of D/E/F); the QQEW-gaps variants have no signed
flip and are reported as such. Both-era = beats the k-live control on search AND holdout Sharpe.

## 3. Descriptive: occupancy, agreement, worse/better, transition timing

```
1a. STATE OCCUPANCY (% of days), same 4,800 rows; macro = 50/200 six-state, eff = after the 20/100 fast overlay
  series                era             A       B       C       D       E       F   A+B(risk-on)  D  E+F
  QQQ macro             full        58.4%    5.9%    5.1%   15.1%    5.7%    9.7%    64.3%    15.1%  15.5%
  QQQ eff               full        64.4%    1.5%    5.7%   15.1%    5.7%    7.5%    65.9%    15.1%  13.2%
  QQEW macro            full        54.0%    5.5%    7.0%   15.6%    4.9%   13.0%    59.5%    15.6%  17.9%
  QQEW eff              full        61.5%    0.8%    7.6%   15.6%    4.9%    9.6%    62.3%    15.6%  14.5%
  ratio macro           full        20.0%    4.5%   18.8%    8.3%    2.9%   45.6%    24.5%     8.3%  48.4%
  ratio eff             full        29.4%    0.9%   20.3%    8.3%    2.9%   38.3%    30.3%     8.3%  41.1%
  (search / holdout rows in the log; QQEW is 3-5 pp less in A and 2-3 pp more in F than QQQ in both eras)
  extension-trim votes on effective-A days:  QQQ 3092 days votes 0/1/2/3 = 2294/230/277/291 (mean scale 0.821)
                                             QQEW 2951 days 2399/186/191/175 (mean scale 0.877); ratio: never extended
```

```
1b. AGREEMENT MATRIX, EFFECTIVE states: rows = QQQ, cols = QQEW, cell = % of the 4800 days
               A       B       C       D       E       F     row%
  QQQ A    58.1%    0.4%    1.4%    4.4%    0.1%    0.1%   64.4%
  QQQ B     0.7%    0.3%    0.4%    0.0%    0.0%    0.0%    1.5%
  QQQ C     0.9%    0.1%    4.5%    0.0%    0.0%    0.2%    5.7%
  QQQ D     1.4%    0.0%    0.2%   11.0%    2.2%    0.3%   15.1%
  QQQ E     0.3%    0.0%    0.4%    0.2%    2.5%    2.4%    5.7%
  QQQ F     0.1%    0.0%    0.7%    0.0%    0.1%    6.6%    7.5%
  col%       61.5%    0.8%    7.6%   15.6%    4.9%   9.6%
  agreement 83.1% (chance 43.4%, Cohen kappa 0.701).  Macro states: agreement 80.1% (chance 36.1%, kappa 0.688).
  conditional P(QQEW eff | QQQ eff): A -> A 90.2%, D 6.8%;  D -> D 72.8%, E 14.9%, A 9.1%, F 2.2%;  E -> E 43.6%, F 41.1%;  F -> F 88.5%, C 9.2%
```

```
1c. IS QQEW'S READ WORSE OR BETTER THAN QQQ'S?  ('worse' = QQEW rank higher)
  basis     era           n   worse    same  better  mean(rank diff)  worse by >=2 | QQQ-eff-A days: worse | QQQ-eff-D days: worse (=QQEW E/F)
  macro     full       4800   15.1%   80.1%    4.9%  +0.179              6.7%     |  13.5%                |  18.2%
  macro     search     2719   14.0%   81.1%    4.9%  +0.185              7.2%     |  12.4%                |  19.9%
  macro     holdout    2081   16.4%   78.7%    4.9%  +0.171              6.0%     |  15.2%                |  16.2%
  eff       full       4800   11.9%   83.1%    5.0%  +0.119              6.5%     |   9.8%                |  17.1%
  eff       search     2719   11.7%   83.6%    4.7%  +0.134              6.8%     |   9.8%                |  18.3%
  eff       holdout    2081   12.1%   82.4%    5.5%  +0.099              6.2%     |   9.7%                |  15.7%
```

```
1d. TRANSITION TIMING, EFFECTIVE states (QQQ changes 235, QQEW changes 269 = 12.3 vs 14.1 per year).  lag < 0 = QQEW moved EARLIER.
  strict downgrades  n  121 matched  108 (89.3%)  QQEW earlier  38.0%  same day  41.7%  later  20.4% | Q1 -3.0 median +0.0 Q3 +0.0 mean -2.2
      search          n   64 matched   59 (92.2%)  QQEW earlier  35.6%  same day  44.1%  later  20.3% | Q1 -3.0 median +0.0 Q3 +0.0 mean -2.5
      holdout         n   57 matched   49 (86.0%)  QQEW earlier  40.8%  same day  38.8%  later  20.4% | Q1 -3.0 median +0.0 Q3 +0.0 mean -1.9
  strict upgrades    n  114 matched   97 (85.1%)  QQEW earlier  25.8%  same day  40.2%  later  34.0% | Q1 -1.0 median +0.0 Q3 +2.0 mean +0.8
      search          n   60 matched   51 (85.0%)  QQEW earlier  25.5%  same day  35.3%  later  39.2% | Q1 -0.5 median +0.0 Q3 +2.5 mean +0.9
      holdout         n   54 matched   46 (85.2%)  QQEW earlier  26.1%  same day  45.7%  later  28.3% | Q1 -0.8 median +0.0 Q3 +1.0 mean +0.7
  loose  downgrades  n  121 matched  121 (100%)   QQEW earlier  31.4%  same day  47.1%  later  21.5% | Q1 -1.0 median +0.0 Q3 +0.0 mean -1.0
  loose  upgrades    n  114 matched  114 (100%)   QQEW earlier  27.2%  same day  41.2%  later  31.6% | Q1 -1.0 median +0.0 Q3 +1.0 mean +1.0
  by transition type (strict):
    A>D    n   60 matched   56  QQEW earlier  37.5%  same day  41.1%  later  21.4% | Q1  -3.0 median  +0.0 Q3  +0.0 mean  -2.2
    D>A    n   52 matched   51  QQEW earlier  15.7%  same day  35.3%  later  49.0% | Q1  +0.0 median  +0.0 Q3  +3.0 mean  +3.7
    F>C    n   23 matched   23  QQEW earlier  34.8%  same day  52.2%  later  13.0% | Q1  -1.0 median  +0.0 Q3  +0.0 mean  -0.7
    D>E    n   19 matched   17  QQEW earlier  64.7%  same day  29.4%  later   5.9% | Q1  -3.0 median  -2.0 Q3  +0.0 mean  -3.5
    C>F    n   17 matched   17  QQEW earlier   0.0%  same day  76.5%  later  23.5% | Q1  +0.0 median  +0.0 Q3  +0.0 mean  +2.8
    C>A    n   12 matched   12  QQEW earlier  41.7%  same day  41.7%  later  16.7% | Q1  -5.2 median  +0.0 Q3  +0.0 mean  -4.7
    E>F    n    8 matched    8  QQEW earlier  62.5%  same day  12.5%  later  25.0% | Q1 -11.5 median  -4.0 Q3  +0.5 mean  -5.8
  REVERSE (QQEW change -> nearest QQQ change) downgrades n 137 matched 115: QQQ earlier 19.1%, same day 39.1%, later 41.7% (mean +3.8)
  REVERSE upgrades n 132 matched 111: QQQ earlier 33.3%, same day 35.1%, later 31.5% (mean +1.2)
  cross-corr of daily rank changes corr(dQQQ_t, dQQEW_{t+k}): k=-1 +0.078  k=0 +0.424  k=+1 +0.056  k=+2 +0.047; |k|>=3: <= 0.03
  (macro-state version in the log: downgrades earlier 44% / same 36% / later 20%, mean -3.6; upgrades earlier 30% / same 29% / later 40%,
   mean +2.4; D>E earlier 65% median -2; E>F median -11; D>A later 53% mean +5.4)
```

Reading. QQEW's read is the index's read: 83 % same-day agreement of the effective state, kappa 0.70, and a rank-change cross-correlation
that is 0.42 at lag 0 and under 0.08 at every other lag. Where they differ, QQEW is on the worse side 2.4× as often as on the better side
(11.9 % vs 5.0 %) — equal-weight spends more time in C/F and less in A, i.e. the average stock has a weaker trend than the cap-weighted
index, in both eras. On timing: for downgrades the median lag is zero and the distribution is skewed to the lead (Q1 −3 sessions, 38 %
earlier vs 20 % later); for upgrades it is skewed to the lag (Q3 +2, 34 % later vs 26 % earlier). The lead is concentrated in the
breakdowns through the 200d (D→E: 65 % earlier, median −2; E→F: median −4 effective / −11 macro), and the lag in the recoveries (D→A:
49–53 % later, mean +4..+5). QQEW also changes state 15 % more often (14.1 vs 12.3 per year) and 15 % of its changes have no QQQ
counterpart within 60 sessions — the "false" divergences. The reverse table confirms the asymmetry: when QQEW downgrades first, QQQ
follows later 42 % of the time; when QQEW upgrades, QQQ is as likely to have moved already. Search and holdout give the same numbers to
within a few points. So: lead on the way down by a couple of sessions, lag on the way up by a few, echo the rest of the time.

## 4. Event study

```
2a. TRANSITION-DAY events (effective states): mean forward return from the d0 close; P<= / P>= from 2,000 circular shifts
  flag                          n |  QQQ 5d   P<=  P>=  QQQ 10d  P<=  P>=  QQQ 20d  P<=  P>=  QQQ 60d  P<=  P>= | live 5d  P<=  P>=  live 10d P<=  P>=  live 20d P<=  P>=  live 60d P<=  P>=
  QQEW down, QQQ holds         80 |  +0.52  .712 .288   +0.80  .614 .387   +1.57  .647 .352   +4.39  .612 .388 |  +0.92 .828 .172   +1.04 .469 .531   +2.47 .614 .386   +7.96 .754 .246
  QQEW up, QQQ holds           84 |  +0.35  .535 .465   +0.45  .308 .692   +0.95  .280 .720   +3.58  .364 .636 |  +0.47 .458 .542   +0.82 .336 .664   +2.06 .464 .536   +6.54 .485 .514
  both down                    57 |  +0.18  .361 .638   -0.31  .048 .952   +0.81  .256 .745   +5.19  .830 .170 |  +0.33 .339 .661   +0.27 .145 .855   +0.68 .089 .910   +5.80 .344 .655
  both up                      47 |  +0.60  .753 .247   +1.83  .976 .025   +3.13  .983 .018   +6.58  .978 .022 |  +0.72 .641 .359   +2.44 .971 .029   +4.16 .972 .028  +11.22 .997 .003
  QQQ down alone               63 |  -0.37  .024 .977   -0.03  .095 .905   +1.65  .689 .311   +2.71  .177 .823 |  -0.04 .102 .898   -0.23 .026 .974   +1.83 .323 .677   +6.31 .459 .541
  QQQ up alone                 67 |  +0.44  .631 .368   +0.33  .261 .740   +0.81  .223 .777   +2.13  .075 .924 |  +0.89 .788 .211   +0.88 .378 .622   +1.61 .282 .718   +4.18 .090 .910

2b. PERSISTENT divergence (every day): narrow = QQEW worse (div>=1), agree, broad = QQEW better (div<=-1)
  narrow (div>=1)             570 |  +0.08  .131 .870   +0.11  .087 .913   +0.62  .139 .861   +3.40  .357 .642 |  +0.31 .219 .781   +0.41 .117 .882   +1.34 .182 .818   +6.63 .503 .497
  agree (div=0)              3989 |  +0.35  .795 .205   +0.69  .782 .217   +1.33  .600 .401   +3.79  .346 .654 |  +0.58 .850 .150   +1.15 .853 .147   +2.21 .638 .361   +6.23 .277 .724
  broad (div<=-1)             241 |  +0.40  .576 .424   +1.09  .807 .193   +2.38  .896 .104   +6.74  .923 .076 |  +0.20 .220 .780   +1.05 .492 .508   +3.04 .774 .226   +9.75 .858 .142
  narrow, QQQ eff A           302 |  +0.09  .214 .785   +0.15  .155 .845   +0.56  .147 .853   +1.97  .090 .909 |  +0.06 .115 .885   +0.04 .059 .941   +0.98 .135 .865   +4.34 .137 .863
  narrow, QQQ eff D           124 |  +0.34  .501 .499   +0.03  .234 .766   +0.42  .273 .728   +6.82  .801 .199 |  +0.77 .638 .362   +0.42 .281 .719   +0.57 .210 .789  +10.61 .830 .171
  agree, QQQ eff D            529 |  +0.71  .950 .051   +1.46  .968 .032   +2.78  .969 .031   +5.51  .853 .147 |  +1.18 .977 .024   +2.44 .986 .014   +4.64 .990 .011   +9.79 .950 .051
  broad, QQQ eff D             74 |  -0.00  .257 .743   +0.35  .346 .653   +2.11  .706 .294   +5.44  .689 .311 |  -0.18 .152 .848   +0.39 .276 .725   +3.04 .695 .305   +7.43 .587 .413
  pct<0.20 (pre-reg), eff D   124 |  -1.32  .004 .996   -2.05  .009 .992   -1.91  .036 .964   -1.31  .058 .942 |  -2.14 .003 .997   -3.17 .004 .996   -3.99 .007 .993   -2.32 .037 .963
2c. by era: narrow-D search (70) QQQ 20d -0.41 (P<= .166), live 20d -1.21 (.112), 60d +10.0 / +14.3;  narrow-D holdout (54) QQQ 20d +1.49
    (.547), live +2.89 (.624);  QQEW-down/QQQ-holds S (40) 20d +2.09 / +2.72;  H (40) +1.05 / +2.21 -- none with P <= 0.05 in either direction.
```

Reading. Neither divergence *event* predicts anything: after QQEW downgrades while QQQ holds, QQQ is up +1.6 % over 20 sessions and the
live design +2.5 %, at P 0.65 / 0.61 — the same as an ordinary day. The only P ≤ 0.05 cells are the trivial ones (QQQ's own downgrade
day is followed by a weak week; "both up" is followed by a strong month — the trend the classifier is built on). The *persistent* narrow
flag is a mild general negative (5–20d forward QQQ +0.1..+0.6 % vs +0.4..+1.3 % when the reads agree; P 0.09–0.14), which is the
"weak general negative" dgate_anatomy already found in the pct series and which no gate could monetise; on D days specifically it is *not*
negative (+0.4 % at 20d; the search era −0.4 %, the holdout +1.5 %), whereas the pre-registered percentile flag on the same 124-day count is
−1.9 % (P 0.036) with the live design at −4.0 % (P 0.007). The two flags pick different days (section 6).

## 5. Overlays through the harness

```
3. OVERLAYS on the 4,800 rows.  same-rows live 26.09% / 1.006 / -33.6% S 1.103 H 0.876 exp 72.1% rebal/yr 48.4 | real 31.40% / 1.248 / -25.0%
   REFERENCE pre-registered pct<0.20 D-gate (not a candidate): 31.71% / 1.218 / -28.5% S 1.332 H 1.065 exp 70.0% | vs live +0.229/+0.189
     | k-live k=0.970 S 1.107 H 0.875 -> +0.225/+0.190 | real 1.490 | rebal/yr 49.6
  candidate                            CAGR/Sh/MDD      S     H    exp | vs live  S/H  | k-live k    S     H  -> dS/dH     | flip dS/dH    | real   dReal | reb/yr | both>ctrl | on days
  a  conf worse-of            24.85% / 1.006 / -35.6%  1.169 0.782  69.6% | +0.066/-0.094 | 0.966 1.108 0.875 -> +0.061/-0.093 | +0.030/+0.037 | 1.173 -0.075 |  51.1 |     - |   570
  a  conf D/E/F side          25.94% / 1.032 / -34.1%  1.204 0.799  69.6% | +0.101/-0.078 | 0.966 1.108 0.875 -> +0.096/-0.077 | +0.006/+0.003 | 1.206 -0.042 |  50.5 |     - |   467
  b  QQEW-only + QQEW gaps    24.58% / 0.959 / -41.6%  1.112 0.741  74.4% | +0.010/-0.135 | 1.032 1.099 0.876 -> +0.013/-0.135 |    (none)     | 1.109 -0.139 |  49.9 |     - |  1351
  b  QQEW-only + QQQ gaps     26.35% / 1.040 / -37.4%  1.199 0.823  70.6% | +0.097/-0.053 | 0.980 1.105 0.875 -> +0.094/-0.052 |    (none)     | 1.165 -0.083 |  52.7 |     - |   811
  c.i  narrow = extra vote    24.72% / 0.986 / -32.8%  1.059 0.888  70.2% | -0.044/+0.012 | 0.973 1.106 0.875 -> -0.047/+0.013 | +0.000/+0.000 | 1.255 +0.007 |  49.8 |     - |   301
  c.ii narrow D-gate 100%     25.46% / 1.018 / -35.6%  1.174 0.806  69.7% | +0.071/-0.070 | 0.966 1.108 0.875 -> +0.066/-0.069 | +0.014/-0.015 | 1.244 -0.004 |  48.9 |     - |   124
  c.ii narrow D-gate 50%      25.88% / 1.022 / -32.8%  1.148 0.853  70.9% | +0.046/-0.024 | 0.983 1.105 0.875 -> +0.044/-0.023 | +0.012/-0.005 | 1.258 +0.010 |  49.1 |     - |   124
  c.iii narrow blocks fast    25.59% / 0.993 / -33.8%  1.092 0.860  72.1% | -0.011/-0.016 | 0.999 1.103 0.876 -> -0.011/-0.016 | -0.003/-0.009 | 1.228 -0.020 |  48.6 |     - |    44
  c.iv narrow de-lever 25%    25.13% / 1.008 / -31.1%  1.102 0.880  70.1% | -0.000/+0.004 | 0.972 1.106 0.875 -> -0.004/+0.005 | +0.007/-0.002 | 1.263 +0.016 |  50.7 |     - |   425
  c.iv narrow de-lever 50%    24.04% / 0.997 / -29.8%  1.089 0.872  68.1% | -0.014/-0.004 | 0.944 1.110 0.876 -> -0.021/-0.004 | +0.012/-0.005 | 1.266 +0.018 |  50.5 |     - |   425
  d  QQEW gaps replace        24.52% / 0.934 / -34.6%  1.034 0.796  75.9% | -0.068/-0.080 | 1.054 1.097 0.878 -> -0.063/-0.082 |    (none)     | 1.190 -0.058 |  45.4 |     - |   555
  d  QQEW gaps sum            25.66% / 1.004 / -33.6%  1.112 0.858  69.5% | +0.009/-0.018 | 0.964 1.107 0.875 -> +0.005/-0.017 |    (none)     | 1.266 +0.018 |  48.1 |     - |   363
  d  QQEW gaps max            25.83% / 1.004 / -33.6%  1.105 0.869  71.0% | +0.002/-0.007 | 0.985 1.105 0.875 -> +0.000/-0.006 |    (none)     | 1.258 +0.010 |  48.7 |     - |   146
  e  ratio D/E/F gates A 25%  23.58% / 0.987 / -32.0%  1.092 0.848  65.0% | -0.011/-0.028 | 0.901 1.111 0.876 -> -0.019/-0.028 | -0.043/-0.031 | 1.270 +0.022 |  49.4 |     - |  1542
  e  ratio D/E/F gates A 50%  20.98% / 0.946 / -30.6%  1.058 0.804  57.8% | -0.045/-0.072 | 0.801 1.122 0.876 -> -0.065/-0.072 | -0.106/-0.080 | 1.265 +0.017 |  48.8 |     - |  1542
  e  ratio D/E/F = extra vote 22.87% / 0.984 / -31.5%  1.094 0.840  61.8% | -0.009/-0.036 | 0.856 1.114 0.877 -> -0.021/-0.037 | -0.062/-0.044 | 1.292 +0.044 |  48.0 |     - |  1542
  c.ii narrow AND pct<0.2     28.11% / 1.080 / -35.6%  1.187 0.936  71.5% | +0.084/+0.060 | 0.992 1.104 0.875 -> +0.083/+0.061 | +0.006/+0.000 | 1.306 +0.058 |  48.8 |   YES |    33
  c.ii narrow OR pct<0.2      29.01% / 1.158 / -34.5%  1.325 0.935  68.2% | +0.222/+0.059 | 0.945 1.110 0.876 -> +0.215/+0.058 | +0.242/+0.176 | 1.433 +0.185 |  49.5 |   YES |   215
  CANDIDATE COUNT this line: 18 (sign-flip placebos and the reference gate not counted); cumulative with the three earlier lines: 258
  both-era passes vs the k-live control: 2 -> the two combinations with the pre-registered gate; stand-alone QQEW-DMA variants: 0 of 16
    c.ii narrow AND pct<0.2: LORO vs same-rows live: GFC +0.098; COVID +0.069; 2022 +0.071; SPMO era +0.060;  flip both-era: False
    c.ii narrow OR  pct<0.2: LORO vs same-rows live: GFC +0.163; COVID +0.111; 2022 +0.140; SPMO era +0.059;  flip both-era: TRUE (placebo passes)

5. BLOCK BOOTSTRAP (2000 draws) vs same-rows live; last column = vs the pre-registered pct gate (20d blocks)
  c.ii narrow AND pct<0.2   point +1.59pp/yr +0.075 Sh | 20d: logret CI [-0.60,+3.84] P<=0 .079  Sharpe CI [-0.011,+0.164] P<=0 .048 | 60d: logret [-0.53,+3.67] .062  Sharpe [-0.007,+0.156] .037 | vs pct-gate -0.137 Sh, CI [-0.264,-0.029] P<=0 .995
  c.ii narrow OR pct<0.2    point +2.29pp/yr +0.153 Sh | 20d: logret CI [-2.03,+7.06] P<=0 .148  Sharpe CI [-0.018,+0.343] P<=0 .038 | 60d: logret [-2.48,+7.31] .181  Sharpe [-0.041,+0.359] .061 | vs pct-gate -0.060 Sh, CI [-0.166,+0.033] P<=0 .876
  c.ii narrow D-gate 100%   point -0.50pp/yr +0.012 Sh | 20d: logret CI [-3.94,+2.82] P<=0 .603  Sharpe CI [-0.123,+0.146] P<=0 .443 | 60d: logret [-4.84,+3.36] .613  Sharpe [-0.152,+0.161] .462 | vs pct-gate -0.200 Sh, CI [-0.358,-0.049] P<=0 .997
  a  conf worse-of          point -0.99pp/yr +0.001 Sh | 20d: logret CI [-4.44,+2.65] P<=0 .718  Sharpe CI [-0.132,+0.143] P<=0 .508 | 60d: logret [-5.15,+2.91] .670  Sharpe [-0.154,+0.152] .492 | vs pct-gate -0.211 Sh, CI [-0.371,-0.058] P<=0 .998
  ref_pct (pre-registered)  point +4.36pp/yr +0.212 Sh | 20d: logret CI [+0.95,+8.43] P<=0 .004  Sharpe CI [+0.067,+0.372] P<=0 .000 | 60d: logret [+1.09,+8.00] .003  Sharpe [+0.072,+0.361] .002
```

Reading, family by family.
- **(a) Confirmation.** Worse-of gains +0.07 in the search era and loses −0.09 in the holdout; the D/E/F-side variant +0.10 / −0.08.
  Exposure is 2.5 pp below live and the k-control changes nothing. Both lose on the real rows (1.173 / 1.206 vs 1.248), and the
  bootstrap Sharpe interval vs live is centred on zero (+0.001, [−0.13, +0.14]). The mechanism is section 3: QQEW's downgrades come at the
  same time or a few days early, so confirmation rarely leaves earlier than the live design, but QQEW's upgrades come later, so
  worse-of keeps the row de-levered through the first days of every recovery — the holdout (2009–2012, many D→A recoveries) is where it pays.
- **(b) QQEW-only classifier.** Not a duplicate of `breadth_signal`'s replacement variants (those replaced the price-vs-50d / 200d booleans
  with breadth *percentiles* and kept QQQ's 50>200 cross; they failed the search era, e.g. qqew_s200 repl −0.183 / +0.195). Driving the row
  with QQEW's own effective state fails the holdout (−0.135 with QQEW's gaps, −0.053 with QQQ's) and the real rows (1.109 / 1.165), with a
  worse drawdown (−41.6 % / −37.4 %). Different failure era, same conclusion as the earlier line: equal-weight cannot replace the index's
  state machine on an index-instrument design.
- **(c) Divergence as a signal.** (i) as an extra trim vote: −0.047 / +0.013, flip identical to four decimals (the vote rarely changes the
  A row); (ii) as the D-row gate: +0.066 / −0.069 at 100 %, +0.044 / −0.023 at 50 %, point −0.50 pp/yr vs live, bootstrap [−0.12, +0.15];
  it is on for exactly 124 D days, the same count as the pct gate, but only 33 of them coincide, and head-to-head it is −0.200 Sharpe
  behind the pct gate with a 20d interval that excludes zero ([−0.358, −0.049]); (iii) blocking the fast re-entry fires 44 days and is a
  no-op-level loss (−0.011 / −0.016); (iv) de-levering A/D by 25 / 50 % is ±0.00 / −0.02 — noise, with the flips equally flat.
- **(d) QQEW's own extension gaps.** Replacing QQQ's gaps with QQEW's (which are extended less often: mean A-row scale 0.877 vs 0.821) loses
  in both eras (−0.063 / −0.082 vs the k-control, real 1.190); adding them as extra votes (sum / max) is a no-op (+0.005 / −0.017,
  +0.000 / −0.006). The index's own extension is the right trim input.
- **(e) The ratio's 50/200 state as a gate on A.** The ratio is below its 50d/200d (D/E/F) on 1,542 of 3,092 effective-A days — half of the
  bull market is "narrow leadership" by this definition — and de-levering A on those days is a loss at matched capital (−0.019 / −0.028 at
  25 %, −0.065 / −0.072 at 50 %, −0.021 / −0.037 as a vote). This agrees with `breadth_signal`'s A-only scope of the qqew_s50 / qqew_s200
  percentile gates (S 1.014–1.050, H 0.870–0.901 vs the 1.111 / 0.876–0.923 controls) and with `dgate_anatomy` §4: bottom-quintile breadth in
  A is what a mega-cap-led bull looks like, not a sell signal. Real rows are slightly above live (1.265–1.292) because the SPMO era is the
  era of the trim; the flips are worse, but that is the exposure ladder, not a signal.
- **The two combinations.** AND (33 days) and OR (215 days) pass both eras vs the control — because they contain the pre-registered gate.
  Both are worse than the pct gate by itself: AND gives up +0.137 Sharpe (CI excludes zero), OR gives up +0.060 and its sign-flip (which
  still contains the pct gate) also passes both eras. Adding the divergence flag to the pct gate can only subtract.

Rebalances/yr: 45–53 for every candidate vs 48.4 live on these rows (the QQEW-only classifier 50–53, the gaps-replace 45); nothing here
is a turnover story.

## 6. Verdict material: is the divergence gate the pct<0.20 gate under another name?

```
4. OVERLAP on effective-D days (727): the pre-registered flag (pct<0.20) vs the divergence flag (QQEW eff rank > QQQ eff rank)
    pct<0.2=True  narrow=True  n   33  QLD d1   -90.1bp  QQQ d1   -44.5bp  E/F within 5: 48.5%
    pct<0.2=True  narrow=False n   91  QLD d1   -63.4bp  QQQ d1   -31.3bp  E/F within 5: 20.9%
    pct<0.2=False narrow=True  n   91  QLD d1   +48.0bp  QQQ d1   +24.4bp  E/F within 5: 16.5%
    pct<0.2=False narrow=False n  512  QLD d1   +35.2bp  QQQ d1   +17.9bp  E/F within 5:  3.9%
  Jaccard(pct flag, narrow flag) on D days = 0.153;  QQEW eff state on narrow D days: E 108, F 16;  on all D days: A 66, C 8, D 529, E 108, F 16
```

No. The two flags fire on the same number of D days (124 each) but overlap on 33 (Jaccard 0.15). Where they overlap the next day is the
worst (QLD −90 bp, 49 % of those days are within five sessions of an E/F read); where only the pct flag fires it is still bad (−63 bp);
where only the divergence flag fires the next day is *good* (+48 bp, better than the 512 unflagged D days). The state comparison says
"QQEW is already below its 200d while QQQ is still above it" — a level condition that 108 + 16 D days satisfy; the percentile says "over
the last 60 sessions equal-weight has fallen behind cap-weight faster than in 80 % of the trailing year" — a drift condition. Only the
drift condition marks the D days that precede the break. The divergence flag does carry the transition information the dgate_anatomy
mechanism needs (E/F within five sessions: 16.5–48.5 % vs 3.9 %), but the days it adds are the ones where the index recovers, which is
why the OR combination gives up Sharpe relative to the pct gate alone.

## 7. Plain-language reading and verdict

What the DMA lines on QQEW say, in words: the average Nasdaq-100 stock is in the same trend state as the index on five days out of six.
When they differ the average stock is usually the weaker one (it spends less time in A and more in F than the index in both eras). When
the index changes state, the average stock has typically already changed or changes the same day; on the way down it is a couple of
sessions early about a third of the time (most clearly at the break of the 200d), on the way up it is a few sessions late about a third of
the time (most clearly at the return to A). That is the whole descriptive content: a coincident indicator with a short lead on breakdowns
and a short lag on recoveries. Every overlay built from it inherits both halves — a confirmation rule leaves at about the same time as
the live design and re-enters later, so it pays in a search era with few false recoveries and loses in a holdout full of them; a
divergence gate on the D row selects days that are half breakdowns and half recoveries and nets to nothing.

Verdict: **clean negative on the overlays, with a clear descriptive picture.** 0 of 16 stand-alone QQEW-DMA variants beat the live design
in both eras at matched capital; the two both-era passes are the pre-registered gate with a QQEW-state flag bolted on, and both are worse
than the gate alone. The QQEW DMA lines add nothing beyond what the pct<0.20 D-gate already captures, and the divergence gate is not that
rule under another name — it is a different rule that does not work. Nothing here changes the standing recommendation (no change; the
pct<0.20 D-gate stays a pre-registered candidate under its frozen tracking spec). Classification per the briefing: "no signal" for the
event-day divergences and the confirmation / replacement / gaps / ratio variants; "signal, but it is the pre-registered rule's" for the
combinations. Candidate count 18 this line (258 cumulative); no threshold was fitted anywhere (the classifier constants are the live ones,
the percentile is trailing-252, the rows are the same 4,800 as the earlier notes).

Today (provisional after 2026-09-04, from the extension file and the three Robinhood QQQ closes): QQEW macro state flipped A→D on
2026-09-10 (fast D since 09-01; gaps +1.7 / +6.9 / +7.7 %), the ratio has been D since 09-08, QQQ is macro A (−0.3 % vs its 50d, inside the
1 % band; fast D since 09-01; gap200 +7.5 %) — div = +3 as of the 09-10 close, a "QQEW down, QQQ holds" day, the event type that section 4
finds uninformative (20d forward +1.6 % QQQ, P 0.65). The pre-registered gate is off (pct 0.82; effective state A). The harness's last row
(2026-08-26) is A/A, div 0.

```
  date         QQEW macro  fast  eff  gap100  gap150  gap200 |  ratio macro  eff |  QQQ macro  fast  eff   gap50  gap200  div
  2026-09-04            A     D    A   +5.2%  +10.5%  +11.2% |            A    A |          A     D    A   +1.1%   +9.3%  +0
  2026-09-08            A     D    A   +3.6%   +8.8%   +9.6% |            D    D |          A     D    A   +1.0%   +9.1%  +0
  2026-09-09            A     D    A   +2.9%   +8.2%   +8.9% |            D    D |          A     D    A   +0.7%   +8.7%  +0
  2026-09-10            D     D    D   +1.7%   +6.9%   +7.7% |            D    D |          A     D    A   -0.3%   +7.5%  +3
```
