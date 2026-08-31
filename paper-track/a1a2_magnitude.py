"""How big would the A1/A2 vol-substate be if applied to the CURRENT live
5-leg system (QLD in D, XLU in E intact), not the simplified 3-leg
comparison used in substate_v2_check.py? Only state A's weight is split;
every other state keeps its live TARGET_WEIGHTS.
"""
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import compute_states, TARGET_WEIGHTS
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
from four_leg_overlay import last_trading_day_per_week
from a1a2_deepdive import qqq_realized_vol_20d, rolling_percentile, nearest_prior

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
SEARCH_HOLDOUT_SPLIT = '2020-01-01'


def sharpe(rets):
    mean_r = sum(rets) / len(rets)
    var = sum((r - mean_r) ** 2 for r in rets) / (len(rets) - 1)
    vol = math.sqrt(var) * math.sqrt(52.1775)
    return (mean_r * 52.1775) / vol


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


def main():
    qqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    spmo = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPMO.csv')
    tqqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/TQQQ.csv')
    qld = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QLD.csv')
    xlu = load_daily_csv(f'{ROBINHOOD_REPO}/etf/XLU.csv')
    boxx = load_daily_csv(f'{ROBINHOOD_REPO}/etf/BOXX.csv')
    tbill = load_tbill()

    qqq_dates = sorted(qqq)
    states = compute_states(qqq_dates, qqq)
    state_by_date = dict(zip(qqq_dates, states))
    vol20 = qqq_realized_vol_20d(qqq, qqq_dates)
    vol_pct = rolling_percentile(vol20, qqq_dates, 252)

    all_dates = sorted(set(qqq) | set(tqqq) | set(spmo) | set(qld) | set(xlu))
    cash_idx = build_cash_index(all_dates, boxx, tbill)

    spmo_wk = last_trading_day_per_week(sorted(set(spmo)))
    tqqq_wk = last_trading_day_per_week(sorted(set(tqqq)))
    qld_wk = last_trading_day_per_week(sorted(set(qld)))
    xlu_wk = last_trading_day_per_week(sorted(set(xlu)))
    cash_wk = last_trading_day_per_week(sorted(set(cash_idx)))
    keys = sorted(set(spmo_wk) & set(tqqq_wk) & set(qld_wk) & set(xlu_wk) & set(cash_wk))
    keys = [k for k in keys if spmo_wk[k] >= '2015-11-02']

    rows = []
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        w0, w1 = spmo_wk[k0], spmo_wk[k1]
        t0, t1 = tqqq_wk[k0], tqqq_wk[k1]
        q0, q1 = qld_wk[k0], qld_wk[k1]
        x0, x1 = xlu_wk[k0], xlu_wk[k1]
        c0, c1 = cash_wk[k0], cash_wk[k1]
        sd = w0
        while sd not in state_by_date and sd > qqq_dates[0]:
            sd = (date.fromisoformat(sd) - timedelta(days=1)).isoformat()
        st = state_by_date.get(sd)
        if st is None:
            continue
        vp = nearest_prior(vol_pct, sd, qqq_dates[0])
        r_core = spmo[w1] / spmo[w0] - 1
        r_tqqq = tqqq[t1] / tqqq[t0] - 1
        r_qld = qld[q1] / qld[q0] - 1
        r_xlu = xlu[x1] / xlu[x0] - 1
        r_cash = cash_idx[c1] / cash_idx[c0] - 1
        rows.append((w1, st, r_core, r_tqqq, r_qld, r_xlu, r_cash, vp))

    def weekly_ret(row, a_split):
        w1, st, rc, rt, rq, rx, rca, vp = row
        if st == 'A' and a_split:
            cw, tw = (0.55, 0.45) if (vp is not None and vp < 0.75) else (0.85, 0.15)
            return cw * rc + tw * rt
        cw, tw, qw, xw, chw = TARGET_WEIGHTS[st]
        return cw * rc + tw * rt + qw * rq + xw * rx + chw * rca

    live_rets = [weekly_ret(r, False) for r in rows]
    sub_rets = [weekly_ret(r, True) for r in rows]
    weeks = [r[0] for r in rows]

    def year_returns(rets):
        yr = {}
        for w, r in zip(weeks, rets):
            yr.setdefault(w[:4], []).append(r)
        out = {}
        for y, rs in yr.items():
            nav = 1.0
            for r in rs:
                nav *= (1 + r)
            out[y] = nav - 1
        return out

    live_yr = year_returns(live_rets)
    sub_yr = year_returns(sub_rets)

    print(f"{'Year':<6}{'Live':>10}{'A1/A2':>10}{'Delta':>10}")
    for y in sorted(live_yr):
        d = sub_yr[y] - live_yr[y]
        print(f"{y:<6}{live_yr[y]*100:>9.1f}%{sub_yr[y]*100:>9.1f}%{d*100:>+9.2f}%")

    print()
    print(f"Full-timeline CAGR : live={cagr(live_rets)*100:.2f}%  A1/A2={cagr(sub_rets)*100:.2f}%  "
          f"delta={cagr(sub_rets)*100-cagr(live_rets)*100:+.2f}pp")
    nav_live = 1.0
    nav_sub = 1.0
    for r in live_rets: nav_live *= (1+r)
    for r in sub_rets: nav_sub *= (1+r)
    print(f"Cumulative (11yr)  : live={nav_live*100-100:.1f}%  A1/A2={nav_sub*100-100:.1f}%  "
          f"delta={(nav_sub-nav_live)*100:+.1f}pp")
    print(f"Sharpe             : live={sharpe(live_rets):.3f}  A1/A2={sharpe(sub_rets):.3f}  "
          f"delta={sharpe(sub_rets)-sharpe(live_rets):+.3f}")
    print(f"MaxDD              : live={mdd(live_rets)*100:.2f}%  A1/A2={mdd(sub_rets)*100:.2f}%  "
          f"delta={mdd(sub_rets)*100-mdd(live_rets)*100:+.2f}pp")

    # dollar terms on the actual account size
    acct = 76000
    print(f"\nOn a ~${acct:,} account, 11yr cumulative delta = ${(nav_sub-nav_live)*acct:,.0f} "
          f"(illustrative, not a real compounding projection -- account didn't exist for 11yrs)")


if __name__ == '__main__':
    main()
