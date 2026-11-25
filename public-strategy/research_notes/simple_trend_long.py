"""2026-11-25, owner: the plain 200-day rule (2x S&P above the line, T-bills below, no buffer) on long history.
S&P = ^GSPC price index + 2%/yr dividends; 2x fund = 2x the daily return less one T-bill of financing and 0.9%/yr
(SSO did not exist before 2006); T-bills = ^IRX. Checked against the real SPY/SSO result for 2007-2026. Before tax."""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, better as B
g = json.load(open(os.path.join(B.CACHE, 'GSPC_long.json')))['chart']['result'][0]
gs = {(dt.datetime(1970, 1, 1) + dt.timedelta(seconds=t)).date().isoformat(): v for t, v in zip(g['timestamp'], g['indicators']['quote'][0]['close']) if v}
irx = B._raw('^IRX'); d = [x for x in sorted(gs) if '1988-06-01' <= x <= B.dates[-1]]; n = len(d)
y = 6.0; C = np.zeros(n)
for i, x in enumerate(d):
    y = irx.get(x, y); C[i] = y / 100 / 252
p = np.array([gs[x] for x in d]); r1 = np.r_[0, p[1:] / p[:-1] - 1] + 0.02 / 252; r2 = 2 * r1 - C - 0.009 / 252
tr = np.cumprod(1 + r1); c = np.cumsum(np.insert(tr, 0, 0)); sma = np.full(n, np.nan); sma[199:] = (c[200:] - c[:-200]) / 200
def run(band, a, b):
    on = False; r = []; ds = []; sw = 0; inn = 0
    for i in range(199, n - 1):
        gp = tr[i] / sma[i] - 1; new = (gp > -band) if on else (gp > band)
        if a <= d[i + 1] <= b:
            sw += new != on and len(r) > 0; r.append(r2[i + 1] if new else C[i + 1]); ds.append(d[i + 1]); inn += new
        on = new
    return np.array(r), ds, sw, inn / len(r)
def st(r, ds):
    nav = np.cumprod(1 + r); yr = {}
    for x, v in zip(ds, r): yr.setdefault(x[:4], []).append(v)
    ys = {k: np.prod(1 + np.array(v)) - 1 for k, v in yr.items()}
    return (nav[-1] ** (252 / len(r)) - 1) * 100, r.mean() * 252 / (r.std(ddof=1) * 252 ** .5), (nav / np.maximum.accumulate(nav) - 1).min() * 100, min(ys.values()) * 100, nav[-1], ys
P = [('1990-01-02', '9999'), ('1990-01-02', '1999-12-31'), ('2000-01-03', '2009-12-31'), ('2010-01-04', '2019-12-31'), ('2020-01-02', '9999'), ('2007-07-02', '9999')]
for a, b in P:
    print(f"== {a[:4]}-{'2026' if b == '9999' else b[:4]} ==   CAGR Sharpe  MaxDD worst yr  $1 ->   switches/yr  time in 2x")
    for nm, band in (('2x S&P / T-bills, 200-day', 0.0), ('same with a 2% buffer', 0.02)):
        r, ds, sw, inn = run(band, a, b); s = st(r, ds)
        print(f"  {nm:28s} {s[0]:5.1f} {s[1]:5.2f} {s[2]:6.1f} {s[3]:6.1f}  {s[4]:7.2f}   {sw / (len(r) / 252):5.1f}       {inn:4.0%}")
        if band == 0 and a == P[0][0] and b == '9999': Y = s[5]
    i0 = d.index(ds[0])
    for nm, rr in (('S&P 500 buy and hold', r1), ('2x S&P buy and hold', r2)):
        s = st(rr[i0:i0 + len(ds)], ds); print(f"  {nm:28s} {s[0]:5.1f} {s[1]:5.2f} {s[2]:6.1f} {s[3]:6.1f}  {s[4]:7.2f}")
        if nm[0] == 'S' and a == P[0][0] and b == '9999': YS = s[5]
print("years (rule / S&P): " + '  '.join(f"{y} {Y[y]*100:+.0f}/{YS[y]*100:+.0f}" for y in sorted(Y)))
