"""Research line `e_outcome_explore` (2026-09-19): DESCRIPTIVE study of state-E episodes split by how they END.

State E: QQQ below both its 50d and 200d SMAs while the 50d is still ABOVE the 200d ("breakdown"). An E episode
ends either when price recovers above the 50d (-> D, occasionally straight to A/B/C: the REVERSAL) or when the 50d
crosses below the 200d (-> F: the BREAK). Two earlier studies (e_pair_test.py, de_substate_search.py) found no
rule INSIDE E that separates good from bad E days. This study asks a different, purely descriptive question: do the
BREAK and REVERSAL episodes look different in the other market data available at E ENTRY?

THIS IS EXPLORATION, NOT A CANDIDATE SEARCH. No action rows, no backtest of any rule, no recommendation. n is ~32
episodes total, of which only a handful are breaks, so the honest deliverable is "do the two groups look different
at all", with the multiple-comparison problem stated up front and a permutation check on the max statistic.

Features (each at the E entry session; "approach" = entry value minus the value 10 sessions earlier; "avg3" = mean
over the first 3 E sessions where sensible):
  VIX level / 252-obs percentile / 5-obs change / VIX minus its 20-obs mean; VXN level; VXN-VIX spread
  2y level; 10y-2y slope; 20-session change in 2y and in 10y; 10y-3m slope
  breadth: QQEW/QQQ 60-session log change and its trailing-252 percentile (breadth_tracker verbatim); RSP/SPY same
  price structure: % below 50d and 200d; 50d-200d spread (% of price) and its 20-session change; drawdown from the
  252-session high; 20-session return before entry; 30d realised vol; 10d/30d vol ratio; sessions in A over the
  prior 120; prior state == D; sessions since the last F day; sessions the 50d needs to cross the 200d if price
  flatlines at the entry close (a purely mechanical quantity)
  QQQ/SPY 20-session relative return
Statistics per feature: mean/median by group, difference, Welch t (two-sided p), Mann-Whitney U (normal approx with
tie correction), AUC of the feature as a classifier of BREAK (AUC > 0.5 = higher value -> more likely BREAK).
Multiplicity: Bonferroni threshold; label permutation (2000 shuffles) of the max |AUC-0.5| across all features.
Multivariate: leave-one-episode-out logistic regression (ridge-stabilised Newton) for the best single feature and
for the best two features from different families.

PART II (owner follow-up, same day): the same question INSIDE the episodes, for the survivors at E sessions k = 3, 5, 10:
survivorship and the conditional base rate P(BREAK | still in E at k), the feature set as levels at k and changes since
entry, Mann-Whitney/AUC per feature with a per-k permutation of the max, LOO logistic, forward QQQ returns from k (to exit
and next 20 sessions) by group and their Spearman correlation with the best feature, and one-line paths per episode.

PART III (owner hypothesis, pre-registered 2026-09-20, three candidates): a TIME-IN-STATE rule for E -- C row (100 % SPMO)
for E sessions 1..k then cash, k in {2, 3, 5} -- run on the d_substate_fresh proxy and real-daily harnesses with the D gate,
against the current live E row (100 % cash, baselines asserted) and the constant-E SPMO ladder as exposure-matched control:
full / search / holdout and real figures, deltas, per-episode gains, 2000-draw block bootstrap for the best k, and the raw
ingredient (QQQ and SPMO return over E sessions 1..k by label). Reported, not recommended.

Pure Python (no numpy/scipy in this environment). Research only; nothing in the repo is modified.

Run from the repo root:
    python3 paper-track/e_outcome_explore.py
Log: paper-track/research_notes/e_outcome_explore_run.log
"""
import sys, os, math, csv, bisect, random, statistics, time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)
sys.path.insert(0, 'paper-track')
import state
import long_history_backtest as lhb
import breadth_tracker as bt

LOG_PATH = 'paper-track/research_notes/e_outcome_explore_run.log'
_log_f = open(LOG_PATH, 'w')
def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s); _log_f.write(s + '\n'); _log_f.flush()

REAL_ERA_START = '2015-11-01'
N_PERM = int(os.environ.get('EOE_NPERM', '2000'))
random.seed(20260919)

# ----------------------------------------------------------------------------------------------------------------
# data
# ----------------------------------------------------------------------------------------------------------------
def load_fred(path):
    """FRED csv: observation_date,<SERIES>; '.' = missing. Returns (sorted dates, values)."""
    ds, vs = [], []
    with open(path) as f:
        r = csv.reader(f); hdr = next(r)
        for row in r:
            if len(row) < 2: continue
            try: v = float(row[1])
            except ValueError: continue
            ds.append(row[0]); vs.append(v)
    return ds, vs

class Series:
    """Sorted (dates, values) with as-of lookup and index-offset helpers."""
    def __init__(self, dates, values, name):
        self.d, self.v, self.name = dates, values, name
    def idx_asof(self, date):
        i = bisect.bisect_right(self.d, date) - 1
        return i if i >= 0 else None
    def asof(self, date, back=0):
        i = self.idx_asof(date)
        if i is None or i - back < 0: return None
        return self.v[i - back]
    def pct_window(self, date, n=252):
        i = self.idx_asof(date)
        if i is None or i - n + 1 < 0: return None
        w = self.v[i - n + 1:i + 1]; x = self.v[i]
        lo = sum(1 for y in w if y < x); eq = sum(1 for y in w if y == x)
        return (lo + 0.5 * eq) / n
    def mean_window(self, date, n=20):
        i = self.idx_asof(date)
        if i is None or i - n + 1 < 0: return None
        return sum(self.v[i - n + 1:i + 1]) / n

qqq = lhb.load_px('data/qqq_long_history.csv')
spy = lhb.load_px('data/spy_long_history.csv')
qqew = lhb.load_px('data/QQEW_daily_ext.csv')
rsp = lhb.load_px('data/RSP_daily.csv')
dates = sorted(qqq)
px = [qqq[d] for d in dates]
N = len(dates)
states = state.compute_states(dates, qqq)
didx = {d: i for i, d in enumerate(dates)}

vix = Series(*load_fred('data/vixcls_full.csv'), 'VIX')
vxn = Series(*load_fred('data/vxncls.csv'), 'VXN')
dgs2 = Series(*load_fred('data/dgs2.csv'), 'DGS2')
dgs10 = Series(*load_fred('data/dgs10.csv'), 'DGS10')
dgs3m = Series(*load_fred('data/dgs3mo_full.csv'), 'DGS3MO')

def breadth_maps(a, b):
    common, x = bt.relative_strength_series(dates, a, b)
    p = bt.trailing_pct(x)
    return {d: xx for d, xx in zip(common, x) if xx is not None}, {d: pp for d, pp in zip(common, p) if pp is not None}
qqew_x60, qqew_pct = breadth_maps(qqew, qqq)
rsp_x60, rsp_pct = breadth_maps(rsp, spy)

# QQQ-derived per-session arrays
def sma_arr(v, n):
    out = [None] * len(v); s = 0.0
    for i, x in enumerate(v):
        s += x
        if i >= n: s -= v[i - n]
        if i >= n - 1: out[i] = s / n
    return out
m50 = sma_arr(px, 50); m200 = sma_arr(px, 200)
logret = [None] + [math.log(px[i] / px[i - 1]) for i in range(1, N)]
def realised_vol(i, n):
    w = [r for r in logret[i - n + 1:i + 1] if r is not None]
    if len(w) < n: return None
    return statistics.pstdev(w) * math.sqrt(252) * 100
hi252 = [None] * N
for i in range(N):
    if i >= 251: hi252[i] = max(px[i - 251:i + 1])
spread_pct = [None if (m50[i] is None or m200[i] is None) else (m50[i] - m200[i]) / px[i] * 100 for i in range(N)]

def sessions_to_cross_if_flat(i):
    """Mechanical: hold price at px[i] forever; how many further sessions until SMA50 < SMA200? None if never (cap 300)."""
    if m50[i] is None or m50[i] <= m200[i]: return 0
    v = px[:i + 1]; p = px[i]
    s50 = sum(v[-50:]); s200 = sum(v[-200:])
    for k in range(1, 301):
        # append p, drop oldest of each window
        s50 += p - v[-50 + k - 1] if k <= 50 else 0.0
        s200 += p - v[-200 + k - 1] if k <= 200 else 0.0
        if s50 / 50 < s200 / 200: return k
    return 300

# ----------------------------------------------------------------------------------------------------------------
# episodes
# ----------------------------------------------------------------------------------------------------------------
def enumerate_e_episodes():
    eps = []; i = 0
    while i < N:
        if states[i] == 'E':
            j = i
            while j + 1 < N and states[j + 1] == 'E': j += 1
            exit_state = states[j + 1] if j + 1 < N else None
            prior = states[i - 1] if i > 0 else None
            e = dict(i0=i, i1=j, start=dates[i], end=dates[j], n=j - i + 1, exit=exit_state, prior=prior,
                     ret_in=(px[j] / px[i - 1] - 1) * 100 if i > 0 else None,
                     post20=(px[j + 20] / px[j] - 1) * 100 if j + 20 < N else None,
                     post60=(px[j + 60] / px[j] - 1) * 100 if j + 60 < N else None)
            if exit_state is None: e['label'] = 'ONGOING'
            elif exit_state == 'F': e['label'] = 'BREAK'
            else: e['label'] = 'REVERSAL'
            eps.append(e); i = j + 1
        else: i += 1
    return eps

EPS = [e for e in enumerate_e_episodes() if e['label'] != 'ONGOING']
ONGOING = [e for e in enumerate_e_episodes() if e['label'] == 'ONGOING']

# ----------------------------------------------------------------------------------------------------------------
# features
# ----------------------------------------------------------------------------------------------------------------
# family, name, function(i) -> value or None ; each is a LEVEL feature evaluated at a session index
def f_vix(i): return vix.asof(dates[i])
def f_vix_pct(i): return vix.pct_window(dates[i], 252)
def f_vix_chg5(i):
    a, b = vix.asof(dates[i]), vix.asof(dates[i], back=5); return None if a is None or b is None else a - b
def f_vix_minus_m20(i):
    a, m = vix.asof(dates[i]), vix.mean_window(dates[i], 20); return None if a is None or m is None else a - m
def f_vxn(i):
    return vxn.asof(dates[i]) if vxn.idx_asof(dates[i]) is not None else None
def f_vxn_minus_vix(i):
    a, b = f_vxn(i), f_vix(i); return None if a is None or b is None else a - b
def f_2y(i): return dgs2.asof(dates[i])
def f_10y2y(i):
    a, b = dgs10.asof(dates[i]), dgs2.asof(dates[i]); return None if a is None or b is None else a - b
def f_10y3m(i):
    a, b = dgs10.asof(dates[i]), dgs3m.asof(dates[i]); return None if a is None or b is None else a - b
def f_2y_chg20(i):
    a, b = dgs2.asof(dates[i]), dgs2.asof(dates[i - 20]); return None if a is None or b is None else a - b
def f_10y_chg20(i):
    a, b = dgs10.asof(dates[i]), dgs10.asof(dates[i - 20]); return None if a is None or b is None else a - b
def f_br_x60(i): return qqew_x60.get(dates[i])
def f_br_pct(i): return qqew_pct.get(dates[i])
def f_rsp_x60(i): return rsp_x60.get(dates[i])
def f_rsp_pct(i): return rsp_pct.get(dates[i])
def f_below50(i): return (px[i] / m50[i] - 1) * 100 if m50[i] else None
def f_below200(i): return (px[i] / m200[i] - 1) * 100 if m200[i] else None
def f_spread(i): return spread_pct[i]
def f_spread_chg20(i):
    return None if spread_pct[i] is None or spread_pct[i - 20] is None else spread_pct[i] - spread_pct[i - 20]
def f_dd252(i): return (px[i] / hi252[i] - 1) * 100 if hi252[i] else None
def f_ret20(i): return (px[i] / px[i - 20] - 1) * 100 if i >= 20 else None
def f_vol30(i): return realised_vol(i, 30)
def f_volratio(i):
    a, b = realised_vol(i, 10), realised_vol(i, 30); return None if a is None or b is None or b == 0 else a / b
def f_a_days120(i): return sum(1 for s in states[max(0, i - 120):i] if s == 'A')
def f_since_f(i):
    k = i - 1
    while k >= 0 and states[k] != 'F': k -= 1
    return i - k if k >= 0 else None
def f_flat_cross(i): return sessions_to_cross_if_flat(i)
def f_qqq_spy_rel20(i):
    d0, d1 = dates[i - 20], dates[i]
    if d0 not in spy or d1 not in spy: return None
    return ((px[i] / px[i - 20]) / (spy[d1] / spy[d0]) - 1) * 100

LEVELS = [
    # family, short name, fn, approach?, avg3?
    ('vol_implied', 'VIX', f_vix, True, True),
    ('vol_implied', 'VIX_pct252', f_vix_pct, False, True),
    ('vol_implied', 'VIX_chg5', f_vix_chg5, False, False),
    ('vol_implied', 'VIX_minus_m20', f_vix_minus_m20, False, True),
    ('vol_implied', 'VXN', f_vxn, True, True),
    ('vol_implied', 'VXN_minus_VIX', f_vxn_minus_vix, True, True),
    ('rates', 'DGS2', f_2y, True, False),
    ('rates', 'slope_10y2y', f_10y2y, True, False),
    ('rates', 'slope_10y3m', f_10y3m, True, False),
    ('rates', 'DGS2_chg20', f_2y_chg20, False, False),
    ('rates', 'DGS10_chg20', f_10y_chg20, False, False),
    ('breadth', 'QQEW_x60', f_br_x60, True, True),
    ('breadth', 'QQEW_pct', f_br_pct, True, True),
    ('breadth', 'RSP_x60', f_rsp_x60, True, True),
    ('breadth', 'RSP_pct', f_rsp_pct, True, True),
    ('price', 'below50_pct', f_below50, False, True),
    ('price', 'below200_pct', f_below200, False, True),
    ('spread', 'spread50_200_pct', f_spread, True, True),
    ('spread', 'spread_chg20', f_spread_chg20, False, False),
    ('spread', 'flat_sessions_to_cross', f_flat_cross, False, False),
    ('price', 'dd_from_252hi', f_dd252, True, True),
    ('price', 'ret20_pre', f_ret20, False, False),
    ('realised_vol', 'rvol30', f_vol30, True, True),
    ('realised_vol', 'volratio_10_30', f_volratio, False, True),
    ('regime', 'A_days_prior120', f_a_days120, False, False),
    ('regime', 'since_last_F', f_since_f, False, False),
    ('relative', 'QQQ_SPY_rel20', f_qqq_spy_rel20, False, True),
]

