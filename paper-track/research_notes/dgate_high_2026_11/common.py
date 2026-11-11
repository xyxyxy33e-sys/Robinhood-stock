"""Intraday high/low reaction test on the D gate. Research only."""
import csv, os, sys
import numpy as np
HERE = '/home/user/Robinhood-stock/paper-track'; sys.path.insert(0, HERE)
import monte_carlo as MC, state as S, vol_curve as VC
SP = '/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad'
MC.DATA = SP + '/sb_data'
S.A_BASE_FROM_SESSION = ('2026-11-06', (0.40, 0.60))
NEW = dict(MC.LIVE, name='11 Nov', a_base=(0.40, 0.60), vol='max10_30')
COST = MC.COST

p = MC.load_panel('proxy'); dates = p['dates']
qfull = 100*np.cumprod(1+p['qqq'])
sig = MC.signals(qfull[None], (100*np.cumprod(1+p['ew']))[None])
pr = MC.load_panel('real'); off = dates.index(pr['dates'][0])
sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items()}
rd = pr['dates']
vix, _ = VC.history('VIX'); vix3m, _ = VC.history('VIX3M')
vol30 = {d: (None if np.isnan(v) else float(v)) for d, v in zip(rd, sr['vol'][0])}
VX = S.vixm_series(rd, vix, vix3m, vol30)
eff_r = MC._eff(sr, NEW)[0]
allowed = np.array([bool(VX.get(d, {}).get('allowed')) for d in rd])
allowed_raw = allowed.copy()
allowed &= ~((eff_r == 3) & ~sr['gate'][0].astype(bool) & (sr['zone'][0] == 2))
_px = {r['d']: float(r['c']) for r in csv.DictReader(open(os.path.join(MC.DATA, 'vixm_daily.csv')))}
vixm_r = MC._rets(_px, rd); vixm_r[0] = 0.0

def qlegs(sg, ds, cfg):
    e = MC._eff(sg, cfg)[0]; g = np.nan_to_num(sg['gaps'][200][0])
    deep = ((e == 4) & (g <= -0.05)).astype(float)*0.5
    on = False; pan = np.zeros(len(ds))
    for i, d in enumerate(ds):
        v = vix.get(d, np.nan)
        if not np.isnan(v):
            if on and v < 25: on = False
            elif not on and v >= 30: on = True
        pan[i] = 0.25 if on else 0.0
    return deep, pan

def run(sg, pn, d0, cfg, qq, vixm=True):
    ds = pn['dates']; s0 = next(i for i, d in enumerate(ds) if d >= d0)
    w5 = MC.target_weights(sg, cfg); key = MC.regime_key(sg, cfg).astype(np.int64)
    cash = w5[0, :, 4].copy()
    legs = [pn['core'], pn['tqqq'], pn['qld'], pn['xlu']]; W = [w5[0, :, i] for i in range(4)]
    used = np.zeros_like(cash)
    if pn is pr and vixm:
        legs.append(vixm_r); W.append(np.where(allowed, cash*S.VIXM_CASH_SHARE, 0.0)); used = W[-1].copy()
        key = key + allowed[None].astype(np.int64)*100000
    if qq:
        deep, pan = qlegs(sg, ds, cfg)
        for j, sh in enumerate((deep, pan)):
            x = np.minimum(cash*sh, cash-used); used = used + x
            legs.append(pn['qqq']); W.append(x); key = key + (sh[None] > 0).astype(np.int64)*(10**(6+j))
    legs.append(pn['cash']); W.append(cash-used)
    r, tr = MC.run_strategy(np.stack(W, -1)[None], key, np.stack(legs, -1)[None], s0)
    return r[0], tr[0], ds[s0:], s0

# ---- OHLC on the proxy date axis
ohlc = {r['d']: r for r in csv.DictReader(open(MC.DATA + '/qqq_ohlc.csv'))}
def col(k): return np.array([float(ohlc[d][k]) if d in ohlc else np.nan for d in dates])
O, H, L = col('o'), col('h'), col('l')
dset = set(dates)
C = np.array([float(r['c']) for r in csv.DictReader(open(MC.DATA + '/qqq_long_history.csv')) if r['d'] in dset])
assert len(C) == len(dates)
def sma(n): return MC._sma(C[None], n)[0]
S50, S100, S150, S200 = sma(50), sma(100), sma(150), sma(200)
def line(Sn, n, k):      # price p where p = k*SMA_n(incl p)  =>  p(1-k/n) = k*sum_{n-1}/n
    s = n*Sn - C
    return k*s/n/(1 - k/n)
PL = line(S200, 200, 1.02)      # gate line, SMA includes that day's own price
P50 = line(S50, 50, 1.01)       # above this the intraday state would be C, not D
def gapz(Sn, n):
    s = n*Sn - C
    return lambda pp: pp/((s+pp)/n) - 1
