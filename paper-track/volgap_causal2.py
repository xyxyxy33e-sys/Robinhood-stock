"""Vol-gap tilt, causal threshold done CORRECTLY.

volgap_causal.py had a harness bug I caught in its own output: it built the
trailing median from each row list separately, so the WEEKLY real rows burned
500 *weeks* of warm-up -- real confirmation collapsed from 564 rows to 64
(~15 months), and the proxy lost everything before 2010, i.e. both the
dot-com bust and the GFC. Any bootstrap on that is measuring a window with no
real bear market in it.

Fixed: the trailing median is built ONCE from the DAILY gap series and
attached to daily and weekly rows alike by date lookup. Both harnesses keep
their full samples.

One structural asymmetry that then decides which version is usable:
  - IMPLIED gap (VXN-VIX) needs BOTH indices, and VIXCLS starts 2008-01-02.
    After a 500-session causal warm-up it is usable only from ~2010. No
    dot-com, no GFC onset.
  - REALIZED gap (QQQ vol30 - SPY vol30) needs only price data, available
    from 2000. Usable from ~2002, covering both bears.
Each is therefore evaluated on its OWN maximal window against a LIVE baseline
computed on those same rows -- never against a baseline from a different span.
"""
import sys, math, csv, bisect
sys.path.insert(0, 'paper-track')
exec(open('paper-track/volgap_test.py').read().split('# ---- IDEA A')[0])
from block_bootstrap import boot, stats, N_BOOT

