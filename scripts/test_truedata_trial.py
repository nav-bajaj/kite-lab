"""Probe the TrueData trial: pull ~1 month of EOD bars for a handful of NSE
equities, save them to truedata_test/, and compare close prices against the
existing Kite-sourced files in nse500_data/ for a quick parity check.

Run:
    source .venv/bin/activate
    python scripts/test_truedata_trial.py
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from data_pipeline.truedata_client import TrueDataClient, TrueDataAPIError, TrueDataAuthError

DEFAULT_SYMBOLS = [
    "RELIANCE", "INFY", "TCS", "HDFCBANK", "ICICIBANK", "SBIN",
    "ITC", "AXISBANK", "LT", "HINDALCO", "TATAMOTORS", "MARUTI",
]

OUT_DIR = REPO_ROOT / "truedata_test"
KITE_DIR = REPO_ROOT / "nse500_data"


def parity_row(symbol: str, td_df: pd.DataFrame, kite_path: Path) -> dict:
    row = {"symbol": symbol, "td_rows": len(td_df), "kite_rows": 0,
           "overlap_days": 0, "max_close_diff_pct": None, "mean_close_diff_pct": None,
           "td_first": None, "td_last": None, "note": ""}
    if td_df.empty:
        row["note"] = "no truedata rows"
        return row
    td = td_df.copy()
    td["date"] = pd.to_datetime(td["timestamp"]).dt.date
    row["td_first"] = str(td["date"].min())
    row["td_last"] = str(td["date"].max())

    if not kite_path.exists():
        row["note"] = "no kite file"
        return row
    kite = pd.read_csv(kite_path)
    kite["date"] = pd.to_datetime(kite["date"]).dt.date
    row["kite_rows"] = len(kite)

    merged = td.merge(kite[["date", "close"]], on="date", suffixes=("_td", "_kite"))
    row["overlap_days"] = len(merged)
    if merged.empty:
        row["note"] = "no overlapping dates"
        return row
    diff_pct = ((merged["close_td"] - merged["close_kite"]).abs() / merged["close_kite"]) * 100
    row["max_close_diff_pct"] = round(float(diff_pct.max()), 4)
    row["mean_close_diff_pct"] = round(float(diff_pct.mean()), 4)
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="*", default=DEFAULT_SYMBOLS)
    parser.add_argument("--days", type=int, default=30, help="lookback window in calendar days")
    parser.add_argument("--interval", default="EOD",
                        choices=["EOD", "1min", "5min", "15min", "30min", "60min"])
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    OUT_DIR.mkdir(exist_ok=True)

    end = pd.Timestamp.now().normalize().replace(hour=15, minute=30)
    start = (end - pd.Timedelta(days=args.days)).replace(hour=9, minute=0)

    print(f"TrueData trial probe")
    print(f"  range: {start} -> {end}")
    print(f"  interval: {args.interval}")
    print(f"  symbols: {len(args.symbols)} ({', '.join(args.symbols)})")
    print()

    try:
        client = TrueDataClient()
        client.login()
        print(f"  auth OK; token acquired (user={client.username})\n")
    except TrueDataAuthError as exc:
        print(f"AUTH FAILED: {exc}")
        sys.exit(1)

    summary = []
    for sym in args.symbols:
        try:
            df = client.get_bars(sym, start, end, interval=args.interval)
        except TrueDataAPIError as exc:
            print(f"  [{sym}] ERROR: {exc}")
            summary.append({"symbol": sym, "td_rows": 0, "kite_rows": 0, "overlap_days": 0,
                            "max_close_diff_pct": None, "mean_close_diff_pct": None,
                            "td_first": None, "td_last": None, "note": f"api error: {exc}"})
            time.sleep(0.2)
            continue
        out_path = OUT_DIR / f"{sym}_{args.interval}.csv"
        df.to_csv(out_path, index=False)
        row = parity_row(sym, df, KITE_DIR / f"{sym}_day.csv") if args.interval == "EOD" else \
              {"symbol": sym, "td_rows": len(df), "kite_rows": 0, "overlap_days": 0,
               "max_close_diff_pct": None, "mean_close_diff_pct": None,
               "td_first": str(df["timestamp"].min()) if not df.empty else None,
               "td_last": str(df["timestamp"].max()) if not df.empty else None,
               "note": "intraday: parity skipped"}
        summary.append(row)
        msg = f"  [{sym}] {row['td_rows']} td rows"
        if args.interval == "EOD":
            msg += f", overlap={row['overlap_days']}, max_diff={row['max_close_diff_pct']}%, mean_diff={row['mean_close_diff_pct']}%"
        if row["note"]:
            msg += f"  ({row['note']})"
        print(msg)
        time.sleep(0.15)  # well under the 10/sec REST limit

    summary_df = pd.DataFrame(summary)
    summary_path = OUT_DIR / "parity_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    print(f"\nWrote per-symbol CSVs and {summary_path}")

    if args.interval == "EOD" and not summary_df.empty:
        ok = summary_df["overlap_days"].fillna(0).gt(0).sum()
        print(f"Symbols with overlap vs Kite: {ok}/{len(summary_df)}")
        good = summary_df["max_close_diff_pct"].dropna()
        if not good.empty:
            print(f"Worst max-close-diff across symbols: {good.max()}%   median: {good.median()}%")


if __name__ == "__main__":
    main()
