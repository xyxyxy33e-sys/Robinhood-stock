"""Research line `d_pair_test` (2026-09-19): can two (or more) of the five D-exit rules be combined?

Owner question. An outside study on the real-ETF daily window (2015-10..2026-08) reported five single rules that each
improve on live when they send state D (QQQ below its 50d SMA, above its 200d, 50d > 200d; live row 100 % QLD) to cash
on flagged days:
  (1) breadth      QQEW/QQQ 60-session log-change in its trailing-252 bottom quintile  [the pre-registered breadth gate,
                   paper-track/breadth_tracker.py -- its functions are used verbatim, on data/QQEW_daily_ext.csv]
  (2) sma20>=sma60 QQQ 20d SMA at or above its 60d SMA
  (3) px>=sma100   QQQ close at or above its 100d SMA
  (4) gap200<2%    QQQ less than 2 % above its 200d SMA
  (5) volratio>1.5 QQQ 10d realised vol more than 1.5x its 30d realised vol
"Is it possible to combine two?"  And, as a scope extension pre-registered before any pair result was seen: "maybe D1,
then D2a, D2b, special cases that are worth going to cash" -- a TREE inside D, where D1 = default (live) and D2a, D2b, ...
are named special cases, any flagged day -> exit. A tree of k cases is the UNION of k flags.

PRE-REGISTERED GRID (fixed before any result): the 5 singles + all 10 pairs x {AND, OR} (20) + all unions of 3, 4 and 5
rules (10 + 5 + 1 = 16; the 2-unions are the OR pairs) = 41 candidates. Action: D -> 100 % cash on flagged days,
unflagged D stays live. Controls: constant-D rows (QLD fraction 0..100 % in 5 % steps, rest cash). No other rules, no
threshold tuning. Where the breadth signal is missing (QQEW starts 2006-05; the reading needs 312 sessions, so the first
value is 2007-07) D stays live: AND-combinations with breadth are False there, OR-combinations reduce to the other
member(s). Nothing is backfilled.

Harness: imports paper-track/d_substate_fresh.py (with DSF_STAGE=none, so only its bootstrap runs) and reuses its
machinery -- the 26-year QQQ-core proxy through the project harness (standing 22.18 % / 0.913 / -33.6 % asserted there),
the verified day-by-day mirror of monthly_returns.simulate for the real DAILY rows (29.66 % / 1.145 / -32.9 %), the data
symlink shim and the MR.TAIL['BOXX'] neutralisation, the search/holdout split (search 2015-11+, holdout 2000-07..2015-10),
evaluate_full / run_count / simulate_real / real_metrics, the signal calendar extended back to 1998, the SPY-core proxy,
block bootstrap and the leave-one-regime-out windows. No backtest loop is re-implemented here.

Sharpe is the repo's ZERO-RATE annualised Sharpe (drift_band_test.annual_stats) everywhere, as in the standing figures.
The outside study quoted an excess-of-cash Sharpe; for the real daily harness only, an excess-of-cash Sharpe (cash leg =
the synthetic BOXX = 3m T-bill index) is printed alongside as `xSh` so the two can be reconciled. Everything else --
weight table (A 50/50, B 75/25, C 100 % SPMO, D 100 % QLD, E 50/50 XLU/cash, F cash), fast 20/100 overlay, extension
trim, plain 30d vol target 20 %, 4 bp one-way cost, 5 % drift band -- is the live design as the harness carries it.

Research only. Nothing is applied. No repo data file, no protected file, no commit, no trade.

Run from the repo root:
    python3 paper-track/d_pair_test.py                     # grid + permutation + diagnostics (~15 min)
    DPT_STAGE=grid|perm|diag  DPT_NPERM=1000  DPT_PROCS=4
Intermediates go to the scratchpad (DPT_SCRATCH).
"""
import sys, os, math, json, random, csv, time, itertools

os.environ.setdefault('DSF_STAGE', 'none')          # import d_substate_fresh for its bootstrap only
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)
sys.path.insert(0, 'paper-track')
SCRATCH = os.environ.get('DPT_SCRATCH',
                         '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad')
os.makedirs(SCRATCH, exist_ok=True)
STAGE = os.environ.get('DPT_STAGE', 'all')
N_PERM = int(os.environ.get('DPT_NPERM', '1000'))
N_PROCS = int(os.environ.get('DPT_PROCS', '4'))
SEED = 20260919
T0 = time.time()

import d_substate_fresh as DSF
from d_substate_fresh import (rows, run, evaluate, vt, RF, W, BASE, D_ROWS, nD, QIX, RIX, SIG_Q, SIG_R, log,
                              evaluate_full, simulate_real, real_metrics, run_count, sliced_sharpe, tstat,
                              BASE_EV, REAL_EV, REAL_EXP, REAL_REB, LIVE_SER, RPX, RQQQ, RDAYS, RQD,
                              SEARCH, HOLDOUT, REGIMES, boot, bstats, annual_stats, live_fn, sma_series)
import improvement_search as IS
import breadth_tracker as BT
from long_history_backtest import load_px

CASH = DSF.ACTIONS['cash']
HALF = DSF.ACTIONS['half']

# ---------------------------------------------------------------- signals
def load_dc(path):
    out = {}
    for r in csv.DictReader(open(path)):
        try: out[r['d']] = float(r['c'])
        except ValueError: pass
    return out
QQEW = load_dc('data/QQEW_daily_ext.csv')

def breadth_pct(qqq, other=QQEW):
    """breadth_tracker's own functions: 60-session change of log(other/qqq), trailing-252 percentile."""
    common, x = BT.relative_strength_series(sorted(qqq), other, qqq)
    return dict(zip(common, BT.trailing_pct(x)))

RULES = [
    ('breadth',      'QQEW/QQQ 60-session log-change in trailing-252 bottom quintile (pct < 0.20) [pre-registered gate]'),
    ('sma20>=sma60', 'QQQ 20d SMA >= 60d SMA'),
    ('px>=sma100',   'QQQ close >= 100d SMA'),
    ('gap200<2%',    'QQQ less than 2 % above 200d SMA'),
    ('volratio>1.5', 'QQQ 10d realised vol > 1.5x 30d realised vol'),
]
RNAMES = [r[0] for r in RULES]
SHORT = {'breadth': 'BR', 'sma20>=sma60': 'S20', 'px>=sma100': 'P100', 'gap200<2%': 'G200', 'volratio>1.5': 'VR'}

def build_flags(dates, close, SIG, bp):
    sm20, sm60 = sma_series(close, 20), sma_series(close, 60)
    F = {}
    F['breadth'] = [bp.get(d) is not None and bp[d] < BT.GATE_PCT for d in dates]
    F['sma20>=sma60'] = [a is not None and b is not None and a >= b for a, b in zip(sm20, sm60)]
    F['px>=sma100'] = [g is not None and g >= 0.0 for g in SIG['gap100']]
    F['gap200<2%'] = [g is not None and g < 0.02 for g in SIG['gap200']]
    F['volratio>1.5'] = [v is not None and v > 1.5 for v in SIG['volratio']]
    F['_breadth_avail'] = [bp.get(d) is not None for d in dates]
    return F
