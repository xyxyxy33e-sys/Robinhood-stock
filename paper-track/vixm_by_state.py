"""Owner (2026-10-22): "Break down the VIXM sleeve by state." Research only.

Live design as re-baselined on 2026-10-22 (rebaseline_2026_10_22.py), real ETFs
2015-11..2026-08. Each day's VIXM contribution = return with the sleeve minus the same
design without it, credited to the state that set that day's position (decision at the
close, return earned to the next close). Also: VIXM spells (consecutive sessions with a
VIXM target) by the state they started in, with their result vs BOXX.
"""
import csv, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import monte_carlo as MC, state as S, vol_curve as VC

LIVE = dict(MC.LIVE, a_base=(0.40, 0.60), vol='max10_30')
LOG = open(os.path.join(HERE, 'research_notes', 'vixm_by_state_run.log'), 'w')
def log(*a):
    s = ' '.join(str(x) for x in a); print(s); LOG.write(s + '\n'); LOG.flush()

p = MC.load_panel('proxy'); dates = p['dates']
sig = MC.signals((100 * np.cumprod(1 + p['qqq']))[None], (100 * np.cumprod(1 + p['ew']))[None])
pr = MC.load_panel('real'); off = dates.index(pr['dates'][0])
sr = {k: (v[:, off:] if not isinstance(v, dict) else {n: a[:, off:] for n, a in v.items()}) for k, v in sig.items()}
rd = pr['dates']
vix, _ = VC.history('VIX'); vix3m, _ = VC.history('VIX3M')
VX = S.vixm_series(rd, vix, vix3m, {d: (None if np.isnan(v) else float(v)) for d, v in zip(rd, sr['vol'][0])})
allowed = np.array([bool(VX.get(d, {}).get('allowed')) for d in rd])
vm = {r['d']: float(r['c']) for r in csv.DictReader(open(os.path.join(MC.DATA, 'vixm_daily.csv')))}
vr = MC._rets(vm, rd); vr[0] = 0.0

w5 = MC.target_weights(sr, LIVE); key = MC.regime_key(sr, LIVE)
L5 = np.stack([pr['core'], pr['tqqq'], pr['qld'], pr['xlu'], pr['cash']], -1)[None]
v = np.where(allowed, w5[0, :, 4] * S.VIXM_CASH_SHARE, 0.0)
w6 = np.concatenate([w5[..., :4], v[None, :, None], (w5[0, :, 4] - v)[None, :, None]], -1)
L6 = np.stack([pr['core'], pr['tqqq'], pr['qld'], pr['xlu'], vr, pr['cash']], -1)[None]
s0 = next(i for i, d in enumerate(rd) if d >= '2015-11-02')
r6 = MC.run_strategy(w6, key + allowed[None].astype(int) * 100000, L6, s0)[0][0]
r5 = MC.run_strategy(w5, key, L5, s0)[0][0]
diff = r6 - r5; days = rd[s0 + 1:]

eff = MC._eff(sr, LIVE)[0]
def lab(i):
    e = 'ABCDEF'[eff[i]]
    if e == 'D':
        return 'D gated (cash)' if sr['gate'][0, i] else f"D{sr['zone'][0, i]}"
    if e == 'A':
        return 'A trimmed' if sr['held'][0, i] > 0 else 'A'
    return e
labs = [lab(s0 + j) for j in range(len(diff))]
vw = v[s0:s0 + len(diff)]                                   # VIXM target weight at each decision
cash = w5[0, s0:s0 + len(diff), 4]

log('=' * 130); log(f"VIXM sleeve by state -- live design 2026-10-22, real ETFs {days[0]}..{days[-1]}"); log('=' * 130)
tot = np.sum(np.log1p(r6)) - np.sum(np.log1p(r5))
log(f"  total: with VIXM {np.prod(1+r6)**(252/len(r6))*100-100:.1f}% CAGR vs without {np.prod(1+r5)**(252/len(r5))*100-100:.1f}%; "
    f"cumulative log gain {tot*100:+.1f} pts")
order = ['A', 'A trimmed', 'B', 'C', 'D1', 'D2', 'D3', 'D gated (cash)', 'E', 'F']
log(f"\n  {'state':<16}{'days':>6}{'VIXM days':>10}{'avg cash leg':>13}{'avg VIXM wt':>12}{'contribution':>13}{'share':>7}{'win days':>9}")
for k in order:
    m = np.array([x == k for x in labs])
    if not m.any(): continue
    on = m & (vw > 0)
    c = np.sum(np.log1p(r6[m])) - np.sum(np.log1p(r5[m]))
    win = f"{np.mean(diff[on] > 0)*100:.0f}%" if on.any() else '-'
    log(f"  {k:<16}{m.sum():6d}{on.sum():10d}{cash[m].mean()*100:12.0f}%{(vw[on].mean()*100 if on.any() else 0):11.0f}%"
        f"{(np.expm1(c))*100:+12.1f}%{(c/tot*100 if tot else 0):6.0f}%{win:>9}")

# spells
log(f"\n  VIXM spells (consecutive sessions with a VIXM target), by the state they started in")
sp = []; j = 0
while j < len(vw):
    if vw[j] > 0:
        k = j
        while k < len(vw) and vw[k] > 0: k += 1
        g = np.sum(np.log1p(r6[j:k])) - np.sum(np.log1p(r5[j:k]))
        sp.append((days[j], k - j, labs[j], sorted(set(labs[j:k]), key=order.index), np.expm1(g))); j = k
    else: j += 1
by = {}
for d, n, st, sts, g in sp: by.setdefault(st, []).append(g)
log(f"  {'started in':<16}{'spells':>7}{'won':>5}{'median':>9}{'total':>9}")
for k in order:
    if k in by:
        g = by[k]; log(f"  {k:<16}{len(g):7d}{sum(x > 0 for x in g):5d}{np.median(g)*100:+8.2f}%{(np.prod(1+np.array(g))-1)*100:+8.1f}%")
log(f"\n  all {len(sp)} spells (start, sessions, states held, gain vs no VIXM):")
for d, n, st, sts, g in sp:
    log(f"    {d}  {n:3d}  {'/'.join(sts):<28} {g*100:+6.2f}%")
big = sorted(sp, key=lambda x: -x[4])[:3]
ex = tot - sum(np.log1p(x[4]) for x in big[:1])
log(f"\n  without the single best spell ({big[0][0]}, {big[0][4]*100:+.1f}%): cumulative gain {np.expm1(ex)*100:+.1f}% "
    f"(~{np.expm1(ex/(len(diff)/252))*100:+.2f}%/yr) vs {np.expm1(tot)*100:+.1f}% (~{np.expm1(tot/(len(diff)/252))*100:+.2f}%/yr)")
