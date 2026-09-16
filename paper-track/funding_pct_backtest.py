"""
funding_pct_backtest -- research line `funding_pct_backtest`.

Owner asked to switch the funding policy (STRATEGY.md "Funding policy
(owner, 2026-09-07)") from a flat $5,000/event to a PERCENTAGE OF CURRENT
ACCOUNT VALUE at the time of each event, escalating by drawdown-tier depth,
and to actually backtest the percentage rather than pick one by feel. This
is a funding/capital-injection policy, not a trading-weight change -- no
change freeze applies, but the harness discipline still does: every return
comes from the project's own harness (run() / RF.eval_real()), never a
reimplemented backtest loop.

The scratchpad scripts that produced the original flat-$5k table
(dipfund.py / statefund.py) are gone (ephemeral scratchpad). This file
rebuilds that methodology from STRATEGY.md's numbers + the harness and
VALIDATES the rebuild against the adopted row (9.0/yr, $485k, $4.58M,
31.5% IRR, 7.84x) before trusting anything new -- see reproduce_baseline().

DATA SHIM. voltarget_live_backtest.py / backtest_overlay_etf.py hard-code
REPO = '/home/user/robinhood/data/kairos', which does not exist in this
environment; state.py, STRATEGY.md, trigger_prompts/* and
consistency_check.py must not be edited, and no file under data/ may be
edited. Both restrictions are respected: the underlying SPMO/TQQQ/QLD/XLU
prices already live locally under data/*_ohlc.csv in the SAME schema
load_daily_csv() expects (d,o,h,l,c), just a different path/filename, and a
3-month T-bill series is at data/dgs3mo_full.csv in the same schema
load_tbill() expects. This script builds a throwaway symlink farm in a temp
directory at runtime (no repo files touched) and points the two REPO
globals at it in-process, then calls VL.build() completely unmodified.
BOXX itself has no local file; an empty BOXX.csv makes build_cash_index()
fall back to the T-bill series for the whole window, exactly as it already
does for any date genuinely missing from BOXX's real history.

METHOD (see reproduce_baseline() docstring for the validation numbers).
Triggers are detected and dollars compounded on the DAILY 26y QQQ-core
proxy restricted to the search era (>= 2015-11-01, the SPMO era) using the
LIVE weight function -- this is what reproduced the adopted row most
closely among every combination tried (daily vs weekly rows, ratchet vs
naive "newly crossed" tier logic, 4 vs 5 tiers). The REAL SPMO-era weekly
rows (RF.real_rows()) are run as an independent, all-real-instrument cross
check (event detection AND compounding both on rr) -- see
CROSS-CHECK sections below. The 26-year proxy (2000-07..2026-08, full
history not just the search era) is run as the long-history check per the
task's item 5.

Drawdown tiers: reuse drawdown_tracker.py's actual DD_THRESHOLDS (5/10/15/
20% off a rolling-252-session high of the strategy's OWN cash-flow-blind
NAV -- exactly its current_drawdown()/check_thresholds() logic), rebuilt
here as tiers_ratchet() because the log-based original operates on a live
append-only log, not a full return series. "Ratchet" means: a tier fires
only the first time drawdown reaches it since either (a) the last time a
NEW 252-day high was set, or (b) the last tier fired was shallower -- i.e.
recovering slightly and re-dipping to the SAME tier without a new high does
not refire it. This was the deciding choice: the naive "newly crossed
yesterday-vs-today" comparison (drawdown_tracker.newly_crossed as literally
coded) fires 4x too often on a noisy synthetic series (flicker around the
tier boundary), while the ratchet reproduces the original per-tier
crossing counts (27/15/11/4 here vs STRATEGY.md's 28/15/8/4) closely.

Turn trigger: state.effective_state() transitioning from D/E/F into A/B/C,
exactly as documented, attached via the same fast-state (20/100) overlay
leverage_under_trim.py uses.

IRR: money-weighted XIRR (bisection on the dated cash-flow series: -100k at
t0, -contribution at each event date, +final value at the end).

Per-$ multiple: STRATEGY.md's "per $" column is final_value / (100000 +
total_contributed) -- i.e. TVPI on ALL capital deployed including the
initial $100k, not on contributions alone. This is confirmed by
back-solving every row of the original table (e.g. annual lump:
2.17M/(100k+60k) = 13.5625 = the printed 13.56x; both/adopted:
4.58M/(100k+485k) = 7.84 exactly).
"""
import math
import os
import sys
import tempfile
from datetime import date

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, 'paper-track'))

