"""Year-by-year: live vs the VXN-VIX gap tilt (delta 0.20, causal trailing
median), the one open candidate from 2026-09-08. Reuses volgap_causal2's
harness; adds nothing new. Proxy = SPY-core 2003+; real = SPMO weekly rows."""
import sys, math
sys.path.insert(0, 'paper-track')
src = open('paper-track/volgap_causal2.py').read().split("for gk, tk, lab in")[0]
exec(src)
gk, tk = 'gI', 'tI'
P  = [r for r in srows if r.get(gk) is not None and r.get(tk) is not None]
Pr = [r for r in rr    if r.get(gk) is not None and r.get(tk) is not None]
live = live_fn(); cand = tilt(0.20, gk, tk)
def byyear(rl, fn, key):
    rets, _ = run(rl, fn) if key == 'd' else (RF_rets(rl, fn), None)
    by = {}
    for r, x in zip(rl, rets): by[r[key][:4]] = by.get(r[key][:4], 0.0) + math.log1p(x)
    return {y: math.expm1(v) for y, v in by.items()}
def RF_rets(rl, fn):
    prev = None; out = []
    for r in rl:
        w = fn(r); cost = 0.0004 * sum(abs(w[i] - (prev[i] if prev else 0)) for i in range(5))
        out.append(sum(w[i]*r['legs'][i] for i in range(5)) - cost); prev = w
    return out
def qqq_by_year(rl, key):
    by = {}
    for r in rl: by[r[key][:4]] = by.get(r[key][:4], 0.0) + math.log1p(r['legs'][1]/3.0 if key=='d' else r['bench_qqq'])
    return {y: math.expm1(v) for y, v in by.items()}
pl, pc = byyear(P, live, 'd'), byyear(P, cand, 'd')
rl_, rc = byyear(Pr, live_fn(RF.vt), 'd0'), byyear(Pr, tilt(0.20, gk, tk, 1, RF.vt), 'd0')
print(f"{'year':<6}{'proxy LIVE':>12}{'proxy TILT':>12}{'diff':>8}   {'real LIVE':>11}{'real TILT':>11}{'diff':>8}")
wins = 0; n = 0
for y in sorted(pl):
    d = pc[y]-pl[y]; n += 1; wins += d > 0
    rs = f"{rl_[y]*100:+10.1f}%{rc[y]*100:+10.1f}%{(rc[y]-rl_[y])*100:+7.1f}" if y in rl_ else ""
    print(f"{y:<6}{pl[y]*100:+11.1f}%{pc[y]*100:+11.1f}%{d*100:+7.1f}   {rs}")
print(f"\nproxy: tilt beats live in {wins} of {n} years")
rw = sum(1 for y in rl_ if rc[y] > rl_[y]); print(f"real:  tilt beats live in {rw} of {len(rl_)} years")
