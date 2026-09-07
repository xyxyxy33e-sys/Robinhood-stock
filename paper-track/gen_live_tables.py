"""Emit the canonical live-design tables FROM state.py.

Added 2026-09-07 after an outside review found STRATEGY.md's detailed weight
table still showing A = 50/50 and the overlay chain still showing 0.25 per
vote, days after the code moved to 40/60 and 1/3. Hand-maintained duplicates
of the weights drift; these are generated, and consistency_check.py asserts
STRATEGY.md agrees with this output.  Usage: python3 paper-track/gen_live_tables.py
"""
import sys
sys.path.insert(0, 'paper-track')
from state import (TARGET_WEIGHTS, EXTENSION_RULES, EXTENSION_STEP, STATE_LABEL,
                   VOL_TARGET_PA, VOL_LOOKBACK_DAYS, VOL_FAST_LOOKBACK_DAYS,
                   VOL_ESTIMATOR_MAX_ENABLED, FAST_SHORT_N, FAST_LONG_N)

LEV = (1.0, 3.0, 2.0, 0.5, 0.0)   # core, TQQQ, QLD, XLU, cash


def exposure(w):
    return sum(x * l for x, l in zip(w, LEV))


def expfmt(e):
    """2 decimals below 1x so state E reads 0.25x, not a misleading 0.2x."""
    return f"{e:.2f}x" if e < 1 else f"{e:.1f}x"


def pct(x):
    return f"{x * 100:.0f}%"


def glance_table():
    out = ["| State | Holds | Effective exposure |", "|---|---|---|"]
    for st in 'ABCDEF':
        c, t, q, x, k = TARGET_WEIGHTS[st]
        parts = [(c, 'SPMO'), (t, 'TQQQ'), (q, 'QLD'), (x, 'XLU'), (k, 'BOXX')]
        holds = ' / '.join(f"{pct(v)} {n}" for v, n in parts if v > 0)
        out.append(f"| {st} | {holds} | {expfmt(exposure(TARGET_WEIGHTS[st]))} |")
    return '\n'.join(out)


def full_table():
    out = ["| State | Core | TQQQ (3x) | QLD (2x) | XLU | Cash (BOXX) | Effective exposure |",
           "|---|---|---|---|---|---|---|"]
    for st in 'ABCDEF':
        w = TARGET_WEIGHTS[st]
        out.append(f"| {st} | " + " | ".join(pct(v) for v in w) + f" | {expfmt(exposure(w))} |")
    return '\n'.join(out)


def overlay_chain():
    steps = ' / '.join(f"x{round(1 - EXTENSION_STEP * v, 4):g}"
                       for v in range(1, len(EXTENSION_RULES) + 1))
    rules = ', '.join(f"{n}d > {t * 100:.0f}%" for n, t in EXTENSION_RULES)
    return (f"extension trim: votes over ({rules}); risky legs of the A row scaled by "
            f"1 - {EXTENSION_STEP:.4g} x votes ({steps}); "
            f"fast re-entry {FAST_SHORT_N}/{FAST_LONG_N}; "
            f"vol target {VOL_TARGET_PA:.0%} on "
            + (f"max({VOL_FAST_LOOKBACK_DAYS}d, {VOL_LOOKBACK_DAYS}d)" if VOL_ESTIMATOR_MAX_ENABLED
               else f"{VOL_LOOKBACK_DAYS}d")
            + " realized vol")


if __name__ == '__main__':
    print("## At a glance\n"); print(glance_table())
    print("\n## Full weight table\n"); print(full_table())
    print("\n## Overlay chain\n"); print(overlay_chain())
