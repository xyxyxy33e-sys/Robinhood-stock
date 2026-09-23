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

    # zero-target-leg sweep (ZERO_LEG_EPS, added 2026-09-04): a leg the design
    # says should be empty must not be able to sit inside the band forever.
    from state import ZERO_LEG_EPS
    assert 0 < ZERO_LEG_EPS < REBALANCE_DRIFT_BAND, (
        f"ZERO_LEG_EPS={ZERO_LEG_EPS} must be in (0, {REBALANCE_DRIFT_BAND}): at or above the "
        f"band it could never add a fire the band did not already cause, making it dead code"
    )
    zt = (0.70, 0.30, 0.0, 0.0, 0.0)              # target: no cash at all
    stub = (0.6985, 0.2965, 0.0, 0.0, 0.0050)     # 0.50% cash held, drift 0.99% -- inside band
    do, d, why = needs_rebalance(zt, stub, regime_changed=False)
    assert do and 'zero-target leg' in why, (
        f"a zero-target leg held at 0.50% must fire even at drift {d*100:.2f}%, got {why!r}")
    assert d < REBALANCE_DRIFT_BAND, "test case must be INSIDE the band or it proves nothing"
    # opting out reproduces the old behaviour exactly
    do_off, _, _ = needs_rebalance(zt, stub, regime_changed=False, zero_leg_eps=None)
    assert not do_off, "zero_leg_eps=None must restore the pre-2026-09-04 band-only rule"
    # dust below the epsilon is left alone
    dust = (0.6995, 0.2997, 0.0, 0.0, ZERO_LEG_EPS * 0.8)
    do_dust, _, _ = needs_rebalance(zt, dust, regime_changed=False)
    assert not do_dust, "holdings below ZERO_LEG_EPS must not fire"
    # a leg with a NONZERO target near it is not a stub, however close to zero
    do_nz, _, _ = needs_rebalance((0.0, 0.0, 0.85, 0.0, 0.15),
                                  (0.0, 0.0, 0.855, 0.0, 0.145), regime_changed=False)
    assert not do_nz, "only EXACTLY-zero targets are stubs; a small nonzero target is not"

    print(f"OK: rebalance drift band {REBALANCE_DRIFT_BAND*100:.0f}% (L1) gates correctly -- "
          f"regime changes always fire, empty holdings always fire, "
          f"drift {d_in*100:.1f}% holds and {d_out*100:.1f}% trades")
    print(f"OK: zero-target-leg sweep at {ZERO_LEG_EPS*100:.2f}% fires on a stub inside the band, "
          f"ignores dust below it, and is a no-op with zero_leg_eps=None")


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

def check_fast_reentry():
    """Fast re-entry overlay (2026-09-06): only B/C/F ever change, only toward
    MORE exposure, never with a fast reading that is itself defensive."""
    from state import (effective_state, FAST_REENTRY_MAP, FAST_REENTRY_ENABLED,
                       FAST_SHORT_N, FAST_LONG_N, target_weights_with_voltarget,
                       TARGET_WEIGHTS)
    assert FAST_REENTRY_ENABLED and (FAST_SHORT_N, FAST_LONG_N) == (20, 100), "fast window must stay 20/100"
    for m in 'ABCDEF':
        for f in 'ABCDEF':
            e = effective_state(m, f)
            if m in 'ADE':
                assert e == m, f"overlay must not touch {m}"
            if f in 'DEF':
                assert e == m, f"a defensive fast reading must never change {m}"
            if e != m:
                assert (m, f) in FAST_REENTRY_MAP
                assert sum(TARGET_WEIGHTS[e][:4]) >= sum(TARGET_WEIGHTS[m][:4]), "overlay only adds exposure"
        assert effective_state(m, None) == m
        assert target_weights_with_voltarget(m, False, 0.15) == target_weights_with_voltarget(m, False, 0.15, fast_state=None)
    assert effective_state('C', 'A') == 'A' and effective_state('B', 'B') == 'A' and effective_state('F', 'C') == 'C'
    assert effective_state('F', 'D') == 'F' and effective_state('C', 'C') == 'C'
    print("OK: fast re-entry overlay touches only B/C/F, only adds exposure, and is a no-op without a fast reading")

check_fast_reentry()

