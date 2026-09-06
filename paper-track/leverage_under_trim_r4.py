import sys, math
sys.path.insert(0,'paper-track')
exec(open('paper-track/leverage_under_trim_r2.py').read().split('SCHED={')[0])
from downturn_review import exposure_control
SCHED={'live 1/.67/.33/0':(1,2/3,1/3,0),'1/.67/.33/.15':(1,2/3,1/3,.15),'1/.67/.33/.25':(1,2/3,1/3,.25),'1/.67/.33/.1':(1,2/3,1/3,.1),'1/.5/.25/.15':(1,.5,.25,.15),'old 1/.75/.5/.25':(1,.75,.5,.25)}
base=evaluate(rows,mk2(W,SCHED['live 1/.67/.33/0']))
print("A 40/60 throughout. proxy CAGR/Sharpe/MDD, S/H Sharpe, expo-ctl, real weekly")
for lab,s in SCHED.items():
    ev=evaluate(rows,mk2(W,s)); e=RF.eval_real(rr,mk2(W,s,RF.vt)); k1,c1=exposure_control(rows,ev['risky'])
    print(f"  {lab:<18} {ev['cagr']*100:5.2f}/{ev['sharpe']:.3f}/{ev['mdd']*100:5.1f}  S {ev['s_sharpe']:.3f} H {ev['h_sharpe']:.3f}  expo {c1['sharpe']:.3f}  real {e['cagr']*100:5.2f}/{e['sharpe']:.3f}/{e['mdd']*100:5.1f}")
exec("px={"+open('paper-track/leverage_under_trim_r2.py').read().split("px={",1)[1].split("for lab,Wd,s in")[0])
print("\nreal daily with the band")
for lab in ('live 1/.67/.33/0','1/.67/.33/.15','old 1/.75/.5/.25'):
    out,nreb=simulate(W,SCHED[lab]); c,sh,m,by=stats(out)
    print(f"  {lab:<18} {c*100:.2f}% / {sh:.3f} / {m*100:.1f}%  reb/yr {nreb/(len(days)/252):.0f}  "+' '.join(f"{y[2:]}:{math.expm1(by[y])*100:+.0f}" for y in sorted(by)))
def byyear(s):
    rets,_=run(rows,mk2(W,s)); by={}
    for r,x in zip(rows,rets): by[r['d'][:4]]=by.get(r['d'][:4],0)+math.log1p(x)
    return by
a=byyear(SCHED['live 1/.67/.33/0']); b=byyear(SCHED['1/.67/.33/.15'])
print("\nproxy per-year diff, floor .15 minus live:", '  '.join(f"{y}:{(b[y]-a[y])*100:+.1f}" for y in sorted(a) if abs(b[y]-a[y])>0.003))
