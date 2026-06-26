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
import glob
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_pipeline.eod_proposal import build_eod_artifact


# Match the UNIVERSE_DIRS spec in kite-api/app/services/sync_service.py so
# the producer writes into the same run dir the API's latest.json pointer
# already advances to. That way the dashboard sync picks up
# `proposed_regime.json` next to `momentum_*.csv` without any extra glob.
_STRATEGY_PARENT_DIR = {
    "om25_v3": ROOT / "data/om25_v3_portfolios",
    "tl25_v3": ROOT / "data/tl25_v3_portfolios",
}
_STRATEGY_RUN_GLOB = {
    "om25_v3": "om25_v3_portfolio_202*",
    "tl25_v3": "tl25_v3_portfolio_202*",
}


def _latest_production_run_dir(strategy: str) -> Path:
    """Return the newest <strategy>_portfolio_<ts> dir, or raise.

    Mirrors sync_service.get_latest_experiment_dir's filter: only dirs that
    contain ``backtests/baseline/momentum_holdings.csv`` qualify, so we
    never write into an empty/aborted run.
    """
    parent = _STRATEGY_PARENT_DIR[strategy]
    pattern = _STRATEGY_RUN_GLOB[strategy]
    candidates = sorted(glob.glob(str(parent / pattern)), reverse=True)
    for d in candidates:
        run = Path(d)
        if (run / "backtests" / "baseline" / "momentum_holdings.csv").exists():
            return run
    raise RuntimeError(
        f"No completed production run found under {parent}; run the "
        f"daily pipeline (scripts/run_{strategy}_portfolio.py) first."
    )


def parse_args():
    ap = argparse.ArgumentParser(description="EOD proposed-orders producer")
    # Accept either --strategy (CLI-natural) or --universe (job-service-natural,
    # since scheduler/job_service.py passes the universe arg uniformly). Both
    # mean the same thing here — the strategy name *is* the universe ID.
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--strategy", choices=sorted(_STRATEGY_PARENT_DIR))
    group.add_argument("--universe", choices=sorted(_STRATEGY_PARENT_DIR),
                       help="Alias for --strategy; used when invoked via the "
                            "job-service scheduler.")
    ap.add_argument("--prices-dir", type=Path,
                    default=ROOT / "nse500_data_merged")
    ap.add_argument("--signal-date", type=str, default=None,
                    help="Override signal date (YYYY-MM-DD). "
                         "Default: latest cadence date in panels.")
    ap.add_argument("--output-dir", type=Path, default=None,
                    help="Where to write the artifacts. Default: the latest "
                         "<strategy>_portfolio_<ts>/backtests/baseline/ dir "
                         "so the dashboard sync (which already advances "
                         "latest.json to that run) picks it up alongside "
                         "momentum_*.csv. Override to a fresh dir when "
                         "verifying a past signal date in isolation.")
    ap.add_argument("--initial-capital", type=float, default=1_000_000)
    ap.add_argument("--backtest-start", type=str, default="2018-01-01")
    return ap.parse_args()


def main():
    args = parse_args()
    strategy = args.strategy or args.universe
    signal_date = (pd.Timestamp(args.signal_date)
                   if args.signal_date else None)

    if args.output_dir is None:
        run_dir = _latest_production_run_dir(strategy)
        print(f"[eod] writing into latest production run: {run_dir.name}")
    else:
        run_dir = args.output_dir
    out_dir = run_dir / "backtests" / "baseline"

    summary = build_eod_artifact(
        strategy=strategy,
        prices_dir=args.prices_dir,
        output_dir=out_dir,
        signal_date=signal_date,
        initial_capital=args.initial_capital,
        backtest_start=args.backtest_start,
    )

    print()
    print(f"=== {strategy} EOD readout ===")
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
