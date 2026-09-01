"""Transaction-cost-adjusted comparison: live 50/200-only classifier vs. the
micro(30/150)/macro(50/200) agreement design (micro_macro_sweep.py's
strongest finding), net of realistic bid-ask spread/slippage drag. Neither
prior backtest modeled this -- every Sharpe/CAGR number produced so far in
this project's MA-window research has been frictionless.

COST MODEL: a one-way spread/slippage cost in basis points, applied to
dollar turnover each week a rebalance actually happens. Dollar turnover
(as a fraction of portfolio) = sum over the 5 legs of |new_weight -
old_weight| -- this already counts both the sell-side and buy-side dollar
amount, so a ONE-WAY bps rate applied to it is the right units (a full
round-trip is captured by summing the two legs' separate |delta| terms).

Rate calibrated from THIS SESSION's own live fills: SPMO spread ~5.4bps,
GLD ~7.4bps, TQQQ ~2-3bps, XLU/BOXX typically tighter. Use 4bps one-way as
a single blended, slightly-conservative rate across all legs -- Robinhood
has no commission, so spread/slippage is the only real per-trade cost here.

WASH-SALE DRAG is NOT modeled as a NAV cost here -- it's a tax-TIMING
effect (defers when a loss can offset a gain), not a return effect, so it
doesn't belong in the same units as a Sharpe/CAGR backtest. Reported
separately as a directional estimate only: this project's live wash-sale
tracking (paper-track/wash_sale.py) has already shown substantial deferred-
loss volume at the CURRENT turnover rate; a proportional scaling with the
~50% higher transition rate is a reasonable direction-of-travel estimate,
not something to present as a precise dollar figure without the account's
actual tax situation.

RESULTS SUMMARY (run 2026-09-01, re-run same day after fixing a BOXX
data bug -- see backtest_overlay_etf.py's _strip_boxx_flat_stub(): BOXX's
price feed was a flat placeholder for all of 2022 pre-2022-12-29, making
every cash leg read a fake 0% return that whole year; numbers below are
POST-fix): the turnover objection does NOT hold up. At the calibrated
4bps rate, the NEW (micro 30/150 + macro) design's annualized cost drag
is still LOWER than the old 50/200-only design (0.49pp/yr vs 0.74pp/yr)
despite having more total transitions (16.7/yr vs 11.2/yr) -- because
most of the "extra" transitions are the small A-agree/A-diverge weight
tweaks (0.9/0.1 vs 0.8/0.2 core/TQQQ, only 0.2 turnover fraction), while
the old design's fewer transitions are all FULL state changes (up to
~2.0 turnover fraction each, e.g. exiting QLD entirely). More
transitions, but mostly cheap ones, beats fewer transitions that are all
expensive. Net Sharpe: old 1.094, new 1.107 -- new design still wins (the
BOXX fix raised both designs' CAGR, since cash-heavy weeks now earn a
real 2022 T-bill return instead of a fake 0%, but did not change which
design wins or by roughly how much). Robust across a wide cost range
(2/4/8/15bps all tested): new design's Sharpe edge over old holds at
every level, including a 15bps stress test well above what these liquid
ETFs actually trade at. Wash-sale drag is NOT modeled as a NAV cost here
(it's a tax-timing effect, not a return effect) -- reported only as a
qualitative direction-of-travel note.
VERDICT: the main open objection from micro_macro_sweep.py is resolved;
this design's edge survives realistic transaction costs, before and
after the BOXX data fix.
"""
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import load_csv, compute_states, TARGET_WEIGHTS, CORE_SPMO_FRAC, CORE_GLD_FRAC
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
from four_leg_overlay import last_trading_day_per_week
from ma_window_sweep import compute_states_custom

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
CANDIDATES_DIR = 'data/defensive_candidates'
SEARCH_HOLDOUT_SPLIT = '2020-01-01'
ONE_WAY_SPREAD_BPS = 0.0004  # 4bps, blended estimate across SPMO/GLD/TQQQ/QLD/XLU/BOXX


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


def nearest_prior(dmap, d, floor):
    dd = d
    while dd not in dmap and dd > floor:
        dd = (date.fromisoformat(dd) - timedelta(days=1)).isoformat()
    return dmap.get(dd)


# Validated micro=30/150 weights (core, tqqq, qld, xlu, cash), from micro_macro_sweep.py
MICRO_WEIGHTS = {
    ('A', True): (0.9, 0.1, 0.0, 0.0, 0.0),
    ('D', False): (0.7, 0.0, 0.0, 0.0, 0.3),
}


