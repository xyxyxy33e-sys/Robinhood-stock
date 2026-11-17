"""hl2: audit extension of harness_live (own copy, nothing in the repo is edited).

hl_orig_copy.py is paper-track/harness_live.py verbatim except (a) HERE hard-wired and (b) the assert on
S.DGATE_HIGH_ENABLED removed (L1 was switched OFF on 2026-11-17, so the original no longer imports).
This module adds the hooks the audit needs, by copying HL.build() and adding keyword arguments:

  cfg_over     dict merged into the MC cfg (d_gate, d_ladder, vol, trim, fast, d_buffer, ...)
  rows_over    dict letter -> (core, tqqq, qld, xlu, cash) replacing rows of cfg['rows'] (B, E)
  d3_row       (core, tqqq, qld) replacing S.D_LADDER_ROWS['D3'] for the weight call only
  deep_share   deep-E QQQ share of the cash leg (default state.DEEP_E_CASH_SHARE; 0 = off)
  panic_share  VIX-panic QQQ share (default state.VIX_PANIC_CASH_SHARE; 0 = off)
  sleeve       'vixy' (live) | 'vixm' (the 10-08..11-10 sleeve: VIXM from data/vixm_daily.csv + live_closes) | 'none'
  d2_off       True = sleeve blocked in ungated D2 (state.VIXM_OFF_D_ZONES, 10-22)
  carry        None | int: state.A_SPELL_GAP_CARRY used when the held trim votes are computed (signals recomputed)
  ew_lag       sessions the QQEW path is delayed in the breadth signal (look-ahead test)
  vix, vix3m   dict date->close overriding harness VIX / VIX3M for the latch and the panic latch
  band         drift band (default state.REBALANCE_DRIFT_BAND)
and run2() = HL.run_live_detail with the band hook.  The mechanics are otherwise identical to harness_live.build().
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hl_orig_copy as HL
H, MC, S = HL.H, HL.MC, HL.S

DEF2 = dict(HL.DEFAULTS, cfg_over={}, rows_over=None, d3_row=None, deep_share=S.DEEP_E_CASH_SHARE,
            panic_share=S.VIX_PANIC_CASH_SHARE, sleeve='vixy', d2_off=True, carry=None, ew_lag=0, ew_freeze=None, qnoise=None, vix=None, vix3m=None)

_SG = {}
def signals2(l1, use_live, carry, ew_lag, ew_freeze=None, qnoise=None):
    if carry is None and not ew_lag and ew_freeze is None and qnoise is None:
        return HL.signals(l1, use_live)
    k = (bool(l1), bool(use_live), carry, ew_lag, ew_freeze) if qnoise is None else None
    if k is None or k not in _SG:
        p = H.p
        ew = p['ew'].copy()
        if ew_freeze is not None:
            ew = np.where(np.array(H.PD) > ew_freeze, 0.0, ew)
        if ew_lag:
            ew = np.concatenate([np.zeros(ew_lag), ew[:-ew_lag]])
        old = S.A_SPELL_GAP_CARRY
        if carry is not None: S.A_SPELL_GAP_CARRY = carry
        try:
            qp = 100 * np.cumprod(1 + p['qqq']); ep = 100 * np.cumprod(1 + ew)
            if qnoise is not None:                       # (seed, sd_qqq, sd_qqew): signals read the level x (1+e); returns stay true
                rr = np.random.default_rng(qnoise[0]); qp = qp * (1 + rr.normal(0, qnoise[1], len(qp))); ep = ep * (1 + rr.normal(0, qnoise[2], len(ep)))
            sg = MC.signals(qp[None], ep[None])
        finally:
            S.A_SPELL_GAP_CARRY = old
        if l1:
            Hh, _ = HL.highs(use_live); s200 = MC._sma(HL.Q0[None], 200)[0]
            with np.errstate(invalid='ignore'):
                g = (sg['macro'][0] == 3) & (Hh / s200 - 1 < S.D_GATE_GAP200)
            sg['gate_g'] = g[None]; sg['gate'] = sg['gate_b'] | sg['gate_g']
        res = (sg, H.slice_sig(sg, H.OFF))
        if k is None: return res
        _SG[k] = res
    return _SG[k]


def panic_series(ds, vix, share):
    on = False; out = np.zeros(len(ds))
    for i, d in enumerate(ds):
        v = vix.get(d, np.nan)
        if not np.isnan(v):
            if on and v < S.VIX_PANIC_OFF: on = False
            elif not on and v >= S.VIX_PANIC_ON: on = True
        out[i] = share if on else 0.0
    return out


_VX = {}
def vixm_leg(ds):
    px = MC._load('vixm_daily.csv')                       # harness-patched: file + live_closes VIXM (ends 2026-11-13)
    x = MC._rets(px, ds); x[0] = 0.0
    return x, min(px)


def build2(track='real', **kw):
    bad = set(kw) - set(DEF2)
    if bad: raise TypeError('unknown override %s' % sorted(bad))
    c = dict(DEF2); c.update(kw)
    real = HL._track(track); pn = H.pr if real else H.p; ds = pn['dates']
    sgp, sgr = signals2(c['l1'], c['use_live_highs'], c['carry'], c['ew_lag'], c['ew_freeze'], c['qnoise']); sg = sgr if real else sgp
    cfg = dict(H.CUR, a_base=tuple(c['a_split']), gross_cap=None, vol_target=c['vol_target'])
    cfg.update(c['cfg_over'])
    if c['rows_over']:
        cfg['rows'] = dict(cfg['rows'], **c['rows_over'])
    saved = dict(S.D_LADDER_ROWS)
    if c['d3_row'] is not None: S.D_LADDER_ROWS['D3'] = tuple(c['d3_row'])
    try:
        w5 = MC.target_weights(sg, cfg)
    finally:
        S.D_LADDER_ROWS.clear(); S.D_LADDER_ROWS.update(saved)
    eff = MC._eff(sg, cfg)[0]; gate = MC._gate(sg, cfg)[0]; z = MC._zone(sg, cfg)[0]
    amask = eff == 0
    gx = np.array(S.GROSS_EXPOSURE)
    gross = (w5[0, :, :4] * gx).sum(-1)
    capv = np.full(len(ds), np.inf if c['gross_cap'] is None else float(c['gross_cap']))
    f = np.where(gross > capv, capv / np.maximum(gross, 1e-12), 1.0)
    w5[0, :, :4] *= f[:, None]; w5[0, :, 4] = 1.0 - w5[0, :, :4].sum(-1)
    key = MC.regime_key(sg, cfg).astype(np.int64)[0]
    cash = w5[0, :, 4].copy()
    legs = [pn['core'], pn['tqqq'], pn['qld'], pn['xlu']]; W = [w5[0, :, i] for i in range(4)]
    names = ['core', 'tqqq', 'qld', 'xlu']; used = np.zeros_like(cash)
    vixd = c['vix'] if c['vix'] is not None else H.VIX
    vix3d = c['vix3m'] if c['vix3m'] is not None else H.VIX3M
    if c['sleeve'] != 'none':
        if c['sleeve'] == 'vixy':
            vr, vfirst = HL._vixy_rets(ds, c['vixy_source']); share = S.VIXM_CASH_SHARE if c['sleeve_share'] is None else c['sleeve_share']
        else:
            vr, vfirst = vixm_leg(ds); share = 0.75 if c['sleeve_share'] == S.VIXM_CASH_SHARE else c['sleeve_share']
        vd = {d: (None if np.isnan(v) else float(v)) for d, v in zip(ds, sg['vol'][0])}
        vx = S.vixm_series(ds, vixd, vix3d, vd)
        latch = np.array([bool(vx.get(d, {}).get('allowed')) for d in ds])
        allowed = latch & np.array([d >= vfirst for d in ds])
        if c['d2_off']: allowed &= ~((eff == 3) & ~gate & (z == 2))
        if share and (real or c['sleeve_proxy']):
            v = np.where(allowed, cash * share, 0.0)
            legs.append(vr); W.append(v); names.append('vixy'); used = v.copy(); key = key + allowed.astype(np.int64) * 100000
    deep = ((eff == 4) & (np.nan_to_num(sg['gaps'][200][0]) <= S.DEEP_E_GAP200)).astype(float) * c['deep_share']
    pan = panic_series(ds, vixd, c['panic_share'])
    for j, sh in enumerate((deep, pan)):
        x = np.minimum(cash * sh, cash - used); used = used + x
        legs.append(pn['qqq']); W.append(x); names.append('qqq'); key = key + (sh > 0).astype(np.int64) * (10 ** (6 + j))
    legs.append(pn['cash']); W.append(cash - used); names.append('cash')
    W = np.stack(W, -1); L = np.stack(legs, -1)
    return dict(W=W, L=L, key=key, names=names, ds=ds, real=real, eff=eff, gate=gate, cfg=c, cfgmc=cfg)


def run2(track='real', d0=None, d1='2099', band=None, cost=None, **kw):
    b = build2(track, **kw); ds, real = b['ds'], b['real']; W, key, L = b['W'], b['key'], b['L']
    d0 = d0 or ('2015-11-02' if real else '2001-01-02')
    s0 = next(i for i, d in enumerate(ds) if d >= d0); e = max(i for i, d in enumerate(ds) if d <= d1)
    old = MC.COST
    if cost is not None: MC.COST = cost
    try:
        r, tr = MC.run_strategy(W[None, :e + 1], key[None, :e + 1], L[None, :e + 1], s0,
                                band=S.REBALANCE_DRIFT_BAND if band is None else band)
    finally:
        MC.COST = old
    n = e - s0
    return dict(r=r[0], ds=ds[s0 + 1:e + 1], tpy=tr[0] / (n / 252), W=W[s0:e], names=b['names'], eff=b['eff'][s0:e], gate=b['gate'][s0:e])


def stat(r):
    nav = np.cumprod(1 + r); pk = np.maximum.accumulate(np.concatenate([[1.0], nav]))[1:]
    sd = r.std(ddof=1) * 252 ** 0.5
    return dict(c=nav[-1] ** (252 / len(r)) - 1, sh=r.mean() * 252 / sd, m=(nav / pk - 1).min())


def fm(s):
    return '%5.1f%% / %.3f / %6.1f%%' % (s['c'] * 100, s['sh'], s['m'] * 100)
