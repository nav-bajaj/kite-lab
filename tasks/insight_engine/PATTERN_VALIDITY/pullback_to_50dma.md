# Pattern validity study — pullback_to_50dma

- Sample window: 2012-01-01 to (last available − 180 days)
- Sample stride: every 21 trading days (165 sample dates)
- Entries per fire-date: top-25 by detector score

## Forward-return statistics

| Horizon | N fires | Mean fwd % | Median | Baseline mean % | Excess (pp) | % positive | Baseline % pos | Direction lift (pp) |
|---|---|---|---|---|---|---|---|---|
| 5d | 3747 | +0.46% | +0.07% | +0.49% | -0.03 | 51% | 50% | +0.5 |
| 20d | 3747 | +1.69% | +0.64% | +1.97% | -0.28 | 53% | 54% | -0.6 |
| 60d | 3747 | +5.54% | +3.35% | +6.15% | -0.61 | 58% | 58% | +0.6 |
| 120d | 3747 | +11.70% | +6.13% | +12.27% | -0.57 | 60% | 60% | +0.7 |

## Findings

- **FAILS** validity check at 20d: excess -0.28pp, direction lift -0.6pp. Do not surface with forward-return framing.