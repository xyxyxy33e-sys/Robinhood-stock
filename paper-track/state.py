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

# TARGET_WEIGHTS is the single source of truth: (core, tqqq, qld, cash) per state,
# each row summing to 1.0. QLD (ProShares Ultra QQQ, 2x) joined TQQQ (3x) as a
# second satellite instrument 2026-08-31, after paper-track/four_leg_overlay.py
# searched each state's (core, tqqq, qld) split independently against the prior
# TQQQ-only baseline (cash implied as the remainder), varying one state at a time,
# full-timeline Sharpe as the objective, search period pre-2020-01-01 only, then
# checked against the 2020+ holdout -- see below per state for what was tested and
# why, and what did NOT survive that check. cash is deployed into CASH_INSTRUMENT
# (BOXX), not held as raw buying power. QLD confirmed tradable/fractional in the
# live account (576391551) on 2026-08-31.
#
# Why QLD at all: TQQQ's daily-rebalancing volatility decay scales with k(k-1) for
# leverage k -- 3x TQQQ's decay coefficient is 6 (3x2) vs 2x QLD's 2 (2x1), a 3x
# higher structural drag, confirmed against realized data (QQQ 2015-2026: TQQQ lost
# ~14.9%/yr to decay alone vs QLD's ~5.0%/yr). QLD trades lower raw CAGR for better
# Sharpe and shallower drawdown in every core/satellite combination tested.
#
# A (0.65->0.80 core, 0.35->0.20 tqqq, 0.0 qld, 0.0 cash) -- established uptrend,
#   60.4% of history, 351 weeks. Four-leg search: trims satellite from 35% to 20%
#   (all TQQQ, QLD not used), +0.030 full-timeline Sharpe (0.988->1.013 -- note this
#   backtest predates the QLD change and used a slightly different core baseline
#   Sharpe than the 3-leg number above; treat the DELTA as the finding, not the
#   absolute levels across the two studies), CONFIRMED on the 2020+ holdout slice
#   (1.116, an improvement over baseline there too). Largest state by far (62% of
#   weeks) so this is the best-evidenced change in this update.
#
# B (0.25, 0.75, 0.0, 0.0) -- UNCHANGED. Four-leg search on B found a "better"
#   search-period weight (0.90 core / 0.10 tqqq) but it made FULL-timeline Sharpe
#   WORSE (-0.036 vs baseline) -- classic search-only overfit, consistent with B's
#   already-flagged 4-episode/28-week sample. Kept at the existing 25/75/0/0 split;
#   see the original per-state note below for that rationale.
#
# C (1.0, 0.0, 0.0, 0.0) -- UNCHANGED. Four-leg search found switching to 100% TQQQ
#   satellite, but full-timeline Sharpe was WORSE (-0.069) -- another search-only
#   overfit on a thin (28-week) sample. Confirms the existing "stay 100% core"
#   conclusion rather than displacing it.
#
# D (0.55/0.20/0.0/0.25 -> 0.0/0.0/0.70/0.30) -- pullback in uptrend, 13.5% of
#   history, 79 weeks, second-most after A. Four-leg search: drops core AND TQQQ
#   entirely in favor of 70% QLD + 30% cash, +0.025 full-timeline Sharpe, CONFIRMED
#   on the 2020+ holdout (1.088). This is the largest STRUCTURAL change in this
#   update -- D goes from "mostly core, some leverage, some cash" to "no core, all
#   leverage via the lower-decay instrument, more cash" -- on a moderate (not thin,
#   not large) sample. Adopted because it passed the same holdout bar as A, but
#   flagged here as the one row in this table most worth re-checking if D's live
#   behavior ever looks off, given the size of the structural jump relative to the
#   evidence base.
#
# E (0.50, 0.0, 0.0, 0.50) -- UNCHANGED. Four-leg search's "best" was 100% cash --
#   a corner solution (cash's near-zero variance trivially wins a Sharpe objective
#   regardless of real foregone return, confirmed as a recurring artifact across
#   this project's search work) -- REJECTED regardless of its Sharpe number, not
#   adopted. Kept at the existing 50/0/0/50 split.
#
# F (0.30, 0.0, 0.0, 0.70) -- UNCHANGED. Four-leg search found switching to 20%
#   TQQQ / 80% QLD (no core, no cash), but full-timeline Sharpe was WORSE (-0.106)
#   than baseline -- the single worst result in the whole four-leg study. Confirms
#   the existing "satellite hurts in F, lean into cash" conclusion.
#
# Below-state substate research (VIX/credit-spread/breadth/utilities-relative-
# strength, both LEVEL and RATE-OF-CHANGE versions, paper-track/substate_research.py
# and substate_research_deltas.py) found nothing that survived a corner-solution
# check, a holdout check, AND a placebo check (random splits cleared the same
# "looks like a finding" bar ~10% of the time by chance) -- concluded not worth
# pursuing further; the six states are treated as the right granularity, not a
# stepping stone to a finer one. See STRATEGY.md for the full writeup.
#
# --- Original 3-leg (TQQQ-only satellite) history below, preserved since B/C/E/F
# --- are unchanged and this is still their operative rationale ---
#
# A (0.65, 0.35, 0.0) [pre-QLD] -- Sharpe plateau 0.30-0.40 satellite (~0.964),
#   0.35 sat inside it. Core/cash axis tested separately: shallow peak near
#   core=55%/cash=10% (Sharpe +0.0015 over full deployment) -- inside the noise
#   floor of everything else tested, left alone. Superseded by the four-leg result
#   above.
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
# D (0.55, 0.20, 0.25) [pre-QLD] -- pullback in uptrend, 13.5% of history,
#   second-most after A. Satellite sweep flattens 20-25%, core/cash sweep
#   (satellite held fixed) plateaus at core 50-57% (peak Sharpe 0.964).
#   Search/holdout: FULL 0.957->0.964, SEARCH 0.995->1.047 (improvement), HOLDOUT
#   0.970->0.959 (small decline) -- roughly a wash to modestly positive. 25% cash
#   chosen by the user as a round number inside the flat part of the plateau.
#   Superseded by the four-leg result above.
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
#
# E (0.50/0.0/0.0/0.0/0.50 -> 0.0/0.0/0.0/0.50/0.50) -- breakdown, 4.2% of
# history, 32 weeks. Added 2026-08-31: XLU (utilities sector, ~0.08% expense
# ratio, cheaper than SPMO itself) as a FIFTH leg, used only in this state --
# not blended into core. Fully replaces E's 50% core allocation with 50% XLU;
# the 50% cash leg is untouched. This is the one candidate from an extensive
# defensive-instrument search (paper-track/five_leg_xlu_search.py,
# five_leg_search_all_candidates.py testing SCHD/VYM/USMV, a standalone BRK.B
# test) to survive THREE independent validation passes: (1) the four/five-leg
# per-state search vs. the live baseline over the full continuous timeline,
# holdout-confirmed; (2) a finer-grid robustness check; (3) fully isolated
# single-state validation (paper-track/isolated_state_validation.py) using
# ONLY state E's own discontiguous weeks, split into pre/post-2020
# search/holdout with NO anchoring to the rest of the portfolio's variance --
# candidate beat live weights on isolated holdout (+7.5% return, Sharpe 0.873
# vs live's +4.5%, Sharpe 0.635). A parallel test of the SAME candidate leg in
# state D, and of BRK.B in state E, both looked promising under method (1) but
# FAILED isolated validation (3) -- D's apparent gain was an artifact of
# blending with the rest of the portfolio's variance, not a real property of
# D's own weeks; BRK.B's E gain likewise didn't survive in isolation. Only
# E/XLU passed all three. Full calendar-year comparison (paper-track's
# ad-hoc year-by-year check, 2026-08-31): this change flips 2016 from -4.0% to
# +4.5%, improves 2022 from -16.6% to -14.3%, and every other year is
# untouched (states outside E don't reference this leg) -- cumulative return
# over the full 10.9yr window improves from +1130.8% to +1305.4%. Still rests
# on state E's thin sample (32 weeks total, 19 in the isolated holdout) --
# treat as the best-evidenced speculative change in this file, not a settled
# one, and revisit if E's live behavior ever looks off.
TARGET_WEIGHTS = {
    'A': (0.80, 0.20, 0.00, 0.00, 0.00),
    'B': (0.25, 0.75, 0.00, 0.00, 0.00),
    'C': (1.00, 0.00, 0.00, 0.00, 0.00),
    'D': (0.00, 0.00, 0.70, 0.00, 0.30),
    'E': (0.00, 0.00, 0.00, 0.50, 0.50),
    'F': (0.30, 0.00, 0.00, 0.00, 0.70),
}

