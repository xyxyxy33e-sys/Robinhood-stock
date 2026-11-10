"""Short-vol leg (idea #1) deep-dive. Research only. Run from /home/user/Robinhood-stock."""
import csv, os, sys
import numpy as np
HERE = '/home/user/Robinhood-stock/paper-track'; sys.path.insert(0, HERE)
import monte_carlo as MC, state as S, vol_curve as VC
SC = '/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad'
MC.DATA = SC + '/data_ext'
S.A_BASE_FROM_SESSION = ('2026-11-06', (0.40, 0.60))
LIVE = dict(MC.LIVE, name='live', a_base=(0.40, 0.60), vol='max10_30')
OUT = open(SC + '/hv/sv_test.log', 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); OUT.write(s + '\n'); OUT.flush()
NOTES = HERE + '/research_notes/vixm_followups_2026_11'
DATA = SC + '/hv/sv_data'
p = MC.load_panel('proxy'); dates = p['dates']
sig = MC.signals((100*np.cumprod(1+p['qqq']))[None], (100*np.cumprod(1+p['ew']))[None])
pr = MC.load_panel('real'); off = dates.index(pr['dates'][0])
sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items()}
rd = pr['dates']; N = len(rd)
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
D = np.array(rd)
svix_first = next(i for i, d in enumerate(rd) if d >= '2022-03-31')   # first return on a real SVIX pair of closes
svix_avail = np.arange(N) >= svix_first
svxy_half = D >= '2018-02-28'                                          # -0.5x from 2018-02-28 on
def syn(fee): return np.maximum(-vixy_r - fee/252, -0.99)

def prof(r):
    nav = np.cumprod(1+r); dd = nav/np.maximum.accumulate(nav)-1
    return nav[-1]**(252/len(r))-1, r.mean()*252/(r.std(ddof=1)*252**.5), dd.min()

cashw_holder = {}
def runner(extra, d0='2015-11-02'):
    """extra: list of (leg returns, share array of the cash leg). Same mechanics as hv_test.runner (real panel + VIXM sleeve)."""
    ds = rd; s0 = next(i for i, d in enumerate(ds) if d >= d0)
    w5 = MC.target_weights(sr, LIVE); key = MC.regime_key(sr, LIVE)
    cash = w5[0, :, 4].copy(); cashw_holder['cash'] = cash
    legs = [pr['core'], pr['tqqq'], pr['qld'], pr['xlu']]; W = [w5[0, :, i] for i in range(4)]
    v = np.where(allowed, cash*S.VIXM_CASH_SHARE, 0.0); legs.append(vixm_r); W.append(v); key = key + allowed[None].astype(int)*100000
    used = v; xs = []
    for j, (rr, sh) in enumerate(extra):
        sh = np.clip(np.nan_to_num(sh), 0, 1)
        x = np.minimum(cash*sh, cash - used); used = used + x; xs.append(x)
        legs.append(rr); W.append(x); key = key + (sh[None] > 0).astype(int) * (10**(6+j))
    legs.append(pr['cash']); W.append(cash - used)
    w = np.stack(W, -1)[None]; L = np.stack(legs, -1)[None]
    r, tr = MC.run_strategy(w, key, L, s0)
    return r[0], tr[0]/((len(ds)-1-s0)/252), ds[s0+1:], xs

def on_mask(lo, thr=1.0, exit_rise=None, lag=0):
    """on[t] = hold the leg over t -> t+1 (decided at close t - lag)."""
    cond = (RATIO < thr) & (VIX >= lo) & ~allowed
    if exit_rise is None: on = cond.copy()
    else:
        on = np.zeros(N, bool); st = False; ent = 0.0; lock = False
        for t in range(N):
            if not cond[t]: lock = False
            if st:
                if (not cond[t]) or VIX[t] >= ent*(1+exit_rise): st = False; lock = cond[t]
            if not st and cond[t] and not lock: st = True; ent = VIX[t]
            on[t] = st
    if lag: on = np.concatenate([np.zeros(lag, bool), on[:-lag]])
    return on

