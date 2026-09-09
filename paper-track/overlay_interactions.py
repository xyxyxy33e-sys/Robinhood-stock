"""Overlay interactions: the complete 2^3 (and 2^4) factorial of the three
live overlays, run through the project harness on identical rows.

Research line `overlay_interactions` (2026-09-09). Research only -- nothing
here is applied (change freeze until 2026-12-07).

Factors (base allocations TARGET_WEIGHTS and the 20% vol target, cap 1.0, held
fixed; 50/200 classifier with 1% hysteresis, 3% drift band, 4bp one-way cost):
  F  fast re-entry overlay 20/100     on: weights keyed by r['eff']; off: r['state']
  T  graded extension trim step 1/3   on: extension_scale applied;  off: not
  E  vol estimator                    on: max(10d,30d) = r['vol_live']; off: 30d = r['vol']
  V  (secondary) vol target           on: vt() multiplier; off: multiplier 1.0
The 8 F/T/E cells with V on are the primary design; the 16 cells including V
are the secondary extension.  block_bootstrap.py already defines four of the
eight (000, 100, 110, 111 = LIVE) and reports F, T, E as ADDITIONS along that
one path; this script adds the other cells, the main effects / interactions,
and the marginal REMOVALS from the full design.

Every number comes from improvement_search.run()/evaluate() (proxy) and
return_frontier.eval_real() (real weekly SPMO rows).  Rebalance counts are
taken from inside run() by passing an object as ONE_WAY_SPREAD whose __mul__
records each `cost = ONE_WAY_SPREAD * drift` call -- the harness's own
decisions, no re-implemented loop.
"""
import sys, math, itertools, time, zlib
sys.path.insert(0, 'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
import improvement_search as _IS
import voltarget_live_backtest as _VL
from improvement_search import era, SEARCH, HOLDOUT
from state import extension_scale, realized_vol
from block_bootstrap import boot, stats, N_BOOT, BLOCKS, trimmed, REGIMES
from downturn_review import exposure_control

T0 = time.time()
LIVE_BP = 0.0004
COSTS = (0.0004, 0.0010, 0.0020)

# ---- real rows: attach the live estimator (max of 10d/30d realized vol as of d0)
for r in rr:
    r['vol_live'] = max(realized_vol(qd, qqq, as_of=r['d0'], lookback=10),
                        realized_vol(qd, qqq, as_of=r['d0'], lookback=30))
    assert abs(r['vol_live'] - r['vol']) < 1e-12 and 'vol30' in r   # rr['vol'] IS the live estimator


def set_cost(bp):
    _IS.ONE_WAY_SPREAD = bp      # read by run() as a module global (pattern: vrp_signal.py)
    _VL.ONE_WAY_SPREAD = bp      # read by return_frontier.eval_real()


# ---------------------------------------------------------------- the cells
def cell_fn(F, T, E, V, vtf=vt, k30='vol'):
    """Weight function for one cell.  Same style as block_bootstrap.F.
    k30 names the plain-30d field: 'vol' on proxy rows, but 'vol30' on the
    real rows, where RF.real_rows() already stores the LIVE max(10,30)
    estimator in r['vol'] (voltarget_live_backtest.build, 2026-09-07).  Using
    r['vol'] there would let the E-off cells silently fall back to the live
    estimator (briefing control 4)."""
    def fn(r):
        s = r['eff'] if F else r['state']
        w = W[s]
        if T:
            w = trimmed(w, s, r['gaps'])
        if not V:
            return w
        return vtf(w, r['vol_live'] if E else r[k30])
    return fn


def bits(F, T, E, V=1):
    return f"{int(F)}{int(T)}{int(E)}"


def name(F, T, E, V=1):
    parts = [('F' if F else '-'), ('T' if T else '-'), ('E' if E else '-')]
    s = ''.join(parts)
    if not V:
        s += ' noVT'
    return s


CELLS8 = [(F, T, E, 1) for F in (0, 1) for T in (0, 1) for E in (0, 1)]
CELLS16 = [(F, T, E, V) for V in (1, 0) for F in (0, 1) for T in (0, 1) for E in (0, 1)]
LIVE = (1, 1, 1, 1)


class _Count:
    """Stand-in for ONE_WAY_SPREAD: records every rebalance run() decides on."""
    def __init__(self):
        self.n = 0; self.l1 = 0.0
    def __mul__(self, drift):
        self.n += 1; self.l1 += drift; return 0.0
    __rmul__ = __mul__


def rebalances(rows_, fn):
    orig = _IS.ONE_WAY_SPREAD; c = _Count(); _IS.ONE_WAY_SPREAD = c
    try:
        run(rows_, fn)
    finally:
        _IS.ONE_WAY_SPREAD = orig
    yrs = len(rows_) / 252.0
    return c.n / yrs, c.l1 / yrs


def measure(cell, bp):
    F, T, E, V = cell
    fn = cell_fn(F, T, E, V); fr = cell_fn(F, T, E, V, RF.vt, 'vol30')
    set_cost(bp)
    try:
        ev = evaluate(rows, fn)
        er = RF.eval_real(rr, fr)
        ser = run(rows, fn)[0]
        ser_s = run(era(rows, *SEARCH), fn)[0]
        ser_h = run(era(rows, *HOLDOUT), fn)[0]
        # real weekly return series (eval_real does not expose it; rebuild the
        # per-row return exactly as eval_real does: weights x legs minus cost)
        prev = None; rser = []
        for r in rr:
            w = fr(r)
            cost = bp * sum(abs(w[i] - (prev[i] if prev else 0)) for i in range(5))
            rser.append(sum(w[i] * r['legs'][i] for i in range(5)) - cost); prev = w
    finally:
        set_cost(LIVE_BP)
    nreb, l1 = rebalances(rows, fn)
    return dict(ev=ev, real=er, ser=ser, ser_s=ser_s, ser_h=ser_h, rser=rser,
                reb=nreb, l1=l1)


RES = {}
for cell in CELLS16:
    for bp in COSTS:
        RES[(cell, bp)] = measure(cell, bp)

# sanity: the real series rebuilt above must reproduce eval_real's Sharpe
_chk = RES[(LIVE, LIVE_BP)]
_m = sum(_chk['rser']) / len(_chk['rser'])
_v = (sum((x - _m) ** 2 for x in _chk['rser']) / (len(_chk['rser']) - 1)) ** 0.5
assert abs(_m * 52 / (_v * 52 ** 0.5) - _chk['real']['sharpe']) < 1e-9

lv = RES[(LIVE, LIVE_BP)]
print(f"OVERLAY INTERACTIONS -- 2^3 factorial (+V as 2^4), harness rows: proxy {len(rows)} "
      f"sessions {rows[0]['d']}..{rows[-1]['d']}, real {len(rr)} weeks {rr[0]['d0']}..{rr[-1]['d0']}")
print(f"LIVE cell reproduction: proxy {lv['ev']['cagr']*100:.2f}% / {lv['ev']['sharpe']:.3f} / "
      f"{lv['ev']['mdd']*100:.1f}%  S {lv['ev']['s_sharpe']:.3f} H {lv['ev']['h_sharpe']:.3f}  "
      f"real {lv['real']['cagr']*100:.2f}% / {lv['real']['sharpe']:.3f} / {lv['real']['mdd']*100:.1f}%"
      f"   (standing: 22.12/0.938/-32.8, 1.150/0.780, 30.67/1.260/-25.3)")
print(f"candidate count: 16 pre-specified cells (8 primary), no parameter search.\n")


def table(cells, bp, title):
    print(f"{title}  [one-way cost {bp*1e4:.0f}bp]")
    print(f"{'cell':<10}{'CAGR':>8}{'Sharpe':>8}{'MDD':>8}{'S':>7}{'H':>7}{'exp':>7}{'reb/yr':>8}{'L1/yr':>7}"
          f"   {'realCAGR':>9}{'realSh':>8}{'realMDD':>9}")
    for c in cells:
        R = RES[(c, bp)]; e = R['ev']; x = R['real']
        tag = '  <- LIVE' if c == LIVE else ''
        print(f"{name(*c):<10}{e['cagr']*100:>7.2f}%{e['sharpe']:>8.3f}{e['mdd']*100:>7.1f}%"
              f"{e['s_sharpe']:>7.3f}{e['h_sharpe']:>7.3f}{e['risky']*100:>6.1f}%{R['reb']:>8.1f}{R['l1']:>7.2f}"
              f"   {x['cagr']*100:>8.2f}%{x['sharpe']:>8.3f}{x['mdd']*100:>8.1f}%{tag}")
    print()


for bp in COSTS:
    table(CELLS8, bp, "8-CELL TABLE (V on)")
for bp in (0.0004, 0.0010):
    table([c for c in CELLS16 if c[3] == 0], bp, "V-OFF CELLS (no vol target, multiplier 1.0)")


# ---------------------------------------------------------------- 1. factorial contrasts
def contrasts(y, factors):
    """Standard 2^k contrasts. y: {cell -> value}; effect of a set S of factors
    = sum(prod_{f in S} sign_f * y) / 2^(k-1).  For a main effect that is mean(on)
    - mean(off); for FxT it is half the difference of F's effect at T on vs T
    off; the three-way term is half the difference of the FxT interaction at E
    on vs E off."""
    k = len(factors); out = {}
    for m in range(1, k + 1):
        for combo in itertools.combinations(range(k), m):
            s = 0.0
            for c, val in y.items():
                sign = 1
                for j in combo:
                    sign *= 1 if c[j] else -1
                s += sign * val
            out[''.join(factors[j] for j in combo)] = s / 2 ** (k - 1)
    return out


METRICS = [('Sharpe', lambda R: R['ev']['sharpe'], 1, ''),
           ('CAGR', lambda R: R['ev']['cagr'], 100, 'pp'),
           ('MDD', lambda R: R['ev']['mdd'], 100, 'pp'),
           ('S-Sharpe', lambda R: R['ev']['s_sharpe'], 1, ''),
           ('H-Sharpe', lambda R: R['ev']['h_sharpe'], 1, ''),
           ('exposure', lambda R: R['ev']['risky'], 100, 'pp'),
           ('real Sharpe', lambda R: R['real']['sharpe'], 1, ''),
           ('real CAGR', lambda R: R['real']['cagr'], 100, 'pp')]


def factorial_table(cells, factors, bp, title):
    print(f"{title}  [cost {bp*1e4:.0f}bp]  (effect = mean(on) - mean(off); interactions = half the "
          f"difference of one effect across the other's levels; MDD/CAGR/exposure in pp)")
    terms = None
    rowsout = []
    for lab, get, scale, unit in METRICS:
        y = {c[:len(factors)]: get(RES[(c, bp)]) * scale for c in cells}
        ct = contrasts(y, factors)
        if terms is None:
            terms = list(ct.keys())
            print(f"{'metric':<13}" + ''.join(f"{t:>9}" for t in terms))
        print(f"{lab:<13}" + ''.join(f"{ct[t]:>+9.3f}" for t in terms))
    print()


for bp in (0.0004, 0.0010):
    factorial_table(CELLS8, 'FTE', bp, "MAIN EFFECTS AND INTERACTIONS, 2^3 design (V on)")
factorial_table(CELLS16, 'FTEV', 0.0004, "MAIN EFFECTS AND INTERACTIONS, 2^4 design incl. vol target V")


# ---------------------------------------------------------------- 2. marginal contributions
def minus(cell, f):
    j = 'FTEV'.index(f); c = list(cell); c[j] = 0; return tuple(c)


def plus(cell, f):
    j = 'FTEV'.index(f); c = list(cell); c[j] = 1; return tuple(c)


ZERO = (0, 0, 0, 1)
NOVT_ZERO = (0, 0, 0, 0)
print("MARGINAL CONTRIBUTION of each overlay: IN THE LIVE CONTEXT (all others on: LIVE minus LIVE-X) "
      "vs IN ISOLATION (all others off: X00 minus 000), V on")
print(f"{'':<12}{'':<10}{'dSharpe':>9}{'dCAGR':>8}{'dMDD':>8}{'dS':>8}{'dH':>8}{'dExp':>7}{'dReb':>7}{'dRealSh':>9}{'dRealCAGR':>10}")


def delta(a, b, bp):
    A = RES[(a, bp)]; B = RES[(b, bp)]
    return (A['ev']['sharpe'] - B['ev']['sharpe'], (A['ev']['cagr'] - B['ev']['cagr']) * 100,
            (A['ev']['mdd'] - B['ev']['mdd']) * 100, A['ev']['s_sharpe'] - B['ev']['s_sharpe'],
            A['ev']['h_sharpe'] - B['ev']['h_sharpe'], (A['ev']['risky'] - B['ev']['risky']) * 100,
            A['reb'] - B['reb'], A['real']['sharpe'] - B['real']['sharpe'],
            (A['real']['cagr'] - B['real']['cagr']) * 100)


def dline(lab, ctx, a, b, bp):
    d = delta(a, b, bp)
    print(f"{lab:<12}{ctx:<10}{d[0]:>+9.3f}{d[1]:>+8.2f}{d[2]:>+8.1f}{d[3]:>+8.3f}{d[4]:>+8.3f}{d[5]:>+7.1f}"
          f"{d[6]:>+7.1f}{d[7]:>+9.3f}{d[8]:>+10.2f}")


for bp in (0.0004, 0.0010):
    print(f"  -- cost {bp*1e4:.0f}bp")
    for f in 'FTE':
        dline(f, 'in LIVE', LIVE, minus(LIVE, f), bp)
        dline(f, 'isolated', plus(ZERO, f), ZERO, bp)
    dline('V', 'in LIVE', LIVE, minus(LIVE, 'V'), bp)
    dline('V', 'isolated', ZERO, NOVT_ZERO, bp)
    print("  -- same three overlays with the vol target OFF (LIVE-V context vs bare 000-noVT)")
    for f in 'FTE':
        L0 = minus(LIVE, 'V')
        dline(f, 'in LIVE-V', L0, minus(L0, f), bp)
        dline(f, 'iso noVT', plus(NOVT_ZERO, f), NOVT_ZERO, bp)
print()

# ---------------------------------------------------------------- 2b. paired block bootstrap of removals
print(f"PAIRED CIRCULAR BLOCK BOOTSTRAP ({N_BOOT} resamples, blocks {BLOCKS}) of each REMOVAL from LIVE, "
      f"full proxy, cost 4bp.  Positive = the overlay earns its place.")
print("(block_bootstrap.py reports F, T, E as additions along one path 000->100->110->111; "
      "these are removals from the full design, plus the same overlays in isolation for contrast.)")
BOOTS = [('LIVE vs LIVE-F (drop fast re-entry)', LIVE, minus(LIVE, 'F')),
         ('LIVE vs LIVE-T (drop extension trim)', LIVE, minus(LIVE, 'T')),
         ('LIVE vs LIVE-E (drop max10/30, use 30d)', LIVE, minus(LIVE, 'E')),
         ('LIVE vs LIVE-V (drop vol target)', LIVE, minus(LIVE, 'V')),
         ('isolated F: 100 vs 000', plus(ZERO, 'F'), ZERO),
         ('isolated T: 010 vs 000', plus(ZERO, 'T'), ZERO),
         ('isolated E: 001 vs 000', plus(ZERO, 'E'), ZERO)]
BOOT_OUT = {}
for lab, a, b in BOOTS:
    A = RES[(a, LIVE_BP)]['ser']; B = RES[(b, LIVE_BP)]['ser']
    la, sa = stats(A); lb, sb = stats(B)
    print(f"{lab}  point: {(la-lb)*100:+.2f}pp/yr log-return, {sa-sb:+.3f} Sharpe")
    for blk in BLOCKS:
        l1, l2, pl, s1, s2, ps = boot(A, B, blk, seed=zlib.crc32(f'{lab}|{blk}'.encode()))
        BOOT_OUT[(lab, blk)] = (l1, l2, pl, s1, s2, ps)
        print(f"   block {blk:>2}d: log-return 95% CI [{l1*100:+.2f}, {l2*100:+.2f}] pp/yr P(<=0)={pl:.3f}"
              f"   Sharpe 95% CI [{s1:+.3f}, {s2:+.3f}] P(<=0)={ps:.3f}")
print(f"  (10bp point estimates of the removals: " + ', '.join(
    f"{f}: {delta(LIVE, minus(LIVE, f), 0.0010)[0]:+.3f} Sharpe" for f in 'FTEV') + ")\n")

# ---------------------------------------------------------------- 3. leave-one-regime-out
print("LEAVE-ONE-REGIME-OUT for each removal from LIVE (Sharpe / log-return difference LIVE minus LIVE-X "
      "on the full-proxy series with that window excluded, cost 4bp)")
for lab, a, b in BOOTS[:4]:
    A = RES[(a, LIVE_BP)]['ser']; B = RES[(b, LIVE_BP)]['ser']
    print(f"  {lab}")
    for rlab, a0, b0 in REGIMES:
        keep = [i for i, r in enumerate(rows) if not (a0 <= r['d'] <= b0)]
        ca = [A[i] for i in keep]; cb = [B[i] for i in keep]
        la, sa = stats(ca); lb, sb = stats(cb)
        # and the contribution INSIDE the window, for the record
        ins = [i for i, r in enumerate(rows) if (a0 <= r['d'] <= b0)]
        _, sai = stats([A[i] for i in ins]); _, sbi = stats([B[i] for i in ins])
        print(f"     drop {rlab:<24} Sharpe {sa-sb:+.3f}  log-return {(la-lb)*100:+.2f}pp/yr"
              f"   (inside the window alone: Sharpe {sai-sbi:+.3f})")
print()

# ---------------------------------------------------------------- 4. exposure accounting
print("EXPOSURE ACCOUNTING: each cell vs downturn_review.exposure_control (macro-only/vol30 baseline "
      "= cell ---, scaled to the cell's average deployed capital).  'dSh vs ctl' > 0 means the cell "
      "beats a plain de-/re-levering of the same capital.")
for bp in (0.0004, 0.0010):
    set_cost(bp)
    print(f"  -- cost {bp*1e4:.0f}bp")
    print(f"  {'cell':<10}{'exp':>7}{'k':>7}{'matched':>8}{'Sharpe':>8}{'ctlSh':>8}{'dSh':>8}"
          f"{'CAGR':>8}{'ctlCAGR':>8}{'MDD':>8}{'ctlMDD':>8}{'ctlS':>7}{'ctlH':>7}{'dS':>7}{'dH':>7}")
    for c in CELLS16:
        R = RES[(c, bp)]; e = R['ev']
        k, ctl = exposure_control(rows, e['risky'])
        R['ctl'] = ctl
        print(f"  {name(*c):<10}{e['risky']*100:>6.1f}%{k:>7.3f}{str(ctl['exp_matched']):>8}{e['sharpe']:>8.3f}"
              f"{ctl['sharpe']:>8.3f}{e['sharpe']-ctl['sharpe']:>+8.3f}{e['cagr']*100:>7.2f}%{ctl['cagr']*100:>7.2f}%"
              f"{e['mdd']*100:>7.1f}%{ctl['mdd']*100:>7.1f}%{ctl['s_sharpe']:>7.3f}{ctl['h_sharpe']:>7.3f}"
              f"{e['s_sharpe']-ctl['s_sharpe']:>+7.3f}{e['h_sharpe']-ctl['h_sharpe']:>+7.3f}")
    set_cost(LIVE_BP)
print()


# ---------------------------------------------------------------- 5. redundancy
def corr(a, b):
    n = len(a); ma = sum(a) / n; mb = sum(b) / n
    sa = sum((x - ma) ** 2 for x in a) ** 0.5; sb = sum((x - mb) ** 2 for x in b) ** 0.5
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb) if sa > 0 and sb > 0 else float('nan')


