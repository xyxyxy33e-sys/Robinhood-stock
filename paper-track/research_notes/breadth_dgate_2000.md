# Research line `breadth_dgate_2000` (2026-09-10): does the D-row breadth gate survive 2000-2002?

Research only. Nothing here is applied; the discipline in BRIEFING.md (ADDENDUM 2026-09-10) binds.
Script: `paper-track/breadth_dgate_2000.py` (run from the repo root; `DGATE_STAGE=1` = data + validation only;
`DGATE_ONLY=comp,rut` restricts Step 3 to named proxies). Full log: `paper-track/research_notes/breadth_dgate_2000_run.log`.

## 0. Summary and verdict

**Question.** The `breadth_signal` line found, post hoc, that *"effective state D AND the 60-day change of log(QQEW/QQQ)
in its trailing-252 bottom quintile -> hold the D row (100 % QLD) in cash"* passes every control on 2007-07+ rows.
QQEW starts 2006-04, so the dot-com bear was never tested. This line extends the test to the full 2000-07..2026-08
proxy window with breadth proxies that carry no survivorship bias.

**Answer.**

1. **A point-in-time equal-weight Nasdaq-100 cannot be built from public data.** The membership *is* reconstructible
   (QQQ prospectus Schedules of Investments, Sept-30 1999..2006), but only 28-33 % of the 2000-2002 members and 45-52 %
   of the 2003-2006 members have full-year prices on Yahoo — the delisted/acquired names are gone. That series
   (`ndxsurv`) is survivorship-biased and is reported as illustrative only.
2. **The rule is untestable on 2000-2002, for a structural reason, not a data reason.** Effective state D (price below
   the 50d, above the 200d) occurred on **6 days** in 2000-07..2003-03 (2000-08-07..09 and 2000-08-14..16) and on **zero
   days in 2001 and 2002** — QQQ never closed above its 200d SMA in those two years. Whatever breadth said, the gate had
   nothing to act on; every proxy's gated series is identical to live on that slice (gate − live Sharpe = +0.000). "Does
   it survive dot-com?" has the answer "it never fires in dot-com". That is not evidence for or against it.
3. **On the part of the extension that does exist (2003-2006, 177 D days) the survivorship-free proxies show no
   effect**: gate − live Sharpe on the 2000-2006 slice is +0.000 / −0.006 / +0.002 for NYSE-Composite/NDX,
   Composite/NDX and Russell-2000/NDX; the per-day QLD-leg return on gated D days is +5..+8 bp vs +12 bp on other D days
   (diff-t −0.1..−0.2). Only the survivorship-biased survivor series shows a gain there (+0.179), which is exactly the
   direction survivorship bias pushes it.
4. **The fallbacks reproduce the search-era result and not the holdout result even on 2007+.** On the same 4,800 rows,
   Composite/NDX, Russell-2000/NDX and NYSE/NDX pass the formal validation (both-era > live and > constant-D at matched
   capital, block bootstrap P(≤0) < 0.05 vs constant-D at 20d and 60d), but their holdout margins over the constant-D
   control are +0.021 / +0.034 / +0.091 against QQEW's +0.178, and Russell-3000/NDX and Wilshire/NDX fail the holdout
   outright. On the common 2004-07+ rows the S&P analogue (RSP/SPY, +0.007 holdout) and the composite fallback (−0.003)
   are equally weak: with the longer history the objection "the S&P analogue is weak in the holdout" becomes "**every
   survivorship-free proxy is weak in the holdout; only QQEW/QQQ itself shows a holdout gain, and its holdout is
   2007-07..2015-10 (8 years, 65 gated days)**".
5. **The window sensitivity is not smooth with the longer history.** Composite/NDX at 100 % depth vs constant-D (S/H):
   10d +0.02/−0.08, 20d +0.17/+0.03, 40d +0.19/+0.07, 60d +0.21/+0.01, 90d +0.24/−0.05, 120d +0.25/−0.01, 250d +0.10/+0.01.
   Russell/NDX: 40d +0.07/+0.04, 60d +0.17/+0.02, 90d +0.22/−0.01, 120d +0.11/−0.04. The search-era gain is present at
   every window ≥ 20d (it is a 2018/2020/2022 crash-avoidance effect); the holdout sign flips from window to window.
