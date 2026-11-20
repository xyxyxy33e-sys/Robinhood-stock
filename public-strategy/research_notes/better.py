"""2026-11-20, owner: "find something better than this". Structurally different designs against the live strategy,
all through ONE engine with the same costs and taxes. Run: PUB_CACHE=<dir> PUB_END=2026-11-19 python3 better.py
Tax: as backtest.py (38.8% short-term and interest, 18.8% long-term, paid each year end, liquidated at the end), PLUS
tax on fund distributions, which backtest.py leaves out: 18.8% on stock-fund dividends, 38.8% on bond and REIT income.
Pre-registered candidates (written before any was run):
  live      the live rules (1% band, fallback filter, VIX leg 25%, SSO vol target 30%, top-2 rotation)
  band2/3   live with a 2% / 3% band on the 200-day rule (fewer, later switches; logged before as tax-motivated only)
  novt      live without the vol target (reference)
  core50    50% VTI bought once and never sold + 50% live, never rebalanced
  gem       dual momentum: VTI or EFA by 12-month return if it beats T-bills, else IEF; monthly; 100% in one fund
  gtaa7     the 7 rotation funds at 1/7 each, each held only above its 10-month average, else cash; monthly
  trend1x   VTI at 100% while SPY is above its 200-day (1% band), else the fallback: the live trend rule unlevered
  live+gtaa live trend half + gtaa7 as the other half
  static    VTI 45 / EFA 15 / IEF 25 / GLD 15 bought once, never traded
  spy       SPY bought once"""
import os, sys, datetime as dt
_bt = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backtest.py'); src = open(_bt).read()
exec(src[:src.index("def run(start, mode='P', tax=False):")].replace('os.path.abspath(__file__)', repr(_bt)))
QUAL = {'VTI', 'SPY', 'SSO', 'EFA', 'EEM', 'GLD', 'DBC'}
DY = {}
for s in SY:
    ev = (_dl(s).get('events') or {}).get('dividends') or {}; raw = _raw(s); rd = sorted(raw); a = np.zeros(n)
    for v in ev.values():
        d = dt.datetime.utcfromtimestamp(v['date']).date().isoformat()
        if d in px[s] and d in dates:
            prev = [x for x in rd if x < d]
            if prev: a[dates.index(d)] += v['amount'] / raw[prev[-1]]
    DY[s] = a
mi = {i: k for k, i in enumerate(me)}

class Live:
    def __init__(s, band=0.01, vt=0.30, panic=0.25, lev1x=False, rot='top2', trend=True):
        s.band, s.vt, s.panic, s.lev1x, s.rot_kind, s.trend = band, vt, panic, lev1x, rot, trend; s.vsq = _vsq(vt)
        s.on = None; s.rot = {}; s.iefok = True; s.pan = False; s.vsp = 1.0
    def step(s, i):
        tr = False
        if not np.isnan(sma[i]):
            g = X['SPY'][i] / sma[i] - 1; new = (g > s.band) if s.on is None else ((g > -s.band) if s.on else (g > s.band))
            if new != s.on: s.on = new; tr = True
        if i in mes and mi[i] >= 10:
            j = me[mi[i] - 6]; cr = np.prod(1 + C[j + 1:i + 1]) - 1
            if s.rot_kind == 'top2':
                nr = {}
                for m, t in sorted(((X[t][i] / X[t][j] - 1, t) for t in ROT), reverse=True)[:2]:
                    if m > cr: nr[t] = 0.5
            elif s.rot_kind == 'none': nr = {}
            else:
                nr = {t: 1 / 7 for t in ROT if X[t][i] > np.mean([X[t][me[mi[i] - k]] for k in range(10)])}
            if nr != s.rot: s.rot = nr; tr = True
            ok = X['IEF'][i] / X['IEF'][j] - 1 > cr
            if ok != s.iefok:
                s.iefok = ok
                if s.on is not None and not s.on: tr = True
        vs = s.vsq[i] if (s.on and not s.lev1x) else 1.0
        if vs != s.vsp: s.vsp = vs; tr = True
        pn = bool(PANIC[i]) and s.on is not None and not s.on and s.panic > 0 and not s.lev1x
        if pn != s.pan: s.pan = pn; tr = True
        return tr
    def target(s):
        th = 0.5 if s.rot_kind != 'none' else 1.0; t = {}
        if s.trend and s.on is not None:
            if s.on: t['VTI' if s.lev1x else 'SSO'] = th * s.vsp
            elif s.iefok: t['IEF'] = th * (1 - s.panic if s.pan else 1)
            if s.pan: t['SSO'] = t.get('SSO', 0) + th * s.panic * 0.5
        if s.rot_kind != 'none':
            rh = 0.5 if s.trend else 1.0
            for k, x in s.rot.items(): t[k] = t.get(k, 0) + x * rh
        return t
