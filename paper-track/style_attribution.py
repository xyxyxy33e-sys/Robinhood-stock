"""Style / exposure attribution of the LIVE design (research line
`style_attribution`, 2026-09-09).  Owner's question: "Does the strategy
outperform after accounting for changing Nasdaq exposure, momentum exposure,
and cash holdings?  This separates timing skill from benefiting when a
particular investment style performs well."

Everything runs through the project's own harness (improvement_search.run /
evaluate on the 26-year QQQ-core proxy, return_frontier.eval_real on the real
weekly SPMO rows).  The only loop-shaped code here is `run_w`, a verbatim copy
of improvement_search.run that ALSO records the held weights and the cost it
charged each day; its returns are asserted equal to run()'s to 1e-15 before
anything uses them.

Return sources (daily, on the proxy calendar; weekly on rr):
  MKT_NDX  QQQ total return minus cash          (D['core'], D['cash'])
  MKT_SPX  SPY total return (1.8%/yr accrual) minus cash  (data/spy_long_history.csv)
  MOM      Fama-French daily momentum factor     (data/ff_momentum_daily.csv,
           fetched 2026-09-09 from Ken French's data library, CRSP 202607)
  SMB/HML  Fama-French daily size/value          (data/ff_3factors_daily.csv)
  LEV      synthetic 3x leg excess minus 3x core excess = L3 - 3C + 2cash:
           the volatility drag + financing cost of holding TQQQ
  SPMO-SPY real momentum-style excess (weekly, rr only, price-only SPMO)

Sections:
  1  static attribution (OLS, Newey-West SEs, block-bootstrap alpha CI)
  2  exposure-matched passive: e_{t-1} x MKT_NDX + cash; LIVE minus it
  3  style-regime buckets (MOM quintile, NDX-SPX quintile, vol tercile, state)
  4  rolling 3y alpha / beta by year
  5  three-way decomposition of the CAGR gap vs QQQ and vs SPY, 4bp / 10bp
  6  placebo: exposure path block-shuffled by year / 60d blocks
"""
import sys, math, random, bisect, time
sys.path.insert(0, 'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
import improvement_search as IS
import voltarget_live_backtest as VL
from improvement_search import SEARCH, HOLDOUT, era
from state import extension_scale, realized_vol
from long_history_backtest import load_px, total_return_index, QQQ_DIV_PA
from block_bootstrap import boot, stats

T0 = time.time()
BETA = (1.0, 3.0, 2.0, 0.5, 0.0)     # equity beta per leg: core 1x, TQQQ 3x, QLD 2x, XLU ~0.5x (improvement_search_r2.BETA)
LIVE_BP = 0.0004
NW_LAG = 10
SEED = 20260909


def set_cost(bp):
    IS.ONE_WAY_SPREAD = bp
    VL.ONE_WAY_SPREAD = bp


# ------------------------------------------------------------------ weight fns
def live_fn(r):
    w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
    if f < 1: w = tuple(a * f for a in w[:4]) + (1 - f * sum(w[:4]),)
    return vt(w, r.get('vol_live') or r['vol'])


def live_fn_real(r):
    w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
    if f < 1: w = tuple(a * f for a in w[:4]) + (1 - f * sum(w[:4]),)
    return RF.vt(w, r['vol_live'])


def base_fn(r):            # base allocations only: macro state, no overlays, no vol target
    return W[r['state']]


def qqq_fn(r):
    return (1.0, 0.0, 0.0, 0.0, 0.0)


for r in rr:
    r['vol_live'] = max(realized_vol(qd, qqq, as_of=r['d0'], lookback=10),
                        realized_vol(qd, qqq, as_of=r['d0'], lookback=30))
    assert abs(r['vol_live'] - r['vol']) < 1e-12

# ------------------------------------------------------------------ reproduce
ev = evaluate(rows, live_fn); er = RF.eval_real(rr, live_fn_real)
print(f"LIVE reproduced: proxy {ev['cagr']*100:.2f}% / {ev['sharpe']:.3f} / {ev['mdd']*100:.1f}%  "
      f"S {ev['s_sharpe']:.3f} H {ev['h_sharpe']:.3f}  risky {ev['risky']*100:.1f}%  |  "
      f"real {er['cagr']*100:.2f}% / {er['sharpe']:.3f} / {er['mdd']*100:.1f}%")
assert abs(ev['cagr'] - 0.2212) < 5e-4 and abs(ev['sharpe'] - 0.938) < 1e-3 and abs(er['sharpe'] - 1.260) < 1e-3


# ------------------------------------------------------------------ run + weights
def run_w(rows_, wfn, band=IS.BAND):
    """improvement_search.run, verbatim, plus the held weights and cost per day."""
    held = prev = None
    rets, risky, ws, costs = [], 0.0, [], []
    for r in rows_:
        t = wfn(r)
        key = (r['state'], r['agree'])
        cost = 0.0
        if held is None:
            held = list(t)
        else:
            drift = sum(abs(t[j] - held[j]) for j in range(5))
            if key != prev or drift > band:
                cost = IS.ONE_WAY_SPREAD * drift
                held = list(t)
        risky += sum(held[:4])
        ws.append(tuple(held)); costs.append(cost)
        g = sum(held[j] * r['legs'][j] for j in range(5))
        rets.append(g - cost)
        dn = 1 + g
        if dn > 0:
            held = [held[j] * (1 + r['legs'][j]) / dn for j in range(5)]
        prev = key
    return rets, ws, costs


def real_w(rows_, wfn):
    """return_frontier.eval_real's per-row return, plus weights and cost."""
    prev = None; rets, ws, costs = [], [], []
    for r in rows_:
        w = wfn(r)
        cost = VL.ONE_WAY_SPREAD * sum(abs(w[i] - (prev[i] if prev else 0)) for i in range(5))
        rets.append(sum(w[i] * r['legs'][i] for i in range(5)) - cost)
        ws.append(tuple(w)); costs.append(cost); prev = w
    return rets, ws, costs


_a = run(rows, live_fn)[0]; _b = run_w(rows, live_fn)[0]
assert len(_a) == len(_b) and max(abs(x - y) for x, y in zip(_a, _b)) < 1e-15, "run_w drifted from run()"

# ------------------------------------------------------------------ factor data
D = data(); ds = D['ds']; ix = {d: i for i, d in enumerate(ds)}
spy = load_px('data/spy_long_history.csv')
SPY_TR = total_return_index({d: spy[d] for d in ds if d in spy}, 1.8)


def load_ff(path):
    out = {}
    for l in open(path).read().splitlines()[1:]:
        p = l.split(','); out[p[0]] = [float(x) for x in p[1:]]
    return out


MOM = load_ff('data/ff_momentum_daily.csv'); FF3 = load_ff('data/ff_3factors_daily.csv')
FF_END = max(MOM)
ffd = sorted(MOM)


def ff_between(d0, d1, src, k=0):
    """Compound a French daily factor over FF dates in (d0, d1]."""
    i = bisect.bisect_right(ffd, d0); j = bisect.bisect_right(ffd, d1)
    g = 1.0
    for d in ffd[i:j]:
        g *= 1 + src[d][k]
    return g - 1


for r in rows:
    d0 = r['d']; d1 = ds[ix[d0] + 1]; r['d1'] = d1
    C, L3, L2, X, cash = r['legs']
    assert abs(C - (D['core'][d1] / D['core'][d0] - 1)) < 1e-12
    r['MKT_NDX'] = C - cash
    r['MKT_SPX'] = SPY_TR[d1] / SPY_TR[d0] - 1 - cash
    r['LEV'] = L3 - 3 * C + 2 * cash
    r['LEV2'] = L2 - 2 * C + cash
    r['XLUX'] = X - 0.5 * C - 0.5 * cash
    r['cash'] = cash
    if d1 <= FF_END:
        r['MOM'] = ff_between(d0, d1, MOM); r['SMB'] = ff_between(d0, d1, FF3, 1); r['HML'] = ff_between(d0, d1, FF3, 2)
        r['MKTRF'] = ff_between(d0, d1, FF3, 0)
    else:
        r['MOM'] = None

# alignment sanity: MKT_NDX vs French Mkt-RF should be strongly positive, contemporaneous
def corr(a, b):
    n = len(a); ma = sum(a) / n; mb = sum(b) / n
    sa = math.sqrt(sum((x - ma) ** 2 for x in a)); sb = math.sqrt(sum((x - mb) ** 2 for x in b))
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb)


