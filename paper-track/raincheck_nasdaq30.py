"""raincheck_nasdaq30 -- standalone analysis of the Raincheck Capital "NASDAQ-30"
strategy the owner holds in a separate account (2026-09-14).

Run from the repo root:  python3 paper-track/raincheck_nasdaq30.py
Standard library only. Research only: nothing here is applied.

Sections
  1  proxy validation (QTOP/QNXT/QQLV/QQXL/TBIL vs long-history proxies)
  2  top-30 concentration premium (MGK, XLG vs QQQ/SPY; QTOP vs QNXT by month)
  3  static-mix backtest of the current 46/35/9/6/4 holdings, harness rows
  4  managed-leverage bounds (perfect foresight, mechanical proxies, exposure-matched)
  5  leveraged-ETF mechanics (daily reset vs monthly 2x; cost of the 35% sleeve)
  6  side by side with the LIVE design; combined book at $200k / $20k

Every portfolio figure goes through the project harness `run()` (4bp one-way,
state.REBALANCE_DRIFT_BAND drift band); the only hand-rolled loop is the
explicit monthly-rebalanced 2x in section 5, which exists to show what a
non-daily-reset 2x would have done and is labelled as such.
"""
import sys, math
sys.path.insert(0, 'paper-track')
exec(open('paper-track/leverage_under_trim.py').read().split('rr=RF.real_rows()')[0])   # stop before the real SPMO rows (external repo not present here); only the daily proxy rows are needed
from long_history_backtest import (load_px, synth_leveraged, total_return_index,
                                   make_rate_lookup, load_tbill_long)
from drift_band_test import annual_stats
from state import extension_scale
from block_bootstrap import boot
import state as S

# ----------------------------------------------------------------------------
# 0. data
# ----------------------------------------------------------------------------
def load_wide(path):
    hdr = None; out = {}
    for line in open(path):
        p = line.rstrip('\n').split(',')
        if hdr is None:
            hdr = p; out = {h: {} for h in hdr[1:]}; continue
        for h, v in zip(hdr[1:], p[1:]):
            if v: out[h][p[0]] = float(v)
    return out

RC = load_wide('data/raincheck_etfs_daily.csv')
MGK = load_px('data/mgk_daily.csv'); XLG = load_px('data/xlg_daily.csv')
SPY = load_px('data/spy_long_history.csv')
QQQL = load_px('data/qqq_long_history.csv')
D = data()                      # harness data dict: ds, qqq, rate_on, core, lev2, lev3, xl, cash
rate_on = D['rate_on']

ER = dict(QTOP=0.20, QNXT=0.20, QQLV=0.25, QQXL=0.95, TBIL=0.15, MGK=0.07, XLG=0.20, QQQ=0.20, QLD=0.95)
MIX = dict(QTOP=0.46, QQXL=0.35, QNXT=0.09, QQLV=0.06, TBIL=0.04)

def rets(px, dates):
    return [px[dates[i]] / px[dates[i - 1]] - 1 for i in range(1, len(dates))]

def common(*series):
    s = set(series[0])
    for x in series[1:]: s &= set(x)
    return sorted(s)

def mean(a): return sum(a) / len(a)
def sd(a):
    m = mean(a); return (sum((x - m) ** 2 for x in a) / (len(a) - 1)) ** 0.5
def beta_corr(y, x):
    mx, my = mean(x), mean(y)
    cxy = sum((a - mx) * (b - my) for a, b in zip(x, y)); vx = sum((a - mx) ** 2 for a in x); vy = sum((b - my) ** 2 for b in y)
    return cxy / vx, cxy / math.sqrt(vx * vy)
def ann(rs):
    nav = 1.0
    for r in rs: nav *= 1 + r
    return nav ** (252 / len(rs)) - 1
def mdd(rs):
    pk = cur = 1.0; m = 0.0
    for r in rs:
        cur *= 1 + r; pk = max(pk, cur); m = min(m, cur / pk - 1)
    return m
def stats(rs):
    c, s, m = annual_stats(rs); return dict(cagr=c, sharpe=s, mdd=m, vol=sd(rs) * math.sqrt(252))
def by_year(dates, rs):
    out = {}
    for d, x in zip(dates, rs): out[d[:4]] = out.get(d[:4], 0.0) + math.log1p(x)
    return {y: math.expm1(v) for y, v in out.items()}
def pct(x, n=1): return f"{x * 100:+.{n}f}%"

print("=" * 100)
print("RAINCHECK NASDAQ-30 -- standalone analysis, 2026-09-14")
print("=" * 100)

