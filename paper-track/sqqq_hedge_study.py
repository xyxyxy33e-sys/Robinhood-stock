"""Owner (2026-10-30), comparing with alphaAI's "Leveraged Nasdaq" (VGT base + TQQQ sleeve, SQQQ
hedge in sustained downtrends): would an SQQQ hedge help this design? Research only.

PRE-REGISTERED before any run (2026-10-30, not edited after). Base = live design incl. the
2026-10-29 zone buffer (monte_carlo.py, cfg d_buffer=0.005), VIXM left out of every arm. SQQQ is
synthetic on both panels (no SQQQ file): daily -3 x QQQ total return + 4 x cash, less the 0.95%
expense ratio and the engine's 0.3% financing spread on the 3x notional. It rides in the XLU slot
(XLU is 0% in every live row). Arms (rows before the vol target, which scales SQQQ like any risky leg):
  F25   F = 25% SQQQ / 75% BOXX            F50   F = 50% SQQQ / 50% BOXX
  F100  F = 100% SQQQ (alphaAI-style: hedge the established downtrend)
  EF25  E and F = 25% SQQQ / 75% BOXX
Pass rules as d_zone_buffer_study.py: P1 Sharpe >= live on real AND proxy (4 bp); P2 holdout
Sharpe >= live; P3 max DD no more than 1.0 pp deeper on either panel; P4 P1 again at 20 bp.
"""
import csv, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import monte_carlo as MC, state as S
from block_bootstrap import boot
LOG = open(os.path.join(HERE, 'research_notes', 'sqqq_hedge_study_run.log'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); LOG.write(s + '\n'); LOG.flush()

LC = list(csv.DictReader(open(os.path.join(MC.DATA, 'live_closes.csv'))))
EXT = {'qqq_long_history.csv': 'QQQ', 'QQEW_daily_ext.csv': 'QQEW', 'spmo_ohlc.csv': 'SPMO',
       'tqqq_ohlc.csv': 'TQQQ', 'qld_ohlc.csv': 'QLD', 'xlu_ohlc.csv': 'XLU'}
_orig = MC._load
def _load(name, dcol='d', ccol='c'):
    out = _orig(name, dcol, ccol)
    if name in EXT or name == 'spy_long_history.csv':
        last = max(out); v = out[last]
        for r in LC:
            if r['date'] > last:
                if name in EXT and r[EXT[name]]: out[r['date']] = float(r[EXT[name]])
                elif name not in EXT: out[r['date']] = v
    return out
MC._load = _load

LIVE = dict(MC.LIVE, a_base=(0.40, 0.60), vol='max10_30', d_buffer=S.D_ZONE_BUFFER)
assert all(r[3] == 0 for r in LIVE['rows'].values()), "XLU slot must be unused in the live rows"
p = MC.load_panel('proxy'); dates = p['dates']
sig = MC.signals((100 * np.cumprod(1 + p['qqq']))[None], (100 * np.cumprod(1 + p['ew']))[None])
pr = MC.load_panel('real'); off = dates.index(pr['dates'][0])
sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items()}
SQQQ_ER = 0.0095
def sqqq(pn):
    return -3 * pn['qqq_tr'] + 4 * pn['cash'] - (SQQQ_ER + 3 * MC.FIN_SPREAD) / 252

ROWS = {'live': {}, 'F25': {'F': (0, 0, 0, 0.25, 0.75)}, 'F50': {'F': (0, 0, 0, 0.5, 0.5)},
        'F100': {'F': (0, 0, 0, 1.0, 0.0)}, 'EF25': {'E': (0, 0, 0, 0.25, 0.75), 'F': (0, 0, 0, 0.25, 0.75)}}
LAB = {'live': 'live design (BOXX in E/F)', 'F25': 'F 25% SQQQ', 'F50': 'F 50% SQQQ', 'F100': 'F 100% SQQQ',
       'EF25': 'E and F 25% SQQQ'}

def run(sg, pn, d0, arm, d1='2099'):
    ds = pn['dates']; s0 = next(i for i, d in enumerate(ds) if d >= d0); e = max(i for i, d in enumerate(ds) if d <= d1)
    sg = {k: (v[:, :e + 1] if not isinstance(v, dict) else {n: a[:, :e + 1] for n, a in v.items()}) for k, v in sg.items()
          if not isinstance(k, tuple)}
    cfg = dict(LIVE, rows=dict(LIVE['rows'], **ROWS[arm]))
    w = MC.target_weights(sg, cfg); key = MC.regime_key(sg, cfg)
    legs = np.stack([pn['core'], pn['tqqq'], pn['qld'], sqqq(pn), pn['cash']], -1)[None][:, :e + 1]
    r, tr = MC.run_strategy(w, key, legs, s0); r = r[0]
    nav = np.cumprod(1 + r); dd = nav / np.maximum.accumulate(np.concatenate([[1.0], nav]))[1:] - 1
    sq = w[0, s0:e, 3]
    return dict(r=r, c=nav[-1] ** (252 / len(r)) - 1, sh=r.mean() * 252 / (r.std(ddof=1) * 252 ** 0.5), m=dd.min(),
                a=dd.mean(), tpy=tr[0] / ((e - s0) / 252), sqd=(sq > 0).mean(), cash=pn['cash'][s0 + 1:e + 1],
                days=ds[s0 + 1:e + 1], nav=nav, ds=ds[s0 + 1:e + 1])

