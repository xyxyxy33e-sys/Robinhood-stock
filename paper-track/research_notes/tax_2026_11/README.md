# Tax research, November 2026 (research only; not tax advice)

Owner, 2026-11-11: the Agentic account is taxable and is offset by tax-loss harvesting in other
accounts. Two questions: do wash-sale-aware substitutes help, and how much capital gain will the
account realize in 2027? Code and full log here (`wash.py` lot simulator, `run_all.py`, `fc.py`
forecast, `live.py` live reconstruction, `wash.log`). Design: live rules incl. the D gate on the
day's high (L1), 2bp, $600k book, price-only. Tax: 50.3% ST / 37.1% LT, paid each 15 April,
netting, $3k ordinary offset, carryforward. VIXY/VIXM special tax treatment not modelled.
Whether TQQQ/QLD/QQQ are "substantially identical" is unresolved (tested both ways).

## Wash-sale substitutes: rejected
Real 2015-11..2026-11, FIFO: BASE pre-tax 52.9% / 2.136 / -16.6%, after-tax 29.7%.
S1 (exposure-matched swap: TQQQ<->QLD, SPMO->QQQ, VIXY->VIXM) 51.8% / 29.0% after tax;
S2 (QQQ for the leveraged legs) 48.8% / 27.3%; S3 (S1 + QQQ fallback) 51.8% / 29.0%.
Turning the wash rule off entirely lifts BASE only to 29.9%: wash sales are a deferral worth ~0.2pp,
and every substitute costs more in tracking error than it saves.

## 2027 capital-gain forecast ($608k book, no deposits, pre-tax)
Each historical year replayed from today-like lots.
Real panel 2016-2025: net short-term gain p10 $143k / p25 $252k / median $315k / p75 $492k /
p90 $556k; long-term ~$0; no year with a net loss (worst 2022, +$4k).
Proxy 2002-2025 (no VIX sleeve): total p10 $5k / median $174k / p90 $496k; net loss in 12% of years.
Gains are almost all short-term (positions rarely live a year); by quarter roughly evenly spread
(Q4 slightly heaviest). A deferred wash loss carried in the TQQQ basis lowers 2027 dollar for dollar
when released. Path-dependent: a range, not a point estimate.

## December-only substitutes: rejected (2026-11-11)
Substitutes only for re-buys in Dec (D1), 1 Dec-30 Jan (D2), or D2 for losses over $5k (D3).
After tax: BASE 29.7%, D1 29.9% (noise; its 2 Jan switch-back can push a loss across the year,
$567k in 2025), D2 29.4%, D3 29.4%. BASE strands a loss across a year boundary in 4 of 11
year-ends (median $0, max $62k in 2022). Replaced by a report-only December wash check in the
weekly report (RUNBOOK 2.4). Log: `wash_dec.log`.

## 2027 forecast, revised (NYC rates, K-1 treatment)
Not tax advice; research only. Code `fc2.py`, full log `fc2.log` (per-year tables, all four start-lot variants, proxy panel).
Same method, panels, "today" lots and $608,122 book as `fc.py` (reproduced: real, plain variant, total p10/p25/median/p75/p90 =
$142,865 / $252,441 / $314,561 / $492,187 / $555,504; the "today" variant is $135,235 / $245,660 / $306,453 / $489,683 / $558,068,
and the old README headline is the plain one). `fc2.py` only logs each realized-gain increment by symbol group (VIXY+VIXM vs the rest)
and ST/LT; the group sums were asserted equal to the simulator's own yearly ST/LT.

**Rates (approximate, from memory of 2025-26 law; check them).** NY State and NYC tax capital gains as ordinary income. No SALT limit,
no AMT modelled. "NYC top": 40.8% + 10.9% + 3.876% = ST 55.576%, 23.8% + 10.9% + 3.876% = LT 38.576%.
"NYC upper-middle": 38.8% + 6.85% + 3.876% = ST 49.526%, 18.8% + 6.85% + 3.876% = LT 29.526%.
Per-dollar so you can plug in your own bracket: tax = rate_ST x net ST + rate_LT x net LT. Each $1 of VIXY/VIXM gain moved from ST to the
60/40 split saves 0.6 x (ST rate - LT rate) = 10.2 cents (top) / 12.0 cents (upper-middle). Net loss: $3k offsets ordinary income
(valued here at the ST rate), the rest carries forward with its character. (The old 50.3% / 37.1% was California.)

