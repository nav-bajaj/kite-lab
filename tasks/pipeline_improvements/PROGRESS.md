# Daily Pipeline Improvements — Progress Log

## 2026-05-15 — Phase 0 kickoff

- Branched off main as `pipeline-improvements`.
- Ran three-agent audit (pipeline orchestration, portfolio scripts, data
  topology). Findings consolidated in PLAN.md.
- Confirmed via grep that `scripts/build_momentum_signals.py` step is
  effectively orphaned within the daily pipeline — its output
  `data/momentum/top25_signals.csv` (last modified 2026-05-12) has no
  pipeline-downstream readers, only ad-hoc research tools.
- Verified actual portfolio output directory conventions:
  - `data/om25_v3_portfolios/om25_v3_portfolio_<ts>/`
    (legacy runs still in `data/om25/v3/runs/<ts>/`)
  - `data/tl25_v3_portfolios/tl25_v3_portfolio_<ts>/`
  - `data/l6_v2_portfolios/l6_v2_portfolio_<ts>/`
  - `data/combo_defensive_portfolios/combo_defensive_portfolio_<ts>/`
- Verified `scripts/sync_to_database.py` and `kite-api/app/services/sync_service.py`
  sync these 7 universes:
  `nse500, nifty100, nifty250, om25_v3, tl25_v3, l6_v2, combo_defensive`.
- Updated CLAUDE.md: status header, daily pipeline comment, OM25 v3 location,
  added L6 v2 + COMBO Defensive sections, updated footer.
- Created `tasks/pipeline_improvements/PLAN.md`.

### Open questions awaiting user decision
- Remove `build_momentum_signals.py` step from daily pipeline?
- Migrate `run_final_momentum_portfolio.py` to `_clean_engine` in Phase 3?

- Built `scripts/snapshot_pipeline_outputs.py` (deterministic SHA256 over
  normalized DataFrames, 10dp float rounding; ignores `captured_at` /
  `run_mtime` / `size_bytes` in diffs).
- Captured **Phase 0 baseline** at
  `tasks/pipeline_improvements/golden_master_20260515_151808.json`.
  Row counts:
  - om25_v3: equity=1326, trades=868, holdings=25
  - tl25_v3: equity=1354, trades=1737, holdings=21
  - l6_v2: equity=1449, trades=2207, holdings=24
  - combo_defensive: equity=1443, trades=1925, holdings=5
  - legacy signals: 7650 rows
- Verified **idempotency** by re-snapshotting against the latest run dirs
  and diffing — zero content differences (only the optional `label` tag
  diverged on the second run, as expected).

### Phase 0 complete

All three Phase 0 deliverables done. Ready to begin Phase 1 (correctness)
pending user confirm on the two open items in PLAN.md (orphan-step removal,
legacy L6 script migration scope).

### Next
- Get user decision on the two open items.
- Phase 1.1: build `scripts/metrics_common.py` and unify Sharpe definitions.
- Phase 1.2: transactional safety on `sync_to_database.py`.
- Phase 1.3: token-expiry preflight in orchestrator.
- Re-snapshot at Validation Gate 1.
