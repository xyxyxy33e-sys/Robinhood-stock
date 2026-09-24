"""Staged deployment of a large deposit -- added 2026-09-24 (owner: "keep 40/60,
do 4 weekly tranches" for a $400k deposit into a ~$218k account).

The strategy's weights are unchanged. This module only decides how much of the
account the weights apply to while a planned deposit is being fed in. The
money not yet released (the RESERVE) sits in BOXX, outside the strategy:

    investable      = total_value - reserve
    dollar target   = weight x investable, per leg; BOXX gets + reserve on top
    held weights    = leg value / investable; the cash leg is
                      (BOXX + idle cash - reserve) / investable

With no active plan (the file is missing, or status 'complete') reserve = 0 and
every formula collapses to the normal one, so the routines stay correct
whether or not a plan is running.

Schedule (owner, 2026-09-24: "stage from today" -- the first $100k landed
before the plan was wired). The deposit is recognised when it lands (idle
cash above ARRIVAL_MIN while the plan is active); it may arrive in pieces.
The session of the FIRST arrival is session 0 and releases tranche 1;
tranche k releases on session 5(k-1). Sessions are counted on the QQQ
daily-bar dates the routine already has, so holidays count correctly. Each
tranche is planned_total / tranches ($100k), capped by what has actually
arrived: money that lands after its tranche date is released at once, and
money that lands early waits in the reserve for its date.

Why staged at all (deposit_staging_backtest.py, 2026-09-24, every start day,
value 126 sessions later, $400k): lump on day 0 beats 4 x weekly 68% of the
time on the real 2015-2026 window (62% on the 2000-2026 proxy), for a median
cost of $3.6k real / $1.4k proxy; the staged plan's worst case is $6k real /
$13k proxy better. This buys less regret, not more expected return.

Evidence for the backtest: see STRATEGY.md "Staged deposit (2026-09-24)".
"""
import json
import os

PLAN_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'deposit_plan.json')
ARRIVAL_MIN = 1000.0       # idle cash below this is rounding / dividends, not the deposit
ARRIVED_FRACTION = 0.95    # the plan completes once all tranches are out and this share has landed
OVERSIZE = 1.10            # arrivals beyond this x planned are NOT this plan -- ask the owner


def load(path=PLAN_PATH):
    """The plan dict, or None when there is no plan file."""
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def save(plan, path=PLAN_PATH):
    with open(path, 'w') as f:
        json.dump(plan, f, indent=2)
        f.write('\n')


def active(plan):
    return bool(plan) and plan.get('status') in ('awaiting_deposit', 'deploying')


def arrived_total(plan):
    return sum(a['amount'] for a in plan.get('arrived', [])) if plan else 0.0


def record_arrival(plan, date, amount):
    """Log money that landed on `date`. Idempotent for a date: a re-run replaces
    that date's figure instead of adding it twice. The first arrival starts
    the tranche clock. Returns the plan (mutated). Raises ValueError if the
    total would exceed OVERSIZE x planned -- that is not this plan's money and
    the normal 'ask the owner' rule applies."""
    if plan.get('status') not in ('awaiting_deposit', 'deploying'):
        raise ValueError(f"plan is {plan.get('status')}; no arrivals expected")
    if plan.get('start_date') and date < plan['start_date']:
        raise ValueError("arrival dated before the tranche clock started")
    arr = [a for a in plan.setdefault('arrived', []) if a['date'] != date]
    arr.append({'date': date, 'amount': round(float(amount), 2)})
    arr.sort(key=lambda a: a['date'])
    total = sum(a['amount'] for a in arr)
    if total > plan['planned_total'] * OVERSIZE:
        raise ValueError(f"arrivals ${total:,.0f} exceed {OVERSIZE:.2f} x the planned "
                         f"${plan['planned_total']:,.0f}; ask the owner")
    plan['arrived'] = arr
    if not plan.get('start_date'):
        plan['start_date'] = arr[0]['date']
        plan['status'] = 'deploying'
    return plan


def session_index(plan, session_dates, today):
    """Sessions since the start date (start = 0), counted on `session_dates`
    (the QQQ daily-bar dates, today included). None before the clock starts."""
    s = plan.get('start_date') if plan else None
    if not s or today < s:
        return None
    return sum(1 for d in set(session_dates) | {today} if s <= d <= today) - 1


