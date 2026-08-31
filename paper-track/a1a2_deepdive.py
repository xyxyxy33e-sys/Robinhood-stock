"""Deep-dive robustness check on the A1/A2 (QQQ realized-vol substate)
finding from substate_v2_check.py: +0.121 Sharpe on search, +0.020 on
holdout, no cash lever involved. Before trusting this further than "worth
watching," this checks the things that have burned this project before:

1. Sensitivity to the two free choices (rolling-percentile lookback window,
   percentile threshold) -- a real effect should not require the exact
   252-day/75th-percentile combo to show up.
2. Whether a genuine grid search (not just the proposed 55/45 vs 85/15
   weights) finds similar optima on each half, and whether THAT holds up
   search->holdout.
3. Confound check: does the A1/A2 split correlate with calendar era, or
   with which state follows (a proxy for "is this secretly the transition
   structure in disguise")?
4. Placebo check: how often does a RANDOM split of A's weeks (same n1/n2
   sizes) clear the same Sharpe-improvement bar by chance?
"""
import math
import random
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import compute_states, STATE_LABEL
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
from four_leg_overlay import last_trading_day_per_week

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
SEARCH_HOLDOUT_SPLIT = '2020-01-01'
BASE_A = (0.80, 0.20, 0.00)


def sharpe(rets):
    if len(rets) < 4:
        return None
    mean_r = sum(rets) / len(rets)
    var = sum((r - mean_r) ** 2 for r in rets) / (len(rets) - 1)
    if var <= 0:
        return None
    vol = math.sqrt(var) * math.sqrt(52.1775)
    return (mean_r * 52.1775) / vol


def qqq_realized_vol_20d(qqq_px, qqq_dates):
    rets = {}
    for i in range(1, len(qqq_dates)):
        d0, d1 = qqq_dates[i - 1], qqq_dates[i]
        rets[d1] = math.log(qqq_px[d1] / qqq_px[d0])
    vol = {}
    ordered = [(d, rets[d]) for d in qqq_dates if d in rets]
    for i in range(19, len(ordered)):
        window = [r for _, r in ordered[i - 19:i + 1]]
        mean_r = sum(window) / len(window)
        var = sum((r - mean_r) ** 2 for r in window) / (len(window) - 1)
        vol[ordered[i][0]] = math.sqrt(var) * math.sqrt(252)
    return vol


def rolling_percentile(values, dates, lookback):
    out = {}
    ordered = [(d, values[d]) for d in dates if d in values]
    for i, (d, v) in enumerate(ordered):
        window = [x for _, x in ordered[max(0, i - lookback):i]]
        if len(window) < 60:
            continue
        rank = sum(1 for w in window if w <= v) / len(window)
        out[d] = rank
    return out


def nearest_prior(d_map, d, floor):
    dd = d
    while dd not in d_map and dd > floor:
        dd = (date.fromisoformat(dd) - timedelta(days=1)).isoformat()
    return d_map.get(dd)


def build_rows(qqq, spmo, tqqq, cash_idx, state_by_date, qqq_dates, vol_pct):
    spmo_wk = last_trading_day_per_week(sorted(set(spmo)))
    tqqq_wk = last_trading_day_per_week(sorted(set(tqqq)))
    cash_wk = last_trading_day_per_week(sorted(set(cash_idx)))
    keys = sorted(set(spmo_wk) & set(tqqq_wk) & set(cash_wk))
    keys = [k for k in keys if spmo_wk[k] >= '2015-11-02']
    rows = []
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        w0, w1 = spmo_wk[k0], spmo_wk[k1]
        t0, t1 = tqqq_wk[k0], tqqq_wk[k1]
        c0, c1 = cash_wk[k0], cash_wk[k1]
        sd = w0
        while sd not in state_by_date and sd > qqq_dates[0]:
            sd = (date.fromisoformat(sd) - timedelta(days=1)).isoformat()
        st = state_by_date.get(sd)
        if st is None:
            continue
        vp = nearest_prior(vol_pct, sd, qqq_dates[0])
        rows.append((w1, st, spmo[w1] / spmo[w0] - 1, tqqq[t1] / tqqq[t0] - 1, cash_idx[c1] / cash_idx[c0] - 1, vp, sd))
    return rows


