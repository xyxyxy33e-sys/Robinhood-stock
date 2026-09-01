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

def compute_states(dates, px, buf=0.01, short_n=50, long_n=200):
    """Six-state classifier: price vs short_n-day SMA, price vs long_n-day
    SMA, short SMA vs long SMA, 1% hysteresis. Defaults (50, 200) are the
    live macro classifier. Also used with (30, 150) as the "micro"
    classifier for the A/D micro-overlay -- see MICRO_SHORT_N/MICRO_LONG_N
    and compute_micro_agreement() below. Never call with untested windows
    for live weights -- paper-track/ma_window_sweep.py and
    three_ma_classifier.py found every OTHER window pair or a merged
    3-MA classifier performs worse or fails search/holdout; only (50,200)
    as the macro classifier and (30,150) as the micro overlay are validated.
    """
    v = [px[d] for d in dates]
    s50 = s200 = None
    out = []
    for i, d in enumerate(dates):
        m50, m200 = sma(v, i, short_n), sma(v, i, long_n)
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


# Micro overlay windows -- validated 2026-09-01, paper-track/micro_macro_sweep.py
# and turnover_cost_model.py. The MICRO classifier is the SAME six-state machine
# as the macro one, just computed with faster windows -- it's never used as a
# state in its own right, only to ask "does the fast reading currently agree
# with the slow (macro) one" for states A and D.
MICRO_SHORT_N = 30
MICRO_LONG_N = 150


def compute_micro_agreement(dates, px, buf=0.01):
    """Per-date bool: does the MICRO (30/150) classifier currently read A or
    B (the two "trend confirmed" states)? Used only to gate the A/D micro
    overlay in MICRO_OVERLAY_WEIGHTS below -- never a state on its own."""
    micro_states = compute_states(dates, px, buf=buf, short_n=MICRO_SHORT_N, long_n=MICRO_LONG_N)
    return {d: (s in ('A', 'B')) for d, s in zip(dates, micro_states)}

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
#   on the 2020+ holdout (1.088). Re-examined 2026-09-01 (user request) with a full
#   2D QLD x XLU grid via state_d_deep_dive.py: the grid-wide "optimum" (QLD=0/
#   XLU=0/cash=100%) is a corner-solution artifact -- search Sharpe 15.695 but
#   holdout CAGR only 2.98%, MaxDD -0.17% -- rejected as economically meaningless,
#   same pattern as the corner solutions caught elsewhere in this file. Excluding
#   that corner, the legitimate interior region is QLD 10-30% / XLU 20-50% / cash
#   ~30%, consistent with the original per-state XLU-for-D subagent finding.
#   Episode-by-episode check (28 episodes since 2015) found XLU only helps in 9 of
#   them -- concentrated in the sharp drawdowns (Dec 2015, Oct 2018, Mar 2020 COVID,
#   Jan 2022, Mar 2025, Feb-Mar 2026) -- and hurts in the other 19, mostly
#   rally/recovery episodes where QLD's leverage captures more upside. User briefly
#   adopted the XLU tilt (30% QLD/40% XLU/30% cash) the same day, then reverted
#   back to 70% QLD/30% cash after a full-portfolio backtest comparison showed the
#   tilt costs CAGR and Sharpe at the whole-portfolio level (net Sharpe 1.098 vs
#   1.109, CAGR 22.13% vs 22.91%) even though it improves state D's OWN isolated
#   Sharpe (1.729 vs 1.610) and roughly halves state D's own MaxDD (-8.59% vs
#   -12.04%) -- state D is only 13.5% of history, so the isolated improvement
#   doesn't carry through to the full portfolio. REVERTED 2026-09-01 (user
#   decision) to the original 70% QLD / 30% cash; the interior region and the
#   isolated-state numbers above are kept as a documented option, not adopted.
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

