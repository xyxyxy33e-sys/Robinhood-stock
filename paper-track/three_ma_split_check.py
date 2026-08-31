"""Does a third (faster) moving average add useful information beyond the
live 50/200 classifier? Tested by splitting state A (351 weeks, 60%+ of all
history) by whether price is also above/below its own 20-day MA (1%
hysteresis, same convention as the main classifier) -- the tractable version
of "relationship among three MAs": rather than redesigning the whole state
truth table (which would require re-validating every downstream weight),
this checks whether a fast MA usefully subdivides the SINGLE largest state.

Same discipline as every other substate check this session: grid search on
search-period weeks only (blind to holdout), cash fixed (here at 0, matching
live A's weight), isolated holdout comparison against live A weights (0.8
core / 0.2 tqqq).

RESULTS SUMMARY (run 2026-08-31): MIXED, not a clean win.
  - Above-20dma (302 of 351 A-weeks, the majority): search (blind, 117
    weeks) converges to 100% core / 0% TQQQ -- de-lever once price is
    ALREADY confirmed above its own 20dma, rather than adding more risk on
    top of an already-confirmed trend. This HOLDS UP on isolated holdout:
    Sharpe 1.051 vs live's 0.959 (185 holdout weeks, a real sample size).
    Not cherry-picked -- the search found it blind to the holdout outcome.
  - Below-20dma (49 of 351 A-weeks, a short pullback within the broader
    uptrend): search picks 50% TQQQ (2.5x live's weight) but this does NOT
    hold up -- holdout Sharpe 1.340 vs live's 1.555. Live wins here.

Net: one real, holdout-confirmed piece (de-lever on confirmed-strength A
weeks), one piece that fails validation. Not implemented -- a partial signal
like this, even where one half validates, is the same category of finding
as A1/A2 (paper-track/a1a2_deepdive.py): real but partial, and adopting only
the confirmed half in isolation risks the same overfitting this project has
disciplined itself against elsewhere. Would need the same robustness
treatment (parameter sensitivity across MA lengths/thresholds, confound
check against the existing A->D transition structure) before being trusted
further. No live weights changed.
"""
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import load_csv, sma, compute_states, TARGET_WEIGHTS, CORE_SPMO_FRAC, CORE_GLD_FRAC
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
from four_leg_overlay import last_trading_day_per_week

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
CANDIDATES_DIR = 'data/defensive_candidates'
SEARCH_HOLDOUT_SPLIT = '2020-01-01'
MIN_N = 15
FAST_MA = 20


def sharpe(rets):
    if len(rets) < 4:
        return None
    m = sum(rets) / len(rets)
    v = sum((r - m) ** 2 for r in rets) / (len(rets) - 1)
    if v <= 0:
        return None
    return (m * 52.1775) / (math.sqrt(v) * math.sqrt(52.1775))


def nearest_prior(dmap, d, floor):
    dd = d
    while dd not in dmap and dd > floor:
        dd = (date.fromisoformat(dd) - timedelta(days=1)).isoformat()
    return dmap.get(dd)


