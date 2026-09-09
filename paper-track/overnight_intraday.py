"""overnight_intraday -- overnight-gap vs intraday risk, and where the live
design's protection lands relative to the damaging move (2026-09-09).

Research line, CHANGE FREEZE: nothing here is applied. Companion writeup:
paper-track/research_notes/overnight_intraday.md.

Every session's QQQ return is split into r_on = open_t/close_{t-1} - 1 and
r_id = close_t/open_t - 1 (data/qqq_ohlc.csv). The live design decides and
trades at the 15:55 close-proxy, so NEW weights are always held through the
next overnight gap and OLD weights through the session on which the decision
is made. Sections:
  1. where the losses are (QQQ and the strategy's own P&L), by regime
  2. what each overlay protects: forward damage after it cut exposure, and
     exposure held INTO the worst gaps / worst intraday sessions
  3. reaction lag of each overlay on the worst 20 gaps / worst 20 sessions
  4. execution-convention counterfactuals through the harness (half-rows)
  5. two small overnight-aware variants, exposure-matched (5 candidates)

Harness: the project's `run` from improvement_search is reproduced by
`run_x` (same loop, plus a per-row `trade` flag, a cost parameter, a held-
weight trace, and the real-daily `needs_rebalance` policy). run_x with the
defaults is asserted equal to run() on every row before anything else runs.
"""
import sys, math, csv, time, random
sys.path.insert(0, 'paper-track')
T0 = time.time()
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from state import (extension_scale, extension_votes, realized_vol, needs_rebalance,
                   VOL_TARGET_PA, FAST_REENTRY_MAP)
from improvement_search import SEARCH, HOLDOUT, era, BAND
from drift_band_test import annual_stats, ONE_WAY_SPREAD
from improvement_search_r2 import BETA
from block_bootstrap import boot, stats as bstats, N_BOOT
import monthly_returns as MR
from backtest_overlay_etf import load_daily_csv, load_tbill, build_cash_index

OUT = []
def say(*a):
    s = ' '.join(str(x) for x in a); print(s); OUT.append(s)

def mean(x): return sum(x) / len(x) if x else float('nan')
def var(x):
    if len(x) < 2: return float('nan')
    m = mean(x); return sum((v - m) ** 2 for v in x) / (len(x) - 1)
def skew(x):
    m = mean(x); s = var(x) ** 0.5
    return mean([((v - m) / s) ** 3 for v in x]) if s > 0 else float('nan')
def kurt(x):
    m = mean(x); s = var(x) ** 0.5
    return mean([((v - m) / s) ** 4 for v in x]) - 3 if s > 0 else float('nan')
def pct(x): return f"{x*100:6.1f}%"

# ------------------------------------------------------------------ live design
def trim_of(w, eff, gaps):
    f = extension_scale(eff, gaps)
    return w if f >= 1 else tuple(a * f for a in w[:4]) + (1 - f * sum(w[:4]),)

def live_fn(r):
    w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
    if f < 1: w = tuple(a * f for a in w[:4]) + (1 - f * sum(w[:4]),)
    return vt(w, r.get('vol_live') or r['vol'])

# the overlays switched off one at a time (targets, no drift)
def fn_no_vt(r):   return trim_of(W[r['eff']], r['eff'], r['gaps'])
def fn_no_trim(r): return vt(W[r['eff']], r['vol_live'])
def fn_no_fast(r): return vt(trim_of(W[r['state']], r['state'], r['gaps']), r['vol_live'])
def fn_macro(r):   return W[r['state']]
def fn_vol30(r):   return vt(trim_of(W[r['eff']], r['eff'], r['gaps']), r['vol'])
def expo(w): return sum(w[:4])
def beta(w): return sum(w[i] * BETA[i] for i in range(5))

for r in rr:
    a = realized_vol(qd, qqq, as_of=r['d0'], lookback=10); b = realized_vol(qd, qqq, as_of=r['d0'], lookback=30)
    r['vol_live'] = b if (a is None or b is None) else max(a, b)
def live_real(r):
    return RF.vt(trim_of(W[r['eff']], r['eff'], r['gaps']), r['vol_live'])

# ------------------------------------------------------------------ run_x: the harness loop + a trade flag
def run_x(rows_, wfn, band=BAND, spread=ONE_WAY_SPREAD, policy='band', trace=False):
    """improvement_search.run, verbatim in its defaults, plus:
       r['trade'] False  -> no rebalance is allowed on this row (used for the
                            overnight half-rows of the execute-at-open test);
       spread            -> one-way cost;
       policy 'needs'    -> state.needs_rebalance (the real-daily harness rule);
       r['key']          -> regime key override (real-daily uses (eff, votes)).
    Returns (rets, avg_risky, held_trace, n_rebalances, turnover)."""
    held = prev = None; rets = []; risky = 0.0; hw = []; nreb = 0; turn = 0.0; costs = []; pending = None
    for r in rows_:
        can = r.get('trade', True)
        key = r.get('key') or (r['state'], r['agree'])
        cost = 0.0
        if pending is not None:            # a fill deferred from the previous row (decided there, executed here)
            drift = sum(abs(pending[j] - held[j]) for j in range(5))
            cost = spread * drift; held = list(pending); nreb += 1; turn += drift / 2; pending = None
        if held is None:
            held = list(wfn(r)); nreb += 1
        elif can:
            t = wfn(r)
            drift = sum(abs(t[j] - held[j]) for j in range(5))
            if policy == 'band': do = key != prev or drift > band
            else: do, drift, _ = needs_rebalance(t, held, key != prev)
            if do:
                if r.get('defer'): pending = t
                else: cost = spread * drift; held = list(t); nreb += 1; turn += drift / 2
        if trace: hw.append(tuple(held))
        risky += sum(held[:4])
        g = sum(held[j] * r['legs'][j] for j in range(5))
        rets.append(g - cost); costs.append(cost)
        dn = 1 + g
        if dn > 0: held = [held[j] * (1 + r['legs'][j]) / dn for j in range(5)]
        if can: prev = key
    return rets, risky / len(rows_), hw, nreb, turn, costs

def stats3(rets, per=252):
    c, s, m = annual_stats(rets)
    return c, s, m

# ------------------------------------------------------------------ 0. sanity
say("== 0. SANITY: live figures through the harness, and run_x == run")
ev = evaluate(rows, live_fn)
say(f"  proxy  {ev['cagr']*100:.2f}% / {ev['sharpe']:.3f} / {ev['mdd']*100:.1f}%  S {ev['s_sharpe']:.3f}  H {ev['h_sharpe']:.3f}  expo {ev['risky']*100:.2f}%  rows {len(rows)} {rows[0]['d']}..{rows[-1]['d']}")
e = RF.eval_real(rr, live_real)
say(f"  real weekly {e['cagr']*100:.2f}% / {e['sharpe']:.3f} / {e['mdd']*100:.1f}%  rows {len(rr)}")
R0, E0 = run(rows, live_fn)
RX, EX, HW, NREB, TURN, _ = run_x(rows, live_fn, trace=True)
assert max(abs(a - b) for a, b in zip(R0, RX)) == 0.0 and abs(E0 - EX) < 1e-15
say(f"  run_x reproduces run() exactly on all {len(rows)} rows; {NREB/len(rows)*252:.0f} reb/yr")
LIVE_EXPO = E0

