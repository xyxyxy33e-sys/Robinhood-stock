"""live_run.py -- every computation a live Routine run needs, in code (2026-10-08).

The Routine prompts used to carry ~40k characters each of recipe that the model
re-derived at 15:5x. This script IS that recipe: it calls the same state.py /
tracker functions the prompts named, so it trades exactly what they traded,
and prints the decision, the orders and the report lines. The model only
fetches a handful of quotes, runs this, places the printed orders, and runs
the record step. RUNBOOK.md is the procedure; STRATEGY.md the design.

    python3 paper-track/live_run.py signal  data/runs/in/<date>.json   # 15:5x
    python3 paper-track/live_run.py record  data/runs/in/<date>-record.json   # after the close
    python3 paper-track/live_run.py check   data/runs/in/<date>-check.json   # same as signal, writes nothing
    python3 paper-track/live_run.py status  [<date>]                   # did today's run finish?

Exit codes: 0 ok, 2 GUARD tripped (do not trade), 3 market closed (stop).

signal input (all numbers straight from the MCP tools; see RUNBOOK.md):
  {"date": "YYYY-MM-DD",                      # today, US/Eastern
   "time": "15:51",                           # ET wall clock of the snapshot
   "quotes": {SYM: {"last": x, "bid": x, "ask": x,
                    "close": x, "close_date": "YYYY-MM-DD",   # official prior close
                    "last_trade_date": "YYYY-MM-DD"}}         # for QQQ QQEW SPMO TQQQ QLD XLU BOXX VIXM
   "vix": x,                                  # get_index_quotes VIX value
   "positions": {SYM: qty},                   # get_equity_positions quantity (0s may be omitted)
   "idle_cash": x, "total_value": x}          # get_portfolio cash / total_value
record input:
  {"date": ..., "closes": {SYM: last_trade_price after 16:00, for the 8 symbols},
   "fills": [{"symbol":, "side": "buy"|"sell", "quantity":, "price":}], "session_lag": 0,
   "total_value": x}
"""
import csv
import datetime
import json
import math
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import state as S                 # noqa: E402
import breadth_tracker as BT      # noqa: E402
import cash_sweep as CS           # noqa: E402
import deposit_plan as DP         # noqa: E402
import drawdown_tracker as DT     # noqa: E402
import fill_quality as FQ         # noqa: E402
import funding_policy as FP       # noqa: E402
import shadow_tracker as ST       # noqa: E402
import vol_curve as VC            # noqa: E402

ROOT = os.path.dirname(HERE)
CLOSES_CSV = os.path.join(ROOT, 'data', 'live_closes.csv')
RUNS_DIR = os.path.join(ROOT, 'data', 'runs')
LEGS6 = ('SPMO', 'TQQQ', 'QLD', 'XLU', 'VIXM', 'BOXX')     # == state.LIVE_LEGS order
LEGS5 = ('SPMO', 'TQQQ', 'QLD', 'XLU', 'BOXX')             # shadow tracks / old NAV
SYMS = ('QQQ', 'QQEW') + LEGS6
LIMIT_BAND = 0.003            # never more than 0.3% through the touch
YAHOO_DAILY = "https://query2.finance.yahoo.com/v8/finance/chart/{sym}?range=1y&interval=1d"


class Guard(RuntimeError):
    """A safety guard tripped: report, do not trade (exit code 2)."""


# ------------------------------------------------------------------ closes cache
def load_closes(path=CLOSES_CSV):
    out = {s: {} for s in SYMS}
    with open(path) as f:
        for r in csv.DictReader(f):
            for s in SYMS:
                v = r.get(s)
                if v not in (None, '', 'nan'):
                    out[s][r['date']] = float(v)
    return out


def save_closes(c, path=CLOSES_CSV):
    dates = sorted(set().union(*[set(v) for v in c.values()]))
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['date'] + list(SYMS))
        for d in dates:
            w.writerow([d] + [('%.4f' % c[s][d]) if d in c[s] else '' for s in SYMS])


