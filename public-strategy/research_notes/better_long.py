"""Band width on history the design never saw: the trend half alone (2x S&P with the 30% vol target while above the
200-day line, else T-bills), 1960-2007, before and after tax. S&P = ^GSPC price index + 3%/yr dividends; 2x fund =
2x the daily return less one T-bill of financing and 0.9%/yr; T-bills = ^IRX. No VIX leg (no VIX before 1990)."""
import os, sys, json, time, urllib.request, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, better as B
f = os.path.join(B.CACHE, 'GSPC_long.json')
if not os.path.exists(f):
    u = f"https://query2.finance.yahoo.com/v8/finance/chart/%5EGSPC?period1=-1325635200&period2={int(time.time())}&interval=1d"
    open(f, 'wb').write(urllib.request.urlopen(urllib.request.Request(u, headers=B.UA), timeout=60).read())
d = json.load(open(f))['chart']['result'][0]
gs = {(dt.datetime(1970, 1, 1) + dt.timedelta(seconds=t)).date().isoformat(): v for t, v in zip(d['timestamp'], d['indicators']['quote'][0]['close']) if v}
irx = B._raw('^IRX'); dates = [x for x in sorted(gs) if '1959-01-01' <= x <= '2007-06-29']; n = len(dates)
y = 3.0; C = np.zeros(n)
for i, x in enumerate(dates):
    y = irx.get(x, y); C[i] = y / 100 / 252
p = np.array([gs[x] for x in dates]); r1 = np.r_[0, p[1:] / p[:-1] - 1] + 0.03 / 252; r2 = 2 * r1 - C - 0.009 / 252
X = {'SPY': np.cumprod(1 + r1), 'SSO': np.cumprod(1 + r2), 'IEF': np.cumprod(1 + C)}
B.dates, B.n, B.C, B.X = dates, n, C, X; B.R = {s: np.r_[0, X[s][1:] / X[s][:-1] - 1] for s in X}; B.DY = {s: np.zeros(n) for s in X}
c = np.cumsum(np.insert(X['SPY'], 0, 0)); B.sma = np.full(n, np.nan); B.sma[199:] = (c[200:] - c[:-200]) / 200
B.me = [i for i in range(n - 1) if dates[i][:7] != dates[i + 1][:7]]; B.mes = set(B.me); B.mi = {i: k for k, i in enumerate(B.me)}
B.PANIC = np.zeros(n, bool); lr = np.log(1 + B.R['SPY']); B._vol = np.full(n, np.nan)
for i in range(31, n): B._vol[i] = max(lr[i-9:i+1].std(ddof=1), lr[i-29:i+1].std(ddof=1)) * 252 ** .5
print("trend half alone, 1960-2007     | before tax: CAGR Sharpe MaxDD | after tax CAGR | 1960-1983 pre/after | 1984-2007 pre/after | switches/yr")
for nm, mk in [(f"band {b:.0%}, vol target {'30%' if vt else 'off'}", (lambda b=b, vt=vt: B.Live(band=b, vt=vt, panic=0, rot='none'))) for vt in (0.30, None) for b in (.01, .02, .03, .04)] + [('S&P buy and hold', lambda: B.Static({'SPY': 1.0}))]:
    a = B.sim(mk, start='1960-01-04'); t = B.sim(mk, start='1960-01-04', tax=True); sa, st = B.stats(a[0], a[1]), B.stats(t[0], t[1])
    h = [B.stats(*B.sim(mk, start=s_, end=e_, tax=tx)[:2])[0] for s_, e_ in (('1960-01-04', '1983-12-30'), ('1984-01-03', '2007-06-29')) for tx in (False, True)]
    st_ = mk(); sw = 0; on = None
    for i in range(200, n):
        st_.step(i)
        if getattr(st_, 'on', None) != on and dates[i] >= '1960-01-04': sw += on is not None; on = st_.on
        elif dates[i] < '1960-01-04': on = getattr(st_, 'on', None)
    print(f"{nm:31s} | {sa[0]:5.1f} {sa[1]:5.2f} {sa[2]:6.1f}            | {st[0]:5.1f}          | {h[0]:5.1f} / {h[1]:5.1f}       | {h[2]:5.1f} / {h[3]:5.1f}       | {sw / (len(a[1]) / 252):4.1f}")
