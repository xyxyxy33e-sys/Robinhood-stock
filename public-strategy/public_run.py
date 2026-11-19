"""Public.com taxable account (5OG87042) strategy: every calculation for the 10:00 brief and the 15:50 trade run.

    python3 public-strategy/public_run.py brief  <input.json>    # read-only, prints a PUSH line
    python3 public-strategy/public_run.py signal <input.json>    # prints the decision and the orders

DESIGN (owner request 2026-11-19; STRATEGY-PUBLIC.md). ETFs only, none shared with the Robinhood strategy
(SPY TQQQ QLD QQQ VIXY XLU) or the IRA (SPMO); BOXX, the cash fund, is shared with Robinhood on purpose:
  TREND sleeve 50%:    SSO (2x S&P 500) while SPY's adjusted close is above its 200-day average, 1% hysteresis
                       (in above +1%, out below -1%); otherwise IEF. Read every day at 15:50 on the live price.
  ROTATION sleeve 50%: the 2 strongest of VTI EFA EEM TLT GLD DBC VNQ by 6-month total return at the last completed
                       month-end close, 25% each; a pick that does not beat T-bills over the same 6 months is held
                       in BOXX instead. Changes take effect at the first 15:50 run of the new month.
  TRADE when a target holding is missing, a non-target holding is still held, or L1 drift exceeds 20%.
  Otherwise hold (no calendar rebalancing: fewer taxable sales).
The strategy manages ONLY its own tickers (UNIVERSE) plus positive cash; every other position in the account is
ignored. data/public/config.json: {"enabled": false} = dry run (orders printed, never placed); "max_capital" caps
the dollars the strategy may deploy. SPY is read as a signal only and never traded here.

Input JSON: {"date","time","quotes":{SYM:{"last","bid","ask"}} for UNIVERSE + SPY, "positions":{SYM:qty},"cash":x}
Exit codes: 0 ok, 2 guard (do not trade), 3 market closed.
"""
import csv, datetime as dt, json, math, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
CONFIG = os.path.join(ROOT, 'data', 'public', 'config.json')
RUNS = os.path.join(ROOT, 'data', 'public', 'runs')
ROT = ('VTI', 'EFA', 'EEM', 'TLT', 'GLD', 'DBC', 'VNQ')
CASH = 'BOXX'    # cash slot (owner 2026-11-19: BOXX, not SGOV -- its return is a capital gain that losses can offset)
UNIVERSE = ('SSO', 'IEF') + ROT + (CASH,)
FORBIDDEN = ('SPY', 'TQQQ', 'QLD', 'QQQ', 'VIXY', 'VIXM', 'XLU', 'SPMO')   # the other two strategies (BOXX is shared on purpose)
HYST, DRIFT_BAND, DUST, LIMIT_BAND = 0.01, 0.20, 0.005, 0.003
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
assert not set(UNIVERSE) & set(FORBIDDEN)


class Guard(RuntimeError):
    pass


def history(sym):
    """{date: (adjclose, close)} for ~2 years, completed sessions and today's partial bar if Yahoo has it."""
    u = f"https://query2.finance.yahoo.com/v8/finance/chart/{sym}?range=2y&interval=1d&events=div"
    r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read())['chart']['result'][0]
    off = r['meta'].get('gmtoffset', 0) or 0
    q = r['indicators']['quote'][0]['close']; a = r['indicators']['adjclose'][0]['adjclose']
    return {dt.datetime.utcfromtimestamp(t + off).date().isoformat(): (x, c) for t, x, c in zip(r['timestamp'], a, q) if x and c}


def adj_series(sym, today, last):
    """Adjusted closes before today, plus today's live price on the same adjusted scale."""
    h = {d: v for d, v in history(sym).items() if d < today}
    if len(h) < 260:
        raise Guard(f'{sym}: only {len(h)} sessions of history')
    ds = sorted(h); pa, pc = h[ds[-1]]
    if (dt.date.fromisoformat(today) - dt.date.fromisoformat(ds[-1])).days > 5:
        raise Guard(f'{sym}: history ends {ds[-1]}, stale')
    out = {d: h[d][0] for d in ds}; out[today] = pa * float(last) / pc
    return out


