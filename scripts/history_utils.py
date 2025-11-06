import os
import time
import datetime as dt

import pandas as pd
from dotenv import load_dotenv
from kiteconnect import KiteConnect

from utils import find_token

INDIA_TZ = "Asia/Kolkata"
EXCHANGE_PRIORITY = ("NSE", "BSE")


def load_credentials():
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


def init_kite_client():
    api_key, access_token = load_credentials()
    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)
    return kite


def to_local_naive(date_series):
    dates = pd.to_datetime(date_series, errors="coerce")
    tz = getattr(dates.dt, "tz", None)
    if tz is not None:
        dates = dates.dt.tz_convert(INDIA_TZ).dt.tz_localize(None)
    return dates


def resolve_instrument_token(symbol, preferred_exchange=None):
    exchanges = []
    if preferred_exchange:
        exchanges.append(preferred_exchange)
    for exch in EXCHANGE_PRIORITY:
        if exch not in exchanges:
            exchanges.append(exch)
    last_error = None
    for exch in exchanges:
        try:
            return find_token(symbol, exchange=exch)
        except ValueError as err:
            last_error = err
    raise last_error or ValueError(f"{symbol} not found in supported exchanges: {exchanges}")


def fetch_history(kite, symbol, start, end, interval="day", exchange=None, oi=False):
    """Fetch historical candles in safe-sized chunks."""
    token = resolve_instrument_token(symbol, preferred_exchange=exchange)
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
    df["date"] = to_local_naive(df["date"])
    return df.sort_values("date").drop_duplicates(subset=["date"])


def load_symbols(csv_path, column="Symbol"):
    df = pd.read_csv(csv_path)
    if column not in df.columns:
        raise ValueError(f"'{column}' column not found in {csv_path}")
    symbols = df[column].dropna().astype(str).str.strip()
    return list(dict.fromkeys(symbols))


def default_configs(today=None, daily_dir="daily_data", hourly_dir="hourly_data"):
    today = today or dt.date.today()
    return [
        {
            "interval": "day",
            "start": pd.Timestamp("2020-01-01"),
            "end": pd.Timestamp(today.isoformat()),
            "output_dir": daily_dir,
            "suffix": "day",
            "step": pd.Timedelta(days=1),
        },
        {
            "interval": "60minute",
            "start": pd.Timestamp(today - dt.timedelta(days=90)),
            "end": pd.Timestamp(today),
            "output_dir": hourly_dir,
            "suffix": "60minute",
            "step": pd.Timedelta(minutes=60),
        },
    ]


def _fetch_with_retries(fetch_callable, symbol, max_retries, throttle_seconds):
    attempt = 0
    while True:
        try:
            return fetch_callable()
        except Exception as exc:
            message = str(exc)
            rate_limited = "Too many requests" in message or "429" in message
            if rate_limited and attempt < max_retries - 1:
                wait = max(throttle_seconds, 0.5) * (2 ** attempt)
                print(f"{symbol}: Rate limited, retrying in {wait:.1f}s ...")
                time.sleep(wait)
                attempt += 1
                continue
            raise


def download_batches(kite, symbols, configs, throttle_seconds=0.2, max_retries=3):
    overall_failures = {}
    for cfg in configs:
        os.makedirs(cfg["output_dir"], exist_ok=True)
        successes = 0
        failures = []
        start_ts = pd.Timestamp(cfg["start"])
        end_ts = pd.Timestamp(cfg["end"])
        print(f"\nFetching {cfg['interval']} data from {start_ts.date()} to {end_ts.date()} ...")

        for symbol in symbols:
            output_path = os.path.join(cfg["output_dir"], f"{symbol}_{cfg['suffix']}.csv")
            existing_df = None
            fetch_start = start_ts

            if os.path.exists(output_path):
                try:
                    existing_df = pd.read_csv(output_path)
                    if "date" in existing_df.columns and not existing_df.empty:
                        existing_df["date"] = to_local_naive(existing_df["date"])
                        last_ts = existing_df["date"].max()
                        if pd.notnull(last_ts):
                            fetch_start = max(start_ts, last_ts + cfg["step"])
                except Exception as read_exc:
                    print(f"{symbol}: Warning - could not read existing data ({read_exc}). Re-fetching all.")
                    existing_df = None
                    fetch_start = start_ts

            if fetch_start >= end_ts:
                print(f"{symbol}: Up to date, skipping")
                continue

            try:
                df = _fetch_with_retries(
                    lambda: fetch_history(
                        kite,
                        symbol,
                        fetch_start,
                        end_ts,
                        interval=cfg["interval"],
                        exchange=cfg.get("exchange"),
                        oi=cfg.get("oi", False),
                    ),
                    symbol,
                    max_retries,
                    throttle_seconds,
                )
                if df.empty:
                    print(f"{symbol}: No new data returned, skipping")
                    continue
                if existing_df is not None and not existing_df.empty:
                    df = pd.concat([existing_df, df], ignore_index=True)
                df["date"] = to_local_naive(df["date"])
                df = df.sort_values("date").drop_duplicates(subset=["date"])
                df.to_csv(output_path, index=False)
                print(f"{symbol}: Saved {len(df)} rows to {output_path}")
                successes += 1
                if throttle_seconds:
                    time.sleep(throttle_seconds)
            except Exception as exc:
                print(f"{symbol}: Failed - {exc}")
                failures.append(symbol)

        print(f"Completed {cfg['interval']}. Succeeded: {successes}, Failed: {len(failures)}")
        if failures:
            overall_failures[cfg["interval"]] = list(failures)
            print("Symbols with errors:", ", ".join(failures))

    return overall_failures
