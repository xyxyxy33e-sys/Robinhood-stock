import sys, math
sys.path.insert(0,'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from downturn_review import exposure_control
from improvement_search_r2 import beta_of, beta_matched_control
from state import realized_vol, extension_scale
LB=(5,10,15,20,30,60)
for r in rows:
    for n in LB: r[f'v{n}']=realized_vol(ds,px,as_of=r['d'],lookback=n)
for r in rr:
    for n in LB: r[f'v{n}']=realized_vol(qd,qqq,as_of=r['d0'],lookback=n)
FAM={'live vol30':('v30',),'vol10':('v10',),'vol20':('v20',),'vol60':('v60',),
     'max(10,30)':('v10','v30'),'max(5,30)':('v5','v30'),'max(15,30)':('v15','v30'),'max(20,30)':('v20','v30'),
     'max(10,60)':('v10','v60'),'max(20,60)':('v20','v60'),'max(10,30,60)':('v10','v30','v60')}
def mk(keys, vtf=vt):
    def fn(r):
        w=W[r['eff']]; f=extension_scale(r['eff'],r['gaps'])
        if f<1: w=tuple(x*f for x in w[:4])+(1-f*sum(w[:4]),)
        vs=[r[k] for k in keys if r.get(k) is not None]
        return vtf(w, max(vs) if vs else r['vol'])
    return fn
base=evaluate(rows,mk(('v30',)))
print(f"{'estimator':<14} proxy CAGR/Sharpe/MDD      S / H      expo   beta   real weekly")
for lab,keys in FAM.items():
    ev=evaluate(rows,mk(keys)); e=RF.eval_real(rr,mk(keys,RF.vt)); k1,c1=exposure_control(rows,ev['risky'])
    tb=beta_of(rows,mk(keys)); k2,c2=beta_matched_control(rows,mk(('v30',)),tb)
    flag='' if lab=='live vol30' else (' BOTH' if ev['s_sharpe']>base['s_sharpe'] and ev['h_sharpe']>base['h_sharpe'] else '')
    print(f"  {lab:<14} {ev['cagr']*100:5.2f}/{ev['sharpe']:.3f}/{ev['mdd']*100:5.1f}   {ev['s_sharpe']:.3f}/{ev['h_sharpe']:.3f}  {c1['sharpe']:.3f}  {c2['sharpe']:.3f}  {e['cagr']*100:5.2f}/{e['sharpe']:.3f}/{e['mdd']*100:5.1f}{flag}")
