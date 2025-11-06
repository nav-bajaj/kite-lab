import argparse
import datetime as dt
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from kiteconnect import KiteConnect

from data_pipeline.price_client import PriceClient
from data_pipeline.storage import load_dataframe, save_dataframe
from data_pipeline.qa import validate_prices
from history_utils import to_local_naive


def init_kite():
    load_dotenv()
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise RuntimeError("Missing API_KEY in environment.")
    access_token = Path("access_token.txt").read_text().strip()
    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)
    return kite


def update_symbol(client, symbol, output_dir, interval, start, end):
    path = Path(output_dir) / f"{symbol}_{interval}.csv"
    existing = load_dataframe(path)
    fetch_start = pd.Timestamp(start)
    if not existing.empty:
        last = existing["date"].max()
        fetch_start = max(fetch_start, last + pd.Timedelta(days=1))
    df = client.fetch_history(symbol, fetch_start, end, interval=interval)
    if df.empty:
        return
    if not existing.empty:
        df = pd.concat([existing, df], ignore_index=True)
    df["date"] = to_local_naive(df["date"])
    df = df.sort_values("date").drop_duplicates(subset=["date"])
    save_dataframe(df, path)
    qa = validate_prices(path, interval)
    if qa["errors"] or qa["warnings"]:
        print(f"{symbol}: QA -> errors={qa['errors']} warnings={qa['warnings']}")


def main():
    parser = argparse.ArgumentParser(description="Update price caches for a universe")
    parser.add_argument("--symbols", nargs="+", required=True)
    parser.add_argument("--daily-dir", default="nse500_data")
    parser.add_argument("--interval", default="day")
    args = parser.parse_args()

    kite = init_kite()
    client = PriceClient(kite)
    today = dt.date.today().isoformat()
    for symbol in args.symbols:
        update_symbol(client, symbol, args.daily_dir, args.interval, "2020-01-01", today)


if __name__ == "__main__":
    main()
