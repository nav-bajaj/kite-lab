"""Tests for scripts/pipeline_core.py.

Synthetic price/benchmark/regime data round-trips through the
``PipelineState`` dataclass + pickle cache and validates the resulting
state. Heavy real-data validation lives in the Phase 2 RESULTS.md
write-up (the bit-identical diff of TL25/L6/OM25/COMBO outputs with vs
without the cache).
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from scripts import pipeline_core  # noqa: E402
from scripts.pipeline_core import (  # noqa: E402
    PipelineState, dump_to_cache, load_from_cache, describe,
    CACHE_SCHEMA_VERSION,
)


def _synthetic_state() -> PipelineState:
    dates = pd.date_range("2024-01-01", periods=30, freq="B")
    close = pd.DataFrame({"INFY": range(1500, 1530), "TCS": range(3500, 3530)},
                         index=dates)
    trade = close + 5.0
    bench = pd.Series(range(20000, 20030), index=dates, dtype=float)
    regime = pd.Series([True] * 20 + [False] * 10, index=dates)
    return PipelineState(
        close_panel=close, trade_panel=trade, benchmark=bench,
        regime_panel=regime,
        prices_dir="synthetic", benchmark_path="synthetic",
        regime_index_path="synthetic", captured_at="2024-01-01T00:00:00",
    )


class PipelineCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(
            prefix="test_pipeline_state_", suffix=".pkl", delete=False,
        )
        self.tmp.close()
        self.path = Path(self.tmp.name)

    def tearDown(self):
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass

    def test_roundtrip_pickle(self):
        st = _synthetic_state()
        dump_to_cache(st, self.path)
        loaded = load_from_cache(self.path)
        pd.testing.assert_frame_equal(loaded.close_panel, st.close_panel)
        pd.testing.assert_frame_equal(loaded.trade_panel, st.trade_panel)
        pd.testing.assert_series_equal(loaded.benchmark, st.benchmark)
        pd.testing.assert_series_equal(loaded.regime_panel, st.regime_panel)
        self.assertEqual(loaded.captured_at, st.captured_at)
        self.assertEqual(loaded.schema_version, CACHE_SCHEMA_VERSION)

    def test_describe_summary(self):
        st = _synthetic_state()
        s = describe(st)
        self.assertIn("2 symbols", s)
        self.assertIn("30 dates", s)
        self.assertIn("with regime", s)

    def test_describe_without_regime(self):
        st = _synthetic_state()
        st_no_regime = PipelineState(
            close_panel=st.close_panel, trade_panel=st.trade_panel,
            benchmark=st.benchmark, regime_panel=None,
            prices_dir="synthetic", benchmark_path="synthetic",
            regime_index_path="", captured_at="2024-01-01T00:00:00",
        )
        s = describe(st_no_regime)
        self.assertIn("no regime", s)

    def test_schema_version_mismatch_raises(self):
        st = _synthetic_state()
        dump_to_cache(st, self.path)
        # Bump the in-memory schema version so loading the dump fails.
        original = pipeline_core.CACHE_SCHEMA_VERSION
        try:
            pipeline_core.CACHE_SCHEMA_VERSION = original + 1
            with self.assertRaises(ValueError) as ctx:
                load_from_cache(self.path)
            self.assertIn("schema version mismatch", str(ctx.exception))
        finally:
            pipeline_core.CACHE_SCHEMA_VERSION = original

    def test_load_wrong_type_raises(self):
        # Write something that isn't a PipelineState.
        import pickle
        with self.path.open("wb") as f:
            pickle.dump({"not": "a pipeline state"}, f)
        with self.assertRaises(TypeError):
            load_from_cache(self.path)


if __name__ == "__main__":
    unittest.main()
