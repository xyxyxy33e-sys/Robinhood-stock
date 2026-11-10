"""Deep-E (hold QQQ with part of the cash leg when effective state is E and QQQ is >= X% under its 200d). Research only."""
exec(open('/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad/hv/hv_test.py').read().split("log('='*130)")[0].replace("hv_test.log", "de_test.log"))
import time
rng = np.random.default_rng(11)
inf = float('inf'); LETTERS = MC.LETTERS

# ---------------------------------------------------------------- masks
eR = MC._eff(sr, LIVE)[0]; eP = MC._eff(sig, LIVE)[0]
gR = np.nan_to_num(sr['gaps'][200][0]); gP = np.nan_to_num(sig['gaps'][200][0])
ER, EP = eR == 4, eP == 4
def mask(E, g, th=0.05, x=None):
    """on at close t: E and gap<=-th to enter; stays on while E and gap<=x (x default -th; inf = until E ends)."""
    x = -th if x is None else x
    if x == -th: return E & (g <= -th)
    m = np.zeros(len(E), bool); on = False
    for t in range(len(E)):
        on = bool(E[t] and (g[t] <= x)) if on else bool(E[t] and g[t] <= -th)
        m[t] = on
    return m
def lag(m): return np.r_[False, m[:-1]]
PAN = {'real': (sr, pr, '2015-11-02', ER, gR), 'proxy': (sig, p, '2001-01-02', EP, gP)}
CACHE = {}
def run(pk, ex, d0=None, key=None):
    sg, pn, dd, E, g = PAN[pk]; d0 = d0 or dd
    ck = (pk, d0, key, MC.COST)
    if key is not None and ck in CACHE: return CACHE[ck]
    out = runner(sg, pn, d0, ex)
    if key is not None: CACHE[ck] = out
    return out
def met(r):
    c, s, m = prof(r); return c, s, m
def sel(r, ds, drop=None, only=None):
    y = np.array([d[:4] for d in ds])
    k = np.ones(len(r), bool)
    if drop: k &= y != drop
    if only: k &= y == only
    return r[k]
def yearly(r, ds):
    y = {}
    for d, x in zip(ds, r): y.setdefault(d[:4], []).append(x)
    return {k: np.prod(1+np.array(v))-1 for k, v in y.items()}
def dd_(r): return prof(r)[2]

H = f"  {'variant':<56}{'CAGR':>7}{'vs base':>8}{'Sharpe':>7}{'maxDD':>8}{'dCAGR x20':>10}{'Sh x20':>7}{'tr/yr':>6}{'+tr/yr':>7}{'days on':>8}"
def table(title, pk, variants, d0=None):
    sg, pn, dd, E, g = PAN[pk]; d0 = d0 or dd
    log(f"\n{title}"); log(H)
    rb, tb, ds = run(pk, [], d0, 'base'); cb = prof(rb)[0]
    rbx = sel(rb, ds, drop='2020'); cbx, sbx, _ = met(rbx)
    log(f"  {'base':<56}{cb*100:6.1f}%{0:+8.2f}{prof(rb)[1]:7.3f}{prof(rb)[2]*100:7.1f}%{0:+10.2f}{sbx:7.3f}{tb:6.0f}{0:+7.1f}{'':>8}")
    for lab, inst, sh, m in variants:
        ex = [(inst, m*sh)] if np.isscalar(sh) else [(i, mm*s) for (i, s), mm in zip(zip(inst, sh), m)]
        r, t, _ = run(pk, ex)
        c, s, mdd = met(r); rx = sel(r, ds, drop='2020'); cx, sx, _ = met(rx)
        log(f"  {lab:<56}{c*100:6.1f}%{(c-cb)*100:+8.2f}{s:7.3f}{mdd*100:7.1f}%{(cx-cbx)*100:+10.2f}{sx:7.3f}{t:6.0f}{t-tb:+7.1f}{int(m[1:].sum()):8d}")

