# Election year / month / day vs the strategy — 2026-10-14

Owner: "research on if election year/month/day will be a big enough factor to this
strategy" (the midterm is Tue 3 Nov 2026). Script `paper-track/election_cycle_study.py`,
log `election_cycle_study_run.log`; hook `fall_protection_study.DATE_SCALE` (default off).
Pre-registered in the script docstring before the run.

## Verdict — not a big enough factor; nothing applied

**1. The market has a cycle, but it is weak evidence.** Calendar-year price return
by cycle position:

| | election yr | post-election | midterm yr | pre-election | permutation p |
|---|---|---|---|---|---|
| NYSE Composite 1971–2025 | +8.0% | +10.4% | **−0.3%** | +14.4% | 0.06 |
| Nasdaq-100 1986–2025 | +9.2% | +19.3% | +5.6% | **+39.1%** | 0.07 |
| QQQ 2000–2025 | +3.8% | +19.3% | **−4.7%** | +28.5% | 0.16 |

The familiar "weak midterm year, strong pre-election year" pattern is there in all
three, but with 6–14 years per bucket none clears 5%.

**2. The strategy already sidesteps it.** Over the same 2001–2025 days the strategy's
midterm years average **+21.3%** against QQQ's −5.2%; its cycle spread (24 pp) is
smaller than QQQ's and nowhere near significant (p 0.62). Bad midterm years (2002,
2022) were bear markets, and the state machine was mostly in cash for them. The
cycle effect is a trend effect the classifier already trades.

**3. Election day itself: a run-up into midterms, nothing reliable after.**
Ten sessions into a midterm election day: Nasdaq-100 +2.9% (p 0.03), NYSE +1.5%
(p 0.04), QQQ +1.9% (p 0.18). The strategy captured it (+3.1% proxy). The ten sessions
after are noise everywhere (all p ≥ 0.10). October of election years is weak for QQQ
(−0.3% vs +6.3% in odd years) but rests on 13 Octobers including 2000 and 2008.

**4. Every rule fails** (A base 40/60; P1 Sharpe ≥ live on both harnesses, P2 holdout
≥ live, P3 placebo top 5% vs 200 shifted calendars):

| rule | ΔSharpe real / proxy | Δholdout | placebo rank | verdict |
|---|---|---|---|---|
| R1 ×0.5, −5..+5 sessions, all elections | +0.004 / −0.023 | −0.036 | 0.90 | fail |
| R2 cash, same window | −0.010 / −0.055 | −0.076 | 0.93 | fail |
| R3 ×0.5, presidential only | +0.001 / −0.010 | −0.010 | 0.83 | fail |
| R4 ×0.75 midterm yr, Jan 1 → election | +0.029 / +0.006 | −0.024 | 0.12 | fail (P2, P3) |
| R5 ×1.2 election → Dec 31 | +0.001 / −0.001 | −0.003 | 0.40 | fail |

De-risking around election day costs money, because the window is a run-up. The only
rule with a positive sign, the midterm-year haircut, loses in the 2000–2015 holdout
and does no better than the same rule on random dates.

## For 3 Nov 2026

No action. The design holds A at 50/50 into the vote; history favours being invested
into a midterm. If the vote moves markets, the vol target and the state machine respond
the same way they do to any shock.
