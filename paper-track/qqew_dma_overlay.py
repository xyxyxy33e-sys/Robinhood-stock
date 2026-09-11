"""Research line qqew_dma_overlay (2026-09-11): the live 50/200 classifier, 20/100 fast read and 100/150/200
extension gaps computed on QQEW (Nasdaq-100 equal-weight) and on the QQEW/QQQ ratio, overlaid on the QQQ-core harness.

Owner's brief: "gather all QQEW data, compute the same multiple DMA lines and overlay to the backtest data, see if
you can find anything, relative to QQQ and such".  Four parts:
  1. DESCRIPTIVE (core deliverable): state occupancy QQEW vs QQQ vs ratio; the 6x6 day-by-day agreement matrix;
     how often QQEW's read is worse / better than QQQ's; transition timing (for every QQQ state change, how many
     sessions earlier/later QQEW made the corresponding change; lead/lag distribution by direction).
  2. EVENT STUDY: forward QQQ and forward live-design returns after each divergence type, 5/10/20/60 sessions,
     circular-shift placebo P-values (the null used in dgate_anatomy).
  3. OVERLAY TESTS through the harness on the 4,800 QQEW rows (2007-07-27..2026-08-26), each with the corrected
     exposure-matched live control (downturn_review.exposure_control over the TRUE live function), sign-flip
     placebo, real weekly rows, rebalances/yr, and a 20/60d block bootstrap for the both-era passes:
     (a) confirmation = worse of QQQ's and QQEW's effective states (+ the D/E/F-side-only variant);
     (b) QQEW-only classifier; (c) divergence (QQEW rank - QQQ rank >= 1) as (i) an extra trim vote, (ii) the D-row
     gate head-to-head with the pre-registered pct<0.20 gate, (iii) a block on fast re-entry, (iv) a 25/50% de-lever
     of A/D; (d) QQEW's own extension gaps as replacement / extra trim inputs; (e) the ratio's own 50/200 state as a
     gate on A.
  4. VERDICT material: overlap of the divergence flag and the pct<0.20 flag on D days.

Research only.  Nothing is applied.  The classifier is state.py's OWN code (compute_states, compute_fast_states,
compute_extension_gaps, effective_state, extension_scale) called on the QQEW / ratio series exactly as the harness
calls it on QQQ; the backtest loop is the project harness (leverage_under_trim bootstrap -> rows, rr, run, evaluate,
RF.eval_real); row attachment, trailing percentile, the D-gate, constant-D control and the k-live control are the
verbatim sections 0-3 of paper-track/breadth_dgate_2000.py, exec'd as dgate_anatomy.py does.  Run from the repo root:
    python3 paper-track/qqew_dma_overlay.py                 (all stages, ~10-15 min with 2000 bootstrap draws)
    QDMA_STAGE=desc|overlay|boot python3 ...                (one stage; the note was produced stage by stage)
    QDMA_NB=200 ...                                          (fewer bootstrap / placebo draws)
"""
import sys, os, math, csv, bisect, zlib, random, inspect, time
sys.path.insert(0, 'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from state import (compute_states, compute_fast_states, compute_extension_gaps, effective_state, extension_scale,
                   extension_votes, EXTENSION_STEP, EXTENSION_RULES, TARGET_WEIGHTS)
import block_bootstrap as BB
from block_bootstrap import boot, stats
from improvement_search import SEARCH, HOLDOUT, era
import improvement_search as IS
import downturn_review as DR
from long_history_backtest import load_px as _load_px
STAGE = os.environ.get('QDMA_STAGE', 'all')
NB = int(os.environ.get('QDMA_NB', '2000')); BB.N_BOOT = NB
T0 = time.time()
def el(): return f"[{time.time()-T0:4.0f}s]"

print("=" * 118)
print("RESEARCH LINE qqew_dma_overlay -- the live DMA classifier computed on QQEW and on QQEW/QQQ, overlaid on the harness")
print("=" * 118)

# ---- reuse: sections 0..3 of breadth_dgate_2000.py verbatim (standing-figure assert, QQEW/QQQ data, ratio series,
#      trailing_pct, attach (r['bp']['qqew_60'] = the pre-registered percentile), trimmed/scale_risky/gate_fn/const_D/
#      calib_q/exposure_control_live/sub_rows/both/seed/dgate_block, mean/corr/tstat, FF, load_dc)
_SRC = open('paper-track/breadth_dgate_2000.py').read()
_A = _SRC.index('# ------------------------------------------------------------------ 0. live design')
_B = _SRC.index('# ------------------------------------------------------------------ 4. VALIDATION')
exec(_SRC[_A:_B])
print(f"\n(reused breadth_dgate_2000.py sections 0-3 verbatim: {_SRC[_A:_B].count(chr(10))} lines)  {el()}")

# ---- counted run: verbatim copy of improvement_search.run plus a rebalance counter (pattern of vol_term_structure.py)
_src = inspect.getsource(IS.run).replace('def run(', 'def run_counted(') \
    .replace('cost = ONE_WAY_SPREAD * drift', 'cost = ONE_WAY_SPREAD * drift; NREB[0] += 1') \
    .replace('return rets, risky / len(rows)', 'return rets, risky / len(rows), NREB[0]') \
    .replace('    held = prev = None', '    NREB[0] = 0\n    held = prev = None')
_ns = dict(ONE_WAY_SPREAD=IS.ONE_WAY_SPREAD, BAND=IS.BAND, NREB=[0]); exec(_src, _ns); run_counted = _ns['run_counted']
_a, _e = run(rows, LIVE); _b, _e2, _n = run_counted(rows, LIVE)
assert _a == _b and _e == _e2, 'counted run diverges from harness run'
print(f"  live rebalances/yr on the full proxy: {_n/(len(rows)/252):.1f}")

