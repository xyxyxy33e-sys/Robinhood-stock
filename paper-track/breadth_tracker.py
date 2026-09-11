"""Breadth forward test -- MEASUREMENT ONLY (added 2026-09-11).

The pre-registered candidate rule under forward test is

    effective state D  AND  the 60-day QQEW/QQQ relative-strength reading is
    in its trailing-252 bottom quintile (pct < 0.20)   ->   D row to cash.

It is NOT applied: nothing here changes a weight, and the live Routines only
call breadth_reading() / record_d_day() / fill_next_returns() after all
trading and reporting steps. Rationale, evidence and the pre-registered
decision rule: STRATEGY.md ("Breadth and rates as regime inputs") and
paper-track/research_notes/dgate_anatomy.md section 6. The percentile code
is the study's own `trailing_pct`, copied verbatim from breadth_signal.py so
the live reading and the research reading are the same function.

Decision rule (evaluated by the OWNER through the normal change process, never
by a Routine): after 8 gated runs or 48 months of logging, whichever first,
the rule passes if the gated-minus-ungated next-day QLD leg return is negative
at P < 0.05 under a circular-shift null AND at least 5 of the 8 gated runs are
negative. GATE_PCT, LOOKBACK and WINDOW are frozen for the duration.
"""
import bisect, csv, math, os

LOOKBACK = 60          # sessions in the relative-strength change
WINDOW = 252           # sessions in the trailing percentile window
GATE_PCT = 0.20        # bottom quintile
LOG = 'data/dgate_forward_log.csv'
FIELDS = ['date', 'eff_state', 'x60', 'pct', 'gate', 'qld_next', 'qqq_next', 'note']

# P(next effective state is E/F | a state-D day), by breadth-percentile bucket.
# From research_notes/dgate_anatomy.md section 2 (727 D days, 2007-07..2026-08,
# n = 124 / 162 / 187 / 132 / 122). Informational only.
BUCKET_BASE = ((0.0, 0.2, 0.54), (0.2, 0.4, 0.27), (0.4, 0.6, 0.05), (0.6, 0.8, 0.05), (0.8, 1.01, 0.30))
D_EPISODE_BASE_RATE = 0.16   # unconditional share of D episodes that end in E/F


def trailing_pct(v, n=WINDOW):
    """Verbatim from breadth_signal.py: percentile of v[i] within the last n
    valid values (inclusive), None until n values are available; a None in v
    resets the window (a stale/missing leg must never leak into the rank)."""
    out = [None] * len(v); win = []; hist = []
    for i, x in enumerate(v):
        if x is None: win = []; hist = []; continue
        bisect.insort(win, x); hist.append(x)
        if len(hist) > n: win.pop(bisect.bisect_left(win, hist.pop(0)))
        if len(win) == n:
            lo = bisect.bisect_left(win, x); hi = bisect.bisect_right(win, x)
            out[i] = (lo + 0.5 * (hi - lo)) / n
    return out


def relative_strength_series(dates, qqew, qqq, lookback=LOOKBACK):
    """x[d] = log(QQEW/QQQ)[d] - log(QQEW/QQQ)[d - lookback sessions] on the
    dates both legs have a close. Both dicts are date -> split-adjusted close."""
    common = [d for d in sorted(dates) if d in qqew and d in qqq]
    lr = [math.log(qqew[d] / qqq[d]) for d in common]
    x = [None] * len(common)
    for i in range(lookback, len(common)):
        x[i] = lr[i] - lr[i - lookback]
    return common, x


def breadth_reading(dates, qqew, qqq, as_of=None):
    """The live reading for one session. Needs >= LOOKBACK + WINDOW common
    sessions of history (312) or pct is None (report 'insufficient history',
    gate False)."""
    common, x = relative_strength_series(dates, qqew, qqq)
    if not common:
        raise ValueError('no common QQEW/QQQ dates')
    p = trailing_pct(x)
    if as_of is None:
        as_of = common[-1]
    if as_of not in common:
        raise ValueError(f'{as_of} is not a session with both QQEW and QQQ closes')
    i = common.index(as_of)
    pct = p[i]
    return dict(date=as_of, x60=x[i], pct=pct, gate=(pct is not None and pct < GATE_PCT),
                n_hist=sum(1 for v in x[:i + 1] if v is not None))


