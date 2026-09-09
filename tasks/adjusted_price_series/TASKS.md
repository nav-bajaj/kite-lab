# Tasks — adjusted price series

Owners: 👤 founder · 🤖 agent
Risk tags: 🔴 irreversible if missed · 🟠 touches production pipeline · 🟢 additive

## Phase 0 — Freeze the pre-flip panel 🔴

Time-critical. Once the feed flips and a re-fetch runs, the un-adjusted
history cannot be recovered from the provider. Everything else in this
plan can wait; this cannot.

| # | Task | Owner |
|---|---|---|
| 0.1 | Tarball `nse500_data/` + `nse500_data_merged/` + `indices_data/` to the backup location used by `scripts/sync_data_backup.py`, named `pre_dividend_adjustment_<date>` | 🤖 |
| 0.2 | Record a manifest: per symbol, first date, last date, row count, and a SHA-256 of the date+OHLC columns | 🤖 |
| 0.3 | Verify the tarball restores into a scratch dir and the manifest re-derives identically | 🤖 |
| 0.4 | Confirm the frozen copy is on a medium independent of the Railway volume | 👤 |

Deliverable: `tasks/adjusted_price_series/manifest_pre_flip.csv` committed
to the repo (small — one row per symbol), tarball stored out of band.

### Status — local freeze done 2026-09-08

- `manifest_pre_flip.csv`: 1112 files hashed (534 `nse500_data`, 534
  `nse500_data_merged`, 44 `indices_data`).
- Tarball: `/Users/navdeep/Documents/stock_data/freezes/pre_dividend_adjustment_2026-09-08.tar.gz`
  (46 MB).
- Restore verified into a scratch dir: 1112/1112 hashes re-derived
  identically, 0 mismatches.

**Caveat — 0.4 is not yet satisfied.** The local panels end 2026-08-21
(`indices_data` 2026-08-28) while today is 2026-09-08. The live panel is
on the Railway volume; these repo-root copies lag it by roughly two and a
half weeks. What is frozen so far is a *floor*, not the definitive
snapshot.

Outstanding: pull `nse500_data` off the Railway volume and freeze that
too, before the feed flips. Until that is done the most recent ~13
trading days of un-adjusted history exist only on the volume.

## Phase 1 — Write the contract 🟢

The stance has to exist in one authoritative place before code can be
said to comply with it.

| # | Task | Owner |
|---|---|---|
| 1.1 | `docs/price_data_contract.md`: the panel is price-return / ex-dividend; adjusted for splits, bonus, rights, demergers; **not** for cash dividends. State the reasoning (dividends are a real cash flow to the investor, not reinvested) so a future reader does not "fix" it | 🤖 |
| 1.2 | Document the provenance table and segment boundaries per panel dir | 🤖 |
| 1.3 | Add an invariant row to CLAUDE.md under "Active invariants — do not break" pointing at the contract | 🤖 |
| 1.4 | Add a line to `docs/portfolios.md` and the client-facing copy: reported returns are ex-dividend, so realised investor returns are higher by the dividend yield | 👤 review, 🤖 draft |

Item 1.4 matters beyond bookkeeping — it turns a methodology constraint
into an honest, conservative claim, which is the right footing for a
SEBI-registered product.

## Phase 2 — Seal the leaks 🟠

| # | Task | Owner | Note |
|---|---|---|---|
| 2.1 | Replace the blanket `lookback_days = 15` with a bounded correction window that **only** accepts a rewritten row when it clears a split/bonus/rights test, not a dividend-sized one | 🤖 | `history_utils.py:270`. A dividend re-adjustment is a fraction of a percent; a split is a clean ratio. They are separable by magnitude, but the check must be explicit, not incidental |
| 2.2 | Replace `os.remove(csv_path)` with quarantine-and-alert: move the file aside, log loudly, do not silently re-fetch | 🤖 | `apply_corporate_actions.py:120,138` |
| 2.3 | Narrow `apply_corporate_actions.py` to events Kite does not handle (demergers today); re-base its raw-row threshold heuristics against a partly-adjusted feed | 🤖 | Guard against double-adjusting VEDL |
| 2.4 | Add a bootstrap guard: a full fetch into an empty panel dir requires an explicit `--bootstrap` flag and prints the adjustment-convention warning | 🤖 | Closes the volume-loss leak |
| 2.5 | Write a per-panel `.manifest.json` sidecar (provenance, convention, segment boundaries, frozen-history hash), updated on legitimate appends only | 🤖 | The artifact the enforcement in Phase 3 reads |

## Phase 3 — Enforcement 🟢

This is the "how do we make sure it is followed" half. Documentation alone
will not survive; each item below fails a run rather than advising one.

| # | Task | Owner |
|---|---|---|
| 3.1 | `tests/test_price_adjustment_contract.py` — golden-hash test asserting that history before the freeze cutoff is byte-identical to `manifest_pre_flip.csv` for a sampled set of symbols, including known dividend payers | 🤖 |
| 3.2 | Same test asserts no dividend-shaped discontinuity: scan for sub-1% single-day gaps clustered on known ex-dates | 🤖 |
| 3.3 | Wire the contract test into the pre-commit config and CI | 🤖 |
| 3.4 | Pipeline preflight gate in `run_daily_pipeline.py`, between the fetch steps and `update_all_portfolios.py`: verify each panel against its manifest and **abort the run** if frozen history moved | 🤖 |
| 3.5 | Surface panel adjustment state on the `/admin` freshness panel alongside the existing staleness flags | 🤖 |
| 3.6 | Add `nse500_data`, `history_utils.py` and `apply_corporate_actions.py` to the `security-reviewer` / review trigger list so panel-touching diffs get a second read | 🤖 |

The load-bearing item is **3.4**. A test in CI protects the repo; the
preflight gate protects the panel on the machine where the damage would
actually happen. If only one of these gets built, build 3.4.

## Phase 4 — 2011 depth ⏸

Blocked on the open decision in PLAN.md. Do not start.

## Sequencing

Phase 0 today, independent of everything else. Phase 1 before Phase 2 so
the code has a spec to comply with. Phase 2 before the feed flips. Phase 3
can land after the flip but should not lag it by more than a cycle.

Push freeze applies: no pushes 09:00–15:30 IST, pushes restart live
services.
