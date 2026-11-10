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

## Follow-ups, 2026-11-10 (on top of the design with deep-E)

| Batch | Files | Verdict |
|---|---|---|
| Short volatility, six more variants (post-spike, steep curve, calm carry, short VIXM, after a VIXM exit, uptrend filter) | `sv2_test` | Rejected: none survives one session of lag + 2020-21 removed + the bootstrap together; steep-curve and calm-carry lose in every cell |
| Buy the panic, six more families (deep F, deep gated D, 5-day oversold, VIX level / turn / backwardation, 252-day drawdown, deep-E refinements) | `bp_test` | Only the VIX-spike entries add on both panels. **Applied: QQQ 25% of the cash leg while VIX latch >= 30 / < 25** (owner, 2026-11-11). The rest add nothing robust or lose on the proxy |

## State-by-state follow-ups, 2026-11-10 (on the 11 Nov design with deep-E and VIX-panic)

| Test | Files | Verdict |
|---|---|---|
| Staged re-entry after the D gate lifts (QLD/QQQ/half/lower vol target for N sessions) | `gx_test` | No change: only 2 real / 5 proxy lifts went straight to D3; fixed-N staging costs return; the vol-window "gain" is one day (2024-08-06) |
| State C row (QQQ, QLD/TQQQ slices, half cash, depth and vol splits) | `cx_test` | No change: vol-scaled SPMO already captures C; more leverage lowers Sharpe, less loses return; the near-misses help the proxy only at one threshold |
| State B row (SPMO, cash, QLD, 50/50 TQQQ, spread and age splits) | `bx_test` | **Applied 2026-11-11: B -> 50% SPMO / 50% cash** (owner). Monotone toward cash on both panels; real 52.7% / 2.039 -> 53.2% / 2.054, proxy 33.8% / 1.384 / -23.6% -> 34.4% / 1.412 / -22.1%; thin (3 real spells) |
| State-specific vol targets (A higher, D lower, 60-day in A, A cap) | `vt_test` | No change: every variant is just more or less leverage; the exposure-matched single target is as good or better |
| Yearly bars for the dashboard (11 Nov design, corrected VIXM file) | `bars1110` | 52.7% / 2.04 / -18.3%; 2022 -3.3%, 2023 +82.5%, 2024 +81.0%, 2025 +32.9%, 2026 to 5 Nov +22.1% |
