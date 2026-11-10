"""State B (reclaim) row tests on effective-B sessions. Research only; base = 11 Nov live design (hv design + deep-E + VIX-panic QQQ legs)."""
import csv, os, sys, math
import numpy as np
HERE = '/home/user/Robinhood-stock/paper-track'; sys.path.insert(0, HERE)
import monte_carlo as MC, state as S, vol_curve as VC
SP = '/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad'
MC.DATA = SP + '/data_ext'
S.A_BASE_FROM_SESSION = ('2026-11-06', (0.40, 0.60))
LIVE = dict(MC.LIVE, name='live', a_base=(0.40, 0.60), vol='max10_30')
OUT = open(SP + '/hv/bx_test.log', 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); OUT.write(s + '\n'); OUT.flush()

p = MC.load_panel('proxy'); dates = p['dates']
qfull = 100*np.cumprod(1+p['qqq'])
sig = MC.signals(qfull[None], (100*np.cumprod(1+p['ew']))[None])
pr = MC.load_panel('real'); off = dates.index(pr['dates'][0])
sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items()}
rd = pr['dates']
vix, vsrc = VC.history('VIX'); vix3m, _ = VC.history('VIX3M')
vol30 = {d: (None if np.isnan(v) else float(v)) for d, v in zip(rd, sr['vol'][0])}
VX = S.vixm_series(rd, vix, vix3m, vol30)
eff_r = MC._eff(sr, LIVE)[0]
allowed = np.array([bool(VX.get(d, {}).get('allowed')) for d in rd])
allowed &= ~((eff_r == 3) & ~sr['gate'][0].astype(bool) & (sr['zone'][0] == 2))
_px = {r['d']: float(r['c']) for r in csv.DictReader(open(os.path.join(MC.DATA, 'vixm_daily.csv')))}
vixm_r = MC._rets(_px, rd); vixm_r[0] = 0.0

# 50d/200d spread of QQQ (full proxy series; real is the tail)
sma50 = MC._sma(qfull[None], 50)[0]; sma200 = MC._sma(qfull[None], 200)[0]
SPREAD_P = sma50/sma200 - 1; SPREAD_R = SPREAD_P[off:]

PAN = {}
for name, sg, pn, ds in (('real', sr, pr, rd), ('proxy', sig, p, dates)):
    e = MC._eff(sg, LIVE)[0]; g = np.nan_to_num(sg['gaps'][200][0])
    deep = ((e == 4) & (g <= -0.05)).astype(float)*0.5
    VIXa = np.array([vix.get(d, np.nan) for d in ds]); on = False; pan = np.zeros(len(ds))
    for i, v in enumerate(VIXa):
        if not np.isnan(v):
            if on and v < 25: on = False
            elif not on and v >= 30: on = True
        pan[i] = 0.25 if on else 0.0
    # spell age within effective B (proxy-full timeline; real = tail)
    eb = (e == 1); age = np.zeros(len(ds), int)
    for i in range(len(ds)): age[i] = (age[i-1]+1 if i and eb[i-1] else 1) if eb[i] else 0
    PAN[name] = dict(sg=sg, pn=pn, ds=ds, e=e, deep=deep, pan=pan, age=age, eb=eb,
                     macroB=(sg['macro'][0] == 1), spread=(SPREAD_R if name == 'real' else SPREAD_P),
                     d0=('2015-11-02' if name == 'real' else '2001-01-02'), cut=('2021-03-01' if name == 'real' else '2015-11-01'))
# age for real must come from the proxy timeline (B spells that began before 2015-11)
PAN['real']['age'] = PAN['proxy']['age'][off:]

def mult_all(sg):
    v = np.fmax(sg['vol'], np.where(np.isnan(sg['vol']), np.nan, sg['vol10']))
    vt = LIVE.get('vol_target', S.VOL_TARGET_PA)
    return np.where(np.isnan(v) | (v <= 0), 1.0, np.minimum(1.0, vt/np.where(v > 0, v, 1)))[0]

