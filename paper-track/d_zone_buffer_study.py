"""Owner (2026-10-29), after the D1<->D2 flips of 16-29 Oct 2026 (A->D2 16 Oct, D1 21 Oct, D2 22 Oct,
D1 27 Oct, D2 29 Oct; each flip swaps ~40% of the account between SPMO and TQQQ): hold SPMO longer
through a zone shift (not in E/F). Research only.

PRE-REGISTERED before any run (2026-10-29, not edited after). Base = live design (monte_carlo.py,
VIXM left out). The ladder zone is read from QQQ's gap to its 100d (D1/D2 line) and 150d (D2/D3
line) averages. Arms change only how the zone moves on effective-D days; the zone memory starts
fresh from the plain zone on the first D day after a non-D day; E/F/gate/A/B/C are untouched.
  SB0.5 / SB1 / SB2  symmetric buffer of b = 0.5 / 1 / 2 % on both lines: move one zone deeper
                     only when the gap is below -b, back up only when it is above +b; else stay.
  AS1 / AS2          SPMO-favouring: leave D1 for D2 only when gap100 < -b (b = 1 / 2 %); back to
                     D1 as soon as gap100 > 0 (plain); the 150d line plain.
  DW3                confirmation: the zone changes only after 3 consecutive closes in the new zone.
Every arm at 4 bp and 20 bp per side. Pass rules as spmo_hold_study.py: P1 Sharpe >= live on real
AND proxy (4 bp); P2 holdout Sharpe >= live; P3 max DD no more than 1.0 pp deeper on either panel;
P4 P1 again at 20 bp. Also reported: D zone changes per year; and the 15 Oct -> 29 Oct 2026 return.
"""
import csv, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import monte_carlo as MC, state as S
from block_bootstrap import boot
LOG = open(os.path.join(HERE, 'research_notes', 'd_zone_buffer_study_run.log'), 'w')
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
assert S.D_LADDER_WINDOWS == (100, 150)
p = MC.load_panel('proxy'); dates = p['dates']
sig = MC.signals((100 * np.cumprod(1 + p['qqq']))[None], (100 * np.cumprod(1 + p['ew']))[None])
pr = MC.load_panel('real'); off = dates.index(pr['dates'][0])
sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items()}

def zone_path(sg, arm):
    eff = MC._eff(sg, LIVE)[0]; g1 = sg['gaps'][100][0]; g2 = sg['gaps'][150][0]; raw = sg['zone'][0]
    if arm == 'live': return raw.copy()
    z = raw.copy(); cur = None; pend = None; cnt = 0
    for t in range(len(raw)):
        if eff[t] != 3 or np.isnan(g1[t]) or np.isnan(g2[t]):
            cur = None; continue
        if cur is None:
            cur = int(raw[t]); pend = None; cnt = 0; z[t] = cur; continue
        if arm.startswith('SB'):
            b = float(arm[2:]) / 100
            up1, dn1, up2, dn2 = b, -b, b, -b
        elif arm.startswith('AS'):
            b = float(arm[2:]) / 100
            up1, dn1, up2, dn2 = 0.0, -b, 0.0, 0.0
        if arm.startswith(('SB', 'AS')):
            if cur == 1 and g1[t] < dn1: cur = 3 if g2[t] < dn2 else 2
            elif cur == 2 and g1[t] > up1: cur = 1
            elif cur == 2 and g2[t] < dn2: cur = 3
            elif cur == 3 and g2[t] > up2: cur = 1 if g1[t] > up1 else 2
        elif arm == 'DW3':
            r = int(raw[t])
            if r == cur: pend = None; cnt = 0
            else:
                cnt = cnt + 1 if r == pend else 1; pend = r
                if cnt >= 3: cur = r; pend = None; cnt = 0
        z[t] = cur
    return z

