"""Margin-funded drawdown deposits -- added 2026-10-13 (owner decision).

The owner funds the funding-policy events (funding_policy.py: each newly
crossed 5% drawdown tier, and each D/E/F -> A/B/C turn) with a MARGIN LOAN in
the individual account ending 6826 instead of outside cash, and wants a rule
with a repayment plan. Owner, 2026-10-13: "I want the rule to be based on a
margin, so confident in the future, and has an exit/repay plan"; the 6826
VTI/VXUS dip-buy margin plan is dropped ("I don't intend to use margin for
vti/vxus"); repay rule and cap left to the runner ("pick your own").

THE RULE
  Draw.   At a funding event, borrow the funding_policy amount in 6826 and
          transfer it to Agentic; it lands as idle cash and the cash sweep
          invests it. Each draw is capped so the loan outstanding never
          exceeds CAP = min(4% of the Agentic account, 25% of the 6826
          collateral). Draws while a loan is open stack on it.
  Repay.  The whole loan (principal + accrued interest) is repaid at the
          first of:
            - RECOVERY: the strategy NAV index closes at or above the
              252-day high it had before the loan's first draw;
            - DEADLINE: 252 sessions (12 months) after the first draw.
          On the repay day the trade run holds the repay amount back as cash
          (sells to free it), and the owner transfers it to 6826. There is no
          forced repay on an E/F state.
  Never.  The runner never moves money between accounts: it only reports the
          draw/repay amounts. The loan is counted from the moment a draw is
          REQUESTED (conservative).

WHY THESE CHOICES (backtest 2026-10-13, scratch margin_sim*.py on the
funding_pct_backtest harness, 5.25% interest, vs not borrowing):
  repay rule, cap 4%    real 2015-26     proxy 2000-26   worst single loan
  recovery/6m/E-F       +0.01 pp/yr      -0.08 pp/yr     -1.1% of account
  recovery/6m           +0.04            -0.09           -1.4%
  recovery/12m (THIS)   +0.14            +0.07           -1.4%
  recovery only         +0.38            +0.25           -0.5%, but loans open
                                                         ~1.5y (2018, 2022), ~3y (2000-03)
The tight exits sell into lows (late 2018, March 2020, 2022). Recovery-or-12
months is the middle: positive on both histories, never open-ended.
Cap: the collateral is ~$139k of VTI/VXUS (crypto is not marginable). At a
30% maintenance requirement a margin call needs the collateral to fall to
loan / 0.70: $20k -> -79%, $35k -> -64%, $51k -> -48% (VTI fell 55% in
2008-09), $98k (the full available margin) -> ~-6%. Draws happen when
markets are already down, so the loan is held to 25% of the collateral and
to 4% of the Agentic account.

Ledger: data/margin_loan.json. REPORTING + one live effect: while a repay
is due, live_run holds `repay_hold()` dollars back as cash (no sweep, no
reinvestment) until the transfer leaves the account.
"""
import datetime
import json
import math
import os

LEDGER_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'margin_loan.json')
RATE = 0.0525                 # owner's margin rate, 2026-10-13
CAP_ACCOUNT_PCT = 0.04        # of the Agentic account value at the draw
CAP_COLLATERAL_PCT = 0.25     # of the 6826 marginable collateral
DEADLINE_SESSIONS = 252       # 12 months
ROUND_TO = 10
TRANSFER_SEEN = 0.5           # repay considered sent once idle cash < this x the hold


def load(path=LEDGER_PATH):
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def save(led, path=LEDGER_PATH):
    with open(path, 'w') as f:
        json.dump(led, f, indent=2)
        f.write('\n')


def _round(x):
    return round(x / ROUND_TO) * ROUND_TO


def principal(led):
    return sum(d['amount'] for d in led.get('draws', [])) if led else 0.0


def is_open(led):
    return bool(led) and led.get('status') in ('open', 'repay_due')


def owed(led, today):
    """Principal plus simple interest accrued per draw to `today` (estimate:
    the broker's figure is authoritative)."""
    if not is_open(led):
        return 0.0
    t = datetime.date.fromisoformat(today)
    tot = 0.0
    for d in led['draws']:
        days = max(0, (t - datetime.date.fromisoformat(d['date'])).days)
        tot += d['amount'] * (1 + RATE * days / 365.0)
    return round(tot, 2)


def cap(led, account_value):
    c = CAP_ACCOUNT_PCT * account_value
    coll = (led or {}).get('collateral_value')
    if coll:
        c = min(c, CAP_COLLATERAL_PCT * float(coll))
    return c


def whole_share_basket(budget, weights, prices, limit_band=0.003):
    """Whole shares of the positive-weight legs worth ~budget, priced at the
    after-hours buy limit (price + limit_band, rounded down to the cent).
    weights/prices: leg -> weight / last price. Returns (basket, total) where
    basket is leg -> {shares, limit}; total <= budget unless budget buys less
    than one share of everything (then total is 0)."""
    w = {l: x for l, x in weights.items() if x > 0 and prices.get(l)}
    if not w:
        return {}, 0.0
    sw = sum(w.values())
    lim = {l: math.floor(round(prices[l] * (1 + limit_band) * 100, 6)) / 100 for l in w}
    sh = {l: int(round(budget * w[l] / sw / lim[l])) for l in w}

    def total():
        return round(sum(sh[l] * lim[l] for l in sh), 2)
    while total() > budget and any(sh.values()):
        # drop one share from the leg furthest above its dollar target
        l = max((l for l in sh if sh[l]), key=lambda l: sh[l] * lim[l] - budget * w[l] / sw)
        sh[l] -= 1
    basket = {l: dict(shares=sh[l], limit=lim[l]) for l in sh if sh[l]}
    return basket, total()


