"""
Build Trend Leaders 25 signals — trend-following stock selection

Two-layer system:
1. Trend Eligibility Filter: Close > 200 DMA, 50 > 200 DMA, 200 DMA rising 20d
2. Trend Quality Score (TQS): 3-component composite (locked-in May 2026)

Components (equal 1/3 weights):
  Persistence       — % of last 252 trading days Close > 100 DMA
  Drawdown Control  — (Close / 126-day rolling high) ** 2  (concave squared)
  Momentum          — 63-day return, percentile-ranked among eligible stocks

The MA-Structure and Distance-from-200 components were dropped May 2026
(redundant with eligibility / hurt CAGR by exiting winners). See
tasks/trend_leaders/DESIGN.md for full review.

Usage:
    python scripts/build_trend_leaders_signals.py
    python scripts/build_trend_leaders_signals.py --rebalance-freq biweekly
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

def compute_persistence_score(close: pd.DataFrame, sma_100: pd.DataFrame,
                               window: int = 252) -> pd.DataFrame:
    """Trend Persistence Score (0-1).

    Rolling fraction of last `window` trading days where Close > 100 DMA.
    Locked-in: 252-day window (~1 year) — long-term reliability beats
    short-term consistency. 100 DMA reference is the sweet spot.
    """
    above_100 = (close > sma_100).astype(float)
    return above_100.rolling(window=window, min_periods=window).mean()


def compute_drawdown_control_score(close: pd.DataFrame,
                                    window: int = 126) -> pd.DataFrame:
    """Drawdown Control Score (0-1) — concave (squared).

    score = clip(Close / rolling_high, 0, 1) ** 2

    Squared form penalizes deep drawdowns more sharply and rewards stocks
    near their highs. Linear form was less discriminating; cubed
    over-penalized. Locked in May 2026.
    """
    rolling_high = close.rolling(window=window, min_periods=window).max()
    ratio = (close / rolling_high).clip(0.0, 1.0)
    return ratio ** 2


def compute_momentum_score(close: pd.DataFrame,
                            eligibility: pd.DataFrame,
                            window: int = 63) -> pd.DataFrame:
    """Momentum Score (0-1) — N-day return, percentile-ranked among eligibles.

    Locked-in: 63-day window (3 months). Tested 126d/252d — all worse.
    Percentile-ranked is regime-stable (raw returns have different scales
    across bull/bear regimes).
    """
    raw = close / close.shift(window) - 1.0
    score = pd.DataFrame(np.nan, index=close.index, columns=close.columns)
    # Rank cross-sectionally per row, restricted to eligible stocks
    for date in raw.index:
        if date not in eligibility.index:
            continue
        elig = eligibility.loc[date]
        masked = raw.loc[date].where(elig).dropna()
        if len(masked) <= 1:
            continue
        ranked = masked.rank(method="average", ascending=True)
        pct = (ranked - 1) / (len(ranked) - 1)
        score.loc[date, pct.index] = pct.values
    return score


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
    persistence_score: pd.DataFrame,
    drawdown_score: pd.DataFrame,
    momentum_score: pd.DataFrame,
    eligibility: pd.DataFrame,
    weights: Tuple[float, float, float] = (1/3, 1/3, 1/3),
    rebalance_dates: pd.DatetimeIndex = None,
) -> pd.DataFrame:
    """Compute composite TQS — equal-weighted by default (1/3 each).

    Components are all 0-1 scaled so a raw weighted sum is meaningful.
    Restricted to eligible stocks (NaN elsewhere).
    """
    if rebalance_dates is None:
        rebalance_dates = eligibility.index

    tqs = pd.DataFrame(np.nan, index=rebalance_dates,
                       columns=persistence_score.columns)
    components = [persistence_score, drawdown_score, momentum_score]

    for date in rebalance_dates:
        if date not in eligibility.index:
            continue
        elig = eligibility.loc[date]
        if elig.sum() == 0:
            continue
        weighted_sum = pd.Series(0.0, index=persistence_score.columns)
        for component, weight in zip(components, weights):
            if date not in component.index:
                continue
            vals = component.loc[date].fillna(0)
            weighted_sum = weighted_sum + weight * vals
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


def derive_weekly_rebalance_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Last trading day of each week (Friday-anchored)."""
    calendar = pd.Series(index=index, data=index)
    weekly_last = calendar.resample("W-FRI").last().dropna()
    return pd.DatetimeIndex(weekly_last.values)


