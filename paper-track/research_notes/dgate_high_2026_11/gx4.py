import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad/gx4')
from common import *
import common as CM
SPD='/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad/gx4'
out=[]
def P(s=''): print(s,flush=True); out.append(s)
PAN=[('REAL',sr,off,pr,'2015-11-02','2021-03-01',True),('PROXY',sig,0,p,'2001-01-02','2015-11-01',False)]
_ql={}; DIAG=[None]
def run2(sg,pn,d0,vm,gline=0.02,bfloor=0.20,scale=None,first=None):
    """scale=(lo,hi_or_None,mode) ; first=(mode,N) ; returns r,tr,ds,w5(T,5)"""
    sg=dict(sg); mac=sg['macro']; g200=sg['gaps'][200]; pct=sg['pct']
    sg['gate_b']=(mac==3)&(pct<bfloor); sg['gate_g']=(mac==3)&(g200<gline); sg['gate']=sg['gate_b']|sg['gate_g']
    cfg=NEW; ds=pn['dates']; s0=next(i for i,d in enumerate(ds) if d>=d0)
    w5=MC.target_weights(sg,cfg)[0].copy(); key=MC.regime_key(sg,cfg).astype(np.int64)[0]
    eff=MC._eff(sg,cfg)[0]; gate=sg['gate'][0].astype(bool); g=np.nan_to_num(g200[0],nan=-9)
    zone=MC._zone(sg,cfg)[0]
    base_w=w5.copy()
    if scale is not None:
        lo,hi,f=scale
        ung=(eff==3)&~gate
        if hi is None: fac=np.ones(len(g))
        else: fac=np.where(g>=hi,1.0, np.where(g<lo,1.0, (f if not callable(f) else f(g))))
        fac=np.where(ung,fac,1.0)
        w5[:,:4]*=fac[:,None]; w5[:,4]=1-w5[:,:4].sum(1)
        key=key+np.round(fac*4).astype(np.int64)*1000000000
    if first is not None:
        mode,N=first
        g100=np.nan_to_num(sg['gaps'][100][0],nan=-9)
        act=np.zeros(len(g),bool); T=len(g)
        origin=0; cnt=0; on=False; prev_e=-1; inspell=False
        for t in range(T):
            e=eff[t]
            if e==3:
                if not inspell: inspell=True; origin=prev_e
                if gate[t]: cnt=0; on=False
                else:
                    if t>0 and (gate[t-1] or cnt==0 and not on) and (t==0 or gate[t-1] or eff[t-1]!=3):
                        pass
                    cnt+=1
                    if cnt==1 and origin in (4,5): on=True      # first ungated session of a run
                    if on:
                        if N=='100d':
                            if g100[t]>0: on=False
                        elif cnt>N: on=False
                    act[t]=on
            else:
                inspell=False; cnt=0; on=False; prev_e=e
        t_=w5[:,1].copy(); sh=np.where(act,t_,0.0); DIAG[0]=(int(act[s0:].sum()),int((sh[s0:]>1e-9).sum()),spells(act[s0:]))
        if mode=='qld': w5[:,1]-=sh; w5[:,2]+=sh
        else: w5[:,1]-=sh*0.5; w5[:,2]+=sh*0.5
        key=key+act.astype(np.int64)*2000000000
    cash=w5[:,4].copy()
    legs=[pn['core'],pn['tqqq'],pn['qld'],pn['xlu']]; W=[w5[:,i] for i in range(4)]; used=np.zeros_like(cash)
    if pn is pr and vm:
        al=allowed_raw & ~((eff==3)&~gate&(zone==2))
        legs.append(vixm_r); W.append(np.where(al,cash*S.VIXM_CASH_SHARE,0.0)); used=W[-1].copy()
        key=key+al.astype(np.int64)*100000
    ck=(id(pn),)
    if ck not in _ql: _ql[ck]=None
    deep,pan=qlegs(sg,ds,cfg)
    for j,shr in enumerate((deep,pan)):
        x=np.minimum(cash*shr,cash-used); used=used+x
        legs.append(pn['qqq']); W.append(x); key=key+(shr>0).astype(np.int64)*(10**(6+j))
    legs.append(pn['cash']); W.append(cash-used)
    r,tr=MC.run_strategy(np.stack(W,-1)[None],key[None],np.stack(legs,-1)[None],s0)
    return r[0],tr[0],ds[s0:],s0,w5
def S_(r,ds,tr,split): return st(r,ds,tr,split)
def spells(mask):
    m=np.asarray(mask,bool); return int(((m[1:]&~m[:-1]).sum())+(1 if m[:1].any() else 0))
def row(nm,r,ds,tr,split,chg=''):
    s=S_(r,ds,tr,split)
    P(f"{nm:34}{s['cagr']*100:6.1f}%{s['sh']:8.3f}{s['dd']*100:7.1f}%{s['tpy']:7.1f}{s['sh1']:6.2f}{s['sh2']:6.2f}  {chg}")
HDR=f"{'variant':34}{'CAGR':>7}{'Sharpe':>8}{'maxDD':>8}{'tr/yr':>7}{'Sh h1':>6}{'Sh h2':>6}  sessions/spells changed vs V0"
def chg(wb,w0,s0):
    d=np.abs(wb-w0).sum(1)[s0:]>1e-9
    return f"{int(d.sum())} sess / {spells(d)} spells"
