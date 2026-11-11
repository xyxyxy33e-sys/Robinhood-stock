"""Shared harness for the 2026-11-11 review tests (items 2-8 of the independent review).

The current live design as of the 2026-11-11 session, on the verified monte_carlo.py engine:
A 40/60 + trim v2, B 50% SPMO / 50% cash, C 100% SPMO, D ladder + D gate + 0.5% zone buffer,
E/F cash, max(10d,30d) vol target 20%, 5% band, 2 bp per side (MC.COST), VIXM sleeve (75% of the
cash leg when the latch allows, off in ungated D2), deep-E QQQ leg (50% of the cash leg in E with
QQQ <= -5% vs its 200-day), VIX-panic QQQ leg (25% of the cash leg while the VIX latch >= 30 / < 25).
Leg stacking follows research_notes/deep_e_2026_11/strategy_page_gen.py, plus d_buffer (live has it;
that script left it at 0). Real-ETF files are extended with data/live_closes.csv; SPY is carried flat
past its file (unused). Hooks let each test change one thing.
"""
import csv, os, sys
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE)
import monte_carlo as MC, state as S, vol_curve as VC

LC = list(csv.DictReader(open(os.path.join(MC.DATA, 'live_closes.csv'))))
EXT = {'qqq_long_history.csv': 'QQQ', 'QQEW_daily_ext.csv': 'QQEW', 'spmo_ohlc.csv': 'SPMO', 'tqqq_ohlc.csv': 'TQQQ',
       'qld_ohlc.csv': 'QLD', 'xlu_ohlc.csv': 'XLU', 'vixm_daily.csv': 'VIXM'}
_orig = MC._load
def _load(name, dcol='d', ccol='c'):
    out = _orig(name, dcol, ccol)
    if name in EXT or name == 'spy_long_history.csv':
        last = max(out); v = out[last]
        for r in LC:
            if r['date'] > last:
                if name in EXT and r.get(EXT[name]): out[r['date']] = float(r[EXT[name]])
                elif name not in EXT: out[r['date']] = v
    return out
MC._load = _load

S.A_BASE_FROM_SESSION = ('2026-11-06', (0.40, 0.60))
CUR = dict(MC.LIVE, name='11 Nov live', a_base=(0.40, 0.60), vol='max10_30', d_buffer=S.D_ZONE_BUFFER)
assert CUR['rows']['B'] == (0.50, 0, 0, 0, 0.50) and S.D_LADDER_ROWS['D3'] == (0.0, 1.0, 0.0)

p = MC.load_panel('proxy'); PD = p['dates']
sig = MC.signals((100 * np.cumprod(1 + p['qqq']))[None], (100 * np.cumprod(1 + p['ew']))[None])
pr = MC.load_panel('real'); RD = pr['dates']; OFF = PD.index(RD[0])
def slice_sig(sg, off):
    return {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sg.items()
            if not isinstance(k, tuple)}
sr = slice_sig(sig, OFF)
VIX, _ = VC.history('VIX'); VIX3M, _ = VC.history('VIX3M')
_vx = S.vixm_series(RD, VIX, VIX3M, {d: (None if np.isnan(v) else float(v)) for d, v in zip(RD, sr['vol'][0])})
VXA = np.array([bool(_vx.get(d, {}).get('allowed')) for d in RD])
VIXM_R = MC._rets(MC._load('vixm_daily.csv'), RD); VIXM_R[0] = 0.0

def panic_series(ds):
    on = False; out = np.zeros(len(ds))
    for i, d in enumerate(ds):
        v = VIX.get(d, np.nan)
        if not np.isnan(v):
            if on and v < S.VIX_PANIC_OFF: on = False
            elif not on and v >= S.VIX_PANIC_ON: on = True
        out[i] = S.VIX_PANIC_CASH_SHARE if on else 0.0
    return out

