# Results — every run counted; in-sample only until §4

Store: `data/master/panels/pr` (price return, D-12), point-in-time
membership, NIFTY 100 from Kite for the regime. Slippage 20 bps. Fully
invested, no weight cap, no stops (brief). Harness smoke test reproduces
market_data_spine Phase 6 OM25 to 0.1pp (15.1% / 0.47 / −65.2% vs 15.2% /
0.47 / −65.1%, 2006→2026-08-21) with the old rules re-enabled.

## §3a — score × universe, one regime (6 trials) — IS 2006-2015

| Universe | UC | CR | 50/50 |
|---|---|---|---|
| LM 250 | −1.8% / −0.22 / −75.6% | **16.5% / 0.56 / −65.7%** | 7.5% / 0.09 / −73.1% |
| N 500 | −1.9% / −0.21 / −82.7% | **14.1% / 0.48 / −67.8%** | 18.3% / 0.46 / −75.8% |

Decision: **capture ratio**. Best Sharpe and shallowest drawdown on both;
the only score positive in 2011 and 2013. Upside capture alone is negative
over ten years on both universes.

## §3b — one regime vs two, ROC grid (48 trials) — IS 2006-2015

Two regimes = bull score X, bear score CR, regime = sign of the N-session
ROC of NIFTY 100 with confirm-day hysteresis, N ∈ {15, 21, 31, 42} ×
confirm ∈ {2, 3, 5}.

| Universe | One-regime CR | bull 50/50 / bear CR, best cell | cells beating one regime | bull UC / bear CR, best |
|---|---|---|---|---|
| LM 250 | 16.5% / 0.56 / −65.7% | ROC31/c3: 11.5% / 0.26 / −70.9% | **0 / 12** | −0.08 |
| N 500 | 14.1% / 0.48 / −67.8% | ROC15/c2: 19.5% / 0.56 / −75.7% | 4 / 12 | −0.12 |

The grid is flat (LM 250 Sharpe 0.15-0.26 across all cells). Decision:
**one regime, no tilt.** The prior thread's ROC-tilt result does not
survive the honest universe.

## Standing after §3a/§3b — 54 trials

Nothing passes G1 (deflated IS Sharpe ≥ 0.9): the best raw Sharpe is 0.56
and 2008 is −62% to −68% for any fully invested book. Under "just the
hysteresis" the regime cannot change exposure, so §3c/§3d cannot close
that gap. Put to the founder 2026-09-10: bring the exposure overlay into
scope, or record the gate failure.

## §3c — mechanics grid (36 trials) — IS 2006-2015, one-regime CR

top-N ∈ {15, 25, 40} × exit buffer ∈ {0, 10, 20} × cadence ∈ {biweekly,
monthly}. **Top 40 / buffer 20** is best on both universes (LM 250 Sharpe
0.66 monthly, 0.64 biweekly; N 500 0.63 / 0.62); monthly ≈ biweekly with
lower turnover. Drawdowns unchanged, −63% to −68%.

## §3d — lookback (10 trials) — IS 2006-2015, CR / one regime / 40 / 20 / monthly

lookback ∈ {126, 189, 252, 378, 504} with min_obs at 87% of it. Flat
plateau at 252-378 on LM 250 (0.66-0.67); 126 and 504 worse. 252 kept —
the plateau, not the peak.

## Standing after §3 — 100 trials

Best in-sample configuration: capture ratio, one regime, top 40, exit
buffer 20, monthly, lookback 252, fully invested. Sharpe 0.66 (LM 250) /
0.63 (N 500) raw; deflated for 100 trials, below zero. **G1 fails for
every configuration the brief allows.** The block is structural — 2008 —
not parametric; the exposure overlay is the only remaining lever.

## Constraints after §3 (founder, 2026-09-10)

Overlay back in scope; return filter as a switch; **≤ 25 positions**;
**lookback ≤ 12 months**. §3c re-picked under the cap: 25 / buffer 20,
monthly on LM 250 (0.62), biweekly on N 500 (0.48).

## §3e — exposure overlay (196 trials) — IS 2006-2015

ROC regime (N ∈ {15, 21, 31, 42} × confirm ∈ {2, 3, 5}) driving gross
exposure in bear ∈ {75, 50, 25, 0%}, entries skipped in bear (engine
default), on one-regime CR / 25 / 20, return filter on and off.

| Universe, cadence | No overlay | Best overlay cell | Cells ≥ 0.9 raw |
|---|---|---|---|
| LM 250, monthly | 17.4% / 0.62 / −67.4% | ROC42/c5, 75%: 16.2% / 0.69 / −54.3% | 0 / 48 |
| N 500, biweekly | 14.1% / 0.48 / −67.8% | **ROC15/c3, 0%: 15.6% / 0.89 / −20.4%** | 0 / 48 (0.89 is the max) |

Full exit in bear is the best setting on N 500 and the worst on LM 250:
a monthly book that exits cannot re-enter until the next monthly date and
misses the 2009-type recovery. §3f (interrupted by a full disk; reruns
from the registry) tests LM 250 at biweekly and weekly, and both
universes with immediate redeployment when exposure rises.

Return filter: on for LM 250 (0.62 vs 0.54), immaterial on N 500. Kept on.

Deflation corrected to the published form (observed cross-trial variance
of IS Sharpe) before any gate is judged; the earlier fixed-variance form
overstated the expected maximum for ~300 near-identical cells.

**Open with the founder:** how G6 (≤ 8 parameters) counts with the overlay
— everything searched (10), tuned values only (8), or a raised cap.