# ------------------------------------------------------------------ data: QQQ OHLC and the split
O = {}; C = {}; H = {}; L = {}
for x in csv.DictReader(open('data/qqq_ohlc.csv')):
    O[x['d']] = float(x['o']); C[x['d']] = float(x['c']); H[x['d']] = float(x['h']); L[x['d']] = float(x['l'])
od = sorted(O); oix = {d: i for i, d in enumerate(od)}
skipped = 0
for r in rows:
    i = ix[r['d']]; d1 = ds[i + 1]; r['d1'] = d1
    if oix[d1] != oix[r['d']] + 1: skipped += 1
    r['on'] = O[d1] / C[r['d']] - 1
    r['id'] = C[d1] / O[d1] - 1
    assert abs((1 + r['on']) * (1 + r['id']) - 1 - r['qqq']) < 1e-9
    on3 = 3 * r['on']; on2 = 2 * r['on']
    r['on_legs'] = (r['on'], on3, on2, 0.0, 0.0)
    r['id_legs'] = tuple((1 + r['legs'][j]) / (1 + r['on_legs'][j]) - 1 for j in range(5))
say(f"  QQQ split attached to {len(rows)} rows; rows whose d0->d1 spans >1 OHLC session: {skipped}")
say("  proxy leg split: core/QLD/TQQQ overnight = 1x/2x/3x QQQ gap (daily-reset funds carry k-times the")
say("  underlying's exposure from the prior close, so open/prev-close ~ 1+k*gap); financing, ER and dividend")
say("  accrual land in the intraday residual. XLU (close-only history) and cash are UNSPLIT: whole return in")
say("  the intraday bucket. They are held only in state E (XLU) and as the cash leg.")

# ------------------------------------------------------------------ 1. where are the losses
REGIMES = [
    ('ALL 2000-07..2026-08', '2000-07-01', '2099'),
    ('dot-com 2000-07..2002-10', '2000-07-01', '2002-10-09'),
    ('GFC 2007-10..2009-03', '2007-10-09', '2009-03-09'),
    ('2011 Jul-Oct', '2011-07-01', '2011-10-31'),
    ('2015-16 Aug-Feb', '2015-08-01', '2016-02-29'),
    ('2018 Q4', '2018-10-01', '2018-12-31'),
    ('COVID 2020-02-19..03-23', '2020-02-19', '2020-03-23'),
    ('2022 bear', '2022-01-01', '2022-12-31'),
    ('calm 2013', '2013-01-01', '2013-12-31'),
    ('calm 2017', '2017-01-01', '2017-12-31'),
    ('calm 2019', '2019-01-01', '2019-12-31'),
    ('calm 2021', '2021-01-01', '2021-12-31'),
    ('calm 2024', '2024-01-01', '2024-12-31'),
    ('SEARCH 2015-11+', '2015-11-01', '2099'),
    ('HOLDOUT 2000-07..2015-10', '2000-07-01', '2015-10-31'),
]

def decomp(on, idd):
    """on/idd: simple returns per session. Returns a dict of shares."""
    n = len(on)
    cc = [(1 + a) * (1 + b) - 1 for a, b in zip(on, idd)]
    lo = [math.log1p(a) for a in on]; li = [math.log1p(b) for b in idd]; lc = [a + b for a, b in zip(lo, li)]
    vo, vi, vc = var(on), var(idd), var(cc)
    cov = (vc - vo - vi) / 2
    so = sum(min(a, 0) ** 2 for a in on); si = sum(min(b, 0) ** 2 for b in idd)
    order = sorted(range(n), key=lambda k: cc[k])
    out = dict(n=n, var_on=vo / vc, var_id=vi / vc, cov2=2 * cov / vc, semi_on=so / (so + si),
               cum_on=sum(lo), cum_id=sum(li), sk_on=skew(on), sk_id=skew(idd), ku_on=kurt(on), ku_id=kurt(idd),
               sd_on=vo ** 0.5 * 252 ** 0.5, sd_id=vi ** 0.5 * 252 ** 0.5)
    for p in (0.01, 0.05):
        k = max(1, int(math.ceil(n * p))); sel = order[:k]
        to = sum(lo[j] for j in sel); ti = sum(li[j] for j in sel)
        out[f'tail{int(p*100)}_on'] = to / (to + ti) if (to + ti) < 0 else float('nan')
        out[f'tail{int(p*100)}_k'] = k; out[f'tail{int(p*100)}_sum'] = to + ti
    return out

def table1(label, get_on, get_id):
    say(f"\n  {label}")
    say(f"  {'regime':<28}{'n':>5} {'var ON':>7}{'var ID':>7}{'2cov':>6} {'semi ON':>8} {'tail1 ON':>9}{'tail5 ON':>9} {'cum ON':>8}{'cum ID':>8} {'skew ON':>8}{'skew ID':>8}{'kurt ON':>8}{'kurt ID':>8} {'ann sd ON':>10}{'ann sd ID':>10}")
    res = {}
    for lab, a, b in REGIMES:
        sel = [r for r in rows if a <= r['d'] <= b]
        if len(sel) < 10: continue
        d = decomp([get_on(r) for r in sel], [get_id(r) for r in sel]); res[lab] = d
        say(f"  {lab:<28}{d['n']:>5} {d['var_on']*100:6.1f}%{d['var_id']*100:6.1f}%{d['cov2']*100:5.1f}% {d['semi_on']*100:7.1f}% "
            f"{d['tail1_on']*100:8.1f}%{d['tail5_on']*100:8.1f}% {d['cum_on']*100:+7.1f}%{d['cum_id']*100:+7.1f}% "
            f"{d['sk_on']:8.2f}{d['sk_id']:8.2f}{d['ku_on']:8.1f}{d['ku_id']:8.1f} {d['sd_on']*100:9.1f}%{d['sd_id']*100:9.1f}%")
    return res

say("\n== 1. WHERE ARE THE LOSSES (shares are of the close-to-close quantity; tail = worst 1%/5% sessions of that window,")
say("   share of the log-return sum; cum = sum of log returns; ann sd = annualised sd of that half)")
Q1 = table1("QQQ (open/close, split-adjusted)", lambda r: r['on'], lambda r: r['id'])

# strategy's own series
for r, h, x in zip(rows, HW, RX):
    r['s_on'] = sum(h[j] * r['on_legs'][j] for j in range(5))
    r['s_cc'] = x
    r['s_id'] = (1 + x) / (1 + r['s_on']) - 1
    r['held'] = h
S1 = table1("LIVE strategy P&L (proxy; overnight = held weights x leg gaps; cost + XLU/cash inside intraday residual)",
            lambda r: r['s_on'], lambda r: r['s_id'])
xs = sum(1 for r in rows if r['held'][3] > 0.01 or r['held'][4] > 0.5)
say(f"  (rows with XLU held >1% or cash >50%, i.e. where the unsplit bucket matters: {xs} of {len(rows)} = {xs/len(rows)*100:.1f}%)")

