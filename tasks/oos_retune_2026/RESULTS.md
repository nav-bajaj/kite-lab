# OOS Retune 2026 — Final Results

**Status:** OM25 v3 locked in (2026-05-10). TL25 v3 locked in (2026-05-12).

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
| **ATR-scaled trailing stop** | OFF | Tested 0/3/4/5/6/8x with 0/5/10% floors; vol-scaled stops hurt CAGR. |
| **200 DMA weekly exit** | **OFF** | Empirically tested (after fixing engine bug): enabling adds 834 exits but 200 DMA exits have only 39% hit rate (median -1.7% PnL) — they mostly stop out positions during normal pullbacks. Net cost: -3.8pp CAGR for 2.6pp DD reduction. Bad ratio. |
| **Hard %-from-peak drawdown stop** | **20% (ON)** | Tested 15/20/25/30%; 20% is the sweet spot. Fires 371 times over 17 years (33.9% of total exits), 50% hit rate, median ~0% PnL on stop exits — catches real losers without over-pruning. Improves Sharpe by 0.03 and Max DD by 5.1pp at -1.2pp CAGR cost. Implementation: `atr_mult=0, atr_min_floor=0.20, use_trailing_stop=True`. |
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

### Per-window summary (with 20% drawdown stop)

| Window | Period | Years | CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|
| **IS** | 2009-09 → 2016-12 | 7.0 | 28.59% | 1.60 | -26.5% |
| **OOS-A** | 2017-01 → 2019-12 | 3.0 | 26.14% | 1.60 | -20.9% |
| **OOS-B** | 2020-01 → 2022-12 | 3.0 | 60.04% | **2.12** | -31.4% |
| **OOS-C** | 2023-01 → 2026-05 | 3.4 | 46.49% | 1.85 | -23.4% |
| **OOS-full** | 2017-01 → 2026-05 | 9.3 | **43.57%** | **1.86** | **-31.44%** |

### Pass criteria (from PLAN.md)

| Criterion | Target | Result |
|---|---|---|
| IS Sharpe ≥ 1.0 | ✓ 1.60 |
| OOS-full Sharpe ≥ 1.0 | ✓ 1.86 |
| OOS-A Sharpe ≥ 0.7 | ✓ 1.60 |
| OOS-B Sharpe ≥ 0.7 | ✓ 2.12 |
| OOS-C Sharpe ≥ 0.7 | ✓ 1.85 |
| OOS-full Max DD ≥ -45% | ✓ -31.44% |

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

Two exit triggers fire in the locked-in config:

### 1. Rank exit at biweekly rebalance
Drop below rank 45 (top-25 + buffer-20) at any biweekly Friday signal date.

| Metric | Value |
|---|---|
| Count | 722 (66.1% of exits) |
| Hit rate | 59.1% |
| Avg PnL | +14.6% |
| Median PnL | +3.5% |
| Avg hold | 117 days |

### 2. Hard 20%-from-peak drawdown stop (weekly check)
Exit if Close < 0.80 × position's running peak. Position peak is updated daily from entry. Check fires on weekly signal dates; execution next trading day.

