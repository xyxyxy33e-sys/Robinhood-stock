import json, os, sys, warnings
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
import inspect, harness as H
S = HL.S
src = inspect.getsource(HL.build)
old = "    deep = ((eff == 4) & (np.nan_to_num(sg['gaps'][200][0]) <= S.DEEP_E_GAP200)).astype(float) * S.DEEP_E_CASH_SHARE\n"
assert src.count(old) == 1
new = """    _g = np.nan_to_num(sg['gaps'][200][0]) <= S.DEEP_E_GAP200
    if VARIANT == 'live': _on = (eff == 4) & _g
    elif VARIANT == 'deepF': _on = ((eff == 4) | (eff == 5)) & _g
    elif VARIANT == 'hold':
        _on = np.zeros(len(eff), bool); st = False
        for i in range(len(eff)):
            st = bool(_g[i]) and (st or eff[i] == 4); _on[i] = st
    deep = _on.astype(float) * S.DEEP_E_CASH_SHARE
"""
ns = HL.__dict__
exec(compile(src.replace(old, new), 'build_variant', 'exec'), ns)
res = {}
for track in ('real', 'proxy'):
    for v in ('live', 'hold', 'deepF'):
        ns['VARIANT'] = v
        r, ds, tpy = HL.run_live(track, vixy_source='old'); res[(track, v)] = (np.asarray(r, float), [str(d) for d in ds], tpy)
for track in ('real', 'proxy'):
    print('==', track, res[(track, 'live')][1][0], '..', res[(track, 'live')][1][-1])
    for v, nm in (('live', 'live (sell at F)'), ('hold', 'hold through F'), ('deepF', 'also enter in F')):
        r, ds, t = res[(track, v)]; s = HL.stats(r)
        print(f"  {nm:17s} CAGR {s['c']*100:5.1f}%  Sharpe {s['sh']:.2f}  maxDD {s['m']*100:6.1f}%  vol {s['v']*100:4.1f}%  trades/yr {t:.0f}")
    r0, ds, _ = res[(track, 'live')]
    for v in ('hold', 'deepF'):
        r1 = res[(track, v)][0]; out = []
        for y in sorted({d[:4] for d in ds}):
            m = np.array([d.startswith(y) for d in ds]); a, b = np.prod(1 + r1[m]) - 1, np.prod(1 + r0[m]) - 1
            if abs(a - b) > 0.001: out.append(f'{y} {(a-b)*100:+.1f}')
        print(f'   {v} vs live, pts by year:', ', '.join(out))