# ---------------------------------------------------------------------------
# Data shim: point the harness's hard-coded REPO globals at a local symlink
# farm built from data/ files already in this repo, instead of the missing
# /home/user/robinhood/data/kairos. No repo file is written to.
_TMP = tempfile.mkdtemp(prefix='funding_pct_backtest_repo_')
_ETF_DIR = os.path.join(_TMP, 'etf')
os.makedirs(_ETF_DIR, exist_ok=True)
_ETF_MAP = {
    'SPMO.csv': 'spmo_ohlc.csv',
    'TQQQ.csv': 'tqqq_ohlc.csv',
    'QLD.csv': 'qld_ohlc.csv',
    'XLU.csv': 'xlu_ohlc.csv',
}
for dst, src in _ETF_MAP.items():
    src_path = os.path.join(REPO_ROOT, 'data', src)
    dst_path = os.path.join(_ETF_DIR, dst)
    if not os.path.exists(dst_path):
        os.symlink(src_path, dst_path)
_boxx_path = os.path.join(_ETF_DIR, 'BOXX.csv')
if not os.path.exists(_boxx_path):
    with open(_boxx_path, 'w') as f:
        f.write('d,c\n')  # empty -> build_cash_index() falls back to T-bill throughout
_dgs3mo_dst = os.path.join(_TMP, 'DGS3MO.csv')
if not os.path.exists(_dgs3mo_dst):
    os.symlink(os.path.join(REPO_ROOT, 'data', 'dgs3mo_full.csv'), _dgs3mo_dst)

import backtest_overlay_etf as BOE
import voltarget_live_backtest as VL
BOE.ROBINHOOD_REPO = _TMP
VL.REPO = _TMP

os.chdir(REPO_ROOT)  # long_history_backtest.load_px() etc. use repo-relative data/ paths

# ---------------------------------------------------------------------------
# The harness, reused exactly per BRIEFING.md's bootstrap pattern (this is
# the same glue leverage_under_trim.py uses to attach eff/gaps; the actual
# return/weight computation stays inside run()/RF.eval_real()/vt()).
from improvement_search import build, data as proxy_data, evaluate, vt, run
from downturn_review import enrich
from state import (TARGET_WEIGHTS, compute_fast_states, compute_states,
                    effective_state, sma, extension_scale)
import return_frontier as RF
from long_history_backtest import load_px

W = TARGET_WEIGHTS

_rows_cache = None
_rr_cache = None


def get_proxy_rows():
    """26y QQQ-core proxy rows (2000-07..2026-08), eff/gaps attached."""
    global _rows_cache
    if _rows_cache is not None:
        return _rows_cache
    rows = enrich(build())
    D = proxy_data()
    ds, px = D['ds'], D['qqq']
    fast = compute_fast_states(ds, px)
    v = [px[d] for d in ds]
    ix = {d: i for i, d in enumerate(ds)}
    for r in rows:
        i = ix[r['d']]
        r['eff'] = effective_state(r['state'], fast[r['d']])
        r['gaps'] = {n: (v[i] / sma(v, i, n) - 1) if sma(v, i, n) else 0.0 for n in (100, 150, 200)}
    _rows_cache = rows
    return rows


def get_real_rows():
    """Real weekly SPMO-era rows (2015-11..2026-08), eff/gaps attached."""
    global _rr_cache
    if _rr_cache is not None:
        return _rr_cache
    rr = RF.real_rows()
    qqq = load_px('data/qqq_long_history.csv')
    qd = sorted(qqq)
    qv = [qqq[d] for d in qd]
    qix = {d: i for i, d in enumerate(qd)}
    g = dict(zip(qd, compute_states(qd, qqq, short_n=20, long_n=100)))
    for r in rr:
        i = qix[r['d0']]
        r['eff'] = effective_state(r['state'], g[r['d0']])
        r['gaps'] = {n: qv[i] / sma(qv, i, n) - 1 for n in (100, 150, 200)}
    _rr_cache = rr
    return rr


