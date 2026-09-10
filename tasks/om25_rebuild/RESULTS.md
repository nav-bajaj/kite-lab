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

## Gate change (founder, 2026-09-10)

G1 relaxed from 0.9 deflated to **0.8 raw**, deflated value reported
alongside. Recorded in TASKS.md §0.

## §3h — the same book started 2010-01-01 (122 trials) — window 2010-2015

No crash, no recovery; the index did 7.8% over the window (15.5% over
2006-2009). Fresh runs starting 2010 (not a window cut from the 2006
path; the two agree to 0.6pp, so path dependence is nil). LM 250 monthly
and N 500 biweekly: no overlay, the §3e overlay grid (48 cells each), and
flip re-entry on the full-exit cells (12 each).

| Universe, cadence | No overlay | Best overlay cell | Overlay cells beating no overlay |
|---|---|---|---|
| LM 250, monthly | **23.7% / 1.50 / −17.0%** | ROC21/c3, 75%: 18.7% / 1.45 / −12.8% | 0 / 48 |
| N 500, biweekly | **22.7% / 1.35 / −15.5%** | ROC42/c2, 75%: 18.2% / 1.28 / −11.6% | 0 / 48 |

The §3e winner (ROC15/c3, full exit) does 7.3% / 0.39 on LM 250 and
12.8% / 0.94 on N 500 over this window. Mean overlay cost by bear
exposure on LM 250: 75% → −5pp CAGR, 50% → −10pp, full exit → −15pp.
Flip re-entry does not rescue the full-exit cells (best 1.01).

Read: **the overlay's entire value is 2008.** In every other regime,
including 2011 (index −25%; the fully invested book's worst drawdown here
is −17%), it costs return and Sharpe. The fully invested book beats the
index by 15-16pp a year on the muted window and clears both G1 at 0.8
and G8 at 20% with room (the only two cells of 122 that clear both are
the two no-overlay books). Deflation for this window: 122 trials, observed
sd 0.30, E[max] 0.77, best raw 1.50 → deflated
0.72; the relaxed gate is raw, so this is reported,
not judged.

**Decision for the founder, recorded when made:** the in-sample window
was pre-committed as 2006-2015 and the book fails it; moving the window
to 2010-2015 after seeing this is a choice to judge the book fully
invested and accept a 2008-type drawdown as out of scope of the gates.
That is defensible (the overlay is a separate risk policy, not part of
the alpha) but it must be written down as such. 738 unique trials
to date. OOS still closed.

## Decisions after §3h (founder, 2026-09-10)

In-sample window moved to **2010-01-01 → 2015-12-31**; the book is judged
fully invested and 2008 is out of the gated window. An overlay is still
required against a 2008-type event, but the ROC price-regime overlay is
not it. The founder's proposal — an indicator of the strength of momentum
across the index's stocks, cutting exposure when it weakens — is explored
as §3j.

## §3i — cadence grid from 2010 (10 trials) — window 2010-2015, fully invested

Entry cadence × exit cadence ("same" = rank exits at the entry dates,
"weekly" = rank exits every Friday via the engine's weekly rank check,
which no earlier run used).

| Universe | Entry / exit | CAGR | Sharpe | MaxDD | Trades |
|---|---|---|---|---|---|
| Nifty 250 | weekly / same | 23.6% | 1.49 | −17.4% | 2012 |
| Nifty 250 | biweekly / same | 23.7% | 1.51 | −18.4% | 1712 |
| Nifty 250 | biweekly / weekly | 23.2% | 1.51 | −17.7% | 1920 |
| Nifty 250 | **monthly / same** | **23.7%** | **1.50** | **−17.0%** | **1434** |
| Nifty 250 | monthly / weekly (extra) | 20.9% | 1.37 | −17.2% | 1807 |
| NSE 500 | weekly / same | 22.9% | 1.35 | −16.9% | 2901 |
| NSE 500 | biweekly / same | 22.7% | 1.35 | −15.5% | 2503 |
| NSE 500 | biweekly / weekly | 21.7% | 1.31 | −16.6% | 2746 |
| NSE 500 | **monthly / same** | **23.6%** | **1.44** | **−15.2%** | **2090** |
| NSE 500 | monthly / weekly (extra) | 18.5% | 1.13 | −16.2% | 2553 |

Entry cadence is a non-lever: weekly, biweekly and monthly are within
0.02 Sharpe on Nifty 250, and monthly is best on NSE 500 by 0.09. Weekly
exits on a slower entry schedule are strictly worse — 1 to 5pp of CAGR
and 0.04 to 0.31 of Sharpe, with more trades — because a rank-out on a
Friday leaves cash idle until the next entry date. Decision: **monthly
entry and exit on both universes**, the fewest trades of any cell (G7).

## §3k — lookback re-check on the 2010 window (10 trials) — monthly, fully invested

Founder asked for 6 months; 3 months added for shape. min_obs at 87%.

