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
