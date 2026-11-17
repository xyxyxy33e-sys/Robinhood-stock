"""Builds the research page from days.csv. python3 page_gen.py <out.html>"""
import sys, numpy as np, pandas as pd
d = pd.read_csv('days.csv', index_col=0); d['abs'] = d.ret.abs()
up = d.sort_values('ret', ascending=False).head(100); dn = d.sort_values('ret').head(100)
E = [0, 13, 16, 20, 25, 30, 40, 200]; L = ['under 13', '13–16', '16–20', '20–25', '25–30', '30–40', '40+']
b = pd.cut(d.p_vix, E, labels=L, right=False); g = d.groupby(b, observed=True)
rows = []
for lab, z in g:
    rows.append((lab, len(z), len(z)/len(d)*100, z['abs'].mean()*100, (z.ret <= -.02).mean()*100, (z.ret >= .02).mean()*100, z.index.isin(dn.index).sum(), z.index.isin(up.index).sum()))
mx = max(r[4] + r[5] for r in rows)
def pct(x, n=2, sign=True):
    if pd.isna(x): return '<td class="na">n/a</td>'
    s = ('%+.*f%%' if sign else '%.*f%%') % (n, x*100)
    return '<td class="%s">%s</td>' % ('neg' if x < 0 and sign else 'pos' if sign else '', s.replace('-', '−'))
def num(x, n=1):
    return '<td class="na">n/a</td>' if pd.isna(x) else '<td>%.*f</td>' % (n, x)
def table(t, cls):
    out = ['<div class="scroll"><table class="days"><thead><tr><th>#</th><th class="l">Date</th><th>QQQ day</th><th>VIX day before</th><th>VIX change day before</th><th>VIX ÷ VIX3M</th><th>10-day realized vol</th><th>vs 200-day</th><th>State</th></tr></thead><tbody>']
    for i, (dt, r) in enumerate(t.iterrows(), 1):
        st = r.p_state if isinstance(r.p_state, str) else 'n/a'
        out.append('<tr><td>%d</td><td class="l">%s</td><td class="%s"><b>%s</b></td>%s%s%s%s%s<td><span class="st st-%s">%s</span></td></tr>' % (
            i, dt, cls, ('%+.2f%%' % (r.ret*100)).replace('-', '−'), num(r.p_vix), pct(r.p_vix_chg1, 1), num(r.p_ratio, 2), num(r.p_rv10, 0), pct(r.p_gap200, 1), st[0] if st != 'n/a' else 'x', st))
    out.append('</tbody></table></div>'); return '\n'.join(out)
bars = []
for lab, n, sh, ma, pd_, pu, tdn, tup in rows:
    bars.append('<div class="brow"><div class="blab">%s</div><div class="btrack"><span class="bdn" style="width:%.1f%%"></span><span class="bup" style="width:%.1f%%"></span></div><div class="bval">%.0f%% <small>(%.0f down + %.0f up)</small></div></div>' % (lab, pd_/mx*100*.98, pu/mx*100*.98, pd_+pu, pd_, pu))
brows = ''.join('<tr><td class="l">%s</td><td>%s</td><td>%.0f%%</td><td>%.2f%%</td><td>%.1f%%</td><td>%.1f%%</td><td>%d</td><td>%d</td></tr>' % (lab, format(n, ','), sh, ma, pd_, pu, tdn, tup) for lab, n, sh, ma, pd_, pu, tdn, tup in rows)
html = open('page_template.html').read()
html = html.replace('{{BARS}}', '\n'.join(bars)).replace('{{BROWS}}', brows).replace('{{DOWN}}', table(dn, 'neg')).replace('{{UP}}', table(up, 'pos'))
open(sys.argv[1], 'w').write(html); print('ok', len(html))
