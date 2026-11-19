# Weakening the extension trim (2026-11-19) — `trim_study.py`, `trim_study_run.log`, `trim_study.json`

Variants (rest of the design = current, cap 2.0, sleeve off): current (all TQQQ out at the first held vote),
half (half out), two-vote (half at 1, all at 2), to-QLD (TQQQ dollars to QLD), wider (lines 15/17/20%), no-trim.
Pre-registered bar: higher Sharpe on untouched sets and synthetic worlds, giving up <= 0.05 median Sharpe and
<= 3 pp median max DD on the bootstrapped QQQ history.

None passes outright.
- half: untouched excess Sharpe NDX 0.52->0.66, Nikkei 0.05->0.14, DAX 0.29->0.33, FTSE -0.11->-0.12; synthetic
  +0.04..+0.10 Sharpe, +2..+4 pp CAGR. QQQ bootstraps: holdout -0.00..-0.03 Sharpe, proxy -0.01..-0.05, real L120
  -0.11 (fails); median DD 2-3 pp deeper. Single paths: real 45.2%/1.93 -> 42.2%/1.68, holdout 22.4/1.07 -> 22.4/1.01.
- two-vote: within ~0.03 of current everywhere; untouched mixed (NDX up, DAX down). Little change either way.
- to-QLD and wider: behave like no-trim out of sample, but lose 0.08-0.17 Sharpe and 3-8 pp DD on QQQ bootstraps.
Half is the only real middle option; it is a preference (more steady-bull upside for ~3 pp more drawdown), not
a demonstrated improvement. No live change.
