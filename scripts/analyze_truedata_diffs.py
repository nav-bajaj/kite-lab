"""Deep-dive on TrueData vs Kite close-price differences.

Pulls a long EOD history for one or two symbols, joins on date with the local
Kite file, and prints (a) summary stats, (b) the top diff days, (c) day-over-day
ratio jumps that betray differing corporate-action adjustment.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from data_pipeline.truedata_client import TrueDataClient

KITE_DIR = REPO_ROOT / "nse500_data"
OUT_DIR = REPO_ROOT / "truedata_test"


def analyze(sym: str, start: pd.Timestamp, end: pd.Timestamp, client: TrueDataClient) -> None:
    print(f"\n{'='*72}\n{sym}   {start.date()} -> {end.date()}\n{'='*72}")
    td = client.get_bars(sym, start, end, interval="EOD")
    if td.empty:
        print("  no truedata rows"); return
    td["date"] = pd.to_datetime(td["timestamp"]).dt.date
    td = td[["date", "open", "high", "low", "close", "volume"]].rename(
        columns=lambda c: f"{c}_td" if c != "date" else c)

    kite_path = KITE_DIR / f"{sym}_day.csv"
    if not kite_path.exists():
        print(f"  no kite file {kite_path}"); return
    kite = pd.read_csv(kite_path)
    kite["date"] = pd.to_datetime(kite["date"]).dt.date
    kite = kite[["date", "open", "high", "low", "close", "volume"]].rename(
        columns=lambda c: f"{c}_kt" if c != "date" else c)

    m = td.merge(kite, on="date", how="inner").sort_values("date").reset_index(drop=True)
    if m.empty:
        print("  no overlap"); return

    m["close_diff_pct"] = (m["close_td"] - m["close_kt"]) / m["close_kt"] * 100
    m["ratio"] = m["close_td"] / m["close_kt"]
    m["ratio_d"] = m["ratio"].diff()              # day-over-day jump in the ratio
    m["vol_ratio"] = m["volume_td"] / m["volume_kt"].replace(0, np.nan)

    print(f"overlap rows: {len(m)}")
    print(f"close_td/close_kt   mean={m['ratio'].mean():.6f}  "
          f"std={m['ratio'].std():.6f}  min={m['ratio'].min():.6f}  max={m['ratio'].max():.6f}")
    print(f"|diff| pct          mean={m['close_diff_pct'].abs().mean():.4f}%  "
          f"max={m['close_diff_pct'].abs().max():.4f}%")
    print(f"volume_td/volume_kt mean={m['vol_ratio'].mean():.4f}  "
          f"min={m['vol_ratio'].min():.4f}  max={m['vol_ratio'].max():.4f}")

    print("\nTop 8 days by |close_diff_pct|:")
    top = m.reindex(m["close_diff_pct"].abs().sort_values(ascending=False).index).head(8)
    print(top[["date", "close_td", "close_kt", "close_diff_pct", "ratio", "vol_ratio"]].to_string(index=False))

    print("\nTop 6 day-over-day ratio jumps (likely diff in corp-action handling):")
    jumps = m.reindex(m["ratio_d"].abs().sort_values(ascending=False).index).head(6)
    print(jumps[["date", "close_td", "close_kt", "ratio", "ratio_d", "close_diff_pct"]].to_string(index=False))

    out_path = OUT_DIR / f"{sym}_diff.csv"
    m.to_csv(out_path, index=False)
    print(f"\nfull joined series -> {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="+", default=["ITC", "INFY"])
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default=None)
    args = ap.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    OUT_DIR.mkdir(exist_ok=True)
    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end) if args.end else pd.Timestamp.now().normalize().replace(hour=15, minute=30)

    client = TrueDataClient()
    client.login()
    for sym in args.symbols:
        analyze(sym, start, end, client)


if __name__ == "__main__":
    main()