**K-1 treatment (a simplification).** VIXY and VIXM are partnerships; futures gains are marked to market and pass through as 60% LT /
40% ST regardless of holding period, plus a little ordinary interest (ignored). Any residual gain/loss on the share sale keeps its own
holding-period character (short-term here). The model treats each year's whole realized gain/loss on VIXY+VIXM lots as 60% LT / 40% ST. The true
split depends on the K-1 monthly allocations and the share-sale residual, which cannot be modelled from prices. Netting: ST and LT
separately, then cross-netted. Everything else keeps the simulator's holding-period character (all short-term).

### Forecast for 2027, real panel 2016-2025 (n=10), "today" lots (plain variant in brackets), pre-tax $
| | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|
| OLD (all short-term): net ST = total | 135,235 (142,865) | 245,660 (252,441) | 306,453 (314,561) | 489,683 (492,187) | 558,068 (555,504) |
| OLD tax, NYC top | 75,158 (79,399) | 136,528 (140,296) | 170,314 (174,821) | 272,146 (273,538) | 310,152 (308,727) |
| OLD tax, NYC upper-middle | 66,977 (70,755) | 121,666 (125,024) | 151,774 (155,790) | 242,520 (243,761) | 276,389 (275,119) |
| K-1: net ST | 134,996 (142,497) | 229,624 (229,676) | 284,404 (296,485) | 471,580 (470,830) | 554,749 (552,482) |
| K-1: net LT | 0 (0) | 0 (0) | 3,023 (1,838) | 24,404 (27,684) | 35,793 (33,453) |
| K-1: total (same as old) | 135,235 | 245,660 | 306,453 | 489,683 | 558,068 |
| K-1 tax, NYC top | 75,118 (79,336) | 135,306 (136,426) | 169,485 (174,821) | 267,609 (268,371) | 309,588 (308,213) |
| K-1 tax, NYC upper-middle | 66,929 (70,682) | 119,610 (120,471) | 149,598 (155,790) | 237,783 (237,682) | 275,725 (274,515) |

Total gain is unchanged by the K-1 view; only character moves. For comparison, the old median at California 50.3% was about $154k.
Proxy 2002-2025 (24 yrs): no VIXY/VIXM sleeve (the VIXY lot in the "today" start is a flat $-24 artefact per year), so the K-1 view changes nothing;
total p10 $2,465 / p25 $84,164 / median $180,056 / p75 $265,351 / p90 $502,191; tax NYC top median $100,068, NYC upper-middle $89,175.

**Sleeve share (real panel).** Realized gain on VIXY+VIXM lots: median year $17,938 vs median total $306,453 = 5.9% (today variant; plain 5.3%);
summed over the 10 years 7.2% (plain 7.5%). It is lumpy: positive in 6 of 10 years (2018 +$98.7k, 2022 +$51.4k, 2024 +$55.3k), negative
in 2016, 2017, 2019, 2021. In the two median-ranked years it is -$6k and +$6k, which is why the K-1 view saves almost nothing at the median.

**Tax saved by the K-1 view (old tax minus K-1 tax, today variant).** Difference of the percentile tax levels: NYC top median $830, p90 $564;
upper-middle median $2,176, p90 $664. Per-year savings: NYC top median $514, p90 $6,085, mean $2,430; upper-middle median $605, p90 $7,159, mean $2,858
(plain variant: median $0 / p90 $514 top, $0 / $604 upper-middle at the percentile level). So: small at the median, a few thousand to about $7k in years the sleeve
has a big gain, and nothing in years it loses (a VIXY loss is then also split 60/40, so a ST-offset loss becomes partly LT, which can cost a little).

**2026 actuals to date** (Robinhood realized, before wash-sale adjustments; non-VIX symbols assumed short-term):
| view | pre-net ST | pre-net LT | netted ST | netted LT | net | $3k offset | carryforward |
|---|---|---|---|---|---|---|---|
| all short-term | -8,943.51 | 0.00 | -8,943.51 | 0.00 | -8,943.51 | 3,000.00 | ST -5,943.51 |
| K-1 (VIXM+VIXY 60/40) | -45,425.93 | +36,482.42 | -8,943.51 | 0.00 | -8,943.51 | 3,000.00 | ST -5,943.51 |

Inputs: VIXM +29,295.67, VIXY +31,508.36 (sum 60,804.03 -> LT 36,482.42 / ST 24,321.61), others -69,747.54. The ST loss absorbs the LT gain, so the net
and its character (short-term loss) are the same either way. The VIXM gain was realized across several 2026 spells, so the 60/40 view is approximate.

**Simplifications.** K-1 split modelled as 60/40 of total realized gain/loss per year; interest ignored; share-sale residual and monthly
allocation ignored; wash-sale-deferred amounts follow the sold symbol's group in the year of the sale; rates from memory; no SALT cap, AMT or
state-specific rules; $3k offset valued at the ST rate; each replay year independent (no carryforward in); 10 real years is a small sample.
