"""Follow-up to the review (owner, 2026-11-11). Report only, no gate. Base = harness.CUR, 2 bp.
(a) The two cheap risk reducers, alone and together: G-scale (any 5-leg target above 2.0x exposure scaled to
    2.0x, rest cash) and VIXY at 35% of the cash leg instead of VIXM at 75%.
(b) Slipped trades: on a random 5% / 10% / 25% of rebalance days the new target is applied one session late
    (the book keeps the old holdings that day); 200 random draws each; real and proxy.
"""
import csv, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import harness as H
from harness import MC, S
LOG = open(os.path.join(HERE, 'followup_risk_exec_run.log'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); LOG.write(s + '\n'); LOG.flush()
LEV = np.array([1.0, 3.0, 2.0, 0.0, 0.0])
def cap_hook(w5, sg, cap=2.0):
    lev = (w5 * LEV).sum(-1); f = np.where(lev > cap, cap / np.maximum(lev, 1e-9), 1.0)
    w = w5.copy(); w[..., :4] *= f[..., None]; w[..., 4] = 1 - w[..., :4].sum(-1); return w
vy = {r['d']: float(r['c']) for r in csv.DictReader(open(os.path.join(H.HERE, 'research_notes', 'vixm_followups_2026_11', 'vixy_daily.csv')))}
VIXY_R = MC._rets(vy, H.RD); VIXY_R[0] = 0.0
def tail(r):
    r5 = np.convolve(np.log1p(r), np.ones(5), 'valid'); return r.min(), np.expm1(r5.min())
def yr(r, ds, y):
    i = [k for k, d in enumerate(ds) if d[:4] == y]; return np.prod(1 + r[i]) - 1
log('=' * 100); log('followup_risk_exec (2026-11-11)'); log('=' * 100)
log("\n(a) two risk reducers")
ARMS = [('live', {}), ('2.0x cap', {'w5_hook': cap_hook}), ('VIXY 35%', {'vixm_share': 0.35, 'vixm_ret': VIXY_R}),
        ('both', {'w5_hook': cap_hook, 'vixm_share': 0.35, 'vixm_ret': VIXY_R})]
for real in (True, False):
    for nm, kw in ARMS:
        if not real and 'vixm_ret' in kw: continue
        r, ds, tpy = H.run(real, **kw); x = H.stats(r, H.cash_for(ds, real)); w1, w5 = tail(r)
        r1, ds1, _ = H.run(real, lag=1, **kw); x1 = H.stats(r1, H.cash_for(ds1, real))
        log(f"  {'real ' if real else 'proxy'} {nm:<10} {H.fmt(x)}  vol {x['v']*100:.1f}%  worst day {w1*100:5.1f}%  worst 5d {w5*100:6.1f}%"
            f"  2022 {yr(r, ds, '2022')*100:+.1f}%  2020 {yr(r, ds, '2020')*100:+.1f}%  | lag1 {H.fmt(x1)}")
W, L, _ = H.weights(H.sr, H.RD, True); Wc, _, _ = H.weights(H.sr, H.RD, True, w5_hook=cap_hook)
lev = (W[:, :5] * LEV).sum(1); levc = (Wc[:, :5] * LEV).sum(1)
log(f"  share of real days above 2.0x exposure: {(lev > 2.0001).mean()*100:.0f}%; mean exposure {lev.mean():.2f}x -> {levc.mean():.2f}x")

log("\n(b) slipped trades (random share of rebalance days executed one session late; 200 draws)")
def run_slip(real, frac, seed):
    pn = H.pr if real else H.p; ds = pn['dates']; sg = H.sr if real else H.sig
    W, L, key = H.weights(sg, ds, real)
    s0 = next(i for i, d in enumerate(ds) if d >= ('2015-11-02' if real else '2001-01-02'))
    rng = np.random.default_rng(seed); T = len(ds)
    h = W[s0].copy(); out = np.zeros(T - s0 - 1); pend = None; band = S.REBALANCE_DRIFT_BAND
    for t in range(s0, T - 1):
        cost = 0.0
        if t > s0:
            tgt = W[t]
            if pend is not None:
                c = np.abs(pend - h).sum(); cost += MC.COST * c; h = pend.copy(); pend = None
            drift = np.abs(tgt - h).sum(); stub = ((tgt == 0) & (h > S.ZERO_LEG_EPS)).any()
            if key[t] != key[t - 1] or drift > band or stub:
                if rng.random() < frac: pend = tgt.copy()
                else: cost += MC.COST * drift; h = tgt.copy()
        r = L[t + 1]; g = (h * r).sum(); out[t - s0] = (1 + g) * (1 - cost) - 1; h = h * (1 + r) / (1 + g)
    return out, ds[s0 + 1:]
for real in (True, False):
    base, ds = run_slip(real, 0.0, 0); xb = H.stats(base)
    ref, _, _ = H.run(real); log(f"  {'real ' if real else 'proxy'} no slips: {H.fmt(xb)} (engine {H.fmt(H.stats(ref))})")
    for frac in (0.05, 0.10, 0.25):
        xs = [H.stats(run_slip(real, frac, s)[0]) for s in range(200)]
        c = np.array([x['c'] for x in xs]); sh = np.array([x['sh'] for x in xs]); m = np.array([x['m'] for x in xs])
        log(f"  {'real ' if real else 'proxy'} {int(frac*100):>2}% of rebalances a day late: CAGR {np.median(c)*100:.1f}% (5-95: {np.percentile(c,5)*100:.1f}..{np.percentile(c,95)*100:.1f}), "
            f"Sharpe {np.median(sh):.3f} ({np.percentile(sh,5):.3f}..{np.percentile(sh,95):.3f}), max DD median {np.median(m)*100:.1f}% worst {m.min()*100:.1f}%")
