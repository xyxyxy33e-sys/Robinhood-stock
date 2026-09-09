"""Research line `recovery_study` (2026-09-09): event-by-event recovery participation.

Owner's framing: "The important question is whether protection pays for its
subsequent recovery cost across many episodes, rather than just improving
maximum drawdown."  Objective is growth (beat SPY/QQQ), so a missed recovery
costs as much as an avoided decline earns.

EPISODES are defined systematically on the QQQ close series (`px` over `ds`):
  running high  = trailing RUN_N(=252)-session max close, including today;
  segment       = the span between two consecutive running-high dates;
  peak/trough   = the first high date / the min close inside the segment;
  R (recovery)  = the next running-high date (price above every close of the
                  past year), F = first close >= the true peak (may be far
                  away or never: dot-com's F is 2015);
  R_win         = window end used for the recovery measures: F if the peak is
                  regained before the NEXT qualifying episode starts, else
                  that next episode's peak date (the running-high date).
Primary set: depth <= -15%.  Secondary set: -8% > depth > -15%.
The dot-com peak (2000-03-27) predates the first strategy row (2000-07-03);
that episode's strategy measures start on the first row (flagged).

All portfolio returns come from the harness `run()` (costs + 3% drift band
inside it) at one-way spread 4 / 10 / 20 bp, set via
improvement_search.ONE_WAY_SPREAD exactly as vrp_signal.py does.  The per-
session exposure path needs the held weights, which run() does not return, so
`run_path` is a verbatim copy of run() with one extra output list; every call
asserts its return series is bit-identical to run()'s.  Real weekly rows use a
per-row copy of return_frontier.eval_real's loop, asserted against eval_real.

Nothing here is applied; the change freeze holds until 2026-12-07.
"""
import sys, math, statistics, os
sys.path.insert(0, 'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
import improvement_search as IS
import voltarget_live_backtest as VL
from improvement_search import SEARCH, HOLDOUT
from state import extension_scale, extension_votes, realized_vol
from block_bootstrap import boot, stats, N_BOOT

RUN_N = 252
MIN_DD = 0.15
SEC_LO = 0.08
BOOK = 200_000.0
COSTS = (0.0004, 0.0010, 0.0020)
PRE_N = 21          # sessions before the peak that define "pre-episode exposure"
REPART = 0.90       # back to >= 90% of pre-episode exposure
NOTES = 'paper-track/research_notes'
PATHS_LOG = os.path.join(NOTES, 'recovery_study_paths.log')

# ---------------------------------------------------------------- portfolios
def trimmed(w, eff, gaps):
    f = extension_scale(eff, gaps)
    return w if f >= 1 else tuple(x * f for x in w[:4]) + (1 - f * sum(w[:4]),)


def make_fns(vtf):
    return {
        'LIVE':       lambda r: vtf(trimmed(W[r['eff']], r['eff'], r['gaps']), r['vol_live']),
        'LIVE-fast':  lambda r: vtf(trimmed(W[r['state']], r['state'], r['gaps']), r['vol_live']),
        'LIVE-trim':  lambda r: vtf(W[r['eff']], r['vol_live']),
        'LIVE vol30': lambda r: vtf(trimmed(W[r['eff']], r['eff'], r['gaps']), r['vol']),
        'LIVE-VT':    lambda r: trimmed(W[r['eff']], r['eff'], r['gaps']),
        'BASE+VT':    lambda r: vtf(W[r['state']], r['vol_live']),
        'BASE':       lambda r: W[r['state']],
        'QQQ':        lambda r: (1.0, 0.0, 0.0, 0.0, 0.0),
        'A5050':      lambda r: (0.5, 0.5, 0.0, 0.0, 0.0),
    }

FNS = make_fns(vt)
FNS_REAL = make_fns(RF.vt)
LOO = ('LIVE-fast', 'LIVE-trim', 'LIVE vol30', 'LIVE-VT')
PORTS = list(FNS)


def run_path(rows, wfn, band=IS.BAND):
    """Verbatim copy of improvement_search.run() plus the held risky weight per
    session.  Asserted identical to run() on every call."""
    held = prev = None
    rets, expo = [], []
    for r in rows:
        t = wfn(r)
        key = (r['state'], r['agree'])
        cost = 0.0
        if held is None:
            held = list(t)
        else:
            drift = sum(abs(t[j] - held[j]) for j in range(5))
            if key != prev or drift > band:
                cost = IS.ONE_WAY_SPREAD * drift
                held = list(t)
        expo.append(sum(held[:4]))
        g = sum(held[j] * r['legs'][j] for j in range(5))
        rets.append(g - cost)
        dn = 1 + g
        if dn > 0:
            held = [held[j] * (1 + r['legs'][j]) / dn for j in range(5)]
        prev = key
    ref, ref_exp = run(rows, wfn)
    assert rets == ref and abs(sum(expo) / len(expo) - ref_exp) < 1e-12, 'run_path drifted from run()'
    return rets, expo


def nav_of(rets):
    nav = [1.0]
    for x in rets:
        nav.append(nav[-1] * (1 + x))
    return nav

# ---------------------------------------------------------------- standing figures
def live_real(r):
    return FNS_REAL['LIVE'](r)

for r in rr:
    a = realized_vol(qd, qqq, as_of=r['d0'], lookback=30); b = realized_vol(qd, qqq, as_of=r['d0'], lookback=10)
    r['vol_live'] = a if (a is None or b is None) else max(a, b)
ev = evaluate(rows, FNS['LIVE']); er = RF.eval_real(rr, live_real)
print(f"STANDING LIVE FIGURES  proxy {ev['cagr']*100:.2f}% / {ev['sharpe']:.3f} / {ev['mdd']*100:.1f}%  "
      f"S {ev['s_sharpe']:.3f} H {ev['h_sharpe']:.3f}  |  real {er['cagr']*100:.2f}% / {er['sharpe']:.3f} / {er['mdd']*100:.1f}%")
assert abs(ev['cagr'] - 0.2212) < 5e-4 and abs(ev['sharpe'] - 0.938) < 1e-3 and abs(er['sharpe'] - 1.260) < 1e-3

# ---------------------------------------------------------------- episodes
vals = [px[d] for d in ds]
N = len(ds)
D0 = rows[0]['d']
rix = {r['d']: k for k, r in enumerate(rows)}
rix[ds[-1]] = len(rows)                 # NAV after the last row's d0->d1 return
di = {d: i for i, d in enumerate(ds)}

high = []
for i in range(N):
    lo = max(0, i - RUN_N + 1)
    high.append(vals[i] >= max(vals[lo:i + 1]))
hi_idx = [i for i in range(N) if high[i]]


def segments():
    out = []
    for a, b in zip(hi_idx, hi_idx[1:] + [None]):
        if b is not None and b == a + 1:
            continue
        end = b if b is not None else N - 1
        t = min(range(a + 1, end + 1), key=lambda i: vals[i])
        depth = vals[t] / vals[a] - 1
        F = next((i for i in range(t, N) if vals[i] >= vals[a]), None)
        out.append(dict(P=a, T=t, R=b, F=F, depth=depth, open=(b is None)))
    return out

SEGS = [s for s in segments() if ds[s['T']] >= D0 and ds[s['P']] <= rows[-1]['d']]
PRIMARY = [s for s in SEGS if s['depth'] <= -MIN_DD]
SECOND = [s for s in SEGS if -MIN_DD < s['depth'] <= -SEC_LO]


def finish(eps):
    """Attach R_win, the clipped strategy peak, era and depth bucket."""
    for k, e in enumerate(eps):
        nxt = eps[k + 1]['P'] if k + 1 < len(eps) else None
        if e['F'] is not None and (nxt is None or e['F'] <= nxt):
            e['Rw'] = e['F']; e['Rw_kind'] = 'F'
        elif nxt is not None:
            e['Rw'] = nxt; e['Rw_kind'] = 'next-peak'
        else:
            e['Rw'] = N - 1; e['Rw_kind'] = 'end'
        e['Ps'] = max(e['P'], di[D0])          # strategy-measurable peak
        e['clipped'] = e['Ps'] != e['P']
        e['name'] = ds[e['P']][:7]
        e['era'] = 'holdout' if ds[e['P']] < SEARCH[0] else 'search'
        e['bucket'] = '>25%' if e['depth'] <= -0.25 else '15-25%' if e['depth'] <= -MIN_DD else '8-15%'
    return eps

finish(PRIMARY); finish(SECOND)


def ep_table(eps, title):
    print(f"\n{title}")
    print(f"{'#':>2} {'peak':<10} {'trough':<10} {'depth':>7} {'P->T':>5} {'R(52w high)':<12} {'F(regain peak)':<15} {'window end':<10} {'T->end':>6} {'era':<7} note")
    for k, e in enumerate(eps, 1):
        Rd = ds[e['R']] if e['R'] is not None else 'open'
        Fd = ds[e['F']] if e['F'] is not None else 'never'
        print(f"{k:>2} {ds[e['P']]:<10} {ds[e['T']]:<10} {e['depth']*100:6.1f}% {e['T']-e['P']:>5} {Rd:<12} {Fd:<15} {ds[e['Rw']]:<10} {e['Rw']-e['T']:>6} {e['era']:<7} "
              f"{'peak predates rows, strategy measured from '+D0 if e['clipped'] else ''}{'(window = '+e['Rw_kind']+')' if e['Rw_kind']!='F' else ''}")

ep_table(PRIMARY, f"PRIMARY EPISODES: QQQ close declines >= {MIN_DD*100:.0f}% from the trailing-{RUN_N}-session high, {D0}..{ds[-1]} ({len(PRIMARY)} episodes)")
ep_table(SECOND, f"SECONDARY EPISODES: declines between {SEC_LO*100:.0f}% and {MIN_DD*100:.0f}% ({len(SECOND)} episodes)")

# ---------------------------------------------------------------- run all portfolios at all costs
RES = {}    # (cost, port) -> dict(rets, expo, nav)
orig = IS.ONE_WAY_SPREAD
for c in COSTS:
    IS.ONE_WAY_SPREAD = c
    for p in PORTS:
        rets, expo = run_path(rows, FNS[p])
        RES[(c, p)] = dict(rets=rets, expo=expo, nav=nav_of(rets))
IS.ONE_WAY_SPREAD = orig


def navat(c, p, i):
    """Portfolio NAV at the close of ds[i]."""
    return RES[(c, p)]['nav'][rix[ds[i]]]


def measure(e, c, p):
    """All per-episode measures for portfolio p at cost c."""
    nav, expo = RES[(c, p)]['nav'], RES[(c, p)]['expo']
    P, T, Rw = e['Ps'], e['T'], e['Rw']
    kP, kT, kR = rix[ds[P]], rix[ds[T]], rix[ds[Rw]]
    last = len(rows)
    k63, k126 = min(kT + 63, last), min(kT + 126, last)
    m = dict(
        pt=nav[kT] / nav[kP] - 1,
        tr=nav[kR] / nav[kT] - 1,
        t63=nav[k63] / nav[kT] - 1,
        t126=nav[k126] / nav[kT] - 1,
        pr=nav[kR] / nav[kP] - 1,
        exp_pt=statistics.mean(expo[kP:kT]) if kT > kP else float('nan'),
        exp_tr=statistics.mean(expo[kT:kR]) if kR > kT else float('nan'),
        exp_t63=statistics.mean(expo[kT:k63]) if k63 > kT else float('nan'),
    )
    pre = statistics.mean(expo[max(0, kP - PRE_N):kP]) if kP > 0 else statistics.mean(expo[kP:kP + PRE_N])
    m['pre'] = pre
    m['exp_at_T'] = expo[kT]
    rp = next((k for k in range(kT, min(kT + RUN_N, last)) if expo[k] >= REPART * pre - 1e-12), None)
    m['repart'] = None if rp is None else rp - kT
    H = max(nav[max(0, kP - RUN_N):kT + 1])
    m['own_high'] = H
    rg = next((k for k in range(kT, last + 1) if nav[k] >= H), None)
    m['regain'] = None if rg is None else rg - kT
    return m


def net(m, b):
    """Single 'did protection pay' number: (P->T advantage) + (T->R shortfall)."""
    return (m['pt'] - b['pt']) + (m['tr'] - b['tr'])


def dollars(m, b):
    return BOOK * ((1 + m['pr']) - (1 + b['pr']))


def fmt_s(x, w=5):
    return f"{'>252' if x is None else x:>{w}}"

M = {(c, p, id(e)): measure(e, c, p) for c in COSTS for p in PORTS for e in PRIMARY + SECOND}

# ---------------------------------------------------------------- per-episode detail, LIVE at 4bp
def detail(eps, c, title):
    print(f"\n{title}  (one-way cost {c*1e4:.0f}bp; returns in %, exposure = held risky weight)")
    print(f"{'ep':<8}{'--- peak->trough ---':^24}{'--- trough->window end ---':^30}{'-- T+63 --':^18}{'-- T+126 --':^18}{'expo P->T':>10}{'expo T->R':>10}{'pre':>6}{'re-part':>8}{'own-high regain':>16}{'net vs QQQ':>11}{'net vs BASE':>12}{'$ vs QQQ':>10}{'$ vs BASE':>10}")
    print(f"{'':<8}{'LIVE':>8}{'BASE':>8}{'QQQ':>8}{'LIVE':>8}{'BASE':>8}{'QQQ':>8}{'sess':>6}{'LIVE':>9}{'QQQ':>9}{'LIVE':>9}{'QQQ':>9}{'LIVE':>10}{'LIVE':>10}{'':>6}{'LIVE':>8}{'LIVE':>8}{'QQQ':>8}{'':>11}{'':>12}{'':>10}{'':>10}")
    for e in eps:
        L, B, Q = (M[(c, p, id(e))] for p in ('LIVE', 'BASE', 'QQQ'))
        print(f"{e['name']:<8}{L['pt']*100:8.1f}{B['pt']*100:8.1f}{Q['pt']*100:8.1f}{L['tr']*100:8.1f}{B['tr']*100:8.1f}{Q['tr']*100:8.1f}{e['Rw']-e['T']:>6}"
              f"{L['t63']*100:9.1f}{Q['t63']*100:9.1f}{L['t126']*100:9.1f}{Q['t126']*100:9.1f}{L['exp_pt']:10.2f}{L['exp_tr']:10.2f}{L['pre']:6.2f}{fmt_s(L['repart'],8)}"
              f"{fmt_s(L['regain'],8)}{fmt_s(Q['regain'],8)}{net(L,Q)*100:+11.1f}{net(L,B)*100:+12.1f}{dollars(L,Q):+10,.0f}{dollars(L,B):+10,.0f}")

detail(PRIMARY, 0.0004, "PER-EPISODE, PRIMARY SET")
detail(SECOND, 0.0004, "PER-EPISODE, SECONDARY SET (8-15%)")

# ---------------------------------------------------------------- every portfolio, per episode (4bp): P->T, T->R, net vs QQQ
print("\nALL PORTFOLIOS PER EPISODE at 4bp: peak->trough / trough->window-end / net-vs-QQQ (pp) ; re-participation sessions in []")
print(f"{'ep':<8}" + ''.join(f"{p:>26}" for p in PORTS))
for e in PRIMARY:
    line = f"{e['name']:<8}"
    Q = M[(0.0004, 'QQQ', id(e))]
    for p in PORTS:
        m = M[(0.0004, p, id(e))]
        line += f"{m['pt']*100:7.1f}/{m['tr']*100:6.1f}/{net(m,Q)*100:+6.1f}[{'>' if m['repart'] is None else m['repart']:>3}]"
    print(line)

# ---------------------------------------------------------------- leave-one-out attribution (4bp)
print("\nLEAVE-ONE-OUT ATTRIBUTION at 4bp: variant minus LIVE.  dTR = trough->window-end return (pp, + means removing the rule would have")
print("caught MORE recovery); dNet = change in net-vs-QQQ (pp); dRep = LIVE re-participation sessions minus variant's (+ means the rule delayed re-entry)")
print(f"{'ep':<8}" + ''.join(f"{p:>30}" for p in LOO) + f"{'BASE+VT':>30}{'BASE':>30}")
print(f"{'':<8}" + ''.join(f"{'dTR':>10}{'dNet':>10}{'dRep':>10}" for _ in LOO + ('BASE+VT', 'BASE')))
AGG_LOO = {p: dict(dtr=[], dnet=[], drep=[]) for p in LOO + ('BASE+VT', 'BASE')}
for e in PRIMARY:
    L = M[(0.0004, 'LIVE', id(e))]; Q = M[(0.0004, 'QQQ', id(e))]
    line = f"{e['name']:<8}"
    for p in LOO + ('BASE+VT', 'BASE'):
        m = M[(0.0004, p, id(e))]
        dtr = (m['tr'] - L['tr']) * 100; dnet = (net(m, Q) - net(L, Q)) * 100
        a, b = L['repart'], m['repart']
        drep = None if (a is None and b is None) else ((252 if a is None else a) - (252 if b is None else b))
        AGG_LOO[p]['dtr'].append(dtr); AGG_LOO[p]['dnet'].append(dnet); AGG_LOO[p]['drep'].append(0 if drep is None else drep)
        line += f"{dtr:+10.1f}{dnet:+10.1f}{fmt_s(drep,10) if drep is not None else '   both>252'}"
    print(line)
def loo_summary(c, eps):
    out = {}
    for p in LOO + ('BASE+VT', 'BASE'):
        dtr, dnet, drep, dpt, dd = [], [], [], [], []
        for e in eps:
            L = M[(c, 'LIVE', id(e))]; Q = M[(c, 'QQQ', id(e))]; m = M[(c, p, id(e))]
            dtr.append((m['tr'] - L['tr']) * 100); dnet.append((net(m, Q) - net(L, Q)) * 100); dpt.append((m['pt'] - L['pt']) * 100)
            a, b = L['repart'], m['repart']
            drep.append((252 if a is None else a) - (252 if b is None else b))
            dd.append(dollars(m, Q) - dollars(L, Q))
        out[p] = dict(dtr=dtr, dnet=dnet, drep=drep, dpt=dpt, dd=dd)
    return out

for c in COSTS:
    S = loo_summary(c, PRIMARY)
    for lab, f in (('mean', statistics.mean), ('median', statistics.median)):
        line = f"{lab+' '+str(int(c*1e4))+'bp':<8}"
        for p in LOO + ('BASE+VT', 'BASE'):
            a = S[p]
            line += f"{f(a['dtr']):+10.1f}{f(a['dnet']):+10.1f}{f(a['drep']):+10.1f}"
        print(line)
print("\nLEAVE-ONE-OUT SUMMARY BY COST (primary set, variant minus LIVE): dP->T = decline-phase return change (pp, - means the rule was")
print("protecting), dT->R = recovery change, dRep = sessions of re-entry delay attributable to the rule, d$ = compounded window $ vs QQQ change, summed")
print(f"{'cost':>5} {'variant':<11}{'sum dP->T':>10}{'sum dT->R':>10}{'sum dNet':>10}{'mean dRep':>10}{'median dRep':>12}{'sum d$':>12}")
for c in COSTS:
    S = loo_summary(c, PRIMARY)
    for p in LOO + ('BASE+VT', 'BASE'):
        a = S[p]
        print(f"{c*1e4:4.0f}bp {p:<11}{sum(a['dpt']):+10.1f}{sum(a['dtr']):+10.1f}{sum(a['dnet']):+10.1f}{statistics.mean(a['drep']):+10.1f}{statistics.median(a['drep']):+12.1f}{sum(a['dd']):+12,.0f}")

# ---------------------------------------------------------------- aggregates at 4/10/20bp
def agg_block(eps, title):
    print(f"\n{title}  ({len(eps)} episodes; net = (P->T advantage) + (T->R shortfall) in pp; $ = compounded P->R_win difference on ${BOOK:,.0f})")
    print(f"{'cost':>5} {'portfolio':<11}{'-- net vs QQQ --':^40}{'-- net vs BASE --':^40}{'$ vs QQQ':>12}{'$ vs BASE':>12}{'P->T mean':>10}{'T->R mean':>10}{'T+126 mean':>11}")
    print(f"{'':>5} {'':<11}{'sum':>8}{'mean':>8}{'median':>8}{'paid':>8}{'lost':>8}{'sum':>8}{'mean':>8}{'median':>8}{'paid':>8}{'lost':>8}{'sum':>12}{'sum':>12}{'':>10}{'':>10}{'':>11}")
    for c in COSTS:
        for p in PORTS:
            nq = [net(M[(c, p, id(e))], M[(c, 'QQQ', id(e))]) * 100 for e in eps]
            nb = [net(M[(c, p, id(e))], M[(c, 'BASE', id(e))]) * 100 for e in eps]
            dq = sum(dollars(M[(c, p, id(e))], M[(c, 'QQQ', id(e))]) for e in eps)
            db = sum(dollars(M[(c, p, id(e))], M[(c, 'BASE', id(e))]) for e in eps)
            pt = statistics.mean(M[(c, p, id(e))]['pt'] for e in eps) * 100
            tr = statistics.mean(M[(c, p, id(e))]['tr'] for e in eps) * 100
            t126 = statistics.mean(M[(c, p, id(e))]['t126'] for e in eps) * 100
            print(f"{c*1e4:4.0f}bp {p:<11}{sum(nq):8.1f}{statistics.mean(nq):8.1f}{statistics.median(nq):8.1f}{sum(1 for x in nq if x > 0):>8}{sum(1 for x in nq if x <= 0):>8}"
                  f"{sum(nb):8.1f}{statistics.mean(nb):8.1f}{statistics.median(nb):8.1f}{sum(1 for x in nb if x > 0):>8}{sum(1 for x in nb if x <= 0):>8}{dq:12,.0f}{db:12,.0f}{pt:10.1f}{tr:10.1f}{t126:11.1f}")
        print()

agg_block(PRIMARY, "AGGREGATE, PRIMARY SET (>=15%)")
for lab, sel in (("DEPTH 15-25%", [e for e in PRIMARY if e['bucket'] == '15-25%']), ("DEPTH >25%", [e for e in PRIMARY if e['bucket'] == '>25%']),
                 ("ERA holdout (peak < 2015-11)", [e for e in PRIMARY if e['era'] == 'holdout']), ("ERA search (peak >= 2015-11)", [e for e in PRIMARY if e['era'] == 'search']),
                 ("SECONDARY SET 8-15%", SECOND)):
    if sel:
        agg_block(sel, f"AGGREGATE, {lab}")

# LIVE net per episode across costs, compact
print("LIVE net-vs-QQQ / net-vs-BASE per episode across costs (pp)")
print(f"{'ep':<8}" + ''.join(f"{c*1e4:.0f}bp vsQQQ{'':>3}{c*1e4:.0f}bp vsBASE{'':>2}" for c in COSTS))
for e in PRIMARY:
    print(f"{e['name']:<8}" + ''.join(f"{net(M[(c,'LIVE',id(e))], M[(c,'QQQ',id(e))])*100:+12.1f}{net(M[(c,'LIVE',id(e))], M[(c,'BASE',id(e))])*100:+13.1f}" for c in COSTS))

# ---------------------------------------------------------------- paired block bootstrap, episode windows only
print(f"\nPAIRED CIRCULAR BLOCK BOOTSTRAP ({N_BOOT} resamples) RESTRICTED TO EPISODE WINDOWS [peak, window end) -- LIVE vs comparator")
win = []
for e in PRIMARY:
    win.extend(range(rix[ds[e['Ps']]], rix[ds[e['Rw']]]))
print(f"  {len(win)} sessions inside the {len(PRIMARY)} primary windows ({len(win)/len(rows)*100:.0f}% of all sessions)")
for c in COSTS:
    for cmp_ in ('BASE', 'BASE+VT', 'QQQ') + (LOO if c in (0.0004, 0.0020) else ()):
        a = [RES[(c, 'LIVE')]['rets'][k] for k in win]; b = [RES[(c, cmp_)]['rets'][k] for k in win]
        la, sa = stats(a); lb, sb = stats(b)
        print(f"  {c*1e4:4.0f}bp LIVE vs {cmp_:<8} point: log-ret {(la-lb)*100:+.2f}pp/yr, Sharpe {sa-sb:+.3f}", end='')
        for blk in (20, 60):
            l1, l2, pl, s1, s2, ps = boot(a, b, blk, seed=(int(c * 1e5) * 100 + blk + len(cmp_)) & 0xffff)
            print(f" | blk{blk}: logret [{l1*100:+.2f},{l2*100:+.2f}] P<=0 {pl:.3f}; Sharpe [{s1:+.3f},{s2:+.3f}] P<=0 {ps:.3f}", end='')
        print()
# recovery halves only (trough -> window end): the part the owner is worried about
print("  Recovery halves only [trough, window end):")
winr = []
for e in PRIMARY:
    winr.extend(range(rix[ds[e['T']]], rix[ds[e['Rw']]]))
for c in (0.0004, 0.0020):
    for cmp_ in ('BASE', 'QQQ') + LOO:
        a = [RES[(c, 'LIVE')]['rets'][k] for k in winr]; b = [RES[(c, cmp_)]['rets'][k] for k in winr]
        la, sa = stats(a); lb, sb = stats(b)
        print(f"  {c*1e4:4.0f}bp LIVE vs {cmp_:<8} point: log-ret {(la-lb)*100:+.2f}pp/yr, Sharpe {sa-sb:+.3f}", end='')
        for blk in (20, 60):
            l1, l2, pl, s1, s2, ps = boot(a, b, blk, seed=(int(c * 1e5) * 100 + blk + 7) & 0xffff)
            print(f" | blk{blk}: logret [{l1*100:+.2f},{l2*100:+.2f}] P<=0 {pl:.3f}; Sharpe [{s1:+.3f},{s2:+.3f}] P<=0 {ps:.3f}", end='')
        print()

# ---------------------------------------------------------------- real rows (weekly SPMO/TQQQ) confirmation
print("\nREAL WEEKLY ROWS (actual SPMO/TQQQ legs) -- episodes with peak >= 2015-11-06")
wd = [r['d0'] for r in rr]


def real_series(fn):
    prev = None; rets = []; expo = []
    for r in rr:
        w = fn(r)
        cost = VL.ONE_WAY_SPREAD * sum(abs(w[i] - (prev[i] if prev else 0)) for i in range(5))
        rets.append(sum(w[i] * r['legs'][i] for i in range(5)) - cost); prev = w; expo.append(sum(w[:4]))
    return rets, expo


def wk(i):
    """First weekly row at or after ds[i]."""
    d = ds[i]
    return next((k for k, x in enumerate(wd) if x >= d), len(rr))

REAL_EPS = [e for e in PRIMARY if ds[e['P']] >= wd[0]]
vorig = VL.ONE_WAY_SPREAD
for c in COSTS:
    VL.ONE_WAY_SPREAD = c
    RR = {}
    for p in PORTS:
        rets, expo = real_series(FNS_REAL[p])
        ev_ = RF.eval_real(rr, FNS_REAL[p]); nav = nav_of(rets)
        assert abs(nav[-1] ** (52 / len(rets)) - 1 - ev_['cagr']) < 1e-12
        RR[p] = dict(rets=rets, expo=expo, nav=nav)
    # QQQ benchmark on real rows: bench_qqq column if it is a weekly return series
    bq = [r['bench_qqq'] for r in rr]
    RR['QQQ-real'] = dict(rets=bq, expo=[1.0] * len(rr), nav=nav_of(bq))
    print(f"  cost {c*1e4:.0f}bp  (weekly rows; 'QQQ' here = 100% core leg = real SPMO, 'QQQ-real' = bench_qqq column)")
    print(f"  {'ep':<8}{'--- P->T ---':^30}{'--- T->R ---':^30}{'-- T+13w --':^20}{'-- T+26w --':^20}{'expo T->R':>10}{'net vs BASE':>12}{'net vs QQQ-real':>16}{'$ vs BASE':>10}")
    print(f"  {'':<8}{'LIVE':>10}{'BASE':>10}{'QQQreal':>10}{'LIVE':>10}{'BASE':>10}{'QQQreal':>10}{'LIVE':>10}{'QQQreal':>10}{'LIVE':>10}{'QQQreal':>10}{'LIVE':>10}{'':>12}{'':>16}{'':>10}")
    tot = dict(nb=0.0, nq=0.0, db=0.0)
    for e in REAL_EPS:
        kP, kT, kR = wk(e['Ps']), wk(e['T']), wk(e['Rw'])
        k13, k26 = min(kT + 13, len(rr)), min(kT + 26, len(rr))
        def mm(p):
            nav, expo = RR[p]['nav'], RR[p]['expo']
            return dict(pt=nav[kT] / nav[kP] - 1, tr=nav[kR] / nav[kT] - 1, t63=nav[k13] / nav[kT] - 1, t126=nav[k26] / nav[kT] - 1,
                        pr=nav[kR] / nav[kP] - 1, exp_tr=statistics.mean(expo[kT:kR]) if kR > kT else float('nan'))
        L, B, Q = mm('LIVE'), mm('BASE'), mm('QQQ-real')
        tot['nb'] += net(L, B) * 100; tot['nq'] += net(L, Q) * 100; tot['db'] += dollars(L, B)
        print(f"  {e['name']:<8}{L['pt']*100:10.1f}{B['pt']*100:10.1f}{Q['pt']*100:10.1f}{L['tr']*100:10.1f}{B['tr']*100:10.1f}{Q['tr']*100:10.1f}{L['t63']*100:10.1f}{Q['t63']*100:10.1f}{L['t126']*100:10.1f}{Q['t126']*100:10.1f}{L['exp_tr']:10.2f}{net(L,B)*100:+12.1f}{net(L,Q)*100:+16.1f}{dollars(L,B):+10,.0f}")
    print(f"  {'sum':<8}{'':>100}{tot['nb']:+12.1f}{tot['nq']:+16.1f}{tot['db']:+10,.0f}")
    if c == 0.0004:
        print("  leave-one-out on real rows, trough->R return delta vs LIVE (pp):")
        print(f"  {'ep':<8}" + ''.join(f"{p:>12}" for p in LOO + ('BASE+VT', 'BASE')))
        for e in REAL_EPS:
            kT, kR = wk(e['T']), wk(e['Rw'])
            lt = RR['LIVE']['nav'][kR] / RR['LIVE']['nav'][kT] - 1
            print(f"  {e['name']:<8}" + ''.join(f"{(RR[p]['nav'][kR]/RR[p]['nav'][kT]-1-lt)*100:+12.1f}" for p in LOO + ('BASE+VT', 'BASE')))
VL.ONE_WAY_SPREAD = vorig

# ---------------------------------------------------------------- deep dives: 2008-09 and 2020
def deep(e, every, turn_lo, turn_hi, fh):
    c = 0.0004
    L, B = RES[(c, 'LIVE')], RES[(c, 'BASE')]
    kP, kT, kR = rix[ds[e['Ps']]], rix[ds[e['T']]], rix[ds[e['Rw']]]
    hdr = f"{'date':<11}{'QQQ':>8}{'dd%':>7}{'st':>3}{'fast':>5}{'eff':>4}{'votes':>6}{'vol30':>7}{'volLv':>7}{'mult':>6}{'tgtLIVE':>8}{'heldLIVE':>9}{'heldBASE':>9}{'navLIVE':>9}{'navBASE':>9}{'navQQQ':>9}"
    def row(k, mark=''):
        r = rows[k]; i = di[r['d']]
        m = 1.0 if not r['vol_live'] else min(1.0, IS.VOL_TARGET_PA / r['vol_live'])
        t = FNS['LIVE'](r)
        return (f"{r['d']:<11}{vals[i]:8.2f}{(vals[i]/vals[e['P']]-1)*100:7.1f}{r['state']:>3}{fast[r['d']] or '-':>5}{r['eff']:>4}{extension_votes(r['eff'], r['gaps']):>6}"
                f"{r['vol']*100:7.1f}{r['vol_live']*100:7.1f}{m:6.2f}{sum(t[:4]):8.2f}{L['expo'][k]:9.2f}{B['expo'][k]:9.2f}"
                f"{L['nav'][k]/L['nav'][kP]:9.3f}{B['nav'][k]/B['nav'][kP]:9.3f}{RES[(c,'QQQ')]['nav'][k]/RES[(c,'QQQ')]['nav'][kP]:9.3f} {mark}")
    print(f"\nDEEP DIVE {e['name']}: peak {ds[e['P']]} trough {ds[e['T']]} window end {ds[e['Rw']]}  (NAVs rebased to the peak; full session-by-session path in {PATHS_LOG})")
    print(f"  every {every} sessions from peak to window end, then EVERY session {turn_lo}..+{turn_hi} around the trough")
    print(hdr)
    for k in range(kP, kR + 1, every):
        print(row(k, '<-- trough' if k == kT else ''))
    print("  --- the turn ---")
    print(hdr)
    for k in range(max(kP, kT - turn_lo), min(kR, kT + turn_hi) + 1):
        print(row(k, '<-- trough' if k == kT else ''))
    fh.write(f"\nDEEP DIVE {e['name']} full path, peak {ds[e['P']]} trough {ds[e['T']]} window end {ds[e['Rw']]}\n{hdr}\n")
    for k in range(max(0, kP - 10), kR + 1):
        fh.write(row(k, '<-- trough' if k == kT else ('<-- peak' if k == kP else '')) + '\n')

with open(PATHS_LOG, 'w') as fh:
    fh.write("recovery_study deep-dive paths (4bp). Columns: QQQ close, drawdown from episode peak, macro state, fast 20/100 state, effective state,\n"
             "extension votes, 30d vol, live vol max(10,30), VT multiplier, LIVE target risky weight, held risky weight LIVE / BASE, NAVs rebased to the peak.\n")
    for want in ('2007', '2020'):
        e = next(x for x in PRIMARY if x['name'].startswith(want))
        deep(e, every=10 if want == '2007' else 5, turn_lo=10, turn_hi=40, fh=fh)

print(f"\nDONE. Portfolios: {len(PORTS)}; costs: {len(COSTS)}; primary episodes {len(PRIMARY)}, secondary {len(SECOND)}. No parameter was searched; nothing applied.")