# ---- leg builders: return (leg returns, share array); share is of the cash leg
def leg_syn(fee, on, sh): return (syn(fee), on*sh)
def leg_svxy(on, sh, match=False):
    mult = np.where(svxy_half, 2.0, 1.0) if match else 1.0
    return (svxy_r, on*sh*mult)
def leg_svix_hybrid(on, sh, fee=0.0135):
    r = np.where(svix_avail, svix_r, syn(fee)); return (r, on*sh)

BASE_R, BASE_T, DS, _ = runner([])
DS = list(DS); DSA = np.array(DS)
REM = ~((DSA >= '2020-03-01') & (DSA <= '2021-12-31'))
def spells(on):
    out = []; i = 0
    while i < N:
        if on[i]:
            j = i
            while j+1 < N and on[j+1]: j += 1
            out.append((i, j)); i = j+1
        else: i += 1
    return out
# BASE_R[k] is return from session s0+k+1 on DS = rd[s0+1:]; on[t] affects the return at rd[t+1] -> BASE_R index (t+1)-(s0+1)=t-s0
s0 = next(i for i, d in enumerate(rd) if d >= '2015-11-02')

H = f"  {'variant':<64}{'CAGR':>7}{'vs base':>8}{'Sharpe':>7}{'maxDD':>8}{'rem.CAGR':>9}{'rem.d':>7}{'tr/yr':>6}"
def line(lab, r, t):
    c, s, m = prof(r); cb = prof(BASE_R)[0]
    cr = prof(r[REM])[0]; crb = prof(BASE_R[REM])[0]
    log(f"  {lab:<64}{c*100:6.1f}%{(c-cb)*100:+8.2f}{s:7.3f}{m*100:7.1f}%{cr*100:8.1f}%{(cr-crb)*100:+7.2f}{t:6.0f}")
def table(title, variants):
    log(f"\n{title}"); log(H)
    for lab, ex in variants:
        r, t, _, _ = runner(ex); line(lab, r, t)

log('='*140); log(f"Short-vol leg deep-dive -- live design, 2bp; VIX source {vsrc}; real panel {rd[0]}..{rd[-1]}; scored from 2015-11-02")
log("'rem.' columns = CAGR scored on the days left after removing 2020-03-01..2021-12-31 (concatenated); rem.d = variant minus base on that subset")
log('='*140)

# ================= 1. data / tracking
log('\n[1] DATA SOURCES')
for s in ('svxy', 'svix'):
    n = sum(1 for _ in open(f'{DATA}/{s}_daily.csv'))-1
    log(f"  {s.upper()}: Robinhood get_equity_historicals (day, regular, split-adj), interpolated bars dropped, {n} real closes; raw in sv_data/{s}_raw.json")
log("  VIXY closes/VIXM/VIX/VIX3M: existing repo notes + vol_curve (as in hv_test.py). No source failed.")
def trk(a, b, mask, lab):
    a = a[mask]; b = b[mask]; c = np.corrcoef(a, b)[0, 1]; te = (a-b).std(ddof=1)*252**.5
    log(f"  {lab:<58} n={mask.sum():5d} corr={c:6.3f} TE={te*100:5.1f}%/yr  drift(ann mean diff a-b)={(a-b).mean()*252*100:+6.2f}%  CAGR a={((np.prod(1+a))**(252/len(a))-1)*100:7.1f}% b={((np.prod(1+b))**(252/len(b))-1)*100:7.1f}%")
m_all = np.arange(N) > 0
trk(syn(0.0135), svix_r, svix_avail, 'syn -1x VIXY (1.35% fee) vs SVIX, overlap')
trk(syn(0.0095), svix_r, svix_avail, 'syn -1x VIXY (0.95% fee) vs SVIX, overlap')
trk(0.5*syn(0.0135), svxy_r, svix_avail, 'syn 0.5x of that vs SVXY, SVIX overlap period')
trk(2*svxy_r, svix_r, svix_avail & svxy_half, '2 x SVXY vs SVIX, overlap')
trk(syn(0.0135), 2*svxy_r, svix_avail & svxy_half, 'syn -1x (1.35%) vs 2 x SVXY, SVIX overlap')
pre = (np.arange(N) > 0) & ~svxy_half
trk(syn(0.0135), svxy_r, pre, 'syn -1x (1.35%) vs SVXY, pre 2018-02-28 (-1x)')
trk(syn(0.0135), 2*svxy_r, (np.arange(N) > 0) & svxy_half, 'syn -1x (1.35%) vs 2 x SVXY, 2018-02-28..end')
mm = svix_avail & svxy_half
for nm, y, x in (('SVIX on 2xSVXY', svix_r, 2*svxy_r), ('SVIX on syn -1x', svix_r, syn(0.0135)), ('2xSVXY on syn -1x', 2*svxy_r, syn(0.0135))):
    bt, a0 = np.polyfit(x[mm], y[mm], 1)
    log(f"  regression {nm} (SVIX overlap): slope {bt:.3f}, intercept {a0*252*100:+.2f}%/yr")
