"""Staged re-entry after a D-gate lift. Research only; reads repo, writes only to scratchpad gx_*."""
import csv, os, sys
import numpy as np
HERE = '/home/user/Robinhood-stock/paper-track'; sys.path.insert(0, HERE)
import monte_carlo as MC, state as S, vol_curve as VC
SP = '/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad'
MC.DATA = SP + '/data_ext'
S.A_BASE_FROM_SESSION = ('2026-11-06', (0.40, 0.60))
LIVE = dict(MC.LIVE, name='live', a_base=(0.40, 0.60), vol='max10_30')
OUT = open(SP + '/hv/gx_test.log', 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); OUT.write(s + '\n'); OUT.flush()

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

def prof(r):
    nav = np.cumprod(1+r); dd = nav/np.maximum.accumulate(nav)-1
    return nav[-1]**(252/len(r))-1, r.mean()*252/(r.std(ddof=1)*252**.5), dd.min()
def halves(r, ds, cut):
    i = next(k for k, d in enumerate(ds) if d >= cut); return prof(r[:i])[1], prof(r[i:])[1]

class Ctx: pass
def mkctx(name, sg, pn, d0, cut, real):
    c = Ctx(); c.name, c.sg, c.pn, c.cut, c.real = name, sg, pn, cut, real
    ds = pn['dates']; c.ds = ds; c.s0 = next(i for i, d in enumerate(ds) if d >= d0)
    c.w5 = MC.target_weights(sg, LIVE); c.key = MC.regime_key(sg, LIVE)[0]
    c.eff = MC._eff(sg, LIVE)[0]; c.gate = MC._gate(sg, LIVE)[0].astype(bool); c.zone = MC._zone(sg, LIVE)[0]
    v = np.fmax(sg['vol'][0], np.where(np.isnan(sg['vol'][0]), np.nan, sg['vol10'][0])); c.v = v
    c.T = len(ds)
    VIX = np.array([vix.get(d, np.nan) for d in ds])
    g = np.nan_to_num(sg['gaps'][200][0]); e = c.eff
    deep = ((e == 4) & (g <= -0.05)).astype(float) * 0.5
    on = False; pan = np.zeros(c.T)
    for i in range(c.T):
        x = VIX[i]
        if not np.isnan(x):
            if on and x < 25: on = False
            elif not on and x >= 30: on = True
        pan[i] = 0.25 if on else 0.0
    c.extra = [(pn['qqq'], deep), (pn['qqq'], pan)]
    # D3 row (unscaled) and mult
    c.d3 = np.array(S.D_LADDER_ROWS['D3'][:3], float)
    c.base_mask_ok = (c.eff == 3) & ~c.gate & (c.zone == 3)
    lift = np.zeros(c.T, bool)
    for t in range(1, c.T):
        lift[t] = c.gate[t-1] and not c.gate[t] and c.eff[t] == 3
    c.lift = lift
    return c

def windows(c, N):
    """list of (t0, length, sessions) windows after each lift. N int = sessions; ('v',thr) = until vol<thr."""
    out = []
    for t0 in np.where(c.lift)[0]:
        t = t0; L = 0
        while t < c.T and c.eff[t] == 3 and not c.gate[t]:
            if isinstance(N, tuple):
                if not (c.v[t] >= N[1]): break      # nan or below thr -> stop
            elif L >= N: break
            L += 1; t += 1
        out.append((t0, L))
    return out

def build_mask(c, N, lag=0):
    m = np.zeros(c.T, bool); ev = []
    for t0, L in windows(c, N):
        if L == 0: continue
        sess = np.arange(t0 + lag, t0 + lag + L)
        sess = sess[sess < c.T]
        hit = [t for t in sess if c.base_mask_ok[t]]
        if hit: ev.append((t0, L, len(hit)))
        for t in hit: m[t] = True
    return m, ev

