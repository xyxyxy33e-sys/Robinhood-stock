# Research line `rates_signal` (2026-09-10): does the rates complex add anything to the regime signal?

**Verdict: clean negative, with one nuance.** 108 candidates (9 rate/oil signals x 2 signs x 6
rule variants), every one evaluated through the project's harness with an exposure-matched live
control. The direction the outside manager argued (rates rising fast = risk-off) is the *right*
sign — 11 of 54 rising-rate candidates beat live on both eras and at matched exposure, versus 1 of
54 for the mirror sign, and the mirror sign loses uniformly (mean −0.044 Sharpe) — but the effect
is too small to use: the nominal-yield rules are worth **+0.004 to +0.019 Sharpe** at matched
exposure, with circular-block-bootstrap **P(≤0) = 0.22 to 0.45 and every 95% CI straddling zero**.
The only series with a larger point estimate, the 10-year TIPS real yield (+0.046 at matched
exposure, both eras, real rows +0.051, all leave-one-regime-out positive), **loses its entire edge
with a one-day publication lag** (+0.046 → −0.002, holdout −0.027), only exists from 2004, and its
bootstrap P(≤0) is 0.21. A 60-session-change signal whose value vanishes when read a day late is
a quintile-boundary-timing artifact, not a regime input. Nothing here is a candidate. Research only.

Script: `paper-track/rates_signal.py` (run from the repo root; `python3 paper-track/rates_signal.py
<series...>` sweeps + deep-controls those series and saves JSON to the scratchpad, ~2 min/series;
`... summary` aggregates; no argument = all nine, ~25 min). Logs: `research_notes/rates_signal_run1.log`
(dgs2_20, dgs2_60, dgs10_20), `_run2.log` (dgs10_60, slope_lvl, slope_60), `_run3.log` (dfii10_20,
dfii10_60, oil_60), `rates_signal_summary.log`. New data: six FRED files under `data/` (below).

## Data and provenance

All raw FRED downloads via the briefing's curl pattern (`https://fred.stlouisfed.org/graph/fredgraph.csv?id=<ID>`),
fetched 2026-09-10, saved untouched, holidays forward-filled in code (never dropped). Also appended
to `data/README.md`.

| file | FRED id | series | span | rows | blanks |
|---|---|---|---|---|---|
| `data/dgs2.csv` | DGS2 | 2y Treasury CMT yield (hike-odds proxy) | 1976-06-01 .. 2026-09-08 | 13,116 | 552 |
| `data/dgs10.csv` | DGS10 | 10y Treasury CMT yield | 1962-01-02 .. 2026-09-08 | 16,876 | 720 |
| `data/t10y2y.csv` | T10Y2Y | 10y − 2y spread, pp | 1976-06-01 .. 2026-09-09 | 13,117 | 552 |
| `data/dfii10.csv` | DFII10 | 10y TIPS real yield | **2003-01-02** .. 2026-09-08 | 6,179 | 254 |
| `data/dcoilwtico.csv` | DCOILWTICO | WTI spot, $/bbl | 1986-01-02 .. 2026-09-09 | 10,615 | 374 |
| `data/dgs3mo.csv` | DGS3MO | 3m T-bill | 1981-09-01 .. 2026-09-08 | 11,746 | 492 |

Notes. (1) DGS3MO was fetched as asked but not used as a signal: the 2y already carries the hike
expectation and a 20/60d change in the bill rate is dominated by realised FOMC moves, not
expectations; `data/dgs3mo_full.csv` is untouched. (2) WTI printed **−37.63 on 2020-04-20**; the
60d log change floors the price at $1 for that one observation. (3) **Timing**: FRED dates a value
by its observation day (H.15 yields are the ~3:30pm New York reads); it is published the next
business morning. The main tables assume the value is known at that day's close (a live
implementation would read the same yields from a market feed at 4pm); every deep-control block
also shows the result with a **one-day lag**, and the lag turns out to matter (below).

## Method

