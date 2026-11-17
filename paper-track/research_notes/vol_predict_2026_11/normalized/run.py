"""Research only. Surprise-ranked QQQ days. Reads ../days.csv, prints everything (see PLAN.md).
    python3 run.py > run.log
"""
import os
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), 'days.csv')
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 300); pd.set_option('display.max_columns', 50)
S252 = np.sqrt(252)
d = pd.read_csv(SRC, index_col=0)
d['year'] = d.index.str[:4].astype(int)
d['abs'] = d.ret.abs()

def hdr(t): print('\n' + '=' * 100 + '\n' + t + '\n' + '=' * 100)
def auc(score, y):
    m = score.notna() & y.notna(); s, y = score[m], y[m].astype(bool)
    if y.sum() == 0 or (~y).sum() == 0: return np.nan
    r = s.rank(); return (r[y].sum() - y.sum() * (y.sum() + 1) / 2) / (y.sum() * (~y).sum())
def rcorr(a, b):
    m = a.notna() & b.notna(); return a[m].rank().corr(b[m].rank())

# ---------------------------------------------------------------- scores
def ewma_sigma(ret, lam=0.94, seed=30):
    r = ret.values; n = len(r); s2 = np.full(n, np.nan)
    s2[seed] = np.mean(r[:seed] ** 2)
    for t in range(seed + 1, n): s2[t] = lam * s2[t - 1] + (1 - lam) * r[t - 1] ** 2
    return pd.Series(np.sqrt(s2), index=ret.index)
def build_scores(df):
    o = pd.DataFrame(index=df.index)
    o['sig_main'] = np.maximum(df.p_rv10, df.p_rv30) / 100 / S252      # NaN if either is NaN
    o['sig_rv30'] = df.p_rv30 / 100 / S252
    o['sig_vix'] = df.p_vix / 100 / S252
    o['sig_vxn'] = df.p_vxn / 100 / S252
    o['sig_ewma'] = ewma_sigma(df.ret)
    return o
sg = build_scores(d)
for k, nm in (('main', 'z'), ('rv30', 'z_rv30'), ('vix', 'z_vix'), ('vxn', 'z_vxn'), ('ewma', 'z_ewma')):
    d[nm] = d.ret / sg['sig_' + k]
SC = {'z (rv max10,30) MAIN': 'z', 'z_rv30': 'z_rv30', 'z_vix': 'z_vix', 'z_vxn': 'z_vxn', 'z_ewma': 'z_ewma'}

hdr('0. sample and look-ahead checks')
print('sessions', len(d), d.index[0], d.index[-1])
print('z available: main %d, rv30 %d, vix %d, vxn %d, ewma %d' % tuple(d[c].notna().sum() for c in ('z', 'z_rv30', 'z_vix', 'z_vxn', 'z_ewma')))
# check 1: rebuild rv from returns through t-1
lr = np.log1p(d.ret)
rv10 = lr.rolling(10).std() * S252 * 100; rv30 = lr.rolling(30).std() * S252 * 100
m = d.p_rv30.notna()
print('check1 p_rv30[t] == rv30 rebuilt through t-1: max abs diff %.2e (n=%d); p_rv10: %.2e' % (
    (d.p_rv30[m] - rv30.shift(1)[m]).abs().max(), m.sum(), (d.p_rv10[d.p_rv10.notna()] - rv10.shift(1)[d.p_rv10.notna()]).abs().max()))
print('check2 p_ret1[t] == ret[t-1]: max abs diff %.2e' % (d.p_ret1.iloc[1:] - d.ret.shift(1).iloc[1:]).abs().max())
# check 3: perturb ret at t -> denominators at t unchanged, t+1 changed
base = build_scores(d.assign(**{}))
rng = np.random.RandomState(0); idx = rng.choice(np.arange(300, len(d) - 2), 25, replace=False)
bad_same = 0; bad_next = 0
for i in idx:
    # rebuild everything from perturbed returns (rv from log returns, EWMA); p_vix is exogenous and not a function of QQQ ret
    r2 = d.ret.copy(); r2.iloc[i] = r2.iloc[i] * 5 + 0.01
    l2 = np.log1p(r2); a10 = (l2.rolling(10).std() * S252 * 100).shift(1); a30 = (l2.rolling(30).std() * S252 * 100).shift(1)
    sig = np.maximum(a10, a30) / 100 / S252; e2 = ewma_sigma(r2)
    for nm, new, old in (('main', sig, base.sig_main), ('ewma', e2, base.sig_ewma)):
        if abs(new.iloc[i] - old.iloc[i]) > 1e-12: bad_same += 1
        if abs(new.iloc[i + 1] - old.iloc[i + 1]) < 1e-12: bad_next += 1