def trend_on(spy, today):
    ds = [d for d in sorted(spy) if d <= today]; on = None; gap = None
    for i in range(199, len(ds)):
        sma = sum(spy[x] for x in ds[i - 199:i + 1]) / 200; gap = spy[ds[i]] / sma - 1
        on = (gap > HYST) if on is None else ((gap > -HYST) if on else (gap > HYST))
    return on, gap, sma


def tbill_6m(sgov, a, b):
    return sgov[b] / sgov[a] - 1


def rotation(series, sgov, today):
    """Picks from the last completed month-end close before today's month."""
    ds = [d for d in sorted(series['VTI']) if d < today]
    ends = [d for i, d in enumerate(ds[:-1]) if d[:7] != ds[i + 1][:7]]
    if ds and ds[-1][:7] != today[:7]:
        ends.append(ds[-1])
    if len(ends) < 7:
        raise Guard('rotation: fewer than 7 month-ends of history')
    e, s = ends[-1], ends[-7]
    hurdle = tbill_6m(sgov, s, e)
    mom = sorted(((series[x][e] / series[x][s] - 1, x) for x in ROT), reverse=True)
    picks = [(x if m > hurdle else CASH) for m, x in mom[:2]]
    return picks, mom, hurdle, e


def targets(on, picks):
    w = {s: 0.0 for s in UNIVERSE}
    w['SSO' if on else 'IEF'] += 0.5
    for p in picks:
        w[p] += 0.25
    return w


def compute(inp, need_account=True):
    today, q = inp['date'], inp['quotes']
    cfg = json.load(open(CONFIG)) if os.path.exists(CONFIG) else {'enabled': False}
    spy = adj_series('SPY', today, q['SPY']['last'])
    series = {s: adj_series(s, today, q[s]['last']) for s in ROT}
    sgov = adj_series(CASH, today, q[CASH]['last'])
    on, gap, sma = trend_on(spy, today)
    picks, mom, hurdle, asof = rotation(series, sgov, today)
    w = targets(on, picks)
    out = dict(date=today, time=inp.get('time'), trend_on=on, gap200=gap, spy_sma200_adj=sma, picks=picks,
               rotation_asof=asof, momentum=[(x, m) for m, x in mom], hurdle=hurdle, target=w, enabled=bool(cfg.get('enabled')))
    if not need_account:
        return out, cfg
    pos = {s: float(v) for s, v in inp.get('positions', {}).items()}
    bad = [s for s in pos if s in FORBIDDEN and pos[s] > 0]
    if bad:
        raise Guard(f'account holds tickers reserved for the other strategies: {bad}')
    val = {s: pos.get(s, 0.0) * float(q[s]['last']) for s in UNIVERSE}
    cash = max(0.0, float(inp.get('cash', 0.0)))
    total = sum(val.values()) + cash
    cap = cfg.get('max_capital')
    if cap is not None and total > float(cap) * 1.25 and sum(val.values()) < 1:
        total = float(cap)                         # first deployment: never more than the cap
    out.update(values=val, cash=cash, total=total)
    if total < 500:
        out.update(decision=False, why=f'strategy capital ${total:,.2f} (its own ETFs + positive cash) is below $500: nothing to trade', orders=[])
        return out, cfg
    held = {s: val[s] / total for s in UNIVERSE}
    drift = sum(abs(w[s] - held[s]) for s in UNIVERSE)
    missing = [s for s in UNIVERSE if w[s] > 0 and held[s] < DUST]
    extra = [s for s in UNIVERSE if w[s] == 0 and held[s] >= DUST]
    do = bool(missing or extra or drift > DRIFT_BAND)
    why = (f"target not held: {missing}" if missing else f"non-target held: {extra}" if extra else
           f"drift {drift:.1%} > {DRIFT_BAND:.0%}" if do else f"holdings match the targets (drift {drift:.1%})")
    orders = []
    if do:
        for s in UNIVERSE:                           # sells first
            d = w[s] * total - val[s]
            if d < -max(25.0, 0.002 * total):
                px = float(q[s]['bid'] or q[s]['last']); lim = max(px, float(q[s]['last']) * (1 - LIMIT_BAND))
                qty = pos.get(s, 0.0) if w[s] == 0 else math.floor(-d / px)
                if qty > 0:
                    orders.append(dict(side='SELL', symbol=s, quantity=round(qty, 6), limit=math.floor(lim * 100) / 100, dollars=qty * px))
        for s in UNIVERSE:
            d = w[s] * total - val[s]
            if d > max(25.0, 0.002 * total):
                px = float(q[s]['ask'] or q[s]['last']); lim = min(px, float(q[s]['last']) * (1 + LIMIT_BAND))
                qty = math.floor(d / lim)
                if qty > 0:
                    orders.append(dict(side='BUY', symbol=s, quantity=qty, limit=math.ceil(lim * 100) / 100, dollars=qty * lim))
    out.update(held=held, drift=drift, decision=do, why=why, orders=orders)
    return out, cfg


