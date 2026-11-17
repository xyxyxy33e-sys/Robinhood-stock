"""L1 variants study (research only). Plan: PLAN.md. Usage: python3 run.py  [PLACEBO_DRAWS=200]"""
import sys, os, time, csv
from common import *
t_start = time.time()
NPL = int(os.environ.get('PLACEBO_DRAWS', 200))
TH = 0.02
HI_FULL = full_highs(); LO = lows_norm()
HI_1550 = HI_FULL.copy()
H1550 = {'2026-03-06': 605.99, '2026-10-30': 697.94, '2026-11-02': 699.43, '2026-11-04': 701.45, '2026-11-11': 695.395}
for d, v in H1550.items():
    i = PD.index(d); old = HI_FULL[i] / SC[i]
    HI_1550[i] = max(v * SC[i], Q0[i])
    print(f'15:50 high substituted {d}: full-day {old:.3f} -> 15:50 {HI_1550[i]/SC[i]:.3f}')
VIXm10 = np.array([np.nanmean(VIX[max(0, i - 9):i + 1]) if i >= 9 else np.nan for i in range(T)])
VIXprev = np.concatenate([[np.nan], VIX[:-1]])

def arms(hi, lo):
    """name -> (open_mask over proxy axis [gap half open], scale or None). open = ~shut."""
    gC = Q0 / S200 - 1; gH = hi / S200 - 1
    oc = ~(gC < TH); oh = ~(gH < TH)
    cvh = Q0 / hi - 1
    A = {}
    A['C0'] = (oc, None); A['L1'] = (oh, None)
    for x in (0.025, 0.03, 0.04): A['H%.1f' % (x * 100)] = (oc | ~(gH < x), None)
    for y in (0.0, 0.005, 0.01, 0.015): A['HC%.1f' % (y * 100)] = (oh & ~(gC < y), None)
    for z in (0.005, 0.01, 0.015): A['R%.1f' % (z * 100)] = (oc | (oh & (cvh >= -z)), None)
    gT3 = (hi + lo + Q0) / 3 / S200 - 1; gT2 = (hi + Q0) / 2 / S200 - 1
    A['TP3'] = (oc | ~(gT3 < TH), None); A['TP2'] = (oc | ~(gT2 < TH), None)
    ohp = np.concatenate([[False], oh[:-1]])
    A['P2'] = (oc | (oh & ohp), None)
    half = D_ & ~gate_b & ~oc & oh
    A['HALF'] = (oh, np.where(half, 0.5, 1.0))
    calm = (VIX < VIXm10) | (VIX < VIXprev); calmA = VIX < VIXm10
    A['VIXF'] = (oc | (oh & calm), None); A['VIXFa'] = (oc | (oh & calmA), None); A['VIXopp'] = (oc | (oh & ~calm & ~np.isnan(VIX)), None)
    for nm, keep in (('OPEN-ONLY', False), ('CLOSE-ONLY', True)):
        op = np.zeros(T, bool)
        for t in range(T):
            if oc[t]: op[t] = True; continue
            if not oh[t]: continue
            pu = t > 0 and macro[t - 1] == 3 and op[t - 1] and not gate_b[t - 1]
            op[t] = pu if keep else (not pu)
        A[nm] = (op, None)
    return A
ORDER = ['C0', 'L1', 'H2.5', 'H3.0', 'H4.0', 'HC0.0', 'HC0.5', 'HC1.0', 'HC1.5', 'R0.5', 'R1.0', 'R1.5', 'TP3', 'TP2', 'P2', 'HALF', 'VIXF', 'VIXFa', 'VIXopp', 'OPEN-ONLY', 'CLOSE-ONLY']
FAM = {'H2.5': ['L1', 'H3.0'], 'H3.0': ['H2.5', 'H4.0'], 'H4.0': ['H3.0'], 'HC0.0': ['L1', 'HC0.5'], 'HC0.5': ['HC0.0', 'HC1.0'], 'HC1.0': ['HC0.5', 'HC1.5'], 'HC1.5': ['HC1.0'],
       'R0.5': ['R1.0'], 'R1.0': ['R0.5', 'R1.5'], 'R1.5': ['R1.0', 'L1'], 'TP3': ['TP2'], 'TP2': ['TP3'], 'VIXF': ['VIXFa'], 'VIXFa': ['VIXF']}
WIN = {'real': ('real', None, '2099'), 'p01': ('proxy', None, '2099'), 'p10': ('proxy', '2010-01-04', '2099'), 'rex': ('real', None, '2026-10-23')}

def shp(r): return r.mean() / r.std(ddof=1) * 252 ** .5
def roll_min(r, k):
    c = np.concatenate([[1.0], np.cumprod(1 + r)]); return (c[k:] / c[:-k] - 1).min()
def wstats(r):
    nav = np.cumprod(1 + r); dd = nav / np.maximum.accumulate(nav) - 1
    return dict(cagr=nav[-1] ** (252 / len(r)) - 1, sh=shp(r), dd=dd.min(), w1=r.min(), w5=roll_min(r, 5), w20=roll_min(r, 20))

