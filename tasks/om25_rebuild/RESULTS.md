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

**Founder rulings 2026-09-10:** G6 raised to ≤ 10, counting everything
searched. **G8 added — a minimum return**: the founder wants 20-25%;
recorded at 20% (OOS and full span) until the founder fixes the number.

Context for G8, in-sample 2006-2015 on the price-return basis: the
benchmark did 10.9%; across 315 trials one cell reaches 20% (a fully
invested §3d cell, 20.9% / 0.86 / −69%) and none reach 25%; the overlay
cells that fix the drawdown sit at 14-16%, i.e. 3-5pp over the index with
the cash they hold in bear markets. Sharpe alone would have let a 15%
book through; the floor rules that out unless §3f's redeployment recovers
the return the overlay gives up.

## §3f — cadence and redeployment (252 trials) — IS 2006-2015

LM 250 at biweekly and weekly, N 500 at weekly, and both with the engine's
`regime_redeploy_on_increase` switch, over the ROC grid × bear exposure
∈ {50, 25, 0%}.

| Universe, cadence | Best cell | vs §3e |
|---|---|---|
| LM 250, biweekly | ROC31/c2, 50%: 14.0% / 0.72 / −40.3% | monthly best 0.69 / −54% |
| LM 250, weekly | ROC42/c2, 0%: 15.3% / 0.75 / −44.0% | |
| N 500, weekly | ROC42/c2, 0%: 15.6% / 0.80 / −36.8% | biweekly best 0.89 / −20% |

Faster cadence helps LM 250 by 0.03-0.06 and hurts N 500 (weekly 0.80 <
biweekly 0.89): more re-entries are more whipsaws. **The redeploy switch
was a no-op for every full-exit cell** — the engine only tops up positions
the book still holds, and a book at 0% has none (equity paths identical to
§3e to the last rupee; those 36 registry rows are duplicate outcomes). With
partial exposure it topped up into recoveries that reversed: drawdowns
7-9pp worse on average, Sharpe 0.04-0.17 lower. Dropped.

## §3g — re-entry on the bull flip (72 trials) — IS 2006-2015

The mechanism the founder actually asked for: a fully exited book re-enters
on the day the regime turns bull instead of waiting for the next cadence
date (an extra entry date; no engine change). ROC grid × bear ∈ {0, 25%}
on LM 250 monthly and biweekly, N 500 biweekly.

| Cell class | Mean effect of flip re-entry vs §3e | Best cell |
|---|---|---|
| LM 250 monthly, full exit | **+0.29 Sharpe, +4.1pp CAGR, +1.7pp MaxDD** | ROC42/c3: 14.0% / 0.64 / −43% |
| LM 250 biweekly, full exit | +0.07, +1.2pp | ROC42/c3: 14.9% / 0.70 / −42% |
| N 500 biweekly, full exit | +0.01, +0.4pp | ROC42/c2: 15.7% / 0.80 / −37% |
| partial exposure, any | ≈ 0 or slightly negative | |

The hypothesis was right mechanically — the monthly book's problem was the
missed re-entry, and fixing it is worth 0.3 Sharpe — and it does not close
the gap: the repaired monthly book lands at 0.64, and on N 500 biweekly the
best flip cell (0.80) is below the best cadence-only cell (0.89).

## Standing after §3 — 616 unique trials, in-sample closed

Best cell anywhere: **N 500, biweekly, CR, one regime, 25 / 20, lookback
252, return filter on, ROC15/c3 overlay, full exit in bear:
15.6% / 0.89 / −20.4%.**

| Gate | Requirement | Best achieved | |
|---|---|---|---|
| G1 | deflated IS Sharpe ≥ 0.9 | 0.89 raw; E[max under null] for 616 trials at observed sd 0.21 = 0.66; **deflated 0.24** | fails |
| G8 | CAGR ≥ 20% | 16.2% best of any overlay cell (benchmark 10.9%) | fails |
| G4 (preview, IS) | MaxDD ≥ −40% | −20% | would pass |

Nothing the brief allows passes in-sample. The Sharpe gap is not
parametric: 616 trials across score, regime, mechanics, lookback, overlay,
cadence and re-entry cover the space, and the raw maximum never crossed
0.9. The return gap is structural on this window: an overlay that survives
2008 holds cash through it, and 2006-2015 on a price-return basis gave the
index 10.9%. **OOS stays closed.** Decision for the founder — see chat.
