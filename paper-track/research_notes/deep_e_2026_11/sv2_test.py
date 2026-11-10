"""Short-vol variants A-F (research only). Run from /home/user/Robinhood-stock. Base includes the deep-E QQQ leg."""
import csv, os, sys
import numpy as np
HERE = '/home/user/Robinhood-stock/paper-track'; sys.path.insert(0, HERE)
import monte_carlo as MC, state as S, vol_curve as VC
SC = '/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad'
MC.DATA = SC + '/data_ext'
S.A_BASE_FROM_SESSION = ('2026-11-06', (0.40, 0.60))
LIVE = dict(MC.LIVE, name='live', a_base=(0.40, 0.60), vol='max10_30')
OUT = open(SC + '/hv/sv2_test.log', 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); OUT.write(s + '\n'); OUT.flush()
NOTES = HERE + '/research_notes/vixm_followups_2026_11'; DATA = SC + '/hv/sv_data'
p = MC.load_panel('proxy'); dates = p['dates']
sig = MC.signals((100*np.cumprod(1+p['qqq']))[None], (100*np.cumprod(1+p['ew']))[None])
pr = MC.load_panel('real'); off = dates.index(pr['dates'][0])
sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items()}
rd = pr['dates']; N = len(rd); D = np.array(rd)
vix, vsrc = VC.history('VIX'); vix3m, _ = VC.history('VIX3M')
vol30 = {d: (None if np.isnan(v) else float(v)) for d, v in zip(rd, sr['vol'][0])}
VX = S.vixm_series(rd, vix, vix3m, vol30)
eff_r = MC._eff(sr, LIVE)[0]
allowed = np.array([bool(VX.get(d, {}).get('allowed')) for d in rd])
allowed &= ~((eff_r == 3) & ~sr['gate'][0].astype(bool) & (sr['zone'][0] == 2))
VIX = np.array([vix.get(d, np.nan) for d in rd]); V3 = np.array([vix3m.get(d, np.nan) for d in rd])
RATIO = VIX / V3
def rets(path):
    px = {r['d']: float(r['c']) for r in csv.DictReader(open(path))}
    r = MC._rets(px, rd); r[0] = 0.0; return r
vixm_r = rets(NOTES + '/vixm_rh_daily.csv'); vixy_r = rets(NOTES + '/vixy_daily.csv')
svxy_r = rets(DATA + '/svxy_daily.csv'); svix_r = rets(DATA + '/svix_daily.csv')
svix_first = next(i for i, d in enumerate(rd) if d >= '2022-03-31')
svix_avail = np.arange(N) >= svix_first
svxy_half = D >= '2018-02-28'
def syn(fee=0.0135): return np.maximum(-vixy_r - fee/252, -0.99)
SYN = syn(); SYNM = np.maximum(-vixm_r - 0.0135/252, -0.99)   # -1x VIXM daily, same 1.35% fee+borrow
def prof(r):
    nav = np.cumprod(1+r); dd = nav/np.maximum.accumulate(nav)-1
    return nav[-1]**(252/len(r))-1, r.mean()*252/(r.std(ddof=1)*252**.5), dd.min()
CUT = '2021-03-01'
g200 = np.nan_to_num(sr['gaps'][200][0])
DEEPE = ((eff_r == 4) & (g200 <= -0.05)).astype(float) * 0.5   # live deep-E QQQ leg: 50% of cash leg

cashw = {}
def runner(extra, d0='2015-11-02'):
    """extra: list of (returns, share-of-cash arrays). Deep-E QQQ leg is always first (after VIXM sleeve)."""
    s0 = next(i for i, d in enumerate(rd) if d >= d0)
    w5 = MC.target_weights(sr, LIVE); key = MC.regime_key(sr, LIVE)
    cash = w5[0, :, 4].copy(); cashw['cash'] = cash
    legs = [pr['core'], pr['tqqq'], pr['qld'], pr['xlu']]; W = [w5[0, :, i] for i in range(4)]
    v = np.where(allowed, cash*S.VIXM_CASH_SHARE, 0.0); legs.append(vixm_r); W.append(v); key = key + allowed[None].astype(int)*100000
    used = v; xs = []
    for j, (rr, sh) in enumerate([(pr['qqq'], DEEPE)] + list(extra)):
        sh = np.clip(np.nan_to_num(sh), 0, 1)
        x = np.minimum(cash*sh, cash - used); used = used + x; xs.append(x)
        legs.append(rr); W.append(x); key = key + (sh[None] > 0).astype(int) * (10**(6+j))
    legs.append(pr['cash']); W.append(cash - used)
    w = np.stack(W, -1)[None]; L = np.stack(legs, -1)[None]
    r, tr = MC.run_strategy(w, key, L, s0)
    return r[0], xs[1:] if extra else []