print('check3 perturbation of ret[t], 25 random days x 2 estimators: denominator at t changed in %d cases (must be 0); denominator at t+1 unchanged in %d cases (must be 0)' % (bad_same, bad_next))
print('Other columns used are p_ columns (prior close) of days.csv; extras below are rebuilt with .shift(1).')

# ---------------------------------------------------------------- 1. similarity and lists
hdr('1a. how similar are the rankings? (common sample: all five scores available)')
com = d.dropna(subset=list(SC.values())); print('common sample n =', len(com), com.index[0], com.index[-1])
names = list(SC.values()); ab = com[names].abs()
cm = pd.DataFrame({a: {b: rcorr(ab[a], ab[b]) for b in names} for a in names}); print('rank correlation of |z| (Spearman via ranks + Pearson):'); print(cm.round(3).to_string())
cs = pd.DataFrame({a: {b: rcorr(com[a], com[b]) for b in names} for a in names}); print('rank correlation of signed z:'); print(cs.round(3).to_string())
def topset(x, col, kind, n=100):
    if kind == 'abs': return set(x[col].abs().sort_values(ascending=False).head(n).index)
    if kind == 'dn': return set(x[col].sort_values().head(n).index)
    return set(x[col].sort_values(ascending=False).head(n).index)
for kind, lab in (('abs', 'top-100 by |z|'), ('dn', 'top-100 down'), ('up', 'top-100 up')):
    ov = pd.DataFrame({a: {b: len(topset(com, a, kind) & topset(com, b, kind)) for b in names} for a in names}); print('overlap of %s lists (of 100):' % lab); print(ov.to_string())
print('also: overlap with the raw-percent top-100 (same common sample): ', end='')
raw_dn = set(com.ret.sort_values().head(100).index); raw_up = set(com.ret.sort_values(ascending=False).head(100).index)
for nm in names: print('%s down %d up %d | ' % (nm, len(topset(com, nm, 'dn') & raw_dn), len(topset(com, nm, 'up') & raw_up)), end='')
print()

ERAS = (('1999-2002', 1999, 2002), ('2003-2007', 2003, 2007), ('2008-2009', 2008, 2009), ('2010-2019', 2010, 2019), ('2020-2026', 2020, 2026))
rawdn = d.sort_values('ret').head(100); rawup = d.sort_values('ret', ascending=False).head(100)
def lists(zc, x=d):
    xx = x.dropna(subset=[zc]); return xx.sort_values(zc).head(100), xx.sort_values(zc, ascending=False).head(100)
hdr('1b. year distribution of the top-100 lists (counts per era)')
rows = []
for lab, lo, hi in ERAS:
    r = {'era': lab, 'share of all days %': round(((d.year >= lo) & (d.year <= hi)).mean() * 100, 1)}
    r['raw down'] = ((rawdn.year >= lo) & (rawdn.year <= hi)).sum(); r['raw up'] = ((rawup.year >= lo) & (rawup.year <= hi)).sum()
    for nm, zc in (('main', 'z'), ('z_rv30', 'z_rv30'), ('z_vix', 'z_vix'), ('z_vxn', 'z_vxn'), ('z_ewma', 'z_ewma')):
        a, b = lists(zc); r[nm + ' down'] = ((a.year >= lo) & (a.year <= hi)).sum(); r[nm + ' up'] = ((b.year >= lo) & (b.year <= hi)).sum()
    rows.append(r)
