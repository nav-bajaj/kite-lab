"""Tests for scripts/sync_validation.py.

Builds synthetic run directories with deliberately malformed CSVs and
asserts the validator catches each failure mode. Uses a tempdir + a
patched REPO_ROOT / RUN_DIR_GLOBS so we don't touch the real data dirs.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from scripts import sync_validation  # noqa: E402


def _make_run(parent: Path, prefix: str, ts: str = "20260101_120000"):
    run = parent / f"{prefix}{ts}"
    (run / "backtests" / "baseline").mkdir(parents=True)
    return run


def _good_csvs(run: Path):
    """Write a known-good set of 4 dashboard CSVs to <run>/backtests/baseline."""
    dash = run / "backtests" / "baseline"
    pd.DataFrame({
        "date": pd.date_range("2020-01-01", periods=60, freq="B"),
        "portfolio_value": [1_000_000 + i * 100 for i in range(60)],
    }).to_csv(dash / "momentum_equity.csv", index=False)
    pd.DataFrame({
        "date": ["2020-01-01", "2020-01-08"],
        "symbol": ["INFY", "INFY"],
        "side": ["BUY", "SELL"],
        "shares": [10, 10],
        "price": [1200.0, 1300.0],
    }).to_csv(dash / "momentum_trades.csv", index=False)
    pd.DataFrame({
        "symbol": ["TCS"], "shares": [5], "avg_cost": [3000.0],
    }).to_csv(dash / "momentum_holdings.csv", index=False)
    pd.DataFrame([{
        "start": "2020-01-01", "end": "2020-03-31",
        "cagr": 0.10, "max_drawdown": -0.05,
        "sharpe_ratio": 1.2, "trades_total": 2,
    }]).to_csv(dash / "momentum_metrics.csv", index=False)


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_root = Path(self.tmp.name)
        (self.tmp_root / "data" / "test_portfolios").mkdir(parents=True)
        # Patch the validator's view of the repo root + universe registry.
        self._patches = [
            patch.object(sync_validation, "REPO_ROOT", self.tmp_root),
            patch.object(sync_validation, "RUN_DIR_GLOBS", {
                "test_strategy": ("data/test_portfolios", "test_portfolio_"),
            }),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        self.tmp.cleanup()

    def _run_dir(self) -> Path:
        return _make_run(self.tmp_root / "data" / "test_portfolios",
                         "test_portfolio_")

    def test_no_run_dir_warns_but_passes(self):
        rep = sync_validation.validate_universe("test_strategy")
        self.assertTrue(rep.ok)
        self.assertEqual(rep.run_dir, None)
        self.assertTrue(any("no run dir" in w for w in rep.warnings))

    def test_unknown_universe_warns(self):
        rep = sync_validation.validate_universe("not_a_universe")
        self.assertTrue(rep.ok)
        self.assertTrue(any("no glob pattern" in w for w in rep.warnings))

    def test_good_run_passes(self):
        run = self._run_dir()
        _good_csvs(run)
        rep = sync_validation.validate_universe("test_strategy")
        self.assertTrue(rep.ok, msg=f"errors={rep.errors}")
        self.assertEqual(rep.errors, [])

    def test_missing_file_fails(self):
        run = self._run_dir()
        _good_csvs(run)
        (run / "backtests" / "baseline" / "momentum_trades.csv").unlink()
        rep = sync_validation.validate_universe("test_strategy")
        self.assertFalse(rep.ok)
        self.assertTrue(any("missing" in e and "momentum_trades.csv" in e
                            for e in rep.errors))

    def test_missing_required_column_fails(self):
        run = self._run_dir()
        _good_csvs(run)
        df = pd.read_csv(run / "backtests" / "baseline" / "momentum_metrics.csv")
        df = df.drop(columns=["sharpe_ratio"])
        df.to_csv(run / "backtests" / "baseline" / "momentum_metrics.csv",
                  index=False)
        rep = sync_validation.validate_universe("test_strategy")
        self.assertFalse(rep.ok)
        self.assertTrue(any("missing columns" in e and "sharpe_ratio" in e
                            for e in rep.errors))

    def test_non_monotonic_dates_fail(self):
        run = self._run_dir()
        _good_csvs(run)
        path = run / "backtests" / "baseline" / "momentum_equity.csv"
        df = pd.read_csv(path)
        # swap two rows so dates go backward
        df.iloc[0], df.iloc[1] = df.iloc[1].copy(), df.iloc[0].copy()
        df.to_csv(path, index=False)
        rep = sync_validation.validate_universe("test_strategy")
        self.assertFalse(rep.ok)
        self.assertTrue(any("not strictly increasing" in e for e in rep.errors))

    def test_non_positive_portfolio_value_fails(self):
        run = self._run_dir()
        _good_csvs(run)
        path = run / "backtests" / "baseline" / "momentum_equity.csv"
        df = pd.read_csv(path)
        df.loc[5, "portfolio_value"] = -1
        df.to_csv(path, index=False)
        rep = sync_validation.validate_universe("test_strategy")
        self.assertFalse(rep.ok)
        self.assertTrue(any("non-positive portfolio_value" in e for e in rep.errors))

    def test_bad_trade_side_fails(self):
        run = self._run_dir()
        _good_csvs(run)
        path = run / "backtests" / "baseline" / "momentum_trades.csv"
        df = pd.read_csv(path)
        df.loc[0, "side"] = "SHORT"
        df.to_csv(path, index=False)
        rep = sync_validation.validate_universe("test_strategy")
        self.assertFalse(rep.ok)
        self.assertTrue(any("unrecognised sides" in e for e in rep.errors))

    def test_positive_max_drawdown_fails(self):
        run = self._run_dir()
        _good_csvs(run)
        path = run / "backtests" / "baseline" / "momentum_metrics.csv"
        df = pd.read_csv(path)
        df.loc[0, "max_drawdown"] = 0.05  # impossible (should be <=0)
        df.to_csv(path, index=False)
        rep = sync_validation.validate_universe("test_strategy")
        self.assertFalse(rep.ok)
        self.assertTrue(any("max_drawdown is positive" in e for e in rep.errors))

    def test_metrics_with_inf_sharpe_fails(self):
        run = self._run_dir()
        _good_csvs(run)
        path = run / "backtests" / "baseline" / "momentum_metrics.csv"
        df = pd.read_csv(path)
        df.loc[0, "sharpe_ratio"] = float("inf")
        df.to_csv(path, index=False)
        rep = sync_validation.validate_universe("test_strategy")
        self.assertFalse(rep.ok)
        self.assertTrue(any("sharpe_ratio is not finite" in e for e in rep.errors))

    def test_empty_holdings_warns_not_fails(self):
        run = self._run_dir()
        _good_csvs(run)
        path = run / "backtests" / "baseline" / "momentum_holdings.csv"
        # Empty but still has header row
        pd.DataFrame(columns=["symbol", "shares", "avg_cost"]).to_csv(
            path, index=False,
        )
        rep = sync_validation.validate_universe("test_strategy")
        self.assertTrue(rep.ok, msg=f"errors={rep.errors}")
        self.assertTrue(any("no current positions" in w for w in rep.warnings))


if __name__ == "__main__":
    unittest.main()
