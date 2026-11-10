# High-volatility ideas, 2026-11-10 (owner) — the deep-E QQQ leg (APPLIED 2026-11-11) and two rejects

Live design (A 40/60, D ladder, D gate, vol target max10_30, VIXM sleeve), 2bp, real ETFs 2015-11..2026-11
and the proxy panel 2001-2026. Each idea moves part of the CASH leg into the tested instrument on its days.
Scripts ran from the session scratchpad (`MC.DATA` = a copy of `data/` extended with live closes by
`../vixm_followups_2026_11/ext_data2.py`); every log is the verbatim output.

| Idea | Files | Verdict |
|---|---|---|
| #1 short volatility after a spike (-1x short-term VIX futures; SVXY/SVIX checked) | `hv_test`, `hv_robust`, `sv_test` | Rejected. +1.4..+5.8 pts in-sample, but 52-65% from three spells (2020-22); one session of lag and the ex-2020/21 gain is ~0 or negative; bootstrap P(not better) 10-42%; a Feb-2018 repeat costs 9% of the book in a day at a 10% share |
| #3 inverse QQQ (PSQ/SQQQ) in F | `hv_test` | Rejected. Loses on real ETFs; small gain on the proxy with a deeper drawdown and lower Sharpe |
| #4 equity in E | `hv_test`, `hv_robust` | Plain QQQ in E: noise (as on 2026-09-19) |
| #4 deep E: QQQ 50% of the cash leg in E when QQQ <= -5% vs its 200-day | `hv_robust`, `de_test` | **Applied 2026-11-11** (owner: "50%"). Real 46.6% / 1.928 -> 50.4% / 2.021, max DD unchanged; proxy 30.5% / 1.314 / -24.3% -> 32.4% / 1.372 / -22.1%; placebos P 0.000; ex-2020 +1.75 / +1.13; ~54% of the real gain is 2020; E days 2-5% under the 200-day lose; one session of lag -> +1.5 real |

STRATEGY.md "Deep-E QQQ leg in the cash leg" is the decision record; `state.py` `DEEP_E_*` the code.
