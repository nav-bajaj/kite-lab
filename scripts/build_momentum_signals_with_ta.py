"""
Build momentum signals with optional technical analysis filters

Extends the base L6 momentum ranking with configurable TA filters:
- RSI filter: Exclude overbought/oversold stocks
- Trend filter: Require price above EMA
- Volatility filter: Exclude low-ADX (choppy) stocks
- Momentum confirmation: Require MACD alignment

Usage:
    python scripts/build_momentum_signals_with_ta.py --ta-filter rsi_neutral
    python scripts/build_momentum_signals_with_ta.py --ta-filter trend_ema50
    python scripts/build_momentum_signals_with_ta.py --ta-filter adx_trending
    python scripts/build_momentum_signals_with_ta.py --ta-filter none  # baseline
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

import ta_indicators as ta


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


def compute_base_scores(prices: pd.DataFrame, skip_days: int, lookback: int, vol_floor: float, vol_power: float):
    """Compute base L6 momentum scores (no TA filters)"""
    prices = prices.sort_index()
    returns = prices.pct_change()
    past_prices = prices.shift(skip_days)

    mom = past_prices / past_prices.shift(lookback) - 1
    vol = returns.shift(skip_days).rolling(lookback).std()
    if vol_floor is not None:
        vol = vol.clip(lower=vol_floor)
    denom = vol.pow(vol_power) if vol_power is not None else vol
    score = mom / denom
    z = row_zscore(score)

    return {
        "composite": z,
        "score_6m": z,
        "mom_6m": mom,
        "vol_6m": vol,
    }


def apply_ta_filter(prices: pd.DataFrame, filter_name: str) -> pd.DataFrame:
    """
    Apply technical analysis filter to price panel

    Args:
        prices: Panel of close prices (date × symbol)
        filter_name: Name of filter to apply

    Returns:
        Boolean mask (True = pass filter, False = exclude)

    Available filters:
        - none: No filter (baseline)
        - rsi_neutral: Exclude RSI < 30 or > 70
        - rsi_bullish: Require RSI > 50
        - trend_ema20: Require price > EMA(20)
        - trend_ema50: Require price > EMA(50)
        - adx_trending: Require ADX > 25 (strong trend)
        - macd_positive: Require MACD histogram > 0
        - combined_conservative: RSI neutral + Trend EMA50 + ADX trending
        - combined_aggressive: RSI bullish + Trend EMA20 + MACD positive
    """
    if filter_name == "none":
        # No filter - all stocks pass
        return pd.DataFrame(True, index=prices.index, columns=prices.columns)

    elif filter_name == "rsi_neutral":
        # Exclude extreme RSI values
        rsi_panel = prices.apply(lambda col: ta.rsi(col, period=14))
        return (rsi_panel >= 30) & (rsi_panel <= 70)

    elif filter_name == "rsi_bullish":
        # Require bullish RSI
        rsi_panel = prices.apply(lambda col: ta.rsi(col, period=14))
        return rsi_panel > 50

    elif filter_name == "trend_ema20":
        # Price above 20-day EMA
        ema_panel = prices.apply(lambda col: ta.ema(col, span=20))
        return prices > ema_panel

    elif filter_name == "trend_ema50":
        # Price above 50-day EMA
        ema_panel = prices.apply(lambda col: ta.ema(col, span=50))
        return prices > ema_panel

    elif filter_name == "adx_trending":
        # Require strong trend (ADX > 25)
        # Note: ADX needs high/low/close, so we approximate with close only
        adx_panel = prices.apply(lambda col: _compute_adx_from_close(col))
        return adx_panel > 25

    elif filter_name == "macd_positive":
        # Require positive MACD histogram
        macd_hist_panel = prices.apply(lambda col: ta.macd(col)[2])  # histogram
        return macd_hist_panel > 0

    elif filter_name == "combined_conservative":
        # Multiple conservative filters
        rsi_panel = prices.apply(lambda col: ta.rsi(col, period=14))
        ema_panel = prices.apply(lambda col: ta.ema(col, span=50))
        adx_panel = prices.apply(lambda col: _compute_adx_from_close(col))

        rsi_ok = (rsi_panel >= 30) & (rsi_panel <= 70)
        trend_ok = prices > ema_panel
        adx_ok = adx_panel > 25

        return rsi_ok & trend_ok & adx_ok

    elif filter_name == "combined_aggressive":
        # Multiple aggressive filters
        rsi_panel = prices.apply(lambda col: ta.rsi(col, period=14))
        ema_panel = prices.apply(lambda col: ta.ema(col, span=20))
        macd_hist_panel = prices.apply(lambda col: ta.macd(col)[2])

        rsi_ok = rsi_panel > 50
        trend_ok = prices > ema_panel
        macd_ok = macd_hist_panel > 0

        return rsi_ok & trend_ok & macd_ok

    else:
        raise ValueError(f"Unknown filter: {filter_name}")


def _compute_adx_from_close(close: pd.Series) -> pd.Series:
    """
    Approximate ADX using only close prices

    Real ADX needs high/low/close. This is a simplified version using
    close-to-close ranges as a proxy.
    """
    # Use close-to-close as proxy for high-low range
    high = close
    low = close
    return ta.adx(high, low, close, period=14)


def derive_rebalance_dates(index: pd.Index) -> pd.Index:
    """Get last trading day of each week (Thursday)"""
    calendar = pd.Series(index=index, data=index)
    weekly = calendar.resample("W-THU").last().dropna()
    return pd.Index(weekly)


def build_rankings(scores: dict, ta_mask: pd.DataFrame, top_n: int, output_path: Path, lookback_label: str):
    """
    Build final rankings with TA filter applied

    Args:
        scores: Dict with composite/mom/vol series
        ta_mask: Boolean mask (True = passes TA filter)
        top_n: Number of stocks to rank
        output_path: Where to save results
        lookback_label: Label for lookback (e.g., "6m")
    """
    composite = scores["composite"].dropna(how="all")
    dates = derive_rebalance_dates(composite.index)
    rows = []

    for date in dates:
        if date not in composite.index:
            continue

        # Get scores for this date
        score_row = composite.loc[date].dropna()

        # Apply TA filter
        if date in ta_mask.index:
            mask_row = ta_mask.loc[date]
            score_row = score_row[mask_row]

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
    print(f"Saved {len(result)} rows to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Build L6 momentum rankings with TA filters")
    parser.add_argument("--prices-dir", default="nse500_data", type=Path)
    parser.add_argument("--output", default=Path("data/momentum/top25_signals_ta.csv"), type=Path)
    parser.add_argument("--skip-days", type=int, default=21)
    parser.add_argument("--lookback-months", type=int, default=6, choices=[3, 6, 12])
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--universe-file", type=Path, help="CSV with Symbol column to limit universe")
    parser.add_argument("--vol-floor", type=float, default=0.0005)
    parser.add_argument("--vol-power", type=float, default=1.0)
    parser.add_argument(
        "--ta-filter",
        default="none",
        choices=[
            "none", "rsi_neutral", "rsi_bullish",
            "trend_ema20", "trend_ema50", "adx_trending",
            "macd_positive", "combined_conservative", "combined_aggressive"
        ],
        help="Technical analysis filter to apply"
    )
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

    # Compute base momentum scores
    print(f"Computing L{args.lookback_months} momentum scores...")
    lookback_days = args.lookback_months * 21  # Approximate trading days
    scores = compute_base_scores(prices, args.skip_days, lookback_days, args.vol_floor, args.vol_power)

    # Apply TA filter
    print(f"Applying TA filter: {args.ta_filter}")
    ta_mask = apply_ta_filter(prices, args.ta_filter)
    filter_rate = ta_mask.mean().mean()
    print(f"TA filter pass rate: {filter_rate:.1%} of stock-dates")

    # Build rankings
    label = f"{args.lookback_months}m"
    build_rankings(scores, ta_mask, args.top_n, Path(args.output), label)


if __name__ == "__main__":
    main()