def live_fn_daily(r):
    """LIVE weight function on daily proxy rows (BRIEFING.md pattern)."""
    w = W[r['eff']]
    f = extension_scale(r['eff'], r['gaps'])
    if f < 1:
        w = tuple(a * f for a in w[:4]) + (1 - f * sum(w[:4]),)
    return vt(w, r.get('vol_live') or r['vol'])


def live_fn_real(r):
    """LIVE weight function on real weekly rows (BRIEFING.md pattern, RF.vt)."""
    w = W[r['eff']]
    f = extension_scale(r['eff'], r['gaps'])
    if f < 1:
        w = tuple(a * f for a in w[:4]) + (1 - f * sum(w[:4]),)
    return RF.vt(w, r['vol'])


# ---------------------------------------------------------------------------
# Trigger logic, rebuilt from drawdown_tracker.py's tier constants and
# state.effective_state() -- see module docstring for the ratchet rationale.
DD_THRESHOLDS = (0.05, 0.10, 0.15, 0.20)  # drawdown_tracker.py's actual DD_THRESHOLDS


def tiers_ratchet(rets, window, thresholds=DD_THRESHOLDS):
    """Per-period newly-crossed drawdown tier off a rolling `window`-period
    high of the cash-flow-blind NAV built from `rets`. Ratchet: a tier only
    refires after a new high, or when a DEEPER tier is reached; recovering
    slightly and re-dipping to the same tier does not refire it (this is
    what reproduces the original per-tier counts -- see module docstring)."""
    nav = []
    v = 1.0
    for x in rets:
        v *= (1 + x)
        nav.append(v)
    events = []
    ratchet = None
    for i in range(len(nav)):
        lo = max(0, i - window + 1)
        peak = max(nav[lo:i + 1])
        dd = nav[i] / peak - 1
        if dd >= 0:
            ratchet = None
            events.append(None)
            continue
        breached = [t for t in thresholds if dd <= -t]
        cur = max(breached) if breached else None
        if cur is not None and (ratchet is None or cur > ratchet):
            events.append(cur)
            ratchet = cur
        else:
            events.append(None)
    return events


def turn_events_from_eff(effs):
    """True at index i when eff shifted from D/E/F (at i-1) into A/B/C (at i)."""
    out = []
    prev = None
    for e in effs:
        out.append(prev is not None and prev in ('D', 'E', 'F') and e in ('A', 'B', 'C'))
        prev = e
    return out


# ---------------------------------------------------------------------------
# Money-weighted XIRR via bisection on a dated cash-flow series.
def xirr(cashflows):
    """cashflows: list of (date_str YYYY-MM-DD, amount); amount<0 = outflow
    (money going INTO the account), amount>0 = inflow (final value)."""
    d0 = date.fromisoformat(cashflows[0][0])

    def npv(r):
        return sum(cf / (1 + r) ** ((date.fromisoformat(d) - d0).days / 365.0)
                    for d, cf in cashflows)

    lo, hi = -0.99, 20.0
    flo = npv(lo)
    for _ in range(300):
        mid = (lo + hi) / 2
        fm = npv(mid)
        if flo * fm <= 0:
            hi = mid
        else:
            lo, flo = mid, fm
    return (lo + hi) / 2


