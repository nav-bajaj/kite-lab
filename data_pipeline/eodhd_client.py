"""EODHD (eodhd.com) REST historical-data client.

Endpoints used:
  GET https://eodhd.com/api/eod/{SYMBOL}.{EXCHANGE}?api_token=...&fmt=csv&from=...&to=...&order=a
  GET https://eodhd.com/api/eod-bulk-last-day/{EXCHANGE}?api_token=...&fmt=csv&date=YYYY-MM-DD

Free demo token "demo" works for AAPL.US, TSLA.US, AMZN.US, VTI.US, BTC-USD.CC, EURUSD.FOREX.
Paid token gives 30+ years of US history and full universe coverage.

EODHD returns raw OHLC plus adjusted_close and split-adjusted volume in the same row.
When adjusted=True, we scale OHL by adjusted_close/close to produce a fully pre-adjusted
panel matching the canonical (date,open,high,low,close,volume) schema used by the rest
of the pipeline.
"""
from __future__ import annotations

import io
import os
import time
from typing import Optional

import pandas as pd
import requests

BASE = "https://eodhd.com/api"
DEFAULT_EXCHANGE = "US"


class EODHDAuthError(Exception):
    pass


class EODHDAPIError(Exception):
    pass


def _fmt_date(ts) -> str:
    return pd.Timestamp(ts).strftime("%Y-%m-%d")


class EODHDClient:
    def __init__(
        self,
        api_token: Optional[str] = None,
        rate_per_min: int = 300,
        timeout: int = 30,
        exchange: str = DEFAULT_EXCHANGE,
    ):
        self.api_token = api_token or os.environ.get("EODHD_API_TOKEN")
        if not self.api_token:
            raise EODHDAuthError("EODHD_API_TOKEN not set")
        self.timeout = timeout
        self.exchange = exchange
        self.rate_per_min = max(1, int(rate_per_min))
        self._min_interval = 60.0 / self.rate_per_min
        self._last_call: float = 0.0

    def _throttle(self):
        elapsed = time.monotonic() - self._last_call
        wait = self._min_interval - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()

    def _get(self, path: str, params: dict, retries: int = 5) -> requests.Response:
        params = {**params, "api_token": self.api_token, "fmt": "csv"}
        url = f"{BASE}/{path}"
        backoff = 1.0
        last_err: Optional[str] = None
        for attempt in range(retries):
            self._throttle()
            try:
                resp = requests.get(url, params=params, timeout=self.timeout)
            except (requests.Timeout, requests.ConnectionError) as e:
                last_err = f"{type(e).__name__}: {e}"
                time.sleep(backoff)
                backoff *= 2
                continue
            if resp.status_code == 429:
                time.sleep(backoff)
                backoff *= 2
                continue
            if resp.status_code == 401:
                raise EODHDAuthError(f"auth failed [401]: {resp.text[:200]}")
            if resp.status_code == 403:
                # 403 from EODHD = symbol not on plan / demo allow-list, not a
                # bad token. Treat as API error so callers can recover.
                raise EODHDAPIError(f"forbidden [403]: {resp.text[:200]}")
            if resp.status_code != 200:
                raise EODHDAPIError(f"GET {path} [{resp.status_code}]: {resp.text[:200]}")
            return resp
        raise EODHDAPIError(f"GET {path}: retries exhausted ({last_err or 'rate-limit'})")

    def get_history(
        self,
        symbol: str,
        start=None,
        end=None,
        adjusted: bool = True,
    ) -> pd.DataFrame:
        """Fetch daily OHLCV for a single US ticker.

        Returns DataFrame with columns: date, open, high, low, close, volume.
        When adjusted=True, OHL is rescaled by adjusted_close/close per row and
        close is set to adjusted_close (volume is already split-adjusted by EODHD).
        Symbols are bare tickers (e.g. "AAPL"); ".US" suffix is appended internally.
        """
        # EODHD uses hyphen for class shares (BRK-B.US), not dot like our universe (BRK.B).
        ticker = f"{symbol.replace('.', '-')}.{self.exchange}"
        params: dict = {"order": "a"}
        if start is not None:
            params["from"] = _fmt_date(start)
        if end is not None:
            params["to"] = _fmt_date(end)

        resp = self._get(f"eod/{ticker}", params)
        text = resp.text.strip()
        if not text:
            return self._empty()

        # EODHD returns text/plain error bodies (no CSV header) on bad symbol /
        # demo-key restrictions. Detect by missing comma in first line.
        first_line = text.splitlines()[0]
        if "," not in first_line:
            raise EODHDAPIError(f"unexpected response for {ticker}: {text[:200]}")

        df = pd.read_csv(io.StringIO(text))
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        if "date" not in df.columns:
            raise EODHDAPIError(f"missing 'date' column for {ticker}: cols={list(df.columns)}")

        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        for c in ("open", "high", "low", "close", "adjusted_close", "volume"):
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")

        if adjusted and "adjusted_close" in df.columns:
            factor = df["adjusted_close"] / df["close"]
            df["open"] = df["open"] * factor
            df["high"] = df["high"] * factor
            df["low"] = df["low"] * factor
            df["close"] = df["adjusted_close"]

        df["volume"] = df["volume"].astype("Int64")
        return df[["date", "open", "high", "low", "close", "volume"]].reset_index(drop=True)

    def get_bulk_eod(self, date, exchange: Optional[str] = None) -> pd.DataFrame:
        """Fetch one day of EOD for every symbol on an exchange (single call).

        Stub for future daily-refresh use; not exercised in initial backfill.
        Returns the raw EODHD bulk schema (caller normalises).
        """
        exch = exchange or self.exchange
        resp = self._get(f"eod-bulk-last-day/{exch}", {"date": _fmt_date(date)})
        text = resp.text.strip()
        if not text or "," not in text.splitlines()[0]:
            raise EODHDAPIError(f"unexpected bulk response: {text[:200]}")
        df = pd.read_csv(io.StringIO(text))
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        return df

    @staticmethod
    def _empty() -> pd.DataFrame:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