def _yahoo(sym):
    req = urllib.request.Request(YAHOO_DAILY.format(sym=sym), headers=VC.UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        res = json.loads(r.read().decode())['chart']['result'][0]
    out = {}
    for t, c in zip(res['timestamp'], res['indicators']['quote'][0]['close']):
        if c is not None:      # split-adjusted, NOT dividend-adjusted == Robinhood adjustment_type='split'
            d = datetime.datetime.fromtimestamp(t, datetime.timezone(datetime.timedelta(hours=-5))).date()
            out[d.isoformat()] = round(float(c), 4)
    return out


def ensure_history(c, prev_session, notes):
    """QQQ and QQEW must have every session up to prev_session. Fill gaps (missed
    runs, weekends of no runs) from Yahoo; raise Guard if still missing."""
    for s in ('QQQ', 'QQEW') + LEGS6:
        if prev_session in c[s]:
            continue
        try:
            y = _yahoo(s)
            n = 0
            for d, v in y.items():
                if d <= prev_session and d not in c[s]:
                    c[s][d] = v
                    n += 1
            notes.append(f'{s}: filled {n} missing closes from Yahoo')
        except Exception as e:   # noqa: BLE001
            notes.append(f'{s}: Yahoo gap-fill failed ({e})')
    for s in ('QQQ', 'QQEW'):
        if prev_session not in c[s]:
            raise Guard(f'{s} has no close for the prior session {prev_session}: pull get_equity_historicals '
                        f'and add it to data/live_closes.csv, then re-run')


# ------------------------------------------------------------------ readings
def reading(dates, qqq, qqew, as_of):
    """Every step-1 input for one session, from the given closes series."""
    i = dates.index(as_of)
    state = S.compute_states(dates, qqq)[i]
    fast = S.compute_fast_states(dates, qqq)[as_of]
    gaps = S.compute_extension_gaps(dates, qqq)[as_of]
    micro = S.compute_micro_agreement(dates, qqq)[as_of]
    vol = S.realized_vol_live(dates, qqq, as_of=as_of)
    cd = [d for d in dates if d in qqew]
    br = BT.breadth_reading(cd, qqew, qqq, as_of=as_of)
    if br['pct'] is None:
        raise Guard(f'breadth pct is None for {as_of}: too little QQEW history')
    a_trim = S.a_trim_state(dates, qqq, as_of=as_of)
    eff = S.effective_state(state, fast)
    return dict(date=as_of, state=state, fast=fast, eff=eff, gaps=gaps, micro=micro, vol=vol,
                mult=S.vol_target_multiplier(vol), breadth_pct=br['pct'], x60=br['x60'],
                d_flags=S.d_gate_flags(br['pct'], gaps[200]),
                d_gate=S.d_gate_active(state, br['pct'], gaps[200]),
                raw_votes=S.extension_votes(eff, gaps), a_trim=a_trim)


def weights5(r):
    return S.live_target_weights(r['state'], r['micro'], r['vol'], r['fast'], r['gaps'],
                                 r['breadth_pct'], r['a_trim'])


def weights6(r, vx):
    return S.live_target_weights_with_vixm(r['state'], r['micro'], r['vol'], r['fast'], r['gaps'],
                                           r['breadth_pct'], r['a_trim'], vx)


def vixm_pair(dates, qqq, today, prev, vix_now, notes):
    """(today's vixm input, prior session's, note). Never raises: a data failure
    becomes vixm_unavailable (VIXM 0%, reported)."""
    try:
        vix, vix3m, note = VC.load_vix_inputs(today, vix_now)
        vx = S.vixm_state(dates, qqq, vix, vix3m, as_of=today)
        vh = {d: v for d, v in vix.items() if d != today}
        v3h = {d: v for d, v in vix3m.items() if d != today}
        vx_prev = S.vixm_state(dates[:-1], qqq, vh, v3h, as_of=prev)
        return vx, vx_prev, note
    except Exception as e:   # noqa: BLE001
        notes.append(f'VIXM inputs unavailable: {e}')
        u = S.vixm_unavailable(e)
        return u, u, f'UNAVAILABLE: {e}'


# ------------------------------------------------------------------ orders
def cents_up(x):
    """Round a price up to the cent. round() first, so a quote like 152.33 (152.33*100 =
    15233.000000000002 in floating point) stays 152.33 instead of becoming 152.34."""
    return math.ceil(round(x * 100, 6)) / 100


def cents_down(x):
    return math.floor(round(x * 100, 6)) / 100


def plan_orders(target, values, qty, quotes, tv, res=0.0):
    """Dollar targets -> concrete orders, sells first. Whole shares as marketable
    limits (sell at the bid, buy at the ask, capped 0.3% through the last), the
    fractional remainder as a regular-hours dollar-based market order; a leg
    going to 0% is a market sell of the full quantity."""
    tgt = DP.dollar_targets(target, tv, res)
    sells, buys = [], []
    for sym in LEGS6:
        delta = tgt[sym] - values.get(sym, 0.0)
        if abs(delta) < 1.0:
            continue
        q = quotes[sym]
        last = q['last']
        if delta < 0:
            px = cents_up(max(q.get('bid') or last, last * (1 - LIMIT_BAND)))   # never below the cap
            if tgt[sym] < 1.0:          # leg to 0%: whole shares as a limit, the fractional stub at market
                held_q = qty.get(sym, 0.0)
                sh = math.floor(held_q)
                if sh:
                    sells.append(dict(symbol=sym, side='sell', kind='limit', quantity=sh, limit=px,
                                      dollars=round(sh * px, 2)))
                stub = round(held_q - sh, 6)
                if stub > 0:
                    sells.append(dict(symbol=sym, side='sell', kind='market_qty', quantity=stub,
                                      note='fractional stub of a 0% leg (market, regular hours)'))
                continue
            sh = math.floor(-delta / px)
            if sh:
                sells.append(dict(symbol=sym, side='sell', kind='limit', quantity=sh, limit=px,
                                  dollars=round(sh * px, 2)))
            rest = -delta - sh * px
            if rest >= 1.0:
                sells.append(dict(symbol=sym, side='sell', kind='market_dollars', dollars=round(rest, 2)))
        else:
            px = cents_down(min(q.get('ask') or last, last * (1 + LIMIT_BAND)))  # never above the cap
            sh = math.floor(delta / px)
            if sh:
                buys.append(dict(symbol=sym, side='buy', kind='limit', quantity=sh, limit=px,
                                 dollars=round(sh * px, 2)))
            rest = delta - sh * px
            if rest >= 1.0:
                buys.append(dict(symbol=sym, side='buy', kind='market_dollars', dollars=round(rest, 2)))
    return sells + buys


# ------------------------------------------------------------------ helpers
def _fmt_w(w):
    return ' / '.join(f'{l} {x * 100:.1f}%' for l, x in zip(LEGS6, w))


def _ser(x):
    if isinstance(x, tuple):
        return list(x)
    if isinstance(x, dict):
        return {str(k): _ser(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_ser(v) for v in x]
    return x


def _run_path(date):
    os.makedirs(RUNS_DIR, exist_ok=True)
    return os.path.join(RUNS_DIR, f'{date}.json')


def _load_run(date):
    p = _run_path(date)
    return json.load(open(p)) if os.path.exists(p) else None


def _restore_reading(r):
    r = dict(r)
    r['gaps'] = {int(k): v for k, v in r['gaps'].items()}
    at = dict(r['a_trim'])
    at['base'] = tuple(at['base']) if at.get('base') else None
    r['a_trim'] = at
    r['d_flags'] = tuple(r['d_flags'])
    return r


# ------------------------------------------------------------------ signal
def cmd_signal(inp, write=True):
    today = inp['date']
    q = inp['quotes']
    notes, lines, pushes = [], [], []
    if q['QQQ'].get('last_trade_date') != today:
        print(f"MARKET CLOSED: QQQ last trade {q['QQQ'].get('last_trade_date')} != {today}. No action.")
        return 3
    prev = q['QQQ']['close_date']

    # closes: record the official prior closes carried by the quotes, fill gaps, append today's snapshot
    c = load_closes()
    for s in SYMS:
        if s in q and q[s].get('close') and q[s].get('close_date'):
            c[s][q[s]['close_date']] = float(q[s]['close'])
    ensure_history(c, prev, notes)
    if write:
        save_closes(c)
    qqq = {d: v for d, v in c['QQQ'].items() if d < today}
    qqew = {d: v for d, v in c['QQEW'].items() if d < today}
    qqq[today], qqew[today] = float(q['QQQ']['last']), float(q['QQEW']['last'])
    dates = sorted(qqq)

    r = reading(dates, qqq, qqew, today)
    rp = reading(dates[:-1], {d: v for d, v in qqq.items() if d != today},
                 {d: v for d, v in qqew.items() if d != today}, prev)
    vx, vx_prev, vnote = vixm_pair(dates, qqq, today, prev, float(inp['vix']), notes)

    # account
    qty = {s: float(inp['positions'].get(s, 0.0)) for s in LEGS6}
    extra = {s: v for s, v in inp['positions'].items() if s not in LEGS6 and float(v) > 0}
    values = {s: qty[s] * float(q[s]['last']) for s in LEGS6}
    idle, tv = float(inp['idle_cash']), float(inp['total_value'])
    implied = sum(values.values()) + idle
    plan = DP.load()
    plan_active = DP.active(plan)

    out = dict(date=today, time=inp.get('time'), prev=prev, notes=notes, reading=_ser(r), prev_reading=_ser(rp),
               vixm=_ser(vx), vixm_prev=_ser(vx_prev), vixm_note=vnote, quotes=q, positions=inp['positions'],
               idle_cash=idle, total_value=tv)
    code = 0
    try:
        if extra:
            raise Guard(f'positions outside the strategy legs: {extra} -- ask the owner (XLU/IAU dust is sold by '
                        f'the band; anything else is not this strategy)')
        S.circuit_breaker_check(tv, implied)
        w6 = weights6(r, vx)
        S.validate_weights_live(r['state'], *w6)
        if plan_active:
            sess = dates
            if idle > DP.ARRIVAL_MIN:
                raise Guard('deposit plan active and idle cash present: follow STRATEGY.md "Staged deposit" '
                            'arrival step by hand, then re-run')
            res = DP.reserve(plan, sess, today)
            held = DP.held_weights(values, idle, tv, res, with_vixm=True)
            lines.append(DP.summary_line(plan, sess, today))
        else:
            res = 0.0
            held = tuple(values[s] / tv for s in LEGS6[:-1]) + ((values['BOXX'] + idle) / tv,)
        w6_prev = weights6(rp, vx_prev)
        changed = []
        if r['eff'] != rp['eff']:
            changed.append(f"effective state {rp['eff']}->{r['eff']}")
        if r['a_trim']['held'] != rp['a_trim']['held']:
            changed.append(f"held trim votes {rp['a_trim']['held']}->{r['a_trim']['held']}")
        if r['d_gate'] != rp['d_gate']:
            changed.append(f"D gate {'on' if r['d_gate'] else 'off'}")
        if bool(vx.get('allowed')) != bool(vx_prev.get('allowed')):
            changed.append(f"VIXM {'in' if vx.get('allowed') else 'out'}")
        do, drift, why = S.needs_rebalance(w6, held, bool(changed))
        orders = plan_orders(w6, values, qty, q, tv, res) if do else []
        sweep = {}
        if not do:
            sweep, swhy = CS.plan_sweep(w6, {s: values[s] for s in LEGS6}, idle, tv, plan_active=plan_active)
            if sweep:
                lines.append(f'idle-cash sweep (${idle:,.2f}): ' + ', '.join(f'{k} ${v:,.2f}' for k, v in sweep.items()))
        # push events (RUNBOOK: exactly these)
        if r['state'] != rp['state']:
            pushes.append(f"Regime shift: macro {rp['state']} -> {r['state']} ({S.STATE_LABEL[r['state']]})")
        if rp['eff'] in 'DEF' and r['eff'] in 'ABC':
            amt = FP.turn_funding_amount(tv)
            pushes.append(f"FUNDING TRIGGER (turn): effective {rp['eff']} -> {r['eff']}; account ${tv:,.0f}; "
                          f"suggested deposit ${amt:,.0f}")
        out.update(target=list(w6), target_prev=list(w6_prev), held=list(held), drift=drift, decision=do,
                   why=why, regime_changed=changed, orders=orders, sweep=sweep, pushes=pushes, status='signal')
    except (Guard, S.WeightSanityError, S.CircuitBreakerTripped, S.MissingOverlayInputs) as e:
        out.update(status='guard', guard=f'{type(e).__name__}: {e}')
        code = 2

    if write:
        out['input'] = inp
        json.dump(_ser(out), open(_run_path(today), 'w'), indent=1)
    else:
        print('(check mode: nothing written)')

    # ---- report
    vz = vx if vx.get('available') else {}
    print(f"=== {today} {inp.get('time', '')} ET snapshot (15:5x proxy for the close) ===")
    prev_eff = '' if r['eff'] == rp['eff'] else f"  [prev effective {rp['eff']}]"
    print(f"macro {r['state']} ({S.STATE_LABEL[r['state']]}), fast {r['fast']}, effective {r['eff']}{prev_eff}")
    g = r['gaps']
    print(f"gaps 100/150/200: {g[100]*100:+.1f}% / {g[150]*100:+.1f}% / {g[200]*100:+.1f}%; trim votes raw "
          f"{r['raw_votes']} held {r['a_trim']['held']} (prev {rp['a_trim']['held']}); A spell from "
          f"{r['a_trim']['spell_start']}, base {r['a_trim']['base']}")
    bf, gf = r['d_flags']
    print(f"breadth pct {r['breadth_pct']:.2f}, 200d gap {g[200]*100:+.1f}%, D gate "
          f"{'ON (' + ('both' if bf and gf else 'breadth' if bf else 'gap200') + ')' if r['d_gate'] else 'off'}"
          f"{'' if r['state'] == 'D' else ' (informational outside D)'}")
    print(f"QQQ 30d vol {r['vol']*100:.1f}% -> multiplier {r['mult']:.3f}")
    print(f"VIXM: {vnote}")
    if vz:
        hi = f", VIX high since entry {vz['vix_high']:.2f}" if vz.get('vix_high') else ''
        print(f"      latch {'ON' if vz['on'] else 'off'}, stress {'yes' if vz['stress'] else 'no'}, "
              f"allowed {'YES' if vz['allowed'] else 'no'}{', faded' if vz.get('faded') else ''}{hi}")
    for n in notes:
        print(f"note: {n}")
    for l in lines:
        print(l)
    if code:
        print(f"\nGUARD TRIPPED -- DO NOT TRADE: {out['guard']}")
        return code
    print(f"\naccount ${tv:,.2f} (positions+cash ${implied:,.2f}, breaker ok)")
    print(f"target: {_fmt_w(out['target'])}")
    print(f"held:   {_fmt_w(out['held'])}")
    print(f"L1 drift {drift*100:.2f}%; regime change: {', '.join(changed) or 'none'}")
    if do:
        print(f"\nDECISION: TRADE ({why}). Place in this order, sells first:")
        for o in orders:
            if o['kind'] == 'limit':
                print(f"  {o['side'].upper():4} {o['symbol']:5} {o['quantity']:>8} sh  LIMIT {o['limit']:.2f}  (~${o['dollars']:,.2f})")
            elif o['kind'] == 'market_dollars':
                print(f"  {o['side'].upper():4} {o['symbol']:5} ${o['dollars']:,.2f}  MARKET dollar-based (regular hours)")
            else:
                print(f"  SELL {o['symbol']:5} {o['quantity']} sh  MARKET (regular hours) -- {o['note']}")
        if any(o['symbol'] == 'VIXM' for o in orders):
            print("  VIXM: regular hours ONLY (no extended-hours trading); it must fill now or wait for the next open.")
    else:
        print(f"\nDECISION: NO TRADE ({why})")
        if sweep:
            print("  idle-cash sweep: dollar-based market BUYs: " + ', '.join(f'{k} ${v:,.2f}' for k, v in sweep.items()))
    for p in pushes:
        print(f"\nPUSH: {p}")
    return 0


# ------------------------------------------------------------------ record
def cmd_record(inp):
    date = inp['date']
    run = _load_run(date)
    closes = {s: float(v) for s, v in inp['closes'].items()}
    lag = int(inp.get('session_lag', 0))
    out_lines, pushes = [], []
    # 1. fills
    for f in inp.get('fills', []):
        row = FQ.record_fill(date, f['symbol'], f['side'], float(f['quantity']), float(f['price']),
                             closes[f['symbol']], session_lag=lag,
                             note=f.get('note', '' if lag == 0 else 'post-close fallback'))
        flag = '  <-- over 25bp' if abs(row['slippage_bps']) > FQ.SLIPPAGE_FLAG_BPS else ''
        out_lines.append(f"fill {f['side']} {f['symbol']} {f['quantity']} @ {f['price']}: {row['slippage_bps']:+.1f}bp{flag}")
    if inp.get('fills'):
        sm = FQ.summarize()
        out_lines.append(f"fill quality: {sm['n']} same-session fills, notional-weighted {sm['weighted_bps']}bp "
                         f"vs the 4bp model; {len(sm['flagged'])} over 25bp; {sm['n_lagged']} lagged fills")
    # 2. closes cache (provisional; the next signal run overwrites with the official close)
    c = load_closes()
    for s, v in closes.items():
        c[s][date] = v
    save_closes(c)
    # 3. NAV: the weights held into today (yesterday's target) x today's close-to-close returns
    prev = max(d for d in c['QQQ'] if d < date)
    pr = _load_run(prev)
    if pr and pr.get('target'):
        w_prev = pr['target']
    else:
        qqq = {d: v for d, v in c['QQQ'].items() if d <= prev}
        qqew = {d: v for d, v in c['QQEW'].items() if d <= prev}
        dts = sorted(qqq)
        rp = reading(dts, qqq, qqew, prev)
        vx = run['vixm_prev'] if run and run.get('vixm_prev') else S.vixm_unavailable('no run file')
        w_prev = list(weights6(rp, vx))
        out_lines.append(f'NAV weights for {prev} recomputed (no run file)')
    rets = {s: closes[s] / c[s][prev] - 1 for s in LEGS6 if c[s].get(prev)}
    daily = sum(w * rets.get(s, 0.0) for w, s in zip(w_prev, LEGS6))
    before = DT.load_log()
    after = DT.record_return(date, daily)
    dd = DT.current_drawdown(after)
    tier = DT.newly_crossed(before, after)
    out_lines.append(f"NAV {date}: strategy {daily*100:+.2f}%, index {after[-1][2]:.4f}, drawdown {dd[0]*100:.2f}% "
                     f"from {dd[1]}")
    tv = float(inp.get('total_value') or (run or {}).get('total_value') or 0)
    if tier:
        amt = FP.tier_funding_amount(tv, tier)
        pushes.append(f"FUNDING TRIGGER (drawdown): strategy crossed -{int(tier*100)}% from its 252-day high; "
                      f"account ${tv:,.0f}; suggested deposit ${amt:,.0f}")
    # 4. shadow tracks + breadth D log, on the inputs the book traded on
    if run and run.get('reading'):
        r = _restore_reading(run['reading'])
        ST.update(date, {s: closes[s] for s in LEGS5}, closes['QQQ'], r['state'], r['micro'], r['vol'],
                  r['fast'], r['gaps'], r['breadth_pct'], r['a_trim'])
        v = ST.revert_check()
        out_lines.append(ST.summary_line())
        if r['state'] == 'D':
            bf, gf = r['d_flags']
            BT.record_d_day(date, 'D', r['x60'], r['breadth_pct'], r['d_gate'],
                            note=f"gap200={r['gaps'][200]*100:+.1f}% gap_flag={gf} applied={r['d_gate']}")
        out_lines.append(f"revert check: {v}")
    else:
        out_lines.append('no signal run file for today: shadow tracks / breadth log NOT updated -- run signal first')
    try:
        prev_d = [x for x in BT._read(BT.LOG) if x['date'] == prev and not x['qld_next']]
        if prev_d:
            BT.fill_next_returns(prev, rets['QLD'], closes['QQQ'] / c['QQQ'][prev] - 1)
    except FileNotFoundError:
        pass
    if run:
        run['status'] = 'recorded'
        run['record'] = dict(fills=inp.get('fills', []), nav_return=daily, tier=tier, session_lag=lag)
        json.dump(_ser(run), open(_run_path(date), 'w'), indent=1)
    print('\n'.join(out_lines))
    for p in pushes:
        print(f"\nPUSH: {p}")
    print(f"\nNext: commit data/ (git add data && git commit -m '{date}: <state>, <traded|no trade>, NAV {daily*100:+.2f}%' && git push)")
    return 0


def cmd_status(date=None):
    date = date or datetime.date.today().isoformat()
    run = _load_run(date)
    if not run:
        print(f'{date}: NO RUN FILE -- the 15:50 signal run did not complete')
        return 1
    print(f"{date}: status {run['status']}; decision {'TRADE' if run.get('decision') else 'no trade'} "
          f"({run.get('why', run.get('guard', ''))}); orders {len(run.get('orders', []))}")
    return 0


def main(argv):
    os.chdir(ROOT)                # tracker logs use repo-relative paths
    if len(argv) < 2 or argv[1] not in ('signal', 'check', 'record', 'status'):
        print(__doc__)
        return 1
    if argv[1] == 'status':
        return cmd_status(argv[2] if len(argv) > 2 else None)
    inp = json.load(open(argv[2]))
    if argv[1] == 'record':
        return cmd_record(inp)
    return cmd_signal(inp, write=(argv[1] == 'signal'))


if __name__ == '__main__':
    sys.exit(main(sys.argv))
