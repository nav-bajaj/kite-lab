# Pattern validity study — sustained_uptrend

- Sample window: 2012-01-01 to (last available − 180 days)
- Sample stride: every 21 trading days (165 sample dates)
- Entries per fire-date: top-25 by detector score

## Forward-return statistics

| Horizon | N fires | Mean fwd % | Median | Baseline mean % | Excess (pp) | % positive | Baseline % pos | Direction lift (pp) |
|---|---|---|---|---|---|---|---|---|
| 5d | 2979 | +0.70% | +0.28% | +0.45% | +0.25 | 53% | 50% | +3.4 |
| 20d | 2979 | +2.48% | +1.58% | +1.73% | +0.75 | 58% | 53% | +4.9 |
| 60d | 2979 | +7.40% | +4.77% | +5.64% | +1.76 | 63% | 57% | +6.1 |
| 120d | 2979 | +13.75% | +8.52% | +11.63% | +2.12 | 65% | 59% | +6.3 |

## Findings

- **MARGINAL** at 20d: excess +0.75pp, direction lift +4.9pp. Publish as names-only (no fwd-return claims).