"""State-C row re-test on the CURRENT live design (hv_test + deep-E QQQ + VIX-panic QQQ + corrected VIXM). Research only."""
import csv, os, sys
import numpy as np
HERE = '/home/user/Robinhood-stock/paper-track'; sys.path.insert(0, HERE)
import monte_carlo as MC, state as S, vol_curve as VC
SP = '/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad'
MC.DATA = SP + '/data_ext'
S.A_BASE_FROM_SESSION = ('2026-11-06', (0.40, 0.60))
LIVE = dict(MC.LIVE, name='live', a_base=(0.40, 0.60), vol='max10_30')
OUT = open(SP + '/hv/cx_test.log', 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); OUT.write(s + '\n'); OUT.flush()

p = MC.load_panel('proxy'); dates = p['dates']
sig = MC.signals((100*np.cumprod(1+p['qqq']))[None], (100*np.cumprod(1+p['ew']))[None])
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

def panic(ds):
    v = np.array([vix.get(d, np.nan) for d in ds]); on = False; out = np.zeros(len(ds))
    for i in range(len(ds)):
        if not np.isnan(v[i]):
            if on and v[i] < 25: on = False
            elif not on and v[i] >= 30: on = True
        out[i] = 0.25 if on else 0.0
    return out

PAN = {}
for nm, sg, pn in (('real', sr, pr), ('proxy', sig, p)):
    e = MC._eff(sg, LIVE)[0]; g = np.nan_to_num(sg['gaps'][200][0])
    deep = ((e == 4) & (g <= -0.05)).astype(float) * 0.5
    PAN[nm] = dict(sg=sg, pn=pn, d0='2015-11-02' if nm == 'real' else '2001-01-02',
                   cut='2021-03-01' if nm == 'real' else '2015-11-01',
                   base_ex=[(pn['qqq'], deep), (pn['qqq'], panic(pn['dates']))], eff=e, g200=g)

def runner2(nm, w5, wq=None, keyx=None, lag_ex=None):
    P = PAN[nm]; sg, pn = P['sg'], P['pn']; real = nm == 'real'
    ds = pn['dates']; s0 = next(i for i, d in enumerate(ds) if d >= P['d0'])
    key = MC.regime_key(sg, LIVE)
    cash = w5[0, :, 4].copy()
    legs = [pn['core'], pn['tqqq'], pn['qld'], pn['xlu']]; W = [w5[0, :, i] for i in range(4)]
    if real:
        legs.append(vixm_r); W.append(np.where(allowed, cash*S.VIXM_CASH_SHARE, 0.0)); key = key + allowed[None].astype(int)*100000
    used = W[4] if real else np.zeros_like(cash)
    for j, (rr, sh) in enumerate(P['base_ex']):
        sh = np.clip(np.nan_to_num(sh), 0, 1)
        x = np.minimum(cash*sh, cash - used); used = used + x
        legs.append(rr); W.append(x); key = key + (sh[None] > 0).astype(int) * (10**(6+j))
    if wq is not None:
        legs.append(pn['qqq']); W.append(wq); key = key + (wq[None] > 0).astype(int) * 10**8
    if keyx is not None: key = key + keyx[None].astype(int) * 10**9
    legs.append(pn['cash']); W.append(cash - used)
    w = np.stack(W, -1)[None]; L = np.stack(legs, -1)[None]
    r, tr = MC.run_strategy(w, key, L, s0)
    return r[0], ds[s0+1:], s0

def prof(r):
    nav = np.cumprod(1+r); dd = nav/np.maximum.accumulate(nav)-1
    return nav[-1]**(252/len(r))-1, r.mean()*252/(r.std(ddof=1)*252**.5), dd.min()
def halves(r, ds, cut):
    i = next(k for k, d in enumerate(ds) if d >= cut); return prof(r[:i])[1], prof(r[i:])[1]

def build(nm, spec):
    """spec: list of (mask, (core,qqq,qld,tqqq,cash) fractions of the row's core weight). Returns w5, wq, keyx."""
    P = PAN[nm]; w5 = MC.target_weights(P['sg'], LIVE).copy(); wq = np.zeros(w5.shape[1]); kx = np.zeros(w5.shape[1], int)
    pan = nm == 'proxy'
    for m, (fc, fq, fl, ft, fh) in spec:
        c = w5[0, :, 0].copy(); m = m.astype(bool)
        if nm == 'proxy' and fq > 0:        # proxy core IS QQQ: the QQQ share stays in the core leg
            fc, fq = fc + fq, 0.0
        w5[0, m, 0] = (c*fc)[m]; wq[m] = (c*fq)[m]
        w5[0, m, 1] = w5[0, m, 1] + (c*ft)[m]; w5[0, m, 2] = w5[0, m, 2] + (c*fl)[m]
        w5[0, m, 4] = 1.0 - w5[0, m, :4].sum(-1) - wq[m]
        kx = kx + m.astype(int)*0   # key term set below
    keyx = np.zeros(w5.shape[1], int)
    for j, (m, fr) in enumerate(spec): keyx = keyx + m.astype(int) * (j + 1) * 1
    return w5, wq, keyx

