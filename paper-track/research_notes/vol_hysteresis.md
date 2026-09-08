# vol_hysteresis — volatility-scaled hysteresis buffer for the six-state classifier

Research line 5 of the 2026-09-08 volatility batch. Research only; CHANGE
FREEZE until 2026-12-07. Nothing here is applied. Script:
`paper-track/vol_hysteresis.py` (run from the repo root, ~60 s).

**Verdict: no signal.** 0 of 21 vol-scaled variants beat live on both eras.
The mechanism does what it claims (it removes whipsaws in turbulent tapes)
and it still loses, because it adds more whipsaws in calm tapes than it
removes in turbulent ones, and the sign-flipped placebo does better than
the hypothesis.

## Hypothesis

`state.compute_states()` applies a fixed 1% hysteresis to price-vs-SMA for
the 50 and the 200 (separate sticky flags, no buffer on the 50-vs-200
cross). A fixed 1% is one daily sigma at 16% vol and a third of one at 50%
vol. Test: `buf_t = clamp(k * vol_t * sqrt(h/252), buf_min, buf_max)` with
k calibrated so the SEARCH-era (2015-11+) mean buffer is exactly 1.000%,
i.e. change the shape of the buffer through time, not its mean. Applied to
the macro 50/200 classifier, the fast 20/100 re-entry classifier, or both;
everything downstream (effective state, graded trim, VT20 on max(10,30),
3% band, 4 bp costs) is the unchanged live design run through the harness.

## Method

- Harness bootstrap from `leverage_under_trim.py`; `rows` (6575 daily proxy
  rows 2000-07..2026-08) and `rr` (564 real weekly rows). New state series
  are computed on the daily QQQ series (`ds` for rows, `qd` for rr) and
  attached by date; `r['state']` and `r['eff']` overwritten, `legs`, `vol`,
  `gaps` untouched. `r['eff']` rebuilt with `effective_state(state, fast)`
  exactly as `leverage_under_trim.py` does.
- Sanity checks (both assert in the script): the variant with a constant
  1% buffer reproduces `compute_states()` element-for-element for 50/200
  and 20/100; rebuilt-but-unchanged rows reproduce live exactly:
  **22.12% / 0.938 / -32.8%, S 1.150, H 0.780, real 30.67% / 1.260 / -25.3%.**
- Realized vol is causal: `vol_series()` on the daily series with the same
  formula as `state.realized_vol`, asserted equal to `r['vol_live']` /
  `r['vol']` on the harness rows. Two estimators: live max(10,30) and plain
  30d.
- Calibration by bisection on c = k*sqrt(h/252). **h and k are not
  separately identified once the mean is pinned**: h=1/5/10 give the same
  buffer path and only relabel k. Shape variation therefore comes from the
  clamp range, the estimator, and a 50% blend with the fixed 1%.

### Calibration and resulting buffer range (search-era mean = 1.000%)

| shape | c | k(h=1) | k(h=5) | k(h=10) | holdout mean | p5 | p50 | p95 | max |
|---|---|---|---|---|---|---|---|---|---|
| live-vol, clamp 0.2-4% | 0.0460 | 0.730 | 0.326 | 0.231 | 1.180% | 0.47% | 0.89% | 2.47% | 4.00% |
| live-vol, clamp 0.5-2% | 0.0472 | 0.749 | 0.335 | 0.237 | 1.104% | 0.50% | 0.91% | 2.00% | 2.00% |
| live-vol, unclamped | 0.0458 | 0.727 | 0.325 | 0.230 | 1.180% | 0.46% | 0.88% | 2.46% | 5.61% |
| live-vol, 50% blend | 0.0458 | 0.727 | 0.325 | 0.230 | 1.090% | 0.73% | 0.94% | 1.73% | 3.30% |
| vol30, clamp 0.2-4% | 0.0504 | 0.801 | 0.358 | 0.253 | 1.196% | 0.49% | 0.90% | 2.52% | 4.00% |
| vol30, clamp 0.5-2% | 0.0516 | 0.820 | 0.367 | 0.259 | 1.118% | 0.50% | 0.92% | 2.00% | 2.00% |
| vol30, unclamped | 0.0504 | 0.801 | 0.358 | 0.253 | 1.198% | 0.49% | 0.90% | 2.52% | 4.67% |

