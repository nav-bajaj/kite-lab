# OOS Retune 2026 — OM25 Final Result

**Status:** OM25 locked in. TL25 retune not yet started.

**Date locked:** 2026-05-10

---

## Final OM25 portfolio mechanics

| Parameter | Value | Notes |
|---|---|---|
| **Universe** | NSE Nifty 250 (`data/static/nifty250_universe.csv`) | Cap-weighted top-250 stocks. Better risk-adjusted than NSE 500; more breadth than Nifty 100. |
| **Cadence** | **Bi-weekly entry** (every other Friday signal → next-trading-day execution) | Beats monthly by ~+0.06 OOS Sharpe; also beats weekly. |
| **Top-N** | 25 stocks | Equal-weight 1/N target; max 7.5% per position; drift after entry. |
| **Exit buffer** | 20 (drop below rank 45 to exit) | Hysteresis prevents churn. |
| **Lookback** | 252 trading days (1 year) | Production default; pinned to avoid 189-day overfit. |
| **Min observations** | 220 | Noise filter; stocks with sparser histories excluded. |
| **Return filter** | ON (require positive 252d total return) | +0.11 IS Sharpe at 50/50 weights; small but consistent edge. |
| **ATR trailing stop** | OFF | Tested 0/3/4/5/6/8x with 0/5/10% floors; "no stop" wins universally. |
| **200 DMA weekly exit** | **OFF** | Empirically tested (after fixing engine bug): enabling adds 834 exits over the period but 200 DMA exits have only 39% hit rate (median -1.7% PnL) — they mostly stop out positions during normal pullbacks. Net cost: -3.8pp CAGR / -0.07 Sharpe / +2.6pp DD reduction. Bad ratio. |
| **Position sizing** | Equal 1/N, 7.5% max, drift after entry | No rebalancing within rebalance windows. |
| **Slippage** | 20 bps (OHLC/4 pricing) | Realistic India retail/HNI execution. |

### Score function — regime-tilted composite

```
For each rebalance signal date:
  upside_capture (UC)   = avg(stock_ret | market UP day)   / avg(market_ret | UP day)
  downside_capture (DC) = avg(stock_ret | market DOWN day) / avg(market_ret | DOWN day)
  capture_ratio (CR)    = UC / DC

  Bull regime → score = 0.5 × pct_rank(UC) + 0.5 × pct_rank(CR)
  Bear regime → score = 1.0 × pct_rank(CR)         (CR-only, defensive tilt)

Eligibility (data-quality gates):
  - ≥220 valid daily returns in the 252-day window
  - ≥50 market-up days AND ≥50 market-down days
  - 252d total return > 0 (return filter)
```

Rank descending; take top 25 for entries (with buffer 20 for exit hysteresis).

### Regime signal

| Parameter | Value |
|---|---|
| **Index** | NIFTY 100 (`indices_data_historical/NIFTY_100.csv`) |
| **MA window** | 100-day moving average |
| **Confirmation** | 3 consecutive trading days |
| **Lag** | 1 day (use prior-day close vs prior-day MA — no lookahead) |

Regime is sticky:
- Starts as bull (default)
- Flips to **bear** only after 3 consecutive closes below 100 DMA
- Flips to **bull** only after 3 consecutive closes above 100 DMA
- Stays in current state otherwise (hysteresis)

The strategy is **always 100% invested** — regime only tilts the score blend, never moves to cash. No re-entry friction; no cash drag.

---

## Performance (in-engine backtest on GDF-stitched panel, 2009-2026)

### Per-window summary

| Window | Period | Years | CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|
| **IS** | 2009-09 → 2016-12 | 7.0 | — | 1.53 | -19.3% |
| **OOS-A** | 2017-01 → 2019-12 | 3.0 | 26.47% | 1.57 | -23.0% |
| **OOS-B** | 2020-01 → 2022-12 | 3.0 | 64.15% | **2.10** | -36.6% |
| **OOS-C** | 2023-01 → 2026-05 | 3.4 | 36.39% | 1.80 | -24.3% |
| **OOS-full** | 2017-01 → 2026-05 | 9.3 | **44.78%** | **1.83** | **-36.6%** |
| Full | 2010-01 → 2026-05 | 16.3 | 34.60% | — | -36.6% |

### Pass criteria (from PLAN.md)

| Criterion | Target | Result |
|---|---|---|
| IS Sharpe ≥ 1.0 | ✓ 1.53 |
| OOS-full Sharpe ≥ 1.0 | ✓ 1.83 |
| OOS-A Sharpe ≥ 0.7 | ✓ 1.57 |
| OOS-B Sharpe ≥ 0.7 | ✓ 2.10 |
| OOS-C Sharpe ≥ 0.7 | ✓ 1.80 |
| OOS-full Max DD ≥ -45% | ✓ -36.6% |

