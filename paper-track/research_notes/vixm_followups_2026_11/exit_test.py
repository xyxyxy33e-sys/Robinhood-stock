"""Owner 2026-11-04: would scaling the VIXM share (instead of a fixed 75% of the cash leg) help?
Live design (A 20/80 from 30 Oct, D ladder, D gate, vol target max10_30, VIXM off in ungated D2),
real ETFs 2015-11..2026-10, 2bp one-way. The latch/stress/fade decide WHEN (unchanged); each
variant only changes HOW MUCH of the cash leg is VIXM on allowed days. Research only."""
import csv, os, sys
import numpy as np
HERE = '/home/user/Robinhood-stock/paper-track'; sys.path.insert(0, HERE)
import monte_carlo as MC, state as S, vol_curve as VC
MC.DATA = '/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad/data_ext'
S.A_BASE_FROM_SESSION = ('2026-10-30', (0.20, 0.80))
LIVE = dict(MC.LIVE, name='live', a_base=(0.20, 0.80), vol='max10_30')
OUT = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exit_test.log'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); OUT.write(s + '\n'); OUT.flush()

p = MC.load_panel('proxy'); dates = p['dates']
sig = MC.signals((100*np.cumprod(1+p['qqq']))[None], (100*np.cumprod(1+p['ew']))[None])
pr = MC.load_panel('real'); off = dates.index(pr['dates'][0])
sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items()}
rd = pr['dates']
try:
    vix, vsrc = VC.history('VIX'); vix3m, _ = VC.history('VIX3M')
except Exception:
    f = lambda fn, c: {r['observation_date']: float(r[c]) for r in csv.DictReader(open(os.path.join(MC.DATA, fn))) if r[c] not in ('', '.')}
    vix, vix3m, vsrc = f('vixcls_full.csv', 'VIXCLS'), f('vxvcls.csv', 'VXVCLS'), 'FRED local'
vol30 = {d: (None if np.isnan(v) else float(v)) for d, v in zip(rd, sr['vol'][0])}
VX = S.vixm_series(rd, vix, vix3m, vol30)
allowed = np.array([bool(VX.get(d, {}).get('allowed')) for d in rd])
eff = MC._eff(sr, LIVE)[0]
allowed &= ~((eff == 3) & ~sr['gate'][0].astype(bool) & (sr['zone'][0] == 2))   # off in ungated D2
g = lambda k: np.array([VX.get(d, {}).get(k) or np.nan for d in rd], float)
VIX, RATIO, VOL = g('vix'), g('ratio'), g('vol')
HI = g('vix_high')
# days into the current allowed spell
age = np.zeros(len(rd)); 
for i in range(len(rd)):
    age[i] = (age[i-1] + 1) if (allowed[i] and i and allowed[i-1]) else (1 if allowed[i] else 0)
vm = {r['d']: float(r['c']) for r in csv.DictReader(open(os.path.join(MC.DATA, 'vixm_daily.csv')))}
vr = MC._rets(vm, rd); vr[0] = 0.0
w5 = MC.target_weights(sr, LIVE); key0 = MC.regime_key(sr, LIVE)
s0 = next(i for i, d in enumerate(rd) if d >= '2015-11-02'); days = rd[s0+1:]
L6 = np.stack([pr['core'], pr['tqqq'], pr['qld'], pr['xlu'], vr, pr['cash']], -1)[None]

