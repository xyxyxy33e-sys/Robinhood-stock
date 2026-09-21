# SPMO's September 2026 reconstitution — analysis, 2026-09-21

**Bottom line: the new portfolio went live at today's open and is not yet
observable. Every holdings source still publishes the OLD book. Nothing in
today's price action can resolve what changed, and no account action is
implied either way.**

## The schedule, pinned

The S&P 500 Momentum Index rebalances **semi-annually, effective after the
close of the third Friday of March and September**, with a **reference date of
the last business day of February and August**.

For this cycle:
- **Reference date: 2026-08-31** — momentum measured as of then
- **Effective: after the close on Friday 2026-09-18**
- **First session of the new portfolio: Monday 2026-09-21 — today**

Note the reference date is exactly the date of our stored snapshot
(`data/spmo_top25_2026-08-31.csv`). That snapshot is the *input* to this
rebalance, not the output.

## The published holdings are still the old book

Invesco's holdings file pulled today carries `last_updated 2026-09-18`.
Compared against our 2026-08-31 snapshot:

| | 31-Aug | 18-Sep |
|---|---|---|
| names in the top 25 | 25 | **same 25** |
| names added / dropped | — | **none / none** |
| rank changes | — | two adjacent swaps (APH↔PM, KLAC↔NEM) |
| Σ\|Δweight\| across the top 25 | — | **1.15 pp** |
| top-25 share of fund | 76.6% | 76.8% |

MU 10.56→10.84, NVDA 8.93→9.05, AVGO 6.41→6.43, JNJ 4.72→4.65 … every move is
a fraction of a point and tracks each name's price over those 13 sessions.
**A momentum reconstitution turns over a large share of the book — 44% annual
turnover on a semi-annual schedule. Zero entries, zero exits and 1.15 pp of
total weight drift is pure price movement, not a rebalance.** The file simply
has not been updated yet.

## Today's price action cannot resolve it

The obvious test — price the old basket and see whether SPMO diverged — is not
powerful enough:

| | today (9/21, official closes) |
|---|---|
| old top-25 basket (76.8% of fund, 18-Sep weights) | **+2.36%** |
| **SPMO actual** | **+1.93%** |
| divergence | **−0.43 pp** |
| SPY | +1.55% |
| QQQ | +2.77% |

The untracked 23.2% tail would need to have returned only **+0.52%** to
explain the whole gap with no rebalance at all — and that tail is the smaller,
lower-beta, defensive half of the book on a day when SPY did +1.55%. Inside
the top 25 the same pattern is visible: XOM −3.20%, KO −1.27%, SNDK −1.44%.
**The gap is fully consistent with no rebalance, and equally consistent with
one. The test is uninformative and I am not going to read a result into it.**

What today *does* show is that whatever is now held behaved normally on day
one: SPMO moved at **0.70× QQQ** (against an 11-year beta of 0.773) and 1.24×
SPY. No discontinuity.

## What actually matters here

**No account action.** SPMO is held as a single ETF; Invesco does the turnover
internally and bears the trading cost. The strategy's own rebalance logic is
untouched — today's drift was 3.7%, inside the band, no trade.

The one thing that matters is whether the new composition **changes SPMO's
risk relationship to the leveraged sleeve**. The case for SPMO as the core leg
(`core_leg_spmo_vs_qqq.md`) rests entirely on beta 0.773 and correlation 0.833
to QQQ — it works *because it is not the Nasdaq*. The pre-rebalance book was
already ~44.8% semiconductors and memory/storage with 50.6% of its top-25
weight also in the Nasdaq-100. Since momentum through August was dominated by
semis, the reference-date ranking makes a *further* concentration more likely
than a diversification.

## Follow-up

1. **Re-pull SPMO holdings in 2–5 sessions**, once Invesco publishes the new
   book, and diff against `data/spmo_top25_2026-08-31.csv`. Record entries,
   exits, the new semiconductor and Nasdaq-100 overlap percentages, and the new
   top-3 concentration.
2. **Then re-measure rolling 6-month beta and correlation of SPMO to QQQ.** If
   beta drifts toward 1.0, the diversification that justifies the core leg is
   eroding and `core_leg_spmo_vs_qqq.md` should be re-run.

