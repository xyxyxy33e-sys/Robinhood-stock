"""Fetch SQQQ daily history from Yahoo chart API -> sqqq_yahoo_full.csv (d, close_split_adj, adjclose, div, volume)."""
import urllib.request, json, time, datetime as dt, csv, os
HERE = os.path.dirname(os.path.abspath(__file__))
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
url = 'https://query2.finance.yahoo.com/v8/finance/chart/SQQQ?period1=1262304000&period2=%d&interval=1d&events=div,split' % (time.time() + 86400)
j = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'}), timeout=60))
r = j['chart']['result'][0]; off = r['meta'].get('gmtoffset', 0)
q = r['indicators']['quote'][0]; adj = r['indicators']['adjclose'][0]['adjclose']
divs = {dt.datetime.fromtimestamp(v['date'] + off, dt.timezone.utc).date().isoformat(): v['amount'] for v in r.get('events', {}).get('dividends', {}).values()}
spl = {dt.datetime.fromtimestamp(v['date'] + off, dt.timezone.utc).date().isoformat(): v['splitRatio'] for v in r.get('events', {}).get('splits', {}).values()}
with open(os.path.join(HERE, 'sqqq_yahoo_full.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['d', 'close_split_adj', 'adjclose', 'div', 'volume'])
    for i, ts in enumerate(r['timestamp']):
        if q['close'][i] is None: continue
        d = dt.datetime.fromtimestamp(ts + off, dt.timezone.utc).date().isoformat()
        w.writerow([d, '%.6f' % q['close'][i], '%.6f' % adj[i], divs.get(d, ''), q['volume'][i]])
print('rows', len(r['timestamp']), 'splits', spl, 'ndiv', len(divs))