s0 = next(i for i, d in enumerate(rd) if d >= '2015-11-02')
BASE_R, _ = runner([])
DSA = D[s0+1:]
REM = ~((DSA >= '2020-03-01') & (DSA <= '2021-12-31'))
I1 = DSA < CUT
cb, sb, mb = prof(BASE_R); cbr = prof(BASE_R[REM])[0]
def lagm(on, lag=1): return np.concatenate([np.zeros(lag, bool), on[:-lag]]) if lag else on

# ---------------- rules: return on[t] (decided at close t, earns return t+1)
def rmax(x, w):
    out = np.full(len(x), np.nan)
    for t in range(len(x)):
        seg = x[max(0, t-w+1):t+1]
        if np.isfinite(seg).any(): out[t] = np.nanmax(seg)
    return out
_mx = {}
def mx(w):
    if w not in _mx: _mx[w] = rmax(VIX, w)
    return _mx[w]
def rule_orig(lo=20):  return (RATIO < 1) & (VIX >= lo)
def rule_A(d=0.2, w=20):
    m = mx(w); ok = np.isfinite(RATIO) & np.isfinite(m)
    ent = ok & (RATIO < 1) & (VIX <= m*(1-d)); on = np.zeros(N, bool); st = False
    for t in range(N):
        if st and (not ok[t] or RATIO[t] >= 1 or VIX[t] >= m[t]): st = False
        if not st and ent[t]: st = True
        on[t] = st
    return on
def rule_B(th=1.10):  return np.isfinite(RATIO) & (1/RATIO >= th)
def rule_C(lv=15):    return (RATIO < 1) & (VIX < lv)
def rule_E2(h=10):
    """armed after allowed True->False with VIX>VIX3M; start when RATIO<1; hold <= h sessions (cut if RATIO>=1 or VIXM latch back on)."""
    on = np.zeros(N, bool); armed = False; st = False; cnt = 0
    for t in range(1, N):
        if allowed[t-1] and not allowed[t] and RATIO[t] > 1: armed = True; st = False
        if allowed[t]: armed = False; st = False
        if st:
            cnt += 1
            if cnt > h or RATIO[t] >= 1: st = False
        if not st and armed and RATIO[t] < 1: st = True; armed = False; cnt = 1
        on[t] = st
    return on
FILT = np.isin(eff_r, (0, 1, 2))

def build(rule):
    """rule = (name, fn, args, leg, filt). returns on (not lagged) and leg returns"""
    nm, fn, args, leg, filt = rule
    on = fn(*args) & ~allowed
    if filt: on = on & FILT
    return on
LEG = {'syn': lambda: SYN, 'vixm': lambda: SYNM,
       'svxy': lambda: svxy_r, 'svix': lambda: np.where(svix_avail, svix_r, SYN)}
def legshare(leg, on, sh):
    if leg == 'svxy': return svxy_r, on*sh*np.where(svxy_half, 2.0, 1.0)
    return LEG[leg](), on*sh
def lagscore(lab, rule, sh, lag=0):
    on = lagm(build(rule), lag); r, xs = runner([legshare(rule[3], on, sh)]); return r, xs[0], on
def worst_on(rule, on):
    lr = LEG[rule[3]]() if rule[3] != 'svxy' else svxy_r
    v = [lr[t+1] for t in range(s0, N-1) if on[t]]
    return (min(v) if v else 0.0)
cache = {}
def metrics(rule, sh):
    k = (rule[0], rule[2], rule[3], rule[4], sh)
    if k in cache: return cache[k]
    r, xs, on = lagscore('', rule, sh); r1, _, _ = lagscore('', rule, sh, 1)
    c, s, m = prof(r); sa, sb2 = prof(r[I1])[1], prof(r[~I1])[1]
    cr = prof(r[REM])[0]; c1 = prof(r1)[0]; cr1 = prof(r1[REM])[0]
    d = dict(c=c, dc=c-cb, s=s, m=m, sh1=sa, sh2=sb2, rc=cr, drc=cr-cbr, lag=c1-cb, lagr=cr1-cbr, worst=worst_on(rule, on),
             days=int(on[s0:N-1].sum()), r=r, xs=xs, on=on)
    cache[k] = d; return d
