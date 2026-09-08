"""RESEARCH LINE `vrp_signal` (2026-09-08): the variance risk premium as a
TIME-VARYING signal. Research only -- nothing here is applied (change freeze
until 2026-12-07).

Today the project used VXN minus QQQ realized vol as ONE CONSTANT (+2.66 vol
points) to rescale an estimator. It never used it as a series. The
Bollerslev-Tauchen-Zhou mechanism: when implied vol runs far above realized,
options are expensive, fear is priced, forward returns have historically been
better; when implied drops BELOW realized, the market is under-pricing risk
that is actually happening. That is a different quantity from vol level, vol
change or vol trend, all of which failed today.

SERIES (causal, daily, attached to rows by date):
    vrp_t = IV_t - realized_vol(underlying, as_of=t, lookback=L)
    defs: q30 = VXN - rv(QQQ,30)   q21 = VXN - rv(QQQ,21)   q10 = VXN - rv(QQQ,10)
          s30 = VIX - rv(SPY,30)   (the S&P side, for the SPMO core leg)
    FRED holidays forward-filled (never dropped). Both legs annualised
    fractions (VXN/100).
THRESHOLDS: trailing 252-session quantiles of the daily series (inclusive of
    today, so causal), plus an expanding-window variant. Never fitted on an
    era.
ROWS: VXN starts 2001-02-02 and the trailing window needs 252 sessions, so
    EVERY variant INCLUDING the live baseline is scored on the same rows,
    first row ~2002-02. Stated in the output.

TESTS
  (a) TILT between core and TQQQ in states A/B at constant deployed capital.
      High VRP -> tilt toward TQQQ, low/negative -> toward core. Sweep delta
      0.10/0.20, thresholds median / 25-75 / zero. Harness: SPY-core proxy
      (srows -- this concerns the S&P core leg), QQQ-core proxy for
      comparison, real weekly SPMO rows rr. Controls: beta-matched live,
      constant-tilt at matched beta, sign-flip.
  (b) MODULATOR of the vol-target multiplier: m = min(1, T/(vol_live * g(vrp)))
      with g > 1 when VRP is negative. T RE-CALIBRATED by bisection so average
      deployed exposure equals live's (perleg_vol_test.py pattern) -- the
      only fair comparison for anything that changes how much risk is held.
      Controls: exposure-matched by construction, sign-flip (g -> 1/g,
      re-calibrated), both-era, real rows.
  (c) DESCRIPTIVE: distribution, autocorrelation, predictive correlation of
      VRP(d0) with QQQ / strategy d0->d1 returns, forward 5/21-day returns by
      VRP quintile (static and causal), by era. This is where the literature
      says the effect lives; it is shown BEFORE (a)/(b) are interpreted.
Survivors (beat live on search AND holdout Sharpe, and beat their matched
control) get the circular block bootstrap (20/60) and leave-one-regime-out.
The total variant count is reported.
"""
import sys, math, csv, bisect
sys.path.insert(0, 'paper-track')
exec(open('paper-track/volgap_test.py').read().split('# ---- IDEA A')[0])
from block_bootstrap import boot, stats, N_BOOT
from long_history_backtest import load_px as _load_px

print("=" * 100)
print("RESEARCH LINE vrp_signal -- variance risk premium as a time-varying signal")
print("=" * 100)

# ---------------------------------------------------------------- 1. series
ds = D['ds']; qpx = D['qqq']
spy_full = _load_px('data/spy_long_history.csv'); spd = sorted(spy_full)
DEFS = {'q30': ('VXN', 'QQQ', 30), 'q21': ('VXN', 'QQQ', 21),
        'q10': ('VXN', 'QQQ', 10), 's30': ('VIX', 'SPY', 30)}
IVS = {'VXN': (VXN, vxk), 'VIX': (VIX, vik)}

RV = {}
for k, (ivn, und, L) in DEFS.items():
    if und == 'QQQ':
        RV[k] = {d: realized_vol(ds, qpx, as_of=d, lookback=L) for d in ds}
    else:
        RV[k] = {d: realized_vol(spd, spy_full, as_of=d, lookback=L) for d in ds}
IVD = {k: {d: prior(*IVS[DEFS[k][0]], d) for d in ds} for k in DEFS}
VRPD = {k: {d: (IVD[k][d] - RV[k][d]) for d in ds
            if IVD[k][d] is not None and RV[k][d] is not None} for k in DEFS}

QS = (0.2, 0.25, 0.4, 0.5, 0.6, 0.75, 0.8)
def quantiles_series(dates, vals, n, expanding=False):
    """Causal trailing (or expanding) quantiles, inclusive of the current
    observation. Returns {date: {q: value}} where a full window exists."""
    out, win = {}, []
    for i, (d, v) in enumerate(zip(dates, vals)):
        bisect.insort(win, v)
        if not expanding and len(win) > n:
            win.pop(bisect.bisect_left(win, vals[i - n]))
        if len(win) >= n:
            out[d] = {q: win[int(round(q * (len(win) - 1)))] for q in QS}
    return out
WINN = 252
THR = {}
for k in DEFS:
    dd = [d for d in ds if d in VRPD[k]]; vv = [VRPD[k][d] for d in dd]
    THR[(k, 't252')] = quantiles_series(dd, vv, WINN)
    THR[(k, 'exp')] = quantiles_series(dd, vv, WINN, expanding=True)
