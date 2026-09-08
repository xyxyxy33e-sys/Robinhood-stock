"""Everything from the VIX tests, rerun on VXN -- the MATCHED volatility index.

Owner, 2026-09-08: "try everything with vxn instead". Correct instinct, and
the earlier VIX work says why in its own output. VIX is S&P 500 implied vol
while this entire design -- classifier, vol target, satellite -- is on QQQ.
The symptom was a NEGATIVE variance risk premium (mean VIX below mean QQQ
realized vol30), the opposite of the textbook, because QQQ realizes more vol
than the S&P implies. VXN is the Nasdaq-100 index and is the right instrument.

It is also a far better dataset here: VXNCLS starts 2001-02-02 vs VIXCLS's
2008-01-02. The 2000-2015 holdout goes from 51% covered to ~96% covered, and
the dot-com bust -- invisible to every VIX variant -- is now largely in view.

Run: PART 1 estimator input (does implied vol beat realized in the overlay),
PART 2 the three overlay families (% change / cutoff / DMA), 40 candidates,
PART 3 the discriminator + block bootstrap + leave-one-regime-out on whatever
survives. Same discipline throughout: every variant including the baseline is
evaluated on the SAME VXN-covered rows, VXN is tested raw AND rescaled by a
search-era-only constant so a Sharpe difference cannot be confounded with
simply holding less risk, and survivors face the BLOCK bootstrap rather than a
day-shuffled permutation.
"""
import sys, math, csv, bisect
sys.path.insert(0, 'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from downturn_review import exposure_control
from improvement_search import SEARCH, HOLDOUT, era
from improvement_search_r2 import beta_of, beta_matched_control
from state import realized_vol, extension_scale

def load_fred(path, col):
    out, last = {}, None
    for row in csv.DictReader(open(path)):
        s = row[col].strip()
        if s: last = float(s) / 100.0
        if last is not None: out[row['observation_date']] = last
    return out

VXN = load_fred('data/vxncls.csv', 'VXNCLS')
xd = sorted(VXN); xv = [VXN[d] for d in xd]
def xat(d):
    i = bisect.bisect_right(xd, d) - 1
    return (i, VXN[xd[i]]) if i >= 0 else (None, None)
def sm(seq, i, n):
    if i is None or i + 1 < n: return None
    return sum(seq[i - n + 1:i + 1]) / n

rv = {d: realized_vol(ds, px, as_of=d, lookback=30) for d in ds}
rvd = [d for d in ds if rv[d] is not None]; rvv = [rv[d] for d in rvd]
rvi = {d: i for i, d in enumerate(rvd)}
WINS = (10, 20, 50, 100, 200)

def attach(rlist, key):
    for r in rlist:
        for n in (10, 30):
            r[f'v{n}'] = realized_vol(ds, px, as_of=r[key], lookback=n) if key == 'd' \
                         else realized_vol(qd, qqq, as_of=r[key], lookback=n)
        r['vol_live'] = r['v30'] if (r['v10'] is None or r['v30'] is None) else max(r['v10'], r['v30'])
        i, x = xat(r[key]); r['x'] = x; r['xi'] = i
        r['xchg'] = (x / xv[i-1] - 1) if (i is not None and i >= 1) else None
        for n in WINS:
            m = sm(xv, i, n); r[f'xs{n}'] = m
            p = sm(xv, i-1, n) if i else None
            r[f'xsl{n}'] = (m - p) if (m is not None and p is not None) else None
        j = rvi.get(r[key]); r['rv'] = rvv[j] if j is not None else None
        for n in (20, 50):
            m = sm(rvv, j, n); r[f'rs{n}'] = m
            p = sm(rvv, j-1, n) if j else None
            r[f'rsl{n}'] = (m - p) if (m is not None and p is not None) else None
attach(rows, 'd'); attach(rr, 'd0')

cov  = [r for r in rows if r['x'] is not None]
covr = [r for r in rr   if r['x'] is not None]
hall = era(rows, *HOLDOUT); hvx = [r for r in hall if r['x'] is not None]
print(f"VXN {len(xd)} days {xd[0]}..{xd[-1]}")
print(f"proxy rows {len(rows)} ({rows[0]['d']}..{rows[-1]['d']}); with VXN {len(cov)} ({cov[0]['d']}..)")
print(f"HOLDOUT coverage {len(hvx)}/{len(hall)} = {100*len(hvx)/len(hall):.0f}%  (VIX was 51%)")
print(f"real weekly {len(rr)} -> {len(covr)}\n")

srch = [r for r in era(cov, *SEARCH) if r['v30']]
k = sum(r['v30'] for r in srch) / sum(r['x'] for r in srch)
prem = sum(r['x'] - r['v30'] for r in srch) / len(srch)
print(f"variance risk premium (SEARCH era): mean(VXN)-mean(QQQvol30) = {prem*100:+.2f} vol pts, "
      f"k = {k:.4f}   [VIX gave -1.34 pts, k=1.0726 -- the mismatch]\n")

# ---------------- PART 1: VXN as the vol-target INPUT -------------------------
def mke(keys, scale=False, blend=None, vtf=vt):
    def fn(r):
        w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
        if f < 1: w = tuple(a*f for a in w[:4]) + (1 - f*sum(w[:4]),)
        vs = []
        for kk in keys:
            a = r.get(kk)
            if a is None: continue
            vs.append(a*k if (kk == 'x' and scale) else a)
        if blend is not None and r.get('v30') and r.get('x'):
            return vtf(w, blend*r['v30'] + (1-blend)*r['x']*k)
        return vtf(w, max(vs) if vs else r['vol'])
    return fn
FAM1 = [('vol30 (ref)',(('v30',),False,None)), ('max(10,30) LIVE',(('v10','v30'),False,None)),
        ('VXN raw',(('x',),False,None)), ('VXN scaled',(('x',),True,None)),
        ('max(v30,VXNraw)',(('v30','x'),False,None)), ('max(v30,VXNsc)',(('v30','x'),True,None)),
        ('max(v10,v30,VXNsc)',(('v10','v30','x'),True,None)), ('50/50 v30+VXNsc',(('v30',),True,0.5))]
b1 = evaluate(cov, mke(('v10','v30')))
print("PART 1 -- VXN as the vol-target INPUT (all on VXN-covered rows)")
print(f"{'estimator':<20} CAGR/Sharpe/MDD      S / H       expo   real weekly")
for lab,(ky,sc,bl) in FAM1:
    ev = evaluate(cov, mke(ky,sc,bl)); e = RF.eval_real(covr, mke(ky,sc,bl,RF.vt))
    fl = ' BOTH' if ev['s_sharpe']>b1['s_sharpe'] and ev['h_sharpe']>b1['h_sharpe'] else ''
    print(f"  {lab:<20} {ev['cagr']*100:5.2f}/{ev['sharpe']:.3f}/{ev['mdd']*100:6.1f}  "
          f"{ev['s_sharpe']:.3f}/{ev['h_sharpe']:.3f}  {ev['risky']*100:5.1f}%  "
          f"{e['cagr']*100:5.2f}/{e['sharpe']:.3f}/{e['mdd']*100:6.1f}{fl}")

# ---------------- PART 2: the three overlay families -------------------------
def mkg(rule, vtf=vt):
    def fn(r):
        w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
        if f < 1: w = tuple(a*f for a in w[:4]) + (1 - f*sum(w[:4]),)
        w = vtf(w, r.get('vol_live') or r['vol'])
        g = rule(r)
        return w if g >= 1.0 else tuple(a*g for a in w[:4]) + (1 - g*sum(w[:4]),)
    return fn
C = []
for X in (0.05,0.10,0.15,0.20,0.25):
    for f in (0.0,0.5): C.append((f"A pct chg >{X*100:.0f}% x{f}", lambda r,X=X,f=f: f if (r['xchg'] is not None and r['xchg']>X) else 1.0))
for T in (18,20,22,25,28,30,35):
    for f in (0.0,0.5): C.append((f"B VXN >{T} x{f}", lambda r,T=T,f=f: f if r['x']*100>T else 1.0))
for n in WINS:
    for f in (0.0,0.5): C.append((f"C VXN>SMA{n} x{f}", lambda r,n=n,f=f: f if r[f'xs{n}'] is not None and r['x']>r[f'xs{n}'] else 1.0))
for n in (20,50,100):
    for f in (0.0,0.5): C.append((f"C SMA{n} rising x{f}", lambda r,n=n,f=f: f if (r[f'xsl{n}'] is not None and r[f'xsl{n}']>0) else 1.0))
cov2 = [r for r in cov if r['xs200'] is not None]
covr2 = [r for r in covr if r['xs200'] is not None]
b2 = evaluate(cov2, mkg(lambda r: 1.0)); b2r = RF.eval_real(covr2, mkg(lambda r: 1.0, RF.vt))
print(f"\nPART 2 -- overlays on the live design. {len(C)} candidates, {len(cov2)} rows from {cov2[0]['d']}")
print(f"  {'LIVE baseline':<26} {b2['cagr']*100:5.2f}/{b2['sharpe']:.3f}/{b2['mdd']*100:6.1f}  "
      f"{b2['s_sharpe']:.3f}/{b2['h_sharpe']:.3f}  {b2['risky']*100:5.1f}%  real {b2r['sharpe']:.3f}")
win = []
for lab, rule in C:
    ev = evaluate(cov2, mkg(rule)); e = RF.eval_real(covr2, mkg(rule, RF.vt))
    both = ev['s_sharpe'] > b2['s_sharpe'] and ev['h_sharpe'] > b2['h_sharpe']
    if both:
        k1, c1 = exposure_control(cov2, ev['risky'])
        win.append((lab, ev, e, c1))
        print(f"  {lab:<26} {ev['cagr']*100:5.2f}/{ev['sharpe']:.3f}/{ev['mdd']*100:6.1f}  "
              f"{ev['s_sharpe']:.3f}/{ev['h_sharpe']:.3f}  {ev['risky']*100:5.1f}%  ctl {c1['sharpe']:.3f} "
              f"(m={c1.get('exp_matched')})  real {e['sharpe']:.3f}  BOTH")
print(f"\n{len(win)} of {len(C)} beat live in BOTH eras.")
import json
json.dump([w[0] for w in win], open('/tmp/vxn_winners.json','w'))
