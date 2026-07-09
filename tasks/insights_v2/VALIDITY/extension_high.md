# Validity study — extension_high (insights_v2 C8.1)

- Cohort: `extension_high`  ·  framing: RISK (do these underperform?)
- Harness: tasks/insight_engine/pattern_validity_study.py (matched NSE 500 unconditional baseline, same sample dates)
- Sample dates: 165 (every 21 trading days)

## Forward-return statistics

| Horizon | N | Mean fwd % | Median | Baseline mean % | Excess (pp) | % positive | Baseline % pos | Direction lift (pp) |
|---|---|---|---|---|---|---|---|---|
| 5d | 2608 | +0.51% | -0.26% | +0.44% | +0.08 | 48% | 50% | -1.9 |
| 20d | 2608 | +2.77% | +0.87% | +1.98% | +0.79 | 54% | 54% | +0.5 |
| 60d | 2608 | +8.94% | +3.67% | +6.11% | +2.82 | 59% | 57% | +1.5 |
| 120d | 2609 | +15.91% | +6.94% | +12.11% | +3.80 | 61% | 59% | +1.5 |

## Verdict (VALIDITY_PROTOCOL.md tiers)

- **Tier: names-only / descriptive**
- 20d excess +0.79pp, direction lift +0.5pp (n=2608). No reliable forward underperformance — 'Extended' must stay a DESCRIPTIVE state label ('stretched vs its own history'), never a forward-return or 'will mean-revert' claim.

- Sign consistency across 5/20/60/120d: consistent (5d +, 20d +, 60d +, 120d +).
