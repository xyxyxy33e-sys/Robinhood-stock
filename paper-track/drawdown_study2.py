"""Where to cut max drawdown, PART II: the general question.

Part I (drawdown_study.py) tested 19 knobs inside the existing design and found
exactly one that beats flat de-levering, by 0.1 pp. This asks the broader
question the owner posed: across the WHOLE strategy, not just its knobs, where
is the drawdown and is any of it structurally removable?

  A. IS IT JUST BETA? Decompose every episode into leveraged-beta loss vs a
     timing residual. If the residual is ~0, nothing but less beta, different
     beta, or convexity can help.
  B. WHICH STATE CARRIES THE RISK? Attribute drawdown-day losses and downside
     semi-variance across ALL sessions by regime, then redistribute leverage
     BETWEEN states and score against the flat-de-lever frontier.
  C. IS THE EXIT FAST ENOUGH? Measure how many sessions the design takes to
     shed risk after a peak, then test faster macro classifiers (50/200 ->
     40/150, 30/120, 20/100).
  D. IS DIVERSIFICATION THE ANSWER? Carve a bond sleeve (synthesised from
     DGS10, full history) out of the risky legs and score it the same way.

Same null throughout: flat de-levering. A lever must land ABOVE that frontier.
MaxDD is negative, so POSITIVE edge = shallower than the null = real work.

NOTHING IS APPLIED. Research only.

Usage:  python3 paper-track/drawdown_study2.py   [DDS2_STAGE=all|a|b|c|d]
"""
import os, sys, io, csv, math, time, contextlib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)
sys.path.insert(0, 'paper-track')
os.environ.setdefault('TDT_STAGE', 'none')
STAGE = os.environ.get('DDS2_STAGE', 'all')
T0 = time.time()

LOG = 'paper-track/research_notes/drawdown_study2_run.log'
_lf = open(LOG, 'a')
def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s); _lf.write(s + '\n'); _lf.flush()

_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    import drawdown_study as DS          # reuses its simulator, frontier and episode finder
import trim_destination_test as TDT
from d_substate_fresh import rows, RDAYS, SEARCH, HOLDOUT
from state import compute_states, compute_fast_states, effective_state, TARGET_WEIGHTS
from drift_band_test import annual_stats

BASE, sim, ev, episodes = DS.BASE, DS.sim, DS.ev, DS.episodes
RINFO, RLEG_RET, BP_Q, BP_R = DS.RINFO, DS.RLEG_RET, DS.BP_Q, DS.BP_R
PLEG = DS.PLEG; LEGN = DS.LEGN; W0 = DS.W0
RW = {r['d']: r for r in rows}
PDATES = [r['d'] for r in rows]

# leg betas to the core index (proxy core = QQQ; real core = SPMO ~0.95 to QQQ)
BETA_LEG = (1.00, 3.00, 2.00, 0.20, 0.00)

_QR = {}
def QQQ_RET(h):
    """QQQ's NEXT-session return keyed by decision date -- the same timing convention
    the harness uses (decide on close t, earn t -> t+1). On the proxy this is the
    precomputed rows['qqq'] field, which is a RETURN, not a price."""
    if h in _QR: return _QR[h]
    if h == 'proxy':
        out = {r['d']: r['qqq'] for r in rows}
    else:
        px = TDT.RQQQ; ds = RDAYS
        out = {ds[i]: px[ds[i + 1]] / px[ds[i]] - 1 for i in range(len(ds) - 1)}
    _QR[h] = out
    return out


def regkey(x):
    return 'D-gated' if x['gate'] else (x['st'] if x['st'] in 'EF' else x['eff'])

def frontier_ready():
    if not DS.FRONT:
        with contextlib.redirect_stdout(io.StringIO()):
            DS.stage_frontier()
frontier_ready()
edge = lambda h, e: (e['mdd'] - DS.front_dd_at(h, e['cagr'])) * 100

