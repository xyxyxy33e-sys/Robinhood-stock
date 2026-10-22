"""Monte Carlo test of the live design (2026-10-09 release: A 25/75 + D ladder)
against buy-and-hold benchmarks, on block-bootstrapped return paths.

WHY. Every figure in STRATEGY.md is one historical path. This asks how the
design does across many plausible paths drawn from the same return history,
and how often it beats simply holding QQQ / SPY / SPMO -- or holding QQQ at the
same volatility as the strategy (the fair test: does the regime machinery add
anything beyond leverage?).

GENERATOR. Stationary block bootstrap (Politis-Romano) of whole trading days:
every column (QQQ, the equal-weight breadth leg, core, TQQQ, QLD, cash, SPY,
SPMO) is drawn from the SAME day, so cross-asset correlation, leverage decay
and fat tails are kept; mean block length L keeps volatility clustering and
short-run trend. The strategy's signals (50/200 and 20/100 classifiers,
gaps, 30d vol, trim votes, breadth percentile, D gate) are recomputed from
each synthetic QQQ / EW path -- nothing is read from the real calendar.
Blocks SHORTER than the moving averages break the multi-month trends the
classifier is built to ride, so short L is a hostile test and long L a
friendly one; read the result across L, not at one L.

PANELS.
  proxy  1999-09..2026-09 (the project's 26y QQQ-core proxy): core = QQQ +0.6%
         div, TQQQ/QLD synthetic (long_history_backtest.synth_leveraged
         constants), cash = 3m T-bill, EW = QQEW (2006-05+) / NDX survivor EW
         before. Contains 2000-02 and 2008.
  real   2015-10..2026-09 real ETFs (SPMO, TQQQ, QLD price closes, T-bill
         cash). One bear market (2022); a strong-drift sample.

ENGINE. A numpy re-implementation of state.py's live path, vectorised across
paths: macro 50/200 + fast 20/100 classifiers (1% hysteresis), effective
state map, extension trim v2 with 3-session spell carry (A base 25/75), D
gate (breadth pct < 0.20 or gap200 < 2%), D ladder, plain 30d vol target
(20%, cap 1), 5% L1 drift band + zero-leg stubs + regime-change triggers,
4bp one-way cost, decide at close t / earn t+1. --verify checks it against
state.py's own functions on the real history, day by day. NOT modelled: the
VIXM cash sleeve (cash is all T-bill/BOXX), taxes, deposits.

    python3 paper-track/monte_carlo.py --verify
    python3 paper-track/monte_carlo.py --paths 1000 --years 10
"""
import argparse
import csv
import json
import math
import os
import sys
import time
from datetime import date

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, 'data')
sys.path.insert(0, HERE)
import state as S  # noqa: E402
import breadth_tracker as BT  # noqa: E402

COST = 0.0004
QQQ_DIV, SPY_DIV = 0.006, 0.018          # %/yr dividend accrual on the proxy panel
XLU_DIV = 0.03                            # flat XLU yield (long_history_backtest), both panels
FIN_SPREAD, TQQQ_ER, QLD_ER = 0.003, 0.0084, 0.0095
WARMUP = 420                              # sessions before the scored horizon (classifier converges <= 323)
A_BASE = (0.25, 0.75)                     # live A base from 2026-10-09
LETTERS = 'ABCDEF'

# A design = the rows and overlays a release traded. LIVE is the 2026-10-09
# release; monte_carlo_versions.py builds the earlier ones from the same keys.
# Rows are (core, tqqq, qld, xlu, cash) before the vol target.
LIVE = dict(
    name='2026-10-09 live (A 25/75 + D ladder)',
    rows={'B': (0.75, 0.25, 0, 0, 0), 'C': (1, 0, 0, 0, 0), 'D': (0, 0, 1, 0, 0),
          'E': (0, 0, 0, 0, 1), 'F': (0, 0, 0, 0, 1)},
    a_base=A_BASE,
    fast=True,            # 20/100 re-entry overlay on B/C/F
    trim='v2',            # 'none' | 'v1' (risky x (1 - step*votes)) | 'v2' (held votes, TQQQ out)
    trim_step=1 / 3,      # v1 only
    d_gate=True, d_ladder=True,
    vol='30',             # '30' | 'max10_30'
    band=0.05, stubs=True,
)


