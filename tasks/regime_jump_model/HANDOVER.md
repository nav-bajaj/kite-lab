# Handover — Statistical Jump Model regime detection

Paste this into a new Claude Code chat to pick up the work. It is a
context primer, not a finished spec.

## Goal

Evaluate whether a **Statistical Jump Model (SJM)** regime detector can
(a) augment our regime-aware portfolios and/or (b) power a
subscriber-facing "Market Regime" indicator.

## Source material (three papers)

- **Hamilton (1989)** — classic Markov regime-switching (HMM). Baseline;
  its raw online signal flips ~9x/year (too noisy to trade).
- **Bemporad, Breschi, Piga, Boyd (2018), "Fitting Jump Models"**
  (arXiv:1711.09220) — the machinery. State assignment + a fixed penalty
  `lambda` on every state transition, fit by coordinate descent with a
  dynamic-programming step. Generalizes k-means/HMM; the penalty buys
  temporal persistence.
- **Shu, Yu, Mulvey (2024), "Downside Risk Reduction Using
  Regime-Switching Signals"** (Journal of Asset Management 25(5); arXiv:2402.05272)
  — the application. 2-state (bull/bear) SJM on exponentially-weighted
  **downside-deviation + Sortino** features; `lambda` tuned by
  walk-forward CV directly on strategy Sharpe. OOS on S&P 500 / DAX /
  Nikkei 1990-2023, 10 bps cost, 1-day delay: signal switches ~1x/year,
  lower vol + max drawdown than buy-and-hold, higher Sharpe than HMM.
- **Reference implementation:** `jumpmodels` (pip, scikit-learn API —
  `JumpModel`, `SparseJumpModel`, `.fit/.predict/.predict_online`).
  <https://github.com/Yizhan-Oliver-Shu/jump-models>

## The critical caveat

The model **confirms** regime shifts, it does **not predict** them
(~half-month detection latency in the COVID example). Treat it as a
risk-management / context tool, not timing alpha. This framing must hold
in any subscriber-facing copy too.

## Why it fits this repo

We already de-risk on regime, with a cruder detector:

- OM25 v3 and COMBO Defensive use `NIFTY 100 close vs 100-DMA, 3-day
  confirmation hysteresis` (`docs/portfolios.md:20, 85`).
- The engine already accepts a pluggable regime signal:
  `run_momentum(... regime_panel=<pd.Series[date]->bool, True=bull>,
  bear_exposure=...)` (`scripts/_momentum_engine.py:194-198`), currently
  produced by `scripts.om25_v3.build_regime_panel_confirmed`.

So the SJM is a **drop-in replacement for `regime_panel`**, not a
rebuild. Write a `build_regime_panel_jump()` returning the same
boolean-series shape and pass it in.

## Two tracks

### Track A — portfolio overlay
Feed an SJM bear-flag into **COMBO Defensive** (our drawdown-reduction
sleeve) first. Fewer regime flips -> lower turnover -> the paper's
downside-risk reduction, which is exactly COMBO's mandate.
**Do NOT touch L6 v2** — it is the deliberately-unhedged pure-momentum
growth sleeve (`docs/portfolios.md:71`).

### Track B — subscriber indicator
A "Market Regime: Bull/Bear, confirmed N days" badge in the insights
engine (`kite-api/app/insights/`, `kite-dashboard/src/content/insights/`),
shown alongside each portfolio's stance. The persistence guarantee (does
not flip weekly) is the trust proposition. Label it a *confirming*
signal, not a forecast.

## Guardrails (from CLAUDE.md)

- Tune `lambda` on **Indian data, walk-forward** — do not import the US value.
- Benchmark against our **existing MA-crossover overlay**, not just naive
  HMM. The paper beats HMM; our bar is beating `build_regime_panel_confirmed`.
- Follow `tasks/insight_engine/TDD_POLICY.md` for any forward-return claim
  (spec test first, see it fail, then implement).
- Use `.predict_online()` (no-lookahead), never `.predict()`, for any
  production/backtest signal.

## Proposed first task

Scaffold `tasks/regime_jump_model/` (PLAN.md + TASKS.md + RESULTS.md +
`_meta.yml`, per `tasks/CONVENTIONS.md`) that:

1. Adds `jumpmodels` to a task-local venv; fits a 2-state SJM on NIFTY 100
   daily returns (downside-deviation + Sortino features, a few EWMA
   half-lives).
2. Plots the SJM regime series vs the current MA-crossover overlay and
   counts switches/year for each.
3. Re-runs COMBO Defensive with the SJM bear-flag; reports
   delta max-DD / delta CAGR / delta turnover vs the current overlay.
4. Writes RESULTS.md with the OOS comparison.

## Blocker

No price panels in the cloud container (only `data/final_portfolio`,
`data/published`, `data/static`). The harness can be built dry; it runs
once NIFTY 100 daily OHLC is available in the session (expects a panel
dir like `nse500_data_merged/`, benchmark under `data/benchmarks/`).

## Open scoping questions

- Which track first — subscriber indicator (lower risk), portfolio
  overlay (needs OOS validation), or one shared research task feeding both?
- Number of states — 2 (matches paper + existing binary overlay) or 3
  (bull/neutral/bear, richer context, more tuning/overfit risk)?

## Key files

- `scripts/_momentum_engine.py` — engine; `regime_panel`/`bear_exposure` hooks
- `scripts/om25_v3.py` — `build_regime_panel_confirmed` (current detector)
- `scripts/run_combo_defensive_portfolio.py` — COMBO runner (Track A target)
- `docs/portfolios.md` — portfolio specs + regime overlay descriptions
- `kite-api/app/insights/` — insights engine (Track B home)
- `tasks/CONVENTIONS.md`, `tasks/insight_engine/TDD_POLICY.md` — process rules
