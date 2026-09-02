"""Search for a SUBSTATE inside states D and E that would justify a bigger cash
position, using the full 1999-2026 QQQ history.

WHY RETRY. An earlier substate study (paper-track/substate_research.py and
substate_research_deltas.py) found nothing that survived a corner-solution, a
holdout AND a placebo check, and this project concluded the six states were
the right granularity. That study ran on the 2015-11+ SPMO window. State D is
~13.5% of history and state E ~4.2%, so on 11 years that is roughly 370 and
115 trading days -- far too thin to split in half and learn anything. The
merged QQQ series (data/qqq_long_history.csv, 1999-09-15 onward) roughly
triples the sample and, unlike the old window, contains the dot-com crash and
the GFC. That is a legitimate reason to re-run, and the same reason the
state-F conclusion flipped on 2026-09-02.

WHAT IS TESTED. Inside state D (or E) only, on days where a candidate signal
says "this instance is the bad kind", scale the four risky legs by f (f=0.0 ->
fully to cash, f=0.5 -> halfway) and route the freed weight to cash. Every
other state and every other day is untouched, so any measured difference is
attributable to the substate rule alone.

SIGNALS. All computed from QQQ closes available AT the decision date -- no
look-ahead, nothing that needs an outside data feed the live trigger doesn't
already pull:
    dd252      drawdown from the trailing 252-day high
    sma200slp  200-day SMA slope over the last 21 days, % of price
    sma50gap   price vs its 50-day SMA, %
    smagap     50-day SMA vs 200-day SMA, %
    mom20      20-day return
    mom12_1    252-day return excluding the most recent 21 days
    trendr2    63-day OLS R^2 signed by the slope
    volratio   30-day realised vol / 252-day realised vol (vol expansion)
    age        trading days elapsed in the current state episode
A "bad" day is signal <= threshold (or >= for volratio/age, where high is bad).
Thresholds come from the SEARCH era only and are then applied unchanged to the
holdout era.

DISCIPLINE. Four hurdles, all of which a candidate must clear:
  1. Improve full-period Sharpe over the live design at all.
  2. Improve in BOTH eras -- searched on 2015-11+ (the era every live
     parameter was already fit in, so it is contaminated either way) and held
     out on 2000-2015, which is clean for every parameter in state.py.
  3. Beat an EXPOSURE-MATCHED control: flatly de-lever the whole live design
     until its average equity exposure matches the candidate's. This is the
     hurdle that separates "the timing is informative" from "we merely took
     less risk", and it is the check that legitimised the state-F change.
  4. Beat a MAX-STATISTIC permutation test: shuffle which days inside the
     state are flagged (preserving the flag COUNT), recompute, and compare the
     candidate's gain against the distribution of the BEST gain across all
     candidates per shuffle. This prices in the fact that we tried many
     signals, which a per-candidate p-value does not.
"""
import math
import random
import sys

sys.path.insert(0, 'paper-track')
from state import (target_weights_with_voltarget, VOL_TARGET_PA,
                   VOL_LOOKBACK_DAYS, TARGET_WEIGHTS)
from long_history_backtest import (load_px, load_tbill_long, make_rate_lookup,
                                   synth_leveraged, START)
from drift_band_test import build_daily, annual_stats, ONE_WAY_SPREAD

BAND = 0.03
SEARCH_ERA = ('2015-11-01', '2099-12-31')   # where live params were already fit
HOLDOUT_ERA = (START, '2015-10-31')         # clean for every parameter in state.py
N_PERM = 200
HIGH_IS_BAD = {'volratio', 'age'}


# ---------------------------------------------------------------- signals