print(pd.DataFrame(rows).set_index('era').to_string())
sdn, sup = lists('z')
print('\nmain-score cut-offs: down z <= %.2f (ret range %.2f%% .. %.2f%%), up z >= %.2f (ret range %.2f%% .. %.2f%%)' % (sdn.z.max(), sdn.ret.min() * 100, sdn.ret.max() * 100, sup.z.min(), sup.ret.min() * 100, sup.ret.max() * 100))
print('year counts, main surprise down:', sdn.year.value_counts().sort_index().to_dict()); print('year counts, main surprise up:  ', sup.year.value_counts().sort_index().to_dict())
cols = ['ret', 'z', 'z_rv30', 'z_vix', 'z_vxn', 'z_ewma', 'p_vix', 'p_vxn', 'p_ratio', 'p_vix_chg1', 'p_rv10', 'p_rv30', 'p_ret1', 'p_ret5', 'p_gap50', 'p_gap200', 'p_dd252', 'p_state']
for nm, x in (('top100_surprise_down.csv', sdn), ('top100_surprise_up.csv', sup)):
    o = x[cols].copy(); o.insert(0, 'rank', range(1, 101)); o.to_csv(os.path.join(HERE, nm), float_format='%.6f')
print('wrote top100_surprise_down.csv, top100_surprise_up.csv')
print('\ntop 15 surprise-down days:'); print(sdn.head(15)[['ret', 'z', 'z_vix', 'z_ewma', 'p_vix', 'p_rv30', 'p_state']].round(3).to_string())
print('\ntop 15 surprise-up days:'); print(sup.head(15)[['ret', 'z', 'z_vix', 'z_ewma', 'p_vix', 'p_rv30', 'p_state']].round(3).to_string())

# ---------------------------------------------------------------- 2. day before
F = ['p_vix', 'p_vxn', 'p_ratio', 'p_vix_chg1', 'p_vix_chg5', 'p_vix_pct252', 'p_rv10', 'p_rv30', 'p_vrp', 'p_ret1', 'p_absret1', 'p_ret5', 'p_gap50', 'p_gap200', 'p_dd252']
SH = (('prior VIX < 13', lambda x: x.p_vix < 13), ('prior VIX < 20', lambda x: x.p_vix < 20), ('prior VIX >= 25', lambda x: x.p_vix >= 25), ('prior VIX >= 30', lambda x: x.p_vix >= 30),
      ('below 200d SMA', lambda x: x.p_gap200 < 0), ('below 50d SMA', lambda x: x.p_gap50 < 0), ('rv10 >= 30%', lambda x: x.p_rv10 >= 30),
      ('prior day |move| >= 2%', lambda x: x.p_absret1 >= 0.02), ('prior day quiet |r| < 0.5%', lambda x: x.p_absret1 < 0.005), ('prior day down', lambda x: x.p_ret1 < 0),
      ('VIX > VIX3M (2008+)', lambda x: x.p_ratio[x.p_ratio.notna()] > 1), ('drawdown <= -10%', lambda x: x.p_dd252 <= -0.10),
      ('state A or D (levered)', lambda x: x.p_state.isin(['A', 'D'])), ('state E or F', lambda x: x.p_state.isin(['E', 'F'])))
def day_before(zc, x, label):
    a, b = lists(zc, x); allx = x.dropna(subset=[zc])
    print('\n--- %s (n all days %d; shares of state use rows with a state; prior-VIX shares use all rows) ---' % (label, len(allx)))
    print(pd.DataFrame({'all days': allx[F].median(), 'surprise down': a[F].median(), 'surprise up': b[F].median()}).round(4).to_string())
    print('shares (%):')
    for lab, f in SH:
        print('  %-28s all %5.1f   down %5.1f   up %5.1f' % (lab, f(allx).mean() * 100, f(a).mean() * 100, f(b).mean() * 100))
    sc = pd.DataFrame({'all': allx.p_state.value_counts(normalize=True), 'down': a.p_state.value_counts(normalize=True), 'up': b.p_state.value_counts(normalize=True)}).fillna(0)
    print('state at prior close (share %%, rows with a state; missing state: all %d, down %d, up %d):' % (allx.p_state.isna().sum(), a.p_state.isna().sum(), b.p_state.isna().sum()))
    print((sc * 100).round(1).T.to_string())
    print('  VIX rose on the surprise day itself is not used (it is same-day, not a prior-close signal).')
hdr('2. what the day before looked like (full history, top 100 within full history)')
for nm, zc in (('MAIN z (rv max10,30)', 'z'), ('z_vix', 'z_vix'), ('z_ewma', 'z_ewma')): day_before(zc, d, nm)
hdr('2b. same, top 100 taken within 2010-2026 only')
d10 = d[d.year >= 2010]
for nm, zc in (('MAIN z, 2010+', 'z'), ('z_vix, 2010+', 'z_vix'), ('z_ewma, 2010+', 'z_ewma')): day_before(zc, d10, nm)