Bootstrapped the 26-year QQQ-core proxy + real SPMO weekly rows with the standard prefix
(`leverage_under_trim.py` split at `base=evaluate`). Standing figures reproduced first, exact:
**26y proxy 22.18% / 0.913 / −33.6%, search 1.103, holdout 0.768, exposure 0.677; real weekly
31.40% / 1.248 / −25.0%** (6,575 proxy rows 2000-07-03..2026-08-26, 564 real rows). Live weight
function: `W[eff]` → `extension_scale` → `vt(w, r['vol'])`, plain 30d vol, band 0.05.

Alignment sanity (contemporaneous d0→d1 QQQ return vs same-window change): DGS2 +0.230,
DGS10 +0.236, WTI +0.048 — the post-2000 positive stock/yield correlation, as expected. Predictive
pairing (signal percentile at d0 vs QQQ d0→d1): −0.02, −0.02, −0.00, i.e. no look-ahead.

Signals (nine), each computed on the FRED series' own business-day calendar and mapped to a QQQ
session as the last value dated ≤ d0: 20/60-observation change in DGS2, DGS10, DFII10; level and
60-obs change of T10Y2Y; 60-obs log change in WTI. Each becomes a **trailing-252-observation
percentile** (causal; never a full-sample constant). Top quintile = pct ≥ 0.8, bottom = pct ≤ 0.2.
Coverage: 2000-07-03 (full proxy) for everything except DFII10 (from 2004-01-16 / 2004-03-12;
**same-rows** — the live baseline is re-run on exactly those rows, so its figures differ there).

Variants, each in both signs (HI = top quintile is risk-off, "rates rising fast"; LO = bottom
quintile is risk-off, "rates falling fast" as in 2001/2008/2020 — the LO family is the sign-flip
placebo of the HI family and vice versa):

| kind | rule |
|---|---|
| delever25 / delever50 | risky legs × 0.75 / × 0.50 while in the quintile (after the trim, before the vol target) |
| vote | one extra extension-trim vote while in the quintile (effective state A only, like the live trim; votes capped at 3) |
| block | the 20/100 fast re-entry overlay is not applied while in the quintile (eff falls back to the macro state) |
| tilt25 / tilt50 | risky legs × clip(1 − k·2·(pct−0.5), 1−k, 1) [HI] or the mirror [LO]; vol-target T re-calibrated by bisection so average deployed exposure matches live on the same rows |

**Exposure control on every candidate**: `scaled(live_fn, k)` with k bisected until average
deployed capital equals the candidate's; "xm" below is the candidate's full-window Sharpe minus
that control's. Harness caveat found on the way: `downturn_review.exposure_control()` uses
`downturn_review.live()` = `vt(W[r['state']], vol)` as its baseline — the **macro-only design
with neither the fast overlay nor the extension trim**. On the 2000-2026 rows it reads 0.751 at
k = 0.845 where the true live design reads 0.918, so it flattered every candidate *including the
placebos* by ~+0.15 Sharpe in a first pass. The script carries its own control over `live_fn`.
Worth fixing in `downturn_review.py` after the freeze; not touched here.

Tilt caveat: with the cap at 1.0 the vol target can only *reduce* exposure, so for tilt50 (and
tilt25 on DFII10) the bisection on T hits its ceiling (T* = 4.0, vol target effectively off) without
reaching live's exposure; the exposure control then matches by k instead. Those rows therefore
test "tilt without a vol target" and their large drawdowns (−46%) are partly the missing vol
target. The delever/vote/block families are the clean tests.

## Mechanism check (before any strategy test)

Forward 20-session QQQ log return (annualised, %) | forward 20d realised vol (%), by trailing quintile.