REG = [r for r in rows if r['MOM'] is not None]
print(f"rows {len(rows)} {rows[0]['d']}..{rows[-1]['d']}; regression rows (French data through {FF_END}) {len(REG)}")
print(f"alignment: corr(MKT_NDX, FF Mkt-RF) = {corr([r['MKT_NDX'] for r in REG], [r['MKTRF'] for r in REG]):+.3f}, "
      f"corr(MKT_NDX, MKT_SPX) = {corr([r['MKT_NDX'] for r in REG], [r['MKT_SPX'] for r in REG]):+.3f}, "
      f"corr(MKT_NDX, MOM) = {corr([r['MKT_NDX'] for r in REG], [r['MOM'] for r in REG]):+.3f}")
for k in ('MKT_NDX', 'MKT_SPX', 'MOM', 'SMB', 'HML', 'LEV'):
    v = [r[k] for r in REG]; m = sum(v) / len(v)
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))
    print(f"   {k:<8} mean {m*252*100:+6.2f} pp/yr  vol {sd*math.sqrt(252)*100:5.1f}%  Sharpe {m*252/(sd*math.sqrt(252)):+.2f}")

# real weekly rows: attach factors on the rr calendar (d1 = next row's d0)
for i, r in enumerate(rr[:-1]):
    d0, d1 = r['d0'], rr[i + 1]['d0']
    r['d1'] = d1
    S, TQ, QL, X, cash = r['legs']
    qtr = r['bench_qqq'] + QQQ_DIV_PA / 100 / 52       # QQQ price + dividend accrual
    r['MKT_NDX'] = qtr - cash
    r['MKT_SPX'] = SPY_TR[d1] / SPY_TR[d0] - 1 - cash
    r['LEV'] = TQ - 3 * qtr + 2 * cash                 # REAL TQQQ decay + financing
    r['LEV2'] = QL - 2 * qtr + cash
    r['XLUX'] = X - 0.5 * qtr - 0.5 * cash
    r['SPMOX'] = S - (SPY_TR[d1] / SPY_TR[d0] - 1)     # SPMO minus SPY: real momentum-style excess
    r['cash'] = cash
    r['MOM'] = ff_between(d0, d1, MOM) if d1 <= FF_END else None
RR = rr[:-1]
RREG = [r for r in RR if r['MOM'] is not None]
print(f"real weeks {len(RR)} ({RR[0]['d0']}..{RR[-1]['d0']}), with French data {len(RREG)}; "
      f"corr(weekly MOM, SPMO-SPY) = {corr([r['MOM'] for r in RREG], [r['SPMOX'] for r in RREG]):+.3f}")


# ------------------------------------------------------------------ linear algebra
def solve(A, b):
    n = len(A); M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda i: abs(M[i][c])); M[c], M[p] = M[p], M[c]
        for i in range(n):
            if i != c:
                f = M[i][c] / M[c][c]
                for j in range(c, n + 1): M[i][j] -= f * M[c][j]
    return [M[i][n] / M[i][i] for i in range(n)]


def inv(A):
    n = len(A); cols = [solve(A, [1.0 if i == j else 0.0 for i in range(n)]) for j in range(n)]
    return [[cols[j][i] for j in range(n)] for i in range(n)]


def ols(y, X, lag=NW_LAG):
    """OLS with intercept; Newey-West (Bartlett) HAC standard errors."""
    n = len(y); k = len(X[0]) + 1
    Z = [[1.0] + list(x) for x in X]
    XtX = [[sum(Z[t][i] * Z[t][j] for t in range(n)) for j in range(k)] for i in range(k)]
    Xty = [sum(Z[t][i] * y[t] for t in range(n)) for i in range(k)]
    b = solve(XtX, Xty)
    u = [y[t] - sum(b[i] * Z[t][i] for i in range(k)) for t in range(n)]
    ybar = sum(y) / n; r2 = 1 - sum(e * e for e in u) / sum((v - ybar) ** 2 for v in y)
    S = [[0.0] * k for _ in range(k)]
    for l in range(0, lag + 1):
        w = 1.0 if l == 0 else 1 - l / (lag + 1)
        for t in range(l, n):
            uu = u[t] * u[t - l] * w
            for i in range(k):
                zi = Z[t][i] * uu
                for j in range(k):
                    v = zi * Z[t - l][j]
                    S[i][j] += v
                    if l: S[j][i] += v
    Vi = inv(XtX)
    V = [[sum(Vi[i][a] * S[a][c] * Vi[c][j] for a in range(k) for c in range(k)) for j in range(k)] for i in range(k)]
    se = [math.sqrt(max(V[i][i], 0)) for i in range(k)]
    return b, se, r2, u


def ann(x, per):      # annualised simple mean, pp/yr
    return sum(x) / len(x) * per * 100


def logret(x, per):
    return sum(math.log1p(v) for v in x) * per / len(x) * 100


def sharpe(x, per):
    n = len(x); m = sum(x) / n; sd = math.sqrt(sum((v - m) ** 2 for v in x) / (n - 1))
    return m * per / (sd * math.sqrt(per)) if sd > 0 else 0.0


