"""dashboard_figures.py -- the derived numbers the post-close dashboard update needs (2026-10-15).

Prints, for a recorded date: QQQ against its 50/100/150/200-day averages, the state
lines (D, E, D-gate, trim votes), and the positions table (value, weight, unrealized
against Robinhood's average cost) at that date's closes. Read-only: it writes
nothing, so the post-close run can call it without editing any file.

    python3 paper-track/dashboard_figures.py <date> SYM=qty@avg_cost [SYM=qty@avg_cost ...]
    e.g.  python3 paper-track/dashboard_figures.py 2026-10-15 SPMO=891.04937@151.34 TQQQ=4980.664967@76.86
"""
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLOSES = os.path.join(ROOT, 'data', 'live_closes.csv')


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    date = argv[1]
    rows = [r for r in csv.DictReader(open(CLOSES)) if r['date'] <= date and r['QQQ']]
    if not rows or rows[-1]['date'] != date:
        print(f'no QQQ close for {date} in data/live_closes.csv')
        return 1
    q = [float(r['QQQ']) for r in rows]
    c = q[-1]

    def sma(n):
        return sum(q[-n:]) / n
    print(f'QQQ close {c:.2f}')
    for n in (50, 100, 150, 200):
        print(f'  {n}d {sma(n):.2f}  ({c / sma(n) - 1:+.2%})')
    print(f'lines: D below ~{sma(50) * 0.99:.0f} | E below ~{sma(200) * 0.99:.0f} | D gate below ~{sma(200) * 1.02:.0f}'
          f' | trim votes at ~{sma(100) * 1.10:.0f} / ~{sma(150) * 1.12:.0f} / ~{sma(200) * 1.15:.0f}')
    last = rows[-1]
    pos = []
    for a in argv[2:]:
        sym, rest = a.split('=')
        qty, avg = rest.split('@')
        px = float(last[sym])
        pos.append((sym, float(qty), float(avg), px))
    if pos:
        tot = sum(q_ * px for _, q_, _, px in pos)
        un = 0.0
        for sym, q_, avg, px in pos:
            v, u = q_ * px, (px - avg) * q_
            un += u
            print(f'{sym:5} {q_:,.4f} sh  avg {avg:.2f}  px {px:.2f}  value {v:,.2f}  weight {v / tot:.2%}  '
                  f'unrealized {u:+,.2f} ({px / avg - 1:+.2%})')
        print(f'total {tot:,.2f}  unrealized {un:+,.2f}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
