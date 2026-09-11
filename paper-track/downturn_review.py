"""Downturn review: where does the live design lose in states D/E/F, and can
any change to those states be shown to help on BOTH eras plus the standard
controls?  Prompted 2026-09-06 by the monthly table (Jan 2024-Sep 2026): the
strategy's down-capture vs QQQ is 1.44x, and its worst relative months were
all D/E/F months (Mar 2025 E/D, Apr 2025 F/E, Feb 2026 D, Jul 2026 A/D).

Already tested and rejected elsewhere -- NOT re-run here:
  de_substate_search.py   108 D/E substate candidates on 9 QQQ signals (dd252,
                          sma200 slope, price/50d gap, 50/200 gap, mom20,
                          mom12_1, trend R^2, vol ratio, episode age): none
                          survive the max-stat permutation test (best p=0.58)
  improvement_search.py   T1 per-state resweep incl. D=(0.7..1.0 QLD), D=core,
                          E=XLU 0..0.5, E=50/50 core/cash; symmetric
                          hysteresis 0.5-5%; semivol/EWMA/blended vol;
                          vol-target exemption for B/C (MaxDD -52%)
  STRATEGY.md             E=100% cash, E+F cash, D+E+F cash, flat cash in D

New here:
  P1  attribution by state (26y proxy AND 2024-26 real instruments)
  P2  D composition beyond the T1 grid (core+QLD blends, XLU in D)
  P3  D substate on the ONE signal the earlier search did not include:
      price proximity to the 200-day SMA (about-to-break-to-E)
  P4  state-conditional vol target (lower target in D/E, or D/E/F)
  P5  synthetic inverse exposure in E and F (no PSQ/SQQQ data on disk, so
      a -1x / -2x daily-reset synthetic: r = -k*r_qqq + (1+k)*tbill - ER)
  P6  asymmetric hysteresis (fast exit to defensive states, slow re-entry)
  P7  strategy-drawdown kill switch (path dependent: cut risk after a -X%
      drawdown from the 252d NAV high, restore when recovered)

Discipline as in improvement_search.py: search era 2015-11+, holdout
2000-2015, a candidate must improve Sharpe in BOTH; survivors then face an
exposure-matched and a beta-matched control.
"""
import math
import sys

sys.path.insert(0, 'paper-track')
from improvement_search import (build, data, run, evaluate, era, header, show, vt,
                                live_base, SEARCH, HOLDOUT, BAND)
from improvement_search_r2 import beta_of, beta_matched_control, scaled, episodes
from state import TARGET_WEIGHTS, sma, compute_states, VOL_TARGET_PA
from long_history_backtest import yearfrac, START
from drift_band_test import annual_stats, ONE_WAY_SPREAD

INV_ER_PA = 0.95   # %/yr, PSQ/SQQQ-class expense ratio


def synth_inverse(under, k, rate_on):
    """Daily-reset -k x synthetic. Short proceeds plus collateral earn T-bill."""
    ds = sorted(under)
    nav = 1.0
    out = {ds[0]: nav}
    for i in range(1, len(ds)):
        d0, d1 = ds[i - 1], ds[i]
        yf = yearfrac(d0, d1)
        r = under[d1] / under[d0] - 1
        nav *= (1 - k * r + (1 + k) * (rate_on(d0) / 100.0) * yf - (INV_ER_PA / 100.0) * yf)
        out[d1] = nav
    return out


def enrich(rows):
    """Add gap200 (price / 200d SMA - 1), qqq (signal-day to next close QQQ
    return), and inverse legs inv1/inv2 to every row."""
    D = data()
    ds, px = D['ds'], D['qqq']
    v = [px[d] for d in ds]
    idx = {d: i for i, d in enumerate(ds)}
    inv1 = synth_inverse(px, 1, D['rate_on'])
    inv2 = synth_inverse(px, 2, D['rate_on'])
    for r in rows:
        i = idx[r['d']]
        d1 = ds[i + 1]
        r['gap200'] = v[i] / sma(v, i, 200) - 1
        r['gap50'] = v[i] / sma(v, i, 50) - 1
        r['qqq'] = v[i + 1] / v[i] - 1
        r['inv1'] = inv1[d1] / inv1[i and ds[i]] - 1 if False else inv1[d1] / inv1[ds[i]] - 1
        r['inv2'] = inv2[d1] / inv2[ds[i]] - 1
    return rows


