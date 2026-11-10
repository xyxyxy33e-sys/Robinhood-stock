exec(open('/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad/hv/hv_test.py').read().split("log('='*130)")[0].replace("hv_test.log", "bars1110.log"))
_px = {r['d']: float(r['c']) for r in csv.DictReader(open(os.path.join(MC.DATA, 'vixm_daily.csv')))}
vixm_r = MC._rets(_px, rd); vixm_r[0] = 0.0
e = MC._eff(sr, LIVE)[0]; g = np.nan_to_num(sr['gaps'][200][0])
deep = ((e == 4) & (g <= -0.05)).astype(float) * 0.5
on = False; pan = np.zeros(len(rd))
for i in range(len(rd)):
    v = VIX[i]
    if not np.isnan(v):
        if on and v < 25: on = False
        elif not on and v >= 30: on = True
    pan[i] = 0.25 if on else 0.0
def yearly(r, ds):
    y = {}
    for d, x in zip(ds, r): y.setdefault(d[:4], []).append(x)
    return {k: np.prod(1+np.array(v))-1 for k, v in y.items()}
for lab, ex in (('before (6 legs)', []), ('11 Nov design', [(pr['qqq'], deep), (pr['qqq'], pan)])):
    r, t, ds = runner(sr, pr, '2015-11-02', ex); c, s, m = prof(r); y = yearly(r, ds)
    log(f"{lab}: {c*100:.1f}% / {s:.3f} / {m*100:.1f}%  through {ds[-1]};  " + '  '.join(f"{k} {v*100:+.1f}%" for k, v in sorted(y.items()) if k >= '2022'))
