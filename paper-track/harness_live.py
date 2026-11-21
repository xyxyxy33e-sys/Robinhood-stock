"""harness_live: the LIVE design (2026-11-11 and later) on the verified monte_carlo engine.

review_2026_11/harness.py (untouched, still reproduces the old studies) predates three live changes;
this module imports it and adds them as the default:
  1. gross cap 2.0x          (state.GROSS_CAP / apply_gross_cap; MC engine cfg['gross_cap'])
  2. volatility sleeve = VIXY at 35% of the cash leg (state.VIXM_INSTRUMENT / VIXM_CASH_SHARE),
     full VIXY history 2011- so it also runs on the proxy panel (off before 2011-01-04)
  3. D gate read on the day's high "L1" (state.DGATE_HIGH_ENABLED / gate_gap200): the gap-to-200d half of
     the gate reads max(close, high) against the 200-day SMA; the trade still fills at the close.

    import harness_live as HL
    r, ds, tpy = HL.run_live('real')                      # same outputs as harness.run
    r, ds, tpy = HL.run_live('proxy', d0='2010-01-04', l1=False, a_split=(0.5, 0.5), gross_cap=1.75)
    d = HL.run_live_detail('real', a_split=(0.2, 0.8))    # dict: r, ds, tpy, W, names, eff, gross, a_mask, ...

Overrides accepted by run_live / run_live_detail (defaults in LIVE_CFG): l1, gross_cap, a_cap, a_split, a_instr,
sleeve_share, sleeve_proxy, vol_target, risky_scale, vixy_source, use_live_highs, plus d0, d1, lag, cost.
Research only; nothing here touches the live code or data.
Fail-loud (2026-11-17 audit): highs() raises when a panel date has no high; the VIXY latch and VIXY returns raise instead of skipping / forward-filling.
"""
import csv, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'review_2026_11'))
import harness as H
from harness import MC, S

VIXY_FULL = os.path.join(HERE, 'research_notes', 'vixy_calm_2026_11', 'vixy_yahoo_full.csv')
VIXY_OLD = os.path.join(HERE, 'research_notes', 'vixm_followups_2026_11', 'vixy_daily.csv')
HIGHS_AV = os.path.join(HERE, 'research_notes', 'leverage_a_2026_11', 'qqq_highs_av_2026_09_11.csv')
HIGHS_LIVE = os.path.join(MC.DATA, 'qqq_highs.csv')