def build_signals(px, states_by_date):
    """date -> dict of point-in-time signals, all from QQQ closes only."""
    ds = sorted(px)
    v = [px[d] for d in ds]
    rets = [None] + [v[i] / v[i - 1] - 1 for i in range(1, len(v))]
    out = {}
    age = 0
    prev_state = None
    for i, d in enumerate(ds):
        st = states_by_date.get(d)
        age = age + 1 if st is not None and st == prev_state else 0
        prev_state = st
        if i < 252:
            continue
        p = v[i]
        sig = {}
        sig['dd252'] = p / max(v[i - 251:i + 1]) - 1
        sma200 = sum(v[i - 199:i + 1]) / 200
        sma200_prev = sum(v[i - 220:i - 20]) / 200
        sig['sma200slp'] = (sma200 - sma200_prev) / p
        sma50 = sum(v[i - 49:i + 1]) / 50
        sig['sma50gap'] = p / sma50 - 1
        sig['smagap'] = sma50 / sma200 - 1
        sig['mom20'] = p / v[i - 20] - 1
        sig['mom12_1'] = v[i - 21] / v[i - 252] - 1
        # 63-day OLS of log price on time; R^2 signed by slope direction
        n = 63
        ys = [math.log(x) for x in v[i - n + 1:i + 1]]
        xs = list(range(n))
        mx, my = sum(xs) / n, sum(ys) / n
        sxy = sum((xs[k] - mx) * (ys[k] - my) for k in range(n))
        sxx = sum((xs[k] - mx) ** 2 for k in range(n))
        syy = sum((ys[k] - my) ** 2 for k in range(n))
        r2 = (sxy * sxy) / (sxx * syy) if sxx > 0 and syy > 0 else 0.0
        sig['trendr2'] = r2 * (1 if sxy >= 0 else -1)
        v30 = _vol(rets[i - 29:i + 1])
        v252 = _vol(rets[i - 251:i + 1])
        sig['volratio'] = v30 / v252 if v252 else 1.0
        sig['age'] = float(age)
        out[d] = sig
    return out


def _vol(r):
    r = [x for x in r if x is not None]
    if len(r) < 2:
        return 0.0
    m = sum(r) / len(r)
    return (sum((x - m) ** 2 for x in r) / (len(r) - 1)) ** 0.5 * math.sqrt(252)


# ---------------------------------------------------------------- simulation

def simulate(rows, flagged, f, band=BAND):
    """Same daily held-weight-drift model as drift_band_test.simulate, with one
    addition: on a date in `flagged`, the four risky legs are scaled by f and
    the freed weight goes to cash. Returns (daily_net_returns, avg_risky_wt)."""
    held, prev_key = None, None
    rets, risky_sum = [], 0.0
    for r in rows:
        t = target_weights_with_voltarget(r['state'], r['agree'], r['vol'])
        if f is not None and r['d'] in flagged:
            risky = sum(t[:4])
            t = tuple(x * f for x in t[:4]) + (1.0 - risky * f,)
        key = (r['state'], r['agree'])
        cost = 0.0
        if held is None:
            held = list(t)
        else:
            drift = sum(abs(t[j] - held[j]) for j in range(5))
            if key != prev_key or drift > band:
                cost = ONE_WAY_SPREAD * drift
                held = list(t)
        risky_sum += sum(held[:4])
        gross = sum(held[j] * r['legs'][j] for j in range(5))
        rets.append(gross - cost)
        denom = 1.0 + gross
        if denom > 0:
            held = [held[j] * (1 + r['legs'][j]) / denom for j in range(5)]
        prev_key = key
    return rets, risky_sum / len(rows)


def delever(rows, scale, band=BAND):
    """Exposure-matched control: scale the risky legs by `scale` on EVERY day,
    regardless of state. Same average exposure, no timing information."""
    return simulate(rows, set(), None, band) if scale == 1.0 else _delever(rows, scale, band)


def _delever(rows, scale, band=BAND):
    held, prev_key = None, None
    rets, risky_sum = [], 0.0
    for r in rows:
        t0 = target_weights_with_voltarget(r['state'], r['agree'], r['vol'])
        risky = sum(t0[:4])
        t = tuple(x * scale for x in t0[:4]) + (1.0 - risky * scale,)
        key = (r['state'], r['agree'])
        cost = 0.0
        if held is None:
            held = list(t)
        else:
            drift = sum(abs(t[j] - held[j]) for j in range(5))
            if key != prev_key or drift > band:
                cost = ONE_WAY_SPREAD * drift
                held = list(t)
        risky_sum += sum(held[:4])
        gross = sum(held[j] * r['legs'][j] for j in range(5))
        rets.append(gross - cost)
        denom = 1.0 + gross
        if denom > 0:
            held = [held[j] * (1 + r['legs'][j]) / denom for j in range(5)]
        prev_key = key
    return rets, risky_sum / len(rows)


