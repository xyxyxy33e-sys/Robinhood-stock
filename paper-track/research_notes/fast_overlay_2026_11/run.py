"""Fast re-entry overlay study (research only). See PLAN.md (pre-registered 2026-11-17 before any arm was run)."""
import sys, os, time, math
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); PT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, PT)
import numpy as np
import harness_live as HL
from harness_live import MC, S, H
LOG = open(os.path.join(HERE, 'run.log'), 'w'); TB = open(os.path.join(HERE, 'tables.md'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); LOG.write(s + '\n'); LOG.flush()
def tb(s=''): TB.write(s + '\n')
T0 = time.time()
NBOOT, BLOCK = 2000, 20
WINS = {'real': ('real', '2015-11-02'), 'p01': ('proxy', '2001-01-02'), 'p10': ('proxy', '2010-01-04'), 'pY': ('proxy', H.PD[200])}
WL = ['real', 'p01', 'p10']
LET = 'ABCDEF'
assert HL.DEFAULTS['l1'] is False

# ------------------------------------------------------------------------------------------------ signals
SG0 = {k: v for k, v in HL.signals(False)[0].items() if not isinstance(k, tuple)}
Q0 = HL.Q0; PD = H.PD; T = len(PD)
MACRO = SG0['macro'][0].astype(np.int64)
VOTES = SG0['votes'][0].astype(int)
_FAST = {}
def fast_read(s, l):
    if (s, l) not in _FAST: _FAST[(s, l)] = MC._classify(Q0[None], s, l)[0].astype(np.int64)
    return _FAST[(s, l)]
assert (fast_read(20, 100) == SG0['fast'][0]).all()
VIXA = np.array([H.VIX.get(d, np.nan) for d in PD]); VIX3A = np.array([H.VIX3M.get(d, np.nan) for d in PD])
VOL30 = SG0['vol'][0]

def held_for(eff):
    held = np.zeros(T, np.int8); h = 0; gapn = 0
    for t in range(T):
        ina = eff[t] == 0
        gapn = 0 if ina else gapn + 1
        if (not ina) and gapn > S.A_SPELL_GAP_CARRY: h = 0
        hi15 = Q0[t] >= Q0[max(0, t - 14):t + 1].max()
        raw = VOTES[t]
        nh = raw if raw > h else (h - 1 if (h > raw and hi15) else h)
        if ina: h = nh
        held[t] = h if ina else 0
    return held
def runlen(c):
    out = np.zeros(len(c), int); n = 0
    for i, v in enumerate(c):
        n = n + 1 if v else 0; out[i] = n
    return out

def variant(spec):
    """Proxy-axis effective state (0..5 = A..F, 6 = flat lower row X), held votes, overlay-active mask, fast read used."""
    fast = fast_read(*spec.get('win', (20, 100)))
    lag = spec.get('lag', 0)
    if lag: fast = np.concatenate([np.full(lag, 5, fast.dtype), fast[:-lag]])
    cbc = ((MACRO == 1) | (MACRO == 2)) & (fast <= 1) if spec['bc'] else np.zeros(T, bool)
    cf = (MACRO == 5) & (fast <= spec.get('fmax', 2)) if spec['f'] else np.zeros(T, bool)
    N = spec.get('conf', 1)
    if N > 1: cbc = runlen(cbc) >= N; cf = runlen(cf) >= N
    st = spec.get('stress')
    if st:
        if st[0] == 'vol': off = np.nan_to_num(VOL30, nan=0.0) > st[1]
        else:
            with np.errstate(invalid='ignore'): off = VIXA > st[1] * VIX3A
            off = np.where(np.isnan(VIXA) | np.isnan(VIX3A), False, off)
        cbc = cbc & ~off; cf = cf & ~off
    eff = MACRO.copy(); eff[cbc] = 6 if spec.get('xrow') is not None else 0; eff[cf] = 2
    held = SG0['held'][0].astype(np.int8) if spec.get('hybrid') else held_for(eff)
    return dict(eff=eff, held=held, act=cbc | cf, fast=fast, bc=cbc, f=cf)

VFIRST = HL._vixy_first()
ARMS = {}; FAMS = {}
def arm(name, **spec):
    spec.setdefault('bc', True); spec.setdefault('f', True); ARMS[name] = spec
arm('OFF_audit', bc=False, f=False, hybrid=True)
arm('OFF', bc=False, f=False)
arm('FULL')
arm('BC_ONLY', f=False)
arm('F_ONLY', bc=False)
arm('LR50', xrow=(0.5, 0.5, 0, 0, 0)); arm('LR75', xrow=(0.75, 0.25, 0, 0, 0)); arm('LR100', xrow=(1.0, 0, 0, 0, 0))
arm('F_AB', fmax=1); arm('F_A', fmax=0)
arm('CONF2', conf=2); arm('CONF3', conf=3)
arm('W20_80', win=(20, 80)); arm('W30_100', win=(30, 100)); arm('W30_150', win=(30, 150))
arm('V25', stress=('vol', 0.25)); arm('V30', stress=('vol', 0.30)); arm('V40', stress=('vol', 0.40))
arm('VT95', stress=('vix', 0.95)); arm('VT100', stress=('vix', 1.00)); arm('VT105', stress=('vix', 1.05))
FAMS = {'lowrow': ['LR50', 'LR75', 'LR100'], 'fcut': ['F_A', 'F_AB'], 'conf': ['CONF2', 'CONF3'], 'win': ['W20_80', 'W30_100', 'W30_150'],
        'vol': ['V25', 'V30', 'V40'], 'vix': ['VT95', 'VT100', 'VT105']}
FAM_OF = {n: f for f, ns in FAMS.items() for n in ns}
CAND = [n for n in ARMS if n not in ('OFF_audit', 'OFF', 'FULL', 'BC_ONLY', 'F_ONLY')]
NEIGHBOUR_ONLY = ('F_A', 'W30_100', 'V25', 'V40', 'VT95', 'VT105')   # marked n in PLAN.md (still evaluated as candidates, but they are the neighbours)

# ------------------------------------------------------------------------------------------------ weights (copy of MC.target_weights + flat row X)
CFG = dict(H.CUR, a_base=tuple(S.A_BASE_FROM_SESSION[1]), gross_cap=None, vol_target=S.VOL_TARGET_PA)
def tw(sg, eff, xrow):
    held = sg['held']; P_, T_ = eff.shape
    w = np.zeros((P_, T_, 5))
    for s_, row in CFG['rows'].items(): w[eff == MC.LETTERS.index(s_)] = row
    if xrow is not None: w[eff == 6] = xrow
    a = eff == 0
    c0, t0 = CFG['a_base']; w[a] = 0.0
    w[..., 0] = np.where(a, c0 * (1 - S.EXTENSION_CORE_CUT_PER_VOTE * held), w[..., 0])
    w[..., 1] = np.where(a, np.where(held == 0, t0, 0.0), w[..., 1])
    z = MC._zone(sg, CFG)
    for zz, k in ((1, 'D1'), (2, 'D2'), (3, 'D3')):
        c, tq, q = S.D_LADDER_ROWS[k]; w[(eff == 3) & (z == zz)] = (c, tq, q, 0.0, 0.0)
    w[MC._gate(sg, CFG)] = (0.0, 0.0, 0.0, 0.0, 1.0)
    v = np.fmax(sg['vol'], np.where(np.isnan(sg['vol']), np.nan, sg['vol10']))
    vt = CFG['vol_target']
    mult = np.where(np.isnan(v) | (v <= 0), 1.0, np.minimum(1.0, vt / np.where(v > 0, v, 1)))
    w[..., :4] *= mult[..., None]
    w[..., 4] = 1.0 - w[..., :4].sum(-1)
    return w
GX = np.array(S.GROSS_EXPOSURE, float)

_ZONE = {}
def zone_for(track, sgbase):
    if track not in _ZONE:
        _ZONE[track] = MC._zone(sgbase, CFG).copy()
    return _ZONE[track]
_BASE = {}
def base_sg(track):
    if track not in _BASE:
        sg = dict(SG0)
        if track == 'real': sg = H.slice_sig(sg, H.OFF)
        _BASE[track] = sg; zone_for(track, dict(sg))
    return _BASE[track]

def prep(spec, track):
    real = track == 'real'; pn = H.pr if real else H.p; ds = pn['dates']
    v = variant(spec)
    sg = dict(SG0); sg['eff'] = v['eff'][None]; sg['eff_slow'] = v['eff'][None]; sg['held'] = v['held'][None]
    if real: sg = H.slice_sig(sg, H.OFF)
    sg[('_zone_b', CFG['d_buffer'], True)] = _ZONE[track] if track in _ZONE else None
    if sg[('_zone_b', CFG['d_buffer'], True)] is None:
        base_sg(track); sg[('_zone_b', CFG['d_buffer'], True)] = _ZONE[track]
    off = H.OFF if real else 0
    w5 = tw(sg, sg['eff'], spec.get('xrow'))[0]
    eff = sg['eff'][0]; gate = MC._gate(sg, CFG)[0]; z = MC._zone(sg, CFG)[0]
    assert ((eff == 3) == (MACRO[off:] == 3)).all()
    key = MC.regime_key(sg, CFG).astype(np.int64)[0]
    allowed = HL._latch(real, sg) & ~((eff == 3) & ~gate & (z == 2)) & np.array([d >= VFIRST for d in ds])
    key = key + allowed.astype(np.int64) * 100000
    deep = ((eff == 4) & (np.nan_to_num(sg['gaps'][200][0]) <= S.DEEP_E_GAP200)).astype(float) * S.DEEP_E_CASH_SHARE
    pan = H.panic_series(ds)
    for j, sh in enumerate((deep, pan)): key = key + (sh > 0).astype(np.int64) * (10 ** (6 + j))
    vr, _ = HL._vixy_rets(ds, 'full')
    L = np.stack([pn['core'], pn['tqqq'], pn['qld'], pn['xlu'], vr, pn['qqq'], pn['qqq'], pn['cash']], -1)
    return dict(ds=ds, real=real, off=off, eff=eff, macro=MACRO[off:], act=v['act'][off:], bc=v['bc'][off:], f=v['f'][off:], fast=v['fast'][off:],
                w5=w5, key=key, allowed=allowed, deep=deep, pan=pan, L=L, qqq=Q0[off:])
def finalize(P, scale=1.0):
    w5 = P['w5'].copy()
    gross = (w5[:, :4] * GX).sum(-1); cap = float(S.GROSS_CAP)
    f = np.where(gross > cap, cap / np.maximum(gross, 1e-12), 1.0) * scale
    w5[:, :4] *= f[:, None]; w5[:, 4] = 1.0 - w5[:, :4].sum(-1)
    cash = w5[:, 4].copy(); W = [w5[:, i] for i in range(4)]
    vx = np.where(P['allowed'], cash * S.VIXM_CASH_SHARE, 0.0); W.append(vx); used = vx.copy()
    for sh in (P['deep'], P['pan']):
        x = np.minimum(cash * sh, cash - used); used = used + x; W.append(x)
    W.append(cash - used); W = np.stack(W, -1)
    eqg = (W[:, [0, 1, 2, 3, 5, 6]] * np.array([1, 3, 2, 1, 1, 1])).sum(1)
    return W, eqg
def s0_of(P, win): return next(i for i, d in enumerate(P['ds']) if d >= WINS[win][1])

# ------------------------------------------------------------------------------------------------ metrics
def rollmin(r, n): return float(np.expm1(np.convolve(np.log1p(r), np.ones(n), 'valid')).min())
def mdd(r): nav = np.cumprod(1 + r); return float((nav / np.maximum.accumulate(np.concatenate([[1.0], nav]))[1:] - 1).min())
def sharpe(r): return float(r.mean() / r.std(ddof=1) * 252 ** .5)
def metrics(r):
    nav = np.cumprod(1 + r)
    return dict(c=float(nav[-1] ** (252 / len(r)) - 1), sh=sharpe(r), dd=mdd(r), w20=rollmin(r, 20))
def run_win(P, win, scale=1.0):
    s0 = s0_of(P, win); W, eqg = finalize(P, scale)
    r, tr = MC.run_strategy(W[None], P['key'][None], P['L'][None], s0)
    r = r[0]; n = len(r); yrs = n / 252
    act = P['act'][s0:-1]; entries = int((act[1:] & ~act[:-1]).sum() + (1 if act[0] else 0))
    return dict(r=r, ds=P['ds'][s0 + 1:], m=metrics(r), avgg=float(eqg[s0:-1].mean()), tpy=float(tr[0] / yrs),
                share=float(act.mean()), epy=entries / yrs, s0=s0)
_P = {}
def getP(name, track, spec=None):
    k = (name, track)
    if k not in _P: _P[k] = prep(spec or ARMS[name], track)
    return _P[k]

# ------------------------------------------------------------------------------------------------ run arms
R = {}
for name in ARMS:
    for w in WL + ['pY']:
        R[(name, w)] = run_win(getP(name, WINS[w][0]), w)
log('=' * 150); log('run.py: fast re-entry overlay (2026-11-17). PLAN.md pre-registered; research only, nothing adopted.'); log('=' * 150)
log(f'(arms computed {time.time()-T0:.0f}s)')
# ---- engine checks
for w, tr in (('real', 'real'), ('p01', 'proxy'), ('p10', 'proxy')):
    ref = HL.run_live(tr, d0=WINS[w][1])[0]
    err = np.abs(ref - R[('FULL', w)]['r']).max(); log(f'check: FULL {w} vs HL.run_live max |diff| = {err:.2e}'); assert err < 1e-12
for w in WL:
    m = R[('OFF_audit', w)]['m']; log(f"check: OFF_audit {w}: {m['c']*100:.1f}% / {m['sh']:.3f} / {m['dd']*100:.1f}%   (audit: real 47.8/2.065/-16.5; proxy 2001 30.1/1.417/-18.6)")
assert abs(R[('OFF_audit', 'real')]['m']['c'] - 0.478) < 0.0006 and abs(R[('OFF_audit', 'p01')]['m']['dd'] + 0.186) < 0.0006
# the weight copy equals MC.target_weights for FULL (pre-cap, before the sleeve)
_pf = getP('FULL', 'proxy'); _sg = dict(SG0); _chk = MC.target_weights(_sg, CFG)[0]
assert np.abs(_chk - _pf['w5']).max() < 1e-12; assert (held_for(SG0['eff'][0]) == SG0['held'][0]).all()
log('check: tw() == MC.target_weights for FULL (max diff 0); held_for(FULL eff) == engine held votes')

# ------------------------------------------------------------------------------------------------ matched de-levers
MS = {}
def matched(name, w):
    track = WINS[w][0]; PF = getP('FULL', track); s0 = s0_of(PF, w); target = R[(name, w)]['avgg']
    f = lambda x: float(finalize(PF, x)[1][s0:-1].mean())
    lo, hi = 0.2, 1.6
    if not (f(lo) <= target <= f(hi)): return None
    for _ in range(40):
        mid = (lo + hi) / 2
        if f(mid) < target: lo = mid
        else: hi = mid
    x = (lo + hi) / 2; res = run_win(PF, w, x); res['scale'] = x; return res
for name in ARMS:
    if name == 'FULL': continue
    for w in WL:
        MS[(name, w)] = matched(name, w)
log(f'(matched de-levers computed {time.time()-T0:.0f}s)')

# ------------------------------------------------------------------------------------------------ tables
def cell(x): m = x['m']; return f"{m['c']*100:5.1f}% {m['sh']:5.3f} {m['dd']*100:6.1f}% {m['w20']*100:6.1f}% {x['avgg']:4.2f}"
HDR = f"  {'arm':<10}" + ''.join(f"| {w+' CAGR   Sh     maxDD   w20    gross':<42}" for w in WL)
log('\nTABLE 1. Arms. cells: CAGR / Sharpe / max DD / worst-20-session / avg target gross.  "m(arm)" = FULL de-levered (flat scale of risky legs) to the arm\'s avg gross, scale s.')
for w in WL:
    x = R[('FULL', w)]; log(f"window {w}: returns {x['ds'][0]}..{x['ds'][-1]} ({len(x['ds'])} sessions)")
log(HDR)
for name in ARMS:
    log(f"  {name:<10}" + ''.join(f"| {cell(R[(name, w)]):<42}" for w in WL))
    if name != 'FULL':
        log(f"  {'  m('+name+')':<10}" + ''.join((f"| {cell(MS[(name, w)])+' s=%.3f' % MS[(name, w)]['scale']:<42}" if MS[(name, w)] else f"| {'n/a (outside 0.2..1.6)':<42}") for w in WL))
log('\nTABLE 2. Overlay activity (share of sessions with effective state != macro; overlay entries per year; trades per year) and dSharpe / dMaxDD (pp, + = shallower) vs FULL and vs matched de-lever')
log(f"  {'arm':<10}" + ''.join(f"| {w:<4} share  ent/y tr/y dSh_F  dDD_F  dSh_m  dDD_m   " for w in WL))
for name in ARMS:
    s = f"  {name:<10}"
    for w in WL:
        x = R[(name, w)]; F = R[('FULL', w)]; m = MS.get((name, w))
        s += f"| {w:<4} {x['share']*100:5.1f}% {x['epy']:5.2f} {x['tpy']:4.0f} {x['m']['sh']-F['m']['sh']:+6.3f} {(x['m']['dd']-F['m']['dd'])*100:+6.1f} "
        s += (f"{x['m']['sh']-m['m']['sh']:+6.3f} {(x['m']['dd']-m['m']['dd'])*100:+6.1f}   " if m else f"{'n/a':>14}   ")
    log(s)

# ---- markdown table 1
tb('### Table 1: CAGR % / Sharpe / max DD % / worst-20-session % / avg gross\n')
tb('| arm | ' + ' | '.join(WL) + ' |'); tb('|---|' + '---|' * len(WL))
def mc(x): m = x['m']; return f"{m['c']*100:.1f} / {m['sh']:.3f} / {m['dd']*100:.1f} / {m['w20']*100:.1f} / {x['avgg']:.2f}"
for name in ARMS:
    tb(f'| **{name}** | ' + ' | '.join(mc(R[(name, w)]) for w in WL) + ' |')
    if name != 'FULL': tb(f'| &nbsp;&nbsp;matched de-lever (s) | ' + ' | '.join((mc(MS[(name, w)]) + f" (s={MS[(name, w)]['scale']:.3f})") if MS[(name, w)] else 'n/a' for w in WL) + ' |')
tb('\n### Table 2: overlay activity, and arm minus FULL / arm minus matched de-lever (dSharpe, dMaxDD pp; + = shallower)\n')
tb('| arm | window | share of sessions | entries/yr | trades/yr | dSh vs FULL | dDD vs FULL | dSh vs matched | dDD vs matched |'); tb('|---|---|---|---|---|---|---|---|---|')
for name in ARMS:
    for w in WL:
        x = R[(name, w)]; F = R[('FULL', w)]; m = MS.get((name, w))
        tb(f"| {name} | {w} | {x['share']*100:.1f}% | {x['epy']:.2f} | {x['tpy']:.0f} | {x['m']['sh']-F['m']['sh']:+.3f} | {(x['m']['dd']-F['m']['dd'])*100:+.1f} | " +
           (f"{x['m']['sh']-m['m']['sh']:+.3f} | {(x['m']['dd']-m['m']['dd'])*100:+.1f} |" if m else 'n/a | n/a |'))

# ------------------------------------------------------------------------------------------------ Q1 attribution
def episodes(r, ds, d_start, k=5):
    nav = np.concatenate([[1.0], np.cumprod(1 + r)]); dts = [d_start] + list(ds); n = len(nav); eps = []; t = 0
    while t < n:
        j = t + 1; tr = t
        while j < n and nav[j] < nav[t]:
            if nav[j] < nav[tr]: tr = j
            j += 1
        if tr > t: eps.append((nav[tr] / nav[t] - 1, dts[t], dts[tr], dts[j] if j < n else 'not recovered', tr - t, t, tr))
        t = j
    return sorted(eps, key=lambda e: e[0])[:k]
log('\n' + '=' * 150); log('Q1. WHERE DOES THE DEEPER PROXY DRAWDOWN COME FROM?  (p01, 2001-01-03..2026-11-16)'); log('=' * 150)
x0 = R[('FULL', 'p01')]; d_start = PD[x0['s0']]
EP = {}
for name in ('FULL', 'OFF_audit', 'OFF', 'BC_ONLY', 'F_ONLY'):
    EP[name] = episodes(R[(name, 'p01')]['r'], x0['ds'], d_start)
    log(f'\nTop 5 drawdown episodes (peak -> trough -> recovery; depth; sessions peak..trough) {name}:')
    for e in EP[name]: log(f'   {e[0]*100:7.1f}%   {e[1]} -> {e[2]} -> {e[3]}   ({e[4]} sessions)')
tb('\n### Top 5 drawdown episodes, p01 (depth %, peak -> trough -> recovery)\n'); tb('| arm | #1 | #2 | #3 | #4 | #5 |'); tb('|---|---|---|---|---|---|')
for name in EP: tb(f'| {name} | ' + ' | '.join(f'{e[0]*100:.1f}%: {e[1]} -> {e[2]} -> {e[3]}' for e in EP[name]) + ' |')
# spells
def spells(P, s0):
    """Contiguous runs of ONE overlay type (BC->A, or F->C); a BC run that follows an F run directly is a separate spell."""
    ty = np.where(P['bc'], 1, np.where(P['f'], 2, 0))[s0:-1]; out = []; i = 0; n = len(ty)
    while i < n:
        if ty[i]:
            j = i
            while j + 1 < n and ty[j + 1] == ty[i]: j += 1
            out.append((i, j)); i = j + 1
        else: i += 1
    return out
PFp = getP('FULL', 'proxy'); s0 = x0['s0']
rF = R[('FULL', 'p01')]['r']
def attribution(offname, label):
    rO = R[(offname, 'p01')]['r']; ld = np.log1p(rF) - np.log1p(rO)
    sp = spells(PFp, s0); rows = []
    ins = np.zeros(len(ld), bool)
    for (i, j) in sp:
        ins[i:j + 1] = True
        t0_ = s0 + i; t1_ = s0 + j
        typ = 'BC->A' if PFp['macro'][t0_] in (1, 2) else 'F->C'
        # QQQ move over the days whose returns the spell's weights earn: close of session t0 to close of session t1+1
        q = PFp['qqq'][min(t1_ + 1, len(PFp['qqq']) - 1)] / PFp['qqq'][t0_] - 1
        rows.append(dict(i=i, j=j, a=PD[t0_], b=PD[t1_], typ=typ, mac=LET[PFp['macro'][t0_]], fast=LET[PFp['fast'][t0_]], n=j - i + 1, qqq=q,
                         rF=float(np.prod(1 + rF[i:j + 1]) - 1), rO=float(np.prod(1 + rO[i:j + 1]) - 1), ld=float(ld[i:j + 1].sum())))
    tot = float(ld.sum()); resid = float(ld[~ins].sum())
    log(f'\n--- Spell attribution, FULL minus {offname} ({label}) on p01: total log-return difference {tot*100:+.1f} pp (= FULL NAV {np.exp(tot):.3f}x {offname} NAV at the end); '
        f'{len(rows)} overlay spells; summed over spells {(tot-resid)*100:+.1f} pp; days outside spells (carry/trim/drift residual) {resid*100:+.2f} pp')
    for typ in ('BC->A', 'F->C'):
        rr = [r_ for r_ in rows if r_['typ'] == typ]
        log(f"    {typ}: {len(rr)} spells, {sum(r_['n'] for r_ in rr)} sessions, sum log diff {sum(r_['ld'] for r_ in rr)*100:+.1f} pp, positive spells {sum(1 for r_ in rr if r_['ld']>0)}, negative {sum(1 for r_ in rr if r_['ld']<0)}")
    srt = sorted(rows, key=lambda r_: r_['ld'])
    hdr = f"    {'spell (sessions of eff!=macro)':<26}{'type':<6}{'macro/fast':<11}{'n':>4} {'QQQ move':>9} {'FULL book':>10} {offname+' book':>10} {'FULL-'+offname+' (pp log)':>20}"
    def pr(r_): log(f"    {r_['a']}..{r_['b']:<12}{r_['typ']:<6}{r_['mac']+'/'+r_['fast']:<11}{r_['n']:>4} {r_['qqq']*100:+8.1f}% {r_['rF']*100:+9.1f}% {r_['rO']*100:+9.1f}% {r_['ld']*100:+19.2f}")
    log('  10 worst spells (most negative log difference):'); log(hdr); [pr(r_) for r_ in srt[:10]]
    log('  10 best spells:'); log(hdr); [pr(r_) for r_ in srt[::-1][:10]]
    s5 = sum(r_['ld'] for r_ in srt[:5]); log(f'  worst 5 spells sum {s5*100:+.1f} pp; share of all negative spells\' sum {s5/sum(r_["ld"] for r_ in srt if r_["ld"]<0)*100:.0f}%')
    return rows, ld
ATT = {}
for off_ in ('OFF_audit', 'OFF'): ATT[off_] = attribution(off_, 'the audit arm' if off_ == 'OFF_audit' else 'clean off')
def window_detail(ep, offname='OFF'):
    a, b = ep[5], ep[6]    # nav indices; days a..b-1 (0-based return index) are the drawdown days
    rows, ld = ATT[offname]; rO = R[(offname, 'p01')]['r']
    navF = np.concatenate([[1.0], np.cumprod(1 + rF)]); navO = np.concatenate([[1.0], np.cumprod(1 + rO)])
    pk = navF[b] / navF[a] - 1; po = navO[b] / navO[a] - 1
    log(f'\n  Episode {ep[1]} -> {ep[2]}: FULL {pk*100:+.1f}%, {offname} {po*100:+.1f}%, QQQ {PFp["qqq"][s0+b]/PFp["qqq"][s0+a]*100-100:+.1f}%; '
        f'NAV FULL/{offname} at the peak date {navF[a]/navO[a]:.3f}, at the trough date {navF[b]/navO[b]:.3f} (log diff over the window {ld[a:b].sum()*100:+.1f} pp, before the peak {ld[:a].sum()*100:+.1f} pp)')
    inw = [r_ for r_ in rows if r_['j'] >= a and r_['i'] < b]
    for r_ in inw:
        lo_, hi_ = max(r_['i'], a), min(r_['j'], b - 1)
        log(f"      spell {r_['a']}..{r_['b']} {r_['typ']} macro/fast {r_['mac']}/{r_['fast']} n={r_['n']} QQQ {r_['qqq']*100:+.1f}%: log diff inside window {ld[lo_:hi_+1].sum()*100:+.2f} pp (whole spell {r_['ld']*100:+.2f})")
    if not inw: log('      no overlay spell inside this window')
    return ld[a:b].sum()
log('\nDrawdown windows: the top 5 episodes of FULL and of OFF (clean), FULL vs OFF over the same peak-to-trough days')
seen = set()
for ep in EP['FULL'] + EP['OFF']:
    if (ep[1], ep[2]) in seen: continue
    seen.add((ep[1], ep[2])); window_detail(ep, 'OFF')
log('\nOFF_audit differs from OFF only through trim held votes (see the table: the two arms have the same max DD, 3.6pp shallower than FULL on p01); the windows above apply to both.')
# FULL vs OFF NAV gap by year (is the DD difference one episode?)
log('\nCumulative log NAV difference FULL - OFF (clean) at calendar-year ends, p01 (pp): shows when the overlay gained or lost')
dsr = np.array(R[('FULL', 'p01')]['ds']); ldc = ATT['OFF'][1]
yrs = sorted(set(d[:4] for d in dsr)); cum = 0; line_ = ''
for y in yrs:
    s_ = ldc[[d.startswith(y) for d in dsr]].sum(); cum += s_; line_ += f' {y}:{s_*100:+.1f}'
log(line_)
# drawdown depth by sub-period for each arm (max DD within calendar periods)
def sub_dd(r, ds, a, b):
    m = np.array([a <= d <= b for d in ds]); return mdd(r[m]) if m.sum() > 5 else float('nan')
PER = [('2001-2003', '2001-01-01', '2003-12-31'), ('2007-2009', '2007-01-01', '2009-12-31'), ('2011', '2011-01-01', '2011-12-31'), ('2018', '2018-01-01', '2018-12-31'), ('2020', '2020-01-01', '2020-12-31'), ('2022', '2022-01-01', '2022-12-31'), ('2025-26', '2025-01-01', '2026-12-31')]
log('\nMax DD computed inside sub-periods (p01 path; each starts at NAV 1), by arm:')
log(f"  {'arm':<10}" + ''.join(f'{p[0]:>11}' for p in PER))
for name in ('FULL', 'OFF_audit', 'OFF', 'BC_ONLY', 'F_ONLY'):
    log(f"  {name:<10}" + ''.join(f"{sub_dd(R[(name,'p01')]['r'], dsr, p[1], p[2])*100:10.1f}%" for p in PER))

# ------------------------------------------------------------------------------------------------ year table
log('\n' + '=' * 150); log('YEAR TABLE: calendar-year return minus FULL (pp). 2000 from the pY run (starts %s, partial year, macro read just formed). p01 for 2001-2026 (2026 to 11-16).' % H.PD[200]); log('=' * 150)
YRS = ['2000', '2001', '2002', '2003', '2008', '2009', '2018', '2020', '2022', '2025', '2026']
def yret(r, ds, y):
    m = np.array([d.startswith(y) for d in ds]); return float(np.prod(1 + r[m]) - 1) if m.any() else float('nan')
def ytab(win, years):
    out = {}
    for name in ARMS:
        r = R[(name, win)]['r']; ds = R[(name, win)]['ds']; out[name] = [yret(r, ds, y) for y in years]
    return out
YP = {y: ytab('pY' if y == '2000' else 'p01', [y])['FULL'][0] for y in YRS}
YT = {}
for name in ARMS:
    YT[name] = [yret(R[(name, 'pY' if y == '2000' else 'p01')]['r'], R[(name, 'pY' if y == '2000' else 'p01')]['ds'], y) for y in YRS]
log(f"  {'arm':<10}" + ''.join(f'{y:>8}' for y in YRS)); log(f"  {'FULL(abs)':<10}" + ''.join(f'{v*100:7.1f}%' for v in YT['FULL']))
for name in ARMS:
    if name != 'FULL': log(f"  {name:<10}" + ''.join(f'{(a-b)*100:+8.1f}' for a, b in zip(YT[name], YT['FULL'])))
YRR = ['2018', '2020', '2022', '2025', '2026']
log('\n  Same on the REAL window (2015-11-03..): arm minus FULL (pp), years ' + ' '.join(YRR))
YTR = {name: [yret(R[(name, 'real')]['r'], R[(name, 'real')]['ds'], y) for y in YRR] for name in ARMS}
log(f"  {'FULL(abs)':<10}" + ''.join(f'{v*100:7.1f}%' for v in YTR['FULL']))
for name in ARMS:
    if name != 'FULL': log(f"  {name:<10}" + ''.join(f'{(a-b)*100:+8.1f}' for a, b in zip(YTR[name], YTR['FULL'])))
tb('\n### Year table (proxy): arm minus FULL, pp; 2000 is partial (from the end of the 200-day warm-up). FULL row is absolute %\n')
tb('| arm | ' + ' | '.join(YRS) + ' |'); tb('|---|' + '---|' * len(YRS))
tb('| FULL (abs %) | ' + ' | '.join(f'{v*100:.1f}' for v in YT['FULL']) + ' |')
for name in ARMS:
    if name != 'FULL': tb(f'| {name} | ' + ' | '.join(f'{(a-b)*100:+.1f}' for a, b in zip(YT[name], YT['FULL'])) + ' |')
tb('\n### Year table (real): arm minus FULL, pp\n'); tb('| arm | ' + ' | '.join(YRR) + ' |'); tb('|---|' + '---|' * len(YRR))
tb('| FULL (abs %) | ' + ' | '.join(f'{v*100:.1f}' for v in YTR['FULL']) + ' |')
for name in ARMS:
    if name != 'FULL': tb(f'| {name} | ' + ' | '.join(f'{(a-b)*100:+.1f}' for a, b in zip(YTR[name], YTR['FULL'])) + ' |')

# ------------------------------------------------------------------------------------------------ robustness
log('\n' + '=' * 150); log('ROBUSTNESS (arm minus FULL): halves of p01 (by sessions), ex-2020, one session of lag on the fast read (arm and FULL both lagged)'); log('=' * 150)
LAGR = {}
for name, spec in ARMS.items():
    if spec.get('hybrid') or (not spec['bc'] and not spec['f']): continue
    sp2 = dict(spec, lag=1)
    for w in WL: LAGR[(name, w)] = run_win(getP(name + '_lag', WINS[w][0], sp2), w)
log(f'(lag runs computed {time.time()-T0:.0f}s)')
def sub(r, ds, kind):
    n = len(r); h = n // 2
    if kind == 'h1': return r[:h]
    if kind == 'h2': return r[h:]
    if kind == 'x20': return r[np.array([not d.startswith('2020') for d in ds])]
RB = {}
for name in ARMS:
    if name == 'FULL': continue
    x = R[(name, 'p01')]; F = R[('FULL', 'p01')]; row = {}
    for k in ('h1', 'h2', 'x20'):
        a, b = sub(x['r'], x['ds'], k), sub(F['r'], F['ds'], k); row[k] = (sharpe(a) - sharpe(b), mdd(a) - mdd(b))
    if (name, 'p01') in LAGR:
        row['lag'] = {w: (LAGR[(name, w)]['m']['sh'] - LAGR[('FULL', w)]['m']['sh'], LAGR[(name, w)]['m']['dd'] - LAGR[('FULL', w)]['m']['dd']) for w in WL}
    RB[name] = row
log(f"  {'arm':<10}| {'h1 dSh':>7} {'dDD':>6} | {'h2 dSh':>7} {'dDD':>6} | {'ex20 dSh':>8} {'dDD':>6} | lagged fast: dSh (real p01 p10) / dDD pp (real p01 p10)")
tb('\n### Robustness: arm minus FULL on p01 halves and ex-2020 (dSharpe / dMaxDD pp), and with the fast read lagged one session (dSharpe real/p01/p10 ; dMaxDD pp real/p01/p10)\n')
tb('| arm | h1 | h2 | ex-2020 | lag1 dSh (real / p01 / p10) | lag1 dDD pp (real / p01 / p10) |'); tb('|---|---|---|---|---|---|')
for name, row in RB.items():
    lg = row.get('lag'); ls = ' '.join(f'{lg[w][0]:+6.3f}' for w in WL) + ' / ' + ' '.join(f'{lg[w][1]*100:+5.1f}' for w in WL) if lg else 'n/a'
    log(f"  {name:<10}| {row['h1'][0]:+7.3f} {row['h1'][1]*100:+6.1f} | {row['h2'][0]:+7.3f} {row['h2'][1]*100:+6.1f} | {row['x20'][0]:+8.3f} {row['x20'][1]*100:+6.1f} | {ls}")
    tb(f"| {name} | {row['h1'][0]:+.3f} / {row['h1'][1]*100:+.1f} | {row['h2'][0]:+.3f} / {row['h2'][1]*100:+.1f} | {row['x20'][0]:+.3f} / {row['x20'][1]*100:+.1f} | " +
       (' / '.join(f'{lg[w][0]:+.3f}' for w in WL) + ' | ' + ' / '.join(f'{lg[w][1]*100:+.1f}' for w in WL) if lg else 'n/a | n/a') + ' |')
log('  lagged FULL absolute (CAGR/Sharpe/maxDD):  ' + '; '.join(f"{w}: {LAGR[('FULL', w)]['m']['c']*100:.1f}% / {LAGR[('FULL', w)]['m']['sh']:.3f} / {LAGR[('FULL', w)]['m']['dd']*100:.1f}%" for w in WL))

# ------------------------------------------------------------------------------------------------ bootstrap
def boot_idx(N, seed=20261117):
    rng = np.random.default_rng(seed); nb = -(-N // BLOCK); st = rng.integers(N, size=(NBOOT, nb))
    return ((st[:, :, None] + np.arange(BLOCK)) % N).reshape(NBOOT, -1)[:, :N]
BI = {}; BV = {}
def bvec(key, r):
    if key in BV: return BV[key]
    N = len(r)
    if N not in BI: BI[N] = boot_idx(N)
    idx = BI[N]; sh = np.empty(NBOOT); dd = np.empty(NBOOT)
    for i in range(0, NBOOT, 100):
        a = r[idx[i:i + 100]]; sh[i:i + 100] = a.mean(1) / a.std(1, ddof=1) * 252 ** .5
        nav = np.cumprod(1 + a, 1); dd[i:i + 100] = (nav / np.maximum(1.0, np.maximum.accumulate(nav, 1))).min(1) - 1
    BV[key] = (sh, dd); return BV[key]
log('\n' + '=' * 150)
log(f'BOOTSTRAP: {NBOOT} paths, {BLOCK}-session circular blocks, paired. dSh = Sharpe(arm) - Sharpe(ref); dDD = maxDD(arm) - maxDD(ref) (pp, + = arm shallower). median [5%, 95%] and P(<=0).')
log('=' * 150)
BS = {}
def pair(a, b):
    sa, da = a; sb, db = b; ds_ = sa - sb; dd_ = da - db
    return (float(np.median(ds_)), float(np.percentile(ds_, 5)), float(np.percentile(ds_, 95)), float((ds_ <= 0).mean()),
            float(np.median(dd_) * 100), float(np.percentile(dd_, 5) * 100), float(np.percentile(dd_, 95) * 100), float((dd_ <= 0).mean()))
for w in WL:
    vF = bvec(('FULL', w), R[('FULL', w)]['r'])
    for name in ARMS:
        if name == 'FULL': continue
        va = bvec((name, w), R[(name, w)]['r']); BS[(name, w, 'F')] = pair(va, vF)
        if MS[(name, w)] is not None: BS[(name, w, 'M')] = pair(va, bvec((name, w, 'm'), MS[(name, w)]['r']))
    log(f'  bootstrap window {w} done {time.time()-T0:.0f}s')
for w in WL:
    log(f'\n window {w}:  vs FULL                                                    | vs matched de-lever')
    log(f"  {'arm':<10}{'dSh med [5,95]':>24}{'P<=0':>6} {'dDD med [5,95] pp':>24}{'P<=0':>6} | {'dSh med [5,95]':>24}{'P<=0':>6} {'dDD med [5,95] pp':>24}{'P<=0':>6}")
    for name in ARMS:
        if name == 'FULL': continue
        s = f"  {name:<10}"
        for t in ('F', 'M'):
            b = BS.get((name, w, t))
            s += (f"{b[0]:+7.3f} [{b[1]:+.3f},{b[2]:+.3f}]{b[3]:6.2f} {b[4]:+7.2f} [{b[5]:+.1f},{b[6]:+.1f}]{b[7]:6.2f} | " if b else f"{'n/a':>60} | ")
        log(s)
tb('\n### Bootstrap (2,000 paths, 20-session blocks): median [5%, 95%] of dSharpe and dMaxDD (pp; + = arm shallower) and P(<=0); vs FULL, vs matched de-lever\n')
for w in WL:
    tb(f'**{w}**\n'); tb('| arm | dSh vs FULL | P(<=0) | dDD vs FULL | P(<=0) | dSh vs matched | P(<=0) | dDD vs matched | P(<=0) |'); tb('|---|---|---|---|---|---|---|---|---|')
    for name in ARMS:
        if name == 'FULL': continue
        s = f'| {name} |'
        for t in ('F', 'M'):
            b = BS.get((name, w, t)); s += (f" {b[0]:+.3f} [{b[1]:+.3f}, {b[2]:+.3f}] | {b[3]:.2f} | {b[4]:+.2f} [{b[5]:+.1f}, {b[6]:+.1f}] | {b[7]:.2f} |" if b else ' n/a | n/a | n/a | n/a |')
        tb(s)
    tb('')

# ------------------------------------------------------------------------------------------------ reading rule
log('\n' + '=' * 150); log('READING RULE (PLAN.md): alternatives vs FULL'); log('=' * 150)
def mget(n, w): return R[(n, w)]['m']
def chk(n):
    F = {w: mget('FULL', w) for w in WL}; a = {w: mget(n, w) for w in WL}
    c = {}
    c['1 p01 DD >= 2pp shallower'] = (a['p01']['dd'] - F['p01']['dd']) * 100 >= 2.0
    c['2 Sharpe >= FULL-0.02 on all'] = all(a[w]['sh'] - F[w]['sh'] >= -0.02 for w in WL)
    c['3 beats matched Sh real & p01'] = all(MS[(n, w)] is not None and a[w]['sh'] > MS[(n, w)]['m']['sh'] for w in ('real', 'p01'))
    c['4 halves & ex2020'] = all(RB[n][k][0] >= -0.02 and RB[n][k][1] >= 0 for k in ('h1', 'h2', 'x20'))
    nb = []
    fam = FAMS[FAM_OF[n]] if n in FAM_OF else []
    i = fam.index(n) if n in fam else None
    if i is not None: nb = [fam[j] for j in (i - 1, i + 1) if 0 <= j < len(fam)]
    c['5 neighbour same way'] = any((mget(q, 'p01')['dd'] - F['p01']['dd']) * 100 >= 1.0 and mget(q, 'p01')['sh'] - F['p01']['sh'] >= -0.02 for q in nb)
    b = BS[(n, 'p01', 'F')]; c['6 boot P(dDD<=0) < 0.20'] = b[7] < 0.20
    return c, nb
PASS = []
log(f"  {'arm':<9}" + ''.join(f'{k.split()[0]:>3}' for k in ['1 a', '2 a', '3 a', '4 a', '5 a', '6 a']) + '   detail')
for n in CAND:
    c, nb = chk(n); ok = all(c.values()); PASS.append(n) if ok else None
    log(f"  {n:<9}" + ''.join(f"{'Y' if v else '.':>3}" for v in c.values()) + f"   p01 dDD {(mget(n,'p01')['dd']-mget('FULL','p01')['dd'])*100:+5.1f}pp, dSh real/p01/p10 " +
        ' '.join(f"{mget(n,w)['sh']-mget('FULL',w)['sh']:+.3f}" for w in WL) + f", boot P(dDD<=0) {BS[(n,'p01','F')][7]:.2f}, neighbours {nb}" + ('   <== ALL SIX' if ok else ''))
log(f'  arms satisfying all six: {PASS or "none"}')
tb('\n### Reading rule: 1 p01 DD >= 2 pp shallower, 2 Sharpe within -0.02 of FULL on all windows, 3 beats matched de-lever on real & p01, 4 halves & ex-2020, 5 neighbour same way, 6 bootstrap P(dDD<=0) < 0.20\n')
tb('| arm | 1 | 2 | 3 | 4 | 5 | 6 | all |'); tb('|---|---|---|---|---|---|---|---|')
for n in CAND:
    c, nb = chk(n); tb(f'| {n} | ' + ' | '.join('Y' if v else '-' for v in c.values()) + f" | {'YES' if all(c.values()) else 'no'} |")
log('\nTURN THE OVERLAY OFF? Sharpe of OFF vs FULL de-levered to OFF\'s average gross (flat scale s):')
offwin = {}
for off_ in ('OFF', 'OFF_audit'):
    s = f'  {off_}: '; k = 0
    for w in WL:
        m = MS[(off_, w)]; a = mget(off_, w)
        if m is None: s += f'{w}: n/a; '; continue
        win_ = a['sh'] > m['m']['sh']; k += win_
        s += f"{w}: OFF {a['sh']:.3f} vs m(OFF) {m['m']['sh']:.3f} (s={m['scale']:.3f}, d {a['sh']-m['m']['sh']:+.3f}, FULL {mget('FULL',w)['sh']:.3f}){' WIN' if win_ else ''}; "
    offwin[off_] = k; log(s + f'-> OFF wins on {k} of 3')
log(f"  rule (OFF clean wins on >= 2 of 3 windows): {'MET' if offwin['OFF'] >= 2 else 'NOT MET'};  OFF_audit: {'MET' if offwin['OFF_audit'] >= 2 else 'NOT MET'}")
# diagnostic: halves of the overlay (does each half beat its own matched de-lever?)
log('\nDIAGNOSTIC. Which half earns / takes risk: arm vs FULL de-levered to its gross (dSharpe vs matched), and vs OFF (clean) with its gross')
for n in ('BC_ONLY', 'F_ONLY', 'FULL'):
    s = f'  {n:<8}'
    for w in WL:
        a = mget(n, w); o = mget('OFF', w)
        s += f"| {w}: vs OFF dCAGR {(a['c']-o['c'])*100:+.1f}pp dSh {a['sh']-o['sh']:+.3f} dDD {(a['dd']-o['dd'])*100:+.1f}pp dGross {R[(n,w)]['avgg']-R[('OFF',w)]['avgg']:+.3f} "
    log(s)
# FULL vs OFF matched: overlay's return vs risk
log('\nOVERLAY vs plain extra risk: FULL vs OFF de-levered?  (OFF levered up by flat scale to FULL\'s gross is not run; instead FULL vs m(OFF) above shows it from the other side.)')
log(f'\nDONE {time.time()-T0:.0f}s')