def scoreline(lab, h, e):
    b = BASE[h]
    return (f"  {lab:<34}{e['cagr']*100:>8.2f}%{e['sharpe']:>9.3f}{e['mdd']*100:>8.1f}%{e['exp']*100:>7.1f}%  |"
            f"{(e['cagr']-b['cagr'])*100:>+8.2f}{(e['mdd']-b['mdd'])*100:>+9.2f}{e['sharpe']-b['sharpe']:>+9.3f}"
            f"{edge(h, e):>+13.2f}")
HDR = (f"  {'variant':<34}{'CAGR':>9}{'Sharpe':>9}{'MaxDD':>9}{'exp':>8}  |{'dCAGR':>8}{'dMaxDD':>9}{'dSharpe':>9}"
       f"{'vs frontier':>13}")

# ---------------------------------------------------------------- A. is it just beta?
def stage_a():
    log("\n" + "=" * 132)
    log("PART II  drawdown_study2 (2026-09-20): where to cut max DD across the WHOLE strategy")
    log("=" * 132)
    log(f"  LIVE (asserted): proxy {BASE['proxy']['cagr']*100:.2f}% / {BASE['proxy']['sharpe']:.3f} / "
        f"{BASE['proxy']['mdd']*100:.1f}% | real {BASE['real']['cagr']*100:.2f}% / {BASE['real']['sharpe']:.3f} / "
        f"{BASE['real']['mdd']*100:.1f}%")
    log("\n" + "=" * 132)
    log("A  IS IT JUST LEVERAGED BETA? Each episode split into (avg effective beta x index move) vs a timing residual.")
    log("=" * 132)
    log("   effective beta = sum(weight_j x leg_beta_j), leg betas core 1.0 / TQQQ 3.0 / QLD 2.0 / XLU 0.2 / BOXX 0.")
    for h in ('proxy', 'real'):
        det = DS.dayidx(h)
        ii = {x['d']: j for j, x in enumerate(det)}
        QR = QQQ_RET(h)
        log(f"\n  {h.upper()}")
        log(f"  {'peak -> trough':<26}{'depth':>8}{'avg beta':>10}{'QQQ move':>11}{'beta-implied':>14}{'residual':>11}{'resid share':>13}")
        for e in episodes(det, topn=6):
            a, b = ii[e['peak']], ii[e['trough']]
            seg = det[a:b + 1]
            ab = sum(sum(x['held'][j] * BETA_LEG[j] for j in range(5)) for x in seg) / len(seg)
            mv = 1.0
            for x in seg: mv *= (1 + QR.get(x['d'], 0.0))
            mv -= 1
            imp = ab * mv
            res = e['depth'] - imp
            log(f"  {e['peak']+' -> '+e['trough']:<26}{e['depth']*100:>7.1f}%{ab:>10.2f}{mv*100:>10.1f}%"
                f"{imp*100:>13.1f}%{res*100:>10.1f}%{abs(res/e['depth'])*100:>12.0f}%")
    log("\n  Reference: hold a CONSTANT beta to QQQ, equal to the design's own average effective beta, over the same window.")
    log("  (First-order: beta x daily QQQ return, no financing or rebalancing drag -- a floor on what constant leverage costs.)")
    for h in ('proxy', 'real'):
        det = DS.dayidx(h); QR = QQQ_RET(h)
        ab = sum(sum(x['held'][j] * BETA_LEG[j] for j in range(5)) for x in det) / len(det)
        ser = [ab * QR.get(x['d'], 0.0) for x in det]
        c, s_, m = annual_stats(ser)
        log(f"    {h:<6} design avg beta {ab:.2f}  ->  constant-beta MaxDD {m*100:6.1f}%  CAGR {c*100:6.2f}%   "
            f"|  the DESIGN: MaxDD {BASE[h]['mdd']*100:6.1f}%  CAGR {BASE[h]['cagr']*100:6.2f}%")
        log(f"    {'':6} i.e. the timing machinery turns a {m*100:.1f}% drawdown into {BASE[h]['mdd']*100:.1f}% "
            f"while raising CAGR from {c*100:.2f}% to {BASE[h]['cagr']*100:.2f}%")

