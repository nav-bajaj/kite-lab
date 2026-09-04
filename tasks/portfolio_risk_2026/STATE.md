# STATE — resume here

Study ran 2026-09-04. Nothing was shipped; no production file was touched.

## What this study concluded, in order of importance

1. **A candidate configuration for OM25 v3 exists and is well-evidenced.**
   Add a NIFTY-100 31-session-ROC exposure overlay (100% invested risk-on,
   75% risk-off) and remove the 20% per-stock trailing stop. Over a **13.1-year
   walk-forward** (parameters re-picked annually from prior data only) it cut
   max drawdown from -34.8% to **-23.4%**, raised Sharpe from 1.88 to **2.03**,
   and cut time spent more than 20% underwater from 7.0% of days to **0.3%**.
   Full spec in `OM25_V3_CANDIDATE_SPEC.md`.

2. **It costs return, and the honest price is large.** Over 13.1 years,
   Rs 10L becomes **Rs 492.6L** under production and **Rs 341.9L** under the
   walk-forward candidate — the protection costs ~31% of terminal wealth. With
   hindsight on the parameters it costs nothing (Rs 491.2L), but nobody
   deploying forward has that. **This is the open decision.**

3. **Under SIP the verdict flips in the candidate's favour.** At 2- and
   3-year monthly-contribution horizons the candidate beats production on
   *both* median XIRR and worst case — and this holds for the walk-forward
   version too. Since retail invests monthly, this is the relevant framing.

4. **Production dashboard numbers are correct; `docs/portfolios.md` is not.**
   All four dashboard figures reproduce (max DD matches to 0.05pp). But
   `docs/portfolios.md`'s OM25 OOS row (44.78% CAGR) does not reproduce, and
   contradicts the research file it cites (43.57%). **Client-facing; unresolved.**

5. **Every dashboard window starts after the COVID bottom** (2020-07 to
   2021-01). They contain no bear market except COVID's tail, which is how
   COMBO's "-16.4% max drawdown" claim survived — its true full-history figure
   is **-36.8%**.

6. **L6 v2 should be left alone.** Overlays cost it 6-14pp of CAGR for ~10pp
   of drawdown and make the 12-month investor statistics worse. Its drawdowns
   are deep and fast (V-shaped); overlays are a tool for slow grinding
   declines.

## Decided (do not redo)

- Exit buffer on L6 v2: **no**. OOS return is a wash; only turnover improves.
  Revisit only if real slippage is measured above ~40bps.
- Exit buffer on COMBO: promising (-5.8pp max DD, half the turnover) but
  superseded — the regime work matters more.
- Swapping the score tilt to N500 ROC31: **no**. ~1pp gain, concentrates the
  design on one signal and permanently breaks pre-2015 reproducibility.
- Conditional (risk-off-only) 20% stop: **no**. Behaves like the always-on
  stop because 75-78% of stop triggers already happen in risk-off.
- Monthly-checked overlays: **no**. Protection disappears, cost remains.
- ROC lookbacks of 63+: **no**. Worse than doing nothing (max DD -49%).

## Open decisions (founder)

1. **Ship the OM25 candidate or not.** The trade is ~31% of 13-year terminal
   wealth for 12 points of drawdown. Research cannot settle this; it is a
   question about who the subscriber is.
2. **Accept single-name tail risk?** Removing the stop removes the only fast
   reaction to one stock collapsing — the rank rule tolerates a slide to
   rank 45. The sample (2009-) contains no 2008-style event, so its verdict
   that the stop "costs more than it saves" is not evidence about tails.
3. **Fix or retract `docs/portfolios.md`'s OM25 OOS row.** Client-facing.
4. **Adopt a product-grade acceptance bar?** Proposed in `RESULTS.md`; all
   four production portfolios fail it today, the candidate passes 5 of 6.

## Open work (mechanical, not yet done)

- Walk-forward the **tilt** choice (only the overlay was walk-forwarded).
- Backfill NIFTY 500 index history pre-2015 — would let the overlay be tested
  on 2008 and 2011.
- Measure real slippage from live fills; the L6 exit-buffer verdict depends
  on it.
- Model the regime dial at the **allocation** level (outside the portfolio) —
  operationally simplest, never modelled.
- A faster re-entry rule. The overlay redeploys cash only at the next
  bi-weekly rebalance, which cost most of the April-2026 bounce.

## Known limitations that apply to everything here

- Survivorship: universes are current membership back-applied. Affects levels,
  not the like-for-like comparisons.
- No tax, no brokerage anywhere. At bi-weekly turnover that is 3-6pp of CAGR.
- The overlay work is bounded by NIFTY 500 index history (2015) except where
  NIFTY 100 was used (2010).
- Corporate-action repairs still pending (`tasks/corporate_actions_fix`).
- `docs/portfolios.md` OM25 CAGR could not be reproduced — the pre-2020
  GDF-stitched panel is the prime suspect and the May-2026 panel is not on disk.

## Scripts — purpose and run order

All are standalone; run from the repo root with the venv active. Panels load
from `nse500_data_merged`. Total re-run time is roughly 15 minutes.

| # | script | produces |
|---|---|---|
| 1 | `exit_buffer_sweep.py` | L6 exit-buffer sweep -> `runs/summary.csv`, `runs/buf*_equity.csv` |
| 2 | `rolling_returns.py` | investor-experience lens on the L6 curves |
| 3 | `combo_buffer_sweep.py` | COMBO rebuilt from 2010 + buffer sweep |
| 4 | `regime_experiment.py` | regime index/mechanic arms; also builds `runs/regime_idx/` |
| 5 | `overlay_experiment.py` | overlay variants on L6 v2 and OM25 v3 |
| 6 | `om25_stop_vs_overlay.py` | OM25 stop vs overlay + calendar years |
| 7 | `om25_stop_and_tilt.py` | conditional stop x tilt-signal grid |
| 8 | `l6_simple_overlay.py` | simplest deployable overlay forms for L6 |
| 9 | `om25_walkforward.py` | **the headline** — walk-forward the overlay |
| 10 | `acceptance_audit.py` | re-scores all four vs the original pass criteria; builds TL25 |
| 11 | `investor_stats.py` | horizon / capture / recovery statistics |
| 12 | `sip_analysis.py` | SIP outcomes by duration |

Dependencies: 11 and 12 read `runs/recent_*.csv` (written by an inline step —
regenerate with `om25_stop_and_tilt.py` equivalents if missing) and
`runs/om25_wf_n100_long/walkforward_equity.csv` (script 9 with
`--index NIFTY_100 --start 2010-07-01 --first-test 2013-07-01 --tag _n100_long`).
Script 10 reads outputs of 1, 3 and 6.

`runs/` commits every summary CSV plus the spliced index inputs. Equity
curves and trade/exit ledgers are **not** committed (the repo gitignores
`*.csv`; they rebuild in minutes). **See `runs/README.md` for the exact
regeneration order** — scripts 10, 11 and 12 depend on curves that must be
rebuilt first on a fresh checkout. Every table in `RESULTS.md` is backed by a
committed summary CSV and needs no regeneration.

## Headline reproduction command

```bash
source .venv/bin/activate
python tasks/portfolio_risk_2026/om25_walkforward.py \
  --index NIFTY_100 --start 2010-07-01 --first-test 2013-07-01 --tag _n100_long
```
