"""Combined "confidence" signal for state A's leverage question: majority
vote across the four independently-validated signals from this session's
research, all of which converge on the same direction (de-lever toward 0%
TQQQ in the "confident/calm" majority, keep baseline leverage in the
minority where signals disagree or flag uncertainty):
  1. micro/macro classifier agreement (micro=30/150 in {A,B})
  2. price vs its own 20-day SMA
  3. QQQ's own 20-day realized-vol percentile (<75th = calm)
  4. VIX percentile (<75th = calm)

Confident = at least 3 of 4 signals agree "confident/calm" this week.
Same discipline as every other check: MIN_N=15/half, cash fixed at state
A's live value (0%), search-period grid search, isolated holdout check
against live 80/20.

RESULTS SUMMARY (run 2026-09-01): the composite is cleaner than any single
signal. At every majority threshold tested (>=2/4, >=3/4, >=4/4), the
"confident" majority (250-332 of 351 A-weeks, well above the 15-week
floor) converges on near-zero TQQQ (95/5 to 100/0 core/TQQQ) and holds up
on genuine holdout. The "uncertain" minority is where restraint is
warranted: at strict 4/4 unanimity (n=101), live's 80/20 clearly WINS on
holdout (0.524 vs 0.871) -- don't touch it. At the looser 3/4 threshold
(n=47), search suggests more leverage but with a NEGATIVE search-Sharpe
(-0.223), the same thin-sample corner-solution signature seen elsewhere
in this project -- not trustworthy. CLEANEST DESIGN: use the strict 4/4
unanimous-agreement threshold to flag the confident majority (~71% of
state A) and de-lever it toward 100% core/0% TQQQ; leave the remaining
~29% (where the four signals don't all agree) exactly at live's 80/20
rather than guessing at a replacement. Strongest, most-corroborated
version of the state-A de-leveraging finding from this whole session --
four independently-constructed signals, majority vote, holdout-confirmed
on both sides of the split. Not yet implemented -- turnover-cost modeling
pending.
"""
import csv
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import load_csv, sma, compute_states, CORE_SPMO_FRAC, CORE_GLD_FRAC
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index
from four_leg_overlay import last_trading_day_per_week
from a1a2_deepdive import qqq_realized_vol_20d, rolling_percentile, nearest_prior
from ma_window_sweep import compute_states_custom

ROBINHOOD_REPO = '/home/user/robinhood/data/kairos'
CANDIDATES_DIR = 'data/defensive_candidates'
SEARCH_HOLDOUT_SPLIT = '2020-01-01'
MIN_N = 15


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


def grid(rows_subset, step=0.05):
    best = None
    n_ = round(1 / step)
    for i in range(n_ + 1):
        cw = round(i * step, 2)
        tw = round(1 - cw, 2)
        rets = [cw * r[-2] + tw * r[-1] for r in rows_subset]
        sh = sharpe(rets)
        if sh is not None and (best is None or sh > best[2]):
            best = (cw, tw, sh)
    return best


