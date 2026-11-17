"""Revised 2027 forecast: symbol-group split (VIXY+VIXM vs rest), K-1 60/40 view, NYC rates. Research only, not tax advice.
Reuses wash.py's lot simulator and fc.py's method (same panels, lots, $608,122 book). wash.py/fc.py are NOT modified:
Book is subclassed here only to log each realized-gain increment by (year, symbol group, ST/LT)."""
import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import wash
from wash import TK, TI, simulate
out = []
def Pn(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); out.append(s)

BK = 608122.0
TODAY = np.zeros(len(TK)); TODAY[TI['TQQQ']] = 0.428; TODAY[TI['VIXY']] = 0.200; TODAY[TI['BOXX']] = 0.372
K1 = ('VIXY', 'VIXM')

# ---------- logging subclass (context: which ticker's sale produced a realized increment)
CTX = [None]; ORIG = [None]; LOG = {}
def grp(sym): return 'A' if sym in K1 else 'B'
class PL(list):
    def __init__(self, y): super().__init__([0.0, 0.0]); self.y = y
    def __setitem__(self, k, v):
        d = v - list.__getitem__(self, k); list.__setitem__(self, k, v)
        sym = ORIG[0] if CTX[0] == 'FWD' else CTX[0]
        assert sym is not None
        key = (self.y, grp(sym), k); LOG[key] = LOG.get(key, 0.0) + d
class Item(list):
    def __getitem__(self, i):
        v = list.__getitem__(self, i)
        if i == 5: ORIG[0] = v           # origin ticker of the pending wash loss, read just before the forward-wash yr() update
        return v
class TL(list):
    def append(self, x): super().append(x if isinstance(x, Item) else Item(x))
class PD(dict):
    def __setitem__(self, s, lst): super().__setitem__(s, TL(Item(x) if not isinstance(x, Item) else x for x in lst))
    def setdefault(self, s, d=None):
        if s not in self: self[s] = TL()
        return dict.__getitem__(self, s)
class Sub(wash.Book):
    def __init__(self, *a, **k): super().__init__(*a, **k); self.pend = PD()
    def yr(self, y):
        if y not in self.real: self.real[y] = PL(y)
        return self.real[y]
    def sell(self, tk, usd, t, tagsel):
        CTX[0] = tk
        try: super().sell(tk, usd, t, tagsel)
        finally: CTX[0] = None
    def buy(self, tk, usd, t, tag=None):
        CTX[0] = 'FWD'
        try: super().buy(tk, usd, t, tag)
        finally: CTX[0] = None
wash.Book = Sub