# ----------------------------------------------------------------------------
# 1. proxy validation
# ----------------------------------------------------------------------------
print("\n## 1. PROXY VALIDATION (daily returns on the overlap window)\n")
print("| pair | window | n | beta | corr | TE (ann) | ann ret A | ann ret B | A-B ann |")
print("|---|---|---|---|---|---|---|---|---|")
def pair(nameA, A, nameB, B, mult=1.0, start=None):
    ds = common(A, B)
    if start: ds = [d for d in ds if d >= start]
    ra = rets(A, ds); rb = [mult * x for x in rets(B, ds)]
    b, c = beta_corr(ra, rb); te = sd([a - x for a, x in zip(ra, rb)]) * math.sqrt(252)
    print(f"| {nameA} vs {nameB}{'' if mult == 1 else ' x%.2f' % mult} | {ds[0]}..{ds[-1]} | {len(ra)} | {b:.3f} | {c:.3f} | {te*100:.2f}% | {pct(ann(ra))} | {pct(ann(rb))} | {pct(ann(ra)-ann(rb))} |")
    return ds, ra, rb
pair('QTOP', RC['QTOP'], 'QQQ', RC['QQQ'])
pair('QTOP', RC['QTOP'], 'MGK', RC['MGK'])
pair('QTOP', RC['QTOP'], 'XLG', RC['XLG'])
pair('QNXT', RC['QNXT'], 'QQQ', RC['QQQ'])
pair('QQLV', RC['QQLV'], 'QQQ', RC['QQQ'])
pair('QQXL', RC['QQXL'], 'QTOP', RC['QTOP'], 2.0)
pair('QQXL', RC['QQXL'], 'QQQ', RC['QQQ'])
pair('QLD', RC['QLD'], 'QQQ', RC['QQQ'], 2.0)
pair('MGK', RC['MGK'], 'QQQ', RC['QQQ'])
pair('XLG', RC['XLG'], 'QQQ', RC['QQQ'])
pair('QTOP', RC['QTOP'], 'QNXT', RC['QNXT'])
# TBIL vs 3-month bill: the CSV is split-adjusted PRICE only (monthly distributions drop out)
ds = common(RC['TBIL'], RC['QQQ']); rt = rets(RC['TBIL'], ds)
bill = [((rate_on(ds[i - 1])) / 100.0) * ((__import__('datetime').date.fromisoformat(ds[i]) - __import__('datetime').date.fromisoformat(ds[i - 1])).days / 365.0) for i in range(1, len(ds))]
print(f"| TBIL price-only vs DGS3MO accrual | {ds[0]}..{ds[-1]} | {len(rt)} | - | - | {sd([a-b for a,b in zip(rt,bill)])*math.sqrt(252)*100:.2f}% | {pct(ann(rt),2)} | {pct(ann(bill),2)} | price series excludes ~monthly distributions; TBIL modelled as the bill |")
# concentration residual: cumulative QTOP-QQQ and QTOP-QNXT by month
ds = common(RC['QTOP'], RC['QQQ'], RC['QNXT'])
print("\nConcentration residual by month (QTOP - QQQ, QTOP - QNXT; monthly total returns):\n")
print("| month | QTOP | QQQ | QNXT | QTOP-QQQ | QTOP-QNXT |")
print("|---|---|---|---|---|---|")
months = sorted({d[:7] for d in ds})
mtab = []
for m in months:
    dm = [d for d in ds if d[:7] == m]
    prev = [d for d in ds if d < dm[0]]
    if not prev: continue
    p0 = prev[-1]; p1 = dm[-1]
    rq = RC['QTOP'][p1] / RC['QTOP'][p0] - 1; rQ = RC['QQQ'][p1] / RC['QQQ'][p0] - 1; rn = RC['QNXT'][p1] / RC['QNXT'][p0] - 1
    mtab.append((m, rq, rQ, rn))
    print(f"| {m} | {pct(rq)} | {pct(rQ)} | {pct(rn)} | {pct(rq-rQ)} | {pct(rq-rn)} |")
win_q = sum(1 for _, a, b, _ in mtab if a > b); win_n = sum(1 for _, a, _, c in mtab if a > c)
print(f"\nQTOP beat QQQ in {win_q}/{len(mtab)} months, beat QNXT in {win_n}/{len(mtab)} months; "
      f"cumulative QTOP {pct(RC['QTOP'][ds[-1]]/RC['QTOP'][ds[0]]-1)} vs QQQ {pct(RC['QQQ'][ds[-1]]/RC['QQQ'][ds[0]]-1)} vs QNXT {pct(RC['QNXT'][ds[-1]]/RC['QNXT'][ds[0]]-1)} ({ds[0]}..{ds[-1]}).")

# ----------------------------------------------------------------------------
# 2. concentration premium over the long window
# ----------------------------------------------------------------------------
print("\n## 2. TOP-30 CONCENTRATION PREMIUM (mega-cap proxies vs QQQ / SPY, price returns, calendar years)\n")
def yearly(px, ds):
    return by_year(ds[1:], rets(px, ds))
