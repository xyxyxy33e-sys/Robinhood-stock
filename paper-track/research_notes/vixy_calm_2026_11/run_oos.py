"""Out-of-sample 2011-2015 check of the calm hedge. Research only. PLAN.md Addendum 2 (pre-registered). Reuses run.py logic (copied; run.py is not imported)."""
import csv, os, sys, re, bisect
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); PT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PT, 'review_2026_11'))
import harness as H
from harness import MC, S
VP = os.path.join(PT, 'research_notes', 'vol_predict_2026_11')
LOG = open(os.path.join(HERE, 'run_oos.log'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); LOG.write(s + '\n'); LOG.flush()
CAPCFG = dict(H.CUR, gross_cap=2.0); EPS = S.ZERO_LEG_EPS; BAND = S.REBALANCE_DRIFT_BAND
ds = H.PD; sg = H.sig; pn = H.p
END = len(ds) - 1
def idx_le(d): return max(i for i, x in enumerate(ds) if x <= d)
WINS = {'oos': ('2011-01-04', '2015-09-02'), 'late': ('2015-09-02', ds[-1]), 'joined': ('2011-01-04', ds[-1])}
WIN = {}
for k, (a, b) in WINS.items(): WIN[k] = (next(i for i, d in enumerate(ds) if d >= a), idx_le(b))

def load_close(fn):
    return {r['d']: float(r['close_split_adj']) for r in csv.DictReader(open(os.path.join(HERE, fn)))}
vy = load_close('vixy_yahoo_full.csv'); vm = load_close('vixm_yahoo_full.csv')
def rr(px):
    x = MC._rets(px, ds); x[0] = 0.0; return x
INSTR = {'Y': rr(vy), 'M': rr(vm)}
# data check vs the original run's VIXY / VIXM series on the overlap
vy_old = {r['d']: float(r['c']) for r in csv.DictReader(open(os.path.join(H.HERE, 'research_notes', 'vixm_followups_2026_11', 'vixy_daily.csv')))}
vm_old = MC._load('vixm_daily.csv')
for nm_, new, old in (('VIXY', vy, vy_old), ('VIXM', vm, vm_old)):
    com = sorted(set(new) & set(old)); a = np.array([new[d] for d in com]); b = np.array([old[d] for d in com])
    ra, rb = a[1:] / a[:-1] - 1, b[1:] / b[:-1] - 1
    log(f"data check {nm_}: new file {min(new)}..{max(new)} ({len(new)} rows); overlap with original series {com[0]}..{com[-1]} n={len(com)}; daily-return max abs diff {np.abs(ra-rb).max()*100:.3f}%, mean abs {np.abs(ra-rb).mean()*100:.4f}%")
CASHR = pn['cash']
_vd = {d: (None if np.isnan(v) else float(v)) for d, v in zip(ds, sg['vol'][0])}
_vx = S.vixm_series(ds, H.VIX, H.VIX3M, _vd)
VXA = np.array([bool(_vx.get(d, {}).get('allowed')) for d in ds])

def load_fred(fn):
    d = {}
    for r in csv.reader(open(os.path.join(VP, fn))):
        try: d[r[0]] = float(r[1])
        except Exception: pass
    keys = sorted(d); out = np.full(len(ds), np.nan)
    for i, x in enumerate(ds):
        j = bisect.bisect_right(keys, x) - 1
        if j >= 0: out[i] = d[keys[j]]
    return out
def base_parts():
    cfg = CAPCFG
    w5 = MC.target_weights(sg, cfg); key = MC.regime_key(sg, cfg).astype(np.int64)[0]
    cash = w5[0, :, 4].copy()
    legs = [pn['core'], pn['tqqq'], pn['qld'], pn['xlu']]; W = [w5[0, :, i] for i in range(4)]
    eff = MC._eff(sg, cfg)[0]; gate = MC._gate(sg, cfg)[0]; z = MC._zone(sg, cfg)[0]
    allowed = VXA & ~((eff == 3) & ~gate & (z == 2))
    v = np.where(allowed, cash * S.VIXM_CASH_SHARE, 0.0)
    legs.append(INSTR['Y']); W.append(v); used = v.copy(); key = key + allowed.astype(np.int64) * 100000
    g = np.nan_to_num(sg['gaps'][200][0])
    deep = ((eff == 4) & (g <= S.DEEP_E_GAP200)).astype(float) * S.DEEP_E_CASH_SHARE
    pan = H.panic_series(ds)
    for j, sh_ in enumerate((deep, pan)):
        x = np.minimum(cash * sh_, cash - used); used = used + x
        legs.append(pn['qqq']); W.append(x); key = key + (sh_ > 0).astype(np.int64) * (10 ** (6 + j))
    legs.append(pn['cash']); W.append(cash - used)
    return np.stack(W, -1), np.stack(legs, -1), key, eff, gate, allowed
Wb, Lb, kb, EFF, GATE, ALLOWED = base_parts()
vix = load_fred('VIXCLS.csv'); v3 = load_fred('VXVCLS.csv')
C = dict(vix=vix, ratio=vix / v3, rv=sg['vol'][0], gap=sg['gaps'][200][0], A=(EFF == 0), lev=(EFF == 0) | ((EFF == 3) & ~GATE), sleeve=Wb[:, 4] > 1e-12)
def active(fam, T):
    with np.errstate(invalid='ignore'):
        if fam == 'C1': x = C['vix'] < T
        elif fam == 'C3': x = np.ones(len(ds), bool)
        elif fam == 'C5': x = C['A'] & (C['gap'] > 0.10)
    return np.asarray(x, bool) & C['lev'] & ~C['sleeve']
def add_hedge(act, h):
    W = np.concatenate([Wb, np.zeros((len(Wb), 1))], 1)
    hv = np.where(act, h, 0.0); R = W[:, :4].sum(1); t2 = np.minimum(hv, R)
    sc = np.where(R > 1e-12, 1 - t2 / np.maximum(R, 1e-12), 1.0); W[:, :4] *= sc[:, None]; W[:, 8] = t2
    return W, kb + (W[:, 8] > 1e-12).astype(np.int64) * 10 ** 8
CV = np.full(9, MC.COST)
def engine(W, key, L, s0, e):
    n = e - s0; out = np.zeros(n); hw = np.zeros(n); ctb = np.zeros(n); h = W[s0].copy(); cost = MC.COST; tr = 0
    for t in range(s0, e):
        if t > s0:
            tgt = W[t]; diff = np.abs(tgt - h)
            if key[t] != key[t - 1] or diff.sum() > BAND or ((tgt == 0) & (h > EPS)).any():
                cost = float((diff * CV).sum()); h = tgt.copy(); tr += 1
            else: cost = 0.0
        r = L[t + 1]; g = float((h * r).sum()); out[t - s0] = (1 + g) * (1 - cost) - 1
        hw[t - s0] = h[8]; ctb[t - s0] = h[8] * r[8]; h = h * (1 + r) / (1 + g)
    return dict(r=out, hw=hw, ctb=ctb, tpy=tr / (n / 252))
def stats(r):
    nav = np.cumprod(1 + r); dd = (nav / np.maximum(np.maximum.accumulate(nav), 1) - 1).min(); v = r.std(ddof=1) * 252 ** .5
    return dict(c=nav[-1] ** (252 / len(r)) - 1, sh=r.mean() * 252 / v, m=dd, v=v, w1=r.min(), w5=float(np.expm1(np.convolve(np.log1p(r), np.ones(5), 'valid')).min()))
_b = {}
def run_base(w):
    if w not in _b:
        s0, e = WIN[w]; W = np.concatenate([Wb, np.zeros((len(Wb), 1))], 1); L = np.concatenate([Lb, np.zeros((len(Lb), 1))], 1); _b[w] = engine(W, kb, L, s0, e)
    return _b[w]
_c = {}
def run_arm(w, arm):
    if (w, arm) in _c: return _c[(w, arm)]
    inst, fam, T, h = arm; s0, e = WIN[w]; W, k = add_hedge(active(fam, T), h)
    La = np.concatenate([Lb, INSTR[inst][:, None]], 1); Lm = np.concatenate([Lb, CASHR[:, None]], 1)
    _c[(w, arm)] = (engine(W, k, La, s0, e), engine(W, k, Lm, s0, e)); return _c[(w, arm)]
ARMS = [('Y', 'C1', 18, .05), ('Y', 'C1', 20, .05), ('M', 'C1', 18, .10), ('Y', 'C5', None, .05), ('M', 'C5', None, .10), ('M', 'C5', None, .20), ('Y', 'C3', None, .05)]
def lab(a): return f"{'VIXY' if a[0]=='Y' else 'VIXM'} {a[1]}{'' if a[2] is None else ' T%d' % a[2]} h{a[3]*100:g}"
RDS = {w: ds[WIN[w][0] + 1:WIN[w][1] + 1] for w in WIN}
txt = open(os.path.join(VP, 'analyze.log')).read().split('biggest surprises')[1].split('big up days')[0]
CD = set(re.findall(r'^(\d{4}-\d\d-\d\d)\s+-0\.', txt, re.M))
CRK = {w: np.array([d in CD for d in RDS[w]]) for w in WIN}
YRS = {w: np.array([d[:4] for d in RDS[w]]) for w in WIN}
def sh(r): return r.mean() * 252 / (r.std(ddof=1) * 252 ** .5)

log('=' * 130); log('run_oos.py: out-of-sample 2011-2015 check of the calm hedge (PLAN.md Addendum 2). Research only.'); log('=' * 130)
log("Proxy panel legs: core QQQ price +0.6%/yr div; TQQQ/QLD synthetic 3x/2x with T-bill+0.3% financing and 0.84%/0.95% ER; XLU long history +3% yield; cash = 3m T-bill accrual; QQQ cash legs = QQQ. VIXY/VIXM real (split-adjusted closes).")
log("Signals: close of t decides hedge traded at close t (same-day VIX/VIX3M, rv30, gap200). Sleeve: VIXY 35% of cash leg, same latch (harness VIX/VIX3M history), VIXY returns for the whole history.")
for w in WIN: log(f"window {w}: returns {RDS[w][0]}..{RDS[w][-1]} ({len(RDS[w])} sessions); calm-crack days inside: {int(CRK[w].sum())}")
oos_crack = [d for d in RDS['oos'] if d in CD]
log(f"calm-crack days (analyze.log list) in OOS window: {oos_crack}")
log(f"share of OOS sessions with sleeve allowed (latch on, any cash): {ALLOWED[WIN['oos'][0]:WIN['oos'][1]].mean()*100:.1f}%; sleeve actually holding: {C['sleeve'][WIN['oos'][0]:WIN['oos'][1]].mean()*100:.1f}%; leveraged state (A or ungated D): {C['lev'][WIN['oos'][0]:WIN['oos'][1]].mean()*100:.1f}%; state A: {C['A'][WIN['oos'][0]:WIN['oos'][1]].mean()*100:.1f}%; VIX<18: {(C['vix'][WIN['oos'][0]:WIN['oos'][1]]<18).mean()*100:.1f}%; VIX<20: {(C['vix'][WIN['oos'][0]:WIN['oos'][1]]<20).mean()*100:.1f}%")
log("\nBASELINES (proxy panel, cap 2.0, VIXY 35% sleeve)")
for w in WIN:
    b = run_base(w); x = stats(b['r']); log(f"  Base {w:<7} CAGR {x['c']*100:.1f}% Sharpe {x['sh']:.3f} maxDD {x['m']*100:.1f}% vol {x['v']*100:.1f}% worst1 {x['w1']*100:.2f}% worst5 {x['w5']*100:.2f}% trades/yr {b['tpy']:.1f}")
log("  (original run.log 'vera' Base for the late window: 52.1% / 2.031 / -20.1%)")

def cmpd(w, a):
    A, M = run_arm(w, a); sa, sm = stats(A['r']), stats(M['r']); return sa, sm, dict(dsh=sa['sh'] - sm['sh'], ddd=sa['m'] - sm['m'], dc=sa['c'] - sm['c'])
def pnl(w, a):
    A, M = run_arm(w, a); yrs = len(A['r']) / 252; c = A['ctb']; k = CRK[w]; on = A['hw'] > 1e-9; inst = INSTR[a[0]][WIN[w][0] + 1:WIN[w][1] + 1]; oo = on & ~k
    return dict(tot=c.sum() * 100 / yrs, crack=c[k].sum() * 100 / yrs, oth=c[~k].sum() * 100 / yrs, net=(c - M['ctb']).sum() * 100 / yrs, non=int((on & k).sum()), nc=int(k.sum()),
                ia=inst[oo].mean() * 252 * 100 if oo.any() else np.nan, ig=(np.prod(1 + inst[oo]) ** (252 / oo.sum()) - 1) * 100 if oo.any() else np.nan, n=int(oo.sum()))
for w in WIN:
    log(f"\n=== ARM vs MATCHED CASH, window {w} ({RDS[w][0]}..{RDS[w][-1]}) ; pro-rata funding ===")
    log(f"  {'arm':<18}{'CAGR arm/MC':>15}{'dCAGR':>7} {'Sharpe arm/MC':>15}{'dSh':>7} {'maxDD arm/MC':>17}{'dDD':>6} {'on%':>5} {'avgW':>6} | {'worst1 arm/MC':>15} {'worst5 arm/MC':>17}")
    for a in ARMS:
        A, M = run_arm(w, a); sa, sm, d = cmpd(w, a)
        log(f"  {lab(a):<18}{sa['c']*100:6.1f}/{sm['c']*100:5.1f}%{d['dc']*100:+7.2f} {sa['sh']:7.3f}/{sm['sh']:.3f}{d['dsh']:+7.3f} {sa['m']*100:7.1f}/{sm['m']*100:6.1f}%{d['ddd']*100:+6.2f} {(A['hw']>1e-9).mean()*100:5.1f} {A['hw'].mean()*100:5.2f}% | {sa['w1']*100:6.2f}/{sm['w1']*100:6.2f}% {sa['w5']*100:7.2f}/{sm['w5']*100:6.2f}%")
log("\n=== HEDGE-LEG STANDALONE P&L, % of NAV per year: total | calm-crack days | other days | net of cash carry | crack days hedge on/n | instrument ann. return on hedge-on non-crack days (arith/geo, n days) ===")
for w in WIN:
    log(f" window {w}")
    for a in ARMS:
        p = pnl(w, a); log(f"  {lab(a):<18} tot {p['tot']:+7.3f} | crack {p['crack']:+7.3f} | other {p['oth']:+7.3f} | net {p['net']:+7.3f} | {p['non']}/{p['nc']} | {p['ia']:+7.1f}% / {p['ig']:+7.1f}% (n={p['n']})")
log("\n=== OOS CALM-CRACK DAYS: state at prior close, base/arm/matched-cash book return, hedge on? ===")
w = 'oos'; s0 = WIN[w][0]; b = run_base(w)['r']
for d in oos_crack:
    i = RDS[w].index(d); t = s0 + i      # decision at close of session t=prev day
    st = 'ABCDEF'[EFF[t]] + ('(gated)' if EFF[t] == 3 and GATE[t] else '')
    qq = pn['qqq'][s0 + 1 + i] * 100
    row = f"  {d}: QQQ {qq:+.2f}% prior-close state {st}, prior VIX {C['vix'][t]:.2f}, sleeve holding {bool(C['sleeve'][t])}; Base {b[i]*100:+.2f}%"
    for a in ARMS:
        A, M = run_arm(w, a); row += f" | {lab(a)}: {A['r'][i]*100:+.2f}% (MC {M['r'][i]*100:+.2f}%) {'ON' if A['hw'][i]>1e-9 else 'off'}"
    log(row)
log("\n=== YEAR BY YEAR in the OOS window: arm minus matched cash (pp); 2015 = Jan..Sep-02 ===")
log(f"  {'year':<6}{'Base':>8}" + ''.join(f"{lab(a):>19}" for a in ARMS))
for y in ('2011', '2012', '2013', '2014', '2015'):
    m = YRS['oos'] == y; row = f"  {y:<6}{(np.prod(1+b[m])-1)*100:7.1f}%"
    for a in ARMS:
        A, M = run_arm('oos', a); row += f"{(np.prod(1+A['r'][m])-np.prod(1+M['r'][m]))*100:19.2f}"
    log(row)
log("\n=== NAMED OOS EPISODES: cumulative book return % over the span (Base | arm (matched cash) per arm). Span inclusive of both ends; single dates also show day+5 sessions ===")
EPS_ = [('2011-08-04..08-10', '2011-08-04', '2011-08-10'), ('2012 full year', '2012-01-03', '2012-12-31'), ('2013-06 (month)', '2013-06-03', '2013-06-28'),
        ('2014-04-10 day', '2014-04-10', '2014-04-10'), ('2014-04-10 +5 sessions', '2014-04-10', None), ('2014-10-09..10-15', '2014-10-09', '2014-10-15'), ('2015-08-21..08-26', '2015-08-21', '2015-08-26')]
rd = list(RDS['oos'])
for nm_, a0, a1 in EPS_:
    i0 = next(i for i, d in enumerate(rd) if d >= a0); i1 = i0 + 5 if a1 is None else max(i for i, d in enumerate(rd) if d <= a1)
    cum = lambda r: (np.prod(1 + r[i0:i1 + 1]) - 1) * 100
    row = f"  {nm_:<24} Base {cum(b):+7.2f}%"
    for a in ARMS:
        A, M = run_arm('oos', a); row += f" | {lab(a)[:11]}{lab(a)[11:]} {cum(A['r']):+.2f} ({cum(M['r']):+.2f})"
    log(row)
log("\n=== READING RULE (PLAN.md Addendum 2), OOS window alone ===")
log(f"  calm-crack days in OOS window: {len(oos_crack)} ({', '.join(oos_crack)}).")
for a in ARMS:
    sa, sm, d = cmpd('oos', a)
    contra = d['dsh'] < -0.02 or (d['dc'] < -0.01 and d['ddd'] < 0.001)
    conf = d['dsh'] > 0 and d['ddd'] >= -0.005
    v = 'CONTRADICTED' if contra else ('CONFIRMED' if conf else 'INCONCLUSIVE')
    isv = {'Y C1 T18 h5': 'in-sample PASS', 'Y C1 T20 h5': 'in-sample PASS', 'M C1 T18 h10': 'in-sample PASS', 'Y C5 h5': 'in-sample neighbours-fail', 'M C5 h10': 'in-sample PASS', 'M C5 h20': 'in-sample PASS', 'Y C3 h5': 'in-sample REJECT'}
    log(f"  {lab(a):<18} dSh {d['dsh']:+.3f}  dCAGR {d['dc']*100:+.2f} pp  dDD {d['ddd']*100:+.2f} pp  -> {v}")
