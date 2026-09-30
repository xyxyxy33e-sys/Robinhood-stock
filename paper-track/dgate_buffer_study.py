"""Owner (2026-09-30), after February 2026's D-gate flip-flop: "run the gate buffer test".

In Feb 2026 QQQ sat ~2% above its 200-day, on the D gate's gap200 line, and the gate
flipped QLD <-> BOXX four times in three weeks (two flips helped, two hurt; net ~0).
The question: does a buffer zone (hysteresis) on the gate's switch-off stop the
flip-flop without costing return or protection? Gate hysteresis has not been tested
before (trim hysteresis was, and was rejected; wider gates were, and were rejected --
this is different: the ON threshold is unchanged, only the OFF threshold moves).

PRE-REGISTERED before any run (2026-09-30, not edited after):
  Arms, each = the live design (trim v2 + whipsaw carry 3) with ONE change to the D gate:
    g2.5  gap200 flag ON below 2% (unchanged), OFF only at/above 2.5%
    g3    ... OFF only at/above 3%
    g4    ... OFF only at/above 4%
    b25   breadth flag ON below pct 0.20 (unchanged), OFF only at/above 0.25 (gap200 live)
  The ON thresholds, the D row and every other rule are untouched; the gate still acts
  in macro D only (the flags are tracked every day so the buffer carries across states).
  Primary base 40/60 (next A spell); 50/50 reported for information.
  An arm PASSES (no-harm fix) only if, at 40/60, ALL hold against live:
    P1 real Sharpe >= live;  P2 proxy Sharpe >= live;  P3 proxy 2000-2015 holdout Sharpe >= live;
    P4 MaxDD no more than 0.5 pp deeper than live on either harness;
    P5 gate switches inside D (gate on<->off between consecutive D days) fall >= 25% on proxy.
  If several pass, the SMALLEST buffer that passes is the candidate (least change).
  Block bootstrap reported, not gated. Research only -- nothing is applied by this script;
  the owner decides.
"""
import sys, io, contextlib, math
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
from block_bootstrap import boot
F._lf = open('paper-track/research_notes/dgate_buffer_study_run.log', 'w'); log = F.log

def sched(s0, t0, ks, kt):
    return [(s0 * max(0, 1 - ks * v), t0 * max(0, 1 - kt * v), 1 - s0 * max(0, 1 - ks * v) - t0 * max(0, 1 - kt * v)) for v in range(4)]
F.CARRY_G = 3
BASES = {'40/60': sched(.4, .6, 1/6, 1.0), '50/50': sched(.5, .5, 1/6, 1.0)}
ARMS = [('live', None, None), ('g2.5', 0.025, None), ('g3', 0.03, None), ('g4', 0.04, None), ('b25', None, 0.25)]

def run(h, sc, gx, bx):
    F.GATE_G_EXIT, F.GATE_B_EXIT = gx, bx
    try:
        det = F.sim(h, ('X', 'stephigh:15', sc), detail=True)[0]
    finally:
        F.GATE_G_EXIT = F.GATE_B_EXIT = None
    return det

def flips(det):
    n = 0; dd = 0; gd = 0
    for a, b in zip(det, det[1:]):
        if a['st'] == 'D' and b['st'] == 'D' and a['gate'] != b['gate']: n += 1
    for x in det:
        if x['st'] == 'D':
            dd += 1; gd += x['gate']
    return n, dd, gd

def dret(det):   # compounded return earned on macro-D days
    return (math.prod(1 + x['net'] for x in det if x['st'] == 'D') - 1) * 100

def month(det, ym):
    return (math.prod(1 + x['net'] for x in det if x['d'][:7] == ym) - 1) * 100

R = {}; SER = {}
for b, sc in BASES.items():
    for lab, gx, bx in ARMS:
        for h in F.H:
            det = run(h, sc, gx, bx); ser = [x['net'] for x in det]; SER[(b, lab, h)] = ser
            c, sh, m = annual_stats(ser)[:3]
            nf, dd, gd = flips(det)
            r = dict(c=c, sh=sh, m=m, nf=nf, dd=dd, gd=gd, dr=dret(det))
            if h == 'proxy':
                D = F.DATES[h]
                hs = [x for x, d in zip(ser, D) if d <= F.HOLDOUT[1]]; r['hc'], r['hsh'], r['hm'] = annual_stats(hs)[:3]
            else:
                r['feb'] = month(det, '2026-02'); r['mar'] = month(det, '2026-03')
            R[(b, lab, h)] = r

