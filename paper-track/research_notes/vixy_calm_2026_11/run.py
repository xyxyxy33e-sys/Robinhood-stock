"""Calm VIXY / VIXM hedge study. Research only. See PLAN.md (pre-registered 2026-11-17, before any arm was run)."""
import csv, os, sys, re, bisect
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); PT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PT, 'review_2026_11'))
import harness as H
from harness import MC, S
VP = os.path.join(PT, 'research_notes', 'vol_predict_2026_11')
LOG = open(os.path.join(HERE, 'run.log'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); LOG.write(s + '\n'); LOG.flush()
CAPCFG = dict(H.CUR, gross_cap=2.0)
NBOOT = 2000; EPS = S.ZERO_LEG_EPS; BAND = S.REBALANCE_DRIFT_BAND
TRK = {'real': dict(real=True, ds=H.RD, sg=H.sr, d0='2015-11-02'),
       'vera': dict(real=False, ds=H.PD, sg=H.sig, d0='2015-09-02')}

# ------------------------------------------------------------------ data
def load_fred(fn, ds):
    d = {}
    for r in csv.reader(open(os.path.join(VP, fn))):
        try: d[r[0]] = float(r[1])
        except Exception: pass
    keys = sorted(d); out = np.full(len(ds), np.nan)
    for i, x in enumerate(ds):
        j = bisect.bisect_right(keys, x) - 1
        if j >= 0: out[i] = d[keys[j]]
    return out
vy = {r['d']: float(r['c']) for r in csv.DictReader(open(os.path.join(H.HERE, 'research_notes', 'vixm_followups_2026_11', 'vixy_daily.csv')))}
vy_last = max(vy)
for r in H.LC:
    if r['date'] > vy_last and r.get('VIXY'): vy[r['date']] = float(r['VIXY'])
vm = MC._load('vixm_daily.csv')            # harness-patched loader: file + live_closes VIXM column
def rr(px, ds):
    x = MC._rets(px, ds); x[0] = 0.0; return x
INSTR = {tn: {'Y': rr(vy, t['ds']), 'M': rr(vm, t['ds'])} for tn, t in TRK.items()}
CASHR = {tn: (H.pr if t['real'] else H.p)['cash'] for tn, t in TRK.items()}
# harness VIX sleeve latch for the proxy panel too (the harness only builds it on the real panel)
_vd = {d: (None if np.isnan(v) else float(v)) for d, v in zip(H.PD, H.sig['vol'][0])}
_vxp = S.vixm_series(H.PD, H.VIX, H.VIX3M, _vd)
VXA_P = np.array([bool(_vxp.get(d, {}).get('allowed')) for d in H.PD])
VXA = {'real': H.VXA, 'vera': VXA_P}

# ------------------------------------------------------------------ baseline weights (copy of H.weights, sleeve on both tracks)
def base_parts(tn):
    t = TRK[tn]; real = t['real']; ds = t['ds']; sg = t['sg']; pn = H.pr if real else H.p; cfg = CAPCFG
    w5 = MC.target_weights(sg, cfg); key = MC.regime_key(sg, cfg).astype(np.int64)[0]
    cash = w5[0, :, 4].copy()
    legs = [pn['core'], pn['tqqq'], pn['qld'], pn['xlu']]; W = [w5[0, :, i] for i in range(4)]
    eff = MC._eff(sg, cfg)[0]; gate = MC._gate(sg, cfg)[0]; z = MC._zone(sg, cfg)[0]
    allowed = VXA[tn] & ~((eff == 3) & ~gate & (z == 2))
    v = np.where(allowed, cash * S.VIXM_CASH_SHARE, 0.0)
    legs.append(INSTR[tn]['Y']); W.append(v); used = v.copy(); key = key + allowed.astype(np.int64) * 100000
    e_ = eff; g = np.nan_to_num(sg['gaps'][200][0])
    deep = ((e_ == 4) & (g <= S.DEEP_E_GAP200)).astype(float) * S.DEEP_E_CASH_SHARE
    pan = H.panic_series(ds)
    for j, sh_ in enumerate((deep, pan)):
        x = np.minimum(cash * sh_, cash - used); used = used + x
        legs.append(pn['qqq']); W.append(x); key = key + (sh_ > 0).astype(np.int64) * (10 ** (6 + j))
    legs.append(pn['cash']); W.append(cash - used)
    return np.stack(W, -1), np.stack(legs, -1), key, eff, gate
BP = {tn: base_parts(tn) for tn in TRK}
WIN = {}
for tn, t in TRK.items():
    ds = t['ds']; s0 = next(i for i, d in enumerate(ds) if d >= t['d0']); WIN[tn] = (s0, len(ds) - 1)

# conditions
COND = {}
for tn, t in TRK.items():
    sg = t['sg']; ds = t['ds']; W, L, k, eff, gate = BP[tn]
    vix = load_fred('VIXCLS.csv', ds); v3 = load_fred('VXVCLS.csv', ds)
    COND[tn] = dict(vix=vix, ratio=vix / v3, rv=sg['vol'][0], gap=sg['gaps'][200][0], A=(eff == 0), lev=(eff == 0) | ((eff == 3) & ~gate),
                    sleeve=W[:, 4] > 1e-12)
def lagged(a, lag): return a if not lag else np.concatenate([np.full(lag, np.nan), a[:-lag]])
_ac = {}
def active(tn, fam, T, lag):
    key = (tn, fam, T, lag if fam != 'C3' else 0)
    if key in _ac: return _ac[key]
    c = COND[tn]; vix = lagged(c['vix'], lag); ratio = lagged(c['ratio'], lag); rv = lagged(c['rv'], lag); gap = lagged(c['gap'], lag)
    with np.errstate(invalid='ignore'):
        if fam == 'C1': x = vix < T
        elif fam == 'C2': x = rv < 0.20
        elif fam == 'C3': x = np.ones(len(vix), bool)
        elif fam == 'C4a': x = (vix < 18) & (ratio <= 0.90)
        elif fam == 'C4b': x = (vix < 18) & (ratio > 0.90)
        elif fam == 'C5': x = c['A'] & (gap > 0.10)
    a = np.asarray(x, bool) & c['lev'] & ~c['sleeve']
    _ac[key] = a; return a

def add_hedge(tn, act, h, var):
    Wb, Lb, kb = BP[tn][:3]
    W = np.concatenate([Wb, np.zeros((len(Wb), 1))], 1)
    hv = np.where(act, h, 0.0); R = W[:, :4].sum(1)
    if var == 'ontop':
        t1 = np.minimum(hv, np.maximum(W[:, 7], 0)); W[:, 7] -= t1
    else: t1 = 0.0
    t2 = np.minimum(hv - t1, R)
    sc = np.where(R > 1e-12, 1 - t2 / np.maximum(R, 1e-12), 1.0)
    W[:, :4] *= sc[:, None]; W[:, 8] = t1 + t2
    return W, kb + (W[:, 8] > 1e-12).astype(np.int64) * 10 ** 8

def engine(W, key, L, s0, e, cvec):
    n = e - s0; out = np.zeros(n); hw = np.zeros(n); ctb = np.zeros(n); h = W[s0].copy(); cost = MC.COST; tr = 0
    for t in range(s0, e):
        if t > s0:
            tgt = W[t]; diff = np.abs(tgt - h)
            if key[t] != key[t - 1] or diff.sum() > BAND or ((tgt == 0) & (h > EPS)).any():
                cost = float((diff * cvec).sum()); h = tgt.copy(); tr += 1
            else: cost = 0.0
        r = L[t + 1]; g = float((h * r).sum()); out[t - s0] = (1 + g) * (1 - cost) - 1
        hw[t - s0] = h[8]; ctb[t - s0] = h[8] * r[8]; h = h * (1 + r) / (1 + g)
    return out, hw, ctb, tr / (n / 252)
CV = np.full(9, MC.COST)
def cvec(sens, hedge_vol):
    c = CV.copy()
    if sens: c[4] = 0.0005; c[8] = 0.0005 if hedge_vol else MC.COST
    return c
def stats(r):
    nav = np.cumprod(1 + r); dd = (nav / np.maximum(np.maximum.accumulate(nav), 1) - 1).min(); v = r.std(ddof=1) * 252 ** .5
    return dict(c=nav[-1] ** (252 / len(r)) - 1, sh=r.mean() * 252 / v, m=dd, v=v, w1=r.min(),
                w5=float(np.expm1(np.convolve(np.log1p(r), np.ones(5), 'valid')).min()))
def sh(r): return r.mean() * 252 / (r.std(ddof=1) * 252 ** .5)
def mdd(r): n = np.cumprod(1 + r); return (n / np.maximum(np.maximum.accumulate(n), 1) - 1).min()

_base = {}
def run_base(tn, sens=False):
    if (tn, sens) in _base: return _base[(tn, sens)]
    s0, e = WIN[tn]; Wb, Lb, kb = BP[tn][:3]
    W = np.concatenate([Wb, np.zeros((len(Wb), 1))], 1); L = np.concatenate([Lb, np.zeros((len(Lb), 1))], 1)
    r, hw, ctb, tpy = engine(W, kb, L, s0, e, cvec(sens, False)); res = dict(r=r, hw=hw, ctb=ctb, tpy=tpy); _base[(tn, sens)] = res; return res
_cache = {}
def run_arm(tn, arm, var, lag=0, sens=False):
    ck = (tn, arm, var, lag, sens)
    if ck in _cache: return _cache[ck]
    inst, fam, T, h = arm; s0, e = WIN[tn]
    W, k = add_hedge(tn, active(tn, fam, T, lag), h, var); Lb = BP[tn][1]
    La = np.concatenate([Lb, INSTR[tn][inst][:, None]], 1); Lm = np.concatenate([Lb, CASHR[tn][:, None]], 1)
    A = engine(W, k, La, s0, e, cvec(sens, True)); M = engine(W, k, Lm, s0, e, cvec(sens, False))
    res = (dict(r=A[0], hw=A[1], ctb=A[2], tpy=A[3]), dict(r=M[0], hw=M[1], ctb=M[2], tpy=M[3])); _cache[ck] = res; return res

# ------------------------------------------------------------------ arms
HY = (0.02, 0.05, 0.10); HM = (0.02, 0.04, 0.05, 0.10, 0.20); TS = (14, 16, 18, 20)
ARMS = []
for h in HY:
    for T in TS: ARMS.append(('Y', 'C1', T, h))
    ARMS += [('Y', 'C2', None, h), ('Y', 'C3', None, h)]
ARMS += [('Y', 'C4a', 18, 0.05), ('Y', 'C4b', 18, 0.05), ('Y', 'C5', None, 0.05), ('Y', 'C5', None, 0.10)]
for h in HM:
    for T in TS: ARMS.append(('M', 'C1', T, h))
    ARMS += [('M', 'C2', None, h), ('M', 'C3', None, h)]
for h in (0.05, 0.10, 0.20): ARMS.append(('M', 'C5', None, h))
def lab(a):
    inst, fam, T, h = a; return f"{inst} {fam}{'' if T is None else ' T%d' % T} h{h*100:g}"
GROUP = lambda a: (a[0], a[1])
VARS = ('prorata', 'ontop')

# ------------------------------------------------------------------ crack days
txt = open(os.path.join(VP, 'analyze.log')).read().split('biggest surprises')[1].split('big up days')[0]
CD = re.findall(r'^(\d{4}-\d\d-\d\d)\s+-0\.', txt, re.M)
RDS = {tn: TRK[tn]['ds'][WIN[tn][0] + 1:WIN[tn][1] + 1] for tn in TRK}
CRK = {tn: np.array([d in set(CD) for d in RDS[tn]]) for tn in TRK}
YRS = {tn: np.array([d[:4] for d in RDS[tn]]) for tn in TRK}

# ------------------------------------------------------------------ bootstrap
def boot_idx(N, n, block=20, seed=11):
    rng = np.random.default_rng(seed); nb = -(-N // block); st = rng.integers(N, size=(n, nb))
    return ((st[:, :, None] + np.arange(block)) % N).reshape(n, -1)[:, :N]
BIDX = {}
def dd_paths(x):
    out = np.empty(len(x))
    for i in range(0, len(x), 500):
        nav = np.cumprod(1 + x[i:i + 500], axis=1); out[i:i + 500] = (nav / np.maximum(np.maximum.accumulate(nav, axis=1), 1)).min(1) - 1
    return out
def boot(ra, rm):
    N = len(ra)
    if N not in BIDX: BIDX[N] = boot_idx(N, NBOOT)
    idx = BIDX[N]; a, m = ra[idx], rm[idx]; s = lambda x: x.mean(1) / x.std(1, ddof=1)
    d = (s(a) - s(m)) * 252 ** .5
    if np.array_equal(ra, rm): return 1.0, 0.0, 1.0, 0.0
    dd = dd_paths(a) - dd_paths(m)
    return float((d <= 0).mean()), float(np.median(d)), float((dd <= 0).mean()), float(np.median(dd))

# ------------------------------------------------------------------ header / baseline
log('=' * 130); log('run.py: calm VIXY / VIXM hedge study (2026-11-17); PLAN.md pre-registered; research only, nothing adopted'); log('=' * 130)
log("Convention: close of session t (VIX, VIX3M, QQQ rv30, SMA gap) decides the hedge traded at close t, earned from t+1 (harness sleeve convention).")
log(f"Harness VIX last {max(H.VIX)}; FRED VIXCLS last used: {COND['real']['vix'][-1]} on {H.RD[-1]} (ffill). VIXY file {min(vy)}..{vy_last} +live_closes to {max(vy)}; VIXM file+live_closes {min(vm)}..{max(vm)}")
log(f"VIXM last real print {max(vm)}; the last session {H.RD[-1]} has no VIXM print so its VIXM return is 0 (forward fill); VIXM column is the only one affected.")
for tn in TRK:
    s0, e = WIN[tn]; ds = TRK[tn]['ds']
    log(f"window {tn}: returns {ds[s0+1]} .. {ds[e]} ({e-s0} sessions); calm-crack days in window: {int(CRK[tn].sum())} of {len(CD)} listed (listed since 2000: pre-2015-09 ones untested: {sum(1 for d in CD if d < '2015-09-02')})")
log("\nBASELINE REPRODUCTION (CUR + gross_cap 2.0 + VIXY 35% sleeve)")
for tn in TRK:
    b = run_base(tn); x = stats(b['r']); extra = ''
    if tn == 'real':
        r0, d0_, tpy0 = H.run(True, cfg=CAPCFG, vixm_share=0.35, vixm_ret=INSTR['real']['Y'])
        assert np.allclose(r0, b['r']), 'engine/base mismatch vs harness'; extra = f"  (== harness.run exactly; harness trades/yr {tpy0:.1f})"
        r1, _, _ = H.run(True, cfg=CAPCFG); log(f"  harness default VIXM 75% sleeve + cap, real: {H.fmt(H.stats(r1))}")
    log(f"  Base {tn:<5} CAGR {x['c']*100:.1f}% Sharpe {x['sh']:.3f} maxDD {x['m']*100:.1f}% vol {x['v']*100:.1f}% trades/yr {b['tpy']:.1f} worst1 {x['w1']*100:.2f}% worst5 {x['w5']*100:.2f}%{extra}")
log("  Base sleeve: VIXY 35% of the cash leg (harness VIXM latch/gating logic, VIXY returns). vera = proxy panel with the sleeve switched on (harness has none there).")

# ------------------------------------------------------------------ compute everything
R = {}   # (tn, arm, var, lag, sens) -> (A, M)
import time; t0 = time.time()
for var in VARS:
    for a in ARMS:
        for tn in TRK:
            R[(tn, a, var, 0, False)] = run_arm(tn, a, var)
            for lag in (1,):
                R[(tn, a, var, lag, False)] = run_arm(tn, a, var, lag)
log(f"\n(computed {len(R)} arm/MC pairs in {time.time()-t0:.0f}s)")
def S_(tn, a, var, lag=0, sens=False):
    A, M = run_arm(tn, a, var, lag, sens); return stats(A['r']), stats(M['r'])

def cmp(tn, a, var, lag=0, sens=False):
    A, M = run_arm(tn, a, var, lag, sens); ra, rm = A['r'], M['r']; n = len(ra); hh = n // 2; x = YRS[tn] != '2020'
    sa, sm = stats(ra), stats(rm)
    return dict(dsh=sa['sh'] - sm['sh'], ddd=sa['m'] - sm['m'], dc=sa['c'] - sm['c'], dw5=sa['w5'] - sm['w5'], dw1=sa['w1'] - sm['w1'],
                h1=sh(ra[:hh]) - sh(rm[:hh]), h2=sh(ra[hh:]) - sh(rm[hh:]), x20=sh(ra[x]) - sh(rm[x]))

# ------------------------------------------------------------------ master tables
HDR = f"  {'arm':<20}{'CAGR':>7} {'Sharpe':>6} {'maxDD':>7} {'vol':>6} {'on%':>5} {'avgW':>6} {'tr/yr':>6} {'worst1':>7} {'worst5':>7}"
def line(l, res, st):
    on = (res['hw'] > 1e-9).mean() * 100; aw = res['hw'].mean() * 100
    return f"  {l:<20}{st['c']*100:6.1f}% {st['sh']:6.3f} {st['m']*100:6.1f}% {st['v']*100:5.1f}% {on:5.1f} {aw:5.2f}% {res['tpy']:6.1f} {st['w1']*100:6.2f}% {st['w5']*100:6.2f}%"
for var in VARS:
    for tn in TRK:
        log(f"\n=== MASTER TABLE: funding {var}, window {tn} ({RDS[tn][0]}..{RDS[tn][-1]}); each arm line followed by its matched cash (MC) line; avgW = mean hedge weight over all days, % of NAV ===")
        log(HDR); b = run_base(tn); log(line('Base', b, stats(b['r'])))
        for a in ARMS:
            A, M = run_arm(tn, a, var); log(line(lab(a), A, stats(A['r']))); log(line('   MC', M, stats(M['r'])))

# ------------------------------------------------------------------ verdicts
CMP = {(tn, a, var): cmp(tn, a, var) for tn in TRK for a in ARMS for var in VARS}
BT = {}
for var in VARS:
    for a in ARMS:
        for tn in TRK:
            A, M = run_arm(tn, a, var); BT[(tn, a, var)] = boot(A['r'], M['r'])
def core(a, var):
    c = {tn: CMP[(tn, a, var)] for tn in TRK}; tol = 1e-9
    a1 = all(c[t]['dsh'] >= -tol for t in c) and c['real']['ddd'] >= 0.01 - tol and c['vera']['ddd'] >= -tol
    a2 = all(c[t][k] >= -tol for t in c for k in ('h1', 'h2', 'x20'))
    b1 = all(c[t]['dsh'] > tol for t in c); b2 = all(c[t][k] > tol for t in c for k in ('h1', 'h2', 'x20'))
    return (a1 and a2) or (b1 and b2)
def grid(a):
    hs = sorted({x[3] for x in ARMS if GROUP(x) == GROUP(a)}); Ts = sorted({x[2] for x in ARMS if GROUP(x) == GROUP(a) and x[2] is not None})
    return hs, Ts
def neigh_ok(a, var):
    hs, Ts = grid(a); g = lambda T, h: next((x for x in ARMS if GROUP(x) == GROUP(a) and x[2] == T and x[3] == h), None)
    if a[1] == 'C1':
        i, j = Ts.index(a[2]), hs.index(a[3]); n = 0
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ii, jj = i + di, j + dj
            if 0 <= ii < len(Ts) and 0 <= jj < len(hs) and core(g(Ts[ii], hs[jj]), var): n += 1
        return n >= 2
    if a[1] in ('C4a', 'C4b'): return False
    cells = [g(a[2], h) for h in hs]; ps = [core(c, var) for c in cells]; i = hs.index(a[3])
    return any(all(ps[j:j + 3]) and j <= i < j + 3 for j in range(len(hs) - 2))
VER = {}
for var in VARS:
    for a in ARMS:
        co = core(a, var); P = min(BT[('real', a, var)][0], BT[('vera', a, var)][0]); c = {tn: CMP[(tn, a, var)] for tn in TRK}
        ins = c['real']['dsh'] < 0 and c['real']['ddd'] >= 0.01 and c['real']['dw5'] >= 0.005
        if not co: v = 'REJECT'
        elif not neigh_ok(a, var): v = 'REJECT (neighbours; would pass otherwise)' if a[1].startswith('C4') else 'REJECT (neighbours)'
        elif P >= 0.10: v = 'REJECT (bootstrap P>=0.10)'
        else: v = 'PASS'
        VER[(a, var)] = (v, ins)
for var in VARS:
    log(f"\n=== VERDICT TABLE, funding {var}: arm minus its matched cash. dSh Sharpe units; dDD pp (+ = arm shallower); h1/h2 halves, ex20 = 2020 removed (all dSharpe); P = bootstrap P(dSh<=0) ===")
    log(f"  {'arm':<20}| {'real: dSh   dDD    h1     h2     ex20    P':<46}| {'vera: dSh   dDD    h1     h2     ex20    P':<46}| verdict")
    for a in ARMS:
        cs = []
        for tn in TRK:
            c = CMP[(tn, a, var)]; cs.append(f"{c['dsh']:+.3f} {c['ddd']*100:+5.2f} {c['h1']:+.3f} {c['h2']:+.3f} {c['x20']:+.3f} {BT[(tn,a,var)][0]:.2f}")
        v, ins = VER[(a, var)]; log(f"  {lab(a):<20}| {cs[0]:<45} | {cs[1]:<45} | {v}{'  [INSURANCE FLAG]' if ins else ''}")
log("\nBOOTSTRAP detail (20-session circular blocks, %d paths, paired with MC): median dSharpe, P(dSh<=0), median dMaxDD pp, P(arm DD not shallower)" % NBOOT)
for var in VARS:
    log(f" funding {var}")
    for a in ARMS:
        log(f"  {lab(a):<20}" + ' | '.join(f"{tn}: {BT[(tn,a,var)][1]:+.3f} P{BT[(tn,a,var)][0]:.2f} dDD {BT[(tn,a,var)][3]*100:+.2f} P{BT[(tn,a,var)][2]:.2f}" for tn in TRK))

# ------------------------------------------------------------------ hedge-leg P&L
log("\n=== HEDGE-LEG STANDALONE P&L (prorata funding; ontop in second block): sum of hedge weight x instrument return, % of NAV. 'per yr' = total / years in window ===")
def pnl_row(tn, a, var):
    A, M = run_arm(tn, a, var); yrs = len(A['r']) / 252; c = A['ctb']; crack = CRK[tn]; on = A['hw'] > 1e-9
    cm = M['ctb']; net = c - cm
    inst = INSTR[tn][a[0]][WIN[tn][0] + 1:WIN[tn][1] + 1]
    oc = on & crack; oo = on & ~crack
    return dict(tot=c.sum() * 100, ann=c.sum() * 100 / yrs, crack=c[crack].sum() * 100, crack_ann=c[crack].sum() * 100 / yrs, oth=c[~crack].sum() * 100,
                oth_ann=c[~crack].sum() * 100 / yrs, net_ann=net.sum() * 100 / yrs, nc=int(crack.sum()), non=int(oc.sum()),
                i_crack=inst[oc].mean() * 100 if oc.any() else np.nan, i_crack_all=inst[crack].mean() * 100,
                i_oth_arith=inst[oo].mean() * 252 * 100 if oo.any() else np.nan, i_oth_geo=(np.prod(1 + inst[oo]) ** (252 / oo.sum()) - 1) * 100 if oo.any() else np.nan, n_oo=int(oo.sum()))
PN = {(tn, a, var): pnl_row(tn, a, var) for tn in TRK for a in ARMS for var in VARS}
for var in VARS:
    for tn in TRK:
        log(f"\n -- funding {var}, window {tn}: columns: total %NAV/yr | calm-crack days %NAV/yr (sum %NAV) | other days %NAV/yr | net of cash carry %NAV/yr | crack days hedge on/n | instrument mean ret on hedge-on crack days % | instrument ann. return on hedge-on non-crack days: arith / geometric %")
        for a in ARMS:
            p = PN[(tn, a, var)]
            log(f"  {lab(a):<20} tot {p['ann']:+7.3f} | crack {p['crack_ann']:+7.3f} ({p['crack']:+6.3f}) | other {p['oth_ann']:+7.3f} | net {p['net_ann']:+7.3f} | {p['non']}/{p['nc']} | {p['i_crack']:+6.2f} | {p['i_oth_arith']:+7.1f} / {p['i_oth_geo']:+7.1f}")

# ------------------------------------------------------------------ crack-day book returns
log("\n=== CALM-CRACK DAYS: mean book return (%) on the crack days in the window (all listed days, whatever the hedge did) ===")
for tn in TRK:
    b = run_base(tn)['r']; cm = CRK[tn]; qq = np.mean((H.pr if TRK[tn]['real'] else H.p)['qqq'][WIN[tn][0] + 1:WIN[tn][1] + 1][cm]) * 100
    log(f" window {tn}: n={int(cm.sum())}  QQQ {qq:+.2f}%  Base {b[cm].mean()*100:+.3f}%")
    for var in VARS:
        for a in ARMS:
            A, M = run_arm(tn, a, var)
            log(f"   {var:<8}{lab(a):<20} arm {A['r'][cm].mean()*100:+.3f}%  MC {M['r'][cm].mean()*100:+.3f}%  arm-MC {(A['r'][cm].mean()-M['r'][cm].mean())*100:+.3f}  arm-Base {(A['r'][cm].mean()-b[cm].mean())*100:+.3f}  hedge on {int(((A['hw']>1e-9)&cm).sum())}/{int(cm.sum())}")

# ------------------------------------------------------------------ best arms
def meand(a, var='prorata'): return np.mean([CMP[(tn, a, var)]['dsh'] for tn in TRK])
BEST = {i: max([a for a in ARMS if a[0] == i], key=meand) for i in 'YM'}
log(f"\nBEST by mean dSharpe vs MC over both windows (prorata): VIXY {lab(BEST['Y'])} ({meand(BEST['Y']):+.4f}); VIXM {lab(BEST['M'])} ({meand(BEST['M']):+.4f})")
C3MAX = ('Y', 'C3', None, 0.10)

# ------------------------------------------------------------------ episodes
log("\n=== NAMED EPISODES, real window, prorata: book return % on the day / cumulative over the day + next 5 sessions (6 sessions). Span row = 2024-07-24..2024-08-05 inclusive ===")
EP = ['2018-02-05', '2018-10-10', '2020-02-24', '2024-07-24', '2025-10-10', '2026-06-05', '2026-10-30', '2026-11-05']
ds_r = list(RDS['real']); show = [('Base', run_base('real')['r'])]
for nm_, a in (('best VIXY', BEST['Y']), ('best VIXM', BEST['M']), ('VIXY C3 h10', C3MAX)):
    A, M = run_arm('real', a, 'prorata'); show += [(f"{nm_} [{lab(a)}]", A['r']), (f"  its MC", M['r'])]
log(f"  {'episode':<28}" + ''.join(f"{n[:34]:>36}" for n, _ in show))
for d in EP + ['span']:
    if d == 'span': i0, i1 = ds_r.index('2024-07-24'), ds_r.index('2024-08-05'); lb = '2024-07-24..08-05'
    else:
        if d not in ds_r: continue
        i0 = ds_r.index(d); i1 = i0 + 5; lb = d
    cells = []
    for n, r in show:
        c1 = r[i0] * 100; cn = (np.prod(1 + r[i0:i1 + 1]) - 1) * 100
        cells.append(f"{c1:+7.2f}% / {cn:+7.2f}%".rjust(36))
    log(f"  {lb:<28}" + ''.join(cells))

# ------------------------------------------------------------------ year by year
log("\n=== YEAR BY YEAR, real window, prorata: arm minus its MC, pp of annual return; then ex-2020 and halves (Sharpe diff) ===")
MAIN = [('Y', 'C1', 18, 0.05), ('Y', 'C2', None, 0.05), ('Y', 'C3', None, 0.05), ('Y', 'C4a', 18, 0.05), ('Y', 'C4b', 18, 0.05), ('Y', 'C5', None, 0.05), BEST['M']]
if BEST['M'] not in MAIN: MAIN.append(BEST['M'])
log(f"  {'year':<6}" + ''.join(f"{lab(a)[:19]:>20}" for a in MAIN))
def yr(r, y): return np.prod(1 + r[YRS['real'] == y]) - 1
for y in sorted(set(YRS['real'])):
    row = []
    for a in MAIN:
        A, M = run_arm('real', a, 'prorata'); row.append((yr(A['r'], y) - yr(M['r'], y)) * 100)
    log(f"  {y:<6}" + ''.join(f"{x:20.2f}" for x in row))
for k, l in (('x20', 'dSharpe ex-2020'), ('h1', 'dSharpe 1st half'), ('h2', 'dSharpe 2nd half'), ('dsh', 'dSharpe full')):
    log(f"  {l:<16}" + ''.join(f"{CMP[('real', a, 'prorata')][k]:20.3f}" for a in MAIN))

# ------------------------------------------------------------------ lag
log("\n=== CALM-SIGNAL LAGGED ONE EXTRA DAY (C3 has no calm input: identical): dSh vs MC / dDD pp vs MC (lag0 in brackets) ===")
for var in VARS:
    log(f" funding {var}")
    for a in ARMS:
        cs = []
        for tn in TRK:
            c1 = cmp(tn, a, var, 1); c0 = CMP[(tn, a, var)]
            cs.append(f"{tn}: {c1['dsh']:+.3f}/{c1['ddd']*100:+.2f} [{c0['dsh']:+.3f}/{c0['ddd']*100:+.2f}]")
        log(f"  {lab(a):<20}" + ' | '.join(cs))

# ------------------------------------------------------------------ cost sensitivity
log("\n=== 5 bp one-way on VIXY/VIXM trades (sleeve and hedge; other legs 2 bp), prorata: dSh / dCAGR pp vs MC at 2 bp [and at 5 bp]; arm CAGR change from 5bp ===")
for a in ARMS:
    cs = []
    for tn in TRK:
        c5 = cmp(tn, a, 'prorata', 0, True); c2 = CMP[(tn, a, 'prorata')]
        cs.append(f"{tn}: dSh {c2['dsh']:+.3f} [5bp {c5['dsh']:+.3f}] dCAGR {c2['dc']*100:+.2f} [5bp {c5['dc']*100:+.2f}]")
    log(f"  {lab(a):<20}" + ' | '.join(cs))
for tn in TRK:
    b2 = stats(run_base(tn)['r']); b5 = stats(run_base(tn, True)['r']); log(f"  Base {tn} 2bp {b2['c']*100:.1f}%/{b2['sh']:.3f}  5bp on sleeve {b5['c']*100:.1f}%/{b5['sh']:.3f}")

# ------------------------------------------------------------------ VIXY vs VIXM
log("\n=== INSTRUMENT SIDE-BY-SIDE (same windows, same rule, prorata): VIXY at h vs VIXM at 2h (like-for-like) and VIXM at h; vs MC ===")
def sbs(a, tn, var='prorata'):
    A, M = run_arm(tn, a, var); sa, sm = stats(A['r']), stats(M['r']); p = PN[(tn, a, var)]; c = CMP[(tn, a, var)]
    return (f"{lab(a):<20} CAGR {sa['c']*100:5.1f}% (MC {sm['c']*100:5.1f}%, d {c['dc']*100:+.2f}) Sharpe {sa['sh']:.3f} (MC {sm['sh']:.3f}, d {c['dsh']:+.3f}) maxDD {sa['m']*100:6.1f}% "
            f"(MC {sm['m']*100:6.1f}%, d {c['ddd']*100:+.2f}) on {(A['hw']>1e-9).mean()*100:4.1f}% | hedge P&L %NAV/yr: crack {p['crack_ann']:+.3f} other {p['oth_ann']:+.3f} total {p['ann']:+.3f} net-of-cash {p['net_ann']:+.3f} | "
            f"instr mean ret on hedge-on crack days {p['i_crack']:+.2f}% ({p['non']}/{p['nc']}), ann. on other hedge-on days {p['i_oth_arith']:+.1f}% arith / {p['i_oth_geo']:+.1f}% geo (n={p['n_oo']})")
for tn in TRK:
    log(f"\n window {tn}")
    for a in (BEST['Y'], BEST['M']): log("  BEST " + sbs(a, tn))
    for fam, T in (('C1', 18), ('C2', None), ('C3', None), ('C5', None)):
        for h in (0.05, 0.10):
            ay = ('Y', fam, T, h); am1 = ('M', fam, T, h); am2 = ('M', fam, T, round(2 * h, 2))
            if ay not in ARMS or am2 not in ARMS: continue
            log("  " + sbs(ay, tn)); log("     " + sbs(am1, tn)); log("     " + sbs(am2, tn))


# ------------------------------------------------------------------ concentration
log("\n=== CONCENTRATION (added after the first run, not part of the pass bar): real window, prorata. dSharpe vs MC full / dropping the 1 / 3 / 5 days with the largest (arm - MC) daily gain; and the dates of the top 3 ===")
for a in ARMS:
    A, M = run_arm('real', a, 'prorata'); d = A['r'] - M['r']; o = np.argsort(-d); row = []
    for k in (0, 1, 3, 5):
        keep = np.ones(len(d), bool); keep[o[:k]] = False; row.append(sh(A['r'][keep]) - sh(M['r'][keep]))
    log(f"  {lab(a):<20} full {row[0]:+.3f} | -1 day {row[1]:+.3f} | -3 days {row[2]:+.3f} | -5 days {row[3]:+.3f} | top days " + ', '.join(f"{RDS['real'][i]} {d[i]*100:+.2f}%" for i in o[:3]))

# ------------------------------------------------------------------ final
log("\n=== FINAL VERDICTS vs pass bar (PLAN.md) ===")
for var in VARS:
    log(f" funding {var}")
    for a in ARMS: log(f"  {lab(a):<20} {VER[(a,var)][0]}{'  [INSURANCE FLAG: lower Sharpe, DD>=1pp shallower, worst5>=0.5pp better]' if VER[(a,var)][1] else ''}")
npass = {var: sum(VER[(a, var)][0] == 'PASS' for a in ARMS) for var in VARS}; log(f"\nPASS counts: {npass}; core-pass (before neighbours/bootstrap): " + str({var: sum(core(a, var) for a in ARMS) for var in VARS}))
log(f"run time {time.time()-t0:.0f}s")
