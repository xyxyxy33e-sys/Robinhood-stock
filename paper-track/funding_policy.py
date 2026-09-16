"""Owner funding policy -- percentage-of-account-value, escalating by tier.

ADOPTED 2026-09-16 (owner decision), replacing the flat $5,000/event policy
of 2026-09-07. Backtested in `funding_pct_backtest.py` /
`research_notes/funding_pct_backtest.md`: the tradeoff between IRR and
per-dollar multiple is smooth and monotonic on both the real 11-year window
and the 26-year proxy -- there is no interior optimum, so the base rate is
a genuine owner preference (a savings-rate choice), not something the
backtest can resolve further. Mild escalation (1x/1.5x/2x/2.5x by tier) was
the one shape choice the data did support: steep and linear escalation buy
at most ~1pp of extra IRR for 2-3x the dollar ask at the deepest tier.

This is a REPORTING duty only -- these functions compute what to TELL the
owner; nothing here moves money or changes a trading weight. Any live report
that combines two or more numbers must be computed in code, never hand-added
in prose (STRATEGY.md's standing rule, `consistency_check.check_pnl_sum`'s
reason for existing) -- these functions are that code for the funding lines.
"""
import bisect

BASE_PCT = 0.02          # of CURRENT account value, at the moment of the event
TIER_MULT = {0.05: 1.0, 0.10: 1.5, 0.15: 2.0, 0.20: 2.5}   # matches state.py-independent DD_THRESHOLDS
TURN_MULT = 1.0          # the D/E/F->A/B/C turn is a confirmation signal, not severity-scaled
ROUND_TO = 10            # nearest $10, so a reported figure never implies false precision


def _round(x, to=ROUND_TO):
    return round(x / to) * to


def tier_funding_amount(account_value, tier, base_pct=BASE_PCT, mult=TIER_MULT):
    """Dollar amount to report for a newly-crossed drawdown tier (0.05/0.10/0.15/0.20)."""
    if tier not in mult:
        raise ValueError(f"unknown tier {tier!r}; expected one of {sorted(mult)}")
    if account_value <= 0:
        raise ValueError("account_value must be positive")
    return _round(account_value * base_pct * mult[tier])


def turn_funding_amount(account_value, base_pct=BASE_PCT, turn_mult=TURN_MULT):
    """Dollar amount to report for the D/E/F -> A/B/C turn."""
    if account_value <= 0:
        raise ValueError("account_value must be positive")
    return _round(account_value * base_pct * turn_mult)


def schedule_table(account_value):
    """All five figures at once, for a report line: {0.05:.., 0.10:.., 0.15:.., 0.20:.., 'turn':..}."""
    out = {tier: tier_funding_amount(account_value, tier) for tier in sorted(TIER_MULT)}
    out['turn'] = turn_funding_amount(account_value)
    return out


if __name__ == '__main__':
    for v in (100_000, 198_000, 500_000):
        print(v, schedule_table(v))
    # today's account, for the record (2026-09-16 close, ~$198k)
    print('today ~$198k:', schedule_table(198_000))
