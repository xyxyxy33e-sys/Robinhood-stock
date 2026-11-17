"""After-tax view of the calm hedge. Research only. PLAN.md Addendum 3 (pre-registered). Lot simulator adapted from review_2026_11/after_tax_test.py."""
import csv, os, sys, re, bisect, datetime as dt, multiprocessing as mp
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); PT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(PT, 'review_2026_11'))
import harness as H
from harness import MC, S
VP = os.path.join(PT, 'research_notes', 'vol_predict_2026_11')
CAPCFG = dict(H.CUR, gross_cap=2.0); EPS = 1e-12; BAND = S.REBALANCE_DRIFT_BAND
SC = {'S1': (0.35 + 0.038, 0.15 + 0.038), 'S2': (0.37 + 0.093 + 0.038, 0.20 + 0.093 + 0.038), 'Z': (0.0, 0.0)}
NAMES = ['SPMO', 'CORE', 'TQQQ', 'QLD', 'XLU', 'VIXY', 'VIXM', 'QQQ', 'BOXX']; NI = {n: i for i, n in enumerate(NAMES)}

# ------------------------------------------------------------------ data
def load_close(fn): return {r['d']: float(r['close_split_adj']) for r in csv.DictReader(open(os.path.join(HERE, fn)))}
VY = load_close('vixy_yahoo_full.csv'); VM = load_close('vixm_yahoo_full.csv')
def load_fred(fn, ds):
    d = {}
    for r in csv.reader(open(os.path.join(VP, fn))):
        try: d[r[0]] = float(r[1])
        except Exception: pass
    keys = sorted(d); out = np.full(len(ds), np.nan)
    for i, x in enumerate(ds):
        j = bisect.bisect_right(keys, x) - 1
        if j >= 0: out[i] = d[keys[j]]
    return out
class Track: pass
def make_track(tn):
    t = Track(); real = tn == 'real'; t.real = real
    t.ds = H.RD if real else H.PD; t.sg = H.sr if real else H.sig; t.pn = H.pr if real else H.p; ds, sg, pn = t.ds, t.sg, t.pn
    rr = lambda px: (lambda x: (x.__setitem__(0, 0.0), x)[1])(MC._rets(px, ds))
    t.INSTR = {'Y': rr(VY), 'M': rr(VM)}; t.cash = pn['cash']
    vd = {d: (None if np.isnan(v) else float(v)) for d, v in zip(ds, sg['vol'][0])}
    vx = S.vixm_series(ds, H.VIX, H.VIX3M, vd); VXA = np.array([bool(vx.get(d, {}).get('allowed')) for d in ds])
    cfg = CAPCFG
    w5 = MC.target_weights(sg, cfg); key = MC.regime_key(sg, cfg).astype(np.int64)[0]; cash = w5[0, :, 4].copy()
    legs = [pn['core'], pn['tqqq'], pn['qld'], pn['xlu']]; W = [w5[0, :, i] for i in range(4)]
    eff = MC._eff(sg, cfg)[0]; gate = MC._gate(sg, cfg)[0]; z = MC._zone(sg, cfg)[0]
    allowed = VXA & ~((eff == 3) & ~gate & (z == 2))
    v = np.where(allowed, cash * S.VIXM_CASH_SHARE, 0.0)
    legs.append(t.INSTR['Y']); W.append(v); used = v.copy(); key = key + allowed.astype(np.int64) * 100000
    g = np.nan_to_num(sg['gaps'][200][0]); deep = ((eff == 4) & (g <= S.DEEP_E_GAP200)).astype(float) * S.DEEP_E_CASH_SHARE; pan = H.panic_series(ds)
    for j, sh_ in enumerate((deep, pan)):
        x = np.minimum(cash * sh_, cash - used); used = used + x
        legs.append(pn['qqq']); W.append(x); key = key + (sh_ > 0).astype(np.int64) * (10 ** (6 + j))
    legs.append(pn['cash']); W.append(cash - used)
    t.Wb, t.Lb, t.kb = np.stack(W, -1), np.stack(legs, -1), key
    vix = load_fred('VIXCLS.csv', ds)
    t.C = dict(vix=vix, gap=sg['gaps'][200][0], A=(eff == 0), lev=(eff == 0) | ((eff == 3) & ~gate), sleeve=t.Wb[:, 4] > 1e-12)
    t.ticks = ['SPMO' if real else 'CORE', 'TQQQ', 'QLD', 'XLU', 'VIXY', 'QQQ', 'QQQ', 'BOXX']
    return t