def tranches_released(plan, session_dates, today):
    n = session_index(plan, session_dates, today)
    if n is None:
        return 0
    return min(plan['tranches'], n // plan['every_sessions'] + 1)


def reserve(plan, session_dates, today):
    """Dollars held back from the strategy today (0 when no plan is active)."""
    if not active(plan):
        return 0.0
    pool = arrived_total(plan)
    k = tranches_released(plan, session_dates, today)
    return round(max(0.0, pool - k * tranche_size(plan)), 2)


def tranche_size(plan):
    return plan['planned_total'] / plan['tranches']


def next_release(plan, session_dates, today):
    """(tranche number, sessions from today) of the next release, or None."""
    if not active(plan):
        return None
    k = tranches_released(plan, session_dates, today)
    if k >= plan['tranches']:
        return None
    if plan.get('start_date') is None:
        return (1, None)          # waits on the deposit, not on the calendar
    n = session_index(plan, session_dates, today)
    return (k + 1, k * plan['every_sessions'] - n)


def held_weights(values, idle_cash, total_value, res):
    """values: dict SPMO/TQQQ/QLD/XLU/BOXX -> market value. Returns the 5-tuple
    of held weights of the INVESTABLE account (reserve removed from the cash
    leg)."""
    inv = total_value - res
    if inv <= 0:
        raise ValueError("reserve is larger than the account")
    cash_leg = values.get('BOXX', 0.0) + idle_cash - res
    return (values.get('SPMO', 0.0) / inv, values.get('TQQQ', 0.0) / inv,
            values.get('QLD', 0.0) / inv, values.get('XLU', 0.0) / inv, cash_leg / inv)


def dollar_targets(weights, total_value, res):
    """weights: the 5-tuple from live_target_weights. Returns dollar targets per
    leg; BOXX carries the reserve on top of its strategy weight. Sums to
    total_value, i.e. no idle cash is left."""
    inv = total_value - res
    legs = ('SPMO', 'TQQQ', 'QLD', 'XLU', 'BOXX')
    out = {l: w * inv for l, w in zip(legs, weights)}
    out['BOXX'] += res
    return out


def mark_complete_if_done(plan, session_dates, today):
    """Flip status to 'complete' once the last tranche date has passed AND at
    least ARRIVED_FRACTION of the planned total has landed (until then a late
    piece is still this plan's money, released at once). The routine calls
    this after trading and commits the file."""
    if plan and plan.get('status') == 'deploying' and \
            tranches_released(plan, session_dates, today) >= plan['tranches'] and \
            arrived_total(plan) >= plan['planned_total'] * ARRIVED_FRACTION:
        plan['status'] = 'complete'
        plan['completed'] = today
    return plan


def log_release(plan, today, tranche, amount):
    """Record that the routine traded a release (idempotent per tranche)."""
    rel = [r for r in plan.setdefault('released', []) if r['tranche'] != tranche]
    rel.append({'tranche': tranche, 'date': today, 'amount': round(float(amount), 2)})
    plan['released'] = sorted(rel, key=lambda r: r['tranche'])
    return plan


def summary_line(plan, session_dates, today):
    if not plan:
        return "deposit plan: none"
    if plan.get('status') == 'complete':
        return f"deposit plan: complete ({plan.get('completed')}), ${arrived_total(plan):,.0f} deployed"
    res = reserve(plan, session_dates, today)
    k = tranches_released(plan, session_dates, today)
    nxt = next_release(plan, session_dates, today)
    if plan.get('start_date') is None:
        return f"deposit plan: awaiting the first deposit (${plan['planned_total']:,.0f} planned)"
    got = arrived_total(plan)
    tail = f"; tranche {nxt[0]} in {nxt[1]} session(s)" if nxt else ""
    return (f"deposit plan: {k}/{plan['tranches']} tranche dates passed, ${got:,.0f} of "
            f"${plan['planned_total']:,.0f} arrived, ${got - res:,.0f} deployed, reserve ${res:,.0f} in BOXX{tail}")
