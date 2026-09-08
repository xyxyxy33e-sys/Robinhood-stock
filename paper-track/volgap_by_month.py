"""Month-by-month for selected years: live vs the VXN-VIX gap tilt (delta 0.20,
causal). Same harness as volgap_by_year.py. Also shows the tilt's sign each
month (share of A/B sessions tilted toward TQQQ) so the P&L can be read
against what the rule was doing."""
import sys, math
sys.path.insert(0, 'paper-track')
src = open('paper-track/volgap_causal2.py').read().split("for gk, tk, lab in")[0]
exec(src)
YEARS = ('2020', '2024', '2026')
gk, tk = 'gI', 'tI'
P  = [r for r in srows if r.get(gk) is not None and r.get(tk) is not None]
Pr = [r for r in rr    if r.get(gk) is not None and r.get(tk) is not None]
def rf_rets(rl, fn):
    prev = None; out = []
    for r in rl:
        w = fn(r); c = 0.0004*sum(abs(w[i]-(prev[i] if prev else 0)) for i in range(5))
        out.append(sum(w[i]*r['legs'][i] for i in range(5)) - c); prev = w
    return out
def bymonth(rl, rets, key):
    by = {}
    for r, x in zip(rl, rets): by[r[key][:7]] = by.get(r[key][:7], 0.0) + math.log1p(x)
    return {m: math.expm1(v) for m, v in by.items()}
pl = bymonth(P, run(P, live_fn())[0], 'd'); pc = bymonth(P, run(P, tilt(0.20, gk, tk))[0], 'd')
rl_ = bymonth(Pr, rf_rets(Pr, live_fn(RF.vt)), 'd0'); rc = bymonth(Pr, rf_rets(Pr, tilt(0.20, gk, tk, 1, RF.vt)), 'd0')
lean = {}
for r in P:
    if r['eff'] in ('A', 'B'):
        m = r['d'][:7]; lean.setdefault(m, [0, 0]); lean[m][0] += r[gk] > r[tk]; lean[m][1] += 1
for y in YEARS:
    print(f"\n{y}   {'month':<8}{'proxy LIVE':>11}{'proxy TILT':>11}{'diff':>7}  {'lean':>14}   {'real LIVE':>10}{'real TILT':>10}{'diff':>7}")
    tl = tc = trl = trc = 0.0
    for mo in range(1, 13):
        m = f"{y}-{mo:02d}"
        if m not in pl: continue
        tl += math.log1p(pl[m]); tc += math.log1p(pc[m])
        a, n = lean.get(m, (0, 0))
        # gap > trailing median => rule moves delta from TQQQ to CORE (see tilt()).
        ln = f"{'core' if a >= n/2 else 'TQQQ'} {100*a/n:3.0f}%core" if n else "not A/B"
        rs = ""
        if m in rl_:
            trl += math.log1p(rl_[m]); trc += math.log1p(rc[m])
            rs = f"{rl_[m]*100:+9.1f}%{rc[m]*100:+9.1f}%{(rc[m]-rl_[m])*100:+6.1f}"
        print(f"       {m:<8}{pl[m]*100:+10.1f}%{pc[m]*100:+10.1f}%{(pc[m]-pl[m])*100:+6.1f}  {ln:>14}   {rs}")
    rs = f"{math.expm1(trl)*100:+9.1f}%{math.expm1(trc)*100:+9.1f}%{(math.expm1(trc)-math.expm1(trl))*100:+6.1f}" if trl else ""
    print(f"       {'YEAR':<8}{math.expm1(tl)*100:+10.1f}%{math.expm1(tc)*100:+10.1f}%{(math.expm1(tc)-math.expm1(tl))*100:+6.1f}  {'':>14}   {rs}")
