"""2026-11-20, owner sent a screenshot of a "Wealthfront mix (pre-tax)" on Public: six funds, weights read off the
donut chart (approximate): VTI 43, VNQ 14, LQD 13, VEA 13, VWO 11, SCHP 6. Bought once and held, and rebalanced yearly,
against the live rules. Engine and taxes of better.py. VEA before Jul 2007 = EFA; SCHP before Aug 2010 = TIP."""
import os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, better as B
W = {'VTI': .43, 'VNQ': .14, 'LQD': .13, 'VEA': .13, 'VWO': .11, 'SCHP': .06}
if len(sys.argv) > 1 and sys.argv[1] == 'classic':   # the 'Classic portfolio mix' the owner pasted afterwards
    W = {'VTI': .45, 'VEA': .18, 'VWO': .16, 'LQD': .12, 'SCHP': .06, 'VIG': .03}
BF = {'VEA': 'EFA', 'SCHP': 'TIP'}; ORD = {'LQD', 'SCHP', 'VNQ'}
ix = {d: i for i, d in enumerate(B.dates)}
def series(sym):
    p = B.yh(sym); x = np.array([p.get(d, np.nan) for d in B.dates]); r = np.r_[0, x[1:] / x[:-1] - 1]
    ev = (B._dl(sym).get('events') or {}).get('dividends') or {}; raw = B._raw(sym); rd = sorted(raw); a = np.zeros(B.n)
    for v in ev.values():
        d = dt.datetime.utcfromtimestamp(v['date']).date().isoformat()
        if d in ix:
            pv = [q for q in rd if q < d]
            if pv: a[ix[d]] += v['amount'] / raw[pv[-1]]
    return r, a
for s in W:
    if s in B.X: continue
    r, a = series(s)
    if s in BF:
        r2, a2 = series(BF[s]); m = np.isnan(r); r = np.where(m, r2, r); a = np.where(m, a2, a)
    B.R[s] = r; B.X[s] = np.cumprod(1 + np.r_[0, r[1:]]); B.DY[s] = a
    if s not in ORD: B.QUAL.add(s)
class Yearly:
    def __init__(s): s.y = None
    def step(s, i):
        y = B.dates[i][:4]; tr = s.y is not None and y != s.y; s.y = y; return tr
    def target(s): return dict(W)
V = {'live rules': lambda: B.Live(band=.02), 'mix, held': lambda: B.Static(W), 'mix, yearly rebalance': Yearly, 'SPY held': lambda: B.Static({'SPY': 1.0})}
print("Jul 2007 - 19 Nov 2026     | before tax: CAGR Sharpe MaxDD worst yr | after tax | 2007-15 pre/after | 2016-26 pre/after | 2008  2020  2022  2026")
for nm, mk in V.items():
    a = B.sim(mk); t = B.sim(mk, tax=True); sa, st = B.stats(a[0], a[1]), B.stats(t[0], t[1])
    h = [B.stats(*B.sim(mk, start=x, end=y, tax=tx)[:2])[0] for x, y in (('2007-07-02', '2015-12-31'), ('2016-01-04', '9999')) for tx in (False, True)]
    nav = np.r_[1, a[0]]; r = nav[1:] / nav[:-1] - 1; yr = {}
    for d, x in zip(a[1], r): yr.setdefault(d[:4], []).append(x)
    u = nav / np.maximum.accumulate(nav) - 1
    print(f"{nm:26s} | {sa[0]:5.1f} {sa[1]:5.2f} {sa[2]:6.1f} {sa[3]:6.1f}            | {st[0]:5.1f}     | {h[0]:5.1f} / {h[1]:5.1f}     | {h[2]:5.1f} / {h[3]:5.1f}     | " + ' '.join(f"{(np.prod(1 + np.array(yr[y])) - 1) * 100:+5.0f}" for y in ('2008', '2020', '2022', '2026')) + f" | avg below high {u.mean():.1%}")
a, b = ix['2026-10-14'], ix['2026-11-18']
print(f"\n14 Oct - 18 Nov 2026 (the screenshot's window): mix {sum(w * (B.X[s][b] / B.X[s][a] - 1) for s, w in W.items()):+.2%} (screenshot shows -2.07%); " + ', '.join(f"{s} {B.X[s][b] / B.X[s][a] - 1:+.1%}" for s in W) + f"; SPY {B.X['SPY'][b] / B.X['SPY'][a] - 1:+.1%}")
lv = B.sim(lambda: B.Live(band=.02)); nav = dict(zip(lv[1], lv[0])); print(f"live rules over the same window (backtest): {nav['2026-11-18'] / nav['2026-10-14'] - 1:+.2%}")
ra = lambda x: np.r_[x[0][0] - 1, x[0][1:] / x[0][:-1] - 1]; m = B.sim(lambda: B.Static(W)); print(f"daily correlation, mix vs live rules {np.corrcoef(ra(m), ra(lv))[0, 1]:.2f}; mix vs SPY {np.corrcoef(ra(m), B.R['SPY'][B.dates.index('2007-07-02') + 1:])[0, 1]:.2f}")
