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
up = np.zeros(n, bool); on = False
for i in range(200, n):
    g = px[i] / m200[i] - 1; on = (g > -0.01) if on else (g > 0.01); up[i] = on
strong = (px > m50) & (m50 > m200)
vt = np.minimum(2.0, 0.20 / np.where(vol > 0, vol, np.nan))
E = {'S1 200-day 1x': np.where(up, 1.0, 0.0), 'S2 200-day 2x': np.where(up, 2.0, 0.0),
     'S3 200-day + vol target': np.where(up, np.nan_to_num(vt), 0.0),
     'S4 simple live': np.where(up, np.minimum(2.0, np.where(strong, 2.0, 1.0) * np.minimum(1.0, 0.20 / np.where(vol > 0, vol, np.nan))), 0.0)}
E['S4 simple live'] = np.nan_to_num(E['S4 simple live'])
def run(e, lag=0):
    if lag: e = np.r_[np.zeros(lag), e[:-lag]]
    r = np.zeros(n)
    for i in range(1, n):
        x = e[i - 1]
        r[i] = x * tr[i] + (1 - x) * cash[i] - max(x - 1, 0) * 0.003 / 252 - (0.009 / 252 * x if x > 1 else 0) \
               - 0.0002 * abs(e[i - 1] - (e[i - 2] if i > 1 else 0))
    return r
def st(r, a, b):
    m = np.array([(a <= d < b) for d in dates]); rr = r[m]; ds = [d for d, k in zip(dates, m) if k]
    nav = np.cumprod(1 + rr); dd = (nav / np.maximum.accumulate(nav) - 1).min(); v = rr.std(ddof=1) * 252 ** .5
    yr = {}
    for d, x in zip(ds, rr): yr.setdefault(d[:4], []).append(x)
    ann = {y: np.prod(1 + np.array(z)) - 1 for y, z in yr.items()}
    return nav[-1] ** (252 / len(rr)) - 1, (rr - cash[m]).mean() * 252 / v, dd, min(ann.values()), ann
BH = tr
eras = [('1951-01-01', '2100', '1951-2026 (76y)'), ('1951-01-01', '1990-01-01', '1951-1989'), ('1990-01-01', '2100', '1990-2026'), ('2007-01-01', '2100', '2007-2026')]
for a, b, lab in eras:
    print(f"\n== {lab} ==   CAGR / excess Sharpe / MaxDD / worst year / years beating SPY")
    _, _, _, _, abh = st(BH, a, b); c, s, dd, w, _ = st(BH, a, b)
    print(f"  {'S&P 500 total return':28s} {c*100:5.1f}% {s:5.2f} {dd*100:6.1f}% {w*100:6.1f}%")
    for k, e in E.items():
        for lag in (0, 1):
            c, s, dd, w, ann = st(run(e, lag), a, b)
            beat = sum(ann[y] > abh[y] for y in ann); nyr = len(ann)
            print(f"  {k + (' (1 day late)' if lag else ''):28s} {c*100:5.1f}% {s:5.2f} {dd*100:6.1f}% {w*100:6.1f}%  {beat}/{nyr}")
for k, e in E.items():
    print(f"{k}: avg exposure {e[200:].mean():.2f}x, switches/yr {np.sum(np.abs(np.diff((e > 0).astype(int)))) / ((n - 200) / 252):.1f}")
