"""Turnover-cost model for the 4-signal majority-vote composite
(combined_confidence_signal.py): state A weeks where all 4 signals
unanimously agree "confident" (micro/macro agreement, price vs 20dma,
QQQ realized-vol percentile <75th, VIX percentile <75th) get de-levered
to 100% core / 0% TQQQ; the remaining ~29% of A stays at live's 80/20.
Every other state (B-F) unchanged from TARGET_WEIGHTS. Same 4bps one-way
spread/slippage cost model as turnover_cost_model.py, calibrated from this
session's own live fills.

RESULTS SUMMARY (run 2026-09-01): REJECTED, decisively -- and this reverses
every isolated-cell result this whole state-A confidence research thread
produced. At the full-timeline, cost-adjusted level, live's unchanged 80/20
core/TQQQ is the actual OPTIMUM: Sharpe declines monotonically as the
confident-weeks weight is de-levered away from 80/20 (1.111 at 80/20 ->
1.103 at 85/15 -> 1.090 at 90/10 -> 1.074 at 95/5 -> 1.054 at the fully
de-levered 100/0). No de-leveraging level beats doing nothing. Confirmed
across the full cost-sensitivity range (2/4/8/15bps), and turnover is also
worse (15.3/yr vs live's 8.6/yr).

WHY THE ISOLATED TESTS WERE MISLEADING: isolated-holdout validation (used
throughout this session, e.g. micro_macro_agreement.py, combined_
confidence_signal.py) checks whether a candidate weight beats live using
ONLY that cell's own week-to-week return variance -- useful for catching
corner-solution artifacts, but blind to how those weeks' returns interact
with the rest of the multi-state portfolio. State A is the majority state
and already contributes the strategy's steadiest, best-behaved return
stream (mostly free of the worse drawdowns concentrated in D/E/F); trimming
its return specifically in its most-confirmed weeks removes some of the
portfolio's best Sharpe contribution, which shows up as a full-timeline
cost even though those weeks individually looked "improvable" in isolation
against ONLY their own variance.

Net conclusion for the entire state-A confidence line of research (four
independently-constructed signals -- micro/macro agreement, price vs
20dma, QQQ realized-vol percentile, VIX percentile -- all mutually
corroborating in isolation): REJECTED at the level that actually matters.
This is the most thoroughly-investigated idea of the whole session and it
is a clean rejection, not an ambiguous one. No live weights changed.
"""
import csv
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import load_csv, sma, compute_states, TARGET_WEIGHTS, CORE_SPMO_FRAC, CORE_GLD_FRAC
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
from four_leg_overlay import last_trading_day_per_week
from a1a2_deepdive import qqq_realized_vol_20d, rolling_percentile, nearest_prior
from ma_window_sweep import compute_states_custom

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
CANDIDATES_DIR = 'data/defensive_candidates'
SEARCH_HOLDOUT_SPLIT = '2020-01-01'
ONE_WAY_SPREAD_BPS = 0.0004


def sharpe(rets):
    if len(rets) < 4:
        return None
    m = sum(rets) / len(rets)
    v = sum((r - m) ** 2 for r in rets) / (len(rets) - 1)
    if v <= 0:
        return None
    return (m * 52.1775) / (math.sqrt(v) * math.sqrt(52.1775))


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


def load_fred(path):
    out = {}
    for row in csv.DictReader(open(path)):
        d, v = row['observation_date'], row[list(row.keys())[1]]
        if v and v != '.':
            out[d] = float(v)
    return out


