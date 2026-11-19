import sys, warnings, csv, os; warnings.filterwarnings('ignore')
sys.path.insert(0, '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/vol'); sys.path.insert(1, '/home/user/Robinhood-stock/paper-track')
import numpy as np
import harness as H
import untouched_test as U
from harness import MC, S
_n = len(H.sr['vol'][0]); _N0 = len(H.pr['dates'])
for _k, _v in list(H.pr.items()):
    if hasattr(_v, '__len__') and len(_v) == _N0 and _N0 != _n: H.pr[_k] = _v[:_n]
H.RD = H.pr['dates']
CAP = S.GROSS_CAP
FULL = dict(H.CUR, gross_cap=CAP, name='full (current)')
A_ROW = (0.40, 0.60, 0, 0, 0)
V = [  # (cfg, qlegs)
    (FULL, True),
    (dict(FULL, name='- trim', trim='none'), True),
    (dict(FULL, name='- D gate', d_gate=False), True),
    (dict(FULL, name='- D ladder (D = 100% QLD)', d_ladder=False), True),
    (dict(FULL, name='- fast re-entry', fast=False), True),
    (dict(FULL, name='- QQQ cash legs'), False),
    (dict(FULL, name='- D zone buffer', d_buffer=0.0), True),
    (dict(FULL, name='BARE (6 rows + vol + cap)', trim='none', d_gate=False, d_ladder=False, fast=False), False),
    (dict(FULL, name='SIMPLE: >200d 40/60, else cash', trim='none', d_gate=False, d_ladder=False, fast=False,
          rows=dict(FULL['rows'], B=A_ROW, C=(0, 0, 0, 0, 1), D=A_ROW)), False),
    (dict(FULL, name='SIMPLE unlevered: >200d core', trim='none', d_gate=False, d_ladder=False, fast=False,
          a_base=(1.0, 0.0), rows=dict(FULL['rows'], B=(1, 0, 0, 0, 0), C=(0, 0, 0, 0, 1), D=(1, 0, 0, 0, 0))), False),
]
def st(r):
    nav = np.cumprod(1+r); dd = (nav/np.maximum.accumulate(nav)-1).min(); v = r.std(ddof=1)*252**.5
    return f"{(nav[-1]**(252/len(r))-1)*100:5.1f}% {r.mean()*252/v:5.2f} {dd*100:6.1f}%"
print('IN-SAMPLE (CAGR Sharpe MaxDD; vol sleeve off everywhere)')
print(f"{'variant':34s} | real 2015-26        | proxy 2001-26       | holdout 2001-Oct15")
for cfg, ql in V:
    out = [st(H.run(real, d1=d1, cfg=cfg, vixm=False, qlegs=ql)[0]) for real, d1 in ((True, '2099'), (False, '2099'), (False, '2015-10-30'))]
    print(f"{cfg['name']:34s} | " + ' | '.join(out))
# untouched sets (excess-of-cash Sharpe, as the review)
vix, _ = U.vix_hist()
ndx = MC._load('NDX_index_daily.csv'); sets = [('NDX 87-00', U.panel(ndx, div=MC.QQQ_DIV), vix, U.END_A)]
for sym in ('^N225', '^GDAXI', '^FTSE'):
    try: sets.append((sym, U.panel(U.yahoo(sym)), None, '2099'))
    except Exception as ex: print(sym, 'unavailable', ex)
print('\nUNTOUCHED SETS: excess Sharpe (CAGR, MaxDD) at lag 0')
hdr = f"{'variant':34s} | " + ' | '.join(f"{n:22s}" for n, *_ in sets)
print(hdr)
bh = []
for n, p, vx, end in sets:
    ds = p['dates']; s0 = MC.WARMUP; e = max(i for i, d in enumerate(ds) if d <= end)
    x = U.stats(p['bh_index'][s0+1:e+1], p['cash'][s0+1:e+1], ds[s0+1:e+1]); bh.append(f"{x['ex']:6.3f} ({x['c']*100:4.1f}% {x['m']*100:5.1f}%)")
print(f"{'buy & hold index':34s} | " + ' | '.join(f"{b:22s}" for b in bh))
SG = {n: U.sigs(p) for n, p, *_ in sets}
for cfg, ql in V:
    row = []
    for n, p, vx, end in sets:
        ds = p['dates']; s0 = MC.WARMUP; e = max(i for i, d in enumerate(ds) if d <= end)
        r, tpy, on = U.run(SG[n], p, cfg, ql and vx is not None, vx, s0, e, 0)
        x = U.stats(r, p['cash'][s0+1:e+1], ds[s0+1:e+1]); row.append(f"{x['ex']:6.3f} ({x['c']*100:4.1f}% {x['m']*100:5.1f}%)")
    print(f"{cfg['name']:34s} | " + ' | '.join(f"{c:22s}" for c in row))
