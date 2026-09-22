# Is 50/50 core/TQQQ the right A row? — 2026-09-22. **KEEP 50/50 (no change).**

Owner: *"So based on these data, is 50/50 the right ratio? Consider drift decay
everything."* Script `paper-track/a_ratio_study.py`, log `a_ratio_study_run.log`
(36 s). Harness = `drawdown_study.sim`, asserted to reproduce live (real 37.30%
/ −18.6%, proxy 25.46% / −27.0%). Sharpe is **excess of BOXX** throughout.
Only the A row moves; the trim, vol target, band, gate and every other state are
unchanged. Proxy core = QQQ, proxy TQQQ = synthetic 3×; real core = SPMO.

## 1. The ratio is a leverage dial on a flat Sharpe ridge

| core/TQQQ | real CAGR | real MaxDD | real exSh | proxy CAGR | proxy MaxDD | proxy exSh (S / H) |
|---|---|---|---|---|---|---|
| 80/20 | 30.03% | −15.0% | 1.375 | 20.89% | −25.1% | 0.984 (1.302 / 0.745) |
| 70/30 | 32.50% | −15.9% | **1.388** | 22.42% | −25.7% | 0.989 (1.307 / 0.750) |
| 60/40 | 34.90% | −16.8% | 1.386 | 23.95% | −26.3% | **0.991** (1.307 / 0.754) |
| **50/50 live** | **37.29%** | **−18.6%** | **1.376** | **25.46%** | **−27.0%** | **0.990** (1.305 / 0.754) |
| 40/60 | 39.63% | −20.8% | 1.360 | 26.93% | −28.8% | 0.988 (1.297 / 0.755) |
| 30/70 | 41.94% | −23.0% | 1.342 | 28.35% | −31.3% | 0.983 (1.289 / 0.753) |
| 20/80 | 44.21% | −25.1% | 1.323 | 29.77% | −33.8% | 0.979 (1.283 / 0.751) |

QQQ buy-and-hold on the same dates: real 18.51% / −35.6% / exSh 0.772; proxy
8.07% / −80.5% / 0.356. **Every ratio from 80/20 to 20/80 beats QQQ by a wide
margin; the ratio decides how much, and at what drawdown.**

- **Each +10 pp of TQQQ buys +2.4 pp CAGR (real) / +1.5 pp (proxy), almost
  linearly** — 2.47 → 2.27 real, 1.53 → 1.41 proxy across the whole range. Decay
  makes the curve concave, but only just (§2 explains why).
- **Excess Sharpe is flat across 70/30–40/60**: real spread 0.028, proxy 0.003.
  Real peaks at 65/35–70/30 (+0.012), proxy at 55/45–60/40 (+0.001).
- **Bootstrap (paired, 60-day blocks, 2000 draws): no ratio's Sharpe difference
  is distinguishable from live.** Real 60/40 +0.010 [−0.029, +0.048]; real 70/30
  +0.012 [−0.074, +0.096]; real 40/60 −0.016 [−0.047, +0.016]; proxy all within
  ±0.035. The **return** differences ARE significant (real 40/60 +1.69 pp/yr
  [+0.11, +3.24]; 60/40 −1.76 [−3.30, −0.17]) — i.e. the dial reliably moves
  return and risk together, and does not reliably move the ratio between them.
- **Against the flat-leverage null** (the live book scaled to the same CAGR),
  **only 55/45–45/55 stay within ±0.55 pp on both eras.** Real: 60/40 +0.36,
  55/45 +0.45, 45/55 −0.50, 40/60 −1.01, 30/70 −1.97. Proxy: 60/40 −1.12, 70/30
  −2.21, 45/55 +0.07, 40/60 +0.02, 30/70 −0.60. Each era punishes a different
  side, so 50/50 is the one ratio that is never worse than plain scaling.

## 2. Decay — measured properly, and why it barely bends the curve

