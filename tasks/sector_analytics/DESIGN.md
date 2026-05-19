# Sector Analytics — Design Document

## 1. Data Model

### 1.1 `sectors` table

One row per sectoral index (23 rows total). Seeded once via the migration's
`op.bulk_insert` using the full list from README.md.

```sql
CREATE TABLE sectors (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(50) NOT NULL UNIQUE,           -- 'nifty-bank', 'nifty-it', ...
    display_name VARCHAR(100) NOT NULL,         -- 'Nifty Bank'
    nifty_tradingsymbol VARCHAR(50),            -- 'NIFTY BANK' — joins to indices_data/NIFTY_BANK.csv; NULL if no Kite token
    has_price_data BOOLEAN NOT NULL DEFAULT FALSE,  -- derived: NOT NULL when nifty_tradingsymbol IS NOT NULL AND csv exists
    landing_page_url TEXT NOT NULL,             -- used by scraper
    constituents_url TEXT,                      -- cached CSV URL after first successful scrape
    last_refreshed_at TIMESTAMP,
    sort_order INTEGER DEFAULT 0                -- for stable ordering in UI
);
```

3 sectors (Cement, REITs & Realty, MidSmall Healthcare) will have
`nifty_tradingsymbol = NULL`, `has_price_data = false` — they're valid
sectors with constituents, but no price index to chart. The UI keeps them
in a secondary "constituents-only" panel.

### 1.2 `sector_constituents` table

Current snapshot of (sector, stock) membership with weightage. Wiped and
rebuilt by the fetcher each refresh — trade off: we lose history of
constituent changes, but snapshot freshness is all niftyindices.com gives
us anyway.

```sql
CREATE TABLE sector_constituents (
    id SERIAL PRIMARY KEY,
    sector_id INTEGER NOT NULL REFERENCES sectors(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    company_name VARCHAR(200),
    industry VARCHAR(100),                      -- NSE sub-industry
    isin VARCHAR(20),
    weightage NUMERIC(8, 4),                    -- percentage, nullable (not all CSVs have it)
    as_of_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE UNIQUE INDEX ix_sector_constituents_sector_symbol
    ON sector_constituents(sector_id, symbol);
CREATE INDEX ix_sector_constituents_symbol
    ON sector_constituents(symbol);             -- fast reverse lookup (what sectors is X in?)
```

A stock can appear in multiple sectors (e.g., SBIN → Bank and PSU Bank),
hence the reverse index on `symbol`.

### 1.3 Why not store sector price data in DB?

Already in `indices_data/*.csv` — reading CSVs with pandas is fast (< 5ms
per sector) and keeps the DB lean. Use an in-process LRU cache keyed on
the file's mtime.

## 2. Constituents Fetcher

File: `scripts/fetch_sector_constituents.py`

```python
def fetch_all_sectors() -> dict[str, FetchResult]:
    """Iterate sectors from the sectors table, scrape each landing page,
    download its CSV, upsert."""

def fetch_sector(slug: str) -> FetchResult:
    """Two-step: discover CSV URL from landing page, then download & parse.
    Wipe & rebuild rows in sector_constituents for this sector."""
```

**Step 1 — discover CSV URL:**

```python
LANDING_URL = "https://www.niftyindices.com/indices/equity/sectoral-indices/{slug}"
CSV_HREF_RE = re.compile(r'IndexConstituent/([^"\']+\.csv)')

def discover_csv_url(slug: str) -> str | None:
    html = httpx.get(LANDING_URL.format(slug=slug), headers=UA_HEADERS).text
    m = CSV_HREF_RE.search(html)
    return f"https://niftyindices.com/IndexConstituent/{m.group(1)}" if m else None
```

The CSV filenames are inconsistently named by NSE (e.g.,
`ind_NiftyCement_list.csv`, `ind_niftymidsmallfinancailservice_list.csv`
— note the typo). Hard-coding is fragile. If the first page fetch
doesn't reveal a CSV link (as with `nifty-reits-realty`), log and skip.

**Step 2 — download:**

```python
def download_csv(url: str) -> pd.DataFrame:
    r = httpx.get(url, headers=UA_HEADERS, timeout=30)
    r.raise_for_status()
    if "DOCTYPE" in r.text[:100]:
        raise CsvFetchError("got HTML instead of CSV — likely rate-limited")
    return pd.read_csv(io.StringIO(r.text), dtype={"Symbol": str})
```

`UA_HEADERS` = `{"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X ...) Chrome/120.0.0.0"}`.
Without this, Cloudflare serves a block page.