# ---------------------------------------------------------------------------------------------
# every setting of the live design and where it comes from
# L1 (DGATE_HIGH_ENABLED) was switched off on 2026-11-17; the 'l1' default below follows state.py.
assert S.GROSS_CAP_ENABLED and S.VIXM_OVERLAY_ENABLED and S.VIXM_INSTRUMENT == 'VIXY'
LIVE_CFG = {
    'gross_cap': (S.GROSS_CAP, 'state.GROSS_CAP (GROSS_CAP_ENABLED); applied after the vol target to the 4 risky legs with state.GROSS_EXPOSURE (1,3,2,1); rest to cash'),
    'a_cap': (None, 'research hook, not live: separate cap for state A only (D keeps gross_cap)'),
    'a_split': (tuple(S.A_BASE_FROM_SESSION[1]), 'state.A_BASE_FROM_SESSION (2026-11-06): SPMO/TQQQ 40/60 base; trim v2 (state.A_TRIM / EXTENSION_*) on top, via MC cfg a_base'),
    'a_instr': ('TQQQ', "state A's satellite leg; 'QLD' is a research hook (TQQQ weight moved to QLD, same $)"),
    'sleeve_share': (S.VIXM_CASH_SHARE, 'state.VIXM_CASH_SHARE: VIXY share of the cash leg when the latch allows (state.VIXM_INSTRUMENT = VIXY; harness default was VIXM 75%)'),
    'sleeve_proxy': (True, 'research choice: the sleeve also runs on the proxy panel from 2011-01-04 (first VIXY print) with the same latch; off before. False = sleeve off on proxy (old harness)'),
    'l1': (S.DGATE_HIGH_ENABLED, 'state.DGATE_HIGH_ENABLED / gate_gap200: gap200 half of the D gate reads max(close, high); fill at the close'),
    'vol_target': (S.VOL_TARGET_PA, 'state.VOL_TARGET_PA 20%; estimator max(10d, 30d) via H.CUR vol=max10_30 (state.VOL_ESTIMATOR_MAX_ENABLED)'),
    'risky_scale': (1.0, 'research hook, not live: flat multiplier on the 4 risky legs after vol target and cap (matched de-lever)'),
    'vixy_source': ('full', "'full' = research_notes/vixy_calm_2026_11/vixy_yahoo_full.csv close_split_adj (2011-); 'old' = vixm_followups vixy_daily.csv + live_closes (what harness-era studies used)"),
    'use_live_highs': (True, "True = highs complete: data/qqq_ohlc.csv to 2026-09-04, then research_notes/leverage_a_2026_11/qqq_highs_av_2026_09_11.csv (full-day highs 2026-09-08..11-10, AlphaVantage QQQ daily), then data/qqq_highs.csv (live 15:50 highs 2026-11-11..). "
                         "False = qqq_ohlc.csv only (50 sessions after 2026-09-04 read the close): this is what the recorded L1 references (52.9%/2.136, STRATEGY.md 53.0%/2.139) had"),
    # inherited unchanged from harness.CUR / monte_carlo.LIVE (live values)
    'inherited': ('H.CUR', 'B 50/50 SPMO/BOXX, C 100% SPMO, D ladder state.D_LADDER_ROWS + zone buffer state.D_ZONE_BUFFER, E/F cash, fast 20/100, trim v2, '
                           'band state.REBALANCE_DRIFT_BAND 5%, cost MC.COST 2bp/side, deep-E state.DEEP_E_* (held through F while the gap stays <= -5%, DEEP_E_HOLD_THROUGH_F), VIX-panic state.VIX_PANIC_*, VIXM latch state.vixm_series (+ off in ungated D2)'),
}
DEFAULTS = {k: v[0] for k, v in LIVE_CFG.items() if k != 'inherited'}

# ---------------------------------------------------------------------------------------------
# daily highs on the proxy axis, scaled to the normalised QQQ path the signals see (as research_notes hlall)
_P, _PD = H.p, H.PD
Q0 = 100 * np.cumprod(1 + _P['qqq'])
_craw = MC._load('qqq_long_history.csv'); _scale = Q0 / np.array([_craw[d] for d in _PD])
def _hi_map(use_live):
    m = {r['d']: float(r['h']) for r in csv.DictReader(open(os.path.join(MC.DATA, 'qqq_ohlc.csv')))}
    if use_live:
        for r in csv.DictReader(open(HIGHS_AV)): m[r['d']] = float(r['h'])
        for r in csv.DictReader(open(HIGHS_LIVE)): m[r['date']] = float(r['high_to_run'])
    return m
def highs(use_live=True):
    m = _hi_map(use_live)
    miss = [d for d in _PD if d not in m]
    if miss:   # research must not read the CLOSE where a high is missing (the 2026-11 L1 error: 50 sessions did)
        raise ValueError(f"harness_live.highs: {len(miss)} panel dates have no high (first {miss[0]}, last {miss[-1]}); "
                         f"refresh data/qqq_ohlc.csv (paper-track/refresh_data.py) or extend HIGHS_AV / data/qqq_highs.csv")
    h = np.array([m[d] for d in _PD]) * _scale
    return np.maximum(h, Q0), 0

_SG = {}
def signals(l1, use_live=True):
    """(proxy-axis signal dict, real-axis signal dict); L1 recomputes only the gap200 half of the gate."""
    k = (bool(l1), bool(use_live))
    if k not in _SG:
        sg = dict(H.sig)
        if l1:
            Hh, _ = highs(use_live)
            s200 = MC._sma(Q0[None], 200)[0]
            with np.errstate(invalid='ignore'):
                g = (H.sig['macro'][0] == 3) & (Hh / s200 - 1 < S.D_GATE_GAP200)
            gate_g = g[None]; sg['gate_g'] = gate_g; sg['gate'] = H.sig['gate_b'] | gate_g
        _SG[k] = (sg, H.slice_sig(sg, H.OFF))
    return _SG[k]

