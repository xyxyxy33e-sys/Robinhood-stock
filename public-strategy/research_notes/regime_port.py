"""2026-11-20, owner: lean towards the QQQ (Robinhood) strategy "structurally, no overlapping etf".
A port of that strategy's STRUCTURE onto funds it does not trade. Same engine, costs and taxes as better.py.
Ported (from paper-track/state.py, read only): the six-state 50/200 classifier with 1% hysteresis; the 20/100 fast
re-entry map; rows A 40% core / 60% 3x, B 50% core / 50% cash, C 100% core, D 100% 2x (cash when the index is under 2%
above its 200-day), E and F cash; extension trim v2 (held votes on 10/12/15% above the 100/150/200-day; a vote takes the
3x out and a sixth of the core per vote; steps down on a 15-session high; resets after 3 sessions out of A); 20% vol
target on max(10, 30)-day realized vol; trade on a regime change or 5% drift.
NOT ported: the VIXM sleeve, the breadth half of the D gate, the D ladder, deep-E and VIX-panic rows.
Funds: core VTI (for SPMO), 3x UPRO (for TQQQ; built from SPY before Jun 2009), 2x SSO (for QLD), cash T-bills (BOXX).
Named before running:
  port-spy     signals read on SPY          port-qqq   signals read on QQQ (read only), same S&P funds
  port-2x      port-spy with SSO in place of UPRO      port-5050  port-spy with A = 50/50
  live+port    half the money in live and half in port-spy, never rebalanced between them (live+portq: port-qqq)"""
import os, sys, json, time, urllib.request, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, better as B
def sma_(x, k):
    c = np.cumsum(np.insert(x, 0, 0)); s = np.full(len(x), np.nan); s[k - 1:] = (c[k:] - c[:-k]) / k; return s
def classify(v, a, b, buf=.01):
    ma, mb = sma_(v, a), sma_(v, b); out = []; sa = sb = None
    for i in range(len(v)):
        if np.isnan(mb[i]): out.append('F'); continue
        if v[i] > ma[i] * (1 + buf): sa = True
        elif v[i] < ma[i] * (1 - buf): sa = False
        if v[i] > mb[i] * (1 + buf): sb = True
        elif v[i] < mb[i] * (1 - buf): sb = False
        cr = ma[i] > mb[i]
        out.append('A' if sa and sb and cr else 'B' if sa and sb else 'C' if sa and not sb else 'D' if (not sa) and sb else 'E' if (not sa) and (not sb) and cr else 'F')
    return out
FAST = {('B', 'A'): 'A', ('B', 'B'): 'A', ('C', 'A'): 'A', ('C', 'B'): 'A', ('F', 'A'): 'C', ('F', 'B'): 'C', ('F', 'C'): 'C'}
def prep(sig):
    v = B.X[sig]; mac = classify(v, 50, 200); fst = classify(v, 20, 100); eff = [FAST.get((m, f), m) for m, f in zip(mac, fst)]
    g = {k: v / sma_(v, k) - 1 for k in (100, 150, 200)}; lr = np.log(1 + B.R[sig]); n = len(v); vol = np.full(n, np.nan)
    for i in range(31, n): vol[i] = max(lr[i-9:i+1].std(ddof=1), lr[i-29:i+1].std(ddof=1)) * 252 ** .5
    held = np.zeros(n, int); h = 0; out_run = 99
    for i in range(n):
        if eff[i] == 'A':
            raw = 0 if np.isnan(g[200][i]) else int(g[100][i] > .10) + int(g[150][i] > .12) + int(g[200][i] > .15)
            if out_run > 3: h = 0
            out_run = 0
            if raw > h: h = raw
            elif h > raw and i >= 15 and v[i] >= v[i-14:i+1].max(): h -= 1
        else: out_run += 1
        held[i] = h if eff[i] == 'A' else 0
    return dict(mac=mac, eff=eff, g200=g[200], vol=vol, held=held)
