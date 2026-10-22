"""Round 2 of improvement candidates, paired against the 2026-10-22 live design
(max(10d, 30d) vol) on the same bootstrapped paths, 12 cells. Fixed before running:
  book-vol target   vol target on the row's own leverage (book vol), with the
                    target re-calibrated per cell so average QQQ-equivalent
                    leverage equals live's -- any gain is timing, not less risk
  D2 at the D1 row  the 100-150d dip zone holds 50/50 SPMO/QLD (1.5x), not 2.5x
  band 10%          drift band 5% -> 10%: what does cutting churn cost?
Same pass rule as monte_carlo_improve.py.

    python3 paper-track/monte_carlo_improve_r2.py --paths 1000
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

LIVE = dict(MC.LIVE, name='live 2026-10-22')
D2_AT_D1 = dict(LIVE, name='D2 at the D1 row', ladder_rows={'D2': MC.S.D_LADDER_ROWS['D1']})
BAND10 = dict(LIVE, name='band 10%', band=0.10)


def lev(sig, cfg):
    w = MC.target_weights(sig, cfg)[:, MC.WARMUP:-1]
    return (w[..., 0] + 3 * w[..., 1] + 2 * w[..., 2] + w[..., 3]).mean()


def cell(panel, P, years, block, seed):
    rng = np.random.default_rng(seed)
    T = MC.WARMUP + int(round(252 * years)) + 1
    src = np.arange(1, len(panel['dates']))
    idx = src[MC.bootstrap_idx(rng, len(src), P, T, block)]
    g = {k: panel[k][idx] for k in panel if k != 'dates'}
    sig = MC.signals(100 * np.cumprod(1 + g['qqq'], 1), 100 * np.cumprod(1 + g['ew'], 1))
    legs = np.stack([g['core'], g['tqqq'], g['qld'], g['xlu'], g['cash']], -1)
    base = I.run(sig, legs, MC.WARMUP, LIVE)
    target = lev(sig, LIVE); lo, hi = 0.10, 0.80
    for _ in range(16):
        mid = (lo + hi) / 2
        if lev(sig, dict(LIVE, vol_scope='book', vol_target=mid)) > target: hi = mid
        else: lo = mid
    book = dict(LIVE, name='book-vol target (matched leverage)', vol_scope='book', vol_target=(lo + hi) / 2)
    out = {}
    for cfg in (book, D2_AT_D1, BAND10):
        out[cfg['name']] = I.compare(I.run(sig, legs, MC.WARMUP, cfg), base, years)
    out['_book_target'] = book['vol_target']
    out['_live'] = dict(cagr=float(np.median(base['cagr'])), sharpe=float(np.median(base['sharpe'])),
                        mdd=float(np.median(base['mdd'])), trades=float(np.median(base['trades'])) / years)
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--paths', type=int, default=1000)
    ap.add_argument('--seed', type=int, default=20261021)
    ap.add_argument('--out', default=os.path.join(HERE, 'research_notes', 'monte_carlo_improve_r2_run.log'))
    a = ap.parse_args(argv)
    res = {}
    for kind in ('proxy', 'holdout', 'real'):
        panel = MC.load_panel(kind)
        for L in (20, 60, 120, 250):
            t0 = time.time(); res[f"{kind}/L{L}"] = cell(panel, a.paths, 10, L, a.seed + L)
            print(f"{kind}/L{L} [{time.time()-t0:.0f}s] book target {res[f'{kind}/L{L}']['_book_target']*100:.1f}%", flush=True)
    names = [k for k in next(iter(res.values())) if not k.startswith('_')]
    lines = ["| candidate | cells Sharpe-better | cells DD-shallower | cells CAGR ≥ −0.5pp | ΔCAGR | ΔSharpe | ΔMaxDD | Δ p5 MaxDD | Δ rebal/yr |", "|---|---|---|---|---|---|---|---|---|"]
    for n in names:
        c = [res[k][n] for k in res]
        r = lambda f, s=100, d=1: f"{min(x[f] for x in c)*s:+.{d}f} … {max(x[f] for x in c)*s:+.{d}f}"
        lines.append(f"| {n} | {sum(x['p_sharpe'] > .5 for x in c)}/12 | {sum(x['p_dd'] > .5 for x in c)}/12 | {sum(x['d_cagr'] >= -0.005 for x in c)}/12 | "
                     f"{r('d_cagr')} pp | {r('d_sharpe', 1, 3)} | {r('d_mdd')} pp | {r('d_mdd_p5')} pp | {np.median([x['d_trades'] for x in c]):+.1f} |")
    lines += ["", "| candidate | " + " | ".join(res) + " |", "|---" * 13 + "|"]
    for n in names:
        lines.append(f"| {n} | " + " | ".join(f"{res[k][n]['p_sharpe']*100:.0f}/{res[k][n]['p_dd']*100:.0f}/{res[k][n]['d_cagr']*100:+.1f}" for k in res) + " |")
    txt = "\n".join(lines); print(txt)
    with open(a.out, 'w') as fh:
        fh.write(f"# Improvement round 2 {time.strftime('%Y-%m-%d %H:%M')} paths={a.paths}\n\nP(Sharpe>live)/P(DD shallower)/median dCAGR pp per cell\n\n" + txt + "\n\n```json\n" + json.dumps(res, indent=1) + "\n```\n")


if __name__ == '__main__':
    main(sys.argv[1:])
