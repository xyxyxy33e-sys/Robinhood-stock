"""Lump vs staged deployment of a $400k deposit (2026-09-24), on the live-design
daily series from fall_protection_study.sim. Every start day, value 126
sessions later; money waiting earns the cash (BOXX / T-bill) return.
Results: STRATEGY.md "Staged deposit (2026-09-24)"."""
import sys, io, contextlib
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    import fall_protection_study as FP
AMT = 400_000
HOR = 126  # evaluate 6 months after the deposit
PLANS = {'lump (day 0)': (1, 0), '2 x 10 sess': (2, 10), '4 x 5 sess (4 wk)': (4, 5),
         '4 x 10 sess (8 wk)': (4, 10), '6 x 10 sess (12 wk)': (6, 10), '12 x 5 sess (12 wk)': (12, 5)}
def run(h):
    ser = FP.sim(h)[0]; cash = FP.CASHR[h]; n = len(ser)
    print(f"\n== {h}: {FP.DATES[h][0]} .. {FP.DATES[h][-1]}, every start day, value {HOR} sessions later ==")
    res = {}
    for name, (k, gap) in PLANS.items():
        outs = []
        for s in range(0, n - HOR):
            inv = 0.0; waiting = AMT
            for i in range(HOR):
                t = i
                if gap == 0 and t == 0 or (gap and t % gap == 0 and t // gap < k):
                    add = AMT / k; waiting -= add; inv += add
                inv *= 1 + ser[s + i]; waiting *= 1 + cash[s + i]
            outs.append(inv + waiting)
        res[name] = outs
    L = res['lump (day 0)']
    for name, o in res.items():
        so = sorted(o); m = len(o)
        win = sum(1 for a, b in zip(L, o) if a > b) / m if name != 'lump (day 0)' else float('nan')
        diff = sorted(b - a for a, b in zip(L, o))
        print(f"{name:22s} median ${so[m//2]:>9,.0f}  worst ${so[0]:>9,.0f}  5th pct ${so[m//20]:>9,.0f}  "
              f"lump beats it {win*100:5.1f}%  vs lump median {diff[m//2]:+9,.0f} best-case {diff[-1]:+9,.0f}")
for h in FP.H: run(h)