def run_arm(arm, lag=0, wins=WIN):
    op, sc = arm; out = {}
    for w, (tr, d0, d1) in wins.items():
        d = run(tr, ~op, d0=d0, d1=d1, lag=lag, scale=sc)
        off = OFF if tr == 'real' else 0
        rng = np.arange(d['s0'], d['e']) + off
        oc_ = ~((Q0 / S200 - 1) < TH)
        opens = int((D_ & ~gate_b & ~oc_ & op)[rng].sum())
        out[w] = dict(st=wstats(d['r']), r=d['r'], ds=d['ds'], gross=float(d['gross'].mean()), opens=opens)
    return out

def cell(x): return f"{x['st']['cagr']*100:5.1f} / {x['st']['sh']:.3f} / {x['st']['dd']*100:6.1f} / {x['st']['w20']*100:6.1f}"
def extra(x): return f"w1 {x['st']['w1']*100:6.1f} w5 {x['st']['w5']*100:6.1f} open {x['opens']:3d} gross {x['gross']:.3f}"

def table(res, title):
    print('\n' + '=' * 30, title, '=' * 30)
    print('cell = CAGR% / Sharpe / maxDD% / worst-20-sessions%   (extra: worst day, worst 5, L1-only opening sessions, avg gross)')
    for w, nm in (('real', 'REAL 2015-11..2026-11-16'), ('p01', 'PROXY 2001'), ('p10', 'PROXY 2010'), ('rex', 'REAL ex 2026-10-26..11-16 (ends 2026-10-23)')):
        print('\n--', nm)
        print('%-11s %-40s %s' % ('arm', 'CAGR / Sharpe / DD / W20', 'extra'))
        for a in ORDER:
            print('%-11s %-40s %s' % (a, cell(res[a][w]), extra(res[a][w])))

def ev_rule(res, lagres, fullrun_name):
    """reading-rule table vs C0 (res = results for the arm set); returns dict arm -> flags"""
    out = {}; c0 = res['C0']
    for a in ORDER[1:]:
        r = res[a]; f = {}
        f['dS'] = {w: r[w]['st']['sh'] - c0[w]['st']['sh'] for w in WIN}
        f['dDD'] = {w: (r[w]['st']['dd'] - c0[w]['st']['dd']) * 100 for w in WIN}       # negative = deeper
        f['r1'] = all(f['dS'][w] >= 0.02 for w in ('real', 'p01', 'p10'))
        f['r2'] = all(f['dDD'][w] >= -0.5 for w in WIN)
        f['r3'] = f['dS']['rex'] >= 0.02 and f['dS']['real'] >= 0.02
        n = len(r['p01']['r']); h = n // 2
        f['halves'] = (shp(r['p01']['r'][:h]) - shp(c0['p01']['r'][:h]), shp(r['p01']['r'][h:]) - shp(c0['p01']['r'][h:]))
        f['r4'] = all(x > 0 for x in f['halves'])
        nb = FAM.get(a)
        f['r5'] = None if nb is None else all(all(res[b][w]['st']['sh'] - c0[w]['st']['sh'] > 0 for w in ('real', 'p01', 'p10')) for b in nb)
        out[a] = f
    return out