log('='*140); log("DEEP-E (QQQ with part of the cash leg when effective state E and QQQ >= X% under its 200d) -- live design, 2bp, research only"); log('='*140)
log(f"real panel {rd[0]}..{rd[-1]} ({len(rd)} sessions); proxy panel {p['dates'][0]}..{p['dates'][-1]}, scored from 2001-01-02; classifier valid from session 200 = {p['dates'][199]}")
log(f"E sessions: real {ER[1:].mean()*100:.1f}%, proxy {EP[1:].mean()*100:.1f}%; deep-E (gap<=-5%) real {mask(ER,gR)[1:].sum()} sessions ({mask(ER,gR)[1:].mean()*100:.1f}%), proxy {mask(EP,gP)[1:].sum()} ({mask(EP,gP)[1:].mean()*100:.1f}%)")
QR, QP = pr['qqq'], p['qqq']

# =============================================================== 1. EPISODES
def spells(m, s0):
    out = []; t = s0
    n = len(m)
    while t < n - 1:
        if m[t]:
            u = t
            while u + 1 < n - 1 and m[u + 1]: u += 1
            out.append((t, u)); t = u + 1
        else: t += 1
    return out
def episodes(pk, d0=None, label=''):
    sg, pn, dd, E, g = PAN[pk]; d0 = d0 or dd; ds_all = pn['dates']; s0 = next(i for i, d in enumerate(ds_all) if d >= d0)
    eff = MC._eff(sg, LIVE)[0]; m = mask(E, g)
    rb, _, ds = run(pk, [], d0, 'base'); rv, _, _ = run(pk, [(pn['qqq'], m*0.5)], d0, 'cand')
    sp = spells(m, s0); rows = []
    for a, b in sp:
        i0, i1 = a - s0, b - s0
        qret = np.prod(1 + pn['qqq'][a+1:b+2]) - 1
        gain = (rv[i0:i1+1] - rb[i0:i1+1]).sum() * 100
        # next non-E state after the spell
        k = b + 1
        while k < len(eff) and eff[k] == 4: k += 1
        nxt = LETTERS[eff[k]] if k < len(eff) else '-'
        # first state of the spell exit day
        ex_state = LETTERS[eff[b+1]] if b + 1 < len(eff) else '-'
        rows.append(dict(a=ds_all[a], b=ds_all[b], n=b-a+1, g=g[a]*100, q=qret*100, gain=gain, nxt=nxt, ex=ex_state))
    log(f"\nEPISODES {label}: {pk} panel, deep-E (E & gap200<=-5%), QQQ 50% of cash, scored from {d0}. Gain = sum of daily (variant - base) return, points of book.")
    log(f"  {'start':<12}{'end':<12}{'sess':>5}{'gap@entry':>10}{'QQQ ret':>9}{'gain pts':>9}   state on exit day / next non-E state")
    for r in rows:
        log(f"  {r['a']:<12}{r['b']:<12}{r['n']:>5}{r['g']:>9.1f}%{r['q']:>8.1f}%{r['gain']:>+9.2f}   {r['ex']} / {r['nxt']}")
    tot = sum(r['gain'] for r in rows); w = [r for r in rows if r['gain'] > 0]; l = [r for r in rows if r['gain'] <= 0]
    top = sorted(rows, key=lambda r: -r['gain'])[:3]
    log(f"  spells {len(rows)}; wins {len(w)} losses {len(l)}; sum gain {tot:+.2f} pts; sum wins {sum(r['gain'] for r in w):+.2f}, sum losses {sum(r['gain'] for r in l):+.2f}")
    log(f"  top 3 spells ({', '.join(r['a'] for r in top)}) = {sum(r['gain'] for r in top):+.2f} pts = {sum(r['gain'] for r in top)/tot*100:.0f}% of total")
    nx = {}
    for r in rows: nx[r['nxt']] = nx.get(r['nxt'], 0) + 1
    log(f"  next non-E state after spell: {nx}")
    y20 = sum(r['gain'] for r in rows if r['a'].startswith('2020')); log(f"  spells starting in 2020: {sum(1 for r in rows if r['a'].startswith('2020'))}, gain {y20:+.2f} pts; ex-2020 spells {tot-y20:+.2f} pts")
    return rows
epR = episodes('real'); epP = episodes('proxy')

