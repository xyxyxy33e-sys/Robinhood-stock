"""After-tax return of the current live design: US taxable account vs IRA (review 2026-11, research only).

PRE-REGISTRATION (written before the first run; not edited afterwards)
---------------------------------------------------------------------
Path. Real panel 2015-11-02 .. latest, legs/weights/regime key from harness.weights() (SPMO, TQQQ, QLD, XLU, VIXM,
QQQ deep-E, QQQ VIX-panic, BOXX-like cash). The engine loop of MC.run_strategy is re-implemented: rebalance at close t
on key change, L1 drift > 5% band, or a zero-target stub; cost MC.COST x L1 turnover applied to the next day's NAV
(as a pro-rata haircut of every lot's market value, basis unchanged -- i.e. costs end up in realized results).
Instruments (tickers): SPMO, TQQQ, QLD, XLU, VIXM, QQQ (the two QQQ legs are ONE ticker), BOXX. Each rebalance is
netted per ticker: sells first (FIFO), then buys (new dollar/share lot at that day's price index).

Lots. Per ticker FIFO lots (shares on a cumulative price index, basis $, buy date, holding-period start date).
Realized gain per lot slice; short-term if days held (sale date - holding-period start) <= 365, else long-term.

Wash sales. A loss on a slice sold on day d is disallowed when shares of the same ticker are bought within 30
calendar days before (lots still held after the sale, bought d-30..d inclusive) or after (d+1..d+30). Matching is
share-for-share; each replacement share absorbs at most one disallowed loss. The disallowed loss is added to the
replacement shares' basis and the old holding period is carried (new hp start = replacement buy date - days held).
A pending (forward-window) loss that finds no buy within 30 days becomes allowed in its sale year (always resolved
before the 15 April payment). Same-day buys count (stricter reading than wash_sale.SAME_DAY_MATCHES=False; the
engine never buys and sells one ticker in the same rebalance, so this only matters for tax-payment sales).

BOXX three ways: 'free' (tax-free accrual, no gains/losses recognised -- a bound only), (i) 'deferred' (capital
asset: gains deferred until sold; sold whenever the cash-leg dollars fall, FIFO, ST/LT by holding period) -- the
HEADLINE treatment, (ii) 'ordinary' (T-bill fund: each day's accrual is ordinary income, added to basis).

Rates (NIIT 3.8% on everything, both scenarios):
  S1 federal: ST/ordinary 35%+3.8% = 38.8%, LT 15%+3.8% = 18.8%
  S2 top+CA : ST/ordinary 37%+9.3%+3.8% = 50.1%, LT 20%+9.3%+3.8% = 33.1%
Year netting: ST and LT netted separately incl. carryforwards (character kept), then cross-netted; net loss carried
forward; $3k ordinary offset ignored; ordinary income is never offset by capital losses. Tax for year Y is paid at
the close of the first session on/after 15 April Y+1, by a pro-rata sale of every holding (2 bp cost; the sale's own
gains/losses go into year Y+1). Pro-rata sales leave the weights unchanged, so the rebalance schedule is the IRA's.

End (liquidation basis). Account value at the last date, minus the liability: tax on (YTD realized ST, YTD realized
LT + all unrealized gains treated as LT) with carryforwards. "Deferred liability" = that liability minus the tax on
YTD realized alone. After-tax CAGR = liquidation value ** (252 / n_days) - 1 (harness convention); the CAGR of the
pre-liquidation account value is also printed.

Outputs per scenario x BOXX treatment and for the IRA: pre-tax and after-tax CAGR, ending multiple, MaxDD of the
daily account value (tax payments included), taxes (paid + end liability) as % of pre-tax gains (IRA multiple - 1),
share of gross positive realized gains that were short-term, number and $ of disallowed wash-sale losses
(per $1 start), deferred liability at the end.
Sanity: the IRA path must reproduce harness.run(real=True) -- report max |daily diff| and ending-multiple diff;
tolerance 1e-9 relative on the multiple.
References: buy-and-hold QQQ and SPMO (real panel price returns, 2 bp in and out), taxable, sold at the end at LT.
Known simplifications (stated in advance): price-only returns (no dividends/distributions taxed; XLU's modelled
dividend stays in its return as price); VIXM treated as an ordinary ETF (it is a commodity pool -- K-1, 60/40
Section 1256 mark-to-market -- not modelled); no state exemption for T-bill income; no $3k offset; no AMT.
"""
import datetime as dt
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as H
MC = H.MC