THRK = {key: sorted(m) for key, m in THR.items()}

def attach(rl, key, qdates, qmap, spydates, spymap):
    for r in rl:
        d = r[key]
        r['vrp'], r['iv'], r['rv'], r['thr'] = {}, {}, {}, {}
        for k, (ivn, und, L) in DEFS.items():
            iv = prior(*IVS[ivn], d)
            rv = (realized_vol(qdates, qmap, as_of=d, lookback=L) if und == 'QQQ'
                  else realized_vol(spydates, spymap, as_of=d, lookback=L))
            r['iv'][k], r['rv'][k] = iv, rv
            r['vrp'][k] = (iv - rv) if (iv is not None and rv is not None) else None
            for w in ('t252', 'exp'):
                m = THR[(k, w)]; ks = THRK[(k, w)]
                i = bisect.bisect_right(ks, d) - 1
                r['thr'][(k, w)] = m[ks[i]] if i >= 0 else None
def covered(r):
    return all(r['vrp'][k] is not None for k in DEFS) and \
           all(r['thr'][(k, 't252')] is not None for k in DEFS)

for r in srows: r['vrp'] = None
attach(srows, 'd', ds, qpx, spd, spy_full)
attach(qrows, 'd', ds, qpx, spd, spy_full)
attach(rr, 'd0', qd2, qqqp, spd, spy_full)
P  = [r for r in srows if covered(r)]
PD = set(r['d'] for r in P)
Q  = [r for r in qrows if r['d'] in PD]
Pr = [r for r in rr if covered(r)]
nS = len(era(P, *SEARCH)); nH = len(era(P, *HOLDOUT))
print(f"\nSAME-ROWS RESTRICTION: VXN starts {vxk[0]}; trailing {WINN}-session thresholds need a full window.")
print(f"  proxy rows used {P[0]['d']}..{P[-1]['d']}: {len(P)} of {len(srows)} "
      f"(holdout {nH}, search {nS}); dropped {len(srows)-len(P)} rows 2000-07..{P[0]['d']}")
print(f"  real weekly rows used: {len(Pr)} of {len(rr)} ({Pr[0]['d0']}..{Pr[-1]['d0']})")
print("  every variant below, INCLUDING the live baseline, is scored on exactly these rows.")

# ---------------------------------------------------------------- baselines
LIVE = live_fn(); LIVE_R = live_fn(RF.vt)
base_s = evaluate(P, LIVE); base_q = evaluate(Q, LIVE); base_r = RF.eval_real(Pr, LIVE_R)
live_ser = run(P, LIVE)[0]; live_exp = run(P, LIVE)[1]
beta_live = beta_of(P, LIVE)
def fmt(ev): return f"{ev['cagr']*100:5.2f}/{ev['sharpe']:.3f}/{ev['mdd']*100:5.1f}"
print(f"\nLIVE on same rows -- SPY-core: {fmt(base_s)}  S {base_s['s_sharpe']:.3f} H {base_s['h_sharpe']:.3f}"
      f"  expo {live_exp*100:.2f}% beta {beta_live:.3f}")
print(f"                     QQQ-core: {fmt(base_q)}  S {base_q['s_sharpe']:.3f} H {base_q['h_sharpe']:.3f}")
print(f"                     real wk : {fmt(base_r)}   (standing full-rr figure 30.67/1.260/-25.3)")

# ============================================================ (c) DESCRIPTIVE
print("\n" + "=" * 100)
print("(c) DESCRIPTIVE -- does the VRP effect exist in THIS data?")
print("=" * 100)
def mean(a): return sum(a) / len(a)
def sd(a):
    m = mean(a); return (sum((x - m) ** 2 for x in a) / (len(a) - 1)) ** 0.5
def corr(a, b):
    ma, mb = mean(a), mean(b)
    va = sum((x - ma) ** 2 for x in a); vb = sum((y - mb) ** 2 for y in b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb) if va > 0 and vb > 0 else 0.0
def tcorr(rho, n): return rho * math.sqrt((n - 2) / max(1e-12, 1 - rho * rho))
def pctl(a, q):
    s = sorted(a); return s[int(round(q * (len(s) - 1)))]

print("\nDistribution of the daily VRP series (vol points = x100), all covered dates:")
print(f"  {'def':<5}{'n':>6}{'first':>12}{'mean':>7}{'sd':>6}{'p5':>7}{'p25':>7}{'p50':>7}{'p75':>7}{'p95':>7}{'%neg':>7}")
for k in DEFS:
    dd = [d for d in ds if d in VRPD[k]]; v = [VRPD[k][d] * 100 for d in dd]
    print(f"  {k:<5}{len(v):>6}{dd[0]:>12}{mean(v):>7.2f}{sd(v):>6.2f}{pctl(v,.05):>7.2f}{pctl(v,.25):>7.2f}"
          f"{pctl(v,.5):>7.2f}{pctl(v,.75):>7.2f}{pctl(v,.95):>7.2f}{100*sum(1 for x in v if x<0)/len(v):>6.1f}%")