def run(sg, pn, d0, arm, d1='2099', window=None):
    ds = pn['dates']; s0 = next(i for i, d in enumerate(ds) if d >= d0); e = max(i for i, d in enumerate(ds) if d <= d1)
    sg = {k: (v[:, :e + 1] if not isinstance(v, dict) else {n: a[:, :e + 1] for n, a in v.items()}) for k, v in sg.items()}
    sg = dict(sg, zone=zone_path(sg, arm)[None])
    w = MC.target_weights(sg, LIVE); key = MC.regime_key(sg, LIVE)
    legs = np.stack([pn['core'], pn['tqqq'], pn['qld'], pn['xlu'], pn['cash']], -1)[None][:, :e + 1]
    r, tr = MC.run_strategy(w, key, legs, s0); r = r[0]
    nav = np.cumprod(1 + r); dd = nav / np.maximum.accumulate(np.concatenate([[1.0], nav]))[1:] - 1
    yrs = (e - s0) / 252; eff = MC._eff(sg, LIVE)[0]; gate = MC._gate(sg, LIVE)[0]
    dz = np.where((eff == 3) & ~gate, sg['zone'][0], 0)[s0:e + 1]
    flips = ((dz[1:] != dz[:-1]) & (dz[1:] > 0) & (dz[:-1] > 0)).sum()
    out = dict(r=r, c=nav[-1] ** (252 / len(r)) - 1, sh=r.mean() * 252 / (r.std(ddof=1) * 252 ** 0.5), m=dd.min(),
               a=dd.mean(), tpy=tr[0] / yrs, fl=flips / yrs, cash=pn['cash'][s0 + 1:e + 1], days=ds[s0 + 1:e + 1])
    if window:
        i0 = ds.index(window[0]) - s0; i1 = ds.index(window[1]) - s0      # return from close w0 to close w1
        out['win'] = np.prod(1 + r[i0:i1]) - 1
        out['path'] = [(ds[s0 + 1 + i], int(dz[i + 1]), w[0, s0 + 1 + i, 0]) for i in range(i0, i1)]
    return out

ARMS = ['live', 'SB0.5', 'SB1', 'SB2', 'AS1', 'AS2', 'DW3']
LAB = {'live': 'live design', 'SB0.5': 'buffer 0.5% both ways', 'SB1': 'buffer 1% both ways', 'SB2': 'buffer 2% both ways',
       'AS1': 'stay D1 to gap100 -1%', 'AS2': 'stay D1 to gap100 -2%', 'DW3': '3-close confirmation'}
WIN = ('2026-10-15', '2026-10-29')
PAN = [('real', sr, pr, '2015-11-02', '2099', 'REAL ETFs (extended with live closes)'),
       ('proxy', sig, p, '2001-01-02', '2099', 'PROXY 2001.. (core = QQQ)'),
       ('hold', sig, p, '2001-01-02', '2015-10-31', 'HOLDOUT 2001..2015-10 (proxy)')]
R = {}
log('=' * 118); log('d_zone_buffer_study (2026-10-29): stop D1<->D2 flip-flops? (pre-registered)'); log('=' * 118)
for bp in (4, 20):
    MC.COST = bp / 1e4
    for tag, sg, pn, d0, d1, title in PAN:
        for a in ARMS: R[(bp, tag, a)] = run(sg, pn, d0, a, d1, WIN if tag == 'real' else None)
        x = R[(bp, tag, 'live')]
        log(f"\n  {title}  {x['days'][0]}..{x['days'][-1]}   cost {bp} bp per side")
        log(f"  {'arm':<26}{'CAGR':>8}{'Sharpe':>8}{'max DD':>8}{'avg DD':>8}{'trades/yr':>10}{'D zone chg/yr':>14}" + ("   15-29 Oct" if tag == 'real' else ''))
        for a in ARMS:
            x = R[(bp, tag, a)]
            log(f"  {LAB[a]:<26}{x['c']*100:7.2f}%{x['sh']:8.3f}{x['m']*100:7.1f}%{x['a']*100:7.1f}%{x['tpy']:10.0f}{x['fl']:14.1f}"
                + (f"{x['win']*100:11.2f}%" if 'win' in x else ''))
MC.COST = 0.0004
log("\n  15-29 Oct 2026 zone path (D zone, SPMO weight) per arm, 4 bp")
for a in ARMS:
    log(f"  {LAB[a]:<26}" + ' '.join(f"{d[5:]}:D{z}/{s*100:.0f}" if z else f"{d[5:]}:-/{s*100:.0f}" for d, z, s in R[(4, 'real', a)]['path']))
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
