"""2026-11-20, owner: "lean more towards qqq strategy". Nasdaq-100 tilts of the live strategy, same engine, costs and
taxes as better.py. QQQ and QLD prices stand in for whatever Nasdaq fund would be traded (QQQ, QLD and TQQQ are
reserved for the Robinhood strategy; see STRATEGY-PUBLIC.md). Named before running:
  live        SSO on the SPY signal (the live rules)
  qld         trend half = QLD on QQQ's own 200-day signal and QQQ's own volatility
  half-half   trend half = 25% SSO on SPY's signal + 25% QLD on QQQ's signal
  qld/spy     trend half = QLD, switched by SPY's signal and volatility
  rot+qqq     live, with QQQ (1x) added to the rotation funds (top 2 of 8)
  half+rot    half-half and QQQ in the rotation
  qqq1x       trend half = QQQ unlevered on QQQ's signal (no vol target)
Second part: the trend half alone on 2000 - Jun 2007 (dot-com bust; 2x funds built from the index funds)."""
import os, sys, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, better as B
def roll(x):
    c = np.cumsum(np.insert(x, 0, 0)); s = np.full(len(x), np.nan); s[199:] = (c[200:] - c[:-200]) / 200; return s
def volq(r, T=0.30):
    lr = np.log(1 + r); v = np.full(len(r), np.nan)
    for i in range(31, len(r)): v[i] = max(lr[i-9:i+1].std(ddof=1), lr[i-29:i+1].std(ddof=1)) * 252 ** .5
    sc = np.minimum(1.0, T / (2 * np.where(v > 0, v, np.nan))); q = np.nan_to_num(np.round(sc * 4) / 4, nan=1.0); q[q < 0.25] = 0.25
    return q
def setup():
    B.SMA = {s: roll(B.X[s]) for s in ('SPY', 'QQQ')}; B.VSQ2 = {s: volq(B.R[s]) for s in ('SPY', 'QQQ')}
for s in ('QQQ', 'QLD'):
    p = B.yh(s); B.px[s] = p; B.X[s] = np.array([p[d] for d in B.dates]); B.R[s] = np.r_[0, B.X[s][1:] / B.X[s][:-1] - 1]
    ev = (B._dl(s).get('events') or {}).get('dividends') or {}; raw = B._raw(s); rd = sorted(raw); a = np.zeros(B.n)
    for v in ev.values():
        d = dt.datetime.utcfromtimestamp(v['date']).date().isoformat()
        if d in B.dates:
            pv = [x for x in rd if x < d]
            if pv: a[B.dates.index(d)] += v['amount'] / raw[pv[-1]]
    B.DY[s] = a; B.QUAL.add(s)
setup()
class N:
    """legs: [(signal, fund, weight, vol_target?)]; weights sum to the trend share. rot: rotation universe or None."""
    def __init__(s, legs, rot=B.ROT, panic=0.25):
        s.legs, s.rotu, s.panic = legs, rot, panic; s.on = [None] * len(legs); s.vs = [1.0] * len(legs); s.pan = [False] * len(legs); s.rot = {}; s.iefok = True
    def step(s, i):
        tr = False
        for k, (sig, fund, wt, vt) in enumerate(s.legs):
            m = B.SMA[sig][i]
            if not np.isnan(m):
                g = B.X[sig][i] / m - 1; new = (g > .01) if s.on[k] is None else ((g > -.01) if s.on[k] else (g > .01))
                if new != s.on[k]: s.on[k] = new; tr = True
            v = B.VSQ2[sig][i] if (s.on[k] and vt) else 1.0
            if v != s.vs[k]: s.vs[k] = v; tr = True
            p = bool(B.PANIC[i]) and s.on[k] is not None and not s.on[k] and s.panic > 0
            if p != s.pan[k]: s.pan[k] = p; tr = True
        if i in B.mes and B.mi[i] >= 10:
            j = B.me[B.mi[i] - 6]; cr = np.prod(1 + B.C[j + 1:i + 1]) - 1; nr = {}
            if s.rotu:
                for m, t in sorted(((B.X[t][i] / B.X[t][j] - 1, t) for t in s.rotu), reverse=True)[:2]:
                    if m > cr: nr[t] = 0.25
            if nr != s.rot: s.rot = nr; tr = True
            ok = B.X['IEF'][i] / B.X['IEF'][j] - 1 > cr
            if ok != s.iefok:
                s.iefok = ok
                if any(o is False for o in s.on): tr = True
        return tr
    def target(s):
        t = {}
        for k, (sig, fund, wt, vt) in enumerate(s.legs):
            if s.on[k] is None: continue
            if s.on[k]: t[fund] = t.get(fund, 0) + wt * s.vs[k]
            else:
                if s.iefok: t['IEF'] = t.get('IEF', 0) + wt * (1 - s.panic if s.pan[k] else 1)
                if s.pan[k]: t[fund] = t.get(fund, 0) + wt * s.panic * 0.5
        for a, x in s.rot.items(): t[a] = t.get(a, 0) + x
        return t