# ------------------------------------------------------------------ real daily rows (SPMO/TQQQ/QLD/XLU/BOXX with opens)
say("\n  REAL DAILY instruments (kairos d,o,c files; opens cross-checked to data/*_ohlc.csv, 0 mismatches > 1c)")
pxd = {s: load_daily_csv(f'{MR.REPO}/{s}.csv') for s in ('SPMO', 'TQQQ', 'QLD', 'XLU')}
opd = {s: load_daily_csv(f'{MR.REPO}/{s}.csv', close_col='o') for s in ('SPMO', 'TQQQ', 'QLD', 'XLU')}
alld = sorted(set.intersection(*[set(x) for x in pxd.values()]) & set(qqq))
pxd['BOXX'] = build_cash_index(alld, load_daily_csv(f'{MR.REPO}/BOXX.csv'), load_tbill())
days = [d for d in alld if d >= '2015-11-02' and d in pxd['BOXX']]
fastd = compute_fast_states(qd, qqq); st = dict(zip(qd, compute_states(qd, qqq)))
gapsd = {d: {n: qv[qix[d]] / sma(qv, qix[d], n) - 1 for n in (100, 150, 200)} for d in days}
V30 = {d: realized_vol(qd, qqq, as_of=d) for d in days}; V10 = {d: realized_vol(qd, qqq, as_of=d, lookback=10) for d in days}
RD = []
for i in range(1, len(days)):
    d0, d1 = days[i - 1], days[i]; eff = effective_state(st[d0], fastd[d0])
    syms = ('SPMO', 'TQQQ', 'QLD', 'XLU', 'BOXX')
    legs = tuple(pxd[s][d1] / pxd[s][d0] - 1 for s in syms)
    onl = tuple(opd[s][d1] / pxd[s][d0] - 1 for s in syms[:4]) + (0.0,)
    RD.append(dict(d=d0, d1=d1, state=st[d0], eff=eff, agree=True, gaps=gapsd[d0], vol=V30[d0],
                   vol_live=(V30[d0] if not V10[d0] or not V30[d0] else max(V30[d0], V10[d0])),
                   key=(eff, extension_votes(eff, gapsd[d0])), legs=legs, on_legs=onl,
                   id_legs=tuple((1 + legs[j]) / (1 + onl[j]) - 1 for j in range(5)),
                   on=O[d1] / C[d0] - 1, id=C[d1] / O[d1] - 1, qqq=C[d1] / C[d0] - 1))
say(f"  {len(RD)} real daily rows {RD[0]['d']}..{RD[-1]['d1']}")
# reproduce vol_estimator_daily.simulate('max10_30') through run_x with the needs_rebalance policy
_src = open('paper-track/vol_estimator_daily.py').read().split('print("real DAILY')[0]
_ns = {}; exec(_src, _ns)
_ref, _nreb, _turn = _ns['simulate']('max10_30', 0.0004)
rd_rets, rd_expo, RDHW, rd_nreb, rd_turn, _ = run_x(RD, live_fn, policy='needs', trace=True)
assert len(_ref) == len(rd_rets) and max(abs(a[1] - b) for a, b in zip(_ref, rd_rets)) < 1e-12 and _nreb == rd_nreb - 1   # run_x counts the initial allocation
c, s, m = annual_stats(rd_rets)
say(f"  run_x(policy='needs') == vol_estimator_daily.simulate('max10_30') on all rows: {c*100:.2f}% / {s:.3f} / {m*100:.1f}%  reb/yr {rd_nreb/len(RD)*252:.0f}")
for r, h, x in zip(RD, RDHW, rd_rets):
    r['s_on'] = sum(h[j] * r['on_legs'][j] for j in range(5)); r['s_cc'] = x; r['s_id'] = (1 + x) / (1 + r['s_on']) - 1; r['held'] = h
def table1_rd(label, get_on, get_id):
    say(f"\n  {label}")
    say(f"  {'window':<28}{'n':>5} {'var ON':>7}{'var ID':>7}{'2cov':>6} {'semi ON':>8} {'tail1 ON':>9}{'tail5 ON':>9} {'cum ON':>8}{'cum ID':>8} {'skew ON':>8}{'skew ID':>8}{'kurt ON':>8}{'kurt ID':>8}")
    for lab, a, b in [('real era 2015-11..2026-08', '2015-11-01', '2099'), ('2018 Q4', '2018-10-01', '2018-12-31'),
                      ('COVID 2020-02-19..03-23', '2020-02-19', '2020-03-23'), ('2022 bear', '2022-01-01', '2022-12-31'),
                      ('2025 Apr tariff', '2025-03-01', '2025-04-30')]:
        sel = [r for r in RD if a <= r['d'] <= b]
        if len(sel) < 10: continue
        d = decomp([get_on(r) for r in sel], [get_id(r) for r in sel])
        say(f"  {lab:<28}{d['n']:>5} {d['var_on']*100:6.1f}%{d['var_id']*100:6.1f}%{d['cov2']*100:5.1f}% {d['semi_on']*100:7.1f}% "
            f"{d['tail1_on']*100:8.1f}%{d['tail5_on']*100:8.1f}% {d['cum_on']*100:+7.1f}%{d['cum_id']*100:+7.1f}% "
            f"{d['sk_on']:8.2f}{d['sk_id']:8.2f}{d['ku_on']:8.1f}{d['ku_id']:8.1f}")
table1_rd("QQQ, real-era windows", lambda r: r['on'], lambda r: r['id'])
table1_rd("LIVE strategy on REAL instruments (SPMO/TQQQ/QLD/XLU opens; BOXX unsplit)", lambda r: r['s_on'], lambda r: r['s_id'])
for s_ in ('SPMO', 'TQQQ', 'QLD', 'XLU'):
    j = ('SPMO', 'TQQQ', 'QLD', 'XLU').index(s_)
    d = decomp([r['on_legs'][j] for r in RD], [r['id_legs'][j] for r in RD])
    say(f"  {s_:<6} own split 2015-11+: var ON {d['var_on']*100:5.1f}%  semi ON {d['semi_on']*100:5.1f}%  tail5 ON {d['tail5_on']*100:5.1f}%  cum ON {d['cum_on']*100:+6.1f}%  cum ID {d['cum_id']*100:+6.1f}%  kurt ON/ID {d['ku_on']:.1f}/{d['ku_id']:.1f}")
# how good is the 3x/2x proxy split against the real funds?
j3 = [(3 * r['on'], r['on_legs'][1]) for r in RD]; j2 = [(2 * r['on'], r['on_legs'][2]) for r in RD]
def corr(p):
    a = [x for x, _ in p]; b = [y for _, y in p]; ma, mb = mean(a), mean(b)
    return sum((x - ma) * (y - mb) for x, y in p) / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
say(f"  proxy check: corr(3x QQQ gap, TQQQ gap) {corr(j3):.4f}, slope {sum(x*y for x,y in j3)/sum(x*x for x,_ in j3):.3f};  corr(2x QQQ gap, QLD gap) {corr(j2):.4f}, slope {sum(x*y for x,y in j2)/sum(x*x for x,_ in j2):.3f}")

# ------------------------------------------------------------------ 2. what does each overlay protect
say("\n== 2. WHAT DOES EACH OVERLAY PROTECT")
N = len(rows)
lon = [math.log1p(r['on']) for r in rows]; lid = [math.log1p(r['id']) for r in rows]
cum_on = [0.0]; cum_id = [0.0]
for a, b in zip(lon, lid): cum_on.append(cum_on[-1] + a); cum_id.append(cum_id[-1] + b)
def fwd(i, k):
    j = min(N, i + k); return cum_on[j] - cum_on[i], cum_id[j] - cum_id[i]