# ---------------------------------------------------------------- P1 attribution
def attribution(rows, wfn, label):
    rets, _ = run(rows, wfn)
    by = {}
    for r, x in zip(rows, rets):
        b = by.setdefault(r['state'], dict(n=0, s=0.0, q=0.0, exp=0.0))
        b['n'] += 1
        b['s'] += math.log1p(x)
        b['q'] += math.log1p(r['qqq'])
        b['exp'] += sum(wfn(r)[:4])
    tot_s = sum(b['s'] for b in by.values())
    tot_q = sum(b['q'] for b in by.values())
    print(f"\n{label}: strategy {math.expm1(tot_s)*100:+.0f}% vs QQQ {math.expm1(tot_q)*100:+.0f}% "
          f"(log-return gap {(tot_s-tot_q)*100:+.1f}pp)")
    print(f"{'state':<6}{'days':>6}{'share':>7}{'strat/yr':>10}{'QQQ/yr':>9}{'avg exp':>9}"
          f"{'gap contrib':>13}")
    for st in 'ABCDEF':
        b = by.get(st)
        if not b:
            continue
        yrs = b['n'] / 252
        print(f"{st:<6}{b['n']:>6}{b['n']/len(rows)*100:>6.1f}%"
              f"{math.expm1(b['s']/yrs)*100:>9.1f}%{math.expm1(b['q']/yrs)*100:>8.1f}%"
              f"{b['exp']/b['n']*100:>8.0f}%{(b['s']-b['q'])*100:>+12.1f}pp")


def attribution_real():
    """Same decomposition on the real-instrument 2024-2026 daily window."""
    import monthly_returns as MR
    px, qqq, days = MR.build()
    days = [d for d in days if d >= MR.START]
    out = MR.simulate(px, qqq, days)
    by = {}
    for (d1, st, x), d0 in zip(out, days):
        b = by.setdefault(st, dict(n=0, s=0.0, q=0.0))
        b['n'] += 1
        b['s'] += math.log1p(x)
        b['q'] += math.log1p(qqq[d1] / qqq[d0] - 1)
    tot_s = sum(b['s'] for b in by.values())
    tot_q = sum(b['q'] for b in by.values())
    print(f"\nREAL instruments {days[0]}..{days[-1]}: strategy {math.expm1(tot_s)*100:+.1f}% "
          f"vs QQQ {math.expm1(tot_q)*100:+.1f}% (log gap {(tot_s-tot_q)*100:+.1f}pp)")
    print(f"{'state':<6}{'days':>6}{'strat':>9}{'QQQ':>9}{'gap contrib':>13}")
    for st in 'ABCDEF':
        b = by.get(st)
        if not b:
            continue
        print(f"{st:<6}{b['n']:>6}{math.expm1(b['s'])*100:>+8.1f}%{math.expm1(b['q'])*100:>+8.1f}%"
              f"{(b['s']-b['q'])*100:>+12.1f}pp")


# ---------------------------------------------------------------- generic 6-leg runner
def run6(rows, wfn, band=BAND, killswitch=None):
    """Like improvement_search.run but weights may have a 6th 'inverse' leg
    (index 5 = -1x synthetic) -- cash is index 4. Optional killswitch=(dd, f,
    recover): when the strategy's own NAV drawdown from its 252d high is
    worse than -dd, every non-cash leg is scaled by f until the drawdown is
    back above -recover."""
    held = prev = None
    rets = []
    nav, hist = 1.0, []
    cut = False
    for r in rows:
        t = list(wfn(r))
        if len(t) == 5:
            t.append(0.0)
        if killswitch:
            dd_lim, f, rec = killswitch
            peak = max(hist[-252:]) if hist else nav
            dd = nav / peak - 1
            if cut and dd > -rec:
                cut = False
            elif not cut and dd < -dd_lim:
                cut = True
            if cut:
                t = [t[j] * f for j in (0, 1, 2, 3)] + [0.0] + [t[5] * f]
                t[4] = 1.0 - sum(t)
        key = (r['state'], r['agree'], cut)
        legs = r['legs'] + (r['inv1'],)
        cost = 0.0
        if held is None:
            held = list(t)
        else:
            drift = sum(abs(t[j] - held[j]) for j in range(6))
            if key != prev or drift > band:
                cost = ONE_WAY_SPREAD * drift
                held = list(t)
        g = sum(held[j] * legs[j] for j in range(6))
        rets.append(g - cost)
        dn = 1 + g
        if dn > 0:
            held = [held[j] * (1 + legs[j]) / dn for j in range(6)]
        hist.append(nav)
        nav *= 1 + g - cost
        prev = key
    return rets


