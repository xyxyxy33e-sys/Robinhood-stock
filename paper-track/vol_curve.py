"""VIX / VIX3M inputs for the VIXM sleeve (state.vixm_state), added 2026-10-08.

Robinhood's index feed carries VIX (real time, via get_index_quotes) but NOT
VIX3M, so the daily histories and the intraday VIX3M come from CBOE's public
files:
  history  https://cdn.cboe.com/api/global/us_indices/daily_prices/{SYM}_History.csv
  live     https://cdn.cboe.com/api/global/delayed_quotes/quotes/_{SYM}.json  (~15 min delayed)

At 15:5x the VIX3M reading is therefore ~15 minutes old while VIX is current.
The latch only flips OFF on VIX > VIX3M, so a stale VIX3M can move an exit by
one session at most on a knife-edge day; that is accepted and reported.

Usage in a live run (today's VIX from get_index_quotes on the VIX index id):

    vix, vix3m, note = vol_curve.load_vix_inputs(today, vix_now=<RH VIX value>)
    vx = state.vixm_state(dates, px, vix, vix3m, as_of=today)

If anything here raises, the run passes state.vixm_unavailable(<error>) and
reports it -- never a guessed reading.
"""
import csv
import datetime
import io
import json
import time
import urllib.request

HIST_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/{sym}_History.csv"
LIVE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/quotes/_{sym}.json"
UA = {"User-Agent": "Mozilla/5.0 (paper-track vol_curve)"}


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


def cboe_history(sym):
    """{ISO date: close} for a CBOE index (VIX, VIX3M), full daily history."""
    out = {}
    for row in csv.DictReader(io.StringIO(_get(HIST_URL.format(sym=sym)))):
        m, d, y = row["DATE"].split("/")
        out[f"{y}-{int(m):02d}-{int(d):02d}"] = float(row["CLOSE"])
    if len(out) < 1000:
        raise ValueError(f"CBOE {sym} history has only {len(out)} rows")
    return out


YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/%5E{sym}?range=1d&interval=1d"


def cboe_live(sym):
    """(value, source/timestamp) for an index's intraday level: CBOE's delayed
    quote, retried once, then Yahoo's chart endpoint (CBOE rate-limits bursts
    with HTTP 429). Raises if every source fails."""
    errors = []
    for attempt in range(2):
        try:
            j = json.loads(_get(LIVE_URL.format(sym=sym)))
            v = float(j["data"]["current_price"])
            if v > 0:
                return v, f"CBOE {j.get('timestamp', '')}"
            errors.append(f"CBOE returned {v}")
        except Exception as e:      # noqa: BLE001 -- any failure falls through to the next source
            errors.append(f"CBOE: {e}")
            time.sleep(3)
    try:
        j = json.loads(_get(YAHOO_URL.format(sym=sym)))
        meta = j["chart"]["result"][0]["meta"]
        v = float(meta["regularMarketPrice"])
        if v > 0:
            ts = datetime.datetime.fromtimestamp(meta.get("regularMarketTime", 0), datetime.timezone.utc)
            return v, f"Yahoo {ts:%Y-%m-%d %H:%M}Z"
        errors.append(f"Yahoo returned {v}")
    except Exception as e:          # noqa: BLE001
        errors.append(f"Yahoo: {e}")
    raise RuntimeError(f"no live {sym} reading: " + "; ".join(errors))


def load_vix_inputs(today, vix_now, vix3m_now=None):
    """Histories with today's 15:5x readings appended (today's row replaces any
    same-date history row). vix_now: Robinhood's live VIX. vix3m_now: pass to
    override, else CBOE's delayed quote. Returns (vix, vix3m, note)."""
    vix = cboe_history("VIX")
    vix3m = cboe_history("VIX3M")
    ts = "given"
    if vix3m_now is None:
        vix3m_now, ts = cboe_live("VIX3M")
    vix[today] = float(vix_now)
    vix3m[today] = float(vix3m_now)
    note = (f"VIX {vix_now:.2f} (Robinhood) / VIX3M {vix3m_now:.2f} ({ts}) "
            f"ratio {vix_now / vix3m_now:.3f}")
    return vix, vix3m, note
