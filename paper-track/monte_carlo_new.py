"""A NEW strategy designed for the Monte Carlo, without the live design in mind.

Premise (from monte_carlo.md): trend rules only win when multi-month trends
persist, so they lose in short-block worlds. An edge that survives every block
length must come from structure the bootstrap keeps at any L: volatility
clustering (vol targeting) and the cross-asset correlation of the same day
(stocks / long Treasuries).

Families, all on QQQ (QQQ / QLD / TQQQ for leverage, never margin) and TLT:
  F1 vol target      e = min(Lmax, s* / vol_hat)
  F2 + trend gate    F1 x g while QQQ < its 200d SMA (1% hysteresis)
  F3 risk parity     inverse-vol QQQ/TLT, book scaled to s* (60d corr), TLT <= 100%
  F4 static          fixed TQQQ / TLT mix (no timing), the control
Instruments are combined without leverage beyond the ETFs': weights sum to <= 1.

Protocol, fixed before running:
  SEARCH  2002-08..2015-10 (proxy legs, real TLT), mean blocks 5/20/60/120/250.
          Winner = highest min-over-L P(CAGR > QQQ), subject to median MaxDD
          <= QQQ's and median Sharpe >= QQQ's at EVERY L; tie-break mean P.
  CONFIRM 2015-11..2026-08 real ETFs (never seen by the search), 1,000 paths,
          against QQQ, SPY and the 2026-10-22 live design on the same paths;
          plus the single historical path.
4 bp one-way, 5% L1 drift band, decide at close t / earn t+1, as the live engine.

    python3 paper-track/monte_carlo_new.py search --paths 400
    python3 paper-track/monte_carlo_new.py confirm --paths 1000
"""
import argparse
import csv
import itertools
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import monte_carlo as MC  # noqa: E402

SEARCH = ('2002-08-01', '2015-10-30')
# Simulated rates (--rates sim): yield CHANGES are drawn with each sampled day (keeping that
# day's stock/bond co-move), demeaned so the 2002-2015 bond bull is not inherited, and
# accumulated from today's level with mean reversion to it. TLT and cash are then priced
# from the simulated paths, and QLD/TQQQ are rebuilt from QQQ with the simulated
# financing rate (long_history_backtest constants), so no leg carries a historical rate path.
TLT_D, TLT_C, TLT_S = 15.81, 261.0, -0.0025     # calibrated on 2002-07..2026-10 (data/tyx_daily_provenance.md)
Y30_0, R3_0 = 0.05439, 0.0391                   # latest ^TYX (2026-10-21) and 3m T-bill (2026-08-31)
KAPPA = 0.20                                    # /yr mean reversion toward the start level (half-life ~3.5 yr)
REAL0 = '2015-10-12'
BLOCKS = (5, 20, 60, 120, 250)
LOG = os.path.join(HERE, 'research_notes')
SUFFIX = ''


# ------------------------------------------------------------------ panels
def load_panel(kind):
    """search / full: proxy legs (QQQ+0.6% div, synthetic 2x/3x) + real TLT TR;
    real: real QQQ (+0.6% div, as the benchmark), QLD, TQQQ, SPMO, TLT TR."""
    tlt = {r['d']: float(r['c']) for r in csv.DictReader(open(os.path.join(MC.DATA, 'tlt_daily_tr.csv')))}
    p = MC.load_panel('real' if kind == 'real' else 'proxy')
    if kind == 'real':
        p['qqq_tr'] = p['qqq'] + MC.QQQ_DIV / 252
    lo = '2002-07-31' if kind != 'real' else REAL0
    hi = SEARCH[1] if kind == 'search' else '9999'
    keep = [i for i, d in enumerate(p['dates']) if lo <= d <= hi]
    q = {k: (v[keep[0]:keep[-1] + 1]) for k, v in p.items()}
    q['tlt'] = MC._rets(tlt, q['dates']); q['tlt'][0] = 0.0
    q['qqq_leg'] = q['qqq_tr']
    # rate changes on the same dates, for --rates sim
    y30 = {r['d']: float(r['yield_pct']) / 100 for r in csv.DictReader(open(os.path.join(MC.DATA, 'tyx_daily.csv')))}
    r3 = {}
    for r in csv.DictReader(open(os.path.join(MC.DATA, 'dgs3mo_full.csv'))):
        try:
            r3[r['observation_date']] = float(r['DGS3MO']) / 100
        except ValueError:
            pass
    def lv(src):
        prior = [d for d in src if d <= q['dates'][0]]
        out, last = [], src[max(prior)] if prior else None     # seed from the last print before the panel (holidays)
        for d in q['dates']:
            last = src.get(d, last); out.append(last)
        return np.array(out, float)
    a30, a3 = lv(y30), lv(r3)
    q['dy30'] = np.concatenate([[0.0], np.diff(a30)]); q['dr3'] = np.concatenate([[0.0], np.diff(a3)])
    from datetime import date
    q['yf'] = np.array([0.0] + [(date.fromisoformat(q['dates'][i]) - date.fromisoformat(q['dates'][i - 1])).days / 365
                                for i in range(1, len(q['dates']))])
    return q