def yeartab(pk):
    sg, pn, dd, E, g = PAN[pk]; m = mask(E, g)
    rb, _, ds = run(pk, [], None, 'base'); rv, _, _ = run(pk, [(pn['qqq'], m*0.5)], None, 'cand')
    yb, yv = yearly(rb, ds), yearly(rv, ds)
    log(f"\nPER-YEAR {pk}: base / deep-E 50% / diff (pts) / deep-E sessions"); log(f"  {'year':<6}{'base':>8}{'deepE':>8}{'diff':>8}{'sess':>6}")
    yrs = np.array([d[:4] for d in pn['dates']])
    for k in sorted(yb):
        log(f"  {k:<6}{yb[k]*100:7.1f}%{yv[k]*100:7.1f}%{(yv[k]-yb[k])*100:+8.2f}{int(m[yrs == k].sum()):6d}")
    for lab, dr in (('all days', None), ('2020 removed (other days only)', '2020')):
        a, b = sel(rb, ds, drop=dr), sel(rv, ds, drop=dr); ca, sa, ma = met(a); cb_, sb, mb = met(b)
        log(f"  {lab:<32} base CAGR {ca*100:5.1f}% Sharpe {sa:.3f} maxDD {ma*100:.1f}%  |  deepE CAGR {cb_*100:5.1f}% ({(cb_-ca)*100:+.2f}) Sharpe {sb:.3f} maxDD {mb*100:.1f}%")
yeartab('real'); yeartab('proxy')

# =============================================================== 2. BEAR MARKETS
log('\n' + '='*140); log("2. BEAR-MARKET CHECK"); log('='*140)
dq = p['dates']; log(f"proxy panel starts {dq[0]}; the 200d SMA (and the classifier) first exists on {dq[199]}; the 2000 top (Mar-2000) and the Apr-Jun 2000 crash are NOT classified. Headline proxy scoring starts 2001-01-02.")
sgP = PAN['proxy'];
d0x = '2000-07-03'
rbx, _, dsx = run('proxy', [], d0x, 'base_x'); mP = mask(EP, gP); rvx, _, _ = run('proxy', [(QP, mP*0.5)], d0x, 'cand_x')
yb, yv = yearly(rbx, dsx), yearly(rvx, dsx)
log(f"\nProxy full strategy scored from {d0x} (state noise from classifier warm-up possible in the first months): base CAGR {prof(rbx)[0]*100:.1f}% Sharpe {prof(rbx)[1]:.3f} maxDD {prof(rbx)[2]*100:.1f}%; deep-E 50% CAGR {prof(rvx)[0]*100:.1f}% Sharpe {prof(rvx)[1]:.3f} maxDD {prof(rvx)[2]*100:.1f}%")
for lab, y0, y1 in (('2000-07..2002', 2000, 2002), ('2007..2009', 2007, 2009), ('2022', 2022, 2022)):
    sel_ = [i for i, d in enumerate(dsx) if y0 <= int(d[:4]) <= y1]
    a, b = rbx[sel_], rvx[sel_]
    log(f"  {lab:<14} base cum {(np.prod(1+a)-1)*100:+7.1f}% maxDD {dd_(a)*100:6.1f}% | deep-E cum {(np.prod(1+b)-1)*100:+7.1f}% maxDD {dd_(b)*100:6.1f}% | diff {(np.prod(1+b)-np.prod(1+a))*100:+.2f} pts")
log("  per-year (base / deep-E / diff pts / deep-E sessions): " + '; '.join(f"{y} {yb[y]*100:+.1f}/{yv[y]*100:+.1f}/{(yv[y]-yb[y])*100:+.2f}/{int(sum(1 for t,d in enumerate(dq) if d[:4]==y and mP[t]))}" for y in ('2000','2001','2002','2003','2007','2008','2009')))
s0x = next(i for i, d in enumerate(dq) if d >= d0x)
log(f"\n  deep-E spells on the proxy 2000-07..2003 and 2007..2010 (gain = sum of daily diff vs base, pts; QQQ price return over spell; QQQ min vs spell-entry close):")
log(f"  {'start':<12}{'end':<12}{'sess':>5}{'gap@entry':>10}{'QQQ ret':>9}{'QQQ worst':>10}{'gain pts':>9}   next non-E")
effP = eP
for a, b in spells(mP, s0x):
    if not (dq[a][:4] in ('2000','2001','2002','2003','2007','2008','2009','2010')): continue
    path = np.cumprod(1 + QP[a+1:b+2]); k = b + 1
    while k < len(effP) and effP[k] == 4: k += 1
    log(f"  {dq[a]:<12}{dq[b]:<12}{b-a+1:>5}{gP[a]*100:>9.1f}%{(path[-1]-1)*100:>8.1f}%{(path.min()-1)*100:>9.1f}%{(rvx[a-s0x:b-s0x+1]-rbx[a-s0x:b-s0x+1]).sum()*100:>+9.2f}   {LETTERS[effP[k]] if k < len(effP) else '-'}")
