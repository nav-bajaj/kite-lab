# universe_membership

## Why

`data/static/*_universe.csv` are point-in-time snapshots applied
anachronistically: every daily pipeline run recomputes each portfolio from
2020 with *today's* universe. Editing the file therefore rewrites the
published track record (removals erase historical trades; additions
retroactively change past picks). The snapshots were last refreshed
2025-11-06 and NSE has reconstituted since (33 adds / 33 drops in NSE 500,
incl. GSPL/GUJGASLTD which froze after the Gujarat Gas merger).

Discovered via tasks/momentum_experiment (TradingView comparison,
2026-07-09): 4 of TradingView's top 6M performers were unpickable because
they were missing from the stale snapshot.

## Outcome

Effective-dated membership (`data/static/<universe>_membership.csv`,
append-only rows `symbol,effective_from,effective_to,note`) so that:

1. Refreshing the universe **never mutates pre-cutover history** — the daily
   full recompute stays byte-identical for published dates.
2. **Grandfather rule** (founder decision, 2026-07-14): a universe change
   never force-exits a live position. Membership gates *new entries* only;
   held ex-members compete for their rank slot and exit by portfolio logic.
   Once out they cannot re-enter. Non-held ex-members are invisible to the
   ranking (can't block entrants or displace holdings).
3. Fresh NSE lists (2026-07-14, incl. new nifty50 tracking) applied at
   cutover **2026-07-15** — must be >= the merge/deploy date; regenerate
   with `build_membership_files.py --cutover <date>` if the merge slips.

## Key decisions

- **Canonical symbols stay ours** (AKZOINDIA, LTIM) even where NSE renamed
  (JSWDULUX, LTM): price files, DB rows and published trades keep one
  continuous symbol; `scripts/history_utils.SYMBOL_ALIASES` bridges the
  fetch. Migrating to the new tickers would relabel historical trades and
  break byte-identity — deferred, revisit deliberately if ever.
- **Seeding**: all old-snapshot symbols get `effective_from=1900-01-01` so
  pre-cutover membership == old snapshot exactly (removals close at
  cutover, additions open at cutover). nifty50 (newly tracked, no snapshot)
  is seeded the same way — research backtests on it carry the usual
  survivorship caveat.
- **`*_universe.csv` are NOT regenerated yet.** 18 consumers read them
  (fetch, other runners, insights on Railway). They keep the old snapshot
  until each portfolio engine is migrated to membership; then the CSVs
  become derived current-members views. Interim effect: the daily fetch
  still covers removed-but-grandfathered names (good), and the 33 additions
  stay priceless/unscoreable until phase 2 (acceptable).

## Critical files

- `scripts/universe_membership.py` — loader + `make_membership_fn`.
- `scripts/_clean_engine.py` — `run_strategy(membership_fn=...)`:
  full-depth ranking precompute + `_relevant_ranking()` filter at the two
  rank-exit sites and the entrant draw. `None` = legacy path, structurally
  unchanged.
- `scripts/run_l6_v2_portfolio.py` — `--membership` (auto-on when
  `data/static/nse500_membership.csv` exists).
- `tests/test_universe_membership.py` — loader boundaries + end-to-end
  grandfather spec + legacy-equivalence.
- `build_membership_files.py` / `reconcile_universes.py` (this folder) —
  seed generator and NSE-list diff (ISIN-based rename detection).

## Verification gate

Production L6 config (`--prices-dir nse500_data --start 2020-01-01`), legacy
vs membership mode: `l6_equity.csv`, `l6_trades.csv`, `l6_exits.csv` and all
dashboard CSVs must be **byte-identical** while the price panel ends before
the cutover date. Verified 2026-07-14 (panel through 2026-07-13). Re-run
after any engine change.

## Phase 2 (not in this branch)

1. Migrate OM25 v3 / TL25 v3 / COMBO runners to membership (same
   `membership_fn` plumbing; COMBO composes the other two).
2. Regenerate `*_universe.csv` as current-members views; switch
   `fetch_nse500_history` to fetch all-ever members.
3. Fetch price history for the 33 NSE-500 additions (needs Kite session).
4. Upload refreshed static CSVs to the Railway volume (insights readers).
5. Wire nifty50 into product surfaces only if/when a portfolio uses it.
6. Post-cutover watch: AKUMS / INOXINDIA are held ex-members — confirm they
   grandfather correctly at the first live rebalance.
