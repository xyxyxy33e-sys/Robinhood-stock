# A new strategy designed for the Monte Carlo (2026-10-22)

Script: `paper-track/monte_carlo_new.py`. Logs: `monte_carlo_new_search.log`, `monte_carlo_new_confirm.log`.
New data: `data/tlt_daily_tr.csv`. Research only. Nothing live changed.

## Premise and protocol

The live design's edge needs multi-month trends, so it loses when trends
are short. A design that beats QQQ in every bootstrapped world has to rely
on structure the bootstrap keeps at any block length:
- volatility clustering, used by vol targeting;
- the same-day stock/Treasury correlation, used by risk parity and static
  mixes.

Four families on QQQ (QQQ/QLD/TQQQ for leverage, no margin) and TLT, 132
candidates:
- **F1** vol target;
- **F2** F1 plus a 200d trend gate;
- **F3** inverse-vol QQQ/TLT risk parity with a vol target;
- **F4** static TQQQ/TLT mixes (no timing; the control).

The protocol was fixed before running:
- **Search:** 2002-08..2015-10 only, 400 paths, blocks 5/20/60/120/250.
- **Winner:** the highest worst-case P(CAGR > QQQ) across block lengths,
  subject to median MaxDD ≤ QQQ's and median Sharpe ≥ QQQ's at every
  length.
- **Confirmation:** 2015-11..2026-08 real ETFs, never seen by the search,
  1,000 paths; plus the full 2002–2026 panel and the single historical path.

## Result: the search winner failed out of sample

**Search (2002–2015).** The winner was the control, **static 30% TQQQ /
70% TLT**: P(CAGR > QQQ) 81–86% at every block length, with a shallower
drawdown. The best timing candidates (vol target, risk parity) only tied
QQQ, at 51–56%.

**Confirmation (real ETFs 2015–2026).**

| series | P(CAGR > QQQ), L5 → L250 | median MaxDD | historical path 2016-11..2026-08 |
|---|---|---|---|
| F4 static 30/70 (search winner) | **6–9%** | −36 … −46% | 15.3% / 0.76 / **−50.8%** |
| F3 risk parity 20% | 0–2% | −31 … −38% | 10.6% / 0.73 / −41.4% |
| F1 vol target 40%, no leverage | 2–41% | −31 … −34% | 20.2% / 0.96 / −35.4% |
| F2 vol target 40%, cap 2x, 200d gate ×0.5 | **83–98%** | **−38 … −46%** | 32.0% / 1.04 / −35.8% |
| live design (10-22) | 17–99% | −28 … −44% | 48.8% / 1.86 / −19.0% (from 2015-11) |
| QQQ | — | −32 … −34% | 21.2% / 0.96 / −35.2% |

## Reading

1. **Cross-asset search picks the regime of its window.**
   - 2002–2015 was a falling-yield bond bull with stocks and bonds
     negatively correlated, so stock/bond mixes looked dominant.
   - In 2022 both fell together. The winner then lost to QQQ on more than
     90% of real-era paths, with a −51% historical drawdown.
   - This is the clearest overfitting failure in the Monte Carlo work, and
     the protocol caught it only because the confirmation era was kept out.
2. **Vol targeting alone does not beat QQQ.** Unlevered it is QQQ with
   slightly better Sharpe in short-trend worlds, and nothing more.
3. **Only leverage beats QQQ's return in every world.**
   - F2 (about 1.5–2x QQQ when calm, half exposure below the 200d line)
     beats QQQ's CAGR on 75–98% of paths at every block length, real and
     full panels. It also beats the live design in short-trend worlds
     (85–92%).
   - It pays with a median drawdown 6–14 pp deeper than QQQ's, and a lower
     Sharpe than QQQ in short-trend worlds.
   - It failed the search's drawdown constraint, so the protocol did not
     pick it. It is a higher-risk QQQ, not a better one.
4. **Nothing beats QQQ on risk-adjusted return in every world.** Neither
   the new families nor the live design manage it. The live design is the
   only one that beats QQQ on Sharpe AND drawdown together, and only when
   trends last for months.
