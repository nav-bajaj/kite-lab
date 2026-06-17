"""
Sync Service - Import CSV data into PostgreSQL database
"""
import glob
import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import get_session_local
from app.models.models import Holding, EquityCurve, Metric, Trade, Signal


logger = logging.getLogger(__name__)


# Phase 3.3 — single source of truth for where each universe's timestamped
# run dirs live. `(parent_dir, glob_pattern)` per universe.
UNIVERSE_DIRS = {
    "nse500":           ("experiments/final_portfolio",      "final_portfolio_202*"),
    "nifty100":         ("nifty_100_tests",                  "nifty100_portfolio_202*"),
    "nifty250":         ("nifty_250_tests",                  "nifty250_portfolio_202*"),
    "om25_v3":          ("data/om25_v3_portfolios",          "om25_v3_portfolio_202*"),
    "tl25_v3":          ("data/tl25_v3_portfolios",          "tl25_v3_portfolio_202*"),
    "l6_v2":            ("data/l6_v2_portfolios",            "l6_v2_portfolio_202*"),
    "combo_defensive":  ("data/combo_defensive_portfolios",  "combo_defensive_portfolio_202*"),
}


def _holdings_present(run_dir: Path) -> bool:
    return (run_dir / "backtests" / "baseline" / "momentum_holdings.csv").exists()


def _read_latest_pointer(parent_dir: Path) -> Optional[Path]:
    """Read parent_dir/latest.json. Returns the pointed-at run dir if it
    still exists on disk and contains the expected holdings CSV; else None.
    """
    pointer = parent_dir / "latest.json"
    if not pointer.is_file():
        return None
    try:
        data = json.loads(pointer.read_text())
        run_name = data.get("path")
        if not run_name:
            return None
        run_dir = parent_dir / run_name
        if run_dir.is_dir() and _holdings_present(run_dir):
            return run_dir
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not read {pointer}: {e}")
    return None


