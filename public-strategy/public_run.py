"""Public.com taxable account (5OG87042) strategy: every calculation for the 10:00 brief and the 15:50 trade run.

    python3 public-strategy/public_run.py brief  <input.json>    # read-only, prints a PUSH line
    python3 public-strategy/public_run.py signal <input.json>    # prints the decision and the orders
    python3 public-strategy/public_run.py record <fills.json>    # after fills: ledger.json and realized.csv
    python3 public-strategy/public_run.py review <input.json>    # Friday after the close: weekly review, weekly.csv
    python3 public-strategy/public_run.py dash   <input.json> <outdir>   # status, holdings and tax CSVs for the dashboard

DESIGN (owner request 2026-11-19; STRATEGY-PUBLIC.md). ETFs only, none shared with the Robinhood strategy
(SPY TQQQ QLD QQQ VIXY XLU) or the IRA (SPMO); BOXX, the cash fund, is shared with Robinhood on purpose:
  TREND sleeve 50%:    SSO (2x S&P 500) while SPY's adjusted close is above its 200-day average, 2% hysteresis
                       (in above +2%, out below -2%; owner 2026-11-20, was 1%); otherwise IEF. Read every day at 15:50 on the live price.
                       Fallback filter (owner 2026-11-19): IEF is held only if its 6-month total return at the last
                       completed month-end beats T-bills (the rotation's own test); otherwise the trend half is in BOXX.
                       VIX-panic leg (owner 2026-11-20): while the trend is off and the VIX latch is on (a close at or
                       above 30 turns it on, a close below 25 off; today's live VIX counts as today's close, and stays the
                       reading for that day on later runs, from data/public/runs/), 50% of the
                       trend half (owner 2026-11-24; 25% before) is 1x S&P: SSO 12.5% of the strategy, fallback 25%, BOXX 12.5%.
                       SSO volatility target (owner 2026-11-20): while the trend is on, SSO is scaled by
                       min(1, 30% / (2 x S&P vol)) in quarter steps (floor one quarter), S&P vol = the larger of the
                       10- and 30-session figures; the rest of the trend half sits in BOXX. A step change trades;
                       a step holds until the reading is 0.025 past its boundary (no flicker).
  ROTATION sleeve 50%: the 2 strongest of VTI EFA EEM TLT GLD DBC VNQ by 6-month total return at the last completed
                       month-end close, 25% each; a pick that does not beat T-bills over the same 6 months is held
                       in BOXX instead. Changes take effect at the first 15:50 run of the new month.
  TRADE when a target holding is missing, a non-target holding is still held, or L1 drift exceeds 20%.
  Otherwise hold (no calendar rebalancing: fewer taxable sales).
The strategy manages ONLY the shares and cash in its own ledger (data/public/ledger.json, updated with `record`
after every fill); the rest of the account, including the autopilot basket and its BOXX, is ignored.
data/public/config.json: {"enabled": false} = dry run (orders printed, never placed); "max_capital" is the
starting cash of the ledger. SPY is read as a signal only and never traded here.

Input JSON: {"date","time","quotes":{SYM:{"last","bid","ask"}} for UNIVERSE + SPY, "positions":{SYM:qty},"cash":x,
             "vix":x (optional), "tax_lots":{SYM:[broker lots]} (only when the run asks for it)}
Sells name the tax lots to use, highest cost first, from all the account's lots of that ticker (owner 2026-11-20).
Exit codes: 0 ok, 2 guard (do not trade), 3 market closed.
"""
import csv, datetime as dt, json, math, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
CONFIG = os.path.join(ROOT, 'data', 'public', 'config.json')
RUNS = os.path.join(ROOT, 'data', 'public', 'runs')
LEDGER = os.path.join(ROOT, 'data', 'public', 'ledger.json')
REALIZED = os.path.join(ROOT, 'data', 'public', 'realized.csv')
DAILY = os.path.join(ROOT, 'data', 'public', 'daily.csv')
FLOWS = os.path.join(ROOT, 'data', 'public', 'flows.csv')
DIVS = os.path.join(ROOT, 'data', 'public', 'dividends.csv')
IDLE_CASH_MAX = 0.01            # dividend cash waits for the next regular trade unless idle cash passes 1% of the strategy
WEEKLY = os.path.join(ROOT, 'data', 'public', 'weekly.csv')
ROT = ('VTI', 'EFA', 'EEM', 'TLT', 'GLD', 'DBC', 'VNQ')
CASH = 'BOXX'    # cash slot (owner 2026-11-19: BOXX, not SGOV -- its return is a capital gain that losses can offset)
UNIVERSE = ('SSO', 'IEF') + ROT + (CASH,)
FORBIDDEN = ('SPY', 'TQQQ', 'QLD', 'QQQ', 'VIXY', 'VIXM', 'XLU', 'SPMO')   # the other two strategies (BOXX is shared on purpose)
HYST, DRIFT_BAND, DUST, LIMIT_BAND = 0.02, 0.20, 0.005, 0.003   # HYST: 2% since 2026-11-20 (owner), 1% before
QTY_DP = 4                      # order quantities: fractional shares to 4 decimals
PANIC_ON, PANIC_OFF, PANIC_SHARE = 30.0, 25.0, 0.50      # share 25% -> 50% (owner 2026-11-24)
VOL_TARGET = 0.30      # owner 2026-11-20: SSO volatility target; None switches it off
VT_BUFFER = 0.025      # owner 2026-11-20: buffer on the volatility-target steps (0 = none)
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


