# Is there a better version of L1? Plan (2026-11-17, written before any arm was run)

Research only; nothing adopted, no existing file touched, nothing committed. Engine: `paper-track/harness_live.py` (live design: 2.0x cap, VIXY 35% sleeve incl. proxy from 2011,
vol target 20%, D ladder, 2 bp) with the **complete** QQQ highs (file + AlphaVantage full-day highs 2026-09-08..11-10 + live 15:50 highs 11-11..). python3, numpy only.
The D gate is a boolean per session; every arm below only changes the gap-to-200d half of it (`gate_g`), injected by replacing `HL.signals`
(SMA200 always includes that day's close; "gap on X" = X / SMA200 - 1; close rule = gap on close >= 2%). HALF additionally scales the four risky legs (after the vol target, before the 2.0x cap).
Fill is at the close in every arm (as live).

## Step 1 - event list (events.py -> events.log, events_real.csv, events_proxy2001.csv, spells_*.csv)
Event = session in macro-D with breadth gate open where close-only gate is shut and L1 gate is open. Fields as requested; return difference L1 minus C0 =
compounded return difference over the next 1/5/20 sessions (the weights set at the event close earn from the next session) and over the "spell" (until the two books' target
weights re-align, plus the following session). Event days within one spell are merged for the concentration table (non-overlapping spells); per-event numbers overlap.

## Step 2 - 15:50 highs
AlphaVantage intraday is a premium endpoint (rate-limit/premium error) so it is unusable. Robinhood get_equity_historicals (5/30-minute bars) works back to ~2026-03 at least and
returns flat interpolated bars for 2025. So only event days 2026-03-06, 2026-10-30, 2026-11-02, 2026-11-04 (+ 2026-11-11 live 15:50) can be checked; older events cannot (reported as such).
Variants are run with the full-day high everywhere and again with the 15:50 high substituted on the days where it was fetched.

## Arms (21; all on complete highs; everything else live)
- C0 close only; L1 live (gap on high >= 2%).
- H-x: open if close gap >= 2% OR gap on high >= x, x in {2.5%, 3%, 4%}.
- HC-y: open if gap on high >= 2% AND close gap >= y, y in {0, 0.5%, 1.0%, 1.5%}.
- R-z: open if close gap >= 2% OR (high gap >= 2% AND close/high - 1 >= -z), z in {0.5%, 1.0%, 1.5%}.
- TP3: open if close gap >= 2% OR gap on (H+L+C)/3 >= 2%; TP2: same with (H+C)/2. Lows after 2026-09-04 from Robinhood daily bars.
- P2: open if close gap >= 2% OR (high gap >= 2% today AND yesterday's high gap >= 2%).
- HALF: gate open when the high clears; when the close does not clear, the four risky legs are halved (rest to the cash leg); full row once the close clears.
- VIXF: high counts only if VIX(t) < mean of VIX over the last 10 sessions incl. t, OR VIX(t) < VIX(t-1); VIXFa: only the 10-day-average condition; VIXopp: the opposite of VIXF (VIX >= its 10-day mean AND not down on the day). Daily VIX close (a 15:50 reading is not in the data: approximation).
- OPEN-ONLY: the high counts only if the previous session was not already in ungated D (L1 may re-open a shut gate, not keep an open one). CLOSE-ONLY: the high counts only if the previous session was in ungated D (L1 may keep an open gate, not open a shut one). The live code (`state.gate_gap200`) is stateless, so this distinction is a research construct that would need a stored flag; it does not exist in the current code path.

## Windows and metrics
real = real ETFs from 2015-11-03; proxy01 = proxy from 2001-01-03; proxy10 = proxy from 2010-01-05 (sleeve from 2011 on the proxy); real-ex = real window ended 2026-10-23
(i.e. without 2026-10-26..11-16, which is the end of the sample). All end 2026-11-16 otherwise. Per arm and window: CAGR, Sharpe (mean*252/vol), max DD, worst day, worst 5 / 20 sessions (rolling compounded),
number of sessions with a gate opening that C0 does not have ("L1-only openings"; HALF counts half-size ones), average target gross.
Robustness for any arm whose Sharpe beats C0 on real, proxy01 and proxy10 (and always for L1): halves (by session count), ex-2020 (2020 sessions dropped), one session of lag (all windows),
paired block bootstrap of the Sharpe difference vs C0 (20-session blocks, 2,000 paths, seed fixed), and a **placebo**: for each session draw a random day from the same calendar year and use its (high/close - 1, low/close - 1) on this session's close,
200 draws, same arm rule on the placebo highs, report the percentile of the real arm's Sharpe gain vs C0 among the 200 placebo gains (real, proxy01, proxy10; proxy10 sliced from the proxy01 run).

## Reading rule (fixed now)
An L1 variant is worth proposing only if, versus C0 (close only):
1. Sharpe higher on real, proxy01 and proxy10 by at least 0.02 each;
2. max DD not deeper by more than 0.5 pp on any window (real, proxy01, proxy10, real-ex);
3. holds with 2026-10-26..11-16 removed (real-ex Sharpe gain >= 0.02) AND with it included (rule 1 on real);
4. holds in both halves of proxy01 (Sharpe gain > 0 in each half);
5. neighbouring parameter values point the same way (Sharpe gain > 0 on real, proxy01 and proxy10 for the adjacent values of its family; arms without a parameter are "n/a" and flagged);
6. placebo percentile >= 90 on at least one track.
Otherwise "keep L1 off" (C0) is the conclusion. The same rule is applied to the original L1 on complete data and reported plainly.
Known approximations to report: full-day highs include 15:50-16:00 (only 5 days checked); VIX is the daily close; HALF/OPEN-ONLY/CLOSE-ONLY are research constructs; sample of L1 events is small (19 real, 49 proxy sessions).