def lagged(F, k=1):
    return {n: [False] * k + v[:-k] for n, v in F.items()}

BP_Q = breadth_pct(DSF._QQQ_FULL)
BP_R = breadth_pct(RQQQ)
FQ = build_flags(DSF._QD_EXT, DSF._QC_EXT, SIG_Q, BP_Q)
_, RC, _, _ = DSF.extend_back(RQQQ)
FR = build_flags(RQD, RC, SIG_R, BP_R)
# live-reading cross-check: breadth_tracker's own self-check value for 2026-09-04 (pct 0.867)
assert abs(BP_R['2026-09-04'] - 0.867) < 0.006, 'breadth reading does not reproduce breadth_tracker self-check'
log(f"\nbreadth reading reproduced: 2026-09-04 pct {BP_R['2026-09-04']:.3f} (breadth_tracker self-check 0.867); "
    f"first breadth value proxy {min(d for d, p in BP_Q.items() if p is not None)}, real {min(d for d, p in BP_R.items() if p is not None)}")

# D-day sequences
D_DATES = [rows[i]['d'] for i in D_ROWS]
RD_IDX = [k for k, d in enumerate(RDAYS[:-1]) if SIG_R['state'][RIX[d]] == 'D']
RD_DATES = [RDAYS[k] for k in RD_IDX]
def dseq(F, dates, ix):
    return {n: [F[n][ix[d]] for d in dates] for n in F}
FLQ = dseq(FQ, D_DATES, QIX); FLR = dseq(FR, RD_DATES, RIX)
DIDX = {d: j for j, d in enumerate(D_DATES)}; RDIDX = {d: j for j, d in enumerate(RD_DATES)}
S_MASK = [d >= SEARCH[0] for d in D_DATES]; H_MASK = [not m for m in S_MASK]
n_bmiss = sum(1 for a in FLQ['_breadth_avail'] if not a)
log(f"proxy D days {nD} (search {sum(S_MASK)}, holdout {sum(H_MASK)}); breadth missing on {n_bmiss} holdout D days "
    f"(all before {min(d for d, a in zip(D_DATES, FLQ['_breadth_avail']) if a)}) -> D stays live there. real daily D days {len(RD_DATES)}")

# ---------------------------------------------------------------- candidates (pre-registered)
CANDS = []
for n in RNAMES: CANDS.append(('single', (n,)))
for a, b in itertools.combinations(RNAMES, 2):
    CANDS.append(('and', (a, b))); CANDS.append(('or', (a, b)))
for k in (3, 4, 5):
    for c in itertools.combinations(RNAMES, k):
        CANDS.append(('or', c))
N_CAND = len(CANDS)
assert N_CAND == 41
def label(spec):
    op, names = spec
    if op == 'single': return names[0]
    if len(names) == 2: return f"{names[0]} {op.upper()} {names[1]}"
    return 'UNION(' + '|'.join(SHORT[n] for n in names) + ')'
def combine(spec, FL):
    op, names = spec
    seqs = [FL[n] for n in names]
    if op == 'single': return list(seqs[0])
    if op == 'and': return [all(t) for t in zip(*seqs)]
    return [any(t) for t in zip(*seqs)]
def members(spec): return spec[1]

# ---------------------------------------------------------------- evaluation helpers
def episodes(flags, idx):
    """runs of consecutive flagged rows (consecutive in the harness row index)."""
    eps = []; cur = None
    for f, i in zip(flags, idx):
        if f:
            if cur is not None and i == cur[1] + 1: cur[1] = i; cur[2] += 1
            else:
                if cur: eps.append(tuple(cur))
                cur = [i, i, 1]
    if cur: eps.append(tuple(cur))
    return eps

def proxy_eval(on, row=CASH, row_fn=None):
    """on: set of proxy decision dates -> row (or row_fn(d) -> row) before the vol target; else live."""
    def fn(r):
        if r['d'] in on: return vt(row if row_fn is None else row_fn(r['d']), r['vol'])
        return BASE[r['d']]
    return evaluate_full(fn)

CASH_R = {}
for i in range(1, len(RDAYS)):
    CASH_R[RDAYS[i]] = RPX['BOXX'][RDAYS[i]] / RPX['BOXX'][RDAYS[i - 1]] - 1
def xsharpe(out):
    x = [v - CASH_R[d] for d, _, v in out]
    m = sum(x) / len(x); v = (sum((a - m) ** 2 for a in x) / (len(x) - 1)) ** 0.5
    return m * 252 / (v * math.sqrt(252))
def real_eval(on, row=CASH, row_fn=None):
    ov = lambda d0: (row if row_fn is None else row_fn(d0)) if d0 in on else None
    out, exp, reb = simulate_real(RPX, RQQQ, RDAYS, ov)
    m, ser = real_metrics(out)
    return dict(m, exp=exp, reb=reb, xsh=xsharpe(out)), ser
_r0, _ = real_eval(set())
assert abs(_r0['sharpe'] - REAL_EV['sharpe']) < 1e-12
REAL_XSH = _r0['xsh']; REAL_SER = _

def dd_window(ser, dates):
    """(peak date, trough date, mdd, recovery date or None) of the max drawdown."""
    nav = 1.0; peak = 1.0; pk_i = 0; best = (0.0, 0, 0)
    navs = []
    for i, r in enumerate(ser):
        nav *= 1 + r; navs.append(nav)
        if nav > peak: peak = nav; pk_i = i
        dd = nav / peak - 1
        if dd < best[0]: best = (dd, pk_i, i)
    mdd, p, t = best
    rec = None
    for i in range(t, len(navs)):
        if navs[i] >= navs[p]: rec = dates[i]; break
    return dates[p], dates[t], mdd, rec

def fmt_ev(ev):
    return f"{ev['cagr']*100:6.2f}% /{ev['sharpe']:6.3f} /{ev['mdd']*100:6.1f}%"

JS_GRID = os.path.join(SCRATCH, 'dpt_grid.json')
JS_PERM = os.path.join(SCRATCH, 'dpt_perm.json')

# ================================================================= STAGE grid
def eval_candidate(spec, FLq=FLQ, FLr=FLR, row=CASH):
    fq = combine(spec, FLq); fr = combine(spec, FLr)
    onq = set(d for d, f in zip(D_DATES, fq) if f); onr = set(d for d, f in zip(RD_DATES, fr) if f)
    ev, ser = proxy_eval(onq, row); rev, rser = real_eval(onr, row)
    epq = episodes(fq, D_ROWS); epr = episodes(fr, RD_IDX)
    return dict(ev=ev, real=rev, n_on=len(onq), n_on_s=sum(1 for d in onq if d >= SEARCH[0]),
                n_on_h=sum(1 for d in onq if d < SEARCH[0]), n_ep=len(epq), n_ep_s=sum(1 for e in epq if rows[e[0]]['d'] >= SEARCH[0]),
                n_ep_h=sum(1 for e in epq if rows[e[0]]['d'] < SEARCH[0]), n_on_r=len(onr), n_ep_r=len(epr)), ser, rser, fq, fr