H = f"  {'variant':<50}{'sz':>4}{'CAGR':>7}{'vs b':>7}{'Shrp':>6}{'maxDD':>7}{'Sh1':>6}{'Sh2':>6}{'exW d':>7}{'lag d':>7}{'lagEx d':>8}{'worst':>7}{'days':>6}"
def row(rule, sh, lab=None):
    m = metrics(rule, sh)
    log(f"  {(lab or rule[0]):<50}{sh*100:3.0f}%{m['c']*100:6.1f}%{m['dc']*100:+7.2f}{m['s']:6.3f}{m['m']*100:6.1f}%{m['sh1']:6.2f}{m['sh2']:6.2f}{m['drc']*100:+7.2f}{m['lag']*100:+7.2f}{m['lagr']*100:+8.2f}{m['worst']*100:6.1f}%{m['days']:6d}")
    return m

log('='*160)
log(f"Short-vol variants A-F -- live design incl. deep-E QQQ leg, 2bp; VIX {vsrc}; real panel {rd[0]}..{rd[-1]}; scored from 2015-11-02")
log(f"BASE (live + VIXM sleeve + deep-E QQQ): CAGR {cb*100:.2f}%  Sharpe {sb:.3f}  maxDD {mb*100:.1f}%  Sharpe 1st/2nd half {prof(BASE_R[I1])[1]:.3f}/{prof(BASE_R[~I1])[1]:.3f}  CAGR ex 2020-03..2021-12 {cbr*100:.2f}%")
log("columns: vs b = CAGR minus base (pts); exW d = (CAGR ex 2020-03-01..2021-12-31) minus base on same days; lag d / lagEx d = same two deltas with 1-session lag;")
log("worst = worst daily return of the leg itself on days it is held (synthetic -1x VIXY 1.35%/yr, or -1x VIXM 1.35%/yr for D); days = sessions held; F = only when QQQ effective state is A/B/C")
log(f"days: scored sessions {N-1-s0}; VIXM sleeve allowed days {allowed[s0:].sum()}; A/B/C sessions {FILT[s0:N-1].sum()}")
log('='*160)

RULES = []
RULES.append(('orig VIX>=20 & VIX<VIX3M (ref)', rule_orig, (20,), 'syn'))
for d in (0.2, 0.3): RULES.append((f'A post-spike -{d*100:.0f}% off 20d high & <VIX3M', rule_A, (d, 20), 'syn'))
for th in (1.10, 1.15, 1.20): RULES.append((f'B V3/VIX>={th:.2f}', rule_B, (th,), 'syn'))
for lv in (15, 13): RULES.append((f'C calm VIX<{lv} & <VIX3M', rule_C, (lv,), 'syn'))
RULES.append(('D -1x VIXM orig VIX>=20 & <VIX3M', rule_orig, (20,), 'vixm'))
for d in (0.2, 0.3): RULES.append((f'D -1x VIXM A -{d*100:.0f}% off 20d high', rule_A, (d, 20), 'vixm'))
for h in (10, 20): RULES.append((f'E after latch off, <VIX3M, hold<={h}', rule_E2, (h,), 'syn'))
SIZES = (0.05, 0.10, 0.25)
allrows = []
for filt in (False, True):
    log(f"\n[{'F: risk-on only (state A/B/C)' if filt else 'no trend filter'}]"); log(H)
    for nm, fn, args, leg in RULES:
        rule = (nm, fn, args, leg, filt)
        for sh in SIZES:
            m = row(rule, sh, nm + (' +F' if filt else '')); allrows.append((rule, sh, m))
        log('')
    if not filt:
        pass

# ---------- ranking by ex-window gain: best size per distinct rule
log('\n[RANKING] best by ex-window gain (exW d) per distinct rule+filter (any size), top 12; star = survives 1-session lag with both full and ex-window gain > 0')
best = {}
for rule, sh, m in allrows:
    k = (rule[0], rule[4])
    if k not in best or m['drc'] > best[k][2]['drc']: best[k] = (rule, sh, m)
top = sorted(best.values(), key=lambda x: -x[2]['drc'])
log(H)
for rule, sh, m in top[:12]:
    row(rule, sh, rule[0] + (' +F' if rule[4] else '') + (' *' if m['lag'] > 0 and m['lagr'] > 0 else ''))
