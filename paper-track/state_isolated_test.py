"""Shared harness for per-state isolated portfolio research -- built
2026-09-01 so multiple parallel (subagent) investigations of "what should
this ONE state's weights be" all use identical, disciplined methodology,
after per-state free optimization already failed badly once in this
project (states C/E collapsed to corner-solution artifacts on 10-13 week
samples; state F's holdout Sharpe fell off a cliff from 3.81 search to
0.058 holdout -- see STRATEGY.md's "Gold: from core-blend to standalone
top-slice" section).

Guardrails baked in, not optional:
  - Only that state's own (discontiguous) weeks are used -- isolated_state_
    validation.py's convention, no anchoring to the rest of the portfolio.
  - ALWAYS search/holdout split at 2020-01-01 and report BOTH -- a result
    that only looks good on search is not a result.
  - Sample size (n_search, n_holdout) is returned with every result --
    treat anything under ~20 weeks per half as low-confidence regardless
    of how good the Sharpe looks.
  - No free-floating cash: when testing a candidate SLOT (adding a new
    instrument), it always trades off against the state's EXISTING legs
    proportionally (same mechanism as the standalone gold slot), never
    against an unconstrained cash residual -- this is what prevents the
    near-zero-variance-cash corner-solution artifact that hit states C/E
    in the free per-state gold search.

Usage (import, don't run standalone):

    from state_isolated_test import load_state_weeks, sharpe, cagr, mdd, \
        test_slot, test_weight_shift, CANDIDATES

    weeks = load_state_weeks('B')   # that state's own (date, leg_rets dict) rows
    test_slot(weeks, base_weights, 'btal', frac_grid=[0,0.1,0.2,0.3])
"""
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import load_csv, compute_states, TARGET_WEIGHTS
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
from four_leg_overlay import last_trading_day_per_week

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
CANDIDATES_DIR = 'data/defensive_candidates'
SPLIT = '2020-01-01'

# Every candidate instrument with full 2015-2026 cached data, EXCLUDING gold
# (GLD/IAU) -- explicitly out of scope per user instruction 2026-09-01.
CANDIDATES = {
    'btal': 'BTAL.csv',    # anti-beta long/short -- structural equity hedge, own return -38.7% over the period
    'kmlm': 'KMLM.csv',    # managed futures / trend-following -- "crisis alpha" by construction
    'uup':  'UUP.csv',     # dollar index bull -- different macro factor (USD strength) than equities/rates/gold
    'vixy': 'VIXY.csv',    # long VIX futures -- convex crash protection, severe structural decay in calm markets
    'tail': 'TAIL.csv',    # Cambria tail-risk ETF -- OTM SPX puts + treasuries, designed explicitly for crash convexity
    'moat': 'MOAT.csv',    # VanEck Morningstar Wide Moat -- quality/moat equity factor
    'qual': 'QUAL.csv',    # iShares MSCI USA Quality Factor
    'splv': 'SPLV.csv',    # Invesco S&P 500 Low Volatility
    'dbc':  'DBC.csv',     # broad commodities (already tested flat-20%, weaker than gold/BTAL -- included for per-state re-check)
    'tlt':  'TLT.csv',     # 20+yr Treasuries (already tested flat-20%, failed badly -- included for per-state re-check, low prior)
}

_CACHE = {}