def weights(sg, ds, real, cfg=CUR, vixm=True, vixm_share=None, vixm_cap=None, vixm_ret=None, qlegs=True,
            w5_hook=None):
    """(W (T,k), legs (T,k), key (T,)) for the current design; hooks change one thing.
    w5_hook(w5, sg) -> w5 lets a test rewrite the 5-leg target (gross cap, soft gate, ensemble)."""
    pn = pr if real else p
    w5 = MC.target_weights(sg, cfg)
    if w5_hook is not None: w5 = w5_hook(w5, sg)
    key = MC.regime_key(sg, cfg).astype(np.int64)[0]
    cash = w5[0, :, 4].copy()
    legs = [pn['core'], pn['tqqq'], pn['qld'], pn['xlu']]; W = [w5[0, :, i] for i in range(4)]
    used = np.zeros_like(cash)
    if real and vixm:
        eff = MC._eff(sg, cfg)[0]; gate = MC._gate(sg, cfg)[0]; z = MC._zone(sg, cfg)[0]
        allowed = VXA & ~((eff == 3) & ~gate & (z == 2))
        v = np.where(allowed, cash * (S.VIXM_CASH_SHARE if vixm_share is None else vixm_share), 0.0)
        if vixm_cap is not None: v = np.minimum(v, vixm_cap)
        legs.append(VIXM_R if vixm_ret is None else vixm_ret); W.append(v); used = v.copy()
        key = key + allowed.astype(np.int64) * 100000
    if qlegs:
        e = MC._eff(sg, cfg)[0]; g = np.nan_to_num(sg['gaps'][200][0])
        deep = ((e == 4) & (g <= S.DEEP_E_GAP200)).astype(float) * S.DEEP_E_CASH_SHARE
        pan = panic_series(ds)
        for j, sh in enumerate((deep, pan)):
            x = np.minimum(cash * sh, cash - used); used = used + x
            legs.append(pn['qqq']); W.append(x); key = key + (sh > 0).astype(np.int64) * (10 ** (6 + j))
    legs.append(pn['cash']); W.append(cash - used)
    return np.stack(W, -1), np.stack(legs, -1), key

def run(real=True, d0=None, d1='2099', lag=0, cost=None, **kw):
    """Daily returns r (aligned to ds[s0+1:e+1]) and dates; lag = sessions of execution delay."""
    pn = pr if real else p; ds = pn['dates']; sg = sr if real else sig
    d0 = d0 or ('2015-11-02' if real else '2001-01-02')
    W, L, key = weights(sg, ds, real, **kw)
    if lag:
        W = np.concatenate([np.repeat(W[:1], lag, 0), W[:-lag]], 0); key = np.concatenate([np.repeat(key[:1], lag), key[:-lag]])
    s0 = next(i for i, d in enumerate(ds) if d >= d0); e = max(i for i, d in enumerate(ds) if d <= d1)
    old = MC.COST
    if cost is not None: MC.COST = cost
    try:
        r, tr = MC.run_strategy(W[None, :e + 1], key[None, :e + 1], L[None, :e + 1], s0)
    finally:
        MC.COST = old
    return r[0], ds[s0 + 1:e + 1], tr[0] / ((e - s0) / 252)

def stats(r, cash=None):
    nav = np.cumprod(1 + r); dd = nav / np.maximum.accumulate(np.concatenate([[1.0], nav]))[1:] - 1
    v = r.std(ddof=1) * 252 ** 0.5
    out = dict(c=nav[-1] ** (252 / len(r)) - 1, sh=r.mean() * 252 / v, m=dd.min(), a=dd.mean(), v=v)
    if cash is not None: out['ex'] = (r - cash).mean() * 252 / v
    return out

def cash_for(ds, real=True):
    pn = pr if real else p; idx = {d: i for i, d in enumerate(pn['dates'])}
    return np.array([pn['cash'][idx[d]] for d in ds])

def fmt(x):
    return f"{x['c']*100:6.1f}% / {x['sh']:.3f}" + (f" (ex {x['ex']:.3f})" if 'ex' in x else '') + f" / {x['m']*100:6.1f}%"

if __name__ == '__main__':
    for real in (True, False):
        r, ds, tpy = run(real)
        print('real' if real else 'proxy', ds[0], ds[-1], fmt(stats(r, cash_for(ds, real))), f"{tpy:.0f} trades/yr")
    r, ds, _ = run(False, d1='2015-10-30'); print('holdout', fmt(stats(r, cash_for(ds, False))))
