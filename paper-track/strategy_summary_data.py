"""Regenerate the DATA / COMPARE_DATA series behind the "Strategy vs Benchmarks"
artifact (https://claude.ai/code/artifact/c21e2827-b249-4f72-b8bc-7edbea289636)
from state.py's CURRENT design, plus the by-year table. Writes DATA.js, COMPARE.js
and byyear.json to the scratchpad path below; splice them into the artifact's
script block in place of the existing constants.

NEW = the live design as of 2026-09-19 (A=50/50, D=100% QLD gated to cash
by breadth pct < 0.20 OR 200d gap < 2%, 20/100 fast re-entry overlay on
B/C/F, graded extension trim on A, plain 30d vol). OLD = the 2026-09-09
design (identical minus the state-D gate) -- the prior comparison baseline,
kept as the "before" column so the gate's effect is visible on its own.

Data shim (2026-09-19): voltarget_live_backtest hard-codes a path that does
not exist here, so the same symlink farm d_substate_fresh.py builds is used
(SPMO/TQQQ/QLD/XLU -> data/*_ohlc.csv, DGS3MO -> data/dgs3mo_full.csv,
synthetic BOXX from T-bills)."""
import json, math, sys, os
sys.path.insert(0,'paper-track')
SCRATCH='/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad'
_TMP=os.path.join(SCRATCH,'kairos_shim'); _ETF=os.path.join(_TMP,'etf'); os.makedirs(_ETF,exist_ok=True)
for dst,src in {'SPMO.csv':'spmo_ohlc.csv','TQQQ.csv':'tqqq_ohlc.csv','QLD.csv':'qld_ohlc.csv','XLU.csv':'xlu_ohlc.csv'}.items():
    pth=os.path.join(_ETF,dst)
    if not os.path.lexists(pth): os.symlink(os.path.abspath(os.path.join('data',src)),pth)
pth=os.path.join(_TMP,'DGS3MO.csv')
if not os.path.lexists(pth): os.symlink(os.path.abspath('data/dgs3mo_full.csv'),pth)
import backtest_overlay_etf as BOE
import voltarget_live_backtest as VL
BOE.ROBINHOOD_REPO=_TMP; VL.REPO=_TMP
from state import (TARGET_WEIGHTS, VOL_TARGET_PA, MICRO_OVERLAY_ENABLED, compute_fast_states, effective_state,
                   compute_extension_gaps, extension_scale, d_gate_active)
from long_history_backtest import load_px, load_tbill_long, make_rate_lookup, cash_index
from four_leg_overlay import last_trading_day_per_week
import breadth_tracker as BT
assert not MICRO_OVERLAY_ENABLED
qqq=load_px('data/qqq_long_history.csv'); spy=load_px('data/spy_long_history.csv')
qd=sorted(qqq)
_boxx=os.path.join(_ETF,'BOXX.csv')
if not os.path.exists(_boxx):
    ci=cash_index(qd, make_rate_lookup(load_tbill_long()))
    with open(_boxx,'w') as f:
        f.write('d,c\n')
        for d in qd: f.write(f'{d},{ci[d]*100:.6f}\n')
rows=VL.build(); rows=rows[0] if isinstance(rows,tuple) else rows
fast=compute_fast_states(qd,qqq); gaps=compute_extension_gaps(qd,qqq)
def _load_dc(path):
    import csv; out={}
    for r in csv.DictReader(open(path)):
        try: out[r['d']]=float(r['c'])
        except ValueError: pass
    return out
_common,_x=BT.relative_strength_series(qd,_load_dc('data/QQEW_daily_ext.csv'),qqq)
BP=dict(zip(_common,BT.trailing_pct(_x)))
wkq=last_trading_day_per_week(sorted(qqq)); wks=last_trading_day_per_week(sorted(spy))
d0_to_key={v:k for k,v in wkq.items()}
keys=sorted(wkq)
# SPY's long series can end before QQQ's: keep only weeks whose end date SPY also has
rows=[r for r in rows if keys.index(d0_to_key[r['d0']])+1 < len(keys)
      and d0_to_key[r['d0']] in wks and keys[keys.index(d0_to_key[r['d0']])+1] in wks]
end_date={}
for r in rows:
    k=d0_to_key[r['d0']]; nk=keys[keys.index(k)+1]; end_date[r['d0']]=wkq[nk]
def vt(w,v):
    m=1.0 if not v else min(1.0,VOL_TARGET_PA/v); risky=sum(w[:4]); return tuple(x*m for x in w[:4])+(1-risky*m,)
def old_w(r):
    # the 2026-09-09 design: everything below except the state-D gate
    st=effective_state(r['state'], fast[r['d0']])
    w=TARGET_WEIGHTS[st]; f=extension_scale(st, gaps[r['d0']])
    if f<1: w=tuple(x*f for x in w[:4])+(1-f*sum(w[:4]),)
    return vt(w, r['vol'])
def new_w(r):
    # 2026-09-19: the state-D gate, decided on the weekly signal date d0
    if d_gate_active(r['state'], BP.get(r['d0']), gaps[r['d0']][200]):
        return (0.0,0.0,0.0,0.0,1.0)
    return old_w(r)
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
    k=d0_to_key[r['d0']]; nk=keys[keys.index(k)+1]
    c*= spy[wks[nk]]/spy[wks[k]]; s.append(c)
DATA=[dict(date=end_date[r['d0']],state=effective_state(r['state'],fast[r['d0']]),strategy=round(NEW[i],6),spmo=round(spmo[i],6),qqq=round(q[i],6),spy=round(s[i],6)) for i,r in enumerate(rows)]
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
def by(v):
    y={};prev=1.0
    for d,x in zip([r['date'] for r in DATA],v):
        yy=d[:4]; y.setdefault(yy,[prev,x]); y[yy][1]=x; prev=x
    return {k:(b/a-1) for k,(a,b) in y.items()}
Y={k:by(v) for k,v in (('new',NEW),('old',OLD),('spmo',spmo),('qqq',q),('spy',s))}
json.dump({'years':sorted(Y['new']),**{k:[round(Y[k][y],4) for y in sorted(Y['new'])] for k in Y}}, open(out+'byyear.json','w'))
print(json.load(open(out+'byyear.json')))