def cagr(x, per):
    nav = 1.0
    for v in x: nav *= 1 + v
    return (nav ** (per / len(x)) - 1) * 100


def block_ci(x, per, nboot, block, seed, fn=None):
    """Circular block bootstrap CI of an annualised mean (default) or fn(sample) of one series."""
    rng = random.Random(seed); n = len(x); nb = math.ceil(n / block); out = []
    for _ in range(nboot):
        s = []
        for _ in range(nb):
            st = rng.randrange(n); s.extend(x[(st + k) % n] for k in range(block))
        s = s[:n]
        out.append(ann(s, per) if fn is None else fn(s))
    out.sort(); lo, hi = int(0.025 * nboot), int(0.975 * nboot) - 1
    return out[lo], out[hi], sum(1 for v in out if v <= 0) / nboot


def alpha_block_ci(y, X, per, nboot=400, block=60, seed=SEED):
    rng = random.Random(seed); n = len(y); nb = math.ceil(n / block); out = []
    for _ in range(nboot):
        idx = []
        for _ in range(nb):
            st = rng.randrange(n); idx.extend((st + k) % n for k in range(block))
        idx = idx[:n]
        b, _, _, _ = ols([y[i] for i in idx], [X[i] for i in idx], lag=0)
        out.append(b[0] * per * 100)
    out.sort(); lo, hi = int(0.025 * nboot), int(0.975 * nboot) - 1
    return out[lo], out[hi], sum(1 for v in out if v <= 0) / nboot


# ------------------------------------------------------------------ 1. static attribution
print("\n" + "=" * 100 + "\n1. STATIC ATTRIBUTION -- daily excess return regressed on return sources (OLS, Newey-West %d lags)" % NW_LAG)
print("   alpha in pp/yr (simple mean x 252); [] = Newey-West 95%% CI; {} = 60d block-bootstrap 95%% CI (400 draws, main model only)")
MODELS = [('NDX only', ['MKT_NDX']),
          ('NDX+SPX+MOM', ['MKT_NDX', 'MKT_SPX', 'MOM']),
          ('NDX+SPX+MOM+LEV', ['MKT_NDX', 'MKT_SPX', 'MOM', 'LEV']),
          ('NDX+MOM+SMB+HML+LEV', ['MKT_NDX', 'MOM', 'SMB', 'HML', 'LEV'])]
SERIES = {}
set_cost(LIVE_BP)
for lab, fn in (('LIVE', live_fn), ('base allocations only', base_fn), ('QQQ buy-and-hold', qqq_fn)):
    rets, ws, costs = run_w(rows, fn)
    SERIES[lab] = dict(rets=rets, ws=ws, costs=costs)
SERIES['SPY buy-and-hold'] = dict(rets=[r['MKT_SPX'] + r['cash'] for r in rows], ws=None, costs=None)
# LIVE with the EXACT leverage decay/financing cost of its TQQQ/QLD holdings added back (w1*LEV + w2*LEV2), so the
# regression need not estimate a beta on the near-constant LEV series (which is collinear with the intercept)
SERIES['LIVE net of exact LEV cost'] = dict(rets=[x - (w[1] * r['LEV'] + w[2] * r['LEV2']) for x, w, r in zip(SERIES['LIVE']['rets'], SERIES['LIVE']['ws'], rows)], ws=None, costs=None)
print("   NOTE: LEV has vol 0.1%/yr -- as a regressor it is nearly collinear with the intercept; treat the +LEV models as robustness only.")
ERAS = [('full', lambda r: True), ('search 2015-11+', lambda r: r['d'] >= SEARCH[0]), ('holdout 2000-07..2015-10', lambda r: r['d'] <= HOLDOUT[1])]
STATIC = {}
for lab in ('LIVE', 'LIVE net of exact LEV cost', 'base allocations only', 'QQQ buy-and-hold', 'SPY buy-and-hold'):
    ser = SERIES[lab]['rets']
    for elab, ef in ERAS:
        idx = [i for i, r in enumerate(rows) if r['MOM'] is not None and ef(r)]
        y = [ser[i] - rows[i]['cash'] for i in idx]
        for mlab, cols in MODELS:
            X = [[rows[i][c] for c in cols] for i in idx]
            b, se, r2, u = ols(y, X)
            a = b[0] * 252 * 100; ase = se[0] * 252 * 100
            line = f"{lab:<27} {elab:<26} {mlab:<18} R2 {r2:.3f}  alpha {a:+6.2f} [{a-1.96*ase:+6.2f},{a+1.96*ase:+6.2f}]"
            if lab in ('LIVE', 'LIVE net of exact LEV cost') and mlab in (MODELS[1][0], MODELS[2][0]):
                lo, hi, p = alpha_block_ci(y, X, 252)
                line += f" {{{lo:+6.2f},{hi:+6.2f}}} P(<=0)={p:.3f}"
            line += "  betas " + " ".join(f"{c} {b[j+1]:+.3f}({se[j+1]:.3f})" for j, c in enumerate(cols))
            print("  " + line)
            STATIC[(lab, elab, mlab)] = dict(alpha=a, se=ase, r2=r2, betas=dict(zip(cols, b[1:])))

# same on the real weekly rows, with the real momentum series
print("\n   REAL weekly SPMO rows (%d weeks with French data), weekly x 52:" % len(RREG))
rr_live = real_w(RR, live_fn_real)
RMODELS = [('NDX only', ['MKT_NDX']), ('NDX+SPX+MOM+LEV', ['MKT_NDX', 'MKT_SPX', 'MOM', 'LEV']),
           ('NDX+SPX+(SPMO-SPY)+LEV', ['MKT_NDX', 'MKT_SPX', 'SPMOX', 'LEV'])]
rr_series = {'LIVE (real)': rr_live[0],
             'base allocations only (real)': real_w(RR, lambda r: W[r['state']])[0],
             'QQQ (real)': [r['MKT_NDX'] + r['cash'] for r in RR],
             'SPMO (real core leg)': [r['legs'][0] for r in RR]}
for lab, ser in rr_series.items():
    idx = [i for i, r in enumerate(RR) if r['MOM'] is not None]
    y = [ser[i] - RR[i]['cash'] for i in idx]
    for mlab, cols in RMODELS:
        X = [[RR[i][c] for c in cols] for i in idx]
        b, se, r2, u = ols(y, X, lag=4)
        a = b[0] * 52 * 100; ase = se[0] * 52 * 100
        print(f"  {lab:<30} {mlab:<24} R2 {r2:.3f}  alpha {a:+6.2f} [{a-1.96*ase:+6.2f},{a+1.96*ase:+6.2f}]  betas "
              + " ".join(f"{c} {b[j+1]:+.3f}({se[j+1]:.3f})" for j, c in enumerate(cols)))