def runner2(c, w5, qqq_w, mkey, extra):
    pn = c.pn; s0 = c.s0
    key = c.key + mkey.astype(np.int64) * 10**9
    cash = w5[0, :, 4].copy()
    legs = [pn['core'], pn['tqqq'], pn['qld'], pn['xlu']]; W = [w5[0, :, i] for i in range(4)]
    used = np.zeros_like(cash)
    # extra stand-alone QQQ leg paid out of cash before the cash legs
    legs.append(pn['qqq']); W.append(qqq_w); used = used + qqq_w
    cash = cash - qqq_w
    used2 = np.zeros_like(cash)
    if c.real:
        v = np.where(allowed, cash*S.VIXM_CASH_SHARE, 0.0); legs.append(vixm_r); W.append(v); key = key + allowed.astype(np.int64)*100000
        used2 = v
    for j, (rr, sh) in enumerate(extra):
        sh = np.clip(np.nan_to_num(sh), 0, 1)
        x = np.minimum(cash*sh, cash - used2); used2 = used2 + x
        legs.append(rr); W.append(x); key = key + (sh > 0).astype(np.int64) * (10**(6+j))
    legs.append(pn['cash']); W.append(cash - used2)
    w = np.stack(W, -1)[None]; L = np.stack(legs, -1)[None]
    r, tr = MC.run_strategy(w, key[None] if key.ndim==1 else key, L, s0)
    return r[0], tr[0]/((c.T-1-s0)/252), c.ds[s0+1:]

def variant(c, kind, N, par=None, lag=0):
    m, ev = build_mask(c, N, lag)
    w5 = c.w5.copy(); qw = np.zeros(c.T)
    tq = w5[0, :, 1].copy()                    # vol-scaled TQQQ weight on D3 rows
    if kind == 'base': m[:] = False; ev = []
    elif kind == 'a':   w5[0, m, 1] = 0; w5[0, m, 2] = tq[m]
    elif kind == 'b':   w5[0, m, 1] = 0; w5[0, m, 2] = tq[m]*0.5; qw[m] = tq[m]*0.5
    elif kind == 'c':   w5[0, m, 1] = 0; qw[m] = tq[m]
    elif kind == 'd':   w5[0, m, 1] = tq[m]*(par if par is not None else 0.5)
    elif kind == 'e':
        vt = par if par is not None else 0.15
        mult = np.where(np.isnan(c.v) | (c.v <= 0), 1.0, np.minimum(1.0, vt/np.where(c.v > 0, c.v, 1)))
        w5[0, m, 1] = np.minimum(tq[m], c.d3[1]*mult[m])
    w5[0, :, 4] = 1.0 - w5[0, :, :4].sum(-1) - qw
    r, t, ds = runner2(c, w5, qw, m, c.extra)
    return r, ev, m

def ex2020(r, ds):
    k = np.array([not d.startswith('2020') for d in ds]); return r[k]
def metrics(c, r, ds, base=None):
    cg, sh, dd = prof(r); a, b = halves(r, ds, c.cut); r2 = ex2020(r, ds); cg2, sh2, _ = prof(r2)
    return dict(cagr=cg, sh=sh, dd=dd, h1=a, h2=b, cagr_x=cg2, sh_x=sh2)

