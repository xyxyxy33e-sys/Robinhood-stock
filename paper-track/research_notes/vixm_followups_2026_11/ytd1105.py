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
HERE = '/home/user/Robinhood-stock/paper-track'; sys.path.insert(0, HERE)
import monte_carlo as MC, state as S, vol_curve as VC
MC.DATA = '/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad/data_ext2'

LIVE = dict(MC.LIVE, name='2026-10-22 live', a_base=(0.40, 0.60), vol='max10_30')
PRE = dict(MC.LIVE, name='before 2026-10-22 (A 25/75, D3 25/75, plain 30d)', a_base=(0.25, 0.75), vol='30')
S.A_BASE_FROM_SESSION = ('2026-10-22', (0.40, 0.60))  # pin the 22 Oct design, as the dashboard bars
LOG = open('/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad/ytd1105.log', 'w')
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


LIVE20 = dict(MC.LIVE, name='current (A 20/80)', a_base=(0.20, 0.80), vol='max10_30')
def ym(r, ds):
    out = {}
    for d, x in zip(ds, r): out.setdefault(d[:7], []).append(x)
    return {k: np.prod(1+np.array(v))-1 for k, v in out.items()}
qd = pr['dates']; s0 = next(i for i, d in enumerate(qd) if d >= '2015-11-02')
for lab, cfg, pin in (('dashboard bars (22 Oct design, A 40/60)', LIVE, ('2026-10-22', (0.40, 0.60))), ('current design (A 20/80)', LIVE20, ('2026-10-30', (0.20, 0.80)))):
    S.A_BASE_FROM_SESSION = pin
    globals()['LIVE'] = cfg if cfg is LIVE else LIVE
    r, tpy, ds, w = run(sr, pr, '2015-11-02', cfg, vixm=True)
    y = yearly(r, ds); m = ym(r, ds)
    nav = np.cumprod(1+r); dd = nav/np.maximum.accumulate(nav)-1
    log(f"{lab}: real ETFs {ds[0]}..{ds[-1]}")
    log("  years: " + '  '.join(f"{k} {v*100:+.1f}%" for k, v in sorted(y.items()) if k >= '2022'))
    log("  2026 months: " + '  '.join(f"{k[5:]} {v*100:+.1f}%" for k, v in sorted(m.items()) if k.startswith('2026')))
    i26 = [i for i, d in enumerate(ds) if d >= '2026-01-01']
    n26 = np.cumprod(1+r[i26]); dd26 = (n26/np.maximum.accumulate(n26)-1).min()
    log(f"  2026 YTD {y['2026']*100:+.1f}%; max DD in 2026 {dd26*100:.1f}%; since 31 Aug {np.prod(1+r[[i for i,d in enumerate(ds) if d>='2026-09-01']])*100-100:+.1f}%")
    log(f"  last 5 sessions: " + '  '.join(f"{d[5:]} {x*100:+.2f}%" for d, x in zip(ds[-5:], r[-5:])))
yq = yearly(pr['qqq'][s0+1:], qd[s0+1:]); ysp = yearly(pr['spmo'][s0+1:], qd[s0+1:])
log(f"  QQQ 2026 {yq['2026']*100:+.1f}%  SPMO 2026 {ysp['2026']*100:+.1f}% (price-only panel)")
