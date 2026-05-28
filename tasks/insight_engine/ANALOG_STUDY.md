# Analog finder — validity study and decision to retire

## TL;DR

**Decision: retire the analog-forward-return content from the subscriber-facing surface.**

The analog finder's forward-return predictions fail the basic actionability bar — the 20-day-horizon information coefficient is ~+0.04 (below the +0.05 "modest signal" threshold), and at the 20d and 60d horizons the directional accuracy of the prediction is actually NEGATIVE: when the analog predicted "up", Nifty went up LESS often than when the analog predicted "down."

The underlying problem is that Nifty's strong unconditional positive drift dominates the noise from a 20-neighbor sample, and the median of 20 mixed-regime neighbors systematically undershoots the unconditional drift. So the analog effectively forecasts a mean-reverted version of drift, while actual outcomes still benefit from drift — a built-in directional miss.

## Methodology

Walk-forward study:
- 345 sample dates (every 10th trading day from 2012-01-01 to 2025-11-28)
- At each sample, run the analog finder to get top-20 closest historical matches
- Take the median of the analogs' forward returns at 5/20/60/120 days
- Compare to the actual realized forward return at that date
- Repeat across the sample

Full script: [`tasks/insight_engine/analog_validity_study.py`](analog_validity_study.py).
Full output: [`tasks/insight_engine/ANALOG_STUDY_OUTPUT.txt`](ANALOG_STUDY_OUTPUT.txt).

## Headline numbers

| Horizon | IC | Direction lift vs unconditional |
|--------:|---:|---:|
|     5d  | +0.077 | +1.1pp |
|    **20d** | **+0.040** | **−2.9pp** |
|    **60d** | **+0.030** | **−3.4pp** |
|   120d  | +0.060 | +1.5pp |

At the 20d and 60d horizons — the headline windows for "next month" / "next quarter" framing — when the analog said up, Nifty was up only 62% / 66% of the time; when it said down, Nifty was up 69% / 75% of the time. The signal is anti-informative at those horizons.

Quartile analysis confirms the same picture:

| Horizon | Q1 (lowest analog pred) actual | Q4 (highest analog pred) actual | Q4 − Q1 |
|--------:|---:|---:|---:|
|     5d  | +0.46% | +1.01% |  +0.55pp |
|    20d  | +0.95% | +2.05% |  +1.11pp |
|    60d  | +2.84% | +3.75% |  +0.91pp |
|   120d  | +5.95% | +7.88% |  +1.93pp |

Even the BOTTOM-quartile-predicted setups had positive realized returns at every horizon — Nifty's drift wins regardless of what the analog said.

## Decomposition — drift dominates

| Horizon | Analog median | Unconditional mean | Difference |
|--------:|---:|---:|---:|
|     5d  | +0.19% | +0.40% |  −0.20pp |
|    20d  | +0.29% | +1.11% |  −0.82pp |
|    60d  | +1.46% | +3.17% |  −1.71pp |
|   120d  | +2.20% | +6.18% |  −3.98pp |

The analog median is systematically lower than the unconditional Nifty mean. The 20-neighbor sample washes out drift; the actual market doesn't. So the analog mean-reverts its prediction while reality keeps drifting.

## What gets retired

- **`/insights/analogs` page** — removed
- **"Analogs" tab in the layout nav** — removed
- **Analog paragraph in `commentary.py`** — removed
- **`🕰 Historical context` section in postclose/weekly templates** — removed

## What stays

- **`app/insights/analog_finder.py` module + its tests** — left in the code as a research artifact. The KNN match identification itself is sound; only the forward-return projection is being retired. Future research could reuse the match-finding component for different purposes (e.g., showing historical narratives at matched dates without claiming forward predictions).
- **Conditional-distribution engine** (`conditional_dist.py`) is unaffected — that engine works on hundreds-to-thousands of observations per bucket and the by-regime forward returns DO carry signal (STRESS regime → +3% 20d median with 72% positive vs ~65% unconditional). Different statistical regime, different result.

## What this teaches us about the broader content design

Three principles to apply going forward:

1. **Any forward-looking number must beat the unconditional baseline materially.** Quoting "+5% over the next month" is misleading if the unconditional 20d return is also +1%; the user perceives the +5% as prediction while it's actually drift.
2. **Sample size matters.** 20-neighbor predictions are too noisy to overcome drift. Aggregate bucketing (regime-level, 700+ observations) holds up; narrow KNN doesn't.
3. **Educational/contextual content can use the analog DATES** ("this resembles October 2018") without making forward-return claims. That framing is honest and informative.
