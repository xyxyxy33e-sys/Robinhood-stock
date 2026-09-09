# Shared briefing for the 2026-09-08 volatility research lines

You are running ONE research line against a live, frozen trading strategy.
Research is welcome; changing anything live is not. Read all of this first.

## Hard constraints
- CHANGE FREEZE until 2026-12-07. This is research-only. Nothing you find gets applied.
- Do NOT edit: paper-track/state.py, STRATEGY.md, paper-track/trigger_prompts/*,
  any file already under data/ (you may ADD new data files under data/ with a
  provenance note in your writeup), paper-track/consistency_check.py.
- Do NOT git commit or push. Do NOT touch the Robinhood account, place orders,
  or edit any artifact. The orchestrator integrates your results.
- Write your script(s) to paper-track/<line_name>.py and a full writeup to
  paper-track/research_notes/<line_name>.md. Return a concise summary with the
  key tables in your final message.
- Run everything from the repo root /home/user/Robinhood-stock. Scripts take
  minutes; use Bash timeouts up to 600000 ms.

## The harness — reuse it, never reimplement the loop
A hand-rolled backtest loop silently rebalances costlessly every day and
produces numbers that look right and are not (this bit the project on 09-07).
Standing rule: reproduce figures ONLY through the project's own harness.

Bootstrap the 26-year QQQ-core proxy + real SPMO rows with:
    import sys; sys.path.insert(0,'paper-track')
    exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
That gives you: `rows` (daily proxy rows 2000-07..2026-08 with r['d'], r['state'],
r['agree'], r['eff'] (effective state after the fast overlay), r['gaps']
({100:,150:,200:} close/SMA-1), r['vol'] (30d), r['vol10'], r['vol_live']
(max(10,30) = the LIVE estimator), r['legs'] (5-tuple of leg returns)),
`rr` (real weekly SPMO-era rows with r['d0'], r['state'], r['agree'], r['legs'],
plus r['eff'] and r['gaps'] attached; NOTE on rr, r['vol'] is ALREADY the live
max(10,30) estimator and r['vol30'] is the plain 30d -- voltarget_live_backtest.build,
2026-09-07; the overlay_interactions line lost a run to this), `ds`/`px` (QQQ dates/closes),
`W` (TARGET_WEIGHTS), `vt` (vol-target function), `evaluate`, `run`, `RF`
(return_frontier: RF.eval_real(rr, fn), RF.vt), `qd`/`qqq`.
- evaluate(rows, wfn) -> dict(cagr, sharpe, mdd, risky, s_sharpe, h_sharpe)
- run(rows, wfn) -> (daily_returns_list, avg_exposure); costs and the 3% drift
  band are inside it.
- from improvement_search import SEARCH, HOLDOUT, era ; SEARCH=2015-11-01+,
  HOLDOUT=2000-07-01..2015-10-31.
- Real rows need r['vol_live'] attached yourself if you use it (pattern in
  paper-track/perleg_vol_test.py: max of realized_vol(qd,qqq,as_of=d0,10/30)).
- If your idea concerns the SPMO (S&P) core leg specifically, the QQQ-core
  proxy is STRUCTURALLY BLIND (core is modelled as QQQ). Use the SPY-core
  proxy: exec(open('paper-track/volgap_test.py').read().split('# ---- IDEA A')[0])
  gives `srows` (SPY-core) and `qrows` (QQQ-core), same row schema.

A weight function is fn(r) -> 5-tuple (core, tqqq, qld, xlu, cash) summing to 1.
The LIVE design as a weight function (copy exactly):
    from state import extension_scale
    def live_fn(r):
        w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
        if f < 1: w = tuple(a*f for a in w[:4]) + (1 - f*sum(w[:4]),)
        return vt(w, r.get('vol_live') or r['vol'])
On rr use RF.vt instead of vt and attach vol_live first.

Standing live figures you must reproduce before trusting anything:
  26y proxy 22.12% / 0.938 / -32.8%, search Sharpe 1.150, holdout 0.780
  real weekly 30.67% / 1.260 / -25.3%
Live design: A row 50/50 SPMO/TQQQ; B 75/25; C 100/0; D 100% QLD; E 50 XLU/50 cash;
F 100% cash. Fast re-entry overlay 20/100. Graded extension trim: votes for
{100d>10%, 150d>12%, 200d>15%}, risky legs x(1 - votes/3), effective state A
only. Vol target 20% on max(10d,30d) realized vol, cap 1.0 (never levers up).
50/200 classifier with 1% hysteresis. 3% L1 drift band, 4bp one-way cost.

## Controls — all mandatory where applicable
1. BOTH-ERA: a candidate must beat live on search AND holdout Sharpe.
2. EXPOSURE / BETA MATCH. Anything that changes how much risk is held will
   look better or worse for that reason alone. from downturn_review import
   exposure_control  -> exposure_control(rows, target_exp) returns (k, ev) with
   ev['exp_matched']; it scales the live baseline to the same DEPLOYED CAPITAL.
   For leverage-mix changes (SPMO 1x vs TQQQ 3x at the same capital) use
   from improvement_search_r2 import beta_of, beta_matched_control.
   Better still for parameterised rules: re-calibrate the rule's constant by
   bisection until its average exposure equals live's (perleg_vol_test.py).
3. CAUSAL THRESHOLDS ONLY. Never fit a threshold on the search era and apply
   it backward. Use trailing/expanding statistics. Build them from the DAILY
   series once and attach to rows by date — building per row-list burned 500
   *weeks* on the weekly rows today and cut real confirmation from 564 to 64.
4. SAME ROWS. If your data starts late, restrict EVERY variant including the
   live baseline to the same rows. Never let a variant fall back to the live
   estimator where its own input is missing.
5. BLOCK BOOTSTRAP, not day-shuffle: from block_bootstrap import boot, stats,
   N_BOOT ; boot(a, b, block, seed) on the two daily return series -> (lo_logret,
   hi_logret, P_logret<=0, lo_sharpe, hi_sharpe, P_sharpe<=0); use blocks 20 and 60.
6. PLACEBO. Sign-flip the signal, or replace it with a random/constant version
   of the same magnitude. A real signal must LOSE when flipped.
7. LEAVE-ONE-REGIME-OUT over dot-com 2000-02, GFC 2007-09, COVID 2020, 2022,
   and the whole SPMO era 2015-11+.
8. REPORT THE CANDIDATE COUNT. Sweeping 40 variants and finding 1 is chance.
9. REAL-INSTRUMENT confirmation on rr for anything that survives.

## Lessons from today, each of which produced a false positive before it was caught
- Wins that grow MONOTONICALLY with a tilt/leverage parameter, with drawdown
  worsening in step, are a leverage artifact, not a signal.
- A threshold fitted on 2015+ and applied to 2001-2015 put 5% of holdout rows
  above it: the rule was permanently tilted one way through the holdout.
- r['d'] is d0 and r['legs'] is the d0->d1 return. Pairing a return with a
  signal at r['d'] is a PREDICTIVE pairing. Contemporaneous needs the signal
  change over d0->d1. Sanity-check alignment (e.g. QQQ vs VIX change should
  be about -0.75).
- compute_states() returns a LIST; compute_fast_states/compute_extension_gaps
  return dicts keyed by date. current_drawdown() returns a 5-tuple.
- FRED CSVs carry EMPTY values on holidays: forward-fill, never drop.
- Every vol-based TIMING overlay tested today failed or landed inside noise;
  vol as a SCALING input is what works. Judge your idea by which it is.

## Data
- data/qqq_long_history.csv  d,o,c  1999-09-15..2026-09-04 (open+close only)
- data/spy_long_history.csv  d,c    1999-09-15..2026-08-27
- data/vxncls.csv  FRED VXNCLS (Nasdaq-100 vol index) 2001-02-02..2026-09-04
- data/vixcls_full.csv  FRED VIXCLS (S&P 500 vol index) 1990-01-02..2026-09-07
- FRED download pattern that works through the proxy:
    curl -sS --max-time 120 -o <file> "https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES>"
- Alpha Vantage / EODHD / Robinhood MCP tools exist (load via ToolSearch) if
  you need OHLC or other series; EODHD free plan is capped at 1 year.

## What "go deep" means
Do not stop at the first table. If something survives the screen, run every
control above and try to break it. If it fails, say exactly WHERE it fails and
what would have to be true for it to work. Distinguish "no signal" from
"signal, but not large enough" from "signal, but it is a risk-preference dial".
Quote numbers, not adjectives.
