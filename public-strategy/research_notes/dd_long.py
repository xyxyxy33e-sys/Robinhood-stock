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

up = np.zeros(n, bool); on = False
for i in range(200, n):
    g = px[i] / m200[i] - 1; on = (g > -0.01) if on else (g > 0.01); up[i] = on
lr=np.log(1+pr); v2=np.full(n,np.nan)
for i in range(31,n): v2[i]=max(lr[i-9:i+1].std(ddof=1), lr[i-29:i+1].std(ddof=1))*252**.5
def vt(T):
    sc=np.minimum(1.0,T/(2*np.where(v2>0,v2,np.nan))); sc=np.nan_to_num(np.round(sc*4)/4,nan=1.0); sc[sc<.25]=.25; return sc
eras=[('1951-01-01','2007-07-01','1951-2007 (untouched)'),('1951-01-01','1975-01-01','1951-1974'),('1975-01-01','1990-01-01','1975-1989'),('1990-01-01','2007-07-01','1990-2007'),('2007-07-01','2100','2007-2026'),('1951-01-01','2100','1951-2026')]
i87=dates.index('1987-10-19')
def dd15(r):
    m=np.array([d>='1951-01-01' for d in dates]); nav=np.cumprod(1+r[m]); u=nav/np.maximum.accumulate(nav)-1; return np.mean(u<=-.30)*100
print("TREND HALF ALONE on 75 years: S&P above its 200-day line -> exposure shown, else T-bills.  CAGR / Sharpe / MaxDD per era")
print("  variant                    | "+" | ".join(f"{l:21s}" for _,_,l in eras)+" | 19 Oct 1987 | Oct 1987 | days <= -30% | changes/yr")
for nm,ex in (('2x (current)',np.full(n,2.0)),('2x, vol target 40%',2*vt(.40)),('2x, vol target 30%',2*vt(.30)),('2x, vol target 25%',2*vt(.25)),('1.5x',np.full(n,1.5)),('1x',np.full(n,1.0))):
    e=np.where(up,ex,0.0); r=run(e); o=[i for i,d in enumerate(dates) if d[:7]=='1987-10']
    print(f"  {nm:26s} | "+" | ".join("{:5.1f} {:4.2f} {:6.1f}  ".format(*(lambda t:(t[0]*100,t[1],t[2]*100))(st(r,a,bb))) for a,bb,_ in eras)+f" | {r[i87]*100:6.1f}%     | {(np.prod(1+r[o])-1)*100:6.1f}%  | {dd15(r):5.1f}%       | {np.sum(np.diff(e)!=0)/((n-200)/252):.1f}")
print(f"  {'S&P 500 buy & hold':26s} | "+" | ".join("{:5.1f} {:4.2f} {:6.1f}  ".format(*(lambda t:(t[0]*100,t[1],t[2]*100))(st(tr,a,bb))) for a,bb,_ in eras)+f" | {tr[i87]*100:6.1f}%")
