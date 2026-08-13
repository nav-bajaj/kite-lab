# Data inventory — what the new dashboard can stand on today

Audited 2026-08-13 on branch `insights_dashboard_v2`. Conclusion up front:
**almost every data asset the new dashboard needs already exists**; the gaps
are (a) a handful of index series not in the daily tracked list, (b) no
sector aggregates on the finer Zerodha taxonomy, and (c) no intraday feed
into the insight engine.

## 1. Index data (three stores; know which is live)

| Store | Role | Freshness |
|---|---|---|
| `indices_data/` (repo root) | live daily fetch, 2020→today, 40 series | daily |
| `~/Documents/stock_data/indices_data_full/` | **live long-history panel the engine reads locally** (`_paths.indices_dir()`), 143 series, 2010→today | daily via `sync_insights_panels.py` |
| `indices_data_historical/` (repo root) | the *production/Railway* name for the same panel | prod: synced by pipeline; local copy stale |

Note the inversion vs. stocks: for indices, the Documents dir is the live
long panel; the repo-root `indices_data_historical/` is the prod path name.
Hardcodes at `kite-api/app/insights/_paths.py:26`, `stress.py:82`,
`analog_finder.py:113`.

**Sectoral indices already fetched daily (23)** — includes NIFTY BANK, IT,
PHARMA, AUTO, FMCG, METAL, REALTY, ENERGY, PSU BANK, PVT BANK,
FIN SERVICE, MEDIA, HEALTHCARE, OIL AND GAS, INFRA, CONSUMPTION,
CONSR DURBL, plus broad NIFTY 50/100/500/NEXT 50/MIDCAP 150/SMLCAP 250
and INDIA VIX. History: majors from 2010-2011, NIFTY 500 from 2015.

**Frozen at 2026-05-08 (not in `tracked_indices.csv`)**: NIFTY 200,
MIDCAP 100/50, SMLCAP 100/50, MICROCAP250, TOTAL_MKT, CHEMICALS,
CAPITAL_MKT, IND_DEFENCE, RAILWAYSPSU, HOUSING, ~100 factor/thematic.
Reviving any of these = add one row (with Kite `instrument_token`) to
`data/static/tracked_indices.csv` — `scripts/fetch_indices_history.py`
is fully list-driven.

**No NSE "Nifty 250" index exists.** Our `nifty250` is a custom universe
(Nifty 100 + Midcap 150, `data/static/nifty250_universe.csv`). Any RRG
scoped to Nifty 250/500 therefore needs **constituent-built composites**,
not official indices (see RRG_SPEC.md).

## 2. Sector classification (three layers, all committed)

1. **NSE macro `Industry`** — on every `data/static/*universe.csv`
   (schema `Company Name,Industry,Symbol,Series,ISIN Code`; 20 industries
   on NSE 500).
2. **Zerodha fine sectors** — `data/static/zerodha_sectors.csv`
   (504 stocks, 30 sectors + **15 super-sectors**), loader
   `kite-api/app/insights/zerodha_sectors.py`. Refreshed quarterly by
   `scripts/fetch_zerodha_sectors.py` (≥97% coverage gate).
3. **Sector-index memberships** — `data/static/sector_constituents/2026-05/`
   (12 NSE sectoral index snapshots), loader
   `kite-api/app/insights/sector_constituents.py`.

Bonus: `data/static/index_weights/<INDEX>/2026-04-30.csv` (cap weights for
6 indices, incl. NIFTY 50 and BANK).

## 3. Stock OHLCV

- `nse500_data_merged/` — **the panel**: 534 symbols, ~17y history for 273
  of them (2009→today), split/bonus/demerger-adjusted (not dividends),
  refreshed daily by the pipeline. This is what `build_breadth_panel.py`
  and the insight engine read.
- `nse500_data_hourly/` — live 60-minute bars per symbol (already fetched;
  an underused asset for the intraday story).
- `~/Documents/stock_data/nse500_data_full/` — orphaned archive, stale
  (2026-05-12), wider universe. Do not build on it.

## 4. Indicator history panels

- `data/breadth/breadth_daily.csv` — 14 breadth metrics × 3,932 days
  (2010-06-24→2026-05-08 at last build), from
  `scripts/build_breadth_panel.py` (~90s rebuild). **This is the
  "historical breadth chart" the dashboard needs — it exists, it is just
  not rebuilt daily nor exposed via API.** Full empirical profile in
  `tasks/breadth_atlas/REPORT.md` (distributions, dwell times, extremes,
  half-lives, PCA → 2-factor structure).

## 5. Existing sector engines (and the gap)

| Module (`kite-api/app/insights/`) | What it computes |
|---|---|
| `sector_rs.py` | sector return − Nifty 50 return over 5/20/60/120/252d, ranked; 10 long-history sector indices; 5d rank delta |
| `sector_breadth.py` | per-sector constituent breadth: % above 50/100/200dma, % advancing, dispersion, RS leaders/laggards, thrust days |
| `macro.py` | index-level sector breadth aggregates |

Gap: nothing aggregates on the Zerodha 30-sector / 15-super-sector
taxonomy, and `sector_rs` is a return-difference table, not a rotation
model — no RS-Ratio/RS-Momentum pair, no trails. That is the RRG build.

## 6. Daily pipeline (context for the realtime layer)

`run_daily_pipeline.py`: login → instruments → parallel fetch (stocks ‖
indices ‖ cross-asset) → corporate actions → benchmark → portfolios →
`sync_insights_panels.py` → insight-cache clear → backup. Everything is
EOD, one shot at ~16:30 IST. `fetch_indices_history.py` re-fetches a
15-day tail each run to absorb Zerodha's preliminary-vs-final index values
(`docs/zerodha_api_index_data_issue.md`) — any intraday index capture must
respect the same caveat (intraday index values are preliminary).
