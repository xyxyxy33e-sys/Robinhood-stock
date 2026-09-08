"""Owner's idea, 2026-09-08: the book holds TWO different volatility regimes.
SPMO is an S&P 500 sleeve (its vol index is VIX); TQQQ and QLD are QQQ sleeves
(their vol index is VXN). So track BOTH, and use the GAP between them to set
the core/satellite split -- tilt toward SPMO when the Nasdaq is priced to be
relatively more violent than the S&P, toward the leveraged QQQ legs when it
is not.

This is a better-posed question than anything in the VIX/VXN work so far, for
one structural reason: it is a TILT BETWEEN TWO RISKY LEGS at constant
deployed capital, not a cash gate. Every previous candidate "worked" by
holding less risk, which is why exposure_control killed them all. This one
holds the same capital and changes only the leverage mix, so the right control
is beta_matched_control(), and the usual de-levering confound does not apply.

IT ALSO EXPOSES A REAL INCONSISTENCY IN THE LIVE DESIGN, worth stating whether
or not the tilt works: the vol overlay scales the WHOLE book -- SPMO leg
included -- by min(1, 0.20 / QQQ's realized vol). The S&P sleeve is being
sized by the Nasdaq's volatility. Tested as idea B below.

METHOD, and the constraint that shapes everything here:

  THE 26-YEAR PROXY IS STRUCTURALLY BLIND TO THIS. improvement_search.data()
  models `core` as QQQ total return, so in the proxy BOTH the core and the
  satellite are QQQ -- there is no S&P/Nasdaq divergence in it to exploit, and
  a null result there would mean nothing. STRATEGY.md already says as much
  ("the core leg must be confirmed on real SPMO rows -- the proxy is blind").
  So this test runs on two harnesses instead:
    (1) an SPY-CORE PROXY -- the same machinery with core swapped to SPY total
        return, giving 25 years with a genuine two-index structure. SPY is not
        SPMO, but it carries the index-level vol gap the idea is about.
    (2) the REAL SPMO weekly rows, where the core leg is actually SPMO.
        These are 2015-11+ only, i.e. the SEARCH era with NO holdout -- stated
        rather than glossed.
"""
import sys, math, csv, bisect
sys.path.insert(0, 'paper-track')
import improvement_search as IS
from long_history_backtest import load_px, total_return_index, QQQ_DIV_PA

D = IS.data()
ORIG_CORE = dict(D['core'])
spy = load_px('data/spy_long_history.csv')
ds_all = D['ds']
missing = [d for d in ds_all if d not in spy]
print(f"SPY covers {len(ds_all)-len(missing)}/{len(ds_all)} proxy dates; {len(missing)} missing")
keep = set(d for d in ds_all if d in spy)
spy_on = {d: spy[d] for d in ds_all if d in keep}
SPY_DIV_PA = 1.8   # S&P 500 dividend yield, long-run average; QQQ uses 0.6
SPY_TR = total_return_index(spy_on, SPY_DIV_PA)

def build_rows(core_index):
    """Rebuild proxy rows with a given core total-return series, reusing the
    project's own build()/enrich() rather than reimplementing the loop."""
    D['core'] = core_index
    IS._DATA['core'] = core_index
    from downturn_review import enrich
    rows = enrich(IS.build())
    from state import compute_fast_states, effective_state, sma
    ds, px = D['ds'], D['qqq']
    fast = compute_fast_states(ds, px); v = [px[d] for d in ds]; ix = {d: i for i, d in enumerate(ds)}
    for r in rows:
        i = ix[r['d']]; r['eff'] = effective_state(r['state'], fast[r['d']])
        r['gaps'] = {n: ((v[i]/sma(v, i, n) - 1) if sma(v, i, n) else 0.0) for n in (100, 150, 200)}
    return [r for r in rows if r['d'] in keep]

