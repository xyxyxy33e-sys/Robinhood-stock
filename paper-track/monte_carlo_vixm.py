"""Monte Carlo of the VIXM cash sleeve (live since 2026-10-08), the one live
overlay monte_carlo.py leaves out.

The sleeve (state.py VIXM section): a latch turns ON when VIX closes below 18
with VIX <= VIX3M and OFF when VIX closes above VIX3M; while ON and QQQ's plain
30-day realized vol is >= 20%, 75% of the cash leg is VIXM; it is sold early
when VIX falls 25% below its high since entry and not re-bought until the
stress reading resets. A change in `allowed` forces a rebalance.

How it is bootstrapped. VIX and VIX3M are LEVELS, so resampling them day by day
would invent spikes at every block boundary. Instead the latch (ON/OFF, and the
day it switched on) is computed on the real VIX/VIX3M history and carried as an
attribute of each sampled day, together with that day's VIX level and VIXM
return. The stress test, the fade and the 'killed' state are then replayed on
each synthetic path, against that path's own QQQ vol -- so a path's VIXM
decisions depend on its own volatility, and blocks keep the curve coherent.

Panels: `real` (2015-10..2026-08, real ETFs) and `proxy2011` (2011-01..2026-08,
QQQ core + synthetic 2x/3x, real VIXM). VIXM does not exist before 2011.
Base: the 2026-10-22 live design (MC.LIVE).

    python3 paper-track/monte_carlo_vixm.py --verify
    python3 paper-track/monte_carlo_vixm.py --paths 1000
"""
import argparse
import csv
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import monte_carlo as MC  # noqa: E402
import monte_carlo_improve as I  # noqa: E402
S = MC.S
DATA = MC.DATA


def _fred(name, col):
    out = {}
    for r in csv.DictReader(open(os.path.join(DATA, name))):
        try:
            out[r['observation_date']] = float(r[col])
        except (ValueError, KeyError):
            pass
    return out


def latch_history():
    """{date: (on, switched_on_today, vix)} from the real VIX/VIX3M closes
    (FRED VIXCLS / VXVCLS), the ON/OFF part of state.vixm_series."""
    vix, v3 = _fred('vixcls_full.csv', 'VIXCLS'), _fred('vxvcls.csv', 'VXVCLS')
    on = False; out = {}
    for d in sorted(set(vix) & set(v3)):
        v, r = vix[d], vix[d] / v3[d]
        sw = False
        if not on and v < S.VIXM_ENTRY_VIX and r <= S.VIXM_EXIT_RATIO:
            on, sw = True, True
        elif on and r > S.VIXM_EXIT_RATIO:
            on = False
        out[d] = (on, sw, v)
    return out


def load_panel(kind):
    base = MC.load_panel('real' if kind == 'real' else 'proxy')
    vx = {r['d']: float(r['c']) for r in csv.DictReader(open(os.path.join(DATA, 'vixm_daily.csv')))}
    lh = latch_history()
    first = '2015-10-12' if kind == 'real' else '2011-01-04'
    keep = [i for i, d in enumerate(base['dates']) if d >= first and d <= max(vx)]
    p = {k: (v[keep[0]:keep[-1] + 1] if k != 'dates' else v[keep[0]:keep[-1] + 1]) for k, v in base.items()}
    dates = p['dates']
    p['vixm'] = MC._rets(vx, dates); p['vixm'][0] = 0.0
    on = np.zeros(len(dates), bool); sw = np.zeros(len(dates), bool); lvl = np.zeros(len(dates))
    last = (False, False, 20.0)
    for i, d in enumerate(dates):
        cur = lh.get(d)
        if cur is None:
            cur = (last[0], False, last[2])          # no index print: latch unchanged
        on[i], sw[i], lvl[i] = cur; last = cur
    p['vix_on'] = on.astype(float); p['vix_sw'] = sw.astype(float); p['vix'] = lvl
    return p