def overlap_table(FL, mask, names, title):
    idx = [j for j, m in enumerate(mask) if m]
    log(f"\n--- {title} (n = {len(idx)} D days): |a|, then Jaccard |a&b|/|a|b| (upper) and conditional P(col | row) = |a&b|/|row| (lower) ---")
    hdr = f"{'':<14}{'|a|':>5} " + "".join(f"{SHORT[n]:>8}" for n in names)
    log(hdr)
    for a in names:
        A = set(j for j in idx if FL[a][j]); cells = []
        for b in names:
            B = set(j for j in idx if FL[b][j])
            if a == b: cells.append(f"{'--':>8}")
            elif names.index(b) > names.index(a):
                u = len(A | B); cells.append(f"{(len(A & B) / u if u else float('nan')):>8.2f}")
            else:
                cells.append(f"{(len(A & B) / len(A) if A else float('nan')):>8.2f}")
        log(f"{a:<14}{len(A):>5} " + "".join(cells))
    return idx

if STAGE in ('all', 'grid'):
    log(f"\n{'='*118}\nRESEARCH LINE d_pair_test -- pre-registered grid of {N_CAND} candidates (5 singles, 10 x AND, 10 x OR, "
        f"16 unions of 3-5) + constant-D controls\n{'='*118}")
    log("Sharpe = zero-rate (repo convention) everywhere; real-daily `xSh` = excess-of-cash Sharpe for reconciliation only.")
    for n, desc in RULES: log(f"  {n:<14} {desc}")

    # ---- overlap matrices
    log(f"\n{'='*118}\nOVERLAP of the five singles' flag sets, counted on D days\n{'='*118}")
    overlap_table(FLQ, [True] * nD, RNAMES, 'proxy, full 2000-07..2026-08')
    overlap_table(FLQ, S_MASK, RNAMES, 'proxy, search era 2015-11+')
    overlap_table(FLQ, [h and a for h, a in zip(H_MASK, FLQ['_breadth_avail'])], RNAMES, 'proxy, holdout 2007-07..2015-10 (breadth available)')
    overlap_table(FLR, [True] * len(RD_DATES), RNAMES, 'real daily 2015-11..2026-09')
    log("\n--- pair detail on proxy D days (full): |a|, |b|, |a&b|, |a|b|, Jaccard, P(b|a), P(a|b); search-era Jaccard; real-daily Jaccard ---")
    PAIRS = {}
    for a, b in itertools.combinations(RNAMES, 2):
        A = set(j for j in range(nD) if FLQ[a][j]); B = set(j for j in range(nD) if FLQ[b][j])
        As = set(j for j in A if S_MASK[j]); Bs = set(j for j in B if S_MASK[j])
        Ar = set(j for j in range(len(RD_DATES)) if FLR[a][j]); Br = set(j for j in range(len(RD_DATES)) if FLR[b][j])
        jf = len(A & B) / len(A | B); js = len(As & Bs) / max(1, len(As | Bs)); jr = len(Ar & Br) / max(1, len(Ar | Br))
        PAIRS[(a, b)] = dict(a=len(A), b=len(B), ab=len(A & B), aub=len(A | B), j=jf, pba=len(A & B) / len(A), pab=len(A & B) / len(B), js=js, jr=jr)
        log(f"  {a:<14}{b:<14} {len(A):>4}{len(B):>5}{len(A & B):>6}{len(A | B):>6}{jf:>7.2f}{len(A & B)/len(A):>7.2f}{len(A & B)/len(B):>7.2f} | {js:>6.2f} | {jr:>6.2f}")

    # ---- constant-D controls
    log(f"\n{'='*118}\nCONSTANT-D CONTROLS: D -> f x QLD + (1-f) cash on every D day, f in 5 % steps (f = 100 % is live)\n{'='*118}")
    log(f"{'f':>5} | proxy {'CAGR':>7}{'Sharpe':>7}{'MaxDD':>7}{'exp':>6}{'reb':>6}{'S Sh':>7}{'H Sh':>7} | real {'CAGR':>7}{'Sharpe':>7}{'xSh':>7}{'MaxDD':>7}{'exp':>6}{'reb':>6}")
    CTRL = []
    allq = set(D_DATES); allr = set(RD_DATES)
    for f in range(0, 101, 5):
        row = (0.0, 0.0, f / 100.0, 0.0, 1 - f / 100.0)
        ev, _ = proxy_eval(allq, row); rev, _ = real_eval(allr, row)
        CTRL.append(dict(f=f, ev=ev, real=rev))
        log(f"{f:>4}% | {ev['cagr']*100:>6.2f}%{ev['sharpe']:>7.3f}{ev['mdd']*100:>6.1f}%{ev['risky']*100:>5.1f}%{ev['reb']:>6.1f}{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f} | "
            f"{rev['cagr']*100:>6.2f}%{rev['sharpe']:>7.3f}{rev['xsh']:>7.3f}{rev['mdd']*100:>6.1f}%{rev['exp']*100:>5.1f}%{rev['reb']:>6.1f}")
    assert abs(CTRL[-1]['ev']['sharpe'] - BASE_EV['sharpe']) < 1e-9 and abs(CTRL[-1]['real']['sharpe'] - REAL_EV['sharpe']) < 1e-9
    def match_ctrl(exp, key):
        return min(CTRL, key=lambda c: abs((c['ev']['risky'] if key == 'ev' else c['real']['exp']) - exp))

    # ---- grid
    log(f"\n{'='*118}\nGRID: every candidate, D -> cash on flagged days (proxy full / search / holdout; real daily)\n{'='*118}")
    log(f"LIVE proxy {fmt_ev(BASE_EV)} exp {BASE_EV['risky']*100:.1f}% reb {BASE_EV['reb']:.1f}/yr  S {BASE_EV['s_sharpe']:.3f} H {BASE_EV['h_sharpe']:.3f} | "
        f"real {fmt_ev(REAL_EV)} xSh {REAL_XSH:.3f} exp {REAL_EXP*100:.1f}% reb {REAL_REB:.1f}/yr")
    hdr = (f"{'#':>3} {'candidate':<40}{'nOn':>5}{'ep':>4}{'CAGR':>7}{'Sharpe':>7}{'MaxDD':>7}{'exp':>6}{'reb':>5}"
           f"{'S Sh':>7}{'H Sh':>7}{'dS_S':>7}{'dS_H':>7}{'dS_F':>7} | {'rCAGR':>7}{'rSh':>6}{'xSh':>6}{'rDD':>7}{'rexp':>5}{'rreb':>5}{'rnOn':>5}{'rep':>4}")
    log(hdr)
    RES = []; SER = {}; RSER = {}; FLAG = {}
    for k, spec in enumerate(CANDS):
        rec, ser, rser, fq, fr = eval_candidate(spec)
        ev, rev = rec['ev'], rec['real']
        rec.update(idx=k, label=label(spec), spec=[spec[0], list(spec[1])],
                   dS_S=ev['s_sharpe'] - BASE_EV['s_sharpe'], dS_H=ev['h_sharpe'] - BASE_EV['h_sharpe'], dS_F=ev['sharpe'] - BASE_EV['sharpe'])
        RES.append(rec); SER[k] = ser; RSER[k] = rser; FLAG[k] = (fq, fr)
        log(f"{k:>3} {rec['label']:<40}{rec['n_on']:>5}{rec['n_ep']:>4}{ev['cagr']*100:>6.2f}%{ev['sharpe']:>7.3f}{ev['mdd']*100:>6.1f}%{ev['risky']*100:>5.1f}%"
            f"{ev['reb']:>5.1f}{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f}{rec['dS_S']:>+7.3f}{rec['dS_H']:>+7.3f}{rec['dS_F']:>+7.3f} | "
            f"{rev['cagr']*100:>6.2f}%{rev['sharpe']:>6.3f}{rev['xsh']:>6.3f}{rev['mdd']*100:>6.1f}%{rev['exp']*100:>4.0f}%{rev['reb']:>5.1f}{rec['n_on_r']:>5}{rec['n_ep_r']:>4}")
    log("  nOn/ep = flagged proxy D days / flagged episodes (full); rnOn/rep = same on the real daily rows. dS_* = Sharpe minus live.")

    # ---- deltas vs live, vs matched constant-D control, vs better single
    log(f"\n{'='*118}\nDELTAS: Sharpe vs (i) live, (ii) constant-D control matched to the nearest 5 % by average exposure, "
        f"(iii) the BETTER of the member singles (per era: the higher of the members' Sharpes in that era)\n{'='*118}")
    log(f"{'#':>3} {'candidate':<40}{'ctrl f':>7}{'vLive S':>8}{'vLive H':>8}{'vLive F':>8}{'vCtl S':>8}{'vCtl H':>8}{'vCtl F':>8}{'vBest S':>8}{'vBest H':>8}{'vBest F':>8}"
        f" | {'rctl f':>6}{'rvLive':>7}{'rvCtl':>7}{'rvBest':>7}  adds?")
    SINGLE = {n: RES[k] for k, spec in enumerate(CANDS) if spec[0] == 'single' for n in spec[1]}
    for rec in RES:
        ev, rev = rec['ev'], rec['real']
        c = match_ctrl(ev['risky'], 'ev'); cr = match_ctrl(rev['exp'], 'real')
        rec['ctrl_f'] = c['f']; rec['rctrl_f'] = cr['f']
        rec['vC_S'] = ev['s_sharpe'] - c['ev']['s_sharpe']; rec['vC_H'] = ev['h_sharpe'] - c['ev']['h_sharpe']; rec['vC_F'] = ev['sharpe'] - c['ev']['sharpe']
        rec['rvL'] = rev['sharpe'] - REAL_EV['sharpe']; rec['rvC'] = rev['sharpe'] - cr['real']['sharpe']
        mem = rec['spec'][1]
        if len(mem) > 1:
            bs = max(SINGLE[n]['ev']['s_sharpe'] for n in mem); bh = max(SINGLE[n]['ev']['h_sharpe'] for n in mem)
            bf = max(SINGLE[n]['ev']['sharpe'] for n in mem); br = max(SINGLE[n]['real']['sharpe'] for n in mem)
            rec['vB_S'] = ev['s_sharpe'] - bs; rec['vB_H'] = ev['h_sharpe'] - bh; rec['vB_F'] = ev['sharpe'] - bf; rec['rvB'] = rev['sharpe'] - br
            rec['best_single'] = max(mem, key=lambda n: SINGLE[n]['ev']['sharpe'])
            rec['best_single_real'] = max(mem, key=lambda n: SINGLE[n]['real']['sharpe'])
            rec['adds'] = rec['vB_S'] > 0 and rec['vB_H'] > 0
            vb = f"{rec['vB_S']:>+8.3f}{rec['vB_H']:>+8.3f}{rec['vB_F']:>+8.3f} | {cr['f']:>5}%{rec['rvL']:>+7.3f}{rec['rvC']:>+7.3f}{rec['rvB']:>+7.3f}  {'ADDS' if rec['adds'] else 'no'}"
        else:
            rec['adds'] = None
            vb = f"{'':>24} | {cr['f']:>5}%{rec['rvL']:>+7.3f}{rec['rvC']:>+7.3f}{'':>7}"
        log(f"{rec['idx']:>3} {rec['label']:<40}{c['f']:>6}%{rec['dS_S']:>+8.3f}{rec['dS_H']:>+8.3f}{rec['dS_F']:>+8.3f}{rec['vC_S']:>+8.3f}{rec['vC_H']:>+8.3f}{rec['vC_F']:>+8.3f}" + vb)
    adders = [r for r in RES if r['adds']]
    log(f"\n  combinations that beat the better of their own singles in BOTH proxy eras: {len(adders)} of {N_CAND - 5}: "
        + (", ".join(f"#{r['idx']} {r['label']} (S {r['vB_S']:+.3f}, H {r['vB_H']:+.3f}, real {r['rvB']:+.3f})" for r in adders) if adders else "(none)"))
    # ---- picks for the deep stage (by full-period proxy Sharpe within class; real daily reported too)
    best_single = max((r for r in RES if len(r['spec'][1]) == 1), key=lambda r: r['ev']['sharpe'])
    best_pair = max((r for r in RES if len(r['spec'][1]) == 2), key=lambda r: r['ev']['sharpe'])
    best_union = max((r for r in RES if r['spec'][0] == 'or' and len(r['spec'][1]) >= 3), key=lambda r: r['ev']['sharpe'])
    full_union = [r for r in RES if len(r['spec'][1]) == 5][0]
    best_pair_real = max((r for r in RES if len(r['spec'][1]) == 2), key=lambda r: r['real']['sharpe'])
    best_single_real = max((r for r in RES if len(r['spec'][1]) == 1), key=lambda r: r['real']['sharpe'])
    best_both = max(RES, key=lambda r: min(r['dS_S'], r['dS_H']))
    log(f"\n  best single (proxy full Sharpe): #{best_single['idx']} {best_single['label']}; best pair: #{best_pair['idx']} {best_pair['label']}; "
        f"best union(3-5): #{best_union['idx']} {best_union['label']}; full 5-union: #{full_union['idx']}")
    log(f"  by REAL daily Sharpe: best single #{best_single_real['idx']} {best_single_real['label']} ({best_single_real['real']['sharpe']:.3f}), "
        f"best pair #{best_pair_real['idx']} {best_pair_real['label']} ({best_pair_real['real']['sharpe']:.3f}); best both-era min(dS_S,dS_H): #{best_both['idx']} {best_both['label']}")
    json.dump(dict(res=RES, ctrl=CTRL, pairs={f"{a}|{b}": v for (a, b), v in PAIRS.items()},
                   picks=dict(single=best_single['idx'], pair=best_pair['idx'], union=best_union['idx'], full=full_union['idx'],
                              pair_real=best_pair_real['idx'], single_real=best_single_real['idx'], both=best_both['idx'])), open(JS_GRID, 'w'))
    log(f"\n[grid saved: {JS_GRID}]  elapsed {time.time()-T0:.0f}s")