6. **26-year figures** (2000-07..2026-08; live 22.18 % / 0.913 / −33.6 %, S 1.103, H 0.768, real 1.248):

   | proxy | rule | CAGR / Sharpe / MDD | S | H | vs live S/H | vs const-D S/H | boot vs const-D P(≤0) 20d/60d | real Sh |
   |---|---|---|---|---|---|---|---|---|
   | Composite/NDX | gate 100 % | 24.59 % / 1.024 / −35.1 % | 1.345 | 0.785 | +0.243 / +0.017 | +0.212 / +0.012 | 0.024 / 0.035 | 1.502 |
   | Composite/NDX | gate 50 % | 23.51 % / 0.980 / −34.3 % | 1.241 | 0.783 | +0.139 / +0.015 | +0.122 / +0.012 | 0.018 / 0.014 | 1.386 |
   | Russell 2000/NDX | gate 100 % | 24.22 % / 1.006 / −30.6 % | 1.292 | 0.792 | +0.190 / +0.024 | +0.166 / +0.020 | 0.051 / 0.047 | 1.514 |
   | Russell 2000/NDX | gate 50 % | 23.29 % / 0.968 / −31.3 % | 1.212 | 0.785 | +0.110 / +0.017 | +0.097 / +0.014 | 0.026 / 0.030 | 1.393 |
   | NYSE Comp/NDX | gate 100 % | 24.48 % / 1.013 / −33.3 % | 1.262 | 0.822 | +0.160 / +0.054 | +0.143 / +0.051 | 0.018 / 0.025 | 1.375 |
   | NYSE Comp/NDX | gate 50 % | 23.40 % / 0.970 / −33.3 % | 1.193 | 0.801 | +0.091 / +0.033 | +0.081 / +0.031 | 0.006 / 0.011 | 1.319 |
   | survivor EW (illustrative) | gate 100 % | 28.45 % / 1.149 / −28.5 % | 1.332 | 1.007 | +0.229 / +0.176 | +0.203 / +0.168 | 0.000 / 0.000 | 1.490 |

   The sign-flip placebo loses on every proxy (−0.10..−0.19 vs constant-D in the search era). The gate is on for
   101-187 of 934 D days; its 26-year value is the 2018-10 / 2020-02 / 2022-01 episodes it was found on.

**Verdict.** *Does the rule survive 2000-2002?* It is not tested by 2000-2002: the D state did not exist there. *Is the
window sensitivity smooth?* No. *Does the gate fire in dot-com D episodes and help?* It fires on 0 of the 6 D days; on
the 2003-2006 D days the survivorship-free versions do nothing. The longer history therefore adds no positive evidence:
the holdout gain remains a property of one instrument pair (QQEW/QQQ) over one 8-year window, is not reproduced by any
survivorship-free proxy of the same idea in the same window beyond +0.02..+0.09, and the one series that "confirms" it
before 2007 is the survivorship-biased one. Recommendation: **pre-register only** — freeze the rule exactly as stated
(qqew_60 trailing-252 pct < 0.20, effective state D only, D row to cash), track it forward on the paper track, and do
not apply it, not at half depth either; a half-depth application is the same bet with the same evidence. Today (2026-09-09)
every proxy reads mid-to-top of its range (qqew 0.82, composite 0.95, NYSE 0.69, Russell 0.35) and the last proxy row is
state A: the rule would be off regardless.

## 1. Step 1 — point-in-time equal-weight Nasdaq-100: provenance and coverage

Sources tried, in order: the Wikipedia "Nasdaq-100" page (its change table lives on "Historical components of the
Nasdaq-100", 226 rows, **2007-02 onward only**); the Unofficial NASDAQ-100 Site (year-end rosters 1985-1998 and
2014-2025, index of changes populated 2008+; **1999-2007 "coming soon"**); SEC EDGAR, Nasdaq-100 Trust / Invesco QQQ
(CIK 1067839): the annual 485BPOS prospectus carries the audited Schedule of Investments as of Sept-30 — the fund is
full-replication, so its holdings are the index. Eight snapshots 1999-09-30..2006-09-30 were parsed (98-100 issuer names
each, 226 unique after normalising), issuer names mapped to era tickers by hand, and all 198 unique tickers probed on
Yahoo (1 attempt each, browser User-Agent, 2 s spacing). A ticker counts as covering a roster year only if its Yahoo
history spans Oct (yr−1)..Sep (yr); this excludes reused tickers (ADPT is Adaptimmune from 2019, DELL relisted 2016,
MNST is Monster Beverage, ATHM is Autohome 2013, CHIR 2018, CNET 2009, SPOT is Spotify, S is SentinelOne, ...).

