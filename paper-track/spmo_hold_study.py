"""Owner (2026-10-29): "hold SPMO longer during a state shift, considering drift costs and others". Research only.

PRE-REGISTERED before any run (2026-10-29, not edited after). Base = live design as in
spmo_consistency_study.py (monte_carlo.py engine, VIXM left out of every arm). Arms change only
WHEN SPMO is cut; when SPMO is bought is unchanged:
  H5 / H10 / H20  after the SPMO target falls, keep holding the higher SPMO weight for 5 / 10 / 20
                  trading days (SPMO target = max of the last N+1 daily targets). The extra SPMO is
                  funded from the cash leg first, then pro rata from TQQQ/QLD/XLU.
  HB15            hysteresis: SPMO is cut only when the target is more than 15 pp below the held
                  SPMO weight; otherwise SPMO stays and the other legs absorb the difference.
Costs: every arm at the engine's 4 bp per side, and again at 20 bp per side (slippage + spread).
Also reported: SPMO turnover (sum of |SPMO weight change| at trades, per year) and SPMO sell
days per year, the tax-relevant figures. Proxy core is QQQ before 2015.
An arm PASSES only if ALL hold, at 4 bp: P1 Sharpe >= live on real AND proxy; P2 holdout Sharpe
>= live; P3 max DD no more than 1.0 pp deeper on either panel. Then also at 20 bp: P4 the same
P1 holds. Bootstrap (4 bp) reported, not gated.
"""
import csv, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import monte_carlo as MC, state as S
from block_bootstrap import boot
LOG = open(os.path.join(HERE, 'research_notes', 'spmo_hold_study_run.log'), 'w')
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

LIVE = dict(MC.LIVE, a_base=(0.40, 0.60), vol='max10_30')
assert S.D_LADDER_ROWS == {'D1': (0.5, 0.0, 0.5), 'D2': (0.0, 0.5, 0.5), 'D3': (0.0, 1.0, 0.0)}
p = MC.load_panel('proxy'); dates = p['dates']
sig = MC.signals((100 * np.cumprod(1 + p['qqq']))[None], (100 * np.cumprod(1 + p['ew']))[None])
pr = MC.load_panel('real'); off = dates.index(pr['dates'][0])
sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items()}

def fund(w, s_new):
    """Set SPMO to s_new; the change comes out of cash first, then TQQQ/QLD/XLU pro rata."""
    w = w.copy(); extra = s_new - w[0]; w[0] = s_new
    take = min(extra, w[4]); w[4] -= take; extra -= take
    if extra > 1e-12:
        o = w[1:4].sum(); w[1:4] *= max(0.0, 1 - extra / o) if o > 0 else 0
    w[4] = 1 - w[:4].sum()
    return w

def run_hold(w, key, legs, s0, arm):
    """Engine loop (as MC.run_strategy) with the arm's SPMO-cut rule applied to the target."""
    w = w[0]; key = key[0]; legs = legs[0]; T = w.shape[0]
    if arm.startswith('H') and arm != 'HB15':
        N = int(arm[1:]); tw = w.copy()
        for t in range(T):
            m = np.nanmax(w[max(0, t - N):t + 1, 0])
            if m > w[t, 0]: tw[t] = fund(w[t], m)
        w = tw
    out = np.zeros(T - s0 - 1); h = w[s0].copy(); cost = MC.COST; trades = 0; sturn = 0.0; ssell = 0
    for t in range(s0, T - 1):
        if t > s0:
            tgt = w[t]
            if arm == 'HB15' and h[0] - tgt[0] > 0 and h[0] - tgt[0] <= 0.15:
                tgt = fund(tgt, h[0])
            drift = np.abs(tgt - h).sum()
            stub = ((tgt == 0) & (h > S.ZERO_LEG_EPS)).any()
            reb = key[t] != key[t - 1] or drift > S.REBALANCE_DRIFT_BAND or stub
            cost = MC.COST * drift if reb else 0.0
            if reb:
                trades += 1; sturn += abs(tgt[0] - h[0]); ssell += tgt[0] < h[0] - 1e-9; h = tgt.copy()
        r = legs[t + 1]; g = (h * r).sum()
        out[t - s0] = (1 + g) * (1 - cost) - 1
        h = h * (1 + r) / (1 + g)
    return out, trades, sturn, ssell

