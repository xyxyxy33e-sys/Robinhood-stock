"""Where can max drawdown be cut, and what does each cut cost?

Owner question (2026-09-20): the live design runs proxy MaxDD -27.0% (26y) and
real daily -18.6% (SPMO era). Where does that damage come from, and which lever
reduces it most cheaply?

THE FRAME, which is the whole point. Any reduction in risk reduces drawdown.
The null is therefore NOT "no change" but "just hold less every day": take the
live design and flat de-lever all four risky legs by a constant k. That traces
a (CAGR, MaxDD) frontier. A lever is only interesting if it lands ABOVE that
frontier -- i.e. buys more drawdown reduction per point of CAGR than simply
holding less would have. Every candidate below is scored that way.

Baseline = the current live design (D gate on, E cash, A 50/50, step 1/3, 20%
vol target on plain 30d vol, 5% band, 4bp), harness borrowed from
trim_destination_test (TDT_STAGE=none), which asserts proxy 25.46% / 1.071 /
-27.0% (S 1.399, H 0.825) and real daily 37.30% / 1.475 / -18.6%.

NOTHING IS APPLIED. Research only.

Usage:  python3 paper-track/drawdown_study.py   [DDS_STAGE=all|census|frontier|levers]
"""
import os, sys, io, math, time, contextlib

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT)
sys.path.insert(0, 'paper-track')
os.environ.setdefault('TDT_STAGE', 'none')
STAGE = os.environ.get('DDS_STAGE', 'all')
T0 = time.time()

LOG = 'paper-track/research_notes/drawdown_study_run.log'
_lf = open(LOG, 'a')
def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s); _lf.write(s + '\n'); _lf.flush()

_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    import trim_destination_test as TDT
from d_substate_fresh import rows, RDAYS, SEARCH, HOLDOUT, REGIMES, boot, bstats
from state import TARGET_WEIGHTS, VOL_TARGET_PA, REBALANCE_DRIFT_BAND, extension_votes
from drift_band_test import annual_stats, ONE_WAY_SPREAD
import monthly_returns as MR

LEGN = ('SPMO/core', 'TQQQ', 'QLD', 'XLU', 'BOXX')
CASH = (0.0, 0.0, 0.0, 0.0, 1.0)
BP_Q, BP_R = TDT.BP_Q, TDT.BP_R
RINFO, RLEG_RET = TDT.RINFO, TDT.RLEG_RET
PLEG = {r['d']: r['legs'] for r in rows}
W0 = dict(TARGET_WEIGHTS)

# ---------------------------------------------------------------- one simulator, both harnesses
_MACRO = {}
def macro_states(harness, sn, ln):
    """Recompute the six-state macro classifier end to end at (short_n, long_n),
    then the effective state through the live 20/100 fast overlay."""
    k = (harness, sn, ln)
    if k in _MACRO: return _MACRO[k]
    from state import compute_states as _cs, compute_fast_states as _cf, effective_state as _es
    if harness == 'real':
        px = TDT.RQQQ
    else:
        import d_substate_fresh as _DSF
        px = _DSF._QQQ_FULL              # REAL QQQ PRICES. rows['qqq'] is a RETURN, not a price.
    ds = sorted(px)
    st = dict(zip(ds, _cs(ds, px, short_n=sn, long_n=ln)))
    fa = _cf(ds, px)
    out = {d: (st[d], _es(st[d], fa[d])) for d in ds}
    _MACRO[k] = out
    return out


