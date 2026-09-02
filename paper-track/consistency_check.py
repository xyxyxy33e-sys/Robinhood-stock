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
                    CORE_SPMO_FRAC, CORE_GLD_FRAC, MICRO_OVERLAY_WEIGHTS,
                    STATE_LABEL, target_weights_with_gold, validate_weights_6leg,
                    target_weights_with_voltarget, vol_target_multiplier,
                    VOL_TARGET_PA, VOL_TARGET_CAP,
                    needs_rebalance, weight_drift, REBALANCE_DRIFT_BAND)


def check_core_blend_fracs(tol=0.005):
    """Assert the core's SPMO/GLD split sums to 1.0. Run alongside
    check_target_weights() after any edit to state.py's core-blend constants."""
    total = CORE_SPMO_FRAC + CORE_GLD_FRAC
    assert abs(total - 1.0) <= tol, (
        f"core blend fractions sum to {total:.4f}, not 1.0: "
        f"CORE_SPMO_FRAC={CORE_SPMO_FRAC}, CORE_GLD_FRAC={CORE_GLD_FRAC}"
    )
    print(f"OK: core blend fractions (SPMO={CORE_SPMO_FRAC}, gold={CORE_GLD_FRAC}) sum to 1.0")


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


def check_micro_overlay_weights(tol=0.005):
    """Assert every MICRO_OVERLAY_WEIGHTS entry (the A/D micro-overlay refinement,
    added 2026-09-01) is internally consistent, same as check_target_weights()."""
    for (state, agree), legs in MICRO_OVERLAY_WEIGHTS.items():
        assert len(legs) == len(TARGET_WEIGHT_LEGS), (
            f"micro overlay ({state}, agree={agree}): expected {len(TARGET_WEIGHT_LEGS)} legs, got {len(legs)}: {legs}"
        )
        core, tqqq, qld, xlu, cash = legs
        try:
            validate_weights(state, core, tqqq, qld, xlu, cash, tol=tol)
        except Exception as exc:
            raise AssertionError(f"micro overlay ({state}, agree={agree}) failed validate_weights: {exc}") from exc
    print(f"OK: all {len(MICRO_OVERLAY_WEIGHTS)} MICRO_OVERLAY_WEIGHTS entries sum to 1.0 within tol={tol}")
    from state import MICRO_OVERLAY_ENABLED, target_weights_with_micro, TARGET_WEIGHTS as _TW
    if not MICRO_OVERLAY_ENABLED:
        assert MICRO_OVERLAY_WEIGHTS == {}, "overlay disabled but MICRO_OVERLAY_WEIGHTS is non-empty"
        for st in _TW:
            for ag in (True, False):
                assert target_weights_with_micro(st, ag) == _TW[st], (st, ag)
        print("OK: micro overlay DISABLED -- target_weights_with_micro() == TARGET_WEIGHTS for all 12 inputs")


def check_gold_overlay(tol=0.005):
    """Assert target_weights_with_gold()'s 6-leg output sums to 1.0 for
    every state, both with and without the micro overlay active (A/D each
    checked at micro_agrees True and False) -- added 2026-09-01 when gold
    moved from an in-core blend to a standalone top-slice present in every
    state. Run this after any edit to STANDALONE_GOLD_FRAC or the micro
    overlay weights."""
    n = 0
    for state in STATE_LABEL:
        for micro_agrees in (True, False):
            core, tqqq, qld, xlu, gold, cash = target_weights_with_gold(state, micro_agrees)
            try:
                validate_weights_6leg(state, core, tqqq, qld, xlu, gold, cash, tol=tol)
            except Exception as exc:
                raise AssertionError(
                    f"state {state} (micro_agrees={micro_agrees}) failed validate_weights_6leg: {exc}"
                ) from exc
            n += 1
    print(f"OK: all {n} (state, micro_agrees) combinations from target_weights_with_gold() sum to 1.0 within tol={tol}")


