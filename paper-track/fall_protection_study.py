"""Protection DURING the fall, inside state A. Research only.

Owner (2026-09-22), after a_ratio_study section 6 showed the extension trim is
off on 19/20 of the worst A days: "consider how we can add protection during
the fall".

Already ruled out on this record (not re-run): NAV/realised-loss brakes
(structurally late), a faster macro classifier end to end (every faster pair
worse on both axes), wider D gates (sell after the fall), a faster vol
estimator (edge was COVID only), VIX/VXN/VRP inputs, fast-state pair cells
(AD/AE/AF cash: no single pair improves real), bond sleeves, trim hysteresis.

PRE-REGISTERED here, 12 arms, scope = effective state A only, everything else
live:
  M  TRIM MEMORY       votes = max(votes over the last N sessions), N = 5/10/20/40.
                       Directly answers "the trim switches off as it falls".
  S  SHORT DRAWDOWN    QQQ close >= X% below its 20-session closing high,
                       X = 4/6/8%;  action HALF (TQQQ 50 -> 25, to core) or
                       ALL (TQQQ -> core, A row becomes 100% core).
  T  SHORT TREND       QQQ close < its 10-day SMA; action HALF or ALL.
Every arm is decided on the close, like everything else, and a flag change is a
rebalance trigger.

Scored against the FLAT-LEVERAGE NULL (live x k): edge = arm MaxDD minus the
null's MaxDD at the arm's CAGR, POSITIVE = shallower than just holding less.
Also excess-of-BOXX Sharpe (full / search / holdout), paired block bootstrap
vs live, and depth inside the worst live episodes.

Usage: python3 paper-track/fall_protection_study.py
"""
import os, sys, io, math, time, contextlib
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO_ROOT); sys.path.insert(0, 'paper-track')
os.environ.setdefault('TDT_STAGE', 'none'); os.environ['DDS_STAGE'] = 'none'
T0 = time.time()
LOG = 'paper-track/research_notes/fall_protection_study_run.log'
_lf = open(LOG, 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); _lf.write(s + '\n'); _lf.flush()

with contextlib.redirect_stdout(io.StringIO()):
    import drawdown_study as DS
    import d_substate_fresh as DSF
from d_substate_fresh import rows, RDAYS, SEARCH, HOLDOUT
from drift_band_test import annual_stats, ONE_WAY_SPREAD
from block_bootstrap import boot
from state import extension_votes, VOL_TARGET_PA, REBALANCE_DRIFT_BAND, TARGET_WEIGHTS
import monthly_returns as MR

TDT = DS.TDT; H = ('real', 'proxy')
W0 = dict(TARGET_WEIGHTS); CASH = (0.0, 0.0, 0.0, 0.0, 1.0)
PX = {'real': TDT.RQQQ, 'proxy': DSF._QQQ_FULL}
PXD = {h: sorted(PX[h]) for h in H}
PXI = {h: {d: i for i, d in enumerate(PXD[h])} for h in H}

def qfeat(h, d, kind, n):
    ds = PXD[h]; px = PX[h]; i = PXI[h][d]
    if kind == 'high': return px[d] / max(px[ds[j]] for j in range(max(0, i - n + 1), i + 1)) - 1
    if kind == 'sma':  return px[d] / (sum(px[ds[j]] for j in range(i - n + 1, i + 1)) / n) - 1

_QV = {}
def qvol(h, d, n):
    """Annualised sd of QQQ daily log returns over the n sessions ending on close d."""
    k = (h, d, n)
    if k not in _QV:
        ds = PXD[h]; px = PX[h]; i = PXI[h][d]
        r = [math.log(px[ds[j]] / px[ds[j - 1]]) for j in range(i - n + 1, i + 1)]
        m = sum(r) / n
        _QV[k] = (sum((x - m) ** 2 for x in r) / (n - 1)) ** 0.5 * math.sqrt(252)
    return _QV[k]