| signal | era | bottom ≤0.2 | middle | top ≥0.8 | n_top |
|---|---|---|---|---|---|
| dgs2_20 | HOLDOUT | +16.4 \| 25.5 | −2.5 \| 22.8 | −2.6 \| 19.9 | 750 |
| | SEARCH | +25.9 \| 21.2 | +15.8 \| 18.3 | +13.7 \| 19.4 | 701 |
| | ALL | +20.3 \| 23.8 | +4.6 \| 21.1 | +5.3 \| 19.6 | 1451 |
| dgs2_60 | HOLDOUT | +1.5 \| 27.4 | +4.7 \| 22.1 | −9.5 \| 19.9 | 793 |
| | SEARCH | +38.3 \| 20.1 | +10.0 \| 18.2 | +14.4 \| 20.1 | 802 |
| | ALL | +16.5 \| 24.4 | +6.7 \| 20.7 | +2.5 \| 20.0 | 1595 |
| dgs10_20 | ALL | +19.8 \| 23.4 | +4.8 \| 20.8 | +4.7 \| 20.6 | 1403 |
| dgs10_60 | HOLDOUT | +13.8 \| 25.3 | −6.4 \| 23.1 | +6.7 \| 19.3 | 861 |
| | SEARCH | +36.3 \| 19.6 | +10.1 \| 18.3 | +15.7 \| 20.7 | 685 |
| | ALL | +22.8 \| 23.0 | +0.2 \| 21.2 | +10.7 \| 19.9 | 1546 |
| slope_lvl | ALL | +12.4 \| 18.0 | −1.4 \| 21.2 | +11.9 \| 24.8 | 2166 |
| slope_60 | ALL | +4.4 \| 21.3 | +9.9 \| 20.9 | +6.3 \| 22.0 | 1842 |
| dfii10_20 | HOLDOUT | +25.8 \| 18.8 | +8.3 \| 17.4 | −2.7 \| 18.1 | 606 |
| | SEARCH | +21.3 \| 18.9 | +15.8 \| 18.3 | +17.2 \| 21.5 | 619 |
| | ALL | +23.6 \| 18.9 | +11.7 \| 17.8 | +7.4 \| 19.8 | 1225 |
| dfii10_60 | HOLDOUT | +21.3 \| 18.5 | +14.1 \| 17.2 | −9.1 \| 18.6 | 702 |
| | SEARCH | +28.3 \| 19.0 | +15.4 \| 17.8 | +11.5 \| 22.3 | 657 |
| | ALL | +24.8 \| 18.7 | +14.7 \| 17.5 | +0.9 \| 20.4 | 1359 |
| oil_60 | HOLDOUT | −0.2 \| 26.4 | −0.4 \| 22.4 | +7.1 \| 19.6 | 766 |
| | SEARCH | +10.1 \| 24.0 | +18.0 \| 18.0 | +22.3 \| 17.6 | 541 |
| | ALL | +3.7 \| 25.5 | +7.4 \| 20.5 | +13.4 \| 18.8 | 1307 |

Reading. The one robust pattern is that **rates falling fast (bottom quintile) precede strong
forward returns with high vol** (+16 to +25%/yr): those are the post-crash rebounds of 2001-02,
2008-09, 2020, which the live 20/100 fast re-entry already captures — so "rates falling = risk-off"
(the LO family) is wrong and loses everywhere. For **rates rising fast (top quintile) there is no
consistent forward-return penalty in nominal yields**: top vs middle is +5.3 vs +4.6 (dgs2_20),
+2.5 vs +6.7 (dgs2_60), +10.7 vs +0.2 (dgs10_60 — the opposite direction), and forward vol is
*lower* in the top quintile (19-20% vs 21-23%), so a de-lever there is cutting exposure in
below-average-vol conditions, which is why it cannot beat an exposure-matched control by much.
Oil at a high precedes *better* returns in every era. The only series with a genuine top-quintile
penalty is the real yield: dfii10_60 top +0.9 vs middle +14.7 (holdout −9.1 vs +14.1), which is
the 2008, 2013-taper and 2022 real-rate shocks — a 2004+ series with three episodes.

## Sweep: 108 candidates

Sharpe deltas vs the LIVE design on the same rows (full window, search era 2015-11+, holdout
2000-07..2015-10, real weekly rows); xm = vs the exposure-matched live control; both = beats live on
search AND holdout. frac = share of rows in the quintile. T* = vol target after bisection (tilt only).

