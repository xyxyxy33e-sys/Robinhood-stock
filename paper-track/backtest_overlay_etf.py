"""Full six-state overlay backtest using SPMO/QQQ ETFs directly as the core
(not the stock-basket mirror) + TQQQ satellite + cash gate, weekly rebalanced,
per TARGET_WEIGHTS in state.py. Cash leg uses BOXX where available (from
2022-01-03) and a 3-month T-bill proxy compounded daily before that (per
state.py's note that BOXX tracks the T-bill proxy within ~0.16pp/yr --
negligible difference, used only because BOXX itself doesn't exist pre-2022).

Compares two core choices (SPMO ETF, QQQ ETF) against plain buy-and-hold
SPMO and QQQ over the same window.
"""
import csv
import math
import sys
from datetime import date, datetime

sys.path.insert(0, 'paper-track')
from state import compute_states, target_weights, validate_weights

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'


def load_daily_csv(path, close_col='c'):
    out = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            try:
                out[r['d']] = float(r[close_col])
            except (ValueError, KeyError):
                pass
    return out


def load_tbill():
    out = {}
    with open(f'{ROBINHOOD_REPO}/DGS3MO.csv') as f:
        for r in csv.DictReader(f):
            try:
                out[r['observation_date']] = float(r['DGS3MO'])
            except ValueError:
                pass
    return out


def build_cash_index(dates, boxx_px, tbill_rate):
    """Daily cash NAV index: BOXX close where available, else compounds the
    3-month T-bill annualized rate day-over-day (calendar-day compounding)."""
    idx = {}
    nav = 1.0
    last_rate = None
    prev_d = None
    for d in dates:
        if d in boxx_px:
            if not idx:
                nav = 1.0
            idx[d] = ('boxx', boxx_px[d])
        else:
            if d in tbill_rate:
                last_rate = tbill_rate[d]
            if prev_d is not None and last_rate is not None:
                days = (date.fromisoformat(d) - date.fromisoformat(prev_d)).days
                nav *= (1 + last_rate / 100.0) ** (days / 365.0)
            idx[d] = ('tbill', nav)
        prev_d = d
    # stitch: convert to a single continuous NAV series, rebasing at the
    # boxx/tbill handoff so there's no discontinuity
    out = {}
    running = None
    last_val = None
    last_kind = None
    for d in dates:
        kind, val = idx[d]
        if running is None:
            running = 1.0
        elif kind != last_kind:
            pass  # handoff point, ratio continues from tracked running value
        if last_val is not None:
            if kind == last_kind:
                ratio = val / last_val
            else:
                ratio = 1.0  # no jump at handoff, just switch source
            running *= ratio
        out[d] = running
        last_val = val
        last_kind = kind
    return out


def weekly_fridays(dates):
    """Pick the last trading day (<=Friday) of each ISO week from a sorted
    daily date list -- matches the live strategy's Friday rebalance."""
    out = []
    cur_week = None
    for d in dates:
        wk = date.fromisoformat(d).isocalendar()[:2]
        if wk != cur_week:
            if out:
                pass
            cur_week = wk
        out.append(d)
    # collapse to last trading day per iso week
    by_week = {}
    for d in dates:
        wk = date.fromisoformat(d).isocalendar()[:2]
        by_week[wk] = d
    return sorted(by_week.values())


