# Breadth Atlas — Empirical Profile of NSE 500 Market Breadth

## Why this work

`tasks/MM-tuning/VALUE_ZONE_REGIME.md` flagged that the Defensive production lock is paused pending **deeper breadth-metric exploration**. The existing work (BV3 in `scripts/_three_state_regime_test.py`) jumps straight from "% above 200-DMA" to a trading regime gate. That's signal-first.

This task goes indicator-first. We profile breadth as a market object — distributions, extremes, dwell times, mean-reversion, relationship to the headline index — **with no portfolio attached**. The goal is to understand what the indicator *looks like* before deciding how to use it, the way you'd profile VIX or the yield curve before building anything on top.

**Deliverable**: a markdown report (`tasks/breadth_atlas/REPORT.md`) + the underlying daily breadth CSVs (`data/breadth/`) + a Jupyter notebook (`notebooks/breadth_atlas.ipynb`) with the plots that drive the report. No strategy, no backtest, no recommendation to trade anything.

---

## Scope

### Universe
**NSE 500** only (current snapshot, `data/static/nse500_universe.csv`). Survivorship caveat acknowledged in report.

### Price panel
`nse500_data_merged/` (the GDF-stitched 2009-2026 panel that OOS retune and walk-forward both use). Daily OHLCV. Volume needed for up-vol/down-vol metric.

### Index references
- **Nifty 100** — `data/benchmarks/nifty100.csv` (production benchmark; large-cap)
- **Nifty 500** — `indices_data/NIFTY_500.csv` (matches the breadth universe)

Both indices used as reference in every "index relationship" view so you can see large-cap vs broad-market divergence directly.

### Date range
2009-09-01 → 2026-05-08 (~16.7 years), matching `oos_retune_2026` and `walk_forward`. First 252 days reserved as warmup for the longest lookback (200-DMA + buffer); first reported date is the 253rd trading day, ~2010-09.

---

## Breadth metrics computed (the indicator surface)

For each trading day, compute and persist:

| # | Metric | Definition | Range |
|---|---|---|---|
| 1 | `pct_above_200dma` | % of valid NSE 500 stocks with `Close > 200-DMA` | [0, 1] |
| 2 | `pct_above_100dma` | same with 100-DMA | [0, 1] |
| 3 | `pct_above_50dma` | same with 50-DMA | [0, 1] |
| 4 | `pct_above_21dma` | same with 21-DMA — short-term participation | [0, 1] |
| 5 | `ad_ratio` | (advancers / decliners) for the day | (0, ∞) |
| 6 | `ad_net_pct` | (advancers − decliners) / total valid stocks | [-1, 1] |
| 7 | `ad_line` | cumulative sum of `ad_net_pct` (rebased to start at 0) | ℝ |
| 8 | `mcclellan_osc` | 19-day EMA of `ad_net_pct` − 39-day EMA | ℝ |
| 9 | `mcclellan_sum` | cumulative sum of `mcclellan_osc` (Summation Index) | ℝ |
| 10 | `pct_at_52w_high` | % of stocks at their 252-day high today | [0, 1] |
| 11 | `pct_at_52w_low` | % at their 252-day low | [0, 1] |
| 12 | `net_new_highs_pct` | `pct_at_52w_high − pct_at_52w_low` | [-1, 1] |
| 13 | `up_vol_ratio` | up-day volume / total volume (across stocks, by stock) | [0, 1] |
| 14 | `avg_dist_from_200dma` | mean of `(Close − 200DMA) / 200DMA` across stocks — continuous version of #1 | ℝ |

**"Valid stock" on a given day** = stock has ≥ N days of price history ending that day (N = max lookback for the metric, e.g., 252 for `pct_at_52w_high`). Stocks with insufficient history are excluded from the denominator for that metric on that date. This handles late entrants without survivor-bias correction.

Output: `data/breadth/breadth_daily.csv` with `date, <metric_1>, <metric_2>, ...` plus `breadth_universe_size.csv` (the per-day denominator per metric — useful diagnostic).

