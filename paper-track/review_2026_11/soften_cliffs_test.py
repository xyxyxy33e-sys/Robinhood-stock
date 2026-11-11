"""Soften-the-cliffs test (review 2026-11-11). Research only; no state/live file is touched.

PRE-REGISTRATION (written before the first run; not edited afterwards)
=====================================================================
Question: an independent reviewer found sharp Sharpe peaks at classifier buffer 1%, D-gate gap200 2%
and macro short MA 50. Does replacing the hard cliffs with smooth versions give a design whose
worst case is better, at no material cost in the typical case?

Baseline ("live"): harness.CUR on the verified engine, exactly as harness.run builds it (A 40/60 +
trim v2, B 50/50, C SPMO, D ladder + 0.5% zone buffer + D gate, vol target max(10d,30d) 20%, 5% band,
VIXM sleeve, deep-E and VIX-panic QQQ legs on the real panel; QQQ legs only on the proxy panel).

Arms (all rewrite only the 5-leg target via harness.weights(w5_hook=...); VIXM / QQQ cash legs are
layered by the harness on top of whatever cash the arm leaves, using the live-variant signals for
their own on/off logic (VIXM 'ungated D2' exclusion, deep-E state, panic latch) -- unchanged):
 S1 soft gate. On an effective-D day (eff == 3, == macro D) where the breadth half does NOT flag
    (breadth pct < 0.20 still sends the row to 100% cash as live), the row is
        w = (1 - f) * w_ungated + f * cash_row,   f = clip((0.04 - gap200) / 0.04, 0, 1)
    where w_ungated = MC.target_weights(sig, CUR with d_gate=False) (same ladder/zone buffer and
    vol target), cash_row = (0,0,0,0,1). gap200 NaN -> f = 0 (live: NaN never flags).
 S2 classifier ensemble. 5-leg target = equal-weight mean of MC.target_weights over 9 signal
    variants: buffer b in {0.5%, 1%, 1.5%} x macro short MA m in {40, 50, 60}; long MA 200; fast
    overlay windows 20/100 unchanged. The classifier buffer is ONE parameter in the live code
    (MC._classify default for both macro and fast), so a variant's b applies to both macro and fast
    classifiers. Each variant recomputes macro, fast, eff, held trim votes, D gate (breadth/gap200
    halves on its own macro D) and uses the shared gaps, vol, breadth pct, raw votes, zone.
 S3 S1 inside S2: each of the 9 variants gets the S1 soft gate, then the mean is taken.
Rebalancing key (choice stated up front): every arm uses the LIVE variant's regime key
(b=1%, m=50, hard-gate flag, zone, held votes, + the harness's VIXM/QQQ-leg terms). Moves of the
averaged / blended target between key changes trade only via the engine's 5% L1 drift band and the
zero-leg stub rule. No new key terms.

Evaluation: periods real 2015-11-02..latest (real-ETF panel), proxy 2001-01-02..latest, holdout
proxy 2001-01-02..2015-10-30; costs 2 bp and 10 bp per side; execution lag 0 and 1 session.
Metrics: Sharpe (mean/sd, annualised, no rf), excess-of-cash Sharpe, CAGR, max DD, trades/yr.

Verdict rule (pre-registered): at 2 bp, take the 6 Sharpe values {real, proxy, holdout} x {lag 0,
lag 1}. An arm is "MORE ROBUST" iff (a) its minimum of the 6 > live's minimum, and (b) its median
of the 6 is within 0.05 of live's (read as: not lower than live median - 0.05; a higher median is
not a failure; the literal |diff| is also printed). The same rule is printed at 10 bp as a
secondary check (does not change the verdict). Reported regardless of outcome.

Sensitivity map (2 bp, lag 0, Sharpe on real / proxy / holdout):
 live: hard gate threshold T in {1%, 2%, 3%} x buffer b in {0.5%, 1%, 1.5%} (macro MA 50).
 S3 at (T, b): soft-gate ramp f = clip((2T - gap200) / (2T), 0, 1) (midpoint at T; T=2% is S3);
    ensemble buffers {0.5b, b, 1.5b} x MAs {40, 50, 60}; key from the (b, 50) variant.
 Supplementary 1-D slice: macro short MA M in {40, 50, 60} at T=2%, b=1% (live uses M; S3 uses
    {M-10, M, M+10}). Flatness = max - min Sharpe across each grid, per period; a flatter peak =
    smaller spread and the centre not a lone maximum.
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as H
MC, S = H.MC, H.S

QPX = (100 * np.cumprod(1 + H.p['qqq']))[None]
SHARED = ('gaps', 'vol', 'vol10', 'pct', 'votes', 'zone')


def _held(eff, qpx, votes):
    """Copy of MC.signals' trim-v2 held-vote recursion for a given eff."""
    P, T = eff.shape
    held = np.zeros((P, T), np.int8); h = np.zeros(P, np.int8); gapn = np.zeros(P, int)
    for t in range(T):
        ina = eff[:, t] == 0
        gapn = np.where(ina, 0, gapn + 1)
        h = np.where(~ina & (gapn > S.A_SPELL_GAP_CARRY), 0, h)
        hi15 = qpx[:, t] >= qpx[:, max(0, t - 14):t + 1].max(1)
        raw = votes[:, t]
        nh = np.where(raw > h, raw, np.where((h > raw) & hi15, h - 1, h))
        h = np.where(ina, nh, h).astype(np.int8)
        held[:, t] = np.where(ina, h, 0)
    return held