def runner(P, mask=None, row=None, lagged=False):
    """base legs + (optional) replace the row on mask sessions (w5 modified before cash legs)."""
    sg, pn, ds = P['sg'], P['pn'], P['ds']; s0 = next(i for i, d in enumerate(ds) if d >= P['d0'])
    w5 = MC.target_weights(sg, LIVE); key = MC.regime_key(sg, LIVE).astype(np.int64)
    if mask is not None:
        m = np.asarray(mask, bool)
        if lagged: m = np.concatenate([[False], m[:-1]]) & P['eb']
        mu = mult_all(sg)
        w5 = w5.copy()
        for i in range(4): w5[0, m, i] = row[i]*mu[m]
        w5[0, m, 4] = 1 - w5[0, m, :4].sum(-1)
        key = key + m[None].astype(np.int64)*10**9
    cash = w5[0, :, 4].copy()
    legs = [pn['core'], pn['tqqq'], pn['qld'], pn['xlu']]; W = [w5[0, :, i] for i in range(4)]
    real = pn is pr
    if real:
        allow = allowed; legs.append(vixm_r); W.append(np.where(allow, cash*S.VIXM_CASH_SHARE, 0.0)); key = key + allow[None].astype(np.int64)*100000
    used = W[4] if real else np.zeros_like(cash)
    for j, (rr, sh) in enumerate(((pn['qqq'], P['deep']), (pn['qqq'], P['pan']))):
        x = np.minimum(cash*sh, cash-used); used = used + x
        legs.append(rr); W.append(x); key = key + (sh[None] > 0).astype(np.int64)*(10**(6+j))
    legs.append(pn['cash']); W.append(cash-used)
    w = np.stack(W, -1)[None]; L = np.stack(legs, -1)[None]
    r, tr = MC.run_strategy(w, key, L, s0)
    return r[0], ds[s0+1:], s0

def prof(r):
    nav = np.cumprod(1+r); dd = nav/np.maximum.accumulate(nav)-1
    return nav[-1]**(252/len(r))-1, r.mean()*252/(r.std(ddof=1)*252**.5), dd.min()
def halves(r, ds, cut):
    i = next(k for k, d in enumerate(ds) if d >= cut); return prof(r[:i])[1], prof(r[i:])[1]
def ex2020(r, ds):
    k = np.array([not d.startswith('2020') for d in ds]); return prof(r[k])
def nspells(m):
    m = np.asarray(m, bool); return int((m & ~np.concatenate([[False], m[:-1]])).sum())

BASE = {}
for k, P in PAN.items():
    r, ds, s0 = runner(P); BASE[k] = dict(r=r, ds=ds, s0=s0, prof=prof(r), h=halves(r, ds, P['cut']), x20=ex2020(r, ds))
    e = P['e']; mB = P['macroB']
    log(f"{k}: base {BASE[k]['prof'][0]*100:.1f}% / Sharpe {BASE[k]['prof'][1]:.3f} / maxDD {BASE[k]['prof'][2]*100:.1f}%  {ds[0]}..{ds[-1]} n={len(r)}; "
        f"halves {BASE[k]['h'][0]:.3f}/{BASE[k]['h'][1]:.3f}; ex-2020 {BASE[k]['x20'][0]*100:.1f}%/{BASE[k]['x20'][1]:.3f}")
    sl = slice(s0, None)
    log(f"   effective-B sessions {P['eb'][sl].mean()*100:.1f}% of sessions, {nspells(P['eb'][sl])} spells; macro-B sessions {mB[sl].mean()*100:.1f}%; "
        f"fast overlay overrides B (macro-B sessions holding A weights): {(mB[sl] & (e[sl]==0)).sum()}/{mB[sl].sum()} = {(mB[sl] & (e[sl]==0)).sum()/mB[sl].sum()*100:.1f}%")

