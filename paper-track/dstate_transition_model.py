"""Research line dstate_transition_model (2026-09-11): a probability model for the outcome of a state-D episode.

Question.  On any effective-state-D day, what is P(breakdown) -- the probability that the episode the day belongs to
ends with the next effective state E or F (QQQ breaks its 200d) rather than A/B (recovery above the 50d)?  The
dgate_anatomy line established the one-feature baseline: P(E/F) by trailing-252 quintile of the 60d change of
log(QQEW/QQQ) = 0.54 / 0.27 / 0.05 / 0.05 / 0.30 on n = 124/162/187/132/122 D days (727 D days, 71 episodes,
2007-07-27..2026-08-26).  That bucket table is the baseline to beat.

Design (all causal, all grouped by episode):
  * label per day = the eventual exit of the day's episode (E/F = 1, A/B = 0); every day of an episode shares it, so
    EVERY cross-validation is grouped by episode (10-fold grouped, stratified on the label; leave-one-episode-out for
    the cheap models) and every metric is reported day-weighted AND episode-weighted (first day; mean over days).
  * features at the d0 close: breadth pct (QQEW/QQQ 60d change, trailing-252 pct; and the survivorship-free
    NASDAQCOM/NASDAQ100 version), gap200, gap50, 30d realized vol and its trailing-252 pct, sessions since the episode
    began (log1p), QQQ 20d return, fast 20/100 state already D/E/F, 10d/30d vol ratio, 60-session change in DGS2.
    Standardized with the TRAINING fold's mean/sd only.
  * models: (1) bucket base rate (training-fold quintile frequency, Jeffreys-smoothed); (2) logistic on breadth alone;
    (3) L2 logistic on all features, lambda by inner grouped 5-fold CV; (4a) 1-3 feature logistic by nested forward
    selection; (4b) a decision stump (feature + threshold chosen in the training fold).
  * metrics: log-loss, Brier, AUC, fixed-width calibration table; same numbers for the bucket baseline on the same folds.
  * time-ordered split: fit on episodes ending before 2015-11-01, test after; and the reverse.
  * decision value through the project harness only: 'D row to cash when P_oof > p*' for p* in {0.3,0.4,0.5,0.6} and the
    continuous 'QLD weight = 1 - P_oof', P_oof strictly out-of-fold (the fold in which the day's episode was held out),
    vs live, vs the plain breadth gate, vs the constant-D capital control, with the episode-block bootstrap.
  * today's reading, and the reading for a hypothetical D day tomorrow with today's features, with an episode-bootstrap
    interval on P.
Two samples: (Q) the 727 D days on the QQEW rows; (C) the 934 D days on the full 2000-07+ proxy rows with the
composite/NDX breadth proxy (adds the 2000-2006 episodes).

Nothing is re-implemented that already exists: the harness bootstrap (leverage_under_trim), sections 0-3 of
breadth_dgate_2000.py (standing-figure assert, data, ratio series, trailing_pct, row attachment, trimmed/scale_risky/
gate_fn/const_D/calib_q) and the reference-figure / episode / exit-labelling / bucket-grid / episode-bootstrap code of
dgate_anatomy.py are exec'd verbatim from those files.  Logistic regression is Newton-Raphson in the standard library
(no numpy / sklearn in this environment).  Research only; nothing is applied.  Run from the repo root:
    DSTM_SAMPLES=Q python3 paper-track/dstate_transition_model.py   (~7 min per sample; run again with =C)
    DSTM_FAST=1 python3 paper-track/dstate_transition_model.py        (both samples, 300 draws, ~4 min)
"""
import sys, os, math, csv, bisect, zlib, random, time
sys.path.insert(0, 'paper-track')
T0 = time.time()
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from state import extension_scale, extension_votes, EXTENSION_STEP
from block_bootstrap import boot, stats, N_BOOT
from improvement_search import SEARCH, HOLDOUT, era
from long_history_backtest import load_px as _load_px
FAST = bool(os.environ.get('DSTM_FAST'))
NB = 300 if FAST else 1000        # episode-bootstrap draws for the harness comparisons (1000: ~44 policies x 2 refs per sample)
KEYS = os.environ.get('DSTM_SAMPLES', 'QC')   # run one sample per call to stay inside a 10-minute foreground timeout
NB_COEF = 100 if FAST else 400    # episode-bootstrap refits for coefficient / today's-P intervals

print("=" * 112)
print("RESEARCH LINE dstate_transition_model -- P(breakdown) for a state-D episode, grouped-by-episode, causal")
print("=" * 112)

# ---- reuse 1: breadth_dgate_2000.py sections 0-3 verbatim (standing-figure assert 22.18/0.913/-33.6 + real 1.248 inside)
_SRC = open('paper-track/breadth_dgate_2000.py').read()
_A = _SRC.index('# ------------------------------------------------------------------ 0. live design')
_B = _SRC.index('# ------------------------------------------------------------------ 4. VALIDATION')
exec(_SRC[_A:_B])
print(f"\n(reused breadth_dgate_2000.py sections 0-3 verbatim: {_SRC[_A:_B].count(chr(10))} lines)")
# ---- reuse 2: dgate_anatomy.py reference rows/figures, episode segmentation, exit labelling, bucket grid, episode bootstrap
_AN = open('paper-track/dgate_anatomy.py').read()
_a = _AN.index('# ---- the reference rows and the reference figures'); _b = _AN.index('# =====', _a)
exec(_AN[_a:_b])                       # RQ, RQ_I0, GATE, EVG, BL_EV, Q, CD, EVC, A_G/A_L/A_C, episodes(), EP_D, exit_state(), ep_of(), gated(), RUNS ...
_a = _AN.index('def grid(scope_rows'); _b = _AN.index('GA = grid(A_ROWS')
print("\nANATOMY BUCKET TABLE (reused grid(); must match P(E/F) 0.54/0.27/0.05/0.05/0.30 on n=124/162/187/132/122):")
exec(_AN[_a:_b])                       # grid(), D_ROWS, A_ROWS, EP_ALL, GD
_a = _AN.index('def ep_boot('); _b = _AN.index("\nfor lab, ref in (('const-D', A_C)", _a)
exec(_AN[_a:_b])                       # ep_boot(a, b, rs, i0, nb, seed_) -> (l_lo, l_hi, P_l, s_lo, s_hi, P_s, n_eps); uses global EP_D
assert [GD[b]['n'] for b in range(5)] == [124, 162, 187, 132, 122] and [round(GD[b]['pef'], 2) for b in range(5)] == [0.54, 0.27, 0.05, 0.05, 0.30], "bucket table not reproduced"
print(f"  reproduced.  (setup {time.time()-T0:.1f}s)")

