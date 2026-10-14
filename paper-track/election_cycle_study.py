"""Owner (2026-10-14): "research on if election year/month/day will be a big enough factor
to this strategy". (Context: the US midterm is Tue 3 Nov 2026.)

PRE-REGISTERED before any run (2026-10-14, not edited after):
  Election days = the Tuesday after the first Monday of November, every even year
  (presidential when year % 4 == 0, midterm otherwise).
  PART A (descriptive, market): NYSE Composite 1970-, Nasdaq-100 1985-, QQQ 1999-.
    A1 four-year cycle: calendar-year return by cycle position; label-shuffle permutation
       test (5000) on the spread of the four bucket means.
    A2 election window: price return over sessions [-10, 0] and [0, +10] around election
       day, and the calendar months of October and November in election years; placebo =
       the same window at a random trading day of the same year (>= 15 sessions away),
       5000 draws of the mean; two-sided p.
  PART B (descriptive, strategy): the same A1/A2 on the current design (trim v2 + carry 3,
    D gate, E cash, 30d vol target, 5% band; A base 40/60) on the 2000-2026 QQQ-core proxy
    and the 2015-2026 real-instrument harness, with QQQ over the same days for contrast.
  PART C (rules, gated): risky legs scaled on the listed decision dates.
    R1  x0.5 from 5 sessions before to 5 after every election day
    R2  all BOXX over the same window
    R3  x0.5 over the same window, presidential elections only
    R4  x0.75 in midterm years from 1 Jan to election day ("midterm slump")
    R5  x1.2 from election day to 31 Dec of every election year ("post-election rally";
        adds leverage beyond the design)
  A rule PASSES only if ALL hold at 40/60:
    P1 full-period excess Sharpe >= live on BOTH harnesses;
    P2 proxy 2000-2015 holdout excess Sharpe >= live;
    P3 placebo: the rule's proxy Sharpe gain ranks in the top 5% of 200 copies of the same
       rule with the whole election calendar shifted by a random 20-200 sessions (+/-).
  Block bootstrap reported, not gated. VIXM sleeve not in the harness. Research only.
"""
import sys, io, contextlib, csv, datetime as dt, random, math, bisect, time
sys.path.insert(0, 'paper-track')
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as F
from drift_band_test import annual_stats
from block_bootstrap import boot
F._lf = open('paper-track/research_notes/election_cycle_study_run.log', 'w'); log = F.log
T0 = time.time(); RNG = random.Random(20261014)

def eday(y):
    d = dt.date(y, 11, 1)
    while d.weekday() != 0: d += dt.timedelta(days=1)
    return (d + dt.timedelta(days=1)).isoformat()
ELEC = {y: eday(y) for y in range(1970, 2027, 2)}
kind = lambda y: 'pres' if y % 4 == 0 else 'mid'
CYC = {0: 'election yr', 1: 'post-election', 2: 'midterm yr', 3: 'pre-election'}

def load(path):
    with open(path) as f:
        return [(r['d'], float(r['c'])) for r in csv.DictReader(f)]

def series_from_returns(dates, rets):            # -> list of (date, level) with level after each date's return
    out, lv = [], 1.0
    for d, r in zip(dates, rets): lv *= 1 + r; out.append((d, lv))
    return out

def cycle_table(name, px, last_full_year):
    yr = {}
    for d, c in px: yr.setdefault(int(d[:4]), []).append(c)
    ys = sorted(y for y in yr if y - 1 in yr and y <= last_full_year)
    ret = {y: yr[y][-1] / yr[y - 1][-1] - 1 for y in ys}
    lab = {y: y % 4 for y in ys}
    def spread(L):
        m = [sum(ret[y] for y in ys if L[y] == k) / max(1, sum(1 for y in ys if L[y] == k)) for k in range(4)]
        return max(m) - min(m), m
    obs, means = spread(lab)
    labs = [lab[y] for y in ys]; ge = 0
    for _ in range(5000):
        RNG.shuffle(labs); ge += spread(dict(zip(ys, labs)))[0] >= obs
    parts = []
    for k in (0, 1, 2, 3):
        v = [ret[y] for y in ys if lab[y] == k]
        parts.append(f"{CYC[k]} {means[k]*100:+6.1f}% (n {len(v)}, {sum(x > 0 for x in v)}/{len(v)} up)")
    log(f"  {name:<28}{ys[0]}-{ys[-1]}  " + ' | '.join(parts) + f"  spread {obs*100:.1f}pp, perm p {ge/5000:.2f}")