# --------------------------------------------------------------------------- data
def _load(name, dcol='d', ccol='c'):
    out = {}
    for r in csv.DictReader(open(os.path.join(DATA, name))):
        try:
            out[r[dcol]] = float(r[ccol])
        except (ValueError, KeyError):
            pass
    return out


def _yf(d0, d1):
    return (date.fromisoformat(d1) - date.fromisoformat(d0)).days / 365.0


def _rets(px, dates):
    """Simple returns on `dates` (r[0] = 0), forward-filling missing closes."""
    out = np.zeros(len(dates)); last = None
    for i, d in enumerate(dates):
        v = px.get(d, last)
        if last is not None and v is not None:
            out[i] = v / last - 1
        last = v
    return out


def load_panel(kind):
    """kind: proxy | real | holdout (the proxy panel cut at 2015-10-31: the era
    before SPMO, which no live parameter was fit inside). dict of aligned daily arrays: dates, qqq (price return, the signal), ew,
    core, tqqq, qld, cash, spy, spmo (spmo only on the real panel), qqq_tr."""
    if kind == 'holdout':
        p = load_panel('proxy')
        n = sum(1 for d in p['dates'] if d <= '2015-10-31')
        return {k: (v[:n] if k == 'dates' else v[:n].copy()) for k, v in p.items()}
    qqq = _load('qqq_long_history.csv')
    spy = _load('spy_long_history.csv')
    tb = _load('dgs3mo_full.csv', 'observation_date', 'DGS3MO')
    qqew = _load('QQEW_daily_ext.csv'); surv = _load('ndx_survivor_ew_daily.csv')
    end = min(max(qqq), max(spy))
    if kind == 'real':
        spmo, tq, ql = _load('spmo_ohlc.csv'), _load('tqqq_ohlc.csv'), _load('qld_ohlc.csv')
        end = min(end, max(spmo), max(tq), max(ql))
        dates = sorted(d for d in qqq if min(spmo) <= d <= end)
    else:
        dates = sorted(d for d in qqq if d <= end)
    rate = []; last = 0.0
    tbd = sorted(tb); j = 0
    for d in dates:                       # 3m T-bill as of the prior available print
        while j < len(tbd) and tbd[j] <= d:
            last = tb[tbd[j]]; j += 1
        rate.append(last / 100.0)
    rate = np.array(rate)
    yf = np.array([0.0] + [_yf(dates[i - 1], dates[i]) for i in range(1, len(dates))])
    rprev = np.concatenate([[rate[0]], rate[:-1]])
    cash = rprev * yf
    rq = _rets(qqq, dates)
    # EW breadth leg: QQEW where it exists, NDX survivor EW before (returns, so no splice jump)
    ew = np.where([d in qqew for d in dates], _rets(qqew, dates), _rets(surv, dates))
    first_qqew = min(qqew)
    ew[[i for i, d in enumerate(dates) if d == first_qqew]] = 0.0
    p = dict(dates=dates, qqq=rq, ew=ew, cash=cash, spy=_rets(spy, dates) + SPY_DIV * yf,
             qqq_tr=rq + QQQ_DIV * yf)
    xlu = _load('xlu_ohlc.csv') if kind == 'real' else _load('xlu_long_history.csv')
    p['xlu'] = _rets(xlu, dates) + XLU_DIV * yf
    if kind == 'real':
        p.update(core=_rets(spmo, dates), tqqq=_rets(tq, dates), qld=_rets(ql, dates),
                 spmo=_rets(spmo, dates), qqq_tr=rq.copy(), spy=_rets(spy, dates))
    else:
        u = rq + QQQ_DIV * yf
        fin = (rprev + FIN_SPREAD) * yf
        p.update(core=u, tqqq=3 * u - 2 * fin - TQQQ_ER * yf, qld=2 * u - fin - QLD_ER * yf)
    for k in list(p):
        if k != 'dates':
            p[k] = np.asarray(p[k], float); p[k][0] = 0.0
    return p


# --------------------------------------------------------------------------- engine
def _sma(px, n):
    c = np.cumsum(px, axis=1)
    out = np.full(px.shape, np.nan)
    out[:, n - 1] = c[:, n - 1] / n
    out[:, n:] = (c[:, n:] - c[:, :-n]) / n
    return out


