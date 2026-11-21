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
src = inspect.getsource(HL.build)
old = "        x = np.minimum(cash * sh, cash - used); used = used + x\n"
assert old in src
new = "        _f = MD if j == 0 else MP\n        if _f is not None: sh = sh * _f(sg['vol'][0])\n" + old
exec(compile(src.replace(old, new), 'b', 'exec'), HL.__dict__)

def mk(fn):
    def f(vol):
        v = np.asarray(vol, float); m = np.ones_like(v); ok = np.isfinite(v) & (v > 0)
        m[ok] = fn(v[ok]); return m
    return f
full = mk(lambda v: np.minimum(1, .20 / v))
sq = mk(lambda v: np.minimum(1, .20 / v) ** .5)
fl = mk(lambda v: np.maximum(.5, np.minimum(1, .20 / v)))
t30 = mk(lambda v: np.minimum(1, .30 / v))
V = {'1 baseline': (None, None), '2 both full(20%)': (full, full), '3 deepE only': (full, None),
     '4 panic only': (None, full), '5 both sqrt': (sq, sq), '6 both floor.5': (fl, fl), '8 both 30%tgt': (t30, t30)}
for track in ('real', 'proxy'):
    print('=====', track); base = None; bds = None
    for name, (fd, fp) in V.items():
        HL.__dict__['MD'] = fd; HL.__dict__['MP'] = fp
        r, ds, t = HL.run_live(track, vixy_source='old'); r = np.asarray(r, float); ds = [str(d) for d in ds]
        s = HL.stats(r); m20 = np.array([not d.startswith('2020') for d in ds]); s2 = HL.stats(r[m20])
        yr = {}
        for y in sorted(set(d[:4] for d in ds)):
            k = np.array([d.startswith(y) for d in ds]); yr[y] = float(np.prod(1 + r[k]) - 1)
        if base is None: base = yr
        print(f"{name:18s} CAGR {s['c']*100:5.1f} Sh {s['sh']:.3f} maxDD {s['m']*100:6.1f} vol {s['v']*100:5.1f} tr/yr {t:5.1f} | ex2020 CAGR {s2['c']*100:5.1f} Sh {s2['sh']:.3f}")
        if name != '1 baseline':
            dif = {y: (yr[y] - base[y]) * 100 for y in yr}
            print('    yrs>0.5pt:', ' '.join(f"{y}:{v:+.1f}" for y, v in dif.items() if abs(v) > .5))
            print('    key:', ' '.join(f"{y}:{dif.get(y, float('nan')):+.1f}" for y in YRS) if (YRS := ['2008','2020','2022','2026']) else '')
        else:
            print('    key yrs base:', ' '.join(f"{y}:{yr.get(y, float('nan'))*100:+.1f}" for y in ['2008','2020','2022','2026']))