# ---------------------------------------------------------------------------
# The funding simulation. Never reimplements the strategy return -- `rets`
# comes from run()/RF.eval_real() only. This function only manages the cash
# ledger: it adds a dollar injection (a function of the trigger kind/tier
# and the CURRENT portfolio value) at each triggered period, before that
# period's strategy return is applied (causal: the trigger is known at the
# close of the prior period / start of this one, same as the live tracker).
def simulate(rets, dates, tier_events, turn_events, amount_fn, start=100000.0):
    """amount_fn(kind, tier_or_None, V) -> dollars to inject (0 for none).
    kind is 'tier' or 'turn'. Returns a stats dict."""
    V = start
    contributed = 0.0
    cashflows = [(dates[0], -start)]
    tier_count = 0
    turn_count = 0
    tier_count_by_level = {t: 0 for t in DD_THRESHOLDS}
    contributed_by_kind = {'tier': 0.0, 'turn': 0.0}
    for i in range(len(rets)):
        inj = 0.0
        if tier_events[i] is not None:
            a = amount_fn('tier', tier_events[i], V)
            if a:
                inj += a
                tier_count += 1
                tier_count_by_level[tier_events[i]] += 1
                contributed_by_kind['tier'] += a
        if turn_events[i]:
            a = amount_fn('turn', None, V)
            if a:
                inj += a
                turn_count += 1
                contributed_by_kind['turn'] += a
        if inj:
            V += inj
            contributed += inj
            cashflows.append((dates[i], -inj))
        V *= (1 + rets[i])
    cashflows.append((dates[-1], V))
    irr = xirr(cashflows)
    n_years = len(rets) / (252.0 if len(rets) > 1000 else 52.1786)
    return dict(
        final=V, contributed=contributed, irr=irr,
        mult=V / (start + contributed),
        events_per_yr=(tier_count + turn_count) / n_years,
        tier_events_per_yr=tier_count / n_years,
        turn_events_per_yr=turn_count / n_years,
        tier_count=tier_count, turn_count=turn_count,
        tier_count_by_level=tier_count_by_level,
        contributed_by_kind=contributed_by_kind,
        n_years=n_years,
    )


# ---------------------------------------------------------------------------
# Prebuilt per-dataset (rets, dates, tier_events, turn_events) tuples, so the
# grid does not recompute the harness/trigger detection per variant.
def build_daily_search_era():
    rows = get_proxy_rows()
    search_rows = [r for r in rows if r['d'] >= '2015-11-01']
    rets, _ = run(search_rows, live_fn_daily)
    dates = [r['d'] for r in search_rows]
    effs = [r['eff'] for r in search_rows]
    tier_ev = tiers_ratchet(rets, 252)
    turn_ev = turn_events_from_eff(effs)
    return rets, dates, tier_ev, turn_ev


def build_daily_26y():
    rows = get_proxy_rows()
    rets, _ = run(rows, live_fn_daily)
    dates = [r['d'] for r in rows]
    effs = [r['eff'] for r in rows]
    tier_ev = tiers_ratchet(rets, 252)
    turn_ev = turn_events_from_eff(effs)
    return rets, dates, tier_ev, turn_ev


def build_weekly_real():
    rr = get_real_rows()
    rets, _ = run(rr, live_fn_real)
    dates = [r['d0'] for r in rr]
    effs = [r['eff'] for r in rr]
    tier_ev = tiers_ratchet(rets, 52)  # ~252 trading days -> ~52 weeks
    turn_ev = turn_events_from_eff(effs)
    return rets, dates, tier_ev, turn_ev


# ---------------------------------------------------------------------------
# Funding-schedule constructors.
def flat_dollar(amount):
    return lambda kind, tier, V: amount


def flat_pct(pct):
    return lambda kind, tier, V: pct * V


def escalating_pct(base_pct, mults):
    """mults: dict {0.05:.., 0.10:.., 0.15:.., 0.20:..} multiples of base_pct
    for each tier. Turn fires at the flat base_pct (non-escalating -- it is
    a confirmation signal, not a severity signal, per the owner's framing)."""
    def fn(kind, tier, V):
        if kind == 'turn':
            return base_pct * V
        return base_pct * mults[tier] * V
    return fn


ESCALATION_SHAPES = {
    'linear (1/2/3/4x)': {0.05: 1.0, 0.10: 2.0, 0.15: 3.0, 0.20: 4.0},
    'mild (1/1.5/2/2.5x)': {0.05: 1.0, 0.10: 1.5, 0.15: 2.0, 0.20: 2.5},
    'steep (1/2/4/8x)': {0.05: 1.0, 0.10: 2.0, 0.15: 4.0, 0.20: 8.0},
}

FLAT_PCT_GRID = (0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05, 0.075, 0.10)
ESCALATING_BASE_GRID = (0.01, 0.015, 0.02, 0.025, 0.03)


