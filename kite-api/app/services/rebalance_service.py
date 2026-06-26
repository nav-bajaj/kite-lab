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

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.config import settings, UNIVERSES
from app.models.database import get_session_local
from app.models.models import (
    EquityCurve,
    Holding,
    OpenPosition,
    ProposedRebalance,
    Rebalance,
    Signal,
    Trade,
)
from app.services.market_service import (
    snap_back_to_trading_day,
    next_trading_day_after,
    trading_days_between,
)


# Rebalance cadence metadata: cadence_key -> (display label, entry interval in
# weeks, signal weekday Mon=0..Fri=4, has_weekly_exit). Drives next-rebalance
# projection. The cadence per universe is declared in
# config.UNIVERSES["rebalance_cadence"].
#
# The biweekly strategies (om25_v3, tl25_v3, combo_defensive) ENTER every other
# Friday but run a weekly rank/drawdown EXIT check on the off-week Fridays too,
# so holdings can be trimmed weekly even though new entries are biweekly. The
# weekly_thu_fri strategies check entries and exits on the same weekly cadence,
# so they need no separate exit overlay.
FRIDAY = 4

CADENCE_META = {
    "weekly_thu_fri":   ("Weekly · Thu signal → Fri", 1, 3, False),
    "biweekly_fri":     ("Biweekly entries · weekly exit checks", 2, 4, True),
    "biweekly_fri_mon": ("Biweekly entries · weekly exit checks (Fri → Mon)", 2, 4, True),
}
DEFAULT_CADENCE = "weekly_thu_fri"


def _project(anchor: date, interval_weeks: int, signal_wd: int, today: date) -> date:
    """Step the `signal_wd`-of-week from `anchor` by `interval_weeks` until it
    lands strictly after `today`, snapping each candidate back onto a real NSE
    trading day (so a holiday Friday falls to that week's Thursday, etc.)."""
    nominal = anchor + timedelta(days=(signal_wd - anchor.weekday()))
    while True:
        candidate = snap_back_to_trading_day(nominal)
        if candidate > today:
            return candidate
        nominal += timedelta(weeks=interval_weeks)


def project_next_signal(last_signal: date, cadence_key: str, today: date) -> date:
    """Project the next ENTRY rebalance date after `today`.

    Anchors on the engine's own last rebalance date and steps the entry cadence
    forward. Weekly exit checks for the biweekly strategies are projected
    separately (next weekly Friday) — see get_rebalance_summary.
    """
    _, interval_weeks, signal_wd, _ = CADENCE_META.get(cadence_key, CADENCE_META[DEFAULT_CADENCE])
    return _project(last_signal, interval_weeks, signal_wd, today)


def project_next_exit_check(today: date) -> date:
    """Next weekly exit-check date (the next trading Friday after `today`)."""
    return _project(today, 1, FRIDAY, today)


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


def get_rebalance_summary(universe: str = "nse500") -> dict:
    """Cadence-aware summary: previous rebalance, next rebalance, holdings.

    Derived from the Trade table (the uniform, DB-backed record of what each
    portfolio actually traded) plus the per-universe cadence in config — not
    the empty Rebalance table or legacy-only changes/orders CSVs.
    """
    cadence_key = UNIVERSES.get(universe, {}).get("rebalance_cadence", DEFAULT_CADENCE)
    label = CADENCE_META.get(cadence_key, CADENCE_META[DEFAULT_CADENCE])[0]

    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        today = date.today()

        # Latest portfolio value, for turnover %.
        pv_row = db.query(EquityCurve.portfolio_value).filter(
            EquityCurve.universe == universe
        ).order_by(desc(EquityCurve.date)).first()
        pv = float(pv_row[0]) if pv_row and pv_row[0] else None

        # Previous rebalance = the most recent trade-date group.
        last_date = db.query(func.max(Trade.trade_date)).filter(
            Trade.universe == universe
        ).scalar()
        previous = None
        if last_date:
            rows = db.query(Trade).filter(
                Trade.universe == universe,
                Trade.trade_date == last_date,
            ).all()
            added = sorted({r.symbol for r in rows if r.side == "BUY"})
            removed = sorted({r.symbol for r in rows if r.side == "SELL"})
            notional = sum(abs(float(r.notional or 0)) for r in rows)
            previous = {
                "date": str(last_date),
                "added": added,
                "removed": removed,
                "buy_count": len(added),
                "sell_count": len(removed),
                "notional_traded": round(notional, 2),
                "turnover_pct": round(notional / pv * 100, 2) if pv else None,
            }

        # Next rebalance = projected from the last entry (BUY) date, which is
        # the engine's last regular rebalance (weekly rank-exits are SELL-only
        # and must not anchor the entry cadence).
        anchor = db.query(func.max(Trade.trade_date)).filter(
            Trade.universe == universe,
            Trade.side == "BUY",
        ).scalar() or last_date
        upcoming = None
        has_weekly_exit = CADENCE_META.get(cadence_key, CADENCE_META[DEFAULT_CADENCE])[3]
        if anchor:
            sig = project_next_signal(anchor, cadence_key, today)
            upcoming = {
                "signal_date": str(sig),
                "exec_date": str(next_trading_day_after(sig)),
                "trading_days_until": trading_days_between(today, sig),
                "has_weekly_exit": has_weekly_exit,
                "exit_check_date": None,
                "exit_check_days_until": None,
            }
            # Biweekly strategies also trim holdings on a weekly exit check;
            # surface the next one so the schedule isn't understated.
            if has_weekly_exit:
                exit_date = project_next_exit_check(today)
                upcoming["exit_check_date"] = str(exit_date)
                upcoming["exit_check_days_until"] = trading_days_between(today, exit_date)

        holdings_count = db.query(func.count(OpenPosition.id)).filter(
            OpenPosition.universe == universe
        ).scalar() or 0

        return {
            "universe": universe,
            "cadence": cadence_key,
            "cadence_label": label,
            "today": str(today),
            "holdings_count": holdings_count,
            "previous": previous,
            "next": upcoming,
        }
    finally:
        db.close()


