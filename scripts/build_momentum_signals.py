import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from typing import Optional, Set

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


def load_price_panel(data_dir: Path, universe: Optional[Set[str]] = None) -> pd.DataFrame:
    series = []
    for csv_path in sorted(data_dir.glob("*_day.csv")):
        symbol = csv_path.name.replace("_day.csv", "")
        if universe and symbol not in universe:
            continue
        df = pd.read_csv(csv_path, parse_dates=["date"])
        if df.empty or "close" not in df.columns:
            continue
        df = df[["date", "close"]].dropna()
        df["symbol"] = symbol
        series.append(df)
    if not series:
        raise RuntimeError(f"No price files found in {data_dir}")
    combined = pd.concat(series, ignore_index=True)
    pivot = combined.pivot(index="date", columns="symbol", values="close").sort_index()
    return pivot


def row_zscore(df: pd.DataFrame) -> pd.DataFrame:
    mean = df.mean(axis=1)
    std = df.std(axis=1).replace(0, np.nan)
    return df.sub(mean, axis=0).div(std, axis=0)


def compute_scores(prices: pd.DataFrame, skip_days: int, lookbacks: dict, vol_floor: float):
    prices = prices.sort_index()
    returns = prices.pct_change()
    past_prices = prices.shift(skip_days)

    zscores = []
    metrics = {}

    for label, window in lookbacks.items():
        mom = past_prices / past_prices.shift(window) - 1
        vol = returns.shift(skip_days).rolling(window).std()
        if vol_floor is not None:
            vol = vol.clip(lower=vol_floor)
        score = mom / vol
        z = row_zscore(score)
        zscores.append(z)
        metrics[f"score_{label}"] = z
        metrics[f"mom_{label}"] = mom
        metrics[f"vol_{label}"] = vol

    composite = sum(zscores) / len(zscores)
    metrics["composite"] = composite
    return metrics


def derive_rebalance_dates(index: pd.Index) -> pd.Index:
    calendar = pd.Series(index=index, data=index)
    weekly = calendar.resample("W-THU").last().dropna()
    return pd.Index(weekly)


def build_rankings(scores: dict, top_n: int, output_path: Path, lookbacks: dict):
    composite = scores["composite"].dropna(how="all")
    dates = derive_rebalance_dates(composite.index)
    rows = []
    for date in dates:
        if date not in composite.index:
            continue
        row = composite.loc[date].dropna().sort_values(ascending=False).head(top_n)
        if row.empty:
            continue
        for rank, (symbol, score) in enumerate(row.items(), start=1):
            row_data = {
                "date": date,
                "rank": rank,
                "symbol": symbol,
                "score": score,
            }
            for label in lookbacks.keys():
                row_data[f"score_{label}"] = scores[f"score_{label}"].loc[date].get(symbol, np.nan)
                row_data[f"mom_{label}"] = scores[f"mom_{label}"].loc[date].get(symbol, np.nan)
                row_data[f"vol_{label}"] = scores[f"vol_{label}"].loc[date].get(symbol, np.nan)
            rows.append(row_data)
    result = pd.DataFrame(rows)
    result.sort_values(["date", "rank"], inplace=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    print(f"Saved {len(result)} rows to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Build momentum rankings for NSE 500")
    parser.add_argument("--prices-dir", default="nse500_data", type=Path)
    parser.add_argument("--output", default=Path("data/momentum/top25_signals.csv"), type=Path)
    parser.add_argument("--skip-days", type=int, default=21, help="Skip window before measuring momentum (trading days)")
    parser.add_argument(
        "--lookbacks",
        nargs="+",
        choices=["3", "6", "12"],
        default=["6"],
        help="Momentum lookback windows in months (default L6 focus)",
    )
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--universe-file", type=Path, help="CSV with Symbol column to limit universe")
    parser.add_argument(
        "--vol-floor",
        type=float,
        default=0.0005,
        help="Lower bound for realized vol to avoid inflating scores when vol is near-zero",
    )
    args = parser.parse_args()

    universe = None
    if args.universe_file:
        df_uni = pd.read_csv(args.universe_file)
        if "Symbol" not in df_uni.columns:
            raise SystemExit("Universe file must contain a Symbol column")
        universe = set(df_uni["Symbol"].astype(str).str.strip())

    prices = load_price_panel(args.prices_dir, universe)
    lookback_map = {"12": 252, "6": 126, "3": 63}
    selected = {lbl: lookback_map[lbl] for lbl in args.lookbacks}
    scores = compute_scores(prices, args.skip_days, selected, vol_floor=args.vol_floor)
    build_rankings(scores, args.top_n, Path(args.output), selected)


if __name__ == "__main__":
    main()
