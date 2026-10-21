# Monte Carlo: does the live design beat the benchmarks? (2026-10-21)

Script: `paper-track/monte_carlo.py`. Full tables: `research_notes/monte_carlo_run.log`.
Research only. Nothing live changed. STRATEGY.md not edited.

## Question

Every figure in STRATEGY.md comes from one historical path. This test asks
how the live design (2026-10-09 release: A 25/75 + extension trim v2 with
carry, D gate, D ladder, 30d vol target, 5% band, 4bp) does across many
plausible 10-year paths. On how many of them does it beat holding QQQ, SPY
or SPMO? And does it beat QQQ held at the **same volatility** or the **same
average leverage**? That last pair is the fair test, because it separates
timing skill from simply holding more risk.

## Method

- **Generator:** a stationary block bootstrap of whole trading days. Every
  column (QQQ, the EW breadth leg, core, TQQQ, QLD, cash, SPY, SPMO) is drawn
  from the same day, so correlations, leverage decay and fat tails are kept.
  The mean block length L is swept over 5, 20, 60, 120 and 250 sessions.
- **Signals are recomputed from each synthetic path.** That covers the 50/200
  and 20/100 classifiers, the gaps, 30d vol, held trim votes, the breadth
  percentile and the D gate. Each path gets a 420-session warm-up, then a
  scored 10-year horizon. 1,000 paths per cell.
- **Engine:** a numpy re-implementation of the live path, vectorised across
  paths. `--verify` checks it against `state.py`'s own functions on 6,378
  real sessions. Macro, fast, held votes, breadth pct and D gate all have
  **0 mismatches**, and the worst target-weight difference is 3e-16. It also
  reproduces the standing figures on the historical path:
  - proxy 2001–2026: **33.7% / Sharpe 1.310 / −26.6%** (spec: 32.7% / 1.275 / −27.7%)
  - real 2015-11..2026-08: **50.9% / 1.879 / −19.2%** (spec, which includes VIXM: 54.7% / 1.977 / −19.4%)
- **Panels:**
  - proxy, 1999–2026: QQQ core, synthetic 2x/3x legs
  - holdout, 1999-09..2015-10: the proxy cut before any live parameter was fit
  - real, 2015-10..2026-08: real ETFs
- **Not modelled:** the VIXM sleeve (cash is all T-bill), taxes, deposits.
  Real-panel prices are price-only.
- **Sharpe** is the project's mean/sd with no risk-free rate (`annual_stats`).

## Result: it depends on how long trends last

| panel / L | strat median CAGR | p5 CAGR | median Sharpe | median MaxDD | P(CAGR > QQQ) | P(CAGR > SPY) | P(CAGR > QQQ same vol) | P(MaxDD shallower than QQQ) |
|---|---|---|---|---|---|---|---|---|
| proxy L5 | 3.8% | −10.0% | 0.27 | −57.7% | 21.6% | 26.8% | 20.5% | 24.3% |
| proxy L20 | 7.0% | −6.3% | 0.39 | −50.8% | 34.8% | 41.3% | 33.5% | 40.7% |
| proxy L60 | 13.8% | 0.4% | 0.63 | −43.0% | 65.7% | 72.7% | 64.1% | 63.0% |
| proxy L120 | 18.5% | 4.5% | 0.81 | −37.8% | 89.1% | 91.5% | 85.5% | 74.7% |
| proxy L250 | 24.0% | 9.0% | 1.00 | −33.9% | 96.2% | 98.2% | 93.4% | 79.6% |
| holdout L5 | 0.2% | −13.7% | 0.14 | −61.2% | 28.9% | 26.8% | 27.6% | 38.9% |
| holdout L20 | 3.4% | −10.0% | 0.26 | −54.2% | 42.0% | 42.8% | 40.6% | 58.3% |
| holdout L60 | 6.8% | −5.1% | 0.39 | −46.5% | 65.7% | 62.5% | 63.0% | 76.7% |
| holdout L120 | 11.6% | −1.5% | 0.57 | −38.5% | 81.7% | 84.2% | 78.7% | 87.5% |
| holdout L250 | 15.2% | 3.6% | 0.70 | −34.4% | 91.3% | 93.5% | 87.9% | 89.1% |
| real L5 | 12.7% | −1.8% | 0.58 | −47.5% | 19.9% | 46.3% | 13.4% | 9.4% |
| real L20 | 14.6% | −0.4% | 0.67 | −43.4% | 30.0% | 58.4% | 20.4% | 14.9% |
| real L60 | 23.1% | 7.9% | 0.98 | −37.7% | 69.6% | 89.4% | 60.1% | 27.9% |
| real L120 | 32.0% | 15.7% | 1.28 | −34.1% | 92.4% | 99.0% | 90.4% | 45.1% |
| real L250 | 40.5% | 24.9% | 1.53 | −29.8% | 99.1% | 99.9% | 98.5% | 66.6% |

