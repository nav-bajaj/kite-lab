# Tasks

Owners: 👤 founder · 🤖 agent.

## §0 — pre-committed pass criteria — SIGNED 2026-09-10, frozen

| # | Criterion | Value |
|---|---|---|
| G1 | IS Sharpe (rf 5%), 2006-2015, after deflation for candidates tried | ≥ 0.9 |
| G2 | OOS Sharpe, 2016-today | ≥ 0.9 |
| G3 | OOS sub-window Sharpe, each of 2016-19 / 2020-22 / 2023-26 | ≥ 0.6 |
| G4 | OOS maximum drawdown | no worse than −40% |
| G5 | Walk-forward Sharpe within this of the static OOS Sharpe | 0.2 |
| G6 | Parameter count, all-in (score weights, regime, N, buffer, cadence, lookback, overlay ROC N, confirm, bear exposure, redeploy) | ≤ 10 (raised from 8 by the founder 2026-09-10 to admit the overlay; counts everything searched) |
| G7 | Turnover reported; no gate, but a candidate that wins only on turnover-blind metrics is flagged |  |
| G8 | Minimum return (added by the founder 2026-09-10: "20-25% range"). Recorded at the floor of the range pending the founder's number. CAGR over OOS 2016-today and over 2006-today; IS CAGR reported against the benchmark (10.9% price return 2006-2015) but not gated, because a 2008-in-window decade floor is an index-relative question | ≥ 20% |

## §1 — retrieve the ROC regime test 🤖

- [x] Located: `tasks/portfolio_risk_2026/` on `beta_gtm_mvp`; definition
      and result recorded in BRIEF.md (sign of N-session ROC of NIFTY 100,
      confirm-days hysteresis, best cell 31/3 on the biased universe)
- [x] 👤 ROC grid N ∈ {15, 21, 31, 42} × confirm ∈ {2, 3, 5}
- [x] 👤 Exposure overlay: later, out of scope here
- [x] 👤 Market for up/down days: (b) equal-weight signal-date members over the window

## §2 — harness 🤖

- [ ] `lib/score.py`: UC, CR, blend — per the OM25 v3 construction minus the
      50-up/50-down rule; positive-return filter kept as a switch
- [ ] `lib/regime.py`: ROC of the regime index with confirmation hysteresis;
      "one regime" = the panel is ignored
- [ ] `lib/run.py`: one candidate → equity/trades/exits on the master store,
      via `_clean_engine.run_strategy`, no weight cap, no stops
- [ ] `lib/windows.py`: IS / OOS / sub-windows / walk-forward evaluator,
      pass-criteria check, candidate counter for deflation
- [ ] Smoke test: the old OM25 v3 configuration reproduces
      market_data_spine's Phase 6 number when its constraints are re-enabled

## §3 — build, IS only 🤖

- [ ] 3a score × universe (6 runs)
- [ ] 3b regime: one vs two, ROC parameters (small grid) on 3a's winner
- [ ] 3c top-N / exit buffer / cadence grid
- [ ] 3d lookback / min_obs
- [ ] 3e exposure overlay: ROC grid × bear exposure {75, 50, 25, 0} × return filter, both universes, ≤25 names
- [ ] Deflate; record every run in RESULTS.md with its number

## §4 — OOS and walk-forward, opened once 🤖👤

- [ ] Surviving configuration per universe → OOS, sub-windows, walk-forward
- [ ] 👤 Decide the universe and whether the book ships

## Done

- [x] Task opened with the founder's constraints verbatim (BRIEF.md)
