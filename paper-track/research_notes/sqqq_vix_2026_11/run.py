"""SQQQ held by VIX level: research only. PLAN.md (pre-registered 2026-11-20) defines every arm, window and the pass bar."""
import csv, os, sys, warnings
import numpy as np
warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.abspath(__file__)); PT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, PT)
import harness_live as HL
H = HL.H; MC = HL.MC; S = HL.S
LOG = open(os.path.join(HERE, 'run.log'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); LOG.write(s + '\n'); LOG.flush()

SQ_FIRST = '2010-02-12'            # first session with a real SQQQ return
SQ_ER = 0.0095
SQ_FIRST_PREV = '2010-02-11'
# ---------------------------------------------------------------- data
SQ = {}
for r in csv.DictReader(open(os.path.join(HERE, 'sqqq_yahoo_full.csv'))):
    SQ[r['d']] = (float(r['close_split_adj']), float(r['adjclose']))
PANELS = {'real': dict(pn=H.pr, ds=H.RD, sg=HL.signals(False)[1], real=True),
          'proxy': dict(pn=H.p, ds=H.PD, sg=HL.signals(False)[0], real=False)}

def synth(pn):
    return np.maximum(-3 * pn['qqq_tr'] + 4 * pn['cash'] - SQ_ER / 252, -0.99)

def sqqq_rets(ds, pn, which):
    """real SQQQ (adjclose = total return, or split-adjusted price) from SQ_FIRST on, synthetic before"""
    j = 1 if which == 'adj' else 0
    out = synth(pn).copy(); last = None; miss = 0
    for i, d in enumerate(ds):
        if d < SQ_FIRST:
            if i + 1 < len(ds) and ds[i + 1] == SQ_FIRST: last = (d,); SQ.setdefault(d, SQ[SQ_FIRST_PREV])   # first return = 02-12 close vs 02-11 close
            continue
        if d in SQ and last is not None and last[0] in SQ:
            out[i] = SQ[d][j] / SQ[last[0]][j] - 1
        elif i == 0 or last is None:
            out[i] = 0.0                                          # panel day 0 (no prior close)
        else:
            miss += 1; out[i] = 0.0
        last = (d,)
    if which == 'adj' and miss: log('  WARNING: SQQQ missing for', miss, 'panel dates')
    return out

# ---------------------------------------------------------------- 0. data check
log('=' * 110); log('0. SQQQ DATA CHECK (real SQQQ vs synthetic -3x QQQ)'); log('=' * 110)
pn = H.p; ds = H.PD
i0 = ds.index(SQ_FIRST)
sq_adj = sqqq_rets(ds, pn, 'adj'); sq_px = sqqq_rets(ds, pn, 'px'); syn = synth(pn)
pure3 = -3 * pn['qqq_tr']; pure3px = -3 * pn['qqq']
miss_in_file = [d for d in ds[i0:] if d not in SQ]
log(f"  SQQQ file: {len(SQ)} rows {min(SQ)}..{max(SQ)}; panel dates from {SQ_FIRST}: {len(ds) - i0}; panel dates with no SQQQ row: {len(miss_in_file)}; file rows not in panel: {sorted(set(SQ) - set(ds))}")
log(f"  worst real daily return {sq_adj[i0:].min()*100:.2f}% on {ds[i0 + int(np.argmin(sq_adj[i0:]))]}, best {sq_adj[i0:].max()*100:+.2f}% on {ds[i0 + int(np.argmax(sq_adj[i0:]))]}")
def cmp(name, a, b):
    d = a[i0:] - b[i0:]
    cg = lambda x: np.prod(1 + x[i0:]) ** (252 / (len(x) - i0)) - 1
    log(f"  {name:62s} mean daily diff {d.mean()*1e4:+7.2f} bp = {d.mean()*252*100:+6.2f}%/yr (sd of daily diff {d.std()*100:.3f}%, corr {np.corrcoef(a[i0:], b[i0:])[0,1]:.5f}); CAGR {cg(a)*100:+6.1f}% vs {cg(b)*100:+6.1f}%")
cmp('real SQQQ (adjclose) minus synthetic (-3 TR + 4 cash - 0.95%)', sq_adj, syn)
cmp('real SQQQ (price only) minus synthetic', sq_px, syn)
cmp('real SQQQ (adjclose) minus pure -3 x QQQ total return', sq_adj, pure3)
cmp('real SQQQ (price only) minus pure -3 x QQQ price return', sq_px, pure3px)
cmp('synthetic minus pure -3 x QQQ total return', syn, pure3)
log('  by year, real SQQQ (adjclose) minus synthetic, mean daily diff annualised (%/yr) | calendar-year return real vs synthetic:')
yrs = np.array([int(d[:4]) for d in ds])
for y in range(2010, 2027):
    m = (yrs == y) & (np.arange(len(ds)) >= i0)
    d = (sq_adj - syn)[m]
    log(f"    {y}: {d.mean()*252*100:+6.2f}   real {(np.prod(1 + sq_adj[m]) - 1)*100:+7.1f}%  synth {(np.prod(1 + syn[m]) - 1)*100:+7.1f}%  price-only {(np.prod(1 + sq_px[m]) - 1)*100:+7.1f}%")
dv = [(d, SQ[d][0]) for d in sorted(SQ) if False]
log('  Distributions: adjclose vs price-only return gap above is the dividend component (SQQQ pays income, mostly 2023).')
log('  PRE-2010 PROXY (flagged): synthetic = max(-3 x QQQ TR + 4 x T-bill - 0.95%/252, -99%), daily reset, no swap spread, no tracking noise; used only in W2 before 2010-02-12.')

# ---------------------------------------------------------------- arms
def trig_defs(vix, vixp, vix3, gap, eff):
    with np.errstate(invalid='ignore'):
        return {
            'S1 VIX<15': vix < 15, 'S1 15-20': (vix >= 15) & (vix < 20), 'S1 20-25': (vix >= 20) & (vix < 25),
            'S1 25-30': (vix >= 25) & (vix < 30), 'S1 VIX>=30': vix >= 30,
            'S2 VIX>=25': vix >= 25, 'S2 VIX>=30': vix >= 30, 'S2 VIX>=35': vix >= 35,
            'S3 calm&stretched': (vix < 18) & (gap > 0.10),
            'S4 E/F': (eff == 4) | (eff == 5), 'S4 E/F & VIX>=25': ((eff == 4) | (eff == 5)) & (vix >= 25),
            'S5 VIX up>=10%': vix / vixp - 1 >= 0.10, 'S5 VIX>VIX3M': vix > vix3}
TRIGS = ['S1 VIX<15', 'S1 15-20', 'S1 20-25', 'S1 25-30', 'S1 VIX>=30', 'S2 VIX>=25', 'S2 VIX>=30', 'S2 VIX>=35',
         'S3 calm&stretched', 'S4 E/F', 'S4 E/F & VIX>=25', 'S5 VIX up>=10%', 'S5 VIX>VIX3M']
HS = (0.05, 0.10, 0.20)
CHAIN = [['S1 VIX<15', 'S1 15-20', 'S1 20-25', 'S1 25-30', 'S1 VIX>=30'], ['S2 VIX>=25', 'S2 VIX>=30', 'S2 VIX>=35'],
         ['S4 E/F', 'S4 E/F & VIX>=25'], ['S5 VIX up>=10%', 'S5 VIX>VIX3M']]
ARMS = [(t, h) for t in TRIGS for h in HS]
def neighbours(t, h):
    out = []; k = HS.index(h)
    for kk in (k - 1, k + 1):
        if 0 <= kk < len(HS): out.append((t, HS[kk]))
    for ch in CHAIN:
        if t in ch:
            q = ch.index(t)
            for qq in ((q - 1, q + 1) if len(ch) > 2 else (1 - q,)):
                if 0 <= qq < len(ch): out.append((ch[qq], h))
    return out

_BUILD = {}
def get_base(track):
    if track not in _BUILD:
        P = PANELS[track]; b = HL.build(track, vixy_source='old'); ds = b['ds']; assert ds == P['ds']
        vix = np.array([H.VIX.get(d, np.nan) for d in ds]); vix3 = np.array([H.VIX3M.get(d, np.nan) for d in ds])
        bad = [d for d, v in zip(ds, vix) if np.isnan(v) and d > '2000-12-31']
        assert not bad, bad[:3]
        vixp = np.concatenate([[np.nan], vix[:-1]])
        gap = np.nan_to_num(P['sg']['gaps'][200][0], nan=-9)
        _BUILD[track] = dict(b=b, vix=vix, trig=trig_defs(vix, vixp, vix3, gap, b['eff']), ds=ds, pn=P['pn'])
    return _BUILD[track]

def run_window(track, d0, d1='2099', lag=0, cost=None, which='adj'):
    B = get_base(track); b = B['b']; ds = B['ds']; pn = B['pn']
    W0, L0, key0 = b['W'], b['L'], b['key']; T = len(ds)
    s0 = next(i for i, d in enumerate(ds) if d >= d0); e = max(i for i, d in enumerate(ds) if d <= d1)
    sq = sqqq_rets(ds, pn, which)
    c = W0[:, -1]; risky = 1 - c
    Lx = np.concatenate([L0, sq[:, None]], 1)                       # [..., cash, sqqq]
    Ws, Wm, Ks, X, info = [W0 * 1.0], [W0 * 1.0], [key0], [np.zeros(T)], [None]
    Ws[0] = np.concatenate([W0, np.zeros((T, 1))], 1); Wm[0] = Ws[0].copy()
    for (t, h) in ARMS:
        on = B['trig'][t].copy()
        if lag: on = np.concatenate([np.zeros(lag, bool), on[:-lag]])
        x = h * on; take = np.minimum(x, c); rest = x - take
        sc = np.where(rest > 1e-15, 1 - rest / np.maximum(risky, 1e-12), 1.0)
        base = W0[:, :-1] * sc[:, None]
        Ws.append(np.concatenate([base, (c - take)[:, None], x[:, None]], 1))
        Wm.append(np.concatenate([base, (c - take + x)[:, None], np.zeros((T, 1))], 1))
        Ks.append(key0 + on.astype(np.int64) * 10 ** 8); X.append(x); info.append((on, rest, x))
    P = len(Ws)
    Wall = np.stack(Ws[:1] + sum(([Ws[i], Wm[i]] for i in range(1, P)), []), 0)[:, :e + 1]
    assert np.allclose(Wall.sum(-1), 1.0)
    Kall = np.stack([Ks[0]] + sum(([Ks[i], Ks[i]] for i in range(1, P)), []), 0)[:, :e + 1]
    old = MC.COST
    if cost is not None: MC.COST = cost
    try: r, tr = MC.run_strategy(Wall, Kall, Lx[None, :e + 1], s0)
    finally: MC.COST = old
    out = dict(ds=ds[s0 + 1:e + 1], s0=s0, e=e, base=r[0], tpy=tr / ((e - s0) / 252), arms={}, sq=sq, qqq=pn['qqq'], cash=pn['cash'])
    for k, a in enumerate(ARMS):
        on, rest, x = info[k + 1]
        out['arms'][a] = dict(r=r[1 + 2 * k], m=r[2 + 2 * k], x=x, on=on, rest=rest, tpy=tr[1 + 2 * k])
    return out

# ---------------------------------------------------------------- metrics
def sharpe(r): return r.mean() * 252 / (r.std(ddof=1) * 252 ** 0.5)
def cagr(r): return np.prod(1 + r) ** (252 / len(r)) - 1
def maxdd(r):
    nav = np.cumprod(1 + r); pk = np.maximum.accumulate(np.concatenate([[1.0], nav]))[1:]; return (nav / pk - 1).min()
def worst20(r):
    lr = np.log1p(r); cs = np.concatenate([[0.0], np.cumsum(lr)]); return np.exp((cs[20:] - cs[:-20]).min()) - 1
def met(r): return dict(c=cagr(r), sh=sharpe(r), dd=maxdd(r), w1=r.min(), w20=worst20(r))

def arm_stats(R, a):
    A = R['arms'][a]; n = len(A['r']); s0 = R['s0']
    xw = A['x'][s0:s0 + n]                       # weight set at close t-1 for the day t = s0+1+i
    rs = R['sq'][s0 + 1:s0 + 1 + n]; q = R['qqq'][s0 + 1:s0 + 1 + n]; ca = R['cash'][s0 + 1:s0 + 1 + n]
    held = xw > 0; yrs_ = n / 252
    pn_ = xw * rs; crash = q <= -0.02
    d = dict(arm=met(A['r']), mc=met(A['m']), on=held.mean(), avgw=xw.mean(), avgw_on=xw[held].mean() if held.any() else 0.0,
             pnl_crash=pn_[crash].sum() / yrs_ * 100, pnl_other=pn_[~crash].sum() / yrs_ * 100, carry=(xw * ca).sum() / yrs_ * 100,
             sq_arith=rs[held].mean() * 252 * 100 if held.any() else np.nan,
             sq_comp=(np.prod(1 + rs[held]) ** (252 / held.sum()) - 1) * 100 if held.sum() > 20 else np.nan,
             n_on=int(held.sum()), n_crash_on=int((held & crash).sum()), n_crash=int(crash.sum()),
             sf_freq=(A['rest'][s0:s0 + n][held] > 1e-12).mean() if held.any() else 0.0,
             sf_mean=(A['rest'][s0:s0 + n][held] / xw[held]).mean() if held.any() else 0.0, tpy=A['tpy'])
    return d

def years_of(R): return np.array([int(x[:4]) for x in R['ds']])

NB = 2000
def boot_idx(n, seed):
    rng = np.random.default_rng(seed); nb = -(-n // 20)
    st = rng.integers(0, n - 19, (NB, nb)); return (st[:, :, None] + np.arange(20)).reshape(NB, -1)[:, :n]
BI = {}
def boot_p(ra, rm, seed=20261120):
    n = len(ra)
    if n not in BI: BI[n] = boot_idx(n, seed)
    idx = BI[n]; ds_ = np.empty(NB)
    for k in range(0, NB, 250):
        i = idx[k:k + 250]; A = ra[i]; M = rm[i]
        ds_[k:k + 250] = A.mean(1) / A.std(1, ddof=1) - M.mean(1) / M.std(1, ddof=1)
    ds_ *= 252 ** 0.5
    return (ds_ <= 0).mean(), np.percentile(ds_, [5, 95])

# ---------------------------------------------------------------- run all windows
WIN = [('W1 real 2015-11..', 'real', '2015-11-02', '2099'), ('W2 proxy 2001..', 'proxy', '2001-01-02', '2099'),
       ('W3 proxy 2010-02..', 'proxy', '2010-02-11', '2099'), ('W4 proxy 2010-02..2015-10', 'proxy', '2010-02-11', '2015-10-30')]
RUN = {}
for nm, tr, d0, d1 in WIN:
    if nm.startswith('W4'): continue
    RUN[nm] = run_window(tr, d0, d1)
def trim(R, n_days_end):   # W4 = exact prefix of W3
    return R
R3 = RUN['W3 proxy 2010-02..']
n4 = sum(1 for d in R3['ds'] if d <= '2015-10-30')
R4 = dict(R3); R4['ds'] = R3['ds'][:n4]; R4['base'] = R3['base'][:n4]
R4['arms'] = {a: dict(v, r=v['r'][:n4], m=v['m'][:n4]) for a, v in R3['arms'].items()}
R4['e'] = R3['s0'] + n4
RUN['W4 proxy 2010-02..2015-10'] = R4
WN = [w[0] for w in WIN]
def stats_window(R):
    n = len(R['ds'])
    out = {}
    for a in ARMS:
        A = R['arms'][a]; s0 = R['s0']
        xw = A['x'][s0:s0 + n]; rs = R['sq'][s0 + 1:s0 + 1 + n]; q = R['qqq'][s0 + 1:s0 + 1 + n]; ca = R['cash'][s0 + 1:s0 + 1 + n]
        held = xw > 0; yrs_ = n / 252; pn_ = xw * rs; crash = q <= -0.02
        out[a] = dict(arm=met(A['r']), mc=met(A['m']), on=held.mean(), avgw=xw.mean(), avgw_on=xw[held].mean() if held.any() else 0.0,
                      pnl_crash=pn_[crash].sum() / yrs_ * 100, pnl_other=pn_[~crash].sum() / yrs_ * 100, carry=(xw * ca).sum() / yrs_ * 100,
                      sq_arith=rs[held].mean() * 252 * 100 if held.any() else np.nan,
                      sq_comp=(np.prod(1 + rs[held]) ** (252 / held.sum()) - 1) * 100 if held.sum() > 20 else np.nan,
                      n_on=int(held.sum()), n_crash=int(crash.sum()), n_crash_on=int((held & crash).sum()),
                      sf_freq=(A['rest'][s0:s0 + n][held] > 1e-12).mean() if held.any() else 0.0,
                      sf_mean=(A['rest'][s0:s0 + n][held] / xw[held]).mean() if held.any() else 0.0)
    return out
ST = {w: stats_window(RUN[w]) for w in WN}
BASE = {w: met(RUN[w]['base']) for w in WN}
for w in WN:
    R = RUN[w]; log(f"\n{w}: {R['ds'][0]}..{R['ds'][-1]}, {len(R['ds'])} sessions; QQQ -2% or worse on {int((R['qqq'][R['s0']+1:R['s0']+1+len(R['ds'])] <= -0.02).sum())} days")
    log(f"  Base (no SQQQ): CAGR {BASE[w]['c']*100:.1f}% Sharpe {BASE[w]['sh']:.3f} maxDD {BASE[w]['dd']*100:.1f}% worst day {BASE[w]['w1']*100:.2f}% worst20 {BASE[w]['w20']*100:.1f}%; trades/yr {RUN['W1 real 2015-11..' if w.startswith('W1') else w]['tpy'][0]:.1f}")

# ---------------------------------------------------------------- 1. arm tables
def aname(a): return f"{a[0]} h{int(a[1]*100)}"
log('\n' + '=' * 110); log('1. ARM vs MATCHED CASH, four windows. cells: CAGR% / Sharpe / maxDD%  (arm | matched cash) ; dSh = arm minus MC; dDD pp (+ = arm shallower); on = share of days SQQQ held; avgW = avg SQQQ weight over all days'); log('=' * 110)
for w in WN:
    log(f"\n--- {w} ---   Base {BASE[w]['c']*100:.1f} / {BASE[w]['sh']:.3f} / {BASE[w]['dd']*100:.1f}")
    log(f"{'arm':26s} {'arm CAGR/Sh/DD':>22s} {'matched cash':>22s}  {'dCAGR':>6s} {'dSh':>7s} {'dDD':>5s} {'dW1':>6s} {'dW20':>6s}  {'on%':>5s} {'avgW%':>5s}")
    for a in ARMS:
        s = ST[w][a]; A, M = s['arm'], s['mc']
        log(f"{aname(a):26s} {A['c']*100:6.1f} {A['sh']:6.3f} {A['dd']*100:6.1f}   {M['c']*100:6.1f} {M['sh']:6.3f} {M['dd']*100:6.1f}  {(A['c']-M['c'])*100:+6.2f} {A['sh']-M['sh']:+7.3f} {(A['dd']-M['dd'])*100:+5.1f} {(A['w1']-M['w1'])*100:+6.2f} {(A['w20']-M['w20'])*100:+6.2f}  {s['on']*100:5.1f} {s['avgw']*100:5.2f}")

# ---------------------------------------------------------------- 2. SQQQ leg P&L
log('\n' + '=' * 110); log('2. SQQQ LEG: P&L in % of NAV per year (target weight x SQQQ return). crash = days QQQ -2% or worse. net = total minus the T-bill the same weight would have earned. own = SQQQ return while held (annualised arithmetic | compounded over held days). sf = share of held days the cash leg was too small (funded partly pro-rata from risky legs) and mean share of the SQQQ weight so funded'); log('=' * 110)
for w in WN:
    log(f"\n--- {w} ---")
    log(f"{'arm':26s} {'crash':>7s} {'other':>7s} {'total':>7s} {'net':>7s}  {'nOn':>5s} {'crashOn/all':>11s}  {'own arith%':>10s} {'own comp%':>10s}  {'sf%':>5s} {'sfShare':>7s}")
    for a in ARMS:
        s = ST[w][a]
        log(f"{aname(a):26s} {s['pnl_crash']:+7.2f} {s['pnl_other']:+7.2f} {s['pnl_crash']+s['pnl_other']:+7.2f} {s['pnl_crash']+s['pnl_other']-s['carry']:+7.2f}  {s['n_on']:5d} {s['n_crash_on']:5d}/{s['n_crash']:<5d}  {s['sq_arith']:10.1f} {s['sq_comp']:10.1f}  {s['sf_freq']*100:5.1f} {s['sf_mean']*100:6.1f}%")

# ---------------------------------------------------------------- 3. robustness for every arm
def half_ex(R, a):
    A = R['arms'][a]; n = len(A['r']); h = n // 2; y = years_of(R)
    out = dict(h1=sharpe(A['r'][:h]) - sharpe(A['m'][:h]), h2=sharpe(A['r'][h:]) - sharpe(A['m'][h:]))
    k = y != 2020
    out['x20'] = sharpe(A['r'][k]) - sharpe(A['m'][k]) if k.sum() < n else np.nan
    return out
RB = {}
for w in WN:
    R = RUN[w]
    for a in ARMS:
        A = R['arms'][a]; p, ci = boot_p(A['r'], A['m'])
        RB[(w, a)] = dict(half_ex(R, a), P=p, ci=ci)
# variants: lag, cost, price-only
VAR = {}
for vn, kw in (('lag1', dict(lag=1)), ('cost5bp', dict(cost=0.0005)), ('priceonly', dict(which='px'))):
    for nm, tr, d0, d1 in WIN:
        if nm.startswith('W4'): continue
        R = run_window(tr, d0, d1, **kw); VAR[(vn, nm)] = R
    R3v = VAR[(vn, 'W3 proxy 2010-02..')]
    VAR[(vn, WN[3])] = dict(R3v, arms={a: dict(v, r=v['r'][:n4], m=v['m'][:n4]) for a, v in R3v['arms'].items()})
def dsh(R, a): A = R['arms'][a]; return sharpe(A['r']) - sharpe(A['m'])
def ddd(R, a): A = R['arms'][a]; return (maxdd(A['r']) - maxdd(A['m'])) * 100

# ---------------------------------------------------------------- 4. verdicts
def crit(a):
    c = {}
    c['c1'] = all(ST[w][a]['arm']['sh'] > ST[w][a]['mc']['sh'] for w in WN)
    c['c2'] = all(ST[w][a]['arm']['dd'] >= ST[w][a]['mc']['dd'] - 0.005 for w in WN)
    c['c3'] = all(RB[(w, a)]['h1'] > 0 and RB[(w, a)]['h2'] > 0 for w in WN) and all(RB[(w, a)]['x20'] > 0 for w in WN[:3])
    c['c5'] = min(RB[(w, a)]['P'] for w in WN) < 0.10
    return c
CR = {a: crit(a) for a in ARMS}
for a in ARMS:
    CR[a]['c4'] = any(CR[n]['c1'] for n in neighbours(*a))
VER = {}
for a in ARMS:
    c = CR[a]; fails = [k for k in ('c1', 'c2', 'c3', 'c4', 'c5') if not c[k]]
    sh_lt = sum(ST[w][a]['arm']['sh'] < ST[w][a]['mc']['sh'] for w in WN)
    ins = sh_lt >= 1 and sum((ST[w][a]['arm']['dd'] - ST[w][a]['mc']['dd']) >= 0.01 and (ST[w][a]['arm']['w20'] - ST[w][a]['mc']['w20']) >= 0.01 for w in WN) >= 3
    VER[a] = ('PASS' if not fails else 'REJECT', fails, ins)
log('\n' + '=' * 110); log('3. ROBUSTNESS, every arm: dSh (arm minus matched cash) per window | halves h1/h2 | ex-2020 | bootstrap P(dSh<=0) | lag1 dSh | 5bp dSh | price-only SQQQ dSh'); log('=' * 110)
for w in WN:
    log(f"\n--- {w} ---")
    log(f"{'arm':26s} {'dSh':>7s} {'h1':>7s} {'h2':>7s} {'ex2020':>7s} {'boot P':>7s} {'90% CI':>16s}  {'lag1':>7s} {'5bp':>7s} {'px-only':>8s}   dDD lag1/5bp/px")
    for a in ARMS:
        s = ST[w][a]; b = RB[(w, a)]
        log(f"{aname(a):26s} {s['arm']['sh']-s['mc']['sh']:+7.3f} {b['h1']:+7.3f} {b['h2']:+7.3f} {b['x20']:+7.3f} {b['P']:7.3f} [{b['ci'][0]:+6.3f},{b['ci'][1]:+6.3f}]  "
            f"{dsh(VAR[('lag1', w)], a):+7.3f} {dsh(VAR[('cost5bp', w)], a):+7.3f} {dsh(VAR[('priceonly', w)], a):+8.3f}   {ddd(VAR[('lag1', w)], a):+.1f}/{ddd(VAR[('cost5bp', w)], a):+.1f}/{ddd(VAR[('priceonly', w)], a):+.1f}")
ncell = len(ARMS) * len(WN); nP = sum(RB[(w, a)]['P'] < 0.10 for w in WN for a in ARMS)
log(f"\nBootstrap cells with P<0.10 (arm better than matched cash): {nP} of {ncell} ({nP/ncell*100:.0f}%); cells with P>0.90 (arm worse): {sum(RB[(w, a)]['P'] > 0.90 for w in WN for a in ARMS)}. Arms are highly correlated (same events), so counts are not independent tests.")

log('\n' + '=' * 110); log('4. PRE-REGISTERED VERDICTS (c1 Sharpe>MC all 4 windows; c2 maxDD not >0.5pp deeper; c3 halves + ex-2020; c4 neighbour c1; c5 bootstrap P<0.10 on >=1 window)'); log('=' * 110)
log(f"{'arm':26s} {'c1':>3s} {'c2':>3s} {'c3':>3s} {'c4':>3s} {'c5':>3s}  verdict  insurance  | dSh W1..W4 | worst-window dDD pp | min P")
for a in ARMS:
    c = CR[a]; v = VER[a]
    log(f"{aname(a):26s} " + ' '.join(f"{'Y' if c[k] else 'n':>3s}" for k in ('c1', 'c2', 'c3', 'c4', 'c5')) + f"  {v[0]:7s}  {'FLAG' if v[2] else '-':9s}| " +
        ' '.join(f"{ST[w][a]['arm']['sh']-ST[w][a]['mc']['sh']:+.3f}" for w in WN) + ' | ' + f"{min((ST[w][a]['arm']['dd']-ST[w][a]['mc']['dd'])*100 for w in WN):+.1f}" + f" | {min(RB[(w, a)]['P'] for w in WN):.3f}")
log(f"\nPASS: {[aname(a) for a in ARMS if VER[a][0] == 'PASS']}")
log(f"insurance flags: {[aname(a) for a in ARMS if VER[a][2]]}")
log(f"arms with c1 (Sharpe > MC on all four windows): {[aname(a) for a in ARMS if CR[a]['c1']]}")

# ---------------------------------------------------------------- 5. year table (W3) for best arms
def score(a): return np.mean([ST[w][a]['arm']['sh'] - ST[w][a]['mc']['sh'] for w in WN])
best = sorted(ARMS, key=score, reverse=True)[:8]
log('\n' + '=' * 110); log('5. BEST 8 ARMS by mean dSh over the four windows: summary'); log('=' * 110)
for a in best:
    log(f"{aname(a):26s} mean dSh {score(a):+.3f}; dSh " + ' '.join(f"{ST[w][a]['arm']['sh']-ST[w][a]['mc']['sh']:+.3f}" for w in WN) + f"; verdict {VER[a][0]} fails {VER[a][1]}")
yrs3 = years_of(R3)
def year_ret(r, y): return (np.prod(1 + r[yrs3 == y]) - 1) * 100
log('\n' + '=' * 110); log('6. YEAR BY YEAR (W3 proxy 2010-02..2026-11-19, real SQQQ), arm return minus matched-cash return, pp; Base return column = no-SQQQ book'); log('=' * 110)
log(f"{'year':6s} {'Base':>7s} " + ' '.join(f"{aname(a)[:22]:>22s}" for a in best[:6]))
for y in range(2010, 2027):
    row = f"{y:<6d} {year_ret(R3['base'], y):7.1f} " + ' '.join(f"{year_ret(R3['arms'][a]['r'], y)-year_ret(R3['arms'][a]['m'], y):+22.2f}" for a in best[:6])
    log(row + ('   <-- 2020' if y == 2020 else '   <-- 2022' if y == 2022 else ''))
ysq = {y: (np.prod(1 + R3['sq'][R3['s0']+1:R3['s0']+1+len(yrs3)][yrs3 == y]) - 1) * 100 for y in range(2010, 2027)}
log('real SQQQ calendar-year total return (W3 days): ' + ' '.join(f"{y}:{v:+.0f}%" for y, v in ysq.items()))
with open(os.path.join(HERE, 'years_all_arms.csv'), 'w') as f:
    f.write('arm,' + ','.join(str(y) for y in range(2010, 2027)) + '\n')
    for a in ARMS:
        f.write(aname(a) + ',' + ','.join('%.2f' % (year_ret(R3['arms'][a]['r'], y) - year_ret(R3['arms'][a]['m'], y)) for y in range(2010, 2027)) + '\n')
log('(all 39 arms x years: years_all_arms.csv)')
log('\nyears where the arm beat matched cash / total, and sum of pp in 2020 and 2022, for every arm (W3):')
for a in ARMS:
    d = [year_ret(R3['arms'][a]['r'], y) - year_ret(R3['arms'][a]['m'], y) for y in range(2010, 2027)]
    log(f"  {aname(a):26s} beat {sum(x > 0 for x in d):2d}/17   2020 {d[10]:+7.2f}  2022 {d[12]:+7.2f}  worst year {min(d):+7.2f} ({2010+int(np.argmin(d))})  best {max(d):+7.2f} ({2010+int(np.argmax(d))})")

# ---------------------------------------------------------------- 7. shares of days on, per window (VIX distribution), and funding
log('\n' + '=' * 110); log('7. TRIGGER DAY COUNTS (share of scored sessions the trigger is on) and cash-leg size on trigger days'); log('=' * 110)
for w in WN:
    R = RUN[w]; s0 = R['s0']; n = len(R['ds'])
    log(f"--- {w}: " + '; '.join(f"{t} {ST[w][(t, .05)]['on']*100:.1f}%" for t in TRIGS))
log('\nTrigger flips per year (on<->off) and the extra cost of a 5 bp SQQQ-leg-only trade cost at h=10%, % of NAV per year (= flips x 0.10 x 5 bp):')
for w in (WN[0], WN[2]):
    R = RUN[w]; s0 = R['s0']; n = len(R['ds']); parts = []
    for t in TRIGS:
        on = R['arms'][(t, .10)]['on'][s0:s0 + n]; fl = (on[1:] != on[:-1]).sum() / (n / 252)
        parts.append(f"{t} {fl:.0f}/yr ({fl * 0.10 * 0.0005 * 100:.3f}%)")
    log(f"--- {w}: " + '; '.join(parts))
log('\nFunding shortfall (SQQQ weight partly funded pro-rata from risky legs), h=10%, share of held days / mean share of weight so funded:')
for w in WN:
    log(f"--- {w}: " + '; '.join(f"{t} {ST[w][(t, .10)]['sf_freq']*100:.0f}%/{ST[w][(t, .10)]['sf_mean']*100:.0f}%" for t in TRIGS))

log('\n' + '=' * 110); log('8. WHICH CHECKS FAILED, best 8 arms (c3 detail: windows where a half or ex-2020 dSh <= 0)'); log('=' * 110)
for a in best:
    bad = [f"{w[:2]}:" + ','.join(k for k in ('h1', 'h2', 'x20') if k in RB[(w, a)] and not (RB[(w, a)][k] > 0) and not (k == 'x20' and w.startswith('W4'))) for w in WN]
    bad = [b for b in bad if not b.endswith(':')]
    log(f"  {aname(a):26s} c3 failures: {bad}; neighbours checked: {[aname(n) for n in neighbours(*a)]}; neighbour c1: {[CR[n]['c1'] for n in neighbours(*a)]}")

log('\n' + '=' * 110); log('9. POST-HOC (NOT part of the pass bar): dSh and dCAGR vs matched cash by sub-period, from the W2 run (2001-2009 uses synthetic SQQQ)'); log('=' * 110)
R2 = RUN['W2 proxy 2001..']; d2 = np.array(R2['ds'])
SUB = [('2001-2009', '2001-01-01', '2010-02-11'), ('2010-02..2015-10', '2010-02-12', '2015-10-31'), ('2015-11..2020-12', '2015-11-01', '2020-12-31'), ('2021-2026', '2021-01-01', '2026-12-31'), ('2015-11..2026 (=W1 span)', '2015-11-01', '2026-12-31')]
log(f"{'arm':26s} " + ' '.join(f"{n:>26s}" for n, _, _ in SUB) + '   (dSh / dCAGR pp)')
for a in best + [('S1 VIX<15', .05)]:
    row = f"{aname(a):26s} "
    for n, lo, hi in SUB:
        m = (d2 >= lo) & (d2 <= hi); A = R2['arms'][a]
        row += f"{sharpe(A['r'][m]) - sharpe(A['m'][m]):+11.3f} / {(cagr(A['r'][m]) - cagr(A['m'][m]))*100:+7.2f}      "
    log(row)
q2 = R2['qqq'][R2['s0'] + 1:R2['s0'] + 1 + len(d2)]
log('QQQ -2% or worse days by sub-period: ' + '; '.join(f"{n} {int((q2[(d2 >= lo) & (d2 <= hi)] <= -0.02).sum())}" for n, lo, hi in SUB))
# ---------------------------------------------------------------- markdown tables for README
with open(os.path.join(HERE, 'arm_table.md'), 'w') as f:
    f.write('| arm | ' + ' | '.join(w.split(' ')[0] + ' ' + ' '.join(w.split(' ')[1:]) for w in WN) + ' |\n|---|' + '---|' * len(WN) + '\n')
    f.write('| Base (no SQQQ) | ' + ' | '.join(f"{BASE[w]['c']*100:.1f} / {BASE[w]['sh']:.3f} / {BASE[w]['dd']*100:.1f}" for w in WN) + ' |\n')
    for a in ARMS:
        cells = []
        for w in WN:
            s = ST[w][a]; A, M = s['arm'], s['mc']
            cells.append(f"{A['c']*100:.1f} / {A['sh']:.3f} / {A['dd']*100:.1f} vs {M['c']*100:.1f} / {M['sh']:.3f} / {M['dd']*100:.1f}; on {s['on']*100:.0f}%")
        f.write(f"| {aname(a)} | " + ' | '.join(cells) + ' |\n')
    f.write('\n\nSQQQ-leg P&L, % of NAV per year (crash days / other days / net of cash carry), SQQQ own return while held (arithmetic / compounded %/yr)\n\n')
    f.write('| arm | ' + ' | '.join(w.split(' ')[0] for w in WN) + ' |\n|---|' + '---|' * len(WN) + '\n')
    for a in ARMS:
        f.write(f"| {aname(a)} | " + ' | '.join(f"{ST[w][a]['pnl_crash']:+.2f} / {ST[w][a]['pnl_other']:+.2f} / {ST[w][a]['pnl_crash']+ST[w][a]['pnl_other']-ST[w][a]['carry']:+.2f}; own {ST[w][a]['sq_arith']:.0f} / {ST[w][a]['sq_comp']:.0f}" for w in WN) + ' |\n')
log('\ndone')
