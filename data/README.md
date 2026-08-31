# data/ — SPMO holdings and price history

This directory holds a reconstructed holdings history for **SPMO** (Invesco S&P
500 Momentum ETF, CIK 1378872, series S000050154), plus weekly price series
for every constituent ticker that has ever appeared in a snapshot, built for
backtesting/mirroring purposes.

## Files

| File | Contents |
|---|---|
| `spmo_holdings_history.csv` / `.json` | One row per (reporting-period, holding): 23 snapshots, 2015-10-31 through 2026-05-31. |
| `spmo_weekly_prices.csv` | Weekly split-adjusted OHLCV bars, one row per (ticker, week), for every ticker in the holdings history. |
| `spmo_weekly_prices_meta.json` | Coverage stats and known gaps for the price file. |
| `spmo_top25_2026-08-31.csv` / `.json` | A point-in-time top-25 snapshot with live quotes (separate one-off export, not part of the historical series). |

## `spmo_holdings_history.*` schema

Columns (CSV) / holding fields (JSON): `rep_pd_date, rep_pd_end, accession,
rank, ticker, name, cusip, pct_val, asset_cat`.

- **`rep_pd_date`** — the "as of" date of the holdings snapshot (e.g.
  `2019-11-30`). This is the join key back to a specific reporting period.
- **`rep_pd_end`** — the fund's fiscal-year-end for that filing (Aug 31 from
  2018-08-31 onward; Oct 31 for earlier N-CSR periods — SPMO's fiscal year
  end moved from October to August partway through 2018; see Methodology).
- **`accession`** — the SEC EDGAR accession number of the source filing.
- **`rank`** — 1-based rank by `pct_val` within that period. `rank <= 25`
  reproduces a "top 25" snapshot.
- **`ticker`** — the resolved ticker symbol (see Methodology; blank only if
  unresolved, which does not currently happen — every row has a ticker).
- **`name`** — company name exactly as it appears in the source filing.
- **`cusip`** — 9-digit CUSIP, present only for the 14 periods sourced from
  N-PORT-P XML (2019-11-30 onward); blank for the 9 N-CSR/N-CSRS periods,
  which don't publish CUSIPs in their HTML holdings tables.
- **`pct_val`** — percent of the fund's equity holdings value, computed as
  `holding value / sum(all equity holding values in that period) * 100`.
  Rows in a period sum to ~100.0.
- **`asset_cat`** — asset category; always `EC` (equity — common stock) in
  this file. Non-equity sleeve items (cash collateral, money-market funds
  used for securities lending) are excluded from every period, both the
  N-PORT-derived and the N-CSR-derived ones, for consistency.

### Sources

- **2019-11-30 through 2026-05-31 (14 periods)**: SEC Form **N-PORT-P**
  filings, parsed from the structured XML. `cusip`/`isin` come directly from
  the filing.
- **2015-10-31 through 2019-08-31 (9 periods)**: SEC Form **N-CSR** (annual)
  / **N-CSRS** (semiannual) shareholder reports, parsed from the filing's
  HTML "Schedule of Investments" exhibit. N-PORT-P does not exist for this
  filer before late 2019 (confirmed against
  `https://data.sec.gov/submissions/CIK0001378872.json`), so these are the
  earliest holdings disclosures available for SPMO, reaching back to shortly
  after the fund's 2015-10-13 inception. Because these are HTML tables inside
  a single filing that bundles dozens of Invesco/PowerShares funds together,
  no CUSIP is published and each fund's "Schedule of Investments" section had
  to be located and isolated from the surrounding document by text search
  (fund name + ticker + date heading), not just by form type.

### Periods covered

```
2015-10-31  2016-04-30  2016-10-31  2017-04-30  2017-10-31  2018-04-30
2018-08-31  2019-02-28  2019-08-31  2019-11-30  2020-05-31  2020-11-30
2021-05-31  2021-11-30  2022-05-31  2022-11-30  2023-05-31  2023-11-30
2024-05-31  2024-11-30  2025-05-31  2025-11-30  2026-05-31
```

This is essentially continuous semiannual coverage back to inception — the
only structural gap is the ~3-month window between 2019-08-31 (last N-CSR
period) and 2019-11-30 (first N-PORT-P period), which is smaller than either
form's own reporting cadence.

## Methodology (N-CSR/N-CSRS periods specifically)

1. Listed every N-CSR/N-CSRS filing for CIK 1378872 via
   `data.sec.gov/submissions/CIK0001378872-submissions-00{2,3}.json`
   (the main submissions.json only carries recent filings).
2. Fetched each candidate filing's primary HTML document and searched for
   `(SPMO)` / `PowerShares S&P 500 Momentum Portfolio` / `Invesco S&P 500
   Momentum ETF` to confirm SPMO is actually included in that filing (this
   registrant bundles many funds together and not every semiannual batch
   includes SPMO — several Oct-31/May-31-dated filings in 2018 turned out to
   cover *other* fund groups within the same trust and were skipped).
3. Located the fund-specific "Schedule of Investments" table by anchoring on
   the fund-name-plus-date heading immediately followed by "Shares"/"Value"
   column headers, then parsed the holdings rows (ticker-free tables of
   `shares, company name, dollar value`, or `company name, shares, dollar
   value` — the row order differs between the pre- and post-2019 template;
   both are handled) up to the "Total Investments" line, excluding any
   money-market/cash-collateral sub-table.
