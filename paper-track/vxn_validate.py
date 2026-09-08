"""Validation of the ONE VXN overlay that survived, plus the discriminator.

PART 2 of vxn_full_test.py left exactly one survivor of 40: "VXN SMA20 rising
-> x0.5". Note what that already tells us. On VIX -- the WRONG index, on a
window starting 2008 -- five of the same forty survived. Moving to the RIGHT
index with 25 years instead of 18 should STRENGTHEN a real signal. Instead it
eliminated four of five. And 1 survivor in 40 is roughly what chance alone
delivers at a nominal 5% threshold.

So this asks whether the last one is real:
  1. DISCRIMINATOR -- the same rule on QQQ's own REALIZED vol. If realized vol
     does the same job, VXN adds nothing beyond price-derived data.
  2. BLOCK BOOTSTRAP, paired circular, 20/60d blocks, vs live.
  3. LEAVE-ONE-REGIME-OUT -- and this time the dot-com bust is IN the window,
     which it never was for VIX.
  4. TURNOVER.
"""
import sys, math, csv, bisect
sys.path.insert(0, 'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from downturn_review import exposure_control
from state import realized_vol, extension_scale
from block_bootstrap import boot, stats, N_BOOT
from vxn_full_test import VXN, xd, xv, xat, sm, rvv, rvi

def attach(rlist, key, isproxy):
    for r in rlist:
        for n in (10, 30):
            r[f'v{n}'] = realized_vol(ds, px, as_of=r[key], lookback=n) if isproxy \
                         else realized_vol(qd, qqq, as_of=r[key], lookback=n)
        r['vol_live'] = r['v30'] if (r['v10'] is None or r['v30'] is None) else max(r['v10'], r['v30'])
        i, x = xat(r[key]); r['x'] = x
        for n in (20, 50):
            m = sm(xv, i, n); p = sm(xv, i-1, n) if i else None
            r[f'xs{n}'] = m; r[f'xsl{n}'] = (m-p) if (m is not None and p is not None) else None
        j = rvi.get(r[key]); r['rv'] = rvv[j] if j is not None else None
        for n in (20, 50):
            m = sm(rvv, j, n); p = sm(rvv, j-1, n) if j else None
            r[f'rs{n}'] = m; r[f'rsl{n}'] = (m-p) if (m is not None and p is not None) else None
attach(rows, 'd', True); attach(rr, 'd0', False)
cov  = [r for r in rows if r['x'] is not None and r['xs50'] is not None and r['rs50'] is not None]
covr = [r for r in rr   if r['x'] is not None and r['xs50'] is not None]
print(f"proxy {len(cov)} rows {cov[0]['d']}..{cov[-1]['d']}; real weekly {len(covr)}\n")

def mkg(rule, vtf=vt):
    def fn(r):
        w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
        if f < 1: w = tuple(a*f for a in w[:4]) + (1 - f*sum(w[:4]),)
        w = vtf(w, r.get('vol_live') or r['vol'])
        g = rule(r)
        return w if g >= 1.0 else tuple(a*g for a in w[:4]) + (1 - g*sum(w[:4]),)
    return fn
R = {
 'LIVE':              lambda r: 1.0,
 'VXNsma20 rise x0.5':lambda r: 0.5 if (r['xsl20'] is not None and r['xsl20']>0) else 1.0,
 'VXNsma50 rise x0.5':lambda r: 0.5 if (r['xsl50'] is not None and r['xsl50']>0) else 1.0,
 'VXN>SMA20 x0.5':    lambda r: 0.5 if (r['xs20'] is not None and r['x']>r['xs20']) else 1.0,
 'VXN>SMA50 x0.5':    lambda r: 0.5 if (r['xs50'] is not None and r['x']>r['xs50']) else 1.0,
 'RVsma20 rise x0.5': lambda r: 0.5 if (r['rsl20'] is not None and r['rsl20']>0) else 1.0,
 'RV>SMA50 x0.5':     lambda r: 0.5 if (r['rs50'] is not None and r['rv']>r['rs50']) else 1.0,
}
def turnover(rl, fn, band=0.03):
    held=prev=None; n=0
    for r in rl:
        t=fn(r); key=(r['state'],r['agree'])
        if held is None: held=list(t)
        elif key!=prev or sum(abs(t[j]-held[j]) for j in range(5))>band: n+=1; held=list(t)
        g=sum(held[j]*r['legs'][j] for j in range(5)); dn=1+g
        if dn>0: held=[held[j]*(1+r['legs'][j])/dn for j in range(5)]
        prev=key
    return n/(len(rl)/252.0)

base = evaluate(cov, mkg(R['LIVE'])); baser = RF.eval_real(covr, mkg(R['LIVE'], RF.vt))
S = {}
print(f"{'rule':<20} CAGR/Sharpe/MDD      S / H       expo   ctlSh  reb/yr  real Sharpe")
for lab, rule in R.items():
    fn = mkg(rule); ev = evaluate(cov, fn); S[lab] = run(cov, fn)[0]
    e = RF.eval_real(covr, mkg(rule, RF.vt)); k1, c1 = exposure_control(cov, ev['risky'])
    print(f"  {lab:<20} {ev['cagr']*100:5.2f}/{ev['sharpe']:.3f}/{ev['mdd']*100:6.1f}  "
          f"{ev['s_sharpe']:.3f}/{ev['h_sharpe']:.3f}  {ev['risky']*100:5.1f}%  {c1['sharpe']:.3f}  "
          f"{turnover(cov,fn):5.0f}   {e['sharpe']:.3f}")

print(f"\nCIRCULAR BLOCK BOOTSTRAP vs LIVE, {N_BOOT} resamples, paired ({len(cov)} sessions)")
for lab in ('VXNsma20 rise x0.5','VXN>SMA50 x0.5','RVsma20 rise x0.5'):
    a,b = S[lab], S['LIVE']
    la,_=stats(a); lb,_=stats(b); _,sa=stats(a); _,sb=stats(b)
    print(f"  {lab}  (point: {(la-lb)*100:+.2f}pp/yr, {sa-sb:+.3f} Sharpe)")
    for blk in (20,60):
        l1,l2,pl,s1,s2,ps = boot(a,b,blk,seed=hash((lab,blk))&0xffff)
        print(f"     block {blk:>2}d: logret 95% CI [{l1*100:+.2f},{l2*100:+.2f}]pp P(<=0)={pl:.3f} | "
              f"Sharpe 95% CI [{s1:+.3f},{s2:+.3f}] P(<=0)={ps:.3f}")

print("\nLEAVE-ONE-REGIME-OUT vs LIVE (dot-com now IN the window)")
REG=[('dot-com 2001-2002','2001-01-01','2002-12-31'),('GFC 2007-2009','2007-01-01','2009-12-31'),
     ('COVID 2020','2020-01-01','2020-12-31'),('2022 bear','2022-01-01','2022-12-31'),
     ('SPMO era 2015-11+','2015-11-01','2099-01-01')]
for lab in ('VXNsma20 rise x0.5','VXN>SMA50 x0.5'):
    print(f"  {lab}")
    for rl,a0,b0 in REG:
        keep=[i for i,r in enumerate(cov) if not (a0<=r['d']<=b0)]
        _,sa=stats([S[lab][i] for i in keep]); _,sb=stats([S['LIVE'][i] for i in keep])
        print(f"     drop {rl:<20} Sharpe {sa-sb:+.3f}")