def metrics(nm, r, ds):
    P = PAN[nm]; c, s, m = prof(r); a, b = halves(r, ds, P['cut'])
    k = np.array([d[:4] != '2020' for d in ds]); c2, s2, _ = prof(r[k])
    return dict(c=c, s=s, m=m, a=a, b=b, c2=c2, s2=s2)

def lagmask(m):
    m = m.astype(bool); o = m.copy(); o[1:] = m[1:] & m[:-1]; o[0] = False; return o

def run_spec(nm, spec, lag=False):
    if lag: spec = [(lagmask(m), fr) for m, fr in spec]
    w5, wq, kx = build(nm, spec)
    r, ds, s0 = runner2(nm, w5, wq, kx); return r, ds

# ------------------------------------------------------------------ sessions
CM = {}
for nm in PAN:
    P = PAN[nm]; e = P['eff']; sg = P['sg']; macro = sg['macro'][0]
    w5 = MC.target_weights(sg, LIVE); Cm = (e == 2)
    row = w5[0][Cm]
    assert np.allclose(row[:, 1:4], 0) and np.allclose(row[:, 0] + row[:, 4], 1), 'C row not core+cash'
    CM[nm] = Cm
    vt = np.fmax(sg['vol'][0], sg['vol10'][0])
    P['vt'] = np.nan_to_num(vt)
    P['g'] = P['g200']

def deep(nm, t): return CM[nm] & (PAN[nm]['g'] <= -t)
def shallow(nm, t): return CM[nm] & (PAN[nm]['g'] > -t)
def hivol(nm, t): return CM[nm] & (PAN[nm]['vt'] > t)

BASE = (1, 0, 0, 0, 0)
VAR = {
 'a  100% QQQ':               lambda nm: [(CM[nm], (0, 1, 0, 0, 0))],
 'b  75% core / 25% QLD':     lambda nm: [(CM[nm], (.75, 0, .25, 0, 0))],
 'c  50% core / 50% QLD':     lambda nm: [(CM[nm], (.5, 0, .5, 0, 0))],
 'd  75% core / 25% TQQQ':    lambda nm: [(CM[nm], (.75, 0, 0, .25, 0))],
 'e  50% core / 50% cash':    lambda nm: [(CM[nm], (.5, 0, 0, 0, 0))],
}
for T in (5, 10):
    t = T/100
    VAR[f'f  deep>={T}%: 100% QQQ']        = (lambda t: lambda nm: [(deep(nm, t), (0, 1, 0, 0, 0))])(t)
    VAR[f'f  deep>={T}%: 50% core/50% QLD'] = (lambda t: lambda nm: [(deep(nm, t), (.5, 0, .5, 0, 0))])(t)
    VAR[f'f  deep>={T}%: 75% core/25% QLD'] = (lambda t: lambda nm: [(deep(nm, t), (.75, 0, .25, 0, 0))])(t)
    VAR[f'f  deep>={T}%: 50% core/50% cash'] = (lambda t: lambda nm: [(deep(nm, t), (.5, 0, 0, 0, 0))])(t)
    VAR[f'f  shallow(<{T}%): 50% core/50% cash'] = (lambda t: lambda nm: [(shallow(nm, t), (.5, 0, 0, 0, 0))])(t)
    VAR[f'f  deep>={T}% 50/50 QLD + shallow 50% cash'] = (lambda t: lambda nm: [(deep(nm, t), (.5, 0, .5, 0, 0)), (shallow(nm, t), (.5, 0, 0, 0, 0))])(t)
    VAR[f'f  deep>={T}% 100% QQQ + shallow 50% cash'] = (lambda t: lambda nm: [(deep(nm, t), (0, 1, 0, 0, 0)), (shallow(nm, t), (.5, 0, 0, 0, 0))])(t)
for fc, lab in ((.75, '75% core'), (.5, '50% core'), (0.0, 'all cash')):
    VAR[f'g  vol>30%: {lab}'] = (lambda fc: lambda nm: [(hivol(nm, .30), (fc, 0, 0, 0, 0))])(fc)

