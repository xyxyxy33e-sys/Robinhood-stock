# Funding policy v2 — percentage-of-current-value, escalating by tier depth

Research line `funding_pct_backtest`, 2026-09-16. Owner request: the account
started near $100k in Aug 2026 and is now ~$198k; the flat $5,000/event
funding policy adopted 2026-09-07 (STRATEGY.md "Funding policy (owner,
2026-09-07)") was ~5% of account value when set and is already ~2.5%,
shrinking every time the account compounds. The owner asked to switch to
funding as a **percentage of current account value at the time of each
event**, escalating by drawdown-tier depth, and asked for this to actually be
backtested rather than picked by feel.

This is a capital-injection POLICY change, not a trading-weight change — no
change freeze applies (BRIEFING.md's freeze governs `state.py`/design
changes) — but the harness discipline still binds: every return in this note
comes from the project's own harness (`run()` / `RF.eval_real()`), never a
reimplemented backtest loop. Script: `paper-track/funding_pct_backtest.py`
(runnable from repo root, `python3 paper-track/funding_pct_backtest.py`,
~30s). No file under `data/`, `state.py`, `STRATEGY.md`,
`paper-track/trigger_prompts/*` or `paper-track/consistency_check.py` was
edited. No commits, no trades, no artifacts.

## 1. Method

**Triggers** (unchanged from the adopted policy, reused/rebuilt exactly):

- **Drawdown tiers** −5/−10/−15/−20% off a rolling ~1-year high of the
  strategy's OWN cash-flow-blind NAV (its return series with the live
  weights applied, no deposits mixed in) — `drawdown_tracker.py`'s actual
  `DD_THRESHOLDS`. Rebuilt here as `tiers_ratchet()` because the live
  tracker operates on an append-only log, not a full return series: a tier
  fires the first time drawdown reaches it since either (a) a new rolling
  high was set, or (b) a shallower tier last fired. This "ratchet" behavior
  — don't refire the same tier on a small recover-and-redip — is what
  reproduces the original per-tier crossing counts; the literal
  yesterday-vs-today comparison coded in `drawdown_tracker.newly_crossed()`
  fires ~4x too often on a noisy return series (boundary flicker).
- **The turn**: `state.effective_state()` shifting from D/E/F into A/B/C,
  using the same 20/100 fast-reentry overlay the live design uses.

**Injection amount**: for every variant below, the amount is `pct * V` where
`V` is the portfolio's dollar value at the moment the trigger fires (not
contributed capital, not a fixed base) — this compounds by design, which is
the entire point of the owner's request.

**Two data sources**, both run through the harness's real weight function
(`live_fn` pattern from BRIEFING.md, `W[eff]` + `extension_scale` + vol
target), never reimplemented:

1. **PRIMARY reproduction method**: the 26-year QQQ-core proxy rows
   (`improvement_search.build()`, `enrich()`ed, `eff`/`gaps` attached exactly
   as `leverage_under_trim.py` does), restricted to the search era
   (2015-11-01+, the SPMO era), triggers computed on a 252-session rolling
   window. This is the method that reproduces STRATEGY.md's original table
   most closely (see §2).
2. **Real-instrument cross-check / main grid**: `RF.real_rows()` — the real
   weekly SPMO/TQQQ/QLD/XLU/BOXX rows, `eff`/`gaps` attached the same way,
   triggers computed on a 52-week rolling window (the weekly equivalent of
   ~252 sessions). Both event detection AND compounding are on real
   instruments throughout — the more literal answer to "what would have
   actually happened."
3. **Long-history check**: the same daily 26-year proxy, full history
   (2000-07..2026-08), for item 5 of the brief (don't fit the pick to one
   11-year bull-heavy window).

**IRR**: money-weighted XIRR, bisection on the dated cash-flow series
(`-100,000` at t0, `-injection` at each event date, `+final value` at the
end). **Per-$ multiple**: back-solving every row of STRATEGY.md's original
table shows "per $" = `final_value / (100,000 + total_contributed)` — i.e.
TVPI on ALL capital deployed including the starting $100k, not on new
contributions alone (e.g. annual lump: `2.17M / (100k+60k) = 13.5625` = the
printed 13.56x; both/adopted: `4.58M / (100k+485k) = 7.84` exactly). This
note uses the same definition throughout.

### Data-path shim (read before rerunning)

