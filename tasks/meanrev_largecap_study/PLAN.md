# Oversold mean-reversion on Nifty 100 — study

Quick research probe: does Connors-style short-term mean reversion
(buy sharp selloffs in large caps that are still in uptrends, exit into
first strength) have per-trade edge on the Nifty 100? Candidate swing
stock-pick strategy for the platform.

## Design (2026-08-22)

- **Form:** per-trade event stats, one open trade per symbol, no
  capital constraint. Follow-on to `tasks/vcp_l6_study/`.
- **Data:** `nse500_data_merged/` (CA-adjusted, current Nifty 100
  constituents, ~2010 → 2026-08-19). Index: NIFTY_100 spliced from
  `indices_data_historical/` (2010→2026-05) + `indices_data/` (live).
- **Gates:** stock close > its 200DMA; regime filter = index > its
  200DMA (ablated).
- **Entries (variants):** RSI(2) < 10; RSI(2) < 5; >= 4 consecutive
  down closes; 5-day return < -5%.
- **Execution:** signal at close, fill next open, 0.1% slippage each
  side (large-cap liquidity; each extra 0.1%/side costs ~0.2%/trade).
- **Exits:** close > 5DMA, else 10-day time stop. No hard stop in base
  (Connors); -7% stop as ablation.

## Data-quality exclusions

Four unadjusted corporate actions found in `nse500_data_merged` during
this study (one-day drops matching bonus/demerger ratios):
ZYDUSLIFE 2010-04-05, MOTHERSON 2013-12-20, ADANIENT 2015-06-03
(demerger), TRENT 2026-05-29. ANANDRATHI 2026-05-29 (-51.6%, 1:1 bonus
signature) found separately via the VCP study. Trades spanning these
dates are excluded. The 2026-05-29 pair suggests recent corporate
actions are not being adjusted — flagged for follow-up outside this
study.

## Known limitations

- Survivorship bias: current constituents (membership file has
  placeholder effective-dates, so no point-in-time universe).
- Signals cluster in selloffs (max ~50 concurrent) — a product would
  need position caps; per-trade stats ignore that.

## Files

- `meanrev_backtest.py` — signals + trade sim + variant summaries.
- `trades_<variant>.csv`, `summary.json` — outputs.
- `RESULTS.md` — findings.
