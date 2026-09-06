"""Calendar-month returns of the CURRENT design (state.py as it stands), run on
the REAL instruments, Jan 2024 -> present.

WHY THIS EXISTS. Ad-hoc "how did it do from X to Y" questions kept producing
one-off scripts, and single windows are easy to cherry-pick. This runs every
month on the same footing so the shape of the return stream is visible rather
than argued about.

WHAT IT IS. A backtest, not account history. It applies TODAY'S weights
(A 70/30, B 75/25, C 100% core, D 85% QLD, E 50 XLU / 50 cash, F 100% cash,
micro overlay off), the 20% volatility target, the 3% drift band and the
zero-leg sweep across the whole period. The live account did not exist before
2026-08-17 and ran different designs before 2026-09-02, so NONE of these
months are realised performance. Read it for the shape, not as a track record.

MECHANICS. Daily resolution, held weights drift with realised returns between
rebalances, 4bps one-way cost on realised turnover. Signal is taken on day t's
close and held into t+1, matching how the live trigger actually trades. A
month's return runs from the last trading day of the prior month to the last
trading day of the month, and the sleeve is NOT reset at month boundaries --
months are reporting slices of one continuous simulation.

CAVEAT ON PRICES. Split-adjusted closes, so dividends are excluded. That
understates SPMO (~0.7%/yr) and especially XLU (~3%/yr), so state-E months are
reported slightly worse than they truly were. BOXX's flat-price stub is
stripped by load_daily_csv().
"""
import sys
from collections import defaultdict

sys.path.insert(0, 'paper-track')
from state import (compute_states, compute_micro_agreement, realized_vol,
                   target_weights_with_voltarget, needs_rebalance)
from backtest_overlay_etf import load_daily_csv
from long_history_backtest import load_px

REPO = '/home/user/robinhood/data/kairos/etf'
ONE_WAY = 0.0004
LEGS = ('SPMO', 'TQQQ', 'QLD', 'XLU', 'BOXX')
START = '2024-01-01'

# Closes after the CSV snapshot ends (2026-08-27/28), from live quotes this session.
TAIL = {
    'SPMO': {'2026-08-28': 146.78, '2026-08-31': 147.09, '2026-09-01': 145.54,
             '2026-09-02': 146.34, '2026-09-03': 147.41, '2026-09-04': 149.72},
    'TQQQ': {'2026-08-28': 71.85, '2026-08-31': 71.92, '2026-09-01': 69.15,
             '2026-09-02': 69.60, '2026-09-03': 72.03, '2026-09-04': 72.37},
    'QLD':  {'2026-08-28': 90.17, '2026-08-31': 90.24, '2026-09-01': 87.92,
             '2026-09-02': 88.31, '2026-09-03': 90.38, '2026-09-04': 90.68},
    'XLU':  {'2026-08-28': 42.73, '2026-08-31': 42.23, '2026-09-01': 42.56,
             '2026-09-02': 42.67, '2026-09-03': 43.03, '2026-09-04': 43.08},
    'BOXX': {'2026-08-31': 118.07, '2026-09-01': 118.11, '2026-09-02': 118.06,
             '2026-09-03': 118.08, '2026-09-04': 118.13},
    'QQQ':  {'2026-09-02': 709.24, '2026-09-03': 717.67, '2026-09-04': 719.12},
}


def build():
    px = {s: load_daily_csv(f'{REPO}/{s}.csv') for s in LEGS}
    for s in LEGS:
        px[s].update(TAIL[s])
    qqq = load_px('data/qqq_long_history.csv')
    qqq.update(TAIL['QQQ'])
    common = sorted(set.intersection(*[set(px[s]) for s in LEGS]) & set(qqq))
    return px, qqq, common


def simulate(px, qqq, days):
    qd = sorted(qqq)
    states = dict(zip(qd, compute_states(qd, qqq)))
    micro = compute_micro_agreement(qd, qqq)
    held = prev = None
    out = []
    for i in range(1, len(days)):
        d0, d1 = days[i - 1], days[i]
        st, ag = states[d0], micro[d0]
        t = target_weights_with_voltarget(st, ag, realized_vol(qd, qqq, as_of=d0))
        cost = 0.0
        if held is None:
            held = list(t)
        else:
            do, drift, _ = needs_rebalance(t, held, st != prev)
            if do:
                cost = ONE_WAY * drift
                held = list(t)
        r = [px[s][d1] / px[s][d0] - 1 for s in LEGS]
        g = sum(held[j] * r[j] for j in range(5))
        out.append((d1, st, g - cost))
        dn = 1 + g
        if dn > 0:
            held = [held[j] * (1 + r[j]) / dn for j in range(5)]
        prev = st
    return out