| Lookback | Nifty 250 | NSE 500 |
|---|---|---|
| 63 (3m) | 12.6% / 0.52 / −31.5% | 24.6% / 1.23 / −24.7% |
| 126 (6m) | 19.3% / 1.06 / −26.7% | 27.9% / 1.53 / −21.0% |
| 189 (9m) | 22.0% / 1.35 / −20.8% | 27.2% / 1.56 / −18.5% |
| **252 (12m)** | **23.7% / 1.50 / −17.0%** | 23.6% / 1.44 / −15.2% |
| 378 (18m, over cap) | 24.1% / 1.52 / −16.9% | 25.6% / 1.65 / −16.7% |

Nifty 250 is monotone in lookback: 6 months costs 4pp of CAGR, 0.44 of
Sharpe and 10pp of drawdown; 252 is the right choice under the 12-month
cap. NSE 500 has no plateau on this six-year window (Sharpe 1.44-1.65
across 6-18 months, 252 the lowest) — the ordering flips between windows
(§3d on 2006-2015 had 252-378 flat and 126 worse). Choosing a shorter
lookback for NSE 500 alone on this evidence would be fitting a six-year
window; 252 is kept on both, pre-chosen on the longer window, and the
NSE 500 sensitivity is recorded as a caveat for the OOS read.

## §3j — momentum-strength overlay (agent, 332 trials) — windows 2006-2009 and 2010-2015

The founder's question: can an indicator of the strength of momentum across
the index's stocks cut the 2008 drawdown at little cost on 2010-2015, where
the ROC price regime could not (§3h)? Acceptance, fixed in
`lib/BRIEF_3j.md` before any run: cost within ~2pp CAGR and ~0.10 Sharpe of
the fully invested book on each universe over 2010-01-01 → 2015-12-31, and
MaxDD no worse than about −40% on a fresh run 2006-02-01 → 2009-12-31
without giving up the 2009 recovery. Both windows are before OOS; `end` was
passed on every run so nothing after 2015-12-31 was simulated.

Harness: `regime_kind="strength"` in `lib/run.py` (keys `str_kind`,
`str_len`, `str_thresh`, `str_mode`; confirm days reuse `confirm`; the new
keys are left out of the id at their defaults, so all 749 stored configs
keep their ids — verified). Indicators in `lib/regime.py`, built from the
harness close panel and a point-in-time membership mask, weak state =
indicator below threshold, `_confirm` hysteresis, lagged one session.
Threshold `abs` = a level; `pct` = the indicator's own expanding-window
quantile (min 252 obs, data ≤ t). A truncation test (panel cut at
2008-06-30 vs cut at 2015-12-31) reproduces every indicator and regime
series exactly, so the panel-level lookahead traps are ruled out.

Indicators (length L): **breadth** = fraction of members with a positive
L-day return; **breadth_ma** = fraction above their L-day MA; **disp** =
interquartile range of L-day returns; **factor** = trailing L-day return of
the top-minus-bottom decile spread ranked by 12-1 momentum; **leaders** =
top decile minus the equal-weight universe; **persist** = rank correlation
of 12-1 momentum at t vs t−L; **capture** = 90th percentile of the
harness's own capture ratio across members over L days (the book's entry
boundary on Nifty 250); `_d` variants = the L-day change of the 252-day
base. 172 engine-free threshold screens (`runs/3j_diag.csv`: weak-day share
in the crash and in 2010-2015) picked 35 settings; each ran at 50% and 0%
exposure in the weak state on Nifty 250 monthly and NSE 500 biweekly, both
windows (140 cells), then 20 refinement cells around the survivors and 4
cross-cadence cells. 166 cells, 332 runs, every run registered as 3j (the
2006-2009 companion runs carry blank IS stats: they have no 2010-2015
path). Fully invested: Nifty 250 monthly 23.7% / 1.50 / −17.0% on
2010-2015 and 7.5% / 0.09 / −67.4% on 2006-2009; NSE 500 biweekly
22.7% / 1.35 / −15.5% and 0.5% / −0.18 / −67.8%.

Best cell per indicator (full exit in the weak state unless noted; "cost"
= 2010-2015, "pre" = 2006-02-01 → 2009-12-31; weak = share of days cut):