print("  by era (q30): ", end='')
for lab, (lo, hi) in (('holdout', HOLDOUT), ('search', SEARCH)):
    v = [VRPD['q30'][d] * 100 for d in ds if d in VRPD['q30'] and lo <= d <= hi]
    print(f"{lab} mean {mean(v):+.2f} p50 {pctl(v,.5):+.2f} %neg {100*sum(1 for x in v if x<0)/len(v):.1f}%   ", end='')
print()

print("\nAutocorrelation of the daily VRP series:")
print(f"  {'def':<5}" + "".join(f"{'lag'+str(l):>9}" for l in (1, 5, 21, 63, 252)))
for k in DEFS:
    dd = [d for d in ds if d in VRPD[k]]; v = [VRPD[k][d] for d in dd]
    print(f"  {k:<5}" + "".join(f"{corr(v[:-l], v[l:]):>9.3f}" for l in (1, 5, 21, 63, 252)))

# alignment sanity: QQQ d0->d1 vs VXN change d0->d1 should be ~ -0.75
qv = [qpx[d] for d in ds]
xa, xb = [], []
for i in range(len(ds) - 1):
    a, b = IVD['q30'][ds[i]], IVD['q30'][ds[i + 1]]
    if a and b: xa.append(qv[i + 1] / qv[i] - 1); xb.append(b / a - 1)
print(f"\nALIGNMENT SANITY: corr(QQQ d0->d1, VXN change d0->d1) = {corr(xa, xb):+.3f}  (expected about -0.75)")

# forward returns
def fwd(v, i, h): return (v[i + h] / v[i] - 1) if i + h < len(v) else None
sv = [spy_full[d] for d in ds]
print("\nPredictive correlation: VRP at d0 vs FORWARD return (Pearson; t-stat naive, "
      "for h>1 divided by sqrt(h) for overlap):")
print(f"  {'def':<5}{'target':<8}" + "".join(f"{'h='+str(h):>18}" for h in (1, 5, 21)))
for k in DEFS:
    for tn, tv in (('QQQ', qv), ('SPY', sv)):
        line = f"  {k:<5}{tn:<8}"
        for h in (1, 5, 21):
            xs, ys = [], []
            for i, d in enumerate(ds):
                x = VRPD[k].get(d); y = fwd(tv, i, h)
                if x is not None and y is not None: xs.append(x); ys.append(y)
            rho = corr(xs, ys); t = tcorr(rho, len(xs)) / math.sqrt(h)
            line += f"{rho:>+9.3f} (t{t:+5.2f})"
        print(line)
# strategy's own d0->d1 return vs VRP at d0 (on P, live design)
for k in DEFS:
    xs = [r['vrp'][k] for r in P]; rho = corr(xs, live_ser)
    print(f"  corr(VRP {k} at d0, LIVE strategy d0->d1 return) = {rho:+.3f} (t {tcorr(rho, len(xs)):+.2f})")

def bucket_table(k, causal, sample=None):
    """Mean forward QQQ return by VRP quintile. causal=True uses the
    trailing-252 quintile cut-points at each date; False uses full-sample
    quintiles (descriptive only, not tradeable)."""
    dd = [d for d in ds if d in VRPD[k] and (sample is None or sample[0] <= d <= sample[1])]
    if not causal:
        allv = [VRPD[k][d] for d in dd]; cuts = [pctl(allv, q) for q in (0.2, 0.4, 0.6, 0.8)]
    ix = {d: i for i, d in enumerate(ds)}
    B = {q: {1: [], 5: [], 21: []} for q in range(5)}
    SA = {q: 0 for q in range(5)}; NA = {q: 0 for q in range(5)}
    effmap = {r['d']: r['eff'] for r in srows}
    for d in dd:
        x = VRPD[k][d]
        if causal:
            th = THR[(k, 't252')].get(d)
            if th is None: continue
            c = [th[0.2], th[0.4], th[0.6], th[0.8]]
        else: c = cuts
        q = sum(1 for cc in c if x > cc)
        i = ix[d]
        for h in (1, 5, 21):
            y = fwd(qv, i, h)
            if y is not None: B[q][h].append(y)
        NA[q] += 1; SA[q] += 1 if effmap.get(d) in ('A', 'B') else 0
    print(f"  {'quintile':<10}{'n':>6}{'fwd1d%':>9}{'fwd5d%':>9}{'fwd21d%':>9}{'21d Sh':>8}{'%A/B':>7}")
    for q in range(5):
        r21 = B[q][21]
        print(f"  Q{q+1}{'(low)' if q==0 else '(high)' if q==4 else '':<8}{NA[q]:>6}"
              f"{mean(B[q][1])*100:>9.3f}{mean(B[q][5])*100:>9.3f}{mean(r21)*100:>9.3f}"
              f"{(mean(r21)/sd(r21)*math.sqrt(252/21)) if len(r21)>2 else 0:>8.2f}"
              f"{100*SA[q]/max(1,NA[q]):>6.0f}%")
    for h in (5, 21):
        a, b = B[4][h], B[0][h]
        diff = mean(a) - mean(b); se = math.sqrt(sd(a) ** 2 / len(a) + sd(b) ** 2 / len(b)) * math.sqrt(h)
        print(f"  Q5-Q1 fwd{h}d: {diff*100:+.3f}%  (overlap-adjusted t {diff/se:+.2f})")