# =====================================================================================================================
print("\n" + "=" * 112)
print("1. SAMPLES, LABELS, FEATURES")
print("=" * 112)
# ---- DGS2 (FRED; empty on holidays -> forward-fill via FF, never dropped)
DGS2 = {}
for r_ in csv.DictReader(open('data/dgs2.csv')):
    if r_['DGS2'] not in ('', '.'): DGS2[r_['observation_date']] = float(r_['DGS2'])
FDG = FF(DGS2)
# ---- 30d realized vol series on the harness QQQ calendar (ds/px), and its trailing-252 percentile (trailing_pct reused)
pv = [px[d] for d in ds]; pix = {d: i for i, d in enumerate(ds)}
_rets = [None] + [pv[i] / pv[i - 1] - 1 for i in range(1, len(pv))]
def _vol_at(i, n):
    r_ = [x for x in _rets[max(1, i - n + 1):i + 1] if x is not None]
    if len(r_) < n: return None
    m = sum(r_) / n; return (sum((x - m) ** 2 for x in r_) / (n - 1)) ** 0.5 * math.sqrt(252)
VOL30 = [_vol_at(i, 30) for i in range(len(ds))]
VOLP = trailing_pct(VOL30)
# rows start 2000-07-03 but the 252-window on VOL30 only fills from ~2000-10: use an EXPANDING percentile (>=60 obs) there,
# still strictly causal (only past values); flagged in the writeup.  Affects ~80 rows in 2000-07..2000-10.
_hist = []; N_EXPAND = 0
for i, v in enumerate(VOL30):
    if v is None: continue
    if VOLP[i] is None and len(_hist) >= 60:
        lo = bisect.bisect_left(_hist, v); hi = bisect.bisect_right(_hist, v); VOLP[i] = (lo + 0.5 * (hi - lo)) / len(_hist); N_EXPAND += 1
    bisect.insort(_hist, v)
    if len(_hist) > 252: _hist.pop(bisect.bisect_left(_hist, VOL30[i - 252]))
def ret_n(i, n): return pv[i] / pv[i - n] - 1 if i - n >= 0 else None
_IDX = {id(r_): i for i, r_ in enumerate(rows)}
EPF = episodes('D')                      # every D episode on the full 2000-07+ rows
def ep_start(i, eps):
    e = ep_of(i, eps); return e[0]

def features_of(r, i, dse, bkey):
    """feature dict for row r (index i in rows) on a D day dse sessions into its episode; bkey = breadth series for 'bp'."""
    j = pix[r['d']]
    d60 = ds[j - 60] if j - 60 >= 0 else None
    dg = (FDG.at(r['d']) - FDG.at(d60)) if (d60 and FDG.at(r['d']) is not None and FDG.at(d60) is not None) else None
    f = {
        'bp': r['bp'][bkey],                           # breadth pct (the gate's series in this sample)
        'bp_sq': None if r['bp'][bkey] is None else (r['bp'][bkey] - 0.5) ** 2,   # U-shape term (top quintile also 0.30)
        'bp_comp': r['bp']['comp_60'],                 # survivorship-free composite/NDX version
        'gap200': r['gaps'][200], 'gap50': r['gap50'],
        'vol30': r['vol'], 'vol_pct': VOLP[j],
        'ldse': math.log1p(dse),                       # sessions since the episode began (log1p)
        'ret20': ret_n(j, 20),
        'fast_def': 1.0 if fast[r['d']] in ('D', 'E', 'F') else 0.0,   # fast 20/100 state already D/E/F
        'volratio': (r['vol10'] / r['vol']) if (r['vol10'] and r['vol']) else None,   # 10d / 30d
        'dgs2_60': dg,                                 # 60-session change in the 2y yield (pp)
    }
    return f
FEATS_Q = ['bp', 'bp_sq', 'bp_comp', 'gap200', 'gap50', 'vol30', 'vol_pct', 'ldse', 'ret20', 'fast_def', 'volratio', 'dgs2_60']
FEATS_C = [f for f in FEATS_Q if f != 'bp_comp']      # in the composite sample 'bp' IS the composite series

def build_sample(eps, i_min, bkey, feats):
    """one record per D day: dict(d, i, ep, y, dse, x=[...]) ; episodes need a known exit; days need every feature."""
    recs = []; ep_ids = {}; n_skip = 0
    for k, e in enumerate(eps):
        ex = exit_state(e)
        if ex is None: continue
        y = 1.0 if ex in ('E', 'F') else 0.0
        for i in range(max(e[0], i_min), e[1] + 1):
            f = features_of(rows[i], i, i - e[0], bkey)
            if any(f[n] is None for n in feats): n_skip += 1; continue
            recs.append(dict(d=rows[i]['d'], i=i, ep=k, y=y, dse=i - e[0], tte=e[1] - i + 1, f=f, x=[f[n] for n in feats], ex=ex))
    return recs, n_skip
SAMPLES = {}
SQ, skq = build_sample(EP_D, RQ_I0, 'qqew_60', FEATS_Q)
SC, skc = build_sample(EPF, 0, 'comp_60', FEATS_C)
SAMPLES['Q'] = dict(recs=SQ, feats=FEATS_Q, rows=RQ, i0=RQ_I0, eps=EP_D, label='Q: QQEW rows 2007-07+', bkey='qqew_60')
SAMPLES['C'] = dict(recs=SC, feats=FEATS_C, rows=rows, i0=0, eps=EPF, label='C: full proxy rows 2000-07+ (composite/NDX breadth)', bkey='comp_60')
from collections import Counter
for key, S in SAMPLES.items():
    R = S['recs']; eps_ = sorted(set(r_['ep'] for r_ in R)); ny = sum(1 for e in eps_ if next(r_ for r_ in R if r_['ep'] == e)['y'] == 1)
    print(f"  [{S['label']}] D days {len(R)} (skipped for missing feature: {skq if key=='Q' else skc}), episodes {len(eps_)}, breakdown episodes {ny} "
          f"({ny/len(eps_):.2f}), breakdown days {sum(1 for r_ in R if r_['y']==1)} ({mean([r_['y'] for r_ in R]):.2f}); exits {dict(Counter(r_['ex'] for r_ in R if r_['dse']==0 or r_['i']==max(S['i0'], S['eps'][r_['ep']][0])))}")
