import sys, math
sys.path.insert(0,'paper-track')
from improvement_search import build, data, evaluate, header, show, vt, run
from downturn_review import enrich
from state import TARGET_WEIGHTS, compute_fast_states, compute_states, effective_state, sma, extension_scale
import return_frontier as RF
from long_history_backtest import load_px
W=TARGET_WEIGHTS
rows=enrich(build()); D=data(); ds,px=D['ds'],D['qqq']; fast=compute_fast_states(ds,px); v=[px[d] for d in ds]; ix={d:i for i,d in enumerate(ds)}
for r in rows:
    i=ix[r['d']]; r['eff']=effective_state(r['state'],fast[r['d']]); r['gaps']={}
    for n in (100,150,200): m=sma(v,i,n); r['gaps'][n]=(v[i]/m-1) if m else 0.0
rr=RF.real_rows(); qqq=load_px('data/qqq_long_history.csv'); qd=sorted(qqq); qv=[qqq[d] for d in qd]; qix={d:i for i,d in enumerate(qd)}; g=dict(zip(qd,compute_states(qd,qqq,short_n=20,long_n=100)))
for r in rr:
    i=qix[r['d0']]; r['eff']=effective_state(r['state'],g[r['d0']]); r['gaps']={n:qv[i]/sma(qv,i,n)-1 for n in (100,150,200)}
def mk(Wd, vtf=vt, target=None):
    def fn(r):
        w=Wd[r['eff']]; f=extension_scale(r['eff'],r['gaps'])
        if f<1: w=tuple(x*f for x in w[:4])+(1-f*sum(w[:4]),)
        return vtf(w,r['vol']) if target is None else vtf(w,r['vol'],target)
    return fn
def byyear(fn):
    rets,_=run(rows,fn); by={}
    for r,x in zip(rows,rets): by[r['d'][:4]]=by.get(r['d'][:4],0)+math.log1p(x)
    return {y:math.expm1(x) for y,x in by.items()}
def line(lab,Wd,base,target=None):
    ev=evaluate(rows,mk(Wd,target=target)); e=RF.eval_real(rr,mk(Wd,RF.vt,target)); by=byyear(mk(Wd,target=target)); worst=min(by.values())
    print(f"{lab:<22} proxy {ev['cagr']*100:5.2f}% / {ev['sharpe']:.3f} / {ev['mdd']*100:5.1f}%  S {ev['s_sharpe']:.3f} H {ev['h_sharpe']:.3f}  "
          f"worst yr {worst*100:+.0f} 2020 {by['2020']*100:+.0f} 2022 {by['2022']*100:+.0f} 2008 {by['2008']*100:+.0f} | real {e['cagr']*100:5.2f}% / {e['sharpe']:.3f} / {e['mdd']*100:5.1f}%")
    return ev
base=evaluate(rows,mk(W))
print("A ladder (core/TQQQ) under full live design: fast 20/100 + graded trim + VT20")
for a in ((0.5,0.5),(0.4,0.6),(0.3,0.7),(0.25,0.75),(0.0,1.0)):
    line(f"A={int(a[0]*100)}/{int(a[1]*100)}",dict(W,A=(a[0],a[1],0,0,0)),base)
print("\nB ladder (core/TQQQ), A held at 50/50")
for b in ((0.75,0.25),(0.6,0.4),(0.5,0.5)):
    line(f"B={int(b[0]*100)}/{int(b[1]*100)}",dict(W,B=(b[0],b[1],0,0,0)),base)
print("\nBoth up")
line("A=40/60 B=60/40",dict(W,A=(0.4,0.6,0,0,0),B=(0.6,0.4,0,0,0)),base)
line("A=30/70 B=50/50",dict(W,A=(0.3,0.7,0,0,0),B=(0.5,0.5,0,0,0)),base)
print("\nVol target with trim on (A 50/50)")
for t in (0.20,0.22,0.25,0.30):
    line(f"VT={int(t*100)}%",W,base,target=t)
print("\nTrim harder AND more leverage: A=30/70 with step 0.33 (x0.67/0.33/0)")
import state as S
S.EXTENSION_STEP=0.3333
line("A=30/70 step 1/3",dict(W,A=(0.3,0.7,0,0,0)),base)
line("A=40/60 step 1/3",dict(W,A=(0.4,0.6,0,0,0)),base)
S.EXTENSION_STEP=0.25
