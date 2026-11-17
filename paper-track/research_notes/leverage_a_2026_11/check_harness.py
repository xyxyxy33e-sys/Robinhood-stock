"""Self-check of paper-track/harness_live.py against the recorded references. Prints the validation table. Research only."""
import sys, os
sys.dont_write_bytecode = True
PT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PT)
import numpy as np
import harness_live as HL
H = HL.H

def row(lab, track, ref, **kw):
    r, ds, tpy = HL.run_live(track, **kw); s = HL.stats(r)
    print(f"{lab:<66} {ds[0]}..{ds[-1]}  {s['c']*100:5.1f}% / {s['sh']:.3f} / {s['m']*100:6.1f}%   ref {ref}")
    return r

print('harness_live validation (CAGR / Sharpe / maxDD; Sharpe = mean*252/vol as harness.stats)\n')
print('REAL ETFs, Nov 2015 -> latest')
row('L1, highs as the recorded studies (file only), to 2026-11-10', 'real', '53.0% / 2.139 (STRATEGY.md); tax study 52.9% / 2.136 / -16.6%', d1='2026-11-10', use_live_highs=False)
row('L1, same highs, to latest', 'real', '(n/a: later sample)', use_live_highs=False)
r_nl = row('no L1 (cap 2.0 + VIXY 35%), to latest', 'real', '51.1% / 2.100 / -16.5% (vixy_sleeve_sweep)', l1=False)
row('DEFAULT: L1 with complete highs (AV full-day 09-08..11-10 + live), to latest', 'real', '(no reference; 50 sessions had no high in the recorded runs)')
# exact equality with the old harness plus the two patches
r_old, _, _ = H.run(True, cfg=dict(H.CUR, gross_cap=2.0), vixm_share=0.35, vixm_ret=HL._vixy_rets(H.RD, 'old')[0])
r_new, _, _ = HL.run_live('real', l1=False, vixy_source='old')
print(f"  no-L1, old-VIXY-series run_live == harness.run(cap 2.0, VIXY 35%) exactly: {np.allclose(r_old, r_new)} (max abs diff {np.abs(r_old - r_new).max():.2e})")
print('\nPROXY 2001 -> latest')
row('L1 (file-only highs), sleeve OFF on proxy', 'proxy', '34.0% / 1.474 (with L1)', use_live_highs=False, sleeve_proxy=False)
row('no L1, sleeve OFF on proxy', 'proxy', '31.8% / 1.409 / -22.1% (cap, no L1, no sleeve)', l1=False, sleeve_proxy=False)
row('L1 (file-only highs), sleeve ON from 2011', 'proxy', '(no reference)', use_live_highs=False)
row('no L1, sleeve ON from 2011', 'proxy', '(no reference)', l1=False)
row('DEFAULT: L1 complete highs, sleeve ON from 2011', 'proxy', '(no reference)')
row('L1 complete highs, sleeve OFF', 'proxy', '(no reference)', sleeve_proxy=False)
