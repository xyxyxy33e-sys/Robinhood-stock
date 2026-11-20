"""2026-11-20, owner: "test it" - a buffer on the SSO volatility-target steps, which flicker when volatility sits on a
rounding boundary (Jan 2015: eight flips between 1.00 and 0.75 in a month). Live rules otherwise (2% band).
sc = min(1, 30% / (2 x vol)); live: step = sc rounded to the nearest quarter, floor 0.25. Named before running:
  live        no buffer
  buf 0.025   keep the current step until sc is more than 0.025 past the boundary, either way
  buf 0.05    the same with 0.05
  up 0.05     cut at once as now; step back up only when sc is more than 0.05 past the boundary
  up 0.10     the same with 0.10
Part B: the trend half alone on 1960 - Jun 2007 (S&P index, 2x built)."""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, better as B
def mk_vsq(dn, up):          # 30% / (2 x vol) is left uncapped so the top step can also be buffered
    def f(T):
        if not T: return np.ones(B.n)
        out = np.ones(B.n); cur = 1.0
        for i in range(B.n):
            v = B._vol[i]
            if not np.isnan(v) and v > 0:
                raw = T / (2 * v); tgt = max(0.25, round(min(1.0, raw) * 4) / 4)
                if tgt < cur and raw < cur - 0.125 - dn: cur = tgt
                elif tgt > cur and raw > tgt - 0.125 + up: cur = tgt
            out[i] = cur
        return out
    return f
VAR = (('live', 0, 0), ('buf 0.025', .025, .025), ('buf 0.05', .05, .05), ('up 0.05', 0, .05), ('up 0.10', 0, .10))
def table(mk, start, end, halves):
    print(f"{'':10s}| before tax: CAGR Sharpe MaxDD worst yr | after tax | " + ' | '.join(f"{a[:4]}-{b[:4]} pre/after" for a, b in halves) + " | size changes/yr | trade days/yr | avg SSO size when on")
    for nm, dn, up in VAR:
        B._vsq = mk_vsq(dn, up)
        a = B.sim(mk, start=start, end=end); t = B.sim(mk, start=start, end=end, tax=True); sa, st = B.stats(a[0], a[1]), B.stats(t[0], t[1])
        h = [B.stats(*B.sim(mk, start=x, end=y, tax=tx)[:2])[0] for x, y in halves for tx in (False, True)]
        s = mk(); ch = 0; prev = None; on_days = 0; sz = 0.0
        for i in range(200, B.n):
            s.step(i)
            if start <= B.dates[i] <= end and s.on:
                on_days += 1; sz += s.vsp
                if prev is not None and s.vsp != prev: ch += 1
                prev = s.vsp
            elif not s.on: prev = None
        yrs = len(a[1]) / 252
        print(f"{nm:10s}| {sa[0]:5.1f} {sa[1]:5.2f} {sa[2]:6.1f} {sa[3]:6.1f}            | {st[0]:5.1f}     | " + ' | '.join(f"{h[2*k]:5.1f} / {h[2*k+1]:5.1f}     " for k in range(len(halves))) + f" | {ch / yrs:5.1f}           | {a[2] / yrs:5.1f}         | {sz / on_days:.2f}")
base = B._vsq(0.30); mine = mk_vsq(0, 0)(0.30); print("check: the no-buffer rule reproduces the live steps on", f"{np.mean(base == mine):.1%}", "of days")
print("A. Whole strategy, Jul 2007 - 19 Nov 2026")
table(lambda: B.Live(band=.02), '2007-07-02', '9999', [('2007-07-02', '2015-12-31'), ('2016-01-04', '9999')])
d = json.load(open(os.path.join(B.CACHE, 'GSPC_long.json')))['chart']['result'][0]
gs = {(dt.datetime(1970, 1, 1) + dt.timedelta(seconds=t)).date().isoformat(): v for t, v in zip(d['timestamp'], d['indicators']['quote'][0]['close']) if v}
irx = B._raw('^IRX'); dates = [x for x in sorted(gs) if '1959-01-01' <= x <= '2007-06-29']; n = len(dates); y = 3.0; C = np.zeros(n)
for i, x in enumerate(dates): y = irx.get(x, y); C[i] = y / 100 / 252
p = np.array([gs[x] for x in dates]); r1 = np.r_[0, p[1:] / p[:-1] - 1] + 0.03 / 252; r2 = 2 * r1 - C - 0.009 / 252
B.dates, B.n, B.C = dates, n, C; B.X = {'SPY': np.cumprod(1 + r1), 'SSO': np.cumprod(1 + r2), 'IEF': np.cumprod(1 + C)}; B.R = {s: np.r_[0, v[1:] / v[:-1] - 1] for s, v in B.X.items()}; B.DY = {s: np.zeros(n) for s in B.X}
c = np.cumsum(np.insert(B.X['SPY'], 0, 0)); B.sma = np.full(n, np.nan); B.sma[199:] = (c[200:] - c[:-200]) / 200
B.me = [i for i in range(n - 1) if dates[i][:7] != dates[i + 1][:7]]; B.mes = set(B.me); B.mi = {i: k for k, i in enumerate(B.me)}; B.PANIC = np.zeros(n, bool)
lr = np.log(1 + B.R['SPY']); B._vol = np.full(n, np.nan)
for i in range(31, n): B._vol[i] = max(lr[i-9:i+1].std(ddof=1), lr[i-29:i+1].std(ddof=1)) * 252 ** .5
print("\nB. Trend half alone, 1960 - Jun 2007")
table(lambda: B.Live(band=.02, panic=0, rot='none'), '1960-01-04', '2007-06-29', [('1960-01-04', '1983-12-30'), ('1984-01-03', '2007-06-29')])
