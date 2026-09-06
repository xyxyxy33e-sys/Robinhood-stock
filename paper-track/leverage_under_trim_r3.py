import sys, math
sys.path.insert(0,'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from downturn_review import exposure_control
for r in rows:
    i=ix[r['d']]
    for n in (50,250): m=sma(v,i,n); r['gaps'][n]=(v[i]/m-1) if m else 0.0
for r in rr:
    i=qix[r['d0']]
    for n in (50,250): m=sma(qv,i,n); r['gaps'][n]=(qv[i]/m-1) if m else 0.0
def mk3(Wd, rules, step, vtf=vt):
    def fn(r):
        w=Wd[r['eff']]
        if r['eff']=='A':
            nv=sum(1 for n,t in rules if r['gaps'][n]>t); f=max(0.0,1-step*nv)
            if f<1: w=tuple(x*f for x in w[:4])+(1-f*sum(w[:4]),)
        return vtf(w,r['vol'])
    return fn
R3=((100,.10),(150,.12),(200,.15))
SETS={'3w 100/150/200':R3,'4w +50d>8%':((50,.08),)+R3,'4w +50d>6%':((50,.06),)+R3,'4w +250d>17%':R3+((250,.17),),'4w +250d>15%':R3+((250,.15),),'5w 50/100/150/200/250':((50,.08),)+R3+((250,.17),)}
base=evaluate(rows,mk3(W,R3,0.25))
print(f"{'set':<24}{'step':>6}  proxy CAGR/Sharpe/MDD      S / H     expo-ctl  real weekly")
for lab,rules in SETS.items():
    for step in ((0.25,1/3) if lab.startswith('3w') else (0.2,0.25,1/3) if lab.startswith('4w') else (0.2,0.25)):
        ev=evaluate(rows,mk3(W,rules,step)); e=RF.eval_real(rr,mk3(W,rules,step,RF.vt)); k1,c1=exposure_control(rows,ev['risky'])
        print(f"{lab:<24}{step:>6.2f}  {ev['cagr']*100:5.2f}/{ev['sharpe']:.3f}/{ev['mdd']*100:5.1f}   {ev['s_sharpe']:.3f}/{ev['h_sharpe']:.3f}   {c1['sharpe']:.3f}    {e['cagr']*100:5.2f}/{e['sharpe']:.3f}/{e['mdd']*100:5.1f}")
from collections import Counter
for lab in ('4w +50d>8%','4w +250d>17%'):
    rules=SETS[lab]; c=Counter(sum(1 for n,t in rules if r['gaps'][n]>t) for r in rows if r['eff']=='A'); n=sum(c.values())
    print(lab,'votes share:',{k:f"{v/n*100:.1f}%" for k,v in sorted(c.items())})
