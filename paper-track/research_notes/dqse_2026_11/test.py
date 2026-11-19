import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/user/Robinhood-stock/paper-track/research_notes/dqse_2026_11')
import numpy as np, syn
from syn import H
from harness import MC, S
_n = H.sr['vol'].shape[1]
_N0 = len(H.pr['dates'])
for _k, _v in list(H.pr.items()):
    if hasattr(_v, '__len__') and len(_v) == _N0 and _N0 != _n: H.pr[_k] = _v[:_n]
H.RD = H.pr['dates']
SPREAD = 0.0013   # extra one-way cost on DQSE trades (half its ~0.3% spread) on top of the 2bp model

def syn_series(pn, ds):
    orig = syn.solve_cap
    syn.solve_cap = lambda sig, r, q: 1.9 * orig(sig, r, q)     # skew calibration: flat-vol cap x1.9 matches Sep-2026 18.75%
    try: return syn.series(pn, ds, IVX=1.0)
    finally: syn.solve_cap = orig

NEW = dict(H.CUR, gross_cap=S.GROSS_CAP)
def run(real, where, d0=None, d1='2099'):
    pn = H.pr if real else H.p; ds = pn['dates']; sg = H.sr if real else H.sig
    W, L, key = H.weights(sg, ds, real, cfg=NEW, vixm=False)   # sleeve off on both arms (no VIXY before 2011 on proxy)
    dq, caps = DQ[real]
    eff = MC._eff(sg, NEW)[0]
    W = W.copy(); add = np.zeros(len(ds))
    if where == 'EF_cash':            # whole BOXX leg while effective E or F
        m = np.isin(eff, (4, 5)); add[m] = W[m, -1]; W[m, -1] = 0
    elif where == 'deepE':            # the deep-E QQQ slot (column 4 when vixm=False: core,tqqq,qld,xlu,deep,panic,cash)
        add = W[:, 4].copy(); W[:, 4] = 0
    elif where == 'all_cash':
        add = W[:, -1].copy(); W[:, -1] = 0
    if where != 'base':
        W = np.concatenate([W, add[:, None]], 1); L = np.concatenate([L, dq[:, None]], 1)
        key = key + (add > 0).astype(np.int64) * 10**9
    s0 = next(i for i, d in enumerate(ds) if d >= (d0 or ('2015-11-02' if real else '2001-01-02')))
    e = max(i for i, d in enumerate(ds) if d <= d1)
    r, tr = MC.run_strategy(W[None, :e+1], key[None, :e+1], L[None, :e+1], s0)
    r = r[0]
    if where != 'base':
        r = r - SPREAD * np.abs(np.diff(add[s0:e+1]))      # extra spread on DQSE weight changes
    return r
DQ = {}
for real in (True, False):
    pn = H.pr if real else H.p
    DQ[real] = syn_series(pn, pn['dates'])
def st(r):
    nav=np.cumprod(1+r); dd=(nav/np.maximum.accumulate(nav)-1).min(); v=r.std(ddof=1)*252**.5
    return f"{(nav[-1]**(252/len(r))-1)*100:5.1f}% / {r.mean()*252/v:5.3f} / {dd*100:6.1f}%"
# sanity: synthetic DQSE buy&hold vs QQQ
for real,lab,d0 in ((True,'real 2015-26','2015-11-02'),(False,'proxy 2001-26','2001-01-02')):
    pn = H.pr if real else H.p; ds=pn['dates']; s0=next(i for i,d in enumerate(ds) if d>=d0)
    print(lab,'DQSE b&h',st(DQ[real][0][s0+1:]),' QQQ b&h',st(pn['qqq'][s0+1:]))
    b = pn['qqq'][s0+1:]; dq=DQ[real][0][s0+1:]; print('   beta of daily DQSE to QQQ', round(np.cov(dq,b)[0,1]/b.var(),2))
caps = DQ[False][1]; print('synthetic caps sample', {k: round(v,3) for k,v in list(caps.items())[-6:]})
for real,lab in ((True,'REAL 2015-26 (no vol sleeve)'),(False,'PROXY 2001-26')):
    print(lab)
    for w in ('base','EF_cash','deepE','all_cash'):
        print(f"  {w:9s}", st(run(real,w)), ('  holdout 2001-Oct15 '+st(run(False,w,d1='2015-10-30'))) if not real else '')
