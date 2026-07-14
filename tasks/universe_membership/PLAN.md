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

## Phase 2 (2026-07-14, same day)

Shipped:

1. **OM25 v3 / TL25 v3 / COMBO / EOD-proposal adapter migrated** — same
   `--membership` resolution as L6 (`resolve_universe`), `membership_fn`
   plumbed into every `run_strategy` call. COMBO uses blend-level
   membership (`union_membership_fns`); per-component slot discipline is
   deliberately not date-masked (component scores must keep flowing for
   grandfathered holds), so a stock dropped from Nifty 250 but still in
   NSE 500 remains OM25-slot-eligible.
2. **Cross-sectional scores are date-masked via `candidate_fn`** ("ever a
   member on or before date"). The first regression run caught two leaks:
   OM25's score is doubly cross-sectional (equal-weight `market_ret` over
   panel columns + pct ranks) and TL25 pct-ranks momentum among eligible —
   an all-ever panel let future additions with price history (AIIL,
   LAURUSLABS, MCX, RADICO had local data) shift pre-cutover ranks and
   rewrite 2021+ picks. L6's z-score is monotone, so it needs no mask.
3. **Component slot-cuts need the mask even when the score is monotone.**
   The post-fetch check (new symbols' price history actually in the panel)
   caught a third leak: L6's z-score is monotone so standalone L6 needs no
   candidate mask, but COMBO's `make_combo_score_fn` truncates each
   component to its top-12 — CEMPRO (listed 2020, added to NSE 500
   2026-07) cracked the L6 component's 2022 top-12 and changed published
   COMBO picks. `make_momentum_score` now takes `candidate_fn` and every
   caller passes it. Rule of thumb: any hard cut inside a score fn
   (top-n_per, eligibility filters) needs point-in-time candidates, not
   just the engine-level entry mask.
4. **Engine tie-order fix**: `nlargest` at different depths orders tied
   scores differently, and entrant order feeds the leftover-cash
   redistribution pass (caught as a TL25 one-row swap). The ranking head
   is now computed with the exact legacy `nlargest(top_n+exit_buffer)`
   call; deeper ranks are appended only when membership is active.
5. **Legacy admin variants frozen** on
   `data/static/legacy_snapshot_2025-11-06/` — the legacy engine has no
   membership support, so it must not read the now-moving universe views.
6. **`*_universe.csv` regenerated as current-members views** (canonical
   symbols: the JSW Dulux row carries AKZOINDIA, LTM carries LTIM) via
   `regenerate_universe_csvs.py`. `fetch_nse500_history` now fetches
   ALL-EVER members (533) so grandfathered holds and history keep pricing.
7. Regression gate re-run in strict order (legacy baselines on the old
   snapshot -> regenerate -> membership runs): all four portfolios
   byte-identical across equity/trades/exits/dashboard CSVs.

Deployment notes (2026-07-15 cutover):

- Railway's 16:30 scheduler runs the repo's `run_daily_pipeline.py`; the
  merged fetch change provisions the 33 new symbols' history on the volume
  automatically at the next run. Static CSVs ship with the deploy (they're
  committed). Confirm Railway redeployed from main before tomorrow 16:00
  (the EOD-proposal producer must use membership code too).
- `nse500_data_merged` (insights breadth long-history panel, uploaded to
  the volume manually) lacks the 33 additions until its next re-upload —
  analytics-only degradation, tracked as follow-up.
- Post-cutover watch: INOXINDIA (Core Momentum) and AKUMS (legacy signals)
  are ex-members — confirm grandfathering at the first live rebalance
  (Thu 2026-07-16 signal -> Fri 2026-07-17 execution).
- nifty50 tracked (membership + universe files); product wiring deferred
  until a portfolio uses it.