def sh_of(r): return r.mean()/r.std(ddof=1)*252**.5
def boot(rb, rv, draws=3000, blk=20, seed=7):
    n = len(rb); rng = np.random.default_rng(seed); nb = -(-n//blk); cnt = 0; d = []
    for ch in range(0, draws, 250):
        k = min(250, draws-ch)
        st = rng.integers(0, n, size=(k, nb))
        idx = ((st[:, :, None] + np.arange(blk)[None, None, :]) % n).reshape(k, -1)[:, :n]
        a, b = rb[idx], rv[idx]
        s = lambda x: x.mean(1)/x.std(1, ddof=1)*252**.5
        dd = s(b) - s(a); d.append(dd)
    d = np.concatenate(d)
    return (d <= 0).mean(), np.percentile(d, [5, 50, 95])

CTX = [mkctx('REAL 2015-11.. (SPMO core, VIXM sleeve)', sr, pr, '2015-11-02', '2021-03-01', True),
       mkctx('PROXY 2001.. (QQQ core, no VIXM)', sig, p, '2001-01-02', '2015-11-01', False)]

log('='*140); log('Staged re-entry after D-gate lift. Base = live design + deep-E QQQ leg + VIX-panic QQQ leg; 2bp.'); log('='*140)
for c in CTX:
    nl = int(c.lift[c.s0:].sum()); ls = [c.ds[t] for t in np.where(c.lift)[0]]
    n3 = int((c.lift & (c.zone == 3))[c.s0:].sum())
    log(f"{c.name}: sessions {c.ds[c.s0]}..{c.ds[-1]}; gate-lift events (effective D, gate on t-1, off t) = {nl}; of which D ladder zone 3 at the lift = {n3}")
    log("  lift dates: " + ', '.join(f"{c.ds[t]}(z{c.zone[t]},vol{c.v[t]*100:.0f}%)" for t in np.where(c.lift)[0] if t >= c.s0))
    nb = sum(1 for t in np.where(c.lift)[0] if t < c.s0)
    if nb: log(f"  ({nb} lift(s) before the backtest start are not counted in the P&L)")

# ---------- reverse check
log('\n' + '='*140); log('REVERSE CHECK: next-session returns (weights set at close t earn t+1) on D3 ungated sessions: first-N after a lift vs all other D3 days'); log('='*140)
for c in CTX:
    pn = c.pn; ok = c.base_mask_ok.copy(); ok[:c.s0] = False; ok[-1] = False
    log(f"\n{c.name}   (all D3 ungated sessions in range: {int(ok.sum())})")
    log(f"  {'window':<12}{'sess':>5}{'ev':>4} |{'TQQQ mean%':>11}{'hit%':>6}{'QLD mean%':>10}{'hit%':>6}{'QQQ mean%':>10}{'hit%':>6}{'TQQQ-3QQQ':>10}")
    def row(lab, sel, ev):
        idx = np.where(sel)[0] + 1
        if len(idx) == 0: log(f"  {lab:<12}{0:>5}"); return
        f = lambda k: (pn[k][idx].mean()*100, (pn[k][idx] > 0).mean()*100)
        t, q, qq = f('tqqq'), f('qld'), f('qqq')
        log(f"  {lab:<12}{len(idx):>5}{ev:>4} |{t[0]:11.3f}{t[1]:6.1f}{q[0]:10.3f}{q[1]:6.1f}{qq[0]:10.3f}{qq[1]:6.1f}{(pn['tqqq'][idx]-3*pn['qqq'][idx]).mean()*100:10.3f}")
    allm = {}
    for N in (3, 5, 10, 20, ('v', .25), ('v', .30)):
        m, ev = build_mask(c, N); m[:c.s0] = False; m &= ok; allm[N] = m
        row(f"first {N}" if isinstance(N, int) else f"vol<{int(N[1]*100)}%", m, len(ev))
        row("  others", ok & ~m, '')
    row('all D3', ok, '')

# ---------- main table
KINDS = [('base', 'base'), ('a', '(a) 100% QLD'), ('b', '(b) 50% QLD / 50% QQQ'), ('c', '(c) 100% QQQ'), ('d', '(d) half D3, rest cash'), ('e', '(e) D3 at 15% vol target')]
NS = [3, 5, 10, 20, ('v', .25), ('v', .30)]
def nlab(N): return f"N={N}" if isinstance(N, int) else f"until vol<{int(N[1]*100)}%"
RES = {}
H = f"  {'variant':<42}{'CAGR':>7}{'vs base':>8}{'Sharpe':>7}{'maxDD':>8}{'Sh 1st':>7}{'Sh 2nd':>7}{'CAGR x20':>9}{'dx20':>7}{'Shx20':>7}{'lag CAGR':>9}{'lag Sh':>7}{'ev':>4}{'sess':>5}"
for c in CTX:
    log('\n' + '='*140); log(f"{c.name}  (x20 = 2020 removed; lag = mask starts one session late; ev = events affected, sess = D3 sessions modified)"); log(H)
    rb, _, _ = variant(c, 'base', 3); ds = c.ds[c.s0+1:]; mb = metrics(c, rb, ds)
    RES[(c.name, 'base')] = (mb, rb)
    log(f"  {'base':<42}{mb['cagr']*100:6.1f}%{0:+8.2f}{mb['sh']:7.3f}{mb['dd']*100:7.1f}%{mb['h1']:7.3f}{mb['h2']:7.3f}{mb['cagr_x']*100:8.1f}%{0:+7.2f}{mb['sh_x']:7.3f}{mb['cagr']*100:8.1f}%{mb['sh']:7.3f}{0:>4}{0:>5}")
    for k, kl in KINDS[1:]:
        for N in NS:
            r, ev, m = variant(c, k, N); rl, _, _ = variant(c, k, N, lag=1); mm = metrics(c, r, ds); ml = metrics(c, rl, ds)
            RES[(c.name, k, N)] = (mm, r, ev, m)
            log(f"  {kl+' '+nlab(N):<42}{mm['cagr']*100:6.1f}%{(mm['cagr']-mb['cagr'])*100:+8.2f}{mm['sh']:7.3f}{mm['dd']*100:7.1f}%{mm['h1']:7.3f}{mm['h2']:7.3f}{mm['cagr_x']*100:8.1f}%{(mm['cagr_x']-mb['cagr_x'])*100:+7.2f}{mm['sh_x']:7.3f}{ml['cagr']*100:8.1f}%{ml['sh']:7.3f}{len(ev):>4}{int(m.sum()):>5}")

# ---------- pick best two that help on both panels
cands = []
for k, kl in KINDS[1:]:
    for N in NS:
        d = []
        ok = True
        for c in CTX:
            mm = RES[(c.name, k, N)][0]; mb = RES[(c.name, 'base')][0]
            d.append((mm['cagr']-mb['cagr'], mm['sh']-mb['sh']))
            if not (mm['cagr'] > mb['cagr'] and mm['sh'] > mb['sh']): ok = False
        cands.append((ok, sum(x[1] for x in d), k, N, d))
good = sorted([x for x in cands if x[0]], key=lambda x: -x[1])
log('\n' + '='*140)
log(f"Variants improving BOTH CAGR and Sharpe on BOTH panels: {len(good)} of {len(cands)}")
for ok, s, k, N, d in sorted(cands, key=lambda x: -x[1])[:8]:
    log(f"  {'HELPS-BOTH' if ok else 'not both  '} {k} {nlab(N):<20} dCAGR real {d[0][0]*100:+.2f}pp / proxy {d[1][0]*100:+.2f}pp ; dSharpe real {d[0][1]:+.3f} / proxy {d[1][1]:+.3f}")
seen=set(); best=[]
for x in good:
    if x[2] not in seen: seen.add(x[2]); best.append(x)
best=best[:2]
if not best:
    log("No variant helps on both panels; running bootstrap/grid/per-event on the top-2 by summed Sharpe delta for information only (NOT supported).")
    best = sorted(cands, key=lambda x: -x[1])[:2]

for ok, s, k, N, d in best:
    kl = dict(KINDS)[k]
    log('\n' + '='*140); log(f"DETAIL: {kl} {nlab(N)}   (helps on both panels: {ok})"); log('='*140)
    for c in CTX:
        mm, r, ev, m = RES[(c.name, k, N)]; rb = RES[(c.name, 'base')][1]
        pv, ci = boot(rb, r)
        log(f"\n{c.name}: block bootstrap (20-day blocks, 3000 draws): P(Sharpe not better than base) = {pv:.3f}; dSharpe 5/50/95 pct = {ci[0]:+.3f} / {ci[1]:+.3f} / {ci[2]:+.3f}")
        # neighbour grid
        log("  neighbour grid (dCAGR pp / dSharpe vs base):")
        grid = []
        Ns = [2, 3, 5, 10, 20, ('v', .20), ('v', .225), ('v', .25), ('v', .275), ('v', .30), ('v', .35), ('v', .40)]
        pars = {'d': [0.25, 0.5, 0.75], 'e': [0.10, 0.125, 0.15, 0.175], 'a': [None], 'b': [None], 'c': [None]}[k]
        mb = RES[(c.name, 'base')][0]
        hdr = '    ' + f"{'par\\N':<8}" + ''.join(f"{(n if isinstance(n,int) else 'v<%g%%' % (n[1]*100)):>14}" for n in Ns); log(hdr)
        for pa in pars:
            line = f"    {str(pa):<8}"
            for n in Ns:
                r2, _, _ = variant(c, k, n, par=pa); m2 = metrics(c, r2, c.ds[c.s0+1:])
                line += f"{(m2['cagr']-mb['cagr'])*100:+7.2f}/{m2['sh']-mb['sh']:+.3f}".rjust(14)
            log(line)
        # per-event
        log("  per-event (window = modified D3 sessions; returns of the strategy over those sessions, weights set at t earn t+1):")
        log(f"    {'lift date':<11}{'zone':>5}{'vol%':>6}{'sess':>5}{'base %':>8}{'variant %':>10}{'diff pp':>8}{'TQQQ %':>8}{'QLD %':>8}{'QQQ %':>8}")
        for t0, L, nh in ev:
            sel = np.where(m[t0:t0+L])[0] + t0
            idx = sel - c.s0
            if idx.min() < 0: continue
            g = lambda x: (np.prod(1 + x[idx]) - 1) * 100
            gp = lambda a: (np.prod(1 + a[sel+1]) - 1) * 100
            log(f"    {c.ds[t0]:<11}{c.zone[t0]:>5}{c.v[t0]*100:6.0f}{len(sel):>5}{g(rb):8.2f}{g(r):10.2f}{g(r)-g(rb):8.2f}{gp(c.pn['tqqq']):8.2f}{gp(c.pn['qld']):8.2f}{gp(c.pn['qqq']):8.2f}")
log('\nDone.')
