# Donchian channel exploration — PLAN

Opened 2026-07-22. Status: in-progress (scope locked 2026-07-22: H2 -> H1 ->
H3 -> H4; H4 added by founder).

## Why

Explore whether the Donchian channel family (N-day high/low channels, Turtle
55/20 system, 52-week-high effects) can (a) improve the existing momentum
portfolios, (b) seed a new systematic strategy, or (c) yield a market-wide
indicator with validated predictive value for subscribers.

Full literature review in `LITERATURE.md`. The two findings that shape this
plan:

1. The classic binary N-day breakout **entry** has weak/decayed evidence in
   equities (Sullivan-Timmermann-White 1999; Park & Irwin 2007). We will not
   build a raw Turtle clone.
2. The **continuous 52-week-high nearness ratio** (price / 252-day Donchian
   upper band) is a first-class, top-journal momentum predictor (George &
   Hwang 2004, JF), replicated internationally, with India-specific support
   (Raju 2023, SSRN) and momentum-crash-mitigation properties (FAJ 2023).
   No rigorous published study covers Donchian rules on Indian single stocks
   — an internal study fills a real gap.

## What already exists in this repo (don't rebuild, must beat)

- `scripts/_clean_engine.py:209` — `run_strategy()` natively accepts a
  `donchian_low_panel` and fires a `hit_donchian` exit when close < N-day
  low. A Donchian exit overlay is already wired; we only build the panel.
- TL25 v3's drawdown-control component is `(Close / 126d rolling high)^2` —
  a squared 126-day nearness-to-high term. H1 must show incremental value
  beyond this, not rediscover it.
- `kite-api/app/insights/breadth.py:124-129` already computes
  `new_52w_highs_pct`, `new_52w_lows_pct`, `net_new_highs_pct`; the breadth
  atlas found net-new-highs carries information independent of
  `pct_above_200dma` (rho = 0.73).
- `tasks/insight_engine/PATTERN_VALIDITY/` — a `multi_year_breakout`
  detector is already validated (+1.41pp at 20d). Any new Donchian-breakout
  detector must be deduplicated against it.
- Full OHLC 2009-03 to present for 533 symbols in `nse500_data_merged/`
  (high/low present; note `load_price_panels()` drops them — build high/low
  panels from raw CSVs, breadth-loader pattern).

## Hypotheses (pre-registered)

### H1 — 52-week-high nearness as a ranking feature (strategy track)

Rank NSE 500 by `close / rolling_max(high, 252)` (George-Hwang), standalone
and blended with the L6 vol-adjusted momentum score. Run through
`run_strategy()` with the standard execution config (top-25, exit-buffer,
7.5% cap, 20bps slippage), untouched across candidates.

Acceptance bars (reused from `tasks/om25_alt/`):

- Differentiation: daily-return corr with L6 < 0.7 AND top-25 holdings
  overlap < 25% AND visibly different drawdown shape; otherwise verdict is
  "momentum in disguise" regardless of returns.
- Return bar for a new product: OOS Sharpe >= 1.5 AND OOS CAGR >= 30%.
- For a blend into an existing portfolio: improves OOS Calmar without
  reducing OOS CAGR by more than 2pp.
- Secondary claim to test (from FAJ 2023): shallower momentum-crash profile —
  compare 2020-03 and 2025-correction drawdowns vs L6/TL25.

### H2 — Donchian trailing exit overlay (cheap, engine-native)

On unchanged L6 v2 and OM25 v3 entries, replace/augment the current exits
(20%-from-peak stop, rank exit) with an N-day-low Donchian exit (N in
{10, 20, 55}), head-to-head across the fixed windows.

Acceptance bar: improves OOS MaxDD or Calmar on the same portfolio without
reducing OOS CAGR by more than 2pp, consistently across OOS-A/B/C (not one
window driving it).

### H3 — Donchian breadth / market-state indicator (subscriber-value track)

Extend the breadth panel with channel metrics: % of universe at N-day channel
highs/lows for N in {20, 55, 252}, and median channel position
`(C - L_N) / (H_N - L_N)` (note: identical to stochastic %K — say so in any
docs to avoid double-counting). Profile per the `tasks/breadth_atlas/`
methodology first (distributions, dwell times, extremes, no forward returns).

Publication gates:

- Descriptive state metric ("X% of NSE 500 at 55-day highs"): breadth-atlas
  verification gates only (no-lookahead audit, boundary asserts,
  survivorship disclosure).
- Any forward-return claim, or a "Donchian breakout" watchlist detector:
  must clear the 6-check gate in `tasks/insight_engine/VALIDITY_PROTOCOL.md`
  via `pattern_validity_study.py`, and must be shown non-duplicative of
  `multi_year_breakout` (report fire-date/name overlap).