def _vixy_rets(ds, source):
    if source == 'full':
        px = {r['d']: float(r['close_split_adj']) for r in csv.DictReader(open(VIXY_FULL))}
    else:
        px = {r['d']: float(r['c']) for r in csv.DictReader(open(VIXY_OLD))}
        for r in H.LC:
            if r['date'] > max(px) and r.get('VIXY'): px[r['date']] = float(r['VIXY'])
    x = MC._rets(px, ds, True, 'VIXY series (%s)' % source); x[0] = 0.0     # raises if the file ends before the panel
    return x, min(px)

def _vixy_first():
    return min(r['d'] for r in csv.DictReader(open(VIXY_FULL)))

_VXA = {}
def _latch(real, sg):
    ds = H.RD if real else H.PD
    if real not in _VXA:
        vd = {d: (None if np.isnan(v) else float(v)) for d, v in zip(ds, sg['vol'][0])}
        vx = S.vixm_series(ds, H.VIX, H.VIX3M, vd)
        # no panel date from the sleeve's first VIXY print on may be skipped by state.vixm_series (the proxy panel has no VIX3M
        # before 2007-12, and the sleeve is off before 2011-01-04 anyway)
        H.assert_latch_covers(ds, vx, 'harness_live VIXY latch', from_date=_vixy_first())
        _VXA[real] = np.array([bool(vx.get(d, {}).get('allowed')) for d in ds])
    return _VXA[real]

def _track(track):
    if track in (True, 'real'): return True
    if track in (False, 'proxy'): return False
    raise ValueError(track)

