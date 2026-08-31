"""Sensitivity sweep on the classifier's own 50/200-day SMA windows -- never
tested in this project before (everything else has been validated; the
windows themselves were inherited as-given from research/leverage_ma.md).

Methodology: for each candidate (short, long) window pair, recompute the
six-state series with the SAME classifier logic (price vs short MA, price
vs long MA, short MA vs long MA, 1% hysteresis) but different periods, then
apply the SAME state->weight mapping (live TARGET_WEIGHTS, keyed by state
LETTER not by what the letter happens to mean under that window pair) to
build a weekly return series. This isolates "does this window pair time
transitions better" from "what should the weights be" -- re-optimizing
weights per candidate pair would be enormous effort and would just overfit
each pair to its own history, exactly the trap this project has avoided
everywhere else. Full-timeline + search(pre-2020)/holdout(post-2020) Sharpe,
CAGR, MaxDD, plus a state-occupancy sanity check (a pair that degenerates
some state to near-zero weeks is a red flag, not a free win).

RESULTS SUMMARY (run 2026-08-31): a real effect, not a fluke -- a whole
neighborhood of shorter pairs (10/100, 20/100, 30/100) beats the live
50/200 baseline on BOTH search (pre-2020) and holdout (post-2020) Sharpe
simultaneously, not just one side. Best: 10/100, full Sharpe 1.261 vs
baseline 1.138, search 1.245 vs 1.090, holdout 1.291 vs 1.174, MaxDD -20.4%
vs -29.7%. No state occupancy degeneracy across any tested pair (all states
stay comfortably above MIN_N=15 in the ones checked here).

BUT: turnover scales badly. 10/100 produces 289 state transitions over
10.9yrs (26.6/yr) vs baseline's 122 (11.2/yr) -- more than double, and each
transition into/out of B/D/E swings 50-80pp of the portfolio. This backtest
has zero transaction-cost or wash-sale-drag modeling, and this project
already runs meaningful wash-sale complexity at the CURRENT lower turnover.
Not adopted: this is a structural classifier change, not an additive leg --
every downstream per-state weight (all validated against 50/200-defined
states) would need re-optimization against whatever new states a different
window pair produces, and the turnover-cost drag needs modeling before the
apparent Sharpe edge can be trusted net of real trading friction. Documented
as a real, worth-revisiting research finding, not implemented.
"""
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import load_csv, sma, TARGET_WEIGHTS, CORE_SPMO_FRAC, CORE_GLD_FRAC, STATE_LABEL
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
from four_leg_overlay import last_trading_day_per_week

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
CANDIDATES_DIR = 'data/defensive_candidates'
SEARCH_HOLDOUT_SPLIT = '2020-01-01'


def compute_states_custom(dates, px, short_n, long_n, buf=0.01):
    v = [px[d] for d in dates]
    s_short = s_long = None
    out = []
    for i, d in enumerate(dates):
        m_short, m_long = sma(v, i, short_n), sma(v, i, long_n)
        if m_long is None:
            out.append('F')
            continue
        if v[i] > m_short * (1 + buf): s_short = True
        elif v[i] < m_short * (1 - buf): s_short = False
        if v[i] > m_long * (1 + buf): s_long = True
        elif v[i] < m_long * (1 - buf): s_long = False
        cross = m_short > m_long
        if s_short and s_long and cross: out.append('A')
        elif s_short and s_long and not cross: out.append('B')
        elif s_short and not s_long: out.append('C')
        elif not s_short and s_long: out.append('D')
        elif not s_short and not s_long and cross: out.append('E')
        else: out.append('F')
    return out


def sharpe(rets):
    if len(rets) < 4:
        return None
    m = sum(rets) / len(rets)
    v = sum((r - m) ** 2 for r in rets) / (len(rets) - 1)
    if v <= 0:
        return None
    vol = math.sqrt(v) * math.sqrt(52.1775)
    return (m * 52.1775) / vol


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


def main():
    qqq_px = load_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    qqq_dates = sorted(qqq_px)
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

    pairs = [
        (50, 200),   # live baseline
        (20, 100), (20, 150), (20, 200),
        (30, 100), (30, 150), (30, 200),
        (40, 150), (40, 200),
        (50, 150), (50, 250),
        (75, 200), (75, 250),
        (100, 200), (100, 300),
        (10, 50), (10, 100),
    ]

    print(f"{'short/long':<12}{'full CAGR':>11}{'full Sharpe':>13}{'full MaxDD':>12}{'search Sh':>11}{'holdout Sh':>12}  state occupancy (weeks)")
    for short_n, long_n in pairs:
        states = compute_states_custom(qqq_dates, qqq_px, short_n, long_n)
        state_by_date = dict(zip(qqq_dates, states))

        rows = []
        floor = qqq_dates[0]
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
            cw, tw, qw, xw, chw = TARGET_WEIGHTS[st]
            wk_ret = cw * r_core + tw * r_tqqq + qw * r_qld + xw * r_xlu + chw * r_cash
            rows.append((w1, st, wk_ret))

        rets_all = [r[2] for r in rows]
        search_rets = [r[2] for r in rows if r[0] < SEARCH_HOLDOUT_SPLIT]
        holdout_rets = [r[2] for r in rows if r[0] >= SEARCH_HOLDOUT_SPLIT]

        occ = {}
        for _, st, _ in rows:
            occ[st] = occ.get(st, 0) + 1
        occ_str = " ".join(f"{s}={occ.get(s,0)}" for s in 'ABCDEF')

        label = f"{short_n}/{long_n}"
        print(f"{label:<12}{cagr(rets_all)*100:>10.2f}%{sharpe(rets_all):>13.3f}{mdd(rets_all)*100:>11.2f}%"
              f"{sharpe(search_rets):>11.3f}{sharpe(holdout_rets):>12.3f}  {occ_str}")


if __name__ == '__main__':
    main()
