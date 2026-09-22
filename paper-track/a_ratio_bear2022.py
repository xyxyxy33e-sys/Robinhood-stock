"""2022 bear: 40/60 vs 50/50 A row (owner, 2026-09-22). Research only; see a_ratio_study.md section 5."""
import os,sys,io,contextlib,math
sys.path.insert(0,'paper-track'); os.environ['TDT_STAGE']='none'; os.environ['DDS_STAGE']='none'
with contextlib.redirect_stdout(io.StringIO()):
    import drawdown_study as DS
from d_substate_fresh import rows, RDAYS
TDT=DS.TDT
def qret(h):
    if h=='proxy': return {r['d']:r['qqq'] for r in rows}
    px=TDT.RQQQ; ds=RDAYS
    return {ds[i]:px[ds[i+1]]/px[ds[i]]-1 for i in range(len(ds)-1)}
ARMS=[('50/50',None),('40/60',(0.4,0.6,0,0,0))]
def isA(x): return x['eff']=='A' and not x['gate'] and x['st'] not in 'EF'
for h in ('real','proxy'):
    Q=qret(h)
    D={lab:DS.sim(h,a_row=a,detail=True)[0] for lab,a in ARMS}
    print(f"\n===== {h.upper()} =====")
    for lo,hi,name in (('2022-01-01','2022-12-31','calendar 2022'),('2021-11-19','2022-12-28','QQQ peak->trough 19 Nov 21 - 28 Dec 22'),('2021-11-01','2023-12-31','Nov 2021 - end 2023 (bear + recovery)')):
        print(f"  {name}")
        for lab,_ in ARMS:
            det=[x for x in D[lab] if lo<=x['d']<=hi]
            nav=1;pk=1;mdd=0
            for x in det:
                nav*=1+x['net']; pk=max(pk,nav); mdd=min(mdd,nav/pk-1)
            nA=sum(1 for x in det if isA(x))
            ra=1
            for x in det:
                if isA(x): ra*=1+x['net']
            print(f"    {lab}: return {100*(nav-1):+7.2f}%  maxDD inside {100*mdd:6.1f}%  A days {nA:3d}/{len(det)}  return earned on A days {100*(ra-1):+6.2f}%")
        q=1;pk=1;m=0
        for d in [x['d'] for x in D['50/50'] if lo<=x['d']<=hi]:
            q*=1+Q.get(d,0); pk=max(pk,q); m=min(m,q/pk-1)
        print(f"    QQQ : return {100*(q-1):+7.2f}%  maxDD inside {100*m:6.1f}%")
    # A episodes in 2021-11..2022-12 and the per-episode difference
    print("  A-row stretches Nov 2021 - Dec 2022 (40/60 minus 50/50):")
    det5=[x for x in D['50/50'] if '2021-11-01'<=x['d']<='2022-12-31']
    det4={x['d']:x for x in D['40/60']}
    run=[]
    def flush(run):
        if not run: return
        a=b=1
        for x in run: a*=1+x['net']; b*=1+det4[x['d']]['net']
        print(f"    {run[0]['d']} .. {run[-1]['d']} ({len(run):3d}d): 50/50 {100*(a-1):+6.2f}%  40/60 {100*(b-1):+6.2f}%  diff {100*(b-a):+5.2f}pp")
    for x in det5:
        if isA(x): run.append(x)
        else: flush(run); run=[]
    flush(run)
    # state occupancy 2022
    from collections import Counter
    c=Counter(('gated D' if x['gate'] else (x['st'] if x['st'] in 'EF' else x['eff'])) for x in D['50/50'] if '2022-01-01'<=x['d']<='2022-12-31')
    print("  2022 occupancy:",dict(sorted(c.items())))
    # full-period worst drawdown episodes
    for lab,_ in ARMS:
        nav=1;pk=1;pkd=None;worst=(0,None,None)
        for x in D[lab]:
            nav*=1+x['net']
            if nav>pk: pk=nav;pkd=x['d']
            dd=nav/pk-1
            if dd<worst[0]: worst=(dd,pkd,x['d'])
        print(f"  full-history worst DD {lab}: {100*worst[0]:.1f}%  peak {worst[1]} trough {worst[2]}")
