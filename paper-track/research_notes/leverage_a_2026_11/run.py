"""How much leverage should state A carry? Research only. See PLAN.md (pre-registered 2026-11-17, before any arm was run)."""
import sys, os, time
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); PT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, PT)
import numpy as np, pandas as pd
import harness_live as HL
from harness_live import MC, S, H
REFS = os.environ.get('HIGHS') == 'refs'   # second pass: highs from the file only (what the recorded L1 references had)
EXTRA = {'use_live_highs': False} if REFS else {}
LOG = open(os.path.join(HERE, 'run_refs.log' if REFS else 'run.log'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); LOG.write(s + '\n'); LOG.flush()
T0 = time.time()
NBOOT, BLOCK = 2000, 20
WINS = {'real': ('real', '2015-11-02'), 'p01': ('proxy', '2001-01-02'), 'p10': ('proxy', '2010-01-04')}
WL = list(WINS)

# ------------------------------------------------------------------ arms
ARMS = {}; FAM = {}
def arm(name, fam, **kw): ARMS[name] = kw; FAM.setdefault(fam, []).append(name)
for a, b in ((100, 0), (80, 20), (60, 40), (50, 50), (40, 60), (30, 70), (20, 80)):
    arm('LIVE A 40/60' if (a, b) == (40, 60) else f'A {a}/{b}', 'split', a_split=(a / 100, b / 100))
arm('A SPMO/QLD 50/50', 'qld', a_split=(0.5, 0.5), a_instr='QLD'); arm('A 0/100 QLD', 'qld', a_split=(0.0, 1.0), a_instr='QLD')
for c in (1.5, 1.75, 2.0, 2.25, None):
    if c != 2.0: arm(f'cap {c}' if c else 'cap none', 'cap', gross_cap=c)
FAM['cap'] = ['cap 1.5', 'cap 1.75', 'LIVE A 40/60', 'cap 2.25', 'cap none']
for c in (1.5, 1.75): arm(f'A-only cap {c}', 'acap', a_cap=c)
for sp in (60, 50, 40):
    for c in (1.75, 2.0):
        if c == 2.0: continue                       # (x, 2.0) cells are the split arms above; (40/60, 1.75) is 'cap 1.75'
        if sp == 40: continue
        arm(f'grid {sp}/{100-sp} cap {c}', 'grid', a_split=(sp / 100, 1 - sp / 100), gross_cap=c)
GRID_CELLS = {('60/40', 2.0): 'A 60/40', ('50/50', 2.0): 'A 50/50', ('40/60', 2.0): 'LIVE A 40/60', ('40/60', 1.75): 'cap 1.75',
              ('60/40', 1.75): 'grid 60/40 cap 1.75', ('50/50', 1.75): 'grid 50/50 cap 1.75'}
LIVE = 'LIVE A 40/60'
for _k in ARMS: ARMS[_k].update(EXTRA)
FAMORDER = {'split': ['A 100/0', 'A 80/20', 'A 60/40', 'A 50/50', LIVE, 'A 30/70', 'A 20/80'], 'cap': FAM['cap'],
            'acap': ['A-only cap 1.5', 'A-only cap 1.75', LIVE], 'qld': ['A 0/100 QLD', 'A SPMO/QLD 50/50']}

# ------------------------------------------------------------------ engine (copy of MC.run_strategy + one-way turnover record)
def engine(b, s0, e=None):
    W, key, L = b['W'], b['key'], b['L']; T = len(W) if e is None else e + 1
    h = W[s0].copy(); cost = MC.COST; out = np.zeros(T - s0 - 1); trades = 0; turn = 0.0
    for t in range(s0, T - 1):
        if t > s0:
            tgt = W[t]; drift = np.abs(tgt - h).sum()
            if key[t] != key[t - 1] or drift > S.REBALANCE_DRIFT_BAND or ((tgt == 0) & (h > S.ZERO_LEG_EPS)).any():
                cost = MC.COST * drift; h = tgt.copy(); trades += 1; turn += drift
            else: cost = 0.0
        r = L[t + 1]; g = float((h * r).sum()); out[t - s0] = (1 + g) * (1 - cost) - 1; h = h * (1 + r) / (1 + g)
    yrs = (T - s0 - 1) / 252
    return out, trades / yrs, turn / yrs
def fast(b, s0):
    r, tr = MC.run_strategy(b['W'][None], b['key'][None], b['L'][None], s0); return r[0], tr[0] / (len(r[0]) / 252)

_B = {}
def built(track, kw):
    k = (track, tuple(sorted(kw.items(), key=lambda x: x[0])));
    if k not in _B: _B[k] = HL.build(track, **kw)
    return _B[k]
def s0_of(track, d0): ds = built(track, {})['ds']; return next(i for i, d in enumerate(ds) if d >= d0)
def avg_gross(track, kw, d0):
    b = built(track, kw); s0 = s0_of(track, d0); return float(b['gross'][s0:-1].mean())

# ------------------------------------------------------------------ metrics
def rollmin(r, n): return float(np.expm1(np.convolve(np.log1p(r), np.ones(n), 'valid')).min())
def mdd(r): nav = np.cumprod(1 + r); return float((nav / np.maximum.accumulate(np.concatenate([[1.0], nav]))[1:] - 1).min())
def sharpe(r): return float(r.mean() / r.std(ddof=1) * 252 ** .5)
def metrics(r):
    nav = np.cumprod(1 + r)
    return dict(c=float(nav[-1] ** (252 / len(r)) - 1), sh=sharpe(r), dd=mdd(r), v=float(r.std(ddof=1) * 252 ** .5), w1=float(r.min()),
                w5=rollmin(r, 5), w20=rollmin(r, 20))

def run_arm(name, kw, win, full=True):
    track, d0 = WINS[win]; b = built(track, kw); s0 = s0_of(track, d0)
    if full: r, tpy, turn = engine(b, s0)
    else: r, tpy = fast(b, s0); turn = np.nan
    ds = b['ds'][s0 + 1:]
    res = dict(r=r, ds=ds, tpy=tpy, turn=turn, g=b['gross'][s0:-1], am=b['a_mask'][s0:-1], m=metrics(r), kw=kw)
    res['lm'] = ((b['eff'] == 0) | ((b['eff'] == 3) & ~b['gate']))[s0:-1]; res['avgg'] = float(res['g'].mean()); res['pa'] = float(res['am'].mean()); res['ga'] = float(res['g'][res['am']].mean()) if res['am'].any() else np.nan
    return res

# sanity: engine copy == MC.run_strategy == HL.run_live
_chk = HL.run_live('real', **EXTRA); _r = run_arm(LIVE, ARMS[LIVE], 'real')
assert np.allclose(_chk[0], _r['r']) and abs(_chk[2] - _r['tpy']) < 1e-9, 'engine copy mismatch'
_p = HL.run_live('proxy', d0='2010-01-04', **EXTRA); assert np.allclose(_p[0], run_arm(LIVE, ARMS[LIVE], 'p10')['r'])

# ------------------------------------------------------------------ matched de-levers
def match(kw, win, target, flavor):
    track, d0 = WINS[win]
    if flavor == 'flat':
        lo, hi = 0.2, 1.5
        f = lambda x: avg_gross(track, dict(kw, risky_scale=x), d0)
    else:
        lo, hi = 0.02, kw.get('vol_target', 0.20)
        f = lambda x: avg_gross(track, dict(kw, vol_target=x), d0)
    if not (f(lo) <= target <= f(hi) + 1e-9): return None
    for _ in range(22):
        mid = (lo + hi) / 2
        if f(mid) < target: lo = mid
        else: hi = mid
    x = (lo + hi) / 2
    return x, dict(kw, **({'risky_scale': x} if flavor == 'flat' else {'vol_target': x}))

R = {}
for name, kw in ARMS.items():
    for w in WL: R[(name, w)] = run_arm(name, kw, w)
log('=' * 150); log('run.py: leverage in state A (2026-11-17). PLAN.md pre-registered; research only, nothing adopted. HIGHS PASS: ' + ('REFS-STYLE (file highs only, 50 late sessions read the close; reproduces the recorded L1 references)' if REFS else 'DEFAULT (complete highs)')); log('=' * 150)
log(f'(arms computed {time.time()-T0:.0f}s)')
for w in WL:
    x = R[(LIVE, w)]; log(f"window {w}: returns {x['ds'][0]}..{x['ds'][-1]} ({len(x['ds'])} sessions); live: {x['m']['c']*100:.1f}% / {x['m']['sh']:.3f} / {x['m']['dd']*100:.1f}%")
LOWER = {}   # (name, win) -> True when avg gross at least 0.02 below live
M = {}       # (name, win, flavor) -> (param, result)
for name in ARMS:
    for w in WL:
        if name != LIVE and R[(name, w)]['avgg'] <= R[(LIVE, w)]['avgg'] - 0.02:
            LOWER[(name, w)] = True
            for fl in ('flat', 'vt'):
                m = match(ARMS[LIVE], w, R[(name, w)]['avgg'], fl)
                if m: M[(name, w, fl)] = (m[0], run_arm(name + ' matched', m[1], w))
log(f'(matched de-levers computed {time.time()-T0:.0f}s: {len(M)} of {2*len(LOWER)})')

# ------------------------------------------------------------------ master tables
HDR = f"  {'arm':<26}{'CAGR':>7} {'Sharpe':>6} {'maxDD':>7} {'vol':>6} {'avgG':>5} {'worst1':>7} {'worst5':>7} {'worst20':>8} {'inA%':>5} {'Agross':>6} {'tr/yr':>6} {'turn/yr':>7}"
def line(lab, x):
    m = x['m']
    return (f"  {lab:<26}{m['c']*100:6.1f}% {m['sh']:6.3f} {m['dd']*100:6.1f}% {m['v']*100:5.1f}% {x['avgg']:5.2f} {m['w1']*100:6.2f}% {m['w5']*100:6.1f}% {m['w20']*100:7.1f}% "
            f"{x['pa']*100:5.1f} {x['ga']:6.2f} {x['tpy']:6.1f} {x['turn']:7.1f}")
for w in WL:
    log(f"\n=== MASTER TABLE, window {w} ({R[(LIVE, w)]['ds'][0]}..{R[(LIVE, w)]['ds'][-1]}). avgG = mean target equity-like gross (SPMO 1x, TQQQ 3x, QLD 2x, XLU 1x, QQQ legs 1x; no VIXY/cash). "
           f"Matched rows: plain de-lever of the live book to the arm's avgG (flat = risky legs x s; vt = vol target lowered) ===")
    log(HDR)
    for fam, names in (('split', FAMORDER['split']), ('qld', FAMORDER['qld']), ('cap', FAMORDER['cap']), ('acap', FAMORDER['acap']),
                       ('grid', ['grid 60/40 cap 1.75', 'grid 50/50 cap 1.75'])):
        log(f'  -- {fam}')
        for n in names:
            log(line(n, R[(n, w)]))
            for fl in ('flat', 'vt'):
                if (n, w, fl) in M:
                    p, x = M[(n, w, fl)]; log(line(f"   matched {fl} {'s' if fl=='flat' else 'vt'}={p:.3f}", x))
    log("  -- joint grid (A split x cap), CAGR / Sharpe / maxDD / worst20 / avgG")
    for sp in ('60/40', '50/50', '40/60'):
        cells = []
        for c in (1.75, 2.0):
            x = R[(GRID_CELLS[(sp, c)], w)]; m = x['m']
            cells.append(f"cap {c}: {m['c']*100:5.1f}% {m['sh']:.3f} {m['dd']*100:6.1f}% {m['w20']*100:6.1f}% {x['avgg']:.2f}")
        log(f"   A {sp:<6} " + ' | '.join(cells))

# ------------------------------------------------------------------ frontier / cost per point
log('\n=== FRONTIER: return given up per point of drawdown avoided. Lower-leverage arms only (avgG >= 0.02 below live). '
    'dCAGR = arm - live (pp); DDav = max-DD points avoided (arm DD - live DD, + = shallower); W20av likewise for the worst 20 sessions. '
    'cost/pp = CAGR given up per 1 pp avoided (n/a if nothing avoided). "beats" = arm cost/pp lower than the matched flat de-lever ===')
def cost(x, live, key):
    dc = (live['m']['c'] - x['m']['c']) * 100; av = (x['m'][key] - live['m'][key]) * 100
    return dc, av, (dc / av if av > 0.005 else np.nan)
FR = {}
for w in WL:
    lv = R[(LIVE, w)]
    log(f"\n window {w}  live CAGR {lv['m']['c']*100:.1f}% maxDD {lv['m']['dd']*100:.1f}% worst20 {lv['m']['w20']*100:.1f}% avgG {lv['avgg']:.2f}")
    log(f"  {'arm':<24}{'avgG':>5} {'dCAGR':>7} | {'DDav':>6} {'cost/pp':>8} | {'matched-flat: dCAGR':>20} {'DDav':>6} {'cost/pp':>8} {'beats':>6} | {'W20av':>6} {'cost/pp':>8} | {'matched: W20av':>14} {'cost/pp':>8} {'beats':>6} | {'matched-vt: DDav':>16} {'cost/pp':>8}")
    for n in ARMS:
        if (n, w) not in LOWER: continue
        x = R[(n, w)]; dc, dd_av, c_dd = cost(x, lv, 'dd'); _, w_av, c_w = cost(x, lv, 'w20')
        s = f"  {n:<24}{x['avgg']:5.2f} {-dc:+6.2f}p | {dd_av:+5.2f}p {c_dd:8.2f} | "
        if (n, w, 'flat') in M:
            mx = M[(n, w, 'flat')][1]; mdc, mdd_av, mc_dd = cost(mx, lv, 'dd'); _, mw_av, mc_w = cost(mx, lv, 'w20')
            bt_dd = (c_dd < mc_dd) if not (np.isnan(c_dd) or np.isnan(mc_dd)) else None
            bt_w = (c_w < mc_w) if not (np.isnan(c_w) or np.isnan(mc_w)) else None
            s += f"{-mdc:+19.2f}p {mdd_av:+5.2f}p {mc_dd:8.2f} {str(bt_dd):>6} | {w_av:+5.2f}p {c_w:8.2f} | {mw_av:+13.2f}p {mc_w:8.2f} {str(bt_w):>6} | "
            FR[(n, w)] = dict(dc=-dc, dd_av=dd_av, c_dd=c_dd, w_av=w_av, c_w=c_w, mdc=-mdc, mdd_av=mdd_av, mc_dd=mc_dd, mw_av=mw_av, mc_w=mc_w, bt_dd=bt_dd, bt_w=bt_w)
        else: s += f"{'n/a':>20} {'':>6} {'':>8} {'':>6} | {w_av:+5.2f}p {c_w:8.2f} | {'':>14} {'':>8} {'':>6} | "
        if (n, w, 'vt') in M:
            vx = M[(n, w, 'vt')][1]; _, vdd, vc = cost(vx, lv, 'dd'); s += f"{vdd:+15.2f}p {vc:8.2f}"
        log(s)
    log("  frontier points, sorted by max DD (live, arms, matched flat): CAGR / maxDD / worst20 / avgG")
    pts = [('LIVE', lv)] + [(n, R[(n, w)]) for n in ARMS if n != LIVE] + [(f'matched({n})', M[(n, w, 'flat')][1]) for n in ARMS if (n, w, 'flat') in M]
    for lab, x in sorted(pts, key=lambda p: p[1]['m']['dd']):
        log(f"   {lab:<34}{x['m']['c']*100:6.1f}% {x['m']['dd']*100:6.1f}% {x['m']['w20']*100:7.1f}% {x['avgg']:5.2f}")

# ------------------------------------------------------------------ calm-crack days
dd_ = pd.read_csv(os.path.join(PT, 'research_notes', 'vol_predict_2026_11', 'days.csv'), index_col=0)
CRACK = set(dd_.index[(dd_.p_vix < 20) & (dd_.ret <= -0.03)]); DN2 = set(dd_.index[dd_.ret <= -0.02])
log(f'\n=== CALM-CRACK DAYS: prior-day VIX < 20 and QQQ <= -3% (days.csv): {len(CRACK)} days since 1999. Book return on those days per arm: mean, total (sum of daily returns), '
    f'and share of the arm\'s summed return on ALL QQQ <= -2% days that falls on them ===')
CK = {}
for w in WL:
    ds = R[(LIVE, w)]['ds']; cm = np.array([d in CRACK for d in ds]); dm = np.array([d in DN2 for d in ds]); qq = dd_.ret.reindex(ds).values
    log(f"\n window {w}: crack days {int(cm.sum())}, QQQ<=-2% days {int(dm.sum())}; QQQ mean on crack days {qq[cm].mean()*100:+.2f}%, total {qq[cm].sum()*100:+.1f}%; QQQ sum on -2% days {qq[dm].sum()*100:+.1f}%")
    log(f"  {'arm':<26}{'mean%':>8} {'total%':>8} {'all-2%days total%':>18} {'share':>7} {'share, lev.days':>16} {'crack days lev (A/ungated D)':>29}")
    rows = [(n, R[(n, w)]) for n in ARMS] + [(f'matched flat({n})', M[(n, w, 'flat')][1]) for n in ARMS if (n, w, 'flat') in M]
    for n, x in rows:
        r = x['r']; tot = r[cm].sum() * 100; allt = r[dm].sum() * 100; sh = tot / allt * 100 if allt < 0 else np.nan
        CK[(n, w)] = (r[cm].mean() * 100, tot, allt, sh)
        lm = x['lm']; lt = r[dm & lm].sum() * 100; shl = r[cm & lm].sum() * 100 / lt * 100 if lt < 0 else np.nan
        CK[(n, w)] = CK[(n, w)] + (shl,)
        log(f"  {n:<26}{r[cm].mean()*100:+8.3f} {tot:+8.2f} {allt:+18.2f} {sh:6.1f}% {shl:15.1f}% {int((cm & lm).sum()):>10} of {int(lm[cm].size and cm.sum())} (lev -2% days {int((dm & lm).sum())})")

# ------------------------------------------------------------------ stress
def per(x, a, b):
    m = np.array([a <= d <= b for d in x['ds']]); return (np.prod(1 + x['r'][m]) - 1) * 100 if m.any() else np.nan
log('\n=== STRESS: calendar 2022, Feb-Mar 2020, 2026-11-05 (single day), 2026-10-30..2026-11-05 (5 sessions); % return of the arm (and matched flat de-lever) ===')
for w in ('real', 'p01'):
    log(f"\n window {w}" + ('   (2026 rows in real only)' if w == 'p01' else ''))
    log(f"  {'arm':<26}{'2022':>8} {'Feb-Mar20':>10} {'11-05':>8} {'10-30..11-05':>13}")
    rows = [(n, R[(n, w)]) for n in ARMS] + [(f'matched flat({n})', M[(n, w, 'flat')][1]) for n in ARMS if (n, w, 'flat') in M]
    for n, x in rows:
        log(f"  {n:<26}{per(x,'2022-01-01','2022-12-31'):+8.1f} {per(x,'2020-02-01','2020-03-31'):+10.1f} {per(x,'2026-11-05','2026-11-05'):+8.2f} {per(x,'2026-10-30','2026-11-05'):+13.2f}")

# ------------------------------------------------------------------ robustness
def boot_idx(N, n=NBOOT, block=BLOCK, seed=17):
    rng = np.random.default_rng(seed); nb = -(-N // block); st = rng.integers(N, size=(n, nb))
    return ((st[:, :, None] + np.arange(block)) % N).reshape(n, -1)[:, :N]
BI = {}
def boot(ra, rb):
    N = len(ra)
    if N not in BI: BI[N] = boot_idx(N)
    idx = BI[N]; out = np.empty(len(idx))
    for i in range(0, len(idx), 250):
        a, b = ra[idx[i:i + 250]], rb[idx[i:i + 250]]
        out[i:i + 250] = (a.mean(1) / a.std(1, ddof=1) - b.mean(1) / b.std(1, ddof=1)) * 252 ** .5
    return float(np.median(out)), float((out <= 0).mean())
def dsh(ra, rb, ds):
    n = len(ra); h = n // 2; x = np.array([not d.startswith('2020') for d in ds])
    return sharpe(ra) - sharpe(rb), sharpe(ra[:h]) - sharpe(rb[:h]), sharpe(ra[h:]) - sharpe(rb[h:]), sharpe(ra[x]) - sharpe(rb[x])
log(f'\n=== ROBUSTNESS of the Sharpe difference, lower-leverage arms. dSh = arm - live (full, first half, second half, ex-2020); bootstrap = {NBOOT} paths, {BLOCK}-session circular blocks, paired: median dSh and P(dSh <= 0). '
    f'"vs matched" = arm - matched flat de-lever: full dSh, bootstrap median, P(<=0) ===')
RB = {}
for w in WL:
    lv = R[(LIVE, w)]; log(f'\n window {w}')
    log(f"  {'arm':<24}{'dSh':>7} {'h1':>7} {'h2':>7} {'ex2020':>7} {'bootmed':>8} {'P<=0':>6} | {'vs matched: dSh':>16} {'bootmed':>8} {'P<=0':>6}")
    for n in ARMS:
        if (n, w) not in LOWER: continue
        x = R[(n, w)]; d = dsh(x['r'], lv['r'], x['ds']); bm, bp = boot(x['r'], lv['r']); RB[(n, w)] = (d, bm, bp)
        s = f"  {n:<24}{d[0]:+7.3f} {d[1]:+7.3f} {d[2]:+7.3f} {d[3]:+7.3f} {bm:+8.3f} {bp:6.2f} | "
        if (n, w, 'flat') in M:
            mx = M[(n, w, 'flat')][1]; dm = sharpe(x['r']) - sharpe(mx['r']); mm, mp = boot(x['r'], mx['r']); s += f"{dm:+16.3f} {mm:+8.3f} {mp:6.2f}"
        log(s)

# ------------------------------------------------------------------ reading rule 1
log('\n=== READING RULE 1: does any arm beat live on Sharpe on ALL THREE windows by more than 0.03, with a plateau? (dSharpe vs live: real / p01 / p10) ===')
DS = {n: [R[(n, w)]['m']['sh'] - R[(LIVE, w)]['m']['sh'] for w in WL] for n in ARMS}
for n in ARMS:
    if n != LIVE: log(f"  {n:<26}" + ' '.join(f'{x:+.3f}' for x in DS[n]) + ('   <-- clears 0.03 on all three' if all(x > 0.03 for x in DS[n]) else ''))
passing = [n for n in ARMS if n != LIVE and all(x > 0.03 for x in DS[n])]
plateau = []
for n in passing:
    for fam, order in FAMORDER.items():
        if n in order:
            i = order.index(n); nb = [order[j] for j in range(max(0, i - 2), min(len(order), i + 3)) if j != i and order[j] != LIVE]
            if sum(1 for q in nb if q in passing) >= 2: plateau.append(n)
log(f"  clear 0.03 everywhere: {passing or 'none'}; with a plateau (>=2 passing neighbours within +/-2 in the family): {plateau or 'none'}")

# ------------------------------------------------------------------ rule 2 summary
log('\n=== READING RULE 2: CAGR cost per 1 pp of max-DD / worst-20 avoided, arm vs matched flat de-lever (pp CAGR per pp). "beats" = arm cheaper ===')
for w in WL:
    log(f' window {w}')
    for n in ARMS:
        f = FR.get((n, w))
        if f: log(f"  {n:<24} DD: arm {f['c_dd']:6.2f} vs matched {f['mc_dd']:6.2f} beats={f['bt_dd']} | W20: arm {f['c_w']:6.2f} vs matched {f['mc_w']:6.2f} beats={f['bt_w']}")

# ------------------------------------------------------------------ sensitivities
log('\n=== SENSITIVITY (CAGR / Sharpe / maxDD / worst20 per arm): default highs (complete, L1) vs refs-style highs (file only, 50 late sessions read the close) vs L1 off ===')
for w in WL:
    log(f'\n window {w}')
    log(f"  {'arm':<26}{'default':>34}  {'refs-style highs':>34}  {'L1 off':>34}")
    for n, kw in ARMS.items():
        cells = []
        for extra in ({}, {'use_live_highs': False}, {'l1': False}):
            x = run_arm(n, dict(kw, **extra), w, full=False); m = x['m']; cells.append(f"{m['c']*100:5.1f}% {m['sh']:.3f} {m['dd']*100:6.1f}% {m['w20']*100:6.1f}%")
        log(f"  {n:<26}" + '  '.join(f'{c:>34}' for c in cells))
log('\n=== SENSITIVITY: proxy sleeve off (old harness behaviour) for the three live-ish arms: CAGR / Sharpe / maxDD ===')
for w in ('p01', 'p10'):
    for n in (LIVE, 'cap 1.75', 'A 50/50', 'A 20/80'):
        x = run_arm(n, dict(ARMS[n], sleeve_proxy=False), w, full=False); m = x['m']; log(f"  {w} {n:<14} {m['c']*100:5.1f}% {m['sh']:.3f} {m['dd']*100:6.1f}%")

# ------------------------------------------------------------------ crack-day anatomy (added after the first run: why the A split barely moves the crack-day loss)
log("\n=== CRACK-DAY ANATOMY, live arm: effective state, held extension votes (A trim: >0 means TQQQ out and core cut), gate, target gross held into the day, book return ===")
for w in ('real',):
    x = R[(LIVE, w)]; track, d0 = WINS[w]; b = built(track, ARMS[LIVE]); s0 = s0_of(track, d0)
    sgp, sgr = HL.signals(ARMS[LIVE].get('l1', True), ARMS[LIVE].get('use_live_highs', True)); held = (sgr if track == 'real' else sgp)['held'][0][s0:-1]
    eff = b['eff'][s0:-1]; gate = b['gate'][s0:-1]; cl = {'A0': [], 'Aext': [], 'D': [], 'other': []}
    for i, dt in enumerate(x['ds']):
        if dt in CRACK:
            lab = ('A' if eff[i] == 0 else 'eff%d' % eff[i]) + ('' if eff[i] != 0 else (' held=%d' % held[i])) + (' GATED' if gate[i] else '')
            log(f"  {dt}  {lab:<18} gross {x['g'][i]:.2f}  book {x['r'][i]*100:+6.2f}%")
            k = 'A0' if (eff[i] == 0 and held[i] == 0) else 'Aext' if eff[i] == 0 else 'D' if (eff[i] == 3 and not gate[i]) else 'other'; cl[k].append(x['r'][i] * 100)
    tot = sum(sum(v) for v in cl.values())
    for k, nm in (('A0', 'A with no extension trim (A split matters here)'), ('Aext', 'A with the extension trim on (TQQQ already out)'), ('D', 'ungated D (A split does not matter; cap does)'), ('other', 'other states / gated')):
        log(f"  {nm:<52} n {len(cl[k]):>2}  sum {sum(cl[k]):+7.2f}%  share of crack-day total {sum(cl[k])/tot*100:5.1f}%")
log(f'run time {time.time()-T0:.0f}s')

# ------------------------------------------------------------------ markdown tables for README
def f1(x): return '' if x is None or (isinstance(x, float) and np.isnan(x)) else f'{x:.2f}'
md = []
md.append('### Leverage table: CAGR % / Sharpe / maxDD % / worst-20-session % / avg gross, per window; matched = plain flat de-lever to the arm\'s avg gross\n')
md.append('| arm | real | proxy 2001 | proxy 2010 |\n|---|---|---|---|')
def cell(x): m = x['m']; return f"{m['c']*100:.1f} / {m['sh']:.3f} / {m['dd']*100:.1f} / {m['w20']*100:.1f} / {x['avgg']:.2f}"
for n in ARMS:
    md.append(f'| {n} | ' + ' | '.join(cell(R[(n, w)]) for w in WL) + ' |')
    if any((n, w, 'flat') in M for w in WL):
        md.append('| &nbsp;&nbsp;matched flat de-lever | ' + ' | '.join(cell(M[(n, w, 'flat')][1]) if (n, w, 'flat') in M else '' for w in WL) + ' |')
md.append('\n### Cost per point (CAGR pp given up per 1 pp avoided): arm vs matched flat de-lever; DD = max drawdown, W20 = worst 20 sessions; * = arm cheaper than matched; n/a = nothing avoided\n')
md.append('| arm | real DD | real W20 | proxy01 DD | proxy01 W20 | proxy10 DD | proxy10 W20 |\n|---|---|---|---|---|---|---|')
for n in ARMS:
    if not any((n, w) in FR for w in WL): continue
    cs = []
    for w in WL:
        f = FR.get((n, w))
        if not f: cs += ['', '']; continue
        for a, b, bt in ((f['c_dd'], f['mc_dd'], f['bt_dd']), (f['c_w'], f['mc_w'], f['bt_w'])):
            cs.append(('n/a' if np.isnan(a) else f"{a:.2f}{'*' if bt else ''}") + f' vs {b:.2f}')
    md.append(f'| {n} | ' + ' | '.join(cs) + ' |')
md.append('\n### Calm-crack days (prior VIX < 20, QQQ <= -3%): mean book return %, total % (sum), share of the arm\'s summed return on all QQQ <= -2% days / on leveraged-state -2% days\n')
md.append('| arm | real (20 days) | proxy 2001 (33) | proxy 2010 (22) |\n|---|---|---|---|')
for n in list(ARMS) + [f'matched flat({n})' for n in ARMS if (n, 'real', 'flat') in M]:
    cs = []
    for w in WL:
        k = (n, w)
        if k not in CK: cs.append(''); continue
        mn, tot, allt, sh, shl = CK[k]; cs.append(f'{mn:+.2f} / {tot:+.1f} / {sh:.1f}% / {shl:.1f}%')
    md.append(f'| {n} | ' + ' | '.join(cs) + ' |')
md.append('\n### Stress, % return (real panel; proxy 2001 for 2022 and Feb-Mar 2020 in brackets)\n')
md.append('| arm | 2022 | Feb-Mar 2020 | 2026-11-05 | 2026-10-30..11-05 |\n|---|---|---|---|---|')
for n in list(ARMS) + [f'matched flat({n})' for n in ARMS if (n, 'real', 'flat') in M]:
    x = R[(n, 'real')] if n in ARMS else M[(n[13:-1], 'real', 'flat')][1]
    y = R[(n, 'p01')] if n in ARMS else (M[(n[13:-1], 'p01', 'flat')][1] if (n[13:-1], 'p01', 'flat') in M else None)
    br = lambda a, b: f"{per(x,a,b):+.1f}" + (f" [{per(y,a,b):+.1f}]" if y is not None else '')
    md.append(f"| {n} | {br('2022-01-01','2022-12-31')} | {br('2020-02-01','2020-03-31')} | {per(x,'2026-11-05','2026-11-05'):+.2f} | {per(x,'2026-10-30','2026-11-05'):+.2f} |")
md.append('\n### Robustness, lower-leverage arms: dSharpe vs live (full / half1 / half2 / ex-2020), bootstrap median and P(dSh<=0); and full dSharpe vs matched de-lever with P\n')
md.append('| arm | window | vs live | bootstrap | vs matched (dSh, P) |\n|---|---|---|---|---|')
for n in ARMS:
    for w in WL:
        if (n, w) in RB:
            d, bm, bp = RB[(n, w)]; x = R[(n, w)]
            mt = ''
            if (n, w, 'flat') in M:
                mx = M[(n, w, 'flat')][1]; mm, mp = boot(x['r'], mx['r']); mt = f"{sharpe(x['r'])-sharpe(mx['r']):+.3f}, P {mp:.2f}"
            md.append(f"| {n} | {w} | {d[0]:+.3f} / {d[1]:+.3f} / {d[2]:+.3f} / {d[3]:+.3f} | {bm:+.3f}, P {bp:.2f} | {mt} |")
md.append('\n### Trades per year / one-way annual turnover (sum |target - held| at rebalances; 1.0 = whole book once)\n')
md.append('| arm | real | proxy 2001 | proxy 2010 |\n|---|---|---|---|')
for n in ARMS: md.append(f'| {n} | ' + ' | '.join(f"{R[(n,w)]['tpy']:.1f} / {R[(n,w)]['turn']:.1f}" for w in WL) + ' |')
open(os.path.join(HERE, 'tables_refs.md' if REFS else 'tables.md'), 'w').write('\n'.join(md) + '\n')