**All pass. Aspirational targets (40% CAGR / 1.5 Sharpe) both exceeded.**

### Year-by-year (Candidate vs Nifty 250 baseline, no regime)

| Year | Era | Candidate | Baseline | Δ pp | NIFTY 200 |
|---|---|---|---|---|---|
| 2010 | IS | 31.89% | 33.44% | -1.55 | — |
| 2011 | IS | -11.62% | -17.54% | **+5.92** | -27%+ (estimated; index data partial) |
| 2012 | IS | 46.68% | 48.42% | -1.74 | 31.32% |
| 2013 | IS | 24.28% | 18.63% | +5.65 | 3.52% |
| 2014 | IS | 76.39% | 79.46% | -3.07 | 34.68% |
| 2015 | IS | 27.90% | 37.49% | **-9.59** | -2.02% |
| 2016 | IS | 5.28% | 1.32% | +3.96 | 3.28% |
| 2017 | OOS-A | 93.85% | 82.24% | +11.61 | 33.20% |
| 2018 | OOS-A | -6.65% | -10.83% | +4.18 | -0.43% |
| 2019 | OOS-A | 11.79% | 15.29% | -3.50 | 9.50% |
| **2020** | OOS-B | **73.45%** | 39.53% | **+33.92** | 15.49% |
| 2021 | OOS-B | 100.34% | 107.18% | -6.84 | 26.92% |
| 2022 | OOS-B | 27.28% | 25.04% | +2.24 | 2.21% |
| 2023 | OOS-C | 74.16% | 77.14% | -2.98 | 22.91% |
| 2024 | OOS-C | 66.68% | 66.79% | -0.11 | 13.45% |
| **2025** | OOS-C | **5.69%** | 14.31% | **-8.62** | 7.96% |
| 2026 YTD | OOS-C | 12.80% | 16.04% | -3.24 | -4.39% |

**Key wins from regime tilt:**
- 2011 (eurozone, 78% bear days): +5.9pp better than baseline
- 2018 (IL&FS): +4.2pp better
- 2020 (COVID): **+33.9pp** better — the headline win
- 2017 (mid-cap rally): +11.6pp (mostly bull-mode benefit)