dsM = common(MGK, QQQL, SPY); dsX = common(XLG, QQQL, SPY)
yM, yQm, ySm = yearly(MGK, dsM), yearly(QQQL, dsM), yearly(SPY, dsM)
yX, yQx, ySx = yearly(XLG, dsX), yearly(QQQL, dsX), yearly(SPY, dsX)
print("| year | XLG | QQQ | SPY | XLG-QQQ | XLG-SPY | MGK | MGK-QQQ | MGK-SPY |")
print("|---|---|---|---|---|---|---|---|---|")
years = sorted(set(yX) | set(yM))
mgk_wins = qqq_wins = 0
for y in years:
    xs = f"{pct(yX[y])} | {pct(yQx[y])} | {pct(ySx[y])} | {pct(yX[y]-yQx[y])} | {pct(yX[y]-ySx[y])}" if y in yX else "- | - | - | - | -"
    ms = f"{pct(yM[y])} | {pct(yM[y]-yQm[y])} | {pct(yM[y]-ySm[y])}" if y in yM else "- | - | -"
    if y in yM and y > '2007':
        mgk_wins += yM[y] > yQm[y]; qqq_wins += yM[y] <= yQm[y]
    print(f"| {y} | {xs} | {ms} |")
def long_stats(px, ds, div):
    tr = total_return_index({d: px[d] for d in ds}, div); r = rets(tr, ds); s = stats(r); return s
print("\n| series | window | CAGR | vol | Sharpe | MaxDD | notes |")
print("|---|---|---|---|---|---|---|")
for nm, px, ds_, div in (('MGK', MGK, dsM, 0.5), ('QQQ', QQQL, dsM, 0.6), ('SPY', SPY, dsM, 1.5)):
    s = long_stats(px, ds_, div); print(f"| {nm} | {ds_[0]}..{ds_[-1]} | {pct(s['cagr'],2)} | {s['vol']*100:.1f}% | {s['sharpe']:.3f} | {pct(s['mdd'])} | div {div}%/yr assumed |")
for nm, px, ds_, div in (('XLG', XLG, dsX, 1.0), ('QQQ', QQQL, dsX, 0.6), ('SPY', SPY, dsX, 1.5)):
    s = long_stats(px, ds_, div); print(f"| {nm} | {ds_[0]}..{ds_[-1]} | {pct(s['cagr'],2)} | {s['vol']*100:.1f}% | {s['sharpe']:.3f} | {pct(s['mdd'])} | div {div}%/yr assumed |")
print(f"\nMGK beat QQQ in {mgk_wins} of {mgk_wins+qqq_wins} full calendar years 2008-2025.")
# sub-period split: before/after 2023
for lo, hi in (('2007-12-21', '2022-12-31'), ('2023-01-01', '2026-09-11')):
    d_ = [d for d in dsM if lo <= d <= hi]
    print(f"  {lo}..{hi}: MGK {pct(ann(rets(MGK,d_)),2)}  QQQ {pct(ann(rets(QQQL,d_)),2)}  SPY {pct(ann(rets(SPY,d_)),2)}  (price CAGR)")
for lo, hi in (('2005-05-10', '2022-12-31'), ('2023-01-01', '2026-09-11')):
    d_ = [d for d in dsX if lo <= d <= hi]
    print(f"  {lo}..{hi}: XLG {pct(ann(rets(XLG,d_)),2)}  QQQ {pct(ann(rets(QQQL,d_)),2)}  SPY {pct(ann(rets(SPY,d_)),2)}  (price CAGR)")

# ----------------------------------------------------------------------------
# 3. static-mix backtest on harness rows
# ----------------------------------------------------------------------------
print("\n## 3. STATIC-MIX BACKTEST of the current holdings (46 QTOP / 35 QQXL / 9 QNXT / 6 QQLV / 4 TBIL)\n")
# measured QQLV beta on the overlap
dsL = common(RC['QQLV'], RC['QQQ']); bL, cL = beta_corr(rets(RC['QQLV'], dsL), rets(RC['QQQ'], dsL))
QQLV_BETA = round(bL, 2)
print(f"QQLV stand-in: measured daily beta to QQQ {bL:.2f} (corr {cL:.2f}) on {dsL[0]}..{dsL[-1]}; Raincheck quotes 0.18. "
      f"Modelled as {QQLV_BETA:.2f} x QQQ-core + {1-QQLV_BETA:.2f} x bill. 6% of the book, so any stand-in moves book beta by < 0.05.")
# expense-ratio adjustments relative to the harness legs: core = QQQ (net of QQQ's 0.20%) -> QTOP/QNXT 0.20% = no adj;
# lev2 carries 0.95% (= QQXL 0.95%); QQLV 0.25% -> -0.05%/yr on that sleeve; TBIL 0.15% on the bill sleeve.
EXTRA_ER_PA = MIX['QQLV'] * QQLV_BETA * 0.0005 + (MIX['TBIL'] + MIX['QQLV'] * (1 - QQLV_BETA)) * 0.0015
print(f"Residual expense drag not already inside the harness legs: {EXTRA_ER_PA*100:.3f}%/yr (applied daily).")

