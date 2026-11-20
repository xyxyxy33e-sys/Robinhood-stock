"""Public taxable strategy candidate (2026-11-19). PRE-REGISTERED:
P = 50% TREND sleeve + 50% ROTATION sleeve, no ticker shared with the Robinhood strategy (SPY TQQQ QLD QQQ VIXY BOXX XLU)
or the IRA (SPMO).
 TREND: SSO (2x S&P) while SPY adj close is above its 200-day average (1% hysteresis), else IEF. Checked daily.
   FALLBACK FILTER (owner 2026-11-19): IEF only if its 6-month return at the last month-end beats T-bills, else cash.
   Set FB_FILTER = False for the original always-IEF rule.
   VIX-PANIC LEG (owner 2026-11-20): while the trend is off and the VIX latch is on (close >= 30 on, < 25 off),
   PANIC_SHARE (25%) of the trend half is 1x S&P, held as SSO at half weight; the fallback keeps the other 75%.
   Set PANIC_SHARE = 0 to switch it off.
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
FB_FILTER = True; PANIC_SHARE = 0.25
import csv as _csv
_vx = {}
for _r in list(_csv.reader(open('/home/user/Robinhood-stock/data/vixcls_full.csv')))[1:]:
    try: _vx[_r[0]] = float(_r[1])
    except ValueError: pass
_d = json.load(open(DL + 'VIX.json'))['chart']['result'][0]
for _t, _v in zip(_d['timestamp'], _d['indicators']['quote'][0]['close']):
    if _v: _vx.setdefault(dt.datetime.utcfromtimestamp(_t).date().isoformat(), _v)
PANIC = np.zeros(n, bool); _p = False
for _i, _dd in enumerate(dates):
    _v = _vx.get(_dd)
    if _v is not None: _p = (_v >= 25.0) if _p else (_v >= 30.0)
    PANIC[_i] = _p
def run(start, mode='P', tax=False):
    iefok = True; pan = False; pend = None; global EV; EV = {}
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
        trade = False; ssoev = False; rotev = False
        if not np.isnan(sma[i]):
            g = X['SPY'][i] / sma[i] - 1; new = (g > 0.01) if on is None else ((g > -0.01) if on else (g > 0.01))
            if new != on: on = new; trade = True; ssoev = True
        if i in mes and me.index(i) >= 6:
            j = me[me.index(i) - 6]; cr = np.prod(1 + C[j + 1:i + 1]) - 1; nr = {}
            for m, s in sorted(((X[s][i] / X[s][j] - 1, s) for s in ROT), reverse=True)[:2]:
                if m > cr: nr[s] = 0.5
            if MODE == 'I2':
                pend = nr
            elif nr != rot: rot = nr; trade = True; rotev = True
            ok = (X['IEF'][i] / X['IEF'][j] - 1 > cr) or not FB_FILTER
            if ok != iefok:
                iefok = ok
                if on is not None and not on: trade = True
        pn = bool(PANIC[i]) and on is not None and not on and PANIC_SHARE > 0
        if pn != pan: pan = pn; trade = True; ssoev = True
        if MODE == 'I2' and ssoev and pend is not None and pend != rot: rot = pend; rotev = True
        EV[dates[i]] = (ssoev, rotev, trade)
        if trade or i == s0:
            t = {}
            if mode in ('P', 'T') and on is not None and (on or iefok): t['SSO' if on else 'IEF'] = 0.5 if mode == 'P' else 1.0
            if mode in ('P', 'R'):
                for s, x in rot.items(): t[s] = t.get(s, 0) + x * (0.5 if mode == 'P' else 1.0)
            if pan and mode in ('P', 'T'):
                fb = 0.5 if mode == 'P' else 1.0
                if 'IEF' in t: t['IEF'] *= 1 - PANIC_SHARE
                t['SSO'] = t.get('SSO', 0) + fb * PANIC_SHARE * 0.5
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
def line(nm,r,ds,extra=''):
    d2=np.array(ds); a=q(r); y=yrs(r,ds)
    print(f"  {nm:52s} | {a[0]:5.1f} {a[1]:5.2f} {a[2]:6.1f} {a[3]:5.1f} | {q(r[d2<'2016'])[0]:5.1f} | {q(r[d2>='2016'])[0]:5.1f} | {extra:22s} | "+' '.join(f"{y[k]:+5.1f}" for k in ('2008','2013','2015','2018','2020','2022')))
print("  variant                                              | CAGR Sharpe MaxDD AvgDD | 07-15 | 16-26 | notes                  | 2008  2013  2015  2018  2020  2022")
MODE='I0'; r0,ds=run('2007-07-02','P'); rt0,_=run('2007-07-02','P',tax=True); ev0=dict(EV); line('current: reset to 50/50 on every signal trade',r0,ds,f'after tax {q(rt0)[0]:.1f}')
rT,_=run('2007-07-02','T'); evT=dict(EV); rR,_=run('2007-07-02','R'); evR=dict(EV)
def combo(reset):      # two sleeves run separately; money moved between them only on reset days (5bp on the amount moved)
    a=b=0.5; out=[]; mx=0; nres=0
    for k,d in enumerate(ds):
        a*=1+rT[k]; b*=1+rR[k]; tot=a+b
        if reset(d):
            mv=abs(a-tot/2); tot-=0.0005*mv*2; a=b=tot/2; nres+=1
        mx=max(mx,a/(a+b)); out.append(a+b)
    nav=np.array(out); return np.r_[nav[0]-1,nav[1:]/nav[:-1]-1], mx, nres
for nm,f in (('check: sleeves separate, reset on every signal trade',lambda d: evT.get(d,(0,0,0))[2] or evR.get(d,(0,0,0))[2]),
             ('reset to 50/50 ONLY when the trend half trades',lambda d: evT.get(d,(0,0,0))[0]),
             ('reset only when SSO is bought (trend turns on)',None),
             ('reset once a year (first session)',lambda d: False),
             ('never reset',lambda d: False)):
    if 'bought' in nm:
        prev={}; days=set(); last=None
        # trend-on days: SSO event where the T sleeve is on afterwards -> use sign of next 2x-like exposure: approximate with EV and on-state log
        f=lambda d: d in ONDAYS
    if 'year' in nm:
        firsts=set(); seen=set()
        for d in ds:
            if d[:4] not in seen: seen.add(d[:4]); firsts.add(d)
        f=lambda d: d in firsts
    if 'bought' in nm:
        # rebuild on-state days from the SPY rule
        ONDAYS=set(); on=None
        for i in range(n):
            if np.isnan(sma[i]): continue
            g=X['SPY'][i]/sma[i]-1; new=(g>0.01) if on is None else ((g>-0.01) if on else (g>0.01))
            if on is not None and new and not on: ONDAYS.add(dates[i])
            on=new
    r,mx,nres=combo(f); line(nm,r,ds,f'{nres/(len(ds)/252):.1f} resets/yr, max trend share {mx*100:.0f}%')
MODE='I2'; r2,_=run('2007-07-02','P'); rt2,_=run('2007-07-02','P',tax=True); nrot=sum(1 for v in EV.values() if v[1])/(len(r2)/252)
line('rotation picks change ONLY on days the trend half trades',r2,ds,f'after tax {q(rt2)[0]:.1f}, {nrot:.1f} rot chg/yr')
