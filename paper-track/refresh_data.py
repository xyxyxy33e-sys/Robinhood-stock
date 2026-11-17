"""Append missing sessions to the research price / rate files in data/ (idempotent).

    python3 paper-track/refresh_data.py              # fetch Yahoo + FRED, append rows later than each file's last date
    python3 paper-track/refresh_data.py --dry-run    # report what would be appended, write nothing
    python3 paper-track/refresh_data.py --through 2026-11-16
    python3 paper-track/refresh_data.py --fred-dir DIR   # read FRED csvs (VIXCLS.csv ...) from DIR instead of fetching

Rules (each file keeps its own column layout, 6-decimal prices, ISO dates, split-adjusted NOT dividend-adjusted prices):
  * only rows with date > the file's last date are appended, never edited, so re-running adds nothing new;
  * the newest EXISTING row is re-fetched and must agree with the source within BASIS_TOL, otherwise that file is skipped with an
    error (guards against mixing a dividend-adjusted source into a price-basis file);
  * the last session fetched is capped at --through (default: the latest session that has closed in New York).
Price source: Yahoo chart API (browser-like User-Agent; returns split-adjusted OHLC in indicators.quote). Rates: FRED fredgraph.csv
(rows copied verbatim, including FRED's blank holiday rows). Cross-check by hand with Robinhood get_equity_historicals
(interval day, bounds regular, adjustment split): it matched the existing rows to the cent.
NOT touched: live_closes.csv, qqq_highs.csv, runs/ and every live state/ledger file.
"""
import argparse, csv, datetime as dt, io, json, os, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), 'data')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
BASIS_TOL = 0.002          # relative disagreement allowed on the last existing row

# file -> (Yahoo symbol, columns): columns map file header -> Yahoo field (o/h/l/c)
YAHOO_FILES = {
    'qqq_ohlc.csv':          ('QQQ',  ['d', 'o', 'h', 'l', 'c']),
    'qqq_long_history.csv':  ('QQQ',  ['d', 'o', 'c']),
    'spmo_ohlc.csv':         ('SPMO', ['d', 'o', 'h', 'l', 'c']),
    'tqqq_ohlc.csv':         ('TQQQ', ['d', 'o', 'h', 'l', 'c']),
    'qld_ohlc.csv':          ('QLD',  ['d', 'o', 'h', 'l', 'c']),
    'xlu_ohlc.csv':          ('XLU',  ['d', 'o', 'h', 'l', 'c']),
    'QQEW_daily_ext.csv':    ('QQEW', ['d', 'c']),
    'spy_long_history.csv':  ('SPY',  ['d', 'c']),
    'xlu_long_history.csv':  ('XLU',  ['d', 'c']),
    'vixm_daily.csv':        ('VIXM', ['d', 'c']),
}
FRED_FILES = {   # file -> FRED series id
    'vixcls_full.csv': 'VIXCLS', 'vxvcls.csv': 'VXVCLS', 'vxncls.csv': 'VXNCLS',
    'dgs3mo.csv': 'DGS3MO', 'dgs3mo_full.csv': 'DGS3MO',
}


def last_closed_session():
    try:
        from zoneinfo import ZoneInfo
        now = dt.datetime.now(ZoneInfo('America/New_York'))
    except Exception:
        now = dt.datetime.utcnow() - dt.timedelta(hours=5)
    d = now.date() if now.hour >= 17 else now.date() - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d.isoformat()


def yahoo_bars(sym, d0, d1, tries=6):
    """{date: {o,h,l,c}} for d0..d1 inclusive (ISO strings)."""
    p1 = int(dt.datetime.fromisoformat(d0).replace(tzinfo=dt.timezone.utc).timestamp()) - 5 * 86400
    p2 = int(dt.datetime.fromisoformat(d1).replace(tzinfo=dt.timezone.utc).timestamp()) + 2 * 86400
    url = f'https://query2.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={p2}&interval=1d'
    err = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
            j = json.load(urllib.request.urlopen(req, timeout=30))
            r = j['chart']['result'][0]
            off = r['meta'].get('gmtoffset', 0); q = r['indicators']['quote'][0]
            out = {}
            for i, ts in enumerate(r['timestamp']):
                d = dt.datetime.fromtimestamp(ts + off, dt.timezone.utc).date().isoformat()
                if None in (q['open'][i], q['high'][i], q['low'][i], q['close'][i]):
                    continue
                out[d] = dict(o=q['open'][i], h=q['high'][i], l=q['low'][i], c=q['close'][i])
            return out
        except Exception as e:           # 429 etc: back off and retry
            err = e; time.sleep(5 * (k + 1))
    raise RuntimeError(f'Yahoo fetch failed for {sym}: {err}')


