# raam_transplant — crowding-aware ranking + bottom-up exposure for the stock engine

Opened 2026-07-19. Branch `raam_transplant` (off `main`).

## Why

Review of Giordano's *Ranked Asset Allocation Model* (2018 Charles H. Dow
Award) found exactly one architectural component the production stock
engine has never tested: a **correlation/crowding factor (C)** — ranking
candidates by how correlated they are with the rest of the selection.
It also suggests one mechanism worth re-testing in a new form:
**bottom-up per-slot cash fallback** (exposure driven by the fraction of
the strategy's own top ranks with positive absolute momentum), which is
structurally different from the top-down index regime gate that failed
its gates in `tasks/breadth_atlas/combo_3state/`.

The production gap both ideas target: momentum portfolios crowd into hot
themes (PSU/defence/railways 2023-24, smallcaps into the 2025
correction) and a theme unwind hits all 24 names at once. No production
scorer measures this ex ante.

RAAM's M/V/T components are already covered in stronger forms (L6
vol-adjusted momentum, TL25 trend structure), and `tasks/om25_alt/`
predicts further vol tilts fail in Indian equities. We transplant C and
the exposure mechanism only. The paper's backtest evidence itself is
weak (gross of costs, no OOS split, 12 assets) — we take the design
pattern, not the numbers.

## Key adaptation: residual correlation, not raw correlation

Among 500 stocks all carrying index beta, ranking on raw pairwise
correlation selects low-beta defensives — the "too defensive" attractor
that killed LV25. So C is computed on **market-residual returns**:

- beta of each stock vs NIFTY 100, trailing 252d
- residual return r_i − beta_i · r_m
- C(stock) = average pairwise correlation of residuals vs the current
  candidate set, trailing 63d

This isolates shared theme/sector exposure (crowding) from beta.
Parameters are v0 defaults; finalized in Phase 0 with data in hand,
before any experiment runs.

## Locked config

- Universe: **NSE 500**, point-in-time membership filter
  (`data/static/nse500_membership.csv`).
- Cadence: **weekly** — Thursday signal, Friday OHLC/4 execution,
  mirroring L6 v2 so results are directly comparable.
- Costs: 0.2% slippage every fill; all reported P&L **net of slippage**.
- Baseline comparator: **L6 v2** (same universe, same cadence).
- Windows: IS 2009-09→2016-12; OOS-A 2017-2019; OOS-B 2020-2022;
  OOS-C 2023-2026; plus 2021+ stitched era.
- Engine: `scripts/_clean_engine.py` via `scripts/_momentum_engine.py`;
  probes live in this folder, `scripts/` stays closed.

## Questions and pre-registered gates

**Q0 (diagnostic).** Does high internal residual correlation of the L6
book predict deeper forward 20-60d portfolio drawdown? Does
positive-momentum breadth in the top-40 predict forward return/DD?
Gate G0: at least one diagnostic shows a monotone quantile spread worth
acting on → proceed to experiments; else close with the diagnostic as
the deliverable.

**E1 — L6-DIV (correlation-penalized selection).** Greedy top-24: pick
rank 1, then each next pick scored `z − λ · avg_residual_corr(candidate,
picked)`. λ tuned on IS only.
Pass: Calmar improves in ≥2 of 3 OOS windows, AND no OOS window gives up
more than 3pp CAGR vs L6, AND annualized turnover rises ≤10pp.

**E2 — breadth throttle on L6.** Exposure =
clip(share of top-40 with positive 126d momentum, floor, 1.0), fed
through the engine's float `regime_panel`. Floor tuned on IS only.
Pass: ≥70% rolling-window Sharpe wins vs bare L6 (breadth_atlas T1
protocol), AND no calendar year with >5pp deeper intra-year drawdown.

**E3 — RC25 (stretch; only if E1 or E2 passes).** Standalone ranked
composite: M = 126d vol-adjusted momentum, C = residual correlation,
T = additive trend state, per-slot cash fallback, top 25.
Pass (om25_alt differentiation bar): daily corr with L6 < 0.7, holdings
overlap < 25%, Sharpe ≥ 1.5, CAGR ≥ 30%.

Gates are fixed before running. A miss is a miss; partial results go to
`docs/failed_experiments.md`, not into gate renegotiation.

## Scope boundary

- No changes to production `scripts/`; no production deployment
  decisions here.
- No multi-asset/ETF RAAM clone (possible separate future task).
- Insight-engine productisation (crowding gauge) only after diagnostics,
  under `tasks/insight_engine/TDD_POLICY.md`, forward-return claims
  gated by the validity-study protocol.

## Data notes (verified 2026-07-19)

- `nse500_data_merged/`: 534 symbols, 2009-03-05 → 2026-07-17, CA-adjusted.
- `indices_data_historical/NIFTY_100.csv` is stale (ends 2026-05-08);
  fresh copy at `/Users/navdeep/Documents/stock_data/indices_data_full/`
  (through 2026-07-17). Experiments must point at the fresh source.
- `nse500_membership.csv` effective-dating is shallow (all rows
  1900-01-01) — deep-window backtests carry survivorship bias. This
  equally affects the L6 baseline, so head-to-head comparisons remain
  apples-to-apples; absolute deep-history CAGRs are indicative only.

## Critical files

- `scripts/_clean_engine.py`, `scripts/_momentum_engine.py` — engine + L6 scorer
- `docs/portfolios.md` — production specs
- `tasks/om25_alt/RESULTS.md`, `tasks/breadth_atlas/combo_3state/` — prior art and gate templates
- `docs/failed_experiments.md` — negative-result ledger
- `kite-api/app/insights/scores.py`, `tasks/insight_engine/TDD_POLICY.md` — if Phase 3 productisation happens
