"""Wash-sale-aware substitute test on the live BASE trade stream (research only)."""
import sys, os, csv, datetime as dt, json
sys.dont_write_bytecode = True
sys.path.insert(0, '/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad/rob')
import numpy as np
import eng
from eng import X, H, pr, MC
RD = H.RD
COST = MC.COST; BAND = MC.S.REBALANCE_DRIFT_BAND; ZE = MC.S.ZERO_LEG_EPS
BOOK0 = 600000.0
R_ST, R_LT = 0.37 + 0.133, 0.20 + 0.038 + 0.133
EPS = 1e-9

TK = ['SPMO', 'TQQQ', 'QLD', 'XLU', 'VIXY', 'QQQ', 'BOXX', 'VIXM', 'MTUM']
TI = {t: i for i, t in enumerate(TK)}
LEV = {'SPMO': 1, 'TQQQ': 3, 'QLD': 2, 'XLU': 1, 'QQQ': 1, 'MTUM': 1}
LEG2T = {'core': 'SPMO', 'tqqq': 'TQQQ', 'qld': 'QLD', 'xlu': 'XLU', 'vix': 'VIXY', 'qqq': 'QQQ', 'cash': 'BOXX'}

def load_mtum():
    d = {r['d']: float(r['c']) for r in csv.DictReader(open('/home/user/Robinhood-stock/data/mtum_yahoo_tr.csv'))}
    last = d[max(d)]
    px = np.array([d.get(x, np.nan) for x in RD])
    # carry last value forward on missing days
    for i in range(len(px)):
        if np.isnan(px[i]): px[i] = px[i - 1] if i > 0 else last
    r = np.zeros(len(px)); r[1:] = px[1:] / px[:-1] - 1
    return r
MTUM_R = load_mtum()

def setpanel(real):
    global base, W7, R, S0, T, P, DATES, ORD, YR, RD, key, EFF
    pn = pr if real else eng.p
    RD = pn['dates']
    base = eng.run(eng.NOV, real)
    BN = base['names']; BW = base['W']
    W7 = np.zeros((BW.shape[0], len(TK)))
    for i, n in enumerate(BN): W7[:, TI[LEG2T[n]]] += BW[:, i]
    _, Lleg, key, _ = eng.weights(eng.NOV, real)
    R = np.zeros((BW.shape[0], len(TK))); seen = set()
    for i, n in enumerate(BN):
        tk = LEG2T[n]
        if tk not in seen: R[:, TI[tk]] = Lleg[:, i]; seen.add(tk)
    if real:
        R[:, TI['VIXM']] = H.VIXM_R; R[:, TI['MTUM']] = MTUM_R
    S0 = base['s0']; T = len(RD)
    P = np.ones((T, len(TK)))
    for t in range(S0 + 1, T): P[t] = P[t - 1] * (1 + R[t])
    DATES = [dt.date.fromisoformat(d) for d in RD]
    ORD = [d.toordinal() for d in DATES]; YR = [d.year for d in DATES]
    sgf, _ = eng.SG[True]
    sg = X.sl(sgf, eng.OFF) if real else sgf
    EFF = MC._eff(sg, eng.cfg_for(eng.NOV))[0]
setpanel(True)

