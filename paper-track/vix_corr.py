"""Correlation of the strategy's own returns with VIX. Split into
CONTEMPORANEOUS (same session as the return) and PREDICTIVE (VIX known before
the return), because they answer different questions and are easy to conflate.

Alignment note, learned the hard way 2026-09-08: improvement_search.build()
sets row['d'] = d0 and row['legs'] = the d0->d1 return. So pairing rets[i]
with vix[rows[i]['d']] is a PREDICTIVE pairing, not a contemporaneous one.
The contemporaneous VIX change for row i is vix[d1] - vix[d0], and d1 is the
NEXT row's 'd'."""
import sys, math, csv, bisect
sys.path.insert(0, 'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from improvement_search import run
from vix_estimator_test import load_vix

vix = load_vix(); vd = sorted(vix)
def at(d):
    i = bisect.bisect_right(vd, d) - 1
    return vix[vd[i]] if i >= 0 else None
for r in rows: r['vix'] = at(r['d'])

cov = [r for r in rows if r['vix'] is not None]
rets, _ = run(cov, mk(W))
qret = {r['d']: r['legs'] for r in cov}

def corr(a, b):
    n = len(a); ma, mb = sum(a)/n, sum(b)/n
    va = sum((x-ma)**2 for x in a); vb = sum((y-mb)**2 for y in b)
    return sum((x-ma)*(y-mb) for x, y in zip(a, b))/math.sqrt(va*vb) if va and vb else float('nan')

# contemporaneous: return over d0->d1 vs VIX change over d0->d1
c_ret, c_dvix, c_lvl = [], [], []
for i in range(len(cov)-1):
    d0, d1 = cov[i]['d'], cov[i+1]['d']
    v0, v1 = at(d0), at(d1)
    if v0 is None or v1 is None: continue
    c_ret.append(rets[i]); c_dvix.append(v1-v0); c_lvl.append(v0)
qqq_ret = [cov[i]['legs'][1]/3.0 for i in range(len(cov)-1)]   # TQQQ/3 ~ QQQ daily

print(f"n = {len(c_ret)} sessions, {cov[0]['d']}..{cov[-1]['d']}\n")
print("CONTEMPORANEOUS (VIX move over the SAME session as the return)")
print(f"  corr(strategy return, VIX change)   {corr(c_ret, c_dvix):+.3f}")
print(f"  corr(QQQ return,      VIX change)   {corr(qqq_ret, c_dvix):+.3f}   <- sanity check, should be strongly negative")
print(f"  corr(strategy return, VIX level)    {corr(c_ret, c_lvl):+.3f}")
print()
print("PREDICTIVE (VIX known at d0, return earned d0->d1)")
lv  = [r['vix'] for r in cov]
dv  = [lv[i]-lv[i-1] for i in range(1, len(lv))]
print(f"  corr(VIX level at d0,  next return) {corr(lv, rets):+.3f}")
print(f"  corr(VIX change to d0, next return) {corr(dv, rets[1:]):+.3f}")
print()
# how much of the strategy's vol-target de-levering VIX would have anticipated
hi = sorted(range(len(c_lvl)), key=lambda i: -c_lvl[i])[:len(c_lvl)//10]
print(f"top-decile VIX days: mean strategy return {1e4*sum(c_ret[i] for i in hi)/len(hi):+.1f} bp/day "
      f"vs {1e4*sum(c_ret)/len(c_ret):+.1f} bp/day overall")
