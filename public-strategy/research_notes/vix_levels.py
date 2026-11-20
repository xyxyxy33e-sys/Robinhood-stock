"""2026-11-20, owner: compare the VIX-leg thresholds 30/25 (live) with 25/20 and 30/20. Live rules otherwise (2% band,
vol target, 25% leg). Engine and taxes of better.py. Part B: the trend half alone on 1990 - Jun 2007 (S&P index, 2x built)."""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, better as B
def latch(dates, on_, off_):
    out = np.zeros(len(dates), bool); p = False
    for i, d in enumerate(dates):
        v = B._vx.get(d)
        if v is not None: p = (v >= off_) if p else (v >= on_)
        out[i] = p
    return out
LV = (('30/25 live', 30, 25), ('25/20', 25, 20), ('30/20', 30, 20), ('35/28', 35, 28), ('no leg', None, None))
def table(mk, start, end, halves, years):
    print(f"{'':11s}| before tax: CAGR Sharpe MaxDD worst yr | after tax | " + ' | '.join(f"{a[:4]}-{b[:4]} pre/after" for a, b in halves) + " | leg on | trade days/yr | " + ' '.join(f"{y:>5s}" for y in years))
    for nm, on_, off_ in LV:
        B.PANIC = latch(B.dates, on_, off_) if on_ else np.zeros(B.n, bool)
        a = B.sim(mk, start=start, end=end); t = B.sim(mk, start=start, end=end, tax=True); sa, st = B.stats(a[0], a[1]), B.stats(t[0], t[1])
        h = [B.stats(*B.sim(mk, start=x, end=y, tax=tx)[:2])[0] for x, y in halves for tx in (False, True)]
        s = mk(); act = 0; tot = 0
        for i in range(200, B.n):
            s.step(i)
            if start <= B.dates[i] <= end: tot += 1; act += bool(s.pan)
        nav = np.r_[1, a[0]]; r = nav[1:] / nav[:-1] - 1; yr = {}
        for d, x in zip(a[1], r): yr.setdefault(d[:4], []).append(x)
        print(f"{nm:11s}| {sa[0]:5.1f} {sa[1]:5.2f} {sa[2]:6.1f} {sa[3]:6.1f}            | {st[0]:5.1f}     | " + ' | '.join(f"{h[2*k]:5.1f} / {h[2*k+1]:5.1f}     " for k in range(len(halves)))
              + f" | {act / tot:5.1%}  | {a[2] / (len(a[1]) / 252):5.1f}         | " + ' '.join(f"{(np.prod(1 + np.array(yr[y])) - 1) * 100:+5.0f}" for y in years))
print("A. Whole strategy, Jul 2007 - 19 Nov 2026")
table(lambda: B.Live(band=.02), '2007-07-02', '9999', [('2007-07-02', '2015-12-31'), ('2016-01-04', '9999')], ('2008', '2011', '2018', '2020', '2022'))
d = json.load(open(os.path.join(B.CACHE, 'GSPC_long.json')))['chart']['result'][0]
gs = {(dt.datetime(1970, 1, 1) + dt.timedelta(seconds=t)).date().isoformat(): v for t, v in zip(d['timestamp'], d['indicators']['quote'][0]['close']) if v}
irx = B._raw('^IRX'); dates = [x for x in sorted(gs) if '1988-06-01' <= x <= '2007-06-29']; n = len(dates); y = 6.0; C = np.zeros(n)
for i, x in enumerate(dates): y = irx.get(x, y); C[i] = y / 100 / 252
p = np.array([gs[x] for x in dates]); r1 = np.r_[0, p[1:] / p[:-1] - 1] + 0.02 / 252; r2 = 2 * r1 - C - 0.009 / 252
B.dates, B.n, B.C = dates, n, C; B.X = {'SPY': np.cumprod(1 + r1), 'SSO': np.cumprod(1 + r2), 'IEF': np.cumprod(1 + C)}; B.R = {s: np.r_[0, v[1:] / v[:-1] - 1] for s, v in B.X.items()}; B.DY = {s: np.zeros(n) for s in B.X}
c = np.cumsum(np.insert(B.X['SPY'], 0, 0)); B.sma = np.full(n, np.nan); B.sma[199:] = (c[200:] - c[:-200]) / 200
B.me = [i for i in range(n - 1) if dates[i][:7] != dates[i + 1][:7]]; B.mes = set(B.me); B.mi = {i: k for k, i in enumerate(B.me)}
lr = np.log(1 + B.R['SPY']); B._vol = np.full(n, np.nan)
for i in range(31, n): B._vol[i] = max(lr[i-9:i+1].std(ddof=1), lr[i-29:i+1].std(ddof=1)) * 252 ** .5
print("\nB. Trend half alone (2x S&P built from the index, else T-bills), 1990 - Jun 2007")
table(lambda: B.Live(band=.02, rot='none'), '1990-01-02', '2007-06-29', [('1990-01-02', '1998-12-31'), ('1999-01-04', '2007-06-29')], ('1990', '1998', '2001', '2002'))
