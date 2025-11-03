import os
from functools import lru_cache

import pandas as pd

@lru_cache(maxsize=None)
def _load_instruments(instruments_csv):
    if not os.path.exists(instruments_csv):
        raise FileNotFoundError(
            f"{instruments_csv} not found. Run scripts/cache_instruments.py to fetch the latest instruments."
        )
    return pd.read_csv(instruments_csv)

def find_token(symbol, exchange="NSE", instruments_csv="data/instruments_full.csv"):
    df = _load_instruments(instruments_csv)
    row = df[(df["tradingsymbol"] == symbol) & (df["exchange"] == exchange)]
    if row.empty:
        raise ValueError(f"Symbol {exchange}:{symbol} not found. Did you fetch instruments?")
    return int(row.iloc[0]["instrument_token"])
