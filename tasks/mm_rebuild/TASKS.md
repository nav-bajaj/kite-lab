# Tasks — MM rebuild

## §0 — pre-committed pass criteria — SIGNED by the founder 2026-09-10, frozen

Proposed as OM25's gate set after its 2026-09-10 rulings.

| # | Criterion | Value |
|---|---|---|
| G1 | IS Sharpe (rf 5%), 2010-2015, raw; deflated value reported alongside | ≥ 0.8 |
| G2 | OOS Sharpe, 2016-today | ≥ 0.9 |
| G3 | OOS sub-window Sharpe, each of 2016-19 / 2020-22 / 2023-26 | ≥ 0.6 |
| G4 | OOS maximum drawdown | no worse than −40% |
| G5 | Walk-forward Sharpe within this of the static OOS Sharpe | 0.2 |
| G6 | Parameter count, all-in | ≤ 10 |
| G7 | Turnover reported; a candidate that wins only on turnover-blind metrics is flagged | |
| G8 | CAGR, OOS and full span, pre-tax | ≥ 20% |

## §1 — score × lookback × universe 🤖
- [x] abs / vol-adjusted × 126 / 189 / 252 × Nifty 250 / NSE 500, monthly, 25 / 20, IS 2010-2015 — DONE 2026-09-10: vol-adjusted wins every cell; N250 12m 0.96, N500 6m 1.05

## §2 — mechanics 🤖 — DONE 2026-09-10: 25 / 20 / monthly holds on both universes (72 trials)
## §3 — filters and devices, one at a time 🤖👤
- [x] a. skip-month ADOPTED (21)  b. positive-only no-op  c. trailing stop not adopted (refit candidate)  d. ROC tilt loses everywhere  e. overlay not adopted — DONE 2026-09-10
## §4 — OOS and walk-forward, opened once 🤖👤 — OPENED 2026-09-10 on the founder's instruction
Candidates fixed before any 2016+ number: A Nifty 250 monthly 12m, B NSE 500 monthly 6m, both the §3 book (voladj, skip 21, 25/20, no stop). Walk-forward refit set per year: kind {abs, voladj, blend} × skip {0, 21} × buffer {10, 20} × stop {off, 20%} × capture-ratio top-quartile pre-filter {off, on}, trailing 5 and 10 years.

- [x] §4 OOS run 2026-09-10: both candidates fail G2/G3, pass G4/G5; Nifty 250 adaptive 10y 0.83. Founder decision pending.