def flat_weight(st):
    if st == 'A':
        return BASE_A
    if st == 'B':
        return (0.25, 0.75, 0.0)
    return (1.0, 0.0, 0.0)


def scheme_rets(rows, a_weight_fn):
    out = []
    for w1, st, rc, rt, rca, vp, sd in rows:
        if st == 'A':
            cw, tw, chw = a_weight_fn(vp)
        else:
            cw, tw, chw = flat_weight(st)
        out.append(cw * rc + tw * rt + chw * rca)
    return out


def eval_split(rows, threshold, w_low=(0.55, 0.45, 0.0), w_high=(0.85, 0.15, 0.0)):
    def a_weight(vp):
        return w_low if (vp is not None and vp < threshold) else w_high
    rets = scheme_rets(rows, a_weight)
    flat_rets = scheme_rets(rows, lambda vp: BASE_A)
    wks = [r[0] for r in rows]
    pre = [i for i, w in enumerate(wks) if w < SEARCH_HOLDOUT_SPLIT]
    post = [i for i, w in enumerate(wks) if w >= SEARCH_HOLDOUT_SPLIT]
    d_full = sharpe(rets) - sharpe(flat_rets)
    d_pre = sharpe([rets[i] for i in pre]) - sharpe([flat_rets[i] for i in pre])
    d_post = sharpe([rets[i] for i in post]) - sharpe([flat_rets[i] for i in post])
    return d_full, d_pre, d_post