def evaluate(lab, mfun, row, show=True):
    out = {}
    for k, P in PAN.items():
        m = mfun(P); B = BASE[k]
        r, ds, s0 = runner(P, m, row); rl, _, _ = runner(P, m, row, lagged=True)
        c, s, dd = prof(r); h = halves(r, ds, P['cut']); x = ex2020(r, ds); cl, sl_, _ = prof(rl)
        out[k] = dict(r=r, c=c, s=s, dd=dd, dc=c-B['prof'][0], ds=s-B['prof'][1], h=h, x=x, lag=(cl, sl_), share=m[s0:].mean(), sp=nspells(m[s0:]))
    if show:
        for k in ('real', 'proxy'):
            o = out[k]; B = BASE[k]
            log(f"  {lab:<44}{k:>6} CAGR {o['c']*100:5.1f}% ({o['dc']*100:+5.2f}) Sh {o['s']:.3f} ({o['ds']:+.3f}) DD {o['dd']*100:6.1f}% | halves {o['h'][0]:.3f}/{o['h'][1]:.3f} (base {B['h'][0]:.3f}/{B['h'][1]:.3f})"
                f" | ex2020 {o['x'][0]*100:5.1f}% ({(o['x'][0]-B['x20'][0])*100:+5.2f}) Sh {o['x'][1]:.3f} ({o['x'][1]-B['x20'][1]:+.3f}) | lag1 {o['lag'][0]*100:5.1f}% ({(o['lag'][0]-B['prof'][0])*100:+5.2f}) Sh {o['lag'][1]:.3f} ({o['lag'][1]-B['prof'][1]:+.3f})"
                f" | rows held {o['share']*100:4.1f}% spells {o['sp']}")
    return out

allB = lambda P: P['eb']
ROWS = {'a 100% SPMO': (1, 0, 0, 0, 0), 'b 50% SPMO/50% cash': (.5, 0, 0, 0, .5), 'c 100% cash': (0, 0, 0, 0, 1),
        'd 75% SPMO/25% QLD': (.75, 0, .25, 0, 0), 'e 50/50 SPMO/TQQQ': (.5, .5, 0, 0, 0)}
log('\n' + '='*150 + '\n(a)-(e) whole effective-B (eff==1) replaced. Base row 75% SPMO / 25% TQQQ (vol-scaled). Deltas vs base. ex2020 = 2020 sessions dropped (delta vs base ex-2020). lag1 = row change applied one session late.\n' + '='*150)
RES = {}
for lab, row in ROWS.items(): RES[lab] = evaluate(lab, allB, row)
log('\n(f) split by 50d/200d spread (QQQ SMA50/SMA200-1, negative in B). near = spread > -x ; deep = spread <= -x')
SPL = {}
for x in (0.01, 0.02):
    for part, f in (('near', lambda P, x=x: P['eb'] & (P['spread'] > -x)), ('deep', lambda P, x=x: P['eb'] & (P['spread'] <= -x))):
        for rl in ('a 100% SPMO', 'b 50% SPMO/50% cash', 'c 100% cash'):
            lab = f"f {part} {x*100:.0f}% -> {rl[:1]}"; SPL[lab] = evaluate(lab, f, ROWS[rl]); RES[lab] = SPL[lab]
log('\n(g) B by age (session # within an effective-B spell, spells measured on the full proxy timeline)')
for n in (5, 10):
    for part, f in (('first', lambda P, n=n: P['eb'] & (P['age'] <= n)), ('later', lambda P, n=n: P['eb'] & (P['age'] > n))):
        for rl in ('a 100% SPMO', 'b 50% SPMO/50% cash', 'c 100% cash'):
            lab = f"g {part} {n} -> {rl[:1]}"; RES[lab] = evaluate(lab, f, ROWS[rl])

# ---- pick best two: help on both panels (dSharpe>0 and dCAGR>0 on both), rank by min dSharpe
cand = [(min(o['real']['ds'], o['proxy']['ds']), l) for l, o in RES.items()
        if all(o[k]['ds'] > 0 and o[k]['dc'] > 0 for k in o)]
