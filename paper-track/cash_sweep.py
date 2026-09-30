"""Idle-cash sweep -- added 2026-09-30 (owner, after TQQQ paid a $224 dividend:
"I don't think it matters much but you should have a plan for it").

Dividends (and any other small cash: interest, fractional-sale leftovers)
land as idle buying power. The drift band never fires on them -- $224 is
0.04% of the account, far inside 5% L1 and under the 0.10% zero-leg sweep --
so without a rule they would sit idle until the next band trade.

The rule, run by the 15:50 routines on a NO-TRADE day only (a band or regime
trade already takes every leg to target, cash included):

  - idle cash below SWEEP_MIN ($100) stays put -- not worth an order;
  - above it, the cash buys the legs that are UNDER their dollar target, in
    proportion to each leg's shortfall. Legs whose target is 0 get nothing,
    so a dividend from a leg the strategy has cut is never reinvested into
    it (the reason DRIP stays off in this account). In E/F the only
    positive-target leg is BOXX, so the cash goes to BOXX.
  - not while a staged deposit plan is active (deposit_plan owns idle cash
    then), and not above UNEXPECTED_FRACTION (20%) of the account -- that is
    daily-prompt section 2a, which asks the owner first.

Why proportional to shortfall rather than to target weight: since
sum(target) = total = sum(positions) + cash, the positive shortfalls always
add up to at least the idle cash, so filling them moves the book toward
target and never away from it.

The NAV index stays price-return (it never counted dividends; neither do the
split-adjusted backtests it is compared with), so a sweep needs no NAV
adjustment. Each sweep is logged to data/cash_sweeps.csv.
"""
import csv
import os

LOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'cash_sweeps.csv')
SWEEP_MIN = 100.0            # dollars; below this idle cash waits for the next band trade
MIN_ORDER = 1.0              # Robinhood's dollar-based order minimum
UNEXPECTED_FRACTION = 0.20   # daily prompt 2a: ask the owner above this
LEGS = ('SPMO', 'TQQQ', 'QLD', 'XLU', 'BOXX')
FIELDS = ['date', 'idle_cash', 'total_value', 'SPMO', 'TQQQ', 'QLD', 'XLU', 'BOXX', 'note']


def plan_sweep(weights, values, idle_cash, total_value, plan_active=False):
    """weights: the 5-tuple from live_target_weights. values: leg -> market
    value (idle cash NOT included). Returns (orders, reason): orders is a
    dict leg -> dollars to buy (empty when nothing should be swept)."""
    if plan_active:
        return {}, 'deposit plan active: deposit_plan handles idle cash'
    if idle_cash < SWEEP_MIN:
        return {}, f'idle cash ${idle_cash:,.2f} below ${SWEEP_MIN:,.0f}'
    if idle_cash > UNEXPECTED_FRACTION * total_value:
        return {}, 'idle cash above 20% of the account: ask the owner (section 2a)'
    short = {l: max(0.0, w * total_value - values.get(l, 0.0))
             for l, w in zip(LEGS, weights) if w > 0}
    short = {l: s for l, s in short.items() if s > 0}
    while short:
        tot = sum(short.values())
        orders = {l: idle_cash * s / tot for l, s in short.items()}
        small = [l for l, d in orders.items() if d < MIN_ORDER]
        if not small:
            # round down to cents so the buys never exceed the cash
            return {l: int(d * 100) / 100 for l, d in orders.items()}, 'sweep'
        for l in small:
            del short[l]
    return {}, 'no leg below target'


def log_sweep(date, idle_cash, total_value, orders, note='', path=LOG_PATH):
    """Record one sweep (idempotent per date: a re-run replaces the row)."""
    rows = []
    if os.path.exists(path):
        with open(path) as f:
            rows = [r for r in csv.DictReader(f) if r['date'] != date]
    row = dict(date=date, idle_cash=round(idle_cash, 2), total_value=round(total_value, 2), note=note)
    row.update({l: round(orders.get(l, 0.0), 2) for l in LEGS})
    rows.append(row)
    rows.sort(key=lambda r: r['date'])
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    return row
