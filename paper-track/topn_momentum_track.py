"""Top-5 / Top-10 / Top-15 momentum baskets — forward paper track, weekly rebalanced.

Owner request (2026-09-22): run a paper trail of concentrated momentum baskets
built from the top N names of the S&P 500 Momentum Index, rebalanced weekly,
against SPMO itself.

PRIOR ART, so this is not started blind. Until 2026-08-31 the live core WAS a
15-stock proportionally-weighted mirror of SPMO, and it was replaced by the ETF
because the ETF beat it on every axis (Sharpe 1.065 vs 1.043, MaxDD -30.4% vs
-33.0%) while removing a weekly scrape, 15 positions and core-side wash-sale
tracking. Top-15 here therefore re-runs a question already answered once. Top-5
and top-10 are genuinely new -- that is where the information is.

CONSTRUCTION
  - Universe: the index constituent list (SPMO's own book; the KIWOOM 0137V0
    file is used as the source when Invesco has not published a rebalance yet).
  - Share classes COMBINED: GOOGL and GOOG are one company and count as one
    name, held in GOOGL. A top-10 basket means ten businesses, not ten lines.
  - Weighting: proportional to index weight, rescaled to 100%.
  - Rebalance: WEEKLY at Friday's close, back to the then-current index weights
    (which also picks up any index reconstitution automatically).
  - Cost: 4 bp one-way on L1 drift traded, the same model the live strategy
    assumes.
  - Benchmarks: SPMO, QQQ, SPY.
  - Everything is PAPER. No account action, ever, from this file.

Usage:  python3 paper-track/topn_momentum_track.py --seed      (once)
        python3 paper-track/topn_momentum_track.py --mark      (weekly, Fri close)
        python3 paper-track/topn_momentum_track.py --report
"""
import csv, io, json, os, sys, math, datetime

LOG = 'data/topn_momentum_paper.csv'
BASKETS = (5, 10, 15)
ONE_WAY = 0.0004
FIELDS = ['date', 'basket', 'nav', 'week_return', 'turnover', 'cost_bp', 'n_names', 'note']

# index weights, share classes combined, from the 2026-09-21 post-reconstitution book
INDEX_WEIGHTS = [
    ('AAPL', 9.2), ('MU', 9.2), ('GOOGL', 9.0), ('AMD', 5.2), ('INTC', 5.1),
    ('JNJ', 4.7), ('XOM', 3.1), ('SNDK', 2.9), ('LRCX', 2.7), ('AMAT', 2.4),
    ('CSCO', 2.4), ('MRK', 2.2), ('STX', 2.1), ('CAT', 2.0), ('WDC', 1.7),
]   # GOOGL 5.0 + GOOG 4.0 combined

def basket(n, weights=None):
    """Top-n names, proportional index weights rescaled to 100%."""
    w = (weights or INDEX_WEIGHTS)[:n]
    tot = sum(x for _, x in w)
    return {t: x / tot for t, x in w}

def load():
    if not os.path.exists(LOG): return []
    with io.open(LOG, encoding='utf-8') as f:
        return list(csv.DictReader(f))

def append(rows):
    new = not os.path.exists(LOG)
    with io.open(LOG, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new: w.writeheader()
        for r in rows: w.writerow(r)

def mark(date, px_now, px_prev=None, held=None, note=''):
    """One weekly mark. `held` is {basket: {ticker: weight}} carried in from the
    previous mark (None on the seed). Returns (rows, new_held)."""
    rows, newheld = [], {}
    prev = {r['basket']: r for r in load() if r['date'] == (sorted({x['date'] for x in load()})[-1] if load() else None)}
    for n in BASKETS:
        tgt = basket(n)
        key = 'top%d' % n
        if held is None or px_prev is None:
            rows.append(dict(date=date, basket=key, nav='1.000000', week_return='',
                             turnover='', cost_bp='', n_names=len(tgt), note=note or 'seed'))
            newheld[key] = dict(tgt)
            continue
        h = held[key]
        gross = sum(h[t] * (px_now[t] / px_prev[t] - 1) for t in h)
        drift = {t: h[t] * (1 + (px_now[t] / px_prev[t] - 1)) / (1 + gross) for t in h}
        turn = sum(abs(tgt.get(t, 0) - drift.get(t, 0)) for t in set(tgt) | set(drift))
        cost = ONE_WAY * turn
        net = gross - cost
        nav = float(prev[key]['nav']) * (1 + net)
        rows.append(dict(date=date, basket=key, nav='%.6f' % nav, week_return='%.6f' % net,
                         turnover='%.4f' % turn, cost_bp='%.1f' % (cost * 1e4),
                         n_names=len(tgt), note=note))
        newheld[key] = dict(tgt)
    return rows, newheld

def bench_row(date, sym, px_now, px_prev, prev_nav):
    if px_prev is None:
        return dict(date=date, basket=sym, nav='1.000000', week_return='', turnover='',
                    cost_bp='', n_names=1, note='seed')
    r = px_now[sym] / px_prev[sym] - 1
    return dict(date=date, basket=sym, nav='%.6f' % (prev_nav * (1 + r)),
                week_return='%.6f' % r, turnover='0', cost_bp='0', n_names=1, note='benchmark')

def report():
    rows = load()
    if not rows: return print('no marks yet')
    dates = sorted({r['date'] for r in rows})
    print('Top-N momentum paper track — %d marks, %s .. %s' % (len(dates), dates[0], dates[-1]))
    last = {r['basket']: r for r in rows if r['date'] == dates[-1]}
    first = {r['basket']: r for r in rows if r['date'] == dates[0]}
    print('  %-8s %10s %12s %10s' % ('basket', 'NAV', 'cum return', 'names'))
    for k in ['top5', 'top10', 'top15', 'SPMO', 'QQQ', 'SPY']:
        if k in last:
            nav = float(last[k]['nav'])
            print('  %-8s %10.4f %11.2f%% %10s' % (k, nav, (nav - 1) * 100, last[k]['n_names']))

if __name__ == '__main__':
    print(__doc__.split('Usage:')[0])
    if '--report' in sys.argv: report()
