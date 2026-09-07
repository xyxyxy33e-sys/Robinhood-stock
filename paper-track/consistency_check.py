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
            live_target_weights('A', False, 0.15, bad_fast, bad_gaps)
        except MissingOverlayInputs:
            pass
        else:
            raise AssertionError(f"live_target_weights accepted {why}")
    a = live_target_weights('A', False, 0.15, 'A', good)
    b = target_weights_with_voltarget('A', False, 0.15, fast_state='A', gaps=good)
    assert a == b, "live_target_weights must not change the maths"
    assert live_target_weights('A', False, None, 'A', good)  # vol=None still allowed
    print("OK: live_target_weights rejects missing/!invalid overlay inputs, maths unchanged")


check_strategy_md_matches_code()
check_live_target_weights_strict()


def check_vol_estimator():
    """max(vol10, vol30) estimator (2026-09-07): may only RAISE the vol
    estimate, hence only shrink the multiplier; None-handling unchanged."""
    import math
    from state import (realized_vol, realized_vol_live, VOL_LOOKBACK_DAYS,
                       VOL_FAST_LOOKBACK_DAYS, VOL_ESTIMATOR_MAX_ENABLED,
                       vol_target_multiplier)
    assert VOL_ESTIMATOR_MAX_ENABLED and VOL_FAST_LOOKBACK_DAYS == 10 and VOL_LOOKBACK_DAYS == 30
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
    assert live == max(slow, fast) == fast
    assert vol_target_multiplier(live) <= vol_target_multiplier(slow), "max estimator must not lever UP"
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
    assert f2 < s2 and realized_vol_live(dates2, px2) == s2, "must fall back to the SLOW reading, not the min"
    # insufficient history -> None, same as the 30d estimator
    short = [f"s{i:02d}" for i in range(12)]
    spx = {d: 100.0 + i for i, d in enumerate(short)}
    assert realized_vol(short, spx, lookback=30) is None
    assert realized_vol_live(short, spx) is None, "None-handling must match the 30d estimator"
    assert vol_target_multiplier(None) == 1.0
    print("OK: vol estimator max(10d, 30d) -- only raises vol, never levers up, None-safe")


check_vol_estimator()