# Instrument for each column of TARGET_WEIGHTS, in order.
TARGET_WEIGHT_LEGS = ('core', 'tqqq', 'qld', 'xlu', 'cash')

# Derived for backward compatibility with anything that reads a combined satellite
# weight (TQQQ + QLD together) rather than the two legs separately (e.g. earlier
# trigger prompts, the published evaluation artifact -- both predate the QLD split).
SAT_WEIGHT_LIVE = {s: w[1] + w[2] for s, w in TARGET_WEIGHTS.items()}

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

# The "core" leg of target_weights() is held directly as the SPMO ETF itself,
# not the 15-stock proportionally-weighted mirror -- changed 2026-08-31 after
# paper-track/backtest_overlay_etf.py (ETF core) vs backtest_overlay_mirror.py
# (mirror core) showed SPMO-ETF-as-core wins on every axis paired with the same
# satellite/cash overlay: better Sharpe (1.065 vs 1.043 with the current
# post-QLD weights; 1.013 vs 0.987 with the prior TQQQ-only weights) and a
# materially shallower max drawdown (-30.4% vs -33.0%), not just a marginal
# CAGR edge either way. Removes the weekly Invesco top-15 scrape and its
# failure modes (stale data, reconstitution-week uncertainty), collapses 15
# core positions into 1, and eliminates core-side wash-sale tracking (the
# satellite/cash legs still churn and still need it). Confirmed tradable,
# fractional, in the live account (576391551) on 2026-08-31.
CORE_INSTRUMENT = 'SPMO'

