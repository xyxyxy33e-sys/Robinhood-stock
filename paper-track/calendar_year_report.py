"""Calendar-year return comparison: the live overlay (SPMO core + TQQQ/QLD
satellite + BOXX/T-bill cash, current TARGET_WEIGHTS) vs. buy-and-hold SPMO,
QQQ, and SPY, using the SAME weekly dates as the overlay backtest so every
column is computed on an identical clock.
"""
import sys
from datetime import date

sys.path.insert(0, 'paper-track')
from four_leg_overlay import build_weekly_series, full_series_rets
from backtest_overlay_etf import load_daily_csv

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'

NEW_WEIGHTS = {
    'A': (0.80, 0.20, 0.00, 0.00),
    'B': (0.25, 0.75, 0.00, 0.00),
    'C': (1.00, 0.00, 0.00, 0.00),
    'D': (0.00, 0.00, 0.70, 0.30),
    'E': (0.50, 0.00, 0.00, 0.50),
    'F': (0.30, 0.00, 0.00, 0.70),
}


def nearest_price(px, d, all_dates_sorted):
    dd = d
    while dd not in px and dd > all_dates_sorted[0]:
        dd = (date.fromisoformat(dd) - __import__('datetime').timedelta(days=1)).isoformat()
    return px.get(dd)


def main():
    rows = build_weekly_series()  # (week_end_date, state, r_core, r_tqqq, r_qld, r_cash)
    overlay_rets = full_series_rets(rows, NEW_WEIGHTS)
    weeks_end = [r[0] for r in rows]

    spmo = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPMO.csv')
    qqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    spy = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPY.csv')
    spmo_dates = sorted(spmo)
    qqq_dates = sorted(qqq)
    spy_dates = sorted(spy)

    def bench_rets(px, dates_sorted):
        out = []
        prev_px = nearest_price(px, weeks_end[0], dates_sorted)
        for w in weeks_end[1:]:
            cur_px = nearest_price(px, w, dates_sorted)
            out.append(cur_px / prev_px - 1 if prev_px else None)
            prev_px = cur_px
        return out

    spmo_rets = bench_rets(spmo, spmo_dates)
    qqq_rets = bench_rets(qqq, qqq_dates)
    spy_rets = bench_rets(spy, spy_dates)

    # overlay_rets[i] is the return from weeks_end[i] to weeks_end[i+1] (per
    # full_series_rets/build_weekly_series's own convention: row i holds the
    # return realized AT weeks_end[i], having started at the prior week).
    # Align: overlay_rets has len(rows) entries, one per row, each row's
    # r_core/r_tqqq/etc already IS the week's return ending at that row's
    # week_end_date. So overlay_rets[i] pairs with weeks_end[i], same as
    # bench_rets computed above (which also skips the first date as the
    # anchor). Slice overlay_rets[1:] to match.
    overlay_rets_aligned = overlay_rets[1:]
    year_of = [w[:4] for w in weeks_end[1:]]

    assert len(overlay_rets_aligned) == len(spmo_rets) == len(qqq_rets) == len(spy_rets) == len(year_of)

    years = sorted(set(year_of))
    print(f"{'Year':<6}{'Overlay':>10}{'SPMO':>10}{'QQQ':>10}{'SPY':>10}{'n_weeks':>9}")
    print('-' * 55)

    cum = {k: 1.0 for k in ('overlay', 'spmo', 'qqq', 'spy')}
    for y in years:
        idxs = [i for i, yy in enumerate(year_of) if yy == y]
        navs = {'overlay': 1.0, 'spmo': 1.0, 'qqq': 1.0, 'spy': 1.0}
        series = {'overlay': overlay_rets_aligned, 'spmo': spmo_rets, 'qqq': qqq_rets, 'spy': spy_rets}
        for k in navs:
            for i in idxs:
                r = series[k][i]
                if r is not None:
                    navs[k] *= (1 + r)
            cum[k] *= navs[k]
        print(f"{y:<6}{(navs['overlay']-1)*100:>9.1f}%{(navs['spmo']-1)*100:>9.1f}%"
              f"{(navs['qqq']-1)*100:>9.1f}%{(navs['spy']-1)*100:>9.1f}%{len(idxs):>9}")

    print('-' * 55)
    print(f"{'TOTAL':<6}{(cum['overlay']-1)*100:>9.1f}%{(cum['spmo']-1)*100:>9.1f}%"
          f"{(cum['qqq']-1)*100:>9.1f}%{(cum['spy']-1)*100:>9.1f}%")


if __name__ == '__main__':
    main()