def describe(w):
    return ' / '.join(f"{s} {x:.0%}" for s, x in w.items() if x > 0)


def main(argv):
    if len(argv) != 3 or argv[1] not in ('brief', 'signal'):
        print(__doc__); return 1
    inp = json.load(open(argv[2])); q = inp['quotes']
    if q['SPY'].get('last_trade_date') and q['SPY']['last_trade_date'] != inp['date']:
        print(f"MARKET CLOSED: SPY last trade {q['SPY']['last_trade_date']} != {inp['date']}. No action."); return 3
    try:
        out, cfg = compute(inp)
    except Guard as e:
        print(f'GUARD: {e}'); return 2
    g = out['gap200']
    print(f"=== Public strategy {out['date']} {out.get('time') or ''} ===")
    print(f"TREND: SPY {g:+.2%} vs its 200-day -> {'ON, SSO' if out['trend_on'] else 'OFF, IEF'} "
          f"(flips {'below -1%' if out['trend_on'] else 'above +1%'})")
    print(f"ROTATION (month-end {out['rotation_asof']}, hurdle {out['hurdle']:+.2%}): " +
          ', '.join(f"{x} {m:+.1%}" for x, m in out['momentum']) + f" -> {out['picks']}")
    print(f"target: {describe(out['target'])}")
    if 'held' in out:
        print(f"held:   {describe(out['held']) or 'nothing'}; strategy capital ${out['total']:,.2f} (cash ${out['cash']:,.2f})")
    print(f"DECISION: {'TRADE' if out['decision'] else 'NO TRADE'} ({out['why']})")
    for o in out['orders']:
        print(f"  {o['side']:4s} {o['symbol']:5s} {o['quantity']} sh  LIMIT {o['limit']:.2f}  (~${o['dollars']:,.2f})")
    if out['orders'] and not out['enabled']:
        print("DRY RUN: data/public/config.json has enabled=false. Do NOT place these orders.")
    if argv[1] == 'brief':
        spyq = q['SPY']; chg = f" {float(spyq['last']) / float(spyq['close']) - 1:+.1%}" if spyq.get('close') else ''
        push = (f"Public 10am: SPY {float(spyq['last']):.0f}{chg}, {g:+.1%} vs 200d | trend {'ON SSO' if out['trend_on'] else 'OFF IEF'}, "
                f"flips at {'-1%' if out['trend_on'] else '+1%'} | rotation {'+'.join(out['picks'])} | 3:50 "
                f"{'TRADE' if out['decision'] else 'no trade'} here" + ('' if out['enabled'] else ' (dry run)'))
        print('PUSH:', push[:199])
    else:
        os.makedirs(RUNS, exist_ok=True)
        json.dump(out, open(os.path.join(RUNS, out['date'] + '.json'), 'w'), indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