_PROXY = {}
def proxy_sig(buf=0.01, ms=50, th=S.D_GATE_GAP200):
    """Signal dict on the proxy panel for a (buffer, macro short MA, gap200 threshold) variant."""
    k = (round(buf, 6), ms, round(th, 6))
    if k in _PROXY: return _PROXY[k]
    base = H.sig
    macro = MC._classify(QPX, ms, 200, buf)
    fast = MC._classify(QPX, 20, 100, buf)
    eff = macro.copy(); eff_slow = macro.copy()
    eff[(macro == 1) & (fast <= 1)] = 0
    eff[(macro == 2) & (fast <= 1)] = 0
    eff[(macro == 5) & (fast <= 2)] = 2
    out = {n: base[n] for n in SHARED}
    held = _held(eff, QPX, base['votes'])
    gate_b = (macro == 3) & (base['pct'] < S.D_GATE_BREADTH_PCT)
    gate_g = (macro == 3) & (base['gaps'][200] < th)
    out.update(macro=macro, fast=fast, eff=eff, eff_slow=eff_slow, held=held, gate_b=gate_b,
               gate_g=gate_g, gate=gate_b | gate_g)
    _PROXY[k] = out
    return out


_REAL = {}
def get_sig(real, buf=0.01, ms=50, th=S.D_GATE_GAP200):
    if not real: return proxy_sig(buf, ms, th)
    k = (round(buf, 6), ms, round(th, 6))
    if k not in _REAL: _REAL[k] = H.slice_sig(proxy_sig(buf, ms, th), H.OFF)
    return _REAL[k]


def soft(v, T=S.D_GATE_GAP200):
    """S1 soft gate on one signal variant: ramp f = clip((2T - gap200)/(2T), 0, 1) on non-breadth-gated D."""
    w = MC.target_weights(v, H.CUR)
    wu = MC.target_weights(v, dict(H.CUR, d_gate=False))
    g = np.nan_to_num(v['gaps'][200], nan=np.inf)
    f = np.clip((2 * T - g) / (2 * T), 0.0, 1.0)
    m = (MC._eff(v, H.CUR) == 3) & ~v['gate_b']
    w4 = np.where(m[..., None], (1 - f)[..., None] * wu[..., :4], w[..., :4])
    w = w.copy(); w[..., :4] = w4; w[..., 4] = 1.0 - w4.sum(-1)
    return w


