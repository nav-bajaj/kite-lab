"""Rebuild us_equities_data/ from yfinance (adjusted daily OHLCV).

Replaces the EODHD backfill (subscription lapsed, 401; original panel was
decluttered). auto_adjust=True gives split+dividend adjusted OHLC, matching
the EODHD pre-adjusted convention closely but not exactly -- disclosed in
the study writeup. Universe: data/static/us_equities_universe.csv, class
shares normalized BRK.B -> BRK-B for Yahoo.

Output format matches the NSE loaders: <SYM>_day.csv with
date,open,high,low,close,volume (symbol name keeps the dot form so the
universe CSV keys match).

Run:
    python tasks/donchian_channel/fetch_us_yfinance.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[2]
import os
UNIVERSE_CSV = Path(os.environ.get("US_UNIVERSE_CSV",
    ROOT / "data/static/us_equities_universe.csv"))
OUT_DIR = ROOT / "us_equities_data"
START = "2008-01-01"
CHUNK = 40


def main():
    OUT_DIR.mkdir(exist_ok=True)
    uni = pd.read_csv(UNIVERSE_CSV)
    symbols = sorted(uni["Symbol"].dropna().astype(str).unique())
    ymap = {s: s.replace(".", "-") for s in symbols}
    todo = [s for s in symbols
            if not (OUT_DIR / f"{s}_day.csv").exists()
            or (OUT_DIR / f"{s}_day.csv").stat().st_size < 200]
    print(f"[fetch] {len(todo)} of {len(symbols)} symbols to fetch")

    ok = failed = 0
    for i in range(0, len(todo), CHUNK):
        batch = todo[i:i + CHUNK]
        ytickers = [ymap[s] for s in batch]
        try:
            df = yf.download(ytickers, start=START, auto_adjust=True,
                             progress=False, group_by="ticker", threads=True)
        except Exception as e:
            print(f"  batch {i//CHUNK}: download error {e}; retrying once")
            time.sleep(10)
            df = yf.download(ytickers, start=START, auto_adjust=True,
                             progress=False, group_by="ticker", threads=True)
        for s in batch:
            yt = ymap[s]
            try:
                sub = df[yt] if len(batch) > 1 else df
                sub = sub.dropna(subset=["Close"])
                if len(sub) < 50:
                    print(f"  {s}: only {len(sub)} rows, skipped")
                    failed += 1
                    continue
                out = pd.DataFrame({
                    "date": sub.index.strftime("%Y-%m-%d"),
                    "open": sub["Open"].round(4).values,
                    "high": sub["High"].round(4).values,
                    "low": sub["Low"].round(4).values,
                    "close": sub["Close"].round(4).values,
                    "volume": sub["Volume"].fillna(0).astype("int64").values,
                })
                out.to_csv(OUT_DIR / f"{s}_day.csv", index=False)
                ok += 1
            except Exception as e:
                print(f"  {s}: {e}")
                failed += 1
        print(f"  [{min(i+CHUNK, len(todo))}/{len(todo)}] ok={ok} failed={failed}")
        time.sleep(1.5)

    print(f"[done] ok={ok} failed={failed}")
    # sanity: AAPL adjustment spot-check around the 2020-08-31 4:1 split
    a = pd.read_csv(OUT_DIR / "AAPL_day.csv", parse_dates=["date"]).set_index("date")
    pre = a.loc["2020-08-28", "close"]
    post = a.loc["2020-08-31", "close"]
    print(f"[sanity] AAPL adj close 2020-08-28={pre:.2f} 2020-08-31={post:.2f} "
          f"(continuous ~= no 4x jump: {'OK' if abs(post/pre - 1) < 0.15 else 'FAIL'})")
    cov = {}
    for f in sorted(OUT_DIR.glob("*_day.csv")):
        d0 = pd.read_csv(f, nrows=1)["date"].iloc[0]
        cov[d0[:4]] = cov.get(d0[:4], 0) + 1
    print("[coverage] first-row year histogram:", dict(sorted(cov.items())))
    return 0 if failed < 30 else 1


if __name__ == "__main__":
    raise SystemExit(main())
