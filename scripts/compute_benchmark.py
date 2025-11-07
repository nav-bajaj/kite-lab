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
    start = pd.Timestamp("2020-01-01")
    if not existing.empty:
        start = existing["date"].max() + pd.Timedelta(days=1)

    end = pd.Timestamp(dt.date.today())
    if start >= end:
        print("Benchmark already up to date")
        return

    fetched = client.fetch_history(SYMBOL, start, end, interval="day", preferred_exchange="NSE")
    if fetched.empty:
        print("No new benchmark data fetched")
        return

    fetched["date"] = to_local_naive(fetched["date"])
    fetched = fetched[["date", "close"]]

    combined = pd.concat([existing, fetched], ignore_index=True)
    combined = combined.drop_duplicates(subset=["date"]).sort_values("date")
    combined["ret"] = combined["close"].pct_change()
    combined["cumret"] = (1 + combined["ret"].fillna(0)).cumprod()

    combined.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved benchmark series to {OUTPUT_PATH} ({len(combined)} rows)")


if __name__ == "__main__":
    main()
