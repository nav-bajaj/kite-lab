"""
Build Trend Leaders 20 signals — trend-following stock selection

Uses a two-layer system:
1. Trend Eligibility Filter: Close > 200 DMA, 50 > 200 DMA, 200 DMA rising
2. Trend Quality Score (TQS): 4-component composite ranking

Components:
  30% MA Structure     — Close > 50 > 100 > 200 DMA stacking
  30% Trend Persistence — % of 63 days Close > 100 DMA
  20% Distance from 200 DMA — penalized outside 5-35% ideal zone
  20% Drawdown Control — proximity to 6-month rolling high

Usage:
    python scripts/build_trend_leaders_signals.py
    python scripts/build_trend_leaders_signals.py --scoring-mode persistence_only
"""

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from typing import Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from ta_indicators import sma


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_close_panel(data_dir: Path, universe: Optional[Set[str]] = None) -> pd.DataFrame:
    """Load daily close prices into a Date x Symbol panel."""
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


def load_universe(path: Path) -> Set[str]:
    """Load universe CSV and return set of symbols."""
    df = pd.read_csv(path)
    if "Symbol" not in df.columns:
        raise SystemExit("Universe file must contain a Symbol column")
    return set(df["Symbol"].astype(str).str.strip())


# ---------------------------------------------------------------------------
# Indicator computation
# ---------------------------------------------------------------------------

def compute_moving_averages(close: pd.DataFrame) -> dict:
    """Compute 50, 100, 200 DMA for all stocks.

    Returns dict with keys 'sma_50', 'sma_100', 'sma_200'.
    Each value is a Date x Symbol DataFrame.
    Uses DataFrame.rolling() directly (vectorized across all columns).
    """
    return {
        "sma_50": close.rolling(window=50, min_periods=50).mean(),
        "sma_100": close.rolling(window=100, min_periods=100).mean(),
        "sma_200": close.rolling(window=200, min_periods=200).mean(),
    }


# ---------------------------------------------------------------------------
# Trend eligibility filter
# ---------------------------------------------------------------------------

def compute_eligibility(close: pd.DataFrame, sma_50: pd.DataFrame,
                        sma_200: pd.DataFrame) -> pd.DataFrame:
    """Boolean Date x Symbol DataFrame. True where stock is trend-eligible.

    Rules:
      1. Close > 200 DMA
      2. 50 DMA > 200 DMA
      3. 200 DMA today > 200 DMA 20 trading days ago (slope rising)
    """
    cond1 = close > sma_200
    cond2 = sma_50 > sma_200
    cond3 = sma_200 > sma_200.shift(20)
    return cond1 & cond2 & cond3


# ---------------------------------------------------------------------------
# Score components
# ---------------------------------------------------------------------------

def compute_ma_structure_score(close: pd.DataFrame, sma_50: pd.DataFrame,
                               sma_100: pd.DataFrame, sma_200: pd.DataFrame) -> pd.DataFrame:
    """Component 1: Moving Average Structure Score (0-1).

    Binary sub-scores:
      0.25 * I(Close > 50 DMA)
    + 0.25 * I(50 DMA > 100 DMA)
    + 0.25 * I(100 DMA > 200 DMA)
    + 0.25 * I(200 DMA slope > 0)
    """
    s1 = (close > sma_50).astype(float) * 0.25
    s2 = (sma_50 > sma_100).astype(float) * 0.25
    s3 = (sma_100 > sma_200).astype(float) * 0.25
    s4 = (sma_200 > sma_200.shift(20)).astype(float) * 0.25
    return s1 + s2 + s3 + s4


def compute_persistence_score(close: pd.DataFrame, sma_100: pd.DataFrame,
                               window: int = 63) -> pd.DataFrame:
    """Component 2: Trend Persistence Score (0-1).

    Rolling fraction of last `window` trading days where Close > 100 DMA.
    """
    above_100 = (close > sma_100).astype(float)
    return above_100.rolling(window=window, min_periods=window).mean()