def evaluate6(rows, wfn, **kw):
    f = run6(rows, wfn, **kw)
    c, s, m = annual_stats(f)
    _, ss, _ = annual_stats(run6(era(rows, *SEARCH), wfn, **kw))
    _, hs, _ = annual_stats(run6(era(rows, *HOLDOUT), wfn, **kw))
    exp = sum(sum(abs(x) for x in (list(wfn(r)) + [0])[:6] if True) - (list(wfn(r)) + [0])[4]
              for r in rows) / len(rows)
    return dict(cagr=c, sharpe=s, mdd=m, risky=exp, s_sharpe=ss, h_sharpe=hs)


def vt6(w, vol, target=VOL_TARGET_PA):
    """Vol-target a 5- or 6-leg weight vector; every non-cash leg scales."""
    m = 1.0 if not vol else min(1.0, target / vol)
    w = list(w) + [0.0] * (6 - len(w))
    out = [w[j] * m for j in range(6)]
    out[4] = 1.0 - sum(out[j] for j in (0, 1, 2, 3, 5))
    return tuple(out)


def live():
    """The TRUE live design as a weight function: effective state (fast
    overlay), graded extension trim, vol target. 2026-09-11 FIX: this used to
    be vt(W[r['state']], vol) -- the MACRO-ONLY design with neither overlay --
    so exposure_control() benchmarked every candidate (placebos included)
    against a baseline ~0.15 Sharpe below live and flattered all of them
    (found by the rates_signal line, 2026-09-10). Rows must carry 'eff' and
    'gaps' (leverage_under_trim / breadth_signal attach them); a row without
    them raises instead of silently reverting to the old baseline."""
    from state import extension_scale
    def fn(r):
        if 'eff' not in r or 'gaps' not in r:
            raise KeyError("downturn_review.live(): rows need 'eff' and 'gaps' (attach the fast overlay and extension gaps first)")
        w = live_base(r, micro=False)
        w = TARGET_WEIGHTS[r['eff']]
        f = extension_scale(r['eff'], r['gaps'])
        if f < 1:
            w = tuple(a * f for a in w[:4]) + (1 - f * sum(w[:4]),)
        return vt(w, r['vol'])
    return fn


def exposure_control(rows, target_exp, tol=0.002, kmax=8.0):
    """Scale the live baseline so its AVERAGE DEPLOYED CAPITAL matches
    target_exp, then evaluate it.

    2026-09-07 FIX, two defects. (1) The bracket was [0, 1], so the control
    could only scale DOWN; a candidate deploying more capital saturated at
    k = 1.0 and the "control" was just the unscaled baseline. The bracket now
    expands and the result carries `exp_achieved` / `exp_matched`.
    (2) READ THE UNITS. `run()`'s exposure is the sum of the four risky
    WEIGHTS -- capital deployed -- NOT leverage. A 50/50 and a 40/60 SPMO
    /TQQQ A row both deploy 100% and score identically here, so this control
    says nothing about a change that only shifts weight between a 1x and a
    3x instrument. Use `beta_matched_control()` for those. This control is
    the right one for rules that move capital in and out (trims, cash
    gates)."""
    lo, hi = 0.0, 1.0
    base = live()
    while run(rows, scaled(base, hi))[1] < target_exp and hi < kmax:
        lo, hi = hi, hi * 2
    for _ in range(40):
        mid = (lo + hi) / 2
        _, e = run(rows, scaled(base, mid))
        if e < target_exp:
            lo = mid
        else:
            hi = mid
    k = (lo + hi) / 2
    ev = evaluate(rows, scaled(base, k))
    ev['exp_achieved'] = run(rows, scaled(base, k))[1]
    ev['exp_target'] = target_exp
    ev['exp_matched'] = abs(ev['exp_achieved'] - target_exp) <= tol
    ev['k'] = k
    ev['cash_negative'] = k > 1.0
    return k, ev


