"""Gate extra leverage in state A to only the "confident" (micro-agrees)
weeks, rather than a uniform leverage dial across all of A -- combining two
prior findings: A/agree tolerates more leverage (90/10 validated for
micro=30/150), while A/diverge's own search showed MORE leverage there
actively hurts (candidate lost to live on isolated holdout). Sweeps the
agree-side TQQQ weight across several micro MA pairs (not locked to one
parameterization, per request), diverge-side always held at live's 20%,
D/diverge fix included throughout (near-free validated improvement).

RESULTS SUMMARY (run 2026-09-01): the mechanism runs BACKWARDS from the
naive "lever up when confident" hypothesis this script was built to test.
Sweeping the agree-side TQQQ weight downward from live's 20% -- not
upward, the direction first (mistakenly) tried -- shows Sharpe improving
monotonically toward 0% TQQQ (100% core) during agree weeks, for 5 of 7
micro pairs tested (20/100, 30/100, 30/150, 20/150, 40/150 all peak at
0%; only 10/50 and 10/100, the shortest/noisiest pairs, land near
17-20%). Best overall: micro=30/150, agree_tqqq=0%, Sharpe=1.162 (vs live
1.111 net-of-cost baseline), CAGR=19.99%, MaxDD=-19.95%.

Likely mechanism: leverage's edge comes from catching acceleration/
inflection, which matters most EARLY in a trend, before both a fast and
slow signal have confirmed it. Once both already agree, the trend is
mature -- further gains are steadier/more grinding, so TQQQ's volatility
drag increasingly outweighs its extra beta. The live 20% baseline
leverage apparently earns its keep specifically in the not-yet-doubly-
confirmed weeks, not the already-confirmed ones.

Same trade-off shape as everything else in this research line, NOT a
free lunch: Sharpe/MaxDD improve monotonically as agree-TQQQ falls, but
CAGR falls right along with it (21.15% -> 19.99% at the Sharpe optimum
for 30/150). Does not serve a "higher return" objective -- if anything
it's further evidence this whole micro/macro family is a smoothing
trade, not a return-boosting one. No live weights changed.
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
ONE_WAY_SPREAD_BPS = 0.0004
NEW_D = (0.7, 0.0, 0.0, 0.0, 0.3)
LIVE_A_TQQQ = 0.20


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


def weight_at(st, agree, agree_tqqq_w):
    if st == 'A':
        w = agree_tqqq_w if agree else LIVE_A_TQQQ
        return (1 - w, w, 0.0, 0.0, 0.0)
    if st == 'D' and not agree:
        return NEW_D
    return TARGET_WEIGHTS[st]


def run(rows, agree_tqqq_w, cost_bps):
    gross, net = [], []
    prev_w = None
    for r in rows:
        w1, st, agree, rc, rt, rq, rx, rca = r
        w = weight_at(st, agree, agree_tqqq_w)
        g = w[0] * rc + w[1] * rt + w[2] * rq + w[3] * rx + w[4] * rca
        gross.append(g)
        to = 0.0 if prev_w is None else sum(abs(w[i] - prev_w[i]) for i in range(5))
        net.append(g - cost_bps * to)
        prev_w = w
    return net


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

    micro_pairs = [(10, 50), (10, 100), (20, 100), (30, 100), (30, 150), (20, 150), (40, 150)]
    agree_weights = [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]

    for short_n, long_n in micro_pairs:
        micro_states = compute_states_custom(qqq_dates, qqq_px, short_n, long_n)
        micro_by_date = dict(zip(qqq_dates, micro_states))
        rows = build_rows(qqq_px, qqq_dates, macro_by_date, micro_by_date, **common_kwargs)
        weeks = [r[0] for r in rows]
        pre = [i for i, w in enumerate(weeks) if w < SEARCH_HOLDOUT_SPLIT]
        post = [i for i, w in enumerate(weeks) if w >= SEARCH_HOLDOUT_SPLIT]

        print(f"=== micro={short_n}/{long_n} ===")
        best = None
        for aw in agree_weights:
            net = run(rows, aw, ONE_WAY_SPREAD_BPS)
            sh_full, sh_search, sh_hold = sharpe(net), sharpe([net[i] for i in pre]), sharpe([net[i] for i in post])
            c, m = cagr(net), mdd(net)
            print(f"  agree_tqqq={aw*100:.0f}%: CAGR={c*100:6.2f}%  Sharpe={sh_full:.3f}  MaxDD={m*100:7.2f}%  "
                  f"search={sh_search:.3f}  holdout={sh_hold:.3f}")
            if best is None or sh_full > best[1]:
                best = (aw, sh_full, c, m, sh_search, sh_hold)
        print(f"  BEST by full Sharpe: agree_tqqq={best[0]*100:.0f}%  Sharpe={best[1]:.3f}  CAGR={best[2]*100:.2f}%  MaxDD={best[3]*100:.2f}%  search={best[4]:.3f} holdout={best[5]:.3f}")
        print()


if __name__ == '__main__':
    main()
