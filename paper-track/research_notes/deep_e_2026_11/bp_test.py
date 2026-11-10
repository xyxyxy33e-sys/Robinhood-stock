"""Buy-the-panic ideas on top of the live design WITH the deep-E leg (and vs the old base without it). Research only."""
exec(open('/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad/hv/hv_test.py').read().split("log('='*130)")[0].replace("hv_test.log", "bp_test.log"))
import time, itertools
rng = np.random.default_rng(23)
LETTERS = MC.LETTERS; T0 = time.time()
SC = '/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad/data_ext/'

# ------------------------------------------------------------------ context arrays (computed on proxy dates, sliced for real)
def ffill(a):
    a = a.copy(); last = np.nan
    for i in range(len(a)):
        if np.isnan(a[i]): a[i] = last
        else: last = a[i]
    return a
def build_ctx(sg, ds, qret):
    """sg: signals dict (1 path); ds: dates; qret: QQQ-like daily returns used only for the price-based triggers."""
    q = np.array(qret, float).copy(); q[0] = 0.0; px = np.cumprod(1 + q); n = len(px)
    r5 = np.zeros(n); r5[5:] = px[5:] / px[:-5] - 1
    hi = np.maximum.accumulate(px)
    from numpy.lib.stride_tricks import sliding_window_view as swv
    hi252 = hi.copy(); hi252[251:] = swv(px, 252).max(1)
    vx = ffill(np.array([vix.get(d, np.nan) for d in ds])); v3 = ffill(np.array([vix3m.get(d, np.nan) for d in ds]))
    h10 = vx.copy(); h10[9:] = swv(vx, 10).max(1)
    eff = MC._eff(sg, LIVE)[0]; gate = sg['gate'][0].astype(bool)
    g = {k: np.nan_to_num(sg['gaps'][k][0]) for k in (100, 150, 200)}
    return dict(eff=eff, gate=gate, g=g, r5=r5, dd=px / hi252 - 1, vx=vx, v3=v3, h10=h10, n=n,
                cash=(eff >= 4) | ((eff == 3) & gate), E=eff == 4, F=eff == 5, gD=(eff == 3) & gate)
cP = build_ctx(sig, dates, p['qqq'])
def slice_ctx(c, o): return {k: (v[o:] if isinstance(v, np.ndarray) else ({a: b[o:] for a, b in v.items()} if isinstance(v, dict) else v)) for k, v in c.items()}
cR = slice_ctx(cP, off); cR['n'] = len(rd)
CT = {'real': cR, 'proxy': cP}
PAN = {'real': (sr, pr, '2015-11-02', '2021-03-01'), 'proxy': (sig, p, '2001-01-02', '2015-11-01')}
log(f"VIX history {min(vix)}..{max(vix)} ({len(vix)} obs); VIX3M {min(vix3m)}..{max(vix3m)}; proxy sessions with VIX3M: {int((~np.isnan(np.array([vix3m.get(d, np.nan) for d in dates]))).sum())}")

# ------------------------------------------------------------------ mask builders
def lag(m): return np.r_[np.zeros(1, m.dtype), m[:-1]]
def roll(trig, N):
    on = np.zeros(len(trig), bool)
    for k in range(N): on[k:] |= trig[:len(trig) - k]
    return on
def deepE_mask(c, th=0.05, x=None):
    E, g = c['E'], c['g'][200]; x = -th if x is None else x
    if x == -th: return E & (g <= -th)
    m = np.zeros(len(E), bool); on = False
    for t in range(len(E)):
        on = bool(E[t] and g[t] <= x) if on else bool(E[t] and g[t] <= -th)
        m[t] = on
    return m
def f_A(c, th, S):
    st = c['F'] if S == 'F' else c['cash']; return st & (c['g'][200] <= -th)
def f_B(c, th, gp): return c['gD'] & (c['g'][gp] <= -th)
def f_C(c, ret, N): return roll(c['cash'] & (c['r5'] <= -ret), N)
def f_Dbk(c, th, ex):
    vx, v3 = c['vx'], c['v3']; m = np.zeros(c['n'], bool); on = False; age = 0
    for t in range(c['n']):
        if on:
            age += 1
            if (ex in ('bk', 'bk10') and not (vx[t] > v3[t])) or (ex == 'bk10' and age >= 10): on = False
        if not on and vx[t] >= th and vx[t] > v3[t]: on = True; age = 0     # NaN v3 -> False
        m[t] = on
    return m
