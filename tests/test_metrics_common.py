"""Tests for scripts/metrics_common.py.

Two layers:
1. Synthetic deterministic checks for CAGR/Sharpe/MDD math.
2. Regression check against the captured Phase 0 baseline — each of the
   four production portfolios on disk has a `momentum_metrics.csv`
   produced by the pre-consolidation inline code; this test feeds the
   same equity/trades/exits CSVs back through the new module and asserts
   bit-equivalence (within 1e-9 float tolerance).
"""
from __future__ import annotations

import math
import sys
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from scripts.metrics_common import (  # noqa: E402
    DEFAULT_RF_RATE, compute_dashboard_metrics,
)


def _eq(dates, values):
    return pd.DataFrame({
        "date": pd.to_datetime(dates),
        "portfolio_value": values,
    })


class SyntheticMetricsTests(unittest.TestCase):
    def test_flat_equity_zero_metrics(self):
        dates = pd.date_range("2020-01-01", periods=252, freq="B")
        eq = _eq(dates, [1_000_000.0] * len(dates))
        m = compute_dashboard_metrics(eq, pd.DataFrame({"side": []}),
                                      pd.DataFrame())
        self.assertAlmostEqual(m["total_return"], 0.0, places=10)
        self.assertAlmostEqual(m["cagr"], 0.0, places=10)
        self.assertAlmostEqual(m["annualized_volatility"], 0.0, places=10)
        # vol == 0 -> sharpe falls back to 0 by the guard branch
        self.assertEqual(m["sharpe_ratio"], 0)
        self.assertAlmostEqual(m["max_drawdown"], 0.0, places=10)
        self.assertEqual(m["trades_total"], 0)
        self.assertEqual(m["buys"], 0)
        self.assertEqual(m["sells"], 0)
        self.assertEqual(m["hit_rate_overall"], 0)
        self.assertEqual(m["avg_holding_days"], 0)

    def test_one_year_doubling_cagr(self):
        start, end = pd.Timestamp("2020-01-01"), pd.Timestamp("2021-01-01")
        eq = _eq([start, end], [1_000_000.0, 2_000_000.0])
        m = compute_dashboard_metrics(eq, pd.DataFrame({"side": []}),
                                      pd.DataFrame())
        # CAGR over exactly 366 days (2020 was a leap year):
        expected_cagr = 2.0 ** (365.25 / 366) - 1
        self.assertAlmostEqual(m["cagr"], expected_cagr, places=10)
        self.assertAlmostEqual(m["total_return"], 1.0, places=10)
        self.assertEqual(m["start"], date(2020, 1, 1))
        self.assertEqual(m["end"], date(2021, 1, 1))

    def test_max_drawdown_is_trough_from_running_peak(self):
        dates = pd.to_datetime([
            "2020-01-01", "2020-02-01", "2020-03-01", "2020-04-01", "2020-05-01",
        ])
        # peak 1.5M at t=1, trough 0.9M at t=3 -> MDD = 0.9/1.5 - 1 = -0.4
        eq = _eq(dates, [1.0e6, 1.5e6, 1.2e6, 0.9e6, 1.1e6])
        m = compute_dashboard_metrics(eq, pd.DataFrame({"side": []}),
                                      pd.DataFrame())
        self.assertAlmostEqual(m["max_drawdown"], 0.9 / 1.5 - 1, places=10)

    def test_trade_counts_split_by_side(self):
        dates = pd.date_range("2020-01-01", periods=3, freq="D")
        eq = _eq(dates, [1.0e6, 1.0e6, 1.0e6])
        trades = pd.DataFrame({"side": ["BUY", "BUY", "SELL", "BUY", "SELL"]})
        m = compute_dashboard_metrics(eq, trades, pd.DataFrame())
        self.assertEqual(m["trades_total"], 5)
        self.assertEqual(m["buys"], 3)
        self.assertEqual(m["sells"], 2)

    def test_hit_rate_and_avg_hold_from_exits(self):
        dates = pd.date_range("2020-01-01", periods=2, freq="D")
        eq = _eq(dates, [1.0e6, 1.0e6])
        exits = pd.DataFrame({
            "pnl_pct": [0.1, -0.05, 0.02, -0.01],
            "hold_days": [10, 20, 30, 40],
        })
        m = compute_dashboard_metrics(eq, pd.DataFrame({"side": []}), exits)
        self.assertAlmostEqual(m["hit_rate_overall"], 0.5, places=10)
        self.assertAlmostEqual(m["avg_holding_days"], 25.0, places=10)

    def test_turnover_gross_contemporaneous(self):
        # Flat 1M book so turnover fractions are exact. Two rebalance dates:
        #   2020-01-01: BUY 100k + SELL 100k -> gross 200k -> 20% of 1M
        #   2020-07-01: BUY 50k            -> gross  50k ->  5% of 1M
        dates = pd.to_datetime(["2020-01-01", "2020-07-01", "2021-01-01"])
        eq = _eq(dates, [1_000_000.0, 1_000_000.0, 1_000_000.0])
        trades = pd.DataFrame({
            "date": pd.to_datetime(["2020-01-01", "2020-01-01", "2020-07-01"]),
            "side": ["BUY", "SELL", "BUY"],
            # sells stored negative — turnover is sign-agnostic (abs)
            "notional": [100_000.0, -100_000.0, 50_000.0],
        })
        m = compute_dashboard_metrics(eq, trades, pd.DataFrame())
        self.assertAlmostEqual(m["avg_turnover_pct"], (0.20 + 0.05) / 2, places=10)
        yrs = (dates[-1] - dates[0]).days / 365.25
        self.assertAlmostEqual(m["annualized_turnover"], 0.25 / yrs, places=10)

    def test_turnover_none_without_notional(self):
        dates = pd.date_range("2020-01-01", periods=2, freq="D")
        eq = _eq(dates, [1.0e6, 1.0e6])
        trades = pd.DataFrame({"side": ["BUY", "SELL"]})  # no notional/date cols
        m = compute_dashboard_metrics(eq, trades, pd.DataFrame())
        self.assertIsNone(m["avg_turnover_pct"])
        self.assertIsNone(m["annualized_turnover"])

    def test_sharpe_uses_rf_rate(self):
        # Construct an equity with non-zero vol and known CAGR-ish.
        dates = pd.date_range("2020-01-01", periods=253, freq="B")
        vals = [1_000_000.0]
        # Alternating +0.5%/-0.4% returns: gentle drift up with vol.
        for i in range(1, len(dates)):
            vals.append(vals[-1] * (1.005 if i % 2 else 0.996))
        eq = _eq(dates, vals)
        m0 = compute_dashboard_metrics(eq, pd.DataFrame({"side": []}),
                                        pd.DataFrame(), rf_rate=0.0)
        m5 = compute_dashboard_metrics(eq, pd.DataFrame({"side": []}),
                                        pd.DataFrame(), rf_rate=0.05)
        # rf=5% must lower the Sharpe ratio relative to rf=0
        self.assertLess(m5["sharpe_ratio"], m0["sharpe_ratio"])
        # And the difference equals 0.05 / vol exactly
        self.assertAlmostEqual(
            m0["sharpe_ratio"] - m5["sharpe_ratio"],
            0.05 / m0["annualized_volatility"],
            places=10,
        )

    def test_default_rf_rate_is_five_percent(self):
        self.assertEqual(DEFAULT_RF_RATE, 0.05)