# ================================================================== 1. the classifier on QQEW and on the ratio
RANK = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5}; STATES = 'ABCDEF'
QPATH = 'data/QQEW_daily_ext.csv' if os.path.exists('data/QQEW_daily_ext.csv') else 'data/QQEW_daily.csv'
QQEW_X = load_dc(QPATH); dq = sorted(QQEW_X)
# QQQ closes for the ratio: the repo's qqq_long_history (the `qqq` dict from the bootstrap) plus, for the provisional
# today's reading only, the three settled closes fetched from Robinhood on 2026-09-11 (see data/breadth_provenance.md)
RH_QQQ = {'2026-09-08': 718.36, '2026-09-09': 716.31, '2026-09-10': 708.69}
QQQ_X = dict(qqq); QQQ_X.update({d: v for d, v in RH_QQQ.items() if d not in QQQ_X})
dr = [d for d in dq if d in QQQ_X]; RATIO = {d: QQEW_X[d] / QQQ_X[d] for d in dr}
# state.py's own classifier, called on the QQEW series (its own session calendar) and on the ratio series
ST_Q = dict(zip(dq, compute_states(dq, QQEW_X))); FS_Q = compute_fast_states(dq, QQEW_X); GP_Q = compute_extension_gaps(dq, QQEW_X)
EF_Q = {d: effective_state(ST_Q[d], FS_Q[d]) for d in dq}
ST_R = dict(zip(dr, compute_states(dr, RATIO))); FS_R = compute_fast_states(dr, RATIO); GP_R = compute_extension_gaps(dr, RATIO)
EF_R = {d: effective_state(ST_R[d], FS_R[d]) for d in dr}
Q_VALID = dq[199]   # first session with a 200d SMA (before it compute_states returns 'F' by construction)
missing_q = [d for d in ds if dq[0] <= d <= dq[-1] and d not in QQEW_X]
missing_h = [d for d in dq if ds[0] <= d <= ds[-1] and d not in set(ds)]
print(f"\nQQEW series: {QPATH} {dq[0]}..{dq[-1]} ({len(dq)} sessions); classifier valid from {Q_VALID}; ratio sessions {len(dr)} to {dr[-1]}")
print(f"  harness sessions with no QQEW print: {len(missing_q)} {missing_q[:5]}; QQEW sessions not in the harness calendar: {len(missing_h)} {missing_h[:5]}")

def attach_q(r, d):
    j = bisect.bisect_right(dq, d) - 1; dd = dq[j]
    r['qs'] = ST_Q[dd]; r['qf'] = FS_Q[dd]; r['qe'] = EF_Q[dd]; r['qg'] = GP_Q[dd]; r['q_stale'] = dd != d
    jr = bisect.bisect_right(dr, d) - 1; rd = dr[jr]
    r['rs'] = ST_R[rd]; r['rf'] = FS_R[rd]; r['re'] = EF_R[rd]; r['rg'] = GP_R[rd]
    r['div'] = RANK[r['qe']] - RANK[r['eff']]; r['divm'] = RANK[r['qs']] - RANK[r['state']]
for r in rows:
    if r['d'] >= Q_VALID: attach_q(r, r['d'])
    r['fast'] = fast[r['d']]
for r in rr:
    attach_q(r, r['d0']); r['fast'] = g[r['d0']]

# the reference rows: the 4,800 rows on which the pre-registered percentile exists (same rows as breadth_signal / dgate_anatomy)
K = 'qqew_60'; RQ = sub_rows(K); assert RQ[0]['d'] >= Q_VALID
BL_EV = evaluate(RQ, LIVE); A_L = run(RQ, LIVE)[0]
print(f"\nREFERENCE on the {len(RQ)} QQEW rows {RQ[0]['d']}..{RQ[-1]['d']}: live {fmt(BL_EV)} S {BL_EV['s_sharpe']:.3f} H {BL_EV['h_sharpe']:.3f}"
      f" exp {BL_EV['risky']*100:.1f}%   (note: 26.09/1.006/-33.6 S 1.103 H 0.876)")
assert abs(BL_EV['sharpe'] - 1.006) < 0.002 and abs(BL_EV['s_sharpe'] - 1.103) < 0.002 and abs(BL_EV['h_sharpe'] - 0.876) < 0.002
NQ = sum(1 for r in RQ if r['q_stale']); print(f"  rows where the QQEW read is a forward-filled stale print: {NQ}")
def pc(n, d): return f"{100*n/d:5.1f}%" if d else "    -"
def sub(rs, lo, hi): return [r for r in rs if lo <= r['d'] <= hi]
ERAS = (('full', RQ), ('search', era(RQ, *SEARCH)), ('holdout', era(RQ, *HOLDOUT)))
def median(a):
    s = sorted(a); n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])
def quart(a, q):
    s = sorted(a); k = (len(s) - 1) * q; f = int(k); c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)

