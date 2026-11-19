import numpy as np, runpy, sys, io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    g = runpy.run_path('spx.py')
dates, E, run, tr, cash = g['dates'], g['E'], g['run'], g['tr'], g['cash']
ST, LT, ORD = 0.388, 0.188, 0.388          # federal incl. NIIT
def taxable_s2(start):
    """2x S&P while up, T-bills otherwise; each exit realizes the spell's gain; ST if held <= 365 days; T-bill
    interest taxed as ordinary yearly; tax paid at year end from the account; losses carried forward."""
    e = E['S2 200-day 2x']; r = run(e)
    s0 = next(i for i, d in enumerate(dates) if d >= start)
    V = 1.0; basis = None; entry = None; yr = dates[s0][:4]; gst = glt = ordi = 0.0; cf = 0.0
    for i in range(s0 + 1, len(dates)):
        d = dates[i]
        if d[:4] != yr:   # pay last year's tax
            net_st = gst + min(cf, 0); net = net_st + glt
            tax = max(net_st, 0) * ST + max(glt + min(net_st, 0), 0) * LT + ordi * ORD
            cf = min(net, 0) if net < 0 else 0.0
            V -= tax
            if basis is not None: basis *= 1  # holding basis unchanged; tax paid from the position pro rata
            gst = glt = ordi = 0.0; yr = d[:4]
        invested = e[i - 1] > 0
        if not invested: ordi += V * cash[i]
        V *= 1 + r[i]
        if invested and basis is None: basis, entry = V / (1 + r[i]), d
        if not invested and basis is not None:
            gain = V / (1 + r[i]) - basis
            days = (np.datetime64(d) - np.datetime64(entry)).astype(int)
            if days > 365: glt += gain
            else: gst += gain
            basis = None
    if basis is not None: V -= max(V - basis, 0) * LT  # liquidate at end, LT
    n = len(dates) - s0 - 1
    return V ** (252 / n) - 1
def taxable_bh(start, dy=0.019):
    s0 = next(i for i, d in enumerate(dates) if d >= start); V = 1.0; basis = 1.0
    for i in range(s0 + 1, len(dates)):
        V *= 1 + tr[i]; t = V * dy / 252 * 0.188; V -= t; basis += 0  # qualified dividend tax, reinvested net
    V -= (V - basis) * LT; n = len(dates) - s0 - 1
    return V ** (252 / n) - 1
for start in ('1990-01-02', '2007-01-03'):
    m = [d >= start for d in dates]
    pre_s2 = np.prod(1 + run(E['S2 200-day 2x'])[np.array(m)]) ** (252 / sum(m)) - 1
    pre_bh = np.prod(1 + tr[np.array(m)]) ** (252 / sum(m)) - 1
    print(f"from {start}: S2 pre-tax {pre_s2*100:.1f}% -> after federal tax {taxable_s2(start)*100:.1f}% | "
          f"S&P buy&hold pre-tax {pre_bh*100:.1f}% -> after tax (div yearly, LT at end) {taxable_bh(start)*100:.1f}%")
# how many exits were long-term
e = E['S2 200-day 2x']; ent = None; n_st = n_lt = 0
for i in range(1, len(dates)):
    if dates[i] < '1990': continue
    if e[i] > 0 and e[i - 1] == 0: ent = dates[i]
    if e[i] == 0 and e[i - 1] > 0 and ent:
        days = (np.datetime64(dates[i]) - np.datetime64(ent)).astype(int); n_lt += days > 365; n_st += days <= 365
print(f"since 1990: {n_st} short-term exits, {n_lt} long-term exits")