# --------------------------------------------------------------------------
# Regression: reproduce existing momentum_metrics.csv from on-disk inputs
# --------------------------------------------------------------------------

PORTFOLIO_RUNS = {
    "om25_v3":
        ("data/om25_v3_portfolios",         "om25_v3_portfolio_",
         "om25_trades.csv", "om25_exits.csv"),
    "tl25_v3":
        ("data/tl25_v3_portfolios",         "tl25_v3_portfolio_",
         "tl25_trades.csv", "tl25_exits.csv"),
    "l6_v2":
        ("data/l6_v2_portfolios",           "l6_v2_portfolio_",
         "l6_trades.csv", "l6_exits.csv"),
    "combo_defensive":
        ("data/combo_defensive_portfolios", "combo_defensive_portfolio_",
         "combo_trades.csv", "combo_exits.csv"),
}

NUMERIC_FIELDS = [
    "total_return", "cagr", "max_drawdown", "sharpe_ratio",
    "annualized_volatility", "hit_rate_overall", "avg_holding_days",
]
INT_FIELDS = ["trades_total", "buys", "sells"]


def _latest_run_dir(parent_rel: str, prefix: str) -> Path | None:
    parent = ROOT / parent_rel
    if not parent.exists():
        return None
    cands = sorted(p for p in parent.iterdir()
                   if p.is_dir() and p.name.startswith(prefix))
    return cands[-1] if cands else None


class RegressionAgainstBaseline(unittest.TestCase):
    """Re-derive momentum_metrics.csv from native equity/trades/exits and
    compare to the on-disk file for each portfolio. Confirms the unified
    module is bit-equivalent (to 1e-9) with the inline code that produced
    the Phase 0 baseline.
    """

    def _run_one(self, universe: str, parent_rel: str, prefix: str,
                 trades_name: str, exits_name: str):
        run = _latest_run_dir(parent_rel, prefix)
        if run is None:
            self.skipTest(f"no run dir under {parent_rel}")
        dash = run / "backtests" / "baseline"
        eq_path = dash / "momentum_equity.csv"
        metrics_path = dash / "momentum_metrics.csv"
        trades_path = run / trades_name
        exits_path = run / exits_name

        for p in (eq_path, metrics_path, trades_path, exits_path):
            if not p.exists():
                self.skipTest(f"missing input: {p.relative_to(ROOT)}")

        eq = pd.read_csv(eq_path, parse_dates=["date"])
        # Native trades CSVs from these engines use a 'side' column.
        trades = pd.read_csv(trades_path)
        exits = pd.read_csv(exits_path) if exits_path.exists() else pd.DataFrame()

        actual = compute_dashboard_metrics(eq, trades, exits,
                                           rf_rate=DEFAULT_RF_RATE)
        expected_row = pd.read_csv(metrics_path).iloc[0]

        for field in NUMERIC_FIELDS:
            self.assertAlmostEqual(
                float(actual[field]),
                float(expected_row[field]),
                places=9,
                msg=f"{universe}.{field}: {actual[field]} vs {expected_row[field]}",
            )
        for field in INT_FIELDS:
            self.assertEqual(
                int(actual[field]),
                int(expected_row[field]),
                msg=f"{universe}.{field}: {actual[field]} vs {expected_row[field]}",
            )

    def test_om25_v3(self):
        self._run_one("om25_v3", *PORTFOLIO_RUNS["om25_v3"])

    def test_tl25_v3(self):
        self._run_one("tl25_v3", *PORTFOLIO_RUNS["tl25_v3"])

    def test_l6_v2(self):
        self._run_one("l6_v2", *PORTFOLIO_RUNS["l6_v2"])

    def test_combo_defensive(self):
        self._run_one("combo_defensive", *PORTFOLIO_RUNS["combo_defensive"])


if __name__ == "__main__":
    unittest.main()