# ---------------------------------------------------------------- 3. asymmetry
hdr('3. asymmetry: days beyond -k sigma vs +k sigma. cell = down/up (ratio). * = a side has <20 events: no conclusion')
KS = (2, 3, 4, 5)
def cell(x, zc, k):
    dn = int((x[zc] <= -k).sum()); up = int((x[zc] >= k).sum())
    rt = ('inf' if up == 0 and dn > 0 else ('n/a' if up == 0 else '%.2f' % (dn / up)))
    return '%d/%d (%s)%s' % (dn, up, rt, '*' if (dn < 20 or up < 20) else '')
def asym_table(x, zc):
    x = x.dropna(subset=[zc]); rows = {}
    rows['ALL (n=%d)' % len(x)] = [cell(x, zc, k) for k in KS]
    b = pd.cut(x.p_vix, [0, 13, 16, 20, 25, 30, 1000], labels=['<13', '13-16', '16-20', '20-25', '25-30', '30+'], right=False)
    for lab in b.cat.categories:
        g = x[b == lab]; rows['VIX %s (n=%d)' % (lab, len(g))] = [cell(g, zc, k) for k in KS]
    for st in 'ABCDEF':
        g = x[x.p_state == st]; rows['state %s (n=%d)' % (st, len(g))] = [cell(g, zc, k) for k in KS]
    g = x[x.p_gap200 >= 0]; rows['above 200d (n=%d)' % len(g)] = [cell(g, zc, k) for k in KS]
    g = x[x.p_gap200 < 0]; rows['below 200d (n=%d)' % len(g)] = [cell(g, zc, k) for k in KS]
    return pd.DataFrame(rows, index=['%s|z|>=%d' % ('' , k) for k in KS]).T.rename(columns=lambda c: 'z<=-%s / z>=+%s' % (c[-1], c[-1]))
csv_rows = []
for nm, x in (('FULL HISTORY', d), ('2010 ONWARD', d10)):
    for zn, zc in (('MAIN z', 'z'), ('z_vix', 'z_vix'), ('z_ewma', 'z_ewma')):
        if zn != 'MAIN z' and nm == 'FULL HISTORY' and False: continue
        print('\n--- %s, %s ---' % (zn, nm)); t = asym_table(x, zc); print(t.to_string())
        t2 = t.copy(); t2.insert(0, 'score', zn); t2.insert(0, 'period', nm); csv_rows.append(t2)
        if zn == 'MAIN z':
            pass
pd.concat(csv_rows).to_csv(os.path.join(HERE, 'asymmetry_cells.csv'))
print('\nreference: under a symmetric fat-tailed distribution the ratio would be ~1; ratios from cells with a star are not conclusions.')

# ---------------------------------------------------------------- 4. predictability
hdr('4. can surprises be predicted?')
close_fix = d.close
d['dow'] = pd.to_datetime(d.index).dayofweek
d['p_monday'] = (d.dow == 0).astype(float)
rvp = d.p_rv30.rolling(252, min_periods=126).rank(pct=True); d['p_rv_pct252'] = rvp                       # percentile of the prior-close rv30 within the last 252 readings (all <= prior close)
big = (d.ret.abs() >= 0.02).values
last = np.full(len(d), np.nan); c = np.nan
for i in range(len(d)):                       # days since the last |r|>=2% move strictly before day i
    last[i] = (i - c) if not np.isnan(c) else np.nan
    if big[i]: c = i
d['p_days_since_2pct'] = last          # 1 = the prior day was itself a >=2% move
cl = d.close.values; ds = np.full(len(d), np.nan)
for i in range(251, len(d)):
    w = cl[i - 251:i + 1]; ds[i] = 251 - np.where(w == w.max())[0][-1]
