"""Is 50/50 core/TQQQ the right A row? Decay, drift, beta-matching, everything.

Owner (2026-09-22): "So based on these data, is 50/50 the right ratio? Consider
drift decay everything."

Four questions, one harness (drawdown_study.sim, which reproduces the asserted
baselines), both eras (real = SPMO/TQQQ 2015-11+, proxy = QQQ/synthetic-3x
2000+). Sharpe is EXCESS of BOXX throughout (scale-invariant, cannot be gamed by
de-levering).

  1  THE DIAL.  core/TQQQ from 80/20 to 20/80. CAGR, excess Sharpe (full /
     search / holdout), MaxDD, and MaxDD against the flat-leverage null: the
     live row simply scaled up or down to the same CAGR (k > 1 borrows at the
     BOXX rate -- a theoretical null, not a buyable one).
  2  DECAY.     Realized TQQQ drag vs 3x QQQ, split by state A vs everything
     else, and what it costs the book at each ratio.
  3  DRIFT.     Realized vs target TQQQ weight inside A, band fires, cost, at
     each ratio.
  4  BETA-MATCHED ALTERNATIVES.  The nominal-beta-2 family SPMO = TQQQ = c,
     QLD = 1 - 2c (c = 0.5 is live, c = 0 is 100% QLD): is there a cheaper way
     to hold the same exposure with less decay?
  5  Paired block bootstrap on the excess-Sharpe differences that matter.

NOTHING IS APPLIED. Design frozen to 7 December. Research only.

Usage:  python3 paper-track/a_ratio_study.py
"""
import os, sys, io, math, time, contextlib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)
sys.path.insert(0, 'paper-track')
os.environ.setdefault('TDT_STAGE', 'none')
os.environ['DDS_STAGE'] = 'none'
T0 = time.time()

LOG = 'paper-track/research_notes/a_ratio_study_run.log'
_lf = open(LOG, 'w')
def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s); _lf.write(s + '\n'); _lf.flush()

_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    import drawdown_study as DS
from d_substate_fresh import rows, RDAYS, SEARCH, HOLDOUT
from drift_band_test import annual_stats
from block_bootstrap import boot, stats as _bst
def stats_lr(x): return _bst(x)[0]

sim = DS.sim; TDT = DS.TDT
H = ('real', 'proxy')
DATES = {'real': RDAYS[:-1], 'proxy': [r['d'] for r in rows]}

def _qret(h):
    if h == 'proxy':
        return {r['d']: r['qqq'] for r in rows}
    px = TDT.RQQQ; ds = RDAYS
    return {ds[i]: px[ds[i + 1]] / px[ds[i]] - 1 for i in range(len(ds) - 1)}
QR = {h: _qret(h) for h in H}

DET = {h: sim(h, detail=True)[0] for h in H}
CASHR = {h: [x['lr'][4] for x in DET[h]] for h in H}

def _sh(x):
    if len(x) < 3: return float('nan')
    m = sum(x) / len(x)
    v = (sum((a - m) ** 2 for a in x) / (len(x) - 1)) ** 0.5
    return (m * math.sqrt(252)) / v if v else float('nan')

def xs(h, ser):
    return [a - c for a, c in zip(ser, CASHR[h])]

def sharpe(h, ser, lo=None, hi=None):
    return _sh([a - c for a, c, d in zip(ser, CASHR[h], DATES[h])
                if (lo is None or d >= lo) and (hi is None or d <= hi)])

def score(h, **kw):
    ser, expo, reb = sim(h, **kw)
    c, s, m = annual_stats(ser)
    return dict(cagr=c, mdd=m, exp=expo, reb=reb, ser=ser,
                F=sharpe(h, ser), S=sharpe(h, ser, lo=SEARCH[0]), H=sharpe(h, ser, hi=HOLDOUT[1]))

LIVE = {h: score(h) for h in H}
assert abs(LIVE['real']['cagr'] - 0.3730) < 0.0006 and abs(LIVE['real']['mdd'] + 0.186) < 0.0006, LIVE['real']
assert abs(LIVE['proxy']['cagr'] - 0.2546) < 0.0006 and abs(LIVE['proxy']['mdd'] + 0.270) < 0.0006, LIVE['proxy']

