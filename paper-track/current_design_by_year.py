"""Calendar-year return breakdown of the CURRENT live design (SPMO/GLD core +
TQQQ/QLD satellite + XLU state-E leg + BOXX cash + the A/D micro overlay,
target_weights_with_micro()), net of a 4bps one-way turnover cost, vs.
buy-and-hold SPMO, QQQ, and SPY -- same weekly clock, same data pipeline as
turnover_cost_model.py (which validated the micro overlay's cost-adjusted
edge). Supersedes calendar_year_report.py, which predates GLD, XLU, and the
micro overlay and is left in place only as history.
"""
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import (load_csv, compute_states, TARGET_WEIGHTS, CORE_SPMO_FRAC,
                    CORE_GLD_FRAC, target_weights_with_micro)
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
from four_leg_overlay import last_trading_day_per_week
from ma_window_sweep import compute_states_custom

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
CANDIDATES_DIR = 'data/defensive_candidates'
ONE_WAY_SPREAD_BPS = 0.0004


def nearest_prior(dmap, d, floor):
    dd = d
    while dd not in dmap and dd > floor:
        dd = (date.fromisoformat(dd) - timedelta(days=1)).isoformat()
    return dmap.get(dd)


def main():
    qqq_px = load_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    qqq_dates = sorted(qqq_px)
    macro_states = compute_states(qqq_dates, qqq_px)
    macro_by_date = dict(zip(qqq_dates, macro_states))
    micro_states = compute_states_custom(qqq_dates, qqq_px, 30, 150)
    micro_by_date = dict(zip(qqq_dates, micro_states))

    spmo = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPMO.csv')
    tqqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/TQQQ.csv')
    qld = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QLD.csv')
    xlu = load_daily_csv(f'{ROBINHOOD_REPO}/etf/XLU.csv')
    gld = load_daily_csv(f'{CANDIDATES_DIR}/GLD.csv')
    boxx = load_daily_csv(f'{ROBINHOOD_REPO}/etf/BOXX.csv')
    qqq_raw = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    spy = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPY.csv')
    tbill = load_tbill()
    all_dates = sorted(set(qqq_dates) | set(tqqq) | set(spmo) | set(qld) | set(xlu) | set(gld))
    cash_idx = build_cash_index(all_dates, boxx, tbill)

    spmo_wk = last_trading_day_per_week(sorted(set(spmo)))
    tqqq_wk = last_trading_day_per_week(sorted(set(tqqq)))
    qld_wk = last_trading_day_per_week(sorted(set(qld)))
    xlu_wk = last_trading_day_per_week(sorted(set(xlu)))
    gld_wk = last_trading_day_per_week(sorted(set(gld)))
    cash_wk = last_trading_day_per_week(sorted(set(cash_idx)))
    qqq_wk = last_trading_day_per_week(sorted(set(qqq_raw)))
    spy_wk = last_trading_day_per_week(sorted(set(spy)))
    keys = sorted(set(spmo_wk) & set(tqqq_wk) & set(qld_wk) & set(xlu_wk)
                  & set(gld_wk) & set(cash_wk) & set(qqq_wk) & set(spy_wk))
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
        y0, y1 = qqq_wk[k0], qqq_wk[k1]
        s0, s1 = spy_wk[k0], spy_wk[k1]
        sd = w0
        while sd not in macro_by_date and sd > floor:
            sd = (date.fromisoformat(sd) - timedelta(days=1)).isoformat()
        macro = macro_by_date.get(sd)
        micro = nearest_prior(micro_by_date, sd, floor)
        if macro is None or micro is None:
            continue
        r_core = CORE_SPMO_FRAC * (spmo[w1] / spmo[w0] - 1) + CORE_GLD_FRAC * (gld[g1] / gld[g0] - 1)
        r_tqqq = tqqq[t1] / tqqq[t0] - 1
        r_qld = qld[q1] / qld[q0] - 1
        r_xlu = xlu[x1] / xlu[x0] - 1
        r_cash = cash_idx[c1] / cash_idx[c0] - 1
        r_spmo_bh = spmo[w1] / spmo[w0] - 1
        r_qqq_bh = qqq_raw[y1] / qqq_raw[y0] - 1
        r_spy_bh = spy[s1] / spy[s0] - 1
        agree = micro in ('A', 'B')
        rows.append((w1, macro, agree, r_core, r_tqqq, r_qld, r_xlu, r_cash,
                     r_spmo_bh, r_qqq_bh, r_spy_bh))

    strat_net = []
    prev_w = None
    for r in rows:
        w1, st, agree, rc, rt, rq, rx, rca, _, _, _ = r
        w = target_weights_with_micro(st, agree)
        gross = w[0] * rc + w[1] * rt + w[2] * rq + w[3] * rx + w[4] * rca
        turnover = 0.0 if prev_w is None else sum(abs(w[i] - prev_w[i]) for i in range(5))
        strat_net.append(gross - ONE_WAY_SPREAD_BPS * turnover)
        prev_w = w

    weeks = [r[0] for r in rows]
    year_of = [w[:4] for w in weeks]
    spmo_bh = [r[8] for r in rows]
    qqq_bh = [r[9] for r in rows]
    spy_bh = [r[10] for r in rows]

    years = sorted(set(year_of))
    print(f"{'Year':<6}{'Strategy':>10}{'SPMO':>10}{'QQQ':>10}{'SPY':>10}{'n_weeks':>9}")
    print('-' * 55)

    cum = {k: 1.0 for k in ('strat', 'spmo', 'qqq', 'spy')}
    for y in years:
        idxs = [i for i, yy in enumerate(year_of) if yy == y]
        navs = {'strat': 1.0, 'spmo': 1.0, 'qqq': 1.0, 'spy': 1.0}
        series = {'strat': strat_net, 'spmo': spmo_bh, 'qqq': qqq_bh, 'spy': spy_bh}
        for k in navs:
            for i in idxs:
                navs[k] *= (1 + series[k][i])
            cum[k] *= navs[k]
        print(f"{y:<6}{(navs['strat']-1)*100:>9.1f}%{(navs['spmo']-1)*100:>9.1f}%"
              f"{(navs['qqq']-1)*100:>9.1f}%{(navs['spy']-1)*100:>9.1f}%{len(idxs):>9}")

    print('-' * 55)
    print(f"{'TOTAL':<6}{(cum['strat']-1)*100:>9.1f}%{(cum['spmo']-1)*100:>9.1f}%"
          f"{(cum['qqq']-1)*100:>9.1f}%{(cum['spy']-1)*100:>9.1f}%")


if __name__ == '__main__':
    main()