ARMS = list(ROWS)
PAN = [('real', sr, pr, '2015-11-02', '2099', 'REAL ETFs (extended with live closes; SQQQ synthetic)'),
       ('proxy', sig, p, '2001-01-02', '2099', 'PROXY 2001.. (core = QQQ)'),
       ('hold', sig, p, '2001-01-02', '2015-10-31', 'HOLDOUT 2001..2015-10 (proxy)')]
R = {}
log('=' * 112); log('sqqq_hedge_study (2026-10-30): an SQQQ hedge in E/F? (pre-registered)'); log('=' * 112)
for bp in (4, 20):
    MC.COST = bp / 1e4
    for tag, sg, pn, d0, d1, title in PAN:
        for a in ARMS: R[(bp, tag, a)] = run(sg, pn, d0, a, d1)
        x = R[(bp, tag, 'live')]
        log(f"\n  {title}  {x['days'][0]}..{x['days'][-1]}   cost {bp} bp per side")
        log(f"  {'arm':<28}{'CAGR':>8}{'Sharpe':>8}{'max DD':>8}{'avg DD':>8}{'trades/yr':>10}{'SQQQ days':>10}")
        for a in ARMS:
            x = R[(bp, tag, a)]
            log(f"  {LAB[a]:<28}{x['c']*100:7.2f}%{x['sh']:8.3f}{x['m']*100:7.1f}%{x['a']*100:7.1f}%{x['tpy']:10.0f}{x['sqd']*100:9.1f}%")
MC.COST = 0.0004
log("\n  Calendar years, proxy, 4 bp (strategy return)")
yrs = sorted({d[:4] for d in R[(4, 'proxy', 'live')]['ds']})
log("  " + f"{'year':<6}" + ''.join(f"{LAB[a][:14]:>16}" for a in ARMS))
for y in yrs:
    row = []
    for a in ARMS:
        x = R[(4, 'proxy', a)]; idx = [i for i, d in enumerate(x['ds']) if d[:4] == y]
        row.append(np.prod(1 + x['r'][idx]) - 1)
    log("  " + f"{y:<6}" + ''.join(f"{v*100:15.1f}%" for v in row))
log("\n  PRE-REGISTERED VERDICT")
for a in ARMS[1:]:
    L = {t: R[(4, t, 'live')] for t in ('real', 'proxy', 'hold')}; A = {t: R[(4, t, a)] for t in ('real', 'proxy', 'hold')}
    L20 = {t: R[(20, t, 'live')] for t in ('real', 'proxy')}; A20 = {t: R[(20, t, a)] for t in ('real', 'proxy')}
    P = [A['real']['sh'] >= L['real']['sh'] and A['proxy']['sh'] >= L['proxy']['sh'], A['hold']['sh'] >= L['hold']['sh'],
         A['real']['m'] >= L['real']['m'] - 0.01 and A['proxy']['m'] >= L['proxy']['m'] - 0.01,
         A20['real']['sh'] >= L20['real']['sh'] and A20['proxy']['sh'] >= L20['proxy']['sh']]
    bs = []
    for t in ('real', 'proxy'):
        *_, s1, s2, ps = boot(list(A[t]['r'] - A[t]['cash']), list(L[t]['r'] - L[t]['cash']), 60, seed=(sum(map(ord, a)) * 31 + len(t)) & 0xffff)
        bs.append(f"{t} [{s1:+.3f}, {s2:+.3f}] P {ps:.2f}")
    log(f"  {LAB[a]:<28} P1 {'Y' if P[0] else 'n'} (dSh {A['real']['sh']-L['real']['sh']:+.3f} / {A['proxy']['sh']-L['proxy']['sh']:+.3f})  "
        f"P2 {'Y' if P[1] else 'n'} ({A['hold']['sh']-L['hold']['sh']:+.3f})  P3 {'Y' if P[2] else 'n'} "
        f"(dDD {(A['real']['m']-L['real']['m'])*100:+.1f} / {(A['proxy']['m']-L['proxy']['m'])*100:+.1f} pp)  "
        f"P4@20bp {'Y' if P[3] else 'n'} ({A20['real']['sh']-L20['real']['sh']:+.3f} / {A20['proxy']['sh']-L20['proxy']['sh']:+.3f})"
        f"  => {'PASS' if all(P) else 'fail'}   bootstrap {'; '.join(bs)}")
