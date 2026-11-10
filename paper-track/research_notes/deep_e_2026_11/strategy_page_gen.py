"""Strategy vs Benchmarks page data, 11 Nov 2026 design vs the design live until 10 Nov. Research only."""
import csv, os, sys, json
import numpy as np
HERE = '/home/user/Robinhood-stock/paper-track'; sys.path.insert(0, HERE)
import monte_carlo as MC, state as S, vol_curve as VC
SP = '/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad'
MC.DATA = SP + '/sb_data'; OUTD = SP + '/sb'
S.A_BASE_FROM_SESSION = ('2026-11-06', (0.40, 0.60))
NEW = dict(MC.LIVE, name='11 Nov', a_base=(0.40, 0.60), vol='max10_30')
assert NEW['rows']['B'] == (0.50, 0, 0, 0, 0.50)
OLD = dict(NEW, name='10 Nov', rows=dict(NEW['rows'], B=(0.75, 0.25, 0, 0, 0)))

p = MC.load_panel('proxy'); dates = p['dates']
qfull = 100*np.cumprod(1+p['qqq'])
sig = MC.signals(qfull[None], (100*np.cumprod(1+p['ew']))[None])
pr = MC.load_panel('real'); off = dates.index(pr['dates'][0])
sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items()}
rd = pr['dates']
vix, _ = VC.history('VIX'); vix3m, _ = VC.history('VIX3M')
vol30 = {d: (None if np.isnan(v) else float(v)) for d, v in zip(rd, sr['vol'][0])}
VX = S.vixm_series(rd, vix, vix3m, vol30)
eff_r = MC._eff(sr, NEW)[0]
allowed = np.array([bool(VX.get(d, {}).get('allowed')) for d in rd])
allowed &= ~((eff_r == 3) & ~sr['gate'][0].astype(bool) & (sr['zone'][0] == 2))
_px = {r['d']: float(r['c']) for r in csv.DictReader(open(os.path.join(MC.DATA, 'vixm_daily.csv')))}
vixm_r = MC._rets(_px, rd); vixm_r[0] = 0.0

def qlegs(sg, ds, cfg):
    e = MC._eff(sg, cfg)[0]; g = np.nan_to_num(sg['gaps'][200][0])
    deep = ((e == 4) & (g <= -0.05)).astype(float)*0.5
    on = False; pan = np.zeros(len(ds))
    for i, d in enumerate(ds):
        v = vix.get(d, np.nan)
        if not np.isnan(v):
            if on and v < 25: on = False
            elif not on and v >= 30: on = True
        pan[i] = 0.25 if on else 0.0
    return deep, pan

def run(sg, pn, d0, cfg, qq, vixm=True):
    ds = pn['dates']; s0 = next(i for i, d in enumerate(ds) if d >= d0)
    w5 = MC.target_weights(sg, cfg); key = MC.regime_key(sg, cfg).astype(np.int64)
    cash = w5[0, :, 4].copy()
    legs = [pn['core'], pn['tqqq'], pn['qld'], pn['xlu']]; W = [w5[0, :, i] for i in range(4)]
    used = np.zeros_like(cash)
    if pn is pr and vixm:
        legs.append(vixm_r); W.append(np.where(allowed, cash*S.VIXM_CASH_SHARE, 0.0)); used = W[-1].copy()
        key = key + allowed[None].astype(np.int64)*100000
    if qq:
        deep, pan = qlegs(sg, ds, cfg)
        for j, sh in enumerate((deep, pan)):
            x = np.minimum(cash*sh, cash-used); used = used + x
            legs.append(pn['qqq']); W.append(x); key = key + (sh[None] > 0).astype(np.int64)*(10**(6+j))
    legs.append(pn['cash']); W.append(cash-used)
    r, tr = MC.run_strategy(np.stack(W, -1)[None], key, np.stack(legs, -1)[None], s0)
    return r[0], ds[s0:]           # r aligned to ds[s0+1:]

def stats(r, ds):
    nav = np.cumprod(1+r); dd = nav/np.maximum.accumulate(nav)-1
    yrs = len(r)/252
    y = {}
    for d, x in zip(ds[1:], r): y.setdefault(d[:4], []).append(x)
    y = {k: float(np.prod(1+np.array(v))-1) for k, v in y.items()}
    c = nav[-1]**(1/yrs)-1
    return dict(mult=float(nav[-1]), cagr=float(c), vol=float(r.std(ddof=1)*252**.5), sharpe=float(r.mean()*252/(r.std(ddof=1)*252**.5)),
                dd=float(dd.min()), years=y)

def px_rets(fn, ds, col='c'):
    px = {}
    for row in csv.DictReader(open(os.path.join(MC.DATA, fn))):
        try: px[row['d']] = float(row[col])
        except (ValueError, KeyError): pass
    r = MC._rets(px, ds); r[0] = 0.0; return r

