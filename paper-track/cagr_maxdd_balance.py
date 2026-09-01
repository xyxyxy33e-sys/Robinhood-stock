"""Assess all six states on a CAGR-vs-MaxDD basis (Sharpe deliberately set
aside for this pass) -- for each state, sweep its own natural one-parameter
leverage/defense dial, holding every other state at live TARGET_WEIGHTS,
and report the full-timeline CAGR/MaxDD frontier so a balance point can be
picked by return-per-unit-of-drawdown rather than by Sharpe.

Dials (one per state, matching what each state's design already varies):
  A: TQQQ weight (core = 1-tqqq)            live: 20% TQQQ
  B: TQQQ weight (core = 1-tqqq)            live: 75% TQQQ
  C: TQQQ weight added on top of core       live: 0% (pure core)
  D: QLD weight (cash = 1-qld, core=0)      live: 70% QLD / 30% cash
  E: XLU weight (cash = 1-xlu)              live: 50% XLU / 50% cash
  F: core weight (cash = 1-core)            live: 30% core / 70% cash

RESULTS SUMMARY (run 2026-09-01): IMPORTANT ARTIFACT -- for B, and for C/F
above roughly 30-40%, the portfolio's overall MaxDD stays completely flat
as the dial changes, because this backtest's single worst 11-year
drawdown episode doesn't occur during those states' weeks at all. Their
CAGR/MaxDD ratio therefore silently favors "more leverage" for free in
THIS backtest, not because it's actually risk-free -- ignore those three
states' "best ratio" points, they're not a real signal.

Where MaxDD genuinely moves (A, D, E), real trade-offs emerge:
  A: best ratio at 0-10% TQQQ (0.864) vs live's 20% (0.857) -- small, real
     preference for less leverage than live, but the curve is fairly flat
     near live's setting.
  D: best ratio at 10% QLD (0.872) vs live's 70% (0.857) -- MaxDD improves
     from -29.70% to -22.68%, but CAGR falls from 25.46% to 19.78%. Live's
     70% is meaningfully more aggressive than the CAGR/MaxDD-optimal point.
  E: best ratio at 10% XLU (0.988, a clear standalone peak, well above
     every other point on any state's curve) vs live's 50% (0.857) --
     CAGR only drops to 24.14% from 25.46% (1.3pp) while MaxDD improves
     from -29.70% to -24.45%. The standout result of this pass -- flagged
     for a proper search/holdout + corner-solution check before trusting
     it, given E is already the thinnest state (32 weeks) in the design.

C: only shows a real trade-off above ~40% TQQQ-added; below that, adding
modest leverage costs nothing this backtest can see (same MaxDD-flatness
caveat as B/F, weaker below 40%).
"""
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import load_csv, compute_states, TARGET_WEIGHTS, CORE_SPMO_FRAC, CORE_GLD_FRAC
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
from four_leg_overlay import last_trading_day_per_week

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
CANDIDATES_DIR = 'data/defensive_candidates'


def cagr(rets):
    nav = 1.0
    for r in rets:
        nav *= (1 + r)
    return nav ** (1 / (len(rets) / 52.1775)) - 1


def mdd(rets):
    nav = 1.0
    peak = 1.0
    m = 0.0
    for r in rets:
        nav *= (1 + r)
        peak = max(peak, nav)
        m = min(m, nav / peak - 1)
    return m


def sharpe(rets):
    m = sum(rets) / len(rets)
    v = sum((r - m) ** 2 for r in rets) / (len(rets) - 1)
    if v <= 0:
        return None
    return (m * 52.1775) / (math.sqrt(v) * math.sqrt(52.1775))


