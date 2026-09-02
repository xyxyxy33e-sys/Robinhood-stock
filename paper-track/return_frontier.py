"""Map the RETURN frontier of the design: what does it cost, in drawdown and
Sharpe, to raise CAGR?

Context (2026-09-02). The improvement search found exactly one edge (state B
leverage should be cut) and several DIALS -- changes that move CAGR and MaxDD
together while Sharpe stays flat. The user asked how to bring the return up.
That is a dial question, so this script draws the dial: take the recommended
base (B=75/25), then sweep the leverage in the TREND states (A via TQQQ, D via
QLD) and the micro overlay (which is an A de-lever), and report every point on
the 26-year proxy (both eras) and on the real SPMO-era instruments.

Not swept: leverage in B/C/E/F. The search showed leverage in counter-trend
states (50 < 200) is harmful, not merely risky -- that is not a dial.
"""
import math
import sys
sys.path.insert(0, 'paper-track')
from improvement_search import build as build_proxy, evaluate as eval_proxy
from improvement_search_r2 import mk as mk_proxy
from state import TARGET_WEIGHTS, MICRO_OVERLAY_WEIGHTS, VOL_TARGET_PA
import voltarget_live_backtest as VL

B_NEW = (0.75, 0.25, 0, 0, 0)


def real_rows():
    rows = VL.build()
    return rows[0] if isinstance(rows, tuple) else rows


def vt(w, v, t=VOL_TARGET_PA):
    m = 1.0 if not v else min(1.0, t / v)
    risky = sum(w[:4])
    return tuple(x * m for x in w[:4]) + (1 - risky * m,)


def mk_real(W, micro):
    def f(r):
        k = (r['state'], r['agree'])
        w = MICRO_OVERLAY_WEIGHTS[k] if micro and k in MICRO_OVERLAY_WEIGHTS else W[r['state']]
        return vt(w, r['vol'])
    return f


def eval_real(rows, wfn):
    prev = None; rets = []
    for r in rows:
        w = wfn(r)
        cost = VL.ONE_WAY_SPREAD * sum(abs(w[i] - (prev[i] if prev else 0)) for i in range(5))
        rets.append(sum(w[i] * r['legs'][i] for i in range(5)) - cost); prev = w
    n = len(rets); nav = 1.0
    for x in rets: nav *= 1 + x
    m = sum(rets) / n; v = (sum((x - m) ** 2 for x in rets) / (n - 1)) ** 0.5
    pk = cur = 1.0; mdd = 0
    for x in rets:
        cur *= 1 + x; pk = max(pk, cur); mdd = min(mdd, cur / pk - 1)
    return dict(cagr=nav ** (52 / n) - 1, sharpe=m * 52 / (v * math.sqrt(52)), mdd=mdd)


def main():
    P = build_proxy(); R = real_rows()
    # micro overlay hard-codes A/D rows, so when A or D move it has to be off.
    configs = [('LIVE (B=25/75, micro on)', TARGET_WEIGHTS['A'], TARGET_WEIGHTS['D'], True, TARGET_WEIGHTS['B'])]
    for micro in (True, False):
        configs.append((f"B=75/25, micro {'on' if micro else 'off'}", TARGET_WEIGHTS['A'], TARGET_WEIGHTS['D'], micro, B_NEW))
    for a in (0.7, 0.6, 0.5):
        configs.append((f"B=75/25, A={a*100:.0f}/{(1-a)*100:.0f}, micro off", (a, 1 - a, 0, 0, 0), TARGET_WEIGHTS['D'], False, B_NEW))
    for q in (0.85, 1.0):
        configs.append((f"B=75/25, D={q*100:.0f}% QLD, micro off", TARGET_WEIGHTS['A'], (0, 0, q, 0, 1 - q), False, B_NEW))
    for a, q in ((0.7, 0.85), (0.7, 1.0), (0.6, 1.0), (0.5, 1.0)):
        configs.append((f"B=75/25, A={a*100:.0f}/{(1-a)*100:.0f}, D={q*100:.0f}% QLD, micro off", (a, 1 - a, 0, 0, 0), (0, 0, q, 0, 1 - q), False, B_NEW))

    print(f"{'design':<46}{'--- 26y proxy ---':^30}{'S':>7}{'H':>7}   {'--- real SPMO era ---':^26}")
    print(f"{'':<46}{'CAGR':>8}{'Sharpe':>8}{'MaxDD':>8}{'':>7}{'':>7}   {'CAGR':>8}{'Sharpe':>8}{'MaxDD':>8}")
    for label, A, D, micro, B in configs:
        W = dict(TARGET_WEIGHTS); W['A'] = A; W['D'] = D; W['B'] = B
        p = eval_proxy(P, mk_proxy(W, 'both' if micro else 'off'))
        r = eval_real(R, mk_real(W, micro))
        print(f"{label:<46}{p['cagr']*100:>7.2f}%{p['sharpe']:>8.3f}{p['mdd']*100:>7.1f}%"
              f"{p['s_sharpe']:>7.3f}{p['h_sharpe']:>7.3f}   {r['cagr']*100:>7.2f}%{r['sharpe']:>8.3f}{r['mdd']*100:>7.1f}%")
    print("\nbenchmarks: proxy QQQ 8.66% / 0.452 / -80.2%, SPY 8.46% / 0.519 / -55.4%;"
          "  real QQQ 18.39% / 0.937 / -35.5%, SPMO 17.39% / 0.938 / -28.3%")


if __name__ == '__main__':
    main()
