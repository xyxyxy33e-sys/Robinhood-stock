"""List every state-F episode over the full QQQ history: when it started, how
long it lasted, what QQQ did, and the worst drawdown INSIDE the episode.

WHY THE WARM-UP MATTERS. compute_states() returns 'F' as a placeholder for
every date before the 200-day SMA exists (`if m200 is None: out.append('F')`).
On data starting 1999-09-15 that fabricates a single 199-day "episode" running
to 2000-06-27 in which QQQ rose 51% -- the longest and most positive entry in
the list, entirely an artifact. This script therefore keeps only dates where
sma(v, i, 200) is not None. The backtests were never exposed to this
(long_history_backtest.START = '2000-07-01' exists precisely to skip it), but
any ad-hoc state tally on this data set must drop the warm-up explicitly.

WHY THE TOTAL DIFFERS FROM STRATEGY.md's -39.4%. That figure is WEEKLY-sampled
(last trading day of each ISO week, 197 weeks / 28 episodes), matching the
weekly backtest cadence used elsewhere in the project. This script samples
DAILY, which resolves entries and exits the weekly grid blurs and does not
merge episodes separated by only a few days -- hence 39 episodes and -83.1%.
Both are correct for what they measure; daily is the more faithful description
of what the classifier actually does, weekly of what a weekly rebalance
captures. Neither is the strategy's own return: state F now holds 100% cash,
so these are the losses the strategy AVOIDS, not ones it takes.
"""
import csv
import statistics
import sys
from datetime import date

sys.path.insert(0, 'paper-track')
from state import compute_states, sma

QQQ = 'data/qqq_long_history.csv'


def load():
    px = {}
    for r in csv.DictReader(open(QQQ)):
        px[r['d']] = float(r['c'])
    return px


def episodes(px, target='F'):
    """(start, end, i0, i1) per contiguous run of `target`, warm-up excluded."""
    ds = sorted(px)
    v = [px[d] for d in ds]
    sts = compute_states(ds, px)
    valid = [(d, s) for i, (d, s) in enumerate(zip(ds, sts))
             if sma(v, i, 200) is not None]      # drop the 200dma warm-up
    eps, cur = [], None
    for i, (d, s) in enumerate(valid):
        if s == target:
            cur = [d, d, i, i] if cur is None else [cur[0], d, cur[2], i]
        elif cur:
            eps.append(cur)
            cur = None
    if cur:
        eps.append(cur)
    return eps, valid


def main():
    px = load()
    eps, valid = episodes(px)
    print(f"{'#':>3}  {'start':<12}{'end':<12}{'tdays':>6}{'weeks':>7}{'QQQ':>9}"
          f"{'  worst DD in F':>16}")
    for n, (a, b, i0, i1) in enumerate(eps, 1):
        td = i1 - i0 + 1
        wk = (date.fromisoformat(b) - date.fromisoformat(a)).days / 7
        seg = [px[d] for d, _ in valid[i0:i1 + 1]]
        pk, mdd = seg[0], 0.0
        for x in seg:
            pk = max(pk, x)
            mdd = min(mdd, x / pk - 1)
        print(f"{n:>3}  {a:<12}{b:<12}{td:>6}{wk:>7.1f}"
              f"{(px[b]/px[a]-1)*100:>8.1f}%{mdd*100:>15.1f}%")

    L = sorted(e[3] - e[2] + 1 for e in eps)
    print(f"\n{len(eps)} episodes, {sum(L)} trading days = "
          f"{sum(L)/len(valid)*100:.1f}% of history "
          f"({valid[0][0]} .. {valid[-1][0]})")
    print(f"duration: min {L[0]}d  median {statistics.median(L):.0f}d  "
          f"mean {sum(L)/len(L):.1f}d  max {L[-1]}d")
    for lo, hi, lab in ((1, 5, '<=1 week'), (6, 20, '1-4 weeks'),
                        (21, 60, '1-3 months'), (61, 9999, '>3 months')):
        sel = [x for x in L if lo <= x <= hi]
        print(f"  {lab:<12}{len(sel):>3} episodes {sum(sel):>5} days "
              f"({sum(sel)/sum(L)*100:>4.1f}% of all F time)")

    nav = 1.0
    for a, b, _, _ in eps:
        nav *= px[b] / px[a]
    pos = sum(1 for a, b, _, _ in eps if px[b] >= px[a])
    print(f"\nQQQ compounded across all F episodes: {(nav-1)*100:+.1f}%")
    print(f"episodes ending flat-or-up: {pos} of {len(eps)} -- most F episodes are "
          f"harmless; most F TIME is spent in the few that are not")
    print("worst 6 by QQQ return:")
    for a, b, i0, i1 in sorted(eps, key=lambda e: px[e[1]] / px[e[0]])[:6]:
        print(f"   {a} -> {b}  {i1-i0+1:>4}d  {(px[b]/px[a]-1)*100:>7.1f}%")


if __name__ == '__main__':
    main()