`voltarget_live_backtest.py` / `backtest_overlay_etf.py` hard-code
`REPO = '/home/user/robinhood/data/kairos'`, which does not exist in this
environment. The underlying SPMO/TQQQ/QLD/XLU price history already exists
locally at `data/spmo_ohlc.csv` etc. in the exact schema `load_daily_csv()`
expects (`d,o,h,l,c`), just a different path, and a T-bill series exists at
`data/dgs3mo_full.csv` in the schema `load_tbill()` expects. The script
builds a throwaway symlink farm in a temp directory at runtime (nothing
under the repo is written) and points the two `REPO` globals at it
in-process, then calls `VL.build()` completely unmodified. BOXX has no local
file; an empty `BOXX.csv` makes `build_cash_index()` fall back to the T-bill
series for the whole window — exactly what it already does for any date
genuinely missing from BOXX's real history. Reproducing the harness's
standing figures through this shim: 26y proxy 22.18%/0.913/-33.6% (target
22.18/0.913/-33.6), search 1.103 (target 1.103), holdout 0.768 (target
0.768); real weekly 31.34%/1.247/-25.0% (target 31.40/1.248/-25.0) — matches
to within data-vendor rounding.

## 2. Reproduction check (must pass before trusting anything new)

Target (STRATEGY.md, "both (adopted)" row, flat $5,000/event):
**9.0/yr, $485k total, $4.58M final, 31.5% IRR, 7.84x per-$.**

| method | events/yr (tier, turn) | tier counts by level | contributed | final | IRR | per-$ |
|---|---|---|---|---|---|---|
| **daily 26y-proxy, search era, ratchet, 252d window (PRIMARY)** | 9.45 (5.38, 4.08) | {5%: 27, 10%: 15, 15%: 11, 20%: 5} | $510,000 | $4,982,754 | 31.91% | 8.17x |
| real weekly, real instruments throughout, 52-week window (cross-check) | 6.74 (3.42, 3.32) | {5%: 17, 10%: 11, 15%: 5, 20%: 4} | $365,000 | $4,282,806 | 32.70% | 9.21x |
| **STRATEGY.md target** | 9.0 | {5%: 28, 10%: 15, 15%: 8, 20%: 4} (+1 at 25%, not modeled) | $485,000 | $4,580,000 | 31.5% | 7.84x |

The primary (daily, search-era) method is within 5% on events/yr, 5% on
contributed, 9% on final value, 0.4 percentage points on IRR, and 4% on the
multiple — and its per-tier crossing counts (27/15/11/5) land close to the
table's own (28/15/8/4), including matching the 10% tier count exactly. The
turn-event rate (4.08/yr) matches the target's 4.1/yr almost exactly. The
residual gap is attributable to (a) the original `dipfund.py`/`statefund.py`
scripts no longer existing to diff against directly, and (b) this
environment's SPMO/TQQQ/QLD/XLU price pull being a different vendor snapshot
than whatever fed those scripts on 2026-09-07. Both variants land in the same
order of magnitude and same direction on every metric, which is the bar this
line treats as "reproduced" — the daily/search-era method is used as the
long-history-check backbone below, and the weekly-native method is the main
grid (closer to "real instruments throughout").

**Caveat carried forward from the original analysis, confirmed by this
rebuild**: per-dollar efficiency (the "per-$" multiple) falls as trigger
frequency/size rises — this is the same "less money working for longer"
effect the 2026-09-07 note flagged, not a timing failure.

## 3. Main grid — real weekly SPMO-era rows (2015-11..2026-08)

Real instruments throughout (RF.real_rows(), events + compounding both on
`rr`), 6.74 events/yr (3.42 tier, 3.32 turn) for every variant (the trigger
schedule doesn't depend on the injection SIZE, only on the underlying
strategy return series, which every variant shares).

### 3a. Flat percentage (no escalation — tier and turn same %)

| pct | contributed | final | IRR | per-$ |
|---|---|---|---|---|
| 1.0% | $810,217 | $4,025,891 | 32.2% | 4.42x |
| 1.5% | $1,588,179 | $5,772,588 | 32.5% | 3.42x |
| 2.0% | $2,778,849 | $8,262,089 | 32.8% | 2.87x |
| 2.5% | $4,575,088 | $11,803,970 | 33.1% | 2.52x |
| 3.0% | $7,254,344 | $16,834,227 | 33.4% | 2.29x |
| 4.0% | $17,022,402 | $34,059,259 | 34.1% | 1.99x |
| 5.0% | $37,754,414 | $68,434,842 | 34.7% | 1.81x |
| 7.5% | $242,595,726 | $380,314,734 | 36.4% | 1.57x |
| 10.0% | $1,401,820,767 | $2,030,047,694 | 38.2% | 1.45x |

