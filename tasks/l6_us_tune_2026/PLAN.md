# L6 v2 US retune 2026

## Why

L6 v2 transferred to US data the cleanest of the four locked-Indian strategies (US 2020-26: 54.0% CAGR / 1.64 Sharpe vs India 59.4% / 1.92). Worth checking if any US-specific tuning lifts CAGR further, especially given US momentum literature suggests different optimal lookbacks (12-1) than NSE.

Approach: step-by-step sweep, one parameter at a time, in this priority order:
1. **lookback_months** ← this run
2. (next, TBD based on results)

## Methodology

**Inverted IS/OOS** to avoid overfitting to recent regimes:

| Window | Period | Length | Role |
|---|---|---:|---|
| IS | 2010-01-01 → 2017-12-31 | 8.0y | Tune here |
| OOS_A | 2018-01-01 → 2019-12-31 | 2y | Late-cycle / 2018 Q4 selloff |
| OOS_B | 2020-01-01 → 2022-12-31 | 3y | COVID + rally + 2022 Fed cycle |
| OOS_C | 2023-01-01 → 2026-05 | 3.4y | AI rally + 2025 correction |
| OOS_full | 2018-01-01 → today | 8.4y | Aggregate |

**Pass criteria** (per oos_retune_2026/PLAN.md):
- IS Sharpe ≥ 1.0
- OOS-full Sharpe ≥ 1.0
- Each OOS sub-window Sharpe ≥ 0.7
- OOS-full Max DD ≥ -45%

**Anti-overfit:** select on IS Sharpe; do not look at OOS during search; one re-tune attempt max if OOS fails.

**Universe:** S&P 500 (incl. SP500 ∩ NDX), 503 symbols.
**Engine:** `_clean_engine.run_strategy()` via `_momentum_engine.run_momentum()`.

## Stage 1 — lookback_months sweep

All other params at locked L6 v2 BASELINE:

| Held fixed | Value |
|---|:---|
| skip_days | 0 |
| top_n | 24 |
| exit_buffer | 0 |
| rebalance | weekly |
| signal_day | thursday |
| vol_floor | 0.05 |
| vol_power | 1.0 |
| min_hold_days | 8 |
| cross_sectional_zscore | True |
| max_weight | 7.5% |
| slippage | 20 bps |
| drawdown_stop | 0 |

| Sweep | Values |
|---|---|
| lookback_months | {3, 6, 9, 12} |

= **4 configs**. Pick best by IS Sharpe; subsequent stages will pivot from there.