TK = {'real': make_track('real'), 'proxy': make_track('proxy')}
WINS = {'real': ('real', '2015-11-02', None), 'oos': ('proxy', '2011-01-04', '2015-09-02'), 'late': ('proxy', '2015-09-02', None), 'joined': ('proxy', '2011-01-04', None)}
WIN = {}
for k, (tn, a, b) in WINS.items():
    ds = TK[tn].ds; WIN[k] = (next(i for i, d in enumerate(ds) if d >= a), len(ds) - 1 if b is None else max(i for i, d in enumerate(ds) if d <= b))
def rds(w): tn = WINS[w][0]; s0, e = WIN[w]; return TK[tn].ds[s0 + 1:e + 1]
ARMS = [('Y', 'C1', 18, .05), ('Y', 'C1', 20, .05), ('M', 'C1', 18, .10), ('Y', 'C5', None, .05), ('M', 'C5', None, .10), ('M', 'C5', None, .20), ('Y', 'C3', None, .05)]
def lab(a): return f"{'VIXY' if a[0]=='Y' else 'VIXM'} {a[1]}{'' if a[2] is None else ' T%d' % a[2]} h{a[3]*100:g}"
def active(t, fam, T):
    with np.errstate(invalid='ignore'):
        if fam == 'C1': x = t.C['vix'] < T
        elif fam == 'C3': x = np.ones(len(t.ds), bool)
        elif fam == 'C5': x = t.C['A'] & (t.C['gap'] > 0.10)
    return np.asarray(x, bool) & t.C['lev'] & ~t.C['sleeve']
def port(wn, pn_):
    """(W9, L9, key, tickers9) for 'Base' / ('A', arm) / ('M', arm)."""
    t = TK[WINS[wn][0]]; W = np.concatenate([t.Wb, np.zeros((len(t.Wb), 1))], 1); key = t.kb; hret = t.cash; tick8 = 'BOXX'
    if pn_ != 'Base':
        kind, (inst, fam, T, h) = pn_; hv = np.where(active(t, fam, T), h, 0.0); R = W[:, :4].sum(1); t2 = np.minimum(hv, R)
        sc = np.where(R > 1e-12, 1 - t2 / np.maximum(R, 1e-12), 1.0); W[:, :4] *= sc[:, None]; W[:, 8] = t2
        key = t.kb + (W[:, 8] > 1e-12).astype(np.int64) * 10 ** 8
        if kind == 'A': hret = t.INSTR[inst]; tick8 = 'VIXY' if inst == 'Y' else 'VIXM'
    return W, np.concatenate([t.Lb, hret[:, None]], 1), key, t.ticks + [tick8]

# ------------------------------------------------------------------ lot book (after_tax_test.Book, plus hedge tags, daily realized, no-wash switch)
def tax_year(st, lt, cf_st, cf_lt, r_st, r_lt):
    s, l = st + cf_st, lt + cf_lt
    if s < 0 < l:
        x = s + l; s, l = (0.0, x) if x >= 0 else (x, 0.0)
    elif l < 0 < s:
        x = s + l; s, l = (x, 0.0) if x >= 0 else (0.0, x)
    return max(s, 0) * r_st + max(l, 0) * r_lt, min(s, 0.0), min(l, 0.0)