# ---------------- substitution rules
K_VIX = 2.0     # VIXM weight per unit VIXY weight (hedge ratio = slope of VIXY on VIXM, 2.01)
RULES = {
 'BASE': {},
 'S1L': {'TQQQ': [('QLD', 1.5)], 'QLD': [('TQQQ', 2 / 3)]},                       # leveraged pair only
 'S1': {'TQQQ': [('QLD', 1.5)], 'QLD': [('TQQQ', 2 / 3)], 'SPMO': [('QQQ', 1.0)], 'VIXY': [('VIXM', K_VIX)],
        'QQQ': [('QLD', 0.5)]},
 'S1m': {'TQQQ': [('QLD', 1.5)], 'QLD': [('TQQQ', 2 / 3)], 'SPMO': [('MTUM', 1.0), ('QQQ', 1.0)], 'VIXY': [('VIXM', K_VIX)],
         'QQQ': [('QLD', 0.5)]},
 'S2': {'TQQQ': [('QQQ', 3.0)], 'QLD': [('QQQ', 2.0)]},
 'S3': {'TQQQ': [('QLD', 1.5), ('QQQ', 3.0)], 'QLD': [('TQQQ', 2 / 3), ('QQQ', 2.0)], 'SPMO': [('QQQ', 1.0)],
        'VIXY': [('VIXM', K_VIX)], 'QQQ': [('QLD', 0.5)]},
 'S3L': {'TQQQ': [('QLD', 1.5), ('QQQ', 3.0)], 'QLD': [('TQQQ', 2 / 3), ('QQQ', 2.0)]},
}
ORDER = ['TQQQ', 'QLD', 'SPMO', 'VIXY', 'QQQ']

def tax_year(st, lt, cst, clt):
    s, l = st + cst, lt + clt
    if s < 0 < l:
        x = s + l; s, l = (0.0, x) if x >= 0 else (x, 0.0)
    elif l < 0 < s:
        x = s + l; s, l = (x, 0.0) if x >= 0 else (0.0, x)
    tax = max(s, 0) * R_ST + max(l, 0) * R_LT
    if s < 0 or l < 0:
        net = min(s, 0) + min(l, 0); off = min(3000.0, -net)
        tax -= off * R_ST
        take = min(off, -min(s, 0)); s += take; off2 = off - take; l += off2
    return tax, min(s, 0.0), min(l, 0.0)