def diff_series(ctx):
    """Daily return DIFFERENCE each overlay produces vs its off-state, in a
    context: 'live' = LIVE minus LIVE-X, 'iso' = X00 minus 000."""
    out = {}
    for f in 'FTE':
        if ctx == 'live':
            a, b = LIVE, minus(LIVE, f)
        else:
            a, b = plus(ZERO, f), ZERO
        A = RES[(a, LIVE_BP)]['ser']; B = RES[(b, LIVE_BP)]['ser']
        out[f] = [x - y for x, y in zip(A, B)]
    return out


def intent_series(ctx):
    """Per-session change in TARGET deployed capital (sum of the four risky
    weights the weight function asks for) that each overlay produces vs its
    off-state -- what the overlay wants to do, before the drift band."""
    out = {}
    for f in 'FTE':
        if ctx == 'live':
            a, b = LIVE, minus(LIVE, f)
        else:
            a, b = plus(ZERO, f), ZERO
        fa = cell_fn(*a); fb = cell_fn(*b)
        out[f] = [sum(fa(r)[:4]) - sum(fb(r)[:4]) for r in rows]
    return out


print("REDUNDANCY: correlation of the daily return DIFFERENCE series each overlay produces vs its off-state")
for ctx, lab in (('live', 'in the LIVE context (LIVE minus LIVE-X)'), ('iso', 'in isolation (X00 minus 000)')):
    D = diff_series(ctx); I = intent_series(ctx)
    print(f"  {lab}")
    print(f"    return-diff corr: F~T {corr(D['F'], D['T']):+.3f}  F~E {corr(D['F'], D['E']):+.3f}  "
          f"T~E {corr(D['T'], D['E']):+.3f}")
    print(f"    target-exposure-diff corr: F~T {corr(I['F'], I['T']):+.3f}  F~E {corr(I['F'], I['E']):+.3f}  "
          f"T~E {corr(I['T'], I['E']):+.3f}")
    act = {f: sum(1 for x in I[f] if abs(x) > 1e-9) for f in 'FTE'}
    sgn = {f: (sum(1 for x in I[f] if x > 1e-9), sum(1 for x in I[f] if x < -1e-9)) for f in 'FTE'}
    print(f"    sessions where the overlay changes target exposure: " + ', '.join(
        f"{f} {act[f]} ({act[f]/len(rows)*100:.1f}%; +{sgn[f][0]}/-{sgn[f][1]})" for f in 'FTE'))
    for x, y in (('F', 'T'), ('F', 'E'), ('T', 'E')):
        both = [(a, b) for a, b in zip(I[x], I[y]) if abs(a) > 1e-9 and abs(b) > 1e-9]
        same = sum(1 for a, b in both if a * b > 0); opp = len(both) - same
        rb = [(a, b) for a, b in zip(D[x], D[y]) if abs(a) > 1e-12 and abs(b) > 1e-12]
        rsame = sum(1 for a, b in rb if a * b > 0)
        print(f"    {x}&{y} both active: {len(both)} sessions -> same direction {same}, opposite {opp}"
              f"   | realized return-diff both nonzero {len(rb)}: same sign {rsame}, opposite {len(rb)-rsame}")
    # magnitude overlap: mean target exposure removed per session by each, and jointly
    print(f"    mean target-exposure change per session: " + ', '.join(
        f"{f} {sum(I[f])/len(rows)*100:+.2f}pp" for f in 'FTE'))
