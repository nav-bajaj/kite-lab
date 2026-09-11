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

## Decisions (founder, 2026-09-11)

1. **Website line-up during the parallel run:** keep legacy **L6 v2** and **OM25 v3** visible
   alongside MM and OM25 v4; remove TL25 v3, COMBO Defensive and the three admin-only legacy
   variants from the site (their pipeline runs and DB rows are untouched; universe IDs are
   never deleted). The legacy two stay on their current data path until the founder retires
   them — they are the day-to-day comparison.
2. **Bhavcopy refresh runs at 19:30 IST**, after NSE publishes and before the nightly backup:
   bhavcopy → CA table → QA reconcile → store manifest → backup. The 16:30 pipeline keeps
   building the books from Kite; the 19:30 job is the audit and the record. A QA failure at
   19:30 flags the next morning's run rather than blocking the evening's.
3. **GDF is paid for three months** (to ~2026-12): use it while it lasts — see the GDF sprint
   below — then let it lapse unless the sprint finds it fills a gap nothing else does.
4. Retention: bhavcopy raw kept in the store (git-ignored, backed up nightly).

## GDF sprint (time-boxed to the subscription) 🤖

- [ ] Pull `GetHistory` for **every** all-ever member of the four tracked indices (not only the
      37 delisted) for GDF's floor (2009) → today, into `prices/gdf/`; keep the raw as served.
- [ ] Cross-check against Kite (adjusted) and bhavcopy × CA (raw) day by day; log every
      symbol-day where the three disagree beyond tolerance to `qa/gdf_discrepancies.csv`, with
      the likely cause (missed CA, wrong factor, delisting date, rename).
- [ ] Fill what only GDF has: names that delisted before Kite's coverage and after 2009, and
      any symbol-days the bhavcopy archive is missing (the spine noted gaps).
- [ ] Ask GDF for what else they serve that we lack — historical index constituents with
      weights, sector classifications by date, delisting reasons — and pull any that would
      replace a Wayback-derived file (the sector history, the membership events).
- [ ] Write `tasks/market_data_spine/GDF_AUDIT.md` with coverage and discrepancy counts;
      decide keep/drop on that evidence before the subscription ends.
