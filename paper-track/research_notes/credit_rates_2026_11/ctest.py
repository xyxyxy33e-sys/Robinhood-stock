"""Credit / rates test. PRE-REGISTERED before the first run (2026-11-19), not tuned afterwards:
Inputs, each read with a ONE-SESSION LAG (value of the prior session; FRED posts after the close):
  CREDIT = Moody's Baa - 10y Treasury (FRED BAA10Y) above its own 100-session average   ("credit widening")
  HYIEF  = HYG/IEF price ratio below its own 100-session average (2007+, real era only)  ("junk underperforming")
  RATES  = 10y Treasury yield (FRED DGS10) up 0.50pp or more over 60 sessions            ("rates shock")
Uses, each alone: A risk halved; D to cash; deep-E QQQ buy skipped. Plus the inverse check for CREDIT
(act when NOT widening). Scored on real 2015-26, proxy 2001-26, holdout 2001-Oct 2015 and untouched NDX 1987-2000.
Adopt only if better on Sharpe in all four with no worse max drawdown."""
import sys, csv, json, datetime as dt, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/vol'); sys.path.insert(1, '/home/user/Robinhood-stock/paper-track')
import numpy as np, harness as H, untouched_test as U
from harness import MC, S
_n = len(H.sr['vol'][0]); _N0 = len(H.pr['dates'])
for _k, _v in list(H.pr.items()):
    if hasattr(_v, '__len__') and len(_v) == _N0 and _N0 != _n: H.pr[_k] = _v[:_n]
H.RD = H.pr['dates']
DL = '/tmp/claude-0/-home-user-Robinhood-stock/e898e69c-6aab-5817-bca0-552f786d2da8/scratchpad/credit/dl/'
def fred(s):
    out = {}
    for r in csv.reader(open(DL + s + '.csv')):
        try: out[r[0]] = float(r[1])
        except (ValueError, IndexError): pass
    return out
def yh(s):
    d = json.load(open(DL + s + '.json'))['chart']['result'][0]
    adj = d['indicators'].get('adjclose', [{}])[0].get('adjclose') or d['indicators']['quote'][0]['close']
    return {dt.datetime.utcfromtimestamp(t).date().isoformat(): v for t, v in zip(d['timestamp'], adj) if v}
BAA, T10, HYG, IEF = fred('BAA10Y'), fred('DGS10'), yh('HYG'), yh('IEF')
def series(src, dates):                     # last known value up to the PRIOR session (1-session lag)
    keys = sorted(src); out = np.full(len(dates), np.nan); j = 0; last = np.nan
    for i, d in enumerate(dates):
        while j < len(keys) and keys[j] < d: last = src[keys[j]]; j += 1
        out[i] = last
    return out
def sma(x, n):
    o = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        if not np.isnan(w).any(): o[i] = w.mean()
    return o
def flags(dates):
    b = series(BAA, dates); t = series(T10, dates)
    hy = series(HYG, dates) / series(IEF, dates)
    f = {'CREDIT widening': b > sma(b, 100),
         'HYG/IEF below 100d': hy < sma(hy, 100),
         'RATES +0.5pp/60d': np.r_[np.full(60, False), (t[60:] - t[:-60]) >= 0.5]}
    f['credit NOT widening'] = ~f['CREDIT widening'] & ~np.isnan(sma(b, 100))
    return {k: np.nan_to_num(v.astype(float)).astype(bool) for k, v in f.items()}
NEW = dict(H.CUR, gross_cap=S.GROSS_CAP)
def hook(rule, fl):
    def h(w5, sg):
        w = w5.copy(); e = MC._eff(sg, NEW)[0]; m0 = fl[:w.shape[1]]
        if rule == 'A_half': m = (e == 0) & m0; k = 0.5
        else: m = (e == 3) & m0; k = 0.0
        r = w[0, m, :4].copy(); w[0, m, :4] = r * k; w[0, m, 4] += r.sum(1) * (1 - k); return w
    return h
