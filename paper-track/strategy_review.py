"""Whole-strategy review, 2026-09-06. Everything below is a question the
project had NOT yet asked (checked against STRATEGY.md and the paper-track
scripts before writing this):

  R1  portfolio-level (leverage-aware) vol target: scale by
      min(1, T / (beta_eff * vol_qqq)) instead of min(1, 0.20 / vol_qqq), so
      a 1.6x state A and a 1.0x state C are held to the SAME risk. Swept T
      and compared to live at matched CAGR.
  R2  classifier ensemble: average the live weights implied by three MA
      pairs (50/200, 40/160, 60/240) -- a whipsaw/timing-luck reducer.
      (ma_window_sweep.py found every OTHER pair worse alone; this asks
      whether averaging helps.)
  R3  simplification: does the six-state granularity earn its keep vs
      2- and 3-state collapses of the same weights?
  R4  after-tax: lot-level FIFO simulation of the live design with annual
      tax on realised gains (ST 40.8% = 37% + 3.8% NIIT, LT 23.8%, losses
      netted and carried forward) vs buy-and-hold QQQ taxed only on
      liquidation. The account's objective is to beat SPY/QQQ; buy-and-hold
      defers tax and the strategy realises short-term gains ~41x/yr, so
      the after-tax gap is the one that matters in a taxable account.
"""
import math
import sys
from datetime import date

sys.path.insert(0, 'paper-track')
from improvement_search import (build, data, run, evaluate, era, header, show, vt,
                                live_base, SEARCH, HOLDOUT, BAND)
from improvement_search_r2 import BETA, scaled
from downturn_review import enrich, live
from state import TARGET_WEIGHTS, compute_states, sma, VOL_TARGET_PA
from drift_band_test import annual_stats, ONE_WAY_SPREAD

ST_RATE, LT_RATE = 0.408, 0.238


def cagr_matched(rows, fn_family, targets, base_cagr, label):
    """Evaluate fn_family(t) over targets, then interpolate the Sharpe/MaxDD at
    the t whose CAGR matches base_cagr."""
    evs = [(t, evaluate(rows, fn_family(t))) for t in targets]
    for t, ev in evs:
        show(f"{label} T={t:.2f}", ev, None)
    return evs


# ------------------------------------------------------------------ R1
def portfolio_vt(T):
    def fn(r):
        w = live_base(r, micro=False)
        beta = sum(w[i] * BETA[i] for i in range(4))
        v = r['vol']
        m = 1.0 if (not v or beta == 0) else min(1.0, T / (beta * v))
        return tuple(x * m for x in w[:4]) + (1 - m * sum(w[:4]),)
    return fn


# ------------------------------------------------------------------ R2
def ensemble_rows(rows, pairs):
    D = data(); ds, px = D['ds'], D['qqq']
    sts = [dict(zip(ds, compute_states(ds, px, short_n=a, long_n=b))) for a, b in pairs]
    out = []
    for r in rows:
        r2 = dict(r); r2['states'] = [s[r['d']] for s in sts]; out.append(r2)
    return out


def ensemble_fn(r):
    ws = [TARGET_WEIGHTS[s] for s in r['states']]
    w = tuple(sum(x[i] for x in ws) / len(ws) for i in range(5))
    return vt(w, r['vol'])


# ------------------------------------------------------------------ R3
def collapsed(mapping):
    def fn(r):
        return vt(TARGET_WEIGHTS[mapping[r['state']]], r['vol'])
    return fn