def _classify(px, short_n, long_n, buf=0.01):
    """state.compute_states vectorised over rows; ints 0..5 = A..F."""
    P, T = px.shape
    ms, ml = _sma(px, short_n), _sma(px, long_n)
    s1 = np.zeros(P, bool); s2 = np.zeros(P, bool)
    out = np.full((P, T), 5, np.int8)
    for t in range(long_n - 1, T):
        v = px[:, t]
        s1 = np.where(v > ms[:, t] * (1 + buf), True, np.where(v < ms[:, t] * (1 - buf), False, s1))
        s2 = np.where(v > ml[:, t] * (1 + buf), True, np.where(v < ml[:, t] * (1 - buf), False, s2))
        cross = ms[:, t] > ml[:, t]
        st = np.where(s1 & s2 & cross, 0, np.where(s1 & s2, 1, np.where(s1, 2,
                      np.where(s2, 3, np.where(cross, 4, 5)))))
        out[:, t] = st
    return out


def signals(qpx, ewpx):
    """Every per-session input of the live weight call, for each row of prices."""
    P, T = qpx.shape
    macro = _classify(qpx, 50, 200)
    fast = _classify(qpx, 20, 100)
    eff = macro.copy()
    eff_slow = macro.copy()
    eff[(macro == 1) & (fast <= 1)] = 0
    eff[(macro == 2) & (fast <= 1)] = 0
    eff[(macro == 5) & (fast <= 2)] = 2
    gaps = {n: qpx / _sma(qpx, n) - 1 for n in (100, 150, 200)}
    vol = np.full((P, T), np.nan); vol10 = np.full((P, T), np.nan)
    sr = qpx[:, 1:] / qpx[:, :-1] - 1                                # simple returns, as realized_vol
    for t in range(10, T):
        vol10[:, t] = sr[:, t - 10:t].std(axis=1, ddof=1) * math.sqrt(252)
        if t >= 30:
            vol[:, t] = sr[:, t - 30:t].std(axis=1, ddof=1) * math.sqrt(252)
    # breadth: x60 = log(EW/QQQ) change over 60 sessions; pct = trailing-252 rank (incl. itself)
    lrel = np.log(ewpx / qpx)
    x = np.full((P, T), np.nan); x[:, 60:] = lrel[:, 60:] - lrel[:, :-60]
    pct = np.full((P, T), np.nan)
    for t in range(60 + 251, T):
        w = x[:, t - 251:t + 1]; xv = x[:, t:t + 1]
        pct[:, t] = ((w < xv).sum(1) + 0.5 * (w == xv).sum(1)) / 252.0
    # extension trim v2 held votes (A spells, 3-session gap carry, 15-session-high step-down)
    votes = sum((gaps[n] > th).astype(int) for n, th in S.EXTENSION_RULES)   # nan (warm-up) never votes
    held = np.zeros((P, T), np.int8)
    h = np.zeros(P, np.int8); gapn = np.zeros(P, int)
    for t in range(T):
        ina = eff[:, t] == 0
        gapn = np.where(ina, 0, gapn + 1)
        h = np.where(~ina & (gapn > S.A_SPELL_GAP_CARRY), 0, h)
        hi15 = qpx[:, t] >= qpx[:, max(0, t - 14):t + 1].max(1)
        raw = votes[:, t]
        nh = np.where(raw > h, raw, np.where((h > raw) & hi15, h - 1, h))
        h = np.where(ina, nh, h).astype(np.int8)
        held[:, t] = np.where(ina, h, 0)
    gate = (macro == 3) & ((pct < S.D_GATE_BREADTH_PCT) | (gaps[200] < S.D_GATE_GAP200))
    zone = np.where(gaps[100] > 0, 1, np.where(gaps[150] > 0, 2, 3))
    return dict(macro=macro, fast=fast, eff=eff, eff_slow=eff_slow, gaps=gaps, vol=vol, vol10=vol10,
                pct=pct, held=held, votes=votes, gate=gate, zone=zone)


def _eff(sig, cfg):
    return sig['eff'] if cfg['fast'] else sig['eff_slow']


