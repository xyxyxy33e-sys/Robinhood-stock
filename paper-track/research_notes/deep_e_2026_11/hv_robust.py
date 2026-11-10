exec(open('/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad/hv/hv_test.py').read().split("log('='*130)")[0].replace("hv_test.log", "hv_robust.log"))
rng = np.random.default_rng(5)
def boot(r, rb, n=3000, B=20):
    N = len(r); c = 0
    for _ in range(n):
        idx = np.concatenate([np.arange(s, s+B) for s in rng.integers(0, N-B, N//B+1)])[:N]
        a, b = r[idx], rb[idx]; c += (a.mean()/a.std() - b.mean()/b.std()) <= 0
    return c/n
def yearly(r, ds):
    y = {}
    for d, x in zip(ds, r): y.setdefault(d[:4], []).append(x)
    return {k: np.prod(1+np.array(v))-1 for k, v in y.items()}
short_vol = np.maximum(-vixy_r - INV_FEE, -0.99)
rb, _, ds = runner(sr, pr, '2015-11-02', [])
log('='*120); log('ROBUSTNESS: #1 short vol and #4 deep-E (real 2015-11.. unless stated)'); log('='*120)
log(f"  {'variant':<52}{'CAGR':>7}{'vs base':>8}{'Sharpe':>7}{'maxDD':>8}{'P(not better)':>14}{'worst day':>10}")
def show(lab, ex, sg=sr, pn=pr, d0='2015-11-02', base=rb):
    r, t, _ = runner(sg, pn, d0, ex); c, s, m = prof(r); cb = prof(base)[0]
    log(f"  {lab:<52}{c*100:6.1f}%{(c-cb)*100:+8.2f}{s:7.3f}{m*100:7.1f}%{boot(r, base):14.2f}{r.min()*100:9.1f}%")
    return r
for lo in (16, 18, 20, 22, 25, 30):
    for sh in (0.10, 0.25):
        on = (RATIO < 1.0) & (VIX >= lo) & ~allowed
        r = show(f"#1 short vol {sh*100:.0f}% when VIX>={lo} & VIX<VIX3M", [(short_vol, on*sh)])
on = (RATIO < 1.0) & (VIX >= 25) & ~allowed
r1 = show("#1 short vol 25% VIX>=25 (again, for years)", [(short_vol, on*0.25)])
y1, yb = yearly(r1, ds), yearly(rb, ds)
log("  years, #1 25% VIX>=25 minus base (pts): " + '  '.join(f"{k} {(y1[k]-yb[k])*100:+.1f}" for k in sorted(yb)))
# largest short-vol days while ON
idx = np.argsort(short_vol)[:8]
log("  8 worst short-vol days and whether #1 (VIX>=25) / (VIX>=18) was on the previous close: " +
    ', '.join(f"{rd[i]} {short_vol[i]*100:+.0f}% {'ON' if (i>0 and on[i-1]) else 'off'}/{'ON' if (i>0 and ((RATIO[i-1]<1)&(VIX[i-1]>=18)&~allowed[i-1])) else 'off'}" for i in idx))
log("")
e_r = MC._eff(sr, LIVE)[0]; E = e_r == 4; g200 = np.nan_to_num(sr['gaps'][200][0])
for th in (0.0, -0.02, -0.03, -0.05, -0.07, -0.10):
    for sh in (0.25, 0.50, 1.00):
        show(f"#4 QQQ {sh*100:.0f}% of cash in E when 200d gap <= {th*100:.0f}%", [(pr['qqq'], (E & (g200 <= th))*sh)])
rp, _, dsp = runner(sig, p, '2001-01-02', [])
eP = MC._eff(sig, LIVE)[0] == 4; gP = np.nan_to_num(sig['gaps'][200][0])
log("  PROXY 2001..:")
for th in (-0.03, -0.05, -0.07, -0.10):
    show(f"#4 PROXY QQQ 50% of cash in E when 200d gap <= {th*100:.0f}%", [(p['qqq'], (eP & (gP <= th))*0.5)], sig, p, '2001-01-02', rp)
r4, _, _ = runner(sr, pr, '2015-11-02', [(pr['qqq'], (E & (g200 <= -0.05))*0.5)])
y4 = yearly(r4, ds)
log("  years, #4 deep-E 50% minus base (pts): " + '  '.join(f"{k} {(y4[k]-yb[k])*100:+.1f}" for k in sorted(yb)))
r4p, _, dsp2 = runner(sig, p, '2001-01-02', [(p['qqq'], (eP & (gP <= -0.05))*0.5)])
y4p, ybp = yearly(r4p, dsp2), yearly(rp, dsp2)
log("  years PROXY, #4 deep-E 50% minus base (pts): " + '  '.join(f"{k} {(y4p[k]-ybp[k])*100:+.1f}" for k in sorted(ybp) if abs(y4p[k]-ybp[k])>0.0005))
log(f"  deep-E (gap<=-5%) share of sessions: real {(E&(g200<=-0.05))[1:].mean()*100:.1f}%, proxy {(eP&(gP<=-0.05))[1:].mean()*100:.1f}%")