d['p_days_since_252hi'] = pd.Series(ds, index=d.index).shift(1)          # measured at the prior close
d['p_ret20'] = d.close.pct_change(20).shift(1)
d['p_vxn_vix'] = d.p_vxn / d.p_vix
d['p_quiet'] = (d.p_absret1 < 0.005).astype(float).where(d.p_absret1.notna())
d['l_vix'] = np.log(d.p_vix); d['l_rv10'] = np.log(d.p_rv10.clip(lower=1)); d['l_rv30'] = np.log(d.p_rv30.clip(lower=1))
d['l_dsince2'] = np.log1p(d.p_days_since_2pct); d['l_dsincehi'] = np.log1p(d.p_days_since_252hi)
# sanity: days since 2% at row t must only use rows < t
i = 1000; prev = np.where(big[:i])[0]; assert d.p_days_since_2pct.iloc[i] == i - prev[-1]; print('check4 days-since-2%-move at row 1000 uses only earlier rows: ok')
BASE = ['p_vix', 'p_vxn', 'p_ratio', 'p_vix_chg1', 'p_vix_chg5', 'p_vix_pct252', 'p_rv10', 'p_rv30', 'p_vrp', 'p_ret1', 'p_absret1', 'p_ret5', 'p_gap50', 'p_gap200', 'p_dd252']
EXTRA = ['p_rv_pct252', 'p_days_since_2pct', 'p_days_since_252hi', 'p_ret20', 'p_vxn_vix', 'dow', 'p_monday', 'p_quiet']
print('extras are built from returns/closes up to the prior close (days since 2%% move: rows before day t; days since 252d high: measured at t-1; day of week is the calendar day of t, known in advance).')
d['y_dn3'] = (d.z <= -3).astype(float).where(d.z.notna()); d['y_up3'] = (d.z >= 3).astype(float).where(d.z.notna()); d['y_ab3'] = (d.z.abs() >= 3).astype(float).where(d.z.notna())
d['y_dn25'] = (d.z <= -2.5).astype(float).where(d.z.notna()); d['y_up25'] = (d.z >= 2.5).astype(float).where(d.z.notna()); d['y_ab25'] = (d.z.abs() >= 2.5).astype(float).where(d.z.notna())
EV = ['y_dn3', 'y_up3', 'y_ab3', 'y_dn25', 'y_up25', 'y_ab25']
print('event counts (n days with z = %d):' % d.z.notna().sum())
ec = pd.DataFrame({e: {'total': int(d[e].sum()), '1999-2009': int(d[e][d.year <= 2009].sum()), '2010-2019': int(d[e][(d.year >= 2010) & (d.year <= 2019)].sum()), '2020-2026': int(d[e][d.year >= 2020].sum()),
                       'rate %': round(d[e].mean() * 100, 2)} for e in EV}); print(ec.to_string())
ERA3 = {'1999-2009': lambda x: x.year <= 2009, '2010-2019': lambda x: (x.year >= 2010) & (x.year <= 2019), '2020-2026': lambda x: x.year >= 2020}
for thr in ('3', '25'):
    print('\n--- single-signal AUC (raw AUC: >0.5 means a higher reading goes with the event; 0.5 = no information), threshold %s sigma ---' % ('3' if thr == '3' else '2.5'))
    rows = []
    for f in BASE + EXTRA:
        r = {'signal': f}
        for e in ('y_dn' + thr, 'y_up' + thr, 'y_ab' + thr): r['AUC ' + e[2:]] = auc(d[f], d[e])
        for era, fn in ERA3.items(): r['dn AUC ' + era] = auc(d[f][fn(d)], d['y_dn' + thr][fn(d)])
        r['n valid'] = int((d[f].notna() & d.z.notna()).sum()); rows.append(r)
    print(pd.DataFrame(rows).set_index('signal').round(3).to_string())
print('note: in-sample rankings, no fitting; with ~23 signals x 3 events some will stray from 0.5 by chance. Event counts above show how noisy small-era AUCs are (SE of an AUC with n events is roughly 0.29/sqrt(n)).')

def fit_logit(X, y, l2=1.0, it=60):
    w = np.zeros(X.shape[1])
    for _ in range(it):
        p = 1 / (1 + np.exp(-np.clip(X @ w, -30, 30))); W = p * (1 - p) + 1e-9
        step = np.linalg.solve(X.T @ (X * W[:, None]) + l2 * np.eye(X.shape[1]), X.T @ (y - p) - l2 * w); w = w + step
        if np.abs(step).max() < 1e-7: break
    return w
def walk(feats, ycol, start=2005):
    x = d[feats + ['year', ycol]].dropna(); pred = pd.Series(index=x.index, dtype=float)
    for yr in range(start, 2027):
        tr, te = x[x.year < yr], x[x.year == yr]
        if len(te) == 0 or tr[ycol].sum() < 5: continue
        mu, sd = tr[feats].mean(), tr[feats].std().replace(0, 1)
        Xtr = np.c_[np.ones(len(tr)), ((tr[feats] - mu) / sd).values]; Xte = np.c_[np.ones(len(te)), ((te[feats] - mu) / sd).values]
        w = fit_logit(Xtr, tr[ycol].values); pred[te.index] = 1 / (1 + np.exp(-np.clip(Xte @ w, -30, 30)))
    pred = pred.dropna(); return pred, x.loc[pred.index, ycol], x.loc[pred.index, 'year']