def match_scale(rows, target_exposure, band=BAND):
    lo, hi = 0.0, 1.0
    for _ in range(30):
        mid = (lo + hi) / 2
        _, e = _delever(rows, mid, band)
        if e < target_exposure:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ---------------------------------------------------------------- driver

def era(rows, lo, hi):
    return [r for r in rows if lo <= r['d'] <= hi]


def sharpe(rows, flagged, f):
    r, e = simulate(rows, flagged, f)
    c, s, m = annual_stats(r)
    return c, s, m, e


def main():
    rate_on = make_rate_lookup(load_tbill_long())
    qqq = load_px('data/qqq_long_history.csv')
    xlu = load_px('data/xlu_long_history.csv')
    common = set(qqq) & set(xlu)          # QQQ history now runs past XLU's
    qqq = {d: v for d, v in qqq.items() if d in common}
    xlu = {d: v for d, v in xlu.items() if d in common}
    rows = build_daily(qqq, synth_leveraged(qqq, 2, 0.95, rate_on),
                       synth_leveraged(qqq, 3, 0.84, rate_on), xlu, qqq, rate_on)
    states_by_date = {r['d']: r['state'] for r in rows}
    sigs = build_signals(qqq, states_by_date)
    rows = [r for r in rows if r['d'] in sigs]

    search = era(rows, *SEARCH_ERA)
    holdout = era(rows, *HOLDOUT_ERA)
    print(f"full {rows[0]['d']}..{rows[-1]['d']}  {len(rows)}d   "
          f"search(2015-11+) {len(search)}d   holdout(2000-2015) {len(holdout)}d")
    for st in ('D', 'E'):
        n = sum(1 for r in rows if r['state'] == st)
        ns = sum(1 for r in search if r['state'] == st)
        nh = sum(1 for r in holdout if r['state'] == st)
        print(f"  state {st}: {n} days total ({n/len(rows)*100:.1f}%), "
              f"{ns} in search, {nh} in holdout")

    base = {}
    for nm, rs in (('FULL', rows), ('SEARCH', search), ('HOLDOUT', holdout)):
        base[nm] = sharpe(rs, set(), None)
    print(f"\nLIVE design (no substate), band {BAND*100:.0f}%:")
    for nm in ('FULL', 'SEARCH', 'HOLDOUT'):
        c, s, m, e = base[nm]
        print(f"  {nm:<8} CAGR {c*100:6.2f}%  Sharpe {s:6.3f}  MaxDD {m*100:6.1f}%  avg risky {e*100:5.1f}%")

    signames = sorted(next(iter(sigs.values())).keys())
    results = []
    print(f"\n{'state':<6}{'signal':<11}{'f':>5}{'pct':>6}"
          f"{'  SEARCH dS':>12}{'HOLDOUT dS':>12}{'  FULL dS':>10}"
          f"{'FULL CAGR':>11}{'MaxDD':>8}{'risky':>7}")
    for st in ('D', 'E'):
        st_days_search = [r['d'] for r in search if r['state'] == st]
        for sg in signames:
            hi_bad = sg in HIGH_IS_BAD
            vals = sorted(sigs[d][sg] for d in st_days_search)
            if len(vals) < 30:
                continue
            for pct in (0.33, 0.50, 0.67):
                idx = int(len(vals) * (1 - pct)) if hi_bad else int(len(vals) * pct)
                idx = min(max(idx, 0), len(vals) - 1)
                thr = vals[idx]
                flagged = {r['d'] for r in rows if r['state'] == st and
                           (sigs[r['d']][sg] >= thr if hi_bad else sigs[r['d']][sg] <= thr)}
                for f in (0.0, 0.5):
                    fs = sharpe(rows, flagged, f)
                    ss = sharpe(search, flagged, f)
                    hs = sharpe(holdout, flagged, f)
                    d_full = fs[1] - base['FULL'][1]
                    d_s = ss[1] - base['SEARCH'][1]
                    d_h = hs[1] - base['HOLDOUT'][1]
                    results.append(dict(state=st, sig=sg, pct=pct, f=f, thr=thr,
                                        flagged=flagged, d_full=d_full, d_s=d_s,
                                        d_h=d_h, full=fs))
                    print(f"{st:<6}{sg:<11}{f:>5.1f}{pct*100:>5.0f}%"
                          f"{d_s:>+12.3f}{d_h:>+12.3f}{d_full:>+10.3f}"
                          f"{fs[0]*100:>10.2f}%{fs[2]*100:>7.1f}%{fs[3]*100:>6.1f}%")

    # hurdles 1+2
    survivors = [r for r in results if r['d_full'] > 0 and r['d_s'] > 0 and r['d_h'] > 0]
    print(f"\n{len(survivors)} of {len(results)} candidates improve Sharpe in BOTH eras "
          f"AND full period")
    if not survivors:
        print("=> nothing clears hurdles 1-2. No substate adopted.")
        return
    survivors.sort(key=lambda r: -r['d_full'])
    for r in survivors[:10]:
        c, s, m, e = r['full']
        print(f"  {r['state']} {r['sig']:<10} f={r['f']:.1f} pct={r['pct']*100:.0f}% "
              f"thr={r['thr']:+.4f}  dS_full {r['d_full']:+.3f} "
              f"(S {r['d_s']:+.3f} / H {r['d_h']:+.3f})  "
              f"CAGR {c*100:.2f}% MaxDD {m*100:.1f}% risky {e*100:.1f}%")

    # hurdle 3: exposure-matched control
    print("\n--- hurdle 3: exposure-matched control (full period) ---")
    kept = []
    for r in survivors[:10]:
        sc = match_scale(rows, r['full'][3])
        cc, cs, cm = annual_stats(_delever(rows, sc)[0])
        ok = r['full'][1] > cs
        kept.append((r, cs, ok))
        print(f"  {r['state']} {r['sig']:<10} f={r['f']:.1f} pct={r['pct']*100:.0f}%  "
              f"candidate Sharpe {r['full'][1]:.3f} vs flat-delever {cs:.3f} "
              f"(scale {sc:.3f}, CAGR {cc*100:.2f}%, MaxDD {cm*100:.1f}%)  "
              f"{'PASS' if ok else 'FAIL'}")
    passers = [k[0] for k in kept if k[2]]
    if not passers:
        print("=> nothing clears the exposure-matched control. No substate adopted.")
        return

    # hurdle 4: max-statistic permutation
    print(f"\n--- hurdle 4: max-statistic permutation, {N_PERM} shuffles ---")
    rng = random.Random(20260902)
    by_state = {st: [r['d'] for r in rows if r['state'] == st] for st in ('D', 'E')}
    shapes = sorted({(r['state'], len(r['flagged']), r['f']) for r in results})
    maxstat = []
    for _ in range(N_PERM):
        best = -9
        for st, k, f in shapes:
            fl = set(rng.sample(by_state[st], k)) if k <= len(by_state[st]) else set(by_state[st])
            best = max(best, sharpe(rows, fl, f)[1] - base['FULL'][1])
        maxstat.append(best)
    maxstat.sort()
    for r in passers:
        p = sum(1 for x in maxstat if x >= r['d_full']) / len(maxstat)
        print(f"  {r['state']} {r['sig']:<10} f={r['f']:.1f} pct={r['pct']*100:.0f}%  "
              f"dS {r['d_full']:+.3f}  max-stat p = {p:.3f}  "
              f"{'PASS' if p < 0.05 else 'FAIL'}")
    print(f"  (null max-stat: median {maxstat[len(maxstat)//2]:+.3f}, "
          f"95th pct {maxstat[int(len(maxstat)*0.95)]:+.3f})")


if __name__ == '__main__':
    main()
