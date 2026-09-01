"""Broader trial on the micro/macro agreement idea (micro_macro_agreement.py
found a real-but-washed effect at micro=10/100): sweep the MICRO classifier's
own window pair, holding the macro classifier fixed at the live 50/200, to
see whether a different micro pair produces validated signals across more
macro states or a stronger net full-timeline effect.

Same discipline throughout: each macro state split into agree/diverge (micro
in {A,B} = agree), MIN_N=15 per half both search and holdout, cash FIXED per
cell (never searched freely), each cell's search-optimal weight checked on
isolated holdout against the live macro weight, and -- the bug fixed last
time -- ONLY cells that actually validate on holdout are applied when
building the full-timeline aggregate; failed cells keep the live weight.

RESULTS SUMMARY (run 2026-09-01): the strongest, best-behaved finding in
this whole "improve the classifier" line of research. A/agree and D/diverge
validate for EVERY micro pair tested (9 windows, 10/50 through 40/150) --
consistent across parameterization, unlike A1/A2's threshold sensitivity.
Best (30/150): full Sharpe 1.171 vs live 1.138, search 1.140 vs 1.090,
holdout 1.203 vs 1.174 -- all three improve simultaneously (the clean
confirmation pattern, not the search-up/holdout-down overfitting signature
that killed three_ma_classifier.py). CAGR 21.56% vs 25.46% (real cost),
MaxDD -21.91% vs -29.70% (materially shallower). Turnover check
(paper-track/ separate ad-hoc check, not re-run here): 30/150 combined
transitions ~16.7/yr vs macro-only 11.2/yr (~50% more, of which ~5.5/yr are
"extra" within-macro-state flips) -- much milder than 10/100's ~24.8/yr or
the STACK/POSITION classifier's blowup. NOT YET IMPLEMENTED: no
transaction-cost/wash-sale-drag modeling at the higher turnover; only A and
D are touched (B/C/E/F stay at live weights, too thin to test); adds a
second classifier + doubled per-state weight table to state.py, a real
complexity increase. Best candidate for a possible future implementation,
pending the above -- flagged to the user as a serious option, not filed
away like the other tested ideas this session.
"""
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import load_csv, compute_states, TARGET_WEIGHTS, STATE_LABEL, CORE_SPMO_FRAC, CORE_GLD_FRAC
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
from four_leg_overlay import last_trading_day_per_week
from ma_window_sweep import compute_states_custom

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
CANDIDATES_DIR = 'data/defensive_candidates'
SEARCH_HOLDOUT_SPLIT = '2020-01-01'
MIN_N = 15
STEP = 0.1


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


def grid_search_cell(search_rows, cash_fixed):
    budget = round(1 - cash_fixed, 6)
    best = (None,) * 4 + (-1e9,)
    n = round(budget / STEP + 1e-9) if budget > 1e-9 else 0
    for i in range(n + 1):
        cw = round(i * STEP, 4)
        for j in range(n + 1 - i):
            tw = round(j * STEP, 4)
            for k in range(n + 1 - i - j):
                qw = round(k * STEP, 4)
                xw = round(budget - cw - tw - qw, 4)
                if xw < -1e-9:
                    continue
                rets = [cw * r[2] + tw * r[3] + qw * r[4] + xw * r[5] + cash_fixed * r[6] for r in search_rows]
                sh = sharpe(rets)
                if sh is not None and sh > best[4]:
                    best = (cw, tw, qw, xw, sh)
    return (*best[:4], cash_fixed, best[4])


def build_rows(qqq_px, qqq_dates, macro_by_date, micro_by_date, spmo, tqqq, qld, xlu, gld, cash_idx,
               spmo_wk, tqqq_wk, qld_wk, xlu_wk, gld_wk, cash_wk, keys, floor):
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
    return rows