def window_table(name, px, years):
    ds = [d for d, _ in px]; cs = [c for _, c in px]
    def at(day): return bisect.bisect_left(ds, day)
    def wret(i, a, b):
        if i + a < 1 or i + b >= len(cs): return None
        return cs[i + b] / cs[i + a - 1] - 1 if a > 0 else cs[i + b] / cs[i + a] - 1
    def mret(y, mo):
        idx = [i for i, d in enumerate(ds) if d[:7] == f"{y}-{mo:02d}"]
        return cs[idx[-1]] / cs[idx[0] - 1] - 1 if idx and idx[0] > 0 else None
    yidx = {}
    for i, d in enumerate(ds): yidx.setdefault(int(d[:4]), []).append(i)
    out = []
    for lab_, (a, b) in (('pre  [-10,0]', (-10, 0)), ('post [0,+10]', (0, 10))):
        for kd in ('all', 'pres', 'mid'):
            Y = [y for y in years if (kd == 'all' or kind(y) == kd) and ELEC[y] >= ds[11] and ELEC[y] <= ds[-12]]
            obs = [wret(at(ELEC[y]), a, b) for y in Y]; obs = [x for x in obs if x is not None]
            if not obs: continue
            m = sum(obs) / len(obs); ge = 0; N = 3000
            pools = [[i for i in yidx[y] if abs(i - at(ELEC[y])) >= 15] for y in Y]
            for _ in range(N):
                s = [wret(RNG.choice(pool), a, b) for pool in pools]; s = [x for x in s if x is not None]
                ge += (sum(s) / len(s)) >= m
            p = ge / N; p2 = 2 * min(p, 1 - p)
            out.append(f"{lab_} {kd:<4} mean {m*100:+5.2f}% (n {len(obs)}, {sum(x>0 for x in obs)} up) placebo p {p2:.2f}")
    for mo, mn in ((10, 'Oct'), (11, 'Nov')):
        v = [mret(y, mo) for y in years]; v = [x for x in v if x is not None]
        allm = [mret(y, mo) for y in sorted(yidx) if y % 2 == 1]; allm = [x for x in allm if x is not None]
        if v: out.append(f"{mn} in election yrs {sum(v)/len(v)*100:+5.2f}% (n {len(v)}) vs odd yrs {sum(allm)/max(1,len(allm))*100:+5.2f}% (n {len(allm)})")
    log(f"  {name}"); [log(f"      {x}") for x in out]

# ---------------------------------------------------------------- PART A
log('=' * 150); log('election_cycle_study (2026-10-14): election year / month / day vs the strategy (pre-registered)'); log('=' * 150)
log('\n  PART A -- market, four-year cycle (calendar-year price return by cycle position)')
MK = {'NYSE Composite': load('data/NYA_index_daily.csv'), 'Nasdaq-100': load('data/NDX_index_daily.csv'),
      'QQQ': load('data/qqq_long_history.csv')}
for nm, px in MK.items(): cycle_table(nm, px, 2025)
log('\n  PART A -- market, election windows (price return; placebo = same window at a random day of the same year)')
for nm, px in MK.items():
    window_table(nm, px, [y for y in ELEC if int(px[0][0][:4]) <= y <= 2024])

# ---------------------------------------------------------------- PART B
def sched(s0, t0, ks, kt):
    return [(s0 * max(0, 1 - ks * v), t0 * max(0, 1 - kt * v), 1 - s0 * max(0, 1 - ks * v) - t0 * max(0, 1 - kt * v)) for v in range(4)]
F.CARRY_G = 3; SC = sched(.4, .6, 1/6, 1.0); ARM = ('X', 'stephigh:15', SC)
def run(h, M=None):
    F.DATE_SCALE = (lambda d: M.get(d, 1.0)) if M else None
    try: ser = F.sim(h, ARM)[0]
    finally: F.DATE_SCALE = None
    c, _, m = annual_stats(ser)
    return dict(ser=ser, c=c, m=m, F=F._sh(F.xs(h, ser)),
                H=F._sh(F.xs(h, ser, hi=F.HOLDOUT[1])) if h == 'proxy' else float('nan'))
LIVE = {h: run(h) for h in F.H}
QQQR = {}
qd = MK['QQQ']; qmap = {d: c for d, c in qd}; qds = [d for d, _ in qd]
for h in F.H:   # QQQ close-to-next-close return aligned with the strategy's decision date
    QQQR[h] = []
    for d in F.DATES[h]:
        i = bisect.bisect_left(qds, d)
        QQQR[h].append(qd[i + 1][1] / qd[i][1] - 1 if i + 1 < len(qd) and qds[i] == d else 0.0)