def controls(rows, label, cand_fn, ev):
    """Print exposure-matched and beta-matched controls for a survivor."""
    k1, c1 = exposure_control(rows, ev['risky'])
    tb = beta_of(rows, cand_fn)
    k2, c2 = beta_matched_control(rows, live(), tb)
    # 2026-09-07: a control that did not reach the candidate's exposure/beta
    # is NOT a comparison -- it must never be reported as PASS.
    ok1 = ev['sharpe'] > c1['sharpe'] and c1.get('exp_matched', True)
    ok2 = ev['sharpe'] > c2['sharpe'] and c2.get('beta_matched', True)
    v1 = 'PASS' if ok1 else ('UNMATCHED' if not c1.get('exp_matched', True) else 'FAIL')
    v2 = 'PASS' if ok2 else ('UNMATCHED' if not c2.get('beta_matched', True) else 'FAIL')
    print(f"   controls for {label}: exposure-matched (k={k1:.3f}, deployed "
          f"{c1.get('exp_achieved', float('nan')):.4f} vs {ev['risky']:.4f}) Sharpe "
          f"{c1['sharpe']:.3f} {v1}; beta-matched (beta {tb:.2f}, k={k2:.3f}, achieved "
          f"{c2.get('beta_achieved', float('nan')):.3f}) Sharpe {c2['sharpe']:.3f} {v2}")
    return ok1 and ok2


def W_with(**kw):
    W = dict(TARGET_WEIGHTS)
    W.update(kw)
    return W