def simulate_rates(g, panel):
    """Replace tlt / cash / qld / tqqq in sampled paths g with legs priced from simulated rates."""
    dy = g['dy30'] - panel['dy30'][1:].mean(); dr = g['dr3'] - panel['dr3'][1:].mean(); yf = g['yf']
    P, T = dy.shape
    y = np.empty((P, T)); r = np.empty((P, T)); y[:, 0], r[:, 0] = Y30_0, R3_0
    for t in range(1, T):
        y[:, t] = np.maximum(0.005, y[:, t - 1] + dy[:, t] - KAPPA * (y[:, t - 1] - Y30_0) * yf[:, t])
        r[:, t] = np.maximum(0.0, r[:, t - 1] + dr[:, t] - KAPPA * (r[:, t - 1] - R3_0) * yf[:, t])
    d = np.concatenate([np.zeros((P, 1)), np.diff(y, axis=1)], 1)
    yp, rp = np.concatenate([y[:, :1], y[:, :-1]], 1), np.concatenate([r[:, :1], r[:, :-1]], 1)
    g['tlt'] = (yp + TLT_S) * yf - TLT_D * d + 0.5 * TLT_C * d * d
    g['cash'] = rp * yf
    u = g['qqq_tr']; fin = (rp + MC.FIN_SPREAD) * yf
    g['qld'] = 2 * u - fin - MC.QLD_ER * yf
    g['tqqq'] = 3 * u - 2 * fin - MC.TQQQ_ER * yf
    g['y30'], g['r3'] = y, r
    return g


# ------------------------------------------------------------------ signals
def roll_vol(r, n):
    c1 = np.cumsum(r, 1); c2 = np.cumsum(r * r, 1)
    out = np.full(r.shape, np.nan)
    s1 = c1[:, n - 1:] - np.concatenate([np.zeros((r.shape[0], 1)), c1[:, :-n]], 1)
    s2 = c2[:, n - 1:] - np.concatenate([np.zeros((r.shape[0], 1)), c2[:, :-n]], 1)
    var = (s2 - s1 * s1 / n) / (n - 1)
    out[:, n - 1:] = np.sqrt(np.maximum(var, 0) * 252)
    return out


def ewma_vol(r, lam=0.94):
    out = np.empty(r.shape); v = np.full(r.shape[0], np.var(r[:, :20], 1))
    for t in range(r.shape[1]):
        v = lam * v + (1 - lam) * r[:, t] ** 2; out[:, t] = np.sqrt(v * 252)
    out[:, :20] = np.nan
    return out


def signals(g):
    rq, rb = g['qqq'], g['tlt']                     # vol reads the price return, like realized_vol
    s = {'vol20': roll_vol(rq, 20), 'max10_30': np.fmax(roll_vol(rq, 10), roll_vol(rq, 30)), 'ewma': ewma_vol(rq)}
    s['q60'], s['b60'] = roll_vol(rq, 60), roll_vol(rb, 60)
    m = lambda x: (np.cumsum(x, 1) - np.concatenate([np.zeros((x.shape[0], 60)), np.cumsum(x, 1)[:, :-60]], 1)) / 60
    cov = (m(rq * rb) - m(rq) * m(rb)) * 252
    s['corr'] = np.clip(cov / (s['q60'] * s['b60']), -1, 1)
    px = 100 * np.cumprod(1 + rq, 1); sma = MC._sma(px, 200)
    up = np.ones(px.shape, bool); st = np.ones(px.shape[0], bool)
    for t in range(px.shape[1]):
        if t >= 199:
            st = np.where(px[:, t] > sma[:, t] * 1.01, True, np.where(px[:, t] < sma[:, t] * 0.99, False, st))
        up[:, t] = st
    s['up'] = up
    return s


