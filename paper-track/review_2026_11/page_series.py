"""Series for the published strategy pages (11 Nov 2026): the current design (2.0x gross cap, VIXY 35%
sleeve on VIXY's own closes) against the design before those changes (uncapped, VIXM 75%), each with
and without the sleeve, plus the 2001-2026 proxy and 2001-Oct 2015 holdout. Writes page_series.json.
VIXY closes 11-05..11-10 (Yahoo; volume left blank) were appended to vixy_daily.csv on 11 Nov."""
import csv, os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness as H
from harness import MC, S
OUT = HERE
vy = {r['d']: float(r['c']) for r in csv.DictReader(open(os.path.join(HERE, '..', 'research_notes', 'vixm_followups_2026_11', 'vixy_daily.csv')))}
VIXY_R = MC._rets(vy, H.RD); VIXY_R[0] = 0.0
NEW = dict(H.CUR, gross_cap=S.GROSS_CAP)
def real(kind):
    if kind == 'new': return H.run(True, cfg=NEW, vixm_share=0.35, vixm_ret=VIXY_R)
    if kind == 'old': return H.run(True, vixm_share=0.75)
    if kind == 'new_nosleeve': return H.run(True, cfg=NEW, vixm=False)
    if kind == 'old_nosleeve': return H.run(True, vixm=False)
def prox(kind, d1='2099'):
    return H.run(False, d1=d1, cfg=NEW if kind == 'new' else H.CUR)
R = {k: real(k) for k in ('new', 'old', 'new_nosleeve', 'old_nosleeve')}
ds = R['new'][1]; assert ds == R['old'][1]
print('real window', ds[0], ds[-1], len(ds))
def st(r):
    nav = np.cumprod(1 + r); dd = nav / np.maximum.accumulate(np.concatenate([[1.0], nav]))[1:] - 1
    v = r.std(ddof=1) * 252 ** .5
    return dict(mult=float(nav[-1]), c=float(nav[-1] ** (252 / len(r)) - 1), v=float(v), sh=float(r.mean() * 252 / v), m=float(dd.min()))
def years(r, dd):
    y = {}
    for d, x in zip(dd, r): y.setdefault(d[:4], []).append(x)
    return {k: float(np.prod(1 + np.array(v)) - 1) for k, v in y.items()}
res = {k: dict(st(v[0]), years=years(v[0], v[1])) for k, v in R.items()}
for k in ('new', 'old'):
    rp, dp, _ = prox(k); rh, dh, _ = prox(k, '2015-10-30')
    res['proxy_' + k] = st(rp); res['hold_' + k] = st(rh)
W, L, _ = H.weights(H.sr, H.RD, True, cfg=NEW, vixm_share=0.35, vixm_ret=VIXY_R)
s0 = H.RD.index(ds[0]) - 1
res['share'] = dict(vixy=float((W[s0:, 4] > 0).mean()), deep=float((W[s0:, 5] > 0).mean()), panic=float((W[s0:, 6] > 0).mean()))
LEV = np.array([1, 3, 2, 1]); lev = (W[s0:, :4] * LEV).sum(1); res['capbind'] = float((lev > 1.999).mean())
for k, v in res.items():
    if isinstance(v, dict) and 'c' in v: print(k, f"{v.get('mult',0):.2f}x {v['c']*100:.1f}% vol {v['v']*100:.1f}% Sh {v['sh']:.3f} DD {v['m']*100:.1f}%")
print('years new', {k: round(x*100,1) for k,x in res['new']['years'].items()})
print('years old', {k: round(x*100,1) for k,x in res['old']['years'].items()})
print(res['share'], 'cap binds', res['capbind'])
nav = {k: np.concatenate([[1.0], np.cumprod(1 + v[0])]) for k, v in R.items()}
dates = [H.RD[s0]] + ds
json.dump(dict(res=res, dates=dates, nav={k: v.tolist() for k, v in nav.items()}), open(OUT + '/page_series.json', 'w'))
