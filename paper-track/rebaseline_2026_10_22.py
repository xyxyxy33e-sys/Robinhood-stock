"""Re-baseline of the LIVE design as of 2026-10-22 (owner: "run the re-baseline").

One run of exactly what trades after the day's changes, so live results can be judged
against a single reference instead of figures from several separate studies:
  A 40/60 SPMO/TQQQ (every A session from 2026-10-22) + extension trim v2 with carry 3,
  B 75/25, C 100% SPMO, E/F cash, fast 20/100 re-entry, D gate, D ladder
  (D1 50% SPMO / 50% QLD, D2 50% TQQQ / 50% QLD, D3 100% TQQQ), vol target 20% on
  max(10d, 30d) QQQ vol, 5% drift band + zero-leg stubs + regime triggers, 4bp one way,
  decide at close t / earn t+1, and (real panel) the VIXM cash sleeve: 75% of the cash leg
  in VIXM while state.vixm_series() says allowed, except on ungated D2 days (2026-10-22) (latch VIX<18 & VIX<=VIX3M on, VIX>VIX3M
  off; plain-30d QQQ vol >= 20%; 25% fade). An `allowed` flip is a regime trigger.
Engine: monte_carlo.py (verified day by day against state.py). VIXM: data/vixm_daily.csv
(Robinhood daily closes, split-adjusted), VIX/VIX3M from vol_curve.history (CBOE, else FRED).
The proxy panel (2001-2026) has no VIXM (VIXM starts 2011): its cash leg is all T-bill.
Price-only on the real panel (as the standing figures). Research record, not a design change.

    python3 paper-track/rebaseline_2026_10_22.py
"""
import csv, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import monte_carlo as MC, state as S, vol_curve as VC

LIVE = dict(MC.LIVE, name='2026-10-22 live', a_base=(0.40, 0.60), vol='max10_30')
PRE = dict(MC.LIVE, name='before 2026-10-22 (A 25/75, D3 25/75, plain 30d)', a_base=(0.25, 0.75), vol='30')
assert S.VIXM_OFF_D_ZONES == ('D2',) and S.D_LADDER_ROWS['D3'] == (0.0, 1.0, 0.0) and S.A_BASE_FROM_SESSION[1] == (0.40, 0.60) and S.VOL_ESTIMATOR_MAX_ENABLED
LOG = open(os.path.join(HERE, 'research_notes', 'rebaseline_2026_10_22_run.log'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); LOG.write(s + '\n'); LOG.flush()

p = MC.load_panel('proxy'); dates = p['dates']
qpx = 100 * np.cumprod(1 + p['qqq']); ewpx = 100 * np.cumprod(1 + p['ew'])
sig = MC.signals(qpx[None], ewpx[None])
pr = MC.load_panel('real'); off = dates.index(pr['dates'][0])
sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items()}

# ---- VIXM sleeve on the real panel, from state.py's own latch
try:
    vix, vsrc = VC.history('VIX'); vix3m, v3src = VC.history('VIX3M')
except Exception as e:        # offline: local FRED files
    rd = lambda f, c: {r['observation_date']: float(r[c]) for r in csv.DictReader(open(os.path.join(MC.DATA, f))) if r[c] not in ('', '.')}
    vix, vix3m, vsrc, v3src = rd('vixcls_full.csv', 'VIXCLS'), rd('vxvcls.csv', 'VXVCLS'), 'FRED (local)', 'FRED (local)'
rdates = pr['dates']
vol30 = {d: (None if np.isnan(v) else float(v)) for d, v in zip(rdates, sr['vol'][0])}      # plain 30d, as pinned
VX = S.vixm_series(rdates, vix, vix3m, vol30)
allowed = np.array([bool(VX.get(d, {}).get('allowed')) for d in rdates])
vm = {r['d']: float(r['c']) for r in csv.DictReader(open(os.path.join(MC.DATA, 'vixm_daily.csv')))}
vixm_r = MC._rets(vm, rdates); vixm_r[0] = 0.0

