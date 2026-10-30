"""Owner (2026-10-30): "try to maximize sharpe, allow to tweak anything". Research only.

PRE-REGISTERED before any run (2026-10-30, not edited after).
Search: coordinate descent from the live design, two full passes, knobs in the order below; each knob
tries every listed value with the others held, keeps the best (a tie keeps the current value).
Objective: Sharpe (mean/sd, as the repo reports it) on the proxy panel 2001-01-02..2015-10-30 -- the
era no live parameter was fit in -- at 4 bp per side, VIXM out (no VIXM data before 2015).
Knobs and values (live value first):
  a_base     40/60, 25/75, 30/70, 50/50, 60/40, 75/25
  vol_target 0.20, 0.15, 0.175, 0.225, 0.25, 0.30
  vol        max10_30, 30
  B row      75/25, 100/0, 60/40, 50/50 (SPMO/TQQQ)
  C row      100% SPMO, 75/25 SPMO/TQQQ, 50% SPMO / 50% cash
  D1 row     50 SPMO/50 QLD, 100 SPMO, 50 SPMO/50 TQQQ, 100 QLD
  D2 row     50 TQQQ/50 QLD, 100 QLD, 50 SPMO/50 QLD, 100 TQQQ
  D3 row     100 TQQQ, 50 TQQQ/50 QLD, 100 QLD, 40/60 SPMO/TQQQ
  d_gate     on, off
  d_buffer   0.005, 0, 0.01
  band       0.05, 0.03, 0.08
  trim       v2, none
  fast       on, off
(E/F stay cash: E/F alternatives were tested at length before -- sqqq_hedge_study.py,
spmo_consistency_study.py.)
Validation, judged once on the winner: real ETFs 2015-11-02..2026-10-29 WITH VIXM (as live), at 4 and
20 bp, plus the full proxy 2001-2026. ADOPT only if the winner beats live on ALL of: real Sharpe at 4 bp
AND 20 bp by >= 0.03; full-proxy Sharpe >= live; real max DD no more than 1 pp deeper; and the real
block bootstrap P(winner not better) <= 0.20. Otherwise report and keep live. Also reported: the
best real-validation Sharpe among configs the search visited (selection-biased, for scale only).
"""
import csv, os, sys, itertools
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import monte_carlo as MC, state as S, vol_curve as VC
from block_bootstrap import boot
LOG = open(os.path.join(HERE, 'research_notes', 'sharpe_search_run.log'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); LOG.write(s + '\n'); LOG.flush()
LC = list(csv.DictReader(open(os.path.join(MC.DATA, 'live_closes.csv'))))
EXT = {'qqq_long_history.csv': 'QQQ', 'QQEW_daily_ext.csv': 'QQEW', 'spmo_ohlc.csv': 'SPMO', 'tqqq_ohlc.csv': 'TQQQ', 'qld_ohlc.csv': 'QLD', 'xlu_ohlc.csv': 'XLU'}
_o = MC._load
def _l(name, dcol='d', ccol='c'):
    out = _o(name, dcol, ccol)
    if name in EXT or name == 'spy_long_history.csv':
        last = max(out); v = out[last]
        for r in LC:
            if r['date'] > last:
                if name in EXT and r[EXT[name]]: out[r['date']] = float(r[EXT[name]])
                elif name not in EXT: out[r['date']] = v
    return out
MC._load = _l
p = MC.load_panel('proxy'); PD = p['dates']
sig = MC.signals((100 * np.cumprod(1 + p['qqq']))[None], (100 * np.cumprod(1 + p['ew']))[None])
pr = MC.load_panel('real'); RD = pr['dates']; off = PD.index(RD[0])
sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items()}
vix, _ = VC.history('VIX'); vix3m, _ = VC.history('VIX3M')
VX = S.vixm_series(RD, vix, vix3m, {d: (None if np.isnan(v) else float(v)) for d, v in zip(RD, sr['vol'][0])})
VXA = np.array([bool(VX.get(d, {}).get('allowed')) for d in RD])
vm = {r['d']: float(r['c']) for r in csv.DictReader(open(os.path.join(MC.DATA, 'vixm_daily.csv')))}
for r in LC:
    if r['date'] > max(vm) and r['VIXM']: vm[r['date']] = float(r['VIXM'])
