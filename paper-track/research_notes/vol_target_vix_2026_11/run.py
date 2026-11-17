"""VIX / VXN in the vol-target estimator. Research only. See PLAN.md (pre-registered)."""
import csv, os, sys, re
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); PT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PT, 'review_2026_11'))
import harness as H
from harness import MC, S
VP = os.path.join(PT, 'research_notes', 'vol_predict_2026_11')
LOG = open(os.path.join(HERE, 'run.log'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); LOG.write(s + '\n'); LOG.flush()
GE = np.array(S.GROSS_EXPOSURE)
TR = {'real': (True, '2015-11-02'), 'proxy': (False, '2001-01-02'), 'p2010': (False, '2010-01-01')}
AX = {True: (H.RD, H.sr), False: (H.PD, H.sig)}
def load(fn, ds):
    d = {}
    for r in csv.reader(open(os.path.join(VP, fn))):
        try: d[r[0]] = float(r[1]) / 100
        except Exception: pass
    out = np.full(len(ds), np.nan); last = np.nan; keys = sorted(d)
    import bisect
    for i, x in enumerate(ds):
        j = bisect.bisect_right(keys, x) - 1          # last observation on or before x
        out[i] = d[keys[j]] if j >= 0 else np.nan
    return out
IND = {real: dict(vix=load('VIXCLS.csv', AX[real][0]), vxn=load('VXNCLS.csv', AX[real][0])) for real in (True, False)}
VXN_START = '2001-02-02'
for real in (True, False):
    ds = AX[real][0]; m = np.array([d < VXN_START for d in ds]); IND[real]['vxn'][m] = np.nan
def lagged(a, lag): return a if not lag else np.concatenate([np.full(lag, np.nan), a[:-lag]])

rv30p = H.sig['vol'][0]; vp = IND[False]['vix']; okm = np.array([d >= '2001-01-02' for d in H.PD]) & np.isfinite(rv30p) & np.isfinite(vp)
KMED = round(float(np.median(rv30p[okm] / vp[okm])), 2)
okr = np.array([d >= '2015-11-02' for d in H.PD]) & np.isfinite(rv30p) & np.isfinite(vp)
okh = np.array([d >= '2010-01-01' for d in H.PD]) & np.isfinite(rv30p) & np.isfinite(vp)

K1 = [0.8, 0.9, 1.0, 1.1, 1.2]; K2 = [0.7, 0.8, 0.9, 1.0]
ARMS = [('Base',)] + [('V1', k) for k in K1] + [('V2', k) for k in K2] + [('V3', w, k) for w in (0.25, 0.5) for k in (1.0, KMED)] \
     + [('V4', k) for k in (1.0, 1.2, KMED)] + [('V5', k) for k in K1]
def nm(a): return 'Base' if a[0] == 'Base' else a[0] + ' ' + ' '.join(f'{x:g}' for x in a[1:])
def fam(a): return a[0]

CFGS = {'cap2.0': dict(H.CUR, gross_cap=2.0), 'nocap': dict(H.CUR)}
_vc = {}
def estimator(real, spec, lag, cfg):
    sg = AX[real][1]; base = np.fmax(sg['vol'][0], sg['vol10'][0]); nanm = np.isnan(sg['vol'][0])
    if spec[0] == 'Base': return base
    vix = lagged(IND[real]['vix'], lag); vxn = lagged(IND[real]['vxn'], lag)
    f = spec[0]
    if f == 'V1': v = np.fmax(base, spec[1] * vix)
    elif f == 'V2': v = np.fmax(base, spec[1] * vxn)
    elif f == 'V3': v = spec[1] * (spec[2] * vix) + (1 - spec[1]) * base
    elif f == 'V4': v = spec[1] * vix
    elif f == 'V5':
        e = MC._eff(sg, cfg)[0]; g = MC._gate(sg, cfg)[0].astype(bool)
        calm = (e == 0) | ((e == 3) & ~g)
        v = np.where(calm, np.fmax(base, spec[1] * vix), base)
    v = np.where(np.isnan(v), base, v)
    return np.where(nanm, np.nan, v)
def mult(v, vt): return np.where(np.isnan(v) | (v <= 0), 1.0, np.minimum(1.0, vt / np.where(v > 0, v, 1)))
def build(real, spec, lag, cfgname, vt=None):
    key = (real, spec, lag, cfgname, vt)
    if key in _vc: return _vc[key]
    cfg = dict(CFGS[cfgname]); cfg['vol'] = 'max10_30'
    if vt: cfg['vol_target'] = vt
    v = estimator(real, spec, lag, CFGS[cfgname]); ds = AX[real][0]
    sg2 = dict(AX[real][1]); sg2['vol'] = v[None]; sg2['vol10'] = v[None]
    W, L, k = H.weights(sg2, ds, real, cfg=cfg)
    gross = (MC.target_weights(sg2, cfg)[0, :, :4] * GE).sum(-1)
    out = (W, L, k, gross, v); _vc[key] = out; return out
def window(real, w):
    ds = AX[real][0]; d0 = TR[w][1]; s0 = next(i for i, d in enumerate(ds) if d >= d0); return s0, len(ds) - 1
def runw(real, spec, lag, cfgname, w, vt=None):
    W, L, k, gross, v = build(real, spec, lag, cfgname, vt); ds = AX[real][0]; s0, e = window(real, w)
    r, tr = MC.run_strategy(W[None, :e + 1], k[None, :e + 1], L[None, :e + 1], s0)
    return dict(r=r[0], ds=ds[s0 + 1:e + 1], tpy=tr[0] / ((e - s0) / 252), gross=float(gross[s0:e].mean()), v=v, vt=vt, s0=s0, e=e)
def match(real, spec, lag, cfgname, w):
    """vol_target for Base so that avg target gross over window equals the arm's."""
    s0, e = window(real, w); tgt = build(real, spec, lag, cfgname)[3][s0:e].mean()
    lo, hi = 0.05, 0.60
    for _ in range(30):
        mid = (lo + hi) / 2
        g = build(real, ('Base',), 0, cfgname, round(mid, 6))[3][s0:e].mean()
        if g < tgt: lo = mid
        else: hi = mid
    return round((lo + hi) / 2, 6)
def metrics(res, real, base_res=None):
    r = res['r']; st = H.stats(r, H.cash_for(res['ds'], real)); r5 = np.expm1(np.convolve(np.log1p(r), np.ones(5), 'valid')).min()
    st.update(g=res['gross'], tpy=res['tpy'], w1=r.min(), w5=r5, bind=np.nan)
    if base_res is not None:
        s0, e = res['s0'], res['e']
        mb = mult(base_res['v'], 0.20)[s0:e]; ma = mult(res['v'], 0.20)[s0:e] if res['vt'] is None else mult(res['v'], res['vt'])[s0:e]
        st['bind'] = float((np.abs(ma - mb) > 1e-9).mean())
    return st
def line(lab, s):
    b = '   -  ' if np.isnan(s['bind']) else f"{s['bind']*100:5.1f}%"
    return f"  {lab:<22}{s['c']*100:7.1f}% {s['sh']:6.3f} {s['m']*100:7.1f}% {s['v']*100:6.1f}% {s['g']:6.3f} {b} {s['tpy']:6.1f} {s['w1']*100:7.2f}% {s['w5']*100:7.2f}%"
HDR = f"  {'arm':<22}{'CAGR':>8} {'Sharpe':>6} {'maxDD':>8} {'vol':>7} {'gross':>6} {'bind':>6} {'tr/yr':>6} {'worst1':>8} {'worst5':>8}"

def sh(r): return r.mean() * 252 / (r.std(ddof=1) * 252 ** .5)
def mdd(r): n = np.cumprod(1 + r); return (n / np.maximum.accumulate(np.concatenate([[1.0], n]))[1:] - 1).min()
def boot_idx(N, n, block=20, seed=11):
    rng = np.random.default_rng(seed); nb = -(-N // block)
    st = rng.integers(N, size=(n, nb)); return ((st[:, :, None] + np.arange(block)) % N).reshape(n, -1)[:, :N]
def boot_p(ra, rm, idx):
    a, m = ra[idx], rm[idx]
    s = lambda x: x.mean(1) / x.std(1, ddof=1)
    d = (s(a) - s(m)) * 252 ** .5
    return float((d <= 0).mean()), float(np.median(d))
BIDX = {}
def compare(A, M, w):
    ra, rm = A['r'], M['r']; ds = np.array(A['ds']); n = len(ra); h = n // 2
    yr = np.array([d[:4] for d in ds]); x = yr != '2020'
    N = len(ra)
    if N not in BIDX: BIDX[N] = boot_idx(N, NBOOT)
    p, md = boot_p(ra, rm, BIDX[N])
    return dict(dsh=sh(ra) - sh(rm), ddd=mdd(ra) - mdd(rm), h1=sh(ra[:h]) - sh(rm[:h]), h2=sh(ra[h:]) - sh(rm[h:]),
                x20=sh(ra[x]) - sh(rm[x]), p=p, medd=md)
NBOOT = 2000

def evaluate(cfgname, full):
    R = {}
    for tn, (real, d0) in TR.items():
        base = runw(real, ('Base',), 0, cfgname, tn); R[(tn, 'Base', 0)] = (base, None, metrics(base, real, base), None)
        for a in ARMS[1:]:
            for lag in (0, 1):
                if lag and not full: continue
                A = runw(real, a, lag, cfgname, tn); vt = match(real, a, lag, cfgname, tn)
                M = runw(real, ('Base',), 0, cfgname, tn, vt)
                R[(tn, a, lag)] = (A, M, metrics(A, real, base), metrics(M, real, base), compare(A, M, tn), vt)
    return R

def core(R, a, lag=0):
    for tn in ('real', 'proxy'):
        c = R[(tn, a, lag)][4]
        if not (c['dsh'] > 0 and c['ddd'] >= -0.005 and c['h1'] > 0 and c['h2'] > 0 and c['x20'] > 0): return False
    return True
def verdict(R, a):
    if not core(R, a): return 'REJECT', 'fails core (see flags)'
    f = fam(a)
    grid = [b for b in ARMS if fam(b) == f]
    cp = [core(R, b) for b in grid]
    if f in ('V3', 'V4'): okn = sum(cp) >= 3
    else:
        i = grid.index(a); okn = any(all(cp[j:j + 3]) and j <= i < j + 3 for j in range(len(grid) - 2))
    if not okn: return 'REJECT', 'no 3 contiguous/neighbour k pass'
    if min(R[('real', a, 0)][4]['p'], R[('proxy', a, 0)][4]['p']) >= 0.10: return 'REJECT', 'bootstrap P >= 0.10 on both tracks'
    return 'PASS', ''

def verdict_table(R, label):
    log(f"\nVERDICT TABLE ({label}) -- arm minus its matched de-lever; dSh in Sharpe units, dDD in pp (positive = arm less deep)")
    log(f"  {'arm':<12}|{'track':<6}{'dSh':>7}{'dDD':>6}{'H1':>7}{'H2':>7}{'ex20':>7}{'P':>6}  |" + ' real/proxy/p2010 repeated | verdict')
    out = {}
    for a in ARMS[1:]:
        cells = []
        for tn in ('real', 'proxy', 'p2010'):
            c = R[(tn, a, 0)][4]
            cells.append(f"{tn[:5]}:{c['dsh']:+.3f}/{c['ddd']*100:+.2f}/{c['h1']:+.3f}/{c['h2']:+.3f}/{c['x20']:+.3f}/P{c['p']:.2f}")
        v, why = verdict(R, a); out[a] = v
        log(f"  {nm(a):<12}| " + ' | '.join(cells) + f" | {v} {why}")
    log("  (cell = dSh / dDD pp / dSh first half / second half / ex-2020 / bootstrap P; p2010 is informational only)")
    return out

def master(R, tn, real):
    log(f"\n--- window {tn} ({TR[tn][1]} .. {AX[real][0][-1]}) ---"); log(HDR)
    b = R[(tn, 'Base', 0)]; log(line('Base', b[2]))
    for a in ARMS[1:]:
        x = R[(tn, a, 0)]; log(line(nm(a), x[2])); log(line('  MD vt=%.4f' % x[5], x[3]) + ('  beats MD Sh' if x[4]['dsh'] > 0 else '  loses to MD Sh'))

log('=' * 120); log('run.py: VIX/VXN vol-target estimator study (2026-11-17), PLAN.md pre-registered'); log('=' * 120)
log(f"Convention: new input (VIX/VXN close of day t) sets the multiplier traded at close t, same as harness rv and harness VIXM/panic VIX. lag=1 uses t-1.")
log(f"Harness VIX (sleeve/panic latch, unchanged) last date: {max(H.VIX)} ; FRED file last date used for the estimator: {AX[False][0][-1]} (ffill)")
log(f"Median rv30/VIX: 2001-26 {np.median(rv30p[okm]/vp[okm]):.3f}; real window {np.median(rv30p[okr]/vp[okr]):.3f}; 2010+ {np.median(rv30p[okh]/vp[okh]):.3f}; "
    f"quartiles 2001-26 {np.percentile(rv30p[okm]/vp[okm],25):.2f}/{np.percentile(rv30p[okm]/vp[okm],75):.2f}. KMED used = {KMED}")
vx = IND[False]['vxn']; okx = np.isfinite(vx) & okm; log(f"Median rv30/VXN 2001-26 {np.median(rv30p[okx]/vx[okx]):.3f}; median VXN/VIX {np.median(vx[okx]/vp[okx]):.3f}")

log("\nBASELINE REPRODUCTION (harness as-is, nothing changed)")
for real in (True, False):
    r, ds, tpy = H.run(real); log(f"  harness default (no gross cap, VIXM) {'real ' if real else 'proxy'} {H.fmt(H.stats(r, H.cash_for(ds, real)))} {tpy:.0f} tr/yr")
    r, ds, tpy = H.run(real, cfg=CFGS['cap2.0']); log(f"  CUR + gross_cap 2.0 (main baseline)  {'real ' if real else 'proxy'} {H.fmt(H.stats(r, H.cash_for(ds, real)))} {tpy:.0f} tr/yr")
r, ds, _ = H.run(False, d0='2010-01-01', cfg=CFGS['cap2.0']); log(f"  CUR + cap, proxy from 2010-01-01      {H.fmt(H.stats(r, H.cash_for(ds, False)))}")
log("  (harness has no L1 gate; the harness default has no 2.0x cap and uses the VIXM sleeve, so it differs from the quoted VIXY numbers)")
r0, d0_, _ = H.run(True, cfg=CFGS['cap2.0']); assert np.allclose(runw(True, ('Base',), 0, 'cap2.0', 'real')['r'], r0), 'my base != harness base'
log("  check: run.py Base reproduces harness CUR+cap returns exactly (real track)")

RM = evaluate('cap2.0', True)
for tn, (real, _) in TR.items(): master(RM, tn, real)
VM = verdict_table(RM, 'cap2.0 main')

log("\nLAG-1 ROBUSTNESS (new input lagged one extra day; MD re-matched): dSh vs MD / dDD pp, tracks real | proxy | p2010")
for a in ARMS[1:]:
    log(f"  {nm(a):<12}" + ' | '.join(f"{tn}: {RM[(tn,a,1)][4]['dsh']:+.3f}/{RM[(tn,a,1)][4]['ddd']*100:+.2f}  vsBase {RM[(tn,a,1)][2]['sh']-RM[(tn,'Base',0)][2]['sh']:+.3f}" for tn in TR))
log("  (no-lag for comparison: vsBase Sharpe change) " + ' | '.join(f"{tn}: V1 1.0 {RM[(tn,('V1',1.0),0)][2]['sh']-RM[(tn,'Base',0)][2]['sh']:+.3f}" for tn in TR))

log("\nBOOTSTRAP detail (20-session circular blocks, %d paths, paired with MD): median dSh (annualised units) and one-sided P(dSh<=0)" % NBOOT)
for a in ARMS[1:]:
    log(f"  {nm(a):<12}" + ' | '.join(f"{tn}: med {RM[(tn,a,0)][4]['medd']:+.3f} P {RM[(tn,a,0)][4]['p']:.3f}" for tn in TR))

log("\nYEAR BY YEAR, real track, arm minus Base (pp) and arm minus MD (pp), and 2020-removed Sharpe")
real_r = {a: RM[('real', a, 0)] for a in ARMS[1:]}; base_r = RM[('real', 'Base', 0)][0]
yrs = sorted({d[:4] for d in base_r['ds']})
def ann(r, ds, y): m = np.array([d[:4] == y for d in ds]); return np.prod(1 + r[m]) - 1
for F in ('V1', 'V2', 'V3', 'V4', 'V5'):
    arms = [a for a in ARMS if fam(a) == F]
    for lab, ix in (('minus Base', 0), ('minus MD', 1)):
        log(f"  {F} {lab:<10}" + ''.join(f"{nm(a)[3:]:>9}" for a in arms))
        for y in yrs:
            row = []
            for a in arms:
                A = real_r[a][0]; ref = base_r if ix == 0 else real_r[a][1]
                row.append((ann(A['r'], A['ds'], y) - ann(ref['r'], ref['ds'], y)) * 100)
            log(f"    {y}        " + ''.join(f"{x:9.2f}" for x in row))
for F in ('V1', 'V5'):
    for a in [a for a in ARMS if fam(a) == F]:
        c = RM[('real', a, 0)]; log(f"  ex-2020 real Sharpe {nm(a)}: arm {sh(c[0]['r'][np.array([d[:4]!='2020' for d in c[0]['ds']])]):.3f} MD {sh(c[1]['r'][np.array([d[:4]!='2020' for d in c[1]['ds']])]):.3f} Base {sh(base_r['r'][np.array([d[:4]!='2020' for d in base_r['ds']])]):.3f}")

log("\nCALM-CRACK DAYS (QQQ <= -3%, prior-day VIX < 20; analyze.log section 7): mean strategy return on those days (%)")
txt = open(os.path.join(VP, 'analyze.log')).read().split('biggest surprises')[1].split('big up days')[0]
CD = re.findall(r'^(\d{4}-\d\d-\d\d)\s+-0\.', txt, re.M); log(f"  {len(CD)} days listed")
def best(F):
    arms = [a for a in ARMS if fam(a) == F]
    return max(arms, key=lambda a: (RM[('real', a, 0)][4]['dsh'] + RM[('proxy', a, 0)][4]['dsh']) / 2)
b1, b5 = best('V1'), best('V5'); log(f"  best V1 by mean dSh vs MD (real, proxy): {nm(b1)};  best V5: {nm(b5)}")
for tn in ('real', 'proxy', 'p2010'):
    ds = RM[(tn, 'Base', 0)][0]['ds']; ix = [ds.index(d) for d in CD if d in ds]
    if not ix: log(f"  {tn}: no listed days in window"); continue
    def avg(res): return np.mean(res['r'][ix]) * 100
    qq = np.mean([H.pr['qqq'][H.RD.index(d)] if tn == 'real' else H.p['qqq'][H.PD.index(d)] for d in CD if d in ds]) * 100
    log(f"  {tn:<6} n={len(ix):>2}: QQQ {qq:+.2f}%  Base {avg(RM[(tn,'Base',0)][0]):+.2f}%  " + '  '.join(
        f"{nm(a)} {avg(RM[(tn,a,0)][0]):+.2f}% (MD {avg(RM[(tn,a,0)][1]):+.2f}%)" for a in ([a for a in ARMS if fam(a) in ('V1', 'V5')])))
    log(f"     best V1 {nm(b1)} {avg(RM[(tn,b1,0)][0]):+.2f}% vs its MD {avg(RM[(tn,b1,0)][1]):+.2f}%;  best V5 {nm(b5)} {avg(RM[(tn,b5,0)][0]):+.2f}% vs its MD {avg(RM[(tn,b5,0)][1]):+.2f}%")
log("  2026-11-05 (-6.5%): " + ', '.join(f"{n}: {RM[('real',a,0)][0]['r'][RM[('real','Base',0)][0]['ds'].index('2026-11-05')]*100:+.2f}%" for n, a in (('Base', 'Base'), ('V1 1.0', ('V1', 1.0)), ('V5 1.0', ('V5', 1.0)), ('V4 1.0', ('V4', 1.0)))) if '2026-11-05' in RM[('real','Base',0)][0]['ds'] else '')

log("\nROBUSTNESS: harness default WITHOUT the 2.0x cap (verdict table only)")
RN = evaluate('nocap', False)
for tn, (real, _) in TR.items():
    log(f"  Base nocap {tn}: " + H.fmt(RN[(tn, 'Base', 0)][2]) + f" gross {RN[(tn,'Base',0)][2]['g']:.3f}")
def vt2(R):
    for a in ARMS[1:]:
        log(f"  {nm(a):<12}" + ' | '.join(f"{tn}: dSh {R[(tn,a,0)][4]['dsh']:+.3f} dDD {R[(tn,a,0)][4]['ddd']*100:+.2f} P {R[(tn,a,0)][4]['p']:.2f}" for tn in TR))
vt2(RN)

log("\nFINAL VERDICTS (main = cap 2.0)")
for a in ARMS[1:]: log(f"  {nm(a):<12} {VM[a]}  core-pass {core(RM, a)}  p2010 beats MD Sharpe: {RM[('p2010', a, 0)][4]['dsh'] > 0}")