class Port:
    def __init__(s, sig='SPY', a=(.40, .60), three='UPRO', vt=.20):
        s.p = PRE[sig]; s.a, s.three, s.vt = a, three, vt; s.w = {}; s.key = None; s.t = {}
    def row(s, i):
        p = s.p; e = p['eff'][i]
        if e == 'A':
            h = p['held'][i]; c = s.a[0] * max(0, 1 - h / 6); r = {'VTI': c, s.three: (s.a[1] if h == 0 else 0)}
        elif e == 'B': r = {'VTI': .5}
        elif e == 'C': r = {'VTI': 1.0}
        elif e == 'D': r = {} if (p['mac'][i] == 'D' and p['g200'][i] < .02) else {'SSO': 1.0}
        else: r = {}
        m = 1.0 if (not s.vt or np.isnan(p['vol'][i]) or p['vol'][i] <= 0) else min(1.0, s.vt / p['vol'][i])
        out = {}
        for k, x in r.items():
            if x > 0: out[k] = out.get(k, 0) + x * m
        return out
    def step(s, i):
        p = s.p
        if s.w:
            tot = 1 + sum(x * B.R[k][i] for k, x in s.w.items()) + (1 - sum(s.w.values())) * B.C[i]
            s.w = {k: x * (1 + B.R[k][i]) / tot for k, x in s.w.items()}
        t = s.row(i); key = (p['eff'][i], int(p['held'][i]), p['mac'][i] == 'D' and p['g200'][i] < .02)
        drift = sum(abs(t.get(k, 0) - s.w.get(k, 0)) for k in set(t) | set(s.w)) + abs(sum(t.values()) - sum(s.w.values()))
        tr = key != s.key or drift > .05
        s.key = key
        if tr: s.t = t; s.w = dict(t)
        return tr
    def target(s): return dict(s.t)
def add(sym, like=None, lev=None):
    if lev:
        r = lev * B.R[like] - (lev - 1) * B.C - 0.0091 / 252
        if sym in B.px:
            real = np.array([B.px[sym].get(d, np.nan) for d in B.dates]); rr = np.r_[0, real[1:] / real[:-1] - 1]; r = np.where(np.isnan(rr), r, rr)
        B.R[sym] = r; r0 = r.copy(); r0[0] = 0; B.X[sym] = np.cumprod(1 + r0)
    else:
        p = B.yh(sym); B.X[sym] = np.array([p[d] for d in B.dates]); B.R[sym] = np.r_[0, B.X[sym][1:] / B.X[sym][:-1] - 1]
    B.DY.setdefault(sym, np.zeros(len(B.dates))); B.QUAL.add(sym)
def table(V, start, end, halves):
    print(f"{'':10s}| before tax: CAGR Sharpe MaxDD worst yr | after tax CAGR MaxDD | " + ' | '.join(f"{a[:4]}-{b[:4]} pre/after" for a, b in halves) + " | trade days/yr turnover")
    for nm, f in V.items():
        a = f(start=start, end=end); t = f(start=start, end=end, tax=True); sa, st = B.stats(a[0], a[1]), B.stats(t[0], t[1])
        h = [B.stats(*f(start=x, end=y, tax=tx)[:2])[0] for x, y in halves for tx in (False, True)]
        print(f"{nm:10s}| {sa[0]:5.1f} {sa[1]:5.2f} {sa[2]:6.1f} {sa[3]:6.1f}            | {st[0]:5.1f} {st[2]:6.1f}       | " + ' | '.join(f"{h[2*k]:5.1f} / {h[2*k+1]:5.1f}     " for k in range(len(halves))) + f" | {a[2] / (len(a[1]) / 252):5.1f}  {a[3] / (len(a[1]) / 252) * 100:5.0f}%")
S_ = lambda mk: (lambda **k: B.sim(mk, **k))
# ---- A. 2007-2026
B.px['UPRO'] = B.yh('UPRO'); add('QQQ'); add('UPRO', like='SPY', lev=3)
PRE = {s: prep(s) for s in ('SPY', 'QQQ')}
V = {'live': S_(lambda: B.Live()), 'port-spy': S_(lambda: Port('SPY')), 'port-qqq': S_(lambda: Port('QQQ')), 'port-2x': S_(lambda: Port('SPY', three='SSO')),
     'port-5050': S_(lambda: Port('SPY', a=(.5, .5))), 'live+port': lambda **k: B.blend([lambda: B.Live(), lambda: Port('SPY')], [.5, .5], **k),
     'live+portq': lambda **k: B.blend([lambda: B.Live(), lambda: Port('QQQ')], [.5, .5], **k),
     'SPY held': S_(lambda: B.Static({'SPY': 1.0}))}