print("\nForward QQQ returns by VRP quintile -- q30, FULL-SAMPLE quintiles (descriptive):")
bucket_table('q30', causal=False)
print("\nForward QQQ returns by VRP quintile -- q30, CAUSAL trailing-252 quintiles (tradeable):")
bucket_table('q30', causal=True)
print("\n  ... causal, HOLDOUT era only:"); bucket_table('q30', causal=True, sample=HOLDOUT)
print("\n  ... causal, SEARCH era only:");  bucket_table('q30', causal=True, sample=SEARCH)
print("\nForward returns by VRP quintile -- s30 (VIX - SPY rv30), causal:")
bucket_table('s30', causal=True)
print("\nForward returns by VRP quintile -- q10, causal:")
bucket_table('q10', causal=True)

# ============================================================ (a) TILT
print("\n" + "=" * 100)
print("(a) VRP as a TILT between core and TQQQ in states A/B (constant deployed capital)")
print("=" * 100)
VARIANTS = []

def trim_w(w, r):
    f = extension_scale(r['eff'], r['gaps'])
    return w if f >= 1 else tuple(a * f for a in w[:4]) + (1 - f * sum(w[:4]),)

def tilt_sign(r, defn, mode, win):
    x = r['vrp'][defn]
    if mode == 'neg0': return -1 if x < 0 else 0
    th = r['thr'][(defn, win)]
    if mode == 'med': return 1 if x > th[0.5] else -1
    if mode == 'q2575': return 1 if x > th[0.75] else (-1 if x < th[0.25] else 0)
    raise ValueError(mode)

def tilt_fn(defn, delta, mode, win='t252', sign=1, vtf=vt):
    def fn(r):
        eff = r['eff']; w = W[eff]
        if eff in ('A', 'B'):
            s = tilt_sign(r, defn, mode, win) * sign
            if s: w = (w[0] - s * delta, w[1] + s * delta, 0.0, 0.0, 0.0)
        return vtf(trim_w(w, r), r.get('vol_live') or r['vol'])
    return fn

def const_tilt_fn(dc, vtf=vt):
    def fn(r):
        eff = r['eff']; w = W[eff]
        if eff in ('A', 'B'): w = (w[0] - dc, w[1] + dc, 0.0, 0.0, 0.0)
        return vtf(trim_w(w, r), r.get('vol_live') or r['vol'])
    return fn

def const_tilt_matched(rows, target_beta):
    lo, hi = -0.25, 0.25
    for _ in range(40):
        mid = (lo + hi) / 2
        if beta_of(rows, const_tilt_fn(mid)) < target_beta: lo = mid
        else: hi = mid
    dc = (lo + hi) / 2
    return dc, evaluate(rows, const_tilt_fn(dc))

def both(ev, base): return ev['s_sharpe'] > base['s_sharpe'] and ev['h_sharpe'] > base['h_sharpe']

print(f"\n{'variant':<28}{'SPY-core CAGR/Sh/MDD':>22}{'S':>7}{'H':>7}{'beta':>7}"
      f"{'| beta-m Sh S/H':>18}{'| const-tilt S/H':>18}{'| flip S/H':>14}{'| QQQ-core S/H':>16}{'| real Sh':>10}")
grid = []
for defn in DEFS:
    for delta in (0.10, 0.20):
        for mode in ('med', 'q2575', 'neg0'):
            grid.append((defn, delta, mode, 't252'))
for delta in (0.10, 0.20):
    for mode in ('med', 'q2575'):
        grid.append(('q30', delta, mode, 'exp'))
TILT_RES = {}
for defn, delta, mode, win in grid:
    lab = f"{defn} d={delta:.2f} {mode} {win}"
    fn = tilt_fn(defn, delta, mode, win); ev = evaluate(P, fn); b = beta_of(P, fn)
    _, bm = beta_matched_control(P, LIVE, b)
    dc, ct = const_tilt_matched(P, b)
    fl = evaluate(P, tilt_fn(defn, delta, mode, win, sign=-1))
    evq = evaluate(Q, fn)
    er = RF.eval_real(Pr, tilt_fn(defn, delta, mode, win, vtf=RF.vt))
    flags = ('BOTH' if both(ev, base_s) else '    ') + (' >bm' if both(ev, bm) else '    ') + \
            (' flipLoses' if not both(fl, base_s) and (fl['sharpe'] < ev['sharpe']) else '')
    VARIANTS.append(('a', lab)); TILT_RES[lab] = dict(ev=ev, bm=bm, ct=ct, fl=fl, evq=evq, er=er, fn=fn, beta=b, dc=dc)
    print(f"{lab:<28}{fmt(ev):>22}{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f}{b:>7.3f}"
          f"{'|':>4}{bm['sharpe']:.3f} {bm['s_sharpe']:.3f}/{bm['h_sharpe']:.3f}"
          f"{'|':>3}{dc:+.3f} {ct['s_sharpe']:.3f}/{ct['h_sharpe']:.3f}"
          f"{'|':>3}{fl['s_sharpe']:.3f}/{fl['h_sharpe']:.3f}"
          f"{'|':>3}{evq['s_sharpe']:.3f}/{evq['h_sharpe']:.3f}{'|':>3}{er['sharpe']:.3f}  {flags}")