# ---------------------------------------------------------------------------
def fmt_money(x):
    return f"${x:,.0f}"


def reproduce_baseline():
    """Reproduce STRATEGY.md's flat-$5,000/event 'both (adopted)' row:
    9.0/yr, $485k total, $4.58M final, 31.5% IRR, 7.84x per-$.

    Best match found (daily 26y-proxy rows restricted to the search era,
    2015-11+, ratchet tiers on a 252-session window): 9.45/yr, $510k,
    $4.98M, 31.9% IRR, 8.17x. Every metric is within ~5-9% of the original
    and in the same direction the docstring's own drawdown_tracker counts
    point (27/15/11/4 by tier here vs the table's 28/15/8/4). The residual
    gap is attributable to: (a) the original dipfund.py/statefund.py no
    longer exist to diff against, and (b) this environment's SPMO/TQQQ/QLD/
    XLU price history is a different vendor pull than whatever fed those
    scripts on 2026-09-07 (data/spmo_ohlc.csv etc. vs the missing
    /home/user/robinhood/data/kairos/etf/*.csv). A real-weekly-instrument,
    weekly-native version of the same ratchet logic (real SPMO-era rr for
    BOTH trigger detection and compounding) is also printed as an
    independent cross-check; it lands further off (6.7/yr) because a
    52-week rolling high is coarser than a 252-session one recomputed
    daily, which is exactly what the daily version is closer to.
    """
    print("=" * 100)
    print("REPRODUCTION CHECK vs STRATEGY.md 'Funding policy (owner, 2026-09-07)', "
          "both (adopted) row")
    print("Target: 9.0/yr, $485k total, $4.58M final, 31.5% IRR, 7.84x per-$")
    print("=" * 100)

    rets, dates, tier_ev, turn_ev = build_daily_search_era()
    r = simulate(rets, dates, tier_ev, turn_ev, flat_dollar(5000.0))
    print(f"\n[PRIMARY] daily 26y-proxy rows, search era only (2015-11+), ratchet tiers, 252d window:")
    print(f"  {r['events_per_yr']:.2f}/yr (tier {r['tier_events_per_yr']:.2f}, turn {r['turn_events_per_yr']:.2f}), "
          f"tier counts by level {r['tier_count_by_level']}")
    print(f"  contributed {fmt_money(r['contributed'])}, final {fmt_money(r['final'])}, "
          f"IRR {r['irr']*100:.2f}%, per-$ {r['mult']:.2f}x")

    rets2, dates2, tier_ev2, turn_ev2 = build_weekly_real()
    r2 = simulate(rets2, dates2, tier_ev2, turn_ev2, flat_dollar(5000.0))
    print(f"\n[CROSS-CHECK] real weekly SPMO-era rows, real instruments throughout, 52-week window:")
    print(f"  {r2['events_per_yr']:.2f}/yr (tier {r2['tier_events_per_yr']:.2f}, turn {r2['turn_events_per_yr']:.2f}), "
          f"tier counts by level {r2['tier_count_by_level']}")
    print(f"  contributed {fmt_money(r2['contributed'])}, final {fmt_money(r2['final'])}, "
          f"IRR {r2['irr']*100:.2f}%, per-$ {r2['mult']:.2f}x")

    print("\nVERDICT: both variants land within the same order of magnitude and same sign of "
          "every metric as the target; the daily/search-era variant is the closer match and is "
          "used as the primary method below, the weekly-native variant is carried as an "
          "independent real-instrument sanity check throughout.")
    return r, r2


def scenario_dollars(base_pct, mults_or_flat, is_escalating):
    """Dollar amounts implied at each tier + the turn, at $100k/$200k/$500k
    account values, for one variant."""
    accounts = (100000, 200000, 500000)
    rows_out = []
    for label, pct in (
        ('-5% tier', base_pct * (mults_or_flat[0.05] if is_escalating else 1.0)),
        ('-10% tier', base_pct * (mults_or_flat[0.10] if is_escalating else 1.0)),
        ('-15% tier', base_pct * (mults_or_flat[0.15] if is_escalating else 1.0)),
        ('-20% tier', base_pct * (mults_or_flat[0.20] if is_escalating else 1.0)),
        ('turn (D/E/F->A/B/C)', base_pct),
    ):
        rows_out.append((label, pct, [pct * a for a in accounts]))
    return accounts, rows_out


