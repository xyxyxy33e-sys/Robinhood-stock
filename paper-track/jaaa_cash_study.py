"""Owner (2026-10-30): alphaAI "also use JAAA probably as cash" -- would JAAA (Janus Henderson AAA
CLO ETF, floating rate) beat BOXX / T-bills as this design's cash leg? Research only.

PRE-REGISTERED before any run (2026-10-30, not edited after). Live design incl. the 0.5% zone buffer,
monte_carlo.py engine, VIXM out. Only the cash leg changes: engine T-bill (3m DGS3MO), BOXX total
return (from 2023-01), JAAA total return (from 2020-10). Yahoo dividend-adjusted closes.
Windows: 2020-11-02..2026-10-29 (JAAA era) and 2023-01-03..2026-10-29 (BOXX era).
JAAA replaces BOXX only if, in the BOXX-era window, Sharpe >= BOXX AND max DD no deeper than BOXX
by more than 0.5 pp, AND in the JAAA-era window Sharpe >= T-bill cash with max DD no more than 0.5 pp
deeper. Also reported: JAAA's own worst days / drawdowns and how it moved on the strategy's E/F days.
"""
import csv, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import monte_carlo as MC, state as S
LOG = open(os.path.join(HERE, 'research_notes', 'jaaa_cash_study_run.log'), 'w')
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
p = MC.load_panel('proxy'); dates = p['dates']
sig = MC.signals((100 * np.cumprod(1 + p['qqq']))[None], (100 * np.cumprod(1 + p['ew']))[None])
pr = MC.load_panel('real'); off = dates.index(pr['dates'][0]); D = pr['dates']
sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items()}
tr = {s: {r['d']: float(r['adj']) for r in csv.DictReader(open(os.path.join(MC.DATA, f'{s}_yahoo_tr.csv')))} for s in ('jaaa', 'boxx')}
def rets(px):
    out = np.full(len(D), np.nan); last = None
    for i, d in enumerate(D):
        v = px.get(d)
        if v is not None and last is not None: out[i] = v / last - 1
        if v is not None: last = v
        elif last is not None: out[i] = 0.0
    return out
CASH = {'T-bill (engine)': pr['cash'], 'BOXX': rets(tr['boxx']), 'JAAA': rets(tr['jaaa'])}
w = MC.target_weights(sr, LIVE); key = MC.regime_key(sr, LIVE); eff = MC._eff(sr, LIVE)[0]

def run(cname, d0):
    s0 = next(i for i, d in enumerate(D) if d >= d0)
    c = CASH[cname].copy(); assert not np.isnan(c[s0 + 1:]).any(), (cname, d0)
    legs = np.stack([pr['core'], pr['tqqq'], pr['qld'], pr['xlu'], c], -1)[None]
    r, n = MC.run_strategy(w, key, legs, s0); r = r[0]
    nav = np.cumprod(1 + r); dd = nav / np.maximum.accumulate(np.concatenate([[1.0], nav]))[1:] - 1
    return dict(c=nav[-1] ** (252 / len(r)) - 1, sh=r.mean() * 252 / (r.std(ddof=1) * 252 ** 0.5), m=dd.min(), a=dd.mean(),
                cashw=w[0, s0 + 1:, 4].mean())
R = {}
log('=' * 100); log('jaaa_cash_study (2026-10-30): JAAA as the cash leg? (pre-registered)'); log('=' * 100)
for d0, title in (('2020-11-02', 'JAAA era 2020-11-02..2026-10-29'), ('2023-01-03', 'BOXX era 2023-01-03..2026-10-29')):
    log(f"\n  {title}")
    log(f"  {'cash leg':<18}{'CAGR':>8}{'Sharpe':>8}{'max DD':>8}{'avg DD':>8}{'avg cash wt':>13}")
    for cn in CASH:
        if cn == 'BOXX' and d0 < '2023': continue
        x = run(cn, d0); R[(d0, cn)] = x
        log(f"  {cn:<18}{x['c']*100:7.2f}%{x['sh']:8.3f}{x['m']*100:7.1f}%{x['a']*100:7.1f}%{x['cashw']*100:12.0f}%")
log("\n  The cash instruments themselves")
for cn in CASH:
    s0 = next(i for i, d in enumerate(D) if d >= ('2023-01-03' if cn == 'BOXX' else '2020-11-02'))
    c = CASH[cn][s0 + 1:]; nav = np.cumprod(1 + c); dd = nav / np.maximum.accumulate(np.concatenate([[1.0], nav]))[1:] - 1
    yrs = sorted({d[:4] for d in D[s0 + 1:]})
    by = ', '.join(f"{y} {np.prod(1 + c[[i for i, d in enumerate(D[s0 + 1:]) if d[:4] == y]]) * 100 - 100:+.2f}%" for y in yrs)
    worst = sorted(zip(c, D[s0 + 1:]))[:3]
    log(f"  {cn:<16} max DD {dd.min()*100:.2f}%  worst days {', '.join(f'{d} {v*100:+.2f}%' for v, d in worst)}")
    log(f"  {'':<16} by year: {by}")
# JAAA on the strategy's E/F days and during the worst QQQ weeks
s0 = next(i for i, d in enumerate(D) if d >= '2020-11-02')
ef = [i for i in range(s0 + 1, len(D)) if eff[i - 1] >= 4]
j = CASH['JAAA']; t = pr['cash']
log(f"\n  On E/F days (book mostly cash), {len(ef)} days: JAAA {np.sum(j[ef])*100:+.2f}% vs T-bill {np.sum(t[ef])*100:+.2f}% (sum of daily returns)")
q = pr['qqq_tr']
worst_q = sorted(range(s0 + 1, len(D)), key=lambda i: q[i])[:10]
log("  JAAA on the 10 worst QQQ days since 2020-11: " + ', '.join(f"{D[i]} QQQ {q[i]*100:+.1f}% JAAA {j[i]*100:+.2f}%" for i in sorted(worst_q)))
log("\n  PRE-REGISTERED VERDICT")
a, b = R[('2023-01-03', 'JAAA')], R[('2023-01-03', 'BOXX')]; c_, t_ = R[('2020-11-02', 'JAAA')], R[('2020-11-02', 'T-bill (engine)')]
ok = a['sh'] >= b['sh'] and a['m'] >= b['m'] - 0.005 and c_['sh'] >= t_['sh'] and c_['m'] >= t_['m'] - 0.005
log(f"  JAAA vs BOXX (2023..): dCAGR {(a['c']-b['c'])*100:+.2f} pp, dSh {a['sh']-b['sh']:+.3f}, dDD {(a['m']-b['m'])*100:+.2f} pp; "
    f"vs T-bill (2020-11..): dCAGR {(c_['c']-t_['c'])*100:+.2f} pp, dSh {c_['sh']-t_['sh']:+.3f}, dDD {(c_['m']-t_['m'])*100:+.2f} pp  => {'PASS' if ok else 'fail'}")