def target_weights(sig, cfg=LIVE):
    """(P, T, 5) targets (core, tqqq, qld, xlu, cash) after the vol target, for design cfg."""
    eff, held = _eff(sig, cfg), sig['held']
    P, T = eff.shape
    w = np.zeros((P, T, 5))
    for s_, row in cfg['rows'].items():
        w[eff == LETTERS.index(s_)] = row
    a = eff == 0
    if cfg['trim'] == 'v2':
        # held votes are computed on the fast-overlay A spells; v2 never ran without the overlay
        c0, t0 = cfg['a_base']
        w[a] = 0.0
        w[..., 0] = np.where(a, c0 * (1 - S.EXTENSION_CORE_CUT_PER_VOTE * held), w[..., 0])
        w[..., 1] = np.where(a, np.where(held == 0, t0, 0.0), w[..., 1])
    else:
        c0, t0 = cfg['a_base']
        w[a] = (c0, t0, 0.0, 0.0, 0.0)
        if cfg['trim'] == 'v1':
            f = np.maximum(0.0, 1 - cfg['trim_step'] * sig['votes'])
            w[..., :4] = np.where(a[..., None], w[..., :4] * f[..., None], w[..., :4])
    if cfg['d_ladder']:
        for z, k in ((1, 'D1'), (2, 'D2'), (3, 'D3')):
            c, tq, q = S.D_LADDER_ROWS[k]
            w[(eff == 3) & (sig['zone'] == z)] = (c, tq, q, 0.0, 0.0)
    if cfg['d_gate']:
        w[sig['gate']] = (0.0, 0.0, 0.0, 0.0, 1.0)
    v = sig['vol'] if cfg['vol'] == '30' else np.fmax(sig['vol'], np.where(np.isnan(sig['vol']), np.nan, sig['vol10']))
    mult = np.where(np.isnan(v) | (v <= 0), 1.0, np.minimum(1.0, S.VOL_TARGET_PA / np.where(v > 0, v, 1)))
    w[..., :4] *= mult[..., None]
    w[..., 4] = 1.0 - w[..., :4].sum(-1)
    return w


def regime_key(sig, cfg=LIVE):
    """Anything whose change forces a rebalance: eff state, trim votes (held for v2, raw for
    v1), D gate, D zone -- each only where the design has it."""
    eff = _eff(sig, cfg)
    k = eff.astype(int) * 1000
    if cfg['trim'] == 'v2':
        k = k + sig['held'] * 100
    elif cfg['trim'] == 'v1':
        k = k + np.where(eff == 0, sig['votes'], 0) * 100
    gate = sig['gate'] if cfg['d_gate'] else np.zeros_like(sig['gate'])
    if cfg['d_gate']:
        k = k + gate * 10
    if cfg['d_ladder']:
        k = k + np.where((eff == 3) & ~gate, sig['zone'], 0)
    return k


def run_strategy(w, key, legs, start, band=S.REBALANCE_DRIFT_BAND, stubs=True):
    """Daily NAV returns from session start+1 on. legs (P, T, 4) simple returns.
    Rebalance at close t when the regime key changed, L1 drift > band, or a
    zero-target leg is held above ZERO_LEG_EPS; cost COST x turnover."""
    P, T, _ = w.shape
    out = np.zeros((P, T - start - 1)); trades = np.zeros(P)
    h = w[:, start].copy(); cost = np.full(P, COST)     # initial allocation: buy every leg (BOXX too)
    for t in range(start, T - 1):
        if t > start:
            tgt = w[:, t]
            drift = np.abs(tgt - h).sum(1)
            stub = ((tgt == 0) & (h > S.ZERO_LEG_EPS)).any(1) if stubs else False
            reb = (key[:, t] != key[:, t - 1]) | (drift > band) | stub
            cost = np.where(reb, COST * drift, 0.0)
            h = np.where(reb[:, None], tgt, h)
            trades += reb
        r = legs[:, t + 1]
        g = (h * r).sum(1)
        out[:, t - start] = (1 + g) * (1 - cost) - 1
        h = h * (1 + r) / (1 + g)[:, None]
    return out, trades


def stats(r, rf=None):
    """CAGR, project Sharpe (mean/sd, no rf -- annual_stats), excess Sharpe, MaxDD, vol."""
    n = r.shape[1]
    nav = np.cumprod(1 + r, axis=1)
    cagr = nav[:, -1] ** (252.0 / n) - 1
    sd = r.std(1, ddof=1)
    sh = r.mean(1) * 252 / (sd * math.sqrt(252))
    ex = (r - (rf if rf is not None else 0)).mean(1) * 252 / (sd * math.sqrt(252))
    peak = np.maximum.accumulate(np.concatenate([np.ones((r.shape[0], 1)), nav], 1), axis=1)[:, 1:]
    mdd = (nav / peak - 1).min(1)
    return dict(cagr=cagr, sharpe=sh, exsharpe=ex, mdd=mdd, vol=sd * math.sqrt(252), nav=nav[:, -1])