def bucket_base_rate(pct):
    """Historical P(next state E/F) for a D day in this breadth bucket."""
    if pct is None:
        return None
    for lo, hi, pr in BUCKET_BASE:
        if lo <= pct < hi:
            return pr
    return None


def _read(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def _write(rows, path):
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in FIELDS})


def record_d_day(date, eff_state, x60, pct, gate, note='', path=LOG):
    """Append one row for a session whose EFFECTIVE state is D. Idempotent:
    a second call for the same date is ignored (returns False)."""
    if eff_state != 'D':
        raise ValueError('record_d_day is for effective-state-D sessions only')
    rows = _read(path)
    if any(r['date'] == date for r in rows):
        return False
    rows.append(dict(date=date, eff_state=eff_state, x60='' if x60 is None else f'{x60:.6f}',
                     pct='' if pct is None else f'{pct:.4f}', gate=int(bool(gate)),
                     qld_next='', qqq_next='', note=note))
    rows.sort(key=lambda r: r['date'])
    _write(rows, path)
    return True


def fill_next_returns(date, qld_next, qqq_next, path=LOG):
    """Fill the next-session official close-to-close returns for a logged D day."""
    rows = _read(path)
    hit = False
    for r in rows:
        if r['date'] == date:
            r['qld_next'] = f'{qld_next:.6f}'; r['qqq_next'] = f'{qqq_next:.6f}'; hit = True
    if not hit:
        raise KeyError(f'no logged D day {date}')
    _write(rows, path)
    return True


def gated_runs(rows):
    """Consecutive gated D days = one run (the study's unit)."""
    runs = []; cur = None
    for r in rows:
        if r['gate'] in ('1', 1, True):
            if cur is None:
                cur = [r]
            else:
                cur.append(r)
        else:
            if cur: runs.append(cur); cur = None
    if cur: runs.append(cur)
    return runs


def summarize(path=LOG):
    """Running tally for the pre-registered decision. Does not decide."""
    rows = _read(path)
    filled = [r for r in rows if r['qld_next'] not in ('', None)]
    g = [float(r['qld_next']) for r in filled if r['gate'] == '1']
    u = [float(r['qld_next']) for r in filled if r['gate'] != '1']
    runs = gated_runs(rows)
    run_ret = []
    for run in runs:
        v = [float(r['qld_next']) for r in run if r['qld_next'] not in ('', None)]
        if v:
            run_ret.append(sum(v))
    months = 0.0
    if rows:
        y0, m0 = int(rows[0]['date'][:4]), int(rows[0]['date'][5:7])
        y1, m1 = int(rows[-1]['date'][:4]), int(rows[-1]['date'][5:7])
        months = (y1 - y0) * 12 + (m1 - m0)
    return dict(n_d_days=len(rows), n_gated_days=sum(1 for r in rows if r['gate'] == '1'),
                n_gated_runs=len(runs), runs_negative=sum(1 for x in run_ret if x < 0),
                gated_mean_qld_next=(sum(g) / len(g) if g else None),
                ungated_mean_qld_next=(sum(u) / len(u) if u else None),
                months_logged=months, decision_due=(len(runs) >= 8 or months >= 48))


if __name__ == '__main__':
    # Self-check against the research reading: with the Yahoo-sourced QQEW and
    # the repo's QQQ closes, 2026-09-04 must read pct 0.867 (dgate_anatomy.md).
    import sys
    def load(path, dcol, ccol):
        out = {}
        with open(path) as f:
            for r in csv.DictReader(f):
                try: out[r[dcol]] = float(r[ccol])
                except (ValueError, KeyError): pass
        return out
    qqew = load('data/QQEW_daily.csv', 'd', 'c')
    qqq = load('data/qqq_ohlc.csv', 'd', 'c')
    r = breadth_reading(sorted(set(qqew) | set(qqq)), qqew, qqq, as_of='2026-09-04')
    print('2026-09-04:', r)
    assert abs(r['pct'] - 0.867) < 0.006, 'live reading does not reproduce the research reading'
    print('OK: breadth_tracker reproduces the research reading for 2026-09-04')