def sso_scale(spy, today):
    """SSO volatility target (owner 2026-11-20), used only while the trend is on: the share of the trend half held
    in SSO follows raw = 30% / (2 x S&P vol) in quarter steps, never below a quarter; S&P vol is the larger of the
    10- and 30-session annualized volatility of SPY's adjusted log returns, today's live price included.
    Step buffer (owner 2026-11-20): the step moves down only when raw is more than VT_BUFFER below the boundary
    under the current step, and up only when raw is more than VT_BUFFER above the boundary of the higher step, so a
    reading that sits on a boundary no longer flips the size every few days. The step is replayed from the price
    history; yesterday's step is taken from yesterday's 15:50 run file when there is one. Returns (scale, vol)."""
    ds = [d for d in sorted(spy) if d <= today]
    lr = [math.log(spy[b] / spy[a]) for a, b in zip(ds[:-1], ds[1:])]
    sd = lambda x: (sum((v - sum(x) / len(x)) ** 2 for v in x) / (len(x) - 1)) ** 0.5
    def vol_at(k):                               # k = index into ds; uses the 30 returns ending at ds[k]
        w = lr[k - 30:k]
        return max(sd(w[-10:]), sd(w)) * 252 ** 0.5
    def move(cur, vol):
        if not VOL_TARGET or vol <= 0:
            return 1.0
        raw = VOL_TARGET / (2 * vol); tgt = max(0.25, round(min(1.0, raw) * 4) / 4)
        if tgt < cur and raw < cur - 0.125 - VT_BUFFER:
            return tgt
        if tgt > cur and raw > tgt - 0.125 + VT_BUFFER:
            return tgt
        return cur
    cur = 1.0
    for k in range(31, len(ds) - 1):
        cur = move(cur, vol_at(k))
    prev = last_run(today)
    if prev and len(ds) > 1 and prev[0] == ds[-2] and prev[1].get('sso_scale') is not None:
        cur = float(prev[1]['sso_scale'])
    vol = vol_at(len(ds) - 1)
    return move(cur, vol), vol


def last_run(today):
    """(date, contents) of the most recent 15:50 run file before today, or None."""
    for f in sorted((x for x in (os.listdir(RUNS) if os.path.isdir(RUNS) else []) if x.endswith('.json') and x[:-5] < today), reverse=True):
        try:
            return f[:-5], json.load(open(os.path.join(RUNS, f)))
        except Exception:  # noqa: BLE001
            continue
    return None


def last_run_value(key, today):
    """The value of `key` in the most recent 15:50 run file before today, or None."""
    for f in sorted((x for x in (os.listdir(RUNS) if os.path.isdir(RUNS) else []) if x.endswith('.json') and x[:-5] < today), reverse=True):
        try:
            v = json.load(open(os.path.join(RUNS, f))).get(key)
        except Exception:  # noqa: BLE001
            continue
        if v is not None:
            return v
    return None


def vix_panic(today, vix_now=None):
    """(latch on?, VIX used today, note). Replays about 2 years of VIX closes, then today's reading.
    vix_now: the input's "vix" if given, else Yahoo's live ^VIX. If VIX cannot be read the leg is off and says so."""
    try:
        u = "https://query2.finance.yahoo.com/v8/finance/chart/%5EVIX?range=2y&interval=1d"
        r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read())['chart']['result'][0]
        off = r['meta'].get('gmtoffset', 0) or 0
        h = {dt.datetime.utcfromtimestamp(t + off).date().isoformat(): c
             for t, c in zip(r['timestamp'], r['indicators']['quote'][0]['close']) if c}
        live = r['meta'].get('regularMarketPrice')
    except Exception as e:  # noqa: BLE001
        return False, None, f'VIX unavailable ({e}): panic leg off'
    ds = sorted(d for d in h if d < today)
    if len(ds) < 250 or (dt.date.fromisoformat(today) - dt.date.fromisoformat(ds[-1])).days > 5:
        return False, None, 'VIX history short or stale: panic leg off'
    # A day the 15:50 run acted on keeps the VIX it used then, not the official close (owner 2026-11-20):
    # otherwise 30.1 at 15:50 and a 29.8 close would buy the leg today and sell it tomorrow.
    for f in (os.listdir(RUNS) if os.path.isdir(RUNS) else []):
        d = f[:-5]
        if f.endswith('.json') and d in h and d < today:
            try:
                v = json.load(open(os.path.join(RUNS, f))).get('vix')
            except Exception:  # noqa: BLE001
                v = None
            if v:
                h[d] = float(v)
    now = float(vix_now) if vix_now else (float(h[today]) if today in h else (float(live) if live else None))
    if now is None:
        return False, None, 'no VIX reading for today: panic leg off'
    on = False
    for v in [h[d] for d in ds] + [now]:
        on = (v >= PANIC_OFF) if on else (v >= PANIC_ON)
    return on, now, None


def load_ledger(cfg):
    """The strategy's own shares and cash. Before the first trade: no shares, cash = max_capital."""
    if os.path.exists(LEDGER):
        return json.load(open(LEDGER))
    if cfg.get('max_capital') is None:
        raise Guard('no ledger and no max_capital: the owner must set the starting capital')
    return {'positions': {}, 'cash': float(cfg['max_capital'])}


def flows():
    """[(date, amount)] of money the owner added to (+) or took out of (-) the strategy after the start."""
    return [(r['date'], float(r['amount'])) for r in csv.DictReader(open(FLOWS))] if os.path.exists(FLOWS) else []


