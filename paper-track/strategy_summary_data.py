"""Regenerate the DATA / COMPARE_DATA series behind the "Strategy vs Benchmarks"
artifact (https://claude.ai/code/artifact/c21e2827-b249-4f72-b8bc-7edbea289636)
from state.py's CURRENT design, plus the by-year table. Writes DATA.js, COMPARE.js
and byyear.json to the scratchpad path below; splice them into the artifact's
script block in place of the existing constants. OLD_W / OLD_MICRO pin the
1 Sep 2026 design as the comparison baseline -- update them if the baseline
should move."""
import json, math, sys
sys.path.insert(0,'paper-track')
import voltarget_live_backtest as VL
from state import TARGET_WEIGHTS, MICRO_OVERLAY_WEIGHTS, VOL_TARGET_PA, MICRO_OVERLAY_ENABLED
from long_history_backtest import load_px
from four_leg_overlay import last_trading_day_per_week
assert not MICRO_OVERLAY_ENABLED
rows=VL.build(); rows=rows[0] if isinstance(rows,tuple) else rows
qqq=load_px('data/qqq_long_history.csv'); spy=load_px('data/spy_long_history.csv')
wkq=last_trading_day_per_week(sorted(qqq)); wks=last_trading_day_per_week(sorted(spy))
d0_to_key={v:k for k,v in wkq.items()}
keys=sorted(wkq)
# end date of each row's week = next weekly key's qqq date
end_date={}
for r in rows:
    k=d0_to_key[r['d0']]; nk=keys[keys.index(k)+1]; end_date[r['d0']]=wkq[nk]
OLD_W={'A':(.8,.2,0,0,0),'B':(.25,.75,0,0,0),'C':(1,0,0,0,0),'D':(0,0,.7,0,.3),'E':(0,0,0,.5,.5),'F':(.3,0,0,0,.7)}
OLD_MICRO={('A',True):(.88,.12,0,0,0),('D',False):(.56,0,.14,0,.3)}
def vt(w,v):
    m=1.0 if not v else min(1.0,VOL_TARGET_PA/v); risky=sum(w[:4]); return tuple(x*m for x in w[:4])+(1-risky*m,)
def new_w(r): return vt(TARGET_WEIGHTS[r['state']], r['vol'])
def old_w(r):
    k=(r['state'],r['agree']); return vt(OLD_MICRO.get(k, OLD_W[r['state']]), r['vol'])
def nav(wfn):
    prev=None; out=[]; n=1.0
    for r in rows:
        w=wfn(r); cost=VL.ONE_WAY_SPREAD*sum(abs(w[i]-(prev[i] if prev else 0)) for i in range(5))
        n*=1+sum(w[i]*r['legs'][i] for i in range(5))-cost; out.append(n); prev=w
    return out
NEW=nav(new_w); OLD=nav(old_w)
spmo=[];q=[];s=[];a=b=c=1.0
for r in rows:
    a*=1+r['bench_spmo']; b*=1+r['bench_qqq']; spmo.append(a); q.append(b)
    # SPY price-only, same weekly grid
    k=d0_to_key[r['d0']]; nk=keys[keys.index(k)+1]
    c*= spy[wks[nk]]/spy[wks[k]]; s.append(c)
DATA=[dict(date=end_date[r['d0']],state=r['state'],strategy=round(NEW[i],6),spmo=round(spmo[i],6),qqq=round(q[i],6),spy=round(s[i],6)) for i,r in enumerate(rows)]
CMP=[dict(date=end_date[r['d0']],state=r['state'],agree=bool(r['agree']),old=round(OLD[i],6),new=round(NEW[i],6),spmo=round(spmo[i],6),qqq=round(q[i],6),spy=round(s[i],6)) for i,r in enumerate(rows)]
out='/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/'
open(out+'DATA.js','w').write('const DATA = '+json.dumps(DATA)+';')
open(out+'COMPARE.js','w').write('const COMPARE_DATA = '+json.dumps(CMP)+';')
def st(navs):
    rets=[navs[0]-1]+[navs[i]/navs[i-1]-1 for i in range(1,len(navs))]
    n=len(rets); m=sum(rets)/n; v=(sum((x-m)**2 for x in rets)/(n-1))**0.5
    pk=1;mdd=0
    for x in navs: pk=max(pk,x); mdd=min(mdd,x/pk-1)
    return navs[-1]**(52/n)-1, m*52/(v*math.sqrt(52)), mdd, navs[-1]
print(f"{len(rows)} weeks {DATA[0]['date']}..{DATA[-1]['date']}")
for lab,v in (('NEW',NEW),('OLD',OLD),('SPMO',spmo),('QQQ',q),('SPY',s)):
    c1,s1,m1,t=st(v); print(f"{lab:<5} CAGR {c1*100:6.2f}%  Sharpe {s1:.3f}  MaxDD {m1*100:6.1f}%  {t:.3f}x")
# by-year
def by(v):
    y={};prev=1.0
    for d,x in zip([r['date'] for r in DATA],v):
        yy=d[:4]; y.setdefault(yy,[prev,x]); y[yy][1]=x; prev=x
    return {k:(b/a-1) for k,(a,b) in y.items()}
Y={k:by(v) for k,v in (('new',NEW),('old',OLD),('spmo',spmo),('qqq',q),('spy',s))}
json.dump({'years':sorted(Y['new']),**{k:[round(Y[k][y],4) for y in sorted(Y['new'])] for k in Y}}, open(out+'byyear.json','w'))
print(json.load(open(out+'byyear.json')))