# E-state days in the bears: how deep was QQQ when E started
log("\n  E-state spells (all, not only deep) in the bears: start, end, sessions, QQQ gap at start, QQQ return over spell")
a = None
for t in range(s0x, len(dq)):
    if EP[t] and (a is None): a = t
    if a is not None and (not EP[t] or t == len(dq)-1):
        b = t - 1
        if dq[a][:4] in ('2000','2001','2002','2003','2007','2008','2009'):
            log(f"  {dq[a]:<12}{dq[b]:<12}{b-a+1:>5} sess  gap@start {gP[a]*100:+6.1f}%  QQQ ret {(np.prod(1+QP[a+1:b+2])-1)*100:+7.1f}%  min gap in spell {gP[a:b+1].min()*100:.1f}%  deep sessions {int(mP[a:b+1].sum())}")
        a = None

# QQQ-only on NDX price index from 1985 (classifier warm from session 200)
log("\nQQQ-ONLY version on the NDX price index (data/NDX_index_daily.csv from 1985-10-01; same classifier + fast overlay; the deep-E leg = 50% in NDX (price only, no dividends) and 50% T-bill vs 100% T-bill; 2bp each way on the NDX share). Scored from 1987-02-02.")
ndx = {}
for rr in csv.DictReader(open('/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad/data_ext/NDX_index_daily.csv')): ndx[rr['d']] = float(rr['c'])
nd = sorted(ndx); npx = np.array([ndx[d] for d in nd]); nr = np.r_[0, npx[1:]/npx[:-1]-1]
tb_ = MC._load('dgs3mo_full.csv', 'observation_date', 'DGS3MO'); tbd = sorted(tb_); j = 0; last = 0.0; rate = []
for d in nd:
    while j < len(tbd) and tbd[j] <= d: last = tb_[tbd[j]]; j += 1
    rate.append(last/100)
rate = np.array(rate); yf = np.r_[0, [MC._yf(nd[i-1], nd[i]) for i in range(1, len(nd))]]; cashN = np.r_[rate[0], rate[:-1]] * yf
sgN = MC.signals(npx[None], npx[None]); effN = MC._eff(sgN, LIVE)[0]; EN = effN == 4; gN = np.nan_to_num(sgN['gaps'][200][0]); mN = mask(EN, gN)
n0 = next(i for i, d in enumerate(nd) if d >= '1987-02-02')
def qonly(m, share=0.5, start=n0, lagged=False, cost=0.0002):
    mm = lag(m) if lagged else m
    rows = []; t = start
    while t < len(nd) - 1:
        if mm[t]:
            u = t
            while u + 1 < len(nd) - 1 and mm[u + 1]: u += 1
            q = np.prod(1 + nr[t+1:u+2]) - 1; c = np.prod(1 + cashN[t+1:u+2]) - 1
            gain = share * (q - c) - 2 * cost * share
            k = u + 1
            while k < len(nd) and effN[k] == 4: k += 1
            rows.append((nd[t], nd[u], u - t + 1, gN[t]*100, q*100, c*100, gain*100, LETTERS[effN[k]] if k < len(nd) else '-', t, u)); t = u + 1
        else: t += 1
    return rows
