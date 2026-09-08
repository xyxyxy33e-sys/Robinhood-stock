"""RESEARCH LINE `zscore_trim` (2026-09-08) -- vol-normalised extension-trim thresholds.

Research only (change freeze until 2026-12-07). Nothing here is applied.

The live graded extension trim votes on PRICE gaps: {100d gap > 10%, 150d gap
> 12%, 200d gap > 15%}, gap = close/SMA - 1, effective state A only, risky
legs x (1 - votes/3). A 10% stretch above the 100d SMA is ~1 sd at 35% vol
and ~3 sd at 12% vol. Hypothesis: express the gap as a z-score,

    z_n = (close/SMA_n - 1) / (vol * sqrt(n/252)),

so the trim fires on a genuinely extended tape and not on a merely volatile
one. Thresholds k are calibrated so the UNCONDITIONAL vote frequency over
the SEARCH era matches the live rule's (changing WHEN it fires, not HOW
OFTEN). Because the briefing forbids fitting on search and applying it
backward, the same rule is also run with k fitted on the HOLDOUT era and
applied forward, with an EXPANDING causal quantile, and with k re-calibrated
by bisection until average deployed exposure equals live's.

Also tested, the milder version: keep the price thresholds and scale them by
(vol / long-run median vol)^a, a in {0.5, 1}, with an expanding (causal)
median and, for reference, the full-sample median.

Harness: the project's own loop (improvement_search.run / evaluate,
return_frontier.eval_real), bootstrapped exactly as leverage_under_trim.py
does. Controls: exposure_control (mandated), plus the live design scaled to
the candidate's exposure, block bootstrap (20d / 60d), leave-one-regime-out,
and a placebo where the vol term is block-shuffled by calendar year.
"""
import sys, math, random, bisect
sys.path.insert(0, 'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from improvement_search import SEARCH, HOLDOUT, era
from downturn_review import exposure_control
from block_bootstrap import boot, stats, N_BOOT, REGIMES
from state import EXTENSION_RULES, EXTENSION_STEP, extension_votes, extension_scale, realized_vol

WINS = [n for n, _ in EXTENSION_RULES]
THR = dict(EXTENSION_RULES)
STEP = EXTENSION_STEP
CANDIDATES = []          # every variant that is evaluated on the proxy is counted here
WINNERS = []             # subset that beats live on BOTH search and holdout Sharpe

# ---------------------------------------------------------------- data prep
for r in rr:  # live estimator on the real rows (briefing pattern)
    a = realized_vol(qd, qqq, as_of=r['d0'], lookback=30)
    b = realized_vol(qd, qqq, as_of=r['d0'], lookback=10)
    r['vol_live'] = a if (a is None or b is None) else max(a, b)

byd = {r['d']: r for r in rows}
ix_ds = {d: i for i, d in enumerate(ds)}
pxv = [px[d] for d in ds]

def zscore(gaps, vol, n):
    return gaps[n] / (vol * math.sqrt(n / 252.0))

# daily z-scores from the DAILY series, attached by date (both vol estimators)
for r in rows:
    r['z30'] = {n: zscore(r['gaps'], r['vol'], n) for n in WINS}
    r['zL'] = {n: zscore(r['gaps'], r['vol_live'], n) for n in WINS}
    r['lvotes'] = extension_votes(r['eff'], r['gaps'])
for r in rr:
    q = byd[r['d0']]
    r['z30'] = q['z30']; r['zL'] = q['zL']; r['lvotes'] = q['lvotes']
    r['vol30d'] = q['vol']            # rr['vol'] is the weekly-harness 30d figure; identical on checked rows

# expanding (causal) median of vol30 over the daily series, from 1999-09
_vd = {d: realized_vol(ds, px, as_of=d, lookback=30) for d in ds}
_sorted = []
EXP_MED = {}
for d in ds:
    v = _vd[d]
    if v is not None:
        bisect.insort(_sorted, v)
    EXP_MED[d] = _sorted[len(_sorted) // 2] if _sorted else None
FULL_MED = sorted(r['vol'] for r in rows)[len(rows) // 2]

A_S = [r for r in era(rows, *SEARCH) if r['eff'] == 'A']
A_H = [r for r in era(rows, *HOLDOUT) if r['eff'] == 'A']
A_ALL = [r for r in rows if r['eff'] == 'A']
print(f"rows {len(rows)} ({rows[0]['d']}..{rows[-1]['d']}), A-days {len(A_ALL)} "
      f"(search {len(A_S)}, holdout {len(A_H)}); real weekly {len(rr)}")
print(f"vol30 median: full-sample {FULL_MED*100:.1f}%, expanding at 2015-11-02 {EXP_MED['2015-11-02']*100:.1f}%, "
      f"at 2026-08-26 {EXP_MED['2026-08-26']*100:.1f}%\n")

# ---------------------------------------------------------------- rules
def live_votes(r):
    return r['lvotes']

def z_votes_fn(key, K):
    """K: dict window -> k, or a float common k. Votes only in effective A."""
    def votes(r):
        if r['eff'] != 'A':
            return 0
        z = r[key]
        return sum(1 for n in WINS if z[n] > (K[n] if isinstance(K, dict) else K))
    return votes

def volscaled_votes_fn(key, a, med):
    """Price thresholds x (vol / median)^a. med: 'exp' (causal expanding) or 'full'."""
    def votes(r):
        if r['eff'] != 'A':
            return 0
        v = r['vol'] if key == 'z30' else r['vol_live']
        m = EXP_MED.get(r.get('d') or r['d0']) if med == 'exp' else FULL_MED
        if not m:
            return 0
        s = (v / m) ** a
        return sum(1 for n in WINS if r['gaps'][n] > THR[n] * s)
    return votes

def weight_fn(votes, real=False):
    vtf = RF.vt if real else vt
    def fn(r):
        w = W[r['eff']]; f = 1.0 - STEP * votes(r)
        if f < 1: w = tuple(a * f for a in w[:4]) + (1 - f * sum(w[:4]),)
        return vtf(w, r.get('vol_live') or r['vol'])
    return fn

LIVE = weight_fn(live_votes)
LIVE_R = weight_fn(live_votes, real=True)

def scaled(fn, k):
    def g(r):
        w = fn(r); risky = [x * k for x in w[:4]]
        return tuple(risky) + (1 - sum(risky),)
    return g

def live_scaled_control(target_exp):
    """The ACTUAL live design (overlay + trim + max(10,30)) scaled to the
    candidate's average deployed capital -- the sharper control for a
    trim-only change. Bracket expands like exposure_control's."""
    lo, hi = 0.0, 1.0
    while run(rows, scaled(LIVE, hi))[1] < target_exp and hi < 8: lo, hi = hi, hi * 2
    for _ in range(40):
        mid = (lo + hi) / 2
        if run(rows, scaled(LIVE, mid))[1] < target_exp: lo = mid
        else: hi = mid
    k = (lo + hi) / 2
    return k, evaluate(rows, scaled(LIVE, k))

# ---------------------------------------------------------------- calibration
def quantile_k(vals, p_exceed):
    """k such that share of vals above k == p_exceed (empirical)."""
    s = sorted(vals); n = len(s)
    if p_exceed <= 0: return s[-1] + 1e-9
    i = int(round((1 - p_exceed) * n)); i = min(max(i, 0), n - 1)
    return s[i]

def per_window_k(key, Arows):
    K = {}
    for n in WINS:
        p = sum(1 for r in Arows if r['gaps'][n] > THR[n]) / len(Arows)
        K[n] = quantile_k([r[key][n] for r in Arows], p)
    return K

def common_k(key, Arows):
    """Single k for all windows: match MEAN VOTES per A-day (bisection)."""
    target = sum(live_votes(r) for r in Arows) / len(Arows)
    lo, hi = 0.0, 10.0
    for _ in range(60):
        mid = (lo + hi) / 2
        mv = sum(z_votes_fn(key, mid)(r) for r in Arows) / len(Arows)
        if mv > target: lo = mid
        else: hi = mid
    return (lo + hi) / 2

def expanding_k_votes(key):
    """CAUSAL: at each A-day, k_n = quantile of PRIOR A-day z_n such that the
    prior frequency of z_n > k_n equals the prior frequency of gap_n > t_n.
    Warm-up: needs 250 prior A-days, else falls back to the live vote."""
    hist_z = {n: [] for n in WINS}; hist_hit = {n: 0 for n in WINS}; cnt = 0
    out = {}
    for r in rows:
        if r['eff'] != 'A':
            out[r['d']] = 0; continue
        if cnt >= 250:
            v = 0
            for n in WINS:
                p = hist_hit[n] / cnt
                s = hist_z[n]; i = min(max(int(round((1 - p) * len(s))), 0), len(s) - 1)
                if r[key][n] > s[i]: v += 1
            out[r['d']] = v
        else:
            out[r['d']] = r['lvotes']
        for n in WINS:
            bisect.insort(hist_z[n], r[key][n]); hist_hit[n] += r['gaps'][n] > THR[n]
        cnt += 1
    def votes(r):
        return out[r.get('d') or r['d0']]
    return votes

def k_for_exposure(key, target_exp):
    """Common k re-calibrated by bisection until AVERAGE EXPOSURE == live's."""
    lo, hi = 0.0, 10.0
    for _ in range(50):
        mid = (lo + hi) / 2
        e = run(rows, weight_fn(z_votes_fn(key, mid)))[1]
        if e < target_exp: lo = mid      # too many trims -> raise k
        else: hi = mid
    return (lo + hi) / 2

# ---------------------------------------------------------------- reporting
def freq(votes, R):
    A = [r for r in R if r['eff'] == 'A']
    v = [votes(r) for r in A]
    return dict(fire=sum(1 for x in v if x > 0) / len(R), fireA=sum(1 for x in v if x > 0) / len(A),
                mv=sum(v) / len(A), depth=sum(STEP * x for x in v) / len(A),
                v3=sum(1 for x in v if x == 3) / len(A))

def report(label, votes, base=None, control=True):
    CANDIDATES.append(label)
    ev = evaluate(rows, weight_fn(votes))
    er = RF.eval_real(rr, weight_fn(votes, real=True))
    fs = freq(votes, era(rows, *SEARCH)); fh = freq(votes, era(rows, *HOLDOUT)); fr = freq(votes, rr)
    both = ''
    if base:
        both = 'YES' if ev['s_sharpe'] > base['s_sharpe'] and ev['h_sharpe'] > base['h_sharpe'] else 'no'
        if both == 'YES': WINNERS.append(label)
    print(f"{label:<34} fireA S/H {fs['fireA']*100:4.1f}/{fh['fireA']*100:4.1f}%  mv {fs['mv']:.3f}/{fh['mv']:.3f}  "
          f"depth {fs['depth']*100:4.1f}/{fh['depth']*100:4.1f}%  exp {ev['risky']*100:5.2f}% | "
          f"proxy {ev['cagr']*100:5.2f}% / {ev['sharpe']:.3f} / {ev['mdd']*100:5.1f}%  S {ev['s_sharpe']:.3f} H {ev['h_sharpe']:.3f} {both:<3}| "
          f"real {er['cagr']*100:5.2f}% / {er['sharpe']:.3f} / {er['mdd']*100:5.1f}%  fireA {fr['fireA']*100:4.1f}%")
    if control and base:
        k1, c1 = exposure_control(rows, ev['risky'])
        k2, c2 = live_scaled_control(ev['risky'])
        print(f"{'':<34}   controls at exp {ev['risky']*100:.2f}%: exposure_control k={k1:.3f} Sharpe {c1['sharpe']:.3f} "
              f"(S {c1['s_sharpe']:.3f} H {c1['h_sharpe']:.3f}) {'matched' if c1['exp_matched'] else 'NOT matched'}; "
              f"live-scaled k={k2:.3f} Sharpe {c2['sharpe']:.3f} (S {c2['s_sharpe']:.3f} H {c2['h_sharpe']:.3f})")
    return ev, er

def fwd(d, h):
    i = ix_ds[d]
    return pxv[i + h] / pxv[i] - 1 if i + h < len(pxv) else None

def disagreement(label, votes, R=None):
    """Live vs candidate on A-days: buckets by (live fires, cand fires) and by
    vote difference, with QQQ's forward 5/21-session return per bucket."""
    R = R or rows
    print(f"\nDISAGREEMENT: live vs {label} (A-days; QQQ forward returns from the decision close)")
    B = {}
    for r in R:
        if r['eff'] != 'A': continue
        lv, cv = live_votes(r), votes(r)
        key = ('both trim' if lv and cv else 'LIVE only' if lv else 'CAND only' if cv else 'neither')
        B.setdefault(key, []).append(r)
    print(f"  {'bucket':<11}{'n':>6}{'mean vol':>10}{'mean g200':>10}{'z200(30)':>9} | {'5d mean':>8}{'hit':>6}{'21d mean':>10}{'hit':>6}{'21d ann.Sh':>11}")
    for key in ('both trim', 'LIVE only', 'CAND only', 'neither'):
        rs = B.get(key, [])
        if not rs: continue
        f5 = [x for x in (fwd(r['d'], 5) for r in rs) if x is not None]
        f21 = [x for x in (fwd(r['d'], 21) for r in rs) if x is not None]
        m5 = sum(f5) / len(f5); m21 = sum(f21) / len(f21)
        sd21 = (sum((x - m21) ** 2 for x in f21) / max(len(f21) - 1, 1)) ** 0.5
        print(f"  {key:<11}{len(rs):>6}{sum(r['vol'] for r in rs)/len(rs)*100:>9.1f}%"
              f"{sum(r['gaps'][200] for r in rs)/len(rs)*100:>9.1f}%{sum(r['z30'][200] for r in rs)/len(rs):>9.2f} | "
              f"{m5*100:>+8.2f}{sum(1 for x in f5 if x>0)/len(f5)*100:>5.0f}%{m21*100:>+10.2f}{sum(1 for x in f21 if x>0)/len(f21)*100:>5.0f}%"
              f"{(m21/sd21*math.sqrt(252/21)) if sd21 else 0:>11.2f}")
    # by vote difference
    D = {}
    for r in R:
        if r['eff'] != 'A': continue
        D.setdefault(votes(r) - live_votes(r), []).append(r)
    print(f"  vote difference (cand - live):")
    for k in sorted(D):
        rs = D[k]; f21 = [x for x in (fwd(r['d'], 21) for r in rs) if x is not None]
        f5 = [x for x in (fwd(r['d'], 5) for r in rs) if x is not None]
        print(f"    {k:+d}: n {len(rs):>5}  5d {sum(f5)/len(f5)*100:+.2f}%  21d {sum(f21)/len(f21)*100:+.2f}%  hit21 {sum(1 for x in f21 if x>0)/len(f21)*100:.0f}%")
    # the years where the two rules diverge most (in trim-depth days)
    Y = {}
    for r in R:
        if r['eff'] != 'A': continue
        y = r['d'][:4]; Y.setdefault(y, [0, 0]); Y[y][0] += live_votes(r); Y[y][1] += votes(r)
    print("  vote-days per year (live / cand): " + ", ".join(f"{y} {a}/{b}" for y, (a, b) in sorted(Y.items()) if a or b))

def bootstrap_and_loro(label, votes):
    a = run(rows, weight_fn(votes))[0]; b = run(rows, LIVE)[0]
    la, sa = stats(a); lb, sb = stats(b)
    print(f"\nBLOCK BOOTSTRAP {label} vs live (point {(la-lb)*100:+.2f}pp/yr, {sa-sb:+.3f} Sharpe), {N_BOOT} resamples")
    for blk in (20, 60):
        l1, l2, pl, s1, s2, ps = boot(a, b, blk, seed=1000 * blk + len(label))   # fixed seed: reproducible run to run
        print(f"   block {blk:>2}d: log-return 95% CI [{l1*100:+.2f}, {l2*100:+.2f}] P(<=0)={pl:.3f}   "
              f"Sharpe 95% CI [{s1:+.3f}, {s2:+.3f}] P(<=0)={ps:.3f}")
    print(f"  leave-one-regime-out (Sharpe diff cand - live):")
    for rlab, a0, b0 in REGIMES:
        keep = [i for i, r in enumerate(rows) if not (a0 <= r['d'] <= b0)]
        _, s1 = stats([a[i] for i in keep]); _, s2 = stats([b[i] for i in keep])
        l1, _ = stats([a[i] for i in keep]); l2, _ = stats([b[i] for i in keep])
        print(f"     drop {rlab:<24} Sharpe {s1-s2:+.3f}   log-return {(l1-l2)*100:+.2f}pp/yr")

def year_shuffled_vol(seed):
    """Placebo: the vol series block-shuffled by CALENDAR YEAR (each year's
    vol path is replaced by another year's path, aligned by position within
    the year, wrapping if shorter). Level and persistence are preserved; the
    match between vol and the tape is destroyed."""
    rng = random.Random(seed)
    years = sorted({r['d'][:4] for r in rows})
    byy = {y: [r['vol'] for r in rows if r['d'][:4] == y] for y in years}
    perm = years[:]; rng.shuffle(perm)
    m = dict(zip(years, perm))
    out = {}; pos = {}
    for r in rows:
        y = r['d'][:4]; src = byy[m[y]]; j = pos.get(y, 0); pos[y] = j + 1
        out[r['d']] = src[j % len(src)]
    return out

# ================================================================ 0. baseline
print("LIVE baseline (must match: proxy 22.12% / 0.938 / -32.8%, S 1.150 H 0.780; real 30.67% / 1.260 / -25.3%)")
base, base_r = report('LIVE graded price trim', live_votes, control=False)
CANDIDATES.pop()

# ================================================================ 1. z-score, k matched on SEARCH frequency
print("\n== 1. Z-SCORE TRIM, per-window k matched to live's SEARCH-era A-day vote frequency ==")
print("   (calibrated on search and applied backward: NOT causal for the holdout -- reported because the task asked; see 3/4 for causal versions)")
KS30 = per_window_k('z30', A_S); KSL = per_window_k('zL', A_S)
print(f"   k (vol30): " + ", ".join(f"{n}d {KS30[n]:.2f}" for n in WINS) + "   k (vol_live): " + ", ".join(f"{n}d {KSL[n]:.2f}" for n in WINS))
print(f"   live search-era A-day fire rates per window: " + ", ".join(f"{n}d {sum(1 for r in A_S if r['gaps'][n]>THR[n])/len(A_S)*100:.1f}%" for n in WINS))
ev_z30, _ = report('z30 per-window k (search-cal)', z_votes_fn('z30', KS30), base)
ev_zL, _ = report('zLIVE per-window k (search-cal)', z_votes_fn('zL', KSL), base)
kc30 = common_k('z30', A_S); kcL = common_k('zL', A_S)
print(f"   common k matched to mean votes: vol30 {kc30:.3f}, vol_live {kcL:.3f}")
ev_c30, _ = report(f'z30 common k={kc30:.2f} (search-cal)', z_votes_fn('z30', kc30), base)
ev_cL, _ = report(f'zLIVE common k={kcL:.2f} (search-cal)', z_votes_fn('zL', kcL), base)

print("\n   sweep of the common k (vol30) -- is there a plateau anywhere?")
for k in (0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.4, 2.8):
    report(f'z30 common k={k:.1f}', z_votes_fn('z30', k), base, control=False)
print("   sweep of the common k (vol_live)")
for k in (0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.4):
    report(f'zLIVE common k={k:.1f}', z_votes_fn('zL', k), base, control=False)

# ================================================================ 2. milder: vol-scaled price thresholds
print("\n== 2. MILDER: price thresholds x (vol / median vol)^a ==")
for med in ('exp', 'full'):
    for a in (0.5, 1.0):
        for key in ('z30', 'zL'):
            report(f"volscaled a={a} med={med} {'vol30' if key=='z30' else 'volLIVE'}", volscaled_votes_fn(key, a, med), base,
                   control=(a == 1.0 and med == 'exp'))

# ================================================================ 3. causal: holdout-calibrated applied forward; expanding quantile
print("\n== 3. CAUSAL VERSIONS ==")
KH30 = per_window_k('z30', A_H); KHL = per_window_k('zL', A_H)
print(f"   k fitted on HOLDOUT A-days (vol30): " + ", ".join(f"{n}d {KH30[n]:.2f}" for n in WINS) +
      "   (vol_live): " + ", ".join(f"{n}d {KHL[n]:.2f}" for n in WINS))
report('z30 per-window k (holdout-cal)', z_votes_fn('z30', KH30), base)
report('zLIVE per-window k (holdout-cal)', z_votes_fn('zL', KHL), base)
report('z30 expanding causal quantile', expanding_k_votes('z30'), base)
report('zLIVE expanding causal quantile', expanding_k_votes('zL'), base)

# ================================================================ 4. exposure-matched by construction
print("\n== 4. common k RE-CALIBRATED so average exposure == live's (risk held constant by construction) ==")
ke30 = k_for_exposure('z30', base['risky']); keL = k_for_exposure('zL', base['risky'])
print(f"   k: vol30 {ke30:.3f}, vol_live {keL:.3f}  (live exposure {base['risky']*100:.2f}%)")
ev_e30, _ = report(f'z30 common k={ke30:.2f} (exp-matched)', z_votes_fn('z30', ke30), base, control=False)
ev_eL, _ = report(f'zLIVE common k={keL:.2f} (exp-matched)', z_votes_fn('zL', keL), base, control=False)

# ================================================================ 5. mechanism: where do the rules disagree?
disagreement(f'z30 common k={kc30:.2f}', z_votes_fn('z30', kc30))
disagreement(f'z30 per-window (search-cal)', z_votes_fn('z30', KS30))
disagreement(f'volscaled a=1 exp vol30', volscaled_votes_fn('z30', 1.0, 'exp'))

# ================================================================ 6. bootstrap, LORO, placebo on the headline variants
import os
FAST = os.environ.get('FAST') == '1'     # FAST=1 skips the bootstraps and placebo while iterating
for lab, v in ([] if FAST else ((f'z30 common k={kc30:.2f}', z_votes_fn('z30', kc30)),
               (f'z30 per-window search-cal', z_votes_fn('z30', KS30)),
               ('volscaled a=1 exp vol30', volscaled_votes_fn('z30', 1.0, 'exp')))):
    bootstrap_and_loro(lab, v)

print(f"\nPLACEBO: z30 common k={kc30:.2f} with the vol term block-shuffled by calendar year (20 seeds)")
pl = []
for seed in ([] if FAST else range(20)):
    sv = year_shuffled_vol(seed)
    def votes(r, sv=sv):
        if r['eff'] != 'A': return 0
        return sum(1 for n in WINS if r['gaps'][n] / (sv[r['d']] * math.sqrt(n / 252.0)) > kc30)
    ev = evaluate(rows, weight_fn(votes)); pl.append(ev)
sh = sorted(e['sharpe'] for e in pl); ss = sorted(e['s_sharpe'] for e in pl); hs = sorted(e['h_sharpe'] for e in pl)
if pl: print(f"   placebo Sharpe: min {sh[0]:.3f} median {sh[10]:.3f} max {sh[-1]:.3f}   search median {ss[10]:.3f}  holdout median {hs[10]:.3f}  "
      f"exposure median {sorted(e['risky'] for e in pl)[10]*100:.2f}%")
if pl: print(f"   real z-trim (same k): {ev_c30['sharpe']:.3f} (S {ev_c30['s_sharpe']:.3f} H {ev_c30['h_sharpe']:.3f}); live {base['sharpe']:.3f}; "
      f"placebos beating the real z-trim: {sum(1 for e in pl if e['sharpe'] > ev_c30['sharpe'])}/20; beating live: {sum(1 for e in pl if e['sharpe'] > base['sharpe'])}/20")

# also: the z-rule with vol replaced by a CONSTANT (its full-sample median) -- this is the price rule with re-scaled thresholds
def const_votes(r):
    if r['eff'] != 'A': return 0
    return sum(1 for n in WINS if r['gaps'][n] / (FULL_MED * math.sqrt(n / 252.0)) > kc30)
report('z30 with vol := constant median', const_votes, base, control=False)

# ================================================================ 7. WHERE does the z-rule lose? P&L attribution, churn, hybrids
def attribution(label, votes):
    """Attribute the HARNESS daily return difference (cand - live) to the
    disagreement bucket on the decision day, by era. This is realised P&L
    through the real loop (costs, drift band, vol target), not forward
    returns."""
    a = run(rows, weight_fn(votes))[0]; b = run(rows, LIVE)[0]
    print(f"\nP&L ATTRIBUTION of ({label} - live): sum of daily return differences (pp) by bucket and era")
    print(f"  {'bucket':<11}{'n':>6}{'holdout':>10}{'search':>10}{'total':>10}   {'mean/day bp':>12}")
    B = {}
    for r, x, y in zip(rows, a, b):
        lv, cv = live_votes(r), votes(r)
        key = ('both trim' if lv and cv else 'LIVE only' if lv else 'CAND only' if cv else 'neither(A)' if r['eff'] == 'A' else 'not A')
        e = 'S' if r['d'] >= SEARCH[0] else 'H'
        d = B.setdefault(key, {'S': 0.0, 'H': 0.0, 'n': 0}); d[e] += x - y; d['n'] += 1
    for key in ('both trim', 'LIVE only', 'CAND only', 'neither(A)', 'not A'):
        d = B.get(key)
        if not d: continue
        print(f"  {key:<11}{d['n']:>6}{d['H']*100:>+10.2f}{d['S']*100:>+10.2f}{(d['H']+d['S'])*100:>+10.2f}   {(d['H']+d['S'])/d['n']*1e4:>+12.2f}")
    Y = {}
    for r, x, y in zip(rows, a, b): Y[r['d'][:4]] = Y.get(r['d'][:4], 0) + (x - y)
    print("  per-year (pp): " + ", ".join(f"{k} {v*100:+.1f}" for k, v in sorted(Y.items()) if abs(v) > 0.005))

def churn(label, votes):
    prev = 0; ch = {}
    for r in rows:
        v = votes(r); y = r['d'][:4]
        ch[y] = ch.get(y, 0) + (1 if v != prev else 0); prev = v
    s_ = [v for y, v in ch.items() if y >= '2016']; h_ = [v for y, v in ch.items() if y < '2016']
    print(f"  vote changes/yr {label:<32} {sum(ch.values())/len(ch):5.1f}   (search {sum(s_)/len(s_):.1f}, holdout {sum(h_)/len(h_):.1f})")

attribution(f'z30 common k={kc30:.2f}', z_votes_fn('z30', kc30))
attribution(f'zLIVE common k={kcL:.2f}', z_votes_fn('zL', kcL))
print("\nCHURN (number of vote-count changes per year, proxy):")
churn('live price rule', live_votes)
churn(f'z30 common k={kc30:.2f}', z_votes_fn('z30', kc30))
churn(f'zLIVE common k={kcL:.2f}', z_votes_fn('zL', kcL))
churn('volscaled a=1 exp vol30', volscaled_votes_fn('z30', 1.0, 'exp'))

print("\n== 8. HYBRIDS: combine the price rule and the z rule per window ==")
def hybrid(mode, key, K):
    def votes(r):
        if r['eff'] != 'A': return 0
        z = r[key]; n_ = 0
        for n in WINS:
            p = r['gaps'][n] > THR[n]; q = z[n] > (K[n] if isinstance(K, dict) else K)
            n_ += (p and q) if mode == 'AND' else (p or q)
        return n_
    return votes
for mode in ('AND', 'OR'):
    report(f'{mode} price & z30 k={kc30:.2f}', hybrid(mode, 'z30', kc30), base)
    report(f'{mode} price & zLIVE k={kcL:.2f}', hybrid(mode, 'zL', kcL), base)

print("\nDISAGREEMENT buckets by era (z30 common k): QQQ forward 21d mean / hit")
for elab, lo, hi in (('holdout', *HOLDOUT), ('search', *SEARCH)):
    B = {}
    for r in era(rows, lo, hi):
        if r['eff'] != 'A': continue
        lv, cv = live_votes(r), z_votes_fn('z30', kc30)(r)
        key = ('both trim' if lv and cv else 'LIVE only' if lv else 'CAND only' if cv else 'neither')
        f = fwd(r['d'], 21)
        if f is not None: B.setdefault(key, []).append(f)
    print(f"  {elab:<8}" + "   ".join(f"{k}: n {len(v)} {sum(v)/len(v)*100:+.2f}% hit {sum(1 for x in v if x>0)/len(v)*100:.0f}%" for k, v in sorted(B.items())))

print(f"\nCANDIDATE COUNT: {len(CANDIDATES)} variants evaluated on the proxy (excluding the live baseline and the 20 placebo draws)")
print(f"both-era winners ({len(WINNERS)}): {WINNERS}")