ENTRY, EXITR, FADE = S.VIXM_ENTRY_VIX, S.VIXM_EXIT_RATIO, S.VIXM_FADE
vmc = np.array([vm.get(d, np.nan) for d in rd])
LIVEALLOWED = np.array([bool(VX.get(d, {}).get('allowed')) for d in rd])
def series(exit_ratio=EXITR, confirm_off=1, fade=FADE, partial=False, half_max=None, trail=None, tstop=None):
    """Replica of state.vixm_series with exit-rule variants. Returns VIXM fraction of the 75% sleeve (0, .5, 1)."""
    on = killed = half = False; hi = None; vhi = None; cnt = 0; hc = 0; bad = 0
    out = np.zeros(len(rd))
    for i, d in enumerate(rd):
        v, v3 = vix.get(d), vix3m.get(d)
        if v is None or v3 is None or v3 <= 0: continue
        ratio = v / v3
        was_full = on and not killed
        if not on and v < ENTRY and ratio <= EXITR: on, killed, hi, vhi, cnt, half, bad = True, False, None, None, 0, False, 0
        elif on:
            bad = bad + 1 if ratio > exit_ratio else 0
            if bad >= confirm_off:
                on = False; bad = 0
                st0 = (vol30.get(d) is not None and vol30[d] >= S.VIXM_MIN_VOL)
                if partial and was_full and st0: half, hc = True, 0
        rv = vol30.get(d)
        stress = rv is not None and rv >= S.VIXM_MIN_VOL
        if not stress: killed, hi, vhi, half, cnt = False, None, None, False, 0
        full = on and not killed and stress
        hlf = (not on) and half and not killed and stress
        if full or hlf:
            hi = v if hi is None else max(hi, v)
            m = vmc[i]
            if trail is not None and not np.isnan(m): vhi = m if vhi is None else max(vhi, m)
            cnt += 1
            if v <= hi * (1 - fade): killed, full, hlf = True, False, False
            elif trail is not None and not np.isnan(m) and m <= vhi * (1 - trail): killed, full, hlf = True, False, False
            elif tstop is not None and cnt > tstop: killed, full, hlf = True, False, False
            if hlf:
                hc += 1
                if half_max is not None and hc > half_max: half, hlf = False, False
        out[i] = 1.0 if full else (0.5 if hlf else 0.0)
    return out
assert ((series() > 0) == LIVEALLOWED).all() and set(np.unique(series())) <= {0.0, 1.0}, 'replica != state.vixm_series'
d2 = ((eff == 3) & ~sr['gate'][0].astype(bool) & (sr['zone'][0] == 2))
def run_sh(sh):
    sh = np.where(d2, 0.0, sh); share = 0.75 * sh
    v = w5[0, :, 4] * share
    w6 = np.concatenate([w5[..., :4], v[None, :, None], (w5[0, :, 4] - v)[None, :, None]], -1)
    key = key0 + (np.round(share * 1000).astype(np.int64) * 100000)[None]
    r, tr = MC.run_strategy(w6, key, L6, s0)
    a = sh[s0:] > 0
    return r[0], int(np.sum(a[1:] != a[:-1])), a, sh[s0:]
mid = days.index(next(d for d in days if d >= '2021-03-01'))
aug = np.array([d[:7] != '2024-08' for d in days])
yrs = (len(rd)-1-s0)/252
sharpe = lambda x: x.mean()*252/(x.std(ddof=1)*252**.5)
cagr = lambda x: np.prod(1+x)**(252/len(x))-1
log('='*124)
log(f"VIXM EXIT-rule variants -- live design, real ETFs {days[0]}..{days[-1]}, 2bp, VIXM 75% of cash (partial = 37.5%); entry unchanged")
log("  'on %' = share of sessions with any VIXM; flips = on/off changes (full<->half not counted)")
log('='*124)
log(f"  {'rule':<34}{'CAGR':>7}{'vs live':>8}{'Sharpe':>7}{'maxDD':>8}{'Sh 1st':>8}{'Sh 2nd':>8}{'exAug24':>9}{'on %':>6}{'flips':>6}")
VARS = [('live (ratio>1.00, fade 25%)', {})]
for x in (0.95, 0.98, 1.02, 1.05, 1.10): VARS.append((f'1. latch-off ratio > {x:.2f}', dict(exit_ratio=x)))
VARS.append(('2. latch-off after 2 closes >1.0', dict(confirm_off=2)))
VARS.append(('3. partial half until fade/stress', dict(partial=True)))
for n in (5, 10): VARS.append((f'3. partial half, max {n} sessions', dict(partial=True, half_max=n)))
for f in (0.15, 0.20, 0.30, 0.35): VARS.append((f'4. fade {int(f*100)}%', dict(fade=f)))
for t in (0.08, 0.12, 0.15): VARS.append((f'5. VIXM trail stop {int(t*100)}%', dict(trail=t)))
for n in (20, 40, 60): VARS.append((f'6. time stop {n} sessions', dict(tstop=n)))
R = {}; base = None
for lab, kw in VARS:
    sh = series(**kw); r, f, a, shd = run_sh(sh); R[lab] = (r, a, shd, sh)
    nav = np.cumprod(1+r); dd = (nav/np.maximum.accumulate(nav)-1).min(); c = cagr(r)
    if base is None: base = c
    ce = cagr(r[aug])
    log(f"  {lab:<34}{c*100:6.1f}%{(c-base)*100:+8.2f}{sharpe(r):7.3f}{dd*100:7.1f}%{sharpe(r[:mid]):8.3f}{sharpe(r[mid:]):8.3f}{ce*100:8.1f}%{a.mean()*100:5.1f}%{f:6d}")
