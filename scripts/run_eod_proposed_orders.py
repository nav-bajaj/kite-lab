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


# CLI --strategy / --universe choices. The actual run-dir lookup goes through
# sync_service.get_latest_experiment_dir which handles the ``settings.data_dir``
# resolution (/app locally, /data on Railway's persistent volume) and shares
# the UNIVERSE_DIRS + latest.json cache logic with the API. Keeping this list
# in one place avoids drift.
_STRATEGIES = ("om25_v3", "tl25_v3", "l6_v2", "combo_defensive")


def _latest_production_run_dir(strategy: str) -> Path:
    """Return the newest <strategy>_portfolio_<ts> dir, or raise.

    Delegates to sync_service.get_latest_experiment_dir so we respect the
    same ``settings.data_dir`` resolution + latest.json pointer that the
    API already uses. Without this the script hard-codes
    ``ROOT / "data/..."`` which is ``/app/data/...`` on Railway — but the
    persistent volume mounts production runs at ``/data/data/...`` on that
    environment.
    """
    kite_api = ROOT / "kite-api"
    if str(kite_api) not in sys.path:
        sys.path.insert(0, str(kite_api))
    from app.services.sync_service import (
        get_latest_experiment_dir, refresh_latest_pointer,
    )

    refresh_latest_pointer(strategy)
    run = get_latest_experiment_dir(strategy)
    if run is None:
        raise RuntimeError(
            f"No completed production run found for {strategy}; run the "
            f"daily pipeline (scripts/run_{strategy}_portfolio.py) first."
        )
    return Path(run)


def parse_args():
    ap = argparse.ArgumentParser(description="EOD proposed-orders producer")
    # Accept either --strategy (CLI-natural) or --universe (job-service-natural,
    # since scheduler/job_service.py passes the universe arg uniformly). Both
    # mean the same thing here — the strategy name *is* the universe ID.
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--strategy", choices=sorted(_STRATEGIES))
    group.add_argument("--universe", choices=sorted(_STRATEGIES),
                       help="Alias for --strategy; used when invoked via the "
                            "job-service scheduler.")
    # nse500_data (Kite live, 2020+) matches what
    # scripts/run_daily_pipeline.py + scripts/update_all_portfolios.py use in
    # production. nse500_data_merged (2009+ stitched) only exists locally for
    # research and is not present on the Railway persistent volume.
    ap.add_argument("--prices-dir", type=Path,
                    default=ROOT / "nse500_data")
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
    ap.add_argument("--mode", choices=["entry", "exit_only"], default="entry",
                    help="'entry' = full rebalance on the strategy's entry "
                         "cadence Friday. 'exit_only' = weekly rank / DD-stop "
                         "/ regime exit preview on an off-week Friday for "
                         "biweekly strategies (no BUYs). Semantically a no-op "
                         "on weekly strategies (l6_v2).")
    ap.add_argument("--no-sync", action="store_true",
                    help="Skip the sync_proposed_rebalance DB write at the "
                         "end. Default: sync so the /api/rebalance/upcoming "
                         "endpoint sees the row within seconds of the "
                         "producer finishing, instead of waiting for the "
                         "next 07:00 IST daily_pipeline sync cycle.")
    return ap.parse_args()


def _sync_to_db(strategy: str) -> None:
    """Import kite-api's sync_service and push the freshly-written JSON into
    the ``proposed_rebalances`` table.

    The 07:00 IST ``daily_pipeline`` runs sync_all *before* the producer
    runs at 16:00 IST, so a producer output stays invisible to the API for
    ~15 hours without this. On Railway the script + API share the same
    ``DATABASE_URL`` env var so the SQLAlchemy engine attaches to the same
    Postgres; locally the same is true.
    """
    kite_api = ROOT / "kite-api"
    if str(kite_api) not in sys.path:
        sys.path.insert(0, str(kite_api))
    from app.models.database import get_session_local
    from app.services.sync_service import (
        refresh_latest_pointer, sync_proposed_rebalance,
    )

    refresh_latest_pointer(strategy)
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        result = sync_proposed_rebalance(db, strategy)
        print(f"[eod] sync → {result}")
    finally:
        db.close()


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

    # Production path (no explicit --signal-date): the 16:00 cron runs on a real
    # signal day, so today's close must be in the panel. Guard against a silent
    # data-refresh failure emitting a back-dated proposal. Skip the guard for
    # past-date verification runs (--signal-date given). IST because the signal
    # day is defined on the NSE calendar, not the server's local date.
    require_through = None
    if signal_date is None:
        require_through = (pd.Timestamp.now(tz="Asia/Kolkata")
                           .normalize().tz_localize(None))

    # Holiday-aware exec_date so the artifact's exec_date matches /summary's
    # (both roll off NSE weekends AND holidays). market_service lives in the API
    # package; the script already imports from it for run-dir resolution.
    next_trading_day = None
    try:
        kite_api = ROOT / "kite-api"
        if str(kite_api) not in sys.path:
            sys.path.insert(0, str(kite_api))
        from app.services.market_service import next_trading_day_after
        next_trading_day = next_trading_day_after
    except Exception as e:  # pragma: no cover - defensive fallback
        print(f"[eod] warning: holiday calendar unavailable ({e!r}); "
              f"exec_date uses weekend-only roll")

    summary = build_eod_artifact(
        strategy=strategy,
        prices_dir=args.prices_dir,
        output_dir=out_dir,
        signal_date=signal_date,
        initial_capital=args.initial_capital,
        backtest_start=args.backtest_start,
        mode=args.mode,
        require_panel_through=require_through,
        next_trading_day=next_trading_day,
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

    if not args.no_sync:
        try:
            _sync_to_db(strategy)
        except Exception as e:
            # Producer artifact is on disk regardless — a sync failure just
            # means the DB row waits until the next sync_all. Don't fail the
            # whole job over it.
            print(f"[eod] warning: sync failed: {e!r}")


if __name__ == "__main__":
    main()
