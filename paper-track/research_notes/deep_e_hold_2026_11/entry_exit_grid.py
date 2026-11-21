import json
import os, sys, warnings
import numpy as np
HERE = "/home/user/Robinhood-stock/paper-track"; sys.path.insert(0, HERE)
DATA = "/home/user/Robinhood-stock/data"; MAX_FILL = 3
import vol_curve as VC
_orig_history = VC.history
_LC_DATES = sorted(l.split(',', 1)[0] for l in open(os.path.join(DATA, 'live_closes.csv')).read().splitlines()[1:] if l)
FILLED = {}


def _history(sym):
    h, src = _orig_history(sym)
    h = dict(h)
    missing = [d for d in _LC_DATES if d > max(h)]
    if len(missing) > MAX_FILL:
        raise RuntimeError(f'{sym} history ends {max(h)}; {len(missing)} later sessions (> {MAX_FILL}): refresh the data')
    key = 'vix' if sym == 'VIX' else 'vix3m'
    for d in missing:
        f = os.path.join(DATA, 'runs', f'{d}.json')
        v = json.load(open(f)).get('vixm', {}).get(key) if os.path.exists(f) else None
        if v is None:
            raise RuntimeError(f'{sym}: no FRED level and no live run reading for {d}')
        h[d] = float(v)
        FILLED.setdefault(d, {})[sym] = float(v)
    return h, src


VC.history = _history

# The research harness extends the real-panel price files from data/live_closes.csv, but not xlu_long_history.csv, which bounds
# the proxy panel; when live_closes is ahead of the Yahoo files (the usual case at 16:10) the two panels end on different
# days and the run fails. Extend xlu_long_history.csv from the same live XLU closes the real panel already uses.
import csv
import monte_carlo as MC
_orig_load = MC._load
_LC = list(csv.DictReader(open(os.path.join(DATA, 'live_closes.csv'))))


def _load(name, dcol='d', ccol='c'):
    out = _orig_load(name, dcol, ccol)
    if name == 'xlu_long_history.csv':
        last = max(out)
        for row in _LC:
            if row['date'] > last and row.get('XLU'):
                out[row['date']] = float(row['XLU'])
    return out


MC._load = _load
warnings.simplefilter('ignore')
import harness_live as HL
import inspect
S = HL.S
src = inspect.getsource(HL.build)
i0 = src.index("    g_deep = "); i1 = src.index("    deep = on.astype(float)")
new = """    gap = np.nan_to_num(sg['gaps'][200][0], nan=9.0)
    on = np.zeros(len(eff), bool); st = False
    for i in range(len(eff)):
        if st: st = gap[i] <= EXIT
        else:  st = (eff[i] == 4) and gap[i] <= ENTRY
        on[i] = st
"""
exec(compile(src[:i0] + new + src[i1:], 'b', 'exec'), HL.__dict__)
import json
D = '/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad/deepe'
res = {}
ens = (-0.04, -0.05, -0.06, -0.07, -0.08); exs = (-0.08, -0.07, -0.06, -0.05, -0.04, -0.03, -0.02, -0.01, 0.0)
for track in ('real', 'proxy'):
    for en in ens:
        for ex in exs:
            if ex < en: continue
            HL.__dict__['ENTRY'] = en; HL.__dict__['EXIT'] = ex
            r, ds, t = HL.run_live(track, vixy_source='old'); r = np.asarray(r, float); ds = [str(d) for d in ds]
            s = HL.stats(r); m = np.array([not d.startswith('2020') for d in ds]); s2 = HL.stats(r[m])
            res[f'{track} {en} {ex}'] = (s['c'], s['sh'], s['m'], s2['c'], s2['sh'])
json.dump(res, open(D + '/grid.json', 'w'))
for k, nm in ((1, 'Sharpe'), (0, 'CAGR %'), (2, 'max DD %'), (4, 'Sharpe ex-2020')):
    for track in ('real', 'proxy'):
        print(f'{nm} ({track}) rows=entry, cols=exit ' + ' '.join(f'{x*100:6.0f}' for x in exs))
        for en in ens:
            cells = []
            for ex in exs:
                v = res.get(f'{track} {en} {ex}')
                cells.append('     .' if v is None else (f'{v[k]:6.3f}' if k in (1, 4) else f'{v[k]*100:6.1f}'))
            print(f'   {en*100:+.0f}%            ' + ' '.join(cells))