def run_one_pair(short_n, long_n, qqq_px, qqq_dates, macro_by_date, common_kwargs):
    micro_states = compute_states_custom(qqq_dates, qqq_px, short_n, long_n)
    micro_by_date = dict(zip(qqq_dates, micro_states))
    rows = build_rows(qqq_px, qqq_dates, macro_by_date, micro_by_date, **common_kwargs)

    validated = {}
    n_validated = 0
    for st in 'ABCDEF':
        st_rows = [r for r in rows if r[1] == st]
        for label, agree_flag in (('agree', True), ('diverge', False)):
            subset = [r for r in st_rows if r[2] == agree_flag]
            search = [r for r in subset if r[0] < SEARCH_HOLDOUT_SPLIT]
            holdout = [r for r in subset if r[0] >= SEARCH_HOLDOUT_SPLIT]
            if len(search) < MIN_N or len(holdout) < MIN_N:
                continue
            cash_fixed = TARGET_WEIGHTS[st][4]
            best = grid_search_cell(search, cash_fixed)
            live_w = TARGET_WEIGHTS[st]
            live_hold = [live_w[0]*r[3]+live_w[1]*r[4]+live_w[2]*r[5]+live_w[3]*r[6]+live_w[4]*r[7] for r in holdout]
            new_hold = [best[0]*r[3]+best[1]*r[4]+best[2]*r[5]+best[3]*r[6]+best[4]*r[7] for r in holdout]
            sh_new, sh_live = sharpe(new_hold), sharpe(live_hold)
            if sh_new is not None and sh_live is not None and sh_new > sh_live:
                validated[(st, agree_flag)] = best[:5]
                n_validated += 1

    old_rets, new_rets = [], []
    for r in rows:
        ow = TARGET_WEIGHTS[r[1]]
        old_rets.append(ow[0]*r[3]+ow[1]*r[4]+ow[2]*r[5]+ow[3]*r[6]+ow[4]*r[7])
        nw = validated.get((r[1], r[2]), ow)
        new_rets.append(nw[0]*r[3]+nw[1]*r[4]+nw[2]*r[5]+nw[3]*r[6]+nw[4]*r[7])

    weeks = [r[0] for r in rows]
    pre = [i for i, w in enumerate(weeks) if w < SEARCH_HOLDOUT_SPLIT]
    post = [i for i, w in enumerate(weeks) if w >= SEARCH_HOLDOUT_SPLIT]

    return {
        'pair': f"{short_n}/{long_n}",
        'n_validated': n_validated,
        'validated_cells': list(validated.keys()),
        'full_sharpe_old': sharpe(old_rets), 'full_sharpe_new': sharpe(new_rets),
        'search_old': sharpe([old_rets[i] for i in pre]), 'search_new': sharpe([new_rets[i] for i in pre]),
        'holdout_old': sharpe([old_rets[i] for i in post]), 'holdout_new': sharpe([new_rets[i] for i in post]),
        'cagr_old': cagr(old_rets), 'cagr_new': cagr(new_rets),
        'mdd_old': mdd(old_rets), 'mdd_new': mdd(new_rets),
    }


def main():
    qqq_px = load_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    qqq_dates = sorted(qqq_px)
    macro_states = compute_states(qqq_dates, qqq_px)
    macro_by_date = dict(zip(qqq_dates, macro_states))

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

    common_kwargs = dict(spmo=spmo, tqqq=tqqq, qld=qld, xlu=xlu, gld=gld, cash_idx=cash_idx,
                          spmo_wk=spmo_wk, tqqq_wk=tqqq_wk, qld_wk=qld_wk, xlu_wk=xlu_wk, gld_wk=gld_wk,
                          cash_wk=cash_wk, keys=keys, floor=floor)

    pairs = [(10, 50), (10, 100), (10, 150), (15, 75), (20, 100), (20, 150), (30, 100), (30, 150), (40, 150)]

    print(f"{'micro':<9}{'#valid':>7}{'full old':>10}{'full new':>10}{'search old':>11}{'search new':>11}{'hold old':>10}{'hold new':>10}{'CAGR new':>10}{'MaxDD new':>11}  validated cells")
    for short_n, long_n in pairs:
        r = run_one_pair(short_n, long_n, qqq_px, qqq_dates, macro_by_date, common_kwargs)
        cells_str = ",".join(f"{s}{'A' if a else 'D'}" for s, a in r['validated_cells'])
        print(f"{r['pair']:<9}{r['n_validated']:>7}{r['full_sharpe_old']:>10.3f}{r['full_sharpe_new']:>10.3f}"
              f"{r['search_old']:>11.3f}{r['search_new']:>11.3f}{r['holdout_old']:>10.3f}{r['holdout_new']:>10.3f}"
              f"{r['cagr_new']*100:>9.2f}%{r['mdd_new']*100:>10.2f}%  {cells_str}")


if __name__ == '__main__':
    main()
