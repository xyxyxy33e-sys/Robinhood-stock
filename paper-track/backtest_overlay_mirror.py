"""Full six-state overlay backtest using the SEC-verified stock-basket
mirror (top-15, proportional, weekly rebalanced) as the core leg -- the
actual live design -- vs. using the plain SPMO ETF as core (see
backtest_overlay_etf.py). Satellite = TQQQ, cash = BOXX/T-bill blend,
same six-state regime timing and TARGET_WEIGHTS for both.
"""
import csv
import math
import sys
from datetime import date

sys.path.insert(0, 'paper-track')
from state import compute_states, target_weights, validate_weights
from backtest_topn_weekly import load_holdings, load_prices as load_mirror_prices, holdings_for_date, top_n_weights
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index, weekly_fridays, buyhold

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'


def mirror_weekly_return(periods, mirror_px, w0, w1, n, scheme):
    d0 = date.fromisoformat(w0)
    rows = holdings_for_date(periods, d0)
    target = top_n_weights(rows, n, scheme)
    avail = {t: wt for t, wt in target.items()
             if w0 in mirror_px.get(t, {}) and w1 in mirror_px.get(t, {})
             and mirror_px[t][w0] > 0}
    if not avail:
        return None
    renorm = sum(avail.values())
    return sum((avail[t] / renorm) * (mirror_px[t][w1] / mirror_px[t][w0] - 1) for t in avail)


def metrics_from_navs(navs, used):
    n = len(navs) - 1
    years = n / 52.1775
    cagr = navs[-1] ** (1 / years) - 1
    rets = [navs[i + 1] / navs[i] - 1 for i in range(len(navs) - 1)]
    mean_r = sum(rets) / len(rets)
    var = sum((r - mean_r) ** 2 for r in rets) / (len(rets) - 1)
    vol = math.sqrt(var) * math.sqrt(52.1775)
    sharpe = (mean_r * 52.1775) / vol
    peak = navs[0]
    mdd = 0
    for v in navs:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    return dict(cagr=cagr, vol=vol, sharpe=sharpe, mdd=mdd, total=navs[-1] - 1,
                weeks=n, start=used[0], end=used[-1])


def iso_week_key(d):
    return date.fromisoformat(d).isocalendar()[:2]


def last_trading_day_per_week(dates):
    by_week = {}
    for d in dates:
        by_week[iso_week_key(d)] = d  # dates must be sorted ascending
    return by_week


def run_mirror_overlay(periods, mirror_px, qqq_daily, tqqq_daily, cash_idx, n, scheme):
    daily_dates = sorted(set(qqq_daily))
    states = compute_states(daily_dates, qqq_daily)
    state_by_date = dict(zip(daily_dates, states))

    mirror_weeks = sorted({w for sym in mirror_px for w in mirror_px[sym]})
    mirror_week_keys = {iso_week_key(w): w for w in mirror_weeks}

    tqqq_by_week = last_trading_day_per_week(sorted(set(tqqq_daily)))
    cash_by_week = last_trading_day_per_week(sorted(set(cash_idx)))

    common_keys = sorted(set(mirror_week_keys) & set(tqqq_by_week) & set(cash_by_week))
    common_keys = [k for k in common_keys if mirror_week_keys[k] >= '2015-11-02']

    nav = 1.0
    navs = [nav]
    used = [mirror_week_keys[common_keys[0]]]
    state_weeks = {}
    skipped = 0
    for i in range(len(common_keys) - 1):
        k0, k1 = common_keys[i], common_keys[i + 1]
        w0, w1 = mirror_week_keys[k0], mirror_week_keys[k1]
        d0, d1 = tqqq_by_week[k0], tqqq_by_week[k1]
        c0, c1 = cash_by_week[k0], cash_by_week[k1]

        state_day = d0
        while state_day not in state_by_date and state_day > daily_dates[0]:
            state_day = (date.fromisoformat(state_day) - __import__('datetime').timedelta(days=1)).isoformat()
        st = state_by_date.get(state_day)
        if st is None:
            navs.append(nav)
            used.append(w1)
            continue
        core_w, sat_w, cash_w = target_weights(st)
        validate_weights(st, core_w, sat_w, cash_w)

        r_core = mirror_weekly_return(periods, mirror_px, w0, w1, n, scheme)
        if r_core is None:
            skipped += 1
            navs.append(nav)
            used.append(w1)
            continue
        r_sat = tqqq_daily[d1] / tqqq_daily[d0] - 1
        r_cash = cash_idx[c1] / cash_idx[c0] - 1

        wk_ret = core_w * r_core + sat_w * r_sat + cash_w * r_cash
        nav *= (1 + wk_ret)
        navs.append(nav)
        used.append(w1)
        state_weeks[st] = state_weeks.get(st, 0) + 1

    m = metrics_from_navs(navs, used)
    m['skipped'] = skipped
    m['state_weeks'] = state_weeks
    return m


def main():
    periods = load_holdings()
    mirror_px = load_mirror_prices()
    qqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    tqqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/TQQQ.csv')
    spmo = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPMO.csv')
    boxx = load_daily_csv(f'{ROBINHOOD_REPO}/etf/BOXX.csv')
    tbill = load_tbill()
    all_dates = sorted(set(qqq) | set(tqqq) | set(spmo))
    cash_idx = build_cash_index(all_dates, boxx, tbill)

    print(f"{'Config':<32} {'CAGR':>8} {'Vol':>7} {'Sharpe':>7} {'MaxDD':>8} {'TotalRet':>10} {'wks':>5} {'skip':>5}")
    print('-' * 90)

    r15 = run_mirror_overlay(periods, mirror_px, qqq, tqqq, cash_idx, 15, 'proportional')
    print(f"{'Overlay: mirror-15 core':<32} {r15['cagr']*100:>7.2f}% {r15['vol']*100:>6.2f}% {r15['sharpe']:>7.3f} {r15['mdd']*100:>7.2f}% {r15['total']*100:>9.1f}% {r15['weeks']:>5} {r15['skipped']:>5}")
    print('  state-weeks:', r15['state_weeks'])

    r5 = run_mirror_overlay(periods, mirror_px, qqq, tqqq, cash_idx, 5, 'proportional')
    print(f"{'Overlay: mirror-5 core':<32} {r5['cagr']*100:>7.2f}% {r5['vol']*100:>6.2f}% {r5['sharpe']:>7.3f} {r5['mdd']*100:>7.2f}% {r5['total']*100:>9.1f}% {r5['weeks']:>5} {r5['skipped']:>5}")

    r25 = run_mirror_overlay(periods, mirror_px, qqq, tqqq, cash_idx, 25, 'proportional')
    print(f"{'Overlay: mirror-25 core':<32} {r25['cagr']*100:>7.2f}% {r25['vol']*100:>6.2f}% {r25['sharpe']:>7.3f} {r25['mdd']*100:>7.2f}% {r25['total']*100:>9.1f}% {r25['weeks']:>5} {r25['skipped']:>5}")


if __name__ == '__main__':
    main()
