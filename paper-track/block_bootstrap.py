"""Block bootstrap + leave-one-regime-out for the applied design changes.

Added 2026-09-07 after an outside review made two fair objections to the
existing evidence:
  (1) the max-statistic permutation tests shuffled DAY LABELS, which destroys
      episode persistence -- a persistent signal looks far more significant
      than it is against an i.i.d. null;
  (2) "p = 0.00" was 0 of 200 shuffles, i.e. p < 0.005, not zero.
This replaces the day-level null with a CIRCULAR BLOCK bootstrap that keeps
runs of adjacent days intact, and adds leave-one-major-regime-out checks.

Reported: 95% intervals for the annualized log-return advantage and for the
Sharpe difference, at block lengths 20 and 60 sessions, 2000 resamples.
An interval spanning zero means the historical edge is NOT distinguishable
from sampling noise at that block length -- which is the honest result for
most of these, and is what the earlier p-values overstated.
"""
import sys, math, random
sys.path.insert(0, 'paper-track')
from improvement_search import build, run, vt
from downturn_review import enrich
from state import (TARGET_WEIGHTS as W, compute_fast_states, effective_state,
                   sma, extension_scale)
from improvement_search import data

N_BOOT = 2000
BLOCKS = (20, 60)


def rows_with_overlays():
    rows = enrich(build())
    D = data(); ds, px = D['ds'], D['qqq']
    fast = compute_fast_states(ds, px)
    v = [px[d] for d in ds]; ix = {d: i for i, d in enumerate(ds)}
    for r in rows:
        i = ix[r['d']]
        r['eff'] = effective_state(r['state'], fast[r['d']])
        r['gaps'] = {n: ((v[i] / sma(v, i, n) - 1) if sma(v, i, n) else 0.0)
                     for n in (100, 150, 200)}
    return rows


def trimmed(w, eff, gaps):
    f = extension_scale(eff, gaps)
    return w if f >= 1 else tuple(x * f for x in w[:4]) + (1 - f * sum(w[:4]),)


F = {
    'macro only, vol30':      lambda r: vt(W[r['state']], r['vol']),
    'fast overlay, vol30':    lambda r: vt(W[r['eff']], r['vol']),
    'overlay+trim, vol30':    lambda r: vt(trimmed(W[r['eff']], r['eff'], r['gaps']), r['vol']),
    'LIVE (overlay+trim, max10_30)': lambda r: vt(trimmed(W[r['eff']], r['eff'], r['gaps']), r['vol_live']),
}


def stats(rets):
    n = len(rets)
    mu = sum(rets) / n
    sd = (sum((x - mu) ** 2 for x in rets) / (n - 1)) ** 0.5
    sharpe = mu * 252 / (sd * 252 ** 0.5) if sd > 0 else 0.0
    logret = sum(math.log1p(x) for x in rets) * 252 / n
    return logret, sharpe


def boot(a, b, block, seed):
    """Circular block bootstrap of the PAIRED series (same blocks for both)."""
    rng = random.Random(seed)
    n = len(a)
    nb = math.ceil(n / block)
    dl, ds_ = [], []
    for _ in range(N_BOOT):
        ia, ib = [], []
        for _ in range(nb):
            s = rng.randrange(n)
            for k in range(block):
                ia.append(a[(s + k) % n]); ib.append(b[(s + k) % n])
        ia, ib = ia[:n], ib[:n]
        la, sa = stats(ia); lb, sb = stats(ib)
        dl.append(la - lb); ds_.append(sa - sb)
    dl.sort(); ds_.sort()
    lo, hi = int(0.025 * N_BOOT), int(0.975 * N_BOOT) - 1
    return (dl[lo], dl[hi], sum(1 for x in dl if x <= 0) / N_BOOT,
            ds_[lo], ds_[hi], sum(1 for x in ds_ if x <= 0) / N_BOOT)


COMPARISONS = [
    ('fast re-entry overlay', 'fast overlay, vol30', 'macro only, vol30'),
    ('graded extension trim (step 1/3)', 'overlay+trim, vol30', 'fast overlay, vol30'),
    ('max(10,30) vol estimator', 'LIVE (overlay+trim, max10_30)', 'overlay+trim, vol30'),
    ('all three together', 'LIVE (overlay+trim, max10_30)', 'macro only, vol30'),
]

REGIMES = [
    ('dot-com 2000-2002', '2000-01-01', '2002-12-31'),
    ('GFC 2007-2009', '2007-01-01', '2009-12-31'),
    ('COVID 2020', '2020-01-01', '2020-12-31'),
    ('2022 bear', '2022-01-01', '2022-12-31'),
    ('whole SPMO era 2015-11+', '2015-11-01', '2099-01-01'),
]


if __name__ == '__main__':
    rows = rows_with_overlays()
    series = {k: run(rows, f)[0] for k, f in F.items()}
    print(f"CIRCULAR BLOCK BOOTSTRAP, {N_BOOT} resamples, proxy 2000-2026 daily "
          f"({len(rows)} sessions)\n")
    for lab, cand, base in COMPARISONS:
        a, b = series[cand], series[base]
        la, _ = stats(a); lb, _ = stats(b)
        _, sa = stats(a); _, sb = stats(b)
        print(f"{lab}  (point estimate: {(la-lb)*100:+.2f}pp/yr log-return, "
              f"{sa-sb:+.3f} Sharpe)")
        for blk in BLOCKS:
            l1, l2, pl, s1, s2, ps = boot(a, b, blk, seed=hash((lab, blk)) & 0xffff)
            print(f"   block {blk:>2}d: log-return 95% CI [{l1*100:+.2f}, {l2*100:+.2f}] pp/yr"
                  f"  P(<=0)={pl:.3f}   Sharpe 95% CI [{s1:+.3f}, {s2:+.3f}]  P(<=0)={ps:.3f}")
        print()
    print("LEAVE-ONE-MAJOR-REGIME-OUT (Sharpe difference, full proxy minus that window)")
    for lab, cand, base in COMPARISONS:
        print(f"  {lab}")
        for rlab, a0, b0 in REGIMES:
            keep = [i for i, r in enumerate(rows) if not (a0 <= r['d'] <= b0)]
            ca = [series[cand][i] for i in keep]; cb = [series[base][i] for i in keep]
            _, sa = stats(ca); _, sb = stats(cb)
            la, _ = stats(ca); lb, _ = stats(cb)
            print(f"     drop {rlab:<24} Sharpe {sa-sb:+.3f}   log-return {(la-lb)*100:+.2f}pp/yr")