def deposit(amount, note=''):
    """public_run.py deposit <dollars> [note]: the owner adds cash to the strategy (negative takes it out). Only the
    ledger's cash changes; the next trade run sees the drift and brings everything back to target. max_capital in
    the config becomes the total put in. Never run this without the owner's instruction in chat."""
    cfg = json.load(open(CONFIG)); led = load_ledger(cfg); amount = round(float(amount), 2)
    if led['cash'] + amount < -0.01:
        raise Guard(f"cannot take ${-amount:,.2f} out: the strategy's cash is ${led['cash']:,.2f}")
    led['cash'] = round(led['cash'] + amount, 2)
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=-5))).date().isoformat()
    new = not os.path.exists(FLOWS)
    with open(FLOWS, 'a', newline='') as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(['date', 'amount', 'note'])
        w.writerow([today, f'{amount:.2f}', note])
    json.dump(led, open(LEDGER, 'w'), indent=1)
    cfg['max_capital'] = round(float(cfg.get('max_capital') or 0) + amount, 2)
    json.dump(cfg, open(CONFIG, 'w'))
    print('LEDGER:', json.dumps(led)); print(f"TOTAL PUT IN: ${cfg['max_capital']:,.2f}")


def credit_dividends(inp):
    """Owner 2026-11-24: dividends are reinvested on the next strategy trading day. inp["dividends"] = the account's DIVIDEND
    rows from get_history ([{"id","symbol","amount","date"}]). Each new one on a strategy ETF is added to the
    ledger's cash (the strategy's share of the account's shares of that ETF, in case the autopilot holds it too),
    logged in data/public/dividends.csv; it is spent at the next regular trade (or the 1% idle-cash backstop). Called by `signal` only, when live."""
    cfg = json.load(open(CONFIG))
    if not cfg.get('enabled') or not inp.get('dividends'):
        return 0.0
    seen = {r['id'] for r in csv.DictReader(open(DIVS))} if os.path.exists(DIVS) else set()
    led = load_ledger(cfg); acct = inp.get('positions', {}); rows = []; got = 0.0
    for d in inp['dividends']:
        s = d.get('symbol')
        if d['id'] in seen or s not in UNIVERSE or float(d['amount']) <= 0:
            continue
        mine, total = float(led['positions'].get(s, 0.0)), float(acct.get(s, 0.0))
        share = min(1.0, mine / total) if total > 0 else 0.0
        amt = round(float(d['amount']) * share, 2); seen.add(d['id'])
        rows.append([d['id'], str(d.get('date', ''))[:10], s, f"{float(d['amount']):.2f}", f'{share:.4f}', f'{amt:.2f}']); got += amt
    if rows:
        new = not os.path.exists(DIVS)
        with open(DIVS, 'a', newline='') as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(['id', 'date', 'symbol', 'account_amount', 'strategy_share', 'strategy_amount'])
            w.writerows(rows)
        led['cash'] = round(led['cash'] + got, 2); led['reinvest'] = round(float(led.get('reinvest', 0.0)) + got, 2)
        json.dump(led, open(LEDGER, 'w'), indent=1)
        print(f"DIVIDENDS: ${got:,.2f} credited to the strategy (" + ', '.join(f'{r[2]} ${r[5]}' for r in rows) + ")")
    return got


def record(path):
    """public_run.py record <fills.json>: [{"side","symbol","quantity","price","lots"?}] of FILLED strategy orders.
    Updates the ledger (shares, cash, cost) and appends every sale to data/public/realized.csv. A sale's cost is
    the cost of the tax lots today's run named for it; with "lots":"default" (the order went without a lot
    instruction) or no run file it is the strategy's average cost, marked "average"."""
    cfg = json.load(open(CONFIG)); led = load_ledger(cfg); cost = led.setdefault('cost', {})
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=-5))).date().isoformat()
    run = os.path.join(RUNS, today + '.json')
    planned = {o['symbol']: o for o in (json.load(open(run)).get('orders', []) if os.path.exists(run) else [])
               if o['side'] == 'SELL' and o.get('tax_lots')}
    rows = []
    for f in json.load(open(path)):
        s = f['symbol']
        if s not in UNIVERSE:
            raise Guard(f"{s} is not a strategy ticker")
        buy = f['side'].upper() == 'BUY'; sgn = 1 if buy else -1
        qty, px = float(f['quantity']), float(f['price'])
        held = led['positions'].get(s, 0.0)
        if not buy and qty > held + 1e-6:
            raise Guard(f'fill would take the ledger negative: {f}')
        if buy:
            cost[s] = round(cost.get(s, 0.0) + qty * px, 2)
        else:
            avg = cost.get(s, 0.0) / held if held else px
            cost[s] = round(cost.get(s, 0.0) - avg * qty, 2)
            o = planned.get(s) if f.get('lots') != 'default' else None
            if o:                                        # lots named by the run: split the fill across them in order
                left = qty
                for x in o['tax_lots']:
                    t = min(float(x['quantity']), left); left -= t
                    if t > 1e-6:
                        days = (dt.date.fromisoformat(today) - dt.date.fromisoformat(x['open_date'])).days
                        rows.append([today, s, f'{t:g}', f'{t * px:.2f}', f'{t * x["unit_cost"]:.2f}',
                                     f'{t * (px - x["unit_cost"]):.2f}', 'LONG' if days > 365 else 'SHORT', 'lots'])
            else:
                rows.append([today, s, f'{qty:g}', f'{qty * px:.2f}', f'{qty * avg:.2f}', f'{qty * (px - avg):.2f}',
                             'UNKNOWN', 'average'])
        led['positions'][s] = round(held + sgn * qty, 6)
        led['cash'] = round(led['cash'] - sgn * qty * px, 2)
        if led['cash'] < -0.01:
            raise Guard(f'fill would take the ledger cash negative: {f}')
    led['positions'] = {s: v for s, v in led['positions'].items() if abs(v) > 1e-6}
    if any(f['side'].upper() == 'BUY' for f in json.load(open(path))):
        led.pop('reinvest', None)          # dividend cash has been put to work
    led['cost'] = {s: v for s, v in cost.items() if s in led['positions']}
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    json.dump(led, open(LEDGER, 'w'), indent=1)
    if rows:
        new = not os.path.exists(REALIZED)
        with open(REALIZED, 'a', newline='') as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(['date', 'symbol', 'quantity', 'proceeds', 'cost', 'gain', 'term', 'basis'])
            w.writerows(rows)
    print('LEDGER:', json.dumps(led))
    for r in rows:
        print('REALIZED:', ' '.join(r))