def main():
    qqq_px = load_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    qqq_dates = sorted(qqq_px)
    states = compute_states(qqq_dates, qqq_px)
    state_by_date = dict(zip(qqq_dates, states))

    spmo = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPMO.csv')
    tqqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/TQQQ.csv')
    qld = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QLD.csv')
    xlu = load_daily_csv(f'{ROBINHOOD_REPO}/etf/XLU.csv')
    gld = load_daily_csv(f'{CANDIDATES_DIR}/GLD.csv')
    boxx = load_daily_csv(f'{ROBINHOOD_REPO}/etf/BOXX.csv')
    tbill = load_tbill()
    all_dates = sorted(set(qqq_dates) | set(tqqq) | set(spmo) | set(qld) | set(xlu) | set(gld))
    cash_idx = build_cash_index(all_dates, boxx, tbill)

    spmo_wk = last_trading_day_per_week(sorted(set(spmo)))
    tqqq_wk = last_trading_day_per_week(sorted(set(tqqq)))
    qld_wk = last_trading_day_per_week(sorted(set(qld)))
    xlu_wk = last_trading_day_per_week(sorted(set(xlu)))
    gld_wk = last_trading_day_per_week(sorted(set(gld)))
    cash_wk = last_trading_day_per_week(sorted(set(cash_idx)))
    keys = sorted(set(spmo_wk) & set(tqqq_wk) & set(qld_wk) & set(xlu_wk) & set(gld_wk) & set(cash_wk))
    keys = [k for k in keys if spmo_wk[k] >= '2015-11-02']
    floor = qqq_dates[0]

    rows = []
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        w0, w1 = spmo_wk[k0], spmo_wk[k1]
        t0, t1 = tqqq_wk[k0], tqqq_wk[k1]
        q0, q1 = qld_wk[k0], qld_wk[k1]
        x0, x1 = xlu_wk[k0], xlu_wk[k1]
        g0, g1 = gld_wk[k0], gld_wk[k1]
        c0, c1 = cash_wk[k0], cash_wk[k1]
        sd = w0
        while sd not in state_by_date and sd > floor:
            sd = (date.fromisoformat(sd) - timedelta(days=1)).isoformat()
        st = state_by_date.get(sd)
        if st is None:
            continue
        r_core = CORE_SPMO_FRAC * (spmo[w1] / spmo[w0] - 1) + CORE_GLD_FRAC * (gld[g1] / gld[g0] - 1)
        r_tqqq = tqqq[t1] / tqqq[t0] - 1
        r_qld = qld[q1] / qld[q0] - 1
        r_xlu = xlu[x1] / xlu[x0] - 1
        r_cash = cash_idx[c1] / cash_idx[c0] - 1
        rows.append((w1, st, r_core, r_tqqq, r_qld, r_xlu, r_cash))

    def weekly_ret(row, target_state, dial_weights):
        w1, st, rc, rt, rq, rx, rca = row
        if st == target_state:
            cw, tw, qw, xw, chw = dial_weights
        else:
            cw, tw, qw, xw, chw = TARGET_WEIGHTS[st]
        return cw * rc + tw * rt + qw * rq + xw * rx + chw * rca

    dial_specs = {
        'A': ('TQQQ%', lambda p: (1 - p, p, 0.0, 0.0, 0.0), 0.20),
        'B': ('TQQQ%', lambda p: (1 - p, p, 0.0, 0.0, 0.0), 0.75),
        'C': ('TQQQ% (added)', lambda p: (1 - p, p, 0.0, 0.0, 0.0), 0.00),
        'D': ('QLD%', lambda p: (0.0, 0.0, p, 0.0, 1 - p), 0.70),
        'E': ('XLU%', lambda p: (0.0, 0.0, 0.0, p, 1 - p), 0.50),
        'F': ('core%', lambda p: (p, 0.0, 0.0, 0.0, 1 - p), 0.30),
    }

    for st, (label, wfn, live_p) in dial_specs.items():
        print(f"=== State {st} -- dial: {label} (live={live_p*100:.0f}%) ===")
        base_rets = [weekly_ret(r, st, wfn(live_p)) for r in rows]
        base_cagr, base_mdd = cagr(base_rets), mdd(base_rets)
        print(f"  {'p':>6}{'CAGR':>9}{'MaxDD':>9}{'Sharpe':>9}   CAGR/|MaxDD|")
        results = []
        for pct in range(0, 101, 10):
            p = pct / 100
            rets = [weekly_ret(r, st, wfn(p)) for r in rows]
            c, m = cagr(rets), mdd(rets)
            sh = sharpe(rets)
            ratio = c / abs(m) if m != 0 else float('inf')
            marker = ' <- live' if abs(p - live_p) < 1e-9 else ''
            print(f"  {pct:>5}%{c*100:>8.2f}%{m*100:>8.2f}%{sh:>9.3f}{ratio:>10.3f}{marker}")
            results.append((p, c, m, sh, ratio))
        best_ratio = max(results, key=lambda x: x[4])
        print(f"  Best CAGR/|MaxDD| ratio: p={best_ratio[0]*100:.0f}%  CAGR={best_ratio[1]*100:.2f}%  MaxDD={best_ratio[2]*100:.2f}%")
        print()


if __name__ == '__main__':
    main()
