"""Owner (2026-10-29): "test if holding spmo more consistently is beneficial". Research only.

PRE-REGISTERED before any run (2026-10-29, not edited after). Base = the live design
(A 40/60 + trim v2 carry 3, B 75/25, C 100% SPMO, D gate, D ladder D1 50 SPMO/50 QLD,
D2 50 TQQQ/50 QLD, D3 100% TQQQ, E/F cash, max(10d,30d) vol target 20%, 5% band, 4bp),
monte_carlo.py engine (verified against state.py). VIXM is left out of every arm (it only
lives in the cash leg these arms shrink, so it would favour the base). Arms:
  V1  E and F hold 50% SPMO / 50% BOXX (was 100% BOXX)
  V2  E and F hold 100% SPMO
  V3  V1 + a gated D day holds 50% SPMO / 50% BOXX (was 100% BOXX)
  V4  SPMO floor of 30% in every row that has less: D2 30/35/35 SPMO/TQQQ/QLD, D3 30/70
      SPMO/TQQQ, E/F/gated D 30% SPMO / 70% BOXX
  V5  trim v2 keeps SPMO at its base while votes are held (TQQQ still out; no 1/6 cut)
The vol target scales SPMO with every other risky leg in all arms.
An arm PASSES only if ALL hold: P1 Sharpe >= live on the real AND proxy panels; P2 proxy
2001-2015 holdout Sharpe >= live; P3 max drawdown no more than 1.0 pp deeper than live on
either panel. Block bootstrap reported, not gated. On the proxy panel the core is QQQ
(SPMO starts 2015), so there the arms test "hold the core more consistently".
"""
import csv, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import monte_carlo as MC, state as S
from block_bootstrap import boot
LOG = open(os.path.join(HERE, 'research_notes', 'spmo_consistency_study_run.log'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); LOG.write(s + '\n'); LOG.flush()

# extend the real-ETF files with the recorded live closes (through the latest run)
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
                elif name not in EXT: out[r['date']] = v        # SPY unused: carried flat
    return out
MC._load = _load

LIVE = dict(MC.LIVE, a_base=(0.40, 0.60), vol='max10_30')
assert S.D_LADDER_ROWS == {'D1': (0.5, 0.0, 0.5), 'D2': (0.0, 0.5, 0.5), 'D3': (0.0, 1.0, 0.0)}
p = MC.load_panel('proxy'); dates = p['dates']
sig = MC.signals((100 * np.cumprod(1 + p['qqq']))[None], (100 * np.cumprod(1 + p['ew']))[None])
pr = MC.load_panel('real'); off = dates.index(pr['dates'][0])
sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items()}

def weights(sg, arm):
    cfg = dict(LIVE, rows=dict(LIVE['rows']))
    ladder = dict(S.D_LADDER_ROWS); gate_row = None; cut = S.EXTENSION_CORE_CUT_PER_VOTE
    if arm in ('V1', 'V3'): cfg['rows']['E'] = cfg['rows']['F'] = (0.5, 0, 0, 0, 0.5)
    if arm == 'V2': cfg['rows']['E'] = cfg['rows']['F'] = (1.0, 0, 0, 0, 0.0)
    if arm == 'V3': gate_row = (0.5, 0, 0, 0, 0.5)
    if arm == 'V4':
        cfg['rows']['E'] = cfg['rows']['F'] = (0.3, 0, 0, 0, 0.7); gate_row = (0.3, 0, 0, 0, 0.7)
        ladder['D2'] = (0.30, 0.35, 0.35); ladder['D3'] = (0.30, 0.70, 0.0)
    if arm == 'V5': cut = 0.0
    saved = dict(S.D_LADDER_ROWS), S.EXTENSION_CORE_CUT_PER_VOTE
    S.D_LADDER_ROWS.update(ladder); S.EXTENSION_CORE_CUT_PER_VOTE = cut
    try:
        w = MC.target_weights(sg, cfg)
    finally:
        S.D_LADDER_ROWS.clear(); S.D_LADDER_ROWS.update(saved[0]); S.EXTENSION_CORE_CUT_PER_VOTE = saved[1]
    if gate_row is not None:                                # gated D: the engine wrote all cash; apply the arm's row
        v = np.fmax(sg['vol'], np.where(np.isnan(sg['vol']), np.nan, sg['vol10']))
        mult = np.where(np.isnan(v) | (v <= 0), 1.0, np.minimum(1.0, S.VOL_TARGET_PA / np.where(v > 0, v, 1)))
        g = MC._gate(sg, cfg)
        for j in range(4): w[..., j] = np.where(g, gate_row[j] * mult, w[..., j])
        w[..., 4] = 1.0 - w[..., :4].sum(-1)
    return w, MC.regime_key(sg, cfg)