rowsN = qonly(mN)
log(f"  state E sessions {EN[n0:].mean()*100:.1f}% of sessions, deep-E {mN[n0:].sum()} sessions in {len(rowsN)} spells")
log(f"  {'start':<12}{'end':<12}{'sess':>5}{'gap@entry':>10}{'NDX ret':>9}{'tbill':>7}{'gain pts':>9}   next non-E")
for r in rowsN: log(f"  {r[0]:<12}{r[1]:<12}{r[2]:>5}{r[3]:>9.1f}%{r[4]:>8.1f}%{r[5]:>6.1f}%{r[6]:>+9.2f}   {r[7]}")
tot = sum(r[6] for r in rowsN); log(f"  total {tot:+.2f} pts (sum of spell gains, simple); wins {sum(r[6]>0 for r in rowsN)} losses {sum(r[6]<=0 for r in rowsN)}")
eras = (('1987-1999', '1987', '1999'), ('2000-2002', '2000', '2002'), ('2003-2006', '2003', '2006'), ('2007-2009', '2007', '2009'), ('2010-2019', '2010', '2019'), ('2020', '2020', '2020'), ('2021-2026', '2021', '2026'))
for lab, a, b in eras:
    rr = [r for r in rowsN if a <= r[0][:4] <= b]
    log(f"  era {lab:<10} spells {len(rr):>2}  sessions {sum(r[2] for r in rr):>4}  gain {sum(r[6] for r in rr):+7.2f} pts  wins {sum(r[6]>0 for r in rr)}/{len(rr)}")
# whole-book approximation: NAV of 'E-state book' is unknown; give the per-year increment of the overlay alone
ovl = np.zeros(len(nd))
for r in rowsN: pass
mm = mN.copy(); inc = np.zeros(len(nd))
for t in range(n0, len(nd) - 1):
    if mm[t]: inc[t+1] = 0.5 * (nr[t+1] - cashN[t+1])
cost_inc = np.zeros(len(nd)); ch = np.abs(np.diff(np.r_[False, mm[:-1]].astype(float), prepend=0.0))
for t in range(n0, len(nd) - 1): cost_inc[t+1] = 0.0002 * 0.5 * abs(float(mm[t]) - float(mm[t-1]))
net = inc - cost_inc
yy = {}
for t in range(n0, len(nd)): yy[nd[t][:4]] = yy.get(nd[t][:4], 0) + net[t]
log("  overlay-only increment per year (pts of book, additive, net of 2bp): " + '  '.join(f"{y} {v*100:+.2f}" for y, v in sorted(yy.items()) if abs(v) > 1e-6))
log(f"  cumulative additive: {sum(yy.values())*100:+.2f} pts over {(len(nd)-n0)/252:.1f} years; worst single-spell {min(r[6] for r in rowsN):+.2f} pts")
# the same without the first-3-spell or with -3% / -7% thresholds
for th in (0.03, 0.07, 0.10):
    rr = qonly(mask(EN, gN, th)); log(f"  NDX-only entry gap<=-{th*100:.0f}%: {len(rr)} spells, {sum(r[2] for r in rr)} sessions, total {sum(r[6] for r in rr):+.2f} pts, wins {sum(r[6]>0 for r in rr)}/{len(rr)}; 2000-2002 {sum(r[6] for r in rr if '2000'<=r[0][:4]<='2002'):+.2f}, 2007-2009 {sum(r[6] for r in rr if '2007'<=r[0][:4]<='2009'):+.2f}")

