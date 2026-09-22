# Decay: 70% TQQQ vs 100% QLD in state D — 2026-09-21. **Candidate WITHDRAWN.**

Owner asked the right question about the `sharpe_study` candidate (D held as
70% TQQQ / 30% BOXX instead of 100% QLD): *what about the decay?* Measuring it
kills the candidate, and exposes a control I failed to apply.

## 1. The decay is real and it is large

> **CORRECTION 2026-09-22 (`a_ratio_study.md`):** the table below understates
> decay. Its "ideal" is a frictionless daily-reset L× fund, which is itself fully
> decayed, so the "realized drag" column is fees + financing only. Against L × QQQ
> the total is **TQQQ −20.01%/yr** (carry −5.02, variance −14.99) and **QLD
> −7.39%/yr** (carry −2.43, variance −4.96); variance decay matches the naive
> formula, it does not run at half. Per unit of beta: TQQQ 6.67%/yr, QLD 3.70%/yr.
> The conclusion below is unchanged and stronger.

Realized on actual fund prices, 2015-10 → 2026-09 (2748 sessions, QQQ
annualised vol 22.16%), against the L × QQQ daily-compounded ideal:

| fund | realized ann. log return | L × QQQ ideal | **realized drag** | naive theory L(L−1)σ²/2 |
|---|---|---|---|---|
| TQQQ (L=3) | +40.04% | +47.25% | **−7.21%/yr** | 14.73%/yr |
| QLD (L=2) | +32.84% | +36.11% | **−3.27%/yr** | 4.91%/yr |

Realized drag runs about half the naive formula — QQQ's returns trend rather
than being i.i.d. — but the *ordering* is exactly as theory says. **Per unit of
beta: TQQQ costs 2.40%/yr, QLD 1.64%/yr. The 3× route is ~0.77%/yr more
expensive for the same exposure.**

Decay needs holding period to bite, and it gets it: real state-D episodes have
a **median length of 8 sessions** (mean 8.9, max 31), and **96% of D days sit
in episodes longer than 3 sessions**. This is not a day trade.

## 2. I never beta-matched the candidate

**0.70 × 3 = 2.10, not 2.00.** The tested row carried 5% more beta than the
100% QLD row it was compared against. That is the exposure-matched control
this project applies to everything — and I did not apply it here, because the
drawdown-frontier check scored the variant +0.00 and I read that as "neutral"
rather than "go check the beta."

Whole era, daily rebalanced to constant weights, BOXX carry included:

| row | beta | ann. log return | ann. vol |
|---|---|---|---|
| **100% QLD** | **2.00** | **+32.84%** | 44.27% |
| 66.7% TQQQ / 33.3% BOXX | 2.00 | +31.45% | 43.72% |
| 70% TQQQ / 30% BOXX (as tested) | **2.10** | +32.58% | 45.91% |

**Beta-matched, QLD wins by 1.39%/yr.** The as-tested row only closes the gap
by carrying more leverage, and still does not pass QLD.

And on the 291 ungated real D days themselves, constant weight:

| D row | beta | bp/day | ann. vol |
|---|---|---|---|
| **100% QLD** | 2.00 | **+52.5** | 44.1% |
| 66.7% TQQQ / 33.3% BOXX | 2.00 | +51.9 | 43.9% |
| 70% TQQQ / 30% BOXX | 2.10 | +54.5 | 46.1% |

**Beta-matched on the days it actually applies, QLD wins.** Decay (−1.5%/yr at
this beta) slightly exceeds the extra BOXX carry (+0.77%/yr).

## 3. What was left is 48 observations

Beta-matching costs about a quarter of the harness gain (real Sharpe +0.014 →
+0.011). The residual is not the vehicle. Attributing the beta-matched arm's
total advantage over the whole real era by bucket:

| bucket | n | cumulative | per day |
|---|---|---|---|
| ungated D days | 291 | +0.68 pp | +0.234 bp |
| **first day AFTER a D episode** | **48** | **+1.54 pp** | **+3.204 bp** |
| all other sessions | 2386 | **+0.00 pp** | 0.000 bp |

**69% of the entire edge is 48 sessions** — the handoff day when the book
leaves state D carrying TQQQ + BOXX rather than QLD. That is a transition
artifact on 48 observations, not a property of the instrument. The D days
themselves contribute +0.68 pp over eleven years.

Forcing a daily rebalance (band = 0) leaves +0.008 of the +0.011, so drift
between rebalances is only about a quarter of the residual; the rest is the
handoff.

## Conclusion

**Withdrawn. QLD is the right vehicle for state D.** The decay difference is
real, measurable and adverse (≈0.77%/yr per unit of beta); beta-matched, QLD
beats the TQQQ sleeve both over the whole era and on the D days specifically;
and the harness gain that survived beta-matching is concentrated in 48
handoff sessions with nothing anywhere else.

This also corrects the 2026-09-20 `sharpe_study` write-up, which called this
"the strongest thing this line has produced" and flagged that it had no clean
mechanism. The mechanism was a missing exposure control plus a 48-day
artifact. **An edge with no mechanism was the right thing to be suspicious of,
and the suspicion should have been converted into this test before the
candidate was written up as strong.**

What survives from that study is unchanged and more important: switching off
the volatility target looks good in every era searched and is catastrophic in
the holdout (−0.111, MaxDD −27.0% → −51.3%). Keep the vol target.

Nothing applied; `state.py` unchanged. State D remains 100% QLD, gated to
100% BOXX.