def levered(r_under, cash, L, spread=FIN_SPREAD / 252):
    """Daily-rebalanced constant leverage L (per row) on an underlying, financed at cash(+spread)."""
    L = L[:, None]
    borrow = np.where(L > 1, cash + spread, cash)
    return L * r_under + (1 - L) * borrow


# --------------------------------------------------------------------------- bootstrap
def bootstrap_idx(rng, n_src, P, T, mean_block):
    """Stationary bootstrap indices: each step continues the block with prob
    1-1/L, else jumps to a uniform random day."""
    idx = np.empty((P, T), int)
    idx[:, 0] = rng.integers(0, n_src, P)
    jump = rng.random((P, T)) < 1.0 / mean_block
    fresh = rng.integers(0, n_src, (P, T))
    for t in range(1, T):
        nxt = idx[:, t - 1] + 1
        nxt = np.where(nxt >= n_src, rng.integers(0, n_src, P), nxt)
        idx[:, t] = np.where(jump[:, t], fresh[:, t], nxt)
    return idx


def simulate(panel, P, years, block, seed):
    rng = np.random.default_rng(seed)
    H = int(round(252 * years)); T = WARMUP + H + 1
    src = np.arange(1, len(panel['dates']))            # day 0 has no return
    idx = src[bootstrap_idx(rng, len(src), P, T, block)]
    g = {k: panel[k][idx] for k in panel if k != 'dates'}
    qpx = 100 * np.cumprod(1 + g['qqq'], 1); ewpx = 100 * np.cumprod(1 + g['ew'], 1)
    sig = signals(qpx, ewpx)
    w = target_weights(sig)
    legs = np.stack([g['core'], g['tqqq'], g['qld'], g['xlu'], g['cash']], -1)
    start = WARMUP
    r, trades = run_strategy(w, regime_key(sig), legs, start)
    sl = slice(start + 1, T)
    cash = g['cash'][:, sl]
    res = {'strategy': stats(r, cash)}
    res['strategy']['trades_pa'] = trades / years
    res['strategy']['exposure'] = w[:, start:T - 1, :4].sum(-1).mean(1)
    lev = w[:, start:T - 1, 0] + 3 * w[:, start:T - 1, 1] + 2 * w[:, start:T - 1, 2]
    res['strategy']['leverage'] = lev.mean(1)
    qtr = g['qqq_tr'][:, sl]
    res['QQQ'] = stats(qtr, cash)
    res['SPY'] = stats(g['spy'][:, sl], cash)
    if 'spmo' in g:
        res['SPMO'] = stats(g['spmo'][:, sl], cash)
    # same-volatility QQQ: constant leverage that matches the strategy's realised vol on that path
    L = res['strategy']['vol'] / res['QQQ']['vol']
    res['QQQ @ strat vol'] = stats(levered(qtr, cash, L), cash)
    res['QQQ @ strat vol']['L'] = L
    # same average leverage: QQQ held at the strategy's average QQQ-equivalent exposure
    L2 = res['strategy']['leverage']
    res['QQQ @ strat lev'] = stats(levered(qtr, cash, L2), cash)
    res['states'] = np.bincount(sig['eff'][:, start:].ravel(), minlength=6) / sig['eff'][:, start:].size
    return res