def main():
    qqq_px = load_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    qqq_dates = sorted(qqq_px)
    macro_states = compute_states(qqq_dates, qqq_px)
    macro_by_date = dict(zip(qqq_dates, macro_states))
    micro_states = compute_states_custom(qqq_dates, qqq_px, 30, 150)
    micro_by_date = dict(zip(qqq_dates, micro_states))

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
        while sd not in macro_by_date and sd > floor:
            sd = (date.fromisoformat(sd) - timedelta(days=1)).isoformat()
        macro = macro_by_date.get(sd)
        micro = nearest_prior(micro_by_date, sd, floor)
        if macro is None or micro is None:
            continue
        r_core = CORE_SPMO_FRAC * (spmo[w1] / spmo[w0] - 1) + CORE_GLD_FRAC * (gld[g1] / gld[g0] - 1)
        r_tqqq = tqqq[t1] / tqqq[t0] - 1
        r_qld = qld[q1] / qld[q0] - 1
        r_xlu = xlu[x1] / xlu[x0] - 1
        r_cash = cash_idx[c1] / cash_idx[c0] - 1
        agree = micro in ('A', 'B')
        rows.append((w1, macro, agree, r_core, r_tqqq, r_qld, r_xlu, r_cash))

    def weight_old(st):
        return TARGET_WEIGHTS[st]

    def weight_new(st, agree):
        return MICRO_WEIGHTS.get((st, agree), TARGET_WEIGHTS[st])

    def run(weight_fn, cost_bps):
        rets_gross, rets_net = [], []
        prev_w = None
        for r in rows:
            w1, st, agree, rc, rt, rq, rx, rca = r
            w = weight_fn(st, agree)
            gross = w[0] * rc + w[1] * rt + w[2] * rq + w[3] * rx + w[4] * rca
            rets_gross.append(gross)
            if prev_w is None:
                turnover = 0.0
            else:
                turnover = sum(abs(w[i] - prev_w[i]) for i in range(5))
            cost = cost_bps * turnover
            rets_net.append(gross - cost)
            prev_w = w
        return rets_gross, rets_net

    old_gross, old_net = run(lambda st, agree: weight_old(st), ONE_WAY_SPREAD_BPS)
    new_gross, new_net = run(lambda st, agree: weight_new(st, agree), ONE_WAY_SPREAD_BPS)

    weeks = [r[0] for r in rows]
    pre = [i for i, w in enumerate(weeks) if w < SEARCH_HOLDOUT_SPLIT]
    post = [i for i, w in enumerate(weeks) if w >= SEARCH_HOLDOUT_SPLIT]

    print(f"Cost assumption: {ONE_WAY_SPREAD_BPS*10000:.0f}bps one-way spread/slippage per dollar turned over\n")
    for label, gross, net in (('OLD (50/200 only)', old_gross, old_net), ('NEW (micro 30/150 + macro)', new_gross, new_net)):
        print(f"{label}:")
        print(f"  gross: Sharpe={sharpe(gross):.3f}  CAGR={cagr(gross)*100:.2f}%  MaxDD={mdd(gross)*100:.2f}%")
        print(f"  net  : Sharpe={sharpe(net):.3f}  CAGR={cagr(net)*100:.2f}%  MaxDD={mdd(net)*100:.2f}%")
        print(f"  search net: {sharpe([net[i] for i in pre]):.3f}   holdout net: {sharpe([net[i] for i in post]):.3f}")
        total_cost_drag = cagr(gross) - cagr(net)
        print(f"  annualized cost drag: {total_cost_drag*100:.2f}pp/yr")
        print()

    # sensitivity: try a couple of other cost assumptions
    print("Sensitivity to the cost assumption (net Sharpe / net CAGR):")
    for bps in (0.0002, 0.0004, 0.0008, 0.0015):
        _, old_net_s = run(lambda st, agree: weight_old(st), bps)
        _, new_net_s = run(lambda st, agree: weight_new(st, agree), bps)
        print(f"  {bps*10000:.0f}bps: old Sharpe={sharpe(old_net_s):.3f} CAGR={cagr(old_net_s)*100:.2f}%   "
              f"new Sharpe={sharpe(new_net_s):.3f} CAGR={cagr(new_net_s)*100:.2f}%")


if __name__ == '__main__':
    main()
