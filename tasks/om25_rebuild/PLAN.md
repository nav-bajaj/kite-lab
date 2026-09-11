# OM25 rebuild — a quality-momentum book built from scratch on the honest universe

## Why

market_data_spine established that the production portfolios were tuned on
today's index membership backdated: on the point-in-time universe OM25 v3
earns 24.8% CAGR from 2020 against a published 42.3%, and −65% in 2008
behind a "20% drawdown stop" that is a per-stock trail. The founder's call
(D-13): nothing of the old parameters is worth preserving. This task
builds the strategy up again, one decision at a time, with the pass
criteria written before the first search run.

## What is fixed by the brief (BRIEF.md)

Universe is a decision (LargeMidcap 250 vs Nifty 500). Score family is the
capture statistics (UC, CR, 50/50). Regime signal is ROC-based with
confirmation hysteresis, and whether the regime changes the score at all is
tested. No weight cap, no per-stock stop, no 50-up/50-down eligibility.

## Method — gates first, then search

1. **Pre-committed criteria** (TASKS.md §0), signed by the founder before
   any run. Once signed they do not move.
2. **Windows.** IS 2006-01-01 → 2015-12-31. OOS 2016-01-01 → today, with
   three sub-windows: 2016-2019, 2020-2022, 2023-2026. Walk-forward on top:
   refit each year on the trailing ten, trade the next twelve months,
   chained 2016 → today.
3. **Build order** — each step is decided on IS only, OOS is opened once:
   a. Score: UC / CR / 50-50, one regime (no tilt), on both universes.
   b. Regime: ROC definition and hysteresis, applied as a tilt (two
      regimes) versus not at all (one regime), on the winner of (a).
   c. Portfolio mechanics: top-N, exit buffer, cadence — a small grid.
   d. Lookback and min_obs.
4. **Multiple-testing correction.** Every candidate run is counted; the
   final IS Sharpe is deflated for the number tried before it is compared
   to the gate.
5. **OOS opened once.** The single surviving configuration per universe
   runs OOS and walk-forward; the result is reported whatever it says.

## Scope boundary

- Reads the master store only. Writes nothing under `data/` except
  `tasks/om25_rebuild/runs/` (gitignored).
- Does not touch production or the four running portfolios.
- Does not restate anything published.

## Critical files

- `scripts/_clean_engine.py` — the backtest engine (run unchanged; the
  score and regime are passed in)
- `scripts/om25_v3.py` — the capture-statistics score, to be re-implemented
  here without the 50/50-day rule and with a ROC regime panel
- `tasks/market_data_spine/` — the store and its decisions
