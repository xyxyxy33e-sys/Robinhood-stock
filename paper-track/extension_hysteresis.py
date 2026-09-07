import sys, math
sys.path.insert(0,'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from state import realized_vol, VOL_TARGET_PA, EXTENSION_RULES, EXTENSION_STEP, needs_rebalance
import monthly_returns as MR
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
def votes_h(eff, gaps, prev, band):
    """Hysteresis per window: a window that is ON stays on until gap < t-band;
    a window that is OFF turns on only above t+band."""
    if eff!='A': return 0, {}
    st={}
    for n,t in EXTENSION_RULES:
        g=gaps.get(n)
        if g is None: st[n]=False; continue
        was=prev.get(n,False)
        st[n]= g > t-band if was else g > t+band
    return sum(st.values()), st
pxd={s:load_daily_csv(f'{MR.REPO}/{s}.csv') for s in ('SPMO','TQQQ','QLD','XLU')}
alld=sorted(set.intersection(*[set(x) for x in pxd.values()])&set(qqq)); pxd['BOXX']=build_cash_index(alld,load_daily_csv(f'{MR.REPO}/BOXX.csv'),load_tbill())
days=[d for d in alld if d>='2015-11-02' and d in pxd['BOXX']]
fastd=compute_fast_states(qd,qqq); stt=dict(zip(qd,compute_states(qd,qqq)))
gapsd={d:{n:qv[qix[d]]/sma(qv,qix[d],n)-1 for n in (100,150,200)} for d in days}
V30={d:realized_vol(qd,qqq,as_of=d) for d in days}
def sim(band, cost=0.0004):
    held=prev=None; out=[]; nreb=0; pv={}; nvc=0; last=None
    for i in range(1,len(days)):
        d0,d1=days[i-1],days[i]; eff=effective_state(stt[d0],fastd[d0])
        nv,pv=votes_h(eff,gapsd[d0],pv,band)
        if last is not None and nv!=last: nvc+=1
        last=nv
        w=W[eff]; f=1-EXTENSION_STEP*nv
        if f<1: w=tuple(x*f for x in w[:4])+(1-f*sum(w[:4]),)
        v=V30[d0]; m=1.0 if not v else min(1.0,VOL_TARGET_PA/v); t=tuple(x*m for x in w[:4])+(1-m*sum(w[:4]),)
        key=(eff,nv); c=0.0
        if held is None: held=list(t)
        else:
            do,drift,_=needs_rebalance(t,held,key!=prev)
            if do: c=cost*drift; held=list(t); nreb+=1
        rr_=[pxd[s][d1]/pxd[s][d0]-1 for s in ('SPMO','TQQQ','QLD','XLU','BOXX')]
        gg=sum(held[j]*rr_[j] for j in range(5)); out.append((d1,gg-c)); dn=1+gg
        if dn>0: held=[held[j]*(1+rr_[j])/dn for j in range(5)]
        prev=key
    nav=1;pk=1;mdd=0
    for d,r in out: nav*=1+r; pk=max(pk,nav); mdd=min(mdd,nav/pk-1)
    n=len(out); mu=sum(r for _,r in out)/n; sd=(sum((r-mu)**2 for _,r in out)/(n-1))**.5
    yrs=len(days)/252
    return nav**(252/n)-1, mu*252/(sd*252**.5), mdd, nreb/yrs, nvc/yrs
print("EXTENSION HYSTERESIS — real daily, band, 4bp (live = band 0)")
for b in (0.0,0.005,0.01,0.015,0.02,0.03):
    c,sh,m,rb,vc=sim(b); print(f"  band {b*100:4.1f}pp  {c*100:5.2f}% / {sh:.3f} / {m*100:5.1f}%   reb/yr {rb:.0f}   vote changes/yr {vc:.1f}")
# proxy both-era check for the best couple
for r in rows: r['_g']=r['gaps']
def mkh(band):
    state={'pv':{}, 'last':None}
    def fn(r):
        nv,state['pv']=votes_h(r['eff'],r['gaps'],state['pv'],band)
        w=W[r['eff']]; f=1-EXTENSION_STEP*nv
        if f<1: w=tuple(x*f for x in w[:4])+(1-f*sum(w[:4]),)
        return vt(w,r['vol'])
    return fn
print("\nproxy 26y (rows are chronological; hysteresis carried in order)")
for b in (0.0,0.01,0.02):
    ev=evaluate(rows,mkh(b)); print(f"  band {b*100:4.1f}pp  {ev['cagr']*100:5.2f}/{ev['sharpe']:.3f}/{ev['mdd']*100:5.1f}  S {ev['s_sharpe']:.3f} H {ev['h_sharpe']:.3f}")
