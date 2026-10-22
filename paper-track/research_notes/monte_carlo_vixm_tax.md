# Monte Carlo: the VIXM sleeve and after-tax returns (2026-10-22)

Scripts: `paper-track/monte_carlo_vixm.py`, `paper-track/monte_carlo_tax.py`.
Run logs: `monte_carlo_vixm_run.log`, `monte_carlo_tax_run.log`.
New data: `data/vixm_daily.csv` (provenance in `data/vixm_daily_provenance.md`).
Research only. Nothing live changed.

## 1. The VIXM cash sleeve (live since 2026-10-08)

**Method.**
- **Bootstrap.** VIX and VIX3M are levels, so resampling them would invent
  spikes at block boundaries. Instead, the ON/OFF latch is computed on the
  real VIX/VIX3M history (FRED). It is carried with each sampled day, along
  with that day's VIX level and VIXM return.
- **Replay.** The stress test (QQQ 30d vol ≥ 20%), the 25% fade and the
  "killed" state are replayed on each synthetic path, against that path's
  own vol.
- **Check.** The replay matches `state.vixm_series` on all 2,735 real
  sessions (0 mismatches).
- **Panels.** `real` (2015-10..2026-08) and `proxy2011` (2011-01..2026-08:
  QQQ core with synthetic 2x/3x legs, real VIXM). VIXM does not exist before
  2011.
- **Base.** The 2026-10-22 live design without VIXM, paired on the same
  1,000 paths.
- **Historical path.** Real ETFs: 48.8% / 1.864 / −19.0% → **52.2% / 1.968 / −19.0%**
  with VIXM.

| cell | P(Sharpe better) | P(MaxDD shallower) | median ΔCAGR | Δ p5 MaxDD |
|---|---|---|---|---|
| real L20 | 50% | 41% | +0.2 pp | −1.2 pp |
| real L60 | 76% | 50% | +1.5 pp | −0.4 pp |
| real L120 | 90% | 49% | +2.3 pp | +0.2 pp |
| real L250 | 96% | 51% | +3.0 pp | −0.1 pp |
| proxy2011 L20 | 35% | 33% | −0.5 pp | −2.1 pp |
| proxy2011 L60 | 57% | 37% | +0.4 pp | −1.5 pp |
| proxy2011 L120 | 74% | 40% | +1.1 pp | −0.8 pp |
| proxy2011 L250 | 85% | 43% | +1.6 pp | −0.5 pp |

**Reading.**
- **The sleeve adds return, not protection.**
  - When trends last a quarter or more, it adds 0.4–3 pp a year and lifts
    Sharpe on 57–96% of paths.
  - In short-trend worlds it is flat to slightly negative.
  - It does not make drawdowns shallower. The p5 MaxDD is 0.1–2 pp deeper
    in most cells, because VIXM decays while held.
  - Gains are smaller on the 2011+ panel than on 2015+.
  - Few spike episodes drive it (STRATEGY.md: about a third of the gain is
    August 2024). Long blocks resample those same episodes, so L250 is the
    flattering end.
- **Lag.** With the whole book traded one session late, the sleeve still
  adds value against the equally lagged base: Sharpe higher on 42–98% of
  paths, ΔCAGR −0.2 to +4.0 pp. This is not the same test as the 10-08
  research's "one extra session of VIXM lag erases most of it", which
  delayed only the VIXM leg. That warning is not contradicted, and the
  sleeve still has to fill in the 15:5x window.
- **Verdict.** Keep it. It is a modest, regime-dependent return enhancer
  with no drawdown benefit, consistent with how it was sold.

## 2. After-tax returns

**Method (lot level).**
- Every buy opens a lot. Sells close FIFO or HIFO lots.
- A lot held < 252 sessions is short-term, otherwise long-term.
- Taxes settle every 252 sessions: ST/LT netted, losses carried forward, the
  tax paid by trimming every leg pro rata.
- The book is liquidated at the end of 10 years. QQQ buy-and-hold pays LT
  tax once, at the end.
- Check: at 0% tax the replay matches the engine to 1e-14.
- Not modelled: wash sales (they would make the strategy look worse),
  dividend tax, state tax.
- 500 paths per cell, 2026-10-22 live design (no VIXM).

Median 10-year CAGR, pre-tax → after tax (share of paths beating QQQ after tax):

| cell | QQQ | live (FIFO) | live (HIFO) | live + 10% band (HIFO) |
|---|---|---|---|---|
| **top bracket, ST 40.8% / LT 23.8%** | | | | |
| proxy L60 | 9.5 → 7.8% | 12.0 → 6.8% (47%) | 12.0 → 6.9% (47%) | 12.1 → 7.0% (46%) |
| proxy L120 | 10.5 → 8.7% | 18.5 → 10.9% (66%) | 18.5 → 10.9% (66%) | 18.4 → 11.0% (67%) |
| holdout L60 | 3.6 → 2.9% | 7.1 → 3.6% (55%) | 7.1 → 3.6% (55%) | 7.0 → 3.7% (56%) |
| real L60 | 19.2 → 16.6% | 22.5 → 13.4% (30%) | 22.5 → 13.5% (30%) | 22.6 → 13.7% (30%) |
| real L120 | 19.5 → 16.9% | 32.2 → 19.4% (65%) | 32.2 → 19.5% (65%) | 32.5 → 19.7% (67%) |
| **middle bracket, ST 24% / LT 15%** | | | | |
| proxy L60 | 9.5 → 8.5% | 12.0 → 9.0% (57%) | 12.0 → 9.1% (57%) | 12.1 → 9.1% (57%) |
| proxy L120 | 10.5 → 9.4% | 18.5 → 14.0% (76%) | 18.5 → 14.1% (76%) | 18.4 → 14.0% (76%) |
| holdout L60 | 3.6 → 3.1% | 7.1 → 5.0% (61%) | 7.1 → 5.0% (62%) | 7.0 → 5.0% (61%) |
| real L60 | 19.2 → 17.6% | 22.5 → 17.3% (48%) | 22.5 → 17.3% (48%) | 22.6 → 17.4% (48%) |
| real L120 | 19.5 → 17.9% | 32.2 → 24.7% (84%) | 32.2 → 24.8% (84%) | 32.5 → 25.0% (85%) |

**Reading.**
- **Tax is the biggest single cost the design carries.**
  - At the top bracket it gives up 5–13 pp a year, against 1.5–2.5 pp for
    QQQ. The after-tax edge over QQQ roughly halves: 30–67% of paths beat
    QQQ, against 66–92% pre-tax.
  - At the middle bracket it keeps most of the edge (48–85% of paths).
  - The cause is structural, as in the 09-06 study. Regime switches realise
    nearly every gain short-term.
- **Lot choice and the band hardly matter.**
  - HIFO adds ≤ 0.1 pp a year.
  - A 10% band adds a further ≤ 0.3 pp.
  - The trades that create the tax are regime trades, which neither touches.
- **Read it in context.** Per STRATEGY.md (2026-09-06), gains here are offset
  in a separate tax-loss-harvesting account, so after-tax return is not the
  objective. If that offset ever stops, this is the number that matters:
  the design's after-tax lead over buy-and-hold QQQ is small and
  regime-dependent at a top bracket.