def check_voltarget_overlay(tol=0.005):
    """Assert target_weights_with_voltarget()'s output stays a valid 5-leg
    weight tuple across every state, both micro settings, and a wide range of
    realized-vol inputs -- including the degenerate ones. Added 2026-09-01
    when volatility targeting became the outermost live overlay.

    Specifically guards the three ways this overlay could break a rebalance:
      * vol=None / 0 (insufficient history, or a bad vol computation) must
        degrade to multiplier 1.0 and return the un-scaled weights, NOT zero
        out the portfolio;
      * cash must never go negative, which holds only while VOL_TARGET_CAP
        <= 1.0 -- this asserts that invariant directly, so raising the cap
        without re-deriving the math trips here instead of at trade time;
      * every leg must stay in [0,1] and the tuple must still sum to 1.0.
    """
    assert VOL_TARGET_CAP <= 1.0, (
        f"VOL_TARGET_CAP={VOL_TARGET_CAP} > 1.0 would lever the risky legs UP and can drive "
        f"the cash leg negative; target_weights_with_voltarget()'s cash formula assumes cap<=1"
    )
    vols = [None, 0.0, 0.05, 0.10, VOL_TARGET_PA, 0.25, 0.40, 0.80, 2.0]
    n = 0
    for state in STATE_LABEL:
        for micro_agrees in (True, False):
            for vol in vols:
                core, tqqq, qld, xlu, cash = target_weights_with_voltarget(state, micro_agrees, vol)
                try:
                    validate_weights(state, core, tqqq, qld, xlu, cash, tol=tol)
                except Exception as exc:
                    raise AssertionError(
                        f"state {state} (micro_agrees={micro_agrees}, vol={vol}) failed "
                        f"validate_weights: {exc}"
                    ) from exc
                if cash < -tol:
                    raise AssertionError(
                        f"state {state} (micro_agrees={micro_agrees}, vol={vol}) produced "
                        f"negative cash={cash!r}"
                    )
                n += 1
    # None/0 vol must be a no-op, not a wipeout
    for state in STATE_LABEL:
        for micro_agrees in (True, False):
            base = target_weights_with_gold(state, micro_agrees)
            base5 = (base[0], base[1], base[2], base[3], base[5])
            for vol in (None, 0.0):
                got = target_weights_with_voltarget(state, micro_agrees, vol)
                if max(abs(a - b) for a, b in zip(got, base5)) > tol:
                    raise AssertionError(
                        f"state {state} (micro_agrees={micro_agrees}) with vol={vol} should be a "
                        f"no-op but returned {got} vs expected {base5}"
                    )
    assert vol_target_multiplier(VOL_TARGET_PA) == 1.0
    assert vol_target_multiplier(VOL_TARGET_PA * 2) < 1.0
    print(f"OK: all {n} (state, micro_agrees, vol) combinations from "
          f"target_weights_with_voltarget() are valid, cash never negative, "
          f"vol=None/0 is a no-op, cap={VOL_TARGET_CAP} <= 1.0")


def check_rebalance_band():
    """Assert the drift-band rebalance gate behaves, especially at its edges.

    The band exists to stop volatility targeting from trading every day, but
    it must NEVER delay a genuine regime change and must never wedge the
    portfolio permanently off-target. Guards:
      * a regime change always rebalances, no matter how small the drift;
      * nothing held yet always rebalances (initial allocation);
      * drift strictly above the band rebalances, drift at/below it does not;
      * the band is in (0, 2] -- L1 drift between two weight tuples that each
        sum to 1.0 cannot exceed 2.0, so a band >= 2 could never trigger and
        would silently disable vol-driven rebalancing entirely.
    """
    assert 0 < REBALANCE_DRIFT_BAND < 2.0, (
        f"REBALANCE_DRIFT_BAND={REBALANCE_DRIFT_BAND} must be in (0, 2): L1 drift between two "
        f"weight tuples summing to 1.0 maxes out at 2.0, so a band at or above that can never "
        f"fire and would disable vol-driven rebalancing"
    )
    base = (0.88, 0.12, 0.0, 0.0, 0.0)
    # regime change always wins, even at zero drift
    do, _, why = needs_rebalance(base, list(base), regime_changed=True)
    assert do and why == 'regime change', f"regime change must always rebalance, got {why!r}"
    # nothing held -> initial allocation
    do, _, why = needs_rebalance(base, None, regime_changed=False)
    assert do and 'initial' in why, f"empty holdings must rebalance, got {why!r}"
    # identical weights, no regime change -> hold
    do, drift, _ = needs_rebalance(base, list(base), regime_changed=False)
    assert not do and drift == 0.0, "identical weights must not trigger a rebalance"
    # just inside vs just outside the band (drift is 2x the per-leg shift:
    # moving x out of core and into cash changes two legs by x each)
    half = REBALANCE_DRIFT_BAND / 2
    inside = (base[0] - half * 0.98, base[1], 0.0, 0.0, base[4] + half * 0.98)
    outside = (base[0] - half * 1.02, base[1], 0.0, 0.0, base[4] + half * 1.02)
    do_in, d_in, _ = needs_rebalance(inside, list(base), regime_changed=False)
    do_out, d_out, _ = needs_rebalance(outside, list(base), regime_changed=False)
    assert not do_in, f"drift {d_in:.4f} should be inside band {REBALANCE_DRIFT_BAND}"
    assert do_out, f"drift {d_out:.4f} should be outside band {REBALANCE_DRIFT_BAND}"
    assert abs(weight_drift(base, base)) == 0.0
    print(f"OK: rebalance drift band {REBALANCE_DRIFT_BAND*100:.0f}% (L1) gates correctly -- "
          f"regime changes always fire, empty holdings always fire, "
          f"drift {d_in*100:.1f}% holds and {d_out*100:.1f}% trades")


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
    check_micro_overlay_weights()
    check_gold_overlay()
    check_voltarget_overlay()
    check_rebalance_band()