Reuse `build_breadth_regime()` math from `scripts/_alternative_regime_test.py:88-125` as the kernel for #1-#4; everything else is new.

---

## Studies (the six sections of the report)

### Section 1 — Distribution profile

For each of the 14 metrics:

- Full-period stats: min, max, mean, median, std, skew, kurtosis
- Percentiles: 1, 5, 10, 25, 50, 75, 90, 95, 99
- Histogram (one per metric)
- Same stats broken out by calendar year (a 14×17 table) — surfaces structural shifts (e.g., did the post-COVID rally permanently elevate `pct_above_200dma`?)

### Section 2 — Dwell-time analysis

Per metric, bucket into natural bands:
- For the `pct_above_*` metrics: deciles 0-10%, 10-20%, ..., 90-100%
- For oscillators (`mcclellan_osc`, `avg_dist_from_200dma`): standardize to z-score, then bucket by σ (≤-2, -2 to -1, -1 to 0, 0 to 1, 1 to 2, ≥2)

For each bucket report:
- % of trading days in the bucket (steady-state probability)
- Average run-length once entered (how long does it stay there)
- Longest consecutive streak
- Number of distinct visits per year (mean and median)

Output: per-metric dwell-time tables + a single heatmap (metric × bucket → % of days), and a run-length CDF plot.

### Section 3 — Extreme-event catalog

Per metric, list every date where the metric crossed below the 5th percentile (or above the 95th), and the date of the subsequent cross back into the middle 90%. For each event record:
- Entry date / exit date / duration
- Nifty 100 level at entry / exit / max-drawdown-during / max-gain-during
- Nifty 500 same
- Concurrent values of the *other* breadth metrics at entry — diagnostic for "do extremes co-occur"

Output: `breadth_extremes.csv` with one row per (metric, event). Sorted view: longest events, deepest events, most clustered (multiple metrics extreme at once).

### Section 4 — Mean-reversion characterization

Per metric:
- AR(1) coefficient (level on lagged level) and implied half-life of deviations from the mean
- Hurst exponent (does the series trend or mean-revert)
- For oscillators: zero-crossing frequency (how often does it flip sign)

This is **descriptive statistics**, not a tradable signal. The goal is to know which metrics are noisy/fast (high zero-crossing, short half-life) vs slow/persistent.

### Section 5 — Index relationship (purely descriptive)

For each metric × each index (Nifty 100, Nifty 500):

1. **Time-series overlay plot** — dual y-axis: breadth metric and index level. Visual sanity, marked with named regimes (COVID, 2025 correction, etc.) from `oos_retune_2026` window labels.
2. **Scatter: metric vs concurrent index level** — fit a non-parametric line (e.g., LOWESS). No forward-return interpretation.
3. **Scatter: metric vs concurrent index drawdown-from-peak** — answers "when breadth is X, is the index typically near a high or in a drawdown?"
4. **Conditional table** — bucket the metric (deciles), report mean concurrent index DD-from-peak, mean concurrent 21-day index return *up to and including today* (lookback, not forward), and mean position in 52-week range.
5. **Nifty 100 vs Nifty 500 difference** — for each metric, plot the simultaneous index-level difference. Large-cap-only breadth (proxied by index difference) vs broad-market breadth (the metric) — when do they diverge?

No forward-return claims in this section. The "what does breadth predict" question is deliberately out of scope here — that's a follow-up.

### Section 6 — Cross-metric correlation matrix

14×14 Pearson correlation. Also Spearman (rank correlation, robust to outliers). Highlight pairs with |ρ| > 0.85 — those carry redundant information and can be collapsed in any future signal work.

Bonus: PCA on the metric panel. How many principal components explain 90% of variance? Interpret PC1 (likely "general breadth"), PC2 (likely "fast vs slow") for intuition.

---

## Output file structure

