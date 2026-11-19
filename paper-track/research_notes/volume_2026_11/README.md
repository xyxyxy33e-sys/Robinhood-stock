# Does QQQ volume add anything? (2026-11-19) — No.

Prompted by a post: "half the sessions since the downtrend flip closed red on above-average volume — institutions
distributing". Volume: QQQ daily from Yahoo (1999-2026). Distribution day = red close on volume above its 50-day
average; D25 = count in the last 25 sessions (latest 16 Nov: 10, in state E). `vtest.py`, `vbt.py` (run from a
scratch copy of `review_2026_11/harness.py` with today's partial row skipped).

1. Forward QQQ returns by state, D25 terciles: no consistent sign. A: high D25 +0.7pp/20d in 2001-15, -1.2pp in
   2015-26 (|t| < 1.5). E/F: high D25 is followed by *better* 20-day returns in both eras (washout), not worse.
   Heavy-volume red days do not predict the next day in any state.
2. Rules in the current design (2.0x cap, sleeve off on every arm), real 2015-26 / proxy 2001-26 / holdout:
   current 45.2% 1.93 -19.3% / 31.8% 1.41 -22.1% / 22.4% 1.07. Every variant — A halved or TQQQ out, D to cash,
   all risk halved, deep-E QQQ skipped, each at D25 >= 8/10/12 — is lower on CAGR and Sharpe in all three; max
   drawdown is unchanged or 0.5pp better in one case. Best case (A, D25 >= 12) ties. Not adopted.
