"""Review items 2, 5, 6, 8 (independent review of 2026-11-11). Research only; nothing live changes.

PRE-REGISTERED before any run (2026-11-11, not edited after). Base = harness.CUR, the live design of the
2026-11-11 session, with VIXM, deep-E and VIX-panic legs, 2 bp per side.
ITEM 2 -- restated expectations (report only, no gate): Sharpe both as the repo reports it (mean/sd) and
  in excess of cash; one session of execution lag; 10-year max-drawdown and Sharpe quantiles from a
  stationary block bootstrap (mean block 20 sessions, 2,000 paths of 2,520 sessions) of the real and the
  proxy daily returns; the live NAV index since 31 Aug against the current design replayed (and the
  caveat that it is not the design as released).
ITEM 5 -- VIXM sleeve size. Arms: V-cap25 (VIXM weight capped at 25% of NAV), V25 (25% of the cash leg),
  VIXY35 (VIXY at 35% of the cash leg, file research_notes/vixm_followups_2026_11/vixy_daily.csv, ends
  2026-11-04 -> later days 0 return), V0 (no sleeve). Reported: CAGR, Sharpe, excess Sharpe, max DD, the
  account's worst day and worst 5 days 2015-2026, the 5th-percentile day, max VIXM weight.
  ACCEPT a cap if it cuts the worst-day / worst-5-day loss and Sharpe falls by no more than 0.05.
ITEM 6 -- gross exposure cap 2.0x (exposure = SPMO + 3 TQQQ + 2 QLD per $). Arms: G-scale (any target above
  2.0x is scaled down to 2.0x, rest to cash), G-ladder (D2 and D3 -> 50% SPMO / 50% TQQQ = 2.0x; A untouched),
  G-scale-all (G-scale + G-ladder). Reported: as item 5 plus the instantaneous loss of the book on a -12% and
  -20% QQQ day for every row held, and bootstrap 10-year max-DD quantiles.
  ACCEPT if the bootstrap median 10-year max DD improves by >= 3 pp and real AND proxy Sharpe fall by no
  more than 0.05 each.
ITEM 8 -- execution. Arms: lag 0 (the backtest = decide and trade at the close), lag 1, half-half (half the
  target change at t's close, half at t+1's), and a circuit breaker CB-X: after a QQQ close-to-close fall of
  X% or worse the book goes to 100% cash at that close for the next 5 sessions (X = 5% pre-registered; 4% and
  6% reported as neighbours). ACCEPT CB-5 if real AND proxy Sharpe do not fall and max DD improves on both,
  at lag 0 and lag 1.
"""
import csv, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import harness as H
from harness import MC, S, np
LOG = open(os.path.join(HERE, 'review_tests_2568_run.log'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); LOG.write(s + '\n'); LOG.flush()
def boot_dd(r, n=2000, T=2520, block=20, seed=7):
    rng = np.random.default_rng(seed); N = len(r); dds, shs = [], []
    for _ in range(n):
        idx = np.empty(T, int); i = rng.integers(N)
        for t in range(T):
            if t and rng.random() >= 1 / block: i = (i + 1) % N
            else: i = rng.integers(N) if t else i
            idx[t] = i
        x = r[idx]; nav = np.cumprod(1 + x); dds.append((nav / np.maximum.accumulate(nav) - 1).min())
        shs.append(x.mean() * 252 / (x.std(ddof=1) * 252 ** .5))
    return np.percentile(dds, [50, 10, 5]), np.percentile(shs, [5, 50, 95])
def tail(r):
    r5 = np.convolve(np.log1p(r), np.ones(5), 'valid')
    return r.min(), np.expm1(r5.min()), np.percentile(r, 5)
log('=' * 110); log('review_tests_2568 (2026-11-11): items 2, 5, 6, 8 of the independent review (pre-registered)'); log('=' * 110)
base = {}
for real in (True, False):
    for lag in (0, 1):
        r, ds, tpy = H.run(real, lag=lag); base[(real, lag)] = (r, ds)
    r, ds = base[(real, 0)]
r_h, ds_h, _ = H.run(False, d1='2015-10-30'); r_h1, _, _ = H.run(False, d1='2015-10-30', lag=1)

log("\nITEM 2 -- restated expectations")
for nm, (r, ds), (r1, _) , real in (('real 2015-11..', base[(True, 0)], base[(True, 1)], True), ('proxy 2001..', base[(False, 0)], base[(False, 1)], False)):
    c = H.cash_for(ds, real); x0, x1 = H.stats(r, c), H.stats(r1, c)
    log(f"  {nm:<16} lag0 {H.fmt(x0)}   lag1 {H.fmt(x1)}")
c = H.cash_for(ds_h, False); log(f"  {'holdout 2001-15':<16} lag0 {H.fmt(H.stats(r_h, c))}   lag1 {H.fmt(H.stats(r_h1, c))}")
for nm, key in (('real', True), ('proxy', False)):
    (q, sq) = boot_dd(base[(key, 0)][0])
    log(f"  bootstrap 10-year paths ({nm}): max DD median {q[0]*100:.1f}%, 10th pct {q[1]*100:.1f}%, 5th pct {q[2]*100:.1f}%; Sharpe 5/50/95 pct {sq[0]:.2f} / {sq[1]:.2f} / {sq[2]:.2f}")
nav = {r['date']: float(r['index_value']) for r in csv.DictReader(open(os.path.join(MC.DATA, 'live_nav_index.csv')))}
r, ds = base[(True, 0)]; i0 = ds.index('2026-09-01'); m = np.cumprod(1 + r[i0:]); dd = [d for d in ds[i0:] if d in nav]
log(f"  live NAV since 31 Aug: {(nav[dd[-1]]-1)*100:+.1f}% to {dd[-1]}; current design replayed {(m[ds[i0:].index(dd[-1])]-1)*100:+.1f}% "
    f"(replayed design is the 11 Nov one, not what was live each day)")

def run_set(arms, reals=(True, False)):
    out = {}
    for nm, kw in arms:
        for real in reals:
            if not real and kw.get('_real_only'): continue
            k = {a: b for a, b in kw.items() if not a.startswith('_')}
            r, ds, tpy = H.run(real, **k); out[(nm, real)] = (r, ds, tpy)
    return out
def report(out, names):
    for nm in names:
        for real in (True, False):
            if (nm, real) not in out: continue
            r, ds, tpy = out[(nm, real)]; x = H.stats(r, H.cash_for(ds, real)); w, w5, p5 = tail(r)
            log(f"  {nm:<14}{'real ' if real else 'proxy'} {H.fmt(x)}  worst day {w*100:5.1f}%  worst 5d {w5*100:6.1f}%  5th-pct day {p5*100:5.2f}%  {tpy:.0f} tr/yr")

log("\nITEM 5 -- VIXM sleeve size (real panel only; the proxy has no VIXM)")
vy = {r['d']: float(r['c']) for r in csv.DictReader(open(os.path.join(H.HERE, 'research_notes', 'vixm_followups_2026_11', 'vixy_daily.csv')))}
VIXY_R = MC._rets(vy, H.RD); VIXY_R[0] = 0.0
A5 = [('live V75', {}), ('V-cap25', {'vixm_cap': 0.25}), ('V25', {'vixm_share': 0.25}),
      ('VIXY35', {'vixm_share': 0.35, 'vixm_ret': VIXY_R}), ('V0', {'vixm': False})]
o5 = run_set(A5, reals=(True,)); report(o5, [a for a, _ in A5])
W, L, _ = H.weights(H.sr, H.RD, True); log(f"  live: max VIXM weight {W[:, 4].max()*100:.0f}% of NAV; days with VIXM > 25% of NAV: {(W[:, 4] > 0.25).mean()*100:.1f}%")
l0 = H.stats(o5[('live V75', True)][0]); t0 = tail(o5[('live V75', True)][0])
for nm in ('V-cap25', 'V25', 'VIXY35'):
    x = H.stats(o5[(nm, True)][0]); t = tail(o5[(nm, True)][0])
    ok = (t[0] > t0[0] or t[1] > t0[1]) and x['sh'] >= l0['sh'] - 0.05
    log(f"  verdict {nm}: dSh {x['sh']-l0['sh']:+.3f}, worst day {t0[0]*100:.1f}% -> {t[0]*100:.1f}%, worst 5d {t0[1]*100:.1f}% -> {t[1]*100:.1f}%  => {'ACCEPT' if ok else 'reject'}")

log("\nITEM 6 -- gross exposure cap 2.0x")
LEV = np.array([1.0, 3.0, 2.0, 0.0, 0.0])
def cap_hook(w5, sg, cap=2.0):
    lev = (w5[..., :5] * LEV).sum(-1); f = np.where(lev > cap, cap / np.maximum(lev, 1e-9), 1.0)
    w = w5.copy(); w[..., :4] *= f[..., None]; w[..., 4] = 1 - w[..., :4].sum(-1); return w
LAD = dict(S.D_LADDER_ROWS)
class Ladder:
    def __enter__(self): S.D_LADDER_ROWS.update({'D2': (0.5, 0.5, 0.0), 'D3': (0.5, 0.5, 0.0)})
    def __exit__(self, *a): S.D_LADDER_ROWS.update(LAD)
o6 = run_set([('live', {}), ('G-scale', {'w5_hook': cap_hook})])
with Ladder():
    o6.update(run_set([('G-ladder', {}), ('G-scale-all', {'w5_hook': cap_hook})]))
report(o6, ['live', 'G-scale', 'G-ladder', 'G-scale-all'])
log("  instantaneous book loss on a QQQ day of -12% / -20% (core and QQQ legs 1x, TQQQ 3x, QLD 2x, VIXM +0):")
rows = {'A 40/60': (0.40, 0.60, 0), 'B 50/0/0': (0.5, 0, 0), 'D1': S.D_LADDER_ROWS['D1'], 'D2': S.D_LADDER_ROWS['D2'], 'D3': S.D_LADDER_ROWS['D3'],
        'D2/D3 capped': (0.5, 0.5, 0)}
for k, (c_, t_, q_) in rows.items():
    lev = c_ + 3 * t_ + 2 * q_
    log(f"    {k:<14} exposure {lev:.2f}x: {-lev*12:.0f}% / {-lev*20:.0f}%  (2.0x cap: {-min(lev, 2)*12:.0f}% / {-min(lev, 2)*20:.0f}%)")
B6 = {}
for nm in ('live', 'G-scale', 'G-ladder', 'G-scale-all'):
    for real in (True, False):
        q, sq = boot_dd(o6[(nm, real)][0], n=1000); B6[(nm, real)] = q
        log(f"  bootstrap 10y max DD {nm:<12}{'real ' if real else 'proxy'} median {q[0]*100:.1f}%  5th pct {q[2]*100:.1f}%   Sharpe 5/50/95 {sq[0]:.2f}/{sq[1]:.2f}/{sq[2]:.2f}")
for nm in ('G-scale', 'G-ladder', 'G-scale-all'):
    dsr = H.stats(o6[(nm, True)][0])['sh'] - H.stats(o6[('live', True)][0])['sh']
    dsp = H.stats(o6[(nm, False)][0])['sh'] - H.stats(o6[('live', False)][0])['sh']
    dq = min(B6[(nm, True)][0] - B6[('live', True)][0], B6[(nm, False)][0] - B6[('live', False)][0])
    ok = dq >= 0.03 and dsr >= -0.05 and dsp >= -0.05
    log(f"  verdict {nm}: dSh real {dsr:+.3f} proxy {dsp:+.3f}; bootstrap median DD gain (worse panel) {dq*100:+.1f} pp  => {'ACCEPT' if ok else 'reject'}")

log("\nITEM 8 -- execution")
def run_mix(real):
    pn = H.pr if real else H.p; ds = pn['dates']; sg = H.sr if real else H.sig
    W, L, key = H.weights(sg, ds, real)
    W1 = np.concatenate([W[:1], W[:-1]], 0); Wm = 0.5 * W + 0.5 * W1
    s0 = next(i for i, d in enumerate(ds) if d >= ('2015-11-02' if real else '2001-01-02'))
    r, _ = MC.run_strategy(Wm[None], key[None], L[None], s0); return r[0], ds[s0 + 1:]
def cb_hook_factory(X, N=5, real=True):
    pn = H.pr if real else H.p; q = pn['qqq']
    hit = np.zeros(len(q), bool)
    for t in np.where(q <= -X)[0]: hit[t:t + N + 1] = True
    def hook(w5, sg):
        w = w5.copy(); w[0, hit, :4] = 0.0; w[0, hit, 4] = 1.0; return w
    return hook, hit
o8 = {}
for real in (True, False):
    for lag in (0, 1):
        o8[('live', real, lag)] = H.run(real, lag=lag)[:2]
        for X in (0.04, 0.05, 0.06):
            hook, hit = cb_hook_factory(X, real=real)
            o8[(f'CB-{int(X*100)}', real, lag)] = H.run(real, lag=lag, w5_hook=hook, qlegs=True)[:2]
    o8[('half-half', real, 0)] = run_mix(real)
for real in (True, False):
    for nm in ('live', 'half-half', 'CB-4', 'CB-5', 'CB-6'):
        for lag in (0, 1):
            if (nm, real, lag) not in o8: continue
            r, ds = o8[(nm, real, lag)]; x = H.stats(r, H.cash_for(ds, real)); w, w5, _ = tail(r)
            log(f"  {nm:<10}{'real ' if real else 'proxy'} lag{lag} {H.fmt(x)}  worst day {w*100:5.1f}%  worst 5d {w5*100:6.1f}%")
ok = True
for real in (True, False):
    for lag in (0, 1):
        a, b = H.stats(o8[('CB-5', real, lag)][0]), H.stats(o8[('live', real, lag)][0])
        ok &= a['sh'] >= b['sh'] and a['m'] > b['m']
log(f"  verdict CB-5 (Sharpe not lower and max DD better on real and proxy, lag 0 and 1)  => {'ACCEPT' if ok else 'reject'}")