def main():
    qqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    spmo = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPMO.csv')
    tqqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/TQQQ.csv')
    boxx = load_daily_csv(f'{ROBINHOOD_REPO}/etf/BOXX.csv')
    tbill = load_tbill()
    qqq_dates = sorted(qqq)
    states = compute_states(qqq_dates, qqq)
    state_by_date = dict(zip(qqq_dates, states))
    vol20 = qqq_realized_vol_20d(qqq, qqq_dates)
    all_dates = sorted(set(qqq) | set(tqqq) | set(spmo))
    cash_idx = build_cash_index(all_dates, boxx, tbill)

    print("=== 1. Sensitivity to lookback window and percentile threshold ===")
    print("     (delta = substate Sharpe - flat-A(80/20) Sharpe; full / search(pre-20) / holdout(post-20))")
    for lookback in (126, 189, 252, 378, 504):
        vol_pct = rolling_percentile(vol20, qqq_dates, lookback)
        rows = build_rows(qqq, spmo, tqqq, cash_idx, state_by_date, qqq_dates, vol_pct)
        for thr in (0.60, 0.70, 0.75, 0.80, 0.90):
            d_full, d_pre, d_post = eval_split(rows, thr)
            a_rows = [r for r in rows if r[1] == 'A' and r[5] is not None]
            n_high = sum(1 for r in a_rows if r[5] >= thr)
            n_high_search = sum(1 for r in a_rows if r[5] >= thr and r[0] < SEARCH_HOLDOUT_SPLIT)
            print(f"  lookback={lookback:>3}d thr={thr:.2f}  n_high={n_high:>3} (search={n_high_search:>3})  "
                  f"d_full={d_full:+.3f}  d_search={d_pre:+.3f}  d_holdout={d_post:+.3f}")
        print()

    print("=== 2. Grid search each half's own optimal weight (252d/75th, the base case) ===")
    vol_pct = rolling_percentile(vol20, qqq_dates, 252)
    rows = build_rows(qqq, spmo, tqqq, cash_idx, state_by_date, qqq_dates, vol_pct)
    a_rows = [r for r in rows if r[1] == 'A' and r[5] is not None]
    a1 = [r for r in a_rows if r[5] < 0.75]
    a2 = [r for r in a_rows if r[5] >= 0.75]
    for label, subset in (('A1 (low vol)', a1), ('A2 (high vol)', a2)):
        search = [r for r in subset if r[0] < SEARCH_HOLDOUT_SPLIT]
        holdout = [r for r in subset if r[0] >= SEARCH_HOLDOUT_SPLIT]
        best = None
        for i in range(11):
            cw = round(i * 0.1, 2)
            tw = round(1 - cw, 2)
            rets = [cw * r[2] + tw * r[3] for r in search]
            sh = sharpe(rets)
            if sh is not None and (best is None or sh > best[2]):
                best = (cw, tw, sh)
        holdout_rets_best = [best[0] * r[2] + best[1] * r[3] for r in holdout]
        print(f"  {label}: n_search={len(search)} n_holdout={len(holdout)}  "
              f"search-optimal core/tqqq={best[0]:.1f}/{best[1]:.1f} (search-Sharpe={best[2]:.3f})  "
              f"applied-to-holdout Sharpe={sharpe(holdout_rets_best)}")
    print()

    print("=== 3. Confound check: calendar distribution + next-state distribution ===")
    for label, subset in (('A1 (low vol)', a1), ('A2 (high vol)', a2)):
        years = {}
        for r in subset:
            y = r[0][:4]
            years[y] = years.get(y, 0) + 1
        print(f"  {label} (n={len(subset)}) by year: {dict(sorted(years.items()))}")
    # next-state: for each A-week, what state follows (use sd date, find next week's state)
    a_dates_sorted = sorted(set(r[6] for r in a_rows))
    date_to_state = state_by_date
    def next_state_after(sd):
        idx = qqq_dates.index(sd) if sd in qqq_dates else None
        if idx is None:
            return None
        for j in range(idx + 1, min(idx + 8, len(qqq_dates))):
            nd = qqq_dates[j]
            if date_to_state.get(nd) != 'A':
                return date_to_state.get(nd)
        return 'A'
    for label, subset in (('A1', a1), ('A2', a2)):
        nxt = {}
        for r in subset:
            ns = next_state_after(r[6])
            nxt[ns] = nxt.get(ns, 0) + 1
        total = sum(nxt.values())
        pct = {k: f"{v/total*100:.0f}%" for k, v in sorted(nxt.items(), key=lambda x: -x[1])}
        print(f"  {label} next-state-within-week distribution: {pct}")
    print()

    print("=== 4. Placebo check: random split of A's weeks (same n1/n2), 500 trials ===")
    random.seed(42)
    n1, n2 = len(a1), len(a2)
    beat_full = beat_both = 0
    trials = 500
    for _ in range(trials):
        shuffled = a_rows[:]
        random.shuffle(shuffled)
        r1, r2 = shuffled[:n1], shuffled[n1:]
        def rand_weight(vp, r1_set):
            return None
        # build rets manually using membership
        r1_ids = set(id(x) for x in r1)
        def a_weight_rand(row):
            return (0.55, 0.45, 0.0) if id(row) in r1_ids else (0.85, 0.15, 0.0)
        rets = []
        for row in rows:
            if row[1] == 'A':
                cw, tw, chw = a_weight_rand(row) if row in a_rows else BASE_A
            else:
                cw, tw, chw = flat_weight(row[1])
            rets.append(cw * row[2] + tw * row[3] + chw * row[4])
        flat_rets = scheme_rets(rows, lambda vp: BASE_A)
        wks = [r[0] for r in rows]
        pre = [i for i, w in enumerate(wks) if w < SEARCH_HOLDOUT_SPLIT]
        post = [i for i, w in enumerate(wks) if w >= SEARCH_HOLDOUT_SPLIT]
        d_full = sharpe(rets) - sharpe(flat_rets)
        d_pre = sharpe([rets[i] for i in pre]) - sharpe([flat_rets[i] for i in pre])
        d_post = sharpe([rets[i] for i in post]) - sharpe([flat_rets[i] for i in post])
        if d_full > 0.050:
            beat_full += 1
        if d_pre > 0.121 and d_post > 0.020:
            beat_both += 1
    print(f"  random splits beating actual full-timeline delta (+0.050): {beat_full}/{trials} ({beat_full/trials*100:.1f}%)")
    print(f"  random splits beating BOTH actual search(+0.121) AND holdout(+0.020): {beat_both}/{trials} ({beat_both/trials*100:.1f}%)")


if __name__ == '__main__':
    main()