TICK = ['SPMO', 'TQQQ', 'QLD', 'XLU', 'VIXM', 'QQQ', 'QQQ', 'BOXX']   # leg -> ticker
NAMES = ['SPMO', 'TQQQ', 'QLD', 'XLU', 'VIXM', 'QQQ', 'BOXX']
LEG2T = np.array([NAMES.index(t) for t in TICK])
SCEN = {'S1 fed 35/15': (0.35 + 0.038, 0.15 + 0.038), 'S2 37+CA/20+CA': (0.37 + 0.093 + 0.038, 0.20 + 0.093 + 0.038)}
EPS = 1e-12
NOWASH = False   # post-hoc diagnostic switch only (see posthoc())


def tax_year(st, lt, cf_st, cf_lt, r_st, r_lt):
    """Tax on one year's net ST/LT with carryforwards (negatives). Returns (tax, new cf_st, new cf_lt)."""
    s, l = st + cf_st, lt + cf_lt
    if s < 0 < l:
        x = s + l; s, l = (0.0, x) if x >= 0 else (x, 0.0)
    elif l < 0 < s:
        x = s + l; s, l = (x, 0.0) if x >= 0 else (0.0, x)
    return max(s, 0) * r_st + max(l, 0) * r_lt, min(s, 0.0), min(l, 0.0)


class Book:
    def __init__(self, rates, boxx, ords):
        self.r_st, self.r_lt = rates if rates else (0.0, 0.0)
        self.taxable = rates is not None; self.boxx = boxx; self.ords = ords
        self.lots = [[] for _ in NAMES]          # lot = [shares, basis, buy_ord, hp_ord, repl_cap]
        self.pend = [[] for _ in NAMES]          # pending forward wash: [shares, loss/share, days_held, expiry, year]
        self.real = {}                           # year -> [st, lt, ordinary]
        self.gross = [0.0, 0.0]                  # gross positive realized gains ST, LT
        self.wash_n = 0; self.wash_usd = 0.0

    def yr(self, y):
        return self.real.setdefault(y, [0.0, 0.0, 0.0])

    def value(self, j, P):
        return sum(l[0] for l in self.lots[j]) * P[j]

    def taxed(self, j):
        return self.taxable and not (NAMES[j] == 'BOXX' and self.boxx == 'free')

    def buy(self, j, usd, P, d):
        sh = usd / P[j]; o = self.ords[d]; lot = [sh, usd, o, o, sh]
        self.lots[j].append(lot)
        if not self.taxed(j): return
        keep = []
        for p in self.pend[j]:                    # forward-window wash sales attach to this buy
            if p[3] >= o and lot[4] > EPS:
                q = min(p[0], lot[4])
                self._attach(j, lot, q, p[1] * q, p[2], o)
                self.real[p[4]][0 if p[2] <= 365 else 1] += p[1] * q    # remove the provisional loss
                p[0] -= q
            if p[0] > EPS and p[3] >= o: keep.append(p)
        self.pend[j] = keep

    def _attach(self, j, lot, q, loss, held, o):
        """Split q replacement shares off `lot`, add the disallowed loss to their basis, carry the holding period."""
        L = self.lots[j]; i = next(k for k, x in enumerate(L) if x is lot)
        frac = q / lot[0]
        new = [q, lot[1] * frac + loss, lot[2], lot[2] - held, 0.0]
        lot[0] -= q; lot[1] *= (1 - frac); lot[4] -= q
        L.insert(i + 1, new)
        if lot[0] <= EPS: L.remove(lot)
        self.wash_n += 1; self.wash_usd += loss

    def sell(self, j, usd, P, d):
        o = self.ords[d]; y = int(self.ords_y[d]); need = usd / P[j]; L = self.lots[j]
        while need > EPS and L:
            lot = L[0]; q = min(need, lot[0]); frac = q / lot[0]; b_ord = lot[2]
            basis = lot[1] * frac; proceeds = q * P[j]; g = proceeds - basis; held = o - lot[3]
            lot[0] -= q; lot[1] -= basis; lot[4] = min(lot[4], lot[0]); need -= q
            if lot[0] <= EPS * 1e3: L.pop(0)
            if not self.taxed(j): continue
            k = 0 if held <= 365 else 1
            self.yr(y)[k] += g
            if g > 0: self.gross[k] += g; continue
            if g == 0 or NOWASH: continue
            lps = -g / q; rem = q                 # loss per share
            for r in list(L):                     # backward window: still-held shares bought d-30..d
                if rem <= EPS: break
                if o - 30 <= r[2] <= o and r[2] != b_ord and r[4] > EPS:   # not the same purchase
                    m = min(rem, r[4]); self._attach(j, r, m, lps * m, held, r[2])
                    self.yr(y)[k] += lps * m; rem -= m
            if rem > EPS: self.pend[j].append([rem, lps, held, o + 30, y])

    def unreal(self, P):
        return sum(sum(l[0] * P[j] - l[1] for l in self.lots[j]) for j in range(len(NAMES)) if self.taxed(j))


