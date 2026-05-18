"""Shared loaders for price panels and benchmark series.

Extracted from scripts/backtest_momentum.py during Phase 3.2. The
original module still re-exports these names so existing callers keep
working without import changes.

Two functions live here:
- `load_price_panels(prices_dir)` -> (close_panel, trade_panel)
  Reads every `<symbol>_day.csv` under `prices_dir`, pivots into wide
  panels, ffills, and returns (close, OHLC/4-mean trade).
- `load_benchmark(path)` -> pd.Series
  Reads a single benchmark CSV and returns the ffilled close series.
"""
from pathlib import Path

import pandas as pd


def load_price_panels(prices_dir: Path):
    rows = []
    for csv_path in sorted(prices_dir.glob("*_day.csv")):
        symbol = csv_path.stem.replace("_day", "")
        df = pd.read_csv(csv_path, parse_dates=["date"])
        if df.empty or "close" not in df.columns:
            continue
        df["symbol"] = symbol
        if {"open", "high", "low", "close"}.issubset(df.columns):
            df["trade_price"] = df[["open", "high", "low", "close"]].mean(axis=1)
        else:
            df["trade_price"] = df["close"]
        rows.append(df[["date", "symbol", "close", "trade_price"]])
    if not rows:
        raise RuntimeError(f"No price files found in {prices_dir}")
    combined = pd.concat(rows, ignore_index=True)
    close_panel = combined.pivot(index="date", columns="symbol", values="close").sort_index()
    trade_panel = combined.pivot(index="date", columns="symbol", values="trade_price").sort_index()
    close_panel = close_panel.ffill()
    trade_panel = trade_panel.ffill()
    return close_panel, trade_panel


def load_benchmark(path: Path):
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date")
    df = df.set_index("date")
    return df["close"].ffill()