print("A. Jul 2007 - 19 Nov 2026")
table(V, '2007-07-02', '9999', [('2007-07-02', '2015-12-31'), ('2016-01-04', '9999')])
e = PRE['SPY']['eff']; s0 = B.dates.index('2007-07-02'); print("   days in each state (SPY signal): " + ', '.join(f"{k} {np.mean([x == k for x in e[s0:]]):.0%}" for k in 'ABCDEF'))
a, b = B.sim(lambda: B.Live()), B.sim(lambda: Port('SPY')); ra, rb = (np.r_[x[0][0] - 1, x[0][1:] / x[0][:-1] - 1] for x in (a, b)); print(f"   daily correlation of port-spy with live: {np.corrcoef(ra, rb)[0, 1]:.2f}")
# ---- B. 1960 - Jun 2007 on the S&P index
f = os.path.join(B.CACHE, 'GSPC_long.json'); d = json.load(open(f))['chart']['result'][0]
gs = {(dt.datetime(1970, 1, 1) + dt.timedelta(seconds=t)).date().isoformat(): v for t, v in zip(d['timestamp'], d['indicators']['quote'][0]['close']) if v}
irx = B._raw('^IRX'); dates = [x for x in sorted(gs) if '1958-06-01' <= x <= '2007-06-29']; n = len(dates); y = 3.0; C = np.zeros(n)
for i, x in enumerate(dates): y = irx.get(x, y); C[i] = y / 100 / 252
p = np.array([gs[x] for x in dates]); r1 = np.r_[0, p[1:] / p[:-1] - 1] + 0.03 / 252
B.dates, B.n, B.C = dates, n, C; B.X = {'SPY': np.cumprod(1 + r1)}; B.R = {'SPY': np.r_[0, B.X['SPY'][1:] / B.X['SPY'][:-1] - 1]}; B.px = {}; B.DY = {}
B.X['VTI'] = B.X['SPY']; B.R['VTI'] = B.R['SPY']; add('SSO', like='SPY', lev=2); add('UPRO', like='SPY', lev=3); B.X['IEF'] = np.cumprod(1 + C); B.R['IEF'] = np.r_[0, C[1:]]
for k in B.X: B.DY.setdefault(k, np.zeros(n))
B.sma = sma_(B.X['SPY'], 200); B.me = [i for i in range(n - 1) if dates[i][:7] != dates[i + 1][:7]]; B.mes = set(B.me); B.mi = {i: k for k, i in enumerate(B.me)}
B.PANIC = np.zeros(n, bool); lr = np.log(1 + B.R['SPY']); B._vol = np.full(n, np.nan)
for i in range(31, n): B._vol[i] = max(lr[i-9:i+1].std(ddof=1), lr[i-29:i+1].std(ddof=1)) * 252 ** .5
PRE = {'SPY': prep('SPY')}
print("\nB. 1960 - Jun 2007 on the S&P 500 index (2x and 3x funds built; no rotation funds exist, so 'live trend' is the live trend half alone)")
V2 = {'live trend': S_(lambda: B.Live(panic=0, rot='none')), 'port-spy': S_(lambda: Port('SPY')), 'port-2x': S_(lambda: Port('SPY', three='SSO')), 'port-5050': S_(lambda: Port('SPY', a=(.5, .5))),
      'S&P held': S_(lambda: B.Static({'SPY': 1.0}))}
table(V2, '1960-01-04', '2007-06-29', [('1960-01-04', '1983-12-30'), ('1984-01-03', '2007-06-29')])
for a_, b_ in (('1973-01-02', '1974-12-31'), ('1987-10-01', '1987-10-30'), ('2000-03-24', '2002-10-09')):
    print(f"   {a_} to {b_}: " + ', '.join(f"{nm} {(lambda x: (x[0][-1] - 1) * 100)(f(start=a_, end=b_)):+.0f}%" for nm, f in V2.items()))