R8 = B.ROT + ['QQQ']
V = {'live': lambda: N([('SPY', 'SSO', .5, 1)]), 'qld': lambda: N([('QQQ', 'QLD', .5, 1)]),
     'half-half': lambda: N([('SPY', 'SSO', .25, 1), ('QQQ', 'QLD', .25, 1)]), 'qld/spy': lambda: N([('SPY', 'QLD', .5, 1)]),
     'rot+qqq': lambda: N([('SPY', 'SSO', .5, 1)], rot=R8), 'half+rot': lambda: N([('SPY', 'SSO', .25, 1), ('QQQ', 'QLD', .25, 1)], rot=R8),
     'qqq1x': lambda: N([('QQQ', 'QQQ', .5, 0)]), 'QQQ held': lambda: B.Static({'QQQ': 1.0}), 'SPY held': lambda: B.Static({'SPY': 1.0})}
def table(V, start, end, halves):
    print(f"{'':10s}| before tax: CAGR Sharpe MaxDD worst yr | after tax CAGR MaxDD | " + ' | '.join(f"{a[:4]}-{b[:4]} pre/after" for a, b in halves) + " | trade days/yr")
    out = {}
    for nm, mk in V.items():
        a = B.sim(mk, start=start, end=end); t = B.sim(mk, start=start, end=end, tax=True); sa, st = B.stats(a[0], a[1]), B.stats(t[0], t[1]); out[nm] = a
        h = [B.stats(*B.sim(mk, start=x, end=y, tax=tx)[:2])[0] for x, y in halves for tx in (False, True)]
        print(f"{nm:10s}| {sa[0]:5.1f} {sa[1]:5.2f} {sa[2]:6.1f} {sa[3]:6.1f}            | {st[0]:5.1f} {st[2]:6.1f}       | " + ' | '.join(f"{h[2*k]:5.1f} / {h[2*k+1]:5.1f}     " for k in range(len(halves))) + f" | {a[2] / (len(a[1]) / 252):5.1f}")
    return out
print("A. Whole strategy, Jul 2007 - 19 Nov 2026")
o = table(V, '2007-07-02', '9999', [('2007-07-02', '2015-12-31'), ('2016-01-04', '9999')])
rr = lambda x: np.r_[x[0][0] - 1, x[0][1:] / x[0][:-1] - 1]
print("   daily correlation with QQQ held: " + ', '.join(f"{k} {np.corrcoef(rr(o[k]), rr(o['QQQ held']))[0, 1]:.2f}" for k in ('live', 'qld', 'half-half', 'rot+qqq', 'half+rot')))
# B. dot-com era, trend half alone
sp, qq = B.yh('SPY'), B.yh('QQQ'); irx = B._raw('^IRX'); d2 = [d for d in sorted(qq) if d <= '2007-06-29' and d in sp]; n2 = len(d2)
y = 4.5; C2 = np.zeros(n2)
for i, d in enumerate(d2): y = irx.get(d, y); C2[i] = y / 100 / 252
X2 = {'SPY': np.array([sp[d] for d in d2]), 'QQQ': np.array([qq[d] for d in d2])}
for a, b in (('SPY', 'SSO'), ('QQQ', 'QLD')):
    r = np.r_[0, X2[a][1:] / X2[a][:-1] - 1]; X2[b] = np.cumprod(1 + 2 * r - C2 - 0.0095 / 252)
X2['IEF'] = np.cumprod(1 + C2)
vx = B._vx; P2 = np.zeros(n2, bool); p = False
for i, d in enumerate(d2):
    v = vx.get(d)
    if v is not None: p = (v >= 25.0) if p else (v >= 30.0)
    P2[i] = p
B.dates, B.n, B.C, B.X, B.PANIC = d2, n2, C2, X2, P2; B.R = {s: np.r_[0, X2[s][1:] / X2[s][:-1] - 1] for s in X2}; B.DY = {s: np.zeros(n2) for s in X2}
B.me = [i for i in range(n2 - 1) if d2[i][:7] != d2[i + 1][:7]]; B.mes = set(B.me); B.mi = {i: k for k, i in enumerate(B.me)}; setup()
print(f"\nB. Trend half alone (else T-bills), {d2[200]} - Jun 2007: Nasdaq-100 fell 83% from 2000 to 2002")
V2 = {'SSO/SPY': lambda: N([('SPY', 'SSO', 1.0, 1)], rot=None), 'QLD/QQQ': lambda: N([('QQQ', 'QLD', 1.0, 1)], rot=None),
      'half-half': lambda: N([('SPY', 'SSO', .5, 1), ('QQQ', 'QLD', .5, 1)], rot=None), 'QLD/SPY': lambda: N([('SPY', 'QLD', 1.0, 1)], rot=None),
      'QQQ held': lambda: B.Static({'QQQ': 1.0}), 'SPY held': lambda: B.Static({'SPY': 1.0})}
table(V2, d2[201], '2007-06-29', [(d2[201], '2002-12-31'), ('2003-01-02', '2007-06-29')])
