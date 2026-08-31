"""Turnover and correlation diagnostics for a top-N SPMO-mirror basket,
using the same reconstructed holdings history and weekly prices as
backtest_topn_weekly.py. Reports, for a given N:

  - turnover at each semiannual reconstitution: fraction of the basket
    that changes from one period to the next
  - within-period pairwise correlation of weekly returns among the basket
    members, averaged across periods (and compared to a wider N as a
    concentration baseline)
"""
import csv
import math
from collections import defaultdict
from datetime import date

HOLDINGS_CSV = 'data/spmo_holdings_history.csv'
PRICES_CSV = 'data/spmo_weekly_prices.csv'


def load_holdings():
    periods = defaultdict(list)
    with open(HOLDINGS_CSV) as f:
        for r in csv.DictReader(f):
            periods[r['rep_pd_date']].append((int(r['rank']), r['ticker']))
    out = []
    for d in sorted(periods):
        rows = sorted(periods[d], key=lambda x: x[0])
        out.append((date.fromisoformat(d), [t for _, t in rows]))
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


def turnover(periods, n):
    print(f"\n=== Turnover, top-{n} ===")
    rows = []
    for i in range(1, len(periods)):
        prev = set(periods[i - 1][1][:n])
        cur = set(periods[i][1][:n])
        kept = prev & cur
        dropped = prev - cur
        added = cur - prev
        pct = len(dropped) / n
        rows.append(pct)
        print(f"{periods[i-1][0]} -> {periods[i][0]}: "
              f"kept {len(kept)}/{n}, dropped {sorted(dropped)}, "
              f"added {sorted(added)}  ({pct*100:.0f}% turnover)")
    avg = sum(rows) / len(rows)
    print(f"Average turnover per reconstitution: {avg*100:.1f}%  "
          f"(annualized, ~2 reconstitutions/yr: {avg*2*100:.1f}%/yr)")
    return avg


def weekly_returns(prices, ticker, weeks):
    rets = []
    for i in range(len(weeks) - 1):
        w0, w1 = weeks[i], weeks[i + 1]
        p0 = prices.get(ticker, {}).get(w0)
        p1 = prices.get(ticker, {}).get(w1)
        if p0 and p1 and p0 > 0:
            rets.append(math.log(p1 / p0))
        else:
            rets.append(None)
    return rets


def pearson(a, b):
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if len(pairs) < 10:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    cov = sum((x - mx) * (y - my) for x, y in pairs)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return None
    return cov / math.sqrt(vx * vy)


def correlation(periods, prices, n):
    print(f"\n=== Within-period pairwise correlation, top-{n} ===")
    all_weeks = sorted({w for sym in prices for w in prices[sym]})
    period_avgs = []
    for i, (pd, tickers) in enumerate(periods):
        basket = tickers[:n]
        end = periods[i + 1][0] if i + 1 < len(periods) else date(2100, 1, 1)
        wk_window = [w for w in all_weeks if pd <= date.fromisoformat(w) < end]
        if len(wk_window) < 8:
            continue
        rets = {t: weekly_returns(prices, t, wk_window) for t in basket}
        corrs = []
        for a in range(len(basket)):
            for b in range(a + 1, len(basket)):
                r = pearson(rets[basket[a]], rets[basket[b]])
                if r is not None:
                    corrs.append(r)
        if corrs:
            avg = sum(corrs) / len(corrs)
            period_avgs.append(avg)
            print(f"{pd}: {len(corrs)} pairs, avg pairwise corr = {avg:.3f}, "
                  f"basket = {basket}")
    overall = sum(period_avgs) / len(period_avgs)
    print(f"\nOverall average pairwise correlation across all periods, top-{n}: {overall:.3f}")
    return overall


def main():
    periods = load_holdings()
    prices = load_prices()

    turnover(periods, 5)
    corr5 = correlation(periods, prices, 5)

    print("\n--- Comparison baselines ---")
    corr15 = correlation(periods, prices, 15)

    print(f"\nSummary: avg pairwise corr top-5 = {corr5:.3f}, top-15 = {corr15:.3f}")


if __name__ == '__main__':
    main()
