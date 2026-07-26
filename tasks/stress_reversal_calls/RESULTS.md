# Stress-regime reversal calls — RESULTS

Ran 2026-07-24. Design pre-registered in PLAN.md before any run.
Run dir: `runs_20260724_151942/` (+ exploratory threshold check).

## Verdict: REJECTED — both legs fail

| arm (trigger >= 70) | calls/yr | win% | mean call | CAGR | Sharpe |
|---|---|---|---|---|---|
| time60 | 98.5 | 53.6 | +3.2% | 6.9% | 0.13 |
| time120 | 55.4 | 55.1 | +7.2% | 8.7% | 0.23 |
| rec50 | 174.1 | 65.1 | +1.2% | 5.7% | 0.05 |

All arms underperform NIFTY buy-and-hold (~10.5% CAGR same window).

Validity dry run (both benchmarks, 20/60/120d):

- **Selection excess ~ zero**: -0.6 to +1.0pp vs the same-date universe
  mean, sign-inconsistent across horizons. Quality-within-panic picks do
  not beat the generic panic bounce.
- **Timing excess negative everywhere**: -1.1 to -5.1pp vs the all-days
  baseline; direction lift negative. Stock-level panic entries LOSE to
  just buying on any day.
- **Exploratory threshold >= 85** (322 trigger days, labeled post-hoc):
  same picture (selection +0.1 to +0.5pp; timing -1.3 to -4.3pp). The
  failure is the idea, not the calibration.

## Why it fails (mechanism)

Stress episodes cluster at the START of drawdowns and persist through
them (2011, 2018, 2022, 2025 were multi-month grinds, not V-bottoms).
Entries triggered by stress systematically forgo the bull-market drift
that dominates the all-days baseline. The production conditional_dist
"buy panic" claim is an INDEX-level, distribution-shaped statement and
remains valid as market commentary; it does not convert into a
stock-level call product net of baseline drift. Consistent with the
insight_engine finding that pullback_to_50dma was not surfaceable.

## Decision

No product. No further calibration search (that would be N-shopping a
dead idea). The diversification path runs through fundamentals instead:
PEAD / multi-factor calls once a fundamentals feed exists (founder
sourcing next). This folder closes as a clean pre-registered negative.

## Reproducibility

```
source .venv/bin/activate
python tasks/stress_reversal_calls/stress_reversal_experiment.py
```

Inputs: nse500_data_merged/, indices_data_historical/{INDIA_VIX,NIFTY_50}.csv.
Caveats: current-snapshot universe (survivorship); offline stress replica
(production weights, rolling-252d percentiles, min_periods 120).
