"""2026-11-20, owner: "add Berkshire as a position, and something defensive like XLU". Same engine, costs and taxes
as better.py. XLU itself is reserved for the Robinhood strategy; XLU prices stand in for a utilities fund (VPU is the
non-overlapping one) and XLP for staples. Named before running:
  rot+brk / rot+util / rot+stap / rot+brk+util / rot+all3   the fund(s) added to the rotation list (still top 2)
  fb=util / fb=stap / fb=brk     the trend half holds that fund when the S&P trend is off (if its 6-month return
                                 beats T-bills, else cash), in place of IEF
  brk20 / util20 / brk10+util10  that share of the money bought once and held, the rest on the live rules
  vti20 (reference, added after the first run): the same with plain VTI, to see whether Berkshire matters or only
  holding does; brk30
Part B: the trend half alone on 2000 - Jun 2007 with each fallback."""
import os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, better as B
NEW = {'BRK': 'BRK-B', 'UTIL': 'XLU', 'STAP': 'XLP'}
def load(dates):
    for k, sym in NEW.items():
        p = B.yh(sym); B.X[k] = np.array([p[d] for d in dates]); B.R[k] = np.r_[0, B.X[k][1:] / B.X[k][:-1] - 1]
        ev = (B._dl(sym).get('events') or {}).get('dividends') or {}; raw = B._raw(sym); rd = sorted(raw); a = np.zeros(len(dates)); ix = {d: i for i, d in enumerate(dates)}
        for v in ev.values():
            d = dt.datetime.utcfromtimestamp(v['date']).date().isoformat()
            if d in ix:
                pv = [x for x in rd if x < d]
                if pv: a[ix[d]] += v['amount'] / raw[pv[-1]]
        B.DY[k] = a; B.QUAL.add(k)
class L2(B.Live):
    def __init__(s, rotu=None, fb='IEF', **k):
        super().__init__(**k); s.rotu = rotu or B.ROT; s.fb = fb; s.picks = {}
    def step(s, i):
        tr = False
        if not np.isnan(B.sma[i]):
            g = B.X['SPY'][i] / B.sma[i] - 1; new = (g > s.band) if s.on is None else ((g > -s.band) if s.on else (g > s.band))
            if new != s.on: s.on = new; tr = True
        if i in B.mes and B.mi[i] >= 10:
            j = B.me[B.mi[i] - 6]; cr = np.prod(1 + B.C[j + 1:i + 1]) - 1; nr = {}
            if s.rot_kind != 'none':
                for m, t in sorted(((B.X[t][i] / B.X[t][j] - 1, t) for t in s.rotu), reverse=True)[:2]:
                    if m > cr: nr[t] = 0.5; s.picks[t] = s.picks.get(t, 0) + 1
            if nr != s.rot: s.rot = nr; tr = True
            ok = B.X[s.fb][i] / B.X[s.fb][j] - 1 > cr
            if ok != s.iefok:
                s.iefok = ok
                if s.on is not None and not s.on: tr = True
        vs = s.vsq[i] if s.on else 1.0
        if vs != s.vsp: s.vsp = vs; tr = True
        pn = bool(B.PANIC[i]) and s.on is not None and not s.on and s.panic > 0
        if pn != s.pan: s.pan = pn; tr = True
        return tr
    def target(s):
        t = super().target()
        if s.fb != 'IEF' and 'IEF' in t: t[s.fb] = t.get(s.fb, 0) + t.pop('IEF')
        return t
def table(V, start, end, halves):
    print(f"{'':13s}| before tax: CAGR Sharpe MaxDD worst yr | after tax CAGR MaxDD | " + ' | '.join(f"{a[:4]}-{b[:4]} pre/after" for a, b in halves) + " | 2008  2022")
    for nm, f in V.items():
        a = f(start=start, end=end); t = f(start=start, end=end, tax=True); sa, st = B.stats(a[0], a[1]), B.stats(t[0], t[1])
        h = [B.stats(*f(start=x, end=y, tax=tx)[:2])[0] for x, y in halves for tx in (False, True)]
        nav = np.r_[1, a[0]]; r = nav[1:] / nav[:-1] - 1; yr = {}
        for d, x in zip(a[1], r): yr.setdefault(d[:4], []).append(x)
        yy = ' '.join(f"{(np.prod(1 + np.array(yr[y])) - 1) * 100:+5.0f}" if y in yr else '     ' for y in ('2008', '2022'))
        print(f"{nm:13s}| {sa[0]:5.1f} {sa[1]:5.2f} {sa[2]:6.1f} {sa[3]:6.1f}            | {st[0]:5.1f} {st[2]:6.1f}       | " + ' | '.join(f"{h[2*k]:5.1f} / {h[2*k+1]:5.1f}     " for k in range(len(halves))) + f" | {yy}")