def compute_distance_200_score(close: pd.DataFrame,
                                sma_200: pd.DataFrame) -> pd.DataFrame:
    """Component 3: Distance from 200 DMA Score (0-1).

    Penalized scoring:
      <5% above:  ramp up (distance / 0.05)
      5-35%:      score = 1.0
      >35%:       ramp down, max(0, 1 - (d - 0.35) / 0.35)
    """
    distance = close / sma_200 - 1.0

    score = pd.DataFrame(np.nan, index=close.index, columns=close.columns)

    ramp_up = distance / 0.05
    ideal = 1.0
    ramp_down = 1.0 - (distance - 0.35) / 0.35

    score = np.where(distance < 0.05, ramp_up, ideal)
    score = np.where(distance > 0.35, ramp_down, score)
    score = np.clip(score, 0.0, 1.0)

    return pd.DataFrame(score, index=close.index, columns=close.columns)


def compute_drawdown_control_score(close: pd.DataFrame,
                                    window: int = 126) -> pd.DataFrame:
    """Component 4: Drawdown Control Score (0-1).

    score = clip(1 + (Close / rolling_high - 1), 0, 1)
         = clip(Close / rolling_high, 0, 1)
    """
    rolling_high = close.rolling(window=window, min_periods=window).max()
    score = close / rolling_high
    return score.clip(0.0, 1.0)


# ---------------------------------------------------------------------------
# Composite Trend Quality Score
# ---------------------------------------------------------------------------

def percentile_rank_eligible(values: pd.Series, eligible: pd.Series) -> pd.Series:
    """Percentile-rank values among eligible stocks (0 to 1).

    Non-eligible stocks get NaN.
    """
    masked = values.where(eligible)
    valid = masked.dropna()
    if len(valid) <= 1:
        # All get 0.5 if only one stock, or NaN if none
        return masked.where(masked.isna(), 0.5)
    ranked = valid.rank(method="average", ascending=True)
    pct = (ranked - 1) / (len(ranked) - 1)
    return pct.reindex(values.index)


def compute_trend_quality_score_fast(
    ma_score: pd.DataFrame,
    persistence_score: pd.DataFrame,
    distance_score: pd.DataFrame,
    drawdown_score: pd.DataFrame,
    eligibility: pd.DataFrame,
    weights: Tuple[float, float, float, float] = (0.30, 0.30, 0.20, 0.20),
    rebalance_dates: pd.DatetimeIndex = None,
) -> pd.DataFrame:
    """Compute composite TQS using raw component scores (all already 0-1).

    Uses raw weighted average (NOT percentile ranking) for more stable rankings.
    Percentile ranking amplifies tiny score differences and causes excessive
    month-to-month rank volatility.
    """
    if rebalance_dates is None:
        rebalance_dates = eligibility.index

    tqs = pd.DataFrame(np.nan, index=rebalance_dates, columns=ma_score.columns)

    components = [ma_score, persistence_score, distance_score, drawdown_score]

    for date in rebalance_dates:
        if date not in eligibility.index:
            continue
        elig = eligibility.loc[date]
        if elig.sum() == 0:
            continue

        weighted_sum = pd.Series(0.0, index=ma_score.columns)
        for component, weight in zip(components, weights):
            if date not in component.index:
                continue
            vals = component.loc[date].fillna(0)
            weighted_sum = weighted_sum + weight * vals

        # Only assign scores to eligible stocks
        weighted_sum = weighted_sum.where(elig)
        tqs.loc[date] = weighted_sum

    return tqs


# ---------------------------------------------------------------------------
# Rebalance dates
# ---------------------------------------------------------------------------

def derive_monthly_rebalance_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """First trading day of each month."""
    calendar = pd.Series(index=index, data=index)
    monthly_first = calendar.resample("MS").first().dropna()
    return pd.DatetimeIndex(monthly_first.values)


# ---------------------------------------------------------------------------
# Signal output
# ---------------------------------------------------------------------------

