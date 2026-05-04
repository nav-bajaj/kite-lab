"""
Orchestrator for Trend Leaders 20 — runs full pipeline

Pipeline:
  1. Build composite signals (+ persistence-only for Variant 4)
  2. Run 4 backtest variants
  3. Print summary comparison

Usage:
    python scripts/run_trend_leaders_portfolio.py
    python scripts/run_trend_leaders_portfolio.py --variant base
    python scripts/run_trend_leaders_portfolio.py --top-n 25 --exit-buffer 15
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import pandas as pd

from scripts.build_trend_leaders_signals import (
    load_close_panel,
    load_universe,
    compute_moving_averages,
    compute_eligibility,
    compute_ma_structure_score,
    compute_persistence_score,
    compute_distance_200_score,
    compute_drawdown_control_score,
    compute_trend_quality_score_fast,
    derive_monthly_rebalance_dates,
    build_signals,
    build_audit,
)

from scripts.backtest_trend_leaders import run_backtest

import numpy as np


VARIANT_CONFIGS = {
    "base": {
        "variant": "base",
        "signals_key": "composite",
        "description": "Monthly entry + weekly exit, no market filter",
    },
    "market_filter": {
        "variant": "market_filter",
        "signals_key": "composite",
        "description": "Monthly entry + weekly exit, Nifty 500 < 200 DMA caps at 50%",
    },
    "monthly_only": {
        "variant": "monthly_only",
        "signals_key": "composite",
        "description": "Monthly entry and exit only, no weekly checks",
    },
    "persistence_only": {
        "variant": "base",
        "signals_key": "persistence_only",
        "description": "Persistence-only ranking, weekly exits",
    },
}


def main():
    parser = argparse.ArgumentParser(description="Run Trend Leaders 20 full pipeline")
    parser.add_argument("--prices-dir", default="nse500_data", type=Path)
    parser.add_argument("--universe", default="data/static/nse500_universe.csv", type=Path)
    parser.add_argument("--output-root", default="data/trend_leaders", type=Path)
    parser.add_argument("--benchmark", default="data/benchmarks/nifty100.csv", type=Path)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--exit-buffer", type=int, default=20)
    parser.add_argument("--rank-output", type=int, default=40)
    parser.add_argument("--max-weight", type=float, default=0.075)
    parser.add_argument("--slippage", type=float, default=0.002)
    parser.add_argument("--initial-capital", type=float, default=1_000_000)
    parser.add_argument("--variant", type=str, default=None,
                        help="Run only this variant (base/market_filter/monthly_only/persistence_only)")
    parser.add_argument("--no-audit", action="store_true")
    parser.add_argument("--market-filter-index", default="indices_data/NIFTY_500.csv", type=Path)
    args = parser.parse_args()

    t0 = time.time()
    signals_dir = args.output_root / "signals"
    signals_dir.mkdir(parents=True, exist_ok=True)

    # Determine which variants to run
    if args.variant:
        variants_to_run = [args.variant]
    else:
        variants_to_run = list(VARIANT_CONFIGS.keys())

    # Check if we need persistence-only signals
    needs_persistence = "persistence_only" in variants_to_run

    # -----------------------------------------------------------------------
    # Step 1: Build signals
    # -----------------------------------------------------------------------
    print("=" * 60)
    print("STEP 1: Building signals")
    print("=" * 60)

    universe = load_universe(args.universe)
    print(f"Universe: {len(universe)} symbols")

    print("Loading prices...")
    close = load_close_panel(args.prices_dir, universe)
    close = close.ffill()
    print(f"Loaded {len(close.columns)} symbols, {len(close)} trading days")

    print("Computing moving averages...")
    sma_dict = compute_moving_averages(close)

    print("Computing eligibility and score components...")
    eligibility = compute_eligibility(close, sma_dict["sma_50"], sma_dict["sma_200"])
    ma_structure = compute_ma_structure_score(
        close, sma_dict["sma_50"], sma_dict["sma_100"], sma_dict["sma_200"]
    )
    persistence = compute_persistence_score(close, sma_dict["sma_100"])
    distance_200 = compute_distance_200_score(close, sma_dict["sma_200"])
    drawdown_control = compute_drawdown_control_score(close)

    components = {
        "ma_structure": ma_structure,
        "persistence": persistence,
        "distance_200": distance_200,
        "drawdown_control": drawdown_control,
    }

    # Derive rebalance dates
    rebalance_dates = derive_monthly_rebalance_dates(close.index)
    min_date = close.index[200 + 63]  # 200 DMA + persistence window
    rebalance_dates = rebalance_dates[rebalance_dates >= min_date]
    print(f"Rebalance dates: {len(rebalance_dates)} months "
          f"({rebalance_dates[0].date()} to {rebalance_dates[-1].date()})")

    # Composite TQS signals
    print("Computing composite Trend Quality Score...")
    tqs_composite = compute_trend_quality_score_fast(
        ma_structure, persistence, distance_200, drawdown_control,
        eligibility, (0.30, 0.30, 0.20, 0.20), rebalance_dates,
    )
    signals_composite = build_signals(
        close, tqs_composite, eligibility, components,
        rebalance_dates, top_n=args.top_n, rank_output=args.rank_output,
    )
    composite_path = signals_dir / "trend_leaders_signals.csv"
    signals_composite.to_csv(composite_path, index=False)
    print(f"Composite signals: {len(signals_composite)} rows -> {composite_path}")

    # Persistence-only signals (if needed)
    persistence_path = signals_dir / "persistence_only_signals.csv"
    if needs_persistence:
        print("Computing persistence-only scores...")
        tqs_persist = pd.DataFrame(np.nan, index=rebalance_dates, columns=close.columns)
        for date in rebalance_dates:
            if date not in eligibility.index:
                continue
            elig = eligibility.loc[date]
            if elig.sum() == 0:
                continue
            tqs_persist.loc[date] = persistence.loc[date].where(elig)
        signals_persist = build_signals(
            close, tqs_persist, eligibility, components,
            rebalance_dates, top_n=args.top_n, rank_output=args.rank_output,
        )
        signals_persist.to_csv(persistence_path, index=False)
        print(f"Persistence signals: {len(signals_persist)} rows -> {persistence_path}")

    # Audit file
    if not args.no_audit:
        print("Building audit file...")
        audit_df = build_audit(
            close, tqs_composite, eligibility, components, sma_dict,
            rebalance_dates, top_n=args.top_n,
        )
        audit_path = signals_dir / "trend_scores_by_rebalance.csv"
        audit_df.to_csv(audit_path, index=False)
        print(f"Audit: {len(audit_df)} rows -> {audit_path}")

    # -----------------------------------------------------------------------
    # Step 2: Run backtests
    # -----------------------------------------------------------------------
    print()
    print("=" * 60)
    print("STEP 2: Running backtests")
    print("=" * 60)

    all_metrics = {}
    for variant_name in variants_to_run:
        config = VARIANT_CONFIGS[variant_name]
        print(f"\n--- Variant: {variant_name} ({config['description']}) ---")

        signals_path = composite_path if config["signals_key"] == "composite" else persistence_path
        output_dir = args.output_root / "backtests" / variant_name

        metrics = run_backtest(
            prices_dir=args.prices_dir,
            signals_path=signals_path,
            benchmark_path=args.benchmark,
            output_dir=output_dir,
            initial_capital=args.initial_capital,
            top_n=args.top_n,
            exit_buffer=args.exit_buffer,
            max_weight=args.max_weight,
            slippage=args.slippage,
            variant=config["variant"],
            market_filter_index_path=args.market_filter_index if config["variant"] == "market_filter" else None,
        )
        all_metrics[variant_name] = metrics.iloc[0] if not metrics.empty else {}

    # -----------------------------------------------------------------------
    # Step 3: Summary
    # -----------------------------------------------------------------------
    elapsed = time.time() - t0
    print()
    print("=" * 60)
    print(f"TREND LEADERS 20 — BACKTEST SUMMARY (completed in {elapsed:.0f}s)")
    print("=" * 60)

    if all_metrics:
        header = f"{'Variant':<20} {'CAGR':>8} {'Max DD':>8} {'Sharpe':>8} {'Sortino':>8} {'Calmar':>8} {'Turnover':>10} {'Cash%':>7}"
        print(header)
        print("-" * len(header))

        for name, m in all_metrics.items():
            if isinstance(m, dict) and not m:
                continue
            print(f"{name:<20} "
                  f"{m.get('cagr', 0):>7.1%} "
                  f"{m.get('max_drawdown', 0):>7.1%} "
                  f"{m.get('sharpe_ratio', 0):>8.2f} "
                  f"{m.get('sortino_ratio', 0):>8.2f} "
                  f"{m.get('calmar_ratio', 0):>8.2f} "
                  f"{m.get('annualized_turnover', 0):>9.0%} "
                  f"{m.get('avg_cash_pct', 0):>6.1%}")

    print(f"\nResults saved to: {args.output_root}/")
    print(f"Signals: {signals_dir}/")
    print(f"Backtests: {args.output_root / 'backtests'}/")
    if not args.no_audit:
        print(f"Audit: {signals_dir / 'trend_scores_by_rebalance.csv'}")


if __name__ == "__main__":
    main()