vfull = np.fmax(sig['vol'][0], np.where(np.isnan(sig['vol'][0]), np.nan, sig['vol10'][0]))
multf = np.where(np.isnan(vfull) | (vfull <= 0), 1.0, np.minimum(1.0, S.VOL_TARGET_PA/np.where(vfull > 0, vfull, 1)))
G100 = gapz(S100, 100)(PL); G150 = gapz(S150, 150)(PL)
ZONEF = np.where(G100 > 0, 1, np.where(G150 > 0, 2, 3))      # zone at the line price
LEV = np.array([1.0, 3.0, 2.0, 0.0])      # core(SPMO ~1x / QQQ), TQQQ 3x, QLD 2x, XLU 0

FILL = lambda o,h,pl: max(o,pl)
def variant(sg, off_, pn, d0, flags, qq=True, vixm=True):
    sg = dict(sg); cfg = NEW
    T = sg['gate'].shape[1]
    if 'V4' in flags:
        gg = sg['gaps'][200]
        prev = np.concatenate([[np.nan], gg[0, :-1]])[None]
        g4 = (sg['macro'] == 3) & ((gg < S.D_GATE_GAP200) | (prev < S.D_GATE_GAP200))
        sg['gate_g'] = g4; sg['gate'] = sg['gate_b'] | g4
    r, tr, ds, s0 = run(sg, pn, d0, cfg, qq, vixm)
    w5 = MC.target_weights(sg, cfg)[0]
    eff = MC._eff(sg, cfg)[0]; gate = sg['gate'][0].astype(bool); pct = sg['pct'][0]
    risk = w5[:, :4].sum(1)
    sl = slice(off_, off_+T)
    o_, h_, l_, c_, pl, p50, mult, zone = O[sl], H[sl], L[sl], C[sl], PL[sl], P50[sl], multf[sl], ZONEF[sl]
    extra = np.zeros(T); xcost = np.zeros(T); ntr = np.zeros(T)
    ev1, ev2 = [], []
    for t in range(max(1, s0+1), T):
        if np.isnan(h_[t]) or np.isnan(pl[t]): continue
        # V1 / V5: buy when the high touches the gate line (held weights were cash because of the gap gate)
        if ('V1' in flags or 'V5' in flags) and risk[t-1] < 1e-9 and not (pct[t-1] < S.D_GATE_BREADTH_PCT) \
                and h_[t] >= pl[t] and pl[t] < p50[t]:
            from_D = eff[t-1] == 3 and gate[t-1]
            from_E = 'V5' in flags and eff[t-1] >= 4
            if from_D or from_E:
                F = FILL(o_[t], h_[t], pl[t]); x = c_[t]/F - 1
                row = np.array(S.D_LADDER_ROWS['D%d' % zone[t]])*mult[t-1]
                extra[t] += float((row*LEV[:3]).sum()*x)
                fc = risk[t] < 1e-9                       # close ended back under the line / still gated
                if fc: xcost[t] += COST*4*row.sum(); ntr[t] += 2
                ev1.append((t, fc))
        # V2: sell when the low breaks the gate line (held D weights, ungated)
        if 'V2' in flags and eff[t-1] == 3 and risk[t-1] > 1e-9 and l_[t] < pl[t]:
            F = min(o_[t], pl[t])
            extra[t] += float((w5[t-1, :4]*LEV).sum()*(F - c_[t])/c_[t-1])
            fc = risk[t] > 1e-9                           # close back above the line: we are re-buying
            if fc: xcost[t] += COST*2*(risk[t-1]+risk[t]); ntr[t] += 2
            ev2.append((t, fc))
    day = s0 + 1 + np.arange(len(r))
    r2 = (1+r)*(1+extra[day]) - 1 - xcost[day]
    tr2 = tr + ntr.sum()
    f5_1 = sum(1 for (t, fc) in ev1 if not fc and any(risk[t+j] < 1e-9 for j in range(1, 6) if t+j < T))
    f5_2 = sum(1 for (t, fc) in ev2 if not fc and any(risk[t+j] > 1e-9 for j in range(1, 6) if t+j < T))
    return r2, tr2, ds, dict(ev1=ev1, ev2=ev2, f5_1=f5_1, f5_2=f5_2, gate=gate, eff=eff, s0=s0)

def sharpe(r): return r.mean()/r.std(ddof=1)*252**.5
def st(r, ds, tr, split):
    nav = np.cumprod(1+r); dd = (nav/np.maximum.accumulate(nav)-1).min()
    yrs = len(r)/252; cut = next(i for i, d in enumerate(ds[1:]) if d >= split)
    return dict(cagr=nav[-1]**(1/yrs)-1, sh=sharpe(r), dd=dd, tpy=tr/yrs, sh1=sharpe(r[:cut]), sh2=sharpe(r[cut:]))
def clears(info):
    g, e = info['gate'], info['eff']
    return sum(1 for t in range(info['s0']+1, len(g)) if g[t-1] and not g[t] and e[t] == 3)