def simulate(rates=None, boxx='deferred'):
    W, Lg, key = H.weights(H.sr, H.RD, True)
    ds = H.RD; s0 = next(i for i, d in enumerate(ds) if d >= '2015-11-02'); T = len(ds)
    assert np.allclose(Lg[:, 5], Lg[:, 6])
    R = np.stack([Lg[:, [i for i in range(8) if LEG2T[i] == j][0]] for j in range(len(NAMES))], -1)   # ticker rets
    P = np.ones((T, len(NAMES)))
    for t in range(s0 + 1, T): P[t] = P[t - 1] * (1 + R[t])
    dates = [dt.date.fromisoformat(d) for d in ds]
    bk = Book(rates, boxx, [x.toordinal() for x in dates]); bk.ords_y = [x.year for x in dates]
    jb = NAMES.index('BOXX')
    h = W[s0].copy(); cost = MC.COST
    for j in range(len(NAMES)):
        u = h[LEG2T == j].sum()
        if u > 0: bk.buy(j, u, P[s0], s0)
    acct = [1.0]; paid = 0.0; cf = [0.0, 0.0]; paid_years = set(); trades = 0
    for t in range(s0, T - 1):
        if t > s0:
            tgt = W[t]; drift = np.abs(tgt - h).sum()
            stub = ((tgt == 0) & (h > MC.S.ZERO_LEG_EPS)).any()
            reb = key[t] != key[t - 1] or drift > MC.S.REBALANCE_DRIFT_BAND or stub
            cost = MC.COST * drift if reb else 0.0
            if reb:
                trades += 1; nav = sum(bk.value(j, P[t]) for j in range(len(NAMES)))
                tt = np.array([tgt[LEG2T == j].sum() for j in range(len(NAMES))]) * nav
                cur = np.array([bk.value(j, P[t]) for j in range(len(NAMES))])
                for j in range(len(NAMES)):
                    if cur[j] - tt[j] > EPS: bk.sell(j, cur[j] - tt[j], P[t], t)
                for j in range(len(NAMES)):
                    if tt[j] - cur[j] > EPS: bk.buy(j, tt[j] - cur[j], P[t], t)
                h = tgt.copy()
            # tax payment for the prior year: first session on/after 15 April
            y = dates[t].year
            if bk.taxable and (y - 1) not in paid_years and dates[t] >= dt.date(y, 4, 15) and (y - 1) >= dates[s0].year:
                st, lt, od = bk.yr(y - 1)
                tx, cf[0], cf[1] = tax_year(st, lt, cf[0], cf[1], bk.r_st, bk.r_lt)
                tx += max(od, 0) * bk.r_st; paid_years.add(y - 1)
                nav = sum(bk.value(j, P[t]) for j in range(len(NAMES)))
                if tx > 0:
                    f = tx / nav
                    for j in range(len(NAMES)):
                        v = bk.value(j, P[t])
                        if v > 0: bk.sell(j, v * f, P[t], t)
                    paid += tx; cost = 1 - (1 - cost) * (1 - MC.COST * f / (1 - f))   # 2 bp on the sale
        r = Lg[t + 1]; g = (h * r).sum()
        if boxx == 'ordinary' and bk.taxable:     # T-bill fund: accrual is ordinary income, into basis
            for l in bk.lots[jb]:
                inc = l[0] * P[t, jb] * R[t + 1, jb]; l[1] += inc; bk.yr(dates[t + 1].year)[2] += inc
        if cost > 0:
            for L in bk.lots:
                for l in L: l[0] *= (1 - cost); l[4] *= (1 - cost)
        h = h * (1 + r) / (1 + g)
        acct.append(sum(bk.value(j, P[t + 1]) for j in range(len(NAMES))))
    acct = np.array(acct); Pe = P[-1]; ye = dates[-1].year
    st, lt, od = bk.yr(ye)
    tx_ytd = tax_year(st, lt, cf[0], cf[1], bk.r_st, bk.r_lt)[0] + max(od, 0) * bk.r_st
    tx_liq = tax_year(st, lt + bk.unreal(Pe), cf[0], cf[1], bk.r_st, bk.r_lt)[0] + max(od, 0) * bk.r_st
    return dict(acct=acct, n=len(acct) - 1, paid=paid, tx_ytd=tx_ytd, deferred=tx_liq - tx_ytd, liq=acct[-1] - tx_liq,
                gross=bk.gross, wash_n=bk.wash_n, wash_usd=bk.wash_usd, trades=trades, cf=cf,
                real=bk.real, dates=ds[s0:])


