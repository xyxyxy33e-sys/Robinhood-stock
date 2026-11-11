import sys; sys.path.insert(0,'/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad/gx4')
from common import *
import common as CM
SPD='/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad/gx4'
out=[]
def P(s=''): print(s,flush=True); out.append(s)
PAN=[('REAL',sr,off,pr,'2015-11-02','2021-03-01',True),('PROXY',sig,0,p,'2001-01-02','2015-11-01',False)]
_ql={}; DIAG=[None]
def run2(sg,pn,d0,vm,gline=0.02,bfloor=0.20,scale=None,first=None,ggo=None):
    """scale=(lo,hi_or_None,mode) ; first=(mode,N) ; returns r,tr,ds,w5(T,5)"""
    sg=dict(sg); mac=sg['macro']; g200=sg['gaps'][200]; pct=sg['pct']
    sg['gate_b']=(mac==3)&(pct<bfloor); sg['gate_g']=(mac==3)&(g200<gline); 
    if ggo is not None: sg['gate_g']=(mac==3)&ggo[None]
    sg['gate']=sg['gate_b']|sg['gate_g']
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

P('HIGH-TRIGGER / CLOSE-TRADE variants (H1,H2,H3); trigger line = exact touch price of 1.02 x SMA200 (own price in SMA); trade at close t')
Pt=len(dates)
def hmask(off_,T,trig):
    sl=slice(off_,off_+T); return sl
def build(kind,T,off_):
    sl=slice(off_,off_+T); o_,h_,c_,pl=O[sl],H[sl],C[sl],PL[sl]
    cg=C[sl]/S200[sl]-1
    nanh=np.isnan(h_)
    if kind=='H3': trig=np.where(nanh,cg>=0.02,np.maximum(o_,(h_+c_)/2)>pl)
    else: trig=np.where(nanh,cg>=0.02,h_>pl)
    trig=np.where(np.isnan(cg),False,trig)
    return trig,cg
def gg_for(kind,sg,T,off_):
    trig,cg=build('H3' if kind=='H3' else 'H1',T,off_)
    mac=sg['macro'][0]
    if kind in('H1','H3'): op=trig
    else:
        x={'H2a':0.01,'H2b':0.02}[kind]; op=np.zeros(T,bool); cur=False
        for t in range(T):
            if mac[t]!=3: cur=False
            elif cur:
                if np.isnan(cg[t]) or cg[t]<x: cur=False
            else: cur=bool(trig[t])
            op[t]=cur
    return ~op        # gate_g true when closed (ANDed with macro==3 in run2)
VARS=[('H1 high>line',"H1"),('H2a open on high, exit close<1.01',"H2a"),('H2b open on high, exit close<1.02 later day',"H2b"),('H3 max(o,(h+c)/2)>line',"H3")]
for name,sg,o_,pn,d0,split,vm in PAN:
    T=sg['gate'].shape[1]
    P(name); P(HDR+' | extra entries (runs) / sessions / entryClose<line / TQQQ fwd5 all, below / fwd20 all, below (avg %)')
    r0,tr0,ds0,s00,w0=run2(sg,pn,d0,vm); row('V0',r0,ds0,tr0,split)
    eff=MC._eff(sg,NEW)[0]; g0=sg['gate'][0].astype(bool); tq=pn['tqqq']
    for nm,k in VARS:
        ggo=gg_for(k,sg,T,o_)
        r,tr,ds,s0,wb=run2(sg,pn,d0,vm,ggo=ggo)
        g1=(sg['gate_b'][0]) | ((sg['macro'][0]==3)&ggo)
        ex=(eff==3)&g0&~g1; ex[:s0+1]=False
        starts=[t for t in range(1,T) if ex[t] and not ex[t-1]]
        below=[t for t in starts if (C[o_:o_+T][t]/S200[o_:o_+T][t]-1)<0.02]
        def fw(ts,k_):
            v=[np.prod(1+tq[t+1:t+1+k_])-1 for t in ts if t+k_<T]; return (np.mean(v)*100 if v else float('nan'))
        ex_s=f"{len(starts)} / {int(ex.sum())} / {len(below)} | {fw(starts,5):+.1f},{fw(below,5):+.1f} / {fw(starts,20):+.1f},{fw(below,20):+.1f}"
        row(nm,r,ds,tr,split,chg(wb,w0,s0)+' | '+ex_s)
open(SPD+'/gx4_h.log','w').write('\n'.join(out)+'\n')
