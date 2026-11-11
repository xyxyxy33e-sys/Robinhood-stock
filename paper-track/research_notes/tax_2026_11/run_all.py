from wash import *
import wash, io
out=[]
def Pn(*a):
    s=' '.join(str(x) for x in a); print(s,flush=True); out.append(s)
Pn('WASH-SALE-AWARE SUBSTITUTE TEST -- real panel 2015-11-03..2026-11-11, BASE = live design + L1 (engine reproduces 53.0%/2.139).')
Pn('Tax: $600k start book; ST 50.3% (37+13.3), LT 37.1% (20+3.8+13.3); netting + $3k ordinary offset + carryforward; tax paid each 15 Apr (first session on/after) from BOXX first, then pro-rata;')
Pn('wash rule: same ticker +-30 calendar days, share-for-share, disallowed loss -> replacement basis + holding period; fwd and bwd windows; 2bp/side; price-only returns; BOXX = capital asset (gain on sale).')
Pn('End wealth = account value minus liquidation tax (all lots, per-lot ST/LT). After-tax CAGR = (liq/600k)^(252/n)-1. wash$ = cumulative disallowed events (chains re-count a loss each time it is re-washed).')
Pn('Substitute blocked-test: a pending loss sale of the security (>= 0.05% of NAV) within the prior 30 calendar days. Switch-back: see README at bottom. NOT TAX ADVICE.')
yrs=None
res={}
def row(lab, r, b):
    global yrs
    n=r['n']; yrs=n/252; s=stats(r['pre']); sb=stats(b['pre'])
    at=(r['liq']/BOOK0)**(252/n)-1
    return '%-26s pre %5.1f%% %5.3f %6.1f%% (d %+.1fpp %+.3f %+.1fpp) | wash$ %6.2fM | AT %5.1f%% (liq %6.2fM) | reb/yr %5.1f (+%.1f) orders/yr %5.1f subdays %4d xs-short %.2fx'%(
        lab,s['c']*100,s['sh'],s['dd']*100,(s['c']-sb['c'])*100,s['sh']-sb['sh'],(s['dd']-sb['dd'])*100,r['wash_usd']/1e6,at*100,r['liq']/1e6,r['nreb']/yrs,(r['nreb']-b['nreb'])/yrs,r['norders']/yrs,r['subdays'],r['gap_sub'])
for ident in (False,True):
  for m in ('FIFO','HIFO'):
    Pn(); Pn('=== %s lots, %s'%(m,'PESSIMISTIC: TQQQ==QLD identical' if ident else 'TQQQ/QLD/QQQ distinct securities'))
    b=simulate('BASE',m,ident); Pn(row('BASE',b,b)); res[('BASE',m,ident)]=b
    for rule in (['S1L','S1','S1m','S2','S3','S3L'] if not ident else ['S1L','S1','S2','S3','S3L']):
        r=simulate(rule,m,ident); res[(rule,m,ident)]=r; Pn(row(rule,r,b))
Pn(); Pn('=== switch-back variant: EAGER (switch the day the primary is unblocked) vs GUARD, FIFO distinct')
b=res[('BASE','FIFO',False)]
for rule in ('S1','S3'):
    r=simulate(rule,'FIFO',False,sb='eager'); Pn(row(rule+' eager',r,b)); Pn(row(rule+' guard',res[(rule,'FIFO',False)],b))
Book.nowash=True
r=simulate('BASE','FIFO'); Pn(); Pn('Reference: BASE with wash rule switched OFF (upper bound) AT %.1f%%, paid %.1fM'%(((r['liq']/BOOK0)**(252/r['n'])-1)*100, r['paid']/1e6))
Book.nowash=False
# per-year tables
def ytab(lab,r):
    Pn(); Pn('Per-year -- '+lab+'  (ST/LT realized net after wash adj, $; wash = disallowed in that sale-year, $; tax = paid the following April, $; acct = year-end value before that April tax, $)')
    dts=RD[S0+1:]
    ye={}
    for i,d in enumerate(dts): ye[int(d[:4])]=r['acct'][i]
    for y in sorted(r['real']):
        st,lt=r['real'][y]
        Pn('  %d ST %13.0f LT %12.0f wash %12.0f tax(paid %d) %12.0f acct %14.0f'%(y,st,lt,r['wash_by_year'].get(y,0),y+1,r['paid_y'].get(y,0),ye.get(y,0)))
    Pn('  end carryforwards',[round(x) for x in r['cf']],' liquidation tax %.0f'%r['tx_liq'])
ytab('BASE FIFO',res[('BASE','FIFO',False)]); ytab('BASE HIFO',res[('BASE','HIFO',False)]); ytab('S3 FIFO',res[('S3','FIFO',False)]); ytab('S1 FIFO',res[('S1','FIFO',False)])
open('wash_matrix.log','w').write('\n'.join(out)+'\n')
