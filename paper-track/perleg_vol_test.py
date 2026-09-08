"""Owner, 2026-09-08: "test blended vol, or SP vol for SPMO, QQQ vol for
TQQQ/QLD." The direct fix to the inconsistency the vol-gap work surfaced --
the overlay currently scales the WHOLE book, SPMO included, by
min(1, 0.20 / QQQ's realized vol), so an S&P sleeve is sized by Nasdaq vol.

THE CONFOUND THAT DECIDES THE TEST DESIGN. SPY vol runs systematically BELOW
QQQ vol. Any variant feeding SPY vol into min(1, T/v) therefore produces a
HIGHER multiplier, de-levers LESS, holds MORE risk -- and would score better
for that reason alone. That is the trap that killed the DMA-slope rule and
every cash-gate candidate this week. Comparing at a fixed T = 0.20 would be
meaningless.

So every variant has its target constant T RE-CALIBRATED by bisection until
its average deployed exposure MATCHES live's. Risk is held constant by
construction, isolating the only question worth asking: is the SHAPE of the
vol signal better when each leg is sized by its own index?

Harness: the SPY-core proxy from volgap_test.py (the 26y proxy models core as
QQQ and is structurally blind to this), plus real SPMO weekly rows. SPY vol
proxies SPMO's vol on both -- SPMO is an S&P momentum sleeve and daily SPMO
history is not in the repo. Stated rather than hidden.
"""
import sys, math
sys.path.insert(0, 'paper-track')
exec(open('paper-track/volgap_test.py').read().split('# ---- IDEA A')[0])
from block_bootstrap import boot, stats, N_BOOT

def rvol(dates, pxm, d, n):
    return realized_vol(dates, pxm, as_of=d, lookback=n)
sd = sorted(spy_on)
QV = {d: (rvol(D['ds'], D['qqq'], d, 30), rvol(D['ds'], D['qqq'], d, 10)) for d in D['ds']}
SV = {d: (rvol(sd, spy_on, d, 30), rvol(sd, spy_on, d, 10)) for d in sd}
def lmax(t):
    a, b = t
    return a if (a is None or b is None) else max(a, b)
def attach_v(rl, key):
    for r in rl:
        d = r[key]
        r['vq'] = lmax(QV.get(d, (None, None)))
        r['vs'] = lmax(SV.get(d, (None, None)))
attach_v(srows, 'd'); attach_v(rr, 'd0')
P  = [r for r in srows if r['vq'] and r['vs']]
Pr = [r for r in rr    if r.get('vq') and r.get('vs')]
mq = sum(r['vq'] for r in P)/len(P); ms = sum(r['vs'] for r in P)/len(P)
print(f"proxy {len(P)} rows {P[0]['d']}..{P[-1]['d']}; real weekly {len(Pr)}")
print(f"mean QQQ vol {mq*100:.2f}%  mean SPY vol {ms*100:.2f}%  ratio {mq/ms:.3f}"
      f"   <- why T must be re-calibrated per variant\n")

def trim_of(r):
    w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
    return w if f >= 1 else tuple(a*f for a in w[:4]) + (1 - f*sum(w[:4]),)

def make(kind, T):
    def fn(r):
        w = trim_of(r); vq, vs = r['vq'], r['vs']
        if kind == 'live':
            m = min(1.0, T/vq) if vq else 1.0
            out = tuple(a*m for a in w[:4])
        elif kind == 'spyonly':
            m = min(1.0, T/vs) if vs else 1.0
            out = tuple(a*m for a in w[:4])
        elif kind == 'perleg':
            mc = min(1.0, T/vs) if vs else 1.0
            mt = min(1.0, T/vq) if vq else 1.0
            out = (w[0]*mc, w[1]*mt, w[2]*mt, w[3]*mc)
        elif kind == 'blend':
            tot = sum(w[:4]) or 1.0
            v = ((w[0]+w[3])*vs + (w[1]+w[2])*vq)/tot
            m = min(1.0, T/v) if v else 1.0
            out = tuple(a*m for a in w[:4])
        elif kind == 'blendlev':
            tot = sum(w[:4]) or 1.0
            v = (w[0]*vs + w[3]*vs + w[1]*3*vq + w[2]*2*vq)/tot
            m = min(1.0, T/v) if v else 1.0
            out = tuple(a*m for a in w[:4])
        return out + (1 - sum(out),)
    return fn

def expo(rl, fn): return run(rl, fn)[1]
LT = 0.20
base = evaluate(P, make('live', LT)); be = expo(P, make('live', LT))
baser = RF.eval_real(Pr, make('live', LT))
print(f"LIVE (T=0.20): expo {be*100:.2f}%  {base['cagr']*100:5.2f}/{base['sharpe']:.3f}/"
      f"{base['mdd']*100:6.1f}  S {base['s_sharpe']:.3f} H {base['h_sharpe']:.3f}  real {baser['sharpe']:.3f}\n")

def calib(kind, te, lo=0.02, hi=4.0):
    for _ in range(60):
        mid = (lo+hi)/2
        if expo(P, make(kind, mid)) < te: lo = mid
        else: hi = mid
    return (lo+hi)/2

print(f"{'variant':<24} T*     expo    CAGR/Sharpe/MDD      S / H       real Sharpe")
SER = {'live': run(P, make('live', LT))[0]}
for kind, lab in (('perleg','per-leg SPY/QQQ'), ('blend','blended vol'),
                  ('blendlev','blend, leverage-aware'), ('spyonly','SPY vol only (ctl)')):
    T = calib(kind, be); fn = make(kind, T)
    ev = evaluate(P, fn); e = RF.eval_real(Pr, make(kind, T)); SER[kind] = run(P, fn)[0]
    both = ev['s_sharpe'] > base['s_sharpe'] and ev['h_sharpe'] > base['h_sharpe']
    print(f"  {lab:<22} {T:.3f}  {expo(P,fn)*100:5.2f}%  {ev['cagr']*100:5.2f}/{ev['sharpe']:.3f}/"
          f"{ev['mdd']*100:6.1f}  {ev['s_sharpe']:.3f}/{ev['h_sharpe']:.3f}  {e['sharpe']:.3f}"
          f"{'  BOTH' if both else ''}")

print(f"\nBLOCK BOOTSTRAP vs LIVE ({N_BOOT} resamples, {len(P)} sessions, exposure-matched)")
for kind, lab in (('perleg','per-leg SPY/QQQ'), ('blendlev','blend, leverage-aware')):
    a, b = SER[kind], SER['live']
    la,_=stats(a); lb,_=stats(b); _,sa=stats(a); _,sb=stats(b)
    print(f"  {lab} (point {(la-lb)*100:+.2f}pp/yr, {sa-sb:+.3f} Sharpe)")
    for blk in (20, 60):
        l1,l2,pl,s1,s2,ps = boot(a, b, blk, seed=hash((kind,blk)) & 0xffff)
        print(f"     block {blk:>2}d: logret [{l1*100:+.2f},{l2*100:+.2f}]pp P(<=0)={pl:.3f} | "
              f"Sharpe [{s1:+.3f},{s2:+.3f}] P(<=0)={ps:.3f}")
