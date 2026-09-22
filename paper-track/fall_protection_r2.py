"""Robustness for the trim-memory arms of fall_protection_study (2026-09-22). Research only."""
import os, sys, io, contextlib, math
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
log = F.log
F._lf = open('paper-track/research_notes/fall_protection_r2_run.log', 'w')
H = F.H; D = F.DATES
def win(ser, dates, lo, hi):
    s = [r for r, d in zip(ser, dates) if lo <= d <= hi]
    c, _, m = annual_stats(s); return c, m, s
log('=' * 120); log('fall_protection_r2: robustness of trim memory'); log('=' * 120)
Ns = (10, 15, 20, 25, 30, 40, 60)
SER = {(h, n): F.sim(h, ('M', n, None))[0] for h in H for n in Ns}
LIVE = {h: F.sim(h)[0] for h in H}
log('\n1  SMOOTHNESS in N (full period): CAGR / MaxDD / exSharpe / edge')
for h in H:
    for n in Ns:
        s = SER[(h, n)]; c, _, m = annual_stats(s); e = (m - F.front(h, c)) * 100
        log(f"  {h:<6} N={n:<3} {c*100:6.2f}% {m*100:6.1f}%  exSh {F._sh(F.xs(h, s)):.3f}  edge {e:+.2f}")
log('\n2  PROXY SUB-PERIODS: holdout 2000-2015 vs search 2015+ (CAGR / MaxDD / exSharpe)')
for lo, hi, nm in (('1900', F.HOLDOUT[1], 'holdout'), (F.SEARCH[0], '2100', 'search'),
                   ('1900', '2007-12-31', '2000-2007'), ('2008-01-01', F.HOLDOUT[1], '2008-2015')):
    for n in (None, 20, 40):
        s = LIVE['proxy'] if n is None else SER[('proxy', n)]
        c, m, ss = win(s, D['proxy'], lo, hi)
        x = F.xs('proxy', s, lo=lo, hi=hi)
        log(f"  {nm:<10} {('LIVE' if n is None else f'M{n}'):<5} {c*100:6.2f}% {m*100:6.1f}%  exSh {F._sh(x):.3f}")
log('\n3  CALENDAR YEARS, return difference M20 minus live (pp)')
for h in H:
    yrs = sorted(set(d[:4] for d in D[h]))
    parts = []
    for y in yrs:
        a = math.prod(1 + r for r, d in zip(SER[(h, 20)], D[h]) if d[:4] == y)
        b = math.prod(1 + r for r, d in zip(LIVE[h], D[h]) if d[:4] == y)
        parts.append(f"{y}:{(a-b)*100:+.1f}")
    pos = sum(1 for p in parts if '+' in p.split(':')[1] and float(p.split(':')[1]) > 0.05)
    neg = sum(1 for p in parts if float(p.split(':')[1]) < -0.05)
    log(f"  {h}: {'  '.join(parts)}")
    log(f"        years better {pos}, worse {neg}")
log('\n4  WITHOUT 2020 (drop the calendar year from both series)')
for h in H:
    for n in (None, 20, 40):
        s = LIVE[h] if n is None else SER[(h, n)]
        ss = [r for r, d in zip(s, D[h]) if d[:4] != '2020']; cc = [c for c, d in zip(F.CASHR[h], D[h]) if d[:4] != '2020']
        c, _, m = annual_stats(ss)
        log(f"  {h:<6} {('LIVE' if n is None else f'M{n}'):<5} {c*100:6.2f}% {m*100:6.1f}%  exSh {F._sh([a-b for a,b in zip(ss,cc)]):.3f}")