def main():
    rows = enrich(build())
    base = evaluate(rows, live())
    print(f"{len(rows)} days {rows[0]['d']}..{rows[-1]['d']}; S = Sharpe 2015-11+, H = Sharpe 2000-2015")
    header(); show('LIVE (current design)', base)

    # ---------------- P1
    print("\n=== P1: attribution by state (signal-day state, next-close return) ===")
    attribution(rows, live(), '26y proxy 2000-2026')
    attribution(era(rows, *HOLDOUT), live(), 'holdout 2000-2015')
    attribution(era(rows, *SEARCH), live(), 'search 2015-11+')
    attribution_real()

    survivors = []

    def test(label, fn, ev=None, six=False, **kw):
        ev = ev or (evaluate6(rows, fn, **kw) if six else evaluate(rows, fn))
        show(label, ev, base)
        if ev['s_sharpe'] > base['s_sharpe'] and ev['h_sharpe'] > base['h_sharpe']:
            survivors.append((label, fn, ev, six))
        return ev

    # ---------------- P2 D composition
    print("\n=== P2: state D composition (beyond T1 grid) ===")
    header()
    for w in [(0, 0, 0.85, 0, 0.15), (0.3, 0, 0.5, 0, 0.2), (0.5, 0, 0.4, 0, 0.1),
              (0, 0, 0.6, 0, 0.4), (0, 0, 0.5, 0.25, 0.25), (0, 0, 0.7, 0.15, 0.15),
              (0.5, 0, 0, 0.25, 0.25), (0.85, 0, 0, 0, 0.15), (0, 0.5, 0, 0, 0.5)]:
        W = W_with(D=w)
        tag = ' (live)' if w == TARGET_WEIGHTS['D'] else ''
        test(f"D={w}{tag}", lambda r, W=W: vt(live_base(r, W, False), r['vol']))

    # ---------------- P3 D substate: proximity to 200d
    print("\n=== P3: D substate -- price within X% ABOVE the 200d SMA -> scale risky by f ===")
    header()
    for X in (0.01, 0.02, 0.03, 0.05):
        for f in (0.0, 0.5):
            def fn(r, X=X, f=f):
                w = live_base(r, micro=False)
                if r['state'] == 'D' and r['gap200'] < X:
                    w = tuple(x * f for x in w[:4]) + (1 - f * sum(w[:4]),)
                return vt(w, r['vol'])
            test(f"D & gap200<{X*100:.0f}% -> x{f}", fn)
    # the mirror: D far ABOVE the 200d (deep uptrend pullback) -> full risk, near -> cash
    print("   (E analogue: E & price within X% BELOW 200d -> restore risk, i.e. treat as D)")
    header()
    for X in (0.02, 0.03, 0.05):
        def fn(r, X=X):
            w = live_base(r, micro=False)
            if r['state'] == 'E' and r['gap200'] > -X:
                w = TARGET_WEIGHTS['D']
            return vt(w, r['vol'])
        test(f"E & gap200>-{X*100:.0f}% -> D weights", fn)

    # ---------------- P4 state-conditional vol target
    print("\n=== P4: lower volatility target inside D/E (/F) ===")
    header()
    for states in ('D', 'E', 'DE', 'DEF', 'CDE'):
        for tgt in (0.10, 0.15):
            def fn(r, states=states, tgt=tgt):
                t = tgt if r['state'] in states else VOL_TARGET_PA
                return vt(live_base(r, micro=False), r['vol'], t)
            test(f"vol target {tgt:.2f} in {states}", fn)

    # ---------------- P5 inverse exposure
    print("\n=== P5: synthetic inverse (-1x, ER 0.95%) in E and F ===")
    header()
    for st, k in (('F', 0.25), ('F', 0.5), ('F', 1.0), ('E', 0.25), ('E', 0.5), ('EF', 0.25), ('EF', 0.5)):
        def fn(r, st=st, k=k):
            w = list(live_base(r, micro=False)) + [0.0]
            if r['state'] in st:
                w[4] -= k
                w[5] = k
            return vt6(w, r['vol'])
        test(f"{st}: {k:.2f} short via -1x", fn, six=True)
    # F with -2x, half the notional
    for k in (0.125, 0.25):
        def fn(r, k=k):
            w = list(live_base(r, micro=False)) + [0.0]
            if r['state'] == 'F':
                w[4] -= k * 2
                w[5] = k * 2
            return vt6(w, r['vol'])
        test(f"F: {k*2:.2f} short via -1x (= {k:.3f} of -2x)", fn, six=True)

    # ---------------- P6 asymmetric hysteresis
    print("\n=== P6: asymmetric hysteresis (buf_up = confirm bull, buf_dn = confirm bear) ===")
    header()
    for up, dn in ((0.01, 0.01), (0.02, 0.005), (0.02, 0.01), (0.03, 0.01), (0.01, 0.005),
                   (0.005, 0.01), (0.01, 0.02), (0.005, 0.02), (0.02, 0.02)):
        rows_a = build_asym(rows, up, dn)
        tag = ' (live)' if (up, dn) == (0.01, 0.01) else ''
        ev = evaluate(rows_a, live())
        show(f"buf up {up*100:.1f}% / dn {dn*100:.1f}%{tag}", ev, base)
        if ev['s_sharpe'] > base['s_sharpe'] and ev['h_sharpe'] > base['h_sharpe']:
            survivors.append((f"asym {up}/{dn}", live(), ev, ('asym', up, dn)))

    # ---------------- P7 kill switch
    print("\n=== P7: strategy-NAV drawdown kill switch (cut risky legs to f until recovered) ===")
    header()
    for dd, f, rec in ((0.10, 0.5, 0.05), (0.15, 0.5, 0.075), (0.20, 0.5, 0.10),
                       (0.10, 0.0, 0.05), (0.15, 0.0, 0.075), (0.15, 0.25, 0.05)):
        test(f"kill DD>{dd*100:.0f}% -> x{f}, restore <{rec*100:.1f}%", live(), six=True,
             killswitch=(dd, f, rec))

    # ---------------- controls on survivors
    print(f"\n=== survivors of the both-era hurdle: {len(survivors)} ===")
    passed = []
    for label, fn, ev, six in survivors:
        show(label, ev, base)
        if isinstance(six, tuple):
            rows_a = build_asym(rows, six[1], six[2])
            ok = controls(rows_a, label, fn, ev)
        elif six is True:
            print("   (6-leg / path-dependent candidate: exposure control on |exposure| via live scaling)")
            k1, c1 = exposure_control(rows, ev['risky'])
            ok = ev['sharpe'] > c1['sharpe']
            print(f"   exposure-matched (k={k1:.3f}) Sharpe {c1['sharpe']:.3f} {'PASS' if ok else 'FAIL'}")
        else:
            ok = controls(rows, label, fn, ev)
        if ok:
            passed.append(label)
    print(f"\npassed both controls: {passed or 'NONE'}")


def build_asym(rows, up, dn):
    """Recompute states with asymmetric hysteresis, keep everything else."""
    D = data()
    ds, px = D['ds'], D['qqq']
    v = [px[d] for d in ds]
    s50 = s200 = None
    st = {}
    for i, d in enumerate(ds):
        m50, m200 = sma(v, i, 50), sma(v, i, 200)
        if m200 is None:
            st[d] = 'F'; continue
        if v[i] > m50 * (1 + up): s50 = True
        elif v[i] < m50 * (1 - dn): s50 = False
        if v[i] > m200 * (1 + up): s200 = True
        elif v[i] < m200 * (1 - dn): s200 = False
        cross = m50 > m200
        if s50 and s200 and cross: st[d] = 'A'
        elif s50 and s200 and not cross: st[d] = 'B'
        elif s50 and not s200: st[d] = 'C'
        elif not s50 and s200: st[d] = 'D'
        elif not s50 and not s200 and cross: st[d] = 'E'
        else: st[d] = 'F'
    out = []
    for r in rows:
        r2 = dict(r)
        r2['state'] = st[r['d']]
        out.append(r2)
    return out


if __name__ == '__main__':
    main()