**Parse:** strip whitespace, normalize column names (`Company Name` →
`company_name`, `Weightage(%)` → `weightage`). Handle absent weightage.

**Upsert strategy:** `DELETE WHERE sector_id = ?` then
`bulk_insert_mappings`. Handles additions + removals in one shot.

**Dry-run mode:** `--dry-run` prints diffs (symbols added / removed,
weights changed by > 0.5%) without writing.

**Failure handling:** each sector fetched independently; failures log and
continue. Return a per-sector result dict. Cache the discovered CSV URL
in the `sectors` table (`constituents_url` column) after first successful
fetch — subsequent fetches skip step 1 unless `--rediscover` is passed
or the cached URL 404s.

**Rate-limiting:** 1-second sleep between sectors (23 fetches → ~25s
total). niftyindices.com is tolerant but no reason to hammer.

## 3. Sector Study Service

File: `app/services/sector_service.py`

### 3.1 Price loading

```python
@lru_cache(maxsize=64)
def load_index_prices(symbol: str) -> pd.DataFrame:
    """Load an index CSV from indices_data/<SYMBOL>.csv, indexed by date."""
```

Cache is invalidated manually by `invalidate_price_cache()` called after
the daily fetch finishes. Simpler than an mtime check.

Stock prices live in `nse500_data/<SYMBOL>_day.csv` — same pattern.

### 3.2 Return windows

```python
WINDOWS = {
    "1d":  1,
    "5d":  5,
    "1m":  21,
    "3m":  63,
    "6m":  126,
    "1y":  252,
    "ytd": None,   # special-case: YTD uses Jan 1 of current year
}

def compute_returns(prices: pd.DataFrame, as_of: date) -> dict[str, float]:
    """Return dict of {window: simple_return} using close-to-close."""
```

Close-to-close simple returns (not log). Robust to missing bars — use
the last available price on-or-before the target date.

### 3.3 Benchmark whitelist

```python
VALID_BENCHMARKS = {
    "NIFTY 50":  "NIFTY 50",
    "NIFTY 100": "NIFTY 100",
    "NIFTY 200": "NIFTY 200",
    "NIFTY 500": "NIFTY 500",
}

def list_benchmarks() -> list[dict]:
    """Expose eligible benchmarks to the UI toggle."""
    return [{"key": k, "display_name": v} for k, v in VALID_BENCHMARKS.items()]
```

Benchmark key is validated against this dict in the API layer. Default is
`NIFTY 100`. v1 does not add portfolio as a "benchmark" option — user wants
this feature standalone.

### 3.4 Sector heatmap payload

```python
@dataclass
class SectorReturns:
    slug: str
    display_name: str
    has_price_data: bool             # false for Cement / REITs&Realty / MidSmall Healthcare
    returns: dict[str, float] | None
    vs_benchmark: dict[str, float] | None
    constituent_count: int

def get_sector_heatmap(benchmark: str = "NIFTY 100") -> list[SectorReturns]:
    """Returns all 23 sectors — constituents-only sectors have returns=None."""
```

### 3.5 Sector detail payload

```python
@dataclass
class ConstituentPerformance:
    symbol: str
    company_name: str
    weightage: float | None
    returns: dict[str, float]
    vs_sector: dict[str, float] | None       # None if sector has no price data
    vs_benchmark: dict[str, float]

@dataclass
class SectorDetail:
    slug: str
    display_name: str
    has_price_data: bool
    as_of_date: date
    constituents: list[ConstituentPerformance]
    # Populated only if has_price_data is True:
    index_price_series: list[dict] | None       # normalized to 100 at window start
    benchmark_price_series: list[dict] | None
    relative_strength_series: list[dict] | None

def get_sector_detail(slug: str, benchmark: str = "NIFTY 100") -> SectorDetail:
    ...
```

### 3.6 Relative strength series

Rolling 63-day (3-month) outperformance of sector vs benchmark:

```python
def get_relative_strength(
    sector_tradingsymbol: str,
    benchmark_tradingsymbol: str = "NIFTY 100",
    window: int = 63,
) -> pd.Series:
    sector_ret = load_index_prices(sector_tradingsymbol)["close"].pct_change(window)
    bench_ret  = load_index_prices(benchmark_tradingsymbol)["close"].pct_change(window)
    return (sector_ret - bench_ret).dropna()
```

## 4. API

File: `app/api/sectors.py`, prefix `/api/sectors`, auth required.

Benchmark query param accepted by all endpoints that compute relative
performance; validated against the whitelist (400 on invalid).

