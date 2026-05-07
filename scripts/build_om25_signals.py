"""
Build OM25 signals — Omega Ratio stock ranking

Computes rolling Omega Ratio for each stock and ranks by return asymmetry.

Usage:
    python scripts/build_om25_signals.py
    python scripts/build_om25_signals.py --lookback 126 --no-return-filter
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


def load_close_panel(data_dir: Path, universe: Optional[Set[str]] = None) -> pd.DataFrame:
    """Load daily close prices into Date x Symbol panel."""
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
    df = pd.read_csv(path)
    return set(df["Symbol"].astype(str).str.strip())


def compute_omega_signals(
    close: pd.DataFrame,
    lookback: int = 252,
    min_obs: int = 220,
    threshold: float = 0.0,
    omega_cap: float = 10.0,
    require_positive_return: bool = True,
    rebalance_dates: pd.DatetimeIndex = None,
    ranking_method: str = "pure_omega",
    top_n: int = 25,
) -> tuple:
    """Compute Omega Ratio signals on rebalance dates.

    Returns (signals_df, audit_df).
    """
    returns = close.pct_change()

    if rebalance_dates is None:
        cal = pd.Series(index=close.index, data=close.index)
        rebalance_dates = pd.DatetimeIndex(cal.resample("MS").first().dropna().values)

    # Filter dates with enough history
    min_date = close.index[lookback + 1]
    rebalance_dates = rebalance_dates[rebalance_dates >= min_date]

    signal_rows = []
    audit_rows = []

    for date in rebalance_dates:
        if date not in returns.index:
            continue

        # Get lookback window of returns ending on this date
        date_idx = returns.index.get_loc(date)
        start_idx = max(0, date_idx - lookback + 1)
        window_returns = returns.iloc[start_idx:date_idx + 1]

        # Get lookback prices for total return
        price_start_idx = max(0, close.index.get_loc(date) - lookback)
        prices_start = close.iloc[price_start_idx]
        prices_end = close.loc[date]

        eligible_stocks = []

        for symbol in close.columns:
            sym_returns = window_returns[symbol].dropna()
            valid_obs = len(sym_returns)

            # Eligibility check: minimum observations
            if valid_obs < min_obs:
                audit_rows.append({
                    "date": date, "symbol": symbol, "eligible": False,
                    "reason": "insufficient_obs", "valid_obs": valid_obs,
                    "raw_omega": np.nan, "omega_capped": np.nan,
                })
                continue

            # Total return over lookback
            p_start = prices_start.get(symbol, np.nan)
            p_end = prices_end.get(symbol, np.nan)
            if pd.isna(p_start) or pd.isna(p_end) or p_start <= 0:
                audit_rows.append({
                    "date": date, "symbol": symbol, "eligible": False,
                    "reason": "missing_price", "valid_obs": valid_obs,
                    "raw_omega": np.nan, "omega_capped": np.nan,
                })
                continue

            total_return = p_end / p_start - 1

            # Positive return filter
            if require_positive_return and total_return <= 0:
                audit_rows.append({
                    "date": date, "symbol": symbol, "eligible": False,
                    "reason": "negative_return", "valid_obs": valid_obs,
                    "total_return": total_return,
                    "raw_omega": np.nan, "omega_capped": np.nan,
                })
                continue

            # Compute Omega Ratio
            gains = (sym_returns[sym_returns > threshold] - threshold).sum()
            losses = (threshold - sym_returns[sym_returns < threshold]).sum()

            if losses <= 1e-12:
                raw_omega = omega_cap
            else:
                raw_omega = gains / losses

            omega_capped = min(raw_omega, omega_cap)

            # Downside deviation
            downside_returns = np.minimum(sym_returns.values - threshold, 0)
            downside_dev = np.sqrt(np.mean(downside_returns ** 2))

            eligible_stocks.append({
                "symbol": symbol,
                "valid_obs": valid_obs,
                "total_return": total_return,
                "raw_omega": raw_omega,
                "omega_capped": omega_capped,
                "downside_dev": downside_dev,
            })

            audit_rows.append({
                "date": date, "symbol": symbol, "eligible": True, "reason": "eligible",
                "valid_obs": valid_obs, "total_return": total_return,
                "raw_omega": raw_omega, "omega_capped": omega_capped,
                "downside_dev": downside_dev,
            })

        if not eligible_stocks:
            continue

        elig_df = pd.DataFrame(eligible_stocks)
        n_eligible = len(elig_df)

        # Ranking
        if ranking_method == "omega_quality":
            # Percentile ranks among eligible
            elig_df["omega_rank"] = elig_df["omega_capped"].rank(ascending=True, method="average") / len(elig_df)
            elig_df["return_rank"] = elig_df["total_return"].rank(ascending=True, method="average") / len(elig_df)
            elig_df["dd_rank"] = elig_df["downside_dev"].rank(ascending=False, method="average") / len(elig_df)  # lower is better
            elig_df["quality_score"] = 0.60 * elig_df["omega_rank"] + 0.20 * elig_df["return_rank"] + 0.20 * elig_df["dd_rank"]
            elig_df = elig_df.sort_values("quality_score", ascending=False)
        else:
            # Pure omega — tiebreaker: total return desc, then downside dev asc
            elig_df = elig_df.sort_values(
                ["omega_capped", "total_return", "downside_dev"],
                ascending=[False, False, True]
            )

        # Select top N
        selected = elig_df.head(top_n)

        for rank, (_, row) in enumerate(selected.iterrows(), start=1):
            signal_rows.append({
                "date": date,
                "rank": rank,
                "symbol": row["symbol"],
                "omega_capped": round(row["omega_capped"], 4),
                "raw_omega": round(row["raw_omega"], 4),
                "total_return": round(row["total_return"], 4),
                "downside_dev": round(row["downside_dev"], 6),
                "quality_score": round(row.get("quality_score", row["omega_capped"]), 4),
                "eligible_count": n_eligible,
            })

    signals_df = pd.DataFrame(signal_rows)
    audit_df = pd.DataFrame(audit_rows)
    return signals_df, audit_df


def main():
    parser = argparse.ArgumentParser(description="Build OM25 Omega Ratio signals")
    parser.add_argument("--prices-dir", default="nse500_data", type=Path)
    parser.add_argument("--universe", default="data/static/nse500_universe.csv", type=Path)
    parser.add_argument("--output", default=Path("data/om25/signals/om25_signals.csv"), type=Path)
    parser.add_argument("--audit-output", default=Path("data/om25/signals/omega_scores_by_rebalance.csv"), type=Path)
    parser.add_argument("--lookback", type=int, default=252)
    parser.add_argument("--min-obs", type=int, default=220)
    parser.add_argument("--threshold", type=float, default=0.0)
    parser.add_argument("--omega-cap", type=float, default=10.0)
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--ranking", choices=["pure_omega", "omega_quality"], default="pure_omega")
    parser.add_argument("--no-return-filter", action="store_true")
    parser.add_argument("--no-audit", action="store_true")
    args = parser.parse_args()

    universe = load_universe(args.universe)
    print(f"Universe: {len(universe)} symbols")

    print(f"Loading prices from {args.prices_dir}...")
    close = load_close_panel(args.prices_dir, universe).ffill()
    print(f"Loaded {len(close.columns)} symbols, {len(close)} days "
          f"({close.index[0].date()} to {close.index[-1].date()})")

    # Monthly rebalance dates
    cal = pd.Series(index=close.index, data=close.index)
    rebalance_dates = pd.DatetimeIndex(cal.resample("MS").first().dropna().values)

    min_obs = args.min_obs
    if args.lookback != 252:
        # Scale min_obs proportionally
        min_obs = int(args.lookback * 220 / 252)

    print(f"Config: lookback={args.lookback}, min_obs={min_obs}, threshold={args.threshold}, "
          f"cap={args.omega_cap}, top_n={args.top_n}, ranking={args.ranking}, "
          f"return_filter={not args.no_return_filter}")

    signals_df, audit_df = compute_omega_signals(
        close,
        lookback=args.lookback,
        min_obs=min_obs,
        threshold=args.threshold,
        omega_cap=args.omega_cap,
        require_positive_return=not args.no_return_filter,
        rebalance_dates=rebalance_dates,
        ranking_method=args.ranking,
        top_n=args.top_n,
    )

    # Save
    args.output.parent.mkdir(parents=True, exist_ok=True)
    signals_df.to_csv(args.output, index=False)
    print(f"Signals: {len(signals_df)} rows ({signals_df['date'].nunique()} months) -> {args.output}")

    if not args.no_audit:
        args.audit_output.parent.mkdir(parents=True, exist_ok=True)
        audit_df.to_csv(args.audit_output, index=False)
        print(f"Audit: {len(audit_df)} rows -> {args.audit_output}")

    # Summary
    if not signals_df.empty:
        print(f"\n=== OM25 Signal Summary ===")
        print(f"Date range: {signals_df['date'].min()} to {signals_df['date'].max()}")
        elig = signals_df.groupby("date")["eligible_count"].first()
        print(f"Eligible: min={elig.min()}, median={elig.median():.0f}, max={elig.max()}")
        counts = signals_df.groupby("date").size()
        print(f"Selected: min={counts.min()}, median={counts.median():.0f}, max={counts.max()}")
        print(f"Unique stocks: {signals_df['symbol'].nunique()}")
        omega_vals = signals_df["omega_capped"]
        print(f"Omega range: {omega_vals.min():.2f} - {omega_vals.max():.2f} (median {omega_vals.median():.2f})")

        latest = signals_df[signals_df["date"] == signals_df["date"].max()].head(10)
        print(f"\nTop 10 on {latest['date'].iloc[0]}:")
        for _, r in latest.iterrows():
            print(f"  #{int(r['rank']):>2} {r['symbol']:<15} Omega={r['omega_capped']:.2f}  "
                  f"Return={r['total_return']:+.1%}  DD_dev={r['downside_dev']:.4f}")


if __name__ == "__main__":
    main()
