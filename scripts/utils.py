import pandas as pd

def find_token(symbol, exchange="NSE", instruments_csv="data/instruments_full.csv"):
    df = pd.read_csv(instruments_csv)
    row = df[(df["tradingsymbol"] == symbol) & (df["exchange"] == exchange)]
    if row.empty:
        raise ValueError(f"Symbol {exchange}:{symbol} not found. Did you fetch instruments?")
    return int(row.iloc[0]["instrument_token"])
