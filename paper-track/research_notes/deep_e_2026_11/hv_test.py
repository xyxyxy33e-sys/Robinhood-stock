"""Owner 2026-11-10: ways to make money when volatility is high -- test #1 short vol after a spike,
#3 inverse QQQ (PSQ/SQQQ) in F, #4 equity in E. Live design (A 40/60, D ladder, D gate, vol target
max10_30, VIXM sleeve 75% / D2-off), 2bp. Real ETFs 2015-11.. and proxy 2001.. (no VIX ETFs on proxy).
Each variant moves part of the CASH leg (BOXX) into the tested leg on its days. Research only."""
import csv, os, sys
import numpy as np
HERE = '/home/user/Robinhood-stock/paper-track'; sys.path.insert(0, HERE)
import monte_carlo as MC, state as S, vol_curve as VC
MC.DATA = '/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad/data_ext'
S.A_BASE_FROM_SESSION = ('2026-11-06', (0.40, 0.60))
LIVE = dict(MC.LIVE, name='live', a_base=(0.40, 0.60), vol='max10_30')
OUT = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hv_test.log'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); OUT.write(s + '\n'); OUT.flush()
NOTES = '/home/user/Robinhood-stock/paper-track/research_notes/vixm_followups_2026_11'
INV_FEE = 0.0095 / 252                     # PSQ/SQQQ/SVIX-style expense ratio, daily

p = MC.load_panel('proxy'); dates = p['dates']
sig = MC.signals((100*np.cumprod(1+p['qqq']))[None], (100*np.cumprod(1+p['ew']))[None])
pr = MC.load_panel('real'); off = dates.index(pr['dates'][0])
sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items()}
rd = pr['dates']
vix, vsrc = VC.history('VIX'); vix3m, _ = VC.history('VIX3M')
vol30 = {d: (None if np.isnan(v) else float(v)) for d, v in zip(rd, sr['vol'][0])}
VX = S.vixm_series(rd, vix, vix3m, vol30)
eff_r = MC._eff(sr, LIVE)[0]
allowed = np.array([bool(VX.get(d, {}).get('allowed')) for d in rd])
allowed &= ~((eff_r == 3) & ~sr['gate'][0].astype(bool) & (sr['zone'][0] == 2))
VIX = np.array([vix.get(d, np.nan) for d in rd]); V3 = np.array([vix3m.get(d, np.nan) for d in rd])
RATIO = VIX / V3
def rets(fn):
    px = {r['d']: float(r['c']) for r in csv.DictReader(open(os.path.join(NOTES, fn)))}
    r = MC._rets(px, rd); r[0] = 0.0; return r
vixm_r = rets('vixm_rh_daily.csv'); vixy_r = rets('vixy_daily.csv')

def prof(r):
    nav = np.cumprod(1+r); dd = nav/np.maximum.accumulate(nav)-1
    return nav[-1]**(252/len(r))-1, r.mean()*252/(r.std(ddof=1)*252**.5), dd.min()
def halves(r, ds, cut):
    i = next(k for k, d in enumerate(ds) if d >= cut); return prof(r[:i])[1], prof(r[i:])[1]

def runner(sg, pn, d0, extra_cash_legs):
    """extra_cash_legs: list of (returns array, share array of the cash leg). Real panel adds the VIXM sleeve."""
    ds = pn['dates']; s0 = next(i for i, d in enumerate(ds) if d >= d0)
    w5 = MC.target_weights(sg, LIVE); key = MC.regime_key(sg, LIVE)
    cash = w5[0, :, 4].copy()
    legs = [pn['core'], pn['tqqq'], pn['qld'], pn['xlu']]; W = [w5[0, :, i] for i in range(4)]
    real = pn is pr
    if real:
        v = np.where(allowed, cash*S.VIXM_CASH_SHARE, 0.0); legs.append(vixm_r); W.append(v); key = key + allowed[None].astype(int)*100000
    used = W[4] if real else np.zeros_like(cash)
    for j, (rr, sh) in enumerate(extra_cash_legs):
        sh = np.clip(np.nan_to_num(sh), 0, 1)
        x = np.minimum(cash*sh, cash - used); used = used + x
        legs.append(rr); W.append(x); key = key + (sh[None] > 0).astype(int) * (10**(6+j))
    legs.append(pn['cash']); W.append(cash - used)
    w = np.stack(W, -1)[None]; L = np.stack(legs, -1)[None]
    r, tr = MC.run_strategy(w, key, L, s0)
    return r[0], tr[0]/((len(ds)-1-s0)/252), ds[s0+1:]