# flat-leverage null: the live design scaled by k (all risky legs), MaxDD at matched CAGR
KS = [0.50, 0.60, 0.70, 0.80, 0.90, 1.00, 1.10, 1.20, 1.30, 1.40, 1.50]
FRONT = {h: sorted(((lambda e: (e['cagr'], e['mdd']))(score(h, scale=k))) for k in KS) for h in H}
def front_dd(h, cagr):
    pts = FRONT[h]
    if cagr <= pts[0][0]: return pts[0][1]
    if cagr >= pts[-1][0]: return pts[-1][1]
    for i in range(1, len(pts)):
        if cagr <= pts[i][0]:
            f = (cagr - pts[i-1][0]) / (pts[i][0] - pts[i-1][0])
            return pts[i-1][1] + f * (pts[i][1] - pts[i-1][1])

def benches():
    out = {}
    for h in H:
        q = [QR[h].get(d, 0.0) for d in DATES[h]]
        c, _, m = annual_stats(q)
        out[h] = (c, m, sharpe(h, q))
    return out

# ======================================================================== 0
log("=" * 128)
log("RESEARCH LINE a_ratio_study (2026-09-22): is 50/50 core/TQQQ the right A row? decay, drift, beta-matching")
log("=" * 128)
for h in H:
    L = LIVE[h]
    log(f"  LIVE {h:<6} CAGR {L['cagr']*100:6.2f}%  MaxDD {L['mdd']*100:6.1f}%  exSharpe F {L['F']:.3f} S {L['S']:.3f} H {L['H']:.3f}"
        f"  exp {L['exp']*100:.1f}%  reb/yr {L['reb']:.1f}")
BN = benches()
for h in H:
    c, m, s = BN[h]
    log(f"  QQQ  {h:<6} CAGR {c*100:6.2f}%  MaxDD {m*100:6.1f}%  exSharpe {s:.3f}   (same dates, buy-and-hold)")
log(f"  proxy core = QQQ total return, proxy TQQQ = synthetic 3x; real core = SPMO, real TQQQ = the fund.")
log(f"  flat-leverage null (live x k): " + ' | '.join(
    f"{h}: " + ', '.join(f"{c*100:.1f}%/{m*100:.1f}%" for c, m in FRONT[h]) for h in H))

# ======================================================================== 1
log("\n" + "=" * 128)
log("1  THE DIAL: core/TQQQ in A (the trim, vol target, band, every other state unchanged)")
log("   edge = MaxDD minus the flat-leverage null's MaxDD at the same CAGR (POSITIVE = shallower than just levering live)")
log("=" * 128)
DIAL = [0.20, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.80]
RES1 = {}
for h in H:
    log(f"\n  {h.upper()}")
    log(f"  {'core/TQQQ':>10}{'CAGR':>9}{'dCAGR':>8}{'MaxDD':>8}{'edge':>7}{'exSh F':>9}{'S':>7}{'H':>7}{'dF':>8}{'exp':>7}{'reb':>6}")
    for t in DIAL:
        c = 1 - t
        e = score(h, a_row=(c, t, 0, 0, 0)); RES1[(h, t)] = e
        edge = (e['mdd'] - front_dd(h, e['cagr'])) * 100
        tag = '  <- LIVE' if abs(t - 0.5) < 1e-9 else ''
        Hs = f"{e['H']:.3f}" if e['H'] == e['H'] else '  -  '
        log(f"  {int(round(c*100)):>5}/{int(round(t*100)):<4}{e['cagr']*100:8.2f}%{(e['cagr']-LIVE[h]['cagr'])*100:+8.2f}"
            f"{e['mdd']*100:7.1f}%{edge:+7.2f}{e['F']:9.3f}{e['S']:7.3f}{Hs:>7}{e['F']-LIVE[h]['F']:+8.3f}"
            f"{e['exp']*100:6.1f}%{e['reb']:6.1f}{tag}")
    # marginal CAGR per +10pp TQQQ
    ms = []
    for a, b in zip(DIAL[:-1], DIAL[1:]):
        ms.append(f"{int(a*100)}->{int(b*100)}: {(RES1[(h,b)]['cagr']-RES1[(h,a)]['cagr'])*100/((b-a)*10):+.2f}")
    log("  marginal CAGR per +10pp TQQQ:  " + '  '.join(ms))

