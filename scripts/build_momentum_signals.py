import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


def load_price_panel(data_dir: Path) -> pd.DataFrame:
    series = []
    for csv_path in sorted(data_dir.glob("*_day.csv")):
        symbol = csv_path.name.replace("_day.csv", "")
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


def compute_scores(prices: pd.DataFrame, skip_days: int, lookback_12m: int, lookback_6m: int, lookback_3m: int):
    prices = prices.sort_index()
    returns = prices.pct_change()
    past_prices = prices.shift(skip_days)

    mom12 = past_prices / past_prices.shift(lookback_12m) - 1
    mom6 = past_prices / past_prices.shift(lookback_6m) - 1
    mom3 = past_prices / past_prices.shift(lookback_3m) - 1

    vol12 = returns.shift(skip_days).rolling(lookback_12m).std()
    vol6 = returns.shift(skip_days).rolling(lookback_6m).std()
    vol3 = returns.shift(skip_days).rolling(lookback_3m).std()

    score12 = mom12 / vol12
    score6 = mom6 / vol6
    score3 = mom3 / vol3

    z12 = row_zscore(score12)
    z6 = row_zscore(score6)
    z3 = row_zscore(score3)
    composite = (z12 + z6 + z3) / 3

    return {
        "composite": composite,
        "score12": z12,
        "score6": z6,
        "score3": z3,
        "mom12": mom12,
        "mom6": mom6,
        "mom3": mom3,
        "vol12": vol12,
        "vol6": vol6,
        "vol3": vol3,
    }


def derive_rebalance_dates(index: pd.Index) -> pd.Index:
    calendar = pd.Series(index=index, data=index)
    weekly = calendar.resample("W-FRI").last().dropna()
    return pd.Index(weekly)


def build_rankings(scores: dict, top_n: int, output_path: Path):
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
            rows.append(
                {
                    "date": date,
                    "rank": rank,
                    "symbol": symbol,
                    "score": score,
                    "score_12m": scores["score12"].loc[date].get(symbol, np.nan),
                    "score_6m": scores["score6"].loc[date].get(symbol, np.nan),
                    "score_3m": scores["score3"].loc[date].get(symbol, np.nan),
                    "mom_12m": scores["mom12"].loc[date].get(symbol, np.nan),
                    "mom_6m": scores["mom6"].loc[date].get(symbol, np.nan),
                    "mom_3m": scores["mom3"].loc[date].get(symbol, np.nan),
                    "vol_12m": scores["vol12"].loc[date].get(symbol, np.nan),
                    "vol_6m": scores["vol6"].loc[date].get(symbol, np.nan),
                    "vol_3m": scores["vol3"].loc[date].get(symbol, np.nan),
                }
            )
    result = pd.DataFrame(rows)
    result.sort_values(["date", "rank"], inplace=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    print(f"Saved {len(result)} rows to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Build momentum rankings for NSE 500")
    parser.add_argument("--prices-dir", default="nse500_data", type=Path)
    parser.add_argument("--output", default=Path("data/momentum/top25_signals.csv"), type=Path)
    parser.add_argument("--skip-days", type=int, default=21)
    parser.add_argument("--lookback-12m", type=int, default=252)
    parser.add_argument("--lookback-6m", type=int, default=126)
    parser.add_argument("--lookback-3m", type=int, default=63)
    parser.add_argument("--top-n", type=int, default=25)
    args = parser.parse_args()

    prices = load_price_panel(args.prices_dir)
    scores = compute_scores(
        prices,
        args.skip_days,
        args.lookback_12m,
        args.lookback_6m,
        args.lookback_3m,
    )
    build_rankings(scores, args.top_n, Path(args.output))


if __name__ == "__main__":
    main()
