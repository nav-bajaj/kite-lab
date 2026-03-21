import os
import time
import datetime as dt
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from dotenv import load_dotenv
from kiteconnect import KiteConnect

from utils import find_token


class RateLimiter:
    """Thread-safe rate limiter for API requests."""

    def __init__(self, requests_per_second=3):
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0
        self.lock = threading.Lock()

    def acquire(self):
        """Wait until a request can be made without exceeding rate limit."""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_request_time
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self.last_request_time = time.time()

INDIA_TZ = "Asia/Kolkata"
EXCHANGE_PRIORITY = ("NSE", "BSE")


def load_credentials():
    load_dotenv()
    api_key = os.getenv("API_KEY") or os.getenv("KITE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing API_KEY in environment. Populate .env before running this script.")

    # Check multiple locations for access_token.txt
    token_paths = ["access_token.txt", "data/access_token.txt"]
    access_token = ""
    for path in token_paths:
        if os.path.exists(path):
            with open(path) as f:
                access_token = f.read().strip()
            if access_token:
                break

    if not access_token:
        raise RuntimeError("Missing access_token.txt. Run scripts/login_and_save_token.py first.")

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

    # CRITICAL FIX: Zerodha API returns preliminary values when to_date equals
    # the target date. Adding +1 day ensures we get finalized values.
    # This affects both indices (large discrepancies) and stocks (small discrepancies).
    # See: docs/zerodha_api_index_data_issue.md
    fetch_end = end_ts + pd.Timedelta(days=1)

    chunk_days = 30 if interval != "day" else 1900
    frames = []
    cur = start_ts
    while cur < fetch_end:
        chunk_end = min(cur + pd.Timedelta(days=chunk_days), fetch_end)
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


def _fetch_with_retries(fetch_callable, symbol, max_retries, rate_limiter):
    """Fetch data with rate limiting and exponential backoff on errors."""
    attempt = 0
    while True:
        try:
            rate_limiter.acquire()
            return fetch_callable()
        except Exception as exc:
            message = str(exc)
            rate_limited = "Too many requests" in message or "429" in message
            if rate_limited and attempt < max_retries - 1:
                wait = 0.5 * (2 ** attempt)
                print(f"{symbol}: Rate limited, retrying in {wait:.1f}s ...")
                time.sleep(wait)
                attempt += 1
                continue
            raise


def _process_symbol(kite, symbol, cfg, start_ts, end_ts, lookback_days, rate_limiter, max_retries):
    """Process a single symbol - designed to run in thread pool."""
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
                    if lookback_days > 0:
                        fetch_start = max(start_ts, last_ts - pd.Timedelta(days=lookback_days))
                    else:
                        fetch_start = max(start_ts, last_ts + cfg["step"])
        except Exception as read_exc:
            print(f"{symbol}: Warning - could not read existing data ({read_exc}). Re-fetching all.")
            existing_df = None
            fetch_start = start_ts

    if fetch_start >= end_ts:
        return {"symbol": symbol, "status": "skipped", "message": "Up to date"}

    try:
        # Capture symbol in closure properly
        def do_fetch(sym=symbol, fs=fetch_start):
            return fetch_history(
                kite,
                sym,
                fs,
                end_ts,
                interval=cfg["interval"],
                exchange=cfg.get("exchange"),
                oi=cfg.get("oi", False),
            )

        df = _fetch_with_retries(do_fetch, symbol, max_retries, rate_limiter)

        if df.empty:
            return {"symbol": symbol, "status": "skipped", "message": "No new data"}

        df["date"] = to_local_naive(df["date"])

        if existing_df is not None and not existing_df.empty:
            df = pd.concat([existing_df, df], ignore_index=True)
            df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
        else:
            df = df.sort_values("date")

        df.to_csv(output_path, index=False)
        return {"symbol": symbol, "status": "success", "rows": len(df), "path": output_path}

    except Exception as exc:
        return {"symbol": symbol, "status": "failed", "error": str(exc)}


def download_batches(kite, symbols, configs, throttle_seconds=0.34, max_retries=3, max_workers=3):
    """Download historical data for symbols using parallel fetching.

    Args:
        kite: KiteConnect instance
        symbols: List of symbols to fetch
        configs: List of config dicts with interval, start, end, output_dir, suffix, step
        throttle_seconds: Ignored (kept for API compatibility), uses RateLimiter instead
        max_retries: Maximum retry attempts on rate limiting
        max_workers: Number of parallel workers (default 3 to match API rate limit)
    """
    overall_failures = {}
    rate_limiter = RateLimiter(requests_per_second=3)

    for cfg in configs:
        os.makedirs(cfg["output_dir"], exist_ok=True)
        successes = 0
        failures = []
        skipped = 0
        start_ts = pd.Timestamp(cfg["start"])
        end_ts = pd.Timestamp(cfg["end"])

        # CRITICAL FIX: Use rolling window for daily data to capture finalized values
        lookback_days = 15 if cfg["interval"] == "day" else 0

        print(f"\nFetching {cfg['interval']} data from {start_ts.date()} to {end_ts.date()} ...")
        print(f"Using {max_workers} parallel workers with rate limiting...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    _process_symbol,
                    kite, symbol, cfg, start_ts, end_ts, lookback_days, rate_limiter, max_retries
                ): symbol
                for symbol in symbols
            }

            for future in as_completed(futures):
                symbol = futures[future]
                try:
                    result = future.result()
                    if result["status"] == "success":
                        print(f"{symbol}: Saved {result['rows']} rows to {result['path']}")
                        successes += 1
                    elif result["status"] == "skipped":
                        print(f"{symbol}: {result['message']}, skipping")
                        skipped += 1
                    else:
                        print(f"{symbol}: Failed - {result['error']}")
                        failures.append(symbol)
                except Exception as exc:
                    print(f"{symbol}: Unexpected error - {exc}")
                    failures.append(symbol)

        print(f"Completed {cfg['interval']}. Succeeded: {successes}, Skipped: {skipped}, Failed: {len(failures)}")
        if failures:
            overall_failures[cfg["interval"]] = list(failures)
            print("Symbols with errors:", ", ".join(failures))

    return overall_failures
