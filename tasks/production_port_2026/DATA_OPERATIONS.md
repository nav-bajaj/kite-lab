# Data operations — sources, cadence, universe upkeep

State on 2026-09-11. Decisions from market_data_spine (D-1 revised, D-11, D-12) carried
forward; open items marked 👤.

## Sources and what each is for

| Source | Use | Cadence | Notes |
|---|---|---|---|
| **Kite Connect** day candles (adjusted) | the price basis for every listed symbol, 2000 → today (`prices/kite/`); the `adjusted` view the engines read | nightly after close (existing pipeline slot ~16:30 IST) plus the intraday quotes the dashboard already uses | back-adjusted by Kite on every corporate action, so a symbol's whole history can move on an ex-date — the store is snapshot-versioned for that reason; all-ever members must be fetched, never only current ones |
| **NSE bhavcopy** (daily archive, UDiFF format from 2024) | raw closes, volume, ISIN and company name per symbol per day; the audit trail that Kite's adjustment is checked against; the only source for names Kite no longer lists | nightly, after NSE publishes (~18:00-19:00 IST) | direct download with UA + landing-page cookie works (spine); `tasks/market_data_spine/lib/export_bhavcopy_series.py` builds per-symbol series; a manifest tracks what is loaded |
| **NSE corporate-actions API** | the CA table (`data/master/corporate_actions.csv`): splits, bonus, rights, demergers | nightly, look-ahead 30 days | raw × factors must reproduce Kite's adjusted series within tolerance (QA); dividends recorded but not applied (price-return basis, D-12) |
| **GDF** (`data_pipeline/gdf_client.py`) | second opinion on delisted names' history; floors at 2009 | on demand at reconstitution or when a name delists | never the basis; cross-check only |
| **NSE index constituent lists** (`ind_nifty500list.csv` etc.) + the inclusion/exclusion feed | membership events for the point-in-time files; sector labels | at each reconstitution (March and September) and for mid-cycle replacements | current lists carry the 21-sector Industry column; historical labels in `tasks/mm_rebuild/sector/` |
| **Zerodha sector file** | fallback sector for names NSE has not labelled | with the reconstitution refresh | `scripts/fetch_zerodha_sectors.py` |

**Principle:** Kite is the basis, the bhavcopy is the record, GDF is the tie-break. A day is
accepted only when the bhavcopy close × CA factors reconciles with Kite's adjusted close for
every held name (tolerance from the spine QA), otherwise the pipeline stops before the
portfolio step and pages.

## Nightly sequence (target)

1. Kite: instruments cache → day candles for all-ever members of every tracked index and the
   benchmark indices (incremental, with a 15-session refetch window for late adjustments).
2. Bhavcopy of the day → per-symbol raw series; ISIN/name map updated; renames detected
   (`symbol_renames_detected.csv`).
3. CA table refresh; recompute adjusted view for symbols with a new event; QA reconcile.
4. Membership: apply any dated event effective today (append-only rows).
5. Portfolios (legacy four + MM + OM25) → DB sync → insight panels → backup.
6. Freshness monitor: `/api/freshness` gains the store's last accepted date.

## Keeping the universe current

- **Reconstitutions** (NSE, ~March and ~September, effective the last Friday): drop the new
  lists into `tasks/universe_membership/data/nse_lists_<date>/`, run `reconcile_universes.py`
  (ISIN-based rename detection), append rows with `build_membership_files.py --cutover
  <effective date>`, regenerate views, run the byte-identity regression on the legacy books,
  refresh sector labels and `zerodha_sectors.csv`, fetch prices for new symbols. Procedure is
  the one shipped 2026-07-14; it moves to a documented runbook under `docs/`.
- **Mid-cycle replacements** (M&A, delisting, suspension): hand-written append-only rows with
  `[from, to)` semantics and a note; `members_asof` must stay exactly 500 / 250 / 100 / 50.
- **Renames**: canonical symbol kept, alias in `SYMBOL_ALIASES`; the bhavcopy ISIN map is the
  authority for "same company".
- **Delistings**: last traded price carried (D-9); the bhavcopy series is the record after
  Kite drops the symbol.
- **Backfill**: the reconstruction (`tasks/index_reconstruction`) is the history; it is not
  re-run — new events append.

## Open decisions 👤

1. Whether the legacy four books switch to the point-in-time membership at cut-over (their
   track restates from that date only) or stay pinned until retired.
2. Where the nightly store refresh runs: the Railway pipeline slot (16:30 IST) is before the
   bhavcopy is published; either a second slot (~19:30 IST) for bhavcopy + QA, or the
   portfolio step waits for it.
3. Retention: bhavcopy raw is ~600 MB for 2005 → today; keep in the store (git-ignored, backed
   up nightly) — confirm.
4. GDF: keep the subscription for delisted cross-checks only, or drop after the store is
   complete.