LOOK = 500
def causal_median_series(dates, val):
    """Trailing median of `val` over the previous LOOK observations, by date.
    Uses only data strictly available at that date."""
    out, hist = {}, []
    for d in dates:
        v = val.get(d)
        out[d] = sorted(hist)[len(hist)//2] if len(hist) >= LOOK else None
        if v is not None:
            hist.append(v)
            if len(hist) > LOOK: hist.pop(0)
    return out

dsx = D['ds']
gI = {d: (prior(VXN, vxk, d) - prior(VIX, vik, d))
      if (prior(VXN, vxk, d) is not None and prior(VIX, vik, d) is not None) else None for d in dsx}
gR = {d: (qv30[d] - sv30[d]) if (qv30.get(d) and sv30.get(d)) else None for d in dsx}
tI = causal_median_series(dsx, gI); tR = causal_median_series(dsx, gR)

def attach2(rl, key):
    for r in rl:
        d = r[key]
        r['gI'], r['gR'] = gI.get(d), gR.get(d)
        r['tI'], r['tR'] = tI.get(d), tR.get(d)
attach2(srows, 'd'); attach2(rr, 'd0')

def tilt(delta, gk, tk, sign=1, vtf=vt, volkey='vol_live'):
    def fn(r):
        w = list(W[r['eff']]); g, t = r.get(gk), r.get(tk)
        if g is not None and t is not None and r['eff'] in ('A', 'B'):
            d = sign * (delta if g > t else -delta)
            mv = min(d, w[1]) if d > 0 else max(d, -w[0])
            w[0] += mv; w[1] -= mv
        w = tuple(w); f = extension_scale(r['eff'], r['gaps'])
        if f < 1: w = tuple(a*f for a in w[:4]) + (1 - f*sum(w[:4]),)
        return vtf(w, r.get(volkey) or r['vol'])
    return fn
def const(delta, vtf=vt, volkey='vol_live'):
    def fn(r):
        w = list(W[r['eff']])
        if r['eff'] in ('A', 'B'):
            mv = min(delta, w[0]); w[0] -= mv; w[1] += mv
        w = tuple(w); f = extension_scale(r['eff'], r['gaps'])
        if f < 1: w = tuple(a*f for a in w[:4]) + (1 - f*sum(w[:4]),)
        return vtf(w, r.get(volkey) or r['vol'])
    return fn

for gk, tk, lab in (('gI','tI','IMPLIED gap (VXN-VIX)'), ('gR','tR','REALIZED gap (QQQvol-SPYvol)')):
    P  = [r for r in srows if r.get(gk) is not None and r.get(tk) is not None]
    Pr = [r for r in rr    if r.get(gk) is not None and r.get(tk) is not None]
    ab = sum(1 for r in P if r[gk] > r[tk]); hi = era(P, *HOLDOUT)
    ah = sum(1 for r in hi if r[gk] > r[tk]) if hi else 0
    print(f"\n=== {lab} ===")
    print(f"proxy {len(P)} rows {P[0]['d']}..{P[-1]['d']} | real weekly {len(Pr)} rows"
          f" | above trailing median: {100*ab/len(P):.1f}% all, "
          f"{(100*ah/len(hi)) if hi else float('nan'):.1f}% holdout ({len(hi)} holdout rows)")
    b0 = evaluate(P, live_fn()); b0r = RF.eval_real(Pr, live_fn(RF.vt)); lb = beta_of(P, live_fn())
    print(f"  {'LIVE (these rows)':<24} {b0['cagr']*100:5.2f}/{b0['sharpe']:.3f}/{b0['mdd']*100:6.1f}  "
          f"S {b0['s_sharpe']:.3f} H {b0['h_sharpe']:.3f}  beta {lb:.3f}  real {b0r['sharpe']:.3f}")
    CB = {}
    for d in (0.05, 0.11, 0.15):
        fn = const(d); ev = evaluate(P, fn); e = RF.eval_real(Pr, const(d, RF.vt))
        CB[beta_of(P, fn)] = (ev, e)
        print(f"  {'const d='+format(d,'.2f'):<24} {ev['cagr']*100:5.2f}/{ev['sharpe']:.3f}/{ev['mdd']*100:6.1f}  "
              f"S {ev['s_sharpe']:.3f} H {ev['h_sharpe']:.3f}  beta {beta_of(P,fn):.3f}  real {e['sharpe']:.3f}")
    ser = {'LIVE': run(P, live_fn())[0]}
    for d in (0.10, 0.20):
        for sg, sl in ((1, ''), (-1, ' FLIP')):
            fn = tilt(d, gk, tk, sg); ev = evaluate(P, fn); e = RF.eval_real(Pr, tilt(d, gk, tk, sg, RF.vt))
            bt = beta_of(P, fn); near = min(CB, key=lambda x: abs(x - bt))
            if sg == 1: ser[f'd={d}'] = run(P, fn)[0]
            both = ev['s_sharpe'] > b0['s_sharpe'] and ev['h_sharpe'] > b0['h_sharpe']
            print(f"  {'tilt d='+format(d,'.2f')+sl:<24} {ev['cagr']*100:5.2f}/{ev['sharpe']:.3f}/{ev['mdd']*100:6.1f}  "
                  f"S {ev['s_sharpe']:.3f} H {ev['h_sharpe']:.3f}  beta {bt:.3f}  real {e['sharpe']:.3f}"
                  f"  vs const@{near:.3f}: {ev['sharpe']-CB[near][0]['sharpe']:+.3f}p/"
                  f"{e['sharpe']-CB[near][1]['sharpe']:+.3f}r{'  BOTH' if both else ''}")
    for nm in ('d=0.2',):
        a, b = ser['d=0.2'], ser['LIVE']
        la,_=stats(a); lb2,_=stats(b); _,sa=stats(a); _,sb=stats(b)
        print(f"  bootstrap d=0.20 vs LIVE (point {(la-lb2)*100:+.2f}pp/yr, {sa-sb:+.3f} Sharpe):")
        for blk in (20, 60):
            l1,l2,pl,s1,s2,ps = boot(a, b, blk, seed=hash((lab, blk)) & 0xffff)
            print(f"     block {blk:>2}d: logret [{l1*100:+.2f},{l2*100:+.2f}]pp P(<=0)={pl:.3f} | "
                  f"Sharpe [{s1:+.3f},{s2:+.3f}] P(<=0)={ps:.3f}")
