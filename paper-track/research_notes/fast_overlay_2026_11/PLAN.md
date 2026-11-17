# Fast re-entry overlay: where does the drawdown come from, which half earns, can it be made safer? (PLAN, written 2026-11-17 before any arm was run)

Research only. Nothing in the repo is edited, committed or pushed; new files live in this folder. Engine: `paper-track/harness_live.py` (live design, L1 off,
2.0x cap, VIXY 35% sleeve from 2011 on the proxy), reused through its own `build()` pieces (copied into `run.py` so the overlay can be varied); `run.py` first
asserts that its FULL arm reproduces `HL.run_live` to 1e-12 on all three windows and that OFF_audit reproduces the 2026-11-17 audit's R02 OFF arm
(real 47.8% / 2.065 / -16.5%, proxy 30.1% / 1.417 / -18.6%).

## Honest framing (stated before the numbers)
The overlay was adopted 2026-09-06 on the 26-year proxy plus the SPMO-era real data, i.e. on data that overlap every window used here. Rules adopted after it
(trim v2, D ladder, D gate, vol-target estimator, A 40/60, cap, sleeve) were tuned with the overlay ON. So OFF is partly "a hybrid that never existed", and
anything that looks better than FULL here is NOT an out-of-sample finding: this study is at best a re-weighing of an in-sample choice. Nothing is adopted.

## Two OFF arms
* OFF_audit: the audit's arm (`cfg fast=False`): effective state = macro, but the extension-trim held votes are still computed on the FAST-OVERLAY A spells
  (the engine's quirk the audit flagged). Needed to reproduce the audit.
* OFF: a clean off. Held votes recomputed on the arm's own A spells (macro A only). Every arm recomputes held votes from its own effective states.
OFF (clean) is the primary OFF for the "turn it off" rule; OFF_audit is shown beside it and a disagreement is reported as such.

## Windows (all end 2026-11-16)
real = real ETFs, returns from 2015-11-03; p01 = proxy from 2001-01-03; p10 = proxy from 2010-01-05 (VIXY sleeve from 2011-01-04 on both proxy windows).
A fourth run pY (proxy from the first session after the 200-day macro read exists, mid-2000) is used ONLY for the 2000 line of the year table; the start is partial.

## Arms (everything else live). 21 arms: 14 pre-registered + OFF_audit + 6 neighbours (marked n)
Base: OFF_audit, OFF, FULL (live), BC_ONLY (B/C->A only), F_ONLY (F->C only).
Lower row (B/C hold X instead of the A row; F->C unchanged; X is a flat row with no trim): LR50 = 50/50 SPMO/TQQQ, LR75 = 75/25, LR100 = 100% SPMO.
F->C stricter: F_AB = fast read A or B only; F_A (n) = fast read A only.
Confirmation (the overlay condition must have held N consecutive sessions to take effect; it drops the day it fails): CONF2, CONF3.
Fast windows (same classifier, 1% hysteresis, on the normalised QQQ path): W20_80, W30_150 (the old micro pair), W30_100 (n; plateau edge per STRATEGY.md).
Stress filter (overlay off for the day when the condition holds): V30 = QQQ 30-day realized vol > 30% (the engine's `vol`), V25 (n), V40 (n);
VT100 = VIX > VIX3M, VT95 (n) = VIX > 0.95 x VIX3M, VT105 (n) = VIX > 1.05 x VIX3M (VIX3M in the harness starts 2009-09-18, so before that date the VIX filter is off and these arms equal FULL: 2001-2002 and 2008 are untouched by them).
Families for the neighbour test (adjacent members only): lowrow [LR50, LR75, LR100]; fcut [F_A, F_AB]; conf [CONF2, CONF3]; win [W20_80, W30_100, W30_150];
vol [V25, V30, V40]; vix [VT95, VT100, VT105]. Each signal-timing choice is the live one (decision on the day's close, trade at that close).

## Fairness control
For every arm and window: FULL with a flat multiplier on the four risky legs (after vol target and cap; `risky_scale` as in leverage_a_2026_11) bisected so that
FULL's average target equity-like gross over the window equals the arm's (SPMO 1x, TQQQ 3x, QLD 2x, XLU 1x, QQQ legs 1x; VIXY/cash excluded; averaged over
sessions s0..T-1 as harness_live reports it). Scale allowed 0.2..1.6 (an arm with MORE gross than FULL is compared with a levered-up FULL).

## Metrics
Per arm and window: CAGR, Sharpe (mean/sd, no rf, as the project), max DD, worst 20 sessions (rolling compounded), average gross, share of sessions where the
effective state differs from macro, overlay entries per year (days the overlay turns on from off), trades/yr.
Year table: calendar-year return of each arm minus FULL (pp) on p01 for 2001-03 and 2008-09, 2018, 2020, 2022, 2025, 2026; 2000 from pY; the same post-2015 years on real.
Robustness: halves of p01 (by sessions); ex-2020 (2020 sessions deleted from both series); one session of lag on the FAST read only (each arm rebuilt with
fast[t-1]; compared with FULL also lagged); block bootstrap, 2,000 paths, 20-session circular blocks, paired across arms, of dSharpe and dMaxDD
(arm minus FULL, and arm minus its matched de-lever; dMaxDD > 0 means the arm is shallower).

## Q1 drawdown attribution (p01)
Top 5 non-overlapping drawdown episodes (peak, trough, recovery, depth) for FULL, OFF, OFF_audit. Every overlay spell (contiguous run with eff != macro):
dates, type, macro/fast state, QQQ move, FULL book return, OFF book return, sum of daily log-return difference (FULL - OFF) allocated to the spell; the spells
inside the FULL and OFF max-DD windows; per-episode concentration (share of the total log-difference from the worst 5 spells).

## Reading rule (fixed now)
Keep FULL unless an alternative A satisfies ALL of, versus FULL:
 1. p01 max DD at least 2.0 pp shallower;
 2. Sharpe not lower than FULL by more than 0.02 on ANY of real, p01, p10;
 3. Sharpe above its own matched de-lever on real AND on p01;
 4. holds in both halves of p01 and with 2020 removed: in each of (h1, h2, ex-2020) dSharpe >= -0.02 and the max DD (computed inside that sub-sample) not deeper than FULL's;
 5. a neighbouring arm in its family points the same way: p01 max DD at least 1.0 pp shallower than FULL and p01 dSharpe >= -0.02 (an arm in a family with no
    other member cannot pass; BC_ONLY, F_ONLY, OFF are diagnostics and are not candidates);
 6. bootstrap P(dMaxDD <= 0 vs FULL) < 0.20 on p01.
Turning the overlay OFF is worth proposing only if OFF (clean) has a higher Sharpe than FULL's matched de-lever on at least 2 of the 3 windows (and OFF_audit is reported alongside).
A difference smaller than about 0.02 Sharpe (the bootstrap's resolution in earlier studies) or 1 pp of max DD is called noise unless the bootstrap says otherwise.
Caveats to report: target-weight (not drifted) gross, VIXY absent before 2011, full-day highs irrelevant (L1 off), proxy leveraged legs synthetic.