def f_Dlv(c, th, ex):          # VIX only (full proxy history): in at VIX>=th, out when VIX<25 or after N=10 sessions
    vx = c['vx']; m = np.zeros(c['n'], bool); on = False; age = 0
    for t in range(c['n']):
        if on:
            age += 1
            if vx[t] < 25 or (ex == 'N10' and age >= 10): on = False
        if not on and vx[t] >= th: on = True; age = 0
        m[t] = on
    return m
def f_Dturn(c, fall, N): return roll((c['vx'] >= 25) & (c['vx'] <= (1 - fall) * c['h10']), N)
def f_E(c, th, S): return ((c['E'] | c['F']) if S == 'EF' else c['F']) & (c['dd'] <= -th)
def f_F1(c, x): return deepE_mask(c, 0.05, x)
SHARE_F2 = lambda c: (lambda g, E: E * np.where(g <= -0.10, 0.75, np.where(g <= -0.07, 0.50, np.where(g <= -0.05, 0.25, 0.0))))(c['g'][200], c['E'])

# variant specs: (family, name, fn, {param: values}, sizes)
SIZES = (0.25, 0.5, 1.0)
SPECS = [
 ('A', 'deep-F', f_A, dict(th=(0.10, 0.15, 0.20), S=('F', 'cash')), SIZES),
 ('B', 'deep-D-gated', f_B, dict(th=(0.05, 0.08), gp=(150, 100)), SIZES),
 ('C', 'oversold5d', f_C, dict(ret=(0.06, 0.08, 0.10), N=(3, 5, 10)), SIZES),
 ('D1', 'VIX-backw', f_Dbk, dict(th=(30, 35, 40), ex=('bk', 'bk10')), SIZES),
 ('D2', 'VIX-level', f_Dlv, dict(th=(30, 35, 40), ex=('lv', 'N10')), SIZES),
 ('D3', 'VIX-turn', f_Dturn, dict(fall=(0.15, 0.20), N=(5, 10, 20)), SIZES),
 ('E', 'dd252', f_E, dict(th=(0.10, 0.15, 0.20), S=('EF', 'F')), SIZES),
 ('F1', 'deepE-exit', f_F1, dict(x=(-0.03, -0.02)), (0.5,)),
]
def combos(params): return [dict(zip(params, v)) for v in itertools.product(*params.values())]
def lab_of(name, kw, sh): return f"{name} " + ' '.join(f"{k}={v}" for k, v in kw.items()) + f" sz={int(sh*100)}"

# ------------------------------------------------------------------ runs
CACHE = {}
def run(pk, legs, key=None):
    """legs: list of (returns, share array); returns (r, tr, ds)."""
    ck = (pk, key, MC.COST)
    if key is not None and ck in CACHE: return CACHE[ck]
    sg, pn, d0, cut = PAN[pk]; out = runner(sg, pn, d0, legs)
    if key is not None: CACHE[ck] = out
    return out
def deepleg(pk):
    c = CT[pk]; return [(PAN[pk][1]['qqq'], deepE_mask(c) * 0.5)]
def sel(r, ds, drop=None):
    y = np.array([d[:4] for d in ds]); return r[y != drop] if drop else r
def spells(m, s0):
    out = []; t = s0; n = len(m)
    while t < n - 1:
        if m[t]:
            u = t
            while u + 1 < n - 1 and m[u + 1]: u += 1
            out.append((t, u)); t = u + 1
        else: t += 1
    return out
BASE = {}
for pk in PAN:
    sg, pn, d0, cut = PAN[pk]
    rn, tn, ds = run(pk, deepleg(pk), key='new'); ro, to, _ = run(pk, [], key='old')
    BASE[pk] = dict(rn=rn, ro=ro, ds=ds, tn=tn, to=to, s0=next(i for i, d in enumerate(pn['dates']) if d >= d0))
    for k in ('rn', 'ro'):
        r = BASE[pk][k]; c_, s_, m_ = prof(r); a, b = halves(r, ds, cut); cx, sx, _ = prof(sel(r, ds, '2020'))
        log(f"BASE {pk} {'with deep-E (NEW)' if k=='rn' else 'without deep-E (OLD)'}: CAGR {c_*100:.2f}% Sharpe {s_:.3f} maxDD {m_*100:.1f}% Sh 1st/2nd {a:.3f}/{b:.3f} CAGR ex-2020 {cx*100:.2f}% (scored {ds[0]}..{ds[-1]})")

