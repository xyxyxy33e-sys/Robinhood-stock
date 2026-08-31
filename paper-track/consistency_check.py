"""Automated consistency checks for the live strategy, meant to be run on
demand (or wired into a trigger) rather than relied on only at trade time.

Two checks, both aimed at classes of bug that have actually happened in this
project:

1. TARGET_WEIGHTS integrity -- every state's 5 legs (core, tqqq, qld, xlu,
   cash) must be within [0, 1] and sum to 1.0. validate_weights() in
   state.py already enforces this per-call at trigger runtime, but nothing
   previously asserted it for every state up front, independent of which
   states happen to fire live. Run this after any edit to TARGET_WEIGHTS.

2. P&L arithmetic cross-check -- given a list of raw trade P&L records
   (as returned by get_pnl_trade_history) and the account's own
   independently-reported aggregate (get_realized_pnl / a P&L bucket
   total), verify that summing the raw records reproduces the aggregate.
   This directly targets the 2026-08-31 bug where a weekly report's
   headline "today's realized P&L" and "new cumulative" figures were
   composed by hand from partial sums and ended up double-counting a
   pre-existing loss. The rule going forward: any such figure must be
   computed in code from raw records, never composed by hand in prose --
   this script is the code that does it.

Usage as a library (intended use -- import into a trigger run or REPL):

    from consistency_check import check_target_weights, check_pnl_sum

    check_target_weights()  # raises AssertionError with a clear message on failure

    check_pnl_sum(trade_pnls, expected_total, label="August 2026 bucket")
    # trade_pnls: list of per-trade realized P&L floats (dollars)
    # expected_total: the account's own reported aggregate for the same set
    # raises AssertionError if they don't match within a cent
"""

from state import (TARGET_WEIGHTS, TARGET_WEIGHT_LEGS, validate_weights,
                    CORE_SPMO_FRAC, CORE_GLD_FRAC)


def check_core_blend_fracs(tol=0.005):
    """Assert the core's SPMO/GLD split sums to 1.0. Run alongside
    check_target_weights() after any edit to state.py's core-blend constants."""
    total = CORE_SPMO_FRAC + CORE_GLD_FRAC
    assert abs(total - 1.0) <= tol, (
        f"core blend fractions sum to {total:.4f}, not 1.0: "
        f"CORE_SPMO_FRAC={CORE_SPMO_FRAC}, CORE_GLD_FRAC={CORE_GLD_FRAC}"
    )
    print(f"OK: core blend fractions (SPMO={CORE_SPMO_FRAC}, GLD={CORE_GLD_FRAC}) sum to 1.0")


def check_target_weights(tol=0.005):
    """Assert every state in TARGET_WEIGHTS is internally consistent.

    Raises AssertionError (via validate_weights' WeightSanityError, caught
    and re-raised with state context) on the first bad state found.
    """
    for state, legs in TARGET_WEIGHTS.items():
        assert len(legs) == len(TARGET_WEIGHT_LEGS), (
            f"state {state}: expected {len(TARGET_WEIGHT_LEGS)} legs "
            f"{TARGET_WEIGHT_LEGS}, got {len(legs)}: {legs}"
        )
        core, tqqq, qld, xlu, cash = legs
        try:
            validate_weights(state, core, tqqq, qld, xlu, cash, tol=tol)
        except Exception as exc:
            raise AssertionError(f"state {state} failed validate_weights: {exc}") from exc
    print(f"OK: all {len(TARGET_WEIGHTS)} states in TARGET_WEIGHTS sum to 1.0 within tol={tol}")


def check_pnl_sum(trade_pnls, expected_total, label="", cent_tol=0.01):
    """Assert summing raw per-trade P&L records matches an independently
    reported aggregate. Use this instead of hand-adding subtotals in prose.

    trade_pnls: iterable of per-trade realized P&L floats (dollars).
    expected_total: the independently-reported aggregate for the identical
        set of trades (e.g. from get_realized_pnl or an account P&L bucket).
    label: optional description used in the assertion message / printout.
    """
    computed = sum(trade_pnls)
    diff = computed - expected_total
    tag = f" ({label})" if label else ""
    assert abs(diff) <= cent_tol, (
        f"P&L mismatch{tag}: summed {len(list(trade_pnls)) if hasattr(trade_pnls, '__len__') else 'N/A'} "
        f"raw trades = {computed:.2f}, but reported aggregate = {expected_total:.2f} "
        f"(diff = {diff:.2f}). Do not report either figure until this is reconciled."
    )
    print(f"OK: raw trade sum {computed:.2f} matches reported aggregate {expected_total:.2f}{tag}")
    return computed


if __name__ == "__main__":
    check_target_weights()
    check_core_blend_fracs()