def mdd(x):
    return (x / np.maximum.accumulate(x) - 1).min()


def bh(leg, rates):
    r = H.pr[leg]; ds = H.RD; s0 = next(i for i, d in enumerate(ds) if d >= '2015-11-02')
    nav = np.concatenate([[1.0], np.cumprod(1 + r[s0 + 1:])]) * (1 - MC.COST)
    end = nav[-1] * (1 - MC.COST); gain = end - (1.0)
    liq = end - max(gain, 0) * (rates[1] if rates else 0.0); n = len(nav) - 1
    return dict(pre=nav[-1] ** (252 / n) - 1, aft=liq ** (252 / n) - 1, mult=liq, mdd=mdd(nav))


def main():
    r_h, ds_h, _ = H.run(True)
    ira = simulate(None)
    a = ira['acct']; ri = a[1:] / a[:-1] - 1
    dmax = np.abs(ri - r_h).max(); mult_h = np.prod(1 + r_h)
    print(f"Panel {ds_h[0]}..{ds_h[-1]}  n={len(r_h)}  rebalances {ira['trades']}")
    print(f"SANITY IRA vs harness.run(real=True): ending {a[-1]:.6f} vs {mult_h:.6f}  rel diff {a[-1]/mult_h-1:+.2e}  "
          f"max |daily diff| {dmax:.2e}  -> {'PASS' if abs(a[-1]/mult_h-1) < 1e-9 else 'FAIL'}")
    n = ira['n']; pre_c = a[-1] ** (252 / n) - 1; pre_g = a[-1] - 1
    print("\nAll $ figures per $1 initial. Taxes% = (taxes paid + end liability) / IRA pre-tax gain.")
    hdr = (f"{'case':<30}{'CAGR acct':>10}{'CAGR liq':>10}{'mult liq':>9}{'MaxDD':>8}{'paid':>8}{'liab end':>9}"
           f"{'defer':>8}{'tax%gain':>9}{'ST share':>9}{'wash n':>7}{'wash $':>8}")
    print(hdr); print('-' * len(hdr))
    print(f"{'IRA (no tax)':<30}{pre_c*100:9.1f}%{pre_c*100:9.1f}%{a[-1]:9.2f}{mdd(a)*100:7.1f}%{0:8.2f}{0:9.2f}{0:8.2f}"
          f"{0:8.1f}%{'-':>9}{'-':>7}{'-':>8}")
    res = {}
    for sn, rates in SCEN.items():
        for bx in ('deferred', 'ordinary', 'free'):
            o = simulate(rates, bx); res[(sn, bx)] = o; ac = o['acct']
            liab = o['tx_ytd'] + o['deferred']; tot = o['paid'] + liab
            g = o['gross']; sts = g[0] / (g[0] + g[1]) if g[0] + g[1] > 0 else float('nan')
            print(f"{sn+' BOXX '+bx:<30}{(ac[-1]**(252/n)-1)*100:9.1f}%{(o['liq']**(252/n)-1)*100:9.1f}%{o['liq']:9.2f}"
                  f"{mdd(ac)*100:7.1f}%{o['paid']:8.2f}{liab:9.2f}{o['deferred']:8.2f}{tot/pre_g*100:8.1f}%"
                  f"{sts*100:8.1f}%{o['wash_n']:7d}{o['wash_usd']:8.3f}")
    print("\nBuy-and-hold references (taxable, sold at end at LT; pre-tax = IRA):")
    for leg, nm in (('qqq', 'QQQ'), ('spmo', 'SPMO')):
        b0 = bh(leg, None)
        print(f"  {nm:<5} pre-tax CAGR {b0['pre']*100:5.1f}%  mult {b0['mult']:6.2f}  MaxDD {b0['mdd']*100:5.1f}%", end='')
        for sn, rates in SCEN.items():
            b = bh(leg, rates); print(f" | {sn}: after-tax {b['aft']*100:5.1f}% (mult {b['mult']:5.2f})", end='')
        print()
    o = res[('S1 fed 35/15', 'deferred')]
    print("\nHeadline (S1, BOXX deferred) realized by year [ST, LT, ordinary] after wash adjustments:")
    for y in sorted(o['real']):
        st, lt, od = o['real'][y]; print(f"  {y}: ST {st:+9.3f}  LT {lt:+9.3f}  ord {od:+7.3f}")
    print(f"  gross positive realized gains: ST {o['gross'][0]:.2f}  LT {o['gross'][1]:.2f}; end carryforwards {o['cf']}")