def get_upcoming_rebalance(universe: str = "nse500") -> dict:
    """Return the EOD-produced "Actionable trades" payload for the page.

    Reads the latest ``ProposedRebalance`` row for ``universe`` (populated by
    ``sync_service.sync_proposed_rebalance`` from
    ``proposed_regime.json``). PLAN.md Phase 2 §3.

    Membership-only contract: ``sells`` are full exits, ``buys`` are new
    entries carrying the model's target weight and optional ₹ sizing,
    ``holds`` are continuing names. The page derives the subscriber's own ₹
    sizing client-side from their portfolio value — the ``est_notional`` /
    ``est_shares`` we hand back here are model-scale ballpark only, sized
    against ``initial_capital`` from the producer.

    Returns ``{"universe", "exec_date": null, "available": false, ...}`` when
    no proposal has been produced yet, so the UI can show a "no upcoming
    rebalance produced yet" state without 404'ing.
    """
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        row = db.query(ProposedRebalance).filter(
            ProposedRebalance.universe == universe
        ).order_by(desc(ProposedRebalance.exec_date)).first()

        if row is None:
            return {
                "universe": universe,
                "available": False,
                "exec_date": None,
                "signal_date": None,
                "data_as_of": None,
                "sells": [], "buys": [], "holds": [],
                "sell_count": 0, "buy_count": 0, "hold_count": 0,
                "regime": None,
                "drawdown_from_peak": None,
                "final_pv": None,
                "initial_capital": None,
            }

        return {
            "universe": universe,
            "available": True,
            "exec_date": str(row.exec_date),
            "signal_date": str(row.signal_date),
            "data_as_of": str(row.data_as_of),
            "sells": row.sells or [],
            "buys": row.buys or [],
            "holds": row.holds or [],
            "sell_count": row.sell_count,
            "buy_count": row.buy_count,
            "hold_count": row.hold_count,
            "regime": row.regime,
            "drawdown_from_peak": (float(row.drawdown_from_peak)
                                    if row.drawdown_from_peak is not None
                                    else None),
            "final_pv": (float(row.final_pv)
                         if row.final_pv is not None else None),
            "initial_capital": (float(row.initial_capital)
                                if row.initial_capital is not None else None),
        }
    finally:
        db.close()


def get_rebalance_history(
    universe: str = "nse500",
    limit: int = 20,
) -> dict:
    """History of past rebalances, derived from the Trade table.

    Groups trades by date (most recent first) into add/drop counts, notional
    traded, and turnover %. Replaces the old implementation that read the
    Rebalance table, which is never populated.
    """
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        dates = [
            r[0] for r in db.query(Trade.trade_date).filter(
                Trade.universe == universe
            ).distinct().order_by(desc(Trade.trade_date)).limit(limit).all()
        ]
        if not dates:
            return {"universe": universe, "history": [], "count": 0}

        rows = db.query(Trade).filter(
            Trade.universe == universe,
            Trade.trade_date.in_(dates),
        ).all()
        pv_map = {
            d: float(v) for d, v in db.query(
                EquityCurve.date, EquityCurve.portfolio_value
            ).filter(EquityCurve.universe == universe).all() if v is not None
        }

        agg: dict = {}
        for r in rows:
            a = agg.setdefault(r.trade_date, {"buys": 0, "sells": 0, "notional": 0.0})
            if r.side == "BUY":
                a["buys"] += 1
            elif r.side == "SELL":
                a["sells"] += 1
            a["notional"] += abs(float(r.notional or 0))

        history = []
        for d in sorted(agg.keys(), reverse=True):
            a = agg[d]
            pv = pv_map.get(d)
            history.append({
                "date": str(d),
                "additions": a["buys"],
                "removals": a["sells"],
                "notional": round(a["notional"], 2),
                "turnover_pct": round(a["notional"] / pv * 100, 2) if pv else None,
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