def main():
    px, qqq, common = build()
    warm = [d for d in common if d >= '2022-06-01']       # 200d SMA + vol warm-up
    daily_all = simulate(px, qqq, warm)
    # the trading day immediately BEFORE the reporting window, so January 2024
    # gets a real benchmark base instead of being compared against itself
    idx = [x[0] for x in daily_all]
    first = next(i for i, d in enumerate(idx) if d >= START)
    base_day = idx[first - 1]
    daily = daily_all[first:]

    months = defaultdict(list)
    for d, st, r in daily:
        months[d[:7]].append((d, st, r))

    def bench(series, a, b):
        return series[b] / series[a] - 1

    keys = sorted(months)
    prev_close = {k: None for k in keys}
    for n, k in enumerate(keys):
        prev_close[k] = base_day if n == 0 else months[keys[n - 1]][-1][0]
    print(f"Calendar-month returns, current design, real instruments, net of 4bps\n"
          f"{keys[0]} .. {keys[-1]}   ({len(daily)} trading days)\n")
    print(f"{'month':<9}{'strategy':>10}{'QQQ':>9}{'SPMO':>9}{'diff vs QQQ':>13}   states")
    nav = navq = navs = 1.0
    rows = []
    for k in keys:
        dd = months[k]
        a, b = prev_close[k], dd[-1][0]
        m = 1.0
        for _, _, r in dd:
            m *= 1 + r
        m -= 1
        q = bench(qqq, a, b)
        s = bench(px['SPMO'], a, b)
        nav *= 1 + m
        navq *= 1 + q; navs *= 1 + s
        occ = defaultdict(int)
        for _, st, _ in dd:
            occ[st] += 1
        top = ' '.join(f"{st}{n}" for st, n in sorted(occ.items(), key=lambda x: -x[1]))
        rows.append((k, m, q, s))
        print(f"{k:<9}{m*100:>9.2f}%{q*100:>8.2f}%{s*100:>8.2f}%{(m-q)*100:>+12.2f}   {top}")

    print(f"\n{'CUMULATIVE':<9}{(nav-1)*100:>9.2f}%{(navq-1)*100:>8.2f}%{(navs-1)*100:>8.2f}%")
    comp = rows
    wins = sum(1 for _, m, q, _ in comp if m > q)
    up = [(m, q) for _, m, q, _ in comp if q > 0]
    dn = [(m, q) for _, m, q, _ in comp if q <= 0]
    print(f"\nbeat QQQ in {wins}/{len(comp)} months")
    if up:
        print(f"  QQQ-up months   ({len(up):>2}): strategy avg {sum(m for m,_ in up)/len(up)*100:+6.2f}%  "
              f"QQQ avg {sum(q for _,q in up)/len(up)*100:+6.2f}%  capture {sum(m for m,_ in up)/sum(q for _,q in up):.2f}x")
    if dn:
        print(f"  QQQ-down months ({len(dn):>2}): strategy avg {sum(m for m,_ in dn)/len(dn)*100:+6.2f}%  "
              f"QQQ avg {sum(q for _,q in dn)/len(dn)*100:+6.2f}%  capture {sum(m for m,_ in dn)/sum(q for _,q in dn):.2f}x")
    worst = min(comp, key=lambda r: r[1]); best = max(comp, key=lambda r: r[1])
    print(f"  best month {best[0]} {best[1]*100:+.2f}%   worst month {worst[0]} {worst[1]*100:+.2f}%")
    # daily-resolution risk comparison -- the point of the whole exercise is
    # whether the extra machinery bought anything for the risk it took
    import math
    days = [d for d, _, _ in daily]

    def dd_and_vol(series_rets):
        peak = cur = 1.0; mdd = 0.0
        for r in series_rets:
            cur *= 1 + r; peak = max(peak, cur); mdd = min(mdd, cur / peak - 1)
        n = len(series_rets); mu = sum(series_rets) / n
        sd = (sum((x - mu) ** 2 for x in series_rets) / (n - 1)) ** 0.5
        ann_vol = sd * math.sqrt(252)
        cagr = cur ** (252 / n) - 1
        return cagr, ann_vol, (mu * 252) / ann_vol, mdd

    strat = [r for _, _, r in daily]
    qser = [qqq[days[i]] / qqq[days[i - 1]] - 1 for i in range(1, len(days))]
    sser = [px['SPMO'][days[i]] / px['SPMO'][days[i - 1]] - 1 for i in range(1, len(days))]
    print(f"\n{'':<12}{'CAGR':>9}{'ann vol':>9}{'Sharpe':>8}{'max DD':>9}")
    for nm, ser in (('strategy', strat), ('QQQ', qser), ('SPMO', sser)):
        c, v, sh, m = dd_and_vol(ser)
        print(f"{nm:<12}{c*100:>8.2f}%{v*100:>8.1f}%{sh:>8.2f}{m*100:>8.1f}%")


if __name__ == '__main__':
    main()
