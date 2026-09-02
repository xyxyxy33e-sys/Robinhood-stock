"""Round 2 of improvement_search.py: dig into what round 1 surfaced.

Round 1 (same harness, full 2000-2026) found:
  - State B at 75% core / 25% TQQQ instead of the live 25/75 improved
    EVERY metric in BOTH eras (Sharpe 0.682 -> 0.765, MaxDD -38.8 -> -29.8).
    B's live weight was chosen from FOUR episodes on the 2015+ window.
  - Micro overlay OFF: CAGR +1.85pp, better holdout, worse search era --
    the signature of an overlay fit to the era it was fit on.
  - State C with modest leverage: small Pareto gain, not both-era.
  - max(10d,30d) realised vol: +0.012 Sharpe, -2.4pp MaxDD, both eras.

This round: fine sweep of B; B episode census with per-episode attribution;
BETA-matched control (leverage changes need a control that matches effective
exposure core+3*tqqq+2*qld, not risky weight); micro overlay split into its A
and D halves; then combinations with marginal attribution.
"""
import sys
sys.path.insert(0, 'paper-track')
from improvement_search import (build, run, vt, live_base, evaluate, era, header,
                                show, SEARCH, HOLDOUT, BAND)
from state import TARGET_WEIGHTS, MICRO_OVERLAY_WEIGHTS
from drift_band_test import annual_stats

BETA = (1.0, 3.0, 2.0, 0.5, 0.0)   # rough equity beta per leg; XLU ~0.5


def beta_of(rows, wfn):
    tot = 0.0
    for r in rows:
        w = wfn(r)
        tot += sum(w[i] * BETA[i] for i in range(5))
    return tot / len(rows)


def scaled(wfn, k):
    def f(r):
        w = wfn(r)
        risky = sum(w[:4])
        return tuple(x * k for x in w[:4]) + (1.0 - risky * k,)
    return f


def beta_matched_control(rows, base_fn, target_beta):
    lo, hi = 0.0, 1.0
    for _ in range(25):
        mid = (lo + hi) / 2
        if beta_of(rows, scaled(base_fn, mid)) < target_beta:
            lo = mid
        else:
            hi = mid
    k = (lo + hi) / 2
    return k, evaluate(rows, scaled(base_fn, k))


def mk(W=None, micro='both', volfn=None):
    W = W or TARGET_WEIGHTS
    def f(r):
        key = (r['state'], r['agree'])
        if micro == 'both' and key in MICRO_OVERLAY_WEIGHTS:
            w = MICRO_OVERLAY_WEIGHTS[key]
        elif micro == 'A' and key == ('A', True):
            w = MICRO_OVERLAY_WEIGHTS[key]
        elif micro == 'D' and key == ('D', False):
            w = MICRO_OVERLAY_WEIGHTS[key]
        else:
            w = W[r['state']]
        v = volfn(r) if volfn else r['vol']
        return vt(w, v)
    return f


def episodes(rows, st):
    eps, cur = [], None
    for i, r in enumerate(rows):
        if r['state'] == st:
            cur = [i, i] if cur is None else [cur[0], i]
        elif cur:
            eps.append(cur); cur = None
    if cur:
        eps.append(cur)
    return eps