# ================================================================= STAGE perm
LIVE_F_SH = bstats(LIVE_SER)[1]
LIVE_S_SL = sliced_sharpe(LIVE_SER, *SEARCH); LIVE_H_SL = sliced_sharpe(LIVE_SER, *HOLDOUT)
SINGLE_IDX = {n: k for k, spec in enumerate(CANDS) if spec[0] == 'single' for n in spec[1]}
def _stats_for(FL):
    """(dF, dS, dH) vs live for every candidate under flag sequences FL (over D_ROWS)."""
    out = []
    for spec in CANDS:
        fl = combine(spec, FL); on = set(d for d, f in zip(D_DATES, fl) if f)
        ser, _ = run(rows, lambda r: vt(CASH, r['vol']) if r['d'] in on else BASE[r['d']])
        out.append((bstats(ser)[1] - LIVE_F_SH, sliced_sharpe(ser, *SEARCH) - LIVE_S_SL, sliced_sharpe(ser, *HOLDOUT) - LIVE_H_SL))
    return out
def _summ(st):
    """max over the grid of: dF; min(dS,dH); combo-minus-best-member dF; combo-minus-best-member both-era."""
    bF = max(s[0] for s in st); bB = max(min(s[1], s[2]) for s in st)
    gF = -9.0; gB = -9.0
    for k, spec in enumerate(CANDS):
        mem = spec[1]
        if len(mem) < 2: continue
        mF = max(st[SINGLE_IDX[n]][0] for n in mem); mS = max(st[SINGLE_IDX[n]][1] for n in mem); mH = max(st[SINGLE_IDX[n]][2] for n in mem)
        gF = max(gF, st[k][0] - mF); gB = max(gB, min(st[k][1] - mS, st[k][2] - mH))
    return bF, bB, gF, gB