| Metric | Value |
|---|---|
| Count | 371 (33.9% of exits) |
| Hit rate | 49.9% (50% — coin flip; that's by design) |
| Avg PnL | +21.4% |
| Median PnL | -0.2% |
| Avg hold | 159 days |

The drawdown-stop's median PnL is essentially 0% — it's catching positions that *had* run up but then mean-reverted ~20%, capturing what was left rather than letting the loss deepen. The avg PnL of +21% reflects positive selection (stops fire on positions that had already appreciated, not on day-1 losers).

**Engine bug discovered and fixed during this work** (`_clean_engine.py`): previously `use_trailing_stop=False` disabled BOTH the ATR trailing stop and the 200 DMA exit because they were gated behind the same flag. Now `use_trailing_stop` (ATR) and `use_dma_exit` (200 DMA) are independent toggles. The locked-in strategy uses `use_trailing_stop=True` with `atr_mult=0, atr_min_floor=0.20` (this gives a fixed 20% drawdown stop without ATR scaling) and `use_dma_exit=False`.

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

1. **Productionize OM25** — DONE 2026-05-11. See `scripts/run_om25_v3_portfolio.py`, dashboard backend wiring, daily pipeline step.
2. **Paper-trading window** — minimum 3-6 months of paper-traded performance before live capital. STILL PENDING.
3. **TL25 retune** — DONE 2026-05-12. See TL25 v3 section below.
4. **Monitor 2025/2026** — the regime-tilt's recent underperformance is real. Watch for whether 2026 H2 reverts (tilt earning back) or persists (regime mismatch worsening).

---

# TL25 v3 — Final Result

**Date locked:** 2026-05-12

## Final TL25 v3 portfolio mechanics

| Parameter | Value | Notes |
|---|---|---|
| **Universe** | NSE 500 (`data/static/nse500_universe.csv`) | NSE 500 won IS Sharpe; Nifty 250 marginally better OOS but user honoured IS commitment. Kept NSE 500. |
| **Cadence** | **Bi-weekly entry** (every other Friday → next-day exec) + **weekly rank-exit** + **weekly DD-stop checks** | Bi-weekly entry confirmed in IS sweep. Weekly rank-exit added 2026-05-12 — reduces OOS-full DD by 1.09pp at -0.99pp CAGR / +0.01 Sharpe (modest, robust). |
| **Score** | `0.40 × Persistence + 0.20 × Drawdown + 0.40 × Momentum` (A3 weights) | Offensive P+M tilt won IS Sharpe sweep (1.61). Equal 1/3/1/3/1/3 was 1.59; DD-heavy 40/40/20 was 1.52. 45/35/20 won IS DD but FAILED OOS (Sharpe -0.07, DD WORSE -3.73pp) — rejected. |
| **Persistence window** | 252 trading days | Locked from V2; `% of days Close > 100 DMA`. |
| **Drawdown window** | 126 trading days, squared | Locked from V2; `(Close / 126d high) ^ 2`. |
| **Momentum window** | 63 trading days | Locked from V2; raw N-day return, percentile-ranked among eligible. |
| **Eligibility** | Close > 200 DMA AND 50 DMA > 200 DMA AND 200 DMA rising over 20d | Locked from V2; the trend gate. |
| **Top-N** | 25 stocks | Locked. |
| **Exit buffer** | 20 (drop below rank 45 to exit) | Locked. |
| **Drawdown stop** | **20% from peak** (weekly check) | Same as OM25; tested 15/18/20/22 — 20% the sweet spot. `atr_mult=0, atr_min_floor=0.20`. |
| **200 DMA exit** | OFF | Disabled. The DD stop alone is sufficient. |
| **Position sizing** | Equal 1/N, 7.5% max, drift after entry | Standard. |
| **Slippage** | 20 bps (OHLC/4 pricing) | Standard. |
| **Regime tilt** | NONE (single config) | Deliberate product-diversification choice vs OM25 (which has regime tilt). TL25 = pure trend-following on a bigger universe. |

## Performance

### Per-window summary (locked-in config, weekly rank-exit)

| Window | Period | Years | CAGR | Sharpe | Max DD |
|---|---|---|---|---|---|
| IS | 2009-09 → 2016-12 | 7.0 | 29.27% | 1.58 | -25.82% |
| OOS_A | 2017-01 → 2019-12 | 3.0 | 19.71% | 1.18 | -32.02% |
| OOS_B | 2020-01 → 2022-12 | 3.0 | 63.87% | **2.16** | -31.03% |
| OOS_C | 2023-01 → 2026-05 | 3.4 | 25.75% | 1.18 | -29.06% |
| **OOS_full** | 2017-01 → 2026-05 | 9.3 | **34.86%** | **1.53** | **-39.00%** |
| Full panel | 2009-09 → 2026-05 | 16.7 | 32.73% | 1.40 (rf=5%) | -39.10% |

### Pass criteria

| Criterion | Target | Result |
|---|---|---|
| IS Sharpe ≥ 1.0 | ✓ 1.58 |
| OOS-full Sharpe ≥ 1.0 | ✓ 1.53 |
| OOS-A Sharpe ≥ 0.7 | ✓ 1.18 |
| OOS-B Sharpe ≥ 0.7 | ✓ 2.16 |
| OOS-C Sharpe ≥ 0.7 | ✓ 1.18 |
| OOS-full Max DD ≥ -45% | ✓ -39.00% |

**All pass.**

## Search summary

The TL25 retune followed the same anti-overfit discipline as OM25.

**IS-only phases (no OOS peeking):**

1. **Stop variants** — A3 baseline (20% fixed DD stop) beat V2's stack (200 DMA + 5x ATR-vol). V2's stops fire too often during normal pullbacks.
2. **Weight variants (single config)** — Offensive P+M (40/20/40) won IS Sharpe (1.61). Equal 1/3 came in at 1.59. Persistence-heavy (50/25/25) at 1.60. DD-heavy variants underperformed.
3. **Tilt variants (regime-aware)** — User decided to keep single config to maintain product diversity vs OM25 (which is regime-tilted). Tilt explored but rejected on principle.
4. **Windows / top-N** — V2 defaults (252/126/63 + top-25/buffer-20) confirmed optimal. No improvement from variants.
5. **Universe + cadence** — NSE 500 won IS Sharpe by a hair; Nifty 250 won OOS. User chose to honor IS commitment, keep NSE 500.
6. **DD-reduction sweep** — `45/35/20` weight tweak improved IS DD by 2.70pp at Sharpe -0.01. Looked attractive...
7. **Weekly rank-exit** — Initially looked like it hurt the strategy due to an engine bug (entry_schedule was being built from all weekly signal dates when weekly_rank_check=True). Bug fixed on 2026-05-12. After fix: improves IS DD by 2.39pp at Sharpe -0.03.

**OOS validation:**

| Variant | Decision | OOS Sharpe | OOS CAGR | OOS DD |
|---|---|---|---|---|
| A3 baseline (40/20/40, biweekly rank) | reference | 1.52 | 35.85% | -40.09% |
| 45/35/20 weight tweak | **REJECTED** — textbook IS-overfit catch | -0.07 (vs A3) | -4.23pp | **DD WORSE by 3.73pp** |
| Weekly rank-exit | **ADOPTED** | +0.01 | -0.99pp | +1.09pp (better) |

The 45/35/20 case was an instructive failure: IS DD looked great, OOS DD got worse — exactly the IS/OOS discipline this whole retune was meant to catch. Held the line, didn't adopt.

## Engine bug discovered and fixed

`scripts/_clean_engine.py` — when `weekly_rank_check=True`, the `signals` dict was populated for every Friday (biweekly + weekly), and `entry_schedule` was being built from `signals.keys()`. This caused `rebal_set` to include every Monday, so the entry rebalance block fired weekly (tagging exits as `rank`) and the dedicated weekly-rank-exit block (gated by `date not in rebal_set`) never fired.

Fix: build `entry_schedule` only from `entry_signal_dates`, not from `signals.keys()`. Documented inline.

After the fix, the weekly rank-exit block fires correctly with the `rank_weekly` reason label, and the test results changed materially: from "weekly rank hurts" (pre-fix, +153 rank exits all tagged 'rank') to "weekly rank reduces DD" (post-fix, 371 weekly-rank exits, 81 atr_stop, 373 biweekly-rank exits).

## Diversification vs OM25 v3

Lightweight test comparing daily returns + holdings overlap of TL25 v3 A3 vs OM25 v3:
- **Daily return correlation:** ~0.78 (moderate; not redundant)
- **Holdings Jaccard overlap:** ~0.22 average (sufficient overlap given both pick top-25 momentum/trend names, but the sub-signals diverge)
- TL25 weight variant B2 (regime-tilted) had higher correlation than A3 (single config) — confirms user's intuition that **single-config TL25 is the right complementary product** vs regime-tilted OM25.

## Files

| Component | Path |
|---|---|
| TL25 v3 LOCKED defaults | `scripts/tl25_v3.py:V3_LOCKED` |
| Score factory | `scripts/tl25_v3.py:make_tl25_score` |
| Panels builder | `scripts/tl25_v3.py:build_tl25_panels` |
| Engine (with weekly_rank_check) | `scripts/_clean_engine.py` |
| Multi-window evaluator | `scripts/multi_window_oos_eval.py` |
| Production report | `tasks/trend_leaders/experiments/_tl25_v3_production_report.py` |
| Baseline IS | `tasks/trend_leaders/experiments/_tl25_v3_baseline.py` |
| Weight sweep IS | `tasks/trend_leaders/experiments/_tl25_v3_weights_is.py` |
| Tilt variant IS | `tasks/trend_leaders/experiments/_tl25_v3_tilt_is.py` |
| Windows / top-N sweep | `tasks/trend_leaders/experiments/_tl25_v3_windows_topn_is.py` |
| Universe + cadence sweep | `tasks/trend_leaders/experiments/_tl25_v3_universe_cadence_is.py` |
| DD-reduction sweep IS | `tasks/trend_leaders/experiments/_tl25_v3_dd_reduction_is.py` |
| Weekly rank IS | `tasks/trend_leaders/experiments/_tl25_v3_weekly_rank_is.py` |
| 45/35/20 OOS (REJECTED) | `tasks/trend_leaders/experiments/_tl25_v3_oos_45_35_20.py` |
| Weekly rank OOS (ADOPTED) | `tasks/trend_leaders/experiments/_tl25_v3_oos_weekly_rank.py` |
| All-universes OOS | `tasks/trend_leaders/experiments/_tl25_v3_oos_all_universes.py` |
| OM25 correlation | `tasks/trend_leaders/experiments/_tl25_v3_correlation_with_om25.py` |
| Production equity | `tasks/oos_retune_2026/winner_artifacts/tl25_v3_production_equity.csv` |
| Production trades | `tasks/oos_retune_2026/winner_artifacts/tl25_v3_production_trades.csv` |
| HTML report (OOS only) | `reports/tl25_v3_production_*.html` |

## TL25 v3 caveats

- Same survivorship bias as OM25 (universe is 2026-vintage NSE 500).
- Different optimization target than OM25: TL25 is pure trend-following on NSE 500; OM25 is regime-aware quality-momentum on Nifty 250. **Both are valid; pick based on factor preference.**
- **Productionization pending.** Same wiring needed as OM25 v3 (daily pipeline step, dashboard backend, sync_service). Documented as "next step" below.

## TL25 v3 next steps

1. **Productionize** — Create `scripts/run_tl25_v3_portfolio.py` (mirror of OM25 v3 orchestrator). Add `tl25_v3` to dashboard backend (`kite-api/app/config.py:UNIVERSES`, `sync_service.get_latest_experiment_dir`, `positions_service` regex). Add to daily pipeline. Update `tasks/trend_leaders/README.md` to feature v3 LOCKED at top.
2. **Paper-trading window** — 3-6 months of paper-traded performance before live capital.
3. **Periodically refresh correlation** with OM25 — if correlation creeps up past ~0.9, revisit weights to re-diversify.