# ------------------------------------------------------------------ 2. exposure-matched passive
def decompose(rows_, rets, ws, costs, per, ebar=None, lag=1):
    """Exact decomposition of the strategy return around an exposure-matched passive.
    e_t = held weights . BETA.  P_path_t = e_{t-lag} MKT_t + cash_t (known ex ante).
    LIVE - P_path0 (contemporaneous e_t) == LEV + LEV2 + XLU + CORE - COST exactly (CORE = core leg minus QQQ TR, 0 on the proxy).
    LIVE - P_path  == that + LAG, LAG = (e_t - e_{t-lag}) MKT_t."""
    e = [sum(w[j] * BETA[j] for j in range(5)) for w in ws]
    if ebar is None: ebar = sum(e) / len(e)
    out = dict(e=e, ebar=ebar, live=rets, cash=[r['cash'] for r in rows_])
    out['p_avg'] = [ebar * r['MKT_NDX'] + r['cash'] for r in rows_]
    out['p_path'] = [e[max(i - lag, 0)] * r['MKT_NDX'] + r['cash'] for i, r in enumerate(rows_)]
    out['p_path0'] = [e[i] * r['MKT_NDX'] + r['cash'] for i, r in enumerate(rows_)]
    out['lev'] = [w[1] * r['LEV'] + w[2] * r['LEV2'] for w, r in zip(ws, rows_)]
    out['xlu'] = [w[3] * r['XLUX'] for w, r in zip(ws, rows_)]
    out['core'] = [w[0] * (r['legs'][0] - r['MKT_NDX'] - r['cash']) for w, r in zip(ws, rows_)]   # core leg vs QQQ TR: 0 on the proxy, SPMO-vs-QQQ on rr
    out['cost'] = costs
    out['lag'] = [(e[i] - e[max(i - lag, 0)]) * r['MKT_NDX'] for i, r in enumerate(rows_)]
    out['resid'] = [a - b for a, b in zip(rets, out['p_path'])]
    out['timing'] = [a - b for a, b in zip(out['p_path'], out['p_avg'])]
    chk = max(abs(out['resid'][i] - (out['lev'][i] + out['xlu'][i] + out['lag'][i] + out['core'][i] - costs[i])) for i in range(len(rets)))
    assert chk < 1e-12, chk
    return out


def sub(dc, idx):
    return {k: ([v[i] for i in idx] if isinstance(v, list) else v) for k, v in dc.items()}


print("\n" + "=" * 100 + "\n2. EXPOSURE-MATCHED PASSIVE.  e_t = held weights . (1, 3, 2, 0.5, 0);  passive = e_{t-1} x MKT_NDX + cash")
print("   residual = LIVE - passive  ==  LEV(decay+financing) + XLU selection + one-day lag term - costs   (exact identity, asserted)")
L = SERIES['LIVE']; DEC = decompose(rows, L['rets'], L['ws'], L['costs'], 252)
print(f"   average exposure e-bar = {DEC['ebar']:.3f}  (deployed capital {ev['risky']*100:.1f}%);  e range [{min(DEC['e']):.2f}, {max(DEC['e']):.2f}]")
hdr = f"   {'era':<28}{'N':>6}{'LIVE xs':>9}{'P_avg xs':>10}{'P_path xs':>10}{'timing(b)':>11}{'resid(c)':>10}{'  = LEV':>8}{'+XLU':>7}{'+LAG':>7}{'-COST':>7} | resid Sharpe  boot CI(20d)      P    CI(60d)         P"
print(hdr)
RES2 = {}
for elab, ef in ERAS + [('2000-07..2009', lambda r: r['d'] < '2010'), ('2010..2019', lambda r: '2010' <= r['d'] < '2020'), ('2020..2026', lambda r: r['d'] >= '2020')]:
    idx = [i for i, r in enumerate(rows) if ef(r)]
    d = sub(DEC, idx); ebar = sum(d['e']) / len(d['e'])
    d['p_avg'] = [ebar * rows[i]['MKT_NDX'] + rows[i]['cash'] for i in idx]
    d['timing'] = [a - b for a, b in zip(d['p_path'], d['p_avg'])]
    xs = lambda k: ann([a - c for a, c in zip(d[k], d['cash'])], 252)
    l20 = boot(d['live'], d['p_path'], 20, SEED); l60 = boot(d['live'], d['p_path'], 60, SEED + 1)
    print(f"   {elab:<28}{len(idx):>6}{xs('live'):>+9.2f}{xs('p_avg'):>+10.2f}{xs('p_path'):>+10.2f}{ann(d['timing'],252):>+11.2f}{ann(d['resid'],252):>+10.2f}"
          f"{ann(d['lev'],252):>+8.2f}{ann(d['xlu'],252):>+7.2f}{ann(d['lag'],252):>+7.2f}{-ann(d['cost'],252):>+7.2f} | "
          f"{sharpe(d['resid'],252):+6.2f}  [{l20[0]*100:+5.2f},{l20[1]*100:+5.2f}] {l20[2]:.3f}  [{l60[0]*100:+5.2f},{l60[1]*100:+5.2f}] {l60[2]:.3f}")
    RES2[elab] = dict(n=len(idx), ebar=ebar, live=xs('live'), pavg=xs('p_avg'), ppath=xs('p_path'), timing=ann(d['timing'], 252),
                      resid=ann(d['resid'], 252), lev=ann(d['lev'], 252), xlu=ann(d['xlu'], 252), lag=ann(d['lag'], 252), cost=ann(d['cost'], 252),
                      rsh=sharpe(d['resid'], 252), ci20=l20, ci60=l60)
print("   'boot CI' = block bootstrap of the LIVE-minus-passive annualised log-return (block_bootstrap.boot, 2000 draws), P = P(<=0)")
print("   Sharpe of LIVE vs the passive path (paired bootstrap, Sharpe difference):")
for elab in ('full', 'search 2015-11+', 'holdout 2000-07..2015-10'):
    idx = [i for i, r in enumerate(rows) if dict(ERAS)[elab](r)]; d = sub(DEC, idx)
    l = RES2[elab]['ci20']; l6 = RES2[elab]['ci60']
    print(f"     {elab:<28} Sharpe LIVE {sharpe(d['live'],252):.3f}  P_path {sharpe(d['p_path'],252):.3f}  P_avg {sharpe(d['p_avg'],252):.3f}  "
          f"dSharpe(LIVE-P_path) CI20 [{l[3]:+.3f},{l[4]:+.3f}] P {l[5]:.3f}  CI60 [{l6[3]:+.3f},{l6[4]:+.3f}] P {l6[5]:.3f}")