class Book:
    def __init__(self, ords, yrs, T, nowash):
        self.ords = ords; self.yrs = yrs; self.nowash = nowash
        self.lots = [[] for _ in NAMES]; self.pend = [[] for _ in NAMES]
        self.real = {}; self.rt = {}; self.dayg = np.zeros((T, 2)); self.wash_tag = {'H': 0.0, 'O': 0.0}; self.wash_n = 0
    def yr(self, y): return self.real.setdefault(y, [0.0, 0.0])
    def tg(self, tag, y): return self.rt.setdefault((tag, y), [0.0, 0.0])
    def value(self, j, P): return sum(l[0] for l in self.lots[j]) * P[j]
    def buy(self, j, usd, P, d, tag):
        sh = usd / P[j]; o = self.ords[d]; lot = [sh, usd, o, o, sh, tag]; self.lots[j].append(lot); keep = []
        for p in self.pend[j]:
            if p[3] >= o and lot[4] > EPS:
                q = min(p[0], lot[4]); self._attach(j, lot, q, p[1] * q, p[2], p[5]); k = 0 if p[2] <= 365 else 1
                self.yr(p[4])[k] += p[1] * q; self.tg(p[5], p[4])[k] += p[1] * q; self.dayg[p[6]][k] += p[1] * q; p[0] -= q
            if p[0] > EPS and p[3] >= o: keep.append(p)
        self.pend[j] = keep
    def _attach(self, j, lot, q, loss, held, otag):
        L = self.lots[j]; i = next(k for k, x in enumerate(L) if x is lot); frac = q / lot[0]
        new = [q, lot[1] * frac + loss, lot[2], lot[2] - held, 0.0, lot[5]]
        lot[0] -= q; lot[1] *= (1 - frac); lot[4] -= q; L.insert(i + 1, new)
        if lot[0] <= EPS: L.remove(lot)
        self.wash_n += 1; self.wash_tag[otag] += loss
    def sell(self, j, usd, P, d):
        o = self.ords[d]; y = self.yrs[d]; need = usd / P[j]; L = self.lots[j]
        while need > EPS and L:
            lot = L[0]; q = min(need, lot[0]); frac = q / lot[0]; b_ord = lot[2]; tag = lot[5]
            basis = lot[1] * frac; g = q * P[j] - basis; held = o - lot[3]
            lot[0] -= q; lot[1] -= basis; lot[4] = min(lot[4], lot[0]); need -= q
            if lot[0] <= EPS * 1e3: L.pop(0)
            k = 0 if held <= 365 else 1
            self.yr(y)[k] += g; self.tg(tag, y)[k] += g; self.dayg[d][k] += g
            if g >= 0 or self.nowash: continue
            lps = -g / q; rem = q
            for r in list(L):
                if rem <= EPS: break
                if o - 30 <= r[2] <= o and r[2] != b_ord and r[4] > EPS:
                    m = min(rem, r[4]); self._attach(j, r, m, lps * m, held, tag)
                    self.yr(y)[k] += lps * m; self.tg(tag, y)[k] += lps * m; self.dayg[d][k] += lps * m; rem -= m
            if rem > EPS: self.pend[j].append([rem, lps, held, o + 30, y, tag, d])
    def unreal(self, P): return sum(sum(l[0] * P[j] - l[1] for l in self.lots[j]) for j in range(len(NAMES)))

def taxsim(wn, pn_, sc, nowash=False):
    W, L, key, tick = port(wn, pn_); tn = WINS[wn][0]; ds = TK[tn].ds; s0, e = WIN[wn]; cj = [NI[x] for x in tick]
    r_st, r_lt = SC[sc]; T = e + 1; nm = len(NAMES)
    R = np.zeros((T, nm)); seen = {}
    for col, j in enumerate(cj):
        if j in seen: assert np.allclose(R[s0:T, j], L[s0:T, col], atol=1e-12), (pn_, col, tick)
        else: R[:, j] = L[:T, col]; seen[j] = col
    P = np.ones((T, nm))
    for t in range(s0 + 1, T): P[t] = P[t - 1] * (1 + R[t])
    dates = [dt.date.fromisoformat(d) for d in ds[:T]]
    bk = Book([x.toordinal() for x in dates], [x.year for x in dates], T, nowash)
    hj = cj[8]; hedged_name = tick[8] != 'BOXX'
    colmap = [[c for c in range(9) if cj[c] == j] for j in range(nm)]
    def tgt_vec(tg): return np.array([tg[colmap[j]].sum() if colmap[j] else 0.0 for j in range(nm)])
    def tagof(j, tg): return 'H' if (hedged_name and j == hj and tg[8] > EPS) else 'O'
    h = W[s0].copy(); cost = MC.COST; tt = tgt_vec(h)
    for j in range(nm):
        if tt[j] > 0: bk.buy(j, tt[j], P[s0], s0, tagof(j, h))
    acct = [1.0]; paid = 0.0; cf = [0.0, 0.0]; paid_y = set(); trades = 0; taxby = {}
    for t in range(s0, e):
        if t > s0:
            tg = W[t]; diff = np.abs(tg - h); drift = diff.sum()
            if key[t] != key[t - 1] or drift > BAND or ((tg == 0) & (h > S.ZERO_LEG_EPS)).any():
                cost = MC.COST * drift; trades += 1
                nav = sum(bk.value(j, P[t]) for j in range(nm)); ttv = tgt_vec(tg) * nav; cur = np.array([bk.value(j, P[t]) for j in range(nm)])
                for j in range(nm):
                    if cur[j] - ttv[j] > EPS: bk.sell(j, cur[j] - ttv[j], P[t], t)
                for j in range(nm):
                    if ttv[j] - cur[j] > EPS: bk.buy(j, ttv[j] - cur[j], P[t], t, tagof(j, tg))
                h = tg.copy()
            else: cost = 0.0
            y = dates[t].year
            if sc != 'Z' and (y - 1) not in paid_y and dates[t] >= dt.date(y, 4, 15) and (y - 1) >= dates[s0].year:
                st, lt = bk.yr(y - 1); tx, cf[0], cf[1] = tax_year(st, lt, cf[0], cf[1], r_st, r_lt); paid_y.add(y - 1); taxby[y - 1] = tx
                nav = sum(bk.value(j, P[t]) for j in range(nm))
                if tx > 0:
                    f = tx / nav
                    for j in range(nm):
                        v = bk.value(j, P[t])
                        if v > 0: bk.sell(j, v * f, P[t], t)
                    paid += tx; cost = 1 - (1 - cost) * (1 - MC.COST * f / (1 - f))
        r = L[t + 1]; g = (h * r).sum()
        if cost > 0:
            for Ls in bk.lots:
                for l in Ls: l[0] *= (1 - cost); l[4] *= (1 - cost)
        h = h * (1 + r) / (1 + g); acct.append(sum(bk.value(j, P[t + 1]) for j in range(nm)))
    acct = np.array(acct); Pe = P[e]; ye = dates[e].year; st, lt = bk.yr(ye)
    tx_ytd = tax_year(st, lt, cf[0], cf[1], r_st, r_lt)[0]; tx_liq = tax_year(st, lt + bk.unreal(Pe), cf[0], cf[1], r_st, r_lt)[0]
    return dict(acct=acct, paid=paid, liq=acct[-1] - tx_liq, real=bk.real, rt=bk.rt, dayg=bk.dayg[s0:e + 1], wash_tag=bk.wash_tag, wash_n=bk.wash_n, trades=trades, taxby=taxby,
                tdates=ds[s0:e + 1])

