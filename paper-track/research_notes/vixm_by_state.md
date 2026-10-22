# VIXM sleeve by state — 2026-10-22

Owner: "Break down the VIXM sleeve by state." Script `paper-track/vixm_by_state.py`, log
`vixm_by_state_run.log`. Live design as re-baselined on 2026-10-22, real ETFs
2015-11..2026-08. Contribution = daily return with the sleeve minus without it, credited
to the state that set the position. Research only.

Total: 47.7% vs 44.5% CAGR, +26.2% cumulative (~+2.2%/yr).

| state | days | VIXM days | avg cash leg | contribution | share | VIXM-day hit rate |
|---|---|---|---|---|---|---|
| E | 150 | 10 | 100% | **+7.8%** | 32% | 70% |
| A trimmed (held votes) | 680 | 40 | 77% | **+6.7%** | 28% | 55% |
| D gated (cash) | 91 | 22 | 100% | +3.9% | 16% | 55% |
| D1 | 183 | 22 | 14% | +3.8% | 16% | 55% |
| A (vol-scaled) | 1,168 | 98 | 5% | +2.4% | 10% | 45% |
| B / C | 174 | 38 | | +0.7% | 3% | |
| D2 | 99 | 19 | 16% | **−1.4%** | −6% | 32% |
| D3 / F | 174 | 0 | | 0 | 0 | — |

- **It earns where the book is in cash** — E, gated D and trimmed A: 76% of the gain. In
  plain A it is a small sleeve (5% average cash leg) and roughly breaks even per day.
- **F never holds VIXM**: by the time the book is in F, VIX is above VIX3M and the latch
  is off. The sleeve is a "calm-before-the-storm" position, not a crash trade.
- **D2 is the one state where it loses** (−1.4%, hit rate 32%): the sell-off is already
  underway and VIXM gives the spike back. Small (19 days), but consistent in sign.
- **Concentrated**: 25 spells, 16 won, but the best 5 (Mar 2025 +5.7%, Aug 2024 +5.1%,
  Feb 2023 +4.2%, Nov 2018 +3.6%, Mar 2018 +3.5%) are 91% of the gain; the other 20 net
  +2.1%. 2026's four spells: three lost (net −2.5%).
- No per-state change is warranted from this: dropping D2 would fit 2 spells / 19 days,
  and the 2026-10-08 study already found no per-state rule that survives both halves.