class Book:
    nowash = False
    def __init__(self, method, ident):
        self.method = method; self.sec = {t: t for t in TK}
        if ident: self.sec['TQQQ'] = self.sec['QLD'] = 'LEV'
        self.lots = {t: [] for t in TK}          # lot = [sh, basis, buy_ord, hp_ord, cap, tag]
        self.pend = {}                           # sec -> list [rem_sh, loss/sh, held, expiry, year, origin_tk]
        self.real = {}; self.wash_by_year = {}; self.wash_usd = 0.0; self.wash_n = 0
        self.events = []                         # (date, tk, disallowed$)
    def _rm(self, L, lot):
        for i, x in enumerate(L):
            if x is lot: del L[i]; return
    def yr(self, y): return self.real.setdefault(y, [0.0, 0.0])
    def val(self, tk, t, tag='ALL'):
        return sum(l[0] for l in self.lots[tk] if tag == 'ALL' or l[5] == tag) * P[t, TI[tk]]
    def blocked(self, tk, t, thr):
        o = ORD[t]
        tot = 0.0
        for p in self.pend.get(self.sec[tk], []):
            if p[3] >= o and p[0] > EPS: tot += p[0] * p[1]
        return tot > thr
    def _attach(self, tk, lot, q, loss, held, o, y):
        L = self.lots[tk]; i = next(k for k, x in enumerate(L) if x is lot); frac = q / lot[0]
        new = [q, lot[1] * frac + loss, lot[2], lot[2] - held, 0.0, lot[5]]
        lot[0] -= q; lot[1] *= (1 - frac); lot[4] -= q
        L.insert(i + 1, new)
        if lot[0] <= EPS: self._rm(L, lot)
        self.wash_n += 1; self.wash_usd += loss; self.wash_by_year[y] = self.wash_by_year.get(y, 0.0) + loss
    seed = 0.0; qlog = None
    def buy(self, tk, usd, t, tag=None):
        sh = usd / P[t, TI[tk]]; o = ORD[t]; lot = [sh, usd, o, o, sh, tag]
        if tk == 'TQQQ' and self.seed > 0: lot[1] += self.seed; self.seed = 0.0
        self.lots[tk].append(lot)
        s = self.sec[tk]; keep = []
        for p in self.pend.get(s, []):
            if p[3] >= o and lot[4] > EPS and p[0] > EPS:
                conv = P[t, TI[tk]] / P[t, TI[p[5]]]                 # replacement shares -> origin-ticker equivalent shares
                q_eq = min(p[0], lot[4] * conv); q = q_eq / conv
                if q > EPS:
                    self._attach(tk, lot, q, p[1] * q_eq, p[2], o, p[4])
                    k = 0 if p[2] <= 365 else 1
                    self.yr(p[4])[k] += p[1] * q_eq                   # remove provisional loss
                    self.events.append((DATES[t].isoformat(), tk, p[1] * q_eq, 'fwd'))
                    p[0] -= q_eq
            if p[0] > EPS and p[3] >= o: keep.append(p)
        self.pend[s] = keep
    def sell(self, tk, usd, t, tagsel):
        """tagsel: None -> own lots (tag None); a primary name -> lots tagged for it; 'ALL' -> any"""
        o = ORD[t]; y = YR[t]; px = P[t, TI[tk]]; need = usd / px; L = self.lots[tk]; s = self.sec[tk]
        losses = []
        elig = [l for l in L if tagsel == 'ALL' or l[5] == tagsel]
        if self.method == 'FIFO': elig.sort(key=lambda l: l[2])
        else: elig.sort(key=lambda l: -l[1] / l[0])
        for lot in elig:
            if need <= EPS: break
            if lot[0] <= EPS or not any(x is lot for x in L): continue
            q = min(need, lot[0]); frac = q / lot[0]; basis = lot[1] * frac; g = q * px - basis; held = o - lot[3]
            b_ord = lot[2]; lot[0] -= q; lot[1] -= basis; lot[4] = min(lot[4], lot[0]); need -= q
            if lot[0] <= EPS * 1e3: self._rm(L, lot)
            k = 0 if held <= 365 else 1
            self.yr(y)[k] += g
            if self.qlog is not None and g > 0: self.qlog[(DATES[t].month - 1) // 3] = self.qlog.get((DATES[t].month - 1) // 3, 0.0) + g
            if g >= -1e-9: continue
            losses.append((q, -g / q, held, b_ord, k))
        if Book.nowash: losses = []
        for q, lps, held, b_ord, k in losses:
            rem = q
            for tk2 in TK:
                if self.sec[tk2] != s: continue
                for r in list(self.lots[tk2]):                        # backward window (shares still held after the sale)
                    if rem <= EPS: break
                    if o - 30 <= r[2] <= o and r[2] != b_ord and r[4] > EPS:
                        conv = P[t, TI[tk2]] / px
                        m_eq = min(rem, r[4] * conv); m = m_eq / conv
                        if m > EPS:
                            self._attach(tk2, r, m, lps * m_eq, held, r[2], y)
                            self.yr(y)[k] += lps * m_eq; rem -= m_eq
                            self.events.append((DATES[t].isoformat(), tk, lps * m_eq, 'bwd'))
            if rem > EPS: self.pend.setdefault(s, []).append([rem, lps, held, o + 30, y, tk])
    def unreal(self, t, tag='ALL', tk_only=None):
        a = b = 0.0
        for tk in TK:
            if tk_only and tk != tk_only: continue
            for l in self.lots[tk]:
                if tag != 'ALL' and l[5] != tag: continue
                g = l[0] * P[t, TI[tk]] - l[1]
                if (ORD[t] - l[3]) > 365: b += g
                else: a += g
        return a, b

REBLOG = []
def simulate(rule, method='FIFO', ident=False, sb='guard', taxed=True, i0=None, i1=None, book0=None, seed=0.0, qlog=None, init_w=None, thr_frac=0.0005, mtum=None, guard_frac=0.0005, maxwait=45, verbose=False):
    cands = RULES[rule]
    i0 = S0 if i0 is None else i0; i1 = (T - 1) if i1 is None else i1
    bk = Book(method, ident); bk.seed = seed; bk.qlog = qlog
    h = np.zeros((len(TK)))
    nav0 = BOOK0 if book0 is None else book0
    # ---- helper to build T1 and per-(ticker,tag) targets
    def targets(t, T0, nav, state):
        """returns dict (tk, tag)->weight, plus dict of informative flags"""
        thr = thr_frac * nav
        tg = {}
        sub_active = {}
        avail = T0[TI['BOXX']]
        for tk in TK:
            if tk in ORDER or tk in ('XLU',): continue
            if tk == 'BOXX': continue
        # primaries not substitutable: XLU, BOXX pass through (own)
        for tk in ('XLU',):
            tg[(tk, None)] = T0[TI[tk]]
        for X_ in ORDER:
            d = T0[TI[X_]]
            tagged = {Y: bk.val(Y, t, X_) / nav for Y in TK if any(l[5] == X_ for l in bk.lots[Y])}
            if X_ not in cands:
                tg[(X_, None)] = tg.get((X_, None), 0.0) + d
                for Y, wY in tagged.items(): pass
                continue
            blocked = bk.blocked(X_, t, thr)
            hown = bk.val(X_, t, None) / nav
            keepeq = {}
            if blocked:
                own = min(d, hown); rem = d - own
            else:
                own = d; rem = 0.0
                if tagged and d > EPS:
                    # switch-back decision per substitute holding
                    for Y, wY in tagged.items():
                        k = dict(cands[X_]).get(Y)
                        if k is None: continue
                        pa, pb = bk.unreal(t, X_, Y); pnl = pa + pb
                        st = state.setdefault((X_, Y), ORD[t])    # day the primary became unblocked while substitute held
                        wait = ORD[t] - st
                        if sb == 'guard' and pnl < -guard_frac * nav and wait <= maxwait:
                            keepeq[Y] = wY / k
                    if keepeq:
                        keep_tot = min(sum(keepeq.values()), d); own = d - keep_tot; rem = keep_tot
                else:
                    for kk in [kk for kk in state if kk[0] == X_]: state.pop(kk, None)
            if blocked or keepeq:
                for kk in [kk for kk in state if kk[0] == X_ and blocked]: state.pop(kk, None)
                # allocate rem through candidate list
                allocated = False
                prim_fallback = False
                rr = rem
                for Y, k in cands[X_]:
                    if rr <= EPS: break
                    wY = tagged.get(Y, 0.0)
                    if not blocked:                                 # guarded keep: only hold the existing substitute
                        use = min(rr * k, wY); 
                        if use > EPS: tg[(Y, X_)] = tg.get((Y, X_), 0.0) + use; rr -= use / k; avail -= use - use / k
                        continue
                    ysec_blocked = bk.blocked(Y, t, thr)
                    cap = wY if ysec_blocked else 1e9
                    want = rr * k
                    use = min(want, cap)
                    budget = rr + max(avail, 0.0)             # X's own dollars plus the cash leg
                    if use > budget + 1e-12:
                        use = budget; rr = 0.0; avail = 0.0    # dollar-limited: all dollars deployed, exposure shortfall
                        if use > EPS: tg[(Y, X_)] = tg.get((Y, X_), 0.0) + use
                    elif use > EPS:
                        tg[(Y, X_)] = tg.get((Y, X_), 0.0) + use; rr -= use / k; avail -= use - use / k
                if blocked and rr > EPS and not cands[X_]: pass
                # leftover: for rules with no unblocked fallback, buy the primary anyway (accept the wash) unless cands cover it
                if blocked and rr > EPS and rule_fallback_primary(rule, X_):
                    own += rr; rr = 0.0
            tg[(X_, None)] = tg.get((X_, None), 0.0) + own
        return tg, avail
    def rule_fallback_primary(rule, X_):
        # S1-type rules (no QQQ fallback for the leveraged pair): accept the wash when every candidate is blocked.
        # S2/S3 (QQQ fallback) and the guarded keep leave any shortfall in cash.
        return not (rule in ('S2', 'S3', 'S3L') and X_ in ('TQQQ', 'QLD'))
    PAIDY = {}
    acct = []; pre = 1.0; pre_series = []; paid = 0.0; cf = [0.0, 0.0]; paid_years = set(); state = {}
    nreb = 0; norders = 0; nsubdays = 0; short_sum = 0.0; short_n = 0; sub_days_any = 0; nswitch = 0
    prev_assign = set()
    cost_next = 0.0
    shortfalls = []
    trade_log = []
    nav = nav0
    exp_gap = []
    for t in range(i0, i1):
        navt = sum(bk.val(tk, t) for tk in TK) if t > i0 else nav0
        T0 = W7[t]
        if t == i0:
            tg, _ = targets(t, T0, nav0, state) if False else ({}, 0)
            T0i = T0 if init_w is None else init_w
            T1 = {(tk, None): T0i[TI[tk]] for tk in TK if T0i[TI[tk]] > 0}
            tg = T1
            cur = {}
            reb = True
        else:
            tg, avail = targets(t, T0, navt, state)
            cur = {}
            for tk in TK:
                for tag in set(l[5] for l in bk.lots[tk]) | {None}:
                    v = bk.val(tk, t, tag)
                    if v > 0: cur[(tk, tag)] = v / navt
            keys = set(tg) | set(cur)
            drift = sum(abs(tg.get(k, 0.0) - cur.get(k, 0.0)) for k in keys)
            # engine drift is per ticker; tags of one ticker net out
            tt_t = {}; tt_c = {}
            for (tk, tag), w in tg.items(): tt_t[tk] = tt_t.get(tk, 0.0) + w
            for (tk, tag), w in cur.items(): tt_c[tk] = tt_c.get(tk, 0.0) + w
            tt_t['BOXX'] = max(0.0, 1.0 - sum(v for k, v in tt_t.items() if k != 'BOXX'))
            drift_tk = sum(abs(tt_t.get(k, 0.0) - tt_c.get(k, 0.0)) for k in set(tt_t) | set(tt_c))
            stub = any(tt_t.get(k, 0.0) <= 1e-12 and tt_c.get(k, 0.0) > ZE for k in tt_c)
            reb = (key[t] != key[t - 1]) or (drift_tk > BAND) or stub
            # tag-level mismatch only matters when it comes with a real rebalance; handled at execution
        # exposure gap diagnostics
        if t > i0:
            g0 = sum(LEV.get(tk, 0) * T0[TI[tk]] for tk in TK)
            ttk = {}
            for (tk, tag), w in tg.items(): ttk[tk] = ttk.get(tk, 0.0) + w
            g1 = sum(LEV.get(tk, 0) * w for tk, w in ttk.items())
            exp_gap.append((g0, g1, any(tag is not None for (_, tag) in tg)))
        REBLOG.append(bool(reb))
        cost = 0.0
        if reb:
            nreb += 1
            if t > i0:
                tg = dict(tg); 
                # BOXX takes the remainder
                tot_nb = sum(w for (tk, tag), w in tg.items() if tk != 'BOXX')
                tg[('BOXX', None)] = max(0.0, 1.0 - tot_nb)
                tot = sum(tg.values())
                if tot > 1 + 1e-9:   # budget overflow: scale substitutes proportionally (should not happen)
                    f = 1 / tot; tg = {k: v * f for k, v in tg.items()}
                keys = set(tg) | set(cur)
                sells = []; buys = []
                for k in keys:
                    dlt = (tg.get(k, 0.0) - cur.get(k, 0.0)) * navt
                    if dlt < -EPS * navt: sells.append((k, -dlt))
                    elif dlt > EPS * navt: buys.append((k, dlt))
                # tags of one ticker: a (tk,tag) buy and another (tk,tag') sell are real tax-lot transactions
                for (tk, tag), usd in sells: bk.sell(tk, usd, t, tag if tag is not None else None) if True else None
                for (tk, tag), usd in buys: bk.buy(tk, usd, t, tag)
                tv = sum(u for _, u in sells) + sum(u for _, u in buys)
                cost = COST * tv / navt
                norders += len(sells) + len(buys)
                assign = set((k[0], k[1]) for k in tg if k[1] is not None and tg[k] > 1e-9)
                nswitch += len(assign ^ prev_assign); prev_assign = assign
            else:
                for (tk, tag), w in tg.items():
                    if w > 0: bk.buy(tk, w * nav0, t, tag)
                cost = COST * sum(tg.values()); norders += len(tg)
        # tax payment: first session on/after 15 Apr
        y = YR[t]
        if taxed and (y - 1) not in paid_years and DATES[t] >= dt.date(y, 4, 15) and (y - 1) >= YR[i0]:
            st, lt = bk.yr(y - 1)
            tx, cf[0], cf[1] = tax_year(st, lt, cf[0], cf[1]); paid_years.add(y - 1)
            navp = sum(bk.val(tk, t) for tk in TK)
            if tx > 0:
                need = tx; vb = bk.val('BOXX', t)
                sb_ = min(need, vb)
                if sb_ > 0: bk.sell('BOXX', sb_, t, 'ALL'); need -= sb_
                if need > 1e-9:
                    navq = sum(bk.val(tk, t) for tk in TK); f = need / navq
                    for tk in TK:
                        v = bk.val(tk, t)
                        if v > 0 and tk != 'BOXX': bk.sell(tk, v * f, t, 'ALL')
                PAIDY[y - 1] = tx; paid += tx; cost = 1 - (1 - cost) * (1 - COST * tx / navp)
            elif tx < 0:
                bk.buy('BOXX', -tx, t, None); paid += tx
        # earn next day
        g = 0.0
        navv = {tk: bk.val(tk, t) for tk in TK}; navs = sum(navv.values())
        for tk in TK: g += navv[tk] * R[t + 1, TI[tk]]
        g /= navs
        pre *= (1 + g) * (1 - cost)
        pre_series.append((1 + g) * (1 - cost) - 1)
        if cost > 0:
            for tk in TK:
                for l in bk.lots[tk]: l[0] *= (1 - cost); l[4] *= (1 - cost)
        acct.append(sum(bk.val(tk, t + 1) for tk in TK))
    # end liquidation
    ye = YR[i1]; st, lt = bk.yr(ye)
    ua, ub = bk.unreal(i1)
    tx_liq = tax_year(st + ua, lt + ub, cf[0], cf[1])[0] if taxed else 0.0
    tx_ytd = tax_year(st, lt, cf[0], cf[1])[0] if taxed else 0.0
    liq = acct[-1] - max(tx_liq, 0.0)
    n = len(acct)
    eg = np.array(exp_gap) if exp_gap else np.zeros((1, 3))
    res = dict(acct=np.array(acct), pre=np.array(pre_series), n=n, paid=paid, tx_liq=tx_liq, liq=liq, real=bk.real, wash_by_year=bk.wash_by_year,
               wash_usd=bk.wash_usd, wash_n=bk.wash_n, nreb=nreb, norders=norders, nswitch=nswitch, cf=cf, events=bk.events,
               gap_all=(eg[:, 0] - eg[:, 1]).mean(), gap_sub=((eg[:, 0] - eg[:, 1])[eg[:, 2] > 0].mean() if (eg[:, 2] > 0).any() else 0.0),
               paid_y=PAIDY, ua=ua, ub=ub, pend_open=sum(p[0]*p[1] for v in bk.pend.values() for p in v if p[3]>=ORD[i1] and p[0]>EPS), subdays=int((eg[:, 2] > 0).sum()), bk=bk)
    return res

def stats(r):
    nav = np.cumprod(1 + r); pk = np.maximum.accumulate(np.concatenate([[1.0], nav]))[1:]
    yrs = len(r) / 252
    return dict(c=nav[-1] ** (1 / yrs) - 1, sh=r.mean() / r.std(ddof=1) * 252 ** .5, dd=(nav / pk - 1).min())

if __name__ == '__main__':
    r = simulate('BASE', 'FIFO', taxed=False)
    eg = eng.stats(eng.rets(base))
    s = stats(r['pre'])
    print('engine', eg, 'sim', s, 'nreb', r['nreb'], base['reb'].sum())
    print('max daily diff', np.abs(r['pre'] - eng.rets(base)).max())