# same ranking restricted to size 10 (comparable)
log('\n[RANKING at 10% size]'); log(H)
for rule, sh, m in sorted([x for x in allrows if x[1] == 0.10], key=lambda x: -x[2]['drc'])[:8]:
    row(rule, sh, rule[0] + (' +F' if rule[4] else '') + (' *' if m['lag'] > 0 and m['lagr'] > 0 else ''))
TOP3 = [x for x in top[:3]]
log('\nTOP 3 chosen for deep tests: ' + '; '.join(f"{r[0]}{' +F' if r[4] else ''} @ {sh*100:.0f}%" for r, sh, m in TOP3))
# also the best-surviving-lag variant for completeness
surv = sorted([x for x in best.values() if x[2]['lag'] > 0 and x[2]['lagr'] > 0], key=lambda x: -x[2]['lagr'])
log('variants surviving lag (full and ex-window both > 0), best size per rule, by lag-ex gain: ' + ('; '.join(f"{r[0]}{' +F' if r[4] else ''} @ {sh*100:.0f}% lagEx {m['lagr']*100:+.2f}" for r, sh, m in surv[:8]) or 'NONE'))

# ---------- real SVXY / SVIX confirmation (rules on VIXY-type legs only)
log('\n[REAL INSTRUMENTS] top-3 with real SVXY (2x share after 2018-02-28, same share before) and SVIX hybrid (real from 2022-03-31, synthetic before)'); log(H)
for rule, sh, m in TOP3:
    if rule[3] != 'syn': log(f"  ({rule[0]} is a VIXM-short: no real instrument)"); continue
    for leg in ('syn', 'svxy', 'svix'):
        rl = (rule[0] + f' [{leg}]', rule[1], rule[2], leg, rule[4]); row(rl, sh)
log("  (also window 2022-04..: leg contribution CAGR pts vs base, syn / SVIX / SVXY2x)")
w = DSA >= '2022-04-01'; cbw = prof(BASE_R[w])[0]
for rule, sh, m in TOP3:
    if rule[3] != 'syn': continue
    out = []
    for leg in ('syn', 'svix', 'svxy'):
        rl = (rule[0], rule[1], rule[2], leg, rule[4]); r, _, _ = lagscore('', rl, sh); out.append(f"{leg} {(prof(r[w])[0]-cbw)*100:+.2f}")
    log(f"  {rule[0]}{' +F' if rule[4] else ''} {sh*100:.0f}%: " + '  '.join(out) + f"  (base CAGR since 2022-04 {cbw*100:.1f}%)")