def sim(h, arm=None, detail=False):
    """drawdown_study.sim (live design) with one A-state hook. arm = (kind, param, action)."""
    if h == 'real':
        days = RDAYS[:-1]; ow = MR.ONE_WAY; info = lambda d: DS.RINFO[d]; legs = lambda d: DS.RLEG_RET[d]
        bp = DS.BP_R; keyf = lambda I, v, g: (I['eff'], v, g)
    else:
        days = [r['d'] for r in rows]; ow = ONE_WAY_SPREAD; RW = {r['d']: r for r in rows}
        info = lambda d: RW[d]; legs = lambda d: DS.PLEG[d]; bp = DS.BP_Q
        keyf = lambda I, v, g: (I['state'], I['agree'])
    held = prev = None; out = []; vhist = []; risky = 0.0; nreb = 0; nflag = 0
    latch = 0
    for d in days:
        I = info(d)
        st = I['st'] if h == 'real' else I['state']
        eff = I['eff']; gaps = I['gaps']; vol = I['vol']
        g200 = gaps.get(200); b = bp.get(d)
        gate = (st == 'D') and ((b is not None and b < 0.20) or (g200 is not None and g200 < 0.02))
        v = 0; flag = 0
        if gate or st == 'E':
            row = CASH; latch = 0
        elif eff == 'A':
            v = extension_votes(eff, gaps)
            if arm and arm[0] == 'X' and len(arm) > 3:   # custom vote thresholds for (100, 150, 200)
                v = sum(1 for n, th in zip((100, 150, 200), arm[3]) if gaps.get(n) is not None and gaps[n] > th)
            vh = v
            if arm and arm[0] == 'X':
                # trim SHAPE test: arm = ('X', 'live'|'latch', schedule of (spmo, tqqq, cash) at 0..3 votes)
                if arm[1] == 'latch':
                    latch = max(latch, v); vh = latch
            if arm and arm[0] == 'V':
                # votes rise at once; they may only FALL when volatility says the market is calm
                v10 = qvol(h, d, 10)
                ok = (v10 < vol) if arm[1] == 'v10<v30' else (v10 < VOL_TARGET_PA)
                if v >= latch or ok: latch = v
                vh = latch
            if arm and arm[0] == 'R':
                # votes rise at once; they may only FALL on a close that clears the release test
                ok = (qfeat(h, d, 'sma', 10) > 0) if arm[1] == 'sma10' else (qfeat(h, d, 'high', 20) >= 0)
                if v >= latch or ok: latch = v
                vh = latch
            if arm and arm[0] == 'L':
                latch = max(latch, v); vh = latch
            if arm and arm[0] == 'M':
                vh = max([v] + vhist[-(arm[1] - 1):]) if arm[1] > 1 else v
            f = max(0.0, 1.0 - (1.0 / 3.0) * vh)
            w = list(W0['A'])
            if arm and arm[0] in ('S', 'T'):
                x = qfeat(h, d, 'high', 20) if arm[0] == 'S' else qfeat(h, d, 'sma', 10)
                hit = (x <= -arm[1]) if arm[0] == 'S' else (x < 0)
                if hit:
                    flag = 1; mv = w[1] * (0.5 if arm[2] == 'HALF' else 1.0)
                    w[1] -= mv; w[0] += mv
            row = tuple(a * f for a in w[:4]) + (1 - f * sum(w[:4]),)
            if arm and arm[0] == 'X':
                sc, tq, ca = arm[2][min(vh, 3)]
                row = (sc, tq, 0.0, 0.0, ca)
            v = (vh, flag)
        else:
            row = W0[eff]; latch = 0
        vhist.append(extension_votes(eff, gaps) if eff == 'A' else 0)
        m = 1.0 if not vol else min(1.0, VOL_TARGET_PA / vol)
        t = tuple(x * m for x in row[:4]) + (1.0 - sum(row[:4]) * m,)
        key = keyf(I, v, gate) + ((flag,) if arm else ())
        cost = 0.0
        if held is None: held = list(t); nreb += 1
        else:
            drift = sum(abs(t[j] - held[j]) for j in range(5))
            if key != prev or drift > REBALANCE_DRIFT_BAND:
                cost = ow * drift; held = list(t); nreb += 1
        lr = tuple(legs(d))
        gg = sum(held[j] * lr[j] for j in range(5)); net = gg - cost
        risky += sum(held[:4]); nflag += flag
        out.append(dict(d=d, net=net, eff=eff, st=st, gate=gate, flag=flag, held=list(held), lr=lr, v=v, t=t) if detail else net)
        dn = 1 + gg
        if dn > 0: held = [held[j] * (1 + lr[j]) / dn for j in range(5)]
        prev = key
    n = len(days)
    return out, risky / n, nreb / (n / 252.0), nflag

# the untouched hook must reproduce drawdown_study.sim exactly
for h in H:
    a = sim(h)[0]; b = DS.sim(h)[0]
    assert len(a) == len(b) and max(abs(x - y) for x, y in zip(a, b)) < 1e-12, h

DATES = {'real': RDAYS[:-1], 'proxy': [r['d'] for r in rows]}
CASHR = {h: [x['lr'][4] for x in DS.sim(h, detail=True)[0]] for h in H}
def _sh(x):
    m = sum(x) / len(x); v = (sum((a - m) ** 2 for a in x) / (len(x) - 1)) ** 0.5
    return m * math.sqrt(252) / v if v else float('nan')
def xs(h, ser, lo=None, hi=None):
    return [a - c for a, c, d in zip(ser, CASHR[h], DATES[h]) if (lo is None or d >= lo) and (hi is None or d <= hi)]
def mdd_window(ser, dates, lo, hi):
    nav = pk = 1.0; m = 0.0
    for r, d in zip(ser, dates):
        if lo <= d <= hi: nav *= 1 + r; pk = max(pk, nav); m = min(m, nav / pk - 1)
    return m
def score(h, arm=None):
    ser, expo, reb, nf = sim(h, arm)
    c, _, m = annual_stats(ser)
    return dict(cagr=c, mdd=m, exp=expo, reb=reb, nf=nf, ser=ser,
                F=_sh(xs(h, ser)), S=_sh(xs(h, ser, lo=SEARCH[0])),
                H=(_sh(xs(h, ser, hi=HOLDOUT[1])) if h == 'proxy' else float('nan')))