qrows = build_rows(ORIG_CORE)
srows = build_rows(SPY_TR)
print(f"QQQ-core rows {len(qrows)}, SPY-core rows {len(srows)}\n")
from improvement_search import evaluate, run, vt, SEARCH, HOLDOUT, era
from improvement_search_r2 import beta_of, beta_matched_control
from downturn_review import exposure_control
from state import TARGET_WEIGHTS as W, extension_scale, realized_vol
import return_frontier as RF

def live_fn(vtf=vt, volkey='vol_live'):
    def fn(r):
        w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
        if f < 1: w = tuple(a*f for a in w[:4]) + (1 - f*sum(w[:4]),)
        return vtf(w, r.get(volkey) or r['vol'])
    return fn

chk = evaluate(qrows, live_fn())
print(f"SANITY -- QQQ-core live: {chk['cagr']*100:.2f}/{chk['sharpe']:.3f}/{chk['mdd']*100:.1f} "
      f"S {chk['s_sharpe']:.3f} H {chk['h_sharpe']:.3f}   (standing: 22.12/0.938/-32.8, 1.150/0.780)")
sp = evaluate(srows, live_fn())
print(f"SPY-core live:          {sp['cagr']*100:.2f}/{sp['sharpe']:.3f}/{sp['mdd']*100:.1f} "
      f"S {sp['s_sharpe']:.3f} H {sp['h_sharpe']:.3f}\n")

# ---- the two vol indices, and the realized-vol version of the same gap ------
def load_fred(path, col):
    out, last = {}, None
    for row in csv.DictReader(open(path)):
        s = row[col].strip()
        if s: last = float(s)/100.0
        if last is not None: out[row['observation_date']] = last
    return out
VIX = load_fred('data/vixcls_full.csv', 'VIXCLS')
VXN = load_fred('data/vxncls.csv', 'VXNCLS')
def prior(m, ks, d):
    i = bisect.bisect_right(ks, d) - 1
    return m[ks[i]] if i >= 0 else None
vik, vxk = sorted(VIX), sorted(VXN)
qv30 = {d: realized_vol(D['ds'], D['qqq'], as_of=d, lookback=30) for d in D['ds']}
sv30 = {d: realized_vol(sorted(spy_on), spy_on, as_of=d, lookback=30) for d in sorted(spy_on)}

def attach_gap(rl, key):
    for r in rl:
        d = r[key]
        a, b = prior(VXN, vxk, d), prior(VIX, vik, d)
        r['vxn'], r['vix'] = a, b
        r['gap']  = (a - b) if (a is not None and b is not None) else None      # implied gap
        r['rgap'] = (qv30.get(d) - sv30.get(d)) if (qv30.get(d) and sv30.get(d)) else None  # realized gap
attach_gap(srows, 'd'); attach_gap(qrows, 'd')
rr = RF.real_rows()
from long_history_backtest import load_px as _lp
from state import compute_states as _cs, compute_fast_states as _cfs, effective_state as _es, sma as _sma
qqqp = _lp('data/qqq_long_history.csv'); qd2 = sorted(qqqp)
_qv = [qqqp[d] for d in qd2]; _qix = {d: i for i, d in enumerate(qd2)}
_fast = dict(zip(qd2, _cs(qd2, qqqp, short_n=20, long_n=100)))
for r in rr:
    _i = _qix[r['d0']]
    r['eff'] = _es(r['state'], _fast[r['d0']])
    r['gaps'] = {n: (_qv[_i]/_sma(_qv, _i, n) - 1) if _sma(_qv, _i, n) else 0.0 for n in (100, 150, 200)}
for r in rr:
    for n in (10, 30): r[f'v{n}'] = realized_vol(qd2, qqqp, as_of=r['d0'], lookback=n)
    r['vol_live'] = r['v30'] if (r['v10'] is None or r['v30'] is None) else max(r['v10'], r['v30'])
attach_gap(rr, 'd0')