# ======================================================================== 2
log("\n" + "=" * 128)
log("2  DECAY: realized TQQQ log return minus 3 x QQQ log return, by where the strategy actually holds it")
log("=" * 128)
def is_A(x): return (x['eff'] == 'A') and not x['gate'] and x['st'] not in 'EF'
for h in H:
    det = DET[h]
    for lab, sel in (('state A days', is_A), ('all other days', lambda x: not is_A(x)), ('every day', lambda x: True)):
        n = 0; lt = lq = 0.0; qs = []
        for x in det:
            if not sel(x): continue
            q = QR[h].get(x['d']);
            if q is None: continue
            rt = x['lr'][1]
            lt += math.log1p(rt); lq += math.log1p(q); qs.append(q); n += 1
        if n < 20: continue
        mu = sum(qs) / n; sd = (sum((a - mu) ** 2 for a in qs) / (n - 1)) ** 0.5 * math.sqrt(252)
        drag = (lt - 3 * lq) * 252 / n
        log(f"  {h:<6} {lab:<16} n {n:5d}  QQQ vol {sd*100:5.1f}%  realized drag {drag*100:+6.2f}%/yr   "
            f"naive 3x2 s^2/2 {-3*sd*sd*100:+6.2f}%/yr")
    # what the drag costs the book at each ratio: sum over A days of held TQQQ weight x the day's drag increment
    log(f"  {h}: decay charged to the BOOK (held TQQQ weight x daily log-drag, A days only), %/yr of the whole strategy:")
    parts = []
    for t in (0.30, 0.40, 0.50, 0.60, 0.70):
        det2 = sim(h, a_row=(1 - t, t, 0, 0, 0), detail=True)[0]
        tot = 0.0
        for x in det2:
            if not is_A(x): continue
            q = QR[h].get(x['d'])
            if q is None: continue
            tot += x['held'][1] * (math.log1p(x['lr'][1]) - 3 * math.log1p(q))
        parts.append(f"{int(round((1-t)*100))}/{int(round(t*100))}: {tot*252/len(det2)*100:+.2f}")
    log("     " + '   '.join(parts))

# ======================================================================== 3
log("\n" + "=" * 128)
log("3  DRIFT: inside A, how far the held TQQQ weight wanders from target, how often the band fires, what it costs")
log("   (weights are shares of the RISKY book, so the vol target and the trim do not blur the ratio)")
log("=" * 128)
log(f"  {'harness':<7}{'row':>8}{'A days':>8}{'mean held T':>13}{'p10':>7}{'p90':>7}{'A band fires/yr':>17}")
for h in H:
    for t in (0.30, 0.40, 0.50, 0.60, 0.70):
        det2 = sim(h, a_row=(1 - t, t, 0, 0, 0), detail=True)[0]
        sh = []; fires = 0; cost = 0.0; prev = None
        yrs = len(det2) / 252.0
        for x in det2:
            if is_A(x):
                rk = x['held'][0] + x['held'][1]
                if rk > 0.02: sh.append(x['held'][1] / rk)
                if prev is not None and is_A(prev) and prev['v'] == x['v'] and x['held'] != prev['post']:
                    fires += 1
            # record post-return weights to detect a trade on the next day
            lr = x['lr']; g = sum(a * b for a, b in zip(x['held'], lr)); dn = 1 + g
            x['post'] = [a * (1 + b) / dn for a, b in zip(x['held'], lr)] if dn > 0 else x['held']
            prev = x
        sh.sort(); n = len(sh)
        mean = sum(sh) / n
        log(f"  {h:<7}{int(round((1-t)*100)):>4}/{int(round(t*100)):<3}{n:>8}{mean*100:12.1f}%{sh[n//10]*100:6.1f}%{sh[9*n//10]*100:6.1f}%"
            f"{fires/yrs:>17.1f}")

