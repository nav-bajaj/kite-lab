"""
Build momentum signals with flexible lookback periods and rebalance frequencies

Supports:
- Lookback periods: 6, 9, or 12 months
- Rebalance frequencies: 1, 2, 3, or 4 weeks

Usage:
    python scripts/build_momentum_signals_flexible.py --lookback-months 9 --rebalance-weeks 2
"""

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
    """Load all price files into a single panel"""
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
    """Compute cross-sectional z-scores"""
    mean = df.mean(axis=1)
    std = df.std(axis=1).replace(0, np.nan)
    return df.sub(mean, axis=0).div(std, axis=0)


def compute_scores(prices: pd.DataFrame, skip_days: int, lookback_days: int, vol_floor: float, vol_power: float):
    """Compute momentum scores with specified lookback"""
    prices = prices.sort_index()
    returns = prices.pct_change()
    past_prices = prices.shift(skip_days)

    mom = past_prices / past_prices.shift(lookback_days) - 1
    vol = returns.shift(skip_days).rolling(lookback_days).std()
    if vol_floor is not None:
        vol = vol.clip(lower=vol_floor)
    denom = vol.pow(vol_power) if vol_power is not None else vol
    score = mom / denom
    z = row_zscore(score)

    lookback_months = lookback_days // 21
    label = f"{lookback_months}m"

    return {
        "composite": z,
        f"score_{label}": z,
        f"mom_{label}": mom,
        f"vol_{label}": vol,
    }, label


def derive_rebalance_dates(index: pd.Index, rebalance_weeks: int) -> pd.Index:
    """
    Get rebalance dates based on frequency

    Args:
        index: DatetimeIndex of trading days
        rebalance_weeks: Rebalance every N weeks (1-12)

    Returns:
        DatetimeIndex of rebalance dates
    """
    calendar = pd.Series(index=index, data=index)

    if rebalance_weeks == 1:
        # Weekly on Thursday
        rebal = calendar.resample("W-THU").last().dropna()
    elif rebalance_weeks <= 3:
        # 2-3 weeks: sample every Nth week
        weekly = calendar.resample("W-THU").last().dropna()
        rebal = weekly.iloc[::rebalance_weeks]
    elif rebalance_weeks == 4:
        # Monthly (every 4 weeks, approximately)
        rebal = calendar.resample("ME").last().dropna()
    elif rebalance_weeks <= 12:
        # 5-12 weeks: sample every Nth week
        weekly = calendar.resample("W-THU").last().dropna()
        rebal = weekly.iloc[::rebalance_weeks]
    else:
        raise ValueError(f"Unsupported rebalance_weeks: {rebalance_weeks} (must be 1-12)")

    return pd.Index(rebal)


def build_rankings(scores: dict, top_n: int, output_path: Path, lookback_label: str, rebalance_weeks: int):
    """
    Build final rankings

    Args:
        scores: Dict with composite/mom/vol series
        top_n: Number of stocks to rank
        output_path: Where to save results
        lookback_label: Label for lookback (e.g., "6m")
        rebalance_weeks: Rebalancing frequency
    """
    composite = scores["composite"].dropna(how="all")
    dates = derive_rebalance_dates(composite.index, rebalance_weeks)
    rows = []

    for date in dates:
        if date not in composite.index:
            continue

        # Get scores for this date
        score_row = composite.loc[date].dropna()

        # Sort and take top N
        score_row = score_row.sort_values(ascending=False).head(top_n)

        if score_row.empty:
            continue

        for rank, (symbol, score) in enumerate(score_row.items(), start=1):
            row_data = {
                "date": date,
                "rank": rank,
                "symbol": symbol,
                "score": score,
                f"score_{lookback_label}": scores[f"score_{lookback_label}"].loc[date].get(symbol, np.nan),
                f"mom_{lookback_label}": scores[f"mom_{lookback_label}"].loc[date].get(symbol, np.nan),
                f"vol_{lookback_label}": scores[f"vol_{lookback_label}"].loc[date].get(symbol, np.nan),
            }
            rows.append(row_data)

    result = pd.DataFrame(rows)
    result.sort_values(["date", "rank"], inplace=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    print(f"Saved {len(result)} rows ({len(dates)} rebalance dates) to {output_path}")
    return len(dates)


def main():
    parser = argparse.ArgumentParser(description="Build momentum rankings with flexible lookback/rebalance")
    parser.add_argument("--prices-dir", default="nse500_data", type=Path)
    parser.add_argument("--output", default=Path("data/momentum/signals_flexible.csv"), type=Path)
    parser.add_argument("--skip-days", type=int, default=21)
    parser.add_argument(
        "--lookback-months",
        type=int,
        default=6,
        help="Momentum lookback period in months (1-12)"
    )
    parser.add_argument(
        "--rebalance-weeks",
        type=int,
        default=1,
        help="Rebalance frequency in weeks (1-12, 1=weekly, 4≈monthly)"
    )
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--universe-file", type=Path, help="CSV with Symbol column to limit universe")
    parser.add_argument("--vol-floor", type=float, default=0.0005)
    parser.add_argument("--vol-power", type=float, default=1.0)
    args = parser.parse_args()

    # Load universe
    universe = None
    if args.universe_file:
        df_uni = pd.read_csv(args.universe_file)
        if "Symbol" not in df_uni.columns:
            raise SystemExit("Universe file must contain a Symbol column")
        universe = set(df_uni["Symbol"].astype(str).str.strip())

    # Load prices
    print(f"Loading prices from {args.prices_dir}...")
    prices = load_price_panel(args.prices_dir, universe)
    print(f"Loaded {len(prices.columns)} symbols, {len(prices)} trading days")

    # Compute momentum scores
    lookback_days = args.lookback_months * 21  # Approximate trading days per month
    print(f"Computing L{args.lookback_months} momentum scores...")
    scores, label = compute_scores(prices, args.skip_days, lookback_days, args.vol_floor, args.vol_power)

    # Build rankings
    print(f"Building rankings with {args.rebalance_weeks}-week rebalance frequency...")
    num_rebalances = build_rankings(scores, args.top_n, Path(args.output), label, args.rebalance_weeks)
    print(f"Total rebalance events: {num_rebalances}")


if __name__ == "__main__":
    main()
