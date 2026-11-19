"""Monte Carlo study of the current design vs simpler versions (2026-11-19, owner request).

PRE-REGISTERED (written before the first run, not tuned after):
DESIGNS (monte_carlo.py engine; VIXY sleeve and the deep-E / VIX-panic QQQ cash legs are NOT modelled):
  current  = A 40/60 + trim v2, B 50/50, C core, D ladder + gate + 0.5% zone buffer, E/F cash,
             max(10d,30d) vol target 20%, gross cap 2.0, 5% band, 2bp
  no-trim  = current without the extension trim
  bare     = six state rows + vol target + cap (no trim, gate, ladder, fast re-entry)
  simple   = 40/60 core/TQQQ when above the 200-day (states A, B, D), cash otherwise; vol target + cap
BENCHMARKS: QQQ buy & hold (with div), QQQ levered to the current design's realized vol on each path.
WORLDS (10-year scored horizon after a 420-session warm-up, 500 paths per cell):
  A  block bootstrap of real days, panels proxy 1999-2026 / holdout 1999-Oct 2015 / real ETFs 2015-2026,
     mean block 20 / 60 / 120 / 250 sessions (central case 60-120)
  B  random walk: GARCH(1,1) with t(5) shocks, long-run vol 23%, ~11%/yr drift, NO trend persistence
  C  bull/bear Markov regimes: bull +25%/yr vol 15%, bear -30%/yr vol 32%, t(5) shocks; mean bear length
     20 / 60 / 125 / 250 sessions, bull 3x as long (75% of time bull, ~11%/yr overall)
CRASH variant of every cell: each path gets ONE crash at a random time in the scored horizon, 50/50:
  flash  = one -20% QQQ day
  fast   = 15 sessions totalling about -35% (daily -2.8%, sd 3%)
  On crash days QQQ/EW/core move by the crash return (SPMO core x0.9, SPY x0.75), 2x/3x legs at 2x/3x
  (floored at -99%); signals are recomputed from the crashed path.
REPORTED per design: median and 5th-pct 10y CAGR, median Sharpe, median and 5th-pct max drawdown,
P(CAGR > QQQ), P(CAGR > QQQ at the same vol), P(10y loss).
"""
import sys, os, time, json, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
import numpy as np
import monte_carlo as MC
import state as S

P = int(os.environ.get('MC_PATHS', 500)); YEARS = 10
H = int(252 * YEARS); T = MC.WARMUP + H + 1
CUR = dict(MC.LIVE, name='current', a_base=(0.40, 0.60), vol='max10_30', d_buffer=S.D_ZONE_BUFFER, gross_cap=S.GROSS_CAP)
A_ROW = (0.40, 0.60, 0, 0, 0)
DESIGNS = [CUR, dict(CUR, name='no-trim', trim='none'),
           dict(CUR, name='bare', trim='none', d_gate=False, d_ladder=False, fast=False),
           dict(CUR, name='simple', trim='none', d_gate=False, d_ladder=False, fast=False,
                rows=dict(CUR['rows'], B=A_ROW, C=(0, 0, 0, 0, 1), D=A_ROW))]

def from_index(panel, idx):
    return {k: panel[k][idx] for k in panel if k != 'dates'}

def synth(r, rng, cash_pa=0.03):
    """Legs from a synthetic QQQ return matrix (P, T)."""
    cash = np.full_like(r, cash_pa / 252); fin = cash + MC.FIN_SPREAD / 252
    return dict(qqq=r, ew=r + rng.normal(0, 0.004, r.shape), core=r + 0.006 / 252, qqq_tr=r + 0.006 / 252,
                tqqq=np.maximum(3 * r - 2 * fin - MC.TQQQ_ER / 252, -0.99),
                qld=np.maximum(2 * r - fin - MC.QLD_ER / 252, -0.99), xlu=np.zeros_like(r), cash=cash,
                spy=0.75 * r + rng.normal(0, 0.004, r.shape) + 0.018 / 252)

def tshock(rng, shape, nu=5):
    return rng.standard_t(nu, shape) / np.sqrt(nu / (nu - 2))

def world_random_walk(rng):
    vol_lr = 0.23 / np.sqrt(252); a, b = 0.09, 0.89; om = vol_lr ** 2 * (1 - a - b)
    mu = (0.11 + 0.23 ** 2 / 2) / 252
    z = tshock(rng, (P, T)); r = np.zeros((P, T)); h = np.full(P, vol_lr ** 2)
    for t in range(1, T):
        e = np.sqrt(h) * z[:, t]; r[:, t] = mu + e; h = om + a * e ** 2 + b * h
    return synth(np.clip(r, -0.5, 0.5), rng)

def world_regimes(rng, bear_len):
    bull_len = 3 * bear_len
    z = tshock(rng, (P, T)); r = np.zeros((P, T)); bear = rng.random(P) < 0.25
    for t in range(1, T):
        flip = np.where(bear, rng.random(P) < 1 / bear_len, rng.random(P) < 1 / bull_len)
        bear = bear ^ flip
        mu = np.where(bear, (-0.30 + 0.32 ** 2 / 2) / 252, (0.25 + 0.15 ** 2 / 2) / 252)
        sd = np.where(bear, 0.32, 0.15) / np.sqrt(252)
        r[:, t] = mu + sd * z[:, t]
    return synth(np.clip(r, -0.5, 0.5), rng)