```
data/breadth/
  breadth_daily.csv               # one row per trading day, all 14 metrics
  breadth_universe_size.csv       # per-day denominator per metric (diagnostic)
  breadth_extremes.csv            # catalog from Section 3

notebooks/
  breadth_atlas.ipynb             # plots + interactive exploration

tasks/breadth_atlas/
  PLAN.md                         # this file
  REPORT.md                       # final narrative (the deliverable)
  figures/                        # PNG plots referenced by REPORT.md
    distributions/                # one per metric
    dwell_time/
    extremes/
    index_relationship/
    correlation/

scripts/
  build_breadth_panel.py          # NEW — computes all 14 metrics, writes CSVs
  breadth_atlas_report.py         # NEW — generates plots and stats tables
```

`scripts/build_breadth_panel.py` is the only piece that touches price data; it's the once-per-data-refresh compute. The report script runs on the cached CSV — fast iteration on framing without recomputing breadth.

---

## Verification gates

Before trusting any number in the report:

1. **Breadth-universe-size sanity**: on 2026-05-08, the NSE 500 panel has ~499 valid stocks; on 2010-09-01, the valid count should be smaller (newer listings not yet present). Plot universe size over time and eyeball.
2. **Boundary metrics match existing code**: `pct_above_200dma` on 2026-05-08 should match what `build_breadth_regime()` in `_alternative_regime_test.py` produces on the same date with the same panel. Add as a one-line assert.
3. **AD ratio sanity**: `ad_ratio` ≈ 1 on average; on a market-up day where index gained >2%, `ad_ratio` >> 1. Single-day spot check.
4. **No look-ahead**: every metric on date `T` uses only prices up to and including `T`. Specifically, `pct_at_52w_high` on `T` uses the [T-252, T] window inclusive of T. Audited by ensuring no `.shift(-N)` or `.rolling().center=True` in the metric code.
5. **Survivorship audit**: report the universe size series so the reader can see how the denominator grows. The metrics are denominator-normalized, so this is descriptive, not a correction.

---

## Phased execution

### Phase 0 — Wire-up (~3 hours)
- Write `scripts/build_breadth_panel.py`. Load merged panel, compute all 14 metrics, write CSVs.
- Pass verification gates 1, 2, 3, 4.

### Phase 1 — Statistics + tables (~2 hours)
- Write `scripts/breadth_atlas_report.py` for Sections 1, 2, 4, 6 (all pure-stats).
- Generate the CSV/markdown tables that anchor the report.

### Phase 2 — Plots + extremes catalog (~3 hours)
- Distribution histograms, dwell-time heatmap, run-length CDF.
- Section 3 extremes catalog (one CSV + one ranked table view).
- Section 5 index-relationship plots (one per metric × each index).

### Phase 3 — Narrative (~half-day)
- Write `REPORT.md` with each section's headline finding in 2-3 sentences, followed by the relevant figure + table. No recommendations, no forward-looking claims — just "here is what the indicator looks like."

Total: ~1.5 days of focused work. Compute cost is negligible (single pass over the panel).

---

## Open questions for the user

1. **Volume data availability**: `up_vol_ratio` (metric 13) requires per-stock volume. The merged panel has it for the Kite portion (2020+); the GDF portion (2009-2019) likely does not have reliable volume. Acceptable to compute #13 only from 2020-09 onward and flag accordingly? (Alternative: drop #13 entirely.)
2. **PCA inclusion**: Section 6 PCA is "bonus" — it's the only piece that needs sklearn and adds 30 min. Keep or cut?
3. **Index = `nifty100.csv` vs `nifty500.csv` data quality**: confirm that `indices_data/NIFTY_500.csv` covers the full 2009-2026 span. If not, Section 5's Nifty-500 view starts later.

---

## What this plan deliberately does NOT do

- Does not propose any trading signal.
- Does not compute forward returns conditional on breadth state. That's a separate study (which this atlas would inform).
- Does not refine BV3 thresholds or revisit `VALUE_ZONE_REGIME.md`. The atlas exists to *enable* that work, not duplicate it.
- Does not add point-and-figure metrics (Bullish Percent Index). Indian markets don't have a standard PnF charting convention; building one is an unrelated rabbit hole.
- Does not handle survivorship bias beyond the per-day valid-stock denominator. NSE 500 list is current snapshot.
- Does not commit until you approve the plan.
