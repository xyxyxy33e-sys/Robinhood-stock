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
q = H.p['qqq']; px = np.cumprod(1 + q)
vol = np.array([YV.get(x, np.nan) for x in PD], float)
def sma(x, n):
    c = np.cumsum(np.insert(x, 0, 0)); o = np.full(len(x), np.nan); o[n-1:] = (c[n:] - c[:-n]) / n; return o
m20, m100 = sma(vol, 20), sma(vol, 100)
F = {'vol > 20d line': vol > m20, 'vol > 100d line': vol > m100,
     'above both lines': (vol > m20) & (vol > m100), 'below both lines': (vol < m20) & (vol < m100),
     '20d line > 100d line': m20 > m100}
valid = ~np.isnan(m100)
eff = MC._eff(H.sig, NEW)[0]; L = 'ABCDEF'
f1 = np.r_[px[1:] / px[:-1] - 1, np.nan]; f20 = np.array([px[i+20]/px[i]-1 if i+20 < len(px) else np.nan for i in range(len(px))])
era = np.array(PD)
print('share of days:', {k: round(float(v[valid].mean())*100) for k, v in F.items()})
for name, fl in F.items():
    print(f'\n== {name}: next-day and next-20-day QQQ return, yes vs no, by state (2001-Oct15 | Nov15-26) ==')
    for k, s in enumerate(L):
        row = []
        for em in ((era >= '2001-01-01') & (era < '2015-11-01'), era >= '2015-11-01'):
            m = (eff == k) & em & valid & ~np.isnan(f20)
            y, n = m & fl, m & ~fl
            if y.sum() < 20 or n.sum() < 20: row.append('   too few            '); continue
            # t on next-day returns (daily, ~independent)
            a, b = f1[y], f1[n]; t = (a.mean()-b.mean())/np.sqrt(a.var(ddof=1)/len(a)+b.var(ddof=1)/len(b))
            row.append(f"1d {(a.mean()-b.mean())*1e4:+5.0f}bp t{t:+.1f} 20d {(f20[y].mean()-f20[n].mean())*100:+5.1f}pp")
        print(f"  {s}: {row[0]} | {row[1]}")
# backtest rules
n_r = _n
def feat(fl, real): return fl[H.OFF:H.OFF + n_r] if real else fl
def hook(rule, fl, real):
    def h(w5, sg):
        w = w5.copy(); e = MC._eff(sg, NEW)[0]; hi = feat(fl, real)[:w.shape[1]]
        if rule == 'A_half': m = (e == 0) & hi; k = 0.5
        elif rule == 'D_cash': m = (e == 3) & hi; k = 0.0
        elif rule == 'any_half': m = hi; k = 0.5
        elif rule == 'A_tqqq_out':
            m = (e == 0) & hi; w[0, m, 4] += w[0, m, 1]; w[0, m, 1] = 0; return w
        r = w[0, m, :4].copy(); w[0, m, :4] = r * k; w[0, m, 4] += r.sum(1) * (1 - k); return w
    return h
def go(real, rule=None, fl=None, d1='2099', deep=None):
    kw = dict(cfg=NEW, vixm=False)
    if rule: kw['w5_hook'] = hook(rule, fl, real)
    if deep is None: return H.run(real, d1=d1, **kw)[0]
    pn = H.pr if real else H.p; ds = pn['dates']; sg = H.sr if real else H.sig
    W, Lg, key = H.weights(sg, ds, real, **kw); m = feat(deep, real)[:len(W)]; W = W.copy(); W[m, -1] += W[m, 4]; W[m, 4] = 0
    s0 = next(i for i, x in enumerate(ds) if x >= ('2015-11-02' if real else '2001-01-02')); e = max(i for i, x in enumerate(ds) if x <= d1)
    return MC.run_strategy(W[None, :e+1], key[None, :e+1], Lg[None, :e+1], s0)[0][0]
def st(r):
    nav = np.cumprod(1+r); dd = (nav/np.maximum.accumulate(nav)-1).min(); v = r.std(ddof=1)*252**.5
    return f"{(nav[-1]**(252/len(r))-1)*100:5.1f}% {r.mean()*252/v:5.3f} {dd*100:6.1f}%"
print(f"\n{'rule':40s} | real 2015-26          | proxy 2001-26         | holdout 2001-Oct15")
print(f"{'current (no sleeve)':40s} | {st(go(True))} | {st(go(False))} | {st(go(False, d1='2015-10-30'))}")
for name in ('above both lines', '20d line > 100d line', 'vol > 20d line'):
    fl = np.nan_to_num(F[name]).astype(bool) & valid
    for rule in ('A_half', 'A_tqqq_out', 'D_cash', 'any_half'):
        lab = f"{rule} when {name}"
        print(f"{lab:40s} | {st(go(True, rule, fl))} | {st(go(False, rule, fl))} | {st(go(False, rule, fl, d1='2015-10-30'))}")
    lab = f"deepE skip when {name}"
    print(f"{lab:40s} | {st(go(True, deep=fl))} | {st(go(False, deep=fl))} | {st(go(False, deep=fl, d1='2015-10-30'))}")
fl = np.nan_to_num(F['below both lines']).astype(bool) & valid
lab = 'deepE skip when below both lines'
print(f"{lab:40s} | {st(go(True, deep=fl))} | {st(go(False, deep=fl))} | {st(go(False, deep=fl, d1='2015-10-30'))}")
i = len(PD)-1
print(f"\nlatest {PD[i]}: vol {vol[i]/1e6:.1f}M, 20d line {m20[i]/1e6:.1f}M, 100d line {m100[i]/1e6:.1f}M")
