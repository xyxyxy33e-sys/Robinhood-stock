"""Out-of-sample test of the VIXM sleeve on earlier history. Research only; touches nothing in the repo.
Run from /home/user/Robinhood-stock:  python3 .../hist_test.py   (needs hist_midterm_proxy.csv from hist_build.py,
hist_data/hist_vixm_2011_2015.csv).  VIXM return series on the proxy panel's dates:
  <= 2011-01-04 : constant-maturity VX months 4-7 roll index built from CFE archive settlements (hist_build.py)
  >  2011-01-04 : real VIXM closes (Robinhood, split-adjusted; data_ext/vixm_daily.csv for 2015-09+)
Cash leg = T-bill (proxy panel). Latch/stress/fade exactly state.vixm_series; D2-off mask as live."""
import csv, os, sys
import numpy as np
HERE = '/home/user/Robinhood-stock/paper-track'; sys.path.insert(0, HERE)
import monte_carlo as MC, state as S, vol_curve as VC
SC = '/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad'
MC.DATA = SC + '/data_ext'
W = SC + '/vixm_scale'
S.A_BASE_FROM_SESSION = ('2026-10-30', (0.20, 0.80))
LIVE = dict(MC.LIVE, name='live', a_base=(0.20, 0.80), vol='max10_30')
OUT = open(W + '/hist_test.log', 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); OUT.write(s + '\n'); OUT.flush()

p = MC.load_panel('proxy'); dates = p['dates']; T = len(dates)
sig = MC.signals((100*np.cumprod(1+p['qqq']))[None], (100*np.cumprod(1+p['ew']))[None])
try:
    vix, vsrc = VC.history('VIX'); vix3m, v3src = VC.history('VIX3M')
except Exception:
    f = lambda fn, c: {r['observation_date']: float(r[c]) for r in csv.DictReader(open(os.path.join(MC.DATA, fn))) if r[c] not in ('', '.')}
    vix, vix3m, vsrc, v3src = f('vixcls_full.csv', 'VIXCLS'), f('vxvcls.csv', 'VXVCLS'), 'FRED local', 'FRED local'
# CBOE's VIX3M csv starts 2009-09-18; the FRED VXVCLS series (same index, ex-VXV) starts 2007-12-04: use CBOE where it exists, FRED before
fr = {r['observation_date']: float(r['VXVCLS']) for r in csv.DictReader(open(os.path.join(MC.DATA, 'vxvcls.csv'))) if r['VXVCLS'] not in ('', '.')}
cm = [d for d in vix3m if d in fr]; dif = np.array([vix3m[d]-fr[d] for d in cm])
log(f'VIX3M CBOE vs FRED on {len(cm)} common days: mean abs diff {np.abs(dif).mean():.3f}, max {np.abs(dif).max():.2f}; filling {sum(1 for d in fr if d not in vix3m)} earlier days from FRED (from {min(fr)})')
vix3m = {**fr, **vix3m}; v3src = 'CBOE + FRED pre-2009-09'
log(f'VIX source {vsrc}; VIX3M source {v3src} (first {min(vix3m)}); panel {dates[0]}..{dates[-1]}, COST={MC.COST}')

# ---- VIXM return series
vm = {}
for fn in (W + '/hist_data/hist_vixm_2011_2015.csv', MC.DATA + '/vixm_daily.csv'):
    for r in csv.DictReader(open(fn)): vm[r['d']] = float(r['c'])
real_r = MC._rets(vm, dates)
lev = {}; x = 1.0
for r in csv.DictReader(open(W + '/hist_midterm_proxy.csv')): x *= 1 + float(r['r']); lev[r['d']] = x
prx_r = MC._rets(lev, dates)                       # forward-fills the one missing proxy day (2008-03-20)
# annual drift gap real-vs-proxy over their overlap (calibrates the "fee/tracking" haircut sensitivity)
ov = [i for i, d in enumerate(dates) if '2011-01-05' <= d <= max(lev) and d in vm]
GAP = (np.log1p(real_r[ov]).sum() - np.log1p(prx_r[ov]).sum()) / (len(ov)/252)
log(f'proxy vs real VIXM overlap {dates[ov[0]]}..{dates[ov[-1]]} n={len(ov)}: corr {np.corrcoef(prx_r[ov], real_r[ov])[0,1]:.3f}, '
    f'annual log-drift gap (VIXM - proxy) {GAP*100:.2f}%/yr')