def _write_latest_pointer(parent_dir: Path, run_dir: Path) -> None:
    """Persist {path: <run-dir-name>, timestamp: <iso>} as latest.json.
    Failure is non-fatal — the next call will just re-glob."""
    pointer = parent_dir / "latest.json"
    payload = {
        "path": run_dir.name,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    try:
        pointer.write_text(json.dumps(payload, indent=2))
    except OSError as e:
        logger.warning(f"Could not write {pointer}: {e}")


def refresh_latest_pointer(universe: str) -> Optional[Path]:
    """Re-point ``latest.json`` at the newest run dir that has a holdings CSV.

    The pointer is a read cache that ``get_latest_experiment_dir`` trusts
    without globbing (Phase 3.3). The daily pipeline creates a *new*
    timestamped run dir every day but nothing here touches the pointer, so
    once written it stays frozen on whatever run it first pointed at — for as
    long as that dir survives on disk (which, on the persistent Railway
    volume, is indefinitely). The result is that every DB sync and every
    dashboard read (holdings, trades, equity, metrics, open positions) keeps
    serving a stale run: rebalances and new trades never surface.

    Call this from the producer side (the daily sync) so the pointer advances
    to the latest run before anything reads it. Returns the run dir now
    pointed at, or None if no valid run exists.
    """
    spec = UNIVERSE_DIRS.get(universe)
    if spec is None:
        return None
    parent_rel, pattern = spec
    parent_dir = settings.data_dir / parent_rel

    candidates = sorted(glob.glob(str(parent_dir / pattern)), reverse=True)
    for d in candidates:
        run_dir = Path(d)
        if _holdings_present(run_dir):
            _write_latest_pointer(parent_dir, run_dir)
            return run_dir
    return None


def get_latest_experiment_dir(universe: str = "nse500") -> Optional[Path]:
    """Find the most recent experiment directory for a universe.

    Phase 3.3 — prefer the `latest.json` pointer file in the parent dir
    when it exists and points at a still-valid run; otherwise fall back
    to the timestamp glob and lazily write the pointer so the next call
    is one stat instead of a full glob.
    """
    spec = UNIVERSE_DIRS.get(universe)
    if spec is None:
        return None
    parent_rel, pattern = spec
    parent_dir = settings.data_dir / parent_rel

    pointed = _read_latest_pointer(parent_dir)
    if pointed is not None:
        return pointed

    candidates = sorted(glob.glob(str(parent_dir / pattern)), reverse=True)
    for d in candidates:
        run_dir = Path(d)
        if _holdings_present(run_dir):
            _write_latest_pointer(parent_dir, run_dir)
            return run_dir

    return None


def sync_holdings(db: Session, universe: str = "nse500") -> dict:
    """
    Sync holdings from CSV to database.

    Returns dict with count of records synced.
    """
    exp_dir = get_latest_experiment_dir(universe)
    if not exp_dir:
        return {"error": f"No experiment directory found for {universe}", "count": 0}

    holdings_path = exp_dir / "backtests" / "baseline" / "momentum_holdings.csv"
    if not holdings_path.exists():
        return {"error": f"Holdings file not found: {holdings_path}", "count": 0}

    df = pd.read_csv(holdings_path)
    snapshot_date = date.today()

    # Delete existing holdings for this universe and date
    db.query(Holding).filter(
        Holding.universe == universe,
        Holding.snapshot_date == snapshot_date
    ).delete()

    # Insert new holdings
    count = 0
    for _, row in df.iterrows():
        holding = Holding(
            universe=universe,
            snapshot_date=snapshot_date,
            symbol=row["symbol"],
            shares=float(row["shares"]),
            avg_cost=float(row["avg_cost"]),
            entry_date=pd.to_datetime(row["entry_date"]).date(),
            entry_rank=int(row["entry_rank"]),
            holding_days=int(row["holding_days"]),
            last_price=float(row["last_price"]),
            pnl_pct=float(row["pnl_pct"]),
            notional=float(row["notional"]),
            contribution_pct=float(row["contribution_pct"]),
        )
        db.add(holding)
        count += 1

    db.commit()
    return {"universe": universe, "count": count, "snapshot_date": str(snapshot_date)}


def sync_equity_curve(db: Session, universe: str = "nse500") -> dict:
    """
    Sync equity curve from CSV to database.
    """
    exp_dir = get_latest_experiment_dir(universe)
    if not exp_dir:
        return {"error": f"No experiment directory found for {universe}", "count": 0}

    equity_path = exp_dir / "backtests" / "baseline" / "momentum_equity.csv"
    if not equity_path.exists():
        return {"error": f"Equity file not found: {equity_path}", "count": 0}

    df = pd.read_csv(equity_path, parse_dates=["date"])

    # Get existing dates to avoid duplicates
    existing_dates = set(
        row[0] for row in db.query(EquityCurve.date).filter(
            EquityCurve.universe == universe
        ).all()
    )

    count = 0
    for _, row in df.iterrows():
        row_date = row["date"].date() if hasattr(row["date"], "date") else row["date"]

        if row_date in existing_dates:
            continue

        equity = EquityCurve(
            universe=universe,
            date=row_date,
            portfolio_value=float(row.get("portfolio_value", row.get("value", 0))),
            benchmark=float(row.get("benchmark", row.get("benchmark_value", 0))) if "benchmark" in row or "benchmark_value" in row else None,
            drawdown=float(row.get("drawdown", 0)) if "drawdown" in row else None,
        )
        db.add(equity)
        count += 1

    db.commit()
    return {"universe": universe, "count": count}


def sync_metrics(db: Session, universe: str = "nse500") -> dict:
    """
    Sync metrics from CSV to database.
    """
    exp_dir = get_latest_experiment_dir(universe)
    if not exp_dir:
        return {"error": f"No experiment directory found for {universe}", "count": 0}

    metrics_path = exp_dir / "backtests" / "baseline" / "momentum_metrics.csv"
    if not metrics_path.exists():
        return {"error": f"Metrics file not found: {metrics_path}", "count": 0}

    df = pd.read_csv(metrics_path)

    # Handle both formats: single row with columns, or two-column metric/value format
    if "metric" in df.columns and "value" in df.columns:
        metrics_dict = dict(zip(df["metric"], df["value"]))
    else:
        # Single row format - columns are the metric names
        metrics_dict = df.iloc[0].to_dict()

    computed_date = date.today()

    # Delete existing metrics for this universe and date
    db.query(Metric).filter(
        Metric.universe == universe,
        Metric.computed_date == computed_date
    ).delete()

    metric = Metric(
        universe=universe,
        computed_date=computed_date,
        start_date=pd.to_datetime(metrics_dict.get("start")).date() if "start" in metrics_dict else None,
        end_date=pd.to_datetime(metrics_dict.get("end")).date() if "end" in metrics_dict else None,
        total_return=float(metrics_dict.get("total_return", 0)),
        cagr=float(metrics_dict.get("cagr", 0)),
        max_drawdown=float(metrics_dict.get("max_drawdown", 0)),
        max_drawdown_duration=int(metrics_dict.get("max_drawdown_duration_days", 0)) if "max_drawdown_duration_days" in metrics_dict else None,
        avg_turnover_pct=float(metrics_dict.get("avg_turnover_pct", 0)) if "avg_turnover_pct" in metrics_dict else None,
        annualized_turnover=float(metrics_dict.get("annualized_turnover", 0)) if "annualized_turnover" in metrics_dict else None,
        hit_rate=float(metrics_dict.get("hit_rate_overall", 0)) if "hit_rate_overall" in metrics_dict else None,
        avg_holding_days=float(metrics_dict.get("avg_holding_days", 0)) if "avg_holding_days" in metrics_dict else None,
        trades_total=int(metrics_dict.get("trades_total", 0)) if "trades_total" in metrics_dict else None,
        buys=int(metrics_dict.get("buys", 0)) if "buys" in metrics_dict else None,
        sells=int(metrics_dict.get("sells", 0)) if "sells" in metrics_dict else None,
    )
    db.add(metric)
    db.commit()

    return {"universe": universe, "count": 1, "computed_date": str(computed_date)}


def sync_trades(db: Session, universe: str = "nse500", full: bool = False) -> dict:
    """
    Sync trades from CSV to database.

    Args:
        full: If True, delete all existing trades and re-insert from CSV.
              Default False (incremental: only add trades after last existing).
    """
    exp_dir = get_latest_experiment_dir(universe)
    if not exp_dir:
        return {"error": f"No experiment directory found for {universe}", "count": 0}

    trades_path = exp_dir / "backtests" / "baseline" / "momentum_trades.csv"
    if not trades_path.exists():
        return {"error": f"Trades file not found: {trades_path}", "count": 0}

    df = pd.read_csv(trades_path, parse_dates=["date"])

    if full:
        # Full replace: delete all existing trades for this universe
        deleted = db.query(Trade).filter(Trade.universe == universe).delete()
        db.flush()
    else:
        # Incremental: only add new trades after last existing
        existing_count = db.query(Trade).filter(Trade.universe == universe).count()
        if existing_count > 0:
            last_trade = db.query(Trade).filter(
                Trade.universe == universe
            ).order_by(Trade.trade_date.desc()).first()
            if last_trade:
                df = df[df["date"] > pd.Timestamp(last_trade.trade_date)]

    count = 0
    for _, row in df.iterrows():
        row_date = row["date"].date() if hasattr(row["date"], "date") else row["date"]

        trade = Trade(
            universe=universe,
            trade_date=row_date,
            symbol=row["symbol"],
            side=row["side"],
            shares=float(row["shares"]),
            price=float(row["price"]),
            notional=float(row["notional"]),
            slippage=float(row.get("slippage", 0)) if "slippage" in row else None,
            cash_after=float(row.get("cash_after", 0)) if "cash_after" in row else None,
        )
        db.add(trade)
        count += 1

    db.commit()
    mode = "full replace" if full else "incremental"
    return {"universe": universe, "count": count, "mode": mode}


def sync_all(universe: str = "nse500", full_trades: bool = False) -> dict:
    """
    Sync all data for a universe.

    Args:
        full_trades: If True, do a full trade re-sync (delete + reinsert).
    """
    from app.services.trade_matching_service import rebuild_matches

    SessionLocal = get_session_local()
    db = SessionLocal()

    # Advance the latest.json pointer to today's run before reading anything.
    # Without this the sync (and the dashboard, which shares this pointer)
    # keeps reading whatever run the pointer first cached — see
    # refresh_latest_pointer for the full failure mode.
    refresh_latest_pointer(universe)

    try:
        results = {
            "universe": universe,
            "holdings": sync_holdings(db, universe),
            "equity_curve": sync_equity_curve(db, universe),
            "metrics": sync_metrics(db, universe),
            "trades": sync_trades(db, universe, full=full_trades),
        }
        try:
            match_result = rebuild_matches(universe, db)
            results["trade_matches"] = {
                "count": match_result.matches_created,
                "unmatched_sell_shares": float(match_result.unmatched_sell_shares),
                "open_lots_remaining": match_result.open_lots_remaining,
            }
        except Exception as e:
            results["trade_matches"] = {"error": str(e)}
        return results
    finally:
        db.close()


def sync_all_universes(full_trades: bool = False) -> dict:
    """
    Sync all data for all universes (and strategies treated as universes).
    """
    results = {}
    for universe in ["nse500", "nifty100", "nifty250", "om25_v3", "tl25_v3", "l6_v2", "combo_defensive"]:
        results[universe] = sync_all(universe, full_trades=full_trades)
    return results
