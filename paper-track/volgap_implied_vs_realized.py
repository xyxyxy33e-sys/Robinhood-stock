"""Does the IMPLIED gap (VXN-VIX) add anything beyond the REALIZED gap
(QQQ rv30 - SPY rv30), after realistic execution costs?  (owner, 2026-09-09)

volgap_causal2.py scored the two on DIFFERENT windows (implied from 2003,
realized from 2001) and never paired them. Here: same rows, same rule
(delta tilt on a causal trailing-252 median), direct PAIRED block bootstrap
implied-vs-realized, at 4 / 10 / 20 bp one-way, plus the disagreement days --
the only sessions where the implied series can add anything at all."""
import sys, math
sys.path.insert(0, 'paper-track')
src = open('paper-track/volgap_causal2.py').read().split("for gk, tk, lab in")[0]
exec(src)
import improvement_search as _IS
from block_bootstrap import boot, stats, N_BOOT

P  = [r for r in srows if all(r.get(k) is not None for k in ('gI','tI','gR','tR'))]
Pr = [r for r in rr    if all(r.get(k) is not None for k in ('gI','tI','gR','tR'))]
print(f"same rows: proxy {len(P)} {P[0]['d']}..{P[-1]['d']}; real weekly {len(Pr)}")
def rf_rets(rl, fn, bp):
    prev=None; out=[]
    for r in rl:
        w=fn(r); c=bp*sum(abs(w[i]-(prev[i] if prev else 0)) for i in range(5))
        out.append(sum(w[i]*r['legs'][i] for i in range(5))-c); prev=w
    return out
def real_sharpe(rets):
    m=sum(rets)/len(rets); v=(sum((x-m)**2 for x in rets)/(len(rets)-1))**0.5
    return m/v*52**0.5
V = {'LIVE': (live_fn(), live_fn(RF.vt)),
     'implied d=0.20': (tilt(0.20,'gI','tI'), tilt(0.20,'gI','tI',1,RF.vt)),
     'realized d=0.20': (tilt(0.20,'gR','tR'), tilt(0.20,'gR','tR',1,RF.vt)),
     'implied d=0.10': (tilt(0.10,'gI','tI'), tilt(0.10,'gI','tI',1,RF.vt)),
     'realized d=0.10': (tilt(0.10,'gR','tR'), tilt(0.10,'gR','tR',1,RF.vt))}
orig=_IS.ONE_WAY_SPREAD
_IS.ONE_WAY_SPREAD=0.0; zero={k:run(P,f)[0] for k,(f,_) in V.items()}
SER={}
for bp in (0.0004,0.0010,0.0020):
    _IS.ONE_WAY_SPREAD=bp
    print(f"\n--- one-way cost {bp*1e4:.0f} bp ---")
    print(f"{'variant':<18}{'CAGR/Sharpe/MDD':>20}{'S / H':>15}{'L1 turn/yr':>12}{'real Sh':>9}")
    for k,(f,fr) in V.items():
        ev=evaluate(P,f); rets=run(P,f)[0]; SER[(k,bp)]=rets
        turn=(stats(zero[k])[0]-stats(rets)[0])/bp
        rs=real_sharpe(rf_rets(Pr,fr,bp))
        print(f"{k:<18}{ev['cagr']*100:7.2f}/{ev['sharpe']:.3f}/{ev['mdd']*100:6.1f}"
              f"{ev['s_sharpe']:8.3f}/{ev['h_sharpe']:.3f}{turn:12.1f}x{rs:9.3f}")
_IS.ONE_WAY_SPREAD=orig
print(f"\nPAIRED BLOCK BOOTSTRAP, {N_BOOT} resamples ({len(P)} sessions)")
for bp in (0.0004,0.0020):
    for a,b in (('implied d=0.20','realized d=0.20'),('implied d=0.20','LIVE'),('realized d=0.20','LIVE')):
        ra,rb=SER[(a,bp)],SER[(b,bp)]; la,sa=stats(ra); lb,sb=stats(rb)
        print(f"  [{bp*1e4:.0f}bp] {a} vs {b}: point {(la-lb)*100:+.2f}pp/yr, {sa-sb:+.3f} Sharpe")
        for blk in (20,60):
            l1,l2,pl,s1,s2,ps=boot(ra,rb,blk,seed=hash((a,b,bp,blk))&0xffff)
            print(f"      block {blk:>2}d: logret [{l1*100:+.2f},{l2*100:+.2f}]pp P(<=0)={pl:.3f} | Sharpe [{s1:+.3f},{s2:+.3f}] P(<=0)={ps:.3f}")
# disagreement days: where do the two series lean differently?
_IS.ONE_WAY_SPREAD=0.0004
fi, fr_ = V['implied d=0.20'][0], V['realized d=0.20'][0]
ab=[r for r in P if r['eff'] in ('A','B')]
same=[r for r in ab if (r['gI']>r['tI'])==(r['gR']>r['tR'])]
diff=[r for r in ab if (r['gI']>r['tI'])!=(r['gR']>r['tR'])]
print(f"\nA/B sessions {len(ab)}: the two gaps agree on {len(same)} ({100*len(same)/len(ab):.1f}%), disagree on {len(diff)} ({100*len(diff)/len(ab):.1f}%)")
ri=dict(zip([r['d'] for r in P],run(P,fi)[0])); rr_=dict(zip([r['d'] for r in P],run(P,fr_)[0]))
for lab,grp in (('agree',same),('disagree',diff)):
    di=sum(ri[r['d']]-rr_[r['d']] for r in grp)
    ic=sum(1 for r in grp if r['gI']>r['tI']); 
    print(f"  {lab:<9} n={len(grp):5d}  implied-minus-realized P&L {di*100:+.2f}pp total  ({100*di/len(grp)*252/1:.2f}pp/yr-equivalent)  implied leans core on {100*ic/len(grp):.0f}%")
