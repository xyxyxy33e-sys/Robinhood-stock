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
OUT = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stress_band.log'), 'w')
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
mid = days.index(next(d for d in days if d >= '2021-03-01'))
aug = np.array([d[:7] != '2024-08' for d in days])
yrs = (len(rd)-1-s0)/252
log('='*124)
log(f"VIXM stress-floor buffer -- live design, real ETFs {days[0]}..{days[-1]}, 2bp, VIXM 75% of cash; latch/fade/D2-off unchanged")
log("  stress ON at QQQ plain 30d vol >= IN (after K closes), OFF only below OUT. Live = 20/20, K 1. 'flips' = sleeve on/off changes")
log('='*124)
log(f"  {'rule':<30}{'CAGR':>7}{'vs live':>8}{'Sharpe':>7}{'maxDD':>8}{'Sh 1st':>8}{'Sh 2nd':>8}{'exAug24':>9}{'on %':>6}{'flips':>6}{'/yr':>5}{'flips<=2d':>10}")
base = None
for vin, vout, k in ((0.20,0.20,1),(0.20,0.195,1),(0.20,0.19,1),(0.20,0.185,1),(0.20,0.18,1),(0.20,0.17,1),(0.205,0.19,1),(0.21,0.19,1),(0.21,0.20,1),(0.22,0.20,1),(0.20,0.20,2),(0.20,0.20,3),(0.20,0.19,2),(0.19,0.19,1),(0.18,0.18,1)):
    r, t, f, a = run_al(series(vin, vout, k))
    nav = np.cumprod(1+r); dd = (nav/np.maximum.accumulate(nav)-1).min()
    c = nav[-1]**(252/len(r))-1; sh = r.mean()*252/(r.std(ddof=1)*252**.5)
    p = lambda x: x.mean()*252/(x.std(ddof=1)*252**.5)
    ce = np.prod(1+r[aug])**(252/aug.sum())-1
    # short spells (<=2 sessions)
    sp = []; j = 0
    while j < len(a):
        if a[j]:
            k2 = j
            while k2 < len(a) and a[k2]: k2 += 1
            sp.append(k2-j); j = k2
        else: j += 1
    if base is None: base = c
    lab = f"in {vin*100:.1f}% / out {vout*100:.1f}%" + (f", {k} closes" if k > 1 else '')
    log(f"  {lab:<30}{c*100:6.1f}%{(c-base)*100:+8.2f}{sh:7.3f}{dd*100:7.1f}%{p(r[:mid]):8.3f}{p(r[mid:]):8.3f}{ce*100:8.1f}%{a.mean()*100:5.1f}%{f:6d}{f/yrs:5.1f}{sum(x<=2 for x in sp):10d}")