def run(sg, pn, d0, arm, d1='2099'):
    ds = pn['dates']; s0 = next(i for i, d in enumerate(ds) if d >= d0); e = max(i for i, d in enumerate(ds) if d <= d1)
    sg = {k: (v[:, :e + 1] if not isinstance(v, dict) else {n: a[:, :e + 1] for n, a in v.items()}) for k, v in sg.items()}
    w, key = weights(sg, arm)
    legs = np.stack([pn['core'], pn['tqqq'], pn['qld'], pn['xlu'], pn['cash']], -1)[None][:, :e + 1]
    r, tr = MC.run_strategy(w, key, legs, s0)
    r = r[0]; nav = np.cumprod(1 + r); dd = nav / np.maximum.accumulate(np.concatenate([[1.0], nav]))[1:] - 1
    sh = r.mean() * 252 / (r.std(ddof=1) * 252 ** 0.5)
    return dict(r=r, c=nav[-1] ** (252 / len(r)) - 1, sh=sh, m=dd.min(), a=dd.mean(), tpy=tr[0] / ((e - s0) / 252),
                core=w[0, s0:e, 0].mean(), cash=pn['cash'][s0 + 1:e + 1], days=ds[s0 + 1:e + 1])

ARMS = ['live', 'V1', 'V2', 'V3', 'V4', 'V5']
LAB = {'live': 'live design', 'V1': 'E/F 50% SPMO', 'V2': 'E/F 100% SPMO', 'V3': 'E/F + gated D 50% SPMO',
       'V4': 'SPMO floor 30% everywhere', 'V5': 'trim keeps SPMO at base'}
PAN = [('real', sr, pr, '2015-11-02', '2099', 'REAL ETFs (extended with live closes)'),
       ('proxy', sig, p, '2001-01-02', '2099', 'PROXY 2001.. (core = QQQ)'),
       ('hold', sig, p, '2001-01-02', '2015-10-31', 'HOLDOUT 2001..2015-10 (proxy)')]
R = {}
log('=' * 120); log('spmo_consistency_study (2026-10-29): hold SPMO more consistently? (pre-registered)'); log('=' * 120)
for tag, sg, pn, d0, d1, title in PAN:
    for a in ARMS: R[(tag, a)] = run(sg, pn, d0, a, d1)
    x = R[(tag, 'live')]
    log(f"\n  {title}  {x['days'][0]}..{x['days'][-1]}")
    log(f"  {'arm':<28}{'CAGR':>8}{'Sharpe':>8}{'max DD':>8}{'avg DD':>8}{'trades/yr':>10}{'avg core wt':>12}")
    for a in ARMS:
        x = R[(tag, a)]
        log(f"  {LAB[a]:<28}{x['c']*100:7.2f}%{x['sh']:8.3f}{x['m']*100:7.1f}%{x['a']*100:7.1f}%{x['tpy']:10.0f}{x['core']*100:11.0f}%")
log("\n  PRE-REGISTERED VERDICT")
for a in ARMS[1:]:
    L = {t: R[(t, 'live')] for t in ('real', 'proxy', 'hold')}; A = {t: R[(t, a)] for t in ('real', 'proxy', 'hold')}
    P = [A['real']['sh'] >= L['real']['sh'] and A['proxy']['sh'] >= L['proxy']['sh'], A['hold']['sh'] >= L['hold']['sh'],
         A['real']['m'] >= L['real']['m'] - 0.01 and A['proxy']['m'] >= L['proxy']['m'] - 0.01]
    bs = []
    for t in ('real', 'proxy'):
        *_, s1, s2, ps = boot(list(A[t]['r'] - A[t]['cash']), list(L[t]['r'] - L[t]['cash']), 60, seed=(sum(map(ord, a)) * 31 + len(t)) & 0xffff)
        bs.append(f"{t} [{s1:+.3f}, {s2:+.3f}] P {ps:.2f}")
    log(f"  {LAB[a]:<28} P1 {'Y' if P[0] else 'n'} (dSh {A['real']['sh']-L['real']['sh']:+.3f} / {A['proxy']['sh']-L['proxy']['sh']:+.3f})  "
        f"P2 {'Y' if P[1] else 'n'} ({A['hold']['sh']-L['hold']['sh']:+.3f})  P3 {'Y' if P[2] else 'n'} "
        f"(dDD {(A['real']['m']-L['real']['m'])*100:+.1f} / {(A['proxy']['m']-L['proxy']['m'])*100:+.1f} pp)  => {'PASS' if all(P) else 'fail'}   bootstrap {'; '.join(bs)}")