def check_extension_trim():
    """Graded extension trim (2026-09-06): only effective state A, one vote
    per window above its threshold, x2/3 / x1/3 / x0 (step 1/3), no-op
    without gaps; the legacy single-window path still works."""
    from state import (extension_votes, extension_scale, is_extended, EXTENSION_RULES,
                       EXTENSION_STEP, EXTENSION_TRIM_ENABLED, target_weights_with_voltarget)
    assert EXTENSION_TRIM_ENABLED and EXTENSION_RULES == ((100, 0.10), (150, 0.12), (200, 0.15)) and abs(EXTENSION_STEP - 1/3) < 1e-12
    hot = {100: 0.2, 150: 0.2, 200: 0.2}; cold = {100: 0.0, 150: 0.0, 200: 0.0}
    for st in 'BCDEF':
        assert extension_votes(st, hot) == 0 and not is_extended(st, hot)
        assert target_weights_with_voltarget(st, False, 0.15, gaps=hot) == target_weights_with_voltarget(st, False, 0.15)
    assert extension_votes('A', cold) == 0 and extension_votes('A', hot) == 3
    assert extension_votes('A', {100: 0.11, 150: 0.0, 200: 0.0}) == 1
    assert extension_votes('A', {100: 0.11, 150: 0.13, 200: 0.0}) == 2
    assert extension_votes('A', {100: None, 150: None, 200: 0.16}) == 1
    assert abs(extension_scale('A', hot)) < 1e-12 and extension_scale('A', cold) == 1.0
    full = target_weights_with_voltarget('A', False, 0.15, fast_state='A', gaps=cold)
    for votes, g in ((1, {100: 0.11, 150: 0.0, 200: 0.0}), (2, {100: 0.11, 150: 0.13, 200: 0.0}), (3, hot)):
        t = target_weights_with_voltarget('A', False, 0.15, fast_state='A', gaps=g)
        f = 1 - votes / 3
        assert abs(sum(t) - 1.0) < 1e-9 and all(abs(t[i] - full[i] * f) < 1e-9 for i in range(4)), votes
    assert target_weights_with_voltarget('C', False, 0.15, fast_state='A', gaps=hot) == target_weights_with_voltarget('A', False, 0.15, fast_state='A', gaps=hot)
    assert target_weights_with_voltarget('A', False, 0.15, gaps=None) == target_weights_with_voltarget('A', False, 0.15)
    legacy = target_weights_with_voltarget('A', False, 0.15, gap200=0.2)
    assert all(abs(legacy[i] - full[i] * 0.5) < 1e-9 for i in range(4))
    print("OK: graded extension trim -- effective A only, one vote per window, x2/3 / x1/3 / x0, no-op without gaps, legacy path intact")


check_extension_trim()


def check_strategy_md_matches_code():
    """STRATEGY.md's Part I weight tables must match state.py (2026-09-07).

    An outside review found the detailed weight table still showing A =
    50/50 and the overlay chain still showing 0.25 per vote, two days after
    the code moved to 40/60 and 1/3 -- a live spec that contradicted the
    code it documents. The tables are now generated by gen_live_tables.py;
    this asserts the file agrees with the generator."""
    import os
    from gen_live_tables import full_table, glance_table
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'STRATEGY.md')
    part1 = open(path).read().split('# Part II')[0]
    for name, tbl in (('full weight table', full_table()), ('at-a-glance table', glance_table())):
        for row in tbl.split('\n')[2:]:
            assert row in part1, f"STRATEGY.md {name} disagrees with state.py; missing row:\n  {row}\nRun: python3 paper-track/gen_live_tables.py"
    print("OK: STRATEGY.md Part I weight tables match state.py")


def _at(eff, held=0, base=(0.50, 0.50)):
    """A minimal a_trim dict (extension trim v2) for unit checks."""
    if eff == 'A':
        return dict(date='x', eff='A', in_a=True, spell_start='2026-08-04', base=base, raw=0, held=held)
    return dict(date='x', eff=eff, in_a=False, spell_start=None, base=None, raw=0, held=0)