def weights_any(sg, ds, p, rule, fl, real=None, vix=None, ql=True):
    cfg = NEW
    if rule in ('A_half', 'D_cash'): cfgh = hook(rule, fl)
    else: cfgh = None
    if real is not None:
        W, L, key = H.weights(sg, ds, real, cfg=cfg, vixm=False, w5_hook=cfgh)
    else:
        orig = MC.target_weights
        if cfgh: MC.target_weights = lambda s, c: cfgh(orig(s, c), s)
        try: W, L, key, _ = U.weights(sg, p, cfg, ql, vix)
        finally: MC.target_weights = orig
    if rule == 'deepE_skip' and ql:
        m = fl[:len(W)]; W = W.copy(); W[m, -1] += W[m, 4]; W[m, 4] = 0
    return W, L, key
def st(r):
    nav = np.cumprod(1+r); dd = (nav/np.maximum.accumulate(nav)-1).min(); v = r.std(ddof=1)*252**.5
    return f"{(nav[-1]**(252/len(r))-1)*100:5.1f}% {r.mean()*252/v:5.2f} {dd*100:6.1f}%"
def run_in(real, rule, fl, d1='2099'):
    pn = H.pr if real else H.p; ds = pn['dates']; sg = H.sr if real else H.sig
    W, L, key = weights_any(sg, ds, pn, rule, fl, real=real)
    s0 = next(i for i, x in enumerate(ds) if x >= ('2015-11-02' if real else '2001-01-02')); e = max(i for i, x in enumerate(ds) if x <= d1)
    return MC.run_strategy(W[None, :e+1], key[None, :e+1], L[None, :e+1], s0)[0][0]
vix, _ = U.vix_hist(); pa = U.panel(MC._load('NDX_index_daily.csv'), div=MC.QQQ_DIV); sga = U.sigs(pa)
def run_ndx(rule, fl):
    ds = pa['dates']; s0 = MC.WARMUP; e = max(i for i, d in enumerate(ds) if d <= U.END_A)
    W, L, key = weights_any(sga, ds, pa, rule, fl, vix=vix)
    r = MC.run_strategy(W[None, :e+1], key[None, :e+1], L[None, :e+1], s0)[0][0]
    x = U.stats(r, pa['cash'][s0+1:e+1], ds[s0+1:e+1]); return f"{x['c']*100:5.1f}% ex{x['ex']:5.2f} {x['m']*100:6.1f}%"
FR, FP, FN = flags(H.pr['dates']), flags(H.p['dates']), flags(pa['dates'])
print('share of days on (proxy 2001-26):', {k: round(float(v[H.p['dates'].index('2001-01-02'):].mean())*100) for k, v in FP.items()})
print(f"{'variant':36s} | real 2015-26         | proxy 2001-26        | holdout 2001-Oct15   | NDX 1987-2000 (untouched)")
z = np.zeros(len(H.p['dates']), bool)
print(f"{'current':36s} | {st(run_in(True, None, FR['CREDIT widening']))} | {st(run_in(False, None, z))} | {st(run_in(False, None, z, '2015-10-30'))} | {run_ndx(None, FN['CREDIT widening'])}")
for name in ('CREDIT widening', 'HYG/IEF below 100d', 'RATES +0.5pp/60d', 'credit NOT widening'):
    for rule in ('A_half', 'D_cash', 'deepE_skip'):
        lab = f"{rule} when {name}"
        nd = run_ndx(rule, FN[name]) if name != 'HYG/IEF below 100d' else 'n/a (no HYG)'
        pr_ = st(run_in(False, rule, FP[name])) if name != 'HYG/IEF below 100d' else 'n/a (HYG from 2007)  '
        ho = st(run_in(False, rule, FP[name], '2015-10-30')) if name != 'HYG/IEF below 100d' else 'n/a                  '
        print(f"{lab:36s} | {st(run_in(True, rule, FR[name]))} | {pr_} | {ho} | {nd}")
i = len(H.pr['dates']) - 1
b = series(BAA, H.pr['dates']); t = series(T10, H.pr['dates'])
print(f"latest {H.pr['dates'][i]}: BAA10Y {b[i]:.2f} vs 100d {sma(b,100)[i]:.2f}; 10y {t[i]:.2f} (60 sessions ago {t[i-60]:.2f}); flags {[k for k,v in FR.items() if v[i]]}")
