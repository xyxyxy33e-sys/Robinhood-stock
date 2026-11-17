"""Research only. Reads days.csv (build.py) and prints every table in the README.

    python3 paper-track/research_notes/vol_predict_2026_11/analyze.py > analyze.log
"""
import os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
d = pd.read_csv(os.path.join(HERE, 'days.csv'), index_col=0)
START = sys.argv[1] if len(sys.argv) > 1 else '1999'
d = d[d.index >= START]
d['abs'] = d.ret.abs()
d['year'] = d.index.str[:4].astype(int)
up = d.sort_values('ret', ascending=False).head(100)
dn = d.sort_values('ret').head(100)
pd.set_option('display.width', 220); pd.set_option('display.max_rows', 200)

def spear(a, b):
    m = a.notna() & b.notna(); return a[m].rank().corr(b[m].rank())
def auc(score, y):
    m = score.notna() & y.notna(); s, y = score[m], y[m].astype(bool)
    if y.sum() == 0 or (~y).sum() == 0: return np.nan
    r = s.rank()
    return (r[y].sum() - y.sum() * (y.sum() + 1) / 2) / (y.sum() * (~y).sum())

print('== 0. sample'); print(len(d), d.index[0], d.index[-1], 'up cut %.2f%% down cut %.2f%%' % (up.ret.min()*100, dn.ret.max()*100))

print('\n== 1. where the top 100 sit: year counts (up / down / either)')
yc = pd.DataFrame({'up': up.year.value_counts(), 'down': dn.year.value_counts()}).fillna(0).astype(int).sort_index()
yc['days'] = d.year.value_counts(); print(yc.T.to_string())
both = pd.concat([up, dn])
for lab, lo, hi in (('1999-2002', 1999, 2002), ('2003-2007', 2003, 2007), ('2008-2009', 2008, 2009), ('2010-2019', 2010, 2019), ('2020-2026', 2020, 2026)):
    print(lab, 'up', ((up.year >= lo) & (up.year <= hi)).sum(), 'down', ((dn.year >= lo) & (dn.year <= hi)).sum(), 'share of all days %.1f%%' % (((d.year >= lo) & (d.year <= hi)).mean()*100))

print('\n== 2. prior-day signal medians: top-100 up vs top-100 down vs all days')
F = ['p_vix', 'p_vxn', 'p_ratio', 'p_vix_chg1', 'p_vix_chg5', 'p_vix_pct252', 'p_rv10', 'p_rv30', 'p_vrp', 'p_ret1', 'p_absret1', 'p_ret5', 'p_gap50', 'p_gap200', 'p_dd252']
t = pd.DataFrame({'all days': d[F].median(), 'top100 up': up[F].median(), 'top100 down': dn[F].median()})
print(t.round(4).to_string())
print('\nshares:')
for lab, f in (('prior VIX >= 25', lambda x: x.p_vix >= 25), ('prior VIX >= 30', lambda x: x.p_vix >= 30), ('prior VIX < 20', lambda x: x.p_vix < 20),
               ('below 200d SMA', lambda x: x.p_gap200 < 0), ('below 50d SMA', lambda x: x.p_gap50 < 0), ('rv10 >= 30%', lambda x: x.p_rv10 >= 30),
               ('prior day |move| >= 2%', lambda x: x.p_absret1 >= 0.02), ('prior day down', lambda x: x.p_ret1 < 0),
               ('VIX > VIX3M (2008+)', lambda x: x.p_ratio[x.p_ratio.notna()] > 1), ('drawdown <= -10%', lambda x: x.p_dd252 <= -0.10)):
    print('  %-26s all %5.1f%%   up %5.1f%%   down %5.1f%%' % (lab, f(d).mean()*100, f(up).mean()*100, f(dn).mean()*100))
print('\nstate the day before (share):')
sc = pd.DataFrame({'all': d.p_state.value_counts(normalize=True), 'up': up.p_state.value_counts(normalize=True), 'down': dn.p_state.value_counts(normalize=True)}).fillna(0)
print((sc*100).round(1).to_string())

def bucket_table(x, col, edges, labels):
    b = pd.cut(x[col], edges, labels=labels, right=False)
    g = x.groupby(b, observed=True)
    t = pd.DataFrame({'days': g.size(), 'share%': g.size() / len(x) * 100, 'mean|r|%': g['abs'].mean()*100, 'implied 1d%': g[col].mean() / np.sqrt(252) if col == 'p_vix' else np.nan,
                      'P(|r|>=2%)': g.apply(lambda z: (z['abs'] >= .02).mean()*100), 'P(r<=-2%)': g.apply(lambda z: (z.ret <= -.02).mean()*100),
                      'P(r>=+2%)': g.apply(lambda z: (z.ret >= .02).mean()*100), 'mean r%': g.ret.mean()*100, 'median r%': g.ret.median()*100,
                      'top100 up': g.apply(lambda z: z.index.isin(up.index).sum()), 'top100 dn': g.apply(lambda z: z.index.isin(dn.index).sum())})
    return t.round(2)
