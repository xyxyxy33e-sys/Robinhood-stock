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
    iefok = True; pan = False
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
main = H.run(False, d0='2007-07-02', cfg=dict(H.CUR, gross_cap=S.GROSS_CAP), vixm=False)
s0 = next(i for i, d in enumerate(dates) if d >= '2007-07-02')
for a, b, lab in (('2007-07-02', '2100', '2007-2026'), ('2007-07-02', '2016', '2007-2015'), ('2016', '2100', '2016-2026')):
    print(f"== {lab} ==")
    for mode, nm in (('P', 'P combined 50/50'), ('T', 'trend sleeve alone'), ('R', 'rotation sleeve alone')):
        r, ds = run('2007-07-02', mode); m = [(a <= d < b) for d in ds]
        print(f"  {nm:24s} {st(r[m], [d for d, k in zip(ds, m) if k])[0]}")
    m = [(a <= d < b) for d in dates[s0 + 1:]]; print(f"  {'SPY buy & hold':24s} {st(R['SPY'][s0 + 1:][m], [d for d, k in zip(dates[s0+1:], m) if k])[0]}")
r, ds = run('2007-07-02', 'P'); rt, _ = run('2007-07-02', 'P', tax=True)
print('after federal tax, combined:', st(rt, ds)[0])
# buy & hold SPY after tax: dividends 1.9% taxed 18.8% yearly, LT at end
nav = np.cumprod(1 + R['SPY'][s0 + 1:] - 0.019 * 0.188 / 252); fin = nav[-1] - (nav[-1] - 1) * 0.188
print(f"after federal tax, SPY buy & hold: {(fin ** (252 / len(nav)) - 1) * 100:.1f}%")
dm = dict(zip(main[1], main[0])); cd = [d for d in ds if d in dm]; dr = dict(zip(ds, r))
print('corr of P to the Robinhood strategy (daily):', round(float(np.corrcoef([dr[d] for d in cd], [dm[d] for d in cd])[0, 1]), 2))
ann = st(r, ds)[1]; sp = st(R['SPY'][s0 + 1:], dates[s0 + 1:])[1]
print('years: ' + '  '.join(f"{y} {ann[y]*100:+.0f}/{sp[y]*100:+.0f}" for y in sorted(ann)))

# dashboard data (month-end NAV, yearly returns, headline stats)
import os
OUT = os.environ.get('PUB_OUT')
if OUT:
    nav = np.cumprod(1 + r); sn = np.cumprod(1 + R['SPY'][s0 + 1:]); dd = lambda x: (x / np.maximum.accumulate(x) - 1).min() * 100
    with open(OUT + '/nav.csv', 'w') as f:
        f.write('date,strategy,spy\n' + f"{dates[s0]},1.0000,1.0000\n")
        for k, d in enumerate(ds):
            if k == len(ds) - 1 or d[:7] != ds[k + 1][:7]: f.write(f"{d},{nav[k]:.4f},{sn[k]:.4f}\n")
    with open(OUT + '/years.csv', 'w') as f:
        f.write('year,strategy_pct,spy_pct\n')
        for y in sorted(ann): f.write(f"{y + (' (part)' if y in (ds[0][:4], ds[-1][:4]) else '')},{ann[y]*100:.1f},{sp[y]*100:.1f}\n")
    sh = lambda x: x.mean() * 252 / (x.std(ddof=1) * 252 ** .5); cg = lambda x: (x[-1] ** (252 / len(x)) - 1) * 100
    with open(OUT + '/stats.csv', 'w') as f:
        f.write('series,cagr_pct,sharpe,max_drawdown_pct,worst_year_pct,cagr_after_tax_pct,growth_of_1\n')
        f.write(f"Public strategy,{cg(nav):.1f},{sh(r):.2f},{dd(nav):.1f},{min(ann.values())*100:.1f},{cg(np.cumprod(1+rt)):.1f},{nav[-1]:.2f}\n")
        f.write(f"SPY buy and hold,{cg(sn):.1f},{sh(R['SPY'][s0+1:]):.2f},{dd(sn):.1f},{min(sp.values())*100:.1f},{(fin ** (252 / len(sn)) - 1) * 100:.1f},{sn[-1]:.2f}\n")
