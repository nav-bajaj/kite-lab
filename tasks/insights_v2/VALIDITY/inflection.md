# Validity study — inflection (insights_v2 C8.1)

- Cohort: `inflection`  ·  framing: momentum-positive
- Harness: tasks/insight_engine/pattern_validity_study.py (matched NSE 500 unconditional baseline, same sample dates)
- Sample dates: 165 (every 21 trading days)

## Forward-return statistics

| Horizon | N | Mean fwd % | Median | Baseline mean % | Excess (pp) | % positive | Baseline % pos | Direction lift (pp) |
|---|---|---|---|---|---|---|---|---|
| 5d | 4122 | +0.30% | -0.05% | +0.49% | -0.19 | 49% | 50% | -0.9 |
| 20d | 4124 | +1.70% | +0.48% | +1.97% | -0.27 | 52% | 54% | -1.7 |
| 60d | 4124 | +6.69% | +2.90% | +6.15% | +0.54 | 57% | 58% | -1.0 |
| 120d | 4124 | +12.49% | +5.97% | +12.27% | +0.21 | 59% | 60% | -0.7 |

## Verdict (VALIDITY_PROTOCOL.md tiers)

- **Tier: not-surfaced-as-prediction**
- Excess -0.27pp, direction lift -1.7pp at 20d (n=4124). Below the bar — surface the cohort as an OBSERVATION only (rank changed / is strong), with NO forward-return framing.

- Sign consistency across 5/20/60/120d: FLIPS (fragile — treat with caution) (5d -, 20d -, 60d +, 120d +).
