# Core + Quality Momentum, India vs US, 2019-2025 — RESULTS

**Date:** 2026-07-20 → 2026-07-24
**Branch context:** analysis only, no production code touched
**Status:** Complete. Findings published as a shareable beta-tester artifact.

## What this was

Beta-tester-facing comparison of Core Momentum (L6 v2) and Quality Momentum
(OM25 v3) on Indian vs US equities over the common window 2019-01-01 →
2025-12-31, extending the `us-data` branch study (May 2026). India: fresh runs
of the locked production configs on NSE 500 / Nifty 250 via
`_clean_engine.run_strategy()`. US: sliced from the saved
`experiments/us_strategies_2017/` curves. Both runs start trading 2017; the
window is sliced and rebased, so 2019 opens with an already-invested book.

## Headline (pre-tax, 20 bps slippage/side)

| | Core IN | Core US | Quality IN | Quality US | NIFTY 100 | SPY |
|---|---:|---:|---:|---:|---:|---:|
| CAGR | 49.1% | 38.7% | 48.2% | 34.2% | 13.5% | 17.2% |
| Sharpe | 1.91 | 1.28 | 2.26 | 1.23 | 0.77 | 0.87 |
| MaxDD | −37.8% | −35.6% | −32.9% | −41.2% | −38.1% | −33.7% |
| ×1M | 16.39 | 9.87 | 15.71 | 7.82 | 2.42 | 3.03 |

## After a flat 25% annual tax (losses carried forward; benchmarks untaxed)

| | Core IN | Core US | Quality IN | Quality US |
|---|---:|---:|---:|---:|
| CAGR | 37.5% | 29.4% | 36.7% | 26.0% |
| ×1M | 9.30 | 6.09 | 8.92 | 5.03 |

Benchmarks left untaxed (buy-and-hold defers realisation). Flat 25% is a
simplification, not actual STCG/LTCG rates.

## Takeaways

1. Both strategies beat their home index by 17-36 pp/yr in both markets under
   parameters that never saw a US price.
2. India is the stronger home — Quality Momentum Sharpe 2.26 (IN) vs 1.23 (US).
3. Quality Momentum flips character abroad: defensive at home (shallowest DD),
   deepest DD in the US (−41.2%, 2022 Fed cycle).
4. The markets complement: India carried 2021-22, the US carried 2025
   (+60.6% Core US vs −8.6% Core IN pre-tax).

## Caveats

Static universe CSVs both sides (survivorship tailwind, but symmetric so the
IN-US comparison is clean). 20 bps slippage kept for US (conservative).
Window-start holdings inherited from the 2017-18 run-up. Backtested, not live.

## Artifact

Published (private, share-controlled) at:
https://claude.ai/code/artifact/82d096ff-4597-472c-9732-a6dd13a1720c
Brand-faithful one-pager per `~/marketworks-design/DESIGN.md` (lichen palette,
Fraunces + Outfit inlined, layered marketing surface, light-locked). Interactive:
strategy tabs, log/linear, pre/after-tax toggle, crosshair tooltips.
Redeploys to the same URL from `output/mw_momentum_two_markets.html`
(source template `code/mw_note_template.html`).

## Files

| Path | What |
|---|---|
| `code/us_in_2019_2025.py` | Harness: India runs + US slicing + window metrics |
| `code/prep_artifact_data.py` | Weekly-resampled chart data → `artifact_data.json` |
| `code/add_tax_series.py` | After-tax curves from daily equity (25%, carryforward) |
| `code/after_tax_25.py` | After-tax summary table |
| `code/mw_note_template.html` | Artifact source template (fonts/data placeholders) |
| `output/summary_2019_2025.csv` | Pre-tax metrics, all 6 series |
| `output/yearly_2019_2025.csv` | Calendar-year returns |
| `output/after_tax_25_summary.csv` | Post-tax CAGR/final/drag |
| `output/equity_*_daily.csv` | India daily equity curves (avoid re-running) |
| `output/mw_momentum_two_markets.html` | Published artifact (self-contained) |

Note: code paths reference the session scratchpad; rerunning needs the path
constants at the top of each script pointed at this folder.
