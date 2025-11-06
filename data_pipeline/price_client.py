import datetime as dt
from typing import Iterable, Optional

import pandas as pd
from kiteconnect import KiteConnect

from .symbol_resolver import find_instrument


class PriceClient:
    def __init__(self, kite: KiteConnect):
        self.kite = kite

    def fetch_history(
        self,
        symbol: str,
        start,
        end,
        interval: str = "day",
        preferred_exchange: Optional[str] = None,
        oi: bool = False,
        chunk_days: Optional[int] = None,
    ) -> pd.DataFrame:
        info = find_instrument(symbol, exchange_priority=[preferred_exchange] if preferred_exchange else None)
        token = info["instrument_token"]
        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)

        if chunk_days is None:
            chunk_days = 30 if interval != "day" else 1900

        frames = []
        cur = start_ts
        while cur < end_ts:
            chunk_end = min(cur + pd.Timedelta(days=chunk_days), end_ts)
            candles = self.kite.historical_data(
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
        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date").drop_duplicates(subset=["date"])
