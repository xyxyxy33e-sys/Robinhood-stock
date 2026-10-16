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
          exceeds CAP = min(10% of the Agentic account, 25% of the 6826
          collateral) -- 4% / 25% until the owner's change of 2026-10-16.
          Draws while a loan is open stack on it.
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

NETTING (owner, 2026-10-16): "the main idea is to avoid paying interest for
margin, so when there is a margin, we shouldn't be holding any portion in
boxx"; "if it's under the margin amount, just leave it as buying power, give
me a notification, I will transfer it".
  While a loan is open, the strategy's BOXX leg pays the loan down instead
  of being bought. Targets are computed on the IMAGINARY account (account +
  principal already netted), so the risky legs hold the same dollars as if
  the loan were still drawn:
    netted target T = min(BOXX weight x imaginary account, principal)
    BOXX bought     = BOXX dollars - T (only what exceeds the whole loan)
    cash held       = T - already netted, left as buying power for the
                      owner's transfer to 6826 (MARGIN REPAY push)
  When the BOXX leg shrinks below what was netted, the difference is
  re-borrowed (MARGIN DRAW push) -- the amount netted earlier, cap or not
  (owner: "when position shifts out of the boxx, let me know I will transfer
  in the previous amount back to the account"); until it lands the risky
  legs are scaled to the cash on hand. A move of under NET_MIN dollars (or
  NET_MIN_PCT of the account) is left alone unless it nets or restores the
  whole loan, and a transfer is requested only after NET_CONFIRM sessions in
  a row. VIXM is the hedge, not idle cash: only the BOXX leg nets. The
  recovery / 252-session repay, the cap and the interest rule are unchanged;
  the full repay covers only what is still drawn.
  Backtest 2026-10-16 (scratch margin_net_sim.py, same harness, cap 4%,
  recovery/12m, 5.25%): extra return vs not borrowing +0.134 -> +0.200 pp/yr
  real 2015-26, +0.067 -> +0.138 proxy 2000-26; interest $28.9k -> $12.2k
  real; transfers 9.4 -> 13.0 a year; band 0.25-2% and 1-5 sessions all
  within 0.004 pp/yr, so 1% / 2 sessions.

Ledger: data/margin_loan.json. REPORTING + two live effects: while a repay
is due, live_run holds `repay_hold()` dollars back as cash (no sweep, no
reinvestment) until the transfer leaves the account; and the netting above.
"""
import datetime
import json
import math
import os

LEDGER_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'margin_loan.json')
RATE = 0.0525                 # owner's margin rate, 2026-10-13
CAP_ACCOUNT_PCT = 0.10        # of the Agentic account value (4% -> 5% -> 10%, owner 2026-10-16)
CAP_COLLATERAL_PCT = 0.25     # of the 6826 marginable collateral (owner 2026-10-16: 10% / 25%)
DEADLINE_SESSIONS = 252       # 12 months
ROUND_TO = 10
TRANSFER_SEEN = 0.5           # repay considered sent once idle cash < this x the hold
NET_MIN = 1000.0              # netting: smallest transfer worth asking for ...
NET_MIN_PCT = 0.01            # ... or this share of the account, whichever is larger
NET_CONFIRM = 2               # sessions in a row before a netting transfer is requested


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


def netted(led):
    """Principal already paid down through netting (re-borrowable)."""
    return float(led.get('netted', 0.0)) if is_open(led) else 0.0


def outstanding(led):
    """Principal still drawn: draws minus what netting paid down."""
    return principal(led) - netted(led)


def owed(led, today):
    """Principal still drawn plus simple interest accrued to `today`: per draw,
    less per netting transfer from its date (estimate: the broker's figure is
    authoritative)."""
    if not is_open(led):
        return 0.0
    t = datetime.date.fromisoformat(today)

    def acc(amount, date):
        return amount * (1 + RATE * max(0, (t - datetime.date.fromisoformat(date)).days) / 365.0)
    tot = sum(acc(d['amount'], d['date']) for d in led['draws'])
    tot -= sum(acc(e['amount'], e['date']) for e in led.get('net_events', []))
    return round(tot, 2)


def net_value(led, account_value, today):
    """The owner's true equity in the strategy: Agentic account value minus the
    margin loan owed in 6826 (principal + accrued interest). Owner, 2026-10-13:
    "consider true account value, minus the margin+interest"."""
    return round(account_value - owed(led, today), 2)


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
                   draws=[], repay=None, netted=0.0, net_events=[])
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
    """Flag the full repay. Netting stops (a pending netting transfer is
    dropped); if netting already paid the whole principal down, only the
    interest accrued before those transfers is left, and the loan closes
    once that is under $10 (otherwise it is repaid like any other)."""
    if led['status'] != 'repay_due':
        led.pop('net_pending', None)
        amt = _round_up(owed(led, today))
        if amt < ROUND_TO:
            _close(led, today, dict(date=today, reason=reason, amount=0.0, note='fully netted'))
            return led
        led['status'] = 'repay_due'
        led['repay'] = dict(date=today, reason=reason, amount=amt)
    return led


def _close(led, today, repay):
    led.setdefault('history', []).append(dict(first_draw=led['first_draw'], draws=led['draws'],
                                              net_events=led.get('net_events', []),
                                              repay=dict(repay, settled=today)))
    led.update(status='closed', draws=[], first_draw=None, peak_date=None, peak_value=None, repay=None,
               netted=0.0, net_events=[])
    led.pop('net_pending', None)


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
        _close(led, today, led['repay'])
        return led, True
    return led, False


def net_step(led, today, boxx_dollars, idle_cash, account_value):
    """One session of the netting rule (module docstring, NETTING). Call it
    at the trade run with boxx_dollars = BOXX weight x the IMAGINARY account
    (account less any repay hold, plus netted(led)) and the idle cash read
    before any order. Returns (led, plan, push, line, dirty):
      plan = dict(T=..., hold=..., gap=...): T is the netted amount to plan
        with (BOXX bought = BOXX dollars - T, floored at 0), hold the cash to
        keep out of the strategy for a repay transfer, gap the re-borrow not
        yet arrived (the risky legs are scaled to the cash on hand);
      push = a MARGIN REPAY / MARGIN DRAW line for the owner, or None;
      line = a status line for the run report, or None."""
    zero = dict(T=0.0, hold=0.0, gap=0.0)
    if not is_open(led) or led.get('status') != 'open':
        return led, zero, None, None, False
    P, n = principal(led), netted(led)
    dirty = False
    pend = led.get('net_pending')
    # 1. a transfer the owner was asked for: has it happened?
    if pend and pend.get('notified'):
        amt = pend['amount']
        if pend['kind'] == 'repay':
            if not pend.get('raised') and idle_cash >= 0.9 * amt:
                pend['raised'] = today
                dirty = True
            elif pend.get('raised') and pend['raised'] < today and idle_cash < TRANSFER_SEEN * amt:
                led['netted'] = round(n + amt, 2)
                led.setdefault('net_events', []).append(dict(date=today, amount=amt))
                led.pop('net_pending')
                return led, dict(T=led['netted'], hold=0.0, gap=0.0), None, \
                    f"margin netting: ${amt:,.0f} repay transfer seen -- ${outstanding(led):,.0f} still drawn", True
            return led, dict(T=n + amt, hold=amt, gap=0.0), None, \
                f"margin netting: ${amt:,.0f} held as cash -- waiting for the transfer to 6826", dirty
        if idle_cash >= TRANSFER_SEEN * amt:
            led['netted'] = round(n - amt, 2)
            led.setdefault('net_events', []).append(dict(date=today, amount=-amt))
            led.pop('net_pending')
            return led, dict(T=led['netted'], hold=0.0, gap=0.0), None, \
                f"margin netting: ${amt:,.0f} re-borrow arrived -- ${outstanding(led):,.0f} drawn", True
        return led, dict(T=n - amt, hold=0.0, gap=amt), None, \
            f"margin netting: waiting for the ${amt:,.0f} re-borrow from 6826", dirty
    # 2. where netting should be today
    T = min(max(boxx_dollars, 0.0), P)
    d = T - n          # a re-borrow restores what was netted, cap or not (owner: "the previous amount")
    big = abs(d) >= max(NET_MIN, NET_MIN_PCT * account_value)
    whole = abs(d) >= ROUND_TO and (T >= P - 0.5 or T <= 0.5)
    if not (big or whole):
        if pend:
            led.pop('net_pending')
            dirty = True
        return led, dict(T=n, hold=0.0, gap=0.0), None, None, dirty
    kind = 'repay' if d > 0 else 'borrow'
    amt = float(math.floor(abs(d) / ROUND_TO) * ROUND_TO) if kind == 'repay' else float(min(_round_up(abs(d)), n))
    same = bool(pend) and pend['kind'] == kind
    streak = pend['streak'] + 1 if same else 1
    led['net_pending'] = dict(kind=kind, amount=amt, since=pend['since'] if same else today,
                              streak=streak, last=today)
    if kind == 'repay' and ((same and pend.get('raised')) or idle_cash >= 0.9 * amt):
        led['net_pending']['raised'] = (pend.get('raised') if same and pend.get('raised') else today)
    dirty = True
    if kind == 'repay':
        plan = dict(T=n + amt, hold=amt, gap=0.0)       # the cash is kept back from day 1
    else:
        plan = dict(T=n, hold=0.0, gap=0.0)             # until confirmed, keep the netted amount netted
    if streak < NET_CONFIRM:
        return led, plan, None, (f"margin netting: {kind} ${amt:,.0f} -- session {streak} of {NET_CONFIRM}"
                                 f"{', cash kept back meanwhile' if kind == 'repay' else ''}"), dirty
    led['net_pending']['notified'] = today
    if kind == 'repay':
        push = (f"MARGIN REPAY: transfer ${amt:,.0f} from Agentic to account 6826 (the BOXX leg, kept as cash) to pay "
                f"the margin loan down from ${outstanding(led):,.0f} to ${outstanding(led) - amt:,.0f}")
        return led, plan, push, None, dirty
    push = (f"MARGIN DRAW (re-borrow): the strategy is moving out of BOXX -- borrow ${amt:,.0f} in account 6826 and "
            f"transfer it back to Agentic (the amount netted earlier); the loan goes back from "
            f"${outstanding(led):,.0f} to ${outstanding(led) + amt:,.0f}")
    return led, dict(T=n - amt, hold=0.0, gap=amt), push, None, dirty


def net_dollar_targets(weights, legs, avail, imaginary, plan):
    """Dollar targets for the cash on hand `avail` (account less every hold):
    the risky legs at weight x the imaginary account, BOXX at its dollars
    less the netted amount T (floored at 0), the risky legs scaled down only
    when a re-borrow has not arrived yet. Returns {leg: dollars}."""
    w = dict(zip(legs, weights))
    boxx = max(w['BOXX'] * imaginary - plan['T'], 0.0)
    risky = {l: w[l] * imaginary for l in legs if l != 'BOXX'}
    tot = sum(risky.values())
    room = max(avail - boxx, 0.0)
    f = min(1.0, room / tot) if tot > 0 else 1.0
    out = {l: v * f for l, v in risky.items()}
    out['BOXX'] = avail - sum(out.values())
    return out


def summary_line(led, account_value, today, nav_rows=None, session_dates=None):
    if not is_open(led):
        return f"margin loan: none (cap ${cap(led, account_value):,.0f})"
    s = (f"margin loan: ${principal(led):,.0f} principal, ~${owed(led, today):,.0f} owed at {RATE*100:.2f}%, "
         f"cap ${cap(led, account_value):,.0f}, first draw {led['first_draw']}")
    if netted(led):
        s += f"; ${netted(led):,.0f} netted against BOXX (${outstanding(led):,.0f} drawn)"
    if led['status'] == 'repay_due':
        return s + f"; REPAY DUE ({led['repay']['reason']}) ${led['repay']['amount']:,.0f}"
    if nav_rows is not None and session_dates is not None:
        _, why = repay_check(led, nav_rows, session_dates, today)
        s += f"; {why}"
    return s
