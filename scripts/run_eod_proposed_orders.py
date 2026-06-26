"""End-of-day producer for the upcoming rebalance.

Reads what the engine decided on the signal day and writes a
membership-only ``proposed_orders_<exec_date>.csv`` + ``proposed_regime.json``
into a run dir's ``backtests/baseline/``. See ``data_pipeline/eod_proposal.py``
for how it works and ``tasks/rebalance_page/PLAN.md`` (Phase 2) for why.

Typical usage:
    # Production (latest data, latest cadence date):
    python scripts/run_eod_proposed_orders.py --strategy om25_v3
    python scripts/run_eod_proposed_orders.py --strategy tl25_v3

    # Reproduce a past signal day for verification:
    python scripts/run_eod_proposed_orders.py --strategy tl25_v3 \
        --signal-date 2026-05-12
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_pipeline.eod_proposal import build_eod_artifact


_STRATEGY_OUT_ROOT = {
    "om25_v3": "data/om25_v3_portfolios",
    "tl25_v3": "data/tl25_v3_portfolios",
}


def parse_args():
    ap = argparse.ArgumentParser(description="EOD proposed-orders producer")
    ap.add_argument("--strategy", required=True,
                    choices=sorted(_STRATEGY_OUT_ROOT))
    ap.add_argument("--prices-dir", type=Path,
                    default=ROOT / "nse500_data_merged")
    ap.add_argument("--signal-date", type=str, default=None,
                    help="Override signal date (YYYY-MM-DD). "
                         "Default: latest cadence date in panels.")
    ap.add_argument("--output-dir", type=Path, default=None,
                    help="Where to write the artifacts. Default: a fresh "
                         "<strategy>_eod_<ts> run dir under the strategy's "
                         "portfolio root, with the same backtests/baseline/ "
                         "layout the dashboard sync reads.")
    ap.add_argument("--initial-capital", type=float, default=1_000_000)
    ap.add_argument("--backtest-start", type=str, default="2018-01-01")
    return ap.parse_args()


def main():
    args = parse_args()
    signal_date = (pd.Timestamp(args.signal_date)
                   if args.signal_date else None)

    if args.output_dir is None:
        ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        run_dir = (ROOT / _STRATEGY_OUT_ROOT[args.strategy]
                   / f"{args.strategy}_eod_{ts}")
    else:
        run_dir = args.output_dir
    out_dir = run_dir / "backtests" / "baseline"

    summary = build_eod_artifact(
        strategy=args.strategy,
        prices_dir=args.prices_dir,
        output_dir=out_dir,
        signal_date=signal_date,
        initial_capital=args.initial_capital,
        backtest_start=args.backtest_start,
    )

    print()
    print(f"=== {args.strategy} EOD readout ===")
    print(f"  signal_date  : {summary['signal_date']}")
    print(f"  exec_date    : {summary['exec_date']}")
    print(f"  regime       : {summary.get('regime')}")
    print(f"  drawdown%    : {summary['drawdown_from_peak']*100:.2f}")
    print(f"  SELL         : {summary['sell_count']} → {summary['sells']}")
    print(f"  BUY          : {summary['buy_count']} → "
          f"{[b['symbol'] for b in summary['buys']]}")
    print(f"  HOLD         : {summary['hold_count']}")
    print(f"  out          : {out_dir}")


if __name__ == "__main__":
    main()