def arm_w5(arm, real, T=S.D_GATE_GAP200, b=0.01, M=50):
    """5-leg target for an arm at sensitivity point (T, b, M)."""
    if arm == 'live':
        return MC.target_weights(get_sig(real, b, M, T), H.CUR)
    if arm == 'S1':
        return soft(get_sig(real, b, M, T), T)
    vs = [get_sig(real, b * s, M + dm, T) for s in (0.5, 1.0, 1.5) for dm in (-10, 0, 10)]
    if arm == 'S2':
        return np.mean([MC.target_weights(v, H.CUR) for v in vs], 0)
    if arm == 'S3':
        return np.mean([soft(v, T) for v in vs], 0)
    raise ValueError(arm)


def run(arm, real, d0=None, d1='2099', lag=0, cost=None, T=S.D_GATE_GAP200, b=0.01, M=50, _cache={}):
    """harness.run with the signal variant (key, VIXM/QQQ legs) = (T, b, M) and the arm's 5-leg target."""
    pn = H.pr if real else H.p; ds = pn['dates']; sg = get_sig(real, b, M, T)
    d0 = d0 or ('2015-11-02' if real else '2001-01-02')
    ck = (arm, real, round(T, 6), round(b, 6), M)
    if ck not in _cache:
        w5 = arm_w5(arm, real, T, b, M)
        _cache[ck] = H.weights(sg, ds, real, w5_hook=lambda _w, _s: w5)
    W, L, key = _cache[ck]
    if lag:
        W = np.concatenate([np.repeat(W[:1], lag, 0), W[:-lag]], 0); key = np.concatenate([np.repeat(key[:1], lag), key[:-lag]])
    s0 = next(i for i, d in enumerate(ds) if d >= d0); e = max(i for i, d in enumerate(ds) if d <= d1)
    old = MC.COST
    if cost is not None: MC.COST = cost
    try:
        r, tr = MC.run_strategy(W[None, :e + 1], key[None, :e + 1], L[None, :e + 1], s0)
    finally:
        MC.COST = old
    return r[0], ds[s0 + 1:e + 1], tr[0] / ((e - s0) / 252)


PERIODS = {'real': (True, None, '2099'), 'proxy': (False, None, '2099'), 'holdout': (False, None, '2015-10-30')}
ARMS = ('live', 'S1', 'S2', 'S3')


