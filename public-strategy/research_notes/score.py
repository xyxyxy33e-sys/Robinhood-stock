"""Public taxable strategy candidate (2026-11-19). PRE-REGISTERED:
P = 50% TREND sleeve + 50% ROTATION sleeve, no ticker shared with the Robinhood strategy (SPY TQQQ QLD QQQ VIXY BOXX XLU)
or the IRA (SPMO).
 TREND: SSO (2x S&P) while SPY adj close is above its 200-day average (1% hysteresis), else IEF. Checked daily.
 ROTATION: top 2 of VTI EFA EEM TLT GLD DBC VNQ by 6-month total return, 25% each, each must beat T-bills else that
   slot in T-bills. Last session of each month.
 Sleeves are reset to 50/50 only when a signal trades (no calendar rebalance). 5bp/side.
After-tax: average-cost lots per ticker; a sale realizes gain pro rata; short-term (38.8%) unless the position was
opened more than 365 days earlier (18.8%); T-bill interest ordinary; tax paid at each year end; losses carried."""
import sys, json, datetime as dt, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/vol'); sys.path.insert(1, '/home/user/Robinhood-stock/paper-track')
import numpy as np, harness as H
from harness import S
DL = '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/ira/dl/'
def yh(s):
    d = json.load(open(DL + s + '.json'))['chart']['result'][0]
    return {dt.datetime.utcfromtimestamp(t).date().isoformat(): v for t, v in zip(d['timestamp'], d['indicators']['adjclose'][0]['adjclose']) if v}
ROT = ['VTI', 'EFA', 'EEM', 'TLT', 'GLD', 'DBC', 'VNQ']; SY = ROT + ['SPY', 'SSO', 'IEF']
px = {s: yh(s) for s in SY}; cashd = dict(zip(H.p['dates'], H.p['cash']))
dates = [d for d in H.p['dates'] if d >= '2006-06-22' and all(d in px[s] for s in SY)]; n = len(dates)
X = {s: np.array([px[s][d] for d in dates]) for s in SY}; R = {s: np.r_[0, X[s][1:] / X[s][:-1] - 1] for s in SY}
C = np.array([cashd[d] for d in dates]); me = [i for i in range(n - 1) if dates[i][:7] != dates[i + 1][:7]]; mes = set(me)
c = np.cumsum(np.insert(X['SPY'], 0, 0)); sma = np.full(n, np.nan); sma[199:] = (c[200:] - c[:-200]) / 200
def run(start, mode='P', tax=False):
    s0 = next(i for i, d in enumerate(dates) if d >= start)
    w = {}; on = None; rot = {}; V = 1.0; out = []; basis = {}; opened = {}; gst = glt = ordi = 0.0; cf = 0.0; yr = dates[s0][:4]
    for i in range(s0, n):
        if i > s0:
            r = sum(w[s] * R[s][i] for s in w) + (1 - sum(w.values())) * C[i]
            ordi += V * (1 - sum(w.values())) * C[i]
            V0 = V; V *= 1 + r; w = {s: w[s] * (1 + R[s][i]) / (1 + r) for s in w}
            if tax and dates[i][:4] != yr:
                nst = gst + cf; t = max(nst, 0) * 0.388 + max(glt + min(nst, 0), 0) * 0.188 + max(ordi, 0) * 0.388
                cf = min(nst + glt, 0) if nst + glt < 0 else 0.0
                for s in list(basis): basis[s] *= (1 - t / V) if V > 0 else 1
                V -= t; gst = glt = ordi = 0.0; yr = dates[i][:4]
            out.append(V)
        trade = False
        if not np.isnan(sma[i]):
            g = X['SPY'][i] / sma[i] - 1; new = (g > 0.01) if on is None else ((g > -0.01) if on else (g > 0.01))
            if new != on: on = new; trade = True
        if i in mes and me.index(i) >= 12:
            k = me.index(i); nr = {}
            def sc(s):   # average of (excess return over T-bills) across lookbacks, each scaled by wt
                tot = 0.0
                for L, wt in LB:
                    j = me[k - L]; tot += wt * ((X[s][i] / X[s][j] - 1) - (np.prod(1 + C[j + 1:i + 1]) - 1))
                return tot
            if RANK:   # weighted rank score: per lookback, best fund gets 7 points ... worst 1; cash test on the 6-month return
                pts = {s: 0.0 for s in ROT}
                for L, wt in LB:
                    j = me[k - L]
                    for p, (m, s) in enumerate(sorted((X[s][i] / X[s][j] - 1, s) for s in ROT)): pts[s] += wt * (p + 1)
                j6 = me[k - 6]; c6 = np.prod(1 + C[j6 + 1:i + 1]) - 1
                for m, s in sorted(((pts[s], s) for s in ROT), reverse=True)[:2]:
                    if X[s][i] / X[s][j6] - 1 > c6: nr[s] = 0.5
            else:
                for m, s in sorted(((sc(s), s) for s in ROT), reverse=True)[:2]:
                    if m > 0: nr[s] = 0.5
            if nr != rot: rot = nr; trade = True
        if trade or i == s0:
            t = {}
            if mode in ('P', 'T') and on is not None: t['SSO' if on else 'IEF'] = 0.5 if mode == 'P' else 1.0
            if mode in ('P', 'R'):
                for s, x in rot.items(): t[s] = t.get(s, 0) + x * (0.5 if mode == 'P' else 1.0)
            for s in set(w) | set(t):
                a, b = w.get(s, 0) * V, t.get(s, 0) * V
                if b < a - 1e-12:      # sell
                    frac = (a - b) / a; gain = (a - basis.get(s, a)) * frac
                    if (np.datetime64(dates[i]) - np.datetime64(opened.get(s, dates[i]))).astype(int) > 365: glt += gain
                    else: gst += gain
                    basis[s] = basis.get(s, a) * (1 - frac)
                elif b > a + 1e-12:
                    if a <= 1e-12: opened[s] = dates[i]
                    basis[s] = basis.get(s, 0) + (b - a)
                V -= 0.0005 * abs(b - a)
            w = {s: v for s, v in t.items() if v > 0}
    if tax:
        un = sum(w[s] * V - basis.get(s, 0) for s in w); V -= max(un + min(gst + cf, 0), 0) * 0.188 + max(gst + cf, 0) * 0.388; out[-1] = V
    nav = np.array(out); r = np.r_[nav[0] - 1, nav[1:] / nav[:-1] - 1]
    return r, dates[s0 + 1:]