print(f"\n  live: SPY-core {base_s['s_sharpe']:.3f}/{base_s['h_sharpe']:.3f}  QQQ-core "
      f"{base_q['s_sharpe']:.3f}/{base_q['h_sharpe']:.3f}  real {base_r['sharpe']:.3f}")
print("  'beta-m' = live scaled to the variant's beta; 'const-tilt' = fixed A/B core->TQQQ shift dc with the same beta;")
print("  'flip' = sign-flipped signal. BOTH = beats live on search and holdout; >bm = beats beta-matched live on both.")

# how often the tilt fires, and in which direction (A/B rows only)
print("\nTilt activity on A/B rows (fraction of A/B rows tilted toward TQQQ / toward core):")
ab = [r for r in P if r['eff'] in ('A', 'B')]
for defn in DEFS:
    for mode in ('med', 'q2575', 'neg0'):
        s = [tilt_sign(r, defn, mode, 't252') for r in ab]
        up = sum(1 for x in s if x > 0) / len(s); dn = sum(1 for x in s if x < 0) / len(s)
        print(f"  {defn} {mode:<6}: toward TQQQ {up*100:5.1f}%  toward core {dn*100:5.1f}%  "
              f"(A/B rows {len(ab)}; holdout share toward core "
              f"{sum(1 for r,x in zip(ab,s) if x<0 and r['d']<=HOLDOUT[1])/max(1,sum(1 for r in ab if r['d']<=HOLDOUT[1]))*100:.1f}%)")

# ============================================================ (b) MODULATOR
print("\n" + "=" * 100)
print("(b) VRP as a MODULATOR of the vol-target multiplier, T re-calibrated to live's exposure")
print("=" * 100)

def gfun(fam, k, r, defn, sign):
    x = r['vrp'][defn]
    if fam == 'pw':  g = (1 + k) if x < 0 else 1.0
    elif fam == 'exp': g = math.exp(-k * x)
    elif fam == 'pow': g = (r['rv'][defn] / r['iv'][defn]) ** k
    else: raise ValueError(fam)
    return 1 / g if sign < 0 else g

def mod_fn(defn, fam, k, T, sign=1, vtf=vt):
    def fn(r):
        w = trim_w(W[r['eff']], r)
        v = (r.get('vol_live') or r['vol']) * gfun(fam, k, r, defn, sign)
        return vtf(w, v, T)
    return fn

def expo(rows, fn): return run(rows, fn)[1]
def calib(defn, fam, k, sign, te, lo=0.02, hi=4.0):
    for _ in range(60):
        mid = (lo + hi) / 2
        if expo(P, mod_fn(defn, fam, k, mid, sign)) < te: lo = mid
        else: hi = mid
    return (lo + hi) / 2
def real_expo(rows, fn): return mean([sum(fn(r)[:4]) for r in rows])
live_rexp = real_expo(Pr, LIVE_R)

print(f"\nlive exposure on P {live_exp*100:.2f}% (T=0.20); real rows live exposure {live_rexp*100:.2f}%")
print(f"{'variant':<20}{'T*':>7}{'expo':>7}{'SPY-core CAGR/Sh/MDD':>22}{'S':>7}{'H':>7}"
      f"{'| flip T*':>10}{'Sh':>7}{'S/H':>13}{'| QQQ-core S/H':>16}{'| real Sh':>10}{'expo':>7}")
MOD_RES = {}
fams = [('pw', 0.25), ('pw', 0.5), ('pw', 1.0), ('exp', 2.0), ('exp', 4.0), ('exp', 8.0), ('pow', 0.5), ('pow', 1.0)]
for defn in DEFS:
    for fam, k in fams:
        lab = f"{defn} {fam} k={k:g}"
        T = calib(defn, fam, k, 1, live_exp); fn = mod_fn(defn, fam, k, T)
        ev = evaluate(P, fn); ex = expo(P, fn)
        Tf = calib(defn, fam, k, -1, live_exp); fl = evaluate(P, mod_fn(defn, fam, k, Tf, -1))
        evq = evaluate(Q, fn)
        fr = mod_fn(defn, fam, k, T, vtf=RF.vt); er = RF.eval_real(Pr, fr); rex = real_expo(Pr, fr)
        flags = ('BOTH' if both(ev, base_s) else '    ') + \
                (' flipLoses' if (not both(fl, base_s)) and fl['sharpe'] < ev['sharpe'] else '')
        VARIANTS.append(('b', lab)); MOD_RES[lab] = dict(ev=ev, fl=fl, evq=evq, er=er, fn=fn, T=T)
        print(f"{lab:<20}{T:>7.3f}{ex*100:>6.2f}%{fmt(ev):>22}{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f}"
              f"{'|':>3}{Tf:>7.3f}{fl['sharpe']:>7.3f}  {fl['s_sharpe']:.3f}/{fl['h_sharpe']:.3f}"
              f"{'|':>3}{evq['s_sharpe']:.3f}/{evq['h_sharpe']:.3f}{'|':>3}{er['sharpe']:.3f}{rex*100:>6.1f}%  {flags}")
print(f"\n  live: SPY-core {fmt(base_s)} S {base_s['s_sharpe']:.3f} H {base_s['h_sharpe']:.3f}; "
      f"QQQ-core {base_q['s_sharpe']:.3f}/{base_q['h_sharpe']:.3f}; real {base_r['sharpe']:.3f}")
