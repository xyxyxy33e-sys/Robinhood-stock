"""Simple S&P trend rules for an IRA vs S&P 500 total return, 1950-2026. PRE-REGISTERED, no tuning:
S1 200-day: S&P above its 200-day average (1% hysteresis) -> 100% S&P, else T-bills.
S2 200-day 2x: same, 2x S&P when above.
S3 200-day + vol target: when above, exposure = min(2, 20% / max(10d, 30d) realized vol), else T-bills.
S4 simple live: above the 200-day -> 1x, and 2x when also above the 50-day with the 50-day above the 200-day;
   then scaled by the same vol target, capped at 2x; below the 200-day -> T-bills.
Decide at close t, earn t+1 (as the live 15:50 run); lag-1 variant too. Costs: 2bp per unit of exposure change;
leverage financed at T-bills + 0.3%, plus 0.9%/yr fee on the 2x-fund share. Total return: SPY adjusted from 1993-02,
before that ^GSPC + decade dividend yields (1950s 4.5%, 60s 3.2%, 70s 4.0%, 80s 4.2%, 1990-92 3.2%).
Cash: 3m T-bill (Ken French RF before 1981-09)."""
import sys, json, datetime as dt, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/vol'); sys.path.insert(1, '/home/user/Robinhood-stock/paper-track')
import numpy as np, untouched_test as U
DL = '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/ira/dl/'
def load(s, adj):
    d = json.load(open(DL + s + '.json'))['chart']['result'][0]
    v = d['indicators']['adjclose'][0]['adjclose'] if adj else d['indicators']['quote'][0]['close']
    return {(dt.datetime(1970, 1, 1) + dt.timedelta(seconds=t)).date().isoformat(): x for t, x in zip(d['timestamp'], v) if x}
gs, spy = load('GSPC', False), load('SPY', True)
dates = sorted(gs); n = len(dates); px = np.array([gs[d] for d in dates])
pr = np.r_[0, px[1:] / px[:-1] - 1]
def dy(d):
    y = int(d[:4]); return 0.045 if y < 1960 else 0.032 if y < 1970 else 0.040 if y < 1980 else 0.042 if y < 1990 else 0.032
tr = pr.copy()
for i in range(1, n):
    d, p = dates[i], dates[i - 1]
    tr[i] = (spy[d] / spy[p] - 1) if (d >= '1993-02-01' and d in spy and p in spy) else pr[i] + dy(d) / 252
cash = U.rates(dates) / 252
def sma(x, k): c = np.cumsum(np.insert(x, 0, 0)); o = np.full(len(x), np.nan); o[k-1:] = (c[k:] - c[:-k]) / k; return o
m50, m200 = sma(px, 50), sma(px, 200)
vol = np.full(n, np.nan)
for i in range(31, n):
    vol[i] = max(pr[i-9:i+1].std(ddof=1), pr[i-29:i+1].std(ddof=1)) * 252 ** .5

def run(e):
    r = np.zeros(n)
    for i in range(1, n):
        x = e[i - 1]
        r[i] = x * tr[i] + (1 - x) * cash[i] - max(x - 1, 0) * 0.003 / 252 - (0.009 / 252 * x if x > 1 else 0) - 0.0002 * abs(e[i - 1] - (e[i - 2] if i > 1 else 0))
    return r
def st(r, a, b):
    m = np.array([(a <= d < b) for d in dates]); rr = r[m]
    nav = np.cumprod(1 + rr); dd = (nav / np.maximum.accumulate(nav) - 1).min(); v = rr.std(ddof=1) * 252 ** .5
    return nav[-1] ** (252 / len(rr)) - 1, (rr - cash[m]).mean() * 252 / v, dd

import datetime as D
wd=[D.date.fromisoformat(d).isocalendar()[:2] for d in dates]; we=[i for i in range(n-1) if wd[i]!=wd[i+1]]; me=[i for i in range(n-1) if dates[i][:7]!=dates[i+1][:7]]
eras=[('1951-01-01','2007-07-01','1951-2007 (untouched)'),('1951-01-01','1975-01-01','1951-1974'),('1975-01-01','1990-01-01','1975-1989'),('1990-01-01','2007-07-01','1990-2007'),('2007-07-01','2100','2007-2026'),('1951-01-01','2100','1951-2026')]
i87=[i for i,d in enumerate(dates) if d[:7]=='1987-10']
print("2x S&P above the 200-day line (1% band), T-bills below; how often the rule is checked.  CAGR / Sharpe / MaxDD (worst phase)")
print("  schedule                   | "+" | ".join(f"{l:21s}" for _,_,l in eras)+" | Oct 1987 (worst phase) | switches/yr")
for nm,sets in (('daily (current)',[set(range(n))]),('every 2nd day',[set(range(k,n,2)) for k in (0,1)]),('weekly (5 weekdays)',[set(i+k for i in we) for k in range(5)]),
                ('every 2 weeks',[set(i+k for i in we[j::2]) for j in (0,1) for k in (0,2)]),('monthly (4 phases)',[set(i+k for i in me) for k in (0,5,10,15)])):
    acc=[]; o87=[]; sw=[]
    for CHK in sets:
        up=np.zeros(n,bool); on=False
        for i in range(200,n):
            if i in CHK:
                g=px[i]/m200[i]-1; on=(g>-0.01) if on else (g>0.01)
            up[i]=on
        r=run(np.where(up,2.0,0.0)); acc.append([st(r,a,b) for a,b,_ in eras]); o87.append(np.prod(1+r[i87])-1); sw.append(np.sum(np.diff(up.astype(int))!=0)/((n-200)/252))
    A=np.array(acc)
    print(f"  {nm:26s} | "+" | ".join(f"{A[:,k,0].mean()*100:5.1f} {A[:,k,1].mean():4.2f} {A[:,k,2].min()*100:6.1f}  " for k in range(len(eras)))+f" | {min(o87)*100:6.1f}%               | {np.mean(sw):.1f}")