### 4.1 `GET /api/sectors/benchmarks`

Returns eligible benchmarks for the UI toggle. No auth.

```json
{
  "benchmarks": [
    {"key": "NIFTY 50",  "display_name": "Nifty 50"},
    {"key": "NIFTY 100", "display_name": "Nifty 100"},
    {"key": "NIFTY 200", "display_name": "Nifty 200"},
    {"key": "NIFTY 500", "display_name": "Nifty 500"}
  ],
  "default": "NIFTY 100"
}
```

### 4.2 `GET /api/sectors?benchmark=NIFTY%20100`

Returns heatmap data. Includes sectors with `has_price_data = false`; their
`returns` and `vs_benchmark` are null — frontend renders them in a secondary
panel.

```json
{
  "as_of_date": "2026-04-17",
  "benchmark": "NIFTY 100",
  "sectors": [
    {
      "slug": "nifty-bank",
      "display_name": "Nifty Bank",
      "has_price_data": true,
      "constituent_count": 12,
      "returns":      {"1d": 0.008, "5d": 0.021, "1m": 0.054, ...},
      "vs_benchmark": {"1d": 0.003, "5d": -0.002, "1m": 0.022, ...}
    },
    {
      "slug": "nifty-cement",
      "display_name": "Nifty Cement",
      "has_price_data": false,
      "constituent_count": 15,
      "returns": null,
      "vs_benchmark": null
    },
    ...
  ]
}
```

### 4.3 `GET /api/sectors/{slug}?benchmark=NIFTY%20100`

Returns detail + constituent table. 404 if slug unknown.

```json
{
  "slug": "nifty-bank",
  "display_name": "Nifty Bank",
  "has_price_data": true,
  "as_of_date": "2026-04-17",
  "constituents": [
    {
      "symbol": "HDFCBANK",
      "weightage": 28.4,
      "returns":      {"1m": 0.045, "3m": 0.102, ...},
      "vs_sector":    {"1m": 0.012, "3m": 0.031, ...},
      "vs_benchmark": {"1m": 0.028, "3m": 0.067, ...}
    },
    ...
  ]
}
```

### 4.4 `GET /api/sectors/{slug}/relative-strength?benchmark=NIFTY%20100`

Returns time-series for the RS chart (3M rolling, default last 2 years).
404 if slug doesn't have `has_price_data`.

```json
{
  "sector_tradingsymbol": "NIFTY BANK",
  "benchmark_tradingsymbol": "NIFTY 100",
  "window_days": 63,
  "series": [
    {"date": "2024-05-01", "value": 0.021},
    ...
  ]
}
```

## 4.5 Stock-coverage expansion (Task #5)

Happens at the end of the constituents fetcher (or as a standalone step):

```python
def expand_stock_universe(session) -> ExpandResult:
    """Ensure every sector constituent has daily price history."""
    constituents = session.query(SectorConstituent.symbol).distinct().all()
    have = set(path.stem.removesuffix("_day") for path in Path("nse500_data").glob("*_day.csv"))
    missing = [s for (s,) in constituents if s not in have]

    tokens = resolve_instrument_tokens(missing)  # via data_pipeline/symbol_resolver
    fetch_prices(tokens, output_dir="nse500_data/")  # reuses PriceClient
    return ExpandResult(added=len(missing), unresolved=[...])
```

Typical result: MidSmall sectors add ~30-60 small-cap stocks not in NSE 500.
Once added, they're picked up by the nightly fetcher going forward. No
separate "sector stocks" directory — we keep one flat stock data dir.

## 5. Frontend

### 5.1 Sectors page

`app/(dashboard)/sectors/page.tsx`. Uses SWR.

**Benchmark toggle** — segmented control at the top (Nifty 50 / 100 / 200 /
500). Persists in localStorage under `sectors.benchmark`. Triggers SWR
re-fetch with the new `benchmark` query param.

**Heatmap table** — 20 sectors with price data:

```
                  1D     5D     1M     3M     6M     1Y     YTD
Benchmark N100   +0.5%  +1.3%  +3.2%  ...     (pinned, grey background)
─────────────────────────────────────────────────────────────
Nifty Bank       +0.8%  +2.1%  +5.4%  +12.3%  ...
Nifty IT         -0.3%  -1.0%  +1.2%  ...
...
```

Color scale: diverging red→neutral→green; clip at ±5% for short windows
(1D/5D), ±30% for long (1Y/YTD). Cells show raw return; hover tooltip
shows vs-benchmark excess.