def tax_table(year=None):
    """Rows for the dashboard's tax dataset: realized gain/loss per strategy ETF for the tax year."""
    year = year or dt.datetime.now(dt.timezone(dt.timedelta(hours=-5))).strftime('%Y')
    t = {s: dict(short=0.0, long=0.0, unknown=0.0, proceeds=0.0, sales=0, last='') for s in UNIVERSE}
    if os.path.exists(REALIZED):
        for r in csv.DictReader(open(REALIZED)):
            if r['date'][:4] == year and r['symbol'] in t:
                x = t[r['symbol']]; x[r['term'].lower()] += float(r['gain']); x['proceeds'] += float(r['proceeds'])
                x['sales'] += 1; x['last'] = max(x['last'], r['date'])
    rows = [['etf', 'tax_year', 'sales', 'proceeds', 'short_term', 'long_term', 'unclassified', 'realized', 'last_sale']]
    for s in UNIVERSE:
        x = t[s]
        rows.append([s, year, x['sales'], f"{x['proceeds']:.2f}", f"{x['short']:.2f}", f"{x['long']:.2f}",
                     f"{x['unknown']:.2f}", f"{x['short'] + x['long'] + x['unknown']:.2f}", x['last']])
    return rows


NAMES = {'SSO': '2x S&P 500', 'IEF': '7-10 year Treasuries', 'VTI': 'US total market', 'EFA': 'Developed international',
         'EEM': 'Emerging markets', 'TLT': 'Long Treasuries', 'GLD': 'Gold', 'DBC': 'Commodities', 'VNQ': 'Real estate',
         'BOXX': 'T-bill-like cash fund'}


def dash_files(inp, outdir):
    """public_run.py dash <input.json> <outdir>: status.csv, holdings.csv and tax.csv for the dashboard."""
    out, cfg = compute(inp)
    mom = dict(out['momentum']); mom['IEF'] = out['ief_mom']
    hold = out['trend_holding'] + (' + SSO (VIX leg)' if out['panic_leg'] else '')
    w = lambda name, rows: csv.writer(open(os.path.join(outdir, name), 'w', newline='')).writerows(rows)
    os.makedirs(outdir, exist_ok=True)
    w('status.csv', [['as_of', 'spy_price', 'spy_gap_200d_pct', 'trend', 'trend_holding', 'flip_level', 'rotation_picks',
                      'rotation_month_end', 'tbill_hurdle_pct', 'mode', 'strategy_capital', 'account_value', 'vix', 'updated_et'],
                     [out['date'], inp['quotes']['SPY']['last'], f"{out['gap200'] * 100:.1f}", 'On' if out['trend_on'] else 'Off',
                      hold, f'-{HYST:.0%}' if out['trend_on'] else f'+{HYST:.0%}', ' + '.join(out['picks']), out['rotation_asof'],
                      f"{out['hurdle'] * 100:.1f}", 'Live' if out['enabled'] else 'Dry run', f"{out['total']:.2f}",
                      inp.get('account_value', ''), '' if out['vix'] is None else f"{out['vix']:.1f}",
                      f"{out['date']} {inp.get('time') or ''}".strip()]])     # when the prices were read, Eastern time
    w('holdings.csv', [['ticker', 'asset', 'sleeve', 'six_month_return_pct', 'target_weight_pct', 'held_value']] + [
        [s, NAMES[s], 'Trend' if s in ('SSO', 'IEF') else 'Cash slot' if s == CASH else 'Rotation',
         f"{mom[s] * 100:.1f}" if s in mom else '', f"{out['target'][s] * 100:.2f}", f"{out['values'][s]:.2f}"] for s in UNIVERSE])
    # realized (tax year) plus unrealized on what the strategy holds now: ledger cost against current value
    cost = load_ledger(cfg).get('cost', {}); tax = tax_table(out['date'][:4])
    tax[0] += ['cost_basis', 'market_value', 'unrealized', 'unrealized_pct']
    for r in tax[1:]:
        c, v = float(cost.get(r[0], 0.0)), out['values'][r[0]]
        r += [f'{c:.2f}', f'{v:.2f}', f'{v - c:.2f}', f'{(v / c - 1) * 100:.2f}' if c > 0 else '']
    w('tax.csv', tax)
    w('value.csv', value_rows(out['date'], out['total'], float(inp['quotes']['SPY']['last']), str(inp.get('time', '')) >= '16:00'))


