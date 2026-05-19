# Sector Analytics

## Overview

Track Nifty sectoral indices and their constituents, so we can study:

1. **Sector vs market** — how each sector (Bank, IT, Auto, Pharma, …) is
   performing relative to a benchmark (Nifty 100 / Nifty 500) over multiple
   time windows.
2. **Stock vs sector** — which stocks inside a sector are leading or lagging
   their sector index.
3. **Portfolio overlay** — where our momentum portfolio sits across sectors,
   and whether its holdings are outperforming their sector peers.

Data source for constituents: [niftyindices.com sectoral indices](https://www.niftyindices.com/indices/equity/sectoral-indices).
Each sector page links to a constituent-list CSV (Company Name, Industry,
Symbol, Series, ISIN). Historical index prices are already fetched nightly
into `indices_data/` via `scripts/fetch_indices_history.py`.

## What Already Exists (Don't Rebuild)

- ✅ **Price histories for 15 of 23 sectoral indices** in `indices_data/`
  (Bank, IT, Auto, Pharma, Healthcare, Metal, FMCG, Realty, Media,
  Consumer Durables, PSU Bank, Private Bank, Oil & Gas, Financial
  Services). See list below — 8 still need to be added to
  `tracked_indices.csv`.
- ✅ **Index fetcher** (`scripts/fetch_indices_history.py`) reads from
  [data/static/tracked_indices.csv](../../data/static/tracked_indices.csv)
  — uses Zerodha instrument tokens to fetch daily OHLCV.
- ✅ **Universe files** have an `Industry` column (NSE classification) that
  gives rough sector info per stock.
- ✅ **`Holding` model** already has `sector` / `industry` columns (unused).
- ✅ **Relative-performance math** in `scripts/report_backtests.py`
  (information ratio, tracking error, rolling metrics).

## Full Sectoral Index List (23)

Confirmed via [niftyindices.com/indices/equity/sectoral-indices](https://www.niftyindices.com/indices/equity/sectoral-indices). "Price data" column reflects Kite instrument-master availability checked against [data/instruments_full.csv](../../data/instruments_full.csv).

| # | Sector | Slug | Kite tradingsymbol | Token | Status |
|---|--------|------|---------------------|-------|--------|
| 1 | Nifty Auto | `nifty-auto` | `NIFTY AUTO` | 263433 | ✅ tracked |
| 2 | Nifty Bank | `nifty-bank` | `NIFTY BANK` | 260105 | ✅ tracked |
| 3 | Nifty Cement | `nifty-cement` | — | — | ⚠️ constituents only (no Kite token) |
| 4 | Nifty Chemicals | `nifty-chemicals` | `NIFTY CHEMICALS` | 420105 | 🆕 **to add** |
| 5 | Nifty Financial Services | `nifty-financial-services` | `NIFTY FIN SERVICE` | 257801 | ✅ tracked |
| 6 | Nifty Financial Services 25/50 | `nifty-financial-services-25-50-index` | `NIFTY FINSRV25 50` | 288265 | 🆕 **to add** |
| 7 | Nifty Financial Services Ex Bank | `nifty-financial--services-ex-bank` | `NIFTY FINSEREXBNK` | 410633 | 🆕 **to add** |
| 8 | Nifty FMCG | `nifty-fmcg` | `NIFTY FMCG` | 261897 | ✅ tracked |
| 9 | Nifty Healthcare | `nifty-healthcare-index` | `NIFTY HEALTHCARE` | 288521 | ✅ tracked |
| 10 | Nifty IT | `nifty-it` | `NIFTY IT` | 259849 | ✅ tracked |
| 11 | Nifty Media | `nifty-media` | `NIFTY MEDIA` | 263945 | ✅ tracked |
| 12 | Nifty Metal | `nifty-metal` | `NIFTY METAL` | 263689 | ✅ tracked |
| 13 | Nifty Pharma | `nifty-pharma` | `NIFTY PHARMA` | 262409 | ✅ tracked |
| 14 | Nifty Private Bank | `nifty-private-bank` | `NIFTY PVT BANK` | 271113 | ✅ tracked |
| 15 | Nifty PSU Bank | `nifty-psu-bank` | `NIFTY PSU BANK` | 262921 | ✅ tracked |
| 16 | Nifty Realty | `nifty-realty` | `NIFTY REALTY` | 261129 | ✅ tracked |
| 17 | Nifty REITs & Realty | `nifty-reits-realty` | — | — | ⚠️ constituents only |
| 18 | Nifty Consumer Durables | `nifty-consumer-durables-index` | `NIFTY CONSR DURBL` | 288777 | ✅ tracked |
| 19 | Nifty Oil and Gas | `nifty-oil-and-gas-index` | `NIFTY OIL AND GAS` | 289033 | ✅ tracked |
| 20 | Nifty500 Healthcare | `nifty500-healthcare` | `Nifty500 Health` | 420873 | 🆕 **to add** |
| 21 | Nifty MidSmall Financial Services | `nifty-midsmall--financial-services` | `NIFTY MS FIN SERV` | 411401 | 🆕 **to add** |
| 22 | Nifty MidSmall Healthcare | `nifty-midsmallhealthcare` | — | — | ⚠️ constituents only |
| 23 | Nifty MidSmall IT & Telecom | `nifty-midsmall--it-telecom` | `NIFTY MS IT TELCM` | 411913 | 🆕 **to add** |

**Summary:** 15 already tracked, **6 to add** (Chemicals, FinServ 25/50, FinServ Ex Bank, MidSmall FinServ, MidSmall IT & Telecom, Nifty500 Healthcare), **3 constituents-only** (Cement, REITs & Realty, MidSmall Healthcare — no Kite token, so we'll show constituent tables but no price index or heatmap row for them).

**Critical data-source insight:** CSV filenames on niftyindices.com are *not*
derivable from slugs — casing, underscores, even typos vary per sector. The
fetcher **must scrape each sector landing page** to discover its CSV URL.

## Benchmarks

User-toggleable in the UI. We track Nifty 50, 100, 200, 500 as eligible benchmarks for sector-vs-market comparison.

| Benchmark | Kite tradingsymbol | Token | Status |
|-----------|--------------------|-------|--------|
| Nifty 50 | `NIFTY 50` | 256265 | ✅ tracked |
| Nifty 100 | `NIFTY 100` | 260617 | ✅ tracked |
| Nifty 200 | `NIFTY 200` | 264457 | 🆕 **to add** |
| Nifty 500 | `NIFTY 500` | 268041 | ✅ tracked |

Default benchmark on first load: Nifty 100 (matches existing portfolio benchmark). Toggle persists in localStorage.

## Stock Coverage

Sector constituents may include stocks outside NSE 500 — especially for MidSmall variants. Plan:

1. After constituents fetch, UNION all unique symbols across all 23 sectors.
2. DIFF against what we have price history for (existing `nse500_data/*.csv`).
3. For missing symbols, resolve instrument tokens via [data_pipeline/symbol_resolver.py](../../data_pipeline/symbol_resolver.py).
4. Fetch daily OHLCV history from Kite, store into the same `nse500_data/` directory (naming is symbol-agnostic — the directory is effectively "all stocks we care about").
5. These extra symbols get picked up by the nightly fetcher once they're in a universe list.

Task #4 handles this stock-coverage expansion.

## What's Missing (Build This)

1. **Price data for 8 sectors** — Cement, Chemicals, Financial Services
   25/50, Financial Services Ex Bank, REITs & Realty, Nifty500
   Healthcare, MidSmall Financial Services, MidSmall Healthcare, MidSmall
   IT & Telecom. Add Zerodha instrument tokens to
   `data/static/tracked_indices.csv` so the nightly fetcher picks them
   up. Some of these indices are young (≤ 2 years) — acceptable.
2. **Constituent membership** — we know which stocks are in NSE 500, but
   not which ones are in Nifty Bank vs Nifty Auto. Stock ↔ sector-index
   mapping comes from the niftyindices.com CSVs (with weightage).
3. **Sector study service** — compute returns / relative strength / beta
   over rolling windows, per sector and per stock-in-sector.
4. **Sectors dashboard page** — heatmap of sector performance + drill-down.

## Data Source Details

**Fetching strategy (two-step):**

1. Scrape each sector's landing page
   (`niftyindices.com/indices/equity/sectoral-indices/<slug>`) and extract
   the `IndexConstituent/ind_*.csv` href — filenames are inconsistent
   (see table above), so hard-coding is fragile.
2. Download that CSV from `niftyindices.com/IndexConstituent/<filename>`.

Both requests need a browser-ish User-Agent; default `requests`/`httpx`
defaults are blocked by Cloudflare.

**CSV columns (typical):** `Company Name, Industry, Symbol, Series,
ISIN Code`. Some indices also include `Weightage(%)` — where present,
use it; where absent, fall back to equal weight.

**Snapshot only:** niftyindices.com serves the *current* constituent list;
no point-in-time history. We persist the latest snapshot with an
`as_of_date` and accept that historical analysis is survivorship-biased
(same caveat as most free Indian data).

**Failure tolerance:** one sector's CSV may fail (HTML error page,
network blip, page redesign). Each sector fetch must fail independently
and log — never block the batch.

## Scope & Non-Goals (v1)

**In scope:**
- All 23 sectoral indices listed on niftyindices.com's sectoral page.
  Not thematic, not strategy, not broad-market.
- Daily-frequency analysis. No intraday.
- Current constituent snapshot. Rebuild weekly.

**Out of scope for v1:**
- Point-in-time constituent history / survivorship correction.
- Sector-neutral or sector-rotation portfolio variants (that's a follow-up).
- Global/sector benchmarks (MSCI, S&P).
- Indices niftyindices.com classifies as **thematic** (Energy, Infra,
  Consumption, Commodities, PSE, CPSE, MNC, Service Sector) — our
  internal `tracked_indices.csv` labels some of these as "sectoral" but
  we'll leave that alone. They can be added to a separate "Thematic
  Indices" page later if useful.

---

## Tasks

### Phase 1: Data Pipeline

#### Task #1: Design data model + fetch strategy
**Status:** ✅ Complete — see [DESIGN.md](DESIGN.md)

Decide schema (sectors + sector_constituents tables), fetcher approach
(scrape landing page → download CSV), benchmark toggle, and study-API shape.

#### Task #2: Add missing indices to `tracked_indices.csv` + fetch history
**Status:** ⬜ Pending
**Blocked by:** #1

Add rows for:
- Benchmark: **Nifty 200** (token 264457, `NIFTY 200`).
- 6 new sectorals: Chemicals (420105), FinServ 25/50 (288265), FinServ Ex Bank (410633), MidSmall FinServ (411401), MidSmall IT & Telecom (411913), Nifty500 Healthcare (420873).

Then run `scripts/fetch_indices_history.py` once to populate `indices_data/` for the new rows. Some of these are young indices (launched 2023+) and may have short histories — that's fine, document the earliest date available.

#### Task #3: `sectors` + `sector_constituents` tables + migration
**Status:** ⬜ Pending
**Blocked by:** #1

- `sectors` table (id, slug, display_name, nifty_tradingsymbol,
  has_price_data, constituents_url, last_refreshed_at). The
  `has_price_data` flag is `false` for Cement / REITs & Realty /
  MidSmall Healthcare where no Kite token exists — UI hides those from
  the heatmap but shows their constituent tables.
- `sector_constituents` table (sector_id, symbol, company_name,
  industry, isin, weightage, as_of_date) with unique (sector_id, symbol).
- Alembic migration `YYYYMMDD_0005_add_sectors.py`. Pre-populate the
  `sectors` table from a seed file or migration data function.

#### Task #4: Constituents fetcher script
**Status:** ⬜ Pending
**Blocked by:** #3

- `scripts/fetch_sector_constituents.py` — scrape each of the 23 sector
  landing pages for a CSV URL, download, parse, upsert.
- Cache the discovered CSV URL in `sectors.constituents_url` after
  first successful fetch.
- Each sector fails independently; aggregate result dict at end.
- Logs per-sector: symbols added / removed / weight changes.
- Robust to missing `Weightage` column.
- `--dry-run` mode for diff preview.

#### Task #5: Stock-coverage expansion
**Status:** ⬜ Pending
**Blocked by:** #4

After constituents are loaded:

- Compute set of unique symbols across all 23 sectors.
- Diff against `nse500_data/*_day.csv` — identify symbols we don't yet
  have price history for.
- Use `data_pipeline/symbol_resolver.py` to map to instrument tokens.
- Fetch historical daily OHLCV from Kite, store in `nse500_data/`.
- Log: "Added N new stocks to universe" (typically from MidSmall
  constituents). These stocks will be picked up by the nightly fetcher
  going forward.
- Create/update a `data/static/sector_stocks_universe.csv` tracking the
  extended universe for bookkeeping.

#### Task #6: Daily / weekly pipeline integration
**Status:** ⬜ Pending
**Blocked by:** #4, #5

- Add a `refresh_sector_constituents` step to
  `scripts/run_daily_pipeline.py`, gated on `weekday == Monday` or an
  `--with-sectors` flag (NSE rebalances sectorals semi-annually; weekly
  refresh is enough).
- Daily index-price fetcher already covers new sectorals via #2.
- Daily stock-price fetcher already covers new constituent stocks via #5.

---

### Phase 2: Analytics

#### Task #7: Sector study service
**Status:** ⬜ Pending
**Blocked by:** #3

- `app/services/sector_service.py` with:
  - `get_sectors(benchmark)` — heatmap payload with returns + vs-benchmark across windows.
  - `get_sector_detail(slug, benchmark)` — constituents with per-stock returns, vs-sector, vs-benchmark, weightage, ranking.
  - `get_relative_strength(slug, benchmark, window=63)` — rolling 3M sector − benchmark series.
  - `list_benchmarks()` — returns the four eligible benchmarks for the UI toggle.
- Benchmark is a parameter on every query — not hardcoded.
- Pure functions over price DataFrames cached via LRU (invalidated after daily fetch).

#### Task #8: Sector API endpoints
**Status:** ⬜ Pending
**Blocked by:** #7

- `GET /api/sectors?benchmark=NIFTY_100` — heatmap payload.
- `GET /api/sectors/{slug}?benchmark=NIFTY_100` — sector detail.
- `GET /api/sectors/{slug}/relative-strength?benchmark=NIFTY_100` — RS time series.
- `GET /api/sectors/benchmarks` — eligible benchmark list for UI toggle.
- Pydantic schemas in `app/schemas/sectors.py`. Benchmark param validated against whitelist.

---

### Phase 3: Frontend

#### Task #9: Sectors page + heatmap + benchmark toggle
**Status:** ⬜ Pending
**Blocked by:** #8

- `kite-dashboard/src/app/(dashboard)/sectors/page.tsx`.
- **Benchmark toggle** (segmented control: Nifty 50 / 100 / 200 / 500) persisted in localStorage; triggers re-fetch.
- Heatmap: rows = sectors with price data (20 of 23), columns = time windows (1D / 5D / 1M / 3M / 6M / 1Y / YTD). Green/red gradient. Benchmark row pinned at top.
- Sort by any column; click-through to sector detail.
- Constituents-only sectors (3) shown in a secondary panel below the heatmap — just a list with links to their constituent tables.

#### Task #10: Sector detail view
**Status:** ⬜ Pending
**Blocked by:** #9

- Route `/sectors/[slug]`.
- Benchmark toggle (same as parent page, synced via context or localStorage).
- Top: sector index price chart + selected benchmark overlay, normalized to 100 at window start. Window selector: 3M / 6M / 1Y / 3Y / All.
- Rolling relative strength chart (3M sector return − 3M benchmark return), zero line + shaded band at ±5%.
- Constituents table: symbol, weightage, returns over 1M / 3M / 6M / 1Y, vs-sector excess, vs-benchmark excess. Sortable.

---

### Phase 4: QA

#### Task #11: Verify numbers + deploy
**Status:** ⬜ Pending
**Blocked by:** #9, #10

- Spot-check sector returns against niftyindices.com's own factsheet values (tolerance ±5 bps due to close-vs-close).
- Verify weightages sum to ~100% per sector with weightage data.
- Confirm benchmark toggle rewrites all numbers + charts correctly.
- Verify constituents-only sectors render without errors.
- Deploy to Railway + Vercel.

---

### Phase 5: Deferred

#### Task #12: Portfolio overlay
**Status:** ⏸️ Deferred (user preference — keep sector analytics standalone for v1)

Future enhancements (not in scope now):
- Annotate each sector with "X of Y holdings in current portfolio".
- Highlight portfolio holdings in constituent tables.
- Show which portfolio picks are outperforming their sector peers.

---

## Dependency Graph

```
#1 Design
  │
  ├──► #2 Add indices to tracked_indices.csv + fetch history
  │
  └──► #3 Sectors tables + migration (with seed data)
         │
         └──► #4 Constituents fetcher
                │
                ├──► #5 Stock-coverage expansion
                │
                ├──► #6 Pipeline integration (weekly refresh)
                │
                └──► #7 Sector study service
                       │
                       └──► #8 API endpoints
                              │
                              └──► #9 Sectors page + heatmap + bench toggle
                                     │
                                     └──► #10 Sector detail view
                                            │
                                            └──► #11 QA + deploy
                                                   │
                                                   └──► #12 Portfolio overlay (deferred)
```

---

## Resolved Questions

- **Benchmarks:** Nifty 50, 100, 200, 500 — user toggles in UI, default Nifty 100.
- **Portfolio overlay:** deferred (Task #12). v1 is standalone sector analytics.
- **Heatmap windows:** 1D / 5D / 1M / 3M / 6M / 1Y / YTD.
- **Refresh frequency:** weekly (Monday), since NSE rebalances sectorals semi-annually.
- **Indices without Kite tokens (Cement, REITs & Realty, MidSmall Healthcare):** constituents still tracked, but those three are hidden from the heatmap (no price series) and shown only in a "constituents-only" sidebar / secondary panel.
- **New stock universe:** extended organically via Task #5 — constituents outside NSE 500 (mostly from MidSmall sectors) get added to `nse500_data/` and the nightly fetcher picks them up going forward.