print()

# how much of T's and E's de-levering overlaps in the LIVE context
I = intent_series('live')
tE = [(a, b) for a, b in zip(I['T'], I['E'])]
jointly = sum(1 for a, b in tE if a < -1e-9 and b < -1e-9)
t_only = sum(1 for a, b in tE if a < -1e-9 and not b < -1e-9)
e_only = sum(1 for a, b in tE if b < -1e-9 and not a < -1e-9)
print(f"  T and E both de-lever on {jointly} sessions; T only {t_only}; E only {e_only}  "
      f"(of {len(rows)}).  Sum of |dExp| when both active: T {sum(abs(a) for a,b in tE if a<-1e-9 and b<-1e-9):.1f}, "
      f"E {sum(abs(b) for a,b in tE if a<-1e-9 and b<-1e-9):.1f} session-fractions\n")

# ---------------------------------------------------------------- 6. simplification candidates
def n_over(c):
    return sum(c[:3])


print("SIMPLIFICATION CANDIDATES -- ranking")
for title, cells in (("8 cells (V on)", CELLS8), ("16 cells", CELLS16)):
    for key, lab in ((lambda c: RES[(c, 0.0004)]['ev']['h_sharpe'], 'holdout Sharpe (4bp)'),
                     (lambda c: RES[(c, 0.0004)]['real']['sharpe'], 'real Sharpe (4bp)'),
                     (lambda c: RES[(c, 0.0010)]['ev']['cagr'], 'CAGR at 10bp')):
        order = sorted(cells, key=key, reverse=True)
        print(f"  {title} by {lab}: " + ' > '.join(
            f"{name(*c)} {key(c):.3f}" if 'CAGR' not in lab else f"{name(*c)} {key(c)*100:.2f}%" for c in order))