def main():
    qqq_px = load_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    qqq_dates = sorted(qqq_px)
    qqq_v = [qqq_px[d] for d in qqq_dates]
    states = compute_states(qqq_dates, qqq_px)
    state_by_date = dict(zip(qqq_dates, states))

    sig_fast = {}
    s_fast = None
    for i, d in enumerate(qqq_dates):
        m = sma(qqq_v, i, FAST_MA)
        if m is None:
            continue
        if qqq_v[i] > m * 1.01: s_fast = True
        elif qqq_v[i] < m * 0.99: s_fast = False
        if s_fast is not None:
            sig_fast[d] = s_fast

    spmo = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPMO.csv')
    tqqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/TQQQ.csv')
    qld = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QLD.csv')
    xlu = load_daily_csv(f'{ROBINHOOD_REPO}/etf/XLU.csv')
    gld = load_daily_csv(f'{CANDIDATES_DIR}/GLD.csv')
    boxx = load_daily_csv(f'{ROBINHOOD_REPO}/etf/BOXX.csv')
    tbill = load_tbill()
    all_dates = sorted(set(qqq_dates) | set(tqqq) | set(spmo) | set(qld) | set(xlu) | set(gld))
    cash_idx = build_cash_index(all_dates, boxx, tbill)

    spmo_wk = last_trading_day_per_week(sorted(set(spmo)))
    tqqq_wk = last_trading_day_per_week(sorted(set(tqqq)))
    qld_wk = last_trading_day_per_week(sorted(set(qld)))
    xlu_wk = last_trading_day_per_week(sorted(set(xlu)))
    gld_wk = last_trading_day_per_week(sorted(set(gld)))
    cash_wk = last_trading_day_per_week(sorted(set(cash_idx)))
    keys = sorted(set(spmo_wk) & set(tqqq_wk) & set(qld_wk) & set(xlu_wk) & set(gld_wk) & set(cash_wk))
    keys = [k for k in keys if spmo_wk[k] >= '2015-11-02']

    floor = qqq_dates[0]
    rows = []
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        w0, w1 = spmo_wk[k0], spmo_wk[k1]
        t0, t1 = tqqq_wk[k0], tqqq_wk[k1]
        q0, q1 = qld_wk[k0], qld_wk[k1]
        x0, x1 = xlu_wk[k0], xlu_wk[k1]
        g0, g1 = gld_wk[k0], gld_wk[k1]
        c0, c1 = cash_wk[k0], cash_wk[k1]
        sd = w0
        while sd not in state_by_date and sd > floor:
            sd = (date.fromisoformat(sd) - timedelta(days=1)).isoformat()
        st = state_by_date.get(sd)
        if st is None:
            continue
        sig = nearest_prior(sig_fast, sd, floor)
        r_core = CORE_SPMO_FRAC * (spmo[w1] / spmo[w0] - 1) + CORE_GLD_FRAC * (gld[g1] / gld[g0] - 1)
        r_tqqq = tqqq[t1] / tqqq[t0] - 1
        r_qld = qld[q1] / qld[q0] - 1
        r_xlu = xlu[x1] / xlu[x0] - 1
        r_cash = cash_idx[c1] / cash_idx[c0] - 1
        rows.append((w1, st, r_core, r_tqqq, r_qld, r_xlu, r_cash, sig))

    a_rows = [r for r in rows if r[1] == 'A' and r[7] is not None]
    a_above = [r for r in a_rows if r[7]]
    a_below = [r for r in a_rows if not r[7]]
    print(f"State A weeks: {len(a_rows)}  above-{FAST_MA}dma={len(a_above)}  below-{FAST_MA}dma={len(a_below)}")

    live_A = TARGET_WEIGHTS['A']
    for label, subset in (('above', a_above), ('below', a_below)):
        search = [r for r in subset if r[0] < SEARCH_HOLDOUT_SPLIT]
        holdout = [r for r in subset if r[0] >= SEARCH_HOLDOUT_SPLIT]
        print(f"  {label}-{FAST_MA}dma: n={len(subset)} search={len(search)} holdout={len(holdout)}")
        if len(search) < MIN_N or len(holdout) < 4:
            print("    INSUFFICIENT DATA")
            continue
        best = None
        for i in range(11):
            cw = round(i * 0.1, 2)
            tw = round(1 - cw, 2)
            rets = [cw * r[2] + tw * r[3] for r in search]
            sh = sharpe(rets)
            if sh is not None and (best is None or sh > best[2]):
                best = (cw, tw, sh)
        print(f"    search-optimal core/tqqq: {best[:2]}  search-Sharpe={best[2]:.3f}")
        hold_cand = [best[0] * r[2] + best[1] * r[3] for r in holdout]
        hold_live = [live_A[0] * r[2] + live_A[1] * r[3] for r in holdout]
        verdict = "HOLDS UP" if sharpe(hold_cand) > sharpe(hold_live) else "does NOT hold up"
        print(f"    holdout: candidate Sharpe={sharpe(hold_cand):.3f}  live(0.8/0.2) Sharpe={sharpe(hold_live):.3f}  [{verdict}]")


if __name__ == '__main__':
    main()
