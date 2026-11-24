import sys; sys.path.insert(0, '/home/user/Robinhood-stock/paper-track/research_notes/trigger_chop_2026_11')
from common import *
out = {}
for track in ('real', 'proxy'):
    R = run(track); st = R['st']
    print(f"== {track} baseline CAGR {st['c']*100:.2f} Sh {st['sh']:.3f} MDD {st['m']*100:.2f} tpy {R['tpy']:.1f} ShEx2020 {R['sh_x20']:.3f}")
    d = R['d']; b = R['b']; s0, e = d['s0'], d['e']
    c = decode(R['key']); yrs = (e - s0) / 252
    sg = HL.signals(False)[0 if track == 'proxy' else 1]
    macro = sg['macro'][0][s0:e]; eff = d['eff']
    gate_b = sg['gate_b'][0][s0:e]; gate_g = sg['gate_g'][0][s0:e]
    comps = [('macro state (1% hyst lines)', macro, False), ('eff state (macro+fast 20/100)', c['eff'], False),
             ('fast overlay active (eff!=macro)', (c['eff'] != macro).astype(int), True),
             ('D gate (effective, key)', c['gate'], True), ('  gate_b breadth (macro D)', gate_b.astype(int), True),
             ('  gate_g gap200<2% (macro D)', gate_g.astype(int), True),
             ('D zone (buffered, when D ungated)', c['zone'], False), ('VIXY sleeve allowed', c['vixy'], True),
             ('VIX-panic', c['panic'], True), ('deep-E', c['deep'], True), ('A trim votes (held)', c['held'], False)]
    A = attribute(b, s0, e)
    print(f"  rebalance days {A['reb'].sum()} ({A['reb'].sum()/yrs:.1f}/yr); engine tpy {R['tpy']:.1f}")
    rows = []
    for nm, x, bi in comps:
        cs = chop_stats(x, bi)
        print(f"  {nm:38s} flips/yr {cs['flips']/yrs:5.1f} spells {cs['spells']:4d} short<=3 {cs['short']:3d}/{cs['elig']:3d} ({100*cs['short']/max(cs['elig'],1):4.0f}%) reflip<=5 {cs['refl']:3d}")
        rows.append((nm, cs))
    print("  rebalance-day attribution (key components changed; a day may have several):")
    for k, v in A['chg'].items(): print(f"    {k:6s} {v.sum():4d} days ({v.sum()/yrs:4.1f}/yr)  sole cause {(v & (sum(A['chg'][j].astype(int) for j in A['chg'])==1)).sum()}")
    print(f"    drift-only (no key change) {A['drift_only'].sum()} ({A['drift_only'].sum()/yrs:.1f}/yr); key-change days {A['any_key'].sum()}")
    # split eff changes by whether macro changed that day (hysteresis) or overlay
    dm = np.r_[False, macro[1:] != macro[:-1]]; de = np.r_[False, c['eff'][1:] != c['eff'][:-1]]
    kc = A['chg']['eff']
    print(f"    eff-change rebalance days with macro also changed {(kc & dm).sum()}, overlay-only {(kc & ~dm).sum()}")

# ===================================================================== PART 2
print("\n\n######## PART 2: buffers (patched in memory only) ########")
_orig_signals = HL.signals
GATE = {'mode': None}          # None = live; ('hyst', enter, exit) or ('hold', n)

def gate_machine(gap, m3, mode):
    P, T = gap.shape; out = np.zeros((P, T), bool)
    for p in range(P):
        st = False; held = 0
        for t in range(T):
            g = gap[p, t]
            if not m3[p, t] or np.isnan(g):
                st = False; held = 0; out[p, t] = False; continue
            if mode[0] == 'hyst':
                st = (g < mode[2]) if st else (g < mode[1])      # enter below mode[1], stay until g >= mode[2]
            else:
                raw = g < S.D_GATE_GAP200
                held += 1                                   # sessions spent in the current state (incl. today)
                if raw != st and held > mode[1]: st = raw; held = 1   # may flip only after >= n sessions in the state
            out[p, t] = st
    return out