For reference, QQQ's median 10-year CAGR is 10–11% on the proxy and ~19–20%
on the real panel at every L. The strategy averages ~0.9–1.2x QQQ-equivalent
leverage, with ~45–55% of NAV in risky legs and ~35–40 rebalances a year.

## Reading

1. **It beats the benchmarks only when market trends last for months.** When
   blocks are longer than about 60 sessions, the paths keep the multi-month
   trends of real history. Then the design beats QQQ, SPY and SPMO in 65–99%
   of paths. It also beats QQQ held at the same volatility and the same
   average leverage, so the gain is timing, not just more risk. When blocks
   are 5–20 sessions, those trends are broken up while daily volatility
   clustering stays. Then the design loses to plain QQQ in 65–80% of paths,
   with a deeper median drawdown (−51% to −58% proxy). The 2.5x rows and the
   classifier whipsaw. **The edge is a bet that multi-month trends keep
   happening, and nothing else.**
2. **The edge survives the holdout era, but smaller.** 2000–2015 was not used
   to fit any live parameter. At L ≥ 60 it still beats QQQ in 66–91% of
   paths, and it cuts drawdown more reliably than in-sample (P(shallower
   MaxDD) 77–89%). The median CAGR is about half the proxy figure.
3. **The real panel is the most flattering and the least trustworthy.** It is
   a single 11-year bull market (one bear, 2022), and the rules were tuned
   inside it. Even so, at short L it loses to QQQ 70–80% of the time and to
   same-vol QQQ ~80–87%. At long L it is 40% median CAGR, which re-samples the
   same episodes the ~90 tested arms were selected on.
4. **Long blocks overstate the edge.** At L=250 a 10-year path is ~10 draws
   from only ~27 (proxy) or ~11 (real) distinct years. These are the years the
   design was tuned on, so long-L numbers are partly in-sample by
   construction. Treat proxy L60–L120 as the central case and holdout L60–L120
   as the conservative one. The single historical path sits above the L=250
   median, as expected for a tuned design.
5. **Tail risk is fat in every world.** The p5 MaxDD is −43% to −85%. In the
   short-L worlds, 6–8% (real), 20–33% (proxy) and 35–49% (holdout) of
   10-year paths end with less money than they started, against ~10–13% for
   QQQ on the proxy (P(loss) in the run log). The single-path −19% to −27% drawdown
   figures in STRATEGY.md are not a planning number.

**Bottom line:** in the central case (proxy L60–120) the design beats buy-and-hold
QQQ in ~66–89% of 10-year paths. The margin is ~+3 to +9 pp median CAGR, with a
shallower drawdown in 63–75% of paths, and the margin survives the
same-risk controls. That is conditional on multi-month trend persistence
continuing. Without it, the design is worse than holding QQQ. The headline
50%+ figures belong to the most favourable resampling and should not be
expected.

## Caveats

- The bootstrap cannot create regimes the history lacks (e.g. a 1987-style
  −20% day from calm). Stitching blocks also produces some trends that never
  happened.
- No VIXM sleeve. The spec credits it with a few points of real-era CAGR.
- Synthetic 2x/3x legs on the proxy carry ~3% tracking error
  (`long_history_backtest.py`).
- No taxes. ~35–40 rebalances a year in a taxable account would cost
  materially more than the 4bp model.
