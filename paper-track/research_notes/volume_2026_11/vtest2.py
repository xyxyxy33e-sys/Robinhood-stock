import sys, json, warnings, datetime as dt; warnings.filterwarnings('ignore')
import numpy as np
sys.path.insert(0, '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/vol'); sys.path.insert(1, '/home/user/Robinhood-stock/paper-track')
import harness as H
from harness import MC, S
d = json.load(open('/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/vol/qqq.json'))['chart']['result'][0]
YV = {dt.datetime.utcfromtimestamp(t).date().isoformat(): v for t, v in zip(d['timestamp'], d['indicators']['quote'][0]['volume']) if v}
PD = H.PD; NEW = dict(H.CUR, gross_cap=S.GROSS_CAP)
q = H.p['qqq']; px = np.cumprod(1 + q)
vol = np.array([YV.get(x, np.nan) for x in PD], float)
print('dates', PD[0], PD[-1], 'missing volume', int(np.isnan(vol).sum()))
for i in range(1, len(vol)):
    if np.isnan(vol[i]): vol[i] = vol[i-1]
def sma(x, n):
    c = np.cumsum(np.insert(x, 0, 0)); o = np.full(len(x), np.nan); o[n-1:] = (c[n:] - c[:-n]) / n; return o
rv = vol / sma(vol, 50)                         # relative volume vs 50-day average
down = q < 0
dist = (down & (rv > 1.0)).astype(float)        # "red day on above-average volume" (the tweet's definition)
d25 = sma(vol, 20) / sma(vol, 100)   # 20-day / 100-day average volume (feature under test)
up_rv = np.where(~down, rv, np.nan)
eff = MC._eff(H.sig, NEW)[0]; L = 'ABCDEF'
fwd = {h: np.array([px[min(i+h, len(px)-1)] / px[i] - 1 if i + h < len(px) else np.nan for i in range(len(px))]) for h in (1, 5, 20)}
def table(mask_era, lab):
    print(f'\n== {lab}: next-20-session QQQ return by state, split by 20d/100d avg volume ratio (tercile) ==')
    print('state   n  | low D25  mid  high | high-low  t(20d, non-overlap) | next-1d by RV>1.5 on red days')
    for k, s in enumerate(L):
        m = (eff == k) & mask_era & ~np.isnan(d25) & ~np.isnan(fwd[20]) & (np.arange(len(PD)) > 75)
        if m.sum() < 60: print(s, int(m.sum()), 'too few'); continue
        x = d25[m]; f = fwd[20][m]; lo, hi = np.percentile(x, [33.3, 66.7])
        g = [f[x <= lo].mean(), f[(x > lo) & (x <= hi)].mean(), f[x > hi].mean()]
        idx = np.where(m)[0]; sel = idx[::20]          # non-overlapping 20d samples
        xs, fs = d25[sel], fwd[20][sel]; a, b = fs[xs > hi], fs[xs <= lo]
        t = (a.mean() - b.mean()) / np.sqrt(a.var(ddof=1)/max(len(a),2) + b.var(ddof=1)/max(len(b),2)) if len(a) > 2 and len(b) > 2 else np.nan
        mr = m & down & (rv > 1.5); mn = m & down & (rv <= 1.0)
        print(f"{s} {int(m.sum()):5d} | {g[0]*100:+5.1f}% {g[1]*100:+5.1f}% {g[2]*100:+5.1f}% | {(g[2]-g[0])*100:+5.1f}pp  t={t:+.2f} (n {len(a)}/{len(b)}) | "
              f"heavy-red {np.nanmean(fwd[1][mr])*100:+.2f}% (n {int(mr.sum())}) vs light-red {np.nanmean(fwd[1][mn])*100:+.2f}%")
era = np.array(PD)
print('ratio pct (proxy): p10/p33/p50/p67/p90/p95', np.round(np.nanpercentile(d25,[10,33.3,50,66.7,90,95]),2))
table((era >= '2001-01-01') & (era < '2015-11-01'), '2001-Oct 2015 (holdout era)')
table(era >= '2015-11-01', 'Nov 2015-2026')
# current reading
i = len(PD) - 1
print(f"\nlatest {PD[i]}: eff {L[eff[i]]}, 20d/100d volume ratio = {d25[i]:.2f}, RV {rv[i]:.2f}")
np.save('/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/vol/feat2010.npy', np.stack([d25, rv]))
