import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/vol'); sys.path.insert(1, '/home/user/Robinhood-stock/paper-track')
import numpy as np, harness as H, untouched_test as U
from harness import MC, S
D0 = '2006-11-17'
NEW = dict(H.CUR, gross_cap=S.GROSS_CAP)
BARE = dict(NEW, trim='none', d_gate=False, d_ladder=False, fast=False)
vix, _ = U.vix_hist()
def summary(name, r, ds):
    nav = np.cumprod(1 + r); dd = (nav / np.maximum.accumulate(nav) - 1).min(); v = r.std(ddof=1) * 252 ** .5
    yr = {}
    for d, x in zip(ds, r): yr.setdefault(d[:4], []).append(x)
    ann = {y: np.prod(1 + np.array(a)) - 1 for y, a in yr.items()}
    return dict(name=name, c=nav[-1] ** (252 / len(r)) - 1, sh=r.mean() * 252 / v, m=dd, v=v, end=100000 * nav[-1], ann=ann)
rows = []
# 1) the live strategy as it is (QQQ signals, QQQ-core proxy, synthetic 2x/3x)
p = H.p; ds = p['dates']; s0 = next(i for i, d in enumerate(ds) if d >= D0)
r = H.run(False, d0=D0, cfg=NEW, vixm=False)[0]; rows.append(summary('Live strategy (QQQ-based), as designed', r, ds[s0+1:]))
rows.append(summary('S&P 500 buy & hold (SPY + dividends)', p['spy'][s0+1:], ds[s0+1:]))
rows.append(summary('QQQ buy & hold (+ dividends)', p['qqq_tr'][s0+1:], ds[s0+1:]))
# 2) the same rules run on the S&P 500 itself (own signals, SPY core, synthetic 2x/3x S&P, QQQ legs = SPY)
spx = MC._load('spy_long_history.csv'); ps = U.panel(spx, div=MC.SPY_DIV); sgs = U.sigs(ps)
dss = ps['dates']; s1 = next(i for i, d in enumerate(dss) if d >= D0); e1 = len(dss) - 1
for cfg, ql, lab in ((NEW, True, 'Live rules run on the S&P 500 (2x/3x S&P)'), (BARE, False, 'Bare rules on the S&P 500 (states + vol + cap)')):
    rr, tpy, _ = U.run(sgs, ps, cfg, ql, vix, s1, e1, 0)
    rows.append(summary(lab, rr, dss[s1+1:e1+1]))
print(f"Window {D0} -> {ds[-1]} (~20 years). $100,000 start. Before tax, 2bp costs, synthetic leverage at T-bill+0.3% financing + ETF fees.")
print(f"{'':48s}{'CAGR':>7}{'Sharpe':>8}{'MaxDD':>8}{'vol':>7}{'$100k ->':>13}")
for x in rows:
    print(f"{x['name']:48s}{x['c']*100:6.1f}%{x['sh']:8.2f}{x['m']*100:7.1f}%{x['v']*100:6.1f}%{x['end']:13,.0f}")
spy = rows[1]['ann']
print('\nCalendar years (2006 and 2026 partial):')
print('year  ' + ''.join(f"{x['name'][:14]:>16}" for x in rows))
for y in sorted(spy):
    print(y + '  ' + ''.join(f"{x['ann'].get(y, np.nan)*100:15.1f}%" for x in rows))
for x in rows[:1] + rows[3:]:
    beat = sum(x['ann'][y] > spy[y] for y in spy if y in x['ann'] and y not in ('2006', '2026'))
    print(f"{x['name']}: beat S&P buy & hold in {beat} of 19 full years")
