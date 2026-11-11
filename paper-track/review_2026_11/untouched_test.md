# Untouched-data test of the 11 Nov live design (one shot, 2026-11-11)

Script: `untouched_test.py`. The pre-registration is in its docstring, written before the run and not edited
after it. Output: `untouched_test_run.log`, verbatim. It ran once with nothing tuned. Before the run, a
mechanical check showed `weights()` reproduces `harness.weights` exactly on the proxy panel (max |dW| = 0,
legs equal, regime keys equal). No performance figure was looked at during that check.

**Frozen design.** harness.CUR (A 40/60 + trim v2, B 50/50, C core, D ladder + D gate + 0.5% zone buffer,
E/F cash, max(10,30)d vol target 20%, 5% band, 2bp). It includes deep-E (on in every set) and VIX-panic (on
for the US sets from 1990-01-02; off before 1990 and off for the non-US sets). VIXM is off. The breadth half
of the D gate is inert on every set, because no EW series exists before 1999 and none exists for the
non-US indices. "Bare" means trim, gate, ladder, fast overlay, deep-E and panic all switched off.

## Results (excess-of-cash Sharpe unless noted)

| Set (scored window) | B&H CAGR / exSh / MaxDD | CUR lag0 CAGR / exSh / MaxDD | CUR lag1 exSh / MaxDD | Bare lag0 / lag1 exSh |
|---|---|---|---|---|
| (a) NDX 1987-06..2000-12 | 21.2% / 0.634 / -52.8% | 15.5% / 0.487 / -34.7% | 0.457 / -55.4% | 0.518 / 0.438 |
| (c) crude Mkt+0.5UMD core, NDX signals | 20.9% / 0.834 / -37.4% (NDX 0.634) | 15.6% / 0.505 / -35.1% | 0.478 / -55.8% | 0.488 / 0.421 |
| (b) Nikkei 1971-09..2026-10 | 6.3% / 0.180 / -81.9% | 3.8% / 0.065 / -65.9% | 0.063 / -61.5% | 0.176 / 0.184 |
| (b) DAX (TR) 1989-09..2026-10 | 7.7% / 0.320 / -72.7% | 6.1% / 0.250 / -51.9% | 0.227 / -54.1% | 0.389 / 0.408 |
| (b) FTSE 1985-08..2026-10 | 5.2% / 0.191 / -52.6% | -1.0% / -0.111 / -94.0% | -0.085 / -92.1% | -0.091 / -0.079 |

Worst calendar years for CUR at lag 0 vs B&H: NDX 1997 -16.9% vs 2000 -36.5%. Nikkei 2016 -29.3% vs 2008 -42.1%.
DAX 2011 -25.5% vs 2002 -43.9%. FTSE 2000 -37.5% vs 2008 -31.3%. On NDX at lag 1, CUR's worst year is
1987 at -42.2%, because the classifier was in A on 19 Oct 1987 and one session of lag kept the 3x leg through the
second leg down. Time in state for CUR on NDX: A 63%, B 1%, C 7%, D 18%, E 5%, F 6%. D was gated on 3.1% of
days, deep-E was on 1.6% and panic 7.2%. The other sets are similar, with A at 51-58%. Full figures, including
plain Sharpe and rebalances per year, are in the log.

## Interpretation

- **The design does not beat holding the index on risk-adjusted terms on any untouched set**, at lag 0 or lag 1.
  This fails the pre-registered criterion five out of five. Its excess Sharpe is 0.07-0.18 below buy-and-hold on
  NDX, DAX and Nikkei, and 0.30 below on FTSE. On the momentum-core set it is 0.33 below buy-and-hold of that
  core.
- **Relative to in-sample**, out-of-sample excess Sharpe is 0.49 on NDX, about 25% of the 1.96 measured on real
  ETFs 2015-2026. It is 0.25 on DAX (13%), 0.07 on Nikkei (3%) and negative on FTSE. This is consistent with most of the
  in-sample Sharpe coming from the 2015-2026 drift and from fitting, not from the regime machinery.
- **What it does deliver** is shallower drawdowns at lag 0 on four of five sets (NDX -35% vs -53%, DAX -52% vs
  -73%, Nikkei -66% vs -82%). That edge is fragile: one session of lag gives back the NDX gain (-55%) because of
  October 1987.
- **The overlays do not help out of sample.** Bare is at or above CUR on excess Sharpe on NDX lag 0, DAX and
  Nikkei, and ties within noise elsewhere. The trim, gate, ladder, fast overlay and deep-E/panic legs, all fitted
  on 2015-2026, add nothing measurable here.

## Caveats

- NDX 1987-2000 is not fully virgin. Deep-E spells were counted on NDX 1987-2026 before deep-E went live
  (STRATEGY.md), and `breadth_dgate_2000.py` touched 1999-2000. The non-US sets have no such prior use.
- The synthetic 3x/2x legs on the non-US sets are financed at USD T-bill + 0.3%, not local rates, and there is no FX.
  Nikkei and FTSE are price indices, so the leveraged legs miss about 3x the dividend yield while still paying financing.
  This biases those sets against the strategy (FTSE yields about 3-4%). DAX is a total-return index and is the
  cleanest non-US test, and it still fails.
- The breadth half of the D gate is inert everywhere. VIX-panic is off for 1987-89 and for the non-US sets. VIXM is off.
- The momentum core is crude: Ken French Mkt + 0.5 UMD with no costs on the long-short leg.
- These are single historical paths with no bootstrap. NDX 1987-2000 has one crash and one bubble.
