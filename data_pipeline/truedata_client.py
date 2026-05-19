"""TrueData REST historical-data client.

Auth flow per TrueData v2.6 spec:
  POST https://auth.truedata.in/token  -> bearer token (3600s validity)
  GET  https://history.truedata.in/getbars?symbol=...&from=...&to=...&interval=...

Date format for from/to is yymmddTHH:mm:ss (2-digit year).
"""
from __future__ import annotations

import datetime as dt
import io
import os
from typing import Optional

import pandas as pd
import requests

AUTH_URL = "https://auth.truedata.in/token"
HISTORY_BASE = "https://history.truedata.in"


class TrueDataAuthError(Exception):
    pass


class TrueDataAPIError(Exception):
    pass


def _fmt(ts: pd.Timestamp) -> str:
    return ts.strftime("%y%m%dT%H:%M:%S")


class TrueDataClient:
    def __init__(self, username: Optional[str] = None, password: Optional[str] = None, timeout: int = 30):
        self.username = username or os.environ.get("TRUEDATA_USER")
        self.password = password or os.environ.get("TRUEDATA_PASSWORD")
        if not self.username or not self.password:
            raise TrueDataAuthError("TRUEDATA_USER / TRUEDATA_PASSWORD not set")
        self.timeout = timeout
        self._token: Optional[str] = None
        self._token_expiry: Optional[dt.datetime] = None

    def login(self) -> str:
        # AUTH_URL is a fixed module constant — no user-controlled URL. R-017.
        resp = requests.post(  # nosemgrep: tools.security.ssrf-via-requests
            AUTH_URL,
            data={"username": self.username, "password": self.password, "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            raise TrueDataAuthError(f"auth failed [{resp.status_code}]: {resp.text}")
        body = resp.json()
        if "access_token" not in body:
            raise TrueDataAuthError(f"auth response missing access_token: {body}")
        self._token = body["access_token"]
        self._token_expiry = dt.datetime.utcnow() + dt.timedelta(seconds=int(body.get("expires_in", 3600)) - 60)
        return self._token

    def _ensure_token(self) -> str:
        if self._token and self._token_expiry and dt.datetime.utcnow() < self._token_expiry:
            return self._token
        return self.login()

    def get_bars(
        self,
        symbol: str,
        start,
        end,
        interval: str = "EOD",
        response_format: str = "csv",
    ) -> pd.DataFrame:
        """Fetch OHLCV bars. interval in {1min,2min,3min,5min,10min,15min,30min,60min,EOD}."""
        token = self._ensure_token()
        params = {
            "symbol": symbol,
            "from": _fmt(pd.Timestamp(start)),
            "to": _fmt(pd.Timestamp(end)),
            "response": response_format,
            "interval": interval,
        }
        # HISTORY_BASE is a fixed module constant; only the path varies. R-017.
        resp = requests.get(  # nosemgrep: tools.security.ssrf-via-requests
            f"{HISTORY_BASE}/getbars",
            params=params,
            headers={"Authorization": f"bearer {token}"},
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            raise TrueDataAPIError(f"getbars failed [{resp.status_code}] {symbol}: {resp.text[:200]}")
        text = resp.text.strip()
        if not text or text.lower().startswith("no data"):
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume", "oi"])
        if response_format == "csv":
            df = pd.read_csv(io.StringIO(text))
        else:
            payload = resp.json()
            records = payload.get("Records", []) or []
            df = pd.DataFrame(records, columns=["timestamp", "open", "volume", "oi", "close", "low", "high"])
        df.columns = [c.strip().lower() for c in df.columns]
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