# ---------------------------------------------------------------- B. which state carries the risk?
def stage_b():
    log("\n" + "=" * 132)
    log("B1  RISK BY REGIME across ALL sessions: share of time, of loss taken while in drawdown, and of downside semi-variance")
    log("=" * 132)
    for h in ('proxy', 'real'):
        det = DS.dayidx(h)
        tot_t = len(det)
        reg = {}
        for x in det:
            k = regkey(x)
            r = reg.setdefault(k, dict(n=0, dd_loss=0.0, semi=0.0, expo=0.0))
            r['n'] += 1; r['expo'] += sum(x['held'][:4])
            if x['net'] < 0:
                r['semi'] += x['net'] ** 2
                if x['dd'] < -0.01: r['dd_loss'] += x['net']
        TS = sum(r['semi'] for r in reg.values()); TL = sum(r['dd_loss'] for r in reg.values())
        log(f"\n  {h.upper()}  ({tot_t} sessions)")
        log(f"  {'regime':<12}{'days':>7}{'% time':>9}{'avg exp':>10}{'loss in DD':>12}{'% of DD loss':>14}{'% of semivar':>14}{'loss/day in DD':>16}")
        for k, r in sorted(reg.items(), key=lambda kv: kv[1]['dd_loss']):
            log(f"  {k:<12}{r['n']:>7}{r['n']/tot_t*100:>8.1f}%{r['expo']/r['n']*100:>9.1f}%"
                f"{r['dd_loss']*100:>11.1f}%{r['dd_loss']/TL*100:>13.1f}%{r['semi']/TS*100:>13.1f}%"
                f"{r['dd_loss']/max(1,r['n'])*1e4:>15.1f}bp")

    log("\n" + "=" * 132)
    log("B2  MOVE THE LEVERAGE BETWEEN STATES (total risk budget roughly held, distribution changed), scored vs the frontier")
    log("=" * 132)
    VAR = [
        ('LIVE  A 50/50, B 75/25, D QLD',  {}),
        ('leverage INTO A (A 40/60, B 90/10)',  dict(a_row=(0.40, 0.60, 0, 0, 0), b_row=(0.90, 0.10, 0, 0, 0))),
        ('leverage INTO B (A 65/35, B 55/45)',  dict(a_row=(0.65, 0.35, 0, 0, 0), b_row=(0.55, 0.45, 0, 0, 0))),
        ('leverage OUT of D (D core, A 35/65)', dict(d_row=(1.0, 0, 0, 0, 0), a_row=(0.35, 0.65, 0, 0, 0))),
        ('D as TQQQ 70/30 cash (same ~2.1x)',   dict(d_row=(0.0, 0.70, 0, 0, 0.30))),
        ('D as QLD 85/15 cash, A 45/55',        dict(d_row=(0.0, 0, 0.85, 0, 0.15), a_row=(0.45, 0.55, 0, 0, 0))),
        ('all leverage as QLD (A 0/0/100 QLD)', dict(a_row=(0.0, 0, 1.0, 0, 0), b_row=(0.30, 0, 0.70, 0, 0))),
    ]
    for h in ('real', 'proxy'):
        log(f"\n  {h.upper()}")
        log(HDR)
        for lab, kw in VAR:
            e, _ = ev(h, **kw)
            log(scoreline(lab, h, e))

