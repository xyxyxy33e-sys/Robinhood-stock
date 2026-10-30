"""Owner (2026-10-30), two more alphaAI marketplace strategies (screenshots; both 2026 tabs stop at Feb):
  Gold Rush:  GLD GDX GDXJ SLV BIL; all 5 held, ranked by 21-period RSI, weights by relative trend
              strength; quarterly rebalance (first trading day); 100% cash when the top-ranked assets
              show a negative 12-month return. Shown: max DD -33.8%, Sharpe 0.86.
  World Tour: SPY EWJ EWG EWU EWT EWY EWZ INDA FXI EEM; top 5 of 10 ranked by 200-day EMA; weights by
              relative trend strength; weekly rebalance (first trading day); "m2 AI" 2-state cash overlay.
Research only.

PRE-REGISTERED before any run (2026-10-30, not edited after). Yahoo total-return closes.
  Gold Rush replica: Wilder RSI(21) on daily closes; weights proportional to RSI across all 5; if the
    highest-RSI asset's 252-session return < 0 -> 100% BIL; trades at the close of the first session of
    Jan/Apr/Jul/Oct.
  World Tour replica: score = close / EMA(200) - 1; top 5 by score; weights proportional to max(score, 0);
    stand-in for the unpublished overlay: a top-5 asset with score <= 0 has its weight in cash (BIL);
    trades at the close of the first session of each week.
Costs 4 and 20 bp per side. Windows: Gold 2010-12-01..2026-10-29 (GDXJ + 1y), World 2013-01-02..
2026-10-29 (INDA + 200d). Blend test, 2015-11-02..2026-10-29: 80% live design (engine, zone buffer,
VIXM out) + 20% sleeve, rebalanced to 80/20 on the first session of each month (cost on the
transfer). A sleeve is worth adding only if the 80/20 blend has Sharpe >= 100% live at 4 AND 20 bp
and max DD no more than 1 pp deeper.
"""
import csv, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import monte_carlo as MC, state as S
LOG = open(os.path.join(HERE, 'research_notes', 'gold_world_sleeve_study_run.log'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); LOG.write(s + '\n'); LOG.flush()
GOLD = ['GLD', 'GDX', 'GDXJ', 'SLV', 'BIL']
WORLD = ['SPY', 'EWJ', 'EWG', 'EWU', 'EWT', 'EWY', 'EWZ', 'INDA', 'FXI', 'EEM']
adj = {s: {r['d']: float(r['adj']) for r in csv.DictReader(open(os.path.join(MC.DATA, f'{s.lower()}_yahoo_tr.csv')))}
       for s in set(GOLD + WORLD)}
D = sorted(d for d in adj['SPY'] if d >= '2007-06-01')
T = len(D)
def series(s):
    a = np.array([adj[s].get(d, np.nan) for d in D])
    for i in range(1, T):
        if np.isnan(a[i]) and not np.isnan(a[i - 1]): a[i] = a[i - 1]
    return a
PX = {s: series(s) for s in set(GOLD + WORLD)}
RET = {s: np.nan_to_num(np.concatenate([[0.0], PX[s][1:] / PX[s][:-1] - 1])) for s in PX}

def rsi(a, n=21):
    out = np.full(T, np.nan); d = np.diff(a); g = np.where(d > 0, d, 0.0); l = np.where(d < 0, -d, 0.0)
    ag = al = None; k = 0
    for i in range(1, T):
        if np.isnan(d[i - 1]): continue
        k += 1
        if k < n: continue
        if ag is None:
            ag, al = np.nanmean(g[i - n:i]), np.nanmean(l[i - n:i])
        else:
            ag = (ag * (n - 1) + g[i - 1]) / n; al = (al * (n - 1) + l[i - 1]) / n
        out[i] = 100 - 100 / (1 + ag / al) if al > 0 else 100.0
    return out
def ema(a, n=200):
    out = np.full(T, np.nan); k = 2 / (n + 1); e = None; c = 0
    for i in range(T):
        if np.isnan(a[i]): continue
        e = a[i] if e is None else a[i] * k + e * (1 - k); c += 1
        if c >= n: out[i] = e
    return out
RSI = {s: rsi(PX[s]) for s in GOLD}; EMA = {s: ema(PX[s]) for s in WORLD}

def sim(names, rebal_day, target_fn, cost):
    out = np.zeros(T); h = None
    for t in range(1, T):
        if h is not None:
            rr = np.array([RET[s][t] for s in names]); g = (h * rr).sum(); out[t] = g
            h = h * (1 + rr) / (1 + g)
        if rebal_day(t):
            w = target_fn(t)
            if w is not None:
                l1 = np.abs(w - (h if h is not None else 0)).sum()
                out[t] = (1 + out[t]) * (1 - cost * l1) - 1; h = w
    return out

def gold_target(t):
    if any(np.isnan(RSI[s][t]) for s in GOLD) or t < 252 or any(np.isnan(PX[s][t - 252]) for s in GOLD): return None
    r = np.array([RSI[s][t] for s in GOLD]); top = GOLD[int(np.argmax(r))]
    if PX[top][t] / PX[top][t - 252] - 1 < 0:
        w = np.zeros(5); w[GOLD.index('BIL')] = 1.0; return w
    return r / r.sum()
def world_target(t):
    sc = {s: PX[s][t] / EMA[s][t] - 1 for s in WORLD if not np.isnan(EMA[s][t])}
    if len(sc) < 10: return None
    top = sorted(sc, key=lambda s: -sc[s])[:5]
    w = np.zeros(11); pos = {s: max(sc[s], 0) for s in top}; tot = sum(pos.values())
    if tot > 0:
        for s in top: w[WORLD.index(s)] = pos[s] / tot * (1 if sc[s] > 0 else 0)
    w[10] = 1 - w[:10].sum(); return w
qstart = lambda t: D[t][:7] != D[t - 1][:7] and D[t][5:7] in ('01', '04', '07', '10')
import datetime as dt
wstart = lambda t: dt.date.fromisoformat(D[t]).isocalendar()[1] != dt.date.fromisoformat(D[t - 1]).isocalendar()[1]
RET['_BIL'] = RET['BIL']

def stats(r):
    nav = np.cumprod(1 + r); dd = nav / np.maximum.accumulate(np.concatenate([[1.0], nav]))[1:] - 1; v = r.std(ddof=1) * 252 ** 0.5
    return dict(c=nav[-1] ** (252 / len(r)) - 1, sh=r.mean() * 252 / v, m=dd.min(), v=v)
log('=' * 100); log('gold_world_sleeve_study (2026-10-30): Gold Rush / World Tour replicas (pre-registered)'); log('=' * 100)
SL = {}
for bp in (4, 20):
    g = sim(GOLD, qstart, gold_target, bp / 1e4)
    w = sim(WORLD + ['_BIL'], wstart, world_target, bp / 1e4)
    SL[(bp, 'gold')], SL[(bp, 'world')] = g, w
    for nm, r, d0, bench in (('Gold Rush replica', g, '2010-12-01', 'GLD'), ('World Tour replica', w, '2013-01-02', 'EEM')):
        s0 = D.index(next(d for d in D if d >= d0)); x = stats(r[s0 + 1:]); b = stats(RET[bench][s0 + 1:]); sp = stats(RET['SPY'][s0 + 1:])
        log(f"  {bp:>2} bp  {nm:<20} {D[s0]}..{D[-1]}: {x['c']*100:6.2f}% / Sh {x['sh']:.2f} / maxDD {x['m']*100:6.1f}% / vol {x['v']*100:.1f}%"
            + (f"   | hold {bench} {b['c']*100:.2f}% / {b['sh']:.2f} / {b['m']*100:.1f}%; SPY {sp['c']*100:.2f}% / {sp['sh']:.2f} / {sp['m']*100:.1f}%" if bp == 4 else ''))
for nm in ('gold', 'world'):
    r = SL[(4, nm)]
    log(f"  {nm} 2026 by month: " + ' '.join(f"{m}:{(np.prod(1 + r[[i for i, d in enumerate(D) if d[:7] == f'2026-{m:02d}']]) - 1)*100:+.1f}" for m in range(1, 11))
        + "   by year: " + ' '.join(f"{y}:{(np.prod(1 + r[[i for i, d in enumerate(D) if d[:4] == y]]) - 1)*100:+.0f}" for y in sorted({d[:4] for d in D if d >= '2011'})))

# blend with the live design
LC = list(csv.DictReader(open(os.path.join(MC.DATA, 'live_closes.csv'))))
EXT = {'qqq_long_history.csv': 'QQQ', 'QQEW_daily_ext.csv': 'QQEW', 'spmo_ohlc.csv': 'SPMO', 'tqqq_ohlc.csv': 'TQQQ', 'qld_ohlc.csv': 'QLD', 'xlu_ohlc.csv': 'XLU'}
_o = MC._load
def _l(name, dcol='d', ccol='c'):
    out = _o(name, dcol, ccol)
    if name in EXT or name == 'spy_long_history.csv':
        last = max(out); v = out[last]
        for r in LC:
            if r['date'] > last:
                if name in EXT and r[EXT[name]]: out[r['date']] = float(r[EXT[name]])
                elif name not in EXT: out[r['date']] = v
    return out
MC._load = _l
LIVE = dict(MC.LIVE, a_base=(0.40, 0.60), vol='max10_30', d_buffer=S.D_ZONE_BUFFER)
p = MC.load_panel('proxy'); PD = p['dates']
sig = MC.signals((100 * np.cumprod(1 + p['qqq']))[None], (100 * np.cumprod(1 + p['ew']))[None])
pr = MC.load_panel('real'); RD = pr['dates']; off = PD.index(RD[0])
sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items() if not isinstance(k, tuple)}
w = MC.target_weights(sr, LIVE); key = MC.regime_key(sr, LIVE)
s0 = next(i for i, d in enumerate(RD) if d >= '2015-11-02')
log("\n  BLEND: 80% live design + 20% sleeve, monthly back to 80/20, real 2015-11..2026-10")
BL = {}
for bp in (4, 20):
    MC.COST = bp / 1e4
    legs = np.stack([pr['core'], pr['tqqq'], pr['qld'], pr['xlu'], pr['cash']], -1)[None]
    live = MC.run_strategy(w, key, legs, s0)[0][0]; ds = RD[s0 + 1:]
    idx = {d: i for i, d in enumerate(D)}
    x0 = stats(live); BL[(bp, 'live')] = x0
    log(f"  {bp:>2} bp  100% live            {x0['c']*100:6.2f}% / Sh {x0['sh']:.3f} / maxDD {x0['m']*100:6.1f}%")
    for nm in ('gold', 'world'):
        sl = np.array([SL[(bp, nm)][idx[d]] if d in idx else 0.0 for d in ds])
        a, b = 0.8, 0.2; out = np.zeros(len(ds))
        for t in range(len(ds)):
            gt = a * live[t] + b * sl[t]; out[t] = gt
            a, b = a * (1 + live[t]) / (1 + gt), b * (1 + sl[t]) / (1 + gt)
            if t + 1 < len(ds) and ds[t + 1][:7] != ds[t][:7]:
                out[t] = (1 + out[t]) * (1 - MC.COST * 2 * abs(a - 0.8)) - 1; a, b = 0.8, 0.2
        x = stats(out); BL[(bp, nm)] = x
        corr = np.corrcoef(live, sl)[0, 1]
        log(f"  {bp:>2} bp  80/20 with {nm:<6}    {x['c']*100:6.2f}% / Sh {x['sh']:.3f} / maxDD {x['m']*100:6.1f}%   (daily corr with live {corr:+.2f})")
MC.COST = 0.0004
log("\n  PRE-REGISTERED VERDICT")
for nm in ('gold', 'world'):
    ok = all(BL[(bp, nm)]['sh'] >= BL[(bp, 'live')]['sh'] for bp in (4, 20)) and BL[(4, nm)]['m'] >= BL[(4, 'live')]['m'] - 0.01
    log(f"  20% {nm} sleeve: dSh {BL[(4, nm)]['sh']-BL[(4, 'live')]['sh']:+.3f} (4bp) / {BL[(20, nm)]['sh']-BL[(20, 'live')]['sh']:+.3f} (20bp), "
        f"dCAGR {(BL[(4, nm)]['c']-BL[(4, 'live')]['c'])*100:+.1f} pp, dDD {(BL[(4, nm)]['m']-BL[(4, 'live')]['m'])*100:+.1f} pp  => {'PASS' if ok else 'fail'}")
