"""Owner (2026-10-30): "test if vgt is a better core", "also looking into the sp version with voo
spxl spxs" (alphaAI's Leveraged Nasdaq uses a VGT base; its Leveraged S&P uses VOO/SPXL/SPXS).
Research only.

PRE-REGISTERED before any run (2026-10-30, not edited after).
Design = live (A 40/60 + trim v2, B 75/25, C core, D ladder + gate + 0.5% zone buffer, E/F BOXX,
max(10d,30d) vol target 20%, 5% band), monte_carlo.py engine, VIXM left out of every arm.
Data: Yahoo split-adjusted daily closes (data/*_yahoo_daily.csv, checked against Robinhood's
29 Oct closes), price returns like the engine's real panel, plus a flat dividend accrual per core
(SPMO 0.8%, VGT 0.6%, QQQ 0.6%, VOO/SPY 1.3% a year) so cores with different yields compare fairly.
Arms:
  N-SPMO   live: QQQ signals, SPMO core, TQQQ, QLD
  N-VGT    same, VGT core            N-QQQ   same, QQQ core (the pre-2015 proxy core)
  S        S&P version: SPY signals (breadth = RSP vs SPY), VOO core, SPXL 3x, SSO 2x, BOXX in E/F
  S-SPXS   S with F = 100% SPXS (alphaAI-style hedge)
  S-NQ     QQQ signals, S&P instruments (VOO/SPXL/SSO)
Windows: W1 real ETFs 2015-11-02..2026-10-29 (SPMO era; S&P legs real);
         W2 real leveraged ETFs 2010-06-01..2026-10-29 (no SPMO: N-VGT vs N-QQQ, S arms);
         W3 2005-01-03..2026-10-29 with synthetic 3x/2x legs from the underlying (+ER, 0.3% spread).
Each at 4 bp and 20 bp per side.
Verdicts: VGT replaces SPMO only if N-VGT Sharpe >= N-SPMO on W1 at both costs, max DD no more than
1 pp deeper on W1, and N-VGT Sharpe >= N-QQQ on W2 and W3 (robustness, the only longer test of VGT).
The S&P version is worth considering only if S (or S-SPXS / S-NQ) has Sharpe >= N-SPMO on W1 at both
costs AND >= N-QQQ on W2 and W3, max DD no more than 1 pp deeper on W1.
"""
import csv, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import monte_carlo as MC, state as S
DATA = MC.DATA
LOG = open(os.path.join(HERE, 'research_notes', 'core_and_sp_study_run.log'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); LOG.write(s + '\n'); LOG.flush()

def ld(name, dcol='d', ccol='c'):
    return {r[dcol]: float(r[ccol]) for r in csv.DictReader(open(os.path.join(DATA, name))) if r.get(ccol) not in (None, '')}
LC = list(csv.DictReader(open(os.path.join(DATA, 'live_closes.csv'))))
def ext(px, col):
    last = max(px)
    for r in LC:
        if r['date'] > last and r.get(col): px[r['date']] = float(r[col])
    return px
qqq = ext(MC._load('qqq_long_history.csv'), 'QQQ'); qqew = ext(MC._load('QQEW_daily_ext.csv'), 'QQEW')
surv = MC._load('ndx_survivor_ew_daily.csv')
spmo = ext(MC._load('spmo_ohlc.csv'), 'SPMO')
tq, ql = ld('tqqq_yahoo_daily.csv'), ld('qld_yahoo_daily.csv')      # repo files start 2015-10; Yahoo from 2010 / 2006
spy, rsp = ld('spy_yahoo_daily.csv'), ld('RSP_daily.csv')
vgt, voo, spxl, spxs, sso = (ld(f'{s}_yahoo_daily.csv') for s in ('vgt', 'voo', 'spxl', 'spxs', 'sso'))
tb = MC._load('dgs3mo_full.csv', 'observation_date', 'DGS3MO')
END = '2026-10-29'
D = sorted(d for d in qqq if '2003-05-01' <= d <= END and d in spy)       # RSP starts 2003-05-01
T = len(D)
yf = np.array([0.0] + [MC._yf(D[i - 1], D[i]) for i in range(1, T)])
tbd = sorted(tb); rate = []; last = 0.0; j = 0
for d in D:
    while j < len(tbd) and tbd[j] <= d: last = tb[tbd[j]]; j += 1
    rate.append(last / 100)
rprev = np.concatenate([[rate[0]], rate[:-1]]); cash = rprev * yf
def R(px): r = MC._rets(px, D); r[0] = 0.0; return r
DIV = dict(spmo=0.008, vgt=0.006, qqq=0.006, voo=0.013)
u_q = R(qqq) + DIV['qqq'] * yf; u_s = R(spy) + DIV['voo'] * yf
fin = (rprev + MC.FIN_SPREAD) * yf
syn = lambda u, L, er: L * u - (L - 1) * fin - er * yf
inv3 = lambda u, er: -3 * u + 4 * rprev * yf - (er + 3 * MC.FIN_SPREAD) * yf
leg = dict(
    spmo=R(spmo) + DIV['spmo'] * yf, vgt=R(vgt) + DIV['vgt'] * yf, qqq=u_q,
    voo=np.where([d in voo for d in D], R(voo) + DIV['voo'] * yf, u_s),                 # SPY before VOO (2010-09)
    tqqq_r=R(tq), qld_r=R(ql), spxl_r=R(spxl), sso_r=R(sso), spxs_r=R(spxs),
    tqqq_s=syn(u_q, 3, MC.TQQQ_ER), qld_s=syn(u_q, 2, MC.QLD_ER), spxl_s=syn(u_s, 3, 0.0091),
    sso_s=syn(u_s, 2, 0.0089), spxs_s=inv3(u_s, 0.0108))
first = {k: min(v) for k, v in dict(spmo=spmo, vgt=vgt, tqqq=tq, qld=ql, spxl=spxl, sso=sso, spxs=spxs).items()}

# signals: Nasdaq from the full QQQ / QQEW(+survivor EW) history; S&P from SPY / RSP (from 2003-05)
pD = sorted(d for d in qqq if d <= END)
ewr = np.where([d in qqew for d in pD], MC._rets(qqew, pD), MC._rets(surv, pD)); ewr[0] = 0
ewr[[i for i, d in enumerate(pD) if d == min(qqew)]] = 0.0
sigN_full = MC.signals(np.array([qqq[d] for d in pD])[None], (100 * np.cumprod(1 + ewr))[None])
o = pD.index(D[0]); idx = [pD.index(d) for d in D]
sigN = {k: (v[:, idx] if not isinstance(v, dict) else {n: a[:, idx] for n, a in v.items()}) for k, v in sigN_full.items()}
spx = np.array([spy.get(d) for d in D], float)
rpx = np.array([np.nan] * T)
lastv = None
for i, d in enumerate(D):
    lastv = rsp.get(d, lastv); rpx[i] = lastv
sigS = MC.signals(spx[None], rpx[None])
LIVE = dict(MC.LIVE, a_base=(0.40, 0.60), vol='max10_30', d_buffer=S.D_ZONE_BUFFER)

ARMS = {  # name: (signals, core, 3x, 2x, F row override)
    'N-SPMO': ('N', 'spmo', 'tqqq', 'qld', None), 'N-VGT': ('N', 'vgt', 'tqqq', 'qld', None),
    'N-QQQ': ('N', 'qqq', 'tqqq', 'qld', None), 'S': ('S', 'voo', 'spxl', 'sso', None),
    'S-SPXS': ('S', 'voo', 'spxl', 'sso', 'spxs'), 'S-NQ': ('N', 'voo', 'spxl', 'sso', None)}
LAB = {'N-SPMO': 'Nasdaq, SPMO core (live)', 'N-VGT': 'Nasdaq, VGT core', 'N-QQQ': 'Nasdaq, QQQ core',
       'S': 'S&P: VOO/SPXL/SSO', 'S-SPXS': 'S&P + 100% SPXS in F', 'S-NQ': 'S&P legs, QQQ signals'}
WIN = {'W1': ('2015-11-02', 'r', 'REAL ETFs 2015-11..2026-10 (SPMO era)'),
       'W2': ('2010-06-01', 'r', 'REAL leveraged ETFs 2010-06..2026-10'),
       'W3': ('2005-01-03', 's', 'SYNTHETIC 3x/2x legs 2005-01..2026-10')}

def run(arm, win):
    sname, core, l3, l2, f = ARMS[arm]; d0, kind, _ = WIN[win]
    if core == 'spmo' and d0 < first['spmo']: return None
    sg = sigN if sname == 'N' else sigS
    s0 = next(i for i, d in enumerate(D) if d >= d0)
    cfg = dict(LIVE, rows=dict(LIVE['rows'], **({'F': (0, 0, 0, 1.0, 0.0)} if f else {})))
    w = MC.target_weights(sg, cfg); key = MC.regime_key(sg, cfg)
    pick = lambda k: leg[f'{k}_{kind}'] if f'{k}_{kind}' in leg else leg[k]
    if kind == 'r':
        for k in (l3, l2) + ((f,) if f else ()):
            assert first[k] <= D[s0], (k, first[k], D[s0])
    hedge = pick(f) if f else np.zeros(T)
    legs = np.stack([leg[core], pick(l3), pick(l2), hedge, cash], -1)[None]
    r, tr = MC.run_strategy(w, key, legs, s0); r = r[0]
    nav = np.cumprod(1 + r); dd = nav / np.maximum.accumulate(np.concatenate([[1.0], nav]))[1:] - 1
    return dict(r=r, c=nav[-1] ** (252 / len(r)) - 1, sh=r.mean() * 252 / (r.std(ddof=1) * 252 ** 0.5),
                m=dd.min(), a=dd.mean(), tpy=tr[0] / (len(r) / 252), ds=D[s0 + 1:])

RES = {}
log('=' * 110); log('core_and_sp_study (2026-10-30): VGT core? S&P version? (pre-registered)'); log('=' * 110)
for bp in (4, 20):
    MC.COST = bp / 1e4
    for wn, (d0, kind, title) in WIN.items():
        log(f"\n  {title}   cost {bp} bp per side")
        log(f"  {'arm':<28}{'CAGR':>8}{'Sharpe':>8}{'max DD':>8}{'avg DD':>8}{'trades/yr':>10}")
        for a in ARMS:
            x = run(a, wn); RES[(bp, wn, a)] = x
            if x: log(f"  {LAB[a]:<28}{x['c']*100:7.2f}%{x['sh']:8.3f}{x['m']*100:7.1f}%{x['a']*100:7.1f}%{x['tpy']:10.0f}")
        # buy-and-hold references on the same window
        s0 = next(i for i, d in enumerate(D) if d >= d0)
        for nm, rr in (('hold QQQ', leg['qqq']), ('hold VOO/SPY', leg['voo']), ('hold VGT', leg['vgt']),
                       ('hold TQQQ', leg['tqqq_' + kind]), ('hold SPXL', leg['spxl_' + kind])):
            if nm == 'hold VGT' and D[s0] < first['vgt']: continue
            q = rr[s0 + 1:]; nav = np.cumprod(1 + q); dd = (nav / np.maximum.accumulate(np.concatenate([[1.0], nav]))[1:] - 1).min()
            if bp == 4: log(f"  {nm:<28}{(nav[-1] ** (252 / len(q)) - 1)*100:7.2f}%{q.mean()*252/(q.std(ddof=1)*252**.5):8.3f}{dd*100:7.1f}%")
MC.COST = 0.0004
log("\n  Calendar years, W3 synthetic, 4 bp")
x0 = RES[(4, 'W3', 'N-QQQ')]; yrs = sorted({d[:4] for d in x0['ds']})
arms3 = [a for a in ARMS if RES[(4, 'W3', a)]]
log("  " + f"{'year':<6}" + ''.join(f"{a:>10}" for a in arms3))
for y in yrs:
    vals = []
    for a in arms3:
        x = RES[(4, 'W3', a)]; ii = [i for i, d in enumerate(x['ds']) if d[:4] == y]; vals.append(np.prod(1 + x['r'][ii]) - 1)
    log("  " + f"{y:<6}" + ''.join(f"{v*100:9.1f}%" for v in vals))
log("\n  PRE-REGISTERED VERDICT")
g = lambda bp, w, a, k: RES[(bp, w, a)][k]
vgt_ok = all(g(bp, 'W1', 'N-VGT', 'sh') >= g(bp, 'W1', 'N-SPMO', 'sh') for bp in (4, 20)) \
    and g(4, 'W1', 'N-VGT', 'm') >= g(4, 'W1', 'N-SPMO', 'm') - 0.01 \
    and all(g(4, w, 'N-VGT', 'sh') >= g(4, w, 'N-QQQ', 'sh') for w in ('W2', 'W3'))
log(f"  VGT core: W1 dSh vs SPMO {g(4,'W1','N-VGT','sh')-g(4,'W1','N-SPMO','sh'):+.3f} (4bp) / "
    f"{g(20,'W1','N-VGT','sh')-g(20,'W1','N-SPMO','sh'):+.3f} (20bp); dDD {(g(4,'W1','N-VGT','m')-g(4,'W1','N-SPMO','m'))*100:+.1f} pp; "
    f"vs QQQ core W2 {g(4,'W2','N-VGT','sh')-g(4,'W2','N-QQQ','sh'):+.3f}, W3 {g(4,'W3','N-VGT','sh')-g(4,'W3','N-QQQ','sh'):+.3f}"
    f"  => {'PASS' if vgt_ok else 'fail'}")
for a in ('S', 'S-SPXS', 'S-NQ'):
    ok = all(g(bp, 'W1', a, 'sh') >= g(bp, 'W1', 'N-SPMO', 'sh') for bp in (4, 20)) \
        and g(4, 'W1', a, 'm') >= g(4, 'W1', 'N-SPMO', 'm') - 0.01 \
        and all(g(4, w, a, 'sh') >= g(4, w, 'N-QQQ', 'sh') for w in ('W2', 'W3'))
    log(f"  {LAB[a]:<28} W1 dSh vs live {g(4,'W1',a,'sh')-g(4,'W1','N-SPMO','sh'):+.3f} / {g(20,'W1',a,'sh')-g(20,'W1','N-SPMO','sh'):+.3f}; "
        f"dDD {(g(4,'W1',a,'m')-g(4,'W1','N-SPMO','m'))*100:+.1f} pp; vs Nasdaq QQQ-core W2 {g(4,'W2',a,'sh')-g(4,'W2','N-QQQ','sh'):+.3f}, "
        f"W3 {g(4,'W3',a,'sh')-g(4,'W3','N-QQQ','sh'):+.3f}  => {'PASS' if ok else 'fail'}")