Neither is urgent and neither implies a trade.

**Status 2026-09-21 (owner decision): held over to tomorrow.** Owner confirmed
the 18-Sep figures are not the reconstituted book. A self-reminder is scheduled
for 2026-09-22 14:00 UTC (10:00 ET, well clear of the 15:50 trading window) —
`trig_01Rm43Fd2cFQ1wpKo3XTuHv7`. **First action on that run is to check the
holdings as-of date**; if it still reads 2026-09-18 or earlier the file has not
updated, in which case change nothing, read no rebalance into price drift, and
re-arm for the following morning.

## Correction to the record

The `core_leg_spmo_vs_qqq.md` write-up and its STRATEGY.md entry, both written
earlier today, described the 2026-09-18 holdings as "post-reconstitution". That
was wrong — they are the **pre**-reconstitution book, as shown above. The
concentration figures quoted there (top 3 = 26.3%, ~44.8% semis, 50.6%
Nasdaq-100 overlap) are accurate for the portfolio held **through 18
September**, and the concern they raise stands; they are simply not yet the
current portfolio. Both files are corrected.


## Third-party report, 21 Sep 17:00 ET — UNVERIFIED

The owner passed on a Seeking Alpha piece (The Sunday Investor) published after
today's close, reporting on this reconstitution:

- **54 substitutions, ~40% of the portfolio** turned over
- **Apple and Merck the top additions**
- **NVIDIA DELETED**, despite a +30.24% one-year gain
- **Micron still #2, at 8.99%** (it was #1 at 10.84% pre-rebalance)
- still ~52% technology

**I could not verify any of it.** Both holdings sources still carry the old
book: alpha_vantage's snapshot is dated 18-Sep, and Webull's is timestamped
**2026-09-21 07:37 ET** — after the rebalance was effective, and still showing
**NVDA at 9.02%** and MU at 11.09%. Webull additionally reports a **uniform
+28.1% share-count change across every single name**, which is fund creations
(shares outstanding up ~28%), not a reconstitution — a 54-substitution event
cannot leave every surviving name's weight intact and change every share count
by the same percentage.

So the article is a **lead, not a fact**, and it is treated as one. What it
does do is corroborate the section above: ~40% turnover is exactly the scale
that makes the 1.15 pp of drift in the published file obviously stale.

### If the report is right, it cuts the other way from the 21 Sep concern

The concern recorded in `core_leg_spmo_vs_qqq.md` was that the book was drifting
*toward* the Nasdaq and eroding the beta-0.773 diversification that justifies
SPMO as the core leg. A NVDA deletion would push hard the other way:

- **NVDA out removes ~9.0 pp of Nasdaq-100 overlap** — the single largest
  doubled-up position against the TQQQ sleeve.
- **AAPL in adds overlap back** (it is a Nasdaq-100 name), but AAPL is a far
  lower-beta, lower-volatility stock than NVDA. Swapping one for the other
  should **lower** SPMO's beta and vol, not raise them.
- **MRK in is purely diversifying** — NYSE healthcare, not in the Nasdaq-100.
- **MU 10.84% → ~8.99%** reduces the largest single-name concentration.

Net, on these reports, the reconstitution likely **strengthens** the core-leg
case rather than weakening it. That is the opposite of what I flagged this
morning, and worth saying plainly.

### Why a momentum index would delete a stock that rose 30%

Not a contradiction. S&P's momentum score is **risk-adjusted** — price momentum
divided by the volatility of returns — so a name can post a large raw gain and
still score poorly if it got there violently. That is also the structural
reason SPMO carries beta 0.773 to QQQ rather than ~1.0: the methodology
systematically down-weights the highest-volatility winners. It is the same
property that makes SPMO the better core leg in the backtest, working as
designed.

### Verification deferred to tomorrow

The 2026-09-22 reminder (`trig_01Rm43Fd2cFQ1wpKo3XTuHv7`) has been rewritten to
check these specific claims first — is NVDA actually gone, are AAPL and MRK in
and at what weights, is MU ~8.99% — before recomputing the concentration and
overlap figures and the rolling beta. Note the rolling beta will be dominated
by the OLD portfolio for months; it is not a fast read on this change.