def since_last(today, total):
    """Change of the strategy's value since the last recorded daily balance before today (data/public/daily.csv,
    the 15:50 readings), with money added in between left out. None if there is no earlier balance."""
    rows = [r for r in csv.DictReader(open(DAILY)) if r['date'] < today] if os.path.exists(DAILY) else []
    if not rows:
        return None
    prev = rows[-1]; added = sum(a for d, a in flows() if prev['date'] < d <= today)
    base = float(prev['strategy_value']) + added
    return (total - base) / base if base > 0 else None


def value_rows(today, total, spy_last, after_close=False):
    """Daily live value against SPY (owner 2026-11-20). Keeps one row per date in data/public/daily.csv
    (date, strategy_value, spy_last as read at that run) and returns the dashboard rows: the strategy's value and
    what the first row's dollars would be worth in SPY with dividends reinvested. A refresh after 16:00 (the
    Friday review) does not replace the day's trade-run reading."""
    rows = list(csv.DictReader(open(DAILY))) if os.path.exists(DAILY) else []
    if not (after_close and any(r['date'] == today for r in rows)):   # an after-close refresh keeps the run's reading
        rows = [r for r in rows if r['date'] != today] + [{'date': today, 'strategy_value': f'{total:.2f}', 'spy_last': f'{spy_last:.4f}'}]
    rows.sort(key=lambda r: r['date'])
    os.makedirs(os.path.dirname(DAILY), exist_ok=True)
    with open(DAILY, 'w', newline='') as fh:
        wr = csv.DictWriter(fh, ['date', 'strategy_value', 'spy_last']); wr.writeheader(); wr.writerows(rows)
    h = history('SPY'); ds = sorted(h)
    def factor(d):                       # adjusted / raw close: the dividend adjustment in force on that date
        k = [x for x in ds if x <= d]; a, c = h[k[-1] if k else ds[0]]; return a / c
    tr = lambda r: float(r['spy_last']) * factor(r['date'])
    fl = flows(); put = float(rows[0]['strategy_value']); units = put / tr(rows[0]); prev = rows[0]['date']
    out = [['date', 'strategy', 'spy', 'put_in']]
    for r in rows:                       # money added later buys SPY at that day's reading, like the strategy's cash
        add = sum(a for d, a in fl if prev < d <= r['date']) if r is not rows[0] else 0.0
        put += add; units += add / tr(r); prev = r['date']
        out.append([r['date'], r['strategy_value'], f"{units * tr(r):.2f}", f"{put:.2f}"])
    return out


def sell_lots(qty, broker):
    """Tax lots for a sell, highest cost first (owner 2026-11-20). Any of the account's lots of the ticker may be
    used, the autopilot's included (owner: "you can sell autopilot's lot"); the share count still comes from the
    strategy's ledger. broker = the "lots" list of get_tax_lots_for_symbol (it is as of the previous night, so
    shares bought today are not in it). Returns ([{"tax_lot_id","quantity"}], None) or (None, why not)."""
    if broker is None:
        return None, 'NEEDED'
    lots = [b for b in broker if b.get('lotSelectionId') and float(b.get('quantity') or 0) > 0]
    out, left = [], round(qty, 5)
    for b in sorted(lots, key=lambda x: -float(x['unitCost'])):
        if left <= 1e-6:
            break
        t = min(float(b['quantity']), left); left = round(left - t, 5)
        out.append({'tax_lot_id': b['lotSelectionId'], 'quantity': f'{t:.5f}'.rstrip('0').rstrip('.'),
                    'unit_cost': float(b['unitCost']), 'open_date': b.get('openDate')})
    if left > 1e-6:
        return None, "the broker's lots do not cover the sale yet"
    if len(out) > 8:
        return None, 'more than 8 lots'
    return out, None


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
    return picks, mom, hurdle, e, s


