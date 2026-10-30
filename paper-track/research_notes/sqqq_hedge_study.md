# SQQQ hedge in E/F (2026-10-30) — prompted by alphaAI's "Leveraged Nasdaq"

**alphaAI (desk review, 2026-10-30).** alphaAI Capital Management LLC, SEC-registered (CRD 316128).
- **Firm size:** Form ADV amendment of 21 Oct 2026 reports 1 employee, 205 accounts and $5,217,537 under management, against the site's "Join thousands".
- **Strategy:** VGT base, TQQQ added in strong trends, SQQQ in sustained downtrends (never with TQQQ), traded daily, driven by "30+ ML models / 200+ predictors". No rules are published.
- **Performance:** every figure on the public pages is blacked out and shown only after sign-up. No dates, no live/backtest label and no net-of-fee statement were found.
- **Earlier figures:** a search snippet of an earlier article described a backtest of ~32% annualized with a ~75% COVID drawdown. The page now redirects, so this is unverified.
- **Fees:** 0.50% a year ($4 a month under $10k). Alpaca custody.

**Test.** Script `sqqq_hedge_study.py` (pre-registered); output `sqqq_hedge_study_run.log`.
- **Base:** live design incl. the 0.5% zone buffer, VIXM out.
- **SQQQ:** synthetic, −3× QQQ total return + 4× cash, less the 0.95% expense ratio and a 0.3% financing spread on the 3× notional.

| arm | real Sharpe 4/20bp | proxy Sharpe 4/20bp | holdout | max DD real / proxy | verdict |
|---|---|---|---|---|---|
| live (BOXX in E/F) | 1.849 / 1.653 | 1.321 / 1.138 | 0.988 | −18.4 / −22.2 | — |
| F 25% SQQQ | 1.812 / 1.617 | 1.303 / 1.122 | 0.989 | −18.4 / −26.0 | fail |
| F 50% SQQQ | 1.730 / 1.541 | 1.234 / 1.063 | 0.942 | −21.0 / −29.7 | fail |
| F 100% SQQQ | 1.491 / 1.322 | 1.036 / 0.892 | 0.797 | −33.8 / −37.6 | fail |
| E and F 25% SQQQ | 1.739 / 1.542 | 1.270 / 1.089 | 0.981 | −20.8 / −29.0 | fail |

**Results.**
- **No arm passes.** The hedge pays in long bears: proxy F 100% SQQQ made 2001 +68%, 2002 +65% and 2008 +34%, against +10%, +1% and −1% for live.
- **Rebounds give it back and more.** 2003 +6% vs +41%, 2011 −28% vs −11%, 2023 +79% vs +97%.
- **Drawdowns deepen.** It adds up to 15 pp of max drawdown, because F is called after the fall and the sharpest rallies come out of bear markets.
- **Conclusion:** keep BOXX in E/F.