| Universe | Indicator, setting | cost | pre | weak cost / pre | bands |
|---|---|---|---|---|---|
| LM 250 m | breadth_ma 200 < 0.30, c3 | 22.2% / 1.57 / −11.8% | 16.7% / 0.54 / −34.8% | 15% / 28% | **both** |
| LM 250 m | same, re-entry on the flip | 22.6% / 1.60 / −12.5% | 18.7% / 0.63 / −35.4% | 15% / 28% | **both** |
| LM 250 m | breadth_ma 200 < exp. 10th pct | 23.7% / 1.50 / −17.0% | 21.8% / 0.74 / −38.7% | 0% / 19% | both, never fires 2010-15 |
| LM 250 m | breadth 126 < exp. 10th pct | 22.7% / 1.43 / −17.0% | 19.1% / 0.61 / −40.9% | 0.4% / 23% | cost only (−40.9) |
| LM 250 m | capture 252 < 1.4 | 23.7% / 1.50 / −17.0% | 8.3% / 0.18 / −33.8% | 0% / 54% | both, recovery lost |
| LM 250 m | disp 252 < exp. 20th pct | 16.2% / 1.02 / −15.7% | 14.5% / 0.43 / −41.8% | 23% / 34% | neither |
| LM 250 m | factor 63 < 0 | 12.8% / 0.70 / −17.8% | 7.9% / 0.17 / −30.1% | 23% / 46% | protection only |
| LM 250 m | leaders 63 < 0 | 8.6% / 0.34 / −19.2% | 12.4% / 0.44 / −30.3% | 23% / 50% | protection only |
| LM 250 m | persist 63 < exp. 20th pct | 14.6% / 0.86 / −16.5% | 9.7% / 0.22 / −40.8% | 15% / 22% | neither |
| LM 250 m | breadth_d 21 < exp. 10th pct | 21.9% / 1.46 / −17.8% | 13.1% / 0.34 / −49.8% | 7% / 9% | cost only |
| N 500 bw | breadth_ma 200 < exp. 10th pct | 22.7% / 1.35 / −15.5% | 21.1% / 0.77 / −34.3% | 0% / 23% | both, never fires 2010-15 |
| N 500 bw | breadth_ma 200 < 0.30, c3 | 16.3% / 0.97 / −14.0% | 18.2% / 0.67 / −32.8% | 18% / 32% | protection only (−6.4pp) |
| N 500 bw | breadth_ma 100 < 0.30 | 18.3% / 1.18 / −16.8% | 25.3% / 1.12 / −24.5% | 22% / 35% | protection only (−4.4pp) |
| N 500 bw | breadth 126 < exp. 10th pct | 21.9% / 1.30 / −15.5% | 15.7% / 0.51 / −42.1% | 1% / 27% | cost only |
| N 500 bw | capture 252 < exp. 10th pct | 22.7% / 1.35 / −15.5% | 14.5% / 0.48 / −33.2% | 0% / 37% | both, never fires 2010-15 |
| N 500 bw | disp 252 < exp. 20th pct | 17.0% / 0.99 / −15.5% | 17.8% / 0.63 / −40.4% | 17% / 36% | neither |
| N 500 bw | factor 63 < 0 | 8.9% / 0.33 / −15.4% | 10.6% / 0.31 / −45.2% | 21% / 40% | neither |
| N 500 bw | leaders 42 < −0.02 | 16.3% / 0.98 / −15.7% | 13.4% / 0.54 / −30.8% | 16% / 35% | protection only |
| N 500 bw | persist 63 < exp. 30th pct | 16.7% / 0.96 / −15.9% | 8.7% / 0.18 / −35.4% | 17% / 26% | protection only |
| N 500 bw | breadth_d 63 < −0.10 | 16.5% / 1.11 / −14.2% | 11.9% / 0.34 / −34.6% | 32% / 37% | protection only |

Fourteen of 166 cells meet both bands; all are breadth-above-MA or the
capture ratio. Three things about them:

1. **The only family that does the job is breadth above the 200-DMA.** The
   accepted cell (< 0.30, confirm 3, full exit) on Nifty 250 monthly exits
   2008-03-12 → 04-25, 05-14 → 05-20 and 05-28 → 2009-04-17, i.e. it
   misses the first −25% of January 2008, holds cash through the rest, and
   is back five weeks after the March 2009 low. On 2010-2015 it cuts in
   2011 (Feb–Apr, May–Jun, Aug–Nov, Nov–Jan 2012) and mid-2013 (Jun–Sep);
   the fully invested book's worst drawdown there was −17%, so those cuts
   cost 1.5pp of CAGR and buy 5pp of MaxDD. Confirm 2 and 5 are within
   0.1pp; flip re-entry (§3g) adds 0.4pp on the cost window and 2pp on the
   recovery. 25% or 50% exposure instead of 0% is worse on both windows
   (pre MaxDD −37.5% / −43.1%).
2. **Acceptance is one threshold notch wide and universe-dependent.** On
   Nifty 250: 0.25 gives −46.8% in the pre window (fails protection), 0.35
   costs 3.6pp (fails cost). On NSE 500 biweekly the same 0.30 cell costs
   6.4pp (16.3% / 0.97); 0.25, 0.35, 0.40, confirm 2/5, 25%/50% exposure and
   flip re-entry all cost 4.4-6.9pp. The cross-cadence cells put it on the
   universe, not the cadence: NSE 500 monthly costs 6.9pp (16.7% / 1.04 vs
   23.6% / 1.44), Nifty 250 biweekly 3.2pp (20.5% / 1.44 vs 23.7% / 1.51).
   The NSE 500 book loses more when it steps out in 2011 and 2013 with the
   same weak-day share (18% vs 15%).