def targets(on, picks, ief_ok=True, panic=False, scale=1.0):
    w = {s: 0.0 for s in UNIVERSE}
    if on:
        w['SSO'] += 0.5 * scale
        w[CASH] += 0.5 * (1 - scale)
    else:
        k = PANIC_SHARE if panic else 0.0          # 1x S&P on k of the trend half = SSO at half that weight
        w['IEF' if ief_ok else CASH] += 0.5 * (1 - k)
        w['SSO'] += 0.5 * k * 0.5
        w[CASH] += 0.5 * k * 0.5
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
    picks, mom, hurdle, asof, start = rotation(series, sgov, today)
    ief = adj_series('IEF', today, q['IEF']['last'])
    ief_mom = ief[asof] / ief[start] - 1; ief_ok = ief_mom > hurdle
    fallback = 'IEF' if ief_ok else CASH
    panic, vix_used, vix_note = vix_panic(today, inp.get('vix'))
    scale, spy_vol = sso_scale(spy, today)
    w = targets(on, picks, ief_ok, panic, scale)
    out = dict(date=today, time=inp.get('time'), trend_on=on, gap200=gap, spy_sma200_adj=sma, picks=picks,
               rotation_asof=asof, momentum=[(x, m) for m, x in mom], hurdle=hurdle, target=w,
               ief_mom=ief_mom, ief_ok=ief_ok, fallback=fallback, trend_holding='SSO' if on else fallback,
               vix=vix_used, sso_scale=scale, spy_vol=spy_vol, vix_panic=panic, panic_leg=bool(panic and not on), vix_note=vix_note, enabled=bool(cfg.get('enabled')))
    if not need_account:
        return out, cfg
    acct = {s: float(v) for s, v in inp.get('positions', {}).items()}
    bad = [s for s in acct if s in FORBIDDEN and acct[s] > 0]
    if bad:
        raise Guard(f'account holds tickers reserved for the other strategies: {bad}')
    # The account also holds a Public autopilot basket that trades on its own (owner 2026-11-20), BOXX included.
    # The strategy therefore counts only what its own ledger says it bought, never the account's whole position.
    led = load_ledger(cfg)
    pos = {s: float(led['positions'].get(s, 0.0)) for s in UNIVERSE}
    short = [f"{s}: ledger {pos[s]:g}, account {acct.get(s, 0.0):g}" for s in UNIVERSE if pos[s] > acct.get(s, 0.0) + 1e-6]
    if short:
        raise Guard(f'account holds fewer shares than the strategy ledger ({"; ".join(short)})')
    val = {s: pos[s] * float(q[s]['last']) for s in UNIVERSE}
    cash = max(0.0, min(float(led['cash']), float(inp.get('cash', 0.0))))
    total = sum(val.values()) + cash
    out.update(values=val, cash=cash, total=total)
    if total < 500:
        out.update(decision=False, why=f'strategy capital ${total:,.2f} (its own ETFs + positive cash) is below $500: nothing to trade', orders=[])
        return out, cfg
    held = {s: val[s] / total for s in UNIVERSE}
    drift = sum(abs(w[s] - held[s]) for s in UNIVERSE)
    missing = [s for s in UNIVERSE if w[s] > 0 and held[s] < DUST]
    extra = [s for s in UNIVERSE if w[s] == 0 and held[s] >= DUST]
    prev_scale = last_run_value('sso_scale', today) if on else None
    step = bool(on and prev_scale is not None and abs(float(prev_scale) - scale) > 1e-9 and last_run_value('trend_on', today))
    do = bool(missing or extra or drift > DRIFT_BAND or step)
    why = (f"target not held: {missing}" if missing else f"non-target held: {extra}" if extra else
           f"SSO volatility step changed {float(prev_scale):.2f} -> {scale:.2f}" if step else
           f"drift {drift:.1%} > {DRIFT_BAND:.0%}" if do else f"holdings match the targets (drift {drift:.1%})")
    orders = []
    frac = lambda x: math.floor(x * 10 ** QTY_DP + 1e-9) / 10 ** QTY_DP
    if do:
        # Fractional shares (owner 2026-11-20): quantities to 4 decimals, rounded down. Public takes fractional
        # LIMIT orders for every ETF here (preflight checked 2026-11-20), so the price limits stay.
        proceeds = 0.0
        for s in UNIVERSE:                           # sells first
            d = w[s] * total - val[s]
            if d < -max(25.0, 0.002 * total):
                px = float(q[s]['bid'] or q[s]['last']); lim = math.floor(max(px, float(q[s]['last']) * (1 - LIMIT_BAND)) * 100) / 100
                qty = pos.get(s, 0.0) if w[s] == 0 else min(pos.get(s, 0.0), frac(-d / px))
                if qty > 0:
                    tl, why_not = sell_lots(qty, (inp.get('tax_lots') or {}).get(s))
                    orders.append(dict(side='SELL', symbol=s, quantity=round(qty, 6), limit=lim,
                                       dollars=qty * px, tax_lots=tl, lots_note=why_not))
                    proceeds += qty * lim
        buys = []
        for s in UNIVERSE:
            d = w[s] * total - val[s]
            if d > max(25.0, 0.002 * total):
                px = float(q[s]['ask'] or q[s]['last']); lim = math.ceil(min(px, float(q[s]['last']) * (1 + LIMIT_BAND)) * 100) / 100
                buys.append((s, d, lim))
        # Buys can never cost more than the strategy's cash plus the sells at their limits, less $1 for cent rounding.
        budget = max(0.0, cash + proceeds - 1.0); want = sum(d for _, d, _ in buys)
        k = min(1.0, budget / want) if want > 0 else 0.0
        for s, d, lim in buys:
            qty = frac(d * k / lim)
            if qty > 0:
                orders.append(dict(side='BUY', symbol=s, quantity=qty, limit=lim, dollars=qty * lim))
    pend = float(led.get('reinvest', 0.0))
    if not do and cash >= IDLE_CASH_MAX * total:
        # Owner 2026-11-24: dividends are credited when they arrive but spent only on regular trade days (a trade
        # resets everything to target, cash included). Backstop: once idle cash passes 1% of the strategy it is
        # bought into the target holdings furthest below target, buys only.
        spend = cash - 1.0
        gaps = sorted(((w[s] * total - val[s], s) for s in UNIVERSE if w[s] > 0 and w[s] * total - val[s] > 0), reverse=True)
        if gaps:
            if spend < 100 or len(gaps) == 1:
                gaps = gaps[:1]
            tot = sum(g for g, _ in gaps)
            for g, s in gaps:
                px = float(q[s]['ask'] or q[s]['last']); lim = math.ceil(min(px, float(q[s]['last']) * (1 + LIMIT_BAND)) * 100) / 100
                qty = frac(spend * g / tot / lim)
                if qty * lim >= 1.0:
                    orders.append(dict(side='BUY', symbol=s, quantity=qty, limit=lim, dollars=qty * lim))
            if orders:
                do = True; why = f"idle cash ${cash:,.2f} is over {IDLE_CASH_MAX:.0%} of the strategy (dividends pending ${pend:,.2f})"
    out.update(held=held, drift=drift, decision=do, why=why, orders=orders)
    return out, cfg


