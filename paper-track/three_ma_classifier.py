"""A genuine three-MA regime classifier (not the letter-reuse trick from
ma_window_sweep.py) -- tests whether three MAs produce meaningfully finer,
still-tradeable regimes than the current 50/200 six-state design.

Construction (F=fast, M=medium, S=slow periods, 1% hysteresis matching the
main classifier's convention):
  STACK    = 'bull' if F-MA > M-MA > S-MA, 'bear' if F-MA < M-MA < S-MA,
             else 'mixed' (the MAs are tangled -- a transitional/choppy
             signal the 2-MA design can't see at all).
  POSITION = 'above' if price > max(F,M,S)-MA, 'below' if price <
             min(F,M,S)-MA, else 'between' (price has pierced some but not
             all of the stack).
  state = (STACK, POSITION) -- up to 9 cells, empirically fewer populated.

For each populated cell with enough sample (MIN_N=15 in both search and
holdout), grid-search its own (core, tqqq, qld, xlu, cash) weight on
search-period (pre-2020) weeks ALONE (blind to holdout), same discipline as
every other search this session. Evaluate isolated holdout Sharpe/return
against what the CURRENT LIVE 50/200 strategy would have earned on those
EXACT SAME weeks (apples-to-apples: same calendar weeks, old vs new
classification). Thin cells get the live-baseline weight by default, not a
search result.

RESULTS SUMMARY (run 2026-08-31): REJECTED, both triples, on the cleanest
possible disqualifying signal -- search-period Sharpe jumps hugely (1.090
-> 2.106 for 10/50/100, -> 1.821 for 50/100/200) while HOLDOUT Sharpe gets
WORSE than the simple 50/200 baseline (1.174 -> 0.952 and -> 0.998
respectively), not better. That search-up/holdout-down pattern is the
textbook overfitting signature this project has flagged as disqualifying
everywhere else it appears (the original joint 6-state grid search,
several rejected substates) -- splitting into 5-6 independently-weighted
cells means each is fit on a much smaller search sample (27-99 weeks vs.
the full state's few hundred), so each cell's "optimum" is more likely
noise that doesn't repeat out of sample. Full-timeline CAGR also drops
hard either way (25.46% -> ~18%), and 10/50/100 more than triples the
transition rate (27.5/yr vs 8.6/yr). Note: an earlier version of this
script searched cash freely and collapsed to the degenerate 100%-cash
corner in every single cell (the standard artifact -- near-zero variance
trivially wins a small-sample Sharpe objective) -- fixed by anchoring each
cell's cash weight to what the OLD classifier held on average across that
cell's own weeks, not searching it. No live weights changed.
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
STEP = 0.1


def sharpe(rets):
    if len(rets) < 4:
        return None
    m = sum(rets) / len(rets)
    v = sum((r - m) ** 2 for r in rets) / (len(rets) - 1)
    if v <= 0:
        return None
    return (m * 52.1775) / (math.sqrt(v) * math.sqrt(52.1775))


def cagr(rets):
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


def nearest_prior(dmap, d, floor):
    dd = d
    while dd not in dmap and dd > floor:
        dd = (date.fromisoformat(dd) - timedelta(days=1)).isoformat()
    return dmap.get(dd)


def compute_three_ma_regime(dates, px, f_n, m_n, s_n, buf=0.01):
    v = [px[d] for d in dates]
    stack_state = None
    pos_state = None
    out = {}
    for i, d in enumerate(dates):
        mf, mm, ms = sma(v, i, f_n), sma(v, i, m_n), sma(v, i, s_n)
        if ms is None:
            continue
        # stack, with hysteresis on the two defining gaps
        bull_gap = (mf - mm) / mm
        bear_gap = (mm - ms) / ms
        if mf > mm * (1 + buf) and mm > ms * (1 + buf):
            stack_state = 'bull'
        elif mf < mm * (1 - buf) and mm < ms * (1 - buf):
            stack_state = 'bear'
        elif stack_state is None:
            stack_state = 'mixed'
        else:
            # only flip out of bull/bear if clearly no longer that stack
            if stack_state == 'bull' and not (mf > mm and mm > ms):
                stack_state = 'mixed'
            elif stack_state == 'bear' and not (mf < mm and mm < ms):
                stack_state = 'mixed'
            elif stack_state == 'mixed' and mf > mm * (1 + buf) and mm > ms * (1 + buf):
                stack_state = 'bull'
            elif stack_state == 'mixed' and mf < mm * (1 - buf) and mm < ms * (1 - buf):
                stack_state = 'bear'

        hi, lo = max(mf, mm, ms), min(mf, mm, ms)
        if v[i] > hi * (1 + buf):
            pos_state = 'above'
        elif v[i] < lo * (1 - buf):
            pos_state = 'below'
        elif pos_state is None or (lo * (1 - buf) <= v[i] <= hi * (1 + buf)):
            pos_state = 'between'

        out[d] = (stack_state, pos_state)
    return out


def main(f_n, m_n, s_n):
    qqq_px = load_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    qqq_dates = sorted(qqq_px)
    old_states = compute_states(qqq_dates, qqq_px)
    old_state_by_date = dict(zip(qqq_dates, old_states))
    new_regime = compute_three_ma_regime(qqq_dates, qqq_px, f_n, m_n, s_n)

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
        while sd not in old_state_by_date and sd > floor:
            sd = (date.fromisoformat(sd) - timedelta(days=1)).isoformat()
        old_st = old_state_by_date.get(sd)
        regime = nearest_prior(new_regime, sd, floor)
        if old_st is None or regime is None:
            continue
        r_core = CORE_SPMO_FRAC * (spmo[w1] / spmo[w0] - 1) + CORE_GLD_FRAC * (gld[g1] / gld[g0] - 1)
        r_tqqq = tqqq[t1] / tqqq[t0] - 1
        r_qld = qld[q1] / qld[q0] - 1
        r_xlu = xlu[x1] / xlu[x0] - 1
        r_cash = cash_idx[c1] / cash_idx[c0] - 1
        rows.append((w1, old_st, regime, r_core, r_tqqq, r_qld, r_xlu, r_cash))

    print(f"\n===== {f_n}/{m_n}/{s_n} =====")
    occ = {}
    for r in rows:
        occ[r[2]] = occ.get(r[2], 0) + 1
    print("Cell occupancy:", {f"{k[0]}/{k[1]}": v for k, v in sorted(occ.items(), key=lambda x: -x[1])})

    def old_baseline_weight(old_st):
        return TARGET_WEIGHTS[old_st]

    def grid_search_cell(search_rows, cash_fixed):
        """Cash is FIXED, not searched -- searching it freely collapses to the
        degenerate 100%-cash corner (near-zero variance trivially wins Sharpe
        regardless of real opportunity cost), the same artifact this project
        has caught and rejected everywhere else it appears. cash_fixed is set
        per-cell to what the OLD classifier would have held on average across
        that cell's own weeks -- a reasonable, non-search-gamed anchor."""
        budget = round(1 - cash_fixed, 6)
        best = (None,) * 4 + (-1e9,)
        n = round(budget / STEP + 1e-9) if budget > 1e-9 else 0
        for i in range(n + 1):
            cw = round(i * STEP, 4)
            for j in range(n + 1 - i):
                tw = round(j * STEP, 4)
                for k in range(n + 1 - i - j):
                    qw = round(k * STEP, 4)
                    xw = round(budget - cw - tw - qw, 4)
                    if xw < -1e-9:
                        continue
                    rets = [cw * r[3] + tw * r[4] + qw * r[5] + xw * r[6] + cash_fixed * r[7] for r in search_rows]
                    sh = sharpe(rets)
                    if sh is not None and sh > best[4]:
                        best = (cw, tw, qw, xw, sh)
        return (*best[:4], cash_fixed, best[4])

    new_weights = {}
    for cell in occ:
        cell_rows = [r for r in rows if r[2] == cell]
        search = [r for r in cell_rows if r[0] < SEARCH_HOLDOUT_SPLIT]
        holdout = [r for r in cell_rows if r[0] >= SEARCH_HOLDOUT_SPLIT]
        if len(search) < MIN_N or len(holdout) < MIN_N:
            print(f"  {cell[0]}/{cell[1]}: n={len(cell_rows)} search={len(search)} holdout={len(holdout)} -- too thin, using old-classifier weight per-week")
            continue
        cash_fixed = round(sum(old_baseline_weight(r[1])[4] for r in cell_rows) / len(cell_rows), 2)
        best = grid_search_cell(search, cash_fixed)
        old_rets_holdout = [old_baseline_weight(r[1])[0] * r[3] + old_baseline_weight(r[1])[1] * r[4]
                             + old_baseline_weight(r[1])[2] * r[5] + old_baseline_weight(r[1])[3] * r[6]
                             + old_baseline_weight(r[1])[4] * r[7] for r in holdout]
        new_rets_holdout = [best[0] * r[3] + best[1] * r[4] + best[2] * r[5] + best[3] * r[6] + best[4] * r[7] for r in holdout]
        print(f"  {cell[0]}/{cell[1]}: n={len(cell_rows)} search={len(search)} holdout={len(holdout)}  "
              f"search-best={best[:5]}  holdout Sharpe: new={sharpe(new_rets_holdout)}  old-classifier-weight={sharpe(old_rets_holdout)}")
        new_weights[cell] = best[:5]

    # full-timeline comparison: new classifier (searched weight where available, else old
    # classifier's own weight for that week) vs old classifier throughout
    old_rets, new_rets = [], []
    for r in rows:
        ow = old_baseline_weight(r[1])
        old_rets.append(ow[0] * r[3] + ow[1] * r[4] + ow[2] * r[5] + ow[3] * r[6] + ow[4] * r[7])
        nw = new_weights.get(r[2], ow)
        new_rets.append(nw[0] * r[3] + nw[1] * r[4] + nw[2] * r[5] + nw[3] * r[6] + nw[4] * r[7])

    weeks = [r[0] for r in rows]
    pre = [i for i, w in enumerate(weeks) if w < SEARCH_HOLDOUT_SPLIT]
    post = [i for i, w in enumerate(weeks) if w >= SEARCH_HOLDOUT_SPLIT]
    print(f"\n  FULL-TIMELINE: old(50/200) Sharpe={sharpe(old_rets):.3f} CAGR={cagr(old_rets)*100:.2f}% MaxDD={mdd(old_rets)*100:.2f}%")
    print(f"                 new(3-MA)   Sharpe={sharpe(new_rets):.3f} CAGR={cagr(new_rets)*100:.2f}% MaxDD={mdd(new_rets)*100:.2f}%")
    print(f"  search-period: old={sharpe([old_rets[i] for i in pre]):.3f}  new={sharpe([new_rets[i] for i in pre]):.3f}")
    print(f"  holdout      : old={sharpe([old_rets[i] for i in post]):.3f}  new={sharpe([new_rets[i] for i in post]):.3f}")

    # turnover
    cells_seq = [r[2] for r in rows]
    transitions = sum(1 for i in range(1, len(cells_seq)) if cells_seq[i] != cells_seq[i-1])
    old_seq = [r[1] for r in rows]
    old_transitions = sum(1 for i in range(1, len(old_seq)) if old_seq[i] != old_seq[i-1])
    print(f"  transitions: old={old_transitions} ({old_transitions/(len(rows)/52.1775):.1f}/yr)  new={transitions} ({transitions/(len(rows)/52.1775):.1f}/yr)")


if __name__ == '__main__':
    main(10, 50, 100)
    main(50, 100, 200)
