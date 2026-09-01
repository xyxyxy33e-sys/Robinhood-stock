"""Run the live strategy over 2000-2026 using QQQ as the core and SYNTHETIC
leveraged legs, to stress-test it against the dot-com crash and the GFC --
the two bear markets the normal 2015-11+ backtest window excludes.

WHY THIS EXISTS: the live backtest starts 2015-11 because that is SPMO's
inception (the real core instrument). That window contains exactly one real
bear market (2022). Every per-state weight in state.py was fit inside it. So
the design had never been evaluated against 2000-02 or 2008-09 at all. This
script substitutes instruments that DO have long history, so the regime
machinery itself can be tested across 26 years:

  core  -> QQQ total return (price + QQQ_DIV_PA dividend accrual)
           NOTE: this is NOT SPMO. Results are therefore a QQQ-core VARIANT
           of the live design, not the live design itself. Read the regime
           behaviour, not the absolute return, as the finding.
  tqqq  -> synthetic 3x, qld -> synthetic 2x (see synth_leveraged below)
  xlu   -> real XLU price + XLU_DIV_PA dividend accrual (utilities yield a
           lot; ignoring it would materially understate state E)
  cash  -> 3-month T-bill (DGS3MO) compounded. BOXX tracks T-bill closely and
           does not exist before 2022 anyway.

SYNTHETIC LEVERAGE MODEL, and its validation. Daily:
    r_lev = k*(r_underlying + div) - (k-1)*(tbill + financing_spread) - ER
The (k-1) financing term is the borrowed notional; volatility decay is not
modelled explicitly -- it emerges naturally from daily compounding, which is
the correct way to get it. Validated against the REAL ETFs over their whole
overlapping history (TQQQ from 2010-02, QLD from 2009-01) at the constants
below:
    TQQQ: real CAGR 42.22%  synthetic 42.14%  gap -0.08pp/yr  tracking err 3.3%
    QLD : real CAGR 35.01%  synthetic 34.62%  gap -0.39pp/yr  tracking err 3.1%
The calibrated 0.6%/yr underlying-income term is not a free fudge factor: it
is approximately QQQ's actual dividend yield, and the SAME single value fits
both the 2x and 3x funds, which a fudge would not do. Run this file with
--validate to re-check those numbers.

CAVEATS to carry into any conclusion drawn from this script:
  - QQQ core, not SPMO (see above).
  - XLU dividend yield is a flat 3.0%/yr assumption, not actual distributions.
  - Synthetic legs carry ~3% annualised tracking error vs the real funds.
  - 2000-07..2015-10 is genuine OUT-OF-SAMPLE data for every live parameter;
    2015-11+ is the window they were fit in. Compare the two, reported below.
"""
import csv
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, 'paper-track')
from state import compute_states, compute_micro_agreement, target_weights_with_micro
from four_leg_overlay import last_trading_day_per_week

QQQ_LONG = 'data/qqq_long_history.csv'
XLU_LONG = 'data/xlu_long_history.csv'
TBILL = 'data/dgs3mo_full.csv'

QQQ_DIV_PA = 0.6          # %/yr, calibrated + matches QQQ's real dividend yield
XLU_DIV_PA = 3.0          # %/yr, assumption -- utilities are high-yield
FINANCING_SPREAD_PA = 0.30  # %/yr over 3mo T-bill, borrowed notional
TQQQ_ER, QLD_ER = 0.84, 0.95
ONE_WAY_SPREAD = 0.0004   # 4bps, same cost model as the rest of the project
START = '2000-07-01'      # 200dma warm-up from the 1999-09 data start


def load_px(path, col='c'):
    out = {}
    for r in csv.DictReader(open(path)):
        try:
            out[r['d']] = float(r[col])
        except (ValueError, KeyError):
            pass
    return out


def load_tbill_long():
    out = {}
    for r in csv.DictReader(open(TBILL)):
        try:
            out[r['observation_date']] = float(r['DGS3MO'])
        except (ValueError, KeyError):
            pass
    return out


def make_rate_lookup(tb):
    def rate_on(d):
        dd = d
        for _ in range(12):          # walk back over weekends/holidays
            if dd in tb:
                return tb[dd]
            dd = (date.fromisoformat(dd) - timedelta(days=1)).isoformat()
        return 0.0
    return rate_on


