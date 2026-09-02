"""Pick the rebalance DRIFT BAND for the volatility-targeting overlay.

WHY THIS EXISTS. Before vol targeting, live weights only moved on a regime
change, so "check daily, act on change" was exact. With vol targeting the
target moves a little EVERY day (the multiplier is min(1, target/realised_vol)),
so a daily "act on any difference" rule would trade constantly, and a
weekly-only rule can sit materially off-target for days during a fast vol
spike -- exactly when being off-target is most expensive.

A drift band fixes both: hold while the gap is noise, rebalance as soon as the
gap is real. This file measures the band rather than guessing it.

MODEL. Unlike the weekly backtests elsewhere in this repo, this one runs at
DAILY resolution and tracks HELD weights, which drift with differential leg
returns between rebalances:

    each trading day:
      held_i        <- held_i * (1 + r_i) / portfolio_growth      (drift)
      target        <- target_weights_with_voltarget(state, micro, vol)
      drift         <- sum_i |target_i - held_i|                  (L1 distance)
      if regime changed OR drift > BAND:  rebalance to target, pay cost
      else:                               hold

Cost is the same 4bps one-way model used project-wide, charged on realised
turnover (sum |new_i - held_i|), so a rule that trades more genuinely pays
more. NO trade threshold is applied: when a rebalance fires, every leg goes to
target (the $100/0.3% per-leg skip was removed 2026-09-01 at the user's
request -- a band on the WHOLE portfolio is the cleaner control, since it
gates on how wrong the portfolio actually is rather than on each leg's size).

BAND=0.0 reproduces "rebalance every day"; BAND=inf with the weekly flag
reproduces "weekly only". Both are reported as reference points.
"""
import math
import sys

sys.path.insert(0, 'paper-track')
from state import (compute_states, compute_micro_agreement, realized_vol,
                   target_weights_with_voltarget, VOL_TARGET_PA, VOL_LOOKBACK_DAYS)
from long_history_backtest import (load_px, load_tbill_long, make_rate_lookup,
                                   synth_leveraged, total_return_index, cash_index,
                                   stats, START, QQQ_DIV_PA, XLU_DIV_PA)

ONE_WAY_SPREAD = 0.0004


def build_daily(core_px, lev2, lev3, xlu_px, signal_px, rate_on, core_div=QQQ_DIV_PA):
    ds = sorted(core_px)
    core = total_return_index(core_px, core_div)
    xl = total_return_index(xlu_px, XLU_DIV_PA)
    cash = cash_index(ds, rate_on)
    sdates = sorted(signal_px)
    states = dict(zip(sdates, compute_states(sdates, signal_px)))
    micro = compute_micro_agreement(sdates, signal_px)

    rows = []
    for i in range(1, len(ds)):
        d0, d1 = ds[i - 1], ds[i]
        st, ag = states.get(d0), micro.get(d0)
        if st is None or ag is None or d0 < START:
            continue
        rows.append(dict(
            d=d0, state=st, agree=ag,
            vol=realized_vol(sdates, signal_px, as_of=d0, lookback=VOL_LOOKBACK_DAYS),
            legs=(core[d1] / core[d0] - 1, lev3[d1] / lev3[d0] - 1,
                  lev2[d1] / lev2[d0] - 1, xl[d1] / xl[d0] - 1,
                  cash[d1] / cash[d0] - 1),
        ))
    return rows