def _perm_worker(args):
    s, = args
    FL = {n: [FLQ[n][(j + s) % nD] for j in range(nD)] for n in FLQ}
    return _summ(_stats_for(FL))

if STAGE in ('all', 'perm'):
    G = json.load(open(JS_GRID)); RES = G['res']
    log(f"\n{'='*118}\nPERMUTATION: whole-grid max statistic over all {N_CAND} candidates, {N_PERM} common circular shifts of the "
        f"D-day flag sequences (all five rules shifted together, so overlap between rules is preserved)\n{'='*118}")
    rng = random.Random(SEED); shifts = [rng.randrange(1, nD) for _ in range(N_PERM)]
    from multiprocessing import Pool
    t1 = time.time()
    with Pool(N_PROCS) as pool:
        outs = pool.map(_perm_worker, [(s,) for s in shifts], chunksize=2)
    log(f"  {N_PERM} permutations in {time.time()-t1:.0f}s")
    real = _stats_for(FLQ)
    for k, (dF, dS, dH) in enumerate(real):
        assert abs(dF - RES[k]['dS_F']) < 1e-9
    rF, rB, rgF, rgB = _summ(real)
    q = lambda v, p: v[min(len(v) - 1, int(len(v) * p))]
    names = ['best-of-41 full-period Sharpe gain vs live', 'best-of-41 both-era gain min(dS_S, dS_H) vs live',
             'best-of-36 combo gain over its best member single (full)', 'best-of-36 combo gain over its best member (both-era min)']
    reals = [rF, rB, rgF, rgB]
    def _gain(k, both):
        mem = CANDS[k][1]
        if len(mem) < 2: return -9.0
        if not both: return real[k][0] - max(real[SINGLE_IDX[n]][0] for n in mem)
        return min(real[k][1] - max(real[SINGLE_IDX[n]][1] for n in mem), real[k][2] - max(real[SINGLE_IDX[n]][2] for n in mem))
    bests = [max(range(N_CAND), key=lambda k: real[k][0]), max(range(N_CAND), key=lambda k: min(real[k][1], real[k][2])),
             max(range(N_CAND), key=lambda k: _gain(k, False)), max(range(N_CAND), key=lambda k: _gain(k, True))]
    P = dict(shifts=shifts)
    for i, nm in enumerate(names):
        null = sorted(o[i] for o in outs); p = sum(1 for x in null if x >= reals[i]) / N_PERM
        P[f'null{i}'] = null; P[f'real{i}'] = reals[i]; P[f'p{i}'] = p
        log(f"  {nm}: null median {q(null,0.5):+.3f}  95th {q(null,0.95):+.3f}  max {null[-1]:+.3f} | best real {reals[i]:+.3f} -> p = {p:.3f}")
    log("  best real candidate per statistic: " + "; ".join(f"stat {i+1} #{b} {RES[b]['label']}" for i, b in enumerate(bests)))
    per_p = [sum(1 for o in outs if o[0] >= real[k][0]) / N_PERM for k in range(N_CAND)]
    P['per_cand_p'] = per_p
    log("  per-candidate p on the best-of-41 full-period null: " + ", ".join(f"#{k} {per_p[k]:.2f}" for k in range(N_CAND)))
    json.dump(P, open(JS_PERM, 'w'))
    log(f"[perm saved: {JS_PERM}]  elapsed {time.time()-T0:.0f}s")

# ================================================================= STAGE diag
def spy_setup():
    SP_ROWS, SP_D, SIG_S = DSF.build_spy_rows()
    SPY = DSF.SPY; RSP = load_dc('data/RSP_daily.csv')
    v = [SPY[d] for d in SP_D]
    sp_px = {d: SPY[d] for d in SP_D}
    bp = breadth_pct(sp_px, other=RSP)          # SPY analogue of breadth: RSP/SPY 60-session change, bottom quintile
    F = build_flags(SP_D, v, SIG_S, bp)
    SPIX = {d: i for i, d in enumerate(SP_D)}
    D_IDX = [i for i, r in enumerate(SP_ROWS) if r['state'] == 'D']
    dd = [SP_ROWS[i]['d'] for i in D_IDX]
    FL = {n: [F[n][SPIX[d]] for d in dd] for n in F}
    SPB = {r['d']: live_fn(r) for r in SP_ROWS}
    base = evaluate(SP_ROWS, live_fn)
    def ev_of(spec):
        fl = combine(spec, FL); on = set(d for d, f in zip(dd, fl) if f)
        e = evaluate(SP_ROWS, lambda r: vt(CASH, r['vol']) if r['d'] in on else SPB[r['d']])
        return e, len(on)
    return base, ev_of, len(SP_ROWS), len(D_IDX), sum(1 for a in FL['_breadth_avail'] if not a)