# Both satellite instruments, in TARGET_WEIGHTS column order. TQQQ (3x) is the
# higher-return/higher-decay leg; QLD (2x) is the lower-decay/better-Sharpe leg
# (see the TARGET_WEIGHTS comment block above). A state can use either, both, or
# neither -- there's no requirement that a state pick exactly one.
SATELLITE_INSTRUMENTS = ('TQQQ', 'QLD')

# Defensive leg, used only in state E as of 2026-08-31 -- see the TARGET_WEIGHTS
# comment block for the three-pass validation this survived. Confirmed
# tradable/fractional (regular hours only, no extended-hours fractional) in the
# live account (576391551) on 2026-08-31.
DEFENSIVE_INSTRUMENT = 'XLU'

def target_weights(state):
    """Returns (core_weight, tqqq_weight, qld_weight, xlu_weight, cash_weight) for
    a given state letter, straight from TARGET_WEIGHTS -- the single source of
    truth. cash_weight is deployed into CASH_INSTRUMENT (BOXX), not held as raw
    buying power. Five legs since 2026-08-31 (XLU joined as a defensive leg used
    only in state E) -- see TARGET_WEIGHT_LEGS for the column order and
    SAT_WEIGHT_LIVE for a combined-satellite (TQQQ+QLD only, excludes XLU) view
    if a caller only needs total leveraged exposure."""
    return TARGET_WEIGHTS[state]

STATE_LABEL = dict(
    A='established uptrend', B='reclaim', C='bounce in downtrend',
    D='pullback in uptrend', E='breakdown', F='established downtrend',
)

class WeightSanityError(ValueError):
    """Raised when a computed (state, core, tqqq, qld, xlu, cash) tuple fails
    validation. Every live trigger must call validate_weights() before placing
    any order and abort the rebalance (report, do not trade) if this raises --
    added 2026-08-29 after the strategy grew to three weight legs across 17
    instruments with no guard between "compute a state" and "place real
    orders"; extended 2026-08-31 to four legs when QLD joined TQQQ as a second
    satellite instrument, then to five legs the same day when XLU joined as a
    defensive leg used only in state E."""
    pass

def validate_weights(state, core, tqqq, qld, xlu, cash, tol=0.005):
    if state not in STATE_LABEL:
        raise WeightSanityError(f"state {state!r} is not one of {sorted(STATE_LABEL)}")
    legs = (('core', core), ('tqqq', tqqq), ('qld', qld), ('xlu', xlu), ('cash', cash))
    for name, w in legs:
        if not (-tol <= w <= 1.0 + tol):
            raise WeightSanityError(f"{name}_weight={w!r} out of [0,1] range for state {state}")
    total = core + tqqq + qld + xlu + cash
    if abs(total - 1.0) > tol:
        raise WeightSanityError(
            f"weights for state {state} sum to {total:.4f}, expected 1.0 +/- {tol} "
            f"(core={core}, tqqq={tqqq}, qld={qld}, xlu={xlu}, cash={cash})"
        )


class CircuitBreakerTripped(RuntimeError):
    """Raised when the account's actual move doesn't match what its own holdings
    should have produced -- added 2026-08-30. This is deliberately NOT a "the
    market moved a lot" check (large moves are expected and priced into this
    design -- 1.7x effective exposure means a bad day is supposed to be a bad
    day). It's an "the numbers don't add up" check: a live trigger must call
    circuit_breaker_check() with the account's actual total_value and the value
    IMPLIED by summing each held position's quantity * its live quote, using
    quote.adjusted_previous_close for the prior-close side of the comparison
    (both sides self-contained from a single get_portfolio + get_equity_quotes
    call, no persisted state needed across trigger firings). A real mismatch
    here means a data error, a bad fill, an unaccounted-for position, or a bug
    -- not market volatility -- and should halt automated trading and alert
    rather than push another trade into an already-wrong state."""
    pass

def circuit_breaker_check(actual_total_value, implied_total_value, tol=0.02):
    """actual_total_value: get_portfolio's total_value right now.
    implied_total_value: sum over held positions of quantity * live quote,
    reconstructed independently from get_equity_positions + get_equity_quotes.
    These should agree to within `tol` (default 2%, to absorb bid/ask and
    intraday timing noise) -- they are two views of the SAME thing, not two
    different predictions, so a real gap means something is wrong, not that
    the market moved. Raises CircuitBreakerTripped if they diverge beyond tol;
    callers must halt (report, do not trade) rather than catch and continue."""
    if implied_total_value <= 0:
        raise CircuitBreakerTripped(
            f"implied_total_value={implied_total_value!r} is not positive -- "
            "can't reconcile, treat as a data problem"
        )
    pct = abs(actual_total_value - implied_total_value) / implied_total_value
    if pct > tol:
        raise CircuitBreakerTripped(
            f"account total_value ({actual_total_value:.2f}) diverges from the "
            f"sum of its own positions at live quotes ({implied_total_value:.2f}) "
            f"by {pct*100:.1f}%, more than the {tol*100:.0f}% tolerance -- "
            "reconciliation failed, do not trade"
        )
    return pct