**Headline counts**
- candidates: **108** (9 series × 2 signs × 6 variants); exposure control matched on all 108
- beat live on both eras (raw Sharpe): **12** — all 12 also beat the exposure-matched live; **7** of those also beat live on real rows
- xm across all 108: mean **−0.032**, max +0.048, min −0.187
- HI sign (rates rising fast = risk-off): **11 of 54** pass both-era + exposure control; mean xm −0.021; mean Δreal −0.001
- LO sign (rates falling fast = risk-off): **1 of 54**; mean xm −0.044; mean Δreal −0.036
- by kind (mean xm / Δsearch / Δholdout / Δreal): delever25 −0.006/−0.003/+0.000/−0.005; delever50 −0.025/−0.022/−0.012/−0.030; vote −0.013/−0.017/−0.001/−0.002; block −0.019/−0.013/−0.023/−0.021; tilt25 −0.047/−0.029/−0.060/−0.019; tilt50 −0.083/−0.038/−0.101/−0.036

**Every candidate that beats live on both eras**

| candidate | exposure | ΔS full | ΔS search | ΔS holdout | ΔS real | xm |
|---|---|---|---|---|---|---|
| dfii10_60 HI delever50 | 0.656 | +0.054 | +0.093 | +0.024 | +0.051 | **+0.046** |
| dfii10_60 HI tilt50 | 0.681 | +0.048 | +0.073 | +0.022 | +0.042 | +0.042 |
| dfii10_60 HI delever25 | 0.700 | +0.034 | +0.055 | +0.016 | +0.035 | +0.029 |
| dfii10_60 HI vote | 0.699 | +0.034 | +0.064 | +0.004 | +0.053 | +0.028 |
| dfii10_20 HI delever25 | 0.705 | +0.032 | +0.066 | +0.004 | +0.069 | +0.027 |
| dgs10_60 HI vote | 0.633 | +0.025 | +0.049 | +0.006 | +0.025 | +0.019 |
| dfii10_60 HI tilt25 | 0.738 | +0.013 | +0.021 | +0.001 | +0.015 | +0.012 |
| oil_60 LO delever25 | 0.641 | +0.014 | +0.026 | +0.003 | −0.001 | +0.009 |
| dgs10_60 HI delever25 | 0.638 | +0.014 | +0.023 | +0.010 | −0.009 | +0.009 |
| dgs2_60 HI block | 0.675 | +0.009 | +0.006 | +0.010 | −0.002 | +0.008 |
| dgs10_60 HI block | 0.676 | +0.007 | +0.016 | +0.000 | −0.005 | +0.006 |
| dgs10_60 HI delever50 | 0.599 | +0.014 | +0.025 | +0.010 | −0.043 | +0.005 |

Seven of the twelve are the two real-yield series (2004+ window, 5,649-5,687 rows, where the
live baseline itself reads 0.932 / 0.959). Of the full-window series, the best both-era result is
dgs10_60 HI vote at +0.019, and the two-year yield — the actual hike-odds proxy — tops out at
+0.008 (dgs2_60 HI block). The worst five are all tilt50 / LO / slope: slope_lvl HI tilt50 −0.187,
dgs10_60 LO tilt50 −0.139, dfii10_60 LO tilt50 −0.132, slope_lvl HI delever50 −0.121, slope_60 LO
tilt50 −0.119. Wins do not grow monotonically with the de-lever size for the nominal series
(delever25 ≥ delever50 on dgs2_20, dgs2_60, dgs10_60), so this is not a leverage artifact — it is
simply small.

**Per-series full tables** (all 12 variants each) are in the run logs; the pattern is the same in
every series: HI delever25/vote hover at −0.01..+0.03, HI block at −0.015..+0.008, all LO variants
negative, all tilts negative except on DFII10.

## Deep controls: best variant per series

Best = highest xm within the series. Bootstrap = circular block bootstrap, 2,000 draws, candidate vs
the exposure-matched live series, Sharpe-difference 95% CI and P(Δ ≤ 0). flip = xm of the mirror-sign
variant of the same kind (sign-flip placebo). lag = the same rule reading the signal one day late.
LORO = range of the Sharpe delta over the five leave-one-regime-out windows.