# the timing term (b) itself: passive path vs constant-exposure passive
print("\n   TIMING TERM (b) = P_path - P_avg: does the exposure PATH beat the same average exposure held constantly?")
for elab, ef in ERAS:
    idx = [i for i, r in enumerate(rows) if ef(r)]; d = sub(DEC, idx); ebar = sum(d['e']) / len(d['e'])
    d['p_avg'] = [ebar * rows[i]['MKT_NDX'] + rows[i]['cash'] for i in idx]
    b20 = boot(d['p_path'], d['p_avg'], 20, SEED + 2); b60 = boot(d['p_path'], d['p_avg'], 60, SEED + 3)
    print(f"     {elab:<28} e-bar {ebar:.3f}  (b) {ann([a-b for a,b in zip(d['p_path'],d['p_avg'])],252):+6.2f} pp/yr  "
          f"log-return CI20 [{b20[0]*100:+5.2f},{b20[1]*100:+5.2f}] P {b20[2]:.3f}  CI60 [{b60[0]*100:+5.2f},{b60[1]*100:+5.2f}] P {b60[2]:.3f}  "
          f"dSharpe CI60 [{b60[3]:+.3f},{b60[4]:+.3f}] P {b60[5]:.3f}")

# 2b. how fast does the timing value decay with execution delay?  (b) at lags 0..10 sessions
print("\n   TIMING TERM vs EXECUTION DELAY: (b) = P_path(lag k) - P_avg, pp/yr, with 60d-block bootstrap P(<=0) in brackets")
print(f"     {'era':<28}" + "".join(f"{'lag '+str(k):>16}" for k in (0, 1, 2, 3, 5, 10)))
for elab, ef in ERAS:
    idx = [i for i, r in enumerate(rows) if ef(r)]; e = [DEC['e'][i] for i in idx]; ebar = sum(e) / len(e)
    pav = [ebar * rows[i]['MKT_NDX'] + rows[i]['cash'] for i in idx]; cells = []
    for k in (0, 1, 2, 3, 5, 10):
        pp = [e[max(j - k, 0)] * rows[i]['MKT_NDX'] + rows[i]['cash'] for j, i in enumerate(idx)]
        bb = boot(pp, pav, 60, SEED + 10 + k)
        cells.append(f"{ann([a-b for a,b in zip(pp,pav)],252):>+7.2f} [{bb[2]:.3f}]")
    print(f"     {elab:<28}" + "".join(f"{c:>16}" for c in cells))

# 2c. where does the timing come from: the same decomposition for simpler designs (all through run_w, 4bp)
print("\n   TIMING TERM BY DESIGN (lag 1, pp/yr): which rule produces the exposure timing?")
DESIGNS = [('base allocations only (no VT)', base_fn),
           ('base + vol target', lambda r: vt(W[r['state']], r['vol_live'])),
           ('base + fast overlay + VT', lambda r: vt(W[r['eff']], r['vol_live'])),
           ('base + trim + VT', lambda r: vt(trimmed_w(W[r['state']], r['state'], r['gaps']), r['vol_live'])),
           ('LIVE', live_fn)]
def trimmed_w(w, s, gaps):
    f = extension_scale(s, gaps)
    return w if f >= 1 else tuple(x * f for x in w[:4]) + (1 - f * sum(w[:4]),)
print(f"     {'design':<32}{'era':<26}{'e-bar':>6}{'LIVE xs':>9}{'P_avg xs':>9}{'(b)':>8}{'P(b<=0)':>9}{'(c)':>8}{'Sharpe':>8}{'Sh P_path':>10}")
for dlab, dfn in DESIGNS:
    rets_, ws_, costs_ = run_w(rows, dfn); dd = decompose(rows, rets_, ws_, costs_, 252)
    for elab, ef in ERAS:
        idx = [i for i, r in enumerate(rows) if ef(r)]; d = sub(dd, idx); ebar = sum(d['e']) / len(d['e'])
        d['p_avg'] = [ebar * rows[i]['MKT_NDX'] + rows[i]['cash'] for i in idx]
        bb = boot(d['p_path'], d['p_avg'], 60, SEED + 20)
        print(f"     {dlab:<32}{elab:<26}{ebar:>6.2f}{ann([a-c for a,c in zip(d['live'],d['cash'])],252):>+9.2f}{ann([a-c for a,c in zip(d['p_avg'],d['cash'])],252):>+9.2f}"
              f"{ann([a-b for a,b in zip(d['p_path'],d['p_avg'])],252):>+8.2f}{bb[2]:>9.3f}{ann(d['resid'],252):>+8.2f}{sharpe(d['live'],252):>8.3f}{sharpe(d['p_path'],252):>10.3f}")

# real rows
print("\n   REAL weekly rows (same decomposition, weights = RF.eval_real's, exposure lagged one week):")
RDEC = decompose(RR, rr_live[0], rr_live[1], rr_live[2], 52)
xs = lambda k: ann([a - c for a, c in zip(RDEC[k], RDEC['cash'])], 52)
b20 = boot(RDEC['live'], RDEC['p_path'], 4, SEED); b60 = boot(RDEC['live'], RDEC['p_path'], 12, SEED + 1)
t20 = boot(RDEC['p_path'], RDEC['p_avg'], 4, SEED + 2); t60 = boot(RDEC['p_path'], RDEC['p_avg'], 12, SEED + 3)
print(f"     N {len(RR)}  e-bar {RDEC['ebar']:.3f}  LIVE xs {xs('live'):+.2f}  P_avg xs {xs('p_avg'):+.2f}  P_path xs {xs('p_path'):+.2f}  "
      f"timing(b) {ann(RDEC['timing'],52):+.2f}  resid(c) {ann(RDEC['resid'],52):+.2f} = LEV {ann(RDEC['lev'],52):+.2f} + XLU {ann(RDEC['xlu'],52):+.2f} "
      f"+ LAG {ann(RDEC['lag'],52):+.2f} + SPMO-vs-QQQ core {ann(RDEC['core'],52):+.2f} - COST {ann(RDEC['cost'],52):.2f}")
print(f"     resid Sharpe {sharpe(RDEC['resid'],52):+.2f}; LIVE-P_path log-ret CI(4w) [{b20[0]*100:+.2f},{b20[1]*100:+.2f}] P {b20[2]:.3f}, "
      f"(12w) [{b60[0]*100:+.2f},{b60[1]*100:+.2f}] P {b60[2]:.3f};  timing(b) CI(4w) [{t20[0]*100:+.2f},{t20[1]*100:+.2f}] P {t20[2]:.3f}, "
      f"(12w) [{t60[0]*100:+.2f},{t60[1]*100:+.2f}] P {t60[2]:.3f}")
