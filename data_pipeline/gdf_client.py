"""Global Datafeeds Nimble Websocket API client.

Auth flow:
  open WS to wss://nimblewebstream.lisuns.com:4576/
  send {"MessageType":"Authenticate","Password":"<api_key>"}
  expect {"Complete":true,"Message":"Welcome!","MessageType":"AuthenticateResult"}

Historical bars (single-shot reply):
  send {"MessageType":"GetHistory","Exchange":"NSE","InstrumentIdentifier":"<sym>",
        "Periodicity":"DAY","Period":1,"Max":0,"From":<unix>,"To":<unix>,
        "isShortIdentifier":"False","UserTag":"<tag>"}
  server returns ONE message of shape {"Request":{...},"Result":[{bar},...]} with bars
  newest-first. Various "Echo", "AllowVMRunningResult" keepalives can arrive in
  between and must be ignored. Errors come as MessageType="RequestError".

NOTE: API key is single-session — overlapping connections get
"Access Denied. Key already in use by other session." So always close cleanly.
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Iterable, Optional

import pandas as pd
import websockets

DEFAULT_URL = "wss://nimblewebstream.lisuns.com:4576/"
SKIP_TYPES = {"Echo", "AllowVMRunningResult", "AllowServerOSRunningResult"}


class GDFAuthError(Exception):
    pass


class GDFAPIError(Exception):
    pass


def _to_unix(ts) -> int:
    return int(pd.Timestamp(ts).timestamp())


class GDFClient:
    def __init__(self, api_key: Optional[str] = None, url: Optional[str] = None,
                 timeout: float = 30.0):
        self.api_key = api_key or os.environ.get("GDF_API_KEY")
        if not self.api_key:
            raise GDFAuthError("GDF_API_KEY not set")
        self.url = url or os.environ.get("GDF_WSS_URL") or DEFAULT_URL
        self.timeout = timeout
        self._ws = None

    async def __aenter__(self):
        self._ws = await websockets.connect(self.url, ping_interval=30, ping_timeout=30)
        await self._authenticate()
        return self

    async def __aexit__(self, *_):
        if self._ws:
            try:
                await self._ws.close()
            finally:
                self._ws = None

    async def _authenticate(self) -> None:
        await self._ws.send(json.dumps({"MessageType": "Authenticate",
                                        "Password": self.api_key}))
        # auth reply may arrive after a couple of keepalives in some cases
        for _ in range(8):
            raw = await asyncio.wait_for(self._ws.recv(), timeout=self.timeout)
            body = json.loads(raw)
            if body.get("MessageType") == "AuthenticateResult":
                if body.get("Complete"):
                    return
                raise GDFAuthError(f"auth failed: {body}")
            if body.get("MessageType") == "RequestError":
                raise GDFAuthError(f"auth error: {body}")
        raise GDFAuthError("no AuthenticateResult received")

    async def _await_result(self) -> list:
        for _ in range(120):  # up to ~120 messages of keepalive noise
            raw = await asyncio.wait_for(self._ws.recv(), timeout=self.timeout)
            msg = json.loads(raw)
            mtype = msg.get("MessageType", "")
            if mtype in SKIP_TYPES:
                continue
            if mtype == "RequestError":
                raise GDFAPIError(msg.get("Message", str(msg)))
            if "Result" in msg:
                return msg.get("Result") or []
        raise GDFAPIError("no Result message received within message budget")

    async def get_history(self, symbol: str, start, end, *,
                          exchange: str = "NSE", periodicity: str = "DAY",
                          period: int = 1, max_bars: int = 0,
                          tag: str = "probe") -> pd.DataFrame:
        """Fetch historical bars for a single instrument.

        Returns DataFrame with columns [date, open, high, low, close, volume, oi]
        sorted oldest -> newest.
        """
        req = {
            "MessageType": "GetHistory",
            "Exchange": exchange,
            "InstrumentIdentifier": symbol,
            "Periodicity": periodicity,
            "Period": period,
            "Max": max_bars,
            "From": _to_unix(start),
            "To": _to_unix(end),
            "isShortIdentifier": "False",
            "UserTag": tag,
        }
        await self._ws.send(json.dumps(req))
        bars = await self._await_result()

        if not bars:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close",
                                         "volume", "oi"])
        df = pd.DataFrame(bars)
        df["date"] = pd.to_datetime(df["LastTradeTime"], unit="s", utc=True)
        df["date"] = df["date"].dt.tz_convert("Asia/Kolkata").dt.tz_localize(None).dt.normalize()
        df = df.rename(columns={
            "Open": "open", "High": "high", "Low": "low", "Close": "close",
            "TradedQty": "volume", "OpenInterest": "oi",
        })
        cols = [c for c in ["date", "open", "high", "low", "close", "volume", "oi"]
                if c in df.columns]
        return df[cols].sort_values("date").reset_index(drop=True)

    async def get_history_many(self, symbols: Iterable[str], start, end, **kw) -> dict:
        out = {}
        for sym in symbols:
            try:
                out[sym] = await self.get_history(sym, start, end, **kw)
            except Exception as e:
                out[sym] = e
        return out