# ------------------------------------------------------------------ R4
def run_taxed(rows, wfn, band=BAND, st_rate=ST_RATE, lt_rate=LT_RATE):
    """Lot-level FIFO after-tax simulation. NAV starts at 1.0; each leg holds
    a list of lots [cost, value, open_date]. Tax on the year's net realised
    gains is paid from the cash leg on the first day of the next year; net
    losses carry forward. Returns (pre-tax daily rets, after-tax NAV path,
    unrealised gain at end, cumulative tax paid)."""
    lots = {j: [] for j in range(5)}
    held = prev = None
    nav = 1.0
    pre, post = [], []
    st_g = lt_g = 0.0
    carry = 0.0
    tax_paid = 0.0
    year = rows[0]['d'][:4]

    def value(j):
        return sum(l[1] for l in lots[j])

    def sell(j, amt, d):
        nonlocal st_g, lt_g
        rem = amt
        while rem > 1e-12 and lots[j]:
            l = lots[j][0]
            take = min(rem, l[1])
            frac = take / l[1]
            gain = take - l[0] * frac
            age = (date.fromisoformat(d) - date.fromisoformat(l[2])).days
            if age > 365: lt_g += gain
            else: st_g += gain
            l[0] -= l[0] * frac; l[1] -= take
            if l[1] <= 1e-12: lots[j].pop(0)
            rem -= take

    for r in rows:
        d = r['d']
        if d[:4] != year:
            # settle last year's tax
            net = st_g + lt_g + carry
            if net < 0:
                carry = net; tax = 0.0
            else:
                carry = 0.0
                # apply carried loss against ST first (worst rate) -- approximate
                st_t = max(0.0, st_g + min(0.0, lt_g))  # LT losses offset ST gains
                lt_t = max(0.0, lt_g + min(0.0, st_g))
                tax = max(0.0, min(net, st_t)) * st_rate + max(0.0, net - min(net, st_t)) * lt_rate
                tax = min(tax, net * st_rate)
            if tax > 0:
                # pay from cash leg (sell BOXX lots, which itself realises a bit; ignore that second-order)
                sell(4, min(tax, value(4)), d)
                short = tax - min(tax, value(4))
                if short > 0:   # not enough cash: sell core
                    sell(0, min(short, value(0)), d)
                nav -= tax; tax_paid += tax
            st_g = lt_g = 0.0
            year = d[:4]
        t = wfn(r)
        key = (r['state'], r['agree'])
        cost = 0.0
        if held is None:
            for j in range(5):
                if t[j] > 0: lots[j].append([t[j] * nav, t[j] * nav, d])
            held = list(t)
        else:
            cur = [value(j) for j in range(5)]
            tot = sum(cur)
            heldw = [c / tot for c in cur]
            drift = sum(abs(t[j] - heldw[j]) for j in range(5))
            if key != prev or drift > band:
                cost = ONE_WAY_SPREAD * drift
                for j in range(5):
                    tgt = t[j] * tot
                    if cur[j] > tgt + 1e-12: sell(j, cur[j] - tgt, d)
                for j in range(5):
                    tgt = t[j] * tot
                    if tgt > cur[j] + 1e-12: lots[j].append([tgt - cur[j], tgt - cur[j], d])
                held = list(t)
        # apply returns
        g = 0.0
        tot = sum(value(j) for j in range(5))
        for j in range(5):
            for l in lots[j]:
                l[1] *= (1 + r['legs'][j])
        newtot = sum(value(j) for j in range(5))
        g = newtot / tot - 1
        # transaction cost: shave proportionally
        if cost:
            for j in range(5):
                for l in lots[j]: l[1] *= (1 - cost)
            newtot *= (1 - cost)
        pre.append(g - cost)
        nav = newtot
        post.append(nav)
        prev = key
    unreal = sum(l[1] - l[0] for j in range(5) for l in lots[j])
    return pre, post, unreal, tax_paid, carry