The 0.2-4% clamp never binds at the bottom and only binds at the top in
2008/2020, so "clamp 0.2-4%" and "unclamped" are near-identical. The
holdout mean is 1.09-1.20% (the dot-com/GFC tape is more volatile), so in
the holdout the variant is a slightly WIDER buffer on average as well.

## Results

### Reference: fixed buffers (context, not candidates; re-confirms T2)

| fixed buf (macro+fast) | CAGR | Sharpe | MaxDD | S | H | real | macro tr/yr | whip5 | whip10 |
|---|---|---|---|---|---|---|---|---|---|
| 0.50% | 20.67% | 0.890 | -32.9% | 1.169 | 0.683 | 30.40% / 1.256 / -26.6% | 15.6 | 132 | 188 |
| 0.75% | 21.96% | 0.935 | -33.2% | 1.199 | 0.738 | 31.18% / 1.278 / -25.3% | 13.1 | 83 | 126 |
| **1.00% (live)** | **22.12%** | **0.938** | **-32.8%** | **1.150** | **0.780** | **30.67% / 1.260 / -25.3%** | **11.7** | **51** | **91** |
| 1.25% | 22.42% | 0.947 | -31.4% | 1.163 | 0.785 | 29.45% / 1.225 / -28.6% | 10.6 | 33 | 66 |
| 1.50% | 21.28% | 0.909 | -32.2% | 1.152 | 0.727 | 28.82% / 1.198 / -30.0% | 9.9 | 24 | 50 |
| 2.00% | 19.89% | 0.860 | -35.4% | 1.116 | 0.670 | 28.26% / 1.174 / -30.0% | 8.4 | 11 | 29 |

Whipsaw count falls monotonically with the buffer (91 -> 29 at 2%) while
Sharpe peaks near 1-1.25% and falls: fewer whipsaws is not the objective,
because a wider buffer also delays every genuine break. 1.25% is BOTH on
the proxy by +0.013/+0.005 but loses 1.2pp CAGR and 3.3pp MaxDD on real
instruments (1.225 vs 1.260) — the same T2 conclusion as before.

### Candidates: vol-scaled buffer, mean 1% (21 variants)