# the live arm must still be the live design
for b, sc in BASES.items():
    for h in F.H:
        ref = F.sim(h, ('X', 'stephigh:15', sc))[0]
        assert max(abs(p - q) for p, q in zip(ref, SER[(b, 'live', h)])) < 1e-12, (b, h)

log('=' * 140); log('dgate_buffer_study (2026-09-30): buffer zone on the state-D gate switch-off (pre-registered)'); log('=' * 140)
for b in BASES:
    for h in F.H:
        log(f"\n  {h.upper()}  base {b}")
        hdr = f"  {'arm':<6}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>8}{'D days':>8}{'gated':>7}{'flips':>7}{'D-day ret':>11}"
        hdr += f"{'holdCAGR':>10}{'holdSh':>8}{'holdDD':>8}" if h == 'proxy' else f"{'Feb26':>8}{'Mar26':>8}"
        log(hdr)
        for lab, _, _ in ARMS:
            r = R[(b, lab, h)]
            s = (f"  {lab:<6}{r['c']*100:7.2f}%{r['sh']:8.3f}{r['m']*100:7.1f}%{r['dd']:8d}{r['gd']:7d}{r['nf']:7d}{r['dr']:10.1f}%")
            s += f"{r['hc']*100:9.2f}%{r['hsh']:8.3f}{r['hm']*100:7.1f}%" if h == 'proxy' else f"{r['feb']:7.1f}%{r['mar']:7.1f}%"
            log(s)

log("\n  PRE-REGISTERED VERDICT (base 40/60)")
L = {h: R[('40/60', 'live', h)] for h in F.H}
passing = []
for lab, _, _ in ARMS[1:]:
    a = {h: R[('40/60', lab, h)] for h in F.H}
    P = [a['real']['sh'] >= L['real']['sh'], a['proxy']['sh'] >= L['proxy']['sh'],
         a['proxy']['hsh'] >= L['proxy']['hsh'],
         all(a[h]['m'] >= L[h]['m'] - 0.005 for h in F.H),
         a['proxy']['nf'] <= 0.75 * L['proxy']['nf']]
    ok = all(P); passing += [lab] if ok else []
    log(f"  {lab:<6} P1 {'Y' if P[0] else 'n'} ({a['real']['sh']-L['real']['sh']:+.3f})  P2 {'Y' if P[1] else 'n'} ({a['proxy']['sh']-L['proxy']['sh']:+.3f})"
        f"  P3 {'Y' if P[2] else 'n'} ({a['proxy']['hsh']-L['proxy']['hsh']:+.3f})  P4 {'Y' if P[3] else 'n'} "
        f"(real {(a['real']['m']-L['real']['m'])*100:+.1f} / proxy {(a['proxy']['m']-L['proxy']['m'])*100:+.1f} pp)"
        f"  P5 {'Y' if P[4] else 'n'} (flips {L['proxy']['nf']} -> {a['proxy']['nf']})  => {'PASS' if ok else 'fail'}")
log(f"  candidate: {passing[0] if passing else 'none -- keep the live gate'}")

log("\n  PAIRED BLOCK BOOTSTRAP vs live, base 40/60 (60-day blocks, 2000 draws): excess-Sharpe 95% CI, P(not better)")
for lab, _, _ in ARMS[1:]:
    parts = []
    for h in F.H:
        l1, l2, pl, s1, s2, ps = boot(F.xs(h, SER[('40/60', lab, h)]), F.xs(h, SER[('40/60', 'live', h)]), 60,
                                      seed=(sum(map(ord, lab)) * 31 + len(h)) & 0xffff)
        parts.append(f"{h} [{s1:+.3f}, {s2:+.3f}] P {ps:.2f}")
    log(f"  {lab:<6} " + '   '.join(parts))