S_ = lambda mk: (lambda **k: B.sim(mk, **k)); R_ = B.ROT
load(B.dates)
V = {'live': S_(lambda: L2()),
     'rot+brk': S_(lambda: L2(rotu=R_ + ['BRK'])), 'rot+util': S_(lambda: L2(rotu=R_ + ['UTIL'])), 'rot+stap': S_(lambda: L2(rotu=R_ + ['STAP'])),
     'rot+brk+util': S_(lambda: L2(rotu=R_ + ['BRK', 'UTIL'])), 'rot+all3': S_(lambda: L2(rotu=R_ + ['BRK', 'UTIL', 'STAP'])),
     'fb=util': S_(lambda: L2(fb='UTIL')), 'fb=stap': S_(lambda: L2(fb='STAP')), 'fb=brk': S_(lambda: L2(fb='BRK')),
     'brk20': lambda **k: B.blend([lambda: L2(), lambda: B.Static({'BRK': 1.0})], [.8, .2], **k),
     'util20': lambda **k: B.blend([lambda: L2(), lambda: B.Static({'UTIL': 1.0})], [.8, .2], **k),
     'brk10+util10': lambda **k: B.blend([lambda: L2(), lambda: B.Static({'BRK': .5, 'UTIL': .5})], [.8, .2], **k),
     'vti20 (ref)': lambda **k: B.blend([lambda: L2(), lambda: B.Static({'VTI': 1.0})], [.8, .2], **k),
     'brk30': lambda **k: B.blend([lambda: L2(), lambda: B.Static({'BRK': 1.0})], [.7, .3], **k),
     'BRK held': S_(lambda: B.Static({'BRK': 1.0})), 'utilities held': S_(lambda: B.Static({'UTIL': 1.0})), 'staples held': S_(lambda: B.Static({'STAP': 1.0})), 'SPY held': S_(lambda: B.Static({'SPY': 1.0}))}
print("A. Whole strategy, Jul 2007 - 19 Nov 2026")
table(V, '2007-07-02', '9999', [('2007-07-02', '2015-12-31'), ('2016-01-04', '9999')])
x = L2(rotu=R_ + ['BRK', 'UTIL', 'STAP']); B.sim(lambda: x); tot = sum(x.picks.values())
print("   rot+all3, share of monthly picks: " + ', '.join(f"{k} {v / tot:.0%}" for k, v in sorted(x.picks.items(), key=lambda z: -z[1])))
# ---- B. 2000 - Jun 2007, trend half alone
sp = B.yh('SPY'); irx = B._raw('^IRX'); xs = {k: B.yh(s) for k, s in NEW.items()}; d2 = [d for d in sorted(sp) if '1999-01-04' <= d <= '2007-06-29' and all(d in xs[k] for k in xs)]; n2 = len(d2); y = 4.5; C2 = np.zeros(n2)
for i, d in enumerate(d2): y = irx.get(d, y); C2[i] = y / 100 / 252
B.dates, B.n, B.C = d2, n2, C2; B.X = {'SPY': np.array([sp[d] for d in d2])}; B.R = {'SPY': np.r_[0, B.X['SPY'][1:] / B.X['SPY'][:-1] - 1]}; B.DY = {}
B.R['SSO'] = 2 * B.R['SPY'] - C2 - 0.0091 / 252; B.X['SSO'] = np.cumprod(1 + B.R['SSO']); B.X['IEF'] = np.cumprod(1 + C2); B.R['IEF'] = np.r_[0, C2[1:]]
load(d2)
for k in B.X: B.DY.setdefault(k, np.zeros(n2))
c = np.cumsum(np.insert(B.X['SPY'], 0, 0)); B.sma = np.full(n2, np.nan); B.sma[199:] = (c[200:] - c[:-200]) / 200
B.me = [i for i in range(n2 - 1) if d2[i][:7] != d2[i + 1][:7]]; B.mes = set(B.me); B.mi = {i: k for k, i in enumerate(B.me)}
P2 = np.zeros(n2, bool); p = False
for i, d in enumerate(d2):
    v = B._vx.get(d)
    if v is not None: p = (v >= 25.0) if p else (v >= 30.0)
    P2[i] = p
B.PANIC = P2; lr = np.log(1 + B.R['SPY']); B._vol = np.full(n2, np.nan)
for i in range(31, n2): B._vol[i] = max(lr[i-9:i+1].std(ddof=1), lr[i-29:i+1].std(ddof=1)) * 252 ** .5
st = d2[230]
print(f"\nB. Trend half alone, {st} - Jun 2007 (S&P -47%): what it holds while the trend is off")
V2 = {'T-bills': S_(lambda: L2(rot='none')), 'fb=util': S_(lambda: L2(rot='none', fb='UTIL')), 'fb=stap': S_(lambda: L2(rot='none', fb='STAP')), 'fb=brk': S_(lambda: L2(rot='none', fb='BRK')),
      'BRK held': S_(lambda: B.Static({'BRK': 1.0})), 'utilities held': S_(lambda: B.Static({'UTIL': 1.0})), 'staples held': S_(lambda: B.Static({'STAP': 1.0})), 'SPY held': S_(lambda: B.Static({'SPY': 1.0}))}
table(V2, st, '2007-06-29', [(st, '2002-12-31'), ('2003-01-02', '2007-06-29')])
