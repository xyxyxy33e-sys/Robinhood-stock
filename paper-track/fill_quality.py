"""Execution-quality tracker -- added 2026-09-07.

WHY THIS EXISTS. On 2026-09-07 a drawdown reconciliation showed that ONE
extra session between signal and fill takes the same design from -34.7% to
-39.5% max drawdown and costs 3.1pp of CAGR -- larger than any design change
argued over that week. Execution is therefore the biggest single lever on
this strategy, and until now NOTHING measured it: the triggers assumed they
filled at (or within five minutes of) the signal close and never checked.

This records, per leg per rebalance, the realised fill price against a
reference price (the official close of the signal session), so slippage
becomes a monitored fact rather than an assumption. It gates nothing and
never blocks a trade -- it is measurement only.

Sign convention: `slippage_bps` is COST-POSITIVE. A buy filled ABOVE the
reference and a sell filled BELOW it both give a positive number, meaning
money lost to execution. Negative means the fill beat the reference.
"""
import csv
import os

LOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'fill_quality.csv')
# 2026-09-09: 'session_lag' = sessions between the signal session and the
# fill (0 = same-session 15:5x run, the normal case; 1 = filled the next
# session, e.g. the watchdog/next-open fallback). The 25bp alarm and the
# 4bp cost comparison count ONLY lag-0 fills: on a lagged fill most of the
# number is the overnight gap, not broker execution (overnight_intraday.md),
# and letting those trip the alarm would cry wolf on exactly the days the
# fallback rule is used. Lagged fills are still recorded and reported apart.
FIELDS = ('date', 'symbol', 'side', 'quantity', 'fill_price', 'ref_price',
          'ref_kind', 'slippage_bps', 'notional', 'note', 'session_lag')

# A single fill worse than this is worth calling out in the report. Not a
# gate -- the trade has already happened by the time this is computed.
SLIPPAGE_FLAG_BPS = 25.0


def slippage_bps(side, fill_price, ref_price):
    """Cost-positive slippage in basis points. Raises on bad input rather
    than silently returning a plausible number."""
    if ref_price is None or fill_price is None:
        raise ValueError("fill_price and ref_price are both required")
    if ref_price <= 0 or fill_price <= 0:
        raise ValueError(f"prices must be positive, got {fill_price!r}/{ref_price!r}")
    side = side.lower()
    if side not in ('buy', 'sell'):
        raise ValueError(f"side must be 'buy' or 'sell', got {side!r}")
    raw = (fill_price - ref_price) / ref_price
    return (raw if side == 'buy' else -raw) * 10000.0


def record_fill(date, symbol, side, quantity, fill_price, ref_price,
                ref_kind='signal_session_close', note='', path=LOG_PATH,
                session_lag=0):
    """Append one filled leg. `ref_price` is the price the backtest assumes
    we traded at -- normally the official close of the session the signal was
    computed on. `ref_kind` records which reference was used, so a run that
    had to use something else (an open, a delayed close) is not silently
    compared against a different benchmark later."""
    bps = slippage_bps(side, fill_price, ref_price)
    row = dict(date=date, symbol=symbol, side=side.lower(), quantity=quantity,
               fill_price=fill_price, ref_price=ref_price, ref_kind=ref_kind,
               slippage_bps=round(bps, 2),
               notional=round(abs(quantity) * fill_price, 2), note=note,
               session_lag=int(session_lag))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    exists = os.path.exists(path)
    with open(path, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            w.writeheader()
        w.writerow(row)
    return row


def load_log(path=LOG_PATH):
    if not os.path.exists(path):
        return []
    with open(path, newline='') as f:
        return [r for r in csv.DictReader(f)]


def summarize(rows=None, path=LOG_PATH):
    """Notional-weighted slippage, which is the number that matters: a bad
    fill on a $30k leg is not the same event as a bad fill on a $500 stub."""
    rows = load_log(path) if rows is None else rows
    allrows = rows
    # legacy rows (before 2026-09-09) have no session_lag column: the one
    # batch on 2026-09-08 was a Tuesday-open fill of a Friday signal, lag 1.
    def lag(r):
        v = r.get('session_lag')
        if v in (None, ''):
            return 1 if r.get('date') == '2026-09-08' else 0
        return int(float(v))
    rows = [r for r in allrows if lag(r) == 0]
    lagged = [r for r in allrows if lag(r) != 0]
    if not rows:
        return dict(n=0, notional=0.0, weighted_bps=None, simple_bps=None,
                    worst=None, flagged=[], n_lagged=len(lagged),
                    lagged_weighted_bps=_wbps(lagged))
    notional = sum(float(r['notional']) for r in rows)
    wb = (sum(float(r['slippage_bps']) * float(r['notional']) for r in rows) / notional
          if notional > 0 else None)
    sb = sum(float(r['slippage_bps']) for r in rows) / len(rows)
    worst = max(rows, key=lambda r: float(r['slippage_bps']))
    flagged = [r for r in rows if float(r['slippage_bps']) > SLIPPAGE_FLAG_BPS]
    return dict(n=len(rows), notional=round(notional, 2),
                weighted_bps=round(wb, 2) if wb is not None else None,
                simple_bps=round(sb, 2), worst=worst, flagged=flagged,
                n_lagged=len(lagged), lagged_weighted_bps=_wbps(lagged))


def _wbps(rows):
    n = sum(float(r['notional']) for r in rows)
    return (round(sum(float(r['slippage_bps']) * float(r['notional']) for r in rows) / n, 2)
            if n > 0 else None)


def cost_estimate_pa(rows=None, path=LOG_PATH, years=None):
    """Annualised drag implied by observed slippage, for comparison with the
    4bp one-way cost model the backtests assume. Returns None until there is
    enough history to be worth quoting."""
    rows = load_log(path) if rows is None else rows
    if not rows or years in (None, 0):
        return None
    cost = sum(float(r['slippage_bps']) / 10000.0 * float(r['notional']) for r in rows)
    return cost / years
