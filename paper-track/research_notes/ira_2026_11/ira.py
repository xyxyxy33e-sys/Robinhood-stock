"""IRA strategy candidates (2026-11-19). PRE-REGISTERED, published rules, no tuning:
C1 trend across asset classes: SPY, EFA, IEF, VNQ, DBC, GLD, equal 1/6 each, held only if its month-end
   adjusted close is above its 10-month average of month-end closes, else that slice in T-bills. Monthly.
C2 momentum rotation: of SPY, EFA, EEM, TLT, GLD, DBC, VNQ hold the 2 with the best 6-month total return,
   50% each, only if that return beats T-bills over the same 6 months, else T-bills. Monthly.
C3 the live six-state rules on the S&P 500 (SPY core, 2x/3x S&P synthetic), full and bare.
Costs 5bp per side (C1/C2). Trade at month-end close, earn from the next session. Window 2007-01 -> latest,
split 2007-2015 / 2016-2026. Also: daily correlation with the live strategy (QQQ proxy) and 50/50 blends."""
import sys, json, datetime as dt, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/vol'); sys.path.insert(1, '/home/user/Robinhood-stock/paper-track')
import numpy as np, harness as H, untouched_test as U
from harness import MC, S
DL = '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/ira/dl/'
def yh(s):
    d = json.load(open(DL + s + '.json'))['chart']['result'][0]
    a = d['indicators']['adjclose'][0]['adjclose']
    return {dt.datetime.utcfromtimestamp(t).date().isoformat(): v for t, v in zip(d['timestamp'], a) if v}
P = H.p; PD = P['dates']; cashd = dict(zip(PD, P['cash']))
U1 = ['SPY', 'EFA', 'IEF', 'VNQ', 'DBC', 'GLD']; U2 = ['SPY', 'EFA', 'EEM', 'TLT', 'GLD', 'DBC', 'VNQ']
px = {s: yh(s) for s in set(U1 + U2)}
dates = [d for d in PD if d >= '2006-02-07' and all(d in px[s] for s in px)]
X = {s: np.array([px[s][d] for d in dates]) for s in px}
R = {s: np.r_[0, X[s][1:] / X[s][:-1] - 1] for s in px}
cash = np.array([cashd[d] for d in dates])
me = [i for i in range(len(dates) - 1) if dates[i][:7] != dates[i + 1][:7]]   # month-end indices
def run(wfun, start='2007-01-01'):
    syms = sorted(px); w = np.zeros(len(syms) + 1); w[-1] = 1.0; out = np.zeros(len(dates))
    mset = set(me); cost = 0.0005
    for i in range(1, len(dates)):
        rr = np.array([R[s][i] for s in syms] + [cash[i]])
        out[i] = (w * rr).sum()
        w = w * (1 + rr); w = w / w.sum()
        if i in mset and dates[i] >= start[:7]:
            nw = wfun(i, syms)
            out[i] -= cost * np.abs(nw - w).sum(); w = nw
    s0 = next(i for i, d in enumerate(dates) if d >= start)
    return out[s0 + 1:], dates[s0 + 1:]
def c1(i, syms):
    k = me.index(i); idx = me[max(0, k - 9):k + 1]; nw = np.zeros(len(syms) + 1)
    for s in U1:
        if X[s][i] > np.mean(X[s][idx]): nw[syms.index(s)] = 1 / 6
        else: nw[-1] += 1 / 6
    return nw
def c2(i, syms):
    k = me.index(i); j = me[k - 6]; nw = np.zeros(len(syms) + 1)
    cr = np.prod(1 + cash[j + 1:i + 1]) - 1
    mom = sorted(((X[s][i] / X[s][j] - 1, s) for s in U2), reverse=True)[:2]
    for m, s in mom:
        if m > cr: nw[syms.index(s)] += 0.5
        else: nw[-1] += 0.5
    return nw
res = {}
res['C1 trend 6 assets'] = run(c1); res['C2 momentum top-2'] = run(c2)
# C3: live rules on the S&P (from sp20 approach)
NEW = dict(H.CUR, gross_cap=S.GROSS_CAP); BARE = dict(NEW, trim='none', d_gate=False, d_ladder=False, fast=False)
vix, _ = U.vix_hist(); ps = U.panel(MC._load('spy_long_history.csv'), div=MC.SPY_DIV); sgs = U.sigs(ps); dss = ps['dates']
s1 = next(i for i, d in enumerate(dss) if d >= '2007-01-01'); e1 = len(dss) - 1
for cfg, ql, lab in ((NEW, True, 'C3 S&P live rules'), (BARE, False, 'C3b S&P bare rules')):
    rr, _, _ = U.run(sgs, ps, cfg, ql, vix, s1, e1, 0); res[lab] = (rr, dss[s1 + 1:e1 + 1])
r_main, d_main = H.run(False, d0='2007-01-01', cfg=NEW, vixm=False)[:2]
res['MAIN live strategy (QQQ proxy)'] = (r_main, d_main)
sp = R['SPY']; res['SPY buy & hold'] = (sp[next(i for i, d in enumerate(dates) if d >= '2007-01-01') + 1:], dates[next(i for i, d in enumerate(dates) if d >= '2007-01-01') + 1:])
def align(a, b):
    da = dict(zip(a[1], a[0])); db = dict(zip(b[1], b[0])); cd = sorted(set(da) & set(db))
    return np.array([da[d] for d in cd]), np.array([db[d] for d in cd]), cd
def st(r, ds):
    nav = np.cumprod(1 + r); dd = (nav / np.maximum.accumulate(nav) - 1).min(); v = r.std(ddof=1) * 252 ** .5
    yr = {}
    for d, x in zip(ds, r): yr.setdefault(d[:4], []).append(x)
    ann = {y: np.prod(1 + np.array(a)) - 1 for y, a in yr.items()}
    return f"{(nav[-1] ** (252 / len(r)) - 1) * 100:5.1f}% {r.mean() * 252 / v:5.2f} {dd * 100:6.1f}% {min(ann.values()) * 100:6.1f}%"
def split(r, ds, a, b):
    m = [(a <= d < b) for d in ds]; rr = np.array(r)[m]; return rr, [d for d, k in zip(ds, m) if k]
print(f"{'':32s} {'2007-2026: CAGR Sharpe MaxDD worstYr':38s} {'2007-15 CAGR Sh':16s} {'2016-26 CAGR Sh':16s} corr-to-MAIN")
mr = res['MAIN live strategy (QQQ proxy)']
for k, (r, ds) in res.items():
    a1 = split(r, ds, '2007', '2016'); a2 = split(r, ds, '2016', '2100')
    x, y, _ = align((r, ds), mr)
    print(f"{k:32s} {st(r, ds):38s} {st(*a1)[:13]:16s} {st(*a2)[:13]:16s} {np.corrcoef(x, y)[0, 1]:5.2f}")
print('\n50/50 blends with MAIN (rebalanced daily, household view):')
for k in ('C1 trend 6 assets', 'C2 momentum top-2', 'C3b S&P bare rules', 'SPY buy & hold'):
    x, y, cd = align(res[k], mr); print(f"  MAIN + {k:22s} {st(0.5 * x + 0.5 * y, cd)}")
print(f"  MAIN alone                     {st(*mr)}")
