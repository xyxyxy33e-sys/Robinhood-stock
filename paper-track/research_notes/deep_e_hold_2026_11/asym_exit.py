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
import inspect
S = HL.S
src = inspect.getsource(HL.build)
i0 = src.index("    g_deep = "); i1 = src.index("    deep = on.astype(float)")
new = """    gap = np.nan_to_num(sg['gaps'][200][0], nan=9.0)
    on = np.zeros(len(eff), bool); st = False
    for i in range(len(eff)):
        if st: st = gap[i] <= EXIT
        else:  st = (eff[i] == 4) and gap[i] <= S.DEEP_E_GAP200
        on[i] = st
"""
exec(compile(src[:i0] + new + src[i1:], 'b', 'exec'), HL.__dict__)
for track in ('real', 'proxy'):
    print('==', track)
    base = None
    for ex in (-0.05, -0.04, -0.03, -0.02, -0.01, 0.0, 0.02):
        HL.__dict__['EXIT'] = ex
        r, ds, t = HL.run_live(track, vixy_source='old'); r = np.asarray(r, float); s = HL.stats(r)
        ds = [str(d) for d in ds]
        if base is None: base = r
        m20 = np.array([not d.startswith('2020') for d in ds])
        s2 = HL.stats(r[m20]); b2 = HL.stats(base[m20])
        print(f"  exit at gap > {ex*100:+.0f}%: CAGR {s['c']*100:5.1f}%  Sharpe {s['sh']:.3f}  maxDD {s['m']*100:6.1f}%  "
              f"| ex-2020 CAGR {s2['c']*100:5.1f}% ({(s2['c']-b2['c'])*100:+.2f} vs -5%)  trades/yr {t:.0f}")
