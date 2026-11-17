# VIXY sleeve sweep (weight, trigger, NAV cap) - PLAN, pre-registered 2026-11-17 before any cell was run

Research only. Nothing adopted. No existing file touched; new files only in this folder.

## Live constants (paper-track/state.py, read 2026-11-17)
VIXM_INSTRUMENT = 'VIXY'; VIXM_ENTRY_VIX = 18.0 (VIX close strictly below); VIXM_EXIT_RATIO = 1.0 (used both as the entry
condition VIX/VIX3M <= 1.0 and the exit condition VIX/VIX3M > 1.0); VIXM_MIN_VOL = 0.20 (stress floor, plain 30d QQQ realized vol,
>=); VIXM_CASH_SHARE = 0.35; VIXM_FADE = 0.25 (exit when VIX <= 0.75 x highest VIX close since the latch was entered, high tracked only
while allowed; fade stays "killed" until the stress floor fails or the latch is re-entered); VIXM_OFF_D_ZONES = ('D2',) (off on ungated
effective-D days whose zone is D2). The sleeve is taken out of the cash leg first, then the QQQ legs (deep-E, VIX-panic) take from the rest.

## Engine
harness.py (review_2026_11) + gross cap 2.0 via cfg (CUR + gross_cap=2.0), sleeve rebuilt with a parametrised latch (verified to reproduce
the harness latch bit for bit at live values). Instrument returns: VIXY / VIXM split-adjusted closes from
vixy_calm_2026_11/{vixy,vixm}_yahoo_full.csv (on all windows). Same engine loop as the earlier study (rebalance on regime-key change, 5% drift
band, zero-leg rule, 2 bp one-way).
Windows: real 2015-11-03.. (real ETFs), proxy panel oos 2011-01-05..2015-09-02, late 2015-09-03.., joined 2011-01-05..2026-11-16.
Reference baselines to reproduce: real ~51.1% / 2.100 / -16.5; late ~52.0 / 2.029 / -20.1; oos ~22.6 / 0.963 / -16.4; joined ~42.7 / 1.690 / -20.1.
Known limit (stated up front): the sleeve was allowed on only 1.4% of 2011-2015 sessions in the earlier run, so the oos window may say little;
every table reports share of days the sleeve holds VIXY and the number of spells in each window.

## Implementation choices fixed in advance
- Latch entry requires VIX < entry_vix (or no level test), AND VIX/VIX3M <= entry_ratio (or no test), AND VIX/VIX3M <= exit_ratio. The last
  clause avoids a same-day-in/next-day-out flip-flop when the exit threshold is below the entry one; at live values it changes nothing. A
  consequence: "entry curve condition none" is identical to live while exit stays 1.00 (reported, not a bug). An extra diagnostic cell with no
  curve test at all (entry none AND exit none) is added and labelled EXTRA.
- Stress floor none => stress always true. Fade off => never kills. D2-off "off" => the D2 gate is not applied.
- Weight 0% is the no-sleeve book (the sleeve flag is dropped from the rebalance key). Weight > 0 keeps the live key behaviour.
- Spell = maximal run of sessions with a held sleeve weight > 0. "Days on" = share of window return sessions with held sleeve weight > 0.
- Sleeve P&L per day = held sleeve weight (NAV fraction after that close's rebalance) x VIXY return of the next session, in % of NAV (before
  trading cost). "Sleeve contribution %NAV/yr" = sum of that over the window / years.
- Worst 5 days of the book = worst 5-session compounded return (as in the earlier study). "Worst 5 sleeve days" = the five most negative daily
  sleeve P&L values, with dates (return dates).
- NAV cap (Part 4): target sleeve weight = min(0.35 x cash-leg, c); weights drift between rebalances, so max held weight can exceed c slightly.

## Grid
Part 1 weight w of cash leg, live trigger: VIXY {0,10,20,25,30,35*,40,50,60,75,100}%; VIXM reference {50,75,100}%.
Part 2 at w=35%, one knob at a time: entry VIX {15,16,17,18*,19,20,22,none}; entry ratio <= {0.90,0.95,1.00*,none}; exit ratio > {0.95,1.00*,1.05,1.10};
fade {off,15,20,25*,30,40}%; stress floor {none,15,18,20*,22,25}%; D2-off {on*, off}. Plus the EXTRA diagnostic above.
Part 3 joint: the two non-binary Part-2 knobs with the largest spread = max - min over the knob's cells of mean(dSharpe real, dSharpe joined)
vs live. Knob with the larger spread gets up to 5 values, the other up to 4 (window of grid values containing the live value, as centred as
possible), x weight {25,35,50}% => at most 60 cells.
Part 4 NAV cap c in {10,15,20,25,30}% on the live cell (sleeve = min(35% of cash leg, c x NAV)).

Metrics for every cell on every window: CAGR, Sharpe, max DD, annual vol, days on, spells, average sleeve weight when on and maximum, sleeve
contribution %NAV/yr, worst day and worst 5-session book return, worst single-day sleeve P&L and the 5 worst with dates. Differences vs live cell.

## Live-cell detail (real window)
Spell list (entry, exit, exit reason, days, VIXY return, contribution), win rate, share of total from best 1/3/5 spells, result with best 3 removed
(removal = subtract those days' sleeve P&L from the book's daily returns; approximate, carry not re-added).

## Robustness (live + shortlist)
Shortlist: live, w=25, w=50, top-4 non-live cells by mean dSharpe over the four windows (Parts 1-3, excluding w=0 and cells identical to live),
every cell that passes the reading rule below, NAV cap 20%. For each: first/second half (by sessions) and 2020-removed Sharpe difference vs
live on real and joined; one extra session of lag on the sleeve signal; 5 bp one-way on VIXY trades (differences vs live under the same
condition); block bootstrap 20-session circular blocks, 2,000 paths, paired with live: Sharpe and max-DD difference, P(diff<=0) / P(arm DD
not shallower), on all four windows (the Sharpe bootstrap is run for every cell on real and joined, the DD bootstrap for the shortlist only).

## Reading rule (fixed now)
"35% is fine / no change" if live Sharpe is within 0.03 of the best weight (Part 1 VIXY weights incl. 0) on BOTH real and joined, AND no
neighbouring weight (25, 30, 40, 50) beats live on Sharpe on BOTH oos and late by more than 0.02.
A different weight or trigger value is "worth proposing" only if, vs live: Sharpe higher on real, late, joined; oos Sharpe not lower by more
than 0.01; max DD not deeper by more than 0.5 pp on any of the four windows; its adjacent grid neighbours on the same knob (the live cell
counts as neutral; neighbours other than live must have Sharpe above live on real, late and joined) agree (plateau, not spike; for Part 3
the neighbours are the axis-adjacent cells of the 3-D grid); dSharpe > 0 in both halves and with 2020 removed on both real and joined;
bootstrap P(dSharpe<=0) < 0.10 on real or joined. Otherwise no change.
Separately flagged (not a proposal): a pure risk trade-off = worst single-day sleeve loss on real or joined at least 20% smaller than live, or max
DD at least 1.0 pp shallower on real or joined, reported with its CAGR cost.
Caveats stated in advance: ~110 cells are tested; a best cell picked from a grid is biased upward, so judge by plateaus; Sharpe differences below
roughly 0.03 are within bootstrap noise; the oos window has very few sleeve days; real and late are the same market years (not independent).
