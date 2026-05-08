# OM25 Parameter Review — May 2026

These scripts run the parameter studies that produced the locked-in OM25
stack. All use `scripts/_clean_engine.py` (no-lookahead engine, daily-peak
fixed). Run from repo root:

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

## Pending studies

- Min observations threshold (currently 220/252 ≈ 87%)
- Cadence head-to-head (monthly vs bi-weekly under locked-in stack)
- Top-N × buffer grid
- Sizing (equal-weight vs score-weighted vs pyramid)
- Universe finalization (especially flagship choice given 2025 resilience)

## Locked-in stack (so far)

See `../DESIGN.md` for the full review writeup. Headline:

- Engine: clean, daily-peak (no-lookahead, all closes update peak)
- Signal: 50/50 pct_rank(upside_capture) + pct_rank(capture_ratio)
- Window: 252 trading days
- Eligibility: data-quantity only (≥220 obs, ≥50 up/dn days)
- Exit: Close < 200 DMA on weekly check + rank-drop at next entry
- NO trailing stop
- Top-25, exit_buffer=15, equal 1/N, 7.5% cap
- 20 bps slippage, OHLC/4 next-day execution

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
4. **Universe-size pattern in lookback.** NSE 500 wants 378d, Nifty 250 wants
   252d, Nifty 100 wants 126d. Bigger universe → longer window. Picked 252d
   as universe-agnostic compromise.
5. **CR-only is a real alternative product, not just a weight variant.** V5's
   selection bias (defensive low-beta) is genuinely different from V1's
   (asymmetric high-beta). Same signal family, different question — clean
   basis for a "defensive" tier.

## Important: numbers across scripts use slightly different periods

- `_om25_atr_test.py`, `_om25_eligibility_test.py`, `_om25_weights_test.py`:
  start at idx 252 (~1 year of history). Period: 2021-02 to 2026-05.
- `_om25_lookback_test.py`: start at idx 504 (longest lookback) for fair
  comparison. Period: 2022-02 to 2026-05.

This means lookback-study absolute numbers are lower across the board (excluded
the strong 2022 capture-asymmetry period); rankings between variants are still
comparable within each script.
