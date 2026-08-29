"""SPMO core + TQQQ satellite regime overlay -- state machine, ported from
xyxyxy33e-sys/robinhood research/leverage_ma.md so the paper track has no
dependency on that repo staying checked out.

Six-state classifier on QQQ (market signal, per the study's finding 3),
1% hysteresis buffer, 50/200-day SMAs.
"""
import csv

def load_csv(path):
    out = {}
    for r in csv.DictReader(open(path)):
        try: out[r['d']] = float(r['c'])
        except Exception: pass
    return out

def sma(v, i, n):
    return sum(v[i-n+1:i+1])/n if i >= n-1 else None

def compute_states(dates, px, buf=0.01):
    v = [px[d] for d in dates]
    s50 = s200 = None
    out = []
    for i, d in enumerate(dates):
        m50, m200 = sma(v, i, 50), sma(v, i, 200)
        if m200 is None:
            out.append('F'); continue
        if v[i] > m50*(1+buf): s50 = True
        elif v[i] < m50*(1-buf): s50 = False
        if v[i] > m200*(1+buf): s200 = True
        elif v[i] < m200*(1-buf): s200 = False
        cross = m50 > m200
        if s50 and s200 and cross: out.append('A')
        elif s50 and s200 and not cross: out.append('B')
        elif s50 and not s200: out.append('C')
        elif not s50 and s200: out.append('D')
        elif not s50 and not s200 and cross: out.append('E')
        else: out.append('F')
    return out

SAT_WEIGHT_35 = dict(A=0.35, B=0.35, C=0.0, D=0.15, E=0.15, F=0.0)
STATE_LABEL = dict(
    A='established uptrend', B='reclaim', C='bounce in downtrend',
    D='pullback in uptrend', E='breakdown', F='established downtrend',
)