def main():
    qqq_px = load_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    qqq_dates = sorted(qqq_px)
    qqq_v = [qqq_px[d] for d in qqq_dates]
    states = compute_states(qqq_dates, qqq_px)
    state_by_date = dict(zip(qqq_dates, states))

    micro_states = compute_states_custom(qqq_dates, qqq_px, 30, 150)
    micro_by_date = dict(zip(qqq_dates, micro_states))

    sig20 = {}
    s20 = None
    for i, d in enumerate(qqq_dates):
        m20 = sma(qqq_v, i, 20)
        if m20 is None:
            continue
        if qqq_v[i] > m20 * 1.01:
            s20 = True
        elif qqq_v[i] < m20 * 0.99:
            s20 = False
        if s20 is not None:
            sig20[d] = s20

    vol20 = qqq_realized_vol_20d(qqq_px, qqq_dates)
    vol_pct = rolling_percentile(vol20, qqq_dates, 252)

    vix = load_fred(f'{ROBINHOOD_REPO}/VIXCLS.csv')
    vix_dates = sorted(vix)
    vix_pct = rolling_percentile(vix, vix_dates, 252)

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
        sig1 = nearest_prior(micro_by_date, sd, floor)
        sig1 = (sig1 in ('A', 'B')) if sig1 is not None else None
        sig2 = nearest_prior(sig20, sd, floor)
        sig3 = nearest_prior(vol_pct, sd, floor)
        sig3 = (sig3 < 0.75) if sig3 is not None else None
        sig4 = nearest_prior(vix_pct, sd, vix_dates[0])
        sig4 = (sig4 < 0.75) if sig4 is not None else None
        signals = [sig1, sig2, sig3, sig4]
        unanimous_confident = all(s is True for s in signals) if None not in signals else False

        r_core = CORE_SPMO_FRAC * (spmo[w1] / spmo[w0] - 1) + CORE_GLD_FRAC * (gld[g1] / gld[g0] - 1)
        r_tqqq = tqqq[t1] / tqqq[t0] - 1
        r_qld = qld[q1] / qld[q0] - 1
        r_xlu = xlu[x1] / xlu[x0] - 1
        r_cash = cash_idx[c1] / cash_idx[c0] - 1
        rows.append((w1, st, unanimous_confident, r_core, r_tqqq, r_qld, r_xlu, r_cash))

    def old_w(st):
        return TARGET_WEIGHTS[st]

    def new_w(st, confident):
        if st == 'A' and confident:
            return (1.0, 0.0, 0.0, 0.0, 0.0)
        return TARGET_WEIGHTS[st]

    def run(weight_fn, cost_bps):
        gross, net = [], []
        prev_w = None
        for r in rows:
            w1, st, confident, rc, rt, rq, rx, rca = r
            w = weight_fn(st, confident)
            g = w[0] * rc + w[1] * rt + w[2] * rq + w[3] * rx + w[4] * rca
            gross.append(g)
            to = 0.0 if prev_w is None else sum(abs(w[i] - prev_w[i]) for i in range(5))
            net.append(g - cost_bps * to)
            prev_w = w
        return gross, net

    old_gross, old_net = run(lambda st, c: old_w(st), ONE_WAY_SPREAD_BPS)
    new_gross, new_net = run(lambda st, c: new_w(st, c), ONE_WAY_SPREAD_BPS)

    weeks = [r[0] for r in rows]
    pre = [i for i, w in enumerate(weeks) if w < SEARCH_HOLDOUT_SPLIT]
    post = [i for i, w in enumerate(weeks) if w >= SEARCH_HOLDOUT_SPLIT]

    print(f"Cost assumption: {ONE_WAY_SPREAD_BPS*10000:.0f}bps one-way spread/slippage\n")
    for label, gross, net in (('OLD (live, all states unchanged)', old_gross, old_net),
                               ('NEW (composite de-lever confident A)', new_gross, new_net)):
        print(f"{label}:")
        print(f"  gross: Sharpe={sharpe(gross):.3f}  CAGR={cagr(gross)*100:.2f}%  MaxDD={mdd(gross)*100:.2f}%")
        print(f"  net  : Sharpe={sharpe(net):.3f}  CAGR={cagr(net)*100:.2f}%  MaxDD={mdd(net)*100:.2f}%")
        print(f"  search net: {sharpe([net[i] for i in pre]):.3f}   holdout net: {sharpe([net[i] for i in post]):.3f}")
        print(f"  annualized cost drag: {(cagr(gross)-cagr(net))*100:.2f}pp/yr\n")

    # turnover
    old_seq = [(r[1],) for r in rows]
    new_seq = [(r[1], r[1] == 'A' and r[2]) for r in rows]
    old_trans = sum(1 for i in range(1, len(old_seq)) if old_seq[i] != old_seq[i - 1])
    new_trans = sum(1 for i in range(1, len(new_seq)) if new_seq[i] != new_seq[i - 1])
    yrs = len(rows) / 52.1775
    print(f"transitions: old={old_trans} ({old_trans/yrs:.1f}/yr)  new={new_trans} ({new_trans/yrs:.1f}/yr)")

    print("\nSensitivity to cost assumption:")
    for bps in (0.0002, 0.0004, 0.0008, 0.0015):
        _, old_s = run(lambda st, c: old_w(st), bps)
        _, new_s = run(lambda st, c: new_w(st, c), bps)
        print(f"  {bps*10000:.0f}bps: old Sharpe={sharpe(old_s):.3f} CAGR={cagr(old_s)*100:.2f}%   "
              f"new Sharpe={sharpe(new_s):.3f} CAGR={cagr(new_s)*100:.2f}%")


if __name__ == '__main__':
    main()