def review(inp):
    """public_run.py review <input.json>: the Friday after-close review. Appends the strategy's value to
    data/public/weekly.csv (one row per date) and prints the week against SPY, trades, realized gains and signals."""
    out, cfg = compute(inp); today = out['date']
    spy = adj_series('SPY', today, inp['quotes']['SPY']['last'])
    rows = list(csv.DictReader(open(WEEKLY))) if os.path.exists(WEEKLY) else []
    rows = [r for r in rows if r['date'] != today]
    prev = rows[-1] if rows else None
    rows.append({'date': today, 'strategy_value': f"{out['total']:.2f}", 'spy_adj': f"{spy[today]:.4f}"})
    os.makedirs(os.path.dirname(WEEKLY), exist_ok=True)
    with open(WEEKLY, 'w', newline='') as fh:
        w = csv.DictWriter(fh, ['date', 'strategy_value', 'spy_adj']); w.writeheader(); w.writerows(rows)
    start = float(cfg.get('max_capital') or rows[0]['strategy_value']); first = rows[0]
    spy_at = lambda d: spy.get(d) or spy[max(x for x in spy if x <= d)]
    print(f"=== Public strategy weekly review {today} ===")
    print(f"VALUE: ${out['total']:,.2f} (cash ${out['cash']:,.2f}); on the ${start:,.0f} put in {out['total'] / start - 1:+.2%}"
          + (f", SPY since {first['date']} {spy[today] / spy_at(first['date']) - 1:+.2%}" if first['date'] != today else ''))
    wk = None
    if prev:
        added = sum(a for d, a in flows() if prev['date'] < d <= today)     # money added this week counts as capital, not gain
        wk = (out['total'] - added) / (float(prev['strategy_value']) + added) + added / (float(prev['strategy_value']) + added) - 1
        swk = spy[today] / spy_at(prev['date']) - 1
        if added:
            print(f"ADDED THIS WEEK: ${added:,.2f} (the week's return is on last week's value plus this money)")
        print(f"WEEK (since {prev['date']}): strategy {wk:+.2%}, SPY {swk:+.2%}, difference {wk - swk:+.2%}")
    else:
        print("WEEK: first review, this is the baseline; the first weekly comparison comes next Friday.")
    since = prev['date'] if prev else '0000'
    n = 0; days = []
    for f in sorted(os.listdir(RUNS) if os.path.isdir(RUNS) else []):
        if f.endswith('.json') and since < f[:-5] <= today:
            o = json.load(open(os.path.join(RUNS, f))).get('orders') or []
            if o:
                n += len(o); days.append(f"{f[5:-5]} " + ', '.join(f"{x['side'].lower()} {x['quantity']:g} {x['symbol']}" for x in o))
    print(f"ORDERS PRINTED THIS WEEK: {n}" + (' | ' + ' | '.join(days) if days else ''))
    rw = ry = 0.0
    if os.path.exists(REALIZED):
        for r in csv.DictReader(open(REALIZED)):
            if r['date'][:4] == today[:4]:
                ry += float(r['gain']); rw += float(r['gain']) if since < r['date'] <= today else 0.0
    print(f"REALIZED: this week ${rw:+,.2f}, tax year {today[:4]} ${ry:+,.2f}")
    print("HOLDINGS (held vs target): " + ', '.join(f"{s} {out['held'][s]:.0%}/{out['target'][s]:.0%}" for s in UNIVERSE
          if out['held'][s] >= DUST or out['target'][s] > 0) + f"; drift {out['drift']:.1%} (trades above {DRIFT_BAND:.0%})")
    g = out['gap200']
    print(f"SIGNALS: SPY {g:+.2%} vs 200-day, trend {'ON' if out['trend_on'] else 'OFF'} (flips {f'below -{HYST:.0%}' if out['trend_on'] else f'above +{HYST:.0%}'}); "
          + (f"VIX {out['vix']:.1f}, latch {'ON' if out['vix_panic'] else 'off'}; " if out['vix'] else 'VIX unavailable; ')
          + f"rotation {' + '.join(out['picks'])} from {out['rotation_asof']}; next action here: {'TRADE' if out['decision'] else 'none'} ({out['why']})")
    nxt = dt.date.fromisoformat(today) + dt.timedelta(days=7)
    if nxt.month != dt.date.fromisoformat(today).month:
        print("NEXT WEEK: a new month starts; the rotation is re-picked at its first 15:50 run.")
    push = (f"Public week: ${out['total']:,.0f}" + (f" {wk:+.1%} vs SPY {swk:+.1%}" if prev else ' (baseline)')
            + f" | since start {out['total'] / start - 1:+.1%} | trend {'ON' if out['trend_on'] else 'OFF'} {g:+.1%} | {' + '.join(out['picks'])} | realized YTD ${ry:+,.0f}")
    print('PUSH:', push[:199])
    return 0


def describe(w):
    return ' / '.join(f"{s} {x:.0%}" for s, x in w.items() if x > 0)