| series | best | xm | Δsearch | Δholdout | Δreal | both | block-20 CI, P | block-60 CI, P | flip xm | lag xm (S/H/R) | LORO min..max |
|---|---|---|---|---|---|---|---|---|---|---|---|
| dgs2_20 | HI delever25 | +0.004 | +0.023 | −0.001 | +0.026 | n | [−0.037,+0.047] 0.448 | [−0.034,+0.042] 0.437 | −0.010 | +0.009 (+0.025/+0.007/+0.057) | −0.004..+0.007 |
| dgs2_60 | HI block | +0.008 | +0.006 | +0.010 | −0.002 | Y | [−0.012,+0.029] 0.238 | [−0.011,+0.027] 0.218 | −0.044 | +0.011 (+0.006/+0.015/−0.002) | −0.002..+0.013 |
| dgs10_20 | HI delever25 | +0.005 | +0.031 | −0.006 | +0.011 | n | [−0.035,+0.046] 0.411 | [−0.036,+0.047] 0.416 | −0.000 | +0.010 (+0.039/−0.003/+0.013) | −0.009..+0.010 |
| dgs10_60 | HI vote | +0.019 | +0.049 | +0.006 | +0.025 | Y | [−0.035,+0.076] 0.258 | [−0.032,+0.070] 0.235 | −0.046 | +0.003 (+0.017/+0.003/+0.007) | +0.002..+0.025 |
| slope_lvl | LO delever25 | −0.000 | +0.056 | −0.033 | +0.049 | n | [−0.052,+0.050] 0.495 | [−0.048,+0.053] 0.491 | −0.050 | −0.007 (+0.051/−0.041/+0.022) | −0.039..+0.009 |
| slope_60 | HI block | +0.002 | −0.005 | +0.008 | −0.003 | n | [−0.025,+0.028] 0.453 | [−0.024,+0.026] 0.446 | −0.008 | −0.005 (+0.008/−0.013/−0.009) | −0.004..+0.008 |
| dfii10_20 | HI delever50 | +0.048 | +0.123 | −0.001 | +0.122 | n | [−0.045,+0.148] 0.167 | [−0.053,+0.153] 0.159 | −0.032 | +0.020 (+0.072/−0.006/+0.165) | −0.005..+0.063 |
| dfii10_60 | HI delever50 | +0.046 | +0.093 | +0.024 | +0.051 | Y | [−0.062,+0.153] 0.212 | [−0.063,+0.149] 0.220 | −0.111 | **−0.002** (+0.047/**−0.027**/+0.060) | +0.018..+0.055 |
| oil_60 | LO delever50 | +0.010 | +0.041 | −0.004 | −0.016 | n | [−0.083,+0.105] 0.427 | [−0.072,+0.096] 0.414 | −0.010 | −0.020 (−0.018/−0.011/−0.025) | −0.011..+0.018 |

Log-return terms, for scale: the best nominal-yield rule (dgs10_60 HI vote) is +0.9 pp/yr with a
20d-block CI of [−0.49, +2.20] pp/yr, P(≤0) = 0.115; dfii10_60 HI delever50 is +1.6 pp/yr, CI
[−0.79, +4.01], P(≤0) = 0.10.

What the controls say, series by series:
- **Sign-flip placebo loses in all nine series** — the direction (rising rates = risk-off) is not
  random. This is the one positive statement the line supports, and it is a statement about
  sign, not size.
- **Bootstrap**: no series clears it. Best P(Δ Sharpe ≤ 0) is 0.16 (dfii10_20, which fails the
  holdout at −0.001); the two-year yield rules are at 0.44 / 0.22, i.e. indistinguishable from the
  matched control.
- **Both-era**: passes for dgs2_60 (+0.006 / +0.010 — a rounding-level margin), dgs10_60
  (+0.049 / +0.006), dfii10_60 (+0.093 / +0.024). The two nominal ones have holdout margins under
  0.01.
