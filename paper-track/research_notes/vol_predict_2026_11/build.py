"""Research only (2026-11-17, owner question): can big QQQ days be seen coming from the day before?

Builds one table: every QQQ session 1999-09..2026-11-16 with its close-to-close return and the
signals known at the PRIOR close (VIX, VIX3M, VXN, realized vol, trend, strategy state).
Writes days.csv, top100_up.csv, top100_down.csv next to this file.

    python3 paper-track/research_notes/vol_predict_2026_11/build.py
"""
import csv, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, 'paper-track'))
import state as S  # noqa: E402

def fred(name):
    s = pd.read_csv(os.path.join(HERE, name + '.csv'), index_col=0).iloc[:, 0]
    return pd.to_numeric(s, errors='coerce').dropna()

q = pd.read_csv(os.path.join(ROOT, 'data', 'qqq_ohlc.csv'), index_col=0)['c']
live = pd.read_csv(os.path.join(ROOT, 'data', 'live_closes.csv'), index_col=0)['QQQ']
q = pd.concat([q, live[live.index > q.index[-1]]]).astype(float)
vix, v3m, vxn = fred('VIXCLS'), fred('VXVCLS'), fred('VXNCLS')

df = pd.DataFrame({'close': q})
df['ret'] = df.close.pct_change()
lr = np.log(df.close).diff()
for name, s in (('vix', vix), ('vix3m', v3m), ('vxn', vxn)):
    df[name] = s.reindex(df.index).ffill(limit=3)
df['vix_chg1'] = df.vix.pct_change()
df['vix_chg5'] = df.vix.pct_change(5)
df['ratio'] = df.vix / df.vix3m
df['vix_pct252'] = df.vix.rolling(252).rank(pct=True)
df['rv10'] = lr.rolling(10).std() * np.sqrt(252) * 100
df['rv30'] = lr.rolling(30).std() * np.sqrt(252) * 100
df['vrp'] = df.vix - df.rv30
df['ret1'] = df.ret
df['absret1'] = df.ret.abs()
df['ret5'] = df.close.pct_change(5)
df['gap50'] = df.close / df.close.rolling(50).mean() - 1
df['gap200'] = df.close / df.close.rolling(200).mean() - 1
df['dd252'] = df.close / df.close.rolling(252, min_periods=60).max() - 1
dates = list(df.index); px = list(df.close)
df['state'] = S.compute_states(dates, dict(zip(dates, px)))
df.loc[df.index[:200], 'state'] = None      # warm-up
feat = ['vix', 'vix3m', 'vxn', 'vix_chg1', 'vix_chg5', 'ratio', 'vix_pct252', 'rv10', 'rv30', 'vrp',
        'ret1', 'absret1', 'ret5', 'gap50', 'gap200', 'dd252', 'state']
out = df[['close', 'ret']].copy()
for f in feat:
    out['p_' + f] = df[f].shift(1)          # known at the prior close
out = out.dropna(subset=['ret'])
out.index.name = 'date'
out.to_csv(os.path.join(HERE, 'days.csv'), float_format='%.6f')
cols = ['ret', 'close', 'p_vix', 'p_vix_chg1', 'p_ratio', 'p_vxn', 'p_rv10', 'p_rv30', 'p_ret1', 'p_gap200', 'p_dd252', 'p_state']
up = out.sort_values('ret', ascending=False).head(100)[cols]; up.insert(0, 'rank', range(1, 101))
dn = out.sort_values('ret').head(100)[cols]; dn.insert(0, 'rank', range(1, 101))
up.to_csv(os.path.join(HERE, 'top100_up.csv'), float_format='%.6f')
dn.to_csv(os.path.join(HERE, 'top100_down.csv'), float_format='%.6f')
print(len(out), out.index[0], out.index[-1])
print('up threshold', up.ret.min(), 'down threshold', dn.ret.max())
print(out.tail(3).T)