SPL = '2011-01-04'
def vixm_ret(haircut):
    r = np.zeros(T)
    for i, d in enumerate(dates):
        if d <= SPL: r[i] = (1 + prx_r[i]) * np.exp(haircut*GAP/252) - 1 if prx_r[i] != 0 or d in lev else 0.0
        else: r[i] = real_r[i]
    r[0] = 0.0
    return r
vol30 = {d: (None if np.isnan(v) else float(v)) for d, v in zip(dates, sig['vol'][0])}
VX = S.vixm_series(dates, vix, vix3m, vol30)
allowed0 = np.array([bool(VX.get(d, {}).get('allowed')) for d in dates])
eff = MC._eff(sig, LIVE)[0]
allowed = allowed0 & ~((eff == 3) & ~sig['gate'][0].astype(bool) & (sig['zone'][0] == 2))   # off in ungated D2
w5 = MC.target_weights(sig, LIVE); key0 = MC.regime_key(sig, LIVE)

def run(d0, d1, share, vr, al=allowed):
    s0 = next(i for i, d in enumerate(dates) if d >= d0); e = max(i for i, d in enumerate(dates) if d <= d1)
    a = al.copy()
    v = np.where(a, w5[0, :, 4] * share, 0.0)
    w6 = np.concatenate([w5[..., :4], v[None, :, None], (w5[0, :, 4] - v)[None, :, None]], -1)[:, :e+1]
    L = np.stack([p['core'], p['tqqq'], p['qld'], p['xlu'], vr, p['cash']], -1)[None, :e+1]
    r, tr = MC.run_strategy(w6, (key0 + a[None].astype(int)*100000)[:, :e+1], L, s0)
    return r[0], a[s0:e+1], dates[s0+1:e+1], s0, e

def spells(a):
    out = []; j = 0
    while j < len(a):
        if a[j]:
            k = j
            while k < len(a) and a[k]: k += 1
            out.append((j, k-1)); j = k
        else: j += 1
    return out
def met(r):
    nav = np.cumprod(1+r); pk = np.maximum.accumulate(nav)
    return (nav[-1]**(252/len(r))-1)*100, r.mean()*252/(r.std(ddof=1)*252**.5), (nav/pk).min()*100-100
def yearly(r, ds):
    y = {}
    for d, x in zip(ds, r): y.setdefault(d[:4], []).append(x)
    return {k: (np.prod(1+np.array(v))-1)*100 for k, v in y.items()}

def block(title, d0, d1, vr, shares=(0.0, 0.5, 0.75, 1.0), detail=True):
    log('\n' + '='*118); log(title); log('='*118)
    res = {s: run(d0, d1, s, vr) for s in shares}
    r0, a, ds, s0, e = res[0.0]
    sp = spells(a)
    log(f"  window {ds[0]}..{ds[-1]} ({len(ds)} sessions); sleeve allowed (after D2-off) on {a.mean()*100:.1f}% of sessions, {len(sp)} spells")
    log(f"  {'variant':<30}{'CAGR':>8}{'d CAGR':>8}{'Sharpe':>8}{'maxDD':>8}")
    for s in shares:
        c, sh, dd = met(res[s][0]); c0 = met(r0)[0]
        log(f"  {('no sleeve (cash all T-bill)' if s == 0 else f'VIXM {s*100:.0f}% of cash' + (' (live)' if s == .75 else '')):<30}{c:7.1f}%{c-c0:+8.2f}{sh:8.3f}{dd:7.1f}%")
    if detail:
        rl = res[0.75][0]; yl, y0 = yearly(rl, ds), yearly(r0, ds)
        log('  per-year, live(75%) vs no sleeve (% return):')
        log('    ' + '  '.join(f"{y}: {yl[y]:+.1f} vs {y0[y]:+.1f} ({yl[y]-y0[y]:+.1f})" for y in sorted(yl)))
        nl, n0 = np.cumprod(1+rl), np.cumprod(1+r0)
        log(f"  per-spell (75% sleeve): gain = (NAVwith/NAVwithout ratio change over the spell's earning days) in points of the book")
        log(f"    {'start':<12}{'last day':<12}{'sessions':>9}{'VIX start':>10}{'gain pts':>10}{'VIXM ret%':>10}")
        tot = 0; gains = []
        for i, j in sp:
            k0, k1 = i, j     # allowed at close idx -> earns next session; r index k = day idx - s0 ... (a is offset by s0 already)
            k1 = min(k1, len(rl)-1)
            b = (nl[k0-1]/n0[k0-1]) if k0 > 0 else 1.0
            g = (nl[k1]/n0[k1]/b - 1) * 100
            vr_ = np.prod(1 + vr[s0+1+k0:s0+2+k1]) - 1
            gains.append(g); tot += g
            log(f"    {ds[k0-1] if k0>0 else dates[s0]:<12}{ds[k1]:<12}{j-i+1:9d}{VX[dates[s0+i]]['vix']:10.1f}{g:+10.2f}{vr_*100:+10.1f}")
        gains = np.array(gains)
        if len(gains):
            pos = (gains > 0).sum(); srt = np.sort(gains)[::-1]
            log(f"  spells: {len(gains)}, positive {pos}, negative {len(gains)-pos}; sum of spell gains {tot:+.2f} pts; best 1: {srt[:1].sum():+.2f}, best 3: {srt[:3].sum():+.2f}, worst 3: {np.sort(gains)[:3].sum():+.2f}; "
                f"total CAGR effect with/without {met(rl)[0]-met(r0)[0]:+.2f} pts/yr")
    return res