def main():
    # ---- reproduction checks
    v0 = proxy_sig()
    for k in ('macro', 'fast', 'eff', 'held', 'gate', 'gate_b', 'gate_g'):
        assert np.array_equal(v0[k], H.sig[k]), k
    for nm, (real, d0, d1) in PERIODS.items():
        a, _, _ = run('live', real, d0, d1); h, _, _ = H.run(real, d0, d1, 0)
        assert np.allclose(a, h, atol=1e-14), nm
    # S1 at a hard-gate-equivalent check: ramp with T -> soft rows must equal live off D
    w_l, w_s = arm_w5('live', False), arm_w5('S1', False)
    offD = MC._eff(v0, H.CUR) != 3
    assert np.allclose(w_l[offD], w_s[offD])
    print('checks: variant(1%,50,2%) == MC.signals; live run == harness.run on 3 periods; S1 == live off D')

    # ---- descriptive: how often do the arms differ from live
    eff = MC._eff(v0, H.CUR)[0]; ds = H.PD
    for arm in ARMS[1:]:
        d = np.abs(arm_w5(arm, False) - w_l).sum(-1)[0]
        print(f'{arm}: sessions with L1 target diff > 1% vs live: {(d > 0.01).mean()*100:5.1f}% '
              f'(on D: {(d[eff == 3] > 0.01).mean()*100:5.1f}%), mean L1 diff {d.mean():.3f}')

    # ---- main table
    res = {}
    print('\nMAIN TABLE  (CAGR / Sharpe (ex-cash Sharpe) / maxDD, trades/yr)')
    for cost in (0.0002, 0.0010):
        for lag in (0, 1):
            print(f'\n-- cost {cost*1e4:.0f} bp, lag {lag}')
            print(f"{'arm':5s} " + ''.join(f'{nm:>44s}' for nm in PERIODS))
            for arm in ARMS:
                row = f'{arm:5s} '
                for nm, (real, d0, d1) in PERIODS.items():
                    r, dd, tpy = run(arm, real, d0, d1, lag, cost)
                    st = H.stats(r, H.cash_for(dd, real)); res[(arm, nm, cost, lag)] = st
                    row += f'{H.fmt(st):>36s} {tpy:4.0f}t/y'
                print(row)

    # ---- verdict
    print('\nVERDICT (Sharpe over {real,proxy,holdout} x {lag0,lag1})')
    verdict = {}
    for cost in (0.0002, 0.0010):
        base = [res[('live', nm, cost, lg)]['sh'] for nm in PERIODS for lg in (0, 1)]
        bmin, bmed = min(base), float(np.median(base))
        tag = 'PRIMARY' if cost == 0.0002 else 'secondary'
        print(f'-- {cost*1e4:.0f} bp ({tag}): live min {bmin:.3f} median {bmed:.3f}')
        for arm in ARMS[1:]:
            x = [res[(arm, nm, cost, lg)]['sh'] for nm in PERIODS for lg in (0, 1)]
            mn, md = min(x), float(np.median(x))
            ok = (mn > bmin) and (md >= bmed - 0.05)
            if cost == 0.0002: verdict[arm] = ok
            print(f'   {arm}: min {mn:.3f} ({mn-bmin:+.3f})  median {md:.3f} ({md-bmed:+.3f}, |diff|<=0.05: {abs(md-bmed)<=0.05})'
                  f'  -> {"MORE ROBUST" if ok else "not more robust"}')

    # ---- sensitivity map
    print('\nSENSITIVITY (2 bp, lag 0): Sharpe real / proxy / holdout')
    for arm in ('live', 'S3'):
        grid = {}
        print(f'\n-- {arm}: rows gate threshold T, cols buffer b (macro MA 50)')
        print('  T \\ b ' + ''.join(f'{b*100:>24.1f}%' for b in (0.005, 0.01, 0.015)))
        for T in (0.01, 0.02, 0.03):
            row = f'  {T*100:3.0f}%  '
            for b in (0.005, 0.01, 0.015):
                sh = [H.stats(run(arm, real, d0, d1, 0, 0.0002, T=T, b=b)[0])['sh'] for real, d0, d1 in PERIODS.values()]
                grid[(T, b)] = sh
                row += '   ' + ' / '.join(f'{s:.3f}' for s in sh)
            print(row)
        for i, nm in enumerate(PERIODS):
            vals = [g[i] for g in grid.values()]; c = grid[(0.02, 0.01)][i]
            print(f'  {nm:8s} spread (max-min) {max(vals)-min(vals):.3f}  centre {c:.3f}  '
                  f'centre - mean(neighbours) {c - np.mean([v for k, g in grid.items() if k != (0.02, 0.01) for v in [g[i]]]):+.3f}')
        print(f'  1-D macro MA slice (T=2%, b=1%):')
        for M in (40, 50, 60):
            sh = [H.stats(run(arm, real, d0, d1, 0, 0.0002, M=M)[0])['sh'] for real, d0, d1 in PERIODS.values()]
            print(f'    M={M}: ' + ' / '.join(f'{s:.3f}' for s in sh))

    print('\nSUMMARY verdict @2bp: ' + ', '.join(f'{a}: {"MORE ROBUST" if v else "not more robust"}' for a, v in verdict.items()))


if __name__ == '__main__':
    main()