def simulate(rows, band=None, weekly_only=False):
    """Daily simulation with held-weight drift.

    band: rebalance when L1 drift from target exceeds this. band=0.0 -> every
          day. Ignored when weekly_only is True.
    weekly_only: rebalance on a regime change or on the last trading day of
          each ISO week, whatever the drift (reproduces the current draft).

    Returns (daily_net_returns, rebalances_per_year, turnover_per_year).
    """
    held = None
    prev_key = None
    rets, n_rebal, turnover = [], 0, 0.0

    for idx, r in enumerate(rows):
        target = target_weights_with_voltarget(r['state'], r['agree'], r['vol'])
        key = (r['state'], r['agree'])
        cost = 0.0

        if held is None:
            held = list(target)
            n_rebal += 1
        else:
            regime_changed = key != prev_key
            if weekly_only:
                last_of_week = (idx + 1 >= len(rows) or
                                _isofweek(rows[idx + 1]['d']) != _isofweek(r['d']))
                do_rebalance = regime_changed or last_of_week
            else:
                drift = sum(abs(target[j] - held[j]) for j in range(5))
                do_rebalance = regime_changed or drift > band
            if do_rebalance:
                t = sum(abs(target[j] - held[j]) for j in range(5))
                turnover += t
                cost = ONE_WAY_SPREAD * t
                held = list(target)
                n_rebal += 1

        gross = sum(held[j] * r['legs'][j] for j in range(5))
        rets.append(gross - cost)

        # carry held weights forward, drifting with realised leg returns
        denom = 1.0 + gross
        if denom > 0:
            held = [held[j] * (1 + r['legs'][j]) / denom for j in range(5)]
        prev_key = key

    yrs = len(rows) / 252.0
    return rets, n_rebal / yrs, turnover / yrs


def _isofweek(d):
    from datetime import date
    return date.fromisoformat(d).isocalendar()[:2]


def annual_stats(daily_rets):
    n = len(daily_rets)
    nav = 1.0
    for r in daily_rets:
        nav *= (1 + r)
    m = sum(daily_rets) / n
    v = (sum((x - m) ** 2 for x in daily_rets) / (n - 1)) ** 0.5
    peak = cur = 1.0
    mdd = 0.0
    for r in daily_rets:
        cur *= (1 + r)
        peak = max(peak, cur)
        mdd = min(mdd, cur / peak - 1)
    return nav ** (252.0 / n) - 1, (m * 252) / (v * math.sqrt(252)), mdd


def main():
    rate_on = make_rate_lookup(load_tbill_long())
    qqq = load_px('data/qqq_long_history.csv')
    xlu = load_px('data/xlu_long_history.csv')
    common = set(qqq) & set(xlu)          # QQQ history now runs past XLU's
    qqq = {d: v for d, v in qqq.items() if d in common}
    xlu = {d: v for d, v in xlu.items() if d in common}
    rows = build_daily(qqq, synth_leveraged(qqq, 2, 0.95, rate_on),
                       synth_leveraged(qqq, 3, 0.84, rate_on), xlu, qqq, rate_on)
    print(f"daily-cadence simulation, {rows[0]['d']}..{rows[-1]['d']}, {len(rows)} trading days")
    print(f"vol target {VOL_TARGET_PA*100:.0f}%, {VOL_LOOKBACK_DAYS}d lookback, "
          f"4bps cost, NO per-leg trade threshold\n")

    def report(label, rets, nreb, turn):
        c, s, m = annual_stats(rets)
        print(f"{label:<28}{c*100:>8.2f}%{s:>9.3f}{m*100:>9.1f}%{nreb:>12.1f}{turn:>11.2f}x")

    print(f"{'rule':<28}{'CAGR':>8}{'Sharpe':>9}{'MaxDD':>9}{'rebal/yr':>12}{'turn/yr':>11}")
    r, nb, tn = simulate(rows, weekly_only=True)
    report('weekly only (draft)', r, nb, tn)
    for band in (0.0, 0.01, 0.02, 0.03, 0.05, 0.075, 0.10, 0.15, 0.20, 0.30):
        r, nb, tn = simulate(rows, band=band)
        report(f'drift band {band*100:.0f}%' if band else 'every day (band 0%)', r, nb, tn)

    print("\n--- same, split by era ---")
    for nm, a, b in (('OOS 2000-2015', START, '2015-10-31'),
                     ('fitted 2015-2026', '2015-11-01', '2026-12-31')):
        sub = [x for x in rows if a <= x['d'] <= b]
        print(f"\n{nm} ({len(sub)} days)")
        print(f"{'rule':<28}{'CAGR':>8}{'Sharpe':>9}{'MaxDD':>9}{'rebal/yr':>12}{'turn/yr':>11}")
        r, nb, tn = simulate(sub, weekly_only=True)
        report('weekly only (draft)', r, nb, tn)
        for band in (0.02, 0.05, 0.10, 0.20):
            r, nb, tn = simulate(sub, band=band)
            report(f'drift band {band*100:.0f}%', r, nb, tn)


if __name__ == '__main__':
    main()
