"""End-to-end test of the proposal artifact writer with synthetic run data."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._proposal import emit_proposal, is_entry_week  # noqa: E402


def _setup_run(tmp_path, current):
    """Write the dashboard CSVs a runner produces; return the dashboard dir."""
    d = tmp_path / "backtests" / "baseline"
    d.mkdir(parents=True)
    pd.DataFrame({"symbol": current, "shares": [1] * len(current)}).to_csv(
        d / "momentum_holdings.csv", index=False
    )
    pd.DataFrame(
        {"date": ["2026-06-12", "2026-06-19"],
         "portfolio_value": [900000.0, 1000000.0],
         "drawdown": [-0.05, -0.02]}
    ).to_csv(d / "momentum_equity.csv", index=False)
    return d


def test_emit_writes_artifact_with_engine_faithful_membership(tmp_path):
    # close panel: last bar is T-1 = 2026-06-18 (Thu); rebalance is Fri 06-19.
    cal = pd.to_datetime(["2026-06-17", "2026-06-18"])
    syms = ["S00", "S01", "S02", "S03", "S04", "S99"]
    close = pd.DataFrame(
        [[100, 50, 30, 20, 10, 5], [100, 50, 30, 20, 10, 5]],
        index=cal, columns=syms,
    )

    def score_fn(_date):
        # ranking S00 > S01 > ... ; S99 worst
        return pd.Series({"S00": 6, "S01": 5, "S02": 4, "S03": 3, "S04": 2, "S99": 1})

    dash = _setup_run(tmp_path, current=["S03", "S99"])
    meta = emit_proposal(
        dashboard_dir=dash, score_fn=score_fn, close_panel=close, calendar=cal,
        entry_dates=["2026-06-05"], top_n=3, exit_buffer=2, interval_weeks=2,
    )

    # 2026-06-05 -> +2wk -> Fri 2026-06-19 is an entry week.
    assert meta["is_entry"] is True
    assert meta["target_date"] == "2026-06-19"

    orders = pd.read_csv(dash / "proposed_orders_2026-06-19.csv")
    sells = orders[orders.side == "SELL"]["symbol"].tolist()
    buys = orders[orders.side == "BUY"]["symbol"].tolist()
    assert sells == ["S99"]                 # fell outside top_n+buffer
    assert buys == ["S00", "S01"]           # fill to top_n, S03 retained in buffer
    # sizing: equal weight 1/3 of 1,000,000 = 333,333; S00 @100 -> 3333 sh
    s00 = orders[orders.symbol == "S00"].iloc[0]
    assert s00["est_shares"] == 3333

    meta_on_disk = json.loads((dash / "proposal_meta.json").read_text())
    assert meta_on_disk["buy_count"] == 2 and meta_on_disk["sell_count"] == 1


def test_is_entry_week_parity():
    last = pd.Timestamp("2026-06-19")  # a Friday, entry anchor
    # +1 week (2026-06-26 week) -> off-week exit-only for biweekly
    assert is_entry_week(["2026-06-19"], pd.Timestamp("2026-06-22"), 2) is False
    # +2 weeks -> entry
    assert is_entry_week(["2026-06-19"], pd.Timestamp("2026-06-29"), 2) is True
    # weekly strategy: every Friday is an entry
    assert is_entry_week(["2026-06-19"], pd.Timestamp("2026-06-22"), 1) is True
