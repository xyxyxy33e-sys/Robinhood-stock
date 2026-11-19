"""Paper track of the simple S&P rule, the yardstick for the live strategy's one-year review (owner, 2026-11-19).

RULE (research_notes/ira_2026_11/spx.py, S2): hold 2x S&P (SSO) while SPY's adjusted close is above its 200-day
average (1% hysteresis: in above +1%, out below -1%); otherwise T-bills (BIL). Decided at a close, earned from the
next session. Paper only: nothing is traded. Inception 2026-11-19 close = 1.0.

    python3 paper-track/simple_sp_track.py            # rebuilds data/simple_sp_paper.csv, prints the last row

Also prints a WASH-SALE line for the owner's IRA SPMO purchases: whether the live account sold SPMO at a loss in
the last 30 days (data/fill_quality.csv sells vs average cost are not tracked here, so it lists SPMO sells)."""
import csv, json, os, sys, urllib.request, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'data', 'simple_sp_paper.csv')
INCEPTION = '2026-11-19'
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}

def adj(sym):
    u = f"https://query2.finance.yahoo.com/v8/finance/chart/{sym}?range=2y&interval=1d&events=div"
    r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read())['chart']['result'][0]
    off = r['meta'].get('gmtoffset', 0) or 0
    return {dt.datetime.utcfromtimestamp(t + off).date().isoformat(): v
            for t, v in zip(r['timestamp'], r['indicators']['adjclose'][0]['adjclose']) if v}

def build():
    spy, sso, bil = adj('SPY'), adj('SSO'), adj('BIL')
    ds = [d for d in sorted(spy) if d in sso and d in bil]
    rows, on = [], None
    for i, d in enumerate(ds):
        if i < 199:
            continue
        sma = sum(spy[x] for x in ds[i - 199:i + 1]) / 200; g = spy[d] / sma - 1
        on = (g > 0.01) if on is None else (g > -0.01 if on else g > 0.01)
        rows.append(dict(date=d, spy=spy[d], sma200=sma, gap=g, hold='SSO' if on else 'BIL', sso=sso[d], bil=bil[d]))
    nav, prev = None, None
    for r in rows:
        if r['date'] >= INCEPTION:
            if nav is None:
                nav = 1.0
            else:
                k = prev['hold']
                nav *= r[k.lower()] / prev[k.lower()]
        r['nav'] = nav
        prev = r
    rows = [r for r in rows if r['nav'] is not None]
    with open(OUT, 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['date', 'spy_adj', 'sma200', 'gap200', 'hold_next', 'sso_adj', 'bil_adj', 'nav'])
        for r in rows:
            w.writerow([r['date'], f"{r['spy']:.4f}", f"{r['sma200']:.4f}", f"{r['gap']:.5f}", r['hold'],
                        f"{r['sso']:.4f}", f"{r['bil']:.4f}", f"{r['nav']:.6f}"])
    return rows

def spmo_sells(days=30):
    p = os.path.join(ROOT, 'data', 'fill_quality.csv'); cut = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    if not os.path.exists(p):
        return []
    return [r for r in csv.DictReader(open(p)) if r['symbol'] == 'SPMO' and r['side'] == 'sell' and r['date'] >= cut]

if __name__ == '__main__':
    rows = build(); r = rows[-1]
    print(f"simple S&P paper ({r['date']}): SPY {r['gap']*100:+.1f}% vs 200-day -> holds {r['hold']} next session; "
          f"NAV {r['nav']:.4f} ({(r['nav']-1)*100:+.2f}% since {INCEPTION})")
    s = spmo_sells()
    print("IRA SPMO buy window: " + ("CAUTION -- live sold SPMO on " + ", ".join(sorted({x['date'] for x in s})) +
          " (check for a loss; an IRA buy within 30 days of a loss sale makes that part of the loss permanent)"
          if s else "OK -- no live SPMO sales in the last 30 days (a live loss sale in the next 30 days can still wash)"))
