"""dashboard_figures.py -- the derived numbers the post-close dashboard update needs (2026-10-15).

Prints, for a recorded date: QQQ against its 50/100/150/200-day averages, the state
lines (D, E, D-gate, trim votes), the positions table (value, weight, unrealized
against Robinhood's average cost) at that date's closes, and (2026-10-22) the
cumulative-return card: the strategy's NAV index since its 1 Sep 2026 start against
QQQ and SPMO price over the same days, by month, plus the `const CUM = [...]` line
for the dashboard chart. Read-only: it writes nothing, so the post-close run can
call it without editing any file.

    python3 paper-track/dashboard_figures.py <date> SYM=qty@avg_cost [SYM=qty@avg_cost ...]
    e.g.  python3 paper-track/dashboard_figures.py 2026-10-15 SPMO=891.04937@151.34 TQQQ=4980.664967@76.86
"""
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLOSES = os.path.join(ROOT, 'data', 'live_closes.csv')
NAV = os.path.join(ROOT, 'data', 'live_nav_index.csv')


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
    cumulative(date, rows)
    return 0


def cumulative(date, rows):
    """Strategy NAV index (cash-flow-blind, from 1 Sep 2026; base = the prior close) vs
    QQQ and SPMO price return over the same sessions."""
    nav = [r for r in csv.DictReader(open(NAV)) if r['date'] <= date]
    if not nav:
        return
    px = {r['date']: r for r in rows}
    days = [r['date'] for r in rows]
    base = days[days.index(nav[0]['date']) - 1]          # the close before the first NAV row
    pts = [(base, 1.0)] + [(r['date'], float(r['index_value'])) for r in nav]
    def rel(sym, d):
        return float(px[d][sym]) / float(px[base][sym]) - 1
    out = [(d, v - 1, rel('QQQ', d), rel('SPMO', d)) for d, v in pts if d in px]
    d, s_, q_, m_ = out[-1]
    peak = max(v for _, v in pts)
    print(f'cumulative since {base} close (strategy NAV index, cash-flow-blind; QQQ/SPMO price):')
    print(f'  strategy {s_:+.2%}  QQQ {q_:+.2%}  SPMO {m_:+.2%}  (strategy vs QQQ {s_ - q_:+.2%}); '
          f'NAV {pts[-1][1]:.4f}, {pts[-1][1] / peak - 1:+.2%} vs its high {peak:.4f}')
    months = sorted({x[0][:7] for x in out[1:]})
    for mo in months:
        first = max(x for x in out if x[0][:7] < mo)        # last point before the month
        last = max(x for x in out if x[0][:7] == mo)
        f = lambda i: (1 + last[i]) / (1 + first[i]) - 1
        print(f'  {mo}: strategy {f(1):+.2%}  QQQ {f(2):+.2%}  SPMO {f(3):+.2%}')
    print('  const CUM = [' + ','.join(f'["{a}",{b * 100:.2f},{c * 100:.2f},{e * 100:.2f}]' for a, b, c, e in out) + '];')


if __name__ == '__main__':
    sys.exit(main(sys.argv))
