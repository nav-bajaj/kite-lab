# TASKS

Status of every thread in this study. Done items record the verdict so they
are not repeated.

## Done — with verdicts

| # | Item | Verdict |
|---|---|---|
| 1 | L6 v2 exit-buffer sweep (0/5/10/15/20), IS + OOS + to date | Turnover halves; OOS return a wash. Not adopted. |
| 2 | Slippage sensitivity (20/40/60bps) | Buffer only pays if real slippage >~40bps. Unmeasured. |
| 3 | Extended buffer grid (25/30/40) | OOS peaks at 20-25; IS keeps climbing — classic divergence. |
| 4 | Investor-experience lens on L6 | Buffer improves every metric slightly; not enough to change category. |
| 5 | COMBO full-history rebuild | **Max DD is -36.8%, not -16.4%.** Prior figure was a 2020+ window artifact. |
| 6 | Exit buffer on COMBO | Best buffer case found: -5.8pp max DD, half the turnover, flat CAGR. |
| 7 | COMBO regime-signal experiment (index + mechanic) | Index swap barely helps; short-lookback ROC does. |
| 8 | ROC lookback x confirm grid (35 cells) | Optimum is a contiguous plateau. Long lookbacks are worse than nothing. |
| 9 | Overlay on L6 v2 | **No.** Costs 6-14pp CAGR; V-shaped drawdowns are the wrong target. |
| 10 | Overlay on OM25 v3 | **Yes.** Strongest case of the three portfolios. |
| 11 | OM25: overlay as replacement for the 20% stop | Overlay wins; the two are substitutes, not complements. |
| 12 | Conditional (risk-off-only) stop | **No.** 75-78% of stop triggers already occur in risk-off. |
| 13 | Tilt swap to N500 ROC31 | **No.** ~1pp gain, kills pre-2015 reproducibility. |
| 14 | Tilt swap to N100 ROC31 | Best standalone tilt (16y evidence); redundant once an overlay runs. |
| 15 | N100 as the overlay index | **Adopted in the candidate.** Equivalent to N500, unlocks 13.1y walk-forward. |
| 16 | Walk-forward (N500, 8.1y and N100, 13.1y) | Risk benefit survives intact; return benefit does not. |
| 17 | L6 simplest-overlay forms (timing x action) | Entry gate is cheapest and reduces trading; still not recommended. |
| 18 | Production-number audit | Dashboard reproduces. `docs/portfolios.md` does not. |
| 19 | Acceptance re-audit vs original pass criteria | All four portfolios still PASS on today's data. |
| 20 | Recent-period check on the candidate | Behind on return in 2026; the March/April V-shape cost it. |
| 21 | Year-by-year, trailing, terminal wealth | Protection costs ~31% of 13-year terminal wealth (walk-forward). |
| 22 | Investor-pitch statistics | 1y/2y horizon claims supportable; 3y/5y are not. |
| 23 | SIP analysis | Candidate wins at 2y/3y on median *and* worst — inverts the lump-sum verdict. |

## Open — founder decisions

| # | Item | Why it matters |
|---|---|---|
| 24 | Ship the OM25 candidate, or not | ~31% of terminal wealth for 12pp of drawdown. Not a research question. |
| 25 | Accept single-name tail risk with the stop removed | Sample contains no 2008-style event; its verdict on stops is not evidence about tails. |
| 26 | Fix or retract `docs/portfolios.md` OM25 OOS row | **Client-facing.** 44.78% does not reproduce and contradicts its own source. |
| 27 | Adopt a product-grade acceptance bar | All four portfolios fail it today; the candidate passes 5 of 6. |
| 28 | Dashboard windows all start post-COVID-bottom | Structurally excludes every bear. Add a full-cycle number. |
| 29 | Standardise the Sharpe convention | Dashboard uses rf=5%, docs use rf=0, shown side by side. |

## Open — work not yet done

| # | Item | Note |
|---|---|---|
| 30 | Walk-forward the **tilt** choice | Only the overlay was walk-forwarded. |
| 31 | Backfill NIFTY 500 index history pre-2015 | Would allow testing on 2008 and 2011. Highest-value data task. |
| 32 | Measure real slippage from live fills | The L6 exit-buffer verdict depends on it. |
| 33 | Model the regime dial at allocation level | Operationally simplest option; never modelled. |
| 34 | Faster re-entry rule after risk-off | Cash currently redeploys only at the next bi-weekly rebalance. |
| 35 | Test the overlay on COMBO with N100 ROC | COMBO work predates the N100 finding. |