RES2['real'] = dict(n=len(RR), ebar=RDEC['ebar'], live=xs('live'), pavg=xs('p_avg'), ppath=xs('p_path'), timing=ann(RDEC['timing'], 52),
                    resid=ann(RDEC['resid'], 52), lev=ann(RDEC['lev'], 52), xlu=ann(RDEC['xlu'], 52), lag=ann(RDEC['lag'], 52),
                    cost=ann(RDEC['cost'], 52), rsh=sharpe(RDEC['resid'], 52), ci20=b20, ci60=b60, t20=t20, t60=t60)
# real: the core leg is SPMO, not QQQ -- separate the SPMO-vs-QQQ selection out of the residual
print(f"     [real LEV uses the REAL TQQQ/QLD legs, so it carries their tracking error too; identity LEV+XLU+LAG+CORE-COST asserted exactly]")


# ------------------------------------------------------------------ 3. style-regime buckets
print("\n" + "=" * 100 + "\n3. STYLE-REGIME BUCKETS (daily rows; regimes are calendar-quarter statistics, contemporaneous, quintiles/terciles over quarters)")
print("   columns: pp/yr = annualised mean within bucket; 'share' = bucket's share of the full-sample SUM of that term")
Q = {}
for i, r in enumerate(rows):
    q = r['d'][:4] + 'Q' + str((int(r['d'][5:7]) - 1) // 3 + 1)
    Q.setdefault(q, []).append(i)
qstat = {}
for q, idx in Q.items():
    mom = [rows[i]['MOM'] for i in idx if rows[i]['MOM'] is not None]
    rel = [rows[i]['MKT_NDX'] - rows[i]['MKT_SPX'] for i in idx]
    mk = [rows[i]['MKT_NDX'] for i in idx]
    qstat[q] = dict(mom=(sum(mom) if mom else None), rel=sum(rel), vol=math.sqrt(sum(x * x for x in mk) / len(mk) * 252), mkt=sum(mk))


def quantile_buckets(key, nq, names):
    qs = [q for q in Q if qstat[q][key] is not None]
    qs.sort(key=lambda q: qstat[q][key]); out = {}
    for j, q in enumerate(qs):
        out[q] = names[min(j * nq // len(qs), nq - 1)]
    return out


def bucket_table(title, qmap, order, per_row_key=None):
    print(f"\n   {title}")
    print(f"   {'bucket':<22}{'N':>6}{'e-bar':>7}{'MKT_NDX':>9}{'LIVE xs':>9}{'P_avg xs':>10}{'P_path xs':>10}{'timing(b)':>11}{'resid(c)':>10}{'LEV':>7}{'LAG':>7} | share of: (b) {'':>3} (c)")
    tot_b = sum(DEC['timing']); tot_c = sum(DEC['resid'])
    for name in order:
        if per_row_key:
            idx = [i for i, r in enumerate(rows) if r[per_row_key] == name]
        else:
            idx = [i for q, b in qmap.items() if b == name for i in Q[q]]
        if not idx: continue
        d = sub(DEC, idx)
        xs = lambda k: ann([a - c for a, c in zip(d[k], d['cash'])], 252)
        print(f"   {name:<22}{len(idx):>6}{sum(d['e'])/len(idx):>7.2f}{ann([rows[i]['MKT_NDX'] for i in idx],252):>+9.1f}{xs('live'):>+9.1f}{xs('p_avg'):>+10.1f}{xs('p_path'):>+10.1f}"
              f"{ann(d['timing'],252):>+11.1f}{ann(d['resid'],252):>+10.1f}{ann(d['lev'],252):>+7.1f}{ann(d['lag'],252):>+7.1f} | "
              f"{sum(d['timing'])/tot_b*100:>+6.0f}%  {sum(d['resid'])/tot_c*100:>+6.0f}%")


QN = ['Q1 (lowest)', 'Q2', 'Q3', 'Q4', 'Q5 (highest)']
bucket_table("(i) Fama-French MOMENTUM factor, quarterly return quintile  (Q5 = momentum works best)", quantile_buckets('mom', 5, QN), QN)
bucket_table("(ii) NASDAQ vs S&P relative performance (MKT_NDX - MKT_SPX), quarterly quintile  (Q5 = Nasdaq beats S&P most)", quantile_buckets('rel', 5, QN), QN)
TN = ['T1 (low vol)', 'T2', 'T3 (high vol)']
bucket_table("(iii) realised QQQ vol, quarterly tercile", quantile_buckets('vol', 3, TN), TN)
MN = ['M1 (worst)', 'M2', 'M3', 'M4', 'M5 (best)']
bucket_table("(iv-a) market direction: MKT_NDX quarterly quintile (the leverage-timing view)", quantile_buckets('mkt', 5, MN), MN)
bucket_table("(iv-b) macro state (50/200 classifier, daily)", None, ['A', 'B', 'C', 'D', 'E', 'F'], per_row_key='state')
bucket_table("(iv-c) effective state after the fast overlay", None, ['A', 'B', 'C', 'D', 'E', 'F'], per_row_key='eff')
# momentum x live: is LIVE's alpha different in good vs bad momentum quarters?  (regression alpha by MOM half)
mq = quantile_buckets('mom', 2, ['low MOM half', 'high MOM half'])
print("\n   regression alpha (NDX+SPX+MOM+LEV) of LIVE inside momentum halves and Nasdaq-vs-S&P halves:")
for lab, qm in (('MOM', mq), ('NDX-SPX', quantile_buckets('rel', 2, ['low NDX-SPX half', 'high NDX-SPX half']))):
    for name in sorted(set(qm.values())):
        idx = [i for q, b in qm.items() if b == name for i in Q[q] if rows[i]['MOM'] is not None]
        y = [L['rets'][i] - rows[i]['cash'] for i in idx]; X = [[rows[i][c] for c in MODELS[1][1]] for i in idx]
        b, se, r2, _ = ols(y, X)
        print(f"     {name:<22} N {len(idx):>5}  alpha {b[0]*252*100:+6.2f} [{(b[0]-1.96*se[0])*252*100:+6.2f},{(b[0]+1.96*se[0])*252*100:+6.2f}]  beta_NDX {b[1]:.3f}  beta_MOM {b[3]:+.3f}")


# ------------------------------------------------------------------ 4. rolling
print("\n" + "=" * 100 + "\n4. ROLLING 3-YEAR (756-session) windows ending each year-end; plus that calendar year's own numbers")
print(f"   {'year':<6}{'3y beta':>8}{'3y a1':>7}{'3y a4':>7}{'3y bMOM':>8}{'3y e':>6}{'3y R2':>7} | {'1y beta':>8}{'1y a4':>7}{'1y e':>6}{'LIVE':>7}{'QQQ':>7}{'MOM':>7}{'flag'}")
YEARS = sorted(set(r['d'][:4] for r in rows))
allb = []
ROLL = {}
for y in YEARS:
    end = max(i for i, r in enumerate(rows) if r['d'][:4] == y)
    idx3 = [i for i in range(max(0, end - 755), end + 1) if rows[i]['MOM'] is not None]
    idx1 = [i for i, r in enumerate(rows) if r['d'][:4] == y and r['MOM'] is not None]
    if len(idx3) < 500: continue
    yv = [L['rets'][i] - rows[i]['cash'] for i in idx3]
    b1, se1, r21, _ = ols(yv, [[rows[i]['MKT_NDX']] for i in idx3], lag=0)
    b4, se4, r24, _ = ols(yv, [[rows[i][c] for c in MODELS[1][1]] for i in idx3], lag=0)
    y1 = [L['rets'][i] - rows[i]['cash'] for i in idx1]
    c1, _, _, _ = ols(y1, [[rows[i]['MKT_NDX']] for i in idx1], lag=0)
    c4, _, _, _ = ols(y1, [[rows[i][c] for c in MODELS[1][1]] for i in idx1], lag=0)
    e3 = sum(DEC['e'][i] for i in idx3) / len(idx3); e1 = sum(DEC['e'][i] for i in idx1) / len(idx1)
    ROLL[y] = dict(beta=b1[1], a1=b1[0] * 252 * 100, a4=b4[0] * 252 * 100, bmom=b4[3], e=e3, r2=r24, beta1=c1[1], a41=c4[0] * 252 * 100, e1=e1,
                   live=logret([L['rets'][i] for i in idx1], 252), qqq=logret([rows[i]['legs'][0] for i in idx1], 252), mom=logret([rows[i]['MOM'] for i in idx1], 252))
med_beta = sorted(v['beta'] for v in ROLL.values())[len(ROLL) // 2]
for y, v in ROLL.items():
    flag = ''
    if v['a4'] < 0 and v['beta'] > med_beta: flag = 'STYLE-RIDING (alpha<0, beta high)'
    elif v['a4'] > 0 and v['beta'] < med_beta: flag = 'timing (alpha>0, beta low)'
    print(f"   {y:<6}{v['beta']:>8.2f}{v['a1']:>+7.1f}{v['a4']:>+7.1f}{v['bmom']:>+8.2f}{v['e']:>6.2f}{v['r2']:>7.2f} | {v['beta1']:>8.2f}{v['a41']:>+7.1f}{v['e1']:>6.2f}{v['live']:>+7.1f}{v['qqq']:>+7.1f}{v['mom']:>+7.1f}  {flag}")
print(f"   (a1 = single-factor alpha pp/yr; a4 = NDX+SPX+MOM+LEV alpha; e = average realised exposure; median 3y beta {med_beta:.2f})")
print(f"   corr across windows: 3y alpha4 vs 3y beta {corr([v['a4'] for v in ROLL.values()], [v['beta'] for v in ROLL.values()]):+.2f};  "
      f"1y alpha4 vs 1y MOM return {corr([v['a41'] for v in ROLL.values()], [v['mom'] for v in ROLL.values()]):+.2f};  "
      f"1y alpha4 vs 1y QQQ return {corr([v['a41'] for v in ROLL.values()], [v['qqq'] for v in ROLL.values()]):+.2f}")


# ------------------------------------------------------------------ 5. CAGR-gap decomposition
print("\n" + "=" * 100 + "\n5. THREE-WAY DECOMPOSITION OF THE GAP vs QQQ AND vs SPY  (annualised LOG return, pp/yr -- terms add exactly; CAGRs shown alongside)")
print("   gap = [index choice: QQQ - SPY] + (a) average leverage [P_avg - QQQ] + (b) time-varying exposure [P_path - P_avg] + (c) residual [LIVE - P_path]")
print("   (c) = LEV(decay+financing) + XLU selection + one-day lag - costs")
DECOMP = {}
for bp in (0.0004, 0.0010):
    set_cost(bp)
    rets, ws, costs = run_w(rows, live_fn); dfull = decompose(rows, rets, ws, costs, 252)
    for elab, ef in ERAS:
        idx = [i for i, r in enumerate(rows) if ef(r)]; d = sub(dfull, idx); ebar = sum(d['e']) / len(d['e'])
        d['p_avg'] = [ebar * rows[i]['MKT_NDX'] + rows[i]['cash'] for i in idx]
        qq = [rows[i]['legs'][0] for i in idx]; sp = [rows[i]['MKT_SPX'] + rows[i]['cash'] for i in idx]
        lr = lambda k: logret(d[k], 252)
        g_idx = logret(qq, 252) - logret(sp, 252); a = lr('p_avg') - logret(qq, 252); b = lr('p_path') - lr('p_avg'); c = lr('live') - lr('p_path')
        gq = lr('live') - logret(qq, 252); gs = lr('live') - logret(sp, 252)
        DECOMP[(bp, elab)] = dict(ebar=ebar, live=cagr(d['live'], 252), qqq=cagr(qq, 252), spy=cagr(sp, 252), pavg=cagr(d['p_avg'], 252), ppath=cagr(d['p_path'], 252),
                                  g_idx=g_idx, a=a, b=b, c=c, gq=gq, gs=gs)
        lev_c = ann(d['lev'], 252); xlu_c = ann(d['xlu'], 252); lag_c = ann(d['lag'], 252); cost_c = -ann(d['cost'], 252)
        DECOMP[(bp, elab)].update(lev=lev_c, xlu=xlu_c, lag=lag_c, cost=cost_c)
        print(f"   {bp*1e4:.0f}bp {elab:<26} e-bar {ebar:.2f}  CAGR LIVE {cagr(d['live'],252):5.2f} QQQ {cagr(qq,252):5.2f} SPY {cagr(sp,252):5.2f} P_avg {cagr(d['p_avg'],252):5.2f} P_path {cagr(d['p_path'],252):5.2f}")
        print(f"        vs QQQ gap {gq:+6.2f} = (a) {a:+6.2f} ({a/gq*100 if gq else 0:+4.0f}%) + (b) {b:+6.2f} ({b/gq*100 if gq else 0:+4.0f}%) + (c) {c:+6.2f} ({c/gq*100 if gq else 0:+4.0f}%)"
              f"   [(c): LEV {lev_c:+.2f}, XLU {xlu_c:+.2f}, lag {lag_c:+.2f}, cost {cost_c:+.2f}; simple-mean terms]")
        print(f"        vs SPY gap {gs:+6.2f} = index {g_idx:+6.2f} ({g_idx/gs*100:+4.0f}%) + (a) {a:+6.2f} ({a/gs*100:+4.0f}%) + (b) {b:+6.2f} ({b/gs*100:+4.0f}%) + (c) {c:+6.2f} ({c/gs*100:+4.0f}%)")
    # real rows
    rl = real_w(RR, live_fn_real); d = decompose(RR, rl[0], rl[1], rl[2], 52)
    qq = [r['MKT_NDX'] + r['cash'] for r in RR]; sp = [r['MKT_SPX'] + r['cash'] for r in RR]; sm = [r['legs'][0] for r in RR]
    lr = lambda k: logret(d[k], 52)
    g_idx = logret(qq, 52) - logret(sp, 52); a = lr('p_avg') - logret(qq, 52); b = lr('p_path') - lr('p_avg'); c = lr('live') - lr('p_path')
    gq = lr('live') - logret(qq, 52); gs = lr('live') - logret(sp, 52)
    print(f"   {bp*1e4:.0f}bp REAL weekly {'':<15} e-bar {d['ebar']:.2f}  CAGR LIVE {cagr(d['live'],52):5.2f} QQQ {cagr(qq,52):5.2f} SPY {cagr(sp,52):5.2f} SPMO {cagr(sm,52):5.2f} P_avg {cagr(d['p_avg'],52):5.2f} P_path {cagr(d['p_path'],52):5.2f}")
    print(f"        vs QQQ gap {gq:+6.2f} = (a) {a:+6.2f} + (b) {b:+6.2f} + (c) {c:+6.2f}   [(c): LEV {ann(d['lev'],52):+.2f}, XLU {ann(d['xlu'],52):+.2f}, lag {ann(d['lag'],52):+.2f}, cost {-ann(d['cost'],52):+.2f}, SPMO-vs-QQQ core {ann(d['core'],52):+.2f}]")
    print(f"        vs SPY gap {gs:+6.2f} = index {g_idx:+6.2f} + (a) {a:+6.2f} + (b) {b:+6.2f} + (c) {c:+6.2f}")
    DECOMP[(bp, 'real')] = dict(ebar=d['ebar'], live=cagr(d['live'], 52), qqq=cagr(qq, 52), spy=cagr(sp, 52), g_idx=g_idx, a=a, b=b, c=c, gq=gq, gs=gs)
set_cost(LIVE_BP)


# ------------------------------------------------------------------ 6. placebo
print("\n" + "=" * 100 + "\n6. PLACEBO: the exposure PATH with its timing destroyed -- same exposure values, same average, random placement")
print("   (i) calendar-year blocks permuted; (ii) 60-session circular blocks resampled.  Statistic: P_path annualised log return and Sharpe.")
print("   P = fraction of placebo paths at least as good as the actual path (one-sided).  1000 draws each.")


def passive_of(e_seq, idx, lag=1):
    return [e_seq[max(k - lag, 0)] * rows[i]['MKT_NDX'] + rows[i]['cash'] for k, i in enumerate(idx)]


def placebo(idx, nboot=1000, seed=SEED):
    e = [DEC['e'][i] for i in idx]
    act = passive_of(e, idx); a_lr = logret(act, 252); a_sh = sharpe(act, 252)
    yrs = {}
    for k, i in enumerate(idx): yrs.setdefault(rows[i]['d'][:4], []).append(k)
    segs = [[e[k] for k in v] for v in yrs.values()]
    rng = random.Random(seed); out = {'year': ([], []), 'block60': ([], [])}
    n = len(e)
    for _ in range(nboot):
        order = segs[:]; rng.shuffle(order); es = [x for s in order for x in s]
        p = passive_of(es, idx); out['year'][0].append(logret(p, 252)); out['year'][1].append(sharpe(p, 252))
        es = []
        while len(es) < n:
            st = rng.randrange(n); es.extend(e[(st + k) % n] for k in range(60))
        p = passive_of(es[:n], idx); out['block60'][0].append(logret(p, 252)); out['block60'][1].append(sharpe(p, 252))
    res = {}
    for k, (lrs, shs) in out.items():
        lrs.sort(); shs.sort()
        res[k] = dict(lr_med=lrs[len(lrs) // 2], lr_lo=lrs[int(0.025 * nboot)], lr_hi=lrs[int(0.975 * nboot) - 1], p_lr=sum(1 for v in lrs if v >= a_lr) / nboot,
                      sh_med=shs[len(shs) // 2], sh_lo=shs[int(0.025 * nboot)], sh_hi=shs[int(0.975 * nboot) - 1], p_sh=sum(1 for v in shs if v >= a_sh) / nboot)
    return a_lr, a_sh, res


PLAC = {}
for elab, ef in ERAS:
    idx = [i for i, r in enumerate(rows) if ef(r)]
    a_lr, a_sh, res = placebo(idx)
    PLAC[elab] = (a_lr, a_sh, res)
    print(f"   {elab:<26} actual P_path: log-ret {a_lr:+6.2f} pp/yr, Sharpe {a_sh:.3f}")
    for k, v in res.items():
        print(f"      {k:<8} placebo log-ret median {v['lr_med']:+6.2f} [{v['lr_lo']:+6.2f},{v['lr_hi']:+6.2f}]  P(placebo>=actual) {v['p_lr']:.3f}   "
              f"Sharpe median {v['sh_med']:.3f} [{v['sh_lo']:.3f},{v['sh_hi']:.3f}]  P {v['p_sh']:.3f}")
# LIVE itself against placebo passive paths (adds the residual back on top): residual of LIVE vs the placebo distribution
print("   LIVE (with its residual) vs the placebo passive distribution:")
for elab, ef in ERAS:
    idx = [i for i, r in enumerate(rows) if ef(r)]
    lv = logret([L['rets'][i] for i in idx], 252); ls = sharpe([L['rets'][i] for i in idx], 252)
    a_lr, a_sh, res = PLAC[elab]
    print(f"      {elab:<26} LIVE log-ret {lv:+6.2f} Sharpe {ls:.3f}  vs year-placebo median {res['year']['lr_med']:+6.2f}/{res['year']['sh_med']:.3f}  "
          f"P(placebo log-ret >= LIVE) ~ {'<' if lv > res['year']['lr_hi'] else '>'}0.025;  LIVE - placebo median = {lv-res['year']['lr_med']:+.2f} pp/yr")

# sign-flip placebo on the timing term: exposure path mirrored around its mean
print("   sign-flip: exposure path mirrored around e-bar (2e-bar - e_t): a real timing signal must LOSE")
for elab, ef in ERAS:
    idx = [i for i, r in enumerate(rows) if ef(r)]; e = [DEC['e'][i] for i in idx]; eb = sum(e) / len(e)
    act = passive_of(e, idx); flip = passive_of([2 * eb - x for x in e], idx); const = [eb * rows[i]['MKT_NDX'] + rows[i]['cash'] for i in idx]
    print(f"      {elab:<26} actual {logret(act,252):+6.2f}/{sharpe(act,252):.3f}   flipped {logret(flip,252):+6.2f}/{sharpe(flip,252):.3f}   constant e-bar {logret(const,252):+6.2f}/{sharpe(const,252):.3f}")

print(f"\ndone in {time.time()-T0:.0f}s")