log(f"  SVXY worst day {svxy_r.min()*100:.1f}% on {rd[int(svxy_r.argmin())]}; SVIX worst day {svix_r[svix_avail].min()*100:.1f}% on {rd[int(np.where(svix_avail, svix_r, 0).argmin())]}; syn -1x(1.35%) worst day {syn(0.0135).min()*100:.1f}% on {rd[int(syn(0.0135).argmin())]}")
log("  worst 5 syn days: " + ', '.join(f"{rd[i]} {syn(0.0135)[i]*100:.0f}%" for i in np.argsort(syn(0.0135))[:5]))

# ================= 2. real-instrument variants
log('\n[2] REAL-INSTRUMENT VARIANTS (rule: VIX>=lo & VIX/VIX3M<1 & VIXM sleeve off; share of CASH leg)')
v = [('base (live, VIXM sleeve)', [])]
for lo in (20, 25):
    for sh in (0.10, 0.25):
        on = on_mask(lo)
        v.append((f"VIX>={lo} {sh*100:.0f}% | (0) syn -1x 0.95% (hv_test)", [leg_syn(0.0095, on, sh)]))
        v.append((f"VIX>={lo} {sh*100:.0f}% | (a) syn -1x 1.35%", [leg_syn(0.0135, on, sh)]))
        v.append((f"VIX>={lo} {sh*100:.0f}% | (b1) real SVXY same share", [leg_svxy(on, sh)]))
        v.append((f"VIX>={lo} {sh*100:.0f}% | (b2) real SVXY 2x share after 2018-02-28", [leg_svxy(on, sh, True)]))
        v.append((f"VIX>={lo} {sh*100:.0f}% | (c) SVIX from 2022-03-31, syn before", [leg_svix_hybrid(on, sh)]))
table('Real vs synthetic', v)
# SVIX-only window: score variants only 2022-03-31..
log("\n  SVIX-only window (2022-03-31..): contribution of the leg, synthetic vs SVIX, CAGR pts vs base over that window")
w = DSA >= '2022-04-01'
for lo, sh in ((20, 0.10), (25, 0.10), (25, 0.25)):
    on = on_mask(lo)
    rb = BASE_R[w]; cb = prof(rb)[0]
    out = []
    for lab, ex in (('syn1.35', leg_syn(0.0135, on, sh)), ('SVIX', leg_svix_hybrid(on, sh)), ('SVXY2x', leg_svxy(on, sh, True))):
        r, _, _, _ = runner([ex]); out.append(f"{lab} {(prof(r[w])[0]-cb)*100:+.2f}")
    log(f"  VIX>={lo} {sh*100:.0f}%: " + '  '.join(out) + f"   (base CAGR {cb*100:.1f}%)")

