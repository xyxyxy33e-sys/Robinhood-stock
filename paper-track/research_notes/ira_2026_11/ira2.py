"""IRA design vs 'buy and hold SPMO + $7,500/yr' (2026-11-19). PRE-REGISTERED, no tuning after the run:
I1 rotation: top-2 of SPY EFA EEM TLT GLD DBC VNQ by 6-month return, each must beat T-bills, monthly.
I3 trend-levered S&P: SSO (2x S&P) while SPY's close is above its 200-day average (1% hysteresis), else IEF;
   checked every close.
I4 50% I1 + 50% I3 (rebalanced daily).
I5 trend-filtered momentum: MTUM while SPY is above its 10-month average, else the better of IEF / GLD by
   6-month return if it beats T-bills, else T-bills; monthly.
Benchmarks: SPMO, SPY, MTUM buy & hold. Costs 5bp/side. Windows: Nov 2015 -> now (vs SPMO) and 2007 -> now.
Money test: $48,241 start + $7,500 on the first session of each later year, ending value."""
import sys, json, datetime as dt, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/vol'); sys.path.insert(1, '/home/user/Robinhood-stock/paper-track')
import numpy as np, harness as H
DL = '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/ira/dl/'
def yh(s):
    d = json.load(open(DL + s + '.json'))['chart']['result'][0]
    return {dt.datetime.utcfromtimestamp(t).date().isoformat(): v for t, v in zip(d['timestamp'], d['indicators']['adjclose'][0]['adjclose']) if v}
SY = ['SPY', 'EFA', 'EEM', 'TLT', 'GLD', 'DBC', 'VNQ', 'IEF', 'SSO', 'MTUM', 'SPMO']
px = {s: yh(s) for s in SY}
cashd = dict(zip(H.p['dates'], H.p['cash']))
dates = [d for d in H.p['dates'] if d >= '2006-06-22' and all(d in px[s] for s in SY[:9])]
n = len(dates); C = np.array([cashd[d] for d in dates])
def ser(s):
    x = np.array([px[s].get(d, np.nan) for d in dates]); return x
X = {s: ser(s) for s in SY}
R = {s: np.r_[0, X[s][1:] / X[s][:-1] - 1] for s in SY}
for s in SY: R[s] = np.nan_to_num(R[s])
me = set(i for i in range(n - 1) if dates[i][:7] != dates[i + 1][:7]); mel = sorted(me)
def sma(x, k): c = np.cumsum(np.insert(np.nan_to_num(x), 0, 0)); o = np.full(len(x), np.nan); o[k-1:] = (c[k:] - c[:-k]) / k; return o
spy200 = sma(X['SPY'], 200)
def engine(target, start):
    """target(i) -> dict sym->weight (rest cash) or None (keep). Trade at close i, earn from i+1."""
    w = {}; out = np.zeros(n); s0 = next(i for i, d in enumerate(dates) if d >= start)
    for i in range(s0, n):
        if i > s0:
            out[i] = sum(w[s] * R[s][i] for s in w) + (1 - sum(w.values())) * C[i]
            tot = 1 + out[i]; w = {s: w[s] * (1 + R[s][i]) / tot for s in w}
        t = target(i)
        if t is not None:
            keys = set(w) | set(t); out[i] -= 0.0005 * (sum(abs(t.get(s, 0) - w.get(s, 0)) for s in keys) + abs((1 - sum(t.values())) - (1 - sum(w.values()))))
            w = {s: v for s, v in t.items() if v > 0}
    return out[s0 + 1:], dates[s0 + 1:]
def bh(sym): return lambda i: {sym: 1.0} if i == bh.s0 else None
def i1(i):
    if i not in me: return None
    k = mel.index(i)
    if k < 6: return None
    j = mel[k - 6]; cr = np.prod(1 + C[j + 1:i + 1]) - 1; t = {}
    for m, s in sorted(((X[s][i] / X[s][j] - 1, s) for s in ['SPY', 'EFA', 'EEM', 'TLT', 'GLD', 'DBC', 'VNQ']), reverse=True)[:2]:
        if m > cr: t[s] = t.get(s, 0) + 0.5
    return t
state = {'on': None}
def i3(i):
    if np.isnan(spy200[i]): return None
    g = X['SPY'][i] / spy200[i] - 1; on = state['on']
    new = (g > 0.01) if on is None else (on and g > -0.01) or (not on and g > 0.01)
    if new != on:
        state['on'] = new; return {'SSO': 1.0} if new else {'IEF': 1.0}
    return None
def i5(i):
    if i not in me: return None
    k = mel.index(i)
    if k < 10 or np.isnan(X['MTUM'][i]): return None
    if X['SPY'][i] > np.mean([X['SPY'][m] for m in mel[k - 9:k + 1]]): return {'MTUM': 1.0}
    j = mel[k - 6]; cr = np.prod(1 + C[j + 1:i + 1]) - 1
    m, s = max((X[s][i] / X[s][j] - 1, s) for s in ('IEF', 'GLD'))
    return {s: 1.0} if m > cr else {}
def run_all(start):
    out = {}
    for lab, sym in (('SPMO buy & hold', 'SPMO'), ('SPY buy & hold', 'SPY'), ('MTUM buy & hold', 'MTUM')):
        s0 = next(i for i, d in enumerate(dates) if d >= start)
        if np.isnan(X[sym][s0]): continue
        bh.s0 = s0; out[lab] = engine(bh(sym), start)
    out['I1 rotation'] = engine(i1, start)
    state['on'] = None; out['I3 SSO/IEF 200-day'] = engine(i3, start)
    a, b = out['I1 rotation'], out['I3 SSO/IEF 200-day']; out['I4 50/50 I1+I3'] = (0.5 * a[0] + 0.5 * b[0], a[1])
    if start >= '2014-03': out['I5 trend-filtered MTUM'] = engine(i5, start)
    return out
def st(r, ds):
    nav = np.cumprod(1 + r); dd = (nav / np.maximum.accumulate(nav) - 1).min(); v = r.std(ddof=1) * 252 ** .5
    yr = {}
    for d, x in zip(ds, r): yr.setdefault(d[:4], []).append(x)
    ann = {y: np.prod(1 + np.array(a)) - 1 for y, a in yr.items()}
    return (nav[-1] ** (252 / len(r)) - 1, r.mean() * 252 / v, dd, min(ann.values()), ann)
def money(r, ds, start_amt=48241, add=7500):
    v = start_amt; yr = ds[0][:4]
    for d, x in zip(ds, r):
        if d[:4] != yr: v += add; yr = d[:4]
        v *= 1 + x
    return v
for start in ('2015-11-02', '2007-01-03'):
    res = run_all(start); print(f"\n=== from {start} to {dates[-1]} ===")
    print(f"{'':26s}{'CAGR':>7}{'Sharpe':>8}{'MaxDD':>8}{'worstYr':>9}" + (f"{'$48k + $7.5k/yr ->':>21}" if start == '2015-11-02' else ''))
    for k, (r, ds) in res.items():
        c, sh, dd, wy, ann = st(r, ds)
        print(f"{k:26s}{c*100:6.1f}%{sh:8.2f}{dd*100:7.1f}%{wy*100:8.1f}%" + (f"{money(r, ds):>21,.0f}" if start == '2015-11-02' else ''))
    if start == '2015-11-02':
        ys = sorted(st(*res['SPMO buy & hold'])[4])
        print('\nyear   ' + ''.join(f"{k[:12]:>13}" for k in res))
        for y in ys: print(y + '   ' + ''.join(f"{st(*res[k])[4].get(y, np.nan)*100:12.1f}%" for k in res))
