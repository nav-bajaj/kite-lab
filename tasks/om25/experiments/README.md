# OM25 Parameter Review — May 2026

These scripts run the parameter studies that produced the locked-in OM25
stack. All use `scripts/_clean_engine.py` (no-lookahead engine, daily-peak
fixed, V2 eligibility codified). Run from repo root:

```bash
source .venv/bin/activate
python tasks/om25/experiments/_om25_atr_test.py
```

## Studies (in order they were run)

| Script | Study | Outcome |
|--------|-------|---------|
| `_om25_baseline_refresh.py` | Baseline under daily-peak engine | Refresh — pre-fix numbers superseded |
| `_om25_atr_test.py` | ATR mult × floor × no-stop | DROPPED trailing stop entirely |
| `_om25_eligibility_test.py` | Eligibility variants (6) | Keep V2 (no filter, data-quantity only) |
| `_om25_lookback_test.py` | Capture-window lookback (6) | Keep 252d (unchanged) |
| `_om25_weights_test.py` | Composite signal weights (8) | Keep V1 50/50 (unchanged); V5 noted as productization candidate |
| `_om25_cadence_test.py` | Entry cadence (4) | Keep Monthly + Bi-weekly (unchanged); Weekly numerically best, kept off-menu for branding |
| `_om25_min_obs_test.py` | Min observations threshold (6) | Keep 220 (unchanged) — non-parameter, robustness check |
| `_om25_topn_buffer_test.py` | Top-N × buffer 3×3 grid | Keep 25/15 (unchanged) |

## Skipped studies

- **Sizing** — kept equal-weight 1/N + drift, not re-tested. TL25 review
  found pyramid-into-winners had no universal benefit; assumed similar.
- **Universe finalization** — decision is to offer all three universes
  (NSE 500, Nifty 250, Nifty 100) as subscriber-choice tiers rather than
  pick one flagship.

## Locked-in stack (final)

See `../DESIGN.md` for the full review writeup. Headline:

- **Engine:** clean, daily-peak, V2 score function (no positive-return filter inside `_score_om25_window`)
- **Signal:** 50/50 pct_rank(upside_capture) + pct_rank(capture_ratio)
- **Window:** 252 trading days
- **Eligibility:** data-quantity only (≥220 obs, ≥50 up/dn days)
- **Exit:** Close < 200 DMA on weekly check + rank-drop at next entry
- **NO trailing stop**
- **Top-25, exit_buffer=15, equal 1/N, 7.5% cap, drift after entry**
- **20 bps slippage, OHLC/4 next-day execution**
- **Tiers:** Monthly + Bi-weekly, on each of NSE 500 / Nifty 250 / Nifty 100

## Productization candidate

**OM25 Defensive (V5)** — same stack, signal becomes `pct_rank(capture_ratio)`
only. Trades 18% CAGR for 7% better DD; picks defensive low-beta names.
See README for subscriber-fit detail and open questions.

## Interesting observations from this review

1. **The Friday-peak engine quirk was performance-flattering.** Daily-peak
   correction reduced CAGR by 2-7% and Sharpe by 0.07-0.29 across variants.
2. **Trailing stop wasn't earning its keep.** "No stop" wins CAGR universally
   and ties or wins Sharpe on the flagship. Dropped — strategy gets simpler.
3. **The positive-return prefilter was empirically wrong.** V2 (no filter)
   strictly beats V1 (positive 252d return) on Sharpe, CAGR, and even DD.
4. **The cash-drag-as-defense story for Monthly is dead.** Avg cash now
   0.4-0.9% (vs 16-23% pre-fix). V2's looser eligibility + no trailing stop
   means Monthly stays fully deployed; it's just slower-redeploying.
5. **Universe-size pattern in lookback.** NSE 500 wants 378d, Nifty 250 wants
   252d, Nifty 100 wants 126d. Bigger universe → longer window. Picked 252d
   as universe-agnostic compromise.
6. **CR-only is a real alternative product, not just a weight variant.** V5's
   selection bias (defensive low-beta) is genuinely different from V1's
   (asymmetric high-beta).
7. **Weekly is the numerical winner on cadence.** Avg Sharpe 2.05 vs
   1.94/1.98 for Monthly/Bi-weekly. Not adopted: preserves the existing
   two-tier subscriber product, +0.07-0.10 Sharpe wasn't worth migration
   churn.
8. **Several "knobs" turned out to be non-parameters.** min_obs and Top-N/
   buffer both showed all-tested-values within noise of the current setting.
   These are robustness checks rather than tuning opportunities.

## Important: numbers across scripts use slightly different periods

- `_om25_atr_test.py`, `_om25_eligibility_test.py`, `_om25_weights_test.py`,
  `_om25_cadence_test.py`, `_om25_min_obs_test.py`,
  `_om25_topn_buffer_test.py`: start at idx 252 (~1 year of history).
  Period: 2021-02 to 2026-05.
- `_om25_lookback_test.py`: start at idx 504 (longest lookback) for fair
  comparison. Period: 2022-02 to 2026-05.

This means lookback-study absolute numbers are lower across the board
(excluded the strong 2022 capture-asymmetry period); rankings between
variants are still comparable within each script.