def _patched(l1, use_live=True):
    sgp, sgr = _orig_signals(l1, use_live)
    if GATE['mode'] is None: return sgp, sgr
    res = []
    for sg in (sgp, sgr):
        sg = dict(sg); gg = gate_machine(sg['gaps'][200], sg['macro'] == 3, GATE['mode'])
        sg['gate_g'] = gg; sg['gate'] = sg['gate_b'] | gg; res.append(sg)
    return tuple(res)
HL.signals = _patched

def evaluate(label):
    rows = {}
    for track in ('real', 'proxy'):
        R = run(track); c = decode(R['key']); st = R['st']
        gs = chop_stats(c['gate'], True); zs = chop_stats(c['zone'], False)
        rows[track] = dict(c=st['c'] * 100, sh=st['sh'], m=st['m'] * 100, tpy=R['tpy'], shx=R['sh_x20'],
                           g_short=gs['short'], g_spells=gs['spells'], z_short=zs['short'], z_spells=zs['spells'],
                           g_flips=gs['flips'], z_flips=zs['flips'])
    return rows

import json
variants = [('BASE (live)', None, None)]
variants += [('gate_g enter<1.5% leave>2.5%', ('hyst', 0.015, 0.025), None), ('gate_g enter<1.0% leave>3.0%', ('hyst', 0.01, 0.03), None),
             ('gate_g min-hold 2', ('hold', 2), None), ('gate_g min-hold 3', ('hold', 3), None)]
variants += [('zone buffer 0.75%', None, 0.0075), ('zone buffer 1.0%', None, 0.01), ('zone buffer 1.5%', None, 0.015)]
base_b = H.CUR['d_buffer']
res = {}
for name, gm, zb in variants:
    GATE['mode'] = gm; H.CUR['d_buffer'] = base_b if zb is None else zb
    res[name] = evaluate(name)
    for tr in ('real', 'proxy'):
        x = res[name][tr]
        print(f"{name:32s} {tr:5s} CAGR {x['c']:6.2f} Sh {x['sh']:.3f} ShEx20 {x['shx']:.3f} MDD {x['m']:7.2f} tpy {x['tpy']:5.1f} | gate flips {x['g_flips']:3d} on-spells {x['g_spells']:3d} short {x['g_short']:3d} | zone flips {x['z_flips']:3d} short {x['z_short']:3d}", flush=True)
GATE['mode'] = None; H.CUR['d_buffer'] = base_b

print("\n--- bar check (vs BASE) ---")
B = res['BASE (live)']
for name, gm, zb in variants[1:]:
    ok = True; det = []
    for tr in ('real', 'proxy'):
        x, b0 = res[name][tr], B[tr]
        ds_ = x['sh'] - b0['sh']; dm = x['m'] - b0['m']; dt = b0['tpy'] - x['tpy']
        key_s, key0 = ('g_short', 'g_short') if gm else ('z_short', 'z_short')
        rt_cut = (b0[key0] - x[key_s]) / max(b0[key0], 1)
        c1 = ds_ >= -0.01; c2 = dm >= -0.5; c3 = (dt >= 3) or (rt_cut >= 0.30)
        det.append((tr, ds_, dm, dt, rt_cut, c1, c2, c3)); ok &= (c1 and c2 and c3)
    print(f"{name:32s} PASS={ok}  " + ' | '.join(f"{t}: dSh {a:+.3f} dMDD {m:+.2f} tpy_cut {tc:+.1f} RT_cut {r*100:+.0f}% [{int(c1)}{int(c2)}{int(c3)}]" for t, a, m, tc, r, c1, c2, c3 in det))
json.dump(res, open(__file__.replace('run.py', 'results.json'), 'w'), indent=1)