H = f"  {'variant':<58}{'CAGR':>7}{'vs base':>8}{'Sharpe':>7}{'maxDD':>8}{'Sh 1st':>8}{'Sh 2nd':>8}{'tr/yr':>6}"
def table(title, sg, pn, d0, cut, variants):
    log(f"\n{title}"); log(H)
    base = None
    for lab, ex in variants:
        r, t, ds = runner(sg, pn, d0, ex); c, s, m = prof(r); a, b = halves(r, ds, cut)
        if base is None: base = c
        log(f"  {lab:<58}{c*100:6.1f}%{(c-base)*100:+8.2f}{s:7.3f}{m*100:7.1f}%{a:8.3f}{b:8.3f}{t:6.0f}")

log('='*130); log(f"High-volatility ideas -- live design, 2bp; VIX source {vsrc}; real panel {rd[0]}..{rd[-1]}"); log('='*130)
ONE = np.ones(len(rd))

# ---------- #1 short volatility after the spike: synthetic -1x short-term VIX futures (daily reset) = -VIXY daily return
short_vol = -vixy_r - INV_FEE
short_vol = np.maximum(short_vol, -0.99)
v1 = [('base (live, VIXM sleeve)', [])]
for lo in (18, 20, 25):
    for sh in (0.10, 0.25, 0.50):
        on = (RATIO < 1.0) & (VIX >= lo) & ~allowed
        v1.append((f"#1 short vol {sh*100:.0f}% of cash when VIX>={lo} & VIX<VIX3M", [(short_vol, on*sh)]))
on = (RATIO < 0.95) & (VIX >= 20) & ~allowed
v1.append(("#1 short vol 25% of cash when VIX>=20 & ratio<0.95", [(short_vol, on*0.25)]))
table("#1 SHORT VOLATILITY after a spike (real 2015-11.., -1x VIXY daily, 0.95%/yr fee)", sr, pr, '2015-11-02', '2021-03-01', v1)
on20 = (RATIO < 1.0) & (VIX >= 20) & ~allowed
log(f"  days on (VIX>=20 & VIX<VIX3M, sleeve off): {on20[1:].mean()*100:.1f}% of sessions; short-vol worst day {short_vol.min()*100:.1f}%, worst 5-day {min(np.prod(1+short_vol[i:i+5])-1 for i in range(len(rd)-5))*100:.1f}%")

# ---------- #3 inverse QQQ in F (and E+F) -- both panels
def inv(qr, lev): return np.maximum(-lev*qr - INV_FEE, -0.99)
def fsets(sg):
    e = MC._eff(sg, LIVE)[0]; return e == 5, (e == 4) | (e == 5)
for name, sg, pn, d0, cut in (('REAL 2015-11..', sr, pr, '2015-11-02', '2021-03-01'), ('PROXY 2001.. (no VIXM)', sig, p, '2001-01-02', '2015-11-01')):
    qr = pn['qqq']; F, EF = fsets(sg)
    v3 = [('base', [])]
    for sh in (0.25, 0.50, 1.00):
        v3.append((f"#3 PSQ (-1x QQQ) {sh*100:.0f}% of cash in F", [(inv(qr, 1), F*sh)]))
    for sh in (0.10, 0.25):
        v3.append((f"#3 SQQQ (-3x QQQ) {sh*100:.0f}% of cash in F", [(inv(qr, 3), F*sh)]))
    v3.append(("#3 PSQ 50% of cash in E and F", [(inv(qr, 1), EF*0.5)]))
    table(f"#3 INVERSE QQQ in the downtrend -- {name}", sg, pn, d0, cut, v3)
    log(f"  F share of sessions {F[1:].mean()*100:.1f}%, E {((EF & ~F)[1:]).mean()*100:.1f}%")

# ---------- #4 equity in E -- both panels
for name, sg, pn, d0, cut in (('REAL 2015-11..', sr, pr, '2015-11-02', '2021-03-01'), ('PROXY 2001.. (no VIXM)', sig, p, '2001-01-02', '2015-11-01')):
    e = MC._eff(sg, LIVE)[0]; E = e == 4
    v4 = [('base', [])]
    for sh in (0.25, 0.50, 1.00):
        v4.append((f"#4 QQQ {sh*100:.0f}% of cash in E", [(pn['qqq'], E*sh)]))
    v4.append(("#4 core (SPMO real / QQQ proxy) 50% of cash in E", [(pn['core'], E*0.5)]))
    v4.append(("#4 TQQQ 25% of cash in E", [(pn['tqqq'], E*0.25)]))
    # buy the panic only after a deep fall: E and QQQ >= 10% below its 50d (gaps[100] proxy not in sig; use 200d gap)
    g200 = np.nan_to_num(sg['gaps'][200][0] if isinstance(sg.get('gaps'), dict) else np.zeros(len(pn['dates'])))
    deep = E & (g200 <= -0.05)
    v4.append(("#4 QQQ 50% of cash in E only when >=5% under the 200d", [(pn['qqq'], deep*0.5)]))
    table(f"#4 EQUITY IN E (buy the panic) -- {name}", sg, pn, d0, cut, v4)