print(f"  vol percentile: {N_EXPAND} early sessions use an expanding (>=60 obs) causal percentile instead of the 252-window")
print("\n  feature means on D days by label (raw units), sample Q:")
print(f"  {'feature':<10}{'recover':>10}{'breakdown':>11}{'diff t':>8}  |  sample C: {'recover':>10}{'breakdown':>11}{'diff t':>8}")
def _t2(a, b):
    ma, mb = mean(a), mean(b); va = sum((x - ma) ** 2 for x in a) / (len(a) - 1); vb = sum((x - mb) ** 2 for x in b) / (len(b) - 1)
    return (mb - ma) / math.sqrt(va / len(a) + vb / len(b))
for n in FEATS_Q:
    line = f"  {n:<10}"
    for key in KEYS:
        R = SAMPLES[key]['recs']
        if n not in SAMPLES[key]['feats']: line += f"{'':>29}  |  "; continue
        a = [r_['f'][n] for r_ in R if r_['y'] == 0]; b = [r_['f'][n] for r_ in R if r_['y'] == 1]
        line += f"{mean(a):>10.4f}{mean(b):>11.4f}{_t2(a, b):>8.2f}" + ("  |  " if key == 'Q' else "")
    print(line)
print("  (t is day-weighted and overstated: the ~70-90 episodes are the independent units, not the days)")

# =====================================================================================================================
# 2. MODELS (standard library only)
# =====================================================================================================================
def _solve(A, b):
    n = len(b); M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r_: abs(M[r_][c])); M[c], M[p] = M[p], M[c]
        piv = M[c][c]
        if abs(piv) < 1e-14: piv = 1e-14
        for r_ in range(c + 1, n):
            f = M[r_][c] / piv
            if f:
                Mr = M[r_]; Mc = M[c]
                for k in range(c, n + 1): Mr[k] -= f * Mc[k]
    x = [0.0] * n
    for r_ in range(n - 1, -1, -1):
        x[r_] = (M[r_][n] - sum(M[r_][k] * x[k] for k in range(r_ + 1, n))) / (M[r_][r_] if abs(M[r_][r_]) > 1e-14 else 1e-14)
    return x
def _sig(z): return 1.0 / (1.0 + math.exp(-z)) if z > -700 else 0.0
def standardize(Xtr, Xte):
    p = len(Xtr[0]); n = len(Xtr)
    mu = [sum(x[k] for x in Xtr) / n for k in range(p)]
    sd_ = [max(1e-9, (sum((x[k] - mu[k]) ** 2 for x in Xtr) / max(1, n - 1)) ** 0.5) for k in range(p)]
    f = lambda X: [[(x[k] - mu[k]) / sd_[k] for k in range(p)] for x in X]
    return f(Xtr), f(Xte), mu, sd_
def logit_fit(X, y, lam, iters=30, beta0=None):
    """L2-penalized logistic regression by Newton-Raphson; X standardized (no intercept column), penalty on slopes only.
    Returns [b0, b1..bp]."""
    n = len(X); p = len(X[0]) + 1; beta = list(beta0) if beta0 else [0.0] * p
    X1 = [[1.0] + list(x) for x in X]
    def nll(bt):
        s = 0.0
        for xi, yi in zip(X1, y):
            z = sum(b * v for b, v in zip(bt, xi)); s += math.log1p(math.exp(-abs(z))) + max(z, 0.0) - z * yi
        return s + 0.5 * lam * sum(b * b for b in bt[1:])
    cur = nll(beta)
    for it in range(iters):
        g = [0.0] * p; H = [[0.0] * p for _ in range(p)]
        for xi, yi in zip(X1, y):
            pr = _sig(sum(b * v for b, v in zip(beta, xi))); d = pr - yi; s = pr * (1 - pr)
            for a in range(p):
                xa = xi[a]
                if xa == 0.0: continue
                g[a] += d * xa; Ha = H[a]; xs = xa * s
                for b in range(a, p): Ha[b] += xs * xi[b]
        for a in range(p):
            for b in range(a):
                H[a][b] = H[b][a]
        for a in range(1, p): g[a] += lam * beta[a]; H[a][a] += lam
        step = _solve(H, g); t = 1.0
        while True:
            nb_ = [b - t * s_ for b, s_ in zip(beta, step)]; v = nll(nb_)
            if v <= cur + 1e-12 or t < 1e-4: break
            t *= 0.5
        conv = max(abs(t * s_) for s_ in step) < 1e-7; beta, cur = nb_, v
        if conv: break
    return beta
def logit_pred(beta, X): return [_sig(beta[0] + sum(b * v for b, v in zip(beta[1:], x))) for x in X]
LAMS = [0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0]

# ---- metrics
def _clip(p): return min(1 - 1e-6, max(1e-6, p))
def logloss(P, Y): return -mean([y * math.log(_clip(p)) + (1 - y) * math.log(1 - _clip(p)) for p, y in zip(P, Y)])
def brier(P, Y): return mean([(p - y) ** 2 for p, y in zip(P, Y)])
def auc(P, Y):
    pos = [p for p, y in zip(P, Y) if y == 1]; neg = [p for p, y in zip(P, Y) if y == 0]
    if not pos or not neg: return float('nan')
    sn = sorted(neg); s = 0.0
    for p in pos: s += bisect.bisect_left(sn, p) + 0.5 * (bisect.bisect_right(sn, p) - bisect.bisect_left(sn, p))
    return s / (len(pos) * len(neg))
def metrics(P, Y): return dict(ll=logloss(P, Y), br=brier(P, Y), auc=auc(P, Y), n=len(Y))
def ep_views(recs, P):
    """three views: day-weighted; first day of each episode; per-episode mean of the daily P."""
    by = {}
    for r_, p in zip(recs, P): by.setdefault(r_['ep'], []).append((r_['dse'], p, r_['y']))
    first = [(min(v)[1], v[0][2]) for v in by.values()]; meanp = [(mean([p for _, p, _ in v]), v[0][2]) for v in by.values()]
    far = [(p, r_['y']) for r_, p in zip(recs, P) if r_['tte'] >= 5]
    return dict(day=metrics(P, [r_['y'] for r_ in recs]), first=metrics([p for p, _ in first], [y for _, y in first]), epmean=metrics([p for p, _ in meanp], [y for _, y in meanp]),
                far=metrics([p for p, _ in far], [y for _, y in far]))