# ---------------------------------------------------------------- C. is the exit fast enough?
def stage_c():
    log("\n" + "=" * 132)
    log("C1  HOW FAST DOES THE DESIGN SHED RISK after an episode peak? (effective beta, sessions after the peak)")
    log("=" * 132)
    for h in ('proxy', 'real'):
        det = DS.dayidx(h); ii = {x['d']: j for j, x in enumerate(det)}
        log(f"\n  {h.upper()}")
        log(f"  {'peak -> trough':<26}{'depth':>8}{'beta at peak':>14}{'+5d':>8}{'+10d':>8}{'+20d':>8}"
            f"{'sess to beta<0.5':>19}{'trough at sess':>16}")
        for e in episodes(det, topn=6):
            a, b = ii[e['peak']], ii[e['trough']]
            bt = lambda j: sum(det[j]['held'][k] * BETA_LEG[k] for k in range(5)) if j < len(det) else float('nan')
            first = next((j - a for j in range(a, b + 1) if bt(j) < 0.5), None)
            log(f"  {e['peak']+' -> '+e['trough']:<26}{e['depth']*100:>7.1f}%{bt(a):>14.2f}{bt(a+5):>8.2f}"
                f"{bt(a+10):>8.2f}{bt(a+20):>8.2f}{(str(first) if first is not None else 'never'):>19}{b-a:>16}")

    log("\n" + "=" * 132)
    log("C2  FASTER MACRO CLASSIFIER (live 50/200). States recomputed end to end; fast overlay and everything else unchanged.")
    log("=" * 132)
    for h in ('real', 'proxy'):
        log(f"\n  {h.upper()}")
        log(HDR)
        for sn, ln in ((50, 200), (40, 150), (30, 120), (20, 100), (50, 150), (30, 200)):
            lab = f"macro {sn}/{ln}" + ("  (LIVE)" if (sn, ln) == (50, 200) else "")
            e, _ = ev(h, macro=(sn, ln))
            if (sn, ln) == (50, 200):
                assert abs(e['cagr'] - BASE[h]['cagr']) < 1e-9 and abs(e['mdd'] - BASE[h]['mdd']) < 1e-9, \
                    'recomputing the classifier at 50/200 must reproduce LIVE exactly'
            log(scoreline(lab, h, e))
        log("  (the 50/200 row is the classifier RECOMPUTED end to end; it reproduces LIVE exactly -- asserted)")

# ---------------------------------------------------------------- D. a diversification sleeve
def load_dgs10():
    y = {}
    for r in csv.DictReader(open('data/dgs10.csv')):
        try: y[r['observation_date']] = float(r['DGS10']) / 100.0
        except (ValueError, KeyError): pass
    return y
def bond_series(dates, dur=8.5):
    """Daily total return of a constant-maturity 10y note: carry minus duration x yield change.
    Crude but standard, and it covers the whole history (DGS10 starts 1962)."""
    y = load_dgs10(); out = {}; prev = None
    for d in dates:
        yy = y.get(d)
        if yy is None: yy = prev
        if yy is None or prev is None:
            out[d] = 0.0
        else:
            out[d] = yy / 252.0 - dur * (yy - prev)
        if yy is not None: prev = yy
    return out

def stage_d():
    log("\n" + "=" * 132)
    log("D  DIVERSIFICATION SLEEVE: carve x% out of the RISKY legs into a 10y-note proxy (DGS10 carry - 8.5 x dy).")
    log("=" * 132)
    log("   This is the one axis Part I never touched: not less risk, DIFFERENT risk. Scored on the same frontier.")
    for h in ('real', 'proxy'):
        dates = (RDAYS[:-1] if h == 'real' else PDATES)
        nxt = {dates[i]: dates[i + 1] for i in range(len(dates) - 1)}
        BR = bond_series(sorted(set(list(dates) + list(nxt.values()))))
        log(f"\n  {h.upper()}   bond proxy over this window: "
            f"CAGR {annual_stats([BR[d] for d in dates])[0]*100:.2f}%, "
            f"MaxDD {annual_stats([BR[d] for d in dates])[2]*100:.1f}%")
        log(HDR)
        e, _ = ev(h); log(scoreline('LIVE', h, e))
        for x in (0.10, 0.20, 0.30):
            e, _ = ev(h, bond_sleeve=(x, BR))
            log(scoreline(f'bond sleeve {x*100:.0f}% of risky', h, e))

if __name__ == '__main__':
    if STAGE in ('all', 'a'): stage_a()
    if STAGE in ('all', 'b'): stage_b()
    if STAGE in ('all', 'c'): stage_c()
    if STAGE in ('all', 'd'): stage_d()
    log(f"\n[done] elapsed {time.time()-T0:.0f}s")