def add_crash(g, rng, spmo_core=False):
    g = {k: v.copy() for k, v in g.items()}
    for i in range(P):
        if rng.random() < 0.5:
            days = [rng.integers(MC.WARMUP + 1, T)]; rets = [-0.20]
        else:
            s = rng.integers(MC.WARMUP + 1, T - 15); days = list(range(s, s + 15))
            rets = list(-0.028 + rng.normal(0, 0.03, 15))
        for d, rc in zip(days, rets):
            g['qqq'][i, d] = rc; g['ew'][i, d] = rc; g['qqq_tr'][i, d] = rc
            g['core'][i, d] = 0.9 * rc if spmo_core else rc
            g['tqqq'][i, d] = max(3 * rc, -0.99); g['qld'][i, d] = max(2 * rc, -0.99)
            g['spy'][i, d] = 0.75 * rc
            if 'spmo' in g: g['spmo'][i, d] = 0.9 * rc
    return g

def score(g):
    qpx = 100 * np.cumprod(1 + g['qqq'], 1); ewpx = 100 * np.cumprod(1 + g['ew'], 1)
    sig = MC.signals(qpx, ewpx)
    legs = np.stack([g['core'], g['tqqq'], g['qld'], g['xlu'], g['cash']], -1)
    sl = slice(MC.WARMUP + 1, T); cash = g['cash'][:, sl]
    out = {}
    for cfg in DESIGNS:
        w = MC.target_weights(sig, cfg)
        r, tr = MC.run_strategy(w, MC.regime_key(sig, cfg), legs, MC.WARMUP)
        out[cfg['name']] = MC.stats(r, cash)
    q = MC.stats(g['qqq_tr'][:, sl], cash); out['QQQ'] = q
    L = out['current']['vol'] / q['vol']
    out['QQQ same vol'] = MC.stats(MC.levered(g['qqq_tr'][:, sl], cash, L), cash)
    return out

def summarize(out):
    q = out['QQQ']['cagr']; qv = out['QQQ same vol']['cagr']; rows = {}
    for k, s in out.items():
        rows[k] = dict(med=float(np.median(s['cagr'])), p5=float(np.percentile(s['cagr'], 5)),
                       sh=float(np.median(s['sharpe'])), mdd=float(np.median(s['mdd'])),
                       mdd5=float(np.percentile(s['mdd'], 5)), beatq=float(np.mean(s['cagr'] > q)),
                       beatv=float(np.mean(s['cagr'] > qv)), loss=float(np.mean(s['nav'] < 1)))
    return rows

def fmt(lab, rows):
    lines = [f"\n## {lab}", f"{'':14s}{'medCAGR':>8}{'p5CAGR':>8}{'Sharpe':>7}{'medDD':>7}{'p5DD':>7}{'>QQQ':>6}{'>QQQv':>6}{'loss':>6}"]
    for k, x in rows.items():
        lines.append(f"{k:14s}{x['med']*100:7.1f}%{x['p5']*100:7.1f}%{x['sh']:7.2f}{x['mdd']*100:6.0f}%{x['mdd5']*100:6.0f}%"
                     f"{x['beatq']*100:5.0f}%{x['beatv']*100:5.0f}%{x['loss']*100:5.0f}%")
    return '\n'.join(lines)

def main():
    here = os.path.dirname(os.path.abspath(__file__)); log = open(os.path.join(here, 'mc_study_run.log'), 'w')
    allres = {}
    def emit(lab, g, crash_core=False):
        t0 = time.time()
        for tag, gg in (('', g), (' + CRASH', add_crash(g, np.random.default_rng(hash(lab) % 2**32), crash_core))):
            rows = summarize(score(gg)); allres[lab + tag] = rows
            txt = fmt(lab + tag, rows) + f"   [{time.time()-t0:.0f}s]"; print(txt, flush=True); log.write(txt + '\n'); log.flush()
    for kind in ('holdout', 'proxy', 'real'):
        panel = MC.load_panel(kind); src = np.arange(1, len(panel['dates']))
        for Lb in (20, 60, 120, 250):
            rng = np.random.default_rng(20261119 + Lb)
            g = from_index(panel, src[MC.bootstrap_idx(rng, len(src), P, T, Lb)])
            emit(f"A bootstrap {kind}, block {Lb}", g, kind == 'real')
    emit('B random walk (no trends)', world_random_walk(np.random.default_rng(1)))
    for bl in (20, 60, 125, 250):
        emit(f"C regimes, mean bear {bl} sessions", world_regimes(np.random.default_rng(100 + bl), bl))
    json.dump(allres, open(os.path.join(here, 'mc_study.json'), 'w'), indent=1)
    log.write('\ndone\n'); log.close(); print('done')

if __name__ == '__main__':
    main()