cand.sort(reverse=True)
log('\nVariants improving BOTH Sharpe and CAGR on BOTH panels (ranked by min dSharpe): ' + ('; '.join(f"{l} ({v:+.3f})" for v, l in cand) or 'NONE'))
cand2 = [(min(o['real']['ds'], o['proxy']['ds']), l) for l, o in RES.items() if all(o[k]['ds'] > 0 for k in o) and l not in [c[1] for c in cand]]
cand2.sort(reverse=True)
log('Variants improving Sharpe only on both panels: ' + ('; '.join(f"{l} ({v:+.3f})" for v, l in cand2) or 'NONE'))
best = [l for _, l in cand[:2]] if cand else []
if not best: best = [l for _, l in cand2[:2]]
log('Deep-dive on: ' + (', '.join(best) if best else 'none (nothing helps on both panels)'))

# ---- deep dive
MASKS = {}
def mk_from_label(l):
    if l[0] in 'abcde': return allB, ROWS[[k for k in ROWS if k[0] == l[0]][0]]
    parts = l.split()
    rowlab = [k for k in ROWS if k[0] == parts[-1]][0]
    if parts[0] == 'f':
        x = float(parts[2][:-1])/100; return ((lambda P, x=x: P['eb'] & (P['spread'] > -x)) if parts[1] == 'near' else (lambda P, x=x: P['eb'] & (P['spread'] <= -x))), ROWS[rowlab]
    n = int(parts[2]); return ((lambda P, n=n: P['eb'] & (P['age'] <= n)) if parts[1] == 'first' else (lambda P, n=n: P['eb'] & (P['age'] > n))), ROWS[rowlab]

def sharpe_paired(r, b, idx): 
    rr = r[idx]; bb = b[idx]
    return (rr.mean(1)/rr.std(1, ddof=1) - bb.mean(1)/bb.std(1, ddof=1))*math.sqrt(252)
