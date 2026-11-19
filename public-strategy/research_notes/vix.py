"""Public taxable strategy candidate (2026-11-19). PRE-REGISTERED:
P = 50% TREND sleeve + 50% ROTATION sleeve, no ticker shared with the Robinhood strategy (SPY TQQQ QLD QQQ VIXY BOXX XLU)
or the IRA (SPMO).
 TREND: SSO (2x S&P) while SPY adj close is above its 200-day average (1% hysteresis), else IEF. Checked daily.
   FALLBACK FILTER (owner 2026-11-19): IEF only if its 6-month return at the last month-end beats T-bills, else cash.
   Set FB_FILTER = False for the original always-IEF rule.
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
FB_FILTER = True
def run(start, mode='P', tax=False):
    iefok = True; ovp = (False, False); global DAYS; DAYS = [0, 0, 0]
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
        if i in mes and me.index(i) >= 6:
            j = me[me.index(i) - 6]; cr = np.prod(1 + C[j + 1:i + 1]) - 1; nr = {}
            for m, s in sorted(((X[s][i] / X[s][j] - 1, s) for s in ROT), reverse=True)[:2]:
                if m > cr: nr[s] = 0.5
            if nr != rot: rot = nr; trade = True
            ok = (X['IEF'][i] / X['IEF'][j] - 1 > cr) or not FB_FILTER
            if ok != iefok:
                iefok = ok
                if on is not None and not on: trade = True
        ov = (bool(ALLOW[i]) and on is not None and not on and OV['share'] > 0, bool(PANIC[i]) and on is not None and not on and OV['pshare'] > 0)
        if i >= s0: DAYS[0] += ov[0]; DAYS[1] += ov[1]; DAYS[2] += 1
        if ov != ovp: ovp = ov; trade = True
        if trade or i == s0:
            t = {}
            if mode in ('P', 'T') and on is not None and (on or iefok): t['SSO' if on else 'IEF'] = 0.5 if mode == 'P' else 1.0
            if mode in ('P', 'R'):
                for s, x in rot.items(): t[s] = t.get(s, 0) + x * (0.5 if mode == 'P' else 1.0)
            if mode in ('P', 'T') and (ov[0] or ov[1]):
                fb = 0.5 if mode == 'P' else 1.0; ief = t.get('IEF', 0.0); k = 0.0
                if ov[0]: t[OV['fund']] = fb * OV['share']; k += OV['share']
                if ov[1]: t['SSO'] = t.get('SSO', 0) + fb * OV['pshare'] * 0.5; k += OV['pshare']
                if ief > 0: t['IEF'] = ief * (1 - k)
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

vix, v3 = {}, {}
for nm, tgt in (('VIX', vix), ('VIX3M', v3)):
    d = json.load(open(DL + nm + '.json'))['chart']['result'][0]
    for t_, v in zip(d['timestamp'], d['indicators']['quote'][0]['close']):
        if v: tgt[dt.datetime.utcfromtimestamp(t_).date().isoformat()] = v
for s in ('VIXY', 'VIXM'):
    p = yh(s); a = np.array([p.get(d, np.nan) for d in dates]); r = np.r_[0, a[1:] / a[:-1] - 1]; R[s] = np.nan_to_num(r); X[s] = a
rv = {}
for i in range(30, n): rv[dates[i]] = float(np.std(np.log(X['SPY'][i-29:i+1] / X['SPY'][i-30:i]), ddof=1) * 252 ** .5)
def flags(minvol):
    S.VIXM_MIN_VOL = minvol; ser = S.vixm_series(dates, vix, v3, rv)
    return np.array([bool(ser.get(d, {}).get('allowed')) for d in dates])
pan = S.vix_panic_series(dates, vix); PANIC = np.array([bool(pan.get(d)) for d in dates])
def q(r):
    nav=np.cumprod(1+r); v=r.std(ddof=1)*252**.5; u=nav/np.maximum.accumulate(nav)-1
    return (nav[-1]**(252/len(r))-1)*100, r.mean()*252/v, u.min()*100, u.mean()*100
def yrs(r,ds):
    y={}
    for d,x in zip(ds,r): y.setdefault(d[:4],[]).append(x)
    return {k:(np.prod(1+np.array(a))-1)*100 for k,a in y.items()}
def show(title, V, start, ycols, split):
    print(title); print(f"  variant                              | CAGR Sharpe MaxDD AvgDD | first half | second half | aftertax | days on | "+'  '.join(ycols))
    for nm, ov, mv in V:
        global OV, ALLOW; OV = ov; ALLOW = flags(mv)
        r, ds = run(start, 'P'); dy = DAYS[:]; rt, _ = run(start, 'P', tax=True); d2 = np.array(ds); a = q(r); y = yrs(r, ds)
        print(f"  {nm:36s} | {a[0]:5.1f} {a[1]:5.2f} {a[2]:6.1f} {a[3]:5.1f} | {q(r[d2<split])[0]:5.1f} {q(r[d2<split])[1]:4.2f} | {q(r[d2>=split])[0]:5.1f} {q(r[d2>=split])[1]:4.2f}  | {q(rt)[0]:5.1f}    | {max(dy[0],dy[1])/dy[2]*100:4.1f}%  | "+' '.join(f"{y[k]:+5.1f}" for k in ycols))
N=dict(fund='VIXY',share=0,pshare=0)
show("A. VIX SLEEVE while the trend half is off (live latch: VIX<18 entry, exit VIX>VIX3M, S&P 30d vol >= threshold, 25% fade). 2011-02 to 2026-11",[
 ('no sleeve (current)',N,0.20),
 ('VIXY 35% of fallback, vol>=20%',dict(N,share=.35),0.20),('VIXY 35%, vol>=15%',dict(N,share=.35),0.15),('VIXY 35%, vol>=10%',dict(N,share=.35),0.10),
 ('VIXY 20%, vol>=15%',dict(N,share=.20),0.15),('VIXY 50%, vol>=15%',dict(N,share=.50),0.15),
 ('VIXM 75%, vol>=20%',dict(N,fund='VIXM',share=.75),0.20),('VIXM 75%, vol>=15%',dict(N,fund='VIXM',share=.75),0.15),('VIXM 75%, vol>=10%',dict(N,fund='VIXM',share=.75),0.10)],
 '2011-02-01',['2011','2015','2018','2020','2022','2025'],'2019')
show("B. VIX-PANIC leg while the trend half is off (VIX closes >= 30 on, < 25 off): that share of the fallback goes to 1x S&P. 2007-07 to 2026-11",[
 ('no panic leg (current)',N,0.20),('25% of fallback',dict(N,pshare=.25),0.20),('50% of fallback',dict(N,pshare=.50),0.20),('100% of fallback',dict(N,pshare=1.0),0.20)],
 '2007-07-02',['2008','2009','2011','2015','2020','2022'],'2016')
