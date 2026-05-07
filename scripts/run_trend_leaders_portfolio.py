"""
Orchestrator for Trend Leaders 25 — runs full pipeline

Pipeline:
  1. Build composite signals (locked-in TQS: 1/3 persist + 1/3 dd + 1/3 mom)
  2. Run backtest variants
  3. Print summary comparison

Usage:
    python scripts/run_trend_leaders_portfolio.py
    python scripts/run_trend_leaders_portfolio.py --variant base
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
    compute_persistence_score,
    compute_drawdown_control_score,
    compute_momentum_score,
    compute_trend_quality_score_fast,
    derive_biweekly_rebalance_dates,
    build_signals,
    build_audit,
)

from scripts.backtest_trend_leaders import run_backtest

import numpy as np


VARIANT_CONFIGS = {
    "base": {
        "variant": "base",
        "description": "Bi-weekly entry + weekly exit, no market filter",
    },
    "market_filter": {
        "variant": "market_filter",
        "description": "Bi-weekly entry + weekly exit, Nifty 500 < 200 DMA caps at 50%",
    },
}


def main():
    parser = argparse.ArgumentParser(description="Run Trend Leaders 20 full pipeline")
    parser.add_argument("--prices-dir", default="nse500_data", type=Path)
    parser.add_argument("--universe", default="data/static/nse500_universe.csv", type=Path)
    parser.add_argument("--output-root", default="data/trend_leaders", type=Path)
    parser.add_argument("--benchmark", default="data/benchmarks/nifty100.csv", type=Path)
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--exit-buffer", type=int, default=20)
    parser.add_argument("--rank-output", type=int, default=45)
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
    persistence = compute_persistence_score(close, sma_dict["sma_100"], window=252)
    drawdown_control = compute_drawdown_control_score(close, window=126)
    momentum = compute_momentum_score(close, eligibility, window=63)

    components = {
        "persistence": persistence,
        "drawdown_control": drawdown_control,
        "momentum": momentum,
    }

    # Bi-weekly rebalance dates (locked-in for TL25 entries)
    rebalance_dates = derive_biweekly_rebalance_dates(close.index)
    min_date = close.index[200 + 252]  # 200 DMA + 252d persistence window
    rebalance_dates = rebalance_dates[rebalance_dates >= min_date]
    print(f"Bi-weekly rebalance dates: {len(rebalance_dates)} "
          f"({rebalance_dates[0].date()} to {rebalance_dates[-1].date()})")

    # Composite TQS — equal 1/3 weights (locked-in)
    print("Computing composite Trend Quality Score (1/3 each: persist, dd, mom)...")
    tqs_composite = compute_trend_quality_score_fast(
        persistence, drawdown_control, momentum,
        eligibility, (1/3, 1/3, 1/3), rebalance_dates,
    )
    signals_composite = build_signals(
        close, tqs_composite, eligibility, components,
        rebalance_dates, top_n=args.top_n, rank_output=args.rank_output,
    )
    composite_path = signals_dir / "trend_leaders_signals.csv"
    signals_composite.to_csv(composite_path, index=False)
    print(f"Composite signals: {len(signals_composite)} rows -> {composite_path}")

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

        signals_path = composite_path
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
    print(f"TREND LEADERS 25 — BACKTEST SUMMARY (completed in {elapsed:.0f}s)")
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