LIVE = {h: score(h) for h in H}
FRONT = {}
for h in H:
    pts = []
    for k in (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0, 1.1, 1.2):
        ser = DS.sim(h, scale=k)[0]; c, _, m = annual_stats(ser); pts.append((c, m))
    FRONT[h] = sorted(pts)
def front(h, c):
    p = FRONT[h]
    if c <= p[0][0]: return p[0][1]
    if c >= p[-1][0]: return p[-1][1]
    for i in range(1, len(p)):
        if c <= p[i][0]:
            f = (c - p[i-1][0]) / (p[i][0] - p[i-1][0]); return p[i-1][1] + f * (p[i][1] - p[i-1][1])

# worst live episodes, per harness
EPIS = {'real': [('2021-11-18', '2023-01-17', '2021-23 bear'), ('2025-02-18', '2025-03-03', 'Feb-Mar 2025'),
                 ('2023-09-13', '2023-10-26', 'Sep-Oct 2023'), ('2018-08-28', '2018-12-07', 'Q4 2018'),
                 ('2020-02-19', '2020-03-23', 'COVID')],
        'proxy': [('2004-12-13', '2005-10-31', '2005'), ('2000-07-14', '2002-08-28', 'dot-com'),
                  ('2007-11-05', '2009-03-13', 'GFC'), ('2021-11-18', '2023-01-18', '2021-23 bear'),
                  ('2020-02-19', '2020-03-23', 'COVID')]}

ARMS = ([('M', n, None) for n in (5, 10, 20, 40)] +
        [('S', x, a) for x in (0.04, 0.06, 0.08) for a in ('HALF', 'ALL')] +
        [('T', 10, a) for a in ('HALF', 'ALL')])
def lab(a):
    return {'M': f'trim memory {a[1]}d', 'S': f'QQQ {int(a[1]*100)}% off 20d high, {a[2]}',
            'T': f'QQQ < 10d SMA, {a[2]}'}[a[0]]

log('=' * 150)
log('RESEARCH LINE fall_protection_study (2026-09-22): protection DURING the fall, inside state A. 12 pre-registered arms.')
log('=' * 150)
for h in H:
    L = LIVE[h]
    log(f"  LIVE {h:<6} {L['cagr']*100:.2f}% / MaxDD {L['mdd']*100:.1f}% / exSh F {L['F']:.3f} S {L['S']:.3f} H {L['H']:.3f} / reb {L['reb']:.1f}")
RES = {}
for h in H:
    log(f"\n  {h.upper()}   edge = MaxDD vs flat-leverage null at the same CAGR (+ = shallower than holding less)")
    log(f"  {'arm':<30}{'CAGR':>8}{'dCAGR':>8}{'MaxDD':>8}{'dDD':>7}{'EDGE':>7}{'exSh F':>8}{'dF':>8}{'dS':>7}{'dH':>7}{'reb':>6}{'on%':>6}  worst live episodes (arm vs live)")
    for a in [None] + ARMS:
        e = LIVE[h] if a is None else score(h, a); RES[(h, a)] = e
        edge = (e['mdd'] - front(h, e['cagr'])) * 100
        eps = '  '.join(f"{nm} {mdd_window(e['ser'], DATES[h], lo, hi)*100:.1f}/{mdd_window(LIVE[h]['ser'], DATES[h], lo, hi)*100:.1f}"
                        for lo, hi, nm in EPIS[h])
        dH = f"{e['H']-LIVE[h]['H']:+7.3f}" if h == 'proxy' else '     - '
        log(f"  {('LIVE' if a is None else lab(a)):<30}{e['cagr']*100:7.2f}%{(e['cagr']-LIVE[h]['cagr'])*100:+8.2f}{e['mdd']*100:7.1f}%"
            f"{(e['mdd']-LIVE[h]['mdd'])*100:+7.1f}{edge:+7.2f}{e['F']:8.3f}{e['F']-LIVE[h]['F']:+8.3f}{e['S']-LIVE[h]['S']:+7.3f}{dH}"
            f"{e['reb']:6.1f}{e['nf']/len(DATES[h])*100:5.1f}%  {eps}")

log("\n  PAIRED BLOCK BOOTSTRAP vs live (60-day blocks, 2000 draws): excess-Sharpe 95% CI and P(not better)")
for a in ARMS:
    parts = []
    for h in H:
        l1, l2, pl, s1, s2, ps = boot(xs(h, RES[(h, a)]['ser']), xs(h, LIVE[h]['ser']), 60,
                                      seed=(sum(map(ord, lab(a))) * 31 + len(h)) & 0xffff)
        parts.append(f"{h} [{s1:+.3f}, {s2:+.3f}] P {ps:.2f}")
    log(f"  {lab(a):<30} " + '   '.join(parts))
log(f"\n  done in {time.time()-T0:.0f}s")
