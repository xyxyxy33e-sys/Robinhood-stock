"""One-shot "untouched data" test of the 11 Nov 2026 live design. Research only.

PRE-REGISTRATION (written before the first run; not to be edited after it). Run once, report, do not tune.

DESIGN (frozen). harness.CUR exactly: MC.LIVE rows (B 50% core / 50% cash, C 100% core, E/F cash), A base
40/60 core/3x with extension trim v2 (held votes, 1/6 core cut per vote, 3-session spell carry), 20/100 fast
overlay, D gate (breadth pct < 0.20 OR gap200 < 2%) -> cash, D ladder S.D_LADDER_ROWS (D1 50% core/50% 2x,
D2 50% 3x/50% 2x, D3 100% 3x) with the 0.5% zone buffer, max(10d,30d) vol target 20% (cap 1), 5% L1 drift
band + zero-leg stubs + regime-change triggers, 2bp per side (MC.COST), decide at close t / earn t+1.
Cash-leg QQQ legs, stacked as harness.weights: deep-E = 50% of the cash leg in the SIGNAL index (unlevered,
price return, as harness uses pn['qqq']) on effective-E sessions with gap200 <= -5%; VIX-panic = 25% of the
cash leg in the signal index while the VIX latch is on (>= 30 on, < 25 off), capped by what deep-E left.
VIXM sleeve: OFF everywhere (no VIXM data before 2011). The engine is monte_carlo.py's, unchanged.

INPUTS THAT DO NOT EXIST (inert, stated, not substituted):
  * Breadth half of the D gate: no EW series before 1999 (ndx_survivor_ew_daily.csv starts 1999-01-05) and none
    for non-US indices -> pct = NaN, gate = gap200 half only, on every set.
  * VIX-panic: VIX (CBOE via vol_curve.history('VIX'), else data/vixcls_full.csv) exists from 1990-01-02. ON
    for the US sets (a, c) from 1990, OFF before 1990 (so Oct 1987 has no panic leg). OFF for the non-US sets
    (b): VIX is a US S&P 500 measure and no local implied-vol index is in hand.
  * Deep-E needs only the signal index: on in every set.

TEST SETS. Signals always from the set's own price index (MC.signals); scoring starts at session 420 of the
series (MC.WARMUP; classifier converges <= 323) and ends at the last date given.
  a) NDX 1985-10-01 data, scored ~1987 .. 2000-12-29. Core = NDX + 0.6%/yr dividend accrual (MC.QQQ_DIV),
     3x/2x = 3u - 2fin - 0.84% / 2u - fin - 0.95%, fin = T-bill + 0.3% (load_panel proxy branch). Cash = 3m
     T-bill (dgs3mo_full, prior print). Benchmark buy-and-hold = core (NDX + 0.6%).
  b) Nikkei 225 (^N225), DAX (^GDAXI), FTSE 100 (^FTSE): Yahoo daily closes from their first date to the last
     close (2026-10-30), cached to data/untouched/<SYM>.csv (d,c). Core = index, no dividend added (both
     strategy and benchmark; DAX is a total-return index, N225/FTSE are price indices), synthetic 3x/2x as in
     (a) but financed at USD rates: 3m T-bill from 1981-09, Ken French daily RF before (annualised x252).
     LIMITATION: the financing rate is the US rate, not the local one (JPY rates near zero after 1995 make 3x
     Nikkei look costlier than it would have been; DEM/EUR and GBP rates were often above USD); no FX.
  c) Crude momentum-tilted core on US signals: signals = NDX as in (a), same window; core = Mkt (MktRF + RF)
     + 0.5 x UMD (Ken French daily) - CRUDE, a factor portfolio with no costs or financing for the long-short
     leg; 3x/2x legs = synthetic NDX as in (a); deep-E/VIX-panic legs = NDX. Benchmarks: buy-and-hold of the
     crude core, and of NDX + 0.6%.

VARIANTS on every set: CUR (the live design as above) and BARE = CUR with trim off ('none', A = flat 40/60),
D gate off, D ladder off (D = MC.LIVE row 100% 2x), fast overlay off, and the deep-E / VIX-panic legs off
(pure 50/200 classifier + vol target + band). Each with lag 0 and lag 1 (weights and regime key shifted one
session, as harness.run).

METRICS vs buy-and-hold: CAGR, Sharpe (mean/sd, x sqrt 252), excess-of-cash Sharpe, MaxDD, worst calendar
year (partial first/last years included and marked), % time in each effective state A-F over the scored
window (plus gated-D, deep-E-on and panic-on shares), rebalances/yr.

INTERPRETATION RULE (fixed now): "beats on risk-adjusted terms" = higher excess-of-cash Sharpe than buy-and-hold
at lag 0 AND lag 1. Compare the out-of-sample excess Sharpe to the in-sample real 2015-2026 excess Sharpe 1.96:
report the ratio and the edge over buy-and-hold. No parameter may change after the first run.

    python3 paper-track/review_2026_11/untouched_test.py | tee paper-track/review_2026_11/untouched_test_run.log
"""
import csv, datetime, json, os, sys, urllib.request
import numpy as np
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, HERE)
import monte_carlo as MC, state as S, vol_curve as VC