def main(argv):
    if len(argv) == 3 and argv[1] == 'review':
        try:
            return review(json.load(open(argv[2])))
        except Guard as e:
            print(f'GUARD: {e}'); return 2
    if len(argv) == 4 and argv[1] == 'dash':
        dash_files(json.load(open(argv[2])), argv[3]); return 0
    if len(argv) in (3, 4) and argv[1] == 'deposit':
        try:
            deposit(argv[2], argv[3] if len(argv) == 4 else ''); return 0
        except Guard as e:
            print(f'GUARD: {e}'); return 2
    if len(argv) != 3 or argv[1] not in ('brief', 'signal', 'record'):
        print(__doc__); return 1
    if argv[1] == 'record':
        try:
            record(argv[2]); return 0
        except Guard as e:
            print(f'GUARD: {e}'); return 2
    inp = json.load(open(argv[2])); q = inp['quotes']
    if q['SPY'].get('last_trade_date') and q['SPY']['last_trade_date'] != inp['date']:
        print(f"MARKET CLOSED: SPY last trade {q['SPY']['last_trade_date']} != {inp['date']}. No action."); return 3
    if argv[1] == 'signal':
        credit_dividends(inp)
    try:
        out, cfg = compute(inp)
    except Guard as e:
        print(f'GUARD: {e}'); return 2
    g = out['gap200']
    print(f"=== Public strategy {out['date']} {out.get('time') or ''} ===")
    print(f"TREND: SPY {g:+.2%} vs its 200-day -> {'ON, SSO' if out['trend_on'] else 'OFF, ' + out['fallback']} "
          f"(flips {f'below -{HYST:.0%}' if out['trend_on'] else f'above +{HYST:.0%}'})")
    print(f"FALLBACK: IEF 6-month {out['ief_mom']:+.2%} vs T-bills {out['hurdle']:+.2%} -> "
          f"{'IEF' if out['ief_ok'] else CASH} when the trend is off")
    print(f"SSO VOL TARGET: S&P vol {out['spy_vol']:.1%} (x2 = {2 * out['spy_vol']:.1%} vs {VOL_TARGET:.0%} target) -> SSO at "
          f"{out['sso_scale']:.0%} of the trend half" + ('' if out['trend_on'] else ' when the trend is on (no effect now)'))
    print("VIX PANIC: " + (out['vix_note'] or (f"VIX {out['vix']:.2f}, latch {'ON' if out['vix_panic'] else 'off'} "
          f"(on at {PANIC_ON:.0f}, off below {PANIC_OFF:.0f}) -> " + (f'{PANIC_SHARE:.0%} of the trend half in 1x S&P' if out['panic_leg'] else
          ('no effect while the trend is on' if out['vix_panic'] else 'no panic leg')))))
    print(f"ROTATION (month-end {out['rotation_asof']}, hurdle {out['hurdle']:+.2%}): " +
          ', '.join(f"{x} {m:+.1%}" for x, m in out['momentum']) + f" -> {out['picks']}")
    print(f"target: {describe(out['target'])}")
    if 'held' in out:
        print(f"held:   {describe(out['held']) or 'nothing'}; strategy capital ${out['total']:,.2f} (cash ${out['cash']:,.2f})")
    print(f"DECISION: {'TRADE' if out['decision'] else 'NO TRADE'} ({out['why']})")
    for o in out['orders']:
        print(f"  {o['side']:4s} {o['symbol']:5s} {o['quantity']:g} sh  LIMIT {o['limit']:.2f}  (~${o['dollars']:,.2f})")
        if o.get('tax_lots'):
            print('       tax_lot_matching_instructions: ' +
                  json.dumps([{'tax_lot_id': x['tax_lot_id'], 'quantity': x['quantity']} for x in o['tax_lots']]))
        elif o['side'] == 'SELL' and o.get('lots_note') != 'NEEDED':
            print(f"       no lot instruction ({o.get('lots_note')}): place it without one (broker default)")
    need = [o['symbol'] for o in out['orders'] if o.get('lots_note') == 'NEEDED']
    if need:
        print(f"LOTS NEEDED: call get_tax_lots_for_symbol for {' '.join(need)}, add \"tax_lots\": {{SYM: <its lots list>}} "
              "to the input and run again before placing the sells.")
    if out['orders'] and not out['enabled']:
        print("DRY RUN: data/public/config.json has enabled=false. Do NOT place these orders.")
    if argv[1] == 'brief':
        spyq = q['SPY']; chg = f" {float(spyq['last']) / float(spyq['close']) - 1:+.1%}" if spyq.get('close') else ''
        sl = since_last(out['date'], out['total']) if 'total' in out else None
        if 'total' in out:                 # for the chat summary, not the push (owner 2026-11-24)
            put = float(cfg.get('max_capital') or 0)
            print(f"BALANCE: ${out['total']:,.2f}" + (f", {sl:+.2%} since the last daily balance" if sl is not None else '')
                  + (f", {out['total'] / put - 1:+.2%} on the ${put:,.0f} put in" if put > 0 else ''))
        push = (f"Public 10am: SPY {float(spyq['last']):.0f}{chg}, {g:+.1%} vs 200d | trend {'ON SSO' if out['trend_on'] else 'OFF ' + out['fallback']}, "
                f"flips at {f'-{HYST:.0%}' if out['trend_on'] else f'+{HYST:.0%}'} | " + (f"VIX {out['vix']:.0f}{' PANIC leg on' if out['panic_leg'] else ''} | " if out['vix'] else '') + f"rotation {'+'.join(out['picks'])} | 3:50 "
                f"{'TRADE' if out['decision'] else 'no trade'} here" + ('' if out['enabled'] else ' (dry run)'))
        print('PUSH:', push[:199])
    else:
        os.makedirs(RUNS, exist_ok=True)
        json.dump(out, open(os.path.join(RUNS, out['date'] + '.json'), 'w'), indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