def run(sg, pn, d0, cfg, d3=None, vixm=False, d1='2099'):
    saved = S.D_LADDER_ROWS['D3']
    if d3 is not None: S.D_LADDER_ROWS['D3'] = d3
    try:
        ds = pn['dates']; s0 = next(i for i, d in enumerate(ds) if d >= d0); e = max(i for i, d in enumerate(ds) if d <= d1)
        sg = {k: (v[:, :e + 1] if not isinstance(v, dict) else {n: a[:, :e + 1] for n, a in v.items()}) for k, v in sg.items()}
        w = MC.target_weights(sg, cfg); key = MC.regime_key(sg, cfg)
        legs = [pn['core'], pn['tqqq'], pn['qld'], pn['xlu'], pn['cash']]
        if vixm:
            al = allowed[:e + 1].copy()
            if cfg is LIVE:   # VIXM off in ungated D2 (owner, 2026-10-22; state.VIXM_OFF_D_ZONES)
                effv = MC._eff(sg, cfg)[0]
                al &= ~((effv == 3) & ~sg['gate'][0].astype(bool) & (sg['zone'][0] == 2))
            v = np.where(al, w[0, :, 4] * S.VIXM_CASH_SHARE, 0.0)
            w = np.concatenate([w[..., :4], v[None, :, None], (w[0, :, 4] - v)[None, :, None]], -1)
            key = key + al[None].astype(int) * 100000
            legs = legs[:4] + [vixm_r] + [legs[4]]
        L = np.stack([x[:e + 1] for x in legs], -1)[None]
        r, tr = MC.run_strategy(w, key, L, s0)
        return r[0], tr[0] / ((e - s0) / 252), ds[s0 + 1:e + 1], w[0, s0:e]
    finally:
        S.D_LADDER_ROWS['D3'] = saved

def prof(r, cash=None):
    nav = np.cumprod(1 + r); pk = np.maximum.accumulate(np.concatenate([[1.0], nav]))[1:]; dd = nav / pk - 1
    n = len(r); cagr = nav[-1] ** (252 / n) - 1; sd = r.std(ddof=1)
    eps = []; st = None; wst = 0
    for j, x in enumerate(dd):
        if x < 0 and st is None: st, wst = j, x
        elif x < 0: wst = min(wst, x)
        elif st is not None: eps.append((st, j, wst)); st = None
    if st is not None: eps.append((st, n, wst))
    yrs = n / 252
    return dict(cagr=cagr, sh=r.mean() * 252 / (sd * 252 ** 0.5), vol=sd * 252 ** 0.5, mdd=dd.min(), avg=dd.mean(),
                p95=np.percentile(dd, 5), n15=sum(w <= -0.15 for *_, w in eps), yrs=yrs,
                rec=np.median([b - a for a, b, w in eps if w <= -0.05] or [0]), longest=max([b - a for a, b, _ in eps] or [0]),
                worst12=min(np.prod(1 + r[i:i + 252]) - 1 for i in range(0, max(1, n - 252), 5)))
def yearly(r, ds):
    y = {}
    for d, x in zip(ds, r): y.setdefault(d[:4], []).append(x)
    return {k: np.prod(1 + np.array(v)) - 1 for k, v in y.items()}
H = f"  {'':<44}{'CAGR':>7}{'Sharpe':>8}{'vol':>7}{'max DD':>8}{'avg DD':>8}{'95th DD':>9}{'worst 12m':>10}{'-15% eps':>9}{'med recov':>10}{'longest':>8}{'trades/yr':>10}"
def row(lab, r, tpy=None):
    m = prof(r)
    log(f"  {lab:<44}{m['cagr']*100:6.1f}%{m['sh']:8.3f}{m['vol']*100:6.1f}%{m['mdd']*100:7.1f}%{m['avg']*100:7.1f}%{m['p95']*100:8.1f}%"
        f"{m['worst12']*100:9.1f}%{m['n15']:9d}{m['rec']:9.0f}d{m['longest']:7d}d" + (f"{tpy:10.0f}" if tpy is not None else ''))
    return m