if STAGE in ('all', 'desc'):
    # ---------------------------------------------------------------- 1a. occupancy
    print("\n" + "-" * 118 + "\n1a. STATE OCCUPANCY (% of days), same 4,800 rows; macro = 50/200 six-state, eff = after the 20/100 fast overlay")
    print(f"  {'series':<22}{'era':<9}" + "".join(f"{s:>8}" for s in STATES) + "   A+B(risk-on)  D  E+F")
    for lab, key in (('QQQ macro', 'state'), ('QQQ eff', 'eff'), ('QQEW macro', 'qs'), ('QQEW eff', 'qe'), ('ratio macro', 'rs'), ('ratio eff', 're')):
        for en, rs in ERAS:
            c = {s: sum(1 for r in rs if r[key] == s) for s in STATES}; n = len(rs)
            print(f"  {lab:<22}{en:<9}" + "".join(pc(c[s], n).rjust(8) for s in STATES)
                  + f"   {pc(c['A']+c['B'], n)}   {pc(c['D'], n)} {pc(c['E']+c['F'], n)}")
    print("  fast (20/100) state occupancy, full rows:")
    for lab, key in (('QQQ fast', 'fast'), ('QQEW fast', 'qf'), ('ratio fast', 'rf')):
        c = {s: sum(1 for r in RQ if r[key] == s) for s in STATES}
        print(f"  {lab:<22}{'full':<9}" + "".join(pc(c[s], len(RQ)).rjust(8) for s in STATES))
    print("  extension-trim votes on effective-A days (QQQ's gaps vs QQEW's own gaps vs the ratio's gaps):")
    for lab, ek, gk in (('QQQ', 'eff', 'gaps'), ('QQEW', 'qe', 'qg'), ('ratio', 're', 'rg')):
        ad = [r for r in RQ if r[ek] == 'A']; vv = [extension_votes('A', r[gk]) for r in ad]
        print(f"    {lab:<6} eff-A days {len(ad):>5}: votes 0/1/2/3 = " + "/".join(str(sum(1 for v in vv if v == k)) for k in range(4))
              + f"  mean scale {mean([1-EXTENSION_STEP*v for v in vv]):.3f}")

    # ---------------------------------------------------------------- 1b. agreement matrix
    for lab, kq, ke in (('MACRO states', 'state', 'qs'), ('EFFECTIVE states', 'eff', 'qe')):
        print(f"\n1b. AGREEMENT MATRIX, {lab}: rows = QQQ, cols = QQEW, cell = % of the {len(RQ)} days (row sums in the last column)")
        M = {(a, b): 0 for a in STATES for b in STATES}
        for r in RQ: M[(r[kq], r[ke])] += 1
        print("        " + "".join(f"{b:>8}" for b in STATES) + "     row%")
        for a in STATES:
            print(f"  QQQ {a} " + "".join(pc(M[(a, b)], len(RQ)).rjust(8) for b in STATES) + f"  {pc(sum(M[(a,b)] for b in STATES), len(RQ))}")
        print("  col%    " + "".join(pc(sum(M[(a, b)] for a in STATES), len(RQ)).rjust(8) for b in STATES))
        diag = sum(M[(a, a)] for a in STATES) / len(RQ)
        pa = {a: sum(M[(a, b)] for b in STATES) / len(RQ) for a in STATES}; pb = {b: sum(M[(a, b)] for a in STATES) / len(RQ) for b in STATES}
        pe = sum(pa[s] * pb[s] for s in STATES); kappa = (diag - pe) / (1 - pe)
        print(f"  agreement {diag*100:.1f}% (chance {pe*100:.1f}%, Cohen kappa {kappa:.3f});  conditional P(QQEW state | QQQ state):")
        for a in STATES:
            n = sum(M[(a, b)] for b in STATES)
            print(f"    QQQ {a} (n {n:>4}): " + "  ".join(f"{b} {pc(M[(a,b)], n).strip()}" for b in STATES))

    # ---------------------------------------------------------------- 1c. worse / better
    print("\n1c. IS QQEW'S READ WORSE OR BETTER THAN QQQ'S? (rank A<B<C<D<E<F; 'worse' = QQEW rank higher)")
    print(f"  {'basis':<10}{'era':<9}{'n':>6}{'worse':>8}{'same':>8}{'better':>8}  mean(rankQQEW-rankQQQ)  worse by >=2  | on QQQ-eff-A days: worse | on QQQ-eff-D days: worse  E/F")
    for lab, key in (('macro', 'divm'), ('eff', 'div')):
        for en, rs in ERAS:
            w = sum(1 for r in rs if r[key] > 0); s = sum(1 for r in rs if r[key] == 0); b = sum(1 for r in rs if r[key] < 0)
            w2 = sum(1 for r in rs if r[key] >= 2); ad = [r for r in rs if r['eff'] == 'A']; dd = [r for r in rs if r['eff'] == 'D']
            ek = 'qs' if key == 'divm' else 'qe'
            print(f"  {lab:<10}{en:<9}{len(rs):>6}{pc(w, len(rs)):>8}{pc(s, len(rs)):>8}{pc(b, len(rs)):>8}  {mean([r[key] for r in rs]):+.3f}"
                  f"                  {pc(w2, len(rs))}        | {pc(sum(1 for r in ad if r[key] > 0), len(ad))}"
                  f"                | {pc(sum(1 for r in dd if r[key] > 0), len(dd))}  {pc(sum(1 for r in dd if r[ek] in 'EF'), len(dd))}")

    # ---------------------------------------------------------------- 1d. transition timing
    def change_list(seq):
        return [(i, seq[i - 1], seq[i]) for i in range(1, len(seq)) if seq[i] != seq[i - 1]]
    def match_lag(ch_ref, ch_oth, KW=60, same_dest=True):
        out = []
        for i, a, b in ch_ref:
            down = RANK[b] > RANK[a]; best = None
            for j, c, d in ch_oth:
                if abs(j - i) > KW or (RANK[d] > RANK[c]) != down or (same_dest and d != b): continue
                lag = j - i
                if best is None or abs(lag) < abs(best) or (abs(lag) == abs(best) and lag < best): best = lag
            out.append((i, a, b, best))
        return out
    def lag_summary(m):
        n = len(m); got = [x[3] for x in m if x[3] is not None]
        if not got: return f"n {n:>4} matched {0:>4}"
        lead = sum(1 for x in got if x < 0); same = sum(1 for x in got if x == 0); lag = sum(1 for x in got if x > 0)
        return (f"n {n:>4} matched {len(got):>4} ({pc(len(got), n).strip()})  QQEW earlier {pc(lead, len(got)).strip():>6}  same day {pc(same, len(got)).strip():>6}"
                f"  later {pc(lag, len(got)).strip():>6} | lag sessions: Q1 {quart(got, .25):+5.1f} median {median(got):+5.1f} Q3 {quart(got, .75):+5.1f} mean {mean(got):+5.1f}")
    for lab, kq, ke in (('MACRO', 'state', 'qs'), ('EFFECTIVE', 'eff', 'qe')):
        sq = [r[kq] for r in RQ]; se = [r[ke] for r in RQ]
        chq, che = change_list(sq), change_list(se)
        print(f"\n1d. TRANSITION TIMING, {lab} states: for each QQQ state change, the nearest QQEW change (within +-60 sessions) in the same"
              f" direction; 'strict' = same destination state, 'loose' = any destination.  lag < 0 = QQEW moved EARLIER (lead).")
        print(f"  QQQ changes {len(chq)}, QQEW changes {len(che)} on {len(RQ)} rows ({len(chq)/len(RQ)*252:.1f} vs {len(che)/len(RQ)*252:.1f} per year)")
        for sd, sl in ((True, 'strict'), (False, 'loose')):
            m = match_lag(chq, che, same_dest=sd)
            for dn, dl in ((True, 'downgrades'), (False, 'upgrades')):
                mm = [x for x in m if (RANK[x[2]] > RANK[x[1]]) == dn]
                print(f"  {sl:<7}{dl:<11} {lag_summary(mm)}")
                for en, lo, hi in (('search', *SEARCH), ('holdout', *HOLDOUT)):
                    me = [x for x in mm if lo <= RQ[x[0]]['d'] <= hi]
                    print(f"      {en:<9}       {lag_summary(me)}")
        m = match_lag(chq, che, same_dest=True)
        types = {}
        for x in m: types.setdefault(x[1] + '>' + x[2], []).append(x)
        print("  by transition type (strict), most frequent first:")
        for t, xs in sorted(types.items(), key=lambda kv: -len(kv[1]))[:10]:
            print(f"    {t:<6} {lag_summary(xs)}")
        # the reverse question: when QQEW changes, does QQQ follow?
        mr = match_lag(che, chq, same_dest=True)
        for dn, dl in ((True, 'downgrades'), (False, 'upgrades')):
            mm = [x for x in mr if (RANK[x[2]] > RANK[x[1]]) == dn]
            print(f"  REVERSE (QQEW change -> nearest QQQ change, strict) {dl:<11} {lag_summary(mm).replace('QQEW earlier', 'QQQ earlier')}")
        # cross-correlation of daily rank changes
        dq_ = [RANK[se[i]] - RANK[se[i - 1]] for i in range(1, len(se))]; dQ = [RANK[sq[i]] - RANK[sq[i - 1]] for i in range(1, len(sq))]
        line = []
        for lg in (-20, -10, -5, -3, -2, -1, 0, 1, 2, 3, 5, 10, 20):
            if lg >= 0: a, b = dQ[:len(dQ) - lg], dq_[lg:]
            else: a, b = dQ[-lg:], dq_[:len(dq_) + lg]
            line.append(f"{lg:+d}:{corr(a, b):+.3f}")
        print("  cross-corr of daily rank changes corr(dQQQ_t, dQQEW_{t+k}) (k>0: QQEW moves AFTER QQQ): " + "  ".join(line))

    # ---------------------------------------------------------------- 2. event study
    pv = [px[d] for d in ds]; pix = {d: i for i, d in enumerate(ds)}
    HZ = (5, 10, 20, 60)
    def fwdQ(i, h):
        j = pix[RQ[i]['d']]; return pv[j + h] / pv[j] - 1 if j + h < len(pv) else None
    def fwdL(i, h):
        if i + h > len(A_L): return None
        return math.exp(sum(math.log1p(x) for x in A_L[i:i + h])) - 1
    FQ = {h: [fwdQ(i, h) for i in range(len(RQ))] for h in HZ}; FL = {h: [fwdL(i, h) for i in range(len(RQ))] for h in HZ}
    def ev_types(i):
        r0, r1 = RQ[i - 1], RQ[i]
        dq_ = RANK[r1['qe']] - RANK[r0['qe']]; dQ = RANK[r1['eff']] - RANK[r0['eff']]
        if dq_ > 0 and dQ == 0: return 'QQEW down, QQQ holds'
        if dq_ < 0 and dQ == 0: return 'QQEW up, QQQ holds'
        if dq_ > 0 and dQ > 0: return 'both down'
        if dq_ < 0 and dQ < 0: return 'both up'
        if dQ > 0 and dq_ == 0: return 'QQQ down alone'
        if dQ < 0 and dq_ == 0: return 'QQQ up alone'
        if dq_ == 0 and dQ == 0: return 'no change'
        return 'opposite'
    TYPE = ['no change'] + [ev_types(i) for i in range(1, len(RQ))]
    rng = random.Random(seed('qdma_events'))
    SHIFTS = [rng.randrange(1, len(RQ)) for _ in range(min(NB, 2000))]
    def placebo(flags, arr):
        idx = [i for i, f in enumerate(flags) if f and arr[i] is not None]
        if len(idx) < 3: return None, None, None
        act = mean([arr[i] for i in idx]); n = len(flags); null = []
        for s in SHIFTS:
            vals = [arr[(i + s) % n] for i in idx if arr[(i + s) % n] is not None]
            if vals: null.append(mean(vals))
        return act, sum(1 for x in null if x <= act) / len(null), sum(1 for x in null if x >= act) / len(null)
    def event_table(title, flagsets):
        print(f"\n{title}")
        print(f"  {'flag':<26}{'n':>5} | " + " ".join(f"QQQ {h:>2}d%  P<= P>=" for h in HZ) + " | " + " ".join(f"live {h:>2}d%  P<= P>=" for h in HZ))
        for lab, flags in flagsets:
            n = sum(flags); cells = []
            for arr in (FQ, FL):
                for h in HZ:
                    a, pl, pg = placebo(flags, arr[h])
                    cells.append(f"{a*100:+7.2f} {pl:.3f} {pg:.3f}" if a is not None else "      -     -     -")
            print(f"  {lab:<26}{n:>5} | " + "  ".join(cells[:4]) + " | " + "  ".join(cells[4:]))
    print("\n" + "-" * 118 + "\n2. EVENT STUDY: mean forward return after each event (signal known at the d0 close; return from that close), circular-shift"
          f" placebo P-values ({len(SHIFTS)} shifts of the flag vector; P<= = share of shifts with a mean <= actual, P>= the reverse).")
    event_table("2a. TRANSITION-DAY events (effective states): the day the state changed", [
        (t, [TYPE[i] == t for i in range(len(RQ))]) for t in ('QQEW down, QQQ holds', 'QQEW up, QQQ holds', 'both down', 'both up', 'QQQ down alone', 'QQQ up alone', 'opposite')])
    event_table("2b. PERSISTENT divergence (every day, effective ranks): narrow = QQEW worse (div>=1), agree, broad = QQEW better (div<=-1)", [
        ('narrow (div>=1)', [r['div'] >= 1 for r in RQ]), ('agree (div=0)', [r['div'] == 0 for r in RQ]), ('broad (div<=-1)', [r['div'] <= -1 for r in RQ]),
        ('narrow, QQQ eff A', [r['div'] >= 1 and r['eff'] == 'A' for r in RQ]), ('agree, QQQ eff A', [r['div'] == 0 and r['eff'] == 'A' for r in RQ]),
        ('narrow, QQQ eff D', [r['div'] >= 1 and r['eff'] == 'D' for r in RQ]), ('agree, QQQ eff D', [r['div'] == 0 and r['eff'] == 'D' for r in RQ]),
        ('broad, QQQ eff D', [r['div'] <= -1 and r['eff'] == 'D' for r in RQ]),
        ('pct<0.20 (pre-reg), QQQ eff D', [r['bp'][K] < 0.2 and r['eff'] == 'D' for r in RQ])])
    event_table("2c. by era, the two headline flags", [
        ('narrow, D, search', [r['div'] >= 1 and r['eff'] == 'D' and r['d'] >= SEARCH[0] for r in RQ]),
        ('narrow, D, holdout', [r['div'] >= 1 and r['eff'] == 'D' and r['d'] <= HOLDOUT[1] for r in RQ]),
        ('QQEW down/QQQ holds, S', [TYPE[i] == 'QQEW down, QQQ holds' and RQ[i]['d'] >= SEARCH[0] for i in range(len(RQ))]),
        ('QQEW down/QQQ holds, H', [TYPE[i] == 'QQEW down, QQQ holds' and RQ[i]['d'] <= HOLDOUT[1] for i in range(len(RQ))])])
    print(f"  {el()} descriptive stage done")

