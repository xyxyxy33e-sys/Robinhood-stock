import sys, numpy as np
sys.path.insert(0,'/home/user/Robinhood-stock/paper-track/review_2026_11')
import harness as H
GX, GW = np.polynomial.hermite_e.hermegauss(120); GW = GW/GW.sum()
THR, BUF = 0.0999, 0.0996
def payoff(x, cap):
    return np.where(x>=1, np.minimum(x-1,cap), np.where(x>=1-THR, 1-x, x-1+BUF))
def value(x0, tau, sig, r, q, cap):
    if tau<=1e-9: return float(1+payoff(np.array(x0),cap))
    xT = x0*np.exp((r-q-0.5*sig**2)*tau + sig*np.sqrt(tau)*GX)
    return float(np.exp(-r*tau)*(GW*(1+payoff(xT,cap))).sum())
def solve_cap(sig,r,q):
    lo,hi=0.0,2.0
    for _ in range(50):
        m=(lo+hi)/2
        if value(1.0,1.0,sig,r,q,m)<1: lo=m
        else: hi=m
    return m
def series(pn, ds, Q=0.006, FEE=0.009, IVX=1.2):
    px = np.cumprod(1+pn['qqq']); cash=pn['cash']
    vix=[]; last=20.0
    for d in ds:
        v=H.VIX.get(d); last = v if v is not None and v==v else last; vix.append(last)
    iv = IVX*np.array(vix)/100; rr=np.clip(cash*252,0,None)
    starts=[0]+[next(i for i,d in enumerate(ds) if d>=f'{y}-09-18') for y in range(int(ds[0][:4]),int(ds[-1][:4])+1)
               if any(d>=f'{y}-09-18' for d in ds)]
    starts=sorted(set(starts))
    per=np.zeros(len(ds),int)
    for j,s in enumerate(starts): per[s:]=j
    caps=[solve_cap(iv[s],rr[s],Q) for s in starts]
    def V(i,j):
        s=starts[j]; tau=max(1.0-(i-s)/252,0.0)
        return value(px[i]/px[s],tau,iv[i],rr[i],Q,caps[j])
    ret=np.zeros(len(ds))
    for i in range(1,len(ds)):
        j=per[i-1]
        ret[i]=V(i,j)/V(i-1,j)-1-FEE/252
    return ret, dict(zip([ds[s] for s in starts],caps))
