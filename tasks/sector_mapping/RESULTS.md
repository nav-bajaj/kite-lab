# sector_mapping — results

Status: shipped (data asset produced; nothing wired into production yet).

## What shipped

Two scrapers (stdlib only — `urllib`, no new deps) and their outputs, all
confined to this task folder.

### 1. `resolve_stock_sectors.py` — authoritative per-stock mapping

For each tracked Indian symbol it fetches the stock's own Zerodha page
(`/markets/stocks/NSE|BSE/<SYM>/`) and reads the breadcrumb sector link. This
is the source of truth because it gives Zerodha's **single canonical** sector
per stock and is more complete than the sector-list pages (it recovers LTIM,
GSPL which the list pages omit, and files ASTRAL under Engineering Capital
Goods rather than the niche Plastic Pipes).

Output → `data/tracked_sectors.csv`:

| column | meaning |
|---|---|
| `symbol` | NSE symbol (join key to the universe CSVs) |
| `company` | company name (from universe CSV) |
| `nse_industry` | existing NSE macro industry (unchanged, for comparison) |
| `zerodha_sector` | Zerodha sector, display name (e.g. `Software Services`) |
| `zerodha_sector_slug` | slug (e.g. `software-services`) |
| `in_universes` | which of the 4 universes the symbol is in |
| `source_exchange` | which Zerodha exchange page resolved it (NSE/BSE) |
| `matched` | `yes` / `no` |

### 2. `scrape_zerodha_sectors.py` — full reverse index (reference)

Scrapes all 35 sector-list pages → `data/zerodha_sectors_raw.csv`
(~5.6k NSE+BSE rows: `zerodha_sector, sector_slug, exchange, symbol, company,
market_cap_cr, pe`). Useful as a sector → constituents lookup beyond our
tracked universes.

## Coverage

- **526** tracked Indian symbols (union of nse500/nifty250/nifty100/nifty_smallcap).
- **524 (99.6%)** resolved to a Zerodha sector.
- **2 uncategorized** (left blank + flagged in `data/unmatched.csv`, NOT invented):
  - `DUMMYHDLVR` — a placeholder NSE demerger scrip, not a real company; expected miss.
  - `AKZOINDIA` (Akzo Nobel India) — real stock, but its Zerodha page carries no
    sector link. Its NSE `Industry` (`Consumer Durables`) is still available if a
    label is needed.

Zerodha's 35 sectors are finer than NSE's 21 macro industries; spot-checked
correct (RELIANCE→Energy, TCS→Software Services, DMART→Retail, ASTRAL→Engineering
Capital Goods, M&M→Automobile, BHARTIARTL→Telecom).

## How to re-run

```bash
python tasks/sector_mapping/resolve_stock_sectors.py   # ~20s, 6 workers -> tracked_sectors.csv
python tasks/sector_mapping/scrape_zerodha_sectors.py  # ~30s -> zerodha_sectors_raw.csv (reference)
```

Both are idempotent (overwrite their outputs) and safe to re-run to refresh.

## Promoted to production (branch `sector-mapping`, 2026-07-15)

The founder approved "promote + loader + pipeline". The task-folder scripts
above remain as research history; the production versions are:

- **Refresh script** `scripts/fetch_zerodha_sectors.py` — production sibling of
  `fetch_sector_constituents.py`. Reads the tracked universes, follows
  `history_utils.SYMBOL_ALIASES` for renamed tickers (LTIM→LTM,
  AKZOINDIA→JSWDULUX), skips DUMMY* scrips, and writes the promoted CSV. With
  the alias reuse + DUMMY skip, coverage is now **502/502 (100%)**; the script
  exits non-zero if coverage drops below `--min-coverage` (default 0.97).
- **Data asset** `data/static/zerodha_sectors.csv` — NEW committed file
  (`symbol, company, zerodha_sector, zerodha_sector_slug, source_exchange`).
  The universe CSVs are byte-for-byte unchanged.
- **Loader** `kite-api/app/insights/zerodha_sectors.py` — mirrors
  `sector_constituents.py`: `file_signature`-keyed self-invalidating cache;
  `get_symbol_to_sector()`, `get_sector_for(symbol)`, `get_sector_to_symbols()`,
  `clear_cache()`. Any insight module / research script can now
  `from app.insights import zerodha_sectors`.
- **Test** `kite-api/tests/test_insights_zerodha_sectors.py` — real-data anchors
  + hermetic parse & cache-invalidation. 7 passing.
- **Docs** — new "Sector data" row in `scripts/README.md`; refresh runs at NSE
  reconstitution alongside `tasks/universe_membership/`, **not** in the daily cron
  (sectors change rarely; the daily pipeline invariant is untouched).

### Surfaced in the Insights Panel

- `kite-api/app/api/insights.py` — `_build_row` now carries a `zerodha_sector`
  field; the `/insights/screener` and `/insights/stocks/{symbol}` endpoints
  populate it from the loader. Additive field on the already-public insights
  endpoints; no new route, no auth change.
- `kite-api/app/insights/reading.py` — `clear_all_caches()` now also clears the
  Zerodha loader (belt-and-suspenders; the cache self-invalidates on file mtime).
- `kite-dashboard` — `StockRow` type gains `zerodha_sector`; the stock-detail
  header leads with it (the conventional "TICKER · Sector" identity line), with
  the NSE index baskets kept as a secondary clause.
- Tests: `test_insights_api.py::TestScreenerEndpoint::test_zerodha_sector_present`
  asserts ≥95% of screener rows carry the field. Frontend `npm run build` clean.