UNT = os.path.join(MC.DATA, 'untouched')
CUR = dict(MC.LIVE, name='11 Nov live', a_base=(0.40, 0.60), vol='max10_30', d_buffer=S.D_ZONE_BUFFER)
assert CUR['rows']['B'] == (0.50, 0, 0, 0, 0.50) and S.D_LADDER_ROWS['D3'] == (0.0, 1.0, 0.0)
BARE = dict(CUR, name='bare', trim='none', d_gate=False, d_ladder=False, fast=False)
END_A = '2000-12-29'


# ------------------------------------------------------------------ data
def yahoo(sym):
    os.makedirs(UNT, exist_ok=True)
    fn = os.path.join(UNT, sym.lstrip('^') + '.csv')
    if not os.path.exists(fn):
        u = (f"https://query2.finance.yahoo.com/v8/finance/chart/{sym.replace('^', '%5E')}"
             f"?period1=0&period2=1793404800&interval=1d")
        j = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=VC.UA), timeout=60).read())
        r = j['chart']['result'][0]; off = r['meta'].get('gmtoffset', 0) or 0
        out = {}
        for t, c in zip(r['timestamp'], r['indicators']['quote'][0]['close']):
            if c is not None and c > 0:
                out[datetime.datetime.utcfromtimestamp(t + off).date().isoformat()] = c
        with open(fn, 'w', newline='') as fh:
            w = csv.writer(fh); w.writerow(['d', 'c'])
            for d in sorted(out): w.writerow([d, f"{out[d]:.6f}"])
    return MC._load(os.path.join('untouched', os.path.basename(fn)))


def rates(dates):
    """Annual rate as of the prior available print: 3m T-bill from 1981-09-01, Ken French RF x252 before."""
    tb = MC._load('dgs3mo_full.csv', 'observation_date', 'DGS3MO')
    rf = {r['d']: float(r['RF']) * 252 * 100 for r in csv.DictReader(open(os.path.join(MC.DATA, 'ff_3factors_daily.csv')))}
    src = {d: v for d, v in rf.items() if d < min(tb)}; src.update(tb)
    sd = sorted(src); j = 0; last = 0.0; out = []
    for d in dates:
        while j < len(sd) and sd[j] <= d:
            last = src[sd[j]]; j += 1
        out.append(last / 100.0)
    return np.array(out)


def panel(px, div=0.0, core=None):
    dates = sorted(px)
    rate = rates(dates)
    yf = np.array([0.0] + [MC._yf(dates[i - 1], dates[i]) for i in range(1, len(dates))])
    rprev = np.concatenate([[rate[0]], rate[:-1]])
    rq = MC._rets(px, dates); u = rq + div * yf; fin = (rprev + MC.FIN_SPREAD) * yf
    p = dict(dates=dates, qqq=rq, cash=rprev * yf, core=u if core is None else core, bh_index=u,
             tqqq=3 * u - 2 * fin - MC.TQQQ_ER * yf, qld=2 * u - fin - MC.QLD_ER * yf, xlu=np.zeros(len(dates)))
    for k in p:
        if k != 'dates': p[k] = np.asarray(p[k], float); p[k][0] = 0.0
    return p


def sigs(p):
    q = 100 * np.cumprod(1 + p['qqq'])
    sg = MC.signals(q[None], q[None])
    sg['pct'][:] = np.nan; sg['gate_b'][:] = False; sg['gate'] = sg['gate_g'].copy()   # breadth inert
    return sg


def vix_hist():
    try:
        h, src = VC.history('VIX'); return h, src
    except Exception as e:  # noqa: BLE001
        return MC._load('vixcls_full.csv', 'observation_date', 'VIXCLS'), f'local vixcls_full.csv ({e})'


