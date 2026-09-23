"""Forward shadow tracks and the pre-written revert rule for extension trim v2
(fix 1 of the 2026-09-23 critique; owner: "fixes 1, 3 and 6 now").

WHY. Trim v2 was chosen post hoc from ~90 variants and never cleared
significance (bootstrap vs v1 P 0.06 real / 0.14 proxy). Its trade-off is
structural: the HOLD buys the drawdown protection and costs the melt-ups
(follow-ups 12-13). The honest test is forward, on market paths nobody has
seen, against the two designs it could be wrong against. The rule that decides
is written BELOW, before any forward data exists, so it cannot be fitted to it.

THREE PAPER TRACKS, updated once per completed session by the daily run with
the inputs it already computes (same state, vol, gaps, breadth, a_trim):
  * 'v2'      -- the live rule (live_target_weights). A paper copy, so the
                 comparison is engine-for-engine, free of fills and deposits.
  * 'fastcut' -- v2 WITHOUT the hold: TQQQ out and core cut at the RAW vote
                 count, back as soon as the votes clear (held = raw). Same base
                 row, same whipsaw carry of the spell.
  * 'sep19'   -- the 19 Sep design: the v1 trim (x2/3, x1/3, x0 on raw votes),
                 A 50/50. Information only; not part of the rule.
Each track: weights set at today's close earn tomorrow's close-to-close leg
returns; rebalance on a change of its key (effective state, D gate, its own
trim level) or L1 drift > REBALANCE_DRIFT_BAND; 4 bp one-way cost on the L1
turnover -- the backtest's conventions. Log: data/shadow_tracks.csv.

THE REVERT RULE (pre-registered 2026-09-23; do not edit after data arrives).
A "vote spell" is an A spell (A_SPELL_GAP_CARRY-aware) in which the raw trim
vote count reached >= 1. The WINDOW runs from the first session of the first
vote spell after 2026-09-23 through the last session of the SECOND completed
vote spell (then the next two, cumulatively, if inconclusive). Over the window:
  REVERT  -- recommend switching to fast-cut-only if the v2 track's return
             trails fastcut's by more than 10 percentage points AND v2's max
             drawdown in the window is NOT at least 1 pp shallower.
  AFFIRM  -- keep v2 and stop the comparison if QQQ fell more than 10% from a
             running high inside the window AND v2's max drawdown is at least
             5 pp shallower than fastcut's.
  otherwise INCONCLUSIVE -- keep v2; extend the window by the next two vote
             spells.
The check REPORTS; it never changes the design. The owner decides.
"""
import csv
import os

from state import (live_target_weights, target_weights_with_voltarget, d_gate_active,
                   effective_state, extension_votes, REBALANCE_DRIFT_BAND, A_SPELL_GAP_CARRY)

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'shadow_tracks.csv')
TRACKS = ('v2', 'fastcut', 'sep19')
LEGS = ('SPMO', 'TQQQ', 'QLD', 'XLU', 'BOXX')     # order of the 5-leg weight tuple
ONE_WAY_COST = 0.0004
START_DATE = '2026-09-23'
REVERT_TRAIL = 0.10        # v2 trails fastcut by more than this (return, fraction)
REVERT_DD_EDGE = 0.01      # ... and its max DD is not at least this much shallower
AFFIRM_QQQ_FALL = 0.10     # QQQ falls more than this from a running high in the window
AFFIRM_DD_EDGE = 0.05      # ... and v2's max DD is at least this much shallower
FIELDS = (['date', 'track', 'key', 'ret', 'nav', 'rebalanced']
          + [f'w_{l}' for l in LEGS] + [f'px_{l}' for l in LEGS]
          + ['qqq', 'eff', 'in_a', 'spell_start', 'raw', 'held'])


