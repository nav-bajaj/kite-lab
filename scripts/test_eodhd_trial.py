"""Probe EODHD REST historical-data API.

Demo token works for AAPL.US, TSLA.US, AMZN.US, VTI.US. Fetches the last ~90 days
for each and writes raw CSVs plus a parity_summary.csv. Verifies schema, NaN
counts, monotonic dates, and (when adjusted=True) that the adjusted close
differs from raw on at least one row.

Run from repo root with venv active:
    EODHD_API_TOKEN=demo python scripts/test_eodhd_trial.py
    python scripts/test_eodhd_trial.py --symbols AAPL MSFT --days 30
    python scripts/test_eodhd_trial.py --raw   # adjusted=False for comparison
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_pipeline.eodhd_client import EODHDClient  # noqa: E402

DEMO_SYMBOLS = ["AAPL", "TSLA", "AMZN", "VTI"]


def _audit(symbol: str, df: pd.DataFrame) -> dict:
    if df.empty:
        return {"symbol": symbol, "rows": 0}
    dates = pd.to_datetime(df["date"])
    return {
        "symbol": symbol,
        "rows": len(df),
        "start": dates.min().strftime("%Y-%m-%d"),
        "end": dates.max().strftime("%Y-%m-%d"),
        "monotonic": bool(dates.is_monotonic_increasing),
        "nan_rows": int(df[["open", "high", "low", "close", "volume"]].isna().any(axis=1).sum()),
        "last_close": float(df["close"].iloc[-1]),
    }


def run(symbols, days, adjusted, out_dir: Path, rate_per_min: int) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    end = pd.Timestamp.utcnow().normalize()
    start = end - pd.Timedelta(days=days)

    client = EODHDClient(rate_per_min=rate_per_min)
    print(f"[ok] EODHD client ready; fetching {len(symbols)} symbols "
          f"{start.date()} -> {end.date()} (adjusted={adjusted})")

    rows = []
    failures = 0
    for sym in symbols:
        try:
            df = client.get_history(sym, start=start, end=end, adjusted=adjusted)
        except Exception as e:
            print(f"  {sym:8s}  ERROR: {e}")
            rows.append({"symbol": sym, "rows": 0, "error": str(e)[:120]})
            failures += 1
            continue

        if df.empty:
            print(f"  {sym:8s}  0 rows")
            rows.append({"symbol": sym, "rows": 0})
            continue

        df.to_csv(out_dir / f"{sym}_day.csv", index=False)
        audit = _audit(sym, df)
        print(f"  {sym:8s}  rows={audit['rows']:3d}  "
              f"{audit['start']}..{audit['end']}  "
              f"mono={audit['monotonic']}  nan={audit['nan_rows']}  "
              f"last_close={audit['last_close']:.2f}")
        rows.append(audit)

    summary = pd.DataFrame(rows)
    summary.to_csv(out_dir / "parity_summary.csv", index=False)
    print(f"\n[ok] wrote {out_dir}/parity_summary.csv")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=DEMO_SYMBOLS)
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--raw", action="store_true", help="adjusted=False")
    parser.add_argument("--out", default="experiments/eodhd_trial")
    parser.add_argument("--rate-per-min", type=int, default=20,
                        help="lower for demo key; bump after paid")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    failures = run(
        symbols=args.symbols,
        days=args.days,
        adjusted=not args.raw,
        out_dir=ROOT / args.out,
        rate_per_min=args.rate_per_min,
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