H0, H1 = '2008-01-02', '2015-10-30'
vr_raw, vr_adj = vixm_ret(0.0), vixm_ret(1.0)
# why so few spells: how often each gate condition holds, by year (sessions with VIX & VIX3M data)
log('\nGATE DIAGNOSTIC (share of sessions): latch ON | stress (QQQ 30d vol>=20%) | latch&stress | allowed after fade+D2-off | VIX<18 | mean VIX')
ys = {}
for i, d in enumerate(dates):
    if d < '2008-01-01' or d not in VX: continue
    x = VX[d]; ys.setdefault(d[:4], []).append((x['on'], x['stress'], x['on'] and x['stress'], bool(allowed[i]), x['vix'] < 18, x['vix']))
for y, v in sorted(ys.items()):
    v = np.array(v, float); log(f"  {y}: n={len(v):3d}  on {v[:,0].mean()*100:5.1f}%  stress {v[:,1].mean()*100:5.1f}%  both {v[:,2].mean()*100:5.1f}%  allowed {v[:,3].mean()*100:5.1f}%  VIX<18 {v[:,4].mean()*100:5.1f}%  meanVIX {v[:,5].mean():.1f}")
block('A. OUT-OF-SAMPLE 2008-01..2015-10, proxy panel; VIXM = CFE VX m4-7 roll index to 2011-01-04 (RAW, no fee), real VIXM after', H0, H1, vr_raw)
block(f'A2. same, but pre-2011 proxy haircut by the measured real-vs-proxy drift gap ({GAP*100:.2f}%/yr) -- conservative', H0, H1, vr_adj)
block('B. 2008-01..2010-12 only (proxy index entirely: raw)', '2008-01-02', '2010-12-31', vr_raw)
block('B2. 2008-01..2010-12 only (proxy index with drift haircut)', '2008-01-02', '2010-12-31', vr_adj)
block('C. 2011-01..2015-10 with REAL VIXM only (strategy started 2011-01-04)', '2011-01-04', H1, vr_raw)
block('D. SANITY: proxy panel 2015-11..2026-10 (real VIXM; proxy panel other legs)', '2015-11-02', dates[-1], vr_raw)

# ---- replicate the known real-panel result with the same code path (harness check)
pr = MC.load_panel('real'); rdates = pr['dates']; off = dates.index(rdates[0])
log('\n' + '='*118); log('E. HARNESS CHECK: real ETF panel 2015-11..2026-10 (known: with VIXM 54.3% / 1.931, without 50.6% / 1.829 at 2bp)'); log('='*118)
sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items()}
vr2 = MC._rets(vm, rdates); vr2[0] = 0.0
al2 = allowed[off:]
w5r = MC.target_weights(sr, LIVE); keyr = MC.regime_key(sr, LIVE); s0 = next(i for i, d in enumerate(rdates) if d >= '2015-11-02')
for share in (0.0, 0.75):
    v = np.where(al2, w5r[0, :, 4]*share, 0.0)
    w6 = np.concatenate([w5r[..., :4], v[None, :, None], (w5r[0, :, 4]-v)[None, :, None]], -1)
    L = np.stack([pr['core'], pr['tqqq'], pr['qld'], pr['xlu'], vr2, pr['cash']], -1)[None]
    r, _ = MC.run_strategy(w6, keyr + al2[None].astype(int)*100000, L, s0)
    c, sh, dd = met(r[0]); log(f"  share {share:.2f}: CAGR {c:.1f}%  Sharpe {sh:.3f}  maxDD {dd:.1f}%  (on {al2[s0:].mean()*100:.1f}%, {len(spells(al2[s0:]))} spells)")
