import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd


def analyze_symbol(csv_path: Path) -> dict:
    df = pd.read_csv(csv_path, parse_dates=["date"])
    if df.empty or "close" not in df.columns:
        return {}
    df = df.sort_values("date")
    start_price = df["close"].iloc[0]
    end_price = df["close"].iloc[-1]
    if start_price <= 0 or end_price <= 0:
        return {}
    total_return = end_price / start_price - 1
    days = (df["date"].iloc[-1] - df["date"].iloc[0]).days
    years = max(days / 365.25, 1e-6)
    cagr = (1 + total_return) ** (1 / years) - 1
    return {
        "symbol": csv_path.stem.replace("_day", ""),
        "start": df["date"].iloc[0].date(),
        "end": df["date"].iloc[-1].date(),
        "start_price": start_price,
        "end_price": end_price,
        "total_return": total_return,
        "cagr": cagr,
    }


def main():
    parser = argparse.ArgumentParser(description="Top 25 NSE 500 symbols by performance (total return and CAGR)")
    parser.add_argument("--prices-dir", type=Path, default=Path("nse500_data"), help="Directory containing *_day.csv files")
    parser.add_argument("--output-root", type=Path, default=Path("experiments"), help="Root folder to save results")
    args = parser.parse_args()

    results = []
    for csv_path in sorted(args.prices_dir.glob("*_day.csv")):
        info = analyze_symbol(csv_path)
        if info:
            results.append(info)

    if not results:
        raise SystemExit(f"No valid price files found in {args.prices_dir}")

    df = pd.DataFrame(results)
    df.sort_values("cagr", ascending=False, inplace=True)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    out_dir = args.output_root / f"top25_performance_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(out_dir / "all_symbols.csv", index=False)
    df.head(25).to_csv(out_dir / "top25.csv", index=False)

    print(f"Saved {len(df)} symbols. Top 25 written to {out_dir / 'top25.csv'}")


if __name__ == "__main__":
    main()
