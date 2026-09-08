"""Validation of the VIX-DMA overlay that survived vix_overlay_test.py.

Five of forty candidates beat live in BOTH eras, all in the "DMA on VIX"
family at a HALF de-lever (x0.5), all with shallower drawdowns, and all
beating their exposure-matched control. That is a real screen result, so it
gets the full gauntlet before anyone calls it an edge:

  1. TURNOVER. VIX crosses its own short SMA constantly. If the rule trades
     every few days the 4bp cost model in run() may flatter it relative to
     what a live account with a drift band would actually pay.
  2. THE DISCRIMINATOR. "VIX above its own moving average" is a
     vol-is-accelerating detector. QQQ's OWN REALIZED vol has a moving
     average too. If realized-vol-DMA does the same job, then VIX contributes
     NOTHING beyond a signal we can compute from price alone, with no
     external data feed, no S&P-vs-Nasdaq mismatch, and history back to 2000
     instead of 2008. This is the test that decides whether VIX matters here.
  3. BLOCK BOOTSTRAP, paired, circular, 20/60d blocks -- the standard applied
     in block_bootstrap.py after day-shuffled permutations were shown to
     overstate significance.
  4. LEAVE-ONE-REGIME-OUT over the regimes that exist inside the 2008+ window.
  5. MULTIPLE TESTING. 40 candidates were swept to find these 5. Reported
     alongside, not buried.
"""
import sys, math, bisect, random
sys.path.insert(0, 'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from downturn_review import exposure_control
from state import realized_vol, extension_scale
from vix_estimator_test import load_vix
from block_bootstrap import boot, stats, N_BOOT

vix = load_vix(); vd = sorted(vix); vixv = [vix[d] for d in vd]
def vat(d):
    i = bisect.bisect_right(vd, d) - 1
    return (i, vix[vd[i]]) if i >= 0 else (None, None)
def sm(seq, i, n):
    if i is None or i + 1 < n: return None
    return sum(seq[i - n + 1:i + 1]) / n

# realized-vol series on the SAME calendar, for the discriminator
rv = {}
for d in ds: rv[d] = realized_vol(ds, px, as_of=d, lookback=30)
rvd = [d for d in ds if rv[d] is not None]; rvv = [rv[d] for d in rvd]
rvix = {d: i for i, d in enumerate(rvd)}

def attach(rlist, key):
    for r in rlist:
        i, x = vat(r[key]); r['vix'] = x
        for n in (20, 50):
            m = sm(vixv, i, n); r[f'vs{n}'] = m
            p = sm(vixv, i - 1, n) if i else None
            r[f'vsl{n}'] = (m - p) if (m is not None and p is not None) else None
        j = rvix.get(r[key])
        r['rv'] = rvv[j] if j is not None else None
        for n in (20, 50):
            m = sm(rvv, j, n); r[f'rs{n}'] = m
            p = sm(rvv, j - 1, n) if j else None
            r[f'rsl{n}'] = (m - p) if (m is not None and p is not None) else None
attach(rows, 'd')
for r in rr:
    for n in (10, 30): r[f'v{n}'] = realized_vol(qd, qqq, as_of=r['d0'], lookback=n)
    r['vol_live'] = r['v30'] if (r['v10'] is None or r['v30'] is None) else max(r['v10'], r['v30'])
attach(rr, 'd0')

cov  = [r for r in rows if r['vix'] is not None and r['vs50'] is not None and r['rs50'] is not None]
covr = [r for r in rr   if r['vix'] is not None and r['vs50'] is not None]
print(f"proxy {len(cov)} rows {cov[0]['d']}..{cov[-1]['d']}; real weekly {len(covr)}\n")

def mkg(rule, vtf=vt):
    def fn(r):
        w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
        if f < 1: w = tuple(x*f for x in w[:4]) + (1 - f*sum(w[:4]),)
        w = vtf(w, r.get('vol_live') or r['vol'])
        g = rule(r)
        return w if g >= 1.0 else tuple(x*g for x in w[:4]) + (1 - g*sum(w[:4]),)
    return fn

RULES = {
  'LIVE':               lambda r: 1.0,
  'VIX>SMA20 x0.5':     lambda r: 0.5 if r['vs20'] is not None and r['vix'] > r['vs20'] else 1.0,
  'VIX>SMA50 x0.5':     lambda r: 0.5 if r['vs50'] is not None and r['vix'] > r['vs50'] else 1.0,
  'VIXsma20 rise x0.5': lambda r: 0.5 if (r['vsl20'] is not None and r['vsl20'] > 0) else 1.0,
  'VIXsma50 rise x0.5': lambda r: 0.5 if (r['vsl50'] is not None and r['vsl50'] > 0) else 1.0,
  # ---- discriminator: identical rules on QQQ's OWN realized vol, no VIX ----
  'RV>SMA20 x0.5':      lambda r: 0.5 if r['rs20'] is not None and r['rv'] > r['rs20'] else 1.0,
  'RV>SMA50 x0.5':      lambda r: 0.5 if r['rs50'] is not None and r['rv'] > r['rs50'] else 1.0,
  'RVsma20 rise x0.5':  lambda r: 0.5 if (r['rsl20'] is not None and r['rsl20'] > 0) else 1.0,
  'RVsma50 rise x0.5':  lambda r: 0.5 if (r['rsl50'] is not None and r['rsl50'] > 0) else 1.0,
}

def turnover(rlist, fn, band=0.03):
    held = prev = None; n = 0
    for r in rlist:
        t = fn(r); key = (r['state'], r['agree'])
        if held is None: held = list(t)
        else:
            if key != prev or sum(abs(t[j]-held[j]) for j in range(5)) > band:
                n += 1; held = list(t)
        g = sum(held[j]*r['legs'][j] for j in range(5)); dn = 1+g
        if dn > 0: held = [held[j]*(1+r['legs'][j])/dn for j in range(5)]
        prev = key
    return n / (len(rlist)/252.0)

base = evaluate(cov, mkg(RULES['LIVE']))
baser = RF.eval_real(covr, mkg(RULES['LIVE'], RF.vt))
series = {}
print(f"{'rule':<20} CAGR/Sharpe/MDD      S / H       expo   ctlSh  reb/yr  real Sharpe")
for lab, rule in RULES.items():
    fn = mkg(rule)
    ev = evaluate(cov, fn); series[lab] = run(cov, fn)[0]
    e = RF.eval_real(covr, mkg(rule, RF.vt))
    k1, c1 = exposure_control(cov, ev['risky'])
    tb = turnover(cov, fn)
    print(f"  {lab:<20} {ev['cagr']*100:5.2f}/{ev['sharpe']:.3f}/{ev['mdd']*100:6.1f}  "
          f"{ev['s_sharpe']:.3f}/{ev['h_sharpe']:.3f}  {ev['risky']*100:5.1f}%  {c1['sharpe']:.3f}  "
          f"{tb:5.0f}   {e['sharpe']:.3f}")

print(f"\nCIRCULAR BLOCK BOOTSTRAP vs LIVE, {N_BOOT} resamples, paired, 2008+ ({len(cov)} sessions)")
for lab in ('VIX>SMA20 x0.5','VIX>SMA50 x0.5','VIXsma20 rise x0.5','RV>SMA50 x0.5','RVsma20 rise x0.5'):
    a, b = series[lab], series['LIVE']
    la,_ = stats(a); lb,_ = stats(b); _,sa = stats(a); _,sb = stats(b)
    print(f"  {lab}  (point: {(la-lb)*100:+.2f}pp/yr, {sa-sb:+.3f} Sharpe)")
    for blk in (20, 60):
        l1,l2,pl,s1,s2,ps = boot(a,b,blk,seed=hash((lab,blk)) & 0xffff)
        print(f"     block {blk:>2}d: logret 95% CI [{l1*100:+.2f},{l2*100:+.2f}]pp P(<=0)={pl:.3f} | "
              f"Sharpe 95% CI [{s1:+.3f},{s2:+.3f}] P(<=0)={ps:.3f}")

print("\nLEAVE-ONE-REGIME-OUT (Sharpe diff vs LIVE, dropping that window)")
REG = [('GFC 2008-2009','2008-01-01','2009-12-31'),('COVID 2020','2020-01-01','2020-12-31'),
       ('2022 bear','2022-01-01','2022-12-31'),('SPMO era 2015-11+','2015-11-01','2099-01-01')]
for lab in ('VIX>SMA50 x0.5','VIXsma20 rise x0.5','RV>SMA50 x0.5'):
    print(f"  {lab}")
    for rl,a0,b0 in REG:
        keep=[i for i,r in enumerate(cov) if not (a0 <= r['d'] <= b0)]
        ca=[series[lab][i] for i in keep]; cb=[series['LIVE'][i] for i in keep]
        _,sa=stats(ca); _,sb=stats(cb)
        print(f"     drop {rl:<20} Sharpe {sa-sb:+.3f}")
