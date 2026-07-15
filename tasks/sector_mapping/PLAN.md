# sector_mapping

## Why

Every tracked stock should carry a sector label we can use in the product /
research (sector RS, breadth, grouping). Our universe CSVs already carry NSE's
broad macro `Industry` (21 buckets); we want the finer, more intuitive
**Zerodha** sector taxonomy (35 sectors) alongside it — e.g. NSE lumps TCS,
Info Edge and Sonata into "Information Technology" while Zerodha splits
Software Services vs IT (internet) vs Services.

Source requested by the founder: <https://zerodha.com/markets/sector/>.

## Outcome

A per-symbol mapping `symbol -> zerodha_sector` covering all tracked Indian
symbols (union of nse500 / nifty250 / nifty100 / nifty_smallcap universes),
plus a full NSE/BSE reverse index (sector -> constituents) as a reference.

## Scope boundary — non-disruptive

- Reads `data/static/*_universe.csv` **read-only**.
- Writes **only** inside `tasks/sector_mapping/data/`. Nothing under
  `data/static/`, `scripts/`, `kite-api/` or any production path is touched.
- US equities (`us_equities_universe.csv`) are out of scope — Zerodha's
  sector pages are NSE/BSE only.

## Critical files

- `resolve_stock_sectors.py` — authoritative per-stock resolver (the deliverable).
- `scrape_zerodha_sectors.py` — full sector -> constituents reverse index (reference).
- `data/tracked_sectors.csv` — the mapping.