# ---------- bootstrap
def boot(rv, rb, B=3000, L=20, seed=7):
    rng = np.random.default_rng(seed); n = len(rv); nb = -(-n//L); wins = 0; dsh = []
    for _ in range(B):
        st = rng.integers(0, n-L+1, nb); idx = (st[:, None] + np.arange(L)).ravel()[:n]
        a = rv[idx]; b = rb[idx]
        sa = a.mean()/a.std(ddof=1); sb_ = b.mean()/b.std(ddof=1)
        dsh.append((sa-sb_)*252**.5); wins += sa <= sb_
    dsh = np.array(dsh); return wins/B, np.percentile(dsh, [5, 50, 95])
log('\n[BOOTSTRAP] 20-day blocks, 3000 draws, paired with base: P(Sharpe not better than base); delta-Sharpe 5/50/95')
for rule, sh, m in TOP3:
    pv, q = boot(m['r'], BASE_R); pv2, q2 = boot(m['r'][REM], BASE_R[REM])
    ml = metrics(rule, sh)
    r1, _, _ = lagscore('', rule, sh, 1); pv3, q3 = boot(r1, BASE_R)
    log(f"  {rule[0]}{' +F' if rule[4] else ''} {sh*100:.0f}%: full P={pv*100:5.1f}% dSh {q[0]:+.3f}/{q[1]:+.3f}/{q[2]:+.3f} | ex-window P={pv2*100:5.1f}% dSh {q2[0]:+.3f}/{q2[1]:+.3f}/{q2[2]:+.3f} | lag1 full P={pv3*100:5.1f}%")

# ---------- neighbour grid
def neigh(rule):
    nm, fn, args, leg, filt = rule
    if fn is rule_A: return [(f'd={d:.2f} w={w_}', (nm, fn, (d, w_), leg, filt)) for w_ in (10, 20, 30) for d in (0.15, 0.20, 0.25, 0.30, 0.35)]
    if fn is rule_B: return [(f'th={t:.2f}', (nm, fn, (t,), leg, filt)) for t in (1.05, 1.08, 1.10, 1.12, 1.15, 1.18, 1.20, 1.25)]
    if fn is rule_C: return [(f'VIX<{v}', (nm, fn, (v,), leg, filt)) for v in (11, 12, 13, 14, 15, 16, 17, 18)]
    if fn is rule_orig: return [(f'VIX>={v}', (nm, fn, (v,), leg, filt)) for v in (18, 20, 22, 25, 28, 30)]
    if fn is rule_E2: return [(f'hold<={h}', (nm, fn, (h,), leg, filt)) for h in (5, 10, 15, 20, 30, 40)]
log('\n[NEIGHBOUR GRID] cells: CAGR vs base / ex-window delta / lag-1 ex-window delta (pts) per size 5/10/25%')
for rule, sh, m in TOP3:
    log(f"\n  {rule[0]}{' +F' if rule[4] else ''}")
    log(f"    {'param':<16}" + ''.join(f"{'size '+str(int(s*100))+'%':>34}" for s in SIZES))
    for lab, rl in neigh(rule):
        cells = []
        for s in SIZES:
            mm = metrics(rl, s); cells.append(f"{mm['dc']*100:+6.2f} / {mm['drc']*100:+6.2f} / {mm['lagr']*100:+6.2f}   ")
        log(f"    {lab:<16}" + ''.join(f"{c:>34}" for c in cells))

# ---------- shock cost
log('\n[SHOCK] Feb-2018-style: leg weight x -90%, in pts of book. weight = share of cash leg actually held (capped by cash left after VIXM sleeve and deep-E QQQ)')
for rule, sh, m in TOP3:
    x = m['xs']; on = m['on']; ix = np.arange(N) >= s0
    xo = x[on & ix] if (on & ix).any() else np.array([0.0])
    # 20 sessions of hold at -1x worst: also whole-spell worst compounded loss of the leg
    log(f"  {rule[0]}{' +F' if rule[4] else ''} {sh*100:.0f}%: max leg wt {xo.max()*100:.1f}% of book -> {xo.max()*-0.9*100:.2f}% ; mean wt when on {xo.mean()*100:.1f}% -> {xo.mean()*-0.9*100:.2f}% ; worst leg day while on {m['worst']*100:.1f}% ; base-case backtest worst book day {m['r'].min()*100:.2f}% vs base {BASE_R.min()*100:.2f}%; maxDD {m['m']*100:.1f}% vs {mb*100:.1f}%")
    for s_ in (0.05, 0.10, 0.25):
        mm = metrics(rule, s_); xx = mm['xs'][mm['on'] & ix]
        log(f"      size {s_*100:.0f}%: max wt {xx.max()*100:.1f}% (shock {xx.max()*-90:.2f}% of book)" if len(xx) else f"      size {s_*100:.0f}%: never on")

# ---------- extra: lag-1 bootstrap (full and ex-window) for the top 3 plus the two A -30% variants at 25% (no-lag and lag)
log('\n[EXTRA BOOTSTRAP] as above plus lag-1 ex-window; added: A -30% with and without F at 25% and 10%')
ex_list = [(r, sh) for r, sh, m in TOP3]
for filt in (False, True):
    for sh in (0.10, 0.25): ex_list.append((('A post-spike -30% off 20d high & <VIX3M', rule_A, (0.3, 20), 'syn', filt), sh))
for rule, sh in ex_list:
    m = metrics(rule, sh); r1, _, _ = lagscore('', rule, sh, 1)
    pv, q = boot(m['r'], BASE_R); pv2, q2 = boot(m['r'][REM], BASE_R[REM]); pv3, q3 = boot(r1, BASE_R); pv4, q4 = boot(r1[REM], BASE_R[REM])
    log(f"  {rule[0]}{' +F' if rule[4] else ''} {sh*100:.0f}%: full P={pv*100:5.1f}% | ex-window P={pv2*100:5.1f}% | lag1 full P={pv3*100:5.1f}% dSh {q3[0]:+.3f}/{q3[1]:+.3f}/{q3[2]:+.3f} | lag1 ex-window P={pv4*100:5.1f}% dSh {q4[0]:+.3f}/{q4[1]:+.3f}/{q4[2]:+.3f}")
log("\nDONE")
