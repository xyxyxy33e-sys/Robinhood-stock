"""Pre-declared improvement candidates for the live design, judged on the
Monte Carlo (shared bootstrapped paths, paired against live).

The list was fixed before running, from what monte_carlo.md and
monte_carlo_versions.md showed:
  vol max(10,30)   the reverted estimator; 09-07 beat 09-09 almost everywhere
  D gate breadth   gate on breadth only (the gap200 half failed the holdout)
  no D gate        09-07 had none and led on the 2000-2015 holdout
  no trim          does the extension trim earn its keep off the tuned path?
  vol target 18/22 the vol target is a risk dial; shown for the frontier
  max + breadth    the two non-dial candidates together
plus an execution check: live and the max(10,30) candidate with ONE session
of lag (weights decided at close t traded at close t+1).

A candidate counts as an improvement only if, in most of the 12 cells
(proxy / holdout / real x mean block 20/60/120/250), it has higher Sharpe
than live on more than half of the paths without giving up more than 0.5 pp
of median CAGR.

    python3 paper-track/monte_carlo_improve.py --paths 1000
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

LIVE = dict(MC.LIVE, name='live')
CANDIDATES = [
    dict(LIVE, name='vol max(10,30)', vol='max10_30'),
    dict(LIVE, name='D gate breadth only', d_gate_mode='breadth'),
    dict(LIVE, name='no D gate', d_gate=False),
    dict(LIVE, name='no extension trim', trim='none'),
    dict(LIVE, name='vol target 18%', vol_target=0.18),
    dict(LIVE, name='vol target 22%', vol_target=0.22),
    dict(LIVE, name='vol max + breadth gate', vol='max10_30', d_gate_mode='breadth'),
]
LAGGED = [LIVE, CANDIDATES[0]]


def run(sig, legs, start, cfg, lag=0):
    w = MC.target_weights(sig, cfg); k = MC.regime_key(sig, cfg)
    if lag:
        w = np.concatenate([w[:, :lag], w[:, :-lag]], 1); k = np.concatenate([k[:, :lag], k[:, :-lag]], 1)
    r, trades = MC.run_strategy(w, k, legs, start, band=cfg['band'], stubs=cfg['stubs'])
    m = MC.stats(r); m['trades'] = trades
    return m


def cell(panel, P, years, block, seed):
    rng = np.random.default_rng(seed)
    H = int(round(252 * years)); T = MC.WARMUP + H + 1
    src = np.arange(1, len(panel['dates']))
    idx = src[MC.bootstrap_idx(rng, len(src), P, T, block)]
    g = {k: panel[k][idx] for k in panel if k != 'dates'}
    sig = MC.signals(100 * np.cumprod(1 + g['qqq'], 1), 100 * np.cumprod(1 + g['ew'], 1))
    legs = np.stack([g['core'], g['tqqq'], g['qld'], g['xlu'], g['cash']], -1)
    base = run(sig, legs, MC.WARMUP, LIVE)
    out = {}
    for cfg in CANDIDATES:
        out[cfg['name']] = compare(run(sig, legs, MC.WARMUP, cfg), base, years)
    lag_base = run(sig, legs, MC.WARMUP, LIVE, lag=1)
    out['live, 1-session lag'] = compare(lag_base, base, years)
    out['vol max(10,30), 1-session lag'] = compare(run(sig, legs, MC.WARMUP, CANDIDATES[0], lag=1), lag_base, years)
    out['_live'] = dict(cagr=float(np.median(base['cagr'])), sharpe=float(np.median(base['sharpe'])),
                        mdd=float(np.median(base['mdd'])), trades=float(np.median(base['trades'])) / years)
    return out


def compare(m, b, years):
    return dict(d_cagr=float(np.median(m['cagr'] - b['cagr'])), d_sharpe=float(np.median(m['sharpe'] - b['sharpe'])),
                d_mdd=float(np.median(m['mdd'] - b['mdd'])), d_mdd_p5=float(np.percentile(m['mdd'], 5) - np.percentile(b['mdd'], 5)),
                p_sharpe=float((m['sharpe'] > b['sharpe']).mean()), p_dd=float((m['mdd'] > b['mdd']).mean()),
                p_cagr=float((m['cagr'] > b['cagr']).mean()),
                d_trades=float(np.median(m['trades'] - b['trades'])) / years)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--paths', type=int, default=1000)
    ap.add_argument('--years', type=float, default=10)
    ap.add_argument('--blocks', default='20,60,120,250')
    ap.add_argument('--panels', default='proxy,holdout,real')
    ap.add_argument('--seed', type=int, default=20261021)
    ap.add_argument('--out', default=os.path.join(HERE, 'research_notes', 'monte_carlo_improve_run.log'))
    a = ap.parse_args(argv)
    allres = {}
    for kind in a.panels.split(','):
        panel = MC.load_panel(kind)
        for L in [int(b) for b in a.blocks.split(',')]:
            t0 = time.time()
            allres[f"{kind}/L{L}"] = cell(panel, a.paths, a.years, L, a.seed + L)
            print(f"{kind}/L{L} done [{time.time()-t0:.0f}s]", flush=True)
    names = [k for k in next(iter(allres.values())) if not k.startswith('_')]
    lines = [f"# Improvement candidates {time.strftime('%Y-%m-%d %H:%M')} paths={a.paths} years={a.years} seed={a.seed}", "",
             "Paired against live on the same paths (lag rows: live-lag vs live; max-lag vs live-lag).", "",
             "| candidate | cells Sharpe-better (>50% paths) | cells DD-shallower (>50%) | cells CAGR ≥ −0.5pp | median ΔCAGR range | median ΔSharpe range | median ΔMaxDD range | Δ p5 MaxDD range | Δ rebalances/yr |",
             "|---|---|---|---|---|---|---|---|---|"]
    for n in names:
        c = [allres[k][n] for k in allres]
        rng_ = lambda f, s=100, d=1: f"{min(x[f] for x in c)*s:+.{d}f} … {max(x[f] for x in c)*s:+.{d}f}"
        lines.append(f"| {n} | {sum(x['p_sharpe'] > .5 for x in c)}/{len(c)} | {sum(x['p_dd'] > .5 for x in c)}/{len(c)} | "
                     f"{sum(x['d_cagr'] >= -0.005 for x in c)}/{len(c)} | {rng_('d_cagr')} pp | {rng_('d_sharpe', 1, 3)} | "
                     f"{rng_('d_mdd')} pp | {rng_('d_mdd_p5')} pp | {np.median([x['d_trades'] for x in c]):+.1f} |")
    lines += ["", "Per cell: P(Sharpe > base) / P(MaxDD shallower) / median ΔCAGR pp", "",
              "| candidate | " + " | ".join(allres) + " |", "|---" * (len(allres) + 1) + "|"]
    for n in names:
        lines.append(f"| {n} | " + " | ".join(f"{allres[k][n]['p_sharpe']*100:.0f}/{allres[k][n]['p_dd']*100:.0f}/{allres[k][n]['d_cagr']*100:+.1f}"
                                            for k in allres) + " |")
    lines.append("| live: median CAGR / Sharpe / MaxDD | " + " | ".join(
        f"{allres[k]['_live']['cagr']*100:.1f}/{allres[k]['_live']['sharpe']:.2f}/{allres[k]['_live']['mdd']*100:.0f}" for k in allres) + " |")
    txt = "\n".join(lines); print(txt)
    with open(a.out, 'w') as fh:
        fh.write(txt + "\n\n```json\n" + json.dumps(allres, indent=1) + "\n```\n")


if __name__ == '__main__':
    main(sys.argv[1:])
