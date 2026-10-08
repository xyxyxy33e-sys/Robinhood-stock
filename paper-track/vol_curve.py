"""VIX / VIX3M inputs for the VIXM sleeve (state.vixm_state), added 2026-10-08.

Robinhood's index feed carries VIX (real time, get_index_quotes) but NOT VIX3M.

VIX3M today (15:5x), in order:
  1. MEDIAN of the fresh live quotes from CBOE's delayed-quote JSON, Google
     Finance and Yahoo (all three republish CBOE's index; the median guards
     against one stale or broken feed). "Fresh" = stamped within
     LIVE_MAX_AGE_MIN of now; at least one must be fresh.
  2. If none is fresh: the PROXY, VIX3M ~= PROXY_K x SMA63(VIX). Tested
     2026-10-08 in the VIXM sleeve (research/vol-backtest): the proxy agrees
     with the real "VIX > VIX3M" flag on 96% of days 2011-2026 and the rule
     scored Sharpe 1.95 vs 1.90 with real VIX3M, but PROXY_K (1.32) was fitted
     on that same window, so it is the fallback, not the source.
History (the latch replays it every run): CBOE daily CSVs, then FRED
(VIXCLS / VXVCLS). If VIX3M history is missing but VIX history exists, the
history uses the proxy too (reported).

    vix, vix3m, note = vol_curve.load_vix_inputs(today, vix_now=<RH VIX>)
    vx = state.vixm_state(dates, px, vix, vix3m, as_of=today)

If even VIX history cannot be had, this raises and the run passes
state.vixm_unavailable(<error>) and reports it -- never a guessed reading.
"""
import csv
import datetime
import io
import json
import re
import statistics
import time
import urllib.request

CBOE_HIST = "https://cdn.cboe.com/api/global/us_indices/daily_prices/{sym}_History.csv"
FRED_HIST = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
FRED_IDS = {"VIX": "VIXCLS", "VIX3M": "VXVCLS"}
CBOE_LIVE = "https://cdn.cboe.com/api/global/delayed_quotes/quotes/_{sym}.json"
YAHOO_LIVE = "https://query2.finance.yahoo.com/v8/finance/chart/%5E{sym}?range=1d&interval=1m"
GOOGLE_LIVE = "https://www.google.com/finance/quote/{sym}:INDEXCBOE"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
LIVE_MAX_AGE_MIN = 30
PROXY_K = 1.32
PROXY_N = 63


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


# ---------------------------------------------------------------- history
def _cboe_history(sym):
    out = {}
    for row in csv.DictReader(io.StringIO(_get(CBOE_HIST.format(sym=sym)))):
        m, d, y = row["DATE"].split("/")
        out[f"{y}-{int(m):02d}-{int(d):02d}"] = float(row["CLOSE"])
    return out


def _fred_history(sym):
    out = {}
    for row in csv.reader(io.StringIO(_get(FRED_HIST.format(sid=FRED_IDS[sym]), timeout=60))):
        if len(row) == 2 and row[0][:2] in ("19", "20"):
            try:
                out[row[0]] = float(row[1])
            except ValueError:
                pass            # FRED marks holidays with "."
    return out


def history(sym):
    """({ISO date: close}, source) for VIX or VIX3M: CBOE, then FRED."""
    errors = []
    for name, fn in (("CBOE", _cboe_history), ("FRED", _fred_history)):
        try:
            h = fn(sym)
            if len(h) >= 1000:
                return h, name
            errors.append(f"{name}: only {len(h)} rows")
        except Exception as e:   # noqa: BLE001 -- fall through to the next source
            errors.append(f"{name}: {e}")
    raise RuntimeError(f"no {sym} history: " + "; ".join(errors))


# ---------------------------------------------------------------- live
def _age_min(ts_utc):
    return (datetime.datetime.now(datetime.timezone.utc) - ts_utc).total_seconds() / 60


