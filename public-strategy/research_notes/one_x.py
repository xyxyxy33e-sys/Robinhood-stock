"""2026-11-20, owner: "consider times hold 1x?" (after the SSO decay figures). Live rules otherwise (2% band, vol
target with the 0.025 buffer). Logged before: a middle 1x step by distance from the 200-day (rejected, 11 versions),
1.5x in place of 2x (11.0% / -19.3%). New here, named before running:
  mix          same exposure as live, built with the least borrowing: where the vol target has SSO at half size
               (1x exposure) hold VTI in full; at three-quarter size (1.5x) hold half SSO + half VTI; at a quarter, VTI half
  rate>3/4/5   hold VTI (1x) in place of SSO while the T-bill yield is above 3% / 4% / 5% (financing is dear)
  vol>18/22    hold VTI (1x) in place of SSO, at full weight, while S&P vol (max of 10/30-day) is above 18% / 22%
  1x always    VTI in place of SSO, no vol target (reference)
Part B: the trend half alone on 1960 - Jun 2007 (S&P index as the 1x fund, 2x built)."""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, better as B
class X(B.Live):
    def __init__(s, kind='live', thr=None, **k): super().__init__(**k); s.kind, s.thr, s.i = kind, thr, 0; s.flag = False
    def step(s, i):
        s.i = i; tr = super().step(i); f = False
        if s.kind == 'rate': f = B.C[i] * 252 > s.thr
        if s.kind == 'vol': f = (not np.isnan(B._vol[i])) and B._vol[i] > s.thr
        if f != s.flag:
            s.flag = f
            if s.on: tr = True
        return tr
    def target(s):
        t = super().target()
        if not s.on or 'SSO' not in t: return t
        th = 0.5 if s.rot_kind != 'none' else 1.0
        if s.kind == 'mix':
            e = 2 * s.vsp; t.pop('SSO')
            if e <= 1: t['VTI'] = t.get('VTI', 0) + th * e
            else: t['SSO'] = th * (e - 1); t['VTI'] = t.get('VTI', 0) + th * (2 - e)
        elif s.kind == 'always' or (s.kind == 'rate' and s.flag):
            x = t.pop('SSO'); t['VTI'] = t.get('VTI', 0) + (th if s.kind == 'always' else min(th, 2 * x))
        elif s.kind == 'vol' and s.flag:
            t.pop('SSO'); t['VTI'] = t.get('VTI', 0) + th
        return t
VAR = (('live', {}), ('mix', dict(kind='mix')), ('rate>3%', dict(kind='rate', thr=.03)), ('rate>4%', dict(kind='rate', thr=.04)), ('rate>5%', dict(kind='rate', thr=.05)),
       ('vol>18%', dict(kind='vol', thr=.18)), ('vol>22%', dict(kind='vol', thr=.22)), ('1x always', dict(kind='always', vt=None)))
def table(extra, start, end, halves):
    print(f"{'':10s}| before tax: CAGR Sharpe MaxDD worst yr | after tax | " + ' | '.join(f"{a[:4]}-{b[:4]} pre/after" for a, b in halves) + " | trade days/yr | days in 1x fund")
    for nm, k in VAR:
        mk = lambda: X(band=.02, **{**extra, **k})
        a = B.sim(mk, start=start, end=end); t = B.sim(mk, start=start, end=end, tax=True); sa, st = B.stats(a[0], a[1]), B.stats(t[0], t[1])
        h = [B.stats(*B.sim(mk, start=x, end=y, tax=tx)[:2])[0] for x, y in halves for tx in (False, True)]
        s = mk(); one = tot = 0
        for i in range(200, B.n):
            s.step(i)
            if start <= B.dates[i] <= end:
                tot += 1; tg = s.target(); one += (tg.get('VTI', 0) > (0.26 if s.rot_kind != 'none' else 0)) and bool(s.on)
        print(f"{nm:10s}| {sa[0]:5.1f} {sa[1]:5.2f} {sa[2]:6.1f} {sa[3]:6.1f}            | {st[0]:5.1f}     | " + ' | '.join(f"{h[2*j]:5.1f} / {h[2*j+1]:5.1f}     " for j in range(len(halves))) + f" | {a[2] / (len(a[1]) / 252):5.1f}         | {one / tot:4.0%}")
print("A. Whole strategy, Jul 2007 - 19 Nov 2026 (T-bills were above 3% on " + f"{np.mean(B.C[B.dates.index('2007-07-02'):] * 252 > .03):.0%} of days, above 4% on {np.mean(B.C[B.dates.index('2007-07-02'):] * 252 > .04):.0%})")
table({}, '2007-07-02', '9999', [('2007-07-02', '2015-12-31'), ('2016-01-04', '9999')])
d = json.load(open(os.path.join(B.CACHE, 'GSPC_long.json')))['chart']['result'][0]
gs = {(dt.datetime(1970, 1, 1) + dt.timedelta(seconds=t)).date().isoformat(): v for t, v in zip(d['timestamp'], d['indicators']['quote'][0]['close']) if v}
irx = B._raw('^IRX'); dates = [x for x in sorted(gs) if '1959-01-01' <= x <= '2007-06-29']; n = len(dates); y = 3.0; C = np.zeros(n)
for i, x in enumerate(dates): y = irx.get(x, y); C[i] = y / 100 / 252
p = np.array([gs[x] for x in dates]); r1 = np.r_[0, p[1:] / p[:-1] - 1] + 0.03 / 252; r2 = 2 * r1 - C - 0.009 / 252
B.dates, B.n, B.C = dates, n, C; B.X = {'SPY': np.cumprod(1 + r1), 'SSO': np.cumprod(1 + r2), 'IEF': np.cumprod(1 + C)}; B.X['VTI'] = B.X['SPY']; B.R = {s: np.r_[0, v[1:] / v[:-1] - 1] for s, v in B.X.items()}; B.DY = {s: np.zeros(n) for s in B.X}
c = np.cumsum(np.insert(B.X['SPY'], 0, 0)); B.sma = np.full(n, np.nan); B.sma[199:] = (c[200:] - c[:-200]) / 200
B.me = [i for i in range(n - 1) if dates[i][:7] != dates[i + 1][:7]]; B.mes = set(B.me); B.mi = {i: k for k, i in enumerate(B.me)}; B.PANIC = np.zeros(n, bool)
lr = np.log(1 + B.R['SPY']); B._vol = np.full(n, np.nan)
for i in range(31, n): B._vol[i] = max(lr[i-9:i+1].std(ddof=1), lr[i-29:i+1].std(ddof=1)) * 252 ** .5
i0 = dates.index('1960-01-04')
print(f"\nB. Trend half alone, 1960 - Jun 2007 (T-bills above 3% on {np.mean(C[i0:] * 252 > .03):.0%} of days, above 4% on {np.mean(C[i0:] * 252 > .04):.0%}, above 5% on {np.mean(C[i0:] * 252 > .05):.0%})")
table(dict(panic=0, rot='none'), '1960-01-04', '2007-06-29', [('1960-01-04', '1983-12-30'), ('1984-01-03', '2007-06-29')])
