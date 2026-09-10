# Tasks

Owners: 👤 founder · 🤖 agent.

## §0 — pre-committed pass criteria 👤 (UNSIGNED — no search run until signed)

Proposed 2026-09-10. Edit any number; once signed, frozen.

| # | Criterion | Value |
|---|---|---|
| G1 | IS Sharpe (rf 5%), 2006-2015, after deflation for candidates tried | ≥ 0.9 |
| G2 | OOS Sharpe, 2016-today | ≥ 0.9 |
| G3 | OOS sub-window Sharpe, each of 2016-19 / 2020-22 / 2023-26 | ≥ 0.6 |
| G4 | OOS maximum drawdown | no worse than −40% |
| G5 | Walk-forward Sharpe within this of the static OOS Sharpe | 0.2 |
| G6 | Parameter count, all-in (score weights, regime, N, buffer, cadence, lookback) | ≤ 8 |
| G7 | Turnover reported; no gate, but a candidate that wins only on turnover-blind metrics is flagged |  |

## §1 — retrieve the ROC regime test 🤖

- [ ] Locate the prior thread's ROC regime test: index, lookback, threshold,
      hysteresis, comparison, result (agent dispatched 2026-09-10)
- [ ] Record the definition in BRIEF.md; if the definition is ambiguous,
      👤 confirm before use

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
- [ ] Deflate; record every run in RESULTS.md with its number

## §4 — OOS and walk-forward, opened once 🤖👤

- [ ] Surviving configuration per universe → OOS, sub-windows, walk-forward
- [ ] 👤 Decide the universe and whether the book ships

## Done

- [x] Task opened with the founder's constraints verbatim (BRIEF.md)
