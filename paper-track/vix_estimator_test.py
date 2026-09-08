"""Is IMPLIED volatility (VIX) a better vol-targeting input than REALIZED vol?

Asked 2026-09-08. Every prior VIX test in this repo used VIX as a FILTER or a
SUBSTATE SPLITTER (substate_research.py, substate_research_deltas.py,
combined_confidence_signal.py, the 0-for-6 defensive-layer search) and all of
them failed. This asks the one question none of them did: the vol overlay --
the thing that actually sizes the book every day -- runs entirely on realized
vol, and vol_estimator_family.py's eleven candidates are ALL realized-vol
windows. VIX has never been in that family.

TWO METHODOLOGICAL POINTS, both of which decide the answer:

1. COVERAGE. VIXCLS starts 2008-01-02. The standing holdout is 2000-2015, so
   VIX cannot see the dot-com bust or the 2000-02 bear at ALL -- precisely the
   regime the holdout exists to test. Letting a VIX variant fall back to
   realized vol before 2008 would silently blend two designs and flatter the
   result, so EVERY variant here (realized ones included) is evaluated on the
   SAME 2008+ rows. The realized-vol numbers therefore will NOT match
   vol_estimator_family.py's full-window figures; that is intended.

2. THE VARIANCE RISK PREMIUM. VIX systematically prints ABOVE subsequent
   realized vol. Feeding raw VIX into min(1, 0.20/vol) therefore de-levers
   more than realized vol does, and any Sharpe gain would be the well-known
   consequence of holding less risk, not of forecasting better. That is the
   exact trap the DMA-slope rule fell into (state.py: "an exposure-matched
   control showed ~2/3 of its edge was simply holding more"). So VIX is tested
   BOTH raw and rescaled by a single constant k = mean(realized30)/mean(vix)
   fitted on the SEARCH era only, which removes the level difference and
   leaves only the timing/shape difference.
"""
import sys, math, csv
sys.path.insert(0, 'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from downturn_review import exposure_control
from improvement_search_r2 import beta_of, beta_matched_control
from improvement_search import SEARCH, HOLDOUT, era, run, annual_stats
from state import realized_vol, extension_scale

VIX_CSV = '/home/user/robinhood/data/kairos/VIXCLS.csv'

def load_vix(path=VIX_CSV):
    """FRED VIXCLS. Market holidays carry an EMPTY value -- forward-fill them
    rather than dropping, so a holiday never silently shortens a lookback."""
    out, last = {}, None
    for row in csv.DictReader(open(path)):
        d, s = row['observation_date'], row['VIXCLS'].strip()
        if s:
            last = float(s) / 100.0          # percent -> annualised fraction
        if last is not None:
            out[d] = last
    return out

vix = load_vix()
vd = sorted(vix)
print(f"VIX  {len(vd)} days  {vd[0]} .. {vd[-1]}")

def prior(m, keys, d):
    """Most recent VIX at or before d (FRED lags the live tape by days)."""
    import bisect
    i = bisect.bisect_right(keys, d) - 1
    return m[keys[i]] if i >= 0 else None

for r in rows:
    for n in (10, 30): r[f'v{n}'] = realized_vol(ds, px, as_of=r['d'], lookback=n)
    r['vix'] = prior(vix, vd, r['d'])
for r in rr:
    for n in (10, 30): r[f'v{n}'] = realized_vol(qd, qqq, as_of=r['d0'], lookback=n)
    r['vix'] = prior(vix, vd, r['d0'])

# ---- coverage, stated before any result -------------------------------------
cov = [r for r in rows if r['vix'] is not None]
print(f"proxy rows {len(rows)} ({rows[0]['d']}..{rows[-1]['d']}); "
      f"with VIX {len(cov)} ({cov[0]['d']}..{cov[-1]['d']})")
hold_all = era(rows, *HOLDOUT); hold_vix = [r for r in hold_all if r['vix'] is not None]
print(f"HOLDOUT {HOLDOUT[0]}..{HOLDOUT[1]}: {len(hold_all)} days, only {len(hold_vix)} "
      f"({100*len(hold_vix)/len(hold_all):.0f}%) have VIX -- the 2000-02 bear is INVISIBLE to any VIX variant")
rrv = [r for r in rr if r['vix'] is not None]
print(f"real weekly rows {len(rr)}; with VIX {len(rrv)}\n")

# ---- variance risk premium ---------------------------------------------------
srch = [r for r in era(cov, *SEARCH) if r['v30']]
k = sum(r['v30'] for r in srch) / sum(r['vix'] for r in srch)
prem = sum(r['vix'] - r['v30'] for r in srch) / len(srch)
print(f"variance risk premium, SEARCH era only: mean(VIX)-mean(vol30) = {prem*100:+.2f} vol points; "
      f"scale k = mean(v30)/mean(VIX) = {k:.4f}  (fitted on search only, applied everywhere)\n")

# ---- descriptive correlation -------------------------------------------------
def corr(a, b):
    n = len(a); ma, mb = sum(a)/n, sum(b)/n
    va = sum((x-ma)**2 for x in a); vb = sum((x-mb)**2 for x in b)
    return sum((x-ma)*(y-mb) for x, y in zip(a, b)) / math.sqrt(va*vb) if va and vb else float('nan')

live = mk(W)                      # the live design, live estimator
rets, _ = run(cov, live)
vx  = [r['vix'] for r in cov]
v30 = [r['v30'] or 0 for r in cov]
dvx = [vx[i]-vx[i-1] for i in range(1, len(vx))]
print("DESCRIPTIVE -- strategy vs VIX (2008+, live design):")
print(f"  corr(daily return, VIX level)        {corr(rets, vx):+.3f}")
print(f"  corr(daily return, 1-day VIX change) {corr(rets[1:], dvx):+.3f}")
print(f"  corr(VIX level, realized vol30)      {corr(vx, v30):+.3f}")
print(f"  corr(1d VIX change, next-day return) {corr(dvx[:-1], rets[2:]):+.3f}   <- predictive, if any\n")

# ---- estimator family, all on the SAME 2008+ rows -----------------------------
def mkv(keys, scale_vix=False, blend=None, vtf=vt):
    def fn(r):
        w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
        if f < 1: w = tuple(x*f for x in w[:4]) + (1 - f*sum(w[:4]),)
        vs = []
        for kk in keys:
            x = r.get(kk)
            if x is None: continue
            vs.append(x*k if (kk == 'vix' and scale_vix) else x)
        if blend is not None and r.get('v30') is not None and r.get('vix') is not None:
            return vtf(w, blend*r['v30'] + (1-blend)*r['vix']*k)
        return vtf(w, max(vs) if vs else r['vol'])
    return fn

FAM = [
    ('vol30 (ref)',        (('v30',),        False, None)),
    ('max(10,30) LIVE',    (('v10','v30'),   False, None)),
    ('VIX raw',            (('vix',),        False, None)),
    ('VIX scaled',         (('vix',),        True,  None)),
    ('max(v30, VIXraw)',   (('v30','vix'),   False, None)),
    ('max(v30, VIXsc)',    (('v30','vix'),   True,  None)),
    ('max(v10,v30,VIXsc)', (('v10','v30','vix'), True, None)),
    ('50/50 v30+VIXsc',    (('v30',),        True,  0.5)),
]
base = evaluate(cov, mkv(('v30',)))
print("ALL VARIANTS ON 2008+ ROWS ONLY (S = Sharpe 2015-11+, H = Sharpe 2008-2015)")
print(f"{'estimator':<20} proxy CAGR/Sharpe/MDD     S / H      expo   beta   real weekly")
for lab, (keys, sc, bl) in FAM:
    ev = evaluate(cov, mkv(keys, sc, bl))
    e  = RF.eval_real(rrv, mkv(keys, sc, bl, RF.vt))
    k1, c1 = exposure_control(cov, ev['risky'])
    tb = beta_of(cov, mkv(keys, sc, bl)); k2, c2 = beta_matched_control(cov, mkv(('v30',)), tb)
    both = ' BOTH' if ev['s_sharpe'] > base['s_sharpe'] and ev['h_sharpe'] > base['h_sharpe'] else ''
    print(f"  {lab:<20} {ev['cagr']*100:5.2f}/{ev['sharpe']:.3f}/{ev['mdd']*100:6.1f}  "
          f"{ev['s_sharpe']:.3f}/{ev['h_sharpe']:.3f}  {c1['sharpe']:.3f}  {c2['sharpe']:.3f}  "
          f"{e['cagr']*100:5.2f}/{e['sharpe']:.3f}/{e['mdd']*100:6.1f}  expo {ev['risky']*100:.1f}%{both}")