Click row → `/sectors/[slug]`.

**Constituents-only panel** (below the heatmap) — lists the 3 sectors
without price data (Cement, REITs & Realty, MidSmall Healthcare) as simple
text links. Click → sector detail with constituent table only (no charts).

### 5.2 Sector detail page

Benchmark toggle synced with parent page via localStorage.

1. **Price chart** — sector index + benchmark, normalized to 100 at start
   of visible window. Window selector: 3M / 6M / 1Y / 3Y / All. Hidden if
   `has_price_data = false`.
2. **Relative strength line** — 3M rolling RS (zero line = sector
   matching benchmark). Shaded band at ±5%. Hidden if no price data.
3. **Constituents table** — sortable. Columns: Symbol, Weight %, 1M / 3M
   / 6M / 1Y returns, vs-Sector excess (these windows), vs-Benchmark excess.
   Always visible.

Reuse `recharts` (already a dependency).

## 6. Files Touched

**New:**
- `kite-api/alembic/versions/YYYYMMDD_0005_add_sectors.py`
- `kite-api/app/services/sector_service.py`
- `kite-api/app/api/sectors.py`
- `kite-api/app/schemas/sectors.py`
- `scripts/fetch_sector_constituents.py`
- `kite-dashboard/src/app/(dashboard)/sectors/page.tsx`
- `kite-dashboard/src/app/(dashboard)/sectors/[slug]/page.tsx`
- `kite-dashboard/src/components/sectors/` (heatmap, constituents-table,
  rs-chart)
- `kite-api/tests/test_sector_service.py`

**Modified:**
- `kite-api/app/models/models.py` — `Sector`, `SectorConstituent` models.
- `scripts/run_daily_pipeline.py` — optional weekly sector refresh.
- `kite-dashboard/src/components/layout/sidebar.tsx` (or equivalent) —
  "Sectors" nav link.
- `kite-dashboard/src/lib/api-client.ts` — `getSectors` / `getSectorDetail` /
  `getRelativeStrength` functions.
- `kite-dashboard/src/lib/types.ts` — new types.

## 7. Edge Cases

| Case | Handling |
|------|----------|
| niftyindices.com returns HTML instead of CSV (rate-limit) | Retry with backoff, fail the sector, continue others. |
| Sector CSV is missing `Weightage` column | Store NULL; UI shows "—". |
| Stock has a sector membership but no price file in `nse500_data/` | Skip from per-stock returns; flag in logs. Sectoral indices sometimes include non-NSE500 stocks (e.g., niche PSU banks). |
| Price CSV has stale last date (data gap) | Use most recent available price; flag stale returns with `last_price_date` in response. |
| New constituent added between refreshes | Refreshing is idempotent; next run picks it up. |
| Holiday vs working day | Compute returns using trading-day offsets, not calendar days (our CSVs only have trading days anyway). |

## 8. Testing

Unit tests (`tests/test_sector_service.py`):
- Window return computation on synthetic price series (match manual math).
- Relative-strength series aligns dates correctly when one index is
  longer/shorter than the other.
- Missing-price handling returns None without crashing.
- Heatmap payload shape matches schema.

Integration:
- Run fetcher in dry-run mode, verify expected sector count (15) and
  plausible symbol counts per sector (Bank ≈ 12, IT ≈ 10, Auto ≈ 15).
- Run actual fetcher, confirm rows are upserted.
- Hit `/api/sectors` locally and spot-check a few sector returns against
  niftyindices.com's published factsheets (tolerance: ±5 bps since we
  use close-to-close).

## 9. Rollout

1. **Phase 1 (data):** migration + fetcher only. Ship to prod, run once,
   verify DB state.
2. **Phase 2 (API):** service + endpoints. Deploy, smoke-test via curl.
3. **Phase 3 (UI):** heatmap + detail pages. Dev locally, verify numbers,
   push to main.
4. **Phase 4:** portfolio overlay, polish.

Each phase ships independently. No "big bang" merges.

## 10. Deferred — Nice-to-Haves

- **Point-in-time constituent history** (scrape Wayback Machine for
  historical CSVs) — only worth it if we do sector-momentum backtests.
- **Cross-sector rotation chart** — relative strength ranking over time,
  shows leadership shifts (IT → Pharma → Auto).
- **Industry sub-view** — use the NSE `Industry` column in
  `nse500_universe.csv` for a second classification independent of
  Nifty sectoral membership.
- **Alerts** — email/webhook when a sector breaks out vs benchmark
  (e.g., 3M RS crosses +5%).