| variant | CAGR | Sharpe | MaxDD | S | H | real CAGR/Sharpe/MDD | macro tr/yr | whip5 | whip10 |
|---|---|---|---|---|---|---|---|---|---|
| LIVE | 22.12% | 0.938 | -32.8% | 1.150 | 0.780 | 30.67% / 1.260 / -25.3% | 11.73 | 51 | 91 |
| macro: live-vol 0.2-4% | 21.46% | 0.915 | -33.7% | 1.123 | 0.760 | 30.41% / 1.250 / -25.3% | 12.11 | 55 | 97 |
| macro: live-vol 0.5-2% | 21.60% | 0.920 | -32.5% | 1.135 | 0.760 | 30.41% / 1.250 / -25.3% | 12.07 | 57 | 96 |
| macro: live-vol unclamped | 21.46% | 0.915 | -33.7% | 1.123 | 0.760 | 30.41% / 1.250 / -25.3% | 12.11 | 55 | 97 |
| macro: live-vol 50% blend | 21.84% | 0.929 | -32.4% | 1.140 | 0.771 | 30.65% / 1.259 / -25.3% | 11.92 | 57 | 94 |
| macro: vol30 0.2-4% | 21.23% | 0.907 | -32.4% | 1.125 | 0.744 | 30.81% / 1.266 / -25.3% | 12.26 | 66 | 103 |
| macro: vol30 0.5-2% | 21.63% | 0.921 | -32.4% | 1.140 | 0.758 | 30.80% / 1.265 / -25.3% | 12.11 | 62 | 99 |
| macro: vol30 unclamped | 21.23% | 0.907 | -32.4% | 1.125 | 0.744 | 30.81% / 1.266 / -25.3% | 12.26 | 66 | 103 |
| fast: live-vol 0.2-4% | 21.94% | 0.933 | -32.6% | 1.140 | 0.778 | 30.62% / 1.260 / -26.5% | 11.73 | 51 | 91 |
| fast: live-vol 0.5-2% | 22.06% | 0.936 | -32.6% | 1.141 | 0.783 | 30.62% / 1.260 / -26.5% | 11.73 | 51 | 91 |
| fast: live-vol unclamped | 21.93% | 0.932 | -32.6% | 1.140 | 0.777 | 30.62% / 1.260 / -26.5% | 11.73 | 51 | 91 |
| fast: live-vol 50% blend | 22.10% | 0.938 | -32.4% | 1.147 | 0.781 | 30.67% / 1.260 / -25.3% | 11.73 | 51 | 91 |
| fast: vol30 0.2-4% | 21.87% | 0.930 | -32.6% | 1.138 | 0.775 | 29.93% / 1.240 / -30.5% | 11.73 | 51 | 91 |
| fast: vol30 0.5-2% | 21.98% | 0.934 | -32.9% | 1.139 | 0.781 | 29.93% / 1.240 / -30.5% | 11.73 | 51 | 91 |
| fast: vol30 unclamped | 21.87% | 0.930 | -32.6% | 1.138 | 0.775 | 29.93% / 1.240 / -30.5% | 11.73 | 51 | 91 |
| both: live-vol 0.2-4% | 21.29% | 0.910 | -34.5% | 1.114 | 0.757 | 30.37% / 1.251 / -26.0% | 12.11 | 55 | 97 |
| both: live-vol 0.5-2% | 21.55% | 0.919 | -32.3% | 1.126 | 0.763 | 30.37% / 1.251 / -26.0% | 12.07 | 57 | 96 |
| both: live-vol unclamped | 21.28% | 0.909 | -34.5% | 1.114 | 0.756 | 30.37% / 1.251 / -26.0% | 12.11 | 55 | 97 |
| both: live-vol 50% blend | 21.82% | 0.928 | -32.0% | 1.137 | 0.772 | 30.65% / 1.259 / -25.3% | 11.92 | 57 | 94 |
| both: vol30 0.2-4% | 20.99% | 0.899 | -32.6% | 1.113 | 0.739 | 30.07% / 1.246 / -30.0% | 12.26 | 66 | 103 |
| both: vol30 0.5-2% | 21.50% | 0.917 | -32.5% | 1.130 | 0.759 | 30.06% / 1.246 / -30.0% | 12.11 | 62 | 99 |
| both: vol30 unclamped | 20.99% | 0.899 | -32.6% | 1.113 | 0.739 | 30.07% / 1.246 / -30.0% | 12.26 | 66 | 103 |

(For fast-only variants the macro columns are live's by construction; the
effective-state series changes: eff tr/yr 12.88 live -> 12.26-12.49, eff
whip10 101 -> 86-93. Full eff diagnostics are in the script output.)

**Candidate count: 21 tested, 0 beat live on both search and holdout
Sharpe, 0 beat live on real Sharpe while doing so.** By application:
macro 0/7 search, 0/7 holdout, mean full-Sharpe -0.022; fast 0/7 search,
3/7 holdout (by +0.001 to +0.003), mean -0.005; both 0/7 search, 0/7
holdout, mean -0.027. Search-era Sharpe is worse in all 21 even though the
buffer's mean was pinned to 1% on exactly that era. Exposure is unchanged
(0.662-0.663 vs 0.662 live), as expected for a rule that changes only
state occupancy.

Time-in-state barely moves (A 52.3 -> 51.6-52.0%, D 14.2 -> 14.6-15.0%,
others within 0.2pp). Macro transitions per year go UP, 11.73 -> 11.9-12.3,
and whipsaws go up (whip5 51 -> 55-66, whip10 91 -> 94-103) for every
macro-applied shape.