def check_live_target_weights_strict():
    """live_target_weights() must REFUSE missing overlay inputs (2026-09-07).

    target_weights_with_voltarget() accepts fast_state=None/gaps=None so old
    backtests still run; a live caller that forgot one silently traded the
    pre-overlay design. The live entry point now raises instead."""
    from state import (live_target_weights, MissingOverlayInputs,
                       target_weights_with_voltarget, FAST_REENTRY_ENABLED,
                       EXTENSION_TRIM_ENABLED)
    assert FAST_REENTRY_ENABLED and EXTENSION_TRIM_ENABLED
    good = {100: 0.0, 150: 0.0, 200: 0.0}
    for bad_fast, bad_gaps, why in ((None, good, 'fast_state None'),
                                    ('Z', good, 'fast_state invalid'),
                                    ('A', None, 'gaps None'),
                                    ('A', {100: 0.0}, 'gaps missing windows')):
        try:
            live_target_weights('A', False, 0.15, bad_fast, bad_gaps, 0.5, _at('A'))
        except MissingOverlayInputs:
            pass
        else:
            raise AssertionError(f"live_target_weights accepted {why}")
    for bad_at, why in ((None, 'a_trim None'), ({}, 'a_trim empty'), (_at('C'), 'a_trim not in A on an A day')):
        try:
            live_target_weights('A', False, 0.15, 'A', good, 0.5, bad_at)
        except MissingOverlayInputs:
            pass
        else:
            raise AssertionError(f"live_target_weights accepted {why}")
    try:
        live_target_weights('C', False, 0.15, 'C', good, 0.5, _at('A'))
    except MissingOverlayInputs:
        pass
    else:
        raise AssertionError("live_target_weights accepted an in-A a_trim on a C day")
    a = live_target_weights('A', False, 0.15, 'A', good, 0.5, _at('A'))
    b = target_weights_with_voltarget('A', False, 0.15, fast_state='A', gaps=good, a_trim=_at('A'))
    assert a == b, "live_target_weights must not change the maths"
    assert live_target_weights('A', False, None, 'A', good, 0.5, _at('A'))  # vol=None still allowed
    print("OK: live_target_weights rejects missing/!invalid overlay inputs, maths unchanged")


check_strategy_md_matches_code()
check_live_target_weights_strict()


def check_d_gate():
    """State-D gate (APPLIED 2026-09-19, owner override): breadth pct < 0.20
    OR close < 2% above the 200d SMA sends a macro-D day to 100% cash; every
    other state is untouched; the live function refuses a missing breadth
    reading; the permissive function with d_gate=None is the pre-gate design."""
    from state import (D_GATE_ENABLED, D_GATE_BREADTH_PCT, D_GATE_GAP200, d_gate_flags, d_gate_active,
                       live_target_weights, target_weights_with_voltarget, MissingOverlayInputs, STATE_LABEL)
    import breadth_tracker as BT
    assert D_GATE_ENABLED, "the state-D gate is applied (2026-09-19); flipping it off is a design change"
    assert D_GATE_BREADTH_PCT == BT.GATE_PCT == 0.20, "gate percentile must equal breadth_tracker.GATE_PCT"
    assert D_GATE_GAP200 == 0.02
    assert d_gate_flags(0.19, 0.05) == (True, False) and d_gate_flags(0.5, 0.019) == (False, True)
    assert d_gate_flags(0.20, 0.02) == (False, False), "thresholds are strict '<'"
    assert d_gate_flags(None, None) == (False, False), "warm-up never flags"
    cold = {100: 0.05, 150: 0.05, 200: 0.05}; hot = {100: 0.05, 150: 0.05, 200: 0.01}
    for st in STATE_LABEL:
        assert d_gate_active(st, 0.1, 0.0) == (st == 'D'), f"gate must only act in D, not {st}"
        if st != 'D':
            from state import effective_state as _eff
            at = _at(_eff(st, st))
            assert live_target_weights(st, False, 0.15, st, hot, 0.1, at) == \
                target_weights_with_voltarget(st, False, 0.15, fast_state=st, gaps=hot, a_trim=at), f"gate moved state {st}"
    cash = (0.0, 0.0, 0.0, 0.0, 1.0)
    assert live_target_weights('D', False, 0.15, 'D', cold, 0.5, _at('D')) == (0.0, 0.0, 1.0, 0.0, 0.0), "ungated D is 100% QLD"
    assert live_target_weights('D', False, 0.15, 'D', hot, 0.5, _at('D')) == cash, "gap200 half must gate"
    assert live_target_weights('D', False, 0.15, 'D', cold, 0.1, _at('D')) == cash, "breadth half must gate"
    assert live_target_weights('D', False, 0.50, 'D', cold, 0.1, _at('D')) == cash, "gate ignores the vol multiplier"
    assert target_weights_with_voltarget('D', False, 0.15, fast_state='D', gaps=hot) == (0.0, 0.0, 1.0, 0.0, 0.0), \
        "d_gate=None must be the pre-gate design (research harnesses depend on this)"
    for bad in (None, 'x', 1.5, -0.1, True):
        try:
            live_target_weights('D', False, 0.15, 'D', cold, bad, _at('D'))
        except MissingOverlayInputs:
            pass
        else:
            raise AssertionError(f"live_target_weights accepted breadth_pct={bad!r}")
    print("OK: state-D gate -- breadth<0.20 OR gap200<2% -> cash on D only; live function refuses a missing breadth reading")