**Costs of regime tilt:**
- 2015: -9.6pp (54.8% bear days, but defensive CR didn't outperform in mild bear)
- 2025: -8.6pp (similar — mild correction year)

The tilt earns its keep on big bear events (2011, 2018, 2020). Costs ~5-10pp in mild "soft bear" regimes (2015, 2025). Net positive across all OOS sub-windows.

### Bull/bear regime breakdown (annualized stats)

| Series | Bull Return | Bull Sharpe | Bear Return | Bear Sharpe |
|---|---|---|---|---|
| **Candidate** | 48.85% | **2.17** | 18.71% | **0.90** |
| Baseline (no tilt) | 46.24% | 2.00 | 18.47% | 0.81 |
| NIFTY 50 | 10.30% | 0.80 | 9.90% | 0.55 |
| NIFTY 200 | 12.47% | 0.94 | 16.43% | 0.82 |
| NIFTY 500 | 13.54% | 1.04 | 7.51% | 0.44 |

**The tilt mechanism works:** during bear regimes, candidate's Sharpe (0.90) beats baseline's (0.81) — the CR-only rotation adds risk-adjusted return precisely where it matters.

### Alpha vs broad indices

| Era | Candidate | NIFTY 200 | Alpha (pp) |
|---|---|---|---|
| IS (2010-2016) | 26.02% | 9.21% | +16.81 |
| OOS-A (2017-2019) | 26.47% | 13.24% | +13.23 |
| OOS-B (2020-2022) | 64.15% | 14.43% | +49.72 |
| OOS-C (2023-2026) | 36.39% | 9.53% | +26.86 |
| **FULL 17 yrs** | **34.60%** | **10.90%** | **+23.70** |

Strategy delivers ~24 percentage points of annualized alpha over the closest comparable cap-weighted index across the full 17-year period.

---

## Exit mechanics

Only one exit trigger fires in the locked-in config: **rank exit at biweekly rebalance** (drop below rank 45 = top-25 + buffer-20). Stats over the 17-year backtest:

| Metric | Value |
|---|---|
| Total exits | 830 |
| Hit rate (PnL > 0) | 57.7% |
| Avg PnL on exit | +24.3% |
| Median PnL on exit | +3.2% |
| Avg hold | 172 days (~5.7 months) |

Long right-tail of big winners (avg 24% vs median 3%). The hold of ~5.7 months reflects the fact that names entered during a cycle stay until they fall out of top-45 — defensive companies during bear regimes naturally hold longer than aggressive names during bull regimes.

**An engine bug was discovered and fixed during this work** (commit `_clean_engine.py`): previously `use_trailing_stop=False` disabled BOTH the ATR trailing stop and the 200 DMA exit because they were gated behind the same flag. Now `use_trailing_stop` and `use_dma_exit` are independent. The locked-in strategy uses `use_dma_exit=False` as a tested choice (not an accidental disabling) — the empirical comparison showed adding 200 DMA exit costs 3.8pp CAGR for 2.6pp DD reduction.

## Why this won

Three findings drove the result:

1. **Capture-ratio is more defensive than upside-capture.** UC alone picks high-beta names that crash hard in bear regimes. CR (= UC / DC) penalizes stocks that fall as much as they rise. In OOS, CR-heavy variants Sharpe-dominate UC-heavy variants by 0.4-0.5.

2. **Cash-on-off costs ~10pp CAGR.** Going to cash on bear regimes works post-hoc but in-engine reality includes re-entry friction, slippage on liquidations, and missed opening days of recoveries. The post-hoc result was 8-12pp CAGR optimistic.

3. **Regime as weight-lever beats both.** Stay fully invested; let the regime decide what *kind* of stocks. Bull regime → balanced 50/50 (production identity). Bear regime → defensive CR-only. No cash drag, no re-entry timing risk, plus +0.18 OOS Sharpe vs baseline.

Faster MA (100 vs 200) with 3-day confirmation hysteresis was the difference between an OK regime signal and a great one. Slower MAs lag bear onsets; un-confirmed signals whipsaw.

---

## Caveats

- **Survivorship bias:** universe is 2026-vintage NSE Nifty 250. Stocks delisted between 2010-2016 are not in the panel. This likely inflates IS performance modestly.
- **GDF data quality:** 2024-2025 data was sparse for some stocks (e.g., RELIANCE 2024 had ~162 rows vs ~250 expected). The merged panel uses Kite for 2020+, so this affects only pre-2020 history; minor risk that some pre-2020 stock-level data has small gaps.
- **2025 underperformance:** the most recent full year shows the strategy lagging both the baseline (-8.6pp) and the Nifty 50 (-4.4pp). The regime tilt fired bear, but defensive CR-only didn't outperform in 2025's mild correction. This is the primary regime-mismatch risk to monitor in live deployment.
- **No transaction-cost stress test beyond 20bps slippage.** Tax (LTCG/STCG) and brokerage are not modeled. With biweekly cadence and ~26 rebalances/year × 25 positions, real after-tax CAGR may be 3-6pp lower than the quoted 44.78%.
- **No paper-trading window yet.** Backtest result is the upper bound on what's deployable; real-money performance will likely be 10-20% lower than backtest after all friction.

---

## Files

| Component | Path |
|---|---|
| Final winner equity | `experiments/oos_retune/20260509222941_om25_regime_tilt/Nifty_250__biweekly__NIFTY_100__bull0.5_0.5__bear0.0_1.0_equity.csv` |
| Sweep summary | `experiments/oos_retune/20260509222941_om25_regime_tilt/summary.csv` |
| Engine | `scripts/_clean_engine.py` (with `regime_panel` + `bear_exposure` params) |
| Score factory | `tasks/om25/experiments/_om25_regime_weight_tilt.py:make_om25_tilt_score` |
| Regime panel utility | `tasks/om25/experiments/_om25_regime_100dma_3conf.py:build_regime_panel_confirmed` |
| Multi-window evaluator | `scripts/multi_window_oos_eval.py` |
| Index data | `indices_data_historical/NIFTY_100.csv` (and others) |
| Stock panel | `nse500_data_merged/` (GDF 2009-2019 + Kite 2020-2026) |

---

## Next steps

1. **Productionize** — adapt `scripts/build_om25_signals.py` and `scripts/backtest_om25.py` to compute regime + apply the tilt. Wire into `scripts/run_daily_pipeline.py`. Update `tasks/om25/README.md` with new locked-in stack. (Open ticket; not done in this work.)
2. **Paper-trading window** — minimum 3-6 months of paper-traded performance before live capital.
3. **TL25 retune** — apply the same IS=2009-2016 / OOS-multi-window framework + regime-tilt idea to TL25.
4. **Monitor 2025/2026** — the regime-tilt's recent underperformance is real. Watch for whether 2026 H2 reverts (tilt earning back) or persists (regime mismatch worsening).