def track_targets(state, micro_agrees, vol, fast_state, gaps, breadth_pct, a_trim):
    """{track: (weights, key)} for one date. v2 goes through live_target_weights,
    so a missing input fails here exactly as it would for the live book."""
    eff = effective_state(state, fast_state)
    gate = d_gate_active(state, breadth_pct, gaps[200])
    raw = extension_votes(eff, gaps) if eff == 'A' else 0
    held = a_trim['held'] if a_trim['in_a'] else 0
    w_v2 = live_target_weights(state, micro_agrees, vol, fast_state, gaps, breadth_pct, a_trim)
    fc = dict(a_trim, held=a_trim['raw']) if a_trim['in_a'] else a_trim
    w_fc = target_weights_with_voltarget(state, micro_agrees, vol, fast_state=fast_state, gaps=gaps,
                                         d_gate=gate, a_trim=fc)
    w_19 = target_weights_with_voltarget(state, micro_agrees, vol, fast_state=fast_state, gaps=gaps,
                                         d_gate=gate, a_trim=None)
    base = f'{eff}|{int(gate)}'
    return {'v2': (w_v2, f'{base}|{held}'), 'fastcut': (w_fc, f'{base}|{raw}'),
            'sep19': (w_19, f'{base}|{raw}')}


def load(path=LOG_PATH):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


