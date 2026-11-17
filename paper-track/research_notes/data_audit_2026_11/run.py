"""Data audit 2026-11-17: silent-substitution / look-ahead audit of the backtest chain. Research only; edits nothing in the repo.

    python3 paper-track/research_notes/data_audit_2026_11/run.py        (writes run.log beside it; ~3 min)

Sections: 1 data/loader facts and quantified effects, 2 ON-vs-OFF of every live rule adopted 2026-09-01 or later on complete data,
3 look-ahead / timing. Engine: paper-track/review_2026_11/harness.py + a copy of harness_live.py (hl_orig_copy.py, only the
DGATE_HIGH_ENABLED assert removed because L1 is now off) + hl2.py (extra hooks). Live baseline = everything on, L1 OFF.
"""
import csv, glob, json, os, sys, time, datetime
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import hl2, hl_orig_copy as HL
from hl2 import run2, stat, fm
H, MC, S = hl2.H, hl2.MC, hl2.S
ROOT = '/home/user/Robinhood-stock'; DATA = ROOT + '/data'
LOG = open(os.path.join(HERE, 'run.log'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); LOG.write(s + '\n'); LOG.flush()
T0 = time.time()
X0, X1 = '2026-10-26', '2026-11-16'          # the stretch that reversed L1

# ======================================================================================================== 1. DATA
log('=' * 120); log('1. DATA AND LOADERS'); log('=' * 120)
log('\n1a. file coverage (first, last, rows) -- last session of the panel = %s' % H.PD[-1])
files = ['qqq_ohlc.csv', 'qqq_long_history.csv', 'spmo_ohlc.csv', 'tqqq_ohlc.csv', 'qld_ohlc.csv', 'xlu_ohlc.csv', 'vxncls.csv', 'vxvcls.csv',
         'vixcls_full.csv', 'dgs3mo.csv', 'dgs3mo_full.csv', 'QQEW_daily.csv', 'QQEW_daily_ext.csv', 'spy_long_history.csv', 'xlu_long_history.csv',
         'vixm_daily.csv', 'live_closes.csv', 'qqq_highs.csv', 'boxx_yahoo_tr.csv', 'bil_yahoo_tr.csv', 'ndx_survivor_ew_daily.csv', 'spy_yahoo_daily.csv']
def span(path):
    rows = list(csv.reader(open(path)))
    hdr, body = rows[0], [r for r in rows[1:] if len(r) > 1 and r[1] not in ('', '.')]
    return body[0][0], body[-1][0], len(body)
for f in files:
    a, b, n = span(os.path.join(DATA, f)); log('  %-28s %s .. %s  rows %d' % (f, a, b, n))
for f in ('research_notes/vixy_calm_2026_11/vixy_yahoo_full.csv', 'research_notes/leverage_a_2026_11/qqq_highs_av_2026_09_11.csv',
          'research_notes/vol_predict_2026_11/VIXCLS.csv', 'research_notes/vol_predict_2026_11/VXVCLS.csv', 'research_notes/vol_predict_2026_11/VXNCLS.csv'):
    a, b, n = span(os.path.join(ROOT, 'paper-track', f)); log('  %-28s %s .. %s  rows %d' % (f.split('/')[-1], a, b, n))

log('\n1b. what the harness panel does after each file ends (genuine = file row or live_closes row for that session; panel sessions after 2026-08-20 = 62)')
lc = {}
for r in H.LC:
    for k, v in r.items():
        if k != 'date' and v not in ('', None): lc.setdefault(k, set()).add(r['date'])
colmap = {'qqq_long_history.csv': 'QQQ', 'QQEW_daily_ext.csv': 'QQEW', 'spmo_ohlc.csv': 'SPMO', 'tqqq_ohlc.csv': 'TQQQ', 'qld_ohlc.csv': 'QLD',
          'xlu_ohlc.csv': 'XLU', 'vixm_daily.csv': 'VIXM'}
tail = [d for d in H.PD if d >= '2026-08-20']
for nm in ['qqq_long_history.csv', 'QQEW_daily_ext.csv', 'spmo_ohlc.csv', 'tqqq_ohlc.csv', 'qld_ohlc.csv', 'xlu_ohlc.csv', 'vixm_daily.csv',
           'xlu_long_history.csv', 'spy_long_history.csv']:
    rw = H._orig(nm); gen = set(rw) | lc.get(colmap.get(nm), set())
    miss = [d for d in tail if d not in gen]
    log('  %-24s file ends %s; live_closes col %s; panel sessions w/o a genuine print: %d %s' % (
        nm, max(rw), colmap.get(nm, '(none: not extended by harness._load)' if nm != 'spy_long_history.csv' else '(none: carried FLAT by harness)'),
        len(miss), (miss[0] + '..' + miss[-1]) if miss else ''))
tb = MC._load('dgs3mo_full.csv', 'observation_date', 'DGS3MO')
log('  dgs3mo_full.csv ends %s -> %d panel sessions after it earn the forward-filled last print (%.2f%%)' % (
    max(tb), sum(1 for d in H.PD if d > max(tb)), tb[max(tb)]))
log('  VIX (vol_curve.history, source CBOE here) ends %s, VIX3M ends %s; sessions after 2026-08-27 missing either: %d' % (
    max(H.VIX), max(H.VIX3M), sum(1 for d in tail if d not in H.VIX or d not in H.VIX3M)))
import datetime as dt
bd = [d for d in (dt.date(2026, 9, 5) + dt.timedelta(k) for k in range(0, 80)) if d.weekday() < 5 and d.isoformat() <= '2026-11-16' and d.isoformat() != '2026-09-07']
log('  NYSE sessions 2026-09-08..2026-11-16 expected %d (no 2026-09-07), panel has %d' % (len(bd), sum(1 for d in H.PD if d > '2026-09-04')))
g = [(a, b) for a, b in zip(H.PD[:-1], H.PD[1:]) if (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days > 4 and a > '2015-01-01']
log('  calendar gaps > 4 days since 2015 in the panel calendar: %s' % g)

log('\n1c. basis check: live_closes vs the file series on overlapping dates (live_closes is only used AFTER the file ends)')
for nm, col in colmap.items():
    rw = H._orig(nm); ov = [(d, float(r[col])) for r in H.LC for d in [r['date']] if r.get(col) and d in rw]
    if ov:
        rr = np.array([v / rw[d] - 1 for d, v in ov]); log('  %-24s overlap %d sessions %s..%s: |diff| mean %.3f%% max %.2f%%' % (nm, len(ov), ov[0][0], ov[-1][0], 100 * abs(rr).mean(), 100 * abs(rr).max()))
q = {r['date']: float(r['QQQ']) for r in H.LC}
log('  QQQ live_closes vs qqq_long_history on 2026-09-04: %.2f vs %.2f; first live-only session 2026-09-08 = %.2f' % (q['2026-09-04'], H._orig('qqq_long_history.csv')['2026-09-04'], q['2026-09-08']))

log('\n1d. QQQ highs: sessions after 2026-09-04 whose high is the fallback CLOSE (harness_live.highs())')
for u in (False, True):
    _, n = HL.highs(u); log('  use_live_highs=%s -> %d of 50 sessions fall back to the close' % (u, n))
rec = run2('real', l1=True, use_live_highs=False); com = run2('real', l1=True); off = run2('real')
log('  real L1 with recorded highs (close fallback): %s | complete highs: %s | L1 off: %s' % (fm(stat(rec['r'])), fm(stat(com['r'])), fm(stat(off['r']))))

log('\n1e. stale T-bill: repo dgs3mo_full.csv is frozen at 3.91% from 2026-08-31; fresh FRED DGS3MO (fetched 2026-11-17) is in fetched/')
fr = {}
for r in csv.DictReader(open(os.path.join(HERE, 'fetched', 'DGS3MO.csv'))):
    try: fr[r['observation_date']] = float(r['DGS3MO'])
    except ValueError: pass
ov = [d for d in tb if d in fr]; dd = np.array([tb[d] - fr[d] for d in ov])
log('  fetched DGS3MO %s..%s; overlap with repo file %d dates, max |diff| %.3f (history identical)' % (min(fr), max(fr), len(ov), abs(dd).max()))
log('  FRED 3m: 2026-08-31 %.2f, 2026-09-30 %.2f, 2026-10-30 %.2f, 2026-11-13 %.2f; repo-frozen %.2f' % (fr['2026-08-31'], fr.get('2026-09-30', np.nan), fr.get('2026-10-30', np.nan), fr['2026-11-13'], tb['2026-08-31']))
def fresh_cash(pn):
    ds = pn['dates']; tbd = sorted(fr); j = 0; last = 0.0; rate = []
    for d in ds:
        while j < len(tbd) and tbd[j] <= d: last = fr[tbd[j]]; j += 1
        rate.append(last / 100.0)
    rate = np.array(rate); yf = np.array([0.0] + [MC._yf(ds[i - 1], ds[i]) for i in range(1, len(ds))]); rprev = np.concatenate([[rate[0]], rate[:-1]])
    c = rprev * yf; c[0] = 0.0; return c
saved = {k: H.pr['cash'].copy() if k == 'real' else H.p['cash'].copy() for k in ('real', 'proxy')}
base = {t: stat(run2(t)['r']) for t in ('real', 'proxy')}
cash_fix = {}
for t, pn in (('real', H.pr), ('proxy', H.p)):
    old = pn['cash'].copy(); nc = fresh_cash(pn)
    ix = [i for i, d in enumerate(pn['dates']) if d > '2026-08-31']
    log('  %s panel: cash earned 2026-09-01..2026-11-16 repo %.3f%% vs fresh %.3f%% (compound over %d sessions)' % (t, 100 * (np.prod(1 + old[ix]) - 1), 100 * (np.prod(1 + nc[ix]) - 1), len(ix)))
    pn['cash'][:] = nc
    cash_fix[t] = stat(run2(t)['r']); pn['cash'][:] = old
    log('  %s live design: repo cash %s | fresh T-bill %s' % (t, fm(base[t]), fm(cash_fix[t])))
bx = list(csv.DictReader(open(DATA + '/boxx_yahoo_tr.csv')))
log('  BOXX (live_closes) 2026-09-04..11-16: %.3f%% ; T-bill panel same window %.3f%% (BOXX is not in the backtest; cash = T-bill)' % (
    100 * (float(H.LC[-1]['BOXX']) / float([r for r in H.LC if r['date'] == '2026-09-04'][0]['BOXX']) - 1), 100 * (np.prod(1 + H.pr['cash'][[i for i, d in enumerate(H.RD) if d > '2026-09-04']]) - 1)))

log('\n1f. unused / dead-end series that silently flat-line (proxy XLU, SPY, VIXM last day): are they ever held in the live design?')
for t in ('real', 'proxy'):
    d = run2(t); iv = d['names'].index('xlu'); log('  %s: max XLU weight in the live design %.4f (so XLU/SPY flat-lines cannot reach returns)' % (t, d['W'][:, iv].max()))
x = run2('real', sleeve='vixm'); iv = x['names'].index('vixy')
log('  real VIXM-75%% arm: VIXM return on 2026-11-16 is forward-filled 0 (VIXM ends 2026-11-13); weight held that day %.3f' % x['W'][-1, iv])

log('\n1g. what if VIX/VIX3M came from the stale local FRED files (rebaseline_2026_10_22.py falls back to them silently on any CBOE error)?')
def rd(f, c): return {r['observation_date']: float(r[c]) for r in csv.DictReader(open(DATA + '/' + f)) if r[c] not in ('', '.')}
vloc, v3loc = rd('vixcls_full.csv', 'VIXCLS'), rd('vxvcls.csv', 'VXVCLS')
for t in ('real', 'proxy'):
    a = run2(t); b = run2(t, vix=vloc, vix3m=v3loc)
    ia = a['names'].index('vixy'); log('  %s: complete VIX %s | stale-local VIX (ends %s / %s) %s ; sleeve weight>0 on %d vs %d sessions after 2026-09-08' % (
        t, fm(stat(a['r'])), max(vloc), max(v3loc), fm(stat(b['r'])), sum(1 for d, w in zip(a['ds'], a['W'][:, ia]) if d > '2026-09-08' and w > 0), sum(1 for d, w in zip(b['ds'], b['W'][:, b['names'].index('vixy')]) if d > '2026-09-08' and w > 0)))
log('\n1h. proxy_vix3m substitution (vol_curve.PROXY_K x SMA63(VIX)) for the whole VIX3M history: effect on the sleeve (research cannot do this silently: history() raises)')
vk = sorted(H.VIX); pv3 = {}
for i in range(62, len(vk)): pv3[vk[i]] = 1.32 * sum(H.VIX[d] for d in vk[i - 62:i + 1]) / 63
for t in ('real', 'proxy'):
    a = run2(t); b = run2(t, vix3m=pv3); log('  %s: real VIX3M %s | proxy VIX3M %s' % (t, fm(stat(a['r'])), fm(stat(b['r']))))

log('\n1i. counterfactuals: what each series would do if its file simply ended and the backtest kept running (flat-line = the _rets() forward-fill) -- NOT what the harness does, but what an unpatched loader would')
live_ref = {t: stat(run2(t)['r']) for t in ('real', 'proxy')}
def cf(label, fn):
    row = []
    for t in ('real', 'proxy'):
        out = fn(t); row.append('%s (d Sh %+.3f, d maxDD %+.1fpp)' % (fm(out), out['sh'] - live_ref[t]['sh'], 100 * (out['m'] - live_ref[t]['m'])))
    log('  %-58s real %s\n  %-58s proxy %s' % (label, row[0], '', row[1]))
cf('QQEW frozen after 2026-09-10 (breadth leg flat, QQQ runs)', lambda t: stat(run2(t, ew_freeze='2026-09-10')['r']))
def core_flat(t):
    pn = H.pr if t == 'real' else H.p
    if t != 'real': return stat(run2(t)['r'])
    ds = np.array(pn['dates']); m = ds > '2026-09-04'; sv = {k: pn[k].copy() for k in ('core', 'tqqq', 'qld')}
    for k in sv: pn[k][m] = 0.0
    try: return stat(run2(t)['r'])
    finally:
        for k in sv: pn[k][:] = sv[k]
cf('SPMO/TQQQ/QLD frozen after 2026-09-04 (real legs earn 0; proxy unaffected)', core_flat)
def cash0(t):
    pn = H.pr if t == 'real' else H.p; ds = np.array(pn['dates']); m = ds > '2026-08-31'; sv = pn['cash'].copy(); pn['cash'][m] = 0.0
    try: return stat(run2(t)['r'])
    finally: pn['cash'][:] = sv
cf('T-bill earning 0 after 2026-08-31 (instead of 3.91% frozen)', cash0)
log('  elapsed %.0fs' % (time.time() - T0))

# ======================================================================================================== 2. RULES
log('\n' + '=' * 120); log('2. LIVE RULES ADOPTED 2026-09-01 OR LATER: ON vs OFF on complete data (live design, all else as live, L1 off)'); log('=' * 120)
log('Cells: CAGR / Sharpe (mean/sd, no rf, as the project) / max DD.  real = 2015-11-03..2026-11-16, proxy = 2001-01-03..2026-11-16.  "excl" = daily returns of %s..%s dropped from both arms (paths run in full, days then removed).' % (X0, X1))
log('d = ON minus OFF (Sharpe; max DD in pp, positive = ON shallower).  stretch = compounded return of the arm over %s..%s.  boot = P(ON Sharpe > OFF Sharpe) over 400 paired stationary-bootstrap resamples (block 20) [5%%,95%%] of dSharpe.' % (X0, X1))
RULES = [
 ('R01', '09-01', 'volatility target 20% (outermost overlay)', {}, {'vol_target': 1e9}),
 ('R02', '09-06', '20/100 fast re-entry overlay', {}, {'cfg_over': {'fast': False}}),
 ('R03', '09-06/09-23', 'extension trim v2 vs graded v1 (same A base)', {}, {'cfg_over': {'trim': 'v1'}}),
 ('R03b', '09-06/09-23', 'extension trim v2 vs NO trim', {}, {'cfg_over': {'trim': 'none'}}),
 ('R04', '09-23', 'whipsaw carry of held votes (3 sessions) vs none', {}, {'carry': 0}),
 ('R05', '09-09', 'drift band 5% vs 3%', {}, {'band': 0.03}),
 ('R06', '09-19', 'D gate (breadth<0.20 OR gap200<2%)', {}, {'cfg_over': {'d_gate': False}}),
 ('R07', '09-19', 'state E 100% cash vs 50% XLU/50% cash', {}, {'rows_over': {'E': (0, 0, 0, 0.5, 0.5)}}),
 ('R08', '10-08', 'VIXM sleeve 75% of cash leg (VIXM, D2-off on) vs no sleeve', {'sleeve': 'vixm'}, {'sleeve': 'none'}),
 ('R09', '10-09', 'D ladder vs plain D = 100% QLD', {}, {'cfg_over': {'d_ladder': False}}),
 ('R10', '10-22', 'vol estimator max(10d,30d) vs plain 30d', {}, {'cfg_over': {'vol': '30'}}),
 ('R11', '10-22', 'D3 100% TQQQ vs D3 40/60 SPMO/TQQQ', {}, {'d3_row': (0.40, 0.60, 0.0)}),
 ('R12', '10-22', 'A base 40/60 vs 25/75', {}, {'a_split': (0.25, 0.75)}),
 ('R13', '10-22', 'sleeve OFF in ungated D2 (VIXY live)', {}, {'d2_off': False}),
 ('R14', '10-29', 'D zone buffer +/-0.5% vs none', {}, {'cfg_over': {'d_buffer': 0.0}}),
 ('R15', '10-30', 'A base 20/80 (adopted 10-30, reversed 11-06) vs 40/60', {'a_split': (0.2, 0.8)}, {}),
 ('R16', '11-06', 'A base 40/60 vs 20/80', {}, {'a_split': (0.2, 0.8)}),
 ('R17', '11-11', 'sleeve VIXY 35% vs VIXM 75%', {}, {'sleeve': 'vixm'}),
 ('R17b', '10-08/11-11', 'sleeve VIXY 35% vs no sleeve', {}, {'sleeve': 'none'}),
 ('R18', '11-11', 'deep-E QQQ leg (50% of cash leg)', {}, {'deep_share': 0.0}),
 ('R19', '11-11', 'VIX-panic QQQ leg (25% of cash leg)', {}, {'panic_share': 0.0}),
 ('R20', '11-11', 'B row 50% SPMO/50% cash vs 75/25 SPMO/TQQQ', {}, {'rows_over': {'B': (0.75, 0.25, 0, 0, 0)}}),
 ('R21', '11-11', 'gross cap 2.0x vs no cap', {}, {'gross_cap': None}),
 ('R22', '11-11', 'L1 (day-high D gate), COMPLETE highs, vs off', {'l1': True}, {}),
 ('R22r', '11-11', 'L1 as RECORDED (50 sessions read the close) vs off', {'l1': True, 'use_live_highs': False}, {}),
]
RES = {}
mask_cache = {}
def split(res):
    ds = np.array(res['ds']); r = res['r']; m = (ds >= X0) & (ds <= X1)
    return r, m
rng = np.random.default_rng(20261117)
def boot(a, b, P=400, L=20):
    n = len(a); idx = MC.bootstrap_idx(rng, n, P, n, L)
    def sh(x): return x.mean(1) / x.std(1, ddof=1) * 252 ** 0.5
    d = sh(a[idx]) - sh(b[idx]); return (d > 0).mean(), np.percentile(d, 5), np.percentile(d, 95)
for rid, dt_, label, on, off in RULES:
    log('\n%s  %s  %s' % (rid, dt_, label))
    out = {}
    for t in ('real', 'proxy'):
        A, B = run2(t, **on), run2(t, **off)
        ra, m = split(A); rb, _ = split(B)
        sa, sb = stat(ra), stat(rb); ea, eb = stat(ra[~m]), stat(rb[~m]); st_a, st_b = np.prod(1 + ra[m]) - 1, np.prod(1 + rb[m]) - 1
        pb, lo, hi = boot(ra, rb)
        out[t] = dict(on=sa, off=sb, ex_on=ea, ex_off=eb, st_on=st_a, st_off=st_b, p=pb, lo=lo, hi=hi, tpy_on=A['tpy'], tpy_off=B['tpy'])
        log('  %-5s ON  %s | excl %s | stretch %+6.2f%% | %.0f tr/yr' % (t, fm(sa), fm(ea), 100 * st_a, A['tpy']))
        log('  %-5s OFF %s | excl %s | stretch %+6.2f%% | %.0f tr/yr' % (t, fm(sb), fm(eb), 100 * st_b, B['tpy']))
        log('  %-5s d: Sharpe %+.3f  CAGR %+5.1fpp  maxDD %+5.1fpp | excl d: Sharpe %+.3f  CAGR %+5.1fpp  maxDD %+5.1fpp | stretch %+5.2fpp | boot P %.2f [%+.3f,%+.3f]' % (
            t, sa['sh'] - sb['sh'], 100 * (sa['c'] - sb['c']), 100 * (sa['m'] - sb['m']), ea['sh'] - eb['sh'], 100 * (ea['c'] - eb['c']), 100 * (ea['m'] - eb['m']), 100 * (st_a - st_b), pb, lo, hi))
    RES[rid] = out
json.dump({k: {t: {kk: (vv if not isinstance(vv, dict) else {a: float(b) for a, b in vv.items()}) for kk, vv in v.items()} for t, v in r.items()} for k, r in RES.items()},
          open(os.path.join(HERE, 'rules.json'), 'w'), default=float, indent=1)
log('  elapsed %.0fs' % (time.time() - T0))

log('\nR16 detail: 2026 YTD and calendar years, 40/60 vs 20/80 (live design, complete data)')
for t in ('real',):
    for lab, kw in (('40/60', {}), ('20/80', {'a_split': (0.2, 0.8)})):
        A = run2(t, **kw); ds = np.array(A['ds']); r = A['r']; out = []
        for y in ('2022', '2023', '2024', '2025', '2026'):
            m = np.array([d[:4] == y for d in ds]); out.append('%s %+.1f%%' % (y, 100 * (np.prod(1 + r[m]) - 1)))
        m5 = (ds >= '2026-01-01') & (ds <= '2026-11-05'); mm = A['r'][m5]; nav = np.cumprod(1 + mm); dd = (nav / np.maximum.accumulate(nav) - 1).min()
        log('  %s: %s | 2026 to 11-05 %+.1f%% (max DD within %.1f%%)' % (lab, ' '.join(out), 100 * (nav[-1] - 1), 100 * dd))

# ======================================================================================================== 3. LOOK-AHEAD
log('\n' + '=' * 120); log('3. LOOK-AHEAD AND TIMING'); log('=' * 120)
log('\n3a. harness_live `lag` = delays EVERY target weight and regime key by `lag` sessions (np.concatenate on W and key): an execution delay of the whole book, not a lag of one input.')
for t in ('real', 'proxy'):
    a = stat(HL.run_live(t, l1=False)[0]); b = stat(HL.run_live(t, l1=False, lag=1)[0]); log('  %s: live %s | lag=1 (all inputs, execute one session late) %s' % (t, fm(a), fm(b)))

log('\n3b. 15:50 live reading vs the backtest\'s close, measured on the 27 live runs 2026-10-09..2026-11-16 (data/runs/*.json vs closes)')
vd = []; qd = []; ed = []
lcq = {r['date']: r for r in H.LC}
for f in sorted(glob.glob(DATA + '/runs/2026-*.json')):
    if 'open' in f: continue
    j = json.load(open(f)); d = j['date']; i = j['input']
    if 'vix' in i and d in H.VIX: vd.append(i['vix'] - H.VIX[d])
    if d in lcq and lcq[d].get('QQQ'):
        qd.append(i['quotes']['QQQ']['last'] / float(lcq[d]['QQQ']) - 1)
        if lcq[d].get('QQEW'): ed.append(i['quotes']['QQEW']['last'] / float(lcq[d]['QQEW']) - 1)
vd, qd, ed = map(np.array, (vd, qd, ed))
log('  VIX (15:50 reading, Robinhood until 11-05 then median) minus CBOE close: n=%d mean %+.2f sd %.2f max|.| %.2f pts' % (len(vd), vd.mean(), vd.std(ddof=1), abs(vd).max()))
log('  QQQ 15:50 last / close - 1: n=%d mean %+.3f%% sd %.3f%% max|.| %.2f%% ; QQEW: sd %.3f%%' % (len(qd), 100 * qd.mean(), 100 * qd.std(ddof=1), 100 * abs(qd).max(), 100 * ed.std(ddof=1)))
fq = list(csv.DictReader(open(DATA + '/fill_quality.csv'))); sl = np.array([float(r['slippage_bps']) for r in fq if r['ref_kind'] == 'signal_session_close' and r['symbol'] in ('TQQQ', 'QLD', 'SPMO')])
log('  fill_quality.csv: %d fills of SPMO/TQQQ/QLD vs signal-session close: mean slippage %+.1f bps, sd %.1f bps' % (len(sl), sl.mean(), sl.std(ddof=1)))

log('\n3c. one-day lag of ONE input at a time (live design; real | proxy; Sharpe/CAGR/maxDD)')
def shift_map(m, k=1):
    ks = sorted(m); return {ks[i]: m[ks[i - k]] for i in range(k, len(ks))}
vixL, v3L = shift_map(H.VIX), shift_map(H.VIX3M)
variants = [('live (no lag)', {}), ('VIX + VIX3M lagged 1 session (sleeve latch + panic latch)', {'vix': vixL, 'vix3m': v3L}),
            ('VIX only lagged (VIX3M current)', {'vix': vixL}),
            ('QQEW lagged 1 session in the breadth signal', {'ew_lag': 1}),
            ('ALL inputs lagged (harness lag=1)', 'LAG')]
LA = {}
for lab, kw in variants:
    row = []
    for t in ('real', 'proxy'):
        r = HL.run_live(t, l1=False, lag=1)[0] if kw == 'LAG' else run2(t, **kw)['r']
        LA[(lab, t)] = stat(r); row.append(fm(stat(r)))
    log('  %-62s real %s | proxy %s' % (lab, row[0], row[1]))
log('  deltas vs live (Sharpe, CAGR pp, maxDD pp):')
for lab, _ in variants[1:]:
    for t in ('real', 'proxy'):
        a, b = LA[(lab, t)], LA[('live (no lag)', t)]; log('    %-62s %-5s %+.3f %+5.1f %+5.1f' % (lab, t, a['sh'] - b['sh'], 100 * (a['c'] - b['c']), 100 * (a['m'] - b['m'])))

log('\n3d. QQQ-derived signals lagged 1 session while VIX/QQEW stay current (state, gaps, vol, gate, trim): isolates the "4pm close vs 15:50" input')
orig_sig = hl2.signals2
def lagsig(k):
    def f(l1, use_live, carry, ew_lag, ew_freeze=None, qnoise=None):
        sgp, sgr = orig_sig(l1, use_live, carry, ew_lag, ew_freeze, qnoise)
        def sh(sg):
            out = {}
            for key, v in sg.items():
                if isinstance(key, tuple): continue
                if isinstance(v, dict): out[key] = {n: np.concatenate([np.repeat(a[:, :1], k, 1), a[:, :-k]], 1) for n, a in v.items()}
                else: out[key] = np.concatenate([np.repeat(v[:, :1], k, 1), v[:, :-k]], 1)
            return out
        return sh(sgp), sh(sgr)
    return f
hl2.signals2 = lagsig(1)
try:
    rows = {t: stat(run2(t)['r']) for t in ('real', 'proxy')}
finally:
    hl2.signals2 = orig_sig
for t in ('real', 'proxy'):
    a, b = rows[t], LA[('live (no lag)', t)]
    log('  %-5s QQQ-signals lag 1: %s | d vs live: Sharpe %+.3f CAGR %+.1fpp maxDD %+.1fpp' % (t, fm(a), a['sh'] - b['sh'], 100 * (a['c'] - b['c']), 100 * (a['m'] - b['m'])))

log('\n3e. VIX reading noise matched to the measured 15:50-vs-close spread (sd %.2f pts), applied to VIX and VIX3M independently, 150 draws' % vd.std(ddof=1))
sd = vd.std(ddof=1); rn = np.random.default_rng(7); res = {'real': [], 'proxy': []}
vk_all = sorted(H.VIX); v3k = sorted(H.VIX3M)
for k in range(150):
    vn = {d: H.VIX[d] + rn.normal(0, sd) for d in vk_all}; v3n = {d: H.VIX3M[d] + rn.normal(0, sd) for d in v3k}
    for t in ('real', 'proxy'):
        s_ = stat(run2(t, vix=vn, vix3m=v3n)['r']); res[t].append((s_['sh'], s_['c'], s_['m']))
for t in ('real', 'proxy'):
    a = np.array(res[t]); b = LA[('live (no lag)', t)]
    log('  %-5s noisy-VIX Sharpe mean %.3f (live %.3f) sd %.3f, min %.3f; CAGR mean %.1f%% (live %.1f%%); maxDD mean %.1f%% (live %.1f%%), worst %.1f%%' % (
        t, a[:, 0].mean(), b['sh'], a[:, 0].std(), a[:, 0].min(), 100 * a[:, 1].mean(), 100 * b['c'], 100 * a[:, 2].mean(), 100 * b['m'], 100 * a[:, 2].min()))

log('\n3f. realistic 15:50-vs-close noise on the QQQ and QQEW LEVELS the signals read (sd %.3f%% QQQ, %.3f%% QQEW measured in 3b), independent per day, 40 draws; returns stay true' % (100 * qd.std(ddof=1), 100 * ed.std(ddof=1)))
resq = {'real': [], 'proxy': []}
for k in range(40):
    for t in ('real', 'proxy'):
        s_ = stat(run2(t, qnoise=(1000 + k, qd.std(ddof=1), ed.std(ddof=1)))['r']); resq[t].append((s_['sh'], s_['c'], s_['m']))
for t in ('real', 'proxy'):
    a = np.array(resq[t]); b = LA[('live (no lag)', t)]
    log('  %-5s noisy-signal Sharpe mean %.3f (live %.3f) sd %.3f, min %.3f; CAGR mean %.1f%% (live %.1f%%); maxDD mean %.1f%% (live %.1f%%), worst %.1f%%' % (
        t, a[:, 0].mean(), b['sh'], a[:, 0].std(), a[:, 0].min(), 100 * a[:, 1].mean(), 100 * b['c'], 100 * a[:, 2].mean(), 100 * b['m'], 100 * a[:, 2].min()))

log('\n'+'='*120); log('4. CAN THE QUOTED STRATEGY.md REFERENCE NUMBERS BE REPRODUCED? (harness_live engine with each rule-era design, 4 bp cost where the study used 4 bp, window ends as the study)'); log('='*120)
def f(t,d1='2099',cost=None,**k):
    a=run2(t,d1=d1,cost=cost,**k); return fm(stat(a['r']))+'  (to %s)'%a['ds'][-1]
OLD=dict(gross_cap=None,deep_share=0,panic_share=0,rows_over={'B':(0.75,0.25,0,0,0)},cfg_over={'d_buffer':0},d2_off=False)
log('A ladder 10-09: cited live 47.7/1.912/-18.7 | 28.7/1.226/-23.5 ; pick 54.7/1.977/-19.4 | 32.7/1.275/-27.7 (labelled real 2015-11..2026-10)')
pick=dict(OLD,a_split=(0.25,0.75),d3_row=(0.25,0.75,0.0),sleeve='vixm')
pick['cfg_over']=dict(pick['cfg_over'],vol='30')
live=dict(pick,a_split=(0.4,0.6)); live['cfg_over']=dict(pick['cfg_over'],d_ladder=False)
for d1 in ('2026-08-27','2026-09-04','2026-10-08'):
    log(' d1',d1,'pick real',f('real',d1,0.0004,**pick)); log('     live real',f('real',d1,0.0004,**live))
pp=dict(pick,sleeve='none'); lp=dict(live,sleeve='none')
log(' proxy pick',f('proxy','2026-08-27',0.0004,**pp),'| live',f('proxy','2026-08-27',0.0004,**lp))
log('B rebaseline 10-22: cited real 47.9/2.006/-18.4 proxy 30.4/1.320/-24.6 (to 08-27)')
rb=dict(OLD,sleeve='vixm',d2_off=True)
log(' real',f('real','2026-08-27',0.0004,**rb),'\n proxy',f('proxy','2026-08-27',0.0004,**dict(rb,sleeve='none')))
log('C buffer 10-29: cited real 43.52/1.831/-18.4 -> 44.00/1.849 (to 10-29, 4bp, no VIXM?)')
for sl in ('none','vixm'):
    for buf in (0,0.005):
        k=dict(OLD,sleeve=sl,d2_off=False); k['cfg_over']={'d_buffer':buf}
        log(' sleeve',sl,'buf',buf,f('real','2026-10-29',0.0004,**k))
log('D 10-30 A 20/80: cited real 47.2/1.959/-18.4 -> 53.5/1.911/-20.3; proxy 30.7/1.321/-22.2 -> 33.9/1.301/-26.5')
for a in ((0.4,0.6),(0.2,0.8)):
    k=dict(OLD,sleeve='vixm',d2_off=True,a_split=a); k['cfg_over']={'d_buffer':0.005}
    log(' real',a,f('real','2026-10-29',0.0004,**k),'| proxy',f('proxy','2026-10-29',0.0004,**dict(k,sleeve='none')))
log('E L1 11-11: cited real 53.1/2.053/-18.3 -> 56.0/2.109/-18.3 ; proxy 34.4/1.411/-22.1 -> 37.1/1.485/-22.9 (to 11-10, no cap, VIXM, deep-E+panic)')
for b in ((0.75,0.25,0,0,0),(0.5,0,0,0,0.5)):
  for l1 in (False,True):
    k=dict(OLD,sleeve='vixm',d2_off=True,l1=l1,use_live_highs=False,panic_share=S.VIX_PANIC_CASH_SHARE,deep_share=S.DEEP_E_CASH_SHARE); k['rows_over']={'B':b}; k['cfg_over']={'d_buffer':0.005}
    log(' B',b[:2],'l1',l1,'real',f('real','2026-11-10',**k),'| proxy',f('proxy','2026-11-10',**dict(k,sleeve='none')))
log('F trim v2 09-23: cited real 37.30/1.475/-18.6 (v1 A50/50) -> 39.32/1.717/-17.8 ; proxy 25.46/1.071/-27.0 -> 25.41/1.161/-21.9')
base=dict(gross_cap=None,deep_share=0,panic_share=0,sleeve='none',d2_off=False,rows_over={'B':(0.75,0.25,0,0,0)},a_split=(0.5,0.5))
for tr,ca in (('v1',None),('v2',None)):
    k=dict(base); k['cfg_over']={'d_buffer':0,'vol':'30','trim':tr,'d_ladder':False}
    log(' ',tr,'real',f('real','2026-09-04',0.0004,**k),'| proxy',f('proxy','2026-08-27',0.0004,**k))

log('\ntotal elapsed %.0fs' % (time.time() - T0))