# ================================================================== 3. overlays through the harness
def worse(a, b): return a if RANK[a] >= RANK[b] else b
def better(a, b): return a if RANK[a] <= RANK[b] else b
def scaled_w(w, f): return w if f >= 1 else tuple(x * f for x in w[:4]) + (1 - f * sum(w[:4]),)
def votes_of(eff, gaps): return extension_votes(eff, gaps)

def make(kind, flip=False, depth=1.0):
    """weight-function factory: returns fn(r, vtf). flip = sign-flip placebo (the opposite condition)."""
    def narrow(r): return (r['div'] <= -1) if flip else (r['div'] >= 1)
    def rweak(r): return (r['re'] in 'ABC') if flip else (r['re'] in 'DEF')
    def fn(r, vtf):
        eff, gaps = r['eff'], r['gaps']
        if kind == 'a_worse':
            w = trimmed(better(eff, r['qe']) if flip else worse(eff, r['qe']), gaps)
        elif kind == 'a_def':
            if flip: e2 = better(eff, r['qe']) if r['qe'] in 'ABC' else eff
            else: e2 = worse(eff, r['qe']) if r['qe'] in 'DEF' else eff
            w = trimmed(e2, gaps)
        elif kind == 'b_qqew':          # QQEW's effective state drives the row; QQEW's own gaps trim it
            w = trimmed(r['qe'], r['qg'])
        elif kind == 'b_qqew_qgaps':    # QQEW's state, QQQ's gaps
            w = trimmed(r['qe'], gaps)
        elif kind == 'c_i':
            w = trimmed(eff, gaps, extra=1 if narrow(r) else 0)
        elif kind == 'c_ii':
            w = trimmed(eff, gaps)
            if eff == 'D' and narrow(r): w = scale_risky(w, 1 - depth)
        elif kind == 'c_ii_both':
            w = trimmed(eff, gaps)
            if eff == 'D' and narrow(r) and r['bp'][K] < 0.2: w = scale_risky(w, 1 - depth)
        elif kind == 'c_ii_either':
            w = trimmed(eff, gaps)
            if eff == 'D' and (narrow(r) or r['bp'][K] < 0.2): w = scale_risky(w, 1 - depth)
        elif kind == 'c_iii':           # block the fast re-entry (fall back to the macro row) when narrow
            e2 = r['state'] if (eff != r['state'] and narrow(r)) else eff
            w = trimmed(e2, gaps)
        elif kind == 'c_iv':
            w = trimmed(eff, gaps)
            if eff in 'AD' and narrow(r): w = scale_risky(w, 1 - depth)
        elif kind == 'd_repl':
            w = scaled_w(W[eff], extension_scale(eff, r['qg']))
        elif kind == 'd_sum':
            w = scaled_w(W[eff], 1 - EXTENSION_STEP * min(3, votes_of(eff, gaps) + votes_of(eff, r['qg'])))
        elif kind == 'd_max':
            w = scaled_w(W[eff], 1 - EXTENSION_STEP * max(votes_of(eff, gaps), votes_of(eff, r['qg'])))
        elif kind == 'e_gate':
            w = trimmed(eff, gaps)
            if eff == 'A' and rweak(r): w = scale_risky(w, 1 - depth)
        elif kind == 'e_vote':
            w = trimmed(eff, gaps, extra=1 if rweak(r) else 0)
        elif kind == 'ref_pct':         # the pre-registered gate (not a new candidate)
            w = trimmed(eff, gaps)
            if eff == 'D' and r['bp'][K] < 0.2: w = scale_risky(w, 1 - depth)
        else: raise ValueError(kind)
        return vtf(w, r['vol'])
    return fn