class Gem:
    def __init__(s): s.h = None
    def step(s, i):
        if i in mes and mi[i] >= 12:
            j = me[mi[i] - 12]; cr = np.prod(1 + C[j + 1:i + 1]) - 1; a, b = X['VTI'][i] / X['VTI'][j] - 1, X['EFA'][i] / X['EFA'][j] - 1
            h = 'VTI' if (a >= b and a > cr) else 'EFA' if (b > a and b > cr) else 'IEF'
            if h != s.h: s.h = h; return True
        return False
    def target(s): return {s.h: 1.0} if s.h else {}
class Static:
    def __init__(s, w): s.w = w
    def step(s, i): return False
    def target(s): return dict(s.w)

def sim(mk, start='2007-07-02', end='9999', tax=False):
    st_ = mk(); s0 = next(i for i, d in enumerate(dates) if d >= start); e0 = max(i for i, d in enumerate(dates) if d <= end)
    for i in range(200, s0): st_.step(i)
    w = {}; V = 1.0; out = []; basis = {}; opened = {}; gst = glt = ordi = qd = cf = 0.0; yr = dates[s0][:4]; ntr = 0; turn = 0.0
    for i in range(s0, e0 + 1):
        if i > s0:
            r = sum(w[s] * R[s][i] for s in w) + (1 - sum(w.values())) * C[i]
            ordi += V * (1 - sum(w.values())) * C[i]
            for s in w:
                if DY[s][i]:
                    if s in QUAL: qd += V * w[s] * DY[s][i]
                    else: ordi += V * w[s] * DY[s][i]
            V *= 1 + r; w = {s: w[s] * (1 + R[s][i]) / (1 + r) for s in w}
            if tax and dates[i][:4] != yr:
                nst = gst + cf; t = max(nst, 0) * 0.388 + max(glt + min(nst, 0), 0) * 0.188 + max(ordi, 0) * 0.388 + qd * 0.188
                cf = min(nst + glt, 0) if nst + glt < 0 else 0.0
                for s in list(basis): basis[s] *= (1 - t / V) if V > 0 else 1
                V -= t; gst = glt = ordi = qd = 0.0; yr = dates[i][:4]
            out.append(V)
        if st_.step(i) or i == s0:
            t = st_.target()
            if i > s0: ntr += 1
            for s in set(w) | set(t):
                a, b = w.get(s, 0) * V, t.get(s, 0) * V
                if b < a - 1e-12:
                    frac = (a - b) / a; gain = (a - basis.get(s, a)) * frac
                    if (np.datetime64(dates[i]) - np.datetime64(opened.get(s, dates[i]))).astype(int) > 365: glt += gain
                    else: gst += gain
                    basis[s] = basis.get(s, a) * (1 - frac)
                elif b > a + 1e-12:
                    if a <= 1e-12: opened[s] = dates[i]
                    basis[s] = basis.get(s, 0) + (b - a)
                V -= 0.0005 * abs(b - a)
                if i > s0: turn += abs(b - a) / V
            w = {s: v for s, v in t.items() if v > 0}
    if tax:
        un = sum(w[s] * V - basis.get(s, 0) for s in w)
        V -= max(un + glt + min(gst + cf, 0), 0) * 0.188 + max(gst + cf, 0) * 0.388 + max(ordi, 0) * 0.388 + qd * 0.188; out[-1] = V
    return np.array(out), dates[s0 + 1:e0 + 1], ntr, turn