def damage_table(label, sel):
    say(f"\n  {label}: {len(sel)} sessions ({len(sel)/N*100:.1f}% of rows)")
    say(f"  {'horizon':<10}{'mean ON':>9}{'mean ID':>9}{'|neg windows: ON share of loss(agg)':>32}{'P(ON<ID)':>10}  | unconditional ON / ID")
    for k in (1, 5, 21):
        a = [fwd(i, k) for i in sel]; u = [fwd(i, k) for i in range(N)]
        neg = [(x, y) for x, y in a if x + y < 0]; negu = [(x, y) for x, y in u if x + y < 0]
        share = sum(x for x, _ in neg) / sum(x + y for x, y in neg) if neg else float('nan')
        shareu = sum(x for x, _ in negu) / sum(x + y for x, y in negu)
        say(f"  next {k:<5}{mean([x for x,_ in a])*100:+8.2f}%{mean([y for _,y in a])*100:+8.2f}% {share*100:30.1f}% {mean([1.0 if x<y else 0.0 for x,y in a])*100:9.1f}% "
            f" | {mean([x for x,_ in u])*100:+.2f}% / {mean([y for _,y in u])*100:+.2f}%  (neg-window ON share {shareu*100:.1f}%)")

tgt = [live_fn(r) for r in rows]
sel_vt = [i for i, r in enumerate(rows) if beta(tgt[i]) < beta(fn_no_vt(r)) - 1e-9]
sel_trim = [i for i, r in enumerate(rows) if beta(tgt[i]) < beta(fn_no_trim(r)) - 1e-9]
sel_fast_up = [i for i, r in enumerate(rows) if r['eff'] != r['state']]
sel_fast_dn = [i for i, r in enumerate(rows) if beta(tgt[i]) < beta(fn_no_fast(r)) - 1e-9]
say(f"  NOTE: the fast overlay only ever UPGRADES the row (B/C->A, F->C): sessions where it reduced exposure = {len(sel_fast_dn)}.")
damage_table("VOL TARGET reduced exposure (multiplier < 1)", sel_vt)
damage_table("EXTENSION TRIM reduced exposure (votes > 0 in effective A)", sel_trim)
damage_table("FAST OVERLAY raised exposure (eff != macro state) -- the mirror question", sel_fast_up)
# vt bite-sized buckets
for lo_, hi_ in ((0.9, 1.0), (0.7, 0.9), (0.5, 0.7), (0.0, 0.5)):
    sel = [i for i, r in enumerate(rows) if lo_ <= min(1.0, VOL_TARGET_PA / r['vol_live']) < hi_ - 1e-12]
    if sel: damage_table(f"VOL TARGET multiplier in [{lo_},{hi_})", sel)

# exposure INTO the worst gaps / worst intraday sessions
def into_table(kind, key, pcts=(0.01, 0.05)):
    order = sorted(range(N), key=lambda i: rows[i][key])
    legk = 'on_legs' if key == 'on' else 'id_legs'
    for p in pcts:
        k = int(math.ceil(N * p)); sel = order[:k]
        say(f"\n  WORST {p*100:.0f}% {kind} sessions (k={k}, mean QQQ {kind} {mean([rows[i][key] for i in sel])*100:+.2f}%, worst {rows[sel[0]][key]*100:+.2f}% on {rows[sel[0]]['d1']})")
        say(f"  {'allocation':<34}{'expo':>7}{'beta':>7}{'port ret':>10}{'avoided vs LIVE':>17}  | same alloc 1 session LATER: expo  beta")
        variants = [('macro only W[state]', fn_macro), ('+fast (W[eff])', lambda r: W[r['eff']]), ('+trim (no vt)', fn_no_vt),
                    ('LIVE target (fast+trim+vt live)', live_fn), ('LIVE with vt OFF', fn_no_vt), ('LIVE with trim OFF', fn_no_trim),
                    ('LIVE with fast OFF', fn_no_fast), ('LIVE with plain vol30', fn_vol30)]
        live_ret = mean([sum(rows[i]['held'][j] * rows[i][legk][j] for j in range(5)) for i in sel])
        for lab, f in variants:
            ws = [f(rows[i]) for i in sel]; ws1 = [f(rows[min(N - 1, i + 1)]) for i in sel]
            pr = mean([sum(w[j] * rows[i][legk][j] for j in range(5)) for w, i in zip(ws, sel)])
            say(f"  {lab:<34}{mean([expo(w) for w in ws])*100:6.1f}%{mean([beta(w) for w in ws]):7.2f}{pr*100:+9.2f}% {(live_ret-pr)*100:+16.2f}pp  | {mean([expo(w) for w in ws1])*100:6.1f}% {mean([beta(w) for w in ws1]):5.2f}")
        hs = [rows[i]['held'] for i in sel]; hs1 = [rows[min(N - 1, i + 1)]['held'] for i in sel]
        say(f"  {'LIVE HELD (with drift band)':<34}{mean([expo(w) for w in hs])*100:6.1f}%{mean([beta(w) for w in hs]):7.2f}{live_ret*100:+9.2f}% {'--':>16}  | {mean([expo(w) for w in hs1])*100:6.1f}% {mean([beta(w) for w in hs1]):5.2f}")
        # the day-after signature: how much does LIVE cut on the session right after the event?
        cut = mean([beta(rows[min(N-1,i+1)]['held']) - beta(rows[i]['held']) for i in sel])
        say(f"  beta change LIVE held: into event -> next session {cut:+.3f}  (unconditional mean |change| {mean([abs(beta(rows[i+1]['held'])-beta(rows[i]['held'])) for i in range(N-1)]):.3f})")
into_table('OVERNIGHT', 'on')
into_table('INTRADAY', 'id')

# ------------------------------------------------------------------ 3. reaction lag
say("\n== 3. REACTION LAG on the worst 20 overnight gaps and worst 20 intraday sessions")
say("   lag = sessions between the decision whose holding window contains the event (index 0 = decided the close")
say("   BEFORE the gap / before the session) and the first decision with the signal below the threshold.")
say("   <=0: protection was in place going into the event (-k = it had been in place for k sessions);")
say("   >0: it arrived k sessions after; '-' = never within 60 sessions after.")
mult_live = [min(1.0, VOL_TARGET_PA / r['vol_live']) if r['vol_live'] else 1.0 for r in rows]
mult_30 = [min(1.0, VOL_TARGET_PA / r['vol']) if r['vol'] else 1.0 for r in rows]
votes = [extension_votes(r['eff'], r['gaps']) if r['eff'] == 'A' else 0 for r in rows]
fast_up = [1 if r['eff'] != r['state'] else 0 for r in rows]
not_A = [0 if r['state'] == 'A' else 1 for r in rows]
def lag(series, i, cond):
    if cond(series[i]):
        k = 0
        while i + k - 1 >= 0 and cond(series[i + k - 1]): k -= 1
        return k
    for k in range(1, 61):
        if i + k < N and cond(series[i + k]): return k
    return None