def mix_weights():
    core = MIX['QTOP'] + MIX['QNXT'] + MIX['QQLV'] * QQLV_BETA
    cash = MIX['TBIL'] + MIX['QQLV'] * (1 - QQLV_BETA)
    return (core, 0.0, MIX['QQXL'], 0.0, cash)
MIXW = mix_weights()
MIX_BETA = MIXW[0] + 2 * MIXW[2]
print(f"Harness weights (core, TQQQ, QLD, XLU, cash) = {tuple(round(x,3) for x in MIXW)}; proxy beta {MIX_BETA:.2f} "
      f"(Raincheck's own beta-weighted figure with QTOP 1.05 / QQXL 2.15 / QNXT 0.78 / QQLV 0.18: "
      f"{MIX['QTOP']*1.05+MIX['QQXL']*2.15+MIX['QNXT']*0.78+MIX['QQLV']*0.18:.2f}).")

def const_fn(w):
    def f(r): return w
    return f
def lev_fn(L):
    """constant proxy-beta L using core / lev2 / lev3 / cash (never more than one leveraged leg)."""
    if L <= 1: return const_fn((L, 0, 0, 0, 1 - L))
    if L <= 2: return const_fn((2 - L, 0, L - 1, 0, 0))
    return const_fn((0, L - 2, 3 - L, 0, 0))
def live_fn(r):
    w = W[r['eff']]; f = extension_scale(r['eff'], r['gaps'])
    if f < 1: w = tuple(a * f for a in w[:4]) + (1 - f * sum(w[:4]),)
    return vt(w, r['vol'])

def run_adj(rws, fn, extra_er=0.0):
    rs, exp_ = run(rws, fn)
    if extra_er: rs = [x - extra_er / 252 for x in rs]
    return rs, exp_
def avg_beta(rws, fn):
    return mean([sum(w * b for w, b in zip(fn(r), (1, 3, 2, 0.5, 0))) for r in rws])

def report(label, rws, fn, extra_er=0.0, dates=None):
    rs, exp_ = run_adj(rws, fn, extra_er); s = stats(rs)
    dates = dates or [r['d'] for r in rws]
    yb = by_year(dates, rs); worst = min(yb.items(), key=lambda kv: kv[1])
    return dict(label=label, rs=rs, exp=exp_, beta=avg_beta(rws, fn), yb=yb, worst=worst, **s)
def show_rows(res_list, years=('2008', '2020', '2022')):
    print("| strategy | CAGR | vol | Sharpe | MaxDD | worst yr | " + " | ".join(years) + " | avg deployed | avg nominal beta (w x leg beta) |")
    print("|---|---|---|---|---|---|" + "---|" * len(years) + "---|---|")
    for x in res_list:
        ys = " | ".join(pct(x['yb'][y]) if y in x['yb'] else "-" for y in years)
        print(f"| {x['label']} | {pct(x['cagr'],2)} | {x['vol']*100:.1f}% | {x['sharpe']:.3f} | {pct(x['mdd'])} | {x['worst'][0]} {pct(x['worst'][1])} | {ys} | {x['exp']:.2f} | {x['beta']:.2f} |")

print(f"\nHarness rows 2000-07..2026-08 (n={len(rows)}); costs: 4bp one-way, {S.REBALANCE_DRIFT_BAND:.0%} L1 drift band, lev2 leg = daily-reset 2x QQQ with 0.95% ER + financing at bill+spread.\n")
R3 = [report('NASDAQ-30 static mix (46/35/9/6/4)', rows, const_fn(MIXW), EXTRA_ER_PA),
      report('QQQ buy-and-hold', rows, const_fn((1, 0, 0, 0, 0))),
      report(f'constant {MIX_BETA:.2f}x QQQ (core+lev2, same rows)', rows, lev_fn(MIX_BETA)),
      report('constant 1.30x QQQ (core+lev2)', rows, lev_fn(1.30)),
      report('LIVE design (harness run)', rows, live_fn)]
show_rows(R3)
live_ev = evaluate(rows, live_fn)
print(f"\nLIVE reproduction check: {live_ev['cagr']*100:.2f}% / {live_ev['sharpe']:.3f} / {live_ev['mdd']*100:.1f}%  search {live_ev['s_sharpe']:.3f} holdout {live_ev['h_sharpe']:.3f} (standing: 22.18% / 0.913 / -33.6%, 1.103, 0.768).")

# --- MGK-window rows: same dates, mega-cap legs -----------------------------
mgk_tr = total_return_index(MGK, 0.5)
mgk_l2 = synth_leveraged(MGK, 2, 0.95, rate_on, div_pa=0.5)
mgk_l3 = synth_leveraged(MGK, 3, 0.84, rate_on, div_pa=0.5)
ix_rows = {r['d']: i for i, r in enumerate(rows)}
mrows, qrows_m = [], []
for i in range(len(rows) - 1):
    d0, d1 = rows[i]['d'], rows[i + 1]['d']
    if d0 in MGK and d1 in MGK:
        r = dict(rows[i]); r['legs'] = (mgk_tr[d1] / mgk_tr[d0] - 1, mgk_l3[d1] / mgk_l3[d0] - 1, mgk_l2[d1] / mgk_l2[d0] - 1,
                                       rows[i]['legs'][3], rows[i]['legs'][4])
        mrows.append(r); qrows_m.append(rows[i])
