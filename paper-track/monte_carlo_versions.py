"""Monte Carlo of every past release of the live design, on the SAME bootstrapped
paths, so each release is compared with the current one path by path.

Releases, from STRATEGY.md's change log (rows before the vol target,
(core, tqqq, qld, xlu, cash)):
  2026-09-02  A 70/30, B 75/25, C core, D 85% QLD, E 50% XLU, F cash; no fast
              overlay, no trim; 30d vol, 3% band, no zero-leg sweep
  2026-09-07  A 50/50, D 100% QLD, 20/100 fast overlay, graded trim v1 (x2/3,
              x1/3, x0), max(10,30) vol estimator, 3% band, zero-leg sweep
  2026-09-09  as 09-07 with the plain 30d estimator and the 5% band
  2026-09-19  + state-D gate, E 100% cash
  2026-09-23  trim v2 (held votes, TQQQ out) + 3-session carry; A 50/50 and A 40/60
  2026-10-09  live: A 25/75 + D ladder
plus one control: the live A 25/75 with D at 100% QLD (no ladder).
Not modelled in any release: VIXM sleeve, gold, deposits/margin, taxes.

    python3 paper-track/monte_carlo_versions.py --history     # single-path check vs STRATEGY.md
    python3 paper-track/monte_carlo_versions.py --paths 1000
"""
import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import monte_carlo as MC  # noqa: E402

CASH = (0, 0, 0, 0, 1)
E_XLU = (0, 0, 0, 0.5, 0.5)
V0902 = dict(MC.LIVE, name='2026-09-02', a_base=(0.70, 0.30),
             rows={'B': (0.75, 0.25, 0, 0, 0), 'C': (1, 0, 0, 0, 0), 'D': (0, 0, 0.85, 0, 0.15), 'E': E_XLU, 'F': CASH},
             fast=False, trim='none', d_gate=False, d_ladder=False, vol='30', band=0.03, stubs=False)
V0907 = dict(MC.LIVE, name='2026-09-07', a_base=(0.50, 0.50),
             rows={'B': (0.75, 0.25, 0, 0, 0), 'C': (1, 0, 0, 0, 0), 'D': (0, 0, 1, 0, 0), 'E': E_XLU, 'F': CASH},
             fast=True, trim='v1', trim_step=1 / 3, d_gate=False, d_ladder=False, vol='max10_30', band=0.03)
V0909 = dict(V0907, name='2026-09-09', vol='30', band=0.05)
V0919 = dict(V0909, name='2026-09-19', d_gate=True, rows=dict(V0909['rows'], E=CASH))
V0923_50 = dict(V0919, name='2026-09-23 A 50/50', trim='v2')
V0923_40 = dict(V0923_50, name='2026-09-23 A 40/60', a_base=(0.40, 0.60))
LIVE = dict(MC.LIVE, name='2026-10-09 live')
NOLADDER = dict(LIVE, name='control: live without D ladder', d_ladder=False)
DESIGNS = [V0902, V0907, V0909, V0919, V0923_50, V0923_40, LIVE, NOLADDER]

# STRATEGY.md's own single-path figures (CAGR, Sharpe, MaxDD), where it states them.
# Proxy figures run from 2000-07, real from 2015-11; real 10-09 includes VIXM.
SPEC = {'2026-09-02': ((0.1569, 0.752, -0.324), (0.2325, 1.061, -0.267)),
        '2026-09-07': ((0.2212, 0.938, -0.328), None),   # research_notes/BRIEFING.md standing figure
        '2026-09-09': ((0.2218, 0.913, -0.336), (0.2966, 1.145, -0.329)),
        '2026-09-19': ((0.2546, 1.071, -0.270), (0.3730, 1.475, -0.186)),
        '2026-09-23 A 50/50': ((0.2611, 1.194, -0.219), (0.4103, 1.797, -0.178)),
        '2026-09-23 A 40/60': ((0.2778, 1.199, -0.226), (0.4418, 1.804, -0.187)),
        '2026-10-09 live': ((0.327, 1.275, -0.277), (0.547, 1.977, -0.194))}


def run(sig, legs, start, cfg):
    w = MC.target_weights(sig, cfg)
    r, trades = MC.run_strategy(w, MC.regime_key(sig, cfg), legs, start, band=cfg['band'], stubs=cfg['stubs'])
    lev = (w[:, start:-1, 0] + 3 * w[:, start:-1, 1] + 2 * w[:, start:-1, 2] + w[:, start:-1, 3]).mean(1)
    return r, trades, lev


def history():
    p = MC.load_panel('proxy'); d = p['dates']
    qpx = 100 * np.cumprod(1 + p['qqq']); ewpx = 100 * np.cumprod(1 + p['ew'])
    sig = MC.signals(qpx[None], ewpx[None])
    legs = np.stack([p['core'], p['tqqq'], p['qld'], p['xlu'], p['cash']], -1)[None]
    pr = MC.load_panel('real'); off = d.index(pr['dates'][0])
    sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items()}
    lr = np.stack([pr['core'], pr['tqqq'], pr['qld'], pr['xlu'], pr['cash']], -1)[None]
    s0 = next(i for i, x in enumerate(d) if x >= '2000-07-03')
    s1 = next(i for i, x in enumerate(pr['dates']) if x >= '2015-11-02')
    f = lambda m: f"{m['cagr'][0]*100:5.1f}% / {m['sharpe'][0]:.3f} / {m['mdd'][0]*100:6.1f}%"
    g = lambda t: f"{t[0]*100:5.1f}% / {t[1]:.3f} / {t[2]*100:6.1f}%" if t else '        n/a          '
    print(f"single historical path: proxy {d[s0]}..{d[-1]}, real {pr['dates'][s1]}..{pr['dates'][-1]}")
    print(f"{'design':34s} {'proxy (this engine)':>24s} {'proxy (STRATEGY.md)':>24s}   {'real (this engine)':>24s} {'real (STRATEGY.md)':>24s}")
    for cfg in DESIGNS:
        mp = MC.stats(run(sig, legs, s0, cfg)[0]); mr = MC.stats(run(sr, lr, s1, cfg)[0])
        sp = SPEC.get(cfg['name'], (None, None))
        print(f"{cfg['name']:34s} {f(mp):>24s} {g(sp[0]):>24s}   {f(mr):>24s} {g(sp[1]):>24s}")


