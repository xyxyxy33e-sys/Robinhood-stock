import sys, json, warnings, datetime as dt; warnings.filterwarnings('ignore')
import numpy as np
sys.path.insert(0, '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/vol'); sys.path.insert(1, '/home/user/Robinhood-stock/paper-track')
import harness as H
from harness import MC, S
_n = len(H.sr['vol'][0]); _N0 = len(H.pr['dates'])
for _k, _v in list(H.pr.items()):
    if hasattr(_v, '__len__') and len(_v) == _N0 and _N0 != _n: H.pr[_k] = _v[:_n]
H.RD = H.pr['dates']
d = json.load(open('qqq.json'))['chart']['result'][0]
YV = {dt.datetime.utcfromtimestamp(t).date().isoformat(): v for t, v in zip(d['timestamp'], d['indicators']['quote'][0]['volume']) if v}
PD = H.PD; NEW = dict(H.CUR, gross_cap=S.GROSS_CAP)
vol = np.array([YV.get(x, np.nan) for x in PD], float)
def sma(x, n):
    c = np.cumsum(np.insert(x, 0, 0)); o = np.full(len(x), np.nan); o[n-1:] = (c[n:] - c[:-n]) / n; return o
m1, m5, m20, m100 = vol, sma(vol, 5), sma(vol, 20), sma(vol, 100)
valid = ~np.isnan(m100)
FL = {'always (control)': np.ones(len(PD), bool),
      '5d avg above both lines': (m5 > m20) & (m5 > m100) & valid,
      '5d avg above 20d line': (m5 > m20) & valid,
      'vol above both lines': (m1 > m20) & (m1 > m100) & valid,
      '5d avg below both lines': (m5 < m20) & (m5 < m100) & valid}
def modsig(sg, fl, mode):
    s2 = {k: v for k, v in sg.items() if not (isinstance(k, tuple))}   # drop caches
    eff, fast = sg['eff'].copy(), sg['fast']
    f = fl[None, :eff.shape[1]]
    worse = fast > eff; better = fast < eff
    if mode in ('down', 'both'): eff = np.where(f & worse, fast, eff)
    if mode in ('up', 'both'): eff = np.where(f & better, fast, eff)
    s2['eff'] = eff; return s2
def go(real, fl=None, mode=None, d1='2099'):
    sg = H.sr if real else H.sig
    if fl is not None:
        ff = fl[H.OFF:H.OFF + _n] if real else fl
        sg = modsig(sg, ff, mode)
    pn = H.pr if real else H.p; ds = pn['dates']
    W, L, key = H.weights(sg, ds, real, cfg=NEW, vixm=False)
    s0 = next(i for i, x in enumerate(ds) if x >= ('2015-11-02' if real else '2001-01-02')); e = max(i for i, x in enumerate(ds) if x <= d1)
    r, tr = MC.run_strategy(W[None, :e+1], key[None, :e+1], L[None, :e+1], s0)
    return r[0], tr[0] / ((e - s0) / 252)
def st(x):
    r, t = x; nav = np.cumprod(1+r); dd = (nav/np.maximum.accumulate(nav)-1).min(); v = r.std(ddof=1)*252**.5
    return f"{(nav[-1]**(252/len(r))-1)*100:5.1f}% {r.mean()*252/v:5.3f} {dd*100:6.1f}% {t:3.0f}tr"
print(f"{'variant':46s} | real 2015-26               | proxy 2001-26              | holdout 2001-Oct15")
print(f"{'current (fast read only on the way back up)':46s} | {st(go(True))} | {st(go(False))} | {st(go(False, d1='2015-10-30'))}")
for mode, lab in (('down', 'exit on fast state'), ('up', 'enter on fast state'), ('both', 'fast state both ways')):
    for name, fl in FL.items():
        x = f"{lab}, when {name}"
        print(f"{x:46s} | {st(go(True, fl, mode))} | {st(go(False, fl, mode))} | {st(go(False, fl, mode, d1='2015-10-30'))}")