def calib_table(recs, P, label):
    print(f"    calibration [{label}] fixed bins of predicted P; day-weighted and first-day-of-episode")
    print(f"    {'bin':<10}{'n days':>7}{'mean P':>8}{'realized':>9}{'| n eps':>8}{'mean P':>8}{'realized':>9}")
    by = {}
    for r_, p in zip(recs, P): by.setdefault(r_['ep'], []).append((r_['dse'], p, r_['y']))
    first = [min(v)[1:] for v in by.values()]
    for b in range(10):
        lo, hi = b / 10, (b + 1) / 10
        dd = [(p, r_['y']) for r_, p in zip(recs, P) if lo <= p < hi or (b == 9 and p == 1.0)]; ee = [(p, y) for p, y in first if lo <= p < hi or (b == 9 and p == 1.0)]
        if not dd and not ee: continue
        print(f"    {f'{lo:.1f}-{hi:.1f}':<10}{len(dd):>7}{mean([p for p,_ in dd]) if dd else float('nan'):>8.3f}{mean([y for _,y in dd]) if dd else float('nan'):>9.3f}"
              f"{len(ee):>8}{mean([p for p,_ in ee]) if ee else float('nan'):>8.3f}{mean([y for _,y in ee]) if ee else float('nan'):>9.3f}")

# ---- fold machinery (grouped by episode, stratified on the episode label)
def grouped_folds(recs, k, seed_):
    eps_ = {};
    for r_ in recs: eps_[r_['ep']] = r_['y']
    rng = random.Random(seed_); out = {}
    for lab in (0.0, 1.0):
        e = [x for x, y in eps_.items() if y == lab]; rng.shuffle(e)
        for j, x in enumerate(e): out[x] = j % k
    return out   # episode -> fold
def split(recs, fold_of, f):
    tr = [r_ for r_ in recs if fold_of[r_['ep']] != f]; te = [r_ for r_ in recs if fold_of[r_['ep']] == f]
    return tr, te

# ---- model fitters: each takes (train recs, test recs, feats, ctx) -> (test P, info)
def fit_bucket(tr, te, feats, ctx):
    ib = feats.index('bp'); cnt = [[0, 0] for _ in range(5)]
    for r_ in tr: b = min(4, int(r_['x'][ib] * 5)); cnt[b][0] += r_['y']; cnt[b][1] += 1
    rate = [(c[0] + 0.5) / (c[1] + 1.0) for c in cnt]            # Jeffreys-smoothed training-fold frequency
    return [rate[min(4, int(r_['x'][ib] * 5))] for r_ in te], dict(rate=rate)
def _fit_logit_cols(tr, te, cols, lam):
    Xtr = [[r_['x'][c] for c in cols] for r_ in tr]; Xte = [[r_['x'][c] for c in cols] for r_ in te]
    Xtr_s, Xte_s, mu, sd_ = standardize(Xtr, Xte); beta = logit_fit(Xtr_s, [r_['y'] for r_ in tr], lam)
    return logit_pred(beta, Xte_s), beta, mu, sd_
def inner_cv_ll(tr, cols, lam, k=5, seed_=7):
    fo = grouped_folds(tr, k, seed_); P = []; Y = []
    for f in range(k):
        a, b = split(tr, fo, f)
        if not b or len(set(r_['y'] for r_ in a)) < 2: continue
        p, _, _, _ = _fit_logit_cols(a, b, cols, lam); P += p; Y += [r_['y'] for r_ in b]
    return logloss(P, Y)
def fit_breadth(tr, te, feats, ctx):
    cols = [feats.index('bp')]; lam = ctx.get('lam_b')
    if lam is None: lam = min(LAMS, key=lambda l: inner_cv_ll(tr, cols, l))
    p, beta, mu, sd_ = _fit_logit_cols(tr, te, cols, lam); return p, dict(lam=lam, beta=beta)
def fit_breadth_u(tr, te, feats, ctx):
    cols = [feats.index('bp'), feats.index('bp_sq')]; lam = ctx.get('lam_bu')
    if lam is None: lam = min(LAMS, key=lambda l: inner_cv_ll(tr, cols, l))
    p, beta, mu, sd_ = _fit_logit_cols(tr, te, cols, lam); return p, dict(lam=lam, beta=beta)
def fit_all(tr, te, feats, ctx):
    cols = list(range(len(feats))); lam = ctx.get('lam_all')
    if lam is None: lam = min(LAMS, key=lambda l: inner_cv_ll(tr, cols, l))
    p, beta, mu, sd_ = _fit_logit_cols(tr, te, cols, lam); return p, dict(lam=lam, beta=beta, mu=mu, sd=sd_)
def fit_nogap(tr, te, feats, ctx):
    """all features EXCEPT the distance-to-SMA ones (gap200, gap50): does anything non-mechanical carry information?"""
    cols = [k for k, n in enumerate(feats) if n not in ('gap200', 'gap50')]; lam = ctx.get('lam_ng')
    if lam is None: lam = min(LAMS, key=lambda l: inner_cv_ll(tr, cols, l))
    p, beta, mu, sd_ = _fit_logit_cols(tr, te, cols, lam); return p, dict(lam=lam, beta=beta)
def fit_fwd(tr, te, feats, ctx, kmax=3, lam=3.0):
    """nested forward selection: add the feature that most lowers the inner grouped-CV log-loss; stop when none does."""
    chosen = []; best = float('inf'); hist = []
    while len(chosen) < kmax:
        cand = [(inner_cv_ll(tr, chosen + [c], lam), c) for c in range(len(feats)) if c not in chosen]
        v, c = min(cand)
        if v >= best - 1e-4: break
        chosen.append(c); best = v; hist.append((feats[c], v))
    p, beta, mu, sd_ = _fit_logit_cols(tr, te, chosen, lam); return p, dict(cols=[feats[c] for c in chosen], beta=beta, lam=lam)