# --------------------------------------------------------------------------- verify
def verify():
    """Engine vs state.py on the real proxy history: every input and every target."""
    p = load_panel('proxy')
    dates = p['dates']
    qpx = 100 * np.cumprod(1 + p['qqq']); ewpx = 100 * np.cumprod(1 + p['ew'])
    sig = signals(qpx[None], ewpx[None]); w = target_weights(sig)[0]
    px = dict(zip(dates, qpx)); ew = dict(zip(dates, ewpx))
    st = S.compute_states(dates, px); fa = S.compute_fast_states(dates, px)
    gp = S.compute_extension_gaps(dates, px)
    saved = (S.A_BASE_ROWS, S.A_BASE_FROM_SESSION)
    S.A_BASE_ROWS = (('0000-00-00', A_BASE),); S.A_BASE_FROM_SESSION = ('0000-00-00', A_BASE)
    at = S.a_trim_series(dates, px)
    S.A_BASE_ROWS, S.A_BASE_FROM_SESSION = saved
    common, x = BT.relative_strength_series(dates, ew, px); pc = dict(zip(common, BT.trailing_pct(x)))
    bad = dict(macro=0, fast=0, held=0, pct=0, gate=0, w=0); worst = 0.0
    for i, d in enumerate(dates):
        if i < 400:
            continue
        bad['macro'] += LETTERS[sig['macro'][0, i]] != st[i]
        bad['fast'] += LETTERS[sig['fast'][0, i]] != fa[d]
        bad['held'] += int(sig['held'][0, i]) != at[d]['held']
        q = pc.get(d)
        bad['pct'] += (q is None) != np.isnan(sig['pct'][0, i]) or (q is not None and abs(q - sig['pct'][0, i]) > 1e-9)
        gate = S.d_gate_active(st[i], q, gp[d][200])
        bad['gate'] += gate != bool(sig['gate'][0, i])
        vol = S.realized_vol(dates, px, as_of=d) if i % 25 == 0 else None
        if i % 25 == 0:
            ref = S.target_weights_with_voltarget(st[i], False, vol, fast_state=fa[d], gaps=gp[d], d_gate=gate,
                                                  a_trim=at[d] if at[d]['in_a'] else None, d_ladder=True)
            mine = tuple(w[i])
            dd = max(abs(a - b) for a, b in zip(ref, mine)); worst = max(worst, dd)
            bad['w'] += dd > 1e-9
    n = len(dates) - 400
    print(f"verify over {n} sessions {dates[400]}..{dates[-1]} (weights checked every 25th session):")
    for k, v in bad.items():
        print(f"  {k:6s} mismatches: {v}")
    print(f"  worst weight diff: {worst:.2e}")
    # historical single-path run, 2001-01-02 on (the STRATEGY.md proxy window)
    s0 = next(i for i, d in enumerate(dates) if d >= '2001-01-02')
    legs = np.stack([p['core'], p['tqqq'], p['qld'], p['xlu'], p['cash']], -1)[None]
    r, tr = run_strategy(target_weights(sig), regime_key(sig), legs, s0)
    m = stats(r, p['cash'][None, s0 + 1:]); q = stats(p['qqq_tr'][None, s0 + 1:])
    print(f"  historical proxy {dates[s0]}..{dates[-1]}: strategy {m['cagr'][0]*100:.1f}% / Sharpe "
          f"{m['sharpe'][0]:.3f} / MaxDD {m['mdd'][0]*100:.1f}% / {tr[0]/((len(dates)-s0)/252):.0f} trades/yr; "
          f"QQQ {q['cagr'][0]*100:.1f}% / {q['sharpe'][0]:.3f} / {q['mdd'][0]*100:.1f}%")
    pr = load_panel('real')
    # real panel needs warm-up: take signals from the proxy-panel series on the same dates
    off = dates.index(pr['dates'][0])
    sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()})
          for k, v in sig.items()}
    s1 = next(i for i, d in enumerate(pr['dates']) if d >= '2015-11-02')
    lr_ = np.stack([pr['core'], pr['tqqq'], pr['qld'], pr['xlu'], pr['cash']], -1)[None]
    r, tr = run_strategy(target_weights(sr), regime_key(sr), lr_, s1)
    m = stats(r); q = stats(pr['qqq'][None, s1 + 1:]); sp = stats(pr['spmo'][None, s1 + 1:])
    print(f"  historical real   {pr['dates'][s1]}..{pr['dates'][-1]}: strategy {m['cagr'][0]*100:.1f}% / "
          f"{m['sharpe'][0]:.3f} / {m['mdd'][0]*100:.1f}%; QQQ {q['cagr'][0]*100:.1f}% / {q['sharpe'][0]:.3f} / "
          f"{q['mdd'][0]*100:.1f}%; SPMO {sp['cagr'][0]*100:.1f}% / {sp['sharpe'][0]:.3f} / {sp['mdd'][0]*100:.1f}%")


# --------------------------------------------------------------------------- report
def pct(a, q):
    return np.percentile(a, q)


