"""State-specific volatility target research. Base = 2026-11-10 live design (hv_test design + deep-E + VIX-panic QQQ legs,
VIXM sleeve on the real panel). Risky legs scaled by min(1, target/vol); freed weight -> cash leg; cash legs computed AFTER scaling.
Research only."""
import csv, os, sys, math
import numpy as np
HERE = '/home/user/Robinhood-stock/paper-track'; sys.path.insert(0, HERE)
import monte_carlo as MC, state as S, vol_curve as VC
SP = '/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad'
MC.DATA = SP + '/data_ext'
S.A_BASE_FROM_SESSION = ('2026-11-06', (0.40, 0.60))
LIVE = dict(MC.LIVE, name='live', a_base=(0.40, 0.60), vol='max10_30')
OUT = open(SP + '/hv/vt_test.log', 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); OUT.write(s + '\n'); OUT.flush()
NOTES = HERE + '/research_notes/vixm_followups_2026_11'

p = MC.load_panel('proxy'); dates = p['dates']
qfull = 100*np.cumprod(1+p['qqq'])
sig = MC.signals(qfull[None], (100*np.cumprod(1+p['ew']))[None])
pr = MC.load_panel('real'); off = dates.index(pr['dates'][0])
def cut_sig(sg): return {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sg.items()}
sr = cut_sig(sig); rd = pr['dates']
# 60-day realized vol (same convention as sig['vol'])
srq = qfull[1:]/qfull[:-1]-1
vol60_full = np.full(len(dates), np.nan)
for t in range(60, len(dates)): vol60_full[t] = srq[t-60:t].std(ddof=1)*math.sqrt(252)
sig['vol60'] = vol60_full[None]; sr['vol60'] = vol60_full[None, off:]
vix, vsrc = VC.history('VIX'); vix3m, _ = VC.history('VIX3M')
vol30 = {d: (None if np.isnan(v) else float(v)) for d, v in zip(rd, sr['vol'][0])}
VX = S.vixm_series(rd, vix, vix3m, vol30)
eff_r = MC._eff(sr, LIVE)[0]
allowed = np.array([bool(VX.get(d, {}).get('allowed')) for d in rd])
allowed &= ~((eff_r == 3) & ~sr['gate'][0].astype(bool) & (sr['zone'][0] == 2))
_px = {r['d']: float(r['c']) for r in csv.DictReader(open(os.path.join(MC.DATA, 'vixm_daily.csv')))}
vixm_r = MC._rets(_px, rd); vixm_r[0] = 0.0

def extra_legs(sg, pn):
    ds = pn['dates']; e = MC._eff(sg, LIVE)[0]; g = np.nan_to_num(sg['gaps'][200][0])
    deep = ((e == 4) & (g <= -0.05)).astype(float)*0.5
    V = np.array([vix.get(d, np.nan) for d in ds]); on = False; pan = np.zeros(len(ds))
    for i in range(len(ds)):
        v = V[i]
        if not np.isnan(v):
            if on and v < 25: on = False
            elif not on and v >= 30: on = True
        pan[i] = 0.25 if on else 0.0
    return [(pn['qqq'], deep), (pn['qqq'], pan)]

PANELS = {'real': dict(sg=sr, pn=pr, d0='2015-11-02', cut='2021-03-01', real=True),
          'proxy': dict(sg=sig, pn=p, d0='2001-01-02', cut='2015-11-01', real=False)}
for k, P_ in PANELS.items(): P_['ex'] = extra_legs(P_['sg'], P_['pn']); P_['w0'] = MC.target_weights(P_['sg'], dict(LIVE, vol_target=1e9))

def mults(P_, vt=0.20, A=None, D=None, D2=None, D3=None, est60A=False, capA=None, capthr=0.25, **_):
    sg = P_['sg']; eff = MC._eff(sg, LIVE)[0]; zone = sg['zone'][0]
    v = np.fmax(sg['vol'], np.where(np.isnan(sg['vol']), np.nan, sg['vol10']))[0].copy()
    tv = np.full(len(v), float(vt)); a = eff == 0
    if A is not None: tv[a] = A
    if D is not None: tv[eff == 3] = D
    if D2 is not None: tv[(eff == 3) & (zone == 2)] = D2
    if D3 is not None: tv[(eff == 3) & (zone == 3)] = D3
    vcap = v.copy()
    if est60A: v[a] = sg['vol60'][0][a]
    m = np.where(np.isnan(v) | (v <= 0), 1.0, np.minimum(1.0, tv/np.where(v > 0, v, 1)))
    if capA is not None: m = np.where(a & (vcap > capthr), np.minimum(m, capA), m)
    return m

