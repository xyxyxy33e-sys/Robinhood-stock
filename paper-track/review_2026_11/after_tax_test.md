# After-tax test: taxable account vs IRA (review 2026-11)

Script: `after_tax_test.py` (the pre-registration is in its docstring). Output: `after_tax_test_run.log`. Real panel 2015-11-02 to 2026-11-10, price-only returns, FIFO lots, wash sales on same-ticker buys within ±30 days (the two QQQ legs count as one ticker), and taxes paid on 15 April by a pro-rata sale.

**Sanity check: PASS.** The IRA path matches `harness.run(real=True)`: the ending multiple is 111.699311 on both, the relative difference is -3.7e-15 and the largest daily difference is 4.4e-16.

## Results (liquidation basis, per $1 start)

| Case | Pre-tax CAGR | After-tax CAGR | End multiple | MaxDD | Taxes as % of pre-tax gain | ST share of gains | Wash sales (n / $) |
|---|---|---|---|---|---|---|---|
| IRA | 53.6% | 53.6% | 111.7 | -18.3% | 0 | – | – |
| S1 (38.8% / 18.8%), BOXX deferred | 53.6% | **35.8%** | 29.0 | -28.5% | 16.0% | 99.8% | 1309 / 43.1 |
| S1, BOXX taxed as ordinary income | 53.6% | 35.8% | 29.0 | -28.5% | 16.0% | 99.8% | 1727 / 43.6 |
| S1, BOXX tax-free | 53.6% | 36.1% | 29.7 | -28.5% | 15.7% | 99.8% | 750 / 43.4 |
| S2 (50.1% / 33.1%), BOXX deferred | 53.6% | **30.2%** | 18.2 | -34.6% | 15.6% | 99.8% | 1300 / 30.2 |
| S2, BOXX taxed as ordinary income | 53.6% | 30.2% | 18.2 | -34.6% | 15.5% | 99.8% | 1728 / 30.5 |
| QQQ buy-and-hold, S1 / S2 | 17.5% | 15.7% / 14.1% | 4.97 / 4.27 | -35.6% | – | 0 | – |
| SPMO buy-and-hold, S1 / S2 | 15.7% | 14.0% / 12.5% | 4.21 / 3.64 | -31.3% | – | 0 | – |

**How to read the table:**
- **Liability at the end:** the only tax still owed at the end is the 2026 tax on gains already realized: 0.95 in S1 and 0.76 in S2. The deferred liability on unrealized gains is about 0, because almost no position is held long enough to build up gains.
- **Taxes as % of pre-tax gain:** this figure looks low because it compares dollars, not compounding. Taxes paid come to 16.8 per $1 of starting capital, against 110.7 of IRA gains. The real cost is the compounding the paid tax gives up: the ending multiple falls by 74% in S1 and by 84% in S2.
- **Wash sales:** the disallowed losses are not lost. They are added to the basis of the replacement lots and recovered later. Switching the rule off adds only +0.2 pp of CAGR.

## Drivers (post-hoc diagnostics, S1)

1. **Almost every gain is short-term (99.8%).** The strategy fully exits SPMO 51 times, TQQQ 70 times, QLD 49 times and BOXX 51 times in 11 years, so lots rarely last more than a year. If every gain were taxed at the 18.8% LT rate, after-tax CAGR would be 45.2% instead of 35.8%.
2. **Paying tax every year breaks the compounding.** Take the same gains, all taxed as short-term, but paid once at the end: after-tax CAGR would be 46.9% (S1) or 44.3% (S2). Paying each April instead costs about 11 to 14 pp of CAGR, because roughly 35 to 50% of each year's gain leaves the account.
3. **The tax rate level (S1 to S2) costs another 5.6 pp.** BOXX treatment barely matters (±0.3 pp), and neither does the wash-sale rule (0.2 pp).

**Bottom line:** the strategy still beats buy-and-hold in a taxable account (30 to 36% vs 12.5 to 15.7%). But it keeps only 16 to 26% of the IRA's ending wealth, so the IRA is by far the better place for it. The tax payments on 15 April also deepen MaxDD from -18% to -28% (S1) and -35% (S2).

## Caveats

- Returns are price-only: no dividends or distributions are taxed, and XLU (which is never held) keeps its modelled dividend inside its return.
- VIXM is a commodity pool. In reality it issues a K-1 and its gains are taxed 60/40 under Section 1256, marked to market each year. That is not modelled here.
- There is no state exemption for T-bill income and no $3k ordinary-income offset.
- The end liability treats all unrealized gains as long-term, as pre-registered. In the "BOXX taxed as ordinary income" runs the deferred figure is slightly negative (-0.01), because trading costs leave small unrealized losses on the BOXX lots.
