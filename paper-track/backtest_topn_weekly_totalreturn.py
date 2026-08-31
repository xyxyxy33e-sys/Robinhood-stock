"""Total-return version of backtest_topn_weekly.py. Identical logic (weekly
rebalanced top-N mirror of SPMO's reconstructed holdings history), except
prices come from data/spmo_weekly_prices_totalreturn.csv, which is dividend-
and-split adjusted (total return) for the 325/496 tickers whose Robinhood
adjustment_type='all' series passed validation (see
data/spmo_weekly_prices_totalreturn_meta.json), falling back to the plain
split-only prices from data/spmo_weekly_prices.csv for the other 171 tickers
whose 'all'-adjusted series was corrupted (negative/zero prices or a
systemic pattern of implausible weekly return divergence, mirroring the
adjustment-algorithm breakdown seen for TQQQ/SPMO in their thin-trading
early years -- this turned out to affect many liquid large caps too, not
just thinly-traded ETFs). Tests top-N holdings under two weighting
schemes, rebalanced back to target weights every week:

  - proportional: weight_i = reported SPMO pct_val_i / sum(pct_val over top N)
  - equal: weight_i = 1/N

Every combo of N in {1, 3, 5, 10, 15, 20, 25} x {proportional, equal} is reported.
"""
import csv
import math
from collections import defaultdict
from datetime import date

HOLDINGS_CSV = 'data/spmo_holdings_history.csv'
PRICES_CSV = 'data/spmo_weekly_prices_totalreturn.csv'


def load_holdings():
    periods = defaultdict(list)
    with open(HOLDINGS_CSV) as f:
        for r in csv.DictReader(f):
            periods[r['rep_pd_date']].append(
                (int(r['rank']), r['ticker'], float(r['pct_val']))
            )
    out = []
    for d in sorted(periods):
        rows = sorted(periods[d], key=lambda x: x[0])
        out.append((date.fromisoformat(d), rows))
    return out


def load_prices():
    prices = defaultdict(dict)
    with open(PRICES_CSV) as f:
        for r in csv.DictReader(f):
            try:
                prices[r['symbol']][r['week_start']] = float(r['close'])
            except ValueError:
                pass
    return prices


def top_n_weights(rows, n, scheme):
    top = rows[:n]
    if scheme == 'equal':
        w = 1.0 / len(top)
        return {t: w for _, t, _ in top}
    tot = sum(p for _, _, p in top)
    return {t: p / tot for _, t, p in top}


def holdings_for_date(periods, d):
    chosen = periods[0]
    for pd, rows in periods:
        if pd <= d:
            chosen = (pd, rows)
        else:
            break
    return chosen[1]


def max_drawdown(nav):
    peak = nav[0]
    mdd = 0.0
    for v in nav:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1)
    return mdd


def run_backtest(periods, prices, n, scheme):
    weeks = sorted({w for sym in prices for w in prices[sym]})
    start = periods[0][0]
    weeks = [w for w in weeks if date.fromisoformat(w) >= start]

    nav = [1.0]
    used_weeks = [weeks[0]]
    skipped_weeks = 0
    for i in range(len(weeks) - 1):
        w0, w1 = weeks[i], weeks[i + 1]
        d0 = date.fromisoformat(w0)
        rows = holdings_for_date(periods, d0)
        target = top_n_weights(rows, n, scheme)

        avail = {t: wt for t, wt in target.items()
                 if w0 in prices.get(t, {}) and w1 in prices.get(t, {})
                 and prices[t][w0] > 0}
        if not avail:
            skipped_weeks += 1
            nav.append(nav[-1])
            used_weeks.append(w1)
            continue
        renorm = sum(avail.values())
        wk_ret = sum((avail[t] / renorm) * (prices[t][w1] / prices[t][w0] - 1)
                     for t in avail)
        nav.append(nav[-1] * (1 + wk_ret))
        used_weeks.append(w1)

    n_weeks = len(nav) - 1
    years = n_weeks / 52.1775
    total_ret = nav[-1] / nav[0] - 1
    cagr = (nav[-1] / nav[0]) ** (1 / years) - 1 if years > 0 else float('nan')
    wk_rets = [nav[i + 1] / nav[i] - 1 for i in range(len(nav) - 1)]
    mean_r = sum(wk_rets) / len(wk_rets)
    var_r = sum((r - mean_r) ** 2 for r in wk_rets) / (len(wk_rets) - 1)
    vol_ann = math.sqrt(var_r) * math.sqrt(52.1775)
    sharpe = (mean_r * 52.1775) / vol_ann if vol_ann > 0 else float('nan')
    mdd = max_drawdown(nav)

    return dict(n=n, scheme=scheme, start=used_weeks[0], end=used_weeks[-1],
                weeks=n_weeks, skipped_weeks=skipped_weeks, total_return=total_ret,
                cagr=cagr, vol_ann=vol_ann, sharpe=sharpe, max_dd=mdd, nav=nav[-1])


def main():
    periods = load_holdings()
    prices = load_prices()

    results = []
    for n in (1, 3, 5, 10, 15, 20, 25):
        for scheme in ('proportional', 'equal'):
            results.append(run_backtest(periods, prices, n, scheme))

    hdr = f"{'N':>3} {'scheme':<12} {'start':<10} {'end':<10} {'weeks':>6} {'skip':>5} {'CAGR':>8} {'Vol':>7} {'Sharpe':>7} {'MaxDD':>8} {'TotalRet':>10}"
    print(hdr)
    print('-' * len(hdr))
    for r in results:
        print(f"{r['n']:>3} {r['scheme']:<12} {r['start']:<10} {r['end']:<10} "
              f"{r['weeks']:>6} {r['skipped_weeks']:>5} "
              f"{r['cagr']*100:>7.2f}% {r['vol_ann']*100:>6.2f}% {r['sharpe']:>7.3f} "
              f"{r['max_dd']*100:>7.2f}% {r['total_return']*100:>9.1f}%")


if __name__ == '__main__':
    main()
