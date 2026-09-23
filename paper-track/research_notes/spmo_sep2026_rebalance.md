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


## Third-party reports — CORROBORATED by two independent sources (holdings file still pending)

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


## Online search, 21 Sep — the report is corroborated, and a key fact was missing

Searching turned up a **second, independent source covering the same index**:
Seoul Economic Daily on **Kiwoom's US S&P 500 Momentum ETF**, a Korean fund
tracking the identical S&P 500 Momentum Index. Index-level changes must be the
same in both funds, so this is genuine corroboration, not an echo.

**Confirmed by both:** 54 substitutions (54 of 99 holdings, ~54.5% of the
portfolio), **Apple added at ~9.0–9.2%** (reported as the new largest holding; Invesco's own 21-Sep file actually has MU 9.21% still #1, AAPL 9.04% #2), **NVIDIA
deleted**, Micron trimmed to ~8.95–8.99% from ~10.84–10.94%.

**The fact the first article omitted: Broadcom was deleted too.** NVDA *and*
AVGO — 9.05% + 6.43% = **15.48 pp** of the pre-rebalance book, and the two
largest high-beta semiconductor positions, both gone.

Other reported changes: Intel raised to 4.89% (from 2.36%), AMD to 4.89% (from
3.87%); Dell, Marvell and Lumentum added in tech hardware; **Merck and
UnitedHealth** in healthcare; **Valero and Marathon Petroleum** in energy.

Sector deltas, which are the most useful numbers here:

| sector | change |
|---|---|
| semiconductors & equipment | **−13.00 pp** |
| technology hardware | **+12.10 pp** |
| healthcare | **+3.55 pp** |
| energy | **+2.35 pp** |
| IT overall | 53.14% → **52.22%** (barely moved) |

## What it means for this strategy

**The Nasdaq-100 overlap barely moves; the risk character changes a lot.**
Netting the named moves, overlap falls only about **−4.6 pp** (before Marvell,
weight unknown) — AAPL simply replaces NVDA+AVGO inside the overlap. But it does
*not* replace them in risk: Apple is a mega-cap with roughly market beta, while
NVDA and AVGO are among the highest-beta names in the index. Add ~6 pp moving
into healthcare and energy — sectors with low correlation to the Nasdaq — and
the direction is clear.

**Expected effect: SPMO's beta and correlation to QQQ go DOWN, not up.** That
is the **opposite** of the concern recorded earlier on 21 Sep, and it
*strengthens* the core-leg case in `core_leg_spmo_vs_qqq.md` rather than
undermining it. The headline concentration figure improves too: the largest
single position drops from MU at 10.84% to AAPL at 9.23%, and MU's memory bet
is cut by ~1.9 pp.

**The caveat that remains:** semis + memory are down 13 pp but not gone — MU is
still ~9%, with INTC and AMD both raised to 4.89%. One commentator is already
calling SPMO "a memory trade". The book is less of a levered-Nasdaq echo than
it was, not a diversified one.

**Still no primary confirmation.** Both holdings sources carry the old book
(Webull timestamped 21 Sep 07:37 ET, NVDA still at 9.02%). Two independent
secondary sources agreeing is strong, but the file is the record. Tomorrow's
check stands, and now has specific claims to test: is NVDA gone, is AVGO gone,
is AAPL ~9.23% and #1, is MU ~8.95%.

**No account action.** SPMO is a single ETF; Invesco bore the ~54% turnover
internally. The strategy holds what it held.

**One forward note:** a rolling 6-month beta will be dominated by the OLD
portfolio for months. If this change is to be measured, it needs either a
short-window estimate that accepts wide error bars, or patience. Do not re-run
the core-leg decision on a few weeks of post-rebalance data.


## The new book, obtained 21 Sep via the Korean listing

Invesco had not published, but **the same index is tracked by a Korean fund**
— KIWOOM 미국S&P500모멘텀, **KRX 0137V0**, 100 stocks, 0.12% ER — and Korean
funds publish a daily constituent file. Its file **as of 2026-09-21** carries
the post-reconstitution book. Saved as
`data/spmo_index_top32_2026-09-21_postrebalance.csv`.

**NVDA and AVGO are absent. Confirmed.**

A consistency check that raises confidence: the fund file's weights sit exactly
where one day of price drift past the rebalance-date weights would put them —
AMD 4.89% → 5.2% after a +9.92% session, INTC 4.89% → 5.1% after +12.14%, MU
8.95% → 9.2% after +2.71%. Internally coherent.

### Top 30, before and after

| # | before (18 Sep) | | after (21 Sep) | |
|---|---|---|---|---|
| 1 | MU | 10.84% | **AAPL** | 9.2% |
| 2 | NVDA | 9.05% | MU | 9.2% |
| 3 | AVGO | 6.43% | AMD | 5.2% |
| 4 | JNJ | 4.65% | INTC | 5.1% |
| 5 | GOOGL | 4.39% | GOOGL | 5.0% |
| 6 | AMD | 3.87% | JNJ | 4.7% |
| 7 | GOOG | 3.48% | GOOG | 4.0% |
| 8 | LRCX | 3.43% | XOM | 3.1% |
| 9 | XOM | 3.15% | SNDK | 2.9% |
| 10 | CAT | 2.43% | LRCX | 2.7% |
| 11–20 | INTC, SNDK, CSCO, AMAT, STX, GE, PLTR, RTX, WDC, GS | | AMAT, CSCO, **MRK**, STX, CAT, WDC, **PANW**, **UNH**, KO, **DELL** | |
| 21–30 | APH, PM, KO, KLAC, NEM, GEV, C, MS, GILD, WELL | | MS, KLAC, RTX, GS, **MRVL**, **VLO**, C, **LITE**, **ADI**, WELL | |

**Out of the top 30:** NVDA (9.05%), AVGO (6.43%), GE, PLTR, APH, PM, NEM, GEV,
GILD. **In:** AAPL (9.2%), MRK (2.2%), PANW (1.6%), UNH (1.6%), DELL (1.2%),
MRVL (1.0%), VLO (1.0%), LITE (0.9%), ADI (0.9%).

### The numbers that matter

| | before | after | change |
|---|---|---|---|
| top 3 | 26.32% | 23.6% | **−2.7 pp** |
| top 5 | 35.36% | 33.7% | −1.7 pp |
| top 10 | 51.72% | 51.1% | −0.6 pp |
| top 30 | 81.97% | 79.8% | −2.2 pp |
| semiconductors | 39.13% | 27.6% | **−11.5 pp** |
| memory / storage | 5.67% | 6.7% | **+1.0 pp** |
| semis + memory | 44.80% | 34.3% | **−10.5 pp** |
| **Nasdaq-100 names** | **50.59%** | **49.8%** | **−0.8 pp** |
| non-tech / defensive | 13.70% | 15.0% | +1.3 pp |

### Two corrections to what I said earlier today

**1. The Nasdaq-100 overlap did NOT fall by ~4.6 pp. It is essentially
unchanged at ~50%.** I estimated −4.6 pp from the reported moves; measured, it
is **−0.8 pp**. AMD and INTC were raised further than the rebalance-date figures
suggested, and PANW, MRVL and ADI came in as additional Nasdaq names, replacing
almost all of the NVDA+AVGO overlap. **The doubled-up exposure against the
TQQQ/QLD sleeve is still there.** That concern is not resolved.

**2. Memory concentration went UP, not down.** SNDK 2.33→2.9%, STX 1.81→2.1%,
WDC 1.53→1.7%, with MU still 9.2%. Semiconductors overall fell 11.5 pp, but the
memory complex grew. The "SPMO is becoming a memory trade" characterisation has
support.

### What still holds

The *character* change is real even though the overlap number is not: NVDA and
AVGO, two of the highest-beta names in the index, are replaced at the top by
AAPL at roughly market beta, and ~6 pp moved into healthcare (MRK, UNH) and
energy (VLO, MPC) — sectors with low correlation to the Nasdaq. Top-3
concentration improved 2.7 pp. **Expected direction on SPMO's beta to QQQ is
still down, but through lower-beta composition rather than through less
overlap.** That is a weaker version of this morning's optimistic read, and it
should be measured, not assumed.

### Caveats

Kiwoom's weights are rounded to one decimal, are one session past the rebalance,
and come from a Korean fund whose implementation (FX, cash drag, sampling) is
not identical to SPMO's. **Invesco's own file is still the record** and remains
the job for tomorrow's check — but the constituent list and the structural
conclusions above are very unlikely to move.


## 2026-09-22: Invesco's own site is unreachable, and every US source is stale

Went to the primary source. **Invesco blocks us.** `curl` to their holdings
download endpoint returns **HTTP 406** on every variant tried (Investor and
Institutional `audienceType`, the `/main/holdings/0` path, the `us-rest`
endpoint), with full browser headers; the page fetcher gets only the
navigation shell, since the site renders holdings client-side. This is not a
proxy fault — the agent proxy reports healthy with no relay failures. It is
Invesco's bot protection.

**Every US secondary source carries the pre-reconstitution constituent set,
four calendar days after the effective date:**

| source | as-of | NVDA | AVGO | AAPL |
|---|---|---|---|---|
| alpha_vantage ETF_PROFILE | 2026-09-18 | 9.05% | 6.43% | absent |
| Webull | 2026-09-22 12:21 UTC | 8.98% | 6.12% | absent |
| stockanalysis.com | 2026-09-17 | 9.02% | 6.05% | absent |
| **TipRanks** | **"2026-09-21"** | **8.98%** | **6.12%** | **absent** |
| Yahoo Finance | intraday | 9.05% | 6.43% | absent |

TipRanks and Webull *date* their data after the rebalance while showing the old
names — they are re-pricing a stale constituent list, not refreshing it. The
only source with the new book remains KIWOOM 0137V0.

### The price-action test still cannot discriminate

22 Sep had wide single-name dispersion (SNDK +6.7%, MU +4.0%, STX +3.8% against
CSCO −5.4%, CAT −1.6%), which should have made the two books separable. It does
not:

| basket | top-15 coverage | implied top-15 return | tail needed to match SPMO |
|---|---|---|---|
| old book | 62.0% | **+1.161%** | −0.16% |
| new book | 62.2% | **+1.089%** | −0.05% |

SPMO actual **+0.657%**. The two books differ by only 7 bp across their top 15
because they share most of those names, and both imply an entirely plausible
tail. **Inconclusive, again, and for a structural reason rather than a bad
day — this test will not resolve it.**

### Conclusion on sourcing

The composition question is settled by the Korean file and the 54/54
reconciliation; what is *not* available is US primary confirmation, and it may
stay unavailable for days. **This is worth remembering as a standing data
limitation: SPMO's published holdings cannot be relied on to be current after a
reconstitution, and Invesco's own site is not machine-reachable from here.**
For future reconstitutions (next: March 2027), go straight to the KRX listing.


## 2026-09-22: PRIMARY SOURCE OBTAINED — owner supplied Invesco's complete holdings file

Owner uploaded Invesco's own **Complete Holdings** CSV, as of **2026-09-21**.
Saved as `data/spmo_complete_holdings_2026-09-21.csv`. This closes the
verification. 126 line items, 99.96% of TNA.

### The Korean file held up

Comparing my KIWOOM-derived top-30 weights against Invesco's:
**mean absolute error 0.08 pp, maximum 0.46 pp** (AMD and INTC, which Kiwoom
had at 5.2/5.1 against Invesco's 5.60/5.56). Structural figures:

| | claimed from Kiwoom | Invesco primary |
|---|---|---|
| top 3 | 23.6% | **23.85%** |
| top 5 | 33.7% | **34.32%** |
| top 10 | 51.1% | **51.23%** |
| top 30 | 79.8% | **79.79%** |
| semis + semicap | 31.2% | **32.09%** |
| memory complex | 15.9% | **15.84%** |
| healthcare | 10.7% | **10.53%** |
| energy | 6.1% | **5.55%** |

**54 true additions / 54 true removals — confirmed exactly** against the
primary file (names crossing the 0.02% threshold in either direction; added
30.56%, removed 34.48%).

### TWO CORRECTIONS to what I reported

**1. MU is still #1, at 9.21%. AAPL is #2 at 9.04%.** Both news sources and the
Kiwoom file put Apple at the top; Invesco's own marks do not. Micron remains
the largest holding, so the headline "Apple is the new top holding" is wrong at
SPMO's 21-Sep marks. It is close — 17 bp apart — and could flip on any day's
prices, but as of the primary file **the fund's biggest position is still
Micron.**

**2. NVDA and AVGO are not fully gone.** Both are still held at **0.01%** —
99 shares of NVDA ($22,511) and 3,404 shares of AVGO ($1,234,495). They are
part of **26 residual stubs totalling 0.05%**: MO, GILD, GEV, GE, RL, COR, NEM,
JBL, CBOE, PLTR, WMB, ATO, HOOD, ROK, APH, EBAY, FCX, LDOS, PM, ETR, FOXA, TPR,
DLTR, F and the two above. Functionally deleted, but the wind-down is not
complete — a detail no secondary source showed and one that explains why a
simple "is NVDA in the holdings list" test would have given the wrong answer.

### Nasdaq-100 overlap, like-for-like at last

Measured on the **full book both sides** with one fixed membership set:

| | overlap |
|---|---|
| before (18-Sep) | 53.81% |
| after (21-Sep) | **52.58%** |
| change | **−1.23 pp** |

So the overlap is **essentially unchanged**, confirming the read from the
Kiwoom file (−0.8 pp on a top-30 basis). AAPL 9.04 + INTC 5.56 + AMD 5.60 +
PANW 1.60 + MRVL 1.00 almost exactly replace NVDA 9.05 + AVGO 6.43 + PLTR 1.69
+ GILD 0.92 + AEP 0.29. **The doubled-up exposure against the TQQQ/QLD sleeve
survives the reconstitution.**

### Net

Every structural conclusion drawn from the Korean listing stands. The
reconstitution cut semiconductors ~11 pp, left the memory complex intact, added
~6 pp of healthcare and energy, and **did not reduce Nasdaq overlap**. Combined
with the cycle-beta finding (`spmo_beta_instability.md`), the picture is: a
book that is less semiconductor-concentrated but no less Nasdaq-correlated,
entering a cycle whose beta has yet to be observed.

## 2026-09-23: US vendor feed caught up — item closed

Scheduled third-attempt check (trigger `trig_01LXUcr8SCznB7hSQDA6uw3H`). Its question was
already answered on 22 Sep by Invesco's own complete-holdings file (above). Webull
`get_fund_holdings` (update_time 2026-09-23 11:37 UTC) now carries the NEW book and
matches Invesco's 21-Sep file to the displayed precision: MU 9.21189%, AAPL 9.04854%,
AMD 5.60101%, INTC 5.56336%, GOOGL 4.90775%, JNJ 4.5381%, GOOG 3.93961%, XOM 2.92664%,
SNDK 2.76818%, LRCX 2.72788%; NVDA and AVGO absent from the top 10. Lag from the
18-Sep-close effective date to a US vendor feed: 3 sessions (Webull), for the record.
Nothing to change; beta NOT re-measured (next meaningful reading is a full cycle,
around the March 2027 reconstitution). No account action. Not re-armed.
