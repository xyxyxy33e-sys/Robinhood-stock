import wash, numpy as np, datetime as dt
from wash import *
out=[]
def Pn(*a):
    s=' '.join(str(x) for x in a); print(s,flush=True); out.append(s)
BK=608122.0
TODAY=np.zeros(len(TK)); TODAY[TI['TQQQ']]=0.428; TODAY[TI['VIXY']]=0.200; TODAY[TI['BOXX']]=0.372
STN={0:'A',1:'B',2:'C',3:'D',4:'E',5:'F'}
def years(real):
    wash.setpanel(real); Y=sorted(set(wash.YR[wash.S0:]))
    res=[]
    for y in Y:
        idx=[i for i in range(wash.S0,wash.T) if wash.YR[i]==y]
        full=(real and y>=2016 and y<=2025) or ((not real) and 2002<=y<=2025)
        if not full: continue
        i0,i1=idx[0],idx[-1]
        W=wash.W7
        d=dict(y=y,state=STN.get(int(wash.EFF[i0]),'?'))
        # regime-exit counts
        tq=W[i0:i1+1,TI['TQQQ']]>1e-6; d['tq_exits']=int((tq[:-1]&~tq[1:]).sum())
        vx=W[i0:i1+1,TI['VIXY']]>1e-6; d['vx_sw']=int((vx[:-1]!=vx[1:]).sum())
        d['reb']=0
        for var,kw in (('plain',dict()),('seed',dict(seed=31400.0)),('today',dict(init_w=TODAY)),('today+seed',dict(init_w=TODAY,seed=31400.0))):
            ql={}
            r=simulate('BASE','FIFO',taxed=False,i0=i0,i1=i1,book0=BK,qlog=ql,**kw)
            st,lt=r['real'].get(y,[0,0])
            d[var]=dict(st=st,lt=lt,tot=st+lt,wash=r['wash_by_year'].get(y,0),unr=r['ua']+r['ub'],pend=r['pend_open'],q=ql,nreb=r['nreb'],end=r['acct'][-1])
        d['reb']=d['plain']['nreb']
        res.append(d)
    return res
def pct(a,q): return float(np.percentile(a,q))
def summ(lab,res,var):
    st=np.array([d[var]['st'] for d in res]); lt=np.array([d[var]['lt'] for d in res]); tt=st+lt
    f=lambda a:' '.join('%9.0f'%pct(a,q) for q in (10,25,50,75,90))
    Pn('%-34s n=%2d  p10..p90 (10/25/50/75/90):'%(lab,len(res)))
    Pn('    net ST   '+f(st)); Pn('    net LT   '+f(lt)); Pn('    total    '+f(tt))
    Pn('    P(net realized loss)=%.0f%%  share of years ST>=50%% of positive gains=%.0f%%  mean total %.0f'%(100*(tt<0).mean(),100*np.mean([ (d[var]['st']>0 and d[var]['st']>=abs(d[var]['lt'])) for d in res]),tt.mean()))
Pn('2027 CAPITAL-GAIN FORECAST by historical-year replay. BASE (live design + L1), FIFO, $608,122 book, no deposits, no tax payments (gains are pre-tax $; wash rule applied).')
Pn('Each calendar year Y: buy the target at the first session of Y (all lots short-term, basis = price), run to the last session of Y. Variants: plain; seed (+$31.4k deferred TQQQ loss added to first TQQQ lot basis);')
Pn('today (every year starts from 42.8% TQQQ / 20% VIXY / 37.2% BOXX instead of the date target); today+seed. Real = 2016-2025 (10 yrs, VIXY sleeve in). Proxy = 2002-2025 (24 yrs, QQQ-based legs, NO VIX sleeve).')
for real,nm in ((True,'REAL 2016-2025'),(False,'PROXY 2002-2025')):
    res=years(real)
    Pn(); Pn('======== '+nm)
    Pn('  per year: start-state, TQQQ full exits, VIXY on/off switches, rebalances | plain: ST LT total wash$ endUnreal pendingLoss | seed total | today total')
    for d in res:
        p=d['plain']; Pn('  %d %s exits %2d vixsw %2d reb %3d | ST %9.0f LT %8.0f tot %9.0f wash %8.0f unreal %9.0f pend %7.0f | seed tot %9.0f | today tot %9.0f'%(d['y'],d['state'],d['tq_exits'],d['vx_sw'],d['reb'],p['st'],p['lt'],p['tot'],p['wash'],p['unr'],p['pend'],d['seed']['tot'],d['today']['tot']))
    for var in ('plain','seed','today','today+seed'): summ(nm+' / '+var,res,var)
    # state conditional
    for stt in ('D','A'):
        sub=[d for d in res if d['state']==stt]
        if len(sub)>=2: summ(nm+' / starts in %s (plain)'%stt,sub,'plain')
        else: Pn(nm+' / starts in %s: n=%d %s'%(stt,len(sub),[ (d['y'],round(d['plain']['tot'])) for d in sub]))
    # quarter timing
    qs=np.zeros(4)
    for d in res:
        for k,v in d['plain']['q'].items(): qs[k]+=v
    Pn('  timing of GROSS positive realized gains by quarter (share): '+' '.join('Q%d %.0f%%'%(i+1,100*qs[i]/qs.sum()) for i in range(4)))
    Pn('  median TQQQ full exits/yr %.0f ; median VIXY switches/yr %.0f ; median rebalances/yr %.0f ; median end-of-year unrealized (ST+LT) %.0f ; median pending/open wash loss at year end %.0f'%(
        np.median([d['tq_exits'] for d in res]),np.median([d['vx_sw'] for d in res]),np.median([d['reb'] for d in res]),np.median([d['plain']['unr'] for d in res]),np.median([d['plain']['pend'] for d in res])))
open('wash_forecast.log','w').write('\n'.join(out)+'\n')