def simulate(panel, P, years, block, seed):
    rng = np.random.default_rng(seed)
    H = int(round(252 * years)); T = MC.WARMUP + H + 1
    src = np.arange(1, len(panel['dates']))
    idx = src[MC.bootstrap_idx(rng, len(src), P, T, block)]
    g = {k: panel[k][idx] for k in panel if k != 'dates'}
    sig = MC.signals(100 * np.cumprod(1 + g['qqq'], 1), 100 * np.cumprod(1 + g['ew'], 1))
    legs = np.stack([g['core'], g['tqqq'], g['qld'], g['xlu'], g['cash']], -1)
    start = MC.WARMUP
    out = {'QQQ': MC.stats(g['qqq_tr'][:, start + 1:])}
    for cfg in DESIGNS:
        r, trades, lev = run(sig, legs, start, cfg)
        m = MC.stats(r); m['trades_pa'] = trades / years; m['lev'] = lev
        out[cfg['name']] = m
    return out


def table(res, label):
    live = res[LIVE['name']]; q = res['QQQ']
    lines = [f"### {label}", "",
             "| design | avg lev | median CAGR | p5 CAGR | median Sharpe | median MaxDD | p5 MaxDD | P(CAGR > QQQ) | P(CAGR > live) | P(Sharpe > live) | P(MaxDD shallower than live) |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, m in res.items():
        if k == 'QQQ':
            continue
        same = k == LIVE['name']
        cell = (lambda x: '—') if same else (lambda x: f"{x*100:.0f}%")
        lines.append(f"| {k} | {np.median(m['lev']):.2f}x | {np.median(m['cagr'])*100:.1f}% | {np.percentile(m['cagr'],5)*100:.1f}% | "
                     f"{np.median(m['sharpe']):.2f} | {np.median(m['mdd'])*100:.1f}% | {np.percentile(m['mdd'],5)*100:.1f}% | "
                     f"{(m['cagr'] > q['cagr']).mean()*100:.0f}% | {cell((m['cagr'] > live['cagr']).mean())} | "
                     f"{cell((m['sharpe'] > live['sharpe']).mean())} | {cell((m['mdd'] > live['mdd']).mean())} |")
    lines.append(f"| QQQ buy-and-hold | 1.00x | {np.median(q['cagr'])*100:.1f}% | {np.percentile(q['cagr'],5)*100:.1f}% | "
                 f"{np.median(q['sharpe']):.2f} | {np.median(q['mdd'])*100:.1f}% | {np.percentile(q['mdd'],5)*100:.1f}% | — | "
                 f"{(q['cagr'] > live['cagr']).mean()*100:.0f}% | {(q['sharpe'] > live['sharpe']).mean()*100:.0f}% | {(q['mdd'] > live['mdd']).mean()*100:.0f}% |")
    return "\n".join(lines)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--history', action='store_true')
    ap.add_argument('--paths', type=int, default=1000)
    ap.add_argument('--years', type=float, default=10)
    ap.add_argument('--blocks', default='20,60,120,250')
    ap.add_argument('--panels', default='proxy,holdout,real')
    ap.add_argument('--seed', type=int, default=20261021)
    ap.add_argument('--out', default=os.path.join(HERE, 'research_notes', 'monte_carlo_versions_run.log'))
    a = ap.parse_args(argv)
    if a.history:
        history(); return
    text = [f"# Monte Carlo of past releases {time.strftime('%Y-%m-%d %H:%M')}  paths={a.paths} years={a.years} seed={a.seed}", ""]
    summ = {}
    for kind in a.panels.split(','):
        panel = MC.load_panel(kind)
        for L in [int(b) for b in a.blocks.split(',')]:
            t0 = time.time()
            res = simulate(panel, a.paths, a.years, L, a.seed + L)
            lab = f"{kind} panel, mean block {L} sessions [{time.time()-t0:.0f}s]"
            t = table(res, lab); print(t); print(); text += [t, ""]
            live = res[LIVE['name']]
            summ[f"{kind}/L{L}"] = {k: dict(cagr_med=float(np.median(m['cagr'])), sharpe_med=float(np.median(m['sharpe'])),
                                            mdd_med=float(np.median(m['mdd'])), mdd_p5=float(np.percentile(m['mdd'], 5)),
                                            p_cagr_gt_live=float((m['cagr'] > live['cagr']).mean()),
                                            p_sharpe_gt_live=float((m['sharpe'] > live['sharpe']).mean()),
                                            p_cagr_gt_qqq=float((m['cagr'] > res['QQQ']['cagr']).mean()))
                                    for k, m in res.items()}
    with open(a.out, 'w') as fh:
        fh.write("\n".join(text) + "\n\n```json\n" + json.dumps(summ, indent=1) + "\n```\n")
    print(f"wrote {a.out}")


if __name__ == '__main__':
    main(sys.argv[1:])