### Year-by-year (top-3 by rank, all fast-only): every year within +/-1pp
except 2009 (-2.2 to -4.2pp), 2023 (-3.1pp for the vol30 one), 2003
(+2.9pp) and 2000-2002 (+/-2pp). Nothing systematic.

### Exposure control
All three ranked variants deploy the same capital as live (0.6618-0.6622
vs 0.6621); the full live design scaled to that exposure is k=1.000 and
Sharpe 0.938, above each of them: FAIL. (The harness `exposure_control`,
which scales the older macro-only vol30 baseline, gives k=0.876 / 0.749 —
reported for completeness, not the relevant comparison.)

### Placebo 1: sign-flipped buffer (buf = c/vol, NARROWER in turbulence, mean re-pinned to 1%)

| flip variant | CAGR | Sharpe | MaxDD | S | H | real |
|---|---|---|---|---|---|---|
| FLIP macro: live-vol | 22.07% | 0.937 | -33.3% | 1.163 | 0.768 | 31.11% / 1.273 / -25.4% |
| FLIP macro: vol30 | 22.38% | 0.947 | -33.3% | 1.162 | 0.787 | 30.97% / 1.268 / -25.4% (BOTH) |
| FLIP fast: live-vol | 21.88% | 0.930 | -33.4% | 1.164 | 0.755 | 30.41% / 1.250 / -26.1% |
| FLIP fast: vol30 | 21.53% | 0.918 | -33.4% | 1.161 | 0.736 | 30.41% / 1.250 / -26.1% |
| FLIP both: live-vol | 21.93% | 0.932 | -32.9% | 1.177 | 0.749 | 30.85% / 1.264 / -26.1% |
| FLIP both: vol30 | 21.87% | 0.929 | -32.9% | 1.174 | 0.747 | 30.71% / 1.258 / -26.1% |

The flipped signal beats the hypothesis in all six pairings on search-era
Sharpe (1.161-1.177 vs 1.113-1.147) and one of the six passes BOTH plus
real (FLIP macro vol30: +0.009 full Sharpe). A real signal must lose when
flipped; this one wins. Bootstrap/LORO on that flipped survivor: block 20d
Sharpe 95% CI [-0.027, +0.046] P(<=0)=0.315; block 60d [-0.026, +0.049]
P(<=0)=0.308; LORO +0.009/-0.000/+0.010/+0.019/+0.006. Inside noise —
i.e. the flipped placebo is itself a 1-in-6 chance hit, not an inverse
signal worth pursuing.

### Placebo 2: year-block-shuffled vol series (same c, clamp 0.2-4%, live-vol, 30 seeds)

| application | real variant (full / S / H / real) | placebo median full [2.5-97.5] | P(placebo >= real) full / S / H / real |
|---|---|---|---|
| both | 0.910 / 1.114 / 0.757 / 1.251 | 0.918 [0.892, 0.958] | 0.73 / 1.00 / 0.13 / 0.60 |
| macro | 0.915 / 1.123 / 0.760 / 1.250 | 0.928 [0.902, 0.958] | 0.73 / 0.97 / 0.30 / 0.63 |
| fast | 0.933 / 1.140 / 0.778 / 1.260 | 0.929 [0.915, 0.941] | 0.33 / 0.83 / 0.07 / 0.33 |

A buffer driven by vol from the WRONG years is as good as or better than
the real one on full-history Sharpe (P = 0.73 for macro and both), and
strictly better on the search era (P = 0.97-1.00). The real vol path only
looks good relative to placebo on the holdout for the fast-only version
(P = 0.07), where its absolute edge over live is +0.001 to +0.003.

### Block bootstrap and leave-one-regime-out (top-3, all fast-only)

| variant | point dSharpe | block 20 Sharpe CI, P(<=0) | block 60 Sharpe CI, P(<=0) | LORO range |
|---|---|---|---|---|
| fast: live-vol 0.5-2% | -0.002 | [-0.017, +0.014] 0.596 | [-0.015, +0.011] 0.628 | -0.002 .. +0.003 |
| fast: live-vol 50% blend | -0.001 | [-0.014, +0.012] 0.549 | [-0.012, +0.010] 0.557 | -0.001 .. +0.002 |
| fast: vol30 0.5-2% | -0.004 | [-0.022, +0.014] 0.681 | [-0.020, +0.012] 0.710 | -0.004 .. +0.001 |