def tax_report(rows, label):
    pre, post, unreal, paid, carry = run_taxed(rows, live())
    n = len(rows); yrs = n / 252
    pre_nav = 1.0
    for x in pre: pre_nav *= 1 + x
    end = post[-1]
    liq = end - max(0.0, unreal + carry) * LT_RATE   # liquidate everything at LT (conservative: most lots are young -> ST; report both)
    liq_st = end - max(0.0, unreal + carry) * ST_RATE
    qqq_end = 1.0
    for r in rows: qqq_end *= 1 + r['qqq']
    # QQQ proxy total return incl. dividends = core leg
    core_end = 1.0
    for r in rows: core_end *= 1 + r['legs'][0]
    core_liq = core_end - (core_end - 1) * LT_RATE
    c = lambda v: (v ** (1 / yrs) - 1) * 100
    print(f"\n{label} ({yrs:.1f}y)")
    print(f"  strategy pre-tax CAGR        {c(pre_nav):6.2f}%")
    print(f"  strategy after annual tax    {c(end):6.2f}%   (tax paid {paid:.2f} NAV units; unrealised at end {unreal:+.2f})")
    print(f"  ... and liquidated (LT/ST)   {c(liq):6.2f}% / {c(liq_st):6.2f}%")
    print(f"  QQQ (TR) buy-and-hold        {c(core_end):6.2f}%   liquidated at LT {c(core_liq):6.2f}%")
    print(f"  after-tax edge over QQQ B&H: unliquidated {c(end)-c(core_end):+.2f}pp; both liquidated {c(liq)-c(core_liq):+.2f}pp")


def main():
    rows = enrich(build())
    base = evaluate(rows, live())
    print(f"{len(rows)} days; live: CAGR {base['cagr']*100:.2f}% Sharpe {base['sharpe']:.3f} MaxDD {base['mdd']*100:.1f}%")

    print("\n=== R1: portfolio-level vol target, min(1, T / (beta_eff * vol_qqq)) ===")
    header(); show('LIVE (T=0.20 on QQQ vol)', base)
    for T in (0.20, 0.25, 0.30, 0.35, 0.40, 0.50):
        show(f"portfolio-vol T={T:.2f}", evaluate(rows, portfolio_vt(T)), base)

    print("\n=== R2: classifier ensemble (average weights of 3 MA pairs) ===")
    header(); show('LIVE (50/200 only)', base)
    for pairs in (((50, 200), (40, 160), (60, 240)), ((50, 200), (30, 150), (70, 250)),
                  ((40, 160), (50, 200)), ((50, 200), (60, 240))):
        er = ensemble_rows(rows, pairs)
        show(f"ensemble {'+'.join(f'{a}/{b}' for a, b in pairs)}", evaluate(er, ensemble_fn), base)

    print("\n=== R3: simplification -- collapsed state machines, same weights ===")
    header(); show('LIVE (6 states)', base)
    maps = {
        '2-state: ABCD->A, EF->F': dict(A='A', B='A', C='A', D='A', E='F', F='F'),
        '2-state: ABCD->A, EF->E': dict(A='A', B='A', C='A', D='A', E='E', F='E'),
        '3-state: AB->A, CD->C, EF->F': dict(A='A', B='A', C='C', D='C', E='F', F='F'),
        '3-state: AB->A, CD->D, EF->F': dict(A='A', B='A', C='D', D='D', E='F', F='F'),
        '4-state: B->A, E->F': dict(A='A', B='A', C='C', D='D', E='F', F='F'),
        '5-state: B->A': dict(A='A', B='A', C='C', D='D', E='E', F='F'),
        '5-state: C->D': dict(A='A', B='B', C='D', D='D', E='E', F='F'),
        '5-state: E->D': dict(A='A', B='B', C='C', D='D', E='D', F='F'),
    }
    for lab, m in maps.items():
        show(lab, evaluate(rows, collapsed(m)), base)

    print("\n=== R4: after-tax (taxable account; ST 40.8%, LT 23.8%, annual settlement) ===")
    tax_report(rows, '26y proxy 2000-2026')
    tax_report(era(rows, *SEARCH), 'SPMO era 2015-11+')
    tax_report(era(rows, '2024-01-01', '2099'), '2024-2026')


if __name__ == '__main__':
    main()