def boot(rA, rC, B=2000, blk=20, seed=7):
    rng = np.random.default_rng(seed); n = len(rA); nb = -(-n // blk)
    st = rng.integers(0, n - blk + 1, (B, nb)); idx = (st[:, :, None] + np.arange(blk)).reshape(B, -1)[:, :n]
    a = rA[idx]; c = rC[idx]
    d = a.mean(1) / a.std(1, ddof=1) - c.mean(1) / c.std(1, ddof=1); d *= 252 ** .5
    return float(np.median(d)), float((d <= 0).mean()), float(np.percentile(d, 5)), float(np.percentile(d, 95))

def robustness(name, res, lag_res):
    c0, r = res['C0'], res[name]
    print(f'\n  [{name}] robustness (Sharpe difference vs C0)')
    for w in ('real', 'p01', 'p10', 'rex'):
        a, c, ds = r[w]['r'], c0[w]['r'], np.array(r[w]['ds']); n = len(a); h = n // 2
        yrs = np.array([x[:4] for x in ds]); m20 = yrs != '2020'
        print(f'   {w:4s}: full {shp(a)-shp(c):+.3f} | half1 {shp(a[:h])-shp(c[:h]):+.3f} half2 {shp(a[h:])-shp(c[h:]):+.3f} | ex-2020 {shp(a[m20])-shp(c[m20]):+.3f} | '
              f'lag1 {lag_res[name][w]["st"]["sh"]-lag_res["C0"][w]["st"]["sh"]:+.3f} (lag1 DD {lag_res[name][w]["st"]["dd"]*100:.1f} vs C0 {lag_res["C0"][w]["st"]["dd"]*100:.1f}) | '
              'boot med %+.3f P(<=0) %.3f 5-95%% [%+.3f, %+.3f]' % boot(a, c))

# placebo --------------------------------------------------------------------------------------------------------
YEARS = np.array([int(d[:4]) for d in PD]); HR = HI_FULL / Q0 - 1; LR = LO / Q0 - 1
POOL = {y: np.where(YEARS == y)[0] for y in set(YEARS)}
def placebo_hl(rng):
    j = np.empty(T, int)
    for y, idx in POOL.items(): j[idx] = rng.choice(idx, len(idx))
    return Q0 * (1 + HR[j]), Q0 * (1 + LR[j])
def sl10(r, ds): m = np.array(ds) >= '2010-01-05'; return r[m]
def placebo(names, real_gain, c0res, nd=NPL, seed=11):
    rng = np.random.default_rng(seed); gains = {a: {'real': [], 'p01': [], 'p10': []} for a in names}
    cr, cp = c0res['real']['r'], c0res['p01']['r']; cp10 = sl10(cp, c0res['p01']['ds'])
    for k in range(nd):
        hi, lo = placebo_hl(rng); A = arms(hi, lo)
        for a in names:
            op, sc = A[a]
            dr = run('real', ~op, scale=sc); dp = run('proxy', ~op, scale=sc)
            gains[a]['real'].append(shp(dr['r']) - shp(cr)); gains[a]['p01'].append(shp(dp['r']) - shp(cp))
            gains[a]['p10'].append(shp(sl10(dp['r'], dp['ds'])) - shp(cp10))
    print(f'\n  PLACEBO ({nd} draws; random same-year (H/C-1, L/C-1) pairs on this session close). real gain -> percentile among placebo gains')
    out = {}
    for a in names:
        row = []
        for w in ('real', 'p01', 'p10'):
            g = np.array(gains[a][w]); rg = real_gain[a][w]
            pc = (g < rg).mean() * 100 + 0.5 * (g == rg).mean() * 100
            row.append(pc); print(f'   {a:10s} {w:4s}: real dSharpe {rg:+.3f}; placebo mean {g.mean():+.3f} sd {g.std():.3f} [5%,95%] [{np.percentile(g,5):+.3f},{np.percentile(g,95):+.3f}] -> percentile {pc:.0f}')
        out[a] = row
    return out

def main():
    summary = {}
    for ver, hi in (('FULL-DAY HIGHS', HI_FULL), ('15:50 HIGHS WHERE FETCHED (5 days)', HI_1550)):
        A = arms(hi, LO); res = {a: run_arm(A[a]) for a in ORDER}
        table(res, ver)
        flags = ev_rule(res, None, ver)
        print('\n-- reading-rule flags vs C0 (%s)' % ver)
        print('%-11s dS real/p01/p10/rex           dDD(pp) real/p01/p10/rex        halves dS(p01)    r1 r2 r3 r4 r5' % 'arm')
        for a in ORDER[1:]:
            f = flags[a]
            print('%-11s %+.3f %+.3f %+.3f %+.3f      %+5.1f %+5.1f %+5.1f %+5.1f     %+.3f %+.3f   %s  %s  %s  %s  %s' % (
                a, *[f['dS'][w] for w in WIN], *[f['dDD'][w] for w in WIN], *f['halves'], *[('Y' if v else ('n/a' if v is None else 'n')) for v in (f['r1'], f['r2'], f['r3'], f['r4'], f['r5'])]))
        summary[ver] = (A, res, flags)
        if ver.startswith('FULL'):
            lag = {a: run_arm(A[a], lag=1) for a in ORDER}
            cand = [a for a in ORDER[1:] if all(flags[a]['dS'][w] > 0 for w in ('real', 'p01', 'p10'))]
            print('\nArms with Sharpe above C0 on real, p01 and p10 (full-day highs):', cand)
            print('\n===== ROBUSTNESS (lag, halves, ex-2020, bootstrap)')
            targets = list(dict.fromkeys(['L1'] + cand))
            for a in targets: robustness(a, res, lag)
            real_gain = {a: {w: flags[a]['dS'][w] for w in ('real', 'p01', 'p10')} for a in targets}
            print('\n===== PLACEBO'); pl = placebo(targets, real_gain, res['C0'])
            summary['placebo'] = pl
            print('\n===== READING RULE verdicts (full-day highs)')
            for a in ORDER[1:]:
                f = flags[a]; p = pl.get(a)
                r6 = None if p is None else max(p) >= 90
                ok = f['r1'] and f['r2'] and f['r3'] and f['r4'] and (f['r5'] in (True, None)) and bool(r6)
                print('%-11s r1 %s r2 %s r3 %s r4 %s r5 %s r6(placebo>=90 on a track) %s  => %s' % (a, f['r1'], f['r2'], f['r3'], f['r4'], f['r5'], r6, 'PASS' if ok else 'fail'))
    print('\nruntime %.0f s' % (time.time() - t_start))
if __name__ == '__main__':
    main()