def _cboe_live(sym):
    j = json.loads(_get(CBOE_LIVE.format(sym=sym)))
    # CBOE's "timestamp" is UTC (checked 2026-10-08: 15:03:29 stamped at 15:04 UTC)
    ts = datetime.datetime.strptime(j["timestamp"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
    return float(j["data"]["current_price"]), ts


def _yahoo_live(sym):
    m = json.loads(_get(YAHOO_LIVE.format(sym=sym)))["chart"]["result"][0]["meta"]
    return float(m["regularMarketPrice"]), datetime.datetime.fromtimestamp(m["regularMarketTime"], datetime.timezone.utc)


def _google_live(sym):
    html = _get(GOOGLE_LIVE.format(sym=sym))
    # the quote block: ["VIX3M","INDEXCBOE"],"<name>",1,null,[<last>,<chg>,<pct>,...
    m = re.search(r'\["%s","INDEXCBOE"\],"[^"]*",\d+,null,\[([0-9.]+),' % re.escape(sym), html)
    if not m:
        raise ValueError("price block not found")
    return float(m.group(1)), datetime.datetime.now(datetime.timezone.utc)   # page is live; no stamp exposed


def live_quotes(sym):
    """[(source, value, age_minutes)] for every live source that answered."""
    out = []
    for name, fn in (("CBOE", _cboe_live), ("Google", _google_live), ("Yahoo", _yahoo_live)):
        try:
            v, ts = fn(sym)
            if v > 0:
                out.append((name, v, _age_min(ts)))
        except Exception:        # noqa: BLE001
            pass
        time.sleep(0.2)
    return out


def proxy_vix3m(vix_hist, today, vix_now):
    """PROXY_K x the PROXY_N-session mean of VIX closes up to and including today."""
    days = sorted(d for d in vix_hist if d < today)[-(PROXY_N - 1):]
    vals = [vix_hist[d] for d in days] + [float(vix_now)]
    if len(vals) < PROXY_N:
        raise RuntimeError("not enough VIX history for the proxy")
    return PROXY_K * sum(vals) / len(vals)


def load_vix_inputs(today, vix_now, vix3m_now=None):
    """Histories with today's 15:5x readings appended. vix_now: Robinhood's
    live VIX. vix3m_now: pass to override. Returns (vix, vix3m, note); note
    names every source used and is to be reported verbatim."""
    vix, vsrc = history("VIX")
    parts = [f"VIX {float(vix_now):.2f} (Robinhood; history {vsrc})"]
    try:
        vix3m, v3src = history("VIX3M")
        parts.append(f"VIX3M history {v3src}")
    except RuntimeError as e:
        days = sorted(vix)
        vix3m = {}
        for i in range(PROXY_N - 1, len(days)):
            vix3m[days[i]] = PROXY_K * sum(vix[d] for d in days[i - PROXY_N + 1:i + 1]) / PROXY_N
        parts.append(f"VIX3M history = PROXY ({e})")
    if vix3m_now is None:
        q = live_quotes("VIX3M")
        fresh = [(s, v, a) for s, v, a in q if a <= LIVE_MAX_AGE_MIN]
        if fresh:
            vix3m_now = statistics.median(v for _, v, _ in fresh)
            parts.append("VIX3M {:.2f} = median of ".format(vix3m_now) +
                         ", ".join(f"{s} {v:.2f} ({a:.0f}m)" for s, v, a in fresh))
            stale = [s for s, _, a in q if a > LIVE_MAX_AGE_MIN]
            if stale:
                parts.append("stale ignored: " + ", ".join(stale))
        else:
            vix3m_now = proxy_vix3m(vix, today, vix_now)
            parts.append(f"VIX3M {vix3m_now:.2f} = PROXY {PROXY_K} x SMA{PROXY_N}(VIX) -- no fresh live quote "
                         f"({', '.join(f'{s} {a:.0f}m old' for s, _, a in q) or 'all sources failed'})")
    else:
        parts.append(f"VIX3M {float(vix3m_now):.2f} (given)")
    vix[today] = float(vix_now)
    vix3m[today] = float(vix3m_now)
    parts.append(f"ratio {float(vix_now) / float(vix3m_now):.3f}")
    return vix, vix3m, "; ".join(parts)