# ================= 2b. spells
def spell_table(lo, sh, thr=1.0):
    on = on_mask(lo, thr); ex = leg_syn(0.0135, on, sh)
    r, _, _, xs = runner([ex]); cash = cashw_holder['cash']
    lr = ex[0]
    log(f"\n[2b] PER-SPELL TABLE: syn -1x 1.35%, VIX>={lo}, ratio<{thr}, {sh*100:.0f}% of cash. gain = sum of daily log(1+r_var)-log(1+r_base) over spell days, in pts of book; leg ret = compounded leg over spell")
    log(f"  {'start':<11}{'len':>4}{'VIX@start':>10}{'gain pts':>9}{'leg ret':>9}{'avg leg wt':>11}")
    rows = []
    for a, b in spells(on):
        k0, k1 = a - s0, b - s0           # BASE_R indices of the returns earned by on[a..b]
        if k1 < 0 or k0 < 0: continue
        g = (np.log1p(r[k0:k1+1]) - np.log1p(BASE_R[k0:k1+1])).sum()*100
        lr_c = np.prod(1+lr[a+1:b+2])-1
        rows.append((rd[a], b-a+1, VIX[a], g, lr_c, np.mean(np.minimum(cash[a:b+1]*sh, cash[a:b+1]))))
    for x in rows: log(f"  {x[0]:<11}{x[1]:4d}{x[2]:10.1f}{x[3]:+9.2f}{x[4]*100:+8.1f}%{x[5]*100:10.1f}%")
    tot = sum(x[3] for x in rows); top = sorted((x[3] for x in rows), reverse=True)[:3]
    log(f"  spells {len(rows)}, total {tot:+.2f} pts (sum of log gains), top-3 spells {sum(top):+.2f} = {sum(top)/tot*100:.0f}% of total; positive spells {sum(1 for x in rows if x[3]>0)}, negative {sum(1 for x in rows if x[3]<0)}; days on {on[1:].sum()}")
    yrs = sorted(set(d[:4] for d in DS)); parts = []
    for y in yrs:
        m = np.array([d[:4] == y for d in DS])
        parts.append(f"{y} {(np.prod(1+r[m])-np.prod(1+BASE_R[m]))*100/1:+.1f}")
    log("  per-year return difference (pts of book, calendar-year compounded return, var - base): " + '  '.join(parts))
for lo, sh in ((20, 0.10), (25, 0.10), (25, 0.25)): spell_table(lo, sh)

# ================= 3. tail risk
log('\n[3] TAIL RISK (syn -1x 1.35%)')
def worst5(r): return min(np.prod(1+r[i:i+5])-1 for i in range(len(r)-5))
log(f"  base: worst day {BASE_R.min()*100:.2f}% ({DS[int(BASE_R.argmin())]}), worst 5-day {worst5(BASE_R)*100:.2f}%")
for lo, sh in ((20, 0.10), (25, 0.10), (25, 0.25)):
    on = on_mask(lo); ex = leg_syn(0.0135, on, sh)
    r, _, _, xs = runner([ex]); x = xs[0]
    log(f"  VIX>={lo} {sh*100:.0f}%: worst day {r.min()*100:.2f}% ({DS[int(r.argmin())]}), worst 5-day {worst5(r)*100:.2f}%; max leg weight {x.max()*100:.1f}% of book, mean when on {x[on].mean()*100:.1f}%")
    lost = [(rd[t+1], ex[0][t+1], x[t]) for t in range(N-1) if on[t] and ex[0][t+1] < -0.10 and t >= s0]
    log(f"    days leg lost >10% while on (decided prior close): {len(lost)}")
    for d, lr_, wt in lost: log(f"      {d}  leg {lr_*100:+.1f}%  leg wt {wt*100:.1f}% of book -> book {wt*lr_*100:+.2f} pts")
    for shock, nm in ((-0.34, 'VIXY +34% overnight, -1x leg'), (-0.90, 'XIV-style -90%')):
        log(f"    shock {nm}: on a day when on, book loss = leg weight x shock: at max weight {x.max()*shock*100:.2f}%, at mean on-day weight {x[on].mean()*shock*100:.2f}%")
log("  Feb-5-2018-type, per share of cash leg when the book is fully in cash (weight=share), -90% leg: " + ', '.join(f"{s*100:.0f}% -> {-0.9*s*100:.1f}% of book" for s in (0.05, 0.10, 0.15, 0.25, 0.5)))
log(f"  (max cash-leg weight in the live book while the rule is on, VIX>=25: {cashw_holder['cash'][on_mask(25)].max()*100:.0f}%)")
log("  8 worst syn days and whether rule was on at prior close (VIX>=20 / VIX>=25): " + ', '.join(f"{rd[i]} {syn(0.0135)[i]*100:.0f}% {'ON' if on_mask(20)[i-1] else 'off'}/{'ON' if on_mask(25)[i-1] else 'off'}" for i in np.argsort(syn(0.0135))[:8]))