rng = np.random.default_rng(20261110)
for l in best:
    mf, row = mk_from_label(l); o = RES[l]
    log('\n' + '#'*140 + f"\nDEEP DIVE: {l}  row {row}\n" + '#'*140)
    for k, P in PAN.items():
        r = o[k]['r']; b = BASE[k]['r']; n = len(r)
        # block bootstrap 20-day blocks, 3000 draws, paired
        nb = math.ceil(n/20); d = []
        for _ in range(6):
            st = rng.integers(0, n-19, size=(500, nb)); idx = (st[:, :, None] + np.arange(20)).reshape(500, -1)[:, :n]
            d.append(sharpe_paired(r, b, idx))
        d = np.concatenate(d)
        log(f"  [{k}] block bootstrap (20d, 3000 draws): P(Sharpe not better than base) = {(d <= 0).mean():.3f}; mean dSharpe {d.mean():+.3f}; 5-95% [{np.percentile(d,5):+.3f}, {np.percentile(d,95):+.3f}]")
        # placebo: same-spell-structure mask circularly shifted to random offset, restricted to A/B/C states
        m0 = mf(P); T = len(m0); eok = np.isin(P['e'], (0, 1, 2)); cnt = int(m0.sum()); dS = []; dC = []
        for _ in range(300):
            sh = int(rng.integers(250, T-250)); m = np.roll(m0, sh) & eok
            rp, _, _ = runner(P, m, row); c_, s_, _ = prof(rp); dC.append(c_-BASE[k]['prof'][0]); dS.append(s_-BASE[k]['prof'][1])
        dS = np.array(dS); dC = np.array(dC)
        log(f"  [{k}] placebo (mask rolled by random 250+ session offset, kept to A/B/C sessions, 300 draws): actual dSharpe {o[k]['ds']:+.3f} vs placebo mean {dS.mean():+.3f} sd {dS.std():.3f}; "
            f"share of placebos >= actual dSharpe {(dS >= o[k]['ds']).mean():.3f}; actual dCAGR {o[k]['dc']*100:+.2f} vs placebo mean {dC.mean()*100:+.2f}, share >= {(dC >= o[k]['dc']).mean():.3f}")
    # neighbour grid: interpolate row between base B row and candidate row; thresholds for subset rules
    log("  neighbour grid -- row interpolation lam (0 = live B row, 1 = candidate row, >1 extrapolated and clipped at >=0):")
    B_ROW = np.array((.75, .25, 0, 0, 0))
    for lam in (0.0, 0.25, 0.5, 0.75, 1.0, 1.25):
        rw = np.clip(B_ROW + lam*(np.array(row)-B_ROW), 0, None); rw[4] = 0; rw[4] = 1-rw[:4].sum(); rw = np.clip(rw, 0, None)
        rw = tuple(rw[:4]) + (max(0, 1-sum(rw[:4])),)
        ev = evaluate('', mf, rw, show=False)
        log(f"    lam {lam:4.2f} row {tuple(round(float(x),3) for x in rw)}: " + ' | '.join(f"{k} CAGR {ev[k]['c']*100:5.1f}% ({ev[k]['dc']*100:+5.2f}) Sh {ev[k]['s']:.3f} ({ev[k]['ds']:+.3f}) DD {ev[k]['dd']*100:.1f}%" for k in ev))
    parts = l.split()
    if parts[0] in 'fg':
        log("  neighbour grid -- threshold:")
        if parts[0] == 'f':
            for x in (0.005, 0.01, 0.015, 0.02, 0.03, 0.05):
                f_ = (lambda P, x=x: P['eb'] & (P['spread'] > -x)) if parts[1] == 'near' else (lambda P, x=x: P['eb'] & (P['spread'] <= -x))
                ev = evaluate('', f_, row, show=False)
                log(f"    spread threshold {x*100:.1f}%: " + ' | '.join(f"{k} CAGR {ev[k]['c']*100:5.1f}% ({ev[k]['dc']*100:+5.2f}) Sh {ev[k]['s']:.3f} ({ev[k]['ds']:+.3f}) held {ev[k]['share']*100:.1f}%" for k in ev))
        else:
            for n in (3, 5, 7, 10, 15, 20, 30):
                f_ = (lambda P, n=n: P['eb'] & (P['age'] <= n)) if parts[1] == 'first' else (lambda P, n=n: P['eb'] & (P['age'] > n))
                ev = evaluate('', f_, row, show=False)
                log(f"    age cut {n}: " + ' | '.join(f"{k} CAGR {ev[k]['c']*100:5.1f}% ({ev[k]['dc']*100:+5.2f}) Sh {ev[k]['s']:.3f} ({ev[k]['ds']:+.3f}) held {ev[k]['share']*100:.1f}%" for k in ev))
    # proxy crisis windows
    P = PAN['proxy']; ds = BASE['proxy']['ds']; rv = o['proxy']['r']; bv = BASE['proxy']['r']
    for nm, a, z in (('2001-2002', '2001-01-01', '2002-12-31'), ('2008', '2008-01-01', '2008-12-31')):
        k_ = np.array([a <= d <= z for d in ds]); eb = P['eb'][BASE['proxy']['s0']+1:][k_]
        def win(r): 
            nav = np.cumprod(1+r[k_]); return nav[-1]-1, (nav/np.maximum.accumulate(nav)-1).min()
        wv, wb = win(rv), win(bv)
        log(f"  [proxy {nm}] variant return {wv[0]*100:+.1f}% maxDD {wv[1]*100:.1f}% | base return {wb[0]*100:+.1f}% maxDD {wb[1]*100:.1f}% | effective-B sessions in window {int(eb.sum())}/{k_.sum()}; variant-mask sessions {int(mf(P)[BASE['proxy']['s0']+1:][k_].sum())}")
log('\ndone')
