import os
import datetime as dt

import pandas as pd
from dotenv import load_dotenv
from kiteconnect import KiteConnect

from utils import find_token

INDIA_TZ = "Asia/Kolkata"


def _load_credentials():
    load_dotenv()
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise RuntimeError("Missing API_KEY in environment. Populate .env before running this script.")

    access_token_path = "access_token.txt"
    if not os.path.exists(access_token_path):
        raise RuntimeError("Missing access_token.txt. Run scripts/login_and_save_token.py first.")

    with open(access_token_path) as f:
        access_token = f.read().strip()
    if not access_token:
        raise RuntimeError("access_token.txt is empty. Re-run scripts/login_and_save_token.py to refresh the token.")

    return api_key, access_token


def _init_client():
    api_key, access_token = _load_credentials()
    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)
    return kite


def fetch_history(kite, symbol, start, end, interval="day", exchange="NSE", oi=False):
    """Fetch historical candles in safe-sized chunks."""
    token = find_token(symbol, exchange=exchange)
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)

    chunk_days = 30 if interval != "day" else 1900
    frames = []
    cur = start_ts
    while cur < end_ts:
        chunk_end = min(cur + pd.Timedelta(days=chunk_days), end_ts)
        candles = kite.historical_data(
            instrument_token=token,
            from_date=cur.to_pydatetime(),
            to_date=chunk_end.to_pydatetime(),
            interval=interval,
            continuous=False,
            oi=oi,
        )
        if candles:
            frames.append(pd.DataFrame(candles))
        cur = chunk_end
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df["date"] = _to_local_naive(df["date"])
    return df.sort_values("date").drop_duplicates(subset=["date"])


def load_symbols(csv_path="ind_niftynext50list.csv"):
    df = pd.read_csv(csv_path)
    if "Symbol" not in df.columns:
        raise ValueError(f"'Symbol' column not found in {csv_path}")
    # Drop NA and ensure uniqueness while preserving order
    symbols = df["Symbol"].dropna().astype(str).str.strip()
    return list(dict.fromkeys(symbols))


def _to_local_naive(date_series):
    dates = pd.to_datetime(date_series, errors="coerce")
    tz = getattr(dates.dt, "tz", None)
    if tz is not None:
        dates = dates.dt.tz_convert(INDIA_TZ).dt.tz_localize(None)
    return dates


def main():
    kite = _init_client()
    symbols = load_symbols()
    if not symbols:
        print("No symbols found in ind_niftynext50list.csv")
        return
    today = dt.date.today()

    # Per Kite Connect historical data docs:
    # - Daily candles cover ~2000 trading days.
    # - Intraday (<=60minute) candles cover the last 90 calendar days.
    configs = [
        {
            "interval": "day",
            "start": pd.Timestamp("2020-01-01"),
            "end": pd.Timestamp(today.isoformat()),
            "output_dir": "next50_data",
            "suffix": "day",
            "step": pd.Timedelta(days=1),
        },
        {
            "interval": "60minute",
            "start": pd.Timestamp(today - dt.timedelta(days=90)),
            "end": pd.Timestamp(today),
            "output_dir": "next50_data_hourly",
            "suffix": "60minute",
            "step": pd.Timedelta(minutes=60),
        },
    ]

    overall_failures = {}

    for cfg in configs:
        os.makedirs(cfg["output_dir"], exist_ok=True)
        successes = 0
        failures = []
        print(
            f"\nFetching {cfg['interval']} data from {cfg['start'].date()} to {cfg['end'].date()} ..."
        )

        for symbol in symbols:
            output_path = os.path.join(cfg["output_dir"], f"{symbol}_{cfg['suffix']}.csv")
            existing_df = None
            fetch_start = cfg["start"]

            if os.path.exists(output_path):
                try:
                    existing_df = pd.read_csv(output_path)
                    if "date" in existing_df.columns and not existing_df.empty:
                        existing_df["date"] = _to_local_naive(existing_df["date"])
                        last_ts = existing_df["date"].max()
                        if pd.notnull(last_ts):
                            fetch_start = max(cfg["start"], last_ts + cfg["step"])
                except Exception as read_exc:
                    print(f"{symbol}: Warning - could not read existing data ({read_exc}). Re-fetching all.")
                    existing_df = None
                    fetch_start = cfg["start"]

            if fetch_start >= cfg["end"]:
                print(f"{symbol}: Up to date, skipping")
                continue

            try:
                df = fetch_history(
                    kite,
                    symbol,
                    fetch_start,
                    cfg["end"],
                    interval=cfg["interval"],
                )
                if df.empty:
                    print(f"{symbol}: No new data returned, skipping")
                    continue
                if existing_df is not None and not existing_df.empty:
                    df = pd.concat([existing_df, df], ignore_index=True)
                df["date"] = _to_local_naive(df["date"])
                df = df.sort_values("date").drop_duplicates(subset=["date"])
                df.to_csv(output_path, index=False)
                print(f"{symbol}: Saved {len(df)} rows to {output_path}")
                successes += 1
            except Exception as exc:
                print(f"{symbol}: Failed - {exc}")
                failures.append(symbol)

        print(f"Completed {cfg['interval']}. Succeeded: {successes}, Failed: {len(failures)}")
        if failures:
            overall_failures[cfg["interval"]] = list(failures)
            print("Symbols with errors:", ", ".join(failures))

    if overall_failures:
        print("\nSummary of failures:")
        for interval, symbols_with_error in overall_failures.items():
            print(f"{interval}: {', '.join(symbols_with_error)}")


if __name__ == "__main__":
    main()
