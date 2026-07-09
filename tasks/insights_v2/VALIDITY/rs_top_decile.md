# Validity study — rs_top_decile (insights_v2 C8.1)

- Cohort: `rs_top_decile`  ·  framing: momentum-positive
- Harness: tasks/insight_engine/pattern_validity_study.py (matched NSE 500 unconditional baseline, same sample dates)
- Sample dates: 165 (every 21 trading days)

## Forward-return statistics

| Horizon | N | Mean fwd % | Median | Baseline mean % | Excess (pp) | % positive | Baseline % pos | Direction lift (pp) |
|---|---|---|---|---|---|---|---|---|
| 5d | 4124 | +0.73% | +0.03% | +0.49% | +0.24 | 50% | 50% | +0.1 |
| 20d | 4123 | +3.15% | +1.54% | +1.97% | +1.19 | 56% | 54% | +2.3 |
| 60d | 4122 | +10.08% | +5.37% | +6.15% | +3.93 | 61% | 58% | +3.7 |
| 120d | 4122 | +20.72% | +10.87% | +12.27% | +8.44 | 65% | 60% | +5.0 |

## Verdict (VALIDITY_PROTOCOL.md tiers)

- **Tier: validated**
- Excess +1.19pp AND direction lift +2.3pp at 20d (n=4123). Meets the Validated tier — the cohort MAY carry a forward-return narrative with these figures disclosed.

- Sign consistency across 5/20/60/120d: consistent (5d +, 20d +, 60d +, 120d +).
