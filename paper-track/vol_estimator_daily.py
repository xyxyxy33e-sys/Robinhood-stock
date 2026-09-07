import sys, math
sys.path.insert(0,'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from state import realized_vol, VOL_TARGET_PA, extension_votes, extension_scale, needs_rebalance
import monthly_returns as MR
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
pxd={s:load_daily_csv(f'{MR.REPO}/{s}.csv') for s in ('SPMO','TQQQ','QLD','XLU')}
alld=sorted(set.intersection(*[set(x) for x in pxd.values()])&set(qqq)); pxd['BOXX']=build_cash_index(alld,load_daily_csv(f'{MR.REPO}/BOXX.csv'),load_tbill())
days=[d for d in alld if d>='2015-11-02' and d in pxd['BOXX']]
fastd=compute_fast_states(qd,qqq); st=dict(zip(qd,compute_states(qd,qqq)))
gapsd={d:{n:qv[qix[d]]/sma(qv,qix[d],n)-1 for n in (100,150,200)} for d in days}
V30={d:realized_vol(qd,qqq,as_of=d) for d in days}; V10={d:realized_vol(qd,qqq,as_of=d,lookback=10) for d in days}
def simulate(mode,cost=0.0004):
    held=prev=None; out=[]; nreb=0; turn=0.0
    for i in range(1,len(days)):
        d0,d1=days[i-1],days[i]; eff=effective_state(st[d0],fastd[d0]); w=W[eff]; nv=extension_votes(eff,gapsd[d0])
        f=extension_scale(eff,gapsd[d0])
        if f<1: w=tuple(x*f for x in w[:4])+(1-f*sum(w[:4]),)
        v=V30[d0]
        if mode=='max10_30' and V10[d0] and v: v=max(v,V10[d0])
        m=1.0 if not v else min(1.0,VOL_TARGET_PA/v); t=tuple(x*m for x in w[:4])+(1-m*sum(w[:4]),)
        key=(eff,nv); c=0.0
        if held is None: held=list(t)
        else:
            do,drift,_=needs_rebalance(t,held,key!=prev)
            if do: c=cost*drift; turn+=drift/2; held=list(t); nreb+=1
        rr_=[pxd[s][d1]/pxd[s][d0]-1 for s in ('SPMO','TQQQ','QLD','XLU','BOXX')]; gg=sum(held[j]*rr_[j] for j in range(5)); out.append((d1,gg-c)); dn=1+gg
        if dn>0: held=[held[j]*(1+rr_[j])/dn for j in range(5)]
        prev=key
    return out,nreb,turn
def stats(out):
    nav=1;pk=1;mdd=0;by={}
    for d,r in out: nav*=1+r; pk=max(pk,nav); mdd=min(mdd,nav/pk-1); by[d[:4]]=by.get(d[:4],0)+math.log1p(r)
    n=len(out); mu=sum(r for _,r in out)/n; sd=(sum((r-mu)**2 for _,r in out)/(n-1))**.5
    return nav**(252/n)-1, mu*252/(sd*252**.5), mdd, by
print("real DAILY with the drift band, live design (A 40/60, step 1/3)")
for cost in (0.0004,0.0010,0.0020):
    for mode in ('live','max10_30'):
        out,nreb,turn=simulate(mode,cost); c,sh,m,by=stats(out); yrs=len(days)/252
        print(f"  cost {cost*1e4:.0f}bp {mode:<10} {c*100:5.2f}% / {sh:.3f} / {m*100:5.1f}%  reb/yr {nreb/yrs:.0f}  turnover {turn/yrs:.1f}x/yr"+("  "+' '.join(f"{y[2:]}:{math.expm1(by[y])*100:+.0f}" for y in sorted(by)) if cost==0.0004 else ""))