def jobfn(j): return j, taxsim(*j)

# ------------------------------------------------------------------ analysis helpers
def shp(r): return r.mean() * 252 / (r.std(ddof=1) * 252 ** .5)
def mdd(a): return (a / np.maximum.accumulate(a) - 1).min()
def acc_ret(a): return a[1:] / a[:-1] - 1
def met(res, pre=False):
    a = res['acct']; n = len(a) - 1; ra = acc_ret(a)
    return dict(c=(a[-1] if pre else res['liq']) ** (252 / n) - 1, sh=shp(ra), m=mdd(a), n=n)
def yinfo(res):
    """per calendar year: (year, start value, end value, sessions); account index i <-> tdates[i]."""
    ds = res['tdates']; a = res['acct']; out = []
    ys = sorted({d[:4] for d in ds[1:]})
    for y in ys:
        ix = [i for i, d in enumerate(ds) if d[:4] == y and i >= 1]; i1 = ix[-1]; i0 = max(ix[0] - 1, 0)
        out.append((int(y), a[i0], a[i1], i1 - i0))
    return out
def full_years(res): return [(y, v0, v1) for y, v0, v1, n in yinfo(res) if n >= 240]
def gains_pct(res):
    """net realized (ST+LT) per full year as fraction of start-of-year value; also ST only"""
    out = {}
    for y, v0, v1 in full_years(res):
        st, lt = res['real'].get(y, [0.0, 0.0]); out[y] = ((st + lt) / v0, st / v0, lt / v0, v1 / v0 - 1)
    return out
def acc_after_tax(res, sc):
    a = res['acct']; ra = acc_ret(a); r_st, r_lt = SC[sc]; dg = res['dayg']
    adj = (r_st * dg[1:, 0] + r_lt * dg[1:, 1]) / a[1:]; r2 = ra - adj; n = len(r2); nav = np.cumprod(1 + r2)
    return dict(c=nav[-1] ** (252 / n) - 1, sh=shp(r2), m=(nav / np.maximum(np.maximum.accumulate(nav), 1) - 1).min())
def tax_seq(gdict_st_lt, sc):
    """tax per year with carryforward from dict year->(st, lt) in order."""
    r_st, r_lt = SC[sc]; cf = [0.0, 0.0]; out = {}
    for y in sorted(gdict_st_lt):
        st, lt = gdict_st_lt[y]; tx, cf[0], cf[1] = tax_year(st, lt, cf[0], cf[1], r_st, r_lt); out[y] = tx
    return out