def posthoc():
    """POST-HOC diagnostics (added after the first run, not pre-registered): which drivers make the drag."""
    global NOWASH
    ira = simulate(None)['acct'][-1]; n = len(H.run(True)[0]); c = lambda m: (m ** (252 / n) - 1) * 100
    print("\nPOST-HOC drivers (S1, BOXX deferred unless stated; liquidation-basis CAGR):")
    base = simulate(SCEN['S1 fed 35/15'])['liq']
    print(f"  as registered                                 {c(base):5.1f}%  mult {base:6.2f}")
    r = SCEN['S1 fed 35/15']; lt = simulate((r[1], r[1]))['liq']
    print(f"  all realized gains taxed at the LT rate 18.8%    {c(lt):5.1f}%  mult {lt:6.2f}   (character effect)")
    NOWASH = True; nw = simulate(r)['liq']; NOWASH = False
    print(f"  wash-sale rule switched off                     {c(nw):5.1f}%  mult {nw:6.2f}   (wash effect)")
    for nm, rt in SCEN.items():
        dfr = 1 + (ira - 1) * (1 - rt[0])
        print(f"  {nm}: same gains, all ST, but tax deferred to the end   {c(dfr):5.1f}%  mult {dfr:6.2f}   (pay-annually effect)")


if __name__ == '__main__':
    main()
    posthoc()