def stats(nav, ds):
    nav = np.r_[1.0, nav]; r = nav[1:] / nav[:-1] - 1; v = r.std(ddof=1) * 252 ** .5; u = nav / np.maximum.accumulate(nav) - 1; yr = {}
    for d, x in zip(ds, r): yr.setdefault(d[:4], []).append(x)
    return (nav[-1] ** (252 / len(r)) - 1) * 100, r.mean() * 252 / v, u.min() * 100, min(np.prod(1 + np.array(a)) - 1 for a in yr.values()) * 100
def blend(mks, wts, **k):
    res = [sim(m, **k) for m in mks]; nav = sum(x * a[0] for x, a in zip(wts, res)); return nav, res[0][1], sum(a[2] for a in res), sum(x * a[3] for x, a in zip(wts, res))
C_ = {
 'live': lambda **k: sim(lambda: Live(), **k), 'band2': lambda **k: sim(lambda: Live(band=.02), **k), 'band3': lambda **k: sim(lambda: Live(band=.03), **k),
 'novt': lambda **k: sim(lambda: Live(vt=None), **k),
 'core50': lambda **k: blend([lambda: Live(), lambda: Static({'VTI': 1.0})], [.5, .5], **k),
 'gem': lambda **k: sim(Gem, **k),
 'gtaa7': lambda **k: sim(lambda: Live(rot='gtaa', trend=False), **k),
 'trend1x': lambda **k: sim(lambda: Live(lev1x=True, rot='none'), **k),
 'live+gtaa': lambda **k: sim(lambda: Live(rot='gtaa'), **k),
 'static': lambda **k: sim(lambda: Static({'VTI': .45, 'EFA': .15, 'IEF': .25, 'GLD': .15}), **k),
 'spy': lambda **k: sim(lambda: Static({'SPY': 1.0}), **k)}
if __name__ == '__main__':
    only = sys.argv[1:] or list(C_)
    print(f"{'':10s}|   full period before tax     | after tax        | 2007-2015 pre / after tax | 2016-2026 pre / after tax | trade days/yr turnover/yr")
    print(f"{'':10s}|  CAGR Sharpe  MaxDD worst yr |  CAGR   MaxDD    |  CAGR Sharpe MaxDD | CAGR  |  CAGR Sharpe MaxDD | CAGR  |")
    for nm in only:
        f = C_[nm]; a = f(); b = f(tax=True); yrs_ = len(a[1]) / 252
        h1 = f(end='2015-12-31'); h1t = f(end='2015-12-31', tax=True); h2 = f(start='2016-01-04'); h2t = f(start='2016-01-04', tax=True)
        sa, sb, s1, s1t, s2, s2t = (stats(x[0], x[1]) for x in (a, b, h1, h1t, h2, h2t))
        print(f"{nm:10s}| {sa[0]:5.1f} {sa[1]:5.2f} {sa[2]:6.1f} {sa[3]:6.1f}   | {sb[0]:5.1f} {sb[2]:6.1f}    | {s1[0]:5.1f} {s1[1]:5.2f} {s1[2]:6.1f} | {s1t[0]:5.1f} | {s2[0]:5.1f} {s2[1]:5.2f} {s2[2]:6.1f} | {s2t[0]:5.1f} | {a[2] / yrs_:5.1f}  {a[3] / yrs_ * 100:5.0f}%")