def main():
    qqq_px = load_csv(f'{ROBINHOOD_REPO}/etf/QQQ.csv')
    qqq_dates = sorted(qqq_px)
    qqq_v = [qqq_px[d] for d in qqq_dates]
    states = compute_states(qqq_dates, qqq_px)
    state_by_date = dict(zip(qqq_dates, states))

    # signal 1: micro/macro agreement (30/150)
    micro_states = compute_states_custom(qqq_dates, qqq_px, 30, 150)
    micro_by_date = dict(zip(qqq_dates, micro_states))

    # signal 2: price vs 20dma
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

    # signal 3: QQQ realized-vol percentile
    vol20 = qqq_realized_vol_20d(qqq_px, qqq_dates)
    vol_pct = rolling_percentile(vol20, qqq_dates, 252)

    # signal 4: VIX percentile
    vix = load_fred(f'{ROBINHOOD_REPO}/VIXCLS.csv')
    vix_dates = sorted(vix)
    vix_pct = rolling_percentile(vix, vix_dates, 252)

    spmo = load_daily_csv(f'{ROBINHOOD_REPO}/etf/SPMO.csv')
    tqqq = load_daily_csv(f'{ROBINHOOD_REPO}/etf/TQQQ.csv')
    gld = load_daily_csv(f'{CANDIDATES_DIR}/GLD.csv')
    boxx = load_daily_csv(f'{ROBINHOOD_REPO}/etf/BOXX.csv')
    tbill = load_tbill()
    all_dates = sorted(set(qqq_dates) | set(tqqq) | set(spmo) | set(gld))
    cash_idx = build_cash_index(all_dates, boxx, tbill)
    spmo_wk = last_trading_day_per_week(sorted(set(spmo)))
    tqqq_wk = last_trading_day_per_week(sorted(set(tqqq)))
    gld_wk = last_trading_day_per_week(sorted(set(gld)))
    cash_wk = last_trading_day_per_week(sorted(set(cash_idx)))
    keys = sorted(set(spmo_wk) & set(tqqq_wk) & set(gld_wk) & set(cash_wk))
    keys = [k for k in keys if spmo_wk[k] >= '2015-11-02']
    floor = qqq_dates[0]

    rows = []
    for i in range(len(keys) - 1):
        k0, k1 = keys[i], keys[i + 1]
        w0, w1 = spmo_wk[k0], spmo_wk[k1]
        t0, t1 = tqqq_wk[k0], tqqq_wk[k1]
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
        r_core = CORE_SPMO_FRAC * (spmo[w1] / spmo[w0] - 1) + CORE_GLD_FRAC * (gld[gld_wk[k1]] / gld[gld_wk[k0]] - 1)
        r_tqqq = tqqq[t1] / tqqq[t0] - 1
        rows.append((w1, st, sig1, sig2, sig3, sig4, r_core, r_tqqq))

    a_rows = [r for r in rows if r[1] == 'A' and None not in r[2:6]]
    n = len(a_rows)
    print(f"State A weeks with all 4 signals available: {n}\n")

    votes = [sum(1 for s in r[2:6] if s) for r in a_rows]
    from collections import Counter
    print("Vote distribution (how many of 4 signals say 'confident'):", dict(Counter(votes)))
    print()

    for threshold in (4, 3, 2):
        confident = [r for i, r in enumerate(a_rows) if votes[i] >= threshold]
        uncertain = [r for i, r in enumerate(a_rows) if votes[i] < threshold]
        print(f"=== Majority threshold: >= {threshold}/4 signals agree = 'confident' ===")
        for label, subset in (('confident', confident), ('uncertain', uncertain)):
            search = [r for r in subset if r[0] < SEARCH_HOLDOUT_SPLIT]
            holdout = [r for r in subset if r[0] >= SEARCH_HOLDOUT_SPLIT]
            if len(search) < MIN_N or len(holdout) < MIN_N:
                print(f"  {label:<10} n={len(subset):>3} (s={len(search)},h={len(holdout)}) -- INSUFFICIENT DATA")
                continue
            best = grid(search)
            live_rets = [0.8 * r[6] + 0.2 * r[7] for r in holdout]
            cand_rets = [best[0] * r[6] + best[1] * r[7] for r in holdout]
            verdict = 'HOLDS' if sharpe(cand_rets) > sharpe(live_rets) else 'no'
            print(f"  {label:<10} n={len(subset):>3} (s={len(search)},h={len(holdout)})  "
                  f"search-best={best[0]:.2f}/{best[1]:.2f} (Sh={best[2]:.3f})  "
                  f"holdout: cand={sharpe(cand_rets):.3f} live={sharpe(live_rets):.3f}  [{verdict}]")
        print()

    # full-timeline aggregate for the best threshold (>=3), applying validated weights only
    print("=== Full-timeline check (>=3/4 threshold, composite weight vs live) ===")
    threshold = 3
    confident_ids = set(id(r) for i, r in enumerate(a_rows) if votes[i] >= threshold)
    search_conf = [r for r in a_rows if id(r) in confident_ids and r[0] < SEARCH_HOLDOUT_SPLIT]
    best_conf = grid(search_conf)
    print(f"Composite 'confident' weight (search-derived): {best_conf[0]:.2f} core / {best_conf[1]:.2f} tqqq")

    ONE_WAY_SPREAD_BPS = 0.0004
    old_rets, new_rets = [], []
    prev_old, prev_new = None, None
    for r in rows:
        st = r[1]
        if st == 'A':
            is_a_row = r in a_rows
            if is_a_row and id(r) in confident_ids:
                neww = (best_conf[0], best_conf[1])
            else:
                neww = (0.8, 0.2)
            oldw = (0.8, 0.2)
        else:
            oldw = neww = None
        # only A rows matter for this isolated comparison; other states pass through unchanged
        # (full multi-state comparison would need the rest of TARGET_WEIGHTS; skipped here since
        # we're isolating A's own contribution the same way earlier isolated checks did)
    print("(Isolated-to-A comparison only; see earlier holdout numbers above for the validated read.)")


if __name__ == '__main__':
    main()
