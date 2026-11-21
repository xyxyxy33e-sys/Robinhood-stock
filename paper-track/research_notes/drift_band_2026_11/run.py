"""Yearly bars for the dashboard card "Design of 11 Nov ... real instruments by year, daily" (owner 2026-11-20: update daily).

    python3 paper-track/dashboard_years.py

Runs the live design on real instruments (harness_live.run_live('real'), the research harness the bars always came from)
through the latest session in data/live_closes.csv, and prints three lines to paste into the dashboard:
  YEARS   the whole `const years = [...];` line of the page script (2022 .. current year YTD)
  ASOF    the inner text of <span id="yr-asof">
  FULL    the inner text of <span id="yr-full">

VIX / VIX3M: FRED posts a session's close the next morning, so at the 16:10 post-close run the newest session (sometimes
two) has no FRED level and the harness refuses to run. For those trailing sessions only (at most MAX_FILL), this script
supplies the VIX / VIX3M that the live 15:50 run itself used (data/runs/<date>.json, vixm.vix / vixm.vix3m) and says
so in ASOF. Anything older than that still raises. The next run picks up the FRED closes automatically.
Research only: reads data/, writes nothing.
"""
import json, os, sys, warnings
import numpy as np

HERE = "/home/user/Robinhood-stock/paper-track"
sys.path.insert(0, HERE)
DATA = os.path.join(os.path.dirname(HERE), 'data')
MAX_FILL = 3
FIRST_YEAR = 2022

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
MC = HL.MC
d0 = MC.run_strategy.__defaults__
for track in ('real', 'proxy'):
    print('==', track)
    for cost in (None, 0.0005):
        for band in (0.02, 0.03, 0.04, 0.05, 0.07):
            MC.run_strategy.__defaults__ = (band,) + d0[1:]
            r, ds, t = HL.run_live(track, vixy_source='old', cost=cost); r = np.asarray(r, float); ds = [str(d) for d in ds]
            s = HL.stats(r); m = np.array([not d.startswith('2020') for d in ds]); s2 = HL.stats(r[m])
            print(f"  cost {'2bp' if cost is None else '5bp'} band {band*100:.0f}%: CAGR {s['c']*100:5.1f}%  Sharpe {s['sh']:.3f}  maxDD {s['m']*100:6.1f}%  trades/yr {t:4.0f} | ex-2020 Sharpe {s2['sh']:.3f}")
    MC.run_strategy.__defaults__ = d0