- **Leave-one-regime-out**: dgs10_60 HI vote and dfii10_60 HI delever50 stay positive in every
  window (+0.002..+0.025 and +0.018..+0.055), so neither is a single-episode result; dgs10_60
  drops to +0.002 without the SPMO era, i.e. its holdout contribution is nil.
- **One-day publication lag** (the honest reading for FRED-sourced data): the nominal rules are
  unchanged (+0.004→+0.009, +0.008→+0.011, +0.019→+0.003), which is expected for a 20-60-day
  signal. **dfii10_60 collapses from +0.046 to −0.002 and its holdout from +0.024 to −0.027**;
  dfii10_20 halves to +0.020 with holdout −0.006. A 60-session-change signal that cannot survive
  being read 24 hours late is getting its edge from exact quintile-crossing days, not from the
  regime it nominally measures. That, plus the 2004 start (dot-com untestable) and P(≤0) ≈ 0.21,
  is why the real-yield result is reported as noise rather than as "signal, but small".

## Where the signals stand at the manager's downgrade (trailing-252 percentile at the latest FRED date)

| signal | date | value | pct | in top quintile? |
|---|---|---|---|---|
| dgs2_20 | 2026-09-08 | +17 bp | 0.84 | yes |
| dgs2_60 | 2026-09-08 | +34 bp | 0.77 | no (just under) |
| dgs10_20 | 2026-09-08 | +10 bp | 0.69 | no |
| dgs10_60 | 2026-09-08 | +37 bp | 0.95 | yes |
| slope_lvl | 2026-09-09 | +0.40 pp | 0.15 | (bottom) |
| slope_60 | 2026-09-09 | +11 bp | 0.86 | yes |
| dfii10_20 | 2026-09-08 | 0 bp | 0.36 | no |
| dfii10_60 | 2026-09-08 | +29 bp | 0.83 | yes |
| oil_60 | 2026-09-09 | +18.7% (80.65 → 97.26) | 0.75 | no (just under) |

So the proxies agree with the manager's description of the tape — the 2y is up 17 bp in 20
sessions, the 10y up 37 bp in 60 (95th trailing percentile), real yields up 29 bp, oil +19% — and
today would sit in the risk-off quintile for four of the nine signals. The historical record says
acting on that with the best available rule would have been worth +0.004 to +0.019 Sharpe over 26
years at the same deployed capital, inside sampling noise. The live design's own answer to the
same tape is already in place: the vol target, the extension trim (votes on 100/150/200d gaps) and
the 50/200 classifier respond to what rising rates do to prices, and the mechanism table shows that
fast-rising nominal yields have historically been *low*-vol, mildly positive-return conditions for
QQQ — not the setup a de-lever pays for.

## Verdict

**No usable rates signal.** Across 108 candidates spanning hike-expectation, long-yield, curve,
real-yield and oil proxies, both signs, and four rule families, the rates complex adds at most
+0.02 Sharpe (nominal yields) at matched exposure, with block-bootstrap P(≤0) of 0.22-0.45 and
every interval through zero; the mirror sign is reliably worse, so the manager's *direction* is
right but the *size* is negligible for this design, and the one series with a larger point
estimate (10y TIPS real yield, +0.046, 2004+) is destroyed by a one-day lag and fails the
bootstrap. Classification per the briefing: nominal yields and oil = "no signal"; real yield =
"signal, but not large enough and not robust" (fails lag, P 0.21, 22-year window); curve level and
change = negative in both signs (a steepening/flattening rule is a risk-preference dial that costs
0.02-0.19 Sharpe). What would have to be true for a rates input to work here: fast-rising yields
would need to precede *higher* QQQ vol or *lower* forward returns than the middle quintile; over
2000-2026 they precede neither (forward vol 19.6-20.6% vs 20.7-21.2%, forward return +5.3 vs +4.6
and +10.7 vs +0.2). Two harness notes for the orchestrator: `downturn_review.exposure_control()`
compares against the pre-overlay macro-only design and overstates every candidate by ~0.15 Sharpe;
and the tilt family cannot be exposure-matched by raising T because the vol-target cap never
levers up (T* saturates at 4.0), so tilt results are confounded with removing the vol target.