check_d_gate()


def check_extension_scale_floor():
    """extension_scale() is floored at zero (APPLIED 2026-09-20, owner
    decision -- a safety fix with NO behaviour change at the live step).

    Without the floor any EXTENSION_STEP above 1 / len(EXTENSION_RULES) returns
    a negative multiplier at maximum votes, target_weights_with_voltarget hands
    back negative risky weights, validate_weights raises, and the live trigger
    ABORTS on exactly the days the trim should act. This check asserts (a) the
    floor holds at every step a future revision might pick, (b) it is a no-op
    at the live step, so every figure on record still stands, and (c) the live
    step and rule count are still the pair that lands on exactly zero."""
    import state as _S
    from state import (extension_scale, extension_votes, EXTENSION_STEP, EXTENSION_RULES,
                       target_weights_with_voltarget, validate_weights)
    nrules = len(EXTENSION_RULES)
    hot = {n: t + 0.10 for n, t in EXTENSION_RULES}          # every rule fires
    cold = {n: t - 0.05 for n, t in EXTENSION_RULES}         # none fires
    assert extension_votes('A', hot) == nrules and extension_votes('A', cold) == 0

    # (c) live step x rule count lands on exactly zero -- the reason no floor was needed before
    assert abs(1.0 - EXTENSION_STEP * nrules) < 1e-12, \
        "live EXTENSION_STEP x rule count must land on exactly 0.0 at full votes"
    # (b) no-op at the live step: the floor changes nothing at any vote count
    for v in range(nrules + 1):
        g = {n: (t + 0.10 if i < v else t - 0.05) for i, (n, t) in enumerate(EXTENSION_RULES)}
        assert abs(extension_scale('A', g) - (1.0 - EXTENSION_STEP * v)) < 1e-12, \
            f"floor must be a no-op at the live step ({v} votes)"
    # (a) the floor holds for any step a revision might pick, and the row stays sane
    base = _S.EXTENSION_STEP
    try:
        for step in (0.25, 1.0 / 3.0, 0.4, 0.5, 0.75, 1.0, 2.0):
            _S.EXTENSION_STEP = step
            for g in (cold, hot):
                sc = extension_scale('A', g)
                assert sc >= 0.0, f"extension_scale went negative at step {step}"
                assert sc <= 1.0 + 1e-12
            w = target_weights_with_voltarget('A', False, 0.15, fast_state='A', gaps=hot)
            validate_weights("A", *w)         # must not raise at any step
            assert abs(sum(w) - 1.0) < 1e-12 and min(w) >= -1e-12, f"weights unsane at step {step}"
        _S.EXTENSION_STEP = 0.5
        assert target_weights_with_voltarget('A', False, 0.15, fast_state='A', gaps=hot)[4] == 1.0, \
            "at step 0.5 and full votes the A row must be 100% cash, not a short"
    finally:
        _S.EXTENSION_STEP = base
    assert _S.EXTENSION_STEP == base
    print(f"OK: extension_scale floored at 0 -- no-op at the live step {EXTENSION_STEP:.4f} "
          f"x {nrules} rules, and no step can produce a negative risky weight")


check_extension_scale_floor()


