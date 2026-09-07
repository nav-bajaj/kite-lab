# TASKS — minimum_capital_2026

Owners: 👤 founder · 🤖 agent

## Phase 1 — capital and SIP sizing

| # | item | owner | status |
|---|---|---|---|
| 1.1 | Universe price distribution + share granularity at a 1/25 position | 🤖 | done |
| 1.2 | Whole-share replication feasibility of all 4 current books, Rs 1L-20L | 🤖 | done |
| 1.3 | All-in cost drag by capital (DP per scrip-sale + STT/stamp/txn/GST) from per-year turnover | 🤖 | done |
| 1.4 | Capacity check — position vs p10-liquidity daily traded value | 🤖 | done |
| 1.5 | SIP deployability by amount; deployment rule (1-3 most underweight, not spread across 25) | 🤖 | done |
| 1.6 | Recommendation: Rs 5L min / Rs 10L recommended, Rs 10k floor / Rs 25k SIP | 🤖 | done |
| 1.7 | Decide publishing framing (operational constraint vs advice) — SEBI gate | 👤 | **open** |
| 1.8 | If a SIP calculator ships, choose the forward-return assumption deliberately | 👤 | **open** |

## Phase 2 — price-cap study

| # | item | owner | status | risk |
|---|---|---|---|---|
| 2.1 | Harness mirroring production OM25; validate uncapped arm against the live run | 🤖 | done — 0.008% | |
| 2.2 | OM25 cap sweep Rs 1k-12k | 🤖 | done | |
| 2.3 | Random-exclusion placebo, OM25 @ Rs 4,000, 40 seeds | 🤖 | done | |
| 2.4 | Placebo @ Rs 2,000 after the sweep looked non-monotonic | 🤖 | done — cap sits *outside* noise | |
| 2.5 | Price-decile study to explain 2.4 | 🤖 | done — low-price tilt, reversed 2024 + 2026 | |
| 2.6 | L6 v2 capped arm + placebo; validate baseline | 🤖 | done — 0.17pp | |
| 2.7 | COMBO capped arm + placebo; validate baseline | 🤖 | done — 0.03pp | |
| 2.8 | Forced-exit / grandfathering audit across all arms | 🤖 | done | ⚠️ COMBO cannot grandfather |
| 2.9 | Replication payoff of the capped books | 🤖 | done — Rs 10L -> ~Rs 2L | |
| 2.10 | **TL25 v3 capped arm + placebo** | 🤖 | **not started** | holds NEULANDLAB Rs 23,301, fast turnover — do not assume the result carries |
| 2.11 | **Decide: adopt the cap, and for which portfolios** | 👤 | **open** | |
| 2.12 | **COMBO forced-exit fix** if COMBO is capped | 🤖 | **open** | ⚠️ structural |
| 2.13 | Cap definition — tie to advertised ticket or universe percentile, not a frozen rupee figure | 👤 🤖 | **open** | fixed cap drifts: 94th pctile in 2021 -> 84th today |

## Deliberately not done

- **No production config or strategy code changed.** Every arm ran
  through standalone harnesses in this folder.
- **No re-tune.** Score, cadence, top-N, exit buffer, drawdown stop and
  slippage stayed at LOCKED/BASELINE values in all arms. The cap is an
  entry filter and nothing else.
- **No forward-return projections published.** The 12/18/25% rates run
  during the session were assumed, not derived, and are excluded from
  `RESULTS.md` on purpose.
- **Split-history reconstruction.** Would be needed to remove the
  back-adjustment bias (see STATE.md); we hold no split table, so the
  bias is documented by direction rather than corrected.
