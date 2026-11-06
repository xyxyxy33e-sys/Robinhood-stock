"""Build a constant-maturity ~5-month VX futures roll index (months 4-7, S&P VIX Mid-Term style) from CFE archive
settlements (hist_data/cfe/CFE_<m><yy>_VX.csv) and validate it vs real VIXM (hist_data/hist_vixm_2011_2015.csv + data_ext/vixm_daily.csv)."""
import csv, glob, os, datetime as dt
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(H, 'hist_data')
def pdate(s): m, d, y = s.split('/'); return f'{y}-{int(m):02d}-{int(d):02d}'
con = {}   # name -> {date: settle}
for f in sorted(glob.glob(os.path.join(D, 'cfe', 'CFE_*_VX.csv'))):
    nm = os.path.basename(f)[4:7]; s = {}
    for r in csv.DictReader(open(f)):
        st = float(r['Settle'])
        if st > 5: s[pdate(r['Trade Date'])] = st
    if s: con[nm] = s
exp = {k: max(v) for k, v in con.items()}
alld = sorted({d for v in con.values() for d in v})
order = sorted(con, key=lambda k: exp[k])
idx_d = []; idx_r = []; miss = 0; renorm = 0
for t in range(1, len(alld)):
    d0, d1 = alld[t-1], alld[t]
    alive = [k for k in order if exp[k] > d0]
    if len(alive) < 7: continue
    prev_exp = max([exp[k] for k in order if exp[k] <= d0] or ['0000'])
    if prev_exp == '0000': continue
    nxt = exp[alive[0]]
    N = sum(1 for d in alld if prev_exp < d <= nxt); j = sum(1 for d in alld if prev_exp < d <= d0)
    c = alive
    w = {c[3]: .25*(1 - j/N), c[4]: .25, c[5]: .25, c[6]: .25}
    if len(c) > 7: w[c[7]] = .25*j/N
    ex = [dt.date.fromisoformat(exp[k]) for k in c[:min(8, len(c))]]
    if any(not 20 <= (ex[i+1]-ex[i]).days <= 42 for i in range(len(ex)-1)): continue
    # drop contracts with no settle on either day (e.g. month 8 not yet listed), renormalise the rest to 1
    avail = {k: wk for k, wk in w.items() if wk > 0 and d0 in con[k] and d1 in con[k]}
    if len(avail) < 3: miss += 1; continue
    tot = sum(avail.values())
    if tot < 0.999: renorm += 1
    r = sum(wk/tot*(con[k][d1]/con[k][d0]-1) for k, wk in avail.items())
    idx_d.append(d1); idx_r.append(r)
print('contracts', len(con), 'days', len(idx_d), idx_d[0], idx_d[-1], 'skipped', miss, 'days with renormalised weights (month 8 unlisted/missing)', renorm)
with open(os.path.join(H, 'hist_midterm_proxy.csv'), 'w') as fo:
    fo.write('d,r\n'); [fo.write(f'{d},{r:.8f}\n') for d, r in zip(idx_d, idx_r)]
# validation vs VIXM
vm = {}
for fn in (os.path.join(D, 'hist_vixm_2011_2015.csv'), '/tmp/claude-0/-home-user-Robinhood-stock/75a33379-7559-5bc8-8c7c-77b1afcbcad0/scratchpad/data_ext/vixm_daily.csv'):
    for r in csv.DictReader(open(fn)): vm[r['d']] = float(r['c'])
vd = sorted(vm); vr = {vd[i]: vm[vd[i]]/vm[vd[i-1]]-1 for i in range(1, len(vd))}
px = dict(zip(idx_d, idx_r)); com = [d for d in idx_d if d in vr and dt.date.fromisoformat(d) > dt.date.fromisoformat(vd[0])]
a = np.array([px[d] for d in com]); b = np.array([vr[d] for d in com])
print('overlap', com[0], com[-1], len(com), 'daily-return corr %.3f' % np.corrcoef(a, b)[0, 1], 'beta(VIXM on proxy) %.3f' % (np.cov(a, b)[0, 1]/a.var()))
yrs = {}
for d, x, y in zip(com, a, b): yrs.setdefault(d[:4], []).append((x, y))
for y, v in sorted(yrs.items()):
    v = np.array(v); print(f'  {y}: n={len(v)} proxy {np.prod(1+v[:,0])-1:+.1%}  VIXM {np.prod(1+v[:,1])-1:+.1%}  corr {np.corrcoef(v[:,0], v[:,1])[0,1]:.3f}  gap(VIXM-proxy) {np.prod(1+v[:,1])-np.prod(1+v[:,0]):+.1%}')
print('total over overlap: proxy %+.1f%%  VIXM %+.1f%%  ; ann. drift gap (VIXM-proxy, log) %.2f%%/yr' % ((np.prod(1+a)-1)*100, (np.prod(1+b)-1)*100, (np.log1p(b).sum()-np.log1p(a).sum())/(len(a)/252)*100))
print('daily vol ann: proxy %.1f%% VIXM %.1f%%' % (a.std()*252**.5*100, b.std()*252**.5*100))
