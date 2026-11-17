"""VIXY sleeve sweep: weight, trigger knobs, NAV cap. Research only. See PLAN.md (pre-registered before any cell was run)."""
import csv, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); PT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PT, 'review_2026_11'))
import harness as H
from harness import MC, S
OLD = os.path.join(PT, 'research_notes', 'vixy_calm_2026_11')
LOG = open(os.path.join(HERE, 'run.log'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); LOG.write(s + '\n'); LOG.flush()
T0 = time.time()
CAPCFG = dict(H.CUR, gross_cap=2.0); EPS = S.ZERO_LEG_EPS; BAND = S.REBALANCE_DRIFT_BAND; NBOOT = 2000

# ------------------------------------------------------------------ tracks / windows
TRK = {'real': dict(ds=H.RD, sg=H.sr, pn=H.pr), 'proxy': dict(ds=H.PD, sg=H.sig, pn=H.p)}
WSPEC = {'real': ('real', '2015-11-02', '2099'), 'oos': ('proxy', '2011-01-04', '2015-09-02'),
         'late': ('proxy', '2015-09-02', '2099'), 'joined': ('proxy', '2011-01-04', '2099')}
WN = ['real', 'late', 'oos', 'joined']
WIN = {}
for w, (tn, a, b) in WSPEC.items():
    ds = TRK[tn]['ds']; WIN[w] = (tn, next(i for i, d in enumerate(ds) if d >= a), max(i for i, d in enumerate(ds) if d <= b))
RDS = {w: TRK[WIN[w][0]]['ds'][WIN[w][1] + 1:WIN[w][2] + 1] for w in WN}
YRS = {w: np.array([d[:4] for d in RDS[w]]) for w in WN}

def load_close(fn): return {r['d']: float(r['close_split_adj']) for r in csv.DictReader(open(os.path.join(OLD, fn)))}
vy, vm = load_close('vixy_yahoo_full.csv'), load_close('vixm_yahoo_full.csv')
def rr(px, ds):
    x = MC._rets(px, ds); x[0] = 0.0; return x
INSTR = {tn: {'Y': rr(vy, t['ds']), 'M': rr(vm, t['ds'])} for tn, t in TRK.items()}

# ------------------------------------------------------------------ latch (parametrised copy of state.vixm_series)
LIVE = dict(inst='Y', w=0.35, ev=18.0, er=1.0, xr=1.0, fade=0.25, floor=0.20, d2=True, cap=None)
def latch(tn, ev, er, xr, fade, floor):
    ds = TRK[tn]['ds']; rvv = TRK[tn]['sg']['vol'][0]
    on = killed = False; hi = None; n = len(ds)
    allowed = np.zeros(n, bool); code = np.zeros(n, np.int8)   # code: 1 allowed, 2 latch off by curve, 3 fade-killed, 4 stress floor, 5 not entered, 0 missing
    for i, d in enumerate(ds):
        v, v3 = H.VIX.get(d), H.VIX3M.get(d)
        if v is None or v3 is None or v3 <= 0 or np.isnan(v) or np.isnan(v3): continue
        ratio = v / v3; cd = 5
        if (not on and (ev is None or v < ev) and (er is None or ratio <= er) and (xr is None or ratio <= xr)):
            on, killed, hi = True, False, None
        elif on and xr is not None and ratio > xr:
            on = False; cd = 2
        rv = rvv[i]; rv = None if np.isnan(rv) else float(rv)
        stress = True if floor is None else (rv is not None and rv >= floor)
        if not stress: killed, hi = False, None
        a = on and not killed and stress
        if a:
            hi = v if hi is None else max(hi, v)
            if fade is not None and v <= hi * (1 - fade): killed, a = True, False
        allowed[i] = a
        code[i] = 1 if a else (3 if (on and killed) else (4 if (on and not stress) else cd))
    return allowed, code
_lc = {}
def get_latch(tn, c):
    k = (tn, c['ev'], c['er'], c['xr'], c['fade'], c['floor'])
    if k not in _lc: _lc[k] = latch(tn, *k[1:])
    return _lc[k]

# check: live latch == harness latch on both tracks
_vd = {d: (None if np.isnan(v) else float(v)) for d, v in zip(H.PD, H.sig['vol'][0])}
_vxp = S.vixm_series(H.PD, H.VIX, H.VIX3M, _vd)
VXA_CHECK = {'real': H.VXA, 'proxy': np.array([bool(_vxp.get(d, {}).get('allowed')) for d in H.PD])}
for tn in TRK:
    a, _ = get_latch(tn, LIVE)
    assert np.array_equal(a, VXA_CHECK[tn]), f'parametrised latch != harness latch on {tn}'

# ------------------------------------------------------------------ weights
BASE = {}
for tn, t in TRK.items():
    sg = t['sg']; w5 = MC.target_weights(sg, CAPCFG); key = MC.regime_key(sg, CAPCFG).astype(np.int64)[0]
    eff = MC._eff(sg, CAPCFG)[0]; gate = MC._gate(sg, CAPCFG)[0]; z = MC._zone(sg, CAPCFG)[0]
    g = np.nan_to_num(sg['gaps'][200][0])
    deep = ((eff == 4) & (g <= S.DEEP_E_GAP200)).astype(float) * S.DEEP_E_CASH_SHARE
    BASE[tn] = dict(w5=w5, key=key, eff=eff, gate=gate, z=z, deep=deep, pan=H.panic_series(t['ds']), d2=((eff == 3) & ~gate & (z == 2)))

def build(tn, c, lag=0):
    t = TRK[tn]; b = BASE[tn]; pn = t['pn']; w5 = b['w5']; cash = w5[0, :, 4].copy()
    al, _ = get_latch(tn, c); al = al.copy()
    if lag: al = np.concatenate([np.zeros(lag, bool), al[:-lag]])
    if c['d2']: al = al & ~b['d2']
    v = np.where(al, cash * c['w'], 0.0)
    if c['cap'] is not None: v = np.minimum(v, c['cap'])
    key = b['key'].copy()
    if c['w'] > 0: key = key + al.astype(np.int64) * 100000
    legs = [pn['core'], pn['tqqq'], pn['qld'], pn['xlu'], INSTR[tn][c['inst']]]; W = [w5[0, :, i] for i in range(4)] + [v]; used = v.copy()
    for j, x in enumerate((b['deep'], b['pan'])):
        y = np.minimum(cash * x, cash - used); used = used + y
        legs.append(pn['qqq']); W.append(y); key = key + (x > 0).astype(np.int64) * (10 ** (6 + j))
    legs.append(pn['cash']); W.append(cash - used)
    return np.stack(W, -1), np.stack(legs, -1), key

def engine(W, key, L, s0, e, c4):
    n = e - s0; out = np.zeros(n); hw = np.zeros(n); ctb = np.zeros(n); h = W[s0].copy(); cost = MC.COST; tr = 0
    cv = np.full(W.shape[1], MC.COST); cv[4] = c4
    for t in range(s0, e):
        if t > s0:
            tgt = W[t]; diff = np.abs(tgt - h)
            if key[t] != key[t - 1] or diff.sum() > BAND or ((tgt == 0) & (h > EPS)).any():
                cost = float((diff * cv).sum()); h = tgt.copy(); tr += 1
            else: cost = 0.0
        r = L[t + 1]; g = float((h * r).sum()); out[t - s0] = (1 + g) * (1 - cost) - 1
        hw[t - s0] = h[4]; ctb[t - s0] = h[4] * r[4]; h = h * (1 + r) / (1 + g)
    return dict(r=out, hw=hw, ctb=ctb, tpy=tr / (n / 252))

_bt = {}
def built(tn, c, lag):
    k = (tn, tuple(sorted(c.items(), key=lambda x: x[0])), lag)
    if k not in _bt: _bt[k] = build(tn, c, lag)
    return _bt[k]
RES = {}
def run(c, w, lag=0, c4=MC.COST):
    k = (tuple(sorted(c.items(), key=lambda x: x[0])), w, lag, c4)
    if k in RES: return RES[k]
    tn, s0, e = WIN[w]; W, L, key = built(tn, c, lag); RES[k] = engine(W, key, L, s0, e, c4); return RES[k]

# ------------------------------------------------------------------ metrics
def stats(r):
    nav = np.cumprod(1 + r); dd = (nav / np.maximum(np.maximum.accumulate(nav), 1) - 1).min(); v = r.std(ddof=1) * 252 ** .5
    return dict(c=nav[-1] ** (252 / len(r)) - 1, sh=r.mean() * 252 / v, m=dd, v=v, w1=r.min(),
                w5=float(np.expm1(np.convolve(np.log1p(r), np.ones(5), 'valid')).min()))
def sh(r): return r.mean() * 252 / (r.std(ddof=1) * 252 ** .5)
def spells(hw):
    on = hw > 1e-9; out = []; i = 0; n = len(on)
    while i < n:
        if on[i]:
            j = i
            while j + 1 < n and on[j + 1]: j += 1
            out.append((i, j)); i = j + 1
        else: i += 1
    return out
_mc = {}
def met(c, w, lag=0, c4=MC.COST):
    k = (tuple(sorted(c.items(), key=lambda x: x[0])), w, lag, c4)
    if k in _mc: return _mc[k]
    R_ = run(c, w, lag, c4); st = stats(R_['r']); hw = R_['hw']; on = hw > 1e-9; ctb = R_['ctb']; n = len(R_['r']); yrs = n / 252
    o = np.argsort(ctb)[:5]
    st.update(on=on.mean() * 100, sp=len(spells(hw)), avgw=(hw[on].mean() * 100 if on.any() else 0.0), maxw=hw.max() * 100,
              contrib=ctb.sum() * 100 / yrs, wsd=ctb.min() * 100, w5d=[(RDS[w][i], ctb[i] * 100) for i in o], tpy=R_['tpy'])
    _mc[k] = st; return st

# ------------------------------------------------------------------ labels / cells
def lab(c):
    s = f"{'VIXY' if c['inst']=='Y' else 'VIXM'} w{c['w']*100:g}"
    if c['ev'] != LIVE['ev']: s += f" ev{'none' if c['ev'] is None else '%g' % c['ev']}"
    if c['er'] != LIVE['er']: s += f" er{'none' if c['er'] is None else '%g' % c['er']}"
    if c['xr'] != LIVE['xr']: s += f" xr{'none' if c['xr'] is None else '%g' % c['xr']}"
    if c['fade'] != LIVE['fade']: s += f" fade{'off' if c['fade'] is None else '%g' % (c['fade']*100)}"
    if c['floor'] != LIVE['floor']: s += f" floor{'none' if c['floor'] is None else '%g' % (c['floor']*100)}"
    if not c['d2']: s += ' D2on'
    if c['cap'] is not None: s += f" cap{c['cap']*100:g}"
    return s
def mk(**kw): return dict(LIVE, **kw)
ALL = {}     # label -> (cell, part)
def add(c, part):
    ALL.setdefault(lab(c), (c, part)); return lab(c)
P1 = [add(mk(w=x / 100), 'P1') for x in (0, 10, 20, 25, 30, 35, 40, 50, 60, 75, 100)]
P1M = [add(mk(inst='M', w=x / 100), 'P1M') for x in (50, 75, 100)]
KNOBS = {
    'ev': [15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 22.0, None],
    'er': [0.90, 0.95, 1.00, None],
    'xr': [0.95, 1.00, 1.05, 1.10],
    'fade': [0.15, 0.20, 0.25, 0.30, 0.40, None],   # ordered tight -> loose (off last)
    'floor': [None, 0.15, 0.18, 0.20, 0.22, 0.25],
    'd2': [True, False]}
KN = {'ev': 'entry VIX level', 'er': 'entry VIX/VIX3M <=', 'xr': 'exit VIX/VIX3M >', 'fade': 'fade exit', 'floor': 'stress floor (QQQ rv30)', 'd2': 'off in ungated D2'}
P2 = {k: [add(mk(**{k: v}), 'P2') for v in vals] for k, vals in KNOBS.items()}
EXTRA = add(mk(er=None, xr=None), 'EXTRA')
P4 = [add(mk(cap=x / 100), 'P4') for x in (10, 15, 20, 25, 30)]
LIVEL = lab(LIVE); assert LIVEL in ALL

# ------------------------------------------------------------------ header + baselines
log('=' * 150); log('run.py: VIXY sleeve sweep (2026-11-17); PLAN.md pre-registered before any cell was run; research only, nothing adopted'); log('=' * 150)
log("LIVE constants (state.py): VIXM_INSTRUMENT=%s ENTRY_VIX=%s EXIT_RATIO=%s (also the entry ratio) MIN_VOL=%s CASH_SHARE=%s FADE=%s OFF_D_ZONES=%s" % (
    S.VIXM_INSTRUMENT, S.VIXM_ENTRY_VIX, S.VIXM_EXIT_RATIO, S.VIXM_MIN_VOL, S.VIXM_CASH_SHARE, S.VIXM_FADE, S.VIXM_OFF_D_ZONES))
for w in WN: log(f"window {w}: returns {RDS[w][0]}..{RDS[w][-1]} ({len(RDS[w])} sessions)")
log("parametrised latch == harness latch on both tracks at live values (asserted).")
log("Data: VIXY/VIXM %s..%s from yahoo-full files; VIX/VIX3M via harness (VC.history); cost 2bp one-way (5bp on sleeve only in the cost test)." % (min(vy), max(vy)))
REF = {'real': (51.1, 2.100, -16.5), 'late': (52.0, 2.029, -20.1), 'oos': (22.6, 0.963, -16.4), 'joined': (42.7, 1.690, -20.1)}
log("\nBASELINE REPRODUCTION (live cell: cap 2.0, VIXY 35%, live trigger)")
for w in WN:
    m = met(LIVE, w); log(f"  {w:<7} CAGR {m['c']*100:.1f}% Sharpe {m['sh']:.3f} maxDD {m['m']*100:.1f}% vol {m['v']*100:.1f}% days-on {m['on']:.1f}% spells {m['sp']} trades/yr {m['tpy']:.1f}   (reference ~{REF[w][0]}% / {REF[w][1]:.3f} / {REF[w][2]}%)")
# exact check vs harness.run on real
r0, _, _ = H.run(True, cfg=CAPCFG, vixm_share=0.35, vixm_ret=INSTR['real']['Y'])
log(f"  real: engine == harness.run with VIXY at 35%: {np.allclose(r0, run(LIVE, 'real')['r'])} (max abs diff {np.abs(r0-run(LIVE,'real')['r']).max():.2e})")
m0 = met(mk(w=0.0), 'real')
log("  no-sleeve book (w=0): " + ' | '.join(f"{w} {met(mk(w=0.0), w)['c']*100:.1f}% / {met(mk(w=0.0), w)['sh']:.3f} / {met(mk(w=0.0), w)['m']*100:.1f}%" for w in WN))
for w in WN:
    tn, s0, e = WIN[w]; al, _ = get_latch(tn, LIVE)
    log(f"  {w}: latch+stress allowed on {al[s0:e].mean()*100:.1f}% of sessions (before D2 gate / cash-leg test); sleeve actually held {met(LIVE, w)['on']:.1f}%")

# ------------------------------------------------------------------ tables
LV = {w: met(LIVE, w) for w in WN}
HDR = f"  {'cell':<30}{'CAGR':>7} {'Shrp':>6} {'maxDD':>7} {'vol':>6} {'on%':>5} {'spl':>4} {'avgW':>6} {'maxW':>6} {'ctb/yr':>7} {'wst1':>7} {'wst5':>7} {'wstSlv':>7} | {'dCAGR':>6} {'dSh':>7} {'dDD':>6}"
def row(l, w):
    m = met(ALL[l][0], w); d = LV[w]
    return (f"  {l:<30}{m['c']*100:6.1f}% {m['sh']:6.3f} {m['m']*100:6.1f}% {m['v']*100:5.1f}% {m['on']:5.1f} {m['sp']:4d} {m['avgw']:5.1f}% {m['maxw']:5.1f}% {m['contrib']:+7.2f} "
            f"{m['w1']*100:6.2f}% {m['w5']*100:6.2f}% {m['wsd']:6.2f}% | {(m['c']-d['c'])*100:+6.2f} {m['sh']-d['sh']:+7.3f} {(m['m']-d['m'])*100:+6.2f}")
def full_table(title, labels):
    log(f"\n##### {title}")
    for w in WN:
        log(f"\n--- window {w} ({RDS[w][0]}..{RDS[w][-1]}): CAGR / Sharpe / maxDD / vol / sleeve days-on % / spells / avg sleeve wt when on (% NAV) / max sleeve wt / sleeve contribution %NAV per yr / worst day / worst 5-session / worst sleeve day (% NAV) | differences vs live (CAGR pp, Sharpe, maxDD pp; + = shallower)")
        log(HDR)
        for l in labels: log(row(l, w) + ('   <- LIVE' if l == LIVEL else ''))
def diff_table(title, labels):
    log(f"\n##### {title}: differences vs live, all windows side by side (dSharpe | dCAGR pp | dMaxDD pp | days-on %)")
    log(f"  {'cell':<30}" + ''.join(f"| {w:^34}" for w in ('real', 'late', 'oos', 'joined')))
    for l in labels:
        c = ALL[l][0]; s = f"  {l:<30}"
        for w in ('real', 'late', 'oos', 'joined'):
            m = met(c, w); d = LV[w]; s += f"| {m['sh']-d['sh']:+7.3f} {(m['c']-d['c'])*100:+6.2f} {(m['m']-d['m'])*100:+6.2f} {m['on']:6.1f}   "
        log(s)
def worst_days(title, labels):
    log(f"\n##### {title}: five worst single-day sleeve P&L (% of NAV) with return dates")
    for w in WN:
        log(f" window {w}")
        for l in labels:
            m = met(ALL[l][0], w); log(f"  {l:<30} " + '  '.join(f"{d} {x:+.2f}" for d, x in m['w5d']))

full_table('PART 1: weight of the cash leg in VIXY (live trigger), plus VIXM reference', P1 + P1M)
diff_table('PART 1', P1 + P1M)
worst_days('PART 1', P1 + P1M)

# Part 2
for k in KNOBS:
    full_table(f"PART 2 knob: {KN[k]} (w=35%, others live)", P2[k])
diff_table('PART 2 (all knobs)', [l for k in KNOBS for l in P2[k]] + [EXTRA])
log(f"\n  (EXTRA = {EXTRA}: no curve test at all, entry ratio none and exit ratio none; 'entry ratio none' alone is identical to live because exit stays 1.00)")
full_table('EXTRA diagnostic', [EXTRA])
worst_days('PART 2', [l for k in KNOBS for l in P2[k]] + [EXTRA])

# knob spread -> part 3
spread = {}
for k in KNOBS:
    vals = [0.5 * ((met(ALL[l][0], 'real')['sh'] - LV['real']['sh']) + (met(ALL[l][0], 'joined')['sh'] - LV['joined']['sh'])) for l in P2[k]]
    spread[k] = max(vals) - min(vals)
log("\nPART 2 knob spread (max - min over the knob's cells of mean(dSharpe real, dSharpe joined)): " + ', '.join(f"{k} {v:.3f}" for k, v in sorted(spread.items(), key=lambda x: -x[1])))
cand = sorted([k for k in KNOBS if k != 'd2'], key=lambda k: -spread[k])[:2]
kA, kB = cand
def pick(k, m):
    vals = KNOBS[k]; li = vals.index(LIVE[k]); m = min(m, len(vals)); st = max(0, min(li - m // 2, len(vals) - m)); return vals[st:st + m]
VA, VB = pick(kA, 5), pick(kB, 4); WS = [0.25, 0.35, 0.50]
log(f"PART 3 joint grid: {KN[kA]} {VA} x {KN[kB]} {VB} x weight {WS} = {len(VA)*len(VB)*len(WS)} cells")
P3 = {}
for a_ in VA:
    for b_ in VB:
        for w_ in WS: P3[(a_, b_, w_)] = add(mk(**{kA: a_, kB: b_, 'w': w_}), 'P3')
P3L = list(dict.fromkeys(P3.values()))
diff_table('PART 3 joint grid', P3L)
log("\nPART 3 detail on real + joined windows (full metrics)")
for w in ('real', 'joined'):
    log(f"\n--- window {w}"); log(HDR)
    for l in P3L: log(row(l, w))
worst_days('PART 3 (selected: all cells)', P3L)

# Part 4
full_table('PART 4: NAV cap on the live sleeve: sleeve = min(35% of cash leg, c x NAV)', [LIVEL] + P4)
worst_days('PART 4', [LIVEL] + P4)

# ------------------------------------------------------------------ bootstrap helpers
def boot_idx(N, n, block=20, seed=11):
    rng = np.random.default_rng(seed); nb = -(-N // block); st = rng.integers(N, size=(n, nb))
    return ((st[:, :, None] + np.arange(block)) % N).reshape(n, -1)[:, :N]
BIDX = {}
def bidx(N):
    if N not in BIDX: BIDX[N] = boot_idx(N, NBOOT)
    return BIDX[N]
def dd_paths(x):
    out = np.empty(len(x))
    for i in range(0, len(x), 400):
        nav = np.cumprod(1 + x[i:i + 400], axis=1); out[i:i + 400] = (nav / np.maximum(np.maximum.accumulate(nav, axis=1), 1)).min(1) - 1
    return out
_bs = {}
def boot_sh(l, w):
    if (l, w) in _bs: return _bs[(l, w)]
    ra = run(ALL[l][0], w)['r']; rl = run(LIVE, w)['r']
    if np.array_equal(ra, rl): _bs[(l, w)] = (1.0, 0.0); return _bs[(l, w)]
    idx = bidx(len(ra)); s = lambda x: x.mean(1) / x.std(1, ddof=1)
    d = (s(ra[idx]) - s(rl[idx])) * 252 ** .5; _bs[(l, w)] = (float((d <= 0).mean()), float(np.median(d))); return _bs[(l, w)]
_bd = {}
def boot_dd(l, w):
    if (l, w) in _bd: return _bd[(l, w)]
    ra = run(ALL[l][0], w)['r']; rl = run(LIVE, w)['r']
    if np.array_equal(ra, rl): _bd[(l, w)] = (1.0, 0.0); return _bd[(l, w)]
    idx = bidx(len(ra)); d = dd_paths(ra[idx]) - dd_paths(rl[idx]); _bd[(l, w)] = (float((d <= 0).mean()), float(np.median(d))); return _bd[(l, w)]
for l in ALL:
    for w in ('real', 'joined'): boot_sh(l, w)
log(f"\n(bootstrap Sharpe computed for all {len(ALL)} cells on real and joined; elapsed {time.time()-T0:.0f}s)")

# ------------------------------------------------------------------ robustness primitives (no engine reruns)
def halves(l, w):
    ra, rl = run(ALL[l][0], w)['r'], run(LIVE, w)['r']; h = len(ra) // 2
    return sh(ra[:h]) - sh(rl[:h]), sh(ra[h:]) - sh(rl[h:])
def ex20(l, w):
    ra, rl = run(ALL[l][0], w)['r'], run(LIVE, w)['r']; x = YRS[w] != '2020'; return sh(ra[x]) - sh(rl[x])

# ------------------------------------------------------------------ reading rule
def neighbours(l):
    c, part = ALL[l]
    if part == 'P1':
        ws = [0, 10, 20, 25, 30, 35, 40, 50, 60, 75, 100]; i = ws.index(round(c['w'] * 100)); return [lab(mk(w=ws[j] / 100)) for j in (i - 1, i + 1) if 0 <= j < len(ws)]
    if part == 'P2':
        for k, labs in P2.items():
            if l in labs:
                i = labs.index(l); return [labs[j] for j in (i - 1, i + 1) if 0 <= j < len(labs)]
    if part == 'P3':
        key = next(kk for kk, v in P3.items() if v == l); out = []
        for ax, vals in enumerate((VA, VB, WS)):
            i = vals.index(key[ax])
            for j in (i - 1, i + 1):
                if 0 <= j < len(vals): kk = list(key); kk[ax] = vals[j]; out.append(P3[tuple(kk)])
        return out
    return []
def sh_pos(l, ws=('real', 'late', 'joined')): return all(met(ALL[l][0], w)['sh'] - LV[w]['sh'] > 0 for w in ws)
def rule(l):
    c = ALL[l][0]; d = {w: (met(c, w)['sh'] - LV[w]['sh'], met(c, w)['m'] - LV[w]['m']) for w in WN}
    r = {}
    r['sharpe'] = all(d[w][0] > 0 for w in ('real', 'late', 'joined')) and d['oos'][0] >= -0.01
    r['dd'] = all(d[w][1] >= -0.005 for w in WN)
    nb = [n for n in neighbours(l) if n != LIVEL]; r['plateau'] = bool(nb) and all(sh_pos(n) for n in nb)
    r['halves'] = all(x > 0 for w in ('real', 'joined') for x in halves(l, w)) and all(ex20(l, w) > 0 for w in ('real', 'joined'))
    r['boot'] = min(boot_sh(l, 'real')[0], boot_sh(l, 'joined')[0]) < 0.10
    r['pass'] = all(r.values()); return r

cells123 = [l for l in ALL if ALL[l][1] in ('P1', 'P2', 'P3') and l != LIVEL]
RULE = {l: rule(l) for l in cells123}
log("\n##### READING RULE per cell (Parts 1-3; VIXM refs, EXTRA, P4 excluded). S = Sharpe up on real/late/joined and oos >= -0.01; D = maxDD not deeper than 0.5pp on any window; P = plateau (non-live neighbours also beat live on real/late/joined); H = both halves and ex-2020 positive on real & joined; B = bootstrap P<0.10 on real or joined")
log(f"  {'cell':<30}{'S':>3}{'D':>3}{'P':>3}{'H':>3}{'B':>3}  PASS   | bootP(dSh<=0) real/joined | halves real (1st,2nd) | ex2020 real, joined")
for l in cells123:
    r = RULE[l]; f = lambda b: 'y' if b else '.'
    hr = halves(l, 'real'); log(f"  {l:<30}{f(r['sharpe']):>3}{f(r['dd']):>3}{f(r['plateau']):>3}{f(r['halves']):>3}{f(r['boot']):>3}  {'PASS' if r['pass'] else '-':<6}| {boot_sh(l,'real')[0]:.3f} / {boot_sh(l,'joined')[0]:.3f}            | {hr[0]:+.3f} {hr[1]:+.3f}        | {ex20(l,'real'):+.3f} {ex20(l,'joined'):+.3f}")
PASSERS = [l for l in cells123 if RULE[l]['pass']]
log(f"\nCells passing every clause of the 'worth proposing' rule: {PASSERS if PASSERS else 'NONE'}")

# ------------------------------------------------------------------ weight verdict
log("\n##### WEIGHT VERDICT (reading rule, first clause)")
wl = [l for l in P1 if l != lab(mk(w=0.0)) or True]
best_real = max(wl, key=lambda l: met(ALL[l][0], 'real')['sh']); best_join = max(wl, key=lambda l: met(ALL[l][0], 'joined')['sh'])
gap_r = met(ALL[best_real][0], 'real')['sh'] - LV['real']['sh']; gap_j = met(ALL[best_join][0], 'joined')['sh'] - LV['joined']['sh']
log(f"  best weight by Sharpe on real: {best_real} (live is {gap_r:.3f} below); on joined: {best_join} (live is {gap_j:.3f} below)")
cond1 = gap_r <= 0.03 and gap_j <= 0.03
nbw = [lab(mk(w=x)) for x in (0.25, 0.30, 0.40, 0.50)]
beat = {l: (met(ALL[l][0], 'oos')['sh'] - LV['oos']['sh'], met(ALL[l][0], 'late')['sh'] - LV['late']['sh']) for l in nbw}
for l, (a_, b_) in beat.items(): log(f"  neighbour {l}: dSharpe oos {a_:+.3f}, late {b_:+.3f}")
cond2 = not any(a_ > 0.02 and b_ > 0.02 for a_, b_ in beat.values())
log(f"  condition 1 (live within 0.03 of best on real and joined): {cond1}; condition 2 (no neighbour weight beats live by >0.02 on BOTH oos and late): {cond2}  => 35% is {'FINE / no change' if cond1 and cond2 else 'NOT cleared by the first-clause rule'}")

# ------------------------------------------------------------------ part 3 plateau
log("\n##### PART 3 plateau: for each cell, the minimum over itself and its axis-adjacent cells of mean(dSharpe real, late, joined); best plateau scores")
def msh(l): return np.mean([met(ALL[l][0], w)['sh'] - LV[w]['sh'] for w in ('real', 'late', 'joined')])
pl = sorted(((min([msh(l)] + [msh(n) for n in neighbours(l)]), msh(l), l) for l in P3L), reverse=True)
for s_, m_, l in pl[:8]: log(f"  {l:<30} plateau-min {s_:+.3f}   own mean dSh {m_:+.3f}   oos dSh {met(ALL[l][0],'oos')['sh']-LV['oos']['sh']:+.3f}   worst maxDD diff {min(met(ALL[l][0],w)['m']-LV[w]['m'] for w in WN)*100:+.2f}pp")
log("  top 8 cells by own mean dSh (biased upward: best of a grid): " + '; '.join(f"{l} {m_:+.3f}" for _, m_, l in sorted(pl, key=lambda x: -x[1])[:8]))

# ------------------------------------------------------------------ live cell spell detail
log("\n##### LIVE CELL, real window: sleeve spells")
tn, s0, e = WIN['real']; ds = TRK[tn]['ds']; R_ = run(LIVE, 'real'); hw = R_['hw']; ctb = R_['ctb']; sp = spells(hw); _, code = get_latch(tn, LIVE)
RS = {1: 'allowed?', 2: 'curve exit (VIX > VIX3M)', 3: 'fade exit', 4: 'stress floor (rv30 < 20%)', 5: 'latch not on'}
rows = []
for i, j in sp:
    ent = ds[s0 + i]; xi = s0 + j + 1; ex = ds[xi] if xi < len(ds) and j + 1 < len(hw) else 'open at end'
    if j + 1 >= len(hw): reason = 'window end (still held)'
    else:
        cd = code[xi]; reason = RS.get(cd, str(cd))
        if cd == 1: reason = 'D2 gate / cash leg used'
        if cd == 5 and BASE[tn]['d2'][xi]: reason = 'D2 gate'
    ret = np.prod(1 + INSTR[tn]['Y'][s0 + i + 1:s0 + j + 2]) - 1; cb = ctb[i:j + 1].sum() * 100
    rows.append((ent, ex, reason, j - i + 1, ret * 100, cb, i, j))
log(f"  {'entry':<11}{'exit':<12}{'exit reason':<30}{'days':>5}{'VIXY ret':>10}{'contrib %NAV':>14}")
for r_ in rows: log(f"  {r_[0]:<11}{r_[1]:<12}{r_[2]:<30}{r_[3]:5d}{r_[4]:+9.1f}%{r_[5]:+13.3f}")
cb = np.array([r_[5] for r_ in rows]); tot = cb.sum(); o = np.argsort(-cb)
log(f"  spells {len(rows)}; total sleeve contribution {tot:+.2f} %NAV (sum of daily P&L, before cost); wins {int((cb>0).sum())}, losses {int((cb<0).sum())}, win rate {(cb>0).mean()*100:.0f}%; mean {cb.mean():+.3f}, median {np.median(cb):+.3f}; mean spell length {np.mean([r_[3] for r_ in rows]):.1f} days")
pos = cb[cb > 0].sum()
for k in (1, 3, 5): log(f"  best {k} spell(s): {cb[o[:k]].sum():+.2f} %NAV = {cb[o[:k]].sum()/tot*100:.0f}% of the net total ({cb[o[:k]].sum()/pos*100:.0f}% of gross gains {pos:+.2f})  [{', '.join(rows[i][0] for i in o[:k])}]")
rest = tot - cb[o[:3]].sum(); log(f"  with the best 3 spells removed: net sleeve contribution {rest:+.2f} %NAV over {len(R_['r'])/252:.2f} yrs ({rest/(len(R_['r'])/252):+.3f} %NAV/yr)")
r_adj = R_['r'].copy()
for i in o[:3]: a_, b_ = rows[i][6], rows[i][7]; r_adj[a_:b_ + 1] -= ctb[a_:b_ + 1]
s_adj, s_none, s_live = stats(r_adj), stats(run(mk(w=0.0), 'real')['r']), stats(R_['r'])
log(f"  book with best-3 spells' sleeve P&L subtracted (approx): CAGR {s_adj['c']*100:.1f}% Sharpe {s_adj['sh']:.3f} maxDD {s_adj['m']*100:.1f}% | no-sleeve book {s_none['c']*100:.1f}% / {s_none['sh']:.3f} / {s_none['m']*100:.1f}% | live {s_live['c']*100:.1f}% / {s_live['sh']:.3f} / {s_live['m']*100:.1f}%")
for w in ('late', 'oos', 'joined'):
    tn_, s0_, e_ = WIN[w]; sp_ = spells(run(LIVE, w)['hw']); log(f"  ({w}: {len(sp_)} spells, {met(LIVE,w)['on']:.1f}% of sessions)")
log("  live-cell spells on the proxy panel 2011-2015 (oos): " + ', '.join(f"{TRK['proxy']['ds'][WIN['oos'][1]+a_]}..{TRK['proxy']['ds'][WIN['oos'][1]+b_+1]}" for a_, b_ in spells(run(LIVE, 'oos')['hw'])))

# ------------------------------------------------------------------ shortlist robustness
ranked = sorted([l for l in cells123 if ALL[l][1] in ('P1', 'P2', 'P3') and not np.array_equal(run(ALL[l][0], 'real')['r'], run(LIVE, 'real')['r'])
                 and l != lab(mk(w=0.0))], key=lambda l: -np.mean([met(ALL[l][0], w)['sh'] - LV[w]['sh'] for w in WN]))
SHORT = [LIVEL]
for l in [lab(mk(w=0.25)), lab(mk(w=0.50))] + ranked[:4] + PASSERS[:6] + [lab(mk(cap=0.20))]:
    if l not in SHORT: SHORT.append(l)
log(f"\n##### ROBUSTNESS shortlist: {SHORT}")
log("  top-4 non-live cells by mean dSharpe over four windows: " + '; '.join(f"{l} {np.mean([met(ALL[l][0], w)['sh'] - LV[w]['sh'] for w in WN]):+.3f}" for l in ranked[:4]))
log(f"\n--- A. halves (by sessions), 2020 removed: Sharpe difference vs live (live's own Sharpe in brackets)")
log(f"  {'cell':<30}" + ''.join(f"| {w+' h1':>8} {w+' h2':>8} {w+' x20':>8} " for w in ('real', 'joined')))
for l in SHORT:
    s = f"  {l:<30}"
    for w in ('real', 'joined'):
        h1, h2 = halves(l, w); s += f"| {h1:+8.3f} {h2:+8.3f} {ex20(l, w):+8.3f} "
    log(s)
for w in ('real', 'joined'):
    rl = run(LIVE, w)['r']; h = len(rl) // 2; x = YRS[w] != '2020'
    log(f"  live Sharpe {w}: h1 {sh(rl[:h]):.3f} h2 {sh(rl[h:]):.3f} ex2020 {sh(rl[x]):.3f} full {sh(rl):.3f}")
log(f"\n--- B. one extra session of lag on the sleeve signal, and 5 bp one-way on sleeve trades: differences vs LIVE under the same condition (dSh / dCAGR pp / dMaxDD pp)")
for cond, kw in (('lag +1 session', dict(lag=1)), ('5bp sleeve cost', dict(c4=0.0005))):
    log(f" condition: {cond}")
    log(f"  {'cell':<30}" + ''.join(f"| {w:^24}" for w in WN))
    lvm = {w: met(LIVE, w, **kw) for w in WN}
    log(f"  {'(live itself: Sharpe/CAGR/DD)':<30}" + ''.join(f"| {lvm[w]['sh']:.3f} {lvm[w]['c']*100:5.1f}% {lvm[w]['m']*100:6.1f}% " for w in WN))
    for l in SHORT[1:]:
        s = f"  {l:<30}"
        for w in WN:
            m = met(ALL[l][0], w, **kw); s += f"| {m['sh']-lvm[w]['sh']:+7.3f} {(m['c']-lvm[w]['c'])*100:+6.2f} {(m['m']-lvm[w]['m'])*100:+6.2f} "
        log(s)
log(f"\n--- C. block bootstrap ({NBOOT} paths, 20-session circular blocks), paired vs live: median dSharpe, P(dSharpe<=0) | median dMaxDD pp, P(arm DD not shallower)")
log(f"  {'cell':<30}" + ''.join(f"| {w:^32}" for w in WN))
for l in SHORT[1:]:
    s = f"  {l:<30}"
    for w in WN:
        if w in ('real', 'joined'): bs = boot_sh(l, w)
        else:
            ra, rl = run(ALL[l][0], w)['r'], run(LIVE, w)['r']; idx = bidx(len(ra)); f_ = lambda x: x.mean(1) / x.std(1, ddof=1); d_ = (f_(ra[idx]) - f_(rl[idx])) * 252 ** .5; bs = (float((d_ <= 0).mean()), float(np.median(d_)))
        bd = boot_dd(l, w); s += f"| {bs[1]:+.3f} P{bs[0]:.2f}  {bd[1]*100:+.2f}pp P{bd[0]:.2f}   "
    log(s)
log("  (P(dSharpe<=0) near 0.5 means the arm is indistinguishable from live; DD P near 0.5 likewise.)")

# ------------------------------------------------------------------ risk trade-off flags
log("\n##### PURE RISK TRADE-OFF flags (not proposals): worst sleeve day on real or joined >=20% smaller in loss than live, or maxDD >=1.0pp shallower on real or joined")
log(f"  live worst sleeve day: real {LV['real']['wsd']:.2f}% ({LV['real']['w5d'][0][0]}), joined {LV['joined']['wsd']:.2f}% ({LV['joined']['w5d'][0][0]}); live max sleeve weight real {LV['real']['maxw']:.1f}% joined {LV['joined']['maxw']:.1f}% of NAV")
fl = []
for l in ALL:
    if l == LIVEL or ALL[l][1] in ('P1M',) : continue
    c = ALL[l][0]
    wsd_ok = any(met(c, w)['wsd'] > LV[w]['wsd'] * 0.8 and LV[w]['wsd'] < 0 for w in ('real', 'joined'))
    dd_ok = any(met(c, w)['m'] - LV[w]['m'] >= 0.01 for w in ('real', 'joined'))
    if wsd_ok or dd_ok: fl.append(l)
log(f"  {'cell':<30}{'wstSlv real/joined':>22}{'dMaxDD real/joined pp':>24}{'dCAGR real/joined pp':>24}{'dSh real/joined':>18}")
for l in fl:
    c = ALL[l][0]; mr, mj = met(c, 'real'), met(c, 'joined')
    log(f"  {l:<30}{mr['wsd']:10.2f}/{mj['wsd']:.2f}%{(mr['m']-LV['real']['m'])*100:+12.2f}/{(mj['m']-LV['joined']['m'])*100:+.2f}{(mr['c']-LV['real']['c'])*100:+13.2f}/{(mj['c']-LV['joined']['c'])*100:+.2f}{mr['sh']-LV['real']['sh']:+10.3f}/{mj['sh']-LV['joined']['sh']:+.3f}")
log(f"\nrun time {time.time()-T0:.0f}s")