def build_features():
    feats = []  # (family, name, [value per episode or None])
    for fam, name, fn, appr, avg3 in LEVELS:
        feats.append((fam, name + '@entry', [fn(e['i0']) for e in EPS]))
        if appr:
            vals = []
            for e in EPS:
                a, b = fn(e['i0']), fn(e['i0'] - 10)
                vals.append(None if a is None or b is None else a - b)
            feats.append((fam, name + '@approach10', vals))
        if avg3:
            vals = []
            for e in EPS:
                w = [fn(k) for k in range(e['i0'], min(e['i1'], e['i0'] + 2) + 1)]
                w = [x for x in w if x is not None]
                vals.append(sum(w) / len(w) if w else None)
            feats.append((fam, name + '@avg3', vals))
    feats.append(('regime', 'prior_is_D@entry', [1.0 if e['prior'] == 'D' else 0.0 for e in EPS]))
    return feats

# ----------------------------------------------------------------------------------------------------------------
# statistics (pure python)
# ----------------------------------------------------------------------------------------------------------------
def _betacf(a, b, x):
    MAXIT, EPS_, FPMIN = 300, 3e-14, 1e-300
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < FPMIN: d = FPMIN
    d = 1.0 / d; h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d; d = FPMIN if abs(d) < FPMIN else d
        c = 1.0 + aa / c; c = FPMIN if abs(c) < FPMIN else c
        d = 1.0 / d; h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d; d = FPMIN if abs(d) < FPMIN else d
        c = 1.0 + aa / c; c = FPMIN if abs(c) < FPMIN else c
        d = 1.0 / d; de = d * c; h *= de
        if abs(de - 1.0) < EPS_: break
    return h

def betainc(a, b, x):
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    lb = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    if x < (a + 1) / (a + b + 2): return math.exp(lb) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lb) * _betacf(b, a, 1 - x) / b

def t_sf2(t, df):
    """two-sided p for Student t."""
    x = df / (df + t * t)
    return betainc(df / 2, 0.5, x)

def norm_sf2(z): return math.erfc(abs(z) / math.sqrt(2))

def welch(x, y):
    nx, ny = len(x), len(y)
    if nx < 2 or ny < 2: return None, None
    mx, my = statistics.mean(x), statistics.mean(y)
    vx, vy = statistics.variance(x), statistics.variance(y)
    se2 = vx / nx + vy / ny
    if se2 == 0: return 0.0, 1.0
    t = (mx - my) / math.sqrt(se2)
    df = se2 ** 2 / ((vx / nx) ** 2 / (nx - 1) + (vy / ny) ** 2 / (ny - 1))
    return t, t_sf2(t, df)

def mann_whitney(x, y):
    """x = BREAK values, y = REVERSAL values. Returns (AUC = P(x > y) + 0.5 P(=), two-sided p normal approx)."""
    nx, ny = len(x), len(y)
    if nx == 0 or ny == 0: return None, None
    allv = sorted(x + y)
    # ranks with ties
    ranks = {}; i = 0
    tie_groups = []
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1] == allv[i]: j += 1
        r = (i + j) / 2 + 1
        ranks[allv[i]] = r; tie_groups.append(j - i + 1); i = j + 1
    R1 = sum(ranks[v] for v in x)
    U = R1 - nx * (nx + 1) / 2
    auc = U / (nx * ny)
    n = nx + ny
    mu = nx * ny / 2
    tie_term = sum(t ** 3 - t for t in tie_groups) / (n * (n - 1)) if n > 1 else 0
    sig2 = nx * ny / 12 * ((n + 1) - tie_term)
    if sig2 <= 0: return auc, 1.0
    z = (U - mu) / math.sqrt(sig2)
    return auc, norm_sf2(z)

def auc_only(x, y):
    """fast AUC for the permutation loop."""
    nx, ny = len(x), len(y)
    if nx == 0 or ny == 0: return None
    ys = sorted(y); s = 0.0
    for v in x:
        lo = bisect.bisect_left(ys, v); hi = bisect.bisect_right(ys, v)
        s += lo + 0.5 * (hi - lo)
    return s / (nx * ny)

def logistic_fit(X, y, ridge=0.5, iters=50):
    """X: list of feature vectors (standardised), y: 0/1. Returns weights [b0, b1..]. Ridge on slopes only."""
    p = len(X[0]) + 1
    w = [0.0] * p
    rows = [[1.0] + x for x in X]
    for _ in range(iters):
        g = [0.0] * p; H = [[0.0] * p for _ in range(p)]
        for r, t in zip(rows, y):
            z = sum(wi * xi for wi, xi in zip(w, r)); z = max(min(z, 30), -30)
            pr = 1 / (1 + math.exp(-z))
            for a in range(p):
                g[a] += (pr - t) * r[a]
                for b in range(p): H[a][b] += pr * (1 - pr) * r[a] * r[b]
        for a in range(1, p):
            g[a] += ridge * w[a]; H[a][a] += ridge
        # solve H step = g (gaussian elimination)
        A = [H[a][:] + [g[a]] for a in range(p)]
        for c in range(p):
            piv = max(range(c, p), key=lambda r_: abs(A[r_][c]))
            A[c], A[piv] = A[piv], A[c]
            if abs(A[c][c]) < 1e-12: A[c][c] = 1e-12
            for r_ in range(p):
                if r_ != c:
                    f = A[r_][c] / A[c][c]
                    for k in range(c, p + 1): A[r_][k] -= f * A[c][k]
        step = [A[a][p] / A[a][a] for a in range(p)]
        w = [wi - si for wi, si in zip(w, step)]
        if max(abs(s) for s in step) < 1e-8: break
    return w

def loo_auc(cols, labels):
    """cols: list of feature columns (each list over episodes, may contain None). LOO logistic; returns AUC of
    out-of-fold predicted probabilities and the number of episodes used."""
    idx = [k for k in range(len(labels)) if all(c[k] is not None for c in cols)]
    preds, ys = [], []
    for hold in idx:
        train = [k for k in idx if k != hold]
        mus = [statistics.mean([c[k] for k in train]) for c in cols]
        sds = [statistics.pstdev([c[k] for k in train]) or 1.0 for c in cols]
        X = [[(c[k] - mu) / sd for c, mu, sd in zip(cols, mus, sds)] for k in train]
        w = logistic_fit(X, [labels[k] for k in train])
        xh = [1.0] + [(c[hold] - mu) / sd for c, mu, sd in zip(cols, mus, sds)]
        z = sum(a * b for a, b in zip(w, xh))
        preds.append(1 / (1 + math.exp(-max(min(z, 30), -30)))); ys.append(labels[hold])
    xb = [p for p, t in zip(preds, ys) if t == 1]; yr = [p for p, t in zip(preds, ys) if t == 0]
    return auc_only(xb, yr), len(idx)

def insample_auc(cols, labels):
    idx = [k for k in range(len(labels)) if all(c[k] is not None for c in cols)]
    mus = [statistics.mean([c[k] for k in idx]) for c in cols]
    sds = [statistics.pstdev([c[k] for k in idx]) or 1.0 for c in cols]
    X = [[(c[k] - mu) / sd for c, mu, sd in zip(cols, mus, sds)] for k in idx]
    w = logistic_fit(X, [labels[k] for k in idx])
    pr = [sum(a * b for a, b in zip(w, [1.0] + x)) for x in X]
    xb = [p for p, k in zip(pr, idx) if labels[k] == 1]; yr = [p for p, k in zip(pr, idx) if labels[k] == 0]
    return auc_only(xb, yr), w

def pearson(a, b):
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if len(pairs) < 3: return None
    xs, ys = zip(*pairs)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sx, sy = statistics.pstdev(xs), statistics.pstdev(ys)
    if sx == 0 or sy == 0: return None
    return sum((x - mx) * (y - my) for x, y in pairs) / (len(pairs) * sx * sy)

def fmt(v, w=8, p=2):
    return f"{'--':>{w}}" if v is None else f"{v:>{w}.{p}f}"

