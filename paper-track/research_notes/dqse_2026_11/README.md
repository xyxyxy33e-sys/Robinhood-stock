# DQSE (FT Vest Nasdaq-100 Dual Directional Buffer ETF, September) — does it fit the strategy? (2026-11-19)

Not adopted. Synthetic DQSE (`syn.py`): each September a one-year QQQ payoff — gain to the cap above the start,
|loss| as a gain down to -9.99%, a 9.96% buffer below that — priced daily with a flat vol of 1.0x VIX, the cap
scaled 1.9x from the flat-vol fair cap (matches the Sep-2026 18.75%), 0.6% QQQ dividend yield forgone, 0.90% fee.
Mid-period model prices are within ~1.5% of DQSE's actual closes on 6 Oct, 5 Nov and 18 Nov 2026.
`test.py` puts it in the current design (2.0x cap, vol sleeve off on every arm), +13bp one-way extra on its trades.

| Slot | Real 2015-26 | Proxy 2001-26 | Holdout 2001-Oct 2015 |
|---|---|---|---|
| base (BOXX, QQQ legs) | 45.2% / 1.93 / -19.3% | 31.8% / 1.41 / -22.1% | 22.4% / 1.07 |
| DQSE as the whole cash leg in E/F | 43.8% / 1.69 / -27.5% | 26.5% / 1.05 / -59.0% | 14.8% / 0.66 |
| DQSE in the deep-E QQQ slot | 44.8% / 1.93 / -20.3% | 31.3% / 1.40 / -22.1% | 21.9% / 1.05 |
| DQSE as every cash leg | 36.9% / 1.33 / -32.5% | 23.5% / 0.88 / -63.4% | 14.3% / 0.60 |

Why: the strategy holds a slot for days to weeks, never to the September outcome date, so it only ever gets the
fund's mid-period behaviour: a 0.67-0.74 beta to QQQ with fees, spread and no dividends. In E/F that is QQQ
exposure in exactly the states the design keeps in cash (2008: -59% proxy drawdown). In the deep-E slot it is a
weaker QQQ. Liquidity (~$130k/day, $25M fund) also cannot carry a $300k cash leg.