def sim(harness='real', vol_target=VOL_TARGET_PA, d_vol_target=None, lev_cap=None,
        a_row=None, b_row=None, d_row=None, macro=None, bond_sleeve=None,
        gate_breadth=0.20, gate_gap200=0.02, brake=None, band=REBALANCE_DRIFT_BAND,
        scale=1.0, one_way=None, detail=False):
    """Live design with one knob moved. brake=(x, m): when NAV is more than x
    below its running peak, multiply the risky legs by m (a portfolio-level
    drawdown brake, decided on the same close as everything else)."""
    if harness == 'real':
        days = RDAYS[:-1]; ow = MR.ONE_WAY if one_way is None else one_way
        info = lambda d: RINFO[d]; legs = lambda d: RLEG_RET[d]; bp = BP_R
        keyf = lambda I, v, g: (I['eff'], v, g)
    else:
        days = [r['d'] for r in rows]; ow = ONE_WAY_SPREAD if one_way is None else one_way
        RW = {r['d']: r for r in rows}
        info = lambda d: RW[d]; legs = lambda d: PLEG[d]; bp = BP_Q
        keyf = lambda I, v, g: (I['state'], I['agree'])
    MS = macro_states(harness, *macro) if macro else None
    BW, BR = (bond_sleeve if bond_sleeve else (0.0, None))
    held = prev = None
    out = []; risky = 0.0; nreb = 0
    nav = 1.0; peak = 1.0
    for d in days:
        I = info(d)
        st = I['st'] if harness == 'real' else I['state']
        eff = I['eff']; gaps = I['gaps']; vol = I['vol']
        if MS is not None and d in MS:
            st, eff = MS[d]
        g200 = gaps.get(200)
        b = bp.get(d)
        gate = (st == 'D') and ((b is not None and b < gate_breadth) or
                                (g200 is not None and g200 < gate_gap200))
        v = 0
        if gate or st == 'E':
            row = CASH
        elif eff == 'A':
            v = extension_votes(eff, gaps)
            f = max(0.0, 1.0 - (1.0 / 3.0) * v)
            w = a_row if a_row is not None else W0['A']
            row = tuple(a * f for a in w[:4]) + (1 - f * sum(w[:4]),)
        else:
            row = W0[eff]
            if b_row is not None and eff == 'B': row = b_row
            if d_row is not None and st == 'D': row = d_row
        if lev_cap is not None:                      # cap the 3x leg, surplus to core
            t3 = row[1]
            if t3 > lev_cap:
                row = (row[0] + (t3 - lev_cap), lev_cap) + tuple(row[2:])
        vtg = d_vol_target if (d_vol_target is not None and st == 'D' and not gate) else vol_target
        m = 1.0 if not vol else min(1.0, vtg / vol)
        if brake is not None and nav < peak * (1.0 - brake[0]):
            m *= brake[1]
        t = tuple(x * m for x in row[:4]) + (1.0 - sum(row[:4]) * m,)
        if scale != 1.0:
            rk = sum(t[:4]); t = tuple(x * scale for x in t[:4]) + (1.0 - rk * scale,)
        if BW:                                   # carve BW of the risky book into the bond sleeve
            bw = BW * sum(t[:4])
            t = tuple(x * (1 - BW) for x in t[:4]) + (t[4], bw)
        elif BR is not None:
            t = tuple(t) + (0.0,)
        key = keyf(I, v, gate)
        nl = len(t)
        cost = 0.0
        if held is None:
            held = list(t); nreb += 1
        else:
            drift = sum(abs(t[j] - held[j]) for j in range(nl))
            if key != prev or drift > band:
                cost = ow * drift; held = list(t); nreb += 1
        lr = tuple(legs(d)) + ((BR.get(d, 0.0),) if BR is not None else ())
        gg = sum(held[j] * lr[j] for j in range(nl))
        net = gg - cost
        risky += sum(held[:4])
        nav *= (1 + net); peak = max(peak, nav)
        if detail:
            out.append(dict(d=d, st=st, eff=eff, gate=gate, v=v, held=list(held),
                            lr=lr, net=net, nav=nav, dd=nav / peak - 1))
        else:
            out.append(net)
        dn = 1 + gg
        if dn > 0: held = [held[j] * (1 + lr[j]) / dn for j in range(nl)]
        prev = key
    n = len(days)
    return out, risky / n, nreb / (n / 252.0)

def ev(harness='real', **kw):
    ser, exp, reb = sim(harness, **kw)
    c, s, m = annual_stats(ser)
    return dict(cagr=c, sharpe=s, mdd=m, exp=exp, reb=reb), ser

# sanity: the untouched simulator must reproduce the asserted baselines
_r, _ = ev('real'); _p, _ = ev('proxy')
assert abs(_r['cagr'] * 100 - 37.30) < 0.02 and abs(_r['sharpe'] - 1.475) < 0.002 and abs(_r['mdd'] * 100 + 18.6) < 0.06, \
    f"real baseline not reproduced: {_r}"
assert abs(_p['cagr'] * 100 - 25.46) < 0.02 and abs(_p['sharpe'] - 1.071) < 0.002 and abs(_p['mdd'] * 100 + 27.0) < 0.06, \
    f"proxy baseline not reproduced: {_p}"
BASE = {'real': _r, 'proxy': _p}

