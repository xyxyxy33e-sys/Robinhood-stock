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

HERE = os.path.dirname(os.path.abspath(__file__))
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

r, ds, tpy = HL.run_live('real', vixy_source='old')
ds = [str(d) for d in ds]
r = np.asarray(r, dtype=float)
last = ds[-1]
cur = int(last[:4])
items = []
for y in range(FIRST_YEAR, cur + 1):
    m = np.array([d.startswith(str(y)) for d in ds])
    v = float(np.prod(1 + r[m]) - 1)
    label = ("'%02d YTD" % (y % 100)) if y == cur else str(y)
    items.append('{y:%s,v:%.4f}' % (json.dumps(label), v))
st = HL.stats(r)            # same CAGR / Sharpe / max drawdown as every harness_live figure on record
cagr, sharpe, mdd = st['c'], st['sh'], st['m']
asof = f're-run daily by the post-close run with prices to the {int(last[8:]):d} {["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][int(last[5:7]) - 1]} {last[:4]} close'
if FILLED:
    asof += ' (VIX/VIX3M for ' + ', '.join(sorted(FILLED)) + ' from the live 15:50 reading until FRED posts the close)'
print('YEARS const years = [' + ','.join(items) + '];')
print('ASOF ' + asof)
print(f'FULL Full period Nov 2015&ndash;{int(last[8:])} {["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][int(last[5:7]) - 1]} {last[:4]}: '
      f'<b>{cagr * 100:.1f}% CAGR, Sharpe {sharpe:.2f}, max drawdown &minus;{abs(mdd) * 100:.1f}%</b>')
