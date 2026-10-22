"""Keep the core through state D (re-run of the 2026-09-06 after-tax idea on the
2026-10-22 design). Same leverage per D zone, expressed with SPMO + TQQQ so the
core leg is not sold into a D dip:
  (a) D2 only : D2 0/50/50 TQQQ/QLD (2.5x) -> 25/75 SPMO/TQQQ (2.5x)
  (b) D1 + D2 : also D1 50/50 SPMO/QLD (1.5x) -> 75/25 SPMO/TQQQ (1.5x)
Fixed before running. Pre-tax paired against live in 12 cells; after tax with
monte_carlo_tax's lot model; single historical path; core sell-outs per year.

    python3 paper-track/monte_carlo_core_in_d.py --paths 1000 --tax-paths 500
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
import monte_carlo_tax as TX  # noqa: E402
import monte_carlo_versions as V  # noqa: E402

LIVE = dict(MC.LIVE, name='live 2026-10-22')
CAND_A = dict(LIVE, name='(a) D2 = 25/75 SPMO/TQQQ', ladder_rows={'D2': (0.25, 0.75, 0.0)})
CAND_B = dict(LIVE, name='(b) + D1 = 75/25 SPMO/TQQQ', ladder_rows={'D2': (0.25, 0.75, 0.0), 'D1': (0.75, 0.25, 0.0)})
CANDS = [CAND_A, CAND_B]


def sellouts(w, years):
    """Times per year the core leg goes from held (>1%) to zero."""
    c = w[:, MC.WARMUP:, 0]
    return ((c[:, :-1] > 0.01) & (c[:, 1:] <= 1e-9)).sum(1).mean() / years


def history():
    p = MC.load_panel('proxy'); d = p['dates']
    sig = MC.signals((100 * np.cumprod(1 + p['qqq']))[None], (100 * np.cumprod(1 + p['ew']))[None])
    legs = np.stack([p['core'], p['tqqq'], p['qld'], p['xlu'], p['cash']], -1)[None]
    pr = MC.load_panel('real'); off = d.index(pr['dates'][0])
    sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items()}
    lr = np.stack([pr['core'], pr['tqqq'], pr['qld'], pr['xlu'], pr['cash']], -1)[None]
    s0 = next(i for i, x in enumerate(d) if x >= '2000-07-03'); s1 = next(i for i, x in enumerate(pr['dates']) if x >= '2015-11-02')
    out = []
    for cfg in [LIVE] + CANDS:
        a = MC.stats(V.run(sig, legs, s0, cfg)[0]); b = MC.stats(V.run(sr, lr, s1, cfg)[0])
        out.append(f"| {cfg['name']} | {a['cagr'][0]*100:.1f}% / {a['sharpe'][0]:.3f} / {a['mdd'][0]*100:.1f}% | "
                   f"{b['cagr'][0]*100:.1f}% / {b['sharpe'][0]:.3f} / {b['mdd'][0]*100:.1f}% |")
    return ["| design | proxy 2000-07..2026-08 | real 2015-11..2026-08 |", "|---|---|---|"] + out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--paths', type=int, default=1000)
    ap.add_argument('--tax-paths', type=int, default=500)
    ap.add_argument('--seed', type=int, default=20261021)
    ap.add_argument('--out', default=os.path.join(HERE, 'research_notes', 'monte_carlo_core_in_d_run.log'))
    a = ap.parse_args(argv)
    lines = ["## Single historical path (CAGR / Sharpe / MaxDD)", ""] + history()
    print("\n".join(lines), flush=True)
    pre = {}
    for kind in ('proxy', 'holdout', 'real'):
        panel = MC.load_panel(kind)
        for L in (20, 60, 120, 250):
            rng = np.random.default_rng(a.seed + L); T = MC.WARMUP + 2521
            src = np.arange(1, len(panel['dates'])); idx = src[MC.bootstrap_idx(rng, len(src), a.paths, T, L)]
            g = {k: panel[k][idx] for k in panel if k != 'dates'}
            sig = MC.signals(100 * np.cumprod(1 + g['qqq'], 1), 100 * np.cumprod(1 + g['ew'], 1))
            legs = np.stack([g['core'], g['tqqq'], g['qld'], g['xlu'], g['cash']], -1)
            base = I.run(sig, legs, MC.WARMUP, LIVE)
            c = pre[f"{kind}/L{L}"] = {'_sellouts_live': float(sellouts(MC.target_weights(sig, LIVE), 10))}
            for cfg in CANDS:
                c[cfg['name']] = I.compare(I.run(sig, legs, MC.WARMUP, cfg), base, 10)
                c[cfg['name']]['sellouts'] = float(sellouts(MC.target_weights(sig, cfg), 10))
            print(f"pre-tax {kind}/L{L} done", flush=True)
    lines += ["", "## Pre-tax, paired against live: P(Sharpe better) / P(MaxDD shallower) / median ΔCAGR pp; core sell-outs per year", "",
              "| candidate | " + " | ".join(pre) + " |", "|---" * 13 + "|"]
    lines.append("| live: core sell-outs/yr | " + " | ".join(f"{pre[k]['_sellouts_live']:.1f}" for k in pre) + " |")
    for cfg in CANDS:
        n = cfg['name']
        lines.append(f"| {n} | " + " | ".join(f"{pre[k][n]['p_sharpe']*100:.0f}/{pre[k][n]['p_dd']*100:.0f}/{pre[k][n]['d_cagr']*100:+.1f} ({pre[k][n]['sellouts']:.1f})" for k in pre) + " |")
    for cfg in CANDS:
        c = [pre[k][cfg['name']] for k in pre]
        lines.append(f"\n{cfg['name']}: Sharpe-better cells {sum(x['p_sharpe'] > .5 for x in c)}/12, DD-shallower {sum(x['p_dd'] > .5 for x in c)}/12, "
                     f"ΔCAGR {min(x['d_cagr'] for x in c)*100:+.1f} … {max(x['d_cagr'] for x in c)*100:+.1f} pp, "
                     f"ΔMaxDD {min(x['d_mdd'] for x in c)*100:+.1f} … {max(x['d_mdd'] for x in c)*100:+.1f} pp")
    print("\n".join(lines[-20:]), flush=True)
    tax = {}
    designs = [(LIVE['name'], LIVE, False)] + [(cfg['name'], cfg, False) for cfg in CANDS]
    for kind, L in (('proxy', 60), ('proxy', 120), ('holdout', 60), ('real', 60), ('real', 120)):
        cc = TX.cell(MC.load_panel(kind), a.tax_paths, 10, L, a.seed + L, designs)
        tax[f"{kind}/L{L}"] = {b: {n: dict(pre=float(np.median(v['pre'] ** .1 - 1)), post=float(np.median(v['post'] ** .1 - 1)),
                                            p_vs_live=float((v['post'] > d[LIVE['name']]['post']).mean()),
                                            p_vs_qqq=float((v['post'] > d['QQQ buy-and-hold']['post']).mean()))
                                   for n, v in d.items()} for b, d in cc.items()}
        print(f"tax {kind}/L{L} done", flush=True)
    for b in TX.BRACKETS:
        names = list(next(iter(tax.values()))[b])
        lines += ["", f"## After tax, {b}: median CAGR pre → post (P(after-tax > live), P(> QQQ))", "", "| cell | " + " | ".join(names) + " |", "|---" * (len(names) + 1) + "|"]
        for k, d in tax.items():
            lines.append(f"| {k} | " + " | ".join(f"{d[b][n]['pre']*100:.1f} → **{d[b][n]['post']*100:.1f}%**"
                                                   + ("" if n in ('QQQ buy-and-hold', LIVE['name']) else f" ({d[b][n]['p_vs_live']*100:.0f}%, {d[b][n]['p_vs_qqq']*100:.0f}%)")
                                                   for n in names) + " |")
    txt = "\n".join(lines); print(txt)
    with open(a.out, 'w') as fh:
        fh.write(f"# Core held through D {time.strftime('%Y-%m-%d %H:%M')}\n\n" + txt + "\n\n```json\n" + json.dumps({'pre': pre, 'tax': tax}, indent=1) + "\n```\n")


if __name__ == '__main__':
    main(sys.argv[1:])