### H4 — Momentum-filtered Donchian breakout calls (daily recommendation product)

Founder idea (2026-07-22): a shareable daily "breakout call" list — filter
NSE 500 to the top quartile of momentum rankings, and among those issue a
call when a stock breaks its Donchian upper band. Long-only, max 20-25
active calls at a time, tracked as a group so subscribers see honest
aggregate stats.

Design (pre-registered before running):

- Momentum filter: top quartile by the L6-style score (126d momentum /
  realized vol) computed at signal date.
- Entry signal: signal-date close crosses above the prior N-day high
  (prior = shifted 1 day, else the cross can never fire). Test N = 55
  (Turtle System 2) and N = 20.
- Exit: signal-date close below the prior M-day low, Turtle pairing
  (55/20 and 20/10). No profit targets, no pyramiding.
- Capacity: max 25 active calls; when breakouts exceed free slots,
  priority by momentum rank. Track skipped-for-capacity calls separately.
- Execution accounting: entry/exit at next-day OHLC/4 with 20bps slippage;
  per-call P&L strictly net of slippage (house rule).
- Metrics: per-call P&L distribution, win rate, expectancy, hold days,
  yearly breakdown, active-count utilization, and an equal-weight
  portfolio-equivalent equity curve.
- Core comparison (the founder's question): identical rules on ALL NSE 500
  (no momentum filter) — does the top-quartile filter improve per-call
  expectancy, win rate, and tail profile?

Acceptance bars:

- n >= 100 calls over the study period (validity protocol floor).
- Filtered beats unfiltered on expectancy AND win rate consistently across
  OOS windows (not one regime driving it).
- For any subscriber-facing publication: the 6-check gate in
  `tasks/insight_engine/VALIDITY_PROTOCOL.md` (>= +1.0pp excess vs
  same-date NSE 500 baseline at the headline horizon, positive direction
  lift, sign consistency, persistence across halves), plus dedup analysis
  vs the validated `multi_year_breakout` detector.

## Method — fixed, inherited from om25_alt / oos_retune_2026

- Windows: IS 2009-09..2016-12 (tuning only); OOS-A 2017-01..2019-12;
  OOS-B 2020-01..2022-12; OOS-C 2023-01..2026-05; recent-era 2021-01..2026-05.
  Tune on IS only; verdicts from OOS.
- Metrics: CAGR, Sharpe, MaxDD, Calmar, turnover + differentiation
  diagnostics (corr with L6, holdings overlap) per window.
- No-lookahead: no `.shift(-N)`, no centered rollings; all panels causal.
  Engine enforces signal-date decision / next-day OHLC/4 execution.
- Probe scripts live in this folder (`build_channel_panels.py`,
  `donchian_experiment.py`), importing from `scripts/`; run outputs under
  `runs/<ts>/` (gitignored). Nothing lands in `scripts/`.

## Scope boundary — this task deliberately does NOT

- Build a Turtle-clone binary breakout entry system (evidence decayed in
  equities; see LITERATURE.md section 2.5).
- Short anything, trade intraday, or use pyramiding.
- Touch production specs (`om25_v3.py`, `tl25_v3.py`, `combo_defensive.py`,
  `_momentum_engine.py` BASELINE) — locked.
- Publish any forward-return claim without the validity gate.
- Chase a new production portfolio as the default outcome: per standing
  guidance, production portfolios are working well; frame H1/H2 as
  diagnostic/overlay work unless the bars are clearly cleared.

## Critical files

- `scripts/_clean_engine.py` (run_strategy, donchian_low_panel, metrics)
- `scripts/_momentum_engine.py` (BASELINE config, score-closure pattern)
- `nse500_data_merged/*_day.csv`, `data/static/nse500_universe.csv`,
  `data/benchmarks/nifty100.csv`
- `kite-api/app/insights/breadth.py`, `watchlists.py`
- `tasks/insight_engine/pattern_validity_study.py`, `VALIDITY_PROTOCOL.md`
- `tasks/om25_alt/RESULTS.md` (methodology template)
- `tasks/breadth_atlas/` (indicator-profiling template)

## Suggested phasing (to be locked in TASKS.md)

1. Panels + sanity: build Date x Symbol high/low panels from
   `nse500_data_merged/`, verify against known symbols, no-lookahead audit.
2. H2 first (cheapest): Donchian exit sweep on L6/OM25, fixed windows.
3. H1: George-Hwang ranking standalone + blend, differentiation diagnostics.
4. H3: breadth extension profile; validity study for any detector.
5. RESULTS.md with per-hypothesis verdicts, reproducibility block, decision.
