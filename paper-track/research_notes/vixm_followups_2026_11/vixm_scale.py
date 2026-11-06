"""Owner 2026-11-04: would scaling the VIXM share (instead of a fixed 75% of the cash leg) help?
Live design (A 20/80 from 30 Oct, D ladder, D gate, vol target max10_30, VIXM off in ungated D2),
real ETFs 2015-11..2026-10, 2bp one-way. The latch/stress/fade decide WHEN (unchanged); each
variant only changes HOW MUCH of the cash leg is VIXM on allowed days. Research only."""
import csv, os, sys
import numpy as np
HERE = '/home/user/Robinhood-stock/paper-track'; sys.path.insert(0, HERE)
import monte_carlo as MC, state as S, vol_curve as VC
MC.DATA = '/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad/data_ext'
S.A_BASE_FROM_SESSION = ('2026-10-30', (0.20, 0.80))
LIVE = dict(MC.LIVE, name='live', a_base=(0.20, 0.80), vol='max10_30')
OUT = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vixm_scale.log'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); OUT.write(s + '\n'); OUT.flush()

p = MC.load_panel('proxy'); dates = p['dates']
sig = MC.signals((100*np.cumprod(1+p['qqq']))[None], (100*np.cumprod(1+p['ew']))[None])
pr = MC.load_panel('real'); off = dates.index(pr['dates'][0])
sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items()}
rd = pr['dates']
try:
    vix, vsrc = VC.history('VIX'); vix3m, _ = VC.history('VIX3M')
except Exception:
    f = lambda fn, c: {r['observation_date']: float(r[c]) for r in csv.DictReader(open(os.path.join(MC.DATA, fn))) if r[c] not in ('', '.')}
    vix, vix3m, vsrc = f('vixcls_full.csv', 'VIXCLS'), f('vxvcls.csv', 'VXVCLS'), 'FRED local'
vol30 = {d: (None if np.isnan(v) else float(v)) for d, v in zip(rd, sr['vol'][0])}
VX = S.vixm_series(rd, vix, vix3m, vol30)
allowed = np.array([bool(VX.get(d, {}).get('allowed')) for d in rd])
eff = MC._eff(sr, LIVE)[0]
allowed &= ~((eff == 3) & ~sr['gate'][0].astype(bool) & (sr['zone'][0] == 2))   # off in ungated D2
g = lambda k: np.array([VX.get(d, {}).get(k) or np.nan for d in rd], float)
VIX, RATIO, VOL = g('vix'), g('ratio'), g('vol')
HI = g('vix_high')
# days into the current allowed spell
age = np.zeros(len(rd)); 
for i in range(len(rd)):
    age[i] = (age[i-1] + 1) if (allowed[i] and i and allowed[i-1]) else (1 if allowed[i] else 0)
vm = {r['d']: float(r['c']) for r in csv.DictReader(open(os.path.join(MC.DATA, 'vixm_daily.csv')))}
vr = MC._rets(vm, rd); vr[0] = 0.0
w5 = MC.target_weights(sr, LIVE); key0 = MC.regime_key(sr, LIVE)
s0 = next(i for i, d in enumerate(rd) if d >= '2015-11-02'); days = rd[s0+1:]
L6 = np.stack([pr['core'], pr['tqqq'], pr['qld'], pr['xlu'], vr, pr['cash']], -1)[None]

def run(share):
    """share: array of VIXM fraction of the cash leg on each day (used only where allowed)."""
    sh = np.where(allowed, np.clip(np.nan_to_num(share, nan=0.75), 0, 1), 0.0)
    v = w5[0, :, 4] * sh
    w6 = np.concatenate([w5[..., :4], v[None, :, None], (w5[0, :, 4] - v)[None, :, None]], -1)
    r, tr = MC.run_strategy(w6, key0 + allowed[None].astype(int)*100000, L6, s0)
    return r[0], tr[0] / ((len(rd)-1-s0)/252)

def prof(r):
    nav = np.cumprod(1+r); dd = nav/np.maximum.accumulate(nav) - 1
    return (nav[-1]**(252/len(r))-1, r.mean()*252/(r.std(ddof=1)*252**.5), dd.min())
mid = days.index(next(d for d in days if d >= '2021-03-01'))
def row(lab, r, t, base=None):
    c, s, m = prof(r); c1, s1, _ = prof(r[:mid]); c2, s2, _ = prof(r[mid:])
    ex = '' if base is None else f"{(c-base)*100:+7.2f}"
    log(f"  {lab:<50}{c*100:6.1f}%{ex:>8}{s:7.3f}{m*100:7.1f}%{s1:8.3f}{s2:8.3f}{t:7.0f}")
    return c

one = np.ones(len(rd))
V = {}
V['fixed 75% (LIVE)'] = 0.75*one
for x in (0.25, 0.50, 1.00): V[f'fixed {x*100:.0f}%'] = x*one
# by QQQ 30d vol: more when stress is deeper
for lo, hi in ((0.50, 1.0), (0.25, 1.0), (0.50, 0.90)):
    V[f'vol ramp {lo*100:.0f}%@20% -> {hi*100:.0f}%@30%'] = lo + (hi-lo)*np.clip((VOL-0.20)/0.10, 0, 1)