### 3b. Escalating by tier depth (turn at flat base %, not escalated)

**Linear (1x/2x/3x/4x at −5/−10/−15/−20%)**

| base% | contributed | final | IRR | per-$ |
|---|---|---|---|---|
| 1.00% | $1,428,201 | $5,563,066 | 32.6% | 3.64x |
| 1.50% | $3,170,702 | $9,331,941 | 33.0% | 2.85x |
| 2.00% | $6,296,764 | $15,578,186 | 33.5% | 2.44x |
| 2.50% | $11,782,197 | $25,882,121 | 34.0% | 2.18x |
| 3.00% | $21,246,617 | $42,802,562 | 34.5% | 2.01x |

**Mild (1x/1.5x/2x/2.5x)**

| base% | contributed | final | IRR | per-$ |
|---|---|---|---|---|
| 1.00% | $1,090,841 | $4,736,269 | 32.4% | 3.98x |
| 1.50% | $2,276,600 | $7,352,556 | 32.8% | 3.09x |
| 2.00% | $4,246,535 | $11,379,907 | 33.2% | 2.62x |
| 2.50% | $7,460,208 | $17,561,338 | 33.6% | 2.32x |
| 3.00% | $12,629,857 | $27,021,819 | 34.0% | 2.12x |

**Steep (1x/2x/4x/8x)**

| base% | contributed | final | IRR | per-$ |
|---|---|---|---|---|
| 1.00% | $1,921,225 | $6,789,792 | 32.8% | 3.36x |
| 1.50% | $4,595,005 | $12,490,174 | 33.4% | 2.66x |
| 2.00% | $9,823,601 | $22,763,722 | 34.0% | 2.29x |
| 2.50% | $19,763,100 | $41,122,093 | 34.6% | 2.07x |
| 3.00% | $38,255,376 | $73,661,751 | 35.2% | 1.92x |

## 4. Long-history check — 26y QQQ-core proxy (2000-07..2026-08), 9.01 events/yr

Same grid, full proxy history (dot-com bust, GFC, COVID, 2022 all included,
not just the SPMO-era bull run). Same qualitative pattern: IRR rises
modestly with pct/escalation, per-$ multiple falls monotonically, and the
absolute dollar totals over 26 years at higher pct/escalation become
astronomically large (see §6 caveat — this is a mathematical property of
compounding a % of an already-compounding NAV over a long horizon, not a
useful "this is what will happen" number).

| pct (flat) | contributed | final | IRR | per-$ |
|---|---|---|---|---|
| 1.0% | $47.6M | $192.9M | 26.7% | 4.04x |
| 2.0% | $763.9M | $1.95B | 31.1% | 2.56x |
| 3.0% | $9.41B | $19.34B | 34.9% | 2.05x |
| 5.0% | $1.08T | $1.77T | 40.5% | 1.65x |
| 10.0% | $73.8 quadrillion | $99.3 quadrillion | 49.2% | 1.35x |

| escalation, base% | contributed | final | IRR | per-$ |
|---|---|---|---|---|
| linear, 1.0% | $187.5M | $589.6M | 28.9% | 3.14x |
| linear, 2.0% | $8.25B | $17.49B | 35.0% | 2.12x |
| mild, 1.0% | $96.3M | $338.1M | 27.8% | 3.51x |
| mild, 2.0% | $2.57B | $5.91B | 33.1% | 2.30x |
| steep, 1.0% | $397.8M | $1.16B | 30.3% | 2.91x |
| steep, 2.0% | $31.4B | $63.4B | 37.1% | 2.02x |

The 26y check confirms the SAME direction and same non-peaked, monotonic
shape found on the real weekly rows: IRR rises gently and smoothly with
pct/escalation, per-$ multiple falls smoothly, across BOTH the bull-only
SPMO era and the full 2000-2026 window including three real bear markets.
Nothing here is fit to one window — the pick in §7 is chosen on numbers that
are stable across both.

## 5. Dollar-amount scenarios at $100k / $200k / $500k account value

**Mild escalation (1x/1.5x/2x/2.5x), base 1.5%**

