# Decisions log — insights_dashboard_v2

## 2026-08-13 — founder reconciliation round

**D1 (intraday posture): DECIDED — go live.** Founder approved the live
data route. Engineering target is posture C from `REALTIME_SPEC.md`
(live *derived* indicators; no public per-stock live quote display
until a data agreement exists). Still required before public exposure:
risk-register row documenting the posture + labels ("provisional",
timestamp) as built. Multiple Kite Connect apps are available if
needed (see streaming note below) — note that extra API keys add
capacity/redundancy, not licensing cover.

**Cross-asset module: OUT of scope.** Dropped from the new dashboard.
It was barely wired anyway (only india_10y live; USDINR/gold/crude
registered `data_available=False`). INDIA VIX stays — it is part of
the macro/stress stack, not cross-asset. The global/commodity/rates
rows in `tracked_indices.csv` keep fetching (cheap, harmless) but
nothing in the new UI surfaces them.

**App placement: inside kite-dashboard, promoted to primary.** Insights
does not become a separate app. It stays in the same Next.js app and
becomes the signed-in home surface; portfolio pages demote behind the
admin flag (reversible when regulatory approval lands). Rationale:
shared Supabase auth, palette/token system, API client, CSP, and one
Vercel project on marketworks.in. A separate app would duplicate all
of that and force a microfrontends setup for one domain — available
later if ever needed, unnecessary now.

**Streaming design: single Kite websocket connection.** KiteTicker
supports up to 3,000 instrument tokens per connection (3 connections
per API key). Our full live set — NSE 500 stocks (~534 tokens) + 40
tracked indices — fits in ONE connection with 5x headroom. So:
no multiple API keys needed for data volume; a second app key is
useful only as failover or to separate the trading login from the
data login. Implementation ladder (see REALTIME_SPEC §2):
1. Start with REST polling (`quotes_service.py` already wraps batched
   `kite.quote()`; 500 instruments = one call) driven by the existing
   APScheduler — good to ~1-min cadence, fewest moving parts.
2. Upgrade to a KiteTicker consumer (quote mode — we need volume for
   surge counts) writing an in-memory tick state that the snapshot job
   reads, when/if we want sub-minute freshness.

**Historical data: no new granularity needed.** Daily (17y, merged) +
hourly (`nse500_data_hourly/`, already fetched daily) covers
everything planned: RRG needs daily/weekly; breadth history is daily;
the time-of-day volume curve calibrates fine from hourly bars. Minute
data is NOT needed for launch and can be fetched retroactively from
Kite if a future feature demands it. Index intraday history: not
needed — the live layer produces today's intraday curve going
forward; no backfill required.

**Nifty 250 composition: CONFIRMED.** `nifty250_universe.csv` =
all 100 Nifty 100 names + 150 midcap names (verified disjoint from
the smallcap 250 universe) — structurally NSE's NIFTY LARGEMIDCAP 250
(defined as Nifty 100 + Nifty Midcap 150). The official
`NIFTY LARGEMID250` index is already in the daily fetch and serves as
the official-index benchmark analog for our nifty250 universe in RRG
mode 2.

## Canonical list locations (reconciliation)

| List | File | Notes |
|---|---|---|
| All equities (NSE 500) | `data/static/nse500_universe.csv` (500) | authoritative; NSE schema (Company Name, Industry, Symbol, Series, ISIN) |
| Universe snapshots | `nifty50/100/250_universe.csv`, `nifty_smallcap_universe.csv` | current snapshots |
| Effective-dated membership | `data/static/*_membership.csv` (nse500: 534 rows) | survivorship-safe history; use for composites/drill-downs |
| Indices | `data/static/tracked_indices.csv` (40: 4 broad, 3 segment, 4 factor, 22 sectoral, 3 global, 2 commodity, VIX, GS 10YR) | list-driven daily fetch; add a row to track a new index |
| NSE sectoral-index constituents | `data/static/sector_constituents/2026-05/` (12 indices) | many-to-many, partial coverage; quarterly refresh |
| Our sector taxonomy | `data/static/zerodha_sectors.csv` (504 stocks, 30 sectors → 15 super-sectors) | one sector per stock, ~100% coverage; quarterly refresh |
| Index weights | `data/static/index_weights/<INDEX>/2026-04-30.csv` (6 indices) | used by concentration |

**Sector basis ruling: both, with distinct jobs.** NSE sectoral
*indices* (official price series, 2011+ history) power RRG mode 1 —
the market-convention view. Our Zerodha/super-sector taxonomy powers
RRG mode 2 (universe-scoped composites) and ALL stock-level grouping
(lists, screener, drill-downs) — it is the canonical per-stock sector.
The NSE `Industry` column stays as reference metadata only.

## Local dev data refresh

Same-day EOD refresh for local dev = run after market close (bars
final, 16:30 Railway pipeline already ran):

```
.venv/bin/python scripts/run_daily_pipeline.py --with-login --headless --fetch-only
.venv/bin/python scripts/sync_insights_panels.py
```

`--fetch-only` skips portfolio build / DB sync / backup (prod does
those daily anyway); the second command brings the long panels
(`nse500_data_merged/`, `indices_data_full/`) up to date. Append-only
by construction, so never run it mid-session (partial bars would
freeze into the long panels).