STN = {0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E', 5: 'F'}
VARS = (('plain', dict()), ('seed', dict(seed=31400.0)), ('today', dict(init_w=TODAY)), ('today+seed', dict(init_w=TODAY, seed=31400.0)))
def years(real):
    wash.setpanel(real); Y = sorted(set(wash.YR[wash.S0:])); res = []
    for y in Y:
        idx = [i for i in range(wash.S0, wash.T) if wash.YR[i] == y]
        full = (real and 2016 <= y <= 2025) or ((not real) and 2002 <= y <= 2025)
        if not full: continue
        d = dict(y=y)
        for var, kw in VARS:
            LOG.clear()
            r = simulate('BASE', 'FIFO', taxed=False, i0=idx[0], i1=idx[-1], book0=BK, **kw)
            st, lt = r['real'].get(y, [0, 0])
            g = {(gr, k): LOG.get((y, gr, k), 0.0) for gr in 'AB' for k in (0, 1)}
            assert abs(g['A', 0] + g['B', 0] - st) < 1e-6 and abs(g['A', 1] + g['B', 1] - lt) < 1e-6, (y, var)
            d[var] = dict(st=st, lt=lt, Ast=g['A', 0], Alt=g['A', 1], Bst=g['B', 0], Blt=g['B', 1])
        res.append(d)
    return res

# ---------- tax
CASES = {'NYC top': (0.55576, 0.38576), 'NYC upper-middle': (0.49526, 0.29526)}
def net(st, lt, rst, rlt):
    """IRS netting: ST and LT netted, then cross-netted; net loss: $3k vs ordinary (valued at the ST rate), rest carried with character."""
    s, l = st, lt
    if s < 0 < l:
        x = s + l; s, l = (0.0, x) if x >= 0 else (x, 0.0)
    elif l < 0 < s:
        x = s + l; s, l = (x, 0.0) if x >= 0 else (0.0, x)
    tax = max(s, 0) * rst + max(l, 0) * rlt; off = 0.0; cs = cl = 0.0
    if s < 0 or l < 0:
        n = min(s, 0) + min(l, 0); off = min(3000.0, -n); tax -= off * rst
        cs = min(s, 0.0); cl = min(l, 0.0)
        take = min(off, -cs); cs += take; cl += off - take
    return dict(s=s, l=l, tot=s + l, tax=tax, off=off, cfs=cs, cfl=cl)
def treat(d, mode):
    """mode 'old': all gains as simulated (holding-period character). mode 'k1': VIXY+VIXM total gain/loss 60% LT / 40% ST, rest keeps its own character."""
    if mode == 'old': return d['st'], d['lt']
    a = d['Ast'] + d['Alt']
    return d['Bst'] + 0.4 * a, d['Blt'] + 0.6 * a
def pc(a, q): return float(np.percentile(a, q))
QS = (10, 25, 50, 75, 90)
def row(lab, a): return '    %-30s' % lab + ' '.join('%10.0f' % pc(a, q) for q in QS)

def report(real, nm):
    res = years(real)
    Pn(); Pn('================ ' + nm)
    for var, _ in VARS:
        Pn(); Pn('---- start-lot variant: ' + var)
        Pn('  per year (pre-netting, $): A = VIXY+VIXM lots, B = everything else | then netted ST / LT / total, tax NYC top / NYC upper-middle')
        for mode in ('old', 'k1'):
            Pn('  [%s treatment]  year |  A_st   A_lt |  B_st   B_lt | netST  netLT  total | tax top  tax UM' % ('OLD all-ordinary (holding-period character)' if mode == 'old' else 'K-1 60/40 on VIXY+VIXM'))
            for d in res:
                x = d[var]
                if mode == 'old': st, lt = x['st'], x['lt']; ast, alt, bst, blt = x['Ast'], x['Alt'], x['Bst'], x['Blt']
                else:
                    st, lt = treat(x, 'k1'); a = x['Ast'] + x['Alt']; ast, alt, bst, blt = 0.4 * a, 0.6 * a, x['Bst'], x['Blt']
                n1 = net(st, lt, *CASES['NYC top']); n2 = net(st, lt, *CASES['NYC upper-middle'])
                Pn('    %d | %8.0f %8.0f | %8.0f %8.0f | %8.0f %8.0f %8.0f | %8.0f %8.0f' % (d['y'], ast, alt, bst, blt, n1['s'], n1['l'], n1['tot'], n1['tax'], n2['tax']))
        # forecast distributions
        Pn('  FORECAST DISTRIBUTION %s / %s (n=%d)            p10        p25     median        p75        p90' % (nm, var, len(res)))
        store = {}
        for mode in ('old', 'k1'):
            nets = {c: [net(*treat(d[var], mode), *CASES[c]) for d in res] for c in CASES}
            n0 = nets['NYC top']
            Pn(' ', 'treatment: ' + ('OLD (all ST as simulated)' if mode == 'old' else 'K-1 60/40 on VIXY+VIXM'))
            Pn(row('net ST gain (after netting)', [n['s'] for n in n0]))
            Pn(row('net LT gain (after netting)', [n['l'] for n in n0]))
            Pn(row('total net gain', [n['tot'] for n in n0]))
            for c in CASES:
                Pn(row('tax due, ' + c, [n['tax'] for n in nets[c]]))
            store[mode] = nets
        Pn('  TAX SAVED by K-1 treatment (old tax minus K-1 tax; >0 = K-1 view is cheaper)')
        for c in CASES:
            to = np.array([n['tax'] for n in store['old'][c]]); tk = np.array([n['tax'] for n in store['k1'][c]])
            Pn('    %-18s diff of percentiles: median %9.0f  p90 %9.0f | percentiles of per-year saving: p10 %8.0f median %8.0f p90 %8.0f | mean %8.0f' % (
                c, pc(to, 50) - pc(tk, 50), pc(to, 90) - pc(tk, 90), pc(to - tk, 10), pc(to - tk, 50), pc(to - tk, 90), (to - tk).mean()))
        # sleeve share
        A = np.array([d[var]['Ast'] + d[var]['Alt'] for d in res]); Tt = np.array([d[var]['st'] + d[var]['lt'] for d in res])
        srt = np.argsort(Tt); mid = [res[i]['y'] for i in srt[len(srt) // 2 - 1: len(srt) // 2 + 1]] if len(srt) % 2 == 0 else [res[srt[len(srt) // 2]]['y']]
        Pn('  VIXY+VIXM sleeve share (A = realized gain on VIXY/VIXM lots): median A %.0f / median total %.0f = %.1f%% | sum A %.0f / sum total %.0f = %.1f%%' % (
            np.median(A), np.median(Tt), 100 * np.median(A) / np.median(Tt), A.sum(), Tt.sum(), 100 * A.sum() / Tt.sum()))
        Pn('  median-ranked year(s) by total gain: %s; their A / total: %s' % (mid, ', '.join('%.0f/%.0f' % (A[[r['y'] for r in res].index(y)], Tt[[r['y'] for r in res].index(y)]) for y in mid)))
        Pn('  years with A>0: %d of %d; A by year: %s' % ((A > 0).sum(), len(A), ' '.join('%d:%.0f' % (d['y'], a) for d, a in zip(res, A))))
    return res

# ---------- reproduce old headline (fc.py: plain variant of real panel)
Pn('FC2: revised 2027 forecast (NYC rates, K-1 60/40 view). Research only, not tax advice. $608,122 book, FIFO, BASE+L1, wash rule applied, pre-tax $, each year an independent replay (no carryforward in).')
Pn('Rates (approximate, from memory of 2025-26 law): NYC top ST 55.576% LT 38.576% ; NYC upper-middle ST 49.526% LT 29.526%. No SALT limit, no AMT. $3k loss offset valued at the ST rate. K-1 interest income ignored.')
real_res = report(True, 'REAL 2016-2025')
for var in ('plain', 'today'):
    tt = [d[var]['st'] + d[var]['lt'] for d in real_res]
    Pn('REPRODUCTION of fc.py headline (real, %s): net total p10/p25/med/p75/p90 = %s ; LT p50 = %.0f' % (var, ' / '.join('%.0f' % pc(tt, q) for q in QS), pc([d[var]['lt'] for d in real_res], 50)))
report(False, 'PROXY 2002-2025')

# ---------- 2026 actuals
Pn(); Pn('================ 2026 ACTUALS to date (Robinhood realized, before wash-sale adjustments; all symbols assumed short-term)')
VIXM, VIXY, OTH = 29295.67, 31508.36, -69747.54
TOT = VIXM + VIXY + OTH
Pn('  inputs: VIXM %+.2f, VIXY %+.2f, other symbols %+.2f, total %+.2f (given -8943.51)' % (VIXM, VIXY, OTH, TOT))
a = VIXM + VIXY
views = {'all short-term': (TOT, 0.0), 'K-1 view (VIXM+VIXY 60/40)': (OTH + 0.4 * a, 0.6 * a)}
for k, (s0, l0) in views.items():
    n = net(s0, l0, *CASES['NYC top'])
    Pn('  %-28s pre-net ST %+11.2f LT %+11.2f -> netted ST %+11.2f LT %+11.2f total %+11.2f | $3k offset %.2f | carryforward ST %+.2f LT %+.2f' % (k, s0, l0, n['s'], n['l'], n['tot'], n['off'], n['cfs'], n['cfl']))
Pn('  K-1 sleeve: 60%% LT %.2f, 40%% ST %.2f (of %.2f)' % (0.6 * a, 0.4 * a, a))
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fc2.log'), 'w').write('\n'.join(out) + '\n')
