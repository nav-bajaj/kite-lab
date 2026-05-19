"""
Rebalance Service - Handle weekly rebalance workflow.

Thursday: Generate preview (additions/removals)
Friday: Generate order file for execution
"""
from datetime import date, timedelta
from typing import Optional, List
from pathlib import Path
import glob
import json

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import get_session_local
from app.models.models import Rebalance, Signal, Holding


def get_latest_signals_dir(universe: str = "nse500") -> Optional[Path]:
    """Find the most recent signals/changes directory.

    For the legacy L6 portfolios (nse500/nifty100/nifty250) this resolves
    to the timestamped experiment dir written by
    ``run_final_momentum_portfolio.py`` — those dirs contain
    ``changes_<date>.csv`` and ``orders_<date>.csv`` files that the
    rebalance UI consumes directly.

    For the 4 new v3 portfolios (om25_v3 / tl25_v3 / l6_v2 /
    combo_defensive) this returns the most recent timestamped run dir
    written by their respective runner scripts. Those dirs contain
    ``<strategy>_signals.csv`` / ``<strategy>_exits.csv`` etc. — not
    the legacy ``changes_*.csv`` / ``orders_*.csv`` format. The
    downstream rebalance functions handle the missing files gracefully
    (returning a "No changes file found" message rather than erroring),
    which is the documented degradation path until those strategies grow
    rebalance-UI output of their own.
    """
    base_dir = settings.data_dir

    if universe == "nse500":
        pattern = base_dir / "experiments" / "final_portfolio" / "final_portfolio_202*"
    elif universe == "nifty100":
        pattern = base_dir / "nifty_100_tests" / "nifty100_portfolio_202*"
    elif universe == "nifty250":
        pattern = base_dir / "nifty_250_tests" / "nifty250_portfolio_202*"
    elif universe == "om25_v3":
        pattern = base_dir / "data" / "om25_v3_portfolios" / "om25_v3_portfolio_202*"
    elif universe == "tl25_v3":
        pattern = base_dir / "data" / "tl25_v3_portfolios" / "tl25_v3_portfolio_202*"
    elif universe == "l6_v2":
        pattern = base_dir / "data" / "l6_v2_portfolios" / "l6_v2_portfolio_202*"
    elif universe == "combo_defensive":
        pattern = base_dir / "data" / "combo_defensive_portfolios" / "combo_defensive_portfolio_202*"
    else:
        return None

    dirs = sorted(glob.glob(str(pattern)), reverse=True)
    return Path(dirs[0]) if dirs else None


def get_rebalance_status(universe: str = "nse500") -> dict:
    """
    Get current rebalance status.

    Returns status, signal date, and what's available.
    """
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        # Get latest rebalance record
        rebalance = db.query(Rebalance).filter(
            Rebalance.universe == universe
        ).order_by(desc(Rebalance.signal_date)).first()

        today = date.today()
        weekday = today.weekday()  # 0=Monday, 4=Friday

        # Determine current status based on day
        if weekday == 3:  # Thursday
            current_phase = "preview"
        elif weekday == 4:  # Friday
            current_phase = "ready"
        else:
            current_phase = "waiting"

        # Check for files in latest experiment
        exp_dir = get_latest_signals_dir(universe)
        changes_available = False
        orders_available = False

        if exp_dir:
            changes_files = list(exp_dir.glob("changes_*.csv"))
            orders_files = list(exp_dir.glob("orders_*.csv"))
            changes_available = len(changes_files) > 0
            orders_available = len(orders_files) > 0

        return {
            "universe": universe,
            "status": rebalance.status if rebalance else "none",
            "signal_date": str(rebalance.signal_date) if rebalance else None,
            "order_date": str(rebalance.order_date) if rebalance and rebalance.order_date else None,
            "current_phase": current_phase,
            "is_rebalance_day": weekday in [3, 4],
            "preview_available": changes_available,
            "orders_available": orders_available,
            "today": str(today),
            "weekday": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][weekday],
        }
    finally:
        db.close()


