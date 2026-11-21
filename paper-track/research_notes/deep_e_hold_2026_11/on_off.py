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
import harness as H
S = HL.S
def go(track, share):
    S.DEEP_E_CASH_SHARE = share
    r, ds, tpy = HL.run_live(track, vixy_source='old')
    return np.asarray(r, float), [str(d) for d in ds], tpy
out = {}
for track in ('real', 'proxy'):
    for share in (0.50, 0.0):
        out[(track, share)] = go(track, share)
S.DEEP_E_CASH_SHARE = 0.50
for track in ('real', 'proxy'):
    (r1, ds, t1), (r0, _, t0) = out[(track, 0.5)], out[(track, 0.0)]
    s1, s0 = HL.stats(r1), HL.stats(r0)
    print(f'== {track} {ds[0]}..{ds[-1]}')
    for nm, s, t in (('deep-E on ', s1, t1), ('deep-E off', s0, t0)):
        print(f"  {nm} CAGR {s['c']*100:6.1f}%  Sharpe {s['sh']:.2f}  maxDD {s['m']*100:6.1f}%  vol {s['v']*100:5.1f}%  trades/yr {t:.0f}")
    yrs = sorted({d[:4] for d in ds})
    row = []
    for y in yrs:
        m = np.array([d.startswith(y) for d in ds])
        a, b = np.prod(1 + r1[m]) - 1, np.prod(1 + r0[m]) - 1
        if abs(a - b) > 0.0005: row.append(f'{y}: {a*100:+.1f} vs {b*100:+.1f} ({(a-b)*100:+.1f})')
    print('  years where it differs (on vs off, diff pts):'); [print('   ', x) for x in row]
