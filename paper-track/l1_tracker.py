"""Check of the D gate read on the day's high ("L1", live 2026-11-11..16, switched off 2026-11-17 and followed on paper).

The backtest of L1 used full-day highs, which include 15:50-16:00 and so flatter it. The live
run reads only the high up to the 15:50 run (data/qqq_highs.csv), so every live L1 day is free
of that look-ahead. This script lists the sessions where L1 changed the gate (open on the day
high while the 15:50 price alone would have kept it shut) and what QQQ and the book's risky
legs did afterwards, so the rule can be judged on live data.

    python3 paper-track/l1_tracker.py

Read-only: it reads data/runs/*.json and data/live_closes.csv and writes nothing.
"""
import csv
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import state as S  # noqa: E402

LEG_LEV = {'SPMO': 1.0, 'TQQQ': 3.0, 'QLD': 2.0}
LEGS7 = ('SPMO', 'TQQQ', 'QLD', 'XLU', 'VIXY', 'QQQ', 'BOXX')


def closes():
    out = {}
    with open(os.path.join(ROOT, 'data', 'live_closes.csv')) as f:
        for row in csv.DictReader(f):
            d = row.get('date') or row.get('d')
            out[d] = {k: float(v) for k, v in row.items() if k not in ('date', 'd') and v not in ('', None)}
    return out


def main():
    runs = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'data', 'runs', '20*.json'))):
        try:
            j = json.load(open(p))
        except (ValueError, OSError):
            continue
        r = j.get('reading') or {}
        if j.get('date', '') < S.DGATE_HIGH_FROM_SESSION or r.get('state') != 'D':
            continue
        runs.append(j)
    c = closes()
    days = sorted(c)
    rows = []
    for j in runs:
        r, d = j['reading'], j['date']
        g_close = (r.get('gaps') or {}).get('200', (r.get('gaps') or {}).get(200))
        px = float(j['quotes']['QQQ']['last'])
        hi = r.get('qqq_high')
        if g_close is None or hi is None:
            continue
        # Paper L1 (switched off live on 2026-11-17): recompute the high-based gap from the
        # logged high, whatever the live switch was, so the rule is followed on paper.
        sma = px / (1.0 + g_close)
        g_gate = max(g_close, float(hi) / sma - 1.0)
        close_gate = S.d_gate_active('D', r.get('breadth_pct'), g_close)
        l1_gate = S.d_gate_active('D', r.get('breadth_pct'), g_gate)
        if close_gate == l1_gate:
            continue                       # L1 would not have changed the decision
        tgt = dict(zip(LEGS7, j.get('target') or []))
        lev = sum(tgt.get(k, 0.0) * v for k, v in LEG_LEV.items())
        fwd = {}
        if d in days:
            i = days.index(d)
            for n in (1, 5, 20):
                if i + n < len(days) and 'QQQ' in c[days[i + n]]:
                    fwd[n] = c[days[i + n]]['QQQ'] / px - 1
        rows.append((d, px, hi, g_close, g_gate, lev, fwd))
    print(f"L1 days (gate would open on the day high, shut on the 15:50 price alone; live until 2026-11-16, paper since): {len(rows)}")
    print(f"{'date':<11}{'QQQ 15:50':>10}{'high':>9}{'gap close':>10}{'gap high':>9}{'live x':>8}"
          f"{'QQQ +1d':>9}{'+5d':>8}{'+20d':>8}{'book est +5d':>13}")
    for d, px, hi, gc, gg, lev, fwd in rows:
        f = lambda n: f"{fwd[n]*100:+.2f}%" if n in fwd else '   n/a'
        est = f"{fwd[5]*lev*100:+.2f}%" if 5 in fwd else '   n/a'
        print(f"{d:<11}{px:>10.2f}{(hi or 0):>9.2f}{gc*100:>9.2f}%{gg*100:>8.2f}%{lev:>8.2f}"
              f"{f(1):>9}{f(5):>8}{f(20):>8}{est:>13}")
    print("live x = the risky exposure the live book held (0 on paper days after 2026-11-16, when the gate stayed shut); book est = live x times the QQQ move, a rough guide, not the NAV (leveraged-ETF decay and the "
          "gate closing again within the window are ignored).")


if __name__ == '__main__':
    main()
