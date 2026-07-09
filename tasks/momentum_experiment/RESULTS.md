# Momentum Experiment — Core Momentum picks vs TradingView 6M screener

**Question (2026-07-09):** TradingView's NSE 500 screener sorted by 6-month
performance shows a somewhat different list than Core Momentum (L6 v2)
holdings. Should they match? What's the difference in logic?

**Answer: no, they should not match — but they should (and do) overlap heavily.**
12 of TradingView's visible top 16 were in the live Core Momentum book on
2026-07-09 (HFCL, SCHNEIDER, WELCORP, KIRLOSENG, SYRMA, ATHERENERG,
POWERINDIA, APARINDS, AEGISLOG, JINDALSAW, J&KBANK, ADANIENSOL). The four
misses each have a specific, expected cause.

## The four sources of divergence

### 1. Vol-adjusted score, not raw return (by design)

L6 v2 ranks `momentum_6m / max(realized_vol, floor)` (`scripts/_momentum_engine.py`),
not raw 6M return. TradingView sorts by raw return. Replaying both rankings
on local data (as of 2026-05-12, `tasks/momentum_experiment/rank_compare.py`):
overlap of the two top-24 lists was 19/24.

Demoted by vol-adjustment (raw top-24, out of adj top-24):
JINDALSAW #24→#54 (vol 54%), SYRMA #22→#36, GVT&D #23→#38,
SCHNEIDER #16→#31, ATHERENERG #18→#30.

Promoted despite lower raw return (low-vol steady trends, mostly pharma):
TORNTPHARM #50→#17, JBCHEPHARM #41→#13, AUROPHARMA #32→#15,
GRANULES #34→#23, HSCL #28→#20.

This is the strategy's edge claim: smooth momentum persists better than
volatile momentum.

### 2. Stale NSE 500 universe file (action item)

`data/static/nse500_universe.csv` was last updated 2025-11-06. Four of
TradingView's top names are **not in the file at all**, so the engine can
never pick them regardless of score:

- CPPLUS (Aditya Infotech) — TradingView 6M +165.8%
- CEMPRO (Cemindia Projects) — +116.3%
- ACUTAAS (Acutaas Chemicals) — +97.6%
- EMMVEE (Emmvee Photovoltaic) — +64.9%

These are 2025 listings / renames that entered NSE 500 in a reconstitution
after our snapshot. Their TradingView rows show identical 1Y/5Y/10Y/All-time
returns — the tell of a short listing history. Note: price CSVs for all four
already exist in `nse500_data`, only the universe file lags.

### 3. Portfolio mechanics vs live screener snapshot

- Signals fire weekly (Thursday close → Friday execution); TradingView is a
  rolling intraday snapshot.
- Min-hold 8 days; a holding stays until it drops out of the top 24, so the
  book always contains names whose rank has decayed since entry (entries in
  the current book range 5–138 days old).
- Equal-weight 1/24 top-24 book ≠ a ranked leaderboard; row order on the
  dashboard is by position value, not signal rank.

### 4. Measurement details (minor)

126 trading days vs calendar 6 months; close-to-close on
corporate-action-adjusted data; scores z-scored cross-sectionally
(monotone — doesn't change rank, only comparability across dates).

## Even-if-fresh caveat

New listings still need ~126 trading days of price history before the
momentum panel produces a score (plus vol min_periods), so recent IPOs like
EMMVEE would lag TradingView by up to ~6 months even with a current
universe file. CPPLUS/ACUTAAS/CEMPRO have enough history by now — for those,
the stale universe file is the only blocker.

## Follow-ups proposed

1. Refresh `data/static/nse500_universe.csv` to the current NSE 500
   constituent list, then re-fetch prices for any newly added symbols
   (CLAUDE.md invariant: never change universe CSVs without re-fetching).
2. Consider a scheduled semi-annual universe-refresh reminder aligned to
   NSE index reconstitution (March/September).
