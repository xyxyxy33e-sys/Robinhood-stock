"""Owner (2026-10-30), from an alphaAI strategy page: "Universe SPY QQQ VGT MGK VUG IWF MTUM QUAL SOXX;
top 6 of 9 by 12-month momentum; weights scaled by relative trend strength; monthly rebalance on the
first trading day; defensive overlay: 'm7 AI model' sets cash across 4 states". "Test this". Research only.

PRE-REGISTERED before any run (2026-10-30, not edited after). Yahoo dividend-adjusted closes
(data/*_yahoo_tr.csv). Momentum = total return over the last 252 sessions, read at the close of the
first trading day of each month; trades at that close; holdings drift inside the month. Cost per side
4 bp and 20 bp on every rebalance. The alphaAI overlay is not published, so:
  ROT-EW    top 6 equal weight, always invested
  ROT-MW    top 6 weighted by 12-month return (negatives floored at 0; all <= 0 -> equal weight)
  ROT-OVL   ROT-MW with this repo's QQQ state as the cash overlay, applied daily: cash 0% in
            A/B/C and ungated D, 50% in gated D and E, 100% in F (cash = 3m T-bill)
  LIVE-ROT  the live design (incl. zone buffer, VIXM out) with ROT-MW as its core instead of SPMO
Windows: W1 2015-11-02..2026-10-29 (SPMO era: standalone + core swap);
         W2 2005-03-01..2026-10-29 (standalone only; before an ETF has 252 sessions it is left out and
         the strategy holds the top round(2/3 x available)).
Benchmarks: SPY, QQQ, SPMO (W1), equal-weight of the universe (monthly).
Verdicts: (a) as a standalone, compared with SPY/QQQ/SPMO -- reported, no gate;
(b) LIVE-ROT replaces SPMO only if its Sharpe >= live on W1 at 4 AND 20 bp and its max DD is no more
than 1 pp deeper.
"""
import csv, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import monte_carlo as MC, state as S
LOG = open(os.path.join(HERE, 'research_notes', 'momentum_rotation_study_run.log'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); LOG.write(s + '\n'); LOG.flush()
U = ['SPY', 'QQQ', 'VGT', 'MGK', 'VUG', 'IWF', 'MTUM', 'QUAL', 'SOXX']
adj = {s: {r['d']: float(r['adj']) for r in csv.DictReader(open(os.path.join(MC.DATA, f'{s.lower()}_yahoo_tr.csv')))} for s in U + ['SPMO']}

# engine panels (extended with live closes, as the other 2026-10-30 studies)
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
p = MC.load_panel('proxy'); PD = p['dates']
sig = MC.signals((100 * np.cumprod(1 + p['qqq']))[None], (100 * np.cumprod(1 + p['ew']))[None])
LIVE = dict(MC.LIVE, a_base=(0.40, 0.60), vol='max10_30', d_buffer=S.D_ZONE_BUFFER)
eff = MC._eff(sig, LIVE)[0]; gate = MC._gate(sig, LIVE)[0]
ovl_cash = np.where(eff == 5, 1.0, np.where((eff == 4) | ((eff == 3) & gate), 0.5, 0.0))
OVL = dict(zip(PD, ovl_cash)); CASHR = dict(zip(PD, p['cash']))

def rotation(D, mode, cost, overlay=False):
    """Daily net returns of the rotation on dates D (first entry = 0)."""
    T = len(D); px = {s: np.array([adj[s].get(d, np.nan) for d in D]) for s in U}
    for s in U:                                        # forward-fill holes inside an ETF's life
        a = px[s]
        for i in range(1, T):
            if np.isnan(a[i]) and not np.isnan(a[i - 1]): a[i] = a[i - 1]
    r = {s: np.concatenate([[0.0], px[s][1:] / px[s][:-1] - 1]) for s in U}
    out = np.zeros(T); h = np.zeros(len(U)); hc = 1.0; tgt_risk = None
    for t in range(1, T):
        rr = np.array([0.0 if np.isnan(r[s][t]) else r[s][t] for s in U])
        g = (h * rr).sum() + hc * CASHR.get(D[t], 0.0)
        tot = h.sum() + hc
        out[t] = g / tot if tot > 0 else 0.0
        h = h * (1 + rr); hc = hc * (1 + CASHR.get(D[t], 0.0)); n = h.sum() + hc; h, hc = h / n, hc / n
        month_start = D[t][:7] != D[t - 1][:7]
        if month_start:
            mom = np.array([px[s][t] / px[s][t - 252] - 1 if t >= 252 and not np.isnan(px[s][t - 252]) else np.nan for s in U])
            ok = [i for i in range(len(U)) if not np.isnan(mom[i])]
            if ok:
                k = 6 if len(ok) == 9 else max(1, round(len(ok) * 2 / 3))
                top = sorted(ok, key=lambda i: -mom[i])[:k]
                w = np.zeros(len(U))
                if mode == 'EW' or all(mom[i] <= 0 for i in top):
                    w[top] = 1 / k
                else:
                    m = np.array([max(mom[i], 0) for i in top]); w[top] = m / m.sum()
                tgt_risk = w
        if tgt_risk is None:
            continue
        c = OVL.get(D[t], 0.0) if overlay else 0.0
        want = tgt_risk * (1 - c)
        if month_start or (overlay and abs((h.sum()) - (1 - c)) > 0.25):
            l1 = np.abs(want - h).sum() + abs((1 - want.sum()) - hc)
            out[t] = (1 + out[t]) * (1 - cost * l1) - 1
            h = want.copy(); hc = 1 - want.sum()
    return out

def stats(r, cash):
    nav = np.cumprod(1 + r); dd = nav / np.maximum.accumulate(np.concatenate([[1.0], nav]))[1:] - 1
    v = r.std(ddof=1) * 252 ** 0.5
    return dict(c=nav[-1] ** (252 / len(r)) - 1, sh=r.mean() * 252 / v, ex=(r - cash).mean() * 252 / v, m=dd.min(), a=dd.mean(), v=v)

def tr(sym, D):
    a = np.array([adj[sym].get(d, np.nan) for d in D])
    for i in range(1, len(a)):
        if np.isnan(a[i]): a[i] = a[i - 1]
    return np.concatenate([[0.0], a[1:] / a[:-1] - 1])

log('=' * 104); log('momentum_rotation_study (2026-10-30): alphaAI-style 6-of-9 momentum rotation (pre-registered)'); log('=' * 104)
RES = {}
for bp in (4, 20):
    for wn, d0 in (('W1', '2015-11-02'), ('W2', '2005-03-01')):
        D = [d for d in PD if d >= ('2004-02-01' if wn == 'W2' else '2014-10-01') and d in adj['SPY']]
        s0 = D.index(next(d for d in D if d >= d0))
        cash = np.array([CASHR[d] for d in D])[s0 + 1:]
        log(f"\n  {wn} {D[s0]}..{D[-1]}  cost {bp} bp per side   (CAGR / Sharpe / max DD / avg DD / vol)")
        rows = [('ROT-EW', rotation(D, 'EW', bp / 1e4)), ('ROT-MW', rotation(D, 'MW', bp / 1e4)),
                ('ROT-OVL', rotation(D, 'MW', bp / 1e4, overlay=True))]
        if bp == 4:
            rows += [('hold SPY', tr('SPY', D)), ('hold QQQ', tr('QQQ', D))] + ([('hold SPMO', tr('SPMO', D))] if wn == 'W1' else [])
        for nm, r in rows:
            x = stats(r[s0 + 1:], cash); RES[(bp, wn, nm)] = (x, r, D, s0)
            log(f"  {nm:<12}{x['c']*100:8.2f}%{x['sh']:8.3f}{x['m']*100:8.1f}%{x['a']*100:7.1f}%{x['v']*100:7.1f}%")
# 2026 by month, ROT-MW and ROT-OVL (W1, 4 bp)
for nm in ('ROT-MW', 'ROT-OVL'):
    x, r, D, s0 = RES[(4, 'W1', nm)]
    ms = [f"{m}:{(np.prod(1 + r[[i for i, d in enumerate(D) if d[:7] == f'2026-{m:02d}']]) - 1)*100:+.1f}" for m in range(1, 11)]
    ytd = np.prod(1 + r[[i for i, d in enumerate(D) if d[:4] == '2026']]) - 1
    log(f"  2026 {nm}: {' '.join(ms)}  YTD {ytd*100:+.1f}%")
for nm in ('ROT-MW', 'ROT-OVL', 'hold QQQ'):
    x, r, D, s0 = RES[(4, 'W2', nm)]
    log(f"  {nm} by year: " + ' '.join(f"{y}:{(np.prod(1 + r[[i for i, d in enumerate(D) if d[:4] == y and i > s0]]) - 1)*100:+.0f}" for y in sorted({d[:4] for d in D[s0 + 1:]})))

# core swap inside the live design (real panel)
pr = MC.load_panel('real'); RD = pr['dates']; off = PD.index(RD[0])
sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items() if not isinstance(k, tuple)}
w = MC.target_weights(sr, LIVE); key = MC.regime_key(sr, LIVE)
s0 = next(i for i, d in enumerate(RD) if d >= '2015-11-02')
log("\n  CORE SWAP inside the live design, real ETFs 2015-11..2026-10 (core total return in both arms)")
CS = {}
for bp in (4, 20):
    MC.COST = bp / 1e4
    Drot = [d for d in PD if d >= '2014-10-01' and d in adj['SPY']]
    rot = dict(zip(Drot, rotation(Drot, 'MW', bp / 1e4)))
    cores = {'SPMO (live)': tr('SPMO', RD), 'ROT-MW core': np.array([rot.get(d, 0.0) for d in RD])}
    for nm, core in cores.items():
        legs = np.stack([core, pr['tqqq'], pr['qld'], pr['xlu'], pr['cash']], -1)[None]
        r, n = MC.run_strategy(w, key, legs, s0); r = r[0]
        x = stats(r, pr['cash'][s0 + 1:]); CS[(bp, nm)] = x
        log(f"  {bp:>2} bp  {nm:<14}{x['c']*100:8.2f}%{x['sh']:8.3f}{x['m']*100:8.1f}%{x['a']*100:7.1f}%")
MC.COST = 0.0004
a4, l4, a20, l20 = CS[(4, 'ROT-MW core')], CS[(4, 'SPMO (live)')], CS[(20, 'ROT-MW core')], CS[(20, 'SPMO (live)')]
ok = a4['sh'] >= l4['sh'] and a20['sh'] >= l20['sh'] and a4['m'] >= l4['m'] - 0.01
log(f"\n  PRE-REGISTERED VERDICT (b) core swap: dSh {a4['sh']-l4['sh']:+.3f} (4bp) / {a20['sh']-l20['sh']:+.3f} (20bp), "
    f"dDD {(a4['m']-l4['m'])*100:+.1f} pp  => {'PASS' if ok else 'fail'}")