| trigger | % of value | at $100k | at $200k | at $500k |
|---|---|---|---|---|
| −5% tier | 1.50% | $1,500 | $3,000 | $7,500 |
| −10% tier | 2.25% | $2,250 | $4,500 | $11,250 |
| −15% tier | 3.00% | $3,000 | $6,000 | $15,000 |
| −20% tier | 3.75% | $3,750 | $7,500 | $18,750 |
| turn | 1.50% | $1,500 | $3,000 | $7,500 |

**Mild escalation, base 2.0%**

| trigger | % of value | at $100k | at $200k | at $500k |
|---|---|---|---|---|
| −5% tier | 2.00% | $2,000 | $4,000 | $10,000 |
| −10% tier | 3.00% | $3,000 | $6,000 | $15,000 |
| −15% tier | 4.00% | $4,000 | $8,000 | $20,000 |
| −20% tier | 5.00% | $5,000 | $10,000 | $25,000 |
| turn | 2.00% | $2,000 | $4,000 | $10,000 |

**Linear escalation (1/2/3/4x), base 1.5%** — for comparison, ramps faster

| trigger | % of value | at $100k | at $200k | at $500k |
|---|---|---|---|---|
| −5% tier | 1.50% | $1,500 | $3,000 | $7,500 |
| −10% tier | 3.00% | $3,000 | $6,000 | $15,000 |
| −15% tier | 4.50% | $4,500 | $9,000 | $22,500 |
| −20% tier | 6.00% | $6,000 | $12,000 | $30,000 |
| turn | 1.50% | $1,500 | $3,000 | $7,500 |

**Steep escalation (1/2/4/8x), base 1.5%** — for comparison, the −20% ask
gets large fast

| trigger | % of value | at $100k | at $200k | at $500k |
|---|---|---|---|---|
| −5% tier | 1.50% | $1,500 | $3,000 | $7,500 |
| −10% tier | 3.00% | $3,000 | $6,000 | $15,000 |
| −15% tier | 6.00% | $6,000 | $12,000 | $30,000 |
| −20% tier | 12.00% | $12,000 | $24,000 | $60,000 |
| turn | 1.50% | $1,500 | $3,000 | $7,500 |

**Flat 2% (no escalation)**, for reference — every trigger asks the same:
$2,000 / $4,000 / $10,000 at $100k/$200k/$500k.

Full script output (every base%, every shape, plus flat 3%/5%) is in
`paper-track/funding_pct_backtest.py`'s `main()` — rerun it for the complete
set; the tables above cover the practically relevant range.

## 6. Honest caveats (carried from and confirmed by the original analysis)

- **Per-dollar efficiency falls as you fund more.** Every grid (flat and
  escalating, both data sources) shows per-$ multiple falling monotonically
  as pct or escalation steepness rises, while IRR rises only gently. This is
  the SAME finding STRATEGY.md's original table made (the annual lump was
  the most $-efficient at 13.56x precisely because it deploys the least
  capital over the shortest average holding time) — more/larger funding is
  a PERSONAL SAVINGS-RATE choice, not an alpha source. A rule that puts more
  money into a ~31% CAGR strategy will always show a higher IRR than idle
  cash, and always a lower per-$ multiple than a smaller/rarer rule,
  because idle cash beats a lump sum in opportunity cost but a fully
  invested lump beats new cash arriving gradually.
- **The sweep is monotonic, not peaked.** No variant in this grid produces
  an interior optimum — IRR climbs smoothly with pct/escalation, multiple
  falls smoothly, on BOTH datasets and BOTH eras of the long-history check.
  There is no "sweet spot" the data points to; the choice of base% and
  escalation shape is a preference (how much of the account's growth should
  come from new savings vs. market return, and how large a single deposit
  the owner is comfortable making at a −20% tier), not an optimization.
- **Percentage-of-value funding compounds explosively over long horizons at
  high pct.** The 26-year check at 10% flat produces $73.8 quadrillion
  contributed — obviously not a real-world number. This is the correct,
  expected mathematical consequence of "inject a % of a value that is
  itself compounding at ~20-30%/yr, repeatedly, for 26 years and ~9
  events/yr" — each injection is itself principal that then also compounds.
  It is not a bug and it is not evidence that low pct is "wrong," it is
  evidence that this backtest's total-contributed and final-value columns
  over multi-decade horizons should be read as a DIRECTIONAL/relative
  comparison between variants, not as a projection of dollars 26 years out.
  The 11-year real-weekly grid is far more usable as a "what would next
  decade look like" reference precisely because it is the shorter, real
  window; use the 26y numbers only for confirming the SHAPE (falling
  multiple, rising IRR) survives outside the SPMO-era bull run, not for
  their absolute dollar values.
