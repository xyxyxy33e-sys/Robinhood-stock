"""Step 1: the L1 event list on complete highs (full-day highs). Research only."""
import sys, csv
from common import *

def book_pair(track, hi, d0=None):
    gC = Q0 / S200 - 1; gH = hi / S200 - 1
    c = run(track, gC < 0.02, d0=d0); l = run(track, gH < 0.02, d0=d0)
    return c, l

def events(track, hi, d0=None, label=''):
    real = track == 'real'; off = OFF if real else 0
    gC = Q0 / S200 - 1; gH = hi / S200 - 1; shutC = gC < .02; shutL = gH < .02
    c, l = book_pair(track, hi, d0)
    s0 = c['s0']; n = len(c['W'])               # W rows index s0..e-1 (axis of the track)
    ev = [t for t in range(s0, s0 + n) if D_[t + off] and not gate_b[t + off] and shutC[t + off] and not shutL[t + off]] if False else None
    # axis handling: arrays above are on the proxy axis; track-axis index i <-> proxy index i+off
    rows = []; nav_diff = None
    rc, rl = c['r'], l['r']                      # rc[i] = return on track day s0+1+i
    ds = H.RD if real else H.PD
    zone = MC._zone(HL.signals(True)[0 if not real else 1], dict(H.CUR))[0]
    names = list(l['names'])
    evs = [i for i in range(s0, s0 + n) if D_[i + off] and not gate_b[i + off] and shutC[i + off] and not shutL[i + off]]
    # per-event
    def comp(x): return np.prod(1 + x) - 1
    for t in evs:
        k = t - s0                               # W index
        w = l['W'][k]; wc = c['W'][k]
        # spell: until books' target weights re-align
        j = k
        while j < n - 1 and not np.allclose(l['W'][j], c['W'][j], atol=1e-9): j += 1
        # return index for weights at W idx m is rc[m] (day s0+1+m)
        def diff(a, b): return comp(rl[a:b]) - comp(rc[a:b])
        spell_end = min(j + 1, len(rc))
        rows.append(dict(
            date=ds[t], eff='ABCDEF'[int(l['eff'][k])], zone='D%d' % zone[t], breadth_pct=pct[t + off],
            gap_close=gC[t + off], gap_high=gH[t + off], close_vs_high=Q0[t + off] / hi[t + off] - 1, vix=VIX[t + off],
            gross_L1=l['gross'][k], risky_w=float(w[[names.index(x) for x in ('core', 'tqqq', 'qld', 'xlu')]].sum()),
            qqq_next=Q0[t + off + 1] / Q0[t + off] - 1 if t + off + 1 < T else np.nan,
            d1=diff(k, k + 1), d5=diff(k, k + 5), d20=diff(k, k + 20), spell=diff(k, spell_end), spell_end=ds[s0 + j] if j < n - 1 else 'open-at-end',
            spell_len=j - k + 1))
    return rows, c, l

def clusters(rows):
    """group event rows sharing a spell_end (same spell) -> non-overlapping contributions"""
    out = {}
    for r in rows: out.setdefault(r['spell_end'], []).append(r)
    return [dict(first=v[0]['date'], last=v[-1]['date'], n=len(v), spell=v[0]['spell'], end=k) for k, v in out.items()]

def write(rows, path):
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader()
        for r in rows: w.writerow({k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()})

def conc(vals, label):
    v = sorted(vals); s = sum(vals)
    out = f'{label}: n={len(v)} sum={s*100:+.2f} pp (sum of per-spell compounded differences)'
    for k in (1, 3, 5):
        out += f' | best{k}={sum(v[-k:])*100:+.2f} worst{k}={sum(v[:k])*100:+.2f}'
    pos = sum(1 for x in v if x > 0); out += f' | pos/neg {pos}/{len(v) - pos}; sum ex-best1 {(s - v[-1])*100:+.2f}, ex-worst1 {(s - v[0])*100:+.2f}'
    return out

if __name__ == '__main__':
    hi = full_highs()
    for track, d0, nm in (('real', None, 'real'), ('proxy', None, 'proxy2001')):
        rows, c, l = events(track, hi, d0)
        write(rows, os.path.join(HERE, f'events_{nm}.csv'))
        cl = clusters(rows)
        with open(os.path.join(HERE, f'spells_{nm}.csv'), 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(cl[0])); w.writeheader()
            for r in cl: w.writerow({k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()})
        print(f'\n===== {nm}: {len(rows)} event sessions, {len(cl)} spells')
        rc, rl = c['r'], l['r']
        print('books  C0 %s | L1 %s' % (HL.fmt(HL.stats(rc)), HL.fmt(HL.stats(rl))))
        tot_sum = (rl - rc).sum(); tot_nav = np.prod(1 + rl) / np.prod(1 + rc) - 1
        print(f'total L1-C0: sum of daily diffs {tot_sum*100:+.2f} pp; NAV ratio {tot_nav*100:+.2f} %; sum of spell diffs {sum(x["spell"] for x in cl)*100:+.2f} pp')
        print(conc([x['spell'] for x in cl], 'spells'))
        print(conc([r['d1'] for r in rows], 'per-event 1d'))
        print('date        eff zone  pct   gapC   gapH  c/h-1   VIX  gross  d1%    d5%    d20%   spell%  spell_end   len')
        for r in rows:
            print('%s  %s %s  %.2f %+.3f %+.3f %+.3f %5.1f %5.2f %+6.2f %+6.2f %+6.2f %+7.2f  %s %d' % (
                r['date'], r['eff'], r['zone'], r['breadth_pct'], r['gap_close'], r['gap_high'], r['close_vs_high'], r['vix'], r['gross_L1'],
                r['d1']*100, r['d5']*100, r['d20']*100, r['spell']*100, r['spell_end'], r['spell_len']))
        for w_ in ('d1', 'd5', 'd20'):
            x = np.array([r[w_] for r in rows]); print(f'{w_}: mean {x.mean()*100:+.3f} pp, sum {x.sum()*100:+.2f}, pos {int((x>0).sum())}/{len(x)}')