def build(track='real', **kw):
    cfg_in = dict(DEFAULTS); bad = set(kw) - set(cfg_in)
    if bad: raise TypeError('unknown override %s' % sorted(bad))
    cfg_in.update(kw); c = cfg_in
    real = _track(track); pn = H.pr if real else H.p; ds = pn['dates']
    sgp, sgr = signals(c['l1'], c['use_live_highs']); sg = sgr if real else sgp
    cfg = dict(H.CUR, a_base=tuple(c['a_split']), gross_cap=None, vol_target=c['vol_target'])
    w5 = MC.target_weights(sg, cfg)                          # (1,T,5) after vol target, no cap
    eff = MC._eff(sg, cfg)[0]; gate = MC._gate(sg, cfg)[0]; z = MC._zone(sg, cfg)[0]
    amask = eff == 0
    if c['a_instr'] == 'QLD':
        w5[0, :, 2] += np.where(amask, w5[0, :, 1], 0.0); w5[0, :, 1] = np.where(amask, 0.0, w5[0, :, 1])
    elif c['a_instr'] != 'TQQQ': raise ValueError(c['a_instr'])
    gx = np.array(S.GROSS_EXPOSURE)
    gross = (w5[0, :, :4] * gx).sum(-1)
    capv = np.full(len(ds), np.inf if c['gross_cap'] is None else float(c['gross_cap']))
    if c['a_cap'] is not None: capv = np.where(amask, min(capv[0], float(c['a_cap'])), capv)
    f = np.where(gross > capv, capv / np.maximum(gross, 1e-12), 1.0) * c['risky_scale']
    w5[0, :, :4] *= f[:, None]; w5[0, :, 4] = 1.0 - w5[0, :, :4].sum(-1)
    key = MC.regime_key(sg, cfg).astype(np.int64)[0]
    cash = w5[0, :, 4].copy()
    legs = [pn['core'], pn['tqqq'], pn['qld'], pn['xlu']]; W = [w5[0, :, i] for i in range(4)]
    names = ['core', 'tqqq', 'qld', 'xlu']; used = np.zeros_like(cash)
    vr, vfirst = _vixy_rets(ds, c['vixy_source'])
    if c['sleeve_share'] and (real or c['sleeve_proxy']):
        allowed = _latch(real, sg) & ~((eff == 3) & ~gate & (z == 2)) & np.array([d >= vfirst for d in ds])
        v = np.where(allowed, cash * c['sleeve_share'], 0.0)
        legs.append(vr); W.append(v); names.append('vixy'); used = v.copy(); key = key + allowed.astype(np.int64) * 100000
    gp = np.nan_to_num(sg['gaps'][200][0], nan=9.0)
    # live from 2026-11-23 (state.deep_e_series, deep_e_lines): enter on effective E at the entry line (-6%), then
    # held in any state (DEEP_E_HOLD_THROUGH_F) while the gap stays at or below the exit line (-4%)
    en, ex = S.DEEP_E_ENTRY_GAP200, S.DEEP_E_EXIT_GAP200
    on = np.zeros(len(eff), bool); st = False
    for i in range(len(eff)):
        if st: st = gp[i] <= ex and (S.DEEP_E_HOLD_THROUGH_F or eff[i] == 4)
        else:  st = eff[i] == 4 and gp[i] <= en
        on[i] = st
    deep = on.astype(float) * S.DEEP_E_CASH_SHARE
    pan = H.panic_series(ds)
    for j, sh in enumerate((deep, pan)):
        x = np.minimum(cash * sh, cash - used); used = used + x
        legs.append(pn['qqq']); W.append(x); names.append('qqq'); key = key + (sh > 0).astype(np.int64) * (10 ** (6 + j))
    legs.append(pn['cash']); W.append(cash - used); names.append('cash')
    W = np.stack(W, -1); L = np.stack(legs, -1)
    eqgross = (W[:, [i for i, n in enumerate(names) if n not in ('vixy', 'cash')]] *
               np.array([dict(core=1, tqqq=3, qld=2, xlu=1, qqq=1)[n] for n in names if n not in ('vixy', 'cash')])).sum(1)
    return dict(W=W, L=L, key=key, names=names, ds=ds, real=real, eff=eff, gate=gate, gross=eqgross, a_mask=amask, cfg=c)

def run_live_detail(track='real', d0=None, d1='2099', lag=0, cost=None, **kw):
    b = build(track, **kw); ds, real = b['ds'], b['real']; W, key, L = b['W'], b['key'], b['L']
    d0 = d0 or ('2015-11-02' if real else '2001-01-02')
    if lag:
        W = np.concatenate([np.repeat(W[:1], lag, 0), W[:-lag]], 0); key = np.concatenate([np.repeat(key[:1], lag), key[:-lag]])
    s0 = next(i for i, d in enumerate(ds) if d >= d0); e = max(i for i, d in enumerate(ds) if d <= d1)
    old = MC.COST
    if cost is not None: MC.COST = cost
    try: r, tr = MC.run_strategy(W[None, :e + 1], key[None, :e + 1], L[None, :e + 1], s0)
    finally: MC.COST = old
    n = e - s0
    return dict(r=r[0], ds=ds[s0 + 1:e + 1], tpy=tr[0] / (n / 252), W=W[s0:e], names=b['names'], eff=b['eff'][s0:e],
                gross=b['gross'][s0:e], a_mask=b['a_mask'][s0:e], gate=b['gate'][s0:e], s0=s0, e=e, cfg=b['cfg'])

def run_live(track='real', d0=None, d1='2099', lag=0, cost=None, **overrides):
    """Same outputs as harness.run: (daily returns, dates, trades per year), live design by default."""
    d = run_live_detail(track, d0, d1, lag, cost, **overrides)
    return d['r'], d['ds'], d['tpy']

stats, fmt, cash_for = H.stats, H.fmt, H.cash_for

if __name__ == '__main__':
    for t in ('real', 'proxy'):
        r, ds, tpy = run_live(t); print(t, ds[0], ds[-1], fmt(stats(r, cash_for(ds, t == 'real'))), '%.0f trades/yr' % tpy)