MGK_ER_ADJ = (MIX['QTOP']) * (0.0020 - 0.0007)   # QTOP 0.20% vs MGK 0.07%: mega-cap sleeve pays 13bp more than MGK
print(f"\nMGK window {mrows[0]['d']}..{mrows[-1]['d']} (n={len(mrows)}, rows dropped where MGK has no bar: {len([r for r in rows if mrows[0]['d']<=r['d']<=mrows[-1]['d']])-len(mrows)}). "
      f"QTOP->MGK total return (0.5%/yr div assumed), QQXL->daily-reset 2x MGK (0.95% ER), QNXT->MGK (residual noted in section 1), QQLV->{QQLV_BETA:.2f}x MGK + bill, TBIL->bill. "
      f"Extra ER drag {(EXTRA_ER_PA+MGK_ER_ADJ)*100:.3f}%/yr.\n")
R3m = [report('NASDAQ-30 mix on MGK legs', mrows, const_fn(MIXW), EXTRA_ER_PA + MGK_ER_ADJ),
       report('NASDAQ-30 mix on QQQ legs (same dates)', qrows_m, const_fn(MIXW), EXTRA_ER_PA),
       report('MGK buy-and-hold', mrows, const_fn((1, 0, 0, 0, 0))),
       report('QQQ buy-and-hold', qrows_m, const_fn((1, 0, 0, 0, 0))),
       report(f'constant {MIX_BETA:.2f}x MGK', mrows, lev_fn(MIX_BETA)),
       report('LIVE design (QQQ legs, same dates)', qrows_m, live_fn)]
show_rows(R3m)

# ----------------------------------------------------------------------------
# 4. managed leverage: bounds on the unobservable Market Signal
# ----------------------------------------------------------------------------
print("\n## 4. THE MANAGED-LEVERAGE QUESTION\n")
LADDER = dict(strong=2.15, weak=1.30, neutral=1.05, off=0.18)
def ladder_fn(level_of):
    """level_of(r) -> key in LADDER; weights as a constant-beta line at that rung."""
    cache = {k: lev_fn(v)(None) for k, v in LADDER.items()}
    def f(r): return cache[level_of(r)]
    return f
# causal QQQ features attached by date (signal known at close of d0)
dsq = D['ds']; qvv = [D['qqq'][d] for d in dsq]; qix_ = {d: i for i, d in enumerate(dsq)}
def smaq(i, n): return sum(qvv[i - n + 1:i + 1]) / n if i >= n - 1 else None
FEAT = {}
for r in rows:
    i = qix_[r['d']]; p = qvv[i]
    m50, m200 = smaq(i, 50), smaq(i, 200)
    FEAT[r['d']] = dict(above50=p > m50, above200=p > m200,
                        mom20=p / qvv[i - 20] - 1, mom60=p / qvv[i - 60] - 1,
                        hi20=p >= max(qvv[i - 20:i]), lo20=p <= min(qvv[i - 20:i]),
                        hi55=p >= max(qvv[i - 55:i]), lo55=p <= min(qvv[i - 55:i]))
# (a) perfect foresight: 2.15x if next calendar month's QQQ return > 0 else 0.18x
mstart = {}
for i, r in enumerate(rows):
    mstart.setdefault(r['d'][:7], i)
mret = {}
for m, i0 in mstart.items():
    i1 = mstart.get(next_m := (lambda y, mo: f"{y + (mo == 12):04d}-{(mo % 12) + 1:02d}")(int(m[:4]), int(m[5:7])))
    if i1 is None: continue
    nav = 1.0
    for r in rows[i0:i1]: nav *= 1 + r['legs'][0]
    mret[m] = nav - 1
def pf_level(r):
    m = r['d'][:7]; return 'strong' if mret.get(m, 0.0) > 0 else 'off'
# (b) mechanical proxies
def ma_level(r):
    f = FEAT[r['d']]
    if f['above50'] and f['above200']: return 'strong'
    if f['above200']: return 'weak'
    if f['above50']: return 'neutral'
    return 'off'
CLS = dict(A='strong', B='weak', C='neutral', D='neutral', E='off', F='off')
def cls_level(r): return CLS[r['eff']]
def mom_level(r):
    f = FEAT[r['d']]
    if f['mom20'] > 0 and f['mom60'] > 0: return 'strong'
    if f['mom20'] > 0: return 'weak'
    if f['mom60'] > 0: return 'neutral'
    return 'off'