D0 = '2015-11-02'
rn, ds = run(sr, pr, D0, NEW, True)
ro, _ = run(sr, pr, D0, OLD, False)
rnv, _ = run(sr, pr, D0, NEW, True, vixm=False)
s0 = rd.index(ds[0])
bench = {k: pr[k][s0+1:] for k in ('spmo', 'qqq', 'spy')}
res = {'new': stats(rn, ds), 'old': stats(ro, ds), 'new_novixm': stats(rnv, ds)}
for k, v in bench.items(): res[k] = stats(v, ds)
# state letters (effective, new design)
st = ''.join('ABCDEF'[int(x)] for x in eff_r[s0:])
def cum(r): return np.concatenate([[1.0], np.cumprod(1+r)])
N, O = cum(rn), cum(ro); B = {k: cum(v) for k, v in bench.items()}
DATA = [dict(date=d, state=st[i], strategy=round(float(N[i]), 5), spmo=round(float(B['spmo'][i]), 5), qqq=round(float(B['qqq'][i]), 5), spy=round(float(B['spy'][i]), 5)) for i, d in enumerate(ds)]
COMP = [dict(date=d, state=st[i], old=round(float(O[i]), 5), new=round(float(N[i]), 5), spmo=round(float(B['spmo'][i]), 5), qqq=round(float(B['qqq'][i]), 5), spy=round(float(B['spy'][i]), 5)) for i, d in enumerate(ds)]
# DMA: QQQ close (price), 50/200 SMA, state
qpx = {}
for row in csv.DictReader(open(os.path.join(MC.DATA, 'qqq_long_history.csv'))): qpx[row['d']] = float(row['c'])
qd = sorted(qpx); qv = np.array([qpx[d] for d in qd])
s50 = MC._sma(qv[None], 50)[0]; s200 = MC._sma(qv[None], 200)[0]
DMA = [dict(date=d, close=round(float(qv[qd.index(d)]), 2), sma50=round(float(s50[qd.index(d)]), 4), sma200=round(float(s200[qd.index(d)]), 4), state=st[i]) for i, d in enumerate(ds)]
# time in QQQ legs / VIXM
deep, pan = qlegs(sr, rd, NEW)
res['share'] = dict(vixm=float(allowed[s0:].mean()), deep=float((deep[s0:] > 0).mean()), panic=float((pan[s0:] > 0).mean()),
                    state={L: st.count(L)/len(st) for L in 'ABCDEF'})
# proxy 26-year + holdout
P0 = '2001-01-02'
pn_, pds = run(sig, p, P0, NEW, True); po_, _ = run(sig, p, P0, OLD, False)
ps0 = dates.index(pds[0])
pq = px_rets('qqq_long_history.csv', dates)[ps0+1:]; psy = px_rets('spy_long_history.csv', dates)[ps0+1:]
res['proxy'] = {k: stats(v, pds) for k, v in (('new', pn_), ('old', po_), ('qqq', pq), ('spy', psy))}
cut = next(i for i, d in enumerate(pds[1:]) if d >= '2015-11-01')
res['holdout'] = {k: stats(v[:cut], pds[:cut+1]) for k, v in (('new', pn_), ('old', po_), ('qqq', pq), ('spy', psy))}
res['window'] = [ds[0], ds[-1], len(ds)-1]; res['proxy_window'] = [pds[0], pds[-1]]
for k in ('proxy', 'holdout'):
    for v in res[k].values(): v.pop('years') if k == 'holdout' else None
json.dump(res, open(OUTD + '/res.json', 'w'), indent=1)
open(OUTD + '/DATA.js', 'w').write('const DATA = ' + json.dumps(DATA, separators=(',', ':')) + ';')
open(OUTD + '/COMPARE.js', 'w').write('const COMPARE_DATA = ' + json.dumps(COMP, separators=(',', ':')) + ';')
open(OUTD + '/DMA.js', 'w').write('const DMA_DATA = ' + json.dumps(DMA, separators=(',', ':')) + ';')
for k in ('new', 'old', 'new_novixm', 'qqq', 'spmo', 'spy'):
    v = res[k]; print(f"{k:11} {v['mult']:7.2f}x {v['cagr']*100:6.1f}% vol {v['vol']*100:5.1f}% Sh {v['sharpe']:.3f} DD {v['dd']*100:6.1f}%  " + ' '.join(f"{y[2:]} {x*100:+.1f}" for y, x in sorted(v['years'].items())))
for k in ('proxy', 'holdout'):
    for n, v in res[k].items(): print(k, n, f"{v['cagr']*100:.1f}% Sh {v['sharpe']:.3f} DD {v['dd']*100:.1f}%")
print(res['window'], res['proxy_window'], res['share'])