Decay = TQQQ's log return minus 3 × QQQ's log return (the whole cost of getting
3× through a daily-reset fund: variance drag **and** fees/financing).

| where | QQQ vol | realized drag | variance term alone 3σ² |
|---|---|---|---|
| real, state A days (1854) | 16.3% | **−12.1%/yr** | −7.9% |
| real, all other days (871) | 31.3% | −37.2%/yr | −29.4% |
| real, every day | 22.2% | −20.1%/yr | −14.8% |
| proxy, state A days (3909) | 17.1% | −12.2%/yr | −8.8% |
| proxy, all other days (2666) | 34.5% | −39.6%/yr | −35.8% |

Decay is proportional to σ², and **the design only holds TQQQ in the low-vol
regime** — A days run QQQ at ~16% vol against 31–35% elsewhere, so the drag
TQQQ actually pays is a third of what an all-weather holder pays. That is why
the dial above is so nearly linear.

What it costs the whole strategy (held TQQQ weight × daily drag, A days):

| row | 70/30 | 60/40 | **50/50** | 40/60 | 30/70 |
|---|---|---|---|---|---|
| real, %/yr | −1.73 | −2.30 | **−2.88** | −3.45 | −4.03 |
| proxy, %/yr | −1.52 | −2.02 | **−2.53** | −3.03 | −3.53 |

Each +10 pp of TQQQ costs ~0.55 pp/yr of decay and buys ~2.4 pp (real) /
~1.5 pp (proxy) of gross return: **the decay is real and it is paid, but the
exposure it buys is worth ~3–4× what it costs in state A.**

## 3. Drift — a non-issue for the choice of ratio

