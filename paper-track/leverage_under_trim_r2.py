import sys, math, random
sys.path.insert(0,'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from improvement_search_r2 import beta_of, beta_matched_control
from downturn_review import exposure_control
from drift_band_test import annual_stats
from state import extension_votes, realized_vol, VOL_TARGET_PA, needs_rebalance
import monthly_returns as MR
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
def mk2(Wd, sched, vtf=vt):
    def fn(r):
        w=Wd[r['eff']]; f=sched[r.get('_votes', extension_votes(r['eff'],r['gaps']))] if r['eff']=='A' else 1.0
        if f<1: w=tuple(x*f for x in w[:4])+(1-f*sum(w[:4]),)
        return vtf(w,r['vol'])
    return fn
SCHED={'live 1/.75/.5/.25':(1,.75,.5,.25),'1/.7/.4/.1':(1,.7,.4,.1),'1/.67/.33/0':(1,2/3,1/3,0),'1/.6/.2/0':(1,.6,.2,0),'1/.5/.25/0':(1,.5,.25,0),'1/.5/0/0':(1,.5,0,0),'1/.75/.5/0':(1,.75,.5,0),'1/1/.5/0':(1,1,.5,0),'1/0/0/0':(1,0,0,0)}
base=evaluate(rows,mk2(W,SCHED['live 1/.75/.5/.25']))
print("1. trim schedule variants (multiplier at 0/1/2/3 votes), A 50/50, clamped >=0")
for lab,s in SCHED.items():
    ev=evaluate(rows,mk2(W,s)); e=RF.eval_real(rr,mk2(W,s,RF.vt)); k1,c1=exposure_control(rows,ev['risky'])
    print(f"  {lab:<20} {ev['cagr']*100:5.2f}/{ev['sharpe']:.3f}/{ev['mdd']*100:5.1f}  S {ev['s_sharpe']:.3f} H {ev['h_sharpe']:.3f} expo-ctl {c1['sharpe']:.3f}  real {e['cagr']*100:5.2f}/{e['sharpe']:.3f}/{e['mdd']*100:5.1f}")
print("\n2. max-stat permutation: shuffle vote labels among effective-A days (counts kept), best Sharpe gain over the 8 non-live schedules, 200 shuffles")
a_idx=[i for i,r in enumerate(rows) if r['eff']=='A']; votes=[extension_votes(rows[i]['eff'],rows[i]['gaps']) for i in a_idx]
cands=[s for l,s in SCHED.items() if not l.startswith('live')]
real_best=max(evaluate(rows,mk2(W,s))['sharpe'] for s in cands)-base['sharpe']
rng=random.Random(11); beats=0; N=200
for k in range(N):
    p=votes[:]; rng.shuffle(p)
    for i,vv in zip(a_idx,p): rows[i]['_votes']=vv
    b=-9
    for s in cands:
        f,_=run(rows,mk2(W,s)); _,sh,_=annual_stats(f); b=max(b,sh-base['sharpe'])
    beats+= b>=real_best
for r in rows: r.pop('_votes',None)
print(f"  real best gain {real_best:+.3f}; shuffled >= real {beats}/{N} -> p={beats/N:.2f}")
print("\n3. real DAILY sim (band mechanics, T-bill cash pre-BOXX), by year")
px={s:load_daily_csv(f'{MR.REPO}/{s}.csv') for s in ('SPMO','TQQQ','QLD','XLU')}
alld=sorted(set.intersection(*[set(x) for x in px.values()])&set(qqq)); px['BOXX']=build_cash_index(alld,load_daily_csv(f'{MR.REPO}/BOXX.csv'),load_tbill())
days=[d for d in alld if d>='2015-11-02' and d in px['BOXX']]
fastd=compute_fast_states(qd,qqq); st=dict(zip(qd,compute_states(qd,qqq)))
gapsd={d:{n:qv[qix[d]]/sma(qv,qix[d],n)-1 for n in (100,150,200)} for d in days}
def simulate(Wd,sched):
    held=prev=None; out=[]; nreb=0
    for i in range(1,len(days)):
        d0,d1=days[i-1],days[i]; eff=effective_state(st[d0],fastd[d0]); w=Wd[eff]; nv=extension_votes(eff,gapsd[d0]); key=(eff,nv)
        f=sched[nv] if eff=='A' else 1.0
        if f<1: w=tuple(x*f for x in w[:4])+(1-f*sum(w[:4]),)
        vol=realized_vol(qd,qqq,as_of=d0); m=1.0 if not vol else min(1.0,VOL_TARGET_PA/vol); t=tuple(x*m for x in w[:4])+(1-m*sum(w[:4]),)
        c=0.0
        if held is None: held=list(t)
        else:
            do,drift,_=needs_rebalance(t,held,key!=prev)
            if do: c=0.0004*drift; held=list(t); nreb+=1
        rr_=[px[s][d1]/px[s][d0]-1 for s in ('SPMO','TQQQ','QLD','XLU','BOXX')]; gg=sum(held[j]*rr_[j] for j in range(5)); out.append((d1,gg-c)); dn=1+gg
        if dn>0: held=[held[j]*(1+rr_[j])/dn for j in range(5)]
        prev=key
    return out,nreb
def stats(out):
    nav=1;pk=1;mdd=0;by={}
    for d,r in out: nav*=1+r; pk=max(pk,nav); mdd=min(mdd,nav/pk-1); by[d[:4]]=by.get(d[:4],0)+math.log1p(r)
    n=len(out); mu=sum(r for _,r in out)/n; sd=(sum((r-mu)**2 for _,r in out)/(n-1))**.5
    return nav**(252/n)-1, mu*252/(sd*252**.5), mdd, by
for lab,Wd,s in (('live',W,SCHED['live 1/.75/.5/.25']),('1/.67/.33/0',W,SCHED['1/.67/.33/0']),('1/.5/.25/0',W,SCHED['1/.5/.25/0']),('A40/60 live',dict(W,A=(.4,.6,0,0,0)),SCHED['live 1/.75/.5/.25']),('A40/60 1/.67/.33/0',dict(W,A=(.4,.6,0,0,0)),SCHED['1/.67/.33/0']),('A30/70 1/.67/.33/0',dict(W,A=(.3,.7,0,0,0)),SCHED['1/.67/.33/0'])):
    out,nreb=simulate(Wd,s); c,sh,m,by=stats(out)
    print(f"  {lab:<20} {c*100:.2f}% / {sh:.3f} / {m*100:.1f}%  reb/yr {nreb/(len(days)/252):.0f}  "+' '.join(f"{y[2:]}:{math.expm1(by[y])*100:+.0f}" for y in sorted(by)))
