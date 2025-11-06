import pandas as pd
from functools import lru_cache
from pathlib import Path

INSTRUMENTS_CSV = Path("data/instruments_full.csv")


class InstrumentNotFoundError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _load_instruments(path=INSTRUMENTS_CSV):
    if not Path(path).exists():
        raise FileNotFoundError(f"{path} not found. Run scripts/cache_instruments.py first.")
    df = pd.read_csv(path)
    required = {"tradingsymbol", "instrument_token", "exchange", "name"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"instruments CSV missing columns: {missing}")
    return df


def find_instrument(symbol, exchange_priority=None, path=INSTRUMENTS_CSV):
    df = _load_instruments(path)
    exchanges = exchange_priority or ["NSE", "BSE"]
    for exch in exchanges:
        row = df[(df["tradingsymbol"].str.upper() == symbol.upper()) & (df["exchange"] == exch)]
        if not row.empty:
            return {
                "symbol": row.iloc[0]["tradingsymbol"],
                "exchange": exch,
                "instrument_token": int(row.iloc[0]["instrument_token"]),
                "name": row.iloc[0].get("name"),
            }
    raise InstrumentNotFoundError(f"{symbol} not found in exchanges: {exchanges}")