log('=' * 150); log('RE-BASELINE of the live design, 2026-10-22'); log('=' * 150)
log(f"  VIX history: {vsrc}; VIX3M history: {v3src}; VIXM closes {min(vm)}..{max(vm)}")
# REAL
r, tpy, ds, w = run(sr, pr, '2015-11-02', LIVE, vixm=True)
s0 = next(i for i, d in enumerate(rdates) if d >= '2015-11-02')
log(f"\n  REAL ETFs {ds[0]}..{ds[-1]} (price-only; VIXM on {allowed[s0:].mean()*100:.1f}% of sessions)"); log(H)
mL = row('LIVE 2026-10-22 (with VIXM)', r, tpy); yL = yearly(r, ds)
r2, t2, _, _ = run(sr, pr, '2015-11-02', LIVE); row('LIVE 2026-10-22, no VIXM', r2, t2)
r3, t3, _, _ = run(sr, pr, '2015-11-02', PRE, d3=(0.25, 0.75, 0.0), vixm=True); row('before today (A 25/75, D3 25/75, 30d vol)', r3, t3); y3 = yearly(r3, ds)
for k, b in (('QQQ', pr['qqq']), ('SPMO', pr['spmo']), ('SPY', pr['spy'])):
    row(f"{k} buy & hold", b[s0 + 1:])
yq = yearly(pr['qqq'][s0 + 1:], ds); ys = yearly(pr['spy'][s0 + 1:], ds)
log("\n  calendar years (real): " + '  '.join(f"{y} {yL[y]*100:+.0f}% (QQQ {yq[y]*100:+.0f}%, SPY {ys[y]*100:+.0f}%)" for y in sorted(yL)))
eff = MC._eff(sr, LIVE)[0, s0:len(rdates) - 1]
expo = (w[:, 0] + 3 * w[:, 1] + 2 * w[:, 2]).mean()
log(f"  average QQQ-equivalent exposure {expo:.2f}x; time by effective state: " +
    ', '.join(f"{L} {np.mean(eff == i)*100:.0f}%" for i, L in enumerate('ABCDEF')))
# PROXY
log(f"\n  PROXY 2001..2026 (QQQ core, synthetic 2x/3x, no VIXM)"); log(H)
rp, tp, dp, _ = run(sig, p, '2001-01-02', LIVE); mP = row('LIVE 2026-10-22', rp, tp)
rq, tq, _, _ = run(sig, p, '2001-01-02', PRE, d3=(0.25, 0.75, 0.0)); row('before today', rq, tq)
sp0 = next(i for i, d in enumerate(dates) if d >= '2001-01-02')
row('QQQ buy & hold (total return)', p['qqq_tr'][sp0 + 1:]); row('SPY buy & hold (total return)', p['spy'][sp0 + 1:])
log(f"\n  HOLDOUT 2001..2015-10 (proxy; before any live parameter was fit)"); log(H)
rh, th, _, _ = run(sig, p, '2001-01-02', LIVE, d1='2015-10-31'); row('LIVE 2026-10-22', rh, th)
rh2, th2, _, _ = run(sig, p, '2001-01-02', PRE, d3=(0.25, 0.75, 0.0), d1='2015-10-31'); row('before today', rh2, th2)
e15 = max(i for i, d in enumerate(dates) if d <= '2015-10-31'); row('QQQ buy & hold', p['qqq_tr'][sp0 + 1:e15 + 1])
yP = yearly(rp, dp)
log("\n  calendar years (proxy): " + '  '.join(f"{y} {yP[y]*100:+.0f}%" for y in sorted(yP)))
