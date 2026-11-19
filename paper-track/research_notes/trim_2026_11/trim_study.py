"""Milder extension trims (2026-11-19, owner: "weaken the trim").

PRE-REGISTERED before the first run:
VARIANTS of the A row's trim (everything else = current design: 40/60, gate, ladder, buffer, max(10,30) vol, cap 2.0):
  current   v2: first held vote takes all TQQQ out, SPMO cut 1/6 per vote
  half      first vote takes half the TQQQ out (half stays), SPMO cut as v2
  two-vote  half out at 1 held vote, all out at 2+
  to-QLD    at any held vote the TQQQ dollars move to QLD (3x -> 2x) instead of cash
  wider     v2 unchanged but vote lines 15/17/20% above the 100/150/200-day (instead of 10/12/15%)
  no-trim   reference
TESTS: (1) single historical paths: real 2015-26, proxy 2001-26, holdout 2001-Oct15 (QQQ cash legs on, sleeve off);
(2) untouched sets: NDX 1987-2000, Nikkei, DAX, FTSE (excess Sharpe); (3) Monte Carlo 500 paths x 10y:
bootstrap holdout/proxy/real at blocks 60 and 120, random walk, regimes with mean bear 60 and 125, plus a crash
version of holdout-120, proxy-120 and regimes-125.
A variant is "better than current" if it raises Sharpe on the untouched sets and synthetic worlds while giving up
no more than 0.05 median Sharpe and 3 pp median max DD on the bootstrapped QQQ history.
"""
import sys, os, json, warnings; warnings.filterwarnings('ignore')
SCR = '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/vol'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCR); sys.path.insert(1, os.path.join(HERE, '..', '..')); sys.path.insert(2, os.path.join(HERE, '..', 'mc_2026_11'))
import numpy as np
import harness as H, untouched_test as U
import monte_carlo as MC, state as S
_n = len(H.sr['vol'][0]); _N0 = len(H.pr['dates'])
for _k, _v in list(H.pr.items()):
    if hasattr(_v, '__len__') and len(_v) == _N0 and _N0 != _n: H.pr[_k] = _v[:_n]
H.RD = H.pr['dates']
import mc_study as M

_orig = MC.target_weights
def tw(sig, cfg=MC.LIVE):
    w = _orig(sig, cfg)
    if cfg.get('trim') != 'v2' or 'keep1' not in cfg:
        return w
    # rebuild the A rows with the milder rule, then re-apply vol target and cap exactly as _orig does
    base = _orig(sig, dict(cfg, gross_cap=None, vol_target=1e9))          # pre-vol, pre-cap targets
    eff, held = MC._eff(sig, cfg), sig['held']; a = eff == 0
    c0, t0 = cfg['a_base']
    keep = np.where(held == 0, 1.0, np.where(held == 1, cfg['keep1'], cfg['keep2']))
    core = c0 * (1 - S.EXTENSION_CORE_CUT_PER_VOTE * held)
    base[..., 0] = np.where(a, core, base[..., 0])
    base[..., 1] = np.where(a, t0 * keep, base[..., 1])
    base[..., 2] = np.where(a, t0 * (1 - keep) if cfg.get('to_qld') else 0.0, base[..., 2])
    v = sig['vol'] if cfg['vol'] == '30' else np.fmax(sig['vol'], np.where(np.isnan(sig['vol']), np.nan, sig['vol10']))
    vt = cfg.get('vol_target', S.VOL_TARGET_PA)
    mult = np.where(np.isnan(v) | (v <= 0), 1.0, np.minimum(1.0, vt / np.where(v > 0, v, 1)))
    base[..., :4] *= mult[..., None]
    gc = cfg.get('gross_cap')
    if gc:
        gross = (base[..., :4] * np.array(S.GROSS_EXPOSURE)).sum(-1)
        base[..., :4] *= np.where(gross > gc, gc / np.maximum(gross, 1e-12), 1.0)[..., None]
    base[..., 4] = 1.0 - base[..., :4].sum(-1)
    return base
MC.target_weights = tw

CUR = dict(M.CUR)
V = [CUR, dict(CUR, name='half', keep1=0.5, keep2=0.5), dict(CUR, name='two-vote', keep1=0.5, keep2=0.0),
     dict(CUR, name='to-QLD', keep1=0.0, keep2=0.0, to_qld=True), dict(CUR, name='wider', wider=True),
     dict(CUR, name='no-trim', trim='none')]
WIDE = ((100, 0.15), (150, 0.17), (200, 0.20))
def signals_wide(qpx, ewpx):
    old = S.EXTENSION_RULES; S.EXTENSION_RULES = WIDE
    try: return MC.signals(qpx, ewpx)
    finally: S.EXTENSION_RULES = old
# sanity: the patched function reproduces the original for keep1=keep2=0 (current)
_chk = H.sig
assert np.allclose(tw(_chk, dict(CUR, keep1=0.0, keep2=0.0)), _orig(_chk, CUR)), 'patched trim does not reproduce v2'

out = {}
def st(r):
    nav = np.cumprod(1 + r); dd = (nav / np.maximum.accumulate(nav) - 1).min(); v = r.std(ddof=1) * 252 ** .5
    return dict(c=float(nav[-1] ** (252 / len(r)) - 1), sh=float(r.mean() * 252 / v), m=float(dd))
