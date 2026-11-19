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
ci = np.cumsum(np.insert(X['IEF'], 0, 0)); sma_ief = np.full(n, np.nan); sma_ief[199:] = (ci[200:] - ci[:-200]) / 200
def TT(on):
    k, io = on; top = len(CFG['bounds'])
    if k == top: return {'SSO': 1.0}
    if k == 0:
        if CFG['fb'] == 'CASH' or not io: return {}
        return {'IEF': 1.0}
    return {'VTI': 1.0} if CFG['mid'] == 'VTI' else {'SSO': 0.5}
def run(start, mode='P', tax=False):
    global NT; NT = [0]
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
            g = X['SPY'][i] / sma[i] - 1; B = CFG['bounds']; h = CFG['h']
            lv = None if on is None else on[0]
            k = sum(1 for bi, b in enumerate(B) if g > (b if lv is None else (b - h if lv > bi else b + h)))
            gi = X['IEF'][i] / sma_ief[i] - 1; io = True if on is None else on[1]
            if CFG['fb'] == 'IEFTREND': io = (gi > 0.0) if on is None else ((gi > -0.01) if io else (gi > 0.01))
            elif CFG['fb'] == 'IEFMOM':
                if on is None or i in mes: io = X['IEF'][i] / X['IEF'][i - 126] - 1 > np.prod(1 + C[i - 125:i + 1]) - 1
            new = (k, io)
            if new != on:
                if on is None or TT(new) != TT(on): trade = True; NT[0] += 1
                on = new
        if i in mes and me.index(i) >= 6:
            j = me[me.index(i) - 6]; cr = np.prod(1 + C[j + 1:i + 1]) - 1; nr = {}
            for m, s in sorted(((X[s][i] / X[s][j] - 1, s) for s in ROT), reverse=True)[:CFG['topn']]:
                if m > cr: nr[s] = 1.0 / CFG['topn']
            if nr != rot: rot = nr; trade = True
        if trade or i == s0:
            t = {}
            if mode in ('P', 'T') and on is not None:
                for s, x in TT(on).items(): t[s] = t.get(s, 0) + x * (CFG['split'] if mode == 'P' else 1.0)
            if mode in ('P', 'R'):
                for s, x in rot.items(): t[s] = t.get(s, 0) + x * (1 - CFG['split'] if mode == 'P' else 1.0)
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
def yrs(r,ds):
    y={}
    for d,x in zip(ds,r): y.setdefault(d[:4],[]).append(x)
    return {k:(np.prod(1+np.array(a))-1)*100 for k,a in y.items()}
base=dict(bounds=[0.0],h=0.01,mid='VTI',fb='IEF',topn=2,split=0.5)
s0 = next(i for i, d in enumerate(dates) if d >= '2007-07-02'); spy=yrs(R['SPY'][s0+1:],dates[s0+1:])
def show(title,V,sub='R'):
    print(title); print(f"  variant                          | CAGR Sharpe MaxDD AvgDD | 07-15 | 16-26 | aftertax | {'rot' if sub=='R' else 'trend'}-only CAGR Sh MaxDD | beat SPY yrs | 2008  2010  2015  2018  2019  2022  2023")
    for nm,c in V:
        global CFG; CFG=dict(base,**c)
        r,ds=run('2007-07-02','P'); rt,_=run('2007-07-02','P',tax=True); rr,_=run('2007-07-02',sub); d2=np.array(ds); a=q(r); o=q(rr); y=yrs(r,ds)
        w=sum(1 for k in y if k not in('2007','2026') and y[k]>spy[k])
        print(f"  {nm:32s} | {a[0]:5.1f} {a[1]:5.2f} {a[2]:6.1f} {a[3]:5.1f} | {q(r[d2<'2016'])[0]:5.1f} | {q(r[d2>='2016'])[0]:5.1f} | {q(rt)[0]:5.1f}    | {o[0]:5.1f} {o[1]:5.2f} {o[2]:6.1f}     | {w:2d}/18 | "+' '.join(f"{y[k]:+5.1f}" for k in ('2008','2010','2015','2018','2019','2022','2023')))
show("IDEA 3: how many rotation funds",[(f'top {k}',dict(topn=k)) for k in (1,2,3,4)])
show("IDEA 4: trend / rotation split",[(f'{int(s*100)}/{int(100-s*100)}',dict(split=s)) for s in (0.3,0.4,0.5,0.6,0.7)])
show("BAND SCAN: width of the on/off band around the 200-day line (current 1%)",[(f'{b:.1f}% band',dict(h=b/100)) for b in (0,0.5,1,1.5,2,2.5,3,3.5,4,5,6)],'T')
show("COMBINATIONS",[('current',{}),('IEF 6m filter',dict(fb='IEFMOM')),('2% band',dict(h=.02)),('3% band',dict(h=.03)),
 ('2% band + IEF filter',dict(h=.02,fb='IEFMOM')),('3% band + IEF filter',dict(h=.03,fb='IEFMOM')),
 ('2.5% band + IEF filter',dict(h=.025,fb='IEFMOM')),('2.5% band + IEF filter + top 3',dict(h=.025,fb='IEFMOM',topn=3))],'T')
