"""Three VIX overlays the repo has NOT tested, asked by the owner 2026-09-08:

  A. VIX daily PERCENTAGE change as a de-lever trigger
  B. VIX LEVEL cutoff line
  C. DMA on VIX -- VIX vs its own moving average, and that average's slope

WHY THESE ARE NEW. substate_research_deltas.py tested VIX POINT deltas (1d/5d)
and substate_research.py tested a VIX>25 cutoff, but BOTH used them as
SUBSTATE SPLITTERS inside a state, on weekly rows, under MIN_N sample floors
that made several cells untestable. Neither ran as a GLOBAL overlay on the
whole design. And the 0-for-6 search's DMA slope+acceleration rule was on
QQQ's OWN moving average, never on VIX's. So all three are open questions.

METHOD, same discipline as vix_estimator_test.py:
  - VIXCLS starts 2008, so EVERY variant including the live baseline runs on
    the same 2008+ rows. Figures are NOT comparable to full-window numbers.
  - Each overlay multiplies the four risky legs by g<=1 AFTER the live vol
    target and trim, routing freed weight to cash. So every one of them is a
    CASH GATE, and the exposure-matched control is the right control:
    de-levering raises Sharpe by itself, and the question is whether the
    TIMING beats simply holding less. exposure_control() answers exactly that.
  - Only info known at the decision close is used (VIX at d0).
  - Many candidates are swept, so the count is reported and nothing is called
    significant off this screen alone; a survivor goes to the BLOCK bootstrap
    (day-shuffled permutation overstates significance -- block_bootstrap.py).
"""
import sys, math, bisect
sys.path.insert(0, 'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from downturn_review import exposure_control
from state import realized_vol, extension_scale
from vix_estimator_test import load_vix

vix = load_vix(); vd = sorted(vix)
vixv = [vix[d] for d in vd]
def vat(d):
    i = bisect.bisect_right(vd, d) - 1
    return (i, vix[vd[i]]) if i >= 0 else (None, None)

def vsma(i, n):
    if i is None or i + 1 < n: return None
    return sum(vixv[i - n + 1:i + 1]) / n

WINS = (10, 20, 50, 100, 200)
def attach(rlist, key):
    for r in rlist:
        i, x = vat(r[key])
        r['vix'] = x; r['vixi'] = i
        r['vixchg'] = (x / vixv[i - 1] - 1) if (i is not None and i >= 1) else None
        for n in WINS:
            m = vsma(i, n)
            r[f'vs{n}'] = m
            r[f'vsl{n}'] = (m - vsma(i - 1, n)) if (m is not None and vsma(i - 1, n) is not None) else None
attach(rows, 'd')
for r in rr:
    for n in (10, 30): r[f'v{n}'] = realized_vol(qd, qqq, as_of=r['d0'], lookback=n)
    r['vol_live'] = r['v30'] if (r['v10'] is None or r['v30'] is None) else max(r['v10'], r['v30'])
attach(rr, 'd0')

cov  = [r for r in rows if r['vix'] is not None and r['vs200'] is not None]
covr = [r for r in rr   if r['vix'] is not None and r['vs200'] is not None]
print(f"proxy rows on VIX+200dma: {len(cov)} ({cov[0]['d']}..{cov[-1]['d']}); real weekly: {len(covr)}\n")

def mkg(rule, vtf=vt, volkey='vol_live'):
    """live design (trim -> vol target on max(10,30)) then the overlay's gate."""
    def fn(r):
        w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
        if f < 1: w = tuple(x * f for x in w[:4]) + (1 - f * sum(w[:4]),)
        w = vtf(w, r.get(volkey) or r['vol'])
        g = rule(r)
        if g < 1.0:
            w = tuple(x * g for x in w[:4]) + (1 - g * sum(w[:4]),)
        return w
    return fn

LIVE = mkg(lambda r: 1.0)
base  = evaluate(cov, LIVE)
baser = RF.eval_real(covr, mkg(lambda r: 1.0, RF.vt, 'vol_live'))
print(f"{'LIVE baseline (2008+)':<30} {base['cagr']*100:5.2f}/{base['sharpe']:.3f}/{base['mdd']*100:6.1f}  "
      f"S {base['s_sharpe']:.3f} H {base['h_sharpe']:.3f}  expo {base['risky']*100:.1f}%  "
      f"real {baser['cagr']*100:5.2f}/{baser['sharpe']:.3f}/{baser['mdd']*100:6.1f}\n")

CANDS = []
for X in (0.05, 0.10, 0.15, 0.20, 0.25):
    for f in (0.0, 0.5):
        CANDS.append((f"A pct chg >{X*100:.0f}% -> x{f}",
                      lambda r, X=X, f=f: f if (r['vixchg'] is not None and r['vixchg'] > X) else 1.0))
for T in (18, 20, 22, 25, 28, 30, 35):
    for f in (0.0, 0.5):
        CANDS.append((f"B VIX >{T} -> x{f}",
                      lambda r, T=T, f=f: f if r['vix'] * 100 > T else 1.0))
for n in WINS:
    for f in (0.0, 0.5):
        CANDS.append((f"C VIX>SMA{n} -> x{f}",
                      lambda r, n=n, f=f: f if r[f'vs{n}'] is not None and r['vix'] > r[f'vs{n}'] else 1.0))
for n in (20, 50, 100):
    for f in (0.0, 0.5):
        CANDS.append((f"C SMA{n} rising -> x{f}",
                      lambda r, n=n, f=f: f if (r[f'vsl{n}'] is not None and r[f'vsl{n}'] > 0) else 1.0))

print(f"{len(CANDS)} candidates swept. 'BOTH' = beats live in BOTH eras; 'CTL' = also beats its exposure-matched control.\n")
print(f"{'candidate':<28} CAGR/Sharpe/MDD      S / H       expo   ctlSh  real Sharpe  flags")
winners = []
for lab, rule in CANDS:
    ev = evaluate(cov, mkg(rule))
    e  = RF.eval_real(covr, mkg(rule, RF.vt, 'vol_live'))
    k1, c1 = exposure_control(cov, ev['risky'])
    both = ev['s_sharpe'] > base['s_sharpe'] and ev['h_sharpe'] > base['h_sharpe']
    ctl  = ev['sharpe'] > c1['sharpe'] and c1.get('exp_matched', False)
    flags = ('BOTH ' if both else '') + ('CTL' if ctl else '')
    if both: winners.append((lab, ev, e, c1))
    print(f"  {lab:<28} {ev['cagr']*100:5.2f}/{ev['sharpe']:.3f}/{ev['mdd']*100:6.1f}  "
          f"{ev['s_sharpe']:.3f}/{ev['h_sharpe']:.3f}  {ev['risky']*100:5.1f}%  {c1['sharpe']:.3f}  "
          f"{e['sharpe']:.3f}  {flags}")
print(f"\n{len(winners)} of {len(CANDS)} beat live in BOTH eras.")
for lab, ev, e, c1 in winners:
    print(f"   {lab}: proxy {ev['sharpe']:.3f} vs live {base['sharpe']:.3f}, "
          f"exposure-matched control {c1['sharpe']:.3f} (matched={c1.get('exp_matched')}), "
          f"real {e['sharpe']:.3f} vs {baser['sharpe']:.3f}")