V['vol ramp 1.0@20% -> 0.5@30% (inverse)'] = 1.0 - 0.5*np.clip((VOL-0.20)/0.10, 0, 1)
# by VIX level: cheaper insurance when VIX is low
V['VIX ramp 100%@<=14 -> 50%@>=22'] = 1.0 - 0.5*np.clip((VIX-14)/8, 0, 1)
V['VIX ramp 50%@<=14 -> 100%@>=22 (inverse)'] = 0.5 + 0.5*np.clip((VIX-14)/8, 0, 1)
# by term structure: VIX/VIX3M ratio near 1 = curve flat, spike nearer
V['ratio ramp 50%@<=0.80 -> 100%@>=0.95'] = 0.5 + 0.5*np.clip((RATIO-0.80)/0.15, 0, 1)
V['ratio ramp 100%@<=0.80 -> 50%@>=0.95 (inverse)'] = 1.0 - 0.5*np.clip((RATIO-0.80)/0.15, 0, 1)
# by spell age: decay drag grows the longer a spike fails to come
V['age decay 100% -> 50% over 20 sessions'] = 1.0 - 0.5*np.clip((age-1)/20, 0, 1)
V['age decay 75% -> 25% over 20 sessions'] = 0.75 - 0.5*np.clip((age-1)/20, 0, 1)
# combined vol x VIX
V['vol ramp 50->100% x VIX ramp 100->50% (product, /0.75)'] = np.clip((0.5+0.5*np.clip((VOL-0.20)/0.10,0,1))*(1-0.5*np.clip((VIX-14)/8,0,1))/0.75, 0, 1)
r_no, t_no = run(0*one)

log('='*118)
log(f"VIXM share scaling -- live design, real ETFs {days[0]}..{days[-1]}, 2bp; VIX source {vsrc}; VIXM allowed {allowed[s0:].mean()*100:.1f}% of sessions")
log("  'when' is unchanged (latch, stress, fade, D2 off); only the share of the cash leg on allowed days varies")
log('='*118)
log(f"  {'variant (share of cash leg on allowed days)':<50}{'CAGR':>7}{'vs live':>8}{'Sharpe':>7}{'maxDD':>8}{'Sh 1st':>8}{'Sh 2nd':>8}{'tr/yr':>7}")
base = None
res = {}
for k, sh in V.items():
    r, t = run(sh); c = row(k, r, t, base)
    if base is None: base = c
    res[k] = r
row('no VIXM', r_no, t_no, base)
a = allowed[s0:]
log(f"\n  halves split at 2021-03-01; allowed-day stats: VOL median {np.nanmedian(VOL[s0:][a])*100:.1f}%, VIX median {np.nanmedian(VIX[s0:][a]):.1f}, ratio median {np.nanmedian(RATIO[s0:][a]):.3f}")
# bootstrap: best variant vs live (block bootstrap of daily differences)
rng = np.random.default_rng(7)
rl = res['fixed 75% (LIVE)']
log(f"\n  block bootstrap (20-day blocks, 4000 draws) of Sharpe difference vs LIVE; P(variant not better):")
n = len(rl); B = 20
for k, r in res.items():
    if k.startswith('fixed 75'): continue
    cnt = 0
    for _ in range(4000):
        idx = np.concatenate([np.arange(s, s+B) for s in rng.integers(0, n-B, n//B+1)])[:n]
        a1, a2 = r[idx], rl[idx]
        cnt += (a1.mean()/a1.std() - a2.mean()/a2.std()) <= 0
    log(f"    {k:<55}{cnt/4000:6.2f}")

# fairness: a variant that just holds MORE VIXM on average beats 75% because the sleeve paid overall.
# Compare each to a fixed share with the SAME average VIXM weight (dollar-weighted on allowed days).
log(f"\n  matched-average check: each variant vs a FIXED share equal to its own average share on allowed days")
log(f"  {'variant':<55}{'avg share':>10}{'CAGR':>8}{'fixed same avg':>15}{'edge':>8}{'Sharpe edge':>12}{'ex Aug24 edge':>14}")
aug = np.array([d[:7] != '2024-08' for d in days])
for k, sh in V.items():
    shc = np.clip(np.nan_to_num(sh, nan=0.75), 0, 1)
    m = allowed & (w5[0, :, 4] > 0)
    avg = float(np.sum(shc[m]*w5[0, m, 4]) / np.sum(w5[0, m, 4]))
    r = res[k]; rf, _ = run(avg*one)
    c, s, _ = prof(r); cf, sf, _ = prof(rf)
    ce, _, _ = prof(r[aug]); cfe, _, _ = prof(rf[aug])
    log(f"  {k:<55}{avg*100:9.0f}%{c*100:7.1f}%{cf*100:14.1f}%{(c-cf)*100:+8.2f}{s-sf:+12.3f}{(ce-cfe)*100:+14.2f}")