print("  Each variant's T* is bisected so its average deployed exposure on P equals live's; the flip (g -> 1/g) is")
print("  re-calibrated separately. Real rows use the proxy-calibrated T*, so their exposure is reported, not matched.")

# ============================================================ SURVIVORS
print("\n" + "=" * 100)
print("SURVIVOR TESTS -- block bootstrap and leave-one-regime-out for anything beating live on BOTH eras")
print("=" * 100)
REGIMES = [('dot-com 2000-2002', '2000-01-01', '2002-12-31'), ('GFC 2007-2009', '2007-01-01', '2009-12-31'),
           ('COVID 2020', '2020-01-01', '2020-12-31'), ('2022 bear', '2022-01-01', '2022-12-31'),
           ('whole SPMO era 2015-11+', '2015-11-01', '2099-01-01')]
def survivor_tests(lab, fn, ctrl_fn=None, ctrl_lab='live'):
    a = run(P, fn)[0]; b = run(P, ctrl_fn)[0] if ctrl_fn else live_ser
    la, sa = stats(a); lb, sb = stats(b)
    print(f"\n  {lab}  vs {ctrl_lab}: point {(la-lb)*100:+.2f}pp/yr log-return, {sa-sb:+.3f} Sharpe")
    for blk in (20, 60):
        l1, l2, pl, s1, s2, ps = boot(a, b, blk, seed=hash((lab, blk)) & 0xffff)
        print(f"     block {blk:>2}d: logret 95% [{l1*100:+.2f},{l2*100:+.2f}]pp P(<=0)={pl:.3f} | "
              f"Sharpe 95% [{s1:+.3f},{s2:+.3f}] P(<=0)={ps:.3f}")
    print("     leave-one-regime-out (Sharpe diff / log-return diff):")
    for rl, a0, b0 in REGIMES:
        keep = [i for i, r in enumerate(P) if not (a0 <= r['d'] <= b0)]
        ca = [a[i] for i in keep]; cb = [b[i] for i in keep]
        _, s1 = stats(ca); _, s2 = stats(cb); l1, _ = stats(ca); l2, _ = stats(cb)
        print(f"       drop {rl:<26} {s1-s2:+.3f} / {(l1-l2)*100:+.2f}pp")

n_surv = 0
for lab, R in TILT_RES.items():
    if both(R['ev'], base_s):
        n_surv += 1
        print(f"\n[a] {lab}: beats live both eras. beats beta-matched both eras: {both(R['ev'], R['bm'])}; "
              f"beats const-tilt both eras: {both(R['ev'], R['ct'])}; flip both-era: {both(R['fl'], base_s)}; "
              f"QQQ-core both: {both(R['evq'], base_q)}; real Sharpe {R['er']['sharpe']:.3f} vs {base_r['sharpe']:.3f}")
        survivor_tests(lab, R['fn'])
        survivor_tests(lab, R['fn'], const_tilt_fn(R['dc']), f"const-tilt dc={R['dc']:+.3f}")
for lab, R in MOD_RES.items():
    if both(R['ev'], base_s):
        n_surv += 1
        print(f"\n[b] {lab}: beats live both eras (exposure-matched). flip both-era: {both(R['fl'], base_s)}; "
              f"QQQ-core both: {both(R['evq'], base_q)}; real Sharpe {R['er']['sharpe']:.3f} vs {base_r['sharpe']:.3f}")
        survivor_tests(lab, R['fn'])
if n_surv == 0: print("\n  none beat live on both eras.")

na = sum(1 for t, _ in VARIANTS if t == 'a'); nb = sum(1 for t, _ in VARIANTS if t == 'b')
print(f"\nVARIANT COUNT: {len(VARIANTS)} primary variants ({na} tilt + {nb} modulator), each also run as a "
      f"sign-flip and on the QQQ-core proxy and real rows; {n_surv} beat live on both eras on the SPY-core proxy.")

# ============================================================ (d) WHAT DRIVES THE MODULATOR?
print("\n" + "=" * 100)
print("(d) DECOMPOSITION + ROBUSTNESS of the modulator (controls, not new variants)")
print("=" * 100)
print("""  g = exp(-k*(IV - rv)) = exp(-k*IV) * exp(+k*rv). With T re-calibrated the constant
  is absorbed, so two controls isolate the two halves:
    IV-level only : g = exp(-k*IV)   (implied level, no premium)  -- vxn_full_test PART 1 territory
    rv-only       : g = exp(+k*rv)   (steeper response to realized vol, no implied input at all)
  If rv-only reproduces the gain, the 'VRP' is just a convex realized-vol response.""")
import improvement_search as _IS

def gen_mod_fn(gf, T, vtf=vt):
    def fn(r):
        w = trim_w(W[r['eff']], r)
        return vtf(w, (r.get('vol_live') or r['vol']) * gf(r), T)
    return fn
def calib_g(gf, te, lo=0.02, hi=4.0):
    for _ in range(60):
        mid = (lo + hi) / 2
        if expo(P, gen_mod_fn(gf, mid)) < te: lo = mid
        else: hi = mid
    return (lo + hi) / 2

