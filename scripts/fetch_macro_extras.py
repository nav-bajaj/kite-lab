"""Stub fetch script for Phase 4.5 deferred cross-asset series.

Status: STUB — not yet implemented end-to-end. Documents the exact
endpoints / sources for USDINR, gold, US 10y, and crude so a future
session can wire them up against real APIs.

DO NOT run this as-is; it will print URLs and exit. The cross-asset
engine at `kite-api/app/insights/cross_asset.py` accepts any OHLC CSV
at the standard `indices_data_full/` location — once you've fetched a
dataset and dropped it there, the engine picks it up automatically.

Per the no-fabrication discipline in `tasks/insight_engine/RESULTS.md`,
this script writes NOTHING until real fetching code is implemented.
Use the URLs below as the source of truth for each series.
"""
from __future__ import annotations


SOURCES = {
    "usdinr": {
        "url": "https://api.stlouisfed.org/fred/series/observations?series_id=DEXINUS&api_key=<YOUR_KEY>",
        "alt_url": "RBI reference rate (daily, T-1) — https://www.rbi.org.in/Scripts/ReferenceRateArchive.aspx",
        "target_csv": "indices_data_full/USDINR.csv",
        "expected_columns": "date,close",
        "history_target": "2010-01-01 onward (for stress/regime context)",
    },
    "gold": {
        "url": "Yahoo Finance ticker GC=F (gold futures) via yfinance",
        "alt_url": "MCX gold via Kite Connect (MCXGOLDEX already in panel but only 4 months — need backfill)",
        "target_csv": "indices_data_full/GOLD_INR.csv",
        "expected_columns": "date,close",
        "history_target": "2010-01-01 onward",
    },
    "us_10y": {
        "url": "https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&api_key=<YOUR_KEY>",
        "target_csv": "indices_data_full/US_10Y.csv",
        "expected_columns": "date,close",
        "history_target": "2010-01-01 onward",
    },
    "crude": {
        "url": "https://api.stlouisfed.org/fred/series/observations?series_id=DCOILBRENTEU&api_key=<YOUR_KEY>",
        "target_csv": "indices_data_full/CRUDE_BRENT.csv",
        "expected_columns": "date,close",
        "history_target": "2010-01-01 onward",
    },
}


def main() -> None:
    print("=" * 72)
    print("STUB: cross-asset data sources for Phase 4.5")
    print("=" * 72)
    for asset, info in SOURCES.items():
        print(f"\n[{asset}]")
        for k, v in info.items():
            print(f"  {k:<22} {v}")
    print()
    print("Next steps:")
    print("1. Register a free FRED API key at https://fred.stlouisfed.org/docs/api/api_key.html")
    print("2. For each series, fetch full history, normalise to date,close CSV format")
    print("3. Drop the CSVs at the target_csv paths shown above")
    print("4. Clear the cross_asset cache:")
    print("   from app.insights.cross_asset import clear_cache; clear_cache()")
    print("5. Tests at tests/test_insights_cross_asset.py will start picking up")
    print("   the new series automatically — no engine changes needed.")


if __name__ == "__main__":
    main()