Inside A the held TQQQ share (of the risky book) averages target +0.4 pp at
every ratio, with p10–p90 ≈ −0.9 / +1.6 pp. The band fires 8.1–8.5×/yr (real)
and 9.5–9.9×/yr (proxy) regardless of ratio. The 5% band keeps every ratio
within ~1.5 pp of its target; drift does not favour one ratio over another.
(Today's 52.27% TQQQ share is past p90 — the tail, not the norm.)

## 4. Beta-matched alternatives: can QLD hold the same exposure with less decay?

Nominal beta 2.0 = core + 3·TQQQ + 2·QLD ⇒ the family SPMO = TQQQ = c,
QLD = 1 − 2c. Decay load 2 + 2c units of σ²/2: c = 0.5 (live) carries 3.0,
100% QLD carries 2.0.

| SPMO/TQQQ/QLD | real CAGR | real MaxDD | real exSh | measured β on A | bp/day on A |
|---|---|---|---|---|---|
| **50/50/0 live** | **37.29%** | **−18.6%** | **1.376** | **1.85** | 15.6 |
| 33/33/33 | 37.46% | −19.4% | 1.365 | 1.90 | 15.6 |
| 25/25/50 | 37.56% | −19.8% | 1.359 | 1.92 | 15.7 |
| 0/0/100 | 37.59% | −21.0% | 1.332 | 1.99 | 15.7 |

**No.** Swapping toward QLD saves decay but raises the book's measured beta
(SPMO's beta to QQQ is below 1, so the live row carries 1.85, not 2.0) and adds
back almost exactly the return the decay saving was worth. Result: same return
(+0.3 pp at most), 2.4 pp deeper MaxDD, Sharpe −0.044 for 100% QLD (bootstrap
[−0.114, +0.022]). **Per unit of beta, the live row earns the most.** Proxy
(core = QQQ, all legs synthetic from QQQ) cannot separate the vehicles: every
row lands within ±0.002 Sharpe.

## Verdict

**50/50 is on the ridge and there is no evidence-based reason to move it.**
The ratio is a risk-appetite dial, not an efficiency setting:

- Wanting **more Sharpe**: 60/40 (+0.010 real, +0.001 proxy) — not distinguishable
  from live, costs −2.4 pp CAGR real.
- Wanting **more return** (the owner's "outperform SPY and QQQ"): 40/60 gives
  +2.3 pp real / +1.5 pp proxy for −2.2 / −1.8 pp MaxDD at Sharpe −0.016 /
  −0.002 — a legitimate choice, but it is just more leverage, and on real its
  drawdown is already 1.0 pp worse than simply levering 50/50 to the same CAGR.
- 60/40's Sharpe edge on real comes with a proxy drawdown 1.1 pp worse than
  scaling; 50/50 is the only ratio neutral on both eras.
- **Decay does not argue for a different ratio**: in the low-vol A regime it
  costs ~0.55 pp/yr per 10 pp TQQQ against ~1.5–2.4 pp of return bought.
- **Drift does not argue for a different ratio**: the band holds every ratio
  within ~1.5 pp of target, firing ~8×/yr regardless.
- **QLD does not beat TQQQ+SPMO at matched beta** in state A.

Design is frozen to 7 December regardless. NOTHING APPLIED.

## Correction to `leverage_decay_dq.md` (2026-09-21) found during this study

That note reported TQQQ's decay as −7.21%/yr and QLD's as −3.27%/yr, and said
realized decay "runs about half the naive formula". **Wrong.** It compared each
fund to a frictionless daily-reset L× fund, which is *itself* fully decayed, so
the figure was fees + financing only (in CAGR terms). Split properly (log
returns, 2015-10 → 2026-09):

| fund | carry (fees + financing) | variance decay | **total vs L × QQQ** | naive L(L−1)σ²/2 |
|---|---|---|---|---|
| TQQQ | −5.02%/yr | −14.99%/yr | **−20.01%/yr** | 14.73%/yr |
| QLD | −2.43%/yr | −4.96%/yr | **−7.39%/yr** | 4.91%/yr |

Variance decay matches theory almost exactly. The note's **conclusion stands and
is strengthened**: per unit of beta TQQQ costs 6.67%/yr vs QLD 3.70%/yr, so the
withdrawn D-row TQQQ candidate stays withdrawn. (Its §2 whole-era table, which
compared actual rows head to head, is unaffected.)

## 5. Follow-up: 40/60 vs 50/50 in the 2022 bear (owner, same day)

Script `paper-track/a_ratio_bear2022.py`, log `a_ratio_bear2022_run.log`.

| window | real 50/50 | real 40/60 | proxy 50/50 | proxy 40/60 | QQQ |
|---|---|---|---|---|---|
| calendar 2022 | −10.30% (DD −12.0%) | −11.97% (−13.0%) | −18.40% (−18.5%) | −19.45% (−19.6%) | −34.16% |
| QQQ peak→trough 19 Nov 21 – 28 Dec 22 | −17.30% (−18.2%) | −19.56% (−20.4%) | −24.72% (−24.8%) | −26.35% (−26.4%) | −34.05% |
| Nov 2021 – Dec 2023, bear + recovery | +37.18% | **+42.23%** | +42.58% | **+46.13%** | +3.91% |

- The design spent **236 of 251 days of 2022 outside A** (F 142, C 57, E 27,
  gated D 10), so the ratio touched only **15 days** of the year. 40/60 cost
  1.7 pp real / 1.0 pp proxy in calendar 2022 and 2.3 / 1.6 pp peak to trough.
- The loss is concentrated in **false A stretches**: 22 Dec 21 – 4 Jan 22
  (−0.70 pp for 40/60) and the August 2022 bear-market rally, 3–19 Aug
  (−0.74 pp). These are exactly the days extra TQQQ hurts.
- The 2021-11 → 2023-01 episode is the real harness's worst drawdown on record:
  **−18.6% at 50/50 vs −20.8% at 40/60.**
- Through the recovery, 40/60 ends **+5.0 pp real / +3.6 pp proxy ahead** by
  end-2023, because the 2023 rebound was spent mostly in A.

Same answer as §1 in miniature: 40/60 is more leverage, paid for with about
2 pp more drawdown in the worst bear on the real record and repaid in the
recovery. No change.
