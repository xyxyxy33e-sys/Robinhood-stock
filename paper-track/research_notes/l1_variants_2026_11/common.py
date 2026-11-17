"""Shared pieces for the L1-variants study (research only). Uses harness_live untouched; custom D-gate signals are injected
by replacing HL.signals (the engine only reads sig['gate_g'] / sig['gate'] for the gate)."""
import csv, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); PT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, PT)
import harness_live as HL
H, MC, S = HL.H, HL.MC, HL.S
PD, RD, OFF = H.PD, H.RD, H.OFF
T = len(PD)
Q0 = HL.Q0
sig0 = H.sig                         # proxy-axis signals (close-only gate_g)
S200 = MC._sma(Q0[None], 200)[0]
macro = sig0['macro'][0]; eff = sig0['eff'][0]; pct = sig0['pct'][0]
gate_b = sig0['gate_b'][0]
D_ = macro == 3
VIX = np.array([H.VIX.get(d, np.nan) for d in PD])
Q0RAW = np.array([MC._load('qqq_long_history.csv')[d] for d in PD])   # raw close (incl. live closes) ; scale = Q0/raw
SC = Q0 / Q0RAW

def hi_map(use_live=True): return HL._hi_map(use_live)
def full_highs():
    return HL.highs(True)[0]            # normalised, >= Q0

# AlphaVantage daily lows (for typical-price arms): file below, filled by fetch step
LOWS_CSV = os.path.join(HERE, 'qqq_daily_lows_robinhood_2026_09_11.csv')
def lows_norm():
    m = {r['d']: float(r['l']) for r in csv.DictReader(open(os.path.join(MC.DATA, 'qqq_ohlc.csv')))}
    if os.path.exists(LOWS_CSV):
        for r in csv.DictReader(open(LOWS_CSV)):
            if r['d'] > '2026-09-04': m[r['d']] = float(r['l'])
    lo = np.array([m.get(d, np.nan) for d in PD]) * SC
    return np.where(np.isnan(lo), Q0, np.minimum(lo, Q0))

def make_sig(gate_g_open_mask_shut):
    """gate_g_shut: bool array over proxy axis (already unmasked: True = gap half shuts the gate); masked by macro==3 here."""
    sg = dict(H.sig)
    g = (macro == 3) & gate_g_shut_arr(gate_g_open_mask_shut)
    sg['gate_g'] = g[None]; sg['gate'] = H.sig['gate_b'] | g[None]
    return sg
def gate_g_shut_arr(x): return np.asarray(x, bool)

_CUR = {}
def install(shut, scale=None):
    """Make HL.signals return the signals with the gap half = `shut` (bool over proxy axis); scale = optional (T,) risky-leg multiplier."""
    sg = make_sig(shut)
    sr = H.slice_sig(sg, H.OFF)
    HL.signals = lambda l1, use_live=True: (sg, sr)
    _CUR['scale'] = scale

def run(track, shut, d0=None, d1='2099', lag=0, scale=None, **kw):
    install(shut)
    if scale is None:
        return HL.run_live_detail(track, d0, d1, lag, None, l1=True, **kw)
    return run_scaled(track, d0, d1, lag, scale, **kw)

# --- HALF arm: copy of HL.build with a risky-leg scale vector (applied after vol target, before cap) ---------------
def build_scaled(track, scale, **kw):
    c = dict(HL.DEFAULTS); c.update(kw); c['l1'] = True
    real = HL._track(track); pn = H.pr if real else H.p; ds = pn['dates']
    sgp, sgr = HL.signals(True); sg = sgr if real else sgp
    sc = scale[OFF:] if real else scale
    cfg = dict(H.CUR, a_base=tuple(c['a_split']), gross_cap=None, vol_target=c['vol_target'])
    w5 = MC.target_weights(sg, cfg)
    effv = MC._eff(sg, cfg)[0]; gate = MC._gate(sg, cfg)[0]; z = MC._zone(sg, cfg)[0]
    w5[0, :, :4] *= sc[:, None]; w5[0, :, 4] = 1.0 - w5[0, :, :4].sum(-1)
    amask = effv == 0
    gx = np.array(S.GROSS_EXPOSURE)
    gross = (w5[0, :, :4] * gx).sum(-1)
    capv = np.full(len(ds), float(c['gross_cap']))
    f = np.where(gross > capv, capv / np.maximum(gross, 1e-12), 1.0)
    w5[0, :, :4] *= f[:, None]; w5[0, :, 4] = 1.0 - w5[0, :, :4].sum(-1)
    key = MC.regime_key(sg, cfg).astype(np.int64)[0] + (sc < 1).astype(np.int64) * 10**8
    cash = w5[0, :, 4].copy()
    legs = [pn['core'], pn['tqqq'], pn['qld'], pn['xlu']]; W = [w5[0, :, i] for i in range(4)]
    names = ['core', 'tqqq', 'qld', 'xlu']; used = np.zeros_like(cash)
    vr, vfirst = HL._vixy_rets(ds, c['vixy_source'])
    if c['sleeve_share'] and (real or c['sleeve_proxy']):
        allowed = HL._latch(real, sg) & ~((effv == 3) & ~gate & (z == 2)) & np.array([d >= vfirst for d in ds])
        v = np.where(allowed, cash * c['sleeve_share'], 0.0)
        legs.append(vr); W.append(v); names.append('vixy'); used = v.copy(); key = key + allowed.astype(np.int64) * 100000
    deep = ((effv == 4) & (np.nan_to_num(sg['gaps'][200][0]) <= S.DEEP_E_GAP200)).astype(float) * S.DEEP_E_CASH_SHARE
    pan = H.panic_series(ds)
    for j, sh in enumerate((deep, pan)):
        x = np.minimum(cash * sh, cash - used); used = used + x
        legs.append(pn['qqq']); W.append(x); names.append('qqq'); key = key + (sh > 0).astype(np.int64) * (10 ** (6 + j))
    legs.append(pn['cash']); W.append(cash - used); names.append('cash')
    W = np.stack(W, -1); L = np.stack(legs, -1)
    eqg = [i for i, n in enumerate(names) if n not in ('vixy', 'cash')]
    eqgross = (W[:, eqg] * np.array([dict(core=1, tqqq=3, qld=2, xlu=1, qqq=1)[names[i]] for i in eqg])).sum(1)
    return dict(W=W, L=L, key=key, names=names, ds=ds, real=real, eff=effv, gate=gate, gross=eqgross, a_mask=amask, cfg=c)

def run_scaled(track, d0, d1, lag, scale, **kw):
    orig = HL.build
    HL.build = lambda tr, **k: build_scaled(tr, scale, **k)
    try: return HL.run_live_detail(track, d0, d1, lag, None, **kw)
    finally: HL.build = orig