RES = {}
def evaluate(pk, fam, lab, m, sh, shares=None, replace=False, store=True):
    """m: bool mask (signal at close t); sh scalar; shares: optional share array (overrides m*sh)."""
    sg, pn, d0, cut = PAN[pk]; B = BASE[pk]; ds = B['ds']; s0 = B['s0']; QQ = pn['qqq']
    s_arr = (m * sh).astype(float) if shares is None else shares
    legs = [(QQ, s_arr)]
    rv, tv, _ = run(pk, ([] if replace else deepleg(pk)) + legs)
    ro_, _, _ = run(pk, legs)
    rl, _, _ = run(pk, ([] if replace else deepleg(pk)) + [(QQ, lag(s_arr))])
    cn, sn, _ = prof(B['rn']); cv, sv, mv = prof(rv); a, b = halves(rv, ds, cut)
    cxn = prof(sel(B['rn'], ds, '2020'))[0]; cxv = prof(sel(rv, ds, '2020'))[0]
    co = prof(B['ro'])[0]; cxo = prof(sel(B['ro'], ds, '2020'))[0]; cro = prof(ro_)[0]; crxo = prof(sel(ro_, ds, '2020'))[0]
    sp = spells(s_arr > 0, s0); gains = [(rv[a_ - s0:b_ - s0 + 1] - B['rn'][a_ - s0:b_ - s0 + 1]).sum() * 100 for a_, b_ in sp]
    d = dict(pk=pk, fam=fam, lab=lab, cagr=cv, d_new=cv - cn, sh=sv, mdd=mv, s1=a, s2=b, dx=cxv - cxn, dlag=prof(rl)[0] - cn,
             nsp=len(sp), win=(np.mean([g > 0 for g in gains]) if gains else float('nan')), worst=(min(gains) if gains else float('nan')),
             days=int((s_arr[s0:-1] > 0).sum()), d_old=cro - co, dx_old=crxo - cxo, r=rv, m=(s_arr > 0), sh_s=sh, shares=s_arr, replace=replace)
    if store: RES[(pk, lab)] = d
    return d
HD = f"  {'variant':<46}{'CAGR':>7}{'dNEW':>7}{'Sharpe':>7}{'maxDD':>7}{'Sh1':>6}{'Sh2':>6}{'dNEWx20':>8}{'dLag':>7}{'spl':>4}{'win%':>5}{'worst':>7}{'days':>5}{'dOLD':>7}{'dOLDx20':>8}"
def row(d):
    log(f"  {d['lab']:<46}{d['cagr']*100:6.2f}%{d['d_new']*100:+7.2f}{d['sh']:7.3f}{d['mdd']*100:6.1f}%{d['s1']:6.2f}{d['s2']:6.2f}{d['dx']*100:+8.2f}{d['dlag']*100:+7.2f}{d['nsp']:4d}{d['win']*100:5.0f}{d['worst']:+7.2f}{d['days']:5d}{d['d_old']*100:+7.2f}{d['dx_old']*100:+8.2f}")

log('='*190)
log("BUY-THE-PANIC ideas -- live design + deep-E leg = NEW base; each idea adds QQQ out of the REMAINING cash leg (VIXM sleeve first, deep-E 50% second, idea third). 2bp. Research only.")
log("dNEW = CAGR pts vs new base; dNEWx20 = same with 2020 removed; dLag = dNEW if the idea acts one session late; spl/win%/worst = idea spells, share with positive book gain, worst spell gain (book pts, vs new base); dOLD/dOLDx20 = same idea vs the old base (no deep-E).")
log("Sh1/Sh2 = Sharpe in first/second half (real split 2021-03-01, proxy split 2015-11-01). Triggers computed at close t, traded at close t (as deep-E was modelled).")
log('='*190)
for pk in PAN:
    B = BASE[pk]; c, s, m = prof(B['rn']); a, b = halves(B['rn'], B['ds'], PAN[pk][3]); cx = prof(sel(B['rn'], B['ds'], '2020'))[0]
    log(f"NEW BASE {pk}: CAGR {c*100:.2f}% Sharpe {s:.3f} maxDD {m*100:.1f}% Sh1/Sh2 {a:.3f}/{b:.3f}; ex-2020 CAGR {cx*100:.2f}%")