def st(r, ds):
    nav = np.cumprod(1 + r); dd = (nav / np.maximum.accumulate(nav) - 1).min(); v = r.std(ddof=1) * 252 ** .5
    yr = {}
    for d, x in zip(ds, r): yr.setdefault(d[:4], []).append(x)
    ann = {y: np.prod(1 + np.array(a)) - 1 for y, a in yr.items()}
    return f"{(nav[-1] ** (252 / len(r)) - 1) * 100:5.1f}% {r.mean() * 252 / v:5.2f} {dd * 100:6.1f}% worst yr {min(ann.values()) * 100:6.1f}%", ann

def q(r):
    nav=np.cumprod(1+r); v=r.std(ddof=1)*252**.5; u=nav/np.maximum.accumulate(nav)-1
    return (nav[-1]**(252/len(r))-1)*100, r.mean()*252/v, u.min()*100, u.mean()*100
W=[('6m only (current)',[(6,1)]),('3/6 = 30/70',[(3,.3),(6,.7)]),('3/6/12 = 25/50/25',[(3,.25),(6,.5),(12,.25)]),
   ('3/6/9 = 25/50/25',[(3,.25),(6,.5),(9,.25)]),('1/3/6/12 = 10/20/50/20',[(1,.1),(3,.2),(6,.5),(12,.2)]),
   ('1/3/6/12 = 15/25/40/20',[(1,.15),(3,.25),(6,.4),(12,.2)]),('1/3/6/9/12 = 10/20/40/20/10',[(1,.1),(3,.2),(6,.4),(9,.2),(12,.1)]),
   ('3/6/12 = 20/60/20',[(3,.2),(6,.6),(12,.2)])]
for RANK,lab in ((False,'score = weighted return over T-bills'),(True,'score = weighted rank (1-7 points per lookback)')):
    print(lab); print("  weights                      | CAGR Sharpe MaxDD AvgDD | 07-15 | 16-26 | aftertax | rot-only CAGR Sh MaxDD")
    for nm,LB in W:
        r,ds=run('2007-07-02','P'); rt,_=run('2007-07-02','P',tax=True); rr,_=run('2007-07-02','R'); ds=np.array(ds); a=q(r); o=q(rr)
        print(f"  {nm:28s} | {a[0]:5.1f} {a[1]:5.2f} {a[2]:6.1f} {a[3]:5.1f} | {q(r[ds<'2016'])[0]:5.1f} | {q(r[ds>='2016'])[0]:5.1f} | {q(rt)[0]:5.1f}    | {o[0]:5.1f} {o[1]:5.2f} {o[2]:6.1f}")
