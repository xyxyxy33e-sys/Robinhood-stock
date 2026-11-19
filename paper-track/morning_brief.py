"""Morning brief (RUNBOOK section 5, 10:00 ET): what the 15:50 trade run would do today.

    python3 paper-track/morning_brief.py <input.json>

The input is the same JSON the trade run writes in RUNBOOK 1.2, kept outside data/ (for example
/tmp/morning_<date>.json). READ-ONLY: nothing is written, nothing is traded. It reuses live_run's own
reading and weights, so the levels it prints are the live rules, not a re-derivation:

  1. now: today's reading and target at the morning price (as if 15:50 were now), and the decision;
  2. QQQ ladder: the same reading with QQQ (and QQEW, by the same %) moved -8%..+8% in 0.25% steps,
     VIX held at the morning level; prints the price at which the target changes;
  3. VIX ladder: the vol sleeve and the VIX-panic QQQ leg at VIX levels from the morning reading,
     QQQ held at the morning price.
The S&P 500 is reported only (it does not enter the rules): its level from the optional "spx" field
(index quote) and its move from SPY in the quotes (optional). The last line is the push text.
"""
import contextlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import live_run as L   # noqa: E402
import state as S      # noqa: E402
import vol_curve as VC  # noqa: E402

NAMES = L.LEGS


def _target(r, vx):
    return tuple(round(float(x), 4) for x in L.weights7(r, vx))


def _desc(w):
    parts = [f"{n} {x * 100:.0f}%" for n, x in zip(NAMES, w) if x >= 0.005]
    return ' / '.join(parts) or 'all cash'


def _held(inp):
    q = inp['quotes']
    v = [float(inp['positions'].get(n, 0.0)) * float(q[n]['last']) if n in q else 0.0 for n in NAMES]
    tot = sum(v) + float(inp.get('idle_cash', 0.0))
    return tuple(x / tot for x in v) if tot > 0 else tuple(0.0 for _ in NAMES)


def _label(r):
    s = r['eff']
    if s == 'D':
        s += ' gated (cash)' if r['d_gate'] else f" {r.get('d_zone') or ''}".rstrip()
    return s


