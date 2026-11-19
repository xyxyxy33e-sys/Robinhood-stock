"""Pre-committed scale-down / stop rules for the live strategy (2026-11-19, owner request).

PRE-REGISTERED candidate rules, applied as an overlay on the full-size strategy's daily returns (the strategy keeps
running underneath at full size; the overlay sets the account's share in it, the rest earns cash; switching costs
2bp on the switched share):
  none        always 100%
  DD30 half   strategy drawdown <= -30% -> 50% until the strategy is back above -15% from its peak
  DD40 half   same at -40% / back above -20%
  DD30 out    strategy drawdown <= -30% -> 0% until a new strategy high
  DD50 stop   strategy drawdown <= -50% -> 0% for good
  REL25 half  trailing 12-month return behind QQQ by more than 25 pp -> 50% until the 12-month gap is back >= 0
Worlds: mc_study generators, 500 x 10y paths: bootstrap holdout and proxy at blocks 60 / 120 (with and without the
crash), random walk, regimes with mean bear 125. Plus single historical paths (real 2015-26, proxy 2001-26).
Report per rule: median and 5th-pct CAGR, median and 5th-pct max drawdown, P(rule fires within 10y).
"""
import sys, os, json, warnings; warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..')); sys.path.insert(1, os.path.join(HERE, '..', 'mc_2026_11'))
import numpy as np
import monte_carlo as MC
import mc_study as M

RULES = ['none', 'DD30 half', 'DD40 half', 'DD30 out', 'DD50 stop', 'REL25 half']
def overlay(r, q, cash, rule):
    """r, q, cash: (P, n) daily returns of the full-size strategy, QQQ, cash. Returns account returns and fired flags."""
    P, n = r.shape
    if rule == 'none': return r, np.zeros(P, bool)
    nav = np.cumprod(1 + r, 1); peak = np.maximum.accumulate(nav, 1); dd = nav / peak - 1
    lq = np.log1p(q).cumsum(1); lr = np.log1p(r).cumsum(1)
    share = np.ones(P); out = np.zeros_like(r); fired = np.zeros(P, bool); stopped = np.zeros(P, bool); prev = np.ones(P)
    for t in range(n):
        out[:, t] = share * r[:, t] + (1 - share) * cash[:, t] - 0.0002 * np.abs(share - prev)
        prev = share.copy()
        d = dd[:, t]
        if rule in ('DD30 half', 'DD40 half'):
            lo, hi = (-0.30, -0.15) if rule == 'DD30 half' else (-0.40, -0.20)
            share = np.where(d <= lo, 0.5, np.where(d > hi, 1.0, share))
        elif rule == 'DD30 out':
            share = np.where(d <= -0.30, 0.0, np.where(d >= 0, 1.0, share))
        elif rule == 'DD50 stop':
            stopped |= d <= -0.50; share = np.where(stopped, 0.0, 1.0)
        elif rule == 'REL25 half' and t >= 252:
            gap = (np.expm1(lr[:, t] - lr[:, t - 252]) - np.expm1(lq[:, t] - lq[:, t - 252]))
            share = np.where(gap < -0.25, 0.5, np.where(gap >= 0, 1.0, share))
        fired |= share < 1
    return out, fired

def strat_returns(g):
    qpx = 100 * np.cumprod(1 + g['qqq'], 1); ewpx = 100 * np.cumprod(1 + g['ew'], 1)
    sig = MC.signals(qpx, ewpx); legs = np.stack([g['core'], g['tqqq'], g['qld'], g['xlu'], g['cash']], -1)
    r, _ = MC.run_strategy(MC.target_weights(sig, M.CUR), MC.regime_key(sig, M.CUR), legs, MC.WARMUP)
    sl = slice(MC.WARMUP + 1, M.T)
    return r, g['qqq_tr'][:, sl], g['cash'][:, sl]

res = {}
def cell(lab, g):
    r, q, c = strat_returns(g); res[lab] = {}
    for rule in RULES:
        a, f = overlay(r, q, c, rule); s = MC.stats(a, c)
        res[lab][rule] = dict(med=float(np.median(s['cagr'])), p5=float(np.percentile(s['cagr'], 5)),
                              mdd=float(np.median(s['mdd'])), mdd5=float(np.percentile(s['mdd'], 5)), fired=float(f.mean()))
    print('done', lab, flush=True)
for kind in ('holdout', 'proxy'):
    panel = MC.load_panel(kind); src = np.arange(1, len(panel['dates']))
    for Lb in (60, 120):
        g = M.from_index(panel, src[MC.bootstrap_idx(np.random.default_rng(20261119 + Lb), len(src), M.P, M.T, Lb)])
        cell(f'{kind} L{Lb}', g); cell(f'{kind} L{Lb} +crash', M.add_crash(g, np.random.default_rng(9)))
cell('random walk', M.world_random_walk(np.random.default_rng(1)))
cell('regimes bear125', M.world_regimes(np.random.default_rng(225), 125))
# historical single paths
for kind, d0 in (('real', '2015-11-02'), ('proxy', '2001-01-02')):
    panel = MC.load_panel(kind); ds = panel['dates']
    qpx = 100 * np.cumprod(1 + panel['qqq']); ewpx = 100 * np.cumprod(1 + panel['ew'])
    sig = MC.signals(qpx[None], ewpx[None]); legs = np.stack([panel[k] for k in ('core', 'tqqq', 'qld', 'xlu', 'cash')], -1)[None]
    s0 = next(i for i, d in enumerate(ds) if d >= d0)
    r, _ = MC.run_strategy(MC.target_weights(sig, M.CUR), MC.regime_key(sig, M.CUR), legs, s0)
    q = panel['qqq_tr'][None, s0 + 1:]; c = panel['cash'][None, s0 + 1:]
    res[f'history {kind}'] = {}
    for rule in RULES:
        a, f = overlay(r, q, c, rule); s = MC.stats(a, c)
        res[f'history {kind}'][rule] = dict(med=float(s['cagr'][0]), p5=float('nan'), mdd=float(s['mdd'][0]), mdd5=float('nan'), fired=float(f[0]))
json.dump(res, open(os.path.join(HERE, 'stop_rules.json'), 'w'), indent=1)
with open(os.path.join(HERE, 'stop_rules_run.log'), 'w') as fh:
    for lab, rows in res.items():
        fh.write(f"\n## {lab}\n{'rule':12s}{'medCAGR':>9}{'p5CAGR':>9}{'medDD':>8}{'p5DD':>8}{'fires':>7}\n")
        for rule, x in rows.items():
            fh.write(f"{rule:12s}{x['med']*100:8.1f}%{x['p5']*100:8.1f}%{x['mdd']*100:7.0f}%{x['mdd5']*100:7.0f}%{x['fired']*100:6.0f}%\n")
print(open(os.path.join(HERE, 'stop_rules_run.log')).read())