3. **The cells that pass on both universes never fire after 2008.** The
   expanding 10th percentile (breadth_ma 200, capture 252) and capture
   < 1.4 read weak on 0.0% of 2010-2015 days: once 2008 is in the history
   the bar is "as bad as 2008", so the zero cost is by construction, and
   the 2008 detection is a first-event effect (in early 2008 the history
   was 2006-2007 only). One notch up, the 15th percentile, costs 3.1pp on
   Nifty 250 (20.5% / 1.31) and 2.3pp on NSE 500 (20.3% / 1.21). The
   capture < 1.4 cells also give up the 2009 recovery (pre CAGR 8.3% /
   5.6%, weak 54% / 46% of pre-window days); capture < 1.3 gives −51.4% /
   −45.6%.

**Verdict: acceptance is met by the letter and not robustly.** A
200-DMA-breadth overlay at 0.30 with full exit passes both bands on Nifty
250 monthly and fails the cost band on NSE 500 at every setting tried; the
only cells that pass on both universes are thresholds that 2010-2015 never
reaches. Nothing here is a calibrated "momentum is weakening" reading: the
factor's own return, the leaders' relative return, rank persistence,
dispersion and the capture-ratio level or slope all cost 4-15pp of CAGR on
2010-2015 wherever they protect 2008, because each of them also reads weak
for 15-25% of 2010-2015 (2011 and 2013 look like momentum failing on every
one of them, and the fully invested book came through both at −17%). The
protection in 2008 comes from breadth collapsing, which is a price regime
on the constituents rather than on the index — a cousin of §3e's ROC
overlay with a better 2008 entry (breadth crossed 0.30 in March 2008; the
ROC cells' whipsaws were the cost in §3h).

Deflation for this phase: 332 trials, observed sd of the 2010-2015 Sharpe
0.288, E[max] 0.84, best raw 1.65 (breadth_ma 100 < exp. 20th pct at 50%,
Nifty 250: 21.8% / 1.60), deflated 0.81. Registry: 1090 unique ids.

Parameter count if adopted: length 200, threshold 0.30, confirm 3 on top of
the base book's 7 = 10 = G6, before counting the exposure level (0%) and
the threshold mode as switches.

What did not work: every indicator except 200-DMA breadth; partial
exposure (worse than full exit in every accepted family); shorter breadth
windows (63/126-day return breadth protects to −41% to −47% at best); the
slope variants (weak 7-32% of the cost window for −35% to −50%
protection); any absolute breadth threshold on NSE 500.

Caveats: the choice of the 35 grid settings used the crash window's
weak-day share (disclosed above; the trials count covers the grid, not the
172 screens); the expanding-percentile thresholds had 1.3-2.3 years of
history when 2008 began; the membership file's own reconstruction and the
price-return basis (D-12) are shared with every section. Files:
`lib/phase3j*.py`, `runs/3j_summary.csv` (one row per cell, both windows,
run ids), `runs/3j_diag.csv`, `runs/3j.log`.

## §4 — OOS, opened once (2026-09-10) — 2016-01-01 → 2026-09-09

Five candidates fixed before any 2016+ statistic was computed (TASKS.md
§4). Each is one run from 2010-01-01 to 2026-09-09; IS is the 2010-2015
window of the same path. Walk-forward refits lookback only, from
{63, 126, 189, 252}, on the trailing ten years, chained yearly. Turnover
is gross notional traded over mean equity, per year, and trades per year.

| Candidate | IS 2010-15 | **OOS 2016-26** | Sub-windows 16-19 / 20-22 / 23-26 | Walk-fwd Sharpe | CAGR 2010-26 | Turnover | Gates |
|---|---|---|---|---|---|---|---|
| A N250 monthly lb252 | 23.7% / 1.50 / -17.0% | 18.3% / 0.79 / -34.6% | 0.92 / 1.03 / 0.49 | 0.68 | 20.2% | 3.3x, 90/yr | G2 fail, G3 fail, G4 pass, G5 pass, G8 fail |
| B N250 biweekly lb252 | 23.7% / 1.51 / -18.4% | 17.5% / 0.75 / -34.4% | 0.88 / 1.04 / 0.41 | 0.71 | 19.7% | 3.9x, 106/yr | G2 fail, G3 fail, G4 pass, G5 pass, G8 fail |
| C N500 monthly lb126 | 27.9% / 1.53 / -21.0% | 17.0% / 0.68 / -35.6% | 0.51 / 1.17 / 0.40 | 0.65 | 20.9% | 9.4x, 246/yr | G2 fail, G3 fail, G4 pass, G5 pass, G8 fail |
| D N500 biweekly lb126 | 25.5% / 1.36 / -24.7% | 18.5% / 0.75 / -36.5% | 0.33 / 1.29 / 0.67 | 0.76 | 21.0% | 12.8x, 335/yr | G2 fail, G3 fail, G4 pass, G5 pass, G8 fail |
| E N250 monthly lb252 + breadth | 22.6% / 1.60 / -12.5% | 14.1% / 0.65 / -24.7% | 0.96 / 0.53 / 0.49 | 0.60 | 17.1% | 4.6x, 127/yr | G2 fail, G3 fail, G4 pass, G5 pass, G8 fail |

Benchmark (NIFTY 100, price return): OOS 10.9% / 0.37 / −38%; sub-windows
0.45 / 0.41 / 0.26; 2010-26 9.8%. The production OM25 rules reproduced on
this same store (50/50 score, two regimes, 20% trailing stop, biweekly):
OOS 18.6% / 0.68 / −40%; sub-windows 0.23 / 0.88 / 0.92.

Walk-forward lookback picks by year (2016 → 2026): A [252, 126, 252, 252, 252, 252, 252, 252, 252, 252, 252], C
[126, 126, 189, 189, 126, 126, 126, 126, 126, 126, 252]. The refit never chose below 126 for Nifty 250 and drifted
between 126 and 252 for NSE 500; G5 passes everywhere, i.e. the static
lookback is not the fragile part.

**Every candidate fails G2 (OOS Sharpe ≥ 0.9), G3 (each sub-window ≥ 0.6)
and G8 (OOS CAGR ≥ 20%); every candidate passes G4 and G5.** The decay
from in-sample is 0.6-0.9 of Sharpe on every book. Two things drive it:
2020 (−35% drawdown for the fully invested books, inside G4 but
Sharpe-costly) and 2023-2026, where the rebuild does 0.4-0.5 against the
production rules' 0.92 — the capture-ratio book, tuned on 2010-2015, has
been the wrong score for the last three years while the old 50/50 tilt
with a trailing stop has been the right one.

The breadth overlay (E) did what it was built to do in 2020 (−24.7% vs
−34.6%) and then missed the recovery: 2020-22 Sharpe 0.53 against 1.03
fully invested, 4pp of OOS CAGR gone. The same failure the ROC overlay
showed in 2009, on a different indicator.

The NSE 500 books with the 6-month lookback turn over 9-13x a year
(250-330 trades), three times the Nifty 250 books, for the same OOS
Sharpe — flagged under G7.

Deflation is not applied to OOS (one look). 1090 unique in-sample trials preceded it.

## §4b — full walk-forward (144 runs) — chained 2016-01-01 → 2026-09-09

**Labelled: designed after OOS was opened in §4.** The question from the
founder: parameters tuned on 2010-2015 and held for fifteen years are not
how the book would be run, so evaluate the re-tuning process instead.
Refit set per book: score {CR, 50/50, UC} × regimes {1, 2} × exit buffer
{0, 10, 20} × trailing stop {off, 20%} = 36 configurations, each run
2006-02-01 → today; lookback fixed (12m Nifty 250, 6m NSE 500; its own
walk-forward held in §4). Each January the configuration with the best
Sharpe on the trailing 5 or 10 years is traded for the year. Eight
process variants (4 books × 2 windows) were looked at; no gate was
pre-committed for the adaptive process, so the §4 gates are reported
against, not judged.

| Book | Refit window | Chained OOS | Sub-windows 16-19 / 20-22 / 23-26 | Config changes in 11 yrs | Picks 2024-26 (score/regimes/buffer/stop) |
|---|---|---|---|---|---|
| A N250 monthly | 5y | 21.6% / 0.90 / -34.6% | 0.88 / 0.99 / 0.91 | 6 | 5050/1/10/0.2, 5050/1/0/0.2 |
| A N250 monthly | 10y | 17.5% / 0.78 / -34.6% | 0.80 / 0.99 / 0.60 | 2 | cr/1/20/0.2 |
| B N250 biweekly | 5y | 19.1% / 0.75 / -32.9% | 0.83 / 0.88 / 0.66 | 4 | 5050/1/0/0.2 |
| B N250 biweekly | 10y | 17.1% / 0.74 / -34.5% | 0.78 / 1.01 / 0.48 | 2 | cr/1/20/0.0, cr/1/20/0.2 |
| C N500 monthly | 5y | 16.5% / 0.55 / -35.6% | 0.34 / 0.95 / 0.40 | 5 | 5050/2/20/0.0, 5050/2/10/0.0, 5050/2/10/0.2 |
| C N500 monthly | 10y | 16.2% / 0.64 / -35.6% | 0.42 / 1.12 / 0.39 | 3 | cr/1/20/0.0, 5050/2/20/0.0 |
| D N500 biweekly | 5y | 16.2% / 0.57 / -39.9% | 0.32 / 1.26 / 0.25 | 4 | 5050/1/20/0.0, cr/1/20/0.0, uc/1/0/0.2 |
| D N500 biweekly | 10y | 17.8% / 0.72 / -36.5% | 0.26 / 1.26 / 0.66 | 2 | cr/1/20/0.0 |

References on Nifty 250 monthly, same window: the §4 static book 18.3% /
0.79 / −34.6%; the single best configuration chosen with hindsight on the
whole OOS (CR, 1, 20, stop 20%) 18.5% / 0.89 / −26.7%. The production
rules on this store: 18.6% / 0.68 / −40%.

**Nifty 250 monthly with a five-year refit is the one process that meets
every OOS gate as written: 21.6% / 0.90 / −34.6%, every sub-window above
0.6, walk-forward by construction.** 0.90 is at the gate, not above it;
the standard error of a ten-year Sharpe is about 0.35. It beats the
hindsight-best static configuration because it switched: a trailing
stop from 2021, then the 50/50 score from 2024 — i.e. it converged on the
production rules' choices for the recent regime, from data it had at the
time. The ten-year refit is too slow to make either switch and matches
the static book. Six configuration changes in eleven years is one every
two years, not noise-chasing; the changes are all in stop and score, the
buffer stays at 20.

The NSE 500 books do not benefit: 0.55-0.72 chained, 2016-2019 stays at
0.26-0.42 for every variant (the 6-month lookback is the likely cause;
it was the founder's choice and was not in the refit set), and the
five-year window on NSE 500 biweekly ends on an upside-capture pick with
no buffer, which is the noise-chasing pattern.

Caveats to carry: the refit grid and the two windows were chosen now,
with 2016-2026 known; one of eight variants clears the gates; the result
is one look at a process, not a pre-registered test. It answers the
founder's question — a periodically re-tuned Nifty 250 book would have
held 0.9 through 2016-2026 — and it is the number to pre-commit against
for the next window, not a number that was pre-committed.

## Reference — against Wright Momentum's published grid (Oct-2020 → Aug-2026, 71 months)

Their monthly grid (`~/Downloads/momentum_wright.pdf`, returns exclude
costs); ours net of 20 bps slippage, monthly from daily equity. The
adaptive book is the §4b Nifty 250 monthly five-year-refit chain.

| | CAGR | Monthly MaxDD | 2026 YTD | 1Y | 2Y | 3Y | Vol |
|---|---|---|---|---|---|---|---|
| Wright Momentum | 31.2% | −21.7% | 8.9% | 14.2% | 3.0% | 18.4% | 20.0% |
| Adaptive Nifty 250 monthly | 26.3% | −26.4% | 16.0% | 18.0% | 4.7% | 25.4% | 20.5% |
| Production rules, honest store | 29.7% | −25.9% | 7.3% | 5.9% | 0.2% | 26.7% | 22.3% |
| Static rebuild book | 19.6% | −25.5% | 3.7% | 3.6% | −4.7% | 12.7% | 19.6% |
| NIFTY 100 | 14.4% | −16.4% | −5.4% | 0.9% | −2.0% | 9.5% | 14.5% |

Calendar years: Wright leads 2021 (91% vs 58%) and 2023 (49% vs 31%); the
adaptive book leads 2024 (48% vs 34%) and 2026 to date (16% vs 9%); 2022
and 2025 flat for both. Monthly correlation 0.78. The 2021 gap is where
the CAGR difference lives; the trailing three years favour the adaptive
book.

## §4c — the Nifty 250 monthly process on the NSE 500 universe (Wright's window)

Same rules (monthly, lookback 252, 25 / 20, five-year yearly refit over
the 36-config grid), universe swapped to NSE 500. Wright uses a 500-stock
universe. Oct-2020 → Aug-2026, ours net of 20 bps.

| | CAGR | Monthly MaxDD | 2026 YTD | 1Y | 2Y | 3Y | Corr w/ Wright |
|---|---|---|---|---|---|---|---|
| Wright Momentum (ex-costs) | 31.2% | −21.7% | 8.9% | 14.2% | 3.0% | 18.4% | — |
| Adaptive on NSE 500, own refit | 20.6% | −22.0% | 7.0% | 11.2% | −0.2% | 13.3% | 0.82 |
| Nifty 250's picks applied to NSE 500 | 26.3% | −30.2% | 23.4% | 22.3% | 5.6% | 18.7% | 0.85 |
| Adaptive on Nifty 250 (§4b) | 26.3% | −26.4% | 16.0% | 18.0% | 4.7% | 25.4% | 0.78 |

On NSE 500 the five-year refit never leaves capture ratio (it picks
CR / 1 / 20 / stop from 2022 on) and lands at 20.6%, 6pp below the Nifty
250 process and 10pp below Wright; full OOS 2016-26 17.7% / 0.73 / −37%.
The Nifty 250 picks (50/50 with stop from 2024) applied to NSE 500 match
the Nifty 250 CAGR and win 2026 outright (23% vs 9%) at a deeper
drawdown. The universe is not what separates the book from Wright: the
gap is 2021 (56-78% vs 91%) on either universe, and their bear-regime
model and volatility screen are the likelier source.

## §4d — the Nifty 250-fitted process over the long run, and what is working in 2024-2026

Chained from 2011 (each year's configuration chosen on the trailing five
years, so 2011-2015 is also forward for the process; the grid and the
window were chosen in §4b with 2016-2026 known).

| Process | 2011-26 | 2011-15 | 2016-26 | 2016-19 | 2020-22 | 2023-26 |
|---|---|---|---|---|---|---|
| Nifty 250 fitted, traded on Nifty 250 | **21.4% / 0.97 / −35%** | 21.0 / 1.28 | 21.6 / 0.90 | 16.2 / 0.88 | 25.8 / 0.99 | 24.3 / 0.91 |
| Nifty 250 fitted, traded on NSE 500 | 20.3% / 0.86 / −37% | 19.3 / 1.13 | 21.0 / 0.81 | 12.6 / 0.50 | 33.8 / 1.34 | 20.6 / 0.69 |
| NSE 500 fitted, traded on NSE 500 | 17.2% / 0.72 / −37% | 16.4 / 0.72 | 17.7 / 0.73 | 12.2 / 0.46 | 27.9 / 1.06 | 15.9 / 0.72 |
| NIFTY 100 | 9.4% / 0.27 / −38% | 6.0 / 0.06 | 10.9 / 0.37 | 10.9 / 0.45 | 14.2 / 0.41 | 8.3 / 0.26 |

The Nifty 250-fitted process transfers to NSE 500 (0.86 over fifteen
years) and beats fitting on NSE 500 itself (0.72) — the NSE 500 refit
never finds the score switch. Nifty 250 remains the better home for the
book on every window except 2020-2022, where the broader universe's
small-cap rally paid.

**Attribution of 2024-2026 on Nifty 250 monthly** (fixed configurations,
CAGR / Sharpe / MaxDD; index 4.4% / −0.04):

| Configuration | 2024-26 | 2016-23 |
|---|---|---|
| Capture ratio, buffer 20, no stop (static book) | 8.3% / 0.20 / −27% | 21.8% / 1.00 / −35% |
| + 20% trailing stop | 8.6% / 0.22 / −26% | 22.1% / 1.14 / −27% |
| 50/50 score, buffer 20, stop | 22.3% / 0.74 / −25% | 19.7% / 0.74 / −40% |
| 50/50, buffer 10, stop (the picks) | 22.6% / 0.74 / −26% | 21.9% / 0.85 / −36% |
| Upside capture only, buffer 10, stop | 22.5% / 0.67 / −33% | 14.7% / 0.42 / −55% |

The whole of the recent edge is the score: everything with upside
capture in it does 22% in 2024-26, everything on capture ratio alone
does 8%; the stop and the buffer add nothing in this window. The
reverse held in 2016-2023 (capture ratio 1.00, 50/50 0.74). The static
capture-ratio book's rolling three-year excess over the index is 3.9pp
today, the 20th percentile of its history (median 9.8pp): capture ratio
is in a weak patch and upside capture is carrying the book. Production
OM25 v3 has run 50/50 in its bull state since inception, which is why
its rules read 0.92 for 2023-26.

## §4e — year by year, SIP, and a flat 25% tax (Nifty 250 adaptive process, chained from 2011)

Benchmarks are price indices. Nifty 250 = NIFTY LARGEMIDCAP 250 from
2020-01-02 (real index, `~/Documents/stock_data/indices_data`), spliced
onto a 50/50 NIFTY 100 + NIFTY MIDCAP 150 proxy rebalanced quarterly
before that (the index methodology; correlation 0.98 with the real
index since 2020, CAGR within 0.5pp). 2026 = YTD to 2026-09-09.

| Year | Portfolio | Nifty 250 | Nifty 500 |
|---|---|---|---|
| 2011 | −13.5% | −29.2% | −27.4% |
| 2012 | 45.1% | 37.4% | 31.8% |
| 2013 | 11.2% | 1.8% | 3.6% |
| 2014 | 68.0% | 46.6% | 37.8% |
| 2015 | 10.4% | 2.9% | −0.7% |
| 2016 | 7.3% | 4.6% | 3.8% |
| 2017 | 54.9% | 42.4% | 35.9% |
| 2018 | 0.7% | −6.2% | −3.4% |
| 2019 | 8.1% | 5.0% | 7.7% |
| 2020 | 28.2% | 19.7% | 16.7% |
| 2021 | 57.5% | 35.7% | 30.2% |
| 2022 | −1.5% | 3.4% | 3.0% |
| 2023 | 30.7% | 31.6% | 25.8% |
| 2024 | 47.9% | 17.7% | 15.2% |
| 2025 | 0.4% | 7.3% | 6.7% |
| 2026 YTD | 15.1% | 0.1% | −3.8% |

Beats Nifty 250 in 13 of 16 years, Nifty 500 in 14; the losses are 2022,
2023 (by 1pp) and 2025 — flat or grinding years. Never worse than −13.5%
in a calendar year against −29% for the indices in 2011.

Tax: flat 25% on each financial year's positive gain at March 31, no
loss carry-forward, for the portfolio (its turnover realises gains every
year). For the indices the fair comparison is buy-and-hold taxed once at
exit; the FY-taxed index is shown for symmetry.

| CAGR | Portfolio | Nifty 250 | Nifty 500 |
|---|---|---|---|
| 2011-26 pre-tax | 21.4% | 12.2% | 10.3% |
| 2011-26 post-tax | **16.1%** (FY) | 10.6% (exit) / 8.8% (FY) | 8.7% (exit) / 7.1% (FY) |
| 2016-26 pre-tax | 21.6% | 14.2% | 12.3% |
| 2016-26 post-tax | **16.5%** (FY) | 12.0% (exit) / 10.4% (FY) | 10.3% (exit) / 8.8% (FY) |

The yearly tax costs the portfolio 5.1-5.3pp of CAGR; the index
buy-and-hold loses 1.6-2.2pp to tax at exit. Post-tax the portfolio's
lead over Nifty 250 narrows from 9.2pp to 5.5pp (2011-26).

SIP of Rs 10,000 on the first trading day of each month:

| SIP | Invested | Portfolio | Nifty 250 | Nifty 500 |
|---|---|---|---|---|
| from 2011, pre-tax | 18.9L | 140.6L (7.4x), XIRR 22.7% | 65.5L (3.5x), 14.5% | 53.2L (2.8x), 12.2% |
| from 2011, post-tax | 18.9L | 85.6L (4.5x), 17.4% | 53.8L (2.8x), 12.3% | 44.6L (2.4x), 10.2% |
| from 2016, pre-tax | 12.9L | 46.1L (3.6x), 22.4% | 29.2L (2.3x), 14.6% | 25.4L (2.0x), 12.2% |
| from 2016, post-tax | 12.9L | 34.7L (2.7x), 17.6% | 25.1L (1.9x), 12.0% | 22.3L (1.7x), 9.9% |

Portfolio SIP taxed 25% on each FY's gain of the accumulated pot; index
SIP taxed 25% on the gain at exit. Post-tax, the portfolio SIP ends at
1.6x the Nifty 250 SIP from 2011 and 1.4x from 2016.

## §4f — against a synthetic NIFTY MIDSMALLCAP 400

The real index (Kite history) runs 2019-01-14 → 2026-05-08. Synthetic
elsewhere: Midcap 150 (real, master store) and a small-cap leg, blended
64/36 (the midcap weight fitted on the real index's 2019-26 daily
returns), rebalanced quarterly. Small-cap leg after 2026-05: the real
Smallcap 250. Before 2019: the point-in-time equal-weight basket of NSE
500 members not in Nifty 250 from the master panel — the Smallcap 250's
own definition — which tracks the real Smallcap 250 at 0.986 daily
correlation over 2019-26, 1.6pp a year under it (equal weight versus cap
weight). The full early construction tracks the real MidSmall 400 at
0.984 daily correlation with 3.4% tracking error and matching CAGR (17.8% vs 17.9%). Series in `runs/midsmall400_synthetic.csv`.

| Window | Portfolio | MidSmall 400 |
|---|---|---|
| 2011-26 | 21.4% / 0.97 / -35% | 13.0% / 0.45 / -51% |
| 2016-26 | 21.6% / 0.90 / -35% | 14.9% / 0.55 / -51% |
| 2019-26 (real index) | 23.1% / 0.90 / -35% | 17.9% / 0.70 / -40% |
| Wright window Oct-20 → Aug-26 | 26.2% / 1.07 / -27% | 23.4% / 1.09 / -23% |

| Year | Portfolio | MidSmall 400 | Excess |
|---|---|---|---|
| 2011 | -13.5% | -34.5% | +20.9pp |
| 2012 | 45.1% | 41.3% | +3.8pp |
| 2013 | 11.2% | -6.1% | +17.3pp |
| 2014 | 68.0% | 62.5% | +5.5pp |
| 2015 | 10.4% | 8.8% | +1.6pp |
| 2016 | 7.3% | 2.8% | +4.6pp |
| 2017 | 54.9% | 53.8% | +1.1pp |
| 2018 | 0.7% | -19.9% | +20.5pp |
| 2019 | 8.1% | -3.1% | +11.2pp |
| 2020 | 28.2% | 24.6% | +3.6pp |
| 2021 | 57.5% | 51.3% | +6.2pp |
| 2022 | -1.5% | 0.9% | -2.4pp |
| 2023 | 30.7% | 45.3% | -14.6pp |
| 2024 | 47.9% | 24.7% | +23.1pp |
| 2025 | 0.4% | 1.2% | -0.8pp |
| 2026 | 15.1% | 3.0% | +12.2pp |

Beats the index in 13 of 16 years; the misses are 2022, 2023 (−15pp, the
small-cap year) and 2025. Monthly correlation 0.80, beta 0.67. Post-tax:
portfolio 16.1% (FY tax) against the index taxed once at exit 11.3% (2011-26).
