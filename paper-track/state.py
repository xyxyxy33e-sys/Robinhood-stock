"""SPMO core + TQQQ satellite regime overlay -- state machine, ported from
xyxyxy33e-sys/robinhood research/leverage_ma.md so the paper track has no
dependency on that repo staying checked out.

Six-state classifier on QQQ (market signal, per the study's finding 3),
1% hysteresis buffer, 50/200-day SMAs.
"""
import csv

def load_csv(path):
    out = {}
    for r in csv.DictReader(open(path)):
        try: out[r['d']] = float(r['c'])
        except Exception: pass
    return out

def sma(v, i, n):
    return sum(v[i-n+1:i+1])/n if i >= n-1 else None

def compute_states(dates, px, buf=0.01):
    v = [px[d] for d in dates]
    s50 = s200 = None
    out = []
    for i, d in enumerate(dates):
        m50, m200 = sma(v, i, 50), sma(v, i, 200)
        if m200 is None:
            out.append('F'); continue
        if v[i] > m50*(1+buf): s50 = True
        elif v[i] < m50*(1-buf): s50 = False
        if v[i] > m200*(1+buf): s200 = True
        elif v[i] < m200*(1-buf): s200 = False
        cross = m50 > m200
        if s50 and s200 and cross: out.append('A')
        elif s50 and s200 and not cross: out.append('B')
        elif s50 and not s200: out.append('C')
        elif not s50 and s200: out.append('D')
        elif not s50 and not s200 and cross: out.append('E')
        else: out.append('F')
    return out

# Study default (research/leverage_ma.md, 35% cap variant). Kept for reference/backtests.
SAT_WEIGHT_35 = dict(A=0.35, B=0.35, C=0.0, D=0.15, E=0.15, F=0.0)

# TARGET_WEIGHTS is the single source of truth: (core, satellite, cash) per state,
# each row summing to 1.0. Every earlier per-constant version of this file (LIVE
# satellite mapping + EF_CORE_WEIGHT + D_CASH_WEIGHT) has been folded in here as
# history moved through it -- see below per state for what was tested and why.
# cash is deployed into CASH_INSTRUMENT (BOXX), not held as raw buying power.
#
# A (0.65, 0.35, 0.0) -- established uptrend, 60.4% of history. Sharpe plateau
#   0.30-0.40 satellite (~0.964), current 0.35 sits in it. Core/cash axis tested
#   separately: shallow peak near core=55%/cash=10% (Sharpe +0.0015 over full
#   deployment) -- inside the noise floor of everything else tested, left alone.
#
# B (0.25, 0.75, 0.0) -- reclaim, 3.5% of history, only 4 independent episodes
#   (22/16/30/29 trading days each) in the whole 10.9yr window. EVERY axis tested
#   here points the same direction -- more satellite, not less, no cash -- and the
#   curve doesn't turn over until ~80% satellite (Sharpe 0.976) or on the core/cash
#   axis at all (monotonic to full deployment). Search/holdout split (2020-01-01)
#   improves in BOTH halves as satellite rises (search 1.045->1.077, holdout
#   0.960->0.966 at 30/70), which is some evidence against pure overfitting, but
#   with only 4 episodes that "holdout confirmation" is really 1-2 episodes on each
#   side reshuffled, not independent validation. 25/75 chosen by the user as a
#   deliberately conservative pick relative to the ~80% satellite peak the raw
#   sweep found -- treat the DIRECTION as more trustworthy than the MAGNITUDE.
#
# C (1.0, 0.0, 0.0) -- bounce in downtrend, 4.2% of history. Confirmed: satellite
#   strictly hurts (never tested nonzero, no data suggested it should be), and core
#   weight vs cash is monotonic all the way to 100% core -- stay fully invested.
#
# D (0.55, 0.20, 0.25) -- pullback in uptrend, 13.5% of history, second-most after
#   A. Satellite sweep flattens 20-25%, core/cash sweep (satellite held fixed)
#   plateaus at core 50-57% (peak Sharpe 0.964). Search/holdout: FULL 0.957->0.964,
#   SEARCH 0.995->1.047 (improvement), HOLDOUT 0.970->0.959 (small decline) --
#   roughly a wash to modestly positive. 25% cash chosen by the user as a round
#   number inside the flat part of the plateau (core becomes 1-0.20-0.25=0.55).
#
# E (0.50, 0.0, 0.50) -- breakdown, 4.2% of history. Satellite: adding ANY strictly
#   hurts (monotonic decline from 0%). Core/cash: broad plateau 44-50% core, current
#   50% sits in it (peak ~47%, indistinguishable from 50% given the flatness).
#
# F (0.30, 0.0, 0.70) -- established downtrend, 14.3% of history, THIRD-most after
#   A and D -- not a fringe case. Satellite: same as E, adding any strictly hurts,
#   and hurts FASTER than E does. Core/cash: unlike every other state tested, max
#   drawdown is COMPLETELY PINNED at -32.3% across the entire 0-100% core sweep --
#   whatever sets the account's worst drawdown, it isn't happening during F. Peak
#   Sharpe 0.9654-0.9655 on a broad plateau at core 27-37%; the old EF_CORE_WEIGHT
#   design shared 50% with E, which was too high specifically because of F. 30%
#   chosen inside that plateau.
#
# Combined effect of the B and F changes vs the prior uniform-B/EF design, tested
# together 2026-08-29: SPMO-core full window Sharpe 0.964->0.978 (CAGR 25.4%->26.5%,
# MDD unchanged -32.3%), mirror-core Sharpe 1.021->1.027. Same drawdown either way on
# both cores -- this reads as a real efficiency gain, not a risk trade-off, but B's
# thin sample (4 episodes) means it carries much less confidence than F's (which
# rests on 14.3% of history, the same order of evidence as D).
TARGET_WEIGHTS = {
    'A': (0.65, 0.35, 0.00),
    'B': (0.25, 0.75, 0.00),
    'C': (1.00, 0.00, 0.00),
    'D': (0.55, 0.20, 0.25),
    'E': (0.50, 0.00, 0.50),
    'F': (0.30, 0.00, 0.70),
}