CANDS = [  # (label, kind, depth, has_flip, description)
    ('a  conf worse-of', 'a_worse', 1.0, True, 'effective state = worse of QQQ and QQEW effective states'),
    ('a  conf D/E/F side', 'a_def', 1.0, True, 'downgrade to QQEW state only when QQEW eff is D/E/F'),
    ('b  QQEW-only + QQEW gaps', 'b_qqew', 1.0, False, 'QQEW eff state drives the row, QQEW gaps trim'),
    ('b  QQEW-only + QQQ gaps', 'b_qqew_qgaps', 1.0, False, 'QQEW eff state drives the row, QQQ gaps trim'),
    ('c.i  narrow = extra vote', 'c_i', 1.0, True, 'div>=1 adds one extension-trim vote in A'),
    ('c.ii narrow D-gate 100%', 'c_ii', 1.0, True, 'eff D and div>=1 -> D row cash'),
    ('c.ii narrow D-gate 50%', 'c_ii', 0.5, True, 'eff D and div>=1 -> D row half'),
    ('c.iii narrow blocks fast', 'c_iii', 1.0, True, 'div>=1 blocks the 20/100 re-entry'),
    ('c.iv narrow de-lever 25%', 'c_iv', 0.25, True, 'div>=1 -> A/D risky x0.75'),
    ('c.iv narrow de-lever 50%', 'c_iv', 0.5, True, 'div>=1 -> A/D risky x0.5'),
    ('d  QQEW gaps replace', 'd_repl', 1.0, False, 'trim votes from QQEW 100/150/200 gaps instead of QQQ'),
    ('d  QQEW gaps sum', 'd_sum', 1.0, False, 'votes = QQQ votes + QQEW votes (cap 3)'),
    ('d  QQEW gaps max', 'd_max', 1.0, False, 'votes = max(QQQ votes, QQEW votes)'),
    ('e  ratio D/E/F gates A 25%', 'e_gate', 0.25, True, 'eff A and ratio eff in D/E/F -> A risky x0.75'),
    ('e  ratio D/E/F gates A 50%', 'e_gate', 0.5, True, 'eff A and ratio eff in D/E/F -> A risky x0.5'),
    ('e  ratio D/E/F = extra vote', 'e_vote', 1.0, True, 'ratio eff in D/E/F adds one trim vote in A'),
    ('c.ii narrow AND pct<0.2', 'c_ii_both', 1.0, True, 'D row cash only when both flags fire'),
    ('c.ii narrow OR pct<0.2', 'c_ii_either', 1.0, True, 'D row cash when either flag fires'),
]
RESULTS = {}
def loro(fn):
    """leave-one-regime-out: Sharpe diff (candidate - same-rows live) with the window removed."""
    out = []
    for lab, lo, hi in (('GFC 2007-09', '2007-01-01', '2009-12-31'), ('COVID 2020', '2020-01-01', '2020-12-31'),
                        ('2022 bear', '2022-01-01', '2022-12-31'), ('SPMO era 2015-11+', '2015-11-01', '2099')):
        rs = [r for r in RQ if not (lo <= r['d'] <= hi)]
        out.append(f"{lab} {stats(run(rs, fn)[0])[1] - stats(run(rs, LIVE)[0])[1]:+.3f}")
    return "; ".join(out)