# ------------------------------------------------------------------ weights
def equity_weights(e, cap):
    """QQQ-equivalent exposure e inside capital cap -> (qqq, qld, tqqq), cheapest decay first."""
    e = np.minimum(e, 3 * cap)
    x = np.where(cap > 0, e / np.where(cap > 0, cap, 1), 0)
    qqq = np.where(x <= 1, e, np.where(x <= 2, 2 * cap - e, 0))
    qld = np.where(x <= 1, 0, np.where(x <= 2, e - cap, 3 * cap - e))
    tq = np.where(x <= 2, 0, e - 2 * cap)
    return qqq, qld, tq


def weights(s, c):
    """(P, T, 5) weights over (qqq, qld, tqqq, tlt, cash) and a regime key."""
    shape = s['up'].shape
    key = np.zeros(shape, int)
    if c['fam'] == 'F4':
        e = np.full(shape, 3 * c['tq']); bond = np.full(shape, 1 - c['tq'])
    else:
        v = s[c['est']]; v = np.where(np.isnan(v) | (v <= 0), np.nan, v)
        if c['fam'] in ('F1', 'F2'):
            e = np.where(np.isnan(v), 1.0, np.minimum(c['L'], c['tgt'] / v)); bond = np.zeros(shape)
            if c['fam'] == 'F2':
                e = np.where(s['up'], e, e * c['g']); key = s['up'].astype(int)
        else:   # F3 risk parity: equal risk, then scale the book to the target
            vq = np.where(np.isnan(v), s['q60'], v); vb = s['b60']
            iq, ib = 1 / vq, 1 / vb
            wq, wb = iq / (iq + ib), ib / (iq + ib)
            bv = np.sqrt((wq * vq) ** 2 + (wb * vb) ** 2 + 2 * s['corr'] * wq * wb * vq * vb)
            k = c['tgt'] / bv
            e, bond = wq * k, wb * k
            e = np.minimum(e, c['L'])
            # fit in 100% of capital (equity at up to 3x via TQQQ): scale both legs together, keeping the risk split
            f = np.minimum(1.0, 1.0 / np.maximum(bond + e / 3, 1e-9))
            e, bond = e * f, bond * f
            ok = ~(np.isnan(e) | np.isnan(bond)); e = np.where(ok, e, 1.0); bond = np.where(ok, bond, 0.0)
    cap = np.maximum(0.0, 1 - bond)
    qqq, qld, tq = equity_weights(np.maximum(e, 0), cap)
    w = np.stack([qqq, qld, tq, bond, 1 - qqq - qld - tq - bond], -1)
    return w, key


def grid():
    out = []
    for tgt, L, est in itertools.product((0.15, 0.20, 0.25, 0.30, 0.35, 0.40), (1.0, 1.5, 2.0, 3.0), ('vol20', 'max10_30', 'ewma')):
        out.append(dict(fam='F1', tgt=tgt, L=L, est=est))
    for tgt, L, est, gg in itertools.product((0.20, 0.25, 0.30, 0.35, 0.40), (2.0, 3.0), ('max10_30', 'ewma'), (0.0, 0.5)):
        out.append(dict(fam='F2', tgt=tgt, L=L, est=est, g=gg))
    for tgt, L, est in itertools.product((0.10, 0.15, 0.20, 0.25), (2.0, 3.0), ('vol20', 'max10_30')):
        out.append(dict(fam='F3', tgt=tgt, L=L, est=est))
    for tq in (0.2, 0.3, 0.4, 0.55):
        out.append(dict(fam='F4', tq=tq))
    for c in out:
        c['name'] = label(c)
    return out


def label(c):
    if c['fam'] == 'F4':
        return f"F4 static {int(c['tq']*100)}% TQQQ / {int(round((1-c['tq'])*100))}% TLT"
    base = f"{c['fam']} target {int(c['tgt']*100)}% cap {c['L']:g}x {c['est']}"
    return base + (f" gate x{c['g']:g}" if c['fam'] == 'F2' else '')


# ------------------------------------------------------------------ evaluation
RATES = 'hist'


def paths(panel, P, block, seed, years=10):
    rng = np.random.default_rng(seed)
    T = MC.WARMUP + int(round(252 * years)) + 1
    src = np.arange(1, len(panel['dates']))
    idx = src[MC.bootstrap_idx(rng, len(src), P, T, block)]
    g = {k: panel[k][idx] for k in panel if k != 'dates'}
    return simulate_rates(g, panel) if RATES == 'sim' else g