# =============================================================== 3. VARIANTS
log('\n' + '='*140); log("3. RULE VARIANTS (all keep E required; share = fraction of the cash leg; instrument QQQ unless stated)"); log('='*140)
for pk, E, g, QQ, spm in (('real', ER, gR, QR, pr['spmo']), ('proxy', EP, gP, QP, None)):
    V = []
    for th in (0.04, 0.05, 0.06, 0.07): V.append((f"entry gap<=-{th*100:.0f}%, exit when gap>-{th*100:.0f}% or E ends (orig)", QQ, 0.5, mask(E, g, th)))
    for x, lab in ((-0.03, 'gap>-3%'), (-0.02, 'gap>-2%'), (-0.01, 'gap>-1%'), (inf, 'E ends only')):
        V.append((f"entry -5%, exit {lab}", QQ, 0.5, mask(E, g, 0.05, x)))
    m5 = mask(E, g, 0.05)
    for sh in (0.25, 0.5, 0.75, 1.0): V.append((f"share {sh*100:.0f}% QQQ, entry -5% (orig exit)", QQ, sh, m5))
    if spm is not None: V.append(("SPMO 50%, entry -5%", spm, 0.5, m5))
    V.append(("TQQQ 15%, entry -5%", pr['tqqq'] if pk == 'real' else p['tqqq'], 0.15, m5)); V.append(("TQQQ 25%, entry -5%", pr['tqqq'] if pk == 'real' else p['tqqq'], 0.25, m5))
    V.append(("QLD 25%, entry -5%", pr['qld'] if pk == 'real' else p['qld'], 0.25, m5)); V.append(("QLD 50%, entry -5%", pr['qld'] if pk == 'real' else p['qld'], 0.5, m5))
    table(f"VARIANTS -- {pk.upper()} panel", pk, V)

# =============================================================== 4. TIMING AND COST
log('\n' + '='*140); log("4. TIMING AND COST (candidate = QQQ 50%, entry -5%, orig exit)"); log('='*140)
for pk, E, g, QQ in (('real', ER, gR, QR), ('proxy', EP, gP, QP)):
    m5 = mask(E, g, 0.05); sg, pn, dd, _, _ = PAN[pk]
    for cost, lab in ((0.0002, '2bp'), (0.001, '10bp')):
        MC.COST = cost
        table(f"TIMING/COST {pk.upper()} cost {lab}", pk, [("candidate, signal at close t, trade close t (as modelled)", QQ, 0.5, m5), ("candidate, one session LATE (act at close t+1)", QQ, 0.5, lag(m5)), ("candidate 25% share", QQ, 0.25, m5)])
    MC.COST = 0.0002
    log(f"  episodes per year: {len(spells(m5, 1))/((len(pn['dates'])-1)/252):.2f} spells over the whole panel; each = 1 buy + 1 sell of the QQQ share")
    # NB the base is re-run at the same cost inside table (cache key includes MC.COST)

# =============================================================== 5. ROBUSTNESS
log('\n' + '='*140); log("5. ROBUSTNESS"); log('='*140)
def boot(a, b, n=3000, B=20):
    N = len(a); K = N // B + 1
    st = rng.integers(0, N - B, (n, K)); idx = (st[:, :, None] + np.arange(B)).reshape(n, -1)[:, :N]
    A, Bb = a[idx], b[idx]
    sa = A.mean(1) / A.std(1); sb = Bb.mean(1) / Bb.std(1)
    return float(((sa - sb) <= 0).mean()), float(np.percentile(sa - sb, 5)), float(np.median(sa - sb))
CAND = lambda E, g, QQ: [("C1 QQQ 50%, entry -5%, orig exit", QQ, 0.5, mask(E, g, 0.05)), ("C2 QQQ 25%, entry -5%, orig exit", QQ, 0.25, mask(E, g, 0.05)), ("C3 QQQ 50%, entry -5%, exit gap>-2% (hyst)", QQ, 0.5, mask(E, g, 0.05, -0.02))]
log(f"  {'candidate':<46}{'panel':<7}{'CAGR vs base':>13}{'Sharpe':>8}{'base':>7}{'P(not better)':>14}{'5th pct dSh':>12}{'median dSh':>11}  | ex-2020: {'dCAGR':>6}{'Sharpe':>8}{'base':>7}{'P(not better)':>14}")
for pk, E, g, QQ in (('real', ER, gR, QR), ('proxy', EP, gP, QP)):
    rb, _, ds = run(pk, [], None, 'base'); cb, sbase, _ = met(rb)
    for lab, inst, sh, m in CAND(E, g, QQ):
        r, _, _ = run(pk, [(inst, m*sh)]); c, s, _ = met(r); pn_, q5, med = boot(r, rb)
        rx, rbx_ = sel(r, ds, drop='2020'), sel(rb, ds, drop='2020'); cx, sx, _ = met(rx); cbx, sbx, _ = met(rbx_); pnx, _, _ = boot(rx, rbx_)
        log(f"  {lab:<46}{pk:<7}{(c-cb)*100:+12.2f} {s:8.3f}{sbase:7.3f}{pn_:14.3f}{q5:+12.3f}{med:+11.3f}  |           {(cx-cbx)*100:+6.2f}{sx:8.3f}{sbx:7.3f}{pnx:14.3f}")