def fit_stump(tr, te, feats, ctx):
    """one split on one feature, leaves = Jeffreys-smoothed training frequency; feature/threshold by training log-loss."""
    best = None
    for c in range(len(feats)):
        vals = sorted(set(r_['x'][c] for r_ in tr))
        if len(vals) < 3: cuts = vals[1:]
        else: cuts = [vals[int(len(vals) * q)] for q in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)]
        for t in cuts:
            l = [r_['y'] for r_ in tr if r_['x'][c] < t]; h = [r_['y'] for r_ in tr if r_['x'][c] >= t]
            if len(l) < 20 or len(h) < 20: continue
            pl = (sum(l) + 0.5) / (len(l) + 1); ph = (sum(h) + 0.5) / (len(h) + 1)
            ll = logloss([pl] * len(l) + [ph] * len(h), l + h)
            if best is None or ll < best[0]: best = (ll, c, t, pl, ph)
    _, c, t, pl, ph = best
    return [pl if r_['x'][c] < t else ph for r_ in te], dict(feat=feats[c], thr=t, pl=pl, ph=ph)
MODELS = [('bucket', fit_bucket), ('breadth', fit_breadth), ('breadth+U', fit_breadth_u), ('all-L2', fit_all), ('noGap-L2', fit_nogap), ('fwd-sel', fit_fwd), ('stump', fit_stump)]

def run_cv(recs, feats, k, seed_, models=MODELS, ctx=None, verbose=True):
    """grouped k-fold; returns out-of-fold P per model (aligned with recs) and per-fold info."""
    ctx = ctx or {}; fo = grouped_folds(recs, k, seed_); OOF = {m: [None] * len(recs) for m, _ in models}; INFO = {m: [] for m, _ in models}
    pos = {id(r_): j for j, r_ in enumerate(recs)}
    for f in range(k):
        tr, te = split(recs, fo, f)
        if not te: continue
        for m, fn in models:
            p, info = fn(tr, te, feats, ctx); INFO[m].append(info)
            for r_, v in zip(te, p): OOF[m][pos[id(r_)]] = v
    return OOF, INFO
def report(recs, OOF, title, calib_for=()):
    Y = [r_['y'] for r_ in recs]
    print(f"\n  {title}")
    print(f"  {'model':<10}{'| day: logloss':>15}{'Brier':>7}{'AUC':>7}{'| first-day: logloss':>21}{'Brier':>7}{'AUC':>7}{'| ep-mean: logloss':>19}{'Brier':>7}{'AUC':>7}{'| >=5d to exit: ll':>19}{'Brier':>7}{'AUC':>7}")
    out = {}
    for m, P in OOF.items():
        v = ep_views(recs, P); out[m] = v
        print(f"  {m:<10}{v['day']['ll']:>15.4f}{v['day']['br']:>7.4f}{v['day']['auc']:>7.3f}{v['first']['ll']:>21.4f}{v['first']['br']:>7.4f}{v['first']['auc']:>7.3f}"
              f"{v['epmean']['ll']:>19.4f}{v['epmean']['br']:>7.4f}{v['epmean']['auc']:>7.3f}{v['far']['ll']:>19.4f}{v['far']['br']:>7.4f}{v['far']['auc']:>7.3f}")
    base_ll = logloss([mean(Y)] * len(Y), Y)
    nf = sum(1 for r_ in recs if r_['tte'] >= 5)
    print(f"  (constant P = sample base rate {mean(Y):.3f}: day log-loss {base_ll:.4f}, Brier {brier([mean(Y)]*len(Y), Y):.4f}; n days {len(Y)}, episodes {len(set(r_['ep'] for r_ in recs))}; days >=5 to exit {nf})")
    for m in calib_for: calib_table(recs, OOF[m], m)
    return out

# =====================================================================================================================
print("\n" + "=" * 112)
print("2. GROUPED 10-FOLD CV (stratified on the episode label; lambda / features / stump chosen INSIDE each training fold)")
print("=" * 112)
CV = {}
for key in KEYS:
    S = SAMPLES[key]; t1 = time.time()
    OOF, INFO = run_cv(S['recs'], S['feats'], 10, seed_=zlib.crc32(key.encode()))
    CV[key] = (OOF, INFO)
    lam_all = [i['lam'] for i in INFO['all-L2']]; lam_b = [i['lam'] for i in INFO['breadth']]
    print(f"\n[{S['label']}]  ({time.time()-t1:.0f}s)")
    print(f"  inner-CV lambda chosen per fold: all-L2 {lam_all}; breadth {lam_b}; noGap-L2 {[i['lam'] for i in INFO['noGap-L2']]}")
    print(f"  forward selection per fold: {[i['cols'] for i in INFO['fwd-sel']]}")
    print(f"  stump per fold: {[(i['feat'], round(i['thr'], 3), round(i['pl'], 2), round(i['ph'], 2)) for i in INFO['stump']]}")
    print(f"  bucket rates per fold (bottom..top quintile): " + "; ".join("/".join(f"{x:.2f}" for x in i['rate']) for i in INFO['bucket'][:5]) + " ...")
    report(S['recs'], OOF, f"grouped 10-fold, out-of-fold metrics ({key})", calib_for=('bucket', 'breadth', 'all-L2'))
    # a second seed for the fold assignment, to show the fold-noise
    OOF2, _ = run_cv(S['recs'], S['feats'], 10, seed_=zlib.crc32((key + 'b').encode()), models=[m for m in MODELS if m[0] != 'fwd-sel'])
    report(S['recs'], OOF2, f"same, second fold assignment ({key}; fwd-sel omitted for time)")

