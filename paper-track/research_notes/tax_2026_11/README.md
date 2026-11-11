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
