import datetime as dt
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from data_pipeline.price_client import PriceClient
from history_utils import init_kite_client, to_local_naive


BENCH_DIR = Path("data/benchmarks")
BENCH_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = BENCH_DIR / "nifty100.csv"
SYMBOL = "NIFTY 100"


def load_existing(path: Path) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path, parse_dates=["date"])
    return pd.DataFrame()


def main():
    kite = init_kite_client()
    client = PriceClient(kite)

    existing = load_existing(OUTPUT_PATH)

    # CRITICAL FIX: Zerodha API returns different values for indices when fetching
    # single days vs ranges. Single-day fetches return preliminary values that
    # get revised. Always re-fetch last 30 days to get finalized values.
    # See: docs/zerodha_api_index_data_issue.md
    LOOKBACK_DAYS = 30

    start = pd.Timestamp("2020-01-01")
    if not existing.empty:
        # Re-fetch last N days to capture revised/finalized values
        start = max(
            pd.Timestamp("2020-01-01"),
            existing["date"].max() - pd.Timedelta(days=LOOKBACK_DAYS)
        )
        print(f"Re-fetching last {LOOKBACK_DAYS} days to ensure finalized values")

    end = pd.Timestamp(dt.date.today())

    # CRITICAL FIX: For indices, must fetch with to_date = today + 1 day
    # Otherwise API returns preliminary values instead of finalized values
    # See: docs/zerodha_api_index_data_issue.md
    fetch_end = end + pd.Timedelta(days=1)

    if start >= end:
        print("Benchmark already up to date")
        return

    print(f"Fetching benchmark data from {start.date()} to {end.date()} (API to_date={fetch_end.date()})")
    fetched = client.fetch_history(SYMBOL, start, fetch_end, interval="day", preferred_exchange="NSE")
    if fetched.empty:
        print("No new benchmark data fetched")
        return

    fetched["date"] = to_local_naive(fetched["date"])
    fetched = fetched[["date", "close"]]

    # Merge with existing, keeping newer (more finalized) values for duplicates
    combined = pd.concat([existing, fetched], ignore_index=True)
    combined = combined.drop_duplicates(subset=["date"], keep="last").sort_values("date")

    # Recompute returns and cumulative returns
    combined["ret"] = combined["close"].pct_change()
    combined["cumret"] = (1 + combined["ret"].fillna(0)).cumprod()

    combined.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved benchmark series to {OUTPUT_PATH} ({len(combined)} rows)")

    # Show sample of recent data
    if len(combined) >= 5:
        print("\nLast 5 days:")
        print(combined.tail(5)[["date", "close"]].to_string(index=False))


if __name__ == "__main__":
    main()