def logret_diff(fn, ref_ser=None):
    a = run(P, fn)[0]; b = ref_ser or live_ser
    la, sa = stats(a); lb, sb = stats(b); return (la - lb) * 100, sa - sb

print(f"\n{'control':<26}{'T*':>7}{'SPY-core CAGR/Sh/MDD':>22}{'S':>7}{'H':>7}{'dLogret':>9}{'dSharpe':>9}{'| QQQ-core S/H':>16}{'| real Sh':>10}")
DECOMP = {}
for defn in ('q30', 'q21', 'q10'):
    for k in (2.0, 4.0):
        for lab, gf in ((f'{defn} VRP exp k={k:g}', (lambda r, d=defn, k=k: math.exp(-k * r['vrp'][d]))),
                        (f'{defn} IV-level k={k:g}', (lambda r, d=defn, k=k: math.exp(-k * r['iv'][d]))),
                        (f'{defn} rv-only  k={k:g}', (lambda r, d=defn, k=k: math.exp(+k * r['rv'][d])))):
            T = calib_g(gf, live_exp); fn = gen_mod_fn(gf, T); ev = evaluate(P, fn)
            dl, dsh = logret_diff(fn); evq = evaluate(Q, fn); er = RF.eval_real(Pr, gen_mod_fn(gf, T, RF.vt))
            DECOMP[lab] = dict(ev=ev, fn=fn, T=T, gf=gf)
            print(f"{lab:<26}{T:>7.3f}{fmt(ev):>22}{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f}{dl:>+9.2f}{dsh:>+9.3f}"
                  f"{'|':>3}{evq['s_sharpe']:.3f}/{evq['h_sharpe']:.3f}{'|':>3}{er['sharpe']:.3f}"
                  f"{'  BOTH' if both(ev, base_s) else ''}")
    print()

# bootstrap the VRP version AGAINST the rv-only control (does the implied leg add anything?)
for defn in ('q21', 'q10'):
    k = 4.0 if defn == 'q21' else 2.0
    cand = DECOMP[f'{defn} VRP exp k={k:g}']['fn']; ctl = DECOMP[f'{defn} rv-only  k={k:g}']['fn']
    survivor_tests(f'{defn} VRP exp k={k:g}', cand, ctl, f'{defn} rv-only k={k:g} (exposure-matched)')

# ---- cost sensitivity (ONE_WAY_SPREAD is read by run() as a module global)
print("\nCOST SENSITIVITY (one-way spread 4bp live, 10bp, 20bp): Sharpe S/H and full, live vs top modulators")
TOP = [('q21 exp k=4', MOD_RES['q21 exp k=4']['fn']), ('q10 exp k=2', MOD_RES['q10 exp k=2']['fn']),
       ('q30 exp k=2', MOD_RES['q30 exp k=2']['fn']), ('q21 pow k=0.5', MOD_RES['q21 pow k=0.5']['fn'])]
orig = _IS.ONE_WAY_SPREAD
for bp in (0.0004, 0.0010, 0.0020):
    _IS.ONE_WAY_SPREAD = bp
    lv = evaluate(P, LIVE)
    line = f"  {bp*1e4:4.0f}bp  live {lv['sharpe']:.3f} ({lv['s_sharpe']:.3f}/{lv['h_sharpe']:.3f})"
    for lab, fn in TOP:
        ev = evaluate(P, fn)
        line += f" | {lab} {ev['sharpe']:.3f} ({ev['s_sharpe']:.3f}/{ev['h_sharpe']:.3f}){' BOTH' if both(ev, lv) else '     '}"
    print(line)
# turnover proxy: (zero-cost return - 4bp return) / 4bp = L1 weight traded per year
_IS.ONE_WAY_SPREAD = 0.0
z_live = stats(run(P, LIVE)[0])[0]
zt = {lab: stats(run(P, fn)[0])[0] for lab, fn in TOP}
_IS.ONE_WAY_SPREAD = orig
c_live = stats(live_ser)[0]
print(f"  turnover proxy (L1 traded/yr from cost drag): live {(z_live-c_live)/orig:.1f}x", end='')
for lab, fn in TOP:
    print(f" | {lab} {(zt[lab]-stats(run(P, fn)[0])[0])/orig:.1f}x", end='')
print()

# ---- 1-day lag of the signal (use VRP of the previous row)
print("\nSIGNAL LAG: modulator driven by the PREVIOUS session's VRP (T re-calibrated)")
prevmap = {}
for i, r in enumerate(P):
    prevmap[r['d']] = P[i - 1] if i > 0 else r
for defn, fam, k in (('q21', 'exp', 4.0), ('q10', 'exp', 2.0), ('q30', 'exp', 2.0)):
    gf = (lambda r, d=defn, k=k: math.exp(-k * prevmap[r['d']]['vrp'][d]))
    T = calib_g(gf, live_exp); fn = gen_mod_fn(gf, T); ev = evaluate(P, fn); dl, dsh = logret_diff(fn)
    print(f"  {defn} exp k={k:g} lag1: T* {T:.3f}  {fmt(ev)}  S {ev['s_sharpe']:.3f} H {ev['h_sharpe']:.3f}  "
          f"dLogret {dl:+.2f}pp dSharpe {dsh:+.3f}{'  BOTH' if both(ev, base_s) else ''}")