cov  = [r for r in srows if r['gap'] is not None and r['rgap'] is not None]
covr = [r for r in rr    if r['gap'] is not None]
g = [r['gap'] for r in era(cov, *SEARCH)]
med = sorted(g)[len(g)//2]
print(f"VXN-VIX gap: search-era median {med*100:+.2f} vol pts, "
      f"full range {min(r['gap'] for r in cov)*100:+.1f}..{max(r['gap'] for r in cov)*100:+.1f}")
print(f"corr(implied gap, realized QQQ-SPY vol gap) = ", end='')
a=[r['gap'] for r in cov]; b=[r['rgap'] for r in cov]
ma,mb=sum(a)/len(a),sum(b)/len(b)
va=sum((x-ma)**2 for x in a); vb=sum((y-mb)**2 for y in b)
print(f"{sum((x-ma)*(y-mb) for x,y in zip(a,b))/math.sqrt(va*vb):+.3f}\n")

# ---- IDEA A: tilt core<->satellite on the gap, constant deployed capital ----
def tilt_fn(thr, delta, key='gap', vtf=vt, volkey='vol_live'):
    def fn(r):
        w = list(W[r['eff']])
        gv = r.get(key)
        if gv is not None and r['eff'] in ('A', 'B'):
            d = delta if gv > thr else -delta          # wide gap -> toward core
            c, t = w[0], w[1]
            mv = min(d, t) if d > 0 else max(d, -c)
            w[0], w[1] = c + mv, t - mv
        w = tuple(w); f = extension_scale(r['eff'], r['gaps'])
        if f < 1: w = tuple(a*f for a in w[:4]) + (1 - f*sum(w[:4]),)
        return vtf(w, r.get(volkey) or r['vol'])
    return fn

print("IDEA A -- gap tilt between core and satellite (states A/B), SPY-core proxy 2001+")
print(f"  {'variant':<26} CAGR/Sharpe/MDD      S / H       beta   btlSh  real Sharpe")
b0 = evaluate(cov, live_fn()); b0r = RF.eval_real(covr, live_fn(RF.vt))
print(f"  {'LIVE':<26} {b0['cagr']*100:5.2f}/{b0['sharpe']:.3f}/{b0['mdd']*100:6.1f}  "
      f"{b0['s_sharpe']:.3f}/{b0['h_sharpe']:.3f}   ----   -----  {b0r['sharpe']:.3f}")
res=[]
for key,klab in (('gap','implied'),('rgap','realized')):
    kk=[r[key] for r in era(cov,*SEARCH) if r[key] is not None]; m=sorted(kk)[len(kk)//2]
    for thr,tlab in ((m,'median'),):
        for delta in (0.05,0.10,0.15,0.20):
            fn=tilt_fn(thr,delta,key)
            ev=evaluate(cov,fn); e=RF.eval_real(covr,tilt_fn(thr,delta,key,RF.vt))
            tb=beta_of(cov,fn); k2,c2=beta_matched_control(cov,live_fn(),tb)
            both=ev['s_sharpe']>b0['s_sharpe'] and ev['h_sharpe']>b0['h_sharpe']
            lab=f"{klab} gap {tlab} d={delta:.2f}"
            res.append((lab,ev,e,c2,both))
            print(f"  {lab:<26} {ev['cagr']*100:5.2f}/{ev['sharpe']:.3f}/{ev['mdd']*100:6.1f}  "
                  f"{ev['s_sharpe']:.3f}/{ev['h_sharpe']:.3f}  {tb:.3f}  {c2['sharpe']:.3f}  "
                  f"{e['sharpe']:.3f}{'  BOTH' if both else ''}")
print(f"\n  {sum(1 for x in res if x[4])} of {len(res)} beat live in BOTH eras.")

# ---- CONTROLS. 8-of-8 winning monotonically in delta is the signature of a
# leverage artifact, not a signal (STRATEGY.md: "leverage moves return and
# drawdown together with Sharpe nearly flat"). Three checks decide it:
#   C1 balance -- does the search-era median actually split the full window
#      50/50? If not, the "tilt" is a net leverage add wearing a signal's coat.
#   C2 CONSTANT-TILT control -- the same average core/satellite shift with NO
#      gap signal at all. If a constant tilt does as well, the gap adds nothing.
#      This is the decisive one, and it is the direct analogue of the
#      realized-vol discriminator that decided the VIX/VXN work.
#   C3 SIGN-FLIPPED gap -- tilt the WRONG way. A real signal must lose.
print("\nCONTROLS")
for key,klab in (('gap','implied'),('rgap','realized')):
    kk=[r[key] for r in era(cov,*SEARCH) if r[key] is not None]; m=sorted(kk)[len(kk)//2]
    above=sum(1 for r in cov if r[key] is not None and r[key]>m)
    hi=[r for r in era(cov,*HOLDOUT) if r[key] is not None]
    ah=sum(1 for r in hi if r[key]>m)
    print(f"  C1 {klab} gap: {100*above/len(cov):.1f}% of ALL rows above the search-era median "
          f"({100*ah/len(hi):.1f}% of holdout rows) -- 50% would be balanced")

def const_fn(delta, vtf=vt, volkey='vol_live'):
    """C2: constant shift of `delta` from core to satellite in A/B, no signal."""
    def fn(r):
        w=list(W[r['eff']])
        if r['eff'] in ('A','B'):
            mv=min(delta,w[0]); w[0]-=mv; w[1]+=mv
        w=tuple(w); f=extension_scale(r['eff'],r['gaps'])
        if f<1: w=tuple(a*f for a in w[:4])+(1-f*sum(w[:4]),)
        return vtf(w, r.get(volkey) or r['vol'])
    return fn

print(f"\n  C2 constant tilt (no signal) vs gap tilt, matched by BETA")
print(f"  {'variant':<26} CAGR/Sharpe/MDD      S / H       beta   real Sharpe")
lb = beta_of(cov, live_fn())
print(f"  {'LIVE':<26} {b0['cagr']*100:5.2f}/{b0['sharpe']:.3f}/{b0['mdd']*100:6.1f}  "
      f"{b0['s_sharpe']:.3f}/{b0['h_sharpe']:.3f}  {lb:.3f}  {b0r['sharpe']:.3f}")
for delta in (0.02,0.05,0.08,0.11):
    fn=const_fn(delta); ev=evaluate(cov,fn); e=RF.eval_real(covr,const_fn(delta,RF.vt))
    print(f"  {'const tilt d='+format(delta,'.2f'):<26} {ev['cagr']*100:5.2f}/{ev['sharpe']:.3f}/{ev['mdd']*100:6.1f}  "
          f"{ev['s_sharpe']:.3f}/{ev['h_sharpe']:.3f}  {beta_of(cov,fn):.3f}  {e['sharpe']:.3f}")

print(f"\n  C3 sign-flipped gap (tilt the WRONG way -- a real signal must LOSE)")
for key,klab in (('gap','implied'),('rgap','realized')):
    kk=[r[key] for r in era(cov,*SEARCH) if r[key] is not None]; m=sorted(kk)[len(kk)//2]
    for delta in (0.10,0.20):
        fn=tilt_fn(m,-delta,key); ev=evaluate(cov,fn); e=RF.eval_real(covr,tilt_fn(m,-delta,key,RF.vt))
        print(f"  {klab+' FLIPPED d='+format(delta,'.2f'):<26} {ev['cagr']*100:5.2f}/{ev['sharpe']:.3f}/{ev['mdd']*100:6.1f}  "
              f"{ev['s_sharpe']:.3f}/{ev['h_sharpe']:.3f}  {beta_of(cov,fn):.3f}  {e['sharpe']:.3f}")
