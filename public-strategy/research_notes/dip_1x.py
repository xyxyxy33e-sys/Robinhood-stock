"""2026-11-20, owner: 1x in place of 2x "during a dip and when recovering from a dip". Live rules otherwise.
(Logged before: a 1x middle step by distance from the 200-day, rejected.) Named before running; "1x" is tried two
ways, as VTI at full weight ("v") and as SSO at half weight with the rest in cash ("h", no second fund):
  dip5 / dip8    while the trend is on and SPY is more than 5% / 8% below its 252-session closing high
  rec20 / rec60  for the first 20 / 60 sessions after the trend turns back on
  rechigh        from the trend turning back on until SPY closes at a new 252-session high
  dip5+rechigh   both
Part B: the trend half alone on 1960 - Jun 2007."""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, better as B
def hi252(x):
    return np.array([x[max(0, i - 251):i + 1].max() for i in range(len(x))])
class D(B.Live):
    def __init__(s, rule=None, form='v', **k): super().__init__(**k); s.rule, s.form = rule, form; s.flag = False; s.since = 10**6; s.wait = False
    def step(s, i):
        was = s.on; tr = super().step(i)
        if s.on and not was and was is not None: s.since = 0; s.wait = True
        elif s.on: s.since += 1
        athigh = B.X['SPY'][i] >= B.HI[i] * (1 - 1e-12); dd = B.X['SPY'][i] / B.HI[i] - 1
        if athigh: s.wait = False
        r = s.rule or ''; f = False
        if 'dip5' in r: f |= dd < -.05
        if 'dip8' in r: f |= dd < -.08
        if 'rec20' in r: f |= s.since < 20
        if 'rec60' in r: f |= s.since < 60
        if 'rechigh' in r: f |= s.wait
        f = bool(f and s.on)
        if f != s.flag:
            s.flag = f
            if s.on: tr = True
        return tr
    def target(s):
        t = super().target()
        if not (s.on and s.flag and 'SSO' in t): return t
        th = 0.5 if s.rot_kind != 'none' else 1.0; x = t.pop('SSO')
        if s.form == 'v': t['VTI'] = t.get('VTI', 0) + min(th, 2 * x)
        else: t['SSO'] = min(x, th * 0.5)
        return t
RULES = ('dip5', 'dip8', 'rec20', 'rec60', 'rechigh', 'dip5+rechigh')
def table(extra, start, end, halves):
    print(f"{'':15s}| before tax: CAGR Sharpe MaxDD worst yr | after tax | " + ' | '.join(f"{a[:4]}-{b[:4]} pre/after" for a, b in halves) + " | trade days/yr | days at 1x")
    for nm, k in [('live', {})] + [(f"{r} ({f})", dict(rule=r, form=f)) for r in RULES for f in ('v', 'h')]:
        mk = lambda: D(band=.02, **{**extra, **k})
        a = B.sim(mk, start=start, end=end); t = B.sim(mk, start=start, end=end, tax=True); sa, st = B.stats(a[0], a[1]), B.stats(t[0], t[1])
        h = [B.stats(*B.sim(mk, start=x, end=y, tax=tx)[:2])[0] for x, y in halves for tx in (False, True)]
        s = mk(); one = tot = 0
        for i in range(200, B.n):
            s.step(i)
            if start <= B.dates[i] <= end: tot += 1; one += s.flag
        print(f"{nm:15s}| {sa[0]:5.1f} {sa[1]:5.2f} {sa[2]:6.1f} {sa[3]:6.1f}            | {st[0]:5.1f}     | " + ' | '.join(f"{h[2*j]:5.1f} / {h[2*j+1]:5.1f}     " for j in range(len(halves))) + f" | {a[2] / (len(a[1]) / 252):5.1f}         | {one / tot:4.0%}")
B.HI = hi252(B.X['SPY'])
print("A. Whole strategy, Jul 2007 - 19 Nov 2026")
table({}, '2007-07-02', '9999', [('2007-07-02', '2015-12-31'), ('2016-01-04', '9999')])
d = json.load(open(os.path.join(B.CACHE, 'GSPC_long.json')))['chart']['result'][0]
gs = {(dt.datetime(1970, 1, 1) + dt.timedelta(seconds=t)).date().isoformat(): v for t, v in zip(d['timestamp'], d['indicators']['quote'][0]['close']) if v}
irx = B._raw('^IRX'); dates = [x for x in sorted(gs) if '1958-06-01' <= x <= '2007-06-29']; n = len(dates); y = 3.0; C = np.zeros(n)
for i, x in enumerate(dates): y = irx.get(x, y); C[i] = y / 100 / 252
p = np.array([gs[x] for x in dates]); r1 = np.r_[0, p[1:] / p[:-1] - 1] + 0.03 / 252; r2 = 2 * r1 - C - 0.009 / 252
B.dates, B.n, B.C = dates, n, C; B.X = {'SPY': np.cumprod(1 + r1), 'SSO': np.cumprod(1 + r2), 'IEF': np.cumprod(1 + C)}; B.X['VTI'] = B.X['SPY']; B.R = {s: np.r_[0, v[1:] / v[:-1] - 1] for s, v in B.X.items()}; B.DY = {s: np.zeros(n) for s in B.X}
c = np.cumsum(np.insert(B.X['SPY'], 0, 0)); B.sma = np.full(n, np.nan); B.sma[199:] = (c[200:] - c[:-200]) / 200
B.me = [i for i in range(n - 1) if dates[i][:7] != dates[i + 1][:7]]; B.mes = set(B.me); B.mi = {i: k for k, i in enumerate(B.me)}; B.PANIC = np.zeros(n, bool)
lr = np.log(1 + B.R['SPY']); B._vol = np.full(n, np.nan)
for i in range(31, n): B._vol[i] = max(lr[i-9:i+1].std(ddof=1), lr[i-29:i+1].std(ddof=1)) * 252 ** .5
B.HI = hi252(B.X['SPY'])
print("\nB. Trend half alone, 1960 - Jun 2007")
table(dict(panic=0, rot='none'), '1960-01-04', '2007-06-29', [('1960-01-04', '1983-12-30'), ('1984-01-03', '2007-06-29')])