# ================= 4. timing
v = [('base', [])]
for lo, sh in ((20, 0.10), (25, 0.10), (25, 0.25)):
    for lab, kw in (('as-is', {}), ('1-session lag', dict(lag=1)), ('exit if VIX +20% vs entry', dict(exit_rise=0.20)), ('exit if ratio>=0.95 (enter <0.95)', dict(thr=0.95)),
                    ('lag1 + ratio 0.95', dict(lag=1, thr=0.95))):
        v.append((f"VIX>={lo} {sh*100:.0f}% {lab}", [leg_syn(0.0135, on_mask(lo, **kw), sh)]))
table('[4] TIMING / EXIT RULES (syn -1x 1.35%)', v)
v = [('base', [])]
for lo, sh in ((20, 0.10), (25, 0.10), (25, 0.25)):
    for lab, kw in (('as-is', {}), ('1-session lag', dict(lag=1))):
        v.append((f"VIX>={lo} {sh*100:.0f}% {lab} SVXY 2x share", [leg_svxy(on_mask(lo, **kw), sh, True)]))
        v.append((f"VIX>={lo} {sh*100:.0f}% {lab} SVIX hybrid", [leg_svix_hybrid(on_mask(lo, **kw), sh)]))
table('[4b] LAG with real instruments', v)

# ================= 5. neighbours + bootstrap
v = [('base', [])]
for lo in (18, 20, 22, 25, 28, 30):
    for sh in (0.05, 0.10, 0.15, 0.25):
        v.append((f"VIX>={lo} {sh*100:.0f}% syn -1x 1.35%", [leg_syn(0.0135, on_mask(lo), sh)]))
table('[5a] NEIGHBOURING PARAMETERS (syn -1x 1.35%)', v)
v = [('base', [])]
for lo in (18, 20, 22, 25, 28, 30):
    for sh in (0.05, 0.10, 0.15, 0.25):
        v.append((f"VIX>={lo} {sh*100:.0f}% SVXY 2x share (real)", [leg_svxy(on_mask(lo), sh, True)]))
table('[5a2] NEIGHBOURING PARAMETERS (real SVXY, 2x share after Feb 2018)', v)

def boot(rv, rb, B=3000, L=20, seed=7):
    rng = np.random.default_rng(seed); n = len(rv); nb = -(-n//L); wins = 0; dsh = []
    for _ in range(B):
        st = rng.integers(0, n-L+1, nb); idx = (st[:, None] + np.arange(L)).ravel()[:n]
        a = rv[idx]; b = rb[idx]
        sa = a.mean()/a.std(ddof=1); sb = b.mean()/b.std(ddof=1)
        dsh.append((sa-sb)*252**.5); wins += sa <= sb
    dsh = np.array(dsh); return wins/B, np.percentile(dsh, [5, 50, 95])
log('\n[5b] BLOCK BOOTSTRAP (20-day blocks, 3000 draws, paired with base): P(Sharpe not better than base); delta-Sharpe 5/50/95 pct')
log('  note Sharpe = mean/sd annualised, no rf, as in the repo')
cands = [('VIX>=20 10%', 20, 0.10), ('VIX>=25 10%', 25, 0.10), ('VIX>=25 25%', 25, 0.25)]
for nm, lo, sh in cands:
    on = on_mask(lo)
    for lab, ex in (('syn -1x 1.35%', leg_syn(0.0135, on, sh)), ('SVXY 2x share', leg_svxy(on, sh, True)), ('SVIX hybrid', leg_svix_hybrid(on, sh))):
        r, _, _, _ = runner([ex]); pv, q = boot(r, BASE_R)
        pv2, q2 = boot(r[REM], BASE_R[REM])
        log(f"  {nm:<14}{lab:<16} full: P={pv*100:5.1f}%  dSh {q[0]:+.3f}/{q[1]:+.3f}/{q[2]:+.3f} | excl 2020-03..2021-12: P={pv2*100:5.1f}%  dSh {q2[0]:+.3f}/{q2[1]:+.3f}/{q2[2]:+.3f}")
log('\nDONE')
