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

## Phase 2 — remaining engines + data refresh (follow-up branch)

- [ ] 🤖 OM25 v3 / TL25 v3 / COMBO membership plumbing + same regression gate
- [ ] 🤖 Regenerate `*_universe.csv` as current-members views; fetch list = all-ever members
- [ ] 👤🤖 Fetch price history for 33 NSE-500 additions (Kite session)
- [ ] 🤖 Upload refreshed static CSVs to Railway volume (insights readers)
- [ ] 🤖 Post-cutover verification: AKUMS / INOXINDIA grandfather correctly at first live rebalance