VR = MC._rets(vm, RD); VR[0] = 0.0
LIVE_LADDER = dict(S.D_LADDER_ROWS)

KNOBS = [
    ('a_base', [(0.40, 0.60), (0.25, 0.75), (0.30, 0.70), (0.50, 0.50), (0.60, 0.40), (0.75, 0.25)]),
    ('vol_target', [0.20, 0.15, 0.175, 0.225, 0.25, 0.30]),
    ('vol', ['max10_30', '30']),
    ('B', [(0.75, 0.25), (1.0, 0.0), (0.60, 0.40), (0.50, 0.50)]),
    ('C', [(1.0, 0, 0, 0, 0), (0.75, 0.25, 0, 0, 0), (0.5, 0, 0, 0, 0.5)]),
    ('D1', [(0.5, 0.0, 0.5), (1.0, 0.0, 0.0), (0.5, 0.5, 0.0), (0.0, 0.0, 1.0)]),
    ('D2', [(0.0, 0.5, 0.5), (0.0, 0.0, 1.0), (0.5, 0.0, 0.5), (0.0, 1.0, 0.0)]),
    ('D3', [(0.0, 1.0, 0.0), (0.0, 0.5, 0.5), (0.0, 0.0, 1.0), (0.4, 0.6, 0.0)]),
    ('d_gate', [True, False]),
    ('d_buffer', [0.005, 0.0, 0.01]),
    ('band', [0.05, 0.03, 0.08]),
    ('trim', ['v2', 'none']),
    ('fast', [True, False]),
]
def build(c):
    cfg = dict(MC.LIVE, a_base=c['a_base'], vol=c['vol'], vol_target=c['vol_target'], d_gate=c['d_gate'],
               d_buffer=c['d_buffer'], trim=c['trim'], fast=c['fast'],
               rows=dict(MC.LIVE['rows'], B=(c['B'][0], c['B'][1], 0, 0, 0), C=c['C']))
    return cfg, {'D1': c['D1'], 'D2': c['D2'], 'D3': c['D3']}
def weights(sg, c):
    cfg, lad = build(c)
    S.D_LADDER_ROWS.update(lad)
    try:
        w = MC.target_weights(sg, cfg); k = MC.regime_key(sg, cfg)
    finally:
        S.D_LADDER_ROWS.update(LIVE_LADDER)
    return cfg, w, k
def st(r):
    nav = np.cumprod(1 + r); dd = nav / np.maximum.accumulate(np.concatenate([[1.0], nav]))[1:] - 1
    return dict(c=nav[-1] ** (252 / len(r)) - 1, sh=r.mean() * 252 / (r.std(ddof=1) * 252 ** 0.5), m=dd.min(), a=dd.mean())
P0 = next(i for i, d in enumerate(PD) if d >= '2001-01-02'); P1 = max(i for i, d in enumerate(PD) if d <= '2015-10-30')
LP = np.stack([p['core'], p['tqqq'], p['qld'], p['xlu'], p['cash']], -1)[None]
def proxy(c, bp=4, end=True):
    MC.COST = bp / 1e4
    cfg, w, k = weights(sig, c)
    r = MC.run_strategy(w, k, LP, P0, band=c['band'])[0][0]
    MC.COST = 0.0004
    return r[:P1 - P0] if end else r
R0 = next(i for i, d in enumerate(RD) if d >= '2015-11-02')
def real(c, bp=4):
    MC.COST = bp / 1e4
    cfg, w5, k = weights(sr, c)
    eff = MC._eff(sr, cfg)[0]; gate = MC._gate(sr, cfg)[0]; z = MC._zone(sr, cfg)[0]
    allowed = VXA & ~((eff == 3) & ~gate & (z == 2))
    v = np.where(allowed, w5[0, :, 4] * S.VIXM_CASH_SHARE, 0.0)
    w6 = np.concatenate([w5[..., :4], v[None, :, None], (w5[0, :, 4] - v)[None, :, None]], -1)
    L6 = np.stack([pr['core'], pr['tqqq'], pr['qld'], pr['xlu'], VR, pr['cash']], -1)[None]
    r = MC.run_strategy(w6, k + allowed[None].astype(int) * 100000, L6, R0, band=c['band'])[0][0]
    MC.COST = 0.0004
    return r

