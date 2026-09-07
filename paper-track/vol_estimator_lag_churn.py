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
VOL={n:{d:realized_vol(qd,qqq,as_of=d,lookback=n) for d in days} for n in (5,10,15,20,30)}
def sim(keys, lag=1, cost=0.0004):
    held=prev=None; out=[]; nreb=0
    for i in range(lag,len(days)-0):
        d0,d1=days[i-lag],days[i]   # signal from d0 close, return earned d(i-1)->d(i)
        r0,r1=days[i-1],days[i]
        eff=effective_state(st[d0],fastd[d0]); w=W[eff]; nv=extension_votes(eff,gapsd[d0])
        f=extension_scale(eff,gapsd[d0])
        if f<1: w=tuple(x*f for x in w[:4])+(1-f*sum(w[:4]),)
        vs=[VOL[n][d0] for n in keys if VOL[n][d0]]
        v=max(vs) if vs else None
        m=1.0 if not v else min(1.0,VOL_TARGET_PA/v); t=tuple(x*m for x in w[:4])+(1-m*sum(w[:4]),)
        key=(eff,nv); c=0.0
        if held is None: held=list(t)
        else:
            do,drift,_=needs_rebalance(t,held,key!=prev)
            if do: c=cost*drift; held=list(t); nreb+=1
        rr_=[pxd[s][r1]/pxd[s][r0]-1 for s in ('SPMO','TQQQ','QLD','XLU','BOXX')]
        gg=sum(held[j]*rr_[j] for j in range(5)); out.append((r1,gg-c)); dn=1+gg
        if dn>0: held=[held[j]*(1+rr_[j])/dn for j in range(5)]
        prev=key
    return out,nreb
def stats(out):
    nav=1;pk=1;mdd=0
    for d,r in out: nav*=1+r; pk=max(pk,nav); mdd=min(mdd,nav/pk-1)
    n=len(out); mu=sum(r for _,r in out)/n; sd=(sum((r-mu)**2 for _,r in out)/(n-1))**.5
    return nav**(252/n)-1, mu*252/(sd*252**.5), mdd
print("REAL DAILY (band, 4bp). estimator sweep — why not max(5,30)/max(15,30)?")
for lab,keys in (('vol30 (live)',(30,)),('max(5,30)',(5,30)),('max(10,30)',(10,30)),('max(15,30)',(15,30)),('max(20,30)',(20,30))):
    out,nreb=sim(keys); c,sh,m=stats(out); print(f"  {lab:<13} {c*100:5.2f}% / {sh:.3f} / {m*100:5.1f}%  reb/yr {nreb/(len(days)/252):.0f}")
print("\nEXECUTION LAG sensitivity (#1): signal close d0, return earned over the NEXT session vs one more session later")
for lab,keys in (('vol30 (live)',(30,)),('max(10,30)',(10,30))):
    for lag in (1,2):
        out,nreb=sim(keys,lag=lag); c,sh,m=stats(out)
        print(f"  {lab:<13} lag {lag} session(s): {c*100:5.2f}% / {sh:.3f} / {m*100:5.1f}%")
print("\nEXTENSION THRESHOLD CHURN (#5): vote changes and how many reverse quickly")
seq=[(d,extension_votes(effective_state(st[d],fastd[d]),gapsd[d])) for d in days]
ch=[i for i in range(1,len(seq)) if seq[i][1]!=seq[i-1][1]]
print(f"  vote changes: {len(ch)} over {len(days)/252:.1f}y = {len(ch)/(len(days)/252):.1f}/yr")
for win in (3,5,10):
    rev=sum(1 for j,i in enumerate(ch[:-1]) if ch[j+1]-i<=win and seq[ch[j+1]][1]==seq[i-1][1])
    print(f"  reversed back to the prior vote count within {win:>2} sessions: {rev} ({rev/len(ch)*100:.0f}%)")
mar=[]
for d in days:
    eff=effective_state(st[d],fastd[d])
    if eff!='A': continue
    for n,t in ((100,.10),(150,.12),(200,.15)):
        g=gapsd[d][n]
        if abs(g-t)<0.005: mar.append(d); break
print(f"  A-days within 0.5pp of ANY threshold: {len(mar)} ({len(mar)/sum(1 for d in days if effective_state(st[d],fastd[d])=='A')*100:.1f}% of A-days)")