def build_signals(
    close: pd.DataFrame,
    tqs: pd.DataFrame,
    eligibility: pd.DataFrame,
    components: dict,
    rebalance_dates: pd.DatetimeIndex,
    top_n: int = 20,
    rank_output: int = 40,
) -> pd.DataFrame:
    """Build signal DataFrame (top rank_output stocks per rebalance date).

    Outputs more than top_n to support exit hysteresis in the backtest.
    The backtest uses top_n for entries and rank_output as the exit threshold.

    Returns:
        signals_df: date, rank, symbol, score, component scores, eligible_count
    """
    signal_rows = []

    for date in rebalance_dates:
        if date not in tqs.index or date not in eligibility.index:
            continue

        elig = eligibility.loc[date]
        scores = tqs.loc[date]
        n_eligible = int(elig.sum())

        # Rank eligible stocks by TQS descending — output wider band
        eligible_scores = scores.dropna().sort_values(ascending=False)
        output_n = min(rank_output, len(eligible_scores))
        selected = eligible_scores.head(output_n)

        # Build signal rows
        for rank, (symbol, score) in enumerate(selected.items(), start=1):
            signal_rows.append({
                "date": date,
                "rank": rank,
                "symbol": symbol,
                "score": round(score, 6),
                "ma_structure": round(components["ma_structure"].loc[date, symbol], 6)
                    if not np.isnan(components["ma_structure"].loc[date, symbol]) else np.nan,
                "persistence": round(components["persistence"].loc[date, symbol], 6)
                    if not np.isnan(components["persistence"].loc[date, symbol]) else np.nan,
                "distance_200": round(components["distance_200"].loc[date, symbol], 6)
                    if not np.isnan(components["distance_200"].loc[date, symbol]) else np.nan,
                "drawdown_control": round(components["drawdown_control"].loc[date, symbol], 6)
                    if not np.isnan(components["drawdown_control"].loc[date, symbol]) else np.nan,
                "eligible_count": n_eligible,
            })

    return pd.DataFrame(signal_rows)