for pk in PAN:
    log(f"\n{'#'*20} {pk.upper()} PANEL {'#'*20}"); c = CT[pk]
    log(f"  state shares of sessions: E {c['E'][1:].mean()*100:.1f}%  F {c['F'][1:].mean()*100:.1f}%  gated D {c['gD'][1:].mean()*100:.1f}%  all cash states {c['cash'][1:].mean()*100:.1f}%")
    for fam, name, fn, params, sizes in SPECS:
        log(f"\n[{fam}] {name} -- {pk}"); log(HD)
        for kw in combos(params):
            m = fn(c, **kw)
            for sh in sizes: row(evaluate(pk, fam, lab_of(name, kw, sh), m, sh, replace=(fam == 'F1')))
    # F2 scaled-by-depth (replaces the deep-E leg)
    log(f"\n[F2] deep-E scaled by depth (25% at -5, 50% at -7, 75% at -10; replaces the deep-E leg) -- {pk}"); log(HD)
    sh_arr = SHARE_F2(c); row(evaluate(pk, 'F2', 'deepE scaled 25/50/75', sh_arr > 0, 0.5, shares=sh_arr, replace=True))
    log(f"  [time {time.time()-T0:.0f}s]")

# ------------------------------------------------------------------ selection
log('\n' + '='*190); log("SELECTION: best configuration per family by min over panels of the ex-2020 gain vs the NEW base (needs >0 days on both panels)"); log('='*190)
labs = sorted({k[1] for k in RES if k[0] == 'real'}); best = {}
for lab in labs:
    a, b = RES[('real', lab)], RES[('proxy', lab)]
    if a['days'] == 0 or b['days'] == 0: continue
    sc = min(a['dx'], b['dx']); f = a['fam']
    if f not in best or sc > best[f][0]: best[f] = (sc, lab)
for f, (sc, lab) in sorted(best.items(), key=lambda kv: -kv[1][0]):
    a, b = RES[('real', lab)], RES[('proxy', lab)]
    log(f"  fam {f:<3} {lab:<46} min ex-2020 dNEW {sc*100:+.2f} | real dNEW {a['d_new']*100:+.2f} x20 {a['dx']*100:+.2f} days {a['days']} | proxy dNEW {b['d_new']*100:+.2f} x20 {b['dx']*100:+.2f} days {b['days']}")
top = [lab for f, (sc, lab) in sorted(best.items(), key=lambda kv: -kv[1][0]) if sc > 0][:3]
log(f"  TOP (positive on both panels ex-2020, distinct families): {top}")
if not top:
    top = [lab for f, (sc, lab) in sorted(best.items(), key=lambda kv: -kv[1][0])][:3]
    log(f"  none positive on both; carrying the three least-bad for completeness: {top}")

# ------------------------------------------------------------------ robustness for the top 3
def boot(a, b, n=3000, B=20):
    N = len(a); K = N // B + 1
    st = rng.integers(0, N - B, (n, K)); idx = (st[:, :, None] + np.arange(B)).reshape(n, -1)[:, :N]
    A, Bb = a[idx], b[idx]; sa = A.mean(1) / A.std(1); sb = Bb.mean(1) / Bb.std(1)
    return float(((sa - sb) <= 0).mean()), float(np.percentile(sa - sb, 5)), float(np.median(sa - sb))
