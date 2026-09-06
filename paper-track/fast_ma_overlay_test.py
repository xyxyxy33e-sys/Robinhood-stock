"""Does a faster 20/60-day classifier help at TRANSITIONS? (2026-09-06, asked
after the TQQQ/cash comparison showed our C->B->A re-entry ladder is what
lost 2025.) ma_window_sweep.py already showed 20/60 is worse than 50/200 as
THE classifier, and the 30/150 micro overlay was disabled 09-02. This asks a
narrower question: keep 50/200 as the macro, and use a 20/60 reading only to
accelerate or confirm specific transitions.

  R1  20/60 as the sole classifier (for reference)
  R2  re-entry: macro B or C, fast says A (or A/B) -> hold A weights now
  R3  exit: macro A, fast says D/E/F -> hold D weights now
  R4  bottom re-entry: macro F, fast says A/B/C -> hold C weights (100% core)
  R5  E: macro E, fast says A/B -> D weights
  R6  confirmation: a macro transition only takes effect once fast agrees
      (fast in the same up/down half) -- a whipsaw filter
Both eras on the 26y proxy, then the real SPMO-era weekly rows.
"""
import sys
sys.path.insert(0, 'paper-track')
from improvement_search import build, data, evaluate, header, show, vt, live_base
from downturn_review import enrich, live
import return_frontier as RF
from state import TARGET_WEIGHTS, compute_states
from long_history_backtest import load_px

UP, DOWN = set('ABC'), set('DEF')


def add_fast(rows, s=20, l=60):
    D = data(); ds, px = D['ds'], D['qqq']
    fast = dict(zip(ds, compute_states(ds, px, short_n=s, long_n=l)))
    for r in rows:
        r['fast'] = fast[r['d']]
    return rows


def rules():
    W = TARGET_WEIGHTS
    def r1(r): return W[r['fast']]
    def r2a(r): return W['A'] if r['state'] in 'BC' and r['fast'] == 'A' else W[r['state']]
    def r2b(r): return W['A'] if r['state'] in 'BC' and r['fast'] in 'AB' else W[r['state']]
    def r3(r): return W['D'] if r['state'] == 'A' and r['fast'] in DOWN else W[r['state']]
    def r4(r): return W['C'] if r['state'] == 'F' and r['fast'] in UP else W[r['state']]
    def r5(r): return W['D'] if r['state'] == 'E' and r['fast'] in 'AB' else W[r['state']]
    def r24(r): return r2b(r) if r['state'] in 'BC' else r4(r)
    return [('R1 20/60 as the classifier', r1), ('R2a B/C + fast A -> A weights', r2a),
            ('R2b B/C + fast A/B -> A weights', r2b), ('R3 A + fast D/E/F -> D weights', r3),
            ('R4 F + fast A/B/C -> C weights', r4), ('R5 E + fast A/B -> D weights', r5),
            ('R2b + R4 combined', r24)]


def confirmed(rows):
    """R6: macro state only 'takes' once fast is in the same half."""
    eff = None; out = []
    for r in rows:
        m = r['state']
        if eff is None or (m in UP) == (r['fast'] in UP):
            eff = m
        out.append(eff)
    return out


def main():
    rows = add_fast(enrich(build()))
    base = evaluate(rows, live())
    header(); show('LIVE (50/200 only)', base)
    for lab, fn in rules():
        show(lab, evaluate(rows, lambda r, fn=fn: vt(fn(r), r['vol'])), base)
    eff = confirmed(rows)
    for r, e in zip(rows, eff): r['eff'] = e
    show('R6 transitions confirmed by fast', evaluate(rows, lambda r: vt(TARGET_WEIGHTS[r['eff']], r['vol'])), base)

    print("\nreal SPMO era weekly:")
    rr = RF.real_rows()
    qqq = load_px('data/qqq_long_history.csv'); qd = sorted(qqq)
    fast = dict(zip(qd, compute_states(qd, qqq, short_n=20, long_n=60)))
    for r in rr: r['fast'] = fast[r['d0']]
    e = RF.eval_real(rr, RF.mk_real(TARGET_WEIGHTS, False))
    print(f"  {'live':<36} {e['cagr']*100:.2f}% / {e['sharpe']:.3f} / {e['mdd']*100:.1f}%")
    for lab, fn in rules():
        e = RF.eval_real(rr, lambda r, fn=fn: RF.vt(fn(r), r['vol']))
        print(f"  {lab:<36} {e['cagr']*100:.2f}% / {e['sharpe']:.3f} / {e['mdd']*100:.1f}%")
    eff = confirmed(rr)
    for r, x in zip(rr, eff): r['eff'] = x
    e = RF.eval_real(rr, lambda r: RF.vt(TARGET_WEIGHTS[r['eff']], r['vol']))
    print(f"  {'R6 confirmed':<36} {e['cagr']*100:.2f}% / {e['sharpe']:.3f} / {e['mdd']*100:.1f}%")


if __name__ == '__main__':
    main()
