import csv, datetime as dt, collections
rows=list(csv.DictReader(open('/home/user/Robinhood-stock/data/fill_quality.csv')))
D=lambda s: dt.date.fromisoformat(s)
fills=[(D(r['date']),r['symbol'],r['side'],float(r['quantity']),float(r['fill_price'])) for r in rows]
# pre-ledger inventory, reconstructed from run-file positions on 10-09 (post-trade) -- basis ASSUMED = 2026-08-31 close
pre={'TQQQ':(3340.7-2916.2,71.92),'SPMO':(1702.0-1206.1,147.09)}
lots=collections.defaultdict(list)
for s,(q,p) in pre.items(): lots[s].append([q,p,D('2026-08-31')])
buys=collections.defaultdict(list)   # symbol -> [date, shares, remaining_for_wash]
for s,(q,p) in pre.items(): buys[s].append([D('2026-08-31'),q,q])
loss=[]
for d,s,side,q,p in fills:
    if side=='buy': lots[s].append([q,p,d]); buys[s].append([d,q,q])
    else:
        need=q
        while need>1e-9 and lots[s]:
            l=lots[s][0]; m=min(need,l[0]); g=m*(p-l[1]); l[0]-=m; need-=m
            if l[0]<1e-9: lots[s].pop(0)
            if g<0: loss.append([d,s,m,g,l[2]])
res=collections.OrderedDict()
used=collections.defaultdict(float)
for d,s,m,g,bd in loss:
    rem=m
    for b in buys[s]:
        if rem<=1e-9: break
        if abs((b[0]-d).days)<=30 and b[0]!=bd or (b[0]>d and (b[0]-d).days<=30):
            if b[0]==bd and b[0]<=d: continue
            av=b[1]-b[3] if False else b[2]
            x=min(rem,av); b[2]-=x; rem-=x
    key=(d.isoformat(),s); a=res.setdefault(key,[0,0,0]); a[0]+=m; a[1]+=g; a[2]+=g*(m-rem)/m
print('Loss sales since 2026-08-31 (ledger fills 2026-09-08..11-11; FIFO; pre-ledger lots basis assumed 08-31 close):')
tot=0;totw=0
for (d,s),(m,g,w) in res.items():
    print(f'  {d} {s:5} {m:9.1f} sh  realized {g:11,.0f}  washed (est) {w:11,.0f}'); tot+=g; totw+=w
print('total loss slices %.0f, est disallowed %.0f'%(tot,totw))
print('open lots end:'); 
for s,L in lots.items():
    for l in L: print('  ',s,round(l[0],3),round(l[1],3),l[2])