def yearfrac(d0, d1):
    return (date.fromisoformat(d1) - date.fromisoformat(d0)).days / 365.0


def synth_leveraged(under, k, er_pa, rate_on, div_pa=QQQ_DIV_PA,
                    spread_pa=FINANCING_SPREAD_PA):
    """Daily-reset synthetic leveraged ETF NAV index. See module docstring."""
    ds = sorted(under)
    nav = 1.0
    out = {ds[0]: nav}
    for i in range(1, len(ds)):
        d0, d1 = ds[i - 1], ds[i]
        yf = yearfrac(d0, d1)
        r = under[d1] / under[d0] - 1 + (div_pa / 100.0) * yf
        fin = ((rate_on(d0) + spread_pa) / 100.0) * yf
        nav *= (1 + k * r - (k - 1) * fin - (er_pa / 100.0) * yf)
        out[d1] = nav
    return out


def total_return_index(px, div_pa):
    ds = sorted(px)
    nav = 1.0
    out = {ds[0]: nav}
    for i in range(1, len(ds)):
        d0, d1 = ds[i - 1], ds[i]
        nav *= (1 + px[d1] / px[d0] - 1 + (div_pa / 100.0) * yearfrac(d0, d1))
        out[d1] = nav
    return out


def cash_index(dates, rate_on):
    nav = 1.0
    out = {dates[0]: nav}
    for i in range(1, len(dates)):
        nav *= (1 + (rate_on(dates[i - 1]) / 100.0) * yearfrac(dates[i - 1], dates[i]))
        out[dates[i]] = nav
    return out


def stats(rets):
    n = len(rets)
    nav = 1.0
    for r in rets:
        nav *= (1 + r)
    m = sum(rets) / n
    v = (sum((x - m) ** 2 for x in rets) / (n - 1)) ** 0.5
    peak = cur = 1.0
    mdd = 0.0
    for r in rets:
        cur *= (1 + r)
        peak = max(peak, cur)
        mdd = min(mdd, cur / peak - 1)
    sharpe = (m * 52.1775) / (v * math.sqrt(52.1775)) if v > 0 else float('nan')
    return nav - 1, nav ** (1 / (n / 52.1775)) - 1, sharpe, mdd


def build_weekly_rows():
    qqq = load_px(QQQ_LONG)
    xlu = load_px(XLU_LONG)
    rate_on = make_rate_lookup(load_tbill_long())

    tqqq = synth_leveraged(qqq, 3, TQQQ_ER, rate_on)
    qld = synth_leveraged(qqq, 2, QLD_ER, rate_on)
    core = total_return_index(qqq, QQQ_DIV_PA)
    xl = total_return_index(xlu, XLU_DIV_PA)
    ds = sorted(qqq)
    cash = cash_index(ds, rate_on)

    states = dict(zip(ds, compute_states(ds, qqq)))
    micro = compute_micro_agreement(ds, qqq)
    wk = last_trading_day_per_week(ds)
    keys = sorted(wk)

    rows = []
    prev_w = None
    for i in range(len(keys) - 1):
        d0, d1 = wk[keys[i]], wk[keys[i + 1]]
        st, ag = states.get(d0), micro.get(d0)
        if st is None or ag is None or d0 < START:
            continue
        w = target_weights_with_micro(st, ag)
        legs = (core[d1] / core[d0] - 1, tqqq[d1] / tqqq[d0] - 1,
                qld[d1] / qld[d0] - 1, xl[d1] / xl[d0] - 1,
                cash[d1] / cash[d0] - 1)
        gross = sum(w[j] * legs[j] for j in range(5))
        turn = 0.0 if prev_w is None else sum(abs(w[j] - prev_w[j]) for j in range(5))
        rows.append(dict(d0=d0, d1=d1, state=st, w=w,
                         net=gross - ONE_WAY_SPREAD * turn,
                         bench=legs[0]))
        prev_w = w
    return rows