# ----------------------------------------------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------------------------------------------
def main():
    log('e_outcome_explore -- state-E episodes split by exit (BREAK -> F vs REVERSAL -> D/A/B/C). DESCRIPTIVE ONLY.')
    log(f'QQQ closes {dates[0]}..{dates[-1]} ({N} sessions); states via state.compute_states (50/200, 1% buffer).')
    log(f'Coverage: VIX {vix.d[0]}..{vix.d[-1]}; VXN {vxn.d[0]}..; DGS2 {dgs2.d[0]}..; DGS10 {dgs10.d[0]}..; DGS3MO {dgs3m.d[0]}..; '
        f'QQEW breadth pct from {min(qqew_pct)}; RSP/SPY breadth pct from {min(rsp_pct)}; SPY {min(spy)}..{max(spy)}')

    # ---- 1 episodes ---------------------------------------------------------------------------------------------
    nb = sum(1 for e in EPS if e['label'] == 'BREAK'); nr = sum(1 for e in EPS if e['label'] == 'REVERSAL')
    log(f"\n{'='*118}\n1. E EPISODES: {len(EPS)} completed (+{len(ONGOING)} ongoing): BREAK {nb}, REVERSAL {nr}\n{'='*118}")
    log(f"  # start      end          n  prior exit  label     ret_in  post20  post60   VIX  brPct  spread%  flatX")
    for k, e in enumerate(EPS):
        i0 = e['i0']
        log(f" {k:2d} {e['start']} {e['end']} {e['n']:3d}   {e['prior']}    {e['exit']}   {e['label']:<8}"
            f" {fmt(e['ret_in'],7,1)} {fmt(e['post20'],7,1)} {fmt(e['post60'],7,1)} {fmt(f_vix(i0),5,1)} {fmt(f_br_pct(i0),6,2)}"
            f" {fmt(f_spread(i0),8,2)} {fmt(f_flat_cross(i0),6,0)}")
    for e in ONGOING:
        log(f"    ONGOING: {e['start']}..{e['end']} ({e['n']} sessions) -- excluded")
    exits = {}
    for e in EPS: exits[e['exit']] = exits.get(e['exit'], 0) + 1
    log(f"  exit-state counts: {exits}")
    priors = {}
    for e in EPS: priors[e['prior']] = priors.get(e['prior'], 0) + 1
    log(f"  prior-state counts: {priors}")
    for lab in ('BREAK', 'REVERSAL'):
        g = [e for e in EPS if e['label'] == lab]
        for key in ('n', 'ret_in', 'post20', 'post60'):
            v = [e[key] for e in g if e[key] is not None]
            log(f"  {lab:<8} {key:<7} n={len(v):2d} mean {statistics.mean(v):7.2f} median {statistics.median(v):7.2f}"
                f"  min {min(v):7.2f} max {max(v):7.2f}")
    real = [e for e in EPS if e['start'] >= REAL_ERA_START]
    log(f"  Real-instrument era ({REAL_ERA_START}+): {len(real)} episodes: BREAK {sum(1 for e in real if e['label']=='BREAK')}, "
        f"REVERSAL {sum(1 for e in real if e['label']=='REVERSAL')}: "
        + ', '.join(f"{e['start']}({e['label'][0]})" for e in real))
    # post-exit return conditional on label (what the label is worth if one knew it)
    log("  Note: post20/post60 are QQQ returns from the E exit close; for BREAKs the exit day is the first F day.")

    labels = [1 if e['label'] == 'BREAK' else 0 for e in EPS]

    # ---- 2 feature table -----------------------------------------------------------------------------------------
    feats = build_features()
    log(f"\n{'='*118}\n2. FEATURES: {len(feats)} feature columns from {len(LEVELS)} base quantities x (entry / approach10 / avg3)\n{'='*118}")
    # power statement
    log(f"  n = {len(EPS)} ({nb} BREAK / {nr} REVERSAL). With nb={nb}, nr={nr} the SE of an AUC near 0.5 is about "
        f"{math.sqrt((nb+nr+1)/(12*nb*nr)):.3f}, so the 5% two-sided minimum detectable |AUC-0.5| for a SINGLE pre-specified "
        f"feature is about {1.96*math.sqrt((nb+nr+1)/(12*nb*nr)):.2f} (AUC about {0.5+1.96*math.sqrt((nb+nr+1)/(12*nb*nr)):.2f}), "
        f"and Cohen's d needs to be about {2.8*math.sqrt(1/nb+1/nr):.2f} for 80% power at alpha 5%.")
    log(f"  Bonferroni threshold for {len(feats)} features at family-wise 5%: p < {0.05/len(feats):.5f}. With {len(feats)} correlated "
        f"features the max |AUC-0.5| under the null is expected to exceed 0.2; see the permutation in section 3.")
    rows = []
    for fam, name, vals in feats:
        xb = [v for v, l in zip(vals, labels) if l == 1 and v is not None]
        yr = [v for v, l in zip(vals, labels) if l == 0 and v is not None]
        if len(xb) < 2 or len(yr) < 2:
            rows.append((fam, name, len(xb), len(yr), None, None, None, None, None, None, None, None)); continue
        t, pt = welch(xb, yr); auc, pu = mann_whitney(xb, yr)
        rows.append((fam, name, len(xb), len(yr), statistics.mean(xb), statistics.median(xb), statistics.mean(yr),
                     statistics.median(yr), t, pt, pu, auc))
    rows.sort(key=lambda r: -(abs(r[11] - 0.5) if r[11] is not None else -1))
    log(f"  {'feature':<32} {'fam':<13} nB nR  {'meanB':>8} {'medB':>8} {'meanR':>8} {'medR':>8} {'diff':>8} {'Welch t':>8} {'p_t':>7} {'p_MW':>7} {'AUC':>6}")
    for r in rows:
        fam, name, nbx, nry, mb, mdb, mr, mdr, t, pt, pu, auc = r
        if auc is None:
            log(f"  {name:<32} {fam:<13} {nbx:2d} {nry:2d}   (insufficient coverage)"); continue
        log(f"  {name:<32} {fam:<13} {nbx:2d} {nry:2d}  {fmt(mb,8,3)} {fmt(mdb,8,3)} {fmt(mr,8,3)} {fmt(mdr,8,3)} {fmt(mb-mr,8,3)}"
            f" {fmt(t,8,2)} {fmt(pt,7,3)} {fmt(pu,7,3)} {fmt(auc,6,3)}")
    valid = [r for r in rows if r[11] is not None]
    n_p05_t = sum(1 for r in valid if r[9] < 0.05); n_p05_u = sum(1 for r in valid if r[10] < 0.05)
    n_bonf = sum(1 for r in valid if min(r[9], r[10]) < 0.05 / len(feats))
    log(f"  features with p_t<0.05: {n_p05_t}/{len(valid)}; p_MW<0.05: {n_p05_u}/{len(valid)}; under Bonferroni ({0.05/len(feats):.5f}): {n_bonf}; "
        f"expected false positives at 5% if all null and independent: {0.05*len(valid):.1f}")
    log(f"  features with |AUC-0.5| > 0.20: {sum(1 for r in valid if abs(r[11]-0.5) > 0.2)}; > 0.25: {sum(1 for r in valid if abs(r[11]-0.5) > 0.25)}")

    # real-era subset for top features
    log(f"\n  Real-era subset ({REAL_ERA_START}+), AUC of the top-10 full-history features on the subset (n={len(real)}):")
    real_idx = [k for k, e in enumerate(EPS) if e['start'] >= REAL_ERA_START]
    fmap = {name: vals for fam, name, vals in feats}
    for r in rows[:10]:
        vals = fmap[r[1]]
        xb = [vals[k] for k in real_idx if labels[k] == 1 and vals[k] is not None]
        yr = [vals[k] for k in real_idx if labels[k] == 0 and vals[k] is not None]
        a = auc_only(xb, yr)
        log(f"    {r[1]:<32} full AUC {r[11]:.3f} -> real-era AUC {fmt(a,6,3)} (nB={len(xb)}, nR={len(yr)})")

    # ---- 2b in-episode contamination check for avg3 -----------------------------------------------------------------
    log(f"\n  CAVEAT on @avg3 features: they average sessions 1-3 of the episode, so they contain the price PATH inside E (and are")
    log(f"  truncated for 1-2 session episodes). They are NOT available at entry. Checks:")
    sb = sum(1 for e in EPS if e['n'] < 3 and e['label'] == 'BREAK'); sr = sum(1 for e in EPS if e['n'] < 3 and e['label'] == 'REVERSAL')
    log(f"    episodes shorter than 3 sessions: {sb + sr} ({sb} BREAK, {sr} REVERSAL)")
    # (i) restrict to n>=3
    idx3 = [k for k, e in enumerate(EPS) if e['n'] >= 3]
    for nm in ('below200_pct@avg3', 'below200_pct@entry', 'dd_from_252hi@avg3'):
        vals = fmap[nm]
        xb = [vals[k] for k in idx3 if labels[k] == 1 and vals[k] is not None]
        yr = [vals[k] for k in idx3 if labels[k] == 0 and vals[k] is not None]
        a, pu = mann_whitney(xb, yr)
        log(f"    {nm:<28} on episodes with n>=3 only: AUC {a:.3f} p_MW {pu:.3f} (nB={len(xb)}, nR={len(yr)})")
    # (ii) the raw QQQ return over sessions 1..3 of the episode (entry close vs close 2 sessions later, capped at the end)
    path3 = [(px[min(e['i1'], e['i0'] + 2)] / px[e['i0']] - 1) * 100 for e in EPS]
    xb = [v for v, l in zip(path3, labels) if l]; yr = [v for v, l in zip(path3, labels) if not l]
    a, pu = mann_whitney(xb, yr)
    log(f"    QQQ return from entry close to session 3 of E: BREAK mean {statistics.mean(xb):.2f}% median {statistics.median(xb):.2f}% | "
        f"REVERSAL mean {statistics.mean(yr):.2f}% median {statistics.median(yr):.2f}% | AUC {a:.3f} p_MW {pu:.3f}")
    xb3 = [v for v, l, k in zip(path3, labels, range(len(EPS))) if l and k in idx3]; yr3 = [v for v, l, k in zip(path3, labels, range(len(EPS))) if not l and k in idx3]
    a3, pu3 = mann_whitney(xb3, yr3)
    log(f"    same, n>=3 episodes only: AUC {a3:.3f} p_MW {pu3:.3f} (nB={len(xb3)}, nR={len(yr3)})")
    # (iii) below-200 depth on session 3 alone
    d3 = [f_below200(min(e['i1'], e['i0'] + 2)) for e in EPS]
    xb = [d3[k] for k in idx3 if labels[k] == 1]; yr = [d3[k] for k in idx3 if labels[k] == 0]
    a, pu = mann_whitney(xb, yr)
    log(f"    below200_pct on session 3 alone, n>=3 episodes: BREAK median {statistics.median(xb):.2f}% REVERSAL median {statistics.median(yr):.2f}% AUC {a:.3f} p_MW {pu:.3f}")

    # ---- 3 permutation ----------------------------------------------------------------------------------------------
    log(f"\n{'='*118}\n3. PERMUTATION: shuffle the {len(EPS)} labels {N_PERM}x, max |AUC-0.5| over all {len(valid)} features\n{'='*118}")
    real_max_row = max(valid, key=lambda r: abs(r[11] - 0.5))
    real_max = abs(real_max_row[11] - 0.5)
    cols = [(name, vals) for fam, name, vals in feats]
    maxes = []; n_over_02 = 0
    for _ in range(N_PERM):
        perm = labels[:]; random.shuffle(perm)
        m = 0.0
        for name, vals in cols:
            xb = [v for v, l in zip(vals, perm) if l == 1 and v is not None]
            yr = [v for v, l in zip(vals, perm) if l == 0 and v is not None]
            if len(xb) < 2 or len(yr) < 2: continue
            a = auc_only(xb, yr)
            if abs(a - 0.5) > m: m = abs(a - 0.5)
        maxes.append(m)
        if m > 0.2: n_over_02 += 1
    maxes.sort()
    q = lambda p: maxes[min(len(maxes) - 1, int(p * len(maxes)))]
    p_perm = sum(1 for m in maxes if m >= real_max) / len(maxes)
    log(f"  real max |AUC-0.5| = {real_max:.3f} ({real_max_row[1]}, AUC {real_max_row[11]:.3f})")
    log(f"  null max |AUC-0.5|: median {q(0.5):.3f}, 90th {q(0.9):.3f}, 95th {q(0.95):.3f}, 99th {q(0.99):.3f}; "
        f"share of shuffles with max > 0.20: {n_over_02/len(maxes):.3f}")
    log(f"  permutation p (share of shuffles whose max >= real max) = {p_perm:.3f}")
    # permutation restricted to PRE-ENTRY information (entry + approach10, no avg3)
    pre_cols = [(name, vals) for name, vals in cols if '@avg3' not in name]
    pre_valid = [r for r in valid if '@avg3' not in r[1]]
    pre_max_row = max(pre_valid, key=lambda r: abs(r[11] - 0.5)); pre_max = abs(pre_max_row[11] - 0.5)
    maxes2 = []
    for _ in range(N_PERM):
        perm = labels[:]; random.shuffle(perm); m = 0.0
        for name, vals in pre_cols:
            xb = [v for v, l in zip(vals, perm) if l == 1 and v is not None]
            yr = [v for v, l in zip(vals, perm) if l == 0 and v is not None]
            if len(xb) < 2 or len(yr) < 2: continue
            a = auc_only(xb, yr)
            if abs(a - 0.5) > m: m = abs(a - 0.5)
        maxes2.append(m)
    maxes2.sort()
    q2 = lambda p: maxes2[min(len(maxes2) - 1, int(p * len(maxes2)))]
    log(f"  PRE-ENTRY features only ({len(pre_valid)} columns: @entry and @approach10): real max |AUC-0.5| = {pre_max:.3f} "
        f"({pre_max_row[1]}, AUC {pre_max_row[11]:.3f}, nB={pre_max_row[2]}, nR={pre_max_row[3]})")
    log(f"    null max: median {q2(0.5):.3f}, 90th {q2(0.9):.3f}, 95th {q2(0.95):.3f}, 99th {q2(0.99):.3f}; "
        f"permutation p = {sum(1 for m in maxes2 if m >= pre_max)/len(maxes2):.3f}")
    # also: permutation for the count of features with p_MW < 0.05 (a "how many nominal hits" check)
    cnt_null = []
    for _ in range(min(N_PERM, 500)):
        perm = labels[:]; random.shuffle(perm); c = 0
        for name, vals in cols:
            xb = [v for v, l in zip(vals, perm) if l == 1 and v is not None]
            yr = [v for v, l in zip(vals, perm) if l == 0 and v is not None]
            if len(xb) < 2 or len(yr) < 2: continue
            a, pu = mann_whitney(xb, yr)
            if pu < 0.05: c += 1
        cnt_null.append(c)
    cnt_null.sort()
    log(f"  count of features with p_MW<0.05: real {n_p05_u}; null (500 shuffles) median {cnt_null[len(cnt_null)//2]}, "
        f"95th {cnt_null[int(0.95*len(cnt_null))]}, p = {sum(1 for c in cnt_null if c >= n_p05_u)/len(cnt_null):.3f}")

    # ---- 4 LOO logistic ------------------------------------------------------------------------------------------------
    log(f"\n{'='*118}\n4. LEAVE-ONE-EPISODE-OUT LOGISTIC (ridge 0.5 on standardised slopes)\n{'='*118}")
    # best single = top |AUC-0.5| with full coverage preferred; pair = top + best from a different family with |corr|<0.6
    full_cov = [r for r in valid if r[2] + r[3] == len(EPS)]
    best = full_cov[0] if full_cov else valid[0]
    second = None
    for r in valid:
        if r[0] == best[0] or r[1] == best[1]: continue
        if r[2] + r[3] < len(EPS): continue
        c = pearson(fmap[best[1]], fmap[r[1]])
        if c is not None and abs(c) < 0.6:
            second = r; break
    log(f"  best single (full coverage): {best[1]} (AUC {best[11]:.3f}, p_MW {best[10]:.3f})")
    log(f"  second (different family, full coverage, |corr| with best < 0.6): {second[1]} (AUC {second[11]:.3f}, p_MW {second[10]:.3f}); "
        f"corr = {pearson(fmap[best[1]], fmap[second[1]]):.2f}")
    for desc, colset in (('single: ' + best[1], [fmap[best[1]]]),
                         ('single: ' + second[1], [fmap[second[1]]]),
                         ('pair: ' + best[1] + ' + ' + second[1], [fmap[best[1]], fmap[second[1]]])):
        ins, w = insample_auc(colset, labels)
        loo, nn = loo_auc(colset, labels)
        log(f"  {desc:<70} in-sample AUC {ins:.3f}  LOO AUC {loo:.3f}  (n={nn}; weights {['%.2f' % x for x in w]})")
    # best PRE-ENTRY single and pair (no avg3)
    pre_full = [r for r in valid if '@avg3' not in r[1] and r[2] + r[3] == len(EPS)]
    pb = pre_full[0]; ps = None
    for r in pre_full[1:]:
        if r[0] == pb[0]: continue
        c = pearson(fmap[pb[1]], fmap[r[1]])
        if c is not None and abs(c) < 0.6: ps = r; break
    log(f"  best PRE-ENTRY single with full coverage: {pb[1]} (AUC {pb[11]:.3f}); second: {ps[1]} (AUC {ps[11]:.3f}); corr {pearson(fmap[pb[1]], fmap[ps[1]]):.2f}")
    for desc, colset in (('pre-entry single: ' + pb[1], [fmap[pb[1]]]),
                         ('pre-entry pair: ' + pb[1] + ' + ' + ps[1], [fmap[pb[1]], fmap[ps[1]]])):
        ins, w = insample_auc(colset, labels); loo, nn = loo_auc(colset, labels)
        log(f"  {desc:<70} in-sample AUC {ins:.3f}  LOO AUC {loo:.3f}  (n={nn}; weights {['%.2f' % x for x in w]})")
    # breadth approach (covers 22 episodes)
    ins, w = insample_auc([fmap['QQEW_pct@approach10']], labels); loo, nn = loo_auc([fmap['QQEW_pct@approach10']], labels)
    log(f"  {'single: QQEW_pct@approach10 (2007-07+ episodes)':<70} in-sample AUC {ins:.3f}  LOO AUC {loo:.3f}  (n={nn})")
    log("  (LOO AUC of a near-null feature can fall far below 0.5: leaving out a positive lowers the fitted intercept for that")
    log("   fold, which is the known negative bias of pooled LOO-AUC. Treat LOO AUCs below 0.5 as 'no signal', not as inverse signal.)")
    # the mechanical baselines for comparison
    for nm in ('spread50_200_pct@entry', 'flat_sessions_to_cross@entry', 'spread_chg20@entry'):
        ins, w = insample_auc([fmap[nm]], labels); loo, nn = loo_auc([fmap[nm]], labels)
        log(f"  {'mechanical single: ' + nm:<70} in-sample AUC {ins:.3f}  LOO AUC {loo:.3f}  (n={nn})")
    # best non-mechanical + spread
    for r in valid:
        if r[0] not in ('spread',) and r[2] + r[3] == len(EPS):
            ins, w = insample_auc([fmap['spread50_200_pct@entry'], fmap[r[1]]], labels)
            loo, nn = loo_auc([fmap['spread50_200_pct@entry'], fmap[r[1]]], labels)
            log(f"  {'pair: spread50_200_pct@entry + ' + r[1]:<70} in-sample AUC {ins:.3f}  LOO AUC {loo:.3f}  (n={nn})")
            break
    # LOO in the real era only, for the best single
    loo_cols = [fmap[best[1]]]
    log(f"  (LOO on the real-era subset alone is not run: {len(real)} episodes with "
        f"{sum(1 for e in real if e['label']=='BREAK')} breaks cannot support a fitted model.)")

    # ---- 5 narrative tables --------------------------------------------------------------------------------------------
    log(f"\n{'='*118}\n5. NARRATIVE TABLES\n{'='*118}")
    def narr(e):
        i0 = e['i0']
        return (f"  {e['start']}..{e['end']} ({e['n']:2d}d, prior {e['prior']}, exit {e['exit']}): VIX {fmt(f_vix(i0),5,1)} "
                f"(pct {fmt(f_vix_pct(i0),4,2)}) VXN {fmt(f_vxn(i0),5,1)} | QQEW pct {fmt(f_br_pct(i0),4,2)} RSP pct {fmt(f_rsp_pct(i0),4,2)} "
                f"| 10y-2y {fmt(f_10y2y(i0),5,2)} | spread {fmt(f_spread(i0),5,2)}% chg20 {fmt(f_spread_chg20(i0),5,2)} flatX {fmt(f_flat_cross(i0),3,0)} "
                f"| dd252 {fmt(f_dd252(i0),5,1)}% ret20 {fmt(f_ret20(i0),5,1)}% rvol30 {fmt(f_vol30(i0),4,0)} A120 {f_a_days120(i0):3d} "
                f"| in-E {fmt(e['ret_in'],5,1)}% then +20d {fmt(e['post20'],5,1)}% +60d {fmt(e['post60'],5,1)}%")
    log(f"  BREAK episodes ({nb}):")
    for e in EPS:
        if e['label'] == 'BREAK': log(narr(e))
    revs = sorted([e for e in EPS if e['label'] == 'REVERSAL' and e['post60'] is not None], key=lambda e: -e['post60'])
    log(f"\n  REVERSAL episodes with the largest post-exit 60-session QQQ gain (top 8 of {nr}):")
    for e in revs[:8]: log(narr(e))
    log(f"\n  REVERSAL episodes with the SMALLEST post-exit 60-session gain (bottom 4, for contrast):")
    for e in revs[-4:]: log(narr(e))

    # ---- 6 mechanical spread ---------------------------------------------------------------------------------------------
    log(f"\n{'='*118}\n6. THE MECHANICAL SPREAD POINT\n{'='*118}")
    log("  F is DEFINED by the 50d crossing below the 200d. So the 50d-200d spread at E entry, and the rate at which it is")
    log("  closing, are near-tautological predictors of BREAK: a narrow, shrinking spread simply needs fewer down sessions to cross.")
    for lab in ('BREAK', 'REVERSAL'):
        g = [e for e in EPS if e['label'] == lab]
        sp = [f_spread(e['i0']) for e in g]; ch = [f_spread_chg20(e['i0']) for e in g]; fx = [f_flat_cross(e['i0']) for e in g]
        ln = [e['n'] for e in g]
        log(f"  {lab:<8} n={len(g):2d}  spread% at entry: mean {statistics.mean(sp):5.2f} median {statistics.median(sp):5.2f} "
            f"min {min(sp):5.2f} max {max(sp):5.2f} | 20-session spread change: mean {statistics.mean(ch):5.2f} median {statistics.median(ch):5.2f} "
            f"| flat-price sessions to cross: median {statistics.median(fx):4.0f} (min {min(fx)}, max {max(fx)}) | episode length median {statistics.median(ln):4.0f}")
    log("  Per BREAK episode: spread at entry, sessions to cross if price flatlined at the entry close, actual E length, and the")
    log("  spread's own approach rate (20-session change / 20) -> sessions to close at that rate:")
    for e in EPS:
        if e['label'] != 'BREAK': continue
        i0 = e['i0']; sp = f_spread(i0); ch = f_spread_chg20(i0)
        rate = -ch / 20 if ch is not None and ch < 0 else None
        est = sp / rate if rate else None
        log(f"    {e['start']} spread {sp:5.2f}%  flat-cross {f_flat_cross(i0):3d}  actual {e['n']:3d}  approach rate {fmt(rate,6,3)}%/session -> "
            f"{fmt(est,6,1)} sessions at that rate")
    # how much does the spread explain: AUC and a simple threshold split
    sp_all = [f_spread(e['i0']) for e in EPS]
    a, pu = mann_whitney([s for s, l in zip(sp_all, labels) if l], [s for s, l in zip(sp_all, labels) if not l])
    fx_all = [f_flat_cross(e['i0']) for e in EPS]
    a2, pu2 = mann_whitney([s for s, l in zip(fx_all, labels) if l], [s for s, l in zip(fx_all, labels) if not l])
    log(f"  spread@entry AUC for BREAK = {a:.3f} (p_MW {pu:.3f}) -- AUC < 0.5 means NARROWER spread -> more BREAKs; "
        f"flat-cross sessions AUC = {a2:.3f} (p_MW {pu2:.3f})")
    med = statistics.median(sp_all)
    lo = [l for s, l in zip(sp_all, labels) if s <= med]; hi = [l for s, l in zip(sp_all, labels) if s > med]
    log(f"  split at the median spread ({med:.2f}%): spread <= median -> {sum(lo)}/{len(lo)} BREAK ({sum(lo)/len(lo):.0%}); "
        f"spread > median -> {sum(hi)}/{len(hi)} BREAK ({sum(hi)/len(hi):.0%})")
    for thr in (2.0, 3.0, 4.0, 5.0):
        lo = [l for s, l in zip(sp_all, labels) if s <= thr]; hi = [l for s, l in zip(sp_all, labels) if s > thr]
        log(f"  spread <= {thr:.0f}%: {sum(lo)}/{len(lo)} BREAK; spread > {thr:.0f}%: {sum(hi)}/{len(hi)} BREAK")
    for thr in (20, 40, 60):
        lo = [l for s, l in zip(fx_all, labels) if s <= thr]; hi = [l for s, l in zip(fx_all, labels) if s > thr]
        log(f"  flat-cross <= {thr} sessions: {sum(lo)}/{len(lo)} BREAK; > {thr}: {sum(hi)}/{len(hi)} BREAK")
    # does anything non-mechanical add to the spread? partial check: rank-correlate top non-spread features with spread
    log("  Correlation (Pearson, over episodes) of the top non-spread features with spread@entry -- a feature that merely")
    log("  tracks the spread adds nothing beyond the mechanical point:")
    k = 0
    for r in valid:
        if r[0] == 'spread': continue
        c = pearson(fmap[r[1]], fmap['spread50_200_pct@entry'])
        log(f"    {r[1]:<32} AUC {r[11]:.3f}  corr with spread {fmt(c,6,2)}")
        k += 1
        if k >= 8: break

    log(f"\n{'='*118}\n7. WHAT THIS DOES AND DOES NOT IMPLY -- see the note. No rule is proposed; n = {len(EPS)} ({nb} breaks) is the binding constraint.\n{'='*118}")