if STAGE in ('all', 'overlay', 'boot'):
    print("\n" + "-" * 118 + f"\n3. OVERLAYS through the harness on the {len(RQ)} rows.  Columns: candidate | same-rows live | dS/dH vs live | exposure |"
          " k-live control (downturn_review.exposure_control, TRUE live fn, k) and dS/dH vs it | flip placebo dS/dH vs live | real weekly Sharpe"
          " (live 1.248) | rebalances/yr (live on these rows below) | both-era vs control")
    _, _, nl = run_counted(RQ, LIVE); YRS = len(RQ) / 252
    rl = RF.eval_real(rr, LIVE_R)
    print(f"  same-rows live {fmt(BL_EV)} S {BL_EV['s_sharpe']:.3f} H {BL_EV['h_sharpe']:.3f} exp {BL_EV['risky']*100:.1f}% rebal/yr {nl/YRS:.1f} | real {fmt(rl)}")
    ref = make('ref_pct'); ev = evaluate(RQ, lambda r: ref(r, vt)); kk, ke = DR.exposure_control(RQ, ev['risky'])
    re_ = RF.eval_real(rr, lambda r: ref(r, RF.vt)); _, _, nr = run_counted(RQ, lambda r: ref(r, vt))
    print(f"  REFERENCE pre-registered pct<0.20 D-gate (not a candidate): {fmt(ev)} S {ev['s_sharpe']:.3f} H {ev['h_sharpe']:.3f} exp {ev['risky']*100:.1f}%"
          f" | vs live {ev['s_sharpe']-BL_EV['s_sharpe']:+.3f}/{ev['h_sharpe']-BL_EV['h_sharpe']:+.3f} | k-live k={kk:.3f} S {ke['s_sharpe']:.3f} H {ke['h_sharpe']:.3f}"
          f" -> {ev['s_sharpe']-ke['s_sharpe']:+.3f}/{ev['h_sharpe']-ke['h_sharpe']:+.3f} | real {re_['sharpe']:.3f} | rebal/yr {nr/YRS:.1f}")
    RESULTS['ref_pct'] = dict(ev=ev, fn=lambda r: ref(r, vt))
    NCAND = 0
    print(f"\n  {'candidate':<28}{'CAGR/Sh/MDD':>22}  {'S':>5} {'H':>5}  {'exp':>5} | vs live  S/H     | k-live k   S     H   -> dS/dH      | flip dS/dH     | real   dReal | reb/yr | both>ctrl | on days")
    for label, kind, depth, has_flip, desc in CANDS:
        NCAND += 1
        f = make(kind, depth=depth); fn = lambda r, f=f: f(r, vt); fnr = lambda r, f=f: f(r, RF.vt)
        ev = evaluate(RQ, fn); kk, ke = DR.exposure_control(RQ, ev['risky']); rev = RF.eval_real(rr, fnr); _, _, n_ = run_counted(RQ, fn)
        on = sum(1 for r in RQ if fn(r) != LIVE(r))
        if has_flip:
            ff = make(kind, flip=True, depth=depth); fev = evaluate(RQ, lambda r, ff=ff: ff(r, vt))
            fl = f"{fev['s_sharpe']-BL_EV['s_sharpe']:+.3f}/{fev['h_sharpe']-BL_EV['h_sharpe']:+.3f}"
        else: fev = None; fl = "   (none)   "
        bc = both(ev, ke); RESULTS[label] = dict(ev=ev, k=kk, ke=ke, rev=rev, fev=fev, fn=fn, both_ctrl=bc, both_live=both(ev, BL_EV), on=on, reb=n_ / YRS)
        print(f"  {label:<28}{fmt(ev):>22}  {ev['s_sharpe']:.3f} {ev['h_sharpe']:.3f}  {ev['risky']*100:4.1f}% | {ev['s_sharpe']-BL_EV['s_sharpe']:+.3f}/{ev['h_sharpe']-BL_EV['h_sharpe']:+.3f}"
              f" | {kk:5.3f} {ke['s_sharpe']:.3f} {ke['h_sharpe']:.3f} -> {ev['s_sharpe']-ke['s_sharpe']:+.3f}/{ev['h_sharpe']-ke['h_sharpe']:+.3f}"
              f" | {fl:>13} | {rev['sharpe']:.3f} {rev['sharpe']-rl['sharpe']:+.3f} | {n_/YRS:5.1f} | {'YES' if bc else '-':>9} | {on:>5}", flush=True)
    print(f"  CANDIDATE COUNT this line: {NCAND} (sign-flip placebos and the pre-registered reference gate not counted); cumulative with the three earlier lines: {240 + NCAND}")
    passes = [l for l in RESULTS if l != 'ref_pct' and RESULTS[l]['both_ctrl']]
    print(f"  both-era passes vs the k-live control: {len(passes)} -> {passes}")
    print(f"  both-era passes vs same-rows live only: {[l for l in RESULTS if l != 'ref_pct' and RESULTS[l]['both_live']]}")
    for l in passes:
        R = RESULTS[l]; fl = f" flip both-era vs live: {both(R['fev'], BL_EV)}" if R['fev'] else ""
        print(f"    {l}: LORO (Sharpe diff vs same-rows live, window removed): {loro(R['fn'])}{fl}")

    # ---------------------------------------------------------------- 4. overlap of the two D-day flags
    print("\n" + "-" * 118 + "\n4. OVERLAP on effective-D days: the pre-registered flag (pct<0.20) vs the divergence flag (QQEW eff rank > QQQ eff rank)")
    dd = [r for r in RQ if r['eff'] == 'D']
    cells = {}
    for r in dd: cells.setdefault((r['bp'][K] < 0.2, r['div'] >= 1), []).append(r)
    print(f"  D days {len(dd)};  cell: n, mean next-day QLD leg (bp), mean next-day QQQ (bp), share of days whose eff is E/F within 5 sessions")
    def fwd_ef(r):
        i = RQ.index(r)
        return any(RQ[j]['eff'] in 'EF' for j in range(i + 1, min(len(RQ), i + 6)))
    for a in (True, False):
        for b in (True, False):
            xs = cells.get((a, b), [])
            if not xs: print(f"    pct<0.2={a!s:<5} narrow={b!s:<5} n    0"); continue
            print(f"    pct<0.2={a!s:<5} narrow={b!s:<5} n {len(xs):>4}  QLD d1 {mean([r['legs'][2] for r in xs])*1e4:+7.1f}bp  QQQ d1 {mean([r['qqq'] for r in xs])*1e4:+7.1f}bp"
                  f"  E/F within 5: {pc(sum(1 for r in xs if fwd_ef(r)), len(xs))}")
    n11 = len(cells.get((True, True), [])); n10 = len(cells.get((True, False), [])); n01 = len(cells.get((False, True), []))
    print(f"  Jaccard(pct flag, narrow flag) on D days = {n11/(n11+n10+n01):.3f};  QQEW eff state on narrow D days: "
          + ", ".join(f"{s} {sum(1 for r in dd if r['div']>=1 and r['qe']==s)}" for s in 'EF'))
    print(f"  QQEW eff state on ALL D days: " + ", ".join(f"{s} {sum(1 for r in dd if r['qe']==s)}" for s in STATES))
    # today's reading
    # QQQ's own read on the same sessions: the repo QQQ file (to 2026-09-04) plus the three Robinhood settled closes,
    # through state.py's classifier -- PROVISIONAL after 2026-09-04 (not a harness row); the harness's last row is printed too
    dqq = sorted(QQQ_X); ST_QQ = dict(zip(dqq, compute_states(dqq, QQQ_X))); FS_QQ = compute_fast_states(dqq, QQQ_X); GP_QQ = compute_extension_gaps(dqq, QQQ_X)
    chk = [r for r in rows if r['d'] in ST_QQ]; mism = sum(1 for r in chk if ST_QQ[r['d']] != r['state'] or effective_state(ST_QQ[r['d']], FS_QQ[r['d']]) != r['eff'])
    print(f"\n  TODAY'S READING (last 12 QQEW sessions; ratio and the QQQ columns use the repo QQQ file to 2026-09-04 and Robinhood settled closes"
          f" after, provisional; harness last row {rows[-1]['d']} eff {rows[-1]['eff']}; QQQ-file classifier vs harness rows: {mism} mismatches on {len(chk)} rows)")
    print(f"  {'date':<12}{'QQEW macro':>11}{'fast':>6}{'eff':>5}{'gap100':>8}{'gap150':>8}{'gap200':>8} | {'ratio macro':>12}{'eff':>5} | {'QQQ macro':>10}{'fast':>6}{'eff':>5}{'gap50':>8}{'gap200':>8}  div")
    for d in dq[-12:]:
        gq = GP_Q[d]; rs_ = ST_R.get(d, '-'); re__ = EF_R.get(d, '-')
        i = dqq.index(d); vq = [QQQ_X[x] for x in dqq]; g50 = vq[i] / sma(vq, i, 50) - 1; qe_ = effective_state(ST_QQ[d], FS_QQ[d])
        print(f"  {d:<12}{ST_Q[d]:>11}{FS_Q[d]:>6}{EF_Q[d]:>5}{gq[100]*100:+7.1f}%{gq[150]*100:+7.1f}%{gq[200]*100:+7.1f}% | {rs_:>12}{re__:>5} |"
              f" {ST_QQ[d]:>10}{FS_QQ[d]:>6}{qe_:>5}{g50*100:+7.1f}%{GP_QQ[d][200]*100:+7.1f}%  {RANK[EF_Q[d]]-RANK[qe_]:+d}")
    print(f"  {el()} overlay stage done")