# ======================================================================== 4
log("\n" + "=" * 128)
log("4  BETA-MATCHED ALTERNATIVES: nominal beta 2.0 = core + 3 TQQQ + 2 QLD. Family SPMO = TQQQ = c, QLD = 1 - 2c.")
log("   Decay load (units of s^2/2): 6 x TQQQ + 2 x QLD = 2 + 2c.  c = 0.50 is live (3.0 units), c = 0 is 100% QLD (2.0 units).")
log("   MEASURED beta to QQQ on A days is reported because SPMO's beta is not 1 -- nominal matching is not enough.")
log("=" * 128)
FAM = [0.50, 0.40, 1/3, 0.25, 0.15, 0.00]
RES4 = {}
for h in H:
    log(f"\n  {h.upper()}")
    log(f"  {'SPMO/TQQQ/QLD':>15}{'CAGR':>9}{'dCAGR':>8}{'MaxDD':>8}{'edge':>7}{'exSh F':>9}{'S':>7}{'H':>7}{'dF':>8}{'beta_A':>8}{'bp/d on A':>11}")
    for c in FAM:
        q = 1 - 2 * c
        e = score(h, a_row=(c, c, q, 0, 0)); RES4[(h, c)] = e
        det2 = sim(h, a_row=(c, c, q, 0, 0), detail=True)[0]
        # beta of the A-day book (per unit risky exposure) to QQQ
        ys = []; xs_ = []
        for x in det2:
            if not is_A(x): continue
            qv = QR[h].get(x['d'])
            if qv is None: continue
            rk = sum(x['held'][:4])
            if rk < 0.05: continue
            ys.append(sum(a * b for a, b in zip(x['held'][:4], x['lr'][:4])) / rk); xs_.append(qv)
        mx = sum(xs_) / len(xs_); my = sum(ys) / len(ys)
        beta = sum((a - mx) * (b - my) for a, b in zip(xs_, ys)) / sum((a - mx) ** 2 for a in xs_)
        edge = (e['mdd'] - front_dd(h, e['cagr'])) * 100
        Hs = f"{e['H']:.3f}" if e['H'] == e['H'] else '  -  '
        tag = '  <- LIVE' if abs(c - 0.5) < 1e-9 else ''
        log(f"  {c*100:5.1f}/{c*100:4.1f}/{q*100:5.1f}{e['cagr']*100:8.2f}%{(e['cagr']-LIVE[h]['cagr'])*100:+8.2f}"
            f"{e['mdd']*100:7.1f}%{edge:+7.2f}{e['F']:9.3f}{e['S']:7.3f}{Hs:>7}{e['F']-LIVE[h]['F']:+8.3f}{beta:8.2f}{my*1e4:11.1f}{tag}")

# ======================================================================== 5
log("\n" + "=" * 128)
log("5  PAIRED CIRCULAR BLOCK BOOTSTRAP (2000 draws, 60-day blocks) of the EXCESS-Sharpe and excess log-return difference vs live")
log("=" * 128)
CANDS = [('70/30', ('dial', 0.30)), ('60/40', ('dial', 0.40)), ('40/60', ('dial', 0.60)), ('30/70', ('dial', 0.70)),
         ('1/3 each', ('fam', 1/3)), ('100% QLD', ('fam', 0.0))]
for h in H:
    base = xs(h, LIVE[h]['ser'])
    for lab, (kind, v) in CANDS:
        e = RES1[(h, v)] if kind == 'dial' else RES4[(h, v)]
        a = xs(h, e['ser'])
        l1, l2, pl, s1, s2, ps = boot(a, base, 60, seed=(sum(map(ord, lab)) * 7919 + (1 if h == 'real' else 2)) & 0xffff)
        log(f"  {h:<6} {lab:<10} dSharpe {e['F']-LIVE[h]['F']:+.3f}  95% CI [{s1:+.3f}, {s2:+.3f}]  P(not better) {ps*100:4.0f}%"
            f"   dLogRet {(stats_lr(a)-stats_lr(base))*100:+.2f}pp/yr  95% CI [{l1*100:+.2f}, {l2*100:+.2f}]")

log(f"\n  done in {time.time()-T0:.0f}s")