def get_rebalance_preview(universe: str = "nse500") -> dict:
    """
    Get preview of upcoming rebalance changes.

    Returns additions, removals, and rank changes.
    """
    import pandas as pd

    exp_dir = get_latest_signals_dir(universe)
    if not exp_dir:
        return {"error": f"No experiment directory found for {universe}"}

    # Look for changes file
    changes_files = sorted(exp_dir.glob("changes_*.csv"), reverse=True)
    if not changes_files:
        return {
            "universe": universe,
            "additions": [],
            "removals": [],
            "signal_date": None,
            "message": "No changes file found. Run portfolio generation to create one.",
        }

    changes_path = changes_files[0]
    signal_date = changes_path.stem.replace("changes_", "")

    df = pd.read_csv(changes_path)

    additions = []
    removals = []

    for _, row in df.iterrows():
        action = row.get("action", row.get("change_type", ""))

        if action.upper() in ["ADD", "ENTRY", "BUY"]:
            additions.append({
                "symbol": row["symbol"],
                "rank": int(row.get("rank", row.get("new_rank", 0))),
                "score": round(float(row.get("score", 0)), 4) if "score" in row else None,
            })
        elif action.upper() in ["REMOVE", "EXIT", "SELL", "DROP"]:
            removals.append({
                "symbol": row["symbol"],
                "prev_rank": int(row.get("prev_rank", row.get("old_rank", 0))) if "prev_rank" in row or "old_rank" in row else None,
                "reason": row.get("reason", "rank_drop"),
            })

    return {
        "universe": universe,
        "signal_date": signal_date,
        "additions": additions,
        "removals": removals,
        "additions_count": len(additions),
        "removals_count": len(removals),
    }


def get_rebalance_orders(universe: str = "nse500") -> dict:
    """
    Get order file for execution (Friday).

    Returns buy/sell orders with share quantities.
    """
    import pandas as pd

    exp_dir = get_latest_signals_dir(universe)
    if not exp_dir:
        return {"error": f"No experiment directory found for {universe}"}

    # Look for orders file
    orders_files = sorted(exp_dir.glob("orders_*.csv"), reverse=True)
    if not orders_files:
        return {
            "universe": universe,
            "orders": [],
            "order_date": None,
            "message": "No orders file found. Orders are generated on Fridays.",
        }

    orders_path = orders_files[0]
    order_date = orders_path.stem.replace("orders_", "")

    df = pd.read_csv(orders_path)

    orders = []
    for _, row in df.iterrows():
        orders.append({
            "symbol": row["symbol"],
            "action": row.get("action", row.get("side", "")).upper(),
            "shares": int(row.get("shares", row.get("quantity", 0))),
            "target_price": round(float(row.get("price", row.get("target_price", 0))), 2) if "price" in row or "target_price" in row else None,
            "notional": round(float(row.get("notional", row.get("amount", 0))), 2) if "notional" in row or "amount" in row else None,
        })

    # Sort: sells first, then buys
    orders.sort(key=lambda x: (0 if x["action"] == "SELL" else 1, x["symbol"]))

    buy_orders = [o for o in orders if o["action"] == "BUY"]
    sell_orders = [o for o in orders if o["action"] == "SELL"]

    return {
        "universe": universe,
        "order_date": order_date,
        "orders": orders,
        "buy_count": len(buy_orders),
        "sell_count": len(sell_orders),
        "total_orders": len(orders),
    }


def get_rebalance_history(
    universe: str = "nse500",
    limit: int = 20,
) -> dict:
    """
    Get history of past rebalances.
    """
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        rebalances = db.query(Rebalance).filter(
            Rebalance.universe == universe
        ).order_by(desc(Rebalance.signal_date)).limit(limit).all()

        history = []
        for r in rebalances:
            history.append({
                "signal_date": str(r.signal_date),
                "order_date": str(r.order_date) if r.order_date else None,
                "status": r.status,
                "additions": len(r.additions) if r.additions else 0,
                "removals": len(r.removals) if r.removals else 0,
                "turnover_pct": round(float(r.turnover_pct) * 100, 2) if r.turnover_pct else None,
            })

        return {
            "universe": universe,
            "history": history,
            "count": len(history),
        }
    finally:
        db.close()


def export_orders_csv(universe: str = "nse500") -> Optional[str]:
    """
    Export orders as CSV for Kite execution.
    """
    import io
    import csv

    orders_data = get_rebalance_orders(universe)

    if "error" in orders_data or not orders_data.get("orders"):
        return None

    output = io.StringIO()
    writer = csv.writer(output)

    # Header for Kite basket order format
    writer.writerow(["symbol", "exchange", "order_type", "transaction_type", "quantity", "price"])

    for order in orders_data["orders"]:
        writer.writerow([
            order["symbol"],
            "NSE",
            "LIMIT",
            order["action"],
            order["shares"],
            order["target_price"] or "",
        ])

    return output.getvalue()