def deep(rec, ref_label, ref_ser, ref_rser, extra_refs=()):
    """bootstrap / LORO / lag / 20bp for one candidate against a reference series (proxy + real daily)."""
    k = rec['idx']; spec = (rec['spec'][0], tuple(rec['spec'][1]))
    ser, rser = SER[k], RSER[k]
    log(f"\n{'-'*118}\nDEEP #{k}: {rec['label']}   proxy {fmt_ev(rec['ev'])} S {rec['ev']['s_sharpe']:.3f} H {rec['ev']['h_sharpe']:.3f} exp {rec['ev']['risky']*100:.1f}% "
        f"reb {rec['ev']['reb']:.1f}/yr | real {fmt_ev(rec['real'])} xSh {rec['real']['xsh']:.3f} exp {rec['real']['exp']*100:.0f}% reb {rec['real']['reb']:.0f}/yr")
    log(f"  (a) circular block bootstrap (2000 draws) of the Sharpe / log-return difference:")
    for lab, a, b in ((f'proxy vs {ref_label}', ser, ref_ser), (f'real daily vs {ref_label}', rser, ref_rser)) + tuple(extra_refs):
        for blk in (20, 60):
            l1, l2, pl, s1, s2, ps = boot(a, b, blk, seed=(k * 7919 + blk + len(lab)) & 0xffff)
            log(f"      {lab:<40} block {blk:>2}d: Sharpe 95% CI [{s1:+.3f}, {s2:+.3f}] P(<=0)={ps:.3f}   log-return [{l1*100:+.2f}, {l2*100:+.2f}] pp/yr P(<=0)={pl:.3f}")
    log(f"  (b) leave-one-major-regime-out, proxy (Sharpe difference vs {ref_label} / vs live, that window removed):")
    for rlab, a0, b0 in REGIMES:
        keep = [i for i, r in enumerate(rows) if not (a0 <= r['d'] <= b0)]
        sa = bstats([ser[i] for i in keep])[1]; sb = bstats([ref_ser[i] for i in keep])[1]; sl = bstats([LIVE_SER[i] for i in keep])[1]
        log(f"      drop {rlab:<26} vs {ref_label}: {sa-sb:+.3f}" + (f"   vs live: {sa-sl:+.3f}" if ref_label != 'live' else ""))
    # (c) one-extra-session lag
    recL, _, _, _, _ = eval_candidate(spec, FLQ_LAG, FLR_LAG)
    log(f"  (c) one-extra-session lag (flag from the previous close): proxy {fmt_ev(recL['ev'])} S {recL['ev']['s_sharpe']:.3f} H {recL['ev']['h_sharpe']:.3f} "
        f"(dS vs live S {recL['ev']['s_sharpe']-BASE_EV['s_sharpe']:+.3f} H {recL['ev']['h_sharpe']-BASE_EV['h_sharpe']:+.3f} F {recL['ev']['sharpe']-BASE_EV['sharpe']:+.3f}) | "
        f"real {fmt_ev(recL['real'])} ({recL['real']['sharpe']-REAL_EV['sharpe']:+.3f} vs live)")
    # (d) 20 bp one-way cost
    DSF.ONE_WAY_SPREAD = IS.ONE_WAY_SPREAD = 0.002; DSF.MR.ONE_WAY = 0.002
    try:
        live20, _ = proxy_eval(set()); rlive20, _ = real_eval(set())
        rec20, _, _, _, _ = eval_candidate(spec)
        ref20 = None
        if ref_label != 'live':
            rr_ = REF_REC.get(ref_label)
            if rr_ is not None: ref20, _, _, _, _ = eval_candidate((rr_['spec'][0], tuple(rr_['spec'][1])))
    finally:
        DSF.ONE_WAY_SPREAD = IS.ONE_WAY_SPREAD = 0.0004; DSF.MR.ONE_WAY = 0.0004
    log(f"  (d) 20 bp one-way cost: live proxy {fmt_ev(live20)} S {live20['s_sharpe']:.3f} H {live20['h_sharpe']:.3f}; candidate {fmt_ev(rec20['ev'])} "
        f"S {rec20['ev']['s_sharpe']:.3f} H {rec20['ev']['h_sharpe']:.3f} (vs live S {rec20['ev']['s_sharpe']-live20['s_sharpe']:+.3f} H {rec20['ev']['h_sharpe']-live20['h_sharpe']:+.3f} "
        f"F {rec20['ev']['sharpe']-live20['sharpe']:+.3f}) | real live {fmt_ev(rlive20)} candidate {fmt_ev(rec20['real'])} ({rec20['real']['sharpe']-rlive20['sharpe']:+.3f})"
        + (f" | vs {ref_label} at 20 bp: S {rec20['ev']['s_sharpe']-ref20['ev']['s_sharpe']:+.3f} H {rec20['ev']['h_sharpe']-ref20['ev']['h_sharpe']:+.3f} "
           f"F {rec20['ev']['sharpe']-ref20['ev']['sharpe']:+.3f} real {rec20['real']['sharpe']-ref20['real']['sharpe']:+.3f}" if ref20 else ""))
    # (e) SPY analogue
    e, n_on = SPY_EV(spec)
    log(f"  (e) SPY-core proxy, same rule(s) on SPY (breadth analogue = RSP/SPY): {fmt_ev(e)} S {e['s_sharpe']:.3f} H {e['h_sharpe']:.3f}  "
        f"dS vs SPY-live S {e['s_sharpe']-SPY_BASE['s_sharpe']:+.3f} H {e['h_sharpe']-SPY_BASE['h_sharpe']:+.3f} F {e['sharpe']-SPY_BASE['sharpe']:+.3f}  nOn {n_on}")

def episode_table(rec, harness='proxy', top=6):
    """flagged episodes with the log-return difference vs live accumulated on their days."""
    k = rec['idx']; fq, fr = FLAG[k]
    if harness == 'proxy':
        eps = episodes(fq, D_ROWS); ser, base, dates = SER[k], LIVE_SER, [r['d'] for r in rows]
    else:
        eps = episodes(fr, RD_IDX); ser, base, dates = RSER[k], REAL_SER, RDAYS[:-1]
    out = []
    for a, b, n in eps:
        g = sum(math.log1p(ser[i]) - math.log1p(base[i]) for i in range(a, b + 1))
        out.append((dates[a], dates[b], n, g))
    out.sort(key=lambda e: -e[3])
    return out, sum(e[3] for e in out)