def allowed_path(vol30, on, sw, vix):
    """Replay stress / fade / killed (state.vixm_series) along each row."""
    P, T = vol30.shape
    killed = np.zeros(P, bool); hi = np.full(P, np.nan); out = np.zeros((P, T), bool)
    for t in range(T):
        o = on[:, t] > 0.5
        reset = sw[:, t] > 0.5
        killed = np.where(reset, False, killed); hi = np.where(reset, np.nan, hi)
        stress = ~np.isnan(vol30[:, t]) & (vol30[:, t] >= S.VIXM_MIN_VOL)
        killed = np.where(~stress, False, killed); hi = np.where(~stress, np.nan, hi)
        a = o & ~killed & stress
        v = vix[:, t]
        hi = np.where(a, np.where(np.isnan(hi), v, np.fmax(hi, v)), hi)
        fade = a & (v <= hi * (1 - S.VIXM_FADE))
        killed = killed | fade
        out[:, t] = a & ~fade
    return out


def weights6(sig, cfg, allowed):
    w5 = MC.target_weights(sig, cfg)
    w6 = np.concatenate([w5[..., :4], np.zeros(w5.shape[:-1] + (2,))], -1)
    v = np.where(allowed, w5[..., 4] * S.VIXM_CASH_SHARE, 0.0)
    w6[..., 4] = v; w6[..., 5] = w5[..., 4] - v
    key = MC.regime_key(sig, cfg) * 2 + allowed
    return w6, key


def run6(sig, g, cfg, allowed, lag=0, vixm=True):
    if vixm:
        w, k = weights6(sig, cfg, allowed)
        legs = np.stack([g['core'], g['tqqq'], g['qld'], g['xlu'], g['vixm'], g['cash']], -1)
    else:
        w, k = MC.target_weights(sig, cfg), MC.regime_key(sig, cfg)
        legs = np.stack([g['core'], g['tqqq'], g['qld'], g['xlu'], g['cash']], -1)
    if lag:
        w = np.concatenate([w[:, :lag], w[:, :-lag]], 1); k = np.concatenate([k[:, :lag], k[:, :-lag]], 1)
    r, trades = MC.run_strategy(w, k, legs, MC.WARMUP, band=cfg['band'], stubs=cfg['stubs'])
    m = MC.stats(r); m['trades'] = trades
    m['vixm_share'] = (w[:, MC.WARMUP:-1, 4] if vixm else np.zeros((1, 1))).mean()
    return m


def verify():
    """Replay on the real history vs state.vixm_series with the plain 30d vol."""
    p = load_panel('real'); d = p['dates']
    full = MC.load_panel('proxy'); off = full['dates'].index(d[0])
    qpx = 100 * np.cumprod(1 + full['qqq'])
    sig = MC.signals(qpx[None], (100 * np.cumprod(1 + full['ew']))[None])
    mine = allowed_path(sig['vol'][:, off:], p['vix_on'][None], p['vix_sw'][None], p['vix'][None])[0]
    vix, v3 = _fred('vixcls_full.csv', 'VIXCLS'), _fred('vxvcls.csv', 'VXVCLS')
    px = dict(zip(full['dates'], qpx)); qd = full['dates']
    vols = {x: S.realized_vol(qd, px, as_of=x, lookback=S.VOL_LOOKBACK_DAYS) for x in d}
    ref = S.vixm_series(sorted(set(vix) & set(v3)), vix, v3, vols)
    bad = sum(1 for i, x in enumerate(d) if x in ref and bool(ref[x]['allowed']) != bool(mine[i]))
    n = sum(1 for x in d if x in ref)
    print(f"VIXM allowed vs state.vixm_series: {bad} mismatches over {n} sessions; "
          f"allowed on {mine.mean()*100:.1f}% of sessions")