# ---- C. Dec 1999 - Jun 2007 with real SPY and QQQ (the dot-com bust), S&P funds built from SPY
sp, qq = B.yh('SPY'), B.yh('QQQ'); d2 = [x for x in sorted(qq) if x <= '2007-06-29' and x in sp]; n2 = len(d2); y = 4.5; C2 = np.zeros(n2)
for i, x in enumerate(d2): y = irx.get(x, y); C2[i] = y / 100 / 252
B.dates, B.n, B.C = d2, n2, C2; B.X = {'SPY': np.array([sp[x] for x in d2]), 'QQQ': np.array([qq[x] for x in d2])}; B.R = {k: np.r_[0, v[1:] / v[:-1] - 1] for k, v in B.X.items()}; B.px = {}; B.DY = {}
B.X['VTI'] = B.X['SPY']; B.R['VTI'] = B.R['SPY']; add('SSO', like='SPY', lev=2); add('UPRO', like='SPY', lev=3); B.X['IEF'] = np.cumprod(1 + C2); B.R['IEF'] = np.r_[0, C2[1:]]
for k in B.X: B.DY.setdefault(k, np.zeros(n2))
B.sma = sma_(B.X['SPY'], 200); B.me = [i for i in range(n2 - 1) if d2[i][:7] != d2[i + 1][:7]]; B.mes = set(B.me); B.mi = {i: k for k, i in enumerate(B.me)}
B.PANIC = np.zeros(n2, bool); lr = np.log(1 + B.R['SPY']); B._vol = np.full(n2, np.nan)
for i in range(31, n2): B._vol[i] = max(lr[i-9:i+1].std(ddof=1), lr[i-29:i+1].std(ddof=1)) * 252 ** .5
PRE = {s: prep(s) for s in ('SPY', 'QQQ')}
print(f"\nC. {d2[201]} - Jun 2007, real SPY and QQQ; S&P funds only")
V3 = {'live trend': S_(lambda: B.Live(panic=0, rot='none')), 'port-spy': S_(lambda: Port('SPY')), 'port-qqq': S_(lambda: Port('QQQ')), 'SPY held': S_(lambda: B.Static({'SPY': 1.0}))}
table(V3, d2[201], '2007-06-29', [(d2[201], '2002-12-31'), ('2003-01-02', '2007-06-29')])
# ---- D. 1972 - Jun 2007: signals read on the Nasdaq Composite (QQQ did not exist), S&P 500 index funds built
f = os.path.join(B.CACHE, 'IXIC_long.json')
if not os.path.exists(f):
    u = f"https://query2.finance.yahoo.com/v8/finance/chart/%5EIXIC?period1=0&period2={int(time.time())}&interval=1d"
    open(f, 'wb').write(urllib.request.urlopen(urllib.request.Request(u, headers=B.UA), timeout=60).read())
d = json.load(open(f))['chart']['result'][0]
ix = {(dt.datetime(1970, 1, 1) + dt.timedelta(seconds=t)).date().isoformat(): v for t, v in zip(d['timestamp'], d['indicators']['quote'][0]['close']) if v}
d3 = [x for x in sorted(ix) if x in gs and x <= '2007-06-29']; n3 = len(d3); y = 5.0; C3 = np.zeros(n3)
for i, x in enumerate(d3): y = irx.get(x, y); C3[i] = y / 100 / 252
p = np.array([gs[x] for x in d3]); r1 = np.r_[0, p[1:] / p[:-1] - 1] + 0.03 / 252
B.dates, B.n, B.C = d3, n3, C3; B.X = {'SPY': np.cumprod(1 + r1), 'QQQ': np.array([ix[x] for x in d3])}; B.R = {k: np.r_[0, v[1:] / v[:-1] - 1] for k, v in B.X.items()}; B.px = {}; B.DY = {}
B.X['VTI'] = B.X['SPY']; B.R['VTI'] = B.R['SPY']; add('SSO', like='SPY', lev=2); add('UPRO', like='SPY', lev=3); B.X['IEF'] = np.cumprod(1 + C3); B.R['IEF'] = np.r_[0, C3[1:]]
for k in B.X: B.DY.setdefault(k, np.zeros(n3))
B.sma = sma_(B.X['SPY'], 200); B.me = [i for i in range(n3 - 1) if d3[i][:7] != d3[i + 1][:7]]; B.mes = set(B.me); B.mi = {i: k for k, i in enumerate(B.me)}
B.PANIC = np.zeros(n3, bool); lr = np.log(1 + B.R['SPY']); B._vol = np.full(n3, np.nan)
for i in range(31, n3): B._vol[i] = max(lr[i-9:i+1].std(ddof=1), lr[i-29:i+1].std(ddof=1)) * 252 ** .5
PRE = {s: prep(s) for s in ('SPY', 'QQQ')}; st3 = d3[260]
print(f"\nD. {st3} - Jun 2007: signals on the Nasdaq Composite price index ('port-nasdaq'), S&P 500 funds built")
V4 = {'live trend': S_(lambda: B.Live(panic=0, rot='none')), 'port-spy': S_(lambda: Port('SPY')), 'port-nasdaq': S_(lambda: Port('QQQ')), 'S&P held': S_(lambda: B.Static({'SPY': 1.0}))}
table(V4, st3, '2007-06-29', [(st3, '1989-12-29'), ('1990-01-02', '2007-06-29')])
for a_, b_ in (('1973-01-02', '1974-12-31'), ('1987-10-01', '1987-10-30'), ('2000-03-24', '2002-10-09')):
    print(f"   {a_} to {b_}: " + ', '.join(f"{nm} {(lambda x: (x[0][-1] - 1) * 100)(f(start=a_, end=b_)):+.0f}%" for nm, f in V4.items()))