Run because the briefing asks for them on anything worth documenting; none
of the three beat live on both eras, and the intervals show the fast-only
change is indistinguishable from zero at every block length.

## Why it fails — the mechanism, measured

The premise is TRUE: live whipsaws are concentrated in turbulent tapes.
Per vol_live tercile (bounds 16.0% / 24.5%), live macro whip10 is
13 / 31 / 47 (5.9 / 14.1 / 21.4 per 1000 days). The vol-scaled buffer
(mean 0.58% / 0.90% / 1.83% by tercile) does what it claims in the
high-vol tercile: whip10 47 -> 29, transitions 143 -> 118. But in the
low-vol tercile whip10 goes 13 -> 31 and transitions 44 -> 66, and the
mid tercile also worsens (31 -> 37). Net: 91 -> 97 whipsaws and 306 -> 316
transitions. **The rule redistributes whipsaws from turbulent to calm
tapes and adds more than it removes.**

Two reasons the trade is bad even where the wide buffer "works":

1. Turbulent-tape whipsaws are driven by moves of 3-5% a day; widening the
   buffer from 1% to 2-4% removes only the marginal ones (47 -> 29, not to
   zero) while delaying every genuine break in exactly the tapes where a
   day of delay costs most. 2011 illustrates it: the variant has MORE
   whipsaws that year (7 vs 5 on whip10, same 22 transitions) and its
   better 2011 return (-16.7% vs -18.9%) comes from the accident of an
   11-18 B>F skip, not from fewer flips. 2009 (-2.2 to -4.2pp), the
   recovery from the highest-vol tape in the record, is where the wide
   buffer's delayed re-entries show up.
2. Calm-tape whipsaws are cheap individually but the narrow buffer creates
   many of them, each carrying a forced rebalance (`run()` re-trades on a
   state change regardless of the drift band) at 4 bp one-way, and each
   putting the strategy briefly in the wrong row.

The fixed-buffer sweep says the same thing from the other side: Sharpe is
maximised near 1.0-1.25% and whipsaw count keeps falling well past the
Sharpe peak. Whipsaw count is a symptom, not the objective, and vol is
the wrong dial for it because the tapes with the most whipsaws are also
the tapes where a wider buffer costs the most.

## Classification

**No signal.** Not "signal too small" — the direction is wrong or absent:
the flipped placebo beats the hypothesis 6/6 on the search era, the
year-shuffled placebo matches or beats it, and every one of 21 variants
loses on the search era its mean was pinned to. Not a risk-preference
dial — exposure is unchanged at 0.662 and MaxDD moves both ways with no
CAGR trade-off attached. This is the category the briefing says works (vol
as a scaling input to a parameter) and it still does not work here,
because the parameter it scales (the buffer) has a cost that ALSO scales
with vol.

What would have to be true for it to work: whipsaws in turbulent tapes
would have to be removable with a 2-3% buffer at no cost in entry delay,
and calm-tape whipsaws would have to be rare enough that a 0.5% buffer
does not create them. The tercile table shows neither holds: the wide
buffer only removes 38% of high-vol whipsaws, and the narrow buffer more
than doubles low-vol ones.

Not worth revisiting with a different vol estimator (30d and max(10,30)
give the same answer), a different clamp (three ranges and a 50% blend give
the same answer), or a different horizon (h is not identified once the mean
is pinned). The only untested axis is an asymmetric version (vol-scale the
exit only or the entry only), and P6 on STRATEGY.md already found nothing
in asymmetric hysteresis with fixed buffers.

## Files

- `paper-track/vol_hysteresis.py` — the whole study; `compute_states_volbuf()`
  is the variant classifier, `calibrate()` pins the search-era mean,
  `rebuild()` rewrites `state`/`eff` on copied harness rows.
- No new data files. No edits to state.py, STRATEGY.md, data/, or trigger
  prompts.
