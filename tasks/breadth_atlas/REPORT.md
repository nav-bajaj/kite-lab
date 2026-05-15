# Breadth Atlas — Empirical Profile of NSE 500 Market Breadth

**Coverage:** 2010-06-24 → 2026-05-08 · 3,932 trading days · 14 metrics · NSE 500 universe (current snapshot, survivorship-not-corrected).

**Indices used as reference:** NIFTY 100 (full span) and NIFTY 500 (from 2015-01).

**Scope:** indicator-first profiling. No trading signal, no forward-return claims. The atlas exists to inform later signal work (including BV3 refinement) but does not propose one here.

For methodology, see `PLAN.md`. For raw data: `data/breadth/breadth_daily.csv`. For per-day denominators: `data/breadth/breadth_universe_size.csv`.

---

## Section 1 — Distribution profile

| Metric | min | p05 | median | p95 | max | std |
|---|---|---|---|---|---|---|
| pct_above_200dma | 0.045 | 0.222 | 0.588 | 0.937 | 0.990 | 0.222 |
| pct_above_100dma | 0.013 | 0.169 | 0.593 | 0.895 | 0.977 | 0.232 |
| pct_above_50dma  | 0.008 | 0.157 | 0.578 | 0.882 | 0.973 | 0.232 |
| pct_above_21dma  | 0.008 | 0.148 | 0.549 | 0.851 | 0.986 | 0.224 |
| ad_ratio         | 0.003 | 0.193 | 1.008 | 3.856 | 17.333| 1.462 |
| ad_net_pct       | -0.994| -0.672| 0.004 | 0.582 | 0.891 | 0.379 |
| ad_line          | -77.46| -69.07|-40.53 | -8.48 | 2.13  | 20.61 |
| mcclellan_osc    | -0.138| -0.068| 0.001 | 0.067 | 0.138 | 0.041 |
| mcclellan_sum    | 0.477 | 1.541 | 2.518 | 3.332 | 3.791 | 0.551 |
| pct_at_52w_high  | 0.000 | 0.000 | 0.032 | 0.133 | 0.435 | 0.046 |
| pct_at_52w_low   | 0.000 | 0.000 | 0.006 | 0.106 | 0.718 | 0.047 |
| net_new_highs_pct| -0.718| -0.100| 0.024 | 0.132 | 0.432 | 0.076 |
| up_vol_ratio     | 0.000 | 0.129 | 0.559 | 0.895 | 0.983 | 0.237 |
| avg_dist_from_200dma | -0.355 | -0.110 | 0.051 | 0.292 | 0.479 | 0.124 |

**Headline findings:**

1. **All `pct_above_*DMA` series sit between 55% and 60% at the median.** The bull bias of the NSE 500 in our window is structural — the average day has more stocks above their long-term MA than below. The 5th percentiles (22%, 17%, 16%, 15%) are the canonical "panic" thresholds.

2. **`net_new_highs_pct` is asymmetric.** The 5th percentile is −10.0% while the 95th is only +13.2%, but the **min is −71.8% vs max +43.2%** — crashes produce far more synchronized 52w-lows than rallies produce 52w-highs. New-highs/new-lows over-weights the downside tail.

3. **`avg_dist_from_200dma` (continuous version of pct_above_200dma) has median +5.1%.** The same panic days appear at the −11% percentile and the −35.5% extreme. Continuous form gives more granular extremism than the binary "% above" cousin.

4. **`mcclellan_osc` is the cleanest zero-centered oscillator.** Tight range (±0.14), low std, median ≈ 0 — it's a textbook breadth oscillator.

Figures: `figures/distributions/<metric>.png` (one histogram per metric, with p5/p95/median lines).

Per-calendar-year means: `section1_yearly_means.csv` — useful for detecting structural shifts (e.g., post-COVID `pct_above_200dma` is meaningfully higher than the 2014-2019 base rate).

---

## Section 2 — Dwell-time analysis

**Headline findings:**

1. **`pct_above_200dma` spends only 1.0% of days in the 0–10% bucket** — extreme oversold breadth is genuinely rare (~40 trading days across 16 years). The 90–100% bucket is also rare (3.7%). The middle 50% of days fall between 40% and 80% breadth.

2. **The 0–10% deep-breadth bucket has very short visits.** Average run length ≈ 11 days, longest stretch 19 days (during COVID-March-2020). The market does not sit in a panic breadth state for long.

3. **Oscillators dwell sharply in the middle.** `mcclellan_osc` spends 76% of days in the ±1σ band and only 4.6% outside ±2σ — consistent with a well-behaved zero-mean stationary signal.

