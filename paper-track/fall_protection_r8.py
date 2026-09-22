"""Owner (2026-09-22): "calculate for me, if applying both but also bring the
leverage to 30/70". Both = the latch (trim held until the book leaves A) + the
asymmetric trim (TQQQ cut 1/2 of its base weight per vote, SPMO 1/6, freed
weight to cash). Base A row 30/70 SPMO/TQQQ. Arms fixed before running; 40/60
included as the midpoint. Research only; design frozen to 7 December."""
import os, sys, io, contextlib, math
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
from block_bootstrap import boot
F._lf = open('paper-track/research_notes/fall_protection_r8_run.log', 'w'); log = F.log
H = F.H; D = F.DATES

def prop(s0, t0):   return [(s0 * (1 - v / 3), t0 * (1 - v / 3), (s0 + t0) * v / 3) for v in range(4)]
def asym(s0, t0):
    out = []
    for v in range(4):
        s = s0 * (1 - v / 6); t = max(0.0, t0 * (1 - v / 2)); out.append((s, t, 1 - s - t))
    return out
ARMS = [
    ('live 50/50 (today)',                 ('X', 'live',  prop(.5, .5))),
    ('30/70, nothing else',                ('X', 'live',  prop(.3, .7))),
    ('50/50 + latch + asymmetric',         ('X', 'latch', asym(.5, .5))),
    ('40/60 + latch + asymmetric',         ('X', 'latch', asym(.4, .6))),
    ('30/70 + latch + asymmetric',         ('X', 'latch', asym(.3, .7))),
]
for h in H:
    assert max(abs(p - q) for p, q in zip(F.sim(h, ARMS[0][1])[0], F.LIVE[h]['ser'])) < 1e-12
log('=' * 150); log('fall_protection_r8: latch + asymmetric trim, at 50/50, 40/60 and 30/70'); log('=' * 150)
for lab, a in ARMS:
    log(f"  {lab:<30} rows at 0/1/2/3 votes (SPMO/TQQQ/cash): " + '  '.join(f"{s*100:.0f}/{t*100:.0f}/{c*100:.0f}" for s, t, c in a[2])
        + "   leverage " + ' -> '.join(f"{s+3*t:.2f}" for s, t, c in a[2]))
S = {}
def dd_series(ser):
    nav = pk = 1.0; out = []
    for r in ser: nav *= 1 + r; pk = max(pk, nav); out.append(nav / pk - 1)
    return out
for h in H:
    L = F.LIVE[h]
    log(f"\n  {h.upper()}  ({D[h][0]} .. {D[h][-1]})")
    log(f"  {'arm':<30}{'CAGR':>8}{'dCAGR':>8}{'MaxDD':>8}{'EDGE':>7}{'exSh':>7}{'dSh':>8}{'Calmar':>8}{'vol':>7}{'%time DD>10%':>14}{'exp':>7}{'reb':>6}")
    for lab, a in ARMS:
        ser, expo, reb, _ = F.sim(h, a); S[(h, lab)] = ser
        c, _, m = annual_stats(ser); edge = (m - F.front(h, c)) * 100; sh = F._sh(F.xs(h, ser))
        mu = sum(ser) / len(ser); vol = (sum((x - mu) ** 2 for x in ser) / (len(ser) - 1)) ** .5 * math.sqrt(252)
        dd = dd_series(ser); p10 = sum(1 for x in dd if x < -0.10) / len(dd)
        log(f"  {lab:<30}{c*100:7.2f}%{(c-L['cagr'])*100:+8.2f}{m*100:7.1f}%{edge:+7.2f}{sh:7.3f}{sh-L['F']:+8.3f}{c/-m:8.2f}{vol*100:6.1f}%{p10*100:13.1f}%{expo*100:6.1f}%{reb:6.1f}")
    log(f"  worst live episodes and 2022:")
    for lo, hi, n in F.EPIS[h] + [('2022-01-01', '2022-12-31', 'calendar 2022 (DD)')]:
        log(f"    {n:<22} " + '  '.join(f"{lab.split(' ')[0]+('+' if 'latch' in lab else ''):>7} {F.mdd_window(S[(h, lab)], D[h], lo, hi)*100:6.1f}%" for lab, _ in ARMS))
log('\n  PROXY: search 2015+ vs holdout 2000-2015 (CAGR / MaxDD / exSharpe)')
for lo, hi, w in ((F.SEARCH[0], '2100', 'search 2015+'), ('1900', F.HOLDOUT[1], 'holdout 2000-15')):
    for lab, a in ARMS:
        ss = [r for r, d in zip(S[('proxy', lab)], D['proxy']) if lo <= d <= hi]
        c, _, m = annual_stats(ss)
        log(f"  {w:<16} {lab:<30} {c*100:6.2f}% / {m*100:6.1f}% / {F._sh(F.xs('proxy', S[('proxy', lab)], lo=lo, hi=hi)):.3f}")
log('\n  REAL calendar-year returns (%) and QQQ / SPY-proxy reference')
yrs = sorted(set(d[:4] for d in D['real']))
QR = {d: F.PX['real'][F.PXD['real'][F.PXI['real'][d] + 1]] / F.PX['real'][d] - 1 for d in D['real']}
log(f"  {'year':<6}" + ''.join(f"{lab[:14]:>16}" for lab, _ in ARMS) + f"{'QQQ':>9}")
for y in yrs:
    row = ''.join(f"{(math.prod(1 + r for r, d in zip(S[('real', lab)], D['real']) if d[:4] == y) - 1)*100:16.1f}" for lab, _ in ARMS)
    q = (math.prod(1 + QR[d] for d in D['real'] if d[:4] == y) - 1) * 100
    log(f"  {y:<6}{row}{q:9.1f}")
log('\n  GROWTH OF $222,246 (today\'s account) over the real history, each arm, and the worst dollar drawdown')
for lab, a in ARMS:
    ser = S[('real', lab)]; nav = 1.0; pk = 1.0; worst = 0.0
    for r in ser: nav *= 1 + r; pk = max(pk, nav); worst = min(worst, nav - pk)
    c, _, m = annual_stats(ser)
    log(f"  {lab:<30} x{nav:8.1f} over {len(ser)/252:.1f} yrs;  a {m*100:.1f}% drawdown on $222,246 = ${-m*222246:,.0f}")
log('\n  PAIRED BLOCK BOOTSTRAP vs live (60-day blocks): excess-Sharpe and log-return 95% CI, P(not better)')
for lab, a in ARMS[1:]:
    parts = []
    for h in H:
        l1, l2, pl, s1, s2, ps = boot(F.xs(h, S[(h, lab)]), F.xs(h, F.LIVE[h]['ser']), 60, seed=(sum(map(ord, lab)) + len(h)) & 0xffff)
        parts.append(f"{h} Sh [{s1:+.3f}, {s2:+.3f}] P {ps:.2f} ret [{l1*100:+.2f}, {l2*100:+.2f}]pp P {pl:.2f}")
    log(f"  {lab:<30} " + '   '.join(parts))