def derive_biweekly_rebalance_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Every other Friday (bi-weekly cadence — locked-in for TL25 entries)."""
    weekly = derive_weekly_rebalance_dates(index)
    return weekly[::2]


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
            def _g(comp_name):
                v = components[comp_name].loc[date, symbol]
                return round(v, 6) if not np.isnan(v) else np.nan
            signal_rows.append({
                "date": date,
                "rank": rank,
                "symbol": symbol,
                "score": round(score, 6),
                "persistence": _g("persistence"),
                "drawdown_control": _g("drawdown_control"),
                "momentum": _g("momentum"),
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
    top_n: int = 25,
) -> pd.DataFrame:
    """Build full audit DataFrame — all stocks per rebalance date."""
    sma_200_shifted = sma_dict["sma_200"].shift(20)
    rolling_high_126 = close.rolling(window=126, min_periods=126).max()
    drawdown_6m = close / rolling_high_126 - 1.0

    audit_frames = []
    for date in rebalance_dates:
        if date not in tqs.index or date not in eligibility.index:
            continue

        elig = eligibility.loc[date]
        scores = tqs.loc[date]
        n_eligible = int(elig.sum())

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
            "persistence_score": components["persistence"].loc[date].values,
            "drawdown_6m": drawdown_6m.loc[date].values,
            "drawdown_control_score": components["drawdown_control"].loc[date].values,
            "momentum_score": components["momentum"].loc[date].values,
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
        description="Build Trend Leaders 25 signals — trend-following stock selection"
    )
    parser.add_argument("--prices-dir", default="nse500_data", type=Path)
    parser.add_argument("--universe", default=None, type=Path,
                        help="CSV with Symbol column to limit universe")
    parser.add_argument("--output", default=Path("data/trend_leaders/signals/trend_leaders_signals.csv"), type=Path)
    parser.add_argument("--audit-output", default=Path("data/trend_leaders/signals/trend_scores_by_rebalance.csv"), type=Path)
    parser.add_argument("--top-n", type=int, default=25,
                        help="Number of stocks to select for portfolio (locked-in: 25)")
    parser.add_argument("--rank-output", type=int, default=45,
                        help="Number of stocks to output (top-N + buffer 20)")
    parser.add_argument("--rebalance-freq",
                        choices=["monthly", "biweekly", "weekly"],
                        default="biweekly",
                        help="Rebalance frequency (locked-in: biweekly)")
    parser.add_argument("--no-audit", action="store_true",
                        help="Skip audit file generation (faster)")

    # Configurable indicator parameters
    parser.add_argument("--dma-long", type=int, default=200)
    parser.add_argument("--persistence-window", type=int, default=252,
                        help="Locked-in: 252 trading days (~1 year)")
    parser.add_argument("--drawdown-window", type=int, default=126)
    parser.add_argument("--momentum-window", type=int, default=63,
                        help="Locked-in: 63 trading days (3 months)")

    # Score weights — locked-in at 1/3 each
    parser.add_argument("--w-persistence", type=float, default=1/3)
    parser.add_argument("--w-drawdown", type=float, default=1/3)
    parser.add_argument("--w-momentum", type=float, default=1/3)

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

    # Compute eligibility (using configurable long DMA)
    long_key = f"sma_{args.dma_long}"
    print(f"Computing trend eligibility (Close > {args.dma_long} DMA, "
          f"50 > {args.dma_long} DMA, {args.dma_long} rising 20d)...")
    eligibility = compute_eligibility(close, sma_dict["sma_50"], sma_dict[long_key])

    # Compute the 3 score components (locked-in May 2026)
    print("Computing score components (persistence, drawdown, momentum)...")
    persistence = compute_persistence_score(
        close, sma_dict["sma_100"], window=args.persistence_window
    )
    drawdown_control = compute_drawdown_control_score(
        close, window=args.drawdown_window
    )
    momentum = compute_momentum_score(
        close, eligibility, window=args.momentum_window
    )

    components = {
        "persistence": persistence,
        "drawdown_control": drawdown_control,
        "momentum": momentum,
    }

    # Derive rebalance dates
    if args.rebalance_freq == "weekly":
        rebalance_dates = derive_weekly_rebalance_dates(close.index)
    elif args.rebalance_freq == "biweekly":
        rebalance_dates = derive_biweekly_rebalance_dates(close.index)
    else:
        rebalance_dates = derive_monthly_rebalance_dates(close.index)
    min_date = close.index[args.dma_long + args.persistence_window]
    rebalance_dates = rebalance_dates[rebalance_dates >= min_date]
    print(f"{args.rebalance_freq.capitalize()} rebalance dates: "
          f"{len(rebalance_dates)} "
          f"({rebalance_dates[0].date()} to {rebalance_dates[-1].date()})")

    weights = (args.w_persistence, args.w_drawdown, args.w_momentum)
    print(f"TQS weights: persistence={weights[0]:.3f}, "
          f"drawdown={weights[1]:.3f}, momentum={weights[2]:.3f}")
    tqs = compute_trend_quality_score_fast(
        persistence, drawdown_control, momentum,
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
                  f"TQS={row['score']:.4f}  "
                  f"Persist={row['persistence']:.3f}  "
                  f"DD={row['drawdown_control']:.3f}  "
                  f"Mom={row['momentum']:.3f}")


if __name__ == "__main__":
    main()