```
roster (Sep-30)  members ticker on Yahoo full-year data coverage   not covered (first 15 tickers)
1999-09-30            98              48             29      30%   ADCT ADPT ALTR ANDW APCC APOL ATHM ATML BBBY BGEN BMC BMET CATP CEFT CEXP
2000-09-30            98              45             27      28%   ADCT ADLAC ADPT ALTR AMCC APCC APOL ATHM ATML BBBY BGEN BMC BMET BVSN CEFT
2001-09-30            91              43             27      30%   ABGX ADCT ALTR AMCC ARBA ATHM ATML BBBY BEAS BGEN BMET BRCM BVSN CEFT CHIR
2002-09-30            97              46             32      33%   ABGX ADCT ADRX ALTR AMCC APOL ATML BBBY BEAS BGEN BMET BRCD BRCM CDWC CEFT
2003-09-30            98              55             44      45%   ADCT ALTR APCC APOL BBBY BEAS BGEN BMET BRCD BRCM CDWC CEPH CHIR CMVT CPWR
2004-09-30            98              56             46      47%   ALTR APCC APOL ATYT BBBY BEAS BMET BRCM CDWC CEPH CHIR CMVT CPWR CTXS DELL
2005-09-30            98              56             47      48%   ALTR APCC APOL ATYT BBBY BEAS BMET BRCM CDWC CELG CHIR CMVT CTXS DELL DISH
2006-09-30            98              59             51      52%   ALTR AMLN APCC APOL ATVI ATYT BBBY BEAS BMET BRCM CDWC CELG CKFR CMVT CTXS
```