def validate():
    """Re-check the synthetic legs against the real ETFs."""
    qqq = load_px(QQQ_LONG)
    rate_on = make_rate_lookup(load_tbill_long())
    for nm, path, k, er in (('TQQQ', 'TQQQ', 3, TQQQ_ER), ('QLD', 'QLD', 2, QLD_ER)):
        real = load_px(f'/home/user/robinhood/data/kairos/etf/{path}.csv')
        syn = synth_leveraged(qqq, k, er, rate_on)
        ds = sorted(set(real) & set(syn))
        yrs = (date.fromisoformat(ds[-1]) - date.fromisoformat(ds[0])).days / 365.25
        cr = (real[ds[-1]] / real[ds[0]]) ** (1 / yrs) - 1
        cs = (syn[ds[-1]] / syn[ds[0]]) ** (1 / yrs) - 1
        diffs = [(real[ds[i]] / real[ds[i - 1]] - 1) - (syn[ds[i]] / syn[ds[i - 1]] - 1)
                 for i in range(1, len(ds))]
        m = sum(diffs) / len(diffs)
        te = (sum((x - m) ** 2 for x in diffs) / (len(diffs) - 1)) ** 0.5 * math.sqrt(252)
        print(f"  {nm}: real CAGR {cr*100:6.2f}%  synthetic {cs*100:6.2f}%  "
              f"gap {(cs-cr)*100:+.2f}pp/yr  tracking error {te*100:.2f}%  "
              f"({ds[0]}..{ds[-1]})")


def main():
    if '--validate' in sys.argv:
        print("Synthetic leverage validation vs the real ETFs:")
        validate()
        return

    rows = build_weekly_rows()
    S = [r['net'] for r in rows]
    B = [r['bench'] for r in rows]
    print(f"=== live weights over {rows[0]['d0']}..{rows[-1]['d1']} "
          f"({len(rows)} weeks, {len(rows)/52.1775:.1f} yrs), QQQ core + synthetic leverage ===")
    print(f"{'':<26}{'Total':>12}{'CAGR':>9}{'Sharpe':>9}{'MaxDD':>10}")
    for nm, x in (('STRATEGY (net 4bps)', S), ('QQQ buy & hold (TR)', B)):
        t, c, s, m = stats(x)
        print(f"{nm:<26}{t*100:>11.0f}%{c*100:>8.2f}%{s:>9.3f}{m*100:>9.2f}%")

    print("\n=== in-sample vs out-of-sample (all live params were fit on 2015-11+) ===")
    print(f"{'period':<30}{'wks':>6}{'strat CAGR':>12}{'QQQ CAGR':>10}"
          f"{'strat Sh':>10}{'strat MaxDD':>13}")
    for nm, a, b in (('2000-07..2015-10  (OOS)', START, '2015-10-31'),
                     ('2015-11..2026-08  (fitted)', '2015-11-01', '2026-12-31'),
                     ('FULL 2000..2026', START, '2026-12-31')):
        sub = [r for r in rows if a <= r['d0'] <= b]
        _, cs, ss, ms = stats([r['net'] for r in sub])
        _, cb, _, _ = stats([r['bench'] for r in sub])
        print(f"{nm:<30}{len(sub):>6}{cs*100:>11.2f}%{cb*100:>9.2f}%{ss:>10.3f}{ms*100:>12.2f}%")

    print("\n=== bear markets ===")
    for nm, a, b in (('Dot-com 2000-07..2002-12', START, '2002-12-31'),
                     ('GFC 2007-10..2009-03', '2007-10-01', '2009-03-31'),
                     ('COVID 2020-02..2020-04', '2020-02-01', '2020-04-30'),
                     ('2022 bear', '2022-01-01', '2022-12-31')):
        sub = [r for r in rows if a <= r['d0'] <= b]
        if not sub:
            continue
        ts, _, _, ms = stats([r['net'] for r in sub])
        tb_, _, _, mb = stats([r['bench'] for r in sub])
        print(f"  {nm:<26} strategy {ts*100:>+7.1f}% (DD {ms*100:>6.1f}%)"
              f"   QQQ {tb_*100:>+7.1f}% (DD {mb*100:>6.1f}%)")

    print("\n=== state mix: full history vs the fitted window ===")
    for nm, a in (('2000-2026', START), ('2015-11+', '2015-11-01')):
        sub = [r for r in rows if r['d0'] >= a]
        c = {}
        for r in sub:
            c[r['state']] = c.get(r['state'], 0) + 1
        print(f"  {nm:<11} " + "  ".join(f"{k} {c.get(k,0)/len(sub)*100:4.1f}%" for k in 'ABCDEF'))


if __name__ == '__main__':
    main()
