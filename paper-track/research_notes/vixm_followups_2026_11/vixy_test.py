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
OUT = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vixy_test.log'), 'w')
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
def run(name, share):
    rr = inst[name][0]
    v = np.where(allowed, w5[0, :, 4]*share, 0.0)
    w6 = np.concatenate([w5[..., :4], v[None, :, None], (w5[0, :, 4]-v)[None, :, None]], -1)
    L = np.stack([pr['core'], pr['tqqq'], pr['qld'], pr['xlu'], rr, pr['cash']], -1)[None]
    r, tr = MC.run_strategy(w6, key, L, s0)
    return r[0], tr[0]/((len(rd)-1-s0)/252), v
def prof(r):
    nav = np.cumprod(1+r); dd = nav/np.maximum.accumulate(nav)-1
    return nav[-1]**(252/len(r))-1, r.mean()*252/(r.std(ddof=1)*252**.5), dd.min()
mid = days.index(next(d for d in days if d >= '2021-03-01'))
aug = np.array([d[:7] != '2024-08' for d in days])
log('='*124)
log(f"VIXY vs VIXM in the cash sleeve -- live design, real ETFs {days[0]}..{days[-1]}, 2bp; same latch/stress/fade/D2-off timing; "
    f"sleeve allowed {allowed[s0:].mean()*100:.1f}% of sessions")
log('  Robinhood split-adjusted daily closes for both (VIXY: many reverse splits)')
log('='*124)
for name in ('VIXM', 'VIXY'):
    c = np.cumprod(1+inst[name][0][s0+1:]); 
    a = allowed[s0:-1]
    log(f"  {name}: buy & hold {c[-1]**(252/len(c))*100-100:+.1f}%/yr; mean daily return on sleeve days {inst[name][0][s0+1:][a].mean()*1e4:+.1f}bp, "
        f"off-sleeve days {inst[name][0][s0+1:][~a].mean()*1e4:+.1f}bp")
rv, rx = inst['VIXM'][0][s0+1:], inst['VIXY'][0][s0+1:]
ok = ~np.isnan(rv) & ~np.isnan(rx)
log(f"  daily beta of VIXY to VIXM {np.polyfit(rv[ok], rx[ok], 1)[0]:.2f} (all days)")
log(f"\n  {'sleeve':<22}{'CAGR':>7}{'vs live':>8}{'Sharpe':>7}{'maxDD':>8}{'Sh 1st':>8}{'Sh 2nd':>8}{'ex Aug24':>9}{'tr/yr':>7}{'trade/ADV med':>14}{'max':>7}")
base = None; out = {}
for name, shares in (('VIXM', (0.25, 0.50, 0.75, 1.00)), ('VIXY', (0.15, 0.25, 0.35, 0.50, 0.75, 1.00))):
    for sh in shares:
        r, t, v = run(name, sh)
        c, s, m = prof(r); _, s1, _ = prof(r[:mid]); _, s2, _ = prof(r[mid:]); ce, _, _ = prof(r[aug])
        if base is None and name == 'VIXM' and sh == 0.75: pass
        out[(name, sh)] = (c, ce)
        # trade size vs that day's dollar volume, at today's $581k account
        dv = inst[name][1]; dw = np.abs(np.diff(v[s0:]))
        idx = np.where(dw > 0.01)[0] + s0 + 1
        ratio = dw[idx-s0-1]*581_000/dv[idx]
        ratio = ratio[~np.isnan(ratio)]
        log(f"  {name+' '+format(sh*100,'.0f')+'% of cash':<22}{c*100:6.1f}%{'':>8}{s:7.3f}{m*100:7.1f}%{s1:8.3f}{s2:8.3f}{ce*100:8.1f}%{t:7.0f}"
            f"{np.median(ratio)*100:13.1f}%{ratio.max()*100:6.0f}%")
r0, t0, _ = run('VIXM', 0.0); c, s, m = prof(r0); _, s1, _ = prof(r0[:mid]); _, s2, _ = prof(r0[mid:]); ce, _, _ = prof(r0[aug])
log(f"  {'no sleeve (all BOXX)':<22}{c*100:6.1f}%{'':>8}{s:7.3f}{m*100:7.1f}%{s1:8.3f}{s2:8.3f}{ce*100:8.1f}%{t0:7.0f}")
bl = out[('VIXM', 0.75)][0]
log(f"\n  vs live (VIXM 75%): " + ', '.join(f"{n} {s*100:.0f}% {(c-bl)*100:+.2f}" for (n, s), (c, _) in out.items()))
# spells
log(f"\n  per sleeve spell: VIXY 35% vs VIXM 75% (log gain vs BOXX, pts of book)")
rA, _, vA = run('VIXM', 0.75); rB, _, vB = run('VIXY', 0.35); rN = r0
j = 0; vw = vA[s0:s0+len(rA)]; rows = []
while j < len(vw):
    if vw[j] > 0:
        k = j
        while k < len(vw) and vw[k] > 0: k += 1
        a = np.sum(np.log1p(rA[j:k])) - np.sum(np.log1p(rN[j:k])); b = np.sum(np.log1p(rB[j:k])) - np.sum(np.log1p(rN[j:k]))
        rows.append((days[j], k-j, a, b)); j = k
    else: j += 1
log(f"  spells {len(rows)}; VIXM won {sum(a>0 for _,_,a,_ in rows)}, VIXY won {sum(b>0 for *_,b in rows)}; VIXY better than VIXM in {sum(b>a for *_,a,b in rows)}")
for d, n, a, b in sorted(rows, key=lambda x: -abs(x[2])-abs(x[3]))[:10]:
    log(f"    {d} {n:3d}d  VIXM {a*100:+6.2f}  VIXY {b*100:+6.2f}")
