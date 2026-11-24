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
import monte_carlo as MC2
S = HL.S; H = HL.H

def stat_row(r, ds, track):
    st = HL.stats(r, HL.cash_for(ds, track == 'real')) if False else HL.stats(r)
    return st

def ex2020(r, ds):
    m = np.array([not str(d).startswith('2020') for d in ds])
    x = np.asarray(r)[m]
    return float(x.mean() / x.std(ddof=1) * np.sqrt(252))

def run(track, **kw):
    d = HL.run_live_detail(track, vixy_source='old', **kw)
    r = np.asarray(d['r'], float); ds = [str(x) for x in d['ds']]
    st = HL.stats(r)
    b = HL.build(track, vixy_source='old')
    key = b['key'][d['s0']:d['e']]
    return dict(r=r, ds=ds, st=st, tpy=d['tpy'], sh_x20=ex2020(r, ds), d=d, b=b, key=key)

def decode(key):
    key = np.asarray(key, np.int64)
    return dict(eff=(key // 1000) % 10, held=(key // 100) % 10, gate=(key // 10) % 10, zone=key % 10,
                vixy=(key // 100000) % 10, deep=(key // 10**6) % 10, panic=(key // 10**7) % 10)

def spells(x):
    """runs of constant value of x: list of (value, start, length)"""
    x = np.asarray(x); idx = np.flatnonzero(np.r_[True, x[1:] != x[:-1]]); ends = np.r_[idx[1:], len(x)]
    return [(x[i], i, e - i) for i, e in zip(idx, ends)]

def chop_stats(x, binary=False):
    """flips, runs (binary: on-spells), short (<=3 sessions, interior i.e. bounded both sides), re-flips back within 5."""
    x = np.asarray(x); sp = spells(x)
    flips = len(sp) - 1
    if binary:
        runs = [(v, s, L) for k, (v, s, L) in enumerate(sp) if v]
        inter = [(k, (v, s, L)) for k, (v, s, L) in enumerate(sp) if v and 0 < k < len(sp) - 1]
        nsp = len(runs); short = sum(1 for k, (v, s, L) in inter if L <= 3)
        # re-flip: an on-spell followed by off gap <=5 then on again (off blip) plus on-spell off... count both blip types
        refl = 0
        for k in range(1, len(sp) - 1):
            if sp[k][2] <= 5 and sp[k - 1][0] == sp[k + 1][0]: refl += 1
        base = nsp; elig = len(inter)
    else:
        nsp = len(sp); inter = [(k, s) for k, s in enumerate(sp) if 0 < k < len(sp) - 1]
        short = sum(1 for k, (v, s, L) in inter if L <= 3); elig = len(inter)
        refl = sum(1 for k in range(1, len(sp) - 1) if sp[k][2] <= 5 and sp[k - 1][0] == sp[k + 1][0])
    return dict(flips=flips, spells=nsp, short=short, elig=elig, refl=refl)

def attribute(b, s0, e, band=S.REBALANCE_DRIFT_BAND, stubs=True):
    """replicates MC.run_strategy's rebalance decision; returns per-session bool arrays for each cause"""
    W, key = b['W'], b['key']; t0 = s0
    h = W[t0].copy(); n = e - s0
    out = {k: np.zeros(n, bool) for k in ('reb', 'drift_only', 'any_key')}
    comp = decode(key); chg = {k: np.zeros(n, bool) for k in comp}
    for t in range(t0, e):
        if t > t0:
            tgt = W[t]; drift = np.abs(tgt - h).sum()
            stub = bool(((tgt == 0) & (h > S.ZERO_LEG_EPS)).any())
            kc = key[t] != key[t - 1]
            reb = kc or drift > band or stub
            i = t - t0
            if reb:
                out['reb'][i] = True
                if kc:
                    out['any_key'][i] = True
                    for k, v in comp.items():
                        if v[t] != v[t - 1]: chg[k][i] = True
                else: out['drift_only'][i] = True
                h = tgt.copy()
        r = b['L'][t + 1]; g = (h * r).sum(); h = h * (1 + r) / (1 + g)
    out['chg'] = chg
    return out
