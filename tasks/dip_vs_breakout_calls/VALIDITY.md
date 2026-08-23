# Pattern validity study — dip_momentum (vs breakout_momentum control)

- Methodology: replica of tasks/insight_engine/pattern_validity_study.py
- Sample: 167 dates, stride 21, 2012-01-02 -> 2026-01-30; top-25 by momentum score per date
- Universe/baseline: NSE 500 minus 33 cliff-artifact symbols (tasks/dip_vs_breakout_calls/PLAN.md); baseline = all universe stocks, same dates

## dip_momentum

| Horizon | N fires | Mean fwd % | Median | Baseline mean % | Excess (pp) | % pos | Base % pos | Lift (pp) |
|---|---|---|---|---|---|---|---|---|
| 5d | 978 | +1.69 | +1.24 | +0.48 | +1.21 | 59% | 50% | +9.0 |
| 20d | 978 | +3.11 | +2.40 | +2.09 | +1.02 | 58% | 54% | +3.8 |
| 60d | 978 | +10.46 | +7.19 | +7.01 | +3.45 | 64% | 60% | +4.0 |
| 120d | 978 | +21.36 | +11.91 | +13.70 | +7.66 | 65% | 61% | +3.9 |

- Persistence (20d excess by sample half): H1 +1.49pp (n=376), H2 +0.74pp (n=602)
- Dates with >= 1 fire: 136/167

- check 1 sample n>=100: PASS
- check 2 excess >= +1.0pp @20d: PASS
- check 3 direction lift > 0 @20d: PASS
- check 4 sign consistency 5/20/60d: PASS
- check 6 persistence (both halves same sign): PASS

**Tier: VALIDATED (all checks pass; check 5 carries the standing survivorship caveat)**

## breakout_momentum

| Horizon | N fires | Mean fwd % | Median | Baseline mean % | Excess (pp) | % pos | Base % pos | Lift (pp) |
|---|---|---|---|---|---|---|---|---|
| 5d | 925 | +0.36 | -0.01 | +0.37 | -0.01 | 50% | 49% | +0.6 |
| 20d | 925 | +2.01 | +0.81 | +1.70 | +0.31 | 56% | 53% | +2.5 |
| 60d | 925 | +6.61 | +3.43 | +5.46 | +1.15 | 58% | 56% | +1.8 |
| 120d | 925 | +13.57 | +7.27 | +11.84 | +1.73 | 60% | 59% | +0.8 |

- Persistence (20d excess by sample half): H1 +0.39pp (n=405), H2 +0.26pp (n=520)
- Dates with >= 1 fire: 150/167

- check 1 sample n>=100: PASS
- check 2 excess >= +1.0pp @20d: FAIL
- check 3 direction lift > 0 @20d: PASS
- check 4 sign consistency 5/20/60d: FAIL
- check 6 persistence (both halves same sign): PASS

**Tier: NAMES-ONLY (lift positive, excess modest)**