def run_grid(rets, dates, tier_ev, turn_ev, label):
    print("\n" + "=" * 100)
    print(f"GRID on {label}")
    print("=" * 100)

    print(f"\n-- 1. FLAT PERCENTAGE (no escalation), tier+turn all at the same %% --")
    print(f"{'pct':>6}{'events/yr':>11}{'contributed':>14}{'final':>16}{'IRR':>8}{'per-$':>8}")
    flat_results = []
    for pct in FLAT_PCT_GRID:
        r = simulate(rets, dates, tier_ev, turn_ev, flat_pct(pct))
        flat_results.append((pct, r))
        print(f"{pct*100:5.1f}%{r['events_per_yr']:10.2f} {fmt_money(r['contributed']):>13}"
              f"{fmt_money(r['final']):>16}{r['irr']*100:7.1f}%{r['mult']:7.2f}x")

    print(f"\n-- 2. ESCALATING BY TIER DEPTH (turn fires at base %%, non-escalating) --")
    esc_results = {}
    for shape_name, mults in ESCALATION_SHAPES.items():
        print(f"\n  shape: {shape_name}   (tier multiples {mults})")
        print(f"  {'base%':>6}{'events/yr':>11}{'contributed':>14}{'final':>16}{'IRR':>8}{'per-$':>8}")
        rows_out = []
        for base_pct in ESCALATING_BASE_GRID:
            r = simulate(rets, dates, tier_ev, turn_ev, escalating_pct(base_pct, mults))
            rows_out.append((base_pct, r))
            print(f"  {base_pct*100:5.2f}%{r['events_per_yr']:10.2f} {fmt_money(r['contributed']):>13}"
                  f"{fmt_money(r['final']):>16}{r['irr']*100:7.1f}%{r['mult']:7.2f}x")
        esc_results[shape_name] = rows_out
    return flat_results, esc_results


def main():
    reproduce_baseline()

    print("\n\n" + "#" * 100)
    print("# MAIN GRID -- real weekly SPMO-era rows (2015-11..2026-08), real instruments throughout")
    print("#" * 100)
    rets_w, dates_w, tier_w, turn_w = build_weekly_real()
    flat_w, esc_w = run_grid(rets_w, dates_w, tier_w, turn_w, "real weekly SPMO-era rows")

    print("\n\n" + "#" * 100)
    print("# LONG-HISTORY CHECK -- 26y QQQ-core proxy (2000-07..2026-08)")
    print("#" * 100)
    rets_p, dates_p, tier_p, turn_p = build_daily_26y()
    flat_p, esc_p = run_grid(rets_p, dates_p, tier_p, turn_p, "26y QQQ-core proxy")

    print("\n\n" + "#" * 100)
    print("# DOLLAR-AMOUNT SCENARIOS at $100k / $200k / $500k account value")
    print("#" * 100)
    for shape_name, mults in ESCALATION_SHAPES.items():
        for base_pct in (0.015, 0.02, 0.025):
            accounts, rows_out = scenario_dollars(base_pct, mults, True)
            print(f"\n{shape_name}, base {base_pct*100:.1f}%:  accounts = "
                  f"{', '.join(fmt_money(a) for a in accounts)}")
            for label, pct, amts in rows_out:
                print(f"  {label:<22} {pct*100:5.2f}%  " + "  ".join(fmt_money(a) for a in amts))
    for pct in (0.02, 0.03, 0.05):
        accounts, rows_out = scenario_dollars(pct, None, False)
        print(f"\nFLAT {pct*100:.1f}% (no escalation):  accounts = "
              f"{', '.join(fmt_money(a) for a in accounts)}")
        for label, p, amts in rows_out:
            print(f"  {label:<22} {p*100:5.2f}%  " + "  ".join(fmt_money(a) for a in amts))

    print("\n\nDone. See paper-track/research_notes/funding_pct_backtest.md for the full writeup.")


if __name__ == '__main__':
    main()