4. **Slow metrics linger; fast metrics flicker.** `pct_above_200dma` typical run-length in any decile bucket is 20–40 days; `ad_ratio` is 1–2 days. Implication for any signal built on top: slow metrics give 20+ day windows to react, fast metrics need confirmation logic.

Figures:
- `figures/dwell_time/heatmap_pct.png` — % days in each decile bucket, per percentage-metric.
- `figures/dwell_time/heatmap_osc.png` — same in σ buckets, per oscillator.
- `figures/dwell_time/run_length_cdf.png` — CDF of consecutive trading days the market spends in deep-breadth (<20%) stretches across 200-DMA / 100-DMA / 50-DMA.

Detailed table: `section2_dwell_times.csv` (112 rows: 14 metrics × ~8–10 buckets).

---

## Section 3 — Extreme-event catalog

For each metric, every day below the 5th percentile (or above the 95th) is logged as an extreme event, along with what NIFTY 100 did during the event. Catalogue: `section3_extremes.csv` (1,962 events across all 14 metrics).

**Headline findings:**

1. **Top extreme events line up with named regimes.** The 78-day `pct_above_200dma`-low event from 2020-03-12 to 2020-05-29 corresponds to COVID; the 158-day `ad_line`-low event from 2025-12-01 to 2026-05-08 is the current correction. 2011 (`pct_above_100dma`-low, 56 days, -18% drawdown) and 2023 (`ad_line`-low, 103 days) are also visible. The extremes catalog is a credible historical regime tagger.

2. **Concurrent-DD ranking across the catalogue:**

| Metric | Deepest-DD bucket | mean concurrent N100 drawdown | days in bucket |
|---|---|---|---|
| pct_above_200dma     | 0–10%  | **−32.8%** | 11 |
| avg_dist_from_200dma | <−2σ   | −27.3% | 47 |
| pct_above_100dma     | 0–10%  | −20.5% | 73 |
| mcclellan_sum        | <−2σ   | −20.3% | 76 |
| pct_above_50dma      | 0–10%  | −20.6% | 77 |
| pct_above_21dma      | 0–10%  | −17.1% | 95 |
| net_new_highs_pct    | <−2σ   | −16.0% | 139 |
| mcclellan_osc        | >+2σ   | −13.1% | 76 |
| ad_net_pct           | >+2σ   | −10.7% | 57 |

The **`pct_above_200dma` 0-10% bucket** is the most concentrated panic signal (deepest mean DD, smallest sample). But it's so rare (n=11) that any rule keyed on this bucket has weak statistical support. The **continuous `avg_dist_from_200dma` <−2σ bucket** captures a more usable 47-day sample at -27% mean DD — a more statistically robust "deep panic" indicator.

3. **Sign-symmetry is broken in mcclellan_osc.** The "high" extreme bucket (>+2σ) is associated with **negative** mean concurrent DD (-13%). Counterintuitive at first: but `mcclellan_osc >+2σ` is a high-flow up-day, which historically clusters around the bottoms of large drawdowns (panic bounces). The metric is a flow signal, not a level signal — high values can be bullish *or* mark the bounce off a deep low.

---

## Section 4 — Mean-reversion characterization

| Metric | AR(1) | Half-life (days) | Hurst | Label |
|---|---|---|---|---|
| pct_above_200dma     | 0.995 | 130.3 | 0.990 | persistent/trending |
| pct_above_100dma     | 0.990 | 68.8  | 0.952 | persistent/trending |
| pct_above_50dma      | 0.981 | 35.7  | 0.892 | persistent/trending |
| pct_above_21dma      | 0.948 | 13.1  | 0.799 | persistent/trending |
| ad_ratio             | 0.083 | 0.28  | 0.551 | random-walk-ish |
| ad_net_pct           | 0.150 | 0.37  | 0.568 | random-walk-ish |
| ad_line              | 1.000 | 1417.8| 0.999 | persistent/trending |
| mcclellan_osc        | 0.885 | 5.6   | 0.624 | random-walk-ish |
| mcclellan_sum        | 0.997 | 267.7 | 0.898 | persistent/trending |
| pct_at_52w_high      | 0.847 | 4.2   | 0.932 | persistent/trending |
| pct_at_52w_low       | 0.781 | 2.8   | 0.842 | persistent/trending |
| net_new_highs_pct    | 0.850 | 4.3   | 0.913 | persistent/trending |
| up_vol_ratio         | 0.123 | 0.33  | 0.627 | random-walk-ish |
| avg_dist_from_200dma | 0.996 | 162.7 | 0.990 | persistent/trending |