def cell(kind, panel, P, years, block, seed):
    rng = np.random.default_rng(seed)
    T = MC.WARMUP + int(round(252 * years)) + 1
    src = np.arange(1, len(panel['dates']))
    idx = src[MC.bootstrap_idx(rng, len(src), P, T, block)]
    g = {k: panel[k][idx] for k in panel if k != 'dates'}
    sig = MC.signals(100 * np.cumprod(1 + g['qqq'], 1), 100 * np.cumprod(1 + g['ew'], 1))
    allowed = allowed_path(sig['vol'], g['vix_on'], g['vix_sw'], g['vix'])
    base = run6(sig, g, MC.LIVE, allowed, vixm=False)
    withv = run6(sig, g, MC.LIVE, allowed)
    base_l = run6(sig, g, MC.LIVE, allowed, lag=1, vixm=False)
    withv_l = run6(sig, g, MC.LIVE, allowed, lag=1)
    out = {'VIXM sleeve': I.compare(withv, base, years), 'VIXM sleeve, 1-session lag': I.compare(withv_l, base_l, years)}
    out['_vixm_share'] = float(withv['vixm_share']); out['_allowed'] = float(allowed[:, MC.WARMUP:].mean())
    out['_base'] = dict(cagr=float(np.median(base['cagr'])), sharpe=float(np.median(base['sharpe'])), mdd=float(np.median(base['mdd'])))
    out['_with'] = dict(cagr=float(np.median(withv['cagr'])), sharpe=float(np.median(withv['sharpe'])), mdd=float(np.median(withv['mdd'])),
                        mdd_p5=float(np.percentile(withv['mdd'], 5)), base_mdd_p5=float(np.percentile(base['mdd'], 5)))
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--paths', type=int, default=1000)
    ap.add_argument('--seed', type=int, default=20261021)
    ap.add_argument('--out', default=os.path.join(HERE, 'research_notes', 'monte_carlo_vixm_run.log'))
    a = ap.parse_args(argv)
    if a.verify:
        verify(); return
    res = {}
    for kind in ('real', 'proxy2011'):
        panel = load_panel(kind)
        for L in (20, 60, 120, 250):
            t0 = time.time(); res[f"{kind}/L{L}"] = c = cell(kind, panel, a.paths, 10, L, a.seed + L)
            print(f"{kind}/L{L} [{time.time()-t0:.0f}s] allowed {c['_allowed']*100:.1f}% of days, VIXM avg {c['_vixm_share']*100:.1f}% of book", flush=True)
    lines = ["| cell | live (no VIXM) median CAGR / Sharpe / MaxDD | with VIXM | P(Sharpe better) | P(MaxDD shallower) | median ΔCAGR | Δ p5 MaxDD | same, 1-session lag: P(Sharpe) / ΔCAGR |",
             "|---|---|---|---|---|---|---|---|"]
    for k, c in res.items():
        b, w, v, l = c['_base'], c['_with'], c['VIXM sleeve'], c['VIXM sleeve, 1-session lag']
        lines.append(f"| {k} | {b['cagr']*100:.1f}% / {b['sharpe']:.2f} / {b['mdd']*100:.1f}% | {w['cagr']*100:.1f}% / {w['sharpe']:.2f} / {w['mdd']*100:.1f}% | "
                     f"{v['p_sharpe']*100:.0f}% | {v['p_dd']*100:.0f}% | {v['d_cagr']*100:+.2f} pp | {(w['mdd_p5']-w['base_mdd_p5'])*100:+.1f} pp | "
                     f"{l['p_sharpe']*100:.0f}% / {l['d_cagr']*100:+.2f} pp |")
    txt = "\n".join(lines); print(txt)
    with open(a.out, 'w') as fh:
        fh.write(f"# VIXM sleeve Monte Carlo {time.strftime('%Y-%m-%d %H:%M')} paths={a.paths}\n\n" + txt + "\n\n```json\n" + json.dumps(res, indent=1) + "\n```\n")


if __name__ == '__main__':
    main(sys.argv[1:])