# ================================================================== 5. block bootstrap for the passes and the head-to-head
if STAGE in ('all', 'boot'):
    print("\n" + "-" * 118 + f"\n5. BLOCK BOOTSTRAP ({NB} draws, 20d and 60d circular blocks) vs same-rows live, for the both-era passes vs control and the"
          " head-to-head D-gates; plus the two D-gates against each other")
    keys = [l for l in RESULTS if l != 'ref_pct' and RESULTS[l]['both_ctrl']]
    for l in ('c.ii narrow D-gate 100%', 'a  conf worse-of', 'ref_pct'):
        if l not in keys: keys.append(l)
    A_REF = run(RQ, RESULTS['ref_pct']['fn'])[0]
    for l in keys:
        a = run(RQ, RESULTS[l]['fn'])[0]; ev = RESULTS[l]['ev']
        pt = stats(a); pl_ = stats(A_L)
        line = f"  {l:<28} point vs live {(pt[0]-pl_[0])*100:+.2f}pp/yr {pt[1]-pl_[1]:+.3f} Sh |"
        for blk in (20, 60):
            l1, l2, pl, s1, s2, ps = boot(a, A_L, blk, seed=seed('qdma', l, blk))
            line += f" {blk}d: logret CI [{l1*100:+.2f},{l2*100:+.2f}] P<=0 {pl:.3f} Sharpe CI [{s1:+.3f},{s2:+.3f}] P<=0 {ps:.3f} |"
        if l != 'ref_pct':
            pr = stats(A_REF); l1, l2, pl, s1, s2, ps = boot(a, A_REF, 20, seed=seed('qdma_vsref', l))
            line += f" vs pct-gate: point {pt[1]-pr[1]:+.3f} Sh, 20d Sharpe CI [{s1:+.3f},{s2:+.3f}] P<=0 {ps:.3f}"
        print(line, flush=True)
    print(f"  {el()} bootstrap stage done")
print(f"\nDONE {el()}")