Coverage is below 80 % in every year (below a third in 2000-2002). Per the brief this series is
**survivorship-biased / illustrative ONLY**. It was still built (`data/ndx_survivor_ew_daily.csv`: equal-weight,
daily-rebalanced chain of the 27-51 members with data, roster switching each Oct-1, spliced onto QQEW at 2006-07-03) and
carried through every table under the name `ndxsurv`, labelled as such, so the reader can see what a survivor basket
does — it "confirms" the rule in 2003-2006, which is what survivorship bias would produce (the members that were about
to be dropped are missing, so the survivor basket's relative-strength dips are the mild ones).

## 2. Step 2 — survivorship-free fallbacks and their validation against QQEW/QQQ

Fallbacks (all numerator / NASDAQ-100 from FRED; 60-day change of the log ratio; trailing-252 percentile, inclusive,
ties split; attached to rows by date, value at the close of d0): `comp` NASDAQCOM/NASDAQ100 (FRED), `rut` Russell 2000
(^RUT), `rua` Russell 3000 (^RUA), `nya` NYSE Composite (^NYA), `w5k` Wilshire 5000 (^W5000). Value Line Geometric was
not obtainable (not on Yahoo; stooq behind a JS challenge; FRED has no Wilshire/Russell series any more). Provenance in
`data/breadth_provenance.md`. Yahoo ^NDX agrees with FRED NASDAQ100 on 6,962 dates (1999 tick noise only); FRED is used.
Every fallback has a percentile from 1999-03-29, so all 6,575 proxy rows are covered (same-rows rule satisfied with the
full live baseline). Alignment check (contemporaneous corr of QQQ d0→d1 with the log-ratio change d0→d1): qqew −0.24,
comp −0.44, rut −0.43, rua/nya/w5k −0.67; predictive pairing ≤ |0.01| — the series are what they claim to be.

Agreement with qqew_60 on the 4,800 rows 2007-07-27..2026-08-26 (727 state-D rows):

```
  series       corr chg corr pct agree all  agree D Jaccard D  flags D (qqew/this/both)
  comp_60         0.415    0.494     0.762    0.781     0.264                124/149/57
  rut_60          0.581    0.557     0.769    0.788     0.198                124/106/38
  rua_60          0.569    0.581     0.764    0.792     0.132                 124/73/23
  nya_60          0.608    0.591     0.753    0.776     0.160                124/101/31
  w5k_60          0.572    0.589     0.765    0.795     0.144                 124/75/25
  rsp_60          0.703    0.696     0.804    0.755     0.172                124/128/37
```

The fallbacks are moderately correlated with QQEW/QQQ (0.42-0.61 on the 60d change) but the bottom-quintile flag on
D days overlaps only 13-26 % (Jaccard): they are different signals that share a factor, not the same signal.

The D-gate re-run on the same rows (the validation that matters; same-rows live 26.09 % / 1.006 / −33.6 %, S 1.103,
H 0.876; deltas are S/H Sharpe):

```
  depth 100%                CAGR/Sh/MDD             S      H     on | vs live        | const-D (q)      | boot vs constD P<=0 20d/60d | vs qqew-gated Sh CI 20d      | real Sh
  qqew_60 (reference)  31.71% / 1.218 / -28.5%  1.332  1.065  124 | +0.229/+0.189 | +0.205/+0.178   | 0.002 / 0.000               |                              | 1.490
  comp_60              29.66% / 1.156 / -35.1%  1.345  0.910  149 | +0.243/+0.033 | +0.212/+0.021   | 0.025 / 0.024               | [-0.191,+0.069] P 0.83       | 1.502  VALIDATES (weak H)
  rut_60               29.06% / 1.132 / -30.6%  1.292  0.920  106 | +0.190/+0.044 | +0.166/+0.034   | 0.046 / 0.048               | [-0.246,+0.077] P 0.85       | 1.514  VALIDATES (weak H)
  rua_60               28.83% / 1.114 / -33.3%  1.295  0.873   73 | +0.193/-0.003 | +0.176/-0.011   | 0.045 / 0.029               | [-0.258,+0.038] P 0.91       | 1.382  FAILS (holdout)
  nya_60               29.36% / 1.141 / -33.3%  1.262  0.977  101 | +0.160/+0.101 | +0.138/+0.091   | 0.019 / 0.016               | [-0.223,+0.065] P 0.85       | 1.375  VALIDATES
  w5k_60               28.25% / 1.095 / -33.3%  1.272  0.861   75 | +0.169/-0.015 | +0.153/-0.023   | 0.082 / 0.075               | [-0.270,+0.025] P 0.94       | 1.365  FAILS
  rsp_60               29.14% / 1.139 / -31.1%  1.284  0.948  128 | +0.181/+0.072 | +0.153/+0.060   | 0.059 / 0.050               | [-0.219,+0.060] P 0.85       | 1.412  FAILS (boot)
  depth 50%: qqew +0.115/+0.097 vs const-D; comp +0.122/+0.017; rut +0.097/+0.023; rua +0.097/+0.001; nya +0.079/+0.054; w5k +0.085/-0.006; rsp +0.092/+0.038
```

Validation rule (fixed before running): both-era Sharpe above same-rows live AND above the constant-D control at matched
capital, and block bootstrap vs constant-D P(≤0) < 0.05 at both 20d and 60d. `comp`, `rut`, `nya` pass; `rua`, `w5k`
fail (holdout); `rsp` fails (bootstrap at 20d). Honest reading of the passes: the bootstrap of *fallback-gated minus
QQEW-gated* cannot distinguish them (CIs span zero), but that is a low bar with 4,800 rows and 100-150 gated days — the
point estimates say the fallbacks reproduce the **search-era** gain (+0.21 / +0.17 / +0.14 vs +0.21) and only a fraction
of the **holdout** gain (+0.02 / +0.03 / +0.09 vs +0.18). Two of three would not pass a "holdout margin ≥ +0.05" bar.
They are used as extensions below with that caveat printed on every table.

## 3. Step 3 — the full 2000-07+ run

Rows 6,575 (2000-07-03..2026-08-26), live 22.18 % / 0.913 / −33.6 %, S 1.103, H 0.768, exposure 67.7 %.
Controls per cell: same-rows live; constant-D de-lever at matched deployed capital (q bisected); live scaled to matched
capital (k); circular block bootstrap 20d/60d, 2,000 draws, vs live and vs constant-D; sign flip; real weekly rows.

```
[comp_60]  gate 100%  24.59% / 1.024 / -35.1%  S 1.345 H 0.785  exp 65.1% on 187 | vs live +0.243/+0.017 | const-D q=0.807 +0.212/+0.012 | k-live +0.237/+0.014 | real 1.502
             boot vs live 20d Sh CI [-0.003,+0.240] P 0.028; 60d [+0.004,+0.239] P 0.022; vs constD 20d [+0.001,+0.208] P 0.024; 60d [-0.005,+0.205] P 0.035
           gate  50%  23.51% / 0.980 / -34.3%  S 1.241 H 0.783  exp 66.4% on 187 | vs live +0.139/+0.015 | const-D q=0.903 +0.122/+0.012 | k-live +0.136/+0.015 | real 1.386
             boot vs live 20d [+0.010,+0.129] P 0.011; 60d [+0.008,+0.131] P 0.011; vs constD 20d [+0.007,+0.113] P 0.018; 60d [+0.007,+0.118] P 0.014
[rut_60]   gate 100%  24.22% / 1.006 / -30.6%  S 1.292 H 0.792  exp 65.8% on 136 | vs live +0.190/+0.024 | const-D q=0.855 +0.166/+0.020 | k-live +0.186/+0.022 | real 1.514
             boot vs live 20d [-0.009,+0.211] P 0.036; 60d [-0.004,+0.204] P 0.028; vs constD 20d [-0.014,+0.194] P 0.051; 60d [-0.012,+0.181] P 0.047
           gate  50%  23.29% / 0.968 / -31.3%  S 1.212 H 0.785  exp 66.8% on 136 | vs live +0.110/+0.017 | const-D q=0.928 +0.097/+0.014 | k-live +0.107/+0.016 | real 1.393
             boot vs live 20d [+0.001,+0.118] P 0.022; 60d [+0.005,+0.112] P 0.013; vs constD 20d [-0.000,+0.104] P 0.026; 60d [-0.003,+0.108] P 0.030
[nya_60]   gate 100%  24.48% / 1.013 / -33.3%  S 1.262 H 0.822  exp 66.4% on 101 | vs live +0.160/+0.054 | const-D q=0.899 +0.143/+0.051 | k-live +0.157/+0.053 | real 1.375
             boot vs live 20d [+0.010,+0.197] P 0.014; 60d [+0.008,+0.206] P 0.014; vs constD 20d [+0.005,+0.180] P 0.018; 60d [-0.000,+0.188] P 0.025
           gate  50%  23.40% / 0.970 / -33.3%  S 1.193 H 0.801  exp 67.0% on 101 | vs live +0.091/+0.033 | const-D q=0.950 +0.081/+0.031 | k-live +0.089/+0.032 | real 1.319
             boot vs live 20d [+0.011,+0.109] P 0.005; 60d [+0.012,+0.113] P 0.006; vs constD 20d [+0.007,+0.101] P 0.006; 60d [+0.009,+0.105] P 0.011
[ndxsurv_60, ILLUSTRATIVE, rows 6466 from 2000-12-06; live there 23.38% / 0.950 S 1.103 H 0.830]
           gate 100%  28.45% / 1.149 / -28.5%  S 1.332 H 1.007  exp 66.2% on 167 | vs live +0.229/+0.176 | const-D q=0.836 +0.203/+0.168 | boot P 0.000 everywhere | real 1.490
           gate  50%  26.01% / 1.060 / -30.4%  S 1.231 H 0.927  exp 67.3% on 167 | vs live +0.128/+0.096 | const-D q=0.918 +0.114/+0.092 | real 1.379
```

Over 26 years the survivorship-free gates add +0.09..+0.11 full-sample Sharpe at 100 % depth, essentially all of it from
the search era (holdout +0.01..+0.05); the 50 % depth adds about half with the same shape. Bootstrap intervals vs
constant-D touch zero at 100 % depth for `comp` and `rut` (P 0.024-0.051) and clear it for `nya` and for the 50 % depth.

Leave-one-regime-out (Sharpe diff vs constant-D / vs live on the retained rows; then the dropped slice on its own,
gate − live):

```
                                   comp 100%            rut 100%             nya 100%             | slice alone gate-live: comp   rut    nya
  drop dot-com 2000-07..2003-03    +0.103 / +0.125      +0.088 / +0.105      +0.099 / +0.112      |  (687 d)              +0.000 +0.000 +0.000
  drop 2000-2006 (pre-QQEW)        +0.126 / +0.146      +0.107 / +0.122      +0.120 / +0.131      |  (1633 d)             -0.006 -0.002 +0.000
  drop GFC 2007-09                 +0.117 / +0.138      +0.089 / +0.106      +0.109 / +0.122      |  (756 d)              -0.102 -0.006 -0.079
  drop COVID 2020                  +0.072 / +0.081      +0.055 / +0.063      +0.064 / +0.070      |  (253 d)              +1.335 +1.335 +1.335
  drop 2022 bear                   +0.083 / +0.100      +0.086 / +0.099      +0.095 / +0.105      |  (251 d)              +0.476 +0.000 +0.000
  drop SPMO era 2015-11+           +0.012 / +0.017      +0.020 / +0.024      +0.051 / +0.054      |  (2719 d)             +0.243 +0.190 +0.160
```

Dropping the SPMO era leaves +0.01..+0.05 vs constant-D: the pre-2015 history contributes almost nothing, and the
2000-2006 slice contributes exactly nothing. COVID 2020 (one two-day episode, 2020-02-25/26) is worth +1.3 Sharpe on its
own 253-day slice for every proxy — the same episode found in the original line.

Sign-flip placebo (gate when pct > 0.80), 100 % / 50 %: comp −0.183/−0.084 vs constant-D in S, −0.056/−0.023 in H; rut
−0.187/−0.079, −0.061/−0.025; nya −0.100/−0.035, −0.070/−0.027. Real rows 1.07-1.23 vs 1.248. The flip loses everywhere.

Threshold sweep (100 % depth, vs constant-D S/H):

```
  thr    comp_60            rut_60             nya_60             ndxsurv_60 (illustr.)
  0.10   +0.193 / +0.024    +0.189 / +0.002    +0.117 / +0.043    +0.131 / +0.116
  0.20   +0.212 / +0.012    +0.166 / +0.020    +0.143 / +0.051    +0.203 / +0.168
  0.30   +0.312 / +0.081    +0.318 / -0.011    +0.085 / +0.028    +0.195 / +0.117
  0.40   +0.318 / +0.056    +0.286 / +0.027    +0.147 / -0.033    +0.152 / +0.079
  0.50   +0.211 / -0.002    +0.200 / +0.017    +0.185 / -0.025    +0.117 / +0.083
```

Window sweep (100 % depth, thr 0.20, full rows, vs constant-D S/H; "smooth" would mean the sign and rough size of both
columns persist across neighbouring windows):

```
  window   comp_60            rut_60             nya_60             ndxsurv_60 (illustr.)
   10d     +0.018 / -0.079    +0.112 / -0.113    +0.005 / +0.027    -0.103 / +0.064
   20d     +0.173 / +0.028    +0.242 / -0.001    +0.065 / +0.023    -0.074 / -0.017
   40d     +0.192 / +0.069    +0.065 / +0.041    +0.086 / +0.027    +0.069 / +0.114
   60d     +0.212 / +0.012    +0.166 / +0.020    +0.143 / +0.051    +0.203 / +0.168
   90d     +0.235 / -0.051    +0.222 / -0.009    -0.017 / +0.024    -0.023 / +0.072
  120d     +0.251 / -0.010    +0.112 / -0.041    +0.075 / -0.045    +0.087 / +0.063
  250d     +0.099 / +0.009    +0.013 / -0.022    +0.015 / -0.062    +0.115 / +0.039
```

Not smooth. The search-era column is positive at every window ≥ 20d for comp and rut (the crash episodes are long
enough to be caught by any window), while the holdout column changes sign between adjacent windows for every proxy
(comp 40d +0.07 → 60d +0.01 → 90d −0.05; rut 40d +0.04 → 90d −0.01 → 120d −0.04; nya 60d +0.05 → 120d −0.05). 60d is
again the best or near-best of seven for the two-era criterion — the same selection effect the original line reported.

## 4. Dot-com D episodes and per-day attribution

Effective state D in 2000-07-01..2003-03-31: **2 episodes, 6 days** (2000-08-07..09, QLD leg −5.6 %; 2000-08-14..16,
+5.7 %). Raw (pre-overlay) state D: the same 6 days. 2001: 0 D days (159 F, 0 A, 0 E). 2002: 0 D days. No proxy's gate
was on for any of the 6 days (all four percentiles were above 0.20 in early August 2000). D days by year for the
extension: 2000 6, 2001 0, 2002 0, 2003 20, 2004 37, 2005 82, 2006 38.

Per-day QLD-leg statistics on gated vs other state-D days:

```
  series      slice        gated n  mean bp      t   hit | other n  mean bp   hit | diff t
  comp_60     full             187    -30.3  -1.23  0.51 |     747     29.8  0.57 | -2.28
  comp_60     2000-2006         38      7.6   0.21  0.55 |     145     11.9  0.52 | -0.11
  comp_60     2007+            149    -40.0  -1.36  0.50 |     602     34.2  0.59 | -2.36
  rut_60      full             136    -33.9  -1.10  0.50 |     798     26.6  0.57 | -1.88
  rut_60      2000-2006         30      5.4   0.16  0.53 |     153     12.1  0.52 | -0.17
  rut_60      2007+            106    -45.0  -1.18  0.49 |     645     30.0  0.58 | -1.89
  nya_60      full             101    -56.3  -1.36  0.48 |     833     26.8  0.57 | -1.96   (2000-2006: 0 gated days)
  ndxsurv_60  full             167    -64.5  -2.28  0.47 |     761     35.9  0.58 | -3.37
  ndxsurv_60  2000-2006         43    -47.0  -1.38  0.42 |     134     29.6  0.56 | -2.00   (survivorship-biased)
  ndxsurv_60  2007+            124    -70.5  -1.94  0.48 |     627     37.2  0.59 | -2.85   (= qqew_60)
```

In 2000-2006 the survivorship-free gates select D days that are indistinguishable from the other D days (+5..+8 bp vs
+12 bp, diff-t −0.1..−0.2, hit rates 0.53-0.55 vs 0.52); the NYSE gate never fires there at all. The survivor basket
"finds" −47 bp days — and it is the series whose 2003-2006 members were selected for having survived.

## 5. RSP/SPY vs NASDAQCOM/NASDAQ100 vs QQEW/QQQ on common rows

```
  (rsp rows 2004-07+, n=5556; live 25.42% / 0.994 S 1.103 H 0.886)
  rsp_60  100%  27.51% / 1.097 / -31.1%  S 1.284 H 0.913  | vs live +0.181/+0.026 | const-D +0.153/+0.007 | real 1.412
  comp_60 100%  28.30% / 1.123 / -35.1%  S 1.345 H 0.905  | vs live +0.243/+0.019 | const-D +0.212/-0.003 | real 1.502
  rsp_60   50%  26.60% / 1.058 / -31.6%  S 1.209 H 0.908  | vs live +0.107/+0.022 | const-D +0.092/+0.011 | real 1.345
  comp_60  50%  27.00% / 1.071 / -34.3%  S 1.241 H 0.904  | vs live +0.139/+0.018 | const-D +0.122/+0.006 | real 1.386
  (qqew rows 2007-07+, n=4800; live 26.09% / 1.006 S 1.103 H 0.876)
  qqew_60 100%  31.71% / 1.218 / -28.5%  S 1.332 H 1.065  | vs live +0.229/+0.189 | const-D +0.205/+0.178 | real 1.490
  rsp_60  100%  29.14% / 1.139 / -31.1%  S 1.284 H 0.948  | vs live +0.181/+0.072 | const-D +0.153/+0.060 | real 1.412
  comp_60 100%  29.66% / 1.156 / -35.1%  S 1.345 H 0.910  | vs live +0.243/+0.033 | const-D +0.212/+0.021 | real 1.502
```

With the longer history the S&P analogue and the Nasdaq composite fallback look alike: both carry the search-era gain
(+0.15..+0.21 vs constant-D) and neither carries a holdout gain (−0.003..+0.06). The "S&P analogue is weak" objection is
not specific to the S&P: it is the general finding that the holdout evidence for this rule exists only in the QQEW/QQQ
pair on 2007-07..2015-10.

## 6. Candidate count

54 gate cells in this line (7 proxies × 2 depths on the validation rows + 6 × 2 on the common-window tables + 4 proxies ×
(2 depths + 5 thresholds + 7 windows) on the full rows), plus 8 sign-flip placebos not counted. Cumulative with the
`breadth_signal` line: 224 candidates behind one post-hoc rule. The validation criterion for a fallback was fixed
before the validation table was printed; the D-only scope and the 60d window were inherited from the earlier line.

## 7. What would have to be true for the rule to be usable

Either (a) a licensed point-in-time Nasdaq-100 equal-weight total-return history (Nasdaq's NDXE / NETR indices exist
from 2005-12 only, so even that does not reach dot-com) shows the gate selecting −50 bp D days in 2003-2006 the way the
survivor basket does; or (b) the forward paper-track record accumulates enough gated D days (currently 124 in 19 years,
≈ 6-7 per year) to test the holdout claim out of sample — at that rate a 60-day test takes roughly a decade. Neither
condition is met today; the 2000-2002 window cannot ever meet it because the D state did not occur.
