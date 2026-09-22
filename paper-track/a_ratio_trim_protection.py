"""Does the extension trim protect a heavier A row? (owner, 2026-09-22). Research only; see a_ratio_study.md section 6."""
import os,sys,io,contextlib,math
sys.path.insert(0,'paper-track'); os.environ['TDT_STAGE']='none'; os.environ['DDS_STAGE']='none'
with contextlib.redirect_stdout(io.StringIO()):
    import drawdown_study as DS
from drift_band_test import annual_stats
def isA(x): return x['eff']=='A' and not x['gate'] and x['st'] not in 'EF'
for h in ('real','proxy'):
    print(f"\n===== {h.upper()} =====")
    A5=DS.sim(h,detail=True)[0]; A4=DS.sim(h,a_row=(.4,.6,0,0,0),detail=True)[0]
    # 1 votes on A days, and where the 40/60 extra loss comes from
    from collections import defaultdict
    b=defaultdict(lambda:[0,0.0,0.0,0.0])
    for x,y in zip(A5,A4):
        if not isA(x): continue
        k=min(x['v'],3); b[k][0]+=1; b[k][1]+=math.log1p(y['net'])-math.log1p(x['net']); b[k][2]+=math.log1p(x['net'])
    yrs=len(A5)/252
    print("  A days by trim votes: n | 50/50 log-ret pp/yr contributed | 40/60 minus 50/50 pp/yr")
    for k in sorted(b): print(f"    {k} votes: {b[k][0]:5d} | {b[k][2]*100/yrs:+6.2f} | {b[k][1]*100/yrs:+6.2f}")
    # 2 worst 20 A-days for 50/50 book: votes that day
    worst=sorted([x for x in A5 if isA(x)],key=lambda x:x['net'])[:20]
    print("  20 worst A days for the book: votes = ",[x['v'] for x in worst], " -> with >=1 vote:",sum(1 for x in worst if x['v']>0))
    # 3 drawdown episodes >8%: votes at the peak and on days in the fall
    for lab,D in (('50/50',A5),('40/60',A4)):
        nav=1;pk=1;pkd=0;eps=[];cur=None
        for i,x in enumerate(D):
            nav*=1+x['net']
            if nav>=pk:
                if cur and cur[2]<-0.08: eps.append(cur)
                pk=nav;pkd=i;cur=None
            else:
                dd=nav/pk-1
                if cur is None or dd<cur[2]: cur=(pkd,i,dd)
        if cur and cur[2]<-0.08: eps.append(cur)
        if lab=='50/50':
            print("  50/50 drawdowns deeper than 8%: peak date, trough, depth, max votes in the 20 sessions before the peak, share of the fall spent in A with >=1 vote")
            for p,t,dd in sorted(eps,key=lambda e:e[2])[:8]:
                pre=max(D[j]['v'] for j in range(max(0,p-20),p+1))
                fall=D[p+1:t+1]; nA=sum(1 for x in fall if isA(x)); nV=sum(1 for x in fall if isA(x) and x['v']>0)
                print(f"    {D[p]['d']} -> {D[t]['d']}  {dd*100:6.1f}%   votes pre-peak {pre}   A days in fall {nA}, with a vote {nV}")
    # 4 the same dial with the trim OFF: does the trim change the ratio verdict?
