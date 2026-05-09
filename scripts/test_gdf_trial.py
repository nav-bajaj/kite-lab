"""Probe Global Datafeeds websocket API.

Auth + GetHistory on a small basket; compare daily closes against our
existing nse500_data CSVs to gauge data parity.

Run from repo root with venv active:
    python scripts/test_gdf_trial.py --days 30
    python scripts/test_gdf_trial.py --symbols ITC ANGELONE --days 365
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_pipeline.gdf_client import GDFClient  # noqa: E402

DEFAULT_SYMBOLS = [
    "RELIANCE", "INFY", "TCS", "HDFCBANK", "ICICIBANK",
    "SBIN", "ITC", "AXISBANK", "LT", "MARUTI",
]


def _load_kite(symbol: str) -> pd.DataFrame:
    p = ROOT / "nse500_data" / f"{symbol}_day.csv"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_csv(p, parse_dates=["date"])
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    return df


def _normalise_gdf(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "date" not in df.columns:
        return df
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.tz_localize(None).dt.normalize()
    return out


async def run(symbols, start, end, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    async with GDFClient() as client:
        print(f"[ok] authenticated; fetching {len(symbols)} symbols "
              f"{start.date()} -> {end.date()}")
        for sym in symbols:
            try:
                gdf = await client.get_history(sym, start, end, exchange="NSE",
                                               periodicity="DAY", period=1)
            except Exception as e:
                print(f"  {sym:12s}  ERROR: {e}")
                rows.append({"symbol": sym, "gdf_rows": 0, "error": str(e)})
                continue

            gdf = _normalise_gdf(gdf)
            kite = _load_kite(sym)
            gdf_rows = len(gdf)

            if gdf.empty:
                print(f"  {sym:12s}  GDF returned 0 rows")
                rows.append({"symbol": sym, "gdf_rows": 0})
                continue

            # save raw
            gdf.to_csv(out_dir / f"{sym}_day.csv", index=False)

            if kite.empty:
                print(f"  {sym:12s}  GDF={gdf_rows:4d} rows  (no Kite file)")
                rows.append({"symbol": sym, "gdf_rows": gdf_rows})
                continue

            merged = gdf.merge(kite[["date", "close"]], on="date",
                               how="inner", suffixes=("_gdf", "_kite"))
            if merged.empty:
                print(f"  {sym:12s}  GDF={gdf_rows:4d}  no overlap with Kite")
                rows.append({"symbol": sym, "gdf_rows": gdf_rows, "overlap": 0})
                continue

            merged["diff_pct"] = (merged["close_gdf"] - merged["close_kite"]) / merged["close_kite"] * 100
            stats = {
                "symbol": sym,
                "gdf_rows": gdf_rows,
                "kite_rows": len(kite),
                "overlap": len(merged),
                "max_abs_diff_pct": merged["diff_pct"].abs().max(),
                "mean_abs_diff_pct": merged["diff_pct"].abs().mean(),
                "median_diff_pct": merged["diff_pct"].median(),
                "first_overlap": merged["date"].min().date(),
                "last_overlap": merged["date"].max().date(),
            }
            rows.append(stats)
            print(f"  {sym:12s}  GDF={gdf_rows:4d}  ovl={len(merged):4d}  "
                  f"max|Δ|={stats['max_abs_diff_pct']:6.2f}%  "
                  f"mean|Δ|={stats['mean_abs_diff_pct']:5.2f}%")

    summary = pd.DataFrame(rows)
    summary.to_csv(out_dir / "parity_summary.csv", index=False)
    print(f"\n[ok] wrote {out_dir / 'parity_summary.csv'}")


def main():
    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="*", default=DEFAULT_SYMBOLS)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--start", type=str, default=None,
                    help="ISO date; overrides --days")
    ap.add_argument("--end", type=str, default=None, help="ISO date; default today")
    ap.add_argument("--out", type=str, default="gdf_test")
    args = ap.parse_args()

    end = pd.Timestamp(args.end) if args.end else pd.Timestamp.today().normalize()
    start = pd.Timestamp(args.start) if args.start else end - pd.Timedelta(days=args.days)

    asyncio.run(run(args.symbols, start, end, ROOT / args.out))


if __name__ == "__main__":
    main()