def panic_series(ds, vix):
    on = False; out = np.zeros(len(ds))
    for i, d in enumerate(ds):
        v = vix.get(d, np.nan) if vix else np.nan
        if not np.isnan(v):
            if on and v < S.VIX_PANIC_OFF: on = False
            elif not on and v >= S.VIX_PANIC_ON: on = True
        out[i] = S.VIX_PANIC_CASH_SHARE if on else 0.0
    return out


# ------------------------------------------------------------------ design (harness.weights, VIXM off)
def weights(sg, p, cfg, qlegs, vix):
    w5 = MC.target_weights(sg, cfg)
    assert np.all(w5[0, :, 3] == 0)
    key = MC.regime_key(sg, cfg).astype(np.int64)[0]
    cash = w5[0, :, 4].copy()
    legs = [p['core'], p['tqqq'], p['qld'], p['xlu']]; W = [w5[0, :, i] for i in range(4)]
    used = np.zeros_like(cash); on = {}
    if qlegs:
        e = MC._eff(sg, cfg)[0]; g = np.nan_to_num(sg['gaps'][200][0])
        deep = ((e == 4) & (g <= S.DEEP_E_GAP200)).astype(float) * S.DEEP_E_CASH_SHARE
        pan = panic_series(p['dates'], vix)
        for j, sh in enumerate((deep, pan)):
            x = np.minimum(cash * sh, cash - used); used = used + x
            legs.append(p['qqq']); W.append(x); key = key + (sh > 0).astype(np.int64) * (10 ** (6 + j))
        on = dict(deepE=deep > 0, panic=pan > 0)
    legs.append(p['cash']); W.append(cash - used)
    return np.stack(W, -1), np.stack(legs, -1), key, on


def run(sg, p, cfg, qlegs, vix, s0, e, lag=0):
    W, L, key, on = weights(sg, p, cfg, qlegs, vix)
    if lag:
        W = np.concatenate([np.repeat(W[:1], lag, 0), W[:-lag]], 0)
        key = np.concatenate([np.repeat(key[:1], lag), key[:-lag]])
    r, tr = MC.run_strategy(W[None, :e + 1], key[None, :e + 1], L[None, :e + 1], s0)
    return r[0], tr[0] / ((e - s0) / 252), on


def stats(r, cash, ds):
    nav = np.cumprod(1 + r); dd = nav / np.maximum.accumulate(np.concatenate([[1.0], nav]))[1:] - 1
    sd = r.std(ddof=1)
    yr = {}
    for d, x in zip(ds, r): yr.setdefault(d[:4], []).append(x)
    ann = {y: np.prod(1 + np.array(v)) - 1 for y, v in yr.items()}
    wy = min(ann, key=ann.get)
    part = wy in (ds[0][:4], ds[-1][:4])
    return dict(c=nav[-1] ** (252 / len(r)) - 1, sh=r.mean() / sd * 252 ** 0.5, ex=(r - cash).mean() / sd * 252 ** 0.5,
                m=dd.min(), wy=f"{wy}{'*' if part else ''} {ann[wy]*100:+.1f}%", v=sd * 252 ** 0.5)


def row(lab, x, tpy=None):
    return (f"  {lab:<28}{x['c']*100:7.1f}%{x['sh']:8.3f}{x['ex']:8.3f}{x['m']*100:8.1f}%{x['v']*100:7.1f}%  "
            f"{x['wy']:<16}" + (f"{tpy:6.0f}" if tpy is not None else ''))


