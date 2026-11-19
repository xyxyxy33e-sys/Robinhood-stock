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

## 20-day / 100-day average volume ratio (owner follow-up, same day) — also no

`vtest2.py`, `vbt2.py`. Ratio median 0.97, 90th pct 1.29; latest 1.28 (16 Nov, state E).
- Forward 20-day QQQ by state: A flat to slightly worse with high ratio (-0.0pp / -0.7pp, |t| < 1.6). D slightly
  *better* with high ratio in both eras (+2.8pp, t 1.9 / +0.9pp, t 0.6): expanding volume in a pullback has come
  before rebounds, if anything. E/F mixed sign.
- Rules (A halved / TQQQ out / D to cash / all risk halved at ratio >= 1.15, 1.3, 1.5; deep-E skipped at
  >= 1.15/1.3/1.5 or <= 0.85): all lower or equal on CAGR and Sharpe in real, proxy and holdout. Best: A TQQQ out
  at >= 1.3 ties the holdout (22.4%, 1.076) but costs 1.4pp real. Not adopted.

## Volume above / below its 20-day and 100-day average lines (owner follow-up) — also no

`vline.py`. Flags: today's volume above its 20d line (44% of days), above its 100d line (41%), above both (32%),
below both (48%), 20d line above 100d line (44%). Latest 16 Nov: 43.6M vs 20d 49.7M / 100d 38.9M (between).
- By state, next-day and next-20-day QQQ, yes vs no: no flag keeps its sign across 2001-15 and 2015-26 in A, D, E
  or F; the few |t| ~2 cells (C, E next day) reverse in the other era.
- Rules: A halved / TQQQ out / D cash / all halved / deep-E skipped on "above both", "20d > 100d" and "above 20d":
  every one lower on CAGR (-1.6 to -11 pp real) and on Sharpe in real and proxy; holdout Sharpe at best ties
  (A halved on 20d > 100d: 1.076 vs 1.074 for -2.1 pp CAGR). Drawdown cuts (to -14% real at most) cost far more
  CAGR than holding less across the board (~0.53 pp drawdown per 1 pp CAGR). The daily flags also flip often,
  adding trades. Not adopted.

## 5-day average volume against the 20d and 100d lines (owner follow-up) — also no

`v5.py`. Latest 16 Nov: 5d 41.3M, 20d 49.7M, 100d 38.9M. Same tests. By state, no flag keeps its sign across eras.
Rules: every one lower on real CAGR; the only Sharpe gains are era-specific and opposite —
- A halved when the 5d avg is above both lines: real 42.0% / 1.887 (worse), proxy 30.1% / 1.414, holdout
  21.9% / 1.114, max DD -20.3%. Flags 23% of A days. But simply holding A at 0.85x-0.80x every day gives
  41.0-39.7% / 1.942 real, 1.428-1.434 proxy, 1.097-1.105 holdout, -21.3/-21.0%: as good or better on two of
  three eras, so the volume rule is "hold less in A", not timing.
- All risk halved when the 5d avg is below both: real 39.5% / 2.006 (better) but holdout 17.7% / 1.023 (worse).
Not adopted.
