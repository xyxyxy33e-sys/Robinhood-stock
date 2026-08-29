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

# LIVE mapping -- user-specified 2026-08-29, raises D and zeroes E relative to the
# study default. Backtested both windows before going live:
#   mirror-core, 2016-09-20..2026-08-14: Sharpe 1.00 vs 0.98, MDD -38.7% vs -39.5%
#   SPMO-core,   2015-10-01..2026-08-28: Sharpe 0.93 vs 0.91, MDD -40.7% vs -41.0%
# Marginally better in-sample on this data, but E is only ~4.6% of history in this
# window, so the difference is mostly noise, not a validated finding -- this
# combination was never in the study's own grid.
SAT_WEIGHT_LIVE = dict(A=0.35, B=0.35, C=0.0, D=0.20, E=0.0, F=0.0)

# Core weight override during E/F only -- everywhere else core = 1 - satellite_weight
# (full deployment, no deliberate cash). In E/F, satellite is already 0 in
# SAT_WEIGHT_LIVE, so this leaves the remainder (1 - EF_CORE_WEIGHT) as cash rather
# than fully invested in the 15-stock core. Swept the core weight 0%..100% in E/F
# only (2026-08-29): Sharpe peaks on a broad plateau at 44-50% (0.9571-0.9572, both
# ends of that band within Sharpe 0.9538-0.9566), materially better than either
# extreme -- 0% (all cash) gives 0.927, 100% (always invested, no gating) gives
# 0.926. 50% chosen: statistically indistinguishable from the exact peak (~47%),
# a rounder number, SPMO-core full window 2015-10-01..2026-08-28: CAGR 26.05%,
# MaxDD -34.7%, Sharpe 0.957 (vs the ungated live design's CAGR 27.19%, MaxDD
# -40.7%, Sharpe 0.926). Not validated on a search/holdout split -- treat as a
# reasonably-shaped in-sample optimum, not a proven edge.
EF_CORE_WEIGHT = 0.50

# D also tested (2026-08-29): sweeping the core portion in D (satellite held fixed at
# its 20% SAT_WEIGHT_LIVE value) found a broad Sharpe peak around core=50-57%
# (0.9638 at the exact peak, vs 0.957 for the old fully-invested-in-D design). D is
# ~13.5% of history, the second-most time of any state after A, so this one isn't a
# fringe case. Search/holdout check (split 2020-01-01): FULL Sharpe 0.957->0.964,
# SEARCH 0.995->1.047 (clear improvement), HOLDOUT 0.970->0.959 (small decline) --
# net roughly a wash to modestly positive, not as clean a pass as the satellite
# weights but not a red flag either. D_CASH_WEIGHT = 0.25 was chosen directly by the
# user as a round number rather than the precise ~28% peak -- core in D becomes
# 1 - 0.20 (satellite) - 0.25 (cash) = 0.55, inside the flat part of the plateau,
# effectively indistinguishable from the exact optimum.
D_CASH_WEIGHT = 0.25

# The "cash" leg of target_weights() is held as BOXX (Alpha Architect 1-3 Month Box
# ETF), not literal uninvested buying power -- user preference, 2026-08-29. Backtested
# effect is negligible (BOXX tracks the T-bill proxy within ~0.16pp/yr, its own expense
# ratio; whole-strategy Sharpe identical to 3 decimal places using either as the cash
# return). The reason to hold it instead of plain cash is tax deferral: BOXX has no
# current income while held, unlike a cash sweep or a T-bill, which both pay taxable
# interest every period. Its 60/40 long-term/short-term blended rate under Section 1256
# does NOT apply here -- E/F and D episodes run weeks to months, so any BOXX sale will
# still be a short-term gain, same as everything else in this account. Confirmed
# tradable, fractional, in the live account (576391551) on 2026-08-29.
CASH_INSTRUMENT = 'BOXX'

def target_weights(state):
    """Returns (core_weight, satellite_weight, cash_weight) for a given state letter.
    cash_weight is deployed into CASH_INSTRUMENT (BOXX), not held as raw buying power."""
    sat = SAT_WEIGHT_LIVE[state]
    if state in ('E', 'F'):
        core = EF_CORE_WEIGHT
    elif state == 'D':
        core = 1.0 - sat - D_CASH_WEIGHT
    else:
        core = 1.0 - sat
    cash = max(0.0, 1.0 - core - sat)
    return core, sat, cash

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
