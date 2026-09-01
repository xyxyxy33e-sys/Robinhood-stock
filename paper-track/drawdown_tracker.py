"""Live drawdown-from-high tracker -- added 2026-09-01 for a manual
"add more money on a real dip" decision (the user is funding this account
periodically and wanted an objective trigger rather than reacting to a
single noisy day). Single-day moves are too frequent to be useful (QQQ
closes down >=2% about 14x/year, per this session's own check) -- this
tracks CUMULATIVE drawdown from a rolling high instead, which is far
rarer and a more meaningful signal (per the 2015-2026 backtest: the
strategy's own state-weighted daily series crossed -5% off its 52-week
high about 2.5x/year, -10% about 1.4x/year, -15% about 3 times in 10.9
years, -20% only once, the 2020-03 COVID crash). -5% is included at the
user's explicit request even though it's the noisiest tier -- treat a
-5% alert as a low-conviction "worth a look," the -10%+ tiers as the
higher-conviction signal.

Mechanism: each day the live daily trigger runs, it computes the
STRATEGY's own daily return (not QQQ's) -- yesterday's confirmed state's
weights applied to that day's leg returns (SPMO/IAU/TQQQ/QLD/XLU/BOXX),
same weighting the account is actually holding. This return is appended
to a small local index log (an independent, cash-flow-blind NAV index --
NOT the account's raw total_value, which would be distorted by deposits;
see record_return()'s docstring). Drawdown is measured against a rolling
252-trading-day high once the log has that much history, or an
all-time high before then (log starts empty 2026-09-01, so this
effectively runs as an all-time-high tracker for its first year).

This is READ-ONLY informational -- it never places a trade. The daily
trigger reports a threshold crossing to the user as a suggestion to
consider a manual deposit; it does not gate anything else.
"""
import csv
import os

LOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'live_nav_index.csv')
ROLLING_WINDOW = 252  # trading days, ~1 year -- switches from all-time to rolling once log is this long
# 5% included at the user's request despite being the noisiest tier (~2.5x/yr
# in backtest, vs ~1.4x/yr at 10%, ~0.3x/yr at 15%, ~0.1x/yr at 20%) -- treat
# a -5% alert as a low-conviction "worth a look," not the same signal as -10%+.
DD_THRESHOLDS = (0.05, 0.10, 0.15, 0.20)


def load_log():
    """Returns list of (date_str, daily_return, index_value) rows, oldest first."""
    if not os.path.exists(LOG_PATH):
        return []
    rows = []
    with open(LOG_PATH) as f:
        for r in csv.DictReader(f):
            rows.append((r['date'], float(r['daily_return']), float(r['index_value'])))
    return rows


def record_return(date, daily_return):
    """Append (or overwrite, if date already logged -- idempotent on retry) one
    day's STRATEGY return to the log, chaining the index off the prior row.
    This is a synthetic, cash-flow-blind return index -- NOT the account's
    total_value -- specifically so that a manual deposit (the whole point of
    this tracker) never itself looks like "a new high" or distorts the
    drawdown reading.

    daily_return must be yesterday's CONFIRMED state's weights dotted with each
    leg's official-close-to-official-close return, using
    **target_weights_with_voltarget(state, micro_agrees, vol)** -- i.e. the
    weights actually held, WITH the volatility overlay applied.

    CHANGED 2026-09-01: this previously used target_weights_with_micro(), the
    un-vol-targeted design return. That was wrong for this tracker's purpose.
    Its job is to answer "is this a real dip worth adding money to", so it has
    to describe the portfolio the user actually holds. Volatility targeting
    materially shrinks drawdowns (full-period MaxDD -41.6% vs -69.9%), so an
    un-vol-targeted series would fire the -5%/-10% tiers EARLIER and MORE
    OFTEN than the real account ever experienced -- alerting on a drawdown
    that isn't happening. Keep this in sync with whatever the live triggers
    actually trade.

    Returns the full updated log (list of rows) after writing.
    """
    rows = load_log()
    rows = [r for r in rows if r[0] != date]  # idempotent: drop any existing row for this date first
    prev_index = rows[-1][2] if rows else 1.0
    new_index = prev_index * (1 + daily_return)
    rows.append((date, daily_return, new_index))
    rows.sort(key=lambda r: r[0])
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['date', 'daily_return', 'index_value'])
        for r in rows:
            w.writerow(r)
    return rows


def current_drawdown(rows=None):
    """Drawdown of the latest logged index value from its rolling-252-day (or
    all-time, if log is shorter) high. Returns (drawdown_pct, peak_date,
    peak_value, latest_date, latest_value) or None if the log is empty.
    drawdown_pct is negative or zero (e.g. -0.12 for a 12% drawdown)."""
    if rows is None:
        rows = load_log()
    if not rows:
        return None
    window = rows[-ROLLING_WINDOW:] if len(rows) > ROLLING_WINDOW else rows
    peak_date, _, peak_value = max(window, key=lambda r: r[2])
    latest_date, _, latest_value = rows[-1]
    dd = latest_value / peak_value - 1
    return dd, peak_date, peak_value, latest_date, latest_value


def check_thresholds(dd_pct, thresholds=DD_THRESHOLDS):
    """Returns the deepest threshold in `thresholds` currently breached by
    dd_pct (a negative fraction), or None if none are. E.g. dd_pct=-0.11
    with the default thresholds returns 0.10."""
    breached = [t for t in thresholds if dd_pct <= -t]
    return max(breached) if breached else None


def newly_crossed(rows_before, rows_after, thresholds=DD_THRESHOLDS):
    """Compare drawdown state before vs after appending today's row -- returns
    the threshold newly breached TODAY that was NOT already breached
    yesterday (None if no new crossing, including if today recovered above a
    previously-breached level or was already below it yesterday). Use this to
    decide whether to flag the user -- alert once per crossing, not every day
    the account stays below a threshold."""
    dd_before = check_thresholds(current_drawdown(rows_before)[0]) if rows_before else None
    dd_after = check_thresholds(current_drawdown(rows_after)[0])
    if dd_after is not None and dd_after != dd_before:
        return dd_after
    return None


if __name__ == '__main__':
    rows = load_log()
    if not rows:
        print("No log yet -- paper-track/drawdown_tracker.record_return() hasn't been called.")
    else:
        dd, peak_date, peak_value, latest_date, latest_value = current_drawdown(rows)
        tier = check_thresholds(dd)
        print(f"Log: {len(rows)} days, {rows[0][0]} -> {rows[-1][0]}")
        print(f"Latest ({latest_date}): index={latest_value:.4f}, "
              f"peak ({peak_date})={peak_value:.4f}, drawdown={dd*100:.2f}%")
        print(f"Threshold tier: {'-' + str(int(tier*100)) + '%' if tier else 'none (within 5% of high)'}")