if STAGE in ('all', 'diag'):
    G = json.load(open(JS_GRID)); P = json.load(open(JS_PERM)); RES = G['res']; CTRL = G['ctrl']; PK = G['picks']
    log(f"\n{'='*118}\nDIAGNOSTICS\n{'='*118}")
    # recompute series for all candidates (cheap) so the deep stage can run standalone
    SER = {}; RSER = {}; FLAG = {}
    for k, spec in enumerate(CANDS):
        rec, ser, rser, fq, fr = eval_candidate(spec); SER[k] = ser; RSER[k] = rser; FLAG[k] = (fq, fr)
        assert abs(rec['ev']['sharpe'] - RES[k]['ev']['sharpe']) < 1e-9
    FLQ_LAG = dseq(lagged(FQ), D_DATES, QIX); FLR_LAG = dseq(lagged(FR), RD_DATES, RIX)
    SPY_BASE, SPY_EV, n_sp, n_spd, n_spmiss = spy_setup()
    log(f"SPY-core proxy live: {fmt_ev(SPY_BASE)} S {SPY_BASE['s_sharpe']:.3f} H {SPY_BASE['h_sharpe']:.3f} ({n_sp} rows, {n_spd} D days, "
        f"RSP/SPY breadth missing on {n_spmiss} D days -> live there)")
    log("  the five singles on SPY:")
    for n in RNAMES:
        e, n_on = SPY_EV(('single', (n,)))
        log(f"    {n:<14} {fmt_ev(e)}  dS S {e['s_sharpe']-SPY_BASE['s_sharpe']:+.3f} H {e['h_sharpe']-SPY_BASE['h_sharpe']:+.3f} F {e['sharpe']-SPY_BASE['sharpe']:+.3f}  nOn {n_on}")
    REF_REC = {r['label']: r for r in RES}
    CTRL_SER = {}
    def ctrl_series(f):
        if f not in CTRL_SER:
            row = (0.0, 0.0, f / 100.0, 0.0, 1 - f / 100.0)
            _, s = proxy_eval(set(D_DATES), row); _, rs = real_eval(set(RD_DATES), row); CTRL_SER[f] = (s, rs)
        return CTRL_SER[f]

    # ---- permutation recap
    q = lambda v, p: v[min(len(v) - 1, int(len(v) * p))]
    log(f"\nPERMUTATION recap ({len(P['shifts'])} shifts): best-of-41 full gain null median {q(P['null0'],0.5):+.3f} 95th {q(P['null0'],0.95):+.3f}, "
        f"best real {P['real0']:+.3f} p {P['p0']:.3f}; both-era null 95th {q(P['null1'],0.95):+.3f}, best real {P['real1']:+.3f} p {P['p1']:.3f}; "
        f"combo-over-best-member null 95th {q(P['null2'],0.95):+.3f}, best real {P['real2']:+.3f} p {P['p2']:.3f}; both-era {q(P['null3'],0.95):+.3f} / {P['real3']:+.3f} p {P['p3']:.3f}")

    # ---- drawdown episodes of the five singles
    log(f"\n{'='*118}\nDRAWDOWN EPISODES: where does each single's MaxDD improvement come from?\n{'='*118}")
    for hn, ser0, dates0 in (('proxy', LIVE_SER, [r['d'] for r in rows]), ('real daily', REAL_SER, RDAYS[:-1])):
        p0, t0, m0, r0 = dd_window(ser0, dates0)
        log(f"  {hn} LIVE max drawdown {m0*100:.1f}%: peak {p0} -> trough {t0}, recovered {r0}")
        for n in RNAMES:
            rec = RES[SINGLE_IDX[n]]; k = rec['idx']
            ser = SER[k] if hn == 'proxy' else RSER[k]
            p1, t1, m1, r1 = dd_window(ser, dates0)
            # candidate's drawdown over the LIVE window
            nav = 1.0; pk = 1.0; dd_live_win = 0.0
            for d, x in zip(dates0, ser):
                if p0 <= d <= t0:
                    nav *= 1 + x; pk = max(pk, nav); dd_live_win = min(dd_live_win, nav / pk - 1)
            eps, tot = episode_table(rec, 'proxy' if hn == 'proxy' else 'real')
            inwin = [e for e in eps if not (e[1] < p0 or e[0] > t0)]
            top = eps[:5]; bot = eps[-3:]
            log(f"    {n:<14} MaxDD {m1*100:.1f}% ({p1} -> {t1}); its drawdown inside the live window {dd_live_win*100:.1f}%; "
                f"{len(eps)} flagged episodes, {len(inwin)} inside the live window (days {sum(e[2] for e in inwin)}, +{sum(e[3] for e in inwin)*100:.1f} pp vs live); "
                f"total vs live {tot*100:+.1f} pp")
            log(f"        top episodes: " + "; ".join(f"{a}..{b} ({c}d {g*100:+.1f}pp)" for a, b, c, g in top))
            log(f"        worst:        " + "; ".join(f"{a}..{b} ({c}d {g*100:+.1f}pp)" for a, b, c, g in bot))
    # shared-episode check on the real daily rows: for each pair of singles, the overlap of their top-3 episodes by gain
    log("  real daily: top-3 gain episodes per single (dates) -- identical episodes across singles mean the same days are being dodged:")
    for n in RNAMES:
        eps, _ = episode_table(RES[SINGLE_IDX[n]], 'real')
        log(f"    {n:<14} " + " | ".join(f"{a}..{b} {g*100:+.1f}pp" for a, b, c, g in eps[:3]))

    # ---- deep diagnostics: best single, best pair, best union, full 5-union
    log(f"\n{'='*118}\nDEEP DIAGNOSTICS (best single, best pair, best union of 3-5, full 5-union; picks by full-period proxy Sharpe)\n{'='*118}")
    bs = RES[PK['single']]; bp = RES[PK['pair']]; bu = RES[PK['union']]; fu = RES[PK['full']]
    fctl = ctrl_series(bs['ctrl_f'])
    deep(bs, 'live', LIVE_SER, REAL_SER, extra_refs=((f"proxy vs constant-D f={bs['ctrl_f']}% (matched)", SER[bs['idx']], fctl[0]),
                                                      (f"real vs constant-D f={bs['rctrl_f']}% (matched)", RSER[bs['idx']], ctrl_series(bs['rctrl_f'])[1])))
    for rec in (bp, bu, fu):
        b1 = rec['best_single']; b1r = rec['best_single_real']
        refs = ((f"proxy vs live", SER[rec['idx']], LIVE_SER), (f"real daily vs live", RSER[rec['idx']], REAL_SER))
        if b1r != b1:
            refs += ((f"real daily vs better single by real Sharpe ({b1r})", RSER[rec['idx']], RSER[SINGLE_IDX[b1r]]),)
        deep(rec, b1, SER[SINGLE_IDX[b1]], RSER[SINGLE_IDX[b1]], extra_refs=refs)
    if PK['pair_real'] != PK['pair']:
        rec = RES[PK['pair_real']]; b1 = rec['best_single']
        log(f"\n  (best pair by REAL daily Sharpe differs: #{rec['idx']} {rec['label']})")
        deep(rec, b1, SER[SINGLE_IDX[b1]], RSER[SINGLE_IDX[b1]])

    # ---- tree: marginal contribution of each case
    log(f"\n{'='*118}\nA TREE OF SPECIAL CASES: what each case uniquely contributes (best union and the full 5-union)\n{'='*118}")
    def qld_next(idx_list, harness):
        if harness == 'proxy': return [rows[i]['legs'][2] for i in idx_list]
        return [RPX['QLD'][RDAYS[k + 1]] / RPX['QLD'][RDAYS[k]] - 1 for k in idx_list]
    for rec in (bu, fu) if bu['idx'] != fu['idx'] else (fu,):
        mem = list(rec['spec'][1]); spec = (rec['spec'][0], tuple(mem))
        log(f"\n  UNION #{rec['idx']} {rec['label']}: proxy {fmt_ev(rec['ev'])} S {rec['ev']['s_sharpe']:.3f} H {rec['ev']['h_sharpe']:.3f} | real {fmt_ev(rec['real'])}")
        log(f"  {'case':<14}{'flag':>5}{'uniq':>5}{'uEp':>4}{'J rest':>7} | drop-case: {'dS_S':>7}{'dS_H':>7}{'dS_F':>7}{'dCAGR':>7}{'dMDD':>6}{'rdSh':>7}{'rdCAGR':>7}{'rdDD':>6} | "
            f"QLD next-day bp: {'uniq S':>7}{'shr S':>7}{'t':>5}{'uniq H':>7}{'shr H':>7}{'t':>5}{'uniq R':>7}{'shr R':>7}{'t':>5}  earns?")
        for c in mem:
            others = [m for m in mem if m != c]
            fq_c = FLQ[c]; fq_o = [any(FLQ[m][j] for m in others) for j in range(nD)]
            uniq = [j for j in range(nD) if fq_c[j] and not fq_o[j]]; shared = [j for j in range(nD) if fq_c[j] and fq_o[j]]
            A = set(j for j in range(nD) if fq_c[j]); B = set(j for j in range(nD) if fq_o[j])
            jr = len(A & B) / len(A | B) if A | B else float('nan')
            uep = len(episodes([j in set(uniq) for j in range(nD)], D_ROWS))
            # leave-one-case-out
            sub = ('or', tuple(others)) if len(others) > 1 else ('single', tuple(others))
            rs, _, _, _, _ = eval_candidate(sub)
            d = lambda key: rec['ev'][key] - rs['ev'][key]
            rd = lambda key: rec['real'][key] - rs['real'][key]
            # next-day QLD-leg return on unique vs shared days, by era, and on the real rows
            def prof(idx_u, idx_s, mask=None, harness='proxy'):
                if mask is not None:
                    idx_u = [j for j in idx_u if mask[j]]; idx_s = [j for j in idx_s if mask[j]]
                a = qld_next([D_ROWS[j] for j in idx_u] if harness == 'proxy' else [RD_IDX[j] for j in idx_u], harness)
                b = qld_next([D_ROWS[j] for j in idx_s] if harness == 'proxy' else [RD_IDX[j] for j in idx_s], harness)
                ma = sum(a) / len(a) * 1e4 if a else float('nan'); mb = sum(b) / len(b) * 1e4 if b else float('nan')
                return ma, mb, tstat(a, b)
            uS, sS, tS = prof(uniq, shared, S_MASK); uH, sH, tH = prof(uniq, shared, H_MASK)
            fr_c = FLR[c]; fr_o = [any(FLR[m][j] for m in others) for j in range(len(RD_DATES))]
            uniq_r = [j for j in range(len(RD_DATES)) if fr_c[j] and not fr_o[j]]; shared_r = [j for j in range(len(RD_DATES)) if fr_c[j] and fr_o[j]]
            uR, sR, tR = prof(uniq_r, shared_r, None, 'real')
            earns = (uS < 0) and (uH < 0)
            log(f"  {c:<14}{len(A):>5}{len(uniq):>5}{uep:>4}{jr:>7.2f} |            {d('s_sharpe'):>+7.3f}{d('h_sharpe'):>+7.3f}{d('sharpe'):>+7.3f}{d('cagr')*100:>+7.2f}{d('mdd')*100:>+6.1f}"
                f"{rd('sharpe'):>+7.3f}{rd('cagr')*100:>+7.2f}{rd('mdd')*100:>+6.1f} | {'':>17}{uS:>7.0f}{sS:>7.0f}{tS:>5.1f}{uH:>7.0f}{sH:>7.0f}{tH:>5.1f}{uR:>7.0f}{sR:>7.0f}{tR:>5.1f}  "
                f"{'EARNS' if earns else 'no'} (uniq S n{len([j for j in uniq if S_MASK[j]])} H n{len([j for j in uniq if H_MASK[j]])} R n{len(uniq_r)})")
        log("  drop-case = union WITH the case minus union WITHOUT it (positive = the case helps). 'earns' = the case's unique days are money-losing for QLD in both proxy eras.")
        log("  shr = days the case shares with at least one other case of the union.")

    # ---- post-hoc per-case actions on the best union (NOT part of the permutation)
    log(f"\n{'='*118}\nPOST-HOC (not pre-registered, not in the permutation): per-case actions on the best union #{bu['idx']} {bu['label']} -- "
        f"each case independently cash or 50 % QLD / 50 % cash; a day flagged by a cash case is cash, otherwise half\n{'='*118}")
    mem = list(bu['spec'][1])
    log(f"  {'actions (' + ','.join(SHORT[m] for m in mem) + ')':<28}{'CAGR':>7}{'Sharpe':>7}{'MaxDD':>7}{'exp':>6}{'S Sh':>7}{'H Sh':>7} | real {'CAGR':>7}{'Sharpe':>7}{'MaxDD':>7}")
    for acts in itertools.product(('cash', 'half'), repeat=len(mem)):
        amap = dict(zip(mem, acts))
        def rowq(d, amap=amap):
            j = DIDX[d]; fl = [m for m in mem if FLQ[m][j]]
            return CASH if any(amap[m] == 'cash' for m in fl) else HALF
        def rowr(d, amap=amap):
            j = RDIDX[d]; fl = [m for m in mem if FLR[m][j]]
            return CASH if any(amap[m] == 'cash' for m in fl) else HALF
        onq = set(d for d, f in zip(D_DATES, combine(('or', tuple(mem)), FLQ)) if f)
        onr = set(d for d, f in zip(RD_DATES, combine(('or', tuple(mem)), FLR)) if f)
        ev, _ = proxy_eval(onq, row_fn=rowq); rev, _ = real_eval(onr, row_fn=rowr)
        log(f"  {'/'.join(acts):<28}{ev['cagr']*100:>6.2f}%{ev['sharpe']:>7.3f}{ev['mdd']*100:>6.1f}%{ev['risky']*100:>5.1f}%{ev['s_sharpe']:>7.3f}{ev['h_sharpe']:>7.3f} | "
            f"{rev['cagr']*100:>6.2f}%{rev['sharpe']:>7.3f}{rev['mdd']*100:>6.1f}%")
    log(f"\n[diag done]  elapsed {time.time()-T0:.0f}s")