E = [0, 13, 16, 20, 25, 30, 40, 200]; L = ['<13', '13-16', '16-20', '20-25', '25-30', '30-40', '40+']
print('\n== 3. next-day QQQ by prior-day VIX, all years'); print(bucket_table(d, 'p_vix', E, L).to_string())
print('\n== 3b. same, 2010-2026 only'); print(bucket_table(d[d.year >= 2010], 'p_vix', E, L).to_string())
print('\n== 3c. by prior 10-day realized vol'); print(bucket_table(d, 'p_rv10', [0, 10, 15, 20, 30, 40, 60, 500], ['<10', '10-15', '15-20', '20-30', '30-40', '40-60', '60+']).drop(columns='implied 1d%').to_string())

print('\n== 4. SIZE: does a signal rank tomorrow\'s |move|? Spearman corr with |r| and AUC for a big day')
big2 = d['abs'] >= .02; big3 = d['abs'] >= .03; top = d.index.isin(both.index)
rows = []
for f in F:
    x = d[f]
    row = {'signal': f, 'spearman |r|': spear(x, d['abs']), 'AUC |r|>=2%': auc(x, big2), 'AUC |r|>=3%': auc(x, big3), 'AUC top-200': auc(x, pd.Series(top, index=d.index))}
    for lab, m in (('99-09', d.year <= 2009), ('10-19', (d.year >= 2010) & (d.year <= 2019)), ('20-26', d.year >= 2020)):
        row['AUC2 ' + lab] = auc(x[m], big2[m])
    rows.append(row)
print(pd.DataFrame(rows).set_index('signal').round(3).to_string())
print('base rates: |r|>=2%% %.1f%%, |r|>=3%% %.1f%%' % (big2.mean()*100, big3.mean()*100))

print('\n== 5. DIRECTION: does a signal rank tomorrow\'s signed return? Spearman with r; AUC for down among big days')
rows = []
bd = d[big2]; isdn = bd.ret < 0
for f in F:
    x = d[f]
    rows.append({'signal': f, 'spearman r': spear(x, d.ret), 'AUC down-day (all days)': auc(x, d.ret < 0),
                 'AUC down | big2': auc(bd[f], isdn), 'AUC r<=-2% (all days)': auc(x, d.ret <= -.02), 'AUC r>=+2% (all days)': auc(x, d.ret >= .02)})
print(pd.DataFrame(rows).set_index('signal').round(3).to_string())
print('big2 days %d, down share %.1f%%' % (len(bd), isdn.mean()*100))
print('\nP(down | big day) by condition the day before:')
for lab, m in (('all big days', bd.ret == bd.ret), ('prior VIX >= 30', bd.p_vix >= 30), ('prior VIX < 20', bd.p_vix < 20), ('prior day up >= 2%', bd.p_ret1 >= .02), ('prior day down <= -2%', bd.p_ret1 <= -.02),
               ('VIX rose >= 10% prior day', bd.p_vix_chg1 >= .10), ('VIX fell >= 10% prior day', bd.p_vix_chg1 <= -.10), ('below 200d', bd.p_gap200 < 0), ('above 200d', bd.p_gap200 >= 0),
               ('VIX > VIX3M', bd.p_ratio > 1), ('VIX <= VIX3M', bd.p_ratio <= 1)):
    z = bd[m]; print('  %-28s n %4d  down %5.1f%%  mean r %+.2f%%' % (lab, len(z), (z.ret < 0).mean()*100, z.ret.mean()*100))

print('\n== 6. walk-forward model (expanding window, refit each Jan, tested on the next year, 2005-2026)')
def fit_logit(X, y, l2=1.0, it=50):
    w = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-X @ w)); W = p * (1 - p) + 1e-9
        H = X.T @ (X * W[:, None]) + l2 * np.eye(X.shape[1]); g = X.T @ (y - p) - l2 * w
        w = w + np.linalg.solve(H, g)
    return w
def walk(feats, target, start=max(2005, int(START[:4]) + 4)):
    x = d[feats + ['year']].copy(); x['y'] = target.astype(float); x = x.dropna()
    pred = pd.Series(index=x.index, dtype=float)
    for yr in range(start, 2027):
        tr, te = x[x.year < yr], x[x.year == yr]
        if len(te) == 0: continue
        mu, sd = tr[feats].mean(), tr[feats].std()
        Xtr = np.c_[np.ones(len(tr)), ((tr[feats] - mu) / sd).values]; Xte = np.c_[np.ones(len(te)), ((te[feats] - mu) / sd).values]
        w = fit_logit(Xtr, tr.y.values); pred[te.index] = 1 / (1 + np.exp(-Xte @ w))
    pred = pred.dropna(); return pred, x.loc[pred.index, 'y']