def check_vol_estimator():
    """max(vol10, vol30) estimator (2026-09-07): may only RAISE the vol
    estimate, hence only shrink the multiplier; None-handling unchanged."""
    import math
    from state import (realized_vol, realized_vol_live, VOL_LOOKBACK_DAYS,
                       VOL_FAST_LOOKBACK_DAYS, VOL_ESTIMATOR_MAX_ENABLED,
                       vol_target_multiplier)
    import state as _S
    assert VOL_ESTIMATOR_MAX_ENABLED is False, "2026-09-09: the max(10,30) leg is DISABLED by owner decision; flip this assertion deliberately, not by accident"
    assert VOL_FAST_LOOKBACK_DAYS == 10 and VOL_LOOKBACK_DAYS == 30
    # a calm series with one violent recent stretch: fast must dominate
    dates = [f"d{i:03d}" for i in range(80)]
    px = {}
    v = 100.0
    for i, d in enumerate(dates):
        v *= 1 + (0.0005 if i < 65 else (0.05 if i % 2 else -0.05))
        px[d] = v
    slow = realized_vol(dates, px, lookback=30)
    fast = realized_vol(dates, px, lookback=10)
    live = realized_vol_live(dates, px)
    assert fast > slow, "test series should have a hotter fast window"
    assert live == slow, "flag OFF: realized_vol_live must be the plain 30d even when the 10d is hotter"
    # the max path must still work when re-enabled by flag (kept, not dead code)
    _S.VOL_ESTIMATOR_MAX_ENABLED = True
    try:
        on = realized_vol_live(dates, px)
        assert on == max(slow, fast) == fast
        assert vol_target_multiplier(on) <= vol_target_multiplier(slow), "max estimator must not lever UP"
    finally:
        _S.VOL_ESTIMATOR_MAX_ENABLED = False
    # calm throughout: fast below slow -> live must equal slow, never the lower fast
    # volatile through i=69 then calm: the 30d window (50..79) straddles both,
    # the 10d window (70..79) is calm, so fast < slow.
    dates2 = [f"e{i:03d}" for i in range(80)]
    px2 = {}
    v = 100.0
    for i, d in enumerate(dates2):
        v *= 1 + (0.0005 if i >= 70 else (0.04 if i % 2 else -0.04))
        px2[d] = v
    s2 = realized_vol(dates2, px2, lookback=30)
    f2 = realized_vol(dates2, px2, lookback=10)
    assert f2 < s2 and realized_vol_live(dates2, px2) == s2, "must be the SLOW reading"
    # insufficient history -> None, same as the 30d estimator
    short = [f"s{i:02d}" for i in range(12)]
    spx = {d: 100.0 + i for i, d in enumerate(short)}
    assert realized_vol(short, spx, lookback=30) is None
    assert realized_vol_live(short, spx) is None, "None-handling must match the 30d estimator"
    assert vol_target_multiplier(None) == 1.0
    print("OK: vol estimator -- plain 30d live (max(10,30) leg disabled 2026-09-09), max path still correct if re-enabled, None-safe")


check_vol_estimator()


def check_fill_quality():
    """Execution-quality tracker (2026-09-07): slippage must be COST-POSITIVE
    for both sides, notional-weighted, and must refuse bad input rather than
    returning a plausible-looking number."""
    import tempfile, os
    from fill_quality import slippage_bps, record_fill, summarize
    # a buy filled ABOVE the reference is a cost; a sell BELOW it is a cost
    assert abs(slippage_bps('buy', 101.0, 100.0) - 100.0) < 1e-9
    assert abs(slippage_bps('sell', 99.0, 100.0) - 100.0) < 1e-9
    # beating the reference is negative (a gain)
    assert slippage_bps('buy', 99.0, 100.0) < 0 and slippage_bps('sell', 101.0, 100.0) < 0
    assert slippage_bps('buy', 100.0, 100.0) == 0.0
    for bad in (('buy', None, 100.0), ('buy', 100.0, None), ('buy', 0.0, 100.0),
                ('buy', 100.0, -1.0), ('hold', 100.0, 100.0)):
        try:
            slippage_bps(*bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"slippage_bps accepted {bad!r}")
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'fq.csv')
        # big leg slightly bad, tiny leg very bad -> weighted must track the BIG one
        record_fill('2026-09-08', 'TQQQ', 'buy', 1000, 100.10, 100.0, path=p)
        record_fill('2026-09-08', 'BOXX', 'sell', 1, 99.0, 100.0, path=p)
        s = summarize(path=p)
        assert s['n'] == 2
        assert 9.0 < s['weighted_bps'] < 12.0, s['weighted_bps']
        assert 54.0 < s['simple_bps'] < 56.0, s['simple_bps']
        assert s['worst']['symbol'] == 'BOXX' and len(s['flagged']) == 1
        assert summarize(path=os.path.join(d, 'missing.csv'))['n'] == 0
    print("OK: fill-quality tracker -- cost-positive both sides, notional-weighted, rejects bad input")


check_fill_quality()


