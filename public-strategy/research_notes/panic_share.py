"""2026-11-24, owner: VIX-panic leg share 25% -> 50%. Live rules otherwise (2% band, vol target with buffer).
Engine and taxes of better.py (after-tax figures tax fund distributions too)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import better as B
H = [('2007-07-02', '9999'), ('2007-07-02', '2015-12-31'), ('2016-01-04', '9999')]
print("share | " + " | ".join(f"{a[:4]}-{'2026' if b == '9999' else b[:4]}: CAGR Sharpe MaxDD worst / after-tax CAGR" for a, b in H))
for p in (0.0, 0.25, 0.5, 0.75, 1.0):
    mk = lambda: B.Live(band=.02, panic=p); out = []
    for a, b in H:
        x = B.sim(mk, start=a, end=b); t = B.sim(mk, start=a, end=b, tax=True); s, st = B.stats(x[0], x[1]), B.stats(t[0], t[1])
        out.append(f"{s[0]:5.1f} {s[1]:5.2f} {s[2]:6.1f} {s[3]:6.1f} / {st[0]:5.1f}")
    print(f"{p:4.0%}  | " + " | ".join(out))