# Core is pure SPMO -- NOT blended with gold. History: gold was blended INTO
# the core at a fixed 75/25 SPMO/gold split from 2026-08-31 to 2026-09-01,
# superseded the same day by moving gold OUT of the core into its own
# standalone leg (see STANDALONE_GOLD_FRAC below) after a stress test found
# the in-core design had a structural flaw: because core_weight is 0% in
# states D and E, the in-core blend meant gold exposure silently dropped to
# ZERO exactly during pullback/breakdown -- the states where a safe-haven
# asset matters most. A standalone top-slice, present in every state
# regardless of core_weight, tested better on EVERY metric in EVERY period
# (full timeline, pre-2020 search, 2020-24 holdout, and with gold's outlier
# +62.3% 2025 excluded) -- see the "Gold: from core-blend to standalone
# top-slice" section of STRATEGY.md for the full comparison, including the
# isolation check confirming this is gold's own diversification value, not
# just generic de-risking (an equal-weight cash slice underperforms the gold
# slice on Sharpe and CAGR in every period).
CORE_SPMO_FRAC = 1.0
CORE_GLD_FRAC = 0.0

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
    if a caller only needs total leveraged exposure. core_weight itself is a
    fixed 75/25 SPMO/GLD blend (CORE_SPMO_FRAC/CORE_GLD_FRAC), not pure SPMO
    -- split core_weight * account_value into those two instruments in that
    ratio, in every state that has a nonzero core_weight."""
    return TARGET_WEIGHTS[state]

# Micro overlay -- added 2026-09-01, paper-track/micro_macro_sweep.py,
# turnover_cost_model.py, and the lambda-interpolation frontier that found
# lambda=0.8 as the genuine Pareto-best point (better Sharpe AND CAGR than
# the full lambda=1.0 endpoint, for only slightly worse MaxDD). This is the
# ONE idea from an extensive session of research (MA-window sweeps, 3-MA
# classifiers, state-A "confidence" signals from four independently
# corroborating sources, a majority-vote composite) that survived every
# check: search/holdout, corner-solution, full-timeline blending, and
# turnover-cost modeling (net Sharpe 1.149 vs live's 1.111 at lambda=1.0,
# even better at lambda=0.8's 1.154 -- see STRATEGY.md). Everything else
# from that research either failed search/holdout, failed a corner-solution
# check, or -- most instructively -- validated in isolation but reversed
# once tested at the full-timeline level (the state-A "confidence" line,
# composite_turnover_cost.py): DO NOT re-derive a similar overlay from an
# isolated-cell result alone; always re-check at the full-timeline,
# cost-adjusted level before trusting it, the way this one was.
#
# Mechanism: split states A and D by whether a faster "micro" reading
# (compute_micro_agreement, 30/150-day SMAs, same six-state machine as the
# macro classifier) currently agrees with the macro (50/200) one:
#   A, micro agrees (reads A or B)   -> de-lever modestly (less TQQQ)
#   D, micro diverges (reads C/D/E/F) -> shift from QLD into core+cash
# States B, C, E, F are untouched -- those splits never had enough sample
# to test (see STRATEGY.md). lambda=0.8 blend between live and the fully
# micro-adjusted weight (see micro_macro_sweep.py for the fully-adjusted
# endpoint):
MICRO_LAMBDA = 0.8
_LIVE_A, _NEW_A = (0.80, 0.20, 0.00, 0.00, 0.00), (0.90, 0.10, 0.00, 0.00, 0.00)
_LIVE_D, _NEW_D = (0.00, 0.00, 0.70, 0.00, 0.30), (0.70, 0.00, 0.00, 0.00, 0.30)
MICRO_OVERLAY_WEIGHTS = {
    ('A', True): tuple(round((1 - MICRO_LAMBDA) * b + MICRO_LAMBDA * n, 4) for b, n in zip(_LIVE_A, _NEW_A)),
    ('D', False): tuple(round((1 - MICRO_LAMBDA) * b + MICRO_LAMBDA * n, 4) for b, n in zip(_LIVE_D, _NEW_D)),
}
# = {('A', True): (0.88, 0.12, 0.0, 0.0, 0.0), ('D', False): (0.56, 0.0, 0.14, 0.0, 0.3)}


def target_weights_with_micro(state, micro_agrees):
    """target_weights(state), refined by the micro overlay for states A and
    D only. micro_agrees: bool from compute_micro_agreement() for the same
    date target_weights() is being called for -- whether the fast (30/150)
    classifier currently reads A or B. For every state/agreement combo NOT
    in MICRO_OVERLAY_WEIGHTS (B, C, E, F always; A when micro diverges; D
    when micro agrees), returns the plain target_weights(state) unchanged.
    Returns 5 legs (core, tqqq, qld, xlu, cash) -- see
    target_weights_with_gold() for the 6-leg version that also applies the
    standalone gold overlay; that is the one live triggers should call."""
    return MICRO_OVERLAY_WEIGHTS.get((state, micro_agrees), TARGET_WEIGHTS[state])

# Standalone gold top-slice -- added 2026-09-01, superseding the in-core
# 75/25 SPMO/gold blend the same day (see the CORE_SPMO_FRAC/CORE_GLD_FRAC
# comment above for why). Validated via gold_standalone_test.py and
# gold_offense_defense.py: a FLAT, UNIFORM weight across all six states beats
# every alternative tested, including per-state optimization (which overfit
# badly on thin per-state samples -- states C/E "optimized" to a nonsensical
# 0% with search-Sharpe >4.8, a corner-solution artifact from 10-13-week
# samples; states B/D/F pushed to the grid edge and state F's holdout Sharpe
# collapsed from 3.81 search to 0.058 holdout, textbook overfitting) and a
# defense-tilted design (more gold in D/E/F than A/B/C, testing the
# hypothesis that gold should lean in specifically during downturns) -- every
# tested tilt away from uniform, in either direction, UNDERPERFORMED flat on
# the honest 2020-24 holdout; the offense/defense Sharpe surface ridges along
# offense-weight == defense-weight, not toward extra defense weight. 20% beat
# 15% on every metric in every period tested (no tradeoff), so 20% was
# chosen over the also-defensible 15%. This weight trades off against EVERY
# other leg proportionally, not against cash alone -- see
# target_weights_with_gold() below.
#
# REMOVED 2026-09-01 (same day, user decision) -- STANDALONE_GOLD_FRAC set to
# 0.0. Gold is out of the live design entirely, by explicit user instruction,
# not because the backtest evidence turned against it -- an extensive
# follow-up research pass (candidate replacements BTAL/TLT/DBC/PDBC/KMLM,
# downturn-only variants, alternate uses of the freed-up slot -- cash, extra
# leverage, extra core -- both uniform and bucketed offense/defense, and a
# full continuous-fraction sensitivity sweep of all of the above) never found
# anything that beat gold's own risk-adjusted numbers. Kept here as a
# complete, working code path (not deleted) in case gold is reconsidered
# later -- flip STANDALONE_GOLD_FRAC back to reactivate it; every other
# function in this file (target_weights_with_gold, validate_weights_6leg,
# TARGET_WEIGHT_LEGS_WITH_GOLD) still works correctly at 0.0, it just
# degenerates to the plain 5-leg target_weights_with_micro() design with an
# always-zero gold leg.
STANDALONE_GOLD_FRAC = 0.0
GOLD_INSTRUMENT = 'IAU'

def target_weights_with_gold(state, micro_agrees):
    """The full live weight function -- target_weights_with_micro(), with the
    standalone gold overlay applied on top. Returns 6 legs in
    TARGET_WEIGHT_LEGS_WITH_GOLD order: (core, tqqq, qld, xlu, gold, cash).
    Gold is a flat STANDALONE_GOLD_FRAC in EVERY state (unlike XLU, which is
    state E only) -- every other leg is scaled down by (1 -
    STANDALONE_GOLD_FRAC) to make room, preserving their RELATIVE
    proportions from target_weights_with_micro().

    SUPERSEDED 2026-09-01 as the live entry point: triggers must now call
    target_weights_with_voltarget(), which applies the volatility-target
    overlay. This function remains correct and is kept for the gold code
    path (inert at STANDALONE_GOLD_FRAC=0.0)."""
    core, tqqq, qld, xlu, cash = target_weights_with_micro(state, micro_agrees)
    scale = 1 - STANDALONE_GOLD_FRAC
    return (core * scale, tqqq * scale, qld * scale, xlu * scale,
            STANDALONE_GOLD_FRAC, cash * scale)

# Instrument for each column of target_weights_with_gold()'s output, in order.
TARGET_WEIGHT_LEGS_WITH_GOLD = ('core', 'tqqq', 'qld', 'xlu', 'gold', 'cash')

# ---------------------------------------------------------------------------
# Volatility targeting -- added 2026-09-01. THE OUTERMOST OVERLAY: it runs on
# top of target_weights_with_micro(), and target_weights_with_voltarget() is
# what a live trigger should call.
#
# Mechanism: scale the four RISKY legs (core/tqqq/qld/xlu) by
#     multiplier = min(VOL_TARGET_CAP, VOL_TARGET_PA / realized_vol)
# and put whatever is freed into cash. Unlike every other part of this file,
# this reacts to REALIZED VOLATILITY rather than to a price-vs-moving-average
# state, so it responds in days instead of in 50/200-crossover time.
#
# WHY THIS AND NOTHING ELSE: an extensive 2026-09-01 search for a second
# defensive layer went 0-for-6 -- VIX level/change, credit spreads (Baa-10Y
# and its 252d-median deviation), breadth (% of a 510-name universe in
# uptrend), cross-asset ETFs (DBC/UUP/KMLM/VXUS/GLD/TLT/BTAL/TAIL/...), QQQ's
# own DMA slope+acceleration, and substate splits ALL failed out-of-sample.
# The DMA-slope rule looked strongest until an exposure-matched control showed
# ~2/3 of its "edge" was simply holding more, and a 3.2x larger sample (197
# state-F weeks instead of 62) moved its p-value the WRONG way (0.083 ->
# 0.189) and flipped its episode record from 11-helped/2-hurt to 11/15.
# Volatility targeting is the one idea that survived the same gauntlet.
#
# VALIDATION (paper-track/voltarget_and_sp500_test.py, 2000-2026, QQQ-core
# proxy with validated synthetic 2x/3x legs, net of the 4bps cost model):
#   period                  live CAGR/Sharpe/MaxDD   vol-target 20%
#   2000-07..2015-10 (OOS)   4.51% /0.311/ -65.1%    8.03% /0.512/ -37.9%
#   2015-11..2026-08 (fit)  23.11% /1.051/ -26.7%   20.60% /1.060/ -20.1%
#   FULL 2000..2026         11.84% /0.617/ -65.1%   13.06% /0.746/ -37.9%
# Pareto-better over the full window on ALL THREE metrics, and it improves the
# OUT-OF-SAMPLE slice far more than the fitted one -- the opposite of an
# overfit signature.
#
# It passes the exposure-confound control that killed the DMA rule: flat
# de-levering to the SAME average beta (0.96) returns only 4.45% with -60.4%
# MaxDD in the OOS slice, vs vol targeting's 8.03%/-37.9%. The edge is in
# WHEN it de-levers, not how much on average. Turnover is also slightly LOWER
# than live (12.0x vs 12.9x/yr) -- it smooths some state transitions.
#
# PARAMETERS. Lookback 30 TRADING days = 6.0 calendar weeks (median-verified).
# Chosen from a 2wk..12wk sweep at three target levels: full-period Sharpe
# peaks at 6-7wk in every target column, and 6-8wk is a flat PLATEAU, not a
# spike. Shorter is worse on every axis AT ONCE -- lower CAGR, lower Sharpe,
# deeper drawdown AND higher turnover, because a noisier vol estimate trades
# more (3wk: 12.64%/0.716/-41.0%/13.2x vs 6wk: 13.06%/0.746/-37.9%/12.0x).
# All 18 (lookback x target) combinations tested beat live on full-period
# Sharpe and MaxDD, so the DECISION to vol-target is robust to the parameter;
# only the fine-tuning is uncertain.
#
# VOL_TARGET_PA = 0.20 targets return; 0.15 is the also-defensible
# drawdown-floor choice (full period 11.71%/0.757/-28.3%) -- one-line change.
#
# CAP MUST STAY AT 1.0 (de-lever only, never lever up). cap=1.5 was tested and
# is WORSE where it matters: it levers up into the calm before a crash, taking
# COVID from -16.2% to -22.3%.
#
# WHAT IT DOES NOT FIX: COVID-style crashes. A 5-week crash and 20-week
# recovery is faster than any 6-week vol estimate (-16.2% vs live's -15.9%).
# Its value is in SUSTAINED declines: the dot-com goes from -54.7% to -28.6%
# and 2011's whipsaw from -22.2% to -18.4%. Do not expect crash protection.
#
# CAVEAT: validated on a QQQ-core proxy because SPMO does not exist before
# 2015. The mechanism is instrument-independent so it should carry, but the
# exact CAGR figures do not transfer -- on the real SPMO-era instruments the
# cost in that (bull-dominated) window is smaller than the proxy suggests.
VOL_TARGET_PA = 0.20        # annualized target volatility for the risky sleeve
VOL_LOOKBACK_DAYS = 30      # trading days (= 6.0 calendar weeks)
VOL_TARGET_CAP = 1.0        # never exceed the un-scaled weights; do NOT raise
TRADING_DAYS_PER_YEAR = 252


def realized_vol(dates, px, as_of=None, lookback=VOL_LOOKBACK_DAYS):
    """Annualized realized volatility of daily returns over the trailing
    `lookback` TRADING days ending at `as_of` (default: the last date).
    dates must be sorted ascending and px keyed by those dates -- the same
    (dates, px) pair passed to compute_states(). Returns None when there is
    not enough history, which callers must treat as "no scaling" (multiplier
    1.0), never as zero. Uses only data at or before `as_of`: no lookahead."""
    if as_of is None:
        as_of = dates[-1]
    try:
        end = dates.index(as_of)
    except ValueError:
        return None
    if end < lookback:
        return None
    rets = [px[dates[i]] / px[dates[i - 1]] - 1 for i in range(end - lookback + 1, end + 1)]
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return (var ** 0.5) * (TRADING_DAYS_PER_YEAR ** 0.5)


def vol_target_multiplier(vol, target=VOL_TARGET_PA, cap=VOL_TARGET_CAP):
    """min(cap, target/vol), with vol=None/0 -> 1.0 (no scaling). Never
    exceeds `cap`, so with cap=1.0 this can only ever REDUCE risk."""
    if not vol or vol <= 0:
        return 1.0
    return min(cap, target / vol)


# Rebalance drift band -- added 2026-09-01, together with the removal of the
# old per-leg "$100 or 0.3%" trade threshold (user decision: gate on how wrong
# the WHOLE portfolio is, not on how small each individual leg's trade is).
#
# THE PROBLEM IT SOLVES. Before volatility targeting, live weights only moved
# on a regime change, so "check daily, act on change" was exact. With vol
# targeting the target drifts a little EVERY day, so acting on any difference
# would trade ~250x/year, while a weekly-only rule can sit badly off-target
# during a fast vol spike -- precisely when being off-target costs most.
#
# THE RULE (paper-track/drift_band_test.py): rebalance when the regime changes
# (always, regardless of drift) OR when L1 drift -- sum over the 5 legs of
# |target_i - held_i| -- exceeds REBALANCE_DRIFT_BAND. Because the legs must
# each sum to 1.0, an L1 drift of X corresponds to roughly X/2 of the
# portfolio sitting in the wrong leg; the 0.05 band is therefore about "2.5
# percentage points of the portfolio is misallocated".
#
# WHY 0.05. A daily-resolution simulation that lets held weights DRIFT with
# realised returns between rebalances (more realistic than this repo's weekly
# backtests, which silently reset to target every week) found performance is
# FLAT across the whole 2%-20% band range -- full-period CAGR 11.35-11.43%,
# Sharpe 0.664-0.669, MaxDD -41.4% to -42.5%. The band is therefore
# essentially free in return terms and was chosen on operational grounds:
#
#   band     reb/yr   turn/yr    CAGR   Sharpe   median gap   max gap
#   3%         42.5    15.77x  11.36%    0.665        2 days    74 days
#   5%  (live) 32.7    15.49x  11.35%    0.665        3 days    93 days
#   8%         26.9    15.28x  11.42%    0.667        3 days   118 days
#   10%        24.5    15.09x  11.40%    0.666        4 days   128 days
#   weekly     66.1    15.48x  11.35%    0.668        3 days     4 days
#
# 0.05 was picked (user decision 2026-09-01) for tighter tracking -- max gap
# 93 days vs 10%'s 128, median 3 days vs 4 -- at the cost of ~8 more
# rebalances/year. It also gets nearly the responsiveness of a
# Friday-unconditional rule at LESS THAN HALF its trade count (32.7 vs 75.9
# rebalances/year, same performance), which is the cheaper way to buy
# responsiveness. The two eras disagree mildly on the "best" band (OOS prefers
# 10%, the fitted window prefers 5%) by margins well inside noise -- a reason
# not to fine-tune further. Anything in 3%-10% is defensible; this is one
# constant to change.
#
# RESPONSIVENESS CHECK (the point of the band). Traced through the COVID
# crash, band 0.10 fired NINE rebalances in three weeks -- 2020-02-24, 02-25,
# 02-27, 03-02, 03-04, 03-09, 03-10, 03-11, 03-17 -- taking the risky sleeve
# from 100% to 14% as realised vol went 14% -> 70%. It then correctly HELD
# through the late-March plateau, when vol stayed high but stopped changing.
# Regime changes bypass the band entirely, so genuine state transitions are
# never delayed by it.
#
# NOTE for the drift-aware view of the overlay: in that same daily simulation
# vol targeting still wins clearly over no vol targeting -- full period 11.43%
# /0.669/-41.6% (band 20%) vs 9.56%/0.517/-69.9% -- though both CAGRs are
# lower than the weekly backtests report, because weekly backtests reset to
# target every week and so quietly assume free rebalancing.
REBALANCE_DRIFT_BAND = 0.05


def weight_drift(target, held):
    """L1 distance between a target and a held weight tuple: sum |t_i - h_i|.
    Both must be same-length weight tuples (5 legs, in TARGET_WEIGHT_LEGS
    order). Returns 0.0 when held is None/empty (nothing held yet)."""
    if not held:
        return 0.0
    return sum(abs(t - h) for t, h in zip(target, held))


def needs_rebalance(target, held, regime_changed, band=REBALANCE_DRIFT_BAND):
    """Should a trigger rebalance right now?

    Rebalance if the regime changed (ALWAYS -- a state transition is never
    gated by the band), or if L1 drift from target exceeds `band`, or if
    nothing is held yet. Returns (bool, drift, reason) so the caller can log
    WHY it traded."""
    if not held:
        return True, 0.0, 'initial allocation'
    drift = weight_drift(target, held)
    if regime_changed:
        return True, drift, 'regime change'
    if drift > band:
        return True, drift, f'drift {drift*100:.1f}% > band {band*100:.0f}%'
    return False, drift, f'drift {drift*100:.1f}% within band {band*100:.0f}%'


def target_weights_with_voltarget(state, micro_agrees, vol):
    """THE LIVE WEIGHT FUNCTION as of 2026-09-01. target_weights_with_micro(),
    then scaled by the volatility-target multiplier.

    vol: annualized realized volatility from realized_vol() on the SAME QQQ
    series used for the state, as of the SAME date. Pass None when there is
    insufficient history -- the multiplier degrades to 1.0 and this returns
    target_weights_with_micro() unchanged, which is the correct fallback.

    Returns 5 legs (core, tqqq, qld, xlu, cash). The four risky legs are
    scaled by the multiplier and the freed weight goes to cash, so the tuple
    still sums to 1.0. With cap=1.0 the multiplier is <=1, so cash can only
    increase and never goes negative."""
    core, tqqq, qld, xlu, cash = target_weights_with_micro(state, micro_agrees)
    mult = vol_target_multiplier(vol)
    risky = core + tqqq + qld + xlu
    return (core * mult, tqqq * mult, qld * mult, xlu * mult, 1.0 - risky * mult)

STATE_LABEL = dict(
    A='established uptrend', B='reclaim', C='bounce in downtrend',
    D='pullback in uptrend', E='breakdown', F='established downtrend',
)

class WeightSanityError(ValueError):
    """Raised when a computed weight tuple fails validation. Every live
    trigger must call a validate_weights* function before placing any order
    and abort the rebalance (report, do not trade) if this raises -- added
    2026-08-29 after the strategy grew to three weight legs across 17
    instruments with no guard between "compute a state" and "place real
    orders"; extended 2026-08-31 to four legs when QLD joined TQQQ as a second
    satellite instrument, then to five legs the same day when XLU joined as a
    defensive leg used only in state E, then to six legs 2026-09-01 when gold
    became a standalone leg present in every state (see validate_weights_6leg
    for that case)."""
    pass

def validate_weights(state, core, tqqq, qld, xlu, cash, tol=0.005):
    """5-leg validator, for target_weights()/target_weights_with_micro()
    output. Live triggers should use validate_weights_6leg() instead, for
    target_weights_with_gold()'s output -- this is kept for any caller still
    working with the pre-gold-overlay 5-leg weights."""
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

def validate_weights_6leg(state, core, tqqq, qld, xlu, gold, cash, tol=0.005):
    """6-leg validator for target_weights_with_gold()'s output -- the one
    live triggers must call after 2026-09-01's standalone-gold overlay went
    live. Same checks as validate_weights(), plus the gold leg."""
    if state not in STATE_LABEL:
        raise WeightSanityError(f"state {state!r} is not one of {sorted(STATE_LABEL)}")
    legs = (('core', core), ('tqqq', tqqq), ('qld', qld), ('xlu', xlu), ('gold', gold), ('cash', cash))
    for name, w in legs:
        if not (-tol <= w <= 1.0 + tol):
            raise WeightSanityError(f"{name}_weight={w!r} out of [0,1] range for state {state}")
    total = core + tqqq + qld + xlu + gold + cash
    if abs(total - 1.0) > tol:
        raise WeightSanityError(
            f"weights for state {state} sum to {total:.4f}, expected 1.0 +/- {tol} "
            f"(core={core}, tqqq={tqqq}, qld={qld}, xlu={xlu}, gold={gold}, cash={cash})"
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