def fmt(x): return '-' if x is None else f"{x:+d}"
def lag_table(kind, key):
    order = sorted(range(N), key=lambda i: rows[i][key])[:20]
    say(f"\n  worst 20 {kind}: columns = live max(10,30) mult <0.9/<0.7/<0.5 | plain 30d <0.9/<0.7/<0.5 | trim votes >=1/>=2/>=3 | fast upgrade on | macro state not A")
    say(f"  {'event d1':<12}{'QQQ ' + kind:>9}{'state':>6}{'eff':>4} {'live.9':>7}{'live.7':>7}{'live.5':>7} {'v30.9':>7}{'v30.7':>7}{'v30.5':>7} {'tr1':>5}{'tr2':>5}{'tr3':>5} {'fast':>6}{'notA':>6}  mult into / after")
    acc = {k: [] for k in ('l9', 'l7', 'l5', 'v9', 'v7', 'v5')}
    for i in order:
        r = rows[i]
        l9, l7, l5 = (lag(mult_live, i, lambda m, t=t: m < t) for t in (0.9, 0.7, 0.5))
        v9, v7, v5 = (lag(mult_30, i, lambda m, t=t: m < t) for t in (0.9, 0.7, 0.5))
        t1, t2, t3 = (lag(votes, i, lambda v, t=t: v >= t) for t in (1, 2, 3))
        fu = lag(fast_up, i, lambda v: v == 1); na = lag(not_A, i, lambda v: v == 1)
        for k, v in zip(('l9', 'l7', 'l5', 'v9', 'v7', 'v5'), (l9, l7, l5, v9, v7, v5)): acc[k].append(v)
        say(f"  {r['d1']:<12}{r[key]*100:+8.2f}%{r['state']:>6}{r['eff']:>4} {fmt(l9):>7}{fmt(l7):>7}{fmt(l5):>7} {fmt(v9):>7}{fmt(v7):>7}{fmt(v5):>7} {fmt(t1):>5}{fmt(t2):>5}{fmt(t3):>5} {fmt(fu):>6}{fmt(na):>6}  {mult_live[i]:.2f} / {mult_live[min(N-1,i+1)]:.2f}")
    def summ(v):
        inpl = sum(1 for x in v if x is not None and x <= 0); after = sum(1 for x in v if x is not None and x > 0); never = sum(1 for x in v if x is None)
        med = sorted(x for x in v if x is not None); med = med[len(med) // 2] if med else None
        return f"in place {inpl:2d} / after {after:2d} / never {never:2d}, median lag {fmt(med)}"
    for k, lab in (('l9', 'live <0.9'), ('l7', 'live <0.7'), ('l5', 'live <0.5'), ('v9', 'vol30 <0.9'), ('v7', 'vol30 <0.7'), ('v5', 'vol30 <0.5')):
        say(f"    {lab:<11} {summ(acc[k])}")
lag_table('overnight gaps', 'on')
lag_table('intraday sessions', 'id')
# a broader version: worst 1% (66 events) -- in place vs after, live estimator
for key, kind in (('on', 'gaps'), ('id', 'intraday')):
    order = sorted(range(N), key=lambda i: rows[i][key])[:int(math.ceil(N * 0.01))]
    for t in (0.9, 0.7, 0.5):
        v = [lag(mult_live, i, lambda m, t=t: m < t) for i in order]
        v30 = [lag(mult_30, i, lambda m, t=t: m < t) for i in order]
        say(f"  worst 1% {kind:<9} live mult <{t}: in place {sum(1 for x in v if x is not None and x<=0):2d}/{len(v)}  after(<=60) {sum(1 for x in v if x is not None and x>0):2d}  never {sum(1 for x in v if x is None):2d}"
            f"   | vol30: in place {sum(1 for x in v30 if x is not None and x<=0):2d}  after {sum(1 for x in v30 if x is not None and x>0):2d}  never {sum(1 for x in v30 if x is None):2d}")

# ------------------------------------------------------------------ 4. execution-convention counterfactuals
say("\n== 4. EXECUTION CONVENTION COUNTERFACTUALS (through run_x; half-rows)")
say("   V0 live: decide close d0, trade close d0 -> new weights earn overnight(d0->d1) + intraday(d1)")
say("   V1 open: decide close d0, trade open d1  -> OLD weights earn overnight(d0->d1), new weights earn intraday(d1)")
say("            (the drift-band check and the cost are taken at the open; the 'morning routine' with prior-close signals is this same row set)")
say("   V1b:     SAME trade decisions as V0 (drift band judged at the close d0) but the fill happens at the open d1 -- the pure timing test")
say("   V2 lag1: decide close d0, trade close d1  -> one full session of lag (the standing reference for execution delay)")
def half_rows(rows_, mode):
    out = []
    for i, r in enumerate(rows_):
        base = {k: v for k, v in r.items() if k not in ('legs',)}
        on = dict(base, legs=r['on_legs'], half='on', trade=(mode in ('V0', 'V1b')), defer=(mode == 'V1b'))
        idr = dict(base, legs=r['id_legs'], half='id', trade=(mode == 'V1'))
        out.append(on); out.append(idr)
    return out
def combine(rets2):
    return [(1 + rets2[2 * i]) * (1 + rets2[2 * i + 1]) - 1 for i in range(len(rets2) // 2)]
def lag_rows(rows_):
    out = []
    for i in range(1, len(rows_)):
        r = dict(rows_[i - 1]); r['legs'] = rows_[i]['legs']; r['on_legs'] = rows_[i]['on_legs']; r['id_legs'] = rows_[i]['id_legs']; r['d_ret'] = rows_[i]['d']
        out.append(r)
    return out
def eval_series(rets, dates_):
    c, s, m = annual_stats(rets)
    ss = annual_stats([x for x, d in zip(rets, dates_) if SEARCH[0] <= d <= SEARCH[1]])[1]
    hs = annual_stats([x for x, d in zip(rets, dates_) if HOLDOUT[0] <= d <= HOLDOUT[1]])[1]
    return c, s, m, ss, hs

# check: V0 through half-rows == daily harness
h0 = combine(run_x(half_rows(rows, 'V0'), live_fn)[0])
_md = max(abs(a - b) for a, b in zip(h0, R0)); assert _md < 1e-4   # residual after removing cost*r_id is ~1e-16
_c0 = annual_stats(h0); _c1 = annual_stats(R0)
say(f"  check: V0 rebuilt from overnight+intraday half-rows vs the daily harness: max |diff| per session {_md:.1e} (the cost x intraday cross-term),")
say(f"         CAGR {_c0[0]*100:.3f}% vs {_c1[0]*100:.3f}%, Sharpe {_c0[1]:.4f} vs {_c1[1]:.4f}, MDD {_c0[2]*100:.2f}% vs {_c1[2]*100:.2f}%")
CF = {}
say(f"\n  {'variant':<28}{'cost':>5} {'CAGR':>8}{'Sharpe':>8}{'MDD':>8}{'S':>8}{'H':>8}{'reb/yr':>8}  | dCAGR dSharpe dMDD vs V0")
for cost in (0.0004, 0.0010, 0.0020):
    base = None
    for lab, mk_rows, mode in (('V0 live (close)', lambda: half_rows(rows, 'V0'), 'half'), ('V1 next open', lambda: half_rows(rows, 'V1'), 'half'), ('V1b close-decide/open-fill', lambda: half_rows(rows, 'V1b'), 'half'), ('V2 lag 1 session', lambda: lag_rows(rows), 'day')):
        rs = mk_rows(); res = run_x(rs, live_fn, spread=cost)
        rets = combine(res[0]) if mode == 'half' else res[0]
        dd = [r['d'] for r in rows] if mode == 'half' else [r['d_ret'] for r in rs]
        c, s, m, ss, hs = eval_series(rets, dd); nreb = res[3] / len(rets) * 252
        CF[(lab, cost)] = rets
        if base is None: base = (c, s, m)
        say(f"  {lab:<28}{cost*1e4:4.0f}bp {c*100:7.2f}%{s:8.3f}{m*100:7.1f}%{ss:8.3f}{hs:8.3f}{nreb:8.0f}  | {(c-base[0])*100:+.2f}pp {s-base[1]:+.3f} {(m-base[2])*100:+.1f}pp")
# V1 vs V0 by regime & bootstrap at 4bp
a, b = CF[('V1 next open', 0.0004)], CF[('V0 live (close)', 0.0004)]
say("\n  V1 - V0 (4bp) by regime, log-return pp/yr and Sharpe difference:")
for lab, lo_, hi_ in REGIMES:
    idx_ = [i for i, r in enumerate(rows) if lo_ <= r['d'] <= hi_]
    if len(idx_) < 30: continue
    la, sa = bstats([a[i] for i in idx_]); lb, sb = bstats([b[i] for i in idx_])
    say(f"    {lab:<28} {(la-lb)*100:+6.2f}pp/yr  Sharpe {sa-sb:+.3f}   (V0 there: {lb*100:+.1f}%/yr, {sb:.2f})")
say("  block bootstrap V1 - V0 (4bp), 2000 resamples:")
for blk in (20, 60):
    l1, l2, pl, s1, s2, ps = boot(a, b, blk, seed=11 + blk)
    say(f"    block {blk:>2}d: log-return 95% CI [{l1*100:+.2f}, {l2*100:+.2f}] pp/yr  P(<=0)={pl:.3f}   Sharpe CI [{s1:+.3f}, {s2:+.3f}]  P(<=0)={ps:.3f}")
# decomposition of the V1-V0 difference: gap P&L at old vs new weights
say("  where the difference comes from (PRE-COST, costs shown separately), mean per session in bp:")
hv0 = run_x(half_rows(rows, 'V0'), live_fn, trace=True); hv1 = run_x(half_rows(rows, 'V1'), live_fn, trace=True); hvb = run_x(half_rows(rows, 'V1b'), live_fn, trace=True)
on0 = [hv0[0][2 * i] + hv0[5][2 * i] for i in range(N)]; on1 = [hv1[0][2 * i] + hv1[5][2 * i] for i in range(N)]; onb = [hvb[0][2 * i] + hvb[5][2 * i] for i in range(N)]
id0 = [hv0[0][2 * i + 1] + hv0[5][2 * i + 1] for i in range(N)]; id1 = [hv1[0][2 * i + 1] + hv1[5][2 * i + 1] for i in range(N)]; idb = [hvb[0][2 * i + 1] + hvb[5][2 * i + 1] for i in range(N)]
c0 = [hv0[5][2 * i] + hv0[5][2 * i + 1] for i in range(N)]; c1 = [hv1[5][2 * i] + hv1[5][2 * i + 1] for i in range(N)]; cb = [hvb[5][2 * i] + hvb[5][2 * i + 1] for i in range(N)]
say(f"    overnight: V0 {mean(on0)*1e4:+.2f}bp  V1 {mean(on1)*1e4:+.2f}bp  V1b {mean(onb)*1e4:+.2f}bp | intraday: V0 {mean(id0)*1e4:+.2f}bp  V1 {mean(id1)*1e4:+.2f}bp  V1b {mean(idb)*1e4:+.2f}bp | cost: V0 {mean(c0)*1e4:.2f}bp  V1 {mean(c1)*1e4:.2f}bp  V1b {mean(cb)*1e4:.2f}bp")
say(f"    x252: overnight V1-V0 {(mean(on1)-mean(on0))*252*100:+.2f}pp/yr  V1b-V0 {(mean(onb)-mean(on0))*252*100:+.2f}pp/yr | intraday V1-V0 {(mean(id1)-mean(id0))*252*100:+.2f}pp/yr  V1b-V0 {(mean(idb)-mean(id0))*252*100:+.2f}pp/yr")
# does V1's open fill buy into intraday continuation? intraday at V1 vs V0 held weights, split by the sign of the gap
for lab, cond in (('after gap-down sessions (QQQ gap < -1%)', lambda r: r['on'] < -0.01), ('after gap-up sessions (QQQ gap > +1%)', lambda r: r['on'] > 0.01), ('|gap| <= 1%', lambda r: abs(r['on']) <= 0.01)):
    idx_ = [i for i, r in enumerate(rows) if cond(r)]
    say(f"    intraday P&L {lab:<40} n={len(idx_):5d}  V0 {sum(id0[i] for i in idx_)*100:+7.2f}pp  V1 {sum(id1[i] for i in idx_)*100:+7.2f}pp  (QQQ intraday mean {mean([rows[i]['id'] for i in idx_])*1e4:+.1f}bp)")
for lab, lo_, hi_ in REGIMES[1:8]:
    idx_ = [i for i, r in enumerate(rows) if lo_ <= r['d'] <= hi_]
    say(f"    {lab:<28} overnight V0 {sum(on0[i] for i in idx_)*100:+6.1f}%  V1 {sum(on1[i] for i in idx_)*100:+6.1f}%  | intraday V0 {sum(id0[i] for i in idx_)*100:+6.1f}%  V1 {sum(id1[i] for i in idx_)*100:+6.1f}%")
# exposure into worst gaps under V1 vs V0 (held)
order = sorted(range(N), key=lambda i: rows[i]['on'])[:int(math.ceil(N * 0.05))]
say(f"    beta held INTO the worst-5% gaps: V0 {mean([beta(hv0[2][2*i]) for i in order]):.2f}  V1 {mean([beta(hv1[2][2*i]) for i in order]):.2f}   (all sessions: V0 {mean([beta(h) for h in hv0[2][::2]]):.2f}  V1 {mean([beta(h) for h in hv1[2][::2]]):.2f})")
def mdd_info(rets):
    nav = pk = 1.0; mdd = 0; pkd = trd = None; pkc = rows[0]['d']
    for r_, x in zip(rows, rets):
        nav *= 1 + x
        if nav >= pk: pk = nav; pkc = r_['d1']
        if nav / pk - 1 < mdd: mdd = nav / pk - 1; pkd = pkc; trd = r_['d1']
    return mdd, pkd, trd
for lab in ('V0 live (close)', 'V1 next open', 'V1b close-decide/open-fill', 'V2 lag 1 session'):
    m_, pk_, tr_ = mdd_info(CF[(lab, 0.0004)]); say(f"    max drawdown {lab:<28} {m_*100:6.1f}%  peak {pk_} -> trough {tr_}")
# what triggered the d0 rebalance on the sessions where V1 and V0 differ overnight?
hv0h = hv0[2]; diff_on = [on1[i] - on0[i] for i in range(N)]
trig = {'regime flip at d0': [], 'drift-band trade at d0': [], 'no trade at d0': []}
prevk = None
for i, r in enumerate(rows):
    k = (r['state'], r['agree']); traded = (i > 0 and hv0h[2 * i] != hv0h[2 * i - 1])
    lab = 'no trade at d0' if not traded else ('regime flip at d0' if k != prevk else 'drift-band trade at d0'); trig[lab].append(i); prevk = k
say("    V1 - V0 overnight P&L (sum of session differences) by what happened at the d0 close in V0:")
for lab, idx_ in trig.items():
    say(f"      {lab:<24} n={len(idx_):5d}  sum {sum(diff_on[i] for i in idx_)*100:+7.2f}pp  mean {mean([diff_on[i] for i in idx_])*1e4 if idx_ else 0:+.2f}bp  | sum over the worst-5% gaps in this group {sum(diff_on[i] for i in idx_ if i in set(order))*100:+.2f}pp")
say("    (positive = V1 did better, i.e. the OLD weights were the better ones to hold through that gap)")
top = sorted(range(N), key=lambda i: abs(diff_on[i]), reverse=True)[:12]
say("    the 12 sessions with the largest |V1 - V0| overnight difference (beta held through the gap: V0 = new weights, V1 = old):")
say(f"    {'gap date':<12}{'QQQ gap':>9}{'state d-1->d0':>15}{'eff':>8}{'beta V0':>9}{'beta V1':>9}{'V1-V0':>9}  trigger at d0")
for i in sorted(top, key=lambda i: rows[i]['d1']):
    r = rows[i]; pr = rows[i - 1] if i > 0 else r
    trig_lab = [k for k, v in trig.items() if i in set(v)][0]
    say(f"    {r['d1']:<12}{r['on']*100:+8.2f}%{pr['state']+'->'+r['state']:>15}{pr['eff']+'->'+r['eff']:>8}{beta(hv0h[2*i]):9.2f}{beta(hv1[2][2*i]):9.2f}{diff_on[i]*100:+8.2f}pp  {trig_lab}  (mult live {mult_live[i-1] if i>0 else 1:.2f}->{mult_live[i]:.2f})")

# real daily
say("\n  REAL DAILY instruments (needs_rebalance policy, SPMO/TQQQ/QLD/XLU/BOXX), same three conventions:")
say(f"  {'variant':<28}{'cost':>5} {'CAGR':>8}{'Sharpe':>8}{'MDD':>8}{'reb/yr':>8}  | dCAGR dSharpe dMDD vs V0")
for cost in (0.0004, 0.0010, 0.0020):
    base = None
    for lab, mk_rows, mode in (('V0 live (close)', lambda: half_rows(RD, 'V0'), 'half'), ('V1 next open', lambda: half_rows(RD, 'V1'), 'half'), ('V1b close-decide/open-fill', lambda: half_rows(RD, 'V1b'), 'half'), ('V2 lag 1 session', lambda: lag_rows(RD), 'day')):
        rs = mk_rows(); res = run_x(rs, live_fn, spread=cost, policy='needs')
        rets = combine(res[0]) if mode == 'half' else res[0]
        c, s, m = annual_stats(rets); nreb = res[3] / len(rets) * 252
        if base is None: base = (c, s, m)
        say(f"  {lab:<28}{cost*1e4:4.0f}bp {c*100:7.2f}%{s:8.3f}{m*100:7.1f}%{nreb:8.0f}  | {(c-base[0])*100:+.2f}pp {s-base[1]:+.3f} {(m-base[2])*100:+.1f}pp")
# real weekly rr: first overnight after d0 at old vs new weights
say("\n  REAL WEEKLY rr (RF.eval_real convention: full weekly reset, cost on |dw|): V0 vs V1 where V1 = OLD weights through the")
say("  first overnight gap after d0 and NEW weights for the rest of the week; only that first gap moves.")
OH = {}
for s_ in ('spmo', 'tqqq', 'qld', 'xlu'):
    OH[s_] = {x['d']: (float(x['o']), float(x['c'])) for x in csv.DictReader(open(f'data/{s_}_ohlc.csv'))}
    OH[s_ + '_d'] = sorted(OH[s_])
def first_gap(s_, d0):
    dd = OH[s_ + '_d']; import bisect
    j = bisect.bisect_right(dd, d0)
    if j >= len(dd) or d0 not in OH[s_]: return None
    return OH[s_][dd[j]][0] / OH[s_][d0][1] - 1
rr2 = []
for r in rr:
    g = [first_gap(s_, r['d0']) for s_ in ('spmo', 'tqqq', 'qld', 'xlu')]
    if any(x is None for x in g): continue
    r = dict(r); r['on_legs'] = tuple(g) + (0.0,); r['rest_legs'] = tuple((1 + r['legs'][j]) / (1 + r['on_legs'][j]) - 1 for j in range(5)); rr2.append(r)
def eval_real_x(rows_, wfn, mode, spread=0.0004):
    prev = None; rets = []
    for r in rows_:
        w = wfn(r); cost = spread * sum(abs(w[i] - (prev[i] if prev else 0)) for i in range(5))
        wg = w if (mode == 'V0' or prev is None) else prev
        ret = sum(wg[j] * (1 + r['on_legs'][j]) for j in range(5)) * sum(w[j] * (1 + r['rest_legs'][j]) for j in range(5)) - 1 if mode == 'V1' else sum(w[j] * r['legs'][j] for j in range(5))
        rets.append(ret - cost); prev = w
    n = len(rets); nav = 1.0
    for x in rets: nav *= 1 + x
    m = mean(rets); v = var(rets) ** 0.5; pk = cur = 1.0; mdd = 0
    for x in rets:
        cur *= 1 + x; pk = max(pk, cur); mdd = min(mdd, cur / pk - 1)
    return dict(cagr=nav ** (52 / n) - 1, sharpe=m * 52 / (v * math.sqrt(52)), mdd=mdd)
e0 = eval_real_x(rr2, live_real, 'V0'); eref = RF.eval_real(rr2, live_real)
assert abs(e0['sharpe'] - eref['sharpe']) < 1e-12
for cost in (0.0004, 0.0010, 0.0020):
    e0 = eval_real_x(rr2, live_real, 'V0', cost); e1 = eval_real_x(rr2, live_real, 'V1', cost)
    say(f"  {cost*1e4:4.0f}bp  V0 {e0['cagr']*100:.2f}% / {e0['sharpe']:.3f} / {e0['mdd']*100:.1f}%   V1 {e1['cagr']*100:.2f}% / {e1['sharpe']:.3f} / {e1['mdd']*100:.1f}%   d {(e1['cagr']-e0['cagr'])*100:+.2f}pp {e1['sharpe']-e0['sharpe']:+.3f}  ({len(rr2)} weeks)")

# ------------------------------------------------------------------ 5. overnight-aware variants (brief)
say("\n== 5. OVERNIGHT-AWARE VARIANTS, exposure-matched by T re-calibration (5 candidates + 2 sign-flips)")
# causal series on the daily QQQ calendar
ON_all = {od[i]: O[od[i]] / C[od[i - 1]] - 1 for i in range(1, len(od))}
CC_all = {od[i]: C[od[i]] / C[od[i - 1]] - 1 for i in range(1, len(od))}
def wvar(d, n, a):
    """annualised sqrt(var_cc + (a-1) var_on) over the n sessions ending at d (causal, d = decision date)."""
    i = oix[d]
    if i - n + 1 < 1: return None
    cc = [CC_all[od[k]] for k in range(i - n + 1, i + 1)]; on = [ON_all[od[k]] for k in range(i - n + 1, i + 1)]
    return math.sqrt(max(var(cc) + (a - 1) * var(on), 0.0) * 252)
def attach_w(key):
    a = float(key[1:])
    for r in rows:
        v10, v30 = wvar(r['d'], 10, a), wvar(r['d'], 30, a)
        r[key] = v30 if (v10 is None or v30 is None) else max(v10, v30)
# causal gap-gate threshold: trailing 252-session 95th / 99th percentile of |gap| (min 252 sessions)
absg = [abs(ON_all[d]) for d in od[1:]]
thr95 = {}; thr99 = {}; thr05 = {}
for i in range(1, len(od)):
    if i < 252: continue
    w = sorted(absg[i - 252:i]); thr95[od[i]] = w[int(0.95 * 252)]; thr99[od[i]] = w[int(0.99 * 252)]; thr05[od[i]] = w[int(0.05 * 252)]
for r in rows:
    g = ON_all.get(r['d'])   # the gap INTO the decision session (known at the close)
    r['gate95'] = 1 if (g is not None and r['d'] in thr95 and abs(g) > thr95[r['d']]) else 0
    r['gate99'] = 1 if (g is not None and r['d'] in thr99 and abs(g) > thr99[r['d']]) else 0
    r['gate_small'] = 1 if (g is not None and r['d'] in thr05 and abs(g) < thr05[r['d']]) else 0
say(f"  gate rows: |gap| > trailing-252 p95 on {sum(r['gate95'] for r in rows)} rows, > p99 on {sum(r['gate99'] for r in rows)} rows (sign-flip: |gap| < trailing p05 on {sum(r['gate_small'] for r in rows)} rows)")

def mk_var(kind, T):
    def fn(r):
        w = trim_of(W[r['eff']], r['eff'], r['gaps'])
        if kind.startswith('w'):
            return vt(w, r[kind], T)
        if kind.startswith('gate'):
            w = vt(w, r['vol_live'], T)
            if r[kind]: w = tuple(x * 0.5 for x in w[:4]) + (1 - 0.5 * sum(w[:4]),)
            return w
        return vt(w, r['vol_live'], T)
    return fn
def calib(kind, target=LIVE_EXPO, lo=0.02, hi=3.0):
    for _ in range(40):
        mid = (lo + hi) / 2
        if run(rows, mk_var(kind, mid))[1] < target: lo = mid
        else: hi = mid
    return (lo + hi) / 2
CAND = []
say(f"  {'candidate':<30}{'T*':>7}{'CAGR':>8}{'Sharpe':>8}{'MDD':>8}{'S':>8}{'H':>8}{'expo':>7}{'both?':>7}  real weekly")
base_ev = ev
for kind, lab in (('w1', 'live (a=1, T recal check)'), ('w1.5', 'ON x1.5 var, max(10,30)'), ('w2', 'ON x2 var, max(10,30)'), ('w3', 'ON x3 var, max(10,30)'),
                  ('gate95', 'gap gate p95: risky x0.5'), ('gate99', 'gap gate p99: risky x0.5'),
                  ('w0.5', 'SIGN-FLIP ON x0.5 var'), ('w0.25', 'SIGN-FLIP ON x0.25 var'), ('w0', 'SIGN-FLIP ON x0 (intraday-only var)'), ('gate_small', 'SIGN-FLIP gate on smallest-5% gaps')):
    if kind.startswith('w'): attach_w(kind)
    T = calib(kind); f = mk_var(kind, T); e_ = evaluate(rows, f)
    # real weekly: same rule with T*, needs the estimator on rr's calendar
    for r in rr:
        if kind.startswith('w'):
            v10, v30 = wvar(r['d0'], 10, float(kind[1:])), wvar(r['d0'], 30, float(kind[1:])); r[kind] = v30 if (v10 is None or v30 is None) else max(v10, v30)
        elif kind.startswith('gate'):
            g = ON_all.get(r['d0']); th = thr95 if kind != 'gate99' else thr99
            r[kind] = 1 if (g is not None and r['d0'] in th and (abs(g) < thr05[r['d0']] if kind == 'gate_small' else abs(g) > th[r['d0']])) else 0
    def fr(r, kind=kind, T=T):
        w = trim_of(W[r['eff']], r['eff'], r['gaps'])
        if kind.startswith('w'): return RF.vt(w, r[kind], T)
        w = RF.vt(w, r['vol_live'], T)
        if r[kind]: w = tuple(x * 0.5 for x in w[:4]) + (1 - 0.5 * sum(w[:4]),)
        return w
    er = RF.eval_real(rr, fr)
    both = 'YES' if (e_['s_sharpe'] > base_ev['s_sharpe'] and e_['h_sharpe'] > base_ev['h_sharpe']) else ''
    say(f"  {lab:<30}{T:7.3f}{e_['cagr']*100:7.2f}%{e_['sharpe']:8.3f}{e_['mdd']*100:7.1f}%{e_['s_sharpe']:8.3f}{e_['h_sharpe']:8.3f}{e_['risky']*100:6.1f}%{both:>7}  {er['cagr']*100:.2f}% / {er['sharpe']:.3f} / {er['mdd']*100:.1f}%")
    CAND.append((lab, kind, T, e_, f))
best = max([c for c in CAND if not c[0].startswith('SIGN') and c[1] != 'w1'], key=lambda c: c[3]['sharpe'])
bestf = max([c for c in CAND if c[0].startswith('SIGN') and c[1] != 'gate_small'], key=lambda c: c[3]['sharpe'])
for tag, c_ in (('best non-placebo', best), ('best SIGN-FLIP', bestf)):
    say(f"  {tag} by full Sharpe: {c_[0]} ({c_[3]['sharpe']:.3f} vs live {base_ev['sharpe']:.3f}); block bootstrap vs live:")
    rb = run(rows, c_[4])[0]
    for blk in (20, 60):
        l1, l2, pl, s1, s2, ps = boot(rb, R0, blk, seed=101 + blk)
        say(f"    block {blk:>2}d: log-return 95% CI [{l1*100:+.2f}, {l2*100:+.2f}] pp/yr  P(<=0)={pl:.3f}   Sharpe CI [{s1:+.3f}, {s2:+.3f}]  P(<=0)={ps:.3f}")
    # leave-one-regime-out
    a_ = rb; b_ = R0; loro = []
    for rlab, a0, b0 in (('dot-com', '2000-01-01', '2002-12-31'), ('GFC', '2007-01-01', '2009-12-31'), ('COVID', '2020-01-01', '2020-12-31'), ('2022', '2022-01-01', '2022-12-31'), ('SPMO era', '2015-11-01', '2099')):
        keep = [i for i, r in enumerate(rows) if not (a0 <= r['d'] <= b0)]
        loro.append(f"{rlab} {bstats([a_[i] for i in keep])[1]-bstats([b_[i] for i in keep])[1]:+.3f}")
    say("    leave-one-regime-out Sharpe diff: " + ', '.join(loro))
say("  real DAILY instruments (needs_rebalance harness) at the proxy T*, 4bp:")
for c_ in CAND:
    if not c_[1].startswith('w'): continue
    a_ = float(c_[1][1:])
    for r in RD:
        v10, v30 = wvar(r['d'], 10, a_), wvar(r['d'], 30, a_); r[c_[1]] = v30 if (v10 is None or v30 is None) else max(v10, v30)
    def frd(r, kind=c_[1], T=c_[2]): return vt(trim_of(W[r['eff']], r['eff'], r['gaps']), r[kind], T)
    res = run_x(RD, frd, policy='needs'); cc_, ss_, mm_ = annual_stats(res[0])
    say(f"    {c_[0]:<36} T* {c_[2]:.3f}  {cc_*100:.2f}% / {ss_:.3f} / {mm_*100:.1f}%  expo {res[1]*100:.1f}%  reb/yr {res[3]/len(RD)*252:.0f}")
say(f"  candidate count: 5 (3 overnight-upweighted estimators, 2 gap gates) + 4 sign-flips; both-era survivors among the 5: {sum(1 for c in CAND if not c[0].startswith('SIGN') and c[1]!='w1' and c[3]['s_sharpe']>base_ev['s_sharpe'] and c[3]['h_sharpe']>base_ev['h_sharpe'])}")

say(f"\nelapsed {time.time()-T0:.0f}s")
open('/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/overnight_intraday.out', 'w').write('\n'.join(OUT))
