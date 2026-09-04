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

FEEDING THIS THE RIGHT DATA -- read before calling. This function matches
loss-sales against BUY records in the same list. `get_pnl_trade_history`
returns only CLOSING trades, so a list built from it alone contains no buys
and every loss silently comes back "usable" -- a confidently wrong tax
figure, not an error. That happened on 2026-09-04: the first run reported
$0 deferred; re-running with buy dates recovered from `get_equity_orders`
(side='buy', filled, >=30 days before the earliest loss-sale) turned it into
$1,532.59 deferred out of $1,610.66 of losses. `no_buys_supplied()` below
exists to make that failure loud instead of silent -- call it, or pass
require_buys=True to flag_wash_sales(), whenever the answer will be reported.

SAME-DAY BUYS ARE NOT MATCHED, deliberately but debatably. A buy on the very
date of the loss-sale is excluded from the window (`b['date'] != t['date']`),
so a same-day round trip reads as "usable". That is a judgment call, not a
rule of law: the IRS window is calendar days either side and does not carve
out the sale date itself. Two IAU lots on 2026-09-01 are the live example --
reported usable here, arguably deferred. Treat any "usable" total that comes
entirely from same-day round trips as unproven; SAME_DAY_MATCHES flips the
behaviour if a stricter reading is ever wanted.
"""
import datetime as dt

# Whether a buy on the SAME DATE as the loss-sale counts as a replacement
# purchase. False (the original behaviour) treats a same-day round trip as a
# usable loss; True is the stricter reading. See the module docstring.
SAME_DAY_MATCHES = False


def no_buys_supplied(trades):
    """True when `trades` contains at least one loss-sale but NO buy records at
    all -- the signature of a list built from get_pnl_trade_history alone, where
    every loss would be misreported as usable. Check this before reporting any
    usable/deferred split; see the module docstring for how to get the buys."""
    has_loss = any(t.get('side') == 'sell' and t.get('realized_gain', 0) < 0
                   for t in trades)
    has_buy = any(t.get('side') == 'buy' for t in trades)
    return has_loss and not has_buy


class MissingBuyRecords(ValueError):
    """Raised by flag_wash_sales(require_buys=True) when no buys were supplied."""


def flag_wash_sales(trades, require_buys=False):
    """trades: list of dicts with at least {symbol, side, date (YYYY-MM-DD),
    realized_gain}. Returns the same list of loss-sale trades augmented with
    'wash_sale_candidate': bool and 'wash_sale_window': the matching buy date(s).
    Only loss-sales (realized_gain < 0) are checked; gains are never wash sales.

    require_buys=True raises MissingBuyRecords when the list holds loss-sales
    but no buys at all -- pass it whenever the result will be reported, so the
    get_pnl_trade_history-only mistake fails loudly instead of returning a
    clean-looking $0 deferred."""
    if require_buys and no_buys_supplied(trades):
        raise MissingBuyRecords(
            "no buy records in `trades`, but loss-sales are present: every loss "
            "would be reported as usable. get_pnl_trade_history returns closing "
            "trades only -- add buys from get_equity_orders (side='buy', filled, "
            "reaching >=30 days before the earliest loss-sale). See module docstring.")
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
            and (SAME_DAY_MATCHES or b['date'] != t['date'])
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