SETS = {'VIX only': ['l_vix'], 'rv10+rv30': ['l_rv10', 'l_rv30'], 'VIX+rv10+rv30': ['l_vix', 'l_rv10', 'l_rv30'],
        'WIDE (primary)': ['l_vix', 'l_rv10', 'l_rv30', 'p_vrp', 'p_vix_pct252', 'p_rv_pct252', 'l_dsince2', 'l_dsincehi', 'p_gap50', 'p_gap200', 'p_dd252', 'p_ret1', 'p_absret1', 'p_ret5', 'p_ret20',
                           'p_vix_chg1', 'p_vix_chg5', 'p_vxn_vix', 'p_quiet', 'p_monday']}
print('\nWIDE set features:', SETS['WIDE (primary)'], '(p_ratio / VIX3M left out: not available before Dec 2007)')
hdr('4b. walk-forward logistic (expanding window, refit each January, test next year; test years 2005-2026)')
results = {}
for ycol, lab in (('y_dn3', 'DOWN surprise z<=-3 (PRIMARY)'), ('y_dn25', 'DOWN z<=-2.5'), ('y_up3', 'UP z>=+3'), ('y_ab3', '|z|>=3'), ('y_ab25', '|z|>=2.5')):
    print('\n event:', lab)
    for nm, fs in SETS.items():
        p, y, yr = walk(fs, ycol); results[(ycol, nm)] = (p, y, yr)
        top = p >= p.quantile(.9); row = ['%-16s' % nm, 'OOS AUC %.3f' % auc(p, y)]
        for era, fn in (('05-09', lambda yy: yy <= 2009), ('10-19', lambda yy: (yy >= 2010) & (yy <= 2019)), ('20-26', lambda yy: yy >= 2020)):
            m = fn(yr); row.append('%s %.3f (ev %d)' % (era, auc(p[m], y[m]), int(y[m].sum())))
        row.append('top decile: n %d, events %d, hit %.1f%% vs base %.2f%%, capture %.1f%%' % (top.sum(), y[top].sum(), y[top].mean() * 100, y.mean() * 100, y[top].sum() / y.sum() * 100))
        print('  ' + ' | '.join(row))
print('\n per-year OOS AUC, WIDE model, DOWN z<=-3 (events in brackets):')
p, y, yr = results[('y_dn3', 'WIDE (primary)')]
print('  ' + ', '.join('%d: %s (%d)' % (k, ('%.2f' % auc(p[yr == k], y[yr == k])), int(y[yr == k].sum())) for k in sorted(yr.unique())))
hdr('4c. verdict against the pre-registered bar (pooled OOS AUC >= 0.60 AND >= 0.55 in each of 05-09, 10-19, 20-26)')
for ycol in ('y_dn3', 'y_dn25'):
    for nm in SETS:
        p, y, yr = results[(ycol, nm)]; a = auc(p, y); ers = [auc(p[m], y[m]) for m in ((yr <= 2009), (yr >= 2010) & (yr <= 2019), (yr >= 2020))]
        ok = a >= .60 and all(e >= .55 for e in ers)
        print('  %-8s %-16s pooled %.3f eras %s -> %s | beats 0.55 pooled: %s' % (ycol, nm, a, ['%.3f' % e for e in ers], 'PASSES' if ok else 'does not pass', a >= .55))
print('  (VIX-only / vol-only are references; the pre-registered model is WIDE on z<=-3.)')