def _load_all():
    if _CACHE:
        return _CACHE
    qqq_px = load_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    qqq_dates = sorted(qqq_px)
    macro_states = compute_states(qqq_dates, qqq_px)
    macro_by_date = dict(zip(qqq_dates, macro_states))

    spmo = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPMO.csv')
    tqqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/TQQQ.csv')
    qld = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QLD.csv')
    xlu = load_daily_csv(f'{ROBINHOOD_REPO}/etf/XLU.csv')
    boxx = load_daily_csv(f'{ROBINHOOD_REPO}/etf/BOXX.csv')
    tbill = load_tbill()

    cand_px = {}
    for name, fname in CANDIDATES.items():
        cand_px[name] = load_daily_csv(f'{CANDIDATES_DIR}/{fname}')

    all_dates = sorted(set(qqq_dates) | set(tqqq) | set(spmo) | set(qld) | set(xlu)
                        | set.union(*[set(v) for v in cand_px.values()]))
    cash_idx = build_cash_index(all_dates, boxx, tbill)

    spmo_wk = last_trading_day_per_week(sorted(set(spmo)))
    tqqq_wk = last_trading_day_per_week(sorted(set(tqqq)))
    qld_wk = last_trading_day_per_week(sorted(set(qld)))
    xlu_wk = last_trading_day_per_week(sorted(set(xlu)))
    cash_wk = last_trading_day_per_week(sorted(set(cash_idx)))
    cand_wk = {name: last_trading_day_per_week(sorted(set(px))) for name, px in cand_px.items()}

    key_sets = [set(spmo_wk), set(tqqq_wk), set(qld_wk), set(xlu_wk), set(cash_wk)]
    key_sets += [set(cand_wk[c]) for c in CANDIDATES]
    keys = sorted(set.intersection(*key_sets))
    keys = [k for k in keys if spmo_wk[k] >= '2015-11-02']
    floor = qqq_dates[0]

    rows = []
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        w0, w1 = spmo_wk[k0], spmo_wk[k1]
        t0, t1 = tqqq_wk[k0], tqqq_wk[k1]
        q0, q1 = qld_wk[k0], qld_wk[k1]
        x0, x1 = xlu_wk[k0], xlu_wk[k1]
        c0, c1 = cash_wk[k0], cash_wk[k1]
        sd = w0
        while sd not in macro_by_date and sd > floor:
            sd = (date.fromisoformat(sd) - timedelta(days=1)).isoformat()
        macro = macro_by_date.get(sd)
        if macro is None:
            continue
        leg_rets = {
            'spmo': spmo[w1] / spmo[w0] - 1,
            'tqqq': tqqq[t1] / tqqq[t0] - 1,
            'qld': qld[q1] / qld[q0] - 1,
            'xlu': xlu[x1] / xlu[x0] - 1,
            'cash': cash_idx[c1] / cash_idx[c0] - 1,
        }
        for name in CANDIDATES:
            ck0, ck1 = cand_wk[name][k0], cand_wk[name][k1]
            leg_rets[name] = cand_px[name][ck1] / cand_px[name][ck0] - 1
        rows.append((w1, macro, leg_rets))
    _CACHE['rows'] = rows
    return _CACHE


def load_state_weeks(state_letter):
    """All (date, leg_rets) rows where the MACRO state (plain TARGET_WEIGHTS
    classifier, no micro overlay -- that's a separate refinement, out of
    scope here) equals state_letter. leg_rets is a dict with keys
    'spmo','tqqq','qld','xlu','cash' plus every name in CANDIDATES."""
    rows = _load_all()['rows']
    return [(w1, leg_rets) for (w1, st, leg_rets) in rows if st == state_letter]


def sharpe(rets):
    if len(rets) < 4:
        return None
    m = sum(rets) / len(rets)
    v = sum((r - m) ** 2 for r in rets) / (len(rets) - 1)
    if v <= 0:
        return None
    return (m * 52.1775) / (math.sqrt(v) * math.sqrt(52.1775))


def cagr(rets):
    if not rets:
        return None
    nav = 1.0
    for r in rets:
        nav *= (1 + r)
    return nav ** (1 / (len(rets) / 52.1775)) - 1


def mdd(rets):
    nav = 1.0
    peak = 1.0
    m = 0.0
    for r in rets:
        nav *= (1 + r)
        peak = max(peak, nav)
        m = min(m, nav / peak - 1)
    return m


def split_weeks(weeks):
    search = [(d, r) for d, r in weeks if d < SPLIT]
    holdout = [(d, r) for d, r in weeks if d >= SPLIT]
    return search, holdout


