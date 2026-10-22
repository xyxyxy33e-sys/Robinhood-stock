# D at 1x leverage (2026-10-22)

Script: `paper-track/monte_carlo_d1x.py`. Full tables: `monte_carlo_d1x_run.log`. Research only.

## Candidate and comparisons

**Candidate.** Every D-ladder zone (D1/D2/D3) holds 100% core: SPMO on real
ETFs, QQQ on the proxy. The D gate still goes to cash.

It is paired against two designs on the same 1,000 paths, in 12 cells:
- **the 2026-10-22 live design;**
- **an exposure-matched control:** live with its vol target lowered, per
  cell by bisection, to 16.1–17.1%, until its average QQQ-equivalent
  leverage equals the candidate's.

## Results

**Against live.**
- Shallower MaxDD on 66–83% of paths in every cell. The p5 MaxDD is
  1.4–3.4 pp better.
- Sharpe is better only in short-trend worlds: 52–58% at L20/L60 (real L60
  42%), and 20–45% at L120/L250.
- Median CAGR is −0.1 to +0.2 pp at L20, and −1 to −7 pp at long blocks.
- Single historical path: real 48.8% / 1.864 / −19.0% → 38.2% / 1.688 /
  −20.9%; proxy 31.2% / 1.260 / −27.5% → 25.3% / 1.144 / −28.6%.

**Against the matched control.**
- The candidate never wins. Sharpe is better on at most 54% of paths, and
  on 26–44% at most block lengths.
- The control has the shallower MaxDD on 55–73% of paths, with a p5 MaxDD
  0.4–2.5 pp better.
- The candidate's median CAGR is 0.0 to −2.7 pp lower.

## Reading

- **De-levering D is a risk dial, and an inefficient one.** It buys less
  drawdown and a little help in choppy worlds, at a large return cost in
  trending ones.
- **The same average leverage taken off everywhere** (a ~16.5% vol target)
  does better on drawdown, Sharpe and return in every cell.
- **This fits the D-ladder research.** The deeper D zones (below the 100d)
  carry the strongest next-session returns, so D leverage earns more than
  its share.
- **Verdict:** no change. If less risk is wanted, lower the vol target or
  the A split rather than D.