def build_audit(
    close: pd.DataFrame,
    tqs: pd.DataFrame,
    eligibility: pd.DataFrame,
    components: dict,
    sma_dict: dict,
    rebalance_dates: pd.DatetimeIndex,
    top_n: int = 20,
) -> pd.DataFrame:
    """Build full audit DataFrame — all stocks per rebalance date.

    Uses vectorized operations (no per-symbol loops).
    """
    sma_200_shifted = sma_dict["sma_200"].shift(20)
    rolling_high_126 = close.rolling(window=126, min_periods=126).max()
    distance_200_raw = close / sma_dict["sma_200"] - 1.0
    drawdown_6m = close / rolling_high_126 - 1.0

    audit_frames = []

    for date in rebalance_dates:
        if date not in tqs.index or date not in eligibility.index:
            continue

        elig = eligibility.loc[date]
        scores = tqs.loc[date]
        n_eligible = int(elig.sum())

        # Compute ranks for eligible stocks
        eligible_scores = scores.dropna().sort_values(ascending=False)
        rank_series = pd.Series(np.nan, index=close.columns)
        for r, (sym, _) in enumerate(eligible_scores.items(), start=1):
            rank_series[sym] = r

        selected = rank_series <= top_n

        row = pd.DataFrame({
            "date": date,
            "symbol": close.columns,
            "close": close.loc[date].values,
            "sma_50": sma_dict["sma_50"].loc[date].values if date in sma_dict["sma_50"].index else np.nan,
            "sma_100": sma_dict["sma_100"].loc[date].values if date in sma_dict["sma_100"].index else np.nan,
            "sma_200": sma_dict["sma_200"].loc[date].values if date in sma_dict["sma_200"].index else np.nan,
            "sma_200_20d_ago": sma_200_shifted.loc[date].values if date in sma_200_shifted.index else np.nan,
            "eligible": elig.values,
            "ma_structure_score": components["ma_structure"].loc[date].values,
            "persistence_score": components["persistence"].loc[date].values,
            "distance_200_raw": distance_200_raw.loc[date].values,
            "distance_200_score": components["distance_200"].loc[date].values,
            "drawdown_6m": drawdown_6m.loc[date].values,
            "drawdown_control_score": components["drawdown_control"].loc[date].values,
            "trend_quality_score": scores.where(elig).values,
            "rank": rank_series.values,
            "selected": selected.values,
            "eligible_count": n_eligible,
        })
        audit_frames.append(row)

    if not audit_frames:
        return pd.DataFrame()
    return pd.concat(audit_frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build Trend Leaders 20 signals — trend-following stock selection"
    )
    parser.add_argument("--prices-dir", default="nse500_data", type=Path)
    parser.add_argument("--universe", default=None, type=Path,
                        help="CSV with Symbol column to limit universe")
    parser.add_argument("--output", default=Path("data/trend_leaders/signals/trend_leaders_signals.csv"), type=Path)
    parser.add_argument("--audit-output", default=Path("data/trend_leaders/signals/trend_scores_by_rebalance.csv"), type=Path)
    parser.add_argument("--top-n", type=int, default=20,
                        help="Number of stocks to select for portfolio")
    parser.add_argument("--rank-output", type=int, default=40,
                        help="Number of stocks to output in signals (for exit buffer)")
    parser.add_argument("--scoring-mode", choices=["composite", "persistence_only"], default="composite",
                        help="composite = full TQS, persistence_only = rank by persistence alone")
    parser.add_argument("--no-audit", action="store_true", help="Skip audit file generation (faster)")

    # Configurable indicator parameters
    parser.add_argument("--dma-short", type=int, default=50)
    parser.add_argument("--dma-medium", type=int, default=100)
    parser.add_argument("--dma-long", type=int, default=200)
    parser.add_argument("--slope-lookback", type=int, default=20)
    parser.add_argument("--persistence-window", type=int, default=63)
    parser.add_argument("--drawdown-window", type=int, default=126)
    parser.add_argument("--distance-min", type=float, default=0.05)
    parser.add_argument("--distance-max", type=float, default=0.35)

    # Score weights
    parser.add_argument("--w-ma", type=float, default=0.30)
    parser.add_argument("--w-persistence", type=float, default=0.30)
    parser.add_argument("--w-distance", type=float, default=0.20)
    parser.add_argument("--w-drawdown", type=float, default=0.20)

    args = parser.parse_args()

    # Load universe
    universe = None
    if args.universe:
        universe = load_universe(args.universe)
        print(f"Universe: {len(universe)} symbols from {args.universe}")

    # Load prices
    print(f"Loading prices from {args.prices_dir}...")
    close = load_close_panel(args.prices_dir, universe)
    close = close.ffill()
    print(f"Loaded {len(close.columns)} symbols, {len(close)} trading days "
          f"({close.index[0].date()} to {close.index[-1].date()})")

    # Compute moving averages
    print("Computing moving averages (50, 100, 200 DMA)...")
    sma_dict = compute_moving_averages(close)

    # Compute eligibility
    print("Computing trend eligibility...")
    eligibility = compute_eligibility(close, sma_dict["sma_50"], sma_dict["sma_200"])

    # Compute score components
    print("Computing score components...")
    ma_structure = compute_ma_structure_score(
        close, sma_dict["sma_50"], sma_dict["sma_100"], sma_dict["sma_200"]
    )
    persistence = compute_persistence_score(
        close, sma_dict["sma_100"], window=args.persistence_window
    )
    distance_200 = compute_distance_200_score(close, sma_dict["sma_200"])
    drawdown_control = compute_drawdown_control_score(
        close, window=args.drawdown_window
    )

    components = {
        "ma_structure": ma_structure,
        "persistence": persistence,
        "distance_200": distance_200,
        "drawdown_control": drawdown_control,
    }

    # Derive rebalance dates
    rebalance_dates = derive_monthly_rebalance_dates(close.index)
    # Filter to dates where we have enough history for 200 DMA
    min_date = close.index[args.dma_long + args.persistence_window]  # need both 200 DMA + persistence window
    rebalance_dates = rebalance_dates[rebalance_dates >= min_date]
    print(f"Monthly rebalance dates: {len(rebalance_dates)} "
          f"({rebalance_dates[0].date()} to {rebalance_dates[-1].date()})")

    # Compute TQS
    weights = (args.w_ma, args.w_persistence, args.w_distance, args.w_drawdown)
    if args.scoring_mode == "persistence_only":
        print("Scoring mode: persistence_only (ranking by trend persistence alone)")
        # Create a TQS that's just the persistence score for eligible stocks
        tqs = pd.DataFrame(np.nan, index=rebalance_dates, columns=close.columns)
        for date in rebalance_dates:
            if date not in eligibility.index:
                continue
            elig = eligibility.loc[date]
            if elig.sum() == 0:
                continue
            tqs.loc[date] = persistence.loc[date].where(elig)
    else:
        print(f"Scoring mode: composite (weights: MA={weights[0]}, "
              f"Persist={weights[1]}, Dist={weights[2]}, DD={weights[3]})")
        tqs = compute_trend_quality_score_fast(
            ma_structure, persistence, distance_200, drawdown_control,
            eligibility, weights, rebalance_dates,
        )

    # Quick eligibility stats
    for date in rebalance_dates[:3]:
        n = int(eligibility.loc[date].sum()) if date in eligibility.index else 0
        print(f"  {date.date()}: {n} eligible stocks")
    print(f"  ...")
    for date in rebalance_dates[-2:]:
        n = int(eligibility.loc[date].sum()) if date in eligibility.index else 0
        print(f"  {date.date()}: {n} eligible stocks")

    # Build signals
    print("Building signals...")
    signals_df = build_signals(
        close, tqs, eligibility, components,
        rebalance_dates, top_n=args.top_n, rank_output=args.rank_output,
    )

    # Save signals
    args.output.parent.mkdir(parents=True, exist_ok=True)
    signals_df.to_csv(args.output, index=False)
    print(f"Signals saved: {len(signals_df)} rows "
          f"({len(rebalance_dates)} months, top-{args.top_n}) → {args.output}")

    # Build and save audit (separate, heavier operation)
    if not args.no_audit:
        print("Building audit file...")
        audit_df = build_audit(
            close, tqs, eligibility, components, sma_dict,
            rebalance_dates, top_n=args.top_n,
        )
        args.audit_output.parent.mkdir(parents=True, exist_ok=True)
        audit_df.to_csv(args.audit_output, index=False)
        print(f"Audit saved: {len(audit_df)} rows → {args.audit_output}")

    # Summary stats
    if not signals_df.empty:
        print(f"\n=== Signal Summary ===")
        print(f"Date range: {signals_df['date'].min()} to {signals_df['date'].max()}")
        print(f"Rebalance months: {signals_df['date'].nunique()}")
        eligible_counts = signals_df.groupby("date")["eligible_count"].first()
        print(f"Eligible stocks: min={eligible_counts.min()}, "
              f"median={eligible_counts.median():.0f}, max={eligible_counts.max()}")
        stocks_per_month = signals_df.groupby("date").size()
        print(f"Selected per month: min={stocks_per_month.min()}, "
              f"median={stocks_per_month.median():.0f}, max={stocks_per_month.max()}")
        unique_stocks = signals_df["symbol"].nunique()
        print(f"Unique stocks selected: {unique_stocks}")

        # Show latest rebalance
        latest_date = signals_df["date"].max()
        latest = signals_df[signals_df["date"] == latest_date].head(10)
        print(f"\nTop 10 on {latest_date}:")
        for _, row in latest.iterrows():
            print(f"  #{int(row['rank']):2d} {row['symbol']:20s} "
                  f"TQS={row['score']:.4f}  MA={row['ma_structure']:.3f}  "
                  f"Persist={row['persistence']:.3f}  "
                  f"Dist200={row['distance_200']:.3f}  "
                  f"DD={row['drawdown_control']:.3f}")


if __name__ == "__main__":
    main()