def _write(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def update(date, closes, qqq_close, state, micro_agrees, vol, fast_state, gaps, breadth_pct, a_trim,
           path=LOG_PATH):
    """Record one COMPLETED session for all three tracks. Idempotent: a re-run for
    the same date replaces that date's rows (recomputed from the prior date).
    closes: {'SPMO':..,'TQQQ':..,'QLD':..,'XLU':..,'BOXX':..} official closes.
    Returns {track: (ret, nav, rebalanced)}."""
    missing = [l for l in LEGS if not closes.get(l)]
    if missing:
        raise ValueError(f"shadow_tracker.update: missing closes for {missing}")
    rows = [r for r in load(path) if r['date'] != date]
    prior = [r for r in rows if r['date'] < date]
    if any(r['date'] > date for r in rows):
        raise ValueError(f"shadow_tracker.update: {date} is older than the last logged date; "
                         f"only the latest date may be re-run")
    tt = track_targets(state, micro_agrees, vol, fast_state, gaps, breadth_pct, a_trim)
    last = {}
    if prior:
        d0 = max(r['date'] for r in prior)
        last = {r['track']: r for r in prior if r['date'] == d0}
    out = {}
    for tr in TRACKS:
        target, key = tt[tr]
        p = last.get(tr)
        if p is None:
            held, ret, nav, reb = list(target), 0.0, 100.0, 1
        else:
            w = [float(p[f'w_{l}']) for l in LEGS]
            lr = [closes[l] / float(p[f'px_{l}']) - 1.0 for l in LEGS]
            gross = sum(wi * ri for wi, ri in zip(w, lr))
            drifted = [wi * (1 + ri) / (1 + gross) for wi, ri in zip(w, lr)]
            l1 = sum(abs(t - h) for t, h in zip(target, drifted))
            reb = int(key != p['key'] or l1 > REBALANCE_DRIFT_BAND)
            cost = ONE_WAY_COST * l1 if reb else 0.0
            held = list(target) if reb else drifted
            ret = gross - cost
            nav = float(p['nav']) * (1 + ret)
        row = dict(date=date, track=tr, key=key, ret=f'{ret:.8f}', nav=f'{nav:.6f}', rebalanced=reb,
                   qqq=qqq_close, eff=a_trim['eff'], in_a=int(bool(a_trim['in_a'])),
                   spell_start=a_trim['spell_start'] or '', raw=a_trim['raw'], held=a_trim['held'])
        row.update({f'w_{l}': f'{x:.6f}' for l, x in zip(LEGS, held)})
        row.update({f'px_{l}': closes[l] for l in LEGS})
        rows.append(row)
        out[tr] = (ret, nav, reb)
    rows.sort(key=lambda r: (r['date'], TRACKS.index(r['track'])))
    _write(rows, path)
    return out


def vote_spells(rows):
    """[(spell_start, first_date, last_date, completed)] for A spells with raw >= 1,
    in date order, from the v2 rows. A spell is completed once the book has been
    out of A for more than A_SPELL_GAP_CARRY sessions or a new spell has begun."""
    v = sorted((r for r in rows if r['track'] == 'v2'), key=lambda r: r['date'])
    spells = {}; order = []
    for r in v:
        if r['in_a'] == '1':
            s = r['spell_start']
            if s not in spells:
                spells[s] = dict(first=r['date'], last=r['date'], votes=False); order.append(s)
            spells[s]['last'] = r['date']
            spells[s]['votes'] |= int(r['raw']) >= 1
    out = []
    for s in order:
        after = [r for r in v if r['date'] > spells[s]['last']]
        gap = 0; done = False
        for r in after:
            if r['in_a'] == '1':
                done = r['spell_start'] != s
                break
            gap += 1
            if gap > A_SPELL_GAP_CARRY:
                done = True
                break
        if spells[s]['votes']:
            out.append((s, spells[s]['first'], spells[s]['last'], done))
    return out


def _window_stats(rows, track, lo, hi):
    v = sorted((r for r in rows if r['track'] == track and lo <= r['date'] <= hi), key=lambda r: r['date'])
    prev = [r for r in rows if r['track'] == track and r['date'] < lo]
    nav0 = float(max(prev, key=lambda r: r['date'])['nav']) if prev else float(v[0]['nav'])
    navs = [nav0] + [float(r['nav']) for r in v]
    peak, mdd = navs[0], 0.0
    for x in navs:
        peak = max(peak, x); mdd = min(mdd, x / peak - 1)
    return navs[-1] / nav0 - 1, mdd


def revert_check(rows=None):
    """Apply the pre-registered rule. Returns dict(verdict, ...) where verdict is
    'NO DATA', 'WAITING' (fewer than two completed vote spells), 'REVERT',
    'AFFIRM' or 'INCONCLUSIVE'. Reports only; never changes the design."""
    rows = load() if rows is None else rows
    rows = [r for r in rows if r['date'] >= START_DATE]
    if not rows:
        return dict(verdict='NO DATA')
    sp = vote_spells(rows)
    done = [s for s in sp if s[3]]
    if len(done) < 2:
        return dict(verdict='WAITING', vote_spells=len(sp), completed=len(done))
    n = 2 * (len(done) // 2)                  # windows grow two completed vote spells at a time
    lo, hi = sp[0][1], done[n - 1][2]
    r2, d2 = _window_stats(rows, 'v2', lo, hi)
    rf, df = _window_stats(rows, 'fastcut', lo, hi)
    q = [float(r['qqq']) for r in sorted((r for r in rows if r['track'] == 'v2' and lo <= r['date'] <= hi),
                                          key=lambda r: r['date'])]
    pk, qdd = q[0], 0.0
    for x in q:
        pk = max(pk, x); qdd = min(qdd, x / pk - 1)
    res = dict(window=(lo, hi), completed=len(done), v2_ret=r2, fastcut_ret=rf, v2_mdd=d2, fastcut_mdd=df,
               qqq_fall=qdd)
    if (r2 - rf) < -REVERT_TRAIL and not (d2 >= df + REVERT_DD_EDGE):
        res['verdict'] = 'REVERT'
    elif qdd < -AFFIRM_QQQ_FALL and d2 >= df + AFFIRM_DD_EDGE:
        res['verdict'] = 'AFFIRM'
    else:
        res['verdict'] = 'INCONCLUSIVE'
    return res


def summary_line(rows=None):
    """One line for the weekly report."""
    rows = load() if rows is None else rows
    if not rows:
        return "shadow tracks: no data yet"
    d = max(r['date'] for r in rows)
    nav = {r['track']: float(r['nav']) for r in rows if r['date'] == d}
    rc = revert_check(rows)
    extra = {'WAITING': f"{rc.get('completed', 0)}/2 completed vote spells"}.get(rc['verdict'], '')
    if rc['verdict'] in ('REVERT', 'AFFIRM', 'INCONCLUSIVE'):
        extra = (f"window {rc['window'][0]}..{rc['window'][1]}: v2 {rc['v2_ret']*100:+.1f}% (DD {rc['v2_mdd']*100:.1f}%) "
                 f"vs fast-cut {rc['fastcut_ret']*100:+.1f}% (DD {rc['fastcut_mdd']*100:.1f}%), QQQ fall {rc['qqq_fall']*100:.1f}%")
    return (f"shadow tracks {d} (base 100 on {min(r['date'] for r in rows)}): v2 {nav['v2']:.2f}, "
            f"fast-cut {nav['fastcut']:.2f}, 19 Sep {nav['sep19']:.2f} -- revert rule: {rc['verdict']}"
            + (f" ({extra})" if extra else ''))