d['l_vix'] = np.log(d.p_vix); d['l_rv10'] = np.log(d.p_rv10.clip(lower=1)); d['l_rv30'] = np.log(d.p_rv30.clip(lower=1))
sets = {'VIX only': ['l_vix'], 'rv10 only': ['l_rv10'], 'VIX + rv10 + rv30': ['l_vix', 'l_rv10', 'l_rv30'],
        'vol + trend + yesterday': ['l_vix', 'l_rv10', 'l_rv30', 'p_absret1', 'p_gap200', 'p_dd252', 'p_vix_chg1', 'p_ret1'],
        'kitchen sink': ['l_vix', 'l_rv10', 'l_rv30', 'p_absret1', 'p_gap200', 'p_gap50', 'p_dd252', 'p_vix_chg1', 'p_vix_chg5', 'p_ret1', 'p_ret5', 'p_vix_pct252']}
for tl, tg in (('big day |r|>=2%', big2), ('big DOWN r<=-2%', d.ret <= -.02), ('big UP r>=+2%', d.ret >= .02), ('any down day', d.ret < 0)):
    print(' target:', tl)
    for nm, fs in sets.items():
        p, y = walk(fs, tg)
        top10 = p >= p.quantile(.9)
        print('   %-26s OOS AUC %.3f | top-decile days: hit rate %5.1f%% vs base %5.1f%%, catch %4.1f%% of events' % (nm, auc(p, y), y[top10].mean()*100, y.mean()*100, y[top10].sum() / y.sum() * 100))
p_dn, y_dn = walk(sets['vol + trend + yesterday'], d.ret <= -.02); p_up, y_up = walk(sets['vol + trend + yesterday'], d.ret >= .02)
print(' corr of the big-DOWN and big-UP forecasts (same features): %.3f' % p_dn.corr(p_up))
edge = (p_dn - p_up); q = pd.qcut(edge, 5, labels=False)
print(' quintiles of (P down-big minus P up-big), next-day mean return %:', (d.ret.loc[edge.index].groupby(q).mean()*100).round(3).tolist())

print('\n== 7. how well does VIX size the move? realized next-day |r| / VIX-implied 1-day sigma')
z = d.dropna(subset=['p_vix']); k = z.ret / (z.p_vix / 100 / np.sqrt(252))
print(' QQQ |r| in VIX sigmas: median %.2f, mean %.2f, share beyond 2 sigma %.1f%%, beyond 3 sigma %.1f%% (normal: 4.6%% / 0.3%%)' % (k.abs().median(), k.abs().mean(), (k.abs() > 2).mean()*100, (k.abs() > 3).mean()*100))
print(' top-100 down days in VIX sigmas: median %.2f; top-100 up: %.2f' % (k[dn.index.intersection(k.index)].abs().median(), k[up.index.intersection(k.index)].abs().median()))
z2 = d.dropna(subset=['p_vxn']); k2 = z2.ret / (z2.p_vxn / 100 / np.sqrt(252))
print(' vs VXN (Nasdaq-100 vol index, 2001+): median %.2f, beyond 2 sigma %.1f%%, beyond 3 sigma %.1f%%' % (k2.abs().median(), (k2.abs() > 2).mean()*100, (k2.abs() > 3).mean()*100))
print(' biggest surprises (down days from calm, prior VIX < 20, r <= -3%):')
print(d[(d.p_vix < 20) & (d.ret <= -.03)][['ret', 'p_vix', 'p_rv10', 'p_gap200', 'p_state']].round(4).to_string())
print(' big up days from calm (prior VIX < 20, r >= +3%):', len(d[(d.p_vix < 20) & (d.ret >= .03)]))

print('\n== 8. the day AFTER: do big days cluster?')
for lab, m in (('after a top-100 down day', d.index.isin(dn.index)), ('after a top-100 up day', d.index.isin(up.index)), ('after |r|>=2%', big2.values), ('after a quiet day |r|<1%', (d['abs'] < .01).values)):
    nxt = d.ret.shift(-1)[m].dropna()
    print('  %-26s n %4d  next-day mean %+.2f%%  mean|r| %.2f%%  P(|r|>=2%%) %5.1f%%  P(down) %5.1f%%' % (lab, len(nxt), nxt.mean()*100, nxt.abs().mean()*100, (nxt.abs() >= .02).mean()*100, (nxt < 0).mean()*100))