# ---------------------------------------------------------------- 5. damage share
hdr('5. share of the damage: 2x holder (2*ret per day, no financing or fees), days with ret <= -2%')
def damage(x, label):
    x = x[x.z.notna()]; dd = x[x.ret <= -0.02]
    L1 = -2 * dd.ret; L2 = -np.log1p(2 * dd.ret)
    print('\n--- %s: %d down days of -2%% or worse (of %d days with z); total arithmetic loss %.3f (=%.1f%% of capital summed), log loss %.3f' % (label, len(dd), len(x), L1.sum(), L1.sum() * 100, L2.sum()))
    tests = (('prior VIX < 20', dd.p_vix < 20), ('prior VIX < 16', dd.p_vix < 16), ('z <= -3 (main)', dd.z <= -3), ('z_vix <= -3', dd.z_vix <= -3), ('z_ewma <= -3', dd.z_ewma <= -3),
             ('z <= -2', dd.z <= -2), ('VIX<20 AND z<=-3', (dd.p_vix < 20) & (dd.z <= -3)), ('VIX<20 OR z<=-3', (dd.p_vix < 20) | (dd.z <= -3)))
    for lab, m in tests:
        print('  %-20s days %3d (%4.1f%% of days)  arithmetic loss share %5.1f%%  log-loss share %5.1f%%  mean ret %6.2f%%' % (lab, m.sum(), m.mean() * 100, L1[m].sum() / L1.sum() * 100, L2[m].sum() / L2.sum() * 100, dd.ret[m].mean() * 100 if m.sum() else np.nan))
    print('  size of the whole 2x loss series against gross: this group sum -2*ret on these days vs all negative days: %.1f%% of gross arithmetic loss on all down days' % (L1.sum() / (-2 * x.ret[x.ret < 0]).sum() * 100))
for pn, xx in (('FULL', d), ('2010+', d10)):
    damage(xx, '%s, all states' % pn)
    damage(xx[xx.p_state.isin(['A', 'D'])], '%s, prior state A or D (stand-in for the levered states; D treated as ungated)' % pn)
    damage(xx[xx.p_state.isin(['E', 'F'])], '%s, prior state E or F (for contrast)' % pn)
print('\nnote: p_state is the strategy state at the prior close, used only as a label; no strategy harness is run and A/D days are all counted as 2x exposure, which overstates the exposure of D when its gate is applied.')

# ---------------------------------------------------------------- 6. after the surprise
hdr('6. after the surprise: forward QQQ return from the close of the event day')
for k in (1, 5, 20): d['f%d' % k] = d.close.shift(-k) / d.close - 1
def fwd_table(sel, label, base):
    rows = []
    for tag, m in (('all', lambda x: x.p_gap200.notna()), ('above 200d', lambda x: x.p_gap200 >= 0), ('below 200d', lambda x: x.p_gap200 < 0)):
        s, b = sel[m(sel)], base[m(base)]
        for grp, g in ((label, s), ('all days', b)):
            r = {'split': tag, 'group': grp, 'n': len(g)}
            for k in (1, 5, 20):
                v = g['f%d' % k].dropna(); r['n%d' % k] = len(v); r['mean%d %%' % k] = v.mean() * 100; r['med%d %%' % k] = v.median() * 100; r['pos%d %%' % k] = (v > 0).mean() * 100
            rows.append(r)
    t = pd.DataFrame(rows).round(2); print('\n--- %s (flag: split with n < 20 is not a conclusion; 5- and 20-day windows overlap and events cluster in time) ---' % label); print(t.to_string(index=False))
base = d[d.z.notna()]
fwd_table(sdn, 'surprise DOWN top100 (main z)', base); fwd_table(sup, 'surprise UP top100 (main z)', base)
print('\nclustering: distinct calendar years among surprise-down:', sdn.year.nunique(), ', surprise-up:', sup.year.nunique(), '; distinct 20-day-separated clusters (events more than 20 sessions apart start a new cluster): ', end='')
pos = {dt: i for i, dt in enumerate(d.index)}
def clusters(x):
    ii = sorted(pos[t] for t in x.index); c = 1
    for a, b in zip(ii[:-1], ii[1:]): c += (b - a > 20)
    return c
print('down %d, up %d' % (clusters(sdn), clusters(sup)))
print('\nrobustness: next-day only for z_vix and z_ewma lists:')
for nm, zc in (('z_vix', 'z_vix'), ('z_ewma', 'z_ewma')):
    a, b = lists(zc)
    print('  %s down top100: mean f1 %.2f%% f5 %.2f%% f20 %.2f%% | up top100: f1 %.2f%% f5 %.2f%% f20 %.2f%%' % (nm, a.f1.mean() * 100, a.f5.mean() * 100, a.f20.mean() * 100, b.f1.mean() * 100, b.f5.mean() * 100, b.f20.mean() * 100))
print('\nDONE')
