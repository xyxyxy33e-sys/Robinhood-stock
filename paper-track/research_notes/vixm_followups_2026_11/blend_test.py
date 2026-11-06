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
OUT = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'blend_test.log'), 'w')
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


D = os.path.dirname(os.path.abspath(__file__))
def load(fn):
    px, vol = {}, {}
    for r in csv.DictReader(open(os.path.join(D, fn))):
        px[r['d']] = float(r['c']); vol[r['d']] = float(r['v']) * float(r['c'])
    return px, vol
inst = {}
for name, fn in (('VIXM', 'vixm_rh_daily.csv'), ('VIXY', 'vixy_daily.csv')):
    px, dv = load(fn); rr = MC._rets(px, rd); rr[0] = 0.0
    inst[name] = (rr, np.array([dv.get(d, np.nan) for d in rd]))
key = key0 + allowed[None].astype(int)*100000

RM, RY = inst['VIXM'][0], inst['VIXY'][0]
cashw = w5[0, :, 4]
def run2(m, y):
    """m, y: arrays (or scalars) = VIXM / VIXY share of the cash leg on allowed days (sum capped at 1)."""
    m = np.broadcast_to(np.asarray(m, float), cashw.shape); y = np.broadcast_to(np.asarray(y, float), cashw.shape)
    tot = np.maximum(m + y, 1e-12); scale = np.minimum(1.0, 1.0 / tot)
    vm = np.where(allowed, cashw*m*scale, 0.0); vy = np.where(allowed, cashw*y*scale, 0.0)
    w7 = np.concatenate([w5[..., :4], vm[None, :, None], vy[None, :, None], (cashw-vm-vy)[None, :, None]], -1)
    L = np.stack([pr['core'], pr['tqqq'], pr['qld'], pr['xlu'], RM, RY, pr['cash']], -1)[None]
    r, tr = MC.run_strategy(w7, key, L, s0)
    return r[0], tr[0]/((len(rd)-1-s0)/252)
def prof(r):
    nav = np.cumprod(1+r); dd = nav/np.maximum.accumulate(nav)-1
    return nav[-1]**(252/len(r))-1, r.mean()*252/(r.std(ddof=1)*252**.5), dd.min()
mid = days.index(next(d for d in days if d >= '2021-03-01'))
aug = np.array([d[:7] != '2024-08' for d in days])
res = {}
def row(lab, m, y, H=None):
    r, t = run2(m, y); c, s, dd = prof(r); _, s1, _ = prof(r[:mid]); _, s2, _ = prof(r[mid:]); ce, _, _ = prof(r[aug])
    res[lab] = r
    base = prof(res['VIXM 75 (LIVE)'])[0] if 'VIXM 75 (LIVE)' in res else c
    hs = '' if H is None else f"{H:.2f}"
    log(f"  {lab:<44}{hs:>6}{c*100:7.1f}%{(c-base)*100:+8.2f}{s:7.3f}{dd*100:7.1f}%{s1:8.3f}{s2:8.3f}{ce*100:8.1f}%{t:6.0f}")
H = lambda m, y: m + 2.0*y      # hedge in VIXM-units (VIXY beta 2.0 to VIXM)
log('='*120)
log(f"VIXM + VIXY blends and steps -- live design, real ETFs {days[0]}..{days[-1]}, 2bp; same sleeve timing (on {allowed[s0:].mean()*100:.1f}% of sessions)")
log("  shares are % of the cash leg on sleeve days; H = hedge in VIXM-units (VIXM share + 2 x VIXY share); live H = 0.75")
log('='*120)
hdr = f"  {'variant':<44}{'H':>6}{'CAGR':>8}{'vs live':>8}{'Sharpe':>7}{'maxDD':>8}{'Sh 1st':>8}{'Sh 2nd':>8}{'exAug24':>9}{'tr/yr':>6}"
log("\n  A. same hedge as live (H 0.75), different mix"); log(hdr)
row('VIXM 75 (LIVE)', 0.75, 0, 0.75)
for m, y in ((0.50, 0.125), (0.375, 0.1875), (0.25, 0.25), (0.0, 0.375)):
    row(f"VIXM {m*100:.1f} + VIXY {y*100:.1f}", m, y, H(m, y))
log("\n  B. hedge size ('leverage'), 50/50 hedge mix (half the H from each)"); log(hdr)
for h in (0.50, 0.75, 1.00, 1.25, 1.50, 2.00):
    m, y = h/2, h/4
    row(f"VIXM {m*100:.1f} + VIXY {y*100:.1f}", m, y, h)
log("  same sizes, VIXY only / VIXM only:")
for h in (1.00, 1.50, 2.00):
    row(f"VIXY {h/2*100:.1f}", 0, h/2, h)
row("VIXM 100", 1.0, 0, 1.0)
# steps
log("\n  C. steps within a sleeve spell (H 0.75 throughout unless stated)"); log(hdr)
age = np.zeros(len(rd))
for i in range(1, len(rd)):
    age[i] = age[i-1]+1 if (allowed[i] and allowed[i-1]) else (1 if allowed[i] else 0)
for n in (3, 5, 10):
    early = age <= n
    row(f"VIXY 37.5 first {n} days, then VIXM 75", np.where(early, 0, 0.75), np.where(early, 0.375, 0), 0.75)
    row(f"VIXM 75 first {n} days, then VIXY 37.5", np.where(early, 0.75, 0), np.where(early, 0, 0.375), 0.75)
# step by term structure: closer to inversion -> more VIXY
for lo in (0.90, 0.95):
    near = RATIO >= lo
    row(f"VIXM 75; VIXY 37.5 when VIX/VIX3M >= {lo}", np.where(near, 0, 0.75), np.where(near, 0.375, 0), 0.75)
# step by stress: deeper stress -> more VIXY
for v in (0.25, 0.30):
    deep = VOL >= v
    row(f"VIXM 75; VIXY 37.5 when QQQ 30d vol >= {v*100:.0f}%", np.where(deep, 0, 0.75), np.where(deep, 0.375, 0), 0.75)
# step-UP in size (add VIXY on top) when the spike is building
for lo in (0.90, 0.95):
    near = RATIO >= lo
    row(f"VIXM 75 + add VIXY 12.5 when ratio >= {lo} (H->1.0)", 0.75, np.where(near, 0.125, 0), None)
    row(f"VIXM 75 + add VIXY 25 when ratio >= {lo} (H->1.25)", 0.75, np.where(near, 0.25, 0), None)
# bootstrap for the best few vs live
rng = np.random.default_rng(11); rl = res['VIXM 75 (LIVE)']; n = len(rl); B = 20
sc = {k: prof(r)[1] - prof(rl)[1] for k, r in res.items() if k != 'VIXM 75 (LIVE)'}
log("\n  block bootstrap (20-day blocks, 3000 draws), top 8 by Sharpe gain: P(not better than live)")
for k in sorted(sc, key=lambda k: -sc[k])[:8]:
    r = res[k]; cnt = 0
    for _ in range(3000):
        idx = np.concatenate([np.arange(st, st+B) for st in rng.integers(0, n-B, n//B+1)])[:n]
        a1, a2 = r[idx], rl[idx]; cnt += (a1.mean()/a1.std() - a2.mean()/a2.std()) <= 0
    log(f"    {k:<55} Sharpe {sc[k]:+.3f}   P {cnt/3000:.2f}")
