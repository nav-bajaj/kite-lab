# Pattern validity study — multi_year_breakout

- Sample window: 2012-01-01 to (last available − 180 days)
- Sample stride: every 21 trading days (165 sample dates)
- Entries per fire-date: top-25 by detector score

## Forward-return statistics

| Horizon | N fires | Mean fwd % | Median | Baseline mean % | Excess (pp) | % positive | Baseline % pos | Direction lift (pp) |
|---|---|---|---|---|---|---|---|---|
| 5d | 1783 | +0.96% | +0.15% | +0.44% | +0.53 | 52% | 50% | +2.0 |
| 20d | 1783 | +3.26% | +1.52% | +1.85% | +1.41 | 57% | 53% | +3.5 |
| 60d | 1782 | +10.35% | +3.94% | +6.14% | +4.20 | 60% | 57% | +2.8 |
| 120d | 1782 | +17.83% | +7.38% | +11.87% | +5.96 | 62% | 59% | +3.1 |

## Findings

- **PASSES** validity check at 20d: excess +1.41pp AND direction lift +3.5pp. Promote to live watchlist with forward-return narrative.