def main():
    rows = build()
    live = mk()
    base = evaluate(rows, live)
    print("LIVE:"); header(); show('LIVE', base)

    # ---- B fine sweep
    print("\n=== B fine sweep (core, tqqq, qld) -- micro ON, everything else live ===")
    header()
    grid = [(1, 0, 0), (0.9, 0.1, 0), (0.8, 0.2, 0), (0.75, 0.25, 0), (0.7, 0.3, 0),
            (0.6, 0.4, 0), (0.5, 0.5, 0), (0.25, 0.75, 0),
            (0.5, 0, 0.5), (0.25, 0, 0.75), (0, 0, 1), (0.6, 0.1, 0.3)]
    best = None
    for c, t, q in grid:
        W = dict(TARGET_WEIGHTS); W['B'] = (c, t, q, 0, 0)
        ev = evaluate(rows, mk(W))
        show(f"B=({c:.2f},{t:.2f},{q:.2f})", ev, base)
        if best is None or ev['sharpe'] > best[1]['sharpe']:
            best = ((c, t, q), ev)
    print(f"  best by full Sharpe: B={best[0]}")

    # ---- B episode census + attribution for the 75/25 candidate
    print("\n=== B episodes: live 25/75 vs candidate 75/25, per-episode strategy return ===")
    W = dict(TARGET_WEIGHTS); W['B'] = (0.75, 0.25, 0, 0, 0)
    cand = mk(W)
    r_live, _ = run(rows, live); r_cand, _ = run(rows, cand)
    eps = episodes(rows, 'B')
    print(f"{len(eps)} B episodes, {sum(b-a+1 for a,b in eps)} days")
    print(f"{'start':<12}{'end':<12}{'days':>5}{'  QQQ':>8}{'  live':>8}{'  cand':>8}{'  diff':>8}")
    helped = 0
    for a, b in eps:
        q = 1.0; l = 1.0; c = 1.0
        for i in range(a, b + 1):
            q *= 1 + rows[i]['legs'][0]; l *= 1 + r_live[i]; c *= 1 + r_cand[i]
        d = c - l
        helped += d > 0
        print(f"{rows[a]['d']:<12}{rows[b]['d']:<12}{b-a+1:>5}{(q-1)*100:>7.1f}%{(l-1)*100:>7.1f}%{(c-1)*100:>7.1f}%{d*100:>+7.1f}")
    print(f"candidate better in {helped} of {len(eps)} episodes")
    n15 = sum(1 for a, b in eps if rows[a]['d'] >= '2015-11-01')
    print(f"(episodes in the 2015+ window B's live weight was fit on: {n15})")

    # ---- beta-matched control for B 75/25
    print("\n=== beta-matched control for B=75/25 ===")
    evc = evaluate(rows, cand)
    bl, bc = beta_of(rows, live), beta_of(rows, cand)
    k, ctrl = beta_matched_control(rows, live, bc)
    header()
    show('LIVE', base); show(f'B=75/25 (beta {bc:.3f} vs live {bl:.3f})', evc, base)
    show(f'control: live scaled x{k:.3f}', ctrl, base)
    print(f"  candidate Sharpe {evc['sharpe']:.3f} vs control {ctrl['sharpe']:.3f}: "
          f"{'PASS' if evc['sharpe'] > ctrl['sharpe'] else 'FAIL'}")

    # ---- micro overlay halves
    print("\n=== micro overlay: which half? ===")
    header()
    for m in ('both', 'A', 'D', 'off'):
        show(f'micro={m}', evaluate(rows, mk(micro=m)), base)

    # ---- combinations
    print("\n=== combinations (each row adds one change; marginal = vs previous row) ===")
    header()
    maxvol = lambda r: max(r['vol10'] or 0, r['vol'] or 0)
    steps = [
        ('LIVE', dict()),
        ('+ B=75/25', dict(B=(0.75, 0.25, 0, 0, 0))),
        ('+ micro OFF', dict(micro='off')),
        ('+ C=80/20 TQQQ', dict(C=(0.8, 0.2, 0, 0, 0))),
        ('+ max(10d,30d) vol', dict(volfn=maxvol)),
    ]
    cfg = dict(W=dict(TARGET_WEIGHTS), micro='both', volfn=None)
    prev = None
    for label, chg in steps:
        for k2, v in chg.items():
            if k2 in ('micro', 'volfn'):
                cfg[k2] = v
            else:
                cfg['W'][k2] = v
        ev = evaluate(rows, mk(cfg['W'], cfg['micro'], cfg['volfn']))
        show(label, ev, prev or base)
        prev = ev
    # each change alone vs live, and each REMOVED from the full stack
    print("\n--- each change removed from the full stack (how much does each carry?) ---")
    header()
    full_W = dict(TARGET_WEIGHTS); full_W['B'] = (0.75, 0.25, 0, 0, 0); full_W['C'] = (0.8, 0.2, 0, 0, 0)
    full = evaluate(rows, mk(full_W, 'off', maxvol)); show('FULL STACK', full, base)
    Wb = dict(full_W); Wb['B'] = TARGET_WEIGHTS['B']
    show('  minus B change', evaluate(rows, mk(Wb, 'off', maxvol)), full)
    show('  minus micro OFF (micro back on)', evaluate(rows, mk(full_W, 'both', maxvol)), full)
    Wc = dict(full_W); Wc['C'] = TARGET_WEIGHTS['C']
    show('  minus C change', evaluate(rows, mk(Wc, 'off', maxvol)), full)
    show('  minus max-vol', evaluate(rows, mk(full_W, 'off', None)), full)


if __name__ == '__main__':
    main()