def read_rows(path):
    with open(path, newline='') as f:
        return list(csv.reader(f))


def append_yahoo(fname, sym, cols, through, dry, cache):
    path = os.path.join(DATA, fname)
    rows = read_rows(path); hdr = rows[0]
    if hdr != cols:
        return f'{fname}: SKIP, header {hdr} != expected {cols}'
    last = rows[-1]; ld = last[0]
    if ld >= through:
        return f'{fname}: up to date (last {ld})'
    if sym not in cache:   # one fetch per symbol, starting at the oldest last-date among the files that use it
        d0 = min(read_rows(os.path.join(DATA, f))[-1][0] for f, (s_, _) in YAHOO_FILES.items() if s_ == sym)
        cache[sym] = yahoo_bars(sym, d0, through)
    bars = cache[sym]
    if ld not in bars:
        return f'{fname}: ERROR, source has no bar for the last existing date {ld}; nothing appended'
    for j, c in enumerate(cols[1:], 1):          # basis continuity on the newest existing row
        a, b = float(last[j]), bars[ld][c]
        if abs(b / a - 1) > BASIS_TOL:
            return f'{fname}: ERROR basis mismatch on {ld} col {c}: file {a} vs source {b:.6f}; nothing appended'
    new = [d for d in sorted(bars) if ld < d <= through]
    if not new:
        return f'{fname}: no new sessions after {ld}'
    if not dry:
        with open(path, 'a', newline='') as f:
            for d in new:
                f.write(','.join([d] + ['%.6f' % round(bars[d][c], 4) for c in cols[1:]]) + '\n')   # 4 dp strips Yahoo's float32 noise
    return f'{fname}: {"would append" if dry else "appended"} {len(new)} rows {new[0]}..{new[-1]}'


def fred_text(sid, fred_dir):
    if fred_dir:
        return open(os.path.join(fred_dir, sid + '.csv')).read()
    url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}'
    err = None
    for k in range(4):
        try:   # curl over HTTP/1.1 first: plain urllib / HTTP2 stalled through the sandbox proxy
            out = subprocess.run(['curl', '-sS', '--http1.1', '-m', '40', url], check=True, capture_output=True, text=True).stdout
            if out.startswith(('observation_date', 'DATE')):
                return out
            err = out[:80]
        except Exception as e:
            err = e
        time.sleep(3 * (k + 1))
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60).read().decode()
    except Exception as e:
        err = e
    raise RuntimeError(f'FRED fetch failed for {sid}: {err}')


def append_fred(fname, sid, through, dry, fred_dir, cache):
    path = os.path.join(DATA, fname)
    rows = read_rows(path); ld = rows[-1][0]
    if sid not in cache:
        cache[sid] = list(csv.reader(io.StringIO(fred_text(sid, fred_dir))))
    src = cache[sid]
    if src[0] != rows[0]:
        return f'{fname}: ERROR header {src[0]} != {rows[0]}; nothing appended'
    sm = {r[0]: r[1] for r in src[1:]}
    if ld in sm and rows[-1][1] != sm[ld]:        # basis/revision check on the newest existing row
        return f'{fname}: ERROR last row {ld} differs: file {rows[-1][1]!r} vs FRED {sm[ld]!r}; nothing appended'
    new = [r for r in src[1:] if ld < r[0] <= through]
    if not new:
        return f'{fname}: no new rows after {ld}'
    if not dry:
        with open(path, 'a', newline='') as f:
            for r in new:
                f.write(r[0] + ',' + r[1] + '\n')
    return f'{fname}: {"would append" if dry else "appended"} {len(new)} rows {new[0][0]}..{new[-1][0]} (last value {new[-1][1] or "blank"})'


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--through', default=None, help='last session to append (default: latest closed NY session)')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--fred-dir', default=None, help='directory with VIXCLS.csv, VXVCLS.csv, VXNCLS.csv, DGS3MO.csv')
    a = ap.parse_args()
    through = a.through or last_closed_session()
    print('refresh_data: through', through, '(dry run)' if a.dry_run else '')
    bad = 0; cache = {}
    for fname, (sym, cols) in YAHOO_FILES.items():
        msg = append_yahoo(fname, sym, cols, through, a.dry_run, cache); print(msg); bad += 'ERROR' in msg or 'SKIP' in msg
    fc = {}
    for fname, sid in FRED_FILES.items():
        msg = append_fred(fname, sid, through, a.dry_run, a.fred_dir, fc); print(msg); bad += 'ERROR' in msg
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