def run(g, s, c, start=MC.WARMUP):
    w, key = weights(s, c)
    legs = np.stack([g['qqq_leg'], g['qld'], g['tqqq'], g['tlt'], g['cash']], -1)
    r, trades = MC.run_strategy(w, key, legs, start)
    m = MC.stats(r); m['trades'] = trades; m['lev'] = (w[:, start:-1, 0] + 2 * w[:, start:-1, 1] + 3 * w[:, start:-1, 2]).mean(1)
    m['bond'] = w[:, start:-1, 3].mean(1)
    return m


def cmd_search(a):
    panel = load_panel('search'); cands = grid(); res = {c['name']: {} for c in cands}
    bench = {}
    for L in BLOCKS:
        t0 = time.time(); g = paths(panel, a.paths, L, a.seed + L); s = signals(g)
        q = MC.stats(g['qqq_tr'][:, MC.WARMUP + 1:]); bench[L] = dict(mdd=float(np.median(q['mdd'])), sharpe=float(np.median(q['sharpe'])), cagr=float(np.median(q['cagr'])))
        for c in cands:
            m = run(g, s, c)
            res[c['name']][L] = dict(p_cagr=float((m['cagr'] > q['cagr']).mean()), p_sharpe=float((m['sharpe'] > q['sharpe']).mean()),
                                     cagr=float(np.median(m['cagr'])), sharpe=float(np.median(m['sharpe'])), mdd=float(np.median(m['mdd'])),
                                     mdd_p5=float(np.percentile(m['mdd'], 5)), lev=float(np.median(m['lev'])), trades=float(np.median(m['trades'])) / 10)
        print(f"search L{L}: {len(cands)} candidates [{time.time()-t0:.0f}s]", flush=True)
    rows = []
    for c in cands:
        r = res[c['name']]
        ok = all(r[L]['mdd'] >= bench[L]['mdd'] and r[L]['sharpe'] >= bench[L]['sharpe'] for L in BLOCKS)
        rows.append(dict(name=c['name'], cfg=c, ok=ok, worst=min(r[L]['p_cagr'] for L in BLOCKS), mean=float(np.mean([r[L]['p_cagr'] for L in BLOCKS])), r=r))
    rows.sort(key=lambda x: (x['ok'], x['worst'], x['mean']), reverse=True)
    lines = [f"# New-strategy search {time.strftime('%Y-%m-%d %H:%M')} (panel {SEARCH[0]}..{SEARCH[1]}, paths={a.paths}, {len(cands)} candidates)", "",
             "QQQ median CAGR / Sharpe / MaxDD by block: " + "; ".join(f"L{L} {bench[L]['cagr']*100:.1f}% / {bench[L]['sharpe']:.2f} / {bench[L]['mdd']*100:.1f}%" for L in BLOCKS), "",
             "| rank | candidate | passes constraints | worst-L P(CAGR>QQQ) | " + " | ".join(f"L{L} P / CAGR / MaxDD" for L in BLOCKS) + " | lev | trades/yr |",
             "|---" * (6 + len(BLOCKS)) + "|"]
    for i, x in enumerate(rows[:25] + [y for y in rows[25:] if y['cfg']['fam'] == 'F4']):
        r = x['r']
        lines.append(f"| {i+1 if i < 25 else '—'} | {x['name']} | {'yes' if x['ok'] else 'no'} | {x['worst']*100:.0f}% | "
                     + " | ".join(f"{r[L]['p_cagr']*100:.0f}% / {r[L]['cagr']*100:.1f}% / {r[L]['mdd']*100:.0f}%" for L in BLOCKS)
                     + f" | {r[60]['lev']:.2f}x | {r[60]['trades']:.0f} |")
    best_per_fam = {}
    for x in rows:
        best_per_fam.setdefault(x['cfg']['fam'], x)
    lines += ["", "Best per family: " + "; ".join(f"{f}: {x['name']} (passes {x['ok']}, worst {x['worst']*100:.0f}%)" for f, x in sorted(best_per_fam.items()))]
    txt = "\n".join(lines); print(txt)
    with open(os.path.join(LOG, f'monte_carlo_new_search{SUFFIX}.log'), 'w') as fh:
        fh.write(txt + "\n\n```json\n" + json.dumps({'winner': rows[0]['cfg'], 'per_family': {f: x['cfg'] for f, x in best_per_fam.items()},
                                                       'bench': bench, 'all': [{k: v for k, v in x.items() if k != 'r'} | {'r': x['r']} for x in rows]}, indent=1) + "\n```\n")