# ----------------------------------------------------------------------------------------------------------------
# PART II (owner follow-up, 2026-09-19): inside the episodes, at E sessions k = 3, 5, 10
# ----------------------------------------------------------------------------------------------------------------
CHECKPOINTS = (3, 5, 10)

def spearman(x, y):
    """Spearman rho with a t-approximation two-sided p. Pairs with None dropped."""
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    n = len(pairs)
    if n < 4: return None, None, n
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
        while i < len(v):
            j = i
            while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]: j += 1
            for t in range(i, j + 1): r[order[t]] = (i + j) / 2 + 1
            i = j + 1
        return r
    rx, ry = ranks([a for a, b in pairs]), ranks([b for a, b in pairs])
    rho = pearson(rx, ry)
    if rho is None: return None, None, n
    if abs(rho) >= 1: return rho, 0.0, n
    t = rho * math.sqrt((n - 2) / (1 - rho * rho))
    return rho, t_sf2(t, n - 2), n

def k_features(k):
    """Feature columns for survivors at session k (index i0+k-1): levels at k and changes entry->k. Returns
    (list of (family, name, [value per survivor])), survivors list."""
    surv = [e for e in EPS if e['n'] >= k]
    cols = []
    def add(fam, name, fn):
        cols.append((fam, name, [fn(e) for e in surv]))
    def lvl(fn): return lambda e: fn(e['i0'] + k - 1)
    def chg(fn):
        def g(e):
            a, b = fn(e['i0'] + k - 1), fn(e['i0']); return None if a is None or b is None else a - b
        return g
    LV = [('vol_implied', 'VIX', f_vix, True), ('vol_implied', 'VIX_pct252', f_vix_pct, True),
          ('vol_implied', 'VXN', f_vxn, True), ('vol_implied', 'VXN_minus_VIX', f_vxn_minus_vix, True),
          ('rates', 'DGS2', f_2y, True), ('rates', 'DGS10', lambda i: dgs10.asof(dates[i]), True),
          ('rates', 'DGS3MO', lambda i: dgs3m.asof(dates[i]), True), ('rates', 'slope_10y2y', f_10y2y, True),
          ('breadth', 'QQEW_pct', f_br_pct, True), ('breadth', 'QQEW_x60', f_br_x60, True),
          ('breadth', 'RSP_pct', f_rsp_pct, True), ('breadth', 'RSP_x60', f_rsp_x60, True),
          ('price', 'below50_pct', f_below50, False), ('price', 'below200_pct', f_below200, False),
          ('spread', 'spread50_200_pct', f_spread, True), ('price', 'dd_from_252hi', f_dd252, False),
          ('realised_vol', 'rvol30', f_vol30, True), ('realised_vol', 'volratio_10_30', f_volratio, False)]
    for fam, name, fn, do_chg in LV:
        add(fam, name + f'@k{k}', lvl(fn))
        if do_chg: add(fam, name + f'@chg0-{k}', chg(fn))
    add('path', f'QQQ_ret_entry_to_k{k}', lambda e: (px[e['i0'] + k - 1] / px[e['i0']] - 1) * 100)
    add('path', f'QQQ_ret_pre_entry_to_k{k}', lambda e: (px[e['i0'] + k - 1] / px[e['i0'] - 1] - 1) * 100)
    def rel(e):
        d0, d1 = dates[e['i0']], dates[e['i0'] + k - 1]
        if d0 not in spy or d1 not in spy: return None
        return ((px[e['i0'] + k - 1] / px[e['i0']]) / (spy[d1] / spy[d0]) - 1) * 100
    add('relative', f'QQQ_SPY_rel_entry_to_k{k}', rel)
    add('path', f'up_sessions_first_{k}', lambda e: float(sum(1 for j in range(e['i0'], e['i0'] + k) if px[j] > px[j - 1])))
    return cols, surv

