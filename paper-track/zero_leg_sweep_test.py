"""Should a leg whose TARGET is exactly zero be swept out even when total L1
drift is inside the band?

THE LIVE SYMPTOM (2026-09-04). Realised vol fell below the 20% target, so the
multiplier hit 1.0 and the cash target became exactly 0.00%. The account was
holding 0.50% BOXX. Total L1 drift was 0.99%, inside the 3% band, so nothing
traded -- and nothing will, until some OTHER move pushes drift past 3%. The
stub sits there indefinitely.

Two costs, and they are not the same size:
  - Return drag: 0.5% parked at the T-bill rate instead of ~1.6x equity is
    roughly 5bp/yr while it lasts. Small.
  - BAND BUDGET: the stub contributes 0.5pp of the 0.99% drift -- HALF the
    current reading, and it never decays. A permanent 0.5pp floor on the drift
    metric makes the 3% band behave like a ~2.5% band for real drift. That is
    a quiet degradation of the control, and it is the real argument.

THE CANDIDATE RULE. Fire a rebalance when any leg's target is exactly 0.0 but
it is held above ZERO_LEG_EPS, regardless of total drift. Rationale: a
zero-target leg is not "near its target", it is a position the design says
should not exist.

THE OBJECTION, taken seriously. This is a per-leg trigger, and the per-leg
trade threshold was deliberately REMOVED on 2026-09-01 with "do not reintroduce
one". That removal was about SKIPPING small trades once a rebalance fires; this
is about FIRING one. Different mechanism, but it is still a second condition
bolted onto a control that was simplified on purpose, so it has to earn its
place on the numbers rather than on the argument above.

Measured here on the 2000-2026 daily proxy: CAGR, Sharpe, MaxDD, rebalances
and turnover for the live band alone vs. the band plus the sweep, at several
epsilons.
"""
import sys
sys.path.insert(0, 'paper-track')
from state import target_weights_with_voltarget, TARGET_WEIGHTS
from improvement_search import build, era, SEARCH, HOLDOUT
from drift_band_test import annual_stats, ONE_WAY_SPREAD

BAND = 0.03


def simulate(rows, band=BAND, zero_eps=None):
    """zero_eps=None -> live rule (band only).
    zero_eps=x -> also fire when a leg with target exactly 0 is held above x."""
    held = prev = None
    rets, n_reb, turn, stub_days, stub_sum = [], 0, 0.0, 0, 0.0
    for r in rows:
        t = target_weights_with_voltarget(r['state'], r['agree'], r['vol'])
        key = (r['state'], r['agree'])
        cost = 0.0
        if held is None:
            held = list(t); n_reb += 1
        else:
            drift = sum(abs(t[j] - held[j]) for j in range(5))
            fire = key != prev or drift > band
            if not fire and zero_eps is not None:
                fire = any(t[j] == 0.0 and held[j] > zero_eps for j in range(5))
            if fire:
                turn += drift; cost = ONE_WAY_SPREAD * drift
                held = list(t); n_reb += 1
        # track the stub: weight held in legs whose target is zero
        stub = sum(held[j] for j in range(5) if t[j] == 0.0)
        if stub > 0.001:
            stub_days += 1; stub_sum += stub
        gross = sum(held[j] * r['legs'][j] for j in range(5))
        rets.append(gross - cost)
        dn = 1 + gross
        if dn > 0:
            held = [held[j] * (1 + r['legs'][j]) / dn for j in range(5)]
        prev = key
    yrs = len(rows) / 252.0
    return rets, n_reb / yrs, turn / yrs, stub_days / len(rows), (stub_sum / stub_days if stub_days else 0)


def row(label, rows, **kw):
    r, nreb, turn, stubfrac, stubavg = simulate(rows, **kw)
    c, s, m = annual_stats(r)
    print(f"{label:<26}{c*100:>8.2f}%{s:>8.3f}{m*100:>8.1f}%{nreb:>9.1f}{turn:>9.2f}x"
          f"{stubfrac*100:>9.1f}%{stubavg*100:>8.2f}%")


def main():
    rows = build()
    print(f"{len(rows)} days {rows[0]['d']}..{rows[-1]['d']}  (band {BAND*100:.0f}%)\n")
    hdr = (f"{'rule':<26}{'CAGR':>9}{'Sharpe':>8}{'MaxDD':>8}{'reb/yr':>9}"
           f"{'turn/yr':>9}{'stub days':>9}{'avg stub':>8}")
    for nm, rs in (('FULL 2000-2026', rows), ('OOS 2000-2015', era(rows, *HOLDOUT)),
                   ('fitted 2015-2026', era(rows, *SEARCH))):
        print(f"=== {nm} ({len(rs)} days)"); print(hdr)
        row('live (band only)', rs)
        for eps in (0.0050, 0.0025, 0.0010):
            row(f'+ zero-leg sweep {eps*100:.2f}%', rs, zero_eps=eps)
        print()


if __name__ == '__main__':
    main()