def mom2_level(r): return 'strong' if FEAT[r['d']]['mom20'] > 0 else 'off'
# key-level rule: sticky bull after a 20d-high breakout, sticky bear after a 20d-low breakdown
_kl = {}; st = 'bull'
for r in rows:
    f = FEAT[r['d']]
    if f['hi20']: st = 'bull'
    elif f['lo20']: st = 'bear'
    _kl[r['d']] = st
def key_level(r):
    if _kl[r['d']] == 'bear': return 'off'
    return 'strong' if FEAT[r['d']]['above50'] else 'weak'
def flip(level_of):
    inv = dict(strong='off', weak='neutral', neutral='weak', off='strong')
    def f(r): return inv[level_of(r)]
    return f

def switches(level_of):
    n = 0; prev = None
    for r in rows:
        x = level_of(r)
        if prev is not None and x != prev: n += 1
        prev = x
    return n / (len(rows) / 252)

def matched_const(rws, target_beta):
    """exposure-matched control: constant-beta QQQ line with the same average beta (bisection)."""
    lo, hi = 0.0, 3.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if avg_beta(rws, lev_fn(mid)) < target_beta: lo = mid
        else: hi = mid
    return (lo + hi) / 2

print("Ladder rungs (proxy beta): STRONG 2.15 (0.15 lev3 + 0.85 lev2), WEAK 1.30 (0.30 lev2 + 0.70 core), NEUTRAL 1.05, OFF 0.18 (0.18 core + 0.82 bill).")
print("Each rule is a constant-beta line switched by a causal QQQ feature known at the close of d0; costs/drift band inside harness run().\n")
print("| rule | CAGR | vol | Sharpe | MaxDD | worst yr | 2008 | 2020 | 2022 | avg beta | switches/yr | matched const beta: CAGR / Sharpe / MDD | Sharpe edge vs matched | flipped Sharpe |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
R4 = []
def rule_row(label, level_of, placebo=True):
    x = report(label, rows, ladder_fn(level_of))
    k = matched_const(rows, x['beta']); c = report(f'const {k:.2f}x', rows, lev_fn(k))
    fs = stats(run(rows, ladder_fn(flip(level_of)))[0])['sharpe'] if placebo else float('nan')
    x['matched'] = c; x['flip_sharpe'] = fs; x['sw'] = switches(level_of)
    print(f"| {label} | {pct(x['cagr'],2)} | {x['vol']*100:.1f}% | {x['sharpe']:.3f} | {pct(x['mdd'])} | {x['worst'][0]} {pct(x['worst'][1])} | {pct(x['yb']['2008'])} | {pct(x['yb']['2020'])} | {pct(x['yb']['2022'])} | {x['beta']:.2f} | {x['sw']:.1f} | "
          f"{pct(c['cagr'],2)} / {c['sharpe']:.3f} / {pct(c['mdd'])} | {x['sharpe']-c['sharpe']:+.3f} | {fs:.3f} |")
    R4.append(x); return x
rule_row('(a) PERFECT FORESIGHT next-month sign', pf_level, placebo=False)
rule_row('(b1) price vs 50d/200d (4 rungs)', ma_level)
rule_row('(b2) live 50/200 classifier A..F', cls_level)
rule_row('(b3) 20d & 60d momentum sign', mom_level)
rule_row('(b4) 20d momentum sign (2 rungs)', mom2_level)
rule_row('(b5) key level: 20d breakout/breakdown', key_level)
# static mix and live for reference in the same table
xs = report('static mix (reference)', rows, const_fn(MIXW), EXTRA_ER_PA); k = matched_const(rows, xs['beta']); c = report('', rows, lev_fn(k))
print(f"| static 46/35/9/6/4 mix | {pct(xs['cagr'],2)} | {xs['vol']*100:.1f}% | {xs['sharpe']:.3f} | {pct(xs['mdd'])} | {xs['worst'][0]} {pct(xs['worst'][1])} | {pct(xs['yb']['2008'])} | {pct(xs['yb']['2020'])} | {pct(xs['yb']['2022'])} | {xs['beta']:.2f} | 0 | {pct(c['cagr'],2)} / {c['sharpe']:.3f} / {pct(c['mdd'])} | {xs['sharpe']-c['sharpe']:+.3f} | - |")
xl = R3[4]; k = matched_const(rows, xl['beta']); c = report('', rows, lev_fn(k))
print(f"| LIVE design (reference) | {pct(xl['cagr'],2)} | {xl['vol']*100:.1f}% | {xl['sharpe']:.3f} | {pct(xl['mdd'])} | {xl['worst'][0]} {pct(xl['worst'][1])} | {pct(xl['yb']['2008'])} | {pct(xl['yb']['2020'])} | {pct(xl['yb']['2022'])} | {xl['beta']:.2f} | - | {pct(c['cagr'],2)} / {c['sharpe']:.3f} / {pct(c['mdd'])} | {xl['sharpe']-c['sharpe']:+.3f} | - |")

# search / holdout split for the mechanical rules
from improvement_search import SEARCH, HOLDOUT, era
print("\nBoth-era check (Sharpe): search 2015-11+ / holdout 2000-07..2015-10, rule vs its matched constant-beta line\n")
print("| rule | search rule | search matched | holdout rule | holdout matched |")
print("|---|---|---|---|---|")
for x, lv in zip(R4[1:], (ma_level, cls_level, mom_level, mom2_level, key_level)):
    out = [x['label']]
    for lo, hi in (SEARCH, HOLDOUT):
        e = era(rows, lo, hi); s1 = stats(run(e, ladder_fn(lv))[0])['sharpe']
        k = matched_const(e, avg_beta(e, ladder_fn(lv))); s2 = stats(run(e, lev_fn(k))[0])['sharpe']
        out += [f"{s1:.3f}", f"{s2:.3f}"]
    print("| " + " | ".join(out) + " |")
print(f"\nCandidate count in (b): 5 mechanical rules, no parameter sweeps; 1 perfect-foresight bound.")

# (c) the known switch: 2026-09-09 STRONG->WEAK BULLISH
print("\n(c) The one observed Market Signal action: 2026-09-09 STRONG BULLISH -> WEAK BULLISH (3x sibling cut to 1.71x).")
print("NASDAQ-30 book 2026-09-09 close -> 2026-09-11 close using the actual ETF closes (holdings frozen at 46/35/9/6/4, no rebalance):\n")
print("| leg | weight | 09-09 | 09-10 | 09-11 | 09-09->09-11 | contribution |")
print("|---|---|---|---|---|---|---|")
tot = 0.0
for t, w in MIX.items():
    p = RC[t]; r_ = p['2026-09-11'] / p['2026-09-09'] - 1; tot += w * r_
    print(f"| {t} | {w:.0%} | {p['2026-09-09']:.3f} | {p['2026-09-10']:.3f} | {p['2026-09-11']:.3f} | {pct(r_,2)} | {pct(w*r_,2)} |")
rq = RC['QQQ']['2026-09-11'] / RC['QQQ']['2026-09-09'] - 1
print(f"| **book** | 100% | | | | **{pct(tot,2)}** | vs QQQ {pct(rq,2)}; QQQ 09-10 {pct(RC['QQQ']['2026-09-10']/RC['QQQ']['2026-09-09']-1,2)}, 09-11 {pct(RC['QQQ']['2026-09-11']/RC['QQQ']['2026-09-10']-1,2)} |")
print(f"Two sessions after the downgrade the book did {pct(tot-rq,2)} relative to QQQ: a 1.3x book on a flat two days; the signal change itself had no measurable consequence in this window.")

# ----------------------------------------------------------------------------
# 5. leveraged-ETF mechanics
# ----------------------------------------------------------------------------
print("\n## 5. LEVERAGED-ETF MECHANICS (2x daily reset vs monthly-rebalanced 2x; the 35% sleeve)\n")
def monthly2x(dates, under_r, cash_r, k=2.0, er=0.0095):
    """hand-rolled monthly-rebalanced k-x: exposure reset to k at each month start, financing at bill (k-1), ER; NOT a harness figure."""
    out = []; ex = k
    for i, (d, ru, rc) in enumerate(zip(dates, under_r, cash_r)):
        if i == 0 or d[:7] != dates[i - 1][:7]: ex = k
        g = ex * ru - (k - 1) * rc - er / 252
        out.append(g); ex = ex * (1 + ru) / (1 + g)
    return out
QLD = load_px('data/qld_ohlc.csv')
print("| year | QQQ TR | 2x daily-reset (harness lev2, 0.95% ER) | 2x monthly-rebalanced | daily-reset minus monthly | real QLD (price) | 35% sleeve contribution (daily reset) |")
print("|---|---|---|---|---|---|---|")
for y in ('2008', '2009', '2011', '2015', '2018', '2020', '2021', '2022', '2023', '2024', '2025'):
    e = [r for r in rows if r['d'][:4] == y]; dd = [r['d'] for r in e]
    q = math.expm1(sum(math.log1p(r['legs'][0]) for r in e)); l2 = math.expm1(sum(math.log1p(r['legs'][2]) for r in e))
    m2 = math.expm1(sum(math.log1p(x) for x in monthly2x(dd, [r['legs'][0] for r in e], [r['legs'][4] for r in e])))
    dq = sorted(d for d in QLD if d[:4] == y); real = (QLD[dq[-1]] / QLD[dq[0]] - 1) if dq else None
    print(f"| {y} | {pct(q)} | {pct(l2)} | {pct(m2)} | {pct(l2-m2)} | {pct(real) if real is not None else '-'} | {pct(0.35*l2)} |")
print("\nReading: in a trending year the daily reset HELPS (2x compounding of a one-way move beats monthly 2x); in a choppy or V-shaped year (2020, 2022) it costs. "
      "Holding 35% of the book in a 2x fund through a -33% QQQ year (2022) costs roughly 0.35 x the 2x fund's loss, i.e. the sleeve alone knocks about a fifth off the book, plus ~0.33%/yr of ER (0.35 x 0.95%) and financing at bill+spread on the borrowed half.")
# the mix in the three drawdown years, decomposed
print("\n| year | book (mix) | QTOP-sleeve (core, 55%*) | 2x sleeve (35%) | cash-ish (10%) |")
print("|---|---|---|---|---|")
for y in ('2008', '2020', '2022'):
    e = [r for r in rows if r['d'][:4] == y]
    q = math.expm1(sum(math.log1p(r['legs'][0]) for r in e)); l2 = math.expm1(sum(math.log1p(r['legs'][2]) for r in e)); c_ = math.expm1(sum(math.log1p(r['legs'][4]) for r in e))
    print(f"| {y} | {pct(R3[0]['yb'][y])} | {pct(MIXW[0]*q)} | {pct(MIXW[2]*l2)} | {pct(MIXW[4]*c_)} |")
print("*core sleeve = QTOP 46 + QNXT 9 + QQLV beta share; harness core is QQQ total return.")

# ----------------------------------------------------------------------------
# 6. side by side with the live design; combined book
# ----------------------------------------------------------------------------
print("\n## 6. SIDE BY SIDE WITH THE LIVE DESIGN, AND THE COMBINED BOOK ($200k live + $20k NASDAQ-30)\n")
def side(label, rws_mix, rws_live, extra):
    m = report('NASDAQ-30 static mix', rws_mix, const_fn(MIXW), extra); l = report('LIVE design', rws_live, live_fn)
    q = report('QQQ B&H', rws_live, const_fn((1, 0, 0, 0, 0)))
    b, c = beta_corr(m['rs'], l['rs'])
    wl, wm = 200 / 220, 20 / 220
    combo = [wl * a + wm * x for a, x in zip(l['rs'], m['rs'])]
    cs = stats(combo); cyb = by_year([r['d'] for r in rws_live], combo)
    # daily beta of each book to QQQ core
    bq_m = beta_corr(m['rs'], [r['legs'][0] for r in rws_live])[0]; bq_l = beta_corr(l['rs'], [r['legs'][0] for r in rws_live])[0]; bq_c = beta_corr(combo, [r['legs'][0] for r in rws_live])[0]
    print(f"### {label}: {rws_live[0]['d']}..{rws_live[-1]['d']} (n={len(rws_live)})\n")
    print("| book | CAGR | vol | Sharpe | MaxDD | worst yr | 2008 | 2020 | 2022 | avg deployed | realised regression beta to QQQ |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for x, bq in ((m, bq_m), (l, bq_l), (q, 1.0)):
        print(f"| {x['label']} | {pct(x['cagr'],2)} | {x['vol']*100:.1f}% | {x['sharpe']:.3f} | {pct(x['mdd'])} | {x['worst'][0]} {pct(x['worst'][1])} | {pct(x['yb'].get('2008',float('nan')))} | {pct(x['yb']['2020'])} | {pct(x['yb']['2022'])} | {x['exp']:.2f} | {bq:.2f} |")
    cw = min(cyb.items(), key=lambda kv: kv[1])
    print(f"| combined 200k/20k (91%/9%) | {pct(cs['cagr'],2)} | {cs['vol']*100:.1f}% | {cs['sharpe']:.3f} | {pct(cs['mdd'])} | {cw[0]} {pct(cw[1])} | {pct(cyb.get('2008',float('nan')))} | {pct(cyb['2020'])} | {pct(cyb['2022'])} | - | {bq_c:.2f} |")
    print(f"\nDaily-return correlation mix vs live: {c:.3f} (beta of mix on live {b:.2f}). "
          f"Live avg beta {l['beta']:.2f}, mix {m['beta']:.2f}; combined avg beta {wl*l['beta']+wm*m['beta']:.2f}.")
    lo20, hi20, p20, sl20, sh20, ps20 = boot(m['rs'], l['rs'], 20, 1)
    lo60, hi60, p60, sl60, sh60, ps60 = boot(m['rs'], l['rs'], 60, 2)
    print(f"Block bootstrap (mix minus live): block 20 log-ret CI [{lo20:+.3f},{hi20:+.3f}] P(<=0) {p20:.2f}, Sharpe CI [{sl20:+.3f},{sh20:+.3f}] P(<=0) {ps20:.2f}; "
          f"block 60 log-ret CI [{lo60:+.3f},{hi60:+.3f}] P(<=0) {p60:.2f}, Sharpe CI [{sl60:+.3f},{sh60:+.3f}] P(<=0) {ps60:.2f}.")
    # worst combined drawdown episodes
    return m, l, combo
side('2000-07+ harness rows (QQQ legs for both)', rows, rows, EXTRA_ER_PA)
print()
side('2007-12+ MGK window (mix on MGK legs, live on QQQ legs, identical dates)', mrows, qrows_m, EXTRA_ER_PA + MGK_ER_ADJ)
print("\nDone.")
