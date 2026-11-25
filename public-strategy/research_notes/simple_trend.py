"""2026-11-25, owner: the plain rule on its own. SSO while SPY (adjusted close) is above its 200-day average, T-bills
otherwise, checked daily at the close, no buffer, no volatility target, no VIX leg, no rotation. Against SPY buy and
hold. Before tax. Data and cash series of backtest.py (via better.py)."""
import numpy as np, better as B
d, n = B.dates, B.n; spy = np.array([B.px['SPY'][x] for x in d]); cash = B.C
sma = np.array([spy[i - 199:i + 1].mean() if i >= 199 else np.nan for i in range(n)])
def run(band, a, b):
    on = False; r = []; ds = []; sw = 0; inn = 0
    for i in range(199, n - 1):
        g = spy[i] / sma[i] - 1; new = (g > -band) if on else (g > band)
        if d[i + 1] >= a and d[i + 1] <= b:
            sw += new != on and len(r) > 0; r.append(B.R['SSO'][i + 1] if new else cash[i + 1]); ds.append(d[i + 1]); inn += new
        on = new
    return np.array(r), ds, sw, inn / len(r)
def st(r, ds):
    nav = np.cumprod(1 + r); yr = {}
    for x, y in zip(ds, r): yr.setdefault(x[:4], []).append(y)
    ys = {k: np.prod(1 + np.array(v)) - 1 for k, v in yr.items()}
    return (nav[-1] ** (252 / len(r)) - 1) * 100, r.mean() * 252 / (r.std(ddof=1) * 252 ** .5), (nav / np.maximum.accumulate(nav) - 1).min() * 100, min(ys.values()) * 100, nav[-1], ys
P = [('2007-07-02', '9999'), ('2007-07-02', '2015-12-31'), ('2016-01-04', '9999')]
for a, b in P:
    print(f"== {a[:4]}-{'2026' if b == '9999' else b[:4]} ==   CAGR Sharpe  MaxDD worst yr  $1 ->   switches/yr  time in SSO")
    for nm, band in (('SSO / cash, 200-day, no buffer', 0.0), ('same with a 2% buffer', 0.02)):
        r, ds, sw, inn = run(band, a, b); s = st(r, ds)
        print(f"  {nm:32s} {s[0]:5.1f} {s[1]:5.2f} {s[2]:6.1f} {s[3]:6.1f}  {s[4]:6.2f}   {sw / (len(r) / 252):5.1f}       {inn:4.0%}")
        if band == 0 and b == '9999' and a == P[0][0]: Y = s[5]
    i0 = d.index(ds[0]); rs = np.array(B.R['SPY'][i0:i0 + len(ds)]); s = st(rs, ds)
    print(f"  {'SPY buy and hold':32s} {s[0]:5.1f} {s[1]:5.2f} {s[2]:6.1f} {s[3]:6.1f}  {s[4]:6.2f}")
    rr = np.array(B.R['SSO'][i0:i0 + len(ds)]); s2 = st(rr, ds)
    print(f"  {'SSO buy and hold':32s} {s2[0]:5.1f} {s2[1]:5.2f} {s2[2]:6.1f} {s2[3]:6.1f}  {s2[4]:6.2f}")
    if a == P[0][0] and b == '9999': YS = s[5]
print("years (rule / SPY): " + '  '.join(f"{y} {Y[y]*100:+.0f}/{YS[y]*100:+.0f}" for y in sorted(Y)))