# (1) historical
p = H.p; qpx = 100 * np.cumprod(1 + p['qqq']); ewpx = 100 * np.cumprod(1 + p['ew'])
SIGW = signals_wide(qpx[None], ewpx[None]); SRW = H.slice_sig(SIGW, H.OFF)
def hist(cfg, real, d1='2099'):
    pn = H.pr if real else H.p; ds = pn['dates']
    sg = (SRW if real else SIGW) if cfg.get('wider') else (H.sr if real else H.sig)
    W, L, key = H.weights(sg, ds, real, cfg=cfg, vixm=False)
    s0 = next(i for i, x in enumerate(ds) if x >= ('2015-11-02' if real else '2001-01-02')); e = max(i for i, x in enumerate(ds) if x <= d1)
    return st(MC.run_strategy(W[None, :e+1], key[None, :e+1], L[None, :e+1], s0)[0][0])
for cfg in V:
    out.setdefault(cfg['name'], {})
    out[cfg['name']]['hist real'] = hist(cfg, True); out[cfg['name']]['hist proxy'] = hist(cfg, False)
    out[cfg['name']]['hist holdout'] = hist(cfg, False, '2015-10-30')
# (2) untouched
vix, _ = U.vix_hist()
sets = [('NDX87-00', U.panel(MC._load('NDX_index_daily.csv'), div=MC.QQQ_DIV), vix, U.END_A)]
for sym in ('^N225', '^GDAXI', '^FTSE'): sets.append((sym, U.panel(U.yahoo(sym)), None, '2099'))
for nm, pp, vx, end in sets:
    sg0 = U.sigs(pp); q = 100 * np.cumprod(1 + pp['qqq'])
    sgw = signals_wide(q[None], q[None]); sgw['pct'][:] = np.nan; sgw['gate_b'][:] = False; sgw['gate'] = sgw['gate_g'].copy()
    ds = pp['dates']; s0 = MC.WARMUP; e = max(i for i, d in enumerate(ds) if d <= end)
    for cfg in V:
        r, _, _ = U.run(sgw if cfg.get('wider') else sg0, pp, cfg, vx is not None, vx, s0, e, 0)
        x = U.stats(r, pp['cash'][s0+1:e+1], ds[s0+1:e+1]); out[cfg['name']][f'untouched {nm}'] = dict(c=float(x['c']), sh=float(x['ex']), m=float(x['m']))
# (3) Monte Carlo
P, T = M.P, M.T
def mc_cell(lab, g):
    qpx = 100 * np.cumprod(1 + g['qqq'], 1); ewpx = 100 * np.cumprod(1 + g['ew'], 1)
    sig = MC.signals(qpx, ewpx); sigw = signals_wide(qpx, ewpx)
    legs = np.stack([g['core'], g['tqqq'], g['qld'], g['xlu'], g['cash']], -1); sl = slice(MC.WARMUP + 1, T)
    for cfg in V:
        sg = sigw if cfg.get('wider') else sig
        r, _ = MC.run_strategy(MC.target_weights(sg, cfg), MC.regime_key(sg, cfg), legs, MC.WARMUP)
        s = MC.stats(r, g['cash'][:, sl])
        out[cfg['name']][lab] = dict(c=float(np.median(s['cagr'])), sh=float(np.median(s['sharpe'])), m=float(np.median(s['mdd'])))
    print('done', lab, flush=True)
for kind in ('holdout', 'proxy', 'real'):
    panel = MC.load_panel(kind); src = np.arange(1, len(panel['dates']))
    for Lb in (60, 120):
        g = M.from_index(panel, src[MC.bootstrap_idx(np.random.default_rng(20261119 + Lb), len(src), P, T, Lb)])
        mc_cell(f'MC {kind} L{Lb}', g)
        if Lb == 120 and kind != 'real': mc_cell(f'MC {kind} L{Lb} +crash', M.add_crash(g, np.random.default_rng(7)))
mc_cell('MC random walk', M.world_random_walk(np.random.default_rng(1)))
for bl in (60, 125):
    g = M.world_regimes(np.random.default_rng(100 + bl), bl); mc_cell(f'MC regimes bear{bl}', g)
    if bl == 125: mc_cell(f'MC regimes bear{bl} +crash', M.add_crash(g, np.random.default_rng(8)))
json.dump(out, open(os.path.join(HERE, 'trim_study.json'), 'w'), indent=1)
cols = list(out['current'].keys())
with open(os.path.join(HERE, 'trim_study_run.log'), 'w') as fh:
    for metric, f in (('Sharpe (untouched: excess Sharpe)', lambda x: f"{x['sh']:.2f}"), ('CAGR', lambda x: f"{x['c']*100:.1f}"), ('max DD (MC: median)', lambda x: f"{x['m']*100:.0f}")):
        fh.write(f"\n## {metric}\n{'test':28s}" + ''.join(f"{c['name']:>10s}" for c in V) + '\n')
        for col in cols:
            fh.write(f"{col:28s}" + ''.join(f"{f(out[c['name']][col]):>10s}" for c in V) + '\n')
print(open(os.path.join(HERE, 'trim_study_run.log')).read())