log('='*140)
log(f"C-row re-test, live design as of 2026-11-10 (A 40/60, D ladder+gate, vol max10_30 target {S.VOL_TARGET_PA}, VIXM sleeve real only, deep-E QQQ, VIX-panic QQQ), 2bp; VIX src {vsrc}")
log("Mask = EFFECTIVE C (MC._eff == 2: macro C and the fast 20/100 overlay not A); only those sessions are altered; modified C row = core-weight x fractions (vol scaling kept).")
log("Cash freed in C also feeds the VIXM sleeve (real) and the panic-QQQ leg exactly as in live. No-VIXM proxy. Proxy core IS QQQ: variant (a)/QQQ legs collapse to the base core (identical to base).")
log('='*140)

res = {}; base = {}
for nm in PAN:
    P = PAN[nm]; ds_all = P['pn']['dates']
    w5 = MC.target_weights(P['sg'], LIVE); r, ds, s0 = runner2(nm, w5)
    base[nm] = (r, ds, metrics(nm, r, ds), s0)
    e = P['eff']; macro = P['sg']['macro'][0]; sl = slice(s0+1, None)
    Cm = CM[nm][sl]; mC = (macro == 2)[sl]
    spells = int(((Cm[1:]) & ~(Cm[:-1])).sum() + Cm[0])
    mspells = int(((mC[1:]) & ~(mC[:-1])).sum() + mC[0])
    A_over = mC & (e[sl] == 0)
    log(f"\n[{nm.upper()}] scored {ds[0]}..{ds[-1]}  ({len(ds)} sessions)  base {base[nm][2]['c']*100:.1f}% / Sharpe {base[nm][2]['s']:.3f} / maxDD {base[nm][2]['m']*100:.1f}%  (ex-2020 CAGR {base[nm][2]['c2']*100:.1f}%, Sharpe {base[nm][2]['s2']:.3f}; halves {base[nm][2]['a']:.3f}/{base[nm][2]['b']:.3f})")
    mF = (macro == 5)[sl] & Cm; mCC = mC & Cm
    log(f"  macro-C sessions {mC.sum()} ({mC.mean()*100:.1f}%): hold the C row {mCC.sum()} ({mCC.sum()/mC.sum()*100:.1f}%), fast overlay gives A {A_over.sum()} ({A_over.sum()/mC.sum()*100:.1f}%), other {mC.sum()-mCC.sum()-A_over.sum()}")
    log(f"  effective-C sessions {Cm.sum()} = macro-C holding own row {mCC.sum()} + macro-F promoted to C by the fast overlay {mF.sum()}  (the mask includes both: live holds the C row on all of them)")
    log(f"  effective-C share of all sessions {Cm.mean()*100:.1f}%; C spells {spells} (macro-C spells {mspells}); mean core weight on C days {w5[0,:,0][sl][Cm].mean():.3f}")
    g = P['g'][sl]; v = P['vt'][sl]
    log(f"  within effective-C: QQQ >=5% under 200d {(Cm&(g<=-.05)).sum()} sessions, >=10% {(Cm&(g<=-.10)).sum()}; vol>30% {(Cm&(v>.30)).sum()}")
    # QQQ / core raw returns in C
    for lab, arr in (('QQQ', P['pn']['qqq']), ('core', P['pn']['core'])):
        x = arr[s0+1:][Cm]; log(f"  raw {lab} on effective-C days: {((np.prod(1+x))**(252/len(x))-1)*100:+.1f}%/yr, vol {x.std(ddof=1)*252**.5*100:.0f}%, n={len(x)}")

H = f"  {'variant':<44}{'CAGR':>7}{'vs base':>8}{'Sharpe':>7}{'dSh':>7}{'maxDD':>8}{'Sh 1st':>7}{'Sh 2nd':>7}{'ex20 CAGR':>10}{'vs b':>7}{'ex20 Sh':>8}{'lag CAGR':>9}{'lag Sh':>7}{'Csess chg':>10}"
for nm in PAN:
    log(f"\n--- {nm.upper()} PANEL ---"); log(H)
    bm = base[nm][2]
    log(f"  {'BASE (live)':<44}{bm['c']*100:6.1f}%{0:+8.2f}{bm['s']:7.3f}{0:+7.3f}{bm['m']*100:7.1f}%{bm['a']:7.3f}{bm['b']:7.3f}{bm['c2']*100:9.1f}%{0:+7.2f}{bm['s2']:8.3f}{bm['c']*100:8.1f}%{bm['s']:7.3f}{0:>10}")
    # lag base
    for lab, fn in VAR.items():
        spec = fn(nm); r, ds = run_spec(nm, spec); m = metrics(nm, r, ds)
        rl, dl = run_spec(nm, spec, lag=True); ml = metrics(nm, rl, dl)
        nch = int(np.any([s[0] for s in spec], axis=0).sum())
        res[(nm, lab)] = (m, ml, r)
        log(f"  {lab:<44}{m['c']*100:6.1f}%{(m['c']-bm['c'])*100:+8.2f}{m['s']:7.3f}{m['s']-bm['s']:+7.3f}{m['m']*100:7.1f}%{m['a']:7.3f}{m['b']:7.3f}{m['c2']*100:9.1f}%{(m['c2']-bm['c2'])*100:+7.2f}{m['s2']:8.3f}{ml['c']*100:8.1f}%{ml['s']:7.3f}{nch:>10}")