def test_set(name, p, benches, vix, end, note):
    ds = p['dates']; s0 = MC.WARMUP; e = max(i for i, d in enumerate(ds) if d <= end)
    sd = ds[s0 + 1:e + 1]; cash = p['cash'][s0 + 1:e + 1]
    print(f"\n=== {name}: scored {ds[s0]} -> {ds[e]} ({e - s0} sessions; data from {ds[0]}) ===")
    print(f"  {note}")
    big = np.argsort(-np.abs(p['qqq'][1:e + 1]))[:3] + 1
    print("  largest |daily| signal-index moves (data sanity): " + ", ".join(f"{ds[i]} {p['qqq'][i]*100:+.1f}%" for i in big))
    print(f"  {'':<28}{'CAGR':>8}{'Sharpe':>8}{'exSh':>8}{'MaxDD':>9}{'vol':>8}  {'worst year':<16}{'reb/yr':>6}")
    for lab, br in benches:
        print(row(f"buy&hold {lab}", stats(br[s0 + 1:e + 1], cash, sd)))
    sg = sigs(p); res = {}
    for cfg, ql in ((CUR, True), (BARE, False)):
        for lag in (0, 1):
            r, tpy, on = run(sg, p, cfg, ql, vix, s0, e, lag)
            x = stats(r, cash, sd); res[(cfg['name'], lag)] = x
            print(row(f"{cfg['name']} lag {lag}", x, tpy))
        eff = MC._eff(sg, cfg)[0][s0:e]
        st = ", ".join(f"{MC.LETTERS[i]} {np.mean(eff == i)*100:.0f}%" for i in range(6))
        extra = ''
        if cfg['d_gate']:
            extra += f"; D gated {np.mean(MC._gate(sg, cfg)[0][s0:e])*100:.1f}% of days"
        for k, m in on.items():
            extra += f"; {k} on {np.mean(m[s0:e])*100:.1f}%"
        print(f"    {cfg['name']} time in effective state: {st}{extra}")
    return res


def main():
    vix, vsrc = vix_hist()
    print(f"Untouched-data test, run {datetime.date.today()}. VIX source: {vsrc}, first {min(vix)}. VIXM off. "
          f"Breadth half of D gate inert. Cost {MC.COST*1e4:.0f}bp/side.")
    print("Columns: CAGR, Sharpe = mean/sd, exSh = excess-of-cash Sharpe, MaxDD, vol, worst calendar year (* partial), rebalances/yr.")
    ndx = MC._load('NDX_index_daily.csv')
    pa = panel(ndx, div=MC.QQQ_DIV)
    out = {}
    out['a'] = test_set('(a) NASDAQ-100', pa, [('NDX+0.6%', pa['bh_index'])], vix, END_A,
                        'core = NDX + 0.6%/yr; synthetic 3x/2x; VIX-panic on from 1990-01-02; breadth inert.')
    # (c) crude momentum core on NDX signals
    mk = {r['d']: float(r['MktRF']) + float(r['RF']) for r in csv.DictReader(open(os.path.join(MC.DATA, 'ff_3factors_daily.csv')))}
    um = {r['d']: float(r['MOM']) for r in csv.DictReader(open(os.path.join(MC.DATA, 'ff_momentum_daily.csv')))}
    miss = [d for d in pa['dates'][1:] if d <= END_A and (d not in mk or d not in um)]
    core = np.array([mk.get(d, 0.0) + 0.5 * um.get(d, 0.0) for d in pa['dates']]); core[0] = 0.0
    pc = dict(pa, core=core)
    out['c'] = test_set('(c) CRUDE momentum core (Mkt + 0.5 UMD) on NDX signals', pc,
                        [('Mkt+0.5UMD', core), ('NDX+0.6%', pa['bh_index'])], vix, END_A,
                        f'CRUDE factor core, no costs on the UMD leg; 3x/2x and QQQ legs = NDX; {len(miss)} NDX dates without FF data set to 0.')
    for sym, lab in (('^N225', 'Nikkei 225'), ('^GDAXI', 'DAX (total-return index)'), ('^FTSE', 'FTSE 100')):
        try:
            px = yahoo(sym)
        except Exception as ex:  # noqa: BLE001
            print(f"\n=== (b) {lab}: data unavailable ({ex}) ==="); continue
        pb = panel(px)
        out[sym] = test_set(f'(b) {lab}', pb, [(sym, pb['bh_index'])], None, '2099',
                            'own signals, core = index (no dividend added), synthetic 3x/2x financed at USD T-bill+0.3% '
                            '(KF RF before 1981-09); VIX-panic off; breadth inert.')
    print("\nIn-sample reference: real 2015-2026 excess Sharpe 1.96.")
    print(f"  {'set':<10}{'CUR exSh lag0':>15}{'lag1':>8}{'BARE lag0':>11}{'lag1':>8}{'CUR/1.96':>10}")
    for k, v in out.items():
        a0, a1 = v[('11 Nov live', 0)]['ex'], v[('11 Nov live', 1)]['ex']
        print(f"  {k:<10}{a0:15.3f}{a1:8.3f}{v[('bare', 0)]['ex']:11.3f}{v[('bare', 1)]['ex']:8.3f}{a0/1.96:10.2f}")


if __name__ == '__main__':
    main()