lr = R[VARS[0][0]][0]
# bootstrap: 20-day blocks, 3000 draws, Sharpe difference vs live
rng = np.random.default_rng(7); n = len(lr); B = 20; nb = -(-n // B)
idx = [ (rng.integers(0, n-B+1, nb)[:, None] + np.arange(B)[None]).ravel()[:n] for _ in range(3000)]
best = sorted(VARS[1:], key=lambda v: -cagr(R[v[0]][0]))[:5]
log(''); log('Bootstrap: 20-day blocks, 3000 draws, paired, Sharpe(variant) - Sharpe(live); 5 best variants by CAGR')
for lab, _ in best:
    r = R[lab][0]
    d = np.array([sharpe(r[i]) - sharpe(lr[i]) for i in idx])
    log(f"  {lab:<34} obs dSharpe {sharpe(r)-sharpe(lr):+.4f}  boot mean {d.mean():+.4f}  5-95% [{np.percentile(d,5):+.4f}, {np.percentile(d,95):+.4f}]  P(not better than live) = {(d<=0).mean():.3f}")
# concentration for variants beating live by > 0.5 CAGR points
log(''); log('Concentration check (variants beating live CAGR by > 0.5 pt)')
la = R[VARS[0][0]][3][s0:] > 0
cnt_any = 0
for lab, _ in VARS[1:]:
    r, a, shd, sh = R[lab]
    dc = (cagr(r)-cagr(lr))*100
    if dc <= 0.5: continue
    cnt_any += 1
    ld = np.log1p(r) - np.log1p(lr)
    u = la | a; wins = []; j = 0
    while j < len(u):
        if u[j]:
            k2 = j
            while k2 < len(u) and u[k2]: k2 += 1
            wins.append((j, k2)); j = k2
        else: j += 1
    contrib = [(ld[x:y].sum(), days[x], days[y-1], y-x) for x, y in wins]
    tot = ld.sum(); inw = sum(c[0] for c in contrib)
    cagr_h = lambda x, y: (cagr(x)-cagr(y))*100
    log(f"  {lab}: CAGR vs live {dc:+.2f}; sum log-diff {tot:+.4f} (in spell windows {inw:+.4f}); windows(live-or-variant on)={len(wins)}, windows with +diff={sum(c[0]>0 for c in contrib)}, -diff={sum(c[0]<0 for c in contrib)}")
    log(f"    halves: CAGR diff 1st {cagr_h(r[:mid], lr[:mid]):+.2f}, 2nd {cagr_h(r[mid:], lr[mid:]):+.2f}; Sharpe diff 1st {sharpe(r[:mid])-sharpe(lr[:mid]):+.3f}, 2nd {sharpe(r[mid:])-sharpe(lr[mid:]):+.3f}")
    top = sorted(contrib, key=lambda c: -abs(c[0]))[:5]
    pos = sum(c[0] for c in contrib if c[0] > 0)
    for c in top: log(f"    spell {c[1]}..{c[2]} ({c[3]}d): log-diff {c[0]:+.4f}" + (f" ({c[0]/inw*100:.0f}% of in-window total)" if inw else ''))
    log(f"    top-5 by |contribution| sum {sum(c[0] for c in top):+.4f} vs window total {inw:+.4f}")
if not cnt_any: log('  none')