log("\n(lag = the variant row starts one session after C is first seen: mask & previous-session mask; exits are not delayed.)")

# ------------------------------------------------------------------ best 2
log('\n' + '='*140); log("Selection: variants that beat base on BOTH panels in CAGR and Sharpe (ranked by sum of the two Sharpe gains)"); log('='*140)
cands = []
for lab in VAR:
    a = res[('real', lab)][0]; b = res[('proxy', lab)][0]
    dr = (a['c']-base['real'][2]['c'], a['s']-base['real'][2]['s']); dp = (b['c']-base['proxy'][2]['c'], b['s']-base['proxy'][2]['s'])
    ok = dr[0] > 0 and dr[1] > 0 and dp[0] > 1e-9 and dp[1] > 1e-9
    log(f"  {lab:<44} real dCAGR {dr[0]*100:+.2f} dSh {dr[1]:+.3f} | proxy dCAGR {dp[0]*100:+.2f} dSh {dp[1]:+.3f} | {'BOTH' if ok else '-'}")
    if ok: cands.append((dr[1] + dp[1], lab))
cands.sort(reverse=True); best = [c[1] for c in cands[:2]]
if not best:
    inf = sorted(((res[('real', l)][0]['s']-base['real'][2]['s']) + (res[('proxy', l)][0]['s']-base['proxy'][2]['s']), l) for l in VAR)[::-1][:2]
    best = [l for _, l in inf]; log(f"  NO variant helps on both panels; INFORMATIONAL detail (not qualifying) for the two best by summed Sharpe gain: {best}")
log(f"  best (both panels): {best if best else 'NONE'}")

rng = np.random.default_rng(7)
def sharpe_arr(R):
    return R.mean(1)*252/(R.std(1, ddof=1)*252**.5)
