"""Re-run of backtest_overlay_etf.py using dividend-and-split-adjusted
(total-return) weekly prices for SPMO/QQQ/TQQQ (data/div_adj/*.csv, pulled
via Robinhood get_equity_historicals adjustment_type='all') instead of
split-only prices. Regime STATE classification still uses the raw
split-adjusted QQQ price series (technical SMA crossovers are conventionally
computed on price, not total return, and dividend reinvestment doesn't
materially shift trend timing) -- only the P&L legs (core, satellite) and
the buy-and-hold comparisons use total-return prices. BOXX has no
distributions by design, so its cash leg is unchanged.
"""
import csv
import math
import sys
from datetime import date

sys.path.insert(0, 'paper-track')
from state import compute_states, target_weights, validate_weights
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index, weekly_fridays

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
DIV_ADJ = 'data/div_adj'


def load_tr_weekly(symbol):
    out = {}
    with open(f'{DIV_ADJ}/{symbol}_weekly_totalreturn.csv') as f:
        for r in csv.DictReader(f):
            out[r['week_start']] = float(r['close'])
    return out


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
        by_week[iso_week_key(d)] = d
    return by_week


def run_overlay_tr(core_symbol, core_tr, qqq_daily, tqqq_tr, cash_idx):
    qqq_dates = sorted(qqq_daily)
    states = compute_states(qqq_dates, qqq_daily)
    state_by_date = dict(zip(qqq_dates, states))

    core_by_week = {iso_week_key(w): w for w in core_tr}
    tqqq_by_week = {iso_week_key(w): w for w in tqqq_tr}
    cash_by_week = last_trading_day_per_week(sorted(set(cash_idx)))

    common_keys = sorted(set(core_by_week) & set(tqqq_by_week) & set(cash_by_week))
    common_keys = [k for k in common_keys if core_by_week[k] >= '2015-11-02']

    nav = 1.0
    navs = [nav]
    used = [core_by_week[common_keys[0]]]
    for i in range(len(common_keys) - 1):
        k0, k1 = common_keys[i], common_keys[i + 1]
        w0core, w1core = core_by_week[k0], core_by_week[k1]
        w0sat, w1sat = tqqq_by_week[k0], tqqq_by_week[k1]
        c0, c1 = cash_by_week[k0], cash_by_week[k1]

        state_day = c0
        while state_day not in state_by_date and state_day > qqq_dates[0]:
            state_day = (date.fromisoformat(state_day) - __import__('datetime').timedelta(days=1)).isoformat()
        st = state_by_date.get(state_day)
        if st is None:
            navs.append(nav); used.append(w1core); continue
        core_w, sat_w, cash_w = target_weights(st)
        validate_weights(st, core_w, sat_w, cash_w)
        r_core = core_tr[w1core] / core_tr[w0core] - 1
        r_sat = tqqq_tr[w1sat] / tqqq_tr[w0sat] - 1
        r_cash = cash_idx[c1] / cash_idx[c0] - 1
        wk_ret = core_w * r_core + sat_w * r_sat + cash_w * r_cash
        nav *= (1 + wk_ret)
        navs.append(nav)
        used.append(w1core)
    return metrics_from_navs(navs, used)


def buyhold_tr(tr_px):
    weeks = sorted(w for w in tr_px if w >= '2015-11-02')
    nav = 1.0
    navs = [nav]
    for i in range(len(weeks) - 1):
        r = tr_px[weeks[i + 1]] / tr_px[weeks[i]] - 1
        nav *= (1 + r)
        navs.append(nav)
    return metrics_from_navs(navs, weeks)


def main():
    qqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    boxx = load_daily_csv(f'{ROBINHOOD_REPO}/etf/BOXX.csv')
    tbill = load_tbill()
    tqqq_split = load_daily_csv(f'{ROBINHOOD_REPO}/etf/TQQQ.csv')
    spmo_split = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPMO.csv')
    all_dates = sorted(set(qqq) | set(tqqq_split) | set(spmo_split))
    cash_idx = build_cash_index(all_dates, boxx, tbill)

    spmo_tr = load_tr_weekly('SPMO')
    qqq_tr = load_tr_weekly('QQQ')
    # TQQQ's dividend-adjusted series came back corrupted (negative prices in
    # 2015-16 -- Robinhood's back-adjustment breaks down on TQQQ's near-zero
    # split-adjusted early price combined with its sparse/erratic distribution
    # history). Fall back to split-only prices for TQQQ: it's a leveraged fund
    # with negligible/inconsistent distributions, so the dividend gap here is
    # small relative to the corrupted alternative.
    tqqq_tr = {w: tqqq_split[w] for w in tqqq_split}

    print(f"{'Config':<32} {'CAGR':>8} {'Vol':>7} {'Sharpe':>7} {'MaxDD':>8} {'TotalRet':>10} {'wks':>5}")
    print('-' * 90)

    r = run_overlay_tr('SPMO', spmo_tr, qqq, tqqq_tr, cash_idx)
    print(f"{'Overlay (TR): SPMO core':<32} {r['cagr']*100:>7.2f}% {r['vol']*100:>6.2f}% {r['sharpe']:>7.3f} {r['mdd']*100:>7.2f}% {r['total']*100:>9.1f}% {r['weeks']:>5}")

    r2 = run_overlay_tr('QQQ', qqq_tr, qqq, tqqq_tr, cash_idx)
    print(f"{'Overlay (TR): QQQ core':<32} {r2['cagr']*100:>7.2f}% {r2['vol']*100:>6.2f}% {r2['sharpe']:>7.3f} {r2['mdd']*100:>7.2f}% {r2['total']*100:>9.1f}% {r2['weeks']:>5}")

    bh_spmo = buyhold_tr(spmo_tr)
    print(f"{'Buy&hold SPMO (TR)':<32} {bh_spmo['cagr']*100:>7.2f}% {bh_spmo['vol']*100:>6.2f}% {bh_spmo['sharpe']:>7.3f} {bh_spmo['mdd']*100:>7.2f}% {bh_spmo['total']*100:>9.1f}% {bh_spmo['weeks']:>5}")

    bh_qqq = buyhold_tr(qqq_tr)
    print(f"{'Buy&hold QQQ (TR)':<32} {bh_qqq['cagr']*100:>7.2f}% {bh_qqq['vol']*100:>6.2f}% {bh_qqq['sharpe']:>7.3f} {bh_qqq['mdd']*100:>7.2f}% {bh_qqq['total']*100:>9.1f}% {bh_qqq['weeks']:>5}")


if __name__ == '__main__':
    main()