def report(res, years, label):
    s = res['strategy']
    lines = [f"### {label}", "",
             f"Strategy: avg exposure {s['exposure'].mean()*100:.0f}% of NAV, avg QQQ-equivalent leverage "
             f"{s['leverage'].mean():.2f}x, {s['trades_pa'].mean():.0f} rebalances/yr; time in effective state "
             + ", ".join(f"{LETTERS[i]} {v*100:.0f}%" for i, v in enumerate(res['states'])), "",
             f"| {years:g}-yr path | CAGR p5 | p25 | median | p75 | p95 | Sharpe med | MaxDD med | MaxDD p5 | P(loss) |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    names = [k for k in res if k not in ('states',)]
    for k in names:
        m = res[k]; c = m['cagr'] * 100
        lines.append(f"| {k} | {pct(c,5):.1f}% | {pct(c,25):.1f}% | {pct(c,50):.1f}% | {pct(c,75):.1f}% | "
                     f"{pct(c,95):.1f}% | {np.median(m['sharpe']):.2f} | {np.median(m['mdd'])*100:.1f}% | "
                     f"{pct(m['mdd'],5)*100:.1f}% | {(m['nav'] < 1).mean()*100:.1f}% |")
    lines += ["", "| Strategy vs | P(higher CAGR) | median CAGR edge | P(higher Sharpe) | P(shallower MaxDD) | P(higher Sharpe AND shallower DD) |",
              "|---|---|---|---|---|---|"]
    for k in names[1:]:
        b = res[k]
        lines.append(f"| {k} | {(s['cagr'] > b['cagr']).mean()*100:.1f}% | {np.median(s['cagr']-b['cagr'])*100:+.1f} pp | "
                     f"{(s['sharpe'] > b['sharpe']).mean()*100:.1f}% | {(s['mdd'] > b['mdd']).mean()*100:.1f}% | "
                     f"{((s['sharpe'] > b['sharpe']) & (s['mdd'] > b['mdd'])).mean()*100:.1f}% |")
    if 'QQQ @ strat vol' in res:
        lines.append(f"\n(QQQ @ strat vol = QQQ at constant leverage matching the strategy's realised vol on each "
                     f"path, median L {np.median(res['QQQ @ strat vol']['L']):.2f}x; QQQ @ strat lev = QQQ at the "
                     f"strategy's average QQQ-equivalent leverage, daily rebalanced, financed at T-bill + 0.3%.)")
    return "\n".join(lines)


def summary_row(res):
    s = res['strategy']; out = {}
    for k in res:
        if k in ('strategy', 'states'):
            continue
        b = res[k]
        out[k] = dict(p_cagr=float((s['cagr'] > b['cagr']).mean()), p_sharpe=float((s['sharpe'] > b['sharpe']).mean()),
                      p_dd=float((s['mdd'] > b['mdd']).mean()), med_edge=float(np.median(s['cagr'] - b['cagr'])))
    out['strategy'] = dict(cagr_med=float(np.median(s['cagr'])), sharpe_med=float(np.median(s['sharpe'])),
                           mdd_med=float(np.median(s['mdd'])), cagr_p5=float(pct(s['cagr'], 5)),
                           mdd_p5=float(pct(s['mdd'], 5)))
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--verify', action='store_true')
    ap.add_argument('--paths', type=int, default=1000)
    ap.add_argument('--years', type=float, default=10)
    ap.add_argument('--blocks', default='5,20,60,120,250')
    ap.add_argument('--panels', default='proxy,holdout,real')
    ap.add_argument('--seed', type=int, default=20261021)
    ap.add_argument('--out', default=os.path.join(HERE, 'research_notes', 'monte_carlo_run.log'))
    a = ap.parse_args(argv)
    if a.verify:
        verify(); return
    blocks = [int(b) for b in a.blocks.split(',')]
    text = [f"# Monte Carlo run {time.strftime('%Y-%m-%d %H:%M')}  paths={a.paths} years={a.years} "
            f"blocks={blocks} seed={a.seed}", ""]
    summ = {}
    for kind in a.panels.split(','):
        panel = load_panel(kind)
        for L in blocks:
            t0 = time.time()
            res = simulate(panel, a.paths, a.years, L, a.seed + L)
            lab = (f"{kind} panel ({panel['dates'][0]}..{panel['dates'][-1]}), mean block {L} sessions "
                   f"[{time.time()-t0:.0f}s]")
            print(report(res, a.years, lab)); print()
            text += [report(res, a.years, lab), ""]
            summ[f"{kind}/L{L}"] = summary_row(res)
    with open(a.out, 'w') as fh:
        fh.write("\n".join(text) + "\n\n```json\n" + json.dumps(summ, indent=1) + "\n```\n")
    print(f"wrote {a.out}")


if __name__ == '__main__':
    main(sys.argv[1:])