log('\n  PART B -- the strategy (current design, A base 40/60) vs QQQ over the same days')
for h in F.H:
    lvl_s = series_from_returns(F.DATES[h], LIVE[h]['ser']); lvl_q = series_from_returns(F.DATES[h], QQQR[h])
    cycle_table(f"strategy {h}", lvl_s, 2025); cycle_table(f"QQQ same days ({h})", lvl_q, 2025)
    yrs = [y for y in ELEC if F.DATES[h][0][:4] <= str(y) <= '2024']
    window_table(f"strategy {h}", lvl_s, yrs); window_table(f"QQQ same days ({h})", lvl_q, yrs)

# ---------------------------------------------------------------- PART C
def rule_dates(h, r, shift=0):
    D = F.DATES[h]; M = {}
    for y, e in ELEC.items():
        i = bisect.bisect_left(D, e) + shift
        if not (0 <= i < len(D)): continue
        if r in ('R1', 'R2', 'R3'):
            if r == 'R3' and kind(y) != 'pres': continue
            for j in range(max(0, i - 5), min(len(D), i + 6)): M[D[j]] = 0.0 if r == 'R2' else 0.5
        elif r == 'R4' and kind(y) == 'mid':
            j0 = bisect.bisect_left(D, f"{y}-01-01") + shift
            for j in range(max(0, j0), i): M[D[j]] = 0.75
        elif r == 'R5':
            j1 = bisect.bisect_left(D, f"{y + 1}-01-01") + shift
            for j in range(max(0, i), min(len(D), j1)): M[D[j]] = 1.2
    return M
RULES = {'R1': 'x0.5, -5..+5 sessions, all elections', 'R2': 'cash, -5..+5 sessions, all elections',
         'R3': 'x0.5, -5..+5, presidential only', 'R4': 'x0.75 midterm yr, Jan 1 -> election',
         'R5': 'x1.2 election -> Dec 31'}
log('\n  PART C -- rules (A base 40/60). LIVE: ' + '  '.join(f"{h} {LIVE[h]['c']*100:.2f}% / {LIVE[h]['m']*100:.1f}% / exSh {LIVE[h]['F']:.3f}" for h in F.H)
    + f"  holdout {LIVE['proxy']['H']:.3f}")
log(f"  {'rule':<40}{'real CAGR':>10}{'MaxDD':>7}{'dSh':>8}{'prx CAGR':>10}{'MaxDD':>7}{'dSh':>8}{'dHold':>8}{'placebo rank':>14}  verdict")
for r, desc in RULES.items():
    E = {h: run(h, rule_dates(h, r)) for h in F.H}
    gain = E['proxy']['F'] - LIVE['proxy']['F']; pl = []
    for _ in range(200):
        k = RNG.choice([-1, 1]) * RNG.randint(20, 200)
        pl.append(run('proxy', rule_dates('proxy', r, k))['F'] - LIVE['proxy']['F'])
    rank = sum(x >= gain for x in pl) / len(pl)
    P = [all(E[h]['F'] >= LIVE[h]['F'] for h in F.H), E['proxy']['H'] >= LIVE['proxy']['H'], rank <= 0.05]
    log(f"  {r} {desc:<37}{E['real']['c']*100:9.2f}%{E['real']['m']*100:6.1f}%{E['real']['F']-LIVE['real']['F']:+8.3f}"
        f"{E['proxy']['c']*100:9.2f}%{E['proxy']['m']*100:6.1f}%{gain:+8.3f}{E['proxy']['H']-LIVE['proxy']['H']:+8.3f}"
        f"{rank:13.2f}   P1 {'Y' if P[0] else 'n'} P2 {'Y' if P[1] else 'n'} P3 {'Y' if P[2] else 'n'} => {'PASS' if all(P) else 'fail'}")
    for h in F.H:
        l1, l2, pl_, s1, s2, ps = boot(F.xs(h, E[h]['ser']), F.xs(h, LIVE[h]['ser']), 60, seed=(sum(map(ord, r)) * 31 + len(h)) & 0xffff)
        log(f"       bootstrap {h}: excess-Sharpe 95% CI [{s1:+.3f}, {s2:+.3f}], P(not better) {ps:.2f}")
log(f"\n  next election: midterm {ELEC[2026]}")
log(f"  done in {time.time()-T0:.0f}s")