# ---------- baseline
P('Baseline check (target real 53.1%/2.053/-18.3%; proxy 34.4%/1.411/-22.1%)')
BASE={}
for name,sg,o_,pn,d0,split,vm in PAN:
    r,tr,ds,s0,w0=run2(sg,pn,d0,vm); BASE[name]=(r,tr,ds,s0,w0)
    P(name); P(HDR); row('V0',r,ds,tr,split)
# ---------- test 1
P('\n=== TEST 1: SCALE-IN GATE (partial weight between lo and hi above 200d; full-cash below lo; breadth gate unchanged)')
T1=[('50% in 2-3%',(0.02,0.03,0.5)),('50% in 1.5-2.5%',(0.015,0.025,0.5)),('50% in 2-4%',(0.02,0.04,0.5)),
    ('ramp 2->4%',(0.02,0.04,lambda g:(g-0.02)/0.02)),('ramp 2->3%',(0.02,0.03,lambda g:(g-0.02)/0.01))]
for name,sg,o_,pn,d0,split,vm in PAN:
    P(name); P(HDR); r0,tr0,ds0,s0,w0=BASE[name]; row('V0',r0,ds0,tr0,split)
    for nm,sc in T1:
        lo=sc[0]
        r,tr,ds,s0_,wb=run2(sg,pn,d0,vm,gline=lo,scale=sc); row(nm,r,ds,tr,split,chg(wb,w0,s0))
# ---------- test 2
P('\n=== TEST 2: GENTLER FIRST LEG (TQQQ in D row replaced for first N ungated sessions after a gate clear, D spell that began from effective E/F)')
for name,sg,o_,pn,d0,split,vm in PAN:
    P(name); P(HDR); r0,tr0,ds0,s0,w0=BASE[name]; row('V0',r0,ds0,tr0,split)
    for mode in ('half','qld'):
        for N in (5,10,20,'100d'):
            r,tr,ds,s0_,wb=run2(sg,pn,d0,vm,first=(mode,N)); row(f"{'50/50 TQQQ/QLD' if mode=='half' else '100% QLD'} N={N}",r,ds,tr,split,chg(wb,w0,s0)+f"  | flagged sess/with-TQQQ-in-row/spells {DIAG[0]}")
# ---------- test 3
P('\n=== TEST 3: V1 enter-on-high with realistic fills (fill F; extra = row*lev*(close/F-1); +2 one-way trades on a false close)')
FILLS=[('V0 close (no V1)',None),('V1 fill at line (hl_test)',lambda o,h,pl:max(o,pl)),
  ('V1 line+5bp',lambda o,h,pl:max(o,pl)*1.0005),('V1 line+10bp',lambda o,h,pl:max(o,pl)*1.0010),('V1 line+20bp',lambda o,h,pl:max(o,pl)*1.0020),
  ('V1 15min: max(o,l)*(1+.25(h/l-1))',lambda o,h,pl:max(o,pl)*(1+0.25*(h/pl-1))),
  ('V1 line+10bp capped at high',lambda o,h,pl:min(max(o,pl)*1.0010,h))]
for name,sg,o_,pn,d0,split,vm in PAN:
    P(name); P(HDR)
    for nm,f in FILLS:
        if f is None:
            r,tr,ds,info=variant(sg,o_,pn,d0,set(),True,vm); ex=''
        else:
            CM.FILL=f
            r,tr,ds,info=variant(sg,o_,pn,d0,{'V1'},True,vm); e1=info['ev1']; ex=f"{len(e1)} triggers, {sum(1 for x in e1 if x[1])} close back under line"
        row(nm,r,ds,tr,split,ex)
    CM.FILL=lambda o,h,pl:max(o,pl)
# ---------- test 4
P('\n=== TEST 4: GATE NEIGHBOURS (gate line x breadth floor)')
LINES=[0.01,0.015,0.02,0.025,0.03]; FL=[0.15,0.20,0.25]
for name,sg,o_,pn,d0,split,vm in PAN:
    res={}
    for L_ in LINES:
        for b in FL:
            r,tr,ds,s0,_=run2(sg,pn,d0,vm,gline=L_,bfloor=b); res[(L_,b)]=S_(r,ds,tr,split)
    for key_,lab,fmt in (('cagr','CAGR %',lambda x:f"{x*100:6.1f}"),('sh','Sharpe',lambda x:f"{x:6.3f}"),('dd','maxDD %',lambda x:f"{x*100:6.1f}"),('tpy','trades/yr',lambda x:f"{x:6.1f}"),('sh1','Sharpe half1',lambda x:f"{x:6.2f}"),('sh2','Sharpe half2',lambda x:f"{x:6.2f}")):
        P(f"{name} {lab}: rows=line, cols=breadth floor {FL}")
        for L_ in LINES: P(f"  {L_*100:4.1f}% "+' '.join(fmt(res[(L_,b)][key_]) for b in FL)+("   <- live row" if L_==0.02 else ''))
open(SPD+'/gx4.log','w').write('\n'.join(out)+'\n')
