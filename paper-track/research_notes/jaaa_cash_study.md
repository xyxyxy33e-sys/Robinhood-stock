# JAAA (AAA CLO ETF) as the cash leg (2026-10-30)

**Setup.** Prompted by alphaAI apparently holding JAAA as cash. Research only. Script `jaaa_cash_study.py` (pre-registered); output `jaaa_cash_study_run.log`. Live design incl. the zone buffer, VIXM out, only the cash leg changed.

| cash leg | 2020-11..2026-10 | 2023-01..2026-10 |
|---|---|---|
| T-bill (engine) | 42.5% / 1.746 / −18.4% | 47.6% / 1.756 / −18.4% |
| BOXX | — | 47.5% / 1.752 / −18.4% |
| JAAA | 42.7% / 1.750 / −18.8% | 48.5% / 1.781 / −18.8% |

**Verdict: passes the pre-registered rule, narrowly.**
- JAAA vs BOXX: +1.1 pp CAGR, +0.03 Sharpe, 0.35 pp deeper max drawdown.
- JAAA vs T-bills since 2020: +0.2 pp CAGR.

**Recommendation: do not switch (owner decision).** Three things the rule did not measure all point the same way.
1. **It loses when the book is defensive.** On the 190 E/F days since 2020 (book mostly cash), JAAA summed −2.4% against +1.9% for T-bills.
   - 2022 calendar year: JAAA +0.5% vs T-bills +2.1%.
   - Worst day 10 Apr 2025, −1.03%. Max drawdown −2.6%. BOXX's worst ever was −0.12%.
   - The whole edge is 2023–2026 credit carry.
2. **Untested tail.** JAAA launched Oct 2020, so it has never been through a credit crisis. AAA CLO tranches marked down sharply in 2008, and the design is in cash precisely during crashes.
3. **Taxes, in a taxable account.** JAAA pays monthly distributions taxed as ordinary income. BOXX's return is price appreciation (capital gains, deferred until sold).
   - At a 35% marginal rate, JAAA's 2025 return of +5.2% is about +3.4% after tax, against BOXX's +4.4% pre-tax and deferred.