def check_breadth_tracker():
    """The breadth forward test is measurement only: the percentile function is
    the research one, the gate flag follows GATE_PCT, the log round-trips, and
    nothing here can change a weight (no import of the weight functions)."""
    import tempfile, os
    from breadth_tracker import (trailing_pct, breadth_reading, bucket_base_rate, record_d_day,
                                 fill_next_returns, summarize, GATE_PCT, LOOKBACK, WINDOW)
    assert (GATE_PCT, LOOKBACK, WINDOW) == (0.20, 60, 252), "frozen for the forward test"
    v = list(range(300))
    p = trailing_pct(v, 252)
    assert p[250] is None and p[251] is not None and abs(p[299] - (251.5 / 252)) < 1e-12
    assert trailing_pct([1.0, None, 2.0] * 200, 3) == [None] * 600, "a None must reset the window"
    n = 400; dates = [f'{i:04d}' for i in range(n)]
    qqq = {d: 100.0 * (1.0005 ** i) for i, d in enumerate(dates)}
    qqew = {d: 100.0 * (1.0005 ** i) * (0.999 ** max(0, i - (n - 60))) for i, d in enumerate(dates)}
    r = breadth_reading(dates, qqew, qqq)
    assert r['pct'] is not None and r['pct'] < GATE_PCT and r['gate'] is True
    r0 = breadth_reading(dates[:100], qqew, qqq)
    assert r0['pct'] is None and r0['gate'] is False, "insufficient history must read None/False"
    assert bucket_base_rate(0.1) == 0.54 and bucket_base_rate(0.5) == 0.05 and bucket_base_rate(1.0) == 0.30
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, 'log.csv')
        assert record_d_day('2030-01-02', 'D', r['x60'], r['pct'], r['gate'], path=path) is True
        assert record_d_day('2030-01-02', 'D', r['x60'], r['pct'], r['gate'], path=path) is False, "idempotent"
        try:
            record_d_day('2030-01-03', 'A', 0.0, 0.5, False, path=path)
        except ValueError:
            pass
        else:
            raise AssertionError("record_d_day accepted a non-D day")
        fill_next_returns('2030-01-02', -0.02, -0.01, path=path)
        sm = summarize(path)
        assert sm['n_d_days'] == 1 and sm['n_gated_runs'] == 1 and sm['runs_negative'] == 1 and sm['decision_due'] is False
    print("OK: breadth tracker -- research percentile, gate flag, log round-trip, measurement only")


check_breadth_tracker()


def check_funding_policy():
    """Funding amounts are computed in code, never hand-added in prose (the
    project's standing rule). Frozen constants: 2% base, mild escalation
    1/1.5/2/2.5x at the four DD_THRESHOLDS tiers, turn at the flat base."""
    from funding_policy import (BASE_PCT, TIER_MULT, TURN_MULT, tier_funding_amount,
                                turn_funding_amount, schedule_table)
    from drawdown_tracker import DD_THRESHOLDS
    assert BASE_PCT == 0.02
    assert TIER_MULT == {0.05: 1.0, 0.10: 1.5, 0.15: 2.0, 0.20: 2.5}
    assert TURN_MULT == 1.0
    assert set(TIER_MULT) == set(DD_THRESHOLDS), "funding tiers must match the drawdown tiers exactly"
    assert tier_funding_amount(198_000, 0.05) == 3960
    assert tier_funding_amount(198_000, 0.20) == 9900
    assert turn_funding_amount(198_000) == 3960
    assert tier_funding_amount(100_000, 0.05) == turn_funding_amount(100_000) == 2000, "tier 1 == turn at the same account value (both 1x base)"
    sched = schedule_table(500_000)
    assert sched[0.20] == 25_000 and sched['turn'] == 10_000
    for bad in (0.0, -100):
        try:
            tier_funding_amount(bad, 0.05)
        except ValueError:
            pass
        else:
            raise AssertionError(f"tier_funding_amount accepted account_value={bad!r}")
    try:
        tier_funding_amount(198_000, 0.25)
    except ValueError:
        pass
    else:
        raise AssertionError("tier_funding_amount accepted an unknown tier")
    print("OK: funding policy -- 2% base, mild escalation, tiers match DD_THRESHOLDS, rejects bad input")


check_funding_policy()