# Derived for backward compatibility with anything that reads the satellite mapping
# on its own (e.g. earlier trigger prompts, the published evaluation artifact).
SAT_WEIGHT_LIVE = {s: w[1] for s, w in TARGET_WEIGHTS.items()}

# The "cash" leg of target_weights() is held as BOXX (Alpha Architect 1-3 Month Box
# ETF), not literal uninvested buying power -- user preference, 2026-08-29. Backtested
# effect is negligible (BOXX tracks the T-bill proxy within ~0.16pp/yr, its own expense
# ratio; whole-strategy Sharpe identical to 3 decimal places using either as the cash
# return). The reason to hold it instead of plain cash is tax deferral: BOXX has no
# current income while held, unlike a cash sweep or a T-bill, which both pay taxable
# interest every period. Its 60/40 long-term/short-term blended rate under Section 1256
# does NOT apply here -- every gated state here runs weeks to months, so any BOXX sale
# will still be a short-term gain, same as everything else in this account. Confirmed
# tradable, fractional, in the live account (576391551) on 2026-08-29.
CASH_INSTRUMENT = 'BOXX'

def target_weights(state):
    """Returns (core_weight, satellite_weight, cash_weight) for a given state letter,
    straight from TARGET_WEIGHTS -- the single source of truth. cash_weight is
    deployed into CASH_INSTRUMENT (BOXX), not held as raw buying power."""
    return TARGET_WEIGHTS[state]

STATE_LABEL = dict(
    A='established uptrend', B='reclaim', C='bounce in downtrend',
    D='pullback in uptrend', E='breakdown', F='established downtrend',
)

class WeightSanityError(ValueError):
    """Raised when a computed (state, core, satellite, cash) tuple fails validation.
    Every live trigger must call validate_weights() before placing any order and
    abort the rebalance (report, do not trade) if this raises -- added 2026-08-29
    after the strategy grew to three weight legs across 17 instruments with no
    guard between "compute a state" and "place real orders"."""
    pass

def validate_weights(state, core, sat, cash, tol=0.005):
    if state not in STATE_LABEL:
        raise WeightSanityError(f"state {state!r} is not one of {sorted(STATE_LABEL)}")
    for name, w in (('core', core), ('satellite', sat), ('cash', cash)):
        if not (-tol <= w <= 1.0 + tol):
            raise WeightSanityError(f"{name}_weight={w!r} out of [0,1] range for state {state}")
    total = core + sat + cash
    if abs(total - 1.0) > tol:
        raise WeightSanityError(
            f"weights for state {state} sum to {total:.4f}, expected 1.0 +/- {tol} "
            f"(core={core}, sat={sat}, cash={cash})"
        )