def build(P_, lag=False, **kw):
    sg, pn = P_['sg'], P_['pn']; ds = pn['dates']; s0 = next(i for i, d in enumerate(ds) if d >= P_['d0'])
    w5 = P_['w0'].copy(); m = mults(P_, **kw)
    w5[..., :4] *= m[None, :, None]; w5[..., 4] = 1.0 - w5[..., :4].sum(-1)
    key = MC.regime_key(sg, LIVE); cash = w5[0, :, 4].copy()
    legs = [pn['core'], pn['tqqq'], pn['qld'], pn['xlu']]; W = [w5[0, :, i] for i in range(4)]
    used = np.zeros_like(cash)
    if P_['real']:
        v = np.where(allowed, cash*S.VIXM_CASH_SHARE, 0.0); legs.append(vixm_r); W.append(v); used = v
        key = key + allowed[None].astype(int)*100000
    qq = np.zeros_like(cash)
    for j, (rr, sh) in enumerate(P_['ex']):
        sh = np.clip(np.nan_to_num(sh), 0, 1); x = np.minimum(cash*sh, cash-used); used = used+x; qq = qq+x
        legs.append(rr); W.append(x); key = key + (sh[None] > 0).astype(int)*(10**(6+j))
    legs.append(pn['cash']); W.append(cash-used)
    w = np.stack(W, -1)[None]; L = np.stack(legs, -1)[None]
    if lag:
        w = np.concatenate([w[:, :1], w[:, :-1]], 1); key = np.concatenate([key[:, :1], key[:, :-1]], 1)
    expo = (w5[0, :, 0] + 3*w5[0, :, 1] + 2*w5[0, :, 2] + qq)[s0:-1].mean()
    return w, key, L, s0, ds, expo

def run(P_, **kw):
    w, key, L, s0, ds, expo = build(P_, **kw)
    r, tr = MC.run_strategy(w, key, L, s0)
    return r[0], tr[0]/((len(ds)-1-s0)/252), ds[s0+1:], expo

def expo_only(P_, **kw): return build(P_, **kw)[5]

def prof(r):
    nav = np.cumprod(1+r); dd = nav/np.maximum.accumulate(nav)-1
    return nav[-1]**(252/len(r))-1, r.mean()*252/(r.std(ddof=1)*252**.5), dd.min()
def halves(r, ds, cut):
    i = next(k for k, d in enumerate(ds) if d >= cut); return prof(r[:i])[1], prof(r[i:])[1]
def no2020(r, ds):
    m = np.array([not d.startswith('2020') for d in ds]); return prof(r[m])
def yearly(r, ds):
    y = {}
    for d, x in zip(ds, r): y.setdefault(d[:4], []).append(x)
    return {k: np.prod(1+np.array(v))-1 for k, v in y.items()}

CTRL_CACHE = {}
def control_vt(P_name, target_expo):
    """single global vt (everything else base) whose average QQQ-equivalent exposure matches target_expo."""
    P_ = PANELS[P_name]; lo, hi = 0.03, 3.0
    if expo_only(P_, vt=hi) < target_expo - 1e-4 or expo_only(P_, vt=lo) > target_expo + 1e-4: return None
    for _ in range(40):
        mid = (lo+hi)/2
        if expo_only(P_, vt=mid) < target_expo: lo = mid
        else: hi = mid
    return (lo+hi)/2

def evalv(name, kw):
    """full evaluation of variant kw on both panels; returns dict per panel"""
    res = {}
    for pn_, P_ in PANELS.items():
        r, t, ds, ex = run(P_, **kw); c, s, m = prof(r); a, b = halves(r, ds, P_['cut']); c20, s20, _ = no2020(r, ds)
        rl, _, dsl, _ = run(P_, lag=True, **kw); cl, sl, _ = prof(rl)
        res[pn_] = dict(r=r, ds=ds, cagr=c, sh=s, dd=m, h1=a, h2=b, c20=c20, s20=s20, cl=cl, sl=sl, ex=ex, tr=t)
    return res