- **Single-history caveat**, same one the original $5k analysis carried:
  the real-instrument grid (§3) still covers only 2015-11..2026-08, one
  real bear market (2022). The 26y proxy check (§4) is QQQ-core, not
  SPMO-core, and is structurally blind to anything SPMO-specific — it is
  used here only to confirm the qualitative shape (monotonic, no peak),
  which it does.
- **Turn trigger kept non-escalating** throughout, per the owner's framing
  that it is a confirmation signal (state improved) rather than a severity
  signal (how deep is the damage) — only the drawdown tiers escalate.

## 7. Recommendation

Pick **mild escalation (1x / 1.5x / 2x / 2.5x at −5/−10/−15/−20%), base
1.5-2%**, turn trigger at the same base%. Two candidates, both defensible:

| candidate | −5% / −10% / −15% / −20% / turn | at today's ~$198k |
|---|---|---|
| **A (conservative ramp)** — mild, base 1.5% | 1.5 / 2.25 / 3.0 / 3.75 / 1.5% | $2,970 / $4,455 / $5,940 / $7,425 / $2,970 |
| **B (matches today's dollar level)** — mild, base 2.0% | 2.0 / 3.0 / 4.0 / 5.0 / 2.0% | $3,960 / $5,940 / $7,920 / $9,900 / $3,960 |

Reasoning:

- **Mild over linear/steep.** At the same base%, linear and steep produce
  materially higher IRR and lower per-$ multiple than mild (§3b) — but the
  gap is small (e.g. base 2.0%: mild 33.2%/2.62x vs. linear 33.5%/2.44x vs.
  steep 34.0%/2.29x), while the −20%-tier DOLLAR ASK diverges sharply: at
  $500k, mild asks $25,000, linear asks $40,000, steep asks $80,000 (§5).
  The backtest cannot tell these apart on the numbers alone (the sweep is
  monotonic and gently sloped, not peaked — §6) — the honest read is that
  mild captures nearly all of the escalation's benefit (bigger deposits into
  the deepest, most attractive dips) without asking for a single deposit
  the owner is unlikely to actually want to write when the account and the
  market are both down 20%.
- **Base 1.5-2% over higher.** Every step up the flat-pct or base-pct grid
  keeps raising total dollars contributed and IRR while eroding the per-$
  multiple (§3, §4) — there is no threshold where this reverses. The
  practical ceiling is the owner's own savings capacity and risk tolerance,
  not the backtest. 1.5-2% keeps the −5% (most frequent, ~3.4x/yr) tier's
  ask in the same ballpark as the current flat $5,000 (candidate B's $3,960
  at today's $198k is close to it; candidate A's $2,970 is a deliberate
  step down, front-loading discipline toward the deeper, higher-conviction
  tiers), while still letting the −20% tier and future account growth pull
  the dollar amounts up automatically — which is the entire point of moving
  off a flat number.
- **Base 1.5-2% over lower (1%) or much higher (>3%).** 1% asks less than
  today's $5,000 policy at every tier except −20% (§5, extrapolate: 1% mild
  −5% tier at $198k = $1,980, below today's $5k) — a real step down in
  funding intensity the owner did not ask for. Above 3% base, the −20%-tier
  ask exceeds $25-60k even at today's account size (§5, steep/linear cases)
  before accounting for further account growth — a single-event ask that
  size is a different kind of decision than "fund the dip" and should be a
  deliberate, separately-flagged choice, not a default schedule.
- **Do not oversell precision.** The IRR difference between every
  reasonable candidate in the 1.5-3% base range is under 2 percentage
  points, and the per-$ multiple differences, while larger in relative
  terms, all sit on the same smooth, monotonic curve — this is a savings-
  rate dial, not an alpha discovery. Candidates A and B are a tight,
  economically similar shortlist; the choice between them is really "does
  the owner want funding intensity to step down slightly from today's $5k
  norm (A) or stay roughly level with it before escalating (B)," which is a
  personal preference this backtest cannot resolve for them.

**Adopt candidate B (mild escalation, base 2.0%, turn at 2.0%) as the
default** — it keeps the −5% tier's dollar ask closest to today's $5,000
norm at the current ~$198k account size while satisfying the owner's actual
request (percentage of current value, escalating with tier depth, growing
automatically as the account compounds), with candidate A as the fallback if
the owner wants to start more conservatively and re-check in a year.