def part2():
    log(f"\n\n{'#'*118}\nPART II: INSIDE THE EPISODES -- survivors at E sessions k = {CHECKPOINTS}. DESCRIPTIVE ONLY, no rule proposed.\n{'#'*118}")
    summary = []
    for k in CHECKPOINTS:
        cols, surv = k_features(k)
        lab = [1 if e['label'] == 'BREAK' else 0 for e in surv]
        nb, nr = sum(lab), len(lab) - sum(lab)
        eb = sum(1 for e in EPS if e['n'] < k and e['label'] == 'BREAK'); er = sum(1 for e in EPS if e['n'] < k and e['label'] == 'REVERSAL')
        rs = [e for e in surv if e['start'] >= REAL_ERA_START]; rb = sum(1 for e in rs if e['label'] == 'BREAK')
        log(f"\n{'='*118}\nII.{k}  SESSION k = {k}\n{'='*118}")
        log(f"  1. SURVIVORSHIP: still in E at session {k}: {len(surv)} episodes = {nb} BREAK + {nr} REVERSAL; already ended before session {k}: "
            f"{eb} BREAK + {er} REVERSAL. Base rate P(BREAK | in E at session {k}) = {nb}/{len(surv)} = {nb/len(surv):.2f} "
            f"(unconditional 16/32 = 0.50). Real era: {len(rs)} survivors, {rb} BREAK -> {rb/len(rs) if rs else float('nan'):.2f}.")
        log(f"     Conditioning on survival raises the base rate because REVERSALs are short (median 6.5 sessions vs 16.5): the")
        log(f"     survivors are a selected set, and any 'signal' at k must be read against {nb/len(surv):.2f}, not 0.50.")
        mde = 1.96 * math.sqrt((nb + nr + 1) / (12 * nb * nr)) if nb and nr else None
        log(f"     Minimum detectable |AUC-0.5| for one pre-specified feature at nB={nb}, nR={nr}: about {mde:.2f}.")
        # 2. feature table
        rows = []
        for fam, name, vals in cols:
            xb = [v for v, l in zip(vals, lab) if l and v is not None]; yr = [v for v, l in zip(vals, lab) if not l and v is not None]
            if len(xb) < 2 or len(yr) < 2: continue
            t, pt = welch(xb, yr); auc, pu = mann_whitney(xb, yr)
            rows.append((fam, name, len(xb), len(yr), statistics.mean(xb), statistics.median(xb), statistics.mean(yr), statistics.median(yr), t, pt, pu, auc))
        rows.sort(key=lambda r: -abs(r[11] - 0.5))
        log(f"  2. FEATURES at session {k}: {len(rows)} columns (levels @k{k} and changes @chg0-{k}); Bonferroni p < {0.05/len(rows):.5f}")
        log(f"  {'feature':<34} {'fam':<13} nB nR  {'meanB':>8} {'medB':>8} {'meanR':>8} {'medR':>8} {'diff':>8} {'p_t':>6} {'p_MW':>6} {'AUC':>6}")
        for r in rows:
            fam, name, nbx, nry, mb, mdb, mr, mdr, t, pt, pu, auc = r
            log(f"  {name:<34} {fam:<13} {nbx:2d} {nry:2d}  {fmt(mb,8,3)} {fmt(mdb,8,3)} {fmt(mr,8,3)} {fmt(mdr,8,3)} {fmt(mb-mr,8,3)} {fmt(pt,6,3)} {fmt(pu,6,3)} {fmt(auc,6,3)}")
        n05 = sum(1 for r in rows if r[10] < 0.05); nbf = sum(1 for r in rows if r[10] < 0.05 / len(rows))
        log(f"  p_MW<0.05: {n05}/{len(rows)}; Bonferroni survivors: {nbf}; |AUC-0.5|>0.20: {sum(1 for r in rows if abs(r[11]-0.5)>0.2)}")
        # permutation among survivors
        real_max_row = rows[0]; real_max = abs(real_max_row[11] - 0.5)
        maxes = []
        for _ in range(N_PERM):
            perm = lab[:]; random.shuffle(perm); m = 0.0
            for fam, name, vals in cols:
                xb = [v for v, l in zip(vals, perm) if l and v is not None]; yr = [v for v, l in zip(vals, perm) if not l and v is not None]
                if len(xb) < 2 or len(yr) < 2: continue
                a = abs(auc_only(xb, yr) - 0.5)
                if a > m: m = a
            maxes.append(m)
        maxes.sort(); q = lambda p_: maxes[min(len(maxes) - 1, int(p_ * len(maxes)))]
        p_perm = sum(1 for m in maxes if m >= real_max) / len(maxes)
        # permutation excluding the pure price-path columns
        nonpath = [(f_, n_, v_) for f_, n_, v_ in cols if f_ not in ('path', 'price', 'spread')]
        np_rows = [r for r in rows if r[0] not in ('path', 'price', 'spread')]
        np_max_row = np_rows[0]; np_max = abs(np_max_row[11] - 0.5); maxes2 = []
        for _ in range(N_PERM):
            perm = lab[:]; random.shuffle(perm); m = 0.0
            for fam, name, vals in nonpath:
                xb = [v for v, l in zip(vals, perm) if l and v is not None]; yr = [v for v, l in zip(vals, perm) if not l and v is not None]
                if len(xb) < 2 or len(yr) < 2: continue
                a = abs(auc_only(xb, yr) - 0.5)
                if a > m: m = a
            maxes2.append(m)
        maxes2.sort(); q2 = lambda p_: maxes2[min(len(maxes2) - 1, int(p_ * len(maxes2)))]
        p_perm2 = sum(1 for m in maxes2 if m >= np_max) / len(maxes2)
        log(f"  PERMUTATION ({N_PERM} shuffles of the {len(lab)} survivor labels), all {len(rows)} columns: real max |AUC-0.5| {real_max:.3f} ({real_max_row[1]}, AUC {real_max_row[11]:.3f}); "
            f"null median {q(0.5):.3f} 95th {q(0.95):.3f} 99th {q(0.99):.3f}; p = {p_perm:.3f}")
        log(f"  PERMUTATION, NON-PRICE columns only (implied vol, rates, breadth, realised vol, relative; {len(np_rows)} columns): real max {np_max:.3f} "
            f"({np_max_row[1]}, AUC {np_max_row[11]:.3f}, nB={np_max_row[2]} nR={np_max_row[3]}); null median {q2(0.5):.3f} 95th {q2(0.95):.3f}; p = {p_perm2:.3f}")
        # LOO logistic
        fm = {name: vals for fam, name, vals in cols}
        full = [r for r in rows if r[2] + r[3] == len(surv)]
        best = full[0]; second = None
        for r in full[1:]:
            if r[0] == best[0]: continue
            c = pearson(fm[best[1]], fm[r[1]])
            if c is not None and abs(c) < 0.6: second = r; break
        ins1, w1 = insample_auc([fm[best[1]]], lab); loo1, n1 = loo_auc([fm[best[1]]], lab)
        log(f"  LOO LOGISTIC: best single (full coverage) {best[1]} (AUC {best[11]:.3f}): in-sample {ins1:.3f} LOO {loo1:.3f} (n={n1})")
        loo2 = None
        if second:
            ins2, w2 = insample_auc([fm[best[1]], fm[second[1]]], lab); loo2, n2 = loo_auc([fm[best[1]], fm[second[1]]], lab)
            log(f"                pair {best[1]} + {second[1]} (AUC {second[11]:.3f}, corr {pearson(fm[best[1]], fm[second[1]]):.2f}): in-sample {ins2:.3f} LOO {loo2:.3f} (n={n2})")
        npb = [r for r in np_rows if r[2] + r[3] == len(surv)]
        loo3 = None
        if npb:
            ins3, w3 = insample_auc([fm[npb[0][1]]], lab); loo3, n3 = loo_auc([fm[npb[0][1]]], lab)
            log(f"                best NON-PRICE single with full coverage {npb[0][1]} (AUC {npb[0][11]:.3f}): in-sample {ins3:.3f} LOO {loo3:.3f} (n={n3})")
        # 3. forward returns
        fwd_exit = [(px[e['i1']] / px[e['i0'] + k - 1] - 1) * 100 for e in surv]
        fwd20 = [(px[e['i0'] + k - 1 + 20] / px[e['i0'] + k - 1] - 1) * 100 if e['i0'] + k - 1 + 20 < N else None for e in surv]
        log(f"  3. FORWARD QQQ RETURN from session {k} (survivors):")
        for nm, arr in (('to episode exit', fwd_exit), ('next 20 sessions (regardless of exit)', fwd20)):
            for gname, gl in (('BREAK', 1), ('REVERSAL', 0), ('ALL', None)):
                v = [x for x, l in zip(arr, lab) if x is not None and (gl is None or l == gl)]
                log(f"     {nm:<38} {gname:<8} n={len(v):2d} mean {statistics.mean(v):6.2f}% median {statistics.median(v):6.2f}% "
                    f"min {min(v):6.1f}% max {max(v):6.1f}%  positive {sum(1 for x in v if x > 0)}/{len(v)}")
        rho_e, p_e, n_e = spearman(fm[best[1]], fwd_exit); rho_20, p_20, n_20 = spearman(fm[best[1]], fwd20)
        log(f"     Spearman of {best[1]} with forward return: to exit rho {rho_e:+.3f} (p {p_e:.3f}, n={n_e}); next-20 rho {rho_20:+.3f} (p {p_20:.3f}, n={n_20})")
        rho_np = None
        if npb:
            rho_np, p_np, n_np = spearman(fm[npb[0][1]], fwd20); rho_npe, p_npe, _ = spearman(fm[npb[0][1]], fwd_exit)
            log(f"     Spearman of {npb[0][1]} with forward return: to exit rho {rho_npe:+.3f} (p {p_npe:.3f}); next-20 rho {rho_np:+.3f} (p {p_np:.3f}, n={n_np})")
        # also the path feature vs next-20 (is 'down so far' informative about what comes next?)
        rho_p, p_p, n_p = spearman(fm[f'QQQ_ret_entry_to_k{k}'], fwd20)
        log(f"     Spearman of QQQ_ret_entry_to_k{k} with next-20 return: rho {rho_p:+.3f} (p {p_p:.3f}, n={n_p}); with return to exit: "
            f"rho {spearman(fm[f'QQQ_ret_entry_to_k{k}'], fwd_exit)[0]:+.3f} (p {spearman(fm[f'QQQ_ret_entry_to_k{k}'], fwd_exit)[1]:.3f})")
        summary.append((k, nb, nr, nb / len(surv), best[1], best[11], best[10], p_perm, loo1, rho_e, p_e, rho_20, p_20,
                        np_max_row[1], np_max_row[11], p_perm2, loo3))
    # 4. compact table
    log(f"\n{'='*118}\nII.4  COMPACT TABLE ACROSS k\n{'='*118}")
    log(f"  {'k':>2} {'nB':>3} {'nR':>3} {'P(B)':>5}  {'best feature':<30} {'AUC':>5} {'p_MW':>6} {'perm p':>6} {'LOO':>5} {'rho_exit':>8} {'p':>5} {'rho_20':>7} {'p':>5}  | best non-price {'':<12} {'AUC':>5} {'perm p':>6} {'LOO':>5}")
    for k, nb, nr, br, bn, ba, bp, pp, loo, re_, pe, r20, p20, npn, npa, npp, loo3 in summary:
        log(f"  {k:>2} {nb:>3} {nr:>3} {br:5.2f}  {bn:<30} {ba:5.3f} {bp:6.3f} {pp:6.3f} {loo:5.3f} {re_:+8.3f} {pe:5.3f} {r20:+7.3f} {p20:5.3f}  | {npn:<27} {npa:5.3f} {npp:6.3f} {fmt(loo3,5,3)}")
    # 5. narrative paths
    log(f"\n{'='*118}\nII.5  PATHS: QQQ return from entry close, VIX change, QQEW breadth-pct change and RSP breadth-pct change at sessions 3/5/10 ('--' = episode already over)\n{'='*118}")
    def cell(e, k):
        if e['n'] < k: return f"{'ended':>28}"
        ik = e['i0'] + k - 1
        r = (px[ik] / px[e['i0']] - 1) * 100
        dv = f_vix(ik) - f_vix(e['i0']) if f_vix(ik) is not None and f_vix(e['i0']) is not None else None
        db = None if f_br_pct(ik) is None or f_br_pct(e['i0']) is None else f_br_pct(ik) - f_br_pct(e['i0'])
        dr = None if f_rsp_pct(ik) is None or f_rsp_pct(e['i0']) is None else f_rsp_pct(ik) - f_rsp_pct(e['i0'])
        return f"{r:+5.1f}% V{fmt(dv,5,1)} B{fmt(db,5,2)} R{fmt(dr,5,2)}"
    log(f"  {'episode':<22} {'n':>3} label     {'session 3':^28} | {'session 5':^28} | {'session 10':^28}")
    log("  BREAK episodes:")
    for e in EPS:
        if e['label'] == 'BREAK': log(f"  {e['start']}..{e['end']} {e['n']:3d} {e['label']:<8}  {cell(e,3)} | {cell(e,5)} | {cell(e,10)}")
    log("  REVERSAL episodes that survived to session 10:")
    for e in EPS:
        if e['label'] == 'REVERSAL' and e['n'] >= 10: log(f"  {e['start']}..{e['end']} {e['n']:3d} {e['label']:<8}  {cell(e,3)} | {cell(e,5)} | {cell(e,10)}")
    log("  REVERSAL episodes that ended before session 10 (for the base-rate point):")
    for e in EPS:
        if e['label'] == 'REVERSAL' and e['n'] < 10: log(f"  {e['start']}..{e['end']} {e['n']:3d} {e['label']:<8}  {cell(e,3)} | {cell(e,5)} | {cell(e,10)}")
    log(f"\n{'='*118}\nII.6  No rule proposed. See the note, part II.\n{'='*118}")


# ----------------------------------------------------------------------------------------------------------------
# PART III (owner hypothesis, pre-registered 2026-09-20, THREE candidates only): a TIME-IN-STATE rule for E.
#   hold the C row (100 % SPMO; on the proxy the core leg) for E sessions 1..k, then 100 % cash for the rest of the
#   episode, k in {2, 3, 5}. Baseline = CURRENT live E row (100 % cash) with the D gate applied on D days, built
#   explicitly by E override and asserted to reproduce proxy 25.46 % / 1.071 / -27.0 % and real daily 37.30 % /
#   1.475 / -18.6 % (STRATEGY.md "State E -> 100% cash", e_pair_test ladder rows XLU 0 % / SPMO 0 %). Control = the
#   constant-E SPMO ladder (g x SPMO + (1-g) cash on every E day, 10 % steps), matched by average exposure.
#   Harness: d_substate_fresh (proxy rows, real daily mirror) exactly as e_pair_test used it. No adoption language.
# ----------------------------------------------------------------------------------------------------------------
TIS_KS = (2, 3, 5)