def ctrl(res_v):
    out = {}
    for pn_, P_ in PANELS.items():
        x = control_vt(pn_, res_v[pn_]['ex'])
        if x is None: out[pn_] = None; continue
        r, t, ds, ex = run(P_, vt=x); c, s, m = prof(r); out[pn_] = dict(vt=x, cagr=c, sh=s, dd=m, ex=ex, r=r)
    return out

if __name__ == '__main__':
    log('='*150); log(f"State-specific vol target -- base 20%, max(10d,30d); VIX {vsrc}; real {rd[0]}..{rd[-1]}; proxy {dates[0]}..{dates[-1]}"); log('='*150)
    base = evalv('base', {}); 
    for pn_ in PANELS: log(f"base {pn_}: {base[pn_]['cagr']*100:.1f}% / Sharpe {base[pn_]['sh']:.3f} / DD {base[pn_]['dd']*100:.1f}% exposure {base[pn_]['ex']:.3f}")
    VARS = [('base 20% everywhere', {}),
      ('a) A 22%', dict(A=.22)), ('a) A 25%', dict(A=.25)), ('a) A 30%', dict(A=.30)),
      ('b) D3 15%', dict(D3=.15)), ('b) D3 17.5%', dict(D3=.175)), ('b) D2 15%', dict(D2=.15)), ('b) D2 17.5%', dict(D2=.175)),
      ('b) D2+D3 15%', dict(D2=.15, D3=.15)), ('b) D2+D3 17.5%', dict(D2=.175, D3=.175)),
      ('c) A 25% + D(all zones) 17.5%', dict(A=.25, D=.175)), ('c) A 25% + D2+D3 17.5%', dict(A=.25, D2=.175, D3=.175)),
      ('d) single 18%', dict(vt=.18)), ('d) single 22%', dict(vt=.22)),
      ('e) A uses 60d vol (20%)', dict(est60A=True)), ('e) A uses 60d vol (25%)', dict(est60A=True, A=.25)),
      ('f) A cap 0.8 when vol>25%', dict(capA=.8)), ('f) A cap 0.7 when vol>25%', dict(capA=.7)), ('f) A cap 0.6 when vol>25%', dict(capA=.6)),
      ('f) A 25% + cap 0.7 when vol>25%', dict(A=.25, capA=.7)), ('f) A 25% + cap 0.6 when vol>25%', dict(A=.25, capA=.6))]
    H = f"  {'variant':<36}{'CAGR':>7}{'vsBase':>7}{'Sharpe':>7}{'maxDD':>7}{'Sh1st':>7}{'Sh2nd':>7}{'CAGR-20':>8}{'Sh-20':>7}{'lagCAGR':>8}{'lagSh':>7}{'expo':>6}{'tr/yr':>6} | {'ctrlvt':>6}{'ctrlCAGR':>9}{'ctrlSh':>7}{'ctrlDD':>7}{'dSh':>7}{'dCAGR':>7}"
    ALL = {}
    for pn_ in PANELS:
        log(f"\n=== {pn_.upper()} panel (scored from {PANELS[pn_]['d0']}; halves split {PANELS[pn_]['cut']}); -20 = 2020 removed ==="); log(H)
        for name, kw in VARS:
            if name not in ALL: ALL[name] = (kw, evalv(name, kw), None); ALL[name] = (kw, ALL[name][1], ctrl(ALL[name][1]))
            kw, rv, cv = ALL[name]; x = rv[pn_]; c = cv[pn_]
            cs = (f" | {c['vt']:6.3f}{c['cagr']*100:8.1f}%{c['sh']:7.3f}{c['dd']*100:6.1f}%{x['sh']-c['sh']:+7.3f}{(x['cagr']-c['cagr'])*100:+7.2f}" if c else " | n/a (exposure not reachable by single vt)")
            if name.startswith('base'): cs = ''
            log(f"  {name:<36}{x['cagr']*100:6.1f}%{(x['cagr']-base[pn_]['cagr'])*100:+7.2f}{x['sh']:7.3f}{x['dd']*100:6.1f}%{x['h1']:7.3f}{x['h2']:7.3f}{x['c20']*100:7.1f}%{x['s20']:7.3f}{x['cl']*100:7.1f}%{x['sl']:7.3f}{x['ex']:6.2f}{x['tr']:6.1f}{cs}")
    # ---- select best 2: positive Sharpe margin over exposure-matched control on both panels (variants that change exposure); rank by min margin
    cand = []
    for name, (kw, rv, cv) in ALL.items():
        if name.startswith('base') or name.startswith('d)'): continue
        if cv['real'] is None or cv['proxy'] is None: continue
        mr = rv['real']['sh']-cv['real']['sh']; mp = rv['proxy']['sh']-cv['proxy']['sh']
        cand.append((min(mr, mp), name, mr, mp))
    cand.sort(reverse=True)
    log("\nRanking vs exposure-matched control (Sharpe margin real / proxy; min):")
    for m, n, a, b in cand: log(f"  {n:<36} real {a:+.3f}  proxy {b:+.3f}  min {m:+.3f}")
    best = [c for c in cand if c[0] > 0][:2]
    log("\nQualifying (beat control Sharpe on both panels): " + (', '.join(c[1] for c in best) if best else 'NONE'))
    # report extra detail for top 2 qualifying, or if none, the top 2 by min margin flagged as non-qualifying
    focus = best if best else cand[:2]
    rng = np.random.default_rng(12345)
    def boot(rv, rb, n=3000, L=20):
        T = len(rv); nb = int(math.ceil(T/L)); cnt = 0
        for _ in range(n):
            st = rng.integers(0, T, nb); idx = (st[:, None]+np.arange(L)[None]).reshape(-1)[:T] % T
            a = rv[idx]; b = rb[idx]
            sa = a.mean()/a.std(ddof=1); sb = b.mean()/b.std(ddof=1)
            cnt += (sa <= sb)
        return cnt/n
    for _, name, _, _ in focus:
        kw, rv, cv = ALL[name]
        log(f"\n################ DETAIL: {name}  {kw}" + ('' if best else '   (NOTE: does NOT qualify; shown for completeness only)'))
        for pn_ in PANELS:
            log(f"  bootstrap {pn_} (20d blocks, 3000 draws): P(Sharpe not better than base) = {boot(rv[pn_]['r'], base[pn_]['r']):.3f}" +
                (f";  vs exposure-matched control = {boot(rv[pn_]['r'], cv[pn_]['r']):.3f}" if cv[pn_] else ''))
        # neighbour grid
        log("  neighbour grid (CAGR / Sharpe / maxDD; real | proxy):")
        keys = [k for k, v in kw.items() if isinstance(v, float)]
        grid = []
        for k in keys:
            for d in (-.05, -.025, 0, .025, .05) if k in ('A', 'D', 'D2', 'D3', 'vt') else (-.1, -.05, 0, .05, .1) if k == 'capA' else (0,):
                kk = dict(kw); kk[k] = round(kw[k]+d, 4); grid.append((f"{k}={kk[k]}", kk))
        for lab, kk in grid:
            rr = [run(PANELS[x], **kk) for x in PANELS]; parts = []
            for (r_, t_, ds_, e_) in rr:
                c_, s_, m_ = prof(r_); parts.append(f"{c_*100:5.1f}% / {s_:.3f} / {m_*100:5.1f}% (expo {e_:.2f})")
            log(f"    {lab:<14}  real {parts[0]}   |  proxy {parts[1]}")
        # episodes
        log("  episodes (return over window; maxDD within window) variant | base | control, proxy panel unless noted:")
        def win(r, ds, a, b):
            m = np.array([a <= d <= b for d in ds]); x = r[m]; nav = np.cumprod(1+x); return nav[-1]-1, (nav/np.maximum.accumulate(nav)-1).min()
        for pn_, wins in (('proxy', [('2001-2002', '2001-01-01', '2002-12-31'), ('2008', '2008-01-01', '2008-12-31'), ('2022', '2022-01-01', '2022-12-31')]), ('real', [('2022', '2022-01-01', '2022-12-31')])):
            for lab, a, b in wins:
                o = []
                for rr_, ds_ in ((rv[pn_]['r'], rv[pn_]['ds']), (base[pn_]['r'], base[pn_]['ds']), (cv[pn_]['r'] if cv[pn_] else None, base[pn_]['ds'])):
                    o.append('n/a' if rr_ is None else "%+.1f%% / DD %.1f%%" % tuple(np.array(win(rr_, ds_, a, b))*100))
                log(f"    {pn_:<5} {lab:<10} variant {o[0]:<20} base {o[1]:<20} control {o[2]}")