def request_draw(led, today, kind, suggested, account_value, peak_date, peak_value, latest_value=None,
                 weights=None, prices=None):
    """Size and log a draw for a funding event. Returns (led, amount, line).
    amount is 0 when the cap is full, or when a new loan would start with the
    NAV index already at its high (it would repay at once). Idempotent per
    (date, kind). With weights/prices (owner 2026-10-13: "borrow a whole
    number or calculate based on full share so can be bought after hours")
    the draw is a basket of WHOLE shares at the after-hours buy limit and
    the amount is its cost rounded UP to a whole dollar; without them, a
    whole-dollar amount rounded to $10."""
    led = dict(led or {})
    led.setdefault('draws', [])
    if any(d['date'] == today and d['kind'] == kind for d in led['draws']):
        d = next(d for d in led['draws'] if d['date'] == today and d['kind'] == kind)
        return led, d['amount'], f"margin draw for {kind} on {today} already logged: ${d['amount']:,.0f}"
    if led.get('status') == 'repay_due':
        return led, 0.0, 'margin: repay is due -- no new draw until it is settled'
    if not is_open(led) and latest_value is not None and latest_value >= peak_value:
        return led, 0.0, 'margin: NAV index is at its high -- no loan to start'
    room = cap(led, account_value) - principal(led)
    basket = None
    if weights and prices:
        basket, cost = whole_share_basket(min(suggested, room - 1.0), weights, prices)
        amt = float(math.ceil(cost)) if basket else 0.0
    else:
        amt = max(0.0, _round(min(suggested, room)))
    if amt < ROUND_TO:
        return led, 0.0, (f"margin cap full (${principal(led):,.0f} of ${cap(led, account_value):,.0f}): "
                          f"no draw for this event")
    if not is_open(led):
        led.update(status='open', first_draw=today, peak_date=peak_date, peak_value=peak_value,
                   draws=[], repay=None)
    d = dict(date=today, kind=kind, amount=amt)
    if basket:
        d['basket'] = basket
    led['draws'].append(d)
    return led, amt, None


def basket_lines(draw, market_hours='extended_hours'):
    """The buy orders for a draw's whole-share basket, for the session to place
    once the transfer has landed (after hours: limit orders only)."""
    return [f"BUY {l:5} {b['shares']:>5} sh  LIMIT {b['limit']:.2f}  {market_hours}  (~${b['shares'] * b['limit']:,.2f})"
            for l, b in sorted(draw.get('basket', {}).items())]


def sessions_since(first, session_dates, today):
    return sum(1 for d in set(session_dates) | {today} if first <= d <= today) - 1


def repay_check(led, nav_rows, session_dates, today):
    """(reason, None) when the loan is due today, else (None, why-not).
    nav_rows: drawdown_tracker.load_log() rows; the recovery test uses the
    latest logged index value (yesterday's close at 15:50)."""
    if not is_open(led):
        return None, 'no loan'
    if led['status'] == 'repay_due':
        return led['repay']['reason'], None
    latest = nav_rows[-1][2] if nav_rows else None
    if latest is not None and latest >= led['peak_value']:
        return 'recovery', None
    n = sessions_since(led['first_draw'], session_dates, today)
    if n >= DEADLINE_SESSIONS:
        return 'deadline', None
    return None, (f"repay at NAV index >= {led['peak_value']:.4f} (now {latest:.4f}) or in "
                  f"{DEADLINE_SESSIONS - n} sessions")


def mark_repay_due(led, today, reason):
    if led['status'] != 'repay_due':
        led['status'] = 'repay_due'
        led['repay'] = dict(date=today, reason=reason, amount=_round_up(owed(led, today)))
    return led


def _round_up(x):
    return -(-x // ROUND_TO) * ROUND_TO


def repay_hold(led):
    """Dollars live_run keeps out of the strategy as cash while a repay is due."""
    return float(led['repay']['amount']) if led and led.get('status') == 'repay_due' else 0.0


def settle_if_sent(led, today, idle_cash, sold_today=False):
    """Once the repay cash has left the account (idle cash fell below
    TRANSFER_SEEN x the hold, on a day the hold was not just being raised),
    close the loan. Returns (led, closed?)."""
    if not led or led.get('status') != 'repay_due' or sold_today:
        return led, False
    if led['repay'].get('raised') and idle_cash < TRANSFER_SEEN * repay_hold(led):
        led.setdefault('history', []).append(dict(first_draw=led['first_draw'], draws=led['draws'],
                                                  repay=dict(led['repay'], settled=today)))
        led.update(status='closed', draws=[], first_draw=None, peak_date=None, peak_value=None, repay=None)
        return led, True
    return led, False


def summary_line(led, account_value, today, nav_rows=None, session_dates=None):
    if not is_open(led):
        return f"margin loan: none (cap ${cap(led, account_value):,.0f})"
    s = (f"margin loan: ${principal(led):,.0f} principal, ~${owed(led, today):,.0f} owed at {RATE*100:.2f}%, "
         f"cap ${cap(led, account_value):,.0f}, first draw {led['first_draw']}")
    if led['status'] == 'repay_due':
        return s + f"; REPAY DUE ({led['repay']['reason']}) ${led['repay']['amount']:,.0f}"
    if nav_rows is not None and session_dates is not None:
        _, why = repay_check(led, nav_rows, session_dates, today)
        s += f"; {why}"
    return s