4. Computed `pct_val` from each holding's dollar value divided by the sum of
   all parsed equity holding values in that period; parsed totals were
   cross-checked against the filing's own printed "Total Investments" dollar
   figure and matched exactly or within a few hundred dollars (< 0.06%) for
   every one of the 9 periods — the residual is money-market/cash sleeve
   value correctly excluded from both sides.
5. **Ticker resolution**: these filings publish company name only, no
   ticker. Tickers were resolved by (a) exact/normalized match against the
   name→ticker table implicit in the existing N-PORT-derived periods (which
   do carry tickers), and (b) a manual lookup table for ~110 companies that
   don't appear in any 2019+ snapshot — either because they were removed
   from the fund's target index before 2019, or because they were acquired,
   taken private, or renamed before then. All 897 parsed pre-2019 holdings
   rows resolved to a ticker.

## `spmo_weekly_prices.*` schema

Columns: `symbol, week_start, close, open, high, low, volume`. One row per
(ticker, ISO week), split-adjusted, sourced from Robinhood's
`get_equity_historicals` (weekly bars).

- Originally built to cover 2019-11-01 onward for the 478 tickers in the
  N-PORT-derived periods only.
- Extended in this pass to cover **2015-10-01 onward**, to support the newly
  added pre-2019 N-CSR periods:
  - **101 tickers** that only appear in a pre-2019 period got a full fresh
    fetch (2015-10-01 → present).
  - **284 tickers** that were already covered from 2019-10-28 onward (because
    they also appear in a post-2019 period) got a **backward-only** fetch
    (2015-10-01 → 2019-10-27) appended to their existing rows, rather than
    being re-fetched end-to-end.
  - The remaining ~165 previously-covered tickers only ever appear in
    post-2019 periods and were left untouched.
- Interpolated/flat-filled bars returned by the API for dates before a
  ticker's real trading history (or before Robinhood's own data starts) are
  **dropped**, not written — a ticker with only interpolated bars in a given
  window is treated as having no data for that window.

See `spmo_weekly_prices_meta.json` for current row counts, date range, and
the full missing-ticker list with per-ticker delisting/rename notes. As of
this pass: 496 of 561 known tickers have at least some price data; 65 do
not (64 real tickers + the synthetic `CASH` placeholder — see below).

### Known gaps / limitations

- **65 tickers have no price data at all** — mostly companies acquired,
  taken private, or renamed before Robinhood's instrument coverage begins
  (full per-ticker list and reasons in the meta file's `missing_tickers_note`).
  A handful (e.g. EA, WBA, AVB, K, MMC, SEE) are still actively traded under
  the same ticker today and their absence looks like a data-source gap on
  Robinhood's side rather than a real absence of history.
- **`CASH`** is a synthetic ticker used in the holdings file for
  money-market/cash-collateral sleeve line items (e.g. "Invesco Government &
  Agency Portfolio"); it intentionally has no row in the price file since
  it isn't a listed equity.
- **Ticker mapping for pre-2019 holdings is best-effort**, built from a
  manual lookup table rather than a point-in-time ticker database. Dual/
  multi-class shares (Alphabet, Under Armour, News Corp, Fox, Berkshire,
  Discovery, Viacom) are mapped by explicit class-aware overrides. Companies
  that renamed or re-ticked are mapped to the ticker they trade under today
  where they still trade (e.g. Facebook → META, Praxair/Linde-merger names →
  LIN), and to their former ticker where they were acquired/delisted (e.g.
  Time Warner → TWX, CA Inc → CA) so the row is still meaningful even though
  no further price history exists for it.
- **`cusip` is blank for all 9 pre-2019 (N-CSR/N-CSRS) periods** — these
  filings' HTML "Schedule of Investments" tables don't publish CUSIPs, only
  company name, share count, and dollar value.
- **Not every N-CSR/N-CSRS filing in this window covers SPMO.** The
  registrant (Invesco/PowerShares ETF trust) bundles dozens of funds into
  each shareholder-report filing, and different fund groups within the trust
  report on different fiscal-year cycles. Filings with report dates 2018-05-31
  and 2018-10-31 (and their surrounding cousins) were checked and found to
  cover *other* fund groups, not SPMO, and were skipped rather than forced.
- **SPMO's fiscal year end moved from October 31 to August 31 during 2018**
  (the 2018-08-31 N-CSR is a short "stub" transition-period report). This is
  why `rep_pd_end` is `2018-10-31`-family for early periods and `-08-31`-family
  from 2018-08-31 onward — it reflects what each filing itself reports as its
  fiscal year end, not a normalization choice made here.

## How the files join

`spmo_holdings_history` and `spmo_weekly_prices` join on **ticker** (there is
no CUSIP in the price file, so CUSIP cannot be used as the join key despite
being present in some holdings rows). A typical "top 25 holdings priced over
time" query:

```sql
SELECT h.rep_pd_date, h.rank, h.ticker, h.pct_val, p.week_start, p.close
FROM spmo_holdings_history h
JOIN spmo_weekly_prices p
  ON p.symbol = h.ticker
 AND p.week_start >= h.rep_pd_date
WHERE h.rank <= 25
ORDER BY h.rep_pd_date, h.rank, p.week_start;
```

Because `spmo_weekly_prices` doesn't cover all 561 tickers (see gaps above),
any such join should be an outer join, or should be aware that some
`(ticker)` values will simply return zero price rows.
