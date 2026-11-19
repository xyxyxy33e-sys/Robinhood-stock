import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/vol'); sys.path.insert(1, '/home/user/Robinhood-stock/paper-track')
import numpy as np, harness as H
from harness import MC, S
_n = len(H.sr['vol'][0]); _N0 = len(H.pr['dates'])
for _k, _v in list(H.pr.items()):
    if hasattr(_v, '__len__') and len(_v) == _N0 and _N0 != _n: H.pr[_k] = _v[:_n]
H.RD = H.pr['dates']
d25p, rvp = np.load('/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/vol/feat2010.npy')
NEW = dict(H.CUR, gross_cap=S.GROSS_CAP)
n_r = len(H.sr['vol'][0])
def feat(real): return d25p[H.OFF:H.OFF + n_r] if real else d25p
def hook(rule, thr, real):
    def h(w5, sg):
        w = w5.copy(); eff = MC._eff(sg, NEW)[0]; f = feat(real)[:w.shape[1]]
        hi = (np.nan_to_num(f) >= thr) if thr > 0 else (np.nan_to_num(f, nan=9) <= -thr)
        if rule == 'A_half': m = (eff == 0) & hi; k = 0.5
        elif rule == 'D_cash': m = (eff == 3) & hi; k = 0.0
        elif rule == 'any_half': m = hi; k = 0.5
        elif rule == 'A_tqqq_out':   # TQQQ to cash in A
            m = (eff == 0) & hi; w[0, m, 4] += w[0, m, 1]; w[0, m, 1] = 0; return w
        risky = w[0, m, :4].copy(); w[0, m, :4] = risky * k; w[0, m, 4] += risky.sum(1) * (1 - k)
        return w
    return h
def go(real, rule=None, thr=None, d1='2099', deep_skip=None):
    kw = dict(cfg=NEW, vixm=False)
    if rule: kw['w5_hook'] = hook(rule, thr, real)
    if deep_skip is None:
        r, ds, _ = H.run(real, d1=d1, **kw); return r
    # deep-E QQQ leg skipped when D25 >= thr
    pn = H.pr if real else H.p; ds = pn['dates']; sg = H.sr if real else H.sig
    W, L, key = H.weights(sg, ds, real, **kw); f = feat(real)[:len(W)]
    m = (np.nan_to_num(f) >= deep_skip) if deep_skip > 0 else (np.nan_to_num(f, nan=9) <= -deep_skip); W = W.copy(); W[m, -1] += W[m, 4]; W[m, 4] = 0
    s0 = next(i for i, d in enumerate(ds) if d >= ('2015-11-02' if real else '2001-01-02')); e = max(i for i, d in enumerate(ds) if d <= d1)
    r, _ = MC.run_strategy(W[None, :e+1], key[None, :e+1], L[None, :e+1], s0); return r[0]
def st(r):
    nav = np.cumprod(1+r); dd = (nav/np.maximum.accumulate(nav)-1).min(); v = r.std(ddof=1)*252**.5
    return f"{(nav[-1]**(252/len(r))-1)*100:5.1f}% {r.mean()*252/v:5.3f} {dd*100:6.1f}%"
print(f"{'variant':22s} | real 2015-26          | proxy 2001-26         | holdout 2001-Oct15")
print(f"{'current (no sleeve)':22s} | {st(go(True))} | {st(go(False))} | {st(go(False, d1='2015-10-30'))}")
for rule in ('A_half', 'A_tqqq_out', 'D_cash', 'any_half'):
    for thr in (1.15, 1.3, 1.5):
        print(f"{rule+' ratio>='+str(thr):22s} | {st(go(True, rule, thr))} | {st(go(False, rule, thr))} | {st(go(False, rule, thr, d1='2015-10-30'))}")
for thr in (1.15, 1.3, 1.5, -0.85):
    lab = ('deepE skip ratio>=' + str(thr)) if thr > 0 else ('deepE skip ratio<=' + str(-thr))
    print(f"{lab:22s} | {st(go(True, deep_skip=thr))} | {st(go(False, deep_skip=thr))} | {st(go(False, deep_skip=thr, d1='2015-10-30'))}")
print('pct of days ratio >=1.15/1.3/1.5:', [round((np.nan_to_num(d25p) >= t).mean()*100, 1) for t in (1.15, 1.3, 1.5)])
