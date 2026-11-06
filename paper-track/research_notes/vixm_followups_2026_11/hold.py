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
OUT = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hold.log'), 'w')
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


ENTRY, EXITR, FADE = S.VIXM_ENTRY_VIX, S.VIXM_EXIT_RATIO, S.VIXM_FADE
def series(vin, vout, confirm=1):
    """state.vixm_series with a stress band: stress turns ON at vol >= vin (after `confirm` closes in a
    row), OFF only when vol < vout. vin == vout, confirm 1 == live."""
    on = killed = st = False; hi = None; run_in = 0; out = {}
    for d in rd:
        v, v3 = vix.get(d), vix3m.get(d)
        if v is None or v3 is None or v3 <= 0: continue
        ratio = v / v3
        if not on and v < ENTRY and ratio <= EXITR: on, killed, hi = True, False, None
        elif on and ratio > EXITR: on = False
        rv = vol30.get(d)
        if rv is None: st = False; run_in = 0
        elif st: st = rv >= vout
        else:
            run_in = run_in + 1 if rv >= vin else 0
            st = run_in >= confirm
        if not st: killed, hi = False, None; 
        allowed_ = on and not killed and st
        if allowed_:
            hi = v if hi is None else max(hi, v)
            if v <= hi * (1 - FADE): killed, allowed_ = True, False
        out[d] = allowed_
    return np.array([bool(out.get(d)) for d in rd])
assert (series(0.20, 0.20) == np.array([bool(VX.get(d, {}).get('allowed')) for d in rd])).all(), 'replica != state.vixm_series'
d2 = ((eff == 3) & ~sr['gate'][0].astype(bool) & (sr['zone'][0] == 2))
def run_al(al):
    al = al & ~d2
    v = np.where(al, w5[0, :, 4] * 0.75, 0.0)
    w6 = np.concatenate([w5[..., :4], v[None, :, None], (w5[0, :, 4] - v)[None, :, None]], -1)
    r, tr = MC.run_strategy(w6, key0 + al[None].astype(int)*100000, L6, s0)
    a = al[s0:]; flips = int(np.sum(a[1:] != a[:-1]))
    return r[0], tr[0]/((len(rd)-1-s0)/252), flips, a

a = (series(0.20,0.20) & ~d2)[s0:]
sp=[]; j=0
while j<len(a):
    if a[j]:
        k=j
        while k<len(a) and a[k]: k+=1
        sp.append((rd[s0+j],k-j)); j=k
    else: j+=1
L=np.array([n for _,n in sp])
log(f"spells {len(L)}, mean {L.mean():.1f}, median {np.median(L):.0f}, min {L.min()}, max {L.max()} sessions; total {L.sum()}")
log("distribution: " + ', '.join(f"{lo}-{hi}: {((L>=lo)&(L<=hi)).sum()}" for lo,hi in ((1,2),(3,5),(6,10),(11,20),(21,40),(41,999))))
log(f"weighted by days held (avg session sits in a spell of) {np.sum(L*L)/L.sum():.1f}")
log(' '.join(f"{d}:{n}" for d,n in sp))
