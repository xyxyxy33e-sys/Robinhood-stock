"""Flag likely wash sales in the strategy's own trade history -- added 2026-08-29.

The strategy has grown enough moving parts (weekly/daily core rebalances, TQQQ
resized on every regime change, BOXX bought/sold on every D/E/F entry and exit)
that wash sales are now closer to the normal case than the exception for any
loss-sale it realizes. This does not compute tax liability or basis adjustments
-- it only flags trades whose loss is a wash-sale CANDIDATE per the 61-day
window (30 days before through 30 days after the loss-sale date), so the
weekly report can separate "loss that's actually usable this year" from "loss
that's deferred into the replacement shares' basis."

Real wash-sale determination also covers substantially identical securities
(e.g. options on the same underlying) and multiple lots; this only checks
same-symbol buys, which covers this account's actual trading pattern (no
options here) but is a floor, not a complete determination -- for anything
that matters for an actual tax filing, use the broker's 1099-B, which applies
the full rule.
"""
import datetime as dt

def flag_wash_sales(trades):
    """trades: list of dicts with at least {symbol, side, date (YYYY-MM-DD),
    realized_gain}. Returns the same list of loss-sale trades augmented with
    'wash_sale_candidate': bool and 'wash_sale_window': the matching buy date(s).
    Only loss-sales (realized_gain < 0) are checked; gains are never wash sales."""
    by_symbol = {}
    for t in trades:
        by_symbol.setdefault(t['symbol'], []).append(t)

    flagged = []
    for t in trades:
        if t.get('side') != 'sell' or t.get('realized_gain', 0) >= 0:
            continue
        sell_date = dt.date.fromisoformat(t['date'])
        window_start = sell_date - dt.timedelta(days=30)
        window_end = sell_date + dt.timedelta(days=30)
        matches = [
            b['date'] for b in by_symbol.get(t['symbol'], [])
            if b.get('side') == 'buy'
            and window_start <= dt.date.fromisoformat(b['date']) <= window_end
            and b['date'] != t['date']
        ]
        out = dict(t)
        out['wash_sale_candidate'] = bool(matches)
        out['wash_sale_window'] = matches
        flagged.append(out)
    return flagged

def summarize(flagged):
    """Returns (usable_loss_total, deferred_loss_total, n_deferred)."""
    usable = sum(t['realized_gain'] for t in flagged if not t['wash_sale_candidate'])
    deferred = sum(t['realized_gain'] for t in flagged if t['wash_sale_candidate'])
    n_deferred = sum(1 for t in flagged if t['wash_sale_candidate'])
    return usable, deferred, n_deferred
