import csv, sys, os
D, SRC = sys.argv[1], '/home/user/Robinhood-stock/data'
live = list(csv.DictReader(open(os.path.join(SRC, 'live_closes.csv'))))
spy = {'2026-08-28':769.35,'2026-08-31':767.05,'2026-09-01':761.78,'2026-09-02':765.16,'2026-09-03':773.17,'2026-09-04':770.19,'2026-09-08':765.96,'2026-09-09':762.40,'2026-09-10':757.83,'2026-09-11':764.29,'2026-09-14':760.88,'2026-09-15':757.39,'2026-09-16':754.05,'2026-09-17':762.60,'2026-09-18':761.69,'2026-09-21':773.50,'2026-09-22':773.38,'2026-09-23':767.81,'2026-09-24':767.18,'2026-09-25':771.35,'2026-09-28':765.61,'2026-09-29':764.20,'2026-09-30':762.63,'2026-10-01':763.99,'2026-10-02':769.64,'2026-10-05':774.83,'2026-10-06':779.09,'2026-10-07':777.22,'2026-10-08':773.93,'2026-10-09':778.57,'2026-10-12':778.10,'2026-10-13':778.01,'2026-10-14':769.60,'2026-10-15':771.79,'2026-10-16':763.25,'2026-10-19':766.48,'2026-10-20':769.05,'2026-10-21':773.09,'2026-10-22':763.96,'2026-10-23':759.97,'2026-10-26':765.37,'2026-10-27':769.66,'2026-10-28':772.31,'2026-10-29':769.36,'2026-10-30':755.72,'2026-11-02':752.10,'2026-11-03':754.35,'2026-11-04':766.81,'2026-11-05':733.2499}
def extend(name, col, cols_out, rows_fn):
    p = os.path.join(SRC, name); rows = list(csv.reader(open(p))); hdr = rows[0]; last = rows[-1][0]
    add = rows_fn(last)
    out = os.path.join(D, name); os.remove(out)
    w = csv.writer(open(out, 'w', newline='')); w.writerows(rows)
    for d, c in add:
        w.writerow([d] + [f'{c:.6f}'] * (len(hdr) - 1))
    print(name, last, '->', add[-1][0] if add else last, len(add))
for name, col in [('qqq_long_history.csv','QQQ'),('spmo_ohlc.csv','SPMO'),('tqqq_ohlc.csv','TQQQ'),('qld_ohlc.csv','QLD'),('xlu_ohlc.csv','XLU'),('QQEW_daily_ext.csv','QQEW'),('vixm_daily.csv','VIXM')]:
    extend(name, col, None, lambda last, col=col: [(r['date'], float(r[col])) for r in live if r['date'] > last and r[col]])
extend('spy_long_history.csv', None, None, lambda last: [(d, c) for d, c in sorted(spy.items()) if d > last])
p = os.path.join(SRC, 'dgs3mo_full.csv'); rows = list(csv.reader(open(p))); os.remove(os.path.join(D, 'dgs3mo_full.csv'))
csv.writer(open(os.path.join(D, 'dgs3mo_full.csv'), 'w', newline='')).writerows(rows)