def main(path):
    inp = json.load(open(path))
    today, q = inp['date'], inp['quotes']
    os.chdir(L.ROOT)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = L.cmd_signal(inp, write=False)
    out = buf.getvalue()
    if code == 3:
        print(out.strip())
        return 3
    decision = next((ln for ln in out.splitlines() if ln.startswith('DECISION')), 'DECISION: ?')

    notes = []
    c = L.load_closes()
    for s in L.SYMS:
        if s in q and q[s].get('close') and q[s].get('close_date'):
            c[s][q[s]['close_date']] = float(q[s]['close'])
    prev = q['QQQ']['close_date']
    L.ensure_history(c, prev, notes)
    base_q = {d: v for d, v in c['QQQ'].items() if d < today}
    base_e = {d: v for d, v in c['QQEW'].items() if d < today}
    q0, e0 = float(q['QQQ']['last']), float(q['QQEW']['last'])
    pc = float(q['QQQ']['close'])
    vix0 = float(inp['vix'])
    try:
        vix, vix3m, _ = VC.load_vix_inputs(today, vix0)
    except Exception as e:  # noqa: BLE001
        vix, vix3m = None, None
        notes.append(f'VIX inputs unavailable: {e}')

    def reading_at(px):
        qq, ee = dict(base_q), dict(base_e)
        qq[today], ee[today] = px, e0 * px / q0
        dates = sorted(qq)
        return L.reading(dates, qq, ee, today), dates, qq

    def vx_at(dates, qq, v):
        if vix is None:
            return S.vixm_unavailable('no VIX inputs')
        vv = dict(vix)
        vv[today] = v
        return S.vixm_state(dates, qq, vv, vix3m, as_of=today)

    r0, d0, qq0 = reading_at(q0)
    vx0 = vx_at(d0, qq0, vix0)
    w0 = _target(r0, vx0)
    print(out.rstrip())
    print()
    print(f"=== morning brief {today} {inp.get('time', '')} ET ===")
    print(f"QQQ {q0:.2f} ({(q0 / pc - 1) * 100:+.2f}% vs {pc:.2f}); VIX {vix0:.2f}; reading now: {_label(r0)}; "
          f"target {_desc(w0)}; {decision}")

    # QQQ ladder
    steps = [k / 4 for k in range(-32, 33)]
    rows = []
    for pct in steps:
        px = q0 * (1 + pct / 100)
        r, d, qq = reading_at(px)
        rows.append((pct, px, _label(r), _target(r, vx_at(d, qq, vix0))))
    i0 = steps.index(0.0)
    held = _held(inp)

    def trades(w):          # the band the trade run uses: L1 drift above 5%, or a regime change
        return sum(abs(a - b) for a, b in zip(w, held)) > S.REBALANCE_DRIFT_BAND
    lab0 = rows[i0][2]
    up = next((rw for rw in rows[i0 + 1:] if trades(rw[3])), None)
    dn = next((rw for rw in reversed(rows[:i0]) if trades(rw[3])), None)
    up_s = next((rw for rw in rows[i0 + 1:] if rw[2] != lab0), None)
    dn_s = next((rw for rw in reversed(rows[:i0]) if rw[2] != lab0), None)
    print('QQQ ladder (VIX held):')
    last = None
    for pct, px, lab, w in rows:
        key = (lab, tuple(n for n, x in zip(NAMES, w) if x >= 0.005))
        if key != last:
            print(f"  from {pct:+5.2f}% (${px:,.2f}): {lab}: {_desc(w)}")
            last = key

    # VIX ladder
    vrows = []
    if vix is not None:
        last = None
        print('VIX ladder (QQQ held):')
        for v in [12, 14, 16, 17, 18, 20, 22, 24, 25, 26, 28, 30, 32, 35, 40]:
            w = _target(r0, vx_at(d0, qq0, float(v)))
            if w != last:
                print(f"  VIX {v}: {_desc(w)}")
                last = w
            vrows.append((v, w))
    for n in notes:
        print('note:', n)

    def edge(rw, word):
        if not rw:
            return f"no change {word} within 8%"
        return f"{word} ${rw[1]:,.0f} ({rw[0]:+.1f}%) -> {rw[2]}: {_desc(rw[3])}"
    vup = next((v for v, w in vrows if v > vix0 and w != w0), None)
    vdn = next((v for v, w in reversed(vrows) if v < vix0 and w != w0), None)
    vtxt = ' / '.join(x for x in (f"VIX close >= ~{vup}: {_desc(dict(vrows)[vup])}" if vup else '',
                                  f"VIX <= ~{vdn}: {_desc(dict(vrows)[vdn])}" if vdn else '') if x) \
        or 'no VIX trigger from 12 to 40'

    def sedge(rs, rt):      # state change before the trade level: worth saying, it does not trade
        if rs and (not rt or abs(rs[0]) < abs(rt[0])):
            return f" (state {rs[2]} from ${rs[1]:,.0f}, no trade)"
        return ''
    dec = 'NO TRADE' if 'NO TRADE' in decision else ('TRADE' if 'TRADE' in decision else '?')
    spx = ''
    if 'SPY' in q and q['SPY'].get('close'):
        sp = float(q['SPY']['last']) / float(q['SPY']['close']) - 1
        lvl = f"{float(inp['spx']):,.0f} " if inp.get('spx') else ''
        spx = f", S&P 500 {lvl}({sp * 100:+.1f}%)"
    push = (f"10am: QQQ ${q0:,.2f} ({(q0 / pc - 1) * 100:+.1f}%){spx}, VIX {vix0:.1f}. Now {_label(r0)}, {_desc(w0)}: "
            f"{dec} if it closed here. Up: {edge(up, 'above')}{sedge(up_s, up)}. Down: {edge(dn, 'below')}{sedge(dn_s, dn)}. {vtxt}.")
    print('PUSH:', push)
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
