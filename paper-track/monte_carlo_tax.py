"""After-tax Monte Carlo: the live design in a taxable account, lot by lot.

Same bootstrapped paths and decisions as monte_carlo.py. Each path is replayed
with dollar positions and tax lots:
  - every buy opens a lot; sells close lots FIFO or HIFO (highest cost first);
  - a gain on a lot held < 252 sessions is short-term, otherwise long-term;
  - taxes settle every 252 sessions: ST and LT netted within and across
    character, net losses carried forward; the tax is paid by trimming every
    leg pro rata (the trim itself is not taxed -- a small simplification);
  - at the end of the horizon the whole book is liquidated and taxed;
  - QQQ buy-and-hold pays long-term tax once, at the end.
Not modelled: wash-sale disallowance (it makes the strategy look BETTER),
dividend tax, state tax, the $3k ordinary-income offset. STRATEGY.md records
(2026-09-06) that the owner offsets gains in a separate tax-loss-harvesting
account, so this is a reference figure, not the objective.

    python3 paper-track/monte_carlo_tax.py --paths 200
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

BRACKETS = {'top (ST 40.8% / LT 23.8%)': (0.408, 0.238), 'middle (ST 24% / LT 15%)': (0.24, 0.15)}
YEAR = 252


def settle(st, lt, cf):
    """Net ST/LT with a carried loss cf (<= 0); return (st_taxable, lt_taxable, new_cf)."""
    st += cf
    if st < 0 and lt > 0:
        lt += st; st = 0.0
    elif lt < 0 and st > 0:
        st += lt; lt = 0.0
    if st < 0 or lt < 0:
        loss = min(st, 0) + min(lt, 0)
        return max(st, 0.0), max(lt, 0.0), loss
    return st, lt, 0.0


def tax_path(w, key, rets, start, band, stubs, r_st, r_lt, hifo):
    """One path. w, rets: lists of per-session leg lists; key: list. Returns
    (terminal before the final liquidation tax, after-tax terminal, total tax paid)."""
    n = len(w[0]); T = len(w)
    px = [1.0] * n; units = [0.0] * n; lots = [[] for _ in range(n)]
    nav = 1.0 - MC.COST
    for i in range(n):
        if w[start][i] > 0:
            units[i] = w[start][i] * nav; lots[i].append([units[i], 1.0, start])
    st = lt = 0.0; cf = 0.0; paid = 0.0; pre_nav = nav
    for t in range(start, T - 1):
        if t > start:
            vals = [units[i] * px[i] for i in range(n)]; nav = sum(vals)
            held = [v / nav for v in vals]; tgt = w[t]
            drift = sum(abs(a - b) for a, b in zip(tgt, held))
            reb = key[t] != key[t - 1] or drift > band or (stubs and any(a == 0 and b > MC.S.ZERO_LEG_EPS for a, b in zip(tgt, held)))
            if reb:
                nav_after = nav * (1 - MC.COST * drift)
                for i in range(n):
                    want = tgt[i] * nav_after; have = vals[i]
                    if want < have - 1e-12:
                        sell = (have - want) / px[i]
                        lots[i].sort(key=(lambda l: -l[1]) if hifo else (lambda l: l[2]))
                        while sell > 1e-15 and lots[i]:
                            lot = lots[i][0]; q = min(lot[0], sell)
                            g = q * (px[i] - lot[1])
                            if t - lot[2] >= YEAR: lt += g
                            else: st += g
                            lot[0] -= q; sell -= q
                            if lot[0] <= 1e-15: lots[i].pop(0)
                        units[i] = want / px[i]
                    elif want > have + 1e-12:
                        q = (want - have) / px[i]; lots[i].append([q, px[i], t]); units[i] += q
        r = rets[t + 1]
        for i in range(n):
            px[i] *= 1 + r[i]
        if (t + 1 - start) % YEAR == 0 and t + 1 < T - 1:
            s_, l_, cf = settle(st, lt, cf); tax = s_ * r_st + l_ * r_lt; st = lt = 0.0
            nav = sum(units[i] * px[i] for i in range(n))
            if tax > 0:
                k = 1 - tax / nav; paid += tax
                for i in range(n):
                    units[i] *= k
                    for lot in lots[i]: lot[0] *= k
    nav = sum(units[i] * px[i] for i in range(n))
    for i in range(n):
        for lot in lots[i]:
            g = lot[0] * (px[i] - lot[1])
            if (T - 1) - lot[2] >= YEAR: lt += g
            else: st += g
    s_, l_, cf = settle(st, lt, cf); tax = s_ * r_st + l_ * r_lt; paid += tax
    return nav, nav - tax, paid


def cell(panel, P, years, block, seed, designs):
    rng = np.random.default_rng(seed)
    T = MC.WARMUP + int(round(252 * years)) + 1
    src = np.arange(1, len(panel['dates']))
    idx = src[MC.bootstrap_idx(rng, len(src), P, T, block)]
    g = {k: panel[k][idx] for k in panel if k != 'dates'}
    sig = MC.signals(100 * np.cumprod(1 + g['qqq'], 1), 100 * np.cumprod(1 + g['ew'], 1))
    legs = np.stack([g['core'], g['tqqq'], g['qld'], g['xlu'], g['cash']], -1)
    out = {}
    q = np.prod(1 + g['qqq_tr'][:, MC.WARMUP + 1:], 1)
    for bname, (rs, rl) in BRACKETS.items():
        o = out[bname] = {}
        o['QQQ buy-and-hold'] = dict(pre=q, post=q - np.maximum(q - 1, 0) * rl)
        for name, cfg, hifo in designs:
            W = MC.target_weights(sig, cfg); K = MC.regime_key(sig, cfg)
            r, _ = MC.run_strategy(W, K, legs, MC.WARMUP, band=cfg['band'], stubs=cfg['stubs'])
            pre = np.prod(1 + r, 1)                       # pre-tax: the engine itself (the replay matches it at 0% tax)
            post = np.zeros(P)
            for j in range(P):
                post[j] = tax_path(W[j].tolist(), K[j].tolist(), legs[j].tolist(), MC.WARMUP, cfg['band'], cfg['stubs'], rs, rl, hifo)[1]
            o[name] = dict(pre=pre, post=post)
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--paths', type=int, default=200)
    ap.add_argument('--seed', type=int, default=20261021)
    ap.add_argument('--out', default=os.path.join(HERE, 'research_notes', 'monte_carlo_tax_run.log'))
    a = ap.parse_args(argv)
    designs = [('live, FIFO lots', MC.LIVE, False), ('live, HIFO lots', MC.LIVE, True),
               ('live + 10% band, HIFO', dict(MC.LIVE, band=0.10), True)]
    years = 10; res = {}; lines = []
    for kind, L in (('proxy', 60), ('proxy', 120), ('holdout', 60), ('real', 60), ('real', 120)):
        t0 = time.time()
        c = cell(MC.load_panel(kind), a.paths, years, L, a.seed + L, designs)
        res[f"{kind}/L{L}"] = {b: {k: dict(pre_cagr=float(np.median(v['pre'] ** (1 / years) - 1)),
                                           post_cagr=float(np.median(v['post'] ** (1 / years) - 1)),
                                           p_beats_qqq_after_tax=float((v['post'] > c[b]['QQQ buy-and-hold']['post']).mean()))
                                   for k, v in d.items()} for b, d in c.items()}
        print(f"{kind}/L{L} [{time.time()-t0:.0f}s]", flush=True)
    for b in BRACKETS:
        lines += [f"\n### {b}", "", "| cell | " + " | ".join(next(iter(res.values()))[b]) + " |", "|---" * (1 + len(next(iter(res.values()))[b])) + "|"]
        for k, dd in res.items():
            d = dd[b]
            lines.append(f"| {k} | " + " | ".join(f"{v['pre_cagr']*100:.1f}% → **{v['post_cagr']*100:.1f}%**"
                                                   + ("" if n == 'QQQ buy-and-hold' else f" ({v['p_beats_qqq_after_tax']*100:.0f}% beat QQQ)")
                                                   for n, v in d.items()) + " |")
    txt = "Median 10-year CAGR, pre-tax → after tax (liquidated at the end); in brackets, share of paths beating QQQ after tax.\n" + "\n".join(lines)
    print(txt)
    with open(a.out, 'w') as fh:
        fh.write(f"# After-tax Monte Carlo {time.strftime('%Y-%m-%d %H:%M')} paths={a.paths}\n\n" + txt + "\n\n```json\n" + json.dumps(res, indent=1) + "\n```\n")


if __name__ == '__main__':
    main(sys.argv[1:])