def episodes(det, topn=8, min_depth=0.05):
    """Peak-to-trough-to-recovery episodes, deepest first."""
    eps = []; peak = det[0]['nav']; pd_ = det[0]['d']; tr = peak; td = pd_
    for x in det:
        if x['nav'] >= peak:
            if tr / peak - 1 <= -min_depth:
                eps.append(dict(peak=pd_, trough=td, rec=x['d'], depth=tr / peak - 1))
            peak = x['nav']; pd_ = x['d']; tr = peak; td = pd_
        elif x['nav'] < tr:
            tr = x['nav']; td = x['d']
    if tr / peak - 1 <= -min_depth:
        eps.append(dict(peak=pd_, trough=td, rec=None, depth=tr / peak - 1))
    eps.sort(key=lambda e: e['depth'])
    return eps[:topn]


IDX = {'real': None, 'proxy': None}
def dayidx(h):
    if IDX[h] is None:
        d, _, _ = sim(h, detail=True)
        IDX[h] = d
    return IDX[h]

# ---------------------------------------------------------------- 1. census + anatomy
def stage_census():
    log("\n" + "=" * 130)
    log("RESEARCH LINE drawdown_study (2026-09-20): where does the drawdown come from, and what would cut it?")
    log("=" * 130)
    log(f"  LIVE baselines (asserted): proxy {BASE['proxy']['cagr']*100:.2f}% / {BASE['proxy']['sharpe']:.3f} / "
        f"{BASE['proxy']['mdd']*100:.1f}%  exp {BASE['proxy']['exp']*100:.1f}% | "
        f"real {BASE['real']['cagr']*100:.2f}% / {BASE['real']['sharpe']:.3f} / {BASE['real']['mdd']*100:.1f}%  "
        f"exp {BASE['real']['exp']*100:.1f}%")
    log("\n" + "=" * 130)
    log("1a  DRAWDOWN CENSUS: every peak-to-trough episode deeper than 5%, deepest first")
    log("=" * 130)
    for h in ('proxy', 'real'):
        det = dayidx(h)
        log(f"\n  {h.upper()} ({det[0]['d']} .. {det[-1]['d']}, {len(det)} sessions)")
        log(f"  {'#':<3}{'peak':<12}{'trough':<12}{'recovered':<12}{'depth':>8}{'to trough':>11}{'to recover':>12}   state mix at the trough half")
        for i, e in enumerate(episodes(det, topn=8), 1):
            ii = {x['d']: j for j, x in enumerate(det)}
            a, b = ii[e['peak']], ii[e['trough']]
            rec = ii[e['rec']] - b if e['rec'] else None
            seg = det[a:b + 1]
            mid = seg[len(seg) // 2:]
            cnt = {}
            for x in mid:
                k = 'D-gated' if x['gate'] else (x['st'] if x['st'] in 'EF' else x['eff'])
                cnt[k] = cnt.get(k, 0) + 1
            mix = ', '.join(f"{k} {n/len(mid)*100:.0f}%" for k, n in sorted(cnt.items(), key=lambda kv: -kv[1])[:4])
            log(f"  {i:<3}{e['peak']:<12}{e['trough']:<12}{(e['rec'] or 'not yet'):<12}{e['depth']*100:>7.1f}%"
                f"{b-a:>11}{(str(rec) if rec is not None else '-'):>12}   {mix}")

    log("\n" + "=" * 130)
    log("1b  WHERE THE LOSS IS INFLICTED: inside the 3 worst episodes, total log-loss split by regime and by leg")
    log("=" * 130)
    for h in ('proxy', 'real'):
        det = dayidx(h); ii = {x['d']: j for j, x in enumerate(det)}
        log(f"\n  {h.upper()}")
        for e in episodes(det, topn=3):
            a, b = ii[e['peak']], ii[e['trough']]
            seg = det[a:b + 1]
            byreg = {}; byleg = [0.0] * 5; tot = 0.0
            for x in seg:
                k = 'D-gated' if x['gate'] else (x['st'] if x['st'] in 'EF' else x['eff'])
                lg = math.log1p(x['net']) if x['net'] > -1 else -9
                byreg[k] = byreg.get(k, 0.0) + lg; tot += lg
                for j in range(5):
                    byleg[j] += x['held'][j] * x['lr'][j]
            log(f"    {e['peak']} -> {e['trough']}  {e['depth']*100:.1f}%  ({b-a} sessions)")
            log(f"      by regime: " + ", ".join(
                f"{k} {v*100:+.1f} pp ({sum(1 for x in seg if ('D-gated' if x['gate'] else (x['st'] if x['st'] in 'EF' else x['eff']))==k)}d)"
                for k, v in sorted(byreg.items(), key=lambda kv: kv[1])))
            log(f"      by leg   : " + ", ".join(f"{LEGN[j]} {byleg[j]*100:+.1f} pp" for j in range(5)))
            avx = sum(sum(x['held'][:4]) for x in seg) / len(seg)
            log(f"      average exposure through the episode {avx*100:.1f}% (design average {BASE[h]['exp']*100:.1f}%)")

# ---------------------------------------------------------------- 2. the flat de-lever frontier (the null)
FRONT = {}
def stage_frontier():
    log("\n" + "=" * 130)
    log("2  THE NULL: flat de-lever. All four risky legs x k EVERY day. This is what 'just hold less' buys.")
    log("=" * 130)
    for h in ('proxy', 'real'):
        log(f"\n  {h.upper()}")
        log(f"  {'k':>6}{'CAGR':>9}{'Sharpe':>9}{'MaxDD':>9}{'exp':>8}   {'dCAGR pp':>10}{'dMaxDD pp':>11}{'pp DD per pp CAGR':>20}")
        pts = []
        for k in (1.00, 0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.60, 0.50):
            e, _ = ev(h, scale=k)
            dc = (e['cagr'] - BASE[h]['cagr']) * 100; dm = (e['mdd'] - BASE[h]['mdd']) * 100
            rate = (dm / -dc) if dc < -1e-9 else float('nan')
            pts.append((k, e, dc, dm))
            log(f"  {k:>6.2f}{e['cagr']*100:>8.2f}%{e['sharpe']:>9.3f}{e['mdd']*100:>8.1f}%{e['exp']*100:>7.1f}%   "
                f"{dc:>+10.2f}{dm:>+11.2f}{(f'{rate:.3f}' if rate == rate else '-'):>20}")
        FRONT[h] = pts
        shp = ', '.join('%.3f' % p[1]['sharpe'] for p in pts)
        log("  Sharpe along the frontier is nearly FLAT by construction (same design, de-levered): " + shp)

def front_dd_at(h, cagr):
    """Interpolate the flat-frontier MaxDD at a given CAGR -- the drawdown you could
    have had for free by just holding less.

    SIGN: MaxDD is NEGATIVE. edge = arm_mdd - frontier_mdd, so POSITIVE edge means the
    arm's drawdown is SHALLOWER (closer to zero) than the frontier's at the same CAGR --
    that is the lever doing real work. NEGATIVE edge means it is DEEPER than just
    holding less, i.e. strictly worse than the null."""
    pts = sorted(FRONT[h], key=lambda p: p[1]['cagr'])
    xs = [p[1]['cagr'] for p in pts]; ys = [p[1]['mdd'] for p in pts]
    if cagr <= xs[0]: return ys[0]
    if cagr >= xs[-1]: return ys[-1]
    for i in range(1, len(xs)):
        if cagr <= xs[i]:
            f = (cagr - xs[i - 1]) / (xs[i] - xs[i - 1])
            return ys[i - 1] + f * (ys[i] - ys[i - 1])
    return ys[-1]

# ---------------------------------------------------------------- 3. candidate levers
def stage_levers():
    LEVERS = [
        ('vol target 18%',            dict(vol_target=0.18)),
        ('vol target 16%',            dict(vol_target=0.16)),
        ('vol target 14%',            dict(vol_target=0.14)),
        ('vol target 12%',            dict(vol_target=0.12)),
        ('TQQQ capped at 40%',        dict(lev_cap=0.40)),
        ('TQQQ capped at 25%',        dict(lev_cap=0.25)),
        ('TQQQ capped at 0% (no 3x)', dict(lev_cap=0.00)),
        ('B row 85/15',               dict(b_row=(0.85, 0.15, 0.0, 0.0, 0.0))),
        ('B row 100/0',               dict(b_row=(1.00, 0.00, 0.0, 0.0, 0.0))),
        ('D gate breadth 0.30',       dict(gate_breadth=0.30)),
        ('D gate gap200 5%',          dict(gate_gap200=0.05)),
        ('D gate 0.30 AND gap 5%',    dict(gate_breadth=0.30, gate_gap200=0.05)),
        ('NAV brake -10% -> x0.5',    dict(brake=(0.10, 0.5))),
        ('NAV brake -10% -> cash',    dict(brake=(0.10, 0.0))),
        ('NAV brake -15% -> x0.5',    dict(brake=(0.15, 0.5))),
        ('NAV brake -15% -> cash',    dict(brake=(0.15, 0.0))),
        ('NAV brake -5% -> x0.5',     dict(brake=(0.05, 0.5))),
        ('D-row vol target 15%',      dict(d_vol_target=0.15)),
        ('D-row vol target 12%',      dict(d_vol_target=0.12)),
        ('drift band 3%',             dict(band=0.03)),
        ('drift band 2%',             dict(band=0.02)),
    ]
    for h in ('real', 'proxy'):
        log("\n" + "=" * 130)
        log(f"3  CANDIDATE LEVERS on the {h.upper()} harness. 'vs frontier' = this arm's MaxDD minus the flat-de-lever")
        log(f"   MaxDD at the SAME CAGR. MaxDD is negative, so POSITIVE = SHALLOWER than just holding less (the lever works);")
        log(f"   NEGATIVE = DEEPER than the null, i.e. it gave up return AND got a worse drawdown.")
        log("=" * 130)
        log(f"  {'lever':<28}{'CAGR':>9}{'Sharpe':>9}{'MaxDD':>9}{'exp':>7}{'reb':>6}  |{'dCAGR':>8}{'dMaxDD':>9}{'dSharpe':>9}{'vs frontier':>13}")
        b = BASE[h]
        log(f"  {'LIVE':<28}{b['cagr']*100:>8.2f}%{b['sharpe']:>9.3f}{b['mdd']*100:>8.1f}%{b['exp']*100:>6.1f}%{b['reb']:>6.1f}  |"
            f"{0:>8.2f}{0:>9.2f}{0:>9.3f}{0:>13.2f}")
        recs = []
        for lab, kw in LEVERS:
            e, ser = ev(h, **kw)
            fdd = front_dd_at(h, e['cagr'])
            edge = (e['mdd'] - fdd) * 100        # negative = shallower than the frontier
            recs.append((lab, e, edge, ser))
            log(f"  {lab:<28}{e['cagr']*100:>8.2f}%{e['sharpe']:>9.3f}{e['mdd']*100:>8.1f}%{e['exp']*100:>6.1f}%{e['reb']:>6.1f}  |"
                f"{(e['cagr']-b['cagr'])*100:>+8.2f}{(e['mdd']-b['mdd'])*100:>+9.2f}{e['sharpe']-b['sharpe']:>+9.3f}{edge:>+13.2f}")
        recs.sort(key=lambda r: -r[2])
        log(f"\n  BEST BY 'vs frontier' (most drawdown bought per point of CAGR, {h}) -- positive is good:")
        for lab, e, edge, _ in recs[:5]:
            log(f"    {lab:<28} MaxDD {e['mdd']*100:6.1f}% at CAGR {e['cagr']*100:6.2f}%  -> {edge:+.2f} pp vs the frontier, "
                f"Sharpe {e['sharpe']-BASE[h]['sharpe']:+.3f}")
        log(f"  WORST -- deeper than simply de-levering to the same CAGR ({h}):")
        for lab, e, edge, _ in recs[-3:]:
            log(f"    {lab:<28} {edge:+.2f} pp vs the frontier, Sharpe {e['sharpe']-BASE[h]['sharpe']:+.3f}")
        globals().setdefault('RECS', {})[h] = recs

    # both-era check + bootstrap on whichever levers cleared the frontier on BOTH harnesses
    log("\n" + "=" * 130)
    log("4  CROSS-HARNESS: a lever must beat the frontier on BOTH harnesses to be worth anything")
    log("=" * 130)
    er = {l: e for l, _, e, _ in RECS['real']}; ep = {l: e for l, _, e, _ in RECS['proxy']}
    both = [l for l in er if er[l] > 0.05 and ep[l] > 0.05]
    log(f"  {'lever':<28}{'real vs frontier':>18}{'proxy vs frontier':>19}   both POSITIVE (beats the null)?")
    for lab in sorted(er, key=lambda l: -(min(er[l], ep[l]))):
        ok = 'YES' if (er[lab] > 0.05 and ep[lab] > 0.05) else ''
        log(f"  {lab:<28}{er[lab]:>+18.2f}{ep[lab]:>+19.2f}   {ok}")
    log(f"\n  levers that beat the flat-de-lever frontier on BOTH harnesses: {', '.join(both) if both else 'NONE'}")
    log("  (A lever that only beats the null on one harness is a fitted artifact of that era, not a risk tool.)")

if __name__ == '__main__':
    if STAGE in ('all', 'census'): stage_census()
    if STAGE in ('all', 'frontier', 'levers'): stage_frontier()
    if STAGE in ('all', 'levers'): stage_levers()
    log(f"\n[done] elapsed {time.time()-T0:.0f}s")
