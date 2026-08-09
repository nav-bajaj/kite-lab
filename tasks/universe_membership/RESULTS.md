# universe_membership — RESULTS

**Status: shipped.** Opened 2026-07-14, cutover 2026-07-15, live behavior
verified 2026-07-21 after the first post-cutover rebalance. All of PLAN.md
Phase 1 + Phase 2 shipped same-day; nothing was descoped.

## What shipped

- Effective-dated membership files for nse500 / nifty250 / nifty100 /
  nifty50 (newly tracked), seeded so pre-cutover membership equals the old
  2025-11-06 snapshots exactly. The 2026-07-14 NSE lists applied from
  cutover 2026-07-15 (nse500: 33 adds / 33 drops incl. the frozen
  GSPL/GUJGASLTD; nifty250: 12/12; nifty100: 6/6).
- Grandfather rule in `run_strategy(membership_fn=...)`: membership gates
  NEW entries only; held ex-members compete for their rank slot and exit by
  portfolio logic; once out they cannot re-enter; non-held ex-members are
  invisible to the ranking.
- All four production portfolios (L6 v2, OM25 v3, TL25 v3, COMBO) and the
  EOD-proposal adapter migrated; cross-sectional scores and component
  slot-cuts date-masked via `make_candidate_fn`; legacy admin variants
  pinned to `data/static/legacy_snapshot_2025-11-06/`; `*_universe.csv`
  regenerated as derived current-members views; fetch switched to ALL-EVER
  members; `sync_insights_panels` seeds new members into the merged panel.
- NSE renames (AKZOINDIA→JSWDULUX, LTIM→LTM) kept under our canonical
  symbols via fetch aliases — historical trade labels untouched.

## Commits (all merged to main with --no-ff)

| What | Commits |
|---|---|
| Phase 1 (membership + grandfather + L6) | `1f23cd0`, merge `e7d95b7` |
| Phase 2 (all engines, EOD adapter, views, legacy freeze) | `7566e5a`, merge `3fcb820` |
| COMBO component-slot candidate mask | `97c2af5` |
| Merged-panel seeding for new members | `e8d4cd6` |
| (Related) admin job-timestamp fix found during verification | `96528b9`, merge `04ceaee` |

Branches: `universe-membership` (Phase 1), `universe-membership-p2`
(Phase 2), `fix-job-timestamps` — all merged and pushed 2026-07-14/15.

## Verification log

- **Spec tests:** 6 in `tests/test_universe_membership.py` (loader
  boundaries, end-to-end grandfather scenario, legacy-equivalence,
  candidate-fn semantics) + EOD adapter parity suite; kite-api suite 834
  passed after the timestamp fix.
- **Byte-identity regression (2026-07-14, run three times):** legacy
  baselines on the frozen snapshot -> regenerate views -> membership runs;
  final pass on the post-fetch panel (new symbols' price history present):
  equity/trades/exits/dashboard CSVs identical for all four portfolios.
  The gate caught three real bugs pre-production — OM25/TL25 cross-
  sectional rank pollution by future listings, an `nlargest` tie-order
  regression, and COMBO's component top-12 cut admitting CEMPRO into 2022
  history. All fixed; see PLAN.md items 2–4.
- **Production rollout (2026-07-14 22:17 IST manual pipeline run):** Railway
  logs showed the 533-symbol all-ever fetch, `membership: ...csv` lines for
  all three engines, legacy runners on the pinned snapshot, "33 new symbols
  seeded into merged from live", and a clean DB sync with the most recent
  trade unchanged (2026-07-13) — i.e. the rebuild under new code left the
  published record untouched.
- **First live rebalance (Thu 2026-07-16 signal -> Fri 2026-07-17 exec),
  verified 2026-07-21:**
  - Entries on merit: CPPLUS, CEMPRO, ACUTAAS, EMMVEE (+BHEL) — the four
    names whose absence triggered tasks/momentum_experiment.
  - Grandfathering: INOXINDIA (entered 2026-06-12) and AKUMS (entered
    2026-07-10, last pre-cutover rebalance) NOT force-sold; both still held
    and competing on rank. All 2026-07-17 exits were ordinary `rank` exits
    of current members.
  - No post-cutover BUY of any removed symbol (no re-entry).
  - History stability: trade history through 2026-07-16 identical between
    the 2026-07-17 and 2026-07-21 daily recomputes (2,279 trades).
  - OM25/COMBO: no post-cutover exits; TL25: 3 routine `rank_weekly` exits
    of current members. Legacy frozen variant still ranks AKUMS (#23 on
    2026-07-16) — pinned universe intact.

## Deferred / follow-ups (tracked, non-blocking)

1. Freshness monitor treats closed-membership symbols (GSPL, GUJGASLTD,
   RELINFRA) as lagging — teach it to expect them; until then the NSE500
   panel row reads "critical" in normal conditions.
2. `tasks/momentum_experiment/RESULTS.md` still overstates the vol
   adjustment (the 0.05 floor is daily-vol units and swallows it) — pending
   correction.
3. Phase 3: append-only portfolio ledger (immutable weekly runs, explicit
   corporate-action + restatement events) — design discussed 2026-07-14,
   awaiting go-ahead; would close the remaining history-mutability class
   (engine-code changes and price revisions can still restate).
4. Next NSE reconstitution: follow the refresh procedure in PLAN.md /
   memory — new lists in, reconcile, append membership rows with the new
   cutover, regenerate views, byte-identity gate must pass.
