"""Research line `vol_hysteresis` (2026-09-08): the classifier's hysteresis
buffer as a FUNCTION OF REALIZED VOL instead of a fixed 1%.

Hypothesis: buf_t = clamp(k * vol_t * sqrt(h/252), buf_min, buf_max), with
k chosen so the AVERAGE buffer over the search era (2015-11-01+) is exactly
1% -- i.e. we change the SHAPE of the buffer through time, not its mean.
Wider in turbulent tapes, narrower in calm ones. Applied to the macro 50/200
classifier, the fast 20/100 re-entry classifier, or both. Everything
downstream (effective state, extension trim, vol target, 3% band, costs) is
the unchanged LIVE design run through the project's own harness.

Research only. CHANGE FREEZE until 2026-12-07. Nothing here is applied.

Run from the repo root:  python3 paper-track/vol_hysteresis.py
"""
import sys, math, random, time
sys.path.insert(0, 'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('base=evaluate')[0])
from state import extension_scale, realized_vol, effective_state, sma
from state import FAST_SHORT_N, FAST_LONG_N
from improvement_search import SEARCH, HOLDOUT, era
from downturn_review import exposure_control
from improvement_search_r2 import scaled
from block_bootstrap import boot, stats, REGIMES
import block_bootstrap as BB

T0 = time.time()
BB.N_BOOT = 2000


# ------------------------------------------------------------------ live fn
def live_fn(r):
    w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
    if f < 1: w = tuple(a*f for a in w[:4]) + (1 - f*sum(w[:4]),)
    return vt(w, r.get('vol_live') or r['vol'])


def live_fn_real(r):
    w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
    if f < 1: w = tuple(a*f for a in w[:4]) + (1 - f*sum(w[:4]),)
    return RF.vt(w, r.get('vol_live') or r['vol'])


for r in rr:
    a = realized_vol(qd, qqq, as_of=r['d0'], lookback=10)
    b = realized_vol(qd, qqq, as_of=r['d0'], lookback=30)
    r['vol_live'] = None if b is None else (b if a is None else max(a, b))


# ------------------------------------------------------- causal vol series
def vol_series(dates, px, n):
    """{date: annualized sample-std of the trailing n daily returns ending at
    date}; None during warm-up. Identical formula to state.realized_vol, built
    once on the daily series (BRIEFING control 3)."""
    v = [px[d] for d in dates]
    rets = [None] + [v[i]/v[i-1]-1 for i in range(1, len(v))]
    out = {}
    for i, d in enumerate(dates):
        if i < n:
            out[d] = None; continue
        w = rets[i-n+1:i+1]
        m = sum(w)/n
        out[d] = math.sqrt(sum((x-m)**2 for x in w)/(n-1)*252)
    return out


def vol_live_series(dates, px):
    s30 = vol_series(dates, px, 30); s10 = vol_series(dates, px, 10)
    return {d: (s30[d] if s30[d] is None or s10[d] is None else max(s30[d], s10[d])) for d in dates}


VOLS = {}   # (est, 'ds'|'qd') -> {date: vol}
for est in ('live', 'v30'):
    for tag, (dd, pp) in (('ds', (ds, px)), ('qd', (qd, qqq))):
        VOLS[(est, tag)] = vol_live_series(dd, pp) if est == 'live' else vol_series(dd, pp, 30)

# alignment sanity vs the harness rows
_chk = [(r['vol_live'], VOLS[('live', 'ds')][r['d']]) for r in rows[::500]]
assert all(abs(a-b) < 1e-9 for a, b in _chk), _chk
_chk = [(r['vol'], VOLS[('v30', 'ds')][r['d']]) for r in rows[::500]]
assert all(abs(a-b) < 1e-9 for a, b in _chk), _chk


# ------------------------------------------------------------ the variant
def compute_states_volbuf(dates, px, vol_by_date, k, short_n, long_n,
                          buf_min, buf_max, h=1, lam=1.0, base_buf=0.01,
                          flip=False):
    """state.compute_states() with a per-date hysteresis buffer.

    buf_t = clamp(k * vol_t * sqrt(h/252), buf_min, buf_max), blended with
    the fixed buffer as lam*buf_t + (1-lam)*base_buf. A None vol (warm-up)
    falls back to base_buf. flip=True is the sign-flip placebo: buf_t =
    k / vol_t (k re-calibrated by the caller), i.e. NARROWER in turbulence.
    The 50-vs-200 cross has no buffer, exactly as live."""
    v = [px[d] for d in dates]
    s50 = s200 = None
    out = []; bufs = []
    scale = k * math.sqrt(h/252.0)
    for i, d in enumerate(dates):
        m50, m200 = sma(v, i, short_n), sma(v, i, long_n)
        vol = vol_by_date.get(d)
        if vol is None or vol <= 0:
            buf = base_buf
        else:
            raw = (scale / vol) if flip else scale * vol
            buf = lam * min(max(raw, buf_min), buf_max) + (1-lam) * base_buf
        bufs.append(buf)
        if m200 is None:
            out.append('F'); continue
        if v[i] > m50*(1+buf): s50 = True
        elif v[i] < m50*(1-buf): s50 = False
        if v[i] > m200*(1+buf): s200 = True
        elif v[i] < m200*(1-buf): s200 = False
        cross = m50 > m200
        if s50 and s200 and cross: out.append('A')
        elif s50 and s200 and not cross: out.append('B')
        elif s50 and not s200: out.append('C')
        elif not s50 and s200: out.append('D')
        elif not s50 and not s200 and cross: out.append('E')
        else: out.append('F')
    return out, bufs


def buffer_path(dates, vol_by_date, c, buf_min, buf_max, lam=1.0, flip=False):
    out = {}
    for d in dates:
        vol = vol_by_date.get(d)
        if vol is None or vol <= 0:
            out[d] = 0.01
        else:
            raw = (c/vol) if flip else c*vol
            out[d] = lam*min(max(raw, buf_min), buf_max) + (1-lam)*0.01
    return out


def calibrate(dates, vol_by_date, buf_min, buf_max, lam=1.0, flip=False, target=0.01):
    """Bisect the scale c = k*sqrt(h/252) so the search-era mean buffer is
    `target`. Returns c. Uses only search-era dates that have a vol."""
    sd = [d for d in dates if SEARCH[0] <= d <= SEARCH[1] and vol_by_date.get(d)]
    def mean_buf(c):
        bp = buffer_path(sd, vol_by_date, c, buf_min, buf_max, lam, flip)
        return sum(bp.values())/len(sd)
    lo, hi = 0.0, 1.0
    while mean_buf(hi) < target: hi *= 2
    for _ in range(60):
        mid = (lo+hi)/2
        if mean_buf(mid) < target: lo = mid
        else: hi = mid
    return (lo+hi)/2


# ---------------------------------------------------- rows on a new series
ix_ds = {d: i for i, d in enumerate(ds)}


def rebuild(rows_src, macro_ds, fast_ds, rr_src, macro_qd, fast_qd):
    """Copy the rows and overwrite state/eff from the given per-date state
    dicts. legs, vol, gaps untouched. Mirrors leverage_under_trim.py."""
    out = []
    for r in rows_src:
        q = dict(r); q['state'] = macro_ds[r['d']]
        q['eff'] = effective_state(q['state'], fast_ds[r['d']]); out.append(q)
    outr = []
    for r in rr_src:
        q = dict(r); q['state'] = macro_qd[r['d0']]
        q['eff'] = effective_state(q['state'], fast_qd[r['d0']]); outr.append(q)
    return out, outr


def state_series(dates, px, vol_ds, cfg, which):
    """Return (macro dict, fast dict, mean buffer info) on `dates` for a config
    dict cfg = {c, buf_min, buf_max, lam, flip} applied to `which` in
    {'macro','fast','both','none'}."""
    if cfg is None or which == 'none':
        m = compute_states(dates, px); f = compute_states(dates, px, short_n=FAST_SHORT_N, long_n=FAST_LONG_N)
        return dict(zip(dates, m)), dict(zip(dates, f))
    kw = dict(k=cfg['c'], h=252, buf_min=cfg['buf_min'], buf_max=cfg['buf_max'], lam=cfg.get('lam', 1.0), flip=cfg.get('flip', False))
    if which in ('macro', 'both'):
        m, _ = compute_states_volbuf(dates, px, vol_ds, short_n=50, long_n=200, **kw)
    else:
        m = compute_states(dates, px)
    if which in ('fast', 'both'):
        f, _ = compute_states_volbuf(dates, px, vol_ds, short_n=FAST_SHORT_N, long_n=FAST_LONG_N, **kw)
    else:
        f = compute_states(dates, px, short_n=FAST_SHORT_N, long_n=FAST_LONG_N)
    return dict(zip(dates, m)), dict(zip(dates, f))


# ------------------------------------------------------ state diagnostics
def transitions(seq_dates, seq):
    """list of (index, from, to)"""
    return [(i, seq[i-1], seq[i]) for i in range(1, len(seq)) if seq[i] != seq[i-1]]


def whipsaws(seq, N):
    """Transitions X->Y at i that are followed by a return to X within N
    sessions (any path back to X)."""
    n = 0
    for i in range(1, len(seq)):
        if seq[i] != seq[i-1]:
            x = seq[i-1]
            if any(seq[j] == x for j in range(i+1, min(len(seq), i+N+1))):
                n += 1
    return n


def diag(rowlist, key='state'):
    seq = [r[key] for r in rowlist]; dates_ = [r['d'] for r in rowlist]
    yrs = (len(seq)/252.0)
    tr = transitions(dates_, seq)
    tis = {s: seq.count(s)/len(seq) for s in 'ABCDEF'}
    return dict(n_tr=len(tr), tr_py=len(tr)/yrs, w5=whipsaws(seq, 5), w10=whipsaws(seq, 10), tis=tis)


def diag_line(rowlist, key='state'):
    d = diag(rowlist, key)
    t = ' '.join(f"{s}{d['tis'][s]*100:4.1f}" for s in 'ABCDEF')
    return f"tr/yr {d['tr_py']:5.2f} (n={d['n_tr']:3d})  whip5 {d['w5']:3d} whip10 {d['w10']:3d}  | {t}"


# ------------------------------------------------------------- evaluation
def full_eval(rows_v, rr_v):
    ev = evaluate(rows_v, live_fn); e = RF.eval_real(rr_v, live_fn_real)
    ev['real'] = e
    return ev


def fmt(lab, ev, base=None):
    e = ev['real']
    both = ''
    if base is not None:
        both = ' BOTH' if ev['s_sharpe'] > base['s_sharpe'] and ev['h_sharpe'] > base['h_sharpe'] else ''
    return (f"{lab:<34} {ev['cagr']*100:5.2f}% {ev['sharpe']:.3f} {ev['mdd']*100:5.1f}%  "
            f"S {ev['s_sharpe']:.3f} H {ev['h_sharpe']:.3f} exp {ev['risky']:.3f} | "
            f"real {e['cagr']*100:5.2f}% {e['sharpe']:.3f} {e['mdd']*100:5.1f}%{both}")


def my_exposure_control(rows_orig, target_exp):
    """Scale the FULL live design (overlay+trim+max(10,30) VT) on the ORIGINAL
    state series until its deployed capital equals target_exp."""
    lo, hi = 0.0, 1.0
    while run(rows_orig, scaled(live_fn, hi))[1] < target_exp and hi < 8: lo, hi = hi, hi*2
    for _ in range(40):
        mid = (lo+hi)/2
        if run(rows_orig, scaled(live_fn, mid))[1] < target_exp: lo = mid
        else: hi = mid
    k = (lo+hi)/2
    ev = evaluate(rows_orig, scaled(live_fn, k)); ev['k'] = k
    ev['exp_achieved'] = run(rows_orig, scaled(live_fn, k))[1]
    return k, ev


# ============================================================== MAIN
def main():
    print("=" * 100)
    print("vol_hysteresis -- volatility-scaled hysteresis buffer for the six-state classifier")
    print("=" * 100)

    # sanity 1: the variant with a constant buffer reproduces compute_states
    m_const, _ = compute_states_volbuf(ds, px, {d: 1.0 for d in ds}, k=0.01, h=252, short_n=50, long_n=200, buf_min=0.01, buf_max=0.01)
    assert m_const == compute_states(ds, px), "constant-buffer variant must equal live classifier"
    f_const, _ = compute_states_volbuf(ds, px, {d: 1.0 for d in ds}, k=0.01, h=252, short_n=20, long_n=100, buf_min=0.01, buf_max=0.01)
    assert f_const == compute_states(ds, px, short_n=20, long_n=100)

    # sanity 2: reproduce live on rebuilt-but-unchanged rows
    m0, f0 = state_series(ds, px, None, None, 'none'); mq0, fq0 = state_series(qd, qqq, None, None, 'none')
    rows0, rr0 = rebuild(rows, m0, f0, rr, mq0, fq0)
    assert all(a['state'] == b['state'] and a['eff'] == b['eff'] for a, b in zip(rows0, rows))
    assert all(a['state'] == b['state'] and a['eff'] == b['eff'] for a, b in zip(rr0, rr))
    base = full_eval(rows0, rr0)
    print("\nLIVE (unchanged classifier, rebuilt rows) -- must be 22.12/0.938/-32.8, S 1.150 H 0.780, real 30.67/1.260/-25.3")
    print(fmt('LIVE', base))
    print("   macro:", diag_line(rows0, 'state'))
    print("   eff  :", diag_line(rows0, 'eff'))
    base_rets = run(rows0, live_fn)[0]

    # --------------------------------------------------- vol / buffer shapes
    SHAPES = [
        # name, est, buf_min, buf_max, lam, flip
        ('live-vol, clamp 0.2-4%',  'live', 0.002, 0.04, 1.0, False),
        ('live-vol, clamp 0.5-2%',  'live', 0.005, 0.02, 1.0, False),
        ('live-vol, unclamped',     'live', 0.0,   1.0,  1.0, False),
        ('live-vol, 50% blend w/1%', 'live', 0.0,  1.0,  0.5, False),
        ('vol30, clamp 0.2-4%',     'v30',  0.002, 0.04, 1.0, False),
        ('vol30, clamp 0.5-2%',     'v30',  0.005, 0.02, 1.0, False),
        ('vol30, unclamped',        'v30',  0.0,   1.0,  1.0, False),
    ]
    cfgs = {}
    print("\nCALIBRATION: c = k*sqrt(h/252) bisected so the SEARCH-era mean buffer is 1.000%")
    print(f"{'shape':<28}{'c':>8}{'k(h=1)':>9}{'k(h=5)':>9}{'k(h=10)':>9}{'srch mean':>10}{'hold mean':>10}{'min':>7}{'p5':>7}{'p50':>7}{'p95':>7}{'max':>7}")
    for name, est, bmin, bmax, lam, flip in SHAPES:
        vd = VOLS[(est, 'ds')]
        c = calibrate(ds, vd, bmin, bmax, lam, flip)
        bp = buffer_path(ds, vd, c, bmin, bmax, lam, flip)
        s_ = [bp[d] for d in ds if SEARCH[0] <= d and vd.get(d)]
        h_ = [bp[d] for d in ds if HOLDOUT[0] <= d <= HOLDOUT[1] and vd.get(d)]
        allb = sorted(bp[d] for d in ds if d >= HOLDOUT[0] and vd.get(d))
        q = lambda p: allb[int(p*(len(allb)-1))]
        ks = [c/math.sqrt(h/252) for h in (1, 5, 10)]
        print(f"{name:<28}{c:8.4f}{ks[0]:9.3f}{ks[1]:9.3f}{ks[2]:9.3f}{sum(s_)/len(s_)*100:9.3f}%{sum(h_)/len(h_)*100:9.3f}%"
              f"{allb[0]*100:6.2f}%{q(.05)*100:6.2f}%{q(.5)*100:6.2f}%{q(.95)*100:6.2f}%{allb[-1]*100:6.2f}%")
        cfgs[name] = dict(c=c, buf_min=bmin, buf_max=bmax, lam=lam, flip=flip, est=est)
    print("NOTE: after calibrating the mean, h and k are one constant c -- h=1/5/10 give the SAME buffer path; only k's label changes.")

    # ----------------------------------------------------- reference: fixed
    print("\nREFERENCE (not candidates): fixed buffers, both classifiers, full live design")
    print(f"{'variant':<34} {'CAGR':>6} {'Sharpe':>5} {'MaxDD':>6}")
    ref = {}
    for b in (0.005, 0.0075, 0.01, 0.0125, 0.015, 0.02):
        m = dict(zip(ds, compute_states(ds, px, buf=b))); f = dict(zip(ds, compute_states(ds, px, buf=b, short_n=20, long_n=100)))
        mq = dict(zip(qd, compute_states(qd, qqq, buf=b))); fq = dict(zip(qd, compute_states(qd, qqq, buf=b, short_n=20, long_n=100)))
        rv, rrv = rebuild(rows, m, f, rr, mq, fq); ev = full_eval(rv, rrv); ref[b] = ev
        print(fmt(f'fixed buf {b*100:.2f}% (macro+fast)', ev, base))
        print("   macro:", diag_line(rv, 'state'))

    # ------------------------------------------------------- the candidates
    print("\nCANDIDATES: vol-scaled buffer (search-era mean 1%), applied to macro / fast / both")
    results = []
    for which in ('macro', 'fast', 'both'):
        print(f"\n--- applied to: {which} ---")
        for name, cfg in cfgs.items():
            m, f = state_series(ds, px, VOLS[(cfg['est'], 'ds')], cfg, which)
            mq, fq = state_series(qd, qqq, VOLS[(cfg['est'], 'qd')], cfg, which)
            rv, rrv = rebuild(rows, m, f, rr, mq, fq)
            ev = full_eval(rv, rrv)
            ev['rows'] = rv; ev['rr'] = rrv; ev['name'] = f"{which}: {name}"; ev['which'] = which; ev['cfg'] = cfg
            results.append(ev)
            print(fmt(ev['name'], ev, base))
            print("   macro:", diag_line(rv, 'state'))
            print("   eff  :", diag_line(rv, 'eff'))

    n_cand = len(results)
    both = [ev for ev in results if ev['s_sharpe'] > base['s_sharpe'] and ev['h_sharpe'] > base['h_sharpe']]
    real_ok = [ev for ev in both if ev['real']['sharpe'] > base['real']['sharpe']]
    print(f"\nCANDIDATE COUNT: {n_cand} vol-scaled variants tested; {len(both)} beat live on BOTH search and holdout Sharpe; "
          f"{len(real_ok)} of those also beat live real Sharpe {base['real']['sharpe']:.3f}.")
    # by application
    for which in ('macro', 'fast', 'both'):
        sub = [ev for ev in results if ev['which'] == which]
        print(f"   {which:<6}: {sum(1 for ev in sub if ev['s_sharpe']>base['s_sharpe'])}/{len(sub)} beat search, "
              f"{sum(1 for ev in sub if ev['h_sharpe']>base['h_sharpe'])}/{len(sub)} beat holdout, "
              f"{sum(1 for ev in sub if ev['real']['sharpe']>base['real']['sharpe'])}/{len(sub)} beat real, "
              f"mean dSharpe full {sum(ev['sharpe']-base['sharpe'] for ev in sub)/len(sub):+.3f}")

    # ------------------------------------------------ year-by-year on the best
    top = sorted(results, key=lambda e: (e['s_sharpe'] > base['s_sharpe']) + (e['h_sharpe'] > base['h_sharpe']) + (e['real']['sharpe'] > base['real']['sharpe']) + 0.001*e['sharpe'], reverse=True)[:3]
    def byyear(rowlist):
        rets, _ = run(rowlist, live_fn); by = {}
        for r, x in zip(rowlist, rets): by[r['d'][:4]] = by.get(r['d'][:4], 0) + math.log1p(x)
        return {y: math.expm1(x) for y, x in by.items()}
    by0 = byyear(rows0)
    print("\nYEAR-BY-YEAR (proxy, full live design) for live and the top-3 variants (ranked by both-era + real hits)")
    print("year   live  " + ''.join(f"{'v'+str(i+1):>8}" for i in range(len(top))))
    tops = [byyear(ev['rows']) for ev in top]
    for y in sorted(by0):
        print(f"{y}  {by0[y]*100:+6.1f}  " + ''.join(f"{(t[y]-by0[y])*100:+8.1f}" for t in tops))
    for i, ev in enumerate(top): print(f"   v{i+1} = {ev['name']}")

    # ------------------------------------------------------ controls on survivors
    survivors = both
    if not survivors:
        print("\nNo variant beat live on both eras. Controls below are run on the top-3 by rank anyway, to document WHERE they fail.")
        survivors = top
    print("\nEXPOSURE CONTROL (deployed capital): candidate vs the FULL live design scaled to the same average exposure")
    for ev in survivors:
        k, c = my_exposure_control(rows0, ev['risky'])
        k2, c2 = exposure_control(rows0, ev['risky'])
        verdict = 'PASS' if ev['sharpe'] > c['sharpe'] else 'FAIL'
        print(f"  {ev['name']:<40} cand {ev['sharpe']:.3f} @exp {ev['risky']:.4f} | live_fn scaled k={k:.3f} -> {c['sharpe']:.3f} (S {c['s_sharpe']:.3f} H {c['h_sharpe']:.3f}) {verdict}"
              f" | harness exposure_control k={k2:.3f} Sharpe {c2['sharpe']:.3f} matched={c2['exp_matched']}")

    # --------------------------------------------------------------- placebos
    print("\nPLACEBO 1: sign-flipped buffer (buf = c/vol, NARROWER in turbulence), re-calibrated to search-era mean 1%")
    for which in ('macro', 'fast', 'both'):
        for est in ('live', 'v30'):
            cfg = dict(c=calibrate(ds, VOLS[(est, 'ds')], 0.002, 0.04, 1.0, True), buf_min=0.002, buf_max=0.04, lam=1.0, flip=True, est=est)
            m, f = state_series(ds, px, VOLS[(est, 'ds')], cfg, which); mq, fq = state_series(qd, qqq, VOLS[(est, 'qd')], cfg, which)
            rv, rrv = rebuild(rows, m, f, rr, mq, fq); ev = full_eval(rv, rrv)
            print(fmt(f"FLIP {which}: {est}, clamp 0.2-4%", ev, base))
            print("   macro:", diag_line(rv, 'state'))

    print("\nPLACEBO 2: year-block-shuffled vol series (same c, clamp 0.2-4%, live-vol), 30 seeds, applied to 'both'")
    print("   A real vol-timing effect must beat the shuffled distribution; a shuffled series has the same buffer MAGNITUDE but no relation to the tape.")
    def shuffled_vol(dates, vd, seed):
        rng = random.Random(seed)
        yrs = sorted({d[:4] for d in dates})
        blocks = {y: [vd[d] for d in dates if d[:4] == y] for y in yrs}
        order = yrs[:]; rng.shuffle(order)
        flat = [x for y in order for x in blocks[y]]
        return {d: flat[i] for i, d in enumerate(dates)}
    for which in ('both', 'macro', 'fast'):
        name = 'live-vol, clamp 0.2-4%'; cfg = cfgs[name]
        real_ev = next(e for e in results if e['name'] == f"{which}: {name}")
        sh, hs, ss, rs = [], [], [], []
        for seed in range(30):
            vsd = shuffled_vol(ds, VOLS[('live', 'ds')], seed); vsq = shuffled_vol(qd, VOLS[('live', 'qd')], seed)
            m, f = state_series(ds, px, vsd, cfg, which); mq, fq = state_series(qd, qqq, vsq, cfg, which)
            rv, rrv = rebuild(rows, m, f, rr, mq, fq); ev = full_eval(rv, rrv)
            sh.append(ev['sharpe']); ss.append(ev['s_sharpe']); hs.append(ev['h_sharpe']); rs.append(ev['real']['sharpe'])
        def pr(a, x):
            a = sorted(a); return f"med {a[len(a)//2]:.3f} [{a[1]:.3f},{a[-2]:.3f}] P(placebo>=real)={sum(1 for v in a if v >= x)/len(a):.2f}"
        print(f"  {which:<6} real variant: full {real_ev['sharpe']:.3f} S {real_ev['s_sharpe']:.3f} H {real_ev['h_sharpe']:.3f} real {real_ev['real']['sharpe']:.3f}")
        print(f"         placebo full  : {pr(sh, real_ev['sharpe'])}")
        print(f"         placebo search: {pr(ss, real_ev['s_sharpe'])}")
        print(f"         placebo hold  : {pr(hs, real_ev['h_sharpe'])}")
        print(f"         placebo real  : {pr(rs, real_ev['real']['sharpe'])}")
        print(f"         live          : full {base['sharpe']:.3f} S {base['s_sharpe']:.3f} H {base['h_sharpe']:.3f} real {base['real']['sharpe']:.3f}")

    # ------------------------------------------- block bootstrap + LORO
    print(f"\nBLOCK BOOTSTRAP ({BB.N_BOOT} resamples, blocks 20/60) and LEAVE-ONE-REGIME-OUT, candidate minus live, proxy daily")
    for ev in survivors:
        a = run(ev['rows'], live_fn)[0]; b = base_rets
        la, sa = stats(a); lb, sb = stats(b)
        print(f"  {ev['name']}  point: {(la-lb)*100:+.2f}pp/yr log-return, {sa-sb:+.3f} Sharpe")
        for blk in (20, 60):
            l1, l2, pl, s1, s2, ps = boot(a, b, blk, seed=blk*7+1)
            print(f"     block {blk:>2}d: log-ret 95% CI [{l1*100:+.2f},{l2*100:+.2f}] P(<=0)={pl:.3f}  Sharpe 95% CI [{s1:+.3f},{s2:+.3f}] P(<=0)={ps:.3f}")
        for rlab, a0, b0 in REGIMES:
            keep = [i for i, r in enumerate(ev['rows']) if not (a0 <= r['d'] <= b0)]
            _, xa = stats([a[i] for i in keep]); _, xb = stats([b[i] for i in keep])
            print(f"     drop {rlab:<24} Sharpe {xa-xb:+.3f}")

    # ------------------------------------------- WHY: where do whipsaws live?
    print("\nDIAGNOSTIC: where the LIVE classifier's whipsaws occur, by vol tercile (vol_live at the transition date)")
    print("   The hypothesis needs whipsaws concentrated in the HIGH-vol tercile (where a vol-scaled buffer widens).")
    vl = sorted(r['vol_live'] for r in rows0)
    t1, t2 = vl[len(vl)//3], vl[2*len(vl)//3]
    def terc(v): return 0 if v < t1 else (1 if v < t2 else 2)
    v_ev = next(e for e in results if e['name'] == 'both: live-vol, clamp 0.2-4%')
    for lab, rl in (('LIVE', rows0), ('VARIANT both/live-vol/0.2-4%', v_ev['rows'])):
        for key in ('state', 'eff'):
            seq = [r[key] for r in rl]
            days = [0, 0, 0]; trs = [0, 0, 0]; w5 = [0, 0, 0]; w10 = [0, 0, 0]
            for i, r in enumerate(rl):
                t = terc(r['vol_live']); days[t] += 1
                if i and seq[i] != seq[i-1]:
                    trs[t] += 1; x = seq[i-1]
                    if any(seq[j] == x for j in range(i+1, min(len(seq), i+6))): w5[t] += 1
                    if any(seq[j] == x for j in range(i+1, min(len(seq), i+11))): w10[t] += 1
            print(f"   {lab:<30} {key:<5} tercile bounds vol<{t1*100:.1f}% / <{t2*100:.1f}% / above:  "
                  f"days {days}  transitions {trs}  whip5 {w5}  whip10 {w10}  "
                  f"whip10 per 1000 days {[round(1000*w/d, 1) for w, d in zip(w10, days)]}")
    # the vol-scaled buffer on those same dates
    cfg = cfgs['live-vol, clamp 0.2-4%']; bp = buffer_path(ds, VOLS[('live', 'ds')], cfg['c'], cfg['buf_min'], cfg['buf_max'])
    bt = [[], [], []]
    for r in rows0: bt[terc(r['vol_live'])].append(bp[r['d']])
    print(f"   mean vol-scaled buffer by tercile: {[round(sum(b)/len(b)*100, 2) for b in bt]} %  (fixed live: 1.00 in all three)")

    print("\nDIAGNOSTIC: 2011 (the documented whipsaw year), macro transitions, live vs 'both: live-vol, clamp 0.2-4%'")
    v_ev = next(e for e in results if e['name'] == 'both: live-vol, clamp 0.2-4%')
    for lab, rl in (('live', rows0), ('variant', v_ev['rows'])):
        seq = [r['state'] for r in rl if r['d'][:4] == '2011']; dd = [r['d'] for r in rl if r['d'][:4] == '2011']
        tr = [(dd[i], seq[i-1], seq[i]) for i in range(1, len(seq)) if seq[i] != seq[i-1]]
        print(f"   {lab:<8} n={len(tr):2d} whip10={whipsaws(seq, 10):2d}  " + ' '.join(f"{d[5:]}:{a}>{b}" for d, a, b in tr))
    by_v = byyear(v_ev['rows'])
    print(f"   2011 return: live {by0['2011']*100:+.1f}%  variant {by_v['2011']*100:+.1f}%")

    print("\nBOOTSTRAP + LORO on the sign-FLIPPED placebo that passed both eras (FLIP macro: v30) -- is the placebo itself inside noise?")
    cfg = dict(c=calibrate(ds, VOLS[('v30', 'ds')], 0.002, 0.04, 1.0, True), buf_min=0.002, buf_max=0.04, lam=1.0, flip=True, est='v30')
    m, f = state_series(ds, px, VOLS[('v30', 'ds')], cfg, 'macro'); mq, fq = state_series(qd, qqq, VOLS[('v30', 'qd')], cfg, 'macro')
    rv, rrv = rebuild(rows, m, f, rr, mq, fq); a = run(rv, live_fn)[0]; b = base_rets
    la, sa = stats(a); lb, sb = stats(b)
    print(f"  point: {(la-lb)*100:+.2f}pp/yr log-return, {sa-sb:+.3f} Sharpe")
    for blk in (20, 60):
        l1, l2, pl, s1, s2, ps = boot(a, b, blk, seed=blk*11+3)
        print(f"     block {blk:>2}d: log-ret 95% CI [{l1*100:+.2f},{l2*100:+.2f}] P(<=0)={pl:.3f}  Sharpe 95% CI [{s1:+.3f},{s2:+.3f}] P(<=0)={ps:.3f}")
    for rlab, a0, b0 in REGIMES:
        keep = [i for i, r in enumerate(rv) if not (a0 <= r['d'] <= b0)]
        _, xa = stats([a[i] for i in keep]); _, xb = stats([b[i] for i in keep])
        print(f"     drop {rlab:<24} Sharpe {xa-xb:+.3f}")

    print(f"\n[{time.time()-T0:.0f}s]")


if __name__ == '__main__':
    main()