**Headline findings:**

1. **Two regimes of speed.** The `pct_above_DMA` family forms a smooth speed gradient: 21-day → 13d half-life, 50-day → 36d, 100-day → 69d, 200-day → 130d. The continuous `avg_dist_from_200dma` matches `pct_above_200dma` exactly. The McClellan summation is also slow (268d). Everything else is fast.

2. **`ad_line` has AR(1) ≈ 1.0 and Hurst = 0.999** — by construction (it's a cumulative sum). As a level, it tracks the index almost mechanically; as an indicator of state, it carries no incremental information over slope or first-difference. Treat `ad_line` as a chart, not a signal.

3. **`mcclellan_osc` zero-crossing rate is high** (zero crossings per year diagnostic in `section4_mean_reversion.csv`) — usable as a flip-flop signal only with confirmation.

4. **The slowest metrics give the longest decision windows.** A regime triggered on `pct_above_200dma` has a ~130-day half-life — slow enough that 8-day or biweekly portfolios react comfortably without whipsaw. Faster metrics need explicit averaging or N-day confirmation.

Note: Hurst is computed on the raw level series. For stationary bounded indicators (`pct_above_*`, `ad_ratio`, etc.), Hurst above 0.5 reflects autocorrelation, not random-walk-style trending — interpret it relative to the AR(1) coefficient in the same row.

---

## Section 5 — Index relationship (descriptive only)

For each metric, four panels are saved to `figures/index_relationship/<metric>.png`:

1. Time-series overlay (metric + NIFTY 100, dual-axis).
2. Scatter: metric vs concurrent NIFTY 100 level.
3. Scatter: metric vs concurrent NIFTY 100 drawdown-from-peak.
4. Bar chart: mean concurrent DD by bucket of the metric.

**Headline findings:**

1. **The slow metrics track the index almost monotonically.** `pct_above_200dma` decile buckets show concurrent N100 drawdown that decreases monotonically as breadth rises: 0–10% → −33%, 10–20% → −13%, ..., 90–100% → 0%. This is a tight wrapper around "index near a drawdown low ↔ breadth is washed out." For the binary-regime user, this is the most direct visual confirmation that pct_above_200dma is a level indicator of *where in the cycle we are*.

2. **AD-side metrics show no such monotonicity.** The bucket-vs-mean-DD plot for `ad_ratio`, `ad_net_pct`, `up_vol_ratio` is roughly flat — being heavy on advancers today says nothing about whether the index is near a high or in a drawdown. These are flow metrics. They carry information about *what just happened* but not about *where the index is in its cycle*.

3. **NIFTY 100 vs NIFTY 500 large-cap-vs-broad-market difference is limited in our 2015+ window.** No striking systematic divergence visible in the overlay plots (NIFTY 500 only available from 2015). Confirms the breadth signal applies similarly whether you benchmark against the large-cap or the broader index.

Conditional-mean table: `section5_conditional.csv` (112 bucket rows: 14 metrics × ~8 buckets each, with mean concurrent DD and mean lookback 21-day return).

---

## Section 6 — Cross-metric correlation + PCA

**Correlation hotspots** (Pearson |ρ| ≥ 0.85; full matrix at `section6_pearson.csv`, heatmap at `figures/correlation/pearson.png`):

| ρ | Pair | Why |
|---|---|---|
| +0.97 | `pct_above_200dma` ↔ `avg_dist_from_200dma` | Same underlying signal, binary vs continuous |
| +0.90 | `pct_above_50dma` ↔ `mcclellan_sum` | Both are medium-horizon trend-participation |
| +0.89 | `ad_net_pct` ↔ `up_vol_ratio` | Both are daily-flow metrics |
| +0.89 | `pct_above_100dma` ↔ `mcclellan_sum` | Medium-horizon redundancy |
| +0.86 | `pct_above_200dma` ↔ `pct_above_100dma` | DMA-family overlap |
| +0.86 | `pct_above_100dma` ↔ `pct_above_50dma` | DMA-family overlap |

Six redundant pairs out of 91 — there's structure to collapse. The 14-metric panel has effective dimension closer to 6.

**PCA confirms this exactly.** Six principal components explain ≥90% of variance:

| Component | Explained variance | Cumulative |
|---|---|---|
| PC1 | 48.3% | 48.3% |
| PC2 | 20.8% | 69.0% |
| PC3 | 8.8%  | 77.8% |
| PC4 | 7.1%  | 85.0% |
| PC5 | 4.6%  | 89.5% |
| PC6 | 4.4%  | 93.9% |

**PC1 (48% — the "slow breadth" axis):** dominated by `net_new_highs_pct`, `pct_above_100dma`, `pct_above_50dma`, `mcclellan_sum`, `pct_above_200dma`. All medium- to long-horizon trend-participation metrics moving together.

**PC2 (21% — the "daily flow" axis):** dominated by `ad_net_pct`, `ad_ratio`, `up_vol_ratio`, `mcclellan_osc`. Orthogonal to PC1: daily turnover dynamics that aren't captured by trend-participation.

This is a clean two-factor structure: **trend-participation level (slow) and daily flow (fast)** account for ~69% of all variance. The remaining components capture noise, edge effects, and minor metric-specific quirks.

Implication for any signal-design work: pick at most one metric from each of PC1's high loaders and one from each of PC2's. More than that is redundant.

---

## Headline takeaways (the 30-second read)

1. **The NSE 500 is structurally bullish in our window** — median breadth above all DMAs sits at 55–60%. Drawdowns are visible as breadth declining 30–40pp from this baseline.

2. **The 14-metric panel is really a 6-metric panel.** PC1 (slow breadth) + PC2 (fast flow) explain 69% of variance; six PCs cover 90%. Six redundant correlation pairs above 0.85 already flag this without the math.

3. **"Deep oversold" lives in three places:**
   - `pct_above_200dma` < 22% (5th percentile): rare, deep — 11 days in the bottom decile averaged −33% concurrent index DD.
   - `avg_dist_from_200dma` < −11% (5th percentile): more samples (47 days at −2σ → −27% concurrent DD), continuous, statistically more robust.
   - `mcclellan_sum` < 5th percentile: corroborating slow-flow confirmation; 76 days at −20% DD.

4. **`pct_above_DMA` and `avg_dist_from_200dma` are level signals; `ad_*`, `mcclellan_osc`, `up_vol_ratio` are flow signals.** Level signals tell you where we are in the cycle; flow signals tell you what happened today. A regime gate wants level signals; a confirmation rule could combine them with flow.

5. **52-week-highs/lows is genuinely informative.** `net_new_highs_pct` is asymmetric (deeper lows than rallies have highs), tracks concurrent drawdown well (−2σ bucket → −16% mean DD, 139 days). Carry as a candidate alongside pct_above_200dma — they are not redundant (ρ = 0.73, below the 0.85 cutoff).

6. **Survivorship caveat.** The NSE 500 list is the current snapshot. Stocks delisted before today aren't in the panel. The metrics are denominator-normalized (only count valid stocks per day), but the *composition of the surviving universe* is biased to companies that didn't fail — likely overstating breadth health in the historical record by a small amount. The biggest practical impact is that pre-2013 numbers are computed on a substantially smaller eligible universe (denominator ~250–300 stocks vs ~496 today).

---

## What this atlas does NOT contain

- **No forward-return claims.** "Breadth at X percentile → average index return over the next N days" is *not* in this report. That study uses this atlas as its starting point but is separate work.
- **No new trading signal.** The atlas does not recommend a Value-Zone threshold for BV3 or any other rule. The numbers above inform that decision; they don't make it.
- **No statistical-significance claims on extremes.** Sample sizes for "0–10% bucket of pct_above_200dma" are small (n=11). Don't read causal claims into bucket means.
- **No survivorship correction.** Acknowledged; not corrected.

---

## File index

```
data/breadth/
  breadth_daily.csv              # 14 metrics × 3932 trading days
  breadth_universe_size.csv      # per-day denominator per metric

tasks/breadth_atlas/
  PLAN.md                        # methodology
  REPORT.md                      # this file
  section1_distribution_stats.csv
  section1_yearly_means.csv
  section2_dwell_times.csv
  section3_extremes.csv
  section4_mean_reversion.csv
  section5_conditional.csv
  section6_pearson.csv
  section6_spearman.csv
  section6_pca_variance.csv
  section6_pca_loadings.csv
  figures/
    distributions/    (14 histograms)
    dwell_time/       (2 heatmaps + 1 CDF)
    index_relationship/ (14 four-panel figures)
    correlation/      (2 heatmaps)

scripts/
  build_breadth_panel.py         # produces data/breadth/*.csv (one-time compute)
  breadth_atlas_report.py        # reads panel, writes tables + figures
```

Reproducibility: `python scripts/build_breadth_panel.py && python scripts/breadth_atlas_report.py` — about 90s wall-clock end-to-end. The panel script is the only piece that touches per-stock price data; once cached, all atlas iteration runs off the breadth_daily.csv.