if __name__ == '__main__':
    LOG = open(os.path.join(HERE, 'run_tax.log'), 'w')
    def log(*a):
        s = ' '.join(str(x) for x in a); print(s); LOG.write(s + '\n'); LOG.flush()
    PORTS = ['Base'] + [('A', a) for a in ARMS] + [('M', a) for a in ARMS]
    JOBS = [(w, p, sc, False) for w in WIN for p in PORTS for sc in ('Z', 'S1', 'S2')] + [(w, ('A', a), 'Z', True) for w in WIN for a in ARMS]
    import time; t0 = time.time()
    with mp.get_context('fork').Pool(4) as pool: RES = dict(pool.imap_unordered(jobfn, JOBS))
    log('=' * 130); log('run_tax.py: after-tax view of the calm hedge (PLAN.md Addendum 3). Research only. %d lot simulations in %.0fs' % (len(JOBS), time.time() - t0)); log('=' * 130)
    log("Method: after_tax_test.py lot book (FIFO, ST<=365d, wash sales +/-30d same ticker, price-only, tax for year Y paid first session on/after 15 Apr Y+1 by pro-rata sale, 2 bp, BOXX deferred, no $3k offset).")
    log("Netting/carry: ST and LT netted separately incl. carryforwards, cross-netted; a net-loss year pays no tax and the loss is carried forward (character kept) to later years' gains. Liquidation basis for after-tax CAGR (unrealized gains treated LT).")
    log(f"Rates: S1 federal ST {SC['S1'][0]*100:.1f}% (35+3.8) / LT {SC['S1'][1]*100:.1f}% (15+3.8); S2 top+CA ST {SC['S2'][0]*100:.1f}% (37+9.3+3.8) / LT {SC['S2'][1]*100:.1f}% (20+9.3+3.8). View c: no tax (zero-rate path, realized gains tracked).")
    log("After-tax Sharpe / max DD are on the taxed account's daily value changes INCLUDING the April tax-payment sales (as the existing test's MaxDD); 'acc' columns = accrual alternative (tax or credit at the rate on each day's realized ST/LT gain, no cash-flow jumps).")
    log("VIXY/VIXM treated as ordinary ETFs (commodity-pool / ETN tax treatment, 60/40 1256 for VIXM-type pools, NOT modelled). Proxy-panel core is its own ticker CORE (adds a 0.6%/yr dividend accrual); QQQ cash legs ticker QQQ; VIXY sleeve and VIXY hedge share ticker VIXY (wash sales across them); VIXM hedge ticker VIXM.")
    # sanity: zero-rate path vs engine
    for w in WIN:
        s0, e = WIN[w]
        for p in ('Base', ('A', ARMS[0]), ('M', ARMS[4])):
            W, L, key, tick = port(w, p); r, _ = MC.run_strategy(W[None, :e + 1], key[None, :e + 1], L[None, :e + 1], s0)
            a = RES[(w, p, 'Z', False)]['acct']; d = np.abs(acc_ret(a) - r[0]).max()
            assert d < 1e-9, (w, p, d)
    log("SANITY: zero-rate lot simulation reproduces MC.run_strategy daily returns (max abs diff < 1e-9) for Base / VIXY C1 T18 h5 / its matched cash... and VIXM C5 h10 MC, all 4 windows: PASS")
    H_real, _, _ = H.run(True, cfg=CAPCFG, vixm_share=0.35, vixm_ret=TK['real'].INSTR['Y'])
    log(f"SANITY real Base vs harness.run (VIXY sleeve, cap): max abs diff {np.abs(acc_ret(RES[('real','Base','Z',False)]['acct'])-H_real).max():.2e}")

    # ---------------- baselines
    log("\n=== BASELINE (Base) per window: pre-tax | S1 federal | S2 top+CA : CAGR / Sharpe / max DD  (after-tax CAGR on liquidation basis); taxes paid per $1 start; ST share of gross gains ===")
    for w in WIN:
        row = f"  {w:<7}"
        for sc, nm in (('Z', 'pre'), ('S1', 'S1'), ('S2', 'S2')):
            m = met(RES[(w, 'Base', sc, False)], sc == 'Z'); row += f" | {nm} {m['c']*100:5.1f}% / {m['sh']:.3f} / {m['m']*100:6.1f}%"
        log(row)
    # ---------------- main comparison
    def dif(w, a, sc):
        A = met(RES[(w, ('A', a), sc, False)], sc == 'Z'); M = met(RES[(w, ('M', a), sc, False)], sc == 'Z'); return A, M
    log("\n=== ARM vs MATCHED CASH, pre-tax vs after-tax (differences arm minus matched cash: dCAGR pp / dSharpe / dmaxDD pp) ===")
    log("  columns: pre-tax | S1 federal | S2 top+CA | accrual S1 (dCAGR/dSh) | accrual S2 ;  arm and MC levels for S2 shown in the detail block below")
    DIFF = {}
    for w in WIN:
        log(f" window {w}")
        for a in ARMS:
            row = f"  {lab(a):<16}"
            for sc in ('Z', 'S1', 'S2'):
                A, M = dif(w, a, sc); d = (A['c'] - M['c'], A['sh'] - M['sh'], A['m'] - M['m']); DIFF[(w, a, sc)] = d
                row += f" | {d[0]*100:+6.2f} / {d[1]:+.3f} / {d[2]*100:+5.2f}"
            for sc in ('S1', 'S2'):
                A = acc_after_tax(RES[(w, ('A', a), 'Z', False)], sc); M = acc_after_tax(RES[(w, ('M', a), 'Z', False)], sc); DIFF[(w, a, 'acc' + sc)] = (A['c'] - M['c'], A['sh'] - M['sh'])
                row += f" | acc{sc} {DIFF[(w,a,'acc'+sc)][0]*100:+6.2f} / {DIFF[(w,a,'acc'+sc)][1]:+.3f}"
            log(row)
    log("\n=== DETAIL: arm / matched cash levels (CAGR / Sharpe / maxDD), pre-tax and S2 ===")
    for w in WIN:
        log(f" window {w}")
        for a in ARMS:
            row = f"  {lab(a):<16}"
            for sc in ('Z', 'S1', 'S2'):
                A, M = dif(w, a, sc); row += f" | {sc}: {A['c']*100:5.1f}/{A['sh']:.3f}/{A['m']*100:6.1f}  MC {M['c']*100:5.1f}/{M['sh']:.3f}/{M['m']*100:6.1f}"
            log(row)
    # ---------------- view c: dollars
    log("\n=== VIEW C: net realized gain per full calendar year (ST+LT after wash adjustments; no tax drag), mean / median, $ per $600k of start-of-year account value and % of NAV; pre-tax P&L $ same basis ===")
    log("  full year = >= 240 sessions in the window (real: 2016-2025; oos: 2011-2014; late: 2016-2025; joined: 2011-2025)")
    GIVE = {}
    def vc(res):
        g = gains_pct(res); gv = np.array([v[0] for v in g.values()]); pv = np.array([v[3] for v in g.values()]); stv = np.array([v[1] for v in g.values()])
        return dict(g=gv, p=pv, st=stv, n=len(gv), years=list(g))
    for w in WIN:
        log(f" window {w}")
        b = vc(RES[(w, 'Base', 'Z', False)])
        log(f"  {'Base':<22} gain mean ${b['g'].mean()*6e5:10,.0f} median ${np.median(b['g'])*6e5:10,.0f} ({b['g'].mean()*100:5.1f}% / {np.median(b['g'])*100:5.1f}% NAV); ST share {b['st'].sum()/b['g'].sum()*100:.1f}%; pre-tax P&L mean ${b['p'].mean()*6e5:10,.0f}")
        for a in ARMS:
            A = vc(RES[(w, ('A', a), 'Z', False)]); M = vc(RES[(w, ('M', a), 'Z', False)])
            dg = (M['g'].mean() - A['g'].mean()) * 6e5; dp = (M['p'].mean() - A['p'].mean()) * 6e5
            GIVE[(w, a)] = (dg, dp, dp / dg if dg > 0 else np.nan)
            log(f"  {lab(a):<22} arm mean ${A['g'].mean()*6e5:10,.0f} med ${np.median(A['g'])*6e5:10,.0f} ({A['g'].mean()*100:5.1f}%/{np.median(A['g'])*100:5.1f}%) | MC mean ${M['g'].mean()*6e5:10,.0f} med ${np.median(M['g'])*6e5:10,.0f} ({M['g'].mean()*100:5.1f}%/{np.median(M['g'])*100:5.1f}%) | "
                f"gain removed/yr ${dg:+9,.0f}; pre-tax P&L given up/yr ${dp:+9,.0f}; ratio {('%.2f' % (dp/dg)) if dg > 0 else 'n/a (gain not reduced)'}")
    # ---------------- realized by year
    log("\n=== REALIZED GAIN/LOSS BY CALENDAR YEAR (no-tax path), % of start-of-year NAV: book ST / LT for arm and MC; hedge leg ST / LT (arm only; matched-cash hedge share sits in BOXX and is not separable) ===")
    def tagy(res, tag, y):
        st, lt = res['rt'].get((tag, y), [0.0, 0.0]); return st, lt
    for w in ('real', 'oos'):
        log(f" window {w}")
        for a in ARMS:
            A = RES[(w, ('A', a), 'Z', False)]; M = RES[(w, ('M', a), 'Z', False)]; yi = {y: (v0, v1, n) for y, v0, v1, n in yinfo(A)}; yim = {y: v0 for y, v0, v1, n in yinfo(M)}
            log(f"  {lab(a)}")
            for y in sorted(yi):
                v0 = yi[y][0]; ast, alt = A['real'].get(y, [0, 0]); mst, mlt = M['real'].get(y, [0, 0]); hst, hlt = tagy(A, 'H', y)
                log(f"    {y}{'*' if yi[y][2] < 240 else ' '} book arm ST {ast/v0*100:+7.2f} LT {alt/v0*100:+6.2f} | MC ST {mst/yim[y]*100:+7.2f} LT {mlt/yim[y]*100:+6.2f} | hedge leg ST {hst/v0*100:+6.2f} LT {hlt/v0*100:+5.2f}")
    log("  (* = partial year; ST share of the book's realized gains is ~100% in every path, as in the existing test)")
    # ---------------- wash sales
    log("\n=== WASH SALES ON THE HEDGE LEG (no-tax path): deferral across year-ends = positive part, by year, of (hedge-lot realized with the wash rule minus without it), % of start-of-year NAV; the rest of the disallowed loss is released within the same year ===")
    WSH = {}
    for w in WIN:
        log(f" window {w}")
        for a in ARMS:
            A = RES[(w, ('A', a), 'Z', False)]; N = RES[(w, ('A', a), 'Z', True)]; v0y = {y: v0 for y, v0, v1, n in yinfo(A)}; ys = sorted(v0y)
            sh_ = {y: (sum(A['rt'].get(('H', y), [0, 0])) - sum(N['rt'].get(('H', y), [0, 0]))) / v0y[y] * 100 for y in ys}   # % of start-of-year NAV
            pos = [max(v, 0) for v in sh_.values()]; across = float(np.mean(pos)); mx = max(pos)
            hnw = np.mean([sum(N['rt'].get(('H', y), [0, 0])) / v0y[y] * 100 for y in ys])
            WSH[(w, a)] = (A['wash_tag']['H'], across, sh_)
            log(f"  {lab(a):<16} mean hedge realized without wash rule {hnw:+.3f}% NAV/yr; across-year-end deferral (loss pushed into a later tax year): mean {across:.3f}% NAV per year, worst year {mx:.3f}% NAV; "
                f"hedge wash events (book total) {A['wash_n']}; disallowed hedge loss counted per event incl. re-washes {A['wash_tag']['H']:.2f} per $1 start (inflated by compounding and chains; use the % columns)")
    log("  yearly shift (with minus without wash rule, hedge lots, % of start-of-year NAV), real window; + = loss pushed out of that year, - = loss arriving from earlier years")
    for a in ARMS:
        sh_ = WSH[('real', a)][2]; log(f"    {lab(a):<16} " + ' '.join(f"{y}:{v:+.3f}" for y, v in sh_.items()))
    # ---------------- year by year featured arms
    log("\n=== YEAR BY YEAR, real window, accrual basis (S2 top+CA): pre-tax return diff vs matched cash; hedge-leg realized P&L (% of start NAV); tax saved vs MC (tax on that year's gains with carryforward, % of start NAV); after-tax return diff = pre + saved ===")
    for a in (ARMS[0], ARMS[4]):
        A = RES[('real', ('A', a), 'Z', False)]; M = RES[('real', ('M', a), 'Z', False)]
        yA = {y: (v0, v1) for y, v0, v1, n in yinfo(A)}; yM = {y: (v0, v1) for y, v0, v1, n in yinfo(M)}
        tA = tax_seq({y: tuple(A['real'].get(y, [0, 0])) for y in yA}, 'S2'); tM = tax_seq({y: tuple(M['real'].get(y, [0, 0])) for y in yM}, 'S2')
        log(f"  {lab(a)}   (year: pre-tax diff pp | hedge realized % NAV | tax arm % | tax MC % | tax saved pp | after-tax diff pp)")
        tot = [0, 0, 0]
        for y in sorted(yA):
            pre = ((yA[y][1] / yA[y][0]) - (yM[y][1] / yM[y][0])) * 100; hr = sum(A['rt'].get(('H', y), [0, 0])) / yA[y][0] * 100
            ta, tm = tA[y] / yA[y][0] * 100, tM[y] / yM[y][0] * 100; sv = tm - ta
            log(f"    {y}  {pre:+7.2f} | {hr:+6.2f} | {ta:6.2f} | {tm:6.2f} | {sv:+6.2f} | {pre+sv:+7.2f}"); tot[0] += pre; tot[1] += sv
        log(f"    sum   {tot[0]:+7.2f}   (pre-tax diffs, simple sum)  tax saved {tot[1]:+.2f}  after-tax {tot[0]+tot[1]:+.2f}")
    # ---------------- arithmetic check
    log("\n=== ARITHMETIC CHECK (S1 / S2): cumulative tax saved vs MC divided by cumulative net realized gain removed vs MC (accrual basis over full years); must be <= ST rate ===")
    flags = 0
    for w in WIN:
        for a in ARMS:
            A = RES[(w, ('A', a), 'Z', False)]; M = RES[(w, ('M', a), 'Z', False)]
            yA = {y: v0 for y, v0, v1 in full_years(A)}; yM = {y: v0 for y, v0, v1 in full_years(M)}
            out = []
            for sc in ('S1', 'S2'):
                tA = tax_seq({y: tuple(A['real'].get(y, [0, 0])) for y in yA}, sc); tM = tax_seq({y: tuple(M['real'].get(y, [0, 0])) for y in yM}, sc)
                dtax = sum(tM[y] / yM[y] - tA[y] / yA[y] for y in yA); dg = sum(sum(M['real'].get(y, [0, 0])) / yM[y] - sum(A['real'].get(y, [0, 0])) / yA[y] for y in yA)
                ratio = dtax / dg if abs(dg) > 1e-9 else np.nan; bad = (not np.isnan(ratio)) and dg > 0 and ratio > SC[sc][0] + 1e-6
                flags += bad; out.append(f"{sc}: gain removed {dg*100:+.2f}% NAV-yrs, tax saved {dtax*100:+.2f}, ratio {ratio:.3f} (ST rate {SC[sc][0]:.3f}){' FLAG' if bad else ''}")
            log(f"  {w:<7}{lab(a):<16}" + ' | '.join(out))
    log(f"  flags where ratio exceeds the ST rate: {flags}")
    log("  Also (pre-tax vs after-tax for the hedge leg): after-tax diff should lie between pre-tax diff and pre-tax diff x (1 - rate) when the hedge leg loses money and the gains it removes are taxed at the ST rate -- see table above; deviations come from Sharpe/drawdown effects, compounding and carryforward timing.")
    # ---------------- verdicts
    log("\n=== VERDICTS under the pre-registered reading rule ===")
    log("  rescue: arm beats matched cash on CAGR and Sharpe after tax under S1 and S2 in BOTH oos and late windows; partly: flips only late, or only one tax view; else no change")
    for a in ARMS:
        ok = {(w, sc): DIFF[(w, a, sc)][0] > 0 and DIFF[(w, a, sc)][1] > 0 for w in ('oos', 'late') for sc in ('S1', 'S2')}
        pre_ok = {w: DIFF[(w, a, 'Z')][0] > 0 and DIFF[(w, a, 'Z')][1] > 0 for w in ('oos', 'late')}
        flip = {(w, sc): ok[(w, sc)] and not pre_ok[w] for (w, sc) in ok}
        resc = all(ok.values())
        late_only = flip[('late', 'S1')] and flip[('late', 'S2')] and not any(flip[('oos', sc)] for sc in ('S1', 'S2'))
        one_view = any(flip.values()) and not resc
        v = 'RESCUED' if resc else ('PARTLY' if (late_only or one_view) else 'NO CHANGE')
        pre = {w: DIFF[(w, a, 'Z')] for w in ('oos', 'late')}
        log(f"  {lab(a):<16} {v:<10} flips (pre-tax fails CAGR or Sharpe -> after-tax passes both): {[k for k, x in flip.items() if x] or 'none'}; after-tax passes: {[k for k, x in ok.items() if x] or 'none'}")
        log(f"{'':20}oos pre dC/dSh {pre['oos'][0]*100:+.2f}/{pre['oos'][1]:+.3f} -> S1 {DIFF[('oos',a,'S1')][0]*100:+.2f}/{DIFF[('oos',a,'S1')][1]:+.3f} S2 {DIFF[('oos',a,'S2')][0]*100:+.2f}/{DIFF[('oos',a,'S2')][1]:+.3f} | late pre {pre['late'][0]*100:+.2f}/{pre['late'][1]:+.3f} -> S1 {DIFF[('late',a,'S1')][0]*100:+.2f}/{DIFF[('late',a,'S1')][1]:+.3f} S2 {DIFF[('late',a,'S2')][0]*100:+.2f}/{DIFF[('late',a,'S2')][1]:+.3f}")
    log(f"\nrun time {time.time()-t0:.0f}s")