log("\nPLACEBOS (candidate C1: QQQ 50% of cash; real panel and proxy panel)")
NPL = 300
for pk, E, g, QQ in (('real', ER, gR, QR), ('proxy', EP, gP, QP)):
    sg, pn, dd, _, _ = PAN[pk]; s0 = next(i for i, d in enumerate(pn['dates']) if d >= dd)
    m5 = mask(E, g, 0.05); rb, tb, ds = run(pk, [], None, 'base'); rv, tv, _ = run(pk, [(QQ, m5*0.5)], None, 'cand'); cb, sb, _ = met(rb); cv, sv, _ = met(rv)
    nd_ = int(m5[s0:-1].sum()); Eidx = np.where(E[s0:-1])[0] + s0; deep_set = set(np.where(m5)[0])
    log(f"\n  {pk}: actual deep-E {nd_} sessions of {len(Eidx)} E sessions: dCAGR {(cv-cb)*100:+.2f} dSharpe {sv-sb:+.3f} dMaxDD {(prof(rv)[2]-prof(rb)[2])*100:+.1f}")
    # (a) iid random E days
    A = []; Bk = []
    sp = spells(m5, s0); lens = [b - a + 1 for a, b in sp]
    # E runs
    runs_ = []; t = s0
    while t < len(E) - 1:
        if E[t]:
            u = t
            while u + 1 < len(E) - 1 and E[u + 1]: u += 1
            runs_.append((t, u)); t = u + 1
        else: t += 1
    for it in range(NPL):
        m = np.zeros(len(E), bool); m[rng.choice(Eidx, nd_, replace=False)] = True
        r, _, _ = run(pk, [(QQ, m*0.5)]); c, s, _ = met(r); A.append(((c-cb)*100, s-sb))
        # (b) random spells of the same lengths inside E runs (non-deep-conditional)
        m = np.zeros(len(E), bool)
        for L in lens:
            cand = [(a, b) for a, b in runs_ if b - a + 1 >= L]
            if not cand: continue
            a, b = cand[rng.integers(len(cand))]; st = rng.integers(a, b - L + 2); m[st:st+L] = True
        r, _, _ = run(pk, [(QQ, m*0.5)]); c, s, _ = met(r); Bk.append(((c-cb)*100, s-sb))
    A = np.array(A); Bk = np.array(Bk)
    for lab, X in (('random E days (same count)', A), ('random E spells (same lengths, anywhere in E runs)', Bk)):
        log(f"   placebo {lab}: dCAGR mean {X[:,0].mean():+.2f} 5-95% [{np.percentile(X[:,0],5):+.2f},{np.percentile(X[:,0],95):+.2f}] max {X[:,0].max():+.2f}; dSharpe mean {X[:,1].mean():+.3f} 95th {np.percentile(X[:,1],95):+.3f}; P(placebo dCAGR >= actual) {(X[:,0] >= (cv-cb)*100).mean():.3f}, P(placebo dSharpe >= actual) {(X[:,1] >= sv-sb).mean():.3f}  ({NPL} draws)")
    # deterministic: shallow E (gap -2..0), mid (-5..-2), deep
    for lab, m in (('E & gap in (-2%,0]', E & (g > -0.02) & (g <= 0)), ('E & gap in (-5%,-2%]', E & (g > -0.05) & (g <= -0.02)), ('E & gap > 0 (E above the 200d)', E & (g > 0)), ('E & gap<=-5% (candidate)', m5)):
        r, t, _ = run(pk, [(QQ, m*0.5)]); c, s, mdd = met(r)
        log(f"   {lab:<34} sessions {int(m[s0:-1].sum()):5d}  dCAGR {(c-cb)*100:+6.2f}  Sharpe {s:.3f} (base {sb:.3f})  maxDD {mdd*100:.1f}%  tr/yr {t:.0f}")
OUT.close()