print()

print(f"SIMPLIFICATION SCREEN: for every cell with FEWER active overlays than LIVE, paired block bootstrap of "
      f"LIVE minus cell on (a) search era, (b) holdout era, (c) real weekly rows [blocks 4/12 weeks, Sharpe "
      f"rescaled to weekly], plus full proxy.  'indistinguishable' = Sharpe 95% CI spans 0 on ALL of S, H, real "
      f"at BOTH block lengths.  Cost 4bp.")
W52 = (52 / 252) ** 0.5
L = RES[(LIVE, LIVE_BP)]
SIMP = {}
for c in CELLS16:
    if c == LIVE:
        continue
    fewer = n_over(c) < 3 or c[3] == 0
    if not fewer:
        continue
    R = RES[(c, LIVE_BP)]
    d_s = R['ev']['s_sharpe'] - L['ev']['s_sharpe']; d_h = R['ev']['h_sharpe'] - L['ev']['h_sharpe']
    d_r = R['real']['sharpe'] - L['real']['sharpe']
    # cheap pre-screen for the V-off cells: a point gap worse than -0.25 Sharpe on any era cannot be inside noise
    if c[3] == 0 and min(d_s, d_h, d_r) < -0.25:
        print(f"  {name(*c):<10} point dS {d_s:+.3f} dH {d_h:+.3f} dReal {d_r:+.3f}  -- skipped (far outside noise)")
        continue
    res = {}
    for era_lab, A, B, blocks, scale in (('full', L['ser'], R['ser'], BLOCKS, 1.0),
                                          ('S', L['ser_s'], R['ser_s'], BLOCKS, 1.0),
                                          ('H', L['ser_h'], R['ser_h'], BLOCKS, 1.0),
                                          ('real', L['rser'], R['rser'], (4, 12), W52)):
        for blk in blocks:
            l1, l2, pl, s1, s2, ps = boot(A, B, blk, seed=zlib.crc32(f'{name(*c)}|{era_lab}|{blk}'.encode()))
            res[(era_lab, blk)] = (s1 * scale, s2 * scale, ps)
    inside = all(res[k][0] <= 0 <= res[k][1] for k in res if k[0] != 'full')
    worse = all(res[k][2] < 0.05 for k in res if k[0] != 'full')  # LIVE better with P>=95% everywhere
    SIMP[c] = (res, inside, d_s, d_h, d_r)
    print(f"  {name(*c):<10} point dS {d_s:+.3f} dH {d_h:+.3f} dReal {d_r:+.3f} | LIVE-minus-cell Sharpe 95% CI: "
          + '  '.join(f"{k[0]}{k[1]}[{v[0]:+.2f},{v[1]:+.2f}]" for k, v in res.items())
          + ("   INDISTINGUISHABLE" if inside else ("   LIVE better everywhere (P<0.05)" if worse else "   mixed")))
print()

cands = [c for c, v in SIMP.items() if v[1]]
if cands:
    best = sorted(cands, key=lambda c: (n_over(c) + c[3], -RES[(c, 0.0010)]['ev']['h_sharpe']))
    print("Cells statistically indistinguishable from LIVE on search, holdout AND real rows, fewest overlays first: "
          + ', '.join(f"{name(*c)} (dS {SIMP[c][2]:+.3f}, dH {SIMP[c][3]:+.3f}, dReal {SIMP[c][4]:+.3f})" for c in best))
else:
    print("No cell with fewer active overlays is inside LIVE's bootstrap noise on search, holdout and real rows.")

print(f"\nelapsed {time.time()-T0:.0f}s")