# ---- year-by-year attribution of the top modulator and the top tilt
print("\nYEAR-BY-YEAR log-return difference vs live (pp):")
def byyear(ser):
    by = {}
    for r, x in zip(P, ser): by[r['d'][:4]] = by.get(r['d'][:4], 0) + math.log1p(x)
    return by
bl = byyear(live_ser)
for lab, fn in (('q21 exp k=4', MOD_RES['q21 exp k=4']['fn']), ('q10 exp k=2', MOD_RES['q10 exp k=2']['fn']),
                ('tilt q21 d=0.10 med', TILT_RES['q21 d=0.10 med t252']['fn'])):
    bc = byyear(run(P, fn)[0])
    print(f"  {lab:<20}" + " ".join(f"{y[2:]}:{(bc[y]-bl[y])*100:+.1f}" for y in sorted(bl)))

# ---- where does the modulator change the multiplier? (state / VRP-sign breakdown)
print("\nMULTIPLIER DIFFERENCE (candidate minus live risky weight sum), q21 exp k=4, by VRP sign and state:")
fn = MOD_RES['q21 exp k=4']['fn']
agg = {}
for r in P:
    key = (r['eff'], 'vrp<0' if r['vrp']['q21'] < 0 else 'vrp>=0')
    d = sum(fn(r)[:4]) - sum(LIVE(r)[:4])
    a = agg.setdefault(key, [0, 0.0]); a[0] += 1; a[1] += d
for key in sorted(agg):
    n, s = agg[key]; print(f"  {key[0]} {key[1]:<7} n={n:>5}  mean exposure diff {s/n*100:+.2f}pp")

# ---- what would have to be true: a SMOOTHED modulator (5-session mean VRP) -- less churn; with lag and 10bp
print("\nSMOOTHED modulator (5-session mean VRP), T re-calibrated; also with 1-session lag and at 10bp cost")
print("  (3 extra variants, counted in the total)")
SMV = {}   # 5-session trailing mean of the DAILY series, by date (attaches to proxy and real rows alike)
for k_ in DEFS:
    dd = [d for d in ds if d in VRPD[k_]]
    for i, d in enumerate(dd):
        SMV[(k_, d, 0)] = mean([VRPD[k_][dd[j]] for j in range(max(0, i - 4), i + 1)])
        SMV[(k_, d, 1)] = SMV[(k_, dd[i - 1], 0)] if i > 0 else SMV[(k_, d, 0)]
SMVK = sorted(set(d for (_, d, _) in SMV))
def sm_vrp(r, d, n=5, lag=0):
    dt = r.get('d') or r['d0']
    if (d, dt, lag) not in SMV: dt = SMVK[bisect.bisect_right(SMVK, dt) - 1]
    return SMV[(d, dt, lag)]
for defn, k in (('q21', 4.0), ('q10', 2.0), ('q30', 2.0)):
    VARIANTS.append(('b', f'{defn} exp k={k:g} sm5'))
    for lag in (0, 1):
        gf = (lambda r, d=defn, k=k, lag=lag: math.exp(-k * sm_vrp(r, d, 5, lag)))
        T = calib_g(gf, live_exp); fn = gen_mod_fn(gf, T); ev = evaluate(P, fn); dl, dsh = logret_diff(fn)
        _IS.ONE_WAY_SPREAD = 0.0; z = stats(run(P, fn)[0])[0]; _IS.ONE_WAY_SPREAD = orig
        tov = (z - stats(run(P, fn)[0])[0]) / orig
        _IS.ONE_WAY_SPREAD = 0.0010; lv10 = evaluate(P, LIVE); ev10 = evaluate(P, fn); _IS.ONE_WAY_SPREAD = orig
        er = RF.eval_real(Pr, gen_mod_fn(gf, T, RF.vt)) if lag == 0 else None
        print(f"  {defn} exp k={k:g} sm5 lag{lag}: T* {T:.3f} {fmt(ev)} S {ev['s_sharpe']:.3f} H {ev['h_sharpe']:.3f} "
              f"dLogret {dl:+.2f}pp dSharpe {dsh:+.3f}{' BOTH' if both(ev, base_s) else '     '} turnover {tov:.1f}x | "
              f"10bp: {ev10['sharpe']:.3f} ({ev10['s_sharpe']:.3f}/{ev10['h_sharpe']:.3f}) vs live {lv10['sharpe']:.3f}"
              f"{' BOTH' if both(ev10, lv10) else ''}" + (f" | real {er['sharpe']:.3f}" if er else ''))
    if defn == 'q21':
        gf = (lambda r, d=defn, k=k: math.exp(-k * sm_vrp(r, d, 5, 0)))
        survivor_tests(f'{defn} exp k={k:g} sm5', gen_mod_fn(gf, calib_g(gf, live_exp)))

na = sum(1 for t, _ in VARIANTS if t == 'a'); nb = sum(1 for t, _ in VARIANTS if t == 'b')
print(f"\nFINAL VARIANT COUNT: {len(VARIANTS)} ({na} tilt + {nb} modulator incl. 3 smoothed), plus per-variant sign-flip, "
      f"QQQ-core and real-row runs and {len(DECOMP)} decomposition controls.")