def cmd_confirm(a):
    j = json.loads(open(os.path.join(LOG, f'monte_carlo_new_search{SUFFIX}.log')).read().split('```json')[1].split('```')[0])
    picks = [j['winner']] + [c for f, c in sorted(j['per_family'].items()) if c['name'] != j['winner']['name']]
    lines = [f"# New-strategy confirmation {time.strftime('%Y-%m-%d %H:%M')} (real ETFs {REAL0}..2026-08, paths={a.paths})", "",
             f"Search winner: **{j['winner']['name']}**. Other rows: best of each family on the search.", ""]
    for kind in ('real', 'full'):
        panel = load_panel(kind)
        lines += [f"## {kind} panel ({panel['dates'][0]}..{panel['dates'][-1]})", "",
                  "| block | series | median CAGR | p5 CAGR | median Sharpe | median MaxDD | p5 MaxDD | P(CAGR > QQQ) | P(Sharpe > QQQ) | P(MaxDD shallower than QQQ) | P(CAGR > live) |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        for L in BLOCKS:
            g = paths(panel, a.paths, L, a.seed + 1000 + L); s = signals(g)
            q = MC.stats(g['qqq_tr'][:, MC.WARMUP + 1:]); spy = MC.stats(g['spy'][:, MC.WARMUP + 1:])
            sig = MC.signals(100 * np.cumprod(1 + g['qqq'], 1), 100 * np.cumprod(1 + g['ew'], 1))
            ll = np.stack([g['core'], g['tqqq'], g['qld'], g['xlu'], g['cash']], -1)
            lr, _ = MC.run_strategy(MC.target_weights(sig, MC.LIVE), MC.regime_key(sig, MC.LIVE), ll, MC.WARMUP); live = MC.stats(lr)
            ser = [(c['name'] + (' (winner)' if c['name'] == j['winner']['name'] else ''), run(g, s, c)) for c in picks]
            ser += [('live design 2026-10-22', live), ('QQQ', q), ('SPY', spy)]
            for n, m in ser:
                lines.append(f"| L{L} | {n} | {np.median(m['cagr'])*100:.1f}% | {np.percentile(m['cagr'],5)*100:.1f}% | {np.median(m['sharpe']):.2f} | "
                             f"{np.median(m['mdd'])*100:.1f}% | {np.percentile(m['mdd'],5)*100:.1f}% | {(m['cagr'] > q['cagr']).mean()*100:.0f}% | "
                             f"{(m['sharpe'] > q['sharpe']).mean()*100:.0f}% | {(m['mdd'] > q['mdd']).mean()*100:.0f}% | {(m['cagr'] > live['cagr']).mean()*100:.0f}% |")
            print(f"confirm {kind} L{L} done", flush=True)
        lines.append("")
    # single historical path, real ETFs
    panel = load_panel('real'); g = {k: panel[k][None] for k in panel if k != 'dates'}; s = signals(g)
    s1 = next(i for i, x in enumerate(panel['dates']) if x >= '2015-11-02') + 0
    lines += ["## Single historical path, real ETFs (warm-up inside the window, scored from 2016-11)", "",
              "| series | CAGR | Sharpe | MaxDD |", "|---|---|---|---|"]
    st = 280
    for c in picks:
        m = run(g, s, c, start=st)
        lines.append(f"| {c['name']} | {m['cagr'][0]*100:.1f}% | {m['sharpe'][0]:.2f} | {m['mdd'][0]*100:.1f}% |")
    q = MC.stats(g['qqq_tr'][:, st + 1:]); lines.append(f"| QQQ | {q['cagr'][0]*100:.1f}% | {q['sharpe'][0]:.2f} | {q['mdd'][0]*100:.1f}% |")
    lines.append(f"\n(scored {panel['dates'][st+1]}..{panel['dates'][-1]})")
    txt = "\n".join(lines); print(txt)
    with open(os.path.join(LOG, f'monte_carlo_new_confirm{SUFFIX}.log'), 'w') as fh:
        fh.write(txt + "\n")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('search', 'confirm'))
    ap.add_argument('--paths', type=int, default=400)
    ap.add_argument('--seed', type=int, default=20261022)
    ap.add_argument('--rates', choices=('hist', 'sim'), default='hist')
    a = ap.parse_args(argv)
    global RATES, SUFFIX
    RATES, SUFFIX = a.rates, ('' if a.rates == 'hist' else '_simrates')
    (cmd_search if a.cmd == 'search' else cmd_confirm)(a)


if __name__ == '__main__':
    main(sys.argv[1:])
