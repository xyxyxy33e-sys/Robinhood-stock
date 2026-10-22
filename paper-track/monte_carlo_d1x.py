"""D at 1x: every D-ladder zone holds 100% core (SPMO; QQQ on the proxy), the D gate
still goes to cash. Paired against the 2026-10-22 live design in 12 cells, and against
an exposure-matched control: live with the vol target lowered (bisection per cell)
until its average QQQ-equivalent leverage equals the candidate's. Research only.

    python3 paper-track/monte_carlo_d1x.py --paths 1000
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
import monte_carlo_improve as I  # noqa: E402
import monte_carlo_versions as V  # noqa: E402

LIVE = dict(MC.LIVE, name='live 2026-10-22')
D1X = dict(LIVE, name='D at 1x (100% core)', ladder_rows={z: (1.0, 0.0, 0.0) for z in ('D1', 'D2', 'D3')})


def lev(sig, cfg):
    w = MC.target_weights(sig, cfg)[:, MC.WARMUP:-1]
    return (w[..., 0] + 3 * w[..., 1] + 2 * w[..., 2] + w[..., 3]).mean()


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--paths', type=int, default=1000)
    ap.add_argument('--seed', type=int, default=20261021)
    a = ap.parse_args(argv)
    p = MC.load_panel('proxy'); d = p['dates']
    sig = MC.signals((100 * np.cumprod(1 + p['qqq']))[None], (100 * np.cumprod(1 + p['ew']))[None])
    legs = np.stack([p['core'], p['tqqq'], p['qld'], p['xlu'], p['cash']], -1)[None]
    pr = MC.load_panel('real'); off = d.index(pr['dates'][0])
    sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: x[:, off:] for n, x in v.items()}) for k, v in sig.items()}
    lr = np.stack([pr['core'], pr['tqqq'], pr['qld'], pr['xlu'], pr['cash']], -1)[None]
    s0 = next(i for i, x in enumerate(d) if x >= '2000-07-03'); s1 = next(i for i, x in enumerate(pr['dates']) if x >= '2015-11-02')
    lines = ["## Single historical path (CAGR / Sharpe / MaxDD)", "", "| design | proxy 2000-07..2026-08 | real 2015-11..2026-08 |", "|---|---|---|"]
    for cfg in (LIVE, D1X):
        x = MC.stats(V.run(sig, legs, s0, cfg)[0]); y = MC.stats(V.run(sr, lr, s1, cfg)[0])
        lines.append(f"| {cfg['name']} | {x['cagr'][0]*100:.1f}% / {x['sharpe'][0]:.3f} / {x['mdd'][0]*100:.1f}% | {y['cagr'][0]*100:.1f}% / {y['sharpe'][0]:.3f} / {y['mdd'][0]*100:.1f}% |")
    res = {}
    for kind in ('proxy', 'holdout', 'real'):
        panel = MC.load_panel(kind)
        for L in (20, 60, 120, 250):
            t0 = time.time()
            rng = np.random.default_rng(a.seed + L); T = MC.WARMUP + 2521
            src = np.arange(1, len(panel['dates'])); idx = src[MC.bootstrap_idx(rng, len(src), a.paths, T, L)]
            g = {k: panel[k][idx] for k in panel if k != 'dates'}
            sg = MC.signals(100 * np.cumprod(1 + g['qqq'], 1), 100 * np.cumprod(1 + g['ew'], 1))
            lg = np.stack([g['core'], g['tqqq'], g['qld'], g['xlu'], g['cash']], -1)
            base = I.run(sg, lg, MC.WARMUP, LIVE); cand = I.run(sg, lg, MC.WARMUP, D1X)
            target = lev(sg, D1X); lo, hi = 0.05, 0.20
            for _ in range(16):
                mid = (lo + hi) / 2
                if lev(sg, dict(LIVE, vol_target=mid)) > target: hi = mid
                else: lo = mid
            ctrl = I.run(sg, lg, MC.WARMUP, dict(LIVE, vol_target=(lo + hi) / 2))
            q = MC.stats(g['qqq_tr'][:, MC.WARMUP + 1:])
            st = lambda m: dict(cagr=float(np.median(m['cagr'])), sharpe=float(np.median(m['sharpe'])), mdd=float(np.median(m['mdd'])),
                                mdd_p5=float(np.percentile(m['mdd'], 5)), p_qqq=float((m['cagr'] > q['cagr']).mean()),
                                p_loss=float((m['nav'] < 1).mean()))
            res[f"{kind}/L{L}"] = dict(live=st(base), d1x=st(cand), ctrl=st(ctrl), ctrl_target=(lo + hi) / 2,
                                       lev_live=float(lev(sg, LIVE)), lev_d1x=float(target),
                                       vs_live=I.compare(cand, base, 10), vs_ctrl=I.compare(cand, ctrl, 10))
            print(f"{kind}/L{L} [{time.time()-t0:.0f}s]", flush=True)
    lines += ["", "## Monte Carlo, median CAGR / Sharpe / MaxDD (P(CAGR > QQQ))", "",
              "| cell | live | D at 1x | matched control (live, lower vol target) | avg leverage live → D1x |", "|---|---|---|---|---|"]
    f = lambda m: f"{m['cagr']*100:.1f}% / {m['sharpe']:.2f} / {m['mdd']*100:.1f}% ({m['p_qqq']*100:.0f}%)"
    for k, r in res.items():
        lines.append(f"| {k} | {f(r['live'])} | {f(r['d1x'])} | {f(r['ctrl'])} @ {r['ctrl_target']*100:.1f}% | {r['lev_live']:.2f}x → {r['lev_d1x']:.2f}x |")
    lines += ["", "## Paired: D at 1x vs live, and vs the matched control — P(Sharpe better) / P(MaxDD shallower) / median ΔCAGR / Δ p5 MaxDD", "",
              "| cell | vs live | vs matched control |", "|---|---|---|"]
    g_ = lambda c: f"{c['p_sharpe']*100:.0f}% / {c['p_dd']*100:.0f}% / {c['d_cagr']*100:+.1f} pp / {c['d_mdd_p5']*100:+.1f} pp"
    for k, r in res.items():
        lines.append(f"| {k} | {g_(r['vs_live'])} | {g_(r['vs_ctrl'])} |")
    txt = "\n".join(lines); print(txt)
    with open(os.path.join(HERE, 'research_notes', 'monte_carlo_d1x_run.log'), 'w') as fh:
        fh.write(f"# D at 1x {time.strftime('%Y-%m-%d %H:%M')} paths={a.paths}\n\n" + txt + "\n\n```json\n" + json.dumps(res, indent=1) + "\n```\n")


if __name__ == '__main__':
    main(sys.argv[1:])