def base_ret(w5, leg_rets):
    """w5: (core, tqqq, qld, xlu, cash) -- core trades as SPMO (pure, no gold)."""
    core_w, tqqq_w, qld_w, xlu_w, cash_w = w5
    return (core_w * leg_rets['spmo'] + tqqq_w * leg_rets['tqqq'] + qld_w * leg_rets['qld']
            + xlu_w * leg_rets['xlu'] + cash_w * leg_rets['cash'])


def slot_ret(w5, frac, candidate, leg_rets):
    """Add `candidate` as a top-slice at `frac`, scaling the existing 5 legs
    down proportionally -- same mechanism validated for the (now-removed)
    gold overlay. NEVER trades off against free cash alone."""
    core_w, tqqq_w, qld_w, xlu_w, cash_w = [x * (1 - frac) for x in w5]
    return (core_w * leg_rets['spmo'] + frac * leg_rets[candidate] + tqqq_w * leg_rets['tqqq']
            + qld_w * leg_rets['qld'] + xlu_w * leg_rets['xlu'] + cash_w * leg_rets['cash'])


def test_slot(weeks, base_w5, candidate, frac_grid=(0.0, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4)):
    """Search/holdout test of adding `candidate` as a top-slice to this
    state's base weights, across frac_grid. Returns dict with search curve,
    best fraction on search, and that fraction's holdout confirmation.
    NOTE: does not itself flag corner solutions or thin samples -- caller
    must check n_search/n_holdout and eyeball the curve shape (grid-edge
    "best" values are a red flag, same as the free gold-weight search that
    failed for states C/E/F)."""
    search, holdout = split_weeks(weeks)
    curve = []
    best_f, best_sh = None, -999
    for f in frac_grid:
        rets = [slot_ret(base_w5, f, candidate, lr) for _, lr in search]
        sh = sharpe(rets)
        curve.append((f, sh))
        if sh is not None and sh > best_sh:
            best_sh, best_f = sh, f
    holdout_rets_best = [slot_ret(base_w5, best_f, candidate, lr) for _, lr in holdout]
    holdout_rets_zero = [slot_ret(base_w5, 0.0, candidate, lr) for _, lr in holdout]
    return {
        'candidate': candidate,
        'n_search': len(search), 'n_holdout': len(holdout),
        'search_curve': curve,
        'best_frac': best_f, 'best_search_sharpe': best_sh,
        'holdout_sharpe_at_best': sharpe(holdout_rets_best),
        'holdout_sharpe_at_zero': sharpe(holdout_rets_zero),
        'holdout_cagr_at_best': cagr(holdout_rets_best),
        'holdout_cagr_at_zero': cagr(holdout_rets_zero),
    }


def test_weight_shift(weeks, candidate_w5_grid, label_fn=None):
    """Search/holdout test of shifting the (core,tqqq,qld,xlu,cash) weights
    within the CURRENT mix (no new instrument) -- candidate_w5_grid is a
    list of 5-tuples that each sum to 1.0. Returns best-on-search plus its
    holdout confirmation, same discipline as test_slot."""
    search, holdout = split_weeks(weeks)
    curve = []
    best_w, best_sh = None, -999
    for w5 in candidate_w5_grid:
        assert abs(sum(w5) - 1.0) < 0.005, f"weights {w5} don't sum to 1.0"
        rets = [base_ret(w5, lr) for _, lr in search]
        sh = sharpe(rets)
        curve.append((w5, sh))
        if sh is not None and sh > best_sh:
            best_sh, best_w = sh, w5
    holdout_rets_best = [base_ret(best_w, lr) for _, lr in holdout]
    return {
        'n_search': len(search), 'n_holdout': len(holdout),
        'search_curve': curve,
        'best_w5': best_w, 'best_search_sharpe': best_sh,
        'holdout_sharpe_at_best': sharpe(holdout_rets_best),
        'holdout_cagr_at_best': cagr(holdout_rets_best),
    }


if __name__ == '__main__':
    # smoke test
    for st in 'ABCDEF':
        weeks = load_state_weeks(st)
        s, h = split_weeks(weeks)
        print(f"state {st}: {len(weeks)} total weeks ({len(s)} search, {len(h)} holdout)")
