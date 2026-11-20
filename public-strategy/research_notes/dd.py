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
    iefok = True; pan = False; vsp = 1.0; ent = {}; stopped = set(); global LOG; LOG = []
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
            stopped = set(); ent = {s: X[s][i] for s in nr}
            if nr != rot: rot = nr; trade = True
            ok = (X['IEF'][i] / X['IEF'][j] - 1 > cr) or not FB_FILTER
            if ok != iefok:
                iefok = ok
                if on is not None and not on: trade = True
        if K.get('stop') and i not in mes:
            for s in list(rot):
                if X[s][i] < ent.get(s, 0) * (1 - K['stop']): stopped.add(s); rot = {a: b for a, b in rot.items() if a != s}; trade = True
        vs = VSQ[i] if (on and K.get('vt')) else 1.0
        if vs != vsp: vsp = vs; trade = True
        pn = bool(PANIC[i]) and on is not None and not on and PANIC_SHARE > 0
        if pn != pan: pan = pn; trade = True
        if trade or i == s0:
            t = {}
            if mode in ('P', 'T') and on is not None and (on or iefok): t['SSO' if on else 'IEF'] = 0.5 if mode == 'P' else 1.0
            if mode in ('P', 'R'):
                for s, x in rot.items(): t[s] = t.get(s, 0) + x * (0.5 if mode == 'P' else 1.0)
            if pan and mode in ('P', 'T'):
                fb = 0.5 if mode == 'P' else 1.0
                if 'IEF' in t: t['IEF'] *= 1 - PANIC_SHARE
                t['SSO'] = t.get('SSO', 0) + fb * PANIC_SHARE * 0.5
            if on and mode in ('P', 'T') and 'SSO' in t: t['SSO'] *= vsp * K.get('lev', 1.0)
            if mode == 'P' and K.get('split'):
                sp_ = K['split']; tr_ = {s: x for s, x in t.items() if s in ('SSO', 'IEF')}
                t = {s: x * ((sp_ / 0.5) if s in tr_ else ((1 - sp_) / 0.5)) for s, x in t.items()}
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
        LOG.append((dates[i], dict(w), bool(on)))
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

lr = np.log(1 + R['SPY']); vol = np.full(n, np.nan)
for i in range(31, n): vol[i] = max(lr[i-9:i+1].std(ddof=1), lr[i-29:i+1].std(ddof=1)) * 252 ** .5
def setvt(T):
    global VSQ; sc = np.minimum(1.0, T / (2 * np.where(vol > 0, vol, np.nan))); VSQ = np.nan_to_num(np.round(sc * 4) / 4, nan=1.0); VSQ[VSQ < 0.25] = 0.25
setvt(0.30)
def q(r, ds):
    nav=np.cumprod(1+r); v=r.std(ddof=1)*252**.5; u=nav/np.maximum.accumulate(nav)-1
    mo={}
    for d,x in zip(ds,r): mo.setdefault(d[:7],[]).append(x)
    wm=min(np.prod(1+np.array(a))-1 for a in mo.values())
    return (nav[-1]**(252/len(r))-1)*100, r.mean()*252/v, u.min()*100, u.mean()*100, np.mean(u<=-.15)*100, r.min()*100, wm*100
def yrs(r,ds):
    y={}
    for d,x in zip(ds,r): y.setdefault(d[:4],[]).append(x)
    return {k:(np.prod(1+np.array(a))-1)*100 for k,a in y.items()}
K={}; r0,ds=run('2007-07-02','P'); log0=LOG[:]
nav=np.cumprod(1+r0); pk=np.maximum.accumulate(nav); u=nav/pk-1
print("A. ANATOMY: the deepest drawdowns of the current strategy")
eps=[]; i=0
while i<len(u):
    if u[i]<0:
        j=i
        while j<len(u) and u[j]<0: j+=1
        k=i+int(np.argmin(u[i:j])); eps.append((u[k],i-1,k,j)); i=j
    else: i+=1
lw={d:(w,on) for d,w,on in log0}
for depth,a,k,j in sorted(eps)[:7]:
    a=max(a,0); tc=rc=0.0
    for x in range(a+1,k+1):
        w,on=lw.get(ds[x-1],({},False)); ii=dates.index(ds[x])
        for s,wt in w.items():
            c=wt*R[s][ii]
            if s in('SSO','IEF'): tc+=c
            else: rc+=c
    w,on=lw.get(ds[a],({},False))
    print(f"  {depth*100:6.1f}%  peak {ds[a]} trough {ds[k]} ({k-a} sessions) recovered {ds[j] if j<len(ds) else 'not yet'} | trend half {tc*100:+5.1f} pts, rotation half {rc*100:+5.1f} pts | held at peak: "+', '.join(f"{s} {x*100:.0f}%" for s,x in sorted(w.items(),key=lambda z:-z[1])))
def brake(r, on_, off_):
    out=np.zeros(len(r)); k=1.0; nv=pkv=1.0; sh=spk=1.0; cd=dict(zip(dates,C))
    for i,x in enumerate(r):
        c=cd[ds[i]]; out[i]=k*x+(1-k)*c; nv*=1+out[i]; pkv=max(pkv,nv); sh*=1+x; spk=max(spk,sh)
        if k==1.0 and nv/pkv-1<=-on_: k=0.5; sh=spk=1.0
        elif k<1.0 and sh/spk-1>-off_ and sh>=spk*(1-off_) and sh/1.0>1.0+on_*0.5: k=1.0; pkv=nv
    return out
print("\nB. FIXES on the Public strategy, Jul 2007 - Nov 2026")
print("  variant                               | CAGR Sharpe MaxDD AvgDD | days<=-15% | worst day | worst month | aftertax | 2008  2011  2015  2018  2020  2022")
def line(nm,r,rt=None):
    a=q(r,ds); y=yrs(r,ds)
    print(f"  {nm:37s} | {a[0]:5.1f} {a[1]:5.2f} {a[2]:6.1f} {a[3]:5.1f} | {a[4]:5.1f}%     | {a[5]:6.1f}%   | {a[6]:6.1f}%     | {'  n/a' if rt is None else f'{q(rt,ds)[0]:5.1f}'}    | "+' '.join(f"{y[k]:+5.1f}" for k in ('2008','2011','2015','2018','2020','2022')))
line('current',r0,run('2007-07-02','P',tax=True)[0])
for nm,k,T in (('SSO vol target 40% (2x fund vol)',dict(vt=1),.40),('SSO vol target 30%',dict(vt=1),.30),('SSO vol target 25%',dict(vt=1),.25),
               ('1.5x instead of 2x',dict(lev=.75),.3),('1x instead of 2x',dict(lev=.5),.3),
               ('split 40 trend / 60 rotation',dict(split=.4),.3),('split 30 / 70',dict(split=.3),.3),
               ('rotation stop: fund -8% from pick',dict(stop=.08),.3),('rotation stop: fund -12% from pick',dict(stop=.12),.3),
               ('vol target 30% + split 40/60',dict(vt=1,split=.4),.30)):
    K=k; setvt(T); r,_=run('2007-07-02','P'); rt,_=run('2007-07-02','P',tax=True); line(nm,r,rt)
K={}
for on_,off_ in ((.10,.05),(.12,.06),(.15,.08)):
    line(f'account brake: half size at -{on_*100:.0f}%',brake(r0,on_,off_))
