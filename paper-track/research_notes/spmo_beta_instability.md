# SPMO's beta to QQQ is not a property — it resets every six months (2026-09-22)

**The core-leg case rests on "SPMO has beta 0.773 and correlation 0.833 to QQQ,
so it diversifies the leveraged sleeve." That number is an average over
reconstitution cycles whose betas range from 0.045 to 1.255. It is close to
meaningless as a forward statement, and the cycle that just ended was the most
Nasdaq-like in the fund's history.**

Measured while running the scheduled post-reconstitution check, because the
holdings feeds were still stale and this was the part that did not depend on
them.

## Rolling windows, on the book held through 18 September

| window | n | beta | corr | SPMO vol |
|---|---|---|---|---|
| full history (11 yr) | 2740 | **0.771** | 0.831 | 20.6% |
| trailing 3 years | 756 | 0.989 | 0.922 | 21.9% |
| trailing 12 months | 252 | 1.112 | 0.894 | 24.3% |
| **trailing 6 months** | 126 | **1.239** | 0.906 | **30.8%** |
| trailing 3 months | 63 | **1.291** | 0.900 | 34.3% |

Beta has not merely drifted toward 1.0 — it is **past it**, and volatility has
risen from 20.6% to 30.8%.

## By reconstitution cycle — the real picture

The index rebalances on the third Friday of March and September, so each cycle
is a distinct portfolio. Beta measured within each:

| cycle | beta | corr | | cycle | beta | corr |
|---|---|---|---|---|---|---|
| 2016-03 → 09 | **0.054** | 0.078 | | 2021-09 → 2022-03 | 0.733 | 0.875 |
| 2016-09 → 2017-03 | 0.045 | 0.073 | | 2022-03 → 09 | 0.610 | 0.883 |
| 2017-03 → 09 | 0.226 | 0.262 | | 2022-09 → 2023-03 | 0.404 | 0.644 |
| 2017-09 → 2018-03 | 0.751 | 0.775 | | 2023-03 → 09 | **0.166** | 0.234 |
| 2018-03 → 09 | 0.842 | 0.925 | | 2023-09 → 2024-03 | 0.890 | 0.906 |
| 2018-09 → 2019-03 | 0.960 | 0.965 | | 2024-03 → 09 | 1.008 | 0.974 |
| 2019-03 → 09 | 0.603 | 0.848 | | 2024-09 → 2025-03 | 0.822 | 0.907 |
| 2019-09 → 2020-03 | 0.965 | 0.951 | | 2025-03 → 09 | 0.983 | 0.977 |
| 2020-03 → 09 | 0.921 | 0.915 | | 2025-09 → 2026-03 | 0.855 | 0.907 |
| 2020-09 → 2021-03 | 0.889 | 0.965 | | **2026-03 → 09** | **1.255** | 0.908 |
| 2021-03 → 09 | 1.021 | 0.963 | | | | |

**Range 0.045 to 1.255, a spread of 1.21.** Cycle mean 0.715; pooled 11-year
beta 0.771. **The cycle just ended is the highest on record.**

In 2016 SPMO was genuinely uncorrelated to the Nasdaq (beta 0.05, corr 0.08).
By March–September 2026 it was a levered Nasdaq proxy (beta 1.26, corr 0.91).
Same fund, same methodology, opposite risk role.

## What this does to the core-leg conclusion

The 2026-09-21 test (`core_leg_spmo_vs_qqq.md`) found SPMO dominates QQQ inside
the design — +0.55 pp CAGR, +0.076 Sharpe, 6.9 pp shallower drawdown, at lower
beta. **That historical result stands.** What does not stand is the mechanism I
attached to it.

I wrote that the case "rests entirely on beta 0.773 and correlation 0.833 — it
works because it is not the Nasdaq." **That is true of the eleven-year average
and false of any particular six months.** SPMO's diversification against the
leveraged sleeve is not a standing property of the instrument; it is an
accident of whatever the momentum screen selected at the last reconstitution,
and it resets twice a year with no warning and no way to forecast it.

Practical consequences:

1. **The +0.076 Sharpe edge is an average over cycles where SPMO was sometimes
   a diversifier and sometimes a leveraged-Nasdaq clone.** It is not an edge you
   can count on in any given half-year.
2. **Entering this reconstitution the book was at its most dangerous
   configuration** — beta 1.26 against a satellite already holding 2× and 3×
   Nasdaq. The concentration concern raised on 21 Sep was, if anything,
   understated.
3. **The September reconstitution matters more than I said.** If it pulls beta
   from 1.26 back toward 0.85, that is a material improvement in the whole
   book's risk — but it is luck, not design, and the March 2027 reconstitution
   can undo it.

## What follows

- **Do not re-run or reverse the core-leg decision on this.** The historical
  evidence for SPMO over QQQ is unchanged, and one cycle's beta is not grounds
  to switch a core holding.
- **Do add beta as a monitored quantity.** The right cadence is per cycle, not
  per quarter: measure beta and correlation within each reconstitution window
  and log it. A cycle beta above ~1.1 means the core and satellite are the same
  bet and the book is carrying more Nasdaq exposure than the design intends.
- **The honest framing for STRATEGY.md:** SPMO is held because it beat QQQ over
  eleven years inside this design, not because it reliably diversifies. Those
  are different claims and only the first is supported.

Nothing applied. No account action. `state.py` unchanged.
