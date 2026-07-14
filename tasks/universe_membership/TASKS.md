# universe_membership — tasks

## Phase 1 — membership infrastructure + L6 cutover (this branch)

- [x] 🤖 Ingest 2026-07-14 NSE lists (50/100/250/500) into `data/nse_lists_2026-07-14/`
- [x] 🤖 Reconciliation diff vs old snapshots (`reconcile_universes.py`) — ISIN rename detection, price-file coverage
- [x] 👤 Founder decisions: grandfather rule (no force-exits on universe change); keep canonical symbols for NSE renames
- [x] 🤖 `scripts/universe_membership.py` loader + membership_fn
- [x] 🤖 `run_strategy(membership_fn=...)` grandfather logic in `_clean_engine.py` ⚠️ touches all 4 portfolio engines' shared code — legacy path must stay structurally identical
- [x] 🤖 L6 runner `--membership` plumbing (auto-on when file exists)
- [x] 🤖 Spec tests (`tests/test_universe_membership.py`, 5 tests)
- [x] 🤖 Seed `data/static/*_membership.csv` (cutover 2026-07-15) ⚠️ regenerate if merge slips past cutover
- [x] 🤖 Byte-identical regression, legacy vs membership (equity/trades/exits/dashboard CSVs)
- [ ] 👤 Merge to main before 2026-07-15 pipeline run

## Phase 2 — remaining engines + data refresh (universe-membership-p2, 2026-07-14)

- [x] 🤖 OM25 v3 / TL25 v3 / COMBO membership plumbing + same regression gate
- [x] 🤖 EOD-proposal adapter (`data_pipeline/eod_proposal.py`) membership parity ⚠️ client-facing proposed orders
- [x] 🤖 `candidate_fn` date-masking for cross-sectional scores (OM25 market_ret + pct ranks, TL25 momentum rank) — leak caught by regression
- [x] 🤖 Engine tie-order fix (legacy `nlargest` head preserved exactly)
- [x] 🤖 Legacy admin variants pinned to `legacy_snapshot_2025-11-06/`
- [x] 🤖 Regenerate `*_universe.csv` as current-members views; fetch list = all-ever members
- [x] 🤖 Fetch price history for 33 NSE-500 additions (local; Railway volume self-provisions at next 16:30 run)
- [x] 🤖 Static CSVs ship via git deploy — no manual Railway upload needed
- [ ] 🤖 Re-upload `nse500_data_merged` insights panel with the 33 additions (analytics-only, non-blocking)
- [ ] 👤 Confirm Railway redeployed from main before 2026-07-15 16:00 IST
- [ ] 🤖 Post-cutover verification: INOXINDIA / AKUMS grandfather correctly at first live rebalance (Thu 07-16 signal)