def run(sg, pn, d0, arm, d1='2099'):
    ds = pn['dates']; s0 = next(i for i, d in enumerate(ds) if d >= d0); e = max(i for i, d in enumerate(ds) if d <= d1)
    sg = {k: (v[:, :e + 1] if not isinstance(v, dict) else {n: a[:, :e + 1] for n, a in v.items()}) for k, v in sg.items()}
    w = MC.target_weights(sg, LIVE); key = MC.regime_key(sg, LIVE)
    legs = np.stack([pn['core'], pn['tqqq'], pn['qld'], pn['xlu'], pn['cash']], -1)[None][:, :e + 1]
    if arm == 'live':                                   # the live arm also goes through the engine itself, as a check
        r0, _ = MC.run_strategy(w, key, legs, s0)
    r, tr, st, ss = run_hold(w, key, legs, s0, arm)
    if arm == 'live': assert np.allclose(r, r0[0]), 'local loop does not reproduce MC.run_strategy'
    nav = np.cumprod(1 + r); dd = nav / np.maximum.accumulate(np.concatenate([[1.0], nav]))[1:] - 1
    yrs = (e - s0) / 252
    return dict(r=r, c=nav[-1] ** (252 / len(r)) - 1, sh=r.mean() * 252 / (r.std(ddof=1) * 252 ** 0.5), m=dd.min(),
                a=dd.mean(), tpy=tr / yrs, st=st / yrs, ss=ss / yrs, cash=pn['cash'][s0 + 1:e + 1], days=ds[s0 + 1:e + 1])

ARMS = ['live', 'H5', 'H10', 'H20', 'HB15']
LAB = {'live': 'live design', 'H5': 'hold SPMO cut 5 days', 'H10': 'hold SPMO cut 10 days',
       'H20': 'hold SPMO cut 20 days', 'HB15': 'cut SPMO only if >15 pp'}
PAN = [('real', sr, pr, '2015-11-02', '2099', 'REAL ETFs (extended with live closes)'),
       ('proxy', sig, p, '2001-01-02', '2099', 'PROXY 2001.. (core = QQQ)'),
       ('hold', sig, p, '2001-01-02', '2015-10-31', 'HOLDOUT 2001..2015-10 (proxy)')]
R = {}
log('=' * 118); log('spmo_hold_study (2026-10-29): hold SPMO longer through state shifts? (pre-registered)'); log('=' * 118)
for bp in (4, 20):
    MC.COST = bp / 1e4
    for tag, sg, pn, d0, d1, title in PAN:
        for a in ARMS: R[(bp, tag, a)] = run(sg, pn, d0, a, d1)
        x = R[(bp, tag, 'live')]
        log(f"\n  {title}  {x['days'][0]}..{x['days'][-1]}   cost {bp} bp per side")
        log(f"  {'arm':<26}{'CAGR':>8}{'Sharpe':>8}{'max DD':>8}{'avg DD':>8}{'trades/yr':>10}{'SPMO turn/yr':>13}{'SPMO sells/yr':>14}")
        for a in ARMS:
            x = R[(bp, tag, a)]
            log(f"  {LAB[a]:<26}{x['c']*100:7.2f}%{x['sh']:8.3f}{x['m']*100:7.1f}%{x['a']*100:7.1f}%{x['tpy']:10.0f}{x['st']*100:12.0f}%{x['ss']:14.1f}")
MC.COST = 0.0004
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
    log(f"  {LAB[a]:<26} P1 {'Y' if P[0] else 'n'} (dSh {A['real']['sh']-L['real']['sh']:+.3f} / {A['proxy']['sh']-L['proxy']['sh']:+.3f})  "
        f"P2 {'Y' if P[1] else 'n'} ({A['hold']['sh']-L['hold']['sh']:+.3f})  P3 {'Y' if P[2] else 'n'} "
        f"(dDD {(A['real']['m']-L['real']['m'])*100:+.1f} / {(A['proxy']['m']-L['proxy']['m'])*100:+.1f} pp)  "
        f"P4@20bp {'Y' if P[3] else 'n'} ({A20['real']['sh']-L20['real']['sh']:+.3f} / {A20['proxy']['sh']-L20['proxy']['sh']:+.3f})"
        f"  => {'PASS' if all(P) else 'fail'}   bootstrap {'; '.join(bs)}")
