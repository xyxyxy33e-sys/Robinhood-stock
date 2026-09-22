"""Owner (2026-09-22): "what about release vs volatility". Votes rise at once; they
may only FALL when volatility is calm. Two arms fixed before running, no new
numbers: (1) 10-day QQQ vol below the live 30-day estimate (vol not expanding);
(2) 10-day QQQ vol below the 20% vol target. Reset on exit from A. Latch and
new-20d-high release for reference. Post-hoc relative to fall_protection_study.
Research only."""
import os, sys, io, contextlib, math
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
from block_bootstrap import boot
F._lf = open('paper-track/research_notes/fall_protection_r5_run.log', 'w'); log = F.log
H = F.H; D = F.DATES
ARMS = [('V', 'v10<v30', None), ('V', 'v10<20', None), ('L', None, None), ('R', 'high20', None)]
nm = lambda a: {'V': lambda: 'release: v10 < v30' if a[1] == 'v10<v30' else 'release: v10 < 20%', 'R': lambda: 'release new 20d high', 'L': lambda: 'latch until exit A'}[a[0]]()
log('=' * 150); log('fall_protection_r5: release votes only when volatility is calm'); log('=' * 150)
S = {}
for h in H:
    L = F.LIVE[h]
    log(f"\n  {h.upper()}")
    log(f"  {'arm':<22}{'CAGR':>8}{'dCAGR':>8}{'MaxDD':>8}{'EDGE':>7}{'exSh F':>8}{'dF':>8}{'dS':>8}{'dH':>8}{'reb':>6}{'exp':>7}  worst live episodes arm/live")
    for a in [None] + ARMS:
        ser, expo, reb, _ = F.sim(h, a); S[(h, a)] = ser
        c, _, m = annual_stats(ser); edge = (m - F.front(h, c)) * 100
        f = F._sh(F.xs(h, ser)); sS = F._sh(F.xs(h, ser, lo=F.SEARCH[0]))
        hh = F._sh(F.xs(h, ser, hi=F.HOLDOUT[1])) if h == 'proxy' else float('nan')
        eps = '  '.join(f"{n} {F.mdd_window(ser, D[h], lo, hi)*100:.1f}/{F.mdd_window(L['ser'], D[h], lo, hi)*100:.1f}" for lo, hi, n in F.EPIS[h])
        dH = f"{hh-L['H']:+8.3f}" if h == 'proxy' else '      - '
        log(f"  {('LIVE' if a is None else nm(a)):<22}{c*100:7.2f}%{(c-L['cagr'])*100:+8.2f}{m*100:7.1f}%{edge:+7.2f}{f:8.3f}{f-L['F']:+8.3f}{sS-L['S']:+8.3f}{dH}{reb:6.1f}{expo*100:6.1f}%  {eps}")
log('\n  PROXY holdout 2000-2015 and its halves (CAGR / MaxDD / exSharpe)')
for lo, hi, w in (('1900', F.HOLDOUT[1], 'holdout'), ('1900', '2007-12-31', '2000-07'), ('2008-01-01', F.HOLDOUT[1], '2008-15'), (F.SEARCH[0], '2100', 'search')):
    parts = []
    for a in [None] + ARMS:
        ss = [r for r, d in zip(S[('proxy', a)], D['proxy']) if lo <= d <= hi]
        c, _, m = annual_stats(ss)
        parts.append(f"{('LIVE' if a is None else nm(a))}: {c*100:.2f}% / {m*100:.1f}% / {F._sh(F.xs('proxy', S[('proxy', a)], lo=lo, hi=hi)):.3f}")
    log(f"  {w:<8} " + ' | '.join(parts))
log('\n  CALENDAR YEARS, first two arms minus live (pp)')
for arm in ARMS[:2]:
  log(f"  {nm(arm)}")
  for h in H:
    yrs = sorted(set(d[:4] for d in D[h])); parts = []; up = dn = 0
    for y in yrs:
        a = math.prod(1 + r for r, d in zip(S[(h, arm)], D[h]) if d[:4] == y)
        b = math.prod(1 + r for r, d in zip(S[(h, None)], D[h]) if d[:4] == y)
        x = (a - b) * 100; parts.append(f"{y}:{x:+.1f}"); up += x > 0.05; dn += x < -0.05
    log(f"  {h}: " + '  '.join(parts)); log(f"        better {up}, worse {dn}")
log('\n  PAIRED BLOCK BOOTSTRAP vs live (60-day blocks): excess-Sharpe 95% CI, P(not better); log-return CI')
for a in ARMS:
    parts = []
    for h in H:
        l1, l2, pl, s1, s2, ps = boot(F.xs(h, S[(h, a)]), F.xs(h, S[(h, None)]), 60, seed=(sum(map(ord, nm(a))) * 17 + len(h)) & 0xffff)
        parts.append(f"{h} Sh [{s1:+.3f}, {s2:+.3f}] P {ps:.2f} | ret [{l1*100:+.2f}, {l2*100:+.2f}]pp")
    log(f"  {nm(a):<22} " + '   '.join(parts))
# how long does the latch hold? A spells with a latched vote
for arm in ARMS[:3]:
  for h in H:
    det = F.sim(h, arm, detail=True)[0]
    held_days = sum(1 for x in det if x['eff'] == 'A' and not x['gate'] and x['st'] not in 'EF' and isinstance(x['v'], tuple) and x['v'][0] > 0)
    live_days = sum(1 for x in F.sim(h, None, detail=True)[0] if isinstance(x['v'], tuple) and x['v'][0] > 0)
    log(f"  {nm(arm):<22} {h}: A days with the trim on — live {live_days}, arm {held_days} (of {len(det)} sessions)")