def part3_time_in_state():
    os.environ.setdefault('DSF_STAGE', 'none')
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):                     # the harness prints its standing figures at import
        import d_substate_fresh as DSF
        import monthly_returns as MR
        import block_bootstrap as BB
    from d_substate_fresh import (rows, run, vt, RF, evaluate_full, run_count, real_metrics, RPX, RQQQ, RDAYS, RQD,
                                  SIG_R, RIX, SEARCH, HOLDOUT, bstats, boot, sliced_sharpe)
    from state import (d_gate_active, compute_micro_agreement, compute_fast_states, compute_extension_gaps,
                       realized_vol_live, target_weights_with_voltarget, effective_state, extension_votes,
                       needs_rebalance, REBALANCE_DRIFT_BAND, D_GATE_ENABLED)
    assert D_GATE_ENABLED
    assert BB.N_BOOT == 2000
    log(f"\n\n{'#'*118}\nPART III: TIME-IN-STATE RULE FOR E (owner hypothesis, pre-registered, 3 candidates: k in {TIS_KS}). NOT applied; owner decides.\n{'#'*118}")
    log("  rule(k): E session age <= k -> C row (100 % SPMO; proxy: core leg), age > k -> 100 % cash. Baseline: live E = 100 % cash, D gate on.")
    log("  Control: constant-E SPMO ladder (every E day g x SPMO + (1-g) cash), matched to the rule by average exposure. Harness: d_substate_fresh.")
    for line in buf.getvalue().splitlines():
        if 'harness' in line or 'proxy' in line: log('  [harness] ' + line.strip())

    CASH = (0.0, 0.0, 0.0, 0.0, 1.0); SPMO = (1.0, 0.0, 0.0, 0.0, 0.0)
    # breadth for the D gate, breadth_tracker verbatim (as e_pair_test)
    def breadth_pct(qqq_):
        common, x = bt.relative_strength_series(sorted(qqq_), qqew, qqq_)
        return dict(zip(common, bt.trailing_pct(x)))
    BP_Q = breadth_pct(DSF._QQQ_FULL); BP_R = breadth_pct(RQQQ)
    # ---- proxy: gated baseline with E -> cash
    GATE_Q = set(r['d'] for r in rows if r['state'] == 'D' and d_gate_active(r['state'], BP_Q.get(r['d']), r['gaps'][200]))
    E_ROWS = [i for i, r in enumerate(rows) if r['state'] == 'E']
    E_SET = set(rows[i]['d'] for i in E_ROWS)
    def eps_of(idx):
        out = []; cur = None
        for i in idx:
            if cur is not None and i == cur[1] + 1: cur[1] = i
            else:
                if cur: out.append(tuple(cur))
                cur = [i, i]
        if cur: out.append(tuple(cur))
        return out
    E_EPS_Q = eps_of(E_ROWS)
    AGE_Q = {}
    for a, b in E_EPS_Q:
        for j, i in enumerate(range(a, b + 1)): AGE_Q[rows[i]['d']] = j + 1
    GBASE_CASH = {}
    for r in rows:
        if r['d'] in GATE_Q or r['d'] in E_SET: GBASE_CASH[r['d']] = vt(CASH, r['vol'])
        else: GBASE_CASH[r['d']] = DSF.BASE[r['d']]
    def proxy_eval(row_fn):
        """row_fn(d, age) -> action row on E days; everything else the gated baseline."""
        def fn(r):
            if r['d'] in E_SET: return vt(row_fn(r['d'], AGE_Q[r['d']]), r['vol'])
            return GBASE_CASH[r['d']]
        return evaluate_full(fn)
    LIVE_EV, LIVE_SER = proxy_eval(lambda d, age: CASH)
    # ---- real daily mirror with D gate + E override (copy of e_pair_test.simulate_real_e)
    def simulate_real_e(px, qqq_, days, override_e=None):
        qd = sorted(qqq_)
        states_ = dict(zip(qd, state.compute_states(qd, qqq_)))
        micro = compute_micro_agreement(qd, qqq_)
        fast = compute_fast_states(qd, qqq_); gaps = compute_extension_gaps(qd, qqq_)
        held = prev = None; out = []; risky = 0.0; nreb = 0
        for i in range(1, len(days)):
            d0, d1 = days[i - 1], days[i]
            st, ag = states_[d0], micro[d0]
            gate = d_gate_active(st, BP_R.get(d0), gaps[d0][200])
            vol = realized_vol_live(qd, qqq_, as_of=d0)
            row = override_e(d0) if (override_e is not None and st == 'E') else None
            if row is None:
                t = target_weights_with_voltarget(st, ag, vol, fast_state=fast[d0], gaps=gaps[d0], d_gate=gate)
            else:
                t = RF.vt(row, vol)
            eff = effective_state(st, fast[d0])
            stk = (eff, extension_votes(eff, gaps[d0]), gate, row is not None)
            cost = 0.0
            if held is None:
                held = list(t); nreb += 1
            else:
                do, drift, _ = needs_rebalance(t, held, stk != prev)
                if do:
                    cost = MR.ONE_WAY * drift; held = list(t); nreb += 1
            r = [px[s_][d1] / px[s_][d0] - 1 for s_ in MR.LEGS]
            g = sum(held[j] * r[j] for j in range(5))
            risky += sum(held[:4])
            out.append((d1, stk[0], g - cost))
            dn = 1 + g
            if dn > 0: held = [held[j] * (1 + r[j]) / dn for j in range(5)]
            prev = stk
        n = len(out)
        return out, risky / n, nreb / (n / 252.0)
    RE_IDX = [k for k, d in enumerate(RDAYS[:-1]) if SIG_R['state'][RIX[d]] == 'E']
    RE_EPS = eps_of(RE_IDX)
    AGE_R = {}
    for a, b in RE_EPS:
        for j, k in enumerate(range(a, b + 1)): AGE_R[RDAYS[k]] = j + 1
    def real_eval(row_fn):
        out, exp, reb = simulate_real_e(RPX, RQQQ, RDAYS, lambda d0: row_fn(d0, AGE_R[d0]))
        m, ser = real_metrics(out)
        return dict(m, exp=exp, reb=reb), ser
    # d_substate_fresh pins state.TARGET_WEIGHTS['E'] back to 50 % XLU at import, so MR.simulate here runs the OLD E row:
    # (1) the mirror with no override must equal MR.simulate day by day (mechanics), (2) the E -> cash override is the
    # explicit current-live baseline and must reproduce the standing figure 37.30 % / 1.475 / -18.6 % (asserted below).
    assert state.TARGET_WEIGHTS['E'] == (0.0, 0.0, 0.0, 0.5, 0.5), 'expected d_substate_fresh to have pinned the E row'
    _ref = MR.simulate(RPX, RQQQ, RDAYS)
    _mine, _, _ = simulate_real_e(RPX, RQQQ, RDAYS, None)
    assert len(_ref) == len(_mine) and all(a[0] == b[0] and abs(a[2] - b[2]) < 1e-12 for a, b in zip(_ref, _mine)), \
        'real mirror (no override) does not reproduce monthly_returns.simulate'
    _old = real_metrics(_mine)[0]
    log(f"  (mirror check: no-override real run = monthly_returns.simulate day by day; with the harness-pinned old E row it gives "
        f"{_old['cagr']*100:.2f}% / {_old['sharpe']:.3f} / {_old['mdd']*100:.1f}%, the e_pair_test gated baseline 37.75 / 1.484 / -19.4)")
    RLIVE_EV, RLIVE_SER = real_eval(lambda d, age: CASH)
    def fmt_ev(ev): return f"{ev['cagr']*100:6.2f}% /{ev['sharpe']:6.3f} /{ev['mdd']*100:6.1f}%"
    log(f"\n  BASELINE (live: E = 100 % cash, D gate): proxy {fmt_ev(LIVE_EV)}  S {LIVE_EV['s_sharpe']:.3f} H {LIVE_EV['h_sharpe']:.3f} "
        f"exp {LIVE_EV['risky']*100:.1f}% reb {LIVE_EV['reb']:.1f}/yr | real daily {fmt_ev(RLIVE_EV)} exp {RLIVE_EV['exp']*100:.1f}% reb {RLIVE_EV['reb']:.1f}/yr")
    assert abs(LIVE_EV['cagr'] * 100 - 25.46) < 0.006 and abs(LIVE_EV['sharpe'] - 1.071) < 0.0006 and abs(LIVE_EV['mdd'] * 100 + 27.0) < 0.06, 'proxy baseline != 25.46/1.071/-27.0'
    assert abs(RLIVE_EV['cagr'] * 100 - 37.30) < 0.006 and abs(RLIVE_EV['sharpe'] - 1.475) < 0.0006 and abs(RLIVE_EV['mdd'] * 100 + 18.6) < 0.06, 'real baseline != 37.30/1.475/-18.6'
    log("  both baselines reproduced (asserted).")
    log(f"  proxy: {len(E_ROWS)} E days in {len(E_EPS_Q)} episodes; real daily: {len(RE_IDX)} E days in {len(RE_EPS)} episodes.")

    # ---- raw ingredient: return over E sessions 1..k (held from the close of E session 1 through the close after session min(k, n))
    log(f"\n  RAW INGREDIENT: return earned by holding the risk leg over E sessions 1..min(k, n) (position taken at the close of E session 1,")
    log(f"  each session's return is close-to-next-close, so this is exactly what rule(k) earns on the risk leg). QQQ from qqq_long_history (all 32")
    log(f"  completed episodes, part I labels); SPMO from the real harness (its {len(RE_EPS)} E episodes, 2015-11+). Also the uncapped k-session return (n >= k only).")
    log(f"  {'leg':<5} {'k':>2} {'group':<9} {'n':>3} {'mean%':>7} {'med%':>7} {'pos':>5} | uncapped (n>=k) {'n':>3} {'mean%':>7} {'med%':>7}")
    for k in TIS_KS:
        for gname in ('BREAK', 'REVERSAL', 'ALL'):
            g = [e for e in EPS if gname == 'ALL' or e['label'] == gname]
            capped = [(px[e['i0'] + min(k, e['n'])] / px[e['i0']] - 1) * 100 for e in g]
            unc = [(px[e['i0'] + k] / px[e['i0']] - 1) * 100 for e in g if e['n'] >= k]
            log(f"  {'QQQ':<5} {k:>2} {gname:<9} {len(capped):>3} {statistics.mean(capped):>7.2f} {statistics.median(capped):>7.2f} {sum(1 for x in capped if x > 0):>2}/{len(capped):<2} | "
                f"{'':>16} {len(unc):>3} {fmt(statistics.mean(unc) if unc else None,7,2)} {fmt(statistics.median(unc) if unc else None,7,2)}")
        sp = RPX['SPMO']; rd = RDAYS
        capped = []; unc = []; lab_r = []
        for a, b in RE_EPS:
            n_ = b - a + 1; i_end = min(a + min(k, n_), len(rd) - 1)
            capped.append((sp[rd[i_end]] / sp[rd[a]] - 1) * 100)
            if n_ >= k: unc.append((sp[rd[a + k]] / sp[rd[a]] - 1) * 100)
            # label from the QQQ classifier on the real harness's own dates
            nxt = SIG_R['state'][RIX[rd[b + 1]]] if b + 1 < len(rd) else None
            lab_r.append('BREAK' if nxt == 'F' else 'REVERSAL')
        for gname in ('BREAK', 'REVERSAL', 'ALL'):
            c = [x for x, l in zip(capped, lab_r) if gname == 'ALL' or l == gname]
            log(f"  {'SPMO':<5} {k:>2} {gname:<9} {len(c):>3} {statistics.mean(c):>7.2f} {statistics.median(c):>7.2f} {sum(1 for x in c if x > 0):>2}/{len(c):<2} | "
                + (f"{'':>16} {len(unc):>3} {statistics.mean(unc):>7.2f} {statistics.median(unc):>7.2f}" if gname == 'ALL' else ''))
    log("  (The per-session QQQ mean on E days overall, from part I's daily state series: "
        f"{statistics.mean([(px[i+1]/px[i]-1)*100 for i in range(N-1) if states[i]=='E']):+.3f}%/day over {sum(1 for i in range(N-1) if states[i]=='E')} E days.)")

    # ---- constant-E SPMO ladder (control)
    log(f"\n  CONSTANT-E SPMO LADDER (control; g = 0 is live): proxy full / S / H, real daily")
    log(f"  {'g':>4} | {'CAGR':>7}{'Sharpe':>7}{'MaxDD':>7}{'exp':>6}{'reb':>6}{'S Sh':>7}{'H Sh':>7}{'dS_F':>7} | {'rCAGR':>7}{'rSh':>7}{'rDD':>7}{'rexp':>6}{'rreb':>6}{'rdSh':>7}")
    LAD = []
    for g in range(0, 101, 10):
        row = (g / 100.0, 0.0, 0.0, 0.0, 1 - g / 100.0)
        ev, ser = proxy_eval(lambda d, age, row=row: row); rev, rser = real_eval(lambda d, age, row=row: row)
        LAD.append(dict(g=g, ev=ev, real=rev, ser=ser, rser=rser))
        log(f"  {g:>3}% | {ev['cagr']*100:>6.2f}%{ev['sharpe']:>7.3f}{ev['mdd']*100:>6.1f}%{ev['risky']*100:>5.1f}%{ev['reb']:>6.1f}{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f}{ev['sharpe']-LIVE_EV['sharpe']:>+7.3f} | "
            f"{rev['cagr']*100:>6.2f}%{rev['sharpe']:>7.3f}{rev['mdd']*100:>6.1f}%{rev['exp']*100:>5.1f}%{rev['reb']:>6.1f}{rev['sharpe']-RLIVE_EV['sharpe']:>+7.3f}")
    assert abs(LAD[0]['ev']['sharpe'] - LIVE_EV['sharpe']) < 1e-12 and abs(LAD[0]['real']['sharpe'] - RLIVE_EV['sharpe']) < 1e-12
    def match(exp, key):
        return min(LAD, key=lambda c: abs((c['ev']['risky'] if key == 'ev' else c['real']['exp']) - exp))

    # ---- the three candidates
    log(f"\n  CANDIDATES rule(k): proxy full / search ({SEARCH[0]}+) / holdout, real daily; deltas vs live and vs the exposure-matched SPMO ladder row")
    log(f"  {'k':>2} {'days->SPMO (proxy/real)':<24} | {'CAGR':>7}{'Sharpe':>7}{'MaxDD':>7}{'exp':>6}{'reb':>6} | S {'CAGR':>7}{'Sh':>6}{'DD':>7} | H {'CAGR':>7}{'Sh':>6}{'DD':>7} | {'dS_F':>7}{'dS_S':>7}{'dS_H':>7} {'ctl':>5}{'vC_F':>7}{'vC_S':>7}{'vC_H':>7} | real {'CAGR':>7}{'Sh':>6}{'DD':>7}{'exp':>5}{'reb':>5}{'rdSh':>7}{'rctl':>5}{'rvC':>7}")
    CAND = []
    for k in TIS_KS:
        rf = lambda d, age, k=k: SPMO if age <= k else CASH
        ev, ser = proxy_eval(rf); rev, rser = real_eval(rf)
        nq = sum(1 for d in E_SET if AGE_Q[d] <= k); nr = sum(1 for d in AGE_R if AGE_R[d] <= k)
        c = match(ev['risky'], 'ev'); cr = match(rev['exp'], 'real')
        rec = dict(k=k, ev=ev, real=rev, ser=ser, rser=rser, nq=nq, nr=nr, ctl=c, rctl=cr,
                   dF=ev['sharpe'] - LIVE_EV['sharpe'], dS=ev['s_sharpe'] - LIVE_EV['s_sharpe'], dH=ev['h_sharpe'] - LIVE_EV['h_sharpe'],
                   vCF=ev['sharpe'] - c['ev']['sharpe'], vCS=ev['s_sharpe'] - c['ev']['s_sharpe'], vCH=ev['h_sharpe'] - c['ev']['h_sharpe'],
                   rd=rev['sharpe'] - RLIVE_EV['sharpe'], rvC=rev['sharpe'] - cr['real']['sharpe'])
        CAND.append(rec)
        log(f"  {k:>2} {f'{nq} / {nr}':<24} | {ev['cagr']*100:>6.2f}%{ev['sharpe']:>7.3f}{ev['mdd']*100:>6.1f}%{ev['risky']*100:>5.1f}%{ev['reb']:>6.1f} | "
            f"{ev['s_cagr']*100:>8.2f}%{ev['s_sharpe']:>6.3f}{ev['s_mdd']*100:>6.1f}% | {ev['h_cagr']*100:>8.2f}%{ev['h_sharpe']:>6.3f}{ev['h_mdd']*100:>6.1f}% | "
            f"{rec['dF']:>+7.3f}{rec['dS']:>+7.3f}{rec['dH']:>+7.3f} {str(c['g'])+'%':>5}{rec['vCF']:>+7.3f}{rec['vCS']:>+7.3f}{rec['vCH']:>+7.3f} | "
            f"{rev['cagr']*100:>11.2f}%{rev['sharpe']:>6.3f}{rev['mdd']*100:>6.1f}%{rev['exp']*100:>4.0f}%{rev['reb']:>5.1f}{rec['rd']:>+7.3f}{str(cr['g'])+'%':>5}{rec['rvC']:>+7.3f}")
    log(f"  live for reference: proxy {fmt_ev(LIVE_EV)} S {LIVE_EV['s_sharpe']:.3f} H {LIVE_EV['h_sharpe']:.3f} exp {LIVE_EV['risky']*100:.1f}% reb {LIVE_EV['reb']:.1f} | "
        f"real {fmt_ev(RLIVE_EV)} exp {RLIVE_EV['exp']*100:.1f}% reb {RLIVE_EV['reb']:.1f}")
    log(f"  live CAGR deltas (pp): " + "; ".join(f"k={r['k']}: proxy {(r['ev']['cagr']-LIVE_EV['cagr'])*100:+.2f} (S {(r['ev']['s_cagr']-LIVE_EV['s_cagr'])*100:+.2f}, H {(r['ev']['h_cagr']-LIVE_EV['h_cagr'])*100:+.2f}), "
        f"real {(r['real']['cagr']-RLIVE_EV['cagr'])*100:+.2f}; MaxDD proxy {(r['ev']['mdd']-LIVE_EV['mdd'])*100:+.1f} pp, real {(r['real']['mdd']-RLIVE_EV['mdd'])*100:+.1f} pp" for r in CAND))

    # ---- per-episode gains vs live
    log(f"\n  PER-EPISODE GAIN vs live (log-return difference accumulated over the episode's days, pp): proxy episodes (32) and real episodes ({len(RE_EPS)})")
    pdates = [r['d'] for r in rows]
    for rec in CAND:
        k = rec['k']
        for hname, eps_, ser, base, dts in (('proxy', E_EPS_Q, rec['ser'], LIVE_SER, pdates), ('real', RE_EPS, rec['rser'], RLIVE_SER, RDAYS[:-1])):
            gains = []
            for a, b in eps_:
                g = sum(math.log1p(ser[i]) - math.log1p(base[i]) for i in range(a, b + 1)) * 100
                # label: the state after the episode on that harness
                if hname == 'proxy':
                    nxt = rows[b + 1]['state'] if b + 1 < len(rows) else None
                else:
                    nxt = SIG_R['state'][RIX[dts[b + 1]]] if b + 1 < len(dts) else None
                gains.append((g, dts[a], dts[b], b - a + 1, 'B' if nxt == 'F' else ('R' if nxt else '?')))
            gains.sort()
            pos = sum(1 for g in gains if g[0] > 0); tot = sum(g[0] for g in gains)
            gb = [g[0] for g in gains if g[4] == 'B']; gr = [g[0] for g in gains if g[4] == 'R']
            log(f"  k={k} {hname:<5}: {len(gains)} episodes, positive {pos}/{len(gains)}, total {tot:+.2f} pp, mean {tot/len(gains):+.2f}, median {statistics.median([g[0] for g in gains]):+.2f}; "
                f"by label: BREAK n={len(gb)} mean {statistics.mean(gb) if gb else float('nan'):+.2f} (pos {sum(1 for x in gb if x>0)}), REVERSAL n={len(gr)} mean {statistics.mean(gr) if gr else float('nan'):+.2f} (pos {sum(1 for x in gr if x>0)})")
            log(f"        top 3: " + "; ".join(f"{d0}..{d1} ({n}d,{l}) {g:+.2f}" for g, d0, d1, n, l in gains[-1:-4:-1]))
            log(f"     bottom 3: " + "; ".join(f"{d0}..{d1} ({n}d,{l}) {g:+.2f}" for g, d0, d1, n, l in gains[:3]))

    # ---- block bootstrap for the best k (by full-period proxy Sharpe vs live; also the best on real rows if different)
    best = max(CAND, key=lambda r: r['dF']); best_r = max(CAND, key=lambda r: r['rd'])
    picks = [best] + ([best_r] if best_r is not best else [])
    log(f"\n  BLOCK BOOTSTRAP (circular, {BB.N_BOOT} draws, paired blocks) of the Sharpe and log-return difference: best k by proxy full Sharpe = {best['k']}"
        + (f"; best on real rows = {best_r['k']}" if best_r is not best else " (also best on real rows)"))
    for rec in picks:
        for lab, a, b in ((f"k={rec['k']} proxy vs live", rec['ser'], LIVE_SER), (f"k={rec['k']} proxy vs SPMO {rec['ctl']['g']}% control", rec['ser'], rec['ctl']['ser']),
                          (f"k={rec['k']} real vs live", rec['rser'], RLIVE_SER), (f"k={rec['k']} real vs SPMO {rec['rctl']['g']}% control", rec['rser'], rec['rctl']['rser'])):
            for blk in (20, 60):
                l1, l2, pl, s1, s2, ps = boot(a, b, blk, seed=(rec['k'] * 7919 + blk + len(lab)) & 0xffff)
                log(f"      {lab:<40} block {blk:>2}d: Sharpe diff 95% CI [{s1:+.3f}, {s2:+.3f}] P(<=0) = {ps:.3f} | log-return [{l1*100:+.2f}, {l2*100:+.2f}] pp/yr P(<=0) = {pl:.3f}")
    # era-sliced Sharpe of the best vs live, for the record
    log(f"  best k={best['k']} sliced Sharpe: search {sliced_sharpe(best['ser'], *SEARCH):.3f} vs live {sliced_sharpe(LIVE_SER, *SEARCH):.3f}; "
        f"holdout {sliced_sharpe(best['ser'], *HOLDOUT):.3f} vs live {sliced_sharpe(LIVE_SER, *HOLDOUT):.3f}")
    log(f"\n  No adoption language here: three pre-registered candidates, reported against live and the exposure-matched control. The owner decides.")

    # ============================================================================================================
    # CARRY-OVER RULE (owner request, second addition; clarified: D -> E transitions ONLY). On a D -> E transition keep
    # the row held on the LAST D day for E sessions 1..k, then the E row (cash). Ungated last-D day -> 100 % QLD
    # carried; gated last-D day (state.d_gate_active) -> already cash, the rule is a no-op for that episode. E episodes
    # entered from A or F hold 100 % cash from session 1. The carried row is the pre-vol-target row of the last D day,
    # vol-targeted daily like every other row.
    # ============================================================================================================
    from state import d_gate_flags, D_GATE_GAP200, D_GATE_BREADTH_PCT
    QLD = tuple(state.TARGET_WEIGHTS['D'])
    assert QLD == (0.0, 0.0, 1.0, 0.0, 0.0), QLD
    KS = [0, 1, 2, 3, 4, 5, 7, 10, 'all']
    log(f"\n{'='*118}\n  CARRY-OVER RULE (D -> E only): hold the last D day's row (ungated D = 100 % QLD; gated D = cash, no-op) for E sessions 1..k, then cash. "
        f"k in {KS}. A -> E and F -> E entries: cash from session 1.\n{'='*118}")
    gaps_r = compute_extension_gaps(sorted(RQQQ), RQQQ)
    def entry_proxy(a):
        pr = rows[a - 1]['state'] if a > 0 else None
        if pr != 'D': return pr, None, None, None
        d = rows[a - 1]['d']; bp = BP_Q.get(d); g2 = rows[a - 1]['gaps'][200]
        return pr, bp, g2, d in GATE_Q
    def entry_real(a):
        d = RDAYS[a - 1] if a > 0 else None
        pr = SIG_R['state'][RIX[d]] if d else None
        if pr != 'D': return pr, None, None, None
        bp = BP_R.get(d); g2 = gaps_r[d][200]
        return pr, bp, g2, d_gate_active('D', bp, g2)
    EPQ = [(a, b) + entry_proxy(a) for a, b in E_EPS_Q]      # (a, b, prior, breadth, gap200, gated)
    EPR = [(a, b) + entry_real(a) for a, b in RE_EPS]
    log(f"  LAST D DAY before each D -> E entry (proxy): the gate is breadth pct < {D_GATE_BREADTH_PCT} OR gap200 < {D_GATE_GAP200*100:.0f} %")
    log(f"  {'entry':<11} {'n':>3} {'last D':<11} {'breadth':>8} {'gap200':>8}  gated  why")
    for a, b, pr, bp, g2, gated in EPQ:
        if pr != 'D': continue
        bflag, gflag = d_gate_flags(bp, g2)
        why = ' + '.join(x for x, f in (('breadth', bflag), ('gap200<2%', gflag)) if f) or '(none)'
        log(f"  {pdates[a]:<11} {b-a+1:>3} {rows[a-1]['d']:<11} {fmt(bp,8,2)} {fmt(g2*100 if g2 is not None else None,7,2)}%  {'YES' if gated else 'no ':<5}  {why}")
    nD = sum(1 for e in EPQ if e[2] == 'D'); nUG = sum(1 for e in EPQ if e[2] == 'D' and not e[5])
    nDr = sum(1 for e in EPR if e[2] == 'D'); nUGr = sum(1 for e in EPR if e[2] == 'D' and not e[5])
    log(f"  proxy: {len(EPQ)} episodes, {nD} entered from D, of which UNGATED on the last D day: {nUG}; entered from A: {sum(1 for e in EPQ if e[2]=='A')}, from F: {sum(1 for e in EPQ if e[2]=='F')}")
    log(f"  real:  {len(EPR)} episodes, {nDr} entered from D, of which UNGATED on the last D day: {nUGr}")
    log(f"  MECHANICAL POINT: an E entry needs QQQ below 0.99 x SMA200, so on the last D day price is at most a session's move above the 200d;")
    log(f"  gap200 < 2 % on that day is all but guaranteed (the 2020-03 entries are the exception by gap and are caught by breadth). The gate")
    log(f"  therefore holds the D row as cash on the last D day of EVERY D -> E transition, and the carry-over rule carries cash: it is live.")
    ACT_Q = [e for e in EPQ if e[2] == 'D' and not e[5]]; ACT_R = [e for e in EPR if e[2] == 'D' and not e[5]]
    log(f"  -> under the CURRENT design the carry-over rule acts on {len(ACT_Q)} proxy and {len(ACT_R)} real episodes: it is a no-op for every k and equals live.")
    log(f"     No k sweep, permutation or bootstrap is run for it. The only path by which a carry-over could matter is if the D gate were ever removed.")

    # ============================================================================================================
    # COUNTERFACTUAL on the RETIRED 2026-09-09 design (owner request): NO D gate (every D day 100 % QLD) and
    # E = 50 % XLU / 50 % cash -- exactly the baseline d_substate_fresh pins (proxy 22.18 % / 0.913 / -33.6 %, S 1.103
    # H 0.768; real daily 29.66 % / 1.145 / -32.9 %). Under that design every D -> E cross is an ungated QLD entry, so
    # the rule acts on all 25 (real: 11). Rule: E entered from D -> 100 % QLD for E sessions 1..k, then the old E row;
    # E entered from A or F -> the old E row from session 1. k = 0 is the old design itself.
    # ============================================================================================================
    E_OLD = (0.0, 0.0, 0.0, 0.5, 0.5)
    assert state.TARGET_WEIGHTS['E'] == E_OLD
    log(f"\n{'='*118}\n  COUNTERFACTUAL ON THE RETIRED 2026-09-09 DESIGN: no D gate, E = 50 % XLU / 50 % cash. 'What the carry-over would have been worth had the D gate not been adopted.'\n{'='*118}")
    OLD_EV, OLD_SER = DSF.BASE_EV, DSF.LIVE_SER
    OLD_REV, OLD_RSER = DSF.REAL_EV, DSF.REAL_SER
    log(f"  BASELINE (old design, k = 0): proxy {fmt_ev(OLD_EV)} S {OLD_EV['s_sharpe']:.3f} H {OLD_EV['h_sharpe']:.3f} exp {OLD_EV['risky']*100:.1f}% | real daily {fmt_ev(OLD_REV)} exp {DSF.REAL_EXP*100:.1f}%")
    assert abs(OLD_EV['cagr'] * 100 - 22.18) < 0.006 and abs(OLD_EV['sharpe'] - 0.913) < 0.0006 and abs(OLD_EV['mdd'] * 100 + 33.6) < 0.06 \
        and abs(OLD_EV['s_sharpe'] - 1.103) < 0.0006 and abs(OLD_EV['h_sharpe'] - 0.768) < 0.0006, 'old proxy baseline != 22.18/0.913/-33.6, S 1.103 H 0.768'
    assert abs(OLD_REV['cagr'] * 100 - 29.66) < 0.006 and abs(OLD_REV['sharpe'] - 1.145) < 0.0006 and abs(OLD_REV['mdd'] * 100 + 32.9) < 0.06, 'old real baseline != 29.66/1.145/-32.9'
    log("  both old-design baselines reproduced (asserted; d_substate_fresh asserts its real mirror against monthly_returns.simulate(d_gate=False)).")
    # real mirror WITHOUT the gate and with an E override (None -> the pinned old design on that day)
    def simulate_real_old(px, qqq_, days, override_e):
        qd = sorted(qqq_)
        states_ = dict(zip(qd, state.compute_states(qd, qqq_)))
        micro = compute_micro_agreement(qd, qqq_)
        fast = compute_fast_states(qd, qqq_); gaps = compute_extension_gaps(qd, qqq_)
        held = prev = None; out = []; risky = 0.0; nreb = 0
        for i in range(1, len(days)):
            d0, d1 = days[i - 1], days[i]
            st, ag = states_[d0], micro[d0]
            vol = realized_vol_live(qd, qqq_, as_of=d0)
            row = override_e(d0) if st == 'E' else None
            if row is None:
                t = target_weights_with_voltarget(st, ag, vol, fast_state=fast[d0], gaps=gaps[d0], d_gate=False)
            else:
                t = RF.vt(row, vol)
            eff = effective_state(st, fast[d0])
            stk = (eff, extension_votes(eff, gaps[d0]), row is not None)
            cost = 0.0
            if held is None:
                held = list(t); nreb += 1
            else:
                do, drift, _ = needs_rebalance(t, held, stk != prev)
                if do:
                    cost = MR.ONE_WAY * drift; held = list(t); nreb += 1
            r = [px[s_][d1] / px[s_][d0] - 1 for s_ in MR.LEGS]
            g = sum(held[j] * r[j] for j in range(5))
            risky += sum(held[:4])
            out.append((d1, stk[0], g - cost))
            dn = 1 + g
            if dn > 0: held = [held[j] * (1 + r[j]) / dn for j in range(5)]
            prev = stk
        n = len(out)
        return out, risky / n, nreb / (n / 252.0)
    _chk, _, _ = simulate_real_old(RPX, RQQQ, RDAYS, lambda d0: None)
    assert all(abs(a[2] - b) < 1e-12 for a, b in zip(_chk, OLD_RSER)), 'old-design real mirror with E override hook does not reproduce d_substate_fresh'
    def proxy_eval_old(row_fn):
        """row_fn(d, age) -> action row or None on E days (None = the old design's own row that day); everything else the old design."""
        def fn(r):
            if r['d'] in E_SET:
                row = row_fn(r['d'], AGE_Q[r['d']])
                return DSF.BASE[r['d']] if row is None else vt(row, r['vol'])
            return DSF.BASE[r['d']]
        return evaluate_full(fn)
    def real_eval_old(row_fn):
        out, exp, reb = simulate_real_old(RPX, RQQQ, RDAYS, lambda d0: row_fn(d0, AGE_R[d0]))
        m, ser = real_metrics(out)
        return dict(m, exp=exp, reb=reb), ser
    _e0, _ = proxy_eval_old(lambda d, age: None); _r0, _ = real_eval_old(lambda d, age: None)
    assert abs(_e0['sharpe'] - OLD_EV['sharpe']) < 1e-12 and abs(_r0['sharpe'] - OLD_REV['sharpe']) < 1e-12
    ALLD_Q = [e for e in EPQ if e[2] == 'D']; ALLD_R = [e for e in EPR if e[2] == 'D']
    nS_ = sum(1 for e in ALLD_Q if pdates[e[0]] >= SEARCH[0])
    log(f"  under the old design every D -> E cross is an ungated QLD entry: the rule acts on {len(ALLD_Q)} proxy episodes (search {nS_}, holdout {len(ALLD_Q)-nS_}) and {len(ALLD_R)} real episodes;")
    log(f"  the {sum(1 for e in EPQ if e[2]=='A')} A -> E and {sum(1 for e in EPQ if e[2]=='F')} F -> E proxy entries hold the old E row from session 1.")
    # control: f x QLD + (1-f) x old E row on every E day (f = 0 reproduces k = 0 up to the extension trim on E days, checked)
    log(f"\n  CONSTANT-QLD-IN-E LADDER (control, old design): f x QLD + (1-f) x (50 % XLU / 50 % cash) on every E day")
    log(f"  {'f':>4} | {'CAGR':>7}{'Sharpe':>7}{'MaxDD':>7}{'exp':>6}{'S Sh':>7}{'H Sh':>7}{'dS_F':>7} | {'rCAGR':>7}{'rSh':>7}{'rDD':>7}{'rexp':>6}{'rdSh':>7}")
    QLAD = []
    for f in (0, 25, 50, 75, 100):
        row = (0.0, 0.0, f / 100.0, 0.5 * (1 - f / 100.0), 0.5 * (1 - f / 100.0))
        ev, ser = proxy_eval_old(lambda d, age, row=row: row); rev, rser = real_eval_old(lambda d, age, row=row: row)
        QLAD.append(dict(f=f, ev=ev, real=rev, ser=ser, rser=rser))
        log(f"  {f:>3}% | {ev['cagr']*100:>6.2f}%{ev['sharpe']:>7.3f}{ev['mdd']*100:>6.1f}%{ev['risky']*100:>5.1f}%{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f}{ev['sharpe']-OLD_EV['sharpe']:>+7.3f} | "
            f"{rev['cagr']*100:>6.2f}%{rev['sharpe']:>7.3f}{rev['mdd']*100:>6.1f}%{rev['exp']*100:>5.1f}%{rev['sharpe']-OLD_REV['sharpe']:>+7.3f}")
    log(f"  (f = 0 % vs k = 0: proxy Sharpe {QLAD[0]['ev']['sharpe']-OLD_EV['sharpe']:+.4f}, real {QLAD[0]['real']['sharpe']-OLD_REV['sharpe']:+.4f} -- any difference is the explicit-row path vs the design's own E-day row.)")
    def qmatch(exp, key): return min(QLAD, key=lambda c: abs((c['ev']['risky'] if key == 'ev' else c['real']['exp']) - exp))
    def maps(EP, dts, act_set):
        m = {}
        for e in EP:
            a, b = e[0], e[1]; act = e in act_set
            for j, i in enumerate(range(a, b + 1)): m[dts[i]] = (j + 1, act)
        return m
    MQ_ = maps(EPQ, pdates, set(ALLD_Q)); MR_ = maps(EPR, RDAYS, set(ALLD_R))
    def rule(m, k):
        kk = 10 ** 9 if k == 'all' else k
        return lambda d, age: (QLD if (m[d][1] and m[d][0] <= kk) else None)
    log(f"\n  K CURVE (old design; k = 0 is the old design itself). act ep = episodes the rule acts on, search / holdout / real")
    log(f"  {'k':>4} {'act ep S/H/real':<16} | {'CAGR':>7}{'Sharpe':>7}{'MaxDD':>7}{'exp':>6}{'reb':>6} | S {'CAGR':>7}{'Sh':>6}{'DD':>7} | H {'CAGR':>7}{'Sh':>6}{'DD':>7} | {'dS_F':>7}{'dS_S':>7}{'dS_H':>7} | real {'CAGR':>7}{'Sh':>6}{'DD':>7}{'exp':>5}{'rdSh':>7} | ctl {'f':>4}{'vC_F':>7}{'rvC':>7}")
    CO = []
    for k in KS:
        ev, ser = proxy_eval_old(rule(MQ_, k)); rev, rser = real_eval_old(rule(MR_, k))
        kk = 10 ** 9 if k == 'all' else k
        actS = nS_ if kk >= 1 else 0; actH = (len(ALLD_Q) - nS_) if kk >= 1 else 0; actR = len(ALLD_R) if kk >= 1 else 0
        c = qmatch(ev['risky'], 'ev'); cr = qmatch(rev['exp'], 'real')
        rec = dict(k=k, ev=ev, real=rev, ser=ser, rser=rser, dF=ev['sharpe'] - OLD_EV['sharpe'], dS=ev['s_sharpe'] - OLD_EV['s_sharpe'],
                   dH=ev['h_sharpe'] - OLD_EV['h_sharpe'], rd=rev['sharpe'] - OLD_REV['sharpe'], ctl=c, rctl=cr,
                   vCF=ev['sharpe'] - c['ev']['sharpe'], rvC=rev['sharpe'] - cr['real']['sharpe'])
        CO.append(rec)
        log(f"  {str(k):>4} {f'{actS}/{actH}/{actR}':<16} | {ev['cagr']*100:>6.2f}%{ev['sharpe']:>7.3f}{ev['mdd']*100:>6.1f}%{ev['risky']*100:>5.1f}%{ev['reb']:>6.1f} | "
            f"{ev['s_cagr']*100:>8.2f}%{ev['s_sharpe']:>6.3f}{ev['s_mdd']*100:>6.1f}% | {ev['h_cagr']*100:>8.2f}%{ev['h_sharpe']:>6.3f}{ev['h_mdd']*100:>6.1f}% | "
            f"{rec['dF']:>+7.3f}{rec['dS']:>+7.3f}{rec['dH']:>+7.3f} | {rev['cagr']*100:>11.2f}%{rev['sharpe']:>6.3f}{rev['mdd']*100:>6.1f}%{rev['exp']*100:>4.0f}%{rec['rd']:>+7.3f} | "
            f"{str(c['f'])+'%':>8}{rec['vCF']:>+7.3f}{rec['rvC']:>+7.3f}")
    ks1 = [r for r in CO if r['k'] != 0]
    bestk = max(ks1, key=lambda r: r['dF']); others = [r['dF'] for r in ks1 if r is not bestk]
    spread_ = max(r['dF'] for r in ks1) - min(r['dF'] for r in ks1)
    shape = ("PLATEAU (all k within 0.01 of each other)" if spread_ < 0.01 else
             "SPIKE (best k more than 0.01 above the next)" if bestk['dF'] - max(others) > 0.01 else "neither a clean plateau nor a spike")
    log(f"  shape (proxy full Sharpe gain vs k=0): best k = {bestk['k']} at {bestk['dF']:+.3f}; other k's range [{min(others):+.3f}, {max(others):+.3f}]; "
        f"k's with gain > 0: {sum(1 for r in ks1 if r['dF'] > 0)}/{len(ks1)}; both-era (S and H) gain > 0: {sum(1 for r in ks1 if r['dS'] > 0 and r['dH'] > 0)}/{len(ks1)}; "
        f"real gain at best proxy k {bestk['rd']:+.3f}; best real k = {max(ks1, key=lambda r: r['rd'])['k']} at {max(r['rd'] for r in ks1):+.3f} -> {shape}")
    log(f"  MaxDD change vs k=0 (pp): " + ", ".join(f"k={r['k']} proxy {(r['ev']['mdd']-OLD_EV['mdd'])*100:+.1f} real {(r['real']['mdd']-OLD_REV['mdd'])*100:+.1f}" for r in ks1))
    # per-episode gains k=3
    log(f"\n  PER-EPISODE GAIN vs k=0, k=3 (pp, log-return difference over the episode; D -> E entries)")
    r3 = next(r for r in CO if r['k'] == 3)
    for hname, EP, ser, base, dts, nxt_of in (('proxy', ALLD_Q, r3['ser'], OLD_SER, pdates, lambda b: rows[b + 1]['state'] if b + 1 < len(rows) else None),
                                              ('real', ALLD_R, r3['rser'], OLD_RSER, RDAYS[:-1], lambda b: SIG_R['state'][RIX[RDAYS[b + 1]]] if b + 1 < len(RDAYS) - 1 else None)):
        gains = []
        for e in EP:
            a, b = e[0], e[1]
            g = sum(math.log1p(ser[i]) - math.log1p(base[i]) for i in range(a, b + 1)) * 100
            nx = nxt_of(b); gains.append((g, dts[a], dts[b], b - a + 1, 'B' if nx == 'F' else 'R'))
        gains.sort(); gb = [g[0] for g in gains if g[4] == 'B']; gr = [g[0] for g in gains if g[4] == 'R']
        log(f"  {hname:<5}: {len(gains)} acting episodes, positive {sum(1 for g in gains if g[0] > 0)}/{len(gains)}, total {sum(g[0] for g in gains):+.2f} pp, "
            f"median {statistics.median([g[0] for g in gains]):+.2f}; BREAK n={len(gb)} mean {fmt(statistics.mean(gb) if gb else None,6,2)} (pos {sum(1 for x in gb if x>0)}), "
            f"REVERSAL n={len(gr)} mean {fmt(statistics.mean(gr) if gr else None,6,2)} (pos {sum(1 for x in gr if x>0)})")
        log(f"        top 3: " + "; ".join(f"{d0}..{d1} ({n}d,{l}) {g:+.2f}" for g, d0, d1, n, l in gains[-1:-4:-1]))
        log(f"     bottom 3: " + "; ".join(f"{d0}..{d1} ({n}d,{l}) {g:+.2f}" for g, d0, d1, n, l in gains[:3]))
    # raw ingredient
    log(f"\n  RAW INGREDIENT: QLD-leg return over E sessions 1..min(k, n) on the {len(ALLD_Q)} proxy / {len(ALLD_R)} real D -> E entries (proxy = the harness's synthetic 2x leg, real = QLD);")
    log(f"  by outcome label (BREAK = exits to F) and pooled. This is what the rule holds instead of the old E row's 50 % XLU / 50 % cash.")
    log(f"  {'leg':<9} {'k':>4} {'group':<9} {'n':>3} {'mean%':>7} {'med%':>7} {'pos':>6}")
    for k in [1, 2, 3, 5, 10, 'all']:
        kk = 10 ** 9 if k == 'all' else k
        for hname, EP, legret, nxt_of in (('proxy2x', ALLD_Q, lambda i: rows[i]['legs'][2], lambda b: rows[b + 1]['state'] if b + 1 < len(rows) else None),
                                          ('realQLD', ALLD_R, lambda i: RPX['QLD'][RDAYS[i + 1]] / RPX['QLD'][RDAYS[i]] - 1, lambda b: SIG_R['state'][RIX[RDAYS[b + 1]]] if b + 1 < len(RDAYS) - 1 else None)):
            vals = []
            for e in EP:
                a, b = e[0], e[1]; n_ = min(kk, b - a + 1); v = 1.0
                for i in range(a, a + n_): v *= 1 + legret(i)
                vals.append(((v - 1) * 100, 'B' if nxt_of(b) == 'F' else 'R'))
            for gname in ('BREAK', 'REVERSAL', 'ALL'):
                c = [x for x, l in vals if gname == 'ALL' or l == gname[0]]
                if not c: continue
                log(f"  {hname:<9} {str(k):>4} {gname:<9} {len(c):>3} {statistics.mean(c):>7.2f} {statistics.median(c):>7.2f} {sum(1 for x in c if x > 0):>3}/{len(c):<2}")
    # permutation: circular shift of the per-E-day action flags (all k together); statistic = best-of-k full-proxy Sharpe gain vs k=0
    E_ORDER = [rows[i]['d'] for i in E_ROWS]
    kl = [k for k in KS if k != 0]
    FLAGS = {k: [(MQ_[d][1] and MQ_[d][0] <= (10 ** 9 if k == 'all' else k)) for d in E_ORDER] for k in kl}
    global _P3
    _P3 = dict(rows=rows, run=run, vt=vt, GB=DSF.BASE, E_ORDER=E_ORDER, FLAGS=FLAGS, kl=kl, QLD=QLD, LIVE_SH=bstats(OLD_SER)[1], bstats=bstats, nE=len(E_ORDER))
    real_gains = {k: next(r for r in CO if r['k'] == k)['dF'] for k in kl}
    chk = _p3_worker(0)
    assert all(abs(chk[k] - real_gains[k]) < 1e-9 for k in kl), 'permutation worker at shift 0 does not reproduce the k curve'
    NP = int(os.environ.get('EOE_NPERM3', '2000'))
    rng = random.Random(20260920); shifts = [rng.randrange(1, len(E_ORDER)) for _ in range(NP)]
    from multiprocessing import Pool
    t1 = time.time()
    with Pool(4) as pool:
        outs = pool.map(_p3_worker, shifts, chunksize=8)
    null_best = sorted(max(o.values()) for o in outs)
    real_best = max(real_gains.values())
    q = lambda v, p_: v[min(len(v) - 1, int(len(v) * p_))]
    log(f"\n  PERMUTATION ({NP} circular shifts of the {len(E_ORDER)}-day E action-flag sequences, all {len(kl)} k's shifted together, run structure preserved; "
        f"statistic = best-of-{len(kl)} full-proxy Sharpe gain vs k=0; {time.time()-t1:.0f}s):")
    log(f"    null best-k gain: median {q(null_best,0.5):+.3f}, 90th {q(null_best,0.9):+.3f}, 95th {q(null_best,0.95):+.3f}, max {null_best[-1]:+.3f} | "
        f"real best-k gain {real_best:+.3f} (k={max(real_gains, key=real_gains.get)}) -> p = {sum(1 for x in null_best if x >= real_best)/NP:.3f}")
    for k in kl:
        nk = sorted(o[k] for o in outs)
        log(f"    k={str(k):>3}: real {real_gains[k]:+.3f}; null median {q(nk,0.5):+.3f} 95th {q(nk,0.95):+.3f}; p = {sum(1 for x in nk if x >= real_gains[k])/NP:.3f}")
    bestr = max(ks1, key=lambda r: r['rd'])
    log(f"\n  BLOCK BOOTSTRAP ({BB.N_BOOT} draws, paired circular blocks): best k by proxy = {bestk['k']}" + (f", best k by real = {bestr['k']}" if bestr is not bestk else " (also best on real)"))
    for rec in ([bestk] + ([bestr] if bestr is not bestk else [])):
        for lab, a, b in ((f"k={rec['k']} proxy vs k=0", rec['ser'], OLD_SER), (f"k={rec['k']} proxy vs QLD {rec['ctl']['f']}% ladder", rec['ser'], rec['ctl']['ser']),
                          (f"k={rec['k']} real vs k=0", rec['rser'], OLD_RSER), (f"k={rec['k']} real vs QLD {rec['rctl']['f']}% ladder", rec['rser'], rec['rctl']['rser'])):
            for blk in (20, 60):
                l1, l2, pl, s1, s2, ps = boot(a, b, blk, seed=(len(str(rec['k'])) * 7919 + blk * 13 + len(lab)) & 0xffff)
                log(f"      {lab:<36} block {blk:>2}d: Sharpe diff 95% CI [{s1:+.3f}, {s2:+.3f}] P(<=0) = {ps:.3f} | log-return [{l1*100:+.2f}, {l2*100:+.2f}] pp/yr P(<=0) = {pl:.3f}")
    log(f"\n  No adoption language: on the current design the carry-over rule equals live; the counterfactual is on a retired design. The owner decides.")


_P3 = None
def _p3_worker(shift):
    """full-proxy Sharpe gain vs k=0 for every k, with the per-E-day QLD action flags circularly shifted by `shift`."""
    P = _P3; nE = P['nE']; out = {}
    for k in P['kl']:
        fl = P['FLAGS'][k]
        on = set(P['E_ORDER'][j] for j in range(nE) if fl[(j - shift) % nE])
        ser, _ = P['run'](P['rows'], lambda r: P['vt'](P['QLD'], r['vol']) if r['d'] in on else P['GB'][r['d']])
        out[k] = P['bstats'](ser)[1] - P['LIVE_SH']
    return out


if __name__ == '__main__':
    main()
    part2()
    part3_time_in_state()
    _log_f.close()