print("\n" + "=" * 112)
print("3. LEAVE-ONE-EPISODE-OUT (cheap models; lambda fixed at the median of the 10-fold inner-CV choices -> a mild leak, noted)")
print("=" * 112)
LOEO = {}
for key in KEYS:
    S = SAMPLES[key]; _, INFO = CV[key]; lam_all = sorted(i['lam'] for i in INFO['all-L2'])[len(INFO['all-L2']) // 2]; lam_b = sorted(i['lam'] for i in INFO['breadth'])[len(INFO['breadth']) // 2]
    lam_bu = sorted(i['lam'] for i in INFO['breadth+U'])[len(INFO['breadth+U']) // 2]; lam_ng = sorted(i['lam'] for i in INFO['noGap-L2'])[len(INFO['noGap-L2']) // 2]
    ne = len(set(r_['ep'] for r_ in S['recs'])); t1 = time.time()
    OOF, _ = run_cv(S['recs'], S['feats'], ne, seed_=1, models=[m for m in MODELS if m[0] != 'fwd-sel'], ctx=dict(lam_all=lam_all, lam_b=lam_b, lam_bu=lam_bu, lam_ng=lam_ng))
    LOEO[key] = OOF
    print(f"\n[{S['label']}] lambda all-L2 {lam_all}, breadth {lam_b}, breadth+U {lam_bu}  ({time.time()-t1:.0f}s)")
    report(S['recs'], OOF, f"leave-one-episode-out ({key}, {ne} folds)")

# =====================================================================================================================
print("\n" + "=" * 112)
print("4. TIME-ORDERED: fit on episodes ending before 2015-11-01, test on the rest; and the reverse")
print("=" * 112)
for key in KEYS:
    S = SAMPLES[key]; R = S['recs']; eps_ = S['eps']
    end_of = {k: rows[e[1]]['d'] for k, e in enumerate(eps_)}
    early = [r_ for r_ in R if end_of[r_['ep']] < SEARCH[0]]; late = [r_ for r_ in R if end_of[r_['ep']] >= SEARCH[0]]
    for lab, tr, te in ((f'fit <2015-11 ({len(set(r_["ep"] for r_ in early))} eps) -> test 2015-11+ ({len(set(r_["ep"] for r_ in late))} eps)', early, late),
                        (f'fit 2015-11+ -> test <2015-11', late, early)):
        OOF = {}
        for m, fn in MODELS:
            p, info = fn(tr, te, S['feats'], {}); OOF[m] = p
            if m == 'all-L2': print(f"  [{key}] {lab}: all-L2 lambda {info['lam']}")
            if m == 'fwd-sel': print(f"  [{key}] {lab}: fwd-sel {info['cols']}")
            if m == 'stump': print(f"  [{key}] {lab}: stump {info['feat']} < {info['thr']:.3f} -> {info['pl']:.2f} else {info['ph']:.2f}")
        report(te, OOF, f"[{key}] {lab}")

# =====================================================================================================================
print("\n" + "=" * 112)
print("5. COEFFICIENTS (all-L2 on the whole sample, lambda = LOEO choice; standardized units; episode-bootstrap 95% interval)")
print("=" * 112)
COEF = {}
for key in KEYS:
    S = SAMPLES[key]; R = S['recs']; feats = S['feats']; _, INFO = CV[key]; lam = sorted(i['lam'] for i in INFO['all-L2'])[len(INFO['all-L2']) // 2]
    cols = list(range(len(feats))); _, beta, mu, sd_ = _fit_logit_cols(R, R[:1], cols, lam)
    # episode bootstrap of the fit
    by_ep = {}
    for r_ in R: by_ep.setdefault(r_['ep'], []).append(r_)
    keys_ = sorted(by_ep); rng = random.Random(zlib.crc32((key + 'coef').encode())); B = []
    for _ in range(NB_COEF):
        samp = [r_ for k in (rng.choice(keys_) for _ in keys_) for r_ in by_ep[k]]
        if len(set(r_['y'] for r_ in samp)) < 2: continue
        _, bb, _, _ = _fit_logit_cols(samp, R[:1], cols, lam); B.append(bb)
    COEF[key] = dict(beta=beta, mu=mu, sd=sd_, lam=lam, boot=B)
    print(f"\n[{S['label']}] lambda {lam}, n {len(R)}, {NB_COEF} episode-bootstrap refits")
    print(f"  {'feature':<10}{'coef':>8}{'boot lo':>9}{'boot hi':>9}{'P(sign flips)':>15}   raw sd (1 unit of coef)")
    print(f"  {'intercept':<10}{beta[0]:>8.3f}{sorted(b[0] for b in B)[int(0.025*len(B))]:>9.3f}{sorted(b[0] for b in B)[int(0.975*len(B))-1]:>9.3f}")
    for k_, n in enumerate(feats):
        bs = sorted(b[k_ + 1] for b in B); lo, hi = bs[int(0.025 * len(bs))], bs[int(0.975 * len(bs)) - 1]
        flip = mean([1.0 if (b[k_ + 1] > 0) != (beta[k_ + 1] > 0) else 0.0 for b in B])
        print(f"  {n:<10}{beta[k_+1]:>8.3f}{lo:>9.3f}{hi:>9.3f}{flip:>15.2f}   {sd_[k_]:.4f}")
    # breadth-only coefficient for reference
    _, bb, _, sb = _fit_logit_cols(R, R[:1], [feats.index('bp')], sorted(i['lam'] for i in INFO['breadth'])[len(INFO['breadth']) // 2])
    print(f"  breadth-only: intercept {bb[0]:+.3f}, slope {bb[1]:+.3f} per sd of pct ({sb[0]:.3f}) -> P at pct 0.1 / 0.5 / 0.9 = "
          + " / ".join(f"{_sig(bb[0] + bb[1] * (p - mean([r_['f']['bp'] for r_ in R])) / sb[0]):.2f}" for p in (0.1, 0.5, 0.9)))

# =====================================================================================================================
print("\n" + "=" * 112)
print("6. DECISION VALUE through the harness: policies driven by the OUT-OF-FOLD P (10-fold grouped CV of section 2)")
print("=" * 112)
print("'cash > p*': the D row's QLD leg to cash when P_oof > p*; 'w=1-P': QLD weight scaled by (1 - P_oof).  Controls: same-rows live,")
print("the plain breadth gate (pct<0.2), constant-D at the policy's deployed capital (calib_q).  Episode-block bootstrap (ep_boot)")
print(f"of the Sharpe / log-return difference vs constant-D and vs live, {NB} draws.  A day with no P (not in the sample) holds the live row.")
def pol_fn(Pmap, mode, thr=None, vtf=vt, bkey=None):
    def fn(r):
        w = trimmed(r['eff'], r['gaps'])
        if r['eff'] == 'D':
            p = Pmap.get(r['d'] if 'd' in r else r['d0']); gt = (r['bp'][bkey] is not None and r['bp'][bkey] < 0.2) if bkey else False
            if p is not None:
                if mode == 'thr' and p > thr: w = scale_risky(w, 0.0)
                elif mode == 'cont': w = scale_risky(w, 1.0 - p)
                elif mode == 'and' and gt and p > thr: w = scale_risky(w, 0.0)
                elif mode == 'or' and (gt or p > thr): w = scale_risky(w, 0.0)
            elif mode == 'or' and gt: w = scale_risky(w, 0.0)
        return vtf(w, r['vol'])
    return fn
def rr_eval(fn_r):
    return RF.eval_real(rr, fn_r)
POL_ROWS = {}
for key in KEYS:
    S = SAMPLES[key]; R = S['recs']; OOF, _ = CV[key]; rs = S['rows']; i0 = S['i0']
    _EP_SAVE = EP_D; EP_D = S['eps']          # ep_boot resamples the sample's own D episodes
    b = evaluate(rs, LIVE); al = run(rs, LIVE)[0]
    gate_ = gate_fn(S['bkey'], 1.0); evg = evaluate(rs, gate_); ag = run(rs, gate_)[0]
    print(f"\n[{S['label']}] rows {len(rs)} {rs[0]['d']}..{rs[-1]['d']}; live {fmt(b)} S {b['s_sharpe']:.3f} H {b['h_sharpe']:.3f} exp {b['risky']*100:.1f}%")
    print(f"  {'policy':<24}{'CAGR/Sh/MDD':>22}{'S':>7}{'H':>7}{'exp':>7}{'on':>5}{'| vs live S/H':>15}{'| vs constD S/H':>16}{'| ep-boot Sh CI vs constD':>26}{'P<=0':>6}{'| vs live Sh CI':>17}{'P<=0':>6}{'| real Sh':>9}{'n':>4}")
    def show_pol(lab, fn, fn_r, on):
        ev = evaluate(rs, fn); q_ = calib_q(rs, ev['risky']); ce_ = evaluate(rs, const_D(q_)); a_ = run(rs, fn)[0]; c_ = run(rs, const_D(q_))[0]
        _, _, _, s1, s2, ps, ne = ep_boot(a_, c_, rs, i0, nb=NB, seed_=zlib.crc32((key + lab + 'c').encode()))
        _, _, _, t1_, t2_, pt, _ = ep_boot(a_, al, rs, i0, nb=NB, seed_=zlib.crc32((key + lab + 'l').encode()))
        re_ = rr_eval(fn_r); nmatch = sum(1 for r_ in rr if r_['eff'] == 'D' and PM.get(r_['d0']) is not None)
        print(f"  {lab:<24}{fmt(ev):>22}{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f}{ev['risky']*100:>6.1f}%{on:>5}"
              f"{ev['s_sharpe']-b['s_sharpe']:>+8.3f}/{ev['h_sharpe']-b['h_sharpe']:+.3f}{ev['s_sharpe']-ce_['s_sharpe']:>+9.3f}/{ev['h_sharpe']-ce_['h_sharpe']:+.3f}"
              f"{'':>8}[{s1:+.3f},{s2:+.3f}]{ps:>6.3f}{'':>2}[{t1_:+.3f},{t2_:+.3f}]{pt:>6.3f}{re_['sharpe']:>9.3f}{nmatch:>4}")
        return ev
    PM = {}
    show_pol('breadth gate pct<0.2', gate_, gate_fn(S['bkey'], 1.0, vtf=RF.vt), sum(1 for r_ in rs if r_['eff'] == 'D' and r_['bp'][S['bkey']] < 0.2))
    nD_rr = sum(1 for r_ in rr if r_['eff'] == 'D'); bk = S['bkey']
    for m in ('bucket', 'breadth', 'breadth+U', 'all-L2', 'noGap-L2', 'fwd-sel', 'stump'):
        PM = {r_['d']: p for r_, p in zip(R, OOF[m])}
        print(f"  -- model {m}: OOF P on {len(PM)} D days; mean P {mean(list(PM.values())):.3f}; P>0.3/0.4/0.5/0.6 on "
              + "/".join(str(sum(1 for p in PM.values() if p > t)) for t in (0.3, 0.4, 0.5, 0.6)) + f" days  (rr D rows {nD_rr})")
        for t in (0.3, 0.4, 0.5, 0.6):
            show_pol(f'{m} cash > {t:.1f}', pol_fn(PM, 'thr', t), pol_fn(PM, 'thr', t, RF.vt), sum(1 for p in PM.values() if p > t))
        show_pol(f'{m} w = 1-P', pol_fn(PM, 'cont'), pol_fn(PM, 'cont', vtf=RF.vt), len(PM))
        if m in ('all-L2', 'noGap-L2', 'fwd-sel'):
            for mode, t in (('and', 0.3), ('and', 0.5), ('or', 0.6), ('or', 0.8)):
                on = sum(1 for r_ in R if ((rows[r_['i']]['bp'][bk] < 0.2 and PM[r_['d']] > t) if mode == 'and' else (rows[r_['i']]['bp'][bk] < 0.2 or PM[r_['d']] > t)))
                show_pol(f'{m} gate {"&" if mode == "and" else "|"} P>{t:.1f}', pol_fn(PM, mode, t, bkey=bk), pol_fn(PM, mode, t, RF.vt, bkey=bk), on)
    # per-day diagnostics: does the OOF P separate the QLD leg WITHIN gated days and WITHIN un-gated days?
    print(f"\n  PER-DAY QLD-LEG (d0->d1, bp) BY OUT-OF-FOLD P, within gated (pct<0.2) and un-gated D days; label share = P(E/F) of the days:")
    print(f"  {'model':<10}{'scope':<10}{'P range':<12}{'n':>5}{'QLD d1 bp':>10}{'t':>6}{'label':>7}{'| fwd20 QQQ %':>13}")
    for m in ('bucket', 'all-L2', 'noGap-L2', 'fwd-sel'):
        PM = {r_['d']: p for r_, p in zip(R, OOF[m])}
        for sc, cond in (('gated', lambda r_: rows[r_['i']]['bp'][bk] < 0.2), ('un-gated', lambda r_: rows[r_['i']]['bp'][bk] >= 0.2)):
            sub = [r_ for r_ in R if cond(r_)]; ps = sorted(PM[r_['d']] for r_ in sub); med_ = ps[len(ps) // 2]
            for lab, c2 in ((f'< med {med_:.2f}', lambda r_: PM[r_['d']] < med_), (f'>= med', lambda r_: PM[r_['d']] >= med_), ('> 0.5', lambda r_: PM[r_['d']] > 0.5)):
                g_ = [r_ for r_ in sub if c2(r_)]
                if len(g_) < 3: print(f"  {m:<10}{sc:<10}{lab:<12}{len(g_):>5}"); continue
                q_ = [rows[r_['i']]['legs'][2] for r_ in g_]; f20 = [x for x in (fwd(rows[r_['i']], 20) for r_ in g_) if x is not None]
                print(f"  {m:<10}{sc:<10}{lab:<12}{len(g_):>5}{mean(q_)*1e4:>10.1f}{tstat(q_):>6.2f}{mean([r_['y'] for r_ in g_]):>7.2f}{mean(f20)*100:>13.2f}")
    EP_D = _EP_SAVE
print("\n  real-rows note: rr is weekly with its own 20/100 overlay on the long QQQ file; a D row gets the daily OOF P at the same d0 when")
print("  that date is a sample D day (n = matched D rows), otherwise the live row.  Real Sharpe is reported, not used for selection.")

# =====================================================================================================================
print("\n" + "=" * 112)
print("7. TODAY'S READING")
print("=" * 112)
last = rows[-1]; iL = len(rows) - 1
print(f"  last proxy row {last['d']}: state {last['state']} eff {last['eff']} fast {fast[last['d']]}; QQQ file last {max(qqq)}; DGS2 last {max(DGS2)} = {DGS2[max(DGS2)]}")
def today_line(key, f, label):
    S = SAMPLES[key]; feats = S['feats']; C = COEF[key]; x = [f[n] for n in feats]
    z = C['beta'][0] + sum(C['beta'][k + 1] * (x[k] - C['mu'][k]) / C['sd'][k] for k in range(len(feats))); p = _sig(z)
    pb = sorted(_sig(bb[0] + sum(bb[k + 1] * (x[k] - C['mu'][k]) / C['sd'][k] for k in range(len(feats)))) for bb in C['boot'])
    contrib = sorted(((C['beta'][k + 1] * (x[k] - C['mu'][k]) / C['sd'][k]), feats[k]) for k in range(len(feats)))
    # bucket / breadth-only for comparison
    ib = feats.index('bp'); cnt = [[0, 0] for _ in range(5)]
    for r_ in S['recs']: b_ = min(4, int(r_['x'][ib] * 5)); cnt[b_][0] += r_['y']; cnt[b_][1] += 1
    pbk = (cnt[min(4, int(f['bp'] * 5))][0] + 0.5) / (cnt[min(4, int(f['bp'] * 5))][1] + 1)
    print(f"  [{key}] {label}: all-L2 P(breakdown) = {p:.3f}  episode-bootstrap 95% [{pb[int(0.025*len(pb))]:.3f}, {pb[int(0.975*len(pb))-1]:.3f}]"
          f" | bucket base rate {pbk:.2f} | largest logit contributions: " + ", ".join(f"{n} {v:+.2f}" for v, n in (contrib[:2] + contrib[-2:])))
for key in KEYS:
    f = features_of(last, iL, 0, SAMPLES[key]['bkey'])
    print(f"  features at {last['d']} (as a hypothetical FIRST D day tomorrow: ldse=0): " + ", ".join(f"{n}={f[n]:.4f}" for n in SAMPLES[key]['feats']))
    today_line(key, f, f"hypothetical D day with {last['d']} features")
# the freshest reading: price-derived features from the full QQQ file (harness QQQ is stale after ds[-1]); breadth from the
# full-file recomputation as in dgate_anatomy section 6; comp pct from the FRED series on cal
_lr = ratio_series(QQEW, qqq); _s60 = diffs(_lr, 60); _p60 = trailing_pct(_s60)
qv_ = [qqq[d] for d in qd]; _r = [None] + [qv_[i] / qv_[i - 1] - 1 for i in range(1, len(qv_))]
def _v(i, n):
    r_ = [x for x in _r[i - n + 1:i + 1] if x is not None]; m = sum(r_) / n; return (sum((x - m) ** 2 for x in r_) / (n - 1)) ** 0.5 * math.sqrt(252)
_V30 = [None if i < 30 else _v(i, 30) for i in range(len(qd))]; _VP = trailing_pct(_V30)
macro = dict(zip(qd, compute_states(qd, qqq)))
dl = max(d for d in qd if d in QQEW and d in cix and _p60[cix[d]] is not None); i = qix[dl]; j = cix[dl]
fL = {'bp': _p60[j], 'bp_sq': (_p60[j] - 0.5) ** 2, 'bp_comp': pct['comp_60'][j], 'gap200': qv_[i] / sma(qv_, i, 200) - 1, 'gap50': qv_[i] / sma(qv_, i, 50) - 1,
      'vol30': _V30[i], 'vol_pct': _VP[i], 'ldse': 0.0, 'ret20': qv_[i] / qv_[i - 20] - 1, 'fast_def': 1.0 if g[dl] in ('D', 'E', 'F') else 0.0,
      'volratio': _v(i, 10) / _V30[i], 'dgs2_60': FDG.at(dl) - FDG.at(qd[i - 60])}
print(f"\n  freshest date with both QQQ and QQEW closes: {dl}: macro state {macro[dl]}, fast {g[dl]}, breadth pct {fL['bp']:.3f} (comp {fL['bp_comp'] if fL['bp_comp'] is not None else float('nan'):.3f})")
print("  features: " + ", ".join(f"{n}={fL[n]:.4f}" for n in FEATS_Q if fL[n] is not None))
for key in KEYS:
    if all(fL[n] is not None for n in SAMPLES[key]['feats']): today_line(key, fL, f"hypothetical D day with {dl} features")
    else: print(f"  [{key}] {dl}: a feature is missing (comp series ends {max(d for d in cal if pct['comp_60'][cix[d]] is not None)}); no reading")
print(f"\nCANDIDATE COUNT this line: 7 model classes x 2 samples, fold-internal hyper-parameters; harness policies 7 models x 5 policies + 3 x 4 gate combinations = 47 cells per sample (reported in full, none selected).")
print(f"Done in {time.time()-T0:.0f}s.")
