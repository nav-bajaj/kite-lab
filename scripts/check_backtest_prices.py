import argparse
from datetime import datetime
from pathlib import Path
import pandas as pd


def expected_trade_price(price_df, date):
    row = price_df.loc[price_df["date"] == pd.Timestamp(date)]
    if row.empty:
        return None, {}
    info = {}
    for col in ["open", "high", "low", "close"]:
        if col in row.columns:
            info[col] = row[col].iloc[0]
    if {"open", "high", "low", "close"}.issubset(row.columns):
        return row[["open", "high", "low", "close"]].mean(axis=1).iloc[0], info
    return row["close"].iloc[0], info


def main():
    p = argparse.ArgumentParser(description="Check trade prices vs price files and write a detailed report")
    p.add_argument("--runs", type=Path, default=Path("data/backtests/check_prices"), help="Backtest output folder")
    p.add_argument("--prices-dir", type=Path, default=Path("nse500_data"), help="Folder of *_day.csv price files")
    p.add_argument("--tolerance", type=float, default=1e-6, help="Allowed absolute diff between logged and expected")
    p.add_argument("--output-root", type=Path, default=Path("experiments"), help="Where to save the report")
    args = p.parse_args()

    trades_path = args.runs / "momentum_trades.csv"
    if not trades_path.exists():
        raise SystemExit(f"No trades file found at {trades_path}")
    trades = pd.read_csv(trades_path, parse_dates=["date"])

    rows = []
    mismatches = []
    for row in trades.itertuples(index=False):
        sym = row.symbol
        price_file = args.prices_dir / f"{sym}_day.csv"
        price_info = {}
        exp_price = None
        if price_file.exists():
            df_price = pd.read_csv(price_file, parse_dates=["date"])
            exp_price, price_info = expected_trade_price(df_price, row.date)
        diff = None
        if exp_price is not None:
            diff = row.price - exp_price
            if abs(diff) > args.tolerance:
                mismatches.append((row.date.date(), sym, row.price, exp_price))
        rows.append(
            {
                "date": row.date.date(),
                "symbol": sym,
                "side": row.side,
                "trade_price": row.price,
                "expected_price": exp_price,
                "diff": diff,
                "open": price_info.get("open"),
                "high": price_info.get("high"),
                "low": price_info.get("low"),
                "close": price_info.get("close"),
                "shares": row.shares,
                "notional": row.notional,
            }
        )

    if mismatches:
        print(f"Found {len(mismatches)} mismatches (|diff| > {args.tolerance}). See report for details.")
    else:
        print("All trade prices match expected OHLC/close within tolerance.")

    report_df = pd.DataFrame(rows)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    out_dir = args.output_root / f"price_check_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_df.to_csv(out_dir / "trade_price_check.csv", index=False)
    if mismatches:
        pd.DataFrame(mismatches, columns=["date", "symbol", "trade_price", "expected"]).to_csv(
            out_dir / "mismatches.csv", index=False
        )
    print(f"Saved detailed report to {out_dir}")


if __name__ == "__main__":
    main()