for lab in best:
    log('\n' + '#'*140); log(f"DETAIL: {lab}"); log('#'*140)
    for nm in PAN:
        P = PAN[nm]; rb, ds, bmz, s0 = base[nm]; rv = res[(nm, lab)][2]; T = len(rv)
        # bootstrap
        nb = -(-T // 20); wins = 0; N = 3000; sd = []
        idxs = (rng.integers(0, T, (N, nb))[:, :, None] + np.arange(20)[None, None, :]).reshape(N, -1)[:, :T] % T
        sv = sharpe_arr(rv[idxs]); sb = sharpe_arr(rb[idxs]); pnb = float((sv <= sb).mean())
        log(f"[{nm}] block bootstrap (20d, 3000): P(Sharpe not better than base) = {pnb:.3f}; mean dSharpe {(sv-sb).mean():+.3f}, 5-95% [{np.percentile(sv-sb,5):+.3f}, {np.percentile(sv-sb,95):+.3f}]")
        # placebo: circular shifts of the C mask (keeps spell structure), same variant fractions applied to shifted sessions
        fn = VAR[lab]; spec = fn(nm); Cn = len(spec)
        act = (rv.mean()*252, ); dC = (res[(nm, lab)][0]['c']-bmz['c'], res[(nm, lab)][0]['s']-bmz['s'])
        dcs = []; dss = []; ncs = []
        full = np.zeros(len(PAN[nm]['pn']['dates']), bool)
        for k in range(150):
            sh = int(rng.integers(300, len(full)-300))
            sp2 = [(np.roll(m, sh), fr) for m, fr in spec]
            w5, wq, kx = build(nm, sp2); r2, d2, _ = runner2(nm, w5, wq, kx); m2 = metrics(nm, r2, d2)
            dcs.append(m2['c']-bmz['c']); dss.append(m2['s']-bmz['s']); ncs.append(int(np.any([s[0] for s in sp2], 0).sum()))
        dcs = np.array(dcs); dss = np.array(dss)
        log(f"[{nm}] placebo (150 random circular shifts of the same C-mask, same row): dCAGR mean {dcs.mean()*100:+.2f} sd {dcs.std()*100:.2f}; dSharpe mean {dss.mean():+.3f} sd {dss.std():.3f}; real dCAGR {dC[0]*100:+.2f}, dSharpe {dC[1]:+.3f}; share of placebos >= real: CAGR {np.mean(dcs>=dC[0]):.3f}, Sharpe {np.mean(dss>=dC[1]):.3f}")
        # crisis windows (proxy)
        if nm == 'proxy':
            for a, b, lb in (('2000-01-01', '2002-12-31', '2000-2002'), ('2008-01-01', '2008-12-31', '2008'), ('2001-01-01', '2002-12-31', '2001-2002 scored')):
                k = np.array([a <= d <= b for d in ds])
                if k.sum() < 10: continue
                cb, _, mb = prof(rb[k]); cv, _, mv = prof(rv[k]); tb = np.prod(1+rb[k])-1; tv = np.prod(1+rv[k])-1
                Cin = CM[nm][s0+1:][k].sum()
                log(f"[proxy] {lb}: total return base {tb*100:+.1f}% vs variant {tv*100:+.1f}%; maxDD base {mb*100:.1f}% vs {mv*100:.1f}%; effective-C sessions in window {Cin}")
    # neighbour grid
    log(f"neighbour grid around: {lab}")
    log(f"  {'point':<44}{'real CAGR':>10}{'d':>7}{'Sh':>7}{'| proxy CAGR':>13}{'d':>7}{'Sh':>7}")
    grid = []
    if lab.startswith('b') or lab.startswith('c'):
        for q in (0, .1, .25, .4, .5, .75, 1.0): grid.append((f"core {1-q:.0%} / QLD {q:.0%}", lambda nm, q=q: [(CM[nm], (1-q, 0, q, 0, 0))]))
    elif lab.startswith('d'):
        for q in (0, .1, .25, .4, .5): grid.append((f"core {1-q:.0%} / TQQQ {q:.0%}", lambda nm, q=q: [(CM[nm], (1-q, 0, 0, q, 0))]))
    elif lab.startswith('e'):
        for q in (0, .1, .25, .5, .75, 1.0): grid.append((f"core {1-q:.0%} / cash {q:.0%}", lambda nm, q=q: [(CM[nm], (1-q, 0, 0, 0, 0))]))
    elif lab.startswith('a'):
        for q in (0, .25, .5, .75, 1.0): grid.append((f"core {1-q:.0%} / QQQ {q:.0%}", lambda nm, q=q: [(CM[nm], (1-q, q, 0, 0, 0))]))
    elif lab.startswith('g'):
        for t in (.20, .25, .30, .35, .40, .50): grid.append((f"vol>{t:.0%}: {lab.split(': ')[1]}", lambda nm, t=t, fc=(.75 if '75' in lab else .5 if '50' in lab else 0.0): [(hivol(nm, t), (fc, 0, 0, 0, 0))]))
    else:   # f family: scan threshold and deep-row share
        deep_fr = {'QQQ': (0, 1, 0, 0, 0), 'QLD50': (.5, 0, .5, 0, 0), 'QLD25': (.75, 0, .25, 0, 0), 'cash50': (.5, 0, 0, 0, 0)}
        kind = 'QQQ' if '100% QQQ' in lab else 'QLD50' if '50/50 QLD' in lab or '50% core/50% QLD' in lab else 'QLD25' if '75% core/25% QLD' in lab else 'cash50'
        shal = '+ shallow' in lab; only_shallow = lab.startswith('f  shallow')
        for T in (.02, .03, .05, .075, .10, .15, .20):
            def mk(T=T):
                def fn(nm):
                    if only_shallow: return [(shallow(nm, T), (.5, 0, 0, 0, 0))]
                    s = [(deep(nm, T), deep_fr[kind])]
                    if shal: s.append((shallow(nm, T), (.5, 0, 0, 0, 0)))
                    return s
                return fn
            grid.append((f"threshold {T:.1%}", mk()))
    for gl, fn in grid:
        out = []
        for nm in PAN:
            r, ds = run_spec(nm, fn(nm)); m = metrics(nm, r, ds); out.append((m['c'], m['c']-base[nm][2]['c'], m['s']))
        log(f"  {gl:<44}{out[0][0]*100:9.1f}%{out[0][1]*100:+7.2f}{out[0][2]:7.3f}{out[1][0]*100:12.1f}%{out[1][1]*100:+7.2f}{out[1][2]:7.3f}")
log('\nDONE')