def check_extension_trim_v2():
    """Extension trim v2 (APPLIED 2026-09-23, owner decision): TQQQ out entirely
    at the first held vote, core x (1 - held/6), held votes rise at once and come
    off one at a time only on a new 15-session closing high and never below the
    raw count, reset on leaving A; A spells starting on/after 2026-09-23 hold
    30/70. Checked on the real QQQ history (a pure function of closes)."""
    import csv, os
    from state import (EXTENSION_TRIM_V2_ENABLED, EXTENSION_REENTRY_HIGH_N, EXTENSION_CORE_CUT_PER_VOTE,
                       A_BASE_ROWS, a_base_row, a_trim_row, a_trim_series, a_trim_state, validate_weights,
                       target_weights_with_voltarget, live_target_weights)
    assert EXTENSION_TRIM_V2_ENABLED and EXTENSION_REENTRY_HIGH_N == 15 and abs(EXTENSION_CORE_CUT_PER_VOTE - 1 / 6) < 1e-12
    assert a_base_row('2026-08-04') == (0.50, 0.50) and a_base_row('2026-09-23') == (0.30, 0.70) and a_base_row('2027-01-04') == (0.30, 0.70)
    for base in ((0.50, 0.50), (0.30, 0.70)):
        for held in range(4):
            r = a_trim_row(base, held)
            validate_weights('A', *r)
            assert (r[1] == base[1]) if held == 0 else (r[1] == 0.0), "TQQQ is all-in at 0 held votes, all-out otherwise"
            assert abs(r[0] - base[0] * (1 - held / 6)) < 1e-12
    assert a_trim_row((0.5, 0.5), 3) == (0.25, 0.0, 0.0, 0.0, 0.75)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    px = {r['d']: float(r['c']) for r in csv.DictReader(open(os.path.join(root, 'data', 'qqq_long_history.csv')))}
    ds = sorted(px); ser = a_trim_series(ds, px); closes = [px[d] for d in ds]
    prev = None; nsteps = 0
    for i, d in enumerate(ds):
        x = ser[d]
        if not x['in_a']:
            assert x['held'] == 0 and x['base'] is None
        else:
            assert x['held'] >= x['raw'], f"{d}: held below raw"
            assert x['base'] == a_base_row(x['spell_start'])
            if prev is not None and prev['in_a'] and x['held'] < prev['held']:
                assert prev['held'] - x['held'] == 1, f"{d}: stepped more than one vote"
                assert closes[i] >= max(closes[max(0, i - EXTENSION_REENTRY_HIGH_N + 1):i + 1]), f"{d}: stepped without a 15-session high"
                nsteps += 1
        prev = x
    assert nsteps >= 20, "the step-down rule fires (25 times on the 1999-2026 history)"
    t = a_trim_state(ds, px, as_of='2026-09-04')
    assert t['in_a'] and t['spell_start'] == '2026-08-04' and t['held'] == 0 and t['base'] == (0.50, 0.50), t
    x = ser['2018-02-02']
    assert x['in_a'] and x['held'] == 3, "Feb 2018: v2 holds the trim through the break (v1 had re-levered)"
    w = target_weights_with_voltarget('A', False, 0.15, fast_state='A', gaps={100: 0.0, 150: 0.0, 200: 0.0},
                                      a_trim=dict(t, held=2))
    assert w == a_trim_row((0.50, 0.50), 2), "a_trim overrides the v1 gaps scaling in A"
    # history-length safety (review 2026-09-23): a 24-month pull + backfill equals the full history;
    # without backfill a short series is REFUSED rather than read wrongly
    from state import A_TRIM_MIN_HISTORY, MissingOverlayInputs
    tail = ds[-504:]; sub = {d: px[d] for d in tail}
    for d in tail[-40:]:
        assert a_trim_state(tail, sub, as_of=d) == ser[d], f"{d}: 24-month pull + backfill disagrees with full history"
    short = ds[-(A_TRIM_MIN_HISTORY - 10):]
    try:
        a_trim_state(short, {d: px[d] for d in short}, backfill=False)
    except MissingOverlayInputs:
        pass
    else:
        raise AssertionError("a_trim_state accepted a series shorter than A_TRIM_MIN_HISTORY")
    print(f"OK: extension trim v2 -- TQQQ out at the first held vote, one-vote steps only on new "
          f"{EXTENSION_REENTRY_HIGH_N}-day highs ({nsteps} steps since 1999), never below raw, reset outside A, "
          f"30/70 for A spells from 2026-09-23; 24-month pull + backfill == full history; short series refused")


check_extension_trim_v2()