log('\n' + '='*190); log("ROBUSTNESS of the top 3"); log('='*190)
NPL = 150
for lab in top:
    log(f"\n--- {lab} ---")
    for pk in ('real', 'proxy'):
        d = RES[(pk, lab)]; B = BASE[pk]; ds = B['ds']; s0 = B['s0']; sg, pn, d0, cut = PAN[pk]; c = CT[pk]
        pn_, q5, med = boot(d['r'], B['rn']); pnx, _, _ = boot(sel(d['r'], ds, '2020'), sel(B['rn'], ds, '2020'))
        log(f"  {pk}: dNEW {d['d_new']*100:+.2f} Sharpe {d['sh']:.3f} vs {prof(B['rn'])[1]:.3f}; bootstrap P(Sharpe not better than deep-E base) {pn_:.3f} (5th pct dSh {q5:+.3f}, median {med:+.3f}); ex-2020 P {pnx:.3f}")
        # placebo: same count, same states
        sh = d['sh_s']; m = d['m']; eff = c['eff']; stk = eff + 10 * c['gate']
        pool = np.isin(stk, np.unique(stk[m])) & (np.arange(len(m)) >= s0) & (np.arange(len(m)) < len(m) - 1)
        pidx = np.where(pool)[0]; nd_ = int(m[s0:-1].sum()); lens = [b - a + 1 for a, b in spells(m, s0)]
        A, Bk = [], []
        for it in range(NPL):
            mm = np.zeros(len(m), bool); mm[rng.choice(pidx, min(nd_, len(pidx)), replace=False)] = True
            r_ = evaluate_r = run(pk, deepleg(pk) + [(pn['qqq'], mm * sh)])[0]; A.append(((prof(r_)[0] - prof(B['rn'])[0]) * 100, prof(r_)[1] - prof(B['rn'])[1]))
            mm = np.zeros(len(m), bool)
            for L in lens:
                st_ = rng.choice(pidx); mm[st_:st_ + L] = True
            r_ = run(pk, deepleg(pk) + [(pn['qqq'], mm * sh)])[0]; Bk.append(((prof(r_)[0] - prof(B['rn'])[0]) * 100, prof(r_)[1] - prof(B['rn'])[1]))
        for nm, X in (('random days, same count', np.array(A)), ('random spells, same lengths', np.array(Bk))):
            log(f"     placebo {nm}, pool = same states ({len(pidx)} days): dCAGR mean {X[:,0].mean():+.2f} 5-95% [{np.percentile(X[:,0],5):+.2f},{np.percentile(X[:,0],95):+.2f}] max {X[:,0].max():+.2f}; actual {d['d_new']*100:+.2f}; P(placebo dCAGR >= actual) {(X[:,0] >= d['d_new']*100).mean():.3f}; P(placebo dSharpe >= actual) {(X[:,1] >= d['sh']-prof(B['rn'])[1]).mean():.3f} ({NPL} draws)")
    # neighbour grid: all sweep configs within one grid step in every parameter and size
    fam = RES[('real', lab)]['fam']; spec = next(s for s in SPECS if s[0] == fam) if fam != 'F2' else None
    if spec:
        _, name, fn, params, sizes = spec; kw0 = None
        for kw in combos(params):
            for sh in sizes:
                if lab_of(name, kw, sh) == lab: kw0, sh0 = kw, sh
        keys = list(params); idx0 = [params[k].index(kw0[k]) for k in keys]; sidx = sizes.index(sh0)
        log(f"  neighbour grid (parameters within +-1 grid step and size within +-1 step; dNEW / dNEW ex-2020 in CAGR pts, real | proxy):")
        for ii in itertools.product(*[[j for j in (i - 1, i, i + 1) if 0 <= j < len(params[k])] for k, i in zip(keys, idx0)]):
            kw = {k: params[k][j] for k, j in zip(keys, ii)}
            cells = []
            for sj in [j for j in (sidx - 1, sidx, sidx + 1) if 0 <= j < len(sizes)]:
                l2 = lab_of(name, kw, sizes[sj]); a, b = RES[('real', l2)], RES[('proxy', l2)]
                cells.append(f"sz{int(sizes[sj]*100)}: {a['d_new']*100:+.2f}/{a['dx']*100:+.2f} | {b['d_new']*100:+.2f}/{b['dx']*100:+.2f}")
            log(f"     {' '.join(f'{k}={v}' for k, v in kw.items()):<26} " + '   '.join(cells))
    # bear markets on the proxy (scored from 2000-07-03)
    c = CT['proxy']; d0x = '2000-07-03'; sg, pn, _, _ = PAN['proxy']; QQ = pn['qqq']; m = RES[('proxy', lab)]['shares']
    PAN['x'] = (sig, p, d0x, '2015-11-01'); CT['x'] = cP
    rbx = run('x', deepleg('proxy'))[0]; rvx, _, dsx = run('x', ([] if RES[('proxy', lab)]['replace'] else deepleg('proxy')) + [(QQ, m)]); dsx = dsx
    log(f"  proxy scored from {d0x}: new base CAGR {prof(rbx)[0]*100:.2f}% Sharpe {prof(rbx)[1]:.3f} maxDD {prof(rbx)[2]*100:.1f}% | +idea CAGR {prof(rvx)[0]*100:.2f}% Sharpe {prof(rvx)[1]:.3f} maxDD {prof(rvx)[2]*100:.1f}%")
    for nm, y0, y1 in (('2000-07..2002', 2000, 2002), ('2008', 2008, 2008), ('2007..2009', 2007, 2009), ('2020', 2020, 2020), ('2022', 2022, 2022)):
        ix = [i for i, dd_ in enumerate(dsx) if y0 <= int(dd_[:4]) <= y1]; a, b = rbx[ix], rvx[ix]
        nv = lambda r: np.cumprod(1 + r); dm = lambda r: (nv(r) / np.maximum.accumulate(nv(r)) - 1).min() * 100
        on = int(sum(1 for t, d_ in enumerate(p['dates']) if y0 <= int(d_[:4]) <= y1 and m[t] > 0))
        log(f"     {nm:<14} new-base cum {(np.prod(1+a)-1)*100:+7.1f}% maxDD {dm(a):6.1f}% | +idea cum {(np.prod(1+b)-1)*100:+7.1f}% maxDD {dm(b):6.1f}% | diff {(np.prod(1+b)-np.prod(1+a))*100:+.2f} pts; idea sessions on {on}")
    # NDX-only overlay from 1987
    if 'NDX' not in globals():
        ndx = {rr['d']: float(rr['c']) for rr in csv.DictReader(open(SC + 'NDX_index_daily.csv'))}
        nd = sorted(ndx); npx = np.array([ndx[d] for d in nd]); nr = np.r_[0, npx[1:] / npx[:-1] - 1]
        tb_ = MC._load('dgs3mo_full.csv', 'observation_date', 'DGS3MO'); tbd = sorted(tb_); j = 0; last = 0.0; rate = []
        for d in nd:
            while j < len(tbd) and tbd[j] <= d: last = tb_[tbd[j]]; j += 1
            rate.append(last / 100)
        rate = np.array(rate); yf = np.r_[0, [MC._yf(nd[i - 1], nd[i]) for i in range(1, len(nd))]]; cashN = np.r_[rate[0], rate[:-1]] * yf
        sgN = MC.signals(npx[None], npx[None]); cN = build_ctx(sgN, nd, nr); NDX = (nd, nr, cashN, cN, next(i for i, d in enumerate(nd) if d >= '1990-06-01'))
    nd, nr, cashN, cN, n0 = NDX
    fam = RES[('real', lab)]['fam']
    if fam == 'F2': mN = SHARE_F2(cN)
    else:
        _, name, fn, params, sizes = next(s for s in SPECS if s[0] == fam)
        for kw in combos(params):
            for sh in sizes:
                if lab_of(name, kw, sh) == lab: mN = fn(cN, **kw) * sh
    dN = deepE_mask(cN) * 0.5
    eff_sh = np.minimum(mN, 1 - dN) if not RES[('real', lab)]['replace'] else mN
    inc = np.zeros(len(nd)); costv = np.zeros(len(nd))
    for t in range(n0, len(nd) - 1):
        inc[t + 1] = eff_sh[t] * (nr[t + 1] - cashN[t + 1]); costv[t + 1] = 0.0002 * abs(eff_sh[t] - (eff_sh[t - 1] if t > n0 else 0))
    net = inc - costv; yy = {}
    for t in range(n0, len(nd)): yy[nd[t][:4]] = yy.get(nd[t][:4], 0) + net[t]
    eras = (('1990-1999', '1990', '1999'), ('2000-2002', '2000', '2002'), ('2003-2006', '2003', '2006'), ('2007-2009', '2007', '2009'), ('2010-2019', '2010', '2019'), ('2020', '2020', '2020'), ('2021-2026', '2021', '2026'))
    sp = spells(eff_sh > 0, n0); wins = 0; wl = []
    for a_, b_ in sp:
        g_ = net[a_ + 1:b_ + 2].sum() * 100; wl.append(g_); wins += g_ > 0
    log(f"  NDX-only overlay (price index + T-bill, VIX from 1990, scored from {nd[n0]}; share capped at 1 - deep-E share; additive pts of book, net of 2bp): total {sum(yy.values())*100:+.2f} pts, {len(sp)} spells, wins {wins}, worst spell {min(wl) if wl else float('nan'):+.2f}")
    log("     by era: " + '; '.join(f"{lb} {sum(v for y, v in yy.items() if a <= y <= b)*100:+.2f}" for lb, a, b in eras))
log(f"\ndone in {time.time()-T0:.0f}s")
OUT.close()