def run(core_symbol, core_px, qqq_px, tqqq_px, cash_idx):
    # Compute states on QQQ's FULL history (back to its earliest available date,
    # ~2009) so the 50/200-day SMA is properly warmed up before the backtest
    # window starts -- truncating to the core/satellite/cash intersection here
    # would force the first ~200 trading days into the SMA-not-ready default
    # state ('F'), corrupting the first year of the regime signal.
    qqq_dates = sorted(qqq_px)
    states = compute_states(qqq_dates, qqq_px)
    state_by_date = dict(zip(qqq_dates, states))

    dates = sorted(set(qqq_px) & set(core_px) & set(tqqq_px) & set(cash_idx))
    fridays = weekly_fridays(dates)
    fridays = [d for d in fridays if d >= '2015-11-02']

    nav = 1.0
    navs = [nav]
    used = [fridays[0]]
    state_weeks = {}
    for i in range(len(fridays) - 1):
        d0, d1 = fridays[i], fridays[i + 1]
        st = state_by_date[d0]
        core_w, sat_w, cash_w = target_weights(st)
        validate_weights(st, core_w, sat_w, cash_w)
        r_core = core_px[d1] / core_px[d0] - 1
        r_sat = tqqq_px[d1] / tqqq_px[d0] - 1
        r_cash = cash_idx[d1] / cash_idx[d0] - 1
        wk_ret = core_w * r_core + sat_w * r_sat + cash_w * r_cash
        nav *= (1 + wk_ret)
        navs.append(nav)
        used.append(d1)
        state_weeks[st] = state_weeks.get(st, 0) + 1

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
    return dict(core=core_symbol, cagr=cagr, vol=vol, sharpe=sharpe, mdd=mdd,
                total=navs[-1] - 1, weeks=n, start=used[0], end=used[-1],
                state_weeks=state_weeks)


def buyhold(symbol, px, dates_ref):
    fridays = weekly_fridays(sorted(px))
    fridays = [d for d in fridays if d >= '2015-11-02' and d in px]
    nav = 1.0
    navs = [nav]
    for i in range(len(fridays) - 1):
        r = px[fridays[i + 1]] / px[fridays[i]] - 1
        nav *= (1 + r)
        navs.append(nav)
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
    return dict(symbol=symbol, cagr=cagr, vol=vol, sharpe=sharpe, mdd=mdd,
                total=navs[-1] - 1, weeks=n, start=fridays[0], end=fridays[-1])


def main():
    qqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    tqqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/TQQQ.csv')
    spmo = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPMO.csv')
    boxx = load_daily_csv(f'{ROBINHOOD_REPO}/etf/BOXX.csv')
    tbill = load_tbill()

    all_dates = sorted(set(qqq) | set(tqqq) | set(spmo))
    cash_idx = build_cash_index(all_dates, boxx, tbill)

    print(f"{'Config':<28} {'CAGR':>8} {'Vol':>7} {'Sharpe':>7} {'MaxDD':>8} {'TotalRet':>10} {'weeks':>6}")
    print('-' * 85)

    r = run('SPMO', spmo, qqq, tqqq, cash_idx)
    print(f"{'Overlay: SPMO core':<28} {r['cagr']*100:>7.2f}% {r['vol']*100:>6.2f}% {r['sharpe']:>7.3f} {r['mdd']*100:>7.2f}% {r['total']*100:>9.1f}% {r['weeks']:>6}")
    print('  state-weeks:', r['state_weeks'])

    r2 = run('QQQ', qqq, qqq, tqqq, cash_idx)
    print(f"{'Overlay: QQQ core':<28} {r2['cagr']*100:>7.2f}% {r2['vol']*100:>6.2f}% {r2['sharpe']:>7.3f} {r2['mdd']*100:>7.2f}% {r2['total']*100:>9.1f}% {r2['weeks']:>6}")

    bh_spmo = buyhold('SPMO', spmo, all_dates)
    print(f"{'Buy&hold SPMO':<28} {bh_spmo['cagr']*100:>7.2f}% {bh_spmo['vol']*100:>6.2f}% {bh_spmo['sharpe']:>7.3f} {bh_spmo['mdd']*100:>7.2f}% {bh_spmo['total']*100:>9.1f}% {bh_spmo['weeks']:>6}")

    bh_qqq = buyhold('QQQ', qqq, all_dates)
    print(f"{'Buy&hold QQQ':<28} {bh_qqq['cagr']*100:>7.2f}% {bh_qqq['vol']*100:>6.2f}% {bh_qqq['sharpe']:>7.3f} {bh_qqq['mdd']*100:>7.2f}% {bh_qqq['total']*100:>9.1f}% {bh_qqq['weeks']:>6}")


if __name__ == '__main__':
    main()