live = {k: v[0] for k, v in KNOBS}
cache = {}
def obj(c):
    key = tuple(sorted((k, str(v)) for k, v in c.items()))
    if key not in cache: cache[key] = st(proxy(c))['sh']
    return cache[key]
log('=' * 100); log('sharpe_search (2026-10-30): coordinate descent on proxy 2001-2015, validated on real 2015-2026'); log('=' * 100)
log(f"  live objective (proxy 2001-2015 Sharpe, 4 bp): {obj(live):.4f}")
cur = dict(live)
for ps in (1, 2):
    for name, vals in KNOBS:
        scores = {}
        for v in vals:
            c = dict(cur, **{name: v}); scores[str(v)] = (obj(c), v)
        best = max(scores.values(), key=lambda x: x[0])
        if best[0] > obj(cur) + 1e-9: cur[name] = best[1]
        log(f"  pass {ps} {name:<10} " + '  '.join(f"{k}:{s:.3f}" for k, (s, _) in scores.items()) + f"   -> {cur[name]}  (obj {obj(cur):.4f})")
log(f"\n  configs evaluated: {len(cache)}")
log("  WINNER vs LIVE (changed knobs): " + ', '.join(f"{k} {live[k]} -> {cur[k]}" for k in live if cur[k] != live[k]))

log("\n  VALIDATION")
res = {}
for nm, c in (('live', live), ('winner', cur)):
    for bp in (4, 20):
        res[(nm, 'real', bp)] = real(c, bp)
    res[(nm, 'proxy')] = proxy(c, 4, end=False)
    res[(nm, 'hold')] = proxy(c, 4)
for nm in ('live', 'winner'):
    a4, a20, fp, ho = st(res[(nm, 'real', 4)]), st(res[(nm, 'real', 20)]), st(res[(nm, 'proxy')]), st(res[(nm, 'hold')])
    log(f"  {nm:<7} real 4bp {a4['c']*100:.1f}% / {a4['sh']:.3f} / {a4['m']*100:.1f}% (avg DD {a4['a']*100:.1f}%) | real 20bp {a20['c']*100:.1f}% / {a20['sh']:.3f} / {a20['m']*100:.1f}%"
        f" | proxy 2001-26 {fp['c']*100:.1f}% / {fp['sh']:.3f} / {fp['m']*100:.1f}% | search window {ho['c']*100:.1f}% / {ho['sh']:.3f} / {ho['m']*100:.1f}%")
cash = pr['cash'][R0 + 1:]
*_, s1, s2, pb = boot(list(res[('winner', 'real', 4)] - cash), list(res[('live', 'real', 4)] - cash), 60, seed=4242)
W4, L4, W20, L20 = (st(res[k]) for k in (('winner', 'real', 4), ('live', 'real', 4), ('winner', 'real', 20), ('live', 'real', 20)))
FW, FL = st(res[('winner', 'proxy')]), st(res[('live', 'proxy')])
ok = W4['sh'] >= L4['sh'] + 0.03 and W20['sh'] >= L20['sh'] + 0.03 and FW['sh'] >= FL['sh'] and W4['m'] >= L4['m'] - 0.01 and pb <= 0.20
log(f"\n  PRE-REGISTERED VERDICT: real dSh {W4['sh']-L4['sh']:+.3f} (4bp) / {W20['sh']-L20['sh']:+.3f} (20bp), proxy dSh {FW['sh']-FL['sh']:+.3f}, "
    f"real dDD {(W4['m']-L4['m'])*100:+.1f} pp, bootstrap [{s1:+.3f}, {s2:+.3f}] P(not better) {pb:.2f}  => {'ADOPT' if ok else 'keep live'}")
